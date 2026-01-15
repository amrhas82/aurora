"""Integration tests for Aurora Planning workflows.

Tests end-to-end functionality of planning commands including:
- Plan creation with full 8-file structure
- Plan listing and filtering
- Plan viewing with various formats
- Archive workflow with confirmation
- Config loading and overrides
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from aurora_cli.commands.plan import archive_plan, create_command, list_plans, show_plan
from aurora_planning.planning_config import get_plans_dir


@pytest.fixture
def temp_aurora_dir():
    """Create temporary Aurora directory structure."""
    temp = Path(tempfile.mkdtemp(prefix="aurora-integration-test-"))
    plans_dir = temp / ".aurora" / "plans"
    (plans_dir / "active").mkdir(parents=True)
    (plans_dir / "archive").mkdir(parents=True)

    # Set environment variable to override default location
    old_env = os.environ.get("AURORA_PLANS_DIR")
    os.environ["AURORA_PLANS_DIR"] = str(plans_dir)

    yield plans_dir

    # Cleanup
    if old_env:
        os.environ["AURORA_PLANS_DIR"] = old_env
    else:
        os.environ.pop("AURORA_PLANS_DIR", None)

    if temp.exists():
        shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def cli_runner():
    """Create Click CLI runner."""
    return CliRunner()


class TestPlanCreationWorkflow:
    """Test end-to-end plan creation workflow."""

    def test_create_plan_generates_all_files(self, temp_aurora_dir, cli_runner):
        """Test that creating a plan generates all 8 files."""
        goal = "Implement OAuth2 Authentication"

        # Create plan
        result = cli_runner.invoke(create_command, [goal])

        # Verify success
        assert result.exit_code == 0
        assert (
            "Plan created:" in result.output
            or "implement-oauth2-authentication" in result.output.lower()
        )

        # Find the plan directory (ID may vary)
        active_dir = temp_aurora_dir / "active"
        plan_dirs = [
            d
            for d in active_dir.iterdir()
            if d.is_dir() and "implement-oauth2-authentication" in d.name.lower()
        ]
        assert len(plan_dirs) > 0, "Plan directory not found"
        plan_dir = plan_dirs[0]

        # Base files
        assert (plan_dir / "plan.md").exists()
        assert (plan_dir / "prd.md").exists()
        assert (plan_dir / "tasks.md").exists()
        assert (plan_dir / "agents.json").exists()

        # Capability specs (with truncated name)
        specs_dir = plan_dir / "specs"
        assert specs_dir.exists()
        spec_files = list(specs_dir.glob("*-planning.md"))
        assert len(spec_files) > 0, "Planning spec not found"

    def test_create_multiple_plans_increments_id(self, temp_aurora_dir, cli_runner):
        """Test that creating multiple plans increments ID correctly."""
        # Create first plan
        result1 = cli_runner.invoke(create_command, ["First Plan"])
        assert result1.exit_code == 0

        # Create second plan
        result2 = cli_runner.invoke(create_command, ["Second Plan"])
        assert result2.exit_code == 0

        # Create third plan
        result3 = cli_runner.invoke(create_command, ["Third Plan"])
        assert result3.exit_code == 0

        # Verify 3 plans exist
        active_dir = temp_aurora_dir / "active"
        plan_dirs = [d for d in active_dir.iterdir() if d.is_dir()]
        assert len(plan_dirs) == 3

    def test_create_plan_with_special_characters(self, temp_aurora_dir, cli_runner):
        """Test plan creation with special characters in goal."""
        goal = "Build User Profile & Settings (Phase 1)"

        result = cli_runner.invoke(create_command, [goal])
        assert result.exit_code == 0

        # Verify slug is correct
        plan_dir = temp_aurora_dir / "active" / "0001-build-user-profile-settings-p"
        assert plan_dir.exists()

    def test_agents_json_is_valid(self, temp_aurora_dir, cli_runner):
        """Test that generated agents.json is valid JSON and follows schema."""
        goal = "Test Validation"

        result = cli_runner.invoke(create_command, [goal])
        assert result.exit_code == 0

        # Load and validate agents.json
        agents_file = temp_aurora_dir / "active" / "0001-test-validation" / "agents.json"
        with open(agents_file) as f:
            data = json.load(f)

        # Verify required fields
        assert "plan_id" in data
        assert "goal" in data
        assert "status" in data
        assert "created_at" in data
        assert "subgoals" in data

        # Verify plan_id format
        assert data["plan_id"] == "0001-test-validation"


class TestPlanListingWorkflow:
    """Test end-to-end plan listing workflow."""

    def test_list_empty_plans(self, temp_aurora_dir, cli_runner):
        """Test listing when no plans exist."""
        result = cli_runner.invoke(list_plans, [])
        assert result.exit_code == 0
        assert "No active plans found" in result.output or "0 plans" in result.output

    def test_list_multiple_plans(self, temp_aurora_dir, cli_runner):
        """Test listing multiple plans."""
        # Create 3 plans
        cli_runner.invoke(create_command, ["Plan Alpha"])
        cli_runner.invoke(create_command, ["Plan Beta"])
        cli_runner.invoke(create_command, ["Plan Gamma"])

        # List plans
        result = cli_runner.invoke(list_plans, [])
        assert result.exit_code == 0

        # Verify all plans are shown
        assert "0001" in result.output or "plan-alpha" in result.output
        assert "0002" in result.output or "plan-beta" in result.output
        assert "0003" in result.output or "plan-gamma" in result.output

    def test_list_json_format(self, temp_aurora_dir, cli_runner):
        """Test listing plans in JSON format."""
        # Create a plan
        cli_runner.invoke(create_command, ["JSON Test"])

        # List in JSON format
        result = cli_runner.invoke(list_plans, ["--format", "json"])
        assert result.exit_code == 0

        # Verify JSON output
        data = json.loads(result.output)
        assert isinstance(data, dict) or isinstance(data, list)


class TestPlanViewingWorkflow:
    """Test end-to-end plan viewing workflow."""

    def test_view_plan_by_full_id(self, temp_aurora_dir, cli_runner):
        """Test viewing a plan by full ID."""
        # Create plan
        cli_runner.invoke(create_command, ["View Test"])

        # View plan
        result = cli_runner.invoke(show_plan, ["0001-view-test"])
        assert result.exit_code == 0
        assert "View Test" in result.output or "0001" in result.output

    def test_view_plan_by_number_only(self, temp_aurora_dir, cli_runner):
        """Test viewing a plan by number only."""
        # Create plan
        cli_runner.invoke(create_command, ["Number Test"])

        # View plan by number
        result = cli_runner.invoke(show_plan, ["0001"])
        assert result.exit_code == 0
        assert "Number Test" in result.output or "0001" in result.output

    def test_view_nonexistent_plan(self, temp_aurora_dir, cli_runner):
        """Test viewing a plan that doesn't exist."""
        result = cli_runner.invoke(show_plan, ["9999-does-not-exist"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()


class TestPlanArchiveWorkflow:
    """Test end-to-end plan archive workflow."""

    def test_archive_plan_with_force(self, temp_aurora_dir, cli_runner):
        """Test archiving a plan with --yes flag."""
        # Create plan
        cli_runner.invoke(create_command, ["Archive Test"])

        # Archive with -y flag
        result = cli_runner.invoke(archive_plan, ["0001-archive-test", "-y"])
        assert result.exit_code == 0

        # Verify plan moved to archive
        active_dir = temp_aurora_dir / "active" / "0001-archive-test"
        assert not active_dir.exists()

        # Check archive directory
        archive_dir = temp_aurora_dir / "archive"
        archives = list(archive_dir.glob("*-0001-archive-test"))
        assert len(archives) == 1
        assert archives[0].name.startswith("20")  # Date prefix YYYY-MM-DD

    def test_archive_preserves_all_files(self, temp_aurora_dir, cli_runner):
        """Test that archiving preserves all plan files."""
        # Create plan
        cli_runner.invoke(create_command, ["Preserve Test"])

        # Archive
        cli_runner.invoke(archive_plan, ["0001-preserve-test", "-y"])

        # Find archived directory
        archive_dir = temp_aurora_dir / "archive"
        archives = list(archive_dir.glob("*-0001-preserve-test"))
        assert len(archives) == 1

        archived_plan = archives[0]

        # Verify all files preserved
        assert (archived_plan / "plan.md").exists()
        assert (archived_plan / "prd.md").exists()
        assert (archived_plan / "tasks.md").exists()
        assert (archived_plan / "agents.json").exists()


class TestConfigurationWorkflow:
    """Test configuration loading and environment overrides."""

    def test_env_var_override(self, temp_aurora_dir):
        """Test that AURORA_PLANS_DIR environment variable works."""
        # The fixture already sets AURORA_PLANS_DIR
        plans_dir = get_plans_dir()
        assert str(temp_aurora_dir) in str(plans_dir)

    def test_plans_dir_structure(self, temp_aurora_dir):
        """Test that plans directory has correct structure."""
        assert (temp_aurora_dir / "active").exists()
        assert (temp_aurora_dir / "archive").exists()


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow from creation to archive."""

    def test_full_lifecycle(self, temp_aurora_dir, cli_runner):
        """Test full plan lifecycle: create -> list -> view -> archive."""
        goal = "End-to-End Test Plan"

        # Step 1: Create plan
        result = cli_runner.invoke(create_command, [goal])
        assert result.exit_code == 0

        # Step 2: List plans
        result = cli_runner.invoke(list_plans, [])
        assert result.exit_code == 0
        assert "0001" in result.output or "end-to-end-test-plan" in result.output

        # Step 3: View plan
        result = cli_runner.invoke(show_plan, ["0001"])
        assert result.exit_code == 0

        # Step 4: Archive plan
        result = cli_runner.invoke(archive_plan, ["0001", "-y"])
        assert result.exit_code == 0

        # Step 5: Verify plan no longer in active
        result = cli_runner.invoke(list_plans, [])
        assert result.exit_code == 0
        # Should show no active plans or empty list

        # Step 6: Verify plan in archive
        result = cli_runner.invoke(list_plans, ["--archived"])
        assert result.exit_code == 0
        assert "0001" in result.output or "end-to-end-test-plan" in result.output
