"""Unit tests for planning CLI commands.

Tests aur plan list, view, and archive commands
using Click's CliRunner for isolated testing.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.plan import plan_group
from aurora_cli.planning.core import archive_plan, init_planning_directory, list_plans, show_plan
from aurora_cli.planning.models import Complexity, Plan, PlanManifest, PlanStatus, Subgoal


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_subgoals() -> list[Subgoal]:
    """Create sample subgoals for testing."""
    return [
        Subgoal(
            id="sg-1",
            title="Implement authentication",
            description="Create OAuth2 authentication flow with JWT",
            assigned_agent="@code-developer",
        ),
        Subgoal(
            id="sg-2",
            title="Write unit tests",
            description="Create comprehensive tests for auth module",
            assigned_agent="@quality-assurance",
            dependencies=["sg-1"],
        ),
    ]


@pytest.fixture
def sample_plan(sample_subgoals: list[Subgoal]) -> Plan:
    """Create sample plan for testing."""
    return Plan(
        plan_id="0001-oauth-auth",
        goal="Implement OAuth2 authentication with JWT tokens",
        subgoals=sample_subgoals,
        status=PlanStatus.ACTIVE,
        complexity=Complexity.MODERATE,
    )


def _mock_config(plans_dir: Path) -> MagicMock:
    """Create mock config with plans directory."""
    config = MagicMock()
    config.get_plans_path.return_value = plans_dir
    config.get_planning_base_dir.return_value = str(plans_dir)
    config.planning_base_dir = str(plans_dir)
    config.soar_default_tool = "claude"
    config.soar_default_model = "sonnet"
    return config


def create_complete_plan_structure(plan_dir: Path, plan: Plan) -> None:
    """Create complete plan directory structure with all required files.

    Creates the 4 base files:
    - plan.md
    - prd.md
    - tasks.md
    - agents.json

    Args:
        plan_dir: Directory to create plan in
        plan: Plan object to write

    """
    plan_dir.mkdir(parents=True, exist_ok=True)

    # Create agents.json
    (plan_dir / "agents.json").write_text(plan.model_dump_json(indent=2))

    # Create plan.md
    (plan_dir / "plan.md").write_text(
        f"""# Plan: {plan.plan_id}

**Goal:** {plan.goal}

**Status:** {plan.status.value}
**Complexity:** {plan.complexity.value}

## Subgoals

{chr(10).join(f"### {i}. {sg.title}" + chr(10) + sg.description for i, sg in enumerate(plan.subgoals, 1))}
""",
    )

    # Create prd.md
    (plan_dir / "prd.md").write_text(
        f"""# Product Requirements: {plan.plan_id}

## Overview

{plan.goal}

## User Stories

<!-- Add user stories here -->

## Functional Requirements

<!-- Add functional requirements here -->
""",
    )

    # Create tasks.md
    (plan_dir / "tasks.md").write_text(
        f"""# Tasks: {plan.plan_id}

Goal: {plan.goal}

## Implementation Tasks

{chr(10).join(f"- [ ] {i}.0 {sg.title}" for i, sg in enumerate(plan.subgoals, 1))}
""",
    )


class TestListPlans:
    """Tests for list_plans core function."""

    def test_list_active_plans(self, tmp_path: Path, sample_plan: Plan) -> None:
        """list_plans returns active plans by default."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        # Create a plan
        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)

        result = list_plans(config=_mock_config(plans_dir))

        assert len(result.plans) == 1
        assert result.plans[0].plan_id == "0001-oauth-auth"
        assert result.plans[0].status == "active"

    def test_list_archived_plans(self, tmp_path: Path, sample_plan: Plan) -> None:
        """list_plans --archived returns archived plans."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        # Create archived plan
        sample_plan.status = PlanStatus.ARCHIVED
        sample_plan.plan_id = f"2024-01-15-{sample_plan.plan_id}"  # Update ID to match directory
        archive_path = plans_dir / "archive" / sample_plan.plan_id
        create_complete_plan_structure(archive_path, sample_plan)

        result = list_plans(archived=True, config=_mock_config(plans_dir))

        assert len(result.plans) == 1
        assert result.plans[0].status == "archived"

    def test_list_all_plans(self, tmp_path: Path, sample_plan: Plan) -> None:
        """list_plans --all returns both active and archived."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        # Create active plan
        active_plan = sample_plan
        active_path = plans_dir / "active" / active_plan.plan_id
        create_complete_plan_structure(active_path, active_plan)

        # Create archived plan
        archived_plan = Plan(
            plan_id="2024-01-15-0002-archived",
            goal="An archived plan for testing purposes",
            subgoals=sample_plan.subgoals,
            status=PlanStatus.ARCHIVED,
        )
        archive_path = plans_dir / "archive" / archived_plan.plan_id
        create_complete_plan_structure(archive_path, archived_plan)

        result = list_plans(all_plans=True, config=_mock_config(plans_dir))

        assert len(result.plans) == 2

    def test_list_empty_returns_empty(self, tmp_path: Path) -> None:
        """list_plans returns empty list when no plans."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        result = list_plans(config=_mock_config(plans_dir))

        assert len(result.plans) == 0
        assert result.warning is None

    def test_list_not_initialized_returns_warning(self, tmp_path: Path) -> None:
        """list_plans returns warning if not initialized."""
        result = list_plans(config=_mock_config(tmp_path / "nonexistent"))

        assert len(result.plans) == 0
        assert result.warning is not None
        assert "init" in result.warning.lower()

    def test_list_sorted_by_date(self, tmp_path: Path, sample_subgoals: list[Subgoal]) -> None:
        """list_plans returns newest first."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        # Create older plan
        old_plan = Plan(
            plan_id="0001-old",
            goal="Older plan created first",
            subgoals=sample_subgoals,
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        old_path = plans_dir / "active" / old_plan.plan_id
        create_complete_plan_structure(old_path, old_plan)

        # Create newer plan
        new_plan = Plan(
            plan_id="0002-new",
            goal="Newer plan created later",
            subgoals=sample_subgoals,
            created_at=datetime.now(timezone.utc),
        )
        new_path = plans_dir / "active" / new_plan.plan_id
        create_complete_plan_structure(new_path, new_plan)

        result = list_plans(config=_mock_config(plans_dir))

        assert len(result.plans) == 2
        assert result.plans[0].plan_id == "0002-new"  # Newest first
        assert result.plans[1].plan_id == "0001-old"


class TestListCommand:
    """Tests for aur plan list CLI command."""

    def test_list_cli_active_plans(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        sample_plan: Plan,
    ) -> None:
        """aur plan list shows active plans."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)

        with patch("aurora_cli.planning.core._get_plans_dir", return_value=plans_dir):
            result = cli_runner.invoke(plan_group, ["list"])

        assert result.exit_code == 0
        # ID may be truncated with ellipsis in rich table, check for partial match
        assert "0001-oauth" in result.output or "Active Plans" in result.output

    def test_list_cli_json_output(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        sample_plan: Plan,
    ) -> None:
        """aur plan list --format json outputs valid JSON."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)

        with patch("aurora_cli.planning.core._get_plans_dir", return_value=plans_dir):
            result = cli_runner.invoke(plan_group, ["list", "--format", "json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["plan_id"] == "0001-oauth-auth"


class TestShowPlan:
    """Tests for show_plan core function."""

    def test_show_existing_plan(self, tmp_path: Path, sample_plan: Plan) -> None:
        """show_plan returns full plan details."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)
        (plan_path / "plan.md").write_text("# Plan")

        result = show_plan(sample_plan.plan_id, config=_mock_config(plans_dir))

        assert result.success is True
        assert result.plan is not None
        assert result.plan.plan_id == "0001-oauth-auth"
        assert result.files_status is not None
        assert result.files_status["plan.md"] is True
        assert result.files_status["prd.md"] is True  # Complete structure creates all files

    def test_show_archived_plan(self, tmp_path: Path, sample_plan: Plan) -> None:
        """show_plan --archived finds archived plan."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        sample_plan.status = PlanStatus.ARCHIVED
        sample_plan.plan_id = f"2024-01-15-{sample_plan.plan_id}"
        archive_path = plans_dir / "archive" / sample_plan.plan_id
        create_complete_plan_structure(archive_path, sample_plan)

        result = show_plan(sample_plan.plan_id, archived=True, config=_mock_config(plans_dir))

        assert result.success is True
        assert result.plan is not None

    def test_show_plan_not_found(self, tmp_path: Path) -> None:
        """show_plan returns error when plan not found."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        result = show_plan("nonexistent", config=_mock_config(plans_dir))

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_show_wrong_location_hint(self, tmp_path: Path, sample_plan: Plan) -> None:
        """show_plan suggests correct flag when plan in other location."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        # Put plan in archive
        archive_path = plans_dir / "archive" / sample_plan.plan_id
        archive_path.mkdir(parents=True)
        (archive_path / "agents.json").write_text(sample_plan.model_dump_json())

        # Search in active
        result = show_plan(sample_plan.plan_id, archived=False, config=_mock_config(plans_dir))

        assert result.success is False
        assert "--archived" in result.error

    def test_show_file_status(self, tmp_path: Path, sample_plan: Plan) -> None:
        """show_plan includes file status for all 4 files."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)
        (plan_path / "plan.md").write_text("# Plan")
        (plan_path / "prd.md").write_text("# PRD")

        result = show_plan(sample_plan.plan_id, config=_mock_config(plans_dir))

        assert result.files_status["plan.md"] is True
        assert result.files_status["prd.md"] is True
        assert result.files_status["tasks.md"] is True  # Complete structure creates all files
        assert result.files_status["agents.json"] is True


class TestShowCommand:
    """Tests for aur plan show CLI command."""

    def test_show_cli_existing_plan(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        sample_plan: Plan,
    ) -> None:
        """aur plan show displays plan details."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)

        with patch("aurora_cli.planning.core._get_plans_dir", return_value=plans_dir):
            result = cli_runner.invoke(plan_group, ["view", sample_plan.plan_id])

        assert result.exit_code == 0
        assert "0001-oauth-auth" in result.output
        assert "OAuth2" in result.output

    def test_show_cli_json_output(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        sample_plan: Plan,
    ) -> None:
        """aur plan show --format json outputs valid JSON."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)

        with patch("aurora_cli.planning.core._get_plans_dir", return_value=plans_dir):
            result = cli_runner.invoke(
                plan_group,
                ["view", sample_plan.plan_id, "--format", "json"],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["plan_id"] == "0001-oauth-auth"


class TestArchivePlan:
    """Tests for archive_plan core function."""

    def test_archive_plan_success(self, tmp_path: Path, sample_plan: Plan) -> None:
        """archive_plan moves plan to archive directory."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)

        result = archive_plan(sample_plan.plan_id, config=_mock_config(plans_dir))

        assert result.success is True
        assert result.target_dir is not None
        assert "archive" in str(result.target_dir)
        assert not plan_path.exists()  # Moved from active

    def test_archive_plan_not_found(self, tmp_path: Path) -> None:
        """archive_plan returns error when plan not found."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        result = archive_plan("nonexistent", config=_mock_config(plans_dir))

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_archive_already_archived(self, tmp_path: Path, sample_plan: Plan) -> None:
        """archive_plan returns error when already archived."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        # Set plan as already archived
        sample_plan.status = PlanStatus.ARCHIVED
        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)

        result = archive_plan(sample_plan.plan_id, config=_mock_config(plans_dir))

        assert result.success is False
        assert "already archived" in result.error.lower()

    def test_archive_duration_calculation(
        self,
        tmp_path: Path,
        sample_subgoals: list[Subgoal],
    ) -> None:
        """archive_plan calculates duration_days correctly."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        # Create plan with past created_at
        plan = Plan(
            plan_id="0001-old-plan",
            goal="Plan created 5 days ago for testing",
            subgoals=sample_subgoals,
            created_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        plan_path = plans_dir / "active" / plan.plan_id
        create_complete_plan_structure(plan_path, plan)

        result = archive_plan(plan.plan_id, config=_mock_config(plans_dir))

        assert result.success is True
        assert result.duration_days is not None
        assert result.duration_days >= 5

    def test_archive_updates_manifest(self, tmp_path: Path, sample_plan: Plan) -> None:
        """archive_plan updates manifest.json."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)

        # Add to manifest
        manifest = PlanManifest(active_plans=[sample_plan.plan_id])
        (plans_dir / "manifest.json").write_text(manifest.model_dump_json())

        archive_plan(sample_plan.plan_id, config=_mock_config(plans_dir))

        # Check manifest updated
        updated_manifest = PlanManifest.model_validate_json(
            (plans_dir / "manifest.json").read_text(),
        )
        assert sample_plan.plan_id not in updated_manifest.active_plans
        assert len(updated_manifest.archived_plans) == 1


class TestArchiveCommand:
    """Tests for aur plan archive CLI command."""

    def test_archive_cli_with_confirmation(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        sample_plan: Plan,
    ) -> None:
        """aur plan archive with confirmation."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)

        with patch("aurora_cli.planning.core._get_plans_dir", return_value=plans_dir):
            result = cli_runner.invoke(plan_group, ["archive", sample_plan.plan_id], input="y\n")

        assert result.exit_code == 0
        assert "archived" in result.output.lower()

    def test_archive_cli_yes_flag(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        sample_plan: Plan,
    ) -> None:
        """aur plan archive --yes skips confirmation."""
        plans_dir = tmp_path / "plans"
        init_planning_directory(path=plans_dir)

        plan_path = plans_dir / "active" / sample_plan.plan_id
        create_complete_plan_structure(plan_path, sample_plan)

        with patch("aurora_cli.planning.core._get_plans_dir", return_value=plans_dir):
            result = cli_runner.invoke(plan_group, ["archive", sample_plan.plan_id, "--yes"])

        assert result.exit_code == 0
        assert "archived" in result.output.lower()
