"""Integration tests for end-to-end agent execution flow.

Tests the complete flow from routing to agent execution:
- Route Phase 5: Agent routing with registry lookup
- Collect Phase 6: Agent execution with parallel and sequential execution
"""

import asyncio

import pytest

from aurora_soar.agent_registry import AgentInfo, AgentRegistry
from aurora_soar.phases.route import route_subgoals
from aurora_soar.phases.collect import execute_agents


@pytest.fixture
def agent_registry():
    """Create a registry with test agents."""
    registry = AgentRegistry()

    registry.register(AgentInfo(
        id="code-analyzer",
        name="Code Analyzer",
        description="Analyzes code",
        capabilities=["code", "analysis"],
        agent_type="local",
    ))

    registry.register(AgentInfo(
        id="test-runner",
        name="Test Runner",
        description="Runs tests",
        capabilities=["testing"],
        agent_type="local",
    ))

    registry.register(AgentInfo(
        id="file-writer",
        name="File Writer",
        description="Writes files",
        capabilities=["file", "writing"],
        agent_type="local",
    ))

    return registry


@pytest.fixture
def simple_decomposition():
    """Create a simple decomposition."""
    return {
        "goal": "Simple code analysis task",
        "subgoals": [
            {
                "description": "Analyze the code structure",
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
        "goal": "Complex multi-agent task",
        "subgoals": [
            {
                "description": "Analyze existing code",
                "suggested_agent": "code-analyzer",
                "is_critical": True,
                "depends_on": [],
            },
            {
                "description": "Run existing tests",
                "suggested_agent": "test-runner",
                "is_critical": True,
                "depends_on": [0],
            },
            {
                "description": "Write results to file",
                "suggested_agent": "file-writer",
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
        "expected_tools": ["code_reader", "test_runner", "file_writer"],
    }


@pytest.fixture
def parallel_decomposition():
    """Create a decomposition with parallel tasks."""
    return {
        "goal": "Parallel task execution",
        "subgoals": [
            {
                "description": "Analyze code module A",
                "suggested_agent": "code-analyzer",
                "is_critical": False,
                "depends_on": [],
            },
            {
                "description": "Analyze code module B",
                "suggested_agent": "code-analyzer",
                "is_critical": False,
                "depends_on": [],
            },
            {
                "description": "Analyze code module C",
                "suggested_agent": "code-analyzer",
                "is_critical": False,
                "depends_on": [],
            },
        ],
        "execution_order": [
            {
                "phase": 1,
                "parallelizable": [0, 1, 2],
                "sequential": [],
            },
        ],
        "expected_tools": ["code_reader"],
    }


class TestSimpleExecution:
    """Test simple single-agent execution."""

    @pytest.mark.asyncio
    async def test_route_and_execute_simple(self, agent_registry, simple_decomposition):
        """Test routing and executing a simple decomposition."""
        # Phase 5: Route
        routing = route_subgoals(simple_decomposition, agent_registry)

        assert len(routing.agent_assignments) == 1
        assert routing.agent_assignments[0][1].id == "code-analyzer"

        # Phase 6: Execute
        result = await execute_agents(routing, {})

        assert len(result.agent_outputs) == 1
        assert result.agent_outputs[0].success is True
        assert result.agent_outputs[0].agent_id == "code-analyzer"
        assert result.execution_metadata["phases_executed"] == 1
        assert result.execution_metadata["failed_subgoals"] == 0


class TestComplexExecution:
    """Test complex multi-agent execution."""

    @pytest.mark.asyncio
    async def test_route_and_execute_complex(self, agent_registry, complex_decomposition):
        """Test routing and executing a complex decomposition."""
        # Phase 5: Route
        routing = route_subgoals(complex_decomposition, agent_registry)

        assert len(routing.agent_assignments) == 3
        assert len(routing.execution_plan) == 3

        # Verify all agents found
        agent_ids = [agent.id for _, agent in routing.agent_assignments]
        assert "code-analyzer" in agent_ids
        assert "test-runner" in agent_ids
        assert "file-writer" in agent_ids

        # Phase 6: Execute
        result = await execute_agents(routing, {})

        assert len(result.agent_outputs) == 3
        assert all(o.success for o in result.agent_outputs)
        assert result.execution_metadata["phases_executed"] == 3
        assert result.execution_metadata["failed_subgoals"] == 0


class TestParallelExecution:
    """Test parallel agent execution."""

    @pytest.mark.asyncio
    async def test_parallel_execution_speedup(self, agent_registry, parallel_decomposition):
        """Test that parallel execution is faster than sequential would be."""
        import time

        # Phase 5: Route
        routing = route_subgoals(parallel_decomposition, agent_registry)

        assert len(routing.agent_assignments) == 3
        assert len(routing.execution_plan[0]["parallelizable"]) == 3

        # Phase 6: Execute
        start_time = time.time()
        result = await execute_agents(routing, {})
        elapsed = time.time() - start_time

        assert len(result.agent_outputs) == 3
        assert all(o.success for o in result.agent_outputs)

        # With mock agents taking 0.1s each, parallel execution should be ~0.1s not 0.3s
        assert elapsed < 0.3, f"Parallel execution took {elapsed}s, expected < 0.3s"
        assert result.execution_metadata["parallel_subgoals"] == 3
        assert result.execution_metadata["sequential_subgoals"] == 0


class TestAgentFallback:
    """Test agent fallback behavior."""

    @pytest.mark.asyncio
    async def test_fallback_to_llm_executor(self, agent_registry, simple_decomposition):
        """Test fallback to llm-executor when agent not found."""
        # Change to non-existent agent
        simple_decomposition["subgoals"][0]["suggested_agent"] = "non-existent-agent"

        # Phase 5: Route
        routing = route_subgoals(simple_decomposition, agent_registry)

        # Should fallback to llm-executor
        assert routing.agent_assignments[0][1].id == "llm-executor"
        assert routing.routing_metadata["fallback_count"] == 1

        # Phase 6: Execute
        result = await execute_agents(routing, {})

        # Execution should still succeed with fallback agent
        assert result.agent_outputs[0].success is True


class TestCapabilitySearch:
    """Test capability-based agent search."""

    @pytest.mark.asyncio
    async def test_capability_search_finds_agent(self, agent_registry, simple_decomposition):
        """Test that capability search finds suitable agent."""
        # Change to agent name that doesn't exist but has recognizable capability
        simple_decomposition["subgoals"][0]["suggested_agent"] = "code-processor"

        # Phase 5: Route
        routing = route_subgoals(simple_decomposition, agent_registry)

        # Should find agent with "code" capability
        assigned_agent = routing.agent_assignments[0][1]
        assert "code" in assigned_agent.capabilities
        assert routing.routing_metadata["capability_searches"] == 1

        # Phase 6: Execute
        result = await execute_agents(routing, {})

        assert result.agent_outputs[0].success is True


class TestExecutionMetadata:
    """Test execution metadata collection."""

    @pytest.mark.asyncio
    async def test_metadata_collection(self, agent_registry, complex_decomposition):
        """Test that execution metadata is properly collected."""
        # Phase 5: Route
        routing = route_subgoals(complex_decomposition, agent_registry)

        # Phase 6: Execute
        result = await execute_agents(routing, {})

        # Check metadata structure
        metadata = result.execution_metadata
        assert "total_duration_ms" in metadata
        assert "phases_executed" in metadata
        assert "parallel_subgoals" in metadata
        assert "sequential_subgoals" in metadata
        assert "failed_subgoals" in metadata
        assert "retries" in metadata

        # Check values
        assert metadata["total_duration_ms"] > 0
        assert metadata["phases_executed"] == 3
        assert metadata["parallel_subgoals"] == 3  # All 3 subgoals are in parallelizable
        assert metadata["sequential_subgoals"] == 0
        assert metadata["failed_subgoals"] == 0
        assert metadata["retries"] == 0


class TestAgentOutputs:
    """Test agent output structure."""

    @pytest.mark.asyncio
    async def test_agent_output_structure(self, agent_registry, simple_decomposition):
        """Test that agent outputs have correct structure."""
        # Phase 5: Route
        routing = route_subgoals(simple_decomposition, agent_registry)

        # Phase 6: Execute
        result = await execute_agents(routing, {})

        output = result.agent_outputs[0]

        # Check required fields
        assert hasattr(output, "subgoal_index")
        assert hasattr(output, "agent_id")
        assert hasattr(output, "success")
        assert hasattr(output, "summary")
        assert hasattr(output, "data")
        assert hasattr(output, "confidence")
        assert hasattr(output, "execution_metadata")

        # Check values
        assert output.subgoal_index == 0
        assert output.agent_id == "code-analyzer"
        assert output.success is True
        assert output.summary != ""
        assert 0 <= output.confidence <= 1
        assert "duration_ms" in output.execution_metadata


class TestEndToEndFlow:
    """Test complete end-to-end flow."""

    @pytest.mark.asyncio
    async def test_complete_flow(self, agent_registry, complex_decomposition):
        """Test complete routing and execution flow."""
        # Starting with a verified decomposition...

        # Phase 5: Route subgoals to agents
        routing = route_subgoals(complex_decomposition, agent_registry)

        # Verify routing completed successfully
        assert len(routing.agent_assignments) == 3
        assert routing.routing_metadata["fallback_count"] == 0
        assert len(routing.execution_plan) == 3

        # Phase 6: Execute agents
        execution_result = await execute_agents(routing, {})

        # Verify execution completed successfully
        assert len(execution_result.agent_outputs) == 3
        assert all(o.success for o in execution_result.agent_outputs)
        assert execution_result.execution_metadata["failed_subgoals"] == 0

        # Verify outputs can be serialized
        routing_dict = routing.to_dict()
        assert "agent_assignments" in routing_dict
        assert "execution_plan" in routing_dict

        execution_dict = execution_result.to_dict()
        assert "agent_outputs" in execution_dict
        assert "execution_metadata" in execution_dict

        # Verify all subgoals were executed
        executed_indices = {o.subgoal_index for o in execution_result.agent_outputs}
        assert executed_indices == {0, 1, 2}


class TestMixedExecutionModes:
    """Test mixed parallel and sequential execution."""

    @pytest.mark.asyncio
    async def test_mixed_parallel_sequential(self, agent_registry):
        """Test decomposition with both parallel and sequential phases."""
        decomposition = {
            "goal": "Mixed execution mode test",
            "subgoals": [
                {
                    "description": "Parallel task A",
                    "suggested_agent": "code-analyzer",
                    "is_critical": False,
                    "depends_on": [],
                },
                {
                    "description": "Parallel task B",
                    "suggested_agent": "code-analyzer",
                    "is_critical": False,
                    "depends_on": [],
                },
                {
                    "description": "Sequential task C",
                    "suggested_agent": "test-runner",
                    "is_critical": True,
                    "depends_on": [0, 1],
                },
            ],
            "execution_order": [
                {
                    "phase": 1,
                    "parallelizable": [0, 1],
                    "sequential": [],
                },
                {
                    "phase": 2,
                    "parallelizable": [],
                    "sequential": [2],
                },
            ],
            "expected_tools": ["code_reader", "test_runner"],
        }

        # Phase 5: Route
        routing = route_subgoals(decomposition, agent_registry)
        assert len(routing.execution_plan) == 2

        # Phase 6: Execute
        result = await execute_agents(routing, {})

        assert len(result.agent_outputs) == 3
        assert result.execution_metadata["parallel_subgoals"] == 2
        assert result.execution_metadata["sequential_subgoals"] == 1
        assert result.execution_metadata["phases_executed"] == 2
