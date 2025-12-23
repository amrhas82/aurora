"""
Scratchpad Manager for Headless Mode

This module manages the scratchpad file that tracks iteration history, actions,
and progress toward goals during headless autonomous execution. The scratchpad
serves as both a log and a memory system for the headless orchestrator.

Scratchpad Purpose:
    - Maintains full audit trail of all actions taken
    - Provides context for LLM evaluation of goal achievement
    - Enables iteration memory across SOAR loops
    - Supports debugging and post-mortem analysis

Scratchpad Format:
    # Experiment Scratchpad
    **Goal**: [goal from prompt]
    **Started**: [timestamp]
    **Status**: IN_PROGRESS | GOAL_ACHIEVED | BUDGET_EXCEEDED | MAX_ITERATIONS

    ## Iteration 1 - [timestamp]
    **Phase**: [phase name]
    **Action**: [action taken]
    **Result**: [result/observation]
    **Cost**: $[cost]

    ## Iteration 2 - [timestamp]
    ...

Usage:
    from aurora_soar.headless import ScratchpadManager, ScratchpadEntry

    manager = ScratchpadManager("scratchpad.md")

    # Initialize scratchpad
    manager.initialize(goal="Implement caching system")

    # Append iteration entry
    manager.append_iteration(
        iteration=1,
        phase="Implementation",
        action="Created cache_manager.py",
        result="File created with CacheManager class",
        cost=0.05
    )

    # Check for termination signals
    if manager.has_termination_signal():
        reason = manager.get_termination_signal()
        print(f"Termination: {reason}")

    # Read scratchpad content
    content = manager.read()
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional


class TerminationSignal(Enum):
    """
    Termination signals that can be detected in scratchpad.

    These signals indicate when headless mode should stop execution.
    """

    GOAL_ACHIEVED = "GOAL_ACHIEVED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    BLOCKED = "BLOCKED"  # Unrecoverable error or stuck state


class ScratchpadStatus(Enum):
    """Current status of the experiment."""

    IN_PROGRESS = "IN_PROGRESS"
    GOAL_ACHIEVED = "GOAL_ACHIEVED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    BLOCKED = "BLOCKED"


@dataclass
class ScratchpadConfig:
    """
    Configuration for scratchpad management.

    Attributes:
        auto_create: Automatically create scratchpad if missing (default: True)
        backup_on_init: Create backup before initializing (default: False)
        include_timestamps: Include timestamps in entries (default: True)
        max_file_size_mb: Maximum scratchpad file size in MB (default: 10)
    """

    auto_create: bool = True
    backup_on_init: bool = False
    include_timestamps: bool = True
    max_file_size_mb: float = 10.0


@dataclass
class ScratchpadEntry:
    """
    A single iteration entry in the scratchpad.

    Attributes:
        iteration: Iteration number
        timestamp: When this iteration occurred
        phase: SOAR phase or execution phase
        action: Action taken in this iteration
        result: Result or observation from the action
        cost: LLM cost for this iteration (dollars)
        notes: Optional additional notes
    """

    iteration: int
    timestamp: datetime
    phase: str
    action: str
    result: str
    cost: float
    notes: Optional[str] = None

    def to_markdown(self) -> str:
        """
        Convert entry to markdown format.

        Returns:
            Markdown string representation
        """
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"## Iteration {self.iteration} - {timestamp_str}",
            f"**Phase**: {self.phase}",
            f"**Action**: {self.action}",
            f"**Result**: {self.result}",
            f"**Cost**: ${self.cost:.4f}",
        ]

        if self.notes:
            lines.append(f"**Notes**: {self.notes}")

        return "\n".join(lines) + "\n"


class ScratchpadManager:
    """
    Manages scratchpad file for headless mode experiments.

    The ScratchpadManager handles creation, initialization, appending,
    and reading of the scratchpad file that tracks experiment progress.

    Key Features:
        - Initialize scratchpad with goal and metadata
        - Append iteration entries with timestamps
        - Detect termination signals in content
        - Parse status from scratchpad
        - Handle file operations safely

    Examples:
        # Create and initialize scratchpad
        >>> manager = ScratchpadManager("scratchpad.md")
        >>> manager.initialize(goal="Implement feature X")

        # Append iteration
        >>> manager.append_iteration(
        ...     iteration=1,
        ...     phase="Implementation",
        ...     action="Created main.py",
        ...     result="File created successfully",
        ...     cost=0.05
        ... )

        # Check status
        >>> status = manager.get_status()
        >>> print(status)
        ScratchpadStatus.IN_PROGRESS

        # Detect termination
        >>> if manager.has_termination_signal():
        ...     signal = manager.get_termination_signal()
        ...     print(f"Termination: {signal}")
    """

    # Template for new scratchpad
    TEMPLATE = """# Experiment Scratchpad
**Goal**: {goal}
**Started**: {timestamp}
**Status**: {status}

---

"""

    def __init__(
        self,
        scratchpad_path: str | Path,
        config: Optional[ScratchpadConfig] = None,
    ):
        """
        Initialize ScratchpadManager.

        Args:
            scratchpad_path: Path to scratchpad markdown file
            config: Optional configuration (uses defaults if None)
        """
        self.scratchpad_path = Path(scratchpad_path)
        self.config = config or ScratchpadConfig()

    def exists(self) -> bool:
        """
        Check if scratchpad file exists.

        Returns:
            True if file exists, False otherwise
        """
        return self.scratchpad_path.exists() and self.scratchpad_path.is_file()

    def get_file_size_mb(self) -> float:
        """
        Get current file size in megabytes.

        Returns:
            File size in MB (0.0 if file doesn't exist)
        """
        if not self.exists():
            return 0.0
        return self.scratchpad_path.stat().st_size / (1024 * 1024)

    def _check_file_size(self) -> None:
        """
        Check if file size exceeds limit.

        Raises:
            RuntimeError: If file size exceeds max_file_size_mb
        """
        size_mb = self.get_file_size_mb()
        if size_mb > self.config.max_file_size_mb:
            raise RuntimeError(
                f"Scratchpad file too large: {size_mb:.2f}MB "
                f"(limit: {self.config.max_file_size_mb}MB). "
                "Experiment may be stuck in a loop or generating excessive output."
            )

    def initialize(
        self,
        goal: str,
        status: ScratchpadStatus = ScratchpadStatus.IN_PROGRESS,
    ) -> None:
        """
        Initialize scratchpad with goal and metadata.

        Creates a new scratchpad file with the experiment goal and initial status.
        If file exists and backup_on_init is True, creates a backup first.

        Args:
            goal: The experiment goal from the prompt
            status: Initial status (default: IN_PROGRESS)

        Raises:
            RuntimeError: If file operations fail

        Examples:
            >>> manager = ScratchpadManager("scratchpad.md")
            >>> manager.initialize(goal="Implement caching")
        """
        # Backup existing file if configured
        if self.exists() and self.config.backup_on_init:
            backup_path = self.scratchpad_path.with_suffix(".md.bak")
            backup_path.write_text(self.scratchpad_path.read_text())

        # Create scratchpad from template
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = self.TEMPLATE.format(
            goal=goal,
            timestamp=timestamp,
            status=status.value,
        )

        try:
            self.scratchpad_path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize scratchpad at {self.scratchpad_path}: {e}"
            ) from e

    def read(self) -> str:
        """
        Read the entire scratchpad content.

        Returns:
            Full scratchpad content as string

        Raises:
            FileNotFoundError: If scratchpad doesn't exist
            RuntimeError: If file cannot be read

        Examples:
            >>> manager = ScratchpadManager("scratchpad.md")
            >>> content = manager.read()
            >>> print(content[:100])
        """
        if not self.exists():
            raise FileNotFoundError(
                f"Scratchpad file not found: {self.scratchpad_path}\n"
                "Initialize with manager.initialize(goal='...') first."
            )

        try:
            return self.scratchpad_path.read_text(encoding="utf-8")
        except Exception as e:
            raise RuntimeError(
                f"Failed to read scratchpad at {self.scratchpad_path}: {e}"
            ) from e

    def append(self, content: str) -> None:
        """
        Append content to scratchpad.

        Low-level method for appending arbitrary content.
        For structured iteration logging, use append_iteration() instead.

        Args:
            content: Content to append

        Raises:
            FileNotFoundError: If scratchpad doesn't exist
            RuntimeError: If file size exceeds limit or write fails

        Examples:
            >>> manager = ScratchpadManager("scratchpad.md")
            >>> manager.append("\\n## Custom Section\\nSome content\\n")
        """
        if not self.exists():
            if self.config.auto_create:
                self.initialize(goal="Auto-created scratchpad")
            else:
                raise FileNotFoundError(
                    f"Scratchpad file not found: {self.scratchpad_path}"
                )

        # Check file size before appending
        self._check_file_size()

        try:
            with open(self.scratchpad_path, "a", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise RuntimeError(
                f"Failed to append to scratchpad at {self.scratchpad_path}: {e}"
            ) from e

    def append_iteration(
        self,
        iteration: int,
        phase: str,
        action: str,
        result: str,
        cost: float,
        notes: Optional[str] = None,
    ) -> None:
        """
        Append a structured iteration entry to the scratchpad.

        This is the primary method for logging iterations during headless execution.

        Args:
            iteration: Iteration number (1-indexed)
            phase: Current phase (e.g., "Implementation", "Testing")
            action: Action taken in this iteration
            result: Result or observation
            cost: LLM cost in dollars
            notes: Optional additional notes

        Raises:
            FileNotFoundError: If scratchpad doesn't exist
            RuntimeError: If file operations fail

        Examples:
            >>> manager = ScratchpadManager("scratchpad.md")
            >>> manager.append_iteration(
            ...     iteration=1,
            ...     phase="Implementation",
            ...     action="Created cache_manager.py with CacheManager class",
            ...     result="File created successfully, basic structure in place",
            ...     cost=0.05,
            ...     notes="Need to add tests next"
            ... )
        """
        timestamp = datetime.now() if self.config.include_timestamps else None
        entry = ScratchpadEntry(
            iteration=iteration,
            timestamp=timestamp or datetime.now(),
            phase=phase,
            action=action,
            result=result,
            cost=cost,
            notes=notes,
        )

        content = "\n" + entry.to_markdown() + "\n"
        self.append(content)

    def update_status(self, status: ScratchpadStatus) -> None:
        """
        Update the status line in the scratchpad.

        Finds and replaces the "**Status**: ..." line with the new status.

        Args:
            status: New status to set

        Raises:
            FileNotFoundError: If scratchpad doesn't exist
            RuntimeError: If file operations fail

        Examples:
            >>> manager = ScratchpadManager("scratchpad.md")
            >>> manager.update_status(ScratchpadStatus.GOAL_ACHIEVED)
        """
        content = self.read()

        # Replace status line
        pattern = r"\*\*Status\*\*:\s*\w+"
        replacement = f"**Status**: {status.value}"
        updated_content = re.sub(pattern, replacement, content)

        try:
            self.scratchpad_path.write_text(updated_content, encoding="utf-8")
        except Exception as e:
            raise RuntimeError(
                f"Failed to update status in scratchpad: {e}"
            ) from e

    def get_status(self) -> Optional[ScratchpadStatus]:
        """
        Parse current status from scratchpad.

        Returns:
            Current ScratchpadStatus, or None if not found/parseable

        Examples:
            >>> manager = ScratchpadManager("scratchpad.md")
            >>> status = manager.get_status()
            >>> if status == ScratchpadStatus.GOAL_ACHIEVED:
            ...     print("Goal achieved!")
        """
        try:
            content = self.read()
            match = re.search(r"\*\*Status\*\*:\s*(\w+)", content)
            if match:
                status_str = match.group(1)
                return ScratchpadStatus(status_str)
        except (FileNotFoundError, ValueError):
            pass
        return None

    def has_termination_signal(self) -> bool:
        """
        Check if scratchpad contains a termination signal.

        Termination signals are status values that indicate execution should stop.

        Returns:
            True if termination signal detected, False otherwise

        Examples:
            >>> manager = ScratchpadManager("scratchpad.md")
            >>> if manager.has_termination_signal():
            ...     print("Should terminate")
        """
        status = self.get_status()
        if not status:
            return False

        termination_statuses = [
            ScratchpadStatus.GOAL_ACHIEVED,
            ScratchpadStatus.BUDGET_EXCEEDED,
            ScratchpadStatus.MAX_ITERATIONS,
            ScratchpadStatus.BLOCKED,
        ]

        return status in termination_statuses

    def get_termination_signal(self) -> Optional[TerminationSignal]:
        """
        Get the termination signal from scratchpad status.

        Returns:
            TerminationSignal if present, None otherwise

        Examples:
            >>> manager = ScratchpadManager("scratchpad.md")
            >>> signal = manager.get_termination_signal()
            >>> if signal == TerminationSignal.GOAL_ACHIEVED:
            ...     print("Success!")
        """
        status = self.get_status()
        if not status:
            return None

        # Map status to termination signal
        mapping = {
            ScratchpadStatus.GOAL_ACHIEVED: TerminationSignal.GOAL_ACHIEVED,
            ScratchpadStatus.BUDGET_EXCEEDED: TerminationSignal.BUDGET_EXCEEDED,
            ScratchpadStatus.MAX_ITERATIONS: TerminationSignal.MAX_ITERATIONS,
            ScratchpadStatus.BLOCKED: TerminationSignal.BLOCKED,
        }

        return mapping.get(status)

    def get_iteration_count(self) -> int:
        """
        Count the number of iterations in the scratchpad.

        Returns:
            Number of "## Iteration N" entries found

        Examples:
            >>> manager = ScratchpadManager("scratchpad.md")
            >>> count = manager.get_iteration_count()
            >>> print(f"Completed {count} iterations")
        """
        try:
            content = self.read()
            matches = re.findall(r"^## Iteration \d+", content, re.MULTILINE)
            return len(matches)
        except FileNotFoundError:
            return 0

    def get_total_cost(self) -> float:
        """
        Calculate total cost from all iterations.

        Sums up all "**Cost**: $X.XX" entries in the scratchpad.

        Returns:
            Total cost in dollars

        Examples:
            >>> manager = ScratchpadManager("scratchpad.md")
            >>> total = manager.get_total_cost()
            >>> print(f"Total cost: ${total:.2f}")
        """
        try:
            content = self.read()
            matches = re.findall(r"\*\*Cost\*\*:\s*\$([0-9.]+)", content)
            return sum(float(cost) for cost in matches)
        except (FileNotFoundError, ValueError):
            return 0.0

    def get_summary(self) -> dict:
        """
        Get a summary of the scratchpad state.

        Returns:
            Dictionary with summary information:
                - exists: bool
                - status: Optional[str]
                - iteration_count: int
                - total_cost: float
                - file_size_mb: float
                - has_termination_signal: bool

        Examples:
            >>> manager = ScratchpadManager("scratchpad.md")
            >>> summary = manager.get_summary()
            >>> print(f"Status: {summary['status']}")
            >>> print(f"Iterations: {summary['iteration_count']}")
            >>> print(f"Cost: ${summary['total_cost']:.2f}")
        """
        summary = {
            "exists": self.exists(),
            "status": None,
            "iteration_count": 0,
            "total_cost": 0.0,
            "file_size_mb": 0.0,
            "has_termination_signal": False,
        }

        if not summary["exists"]:
            return summary

        status = self.get_status()
        summary["status"] = status.value if status else None
        summary["iteration_count"] = self.get_iteration_count()
        summary["total_cost"] = self.get_total_cost()
        summary["file_size_mb"] = self.get_file_size_mb()
        summary["has_termination_signal"] = self.has_termination_signal()

        return summary
