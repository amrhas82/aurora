"""Interactive mode detection utilities.

Provides functions to detect if the current environment is interactive.
"""

import os
import sys
from typing import Any


def is_interactive(options: dict[str, Any] | None = None) -> bool:
    """Check if the current environment is interactive.

    Args:
        options: Optional dictionary with 'noInteractive' or 'interactive' keys

    Returns:
        True if environment is interactive, False otherwise

    """
    # Check if explicitly disabled via options
    if options:
        if options.get("noInteractive"):
            return False
        if "interactive" in options and not options["interactive"]:
            return False

    # Check environment variable
    env_interactive = os.environ.get("AURORA_INTERACTIVE")
    if env_interactive is not None:
        return env_interactive.lower() not in ("0", "false", "no")

    # Check if stdin is a TTY
    return sys.stdin.isatty()
