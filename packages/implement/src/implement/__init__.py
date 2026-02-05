"""Implement package for Aurora framework.

This package provides task parsing and execution capabilities for processing
tasks.md files with agent metadata and dispatching to appropriate agents.
"""

from implement.executor import ExecutionResult, TaskExecutor
from implement.models import ParsedTask
from implement.parser import TaskParser


__all__ = [
    "ParsedTask",
    "TaskParser",
    "TaskExecutor",
    "ExecutionResult",
]

__version__ = "0.1.0"
