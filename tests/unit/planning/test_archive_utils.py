"""Unit tests for archive utilities."""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parents[4] / "packages" / "planning" / "src"))

from aurora_planning.archive_utils import (
    archive_plan,
    generate_archive_name,
    list_archived_plans,
    restore_plan,
)


class TestGenerateArchiveName:
    """Tests for generate_archive_name()."""

    def test_with_specific_date(self):
        """Should generate archive name with provided date."""
        date = datetime(2026, 1, 3, 10, 30, 0)
        result = generate_archive_name("0001-oauth-auth", date)
        assert result == "2026-01-03-0001-oauth-auth"

    def test_with_different_dates(self):
        """Should use correct date format."""
        date1 = datetime(2025, 12, 25)
        assert generate_archive_name("0042-test", date1) == "2025-12-25-0042-test"

        date2 = datetime(2026, 1, 1)
        assert generate_archive_name("0100-plan", date2) == "2026-01-01-0100-plan"

    def test_preserves_plan_id(self):
        """Should preserve complete plan ID including slug."""
        date = datetime(2026, 1, 15)
        result = generate_archive_name("0001-long-plan-slug-with-many-words", date)
        assert result == "2026-01-15-0001-long-plan-slug-with-many-words"


class TestArchivePlan:
    """Tests for archive_plan()."""

    def test_successful_archive(self, temp_plans_dir):
        """Should move plan from active to archive with timestamp."""
        # Create active plan with agents.json
        plan_id = "0001-test-plan"
        plan_dir = temp_plans_dir / "active" / plan_id
        plan_dir.mkdir(parents=True)

        agents_data = {
            "plan_id": plan_id,
            "goal": "Test Goal",
            "status": "active",
            "created_at": "2026-01-01T10:00:00Z",
        }
        agents_file = plan_dir / "agents.json"
        agents_file.write_text(json.dumps(agents_data, indent=2))

        # Archive the plan
        archive_date = datetime(2026, 1, 3)
        result = archive_plan(plan_id, temp_plans_dir, archive_date)

        # Verify plan moved
        assert not plan_dir.exists()
        assert result.exists()
        assert result.parent == temp_plans_dir / "archive"
        assert result.name == "2026-01-03-0001-test-plan"

        # Verify agents.json updated
        archived_agents = json.loads((result / "agents.json").read_text())
        assert archived_agents["status"] == "archived"
        assert archived_agents["archived_at"] == "2026-01-03T00:00:00"

    def test_plan_not_found(self, temp_plans_dir):
        """Should raise FileNotFoundError if plan doesn't exist."""
        with pytest.raises(FileNotFoundError, match="not found in active directory"):
            archive_plan("9999-nonexistent", temp_plans_dir)

    def test_archive_destination_exists(self, temp_plans_dir):
        """Should raise FileExistsError if archive already exists."""
        plan_id = "0001-test-plan"
        plan_dir = temp_plans_dir / "active" / plan_id
        plan_dir.mkdir(parents=True)

        # Create conflicting archive directory
        archive_name = "2026-01-03-0001-test-plan"
        (temp_plans_dir / "archive" / archive_name).mkdir(parents=True)

        with pytest.raises(FileExistsError, match="Archive destination already exists"):
            archive_plan(plan_id, temp_plans_dir, datetime(2026, 1, 3))

    def test_preserves_all_files(self, temp_plans_dir):
        """Should move all files in plan directory."""
        plan_id = "0001-test-plan"
        plan_dir = temp_plans_dir / "active" / plan_id
        plan_dir.mkdir(parents=True)

        # Create multiple files
        (plan_dir / "plan.md").write_text("# Plan")
        (plan_dir / "prd.md").write_text("# PRD")
        (plan_dir / "tasks.md").write_text("# Tasks")
        (plan_dir / "agents.json").write_text('{"plan_id": "0001-test-plan", "status": "active"}')

        result = archive_plan(plan_id, temp_plans_dir, datetime(2026, 1, 3))

        # Verify all files moved
        assert (result / "plan.md").exists()
        assert (result / "prd.md").exists()
        assert (result / "tasks.md").exists()
        assert (result / "agents.json").exists()


class TestRestorePlan:
    """Tests for restore_plan()."""

    def test_successful_restore(self, temp_plans_dir):
        """Should move plan from archive back to active."""
        # Create archived plan
        archive_name = "2026-01-03-0001-test-plan"
        archive_dir = temp_plans_dir / "archive" / archive_name
        archive_dir.mkdir(parents=True)

        agents_data = {
            "plan_id": "0001-test-plan",
            "goal": "Test Goal",
            "status": "archived",
            "archived_at": "2026-01-03T10:00:00Z",
        }
        (archive_dir / "agents.json").write_text(json.dumps(agents_data, indent=2))

        # Restore the plan
        result = restore_plan(archive_name, temp_plans_dir)

        # Verify plan moved
        assert not archive_dir.exists()
        assert result.exists()
        assert result.parent == temp_plans_dir / "active"
        assert result.name == "0001-test-plan"

        # Verify agents.json updated
        restored_agents = json.loads((result / "agents.json").read_text())
        assert restored_agents["status"] == "active"
        assert "archived_at" not in restored_agents

    def test_archive_not_found(self, temp_plans_dir):
        """Should raise FileNotFoundError if archive doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Archived plan not found"):
            restore_plan("2026-01-03-9999-nonexistent", temp_plans_dir)

    def test_active_plan_exists(self, temp_plans_dir):
        """Should raise FileExistsError if plan already in active."""
        # Create archived plan
        archive_name = "2026-01-03-0001-test-plan"
        (temp_plans_dir / "archive" / archive_name).mkdir(parents=True)

        # Create conflicting active plan
        (temp_plans_dir / "active" / "0001-test-plan").mkdir(parents=True)

        with pytest.raises(FileExistsError, match="already exists in active directory"):
            restore_plan(archive_name, temp_plans_dir)

    def test_invalid_archive_name(self, temp_plans_dir):
        """Should raise ValueError for invalid archive name format."""
        with pytest.raises(ValueError, match="Invalid archive name format"):
            restore_plan("invalid-name", temp_plans_dir)


class TestListArchivedPlans:
    """Tests for list_archived_plans()."""

    def test_empty_archive(self, temp_plans_dir):
        """Should return empty list when no archives exist."""
        result = list_archived_plans(temp_plans_dir)
        assert result == []

    def test_single_archive(self, temp_plans_dir):
        """Should list single archived plan."""
        archive_name = "2026-01-03-0001-test-plan"
        (temp_plans_dir / "archive" / archive_name).mkdir(parents=True)

        result = list_archived_plans(temp_plans_dir)

        assert len(result) == 1
        assert result[0][0] == archive_name
        assert result[0][1] == "0001-test-plan"
        assert result[0][2] == datetime(2026, 1, 3)

    def test_multiple_archives_sorted(self, temp_plans_dir):
        """Should list multiple archives sorted by date (newest first)."""
        archives = [
            "2026-01-01-0001-oldest",
            "2026-01-15-0002-newest",
            "2026-01-10-0003-middle",
        ]
        for archive in archives:
            (temp_plans_dir / "archive" / archive).mkdir(parents=True)

        result = list_archived_plans(temp_plans_dir)

        assert len(result) == 3
        # Should be sorted newest first
        assert result[0][0] == "2026-01-15-0002-newest"
        assert result[1][0] == "2026-01-10-0003-middle"
        assert result[2][0] == "2026-01-01-0001-oldest"

    def test_ignores_invalid_formats(self, temp_plans_dir):
        """Should ignore directories with invalid format."""
        (temp_plans_dir / "archive").mkdir(parents=True, exist_ok=True)
        (temp_plans_dir / "archive" / "2026-01-03-0001-valid").mkdir()
        (temp_plans_dir / "archive" / "invalid-format").mkdir()
        (temp_plans_dir / "archive" / "0001-no-date").mkdir()

        result = list_archived_plans(temp_plans_dir)

        assert len(result) == 1
        assert result[0][0] == "2026-01-03-0001-valid"

    def test_ignores_files(self, temp_plans_dir):
        """Should ignore files in archive directory."""
        (temp_plans_dir / "archive").mkdir(parents=True, exist_ok=True)
        (temp_plans_dir / "archive" / "2026-01-03-0001-plan").mkdir()
        (temp_plans_dir / "archive" / "some-file.txt").touch()

        result = list_archived_plans(temp_plans_dir)

        assert len(result) == 1
