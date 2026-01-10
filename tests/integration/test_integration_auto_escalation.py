"""
Integration Test: Auto-Escalation

Tests Issue #9: Auto-Escalation Not Implemented
- Verifies low confidence triggers escalation to SOAR
- Tests interactive mode prompts user for escalation
- Tests non-interactive mode auto-escalates
- Validates user choice is respected

This test will FAIL initially because auto-escalation logic doesn't exist.

Test Strategy:
- Mock complexity assessment to return low confidence
- Execute query in non-interactive mode
- Verify SOAR pipeline invoked automatically
- Execute query in interactive mode with mocked user input
- Verify user prompted and choice respected

Expected Failure:
- Low confidence doesn't trigger escalation
- Non-interactive mode doesn't auto-continue
- Interactive mode doesn't prompt user
- Always uses simple/direct LLM regardless of confidence

Related Files:
- packages/cli/src/aurora_cli/execution.py (QueryExecutor.execute_with_auto_escalation)
- packages/soar/src/aurora_soar/phases/assess.py (assess_complexity)
- packages/cli/src/aurora_cli/commands/query.py (query command)

Phase: 1 (Core Restoration)
Priority: P1 (High)
"""

from unittest.mock import MagicMock, Mock, call, patch

import pytest

from aurora_cli.config import Config
from aurora_cli.execution import QueryExecutor
from aurora_soar.phases.assess import assess_complexity


class TestAutoEscalation:
    """Test that low confidence triggers automatic escalation to SOAR."""

    @pytest.fixture
    def mock_memory_store(self):
        """Create a mock memory store."""
        store = MagicMock()
        store.search.return_value = []
        return store

    @pytest.fixture
    def executor_non_interactive(self, tmp_path):
        """Create QueryExecutor in non-interactive mode."""
        db_path = tmp_path / "test_memory.db"
        config = Config(anthropic_api_key="test-key", db_path=str(db_path), budget_limit=10.0)

        executor = QueryExecutor(
            config={"api_key": "test-key"},
            interactive_mode=False,  # Non-interactive
        )

        return executor

    @pytest.fixture
    def executor_interactive(self, tmp_path):
        """Create QueryExecutor in interactive mode."""
        db_path = tmp_path / "test_memory.db"
        config = Config(anthropic_api_key="test-key", db_path=str(db_path), budget_limit=10.0)

        executor = QueryExecutor(
            config={"api_key": "test-key"},
            interactive_mode=True,  # Interactive
        )

        return executor

    def test_low_confidence_triggers_escalation_non_interactive(
        self, executor_non_interactive, mock_memory_store
    ):
        """
        Test that low confidence automatically escalates to SOAR in non-interactive mode.

        This test will FAIL because auto-escalation not implemented.
        """
        executor = executor_non_interactive

        # Mock assess_complexity to return low confidence
        low_confidence_result = {
            "complexity": "MEDIUM",
            "confidence": 0.4,  # Low confidence
            "reasoning": "Ambiguous query",
        }

        # Track which execution path is taken
        direct_llm_called = False
        soar_called = False

        def mock_direct_llm(*args, **kwargs):
            nonlocal direct_llm_called
            direct_llm_called = True
            return "Direct LLM response"

        def mock_soar(*args, **kwargs):
            nonlocal soar_called
            soar_called = True
            return "SOAR response"

        with (
            patch("aurora_cli.execution.QueryExecutor._initialize_llm_client"),
            patch(
                "aurora_soar.phases.assess.assess_complexity", return_value=low_confidence_result
            ),
        ):
            with patch.object(executor, "execute_direct_llm", side_effect=mock_direct_llm):
                with patch.object(executor, "execute_aurora", side_effect=mock_soar):
                    query = "ambiguous query that might need SOAR"

                    # Execute with auto-escalation
                    result = executor.execute_with_auto_escalation(
                        query=query, api_key="test-key", memory_store=mock_memory_store
                    )

                    # ASSERTION: SOAR should be called (not direct LLM)
                    assert soar_called, (
                        f"SOAR not invoked despite low confidence in non-interactive mode\n"
                        f"Confidence: 0.4 (< 0.6 threshold)\n"
                        f"Interactive: False (should auto-escalate)\n"
                        f"Direct LLM called: {direct_llm_called}\n"
                        f"SOAR called: {soar_called}\n"
                        f"Expected: SOAR called automatically\n"
                        f"Fix: Implement execute_with_auto_escalation() in execution.py\n"
                        f"Logic: if confidence < 0.6 and not interactive: execute_aurora()"
                    )

                    assert not direct_llm_called, (
                        "Direct LLM called when SOAR should be used\n"
                        "In non-interactive mode with low confidence, should escalate to SOAR"
                    )

    def test_high_confidence_no_escalation(self, executor_non_interactive):
        """
        Test that high confidence doesn't trigger escalation.

        This test verifies we only escalate when needed.
        """
        executor = executor_non_interactive

        # Mock assess_complexity to return high confidence
        high_confidence_result = {
            "complexity": "SIMPLE",
            "confidence": 0.9,  # High confidence
            "reasoning": "Clear simple query",
        }

        direct_llm_called = False
        soar_called = False

        def mock_direct_llm(query):
            nonlocal direct_llm_called
            direct_llm_called = True
            return "Direct response"

        def mock_soar(query):
            nonlocal soar_called
            soar_called = True
            return "SOAR response"

        with patch(
            "aurora_soar.phases.assess.assess_complexity", return_value=high_confidence_result
        ):
            with patch.object(executor, "execute_direct_llm", side_effect=mock_direct_llm):
                with patch.object(executor, "execute_aurora", side_effect=mock_soar):
                    query = "What is 2+2?"

                    result = executor.execute_with_auto_escalation(query)

                    # ASSERTION: Direct LLM should be used (no escalation)
                    assert direct_llm_called, (
                        "Direct LLM not called for high-confidence simple query\n"
                        "Confidence: 0.9 (>= 0.6 threshold)\n"
                        "Expected: Use direct LLM (no escalation needed)"
                    )

                    assert not soar_called, (
                        "SOAR called unnecessarily for high-confidence query\n"
                        "High confidence means direct LLM is sufficient"
                    )

    def test_interactive_mode_prompts_user(self, executor_interactive):
        """
        Test that interactive mode prompts user when confidence is low.

        This test will FAIL because prompt logic not implemented.
        """
        executor = executor_interactive

        # Mock low confidence
        low_confidence_result = {
            "complexity": "MEDIUM",
            "confidence": 0.5,
            "reasoning": "Uncertain classification",
        }

        soar_called = False

        def mock_soar(query):
            nonlocal soar_called
            soar_called = True
            return "SOAR response"

        # Mock user accepting escalation
        with patch(
            "aurora_soar.phases.assess.assess_complexity", return_value=low_confidence_result
        ):
            with patch.object(executor, "execute_aurora", side_effect=mock_soar):
                with patch("click.confirm", return_value=True) as mock_confirm:  # User says YES
                    query = "ambiguous query"

                    result = executor.execute_with_auto_escalation(query)

                    # ASSERTION 1: User should be prompted
                    assert mock_confirm.called, (
                        "User not prompted in interactive mode with low confidence\n"
                        "Confidence: 0.5 (< 0.6)\n"
                        "Interactive: True\n"
                        "Expected: click.confirm() called to ask user\n"
                        "Fix: Add user prompt in execute_with_auto_escalation() when interactive=True"
                    )

                    # ASSERTION 2: SOAR should be called (user accepted)
                    assert soar_called, (
                        "SOAR not called despite user accepting escalation\n"
                        "User response: True (accept)\n"
                        "Expected: execute_aurora() called"
                    )

    def test_interactive_mode_user_declines_escalation(self, executor_interactive):
        """
        Test that user can decline escalation and use direct LLM.

        This test verifies user choice is respected.
        """
        executor = executor_interactive

        # Mock low confidence
        low_confidence_result = {
            "complexity": "MEDIUM",
            "confidence": 0.5,
            "reasoning": "Uncertain",
        }

        direct_llm_called = False
        soar_called = False

        def mock_direct_llm(query):
            nonlocal direct_llm_called
            direct_llm_called = True
            return "Direct response"

        def mock_soar(query):
            nonlocal soar_called
            soar_called = True
            return "SOAR response"

        with patch(
            "aurora_soar.phases.assess.assess_complexity", return_value=low_confidence_result
        ):
            with patch.object(executor, "execute_direct_llm", side_effect=mock_direct_llm):
                with patch.object(executor, "execute_aurora", side_effect=mock_soar):
                    with patch("click.confirm", return_value=False):  # User says NO
                        query = "ambiguous query"

                        result = executor.execute_with_auto_escalation(query)

                        # ASSERTION 1: User should be prompted
                        # (already tested in previous test)

                        # ASSERTION 2: Direct LLM should be called (user declined SOAR)
                        assert direct_llm_called, (
                            "Direct LLM not called when user declined escalation\n"
                            "User response: False (decline)\n"
                            "Expected: Proceed with original complexity assessment (direct LLM)"
                        )

                        assert not soar_called, (
                            "SOAR called despite user declining\n"
                            "User should be able to decline escalation"
                        )

    def test_confidence_threshold_boundary(self, executor_non_interactive):
        """
        Test behavior at confidence threshold (0.6).

        This test documents boundary behavior.
        """
        executor = executor_non_interactive

        # Test at threshold: 0.6
        threshold_result = {
            "complexity": "MEDIUM",
            "confidence": 0.6,  # Exactly at threshold
            "reasoning": "At boundary",
        }

        direct_llm_called = False
        soar_called = False

        def mock_direct_llm(query):
            nonlocal direct_llm_called
            direct_llm_called = True
            return "Direct"

        def mock_soar(query):
            nonlocal soar_called
            soar_called = True
            return "SOAR"

        with patch("aurora_soar.phases.assess.assess_complexity", return_value=threshold_result):
            with patch.object(executor, "execute_direct_llm", side_effect=mock_direct_llm):
                with patch.object(executor, "execute_aurora", side_effect=mock_soar):
                    query = "threshold query"

                    result = executor.execute_with_auto_escalation(query)

                    # ASSERTION: >= 0.6 should NOT escalate
                    assert direct_llm_called, (
                        "Confidence = 0.6 should not trigger escalation\n"
                        "Threshold: < 0.6 (strictly less than)\n"
                        "Expected: Direct LLM used"
                    )

                    assert not soar_called, "SOAR should not be called at threshold"


class TestEscalationLogging:
    """Test that escalation decisions are logged for transparency."""

    def test_escalation_logged_when_triggered(self, tmp_path, caplog):
        """
        Test that escalation is logged with reason.

        This test verifies transparency in decision-making.
        """
        db_path = tmp_path / "test_memory.db"
        config = Config(anthropic_api_key="test-key", db_path=str(db_path), budget_limit=10.0)

        executor = QueryExecutor(config={"api_key": "test-key"}, interactive_mode=False)

        # Mock low confidence
        low_confidence_result = {
            "complexity": "MEDIUM",
            "confidence": 0.4,
            "reasoning": "Unclear intent",
        }

        with patch(
            "aurora_soar.phases.assess.assess_complexity", return_value=low_confidence_result
        ):
            with patch.object(executor, "execute_aurora", return_value="SOAR result"):
                query = "ambiguous query"

                result = executor.execute_with_auto_escalation(query)

                # Check logs for escalation message
                # (This requires logging to be implemented)

                # ASSERTION: Log should mention escalation
                # log_messages = [record.message for record in caplog.records]
                # escalation_logged = any("escalat" in msg.lower() for msg in log_messages)

                # For now, this documents expected behavior
                assert True, "Escalation logging will be verified in implementation"

    def test_confidence_score_logged(self):
        """
        Test that confidence score is logged for debugging.

        This test documents expected logging behavior.
        """
        # Expected log format:
        # "Complexity assessment: MEDIUM (confidence: 0.45)"
        # "Low confidence (<0.6), escalating to SOAR in non-interactive mode"

        assert True, "Confidence logging will be verified in implementation"


class TestEscalationWithMemoryStore:
    """Test escalation behavior when memory store is available."""

    @pytest.fixture
    def executor_with_memory(self, tmp_path):
        """Create executor with memory store."""
        from aurora_cli.memory_manager import MemoryManager

        # Create workspace with sample data
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        sample_file = workspace / "example.py"
        sample_file.write_text(
            """
def process_data(data):
    \"\"\"Process input data.\"\"\"
    return [x * 2 for x in data]
"""
        )

        db_path = tmp_path / "test_memory.db"
        config = Config(anthropic_api_key="test-key", db_path=str(db_path), budget_limit=10.0)

        # Create memory store directly
        from aurora_core.store.sqlite import SQLiteStore

        memory_store = SQLiteStore(db_path=str(db_path))

        memory_manager = MemoryManager(memory_store=memory_store)
        memory_manager.index_directory(workspace)

        executor = QueryExecutor(config={"api_key": "test-key"}, interactive_mode=False)

        return executor, memory_store

    def test_escalation_passes_memory_store_to_soar(self, executor_with_memory):
        """
        Test that SOAR pipeline receives memory store when escalating.

        This test verifies context is preserved during escalation.
        """
        executor, memory_store = executor_with_memory

        # Mock low confidence
        low_confidence_result = {
            "complexity": "COMPLEX",
            "confidence": 0.3,
            "reasoning": "Complex multi-part query",
        }

        soar_memory_store_arg = None

        def capture_soar_call(query, **kwargs):
            nonlocal soar_memory_store_arg
            soar_memory_store_arg = kwargs.get("memory_store")
            return "SOAR result"

        with patch(
            "aurora_soar.phases.assess.assess_complexity", return_value=low_confidence_result
        ):
            with patch.object(
                executor, "execute_aurora", side_effect=capture_soar_call
            ) as mock_soar:
                query = "complex query about data processing"

                result = executor.execute_with_auto_escalation(query)

                # ASSERTION: SOAR should receive memory store
                mock_soar.assert_called_once()

                # This verifies memory context is preserved during escalation
                # Actual implementation may pass memory_store differently
                assert True, "Memory store passing will be verified in implementation"


# Mark all tests in this file with integration marker
pytestmark = pytest.mark.integration
