"""CSV logging for the RPA-1 computer-only simulator."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import TextIO

from .model import SimRobot


class CsvRunLogger:
    def __init__(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = output_dir / f"run_{stamp}.csv"
        self._file: TextIO = self.path.open("w", newline="", encoding="utf-8")

        fieldnames = [
            "sim_time_s",
            "mode",
            "fault",
            "gait_active",
            "gait_limb",
            "gait_phase",
            "last_csp_intent",
        ]
        for limb_index in range(1, 6):
            fieldnames.extend(
                [
                    f"limb_{limb_index}_contact",
                    f"limb_{limb_index}_joint_1_position_deg",
                    f"limb_{limb_index}_joint_1_target_deg",
                    f"limb_{limb_index}_joint_2_position_deg",
                    f"limb_{limb_index}_joint_2_target_deg",
                ]
            )

        self._writer = csv.DictWriter(self._file, fieldnames=fieldnames)
        self._writer.writeheader()

    def record(self, robot: SimRobot, sim_time_s: float) -> None:
        row: dict[str, object] = {
            "sim_time_s": f"{sim_time_s:.3f}",
            "mode": robot.mode.value,
            "fault": robot.fault,
            "gait_active": robot.gait_active,
            "gait_limb": robot.gait_limb_index + 1,
            "gait_phase": robot.gait_phase,
            "last_csp_intent": robot.last_csp_intent,
        }
        for limb in robot.limbs:
            n = limb.index + 1
            row[f"limb_{n}_contact"] = limb.contact.value
            row[f"limb_{n}_joint_1_position_deg"] = f"{limb.actuators[0].position_deg:.3f}"
            row[f"limb_{n}_joint_1_target_deg"] = f"{limb.actuators[0].target_deg:.3f}"
            row[f"limb_{n}_joint_2_position_deg"] = f"{limb.actuators[1].position_deg:.3f}"
            row[f"limb_{n}_joint_2_target_deg"] = f"{limb.actuators[1].target_deg:.3f}"

        self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        self._file.close()
