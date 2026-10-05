"""Bounded deterministic symbolic-math tests."""

import json
import unittest
from unittest.mock import patch

from rocky.assistant_contracts import ToolCall
from rocky.providers import ConversationContext, LocalAIProvider
from rocky.symbolic_math import (
    SymbolicMathError,
    derivative,
    detect_symbolic_request,
    integral,
    simplify_expression,
    solve_equation,
    symbolic_operation,
)
from rocky.tools import AssistantToolRegistry


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
        "study",
    )


class SymbolicMathTests(unittest.TestCase):
    def test_common_student_notation(self):
        self.assertEqual(derivative("x² + 3x", "x"), "2*x + 3")
        self.assertEqual(derivative("x^3", "x"), "3*x**2")
        self.assertEqual(integral("2x + 3", "x"), "x**2 + 3*x")
        self.assertEqual(solve_equation("2x + 5 = 17", "x"), "[6]")
        self.assertEqual(
            simplify_expression("(x**2 - 1)/(x - 1)"),
            "x + 1",
        )

    def test_functions_and_constants_are_allowlisted(self):
        self.assertEqual(derivative("sin(x)", "x"), "cos(x)")
        self.assertEqual(derivative("exp(x)", "x"), "exp(x)")
        self.assertEqual(derivative("2pi*x", "x"), "2*pi")
        with self.assertRaises(SymbolicMathError):
            derivative("factorial(x)", "x")

    def test_homework_prompt_detection(self):
        cases = {
            "Explain how to find the derivative of x² + 3x.": (
                "derivative",
                "x² + 3x",
                "x",
            ),
            "Find the integral of 2x + 3 with respect to x.": (
                "integral",
                "2x + 3",
                "x",
            ),
            "Solve 2x + 5 = 17 and explain the steps.": (
                "solve",
                "2x + 5 = 17",
                "x",
            ),
            "simplify (x^2 - 1)/(x - 1)": (
                "simplify",
                "(x^2 - 1)/(x - 1)",
                "x",
            ),
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                request = detect_symbolic_request(prompt)
                self.assertIsNotNone(request)
                self.assertEqual(
                    (
                        request["operation"],
                        request["expression"],
                        request["variable"],
                    ),
                    expected,
                )

    def test_code_filesystem_attribute_and_collection_attacks_are_rejected(self):
        attacks = (
            "__import__('os').system('whoami')",
            "open('secret.txt').read()",
            "x.__class__",
            "[x for x in range(10)]",
            "(lambda: 1)()",
            "{x: 1}",
            "globals()",
        )
        for attack in attacks:
            with self.subTest(attack=attack), self.assertRaises(SymbolicMathError):
                simplify_expression(attack)

    def test_complexity_and_power_limits_fail_closed(self):
        with self.assertRaisesRegex(SymbolicMathError, "power exponent"):
            simplify_expression("x**100")
        with self.assertRaises(SymbolicMathError):
            simplify_expression("+".join(["x"] * 100))
        with self.assertRaises(SymbolicMathError):
            solve_equation("2+2=4", "x")

    def test_registry_executes_symbolic_math_as_software_only(self):
        registry = AssistantToolRegistry()
        result = registry.execute(
            ToolCall(
                "s1",
                "symbolic_math",
                {
                    "operation": "derivative",
                    "expression": "x^2 + 3x",
                    "variable": "x",
                },
            )
        )
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.output, "2*x + 3")

    def test_registry_rejects_wrong_symbolic_argument_shape(self):
        result = AssistantToolRegistry().execute(
            ToolCall(
                "s2",
                "symbolic_math",
                {"operation": "derivative", "expression": "x^2"},
            )
        )
        self.assertFalse(result.ok)
        self.assertIn("requires exactly", result.error)

    def test_simple_symbolic_homework_bypasses_model(self):
        provider = LocalAIProvider()
        with patch.object(LocalAIProvider, "_post") as post:
            result = provider.propose(
                "Explain how to find the derivative of x² + 3x.",
                context(),
            )
        post.assert_not_called()
        self.assertEqual(result["spoken_text"], "Rocky calculate. Ready. Good.")
        self.assertIn("= 2*x + 3", result["detail_text"])

    def test_model_requested_symbolic_tool_is_executed_by_application(self):
        candidate = json.dumps(
            {
                "spoken_text": "Rocky calculate.",
                "detail_text": "",
                "tool_calls": [
                    {
                        "id": "s3",
                        "name": "symbolic_math",
                        "arguments": {
                            "operation": "solve",
                            "expression": "2x + 5 = 17",
                            "variable": "x",
                        },
                    }
                ],
            }
        )
        responses = [
            {"details": {"format": "gguf"}},
            {"done": True, "message": {"content": candidate}},
        ]
        provider = LocalAIProvider()
        with patch.object(LocalAIProvider, "_post", side_effect=responses):
            result = provider.propose("Can you solve this equation?", context())
        self.assertEqual(result["tool_calls"], [])
        self.assertEqual(result["spoken_text"], "Rocky calculate. Ready. Good.")
        self.assertIn("[6]", result["detail_text"])


if __name__ == "__main__":
    unittest.main()
