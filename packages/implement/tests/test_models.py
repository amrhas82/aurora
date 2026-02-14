"""Tests for implement models (ParsedTask).

TDD RED Phase: These tests should fail initially until ParsedTask is implemented.
"""

from implement.models import ParsedTask


def test_parsed_task_required_fields():
    """ParsedTask requires id and description fields."""
    # Should be able to create task with just id and description
    task = ParsedTask(id="1", description="Test task")
    assert task.id == "1"
    assert task.description == "Test task"


def test_parsed_task_defaults():
    """ParsedTask has correct default values for optional fields."""
    task = ParsedTask(id="1", description="Test task")

    # Default values
    assert task.agent == "self"
    assert task.model is None
    assert task.completed is False


def test_parsed_task_custom_values():
    """ParsedTask accepts custom values for all fields."""
    task = ParsedTask(
        id="1.1",
        description="Implement feature X",
        agent="code-developer",
        model="sonnet",
        completed=True,
    )

    assert task.id == "1.1"
    assert task.description == "Implement feature X"
    assert task.agent == "code-developer"
    assert task.model == "sonnet"
    assert task.completed is True


def test_parsed_task_to_dict():
    """ParsedTask.to_dict() returns expected structure."""
    task = ParsedTask(
        id="2",
        description="Fix bug Y",
        agent="quality-assurance",
        model="opus",
        completed=False,
    )

    result = task.to_dict()

    assert isinstance(result, dict)
    assert result["id"] == "2"
    assert result["description"] == "Fix bug Y"
    assert result["agent"] == "quality-assurance"
    assert result["model"] == "opus"
    assert result["completed"] is False


def test_parsed_task_from_dict():
    """ParsedTask.from_dict() creates valid ParsedTask from dict."""
    data = {
        "id": "3",
        "description": "Refactor module Z",
        "agent": "system-architect",
        "model": "sonnet",
        "completed": True,
    }

    task = ParsedTask.from_dict(data)

    assert task.id == "3"
    assert task.description == "Refactor module Z"
    assert task.agent == "system-architect"
    assert task.model == "sonnet"
    assert task.completed is True


def test_parsed_task_from_dict_with_defaults():
    """ParsedTask.from_dict() uses defaults for missing optional fields."""
    data = {
        "id": "4",
        "description": "Add tests",
    }

    task = ParsedTask.from_dict(data)

    assert task.id == "4"
    assert task.description == "Add tests"
    assert task.agent == "self"
    assert task.model is None
    assert task.completed is False
    assert task.depends_on == []


def test_parsed_task_depends_on_default():
    """ParsedTask depends_on defaults to empty list."""
    task = ParsedTask(id="1", description="Test")
    assert task.depends_on == []


def test_parsed_task_depends_on_custom():
    """ParsedTask accepts custom depends_on list."""
    task = ParsedTask(id="2", description="Test", depends_on=["1.0", "1.1"])
    assert task.depends_on == ["1.0", "1.1"]


def test_parsed_task_to_dict_includes_depends_on():
    """to_dict() includes depends_on field."""
    task = ParsedTask(id="2", description="Test", depends_on=["1.0"])
    d = task.to_dict()
    assert d["depends_on"] == ["1.0"]


def test_parsed_task_from_dict_with_depends_on():
    """from_dict() restores depends_on list."""
    data = {"id": "3", "description": "Test", "depends_on": ["1.0", "2.0"]}
    task = ParsedTask.from_dict(data)
    assert task.depends_on == ["1.0", "2.0"]
