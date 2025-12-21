"""Synthesis verification prompt template."""

import json
from typing import Any, Dict

from . import PromptTemplate


class VerifySynthesisPromptTemplate(PromptTemplate):
    """Prompt template for verifying synthesized responses.

    Ensures synthesis is complete, accurate, and properly traces back to agent outputs.
    """

    def __init__(self):
        super().__init__(name="verify_synthesis", version="1.0")

    def build_system_prompt(self, **kwargs: Any) -> str:
        """Build system prompt for synthesis verification."""
        return """You are a quality verifier for synthesized responses.

Your task is to verify that a synthesis meets quality standards:

1. COMPLETENESS: Does it address all aspects of the original query?
2. ACCURACY: Are all claims properly grounded in agent outputs?
3. COHERENCE: Is the synthesis well-structured and clear?
4. TRACEABILITY: Can each claim be traced back to specific agent outputs?

Provide an overall quality score (0.0-1.0) and verdict:
- PASS: score ≥ 0.7 (high quality synthesis)
- RETRY: score < 0.7 (needs revision)

You MUST respond with valid JSON only. Use this exact format:
{
  "quality_score": 0.0-1.0,
  "verdict": "PASS|RETRY",
  "ungrounded_claims": ["claims", "without", "source"],
  "missing_aspects": ["query", "aspects", "not", "addressed"],
  "suggestions": ["improvements", "to", "make"]
}"""

    def build_user_prompt(self, **kwargs: Any) -> str:
        """Build user prompt for synthesis verification.

        Args:
            query: Original user query
            synthesis: The synthesized response
            agent_summaries: List of agent output summaries

        Returns:
            User prompt string
        """
        query = kwargs.get("query", "")
        synthesis = kwargs.get("synthesis", "")
        agent_summaries = kwargs.get("agent_summaries", [])

        prompt_parts = [
            f"Original Query: {query}",
            f"\nSynthesized Response:\n{synthesis}",
            f"\nAgent Summaries:\n{json.dumps(agent_summaries, indent=2)}",
            "\nVerify this synthesis and provide quality assessment in JSON format."
        ]

        return "\n".join(prompt_parts)

    def _format_single_example(self, example: Dict[str, Any]) -> str:
        """Format a single example for synthesis verification."""
        return f"""Query: {example.get('query', '')}
Synthesis: {example.get('synthesis', '')}
Agent Summaries: {json.dumps(example.get('summaries', []), indent=2)}
Verification: {json.dumps(example.get('verification', {}), indent=2)}"""


__all__ = ["VerifySynthesisPromptTemplate"]
