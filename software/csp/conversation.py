"""CT1: reversible UTF-8 musical text transport, separate from CSP-1 intents."""

from dataclasses import dataclass
import unicodedata
import zlib

MAX_TEXT_BYTES = 384
TEXT_VERSION = "rocky-text-v1"


@dataclass(frozen=True)
class Utterance:
    text: str


def validate_text(text: object) -> str:
    if type(text) is not str or not text.strip():
        raise ValueError("text must be a nonempty string")
    if any(unicodedata.category(c).startswith("C") for c in text):
        raise ValueError("control characters are not allowed")
    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError(f"text exceeds {MAX_TEXT_BYTES} UTF-8 bytes")
    return text


def encode_text(text: str) -> tuple[tuple[int, ...], ...]:
    """Four base-five digits per byte; voice order is significant."""
    payload = validate_text(text).encode("utf-8")
    body = b"CT1" + len(payload).to_bytes(2, "big") + payload
    packet = body + zlib.crc32(body).to_bytes(4, "big")
    return tuple(tuple((b // (5 ** n)) % 5 for n in (3, 2, 1, 0)) for b in packet)


def decode_text(symbols: tuple[tuple[int, ...], ...]) -> str:
    if not 10 <= len(symbols) <= MAX_TEXT_BYTES + 9:
        raise ValueError("invalid CT1 length")
    packet = bytearray()
    for chord in symbols:
        if len(chord) != 4 or any(type(d) is not int or not 0 <= d < 5 for d in chord):
            raise ValueError("invalid CT1 digit")
        value = sum(d * 5 ** n for d, n in zip(chord, (3, 2, 1, 0)))
        if value > 255:
            raise ValueError("invalid CT1 byte")
        packet.append(value)
    if packet[:3] != b"CT1" or int.from_bytes(packet[3:5], "big") != len(packet) - 9:
        raise ValueError("invalid CT1 header")
    if zlib.crc32(packet[:-4]) != int.from_bytes(packet[-4:], "big"):
        raise ValueError("CT1 checksum mismatch")
    return validate_text(bytes(packet[5:-4]).decode("utf-8"))
