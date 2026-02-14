"""Implement package for Aurora framework.

This package provides task parsing and execution capabilities for processing
tasks.md files with agent metadata and dispatching to appropriate agents.
"""

from implement.executor import ExecutionResult, TaskExecutor
from implement.models import ParsedTask
from implement.parser import TaskParser
from implement.persistence import SpawnRunStore
from implement.topo_sort import topological_sort_tasks


__all__ = [
    "ParsedTask",
    "TaskParser",
    "TaskExecutor",
    "ExecutionResult",
    "SpawnRunStore",
    "topological_sort_tasks",
]

__version__ = "0.1.0"
