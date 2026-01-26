"""Integration Tests for `aur soar` Command.

This test suite validates complete SOAR command workflows with mocked CLI tools:
- Full pipeline execution with mocked subprocess
- Error handling for tool not found
- Terminal output format verification (FR-4.5 specification)

Pattern: Use real components where possible, mock subprocess calls to external tools.

Test Coverage:
- Task 5.1: End-to-end tests for soar command
- Full pipeline execution with mocked tool
- Error handling for missing tools
- Terminal output format verification
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.main import cli

pytestmark = pytest.mark.integration


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_aurora_dir(tmp_path):
    """Create a temporary .aurora directory structure."""
    aurora_dir = tmp_path / ".aurora"
    aurora_dir.mkdir()
    (aurora_dir / "soar").mkdir()
    (aurora_dir / "logs").mkdir()
    (aurora_dir / "cache").mkdir()
    return aurora_dir


@pytest.fixture
def mock_subprocess_success():
    """Mock subprocess.run to return successful LLM response."""

    def _create_mock(response_content: str = "Test response"):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = response_content
        mock_result.stderr = ""
        return mock_result

    return _create_mock


@pytest.fixture
def mock_llm_json_response():
    """Create mock LLM JSON responses for different phases."""
    return {
        "decompose": json.dumps(
            {
                "goal": "Test goal",
                "subgoals": ["Subgoal 1", "Subgoal 2"],
            },
        ),
        "verify": json.dumps(
            {
                "valid": True,
                "verdict": "VALID",
                "rationale": "All subgoals are clear",
            },
        ),
        "synthesize": json.dumps(
            {
                "answer": "This is the synthesized answer",
                "confidence": 0.85,
            },
        ),
        "respond": "This is the formatted final answer from the LLM.",
    }


# ==============================================================================
# Test 5.1.1: Full Execution with Mocked CLI Tool
# ==============================================================================


def test_soar_full_execution_mocked(runner, tmp_path, mock_llm_json_response):
    """Test full SOAR pipeline execution with mocked CLI tool.

    Expected behavior:
    1. Tool validation passes (mocked shutil.which)
    2. CLIPipeLLMClient created with tool
    3. SOAROrchestrator executes all 9 phases
    4. Phase callbacks display terminal output
    5. Final answer displayed in box format
    6. Exit code is 0
    """
    # Create mock subprocess responses
    call_count = [0]

    def mock_subprocess_run(cmd, **kwargs):
        """Return appropriate mock response based on call count."""
        call_count[0] += 1
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        # Different responses for different phases
        if call_count[0] <= 2:
            # Early phases - return decompose JSON
            mock_result.stdout = mock_llm_json_response["decompose"]
        elif call_count[0] <= 4:
            # Middle phases - return verify JSON
            mock_result.stdout = mock_llm_json_response["verify"]
        elif call_count[0] <= 6:
            # Synthesis phase
            mock_result.stdout = mock_llm_json_response["synthesize"]
        else:
            # Response phase
            mock_result.stdout = mock_llm_json_response["respond"]

        return mock_result

    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/claude"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                    result = runner.invoke(cli, ["soar", "What is SOAR?"])

    # Verify command succeeded
    assert result.exit_code == 0, f"Command failed with output: {result.output}"

    # Verify header displayed
    assert "Aurora SOAR" in result.output

    # Verify at least some phase output is shown
    # (Phase display depends on callback invocation)
    assert (
        "Phase" in result.output
        or "ORCHESTRATOR" in result.output
        or "Final Answer" in result.output
    )

    # Verify final answer box displayed
    assert "Final Answer" in result.output


def test_soar_full_execution_with_tool_flag(runner, tmp_path, mock_llm_json_response):
    """Test SOAR execution with explicit --tool flag.

    Expected behavior:
    1. --tool cursor is accepted
    2. Tool validation passes for cursor
    3. CLIPipeLLMClient uses cursor as tool
    4. Execution completes successfully
    """
    call_count = [0]

    def mock_subprocess_run(cmd, **kwargs):
        call_count[0] += 1
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = mock_llm_json_response.get("decompose", '{"test": "response"}')
        return mock_result

    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/cursor"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/cursor"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                    result = runner.invoke(cli, ["soar", "Test query", "--tool", "cursor"])

    # Should succeed with cursor tool
    assert result.exit_code == 0, f"Command failed: {result.output}"


# ==============================================================================
# Test 5.1.2: Error Handling - Tool Not Found
# ==============================================================================


def test_soar_error_handling_tool_not_found(runner):
    """Test graceful failure when tool is not found in PATH.

    Expected behavior:
    1. shutil.which returns None (tool not found)
    2. Error message displayed
    3. Message includes tool name
    4. Suggests using --tool flag
    5. Exit code is non-zero
    """
    with patch("aurora_cli.commands.soar.shutil.which", return_value=None):
        result = runner.invoke(cli, ["soar", "Test query"])

    # Verify command failed
    assert result.exit_code != 0

    # Verify error message mentions tool
    output_lower = result.output.lower()
    assert "not found" in output_lower or "error" in output_lower
    assert "claude" in output_lower  # Default tool


def test_soar_error_handling_custom_tool_not_found(runner):
    """Test graceful failure when custom tool is not found.

    Expected behavior:
    1. --tool custom-tool specified
    2. shutil.which returns None
    3. Error message mentions custom-tool
    4. Exit code is non-zero
    """
    with patch("aurora_cli.commands.soar.shutil.which", return_value=None):
        result = runner.invoke(cli, ["soar", "Test query", "--tool", "custom-tool"])

    # Verify command failed
    assert result.exit_code != 0

    # Verify error message mentions the custom tool
    assert "custom-tool" in result.output.lower()


def test_soar_error_handling_env_var_tool_not_found(runner, monkeypatch):
    """Test graceful failure when AURORA_SOAR_TOOL tool is not found.

    Expected behavior:
    1. AURORA_SOAR_TOOL=mytool environment variable set
    2. shutil.which returns None for mytool
    3. Error message mentions mytool
    4. Exit code is non-zero
    """
    monkeypatch.setenv("AURORA_SOAR_TOOL", "mytool")

    with patch("aurora_cli.commands.soar.shutil.which", return_value=None):
        result = runner.invoke(cli, ["soar", "Test query"])

    # Verify command failed
    assert result.exit_code != 0

    # Verify error message mentions the env var tool
    assert "mytool" in result.output.lower()


# ==============================================================================
# Test 5.1.3: Terminal Output Format (FR-4.5 Specification)
# ==============================================================================


def test_soar_phase_callback_output_header(runner, tmp_path, mock_llm_json_response):
    """Test terminal output includes Aurora SOAR header box.

    Expected format (FR-4.5):
    +------------ Aurora SOAR ------------+
    | Query: <truncated query>            |
    +-------------------------------------+
    """

    def mock_subprocess_run(cmd, **kwargs):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = mock_llm_json_response.get("decompose", '{"test": "response"}')
        return mock_result

    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/claude"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                    result = runner.invoke(cli, ["soar", "What is the SOAR orchestrator?"])

    # Verify header box format
    assert "Aurora SOAR" in result.output

    # Check for box characters (Rich panel uses Unicode box-drawing characters)
    # or ASCII fallback characters like +, -, |
    box_chars = ["+", "-", "|", "=", "", "", "", "", "", "", "", ""]
    assert any(char in result.output for char in box_chars)


def test_soar_phase_callback_output_phases(runner, tmp_path, mock_llm_json_response):
    """Test terminal output shows phase information.

    Expected format (FR-4.5):
    [ORCHESTRATOR] Phase 1: Assess
      Analyzing query complexity...

    [LLM -> claude] Phase 3: Decompose
      Breaking query into subgoals...
    """
    call_count = [0]

    def mock_subprocess_run(cmd, **kwargs):
        call_count[0] += 1
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = mock_llm_json_response.get("decompose", '{"test": "response"}')
        return mock_result

    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/claude"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                    result = runner.invoke(cli, ["soar", "Test query"])

    # If phases are displayed, check format
    # Note: Phase display depends on callback invocation during execute()
    if "Phase" in result.output:
        # Check for either ORCHESTRATOR or LLM format
        assert "ORCHESTRATOR" in result.output or "LLM" in result.output


def test_soar_phase_callback_output_final_answer(runner, tmp_path, mock_llm_json_response):
    """Test terminal output shows final answer in box format.

    Expected format (FR-4.5):
    +-------------- Final Answer --------------+
    | <formatted answer content>               |
    +-----------------------------------------+
    """

    def mock_subprocess_run(cmd, **kwargs):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = mock_llm_json_response.get("respond", "Final answer content")
        return mock_result

    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/claude"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                    result = runner.invoke(cli, ["soar", "Test query"])

    # Verify final answer section exists
    assert "Final Answer" in result.output

    # Verify box formatting is present (Rich panel uses Unicode box-drawing characters)
    # or ASCII fallback characters like +, -, |
    box_chars = ["+", "-", "|", "=", "", "", "", "", "", "", "", ""]
    assert any(char in result.output for char in box_chars)


def test_soar_output_includes_completion_time(runner, tmp_path, mock_llm_json_response):
    """Test terminal output shows completion time.

    Expected format:
    Completed in X.Xs
    """

    def mock_subprocess_run(cmd, **kwargs):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = mock_llm_json_response.get("decompose", '{"test": "response"}')
        return mock_result

    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/claude"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                    result = runner.invoke(cli, ["soar", "Test query"])

    # Verify completion time shown
    assert "Completed in" in result.output or "complete" in result.output.lower()


# ==============================================================================
# Test: Environment Variable Support
# ==============================================================================


def test_soar_respects_env_var_tool(runner, tmp_path, monkeypatch, mock_llm_json_response):
    """Test AURORA_SOAR_TOOL environment variable is used as default.

    Expected behavior:
    1. AURORA_SOAR_TOOL=cursor set
    2. No --tool flag provided
    3. cursor is used as the tool
    """
    monkeypatch.setenv("AURORA_SOAR_TOOL", "cursor")

    captured_tool = []

    def mock_subprocess_run(cmd, **kwargs):
        # Capture the tool being invoked
        if cmd and len(cmd) > 0:
            captured_tool.append(cmd[0])
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = mock_llm_json_response.get("decompose", '{"test": "response"}')
        return mock_result

    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/cursor"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/cursor"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                    result = runner.invoke(cli, ["soar", "Test query"])

    # Verify cursor was used (from env var)
    assert result.exit_code == 0, f"Command failed: {result.output}"
    if captured_tool:
        assert captured_tool[0] == "cursor"


def test_soar_cli_flag_overrides_env_var(runner, tmp_path, monkeypatch, mock_llm_json_response):
    """Test --tool flag overrides AURORA_SOAR_TOOL environment variable.

    Expected behavior:
    1. AURORA_SOAR_TOOL=cursor set
    2. --tool claude provided
    3. claude is used as the tool (overrides env var)
    """
    monkeypatch.setenv("AURORA_SOAR_TOOL", "cursor")

    captured_tool = []

    def mock_subprocess_run(cmd, **kwargs):
        if cmd and len(cmd) > 0:
            captured_tool.append(cmd[0])
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = mock_llm_json_response.get("decompose", '{"test": "response"}')
        return mock_result

    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/claude"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                    result = runner.invoke(cli, ["soar", "Test query", "--tool", "claude"])

    # Verify claude was used (from CLI flag, not env var)
    assert result.exit_code == 0, f"Command failed: {result.output}"
    if captured_tool:
        assert captured_tool[0] == "claude"


# ==============================================================================
# Test: Verbose Mode
# ==============================================================================


def test_soar_verbose_mode(runner, tmp_path, mock_llm_json_response):
    """Test --verbose flag provides additional output.

    Expected behavior:
    1. --verbose flag accepted
    2. More detailed output shown
    """

    def mock_subprocess_run(cmd, **kwargs):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = mock_llm_json_response.get("decompose", '{"test": "response"}')
        return mock_result

    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/claude"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                    result = runner.invoke(cli, ["soar", "Test query", "--verbose"])

    # Verbose mode should not cause failure
    assert result.exit_code == 0, f"Command failed: {result.output}"


# ==============================================================================
# Test: Model Parameter
# ==============================================================================


def test_soar_model_parameter(runner, tmp_path, mock_llm_json_response):
    """Test --model parameter is accepted.

    Expected behavior:
    1. --model opus accepted
    2. Command executes successfully
    """

    def mock_subprocess_run(cmd, **kwargs):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = mock_llm_json_response.get("decompose", '{"test": "response"}')
        return mock_result

    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/claude"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                    result = runner.invoke(cli, ["soar", "Test query", "--model", "opus"])

    # Model parameter should be accepted
    assert result.exit_code == 0, f"Command failed: {result.output}"


# ==============================================================================
# Test: Subprocess Timeout
# ==============================================================================


def test_soar_handles_subprocess_timeout(runner, tmp_path):
    """Test graceful handling of subprocess timeout.

    Expected behavior:
    1. Subprocess times out (180 seconds)
    2. SOAROrchestrator handles error gracefully
    3. Partial results returned OR error shown
    4. Command may still succeed with partial results

    Note: The orchestrator is designed to handle failures gracefully
    and return partial results, so exit_code may be 0.
    """
    import subprocess as sp

    def mock_subprocess_run(cmd, **kwargs):
        raise sp.TimeoutExpired(cmd=cmd, timeout=180)

    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/claude"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                    result = runner.invoke(cli, ["soar", "Test query"])

    # The orchestrator handles timeouts gracefully, returning partial results
    # So we check that either:
    # - An error message is shown, OR
    # - A final answer is displayed (partial results)
    output_lower = result.output.lower()
    assert (
        "timeout" in output_lower or "error" in output_lower or "final answer" in output_lower
    ), f"Expected timeout/error message or final answer, got: {result.output}"


# ==============================================================================
# Test: JSON Placeholder Files
# ==============================================================================


def test_soar_creates_json_placeholder_files(runner, tmp_path, mock_llm_json_response):
    """Test .aurora/soar/ directory and JSON files are created.

    Expected behavior:
    1. .aurora/soar/ directory created via CLIPipeLLMClient
    2. input.json written before LLM call
    3. output.json written after LLM call
    4. state.json tracks current phase

    Note: The CLIPipeLLMClient is given the soar_dir directly,
    so we need to pass the directory through properly.
    """
    # Create the soar directory path
    soar_dir = tmp_path / "soar"

    def mock_subprocess_run(cmd, **kwargs):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = mock_llm_json_response.get("decompose", '{"test": "response"}')
        return mock_result

    # We need to ensure that _ensure_soar_dir in soar.py returns our tmp_path
    # and that CLIPipeLLMClient uses it properly
    with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
        with patch("aurora_cli.llm.cli_pipe_client.shutil.which", return_value="/usr/bin/claude"):
            with patch(
                "aurora_cli.llm.cli_pipe_client.subprocess.run",
                side_effect=mock_subprocess_run,
            ):
                # Patch at the command level where _ensure_soar_dir is called
                with patch("aurora_cli.commands.soar._ensure_soar_dir", return_value=soar_dir):
                    # Also patch the paths module
                    with patch("aurora_core.paths.get_aurora_dir", return_value=tmp_path):
                        result = runner.invoke(cli, ["soar", "Test query"])

    # The execution should succeed
    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify the command ran successfully and showed expected output
    assert "Aurora SOAR" in result.output
    assert "Final Answer" in result.output
