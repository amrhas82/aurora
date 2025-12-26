"""
Unit tests for HeadlessOrchestrator.

Tests autonomous experiment execution including:
- Initialization and configuration
- Safety validation (git branch, prompt)
- Scratchpad initialization
- Budget tracking and enforcement
- Goal achievement evaluation
- Main iteration loop
- Termination conditions (goal achieved, budget exceeded, max iterations, blocked)
- Error handling and recovery
- Full execute() workflow
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from aurora.soar.headless.git_enforcer import GitBranchError
from aurora.soar.headless.orchestrator import (
    HeadlessConfig,
    HeadlessOrchestrator,
    HeadlessResult,
    TerminationReason,
)
from aurora.soar.headless.prompt_loader import PromptData, PromptValidationError
from aurora.soar.headless.scratchpad_manager import ScratchpadStatus


@pytest.fixture
def prompt_file(tmp_path):
    """Create a temporary experiment.md file for tests."""
    prompt = tmp_path / "experiment.md"
    prompt.write_text(
        """# Goal
Test experiment goal

# Success Criteria
- Test criterion 1
- Test criterion 2

# Constraints
- Test constraint 1
"""
    )
    return str(prompt)


@pytest.fixture
def scratchpad_file(tmp_path):
    """Create a temporary scratchpad.md file for tests."""
    scratchpad = tmp_path / "scratchpad.md"
    scratchpad.write_text("")  # Start empty
    return str(scratchpad)


class TestHeadlessConfig:
    """Test HeadlessConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = HeadlessConfig()
        assert config.max_iterations == 10
        assert config.budget_limit == 5.0
        assert config.required_branch == "headless"
        assert config.blocked_branches == ["main", "master"]
        assert config.auto_create_scratchpad is True
        assert config.scratchpad_backup is True
        assert "Goal Achievement Evaluation" in config.evaluation_prompt_template

    def test_custom_config(self):
        """Test custom configuration."""
        config = HeadlessConfig(
            max_iterations=20,
            budget_limit=10.0,
            required_branch="experiment-123",
            blocked_branches=["main", "master", "develop"],
            auto_create_scratchpad=False,
            scratchpad_backup=False,
        )
        assert config.max_iterations == 20
        assert config.budget_limit == 10.0
        assert config.required_branch == "experiment-123"
        assert len(config.blocked_branches) == 3
        assert config.auto_create_scratchpad is False
        assert config.scratchpad_backup is False

    def test_evaluation_template_contains_placeholders(self):
        """Test evaluation template has required placeholders."""
        config = HeadlessConfig()
        template = config.evaluation_prompt_template
        assert "{goal}" in template
        assert "{success_criteria}" in template
        assert "{scratchpad_content}" in template


class TestHeadlessOrchestratorInit:
    """Test HeadlessOrchestrator initialization."""

    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    def test_init_with_defaults(
        self, mock_scratchpad, mock_prompt, mock_git, prompt_file, scratchpad_file
    ):
        """Test initialization with default config."""
        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        assert orchestrator.prompt_path == Path(prompt_file)
        assert orchestrator.scratchpad_path == Path(scratchpad_file)
        assert orchestrator.soar_orchestrator is mock_soar
        assert orchestrator.config.max_iterations == 10
        assert orchestrator.current_iteration == 0
        assert orchestrator.total_cost == 0.0
        assert orchestrator.prompt_data is None

    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    def test_init_with_custom_config(
        self, mock_scratchpad, mock_prompt, mock_git, prompt_file, scratchpad_file
    ):
        """Test initialization with custom config."""
        mock_soar = Mock()
        config = HeadlessConfig(max_iterations=20, budget_limit=10.0)

        orchestrator = HeadlessOrchestrator(
            prompt_path=Path(prompt_file),
            scratchpad_path=Path(scratchpad_file),
            soar_orchestrator=mock_soar,
            config=config,
        )

        assert orchestrator.config.max_iterations == 20
        assert orchestrator.config.budget_limit == 10.0

    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    def test_init_creates_components(
        self, mock_scratchpad, mock_prompt, mock_git, prompt_file, scratchpad_file
    ):
        """Test initialization creates all required components."""
        mock_soar = Mock()
        HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        # Verify components were created
        assert mock_git.called
        assert mock_prompt.called
        assert mock_scratchpad.called


class TestValidateSafety:
    """Test _validate_safety method."""

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_validate_safety_success(
        self, mock_git_class, mock_prompt_class, mock_scratchpad, prompt_file, scratchpad_file
    ):
        """Test successful safety validation."""
        mock_git = Mock()
        mock_git.validate.return_value = None
        mock_git_class.return_value = mock_git

        mock_prompt = Mock()
        mock_prompt.validate_format.return_value = (True, [])
        mock_prompt_class.return_value = mock_prompt

        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        # Should not raise
        orchestrator._validate_safety()

        mock_git.validate.assert_called_once()
        mock_prompt.validate_format.assert_called_once()

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_validate_safety_git_error(
        self, mock_git_class, mock_prompt_class, mock_scratchpad, prompt_file, scratchpad_file
    ):
        """Test git branch validation error."""
        mock_git = Mock()
        mock_git.validate.side_effect = GitBranchError("Not on headless branch")
        mock_git_class.return_value = mock_git

        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        with pytest.raises(GitBranchError, match="Not on headless branch"):
            orchestrator._validate_safety()

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_validate_safety_prompt_error(
        self, mock_git_class, mock_prompt_class, mock_scratchpad, prompt_file, scratchpad_file
    ):
        """Test prompt validation error."""
        mock_git = Mock()
        mock_git.validate.return_value = None
        mock_git_class.return_value = mock_git

        mock_prompt = Mock()
        mock_prompt.validate_format.return_value = (False, ["Missing goal section"])
        mock_prompt_class.return_value = mock_prompt

        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        with pytest.raises(PromptValidationError, match="Prompt validation failed"):
            orchestrator._validate_safety()


class TestLoadPrompt:
    """Test _load_prompt method."""

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_load_prompt_success(
        self, mock_git, mock_prompt_class, mock_scratchpad, prompt_file, scratchpad_file
    ):
        """Test successful prompt loading."""
        prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1", "Criterion 2"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        mock_prompt = Mock()
        mock_prompt.load.return_value = prompt_data
        mock_prompt_class.return_value = mock_prompt

        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        result = orchestrator._load_prompt()

        assert result.goal == "Test goal"
        assert len(result.success_criteria) == 2
        assert len(result.constraints) == 1
        mock_prompt.load.assert_called_once()

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_load_prompt_error(
        self, mock_git, mock_prompt_class, mock_scratchpad, prompt_file, scratchpad_file
    ):
        """Test prompt loading error."""
        mock_prompt = Mock()
        mock_prompt.load.side_effect = PromptValidationError("Invalid prompt")
        mock_prompt_class.return_value = mock_prompt

        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        with pytest.raises(PromptValidationError, match="Invalid prompt"):
            orchestrator._load_prompt()


class TestInitializeScratchpad:
    """Test _initialize_scratchpad method."""

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_initialize_scratchpad_success(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test successful scratchpad initialization."""
        mock_scratchpad = Mock()
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        orchestrator._initialize_scratchpad()

        mock_scratchpad.initialize.assert_called_once_with(
            goal="Test goal",
            status=ScratchpadStatus.IN_PROGRESS,
        )

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_initialize_scratchpad_no_prompt_data(
        self, mock_git, mock_prompt, mock_scratchpad, prompt_file, scratchpad_file
    ):
        """Test scratchpad initialization without prompt data."""
        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        orchestrator.prompt_data = None

        with pytest.raises(RuntimeError, match="Prompt data not loaded"):
            orchestrator._initialize_scratchpad()


class TestCheckBudget:
    """Test _check_budget method."""

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_check_budget_under_limit(
        self, mock_git, mock_prompt, mock_scratchpad, prompt_file, scratchpad_file
    ):
        """Test budget check under limit."""
        mock_soar = Mock()
        config = HeadlessConfig(budget_limit=5.0)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.total_cost = 3.0
        assert orchestrator._check_budget() is False

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_check_budget_at_limit(
        self, mock_git, mock_prompt, mock_scratchpad, prompt_file, scratchpad_file
    ):
        """Test budget check at exact limit."""
        mock_soar = Mock()
        config = HeadlessConfig(budget_limit=5.0)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.total_cost = 5.0
        assert orchestrator._check_budget() is True

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_check_budget_over_limit(
        self, mock_git, mock_prompt, mock_scratchpad, prompt_file, scratchpad_file
    ):
        """Test budget check over limit."""
        mock_soar = Mock()
        config = HeadlessConfig(budget_limit=5.0)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.total_cost = 6.0
        assert orchestrator._check_budget() is True


class TestEvaluateGoalAchievement:
    """Test _evaluate_goal_achievement method."""

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_evaluate_goal_achieved(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test evaluation when goal is achieved."""
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Test scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.reasoning_llm.complete.return_value = {
            "content": "GOAL_ACHIEVED - all criteria met"
        }

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1", "Criterion 2"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        result = orchestrator._evaluate_goal_achievement()

        assert result == "GOAL_ACHIEVED"
        mock_soar.reasoning_llm.complete.assert_called_once()

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_evaluate_in_progress(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test evaluation when goal is in progress."""
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Test scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.reasoning_llm.complete.return_value = {"content": "IN_PROGRESS - still working"}

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        result = orchestrator._evaluate_goal_achievement()

        assert result == "IN_PROGRESS"

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_evaluate_blocked(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test evaluation when goal is blocked."""
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Test scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.reasoning_llm.complete.return_value = {"content": "BLOCKED - cannot proceed"}

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        result = orchestrator._evaluate_goal_achievement()

        assert result == "BLOCKED"

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_evaluate_no_prompt_data(
        self, mock_git, mock_prompt, mock_scratchpad, prompt_file, scratchpad_file
    ):
        """Test evaluation without prompt data."""
        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        orchestrator.prompt_data = None

        result = orchestrator._evaluate_goal_achievement()

        assert result == "IN_PROGRESS"

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_evaluate_llm_error(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test evaluation when LLM fails."""
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Test scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.reasoning_llm.complete.side_effect = Exception("LLM error")

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        result = orchestrator._evaluate_goal_achievement()

        # Should return IN_PROGRESS on error
        assert result == "IN_PROGRESS"


class TestBuildIterationQuery:
    """Test _build_iteration_query method."""

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_build_query_with_prompt_data(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test building query with prompt data."""
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Previous iteration content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1", "Criterion 2"],
            constraints=["Constraint 1", "Constraint 2"],
            context="Test context",
        )

        query = orchestrator._build_iteration_query(1)

        assert "Iteration 1" in query
        assert "Test goal" in query
        assert "Criterion 1" in query
        assert "Criterion 2" in query
        assert "Constraint 1" in query
        assert "Previous iteration content" in query

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_build_query_without_prompt_data(
        self, mock_git, mock_prompt, mock_scratchpad, prompt_file, scratchpad_file
    ):
        """Test building query without prompt data."""
        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        orchestrator.prompt_data = None

        query = orchestrator._build_iteration_query(1)

        assert query == "Continue working toward the goal."

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_build_query_truncates_long_scratchpad(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test query truncates long scratchpad content."""
        mock_scratchpad = Mock()
        # Create scratchpad content longer than 2000 chars
        long_content = "x" * 3000
        mock_scratchpad.read.return_value = long_content
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        query = orchestrator._build_iteration_query(1)

        # Should only include last 2000 chars of scratchpad
        assert long_content[-2000:] in query
        # The query will have the 2000 'x' chars from truncated scratchpad
        # Count consecutive 'x' in the scratchpad portion
        import re

        # Find the longest sequence of x's (should be exactly 2000)
        x_sequences = re.findall(r"x+", query)
        if x_sequences:
            longest_x_sequence = max(len(seq) for seq in x_sequences)
            assert longest_x_sequence == 2000


class TestExecuteIteration:
    """Test _execute_iteration method."""

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_execute_iteration_success(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test successful iteration execution."""
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.execute.return_value = {
            "answer": "Test answer",
            "confidence": 0.9,
            "cost_usd": 0.25,
        }

        config = HeadlessConfig(budget_limit=5.0)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        result = orchestrator._execute_iteration(1)

        assert result["answer"] == "Test answer"
        assert result["confidence"] == 0.9
        assert result["cost_usd"] == 0.25
        mock_soar.execute.assert_called_once()

        # Verify budget limit is passed correctly
        call_args = mock_soar.execute.call_args
        assert call_args.kwargs["max_cost_usd"] == 5.0


class TestRunMainLoop:
    """Test _run_main_loop method."""

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_run_main_loop_goal_achieved(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test main loop terminates when goal is achieved."""
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.execute.return_value = {
            "answer": "Goal achieved!",
            "confidence": 0.95,
            "cost_usd": 0.5,
        }
        mock_soar.reasoning_llm.complete.return_value = {"content": "GOAL_ACHIEVED"}

        config = HeadlessConfig(max_iterations=10)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        reason = orchestrator._run_main_loop()

        assert reason == TerminationReason.GOAL_ACHIEVED
        assert orchestrator.current_iteration == 1
        mock_scratchpad.update_status.assert_called_with(ScratchpadStatus.GOAL_ACHIEVED)

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_run_main_loop_budget_exceeded_before_iteration(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test main loop terminates when budget exceeded before iteration."""
        mock_scratchpad = Mock()
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()

        config = HeadlessConfig(budget_limit=1.0, max_iterations=10)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        # Set cost to exceed budget
        orchestrator.total_cost = 1.5

        reason = orchestrator._run_main_loop()

        assert reason == TerminationReason.BUDGET_EXCEEDED
        assert orchestrator.current_iteration == 1
        mock_scratchpad.update_status.assert_called_with(ScratchpadStatus.BUDGET_EXCEEDED)
        # Should not execute iteration
        mock_soar.execute.assert_not_called()

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_run_main_loop_budget_exceeded_after_iteration(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test main loop terminates when budget exceeded after iteration."""
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.execute.return_value = {
            "answer": "Test answer",
            "confidence": 0.8,
            "cost_usd": 1.5,  # Exceeds budget
        }
        mock_soar.reasoning_llm.complete.return_value = {"content": "IN_PROGRESS"}

        config = HeadlessConfig(budget_limit=1.0, max_iterations=10)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        reason = orchestrator._run_main_loop()

        assert reason == TerminationReason.BUDGET_EXCEEDED
        assert orchestrator.current_iteration == 1
        assert orchestrator.total_cost == 1.5
        mock_scratchpad.update_status.assert_called_with(ScratchpadStatus.BUDGET_EXCEEDED)

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_run_main_loop_max_iterations(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test main loop terminates at max iterations."""
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.execute.return_value = {
            "answer": "Test answer",
            "confidence": 0.8,
            "cost_usd": 0.1,
        }
        mock_soar.reasoning_llm.complete.return_value = {"content": "IN_PROGRESS"}

        config = HeadlessConfig(max_iterations=3, budget_limit=10.0)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        reason = orchestrator._run_main_loop()

        assert reason == TerminationReason.MAX_ITERATIONS
        assert orchestrator.current_iteration == 3
        assert mock_soar.execute.call_count == 3
        mock_scratchpad.update_status.assert_called_with(ScratchpadStatus.MAX_ITERATIONS)

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_run_main_loop_blocked(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test main loop terminates when blocked."""
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.execute.return_value = {
            "answer": "Stuck",
            "confidence": 0.3,
            "cost_usd": 0.2,
        }
        mock_soar.reasoning_llm.complete.return_value = {"content": "BLOCKED"}

        config = HeadlessConfig(max_iterations=10)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        reason = orchestrator._run_main_loop()

        assert reason == TerminationReason.BLOCKED
        assert orchestrator.current_iteration == 1
        mock_scratchpad.update_status.assert_called_with(ScratchpadStatus.BLOCKED)

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_run_main_loop_iteration_error(
        self, mock_git, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test main loop handles iteration errors."""
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.execute.side_effect = Exception("SOAR execution failed")

        config = HeadlessConfig(max_iterations=10)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.prompt_data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )

        reason = orchestrator._run_main_loop()

        assert reason == TerminationReason.BLOCKED
        assert orchestrator.current_iteration == 1
        mock_scratchpad.append_iteration.assert_called()
        mock_scratchpad.update_status.assert_called_with(ScratchpadStatus.BLOCKED)


class TestExecute:
    """Test execute method (full workflow)."""

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_execute_success_goal_achieved(
        self, mock_git_class, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test successful execution with goal achieved."""
        # Setup git enforcer
        mock_git = Mock()
        mock_git.validate.return_value = None
        mock_git_class.return_value = mock_git

        # Setup prompt loader
        mock_prompt = Mock()
        mock_prompt.validate_format.return_value = (True, [])
        mock_prompt.load.return_value = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )
        mock_prompt_class.return_value = mock_prompt

        # Setup scratchpad
        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        # Setup SOAR
        mock_soar = Mock()
        mock_soar.execute.return_value = {
            "answer": "Goal achieved!",
            "confidence": 0.95,
            "cost_usd": 0.5,
        }
        mock_soar.reasoning_llm.complete.return_value = {"content": "GOAL_ACHIEVED"}

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        with patch.object(orchestrator, "start_time", datetime.now().timestamp()):
            result = orchestrator.execute()

        assert result.goal_achieved is True
        assert result.termination_reason == TerminationReason.GOAL_ACHIEVED
        assert result.iterations == 1
        assert result.total_cost == 0.5
        assert result.duration_seconds >= 0
        assert result.scratchpad_path == scratchpad_file
        assert result.error_message is None

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_execute_git_error(
        self, mock_git_class, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test execution with git validation error."""

        # Use lambda to ensure exception is raised consistently across Python versions
        def raise_git_error():
            raise GitBranchError("Not on headless branch")

        mock_git = Mock()
        mock_git.validate.side_effect = raise_git_error
        mock_git_class.return_value = mock_git

        mock_prompt = Mock()
        mock_prompt.validate_format.return_value = (True, [])
        # Configure load() to return valid PromptData
        mock_prompt.load.return_value = PromptData(
            goal="Test goal",
            success_criteria=["Test criterion"],
            constraints=["Test constraint"],
            context=None,
        )
        mock_prompt_class.return_value = mock_prompt

        # Configure scratchpad mock
        mock_scratchpad = Mock()
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.GIT_SAFETY_ERROR
        assert result.iterations == 0
        assert result.total_cost == 0.0
        assert "Not on headless branch" in result.error_message

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_execute_prompt_error(
        self, mock_git_class, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test execution with prompt validation error."""
        mock_git = Mock()
        mock_git.validate.return_value = None
        mock_git_class.return_value = mock_git

        mock_prompt = Mock()
        mock_prompt.validate_format.return_value = (False, ["Missing goal section"])
        # Configure load() even though it shouldn't be called
        mock_prompt.load.return_value = PromptData(
            goal="Test goal",
            success_criteria=["Test criterion"],
            constraints=["Test constraint"],
            context=None,
        )
        mock_prompt_class.return_value = mock_prompt

        # Configure scratchpad mock
        mock_scratchpad = Mock()
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.PROMPT_ERROR
        assert result.iterations == 0
        assert result.total_cost == 0.0
        assert "Prompt validation failed" in result.error_message

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_execute_unexpected_error(
        self, mock_git_class, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test execution with unexpected error."""

        # Use lambda to ensure exception is raised consistently
        def raise_unexpected_error():
            raise RuntimeError("Unexpected error")

        mock_git = Mock()
        mock_git.validate.side_effect = raise_unexpected_error
        mock_git_class.return_value = mock_git

        mock_prompt = Mock()
        mock_prompt.validate_format.return_value = (True, [])
        mock_prompt.load.return_value = PromptData(
            goal="Test goal",
            success_criteria=["Test criterion"],
            constraints=["Test constraint"],
            context=None,
        )
        mock_prompt_class.return_value = mock_prompt

        # Configure scratchpad mock
        mock_scratchpad = Mock()
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()

        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.BLOCKED
        assert result.error_message is not None
        assert "Unexpected error" in result.error_message

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_execute_max_iterations(
        self, mock_git_class, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test execution reaching max iterations."""
        # Setup mocks
        mock_git = Mock()
        mock_git.validate.return_value = None
        mock_git_class.return_value = mock_git

        mock_prompt = Mock()
        mock_prompt.validate_format.return_value = (True, [])
        mock_prompt.load.return_value = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )
        mock_prompt_class.return_value = mock_prompt

        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.execute.return_value = {
            "answer": "Working on it",
            "confidence": 0.7,
            "cost_usd": 0.1,
        }
        mock_soar.reasoning_llm.complete.return_value = {"content": "IN_PROGRESS"}

        config = HeadlessConfig(max_iterations=2)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.MAX_ITERATIONS
        assert result.iterations == 2
        assert result.total_cost == 0.2

    @patch("aurora_soar.headless.orchestrator.ScratchpadManager")
    @patch("aurora_soar.headless.orchestrator.PromptLoader")
    @patch("aurora_soar.headless.orchestrator.GitEnforcer")
    def test_execute_budget_exceeded(
        self, mock_git_class, mock_prompt_class, mock_scratchpad_class, prompt_file, scratchpad_file
    ):
        """Test execution with budget exceeded."""
        mock_git = Mock()
        mock_git.validate.return_value = None
        mock_git_class.return_value = mock_git

        mock_prompt = Mock()
        mock_prompt.validate_format.return_value = (True, [])
        mock_prompt.load.return_value = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=["Constraint 1"],
            context="Test context",
        )
        mock_prompt_class.return_value = mock_prompt

        mock_scratchpad = Mock()
        mock_scratchpad.read.return_value = "Scratchpad content"
        mock_scratchpad_class.return_value = mock_scratchpad

        mock_soar = Mock()
        mock_soar.execute.return_value = {
            "answer": "Working on it",
            "confidence": 0.7,
            "cost_usd": 6.0,  # Exceeds budget
        }
        mock_soar.reasoning_llm.complete.return_value = {"content": "IN_PROGRESS"}

        config = HeadlessConfig(budget_limit=5.0, max_iterations=10)
        orchestrator = HeadlessOrchestrator(
            prompt_path=prompt_file,
            scratchpad_path=scratchpad_file,
            soar_orchestrator=mock_soar,
            config=config,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.BUDGET_EXCEEDED
        assert result.iterations == 1
        assert result.total_cost == 6.0


class TestHeadlessResult:
    """Test HeadlessResult dataclass."""

    def test_result_creation(self):
        """Test creating result object."""
        result = HeadlessResult(
            goal_achieved=True,
            termination_reason=TerminationReason.GOAL_ACHIEVED,
            iterations=5,
            total_cost=2.5,
            duration_seconds=120.5,
            scratchpad_path="/tmp/scratchpad.md",
            error_message=None,
        )

        assert result.goal_achieved is True
        assert result.termination_reason == TerminationReason.GOAL_ACHIEVED
        assert result.iterations == 5
        assert result.total_cost == 2.5
        assert result.duration_seconds == 120.5
        assert result.scratchpad_path == "/tmp/scratchpad.md"
        assert result.error_message is None

    def test_result_with_error(self):
        """Test creating result with error."""
        result = HeadlessResult(
            goal_achieved=False,
            termination_reason=TerminationReason.BLOCKED,
            iterations=3,
            total_cost=1.0,
            duration_seconds=60.0,
            scratchpad_path="/tmp/scratchpad.md",
            error_message="SOAR execution failed",
        )

        assert result.goal_achieved is False
        assert result.error_message == "SOAR execution failed"


class TestTerminationReason:
    """Test TerminationReason enum."""

    def test_all_reasons_exist(self):
        """Test all termination reasons are defined."""
        assert TerminationReason.GOAL_ACHIEVED.value == "GOAL_ACHIEVED"
        assert TerminationReason.BUDGET_EXCEEDED.value == "BUDGET_EXCEEDED"
        assert TerminationReason.MAX_ITERATIONS.value == "MAX_ITERATIONS"
        assert TerminationReason.BLOCKED.value == "BLOCKED"
        assert TerminationReason.GIT_SAFETY_ERROR.value == "GIT_SAFETY_ERROR"
        assert TerminationReason.PROMPT_ERROR.value == "PROMPT_ERROR"

    def test_reason_comparison(self):
        """Test comparing termination reasons."""
        reason1 = TerminationReason.GOAL_ACHIEVED
        reason2 = TerminationReason.GOAL_ACHIEVED
        reason3 = TerminationReason.BLOCKED

        assert reason1 == reason2
        assert reason1 != reason3
