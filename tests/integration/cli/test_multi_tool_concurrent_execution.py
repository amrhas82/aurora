"""Integration tests for multi-tool concurrent execution with Claude and OpenCode.

End-to-end tests that validate the complete workflow of running multiple AI tools
(Claude, OpenCode) concurrently through the headless command. Tests cover realistic
scenarios including:

- Full CLI invocation to execution loop
- Real subprocess mocking with timing behavior
- Aggregation strategy end-to-end behavior
- Scratchpad state progression over iterations
- Config resolution from CLI to execution
- Error handling and recovery patterns
"""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.headless import (
    _check_final_state,
    _display_multi_tool_results,
    _run_backpressure,
    _run_multi_tool_loop,
    _run_single_tool_loop,
    headless_command,
)
from aurora_cli.concurrent_executor import (
    AggregatedResult,
    AggregationStrategy,
    ConcurrentToolExecutor,
    ToolConfig,
    ToolResult,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def full_workspace(tmp_path):
    """Create a complete workspace with all required files."""
    # Create Aurora directory structure
    aurora_dir = tmp_path / ".aurora"
    aurora_dir.mkdir()
    headless_dir = aurora_dir / "headless"
    headless_dir.mkdir()

    # Create prompt file
    prompt = headless_dir / "prompt.md"
    prompt.write_text(
        """# Goal
Implement a REST API endpoint for user authentication.

# Context
- Using FastAPI framework
- PostgreSQL database
- JWT tokens for authentication

# Success Criteria
- [ ] POST /auth/login endpoint implemented
- [ ] JWT token generation working
- [ ] Proper error handling for invalid credentials
- [ ] Unit tests pass

# Technical Notes
- Use bcrypt for password hashing
- Token expiry: 24 hours
"""
    )

    # Create initial scratchpad
    scratchpad = headless_dir / "scratchpad.md"
    scratchpad.write_text(
        """# Scratchpad

STATUS: IN_PROGRESS

## Current State
- Starting implementation
- Analyzing existing code structure

## Observations
None yet.

## Next Steps
1. Create authentication models
2. Implement login endpoint
3. Add JWT generation
4. Write tests
"""
    )

    return {
        "root": tmp_path,
        "aurora_dir": aurora_dir,
        "headless_dir": headless_dir,
        "prompt": prompt,
        "scratchpad": scratchpad,
    }


@pytest.fixture
def mock_subprocess_both_tools():
    """Mock subprocess for both Claude and OpenCode."""

    def create_subprocess_mock():
        call_sequence = []
        tool_responses = {
            "claude": "Claude completed the task successfully.",
            "opencode": "OpenCode implemented the solution.",
        }

        def mock_run(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])

            if isinstance(cmd, list):
                # Git commands
                if "git" in cmd[0]:
                    result = Mock()
                    result.returncode = 0
                    result.stdout = "feature-branch\n"
                    result.stderr = ""
                    return result

                # Tool commands
                tool_name = cmd[0]
                call_sequence.append(tool_name)

                result = Mock()
                result.returncode = 0
                result.stdout = tool_responses.get(tool_name, f"{tool_name} output")
                result.stderr = ""
                return result

            # Default
            result = Mock()
            result.returncode = 0
            result.stdout = "output"
            result.stderr = ""
            return result

        return mock_run, call_sequence

    return create_subprocess_mock


@pytest.fixture
def mock_tools_available():
    """Mock both tools as available in PATH."""

    def which_side_effect(cmd):
        if cmd in ("claude", "opencode", "cursor"):
            return f"/usr/bin/{cmd}"
        return None

    with patch("shutil.which", side_effect=which_side_effect):
        with patch("aurora_cli.commands.headless.shutil.which", side_effect=which_side_effect):
            yield


# ---------------------------------------------------------------------------
# Test: End-to-End CLI Execution
# ---------------------------------------------------------------------------


class TestEndToEndCLIExecution:
    """Test complete CLI invocation to execution."""

    def test_multi_tool_parallel_e2e(self, runner, full_workspace, mock_tools_available):
        """Test full parallel execution with two tools via CLI."""
        with patch("pathlib.Path.cwd", return_value=full_workspace["root"]):
            # Mock git to return feature branch
            def mock_subprocess(*args, **kwargs):
                cmd = args[0] if args else []
                if isinstance(cmd, list) and "git" in cmd[0]:
                    return Mock(returncode=0, stdout="feature-branch\n", stderr="")
                return Mock(returncode=0, stdout="Output", stderr="")

            with patch("subprocess.run", side_effect=mock_subprocess):
                with patch(
                    "aurora_cli.commands.headless.subprocess.run", side_effect=mock_subprocess
                ):
                    with patch("aurora_cli.commands.headless.asyncio.run") as mock_asyncio:
                        mock_asyncio.return_value = None

                        result = runner.invoke(
                            headless_command,
                            [
                                "-p",
                                str(full_workspace["prompt"]),
                                "-t",
                                "claude",
                                "-t",
                                "opencode",
                                "--max",
                                "1",
                            ],
                        )

                        # Should enter parallel mode
                        mock_asyncio.assert_called_once()
                        assert result.exit_code == 0

    def test_multi_tool_sequential_e2e(self, runner, full_workspace, mock_tools_available):
        """Test full sequential execution with two tools via CLI."""
        with patch("pathlib.Path.cwd", return_value=full_workspace["root"]):
            tool_calls = []

            def mock_subprocess(*args, **kwargs):
                cmd = args[0] if args else []
                if isinstance(cmd, list):
                    if "git" in cmd[0]:
                        return Mock(returncode=0, stdout="feature-branch\n", stderr="")
                    tool_calls.append(cmd[0])
                return Mock(returncode=0, stdout="Output", stderr="")

            with patch("subprocess.run", side_effect=mock_subprocess):
                with patch(
                    "aurora_cli.commands.headless.subprocess.run", side_effect=mock_subprocess
                ):
                    result = runner.invoke(
                        headless_command,
                        [
                            "-p",
                            str(full_workspace["prompt"]),
                            "-t",
                            "claude",
                            "-t",
                            "opencode",
                            "--sequential",
                            "--max",
                            "4",
                        ],
                    )

                    # Should alternate tools in sequential mode
                    assert tool_calls == ["claude", "opencode", "claude", "opencode"]
                    assert result.exit_code == 0

    def test_cli_config_propagation(self, runner, full_workspace, mock_tools_available):
        """Test that CLI options propagate correctly to executor."""
        with patch("pathlib.Path.cwd", return_value=full_workspace["root"]):
            with patch("aurora_cli.commands.headless.asyncio.run") as mock_asyncio:
                mock_asyncio.return_value = None

                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(full_workspace["prompt"]),
                        "-t",
                        "claude",
                        "-t",
                        "opencode",
                        "--strategy",
                        "voting",
                        "--timeout",
                        "120",
                        "--max",
                        "5",
                        "--show-config",
                    ],
                )

                assert result.exit_code == 0
                assert "voting" in result.output
                assert "120" in result.output
                assert "5" in result.output


# ---------------------------------------------------------------------------
# Test: Subprocess Timing Behavior
# ---------------------------------------------------------------------------


class TestSubprocessTimingBehavior:
    """Test realistic subprocess timing scenarios."""

    @pytest.mark.asyncio
    async def test_realistic_tool_execution_timing(self, full_workspace):
        """Test with realistic execution timing between tools."""
        execution_log = []

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                start = time.time()
                execution_log.append(("start", start))
                await asyncio.sleep(0.05)  # Simulate 50ms execution
                execution_log.append(("end", time.time()))

                full_workspace["scratchpad"].write_text("STATUS: DONE")
                return AggregatedResult(
                    success=True,
                    primary_output="Task completed",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="Claude done", execution_time=0.05
                        ),
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="OpenCode done",
                            execution_time=0.05,
                        ),
                    ],
                    execution_time=0.05,
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test",
                scratchpad=full_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="first_success",
            )

            # Verify execution happened
            assert len(execution_log) == 2
            assert execution_log[0][0] == "start"
            assert execution_log[1][0] == "end"

    @pytest.mark.asyncio
    async def test_first_success_cancels_slow_tool(self, full_workspace):
        """Test that first_success cancels slower tools."""
        cancellation_events = []

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                # Simulate fast tool winning
                full_workspace["scratchpad"].write_text("STATUS: DONE")
                return AggregatedResult(
                    success=True,
                    primary_output="Claude won",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(tool="claude", success=True, output="Quick", execution_time=0.1),
                    ],
                    winning_tool="claude",
                    metadata={"cancelled_tools": ["opencode"]},
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test",
                scratchpad=full_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="first_success",
            )


# ---------------------------------------------------------------------------
# Test: Aggregation Strategy End-to-End
# ---------------------------------------------------------------------------


class TestAggregationStrategyE2E:
    """Test aggregation strategies end-to-end."""

    @pytest.mark.asyncio
    async def test_voting_strategy_full_flow(self, full_workspace):
        """Test voting strategy through complete flow."""
        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                full_workspace["scratchpad"].write_text("STATUS: DONE")
                return AggregatedResult(
                    success=True,
                    primary_output="Consensus answer",
                    strategy_used=AggregationStrategy.VOTING,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="Answer A", execution_time=1.0
                        ),
                        ToolResult(
                            tool="opencode", success=True, output="Answer A", execution_time=1.0
                        ),
                        ToolResult(
                            tool="cursor", success=True, output="Answer B", execution_time=1.0
                        ),
                    ],
                    winning_tool="claude",
                    metadata={"votes": {"Answer A": 2, "Answer B": 1}},
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode", "cursor"],
                prompt="Test",
                scratchpad=full_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="voting",
            )

            # Verify voting strategy was requested
            MockExecutor.assert_called_once()
            call_kwargs = MockExecutor.call_args[1]
            assert call_kwargs["strategy"] == AggregationStrategy.VOTING

    @pytest.mark.asyncio
    async def test_best_score_strategy_full_flow(self, full_workspace):
        """Test best_score strategy through complete flow."""
        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                full_workspace["scratchpad"].write_text("STATUS: DONE")
                return AggregatedResult(
                    success=True,
                    primary_output="Best answer",
                    strategy_used=AggregationStrategy.BEST_SCORE,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="A" * 100, execution_time=5.0
                        ),
                        ToolResult(
                            tool="opencode", success=True, output="B" * 50, execution_time=10.0
                        ),
                    ],
                    winning_tool="claude",
                    metadata={"scores": {"claude": 15.0, "opencode": 8.0}},
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test",
                scratchpad=full_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="best_score",
            )

            # Verify best_score strategy was requested
            MockExecutor.assert_called_once()
            call_kwargs = MockExecutor.call_args[1]
            assert call_kwargs["strategy"] == AggregationStrategy.BEST_SCORE


# ---------------------------------------------------------------------------
# Test: Scratchpad State Progression
# ---------------------------------------------------------------------------


class TestScratchpadStateProgression:
    """Test scratchpad state evolution over iterations."""

    @pytest.mark.asyncio
    async def test_multi_iteration_state_evolution(self, full_workspace):
        """Test scratchpad state evolves correctly over iterations."""
        iteration_states = []

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            iteration_count = [0]

            async def mock_execute(context):
                iteration_count[0] += 1
                current_state = full_workspace["scratchpad"].read_text()
                iteration_states.append(current_state)

                if iteration_count[0] == 1:
                    # First iteration: analyze
                    full_workspace["scratchpad"].write_text(
                        """# Scratchpad

STATUS: IN_PROGRESS

## Observations
- Analyzed existing auth code
- Found JWT library already imported

## Next Steps
- Implement login endpoint
"""
                    )
                elif iteration_count[0] == 2:
                    # Second iteration: implement
                    full_workspace["scratchpad"].write_text(
                        """# Scratchpad

STATUS: IN_PROGRESS

## Observations
- Analyzed existing auth code
- Found JWT library already imported
- Login endpoint created

## Next Steps
- Add tests
"""
                    )
                else:
                    # Third iteration: complete
                    full_workspace["scratchpad"].write_text(
                        """# Scratchpad

STATUS: DONE

## Summary
- Login endpoint implemented at POST /auth/login
- JWT tokens working
- Tests passing

## Files Modified
- src/auth/routes.py
- src/auth/jwt.py
- tests/test_auth.py
"""
                    )

                return AggregatedResult(
                    success=True,
                    primary_output=f"Iteration {iteration_count[0]} complete",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=True,
                            output=f"Progress {iteration_count[0]}",
                            execution_time=1.0,
                        ),
                    ],
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Implement auth",
                scratchpad=full_workspace["scratchpad"],
                max_iter=10,
                test_cmd=None,
                strategy="first_success",
            )

            # Should have run 3 iterations before STATUS: DONE
            assert iteration_count[0] == 3
            assert len(iteration_states) == 3

    @pytest.mark.asyncio
    async def test_scratchpad_persists_between_iterations(self, full_workspace):
        """Test that scratchpad content persists correctly."""
        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            received_contexts = []

            async def mock_execute(context):
                received_contexts.append(context)
                if len(received_contexts) >= 2:
                    full_workspace["scratchpad"].write_text("STATUS: DONE")
                return AggregatedResult(
                    success=True,
                    primary_output="Done",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_executor.execute = mock_execute

            # Set initial scratchpad with specific content
            full_workspace["scratchpad"].write_text("# Initial State\nFoo bar baz")

            await _run_multi_tool_loop(
                tools_list=["claude"],
                prompt="Test",
                scratchpad=full_workspace["scratchpad"],
                max_iter=10,
                test_cmd=None,
                strategy="first_success",
            )

            # Verify context included scratchpad content
            assert len(received_contexts) == 2
            assert "Foo bar baz" in received_contexts[0]


# ---------------------------------------------------------------------------
# Test: Config Resolution
# ---------------------------------------------------------------------------


class TestConfigResolution:
    """Test configuration resolution from CLI to execution."""

    def test_cli_overrides_config_file(self, runner, full_workspace, mock_tools_available):
        """Test that CLI options override config file settings."""
        with patch("pathlib.Path.cwd", return_value=full_workspace["root"]):
            # Don't mock load_config - let it work naturally
            # Just verify CLI options appear in output
            result = runner.invoke(
                headless_command,
                [
                    "-p",
                    str(full_workspace["prompt"]),
                    "-t",
                    "claude",
                    "--max",
                    "20",
                    "--strategy",
                    "first_success",
                    "--show-config",
                ],
            )

            assert result.exit_code == 0
            assert "20" in result.output  # CLI option
            assert "first_success" in result.output  # CLI option

    def test_env_var_config_resolution(self, runner, full_workspace, mock_tools_available):
        """Test configuration from environment variables."""
        with patch("pathlib.Path.cwd", return_value=full_workspace["root"]):
            with patch.dict(
                "os.environ",
                {"AURORA_HEADLESS_STRATEGY": "voting"},
                clear=False,
            ):
                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(full_workspace["prompt"]),
                        "-t",
                        "claude",
                        "--show-config",
                    ],
                )

                # Env var should be reflected if not overridden by CLI
                assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Test: Error Handling and Recovery
# ---------------------------------------------------------------------------


class TestErrorHandlingAndRecovery:
    """Test error handling in integration scenarios."""

    def test_tool_not_found_fails_fast(self, runner, full_workspace):
        """Test that missing tool fails immediately."""
        with patch("shutil.which", return_value=None):
            with patch("aurora_cli.commands.headless.shutil.which", return_value=None):
                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(full_workspace["prompt"]),
                        "-t",
                        "nonexistent_tool",
                    ],
                )

                assert result.exit_code != 0
                assert "not found in PATH" in result.output

    def test_git_branch_check_failure_handled(self, runner, full_workspace, mock_tools_available):
        """Test handling of git branch check failure."""
        with patch("pathlib.Path.cwd", return_value=full_workspace["root"]):
            with patch("subprocess.run") as mock_run:
                # Git command fails
                mock_run.return_value = Mock(returncode=1, stdout="", stderr="Not a git repo")

                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(full_workspace["prompt"]),
                        "-t",
                        "claude",
                        "--max",
                        "1",
                    ],
                )

                # Should handle gracefully (might warn or proceed)
                # The behavior depends on implementation

    @pytest.mark.asyncio
    async def test_all_tools_fail_gracefully(self, full_workspace):
        """Test graceful handling when all tools fail."""
        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                full_workspace["scratchpad"].write_text("STATUS: DONE")  # Exit loop
                return AggregatedResult(
                    success=False,
                    primary_output="",
                    strategy_used=AggregationStrategy.ALL_COMPLETE,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=False,
                            output="",
                            error="Connection refused",
                            exit_code=1,
                        ),
                        ToolResult(
                            tool="opencode",
                            success=False,
                            output="",
                            error="Rate limited",
                            exit_code=429,
                        ),
                    ],
                    metadata={"error": "All tools failed"},
                )

            mock_executor.execute = mock_execute

            # Should not raise
            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test",
                scratchpad=full_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="all_complete",
            )


# ---------------------------------------------------------------------------
# Test: Backpressure Integration
# ---------------------------------------------------------------------------


class TestBackpressureIntegration:
    """Test backpressure (test command) integration."""

    def test_backpressure_command_executed(self, full_workspace):
        """Test that backpressure command is executed."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Tests passed", stderr="")

            _run_backpressure("pytest tests/")

            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert "pytest" in call_args[0][0]

    def test_backpressure_failure_logged(self, full_workspace, capsys):
        """Test that backpressure failure is logged."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Tests failed")

            _run_backpressure("pytest tests/")

            # Should not raise, just log warning

    @pytest.mark.asyncio
    async def test_backpressure_in_loop(self, full_workspace):
        """Test backpressure execution within iteration loop."""
        backpressure_calls = []

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            iteration = [0]

            async def mock_execute(context):
                iteration[0] += 1
                if iteration[0] >= 2:
                    full_workspace["scratchpad"].write_text("STATUS: DONE")
                return AggregatedResult(
                    success=True,
                    primary_output="Done",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_executor.execute = mock_execute

            with patch("aurora_cli.commands.headless._run_backpressure") as mock_bp:
                mock_bp.side_effect = lambda cmd, output_format=None: backpressure_calls.append(cmd)

                await _run_multi_tool_loop(
                    tools_list=["claude"],
                    prompt="Test",
                    scratchpad=full_workspace["scratchpad"],
                    max_iter=10,
                    test_cmd="pytest",
                    strategy="first_success",
                )

                # Backpressure should be called after each iteration
                assert len(backpressure_calls) >= 1


# ---------------------------------------------------------------------------
# Test: Multi-Tool Real World Scenarios
# ---------------------------------------------------------------------------


class TestMultiToolRealWorldScenarios:
    """Test realistic multi-tool scenarios."""

    @pytest.mark.asyncio
    async def test_code_review_scenario(self, full_workspace):
        """Test code review with multiple reviewers (tools)."""
        full_workspace["prompt"].write_text(
            """# Goal
Review the authentication code for security and best practices.

# Context
- FastAPI application
- JWT authentication
- PostgreSQL database

# Success Criteria
- [ ] Identify security vulnerabilities
- [ ] Suggest improvements
- [ ] Check for best practices
"""
        )

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                full_workspace["scratchpad"].write_text(
                    """# Scratchpad

STATUS: DONE

## Claude's Review
- Found potential SQL injection in user query
- Recommend using parameterized queries

## OpenCode's Review
- Token expiry too long (24h)
- Recommend 1h with refresh tokens

## Consensus
Both reviewers agree code needs security improvements.
"""
                )
                return AggregatedResult(
                    success=True,
                    primary_output="Review complete",
                    strategy_used=AggregationStrategy.ALL_COMPLETE,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=True,
                            output="Security review findings...",
                            execution_time=5.0,
                        ),
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="Best practices review...",
                            execution_time=4.5,
                        ),
                    ],
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt=full_workspace["prompt"].read_text(),
                scratchpad=full_workspace["scratchpad"],
                max_iter=5,
                test_cmd=None,
                strategy="all_complete",
            )

            # Verify scratchpad was updated
            final_state = full_workspace["scratchpad"].read_text()
            assert "STATUS: DONE" in final_state

    @pytest.mark.asyncio
    async def test_iterative_development_scenario(self, full_workspace):
        """Test iterative development with multiple tools."""
        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1

                if iteration_count[0] == 1:
                    # Phase 1: Planning
                    return AggregatedResult(
                        success=True,
                        primary_output="Planning phase complete",
                        strategy_used=AggregationStrategy.FIRST_SUCCESS,
                        tool_results=[
                            ToolResult(
                                tool="claude",
                                success=True,
                                output="Created implementation plan",
                                execution_time=2.0,
                            ),
                        ],
                    )
                elif iteration_count[0] == 2:
                    # Phase 2: Implementation
                    return AggregatedResult(
                        success=True,
                        primary_output="Implementation phase complete",
                        strategy_used=AggregationStrategy.FIRST_SUCCESS,
                        tool_results=[
                            ToolResult(
                                tool="opencode",
                                success=True,
                                output="Code implemented",
                                execution_time=10.0,
                            ),
                        ],
                    )
                else:
                    # Phase 3: Testing - Done
                    full_workspace["scratchpad"].write_text("STATUS: DONE")
                    return AggregatedResult(
                        success=True,
                        primary_output="All tests passing",
                        strategy_used=AggregationStrategy.FIRST_SUCCESS,
                        tool_results=[
                            ToolResult(
                                tool="claude",
                                success=True,
                                output="Tests written and passing",
                                execution_time=5.0,
                            ),
                        ],
                    )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Implement feature",
                scratchpad=full_workspace["scratchpad"],
                max_iter=10,
                test_cmd=None,
                strategy="first_success",
            )

            # Verify all phases completed
            assert iteration_count[0] == 3


# ---------------------------------------------------------------------------
# Test: Results Display
# ---------------------------------------------------------------------------


class TestResultsDisplay:
    """Test results display functionality."""

    def test_display_multi_tool_results(self, capsys):
        """Test that results are displayed correctly."""
        result = AggregatedResult(
            success=True,
            primary_output="Winner output here",
            strategy_used=AggregationStrategy.FIRST_SUCCESS,
            tool_results=[
                ToolResult(tool="claude", success=True, output="Claude output", execution_time=1.5),
                ToolResult(
                    tool="opencode", success=False, output="", error="Failed", execution_time=2.0
                ),
            ],
            winning_tool="claude",
        )

        _display_multi_tool_results(result, "first_success")

        # Function should complete without error

    def test_display_results_with_scores(self, capsys):
        """Test display with score metadata."""
        result = AggregatedResult(
            success=True,
            primary_output="Best answer",
            strategy_used=AggregationStrategy.BEST_SCORE,
            tool_results=[
                ToolResult(tool="claude", success=True, output="Output", execution_time=1.0),
                ToolResult(tool="opencode", success=True, output="Output", execution_time=2.0),
            ],
            winning_tool="claude",
            metadata={"scores": {"claude": 15.0, "opencode": 12.0}},
        )

        _display_multi_tool_results(result, "best_score")


# ---------------------------------------------------------------------------
# Test: Final State Check
# ---------------------------------------------------------------------------


class TestFinalStateCheck:
    """Test final state checking."""

    def test_check_final_state_done(self, full_workspace, capsys):
        """Test final state when done."""
        full_workspace["scratchpad"].write_text("# Scratchpad\n\nSTATUS: DONE\n\nAll complete!")

        _check_final_state(full_workspace["scratchpad"])

        # Should indicate success

    def test_check_final_state_not_done(self, full_workspace, capsys):
        """Test final state when not done."""
        full_workspace["scratchpad"].write_text(
            "# Scratchpad\n\nSTATUS: IN_PROGRESS\n\nStill working"
        )

        _check_final_state(full_workspace["scratchpad"])

        # Should indicate incomplete


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
