"""TDD Tests for spawn(), spawn_parallel(), and spawn_sequential() functions."""

import asyncio
import os
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aurora_spawner.models import SpawnResult, SpawnTask
from aurora_spawner.spawner import spawn, spawn_parallel, spawn_sequential


class TestSpawn:
    """Tests for spawn() function."""

    @pytest.mark.asyncio
    async def test_spawn_success(self):
        """Test spawn with successful subprocess execution."""
        task = SpawnTask(prompt="test prompt")

        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"success output", b""))
        mock_process.returncode = 0
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = await spawn(task)

        assert result.success is True
        assert result.output == "success output"
        assert result.error == ""
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_spawn_failure_nonzero_exit(self):
        """Test spawn with subprocess returning non-zero exit code."""
        task = SpawnTask(prompt="test prompt")

        # Mock subprocess that fails
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b"error message"))
        mock_process.returncode = 1
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = await spawn(task)

        assert result.success is False
        assert result.error == "error message"
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_spawn_timeout(self):
        """Test spawn with timeout exceeded."""
        task = SpawnTask(prompt="test prompt", timeout=1)

        # Mock subprocess that hangs
        async def slow_communicate():
            await asyncio.sleep(10)
            return (b"", b"")

        mock_process = AsyncMock()
        mock_process.communicate = slow_communicate
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()
        mock_process.kill = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = await spawn(task)

        assert result.success is False
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_spawn_tool_not_found(self):
        """Test spawn raises ValueError when tool not found."""
        task = SpawnTask(prompt="test prompt")

        with patch("shutil.which", return_value=None):
            with pytest.raises(ValueError, match="Tool.*not found"):
                await spawn(task, tool="nonexistent")

    @pytest.mark.asyncio
    async def test_spawn_tool_resolution_cli_flag(self):
        """Test tool resolution prioritizes explicit parameter."""
        task = SpawnTask(prompt="test prompt")

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            with patch("shutil.which", return_value="/usr/bin/custom-tool"):
                with patch.dict(os.environ, {"AURORA_SPAWN_TOOL": "env-tool"}):
                    await spawn(task, tool="custom-tool")

        # Verify custom-tool was used (first arg to create_subprocess_exec)
        call_args = mock_exec.call_args[0]
        assert call_args[0] == "custom-tool"

    @pytest.mark.asyncio
    async def test_spawn_tool_resolution_env_var(self):
        """Test tool resolution uses AURORA_SPAWN_TOOL env var when no flag."""
        task = SpawnTask(prompt="test prompt")

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            with patch("shutil.which", return_value="/usr/bin/env-tool"):
                with patch.dict(os.environ, {"AURORA_SPAWN_TOOL": "env-tool"}):
                    await spawn(task)

        call_args = mock_exec.call_args[0]
        assert call_args[0] == "env-tool"

    @pytest.mark.asyncio
    async def test_spawn_tool_resolution_config(self):
        """Test tool resolution uses config value when no flag or env var."""
        task = SpawnTask(prompt="test prompt")

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()

        mock_config = {"spawner": {"tool": "config-tool"}}

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            with patch("shutil.which", return_value="/usr/bin/config-tool"):
                with patch.dict(os.environ, {}, clear=True):
                    await spawn(task, config=mock_config)

        call_args = mock_exec.call_args[0]
        assert call_args[0] == "config-tool"

    @pytest.mark.asyncio
    async def test_spawn_tool_resolution_default(self):
        """Test tool resolution defaults to 'claude' when nothing configured."""
        task = SpawnTask(prompt="test prompt")

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            with patch("shutil.which", return_value="/usr/bin/claude"):
                with patch.dict(os.environ, {}, clear=True):
                    await spawn(task)

        call_args = mock_exec.call_args[0]
        assert call_args[0] == "claude"

    @pytest.mark.asyncio
    async def test_spawn_model_resolution(self):
        """Test model resolution follows same priority as tool."""
        task = SpawnTask(prompt="test prompt")

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            with patch("shutil.which", return_value="/usr/bin/claude"):
                with patch.dict(os.environ, {}, clear=True):
                    await spawn(task, model="custom-model")

        call_args = mock_exec.call_args[0]
        assert "--model" in call_args
        model_index = call_args.index("--model")
        assert call_args[model_index + 1] == "custom-model"

    @pytest.mark.asyncio
    async def test_spawn_with_agent_flag(self):
        """Test spawn adds --agent flag when agent parameter provided."""
        task = SpawnTask(prompt="test prompt", agent="full-stack-dev")

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            with patch("shutil.which", return_value="/usr/bin/claude"):
                await spawn(task)

        call_args = mock_exec.call_args[0]
        assert "--agent" in call_args
        agent_index = call_args.index("--agent")
        assert call_args[agent_index + 1] == "full-stack-dev"

    @pytest.mark.asyncio
    async def test_spawn_streaming_output(self):
        """Test spawn invokes on_output callback for each line."""
        task = SpawnTask(prompt="test prompt")
        output_lines = []

        def on_output(line: str):
            output_lines.append(line)

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"line1\nline2\nline3", b""))
        mock_process.returncode = 0
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()
        mock_process.stdout = MagicMock()

        # Mock readline to return lines
        async def readline_side_effect():
            for line in [b"line1\n", b"line2\n", b"line3\n", b""]:
                return line

        mock_process.stdout.readline = AsyncMock(
            side_effect=[b"line1\n", b"line2\n", b"line3\n", b""]
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("shutil.which", return_value="/usr/bin/claude"):
                await spawn(task, on_output=on_output)

        # Note: This test verifies the callback interface exists
        # The actual streaming logic will be tested when implemented

    @pytest.mark.asyncio
    async def test_spawn_builds_correct_command(self):
        """Test spawn builds command: [tool, '-p', '--model', model]."""
        task = SpawnTask(prompt="test prompt")

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            with patch("shutil.which", return_value="/usr/bin/claude"):
                await spawn(task)

        call_args = mock_exec.call_args[0]
        # Command should be: tool, '-p', '--model', model_name
        assert call_args[0] == "claude"
        assert "-p" in call_args
        assert "--model" in call_args


class TestSpawnParallel:
    """Tests for spawn_parallel() function."""

    @pytest.mark.asyncio
    async def test_spawn_parallel_empty_list(self):
        """Test spawn_parallel with empty task list returns empty results."""
        results = await spawn_parallel([])
        assert results == []

    @pytest.mark.asyncio
    async def test_spawn_parallel_single_task(self):
        """Test spawn_parallel with single task executes and returns result."""
        task = SpawnTask(prompt="test prompt")

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("shutil.which", return_value="/usr/bin/claude"):
                results = await spawn_parallel([task])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].output == "output"

    @pytest.mark.asyncio
    async def test_spawn_parallel_multiple_tasks(self):
        """Test spawn_parallel executes multiple tasks concurrently."""
        tasks = [
            SpawnTask(prompt="task 1"),
            SpawnTask(prompt="task 2"),
            SpawnTask(prompt="task 3"),
        ]

        call_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate work
            return SpawnResult(
                success=True,
                output=f"output {call_count}",
                error=None,
                exit_code=0,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks)

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_spawn_parallel_respects_max_concurrent(self):
        """Test spawn_parallel respects max_concurrent semaphore limit."""
        tasks = [SpawnTask(prompt=f"task {i}") for i in range(10)]

        max_concurrent_running = 0
        current_running = 0

        async def mock_spawn(task, **kwargs):
            nonlocal max_concurrent_running, current_running
            current_running += 1
            max_concurrent_running = max(max_concurrent_running, current_running)
            await asyncio.sleep(0.01)  # Simulate work
            current_running -= 1
            return SpawnResult(
                success=True,
                output="output",
                error=None,
                exit_code=0,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            await spawn_parallel(tasks, max_concurrent=3)

        # Should never exceed max_concurrent
        assert max_concurrent_running <= 3

    @pytest.mark.asyncio
    async def test_spawn_parallel_continues_on_failure(self):
        """Test spawn_parallel continues execution after individual failures (best-effort)."""
        tasks = [
            SpawnTask(prompt="task 1"),
            SpawnTask(prompt="task 2"),
            SpawnTask(prompt="task 3"),
        ]

        call_index = 0

        async def mock_spawn(task, **kwargs):
            nonlocal call_index
            call_index += 1
            if call_index == 2:
                # Second task fails
                return SpawnResult(
                    success=False,
                    output="",
                    error="Task 2 failed",
                    exit_code=1,
                )
            return SpawnResult(
                success=True,
                output=f"output {call_index}",
                error=None,
                exit_code=0,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True

    @pytest.mark.asyncio
    async def test_spawn_parallel_preserves_order(self):
        """Test spawn_parallel returns results in input order."""
        tasks = [
            SpawnTask(prompt="task A"),
            SpawnTask(prompt="task B"),
            SpawnTask(prompt="task C"),
        ]

        async def mock_spawn(task, **kwargs):
            # Vary sleep time to ensure concurrent execution
            if "A" in task.prompt:
                await asyncio.sleep(0.03)
            elif "B" in task.prompt:
                await asyncio.sleep(0.01)
            else:
                await asyncio.sleep(0.02)

            return SpawnResult(
                success=True,
                output=task.prompt,
                error=None,
                exit_code=0,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_parallel(tasks)

        # Results should be in input order despite different execution times
        assert results[0].output == "task A"
        assert results[1].output == "task B"
        assert results[2].output == "task C"

    @pytest.mark.asyncio
    async def test_spawn_parallel_default_concurrency(self):
        """Test spawn_parallel defaults to max_concurrent=5."""
        tasks = [SpawnTask(prompt=f"task {i}") for i in range(10)]

        max_concurrent_running = 0
        current_running = 0

        async def mock_spawn(task, **kwargs):
            nonlocal max_concurrent_running, current_running
            current_running += 1
            max_concurrent_running = max(max_concurrent_running, current_running)
            await asyncio.sleep(0.01)
            current_running -= 1
            return SpawnResult(
                success=True,
                output="output",
                error=None,
                exit_code=0,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            await spawn_parallel(tasks)  # No max_concurrent specified

        # Should use default of 5
        assert max_concurrent_running <= 5


class TestSpawnSequential:
    """Tests for spawn_sequential() function."""

    @pytest.mark.asyncio
    async def test_spawn_sequential_empty_list(self):
        """Test spawn_sequential with empty task list returns empty results."""
        results = await spawn_sequential([])
        assert results == []

    @pytest.mark.asyncio
    async def test_spawn_sequential_single_task(self):
        """Test spawn_sequential with single task executes and returns result."""
        task = SpawnTask(prompt="test prompt")

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("shutil.which", return_value="/usr/bin/claude"):
                results = await spawn_sequential([task])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].output == "output"

    @pytest.mark.asyncio
    async def test_spawn_sequential_multiple_tasks(self):
        """Test spawn_sequential executes tasks in order."""
        tasks = [
            SpawnTask(prompt="task 1"),
            SpawnTask(prompt="task 2"),
            SpawnTask(prompt="task 3"),
        ]

        execution_order = []

        async def mock_spawn(task, **kwargs):
            # Track that tasks are executed sequentially (original prompts in order)
            if "task 1" in task.prompt:
                execution_order.append(1)
            elif "task 2" in task.prompt:
                execution_order.append(2)
            elif "task 3" in task.prompt:
                execution_order.append(3)
            return SpawnResult(
                success=True,
                output=f"result {len(execution_order)}",
                error=None,
                exit_code=0,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_sequential(tasks, pass_context=False)

        # Verify sequential execution order
        assert execution_order == [1, 2, 3]
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_spawn_sequential_context_accumulation(self):
        """Test spawn_sequential accumulates previous outputs in context."""
        tasks = [
            SpawnTask(prompt="task 1"),
            SpawnTask(prompt="task 2"),
            SpawnTask(prompt="task 3"),
        ]

        received_prompts = []

        async def mock_spawn(task, **kwargs):
            received_prompts.append(task.prompt)
            return SpawnResult(
                success=True,
                output=f"output {len(received_prompts)}",
                error=None,
                exit_code=0,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            await spawn_sequential(tasks, pass_context=True)

        # First task should have original prompt
        assert received_prompts[0] == "task 1"

        # Second task should have original prompt + previous context
        assert "task 2" in received_prompts[1]
        assert "Previous context:" in received_prompts[1]
        assert "output 1" in received_prompts[1]

        # Third task should have original prompt + accumulated context
        assert "task 3" in received_prompts[2]
        assert "Previous context:" in received_prompts[2]
        assert "output 1" in received_prompts[2]
        assert "output 2" in received_prompts[2]

    @pytest.mark.asyncio
    async def test_spawn_sequential_context_format(self):
        """Test spawn_sequential uses correct context format."""
        tasks = [
            SpawnTask(prompt="task 1"),
            SpawnTask(prompt="task 2"),
        ]

        received_prompts = []

        async def mock_spawn(task, **kwargs):
            received_prompts.append(task.prompt)
            return SpawnResult(
                success=True,
                output="test output",
                error=None,
                exit_code=0,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            await spawn_sequential(tasks, pass_context=True)

        # Second task should have context in format: "\n\nPrevious context:\n{accumulated}"
        assert "\n\nPrevious context:\n" in received_prompts[1]

    @pytest.mark.asyncio
    async def test_spawn_sequential_no_context_when_disabled(self):
        """Test spawn_sequential with pass_context=False skips accumulation."""
        tasks = [
            SpawnTask(prompt="task 1"),
            SpawnTask(prompt="task 2"),
        ]

        received_prompts = []

        async def mock_spawn(task, **kwargs):
            received_prompts.append(task.prompt)
            return SpawnResult(
                success=True,
                output="output",
                error=None,
                exit_code=0,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            await spawn_sequential(tasks, pass_context=False)

        # Second task should NOT have context appended
        assert received_prompts[0] == "task 1"
        assert received_prompts[1] == "task 2"
        assert "Previous context:" not in received_prompts[1]

    @pytest.mark.asyncio
    async def test_spawn_sequential_stops_on_failure_when_critical(self):
        """Test spawn_sequential can optionally abort on failure."""
        tasks = [
            SpawnTask(prompt="task 1"),
            SpawnTask(prompt="task 2"),
            SpawnTask(prompt="task 3"),
        ]

        call_count = 0

        async def mock_spawn(task, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                # Second task fails
                return SpawnResult(
                    success=False,
                    output="",
                    error="Task failed",
                    exit_code=1,
                )
            return SpawnResult(
                success=True,
                output="output",
                error=None,
                exit_code=0,
            )

        with patch("aurora_spawner.spawner.spawn", side_effect=mock_spawn):
            results = await spawn_sequential(tasks, stop_on_failure=True)

        # Should stop after second task fails
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
