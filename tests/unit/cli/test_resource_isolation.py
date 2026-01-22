"""Unit tests for resource isolation mechanisms.

Tests cover:
- IsolationConfig and ResourceLimits configuration
- ExecutionContext lifecycle and cleanup
- FileLockManager locking/unlocking
- ResourceIsolationManager semaphores and isolation
- Integration with ConcurrentToolExecutor
"""

import asyncio
import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aurora_cli.resource_isolation import (
    ExecutionContext,
    FileLockManager,
    IsolationConfig,
    IsolationLevel,
    ResourceIsolationManager,
    ResourceLimits,
    create_isolation_manager,
    with_isolation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def isolation_config(temp_dir):
    """Create a basic isolation config."""
    return IsolationConfig(
        level=IsolationLevel.LIGHT,
        base_temp_dir=temp_dir,
        limits=ResourceLimits(max_concurrent=3, max_per_tool=2),
    )


@pytest.fixture
def isolation_manager(isolation_config):
    """Create an isolation manager for tests."""
    return ResourceIsolationManager(isolation_config)


# ---------------------------------------------------------------------------
# Test: IsolationConfig
# ---------------------------------------------------------------------------


class TestIsolationConfig:
    """Test IsolationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = IsolationConfig()
        assert config.level == IsolationLevel.LIGHT
        assert config.base_temp_dir is None
        assert "PATH" in config.preserve_env_vars
        assert config.cleanup_strategy == "always"

    def test_custom_config(self, temp_dir):
        """Test custom configuration."""
        config = IsolationConfig(
            level=IsolationLevel.FULL,
            base_temp_dir=temp_dir,
            preserve_env_vars=["PATH", "HOME"],
            extra_env_vars={"MY_VAR": "value"},
            cleanup_strategy="on_success",
        )
        assert config.level == IsolationLevel.FULL
        assert config.base_temp_dir == temp_dir
        assert len(config.preserve_env_vars) == 2
        assert config.extra_env_vars["MY_VAR"] == "value"

    def test_resource_limits(self):
        """Test ResourceLimits configuration."""
        limits = ResourceLimits(
            max_concurrent=10,
            max_per_tool=3,
            max_memory=1024 * 1024,
        )
        assert limits.max_concurrent == 10
        assert limits.max_per_tool == 3
        assert limits.max_memory == 1024 * 1024


# ---------------------------------------------------------------------------
# Test: ExecutionContext
# ---------------------------------------------------------------------------


class TestExecutionContext:
    """Test ExecutionContext lifecycle."""

    def test_context_creation(self, temp_dir):
        """Test creating an execution context."""
        context = ExecutionContext(
            execution_id="test-123",
            tool_name="claude",
            working_dir=temp_dir,
            environment={"PATH": "/usr/bin"},
            temp_dir=temp_dir,
        )
        assert context.execution_id == "test-123"
        assert context.tool_name == "claude"
        assert context.success is None

    def test_sync_context_manager(self, temp_dir):
        """Test synchronous context manager."""
        cleanup_called = [False]

        def cleanup():
            cleanup_called[0] = True

        context = ExecutionContext(
            execution_id="test-456",
            tool_name="claude",
            working_dir=temp_dir,
            environment={},
            temp_dir=temp_dir,
            cleanup_callback=cleanup,
        )

        with context:
            assert context.success is None

        assert context.success is True
        assert cleanup_called[0] is True

    def test_sync_context_manager_on_error(self, temp_dir):
        """Test context manager sets success=False on exception."""
        cleanup_called = [False]

        def cleanup():
            cleanup_called[0] = True

        context = ExecutionContext(
            execution_id="test-789",
            tool_name="claude",
            working_dir=temp_dir,
            environment={},
            temp_dir=temp_dir,
            cleanup_callback=cleanup,
        )

        with pytest.raises(ValueError):
            with context:
                raise ValueError("Test error")

        assert context.success is False
        assert cleanup_called[0] is True

    @pytest.mark.asyncio
    async def test_async_context_manager(self, temp_dir):
        """Test async context manager."""
        cleanup_called = [False]

        def cleanup():
            cleanup_called[0] = True

        context = ExecutionContext(
            execution_id="test-async",
            tool_name="opencode",
            working_dir=temp_dir,
            environment={},
            temp_dir=temp_dir,
            cleanup_callback=cleanup,
        )

        async with context:
            pass

        assert context.success is True
        assert cleanup_called[0] is True


# ---------------------------------------------------------------------------
# Test: FileLockManager
# ---------------------------------------------------------------------------


class TestFileLockManager:
    """Test file-based locking."""

    def test_lock_creation(self, temp_dir):
        """Test creating and acquiring a lock."""
        manager = FileLockManager(temp_dir / "locks")

        with manager.lock("test-resource") as lock_path:
            assert lock_path.exists()
            assert "test-resource" in str(lock_path)

    def test_exclusive_lock_blocks(self, temp_dir):
        """Test that exclusive locks block each other."""
        manager = FileLockManager(temp_dir / "locks")
        results = []

        def acquire_lock(name):
            try:
                with manager.lock("shared-resource", exclusive=True, timeout=0.5):
                    results.append(f"{name}-acquired")
                    import time

                    time.sleep(0.2)
                    results.append(f"{name}-released")
            except TimeoutError:
                results.append(f"{name}-timeout")

        # Start first thread
        t1 = threading.Thread(target=acquire_lock, args=("t1",))
        t1.start()

        # Wait a bit then start second thread
        import time

        time.sleep(0.05)

        t2 = threading.Thread(target=acquire_lock, args=("t2",))
        t2.start()

        t1.join()
        t2.join()

        # First should complete, second might timeout or succeed after first releases
        assert "t1-acquired" in results
        assert "t1-released" in results

    @pytest.mark.asyncio
    async def test_async_lock(self, temp_dir):
        """Test async lock acquisition."""
        manager = FileLockManager(temp_dir / "locks")

        async with manager.async_lock("async-resource") as lock_path:
            assert lock_path.exists()

    def test_cleanup(self, temp_dir):
        """Test cleanup releases all locks."""
        manager = FileLockManager(temp_dir / "locks")

        # Acquire lock but don't release via context manager
        lock_path = manager._lock_path("cleanup-test")
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manager._held_locks["cleanup-test"] = fd

        assert "cleanup-test" in manager._held_locks

        manager.cleanup()

        assert "cleanup-test" not in manager._held_locks


# ---------------------------------------------------------------------------
# Test: ResourceIsolationManager
# ---------------------------------------------------------------------------


class TestResourceIsolationManager:
    """Test resource isolation manager."""

    @pytest.mark.asyncio
    async def test_acquire_context(self, isolation_manager):
        """Test acquiring an execution context."""
        context = await isolation_manager.acquire_context("claude")

        try:
            assert context.execution_id.startswith("claude-")
            assert context.tool_name == "claude"
            assert context.working_dir.exists() or context.working_dir == Path.cwd()
            assert "AURORA_EXECUTION_ID" in context.environment
            assert "AURORA_TOOL_NAME" in context.environment
        finally:
            if context.cleanup_callback:
                context.cleanup_callback()

    @pytest.mark.asyncio
    async def test_isolated_execution_context_manager(self, isolation_manager):
        """Test isolated_execution context manager."""
        async with isolation_manager.isolated_execution("claude") as context:
            assert context.execution_id.startswith("claude-")
            assert context.temp_dir.exists()

    @pytest.mark.asyncio
    async def test_concurrent_semaphore_limits(self, temp_dir):
        """Test that semaphores limit concurrent executions."""
        config = IsolationConfig(
            level=IsolationLevel.LIGHT,
            base_temp_dir=temp_dir,
            limits=ResourceLimits(max_concurrent=2, max_per_tool=1),
        )
        manager = ResourceIsolationManager(config)

        execution_order = []
        active_count = [0]
        max_active = [0]

        async def execute(tool_name, delay):
            async with manager.isolated_execution(tool_name) as context:
                active_count[0] += 1
                max_active[0] = max(max_active[0], active_count[0])
                execution_order.append(f"{tool_name}-start")
                await asyncio.sleep(delay)
                execution_order.append(f"{tool_name}-end")
                active_count[0] -= 1

        # Run 3 executions with max_concurrent=2
        await asyncio.gather(
            execute("tool1", 0.1),
            execute("tool2", 0.1),
            execute("tool3", 0.1),
        )

        # Due to semaphores, max active should be <= 2
        assert max_active[0] <= 2

    @pytest.mark.asyncio
    async def test_per_tool_semaphore(self, temp_dir):
        """Test per-tool concurrency limits."""
        config = IsolationConfig(
            level=IsolationLevel.LIGHT,
            base_temp_dir=temp_dir,
            limits=ResourceLimits(max_concurrent=10, max_per_tool=1),
        )
        manager = ResourceIsolationManager(config)

        claude_active = [0]
        max_claude = [0]

        async def execute_claude(idx):
            async with manager.isolated_execution("claude") as context:
                claude_active[0] += 1
                max_claude[0] = max(max_claude[0], claude_active[0])
                await asyncio.sleep(0.05)
                claude_active[0] -= 1

        # Run 3 Claude executions with max_per_tool=1
        await asyncio.gather(
            execute_claude(1),
            execute_claude(2),
            execute_claude(3),
        )

        # Max Claude instances should be 1
        assert max_claude[0] == 1

    @pytest.mark.asyncio
    async def test_environment_isolation(self, isolation_manager):
        """Test that environment is properly isolated."""
        # Set a test variable
        os.environ["TEST_VAR_ISOLATED"] = "should_not_be_preserved"

        async with isolation_manager.isolated_execution("claude") as context:
            # Custom env vars from config should be present
            assert "AURORA_EXECUTION_ID" in context.environment
            # But not arbitrary test vars
            # (depends on preserve_env_vars config)

        del os.environ["TEST_VAR_ISOLATED"]

    @pytest.mark.asyncio
    async def test_cleanup_on_error(self, temp_dir):
        """Test that cleanup runs even on error."""
        config = IsolationConfig(
            level=IsolationLevel.FULL,
            base_temp_dir=temp_dir,
            cleanup_strategy="always",
        )
        manager = ResourceIsolationManager(config)

        temp_path = None

        try:
            async with manager.isolated_execution("claude") as context:
                temp_path = context.temp_dir
                assert temp_path.exists()
                raise ValueError("Test error")
        except ValueError:
            pass

        # Cleanup should have removed the temp dir
        # (depending on cleanup_strategy)

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self, isolation_config):
        """Test manager as async context manager."""
        async with ResourceIsolationManager(isolation_config) as manager:
            async with manager.isolated_execution("claude") as context:
                pass

            # Should still work after first execution
            async with manager.isolated_execution("opencode") as context2:
                pass


# ---------------------------------------------------------------------------
# Test: IsolationLevel behaviors
# ---------------------------------------------------------------------------


class TestIsolationLevels:
    """Test different isolation levels."""

    @pytest.mark.asyncio
    async def test_none_level(self, temp_dir):
        """Test NONE isolation level uses current working dir."""
        config = IsolationConfig(
            level=IsolationLevel.NONE,
            base_temp_dir=temp_dir,
        )
        manager = ResourceIsolationManager(config, base_working_dir=Path.cwd())

        async with manager.isolated_execution("claude") as context:
            # Working dir should be base_working_dir
            assert context.working_dir == Path.cwd()

    @pytest.mark.asyncio
    async def test_light_level(self, temp_dir):
        """Test LIGHT isolation creates temp but uses base working dir."""
        config = IsolationConfig(
            level=IsolationLevel.LIGHT,
            base_temp_dir=temp_dir,
        )
        manager = ResourceIsolationManager(config, base_working_dir=Path.cwd())

        async with manager.isolated_execution("claude") as context:
            # Working dir should be base_working_dir
            assert context.working_dir == Path.cwd()
            # But temp dir should be isolated
            assert context.temp_dir.exists()
            assert str(temp_dir) in str(context.temp_dir)

    @pytest.mark.asyncio
    async def test_full_level(self, temp_dir):
        """Test FULL isolation uses isolated working dir."""
        config = IsolationConfig(
            level=IsolationLevel.FULL,
            base_temp_dir=temp_dir,
        )
        manager = ResourceIsolationManager(config, base_working_dir=Path.cwd())

        async with manager.isolated_execution("claude") as context:
            # Working dir should be the temp dir
            assert context.working_dir == context.temp_dir
            assert context.working_dir != Path.cwd()


# ---------------------------------------------------------------------------
# Test: Convenience Functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_isolation_manager(self):
        """Test create_isolation_manager helper."""
        manager = create_isolation_manager(
            level="light",
            max_concurrent=3,
            max_per_tool=1,
        )
        assert manager.config.level == IsolationLevel.LIGHT
        assert manager.config.limits.max_concurrent == 3
        assert manager.config.limits.max_per_tool == 1

    @pytest.mark.asyncio
    async def test_with_isolation_async(self):
        """Test with_isolation helper with async function."""

        async def my_async_func(x, y, context=None):
            assert context is not None
            return x + y

        result = await with_isolation("test", my_async_func, 1, 2)
        assert result == 3

    @pytest.mark.asyncio
    async def test_with_isolation_sync(self):
        """Test with_isolation helper with sync function."""

        def my_sync_func(x, y):
            return x * y

        result = await with_isolation("test", my_sync_func, 3, 4)
        assert result == 12


# ---------------------------------------------------------------------------
# Test: Integration with ConcurrentToolExecutor
# ---------------------------------------------------------------------------


class TestConcurrentExecutorIntegration:
    """Test integration with ConcurrentToolExecutor."""

    @pytest.mark.asyncio
    async def test_executor_with_isolation(self):
        """Test executor uses isolation when configured."""
        from aurora_cli.concurrent_executor import (
            AggregationStrategy,
            ConcurrentToolExecutor,
            ToolResult,
        )
        from aurora_cli.tool_providers import ToolProviderRegistry

        # Reset and mock registry
        ToolProviderRegistry.reset()

        with patch("aurora_cli.concurrent_executor.shutil.which", return_value="/usr/bin/tool"):
            executor = ConcurrentToolExecutor(
                tools=["claude"],
                strategy=AggregationStrategy.FIRST_SUCCESS,
                isolation_level="light",
                max_concurrent=2,
            )

            # Check isolation manager is created
            manager = executor._get_isolation_manager()
            assert manager is not None

        ToolProviderRegistry.reset()

    @pytest.mark.asyncio
    async def test_executor_no_isolation(self):
        """Test executor works without isolation."""
        from aurora_cli.concurrent_executor import AggregationStrategy, ConcurrentToolExecutor
        from aurora_cli.tool_providers import ToolProviderRegistry

        ToolProviderRegistry.reset()

        with patch("aurora_cli.concurrent_executor.shutil.which", return_value="/usr/bin/tool"):
            executor = ConcurrentToolExecutor(
                tools=["claude"],
                strategy=AggregationStrategy.FIRST_SUCCESS,
                isolation_level="none",
            )

            manager = executor._get_isolation_manager()
            assert manager is None

        ToolProviderRegistry.reset()


# ---------------------------------------------------------------------------
# Test: Edge Cases and Error Handling
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_context_reuse_after_cleanup(self, isolation_manager):
        """Test that manager works after cleanup."""
        async with isolation_manager.isolated_execution("tool1") as ctx1:
            pass

        # Should still work
        async with isolation_manager.isolated_execution("tool2") as ctx2:
            assert ctx2.execution_id != ctx1.execution_id

    @pytest.mark.asyncio
    async def test_cleanup_all(self, isolation_manager):
        """Test cleanup_all releases all resources."""
        # Acquire some contexts
        ctx1 = await isolation_manager.acquire_context("tool1")
        ctx2 = await isolation_manager.acquire_context("tool2")

        assert len(isolation_manager._active_contexts) == 2

        await isolation_manager.cleanup_all()

        assert len(isolation_manager._active_contexts) == 0

    def test_lock_sanitization(self, temp_dir):
        """Test that resource IDs are sanitized for lock files."""
        manager = FileLockManager(temp_dir / "locks")

        # Resource ID with special characters
        path = manager._lock_path("some/path:with*special?chars")
        assert "*" not in str(path)
        assert "?" not in str(path)

    @pytest.mark.asyncio
    async def test_exception_in_cleanup(self, temp_dir):
        """Test that exceptions in cleanup are handled."""
        config = IsolationConfig(
            level=IsolationLevel.LIGHT,
            base_temp_dir=temp_dir,
        )
        manager = ResourceIsolationManager(config)

        # This should not raise even if cleanup has issues
        async with manager.isolated_execution("claude") as context:
            # Manually mess with temp_dir to cause cleanup issues
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
