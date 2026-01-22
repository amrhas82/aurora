"""Unit tests for Phase 5: Agent Routing."""

import pytest

from aurora_soar.agent_registry import AgentInfo, AgentRegistry
from aurora_soar.phases.route import (
    RouteResult,
    _check_circular_dependencies,
    _extract_capability_from_agent_id,
    _parse_execution_plan,
    _route_single_subgoal,
    _validate_decomposition,
    _validate_routing,
    route_subgoals,
)


@pytest.fixture
def agent_registry():
    """Create an agent registry with test agents."""
    registry = AgentRegistry()

    # Register test agents
    registry.register(
        AgentInfo(
            id="code-analyzer",
            name="Code Analyzer",
            description="Analyzes code structure",
            capabilities=["code", "analysis"],
            agent_type="local",
        ),
    )

    registry.register(
        AgentInfo(
            id="test-runner",
            name="Test Runner",
            description="Runs tests",
            capabilities=["testing", "validation"],
            agent_type="local",
        ),
    )

    registry.register(
        AgentInfo(
            id="refactoring-engine",
            name="Refactoring Engine",
            description="Refactors code",
            capabilities=["code", "refactoring"],
            agent_type="local",
        ),
    )

    return registry


@pytest.fixture
def simple_decomposition():
    """Create a simple valid decomposition."""
    return {
        "goal": "Test simple routing",
        "subgoals": [
            {
                "description": "Analyze code",
                "suggested_agent": "code-analyzer",
                "is_critical": True,
                "depends_on": [],
            },
        ],
        "execution_order": [
            {
                "phase": 1,
                "parallelizable": [0],
                "sequential": [],
            },
        ],
        "expected_tools": ["code_reader"],
    }


@pytest.fixture
def complex_decomposition():
    """Create a complex decomposition with dependencies."""
    return {
        "goal": "Test complex routing with dependencies",
        "subgoals": [
            {
                "description": "Analyze existing code",
                "suggested_agent": "code-analyzer",
                "is_critical": True,
                "depends_on": [],
            },
            {
                "description": "Write tests",
                "suggested_agent": "test-runner",
                "is_critical": True,
                "depends_on": [0],
            },
            {
                "description": "Refactor code",
                "suggested_agent": "refactoring-engine",
                "is_critical": False,
                "depends_on": [0, 1],
            },
        ],
        "execution_order": [
            {
                "phase": 1,
                "parallelizable": [0],
                "sequential": [],
            },
            {
                "phase": 2,
                "parallelizable": [1],
                "sequential": [],
            },
            {
                "phase": 3,
                "parallelizable": [2],
                "sequential": [],
            },
        ],
        "expected_tools": ["code_reader", "test_runner", "code_writer"],
    }


class TestRouteSubgoals:
    """Test the main route_subgoals function."""

    def test_route_simple_decomposition(self, agent_registry, simple_decomposition):
        """Test routing a simple decomposition with one subgoal."""
        result = route_subgoals(simple_decomposition, agent_registry)

        assert isinstance(result, RouteResult)
        assert len(result.agent_assignments) == 1

        idx, agent = result.agent_assignments[0]
        assert idx == 0
        assert agent.id == "code-analyzer"

        assert len(result.execution_plan) == 1
        assert result.execution_plan[0]["phase"] == 1
        assert len(result.execution_plan[0]["parallelizable"]) == 1

        assert result.routing_metadata["fallback_count"] == 0
        assert result.routing_metadata["capability_searches"] == 0

    def test_route_complex_decomposition(self, agent_registry, complex_decomposition):
        """Test routing a complex decomposition with dependencies."""
        result = route_subgoals(complex_decomposition, agent_registry)

        assert len(result.agent_assignments) == 3
        assert len(result.execution_plan) == 3

        # Check all agents were found
        agent_ids = [agent.id for _, agent in result.agent_assignments]
        assert "code-analyzer" in agent_ids
        assert "test-runner" in agent_ids
        assert "refactoring-engine" in agent_ids

        assert result.routing_metadata["fallback_count"] == 0

    def test_route_with_missing_agent(self, agent_registry, simple_decomposition):
        """Test routing when suggested agent doesn't exist."""
        # Change to non-existent agent
        simple_decomposition["subgoals"][0]["suggested_agent"] = "non-existent-agent"

        result = route_subgoals(simple_decomposition, agent_registry)

        # Should fallback to llm-executor
        idx, agent = result.agent_assignments[0]
        assert agent.id == "llm-executor"
        assert result.routing_metadata["fallback_count"] == 1

    def test_route_with_capability_search(self, agent_registry, simple_decomposition):
        """Test routing falls back to capability search."""
        # Change to agent name with recognizable capability
        simple_decomposition["subgoals"][0]["suggested_agent"] = "code-processor"

        result = route_subgoals(simple_decomposition, agent_registry)

        # Should find agent with "code" capability
        idx, agent = result.agent_assignments[0]
        assert "code" in agent.capabilities
        assert result.routing_metadata["capability_searches"] == 1


class TestValidateDecomposition:
    """Test decomposition validation."""

    def test_validate_valid_decomposition(self, simple_decomposition):
        """Test validation passes for valid decomposition."""
        # Should not raise
        _validate_decomposition(simple_decomposition)

    def test_validate_missing_goal(self, simple_decomposition):
        """Test validation fails when goal is missing."""
        del simple_decomposition["goal"]

        with pytest.raises(ValueError, match="missing required field: goal"):
            _validate_decomposition(simple_decomposition)

    def test_validate_missing_subgoals(self, simple_decomposition):
        """Test validation fails when subgoals are missing."""
        del simple_decomposition["subgoals"]

        with pytest.raises(ValueError, match="missing required field: subgoals"):
            _validate_decomposition(simple_decomposition)

    def test_validate_empty_subgoals(self, simple_decomposition):
        """Test validation fails when subgoals list is empty."""
        simple_decomposition["subgoals"] = []

        with pytest.raises(ValueError, match="has no subgoals"):
            _validate_decomposition(simple_decomposition)

    def test_validate_missing_subgoal_field(self, simple_decomposition):
        """Test validation fails when subgoal is missing required field."""
        del simple_decomposition["subgoals"][0]["suggested_agent"]

        with pytest.raises(ValueError, match="Subgoal 0 missing required field: suggested_agent"):
            _validate_decomposition(simple_decomposition)


class TestRouteSingleSubgoal:
    """Test routing individual subgoals."""

    def test_route_with_direct_lookup(self, agent_registry):
        """Test routing finds agent directly by ID."""
        subgoal = {
            "description": "Test",
            "suggested_agent": "code-analyzer",
            "is_critical": True,
            "depends_on": [],
        }
        metadata = {"fallback_count": 0, "capability_searches": 0, "warnings": []}

        agent = _route_single_subgoal(0, subgoal, agent_registry, metadata)

        assert agent.id == "code-analyzer"
        assert metadata["fallback_count"] == 0
        assert metadata["capability_searches"] == 0

    def test_route_with_capability_search(self, agent_registry):
        """Test routing uses capability search as fallback."""
        subgoal = {
            "description": "Test",
            "suggested_agent": "code-processor",  # Doesn't exist but has "code" capability
            "is_critical": True,
            "depends_on": [],
        }
        metadata = {"fallback_count": 0, "capability_searches": 0, "warnings": []}

        agent = _route_single_subgoal(0, subgoal, agent_registry, metadata)

        assert "code" in agent.capabilities
        assert metadata["capability_searches"] == 1
        assert len(metadata["warnings"]) == 1

    def test_route_with_fallback(self, agent_registry):
        """Test routing uses fallback agent when nothing matches."""
        subgoal = {
            "description": "Test",
            "suggested_agent": "unknown-agent",
            "is_critical": True,
            "depends_on": [],
        }
        metadata = {"fallback_count": 0, "capability_searches": 0, "warnings": []}

        agent = _route_single_subgoal(0, subgoal, agent_registry, metadata)

        assert agent.id == "llm-executor"
        assert metadata["fallback_count"] == 1
        assert len(metadata["warnings"]) == 1


class TestExtractCapability:
    """Test capability extraction from agent IDs."""

    def test_extract_from_hyphenated_id(self):
        """Test extraction from hyphenated agent ID."""
        assert _extract_capability_from_agent_id("code-analyzer") == "code"
        assert _extract_capability_from_agent_id("test-runner") == "test"
        assert _extract_capability_from_agent_id("data-processor-v2") == "data"

    def test_extract_from_single_word(self):
        """Test extraction from single-word agent ID."""
        assert _extract_capability_from_agent_id("analyzer") == "analyzer"

    def test_extract_from_empty(self):
        """Test extraction from empty string."""
        result = _extract_capability_from_agent_id("")
        assert result == "" or result is None


class TestValidateRouting:
    """Test routing validation."""

    def test_validate_valid_routing(self, agent_registry):
        """Test validation passes for valid routing."""
        subgoals = [
            {
                "description": "Test 1",
                "suggested_agent": "code-analyzer",
                "is_critical": True,
                "depends_on": [],
            },
            {
                "description": "Test 2",
                "suggested_agent": "test-runner",
                "is_critical": True,
                "depends_on": [0],
            },
        ]

        agent1 = agent_registry.get("code-analyzer")
        agent2 = agent_registry.get("test-runner")
        agent_assignments = [(0, agent1), (1, agent2)]
        execution_order = [
            {"phase": 1, "parallelizable": [0], "sequential": []},
            {"phase": 2, "parallelizable": [1], "sequential": []},
        ]

        # Should not raise
        _validate_routing(agent_assignments, subgoals, execution_order)

    def test_validate_missing_assignment(self, agent_registry):
        """Test validation fails when subgoal has no assignment."""
        subgoals = [
            {
                "description": "Test 1",
                "suggested_agent": "code-analyzer",
                "is_critical": True,
                "depends_on": [],
            },
            {
                "description": "Test 2",
                "suggested_agent": "test-runner",
                "is_critical": True,
                "depends_on": [],
            },
        ]

        agent1 = agent_registry.get("code-analyzer")
        agent_assignments = [(0, agent1)]  # Missing assignment for subgoal 1
        execution_order = []

        with pytest.raises(RuntimeError, match="not assigned to agents"):
            _validate_routing(agent_assignments, subgoals, execution_order)

    def test_validate_invalid_dependency(self, agent_registry):
        """Test validation fails for invalid dependency index."""
        subgoals = [
            {
                "description": "Test 1",
                "suggested_agent": "code-analyzer",
                "is_critical": True,
                "depends_on": [5],  # Invalid index
            },
        ]

        agent1 = agent_registry.get("code-analyzer")
        agent_assignments = [(0, agent1)]
        execution_order = []

        with pytest.raises(RuntimeError, match="invalid dependency"):
            _validate_routing(agent_assignments, subgoals, execution_order)

    def test_validate_self_dependency(self, agent_registry):
        """Test validation fails for self-dependency."""
        subgoals = [
            {
                "description": "Test 1",
                "suggested_agent": "code-analyzer",
                "is_critical": True,
                "depends_on": [0],  # Self-dependency
            },
        ]

        agent1 = agent_registry.get("code-analyzer")
        agent_assignments = [(0, agent1)]
        execution_order = []

        with pytest.raises(RuntimeError, match="circular dependency on itself"):
            _validate_routing(agent_assignments, subgoals, execution_order)


class TestCheckCircularDependencies:
    """Test circular dependency detection."""

    def test_no_circular_dependencies(self):
        """Test detection passes for valid dependency graph."""
        subgoals = [
            {"description": "A", "depends_on": []},
            {"description": "B", "depends_on": [0]},
            {"description": "C", "depends_on": [0, 1]},
        ]

        # Should not raise
        _check_circular_dependencies(subgoals)

    def test_detect_simple_cycle(self):
        """Test detection fails for simple cycle."""
        subgoals = [
            {"description": "A", "depends_on": [1]},
            {"description": "B", "depends_on": [0]},
        ]

        with pytest.raises(RuntimeError, match="Circular dependency detected"):
            _check_circular_dependencies(subgoals)

    def test_detect_complex_cycle(self):
        """Test detection fails for complex cycle."""
        subgoals = [
            {"description": "A", "depends_on": [1]},
            {"description": "B", "depends_on": [2]},
            {"description": "C", "depends_on": [0]},
        ]

        with pytest.raises(RuntimeError, match="Circular dependency detected"):
            _check_circular_dependencies(subgoals)

    def test_no_dependencies(self):
        """Test detection passes when no dependencies exist."""
        subgoals = [
            {"description": "A", "depends_on": []},
            {"description": "B", "depends_on": []},
            {"description": "C", "depends_on": []},
        ]

        # Should not raise
        _check_circular_dependencies(subgoals)


class TestParseExecutionPlan:
    """Test execution plan parsing."""

    def test_parse_simple_plan(self):
        """Test parsing a simple execution plan."""
        execution_order = [
            {"phase": 1, "parallelizable": [0], "sequential": []},
        ]
        subgoals = [
            {
                "description": "Test subgoal",
                "is_critical": True,
            },
        ]

        result = _parse_execution_plan(execution_order, subgoals)

        assert len(result) == 1
        assert result[0]["phase"] == 1
        assert len(result[0]["parallelizable"]) == 1
        assert result[0]["parallelizable"][0]["subgoal_index"] == 0
        assert result[0]["parallelizable"][0]["description"] == "Test subgoal"
        assert result[0]["parallelizable"][0]["is_critical"] is True

    def test_parse_complex_plan(self):
        """Test parsing a complex execution plan."""
        execution_order = [
            {"phase": 1, "parallelizable": [0, 1], "sequential": []},
            {"phase": 2, "parallelizable": [], "sequential": [2]},
        ]
        subgoals = [
            {"description": "Subgoal 0", "is_critical": True},
            {"description": "Subgoal 1", "is_critical": False},
            {"description": "Subgoal 2", "is_critical": True},
        ]

        result = _parse_execution_plan(execution_order, subgoals)

        assert len(result) == 2
        assert len(result[0]["parallelizable"]) == 2
        assert len(result[0]["sequential"]) == 0
        assert len(result[1]["parallelizable"]) == 0
        assert len(result[1]["sequential"]) == 1

    def test_parse_handles_out_of_bounds(self):
        """Test parsing handles out-of-bounds subgoal indices."""
        execution_order = [
            {"phase": 1, "parallelizable": [0, 5], "sequential": []},  # 5 is out of bounds
        ]
        subgoals = [
            {"description": "Subgoal 0", "is_critical": True},
        ]

        result = _parse_execution_plan(execution_order, subgoals)

        # Should only include valid index
        assert len(result[0]["parallelizable"]) == 1
        assert result[0]["parallelizable"][0]["subgoal_index"] == 0


class TestRouteResultToDict:
    """Test RouteResult serialization."""

    def test_to_dict(self, agent_registry):
        """Test RouteResult converts to dictionary correctly."""
        agent1 = agent_registry.get("code-analyzer")
        agent2 = agent_registry.get("test-runner")

        result = RouteResult(
            agent_assignments=[(0, agent1), (1, agent2)],
            execution_plan=[
                {"phase": 1, "parallelizable": [], "sequential": []},
            ],
            routing_metadata={"fallback_count": 0, "warnings": []},
        )

        result_dict = result.to_dict()

        assert "agent_assignments" in result_dict
        assert "execution_plan" in result_dict
        assert "routing_metadata" in result_dict

        assert len(result_dict["agent_assignments"]) == 2
        assert result_dict["agent_assignments"][0]["agent_id"] == "code-analyzer"
        assert result_dict["agent_assignments"][1]["agent_id"] == "test-runner"
