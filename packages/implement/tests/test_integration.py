"""Integration tests for implement package.

Tests end-to-end parser -> executor workflows.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from implement import TaskExecutor, TaskParser


def test_parser_executor_integration():
    """Parse then execute workflow."""
    content = """# Task List

- [ ] 1. First task
- [ ] 2. Second task
<!-- agent: self -->
- [x] 3. Already completed"""

    # Parse
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 3
    assert tasks[0].id == "1"
    assert tasks[1].id == "2"
    assert tasks[1].agent == "self"
    assert tasks[2].completed is True

    # Execute workflow would happen here (tested separately in test_executor.py)


@pytest.mark.asyncio
async def test_full_tasks_md_processing():
    """Complete tasks.md processing workflow."""
    content = """# Task List: Integration Test

## Tasks

- [ ] 1.0 Setup phase
  - [ ] 1.1 Create config
  - [ ] 1.2 Initialize services

- [ ] 2.0 Execute phase
<!-- agent: self -->
  - [ ] 2.1 Process data
  - [x] 2.2 Already done

- [ ] 3.0 Cleanup phase
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        tasks_file = Path(f.name)

    try:
        # Step 1: Parse tasks
        parser = TaskParser()
        tasks = parser.parse(content)

        assert len(tasks) == 7  # 3.0 is also parsed
        assert tasks[0].id == "1.0"
        assert tasks[1].id == "1.1"
        assert tasks[2].id == "1.2"
        assert tasks[3].id == "2.0"
        assert tasks[3].agent == "self"
        assert tasks[4].id == "2.1"
        assert tasks[5].id == "2.2"
        assert tasks[5].completed is True
        assert tasks[6].id == "3.0"

        # Step 2: Execute tasks (self-execution only for this test)
        executor = TaskExecutor()
        results = await executor.execute(tasks, tasks_file)

        # Verify results
        assert len(results) == 7
        # All but one (2.2 already completed) should be executed
        executed = [r for r in results if not r.skipped]
        assert len(executed) == 6

        # Verify tasks were marked complete in file
        updated_content = tasks_file.read_text()
        assert "- [x] 1.0 Setup phase" in updated_content
        assert "- [x] 1.1 Create config" in updated_content
        assert "- [x] 1.2 Initialize services" in updated_content
        assert "- [x] 2.0 Execute phase" in updated_content
        assert "- [x] 2.1 Process data" in updated_content
        assert "- [x] 2.2 Already done" in updated_content  # Was already [x]
        assert "- [x] 3.0 Cleanup phase" in updated_content

    finally:
        tasks_file.unlink()


@pytest.mark.asyncio
async def test_parser_executor_with_agent_dispatch():
    """Test parsing and executing with agent dispatch."""
    from aurora_spawner.models import SpawnResult

    content = """- [ ] 1. Task for agent
<!-- agent: full-stack-dev -->
<!-- model: sonnet -->

- [ ] 2. Self task
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        tasks_file = Path(f.name)

    try:
        # Parse
        parser = TaskParser()
        tasks = parser.parse(content)

        assert len(tasks) == 2
        assert tasks[0].agent == "full-stack-dev"
        assert tasks[0].model == "sonnet"
        assert tasks[1].agent == "self"

        # Mock spawner for agent task
        mock_result = SpawnResult(
            success=True,
            output="Agent completed the task",
            error=None,
            exit_code=0,
        )

        with patch("implement.executor.spawn", return_value=mock_result):
            executor = TaskExecutor()
            results = await executor.execute(tasks, tasks_file)

        # Verify both tasks executed
        assert len(results) == 2
        assert all(r.success for r in results)

        # Verify both marked complete
        updated_content = tasks_file.read_text()
        assert "- [x] 1. Task for agent" in updated_content
        assert "- [x] 2. Self task" in updated_content

    finally:
        tasks_file.unlink()


def test_parse_complex_real_world_example():
    """Parse a realistic complex tasks.md file."""
    content = """# Task List: Microservices Migration

## Phase 1: Infrastructure

- [ ] 1.0 Setup Kubernetes cluster
  - [x] 1.1 Configure ingress controller
  - [ ] 1.2 Setup monitoring
<!-- agent: holistic-architect -->
<!-- model: opus -->
  - [ ] 1.3 Deploy logging stack

## Phase 2: Service Migration

- [ ] 2.0 Migrate authentication service
<!-- agent: full-stack-dev -->
  - [ ] 2.1 Containerize service
  - [ ] 2.2 Write Helm charts
  - [ ] 2.3 Deploy to staging

- [ ] 3.0 Migrate API gateway
<!-- agent: full-stack-dev -->

## Phase 3: Testing

- [ ] 4.0 Integration testing
<!-- agent: qa-test-architect -->
  - [ ] 4.1 Write test scenarios
  - [ ] 4.2 Execute test suite
  - [ ] 4.3 Performance testing
"""

    parser = TaskParser()
    tasks = parser.parse(content)

    # Verify parsing (13 tasks found: 1.0-1.3, 2.0-2.3, 3.0, 4.0-4.3)
    assert len(tasks) == 13

    # Check specific tasks
    task_12 = [t for t in tasks if t.id == "1.2"][0]
    assert task_12.agent == "holistic-architect"
    assert task_12.model == "opus"

    task_20 = [t for t in tasks if t.id == "2.0"][0]
    assert task_20.agent == "full-stack-dev"

    task_40 = [t for t in tasks if t.id == "4.0"][0]
    assert task_40.agent == "qa-test-architect"

    # Verify completed status
    completed_tasks = [t for t in tasks if t.completed]
    assert len(completed_tasks) == 1
    assert completed_tasks[0].id == "1.1"
