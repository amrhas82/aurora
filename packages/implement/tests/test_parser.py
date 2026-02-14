"""Tests for TaskParser.

TDD RED Phase: These tests should fail initially until TaskParser is implemented.
"""

from implement.parser import TaskParser


def test_parse_empty_file():
    """Empty tasks.md returns empty list."""
    parser = TaskParser()
    tasks = parser.parse("")
    assert tasks == []


def test_parse_single_task():
    """Parse single uncompleted task."""
    content = "- [ ] 1. Implement feature X"
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 1
    assert tasks[0].id == "1"
    assert tasks[0].description == "Implement feature X"
    assert tasks[0].completed is False
    assert tasks[0].agent == "self"
    assert tasks[0].model is None


def test_parse_completed_task():
    """Parse completed task with [x] checkbox."""
    content = "- [x] 2. Fix bug Y"
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 1
    assert tasks[0].id == "2"
    assert tasks[0].description == "Fix bug Y"
    assert tasks[0].completed is True


def test_parse_agent_metadata():
    """Extract agent from markdown sub-bullet."""
    content = """- [ ] 1. Implement feature X
  - Agent: @code-developer"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 1
    assert tasks[0].agent == "code-developer"


def test_parse_model_metadata():
    """Extract model from markdown sub-bullet."""
    content = """- [ ] 1. Implement feature X
  - Model: sonnet"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 1
    assert tasks[0].model == "sonnet"


def test_parse_multiple_tasks():
    """Parse multiple tasks in correct order."""
    content = """- [ ] 1. First task
- [ ] 2. Second task
- [x] 3. Third task (completed)"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 3
    assert tasks[0].id == "1"
    assert tasks[0].description == "First task"
    assert tasks[1].id == "2"
    assert tasks[1].description == "Second task"
    assert tasks[2].id == "3"
    assert tasks[2].description == "Third task (completed)"
    assert tasks[2].completed is True


def test_parse_nested_subtasks():
    """Handle nested subtasks with indentation."""
    content = """- [ ] 1. Parent task
  - [ ] 1.1 Sub-task one
  - [ ] 1.2 Sub-task two
- [ ] 2. Another parent task"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 4
    assert tasks[0].id == "1"
    assert tasks[1].id == "1.1"
    assert tasks[1].description == "Sub-task one"
    assert tasks[2].id == "1.2"
    assert tasks[2].description == "Sub-task two"
    assert tasks[3].id == "2"


def test_parse_task_with_agent_after_blank_line():
    """Agent sub-bullet on separate line below task still applies."""
    content = """- [ ] 1. Implement feature X

  - Agent: @quality-assurance

- [ ] 2. Another task"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 2
    assert tasks[0].agent == "quality-assurance"
    assert tasks[1].agent == "self"


def test_parse_preserves_task_id():
    """Task IDs extracted correctly (1, 1.1, 2.3, etc.)."""
    content = """- [ ] 1. Task one
- [ ] 1.1. Subtask
- [ ] 2.3. Task two point three"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert tasks[0].id == "1"
    assert tasks[1].id == "1.1"
    assert tasks[2].id == "2.3"


def test_parse_default_agent_is_self():
    """Tasks without agent metadata default to 'self'."""
    content = """- [ ] 1. Task without agent
- [ ] 2. Another task"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert all(task.agent == "self" for task in tasks)


def test_parse_ignores_non_task_lines():
    """Section headers and notes are ignored."""
    content = """# Task List

This is a note.

## Section 1

- [ ] 1. Real task

Some more notes here.

- [ ] 2. Another real task

## Section 2"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 2
    assert tasks[0].id == "1"
    assert tasks[1].id == "2"


def test_parse_tasks_md_format():
    """Full example matching production tasks.md format."""
    content = """# Task List: Feature Implementation

## Tasks

- [ ] 1.0 Setup infrastructure
  - [x] 1.1 Create database schema
  - [ ] 1.2 Setup API endpoints
  - Agent: @code-developer
  - Model: sonnet

- [ ] 2.0 Implement UI
  - [ ] 2.1 Design wireframes
  - Agent: @ui-designer
  - [ ] 2.2 Build components
  - Agent: @code-developer

- [x] 3.0 Write tests
  - Agent: @quality-assurance"""
    parser = TaskParser()
    tasks = parser.parse(content)

    # Verify we parsed all tasks
    assert len(tasks) == 7

    # Task 1.0 and subtasks
    task_10 = [t for t in tasks if t.id == "1.0"][0]
    assert task_10.description == "Setup infrastructure"
    assert task_10.agent == "self"

    task_11 = [t for t in tasks if t.id == "1.1"][0]
    assert task_11.completed is True

    task_12 = [t for t in tasks if t.id == "1.2"][0]
    assert task_12.agent == "code-developer"
    assert task_12.model == "sonnet"

    # Task 2.0 and subtasks
    task_21 = [t for t in tasks if t.id == "2.1"][0]
    assert task_21.agent == "ui-designer"

    task_22 = [t for t in tasks if t.id == "2.2"][0]
    assert task_22.agent == "code-developer"

    # Task 3.0
    task_30 = [t for t in tasks if t.id == "3.0"][0]
    assert task_30.completed is True
    assert task_30.agent == "quality-assurance"


def test_parse_agent_and_model_together():
    """Parse both agent and model from markdown sub-bullets."""
    content = """- [ ] 1. Complex task
  - Agent: @system-architect
  - Model: opus"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 1
    assert tasks[0].agent == "system-architect"
    assert tasks[0].model == "opus"


def test_parse_metadata_applies_to_preceding_task():
    """Agent sub-bullets apply to the task immediately above them."""
    content = """- [ ] 1. First task
  - Agent: @agent-one
- [ ] 2. Second task
  - Agent: @agent-two
- [ ] 3. Third task"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert tasks[0].agent == "agent-one"
    assert tasks[1].agent == "agent-two"
    assert tasks[2].agent == "self"


def test_parse_handles_varied_whitespace():
    """Parse tasks with varied indentation and spacing."""
    content = """  - [ ] 1. Task with leading spaces
-   [  ]  2.  Task with extra spaces
-[ ]3.Task with no spaces"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 3
    assert tasks[0].id == "1"
    assert tasks[1].id == "2"
    assert tasks[2].id == "3"


def test_parse_agent_without_at_prefix():
    """Extract agent from sub-bullet without @ prefix."""
    content = """- [ ] 1. Implement feature X
  - Agent: code-developer"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 1
    assert tasks[0].agent == "code-developer"


def test_parse_multiple_tasks_with_agents():
    """Parse multiple tasks with visible markdown agent assignments."""
    content = """- [ ] 1.0 Create calculator module
  - Agent: @code-developer

- [ ] 2.0 Write unit tests
  - Agent: @quality-assurance

- [ ] 3.0 Task without agent"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert len(tasks) == 3
    assert tasks[0].agent == "code-developer"
    assert tasks[1].agent == "quality-assurance"
    assert tasks[2].agent == "self"


def test_parse_agent_case_insensitive():
    """Agent: label is case-insensitive."""
    content = """- [ ] 1. Task one
  - agent: @code-developer
- [ ] 2. Task two
  - AGENT: @quality-assurance"""
    parser = TaskParser()
    tasks = parser.parse(content)

    assert tasks[0].agent == "code-developer"
    assert tasks[1].agent == "quality-assurance"
