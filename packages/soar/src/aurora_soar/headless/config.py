"""
Configuration dataclass for Aurora headless mode.

This module provides a simplified, immutable configuration class for headless
execution with built-in validation.
"""

from dataclasses import dataclass
from pathlib import Path

# Validation constants (Task 1.8 - extracted to module level)
MIN_BUDGET = 1
MAX_ITERATIONS_LIMIT = 10


@dataclass(frozen=True)
class HeadlessConfig:
    """
    Immutable configuration for headless mode execution.

    This configuration enforces safety constraints and provides sensible defaults
    for autonomous AI execution in headless mode.

    Attributes:
        budget: Maximum token budget for the execution (must be positive).
        max_iterations: Maximum number of SOAR iterations allowed (1-10).
        scratchpad_path: Path to the scratchpad markdown file for logging.
        dry_run: If True, validate configuration but don't execute.

    Raises:
        ValueError: If budget or max_iterations are invalid.

    Example:
        >>> config = HeadlessConfig(budget=30000, max_iterations=5)
        >>> config.budget
        30000
        >>> config.dry_run
        False
    """

    budget: int = 30000
    max_iterations: int = 5
    scratchpad_path: str = ".aurora/headless/scratchpad.md"
    dry_run: bool = False

    def __post_init__(self) -> None:
        """
        Validate configuration after initialization.

        Validates:
        - budget must be positive (> 0)
        - max_iterations must be positive and within reasonable limits (1-10)

        Raises:
            ValueError: If any validation constraint is violated.
        """
        # Validate budget
        if self.budget <= 0:
            raise ValueError(
                f"budget must be positive, got {self.budget}. "
                f"Minimum allowed: {MIN_BUDGET}"
            )

        # Validate max_iterations
        if self.max_iterations <= 0:
            raise ValueError(
                f"max_iterations must be positive, got {self.max_iterations}. "
                f"Minimum allowed: 1"
            )

        if self.max_iterations > MAX_ITERATIONS_LIMIT:
            raise ValueError(
                f"max_iterations cannot exceed {MAX_ITERATIONS_LIMIT}, "
                f"got {self.max_iterations}. Headless mode is designed for "
                f"single-iteration or limited autonomous execution."
            )
