"""RPA-Link v0.1 message construction and validation."""

from __future__ import annotations

import json
import time
from enum import Enum
from typing import Any


PROTOCOL_NAME = "RPA-LINK"
PROTOCOL_VERSION = 1
BROADCAST_NODE_ID = 0
MAX_SEQUENCE = 0xFFFFFFFF
MAX_TTL_MS = 0xFFFF


class MessageError(ValueError):
    """Raised when an RPA-Link message is malformed or unsupported."""


class MessageType(str, Enum):
    HELLO = "HELLO"
    HEARTBEAT = "HEARTBEAT"
    SET_MODE = "SET_MODE"
    JOINT_POSITION_CMD = "JOINT_POSITION_CMD"
    ESTOP = "ESTOP"
    ESTOP_RESET_REQUEST = "ESTOP_RESET_REQUEST"
    JOINT_TELEMETRY = "JOINT_TELEMETRY"
    SYSTEM_TELEMETRY = "SYSTEM_TELEMETRY"
    FAULT = "FAULT"
    ACK = "ACK"


class Mode(str, Enum):
    DISABLED = "DISABLED"
    READY = "READY"
    ACTIVE = "ACTIVE"
    SAFE_STOP = "SAFE_STOP"
    ESTOP = "ESTOP"


REQUIRED_FIELDS = {
    "protocol",
    "version",
    "type",
    "source",
    "destination",
    "sequence",
    "timestamp_us",
    "ttl_ms",
    "payload",
}


def monotonic_us() -> int:
    """Return local monotonic time in microseconds."""

    return time.monotonic_ns() // 1000


def _require_plain_int(name: str, value: Any, minimum: int, maximum: int | None = None) -> None:
    if type(value) is not int:
        raise MessageError(f"{name} must be an integer")
    if value < minimum:
        raise MessageError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise MessageError(f"{name} must be <= {maximum}")


def validate_message(message: dict[str, Any]) -> None:
    """Validate the common RPA-Link envelope.

    Message-specific payload validation belongs to the receiver that understands
    that message type.
    """

    if not isinstance(message, dict):
        raise MessageError("message must be a JSON object")

    missing = REQUIRED_FIELDS - set(message)
    if missing:
        raise MessageError("missing fields: " + ", ".join(sorted(missing)))

    extra = set(message) - REQUIRED_FIELDS
    if extra:
        raise MessageError("unexpected fields: " + ", ".join(sorted(extra)))

    if message["protocol"] != PROTOCOL_NAME:
        raise MessageError("unsupported protocol")

    if message["version"] != PROTOCOL_VERSION:
        raise MessageError("unsupported protocol version")

    try:
        MessageType(message["type"])
    except (TypeError, ValueError) as exc:
        raise MessageError("unknown message type") from exc

    _require_plain_int("source", message["source"], 0, 255)
    _require_plain_int("destination", message["destination"], 0, 255)
    _require_plain_int("sequence", message["sequence"], 0, MAX_SEQUENCE)
    _require_plain_int("timestamp_us", message["timestamp_us"], 0)
    _require_plain_int("ttl_ms", message["ttl_ms"], 1, MAX_TTL_MS)

    if not isinstance(message["payload"], dict):
        raise MessageError("payload must be a JSON object")


def make_message(
    msg_type: MessageType | str,
    *,
    source: int,
    destination: int,
    sequence: int,
    payload: dict[str, Any] | None = None,
    ttl_ms: int = 500,
    timestamp_us: int | None = None,
) -> dict[str, Any]:
    """Build and validate one RPA-Link message."""

    if isinstance(msg_type, MessageType):
        msg_type = msg_type.value

    message = {
        "protocol": PROTOCOL_NAME,
        "version": PROTOCOL_VERSION,
        "type": msg_type,
        "source": source,
        "destination": destination,
        "sequence": sequence,
        "timestamp_us": monotonic_us() if timestamp_us is None else timestamp_us,
        "ttl_ms": ttl_ms,
        "payload": {} if payload is None else payload,
    }
    validate_message(message)
    return message


def encode_message(message: dict[str, Any]) -> bytes:
    """Validate and encode one message as compact UTF-8 JSON."""

    validate_message(message)
    return json.dumps(
        message,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
    ).encode("utf-8")


def decode_message(raw: bytes | str) -> dict[str, Any]:
    """Decode UTF-8 JSON and validate the common envelope."""

    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MessageError("message is not valid UTF-8") from exc
    elif isinstance(raw, str):
        text = raw
    else:
        raise MessageError("message must be bytes or text")

    try:
        message = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MessageError("message is not valid JSON") from exc

    validate_message(message)
    return message


def ttl_expired(ttl_ms: int, queued_for_us: int) -> bool:
    """Return True when local queue time exceeded the sender's TTL.

    queued_for_us is measured locally. Sender and receiver clocks do not need
    to be synchronized.
    """

    _require_plain_int("ttl_ms", ttl_ms, 1, MAX_TTL_MS)
    _require_plain_int("queued_for_us", queued_for_us, 0)
    return queued_for_us > ttl_ms * 1000
