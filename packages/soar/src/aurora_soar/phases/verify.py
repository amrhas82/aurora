"""Phase 4: Decomposition Verification.

This module implements the Verify phase of the SOAR pipeline, which validates
decompositions and assigns agents in one lightweight pass.

The verify_lite function combines structural validation with agent assignment,
replacing the previous heavy verify_decomposition + route_subgoals workflow.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "verify_lite",
]


def verify_lite(
    decomposition: dict[str, Any],
    available_agents: list[Any],
) -> tuple[bool, list[tuple[int, Any]], list[str]]:
    """Lightweight verification that checks decomposition validity and assigns agents.

    This function replaces the heavy verify_decomposition + route_subgoals workflow.
    It performs basic structural validation and agent assignment in one pass.

    Checks performed:
    1. Decomposition has "subgoals" key
    2. At least one subgoal exists
    3. Each subgoal has required fields (description, suggested_agent)
    4. All suggested agents exist in available_agents
    5. No circular dependencies in subgoal dependency graph

    Args:
        decomposition: Decomposition dict with subgoals and execution strategy
        available_agents: List of AgentInfo objects from registry

    Returns:
        Tuple of (passed, agent_assignments, issues):
        - passed: True if all checks pass, False otherwise
        - agent_assignments: List of (subgoal_index, AgentInfo) tuples for valid subgoals
        - issues: List of issue strings describing validation failures
    """
    issues: list[str] = []
    agent_assignments: list[tuple[int, Any]] = []

    # Check 1: Validate decomposition has "subgoals" key
    if "subgoals" not in decomposition:
        issues.append("Decomposition missing 'subgoals' key")
        return (False, [], issues)

    subgoals = decomposition["subgoals"]

    # Check 2: At least one subgoal required
    if not subgoals or len(subgoals) == 0:
        issues.append("Decomposition must have at least one subgoal")
        return (False, [], issues)

    # Build agent lookup map
    agent_map = {agent.id: agent for agent in available_agents}

    # Check 3 & 4: Validate subgoal structure and agent existence
    for subgoal in subgoals:
        subgoal_index = subgoal.get("subgoal_index")

        # Validate required fields
        if "description" not in subgoal:
            issues.append(f"Subgoal {subgoal_index} missing 'description' field")
            continue

        if "suggested_agent" not in subgoal:
            issues.append(f"Subgoal {subgoal_index} missing 'suggested_agent' field")
            continue

        suggested_agent = subgoal["suggested_agent"]

        # Check if agent exists
        if suggested_agent not in agent_map:
            issues.append(f"Agent '{suggested_agent}' not found in registry")
            continue

        # Valid subgoal - create assignment
        agent_info = agent_map[suggested_agent]
        agent_assignments.append((subgoal_index, agent_info))

    # Check 5: Detect circular dependencies
    circular_issues = _check_circular_deps(subgoals)
    issues.extend(circular_issues)

    # Determine if passed
    passed = len(issues) == 0

    return (passed, agent_assignments, issues)


def _check_circular_deps(subgoals: list[dict[str, Any]]) -> list[str]:
    """Check for circular dependencies in subgoal dependency graph.

    Uses depth-first search to detect cycles in the dependency graph.

    Args:
        subgoals: List of subgoal dicts with 'subgoal_index' and 'depends_on'

    Returns:
        List of issue strings describing circular dependencies found
    """
    issues: list[str] = []

    # Build adjacency list for dependency graph
    graph: dict[int, list[int]] = {}
    for subgoal in subgoals:
        subgoal_index = subgoal.get("subgoal_index")
        depends_on = subgoal.get("depends_on", [])
        graph[subgoal_index] = depends_on

    # DFS to detect cycles
    visited: set[int] = set()
    rec_stack: set[int] = set()

    def has_cycle(node: int) -> bool:
        """DFS helper to detect cycle from given node."""
        visited.add(node)
        rec_stack.add(node)

        # Visit all dependencies
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found a back edge - cycle detected
                return True

        rec_stack.remove(node)
        return False

    # Check each subgoal for cycles
    for subgoal in subgoals:
        subgoal_index = subgoal.get("subgoal_index")
        if subgoal_index not in visited:
            if has_cycle(subgoal_index):
                issues.append(
                    f"Circular dependency detected in subgoal dependency graph involving subgoal {subgoal_index}"
                )
                break  # One cycle detection is enough

    return issues
