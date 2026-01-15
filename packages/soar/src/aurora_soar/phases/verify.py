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
    for i, subgoal in enumerate(subgoals):
        # Use subgoal_index if provided, otherwise fall back to loop index
        subgoal_index = subgoal.get("subgoal_index", i)

        # Validate required fields
        if "description" not in subgoal:
            issues.append(f"Subgoal {subgoal_index} missing 'description' field")
            continue

        # Support both new schema (assigned_agent) and legacy (suggested_agent)
        # New schema: ideal_agent = what SHOULD handle, assigned_agent = best available
        # Legacy: suggested_agent = both ideal and assigned
        assigned_agent = subgoal.get("assigned_agent") or subgoal.get("suggested_agent")

        if not assigned_agent:
            issues.append(
                f"Subgoal {subgoal_index} missing agent field (assigned_agent or suggested_agent)"
            )
            continue

        # Check for gap using AgentRecommender with keyword matching
        # Only spawn ad-hoc if no agent has adequate capability match
        ideal_agent = subgoal.get("ideal_agent")
        ideal_agent_desc = subgoal.get("ideal_agent_desc", "")

        if ideal_agent and ideal_agent_desc:
            # Use AgentRecommender to find best match based on description
            from aurora_cli.planning.agents import AgentRecommender

            recommender = AgentRecommender(manifest=None)  # Will load from cache
            best_agent, match_score = recommender.recommend_for_description(ideal_agent_desc)

            # Gap only if score < 0.15 (no capable agent found)
            if match_score < 0.15:
                # True gap - create placeholder for ad-hoc spawning
                from aurora_soar.agent_registry import AgentInfo

                placeholder_agent = AgentInfo(
                    id=ideal_agent,
                    name=ideal_agent,
                    description=ideal_agent_desc,
                    capabilities=[],
                    agent_type="local",
                    config={"is_spawn": True},
                )
                agent_assignments.append((subgoal_index, placeholder_agent))
                continue
            # else: LLM found a capable agent - trust its assignment
            # Don't overwrite assigned_agent here

        # Check if assigned agent exists (strip @ prefix if present)
        agent_id = assigned_agent.lstrip("@") if assigned_agent else ""
        if agent_id not in agent_map:
            issues.append(f"Agent '{assigned_agent}' not found in registry")
            continue

        # Valid subgoal - create assignment
        agent_info = agent_map[agent_id]
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
