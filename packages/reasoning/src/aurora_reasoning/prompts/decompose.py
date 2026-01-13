"""Query decomposition prompt template with JSON schema."""

import json
from typing import Any

from . import PromptTemplate


class DecomposePromptTemplate(PromptTemplate):
    """Prompt template for query decomposition into subgoals.

    Decomposes complex queries into actionable subgoals with agent routing
    and execution order.
    """

    def __init__(self) -> None:
        super().__init__(name="decompose", version="1.0")

    def build_system_prompt(self, **kwargs: Any) -> str:
        """Build system prompt for query decomposition."""
        available_agents = kwargs.get("available_agents", [])

        if available_agents:
            agents_text = f"""Available agents: {', '.join(available_agents)}

For each subgoal, you must specify TWO agents:
1. ideal_agent: The IDEAL agent for this task (any name, even if not available)
2. assigned_agent: The BEST AVAILABLE agent from the list above

Common ideal agents (create if needed):
- creative-writer: story editing, narrative, creative writing
- data-analyst: data analysis, visualization, statistics
- ux-designer: UI/UX design, wireframes, prototypes
- devops-engineer: CI/CD, infrastructure, deployment
- security-expert: security audits, vulnerability analysis

Common available agents:
- business-analyst: research, market analysis, competitive intelligence
- master: general tasks, multi-domain work
- full-stack-dev: code implementation, debugging, refactoring
- holistic-architect: architecture, system design, API design
- product-manager/product-owner: product tasks, requirements"""
        else:
            agents_text = """No agents available.

For ideal_agent: specify the ideal agent name for the task (any domain)
For assigned_agent: use 'master' as fallback for all subgoals"""

        return f"""You are a query decomposition expert for a code reasoning system.

Your task is to break down complex queries into concrete, actionable subgoals that can be
executed by specialized agents.

For each subgoal, specify:
1. A clear, specific goal statement
2. The IDEAL agent (unconstrained - what SHOULD handle this task)
3. A brief description of the ideal agent's capabilities
4. The ASSIGNED agent (from available list - best match we have)
5. Whether the subgoal is critical to the overall query
6. Dependencies on other subgoals (by index)

{agents_text}

You MUST respond with valid JSON only. Use this exact schema:
{{
  "goal": "High-level goal summarizing what we're trying to achieve",
  "subgoals": [
    {{
      "description": "Specific subgoal description",
      "ideal_agent": "agent-that-should-handle-this",
      "ideal_agent_desc": "Brief description of ideal agent capabilities",
      "assigned_agent": "best-available-agent",
      "is_critical": true/false,
      "depends_on": [0, 1]  // indices of prerequisite subgoals
    }}
  ],
  "execution_order": [
    {{
      "phase": 1,
      "parallelizable": [0, 1],  // subgoal indices that can run in parallel
      "sequential": [2]  // subgoals that must run after this phase
    }}
  ],
  "expected_tools": ["list", "of", "expected", "tool", "types"]
}}"""

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

    def _format_single_example(self, example: dict[str, Any]) -> str:
        """Format a single example for query decomposition.

        Args:
            example: Dict with 'query' and 'decomposition' keys

        Returns:
            Formatted example string
        """
        decomposition = example.get("decomposition", {})
        return f"""Query: {example["query"]}

Decomposition: {json.dumps(decomposition, indent=2)}"""


__all__ = ["DecomposePromptTemplate"]
