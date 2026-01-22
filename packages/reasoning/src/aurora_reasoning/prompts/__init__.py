"""Prompt templates for AURORA reasoning system."""

from abc import ABC, abstractmethod
from typing import Any


class PromptTemplate(ABC):
    """Base class for prompt templates.

    Provides a consistent interface for building prompts with:
    - System and user message construction
    - Few-shot example injection
    - Variable substitution
    - JSON schema enforcement
    """

    def __init__(self, name: str, version: str = "1.0"):
        """Initialize prompt template.

        Args:
            name: Template identifier
            version: Template version for tracking changes

        """
        self.name = name
        self.version = version

    @abstractmethod
    def build_system_prompt(self, **kwargs: Any) -> str:
        """Build the system prompt for this template.

        Args:
            **kwargs: Template-specific parameters

        Returns:
            System prompt string

        """

    @abstractmethod
    def build_user_prompt(self, **kwargs: Any) -> str:
        """Build the user prompt for this template.

        Args:
            **kwargs: Template-specific parameters (query, context, etc.)

        Returns:
            User prompt string

        """

    def build_prompt(
        self,
        *,
        examples: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, str]:
        """Build complete prompt with system and user messages.

        Args:
            examples: Optional few-shot examples to inject
            **kwargs: Template-specific parameters

        Returns:
            Dict with 'system' and 'user' keys

        """
        system_prompt = self.build_system_prompt(**kwargs)
        user_prompt = self.build_user_prompt(**kwargs)

        # Inject few-shot examples into user prompt if provided
        if examples:
            examples_text = self._format_examples(examples)
            user_prompt = f"{examples_text}\n\n{user_prompt}"

        return {
            "system": system_prompt,
            "user": user_prompt,
        }

    def _format_examples(self, examples: list[dict[str, Any]]) -> str:
        """Format few-shot examples for inclusion in prompt.

        Args:
            examples: List of example dicts (implementation-specific structure)

        Returns:
            Formatted examples string

        """
        if not examples:
            return ""

        lines = ["Here are some examples to guide your response:\n"]
        for i, example in enumerate(examples, 1):
            lines.append(f"Example {i}:")
            lines.append(self._format_single_example(example))
            lines.append("")

        return "\n".join(lines)

    @abstractmethod
    def _format_single_example(self, example: dict[str, Any]) -> str:
        """Format a single example for this template.

        Args:
            example: Example dict with template-specific structure

        Returns:
            Formatted example string

        """


__all__ = ["PromptTemplate"]
