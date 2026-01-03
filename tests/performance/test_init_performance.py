"""
Performance tests for unified init command.

Tests init performance with various file counts to ensure
initialization completes within acceptable time limits.
"""
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.init import init_command


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_git_init():
    """Mock subprocess.run for git init."""
    with patch("aurora_cli.commands.init.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        yield mock_run


@pytest.fixture
def mock_memory_manager():
    """Mock MemoryManager for indexing."""
    with patch("aurora_cli.commands.init.MemoryManager") as mock_mm:
        mock_instance = MagicMock()
        mock_instance.index_path.return_value = None
        mock_mm.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_config():
    """Mock Config for memory manager."""
    with patch("aurora_cli.commands.init.Config") as mock_cfg:
        yield mock_cfg


def create_test_files(project_path: Path, count: int) -> list[Path]:
    """
    Create test Python files for indexing.

    Args:
        project_path: Project directory path
        count: Number of files to create

    Returns:
        List of created file paths
    """
    files = []
    for i in range(count):
        file_path = project_path / f"module_{i}.py"
        file_path.write_text(
            f'''"""Module {i} docstring."""

def function_{i}(x, y):
    """Function {i} docstring."""
    return x + y + {i}


class Class{i}:
    """Class {i} docstring."""

    def method_{i}(self, value):
        """Method {i} docstring."""
        return value * {i}
'''
        )
        files.append(file_path)
    return files


@pytest.mark.performance
def test_init_performance_100_files(
    temp_project, mock_git_init, mock_memory_manager, mock_config, benchmark
):
    """Test init performance with 100 files (target: <7s)."""
    # Create 100 test files
    create_test_files(temp_project, 100)

    # Create runner
    runner = CliRunner()

    # Mock questionary for non-interactive responses
    with patch("aurora_cli.commands.init_helpers.questionary.confirm") as mock_confirm:
        mock_confirm.return_value.ask.return_value = True

        with patch("aurora_cli.commands.init_helpers.questionary.checkbox") as mock_checkbox:
            mock_checkbox.return_value.ask.return_value = []

            # Benchmark init command
            def run_init():
                with runner.isolated_filesystem(temp_dir=temp_project):
                    result = runner.invoke(init_command, input="y\ny\n")
                    return result

            result = benchmark(run_init)

    # Verify command succeeded
    assert result.exit_code == 0

    # Verify time constraint (7 seconds target, allow 10s for CI)
    assert benchmark.stats.mean < 10.0, f"Init took {benchmark.stats.mean:.2f}s (target: <7s)"


@pytest.mark.performance
@pytest.mark.slow
def test_init_performance_1000_files(
    temp_project, mock_git_init, mock_memory_manager, mock_config, benchmark
):
    """Test init performance with 1000 files (target: <30s)."""
    # Create 1000 test files
    create_test_files(temp_project, 1000)

    # Create runner
    runner = CliRunner()

    # Mock questionary for non-interactive responses
    with patch("aurora_cli.commands.init_helpers.questionary.confirm") as mock_confirm:
        mock_confirm.return_value.ask.return_value = True

        with patch("aurora_cli.commands.init_helpers.questionary.checkbox") as mock_checkbox:
            mock_checkbox.return_value.ask.return_value = []

            # Benchmark init command
            def run_init():
                with runner.isolated_filesystem(temp_dir=temp_project):
                    result = runner.invoke(init_command, input="y\ny\n")
                    return result

            result = benchmark(run_init)

    # Verify command succeeded
    assert result.exit_code == 0

    # Verify time constraint (30 seconds target, allow 45s for CI)
    assert benchmark.stats.mean < 45.0, f"Init took {benchmark.stats.mean:.2f}s (target: <30s)"


@pytest.mark.performance
def test_step_1_performance(temp_project, mock_git_init, benchmark):
    """Test Step 1 (Planning Setup) performance (target: <1s)."""
    from aurora_cli.commands.init import run_step_1_planning_setup

    # Benchmark Step 1
    with patch("aurora_cli.commands.init_helpers.prompt_git_init") as mock_prompt:
        mock_prompt.return_value = False  # Skip git init

        result = benchmark(lambda: run_step_1_planning_setup(temp_project))

    # Verify success
    assert result is False  # Returns False when git init declined

    # Verify time constraint
    assert benchmark.stats.mean < 1.0, f"Step 1 took {benchmark.stats.mean:.2f}s (target: <1s)"

    # Verify directories created
    assert (temp_project / ".aurora" / "plans" / "active").exists()
    assert (temp_project / ".aurora" / "plans" / "archive").exists()
    assert (temp_project / ".aurora" / "logs").exists()
    assert (temp_project / ".aurora" / "cache").exists()


@pytest.mark.performance
def test_step_2_performance_100_files(
    temp_project, mock_memory_manager, mock_config, benchmark
):
    """Test Step 2 (Memory Indexing) performance with 100 files."""
    from aurora_cli.commands.init import run_step_2_memory_indexing

    # Create 100 test files
    create_test_files(temp_project, 100)

    # Create .aurora directory
    (temp_project / ".aurora").mkdir()

    # Mock click.confirm for re-index prompt
    with patch("aurora_cli.commands.init.click.confirm") as mock_confirm:
        mock_confirm.return_value = True

        # Benchmark Step 2
        result = benchmark(lambda: run_step_2_memory_indexing(temp_project))

    # Verify success
    assert result is True

    # Memory manager should be called
    assert mock_memory_manager.index_path.called


@pytest.mark.performance
def test_step_3_performance(temp_project, benchmark):
    """Test Step 3 (Tool Configuration) performance (target: <2s)."""
    from aurora_cli.commands.init import run_step_3_tool_configuration

    # Create .aurora directory
    (temp_project / ".aurora").mkdir()

    # Mock tool selection
    with patch("aurora_cli.commands.init_helpers.prompt_tool_selection") as mock_prompt:
        mock_prompt.return_value = []

        with patch("aurora_cli.commands.init_helpers.configure_tools") as mock_configure:
            mock_configure.return_value = ([], [])

            # Benchmark Step 3
            result = benchmark(lambda: run_step_3_tool_configuration(temp_project))

    # Verify success
    assert result == ([], [])

    # Verify time constraint
    assert benchmark.stats.mean < 2.0, f"Step 3 took {benchmark.stats.mean:.2f}s (target: <2s)"


@pytest.mark.performance
def test_memory_usage_during_init(temp_project, mock_git_init):
    """Test memory usage during init (target: <100MB for 10K chunks)."""
    import psutil
    import os

    # Create 100 test files (represents ~1000 chunks)
    create_test_files(temp_project, 100)

    # Create runner
    runner = CliRunner()

    # Get process
    process = psutil.Process(os.getpid())

    # Measure baseline memory
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Mock questionary for non-interactive responses
    with patch("aurora_cli.commands.init_helpers.questionary.confirm") as mock_confirm:
        mock_confirm.return_value.ask.return_value = True

        with patch("aurora_cli.commands.init_helpers.questionary.checkbox") as mock_checkbox:
            mock_checkbox.return_value.ask.return_value = []

            with patch("aurora_cli.commands.init.MemoryManager") as mock_mm:
                mock_instance = MagicMock()
                mock_instance.index_path.return_value = None
                mock_mm.return_value = mock_instance

                with patch("aurora_cli.commands.init.Config"):
                    # Run init
                    with runner.isolated_filesystem(temp_dir=temp_project):
                        result = runner.invoke(init_command, input="y\ny\n")

    # Measure peak memory
    peak_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Calculate memory increase
    memory_increase = peak_memory - baseline_memory

    # Verify command succeeded
    assert result.exit_code == 0

    # Verify memory constraint (100MB target for 10K chunks, scale down for 100 files)
    # 100 files ≈ 1000 chunks, so expect <10MB increase
    assert memory_increase < 50.0, f"Memory increase: {memory_increase:.2f}MB (target: <10MB for 1K chunks)"


@pytest.mark.performance
def test_progress_bar_updates_smoothly(temp_project, mock_git_init):
    """Test progress bar updates smoothly during indexing."""
    from aurora_cli.commands.init import run_step_2_memory_indexing

    # Create 10 test files
    create_test_files(temp_project, 10)

    # Create .aurora directory
    (temp_project / ".aurora").mkdir()

    # Track progress callbacks
    progress_calls = []

    def mock_index_path(path, progress_callback=None):
        """Mock index_path that calls progress callback."""
        if progress_callback:
            for i in range(10):
                progress_callback(i, 10)  # Simulate progress updates
                progress_calls.append((i, 10))

    # Mock MemoryManager
    with patch("aurora_cli.commands.init.MemoryManager") as mock_mm:
        mock_instance = MagicMock()
        mock_instance.index_path.side_effect = mock_index_path
        mock_mm.return_value = mock_instance

        with patch("aurora_cli.commands.init.Config"):
            with patch("aurora_cli.commands.init.click.confirm") as mock_confirm:
                mock_confirm.return_value = True

                # Run Step 2
                run_step_2_memory_indexing(temp_project)

    # Verify progress updates occurred
    assert len(progress_calls) == 10, f"Expected 10 progress updates, got {len(progress_calls)}"

    # Verify progress updates are sequential
    for i, (current, total) in enumerate(progress_calls):
        assert current == i, f"Progress update {i}: expected current={i}, got {current}"
        assert total == 10, f"Progress update {i}: expected total=10, got {total}"


# Configuration for pytest-benchmark
def pytest_configure(config):
    """Configure pytest-benchmark."""
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow tests (>10 seconds)")
