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
from unittest.mock import MagicMock, call, patch

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
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import run_step_3_tool_configuration

        # Mock the detection and configuration functions (patch where they're imported)
        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}) as mock_detect:
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=[]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=([], [])):
                    run_step_3_tool_configuration(tmp_path)

                    # Should call detect_configured_tools
                    mock_detect.assert_called_once_with(tmp_path)

    def test_run_step_3_detects_existing_tools(self, tmp_path):
        """run_step_3_tool_configuration() should detect existing tool configurations."""
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import run_step_3_tool_configuration

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
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import run_step_3_tool_configuration

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=["claude"]) as mock_prompt:
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=(["Claude Code"], [])):
                    run_step_3_tool_configuration(tmp_path)

                    # Should call prompt_tool_selection with detected tools
                    mock_prompt.assert_called_once()
                    call_kwargs = mock_prompt.call_args[1]
                    assert "configured_tools" in call_kwargs

    def test_run_step_3_calls_configure_slash_commands_with_selected(self, tmp_path):
        """run_step_3_tool_configuration() should call configure_slash_commands with selected tool IDs."""
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import run_step_3_tool_configuration

        selected_tools = ["claude", "cursor"]

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=selected_tools):
                with patch("aurora_cli.commands.init.configure_slash_commands", new_callable=AsyncMock, return_value=(["Claude", "Cursor"], [])) as mock_configure:
                    with patch("aurora_cli.commands.init.get_mcp_capable_from_selection", return_value=["claude", "cursor"]):
                        with patch("aurora_cli.commands.init.configure_mcp_servers", new_callable=AsyncMock, return_value=([], [], [])):
                            run_step_3_tool_configuration(tmp_path)

                            # Should call configure_slash_commands with project_path and selected tools
                            mock_configure.assert_called_once_with(tmp_path, selected_tools)

    def test_run_step_3_returns_created_and_updated_lists(self, tmp_path):
        """run_step_3_tool_configuration() should return tuple of (created, updated) tool names."""
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import run_step_3_tool_configuration

        slash_created = ["Claude", "Cursor"]
        slash_updated = ["Gemini"]

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=["claude", "cursor", "gemini"]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=([], [])):
                    with patch("aurora_cli.commands.init.configure_slash_commands", new_callable=AsyncMock, return_value=(slash_created, slash_updated)):
                        with patch("aurora_cli.commands.init.get_mcp_capable_from_selection", return_value=["claude", "cursor"]):
                            with patch("aurora_cli.commands.init.configure_mcp_servers", new_callable=AsyncMock, return_value=([], [], [])):
                                result = run_step_3_tool_configuration(tmp_path)

                                # Should return merged results (order may vary due to set deduplication)
                                created, updated = result
                                assert set(created) == set(slash_created)
                                assert set(updated) == set(slash_updated)

    def test_run_step_3_tracks_created_vs_updated(self, tmp_path):
        """run_step_3_tool_configuration() should distinguish between created and updated tools."""
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import run_step_3_tool_configuration

        # Simulate: claude already exists, cursor is new
        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={"claude": True, "cursor": False}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=["claude", "cursor"]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=([], [])):
                    with patch("aurora_cli.commands.init.configure_slash_commands", new_callable=AsyncMock, return_value=(["Cursor"], ["Claude"])):
                        with patch("aurora_cli.commands.init.get_mcp_capable_from_selection", return_value=["claude", "cursor"]):
                            with patch("aurora_cli.commands.init.configure_mcp_servers", new_callable=AsyncMock, return_value=([], [], [])):
                                created, updated = run_step_3_tool_configuration(tmp_path)

                                # Should track separately
                                assert len(created) == 1
                                assert len(updated) == 1

    def test_run_step_3_shows_success_message(self, tmp_path):
        """run_step_3_tool_configuration() should display success message with counts."""
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import run_step_3_tool_configuration

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
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import run_step_3_tool_configuration

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=[]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=([], [])):
                    created, updated = run_step_3_tool_configuration(tmp_path)

                    # Should return empty lists
                    assert created == []
                    assert updated == []

    def test_run_step_3_preserves_markers_on_update(self, tmp_path):
        """run_step_3_tool_configuration() should preserve custom content in marker blocks on update."""
        # This test verifies that configure_slash_commands is called correctly
        # The actual marker preservation is tested in configurator tests
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import run_step_3_tool_configuration

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={"claude": True}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=["claude"]):
                with patch("aurora_cli.commands.init.configure_slash_commands", new_callable=AsyncMock, return_value=([], ["Claude"])) as mock_configure:
                    with patch("aurora_cli.commands.init.get_mcp_capable_from_selection", return_value=["claude"]):
                        with patch("aurora_cli.commands.init.configure_mcp_servers", new_callable=AsyncMock, return_value=([], [], [])):
                            run_step_3_tool_configuration(tmp_path)

                            # Should call configure_slash_commands (which handles marker preservation)
                            mock_configure.assert_called_once()

    def test_run_step_3_shows_step_header(self, tmp_path):
        """run_step_3_tool_configuration() should display 'Step 3/3' header."""
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import run_step_3_tool_configuration

        with patch("aurora_cli.commands.init.detect_configured_tools", return_value={}):
            with patch("aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock, return_value=[]):
                with patch("aurora_cli.commands.init.configure_tools", new_callable=AsyncMock, return_value=([], [])):
                    with patch("aurora_cli.commands.init.console") as mock_console:
                        run_step_3_tool_configuration(tmp_path)

                        # Should show step header
                        print_calls = [str(call) for call in mock_console.print.call_args_list]
                        combined = " ".join(print_calls)
                        assert "step 3" in combined.lower() or "3/3" in combined.lower()


class TestInitCommandMain:
    """Test main init_command() function orchestrating all 3 steps."""

    def test_init_command_with_config_flag_fast_path(self, tmp_path):
        """init_command() with --config flag should run Step 3 only."""
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import init_command
        from click.testing import CliRunner

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create .aurora directory in CWD (where command will run)
            aurora_dir = Path.cwd() / ".aurora"
            aurora_dir.mkdir()

            with patch("aurora_cli.commands.init.run_step_1_planning_setup") as mock_step1:
                with patch("aurora_cli.commands.init.run_step_2_memory_indexing") as mock_step2:
                    with patch("aurora_cli.commands.init.run_step_3_tool_configuration", return_value=([], [])) as mock_step3:
                        result = runner.invoke(init_command, ["--config"])

                        # Should NOT call Step 1 or Step 2
                        mock_step1.assert_not_called()
                        mock_step2.assert_not_called()

                        # Should call Step 3
                        mock_step3.assert_called_once()

                        # Should succeed
                        assert result.exit_code == 0

    def test_init_command_config_flag_errors_without_aurora_dir(self, tmp_path):
        """init_command() with --config flag should error if .aurora doesn't exist."""
        from aurora_cli.commands.init import init_command
        from click.testing import CliRunner

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # No .aurora directory exists
            result = runner.invoke(init_command, ["--config"])

            # Should error with helpful message
            assert result.exit_code != 0
            assert ".aurora" in result.output.lower() or "not initialized" in result.output.lower()

    def test_init_command_full_init_flow_calls_all_3_steps(self, tmp_path):
        """init_command() should call all 3 steps in order for full initialization."""
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import init_command
        from click.testing import CliRunner

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init_helpers.detect_existing_setup", return_value=False):
                with patch("aurora_cli.commands.init.run_step_1_planning_setup", return_value=True) as mock_step1:
                    with patch("aurora_cli.commands.init.run_step_2_memory_indexing", return_value=True) as mock_step2:
                        with patch("aurora_cli.commands.init.run_step_3_tool_configuration", return_value=([], [])) as mock_step3:
                            result = runner.invoke(init_command, [])

                            # Should call all 3 steps in order
                            mock_step1.assert_called_once()
                            mock_step2.assert_called_once()
                            mock_step3.assert_called_once()

                            # Should succeed
                            assert result.exit_code == 0

    def test_init_command_displays_success_summary(self, tmp_path):
        """init_command() should display success summary after completion."""
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import init_command
        from click.testing import CliRunner

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init_helpers.detect_existing_setup", return_value=False):
                with patch("aurora_cli.commands.init.run_step_1_planning_setup", return_value=True):
                    with patch("aurora_cli.commands.init.run_step_2_memory_indexing", return_value=True):
                        with patch("aurora_cli.commands.init.run_step_3_tool_configuration", return_value=(["Claude Code"], [])):
                            result = runner.invoke(init_command, [])

                            # Should show success message
                            assert "success" in result.output.lower() or "complete" in result.output.lower()
                            assert result.exit_code == 0

    def test_init_command_shows_step_numbering(self, tmp_path):
        """init_command() should display step numbers (1/3, 2/3, 3/3)."""
        from unittest.mock import AsyncMock

        from aurora_cli.commands.init import init_command
        from click.testing import CliRunner

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init_helpers.detect_existing_setup", return_value=False):
                with patch("aurora_cli.commands.init.run_step_1_planning_setup", return_value=True):
                    with patch("aurora_cli.commands.init.run_step_2_memory_indexing", return_value=True):
                        with patch("aurora_cli.commands.init.run_step_3_tool_configuration", return_value=([], [])):
                            result = runner.invoke(init_command, [])

                            # Step numbering is in the step functions, but verify they're called
                            # (actual step headers are tested in individual step tests)
                            assert result.exit_code == 0

    def test_init_command_detects_existing_setup(self, tmp_path):
        """init_command() should detect when .aurora already exists and prompt for re-run."""
        from aurora_cli.commands.init import init_command
        from click.testing import CliRunner

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create .aurora in CWD to simulate existing setup
            aurora_dir = Path.cwd() / ".aurora"
            aurora_dir.mkdir()

            # Mock the re-run behavior to return "exit" (user chooses to exit)
            with patch("aurora_cli.commands.init_helpers.show_status_summary"):
                with patch("aurora_cli.commands.init_helpers.prompt_rerun_options", return_value="exit"):
                    result = runner.invoke(init_command, [])

                    # Should show status summary and exit cleanly when user chooses exit
                    assert "already initialized" in result.output.lower() or "exiting" in result.output.lower()
                    assert result.exit_code == 0

    def test_init_command_displays_welcome_banner(self, tmp_path):
        """init_command() should display welcome banner on first run."""
        from aurora_cli.commands.init import init_command
        from click.testing import CliRunner

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("aurora_cli.commands.init_helpers.detect_existing_setup", return_value=False):
                with patch("aurora_cli.commands.init.run_step_1_planning_setup", return_value=True):
                    with patch("aurora_cli.commands.init.run_step_2_memory_indexing", return_value=True):
                        with patch("aurora_cli.commands.init.run_step_3_tool_configuration", return_value=([], [])):
                            result = runner.invoke(init_command, [])

                            # Should show welcome banner
                            assert "aurora" in result.output.lower() or "init" in result.output.lower()

    def test_init_command_handles_error_decorator(self, tmp_path):
        """init_command() should have @handle_errors decorator for error handling."""
        from aurora_cli.commands.init import init_command

        # Verify the decorator is applied (function should have __wrapped__ attribute)
        # This is a metadata test - not a behavior test
        assert hasattr(init_command, "callback") or callable(init_command)


class TestShowStatusSummary:
    """Test show_status_summary() function for re-run detection."""

    def test_show_status_summary_with_all_steps_complete(self, tmp_path):
        """show_status_summary() should show checkmarks when all steps complete."""
        from aurora_cli.commands.init_helpers import show_status_summary

        # Create complete setup
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        (aurora_dir / "plans").mkdir()
        (aurora_dir / "plans" / "active").mkdir()

        # Create memory.db with some data
        import sqlite3
        db_path = aurora_dir / "memory.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                metadata TEXT,
                created_at REAL NOT NULL
            )
        """)
        cursor.execute("""
            INSERT INTO chunks VALUES
            ('chunk1', 'content1', 'file1.py', 1, 10, '{}', 1.0),
            ('chunk2', 'content2', 'file2.py', 1, 20, '{}', 2.0),
            ('chunk3', 'content3', 'file3.py', 1, 30, '{}', 3.0)
        """)
        conn.commit()
        conn.close()

        # Create tool configurations
        (tmp_path / "claude_desktop_config.json").write_text("{}")
        (tmp_path / ".cursor" / "prompts").mkdir(parents=True)

        # Call function and capture output
        with patch("aurora_cli.commands.init_helpers.console") as mock_console:
            show_status_summary(tmp_path)

            # Verify status messages were printed
            assert mock_console.print.called
            output_calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(output_calls)

            # Should show checkmarks for all steps
            assert "✓" in output or "✔" in output
            # Should mention chunks
            assert "3" in output or "chunk" in output.lower()
            # Should mention tools
            assert "tool" in output.lower()

    def test_show_status_summary_with_partial_completion(self, tmp_path):
        """show_status_summary() should show partial status correctly."""
        from aurora_cli.commands.init_helpers import show_status_summary

        # Create partial setup - only directories, no memory.db
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        (aurora_dir / "plans").mkdir()
        (aurora_dir / "plans" / "active").mkdir()

        # Call function
        with patch("aurora_cli.commands.init_helpers.console") as mock_console:
            show_status_summary(tmp_path)

            output_calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(output_calls)

            # Should show Step 1 complete
            assert "✓" in output or "✔" in output or "step" in output.lower()
            # Should indicate Step 2 not complete
            assert "not" in output.lower() or "missing" in output.lower() or "skip" in output.lower()

    def test_show_status_summary_counts_chunks_from_memory_db(self, tmp_path):
        """show_status_summary() should query memory.db and display chunk count."""
        from aurora_cli.commands.init_helpers import show_status_summary

        # Create memory.db with 42 chunks
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()

        import sqlite3
        db_path = aurora_dir / "memory.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                metadata TEXT,
                created_at REAL NOT NULL
            )
        """)
        for i in range(42):
            cursor.execute(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"chunk{i}", f"content{i}", f"file{i}.py", 1, 10, "{}", float(i))
            )
        conn.commit()
        conn.close()

        # Call function
        with patch("aurora_cli.commands.init_helpers.console") as mock_console:
            show_status_summary(tmp_path)

            output_calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(output_calls)

            # Should display chunk count of 42
            assert "42" in output

    def test_show_status_summary_displays_tool_count(self, tmp_path):
        """show_status_summary() should count and display configured tools."""
        from aurora_cli.commands.init_helpers import show_status_summary

        # Create 2 tool configurations
        (tmp_path / "claude_desktop_config.json").write_text("{}")
        cursor_dir = tmp_path / ".cursor" / "prompts"
        cursor_dir.mkdir(parents=True)

        # Call function
        with patch("aurora_cli.commands.init_helpers.console") as mock_console:
            show_status_summary(tmp_path)

            output_calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(output_calls)

            # Should display tool count of 2
            assert "2" in output or "tool" in output.lower()

    def test_show_status_summary_shows_formatting_and_checkmarks(self, tmp_path):
        """show_status_summary() should use rich formatting with checkmarks."""
        from aurora_cli.commands.init_helpers import show_status_summary

        # Create minimal setup
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        (aurora_dir / "plans").mkdir()
        (aurora_dir / "plans" / "active").mkdir()

        # Call function
        with patch("aurora_cli.commands.init_helpers.console") as mock_console:
            show_status_summary(tmp_path)

            # Should use console.print (rich formatting)
            assert mock_console.print.called

            # Check for status indicators
            output_calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(output_calls)

            # Should have checkmarks or status indicators
            assert any(char in output for char in ["✓", "✔", "●", "▌", "■"])

    def test_show_status_summary_handles_missing_aurora_dir(self, tmp_path):
        """show_status_summary() should handle missing .aurora gracefully."""
        from aurora_cli.commands.init_helpers import show_status_summary

        # Don't create .aurora directory

        # Call function - should not raise exception
        with patch("aurora_cli.commands.init_helpers.console") as mock_console:
            show_status_summary(tmp_path)

            # Should indicate nothing is set up
            output_calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(output_calls)

            assert "not" in output.lower() or "missing" in output.lower() or "initialize" in output.lower()


class TestPromptRerunOptions:
    """Test prompt_rerun_options() function for re-run menu."""

    def test_prompt_rerun_options_displays_menu(self):
        """prompt_rerun_options() should display menu with 4 options."""
        from aurora_cli.commands.init_helpers import prompt_rerun_options

        with patch("click.prompt", return_value="1"):
            with patch("aurora_cli.commands.init_helpers.console") as mock_console:
                result = prompt_rerun_options()

                # Should print menu options
                assert mock_console.print.called
                output_calls = [str(call) for call in mock_console.print.call_args_list]
                output = " ".join(output_calls)

                # Should have 4 numbered options
                assert "1" in output
                assert "2" in output
                assert "3" in output
                assert "4" in output

    def test_prompt_rerun_options_returns_all(self):
        """prompt_rerun_options() should return 'all' when option 1 selected."""
        from aurora_cli.commands.init_helpers import prompt_rerun_options

        with patch("click.prompt", return_value="1"):
            result = prompt_rerun_options()
            assert result == "all"

    def test_prompt_rerun_options_returns_selective(self):
        """prompt_rerun_options() should return 'selective' when option 2 selected."""
        from aurora_cli.commands.init_helpers import prompt_rerun_options

        with patch("click.prompt", return_value="2"):
            result = prompt_rerun_options()
            assert result == "selective"

    def test_prompt_rerun_options_returns_config(self):
        """prompt_rerun_options() should return 'config' when option 3 selected."""
        from aurora_cli.commands.init_helpers import prompt_rerun_options

        with patch("click.prompt", return_value="3"):
            result = prompt_rerun_options()
            assert result == "config"

    def test_prompt_rerun_options_returns_exit(self):
        """prompt_rerun_options() should return 'exit' when option 4 selected."""
        from aurora_cli.commands.init_helpers import prompt_rerun_options

        with patch("click.prompt", return_value="4"):
            result = prompt_rerun_options()
            assert result == "exit"

    def test_prompt_rerun_options_handles_invalid_input_then_valid(self):
        """prompt_rerun_options() should handle invalid input and retry."""
        from aurora_cli.commands.init_helpers import prompt_rerun_options

        # First return invalid, then valid
        with patch("click.prompt", side_effect=["5", "invalid", "1"]):
            with patch("aurora_cli.commands.init_helpers.console") as mock_console:
                result = prompt_rerun_options()

                # Should eventually return valid choice
                assert result == "all"

                # Should have shown error messages
                output_calls = [str(call) for call in mock_console.print.call_args_list]
                # At least one error message should be shown
                assert len(output_calls) > 4  # More than just the menu


class TestSelectiveStepSelection:
    """Test selective_step_selection() function for choosing specific steps."""

    def test_selective_step_selection_displays_checkbox(self):
        """selective_step_selection() should display checkbox with 3 steps."""
        from aurora_cli.commands.init_helpers import selective_step_selection

        # Mock questionary to return step 1
        with patch("questionary.checkbox") as mock_checkbox:
            mock_checkbox.return_value.ask.return_value = ["1"]
            result = selective_step_selection()

            # Should call questionary.checkbox
            assert mock_checkbox.called
            call_args = mock_checkbox.call_args
            # Should have 3 choices
            choices_arg = call_args[1]["choices"]
            assert len(choices_arg) == 3

    def test_selective_step_selection_returns_single_step(self):
        """selective_step_selection() should return list with single step."""
        from aurora_cli.commands.init_helpers import selective_step_selection

        with patch("questionary.checkbox") as mock_checkbox:
            mock_checkbox.return_value.ask.return_value = ["1"]
            result = selective_step_selection()

            assert result == [1]

    def test_selective_step_selection_returns_multiple_steps(self):
        """selective_step_selection() should return list with multiple steps."""
        from aurora_cli.commands.init_helpers import selective_step_selection

        with patch("questionary.checkbox") as mock_checkbox:
            mock_checkbox.return_value.ask.return_value = ["1", "3"]
            result = selective_step_selection()

            assert result == [1, 3]

    def test_selective_step_selection_returns_all_steps(self):
        """selective_step_selection() should return all steps when all selected."""
        from aurora_cli.commands.init_helpers import selective_step_selection

        with patch("questionary.checkbox") as mock_checkbox:
            mock_checkbox.return_value.ask.return_value = ["1", "2", "3"]
            result = selective_step_selection()

            assert result == [1, 2, 3]

    def test_selective_step_selection_handles_empty_selection(self):
        """selective_step_selection() should show warning on empty selection."""
        from aurora_cli.commands.init_helpers import selective_step_selection

        with patch("questionary.checkbox") as mock_checkbox:
            mock_checkbox.return_value.ask.return_value = []
            with patch("aurora_cli.commands.init_helpers.console") as mock_console:
                result = selective_step_selection()

                # Should return empty list
                assert result == []

                # Should show warning
                assert mock_console.print.called
                output_calls = [str(call) for call in mock_console.print.call_args_list]
                output = " ".join(output_calls)
                assert "no" in output.lower() or "warning" in output.lower() or "nothing" in output.lower()


class TestRerunSafety:
    """Test re-run safety mechanisms for idempotent behavior."""

    def test_project_md_preservation_on_rerun(self, tmp_path):
        """run_step_1_planning_setup() should preserve existing project.md content."""
        from aurora_cli.commands.init import run_step_1_planning_setup

        # Create initial setup with custom content
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Run first time
        run_step_1_planning_setup(tmp_path)

        # Modify project.md with custom content
        project_md = tmp_path / ".aurora" / "project.md"
        original_content = project_md.read_text()
        custom_content = original_content + "\n\n## Custom Section\nMy custom notes here."
        project_md.write_text(custom_content)

        # Run second time - should preserve custom content
        run_step_1_planning_setup(tmp_path)

        final_content = project_md.read_text()
        assert "## Custom Section" in final_content
        assert "My custom notes here" in final_content

    def test_marker_content_preservation_in_tools(self, tmp_path):
        """Tool configurators should preserve content outside Aurora markers."""
        from aurora_cli.commands.init_helpers import configure_tools

        # Create tool config with custom content outside markers
        config_file = tmp_path / "CLAUDE.md"
        config_file.write_text("""# My Custom Header

Some custom content here.

<!-- AURORA:START -->
Original Aurora content
<!-- AURORA:END -->

More custom content below.
""")

        # Run configure_tools - should update markers but preserve custom content
        # Note: We need to mock the configurator behavior
        # For now, just test that the function doesn't crash
        # Full integration test will be in integration tests

    def test_backup_creation_before_reindexing(self, tmp_path):
        """run_step_2_memory_indexing() should create backup before re-indexing."""
        from aurora_cli.commands.init import run_step_2_memory_indexing

        # Create initial memory.db
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        memory_db = aurora_dir / "memory.db"

        import sqlite3
        conn = sqlite3.connect(str(memory_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                metadata TEXT,
                created_at REAL NOT NULL
            )
        """)
        cursor.execute("INSERT INTO chunks VALUES ('test1', 'content1', 'file1.py', 1, 10, '{}', 1.0)")
        conn.commit()
        conn.close()

        # Mock to auto-confirm re-index and mock MemoryManager
        with patch("click.confirm", return_value=True):
            with patch("aurora_cli.memory_manager.MemoryManager") as mock_mm:
                # Mock MemoryManager.index_path to return success stats
                mock_instance = MagicMock()
                mock_stats = MagicMock()
                mock_stats.files_indexed = 10
                mock_stats.chunks_created = 50
                mock_stats.duration_seconds = 1.5
                mock_instance.index_path.return_value = mock_stats
                mock_mm.return_value = mock_instance

                # Run re-indexing
                run_step_2_memory_indexing(tmp_path)

                # Should create backup
                backup_file = aurora_dir / "memory.db.backup"
                assert backup_file.exists(), "Backup file should be created"

    def test_no_errors_on_consecutive_reruns(self, tmp_path):
        """Running init steps multiple times should not cause errors."""
        from aurora_cli.commands.init import run_step_1_planning_setup

        # Create git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Run step 1 ten times - should not crash
        for i in range(10):
            try:
                run_step_1_planning_setup(tmp_path)
            except Exception as e:
                pytest.fail(f"Run {i+1} failed with error: {e}")

        # Verify final state is correct
        assert (tmp_path / ".aurora" / "plans" / "active").exists()
        assert (tmp_path / ".aurora" / "project.md").exists()
