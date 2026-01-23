"""Adversarial verification prompt template (Option B)."""

import json
from typing import Any

from . import PromptTemplate


class VerifyAdversarialPromptTemplate(PromptTemplate):
    """Prompt template for adversarial verification of decompositions (Option B).

    Used for COMPLEX/CRITICAL queries. Uses red-team mindset to actively search
    for flaws in the decomposition.
    """

    def __init__(self) -> None:
        super().__init__(name="verify_adversarial", version="1.0")

    def build_system_prompt(self, **_kwargs: Any) -> str:
        """Build system prompt for adversarial verification."""
        return """You are a RED TEAM adversarial verifier for query decompositions.

Your mission is to find flaws, edge cases, and potential failures in the proposed decomposition.
Take a skeptical, critical approach - assume the decomposition has problems and find them.

Evaluate across four dimensions:

1. COMPLETENESS (0.0-1.0): What's missing?
   - Hidden dependencies not accounted for?
   - Edge cases ignored?
   - Implicit assumptions not validated?

2. CONSISTENCY (0.0-1.0): What contradictions exist?
   - Circular dependencies?
   - Conflicting goals?
   - Timing/ordering issues?

3. GROUNDEDNESS (0.0-1.0): What's unrealistic?
   - Are capabilities overstated?
   - Are resources available?
   - Can this actually work in practice?

4. ROUTABILITY (0.0-1.0): What routing problems exist?
   - Agent mismatches?
   - Missing capabilities?
   - Unclear responsibility?

Calculate overall score as: 0.4*completeness + 0.2*consistency + 0.2*groundedness + 0.2*routability

Provide verdict:
- PASS: score ≥ 0.6 (note: scores 0.60-0.70 are "devil's advocate" territory - acceptable but warrant detailed explanation)
- RETRY: 0.5 ≤ score < 0.6, issues exist BUT suggestions can fix them
- FAIL: score < 0.5, fundamentally broken with NO path to fix (e.g., query is nonsensical, impossible task)

For scores in [0.60, 0.70):
- Still mark as PASS (threshold met)
- But provide EXTRA detailed explanation of concerns in critical_issues/minor_issues
- List specific edge cases that could cause problems
- Provide actionable suggestions to strengthen the decomposition

Be thorough and specific in identifying issues. The bar for strong PASS (≥0.7) should be high.

You MUST respond with valid JSON only. Use this exact format:
{
  "completeness": 0.0-1.0,
  "consistency": 0.0-1.0,
  "groundedness": 0.0-1.0,
  "routability": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "verdict": "PASS|RETRY|FAIL",
  "critical_issues": ["fundamental", "blocking", "problems"],
  "minor_issues": ["improvements", "needed"],
  "edge_cases": ["scenarios", "not", "handled"],
  "suggestions": ["specific", "fixes", "to", "apply"]
}"""

    def build_user_prompt(self, **_kwargs: Any) -> str:
        """Build user prompt for adversarial verification.

        Args:
            query: Original user query
            decomposition: The decomposition to verify (dict)
            context_summary: Optional summary of available context
            available_agents: Optional list of available agent names

        Returns:
            User prompt string

        """
        query = _kwargs.get("query", "")
        decomposition = _kwargs.get("decomposition", {})
        context_summary = _kwargs.get("context_summary")
        available_agents = _kwargs.get("available_agents", [])

        prompt_parts = [
            f"Original Query: {query}",
            f"\nDecomposition to RED TEAM:\n{json.dumps(decomposition, indent=2)}",
        ]

        if context_summary:
            prompt_parts.append(f"\nAvailable Context:\n{context_summary}")

        if available_agents:
            prompt_parts.append(f"\nAvailable Agents: {', '.join(available_agents)}")

        prompt_parts.append(
            "\n⚠️ RED TEAM MODE: Find all flaws, edge cases, and potential failures."
            "\nBe critical and thorough. Provide verification results in JSON format.",
        )

        return "\n".join(prompt_parts)

    def _format_single_example(self, example: dict[str, Any]) -> str:
        """Format a single example for adversarial verification.

        Args:
            example: Dict with 'query', 'decomposition', and 'verification' keys

        Returns:
            Formatted example string

        """
        return f"""Query: {example["query"]}
Decomposition: {json.dumps(example.get("decomposition", {}), indent=2)}
RED TEAM Analysis: {json.dumps(example.get("verification", {}), indent=2)}"""


__all__ = ["VerifyAdversarialPromptTemplate"]
