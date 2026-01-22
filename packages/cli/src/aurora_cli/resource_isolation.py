"""Resource isolation for concurrent tool execution.

Provides mechanisms for running multiple AI tools in parallel with proper
resource isolation to prevent interference between concurrent executions.

Features:
- Working directory isolation (temporary per-execution directories)
- Environment variable isolation
- Semaphore-based concurrency limiting
- File locking for shared resources
- Automatic cleanup on completion or failure

Example usage:
    async with ResourceIsolationManager(max_concurrent=3) as manager:
        context = await manager.acquire_context("claude")
        async with context:
            # Execute tool with isolated resources
            result = await run_tool_with_context(context)
"""

from __future__ import annotations

import asyncio
import fcntl
import logging
import os
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable


logger = logging.getLogger(__name__)


class IsolationLevel(Enum):
    """Level of resource isolation for tool execution."""

    # No isolation - use shared working directory
    NONE = "none"

    # Light isolation - isolated temp dir, shared env
    LIGHT = "light"

    # Full isolation - isolated working dir, env, and file locks
    FULL = "full"

    # Container isolation (future) - run in isolated container
    CONTAINER = "container"


@dataclass
class ResourceLimits:
    """Resource limits for tool execution."""

    # Maximum concurrent executions across all tools
    max_concurrent: int = 5

    # Maximum concurrent executions per tool type
    max_per_tool: int = 2

    # Maximum memory per execution (bytes, 0 = unlimited)
    max_memory: int = 0

    # Maximum file descriptors per execution
    max_file_descriptors: int = 256

    # Maximum temporary disk usage (bytes, 0 = unlimited)
    max_temp_disk: int = 0


@dataclass
class IsolationConfig:
    """Configuration for resource isolation."""

    level: IsolationLevel = IsolationLevel.LIGHT

    # Base directory for isolated working dirs
    base_temp_dir: Path | None = None

    # Environment variables to preserve (others are filtered)
    preserve_env_vars: list[str] = field(
        default_factory=lambda: [
            "PATH",
            "HOME",
            "USER",
            "SHELL",
            "TERM",
            "LANG",
            "LC_ALL",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GOOGLE_API_KEY",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION",
            "AURORA_*",
            "CLAUDE_*",
        ],
    )

    # Environment variables to explicitly set
    extra_env_vars: dict[str, str] = field(default_factory=dict)

    # Files/directories to copy into isolated working dir
    copy_paths: list[Path] = field(default_factory=list)

    # Files/directories to symlink into isolated working dir
    symlink_paths: list[Path] = field(default_factory=list)

    # Cleanup strategy: "always", "on_success", "never"
    cleanup_strategy: str = "always"

    # Resource limits
    limits: ResourceLimits = field(default_factory=ResourceLimits)


@dataclass
class ExecutionContext:
    """Context for an isolated tool execution.

    Provides all the resources needed for isolated execution including
    working directory, environment, and cleanup tracking.
    """

    # Unique identifier for this execution
    execution_id: str

    # Tool being executed
    tool_name: str

    # Isolated working directory
    working_dir: Path

    # Environment variables for this execution
    environment: dict[str, str]

    # Temp directory for this execution (may be same as working_dir)
    temp_dir: Path

    # Lock file for shared resource coordination
    lock_file: Path | None = None

    # Cleanup callback
    cleanup_callback: Callable[[], None] | None = None

    # Whether execution succeeded (for cleanup strategy)
    success: bool | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def __enter__(self) -> ExecutionContext:
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and trigger cleanup."""
        self.success = exc_type is None
        if self.cleanup_callback:
            try:
                self.cleanup_callback()
            except Exception as e:
                logger.warning(f"Cleanup failed for {self.execution_id}: {e}")

    async def __aenter__(self) -> ExecutionContext:
        """Async enter context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async exit context manager."""
        self.success = exc_type is None
        if self.cleanup_callback:
            try:
                self.cleanup_callback()
            except Exception as e:
                logger.warning(f"Cleanup failed for {self.execution_id}: {e}")


class FileLockManager:
    """Manages file-based locks for shared resource coordination.

    Uses fcntl for POSIX file locking to coordinate access to shared
    resources like databases, caches, or config files.
    """

    def __init__(self, lock_dir: Path | None = None):
        """Initialize lock manager.

        Args:
            lock_dir: Directory for lock files (default: system temp)

        """
        self.lock_dir = lock_dir or Path(tempfile.gettempdir()) / "aurora_locks"
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self._held_locks: dict[str, int] = {}  # resource_id -> fd

    def _lock_path(self, resource_id: str) -> Path:
        """Get lock file path for a resource."""
        # Sanitize resource_id for filename
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in resource_id)
        return self.lock_dir / f"{safe_id}.lock"

    @contextmanager
    def lock(self, resource_id: str, exclusive: bool = True, timeout: float = 30.0):
        """Acquire a lock on a resource.

        Args:
            resource_id: Unique identifier for the resource
            exclusive: True for exclusive lock, False for shared
            timeout: Maximum time to wait for lock (seconds)

        Yields:
            Lock file path

        """
        import time as time_module

        lock_path = self._lock_path(resource_id)
        lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fd = None

        try:
            # Create/open lock file
            fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)

            # Try to acquire lock with timeout (using time.time, not asyncio)
            deadline = time_module.time() + timeout if timeout > 0 else float("inf")

            while True:
                try:
                    fcntl.flock(fd, lock_type | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time_module.time() >= deadline:
                        raise TimeoutError(f"Timeout acquiring lock for {resource_id}")
                    time_module.sleep(0.1)

            self._held_locks[resource_id] = fd
            logger.debug(f"Acquired lock for {resource_id}")

            yield lock_path

        finally:
            if fd is not None and resource_id in self._held_locks:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    os.close(fd)
                    del self._held_locks[resource_id]
                    logger.debug(f"Released lock for {resource_id}")
                except Exception as e:
                    logger.warning(f"Error releasing lock for {resource_id}: {e}")

    @asynccontextmanager
    async def async_lock(self, resource_id: str, exclusive: bool = True, timeout: float = 30.0):
        """Async version of lock acquisition.

        Args:
            resource_id: Unique identifier for the resource
            exclusive: True for exclusive lock, False for shared
            timeout: Maximum time to wait for lock (seconds)

        Yields:
            Lock file path

        """
        lock_path = self._lock_path(resource_id)
        lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fd = None

        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)

            deadline = asyncio.get_event_loop().time() + timeout if timeout > 0 else float("inf")

            while True:
                try:
                    fcntl.flock(fd, lock_type | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if asyncio.get_event_loop().time() >= deadline:
                        raise TimeoutError(f"Timeout acquiring lock for {resource_id}")
                    await asyncio.sleep(0.1)

            self._held_locks[resource_id] = fd
            logger.debug(f"Acquired async lock for {resource_id}")

            yield lock_path

        finally:
            if fd is not None and resource_id in self._held_locks:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    os.close(fd)
                    del self._held_locks[resource_id]
                    logger.debug(f"Released async lock for {resource_id}")
                except Exception as e:
                    logger.warning(f"Error releasing async lock for {resource_id}: {e}")

    def cleanup(self) -> None:
        """Release all held locks and cleanup lock files."""
        for resource_id in list(self._held_locks.keys()):
            try:
                fd = self._held_locks.pop(resource_id)
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
            except Exception as e:
                logger.warning(f"Error cleaning up lock {resource_id}: {e}")


class ResourceIsolationManager:
    """Manages resource isolation for concurrent tool executions.

    Provides:
    - Semaphore-based concurrency control
    - Working directory isolation
    - Environment isolation
    - File locking for shared resources
    - Automatic cleanup
    """

    def __init__(
        self,
        config: IsolationConfig | None = None,
        base_working_dir: Path | None = None,
    ):
        """Initialize resource isolation manager.

        Args:
            config: Isolation configuration
            base_working_dir: Base working directory for isolated executions

        """
        self.config = config or IsolationConfig()
        self.base_working_dir = base_working_dir or Path.cwd()

        # Semaphores for concurrency control
        self._global_semaphore = asyncio.Semaphore(self.config.limits.max_concurrent)
        self._tool_semaphores: dict[str, asyncio.Semaphore] = {}

        # File lock manager
        self._lock_manager = FileLockManager(self.config.base_temp_dir)

        # Track active contexts for cleanup
        self._active_contexts: dict[str, ExecutionContext] = {}

        # Base environment (filtered from current env)
        self._base_environment = self._build_base_environment()

    def _build_base_environment(self) -> dict[str, str]:
        """Build base environment by filtering current env."""
        env = {}
        preserve_patterns = self.config.preserve_env_vars

        for key, value in os.environ.items():
            for pattern in preserve_patterns:
                if pattern.endswith("*"):
                    if key.startswith(pattern[:-1]):
                        env[key] = value
                        break
                elif key == pattern:
                    env[key] = value
                    break

        # Add any extra env vars
        env.update(self.config.extra_env_vars)

        return env

    def _get_tool_semaphore(self, tool_name: str) -> asyncio.Semaphore:
        """Get or create semaphore for a specific tool."""
        if tool_name not in self._tool_semaphores:
            self._tool_semaphores[tool_name] = asyncio.Semaphore(self.config.limits.max_per_tool)
        return self._tool_semaphores[tool_name]

    async def _create_isolated_directory(self, execution_id: str) -> Path:
        """Create isolated working directory for execution."""
        base = self.config.base_temp_dir or Path(tempfile.gettempdir())
        isolated_dir = base / "aurora_isolated" / execution_id
        isolated_dir.mkdir(parents=True, exist_ok=True)

        # Copy specified paths
        for path in self.config.copy_paths:
            if path.exists():
                dest = isolated_dir / path.name
                if path.is_dir():
                    shutil.copytree(path, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(path, dest)

        # Create symlinks for specified paths
        for path in self.config.symlink_paths:
            if path.exists():
                dest = isolated_dir / path.name
                if not dest.exists():
                    dest.symlink_to(path.absolute())

        return isolated_dir

    def _cleanup_isolated_directory(self, context: ExecutionContext, cleanup_strategy: str) -> None:
        """Clean up isolated directory based on strategy."""
        should_cleanup = cleanup_strategy == "always" or (
            cleanup_strategy == "on_success" and context.success
        )

        if should_cleanup and context.temp_dir.exists():
            try:
                shutil.rmtree(context.temp_dir)
                logger.debug(f"Cleaned up isolated dir: {context.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {context.temp_dir}: {e}")

    async def acquire_context(
        self,
        tool_name: str,
        extra_env: dict[str, str] | None = None,
    ) -> ExecutionContext:
        """Acquire an execution context with isolated resources.

        This method:
        1. Acquires global and tool-specific semaphores
        2. Creates isolated working directory (if configured)
        3. Builds isolated environment
        4. Returns context with cleanup callback

        Args:
            tool_name: Name of the tool being executed
            extra_env: Additional environment variables for this execution

        Returns:
            ExecutionContext with isolated resources

        """
        execution_id = f"{tool_name}-{uuid.uuid4().hex[:8]}"

        # Acquire semaphores
        await self._global_semaphore.acquire()
        await self._get_tool_semaphore(tool_name).acquire()

        try:
            # Create isolated resources based on level
            if self.config.level == IsolationLevel.NONE:
                working_dir = self.base_working_dir
                temp_dir = Path(tempfile.gettempdir()) / "aurora_temp" / execution_id
                temp_dir.mkdir(parents=True, exist_ok=True)
            elif self.config.level in (IsolationLevel.LIGHT, IsolationLevel.FULL):
                temp_dir = await self._create_isolated_directory(execution_id)
                working_dir = (
                    temp_dir if self.config.level == IsolationLevel.FULL else self.base_working_dir
                )
            else:
                # Container level - not implemented, fall back to FULL
                temp_dir = await self._create_isolated_directory(execution_id)
                working_dir = temp_dir

            # Build environment
            environment = self._base_environment.copy()
            environment["AURORA_EXECUTION_ID"] = execution_id
            environment["AURORA_TOOL_NAME"] = tool_name
            environment["AURORA_TEMP_DIR"] = str(temp_dir)
            if extra_env:
                environment.update(extra_env)

            # Create lock file for shared resource coordination
            lock_file = temp_dir / ".aurora_lock" if temp_dir.exists() else None
            if lock_file:
                lock_file.touch()

            # Create cleanup callback
            def cleanup():
                # Release semaphores
                self._global_semaphore.release()
                self._get_tool_semaphore(tool_name).release()

                # Remove from active contexts
                self._active_contexts.pop(execution_id, None)

                # Cleanup directory if needed
                context = self._active_contexts.get(execution_id)
                if context:
                    self._cleanup_isolated_directory(context, self.config.cleanup_strategy)

            context = ExecutionContext(
                execution_id=execution_id,
                tool_name=tool_name,
                working_dir=working_dir,
                environment=environment,
                temp_dir=temp_dir,
                lock_file=lock_file,
                cleanup_callback=cleanup,
                metadata={"isolation_level": self.config.level.value},
            )

            self._active_contexts[execution_id] = context
            logger.debug(f"Created execution context {execution_id} for {tool_name}")

            return context

        except Exception:
            # Release semaphores on failure
            self._global_semaphore.release()
            self._get_tool_semaphore(tool_name).release()
            raise

    @asynccontextmanager
    async def isolated_execution(
        self,
        tool_name: str,
        extra_env: dict[str, str] | None = None,
    ):
        """Context manager for isolated tool execution.

        Usage:
            async with manager.isolated_execution("claude") as context:
                result = await run_tool(
                    working_dir=context.working_dir,
                    env=context.environment,
                )

        Args:
            tool_name: Name of the tool being executed
            extra_env: Additional environment variables

        Yields:
            ExecutionContext with isolated resources

        """
        context = await self.acquire_context(tool_name, extra_env)
        try:
            yield context
            context.success = True
        except Exception:
            context.success = False
            raise
        finally:
            if context.cleanup_callback:
                context.cleanup_callback()

    def get_lock_manager(self) -> FileLockManager:
        """Get the file lock manager for shared resource coordination."""
        return self._lock_manager

    def get_active_contexts(self) -> dict[str, ExecutionContext]:
        """Get currently active execution contexts."""
        return dict(self._active_contexts)

    async def cleanup_all(self) -> None:
        """Cleanup all active contexts and resources."""
        for execution_id, context in list(self._active_contexts.items()):
            try:
                if context.cleanup_callback:
                    context.cleanup_callback()
            except Exception as e:
                logger.warning(f"Error cleaning up context {execution_id}: {e}")

        self._lock_manager.cleanup()
        self._active_contexts.clear()

    async def __aenter__(self) -> ResourceIsolationManager:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.cleanup_all()


# Convenience functions


def create_isolation_manager(
    level: str = "light",
    max_concurrent: int = 5,
    max_per_tool: int = 2,
    **kwargs: Any,
) -> ResourceIsolationManager:
    """Create a ResourceIsolationManager with common defaults.

    Args:
        level: Isolation level ("none", "light", "full")
        max_concurrent: Maximum concurrent executions
        max_per_tool: Maximum concurrent executions per tool
        **kwargs: Additional config options

    Returns:
        Configured ResourceIsolationManager

    """
    config = IsolationConfig(
        level=IsolationLevel(level),
        limits=ResourceLimits(
            max_concurrent=max_concurrent,
            max_per_tool=max_per_tool,
        ),
        **{k: v for k, v in kwargs.items() if hasattr(IsolationConfig, k)},
    )
    return ResourceIsolationManager(config)


async def with_isolation(
    tool_name: str,
    func: Callable,
    *args: Any,
    isolation_level: str = "light",
    **kwargs: Any,
) -> Any:
    """Execute a function with resource isolation.

    Convenience wrapper that creates a temporary isolation context
    for a single function execution.

    Args:
        tool_name: Name of the tool being executed
        func: Async function to execute
        *args: Arguments to pass to func
        isolation_level: Level of isolation
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of func execution

    """
    manager = create_isolation_manager(level=isolation_level)

    async with manager:
        async with manager.isolated_execution(tool_name) as context:
            # Inject context if func accepts it
            import inspect

            sig = inspect.signature(func)
            if "context" in sig.parameters:
                kwargs["context"] = context
            elif "execution_context" in sig.parameters:
                kwargs["execution_context"] = context

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
