import csv
import json
from pathlib import Path
import tempfile
import unittest

from simulation.logger import CsvRunLogger
from simulation.model import ContactState, RobotMode, SimRobot


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "robot.json"


def load_robot() -> SimRobot:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return SimRobot(config)


def set_all_contacts(robot: SimRobot) -> None:
    for limb in robot.limbs:
        limb.contact = ContactState.CONTACT


class SimulationTests(unittest.TestCase):
    def test_has_five_limbs_with_two_actuators_each(self):
        robot = load_robot()
        self.assertEqual(len(robot.limbs), 5)
        self.assertTrue(all(len(limb.actuators) == 2 for limb in robot.limbs))

    def test_out_of_range_target_trips_stop(self):
        robot = load_robot()
        self.assertTrue(robot.arm())
        max_deg = robot.limbs[0].actuators[0].config.max_deg

        accepted = robot.set_joint_target(0, 0, max_deg + 1.0)

        self.assertFalse(accepted)
        self.assertEqual(robot.mode, RobotMode.STOPPED)
        self.assertEqual(robot.fault, "JOINT_LIMIT")
        self.assertTrue(
            all(
                not actuator.enabled
                for limb in robot.limbs
                for actuator in limb.actuators
            )
        )

    def test_estop_latches_until_explicit_reset(self):
        robot = load_robot()
        robot.arm()
        robot.emergency_stop()

        self.assertEqual(robot.mode, RobotMode.STOPPED)
        self.assertFalse(robot.arm())

        robot.reset()
        self.assertEqual(robot.mode, RobotMode.IDLE)
        self.assertFalse(robot.gait_active)
        self.assertTrue(
            all(
                not actuator.enabled
                for limb in robot.limbs
                for actuator in limb.actuators
            )
        )

    def test_gait_requires_known_contacts(self):
        robot = load_robot()
        robot.arm()

        self.assertFalse(robot.start_gait())
        self.assertEqual(robot.mode, RobotMode.STOPPED)
        self.assertEqual(robot.fault, "GAIT_REQUIRES_FIVE_CONTACTS")

    def test_support_contact_loss_stops_gait(self):
        robot = load_robot()
        set_all_contacts(robot)
        robot.arm()
        self.assertTrue(robot.start_gait())

        support_limb = 1
        robot.limbs[support_limb].contact = ContactState.FREE
        robot.update(float(robot.config["fixed_step_s"]))

        self.assertEqual(robot.mode, RobotMode.STOPPED)
        self.assertEqual(robot.fault, "SUPPORT_CONTACT_LOST")

    def test_valid_existing_csp_message_does_not_move_robot(self):
        robot = load_robot()
        before = robot.snapshot()

        accepted = robot.handle_csp("C1|SOCIAL.HELLO|\n")

        self.assertTrue(accepted)
        self.assertEqual(robot.last_csp_intent, "SOCIAL.HELLO")
        self.assertEqual(robot.mode, RobotMode.IDLE)
        after = robot.snapshot()
        self.assertEqual(before[:-1], after[:-1])

    def test_invalid_csp_message_fails_closed(self):
        robot = load_robot()

        accepted = robot.handle_csp("C1|MOTION.WALK|\n")

        self.assertFalse(accepted)
        self.assertEqual(robot.mode, RobotMode.STOPPED)
        self.assertTrue(robot.fault.startswith("CSP_"))

    def test_same_fixed_step_sequence_is_deterministic(self):
        def run_sequence():
            robot = load_robot()
            set_all_contacts(robot)
            robot.arm()
            robot.start_gait()
            for _ in range(80):
                robot.update(float(robot.config["fixed_step_s"]))
            return robot.snapshot()

        self.assertEqual(run_sequence(), run_sequence())

    def test_csv_logger_writes_state(self):
        robot = load_robot()
        with tempfile.TemporaryDirectory() as tmp:
            logger = CsvRunLogger(Path(tmp))
            logger.record(robot, 0.02)
            path = logger.path
            logger.close()

            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["mode"], "IDLE")
        self.assertIn("limb_5_joint_2_target_deg", rows[0])


if __name__ == "__main__":
    unittest.main()
