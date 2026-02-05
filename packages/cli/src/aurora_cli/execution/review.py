"""Decomposition review module for user approval before execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table


console = Console()


class ReviewDecision(Enum):
    """User decision after reviewing decomposition."""

    PROCEED = "proceed"  # Execute with ad-hoc agents -> fallback to LLM
    FALLBACK = "fallback"  # Execute with LLM directly for gaps (faster)
    ABORT = "abort"  # Cancel and restart


@dataclass
class AgentGap:
    """Represents a subgoal with no suitable agent."""

    subgoal_index: int
    description: str
    required_agent: str | None = None


class DecompositionReview:
    """Display decomposition summary and prompt for user approval."""

    def __init__(
        self,
        subgoals: list[dict[str, Any]],
        agent_gaps: list[AgentGap] | None = None,
        goal: str = "",
        complexity: str = "",
        source: str = "",
        files_count: int = 0,
        files_confidence: float = 0.0,
    ):
        """Initialize decomposition review.

        Args:
            subgoals: List of subgoal dictionaries with agent assignments
            agent_gaps: List of subgoals with missing agents
            goal: Original user goal/query
            complexity: Complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
            source: Decomposition source (soar, heuristic)
            files_count: Number of resolved files
            files_confidence: Average confidence score for files

        """
        self.subgoals = subgoals
        self.agent_gaps = agent_gaps or []
        self.goal = goal
        self.complexity = complexity
        self.source = source
        self.files_count = files_count
        self.files_confidence = files_confidence

    def display(self) -> None:
        """Display summary to terminal.

        Note: The detailed decomposition summary is already shown by
        DecompositionSummary.display() - this method is now a no-op
        to avoid redundant output. The approval prompt still works.
        """
        # Decomposition details already shown by DecompositionSummary.display()
        # This method intentionally does nothing to avoid duplicate output

    def prompt(self, planning_only: bool = False) -> ReviewDecision:
        """Prompt user for decision.

        Args:
            planning_only: If True, show simpler save/abort options (for aur goals).
                          If False, show full execution options (for aur spawn).

        Returns:
            ReviewDecision enum value (PROCEED, FALLBACK, or ABORT)

        """
        console.print()

        if planning_only:
            # Simple prompt for aur goals (planning only, no execution)
            choice = Prompt.ask(
                "Save goals? [Y/n]",
                choices=["Y", "y", "N", "n", ""],
                default="",
                show_choices=False,
            )
            if choice.upper() == "N":
                return ReviewDecision.ABORT
            return ReviewDecision.PROCEED
        # Full prompt for execution contexts (aur spawn)
        console.print("[bold]Options:[/bold]")
        console.print("  [P]roceed   - Execute (try ad-hoc agents -> fallback to LLM)")
        console.print("  [F]allback  - Execute (LLM directly for gaps, faster)")
        console.print("  [A]bort     - Cancel and restart")
        console.print()

        choice = Prompt.ask(
            "Choice",
            choices=["P", "p", "F", "f", "A", "a"],
            default="P",
            show_choices=False,
        )

        if choice.upper() == "P":
            return ReviewDecision.PROCEED
        if choice.upper() == "F":
            return ReviewDecision.FALLBACK
        return ReviewDecision.ABORT


class ExecutionPreview:
    """Display execution preview for spawn command."""

    def __init__(self, tasks: list[dict[str, Any]], agent_gaps: list[AgentGap] | None = None):
        """Initialize execution preview.

        Args:
            tasks: List of task dictionaries with agent assignments
            agent_gaps: List of tasks with missing agents

        """
        self.tasks = tasks
        self.agent_gaps = agent_gaps or []

    def display(self) -> None:
        """Display execution preview to terminal."""
        # Create preview table
        table = Table(title="Execution Preview", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Status", width=6)
        table.add_column("Task", style="cyan")
        table.add_column("Agent", style="green")

        for i, task in enumerate(self.tasks, 1):
            description = task.get("description", task.get("task", ""))
            agent_id = task.get("agent_id", "unknown")

            # Check if this is a gap and get ideal agent
            gap = next((g for g in self.agent_gaps if g.subgoal_index == i - 1), None)
            if gap and gap.required_agent:
                # Show: @assigned → @ideal ⚠
                agent_display = f"[yellow]{agent_id} → {gap.required_agent} ⚠[/yellow]"
            else:
                agent_display = agent_id

            table.add_row(str(i), "[ ]", description[:80], agent_display)

        console.print()
        console.print(table)

        # Display summary
        assigned_count = len(self.tasks) - len(self.agent_gaps)
        gap_count = len(self.agent_gaps)

        summary_lines = [f"[green]✓[/green] {assigned_count} task(s) with available agents"]

        if gap_count > 0:
            # Collect unique ideal agents
            unique_agents = sorted(
                set(gap.required_agent for gap in self.agent_gaps if gap.required_agent),
            )

            if unique_agents:
                agents_display = ", ".join(unique_agents)
                summary_lines.append(f"[yellow]⚠[/yellow] Agent gaps: {agents_display}")
            else:
                summary_lines.append(
                    f"[yellow]⚠[/yellow] {gap_count} gap(s) (will spawn ad-hoc or fallback)",
                )

        summary_text = "\n".join(summary_lines)
        console.print()
        console.print(Panel(summary_text, title="Summary", border_style="blue"))

    def prompt(self) -> ReviewDecision:
        """Prompt user for decision.

        Returns:
            ReviewDecision enum value (PROCEED, FALLBACK, or ABORT)

        """
        console.print()
        console.print("[bold]Options:[/bold]")
        console.print("  [P]roceed   - Execute (try ad-hoc agents → fallback to LLM)")
        console.print("  [F]allback  - Execute (LLM directly for gaps, faster)")
        console.print("  [A]bort     - Cancel and restart")
        console.print()

        choice = Prompt.ask(
            "Choice",
            choices=["P", "p", "F", "f", "A", "a"],
            default="P",
            show_choices=False,
        )

        if choice.upper() == "P":
            return ReviewDecision.PROCEED
        if choice.upper() == "F":
            return ReviewDecision.FALLBACK
        return ReviewDecision.ABORT
