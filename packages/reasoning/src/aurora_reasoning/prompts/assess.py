"""Complexity assessment prompt template (Tier 2 LLM verification)."""

import json
from typing import Any

from . import PromptTemplate


class AssessPromptTemplate(PromptTemplate):
    """Prompt template for LLM-based complexity assessment.

    Used when keyword-based assessment is uncertain (confidence <0.8 or score in [0.4, 0.6]).
    LLM provides final complexity classification.
    """

    def __init__(self) -> None:
        super().__init__(name="assess", version="1.0")

    def build_system_prompt(self, **_kwargs: Any) -> str:
        """Build system prompt for complexity assessment."""
        return """You are a query complexity analyzer for a code reasoning system.

Your task is to classify user queries into one of four complexity levels:
- SIMPLE: Direct factual questions, single-file lookups, straightforward queries
- MEDIUM: Multi-step reasoning, cross-file references, moderate analysis
- COMPLEX: Deep analysis, architectural understanding, multi-component interactions
- CRITICAL: Strategic decisions, large-scale refactoring, system-wide impact

Consider:
1. Number of steps required
2. Amount of context needed
3. Depth of reasoning required
4. Number of files/components involved
5. Risk and impact of the query

You MUST respond with valid JSON only. Use this exact format:
{
  "complexity": "SIMPLE|MEDIUM|COMPLEX|CRITICAL",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of your classification"
}"""

    def build_user_prompt(self, **_kwargs: Any) -> str:
        """Build user prompt for complexity assessment.

        Args:
            query: The user query to assess
            keyword_result: Optional keyword classification result (dict with complexity, score, confidence)

        Returns:
            User prompt string

        """
        query = _kwargs.get("query", "")
        keyword_result = _kwargs.get("keyword_result")

        prompt_parts = [f"Query to assess: {query}"]

        if keyword_result:
            prompt_parts.append(
                f"\nKeyword-based classification: {keyword_result.get('complexity')} "
                f"(score: {keyword_result.get('score'):.2f}, confidence: {keyword_result.get('confidence'):.2f})",
            )
            prompt_parts.append(
                "\nThe keyword classifier was uncertain. Please provide the final classification.",
            )

        prompt_parts.append("\nProvide your complexity assessment in JSON format.")

        return "\n".join(prompt_parts)

    def _format_single_example(self, example: dict[str, Any]) -> str:
        """Format a single example for complexity assessment.

        Args:
            example: Dict with 'query', 'complexity', and 'reasoning' keys

        Returns:
            Formatted example string

        """
        return f"""Query: {example["query"]}
Classification: {
            json.dumps(
                {
                    "complexity": example["complexity"],
                    "confidence": example.get("confidence", 0.9),
                    "reasoning": example["reasoning"],
                },
                indent=2,
            )
        }"""


__all__ = ["AssessPromptTemplate"]
