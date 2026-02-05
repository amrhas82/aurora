"""Aurora Planning System.

This module provides goal decomposition and plan management for AURORA CLI:
- Plan creation with SOAR-based goal decomposition
- Plan lifecycle management (active, archived)
- Agent recommendation and gap detection
- Four-file structure: plan.md, prd.md, tasks.md, agents.json

Exports:
    Plan: Main plan model with subgoals and metadata
    Subgoal: Individual subgoal with agent assignment
    PlanStatus: Plan lifecycle status enum
    Complexity: Plan complexity assessment enum
    PlanManifest: Manifest for fast plan listing
    PlanSummary: Lightweight summary for list views
    Result types: InitResult, PlanResult, ListResult, ShowResult, ArchiveResult
    Errors: PlanningError, PlanNotFoundError, PlanValidationError, etc.
    Core functions: init_planning_directory, list_plans, show_plan, archive_plan
"""

from __future__ import annotations

from aurora_cli.planning.core import (
    archive_plan,
    create_plan,
    init_planning_directory,
    list_plans,
    show_plan,
)
from aurora_cli.planning.errors import (
    VALIDATION_MESSAGES,
    ContextError,
    PlanArchiveError,
    PlanDirectoryError,
    PlanFileError,
    PlanningError,
    PlanNotFoundError,
    PlanValidationError,
)
from aurora_cli.planning.models import Complexity, Plan, PlanManifest, PlanStatus, Subgoal
from aurora_cli.planning.results import (
    ArchiveResult,
    InitResult,
    ListResult,
    PlanResult,
    PlanSummary,
    ShowResult,
)


__all__ = [
    # Models
    "Plan",
    "Subgoal",
    "PlanStatus",
    "Complexity",
    "PlanManifest",
    # Results
    "PlanSummary",
    "InitResult",
    "PlanResult",
    "ListResult",
    "ShowResult",
    "ArchiveResult",
    # Errors
    "VALIDATION_MESSAGES",
    "PlanningError",
    "PlanNotFoundError",
    "PlanValidationError",
    "PlanDirectoryError",
    "PlanArchiveError",
    "PlanFileError",
    "ContextError",
    # Core functions
    "init_planning_directory",
    "create_plan",
    "list_plans",
    "show_plan",
    "archive_plan",
]
