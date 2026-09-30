"""Small local/offline UDP adapter for RPA-Link JSON messages."""

from __future__ import annotations

import socket
from typing import Any

from .messages import decode_message, encode_message


DEFAULT_COMMAND_HOST = "127.0.0.1"
DEFAULT_COMMAND_PORT = 7401
DEFAULT_TELEMETRY_HOST = "127.0.0.1"
DEFAULT_TELEMETRY_PORT = 7402
MAX_DATAGRAM_BYTES = 65507


class UdpJsonReceiver:
    """Receive one complete RPA-Link JSON message per UDP datagram."""

    def __init__(
        self,
        host: str = DEFAULT_COMMAND_HOST,
        port: int = DEFAULT_COMMAND_PORT,
        timeout_s: float | None = None,
    ) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))
        self.socket.settimeout(timeout_s)

    def receive(self) -> tuple[dict[str, Any], tuple[str, int]]:
        raw, address = self.socket.recvfrom(MAX_DATAGRAM_BYTES)
        return decode_message(raw), address

    def close(self) -> None:
        self.socket.close()

    def __enter__(self) -> "UdpJsonReceiver":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def send_message(
    message: dict[str, Any],
    host: str = DEFAULT_TELEMETRY_HOST,
    port: int = DEFAULT_TELEMETRY_PORT,
) -> None:
    """Send one complete validated JSON message in one UDP datagram."""

    raw = encode_message(message)
    if len(raw) > MAX_DATAGRAM_BYTES:
        raise ValueError("RPA-Link JSON message is too large for one UDP datagram")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(raw, (host, port))
