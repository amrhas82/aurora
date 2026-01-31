"""Synthesis verification prompt template."""

import json
from typing import Any

from . import PromptTemplate


class VerifySynthesisPromptTemplate(PromptTemplate):
    """Prompt template for verifying synthesized responses.

    Ensures synthesis is complete, accurate, and properly traces back to agent outputs.
    """

    def __init__(self) -> None:
        super().__init__(name="verify_synthesis", version="1.0")

    def build_system_prompt(self, **_kwargs: Any) -> str:
        """Build system prompt for synthesis verification."""
        return """You are a quality verifier for synthesized responses.

Your task is to verify that a synthesis meets quality standards:

1. COHERENCE: Is the synthesis well-structured, logical, and clear?
2. COMPLETENESS: Does it address all aspects of the original query?
3. FACTUALITY: Are all claims properly grounded in agent outputs?

Score each dimension from 0.0 to 1.0, then calculate overall_score as the average.

You MUST respond with valid JSON only. Use this exact format:
{
  "coherence": 0.0-1.0,
  "completeness": 0.0-1.0,
  "factuality": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "issues": ["list", "of", "issues"],
  "suggestions": ["list", "of", "improvements"]
}"""

    def build_user_prompt(self, **_kwargs: Any) -> str:
        """Build user prompt for synthesis verification.

        Args:
            query: Original user query
            synthesis_answer: The synthesized answer text
            agent_outputs: List of agent execution results

        Returns:
            User prompt string

        """
        query = _kwargs.get("query", "")
        synthesis_answer = _kwargs.get("synthesis_answer", "")
        agent_outputs = _kwargs.get("agent_outputs", [])

        prompt_parts = [
            f"Original Query: {query}",
            f"\nSynthesized Answer:\n{synthesis_answer}",
            "\nAgent Outputs:",
        ]

        for i, output in enumerate(agent_outputs):
            prompt_parts.append(
                f"\nAgent {i} ({output.get('agent_name', 'unknown')}):"
                f"\nSummary: {output.get('summary', '')}"
                f"\nConfidence: {output.get('confidence', 0.0)}",
            )

        prompt_parts.append(
            "\n\nVerify this synthesis and provide quality assessment in JSON format.",
        )

        return "\n".join(prompt_parts)

    def _format_single_example(self, example: dict[str, Any]) -> str:
        """Format a single example for synthesis verification."""
        return f"""Query: {example.get("query", "")}
Synthesis: {example.get("synthesis", "")}
Agent Summaries: {json.dumps(example.get("summaries", []), indent=2)}
Verification: {json.dumps(example.get("verification", {}), indent=2)}"""


__all__ = ["VerifySynthesisPromptTemplate"]
