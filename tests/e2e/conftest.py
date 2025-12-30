"""
E2E Test Configuration and Utilities.

Provides helpers for subprocess CLI invocations that preserve Python environment.
"""

import os
import subprocess
import sys
import tempfile
import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator


def get_cli_env() -> Dict[str, str]:
    """
    Get environment dict for subprocess CLI calls that preserves PYTHONPATH.

    When E2E tests modify HOME/AURORA_HOME, subprocess calls lose access to
    installed packages. This helper preserves PYTHONPATH to fix that.

    Returns:
        Environment dict with preserved PYTHONPATH
    """
    env = os.environ.copy()

    # Preserve current Python path so subprocess can find installed packages
    if "PYTHONPATH" not in env:
        env["PYTHONPATH"] = ":".join(sys.path)

    return env


def run_cli_command(
    args: List[str],
    cwd: Optional[Path] = None,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    **kwargs: Any
) -> subprocess.CompletedProcess:
    """
    Run CLI command with preserved Python environment.

    Args:
        args: Command arguments (e.g., ["aur", "mem", "index", ...])
        cwd: Working directory
        capture_output: Whether to capture stdout/stderr
        text: Whether to return text output
        check: Whether to raise on non-zero exit
        **kwargs: Additional subprocess.run() arguments

    Returns:
        CompletedProcess result
    """
    # Merge provided env with preserved PYTHONPATH
    env = get_cli_env()
    if "env" in kwargs:
        env.update(kwargs.pop("env"))

    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=capture_output,
        text=text,
        check=check,
        env=env,
        **kwargs
    )


@pytest.fixture
def clean_aurora_home() -> Generator[Path, None, None]:
    """Create a clean, isolated Aurora home directory for testing."""
    original_home = os.environ.get("HOME")
    original_aurora_home = os.environ.get("AURORA_HOME")

    with tempfile.TemporaryDirectory() as tmp_home:
        os.environ["HOME"] = tmp_home
        os.environ["AURORA_HOME"] = str(Path(tmp_home) / ".aurora")

        aurora_home = Path(tmp_home) / ".aurora"
        aurora_home.mkdir(parents=True, exist_ok=True)

        yield aurora_home

    # Restore original environment
    if original_home:
        os.environ["HOME"] = original_home
    else:
        os.environ.pop("HOME", None)

    if original_aurora_home:
        os.environ["AURORA_HOME"] = original_aurora_home
    else:
        os.environ.pop("AURORA_HOME", None)
