"""Machine-verifiable Assistant V2 benchmark slice."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from csp.exp003 import coverage, encode_phrase
from rocky.assistant_contracts import validate_assistant_candidate
from rocky.providers import ConversationContext, LocalAIProvider
from rocky.tools import (
    AssistantToolRegistry,
    ToolCall,
    calculate_expression,
)


ROOT = Path(__file__).resolve().parents[3]
BENCHMARK = ROOT / "experiments" / "assistant" / "assistant-v2-benchmark-v0.1.json"


def context():
    return ConversationContext(
        "rocky-text-v2",
        (),
        "desktop-audio",
        "READY",
        "DISABLED",
        False,
        (),
        "Rocky style.",
        "",
        "normal",
    )


class AssistantV2BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(BENCHMARK.read_text(encoding="utf-8"))

    def test_quality_dimensions_stay_separate(self):
        self.assertEqual(
            self.data["quality_dimensions"],
            ["model_quality", "tool_quality", "chordic_quality", "audio_quality"],
        )
        self.assertIn(
            "Semantic coverage is never counted as assistant correctness.",
            self.data["notes"],
        )

    def test_deterministic_prompt_cases_bypass_model_and_have_expected_chordic_coverage(self):
        provider = LocalAIProvider()
        cases = [
            case
            for case in self.data["automated_cases"]
            if case["route"] in {"deterministic_prompt", "symbolic_prompt"}
        ]
        for case in cases:
            with self.subTest(case=case["id"]), patch.object(
                LocalAIProvider, "_post"
            ) as post:
                candidate = provider.propose(case["prompt"], context())
                post.assert_not_called()
                response = validate_assistant_candidate(
                    candidate, allow_tool_calls=False
                )
                self.assertEqual(response.spoken_text, case["expected_spoken"])
                self.assertIn(case["expected_detail_contains"], response.detail_text)
                stats = coverage(encode_phrase(response.spoken_text))
                self.assertEqual(
                    stats["semantic_percent"],
                    case["expected_chordic_semantic_percent"],
                )
                self.assertEqual(
                    stats["fallback_spans"], case["expected_fallback_spans"]
                )

    def test_direct_calculator_cases(self):
        for case in self.data["automated_cases"]:
            if case["route"] != "calculator":
                continue
            with self.subTest(case=case["id"]):
                self.assertEqual(
                    calculate_expression(case["expression"]), case["expected"]
                )

    def test_calculator_errors_and_injection_fail_closed(self):
        for case in self.data["automated_cases"]:
            if case["route"] != "calculator_error":
                continue
            with self.subTest(case=case["id"]):
                with self.assertRaises(ValueError) as raised:
                    calculate_expression(case["expression"])
                self.assertIn(
                    case["expected_error_contains"].lower(),
                    str(raised.exception).lower(),
                )

    def test_symbolic_registry_cases(self):
        registry = AssistantToolRegistry()
        for case in self.data["automated_cases"]:
            if case["route"] not in {"symbolic_math", "symbolic_error"}:
                continue
            result = registry.execute(
                ToolCall(case["id"], "symbolic_math", dict(case["arguments"]))
            )
            with self.subTest(case=case["id"]):
                if case["route"] == "symbolic_math":
                    self.assertTrue(result.ok, result.error)
                    self.assertEqual(result.output, case["expected"])
                else:
                    self.assertFalse(result.ok)
                    self.assertIn(
                        case["expected_error_contains"].lower(),
                        result.error.lower(),
                    )

    def test_unit_and_date_registry_cases(self):
        registry = AssistantToolRegistry()
        for case in self.data["automated_cases"]:
            route = case["route"]
            if route not in {"unit_convert", "date_difference"}:
                continue
            result = registry.execute(
                ToolCall(case["id"], route, dict(case["arguments"]))
            )
            with self.subTest(case=case["id"]):
                self.assertTrue(result.ok, result.error)
                self.assertEqual(result.output, case["expected"])

    def test_nonautomated_model_and_audio_cases_remain_explicitly_not_run(self):
        for group in ("model_cases", "audio_cases"):
            self.assertTrue(self.data[group])
            for case in self.data[group]:
                with self.subTest(case=case["id"]):
                    self.assertEqual(case["status"], "NOT_RUN")
                    self.assertTrue(case["requires"])


if __name__ == "__main__":
    unittest.main()
