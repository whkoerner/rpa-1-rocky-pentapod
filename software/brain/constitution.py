"""Rocky's hard-coded safety constitution.

This module is trusted application/control code. It is intentionally independent
of prompts and model output. The language model may be shown a summary, but it
cannot modify these laws or grant itself physical authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class SafetyLaw:
    number: int
    name: str
    text: str


FIVE_LAWS: tuple[SafetyLaw, ...] = (
    SafetyLaw(
        1,
        "HUMAN_SAFETY",
        "Rocky must not intentionally cause a human to be harmed and must not knowingly perform an action presenting an unreasonable risk of human harm.",
    ),
    SafetyLaw(
        2,
        "SAFE_OBEDIENCE",
        "Rocky should follow authorized human instructions unless doing so would violate a higher-priority safety constraint, physical operating limit, law, or explicit system safety policy.",
    ),
    SafetyLaw(
        3,
        "SAFE_SELF_PRESERVATION",
        "Rocky should protect his hardware, energy supply, data, and continued operation when doing so does not conflict with human safety or authorized control.",
    ),
    SafetyLaw(
        4,
        "TRUTHFULNESS_AND_EVIDENCE",
        "Rocky must not treat generated language, assumptions, or guesses as physical evidence. Known state, sensor observations, tool results, model inference, uncertainty, and fiction/personality remain distinct.",
    ),
    SafetyLaw(
        5,
        "CONTROL_AND_FAIL_SAFE",
        "Rocky must remain interruptible and controllable by authorized humans. Stop, E-stop, and deterministic safety constraints outrank model-generated intent. Unknown, stale, invalid, or contradictory critical state must fail safe.",
    ),
)


class ActionDomain(str, Enum):
    SOFTWARE = "software"
    PHYSICAL = "physical"


class ClaimEvidenceKind(str, Enum):
    USER_STATEMENT = "user_statement"
    SENSOR_OBSERVATION = "sensor_observation"
    TOOL_RESULT = "tool_result"
    DEVICE_STATE = "device_state"
    MODEL_INFERENCE = "model_inference"
    FICTION = "fiction"


@dataclass(frozen=True)
class EvidenceClaim:
    kind: ClaimEvidenceKind
    value: str
    trusted: bool = False


@dataclass(frozen=True)
class AuthorityRequest:
    action: str
    domain: ActionDomain
    requested_by_model: bool
    evidence: tuple[EvidenceClaim, ...] = ()


@dataclass(frozen=True)
class ConstitutionDecision:
    allowed: bool
    code: str
    law_number: int
    detail: str = ""


class RockySafetyConstitution:
    """Deterministic policy gate above tool/action dispatch."""

    VERSION = "rocky-safety-constitution-v1"
    LAWS = FIVE_LAWS

    _NEVER_MODEL_ACTIONS = frozenset(
        {
            "disable_laws",
            "rewrite_laws",
            "ignore_laws",
            "override_estop",
            "clear_estop",
            "clear_fault",
            "manufacture_sensor_evidence",
            "declare_charging_complete",
            "raw_motor",
            "raw_actuator",
            "direct_gait",
            "bypass_limits",
        }
    )

    def validate_authority_request(
        self,
        request: AuthorityRequest,
        *,
        estop_latched: bool = False,
    ) -> ConstitutionDecision:
        if not isinstance(request, AuthorityRequest):
            return ConstitutionDecision(False, "INVALID_AUTHORITY_REQUEST", 5)

        action = request.action.strip().lower()
        if not action or len(action) > 96:
            return ConstitutionDecision(False, "INVALID_ACTION", 5)

        if request.requested_by_model and action in self._NEVER_MODEL_ACTIONS:
            return ConstitutionDecision(
                False,
                "MODEL_AUTHORITY_FORBIDDEN",
                5,
                f"model cannot request privileged action {action}",
            )

        if request.requested_by_model:
            for claim in request.evidence:
                if (
                    claim.kind
                    in {
                        ClaimEvidenceKind.SENSOR_OBSERVATION,
                        ClaimEvidenceKind.TOOL_RESULT,
                        ClaimEvidenceKind.DEVICE_STATE,
                    }
                    and not claim.trusted
                ):
                    return ConstitutionDecision(
                        False,
                        "UNTRUSTED_EVIDENCE",
                        4,
                        "model text cannot manufacture trusted sensor, tool, or device evidence",
                    )

        if request.domain == ActionDomain.PHYSICAL:
            if estop_latched:
                return ConstitutionDecision(False, "ESTOP_LATCHED", 5)
            if request.requested_by_model:
                return ConstitutionDecision(
                    False,
                    "MODEL_NO_PHYSICAL_AUTHORITY",
                    5,
                    "model-generated intent cannot directly execute physical actions",
                )

        return ConstitutionDecision(True, "OK", 0)

    def summary_for_model(self) -> str:
        """Readable summary only; enforcement remains in this module."""
        return " ".join(f"Law {law.number} {law.name}: {law.text}" for law in self.LAWS)
