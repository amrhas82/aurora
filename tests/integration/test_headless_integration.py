"""
Integration tests for simplified headless execution.

This test suite verifies that the simplified HeadlessOrchestrator works end-to-end with all
components integrated:
- GitEnforcer validates branch safety
- PromptLoader loads and parses experiment prompt
- Scratchpad tracks single iteration
- Main loop executes one SOAR iteration
- Goal evaluation detects completion

Test Strategy:
1. Create mock SOAR orchestrator that simulates LLM responses
2. Set up test fixtures (prompt.md, scratchpad.md)
3. Test different scenarios:
   - Successful single iteration execution
   - Git branch enforcement blocks unsafe branches
   - Invalid prompt rejection
   - Scratchpad captures execution details

Integration Points:
- HeadlessOrchestrator.execute() is the main entry point
- GitEnforcer.validate() checks branch safety
- PromptLoader.load() parses experiment definition
- Scratchpad manages iteration logs
- SOAR orchestrator executes single iteration
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class MockSOAROrchestrator:
    """Mock SOAR orchestrator for integration testing."""

    def __init__(
        self,
        success: bool = True,
        cost_usd: float = 0.50,
        should_fail: bool = False,
    ):
        """
        Initialize mock SOAR orchestrator.

        Args:
            success: If True, return successful result
            cost_usd: Cost in USD for the iteration
            should_fail: If True, raise error on execute
        """
        self.success = success
        self.cost_usd = cost_usd
        self.should_fail = should_fail
        self.call_count = 0
        self.calls = []

    def execute(self, query: str, **kwargs) -> dict:
        """
        Execute a SOAR iteration.

        Args:
            query: The query/prompt for this iteration
            **kwargs: Additional arguments

        Returns:
            Execution result with answer and cost
        """
        self.call_count += 1
        self.calls.append(
            {
                "query": query,
                "iteration": self.call_count,
            }
        )

        if self.should_fail:
            raise RuntimeError(f"SOAR execution failed at iteration {self.call_count}")

        # Simulate progress
        if self.success:
            answer = "Implementation complete! All tests passing, code coverage 95%."
        else:
            answer = f"Iteration {self.call_count} progress: implemented feature, some tests failing."

        return {
            "answer": answer,
            "cost_usd": self.cost_usd,
            "confidence": 0.85 if self.success else 0.50,
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
- Budget: 10000 tokens
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


class TestHeadlessIntegrationSuccess:
    """Test successful headless execution scenarios."""

    def test_full_workflow_with_success(self, valid_prompt_file, scratchpad_path, tmp_path):
        """Test complete workflow: load prompt → execute → verify scratchpad."""
        from aurora_soar.headless.config import HeadlessConfig
        from aurora_soar.headless.git_enforcer import GitEnforcer
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator
        from aurora_soar.headless.prompt_loader_simplified import PromptLoader
        from aurora_soar.headless.scratchpad import Scratchpad

        # Setup mock SOAR that returns success
        mock_soar = MockSOAROrchestrator(success=True, cost_usd=0.50)

        # Create config
        config = HeadlessConfig(budget=10000)

        # Mock git enforcer to pass validation
        mock_git = Mock(spec=GitEnforcer)
        mock_git.validate.return_value = None
        mock_git.get_current_branch.return_value = "feature-test"

        # Create orchestrator - it will create its own loader and scratchpad
        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git,
        )

        # Execute
        result = orchestrator.execute()

        # Verify result structure
        assert hasattr(result, "goal_achieved")
        assert hasattr(result, "total_cost")
        assert hasattr(result, "scratchpad_path")
        assert result.goal_achieved is True  # Simplified version always returns True for success
        assert result.total_cost == 0.50
        assert result.scratchpad_path == str(scratchpad_path)

        # Verify SOAR was called once
        assert mock_soar.call_count == 1

        # Verify scratchpad was created and contains execution details
        assert scratchpad_path.exists()
        scratchpad_content = scratchpad_path.read_text()
        assert len(scratchpad_content) > 0
        assert "SOAR Execution" in scratchpad_content or "Iteration" in scratchpad_content

        # Verify git validation was called
        mock_git.validate.assert_called_once()

    def test_minimal_prompt_execution(self, minimal_prompt_file, scratchpad_path, tmp_path):
        """Test execution with minimal prompt (no context, minimal constraints)."""
        from aurora_soar.headless.config import HeadlessConfig
        from aurora_soar.headless.git_enforcer import GitEnforcer
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        mock_soar = MockSOAROrchestrator(success=True, cost_usd=0.30)

        config = HeadlessConfig(budget=10000)

        # Mock git enforcer
        mock_git = Mock(spec=GitEnforcer)
        mock_git.validate.return_value = None

        orchestrator = HeadlessOrchestrator(
            prompt_path=minimal_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is True
        assert result.total_cost == 0.30


class TestHeadlessIntegrationGitSafety:
    """Test git safety enforcement."""

    def test_git_branch_safety_blocks_main_branch(
        self, valid_prompt_file, scratchpad_path, tmp_path
    ):
        """Test execution fails if git branch validation fails on main branch."""
        from aurora_soar.headless.config import HeadlessConfig
        from aurora_soar.headless.git_enforcer import GitBranchError, GitEnforcer
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        mock_soar = MockSOAROrchestrator(success=True)

        config = HeadlessConfig(budget=10000)

        # Mock git enforcer to raise error for main branch
        mock_git = Mock(spec=GitEnforcer)
        mock_git.validate.side_effect = GitBranchError(
            "Execution blocked: currently on 'main' branch"
        )

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git,
        )

        result = orchestrator.execute()

        # Verify execution was blocked
        assert result.goal_achieved is False
        assert "main" in result.error_message.lower() or "branch" in result.error_message.lower()

        # Verify SOAR was never called
        assert mock_soar.call_count == 0

    def test_git_branch_safety_blocks_master_branch(
        self, valid_prompt_file, scratchpad_path, tmp_path
    ):
        """Test execution fails if git branch validation fails on master branch."""
        from aurora_soar.headless.config import HeadlessConfig
        from aurora_soar.headless.git_enforcer import GitBranchError, GitEnforcer
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        mock_soar = MockSOAROrchestrator(success=True)

        config = HeadlessConfig(budget=10000)

        # Mock git enforcer to raise error for master branch
        mock_git = Mock(spec=GitEnforcer)
        mock_git.validate.side_effect = GitBranchError(
            "Execution blocked: currently on 'master' branch"
        )

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git,
        )

        result = orchestrator.execute()

        # Verify execution was blocked
        assert result.goal_achieved is False
        assert "master" in result.error_message.lower() or "branch" in result.error_message.lower()

        # Verify SOAR was never called
        assert mock_soar.call_count == 0


class TestHeadlessIntegrationPromptValidation:
    """Test prompt validation and error handling."""

    def test_invalid_prompt_missing_goal(self, invalid_prompt_file, scratchpad_path, tmp_path):
        """Test execution fails if prompt validation fails (missing Goal section)."""
        from aurora_soar.headless.config import HeadlessConfig
        from aurora_soar.headless.git_enforcer import GitEnforcer
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        mock_soar = MockSOAROrchestrator(success=True)

        config = HeadlessConfig(budget=10000)

        # Mock git enforcer to pass
        mock_git = Mock(spec=GitEnforcer)
        mock_git.validate.return_value = None

        orchestrator = HeadlessOrchestrator(
            prompt_path=invalid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git,
        )

        result = orchestrator.execute()

        # Verify execution failed due to prompt validation
        assert result.goal_achieved is False
        assert "goal" in result.error_message.lower() or "validation" in result.error_message.lower()

        # Verify SOAR was never called
        assert mock_soar.call_count == 0

    def test_missing_prompt_file(self, temp_workspace, scratchpad_path, tmp_path):
        """Test execution fails if prompt file doesn't exist."""
        from aurora_soar.headless.config import HeadlessConfig
        from aurora_soar.headless.git_enforcer import GitEnforcer
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        nonexistent_prompt = temp_workspace / "nonexistent.md"
        mock_soar = MockSOAROrchestrator(success=True)

        config = HeadlessConfig(budget=10000)

        # Mock git enforcer to pass
        mock_git = Mock(spec=GitEnforcer)
        mock_git.validate.return_value = None

        orchestrator = HeadlessOrchestrator(
            prompt_path=nonexistent_prompt,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git,
        )

        result = orchestrator.execute()

        # Verify execution failed
        assert result.goal_achieved is False
        assert "not found" in result.error_message.lower() or "file" in result.error_message.lower()

        # Verify SOAR was never called
        assert mock_soar.call_count == 0


class TestHeadlessIntegrationScratchpad:
    """Test scratchpad logging and state management."""

    def test_scratchpad_captures_execution_details(
        self, valid_prompt_file, scratchpad_path, tmp_path
    ):
        """Test scratchpad contains execution details after run."""
        from aurora_soar.headless.config import HeadlessConfig
        from aurora_soar.headless.git_enforcer import GitEnforcer
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        mock_soar = MockSOAROrchestrator(success=True, cost_usd=0.75)

        config = HeadlessConfig(budget=10000)

        # Mock git enforcer
        mock_git = Mock(spec=GitEnforcer)
        mock_git.validate.return_value = None

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git,
        )

        orchestrator.execute()

        # Read scratchpad
        scratchpad_content = scratchpad_path.read_text()

        # Verify scratchpad has substantial content
        assert len(scratchpad_content) > 100

        # Verify it contains key execution info (cost or status markers)
        assert "0.75" in scratchpad_content or "SOAR" in scratchpad_content or "iteration" in scratchpad_content.lower()

    def test_scratchpad_created_if_not_exists(self, valid_prompt_file, tmp_path):
        """Test scratchpad file is created if it doesn't exist."""
        from aurora_soar.headless.config import HeadlessConfig
        from aurora_soar.headless.git_enforcer import GitEnforcer
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        scratchpad_path = tmp_path / "new_scratchpad.md"

        # Verify file doesn't exist yet
        assert not scratchpad_path.exists()

        mock_soar = MockSOAROrchestrator(success=True)

        config = HeadlessConfig(budget=10000)

        # Mock git enforcer
        mock_git = Mock(spec=GitEnforcer)
        mock_git.validate.return_value = None

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git,
        )

        orchestrator.execute()

        # Verify scratchpad was created
        assert scratchpad_path.exists()
        assert len(scratchpad_path.read_text()) > 0


class TestHeadlessIntegrationConfiguration:
    """Test different configuration scenarios."""

    def test_budget_enforcement(self, valid_prompt_file, scratchpad_path, tmp_path):
        """Test budget configuration is passed to components."""
        from aurora_soar.headless.config import HeadlessConfig
        from aurora_soar.headless.git_enforcer import GitEnforcer
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        # Create config with specific budget
        config = HeadlessConfig(budget=5000)

        mock_soar = MockSOAROrchestrator(success=True, cost_usd=0.40)

        # Mock git enforcer
        mock_git = Mock(spec=GitEnforcer)
        mock_git.validate.return_value = None

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git,
        )

        # Verify config is used
        assert orchestrator.config.budget == 5000

        result = orchestrator.execute()

        # Should succeed with 0.40 USD under budget
        assert result.goal_achieved is True
        assert result.total_cost == 0.40


class TestHeadlessIntegrationEdgeCases:
    """Test edge cases and error scenarios."""

    def test_soar_execution_failure(self, valid_prompt_file, scratchpad_path, tmp_path):
        """Test handling of SOAR execution failure."""
        from aurora_soar.headless.config import HeadlessConfig
        from aurora_soar.headless.git_enforcer import GitEnforcer
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        # Mock SOAR that raises exception
        mock_soar = MockSOAROrchestrator(should_fail=True)

        config = HeadlessConfig(budget=10000)

        # Mock git enforcer
        mock_git = Mock(spec=GitEnforcer)
        mock_git.validate.return_value = None

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git,
        )

        result = orchestrator.execute()

        # Should handle error gracefully
        assert result.goal_achieved is False
        assert result.error_message is not None
        assert "error" in result.error_message.lower() or "fail" in result.error_message.lower()

    def test_zero_cost_execution(self, valid_prompt_file, scratchpad_path, tmp_path):
        """Test execution with zero cost (edge case)."""
        from aurora_soar.headless.config import HeadlessConfig
        from aurora_soar.headless.git_enforcer import GitEnforcer
        from aurora_soar.headless.orchestrator_simplified import HeadlessOrchestrator

        mock_soar = MockSOAROrchestrator(success=True, cost_usd=0.0)

        config = HeadlessConfig(budget=10000)

        # Mock git enforcer
        mock_git = Mock(spec=GitEnforcer)
        mock_git.validate.return_value = None

        orchestrator = HeadlessOrchestrator(
            prompt_path=valid_prompt_file,
            scratchpad_path=scratchpad_path,
            soar_orchestrator=mock_soar,
            config=config,
            git_enforcer=mock_git,
        )

        result = orchestrator.execute()

        assert result.goal_achieved is True
        assert result.total_cost == 0.0
