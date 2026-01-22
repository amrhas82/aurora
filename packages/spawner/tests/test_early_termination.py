"""Tests for early termination logic with configurable timeout thresholds and retry policies."""

import time

import pytest

from aurora_spawner.models import SpawnResult, SpawnTask
from aurora_spawner.spawner import spawn, spawn_with_retry_and_fallback
from aurora_spawner.timeout_policy import (
    RetryPolicy,
    RetryStrategy,
    SpawnPolicy,
    TerminationPolicy,
    TimeoutMode,
    TimeoutPolicy,
)


@pytest.mark.asyncio
async def test_early_termination_on_error_pattern():
    """Test that process is terminated immediately on error pattern match."""
    task = SpawnTask(
        prompt="echo 'API error occurred' >&2; sleep 30",
        agent=None,
        timeout=60,
    )

    policy = SpawnPolicy(
        name="test",
        timeout_policy=TimeoutPolicy(mode=TimeoutMode.FIXED, timeout=60.0),
        termination_policy=TerminationPolicy(
            enabled=True,
            kill_on_error_patterns=True,
            error_patterns=[r"API.?error"],
        ),
    )

    start = time.time()
    result = await spawn(task, tool="bash", model="-c", policy=policy)
    elapsed = time.time() - start

    assert not result.success
    assert result.termination_reason is not None
    assert "error pattern" in result.termination_reason.lower()
    assert elapsed < 10  # Should terminate quickly, not wait 30s


@pytest.mark.asyncio
async def test_early_termination_on_no_activity():
    """Test that process is terminated on no activity timeout."""
    task = SpawnTask(
        prompt="echo 'start'; sleep 60",
        agent=None,
        timeout=120,
    )

    policy = SpawnPolicy(
        name="test",
        timeout_policy=TimeoutPolicy(
            mode=TimeoutMode.FIXED,
            timeout=120.0,
            no_activity_timeout=5.0,
            activity_check_interval=0.5,
        ),
        termination_policy=TerminationPolicy(
            enabled=True,
            kill_on_no_activity=True,
        ),
    )

    start = time.time()
    result = await spawn(task, tool="bash", model="-c", policy=policy)
    elapsed = time.time() - start

    assert not result.success
    assert result.termination_reason is not None
    assert "no activity" in result.termination_reason.lower()
    assert elapsed < 15  # Should terminate after ~5s of no activity


@pytest.mark.asyncio
async def test_progressive_timeout_extension():
    """Test that progressive timeout extends on activity."""
    task = SpawnTask(
        prompt="for i in {1..5}; do echo $i; sleep 2; done",
        agent=None,
        timeout=60,
    )

    policy = SpawnPolicy(
        name="test",
        timeout_policy=TimeoutPolicy(
            mode=TimeoutMode.PROGRESSIVE,
            initial_timeout=5.0,
            max_timeout=20.0,
            extension_threshold=3.0,
            activity_check_interval=0.5,
        ),
        termination_policy=TerminationPolicy(enabled=False),
    )

    start = time.time()
    result = await spawn(task, tool="bash", model="-c", policy=policy)
    elapsed = time.time() - start

    # Should complete successfully with extension
    assert result.success
    assert result.timeout_extended
    assert elapsed > 5  # Longer than initial timeout
    assert elapsed < 15  # But shorter than max timeout


@pytest.mark.asyncio
async def test_fixed_timeout_no_extension():
    """Test that fixed timeout mode does not extend."""
    task = SpawnTask(
        prompt="for i in {1..10}; do echo $i; sleep 1; done",
        agent=None,
        timeout=5,
    )

    policy = SpawnPolicy(
        name="test",
        timeout_policy=TimeoutPolicy(
            mode=TimeoutMode.FIXED,
            timeout=5.0,
            activity_check_interval=0.5,
        ),
        termination_policy=TerminationPolicy(kill_on_no_activity=False),
    )

    start = time.time()
    result = await spawn(task, tool="bash", model="-c", policy=policy)
    elapsed = time.time() - start

    assert not result.success
    assert result.termination_reason is not None
    assert "timed out" in result.termination_reason.lower()
    assert not result.timeout_extended
    assert elapsed >= 5 and elapsed < 8


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff():
    """Test retry logic with exponential backoff."""
    attempt_count = 0

    async def failing_spawn(task, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            return SpawnResult(
                success=False,
                output="",
                error="Transient error",
                exit_code=1,
            )
        return SpawnResult(
            success=True,
            output="Success on attempt 3",
            error=None,
            exit_code=0,
        )

    # Patch spawn function
    import aurora_spawner.spawner

    original_spawn = aurora_spawner.spawner.spawn
    aurora_spawner.spawner.spawn = failing_spawn

    try:
        task = SpawnTask(prompt="test", agent=None, timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=0.1,
                max_delay=1.0,
                backoff_factor=2.0,
                jitter=False,  # Disable jitter for predictable testing
            ),
        )

        start = time.time()
        result = await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=False)
        elapsed = time.time() - start

        assert result.success
        assert result.retry_count == 2  # Succeeded on 3rd attempt (index 2)
        # Should have delays: 0.1 + 0.2 = 0.3s
        assert elapsed >= 0.3
    finally:
        aurora_spawner.spawner.spawn = original_spawn


@pytest.mark.asyncio
async def test_retry_respects_max_attempts():
    """Test that retry stops after max attempts."""
    attempt_count = 0

    async def always_failing_spawn(task, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        return SpawnResult(
            success=False,
            output="",
            error=f"Failure {attempt_count}",
            exit_code=1,
        )

    # Patch spawn function
    import aurora_spawner.spawner

    original_spawn = aurora_spawner.spawner.spawn
    aurora_spawner.spawner.spawn = always_failing_spawn

    try:
        task = SpawnTask(prompt="test", agent=None, timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(
                max_attempts=3,
                strategy=RetryStrategy.IMMEDIATE,
                circuit_breaker_enabled=False,
            ),
        )

        result = await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=False)

        assert not result.success
        assert attempt_count == 3  # 3 attempts (initial + 2 retries)
        assert result.retry_count == 3
    finally:
        aurora_spawner.spawner.spawn = original_spawn


@pytest.mark.asyncio
async def test_retry_policy_no_retry_on_timeout():
    """Test that retry policy can disable retry on timeout errors."""
    attempt_count = 0

    async def timeout_spawn(task, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        return SpawnResult(
            success=False,
            output="",
            error="Process timed out",
            exit_code=-1,
            termination_reason="Process timed out after 60 seconds",
        )

    # Patch spawn function
    import aurora_spawner.spawner

    original_spawn = aurora_spawner.spawner.spawn
    aurora_spawner.spawner.spawn = timeout_spawn

    try:
        task = SpawnTask(prompt="test", agent=None, timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(
                max_attempts=3,
                strategy=RetryStrategy.IMMEDIATE,
                retry_on_timeout=False,  # Don't retry on timeout
                circuit_breaker_enabled=False,
            ),
        )

        result = await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=False)

        assert not result.success
        assert attempt_count == 1  # Only initial attempt, no retries
    finally:
        aurora_spawner.spawner.spawn = original_spawn


@pytest.mark.asyncio
async def test_retry_with_linear_backoff():
    """Test retry logic with linear backoff."""

    async def track_delays_spawn(task, **kwargs):
        return SpawnResult(
            success=False,
            output="",
            error="Failure",
            exit_code=1,
        )

    # Patch spawn function
    import aurora_spawner.spawner

    original_spawn = aurora_spawner.spawner.spawn
    aurora_spawner.spawner.spawn = track_delays_spawn

    try:
        task = SpawnTask(prompt="test", agent=None, timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(
                max_attempts=4,
                strategy=RetryStrategy.LINEAR_BACKOFF,
                base_delay=0.1,
                backoff_factor=1.0,
                jitter=False,
            ),
        )

        start = time.time()
        await spawn_with_retry_and_fallback(task, policy=policy, fallback_to_llm=False)
        elapsed = time.time() - start

        # Linear backoff: 0.1 * (1 + 1*0) = 0.1, 0.1 * (1 + 1*1) = 0.2, 0.1 * (1 + 1*2) = 0.3
        # Total: 0.1 + 0.2 + 0.3 = 0.6s
        assert elapsed >= 0.6
    finally:
        aurora_spawner.spawner.spawn = original_spawn


@pytest.mark.asyncio
async def test_policy_presets():
    """Test that policy presets are properly configured."""
    # Test default policy
    default = SpawnPolicy.default()
    assert default.timeout_policy.mode == TimeoutMode.PROGRESSIVE
    assert default.retry_policy.max_attempts == 3
    assert default.termination_policy.enabled

    # Test production policy
    prod = SpawnPolicy.production()
    assert prod.timeout_policy.initial_timeout == 120.0
    assert prod.timeout_policy.max_timeout == 600.0
    assert not prod.termination_policy.kill_on_no_activity

    # Test fast fail policy
    fast_fail = SpawnPolicy.fast_fail()
    assert fast_fail.timeout_policy.mode == TimeoutMode.FIXED
    assert fast_fail.timeout_policy.timeout == 60.0
    assert fast_fail.retry_policy.max_attempts == 1

    # Test development policy
    dev = SpawnPolicy.development()
    assert dev.timeout_policy.timeout == 1800.0
    assert not dev.termination_policy.enabled

    # Test test policy
    test = SpawnPolicy.test()
    assert test.timeout_policy.timeout == 30.0
    assert test.retry_policy.max_attempts == 1


@pytest.mark.asyncio
async def test_custom_termination_predicate():
    """Test custom termination predicate."""

    # Custom predicate that terminates if stdout contains "ABORT"
    def abort_predicate(stdout: str, stderr: str) -> bool:
        return "ABORT" in stdout

    task = SpawnTask(
        prompt="echo 'Processing...'; echo 'ABORT'; sleep 30",
        agent=None,
        timeout=60,
    )

    policy = SpawnPolicy(
        name="test",
        timeout_policy=TimeoutPolicy(mode=TimeoutMode.FIXED, timeout=60.0),
        termination_policy=TerminationPolicy(
            enabled=True,
            custom_predicates=[abort_predicate],
        ),
    )

    start = time.time()
    result = await spawn(task, tool="bash", model="-c", policy=policy)
    elapsed = time.time() - start

    assert not result.success
    assert result.termination_reason is not None
    assert "custom termination" in result.termination_reason.lower()
    assert elapsed < 10


@pytest.mark.asyncio
async def test_max_retries_override():
    """Test that max_retries parameter overrides policy."""
    attempt_count = 0

    async def counting_spawn(task, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        return SpawnResult(
            success=False,
            output="",
            error="Failure",
            exit_code=1,
        )

    # Patch spawn function
    import aurora_spawner.spawner

    original_spawn = aurora_spawner.spawner.spawn
    aurora_spawner.spawner.spawn = counting_spawn

    try:
        task = SpawnTask(prompt="test", agent=None, timeout=60)
        policy = SpawnPolicy(
            name="test",
            retry_policy=RetryPolicy(
                max_attempts=5,  # Policy says 5
                strategy=RetryStrategy.IMMEDIATE,
                circuit_breaker_enabled=False,
            ),
        )

        # But override to 2 retries (3 total attempts)
        result = await spawn_with_retry_and_fallback(
            task,
            max_retries=2,
            policy=policy,
            fallback_to_llm=False,
        )

        assert not result.success
        assert attempt_count == 3  # Honored the override, not policy
    finally:
        aurora_spawner.spawner.spawn = original_spawn
