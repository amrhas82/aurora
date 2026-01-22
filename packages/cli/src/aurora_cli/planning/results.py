"""Result types for Aurora Planning System.

This module provides result dataclasses for graceful degradation,
allowing planning operations to return structured results with
warnings instead of raising exceptions.

Result Types:
    - InitResult: Result from init_planning_directory
    - PlanResult: Result from create_plan
    - ListResult: Result from list_plans
    - ShowResult: Result from show_plan
    - ArchiveResult: Result from archive_plan
    - PlanSummary: Lightweight summary for list views
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from aurora_cli.planning.models import Plan


@dataclass
class InitResult:
    """Result from init_planning_directory operation.

    Supports success+warning and failure+error states.

    Attributes:
        success: Whether operation succeeded
        path: Path to planning directory (if successful)
        created: Whether directory was newly created
        message: Success message
        warning: Warning message (e.g., already exists)
        error: Error message (if failed)

    """

    success: bool
    path: Path | None = None
    created: bool = False
    message: str | None = None
    warning: str | None = None
    error: str | None = None


@dataclass
class PlanResult:
    """Result from create_plan operation.

    Captures partial success states like "plan created but with agent gaps".

    Attributes:
        success: Whether operation succeeded
        plan: The created plan (if successful)
        plan_dir: Path to plan directory
        warnings: List of warning messages
        error: Error message (if failed)

    """

    success: bool
    plan: Plan | None = None
    plan_dir: Path | None = None
    warnings: list[str] | None = None
    error: str | None = None


@dataclass
class ListResult:
    """Result from list_plans operation.

    Returns empty list with warning if not initialized.

    Attributes:
        plans: List of plan summaries
        warning: Warning message (e.g., not initialized)
        errors: List of errors encountered while loading plans

    """

    plans: list[PlanSummary] = field(default_factory=list)
    warning: str | None = None
    errors: list[str] | None = None


@dataclass
class ShowResult:
    """Result from show_plan operation.

    Includes file existence status for plan directory.

    Attributes:
        success: Whether operation succeeded
        plan: The plan (if found)
        plan_dir: Path to plan directory
        files_status: Map of filename to exists bool
        error: Error message (if failed)

    """

    success: bool
    plan: Plan | None = None
    plan_dir: Path | None = None
    files_status: dict[str, bool] | None = None
    error: str | None = None


@dataclass
class ArchiveResult:
    """Result from archive_plan operation.

    Includes computed duration from creation to archive.

    Attributes:
        success: Whether operation succeeded
        plan: The archived plan (if successful)
        source_dir: Original plan directory
        target_dir: Archive destination directory
        duration_days: Days from creation to archive
        error: Error message (if failed)

    """

    success: bool
    plan: Plan | None = None
    source_dir: Path | None = None
    target_dir: Path | None = None
    duration_days: int | None = None
    error: str | None = None


@dataclass
class PlanSummary:
    """Lightweight summary for plan listing.

    Contains minimal information needed for list display,
    without loading full plan data.

    Attributes:
        plan_id: Plan identifier
        goal: Truncated goal (max 50 chars)
        created_at: Creation timestamp
        status: Plan status string
        subgoal_count: Number of subgoals
        agent_gaps: Count of missing agents

    """

    plan_id: str
    goal: str  # Truncated to 50 chars
    created_at: datetime
    status: str
    subgoal_count: int
    agent_gaps: int

    @classmethod
    def from_plan(cls, plan: Plan, status: str) -> PlanSummary:
        """Create summary from a full Plan object.

        Args:
            plan: Full Plan object
            status: Status string override

        Returns:
            PlanSummary instance

        """
        goal = plan.goal[:50] + "..." if len(plan.goal) > 50 else plan.goal
        return cls(
            plan_id=plan.plan_id,
            goal=goal,
            created_at=plan.created_at,
            status=status,
            subgoal_count=len(plan.subgoals),
            agent_gaps=len(plan.agent_gaps),
        )
