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

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    def test_missing_prompt_fails(self, mock_which, runner):
        """Test that missing prompt file causes failure."""
        # Note: -p with non-existent file will fail at click validation level
        result = runner.invoke(headless_command, ["-p", "/nonexistent/prompt.md"])

        assert result.exit_code != 0
        # Click will say the path doesn't exist
        assert "does not exist" in result.output or "Invalid value" in result.output

    @patch("aurora_cli.commands.headless.shutil.which", return_value=None)
    def test_missing_tool_fails(self, mock_which, runner, temp_prompt):
        """Test that missing tool causes failure."""
        result = runner.invoke(headless_command, ["-p", str(temp_prompt), "-t", "fake_tool"])

        assert result.exit_code != 0
        assert "not found in PATH" in result.output

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    @patch("aurora_cli.commands.headless.subprocess.run")
    def test_blocks_main_branch_by_default(self, mock_run, mock_which, runner, temp_prompt):
        """Test that main branch is blocked by default."""
        # Mock git to return main branch
        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "main\n"
        mock_run.return_value = git_mock

        result = runner.invoke(headless_command, ["-p", str(temp_prompt), "-t", "claude"])

        assert result.exit_code != 0
        assert "Cannot run on main/master" in result.output

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    @patch("aurora_cli.commands.headless.subprocess.run")
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
            headless_command, ["-p", str(temp_prompt), "--allow-main", "--max", "1"]
        )

        # Should not abort due to branch check
        assert "Cannot run on main/master" not in result.output


class TestHeadlessExecution:
    """Test execution loop and piping."""

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    @patch("aurora_cli.commands.headless.subprocess.run")
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

        result = runner.invoke(headless_command, ["-p", str(temp_prompt), "--max", "1"])

        assert result.exit_code == 0

        # Check scratchpad was created
        scratchpad = tmp_path / ".aurora" / "headless" / "scratchpad.md"
        assert scratchpad.exists()

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    @patch("aurora_cli.commands.headless.subprocess.run")
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

        result = runner.invoke(headless_command, ["-p", str(temp_prompt), "--max", "3"])

        assert result.exit_code == 0
        assert iteration_count[0] == 3

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    @patch("aurora_cli.commands.headless.subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_tool_failure_warns(
        self, mock_cwd, mock_run, mock_which, runner, temp_prompt, tmp_path
    ):
        """Test that tool failure shows warning but continues."""
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

        result = runner.invoke(headless_command, ["-p", str(temp_prompt), "--max", "1"])

        # Tool failure shows warning but doesn't abort
        assert "Warning" in result.output or "exited with code" in result.output


class TestHeadlessDefaults:
    """Test default behaviors."""

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    @patch("aurora_cli.commands.headless.subprocess.run")
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
        tool_mock.stderr = ""

        def mock_subprocess(*args, **kwargs):
            if "git" in args[0][0]:
                return git_mock
            return tool_mock

        mock_run.side_effect = mock_subprocess

        # Run without prompt argument (uses default path)
        result = runner.invoke(headless_command, ["--max", "1"])

        assert result.exit_code == 0

    @patch("aurora_cli.commands.headless.subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_default_tool_is_claude(self, mock_cwd, mock_run, runner, temp_prompt, tmp_path):
        """Test that default tool is 'claude' from config."""
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
        tool_mock.stderr = ""

        def mock_subprocess(*args, **kwargs):
            if "git" in args[0][0]:
                return git_mock
            return tool_mock

        mock_run.side_effect = mock_subprocess

        with patch("aurora_cli.commands.headless.shutil.which", side_effect=track_which):
            # Run without --tool argument (uses config default of claude)
            result = runner.invoke(headless_command, ["-p", str(temp_prompt), "--max", "1"])

            assert "claude" in checked_tool

    @patch("aurora_cli.commands.headless.shutil.which", return_value="/usr/bin/claude")
    @patch("aurora_cli.commands.headless.subprocess.run")
    @patch("pathlib.Path.cwd")
    def test_default_max_iter_is_10(
        self, mock_cwd, mock_run, mock_which, runner, temp_prompt, tmp_path
    ):
        """Test that default max iterations is 10 (from config)."""
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
            mock.stderr = ""
            return mock

        mock_run.side_effect = count_iterations

        # Run without --max argument (uses config default of 10)
        result = runner.invoke(headless_command, ["-p", str(temp_prompt)])

        assert result.exit_code == 0
        assert iteration_count[0] == 10
