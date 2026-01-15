"""Unit tests for DecompositionReview and ExecutionPreview."""

from unittest.mock import patch

from aurora_cli.execution.review import (
    AgentGap,
    DecompositionReview,
    ExecutionPreview,
    ReviewDecision,
)


class TestDecompositionReview:
    """Test DecompositionReview functionality."""

    def test_create_review_without_gaps(self):
        """Test creating review with all agents assigned."""
        subgoals = [
            {"description": "Implement auth", "agent_id": "@full-stack-dev", "goal": "Auth"},
            {"description": "Write tests", "agent_id": "@qa-expert", "goal": "Tests"},
        ]

        review = DecompositionReview(subgoals, agent_gaps=[])

        assert len(review.subgoals) == 2
        assert len(review.agent_gaps) == 0

    def test_create_review_with_gaps(self):
        """Test creating review with agent gaps."""
        subgoals = [
            {"description": "Implement auth", "agent_id": "@full-stack-dev", "goal": "Auth"},
            {"description": "Deploy", "agent_id": "@devops-expert", "goal": "Deploy"},
        ]

        gaps = [AgentGap(subgoal_index=1, description="Deploy", required_agent="@devops-expert")]

        review = DecompositionReview(subgoals, gaps)

        assert len(review.subgoals) == 2
        assert len(review.agent_gaps) == 1
        assert review.agent_gaps[0].required_agent == "@devops-expert"

    @patch("aurora_cli.execution.review.console")
    def test_display_without_gaps(self, mock_console):
        """Test display without gaps."""
        subgoals = [
            {"description": "Implement auth", "agent_id": "@full-stack-dev", "goal": "Auth"}
        ]

        review = DecompositionReview(subgoals, [])
        review.display()

        # Should print table and summary
        assert mock_console.print.called

    @patch("aurora_cli.execution.review.console")
    def test_display_with_gaps(self, mock_console):
        """Test display with gaps."""
        subgoals = [{"description": "Deploy", "agent_id": "@devops-expert", "goal": "Deploy"}]

        gaps = [AgentGap(subgoal_index=0, description="Deploy", required_agent="@devops-expert")]

        review = DecompositionReview(subgoals, gaps)
        review.display()

        # Should print table with gap warnings
        assert mock_console.print.called

    @patch("aurora_cli.execution.review.Prompt.ask")
    def test_prompt_proceed(self, mock_ask):
        """Test prompt returns PROCEED."""
        mock_ask.return_value = "P"

        subgoals = [{"description": "Test", "agent_id": "@test", "goal": "Test"}]
        review = DecompositionReview(subgoals, [])

        decision = review.prompt()

        assert decision == ReviewDecision.PROCEED

    @patch("aurora_cli.execution.review.Prompt.ask")
    def test_prompt_fallback(self, mock_ask):
        """Test prompt returns FALLBACK."""
        mock_ask.return_value = "F"

        subgoals = [{"description": "Test", "agent_id": "@test", "goal": "Test"}]
        review = DecompositionReview(subgoals, [])

        decision = review.prompt()

        assert decision == ReviewDecision.FALLBACK

    @patch("aurora_cli.execution.review.Prompt.ask")
    def test_prompt_abort(self, mock_ask):
        """Test prompt returns ABORT."""
        mock_ask.return_value = "A"

        subgoals = [{"description": "Test", "agent_id": "@test", "goal": "Test"}]
        review = DecompositionReview(subgoals, [])

        decision = review.prompt()

        assert decision == ReviewDecision.ABORT


class TestExecutionPreview:
    """Test ExecutionPreview functionality."""

    def test_create_preview_without_gaps(self):
        """Test creating preview with all agents assigned."""
        tasks = [
            {"description": "Run tests", "agent_id": "@qa-expert", "task": "Run tests"},
            {"description": "Deploy", "agent_id": "@devops", "task": "Deploy"},
        ]

        preview = ExecutionPreview(tasks, agent_gaps=[])

        assert len(preview.tasks) == 2
        assert len(preview.agent_gaps) == 0

    def test_create_preview_with_gaps(self):
        """Test creating preview with agent gaps."""
        tasks = [
            {"description": "Run tests", "agent_id": "@qa-expert", "task": "Run tests"},
            {"description": "Deploy", "agent_id": "llm", "task": "Deploy"},
        ]

        gaps = [AgentGap(subgoal_index=1, description="Deploy", required_agent=None)]

        preview = ExecutionPreview(tasks, gaps)

        assert len(preview.tasks) == 2
        assert len(preview.agent_gaps) == 1

    @patch("aurora_cli.execution.review.console")
    def test_display_tasks(self, mock_console):
        """Test display renders tasks table."""
        tasks = [
            {"description": "Task 1", "agent_id": "@agent1", "task": "Task 1"},
            {"description": "Task 2", "agent_id": "@agent2", "task": "Task 2"},
        ]

        preview = ExecutionPreview(tasks, [])
        preview.display()

        # Should print table
        assert mock_console.print.called

    @patch("aurora_cli.execution.review.Prompt.ask")
    def test_prompt_proceed(self, mock_ask):
        """Test prompt returns PROCEED."""
        mock_ask.return_value = "p"

        tasks = [{"description": "Test", "agent_id": "@test", "task": "Test"}]
        preview = ExecutionPreview(tasks, [])

        decision = preview.prompt()

        assert decision == ReviewDecision.PROCEED

    @patch("aurora_cli.execution.review.Prompt.ask")
    def test_prompt_abort(self, mock_ask):
        """Test prompt returns ABORT."""
        mock_ask.return_value = "a"

        tasks = [{"description": "Test", "agent_id": "@test", "task": "Test"}]
        preview = ExecutionPreview(tasks, [])

        decision = preview.prompt()

        assert decision == ReviewDecision.ABORT


class TestAgentGap:
    """Test AgentGap dataclass."""

    def test_create_agent_gap(self):
        """Test creating AgentGap."""
        gap = AgentGap(
            subgoal_index=0, description="Deploy to production", required_agent="@devops-expert"
        )

        assert gap.subgoal_index == 0
        assert gap.description == "Deploy to production"
        assert gap.required_agent == "@devops-expert"

    def test_agent_gap_optional_agent(self):
        """Test AgentGap with optional required_agent."""
        gap = AgentGap(subgoal_index=1, description="Run tests")

        assert gap.subgoal_index == 1
        assert gap.description == "Run tests"
        assert gap.required_agent is None
