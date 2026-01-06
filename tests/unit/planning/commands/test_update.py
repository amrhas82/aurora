"""
Tests for aurora.commands.update module.

Simplified tests focusing on AGENTS.md update.
Full configurator tests will be added in Phase 7.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from aurora_planning.commands.update import UpdateCommand
from aurora_planning.templates.agents import AGENTS_TEMPLATE


class TestUpdateCommand:
    """Test UpdateCommand class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp = Path(tempfile.mkdtemp(prefix="openspec-update-test-"))
        yield temp
        # Cleanup
        if temp.exists():
            shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def setup_openspec_structure(self, temp_dir):
        """Create Aurora directory structure."""
        openspec_dir = temp_dir / ".aurora/plans"
        openspec_dir.mkdir(parents=True)
        return temp_dir

    @pytest.fixture
    def update_command(self):
        """Create UpdateCommand instance."""
        return UpdateCommand()

    def test_update_creates_agents_md(
        self, update_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should create AGENTS.md if it doesn't exist."""
        # Execute update command
        update_command.execute(str(temp_dir))

        # Check that AGENTS.md was created
        agents_path = temp_dir / ".aurora/plans" / "AGENTS.md"
        assert agents_path.exists()

        # Verify content matches template
        content = agents_path.read_text()
        assert content == AGENTS_TEMPLATE
        assert "# Aurora Instructions" in content

        # Check console output
        captured = capsys.readouterr()
        assert "Updated Aurora instructions" in captured.out
        assert ".aurora/plans/AGENTS.md" in captured.out

    def test_update_replaces_existing_agents_md(
        self, update_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should replace existing AGENTS.md with new template."""
        # Create existing AGENTS.md with old content
        agents_path = temp_dir / ".aurora/plans" / "AGENTS.md"
        old_content = "# Old Aurora Instructions\n\nOld content here."
        agents_path.write_text(old_content)

        # Execute update command
        update_command.execute(str(temp_dir))

        # Check that AGENTS.md was replaced
        new_content = agents_path.read_text()
        assert new_content == AGENTS_TEMPLATE
        assert "# Aurora Instructions" in new_content
        assert "Old content here" not in new_content

        # Check console output
        captured = capsys.readouterr()
        assert "Updated Aurora instructions" in captured.out

    def test_error_if_openspec_directory_missing(
        self, update_command, temp_dir
    ):
        """Should throw error if .aurora/plans directory does not exist."""
        with pytest.raises(
            RuntimeError,
            match="No Aurora plans directory found. Run .aur init' first."
        ):
            update_command.execute(str(temp_dir))

    def test_verbose_output(
        self, update_command, setup_openspec_structure, temp_dir, capsys
    ):
        """Should show detailed output in verbose mode."""
        # Execute with verbose flag
        update_command.execute(str(temp_dir), verbose=True)

        # Check verbose output
        captured = capsys.readouterr()
        assert "Creating" in captured.out or "Updating" in captured.out
        assert ".aurora/plans/AGENTS.md" in captured.out
        assert "✓ Updated" in captured.out

    def test_agents_template_contains_key_sections(
        self, update_command, setup_openspec_structure, temp_dir
    ):
        """Should verify AGENTS.md contains all key sections."""
        update_command.execute(str(temp_dir))

        agents_path = temp_dir / ".aurora/plans" / "AGENTS.md"
        content = agents_path.read_text()

        # Verify key sections are present
        assert "## TL;DR Quick Checklist" in content
        assert "## Three-Stage Workflow" in content
        assert "### Stage 1: Creating Changes" in content
        assert "### Stage 2: Implementing Changes" in content
        assert "### Stage 3: Archiving Changes" in content
        assert "## Spec File Format" in content
        assert "### Delta Operations" in content
        assert "## ADDED Requirements" in content
        assert "## MODIFIED Requirements" in content
        assert "## REMOVED Requirements" in content
        assert "## RENAMED Requirements" in content
        assert "#### Scenario:" in content
        assert "## Troubleshooting" in content
        assert "## Best Practices" in content

    def test_agents_template_has_critical_rules(
        self, update_command, setup_openspec_structure, temp_dir
    ):
        """Should verify AGENTS.md contains critical formatting rules."""
        update_command.execute(str(temp_dir))

        agents_path = temp_dir / ".aurora/plans" / "AGENTS.md"
        content = agents_path.read_text()

        # Critical formatting rules
        assert "### Critical: Scenario Formatting" in content
        assert "use #### headers" in content
        assert "Every requirement MUST have at least one scenario" in content

        # When to use ADDED vs MODIFIED guidance
        assert "#### When to use ADDED vs MODIFIED" in content
        assert "Authoring a MODIFIED requirement correctly:" in content

        # Validation tips
        assert "### Validation Tips" in content
        assert "aur validate" in content
        assert "--strict" in content
