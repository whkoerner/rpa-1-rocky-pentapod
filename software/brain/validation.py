"""Strict semantic candidate validation using the existing CSP-1 wire codec."""

from __future__ import annotations

from csp.wire import WireError, WireMessage, decode, encode

from .contracts import ResultCode


class CandidateValidationError(ValueError):
    def __init__(self, code: ResultCode, detail: str, *, wire_code: str = "") -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.wire_code = wire_code


def validate_candidate(candidate: object) -> WireMessage:
    if type(candidate) is not dict:
        raise CandidateValidationError(
            ResultCode.INVALID_RESPONSE,
            "provider response must be a plain object",
        )

    expected = {"intent", "arg"}
    if set(candidate) != expected:
        raise CandidateValidationError(
            ResultCode.INVALID_RESPONSE,
            "provider response must contain exactly intent and arg",
        )

    intent = candidate["intent"]
    arg = candidate["arg"]
    if type(intent) is not str or type(arg) is not str:
        raise CandidateValidationError(
            ResultCode.INVALID_RESPONSE,
            "intent and arg must both be plain strings",
        )

    message = WireMessage(intent=intent, arg=arg)
    try:
        return decode(encode(message))
    except WireError as exc:
        code = (
            ResultCode.UNSUPPORTED_INTENT
            if exc.code == "INTENT"
            else ResultCode.INVALID_RESPONSE
        )
        raise CandidateValidationError(
            code,
            str(exc),
            wire_code=exc.code,
        ) from exc
