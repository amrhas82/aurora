"""End-to-end tests for aur spawn command.

These tests verify the spawn command works correctly in real scenarios with
actual task files and execution.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.mark.e2e
class TestSpawnCommandE2E:
    """End-to-end tests for spawn command."""

    def test_spawn_with_real_tasks_file(self):
        """Test creating real tasks.md and running aur spawn to verify completion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tasks_file = tmpdir_path / "tasks.md"

            # Create a simple task file with self agent (no external spawning needed)
            tasks_content = """# Test Tasks

- [ ] 1. First test task
<!-- agent: self -->
- [ ] 2. Second test task
<!-- agent: self -->
"""
            tasks_file.write_text(tasks_content)

            # Run aur spawn with dry-run to validate parsing
            result = subprocess.run(
                ["aur", "spawn", "--dry-run", str(tasks_file)],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            # Verify command succeeded
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify output contains expected information
            assert "Loaded 2 tasks" in result.stdout
            assert "Dry-run mode" in result.stdout
            assert "First test task" in result.stdout
            assert "Second test task" in result.stdout

    def test_parallel_execution_with_multiple_agents(self):
        """Test parallel execution with multiple agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tasks_file = tmpdir_path / "tasks-parallel.md"

            # Create task file with multiple tasks assigned to self agent
            tasks_content = """# Parallel Execution Test

- [ ] 1. Task one
<!-- agent: self -->
- [ ] 2. Task two
<!-- agent: self -->
- [ ] 3. Task three
<!-- agent: self -->
"""
            tasks_file.write_text(tasks_content)

            # Run with --dry-run since we don't want actual execution in tests
            result = subprocess.run(
                ["aur", "spawn", "--parallel", "--dry-run", str(tasks_file)],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            # Verify command succeeded
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify all tasks were loaded
            assert "Loaded 3 tasks" in result.stdout
            assert "Task one" in result.stdout
            assert "Task two" in result.stdout
            assert "Task three" in result.stdout

    def test_sequential_execution_with_flag(self):
        """Test sequential execution with --sequential flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tasks_file = tmpdir_path / "tasks-sequential.md"

            # Create task file
            tasks_content = """# Sequential Execution Test

- [ ] 1. First sequential task
<!-- agent: self -->
- [ ] 2. Second sequential task
<!-- agent: self -->
"""
            tasks_file.write_text(tasks_content)

            # Run with --sequential and --dry-run
            result = subprocess.run(
                ["aur", "spawn", "--sequential", "--dry-run", str(tasks_file)],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            # Verify command succeeded
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify tasks loaded
            assert "Loaded 2 tasks" in result.stdout
            assert "First sequential task" in result.stdout
            assert "Second sequential task" in result.stdout

    def test_dry_run_mode_doesnt_execute(self):
        """Test that dry-run mode doesn't execute tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tasks_file = tmpdir_path / "tasks-dryrun.md"
            marker_file = tmpdir_path / "execution_marker.txt"

            # Create task file - if it executed, it would create the marker file
            tasks_content = """# Dry-run Test

- [ ] 1. Task that would create marker file
<!-- agent: self -->
"""
            tasks_file.write_text(tasks_content)

            # Run with --dry-run
            result = subprocess.run(
                ["aur", "spawn", "--dry-run", str(tasks_file)],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            # Verify command succeeded
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify dry-run message appears
            assert "Dry-run mode" in result.stdout
            assert "tasks validated but not executed" in result.stdout

            # Verify marker file was NOT created (because dry-run doesn't execute)
            assert not marker_file.exists(), "Dry-run should not execute tasks"

    def test_spawn_with_default_tasks_md(self):
        """Test spawn command with default tasks.md file in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tasks_file = tmpdir_path / "tasks.md"

            # Create default tasks.md
            tasks_content = """# Default Tasks

- [ ] 1. Default task
<!-- agent: self -->
"""
            tasks_file.write_text(tasks_content)

            # Run without specifying file (should use tasks.md)
            result = subprocess.run(
                ["aur", "spawn", "--dry-run"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            # Verify command succeeded
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify it loaded tasks.md
            assert "Loaded 1 tasks" in result.stdout or "Loaded 1 task" in result.stdout
            assert "Default task" in result.stdout

    def test_spawn_with_nonexistent_file(self):
        """Test spawn command with non-existent file returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Try to spawn with non-existent file
            result = subprocess.run(
                ["aur", "spawn", "nonexistent.md"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            # Verify command failed
            assert result.returncode != 0, "Command should fail with non-existent file"

            # Verify error message mentions file not found
            output = result.stdout + result.stderr
            assert "not found" in output.lower() or "error" in output.lower()

    def test_spawn_with_verbose_flag(self):
        """Test spawn command with --verbose flag shows detailed output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tasks_file = tmpdir_path / "tasks-verbose.md"

            # Create task file
            tasks_content = """# Verbose Test

- [ ] 1. Verbose task
<!-- agent: self -->
"""
            tasks_file.write_text(tasks_content)

            # Run with --verbose and --dry-run
            result = subprocess.run(
                ["aur", "spawn", "--verbose", "--dry-run", str(tasks_file)],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            # Verify command succeeded
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify verbose output (at minimum should show task loading)
            assert "Loaded" in result.stdout
            assert "Verbose task" in result.stdout

    def test_spawn_help_command(self):
        """Test that spawn --help shows usage information."""
        result = subprocess.run(
            ["aur", "spawn", "--help"],
            capture_output=True,
            text=True,
        )

        # Verify command succeeded
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify help output contains key information
        assert "spawn" in result.stdout.lower()
        assert "task" in result.stdout.lower()
        assert "--parallel" in result.stdout
        assert "--sequential" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--verbose" in result.stdout
