import json
from pathlib import Path
import statistics
import unittest

from brain.controller import TaskController
from csp.conversation import Utterance
from csp.core import CspCodec
import csp.exp002 as exp002
from csp.exp003 import Exp003Phrase, SOURCE_COMMIT, coverage, decode_phrase, encode_phrase, load_profile
from rocky.audio import estimated_duration, synthesize

ROOT = Path(__file__).resolve().parents[3]
BENCHMARK = ROOT / "experiments" / "chordic" / "exp-003-benchmark.json"


class Exp003RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.codec = CspCodec.from_default_spec()
        self.tasks = TaskController(self.codec, "exp003")
        self.profile = load_profile()
        self.benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))

    def test_chordic_export_is_pinned_and_rocky_has_no_exp002_surface_dictionary(self):
        self.assertEqual(SOURCE_COMMIT, "654deaa0ab7c77efe4d36876936a73ec0890065c")
        self.assertEqual(self.profile["export_id"], "EXP-003-runtime-v1")
        self.assertFalse(hasattr(exp002, "_SURFACES"))
        exported = exp002.surface_registry()
        self.assertEqual(exported["hello"], ("SOCIAL.HELLO",))
        self.assertEqual(exported["fist my bump"], ("SOCIAL.FIST_BUMP",))

    def test_real_math_and_food_evidence_have_no_fallback(self):
        samples = (
            "8 times 8 is 64. Rocky calculate. Good.",
            "Rocky no eat. Rocky think food is energy. Rocky use energy to think and build.",
        )
        for text in samples:
            with self.subTest(text=text):
                phrase = encode_phrase(text)
                self.assertEqual(decode_phrase(phrase), text)
                stats = coverage(phrase)
                self.assertEqual(stats["semantic_percent"], 100.0)
                self.assertEqual(stats["fallback_spans"], 0)
                self.assertEqual(stats["fallback_bytes"], 0)

    def test_open_conversation_benchmark_reproduces_coverage_and_timing(self):
        durations = []
        for expected in self.benchmark["results"]:
            with self.subTest(case=expected["id"]):
                output = self.tasks.build_communication(Utterance(expected["english"]))
                self.assertIsInstance(output.phrase, Exp003Phrase)
                stats = coverage(output.phrase)
                self.assertEqual(stats["semantic_tokens"], expected["semantic_token_count"])
                self.assertEqual(stats["fallback_spans"], expected["fallback_span_count"])
                self.assertEqual(stats["fallback_bytes"], expected["fallback_bytes"])
                self.assertEqual(stats["semantic_percent"], expected["semantic_coverage_percent"])
                duration = estimated_duration(output, self.codec, self.benchmark["playback_multiplier"])
                self.assertAlmostEqual(duration, expected["total_duration_seconds"], places=2)
                durations.append((expected["class"], duration))
        non_seed = [value for kind, value in durations if kind != "seed"]
        self.assertAlmostEqual(statistics.mean(non_seed), self.benchmark["summary"]["non_seed"]["mean_seconds"], places=2)
        self.assertLessEqual(max(non_seed), 10.0)

    def test_unseen_technical_words_stay_visible_as_exact_fallback(self):
        phrase = encode_phrase("Rocky calibrate spectrometer")
        self.assertEqual(decode_phrase(phrase), "Rocky calibrate spectrometer")
        stats = coverage(phrase)
        self.assertEqual(stats["fallback_spans"], 2)
        self.assertGreater(stats["fallback_bytes"], 0)
        self.assertLess(stats["semantic_percent"], 100.0)

    def test_math_is_compositional_not_whole_sentence_mapping(self):
        phrase = encode_phrase("8 times 8 is 64")
        tokens = tuple(token for unit in phrase.units for token in unit.tokens)
        self.assertEqual(tokens, ("NUM.8", "OP.MUL", "NUM.8", "NUM.6", "NUM.4"))
        surfaces = {row["text"].lower() for row in self.profile["surface_forms"]}
        self.assertNotIn("8 times 8 is 64", surfaces)

    def test_contour_v1_pcm_is_deterministic_bounded_and_duration_matches(self):
        output = self.tasks.build_communication(Utterance("hello rocky"))
        first = synthesize(output, self.codec, volume=0.12, duration_multiplier=3, tone_style="contour-v1")
        second = synthesize(output, self.codec, volume=0.12, duration_multiplier=3, tone_style="contour-v1")
        self.assertEqual(first, second)
        self.assertGreater(len(first), 0)
        self.assertEqual(len(first) % 2, 0)
        expected_frames = round(estimated_duration(output, self.codec, 3) * 22050)
        self.assertLessEqual(abs(len(first) // 2 - expected_frames), 8)

    def test_ct2_and_exp002_profiles_remain_available(self):
        self.assertEqual(TaskController(self.codec, "ct2").text_encoding, "ct2")
        self.assertEqual(TaskController(self.codec, "exp002").text_encoding, "exp002")
        self.assertEqual(TaskController(self.codec, "exp003").text_encoding, "exp003")


if __name__ == "__main__":
    unittest.main()
