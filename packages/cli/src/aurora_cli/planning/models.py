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
    - DecompositionSummary: Summary for checkpoint display
"""

from __future__ import annotations

import re
from datetime import datetime
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


class Subgoal(BaseModel):
    """Individual subgoal with agent assignment.

    Represents a decomposed piece of work that can be assigned
    to a specific agent for implementation.

    Binary gap detection model:
    - ideal_agent: The agent that SHOULD handle this task (unconstrained)
    - ideal_agent_desc: Description of the ideal agent's capabilities
    - assigned_agent: Best AVAILABLE agent from manifest

    Gap detection: ideal_agent != assigned_agent → gap exists

    Attributes:
        id: Unique subgoal ID in format 'sg-N' (e.g., 'sg-1')
        title: Short descriptive title (5-100 chars)
        description: Detailed description (10-500 chars)
        ideal_agent: Agent that SHOULD handle this (unconstrained)
        ideal_agent_desc: Description of ideal agent's capabilities
        assigned_agent: Best AVAILABLE agent ID in '@agent-id' format
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
        examples=["@full-stack-dev", "@qa-test-architect"],
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of subgoal IDs this depends on",
    )

    @field_validator("id")
    @classmethod
    def validate_subgoal_id(cls, v: str) -> str:
        """Validate subgoal ID is in 'sg-N' format.

        Args:
            v: The subgoal ID to validate

        Returns:
            The validated ID

        Raises:
            ValueError: If ID format is invalid
        """
        pattern = r"^sg-\d+$"
        if not re.match(pattern, v):
            raise ValueError(f"Subgoal ID must be 'sg-N' format (e.g., 'sg-1'). Got: {v}")
        return v

    @field_validator("assigned_agent", "ideal_agent")
    @classmethod
    def validate_agent_format(cls, v: str) -> str:
        """Validate agent ID starts with '@'.

        Args:
            v: The agent ID to validate

        Returns:
            The validated agent ID

        Raises:
            ValueError: If agent format is invalid (only when non-empty)
        """
        # Allow empty strings for optional ideal_agent field
        if not v:
            return v

        pattern = r"^@[a-z0-9][a-z0-9-]*$"
        if not re.match(pattern, v):
            raise ValueError(f"Agent must start with '@' (e.g., '@full-stack-dev'). Got: {v}")
        return v

    @field_validator("dependencies", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> list[str]:
        """Ensure dependencies is a list.

        Args:
            v: Value to normalize

        Returns:
            List of dependency IDs
        """
        if v is None:
            return []
        if isinstance(v, str):
            return [v.strip()] if v.strip() else []
        if isinstance(v, list):
            return [str(item).strip() for item in v if item]
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
        default_factory=lambda: datetime.utcnow(),
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
    memory_context: list["MemoryContext"] = Field(
        default_factory=list,
        description="Relevant files from memory search",
    )

    @field_validator("plan_id")
    @classmethod
    def validate_plan_id(cls, v: str) -> str:
        """Validate plan ID is in 'NNNN-slug' format.

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

        pattern = r"^\d{4}-[a-z0-9-]+$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Plan ID must be 'NNNN-slug' format (e.g., '0001-oauth-auth'). Got: {v}"
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
                        f"Valid subgoal IDs: {sorted(valid_ids)}"
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
        default_factory=lambda: datetime.utcnow(),
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
        self.updated_at = datetime.utcnow()

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
        self.updated_at = datetime.utcnow()

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
    def validate_line_range(self) -> "FileResolution":
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
                f"line_end ({self.line_end}) must be >= line_start ({self.line_start})"
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
        examples=["@business-analyst", "@master"],
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
    """Summary of plan decomposition for checkpoint display.

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
            ValueError: If source is not 'soar' or 'heuristic'
        """
        valid_sources = {"soar", "heuristic"}
        if v not in valid_sources:
            raise ValueError(f"decomposition_source must be one of {valid_sources}. Got: {v}")
        return v

    def display(self) -> None:
        """Display the summary using Rich formatting.

        This method renders the decomposition summary in a user-friendly
        format with colors and formatting for easy review.
        """
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table

            console = Console()

            # Build summary content
            content = []

            # Goal
            content.append(f"[bold cyan]Goal:[/bold cyan] {self.goal}\n")

            # Subgoals count
            content.append(f"[bold cyan]Subgoals:[/bold cyan] {len(self.subgoals)}\n")

            # List each subgoal with gap detection:
            #   Matched: ideal == assigned (green)
            #   Gap: ideal != assigned (yellow)
            for sg in self.subgoals:
                is_gap = sg.ideal_agent != sg.assigned_agent
                if is_gap:
                    content.append(
                        f"   {sg.title} ([yellow]{sg.assigned_agent} → {sg.ideal_agent} ⚠[/yellow])"
                    )
                else:
                    content.append(f"   {sg.title} ([green]{sg.assigned_agent}[/green])")

            content.append("")

            # Agent summary
            gap_count = len(self.agent_gaps)
            agent_summary = f"[bold cyan]Agents:[/bold cyan] {self.agents_assigned} assigned"
            if gap_count > 0:
                agent_summary += f", [yellow]{gap_count} gaps[/yellow]"
            content.append(agent_summary)

            # File summary
            file_summary = f"[bold cyan]Files:[/bold cyan] {self.files_resolved} resolved"
            if self.files_resolved > 0:
                file_summary += f" (avg confidence: {self.avg_confidence:.2f})"
            content.append(file_summary)

            # Complexity
            complexity_colors = {
                Complexity.SIMPLE: "green",
                Complexity.MODERATE: "yellow",
                Complexity.COMPLEX: "red",
            }
            complexity_color = complexity_colors[self.complexity]
            content.append(
                f"[bold cyan]Complexity:[/bold cyan] [{complexity_color}]{self.complexity.value.upper()}[/{complexity_color}]"
            )

            # Decomposition source
            source_color = "green" if self.decomposition_source == "soar" else "yellow"
            content.append(
                f"[bold cyan]Source:[/bold cyan] [{source_color}]{self.decomposition_source}[/{source_color}]"
            )

            # Warnings
            if self.warnings:
                content.append("")
                content.append("[bold yellow]Warnings:[/bold yellow]")
                for warning in self.warnings:
                    content.append(f"  ⚠ {warning}")

            # Create panel and display
            panel = Panel(
                "\n".join(content),
                title="[bold]Plan Decomposition Summary[/bold]",
                border_style="cyan",
            )
            console.print(panel)

        except ImportError:
            # Fallback to plain text if Rich not available
            print("\n" + "=" * 60)
            print("PLAN DECOMPOSITION SUMMARY")
            print("=" * 60)
            print(f"Goal: {self.goal}")
            print(f"Subgoals: {len(self.subgoals)}")
            for sg in self.subgoals:
                is_gap = sg.ideal_agent != sg.assigned_agent
                if is_gap:
                    print(f"  {sg.title} ({sg.assigned_agent} → {sg.ideal_agent} - GAP)")
                else:
                    print(f"  {sg.title} ({sg.assigned_agent})")
            print(f"Agents: {self.agents_assigned} assigned, {len(self.agent_gaps)} gaps")
            print(
                f"Files: {self.files_resolved} resolved (avg confidence: {self.avg_confidence:.2f})"
            )
            print(f"Complexity: {self.complexity.value.upper()}")
            print(f"Source: {self.decomposition_source}")
            if self.warnings:
                print("Warnings:")
                for warning in self.warnings:
                    print(f"  ⚠ {warning}")
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

    Represents a subgoal with agent assignment and dependencies.
    This is the format used in goals.json for the /plan skill.

    Binary gap detection: ideal_agent != agent → gap exists

    Attributes:
        id: Subgoal ID (sg-1, sg-2, etc.)
        title: Short title
        description: Detailed description
        ideal_agent: Agent that SHOULD handle this (unconstrained)
        ideal_agent_desc: Description of ideal agent's capabilities
        agent: Best AVAILABLE agent ID with @ prefix (assigned_agent)
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
        examples=["@full-stack-dev", "@qa-test-architect"],
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
        description="Plan ID in NNNN-slug format",
        pattern=r"^\d{4}-[a-z0-9-]+$",
        examples=["0001-add-oauth2", "0042-refactor-api"],
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
