"""Unit tests for planning result types.

Tests result dataclasses for graceful degradation pattern:
InitResult, PlanResult, ListResult, ShowResult, ArchiveResult, PlanSummary.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from aurora_cli.planning.models import Complexity, Plan, PlanStatus, Subgoal
from aurora_cli.planning.results import (
    ArchiveResult,
    InitResult,
    ListResult,
    PlanResult,
    PlanSummary,
    ShowResult,
)


@pytest.fixture
def sample_subgoals() -> list[Subgoal]:
    """Create sample subgoals for testing."""
    return [
        Subgoal(
            id="sg-1",
            title="Implement authentication",
            description="Create OAuth2 authentication flow with JWT",
            recommended_agent="@full-stack-dev",
        ),
        Subgoal(
            id="sg-2",
            title="Write unit tests",
            description="Create comprehensive tests for auth module",
            recommended_agent="@qa-test-architect",
            dependencies=["sg-1"],
        ),
    ]


@pytest.fixture
def sample_plan(sample_subgoals: list[Subgoal]) -> Plan:
    """Create sample plan for testing."""
    return Plan(
        plan_id="0001-oauth-auth",
        goal="Implement OAuth2 authentication with JWT tokens for secure API access",
        subgoals=sample_subgoals,
        status=PlanStatus.ACTIVE,
        complexity=Complexity.MODERATE,
        agent_gaps=["@missing-agent"],
        context_sources=["indexed_memory"],
    )


class TestInitResult:
    """Tests for InitResult dataclass."""

    def test_success_with_message(self) -> None:
        """InitResult can express success with message."""
        result = InitResult(
            success=True,
            path=Path("/home/user/.aurora/plans"),
            created=True,
            message="Planning directory initialized successfully",
        )

        assert result.success is True
        assert result.path == Path("/home/user/.aurora/plans")
        assert result.created is True
        assert result.message is not None
        assert result.warning is None
        assert result.error is None

    def test_success_with_warning(self) -> None:
        """InitResult can express success with warning (already exists)."""
        result = InitResult(
            success=True,
            path=Path("/home/user/.aurora/plans"),
            created=False,
            warning="Planning directory already exists. No changes made.",
        )

        assert result.success is True
        assert result.created is False
        assert result.warning is not None
        assert result.error is None

    def test_failure_with_error(self) -> None:
        """InitResult can express failure with error."""
        result = InitResult(
            success=False,
            path=Path("/home/user/.aurora/plans"),
            error="Cannot write to /home/user/.aurora/plans. Check permissions.",
        )

        assert result.success is False
        assert result.error is not None
        assert result.message is None
        assert result.warning is None

    def test_default_values(self) -> None:
        """InitResult has sensible default values."""
        result = InitResult(success=True)

        assert result.path is None
        assert result.created is False
        assert result.message is None
        assert result.warning is None
        assert result.error is None


class TestPlanResult:
    """Tests for PlanResult dataclass."""

    def test_success_with_plan(self, sample_plan: Plan) -> None:
        """PlanResult can express success with plan."""
        result = PlanResult(
            success=True,
            plan=sample_plan,
            plan_dir=Path("/home/user/.aurora/plans/active/0001-oauth-auth"),
        )

        assert result.success is True
        assert result.plan is not None
        assert result.plan.plan_id == "0001-oauth-auth"
        assert result.plan_dir is not None
        assert result.error is None

    def test_success_with_warnings(self, sample_plan: Plan) -> None:
        """PlanResult can express partial success (plan created but with warnings)."""
        result = PlanResult(
            success=True,
            plan=sample_plan,
            plan_dir=Path("/home/user/.aurora/plans/active/0001-oauth-auth"),
            warnings=["Agent gaps detected: @missing-agent", "No indexed memory available"],
        )

        assert result.success is True
        assert result.warnings is not None
        assert len(result.warnings) == 2
        assert "Agent gaps" in result.warnings[0]

    def test_failure_with_error(self) -> None:
        """PlanResult can express failure."""
        result = PlanResult(
            success=False,
            error="Goal must be at least 10 characters.",
        )

        assert result.success is False
        assert result.plan is None
        assert result.error is not None

    def test_default_values(self) -> None:
        """PlanResult has sensible default values."""
        result = PlanResult(success=True)

        assert result.plan is None
        assert result.plan_dir is None
        assert result.warnings is None
        assert result.error is None


class TestListResult:
    """Tests for ListResult dataclass."""

    def test_with_plans(self, sample_plan: Plan) -> None:
        """ListResult contains plan summaries."""
        summary = PlanSummary.from_plan(sample_plan, "active")
        result = ListResult(plans=[summary])

        assert len(result.plans) == 1
        assert result.plans[0].plan_id == "0001-oauth-auth"
        assert result.warning is None
        assert result.errors is None

    def test_empty_with_warning(self) -> None:
        """ListResult can be empty with warning (not initialized)."""
        result = ListResult(
            plans=[],
            warning="Planning directory not initialized. Run 'aur plan init' first.",
        )

        assert len(result.plans) == 0
        assert result.warning is not None
        assert "init" in result.warning

    def test_with_errors(self, sample_plan: Plan) -> None:
        """ListResult can contain errors from failed plan loads."""
        summary = PlanSummary.from_plan(sample_plan, "active")
        result = ListResult(
            plans=[summary],
            errors=["Invalid plan 0002-broken: JSON decode error"],
        )

        assert len(result.plans) == 1
        assert result.errors is not None
        assert len(result.errors) == 1

    def test_default_values(self) -> None:
        """ListResult has sensible default values."""
        result = ListResult()

        assert result.plans == []
        assert result.warning is None
        assert result.errors is None


class TestShowResult:
    """Tests for ShowResult dataclass."""

    def test_success_with_all_files(self, sample_plan: Plan) -> None:
        """ShowResult shows plan with all files present."""
        result = ShowResult(
            success=True,
            plan=sample_plan,
            plan_dir=Path("/home/user/.aurora/plans/active/0001-oauth-auth"),
            files_status={
                "plan.md": True,
                "prd.md": True,
                "tasks.md": True,
                "agents.json": True,
            },
        )

        assert result.success is True
        assert result.plan is not None
        assert result.files_status is not None
        assert all(result.files_status.values())

    def test_success_with_missing_files(self, sample_plan: Plan) -> None:
        """ShowResult shows plan with some files missing."""
        result = ShowResult(
            success=True,
            plan=sample_plan,
            plan_dir=Path("/home/user/.aurora/plans/active/0001-oauth-auth"),
            files_status={
                "plan.md": True,
                "prd.md": False,
                "tasks.md": False,
                "agents.json": True,
            },
        )

        assert result.success is True
        assert result.files_status["plan.md"] is True
        assert result.files_status["prd.md"] is False

    def test_failure_with_error(self) -> None:
        """ShowResult can express failure."""
        result = ShowResult(
            success=False,
            error="Plan '0001-test' not found. Use 'aur plan list' to see available plans.",
        )

        assert result.success is False
        assert result.plan is None
        assert result.error is not None

    def test_default_values(self) -> None:
        """ShowResult has sensible default values."""
        result = ShowResult(success=True)

        assert result.plan is None
        assert result.plan_dir is None
        assert result.files_status is None
        assert result.error is None


class TestArchiveResult:
    """Tests for ArchiveResult dataclass."""

    def test_success_with_duration(self, sample_plan: Plan) -> None:
        """ArchiveResult includes computed duration."""
        # Set archive metadata
        sample_plan.status = PlanStatus.ARCHIVED
        sample_plan.archived_at = datetime.utcnow()
        sample_plan.duration_days = 5

        result = ArchiveResult(
            success=True,
            plan=sample_plan,
            source_dir=Path("/home/user/.aurora/plans/active/0001-oauth-auth"),
            target_dir=Path("/home/user/.aurora/plans/archive/2024-01-15-0001-oauth-auth"),
            duration_days=5,
        )

        assert result.success is True
        assert result.duration_days == 5
        assert result.source_dir is not None
        assert result.target_dir is not None
        assert "archive" in str(result.target_dir)

    def test_failure_with_error(self) -> None:
        """ArchiveResult can express failure."""
        result = ArchiveResult(
            success=False,
            error="Archive failed, rolled back to original state. Error: permission denied",
        )

        assert result.success is False
        assert result.error is not None
        assert "rolled back" in result.error

    def test_default_values(self) -> None:
        """ArchiveResult has sensible default values."""
        result = ArchiveResult(success=True)

        assert result.plan is None
        assert result.source_dir is None
        assert result.target_dir is None
        assert result.duration_days is None
        assert result.error is None


class TestPlanSummary:
    """Tests for PlanSummary dataclass."""

    def test_from_plan_basic(self, sample_plan: Plan) -> None:
        """PlanSummary.from_plan creates summary from full plan."""
        summary = PlanSummary.from_plan(sample_plan, "active")

        assert summary.plan_id == "0001-oauth-auth"
        assert summary.status == "active"
        assert summary.subgoal_count == 2
        assert summary.agent_gaps == 1  # @missing-agent

    def test_from_plan_truncates_long_goal(self, sample_subgoals: list[Subgoal]) -> None:
        """PlanSummary.from_plan truncates goals longer than 50 chars."""
        long_goal = "A" * 100  # 100 character goal
        plan = Plan(
            plan_id="0002-long-goal",
            goal=long_goal,
            subgoals=sample_subgoals,
        )

        summary = PlanSummary.from_plan(plan, "active")

        assert len(summary.goal) == 53  # 50 chars + "..."
        assert summary.goal.endswith("...")

    def test_from_plan_keeps_short_goal(self, sample_subgoals: list[Subgoal]) -> None:
        """PlanSummary.from_plan keeps goals 50 chars or less unchanged."""
        short_goal = "Short goal description"
        plan = Plan(
            plan_id="0003-short-goal",
            goal=short_goal,
            subgoals=sample_subgoals,
        )

        summary = PlanSummary.from_plan(plan, "active")

        assert summary.goal == short_goal
        assert not summary.goal.endswith("...")

    def test_from_plan_preserves_created_at(self, sample_plan: Plan) -> None:
        """PlanSummary.from_plan preserves creation timestamp."""
        original_time = sample_plan.created_at
        summary = PlanSummary.from_plan(sample_plan, "active")

        assert summary.created_at == original_time

    def test_from_plan_with_archived_status(self, sample_plan: Plan) -> None:
        """PlanSummary.from_plan respects status override."""
        # Plan model says ACTIVE but we're overriding to archived
        summary = PlanSummary.from_plan(sample_plan, "archived")

        assert summary.status == "archived"

    def test_from_plan_with_no_agent_gaps(self, sample_subgoals: list[Subgoal]) -> None:
        """PlanSummary.from_plan handles plan with no agent gaps."""
        plan = Plan(
            plan_id="0004-no-gaps",
            goal="Plan with all agents available",
            subgoals=sample_subgoals,
            agent_gaps=[],  # No gaps
        )

        summary = PlanSummary.from_plan(plan, "active")

        assert summary.agent_gaps == 0


class TestResultNoneHandling:
    """Tests that result types handle None values correctly."""

    def test_init_result_all_none_optional(self) -> None:
        """InitResult handles all optional fields as None."""
        result = InitResult(success=False)

        assert result.path is None
        assert result.message is None
        assert result.warning is None
        assert result.error is None

    def test_plan_result_all_none_optional(self) -> None:
        """PlanResult handles all optional fields as None."""
        result = PlanResult(success=False)

        assert result.plan is None
        assert result.plan_dir is None
        assert result.warnings is None
        assert result.error is None

    def test_list_result_all_none_optional(self) -> None:
        """ListResult handles all optional fields as None."""
        result = ListResult()

        assert result.warning is None
        assert result.errors is None

    def test_show_result_all_none_optional(self) -> None:
        """ShowResult handles all optional fields as None."""
        result = ShowResult(success=False)

        assert result.plan is None
        assert result.plan_dir is None
        assert result.files_status is None
        assert result.error is None

    def test_archive_result_all_none_optional(self) -> None:
        """ArchiveResult handles all optional fields as None."""
        result = ArchiveResult(success=False)

        assert result.plan is None
        assert result.source_dir is None
        assert result.target_dir is None
        assert result.duration_days is None
        assert result.error is None


class TestResultSuccessVsError:
    """Tests for success vs error state consistency."""

    def test_init_result_success_has_path(self) -> None:
        """Successful InitResult typically has path."""
        result = InitResult(
            success=True,
            path=Path("/test/path"),
            created=True,
            message="Success",
        )

        assert result.success is True
        assert result.path is not None
        assert result.error is None

    def test_init_result_failure_has_error(self) -> None:
        """Failed InitResult typically has error."""
        result = InitResult(
            success=False,
            error="Permission denied",
        )

        assert result.success is False
        assert result.error is not None
        # Path might still be set to indicate where failure occurred
        assert result.message is None

    def test_plan_result_success_has_plan(self, sample_plan: Plan) -> None:
        """Successful PlanResult has plan."""
        result = PlanResult(
            success=True,
            plan=sample_plan,
            plan_dir=Path("/test"),
        )

        assert result.success is True
        assert result.plan is not None
        assert result.error is None

    def test_plan_result_failure_has_error(self) -> None:
        """Failed PlanResult has error."""
        result = PlanResult(
            success=False,
            error="Goal too short",
        )

        assert result.success is False
        assert result.error is not None
        assert result.plan is None
