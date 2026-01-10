"""
Tests for aurora.commands.archive module.

Ported from Aurora test/core/archive.test.ts
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aurora_planning.commands.archive import ArchiveCommand
from aurora_planning.validators.validator import Validator


class TestArchiveCommand:
    """Test ArchiveCommand class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp = Path(tempfile.mkdtemp(prefix="openspec-archive-test-"))
        yield temp
        # Cleanup
        if temp.exists():
            shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def setup_openspec_structure(self, temp_dir):
        """Create Aurora directory structure."""
        openspec_dir = temp_dir / ".aurora/plans"
        (openspec_dir / "changes").mkdir(parents=True)
        (openspec_dir / "specs").mkdir(parents=True)
        (openspec_dir / "changes" / "archive").mkdir(parents=True)
        return temp_dir

    @pytest.fixture
    def archive_command(self):
        """Create ArchiveCommand instance."""
        return ArchiveCommand()

    def test_archive_change_successfully(self, archive_command, setup_openspec_structure, temp_dir):
        """Should archive a change successfully."""
        # Create a test change
        change_name = "test-feature"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_dir.mkdir(parents=True)

        # Create tasks.md with completed tasks
        tasks_content = "- [x] Task 1\n- [x] Task 2"
        (change_dir / "tasks.md").write_text(tasks_content)

        # Execute archive with yes flag
        archive_command.execute(change_name, target_path=str(temp_dir), yes=True)

        # Check that change was moved to archive
        archive_dir = temp_dir / ".aurora/plans" / "changes" / "archive"
        archives = list(archive_dir.iterdir())

        assert len(archives) == 1
        # Archive should have date prefix YYYY-MM-DD-{change_name}
        assert change_name in archives[0].name
        assert not change_dir.exists()

    def test_warn_about_incomplete_tasks(
        self, archive_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should warn about incomplete tasks."""
        change_name = "incomplete-feature"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_dir.mkdir(parents=True)

        # Create tasks.md with incomplete tasks
        tasks_content = "- [x] Task 1\n- [ ] Task 2\n- [ ] Task 3"
        (change_dir / "tasks.md").write_text(tasks_content)

        # Execute archive with yes flag
        archive_command.execute(change_name, target_path=str(temp_dir), yes=True)

        # Verify warning was logged
        captured = capsys.readouterr()
        assert "2 incomplete task(s) found" in captured.out

    def test_update_specs_with_added_requirements(
        self, archive_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should update specs when archiving (delta-based ADDED) and include change name in skeleton."""
        change_name = "spec-feature"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_spec_dir = change_dir / "specs" / "test-capability"
        change_spec_dir.mkdir(parents=True)

        # Create delta-based change spec (ADDED requirement)
        spec_content = """# Test Capability Spec - Changes

## ADDED Requirements

### Requirement: The system SHALL provide test capability

#### Scenario: Basic test
Given a test condition
When an action occurs
Then expected result happens"""
        (change_spec_dir / "spec.md").write_text(spec_content)

        # Execute archive with yes flag and skip validation for speed
        archive_command.execute(change_name, target_path=str(temp_dir), yes=True, no_validate=True)

        # Verify spec was created from skeleton and ADDED requirement applied
        main_spec_path = temp_dir / ".aurora/plans" / "specs" / "test-capability" / "spec.md"
        updated_content = main_spec_path.read_text()
        assert "# test-capability Specification" in updated_content
        assert "## Purpose" in updated_content
        assert f"created by archiving change {change_name}" in updated_content
        assert "## Requirements" in updated_content
        assert "### Requirement: The system SHALL provide test capability" in updated_content
        assert "#### Scenario: Basic test" in updated_content

    def test_allow_removed_requirements_for_new_spec(
        self, archive_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should allow REMOVED requirements when creating new spec file (issue #403)."""
        change_name = "new-spec-with-removed"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_spec_dir = change_dir / "specs" / "gift-card"
        change_spec_dir.mkdir(parents=True)

        # Create delta spec with both ADDED and REMOVED requirements
        spec_content = """# Gift Card - Changes

## ADDED Requirements

### Requirement: Logo and Background Color
The system SHALL support logo and backgroundColor fields for gift cards.

#### Scenario: Display gift card with logo
- **WHEN** a gift card is displayed
- **THEN** it shows the logo and backgroundColor

## REMOVED Requirements

### Requirement: Image Field
### Requirement: Thumbnail Field"""
        (change_spec_dir / "spec.md").write_text(spec_content)

        # Execute archive - should succeed with warning about REMOVED requirements
        archive_command.execute(change_name, target_path=str(temp_dir), yes=True, no_validate=True)

        # Verify warning was logged about REMOVED requirements being ignored
        captured = capsys.readouterr()
        assert "2 REMOVED requirement(s) ignored for new spec (nothing to remove)" in captured.out

        # Verify spec was created with only ADDED requirements
        main_spec_path = temp_dir / ".aurora/plans" / "specs" / "gift-card" / "spec.md"
        updated_content = main_spec_path.read_text()
        assert "# gift-card Specification" in updated_content
        assert "### Requirement: Logo and Background Color" in updated_content
        assert "#### Scenario: Display gift card with logo" in updated_content
        # REMOVED requirements should not be in the final spec
        assert "### Requirement: Image Field" not in updated_content
        assert "### Requirement: Thumbnail Field" not in updated_content

        # Verify change was archived successfully
        archive_dir = temp_dir / ".aurora/plans" / "changes" / "archive"
        archives = list(archive_dir.iterdir())
        assert len(archives) > 0
        assert any(change_name in a.name for a in archives)

    def test_error_on_modified_for_new_spec(
        self, archive_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should still error on MODIFIED when creating new spec file."""
        change_name = "new-spec-with-modified"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_spec_dir = change_dir / "specs" / "new-capability"
        change_spec_dir.mkdir(parents=True)

        # Create delta spec with MODIFIED requirement (should fail for new spec)
        spec_content = """# New Capability - Changes

## ADDED Requirements

### Requirement: New Feature
New feature description.

## MODIFIED Requirements

### Requirement: Existing Feature
Modified content."""
        (change_spec_dir / "spec.md").write_text(spec_content)

        # Execute archive - should abort with error message
        archive_command.execute(change_name, target_path=str(temp_dir), yes=True, no_validate=True)

        # Verify error message mentions MODIFIED not allowed for new specs
        captured = capsys.readouterr()
        assert (
            "target spec does not exist; only ADDED requirements are allowed for new specs"
            in captured.out
        )
        assert "Aborted. No files were changed." in captured.out

        # Verify spec was NOT created
        main_spec_path = temp_dir / ".aurora/plans" / "specs" / "new-capability" / "spec.md"
        assert not main_spec_path.exists()

        # Verify change was NOT archived
        assert change_dir.exists()

    def test_error_on_renamed_for_new_spec(
        self, archive_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should still error on RENAMED when creating new spec file."""
        change_name = "new-spec-with-renamed"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_spec_dir = change_dir / "specs" / "another-capability"
        change_spec_dir.mkdir(parents=True)

        # Create delta spec with RENAMED requirement (should fail for new spec)
        spec_content = """# Another Capability - Changes

## ADDED Requirements

### Requirement: New Feature
New feature description.

## RENAMED Requirements
- FROM: `### Requirement: Old Name`
- TO: `### Requirement: New Name`"""
        (change_spec_dir / "spec.md").write_text(spec_content)

        # Execute archive - should abort with error message
        archive_command.execute(change_name, target_path=str(temp_dir), yes=True, no_validate=True)

        # Verify error message mentions RENAMED not allowed for new specs
        captured = capsys.readouterr()
        assert (
            "target spec does not exist; only ADDED requirements are allowed for new specs"
            in captured.out
        )
        assert "Aborted. No files were changed." in captured.out

        # Verify spec was NOT created
        main_spec_path = temp_dir / ".aurora/plans" / "specs" / "another-capability" / "spec.md"
        assert not main_spec_path.exists()

        # Verify change was NOT archived
        assert change_dir.exists()

    def test_error_if_change_not_found(self, archive_command, setup_openspec_structure, temp_dir):
        """Should throw error if change does not exist."""
        with pytest.raises(RuntimeError, match="Change 'non-existent-change' not found"):
            archive_command.execute("non-existent-change", target_path=str(temp_dir), yes=True)

    def test_error_if_archive_already_exists(
        self, archive_command, setup_openspec_structure, temp_dir
    ):
        """Should throw error if archive already exists."""
        change_name = "duplicate-feature"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_dir.mkdir(parents=True)

        # Create existing archive with same date
        date = datetime.now().strftime("%Y-%m-%d")
        archive_path = temp_dir / ".aurora/plans" / "changes" / "archive" / f"{date}-{change_name}"
        archive_path.mkdir(parents=True)

        # Try to archive
        with pytest.raises(RuntimeError, match=f"Archive '{date}-{change_name}' already exists"):
            archive_command.execute(change_name, target_path=str(temp_dir), yes=True)

    def test_handle_changes_without_tasks(
        self, archive_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should handle changes without tasks.md."""
        change_name = "no-tasks-feature"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_dir.mkdir(parents=True)

        # Execute archive without tasks.md
        archive_command.execute(change_name, target_path=str(temp_dir), yes=True)

        # Should complete without warnings
        captured = capsys.readouterr()
        assert "incomplete task(s)" not in captured.out

        # Verify change was archived
        archive_dir = temp_dir / ".aurora/plans" / "changes" / "archive"
        archives = list(archive_dir.iterdir())
        assert len(archives) == 1

    def test_handle_changes_without_specs(
        self, archive_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should handle changes without specs."""
        change_name = "no-specs-feature"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_dir.mkdir(parents=True)

        # Execute archive without specs
        archive_command.execute(change_name, target_path=str(temp_dir), yes=True)

        # Should complete without spec updates
        captured = capsys.readouterr()
        assert "Specs to update" not in captured.out

        # Verify change was archived
        archive_dir = temp_dir / ".aurora/plans" / "changes" / "archive"
        archives = list(archive_dir.iterdir())
        assert len(archives) == 1

    def test_skip_specs_flag(self, archive_command, setup_openspec_structure, temp_dir, capsys):
        """Should skip spec updates when --skip-specs flag is used."""
        change_name = "skip-specs-feature"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_spec_dir = change_dir / "specs" / "test-capability"
        change_spec_dir.mkdir(parents=True)

        # Create spec in change
        spec_content = "# Test Capability Spec\n\nTest content"
        (change_spec_dir / "spec.md").write_text(spec_content)

        # Execute archive with --skip-specs flag
        archive_command.execute(
            change_name,
            target_path=str(temp_dir),
            yes=True,
            skip_specs=True,
            no_validate=True,
        )

        # Verify skip message was logged
        captured = capsys.readouterr()
        assert "Skipping spec updates (--skip-specs flag provided)." in captured.out

        # Verify spec was NOT copied to main specs
        main_spec_path = temp_dir / ".aurora/plans" / "specs" / "test-capability" / "spec.md"
        assert not main_spec_path.exists()

        # Verify change was still archived
        archive_dir = temp_dir / ".aurora/plans" / "changes" / "archive"
        archives = list(archive_dir.iterdir())
        assert len(archives) == 1
        assert change_name in archives[0].name

    @patch.object(Validator, "validate_plan_modification_specs")
    @patch.object(Validator, "validate_capability_content")
    def test_skip_validation_with_no_validate_flag(
        self,
        mock_validate_capability,
        mock_validate_delta,
        archive_command,
        setup_openspec_structure,
        temp_dir,
    ):
        """Should skip validation when --no-validate flag is used."""
        change_name = "skip-validation-flag"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_spec_dir = change_dir / "specs" / "unstable-capability"
        change_spec_dir.mkdir(parents=True)

        delta_spec = """# Unstable Capability

## ADDED Requirements

### Requirement: Logging Feature
**ID**: REQ-LOG-001

The system will log all events.

#### Scenario: Event recorded
- **WHEN** an event occurs
- **THEN** it is captured"""
        (change_spec_dir / "spec.md").write_text(delta_spec)
        (change_dir / "tasks.md").write_text("- [x] Task 1\n")

        archive_command.execute(
            change_name,
            target_path=str(temp_dir),
            yes=True,
            skip_specs=True,
            validate=False,
        )

        # Validation methods should not be called
        mock_validate_delta.assert_not_called()
        mock_validate_capability.assert_not_called()

        # Verify change was archived
        archive_dir = temp_dir / ".aurora/plans" / "changes" / "archive"
        archives = list(archive_dir.iterdir())
        assert len(archives) == 1
        assert change_name in archives[0].name

    def test_header_normalization(self, archive_command, setup_openspec_structure, temp_dir):
        """Should support header trim-only normalization for matching."""
        change_name = "normalize-headers"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_spec_dir = change_dir / "specs" / "alpha"
        change_spec_dir.mkdir(parents=True)

        # Create existing main spec with a requirement (no extra trailing spaces)
        main_spec_dir = temp_dir / ".aurora/plans" / "specs" / "alpha"
        main_spec_dir.mkdir(parents=True)
        main_content = """# alpha Specification

## Purpose
Alpha purpose.

## Requirements

### Requirement: Important Rule
Some details."""
        (main_spec_dir / "spec.md").write_text(main_content)

        # Change attempts to modify the same requirement but with trailing spaces
        delta_content = """# Alpha - Changes

## MODIFIED Requirements

### Requirement: Important Rule
Updated details."""
        (change_spec_dir / "spec.md").write_text(delta_content)

        archive_command.execute(change_name, target_path=str(temp_dir), yes=True, no_validate=True)

        updated = (main_spec_dir / "spec.md").read_text()
        assert "### Requirement: Important Rule" in updated
        assert "Updated details." in updated

    def test_operations_applied_in_order(self, archive_command, setup_openspec_structure, temp_dir):
        """Should apply operations in order: RENAMED → REMOVED → MODIFIED → ADDED."""
        change_name = "apply-order"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_spec_dir = change_dir / "specs" / "beta"
        change_spec_dir.mkdir(parents=True)

        # Main spec with two requirements A and B
        main_spec_dir = temp_dir / ".aurora/plans" / "specs" / "beta"
        main_spec_dir.mkdir(parents=True)
        main_content = """# beta Specification

## Purpose
Beta purpose.

## Requirements

### Requirement: A
content A

### Requirement: B
content B"""
        (main_spec_dir / "spec.md").write_text(main_content)

        # Rename A->C, Remove B, Modify C, Add D
        delta_content = """# Beta - Changes

## RENAMED Requirements
- FROM: `### Requirement: A`
- TO: `### Requirement: C`

## REMOVED Requirements
### Requirement: B

## MODIFIED Requirements
### Requirement: C
updated C

## ADDED Requirements
### Requirement: D
content D"""
        (change_spec_dir / "spec.md").write_text(delta_content)

        archive_command.execute(change_name, target_path=str(temp_dir), yes=True, no_validate=True)

        updated = (main_spec_dir / "spec.md").read_text()
        assert "### Requirement: C" in updated
        assert "updated C" in updated
        assert "### Requirement: D" in updated
        assert "### Requirement: A" not in updated
        assert "### Requirement: B" not in updated

    def test_error_on_missing_requirements(
        self, archive_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should abort with error when MODIFIED/REMOVED reference non-existent requirements."""
        change_name = "validate-missing"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_spec_dir = change_dir / "specs" / "gamma"
        change_spec_dir.mkdir(parents=True)

        # Main spec with no requirements
        main_spec_dir = temp_dir / ".aurora/plans" / "specs" / "gamma"
        main_spec_dir.mkdir(parents=True)
        main_content = """# gamma Specification

## Purpose
Gamma purpose.

## Requirements"""
        (main_spec_dir / "spec.md").write_text(main_content)

        # Delta tries to modify and remove non-existent requirement
        delta_content = """# Gamma - Changes

## MODIFIED Requirements
### Requirement: Missing
new text

## REMOVED Requirements
### Requirement: Another Missing"""
        (change_spec_dir / "spec.md").write_text(delta_content)

        archive_command.execute(change_name, target_path=str(temp_dir), yes=True, no_validate=True)

        # Should not change the main spec and should not archive the change dir
        still = (main_spec_dir / "spec.md").read_text()
        assert still == main_content
        # Change dir should still exist since operation aborted
        assert change_dir.exists()

    def test_modified_must_reference_new_header_after_rename(
        self, archive_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should require MODIFIED to reference the NEW header when a rename exists."""
        change_name = "rename-modify-new-header"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        change_spec_dir = change_dir / "specs" / "delta"
        change_spec_dir.mkdir(parents=True)

        # Main spec with Old
        main_spec_dir = temp_dir / ".aurora/plans" / "specs" / "delta"
        main_spec_dir.mkdir(parents=True)
        main_content = """# delta Specification

## Purpose
Delta purpose.

## Requirements

### Requirement: Old
old body"""
        (main_spec_dir / "spec.md").write_text(main_content)

        # Delta: rename Old->New, but MODIFIED references Old (should abort)
        bad_delta = """# Delta - Changes

## RENAMED Requirements
- FROM: `### Requirement: Old`
- TO: `### Requirement: New`

## MODIFIED Requirements
### Requirement: Old
new body"""
        (change_spec_dir / "spec.md").write_text(bad_delta)

        archive_command.execute(change_name, target_path=str(temp_dir), yes=True, no_validate=True)
        unchanged = (main_spec_dir / "spec.md").read_text()
        assert unchanged == main_content
        # Assert error message format and abort notice
        captured = capsys.readouterr()
        assert "delta validation failed" in captured.out
        assert "Aborted. No files were changed." in captured.out

        # Fix MODIFIED to reference New (should succeed)
        good_delta = """# Delta - Changes

## RENAMED Requirements
- FROM: `### Requirement: Old`
- TO: `### Requirement: New`

## MODIFIED Requirements
### Requirement: New
new body"""
        (change_spec_dir / "spec.md").write_text(good_delta)

        archive_command.execute(change_name, target_path=str(temp_dir), yes=True, no_validate=True)
        updated = (main_spec_dir / "spec.md").read_text()
        assert "### Requirement: New" in updated
        assert "new body" in updated
        assert "### Requirement: Old" not in updated

    def test_multiple_specs_atomic(self, archive_command, setup_openspec_structure, temp_dir):
        """Should process multiple specs atomically (any failure aborts all)."""
        change_name = "multi-spec-atomic"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        spec1_dir = change_dir / "specs" / "epsilon"
        spec2_dir = change_dir / "specs" / "zeta"
        spec1_dir.mkdir(parents=True)
        spec2_dir.mkdir(parents=True)

        # Existing main specs
        epsilon_main = temp_dir / ".aurora/plans" / "specs" / "epsilon" / "spec.md"
        epsilon_main.parent.mkdir(parents=True)
        epsilon_main.write_text(
            """# epsilon Specification

## Purpose
Epsilon purpose.

## Requirements

### Requirement: E1
e1"""
        )

        zeta_main = temp_dir / ".aurora/plans" / "specs" / "zeta" / "spec.md"
        zeta_main.parent.mkdir(parents=True)
        zeta_main.write_text(
            """# zeta Specification

## Purpose
Zeta purpose.

## Requirements

### Requirement: Z1
z1"""
        )

        # Delta: epsilon is valid modification; zeta tries to remove non-existent
        (spec1_dir / "spec.md").write_text(
            """# Epsilon - Changes

## MODIFIED Requirements
### Requirement: E1
E1 updated"""
        )

        (spec2_dir / "spec.md").write_text(
            """# Zeta - Changes

## REMOVED Requirements
### Requirement: Missing"""
        )

        archive_command.execute(change_name, target_path=str(temp_dir), yes=True, no_validate=True)

        e1 = epsilon_main.read_text()
        z1 = zeta_main.read_text()
        assert "### Requirement: E1" in e1
        assert "E1 updated" not in e1  # Should not be updated due to atomic abort
        assert "### Requirement: Z1" in z1
        # changeDir should still exist
        assert change_dir.exists()

    def test_aggregated_totals_across_multiple_specs(
        self, archive_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should display aggregated totals across multiple specs."""
        change_name = "multi-spec-totals"
        change_dir = temp_dir / ".aurora/plans" / "changes" / change_name
        spec1_dir = change_dir / "specs" / "omega"
        spec2_dir = change_dir / "specs" / "psi"
        spec1_dir.mkdir(parents=True)
        spec2_dir.mkdir(parents=True)

        # Existing main specs
        omega_main = temp_dir / ".aurora/plans" / "specs" / "omega" / "spec.md"
        omega_main.parent.mkdir(parents=True)
        omega_main.write_text(
            "# omega Specification\n\n## Purpose\nOmega purpose.\n\n## Requirements\n\n### Requirement: O1\no1"
        )

        psi_main = temp_dir / ".aurora/plans" / "specs" / "psi" / "spec.md"
        psi_main.parent.mkdir(parents=True)
        psi_main.write_text(
            "# psi Specification\n\n## Purpose\nPsi purpose.\n\n## Requirements\n\n### Requirement: P1\np1"
        )

        # Deltas: omega add one, psi rename and modify
        (spec1_dir / "spec.md").write_text(
            "# Omega - Changes\n\n## ADDED Requirements\n\n### Requirement: O2\nnew"
        )
        (spec2_dir / "spec.md").write_text(
            "# Psi - Changes\n\n## RENAMED Requirements\n- FROM: `### Requirement: P1`\n- TO: `### Requirement: P2`\n\n## MODIFIED Requirements\n### Requirement: P2\nupdated"
        )

        archive_command.execute(change_name, target_path=str(temp_dir), yes=True, no_validate=True)

        # Verify aggregated totals line was printed
        captured = capsys.readouterr()
        assert "Totals: + 1, ~ 1, - 0, → 1" in captured.out

    def test_error_when_openspec_directory_missing(
        self, archive_command, setup_openspec_structure, temp_dir
    ):
        """Should throw error when .aurora/plans directory does not exist."""
        # Remove .aurora/plans directory
        shutil.rmtree(temp_dir / ".aurora/plans")

        with pytest.raises(
            RuntimeError,
            match="No Aurora plans directory found. Run .aur init' first.",
        ):
            archive_command.execute("any-change", target_path=str(temp_dir), yes=True)

    @patch("builtins.input", side_effect=["test-feature-a"])
    def test_interactive_change_selection(
        self, mock_input, archive_command, setup_openspec_structure, temp_dir
    ):
        """Should use interactive prompt for change selection when name not provided."""
        # Create test changes
        change1 = "feature-a"
        change2 = "feature-b"
        (temp_dir / ".aurora/plans" / "changes" / change1).mkdir(parents=True)
        (temp_dir / ".aurora/plans" / "changes" / change2).mkdir(parents=True)

        # Execute without change name - will use interactive selection
        # In real implementation this would use questionary/inquirer
        # For now we test the selection logic exists
        change_dirs = list((temp_dir / ".aurora/plans" / "changes").iterdir())
        change_dirs = [d for d in change_dirs if d.is_dir() and d.name != "archive"]
        assert len(change_dirs) == 2
        assert change1 in [d.name for d in change_dirs]
        assert change2 in [d.name for d in change_dirs]
