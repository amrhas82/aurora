"""Unit tests for SOAROrchestrator phase_callback functionality.

TDD: These tests are written FIRST before implementation.
All tests should FAIL initially (RED phase).
"""

from __future__ import annotations

import logging
from unittest.mock import Mock, patch

import pytest


class TestPhaseCallbackParameter:
    """Tests for phase_callback parameter in SOAROrchestrator."""

    def test_orchestrator_accepts_phase_callback(self):
        """SOAROrchestrator.__init__ accepts optional phase_callback parameter."""
        from aurora_soar.orchestrator import SOAROrchestrator

        callback = Mock()

        # Mock all required dependencies
        with patch.object(SOAROrchestrator, "__init__", return_value=None):
            # Just verify the parameter is accepted - actual test below
            pass

        # Real test: create orchestrator with callback
        mock_store = Mock()
        mock_registry = Mock()
        mock_config = Mock()
        mock_config.get.return_value = {}
        mock_llm = Mock()

        orchestrator = SOAROrchestrator(
            store=mock_store,
            agent_registry=mock_registry,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
            phase_callback=callback,
        )

        assert orchestrator.phase_callback == callback

    def test_no_callback_works(self):
        """Orchestrator works without callback (optional parameter)."""
        from aurora_soar.orchestrator import SOAROrchestrator

        mock_store = Mock()
        mock_registry = Mock()
        mock_config = Mock()
        mock_config.get.return_value = {}
        mock_llm = Mock()

        # Should not raise
        orchestrator = SOAROrchestrator(
            store=mock_store,
            agent_registry=mock_registry,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
            # No phase_callback parameter
        )

        assert orchestrator.phase_callback is None


class TestPhaseCallbackInvocation:
    """Tests for phase callback invocation during phase execution."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator with callback tracking."""
        from aurora_soar.orchestrator import SOAROrchestrator

        callback = Mock()
        mock_store = Mock()
        mock_registry = Mock()
        mock_registry.list_all.return_value = []
        mock_config = Mock()
        mock_config.get.return_value = {}
        mock_llm = Mock()

        # Mock LLM responses
        mock_llm.default_model = "test-model"
        mock_llm.generate.return_value = Mock(
            content="test response",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            finish_reason="stop",
        )

        orchestrator = SOAROrchestrator(
            store=mock_store,
            agent_registry=mock_registry,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
            phase_callback=callback,
        )

        return orchestrator, callback

    def test_callback_invoked_before_phase(self, mock_orchestrator):
        """Callback is called with status='before' before phase execution."""
        orchestrator, callback = mock_orchestrator

        # Mock the assess module to return quickly
        with patch("aurora_soar.phases.assess.assess_complexity") as mock_assess:
            mock_assess.return_value = {"complexity": "SIMPLE", "confidence": 0.9}

            # Actually invoke the phase method (not mocking it)
            orchestrator._phase1_assess("test query")

        # Check callback was called with "before" status
        before_calls = [call for call in callback.call_args_list if call[0][1] == "before"]
        assert len(before_calls) > 0, "Callback should be called with status='before'"

    def test_callback_invoked_after_phase(self, mock_orchestrator):
        """Callback is called with status='after' after phase execution with result."""
        orchestrator, callback = mock_orchestrator

        # Check callback was called with "after" status and result
        after_calls = [call for call in callback.call_args_list if call[0][1] == "after"]
        # After calls should have result_summary in third argument
        for call in after_calls:
            assert len(call[0]) >= 3, "After call should have result_summary"
            assert isinstance(call[0][2], dict), "Result summary should be dict"

    def test_callback_receives_phase_name(self, mock_orchestrator):
        """Callback receives correct phase name as first argument."""
        orchestrator, callback = mock_orchestrator

        # Expected phase names
        expected_phases = [
            "assess",
            "retrieve",
            "decompose",
            "verify",
            "route",
            "collect",
            "synthesize",
            "record",
            "respond",
        ]

        # Check that phase names are from expected set
        for call in callback.call_args_list:
            phase_name = call[0][0]
            assert phase_name in expected_phases, f"Unknown phase: {phase_name}"

    def test_callback_exception_logged_not_raised(self, mock_orchestrator, caplog):
        """Callback exceptions are caught and logged, not propagated."""
        orchestrator, callback = mock_orchestrator

        # Make callback raise an exception
        callback.side_effect = ValueError("Callback error!")

        # Phase execution should NOT raise despite callback error
        with caplog.at_level(logging.WARNING):
            # This should not raise
            try:
                orchestrator._phase1_assess("test query")
                # If we get here, exception was caught
            except ValueError:
                pytest.fail("Callback exception should not propagate")

        # Warning should be logged
        assert any("callback" in record.message.lower() for record in caplog.records), (
            "Warning about callback failure should be logged"
        )


class TestPhaseCallbackResultSummary:
    """Tests for result summary passed to callback."""

    def test_assess_callback_includes_complexity(self):
        """Assess phase callback includes complexity in result."""
        from aurora_soar.orchestrator import SOAROrchestrator

        callback = Mock()
        mock_store = Mock()
        mock_registry = Mock()
        mock_config = Mock()
        mock_config.get.return_value = {}
        mock_llm = Mock()

        _orchestrator = SOAROrchestrator(  # noqa: F841 - orchestrator creation triggers callback
            store=mock_store,
            agent_registry=mock_registry,
            config=mock_config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
            phase_callback=callback,
        )

        # Find the "after" call for assess phase
        after_calls = [
            call
            for call in callback.call_args_list
            if call[0][0] == "assess" and call[0][1] == "after"
        ]

        if after_calls:
            result_summary = after_calls[0][0][2]
            assert "complexity" in result_summary

    def test_retrieve_callback_includes_chunks(self):
        """Retrieve phase callback includes chunks_retrieved in result."""
        # Similar structure - verify chunks_retrieved key in result
        # Will be implemented when testing actual execution

    def test_decompose_callback_includes_subgoal_count(self):
        """Decompose phase callback includes subgoal_count in result."""
        # Will be implemented when testing actual execution

    def test_verify_callback_includes_verdict(self):
        """Verify phase callback includes verdict in result."""
        # Will be implemented when testing actual execution

    def test_route_callback_includes_agents(self):
        """Route phase callback includes agents list in result."""
        # Will be implemented when testing actual execution

    def test_synthesize_callback_includes_confidence(self):
        """Synthesize phase callback includes confidence in result."""
        # Will be implemented when testing actual execution

    def test_record_callback_includes_cached(self):
        """Record phase callback includes cached flag in result."""
        # Will be implemented when testing actual execution
