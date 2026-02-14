"""Tests for topological sort of tasks."""

import pytest

from implement.models import ParsedTask
from implement.topo_sort import topological_sort_tasks


def _task(tid: str, depends_on: list[str] | None = None) -> ParsedTask:
    return ParsedTask(id=tid, description=f"Task {tid}", depends_on=depends_on or [])


def test_empty_tasks():
    """Empty input returns empty waves."""
    assert topological_sort_tasks([]) == []


def test_no_dependencies_single_wave():
    """Tasks without dependencies all go in one wave."""
    tasks = [_task("1"), _task("2"), _task("3")]
    waves = topological_sort_tasks(tasks)

    assert len(waves) == 1
    assert len(waves[0]) == 3


def test_linear_chain():
    """Linear dependency chain produces one task per wave."""
    tasks = [_task("1"), _task("2", ["1"]), _task("3", ["2"])]
    waves = topological_sort_tasks(tasks)

    assert len(waves) == 3
    assert waves[0][0].id == "1"
    assert waves[1][0].id == "2"
    assert waves[2][0].id == "3"


def test_diamond_dependency():
    """Diamond pattern: 1 -> 2,3 -> 4."""
    tasks = [
        _task("1"),
        _task("2", ["1"]),
        _task("3", ["1"]),
        _task("4", ["2", "3"]),
    ]
    waves = topological_sort_tasks(tasks)

    assert len(waves) == 3
    assert waves[0][0].id == "1"
    wave1_ids = {t.id for t in waves[1]}
    assert wave1_ids == {"2", "3"}
    assert waves[2][0].id == "4"


def test_circular_dependency_raises():
    """Circular dependency raises ValueError."""
    tasks = [_task("1", ["2"]), _task("2", ["1"])]
    with pytest.raises(ValueError, match="Circular dependency"):
        topological_sort_tasks(tasks)


def test_partial_dependencies():
    """Mixed: some tasks have deps, some don't."""
    tasks = [_task("1"), _task("2"), _task("3", ["1"])]
    waves = topological_sort_tasks(tasks)

    assert len(waves) == 2
    wave0_ids = {t.id for t in waves[0]}
    assert "1" in wave0_ids
    assert "2" in wave0_ids
    assert waves[1][0].id == "3"


def test_unknown_dependency_ignored():
    """Dependencies referencing non-existent task IDs are ignored."""
    tasks = [_task("1"), _task("2", ["99"])]
    waves = topological_sort_tasks(tasks)

    # Both should be in wave 0 since "99" doesn't exist in task set
    assert len(waves) == 1
    assert len(waves[0]) == 2
