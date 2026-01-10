"""End-to-end integration tests for ArchiveCommand.

Tests the full archive workflow with real directory structures,
validating that all components work together correctly.

Task 1.13: Verify archive command works end-to-end
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from aurora_cli.planning.commands import ArchiveCommand


class TestArchiveCommandEndToEnd:
    """End-to-end tests for archive command workflow."""

    def test_archive_command_full_workflow(self):
        """Test complete archive workflow with all components."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            # Setup Aurora directory structure
            plans_active = target / ".aurora" / "plans" / "active"
            plans_active.mkdir(parents=True)
            plans_archive = target / ".aurora" / "plans" / "archive"
            plans_archive.mkdir(parents=True)

            # Create a test plan with tasks
            plan_id = "test-plan-001"
            plan_dir = plans_active / plan_id
            plan_dir.mkdir()

            # Create tasks.md
            (plan_dir / "tasks.md").write_text(
                """# Tasks
- [x] Task 1
- [x] Task 2
- [ ] Task 3
"""
            )

            # Create proposal.md
            (plan_dir / "proposal.md").write_text(
                """# Test Plan

## Why
This is a test plan to verify archive functionality works end-to-end.

## What Changes
Test changes for verification.
"""
            )

            # Execute archive command
            command = ArchiveCommand()
            command.execute(
                plan_name=plan_id,
                target_path=str(target),
                yes=True,  # Skip confirmations
                skip_specs=True,  # Skip spec updates for this test
            )

            # Verify plan was moved to archive
            archived_plans = list(plans_archive.iterdir())
            assert len(archived_plans) == 1

            # Verify archive name format (YYYY-MM-DD-plan-id)
            archived_name = archived_plans[0].name
            assert plan_id in archived_name
            assert archived_name.startswith(datetime.now().strftime("%Y-%m-%d"))

            # Verify original plan directory is gone
            assert not plan_dir.exists()

            # Verify archived plan contains original files
            archived_plan_dir = archived_plans[0]
            assert (archived_plan_dir / "tasks.md").exists()
            assert (archived_plan_dir / "proposal.md").exists()

    def test_archive_with_spec_updates(self):
        """Test archive workflow with spec delta updates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            # Setup Aurora directory structure
            plans_active = target / ".aurora" / "plans" / "active"
            plans_active.mkdir(parents=True)
            capabilities_dir = target / ".aurora" / "capabilities"
            capabilities_dir.mkdir(parents=True)

            # Create a test plan
            plan_id = "spec-update-plan"
            plan_dir = plans_active / plan_id
            plan_dir.mkdir()

            # Create existing capability spec
            capability_dir = capabilities_dir / "test-feature"
            capability_dir.mkdir()
            (capability_dir / "spec.md").write_text(
                """# Test Feature Specification

## Purpose
Existing test feature.

## Requirements

### Requirement: Existing Feature
The system SHALL have existing functionality.

#### Scenario: Works
Given existing setup
When using feature
Then it works
"""
            )

            # Create plan with spec updates
            spec_dir = plan_dir / "specs" / "test-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").write_text(
                """# Test Feature Specification

## ADDED Requirements

### Requirement: New Feature
The system SHALL implement new feature.

#### Scenario: New Works
Given new setup
When using new feature
Then new result
"""
            )

            # Execute archive with spec updates
            command = ArchiveCommand()
            command.execute(
                plan_name=plan_id,
                target_path=str(target),
                yes=True,
                skip_specs=False,  # Include spec updates
            )

            # Verify capability spec was updated
            updated_spec = (capability_dir / "spec.md").read_text()
            assert "Existing Feature" in updated_spec
            assert "New Feature" in updated_spec

    def test_archive_rejects_duplicate_archive_name(self):
        """Test that archive fails if archive name already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            # Setup Aurora directory structure
            plans_active = target / ".aurora" / "plans" / "active"
            plans_active.mkdir(parents=True)
            plans_archive = target / ".aurora" / "plans" / "archive"
            plans_archive.mkdir(parents=True)

            # Create first plan and archive it
            plan_id = "duplicate-test"
            plan_dir = plans_active / plan_id
            plan_dir.mkdir()

            command = ArchiveCommand()
            command.execute(plan_name=plan_id, target_path=str(target), yes=True, skip_specs=True)

            # Create second plan with same ID
            plan_dir.mkdir()

            # Try to archive again - should fail
            with pytest.raises(RuntimeError) as exc_info:
                command.execute(
                    plan_name=plan_id, target_path=str(target), yes=True, skip_specs=True
                )

            assert "already exists" in str(exc_info.value)

    def test_archive_validates_plan_exists(self):
        """Test that archive fails if plan doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            # Setup Aurora directory structure
            plans_active = target / ".aurora" / "plans" / "active"
            plans_active.mkdir(parents=True)

            # Try to archive non-existent plan
            command = ArchiveCommand()
            with pytest.raises(RuntimeError) as exc_info:
                command.execute(
                    plan_name="non-existent-plan",
                    target_path=str(target),
                    yes=True,
                    skip_specs=True,
                )

            assert "not found" in str(exc_info.value).lower()

    def test_archive_validates_aurora_directory_exists(self):
        """Test that archive fails if .aurora directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            # Don't create .aurora directory
            command = ArchiveCommand()
            with pytest.raises(RuntimeError) as exc_info:
                command.execute(
                    plan_name="any-plan", target_path=str(target), yes=True, skip_specs=True
                )

            assert "Aurora plans directory" in str(exc_info.value)
            assert "aur plan init" in str(exc_info.value)

    def test_archive_preserves_task_progress(self):
        """Test that task progress is correctly reported before archive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            # Setup Aurora directory structure
            plans_active = target / ".aurora" / "plans" / "active"
            plans_active.mkdir(parents=True)

            # Create a test plan with partial completion
            plan_id = "progress-test"
            plan_dir = plans_active / plan_id
            plan_dir.mkdir()

            # Create tasks with 2/5 complete
            (plan_dir / "tasks.md").write_text(
                """# Tasks
- [x] Task 1
- [x] Task 2
- [ ] Task 3
- [ ] Task 4
- [ ] Task 5
"""
            )

            command = ArchiveCommand()

            # Get task progress before archive
            progress = command._get_task_progress(plans_active, plan_id)
            assert progress["total"] == 5
            assert progress["completed"] == 2

            # Archive the plan
            command.execute(plan_name=plan_id, target_path=str(target), yes=True, skip_specs=True)

            # Verify archived plan still has tasks.md
            archive_dir = target / ".aurora" / "plans" / "archive"
            archived_plans = list(archive_dir.iterdir())
            archived_tasks = (archived_plans[0] / "tasks.md").read_text()
            assert "- [x] Task 1" in archived_tasks
            assert "- [ ] Task 3" in archived_tasks


class TestArchiveCommandFlagCombinations:
    """Test various flag combinations work correctly."""

    def test_yes_skip_specs_combination(self):
        """Test --yes and --skip-specs flags work together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            # Setup
            plans_active = target / ".aurora" / "plans" / "active"
            plans_active.mkdir(parents=True)
            plan_dir = plans_active / "test-plan"
            plan_dir.mkdir()

            # Execute with both flags
            command = ArchiveCommand()
            command.execute(
                plan_name="test-plan", target_path=str(target), yes=True, skip_specs=True
            )

            # Verify archived
            archive_dir = target / ".aurora" / "plans" / "archive"
            assert len(list(archive_dir.iterdir())) == 1

    def test_no_validate_flag(self):
        """Test --no-validate flag skips validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            # Setup
            plans_active = target / ".aurora" / "plans" / "active"
            plans_active.mkdir(parents=True)
            plan_dir = plans_active / "test-plan"
            plan_dir.mkdir()

            # Create invalid proposal (would normally fail validation)
            (plan_dir / "proposal.md").write_text("# Incomplete")

            # Execute with no-validate flag - should succeed despite invalid proposal
            command = ArchiveCommand()
            command.execute(
                plan_name="test-plan",
                target_path=str(target),
                yes=True,
                skip_specs=True,
                no_validate=True,
            )

            # Verify archived despite invalid content
            archive_dir = target / ".aurora" / "plans" / "archive"
            assert len(list(archive_dir.iterdir())) == 1
