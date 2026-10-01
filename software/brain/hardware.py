"""Hardware boundary and headless simulator adapter for Brain v0.2."""

from __future__ import annotations

import json
from importlib import resources
from typing import Callable, Protocol

from rpa_link.messages import monotonic_us
from simulation.model import SimRobot

from .contracts import (
    Capability,
    ConnectionState,
    EvidenceKind,
    HardwareCommand,
    HardwareEvent,
    HardwareReceipt,
    HardwareStatus,
    ReceiptStatus,
)


class HardwareInterface(Protocol):
    def open(self) -> HardwareStatus:
        ...

    def dispatch(self, command: HardwareCommand) -> HardwareReceipt:
        ...

    def poll(self) -> tuple[HardwareEvent, ...]:
        ...

    def stop(self, reason: str, *, emergency: bool) -> HardwareReceipt:
        ...

    def close(self) -> None:
        ...


class SimulatorHardware:
    """Adapter over the existing SimRobot; communication only, no motion authority."""

    backend_id = "simulator"

    def __init__(self, *, clock_us: Callable[[], int] = monotonic_us) -> None:
        self._clock_us = clock_us
        self._robot: SimRobot | None = None
        self._open = False
        self._last_command_id = 0
        self._session_id = ""

    def _new_robot(self) -> SimRobot:
        config_text = (
            resources.files("simulation")
            .joinpath("config", "robot.json")
            .read_text(encoding="utf-8")
        )
        return SimRobot(json.loads(config_text))

    def open(self) -> HardwareStatus:
        self._robot = self._new_robot()
        self._open = True
        return self.status()

    def status(self) -> HardwareStatus:
        native_mode = self._robot.mode.value if self._robot is not None else "CLOSED"
        return HardwareStatus(
            backend_id=self.backend_id,
            capabilities=frozenset({Capability.COMMUNICATION, Capability.LOCAL_STOP}),
            connection_state=(
                ConnectionState.READY if self._open else ConnectionState.DISCONNECTED
            ),
            native_mode=native_mode,
        )

    def dispatch(self, command: HardwareCommand) -> HardwareReceipt:
        now = self._clock_us()
        if not self._open or self._robot is None:
            return self._receipt(
                command,
                ReceiptStatus.REJECTED,
                "BACKEND_NOT_OPEN",
                EvidenceKind.NONE,
                now,
            )
        if now > command.deadline_us:
            return self._receipt(
                command,
                ReceiptStatus.REJECTED,
                "DEADLINE_EXPIRED",
                EvidenceKind.NONE,
                now,
            )

        before = self._robot.snapshot()
        accepted = self._robot.handle_csp(command.communication.csp_line)
        after = self._robot.snapshot()
        if not accepted:
            return self._receipt(
                command,
                ReceiptStatus.REJECTED,
                self._robot.fault or "SIMULATOR_REJECTED",
                EvidenceKind.SIMULATED,
                now,
            )
        if before != after:
            self._robot.trip("BRAIN_COMMUNICATION_CHANGED_MOTION_STATE")
            return self._receipt(
                command,
                ReceiptStatus.REJECTED,
                "SIMULATOR_MOTION_STATE_CHANGED",
                EvidenceKind.SIMULATED,
                now,
            )

        self._last_command_id = command.command_id
        self._session_id = command.session_id
        return self._receipt(
            command,
            ReceiptStatus.COMPLETED,
            "SIMULATED_COMMUNICATION_COMPLETED",
            EvidenceKind.SIMULATED,
            now,
        )

    def poll(self) -> tuple[HardwareEvent, ...]:
        return ()

    def stop(self, reason: str, *, emergency: bool) -> HardwareReceipt:
        now = self._clock_us()
        if self._robot is not None:
            if emergency:
                self._robot.emergency_stop(reason)
            else:
                self._robot.trip(reason)
        return HardwareReceipt(
            command_id=self._last_command_id,
            session_id=self._session_id,
            backend_id=self.backend_id,
            status=ReceiptStatus.COMPLETED if self._robot is not None else ReceiptStatus.UNKNOWN,
            reason=reason,
            evidence_kind=(
                EvidenceKind.SIMULATED if self._robot is not None else EvidenceKind.NONE
            ),
            received_us=now,
        )

    def close(self) -> None:
        self._open = False

    def _receipt(
        self,
        command: HardwareCommand,
        status: ReceiptStatus,
        reason: str,
        evidence_kind: EvidenceKind,
        now_us: int,
    ) -> HardwareReceipt:
        return HardwareReceipt(
            command_id=command.command_id,
            session_id=command.session_id,
            backend_id=self.backend_id,
            status=status,
            reason=reason,
            evidence_kind=evidence_kind,
            received_us=now_us,
        )
