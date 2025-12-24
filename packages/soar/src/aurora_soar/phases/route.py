"""Phase 5: Agent Routing.

This module implements the Route phase of the SOAR pipeline, which matches
subgoals to appropriate agents based on capabilities.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from aurora.soar.agent_registry import AgentInfo, AgentRegistry

logger = logging.getLogger(__name__)

__all__ = ["route_subgoals", "RouteResult"]


class RouteResult:
    """Result of agent routing phase.

    Attributes:
        agent_assignments: List of (subgoal_index, agent_info) tuples
        execution_plan: Parsed execution order with phases
        routing_metadata: Metadata about routing decisions (fallbacks, warnings)
    """

    def __init__(
        self,
        agent_assignments: list[tuple[int, AgentInfo]],
        execution_plan: list[dict[str, Any]],
        routing_metadata: dict[str, Any] | None = None,
    ):
        self.agent_assignments = agent_assignments
        self.execution_plan = execution_plan
        self.routing_metadata = routing_metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "agent_assignments": [
                {
                    "subgoal_index": idx,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "agent_type": agent.agent_type,
                }
                for idx, agent in self.agent_assignments
            ],
            "execution_plan": self.execution_plan,
            "routing_metadata": self.routing_metadata,
        }


def route_subgoals(decomposition: dict[str, Any], agent_registry: AgentRegistry) -> RouteResult:
    """Route subgoals to agents based on suggested agents and capabilities.

    This function:
    1. Validates decomposition structure
    2. For each subgoal, looks up suggested agent in registry
    3. Falls back to capability-based search if agent not found
    4. Uses fallback llm-executor agent if no match found
    5. Parses execution order from decomposition
    6. Validates routing (all subgoals assigned, no circular dependencies)

    Args:
        decomposition: Verified decomposition from Phase 4
        agent_registry: AgentRegistry instance for agent lookup

    Returns:
        RouteResult with agent assignments and execution plan

    Raises:
        ValueError: If decomposition structure is invalid
        RuntimeError: If critical routing validation fails
    """
    # Validate decomposition structure
    _validate_decomposition(decomposition)

    subgoals = decomposition["subgoals"]
    execution_order = decomposition.get("execution_order", [])

    agent_assignments: list[tuple[int, AgentInfo]] = []
    routing_metadata: dict[str, Any] = {
        "fallback_count": 0,
        "capability_searches": 0,
        "warnings": [],
    }

    # Route each subgoal to an agent
    for idx, subgoal in enumerate(subgoals):
        agent = _route_single_subgoal(idx, subgoal, agent_registry, routing_metadata)
        agent_assignments.append((idx, agent))

    # Validate routing
    _validate_routing(agent_assignments, subgoals, execution_order)

    # Parse execution plan
    parsed_plan = _parse_execution_plan(execution_order, subgoals)

    logger.info(
        f"Routed {len(agent_assignments)} subgoals to agents "
        f"({routing_metadata['fallback_count']} fallbacks)"
    )

    return RouteResult(
        agent_assignments=agent_assignments,
        execution_plan=parsed_plan,
        routing_metadata=routing_metadata,
    )


def _validate_decomposition(decomposition: dict[str, Any]) -> None:
    """Validate decomposition structure has required fields.

    Args:
        decomposition: Decomposition to validate

    Raises:
        ValueError: If required fields are missing
    """
    required_fields = ["goal", "subgoals", "execution_order", "expected_tools"]
    for field in required_fields:
        if field not in decomposition:
            raise ValueError(f"Decomposition missing required field: {field}")

    if not decomposition["subgoals"]:
        raise ValueError("Decomposition has no subgoals")

    # Validate each subgoal has required fields
    for idx, subgoal in enumerate(decomposition["subgoals"]):
        required_subgoal_fields = [
            "description",
            "suggested_agent",
            "is_critical",
            "depends_on",
        ]
        for field in required_subgoal_fields:
            if field not in subgoal:
                raise ValueError(f"Subgoal {idx} missing required field: {field}")


def _route_single_subgoal(
    idx: int,
    subgoal: dict[str, Any],
    agent_registry: AgentRegistry,
    metadata: dict[str, Any],
) -> AgentInfo:
    """Route a single subgoal to an appropriate agent.

    Tries in order:
    1. Lookup suggested agent by ID
    2. Search by capabilities (derived from subgoal description)
    3. Use fallback llm-executor agent

    Args:
        idx: Subgoal index
        subgoal: Subgoal dictionary with suggested_agent field
        agent_registry: AgentRegistry for lookups
        metadata: Routing metadata to update

    Returns:
        AgentInfo for the assigned agent
    """
    suggested_agent_id = subgoal["suggested_agent"]

    # Try direct lookup first
    agent = agent_registry.get(suggested_agent_id)
    if agent is not None:
        logger.debug(f"Subgoal {idx}: Found suggested agent '{agent.id}'")
        return agent

    # Agent not found, try capability-based search
    logger.warning(
        f"Subgoal {idx}: Suggested agent '{suggested_agent_id}' not found, "
        f"searching by capabilities"
    )
    metadata["capability_searches"] += 1

    # Extract capabilities from agent name (simple heuristic)
    # e.g., "code-analyzer" -> "code" capability
    capability = _extract_capability_from_agent_id(suggested_agent_id)
    if capability:
        agents = agent_registry.find_by_capability(capability)
        if agents:
            agent = agents[0]  # Use first matching agent
            logger.info(f"Subgoal {idx}: Found agent '{agent.id}' with capability '{capability}'")
            metadata["warnings"].append(
                f"Subgoal {idx}: Using '{agent.id}' instead of '{suggested_agent_id}'"
            )
            return agent

    # No suitable agent found, use fallback
    logger.warning(
        f"Subgoal {idx}: No suitable agent found for '{suggested_agent_id}', "
        f"using fallback llm-executor"
    )
    metadata["fallback_count"] += 1
    metadata["warnings"].append(
        f"Subgoal {idx}: Using fallback agent instead of '{suggested_agent_id}'"
    )

    return agent_registry.create_fallback_agent()


def _extract_capability_from_agent_id(agent_id: str) -> str | None:
    """Extract capability hint from agent ID.

    Args:
        agent_id: Agent identifier (e.g., "code-analyzer")

    Returns:
        Capability string (e.g., "code") or None if no clear capability
    """
    # Simple heuristic: take first part of hyphenated ID
    parts = agent_id.split("-")
    if len(parts) > 0:
        return parts[0].lower()
    return None


def _validate_routing(
    agent_assignments: list[tuple[int, AgentInfo]],
    subgoals: list[dict[str, Any]],
    execution_order: list[dict[str, Any]],
) -> None:
    """Validate routing assignments.

    Checks:
    1. All subgoals have agent assignments
    2. No circular dependencies in execution order
    3. Dependencies reference valid subgoal indices

    Args:
        agent_assignments: List of (subgoal_index, agent) tuples
        subgoals: List of subgoal dictionaries
        execution_order: Execution order specification

    Raises:
        RuntimeError: If validation fails
    """
    # Check all subgoals assigned
    assigned_indices = {idx for idx, _ in agent_assignments}
    expected_indices = set(range(len(subgoals)))
    if assigned_indices != expected_indices:
        missing = expected_indices - assigned_indices
        raise RuntimeError(f"Subgoals not assigned to agents: {missing}")

    # Check dependencies are valid
    for idx, subgoal in enumerate(subgoals):
        deps = subgoal.get("depends_on", [])
        for dep_idx in deps:
            if dep_idx < 0 or dep_idx >= len(subgoals):
                raise RuntimeError(f"Subgoal {idx} has invalid dependency: {dep_idx}")
            if dep_idx == idx:
                raise RuntimeError(f"Subgoal {idx} has circular dependency on itself")

    # Check for circular dependencies (simple cycle detection)
    _check_circular_dependencies(subgoals)

    logger.debug("Routing validation passed")


def _check_circular_dependencies(subgoals: list[dict[str, Any]]) -> None:
    """Check for circular dependencies in subgoals.

    Uses depth-first search to detect cycles.

    Args:
        subgoals: List of subgoal dictionaries with depends_on fields

    Raises:
        RuntimeError: If circular dependency detected
    """
    # Build adjacency list
    graph: dict[int, list[int]] = {}
    for idx, subgoal in enumerate(subgoals):
        graph[idx] = subgoal.get("depends_on", [])

    # DFS to detect cycles
    visited = set()
    rec_stack = set()

    def dfs(node: int) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for node in graph:
        if node not in visited and dfs(node):
            raise RuntimeError(f"Circular dependency detected involving subgoal {node}")


def _parse_execution_plan(
    execution_order: list[dict[str, Any]], subgoals: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Parse and enrich execution order with subgoal details.

    Args:
        execution_order: List of execution phase dictionaries
        subgoals: List of subgoal dictionaries

    Returns:
        Enriched execution plan with subgoal descriptions
    """
    parsed_plan: list[dict[str, Any]] = []

    for phase_dict in execution_order:
        phase_num = phase_dict.get("phase", len(parsed_plan) + 1)
        parallelizable = phase_dict.get("parallelizable", [])
        sequential = phase_dict.get("sequential", [])

        # Enrich with subgoal descriptions
        parsed_phase = {
            "phase": phase_num,
            "parallelizable": [
                {
                    "subgoal_index": idx,
                    "description": subgoals[idx]["description"],
                    "is_critical": subgoals[idx]["is_critical"],
                }
                for idx in parallelizable
                if idx < len(subgoals)
            ],
            "sequential": [
                {
                    "subgoal_index": idx,
                    "description": subgoals[idx]["description"],
                    "is_critical": subgoals[idx]["is_critical"],
                }
                for idx in sequential
                if idx < len(subgoals)
            ],
        }
        parsed_plan.append(parsed_phase)

    return parsed_plan
