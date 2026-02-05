"""Query decomposition logic using LLM-based reasoning.

This module implements the decomposition step of the SOAR pipeline, which breaks
down complex queries into actionable subgoals with agent routing and execution planning.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .prompts.decompose import DecomposePromptTemplate
from .prompts.examples import Complexity, get_loader


if TYPE_CHECKING:
    from .llm_client import LLMClient

__all__ = ["decompose_query", "DecompositionResult"]


class DecompositionResult:
    """Result of query decomposition.

    Attributes:
        goal: High-level goal of the decomposition
        subgoals: List of subgoal dictionaries with description, agent, criticality, dependencies
        execution_order: List of execution phase dictionaries with parallelizable/sequential groups
        expected_tools: List of expected tool types
        raw_response: Raw LLM response text
        prompt_used: Prompt text sent to LLM

    """

    def __init__(
        self,
        goal: str,
        subgoals: list[dict[str, Any]],
        execution_order: list[dict[str, Any]],
        expected_tools: list[str],
        raw_response: str = "",
        prompt_used: str = "",
    ):
        self.goal = goal
        self.subgoals = subgoals
        self.execution_order = execution_order
        self.expected_tools = expected_tools
        self.raw_response = raw_response
        self.prompt_used = prompt_used

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "goal": self.goal,
            "subgoals": self.subgoals,
            "execution_order": self.execution_order,
            "expected_tools": self.expected_tools,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecompositionResult:
        """Create from dictionary representation."""
        return cls(
            goal=data["goal"],
            subgoals=data["subgoals"],
            execution_order=data["execution_order"],
            expected_tools=data["expected_tools"],
        )


def decompose_query(
    llm_client: LLMClient,
    query: str,
    complexity: Complexity,
    context_summary: str | None = None,
    available_agents: list[str] | None = None,
    retry_feedback: str | None = None,
) -> DecompositionResult:
    """Decompose a query into actionable subgoals using LLM reasoning.

    This function:
    1. Loads few-shot examples based on complexity (0/2/4/6 examples)
    2. Builds decomposition prompt with context and available agents
    3. Calls LLM with JSON-only output requirement
    4. Validates and parses the decomposition response
    5. Returns structured DecompositionResult

    Args:
        llm_client: LLM client to use for decomposition
        query: User query to decompose
        complexity: Query complexity level (determines example count)
        context_summary: Optional summary of retrieved context chunks
        available_agents: Optional list of available agent names
        retry_feedback: Optional feedback from previous decomposition attempt

    Returns:
        DecompositionResult with validated decomposition

    Raises:
        ValueError: If LLM response is invalid or missing required fields
        RuntimeError: If LLM call fails after retries

    """
    # Load few-shot examples based on complexity
    examples_loader = get_loader()
    examples = examples_loader.get_examples_by_complexity("example_decompositions.json", complexity)

    # Build prompt using template
    prompt_template = DecomposePromptTemplate()

    # Create prompt with examples
    system_prompt = prompt_template.build_system_prompt(
        available_agents=available_agents or [],
        complexity=complexity.value,  # Pass complexity to enable subgoal limits
    )
    user_prompt = prompt_template.build_user_prompt(
        query=query,
        context_summary=context_summary,
        available_agents=available_agents or [],
        retry_feedback=retry_feedback,
    )

    # Add few-shot examples if any
    if examples:
        examples_text = "\n\n".join(prompt_template._format_single_example(ex) for ex in examples)
        user_prompt = f"Here are some examples:\n\n{examples_text}\n\n---\n\n{user_prompt}"

    # Call LLM with JSON output requirement
    decomposition = llm_client.generate_json(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.2,  # Low temperature for structured output
    )

    # Validate response is a dict (generate_json already parses JSON)
    if not isinstance(decomposition, dict):
        raise ValueError(
            f"LLM returned non-dict response: {type(decomposition)}\n"
            f"Response: {str(decomposition)[:500]}",
        )

    # Validate required fields
    required_fields = ["goal", "subgoals", "execution_order", "expected_tools"]
    missing = [f for f in required_fields if f not in decomposition]
    if missing:
        raise ValueError(
            f"Decomposition missing required fields: {missing}\nResponse: {decomposition}",
        )

    # Validate subgoals structure
    if not isinstance(decomposition["subgoals"], list):
        raise ValueError(f"'subgoals' must be a list, got {type(decomposition['subgoals'])}")

    for i, subgoal in enumerate(decomposition["subgoals"]):
        # New schema: ideal_agent, ideal_agent_desc, assigned_agent
        # Backward compatibility: also accept suggested_agent
        required_subgoal_fields = ["description", "is_critical", "depends_on"]
        missing_sg = [f for f in required_subgoal_fields if f not in subgoal]
        if missing_sg:
            raise ValueError(
                f"Subgoal {i} missing required fields: {missing_sg}\nSubgoal: {subgoal}",
            )

        # Check for new schema fields OR legacy field
        has_new_schema = "ideal_agent" in subgoal and "assigned_agent" in subgoal
        has_legacy_schema = "suggested_agent" in subgoal

        if not has_new_schema and not has_legacy_schema:
            raise ValueError(
                f"Subgoal {i} missing agent fields. Expected 'ideal_agent' + 'assigned_agent' "
                f"(or legacy 'suggested_agent').\nSubgoal: {subgoal}",
            )

        # If legacy schema, convert to new schema for downstream compatibility
        if has_legacy_schema and not has_new_schema:
            subgoal["ideal_agent"] = subgoal["suggested_agent"]
            subgoal["ideal_agent_desc"] = ""
            subgoal["assigned_agent"] = subgoal["suggested_agent"]

        # Validate match_quality field (new in v1.1)
        match_quality = subgoal.get("match_quality", "acceptable")  # Default for backward compat
        valid_qualities = ["excellent", "acceptable", "insufficient"]
        if match_quality not in valid_qualities:
            raise ValueError(
                f"Subgoal {i} has invalid match_quality '{match_quality}'. "
                f"Must be one of: {valid_qualities}\nSubgoal: {subgoal}",
            )
        # Ensure field exists for downstream consumers
        subgoal["match_quality"] = match_quality

    # Validate execution_order structure
    if not isinstance(decomposition["execution_order"], list):
        raise ValueError(
            f"'execution_order' must be a list, got {type(decomposition['execution_order'])}",
        )

    for i, phase in enumerate(decomposition["execution_order"]):
        if "phase" not in phase:
            raise ValueError(f"Execution phase {i} missing 'phase' field: {phase}")
        if "parallelizable" not in phase and "sequential" not in phase:
            raise ValueError(
                f"Execution phase {i} must have 'parallelizable' or 'sequential': {phase}",
            )

    # Create result
    full_prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"

    return DecompositionResult(
        goal=decomposition["goal"],
        subgoals=decomposition["subgoals"],
        execution_order=decomposition["execution_order"],
        expected_tools=decomposition.get("expected_tools", []),
        raw_response=json.dumps(decomposition),
        prompt_used=full_prompt,
    )
