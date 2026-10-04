import json
import statistics
import unittest
from pathlib import Path

from brain.ai import DummyAIProvider
from brain.contracts import BrainOutcome
from brain.controller import BrainController, TaskController
from csp.conversation import Utterance
from csp.core import CspCodec
from rocky.audio import estimated_duration
from brain.hardware import SimulatorHardware
from rpa_link.messages import Mode


ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "experiments" / "chordic" / "exp-002-snapshot.json"


def load_snapshot():
    with SNAPSHOT.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def candidate_duration_seconds(case, snapshot):
    timing = snapshot["timing"]
    total_ms = timing["phrase_header_ms"] + timing["profile_marker_ms"]
    for token in case["tokens"]:
        pattern = snapshot["patterns"][token]
        total_ms += len(pattern) * (timing["note_ms"] + timing["inter_note_gap_ms"])
        total_ms += timing["token_boundary_ms"]
    return total_ms * timing["playback_multiplier"] / 1000


class SequenceClock:
    def __init__(self, start=1_000_000, step=100):
        self.value = start
        self.step = step

    def __call__(self):
        value = self.value
        self.value += self.step
        return value


class ChordicExp002IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = load_snapshot()
        self.codec = CspCodec.from_default_spec()
        self.tasks = TaskController(self.codec)

    def test_snapshot_is_pinned_and_explicitly_non_authoritative(self):
        self.assertEqual(
            self.snapshot["source_commit"],
            "65e04f31cd7d53f75efe2d00583270835cabb92b",
        )
        self.assertEqual(self.snapshot["source_pull_request"], 1)
        self.assertIn("read-only exported test fixture", self.snapshot["purpose"].lower())
        self.assertIn("authoritative", self.snapshot["purpose"].lower())

    def test_real_rocky_ct2_timing_reproduces_recorded_baseline(self):
        durations = []
        for case in self.snapshot["cases"]:
            output = self.tasks.build_communication(Utterance(case["english"]))
            durations.append(estimated_duration(output, self.codec, 3))
        expected = self.snapshot["expected_metrics"]
        self.assertAlmostEqual(
            statistics.mean(durations),
            expected["rocky_ct2_baseline_mean_seconds"],
            places=3,
        )
        self.assertAlmostEqual(max(durations), 10.875, places=3)
        self.assertEqual(sum(value > 10 for value in durations), 1)

    def test_compact_candidate_hits_normal_target_without_speed_change(self):
        durations = [
            candidate_duration_seconds(case, self.snapshot)
            for case in self.snapshot["cases"]
        ]
        expected = self.snapshot["expected_metrics"]
        self.assertAlmostEqual(
            statistics.mean(durations),
            expected["candidate_mean_seconds"],
            places=3,
        )
        self.assertAlmostEqual(max(durations), expected["candidate_max_seconds"], places=3)
        self.assertEqual(
            100 * sum(value <= 10 for value in durations) / len(durations),
            expected["candidate_percent_at_or_below_10_seconds"],
        )
        self.assertEqual(sum(value > 10 for value in durations), 0)

    def test_registered_intents_round_trip_through_snapshot_registry(self):
        by_tokens = {}
        for case in self.snapshot["cases"]:
            sequence = tuple(case["tokens"])
            self.assertNotIn(sequence, by_tokens)
            by_tokens[sequence] = case["english"]
        for case in self.snapshot["cases"]:
            self.assertEqual(by_tokens[tuple(case["tokens"])], case["english"])

    def test_brain_path_accepts_benchmark_utterance_without_motion_authority(self):
        clock = SequenceClock()
        controller = BrainController(
            provider=DummyAIProvider(),
            hardware=SimulatorHardware(clock_us=clock),
            clock_us=clock,
            session_id="chordic-exp002",
        )
        try:
            state = controller.boot()
            self.assertEqual(state.host_motion_mode, Mode.DISABLED)
            result = controller.submit_utterance({"text": "I will help you."})
            self.assertIn(result.outcome, {BrainOutcome.ACCEPTED, BrainOutcome.COMPLETED})
            self.assertEqual(result.communication.canonical_text, "I will help you.")
            self.assertEqual(controller.state.host_motion_mode, Mode.DISABLED)
            self.assertFalse(controller.state.estop_latched)
        finally:
            controller.close()


if __name__ == "__main__":
    unittest.main()
