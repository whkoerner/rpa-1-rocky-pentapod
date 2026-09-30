"""Small deterministic CSP-1 semantic wire codec."""

from dataclasses import dataclass
import re

VERSION = "C1"
MAX_MESSAGE_LENGTH = 63

INTENTS = {
    "SOCIAL.HELLO": ("Hello.", "SOCIAL.hello"),
    "RESPONSE.YES": ("Yes.", "SOCIAL.yes"),
    "RESPONSE.NO": ("No.", "SOCIAL.no"),
    "REQUEST.HELP": ("Help.", "ACTION.help"),
    "SOCIAL.THANKS": ("Thank you.", "SOCIAL.thank_you"),
    "SOCIAL.GOODBYE": ("Goodbye.", "SOCIAL.goodbye"),
}

_INTENT_RE = re.compile(r"^[A-Z]+\.[A-Z]+$")
_ARG_RE = re.compile(r"^[A-Z0-9_]*$")


class WireError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WireMessage:
    intent: str
    arg: str = ""


def encode(message: WireMessage) -> str:
    _validate_semantics(message.intent, message.arg)
    payload = f"{VERSION}|{message.intent}|{message.arg}"
    if len(payload) > MAX_MESSAGE_LENGTH:
        raise WireError("TOO_LONG", "message exceeds 63 characters")
    return payload + "\n"


def decode(raw: str) -> WireMessage:
    if not isinstance(raw, str):
        raise WireError("FORMAT", "wire input must be text")

    line = raw
    if line.endswith("\n"):
        line = line[:-1]
        if line.endswith("\r"):
            line = line[:-1]

    if len(line) > MAX_MESSAGE_LENGTH:
        raise WireError("TOO_LONG", "message exceeds 63 characters")

    parts = line.split("|")
    if len(parts) != 3:
        raise WireError("FORMAT", "message must contain exactly three fields")

    version, intent, arg = parts
    if version != VERSION:
        raise WireError("VERSION", "unsupported CSP-1 wire version")

    _validate_semantics(intent, arg)
    return WireMessage(intent=intent, arg=arg)


def canonical_text(message: WireMessage) -> str:
    _validate_semantics(message.intent, message.arg)
    return INTENTS[message.intent][0]


def chordic_token(message: WireMessage) -> str:
    _validate_semantics(message.intent, message.arg)
    return INTENTS[message.intent][1]


def _validate_semantics(intent: str, arg: str) -> None:
    if not _INTENT_RE.fullmatch(intent):
        raise WireError("INTENT", "invalid intent syntax")
    if intent not in INTENTS:
        raise WireError("INTENT", "unknown intent")
    if not _ARG_RE.fullmatch(arg):
        raise WireError("ARGUMENT", "invalid argument syntax")
    if arg:
        raise WireError("ARGUMENT", "v0.1 registered intents require an empty argument")
