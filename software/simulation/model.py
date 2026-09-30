"""Deterministic state model for the computer-only RPA-1 simulator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

from csp.wire import WireError, canonical_text, decode


class ContactState(str, Enum):
    UNKNOWN = "UNKNOWN"
    CONTACT = "CONTACT"
    FREE = "FREE"


class RobotMode(str, Enum):
    IDLE = "IDLE"
    ENABLED = "ENABLED"
    STOPPED = "STOPPED"


class JointLimitError(ValueError):
    pass


@dataclass(frozen=True)
class JointConfig:
    name: str
    min_deg: float
    max_deg: float


class SimActuator:
    """Placeholder actuator that moves toward a target at a configured simulation rate."""

    def __init__(self, config: JointConfig, speed_deg_per_s: float) -> None:
        self.config = config
        self.speed_deg_per_s = float(speed_deg_per_s)
        self.position_deg = 0.0
        self.target_deg = 0.0
        self.enabled = False

    def set_target(self, angle_deg: float) -> None:
        angle = float(angle_deg)
        if not self.config.min_deg <= angle <= self.config.max_deg:
            raise JointLimitError(
                f"{self.config.name} target {angle} outside "
                f"[{self.config.min_deg}, {self.config.max_deg}]"
            )
        self.target_deg = angle

    def update(self, dt_s: float) -> None:
        if not self.enabled:
            return

        delta = self.target_deg - self.position_deg
        max_step = self.speed_deg_per_s * dt_s
        if abs(delta) <= max_step:
            self.position_deg = self.target_deg
        elif delta:
            self.position_deg += math.copysign(max_step, delta)

    def disable(self) -> None:
        self.enabled = False

    def enable(self) -> None:
        self.enabled = True

    def hold_current_position(self) -> None:
        self.target_deg = self.position_deg


@dataclass
class Limb:
    index: int
    actuators: list[SimActuator]
    contact: ContactState = ContactState.UNKNOWN


class SimRobot:
    """Five-limb simulation state with a fail-closed safety latch."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        joint_configs = [
            JointConfig(
                name=item["name"],
                min_deg=float(item["min_deg"]),
                max_deg=float(item["max_deg"]),
            )
            for item in config["joints"]
        ]
        speed = float(config["actuator"]["sim_speed_deg_per_s"])
        self.limbs = [
            Limb(
                index=i,
                actuators=[SimActuator(joint, speed) for joint in joint_configs],
            )
            for i in range(int(config["limb_count"]))
        ]

        self.mode = RobotMode.IDLE
        self.fault = ""
        self.gait_active = False
        self.gait_limb_index = 0
        self.gait_phase = "IDLE"
        self.gait_phase_elapsed_s = 0.0
        self.last_csp_intent = ""
        self.last_csp_text = ""

    def arm(self) -> bool:
        if self.mode == RobotMode.STOPPED:
            return False
        for limb in self.limbs:
            for actuator in limb.actuators:
                actuator.enable()
        self.mode = RobotMode.ENABLED
        return True

    def emergency_stop(self, reason: str = "E_STOP") -> None:
        self.trip(reason)

    def trip(self, reason: str) -> None:
        self.gait_active = False
        self.gait_phase = "IDLE"
        self.fault = reason
        self.mode = RobotMode.STOPPED
        for limb in self.limbs:
            for actuator in limb.actuators:
                actuator.disable()

    def reset(self) -> None:
        self.gait_active = False
        self.gait_phase = "IDLE"
        self.gait_phase_elapsed_s = 0.0
        self.fault = ""
        self.mode = RobotMode.IDLE
        for limb in self.limbs:
            for actuator in limb.actuators:
                actuator.hold_current_position()
                actuator.disable()

    def set_joint_target(self, limb_index: int, joint_index: int, angle_deg: float) -> bool:
        if self.mode != RobotMode.ENABLED:
            return False
        try:
            actuator = self.limbs[limb_index].actuators[joint_index]
        except IndexError:
            self.trip("INVALID_JOINT_INDEX")
            return False

        try:
            actuator.set_target(angle_deg)
        except JointLimitError:
            self.trip("JOINT_LIMIT")
            return False
        return True

    def toggle_contact(self, limb_index: int) -> ContactState:
        try:
            limb = self.limbs[limb_index]
        except IndexError:
            self.trip("INVALID_LIMB_INDEX")
            return ContactState.UNKNOWN

        next_state = {
            ContactState.UNKNOWN: ContactState.CONTACT,
            ContactState.CONTACT: ContactState.FREE,
            ContactState.FREE: ContactState.UNKNOWN,
        }
        limb.contact = next_state[limb.contact]
        return limb.contact

    def handle_csp(self, raw: str) -> bool:
        """Validate existing CSP-1 v0.1 communication messages.

        Current CSP-1 v0.1 has no motion intents. A valid message updates
        communication state only. It never moves a joint or starts a gait.
        """
        try:
            message = decode(raw)
            text = canonical_text(message)
        except WireError as exc:
            self.trip(f"CSP_{exc.code}")
            return False

        self.last_csp_intent = message.intent
        self.last_csp_text = text
        return True

    def start_gait(self) -> bool:
        if self.mode != RobotMode.ENABLED:
            return False
        if any(limb.contact != ContactState.CONTACT for limb in self.limbs):
            self.trip("GAIT_REQUIRES_FIVE_CONTACTS")
            return False

        self.gait_active = True
        self.gait_limb_index = 0
        self.gait_phase = "SWING"
        self.gait_phase_elapsed_s = 0.0
        self._enter_swing()
        return self.mode != RobotMode.STOPPED

    def stop_gait(self) -> None:
        self.gait_active = False
        self.gait_phase = "IDLE"
        self.gait_phase_elapsed_s = 0.0

    def update(self, dt_s: float) -> None:
        if dt_s <= 0:
            return

        if self.gait_active and self.mode == RobotMode.ENABLED:
            for limb in self.limbs:
                if limb.index != self.gait_limb_index and limb.contact != ContactState.CONTACT:
                    self.trip("SUPPORT_CONTACT_LOST")
                    break

        if self.gait_active and self.mode == RobotMode.ENABLED:
            self._update_gait(dt_s)

        for limb in self.limbs:
            for actuator in limb.actuators:
                actuator.update(dt_s)

    def _update_gait(self, dt_s: float) -> None:
        self.gait_phase_elapsed_s += dt_s
        duration = float(self.config["gait"]["phase_duration_s"])

        while self.gait_active and self.gait_phase_elapsed_s >= duration:
            self.gait_phase_elapsed_s -= duration

            if self.gait_phase == "SWING":
                self.gait_phase = "SETTLE"
                self._enter_settle()
            else:
                self.limbs[self.gait_limb_index].contact = ContactState.CONTACT
                self.gait_limb_index = (self.gait_limb_index + 1) % len(self.limbs)
                self.gait_phase = "SWING"
                self._enter_swing()

    def _enter_swing(self) -> None:
        limb = self.limbs[self.gait_limb_index]
        limb.contact = ContactState.FREE
        ok_1 = self.set_joint_target(
            limb.index, 0, float(self.config["gait"]["swing_joint_1_deg"])
        )
        ok_2 = self.set_joint_target(
            limb.index, 1, float(self.config["gait"]["swing_joint_2_deg"])
        )
        if not (ok_1 and ok_2) and self.mode != RobotMode.STOPPED:
            self.trip("GAIT_TARGET_REJECTED")

    def _enter_settle(self) -> None:
        limb = self.limbs[self.gait_limb_index]
        ok_1 = self.set_joint_target(limb.index, 0, 0.0)
        ok_2 = self.set_joint_target(limb.index, 1, 0.0)
        if not (ok_1 and ok_2) and self.mode != RobotMode.STOPPED:
            self.trip("GAIT_TARGET_REJECTED")

    def snapshot(self) -> tuple[Any, ...]:
        values: list[Any] = [
            self.mode.value,
            self.fault,
            self.gait_active,
            self.gait_limb_index,
            self.gait_phase,
            round(self.gait_phase_elapsed_s, 6),
        ]
        for limb in self.limbs:
            values.append(limb.contact.value)
            for actuator in limb.actuators:
                values.extend(
                    [
                        round(actuator.position_deg, 6),
                        round(actuator.target_deg, 6),
                        actuator.enabled,
                    ]
                )
        return tuple(values)
