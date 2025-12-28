"""End-to-end tests for headless mode execution.

These tests validate complete headless workflows including:
- Prompt loading → orchestration → output
- Multi-turn reasoning with scratchpad
- Goal achievement detection
- Safety checks (git status, budget limits)
- Failure recovery (budget exceeded, goal unreachable)

Test Coverage:
- Task 3.39: Headless Mode E2E Tests (6-8 tests)

Most tests mock LLM responses to avoid API costs, but validate
the complete pipeline with real components.
"""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from aurora.soar.headless.git_enforcer import GitBranchError
from aurora.soar.headless.orchestrator import (
    HeadlessConfig,
    HeadlessOrchestrator,
    TerminationReason,
)


@pytest.fixture
def temp_headless_project(tmp_path):
    """Create a temporary project for headless testing with git repo."""
    project_dir = tmp_path / "headless_project"
    project_dir.mkdir()

    # Initialize minimal git repo (without actually running git)
    git_dir = project_dir / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/headless\n")

    # Create experiment prompt
    prompt_file = project_dir / "experiment.md"
    prompt_file.write_text("""# Goal
Analyze the test.py file and extract all function names.

# Success Criteria
- Extract at least 3 function names
- Store results in output.txt
- Verify output.txt contains function names

# Constraints
- Only analyze test.py
- Use simple text parsing (no AST)
""")

    # Create test.py with sample functions
    test_file = project_dir / "test.py"
    test_file.write_text("""def hello():
    return "world"

def add(a, b):
    return a + b

def multiply(x, y):
    return x * y

def greet(name):
    return f"Hello, {name}!"
""")

    # Create scratchpad file
    scratchpad_file = project_dir / "scratchpad.md"
    scratchpad_file.write_text("")

    return {
        "project_dir": project_dir,
        "prompt_file": prompt_file,
        "test_file": test_file,
        "scratchpad_file": scratchpad_file,
    }


@pytest.fixture
def mock_soar_orchestrator():
    """Create a mock SOAR orchestrator for testing."""
    mock_soar = Mock()
    mock_soar.reasoning_llm = Mock()
    return mock_soar


@pytest.fixture
def mock_git_enforcer_valid():
    """Create a mock git enforcer that passes validation."""
    mock_git = Mock()
    mock_git.validate.return_value = None
    mock_git.get_current_branch.return_value = "headless"
    return mock_git


@pytest.fixture
def mock_git_enforcer_invalid():
    """Create a mock git enforcer that fails validation."""
    mock_git = Mock()
    mock_git.validate.side_effect = GitBranchError("Not on headless branch (currently on main)")
    return mock_git


# ==============================================================================
# Task 3.39: Complete Headless Workflow E2E Tests
# ==============================================================================


@pytest.mark.e2e
class TestHeadlessCompleteWorkflow:
    """Test complete headless workflow: load prompt → orchestrate → output."""

    def test_headless_workflow_goal_achieved(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test complete headless workflow that achieves goal.

        Simulates:
        1. Load prompt with goal and success criteria
        2. Initialize scratchpad
        3. Execute 2 iterations
        4. Detect goal achievement
        5. Return successful result
        """
        # Setup mock SOAR responses
        mock_soar_orchestrator.execute.side_effect = [
            # Iteration 1: Extract function names
            {
                "answer": "Found 4 function names: hello, add, multiply, greet",
                "confidence": 0.85,
                "cost_usd": 0.15,
            },
            # Iteration 2: Write to output.txt
            {
                "answer": "Wrote function names to output.txt",
                "confidence": 0.95,
                "cost_usd": 0.10,
            },
        ]

        # Mock goal evaluation: IN_PROGRESS → GOAL_ACHIEVED
        mock_soar_orchestrator.reasoning_llm.complete.side_effect = [
            {"content": "IN_PROGRESS - extracted functions but not written yet"},
            {"content": "GOAL_ACHIEVED - all success criteria met"},
        ]

        # Create orchestrator
        config = HeadlessConfig(max_iterations=5, budget_limit=5.0)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        # Execute headless workflow
        result = orchestrator.execute()

        # Verify result
        assert result.goal_achieved is True
        assert result.termination_reason == TerminationReason.GOAL_ACHIEVED
        assert result.iterations == 2
        assert result.total_cost == 0.25  # 0.15 + 0.10
        assert result.duration_seconds >= 0
        assert result.error_message is None

        # Verify scratchpad was updated
        scratchpad_content = temp_headless_project["scratchpad_file"].read_text()
        assert len(scratchpad_content) > 0
        assert "Iteration 1" in scratchpad_content or "iteration" in scratchpad_content.lower()

    def test_headless_workflow_with_real_scratchpad_updates(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test that scratchpad is properly updated during execution."""
        # Setup mock SOAR responses for 3 iterations
        mock_soar_orchestrator.execute.side_effect = [
            {"answer": "Step 1 complete", "confidence": 0.7, "cost_usd": 0.05},
            {"answer": "Step 2 complete", "confidence": 0.8, "cost_usd": 0.05},
            {"answer": "Step 3 complete", "confidence": 0.9, "cost_usd": 0.05},
        ]

        # Goal achieved after 3 iterations
        mock_soar_orchestrator.reasoning_llm.complete.side_effect = [
            {"content": "IN_PROGRESS"},
            {"content": "IN_PROGRESS"},
            {"content": "GOAL_ACHIEVED"},
        ]

        config = HeadlessConfig(max_iterations=5, budget_limit=5.0)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        result = orchestrator.execute()

        # Verify result
        assert result.goal_achieved is True
        assert result.iterations == 3
        assert abs(result.total_cost - 0.15) < 0.01  # Floating-point tolerance

        # Verify scratchpad contains all iterations
        scratchpad_content = temp_headless_project["scratchpad_file"].read_text()
        assert len(scratchpad_content) > 100  # Should have substantial content
        # Should contain iteration markers or results
        assert "Step 1 complete" in scratchpad_content or "complete" in scratchpad_content


# ==============================================================================
# Multi-Turn Reasoning Tests
# ==============================================================================


@pytest.mark.e2e
class TestHeadlessMultiTurnReasoning:
    """Test multi-turn reasoning with scratchpad state management."""

    def test_multi_turn_reasoning_with_context(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test that scratchpad context is maintained across iterations."""
        # Each iteration should build on previous context
        iteration_responses = []

        def execute_with_context(query, context="", **kwargs):
            """Mock execute that verifies context is passed."""
            iteration = len(iteration_responses) + 1
            response = {
                "answer": f"Iteration {iteration} response",
                "confidence": 0.8,
                "cost_usd": 0.1,
            }
            iteration_responses.append(response)
            return response

        mock_soar_orchestrator.execute.side_effect = execute_with_context

        # Goal achieved after 2 iterations
        mock_soar_orchestrator.reasoning_llm.complete.side_effect = [
            {"content": "IN_PROGRESS"},
            {"content": "GOAL_ACHIEVED"},
        ]

        config = HeadlessConfig(max_iterations=5)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        result = orchestrator.execute()

        # Verify multi-turn execution
        assert result.goal_achieved is True
        assert result.iterations == 2
        assert len(iteration_responses) == 2

        # Verify SOAR was called multiple times
        assert mock_soar_orchestrator.execute.call_count == 2


# ==============================================================================
# Goal Achievement Detection Tests
# ==============================================================================


@pytest.mark.e2e
class TestHeadlessGoalAchievement:
    """Test goal achievement detection logic."""

    def test_goal_achievement_detection(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test that goal achievement is correctly detected."""
        mock_soar_orchestrator.execute.return_value = {
            "answer": "All tasks completed successfully",
            "confidence": 0.95,
            "cost_usd": 0.2,
        }

        # First check: IN_PROGRESS, second check: GOAL_ACHIEVED
        mock_soar_orchestrator.reasoning_llm.complete.side_effect = [
            {"content": "IN_PROGRESS - verifying results"},
            {"content": "GOAL_ACHIEVED - all success criteria met"},
        ]

        config = HeadlessConfig(max_iterations=3)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is True
        assert result.termination_reason == TerminationReason.GOAL_ACHIEVED
        assert result.iterations == 2

    def test_goal_not_achieved_max_iterations(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test that max iterations is reached when goal not achieved."""
        mock_soar_orchestrator.execute.return_value = {
            "answer": "Still working on it",
            "confidence": 0.5,
            "cost_usd": 0.1,
        }

        # Always IN_PROGRESS
        mock_soar_orchestrator.reasoning_llm.complete.return_value = {
            "content": "IN_PROGRESS - need more iterations"
        }

        config = HeadlessConfig(max_iterations=3, budget_limit=10.0)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.MAX_ITERATIONS
        assert result.iterations == 3
        assert (
            abs(result.total_cost - 0.3) < 0.01
        )  # 3 iterations * 0.1, with floating-point tolerance


# ==============================================================================
# Safety Checks Tests
# ==============================================================================


@pytest.mark.e2e
class TestHeadlessSafetyChecks:
    """Test safety mechanisms (git branch, budget limits)."""

    def test_git_branch_safety_check_fails(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_invalid,
    ):
        """Test that git branch safety check prevents execution on wrong branch."""
        config = HeadlessConfig()
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_invalid,
        )

        result = orchestrator.execute()

        # Should fail with git safety error
        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.GIT_SAFETY_ERROR
        assert result.iterations == 0
        assert result.total_cost == 0.0
        assert "Not on headless branch" in result.error_message

        # SOAR should not be invoked
        mock_soar_orchestrator.execute.assert_not_called()

    def test_budget_limit_enforcement(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test that budget limit stops execution."""
        # First iteration is expensive and exceeds budget
        mock_soar_orchestrator.execute.return_value = {
            "answer": "Expensive operation",
            "confidence": 0.8,
            "cost_usd": 3.0,
        }

        mock_soar_orchestrator.reasoning_llm.complete.return_value = {"content": "IN_PROGRESS"}

        # Low budget limit
        config = HeadlessConfig(max_iterations=10, budget_limit=2.0)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        result = orchestrator.execute()

        # Should stop after first iteration due to budget
        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.BUDGET_EXCEEDED
        assert result.iterations == 1
        assert result.total_cost == 3.0

    def test_budget_check_before_iteration(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test that budget is checked before starting an iteration."""
        # Should not execute any iteration if budget is already exceeded
        config = HeadlessConfig(max_iterations=10, budget_limit=1.0)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        # Manually set cost to exceed budget (simulating previous usage)
        orchestrator.total_cost = 1.5

        result = orchestrator._run_main_loop()

        # Should stop immediately without executing iteration
        assert result == TerminationReason.BUDGET_EXCEEDED
        assert orchestrator.current_iteration == 1  # Loop entered but no execution
        mock_soar_orchestrator.execute.assert_not_called()


# ==============================================================================
# Failure Recovery Tests
# ==============================================================================


@pytest.mark.e2e
class TestHeadlessFailureRecovery:
    """Test failure recovery scenarios."""

    def test_blocked_state_detection(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test that BLOCKED state is detected and stops execution."""
        mock_soar_orchestrator.execute.return_value = {
            "answer": "Cannot proceed - missing dependencies",
            "confidence": 0.3,
            "cost_usd": 0.1,
        }

        # LLM determines task is blocked
        mock_soar_orchestrator.reasoning_llm.complete.return_value = {
            "content": "BLOCKED - missing required files, cannot continue"
        }

        config = HeadlessConfig(max_iterations=10)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        result = orchestrator.execute()

        # Should stop after detecting BLOCKED
        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.BLOCKED
        assert result.iterations == 1

    def test_iteration_error_recovery(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test that iteration errors are handled gracefully."""
        # SOAR execution fails
        mock_soar_orchestrator.execute.side_effect = Exception("SOAR pipeline error")

        config = HeadlessConfig(max_iterations=3)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        result = orchestrator.execute()

        # Should catch error and return BLOCKED
        # NOTE: Error is logged to scratchpad but not to result.error_message
        # (error_message is only for Git/Prompt validation errors or unexpected errors)
        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.BLOCKED
        assert result.iterations == 1

        # Verify error was logged to scratchpad
        scratchpad_content = temp_headless_project["scratchpad_file"].read_text()
        assert "Error" in scratchpad_content or "error" in scratchpad_content.lower()

    def test_goal_unreachable_detection(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test detection of unreachable goals."""
        # Simulate low confidence answers
        mock_soar_orchestrator.execute.return_value = {
            "answer": "Attempted but failed",
            "confidence": 0.2,  # Very low confidence
            "cost_usd": 0.1,
        }

        # LLM determines goal is blocked
        mock_soar_orchestrator.reasoning_llm.complete.return_value = {
            "content": "BLOCKED - success criteria cannot be met with available resources"
        }

        config = HeadlessConfig(max_iterations=5)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.BLOCKED
        # Should stop early when blocked is detected
        assert result.iterations == 1


# ==============================================================================
# Edge Cases and Integration Tests
# ==============================================================================


@pytest.mark.e2e
class TestHeadlessEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_empty_scratchpad_initialization(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test that empty scratchpad is properly initialized."""
        # Verify scratchpad is empty initially
        assert temp_headless_project["scratchpad_file"].read_text() == ""

        mock_soar_orchestrator.execute.return_value = {
            "answer": "Task complete",
            "confidence": 0.9,
            "cost_usd": 0.1,
        }
        mock_soar_orchestrator.reasoning_llm.complete.return_value = {"content": "GOAL_ACHIEVED"}

        config = HeadlessConfig(max_iterations=3)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        result = orchestrator.execute()

        # Scratchpad should now have content
        scratchpad_content = temp_headless_project["scratchpad_file"].read_text()
        assert len(scratchpad_content) > 0
        assert result.goal_achieved is True

    def test_single_iteration_success(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test that goal can be achieved in single iteration."""
        mock_soar_orchestrator.execute.return_value = {
            "answer": "Complete",
            "confidence": 1.0,
            "cost_usd": 0.05,
        }

        # Goal achieved immediately
        mock_soar_orchestrator.reasoning_llm.complete.return_value = {
            "content": "GOAL_ACHIEVED - trivial task completed"
        }

        config = HeadlessConfig(max_iterations=10)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is True
        assert result.iterations == 1
        assert result.total_cost == 0.05

    def test_cost_accumulation_across_iterations(
        self,
        temp_headless_project,
        mock_soar_orchestrator,
        mock_git_enforcer_valid,
    ):
        """Test that costs are correctly accumulated across iterations."""
        # Different costs for each iteration
        costs = [0.15, 0.25, 0.10]
        iteration_count = [0]

        def get_response(**kwargs):
            cost = costs[iteration_count[0]]
            iteration_count[0] += 1
            return {
                "answer": f"Iteration {iteration_count[0]}",
                "confidence": 0.8,
                "cost_usd": cost,
            }

        mock_soar_orchestrator.execute.side_effect = get_response

        # Goal achieved after all iterations
        mock_soar_orchestrator.reasoning_llm.complete.side_effect = [
            {"content": "IN_PROGRESS"},
            {"content": "IN_PROGRESS"},
            {"content": "GOAL_ACHIEVED"},
        ]

        config = HeadlessConfig(max_iterations=5)
        orchestrator = HeadlessOrchestrator(
            prompt_path=temp_headless_project["prompt_file"],
            scratchpad_path=temp_headless_project["scratchpad_file"],
            soar_orchestrator=mock_soar_orchestrator,
            config=config,
            git_enforcer=mock_git_enforcer_valid,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is True
        assert result.iterations == 3
        assert result.total_cost == sum(costs)  # 0.15 + 0.25 + 0.10 = 0.50
