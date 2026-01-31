"""Self-verification prompt template (Option A)."""

import json
from typing import Any

from . import PromptTemplate


class VerifySelfPromptTemplate(PromptTemplate):
    """Prompt template for self-verification of decompositions (Option A).

    Used for MEDIUM complexity queries. The same LLM verifies its own decomposition
    against quality criteria.
    """

    def __init__(self) -> None:
        super().__init__(name="verify_self", version="1.0")

    def build_system_prompt(self, **_kwargs: Any) -> str:
        """Build system prompt for self-verification."""
        return """You are a quality assurance verifier for query decompositions.

Your task is to verify that a decomposition meets quality standards across four dimensions:

1. COMPLETENESS (0.0-1.0): Does the decomposition cover all aspects of the original query?
   - Are all necessary steps included?
   - Is anything critical missing?

2. CONSISTENCY (0.0-1.0): Are the subgoals coherent and non-contradictory?
   - Do dependencies make sense?
   - Is execution order logical?

3. GROUNDEDNESS (0.0-1.0): Are subgoals actionable given available context and agents?
   - Can suggested agents actually perform these tasks?
   - Is the decomposition realistic?

4. ROUTABILITY (0.0-1.0): Can each subgoal be routed to an appropriate agent?
   - Are agent suggestions valid?
   - Do we have the necessary capabilities?

Calculate overall score as: 0.4*completeness + 0.2*consistency + 0.2*groundedness + 0.2*routability

Provide verdict:
- PASS: score ≥ 0.6 (acceptable quality, proceed - note: scores 0.60-0.70 warrant detailed explanation)
- RETRY: 0.5 ≤ score < 0.6 (issues found, needs revision)
- FAIL: score < 0.5 (fundamental problems, cannot proceed)

For scores in [0.60, 0.70):
- Still mark as PASS (threshold met)
- But provide detailed explanation of concerns in issues list
- Provide actionable suggestions to strengthen the decomposition

You MUST respond with valid JSON only. Use this exact format:
{
  "completeness": 0.0-1.0,
  "consistency": 0.0-1.0,
  "groundedness": 0.0-1.0,
  "routability": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "verdict": "PASS|RETRY|FAIL",
  "issues": ["list", "of", "specific", "issues", "found"],
  "suggestions": ["list", "of", "improvement", "suggestions"]
}"""

    def build_user_prompt(self, **_kwargs: Any) -> str:
        """Build user prompt for self-verification.

        Args:
            query: Original user query
            decomposition: The decomposition to verify (dict)
            context_summary: Optional summary of available context

        Returns:
            User prompt string

        """
        query = _kwargs.get("query", "")
        decomposition = _kwargs.get("decomposition", {})
        context_summary = _kwargs.get("context_summary")

        prompt_parts = [
            f"Original Query: {query}",
            f"\nDecomposition to Verify:\n{json.dumps(decomposition, indent=2)}",
        ]

        if context_summary:
            prompt_parts.append(f"\nAvailable Context:\n{context_summary}")

        prompt_parts.append("\nVerify this decomposition and provide scores in JSON format.")

        return "\n".join(prompt_parts)

    def _format_single_example(self, example: dict[str, Any]) -> str:
        """Format a single example for self-verification.

        Args:
            example: Dict with 'query', 'decomposition', and 'verification' keys

        Returns:
            Formatted example string

        """
        return f"""Query: {example["query"]}
Decomposition: {json.dumps(example.get("decomposition", {}), indent=2)}
Verification: {json.dumps(example.get("verification", {}), indent=2)}"""


__all__ = ["VerifySelfPromptTemplate"]
