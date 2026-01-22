"""Filesystem utilities for Aurora.

Provides functions for file system operations like finding project root
and reading markdown files.
"""

from pathlib import Path


def find_project_root(start_path: Path | None = None) -> Path | None:
    """Find the project root by looking for aurora/ directory.

    Args:
        start_path: Starting path for search (defaults to cwd)

    Returns:
        Path to project root, or None if not found

    """
    current = start_path or Path.cwd()

    # Check current directory
    if (current / "aurora").exists():
        return current

    # Walk up the directory tree
    for parent in current.parents:
        if (parent / "aurora").exists():
            return parent

    return None


def read_markdown_file(file_path: str) -> str:
    """Read a markdown file and return its contents.

    Args:
        file_path: Path to the markdown file

    Returns:
        File contents as string

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read

    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return path.read_text(encoding="utf-8")
