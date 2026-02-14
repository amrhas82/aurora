"""Tests for prompt-to-tasks.md decomposition."""

from implement.decompose import _json_to_tasks_md


def test_json_to_tasks_md_basic():
    """Convert basic JSON tasks to markdown."""
    data = {
        "tasks": [
            {"id": "1.0", "description": "Create project structure"},
            {"id": "2.0", "description": "Write tests"},
        ]
    }

    result = _json_to_tasks_md(data, "Build a calculator")

    assert "# Tasks: decomposed from prompt" in result
    assert "Goal: Build a calculator" in result
    assert "- [ ] 1.0 Create project structure" in result
    assert "- [ ] 2.0 Write tests" in result


def test_json_to_tasks_md_with_agent():
    """Agent sub-bullet rendered with @ prefix."""
    data = {
        "tasks": [
            {"id": "1.0", "description": "Setup", "agent": "code-developer"},
        ]
    }

    result = _json_to_tasks_md(data, "prompt")
    assert "  - Agent: @code-developer" in result


def test_json_to_tasks_md_with_depends():
    """Depends sub-bullet rendered with comma-separated IDs."""
    data = {
        "tasks": [
            {"id": "1.0", "description": "First"},
            {"id": "2.0", "description": "Second", "depends_on": ["1.0"]},
            {"id": "3.0", "description": "Third", "depends_on": ["1.0", "2.0"]},
        ]
    }

    result = _json_to_tasks_md(data, "prompt")
    assert "  - Depends: 1.0" in result
    assert "  - Depends: 1.0, 2.0" in result


def test_json_to_tasks_md_no_agent_no_depends():
    """Tasks without agent or depends have no sub-bullets."""
    data = {
        "tasks": [
            {"id": "1.0", "description": "Simple task"},
        ]
    }

    result = _json_to_tasks_md(data, "prompt")
    assert "Agent:" not in result
    assert "Depends:" not in result


def test_json_to_tasks_md_null_agent_skipped():
    """Null agent is not rendered."""
    data = {
        "tasks": [
            {"id": "1.0", "description": "Task", "agent": None},
        ]
    }

    result = _json_to_tasks_md(data, "prompt")
    assert "Agent:" not in result


def test_json_to_tasks_md_empty_depends_skipped():
    """Empty depends_on list is not rendered."""
    data = {
        "tasks": [
            {"id": "1.0", "description": "Task", "depends_on": []},
        ]
    }

    result = _json_to_tasks_md(data, "prompt")
    assert "Depends:" not in result


def test_json_to_tasks_md_full_metadata():
    """Task with all metadata renders correctly."""
    data = {
        "tasks": [
            {
                "id": "2.0",
                "description": "Build feature",
                "agent": "code-developer",
                "depends_on": ["1.0"],
            },
        ]
    }

    result = _json_to_tasks_md(data, "Build app")

    assert "- [ ] 2.0 Build feature" in result
    assert "  - Agent: @code-developer" in result
    assert "  - Depends: 1.0" in result


def test_json_to_tasks_md_empty_tasks():
    """Empty tasks list produces header only."""
    data = {"tasks": []}
    result = _json_to_tasks_md(data, "prompt")

    assert "# Tasks:" in result
    assert "- [ ]" not in result
