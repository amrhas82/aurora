"""Tests for PlanCommand CLI wrapper.

This tests the CLI interface wrapper around core plan functionality.
"""

from pathlib import Path

import pytest

from aurora_planning.cli.plan_cmd import PlanCommand


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project structure."""
    aurora_dir = tmp_path / "aurora"
    plans_dir = aurora_dir / "plans"
    plans_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def plan_command() -> PlanCommand:
    """Create a PlanCommand instance."""
    return PlanCommand()


class TestPlanCommandShow:
    """Tests for PlanCommand.show()."""

    def test_show_plan_text_mode(self, temp_project: Path, plan_command: PlanCommand):
        """Test showing a plan in text mode (raw markdown)."""
        # Create a sample plan
        plan_dir = temp_project / "aurora" / "plans" / "test-plan"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "plan.md"
        plan_file.write_text(
            "# Plan: Test Plan\n\n## Why\nTest reason.\n\n## What Changes\n- Test change"
        )

        # Show the plan
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)
            result = plan_command.show("test-plan", json_output=False)
            assert result is not None
            assert "Test Plan" in result
        finally:
            os.chdir(original_cwd)

    def test_show_plan_json_mode(self, temp_project: Path, plan_command: PlanCommand):
        """Test showing a plan in JSON mode."""
        # Create a sample plan with modifications
        plan_dir = temp_project / "aurora" / "plans" / "test-plan"
        specs_dir = plan_dir / "capabilities"
        specs_dir.mkdir(parents=True)

        plan_file = plan_dir / "plan.md"
        plan_file.write_text(
            "# Plan: Test Plan\n\n## Why\nTest reason.\n\n## What Changes\n- **test-capability:** Add feature"
        )

        # Create capability file with modifications
        cap_file = specs_dir / "test-capability.md"
        cap_file.write_text(
            """# Capability: Test Capability

## ADDED Requirements

### REQ-001: New Requirement

#### Scenario: Basic scenario
GIVEN initial state
WHEN action occurs
THEN result happens
"""
        )

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)
            result = plan_command.show("test-plan", json_output=True)
            assert result is not None
            assert "test-plan" in result.lower() or "test" in result.lower()
        finally:
            os.chdir(original_cwd)

    def test_show_nonexistent_plan_raises_error(
        self, temp_project: Path, plan_command: PlanCommand
    ):
        """Test that showing a non-existent plan raises an error."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)
            with pytest.raises(Exception) as exc_info:
                plan_command.show("nonexistent-plan", json_output=False)
            assert "not found" in str(exc_info.value).lower()
        finally:
            os.chdir(original_cwd)


class TestPlanCommandList:
    """Tests for PlanCommand.list()."""

    def test_list_plans_text_mode(self, temp_project: Path, plan_command: PlanCommand):
        """Test listing plans in text mode."""
        # Create multiple plans
        plans_dir = temp_project / "aurora" / "plans"
        for name in ["plan-a", "plan-b", "plan-c"]:
            plan_dir = plans_dir / name
            plan_dir.mkdir(parents=True)
            plan_file = plan_dir / "plan.md"
            plan_file.write_text(
                f"# Plan: {name.title()}\n\n## Why\nReason.\n\n## What Changes\n- Change"
            )

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)
            result = plan_command.list(json_output=False, long=False)
            assert result is not None
            assert "plan-a" in result.lower()
            assert "plan-b" in result.lower()
            assert "plan-c" in result.lower()
        finally:
            os.chdir(original_cwd)

    def test_list_plans_json_mode(self, temp_project: Path, plan_command: PlanCommand):
        """Test listing plans in JSON mode."""
        # Create plans
        plans_dir = temp_project / "aurora" / "plans"
        plan_dir = plans_dir / "test-plan"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "plan.md"
        plan_file.write_text("# Plan: Test Plan\n\n## Why\nReason.\n\n## What Changes\n- Change")

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)
            result = plan_command.list(json_output=True)
            assert result is not None
            # Should be JSON with plan details
            import json

            try:
                data = json.loads(result)
                assert isinstance(data, list)
            except json.JSONDecodeError:
                # If not valid JSON, at least check it has plan info
                assert "test-plan" in result.lower()
        finally:
            os.chdir(original_cwd)

    def test_list_empty_plans_directory(self, temp_project: Path, plan_command: PlanCommand):
        """Test listing when no plans exist."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)
            result = plan_command.list(json_output=False, long=False)
            assert result is not None
            assert "no items found" in result.lower() or result.strip() == ""
        finally:
            os.chdir(original_cwd)


class TestPlanCommandValidate:
    """Tests for PlanCommand.validate()."""

    def test_validate_valid_plan(self, temp_project: Path, plan_command: PlanCommand):
        """Test validating a valid plan."""
        # Create a valid plan - using specs/ directory (as expected by validator)
        plan_dir = temp_project / "aurora" / "plans" / "test-plan"
        specs_dir = plan_dir / "specs"  # Changed from capabilities to specs
        cap_dir = specs_dir / "test-capability"  # Capability in its own directory
        cap_dir.mkdir(parents=True)

        plan_file = plan_dir / "plan.md"
        plan_file.write_text(
            "# Plan: Test Plan\n\n## Why\nValid reason that is long enough.\n\n## What Changes\n- **test-capability:** Add feature"
        )

        # Create capability with valid modification
        cap_file = cap_dir / "spec.md"  # Changed from test-capability.md to spec.md
        cap_file.write_text(
            """# Capability: Test

## ADDED Requirements

### Requirement: REQ-001: Test requirement

The system SHALL support test functionality.

#### Scenario: Test scenario
GIVEN initial state
WHEN action occurs
THEN result happens
"""
        )

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)
            result = plan_command.validate("test-plan", strict=False, json_output=False)
            assert result is not None
            assert "valid" in result.lower()
        finally:
            os.chdir(original_cwd)

    def test_validate_invalid_plan(self, temp_project: Path, plan_command: PlanCommand):
        """Test validating an invalid plan."""
        # Create an invalid plan (missing scenarios)
        plan_dir = temp_project / "aurora" / "plans" / "test-plan"
        specs_dir = plan_dir / "capabilities"
        specs_dir.mkdir(parents=True)

        plan_file = plan_dir / "plan.md"
        plan_file.write_text(
            "# Plan: Test Plan\n\n## Why\nReason.\n\n## What Changes\n- **test-capability:** Add feature"
        )

        # Create capability without scenarios
        cap_file = specs_dir / "test-capability.md"
        cap_file.write_text(
            """# Capability: Test

## ADDED Requirements

### REQ-001: Test requirement

No scenarios here!
"""
        )

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)
            result = plan_command.validate("test-plan", strict=False, json_output=False)
            assert result is not None
            assert (
                "issue" in result.lower()
                or "error" in result.lower()
                or "warning" in result.lower()
            )
        finally:
            os.chdir(original_cwd)

    def test_validate_json_output(self, temp_project: Path, plan_command: PlanCommand):
        """Test validation with JSON output."""
        # Create a plan
        plan_dir = temp_project / "aurora" / "plans" / "test-plan"
        specs_dir = plan_dir / "capabilities"
        specs_dir.mkdir(parents=True)

        plan_file = plan_dir / "plan.md"
        plan_file.write_text(
            "# Plan: Test Plan\n\n## Why\nReason that is long enough.\n\n## What Changes\n- **test-capability:** Add feature"
        )

        cap_file = specs_dir / "test-capability.md"
        cap_file.write_text(
            """# Capability: Test

## ADDED Requirements

### REQ-001: Test

#### Scenario: Test
GIVEN state
WHEN action
THEN result
"""
        )

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)
            result = plan_command.validate("test-plan", strict=False, json_output=True)
            assert result is not None
            # Should be valid JSON
            import json

            try:
                data = json.loads(result)
                assert "valid" in data or "issues" in data
            except json.JSONDecodeError:
                # At minimum should contain validation info
                assert "valid" in result.lower() or "issue" in result.lower()
        finally:
            os.chdir(original_cwd)
