import tempfile
import unittest
from pathlib import Path

from brain.ai import DummyAIProvider
from brain.contracts import (
    BrainConfig,
    BrainOutcome,
    Capability,
    ConnectionState,
    EvidenceKind,
    HardwareReceipt,
    HardwareStatus,
    ReceiptStatus,
    ResultCode,
)
from brain.controller import BrainController, JsonlEventLogger
from brain.hardware import SimulatorHardware
from brain.validation import CandidateValidationError, validate_candidate
from rpa_link.messages import Mode


class SequenceClock:
    def __init__(self, start=1_000_000, step=100):
        self.value = start
        self.step = step

    def __call__(self):
        value = self.value
        self.value += self.step
        return value


class StaticProvider:
    def __init__(self, candidate):
        self.candidate = candidate
        self.calls = 0

    def propose(self, text, context):
        self.calls += 1
        return self.candidate


class SpyHardware:
    def __init__(self, clock):
        self.clock = clock
        self.dispatch_count = 0
        self.stop_count = 0
        self.last_command = None

    def open(self):
        return HardwareStatus(
            backend_id="spy",
            capabilities=frozenset({Capability.COMMUNICATION, Capability.LOCAL_STOP}),
            connection_state=ConnectionState.READY,
            native_mode="IDLE",
        )

    def dispatch(self, command):
        self.dispatch_count += 1
        self.last_command = command
        return HardwareReceipt(
            command_id=command.command_id,
            session_id=command.session_id,
            backend_id="spy",
            status=ReceiptStatus.COMPLETED,
            reason="OK",
            evidence_kind=EvidenceKind.SIMULATED,
            received_us=self.clock(),
        )

    def poll(self):
        return ()

    def stop(self, reason, *, emergency):
        self.stop_count += 1
        return HardwareReceipt(
            command_id=0,
            session_id="",
            backend_id="spy",
            status=ReceiptStatus.COMPLETED,
            reason=reason,
            evidence_kind=EvidenceKind.SIMULATED,
            received_us=self.clock(),
        )

    def close(self):
        pass


class BrainValidationTests(unittest.TestCase):
    def test_dummy_provider_maps_all_six_registered_intents(self):
        provider = DummyAIProvider()
        samples = {
            "hello": "SOCIAL.HELLO",
            "yes": "RESPONSE.YES",
            "no": "RESPONSE.NO",
            "help": "REQUEST.HELP",
            "thank you": "SOCIAL.THANKS",
            "goodbye": "SOCIAL.GOODBYE",
        }
        for text, expected in samples.items():
            candidate = provider.propose(text, None)
            message = validate_candidate(candidate)
            self.assertEqual(message.intent, expected)
            self.assertEqual(message.arg, "")

    def test_extra_provider_fields_fail_closed(self):
        with self.assertRaises(CandidateValidationError) as ctx:
            validate_candidate({"intent": "SOCIAL.HELLO", "arg": "", "pin": 13})
        self.assertEqual(ctx.exception.code, ResultCode.INVALID_RESPONSE)

    def test_nonempty_argument_fails_closed(self):
        with self.assertRaises(CandidateValidationError) as ctx:
            validate_candidate({"intent": "SOCIAL.HELLO", "arg": "MOVE"})
        self.assertEqual(ctx.exception.code, ResultCode.INVALID_RESPONSE)


class BrainControllerTests(unittest.TestCase):
    def test_boot_is_ready_but_motion_disabled(self):
        clock = SequenceClock()
        controller = BrainController(
            provider=DummyAIProvider(),
            hardware=SimulatorHardware(clock_us=clock),
            clock_us=clock,
            session_id="test-session",
        )
        state = controller.boot()
        self.assertEqual(state.connection_state, ConnectionState.READY)
        self.assertEqual(state.host_motion_mode, Mode.DISABLED)
        self.assertFalse(state.estop_latched)
        self.assertEqual(
            state.capabilities,
            frozenset({Capability.COMMUNICATION, Capability.LOCAL_STOP}),
        )
        controller.close()

    def test_hello_completes_in_simulation_without_motion_change(self):
        clock = SequenceClock()
        hardware = SimulatorHardware(clock_us=clock)
        controller = BrainController(
            provider=DummyAIProvider(),
            hardware=hardware,
            clock_us=clock,
            session_id="test-session",
        )
        controller.boot()
        before = hardware._robot.snapshot()

        result = controller.submit_text("hello")

        after = hardware._robot.snapshot()
        self.assertEqual(before, after)
        self.assertEqual(result.outcome, BrainOutcome.COMPLETED)
        self.assertEqual(result.code, ResultCode.OK)
        self.assertTrue(result.safety.allowed)
        self.assertEqual(result.receipt.evidence_kind, EvidenceKind.SIMULATED)
        self.assertEqual(hardware._robot.last_csp_intent, "SOCIAL.HELLO")
        controller.close()

    def test_unknown_text_never_dispatches(self):
        clock = SequenceClock()
        hardware = SpyHardware(clock)
        controller = BrainController(
            provider=DummyAIProvider(),
            hardware=hardware,
            clock_us=clock,
            session_id="test-session",
        )
        controller.boot()
        result = controller.submit_text("walk forward")
        self.assertEqual(result.code, ResultCode.NO_MATCH)
        self.assertEqual(hardware.dispatch_count, 0)
        controller.close()

    def test_estop_blocks_dispatch_and_does_not_call_provider(self):
        clock = SequenceClock()
        provider = StaticProvider({"intent": "SOCIAL.HELLO", "arg": ""})
        hardware = SpyHardware(clock)
        controller = BrainController(
            provider=provider,
            hardware=hardware,
            clock_us=clock,
            session_id="test-session",
        )
        controller.boot()
        controller.emergency_stop("TEST_ESTOP")
        calls_before = provider.calls

        result = controller.submit_text("hello")

        self.assertEqual(result.code, ResultCode.ESTOP_LATCHED)
        self.assertEqual(hardware.dispatch_count, 0)
        self.assertEqual(provider.calls, calls_before)
        controller.close()

    def test_estop_reset_returns_to_disabled_without_starting_task(self):
        clock = SequenceClock()
        provider = StaticProvider({"intent": "SOCIAL.HELLO", "arg": ""})
        hardware = SimulatorHardware(clock_us=clock)
        controller = BrainController(
            provider=provider,
            hardware=hardware,
            clock_us=clock,
            session_id="test-session",
        )
        controller.boot()
        controller.emergency_stop("TEST_ESTOP")

        self.assertTrue(controller.reset_stop())
        self.assertFalse(controller.state.estop_latched)
        self.assertEqual(controller.state.host_motion_mode, Mode.DISABLED)
        self.assertIsNone(controller.state.pending_command_id)
        self.assertEqual(provider.calls, 0)
        controller.close()

    def test_safety_is_rechecked_before_dispatch(self):
        clock = SequenceClock()
        hardware = SpyHardware(clock)

        class FlipSafety:
            def __init__(self):
                self.calls = 0

            def validate(self, message, request, state, now_us):
                from brain.contracts import SafetyDecision
                self.calls += 1
                if self.calls == 1:
                    return SafetyDecision(True, ResultCode.OK, state.revision)
                return SafetyDecision(False, ResultCode.ESTOP_LATCHED, state.revision)

        safety = FlipSafety()
        controller = BrainController(
            provider=DummyAIProvider(),
            hardware=hardware,
            safety=safety,
            clock_us=clock,
            session_id="test-session",
        )
        controller.boot()
        result = controller.submit_text("hello")
        self.assertEqual(safety.calls, 2)
        self.assertEqual(result.code, ResultCode.ESTOP_LATCHED)
        self.assertEqual(hardware.dispatch_count, 0)
        controller.close()

    def test_receipt_is_correlated_to_request_and_session(self):
        clock = SequenceClock()
        hardware = SpyHardware(clock)
        controller = BrainController(
            provider=DummyAIProvider(),
            hardware=hardware,
            clock_us=clock,
            session_id="test-session",
        )
        controller.boot()
        result = controller.submit_text("yes")
        self.assertEqual(result.request_id, hardware.last_command.request_id)
        self.assertEqual(result.receipt.command_id, hardware.last_command.command_id)
        self.assertEqual(result.receipt.session_id, "test-session")
        controller.close()

    def test_structured_jsonl_log_is_written(self):
        clock = SequenceClock()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brain.jsonl"
            controller = BrainController(
                provider=DummyAIProvider(),
                hardware=SimulatorHardware(clock_us=clock),
                clock_us=clock,
                event_logger=JsonlEventLogger(path),
                session_id="test-session",
            )
            controller.boot()
            controller.submit_text("hello")
            controller.close()
            text = path.read_text(encoding="utf-8")
        self.assertIn('"event":"boot"', text)
        self.assertIn('"event":"dispatch"', text)
        self.assertIn('"event":"result"', text)

    def test_provider_timeout_rejects_before_dispatch(self):
        clock = SequenceClock(step=0)

        class SlowProvider:
            def propose(self, text, context):
                clock.value += 2_000_000
                return {"intent": "SOCIAL.HELLO", "arg": ""}

        hardware = SpyHardware(clock)
        controller = BrainController(
            provider=SlowProvider(),
            hardware=hardware,
            clock_us=clock,
            config=BrainConfig(provider_timeout_ms=1, operation_timeout_ms=5000),
            session_id="test-session",
        )
        controller.boot()
        result = controller.submit_text("hello")
        self.assertEqual(result.code, ResultCode.PROVIDER_TIMEOUT)
        self.assertEqual(hardware.dispatch_count, 0)
        controller.close()


if __name__ == "__main__":
    unittest.main()
