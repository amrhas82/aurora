"""Tests for ValidateCommand CLI wrapper."""

from pathlib import Path

import pytest

from aurora_planning.cli.validate_cmd import ValidateCommand


@pytest.fixture
def validate_command() -> ValidateCommand:
    """Create a ValidateCommand instance."""
    return ValidateCommand()


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project structure."""
    aurora_dir = tmp_path / "aurora"
    plans_dir = aurora_dir / "plans"
    plans_dir.mkdir(parents=True)
    return tmp_path


class TestValidateCommandPlan:
    """Tests for validating plans."""

    def test_validate_valid_plan(self, temp_project: Path, validate_command: ValidateCommand):
        """Test validating a valid plan."""
        plan_dir = temp_project / "aurora" / "plans" / "test-plan"
        specs_dir = plan_dir / "specs"
        cap_dir = specs_dir / "test-capability"
        cap_dir.mkdir(parents=True)

        plan_file = plan_dir / "plan.md"
        plan_file.write_text("# Plan: Test\n\n## Why\nReason text.\n\n## What Changes\n- Change")

        cap_file = cap_dir / "spec.md"
        cap_file.write_text(
            """# Capability: Test

## ADDED Requirements

### Requirement: REQ-001: Test

The system SHALL do something.

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
            result = validate_command.validate_plan("test-plan", strict=False, json_output=False)
            assert "valid" in result.lower()
        finally:
            os.chdir(original_cwd)

    def test_validate_plan_json_output(self, temp_project: Path, validate_command: ValidateCommand):
        """Test JSON output for plan validation."""
        plan_dir = temp_project / "aurora" / "plans" / "test-plan"
        specs_dir = plan_dir / "specs"
        cap_dir = specs_dir / "test-capability"
        cap_dir.mkdir(parents=True)

        plan_file = plan_dir / "plan.md"
        plan_file.write_text("# Plan: Test\n\n## Why\nReason.\n\n## What Changes\n- Change")

        cap_file = cap_dir / "spec.md"
        cap_file.write_text(
            """# Capability: Test

## ADDED Requirements

### Requirement: REQ-001: Test

Text here.

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
            result = validate_command.validate_plan("test-plan", strict=False, json_output=True)
            import json

            data = json.loads(result)
            assert "valid" in data
            assert "issues" in data
        finally:
            os.chdir(original_cwd)


class TestValidateCommandCapability:
    """Tests for validating capability files."""

    def test_validate_valid_capability(self, tmp_path: Path, validate_command: ValidateCommand):
        """Test validating a valid capability file."""
        cap_file = tmp_path / "test-capability.md"
        cap_file.write_text(
            """# Capability: Test Capability

## Requirements

### Requirement: REQ-001: Test requirement

The system SHALL support test functionality.

#### Scenario: Basic scenario
GIVEN initial state
WHEN action occurs
THEN result happens
"""
        )

        result = validate_command.validate_capability(
            str(cap_file), strict=False, json_output=False
        )
        assert "valid" in result.lower()

    def test_validate_capability_not_found(self, validate_command: ValidateCommand):
        """Test validation of non-existent capability file."""
        with pytest.raises(Exception) as exc_info:
            validate_command.validate_capability("nonexistent.md", strict=False, json_output=False)
        assert "not found" in str(exc_info.value).lower()

    def test_validate_capability_json_output(
        self, tmp_path: Path, validate_command: ValidateCommand
    ):
        """Test JSON output for capability validation."""
        cap_file = tmp_path / "test-capability.md"
        cap_file.write_text(
            """# Capability: Test

## Requirements

### Requirement: REQ-001: Test

The system SHALL do something.

#### Scenario: Test
GIVEN state
WHEN action
THEN result
"""
        )

        result = validate_command.validate_capability(str(cap_file), strict=False, json_output=True)
        import json

        data = json.loads(result)
        assert "valid" in data
        assert "issues" in data
