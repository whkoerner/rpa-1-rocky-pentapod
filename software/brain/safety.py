"""Pure deterministic safety policy for the Brain v0.2 communication slice."""

from __future__ import annotations

from csp.wire import INTENTS, WireMessage

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
        message: WireMessage,
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
        if Capability.COMMUNICATION not in state.capabilities:
            return SafetyDecision(False, ResultCode.CAPABILITY_UNAVAILABLE, revision)
        if message.intent not in INTENTS or message.arg:
            return SafetyDecision(False, ResultCode.UNSUPPORTED_INTENT, revision)

        return SafetyDecision(True, ResultCode.OK, revision)
