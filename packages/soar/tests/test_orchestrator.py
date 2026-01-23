"""Tests for SOAR orchestrator."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aurora_soar.orchestrator import SOAROrchestrator

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_store():
    """Mock Store for testing."""
    store = MagicMock()
    return store


@pytest.fixture
def mock_agent_registry():
    """Mock AgentRegistry for testing."""
    registry = MagicMock()

    # Mock an agent
    agent = MagicMock()
    agent.id = "test-agent"
    agent.name = "Test Agent"
    agent.capabilities = ["testing"]

    registry.list_agents.return_value = [agent]
    registry.get_agent.return_value = agent

    return registry


@pytest.fixture
def mock_config():
    """Mock Config for testing."""
    config = MagicMock()
    config.budget = MagicMock()
    config.budget.max_cost_usd = 1.0
    return config


@pytest.fixture
def mock_llm():
    """Mock LLMClient for testing."""
    llm = MagicMock()
    llm.generate = AsyncMock(return_value="Mock response")
    return llm


@pytest.fixture
def orchestrator(mock_store, mock_agent_registry, mock_config, mock_llm):
    """Create SOAROrchestrator instance for testing."""
    return SOAROrchestrator(
        store=mock_store,
        config=mock_config,
        reasoning_llm=mock_llm,
        solving_llm=mock_llm,
        agent_registry=mock_agent_registry,
    )


# ============================================================================
# Smoke Tests
# ============================================================================


def test_imports():
    """Test that basic imports work."""
    from aurora_soar import orchestrator
    from aurora_soar.orchestrator import SOAROrchestrator

    assert orchestrator is not None
    assert SOAROrchestrator is not None


def test_orchestrator_creation(orchestrator):
    """Test that SOAROrchestrator can be created."""
    assert orchestrator is not None
    assert hasattr(orchestrator, "store")
    assert hasattr(orchestrator, "agent_registry")


# ============================================================================
# Agent Discovery Integration Tests (Task 2.3)
# ============================================================================


def test_orchestrator_uses_manifest_manager(mock_store, mock_config, mock_llm):
    """Test that orchestrator can use ManifestManager instead of AgentRegistry.

    Verifies that when no agent_registry is provided, the orchestrator
    initializes using the discovery_adapter's ManifestManager.
    """
    from unittest.mock import Mock, patch

    from aurora_cli.agent_discovery.models import (
        AgentCategory,
        AgentInfo,
        AgentManifest,
        ManifestStats,
    )

    # Create sample agents for discovery system
    sample_agents = [
        AgentInfo(
            id="test-agent",
            role="Test Agent",
            goal="Execute test tasks",
            category=AgentCategory.ENG,
            skills=["testing"],
        ),
    ]

    sample_manifest = AgentManifest(
        version="1.0.0",
        sources=["/home/user/.aurora/agents"],
        agents=sample_agents,
        stats=ManifestStats(total=1, by_category={"eng": 1}, malformed_files=0),
    )

    # Mock the discovery adapter
    with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
        mock_instance = Mock()
        mock_instance.get_or_refresh.return_value = sample_manifest
        MockManager.return_value = mock_instance

        # Create orchestrator with agent_registry=None (will use discovery)
        orchestrator = SOAROrchestrator(
            store=mock_store,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
            agent_registry=None,  # Should trigger discovery_adapter usage
        )

        # Verify orchestrator uses discovery adapter
        assert orchestrator._use_discovery is True
        assert hasattr(orchestrator, "_manifest_manager")
        # When agent_registry is None, orchestrator should use discovery_adapter functions


def test_orchestrator_fallback_agent_from_discovery(mock_store, mock_config, mock_llm):
    """Test that orchestrator can create fallback agent using discovery system.

    Verifies that when an agent is not found, the orchestrator can use
    the discovery adapter's fallback agent creation.
    """
    from unittest.mock import Mock, patch

    from aurora_cli.agent_discovery.models import AgentManifest, ManifestStats

    # Create empty manifest (no agents)
    empty_manifest = AgentManifest(
        version="1.0.0",
        sources=[],
        agents=[],
        stats=ManifestStats(total=0, by_category={}, malformed_files=0),
    )

    with patch("aurora_soar.discovery_adapter.ManifestManager") as MockManager:
        mock_instance = Mock()
        mock_instance.get_or_refresh.return_value = empty_manifest
        MockManager.return_value = mock_instance

        # Create orchestrator with agent_registry=None
        orchestrator = SOAROrchestrator(
            store=mock_store,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
            agent_registry=None,
        )

        # Test that fallback agent can be created from discovery
        fallback = orchestrator._get_or_create_fallback_agent()
        assert fallback is not None
        assert fallback.id == "llm-executor"
        assert fallback.name == "Default LLM Executor"


# ============================================================================
# Orchestrator Simplification Tests (Task 5.1)
# ============================================================================


class TestOrchestratorSimplified:
    """Tests for simplified orchestrator without route phase."""

    def test_no_route_phase_in_execution(self, orchestrator, monkeypatch):
        """Test that route phase is skipped in simplified orchestrator.

        Verifies that the orchestrator no longer calls _phase5_route()
        and proceeds directly from verify to collect.
        """
        # Mock all phases to track calls
        phase_calls = []

        def track_phase(phase_name):
            def wrapper(*_args, **_kwargs):
                phase_calls.append(phase_name)
                # Return minimal mock objects based on phase
                if phase_name == "assess":
                    return {"complexity": "MEDIUM", "assessment": "test"}
                if phase_name == "retrieve":
                    return {"code_chunks": [], "reasoning_chunks": []}
                if phase_name == "decompose":
                    return {"decomposition": {"subgoals": [{"goal": "test"}]}}
                if phase_name == "verify":
                    # Return verify_lite format: (passed, agent_assignments, issues)
                    return {"final_verdict": "PASS", "agent_assignments": []}
                if phase_name == "collect":
                    from aurora_soar.phases.collect import CollectResult

                    return CollectResult([], {}, [], [])
                if phase_name == "synthesize":
                    from aurora_soar.phases.synthesize import SynthesisResult

                    return SynthesisResult("answer", 0.9, [], {}, {})
                if phase_name == "record":
                    from aurora_soar.phases.record import RecordResult

                    return RecordResult(False, None, False, 0.0, {})
                return {}

            return wrapper

        # Patch phase methods (updated phase numbers for simplified orchestrator)
        monkeypatch.setattr(orchestrator, "_phase1_assess", track_phase("assess"))
        monkeypatch.setattr(orchestrator, "_phase2_retrieve", track_phase("retrieve"))
        monkeypatch.setattr(orchestrator, "_phase3_decompose", track_phase("decompose"))
        monkeypatch.setattr(orchestrator, "_get_available_agents", lambda: [])

        # Mock verify_lite to track verify phase
        from aurora_soar.phases import verify

        def mock_verify_lite(*_args, **_kwargs):
            phase_calls.append("verify")
            return (True, [], [])  # passed, agent_assignments, issues

        monkeypatch.setattr(verify, "verify_lite", mock_verify_lite)

        monkeypatch.setattr(orchestrator, "_phase5_collect", track_phase("collect"))
        monkeypatch.setattr(orchestrator, "_phase6_synthesize", track_phase("synthesize"))
        monkeypatch.setattr(orchestrator, "_phase7_record", track_phase("record"))
        monkeypatch.setattr(
            orchestrator,
            "_phase8_respond",
            lambda *_args, **_kwargs: {"answer": "test", "metadata": {}},
        )

        # Execute query
        orchestrator.execute("test query")

        # Verify route phase was NOT called
        assert "route" not in phase_calls
        # Verify collect comes after verify (no route in between)
        verify_idx = phase_calls.index("verify")
        collect_idx = phase_calls.index("collect")
        assert collect_idx == verify_idx + 1

    def test_verify_lite_called_instead(self, orchestrator, monkeypatch):
        """Test that verify_lite is called instead of verify_decomposition.

        Verifies that the orchestrator uses the new lightweight verification
        function that combines validation and agent assignment.
        """
        verify_lite_called = []

        def mock_verify_lite(decomposition, available_agents):
            verify_lite_called.append((decomposition, available_agents))
            # Return format: (passed, agent_assignments, issues)
            return (True, [], [])

        # Patch verify_lite in the orchestrator's verify phase
        from aurora_soar.phases import verify

        monkeypatch.setattr(verify, "verify_lite", mock_verify_lite)

        # Mock other phases minimally
        monkeypatch.setattr(orchestrator, "_phase1_assess", lambda _: {"complexity": "MEDIUM"})
        monkeypatch.setattr(orchestrator, "_phase2_retrieve", lambda _q, _c: {"code_chunks": []})
        monkeypatch.setattr(
            orchestrator,
            "_phase3_decompose",
            lambda _q, _ctx, _c: {"decomposition": {"subgoals": []}},
        )
        monkeypatch.setattr(
            orchestrator,
            "_phase5_collect",
            lambda *_args: MagicMock(agent_outputs=[], execution_metadata={}, fallback_agents=[]),
        )
        monkeypatch.setattr(
            orchestrator,
            "_phase6_synthesize",
            lambda *_args: MagicMock(answer="test", confidence=0.9, to_dict=lambda: {}),
        )
        monkeypatch.setattr(
            orchestrator,
            "_phase7_record",
            lambda *_args: MagicMock(cached=False, to_dict=lambda: {}),
        )
        monkeypatch.setattr(orchestrator, "_phase8_respond", lambda *_args: {"answer": "test"})

        # Execute query
        orchestrator.execute("test query")

        # Verify verify_lite was called
        assert len(verify_lite_called) > 0

    def test_auto_retry_on_verification_failure(self, orchestrator, monkeypatch):
        """Test that orchestrator retries decompose on verification failure.

        Verifies that when verify_lite fails, the orchestrator generates
        retry feedback and calls decompose again.
        """
        from aurora_soar.phases import verify

        decompose_calls = []
        verify_calls = []

        def mock_decompose(_query, _context, _complexity, retry_feedback=None):
            decompose_calls.append({"retry_feedback": retry_feedback})
            return {"decomposition": {"subgoals": []}}

        def mock_verify_lite(_decomposition, _available_agents):
            verify_calls.append(True)
            if len(verify_calls) == 1:
                # First call fails
                return (
                    False,
                    [],
                    ["missing agent"],
                )  # passed=False, agent_assignments=[], issues=[...]
            # Second call passes
            return (True, [], [])  # passed=True, agent_assignments=[], issues=[]

        monkeypatch.setattr(orchestrator, "_phase1_assess", lambda _: {"complexity": "MEDIUM"})
        monkeypatch.setattr(orchestrator, "_phase2_retrieve", lambda _q, _c: {"code_chunks": []})
        monkeypatch.setattr(orchestrator, "_phase3_decompose", mock_decompose)
        monkeypatch.setattr(verify, "verify_lite", mock_verify_lite)
        monkeypatch.setattr(
            orchestrator,
            "_phase5_collect",
            lambda *_args: MagicMock(agent_outputs=[], execution_metadata={}, fallback_agents=[]),
        )
        monkeypatch.setattr(
            orchestrator,
            "_phase6_synthesize",
            lambda *_args: MagicMock(answer="test", confidence=0.9, to_dict=lambda: {}),
        )
        monkeypatch.setattr(
            orchestrator,
            "_phase7_record",
            lambda *_args: MagicMock(cached=False, to_dict=lambda: {}),
        )
        monkeypatch.setattr(orchestrator, "_phase8_respond", lambda *_args: {"answer": "test"})

        # Execute query
        orchestrator.execute("test query")

        # Verify decompose was called twice (initial + retry)
        assert len(decompose_calls) >= 2
        # Verify first call had no retry_feedback
        assert decompose_calls[0]["retry_feedback"] is None
        # Verify second call had retry_feedback
        assert decompose_calls[1]["retry_feedback"] is not None

    def test_streaming_progress_callback_wired(self, orchestrator, monkeypatch):
        """Test that progress callback reaches collect phase.

        Verifies that the orchestrator creates and wires a progress callback
        to the collect phase for streaming progress updates.
        """
        from aurora_soar.phases import verify

        progress_messages = []

        def mock_execute_agents(
            _agent_assignments, _subgoals, _context, on_progress=None, **_kwargs
        ):
            """Mock execute_agents that calls progress callback."""
            if on_progress:
                on_progress("[Agent 1/2] test-agent: Starting...")
                on_progress("[Agent 1/2] test-agent: Completed (1.2s)")
            from aurora_soar.phases.collect import CollectResult

            return CollectResult([], {}, [], [])

        # Capture progress output
        def capture_progress(msg):
            progress_messages.append(msg)

        # Mock phases
        monkeypatch.setattr(orchestrator, "_phase1_assess", lambda _: {"complexity": "MEDIUM"})
        monkeypatch.setattr(orchestrator, "_phase2_retrieve", lambda _q, _c: {"code_chunks": []})
        monkeypatch.setattr(
            orchestrator,
            "_phase3_decompose",
            lambda _q, _ctx, _c: {"decomposition": {"subgoals": []}},
        )
        # Mock verify_lite instead of _phase4_verify (which no longer exists)
        monkeypatch.setattr(
            verify,
            "verify_lite",
            lambda _decomposition, _available_agents: (
                True,
                [],
                [],
            ),  # passed=True, agent_assignments=[], issues=[]
        )

        # Mock collect phase to use our mock execute_agents
        from aurora_soar.phases import collect

        monkeypatch.setattr(collect, "execute_agents", AsyncMock(side_effect=mock_execute_agents))

        monkeypatch.setattr(
            orchestrator,
            "_phase6_synthesize",
            lambda *_args: MagicMock(answer="test", confidence=0.9, to_dict=lambda: {}),
        )
        monkeypatch.setattr(
            orchestrator,
            "_phase7_record",
            lambda *_args: MagicMock(cached=False, to_dict=lambda: {}),
        )
        monkeypatch.setattr(orchestrator, "_phase8_respond", lambda *_args: {"answer": "test"})

        # TODO: Once orchestrator has _get_progress_callback(), wire it here
        # For now, test will fail (RED phase) until implementation

        # Execute query
        orchestrator.execute("test query")

    def test_lightweight_record_used(self, orchestrator, monkeypatch):
        """Test that record_pattern_lightweight is called instead of record_pattern.

        Verifies that the orchestrator uses the new lightweight recording
        function with minimal overhead.
        """
        record_lightweight_called = []

        def mock_record_lightweight(_store, query, _synthesis_result, log_path):
            record_lightweight_called.append((query, log_path))
            from aurora_soar.phases.record import RecordResult

            return RecordResult(True, "chunk-123", True, 0.2, {})

        # Patch record_pattern_lightweight
        from aurora_soar.phases import record

        monkeypatch.setattr(record, "record_pattern_lightweight", mock_record_lightweight)

        # Mock phases (support retry_feedback parameter in decompose)
        monkeypatch.setattr(orchestrator, "_phase1_assess", lambda _: {"complexity": "MEDIUM"})
        monkeypatch.setattr(orchestrator, "_phase2_retrieve", lambda _q, _c: {"code_chunks": []})
        monkeypatch.setattr(
            orchestrator,
            "_phase3_decompose",
            lambda _q, _ctx, _c, _retry_feedback=None: {
                "decomposition": {"subgoals": [{"goal": "test"}]},
            },
        )
        monkeypatch.setattr(orchestrator, "_get_available_agents", lambda: [])

        # Mock verify_lite directly
        from aurora_soar.phases import verify

        monkeypatch.setattr(verify, "verify_lite", lambda *_args, **_kwargs: (True, [], []))
        monkeypatch.setattr(
            orchestrator,
            "_phase5_collect",
            lambda *_args: MagicMock(agent_outputs=[], execution_metadata={}, fallback_agents=[]),
        )
        monkeypatch.setattr(
            orchestrator,
            "_phase6_synthesize",
            lambda *_args: MagicMock(
                answer="test",
                confidence=0.9,
                summary="test",
                to_dict=lambda: {},
            ),
        )

        # Mock _phase7_record to call our lightweight version
        def mock_phase7_record(query, synthesis_result, _log_path):
            """Mock that calls the actual record_pattern_lightweight."""
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as tmp:
                temp_log_path = tmp.name
            result = record.record_pattern_lightweight(
                orchestrator.store,
                query,
                synthesis_result,
                temp_log_path,
            )
            return result

        monkeypatch.setattr(orchestrator, "_phase7_record", mock_phase7_record)
        monkeypatch.setattr(orchestrator, "_phase8_respond", lambda *_args: {"answer": "test"})

        # Execute query
        orchestrator.execute("test query")

        # Verify record_pattern_lightweight was called
        assert len(record_lightweight_called) > 0

    def test_agent_assignments_passed_to_collect(self, orchestrator, monkeypatch):
        """Test that agent_assignments list is passed to collect phase.

        Verifies that the orchestrator passes the agent assignments list
        (not RouteResult) directly to execute_agents.
        """
        from aurora_soar.phases import verify

        collect_calls = []

        def mock_execute_agents(agent_assignments, subgoals, _context, **_kwargs):
            collect_calls.append({"agent_assignments": agent_assignments, "subgoals": subgoals})
            from aurora_soar.phases.collect import CollectResult

            return CollectResult([], {}, [], [])

        # Mock phases
        monkeypatch.setattr(orchestrator, "_phase1_assess", lambda _: {"complexity": "MEDIUM"})
        monkeypatch.setattr(orchestrator, "_phase2_retrieve", lambda _q, _c: {"code_chunks": []})
        monkeypatch.setattr(
            orchestrator,
            "_phase3_decompose",
            lambda _q, _ctx, _c: {"decomposition": {"subgoals": [{"goal": "test"}]}},
        )

        # Return agent_assignments in verify result
        test_agent = MagicMock()
        test_agent.id = "test-agent"
        # Mock verify_lite instead of _phase4_verify (which no longer exists)
        monkeypatch.setattr(
            verify,
            "verify_lite",
            lambda _decomposition, _available_agents: (
                True,  # passed
                [(0, test_agent)],  # agent_assignments
                [],  # issues
            ),
        )

        # Mock collect to use our tracking function
        from aurora_soar.phases import collect

        monkeypatch.setattr(collect, "execute_agents", AsyncMock(side_effect=mock_execute_agents))

        monkeypatch.setattr(
            orchestrator,
            "_phase6_synthesize",
            lambda *_args: MagicMock(answer="test", confidence=0.9, to_dict=lambda: {}),
        )
        monkeypatch.setattr(
            orchestrator,
            "_phase7_record",
            lambda *_args: MagicMock(cached=False, to_dict=lambda: {}),
        )
        monkeypatch.setattr(orchestrator, "_phase8_respond", lambda *_args: {"answer": "test"})

        # Execute query
        orchestrator.execute("test query")

    def test_simple_query_bypasses_decompose(self, orchestrator, monkeypatch):
        """Test that SIMPLE queries bypass decomposition phase.

        Verifies that SIMPLE complexity queries skip decompose, verify,
        route, and collect phases entirely.
        """
        phase_calls = []

        def track_phase(phase_name):
            def wrapper(*_args, **_kwargs):
                phase_calls.append(phase_name)
                if phase_name == "assess":
                    return {"complexity": "SIMPLE"}
                if phase_name == "retrieve":
                    return {"code_chunks": [], "reasoning_chunks": []}
                return {}

            return wrapper

        monkeypatch.setattr(orchestrator, "_phase1_assess", track_phase("assess"))
        monkeypatch.setattr(orchestrator, "_phase2_retrieve", track_phase("retrieve"))

        # Mock simple path execution
        monkeypatch.setattr(
            orchestrator,
            "_execute_simple_path",
            lambda *_args, **_kwargs: {"answer": "simple answer", "metadata": {}},
        )

        # Execute query
        result = orchestrator.execute("What is 2+2?")

        # Verify only assess and retrieve were called
        assert "assess" in phase_calls
        assert "retrieve" in phase_calls
        assert "decompose" not in phase_calls
        assert "verify" not in phase_calls
        assert "route" not in phase_calls
        assert "collect" not in phase_calls
        assert result["answer"] == "simple answer"
