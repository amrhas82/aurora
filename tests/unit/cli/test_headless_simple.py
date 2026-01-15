"""Tests for simplified headless command (pipe-to-CLI approach)."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.headless import headless_command


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_prompt(tmp_path):
    """Create temporary prompt file."""
    prompt = tmp_path / "prompt.md"
    prompt.write_text("# Goal\nTest task\n\n# Success Criteria\n- [ ] Works")
    return prompt


class TestHeadlessValidation:
    """Test validation (prompt exists, tool exists, git safety)."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_missing_prompt_fails(self, mock_which, runner):
        """Test that missing prompt file causes failure."""
        result = runner.invoke(headless_command, ["/nonexistent/prompt.md"])

        assert result.exit_code != 0
        assert "does not exist" in result.output

    @patch("shutil.which", return_value=None)
    def test_missing_tool_fails(self, mock_which, runner, temp_prompt):
        """Test that missing tool causes failure."""
        result = runner.invoke(headless_command, [str(temp_prompt)])

        assert result.exit_code != 0
        assert "not found in PATH" in result.output

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("subprocess.run")
    def test_blocks_main_branch_by_default(self, mock_run, mock_which, runner, temp_prompt):
        """Test that main branch is blocked by default."""
        # Mock git to return main branch
        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "main\n"
        mock_run.return_value = git_mock

        result = runner.invoke(headless_command, [str(temp_prompt)])

        assert result.exit_code != 0
        assert "Cannot run on main/master" in result.output

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_allows_main_with_flag(
        self, mock_cwd, mock_run, mock_which, runner, temp_prompt, tmp_path
    ):
        """Test that --allow-main overrides branch check."""
        mock_cwd.return_value = tmp_path

        # Mock git to return main branch first, then successful tool execution
        call_count = [0]

        def mock_subprocess(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # First call is git check
                mock = Mock()
                mock.returncode = 0
                mock.stdout = "main\n"
                return mock
            else:  # Subsequent calls are tool execution
                mock = Mock()
                mock.returncode = 0
                mock.stdout = "Response"
                return mock

        mock_run.side_effect = mock_subprocess

        result = runner.invoke(
            headless_command, [str(temp_prompt), "--allow-main", "--max-iter", "1"]
        )

        # Should not abort due to branch check
        assert "Cannot run on main/master" not in result.output


class TestHeadlessExecution:
    """Test execution loop and piping."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_single_iteration_success(
        self, mock_cwd, mock_run, mock_which, runner, temp_prompt, tmp_path
    ):
        """Test successful single iteration."""
        mock_cwd.return_value = tmp_path

        # Mock git check to pass
        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "feature\n"

        # Track subprocess calls
        calls = []

        def track_subprocess(*args, **kwargs):
            calls.append(args)
            if "git" in args[0][0]:
                return git_mock
            mock = Mock()
            mock.returncode = 0
            mock.stdout = "Tool response"
            return mock

        mock_run.side_effect = track_subprocess

        result = runner.invoke(headless_command, [str(temp_prompt), "--max-iter", "1"])

        assert result.exit_code == 0
        assert "✓" in result.output

        # Check scratchpad was created
        scratchpad = tmp_path / ".aurora" / "headless" / "scratchpad.md"
        assert scratchpad.exists()
        content = scratchpad.read_text()
        assert "Iteration 1" in content

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_multiple_iterations(
        self, mock_cwd, mock_run, mock_which, runner, temp_prompt, tmp_path
    ):
        """Test multiple iterations loop correctly."""
        mock_cwd.return_value = tmp_path

        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "feature\n"

        iteration_count = [0]

        def track_iterations(*args, **kwargs):
            if "git" in args[0][0]:
                return git_mock
            iteration_count[0] += 1
            mock = Mock()
            mock.returncode = 0
            mock.stdout = f"Response {iteration_count[0]}"
            return mock

        mock_run.side_effect = track_iterations

        result = runner.invoke(headless_command, [str(temp_prompt), "--max-iter", "3"])

        assert result.exit_code == 0
        assert iteration_count[0] == 3

        scratchpad = tmp_path / ".aurora" / "headless" / "scratchpad.md"
        content = scratchpad.read_text()
        assert "Iteration 1" in content
        assert "Iteration 2" in content
        assert "Iteration 3" in content

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_tool_failure_aborts(
        self, mock_cwd, mock_run, mock_which, runner, temp_prompt, tmp_path
    ):
        """Test that tool failure aborts execution."""
        mock_cwd.return_value = tmp_path

        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "feature\n"

        fail_mock = Mock()
        fail_mock.returncode = 1
        fail_mock.stderr = "Tool crashed"

        def mock_subprocess(*args, **kwargs):
            if "git" in args[0][0]:
                return git_mock
            return fail_mock

        mock_run.side_effect = mock_subprocess

        result = runner.invoke(headless_command, [str(temp_prompt), "--max-iter", "3"])

        assert result.exit_code != 0
        assert "Tool failed" in result.output


class TestHeadlessDefaults:
    """Test default behaviors."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_default_prompt_path(self, mock_cwd, mock_run, mock_which, runner, tmp_path):
        """Test that default prompt path is .aurora/headless/prompt.md."""
        mock_cwd.return_value = tmp_path

        # Create default prompt location
        default_prompt = tmp_path / ".aurora" / "headless" / "prompt.md"
        default_prompt.parent.mkdir(parents=True, exist_ok=True)
        default_prompt.write_text("# Goal\nDefault test")

        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "feature\n"

        tool_mock = Mock()
        tool_mock.returncode = 0
        tool_mock.stdout = "Response"

        def mock_subprocess(*args, **kwargs):
            if "git" in args[0][0]:
                return git_mock
            return tool_mock

        mock_run.side_effect = mock_subprocess

        # Run without prompt argument
        result = runner.invoke(headless_command, ["--max-iter", "1"])

        assert result.exit_code == 0

    @patch("subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_default_tool_is_claude(self, mock_cwd, mock_run, runner, temp_prompt, tmp_path):
        """Test that default tool is 'claude'."""
        mock_cwd.return_value = tmp_path

        # Mock shutil.which to track which tool is checked
        checked_tool = []

        def track_which(tool):
            checked_tool.append(tool)
            return f"/usr/bin/{tool}"

        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "feature\n"

        tool_mock = Mock()
        tool_mock.returncode = 0
        tool_mock.stdout = "Response"

        def mock_subprocess(*args, **kwargs):
            if "git" in args[0][0]:
                return git_mock
            return tool_mock

        mock_run.side_effect = mock_subprocess

        with patch("shutil.which", side_effect=track_which):
            # Run without --tool argument
            result = runner.invoke(headless_command, [str(temp_prompt), "--max-iter", "1"])

            assert "claude" in checked_tool

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_default_max_iter_is_10(
        self, mock_cwd, mock_run, mock_which, runner, temp_prompt, tmp_path
    ):
        """Test that default max iterations is 10."""
        mock_cwd.return_value = tmp_path

        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "feature\n"

        iteration_count = [0]

        def count_iterations(*args, **kwargs):
            if "git" in args[0][0]:
                return git_mock
            iteration_count[0] += 1
            mock = Mock()
            mock.returncode = 0
            mock.stdout = "Response"
            return mock

        mock_run.side_effect = count_iterations

        # Run without --max-iter argument
        result = runner.invoke(headless_command, [str(temp_prompt)])

        assert result.exit_code == 0
        assert iteration_count[0] == 10
