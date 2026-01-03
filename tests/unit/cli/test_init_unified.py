"""Tests for unified init command - test_init_unified.py

This test module verifies the unified `aur init` command that combines
initialization and planning setup into a single 3-step flow.

Test-Driven Development (TDD):
- Tests are written FIRST (RED phase)
- Implementation comes SECOND (GREEN phase)
- Refactor THIRD (REFACTOR phase)
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from aurora_cli.commands.init import run_step_1_planning_setup


class TestStep1PlanningSetup:
    """Test Step 1: Planning Setup (Git + Directories)."""

    def test_run_step_1_detects_existing_git_repository(self, tmp_path):
        """run_step_1_planning_setup() should detect existing .git directory."""
        # Create .git directory
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("subprocess.run") as mock_subprocess:
            result = run_step_1_planning_setup(tmp_path)

            # Should NOT call git init since .git exists
            mock_subprocess.assert_not_called()

        # Should still create directories and project.md
        assert (tmp_path / ".aurora" / "plans" / "active").exists()
        assert (tmp_path / ".aurora" / "project.md").exists()

    def test_run_step_1_prompts_git_init_when_no_git(self, tmp_path):
        """run_step_1_planning_setup() should prompt for git init when .git missing."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=False):
            result = run_step_1_planning_setup(tmp_path)

            # Should detect no git and prompt user
            # User declined, so no git initialization

        # Should still create Aurora directories
        assert (tmp_path / ".aurora" / "plans" / "active").exists()

    def test_run_step_1_runs_git_init_when_user_accepts(self, tmp_path):
        """run_step_1_planning_setup() should run git init when user accepts."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=True) as mock_prompt:
            with patch("subprocess.run") as mock_subprocess:
                result = run_step_1_planning_setup(tmp_path)

                # Should prompt for git init
                mock_prompt.assert_called_once()

                # Should call git init
                mock_subprocess.assert_called_once_with(
                    ["git", "init"],
                    cwd=tmp_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )

        # Should create directories
        assert (tmp_path / ".aurora" / "plans" / "active").exists()

    def test_run_step_1_skips_git_init_when_user_declines(self, tmp_path):
        """run_step_1_planning_setup() should skip git init when user declines."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=False) as mock_prompt:
            with patch("subprocess.run") as mock_subprocess:
                result = run_step_1_planning_setup(tmp_path)

                # Should prompt
                mock_prompt.assert_called_once()

                # Should NOT call git init
                mock_subprocess.assert_not_called()

    def test_run_step_1_creates_plans_active_directory(self, tmp_path):
        """run_step_1_planning_setup() should create .aurora/plans/active directory."""
        # Mock git detection to skip prompts
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        run_step_1_planning_setup(tmp_path)

        active_dir = tmp_path / ".aurora" / "plans" / "active"
        assert active_dir.exists()
        assert active_dir.is_dir()

    def test_run_step_1_creates_plans_archive_directory(self, tmp_path):
        """run_step_1_planning_setup() should create .aurora/plans/archive directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        run_step_1_planning_setup(tmp_path)

        archive_dir = tmp_path / ".aurora" / "plans" / "archive"
        assert archive_dir.exists()
        assert archive_dir.is_dir()

    def test_run_step_1_creates_logs_directory(self, tmp_path):
        """run_step_1_planning_setup() should create .aurora/logs directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        run_step_1_planning_setup(tmp_path)

        logs_dir = tmp_path / ".aurora" / "logs"
        assert logs_dir.exists()
        assert logs_dir.is_dir()

    def test_run_step_1_creates_cache_directory(self, tmp_path):
        """run_step_1_planning_setup() should create .aurora/cache directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        run_step_1_planning_setup(tmp_path)

        cache_dir = tmp_path / ".aurora" / "cache"
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_run_step_1_creates_project_md_with_metadata(self, tmp_path):
        """run_step_1_planning_setup() should create project.md with auto-detected metadata."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Create pyproject.toml for detection
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.poetry]\nname = "test-project"\n', encoding="utf-8")

        run_step_1_planning_setup(tmp_path)

        project_md = tmp_path / ".aurora" / "project.md"
        assert project_md.exists()

        content = project_md.read_text()
        assert "# Project Overview" in content
        assert "## Tech Stack" in content

    def test_run_step_1_preserves_existing_project_md(self, tmp_path):
        """run_step_1_planning_setup() should NOT overwrite existing project.md."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Create .aurora directory and project.md
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        project_md = aurora_dir / "project.md"
        custom_content = "# My Custom Project\n\nDo not overwrite this!"
        project_md.write_text(custom_content, encoding="utf-8")

        run_step_1_planning_setup(tmp_path)

        # Should preserve custom content
        final_content = project_md.read_text()
        assert final_content == custom_content

    def test_run_step_1_returns_true_when_git_initialized(self, tmp_path):
        """run_step_1_planning_setup() should return True when git was initialized."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=True):
            with patch("subprocess.run"):
                result = run_step_1_planning_setup(tmp_path)

                assert result is True

    def test_run_step_1_returns_false_when_git_declined(self, tmp_path):
        """run_step_1_planning_setup() should return False when git init declined."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=False):
            result = run_step_1_planning_setup(tmp_path)

            assert result is False

    def test_run_step_1_returns_true_when_git_already_exists(self, tmp_path):
        """run_step_1_planning_setup() should return True when .git already exists."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = run_step_1_planning_setup(tmp_path)

        assert result is True

    def test_run_step_1_handles_git_init_failure(self, tmp_path):
        """run_step_1_planning_setup() should handle git init subprocess errors."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=True):
            with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git init")):
                # Should not raise - should handle gracefully
                with patch("aurora_cli.commands.init.console") as mock_console:
                    result = run_step_1_planning_setup(tmp_path)

                    # Should print error message
                    assert any("failed" in str(call).lower() or "error" in str(call).lower()
                               for call in mock_console.print.call_args_list)

                    # Should still create directories
                    assert (tmp_path / ".aurora" / "plans" / "active").exists()

    def test_run_step_1_is_idempotent(self, tmp_path):
        """run_step_1_planning_setup() should be safe to run multiple times."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Run first time
        result1 = run_step_1_planning_setup(tmp_path)
        assert result1 is True

        # Create custom content in project.md
        project_md = tmp_path / ".aurora" / "project.md"
        original_content = project_md.read_text()
        project_md.write_text("# Custom content", encoding="utf-8")

        # Run second time
        result2 = run_step_1_planning_setup(tmp_path)
        assert result2 is True

        # Should preserve custom content
        final_content = project_md.read_text()
        assert final_content == "# Custom content"

    def test_run_step_1_shows_success_message(self, tmp_path):
        """run_step_1_planning_setup() should display success message to user."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("aurora_cli.commands.init.console") as mock_console:
            run_step_1_planning_setup(tmp_path)

            # Should print success message
            assert any("created" in str(call).lower() or "detected" in str(call).lower()
                       for call in mock_console.print.call_args_list)


class TestStep2MemoryIndexing:
    """Test Step 2: Memory Indexing."""

    def test_run_step_2_calculates_project_specific_db_path(self, tmp_path):
        """run_step_2_memory_indexing() should use project-specific db_path."""
        from aurora_cli.commands.init import run_step_2_memory_indexing

        # Mock MemoryManager to avoid actual indexing (patch where it's imported)
        with patch("aurora_cli.memory_manager.MemoryManager") as mock_manager:
            with patch("aurora_cli.config.Config") as mock_config:
                mock_instance = MagicMock()
                mock_manager.return_value = mock_instance

                # Mock index_path to return stats
                from aurora_cli.memory_manager import IndexStats
                mock_instance.index_path.return_value = IndexStats(
                    files_indexed=5,
                    chunks_created=20,
                    duration_seconds=1.5
                )

                run_step_2_memory_indexing(tmp_path)

                # Should create Config with project-specific db_path
                mock_config.assert_called_once()
                config_call = mock_config.call_args

                # db_path should be project_path / ".aurora" / "memory.db"
                expected_db = str(tmp_path / ".aurora" / "memory.db")
                # Check that Config was called with db_path parameter
                assert config_call[1]["db_path"] == expected_db

    def test_run_step_2_prompts_reindex_when_db_exists(self, tmp_path):
        """run_step_2_memory_indexing() should prompt to re-index when memory.db exists."""
        from aurora_cli.commands.init import run_step_2_memory_indexing

        # Create existing memory.db
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir(parents=True)
        memory_db = aurora_dir / "memory.db"
        memory_db.write_text("fake db content", encoding="utf-8")

        with patch("aurora_cli.memory_manager.MemoryManager"):
            with patch("aurora_cli.config.Config"):
                with patch("click.confirm", return_value=False) as mock_confirm:
                    run_step_2_memory_indexing(tmp_path)

                    # Should ask user to confirm re-indexing
                    mock_confirm.assert_called_once()
                    args = mock_confirm.call_args
                    assert "re-index" in str(args).lower() or "reindex" in str(args).lower()

    def test_run_step_2_creates_backup_before_reindexing(self, tmp_path):
        """run_step_2_memory_indexing() should backup memory.db before re-indexing."""
        from aurora_cli.commands.init import run_step_2_memory_indexing

        # Create existing memory.db
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir(parents=True)
        memory_db = aurora_dir / "memory.db"
        original_content = "original database content"
        memory_db.write_text(original_content, encoding="utf-8")

        with patch("aurora_cli.memory_manager.MemoryManager") as mock_manager:
            with patch("aurora_cli.config.Config"):
                with patch("click.confirm", return_value=True):
                    mock_instance = MagicMock()
                    mock_manager.return_value = mock_instance

                    from aurora_cli.memory_manager import IndexStats
                    mock_instance.index_path.return_value = IndexStats(
                        files_indexed=1,
                        chunks_created=5,
                        duration_seconds=0.5
                    )

                    run_step_2_memory_indexing(tmp_path)

                    # Should create backup file
                    backup_file = aurora_dir / "memory.db.backup"
                    assert backup_file.exists()
                    assert backup_file.read_text() == original_content

    def test_run_step_2_handles_indexing_errors(self, tmp_path):
        """run_step_2_memory_indexing() should handle indexing errors gracefully."""
        from aurora_cli.commands.init import run_step_2_memory_indexing

        with patch("aurora_cli.memory_manager.MemoryManager") as mock_manager:
            with patch("aurora_cli.config.Config"):
                mock_instance = MagicMock()
                mock_manager.return_value = mock_instance

                # Simulate indexing error
                mock_instance.index_path.side_effect = RuntimeError("Indexing failed")

                with patch("click.confirm", return_value=True) as mock_confirm:
                    # Should not raise - should handle gracefully (skip=True)
                    run_step_2_memory_indexing(tmp_path)

                    # Should prompt user for action (skip/abort)
                    assert mock_confirm.called

    def test_run_step_2_skip_continues_to_next_step(self, tmp_path):
        """run_step_2_memory_indexing() skip option should return without error."""
        from aurora_cli.commands.init import run_step_2_memory_indexing

        with patch("aurora_cli.memory_manager.MemoryManager") as mock_manager:
            with patch("aurora_cli.config.Config"):
                mock_instance = MagicMock()
                mock_manager.return_value = mock_instance
                mock_instance.index_path.side_effect = RuntimeError("Error")

                with patch("click.confirm", return_value=True):  # Yes, skip
                    # Should return without raising
                    result = run_step_2_memory_indexing(tmp_path)
                    # Should return False (skipped)
                    assert result is False

    def test_run_step_2_abort_exits_cleanly(self, tmp_path):
        """run_step_2_memory_indexing() abort option should exit."""
        from aurora_cli.commands.init import run_step_2_memory_indexing

        with patch("aurora_cli.memory_manager.MemoryManager") as mock_manager:
            with patch("aurora_cli.config.Config"):
                mock_instance = MagicMock()
                mock_manager.return_value = mock_instance
                mock_instance.index_path.side_effect = RuntimeError("Error")

                with patch("click.confirm", return_value=False):  # No, abort
                    with pytest.raises(SystemExit):
                        run_step_2_memory_indexing(tmp_path)

    def test_run_step_2_uses_progress_callback(self, tmp_path):
        """run_step_2_memory_indexing() should use progress bar for indexing."""
        from aurora_cli.commands.init import run_step_2_memory_indexing

        with patch("aurora_cli.memory_manager.MemoryManager") as mock_manager:
            with patch("aurora_cli.config.Config"):
                mock_instance = MagicMock()
                mock_manager.return_value = mock_instance

                from aurora_cli.memory_manager import IndexStats
                mock_instance.index_path.return_value = IndexStats(
                    files_indexed=10,
                    chunks_created=50,
                    duration_seconds=2.0
                )

                with patch("rich.progress.Progress") as mock_progress:
                    run_step_2_memory_indexing(tmp_path)

                    # Should create progress bar
                    assert mock_progress.called

                    # Should call index_path with progress_callback
                    mock_instance.index_path.assert_called_once()
                    call_kwargs = mock_instance.index_path.call_args[1]
                    assert "progress_callback" in call_kwargs
                    assert call_kwargs["progress_callback"] is not None

    def test_run_step_2_shows_success_stats(self, tmp_path):
        """run_step_2_memory_indexing() should display indexing statistics."""
        from aurora_cli.commands.init import run_step_2_memory_indexing

        with patch("aurora_cli.memory_manager.MemoryManager") as mock_manager:
            with patch("aurora_cli.config.Config"):
                mock_instance = MagicMock()
                mock_manager.return_value = mock_instance

                from aurora_cli.memory_manager import IndexStats
                stats = IndexStats(
                    files_indexed=15,
                    chunks_created=75,
                    duration_seconds=3.5
                )
                mock_instance.index_path.return_value = stats

                with patch("aurora_cli.commands.init.console") as mock_console:
                    run_step_2_memory_indexing(tmp_path)

                    # Should print stats
                    print_calls = [str(call) for call in mock_console.print.call_args_list]
                    combined = " ".join(print_calls)

                    # Should show file count
                    assert "15" in combined or "files" in combined.lower()

    def test_run_step_2_skips_prompt_on_fresh_install(self, tmp_path):
        """run_step_2_memory_indexing() should not prompt when memory.db doesn't exist."""
        from aurora_cli.commands.init import run_step_2_memory_indexing

        # No memory.db exists yet
        with patch("aurora_cli.memory_manager.MemoryManager") as mock_manager:
            with patch("aurora_cli.config.Config"):
                mock_instance = MagicMock()
                mock_manager.return_value = mock_instance

                from aurora_cli.memory_manager import IndexStats
                mock_instance.index_path.return_value = IndexStats(
                    files_indexed=1,
                    chunks_created=5,
                    duration_seconds=0.5
                )

                with patch("click.confirm") as mock_confirm:
                    run_step_2_memory_indexing(tmp_path)

                    # Should NOT prompt since db doesn't exist
                    mock_confirm.assert_not_called()


class TestStep3ToolConfiguration:
    """Test Step 3: Tool Configuration."""

    def test_run_step_3_detects_no_configured_tools(self, tmp_path):
        """run_step_3_tool_configuration() should detect when no tools are configured."""
        from aurora_cli.commands.init import run_step_3_tool_configuration
        from unittest.mock import AsyncMock

        # Mock the detection and configuration functions (patch where they're imported)
        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}) as mock_detect:
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=[]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=([], [])):
                    run_step_3_tool_configuration(tmp_path)

                    # Should call detect_configured_tools
                    mock_detect.assert_called_once_with(tmp_path)

    def test_run_step_3_detects_existing_tools(self, tmp_path):
        """run_step_3_tool_configuration() should detect existing tool configurations."""
        from aurora_cli.commands.init import run_step_3_tool_configuration
        from unittest.mock import AsyncMock

        # Simulate 2 tools already configured
        configured_tools = {
            "claude": True,
            "universal-agents.md": True,
            "opencode": False,
        }

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value=configured_tools):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=[]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=([], [])):
                    run_step_3_tool_configuration(tmp_path)

    def test_run_step_3_calls_prompt_tool_selection(self, tmp_path):
        """run_step_3_tool_configuration() should call prompt_tool_selection for interactive mode."""
        from aurora_cli.commands.init import run_step_3_tool_configuration
        from unittest.mock import AsyncMock

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=["claude"]) as mock_prompt:
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=(["Claude Code"], [])):
                    run_step_3_tool_configuration(tmp_path)

                    # Should call prompt_tool_selection with detected tools
                    mock_prompt.assert_called_once()
                    call_kwargs = mock_prompt.call_args[1]
                    assert "configured_tools" in call_kwargs

    def test_run_step_3_calls_configure_tools_with_selected(self, tmp_path):
        """run_step_3_tool_configuration() should call configure_tools with selected tool IDs."""
        from aurora_cli.commands.init import run_step_3_tool_configuration
        from unittest.mock import AsyncMock

        selected_tools = ["claude", "universal-agents.md"]

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=selected_tools):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=(["Claude Code", "Universal"], [])) as mock_configure:
                    run_step_3_tool_configuration(tmp_path)

                    # Should call configure_tools with project_path and selected tools
                    mock_configure.assert_called_once_with(tmp_path, selected_tools)

    def test_run_step_3_returns_created_and_updated_lists(self, tmp_path):
        """run_step_3_tool_configuration() should return tuple of (created, updated) tool names."""
        from aurora_cli.commands.init import run_step_3_tool_configuration
        from unittest.mock import AsyncMock

        created = ["Claude Code", "Universal AGENTS.md"]
        updated = ["OpenCode"]

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=["claude", "opencode", "universal-agents.md"]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=(created, updated)):
                    result = run_step_3_tool_configuration(tmp_path)

                    # Should return the tuple from configure_tools
                    assert result == (created, updated)

    def test_run_step_3_tracks_created_vs_updated(self, tmp_path):
        """run_step_3_tool_configuration() should distinguish between created and updated tools."""
        from aurora_cli.commands.init import run_step_3_tool_configuration
        from unittest.mock import AsyncMock

        # Simulate: claude already exists, universal is new
        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={"claude": True, "universal-agents.md": False}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=["claude", "universal-agents.md"]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=(["Universal AGENTS.md"], ["Claude Code"])):
                    created, updated = run_step_3_tool_configuration(tmp_path)

                    # Should track separately
                    assert len(created) == 1
                    assert len(updated) == 1

    def test_run_step_3_shows_success_message(self, tmp_path):
        """run_step_3_tool_configuration() should display success message with counts."""
        from aurora_cli.commands.init import run_step_3_tool_configuration
        from unittest.mock import AsyncMock

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=["claude"]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=(["Claude Code"], [])):
                    with patch("aurora_cli.commands.init.console") as mock_console:
                        run_step_3_tool_configuration(tmp_path)

                        # Should print success message
                        print_calls = [str(call) for call in mock_console.print.call_args_list]
                        combined = " ".join(print_calls)

                        # Should mention tools/configuration
                        assert any("tool" in call.lower() or "config" in call.lower() for call in print_calls)

    def test_run_step_3_handles_no_tools_selected(self, tmp_path):
        """run_step_3_tool_configuration() should handle case when user selects no tools."""
        from aurora_cli.commands.init import run_step_3_tool_configuration
        from unittest.mock import AsyncMock

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=[]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=([], [])):
                    created, updated = run_step_3_tool_configuration(tmp_path)

                    # Should return empty lists
                    assert created == []
                    assert updated == []

    def test_run_step_3_preserves_markers_on_update(self, tmp_path):
        """run_step_3_tool_configuration() should preserve custom content in marker blocks on update."""
        # This test verifies that configure_tools is called correctly
        # The actual marker preservation is tested in configurator tests
        from aurora_cli.commands.init import run_step_3_tool_configuration
        from unittest.mock import AsyncMock

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={"claude": True}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=["claude"]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=([], ["Claude Code"])) as mock_configure:
                    run_step_3_tool_configuration(tmp_path)

                    # Should call configure_tools (which handles marker preservation)
                    mock_configure.assert_called_once()

    def test_run_step_3_shows_step_header(self, tmp_path):
        """run_step_3_tool_configuration() should display 'Step 3/3' header."""
        from aurora_cli.commands.init import run_step_3_tool_configuration
        from unittest.mock import AsyncMock

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=[]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=([], [])):
                    with patch("aurora_cli.commands.init.console") as mock_console:
                        run_step_3_tool_configuration(tmp_path)

                        # Should show step header
                        print_calls = [str(call) for call in mock_console.print.call_args_list]
                        combined = " ".join(print_calls)
                        assert "step 3" in combined.lower() or "3/3" in combined.lower()
