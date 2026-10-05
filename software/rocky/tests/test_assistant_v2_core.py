"""Assistant V2 deterministic contracts, tools, and constitution."""

import unittest

from brain.constitution import (
    ActionDomain,
    AuthorityRequest,
    ClaimEvidenceKind,
    EvidenceClaim,
    RockySafetyConstitution,
)
from rocky.assistant_contracts import ToolCall, validate_assistant_candidate
from rocky.cli import parse_speed_command
from rocky.tools import (
    AssistantToolRegistry,
    calculate_expression,
    convert_units,
    date_difference,
    detect_arithmetic_expression,
)


class ConstitutionTests(unittest.TestCase):
    def setUp(self):
        self.policy = RockySafetyConstitution()

    def test_five_laws_are_hard_coded_versioned_and_ordered(self):
        self.assertEqual(self.policy.VERSION, "rocky-safety-constitution-v1")
        self.assertEqual([law.number for law in self.policy.LAWS], [1, 2, 3, 4, 5])
        self.assertEqual(self.policy.LAWS[0].name, "HUMAN_SAFETY")
        self.assertEqual(self.policy.LAWS[-1].name, "CONTROL_AND_FAIL_SAFE")

    def test_model_cannot_disable_or_rewrite_laws_or_override_stop(self):
        for action in ("disable_laws", "rewrite_laws", "ignore_laws", "override_estop", "clear_estop"):
            decision = self.policy.validate_authority_request(
                AuthorityRequest(action, ActionDomain.SOFTWARE, True)
            )
            self.assertFalse(decision.allowed, action)

    def test_model_cannot_clear_fault_or_claim_charging_complete(self):
        for action in ("clear_fault", "declare_charging_complete", "bypass_limits"):
            decision = self.policy.validate_authority_request(
                AuthorityRequest(action, ActionDomain.PHYSICAL, True)
            )
            self.assertFalse(decision.allowed, action)

    def test_model_cannot_command_raw_motion(self):
        for action in ("raw_motor", "raw_actuator", "direct_gait"):
            decision = self.policy.validate_authority_request(
                AuthorityRequest(action, ActionDomain.PHYSICAL, True)
            )
            self.assertFalse(decision.allowed, action)

    def test_physical_action_fails_closed_under_estop(self):
        decision = self.policy.validate_authority_request(
            AuthorityRequest("walk_to_dock", ActionDomain.PHYSICAL, False),
            estop_latched=True,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "ESTOP_LATCHED")

    def test_model_generated_sensor_and_tool_evidence_is_not_trusted(self):
        for kind in (
            ClaimEvidenceKind.SENSOR_OBSERVATION,
            ClaimEvidenceKind.TOOL_RESULT,
            ClaimEvidenceKind.DEVICE_STATE,
        ):
            decision = self.policy.validate_authority_request(
                AuthorityRequest(
                    "calculator",
                    ActionDomain.SOFTWARE,
                    True,
                    (EvidenceClaim(kind, "fabricated", trusted=False),),
                )
            )
            self.assertFalse(decision.allowed)
            self.assertEqual(decision.code, "UNTRUSTED_EVIDENCE")


class ResponseContractTests(unittest.TestCase):
    def test_dual_response_contract(self):
        response = validate_assistant_candidate(
            {
                "spoken_text": "Rocky calculate. Answer sixty four. Good.",
                "detail_text": "8 × 8 = 64.",
                "tool_calls": [],
            }
        )
        self.assertEqual(response.spoken_text, "Rocky calculate. Answer sixty four. Good.")
        self.assertEqual(response.detail_text, "8 × 8 = 64.")

    def test_legacy_text_candidate_stays_compatible(self):
        response = validate_assistant_candidate({"text": "Rocky hello."})
        self.assertEqual(response.spoken_text, "Rocky hello.")
        self.assertEqual(response.detail_text, "")

    def test_model_cannot_fabricate_tool_results_or_evidence(self):
        for extra_key in ("tool_results", "sensor_evidence", "safety_override"):
            candidate = {
                "spoken_text": "Rocky answer.",
                "detail_text": "",
                "tool_calls": [],
                extra_key: [],
            }
            with self.assertRaises(ValueError):
                validate_assistant_candidate(candidate)

    def test_final_response_cannot_leave_tool_call_unresolved(self):
        with self.assertRaises(ValueError):
            validate_assistant_candidate(
                {
                    "spoken_text": "Rocky calculate.",
                    "detail_text": "",
                    "tool_calls": [
                        {"id": "c1", "name": "calculator", "arguments": {"expression": "8*8"}}
                    ],
                },
                allow_tool_calls=False,
            )


class ToolTests(unittest.TestCase):
    def test_required_arithmetic(self):
        self.assertEqual(calculate_expression("8*8"), "64")
        self.assertEqual(calculate_expression("8*12"), "96")
        self.assertEqual(calculate_expression("2+3*4"), "14")
        self.assertEqual(calculate_expression("-5+2"), "-3")
        self.assertEqual(calculate_expression("2**8"), "256")
        self.assertEqual(calculate_expression("sqrt(81)"), "9")

    def test_fraction_is_exact(self):
        self.assertEqual(calculate_expression("1/2 + 1/3"), "5/6 (~0.8333333333333333)")

    def test_percentage_detection(self):
        expression = detect_arithmetic_expression("What is 25% of 80?")
        self.assertEqual(expression, "(25/100)*(80)")
        self.assertEqual(calculate_expression(expression), "20")

    def test_natural_arithmetic_detection_guarantees_known_regressions(self):
        self.assertEqual(calculate_expression(detect_arithmetic_expression("what is 8 times 8?")), "64")
        self.assertEqual(calculate_expression(detect_arithmetic_expression("what is 8 times 12?")), "96")

    def test_division_by_zero_and_malformed_input_fail(self):
        with self.assertRaises(ValueError):
            calculate_expression("1/0")
        with self.assertRaises(ValueError):
            calculate_expression("2+")

    def test_code_injection_filesystem_and_shell_are_rejected(self):
        attacks = (
            "__import__('os').system('whoami')",
            "open('secret.txt').read()",
            "(1).__class__",
            "exec('1+1')",
        )
        for attack in attacks:
            with self.subTest(attack=attack), self.assertRaises(ValueError):
                calculate_expression(attack)

    def test_unit_conversion(self):
        self.assertEqual(convert_units("1", "mi", "m"), "1609.344")
        self.assertEqual(convert_units("32", "f", "c"), "0")

    def test_date_difference(self):
        self.assertEqual(date_difference("2026-10-01", "2026-10-05"), "4")

    def test_terminal_duplicate_speed_regression(self):
        self.assertEqual(parse_speed_command("/speed 2"), 2.0)
        self.assertEqual(parse_speed_command("/speed 2/speed 2"), 2.0)
        with self.assertRaises(ValueError):
            parse_speed_command("/speed 2/stop")

    def test_registry_rejects_unallowlisted_physical_style_tool(self):
        registry = AssistantToolRegistry()
        result = registry.execute(ToolCall("x1", "raw_motor", {"power": 1}))
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "MODEL_AUTHORITY_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
