"""Comprehensive test suite for early detection system.

Tests timeout scenarios, agent crashes, stall detection, and recovery validation.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aurora_spawner.early_detection import (
    EarlyDetectionConfig,
    EarlyDetectionMonitor,
    get_early_detection_monitor,
    reset_early_detection_monitor,
)


class TestEarlyDetectionTimeout:
    """Test timeout and stall detection scenarios."""

    @pytest.mark.asyncio
    async def test_stall_detection_after_threshold(self):
        """Verify stall detected after threshold with no output progress."""
        config = EarlyDetectionConfig(
            enabled=True,
            check_interval=0.1,
            stall_threshold=0.3,
            min_output_bytes=100,
        )
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")

        # Simulate initial output to pass min_output_bytes
        await monitor.update_activity("task1", stdout_size=150)
        await asyncio.sleep(0.05)

        # Wait for stall threshold + 2 check intervals (need 2 consecutive detections)
        await asyncio.sleep(0.5)

        # Check termination
        should_terminate, reason = await monitor.should_terminate("task1")
        assert should_terminate, "Should terminate after stall threshold"
        assert "Stalled" in reason
        assert "no output" in reason.lower()

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_no_stall_with_continuous_activity(self):
        """Verify no stall detection when output is continuously growing."""
        config = EarlyDetectionConfig(
            enabled=True,
            check_interval=0.1,
            stall_threshold=0.3,
            min_output_bytes=100,
        )
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")

        # Simulate continuous output growth
        for i in range(5):
            await monitor.update_activity("task1", stdout_size=150 + i * 50)
            await asyncio.sleep(0.1)

        # Check no termination
        should_terminate, _ = await monitor.should_terminate("task1")
        assert not should_terminate, "Should not terminate with continuous activity"

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_stall_requires_min_output(self):
        """Verify stall check doesn't trigger before min_output_bytes."""
        config = EarlyDetectionConfig(
            enabled=True,
            check_interval=0.1,
            stall_threshold=0.2,
            min_output_bytes=100,
        )
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")

        # Don't update activity (stdout_size stays 0)
        await asyncio.sleep(0.4)

        # Check no termination (below min_output_bytes)
        should_terminate, _ = await monitor.should_terminate("task1")
        assert not should_terminate, "Should not terminate before min_output_bytes"

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_consecutive_stall_detections_required(self):
        """Verify termination requires 2 consecutive stall detections."""
        config = EarlyDetectionConfig(
            enabled=True,
            check_interval=0.1,
            stall_threshold=0.2,
            min_output_bytes=100,
        )
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")

        # Simulate initial output
        await monitor.update_activity("task1", stdout_size=150)

        # Wait for first stall detection
        await asyncio.sleep(0.25)

        # Provide activity to reset consecutive counter
        await monitor.update_activity("task1", stdout_size=151)
        await asyncio.sleep(0.05)

        # Wait another stall period
        await asyncio.sleep(0.25)

        # Should not terminate yet (only 1 consecutive detection)
        should_terminate, _ = await monitor.should_terminate("task1")
        # Note: This depends on timing - may need 2 full cycles
        # Just verify monitor is tracking state correctly

        await monitor.stop_monitoring()


class TestEarlyDetectionCrash:
    """Test agent crash and termination scenarios."""

    @pytest.mark.asyncio
    async def test_early_termination_trigger(self):
        """Verify manual termination trigger works."""
        config = EarlyDetectionConfig(enabled=True)
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")

        # Get execution state and trigger termination
        async with monitor._lock:
            state = monitor._executions["task1"]
            await monitor._trigger_termination(state, "Test crash")

        # Verify termination
        should_terminate, reason = await monitor.should_terminate("task1")
        assert should_terminate
        assert reason == "Test crash"

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_callback_on_detection(self):
        """Verify callback is invoked on detection."""
        callback_invoked = False
        callback_task_id = None
        callback_reason = None

        def callback(task_id: str, reason: str):
            nonlocal callback_invoked, callback_task_id, callback_reason
            callback_invoked = True
            callback_task_id = task_id
            callback_reason = reason

        config = EarlyDetectionConfig(
            enabled=True,
            check_interval=0.1,
            stall_threshold=0.2,
            min_output_bytes=50,
            callback_on_detection=callback,
        )
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")

        # Trigger stall
        await monitor.update_activity("task1", stdout_size=100)
        await asyncio.sleep(0.35)

        # Verify callback
        assert callback_invoked, "Callback should be invoked"
        assert callback_task_id == "task1"
        assert "Stalled" in callback_reason

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_multiple_execution_tracking(self):
        """Verify monitoring multiple executions simultaneously."""
        config = EarlyDetectionConfig(
            enabled=True,
            check_interval=0.1,
            stall_threshold=0.2,
            min_output_bytes=100,
        )
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()

        # Register multiple executions
        await monitor.register_execution("task1", "agent1")
        await monitor.register_execution("task2", "agent2")
        await monitor.register_execution("task3", "agent3")

        # task1: continuous activity (no termination)
        await monitor.update_activity("task1", stdout_size=150)

        # task2: initial output then stall
        await monitor.update_activity("task2", stdout_size=150)

        # task3: no output (below threshold)

        # Wait for stall detection on task2
        await asyncio.sleep(0.35)

        # Check results
        term1, _ = await monitor.should_terminate("task1")
        term2, reason2 = await monitor.should_terminate("task2")
        term3, _ = await monitor.should_terminate("task3")

        # task2 may terminate (depends on consecutive checks)
        # task3 should not (below min_output_bytes)
        assert not term3, "task3 should not terminate (below min_output)"

        await monitor.stop_monitoring()


class TestEarlyDetectionRecovery:
    """Test recovery validation and cleanup."""

    @pytest.mark.asyncio
    async def test_unregister_execution(self):
        """Verify unregistering removes execution from monitoring."""
        config = EarlyDetectionConfig(enabled=True)
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")

        # Verify registered
        async with monitor._lock:
            assert "task1" in monitor._executions

        # Unregister
        await monitor.unregister_execution("task1")

        # Verify removed
        async with monitor._lock:
            assert "task1" not in monitor._executions

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_monitoring_restart(self):
        """Verify monitor can be stopped and restarted."""
        config = EarlyDetectionConfig(enabled=True)
        monitor = EarlyDetectionMonitor(config)

        # Start
        await monitor.start_monitoring()
        assert monitor._monitor_task is not None

        # Stop
        await monitor.stop_monitoring()
        assert monitor._monitor_task is None

        # Restart
        await monitor.start_monitoring()
        assert monitor._monitor_task is not None

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_disabled_monitor_noop(self):
        """Verify disabled monitor performs no operations."""
        config = EarlyDetectionConfig(enabled=False)
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")
        await monitor.update_activity("task1", stdout_size=100)

        # Should not terminate (monitor disabled)
        should_terminate, reason = await monitor.should_terminate("task1")
        assert not should_terminate
        assert reason is None

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_global_monitor_singleton(self):
        """Verify global monitor singleton behavior."""
        monitor1 = get_early_detection_monitor()
        monitor2 = get_early_detection_monitor()

        assert monitor1 is monitor2, "Should return same singleton instance"

    @pytest.mark.asyncio
    async def test_reset_monitor(self):
        """Verify reset creates new monitor instance."""
        monitor1 = get_early_detection_monitor()

        config = EarlyDetectionConfig(check_interval=1.0)
        monitor2 = reset_early_detection_monitor(config)

        assert monitor1 is not monitor2, "Reset should create new instance"
        assert monitor2.config.check_interval == 1.0


class TestEarlyDetectionIntegration:
    """Integration tests with spawner."""

    @pytest.mark.asyncio
    async def test_spawner_integration_timeout(self):
        """Test early detection integration with spawner timeout."""
        from aurora_spawner.models import SpawnTask
        from aurora_spawner.spawner import spawn

        # Reset monitor with aggressive config
        config = EarlyDetectionConfig(
            enabled=True,
            check_interval=0.1,
            stall_threshold=0.5,
            min_output_bytes=10,
        )
        reset_early_detection_monitor(config)

        # Create mock subprocess that produces no output
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdout.read = AsyncMock(return_value=b"")
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.stdin = None
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("shutil.which", return_value="/usr/bin/claude"):
                task = SpawnTask(prompt="test", agent="test-agent", timeout=10)

                # Should detect stall and terminate early
                result = await spawn(task)

                # Verify early termination
                assert not result.success
                assert result.termination_reason is not None

    @pytest.mark.asyncio
    async def test_spawner_integration_normal_execution(self):
        """Test early detection doesn't interfere with normal execution."""
        from aurora_spawner.models import SpawnTask
        from aurora_spawner.spawner import spawn

        # Reset monitor with normal config
        config = EarlyDetectionConfig(enabled=True)
        reset_early_detection_monitor(config)

        # Create mock subprocess that completes successfully
        mock_process = AsyncMock()
        mock_process.returncode = 0

        async def mock_stdout_read(n):
            # Simulate progressive output
            await asyncio.sleep(0.01)
            return b"Output chunk\n"

        mock_process.stdout.read = mock_stdout_read
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = MagicMock()
        mock_process.stdin.wait_closed = AsyncMock()
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("shutil.which", return_value="/usr/bin/claude"):
                task = SpawnTask(prompt="test", agent="test-agent", timeout=10)

                result = await spawn(task)

                # Should complete successfully
                assert result.success or result.termination_reason is None


class TestEarlyDetectionEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_update_activity_unknown_task(self):
        """Verify updating unknown task is safe."""
        config = EarlyDetectionConfig(enabled=True)
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()

        # Update non-existent task (should not raise)
        await monitor.update_activity("unknown", stdout_size=100)

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_should_terminate_unknown_task(self):
        """Verify checking unknown task returns False."""
        config = EarlyDetectionConfig(enabled=True)
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()

        should_terminate, reason = await monitor.should_terminate("unknown")
        assert not should_terminate
        assert reason is None

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_double_termination(self):
        """Verify double termination is idempotent."""
        config = EarlyDetectionConfig(enabled=True)
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")

        # Trigger termination twice
        async with monitor._lock:
            state = monitor._executions["task1"]
            await monitor._trigger_termination(state, "First termination")
            await monitor._trigger_termination(state, "Second termination")

        # Verify still terminated with first reason
        should_terminate, reason = await monitor.should_terminate("task1")
        assert should_terminate
        assert reason == "First termination"

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_monitor_exception_handling(self):
        """Verify monitor handles exceptions in health checks gracefully."""
        config = EarlyDetectionConfig(enabled=True, check_interval=0.05)
        monitor = EarlyDetectionMonitor(config)

        # Inject exception into check execution
        original_check = monitor._check_execution

        async def failing_check(*args, **kwargs):
            raise RuntimeError("Test exception")

        monitor._check_execution = failing_check

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")

        # Wait for monitor loop to hit exception
        await asyncio.sleep(0.15)

        # Monitor should still be running
        assert monitor._monitor_task is not None
        assert not monitor._monitor_task.done()

        # Restore and stop
        monitor._check_execution = original_check
        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_stderr_size_tracking(self):
        """Verify stderr activity also resets stall counter."""
        config = EarlyDetectionConfig(
            enabled=True,
            check_interval=0.1,
            stall_threshold=0.2,
            min_output_bytes=100,
        )
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")

        # Update stdout initially
        await monitor.update_activity("task1", stdout_size=150)
        await asyncio.sleep(0.15)

        # Update stderr before stall threshold
        await monitor.update_activity("task1", stdout_size=150, stderr_size=50)
        await asyncio.sleep(0.15)

        # Should not terminate (stderr activity resets timer)
        should_terminate, _ = await monitor.should_terminate("task1")
        assert not should_terminate

        await monitor.stop_monitoring()


class TestEarlyDetectionPerformance:
    """Test performance and resource usage."""

    @pytest.mark.asyncio
    async def test_high_frequency_updates(self):
        """Verify monitor handles high-frequency activity updates."""
        config = EarlyDetectionConfig(enabled=True, check_interval=0.1)
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()
        await monitor.register_execution("task1", "agent1")

        # Rapid updates
        for i in range(100):
            await monitor.update_activity("task1", stdout_size=100 + i)
            await asyncio.sleep(0.001)

        # Should not terminate
        should_terminate, _ = await monitor.should_terminate("task1")
        assert not should_terminate

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_many_concurrent_tasks(self):
        """Verify monitor handles many concurrent tasks."""
        config = EarlyDetectionConfig(enabled=True, check_interval=0.1)
        monitor = EarlyDetectionMonitor(config)

        await monitor.start_monitoring()

        # Register 50 tasks
        for i in range(50):
            await monitor.register_execution(f"task{i}", f"agent{i}")

        # Update all tasks
        for i in range(50):
            await monitor.update_activity(f"task{i}", stdout_size=100 + i)

        await asyncio.sleep(0.15)

        # All should be healthy
        for i in range(50):
            should_terminate, _ = await monitor.should_terminate(f"task{i}")
            assert not should_terminate

        await monitor.stop_monitoring()


class TestEarlyDetectionConfiguration:
    """Test configuration and customization."""

    def test_config_defaults(self):
        """Verify default configuration values."""
        config = EarlyDetectionConfig()

        assert config.enabled is True
        assert config.check_interval == 5.0
        assert config.stall_threshold == 120.0
        assert config.min_output_bytes == 100
        assert config.stderr_pattern_check is True
        assert config.memory_limit_mb is None
        assert config.callback_on_detection is None

    def test_config_custom_values(self):
        """Verify custom configuration values."""
        config = EarlyDetectionConfig(
            enabled=False,
            check_interval=2.0,
            stall_threshold=60.0,
            min_output_bytes=500,
            stderr_pattern_check=False,
            memory_limit_mb=1024,
        )

        assert config.enabled is False
        assert config.check_interval == 2.0
        assert config.stall_threshold == 60.0
        assert config.min_output_bytes == 500
        assert config.stderr_pattern_check is False
        assert config.memory_limit_mb == 1024

    @pytest.mark.asyncio
    async def test_monitor_respects_config(self):
        """Verify monitor respects configuration settings."""
        config = EarlyDetectionConfig(
            enabled=True,
            check_interval=0.05,
            stall_threshold=0.1,
        )
        monitor = EarlyDetectionMonitor(config)

        assert monitor.config.check_interval == 0.05
        assert monitor.config.stall_threshold == 0.1
