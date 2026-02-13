"""Tests for heartbeat mechanism."""

import asyncio
import time

import pytest

from aurora_spawner.heartbeat import (
    HeartbeatEmitter,
    HeartbeatEventType,
    HeartbeatMonitor,
    create_heartbeat_emitter,
    create_heartbeat_monitor,
)


class TestHeartbeatEmitter:
    """Test heartbeat emitter functionality."""

    def test_emit_event(self):
        """Test basic event emission."""
        emitter = HeartbeatEmitter(task_id="test-001")

        emitter.emit(HeartbeatEventType.STARTED, agent_id="agent-1", message="Starting")

        events = emitter.get_all_events()
        assert len(events) == 1
        assert events[0].event_type == HeartbeatEventType.STARTED
        assert events[0].task_id == "test-001"
        assert events[0].agent_id == "agent-1"
        assert events[0].message == "Starting"

    def test_emit_multiple_events(self):
        """Test emitting multiple events."""
        emitter = HeartbeatEmitter(task_id="test-002")

        emitter.emit(HeartbeatEventType.STARTED, message="Start")
        emitter.emit(HeartbeatEventType.STDOUT, message="Output")
        emitter.emit(HeartbeatEventType.COMPLETED, message="Done")

        events = emitter.get_all_events()
        assert len(events) == 3
        assert events[0].event_type == HeartbeatEventType.STARTED
        assert events[1].event_type == HeartbeatEventType.STDOUT
        assert events[2].event_type == HeartbeatEventType.COMPLETED

    def test_get_latest_event(self):
        """Test getting latest event."""
        emitter = HeartbeatEmitter(task_id="test-003")

        assert emitter.get_latest_event() is None

        emitter.emit(HeartbeatEventType.STARTED)
        emitter.emit(HeartbeatEventType.COMPLETED)

        latest = emitter.get_latest_event()
        assert latest is not None
        assert latest.event_type == HeartbeatEventType.COMPLETED

    def test_seconds_since_start(self):
        """Test elapsed time tracking."""
        emitter = HeartbeatEmitter(task_id="test-004")

        assert emitter.seconds_since_start() == 0.0

        emitter.emit(HeartbeatEventType.STARTED)
        time.sleep(0.1)

        elapsed = emitter.seconds_since_start()
        assert elapsed >= 0.1
        assert elapsed < 1.0

    def test_seconds_since_activity(self):
        """Test activity time tracking."""
        emitter = HeartbeatEmitter(task_id="test-005")

        emitter.emit(HeartbeatEventType.STARTED)
        time.sleep(0.1)
        emitter.emit(HeartbeatEventType.STDOUT, message="Activity")
        time.sleep(0.1)

        idle = emitter.seconds_since_activity()
        assert idle >= 0.1
        assert idle < 1.0

    def test_buffer_size_limit(self):
        """Test event buffer respects size limit."""
        emitter = HeartbeatEmitter(task_id="test-006", buffer_size=5)

        for i in range(10):
            emitter.emit(HeartbeatEventType.STDOUT, message=f"Event {i}")

        events = emitter.get_all_events()
        assert len(events) == 5

    def test_thread_safety(self):
        """Test thread-safe emission."""
        import threading

        emitter = HeartbeatEmitter(task_id="test-007")
        threads = []

        def emit_events(thread_id):
            for i in range(100):
                emitter.emit(HeartbeatEventType.STDOUT, message=f"Thread {thread_id} event {i}")

        for tid in range(5):
            thread = threading.Thread(target=emit_events, args=(tid,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        events = emitter.get_all_events()
        assert len(events) == 500

    def test_subscriber_notification(self):
        """Test subscriber callbacks."""
        emitter = HeartbeatEmitter(task_id="test-008")
        received = []

        def callback(event):
            received.append(event)

        emitter.subscribe(callback)

        emitter.emit(HeartbeatEventType.STARTED)
        emitter.emit(HeartbeatEventType.COMPLETED)

        assert len(received) == 2
        assert received[0].event_type == HeartbeatEventType.STARTED
        assert received[1].event_type == HeartbeatEventType.COMPLETED

    def test_metadata_storage(self):
        """Test event metadata."""
        emitter = HeartbeatEmitter(task_id="test-009")

        emitter.emit(
            HeartbeatEventType.STDOUT,
            message="Output",
            bytes=1024,
            line_count=10,
            custom_field="value",
        )

        event = emitter.get_latest_event()
        assert event.metadata["bytes"] == 1024
        assert event.metadata["line_count"] == 10
        assert event.metadata["custom_field"] == "value"


class TestHeartbeatMonitor:
    """Test heartbeat monitor functionality."""

    def test_health_check_healthy(self):
        """Test health check on healthy execution."""
        emitter = HeartbeatEmitter(task_id="test-011")
        monitor = HeartbeatMonitor(emitter, total_timeout=10, activity_timeout=5)

        emitter.emit(HeartbeatEventType.STARTED)
        emitter.emit(HeartbeatEventType.STDOUT, message="Activity")

        healthy, reason = monitor.check_health()
        assert healthy is True
        assert reason is None

    def test_health_check_activity_timeout(self):
        """Test health check detects activity timeout."""
        emitter = HeartbeatEmitter(task_id="test-013")
        monitor = HeartbeatMonitor(emitter, total_timeout=10, activity_timeout=0.1)

        emitter.emit(HeartbeatEventType.STARTED)
        emitter.emit(HeartbeatEventType.STDOUT)
        time.sleep(0.2)

        healthy, reason = monitor.check_health()
        assert healthy is False
        assert "No activity" in reason


class TestHeartbeatStream:
    """Test heartbeat streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_events(self):
        """Test async event streaming."""
        emitter = HeartbeatEmitter(task_id="test-017")

        async def emit_events():
            for i in range(5):
                await asyncio.sleep(0.05)
                emitter.emit(HeartbeatEventType.STDOUT, message=f"Event {i}")

        async def consume_stream():
            received = []
            async for event in emitter.stream(poll_interval=0.01):
                received.append(event)
                if len(received) == 5:
                    break
            return received

        emit_task = asyncio.create_task(emit_events())
        consume_task = asyncio.create_task(consume_stream())

        received = await consume_task
        await emit_task

        assert len(received) == 5
        assert all(e.event_type == HeartbeatEventType.STDOUT for e in received)


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_heartbeat_emitter(self):
        """Test emitter factory."""
        emitter = create_heartbeat_emitter("factory-test")
        assert emitter.task_id == "factory-test"
        assert isinstance(emitter, HeartbeatEmitter)

    def test_create_heartbeat_monitor(self):
        """Test monitor factory."""
        emitter = create_heartbeat_emitter("monitor-test")
        monitor = create_heartbeat_monitor(emitter, timeout=120)

        assert monitor.emitter is emitter
        assert monitor.total_timeout == 120
        assert monitor.activity_timeout == 60  # Half of total
        assert isinstance(monitor, HeartbeatMonitor)

    def test_create_monitor_with_short_timeout(self):
        """Test monitor factory with short timeout."""
        emitter = create_heartbeat_emitter("short-test")
        monitor = create_heartbeat_monitor(emitter, timeout=60)

        # Should use 120s activity timeout (max cap)
        assert monitor.activity_timeout == 30
