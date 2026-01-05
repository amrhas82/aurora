"""
Unit tests for simplified HeadlessOrchestrator.

Tests single-iteration autonomous execution including:
- Initialization with dependency injection
- Single SOAR iteration execution
- Goal achievement evaluation (simplified)
- Success and failure scenarios
- Scratchpad logging integration
- Error handling
"""

from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, create_autospec
import pytest

from aurora_soar.headless.config import HeadlessConfig
from aurora_soar.headless.git_enforcer import GitBranchError, GitEnforcer
from aurora_soar.headless.prompt_loader_simplified import PromptLoader, PromptData, PromptValidationError
from aurora_soar.headless.scratchpad import Scratchpad


# ============================================================================
# Task 5.1: RED - Write test for HeadlessOrchestrator initialization
# ============================================================================

class TestHeadlessOrchestratorInit:
    """Test HeadlessOrchestrator initialization with dependency injection."""

    def test_init_with_all_dependencies(self, tmp_path):
        """Test initialization accepts all required dependencies."""
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("# Goal\nTest goal\n\n# Success Criteria\n- Criterion 1")

        scratchpad_path = tmp_path / "scratchpad.md"

        mock_soar = MagicMock()
        mock_git_enforcer = MagicMock()
        mock_prompt_loader = MagicMock()
        mock_scratchpad = MagicMock()

        config = HeadlessConfig(max_iterations=1)

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_path,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git_enforcer,
            prompt_loader=mock_prompt_loader,
            scratchpad=mock_scratchpad
        )

        assert orchestrator.prompt_path == prompt_path
        assert orchestrator.scratchpad_path == scratchpad_path
        assert orchestrator.soar_orchestrator == mock_soar
        assert orchestrator.config == config
        assert orchestrator.git_enforcer == mock_git_enforcer
        assert orchestrator.prompt_loader == mock_prompt_loader
        assert orchestrator.scratchpad == mock_scratchpad


# ============================================================================
# Task 5.2: RED - Write test for successful single iteration
# ============================================================================

class TestHeadlessOrchestratorExecute:
    """Test HeadlessOrchestrator.execute() method."""

    def test_execute_successful_single_iteration(self, tmp_path):
        """Test successful execution of single SOAR iteration."""
        # This test will fail until we implement execute()
        from aurora_soar.headless.orchestrator_simplified import (
            HeadlessOrchestrator,
            HeadlessResult,
            TerminationReason
        )

        prompt_path = tmp_path / "prompt.md"
        scratchpad_path = tmp_path / "scratchpad.md"

        # Setup mocks
        mock_soar = MagicMock()
        mock_soar.execute.return_value = {
            "answer": "Task completed successfully",
            "confidence": 0.95,
            "cost_usd": 0.05
        }

        mock_git_enforcer = MagicMock()
        mock_git_enforcer.validate.return_value = None  # Success

        prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context"
        )
        mock_prompt_loader = MagicMock()
        mock_prompt_loader.load.return_value = prompt_data

        mock_scratchpad = MagicMock()
        mock_scratchpad.read.return_value = "Initial scratchpad"

        config = HeadlessConfig(max_iterations=1)

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_path,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git_enforcer,
            prompt_loader=mock_prompt_loader,
            scratchpad=mock_scratchpad
        )

        result = orchestrator.execute()

        # Verify result structure
        assert isinstance(result, HeadlessResult)
        assert result.goal_achieved in [True, False]
        assert isinstance(result.termination_reason, TerminationReason)
        assert result.iterations == 1
        assert result.total_cost > 0
        assert result.duration_seconds > 0
        assert result.scratchpad_path == str(scratchpad_path)

        # Verify components were called
        mock_git_enforcer.validate.assert_called_once()
        mock_prompt_loader.load.assert_called_once()
        mock_soar.execute.assert_called_once()


# ============================================================================
# Task 5.3: RED - Write test for SOAR execution failure
# ============================================================================

    def test_execute_handles_soar_failure(self, tmp_path):
        """Test orchestrator handles SOAR execution failures gracefully."""
        from aurora_soar.headless.orchestrator_simplified import (
            HeadlessOrchestrator,
            TerminationReason
        )

        prompt_path = tmp_path / "prompt.md"
        scratchpad_path = tmp_path / "scratchpad.md"

        # Setup mocks
        mock_soar = MagicMock()
        mock_soar.execute.side_effect = Exception("SOAR pipeline failed")

        mock_git_enforcer = MagicMock()
        mock_git_enforcer.validate.return_value = None

        prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=[],
            context=""
        )
        mock_prompt_loader = MagicMock()
        mock_prompt_loader.load.return_value = prompt_data

        mock_scratchpad = MagicMock()
        mock_scratchpad.read.return_value = ""

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_path,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            git_enforcer=mock_git_enforcer,
            prompt_loader=mock_prompt_loader,
            scratchpad=mock_scratchpad
        )

        result = orchestrator.execute()

        # Should return failure result, not raise exception
        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.BLOCKED
        assert result.error_message is not None
        assert "SOAR pipeline failed" in result.error_message


# ============================================================================
# Task 5.4: RED - Write test for goal achievement evaluation
# ============================================================================

    def test_evaluate_goal_achievement(self, tmp_path):
        """Test simplified goal evaluation (check if scratchpad contains success)."""
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        prompt_path = tmp_path / "prompt.md"
        scratchpad_path = tmp_path / "scratchpad.md"

        mock_soar = MagicMock()
        mock_git_enforcer = MagicMock()

        prompt_data = PromptData(
            goal="Complete the task",
            success_criteria=["Task is complete", "Tests pass"],
            constraints=[],
            context=""
        )
        mock_prompt_loader = MagicMock()
        mock_prompt_loader.load.return_value = prompt_data

        # Scratchpad indicates success
        mock_scratchpad = MagicMock()
        mock_scratchpad.read.return_value = """
        Iteration 1: Completed task successfully. All tests passing.
        Status: COMPLETED
        """

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_path,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            git_enforcer=mock_git_enforcer,
            prompt_loader=mock_prompt_loader,
            scratchpad=mock_scratchpad
        )

        # Internal method to test evaluation logic
        is_achieved = orchestrator._evaluate_success()

        assert is_achieved is True


# ============================================================================
# Task 5.5: RED - Write test for scratchpad logging
# ============================================================================

    def test_execute_appends_to_scratchpad(self, tmp_path):
        """Test that execution appends iteration details to scratchpad."""
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        prompt_path = tmp_path / "prompt.md"
        scratchpad_path = tmp_path / "scratchpad.md"

        mock_soar = MagicMock()
        mock_soar.execute.return_value = {
            "answer": "Task completed",
            "confidence": 0.9,
            "cost_usd": 0.05
        }

        mock_git_enforcer = MagicMock()
        mock_git_enforcer.validate.return_value = None

        prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=[],
            context=""
        )
        mock_prompt_loader = MagicMock()
        mock_prompt_loader.load.return_value = prompt_data

        mock_scratchpad = MagicMock()
        mock_scratchpad.read.return_value = ""

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_path,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            git_enforcer=mock_git_enforcer,
            prompt_loader=mock_prompt_loader,
            scratchpad=mock_scratchpad
        )

        orchestrator.execute()

        # Verify scratchpad was updated
        assert mock_scratchpad.append_iteration.called
        assert mock_scratchpad.update_status.called


# ============================================================================
# Additional edge case tests
# ============================================================================

class TestHeadlessOrchestratorEdgeCases:
    """Test edge cases and error handling."""

    def test_git_safety_error_prevents_execution(self, tmp_path):
        """Test that git safety error stops execution before SOAR."""
        from aurora_soar.headless.orchestrator_simplified import (
            HeadlessOrchestrator,
            TerminationReason
        )

        prompt_path = tmp_path / "prompt.md"
        scratchpad_path = tmp_path / "scratchpad.md"

        mock_soar = MagicMock()

        # Git enforcer raises error
        mock_git_enforcer = MagicMock()
        mock_git_enforcer.validate.side_effect = GitBranchError("On main branch")

        mock_prompt_loader = MagicMock()
        mock_scratchpad = MagicMock()

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_path,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            git_enforcer=mock_git_enforcer,
            prompt_loader=mock_prompt_loader,
            scratchpad=mock_scratchpad
        )

        result = orchestrator.execute()

        # Should return error result without calling SOAR
        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.GIT_SAFETY_ERROR
        assert result.iterations == 0
        assert not mock_soar.execute.called

    def test_prompt_validation_error_prevents_execution(self, tmp_path):
        """Test that prompt validation error stops execution."""
        from aurora_soar.headless.orchestrator_simplified import (
            HeadlessOrchestrator,
            TerminationReason
        )

        prompt_path = tmp_path / "prompt.md"
        scratchpad_path = tmp_path / "scratchpad.md"

        mock_soar = MagicMock()
        mock_git_enforcer = MagicMock()
        mock_git_enforcer.validate.return_value = None

        # Prompt loader raises error
        mock_prompt_loader = MagicMock()
        mock_prompt_loader.load.side_effect = PromptValidationError("Missing Goal section")

        mock_scratchpad = MagicMock()

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_path,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            git_enforcer=mock_git_enforcer,
            prompt_loader=mock_prompt_loader,
            scratchpad=mock_scratchpad
        )

        result = orchestrator.execute()

        # Should return error result
        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.PROMPT_ERROR
        assert not mock_soar.execute.called
