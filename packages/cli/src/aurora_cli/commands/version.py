"""Version command implementation for AURORA CLI.

This module implements the 'aur version' command to display version information.
"""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console


__all__ = ["version_command"]

console = Console()


@click.command(name="version")
def version_command() -> None:
    """Display version information.

    Shows Aurora version, git commit hash (if available),
    Python version, and installation path.

    \b
    Examples:
        # Show version information
        aur version
    """
    try:
        # Get Aurora version from package metadata
        try:
            aurora_version = importlib.metadata.version("aurora-actr")
        except Exception:
            aurora_version = "unknown"

        # Get git commit hash if in a git repository
        git_hash = "N/A"
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
            if result.returncode == 0:
                git_hash = result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass  # Git not installed, timeout, or other error

        # Get Python version
        python_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )

        # Get installation path
        try:
            import aurora_cli

            install_path = str(Path(aurora_cli.__file__).parent.parent.parent.parent)
        except Exception:
            install_path = "unknown"

        # Display version information
        console.print(f"[bold cyan]Aurora[/] [bold]v{aurora_version}[/]", end="")
        if git_hash != "N/A":
            console.print(f" [dim]({git_hash})[/]")
        else:
            console.print()

        console.print(f"Python {python_version}")
        console.print(f"Installed at: [cyan]{install_path}[/]")

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}", style="red")
        raise click.Abort()


if __name__ == "__main__":
    version_command()
