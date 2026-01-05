"""
Simplified Scratchpad Manager for Headless Mode

This module provides lightweight tracking of headless execution iterations
and status updates in a markdown file format.

The scratchpad serves as an audit trail and memory for the headless orchestrator,
logging each iteration's goal, action, and result.

Usage:
    from aurora_soar.headless.scratchpad import Scratchpad, ExecutionStatus

    scratchpad = Scratchpad("scratchpad.md")
    scratchpad.update_status(ExecutionStatus.IN_PROGRESS)
    scratchpad.append_iteration(1, "Goal", "Action", "Result")
    scratchpad.update_status(ExecutionStatus.COMPLETED)
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List


class ExecutionStatus(Enum):
    """Execution status states."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ScratchpadEntry:
    """
    Single iteration entry in the scratchpad.

    Attributes:
        iteration: Iteration number
        timestamp: When this iteration occurred
        goal: The goal for this iteration
        action: Action taken during iteration
        result: Result/outcome of the action
        status: Execution status
    """
    iteration: int
    timestamp: datetime
    goal: str
    action: str
    result: str
    status: ExecutionStatus


class Scratchpad:
    """
    Simplified scratchpad manager for headless execution tracking.

    The scratchpad maintains a markdown file with:
    - Current execution status
    - Iteration history (goal, action, result)
    - Termination signals (goal achieved, budget exceeded, etc.)

    The file format is human-readable markdown for easy inspection and debugging.
    """

    def __init__(self, scratchpad_path: str | Path):
        """
        Initialize Scratchpad, creating file if it doesn't exist.

        Args:
            scratchpad_path: Path to the scratchpad markdown file
        """
        self.path = Path(scratchpad_path)
        self._current_status = ExecutionStatus.PENDING

        # Create file and parent directories if needed
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self._initialize_file()
        else:
            # Load existing status if present
            self._load_status()

    def _initialize_file(self) -> None:
        """Initialize a new scratchpad file with header."""
        content = """# Headless Execution Scratchpad

**Status**: PENDING
**Started**: {timestamp}

## Iterations

""".format(timestamp=datetime.now().isoformat())

        self.path.write_text(content, encoding="utf-8")

    def _load_status(self) -> None:
        """Load current status from existing file."""
        content = self.path.read_text(encoding="utf-8")

        # Extract status from **Status**: line
        for line in content.split('\n'):
            if line.startswith("**Status**:"):
                status_str = line.split(":", 1)[1].strip()
                try:
                    self._current_status = ExecutionStatus[status_str]
                except KeyError:
                    # Default to PENDING if status not recognized
                    self._current_status = ExecutionStatus.PENDING
                break

    def append_iteration(
        self,
        iteration: int,
        goal: str,
        action: str,
        result: str
    ) -> None:
        """
        Append an iteration entry to the scratchpad.

        Args:
            iteration: Iteration number
            goal: Goal for this iteration
            action: Action taken
            result: Result/outcome
        """
        timestamp = datetime.now().isoformat()

        entry = f"""
## Iteration {iteration}

**Timestamp**: {timestamp}

**Goal**: {goal}

**Action**: {action}

**Result**: {result}

---

"""

        # Append to file
        with self.path.open("a", encoding="utf-8") as f:
            f.write(entry)

    def read(self) -> str:
        """
        Read the full scratchpad content as a string.

        Returns:
            Full markdown content of the scratchpad file
        """
        if not self.path.exists():
            return ""
        return self.path.read_text(encoding="utf-8")

    def read_entries(self) -> List[ScratchpadEntry]:
        """
        Read all iteration entries from the scratchpad.

        Returns:
            List of ScratchpadEntry objects

        Note:
            This is a simplified implementation that parses the markdown format.
            For production, consider using a more robust parser.
        """
        if not self.path.exists():
            return []

        content = self.path.read_text(encoding="utf-8")
        entries = []

        # Split by ## Iteration headers
        sections = content.split("## Iteration ")

        for section in sections[1:]:  # Skip the header section
            try:
                # Extract iteration number from first line
                lines = section.split('\n')
                iteration = int(lines[0].strip())

                # Parse fields
                timestamp_str = ""
                goal = ""
                action = ""
                result = ""

                for i, line in enumerate(lines):
                    if line.startswith("**Timestamp**:"):
                        timestamp_str = line.split(":", 1)[1].strip()
                    elif line.startswith("**Goal**:"):
                        goal = line.split(":", 1)[1].strip()
                    elif line.startswith("**Action**:"):
                        action = line.split(":", 1)[1].strip()
                    elif line.startswith("**Result**:"):
                        result = line.split(":", 1)[1].strip()

                # Parse timestamp
                timestamp = datetime.fromisoformat(timestamp_str)

                entry = ScratchpadEntry(
                    iteration=iteration,
                    timestamp=timestamp,
                    goal=goal,
                    action=action,
                    result=result,
                    status=self._current_status
                )
                entries.append(entry)

            except (ValueError, IndexError):
                # Skip malformed entries
                continue

        return entries

    def update_status(self, status: ExecutionStatus) -> None:
        """
        Update the current execution status.

        Args:
            status: New execution status
        """
        self._current_status = status

        # Update status in file
        content = self.path.read_text(encoding="utf-8")

        # Replace **Status**: line
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith("**Status**:"):
                lines[i] = f"**Status**: {status.value}"
                break

        self.path.write_text('\n'.join(lines), encoding="utf-8")

    def get_current_status(self) -> ExecutionStatus:
        """
        Get the current execution status.

        Returns:
            Current ExecutionStatus
        """
        return self._current_status

    def append_signal(self, signal_type: str, message: str) -> None:
        """
        Append a termination signal to the scratchpad.

        Args:
            signal_type: Type of signal (e.g., GOAL_ACHIEVED, BUDGET_EXCEEDED)
            message: Descriptive message about the signal
        """
        timestamp = datetime.now().isoformat()

        signal_entry = f"""
## Termination Signal

**Type**: {signal_type}
**Timestamp**: {timestamp}
**Message**: {message}

---

"""

        with self.path.open("a", encoding="utf-8") as f:
            f.write(signal_entry)
