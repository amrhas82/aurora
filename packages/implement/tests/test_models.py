"""Tests for implement models (ParsedTask).

TDD RED Phase: These tests should fail initially until ParsedTask is implemented.
"""

import pytest

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
        agent="full-stack-dev",
        model="sonnet",
        completed=True,
    )

    assert task.id == "1.1"
    assert task.description == "Implement feature X"
    assert task.agent == "full-stack-dev"
    assert task.model == "sonnet"
    assert task.completed is True


def test_parsed_task_to_dict():
    """ParsedTask.to_dict() returns expected structure."""
    task = ParsedTask(
        id="2",
        description="Fix bug Y",
        agent="qa-test-architect",
        model="opus",
        completed=False,
    )

    result = task.to_dict()

    assert isinstance(result, dict)
    assert result["id"] == "2"
    assert result["description"] == "Fix bug Y"
    assert result["agent"] == "qa-test-architect"
    assert result["model"] == "opus"
    assert result["completed"] is False


def test_parsed_task_from_dict():
    """ParsedTask.from_dict() creates valid ParsedTask from dict."""
    data = {
        "id": "3",
        "description": "Refactor module Z",
        "agent": "holistic-architect",
        "model": "sonnet",
        "completed": True,
    }

    task = ParsedTask.from_dict(data)

    assert task.id == "3"
    assert task.description == "Refactor module Z"
    assert task.agent == "holistic-architect"
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
