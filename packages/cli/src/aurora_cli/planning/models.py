"""Pydantic models for Aurora Planning System.

This module defines the data models for plans, subgoals, and manifests
used by the AURORA CLI planning system.

Models:
    - PlanStatus: Enum for plan lifecycle status
    - Complexity: Enum for plan complexity assessment
    - Subgoal: Individual subgoal with agent assignment
    - Plan: Main plan model with subgoals and metadata
    - PlanManifest: Manifest for fast plan listing
    - FileResolution: File path with confidence score
    - AgentGap: Missing agent information
    - DecompositionSummary: Summary for plan decomposition
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PlanStatus(str, Enum):
    """Plan lifecycle status.

    States:
    - ACTIVE: Plan is currently being worked on
    - ARCHIVED: Plan has been completed and archived
    - FAILED: Plan failed and was abandoned
    """

    ACTIVE = "active"
    ARCHIVED = "archived"
    FAILED = "failed"


class Complexity(str, Enum):
    """Plan complexity assessment.

    Levels:
    - SIMPLE: 1-2 subgoals, straightforward implementation
    - MODERATE: 3-5 subgoals, some coordination needed
    - COMPLEX: 6+ subgoals, significant coordination
    """

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class MatchQuality(str, Enum):
    """Agent match quality levels for subgoal assignment.

    Levels:
    - EXCELLENT: Agent's core specialty matches task perfectly
    - ACCEPTABLE: Agent can handle but isn't specialized for task
    - INSUFFICIENT: No capable agent available, using fallback
    """

    EXCELLENT = "excellent"
    ACCEPTABLE = "acceptable"
    INSUFFICIENT = "insufficient"


class Subgoal(BaseModel):
    """Individual subgoal with agent assignment and match quality.

    Represents a decomposed piece of work that can be assigned
    to a specific agent for implementation.

    3-tier match quality model:
    - ideal_agent: The agent that SHOULD handle this task (unconstrained)
    - ideal_agent_desc: Description of the ideal agent's capabilities
    - assigned_agent: Best AVAILABLE agent from manifest
    - match_quality: How well the assigned agent fits the task

    Gap detection: ideal_agent != assigned_agent → gap exists

    Attributes:
        id: Unique subgoal ID in format 'sg-N' (e.g., 'sg-1')
        title: Short descriptive title (5-100 chars)
        description: Detailed description (10-500 chars)
        ideal_agent: Agent that SHOULD handle this (unconstrained)
        ideal_agent_desc: Description of ideal agent's capabilities
        assigned_agent: Best AVAILABLE agent ID in '@agent-id' format
        match_quality: How well assigned agent matches task requirements
        source_file: Primary source file for this subgoal (optional)
        dependencies: List of subgoal IDs this depends on

    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: str = Field(
        ...,
        description="Subgoal ID in 'sg-N' format",
        examples=["sg-1", "sg-2", "sg-10"],
    )
    title: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="Short descriptive title",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Detailed description of what this subgoal accomplishes",
    )
    ideal_agent: str = Field(
        default="",
        description="Agent that SHOULD handle this task (unconstrained)",
        examples=["@creative-writer", "@data-analyst"],
    )
    ideal_agent_desc: str = Field(
        default="",
        description="Description of ideal agent's capabilities",
        examples=["Specialist in story editing, narrative development"],
    )
    assigned_agent: str = Field(
        ...,
        description="Best AVAILABLE agent ID in '@agent-id' format",
        examples=["@code-developer", "@quality-assurance"],
    )
    match_quality: MatchQuality = Field(
        default=MatchQuality.EXCELLENT,
        description="How well the assigned agent matches the task requirements",
    )
    source_file: str | None = Field(
        default=None,
        description="Primary source file for this subgoal",
        examples=["packages/cli/src/aurora_cli/planning/core.py", "docs/guides/COMMANDS.md"],
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of subgoal IDs this depends on",
    )

    @field_validator("id")
    @classmethod
    def coerce_subgoal_id(cls, v: str) -> str:
        """Coerce subgoal ID to 'sg-N' format.

        Accepts SOAR's numeric format (e.g., "1") and normalizes to 'sg-N'.
        Rejects invalid formats that are neither numeric nor 'sg-N'.

        Args:
            v: The subgoal ID to coerce

        Returns:
            Normalized ID in 'sg-N' format

        Raises:
            ValueError: If ID format is invalid

        """
        if not v:
            return v
        # Already in correct format
        if re.match(r"^sg-\d+$", v):
            return v
        # Numeric ID from SOAR - coerce to sg-N
        if v.isdigit():
            return f"sg-{v}"
        # Invalid format - reject
        raise ValueError(f"Subgoal ID must be 'sg-N' or numeric format. Got: {v}")

    @field_validator("assigned_agent", "ideal_agent")
    @classmethod
    def coerce_agent_format(cls, v: str) -> str:
        """Coerce agent ID to '@agent-id' format.

        Accepts SOAR's format (e.g., "code-developer") and normalizes to '@code-developer'.

        Args:
            v: The agent ID to coerce

        Returns:
            Normalized agent ID with '@' prefix

        """
        # Allow empty strings for optional ideal_agent field
        if not v:
            return v
        # Already has @ prefix
        if v.startswith("@"):
            return v
        # Add @ prefix (SOAR returns without @)
        return f"@{v}"

    @field_validator("dependencies", mode="before")
    @classmethod
    def coerce_dependencies(cls, v: Any) -> list[str]:
        """Coerce dependencies to list of 'sg-N' format IDs.

        Accepts SOAR's numeric format (e.g., ["1", "2"]) and normalizes.

        Args:
            v: Value to normalize

        Returns:
            List of dependency IDs in 'sg-N' format

        """
        if v is None:
            return []

        def coerce_dep_id(dep: str) -> str:
            """Coerce a single dependency ID to 'sg-N' format."""
            dep = str(dep).strip()
            if not dep:
                return ""
            if re.match(r"^sg-\d+$", dep):
                return dep
            if dep.isdigit():
                return f"sg-{dep}"
            return f"sg-{dep}"

        if isinstance(v, str):
            v = v.strip()
            return [coerce_dep_id(v)] if v else []
        if isinstance(v, list):
            return [coerce_dep_id(item) for item in v if item]
        return []


class Plan(BaseModel):
    """Main plan model with subgoals and metadata.

    Represents a complete development plan with:
    - Goal decomposition into subgoals
    - Agent assignments for each subgoal
    - Dependency graph between subgoals
    - Lifecycle tracking (created, archived)

    Attributes:
        plan_id: Unique plan ID in 'NNNN-slug' format
        goal: Natural language goal description (10-500 chars)
        created_at: UTC timestamp when plan was created
        status: Current lifecycle status
        complexity: Assessed complexity level
        subgoals: List of 1-10 subgoals
        agent_gaps: List of missing agent IDs
        context_sources: Where context came from
        archived_at: When plan was archived (if applicable)
        duration_days: Days from creation to archive
        decomposition_source: Source of decomposition ("soar" or "heuristic")
        context_summary: Summary of available context
        file_resolutions: Map of subgoal ID to file resolutions

    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    plan_id: str = Field(
        default="",
        description="Plan ID in 'NNNN-slug' format",
        examples=["0001-oauth-auth", "0042-payment-integration"],
    )
    goal: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Natural language goal description",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when plan was created",
    )
    status: PlanStatus = Field(
        default=PlanStatus.ACTIVE,
        description="Current lifecycle status",
    )
    complexity: Complexity = Field(
        default=Complexity.MODERATE,
        description="Assessed complexity level",
    )
    subgoals: list[Subgoal] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of subgoals (1-10)",
    )
    agent_gaps: list[str] = Field(
        default_factory=list,
        description="List of missing agent IDs",
    )
    context_sources: list[str] = Field(
        default_factory=list,
        description="Where context came from",
    )
    archived_at: datetime | None = Field(
        default=None,
        description="When plan was archived",
    )
    duration_days: int | None = Field(
        default=None,
        description="Days from creation to archive",
    )
    decomposition_source: str = Field(
        default="heuristic",
        description="Source of decomposition",
    )
    context_summary: str | None = Field(
        default=None,
        description="Summary of available context",
    )
    file_resolutions: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict,
        description="Map of subgoal ID to file resolutions",
    )
    memory_context: list[MemoryContext] = Field(
        default_factory=list,
        description="Relevant files from memory search",
    )

    @field_validator("plan_id")
    @classmethod
    def validate_plan_id(cls, v: str) -> str:
        """Validate plan ID is in 'slug' or 'NNNN-slug' format (backward compatible).

        Args:
            v: The plan ID to validate

        Returns:
            The validated ID

        Raises:
            ValueError: If ID format is invalid (only when non-empty)

        """
        # Allow empty plan_id (will be generated later)
        if not v:
            return v

        # Accept slug-only format (new) or numbered format (backward compatible)
        slug_pattern = r"^[a-z0-9-]+$"
        numbered_pattern = r"^\d{4}-[a-z0-9-]+$"
        if not (re.match(slug_pattern, v) or re.match(numbered_pattern, v)):
            raise ValueError(
                f"Plan ID must be 'slug' or 'NNNN-slug' format (e.g., 'oauth-auth' or '0001-oauth-auth'). Got: {v}",
            )
        return v

    @model_validator(mode="after")
    def validate_subgoal_dependencies(self) -> Plan:
        """Validate that all subgoal dependencies reference valid subgoals.

        Raises:
            ValueError: If a dependency references an unknown subgoal

        """
        valid_ids = {sg.id for sg in self.subgoals}

        for sg in self.subgoals:
            for dep in sg.dependencies:
                if dep not in valid_ids:
                    raise ValueError(
                        f"Subgoal '{sg.id}' references unknown dependency: {dep}. "
                        f"Valid subgoal IDs: {sorted(valid_ids)}",
                    )

        return self

    @model_validator(mode="after")
    def check_circular_dependencies(self) -> Plan:
        """Check for circular dependencies in subgoal graph.

        Uses depth-first search to detect cycles.

        Raises:
            ValueError: If circular dependency detected

        """
        # Build adjacency list
        graph: dict[str, list[str]] = {sg.id: sg.dependencies for sg in self.subgoals}

        # Track visited nodes
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node: str, path: list[str]) -> list[str] | None:
            """DFS to detect cycle, returns cycle path if found."""
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    result = has_cycle(neighbor, path + [node])
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # Found cycle
                    return path + [node, neighbor]

            rec_stack.remove(node)
            return None

        for sg_id in graph:
            if sg_id not in visited:
                cycle = has_cycle(sg_id, [])
                if cycle:
                    raise ValueError(f"Circular dependency detected: {' -> '.join(cycle)}")

        return self

    def to_json(self) -> str:
        """Serialize plan to JSON string.

        Returns:
            JSON string representation

        """
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, data: str) -> Plan:
        """Deserialize plan from JSON string.

        Args:
            data: JSON string

        Returns:
            Plan instance

        """
        return cls.model_validate_json(data)


class PlanManifest(BaseModel):
    """Manifest for fast plan listing.

    Tracks all plans without loading full plan files,
    enabling fast listing and filtering operations.

    Attributes:
        version: Manifest schema version
        updated_at: When manifest was last updated
        active_plans: List of active plan IDs
        archived_plans: List of archived plan IDs
        stats: Aggregate statistics

    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    version: str = Field(
        default="1.0",
        description="Manifest schema version",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When manifest was last updated",
    )
    active_plans: list[str] = Field(
        default_factory=list,
        description="List of active plan IDs",
    )
    archived_plans: list[str] = Field(
        default_factory=list,
        description="List of archived plan IDs",
    )
    stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregate statistics",
    )

    def add_active_plan(self, plan_id: str) -> None:
        """Add a plan to active list.

        Args:
            plan_id: Plan ID to add

        """
        if plan_id not in self.active_plans:
            self.active_plans.append(plan_id)
        self.updated_at = datetime.now(timezone.utc)

    def archive_plan(self, plan_id: str, archived_id: str | None = None) -> None:
        """Move a plan from active to archived.

        Args:
            plan_id: Original plan ID
            archived_id: New archived ID (defaults to plan_id)

        """
        if plan_id in self.active_plans:
            self.active_plans.remove(plan_id)
        archived_name = archived_id or plan_id
        if archived_name not in self.archived_plans:
            self.archived_plans.append(archived_name)
        self.updated_at = datetime.now(timezone.utc)

    @property
    def total_plans(self) -> int:
        """Get total number of plans."""
        return len(self.active_plans) + len(self.archived_plans)


class FileResolution(BaseModel):
    """File path resolution with confidence score.

    Represents a resolved file path from memory retrieval with line
    ranges and confidence score.

    Attributes:
        path: File path relative to project root
        line_start: Starting line number (optional)
        line_end: Ending line number (optional)
        confidence: Confidence score from 0.0 to 1.0

    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    path: str = Field(
        ...,
        description="File path relative to project root",
        examples=["src/auth/oauth.py", "tests/test_auth.py"],
    )
    line_start: int | None = Field(
        default=None,
        ge=1,
        description="Starting line number (1-indexed)",
    )
    line_end: int | None = Field(
        default=None,
        ge=1,
        description="Ending line number (1-indexed)",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)",
    )

    @model_validator(mode="after")
    def validate_line_range(self) -> FileResolution:
        """Validate line_end >= line_start if both provided.

        Returns:
            The validated model

        Raises:
            ValueError: If line_end < line_start

        """
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError(
                f"line_end ({self.line_end}) must be >= line_start ({self.line_start})",
            )
        return self


class AgentGap(BaseModel):
    """Agent gap information for unmatched subgoals.

    Represents a subgoal where the ideal agent differs from the assigned agent,
    indicating a gap in the agent registry. Used for gap detection and reporting.

    Binary gap detection: ideal_agent != assigned_agent → gap exists

    Attributes:
        subgoal_id: ID of the subgoal with the gap (e.g., "sg-1")
        ideal_agent: Agent that SHOULD handle this task (unconstrained)
        ideal_agent_desc: Description of the ideal agent's capabilities
        assigned_agent: Best AVAILABLE agent from manifest

    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    subgoal_id: str = Field(
        ...,
        description="ID of subgoal with agent gap",
        examples=["sg-1", "sg-4"],
    )
    ideal_agent: str = Field(
        default="",
        description="Agent that SHOULD handle this task (unconstrained)",
        examples=["@creative-writer", "@data-analyst"],
    )
    ideal_agent_desc: str = Field(
        default="",
        description="Description of ideal agent's capabilities",
        examples=["Specialist in story editing, narrative development"],
    )
    assigned_agent: str = Field(
        default="",
        description="Best AVAILABLE agent from manifest",
        examples=["@market-researcher", "@master"],
    )

    @field_validator("subgoal_id")
    @classmethod
    def validate_subgoal_id(cls, v: str) -> str:
        """Validate subgoal ID format.

        Args:
            v: Subgoal ID to validate

        Returns:
            The validated ID

        Raises:
            ValueError: If format is invalid

        """
        pattern = r"^sg-\d+$"
        if not re.match(pattern, v):
            raise ValueError(f"Subgoal ID must be 'sg-N' format. Got: {v}")
        return v

    @field_validator("ideal_agent", "assigned_agent")
    @classmethod
    def validate_agent_format(cls, v: str) -> str:
        """Validate agent ID format.

        Args:
            v: Agent ID to validate

        Returns:
            The validated agent ID

        Raises:
            ValueError: If format is invalid (only when non-empty)

        """
        # Allow empty strings for optional fields
        if not v:
            return v

        pattern = r"^@[a-z0-9][a-z0-9-]*$"
        if not re.match(pattern, v):
            raise ValueError(f"Agent must start with '@'. Got: {v}")
        return v


class DecompositionSummary(BaseModel):
    """Summary of plan decomposition for progress display.

    This model is used to show users a summary of the decomposition
    before generating plan files, allowing them to review and confirm
    the subgoals, agent assignments, and file resolutions.

    Attributes:
        goal: Original goal description
        subgoals: List of decomposed subgoals
        agents_assigned: Count of subgoals with assigned agents
        agent_gaps: List of subgoals with missing/low-confidence agents
        files_resolved: Count of resolved file paths
        avg_confidence: Average confidence score for file resolutions
        complexity: Assessed complexity level
        decomposition_source: Source of decomposition ("soar" or "heuristic")
        warnings: List of warning messages

    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    goal: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Original goal description",
    )
    subgoals: list[Subgoal] = Field(
        ...,
        min_length=1,
        max_length=12,
        description="List of decomposed subgoals (prefer 8-10, max 12)",
    )
    agents_assigned: int = Field(
        ...,
        ge=0,
        description="Count of subgoals with assigned agents",
    )
    agent_gaps: list[AgentGap] = Field(
        default_factory=list,
        description="List of subgoals with agent gaps",
    )
    files_resolved: int = Field(
        ...,
        ge=0,
        description="Count of resolved file paths",
    )
    avg_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average confidence score for file resolutions",
    )
    complexity: Complexity = Field(
        ...,
        description="Assessed complexity level",
    )
    decomposition_source: str = Field(
        ...,
        description="Source of decomposition",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of warning messages",
    )

    @field_validator("decomposition_source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate decomposition source.

        Args:
            v: Source to validate

        Returns:
            The validated source

        Raises:
            ValueError: If source is not a recognized value

        """
        valid_sources = {"soar", "soar_llm", "heuristic", "cached"}
        if v not in valid_sources:
            raise ValueError(f"decomposition_source must be one of {valid_sources}. Got: {v}")
        return v

    def display(self) -> None:
        """Display the summary using Rich formatting with match quality indicators.

        Renders two panels:
        1. Plan Decomposition Summary - goal and subgoals list
        2. Summary - metadata (agent matching, complexity, warnings)

        Match quality indicators:
        - [++] excellent: Green - agent is specialized for this task
        - [+] acceptable: Yellow - agent can handle but not specialized
        - [-] insufficient: Red - no capable agent, needs ad-hoc spawn
        """
        try:
            from rich.console import Console
            from rich.panel import Panel

            console = Console()

            # === Panel 1: Plan Decomposition Summary (goal + subgoals only) ===
            content = []
            content.append(f"[bold cyan]Goal:[/bold cyan] {self.goal}\n")
            content.append(f"[bold cyan]Subgoals:[/bold cyan] {len(self.subgoals)}\n")

            # Count match qualities
            excellent_count = 0
            acceptable_count = 0
            insufficient_count = 0

            # List each subgoal with match quality indicators
            for sg in self.subgoals:
                match_quality = getattr(sg, "match_quality", None)
                is_gap = sg.ideal_agent and sg.ideal_agent != sg.assigned_agent

                if match_quality is None:
                    match_quality = "acceptable" if is_gap else "excellent"

                if match_quality == "excellent":
                    excellent_count += 1
                    indicator = "[green][++][/green]"
                    agent_display = f"[green]{sg.assigned_agent}[/green]"
                elif match_quality == "acceptable":
                    acceptable_count += 1
                    indicator = "[yellow][+][/yellow]"
                    if is_gap:
                        agent_display = (
                            f"[yellow]{sg.assigned_agent}[/yellow] "
                            f"[dim](ideal: {sg.ideal_agent})[/dim]"
                        )
                    else:
                        agent_display = f"[yellow]{sg.assigned_agent}[/yellow]"
                else:  # insufficient
                    insufficient_count += 1
                    indicator = "[red][-][/red]"
                    agent_display = (
                        f"[red]{sg.assigned_agent}[/red] [dim](need: {sg.ideal_agent})[/dim]"
                    )

                content.append(f"  {indicator} {sg.title}: {agent_display}")

            # First panel: subgoals only
            panel1 = Panel(
                "\n".join(content),
                title="[bold]Plan Decomposition Summary[/bold]",
                border_style="cyan",
            )
            console.print(panel1)
            console.print()

            # === Panel 2: Summary (metadata only) ===
            summary = []

            # Agent match quality summary
            quality_parts = []
            if excellent_count > 0:
                quality_parts.append(f"[green]{excellent_count} excellent[/green]")
            if acceptable_count > 0:
                quality_parts.append(f"[yellow]{acceptable_count} acceptable[/yellow]")
            if insufficient_count > 0:
                quality_parts.append(f"[red]{insufficient_count} insufficient[/red]")
            quality_str = ", ".join(quality_parts) if quality_parts else "none"
            summary.append(f"[bold cyan]Agent Matching:[/bold cyan] {quality_str}")

            # Gap summary
            gap_count = len(self.agent_gaps)
            if gap_count > 0:
                summary.append(
                    f"[bold cyan]Gaps Detected:[/bold cyan] "
                    f"[yellow]{gap_count} subgoals need attention[/yellow]",
                )

            # Context files summary
            if self.files_resolved > 0:
                file_summary = (
                    f"[bold cyan]Context:[/bold cyan] {self.files_resolved} files "
                    f"(avg relevance: {self.avg_confidence:.2f})"
                )
                summary.append(file_summary)

            # Complexity
            complexity_colors = {
                Complexity.SIMPLE: "green",
                Complexity.MODERATE: "yellow",
                Complexity.COMPLEX: "red",
            }
            complexity_color = complexity_colors[self.complexity]
            summary.append(
                f"[bold cyan]Complexity:[/bold cyan] "
                f"[{complexity_color}]{self.complexity.value.upper()}[/{complexity_color}]",
            )

            # Decomposition source
            source_display = (
                "soar"
                if self.decomposition_source.startswith("soar")
                else self.decomposition_source
            )
            if source_display == "soar":
                source_color = "green"
            elif source_display == "cached":
                source_color = "cyan"
            else:
                source_color = "yellow"
            summary.append(
                f"[bold cyan]Source:[/bold cyan] [{source_color}]{source_display}[/{source_color}]",
            )

            # Warnings
            if self.warnings:
                summary.append("")
                summary.append("[bold yellow]Warnings:[/bold yellow]")
                for warning in self.warnings:
                    summary.append(f"  ! {warning}")

            # Legend
            if insufficient_count > 0 or acceptable_count > 0:
                summary.append("")
                summary.append(
                    "[dim]Legend: [++] excellent | [+] acceptable | [-] insufficient[/dim]",
                )

            panel2 = Panel(
                "\n".join(summary),
                title="[bold]Summary[/bold]",
                border_style="cyan",
            )
            console.print(panel2)

        except ImportError:
            # Fallback to plain text if Rich not available
            # Panel 1: Plan Decomposition Summary
            print("\n" + "=" * 60)
            print("PLAN DECOMPOSITION SUMMARY")
            print("=" * 60)
            print(f"Goal: {self.goal}")
            print(f"Subgoals: {len(self.subgoals)}\n")

            excellent_count = 0
            acceptable_count = 0
            insufficient_count = 0

            for sg in self.subgoals:
                match_quality = getattr(sg, "match_quality", None)
                is_gap = sg.ideal_agent and sg.ideal_agent != sg.assigned_agent
                if match_quality is None:
                    match_quality = "acceptable" if is_gap else "excellent"

                if match_quality == "excellent":
                    excellent_count += 1
                    indicator = "[++]"
                elif match_quality == "acceptable":
                    acceptable_count += 1
                    indicator = "[+]"
                else:
                    insufficient_count += 1
                    indicator = "[-]"

                if is_gap:
                    print(
                        f"  {indicator} {sg.title}: {sg.assigned_agent} (ideal: {sg.ideal_agent})",
                    )
                else:
                    print(f"  {indicator} {sg.title}: {sg.assigned_agent}")

            print("=" * 60 + "\n")

            # Panel 2: Summary (metadata)
            print("=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(
                f"Agent Matching: {excellent_count} excellent, "
                f"{acceptable_count} acceptable, {insufficient_count} insufficient",
            )
            if len(self.agent_gaps) > 0:
                print(f"Gaps Detected: {len(self.agent_gaps)} subgoals need attention")
            if self.files_resolved > 0:
                print(
                    f"Context: {self.files_resolved} files (avg relevance: {self.avg_confidence:.2f})",
                )
            print(f"Complexity: {self.complexity.value.upper()}")
            source_display = (
                "soar"
                if self.decomposition_source.startswith("soar")
                else self.decomposition_source
            )
            print(f"Source: {source_display}")
            if self.warnings:
                print("\nWarnings:")
                for warning in self.warnings:
                    print(f"  ! {warning}")
            if insufficient_count > 0 or acceptable_count > 0:
                print("\nLegend: [++] excellent | [+] acceptable | [-] insufficient")
            print("=" * 60 + "\n")


class MemoryContext(BaseModel):
    """Memory context file with relevance score.

    Represents a file from memory search that's relevant to the goal.

    Attributes:
        file: File path
        relevance: Relevance score (0.0-1.0)

    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    file: str = Field(
        ...,
        description="File path from memory search",
        examples=["src/auth.py", "docs/architecture.md"],
        min_length=1,
    )
    relevance: float = Field(
        ...,
        description="Relevance score from memory search",
        ge=0.0,
        le=1.0,
    )


class SubgoalData(BaseModel):
    """Subgoal data for goals.json format.

    Represents a subgoal with agent assignment, match quality, and dependencies.
    This is the format used in goals.json for the /plan skill.

    3-tier match quality model:
    - ideal_agent: Agent that SHOULD handle this (unconstrained)
    - agent: Best AVAILABLE agent from manifest
    - match_quality: How well assigned agent fits the task

    Attributes:
        id: Subgoal ID (sg-1, sg-2, etc.)
        title: Short title
        description: Detailed description
        ideal_agent: Agent that SHOULD handle this (unconstrained)
        ideal_agent_desc: Description of ideal agent's capabilities
        agent: Best AVAILABLE agent ID with @ prefix (assigned_agent)
        match_quality: How well agent matches task (excellent/acceptable/insufficient)
        source_file: Primary source file for this subgoal (optional)
        dependencies: List of dependent subgoal IDs

    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: str = Field(
        ...,
        description="Subgoal ID",
        pattern=r"^sg-\d+$",
        examples=["sg-1", "sg-2"],
    )
    title: str = Field(
        ...,
        description="Short subgoal title",
        min_length=5,
        max_length=100,
    )
    description: str = Field(
        ...,
        description="Detailed subgoal description",
        min_length=10,
        max_length=500,
    )
    ideal_agent: str | None = Field(
        default=None,
        description="Agent that SHOULD handle this task (unconstrained)",
        examples=["@creative-writer", "@data-analyst"],
    )
    ideal_agent_desc: str | None = Field(
        default=None,
        description="Description of ideal agent's capabilities",
        examples=["Specialist in story editing, narrative development"],
    )
    agent: str | None = Field(
        default=None,
        description="Best AVAILABLE agent ID with @ prefix (assigned_agent)",
        pattern=r"^@[a-z0-9-]+$",
        examples=["@code-developer", "@quality-assurance"],
    )
    match_quality: str = Field(
        default="excellent",
        description="How well the assigned agent matches the task",
        examples=["excellent", "acceptable", "insufficient"],
    )
    source_file: str | None = Field(
        default=None,
        description="Primary source file for this subgoal",
        examples=["packages/cli/src/aurora_cli/planning/core.py", "docs/guides/COMMANDS.md"],
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of dependent subgoal IDs",
    )


class Goals(BaseModel):
    """Goals format for goals.json file.

    This is the main format used by the /plan skill to generate PRD and tasks.
    Matches FR-6.2 format from PRD-0026.

    Attributes:
        id: Plan ID (NNNN-slug format)
        title: Goal title
        created_at: Creation timestamp
        status: Status (always "ready_for_planning" initially)
        memory_context: Relevant files from memory search
        subgoals: List of subgoals with agent assignments
        gaps: List of agent gaps (missing agents)

    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: str = Field(
        ...,
        description="Plan ID in slug or NNNN-slug format (backward compatible)",
        pattern=r"^([a-z0-9-]+|\d{4}-[a-z0-9-]+)$",
        examples=["add-oauth2", "refactor-api", "0001-add-oauth2", "0042-refactor-api"],
    )
    title: str = Field(
        ...,
        description="Goal title",
        min_length=10,
        max_length=500,
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    status: str = Field(
        default="ready_for_planning",
        description="Status (always ready_for_planning initially)",
    )
    memory_context: list[MemoryContext] = Field(
        default_factory=list,
        description="Relevant files from memory search",
    )
    subgoals: list[SubgoalData] = Field(
        ...,
        description="List of subgoals with agent assignments",
        min_length=1,
    )
    gaps: list[AgentGap] = Field(
        default_factory=list,
        description="List of agent gaps (missing agents)",
    )
