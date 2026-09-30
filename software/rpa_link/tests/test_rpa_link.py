import unittest

from rpa_link.fake_hardware import FakeHardwareController
from rpa_link.messages import (
    MessageError,
    MessageType,
    Mode,
    decode_message,
    encode_message,
    make_message,
)


SUPERVISOR = 1
CONTROLLER = 16


def message(
    msg_type: MessageType,
    sequence: int,
    *,
    payload=None,
    ttl_ms=500,
    timestamp_us=1,
):
    return make_message(
        msg_type,
        source=SUPERVISOR,
        destination=CONTROLLER,
        sequence=sequence,
        timestamp_us=timestamp_us,
        ttl_ms=ttl_ms,
        payload={} if payload is None else payload,
    )


def activate(controller: FakeHardwareController, start_us: int = 1_000_000) -> None:
    controller.receive(
        message(MessageType.HEARTBEAT, 1),
        received_us=start_us,
    )
    accepted = controller.receive(
        message(MessageType.SET_MODE, 2, payload={"mode": "READY"}),
        received_us=start_us,
    )
    if not accepted:
        raise AssertionError("test setup could not enter READY")
    accepted = controller.receive(
        message(MessageType.SET_MODE, 3, payload={"mode": "ACTIVE"}),
        received_us=start_us,
    )
    if not accepted:
        raise AssertionError("test setup could not enter ACTIVE")


class MessageTests(unittest.TestCase):
    def test_json_round_trip_preserves_integer_fields(self):
        original = message(
            MessageType.JOINT_POSITION_CMD,
            42,
            payload={
                "joints": [
                    {
                        "joint_id": 0,
                        "target_urad": 500000,
                        "max_velocity_urad_s": 300000,
                    }
                ]
            },
            ttl_ms=250,
            timestamp_us=91822000,
        )

        decoded = decode_message(encode_message(original))

        self.assertEqual(decoded, original)
        self.assertIs(type(decoded["sequence"]), int)
        self.assertIs(type(decoded["timestamp_us"]), int)

    def test_unsupported_version_fails_closed(self):
        raw = message(MessageType.HEARTBEAT, 1)
        raw["version"] = 99

        with self.assertRaises(MessageError):
            encode_message(raw)


class FakeHardwareTests(unittest.TestCase):
    def test_startup_is_disabled(self):
        controller = FakeHardwareController()
        self.assertEqual(controller.mode, Mode.DISABLED)
        self.assertFalse(controller.estop_latched)

    def test_active_requires_recent_heartbeat(self):
        controller = FakeHardwareController()

        self.assertFalse(
            controller.receive(
                message(MessageType.SET_MODE, 1, payload={"mode": "READY"}),
                received_us=1_000_000,
            )
        )
        self.assertEqual(controller.mode, Mode.DISABLED)

    def test_heartbeat_timeout_enters_safe_stop(self):
        controller = FakeHardwareController(heartbeat_timeout_ms=500)
        activate(controller, 1_000_000)

        controller.tick(1_500_001)

        self.assertEqual(controller.mode, Mode.SAFE_STOP)
        self.assertEqual(controller.fault, "HEARTBEAT_TIMEOUT")

    def test_command_timeout_enters_safe_stop(self):
        controller = FakeHardwareController(
            heartbeat_timeout_ms=1000,
            command_timeout_ms=250,
        )
        activate(controller, 1_000_000)

        controller.receive(
            message(MessageType.HEARTBEAT, 4),
            received_us=1_200_000,
        )
        controller.tick(1_250_001)

        self.assertEqual(controller.mode, Mode.SAFE_STOP)
        self.assertEqual(controller.fault, "COMMAND_TIMEOUT")

    def test_stale_queued_joint_command_is_rejected(self):
        controller = FakeHardwareController()
        activate(controller, 1_000_000)

        accepted = controller.receive(
            message(
                MessageType.JOINT_POSITION_CMD,
                4,
                ttl_ms=250,
                payload={
                    "joints": [
                        {
                            "joint_id": 0,
                            "target_urad": 500000,
                            "max_velocity_urad_s": 300000,
                        }
                    ]
                },
            ),
            received_us=1_010_000,
            queued_for_us=250_001,
        )

        self.assertFalse(accepted)
        self.assertEqual(controller.mode, Mode.SAFE_STOP)
        self.assertEqual(controller.joint_commands, {})

    def test_estop_latches_and_blocks_motion(self):
        controller = FakeHardwareController()
        activate(controller, 1_000_000)

        controller.receive(
            message(MessageType.ESTOP, 4),
            received_us=1_010_000,
        )

        accepted = controller.receive(
            message(
                MessageType.JOINT_POSITION_CMD,
                5,
                payload={
                    "joints": [
                        {
                            "joint_id": 0,
                            "target_urad": 100000,
                            "max_velocity_urad_s": 100000,
                        }
                    ]
                },
            ),
            received_us=1_020_000,
        )

        self.assertFalse(accepted)
        self.assertTrue(controller.estop_latched)
        self.assertEqual(controller.mode, Mode.ESTOP)
        self.assertEqual(controller.joint_commands, {})

    def test_estop_reset_returns_to_disabled_not_active(self):
        controller = FakeHardwareController()
        activate(controller, 1_000_000)
        controller.receive(
            message(MessageType.ESTOP, 4),
            received_us=1_010_000,
        )
        controller.receive(
            message(MessageType.HEARTBEAT, 5),
            received_us=1_020_000,
        )

        reset = controller.receive(
            message(MessageType.ESTOP_RESET_REQUEST, 6),
            received_us=1_020_000,
        )

        self.assertTrue(reset)
        self.assertFalse(controller.estop_latched)
        self.assertEqual(controller.mode, Mode.DISABLED)

    def test_fake_telemetry_does_not_invent_position(self):
        controller = FakeHardwareController()
        activate(controller, 1_000_000)
        accepted = controller.receive(
            message(
                MessageType.JOINT_POSITION_CMD,
                4,
                payload={
                    "joints": [
                        {
                            "joint_id": 7,
                            "target_urad": 123456,
                            "max_velocity_urad_s": 100000,
                        }
                    ]
                },
            ),
            received_us=1_010_000,
        )

        self.assertTrue(accepted)
        telemetry = controller.telemetry_payload(1_010_000)

        self.assertEqual(telemetry["joints"][0]["commanded_urad"], 123456)
        self.assertFalse(telemetry["joints"][0]["position_valid"])
        self.assertNotIn("position_urad", telemetry["joints"][0])


if __name__ == "__main__":
    unittest.main()
