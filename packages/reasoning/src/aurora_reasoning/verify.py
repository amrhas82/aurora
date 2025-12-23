"""Verification logic for query decompositions.

This module implements verification of decompositions using either:
- Option A: Self-verification (MEDIUM complexity)
- Option B: Adversarial verification (COMPLEX/CRITICAL complexity)
"""

from __future__ import annotations

import json
from enum import Enum
from typing import TYPE_CHECKING, Any

from .prompts.verify_adversarial import VerifyAdversarialPromptTemplate
from .prompts.verify_self import VerifySelfPromptTemplate


if TYPE_CHECKING:
    from .llm_client import LLMClient

__all__ = ["verify_decomposition", "VerificationResult", "VerificationVerdict", "VerificationOption"]


class VerificationVerdict(str, Enum):
    """Verification verdict outcomes."""
    PASS = "PASS"      # Score ≥ 0.7, proceed with decomposition
    RETRY = "RETRY"    # 0.5 ≤ score < 0.7, revise and retry
    FAIL = "FAIL"      # Score < 0.5, fundamental issues


class VerificationOption(str, Enum):
    """Verification approach options."""
    SELF = "self"              # Option A: Self-verification (MEDIUM)
    ADVERSARIAL = "adversarial"  # Option B: Adversarial (COMPLEX/CRITICAL)


class VerificationResult:
    """Result of decomposition verification.

    Attributes:
        completeness: Completeness score (0.0-1.0)
        consistency: Consistency score (0.0-1.0)
        groundedness: Groundedness score (0.0-1.0)
        routability: Routability score (0.0-1.0)
        overall_score: Weighted overall score
        verdict: PASS, RETRY, or FAIL
        issues: List of identified issues
        suggestions: List of improvement suggestions
        option_used: Which verification option was used
        raw_response: Raw LLM response text
    """

    def __init__(
        self,
        completeness: float,
        consistency: float,
        groundedness: float,
        routability: float,
        overall_score: float,
        verdict: VerificationVerdict,
        issues: list[str],
        suggestions: list[str],
        option_used: VerificationOption,
        raw_response: str = "",
    ):
        self.completeness = completeness
        self.consistency = consistency
        self.groundedness = groundedness
        self.routability = routability
        self.overall_score = overall_score
        self.verdict = verdict
        self.issues = issues
        self.suggestions = suggestions
        self.option_used = option_used
        self.raw_response = raw_response

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "completeness": self.completeness,
            "consistency": self.consistency,
            "groundedness": self.groundedness,
            "routability": self.routability,
            "overall_score": self.overall_score,
            "verdict": self.verdict.value,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "option_used": self.option_used.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationResult:
        """Create from dictionary representation."""
        return cls(
            completeness=data["completeness"],
            consistency=data["consistency"],
            groundedness=data["groundedness"],
            routability=data["routability"],
            overall_score=data["overall_score"],
            verdict=VerificationVerdict(data["verdict"]),
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
            option_used=VerificationOption(data["option_used"]),
        )


def verify_decomposition(
    llm_client: LLMClient,
    query: str,
    decomposition: dict[str, Any],
    option: VerificationOption,
    context_summary: str | None = None,
    available_agents: list[str] | None = None,
) -> VerificationResult:
    """Verify a query decomposition using specified verification option.

    This function:
    1. Selects appropriate prompt template (self or adversarial)
    2. Builds verification prompt with query, decomposition, and context
    3. Calls LLM for verification scores and verdict
    4. Validates and parses verification response
    5. Returns VerificationResult with scores and verdict

    Args:
        llm_client: LLM client to use for verification
        query: Original user query
        decomposition: Decomposition to verify (dict with goal, subgoals, etc.)
        option: Verification option (SELF or ADVERSARIAL)
        context_summary: Optional summary of available context
        available_agents: Optional list of available agent names

    Returns:
        VerificationResult with scores, verdict, issues, and suggestions

    Raises:
        ValueError: If LLM response is invalid or missing required fields
        RuntimeError: If LLM call fails after retries
    """
    # Select prompt template based on option
    prompt_template: VerifySelfPromptTemplate | VerifyAdversarialPromptTemplate
    if option == VerificationOption.SELF:
        prompt_template = VerifySelfPromptTemplate()
    else:  # ADVERSARIAL
        prompt_template = VerifyAdversarialPromptTemplate()

    # Build prompts
    system_prompt = prompt_template.build_system_prompt()
    user_prompt = prompt_template.build_user_prompt(
        query=query,
        decomposition=decomposition,
        context_summary=context_summary,
        available_agents=available_agents,
    )

    # Call LLM with JSON output requirement
    verification = llm_client.generate_json(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.1,  # Very low temperature for consistent scoring
    )

    # Validate response is a dict (generate_json already parses JSON)
    if not isinstance(verification, dict):
        raise ValueError(
            f"LLM returned non-dict response: {type(verification)}\n"
            f"Response: {str(verification)[:500]}"
        )

    # Validate required fields
    required_fields = [
        "completeness", "consistency", "groundedness", "routability",
        "overall_score", "verdict"
    ]
    missing = [f for f in required_fields if f not in verification]
    if missing:
        raise ValueError(
            f"Verification missing required fields: {missing}\n"
            f"Response: {verification}"
        )

    # Validate score ranges
    for score_field in ["completeness", "consistency", "groundedness", "routability", "overall_score"]:
        score = verification[score_field]
        if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
            raise ValueError(
                f"Invalid {score_field} score: {score} (must be float in [0.0, 1.0])"
            )

    # Validate verdict
    try:
        verdict = VerificationVerdict(verification["verdict"])
    except ValueError as e:
        raise ValueError(
            f"Invalid verdict: {verification['verdict']} "
            f"(must be PASS, RETRY, or FAIL)"
        ) from e

    # Calculate expected overall score and validate
    expected_score = _calculate_overall_score(
        completeness=verification["completeness"],
        consistency=verification["consistency"],
        groundedness=verification["groundedness"],
        routability=verification["routability"],
    )

    # Allow small floating point difference
    if abs(verification["overall_score"] - expected_score) > 0.01:
        # Correct the score if LLM made calculation error
        verification["overall_score"] = expected_score

    # Validate verdict matches score thresholds
    _validate_verdict_consistency(verdict, verification["overall_score"])

    # Extract issues and suggestions (different fields for adversarial vs self)
    if option == VerificationOption.ADVERSARIAL:
        issues = verification.get("critical_issues", []) + verification.get("minor_issues", [])
        if "edge_cases" in verification:
            issues.extend(verification["edge_cases"])
    else:
        issues = verification.get("issues", [])

    suggestions = verification.get("suggestions", [])

    return VerificationResult(
        completeness=verification["completeness"],
        consistency=verification["consistency"],
        groundedness=verification["groundedness"],
        routability=verification["routability"],
        overall_score=verification["overall_score"],
        verdict=verdict,
        issues=issues,
        suggestions=suggestions,
        option_used=option,
        raw_response=json.dumps(verification),
    )


def _calculate_overall_score(
    completeness: float,
    consistency: float,
    groundedness: float,
    routability: float,
) -> float:
    """Calculate overall verification score using weighted formula.

    Formula: 0.4*completeness + 0.2*consistency + 0.2*groundedness + 0.2*routability

    Args:
        completeness: Completeness score (0.0-1.0)
        consistency: Consistency score (0.0-1.0)
        groundedness: Groundedness score (0.0-1.0)
        routability: Routability score (0.0-1.0)

    Returns:
        Weighted overall score (0.0-1.0)
    """
    return (
        0.4 * completeness +
        0.2 * consistency +
        0.2 * groundedness +
        0.2 * routability
    )


def _validate_verdict_consistency(verdict: VerificationVerdict, score: float) -> None:
    """Validate that verdict is consistent with score thresholds.

    Thresholds:
    - PASS: score ≥ 0.7
    - RETRY: 0.5 ≤ score < 0.7
    - FAIL: score < 0.5

    Args:
        verdict: The verdict from LLM
        score: The overall score

    Raises:
        ValueError: If verdict doesn't match score thresholds
    """
    if score >= 0.7 and verdict != VerificationVerdict.PASS:
        raise ValueError(
            f"Verdict {verdict} inconsistent with score {score:.2f} "
            f"(score ≥ 0.7 should be PASS)"
        )
    if 0.5 <= score < 0.7 and verdict not in [VerificationVerdict.RETRY, VerificationVerdict.PASS]:
        # Allow PASS for borderline cases, but not FAIL
        raise ValueError(
            f"Verdict {verdict} inconsistent with score {score:.2f} "
            f"(0.5 ≤ score < 0.7 should be RETRY or PASS)"
        )
    if score < 0.5 and verdict == VerificationVerdict.PASS:
        raise ValueError(
            f"Verdict {verdict} inconsistent with score {score:.2f} "
            f"(score < 0.5 should not be PASS)"
        )
