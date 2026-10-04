"""Immutable Brain v0.2 contracts frozen by the architecture review."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from csp.wire import WireMessage
from csp.conversation import Utterance
from csp.learning import Phrase
from rpa_link.messages import Mode


class ConnectionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    READY = "READY"
    FAULT = "FAULT"


class Capability(str, Enum):
    COMMUNICATION = "COMMUNICATION"
    TEXT_COMMUNICATION = "TEXT_COMMUNICATION"
    LOCAL_STOP = "LOCAL_STOP"


class RequestOrigin(str, Enum):
    PROVIDER = "provider"
    OPERATOR = "operator"


class ReceiptStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"
    COMPLETED = "COMPLETED"


class EvidenceKind(str, Enum):
    SIMULATED = "simulated"
    DEVICE_REPORT = "device_report"
    NONE = "none"


class BrainOutcome(str, Enum):
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"


class ResultCode(str, Enum):
    OK = "OK"
    NO_MATCH = "NO_MATCH"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    UNSUPPORTED_INTENT = "UNSUPPORTED_INTENT"
    PROVIDER_FAILED = "PROVIDER_FAILED"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    BUSY = "BUSY"
    DEADLINE_EXPIRED = "DEADLINE_EXPIRED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    BACKEND_FAILED = "BACKEND_FAILED"
    ESTOP_LATCHED = "ESTOP_LATCHED"
    STALE_FEEDBACK = "STALE_FEEDBACK"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True)
class BrainConfig:
    max_input_bytes: int = 1024
    max_provider_response_bytes: int = 512
    provider_timeout_ms: int = 500
    operation_timeout_ms: int = 1000

    def __post_init__(self) -> None:
        for name in (
            "max_input_bytes",
            "max_provider_response_bytes",
            "provider_timeout_ms",
            "operation_timeout_ms",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class AIContext:
    schema_version: str
    allowed_intents: tuple[str, ...]
    backend_id: str
    connection_state: str
    host_motion_mode: str
    estop_latched: bool


@dataclass(frozen=True)
class RequestContext:
    session_id: str
    request_id: int
    origin: RequestOrigin
    received_us: int
    deadline_us: int


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    code: ResultCode
    state_revision: int
    detail: str = ""


@dataclass(frozen=True)
class CommunicationOutput:
    message: WireMessage
    csp_line: str
    canonical_text: str
    chordic_token: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class ConversationOutput:
    message: Utterance
    canonical_text: str
    symbols: tuple[tuple[int, ...], ...]
    phrase: Phrase | None = None


@dataclass(frozen=True)
class HardwareCommand:
    command_id: int
    session_id: str
    request_id: int
    deadline_us: int
    communication: CommunicationOutput | ConversationOutput


@dataclass(frozen=True)
class HardwareReceipt:
    command_id: int
    session_id: str
    backend_id: str
    status: ReceiptStatus
    reason: str
    evidence_kind: EvidenceKind
    received_us: int


@dataclass(frozen=True)
class Observation:
    name: str
    value: Any
    unit: str
    source: str
    valid: bool
    received_us: int
    simulated: bool


@dataclass(frozen=True)
class HardwareStatus:
    backend_id: str
    capabilities: frozenset[Capability]
    connection_state: ConnectionState
    native_mode: str
    observations: tuple[Observation, ...] = ()


class HardwareEventKind(str, Enum):
    STATUS = "STATUS"
    RECEIPT = "RECEIPT"
    FAULT = "FAULT"


@dataclass(frozen=True)
class HardwareEvent:
    kind: HardwareEventKind
    received_us: int
    status: HardwareStatus | None = None
    receipt: HardwareReceipt | None = None
    reason: str = ""


@dataclass(frozen=True)
class RobotState:
    session_id: str
    revision: int = 0
    backend_id: str = ""
    connection_state: ConnectionState = ConnectionState.DISCONNECTED
    capabilities: frozenset[Capability] = frozenset()
    native_mode: str = ""
    observations: tuple[Observation, ...] = ()
    host_motion_mode: Mode = Mode.DISABLED
    estop_latched: bool = False
    latest_fault: str = ""
    last_communication: CommunicationOutput | ConversationOutput | None = None
    last_result_code: str = ""
    pending_command_id: int | None = None


@dataclass(frozen=True)
class BrainResult:
    request_id: int
    outcome: BrainOutcome
    code: ResultCode
    state_revision: int
    detail: str = ""
    communication: CommunicationOutput | ConversationOutput | None = None
    receipt: HardwareReceipt | None = None
    safety: SafetyDecision | None = None
