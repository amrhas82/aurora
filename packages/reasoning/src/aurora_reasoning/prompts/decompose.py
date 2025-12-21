"""Query decomposition prompt template with JSON schema."""

import json
from typing import Any, Dict

from . import PromptTemplate


class DecomposePromptTemplate(PromptTemplate):
    """Prompt template for query decomposition into subgoals.

    Decomposes complex queries into actionable subgoals with agent routing
    and execution order.
    """

    def __init__(self):
        super().__init__(name="decompose", version="1.0")

    def build_system_prompt(self, **kwargs: Any) -> str:
        """Build system prompt for query decomposition."""
        return """You are a query decomposition expert for a code reasoning system.

Your task is to break down complex queries into concrete, actionable subgoals that can be
executed by specialized agents.

For each subgoal, specify:
1. A clear, specific goal statement
2. The suggested agent to execute it (from available agents)
3. Whether the subgoal is critical to the overall query
4. Dependencies on other subgoals (by index)

Organize subgoals into an execution order, marking which can run in parallel.

Available agent types: code-analyzer, test-runner, refactoring-engine, documentation-generator,
dependency-tracker, security-scanner, llm-executor (general purpose)

You MUST respond with valid JSON only. Use this exact schema:
{
  "goal": "High-level goal summarizing what we're trying to achieve",
  "subgoals": [
    {
      "description": "Specific subgoal description",
      "suggested_agent": "agent-name",
      "is_critical": true/false,
      "depends_on": [0, 1]  // indices of prerequisite subgoals
    }
  ],
  "execution_order": [
    {
      "phase": 1,
      "parallelizable": [0, 1],  // subgoal indices that can run in parallel
      "sequential": [2]  // subgoals that must run after this phase
    }
  ],
  "expected_tools": ["list", "of", "expected", "tool", "types"]
}"""

    def build_user_prompt(self, **kwargs: Any) -> str:
        """Build user prompt for query decomposition.

        Args:
            query: The user query to decompose
            context_summary: Optional summary of retrieved context
            available_agents: Optional list of available agent names
            retry_feedback: Optional feedback from previous decomposition attempt

        Returns:
            User prompt string
        """
        query = kwargs.get("query", "")
        context_summary = kwargs.get("context_summary")
        available_agents = kwargs.get("available_agents", [])
        retry_feedback = kwargs.get("retry_feedback")

        prompt_parts = [f"Query: {query}"]

        if context_summary:
            prompt_parts.append(f"\nRelevant Context Summary:\n{context_summary}")

        if available_agents:
            prompt_parts.append(f"\nAvailable Agents: {', '.join(available_agents)}")

        if retry_feedback:
            prompt_parts.append(
                f"\n⚠️ Previous decomposition had issues. Feedback:\n{retry_feedback}\n"
                "Please revise your decomposition to address these concerns."
            )

        prompt_parts.append("\nDecompose this query into actionable subgoals in JSON format.")

        return "\n".join(prompt_parts)

    def _format_single_example(self, example: Dict[str, Any]) -> str:
        """Format a single example for query decomposition.

        Args:
            example: Dict with 'query' and 'decomposition' keys

        Returns:
            Formatted example string
        """
        decomposition = example.get("decomposition", {})
        return f"""Query: {example['query']}

Decomposition: {json.dumps(decomposition, indent=2)}"""


__all__ = ["DecomposePromptTemplate"]
