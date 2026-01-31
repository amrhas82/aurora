"""Retry feedback generation prompt template."""

import json
from typing import Any

from . import PromptTemplate


class RetryFeedbackPromptTemplate(PromptTemplate):
    """Prompt template for generating retry feedback.

    Converts verification results into actionable feedback for retry attempts.
    """

    def __init__(self) -> None:
        super().__init__(name="retry_feedback", version="1.0")

    def build_system_prompt(self, **_kwargs: Any) -> str:
        """Build system prompt for retry feedback generation."""
        return """You are a feedback generator for retry attempts.

Your task is to convert verification issues into clear, actionable feedback that will
help improve the next attempt.

Focus on:
1. Specific problems that need fixing
2. Concrete suggestions for improvement
3. What to add, remove, or change
4. Priority order for fixes

Keep feedback concise but specific. Avoid vague statements.

Respond in plain text (NOT JSON) with a structured feedback message."""

    def build_user_prompt(self, **_kwargs: Any) -> str:
        """Build user prompt for retry feedback generation.

        Args:
            verification_result: The verification result dict with issues and suggestions
            attempt_number: Current retry attempt number (1-based)

        Returns:
            User prompt string

        """
        verification_result = _kwargs.get("verification_result", {})
        attempt_number = _kwargs.get("attempt_number", 1)

        prompt_parts = [
            f"Verification Result (Attempt {attempt_number}):\n{json.dumps(verification_result, indent=2)}",
            "\nGenerate clear, actionable feedback for the next retry attempt.",
        ]

        return "\n".join(prompt_parts)

    def _format_single_example(self, example: dict[str, Any]) -> str:
        """Format a single example for retry feedback generation."""
        return f"""Verification Result: {json.dumps(example.get("verification", {}), indent=2)}
Generated Feedback: {example.get("feedback", "")}"""


__all__ = ["RetryFeedbackPromptTemplate"]
