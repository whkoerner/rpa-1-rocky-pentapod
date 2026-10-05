"""Deterministic Brain v0.2 orchestration and state ownership."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from threading import Lock
from typing import Callable, Protocol
from uuid import uuid4

from csp.core import CspCodec
from csp.wire import INTENTS, WireMessage, canonical_text, chordic_token, encode
from csp.conversation import Utterance, encode_text
from csp.exp002 import encode_phrase as encode_exp002_phrase
from csp.learning import encode_phrase
from rpa_link.messages import Mode, monotonic_us

from .ai import AIProvider
from .contracts import (
    AIContext,
    BrainConfig,
    BrainOutcome,
    BrainResult,
    CommunicationOutput,
    ConversationOutput,
    ConnectionState,
    HardwareCommand,
    HardwareReceipt,
    HardwareStatus,
    ReceiptStatus,
    RequestContext,
    RequestOrigin,
    ResultCode,
    RobotState,
    SafetyDecision,
)
from .hardware import HardwareInterface
from .safety import SafetyValidator
from .validation import CandidateValidationError, validate_candidate, validate_utterance

_NOT_SUPPLIED = object()


class EventLogger(Protocol):
    def write(self, event: dict[str, object]) -> None:
        ...

    def close(self) -> None:
        ...


class NullEventLogger:
    def write(self, event: dict[str, object]) -> None:
        del event

    def close(self) -> None:
        return None


class JsonlEventLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = path.open("a", encoding="utf-8", newline="\n")

    def write(self, event: dict[str, object]) -> None:
        self._handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
        self._handle.write("\n")
        self._handle.flush()

    def close(self) -> None:
        self._handle.close()


class TaskController:
    """Finite allowlisted task selection; v0.2 implements communication only."""

    def __init__(self, codec: CspCodec, text_encoding: str = "ct2") -> None:
        if text_encoding not in {"ct1", "ct2", "exp002"}:
            raise ValueError("text_encoding must be ct1, ct2 or exp002")
        self._codec = codec
        self.text_encoding = text_encoding

    def build_communication(self, message) -> CommunicationOutput | ConversationOutput:
        if isinstance(message, Utterance):
            if self.text_encoding != "exp002":
                for intent, (text, _) in INTENTS.items():
                    if message.text == text:
                        return self.build_communication(WireMessage(intent))
            if self.text_encoding == "ct1":
                return ConversationOutput(message, message.text, encode_text(message.text))
            if self.text_encoding == "exp002":
                return ConversationOutput(message, message.text, (), encode_exp002_phrase(message.text))
            return ConversationOutput(message, message.text, (), encode_phrase(message.text))
        csp_line = encode(message)
        text = canonical_text(message)
        token = chordic_token(message)
        notes = self._codec.encode_token(token).notes
        return CommunicationOutput(
            message=message,
            csp_line=csp_line,
            canonical_text=text,
            chordic_token=token,
            notes=notes,
        )


class BrainController:
    def __init__(
        self,
        *,
        provider: AIProvider,
        hardware: HardwareInterface,
        safety: SafetyValidator | None = None,
        config: BrainConfig | None = None,
        codec: CspCodec | None = None,
        clock_us: Callable[[], int] = monotonic_us,
        event_logger: EventLogger | None = None,
        session_id: str | None = None,
    ) -> None:
        self.provider = provider
        self.hardware = hardware
        self.safety = safety or SafetyValidator()
        self.config = config or BrainConfig()
        self.codec = codec or CspCodec.from_default_spec()
        self.clock_us = clock_us
        self.event_logger = event_logger or NullEventLogger()
        self.task_controller = TaskController(self.codec)
        self._next_request_id = 1
        self._next_command_id = 1
        self._busy = False
        self._busy_lock = Lock()
        self._stop_generation = 0
        self.state = RobotState(session_id=session_id or uuid4().hex)

    def boot(self) -> RobotState:
        self.state = replace(
            self.state,
            revision=self.state.revision + 1,
            connection_state=ConnectionState.CONNECTING,
            host_motion_mode=(Mode.ESTOP if self.state.estop_latched else Mode.DISABLED),
            pending_command_id=None,
        )
        try:
            status = self.hardware.open()
        except Exception as exc:
            self.state = replace(
                self.state,
                revision=self.state.revision + 1,
                connection_state=ConnectionState.FAULT,
                latest_fault="BACKEND_OPEN_FAILED",
            )
            self._log("boot_failed", detail=type(exc).__name__)
            return self.state

        self._apply_status(status)
        self._log("boot", backend=status.backend_id, native_mode=status.native_mode)
        return self.state

    def submit_text(self, text: str) -> BrainResult:
        return self._submit(text)

    def submit_utterance(self, candidate: object) -> BrainResult:
        """Accept an untrusted text candidate after supervised inference; validate again."""
        return self._submit("", candidate)

    def _submit(self, text: str, candidate: object = _NOT_SUPPLIED) -> BrainResult:
        request_id = self._allocate_request_id()
        with self._busy_lock:
            if self._busy:
                return self._result(request_id, BrainOutcome.REJECTED, ResultCode.BUSY)
            self._busy = True
        try:
            return self._submit_text(request_id, text, candidate)
        finally:
            with self._busy_lock:
                self._busy = False

    def _submit_text(self, request_id: int, text: str, supplied: object = _NOT_SUPPLIED) -> BrainResult:
        if self.state.pending_command_id is not None:
            return self._result(request_id, BrainOutcome.REJECTED, ResultCode.BUSY)
        if self.state.connection_state != ConnectionState.READY:
            return self._result(
                request_id,
                BrainOutcome.REJECTED,
                ResultCode.BACKEND_UNAVAILABLE,
            )
        if self.state.estop_latched:
            return self._result(
                request_id,
                BrainOutcome.REJECTED,
                ResultCode.ESTOP_LATCHED,
            )
        if type(text) is not str or len(text.encode("utf-8")) > self.config.max_input_bytes:
            return self._result(
                request_id,
                BrainOutcome.REJECTED,
                ResultCode.INVALID_RESPONSE,
                detail="input exceeds configured text limits",
            )

        received_us = self.clock_us()
        stop_generation = self._stop_generation
        request = RequestContext(
            session_id=self.state.session_id,
            request_id=request_id,
            origin=RequestOrigin.PROVIDER,
            received_us=received_us,
            deadline_us=received_us + self.config.operation_timeout_ms * 1000,
        )
        self._log("request_received", request_id=request_id)

        provider_started = self.clock_us()
        try:
            candidate = self.provider.propose(text, self._ai_context()) if supplied is _NOT_SUPPLIED else supplied
        except Exception as exc:
            return self._result(
                request_id,
                BrainOutcome.FAILED,
                ResultCode.PROVIDER_FAILED,
                detail=type(exc).__name__,
            )
        provider_finished = self.clock_us()
        if self._stop_generation != stop_generation:
            return self._result(
                request_id,
                BrainOutcome.CANCELLED,
                ResultCode.ESTOP_LATCHED,
                detail="request invalidated by emergency stop",
            )
        if provider_finished - provider_started > self.config.provider_timeout_ms * 1000:
            return self._result(
                request_id,
                BrainOutcome.REJECTED,
                ResultCode.PROVIDER_TIMEOUT,
            )
        if candidate is None:
            return self._result(request_id, BrainOutcome.REJECTED, ResultCode.NO_MATCH)
        if not self._provider_response_within_limit(candidate):
            return self._result(
                request_id,
                BrainOutcome.REJECTED,
                ResultCode.INVALID_RESPONSE,
                detail="provider response exceeds configured limit",
            )

        try:
            message = validate_candidate(candidate) if supplied is _NOT_SUPPLIED else validate_utterance(candidate)
        except CandidateValidationError as exc:
            detail = exc.detail
            if exc.wire_code:
                detail = f"CSP_{exc.wire_code}: {detail}"
            return self._result(
                request_id,
                BrainOutcome.REJECTED,
                exc.code,
                detail=detail,
            )

        decision = self.safety.validate(message, request, self.state, self.clock_us())
        if not decision.allowed:
            return self._result(
                request_id,
                BrainOutcome.REJECTED,
                decision.code,
                safety=decision,
            )

        try:
            communication = self.task_controller.build_communication(message)
        except Exception as exc:
            return self._result(
                request_id,
                BrainOutcome.FAILED,
                ResultCode.INTERNAL_ERROR,
                detail=type(exc).__name__,
                safety=decision,
            )

        command_id = self._allocate_command_id()
        self.state = replace(
            self.state,
            revision=self.state.revision + 1,
            pending_command_id=command_id,
            last_communication=communication,
        )
        command = HardwareCommand(
            command_id=command_id,
            session_id=self.state.session_id,
            request_id=request_id,
            deadline_us=request.deadline_us,
            communication=communication,
        )

        decision = self.safety.validate(message, request, self.state, self.clock_us())
        if not decision.allowed:
            self.state = replace(
                self.state,
                revision=self.state.revision + 1,
                pending_command_id=None,
            )
            return self._result(
                request_id,
                BrainOutcome.REJECTED,
                decision.code,
                communication=communication,
                safety=decision,
            )

        self._log(
            "dispatch",
            request_id=request_id,
            command_id=command_id,
            state_revision=decision.state_revision,
        )
        try:
            receipt = self.hardware.dispatch(command)
        except Exception as exc:
            return self._backend_failure(
                request_id,
                communication,
                decision,
                type(exc).__name__,
            )

        if receipt.command_id != command_id or receipt.session_id != self.state.session_id:
            return self._backend_failure(
                request_id,
                communication,
                decision,
                "receipt correlation mismatch",
            )

        outcome, code = self._map_receipt(receipt)
        self.state = replace(
            self.state,
            revision=self.state.revision + 1,
            pending_command_id=None,
            last_result_code=code.value,
        )
        result = BrainResult(
            request_id=request_id,
            outcome=outcome,
            code=code,
            state_revision=self.state.revision,
            communication=communication,
            receipt=receipt,
            safety=decision,
            detail=receipt.reason,
        )
        self._log(
            "result",
            request_id=request_id,
            command_id=command_id,
            outcome=outcome.value,
            code=code.value,
            evidence=receipt.evidence_kind.value,
        )
        return result

    def emergency_stop(self, reason: str = "OPERATOR_ESTOP") -> HardwareReceipt:
        self._stop_generation += 1
        self.state = replace(
            self.state,
            revision=self.state.revision + 1,
            estop_latched=True,
            host_motion_mode=Mode.ESTOP,
            pending_command_id=None,
            latest_fault=reason,
        )
        self._log("emergency_stop", reason=reason)
        try:
            return self.hardware.stop(reason, emergency=True)
        except Exception:
            self.state = replace(
                self.state,
                revision=self.state.revision + 1,
                connection_state=ConnectionState.FAULT,
                latest_fault="BACKEND_STOP_FAILED",
            )
            raise

    def reset_stop(self) -> bool:
        """Explicit operator recovery. It never arms or starts a task."""
        if not self.state.estop_latched or self.state.pending_command_id is not None:
            return False
        try:
            self.hardware.close()
            status = self.hardware.open()
        except Exception:
            self.state = replace(
                self.state,
                revision=self.state.revision + 1,
                connection_state=ConnectionState.FAULT,
                latest_fault="BACKEND_RESET_FAILED",
            )
            return False
        if status.connection_state != ConnectionState.READY:
            self._apply_status(status)
            return False
        self._apply_status(status)
        self.state = replace(
            self.state,
            revision=self.state.revision + 1,
            estop_latched=False,
            host_motion_mode=Mode.DISABLED,
            latest_fault="",
            pending_command_id=None,
        )
        self._log("reset_stop")
        return True

    def close(self) -> None:
        try:
            self.hardware.close()
        finally:
            self.event_logger.close()

    def _ai_context(self) -> AIContext:
        return AIContext(
            schema_version="brain-request-v0.2",
            allowed_intents=tuple(sorted(INTENTS)),
            backend_id=self.state.backend_id,
            connection_state=self.state.connection_state.value,
            host_motion_mode=self.state.host_motion_mode.value,
            estop_latched=self.state.estop_latched,
        )

    def _provider_response_within_limit(self, candidate: object) -> bool:
        try:
            raw = json.dumps(candidate, ensure_ascii=True, separators=(",", ":"))
        except (TypeError, ValueError):
            return False
        return len(raw.encode("utf-8")) <= self.config.max_provider_response_bytes

    def _apply_status(self, status: HardwareStatus) -> None:
        self.state = replace(
            self.state,
            revision=self.state.revision + 1,
            backend_id=status.backend_id,
            connection_state=status.connection_state,
            capabilities=status.capabilities,
            native_mode=status.native_mode,
            observations=status.observations,
            host_motion_mode=Mode.DISABLED,
            pending_command_id=None,
        )

    def _backend_failure(
        self,
        request_id: int,
        communication: CommunicationOutput,
        decision: SafetyDecision,
        detail: str,
    ) -> BrainResult:
        try:
            self.hardware.stop("BACKEND_FAILED", emergency=False)
        except Exception:
            pass
        self.state = replace(
            self.state,
            revision=self.state.revision + 1,
            pending_command_id=None,
            connection_state=ConnectionState.FAULT,
            latest_fault="BACKEND_FAILED",
            last_result_code=ResultCode.BACKEND_FAILED.value,
        )
        return BrainResult(
            request_id=request_id,
            outcome=BrainOutcome.FAILED,
            code=ResultCode.BACKEND_FAILED,
            state_revision=self.state.revision,
            detail=detail,
            communication=communication,
            safety=decision,
        )

    def _map_receipt(self, receipt: HardwareReceipt) -> tuple[BrainOutcome, ResultCode]:
        if receipt.status == ReceiptStatus.COMPLETED:
            return BrainOutcome.COMPLETED, ResultCode.OK
        if receipt.status == ReceiptStatus.ACCEPTED:
            return BrainOutcome.ACCEPTED, ResultCode.OK
        if receipt.status == ReceiptStatus.UNKNOWN:
            return BrainOutcome.UNKNOWN, ResultCode.BACKEND_FAILED
        if receipt.reason == "DEADLINE_EXPIRED":
            return BrainOutcome.REJECTED, ResultCode.DEADLINE_EXPIRED
        if receipt.reason == "BACKEND_NOT_OPEN":
            return BrainOutcome.FAILED, ResultCode.BACKEND_UNAVAILABLE
        return BrainOutcome.FAILED, ResultCode.BACKEND_FAILED

    def _allocate_request_id(self) -> int:
        value = self._next_request_id
        self._next_request_id += 1
        return value

    def _allocate_command_id(self) -> int:
        value = self._next_command_id
        self._next_command_id += 1
        return value

    def _result(
        self,
        request_id: int,
        outcome: BrainOutcome,
        code: ResultCode,
        *,
        detail: str = "",
        communication: CommunicationOutput | None = None,
        receipt: HardwareReceipt | None = None,
        safety: SafetyDecision | None = None,
    ) -> BrainResult:
        self.state = replace(
            self.state,
            revision=self.state.revision + 1,
            last_result_code=code.value,
        )
        self._log("result", request_id=request_id, outcome=outcome.value, code=code.value)
        return BrainResult(
            request_id=request_id,
            outcome=outcome,
            code=code,
            state_revision=self.state.revision,
            detail=detail,
            communication=communication,
            receipt=receipt,
            safety=safety,
        )

    def _log(self, event_type: str, **fields: object) -> None:
        event = {
            "event": event_type,
            "session_id": self.state.session_id,
            "state_revision": self.state.revision,
            "time_us": self.clock_us(),
        }
        event.update(fields)
        self.event_logger.write(event)
