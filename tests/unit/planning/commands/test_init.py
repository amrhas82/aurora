"""
Tests for aurora.commands.init module.

Ported from Aurora test/core/init.test.ts - SIMPLIFIED VERSION
Full configurator support deferred to Phase 7 (CLI Commands).
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from aurora_planning.commands.init import InitCommand


class TestInitCommand:
    """Test InitCommand class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp = Path(tempfile.mkdtemp(prefix="openspec-init-test-"))
        yield temp
        # Cleanup
        if temp.exists():
            shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def init_command(self):
        """Create InitCommand instance."""
        return InitCommand()

    def test_create_openspec_directory_structure(self, init_command, temp_dir):
        """Should create Aurora directory structure."""
        init_command.execute(str(temp_dir))

        plans_path = temp_dir / ".aurora/plans"
        assert plans_path.exists()
        assert (plans_path / "specs").exists()
        assert (plans_path / "changes").exists()
        assert (plans_path / "changes" / "archive").exists()

    def test_create_agents_md_and_project_md(self, init_command, temp_dir):
        """Should create AGENTS.md and project.md."""
        init_command.execute(str(temp_dir))

        plans_path = temp_dir / ".aurora/plans"
        assert (plans_path / "AGENTS.md").exists()
        assert (plans_path / "project.md").exists()

        agents_content = (plans_path / "AGENTS.md").read_text()
        assert "Aurora Instructions" in agents_content

        project_content = (plans_path / "project.md").read_text()
        assert "Project Context" in project_content

    def test_create_root_agents_md_stub(self, init_command, temp_dir):
        """Should always create AGENTS.md stub in project root."""
        init_command.execute(str(temp_dir))

        root_agents_path = temp_dir / "AGENTS.md"
        assert root_agents_path.exists()

        content = root_agents_path.read_text()
        assert "<!-- AURORA:START -->" in content
        assert "@/.aurora/AGENTS.md" in content
        assert "aur init --config" in content
        assert "<!-- AURORA:END -->" in content

    def test_update_existing_root_agents_md_with_markers(self, init_command, temp_dir):
        """Should update existing root AGENTS.md with markers."""
        root_agents_path = temp_dir / "AGENTS.md"
        existing_content = "# My Project Instructions\nCustom instructions here"
        root_agents_path.write_text(existing_content)

        init_command.execute(str(temp_dir))

        updated_content = root_agents_path.read_text()
        assert "<!-- AURORA:START -->" in updated_content
        assert "@/.aurora/AGENTS.md" in updated_content
        assert "aur init --config" in updated_content
        assert "<!-- AURORA:END -->" in updated_content
        assert "Custom instructions here" in updated_content

    def test_extend_mode_preserves_existing_template_files(self, init_command, temp_dir):
        """Should preserve existing template files in extend mode."""
        # First init
        init_command.execute(str(temp_dir))

        agents_path = temp_dir / ".aurora/plans" / "AGENTS.md"
        custom_content = "# My Custom AGENTS Content\nDo not overwrite this!"
        agents_path.write_text(custom_content)

        # Run init again - should NOT overwrite
        init_command.execute(str(temp_dir))

        content = agents_path.read_text()
        assert content == custom_content
        assert "Aurora Instructions" not in content

    def test_recreate_deleted_agents_md_in_extend_mode(self, init_command, temp_dir):
        """Should recreate deleted .aurora/plans/AGENTS.md in extend mode."""
        # First init
        init_command.execute(str(temp_dir))

        agents_path = temp_dir / ".aurora/plans" / "AGENTS.md"
        assert agents_path.exists()

        # Delete the file
        agents_path.unlink()
        assert not agents_path.exists()

        # Run init again - should recreate the file
        init_command.execute(str(temp_dir))
        assert agents_path.exists()

        content = agents_path.read_text()
        assert "Aurora Instructions" in content

    def test_recreate_deleted_project_md_in_extend_mode(self, init_command, temp_dir):
        """Should recreate deleted .aurora/plans/project.md in extend mode."""
        # First init
        init_command.execute(str(temp_dir))

        project_path = temp_dir / ".aurora/plans" / "project.md"
        assert project_path.exists()

        # Delete the file
        project_path.unlink()
        assert not project_path.exists()

        # Run init again - should recreate the file
        init_command.execute(str(temp_dir))
        assert project_path.exists()

        content = project_path.read_text()
        assert "Project Context" in content

    def test_handle_non_existent_target_directory(self, init_command, temp_dir):
        """Should handle non-existent target directory."""
        new_dir = temp_dir / "new-project"
        init_command.execute(str(new_dir))

        plans_path = new_dir / ".aurora/plans"
        assert plans_path.exists()
