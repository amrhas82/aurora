"""Ignore pattern matching for indexing exclusions.

Supports .auroraignore files with gitignore-style patterns.
"""

import logging
from pathlib import Path


logger = logging.getLogger(__name__)


# Default patterns always excluded (in addition to user's .auroraignore)
DEFAULT_IGNORE_PATTERNS = [
    "tasks/**",
    "CHANGELOG.md",
    "LICENSE*",
    "node_modules/**",
    "venv/**",
    ".venv/**",
    "*.egg-info/**",
    ".git/**",
    "__pycache__/**",
    ".pytest_cache/**",
    "dist/**",
    "build/**",
]


def load_ignore_patterns(root_path: Path) -> list[str]:
    """Load ignore patterns from .auroraignore file.

    Args:
        root_path: Root directory to search for .auroraignore

    Returns:
        List of ignore patterns (includes defaults + user patterns)

    """
    patterns = DEFAULT_IGNORE_PATTERNS.copy()

    ignore_file = root_path / ".auroraignore"
    if ignore_file.exists():
        try:
            content = ignore_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    patterns.append(line)
            logger.info(f"Loaded {len(patterns)} ignore patterns from {ignore_file}")
        except Exception as e:
            logger.warning(f"Failed to read {ignore_file}: {e}")

    return patterns


def should_ignore(file_path: Path, root_path: Path, patterns: list[str]) -> bool:
    """Check if file should be ignored based on patterns.

    Args:
        file_path: Absolute path to file
        root_path: Root path being indexed
        patterns: List of gitignore-style patterns

    Returns:
        True if file should be ignored

    """
    try:
        # Get relative path from root
        rel_path = file_path.relative_to(root_path)
        rel_str = str(rel_path)

        for pattern in patterns:
            if matches_pattern(rel_str, pattern):
                return True
        return False
    except (ValueError, Exception) as e:
        logger.debug(f"Error checking ignore for {file_path}: {e}")
        return False


def matches_pattern(path: str, pattern: str) -> bool:
    """Check if path matches gitignore-style pattern.

    Supports:
    - Exact match: "file.txt"
    - Directory match: "dir/"
    - Wildcard: "*.md"
    - Recursive: "**/test.py" or "dir/**"

    Args:
        path: Relative file path (e.g., "src/main.py")
        pattern: Gitignore-style pattern

    Returns:
        True if path matches pattern

    """
    import fnmatch

    # Handle directory patterns (end with /)
    if pattern.endswith("/"):
        dir_pattern = pattern.rstrip("/")
        return path.startswith(dir_pattern + "/") or path == dir_pattern

    # Handle /** recursive patterns
    if "**" in pattern:
        # Convert ** to * for fnmatch (simple approach)
        simple_pattern = pattern.replace("**/", "*/")
        if fnmatch.fnmatch(path, simple_pattern):
            return True
        # Also check if any parent directory matches
        parts = path.split("/")
        for i in range(len(parts)):
            subpath = "/".join(parts[: i + 1])
            if fnmatch.fnmatch(subpath, simple_pattern):
                return True
        return False

    # Simple fnmatch for wildcards
    return fnmatch.fnmatch(path, pattern)


__all__ = [
    "DEFAULT_IGNORE_PATTERNS",
    "load_ignore_patterns",
    "should_ignore",
    "matches_pattern",
]
