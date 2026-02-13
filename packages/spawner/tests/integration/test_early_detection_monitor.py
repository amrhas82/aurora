"""Integration tests for EarlyDetectionMonitor async lifecycle.

Tests the monitor start/stop/register cycle to catch Python version
regressions (e.g., Python 3.14 asyncio.timeout compatibility).
"""

import asyncio

import pytest

from aurora_spawner.early_detection import EarlyDetectionConfig, EarlyDetectionMonitor


class TestMonitorLifecycle:
    """Tests for monitor start, register, stop cycle."""

    @pytest.mark.asyncio
    async def test_start_and_stop_cleanly(self):
        """Monitor starts background task and stops without errors.

        This is the core regression test for Python 3.14 asyncio compat —
        the monitor loop must run and stop without RuntimeError.
        """
        config = EarlyDetectionConfig(check_interval=0.1)
        monitor = EarlyDetectionMonitor(config=config)

        await monitor.start_monitoring()
        assert monitor._monitor_task is not None
        assert not monitor._monitor_task.done()

        # Let it run at least one check cycle
        await asyncio.sleep(0.15)

        await monitor.stop_monitoring()
        assert monitor._monitor_task is None

    @pytest.mark.asyncio
    async def test_register_and_unregister_execution(self):
        """Executions can be registered and unregistered during monitoring."""
        config = EarlyDetectionConfig(check_interval=0.1)
        monitor = EarlyDetectionMonitor(config=config)

        await monitor.start_monitoring()

        await monitor.register_execution("task-1", "code-developer")
        assert "task-1" in monitor._executions

        await monitor.unregister_execution("task-1")
        assert "task-1" not in monitor._executions

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_should_terminate_returns_false_for_active_task(self):
        """Fresh execution should not be flagged for termination."""
        config = EarlyDetectionConfig(check_interval=0.1)
        monitor = EarlyDetectionMonitor(config=config)

        await monitor.start_monitoring()
        await monitor.register_execution("task-1", "code-developer")

        should_term, reason = await monitor.should_terminate("task-1")
        assert should_term is False
        assert reason is None

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_update_activity_resets_stall_counter(self):
        """Updating activity with new output resets consecutive stall count."""
        config = EarlyDetectionConfig(check_interval=0.1)
        monitor = EarlyDetectionMonitor(config=config)

        await monitor.start_monitoring()
        await monitor.register_execution("task-1", "code-developer")

        # Simulate output growth
        await monitor.update_activity("task-1", stdout_size=500)

        state = monitor._executions["task-1"]
        assert state.stdout_size == 500
        assert state.consecutive_stalls == 0

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_disabled_monitor_is_noop(self):
        """Disabled config skips all monitoring without errors."""
        config = EarlyDetectionConfig(enabled=False)
        monitor = EarlyDetectionMonitor(config=config)

        await monitor.start_monitoring()
        assert monitor._monitor_task is None  # Never started

        # These should all be no-ops
        await monitor.register_execution("task-1", "agent")
        assert "task-1" not in monitor._executions

        should_term, reason = await monitor.should_terminate("task-1")
        assert should_term is False

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_multiple_start_calls_are_idempotent(self):
        """Calling start_monitoring twice doesn't create duplicate tasks."""
        config = EarlyDetectionConfig(check_interval=0.1)
        monitor = EarlyDetectionMonitor(config=config)

        await monitor.start_monitoring()
        first_task = monitor._monitor_task

        await monitor.start_monitoring()
        assert monitor._monitor_task is first_task  # Same task, not replaced

        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self):
        """Stopping a monitor that was never started doesn't raise."""
        monitor = EarlyDetectionMonitor()
        await monitor.stop_monitoring()  # Should not raise

    @pytest.mark.asyncio
    async def test_monitor_survives_multiple_check_cycles(self):
        """Monitor runs through several health check iterations without error."""
        config = EarlyDetectionConfig(check_interval=0.05, stall_threshold=120.0)
        monitor = EarlyDetectionMonitor(config=config)

        await monitor.start_monitoring()
        await monitor.register_execution("task-1", "code-developer")

        # Let it run ~5 cycles
        await asyncio.sleep(0.3)

        assert not monitor._monitor_task.done()
        should_term, _ = await monitor.should_terminate("task-1")
        assert should_term is False  # stall_threshold=120s, only 0.3s elapsed

        await monitor.stop_monitoring()
