"""
Integration tests for headless execution.

This test suite verifies that the HeadlessOrchestrator works end-to-end with all
components integrated:
- GitEnforcer validates branch safety
- PromptLoader loads and parses experiment prompt
- ScratchpadManager tracks iterations
- Main loop executes until termination
- Budget tracking enforces limits
- Goal evaluation detects completion
- Max iterations prevents runaway execution

Test Strategy:
1. Create mock SOAR orchestrator that simulates LLM responses
2. Set up test fixtures (prompt.md, scratchpad.md)
3. Test different termination scenarios:
   - Goal achieved within budget and iterations
   - Budget exceeded before completion
   - Max iterations reached without goal
4. Verify scratchpad captures all iteration actions
5. Verify git branch enforcement blocks unsafe branches

Integration Points:
- HeadlessOrchestrator.execute() is the main entry point
- GitEnforcer.validate() checks branch safety
- PromptLoader.load() parses experiment definition
- ScratchpadManager manages iteration logs
- SOAR orchestrator executes each iteration
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from aurora.soar.headless.git_enforcer import GitBranchError
from aurora.soar.headless.orchestrator import (
    HeadlessConfig,
    HeadlessOrchestrator,
    TerminationReason,
)


class MockSOAROrchestrator:
    """Mock SOAR orchestrator for integration testing."""

    def __init__(
        self,
        iterations_to_success: int | None = None,
        cost_per_iteration: float = 0.25,
        should_fail: bool = False,
    ):
        """
        Initialize mock SOAR orchestrator.

        Args:
            iterations_to_success: Number of iterations before goal achieved (None = never)
            cost_per_iteration: Cost in USD for each iteration
            should_fail: If True, raise error on execute
        """
        self.iterations_to_success = iterations_to_success
        self.cost_per_iteration = cost_per_iteration
        self.should_fail = should_fail
        self.call_count = 0
        self.calls = []

        # Mock reasoning_llm for goal evaluation
        self.reasoning_llm = Mock()
        self.reasoning_llm.complete = self._mock_llm_complete

    def _mock_llm_complete(self, prompt: str, max_tokens: int = 50, **kwargs) -> dict:
        """
        Mock LLM completion for goal evaluation.

        Returns "GOAL_ACHIEVED" if iterations_to_success met, otherwise "IN_PROGRESS".
        """
        if self.iterations_to_success and self.call_count >= self.iterations_to_success:
            return {"content": "GOAL_ACHIEVED"}
        return {"content": "IN_PROGRESS"}

    def execute(
        self, query: str, verbosity: str = "NORMAL", max_cost_usd: float = None, **kwargs
    ) -> dict:
        """
        Execute a SOAR iteration.

        Args:
            query: The query/prompt for this iteration
            verbosity: Verbosity level (not used in mock)
            max_cost_usd: Max cost allowed (not enforced in mock)
            **kwargs: Additional arguments

        Returns:
            Execution result with answer and cost
        """
        self.call_count += 1
        self.calls.append(
            {
                "query": query,
                "verbosity": verbosity,
                "max_cost_usd": max_cost_usd,
                "iteration": self.call_count,
            }
        )

        if self.should_fail:
            raise RuntimeError(f"SOAR execution failed at iteration {self.call_count}")

        # Simulate progress
        if self.iterations_to_success and self.call_count >= self.iterations_to_success:
            answer = "Implementation complete! All tests passing, code coverage 95%."
        else:
            answer = (
                f"Iteration {self.call_count} progress: implemented feature, some tests failing."
            )

        return {
            "answer": answer,
            "cost_usd": self.cost_per_iteration,  # Note: orchestrator looks for "cost_usd"
            "confidence": 0.85,
            "iterations": 1,
            "agents_executed": ["planner", "coder", "tester"],
        }


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        yield workspace


@pytest.fixture
def valid_prompt_file(temp_workspace):
    """Create a valid prompt file."""
    prompt_path = temp_workspace / "prompt.md"
    prompt_path.write_text(
        """# Goal
Implement user authentication with login and logout functionality

# Success Criteria
- Users can register with email and password
- Users can login with credentials
- Users can logout
- All tests pass
- Code coverage >90%

# Constraints
- Budget limit: $5.00
- Max iterations: 10
- Must use bcrypt for password hashing

# Context
This is for a Flask web application. User table already exists in database.
"""
    )
    return prompt_path


@pytest.fixture
def minimal_prompt_file(temp_workspace):
    """Create a minimal valid prompt file."""
    prompt_path = temp_workspace / "prompt_minimal.md"
    prompt_path.write_text(
        """# Goal
Fix the login bug

# Success Criteria
- Bug is fixed
- Tests pass

# Constraints
"""
    )
    return prompt_path


@pytest.fixture
def invalid_prompt_file(temp_workspace):
    """Create an invalid prompt file (missing Goal)."""
    prompt_path = temp_workspace / "prompt_invalid.md"
    prompt_path.write_text(
        """# Success Criteria
- Criterion 1

# Constraints
- Constraint 1
"""
    )
    return prompt_path


@pytest.fixture
def scratchpad_path(temp_workspace):
    """Return path for scratchpad (will be auto-created)."""
    return temp_workspace / "scratchpad.md"


class TestHeadlessExecutionSuccess:
    """Test successful headless execution scenarios."""

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_goal_achieved_within_budget(
        self, mock_git_validate, valid_prompt_file, scratchpad_path
    ):
        """Test successful execution when goal is achieved within budget and iterations."""
        # Setup: Goal achieved after 3 iterations
        mock_soar = MockSOAROrchestrator(iterations_to_success=3, cost_per_iteration=0.50)

        config = HeadlessConfig(
            max_iterations=10,
            budget_limit=5.0,
            required_branch="headless",
        )

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
        )

        # Mock goal evaluation to return IN_PROGRESS for first 2 iterations, then GOAL_ACHIEVED
        evaluation_returns = ["IN_PROGRESS", "IN_PROGRESS", "GOAL_ACHIEVED"]
        with patch.object(
            orchestrator, "_evaluate_goal_achievement", side_effect=evaluation_returns
        ):
            # Execute
            result = orchestrator.execute()

        # Verify result
        assert result.goal_achieved is True
        assert result.termination_reason == TerminationReason.GOAL_ACHIEVED
        assert result.iterations == 3
        assert result.total_cost == 1.50  # 3 iterations × $0.50
        assert result.error_message is None

        # Verify SOAR was called correct number of times
        assert mock_soar.call_count == 3

        # Verify scratchpad was created and contains iterations
        assert scratchpad_path.exists()
        scratchpad_content = scratchpad_path.read_text()
        assert "## Iteration 1" in scratchpad_content
        assert "## Iteration 2" in scratchpad_content
        assert "## Iteration 3" in scratchpad_content
        assert "GOAL_ACHIEVED" in scratchpad_content or "COMPLETED" in scratchpad_content

        # Verify git validation was called
        mock_git_validate.assert_called_once()

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_minimal_prompt_execution(
        self, mock_git_validate, minimal_prompt_file, scratchpad_path
    ):
        """Test execution with minimal prompt (no context, minimal constraints)."""
        mock_soar = MockSOAROrchestrator(iterations_to_success=2, cost_per_iteration=0.30)

        config = HeadlessConfig(max_iterations=5, budget_limit=2.0)

        orchestrator = HeadlessOrchestrator(
            prompt_path=minimal_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is True
        assert result.iterations == 2
        assert result.total_cost == 0.60


class TestHeadlessExecutionBudgetExceeded:
    """Test budget limit enforcement."""

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_budget_exceeded_before_goal(
        self, mock_git_validate, valid_prompt_file, scratchpad_path
    ):
        """Test execution terminates when budget is exceeded before goal is achieved."""
        # Setup: Never achieves goal, costs $1.50 per iteration, budget is $5.00
        mock_soar = MockSOAROrchestrator(
            iterations_to_success=None,  # Never succeeds
            cost_per_iteration=1.50,
        )

        config = HeadlessConfig(
            max_iterations=10,
            budget_limit=5.0,  # Will exceed after 3 iterations (3 × $1.50 = $4.50)
            required_branch="headless",
        )

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
        )

        result = orchestrator.execute()

        # Verify termination due to budget
        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.BUDGET_EXCEEDED
        assert result.iterations <= 4  # Should stop around iteration 3-4
        assert result.total_cost >= 4.50  # Exceeded budget

        # Verify scratchpad shows budget exceeded
        scratchpad_content = scratchpad_path.read_text()
        assert "BUDGET_EXCEEDED" in scratchpad_content

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_budget_exactly_at_limit(self, mock_git_validate, valid_prompt_file, scratchpad_path):
        """Test execution when budget is exactly at the limit."""
        # Setup: Costs exactly $1.00 per iteration, budget is $3.00
        mock_soar = MockSOAROrchestrator(
            iterations_to_success=None,  # Never succeeds
            cost_per_iteration=1.00,
        )

        config = HeadlessConfig(
            max_iterations=10,
            budget_limit=3.0,  # Will run exactly 3 iterations
        )

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
        )

        result = orchestrator.execute()

        # Should stop at or right after hitting budget
        assert result.iterations in [3, 4]  # Might check budget after iteration completes
        assert result.total_cost >= 3.0


class TestHeadlessExecutionMaxIterations:
    """Test max iterations enforcement."""

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_max_iterations_reached(self, mock_git_validate, valid_prompt_file, scratchpad_path):
        """Test execution terminates when max iterations is reached without achieving goal."""
        # Setup: Never achieves goal, low cost per iteration
        mock_soar = MockSOAROrchestrator(
            iterations_to_success=None,  # Never succeeds
            cost_per_iteration=0.20,
        )

        config = HeadlessConfig(
            max_iterations=5,  # Low iteration limit
            budget_limit=10.0,  # High budget (won't be the limiting factor)
        )

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
        )

        result = orchestrator.execute()

        # Verify termination due to max iterations
        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.MAX_ITERATIONS
        assert result.iterations == 5
        assert result.total_cost == 1.00  # 5 iterations × $0.20

        # Verify scratchpad shows max iterations
        scratchpad_content = scratchpad_path.read_text()
        assert "MAX_ITERATIONS" in scratchpad_content or "Iteration 5" in scratchpad_content

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_max_iterations_one(self, mock_git_validate, valid_prompt_file, scratchpad_path):
        """Test execution with max_iterations=1 (edge case)."""
        mock_soar = MockSOAROrchestrator(
            iterations_to_success=None,
            cost_per_iteration=0.10,
        )

        config = HeadlessConfig(max_iterations=1, budget_limit=10.0)

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
        )

        result = orchestrator.execute()

        assert result.iterations == 1
        assert result.termination_reason == TerminationReason.MAX_ITERATIONS


class TestHeadlessExecutionSafetyValidation:
    """Test safety validation and error handling."""

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_git_branch_safety_error(self, mock_git_validate, valid_prompt_file, scratchpad_path):
        """Test execution fails if git branch validation fails."""
        # Setup: Git validation raises error
        mock_git_validate.side_effect = GitBranchError(
            "Execution blocked: currently on 'main' branch. Switch to 'headless' branch."
        )

        mock_soar = MockSOAROrchestrator(iterations_to_success=2)

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
        )

        result = orchestrator.execute()

        # Verify termination due to git safety
        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.GIT_SAFETY_ERROR
        assert result.iterations == 0  # Should not execute any iterations
        assert "main" in result.error_message or "branch" in result.error_message.lower()

        # Verify SOAR was never called
        assert mock_soar.call_count == 0

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_invalid_prompt_error(self, mock_git_validate, invalid_prompt_file, scratchpad_path):
        """Test execution fails if prompt validation fails."""
        mock_soar = MockSOAROrchestrator(iterations_to_success=2)

        orchestrator = HeadlessOrchestrator(
            prompt_path=invalid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
        )

        result = orchestrator.execute()

        # Verify termination due to prompt error
        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.PROMPT_ERROR
        assert result.iterations == 0
        assert "Goal" in result.error_message or "validation" in result.error_message.lower()

        # Verify SOAR was never called
        assert mock_soar.call_count == 0

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_missing_prompt_file(self, mock_git_validate, temp_workspace, scratchpad_path):
        """Test execution fails if prompt file doesn't exist."""
        nonexistent_prompt = temp_workspace / "nonexistent.md"
        mock_soar = MockSOAROrchestrator(iterations_to_success=2)

        orchestrator = HeadlessOrchestrator(
            prompt_path=nonexistent_prompt,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is False
        assert result.termination_reason == TerminationReason.PROMPT_ERROR
        assert result.iterations == 0
        assert "not found" in result.error_message.lower() or "file" in result.error_message.lower()


class TestHeadlessExecutionScratchpadLogging:
    """Test scratchpad logging captures iteration actions."""

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_scratchpad_captures_all_iterations(
        self, mock_git_validate, valid_prompt_file, scratchpad_path
    ):
        """Test scratchpad contains entry for every iteration."""
        mock_soar = MockSOAROrchestrator(
            iterations_to_success=4,
            cost_per_iteration=0.25,
        )

        config = HeadlessConfig(max_iterations=10, budget_limit=5.0)

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.execute()

        # Read scratchpad
        scratchpad_content = scratchpad_path.read_text()

        # Verify all iterations are logged
        for i in range(1, 5):
            assert f"## Iteration {i}" in scratchpad_content

        # Verify cost tracking
        assert "$0.25" in scratchpad_content or "0.25" in scratchpad_content

        # Verify status tracking
        assert "Status" in scratchpad_content or "STATUS" in scratchpad_content

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_scratchpad_shows_termination_reason(
        self, mock_git_validate, valid_prompt_file, scratchpad_path
    ):
        """Test scratchpad contains termination reason."""
        # Test budget exceeded
        mock_soar = MockSOAROrchestrator(
            iterations_to_success=None,
            cost_per_iteration=2.00,
        )

        config = HeadlessConfig(max_iterations=10, budget_limit=3.0)

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
        )

        orchestrator.execute()

        scratchpad_content = scratchpad_path.read_text()
        assert "BUDGET" in scratchpad_content.upper() or "EXCEEDED" in scratchpad_content.upper()


class TestHeadlessExecutionConfiguration:
    """Test different configuration scenarios."""

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_custom_branch_requirement(self, mock_git_validate, valid_prompt_file, scratchpad_path):
        """Test execution with custom required branch name."""
        mock_soar = MockSOAROrchestrator(iterations_to_success=2)

        config = HeadlessConfig(
            max_iterations=5,
            budget_limit=5.0,
            required_branch="experiment-123",  # Custom branch
        )

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
        )

        # Should succeed (mocked git validation)
        result = orchestrator.execute()
        assert result.goal_achieved is True

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_high_budget_limit(self, mock_git_validate, valid_prompt_file, scratchpad_path):
        """Test execution with high budget limit."""
        mock_soar = MockSOAROrchestrator(
            iterations_to_success=3,
            cost_per_iteration=5.00,  # High cost
        )

        config = HeadlessConfig(
            max_iterations=10,
            budget_limit=20.0,  # High budget
        )

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is True
        assert result.total_cost == 15.0  # 3 iterations × $5.00


class TestHeadlessExecutionEdgeCases:
    """Test edge cases and corner scenarios."""

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_goal_achieved_on_first_iteration(
        self, mock_git_validate, valid_prompt_file, scratchpad_path
    ):
        """Test execution when goal is achieved on first iteration."""
        mock_soar = MockSOAROrchestrator(
            iterations_to_success=1,  # Succeed immediately
            cost_per_iteration=0.10,
        )

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is True
        assert result.iterations == 1
        assert result.total_cost == 0.10

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_zero_cost_iterations(self, mock_git_validate, valid_prompt_file, scratchpad_path):
        """Test execution with zero-cost iterations (edge case)."""
        mock_soar = MockSOAROrchestrator(
            iterations_to_success=3,
            cost_per_iteration=0.0,  # Zero cost
        )

        config = HeadlessConfig(max_iterations=10, budget_limit=1.0)

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is True
        assert result.total_cost == 0.0

    @patch("aurora.soar.headless.orchestrator.GitEnforcer.validate")
    def test_scratchpad_survives_multiple_runs(
        self, mock_git_validate, valid_prompt_file, scratchpad_path
    ):
        """Test scratchpad persists across multiple orchestrator runs."""
        # First run
        mock_soar_1 = MockSOAROrchestrator(iterations_to_success=2, cost_per_iteration=0.20)
        orchestrator_1 = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar_1,
        )
        orchestrator_1.execute()

        # Verify scratchpad exists
        assert scratchpad_path.exists()
        first_content = scratchpad_path.read_text()
        assert "## Iteration 1" in first_content

        # Second run (should append to existing scratchpad or create backup)
        mock_soar_2 = MockSOAROrchestrator(iterations_to_success=1, cost_per_iteration=0.15)
        orchestrator_2 = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar_2,
        )
        result_2 = orchestrator_2.execute()

        # Verify second run succeeded
        assert result_2.goal_achieved is True
