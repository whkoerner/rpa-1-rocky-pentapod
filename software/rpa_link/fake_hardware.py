"""Fake RPA-Link motion controller for computer-only safety testing."""

from __future__ import annotations

import argparse
import socket
import time
from typing import Any

from .messages import (
    MessageError,
    MessageType,
    Mode,
    make_message,
    monotonic_us,
    ttl_expired,
    validate_message,
)
from .udp import (
    DEFAULT_COMMAND_HOST,
    DEFAULT_COMMAND_PORT,
    DEFAULT_TELEMETRY_HOST,
    DEFAULT_TELEMETRY_PORT,
    UdpJsonReceiver,
    send_message,
)


DEFAULT_HEARTBEAT_TIMEOUT_MS = 500
DEFAULT_COMMAND_TIMEOUT_MS = 250
DEFAULT_TELEMETRY_PERIOD_MS = 100
FAKE_NODE_ID = 16
SUPERVISOR_NODE_ID = 1


class FakeHardwareController:
    """Safety state machine with no invented physical measurements."""

    def __init__(
        self,
        *,
        heartbeat_timeout_ms: int = DEFAULT_HEARTBEAT_TIMEOUT_MS,
        command_timeout_ms: int = DEFAULT_COMMAND_TIMEOUT_MS,
    ) -> None:
        self.heartbeat_timeout_us = int(heartbeat_timeout_ms) * 1000
        self.command_timeout_us = int(command_timeout_ms) * 1000
        self.mode = Mode.DISABLED
        self.estop_latched = False
        self.physical_estop_released = True
        self.fault = ""
        self.last_heartbeat_received_us: int | None = None
        self.last_command_received_us: int | None = None
        self.joint_commands: dict[int, dict[str, int]] = {}

    def heartbeat_ok(self, now_us: int) -> bool:
        if self.last_heartbeat_received_us is None:
            return False
        return now_us - self.last_heartbeat_received_us <= self.heartbeat_timeout_us

    def _safe_stop(self, reason: str) -> None:
        if self.estop_latched:
            return
        self.mode = Mode.SAFE_STOP
        self.fault = reason
        self.joint_commands.clear()

    def emergency_stop(self, reason: str = "ESTOP_ACTIVE") -> None:
        self.estop_latched = True
        self.mode = Mode.ESTOP
        self.fault = reason
        self.joint_commands.clear()

    def receive(
        self,
        message: dict[str, Any],
        *,
        received_us: int | None = None,
        queued_for_us: int = 0,
    ) -> bool:
        """Process one already-received message.

        Safety timing uses received_us from this controller's local monotonic
        clock. timestamp_us in the message is not compared against this clock.
        """

        validate_message(message)
        now_us = monotonic_us() if received_us is None else received_us

        if ttl_expired(message["ttl_ms"], queued_for_us):
            if message["type"] == MessageType.JOINT_POSITION_CMD.value:
                self._safe_stop("EXPIRED_COMMAND")
            return False

        msg_type = MessageType(message["type"])
        payload = message["payload"]

        if msg_type == MessageType.HEARTBEAT:
            self.last_heartbeat_received_us = now_us
            return True

        if msg_type == MessageType.ESTOP:
            self.emergency_stop()
            return True

        if msg_type == MessageType.ESTOP_RESET_REQUEST:
            return self._reset_estop(now_us)

        if self.estop_latched:
            return False

        if msg_type == MessageType.SET_MODE:
            return self._set_mode(payload, now_us)

        if msg_type == MessageType.JOINT_POSITION_CMD:
            return self._accept_joint_command(payload, now_us)

        if msg_type == MessageType.HELLO:
            return True

        return False

    def _set_mode(self, payload: dict[str, Any], now_us: int) -> bool:
        raw_mode = payload.get("mode")
        try:
            requested = Mode(raw_mode)
        except (TypeError, ValueError):
            self.fault = "INVALID_MODE"
            return False

        if requested == Mode.ESTOP:
            self.emergency_stop()
            return True

        if requested == Mode.DISABLED:
            self.mode = Mode.DISABLED
            self.fault = ""
            self.joint_commands.clear()
            self.last_command_received_us = None
            return True

        if requested == Mode.SAFE_STOP:
            self._safe_stop("SUPERVISOR_SAFE_STOP")
            return True

        if requested == Mode.READY:
            if not self.heartbeat_ok(now_us):
                self.fault = "HEARTBEAT_REQUIRED"
                return False
            self.mode = Mode.READY
            self.fault = ""
            self.joint_commands.clear()
            self.last_command_received_us = None
            return True

        if requested == Mode.ACTIVE:
            if self.mode != Mode.READY:
                self.fault = "READY_REQUIRED"
                return False
            if not self.heartbeat_ok(now_us):
                self._safe_stop("HEARTBEAT_TIMEOUT")
                return False
            self.mode = Mode.ACTIVE
            self.fault = ""
            self.last_command_received_us = now_us
            return True

        return False

    def _accept_joint_command(self, payload: dict[str, Any], now_us: int) -> bool:
        if self.mode != Mode.ACTIVE:
            return False

        if not self.heartbeat_ok(now_us):
            self._safe_stop("HEARTBEAT_TIMEOUT")
            return False

        joints = payload.get("joints")
        if not isinstance(joints, list) or not joints:
            self._safe_stop("INVALID_JOINT_COMMAND")
            return False

        next_commands: dict[int, dict[str, int]] = {}

        for item in joints:
            if not isinstance(item, dict):
                self._safe_stop("INVALID_JOINT_COMMAND")
                return False

            joint_id = item.get("joint_id")
            target_urad = item.get("target_urad")
            max_velocity = item.get("max_velocity_urad_s")

            if type(joint_id) is not int or not 0 <= joint_id <= 255:
                self._safe_stop("INVALID_JOINT_COMMAND")
                return False
            if type(target_urad) is not int:
                self._safe_stop("INVALID_JOINT_COMMAND")
                return False
            if type(max_velocity) is not int or max_velocity < 0:
                self._safe_stop("INVALID_JOINT_COMMAND")
                return False

            next_commands[joint_id] = {
                "target_urad": target_urad,
                "max_velocity_urad_s": max_velocity,
            }

        self.joint_commands = next_commands
        self.last_command_received_us = now_us
        return True

    def _reset_estop(self, now_us: int) -> bool:
        if not self.estop_latched:
            return True
        if not self.physical_estop_released:
            return False
        if not self.heartbeat_ok(now_us):
            return False

        self.estop_latched = False
        self.mode = Mode.DISABLED
        self.fault = ""
        self.joint_commands.clear()
        self.last_command_received_us = None
        return True

    def tick(self, now_us: int | None = None) -> None:
        """Run watchdog checks using local monotonic time."""

        now = monotonic_us() if now_us is None else now_us

        if self.mode != Mode.ACTIVE or self.estop_latched:
            return

        if not self.heartbeat_ok(now):
            self._safe_stop("HEARTBEAT_TIMEOUT")
            return

        if self.last_command_received_us is None:
            self._safe_stop("COMMAND_TIMEOUT")
            return

        if now - self.last_command_received_us > self.command_timeout_us:
            self._safe_stop("COMMAND_TIMEOUT")

    def telemetry_payload(self, now_us: int | None = None) -> dict[str, Any]:
        """Return fake telemetry without claiming a measured joint position."""

        now = monotonic_us() if now_us is None else now_us
        joints = []
        for joint_id, command in sorted(self.joint_commands.items()):
            joints.append(
                {
                    "joint_id": joint_id,
                    "commanded_urad": command["target_urad"],
                    "position_valid": False,
                }
            )

        return {
            "mode": self.mode.value,
            "estop_latched": self.estop_latched,
            "heartbeat_ok": self.heartbeat_ok(now),
            "fault": self.fault,
            "joints": joints,
        }


def run_udp_fake(
    *,
    listen_host: str,
    command_port: int,
    telemetry_host: str,
    telemetry_port: int,
    drop_heartbeat: bool,
    start_estopped: bool,
) -> None:
    controller = FakeHardwareController()
    if start_estopped:
        controller.emergency_stop("OPERATOR_TEST_ESTOP")

    telemetry_sequence = 0
    next_telemetry_us = monotonic_us()
    receiver = UdpJsonReceiver(listen_host, command_port, timeout_s=0.02)

    print(f"RPA-Link fake hardware listening on {listen_host}:{command_port}")
    print(f"Telemetry target {telemetry_host}:{telemetry_port}")
    print("No physical actuator output is produced. Press Ctrl+C to stop.")

    try:
        while True:
            receive_start_us = monotonic_us()
            try:
                message, _address = receiver.receive()
            except socket.timeout:
                message = None
            except MessageError as exc:
                print(f"Rejected message: {exc}")
                message = None

            now_us = monotonic_us()
            if message is not None:
                if drop_heartbeat and message["type"] == MessageType.HEARTBEAT.value:
                    pass
                else:
                    controller.receive(
                        message,
                        received_us=now_us,
                        queued_for_us=max(0, now_us - receive_start_us),
                    )

            controller.tick(now_us)

            if now_us >= next_telemetry_us:
                telemetry = make_message(
                    MessageType.SYSTEM_TELEMETRY,
                    source=FAKE_NODE_ID,
                    destination=SUPERVISOR_NODE_ID,
                    sequence=telemetry_sequence,
                    timestamp_us=now_us,
                    ttl_ms=500,
                    payload=controller.telemetry_payload(now_us),
                )
                send_message(telemetry, telemetry_host, telemetry_port)
                telemetry_sequence = (telemetry_sequence + 1) & 0xFFFFFFFF
                next_telemetry_us = now_us + DEFAULT_TELEMETRY_PERIOD_MS * 1000
    except KeyboardInterrupt:
        pass
    finally:
        receiver.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="RPA-Link v0.1 fake motion controller")
    parser.add_argument("--listen-host", default=DEFAULT_COMMAND_HOST)
    parser.add_argument("--command-port", type=int, default=DEFAULT_COMMAND_PORT)
    parser.add_argument("--telemetry-host", default=DEFAULT_TELEMETRY_HOST)
    parser.add_argument("--telemetry-port", type=int, default=DEFAULT_TELEMETRY_PORT)
    parser.add_argument(
        "--drop-heartbeat",
        action="store_true",
        help="ignore HEARTBEAT messages so the watchdog can be tested",
    )
    parser.add_argument(
        "--estop",
        action="store_true",
        help="start with the software E-stop latched",
    )
    args = parser.parse_args()

    run_udp_fake(
        listen_host=args.listen_host,
        command_port=args.command_port,
        telemetry_host=args.telemetry_host,
        telemetry_port=args.telemetry_port,
        drop_heartbeat=args.drop_heartbeat,
        start_estopped=args.estop,
    )


if __name__ == "__main__":
    main()
