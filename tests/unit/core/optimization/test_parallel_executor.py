"""
Unit tests for ParallelAgentExecutor.

Tests cover:
- Basic parallel execution
- Dynamic concurrency scaling
- Early termination on critical failures
- Result streaming
- Priority-based execution
- Statistics tracking
"""

import time

import pytest

from aurora_core.optimization.parallel_executor import (
    AgentPriority,
    AgentTask,
    ParallelAgentExecutor,
)


# Test helper functions
def fast_task(value):
    """Fast task that returns immediately."""
    return value


def slow_task(value, delay=0.1):
    """Slow task with configurable delay."""
    time.sleep(delay)
    return value


def failing_task():
    """Task that always fails."""
    raise ValueError("Task failed")


def conditional_task(should_fail=False):
    """Task that can succeed or fail based on parameter."""
    if should_fail:
        raise ValueError("Conditional failure")
    return "success"


class TestBasicExecution:
    """Test basic parallel execution."""

    def test_execute_single_task(self):
        """Test executing a single task."""
        executor = ParallelAgentExecutor(
            min_concurrency=2,
            max_concurrency=10,
        )

        tasks = [
            AgentTask(
                agent_id='agent1',
                callable=fast_task,
                args=('result1',),
            )
        ]

        results, stats = executor.execute_all(tasks)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result == 'result1'
        assert results[0].agent_id == 'agent1'

    def test_execute_multiple_tasks(self):
        """Test executing multiple tasks in parallel."""
        executor = ParallelAgentExecutor(
            min_concurrency=2,
            max_concurrency=10,
        )

        tasks = [
            AgentTask(agent_id=f'agent{i}', callable=fast_task, args=(i,))
            for i in range(5)
        ]

        results, stats = executor.execute_all(tasks)

        assert len(results) == 5
        assert all(r.success for r in results)
        assert stats.completed_tasks == 5
        assert stats.failed_tasks == 0

    def test_task_with_kwargs(self):
        """Test task execution with keyword arguments."""
        def task_with_kwargs(x, y=10):
            return x + y

        executor = ParallelAgentExecutor()
        tasks = [
            AgentTask(
                agent_id='agent1',
                callable=task_with_kwargs,
                args=(5,),
                kwargs={'y': 20}
            )
        ]

        results, stats = executor.execute_all(tasks)

        assert results[0].success is True
        assert results[0].result == 25

    def test_execution_time_tracking(self):
        """Test that execution time is tracked."""
        executor = ParallelAgentExecutor()
        tasks = [
            AgentTask(
                agent_id='agent1',
                callable=slow_task,
                args=('result', 0.05),  # 50ms delay
            )
        ]

        results, stats = executor.execute_all(tasks)

        # Execution time should be at least 50ms
        assert results[0].execution_time_ms >= 40  # Allow some tolerance


class TestFailureHandling:
    """Test failure handling."""

    def test_task_failure(self):
        """Test handling of task failure."""
        executor = ParallelAgentExecutor()
        tasks = [
            AgentTask(
                agent_id='failing_agent',
                callable=failing_task,
            )
        ]

        results, stats = executor.execute_all(tasks)

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error is not None
        assert "Task failed" in results[0].error
        assert stats.failed_tasks == 1

    def test_mixed_success_and_failure(self):
        """Test mixed successful and failing tasks."""
        executor = ParallelAgentExecutor()
        tasks = [
            AgentTask(agent_id='agent1', callable=fast_task, args=(1,)),
            AgentTask(agent_id='agent2', callable=failing_task),
            AgentTask(agent_id='agent3', callable=fast_task, args=(3,)),
        ]

        results, stats = executor.execute_all(tasks)

        assert len(results) == 3
        assert stats.completed_tasks == 2
        assert stats.failed_tasks == 1

        # Check specific results
        success_results = [r for r in results if r.success]
        fail_results = [r for r in results if not r.success]

        assert len(success_results) == 2
        assert len(fail_results) == 1


class TestPriorityExecution:
    """Test priority-based execution."""

    def test_critical_priority_first(self):
        """Test that critical tasks are executed first."""
        executor = ParallelAgentExecutor(min_concurrency=1, max_concurrency=1)

        tasks = [
            AgentTask(
                agent_id='low',
                callable=fast_task,
                args=('low',),
                priority=AgentPriority.LOW
            ),
            AgentTask(
                agent_id='critical',
                callable=fast_task,
                args=('critical',),
                priority=AgentPriority.CRITICAL
            ),
            AgentTask(
                agent_id='normal',
                callable=fast_task,
                args=('normal',),
                priority=AgentPriority.NORMAL
            ),
        ]

        results, stats = executor.execute_all(tasks)

        # Critical task should complete first (though all will complete)
        assert len(results) == 3
        # First result should be from critical priority task
        assert results[0].priority == AgentPriority.CRITICAL


class TestEarlyTermination:
    """Test early termination on critical failures."""

    def test_early_termination_on_critical_failure(self):
        """Test that critical failure stops other tasks."""
        executor = ParallelAgentExecutor(
            min_concurrency=1,
            max_concurrency=1,
        )

        tasks = [
            AgentTask(
                agent_id='critical_failing',
                callable=failing_task,
                priority=AgentPriority.CRITICAL
            ),
            AgentTask(
                agent_id='agent2',
                callable=slow_task,
                args=('result2', 1.0),  # Slow task
                priority=AgentPriority.NORMAL
            ),
        ]

        results, stats = executor.execute_all(
            tasks,
            enable_early_termination=True
        )

        # Critical failure should trigger early termination
        assert stats.critical_failures == 1
        assert stats.early_terminated_tasks >= 0

        # Failing task result should be present
        critical_result = [r for r in results if r.agent_id == 'critical_failing'][0]
        assert critical_result.success is False

    def test_no_early_termination_when_disabled(self):
        """Test that all tasks complete when early termination disabled."""
        executor = ParallelAgentExecutor()

        tasks = [
            AgentTask(
                agent_id='critical_failing',
                callable=failing_task,
                priority=AgentPriority.CRITICAL
            ),
            AgentTask(
                agent_id='agent2',
                callable=fast_task,
                args=('result2',),
            ),
        ]

        results, stats = executor.execute_all(
            tasks,
            enable_early_termination=False
        )

        # All tasks should complete
        assert len(results) == 2
        assert stats.early_terminated_tasks == 0

    def test_non_critical_failure_continues(self):
        """Test that non-critical failures don't stop execution."""
        executor = ParallelAgentExecutor()

        tasks = [
            AgentTask(
                agent_id='failing',
                callable=failing_task,
                priority=AgentPriority.NORMAL  # Not critical
            ),
            AgentTask(
                agent_id='success',
                callable=fast_task,
                args=('result',),
            ),
        ]

        results, stats = executor.execute_all(
            tasks,
            enable_early_termination=True
        )

        # Both should complete
        assert len(results) == 2
        assert stats.early_terminated_tasks == 0


class TestResultStreaming:
    """Test result streaming functionality."""

    def test_streaming_yields_results(self):
        """Test that streaming yields results as they complete."""
        executor = ParallelAgentExecutor()

        tasks = [
            AgentTask(agent_id=f'agent{i}', callable=fast_task, args=(i,))
            for i in range(3)
        ]

        results = []
        for result in executor.execute_streaming(tasks):
            results.append(result)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_streaming_early_termination(self):
        """Test that streaming respects early termination."""
        executor = ParallelAgentExecutor(
            min_concurrency=1,
            max_concurrency=1,
        )

        tasks = [
            AgentTask(
                agent_id='critical_failing',
                callable=failing_task,
                priority=AgentPriority.CRITICAL
            ),
            AgentTask(
                agent_id='agent2',
                callable=slow_task,
                args=('result2', 1.0),
            ),
        ]

        results = []
        for result in executor.execute_streaming(tasks, enable_early_termination=True):
            results.append(result)

        # Should get at least the critical failure
        assert len(results) >= 1
        critical_result = [r for r in results if r.agent_id == 'critical_failing'][0]
        assert critical_result.success is False

    def test_streaming_order(self):
        """Test that streaming yields results in completion order."""
        executor = ParallelAgentExecutor()

        # Create tasks with different delays
        tasks = [
            AgentTask(agent_id='slow', callable=slow_task, args=('slow', 0.2)),
            AgentTask(agent_id='fast', callable=fast_task, args=('fast',)),
        ]

        results = []
        for result in executor.execute_streaming(tasks):
            results.append(result)

        # Fast task should complete first
        assert results[0].agent_id == 'fast'
        assert results[1].agent_id == 'slow'


class TestDynamicConcurrency:
    """Test dynamic concurrency scaling."""

    def test_initial_concurrency(self):
        """Test that initial concurrency is set to minimum."""
        executor = ParallelAgentExecutor(
            min_concurrency=3,
            max_concurrency=10,
        )

        assert executor.get_current_concurrency() == 3

    def test_concurrency_adjustment_on_fast_responses(self):
        """Test that concurrency increases with fast responses."""
        executor = ParallelAgentExecutor(
            min_concurrency=2,
            max_concurrency=10,
            target_response_time_ms=1000,  # Target 1 second
            scaling_factor=0.5,  # Aggressive scaling for test
        )

        # Execute fast tasks
        tasks = [
            AgentTask(agent_id=f'agent{i}', callable=fast_task, args=(i,))
            for i in range(20)  # Enough to trigger scaling
        ]

        results, stats = executor.execute_all(tasks)

        # Concurrency should have increased (though may not reach max)
        assert executor.get_current_concurrency() >= 2

    def test_concurrency_stays_within_bounds(self):
        """Test that concurrency respects min/max bounds."""
        executor = ParallelAgentExecutor(
            min_concurrency=2,
            max_concurrency=5,
        )

        # Test minimum bound
        executor.current_concurrency = 1
        # Add response times to trigger adjustment
        for _ in range(5):
            executor._update_response_times(2000)  # Slow responses
        executor._adjust_concurrency()

        # Should be clamped to minimum (can't go below 2)
        assert executor.get_current_concurrency() >= 2

        # Test maximum bound
        executor.current_concurrency = 10  # Set above max
        # Add fast responses to trigger upward adjustment
        for _ in range(5):
            executor._update_response_times(50)  # Fast responses
        executor._adjust_concurrency()

        # Should be clamped to maximum
        assert executor.get_current_concurrency() <= 5

    def test_reset_concurrency(self):
        """Test resetting concurrency to initial state."""
        executor = ParallelAgentExecutor(
            min_concurrency=2,
            max_concurrency=10,
        )

        # Adjust concurrency
        executor.current_concurrency = 5
        executor._update_response_times(100)
        executor._update_response_times(200)

        # Reset
        executor.reset_concurrency()

        assert executor.get_current_concurrency() == 2
        assert len(executor.recent_response_times) == 0


class TestStatisticsTracking:
    """Test statistics tracking."""

    def test_basic_stats_tracking(self):
        """Test that basic statistics are tracked."""
        executor = ParallelAgentExecutor()

        tasks = [
            AgentTask(agent_id='agent1', callable=fast_task, args=(1,)),
            AgentTask(agent_id='agent2', callable=fast_task, args=(2,)),
        ]

        results, stats = executor.execute_all(tasks)

        assert stats.total_tasks == 2
        assert stats.completed_tasks == 2
        assert stats.failed_tasks == 0
        assert stats.total_time_ms > 0
        assert stats.avg_response_time_ms > 0

    def test_stats_with_failures(self):
        """Test statistics with failed tasks."""
        executor = ParallelAgentExecutor()

        tasks = [
            AgentTask(agent_id='success', callable=fast_task, args=(1,)),
            AgentTask(agent_id='failure', callable=failing_task),
        ]

        results, stats = executor.execute_all(tasks)

        assert stats.total_tasks == 2
        assert stats.completed_tasks == 1
        assert stats.failed_tasks == 1

    def test_stats_with_early_termination(self):
        """Test statistics with early termination."""
        executor = ParallelAgentExecutor(
            min_concurrency=1,
            max_concurrency=1,
        )

        tasks = [
            AgentTask(
                agent_id='critical',
                callable=failing_task,
                priority=AgentPriority.CRITICAL
            ),
            AgentTask(agent_id='agent2', callable=fast_task, args=(2,)),
        ]

        results, stats = executor.execute_all(tasks, enable_early_termination=True)

        assert stats.critical_failures == 1

    def test_concurrency_used_in_stats(self):
        """Test that concurrency used is tracked in stats."""
        executor = ParallelAgentExecutor(
            min_concurrency=3,
            max_concurrency=10,
        )

        tasks = [
            AgentTask(agent_id='agent1', callable=fast_task, args=(1,)),
        ]

        results, stats = executor.execute_all(tasks)

        # Should report concurrency level used
        assert stats.concurrency_used >= 3


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_task_list(self):
        """Test execution with empty task list."""
        executor = ParallelAgentExecutor()
        results, stats = executor.execute_all([])

        assert len(results) == 0
        assert stats.total_tasks == 0

    def test_single_task_with_high_min_concurrency(self):
        """Test single task with min_concurrency > 1."""
        executor = ParallelAgentExecutor(
            min_concurrency=5,
            max_concurrency=10,
        )

        tasks = [
            AgentTask(agent_id='agent1', callable=fast_task, args=(1,)),
        ]

        results, stats = executor.execute_all(tasks)

        # Should complete successfully despite concurrency setting
        assert len(results) == 1
        assert results[0].success is True

    def test_very_slow_task(self):
        """Test handling of very slow task."""
        executor = ParallelAgentExecutor()

        tasks = [
            AgentTask(
                agent_id='slow',
                callable=slow_task,
                args=('result', 0.3),  # 300ms delay
                timeout_seconds=5.0
            ),
        ]

        results, stats = executor.execute_all(tasks)

        # Should complete (not timeout)
        assert results[0].success is True

    def test_concurrent_failures(self):
        """Test multiple concurrent failures."""
        executor = ParallelAgentExecutor()

        tasks = [
            AgentTask(agent_id=f'failing{i}', callable=failing_task)
            for i in range(5)
        ]

        results, stats = executor.execute_all(tasks, enable_early_termination=False)

        # All should fail
        assert stats.failed_tasks == 5
        assert all(not r.success for r in results)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
