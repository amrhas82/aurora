"""Checkpoint flow for Aurora Planning System.

This module implements the checkpoint flow that displays a decomposition
summary and prompts the user for confirmation before generating plan files.

Functions:
    - prompt_for_confirmation: Prompt user to proceed with plan generation
    - display_summary: Display decomposition summary before checkpoint
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aurora_cli.planning.models import DecompositionSummary


def prompt_for_confirmation() -> bool:
    """Prompt user to confirm plan generation.

    Displays the prompt: "Proceed with plan generation? [Y/n]"

    Valid inputs:
    - 'Y', 'y', or Enter (empty): Return True (proceed)
    - 'N' or 'n': Return False (abort)
    - Invalid input: Repeat prompt
    - Ctrl+C (KeyboardInterrupt): Return False with message

    Returns:
        True if user confirms, False otherwise
    """
    try:
        while True:
            response = input("\nProceed with plan generation? [Y/n]: ").strip()

            # Empty input or 'Y'/'y' means proceed
            if response == "" or response.lower() == "y":
                return True

            # 'N'/'n' means abort
            if response.lower() == "n":
                print("Plan creation cancelled.")
                return False

            # Invalid input - prompt again
            print(f"Invalid input: '{response}'. Please enter 'Y' or 'n'.")

    except KeyboardInterrupt:
        print("\nPlan creation cancelled.")
        return False


def display_summary(summary: DecompositionSummary) -> None:
    """Display decomposition summary before checkpoint.

    This is a convenience wrapper around DecompositionSummary.display()
    for use in the planning workflow.

    Args:
        summary: The decomposition summary to display
    """
    summary.display()
