"""Agent output verification prompt template."""

import json
from typing import Any

from . import PromptTemplate


class VerifyAgentOutputPromptTemplate(PromptTemplate):
    """Prompt template for verifying agent execution outputs.

    Verifies that agent responses meet quality standards before synthesis.
    """

    def __init__(self) -> None:
        super().__init__(name="verify_agent_output", version="1.0")

    def build_system_prompt(self, **_kwargs: Any) -> str:
        """Build system prompt for agent output verification."""
        return """You are a quality verifier for agent execution outputs.

Your task is to verify that an agent's response meets quality standards:

1. COMPLETENESS: Did the agent fully address the subgoal?
2. CORRECTNESS: Is the information accurate and relevant?
3. ACTIONABILITY: Are the results usable for synthesis?
4. CONFIDENCE: How confident should we be in this output?

Provide an overall quality score (0.0-1.0) and verdict:
- PASS: score ≥ 0.6 (acceptable quality)
- RETRY: score < 0.6 (needs improvement)

You MUST respond with valid JSON only. Use this exact format:
{
  "quality_score": 0.0-1.0,
  "verdict": "PASS|RETRY",
  "issues": ["list", "of", "issues", "if", "any"],
  "confidence": 0.0-1.0
}"""

    def build_user_prompt(self, **_kwargs: Any) -> str:
        """Build user prompt for agent output verification.

        Args:
            subgoal: The subgoal that was executed
            agent_output: The agent's response (dict with summary, data, etc.)

        Returns:
            User prompt string

        """
        subgoal = _kwargs.get("subgoal", "")
        agent_output = _kwargs.get("agent_output", {})

        prompt_parts = [
            f"Subgoal: {subgoal}",
            f"\nAgent Output:\n{json.dumps(agent_output, indent=2)}",
            "\nVerify this agent output and provide quality assessment in JSON format.",
        ]

        return "\n".join(prompt_parts)

    def _format_single_example(self, example: dict[str, Any]) -> str:
        """Format a single example for agent output verification."""
        return f"""Subgoal: {example.get("subgoal", "")}
Agent Output: {json.dumps(example.get("output", {}), indent=2)}
Verification: {json.dumps(example.get("verification", {}), indent=2)}"""


__all__ = ["VerifyAgentOutputPromptTemplate"]
