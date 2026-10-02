"""Pure deterministic safety policy for the Brain v0.2 communication slice."""

from __future__ import annotations

from csp.wire import INTENTS, WireMessage
from csp.conversation import Utterance, validate_text

from .contracts import (
    Capability,
    ConnectionState,
    RequestContext,
    ResultCode,
    RobotState,
    SafetyDecision,
)


class SafetyValidator:
    def validate(
        self,
        message: WireMessage | Utterance,
        request: RequestContext,
        state: RobotState,
        now_us: int,
    ) -> SafetyDecision:
        revision = state.revision

        if now_us > request.deadline_us:
            return SafetyDecision(False, ResultCode.DEADLINE_EXPIRED, revision)
        if state.estop_latched:
            return SafetyDecision(False, ResultCode.ESTOP_LATCHED, revision)
        if state.connection_state != ConnectionState.READY:
            return SafetyDecision(False, ResultCode.BACKEND_UNAVAILABLE, revision)
        capability = Capability.TEXT_COMMUNICATION if isinstance(message, Utterance) else Capability.COMMUNICATION
        if capability not in state.capabilities:
            return SafetyDecision(False, ResultCode.CAPABILITY_UNAVAILABLE, revision)
        if isinstance(message, Utterance):
            try:
                validate_text(message.text)
            except ValueError:
                return SafetyDecision(False, ResultCode.INVALID_RESPONSE, revision)
            return SafetyDecision(True, ResultCode.OK, revision)
        if message.intent not in INTENTS or message.arg:
            return SafetyDecision(False, ResultCode.UNSUPPORTED_INTENT, revision)

        return SafetyDecision(True, ResultCode.OK, revision)
