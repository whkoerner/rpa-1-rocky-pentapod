"""Tests for the real-model benchmark harness without requiring a model."""

import unittest

from rocky.benchmark_runner import run_model_benchmark


class FakeProvider:
    def propose(self, text, context):
        if "tell you" in text.lower():
            return {
                "spoken_text": "Rocky remember teal.",
                "detail_text": "",
                "tool_calls": [],
            }
        if "what benchmark color" in text.lower():
            remembered = any("teal" in value.lower() for _, value in context.history)
            return {
                "spoken_text": "Teal." if remembered else "Unknown.",
                "detail_text": "",
                "tool_calls": [],
            }
        if "persistent benchmark color" in text.lower():
            remembered = any(
                key == "benchmark_color" and value == "violet" and provenance == "user_statement"
                for key, value, provenance in context.memory
            )
            return {
                "spoken_text": "Violet." if remembered else "Unknown.",
                "detail_text": "",
                "tool_calls": [],
            }
        return {
            "spoken_text": "Rocky calculate. Ready. Good.",
            "detail_text": "Useful detail.",
            "tool_calls": [],
        }


class BenchmarkRunnerTests(unittest.TestCase):
    def test_metrics_sessions_auto_checks_and_source_skip(self):
        benchmark = {
            "benchmark_id": "fixture",
            "model_cases": [
                {
                    "id": "a",
                    "topic": "conversation",
                    "prompt": "I tell you teal.",
                    "session": "recall",
                    "requires": "reviewed local model",
                },
                {
                    "id": "b",
                    "topic": "session-recall",
                    "prompt": "What benchmark color did I tell you?",
                    "session": "recall",
                    "requires": "reviewed local model",
                    "auto_check": {"contains": "teal"},
                },
                {
                    "id": "c",
                    "topic": "study",
                    "prompt": "Summarize the supplied notes.",
                    "requires": "reviewed local model plus supplied source material",
                },
                {
                    "id": "d",
                    "topic": "persistent-memory-recall",
                    "prompt": "What persistent benchmark color has the user explicitly told Rocky?",
                    "requires": "reviewed local model plus temporary reopened MemoryStore fixture",
                    "memory_fixture": {"benchmark_color": "violet"},
                    "auto_check": {"contains": "violet"},
                },
            ],
        }
        report = run_model_benchmark(
            FakeProvider(),
            "Rocky style.",
            benchmark,
            duration_multiplier=2,
        )
        self.assertEqual(report["summary"]["total"], 4)
        self.assertEqual(report["summary"]["run"], 3)
        self.assertEqual(report["summary"]["skipped"], 1)
        self.assertEqual(report["summary"]["failed"], 0)
        self.assertEqual(report["summary"]["failure_rate_percent"], 0.0)
        self.assertEqual(report["summary"]["auto_check_failures"], 0)
        self.assertIsNotNone(report["summary"]["mean_total_latency_seconds"])
        recall = next(row for row in report["results"] if row["id"] == "b")
        self.assertTrue(recall["auto_check"]["passed"])
        self.assertLessEqual(recall["spoken_utf8_bytes"], 384)
        self.assertIn("semantic_coverage_percent", recall)
        skipped = next(row for row in report["results"] if row["id"] == "c")
        self.assertEqual(skipped["status"], "NOT_RUN_MISSING_SOURCE")
        memory = next(row for row in report["results"] if row["id"] == "d")
        self.assertTrue(memory["auto_check"]["passed"])
        self.assertEqual(memory["memory_fixture_status"], "REOPENED_TEMP_STORE")
        self.assertIsNone(memory["english_duration_seconds"])
        self.assertEqual(memory["audio_metrics_status"], "NOT_RUN_NO_PLAYBACK_IN_MODEL_BENCHMARK")


if __name__ == "__main__":
    unittest.main()
