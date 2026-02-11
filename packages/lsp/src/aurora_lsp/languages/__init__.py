"""Language configuration registry for LSP tools.

This module provides a registry of language configurations and helper functions
to get the appropriate config for a file based on its extension.

Usage:
    from aurora_lsp.languages import get_config, get_complexity_branch_types

    # Get full config for a file
    config = get_config("foo.py")
    if config:
        print(config.entry_points)  # {"main", "cli", ...}

    # Get just branch types for complexity calculation
    branch_types = get_complexity_branch_types("foo.py")
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from aurora_lsp.languages.base import LanguageConfig
from aurora_lsp.languages.go import GO
from aurora_lsp.languages.java import JAVA
from aurora_lsp.languages.javascript import JAVASCRIPT
from aurora_lsp.languages.python import PYTHON
from aurora_lsp.languages.typescript import TYPESCRIPT


if TYPE_CHECKING:
    pass


# Registry of all language configurations
# Add new languages here after creating their config file
LANGUAGES: dict[str, LanguageConfig] = {
    "python": PYTHON,
    "javascript": JAVASCRIPT,
    "typescript": TYPESCRIPT,
    "go": GO,
    "java": JAVA,
}

# Extension to language mapping
EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
}


def get_language(file_path: str | Path) -> str | None:
    """Get the language name for a file based on extension.

    Args:
        file_path: Path to file

    Returns:
        Language name (e.g., "python") or None if unsupported
    """
    ext = Path(file_path).suffix.lower()
    return EXTENSION_MAP.get(ext)


def get_config(file_path: str | Path) -> LanguageConfig | None:
    """Get the language configuration for a file.

    Args:
        file_path: Path to file

    Returns:
        LanguageConfig for the file's language, or None if unsupported
    """
    lang = get_language(file_path)
    if lang:
        return LANGUAGES.get(lang)
    return None


def get_complexity_branch_types(file_path: str | Path) -> set[str]:
    """Get branch types for complexity calculation.

    Args:
        file_path: Path to file

    Returns:
        Set of AST node types that represent branch points,
        or empty set if language not supported
    """
    config = get_config(file_path)
    if config:
        return config.branch_types
    return set()


def is_entry_point(file_path: str | Path, name: str) -> bool:
    """Check if a symbol name is an entry point for the file's language.

    Args:
        file_path: Path to file
        name: Symbol name to check

    Returns:
        True if the name is an entry point (should skip in deadcode)
    """
    config = get_config(file_path)
    if config:
        return config.is_entry_point(name)
    return False


def is_nested_helper(file_path: str | Path, name: str) -> bool:
    """Check if a symbol name is a nested helper for the file's language.

    Args:
        file_path: Path to file
        name: Symbol name to check

    Returns:
        True if the name is a nested helper pattern
    """
    config = get_config(file_path)
    if config:
        return config.is_nested_helper(name)
    return False


def supported_extensions() -> set[str]:
    """Get all supported file extensions.

    Returns:
        Set of file extensions (e.g., {".py", ".pyi"})
    """
    return set(EXTENSION_MAP.keys())


def get_call_node_type(file_path: str | Path) -> str:
    """Get the AST node type for function calls.

    Args:
        file_path: Path to file

    Returns:
        Node type string (e.g., "call" for Python), or empty string if unsupported
    """
    config = get_config(file_path)
    if config:
        return config.call_node_type
    return ""


def get_function_def_types(file_path: str | Path) -> set[str]:
    """Get AST node types for function definitions.

    Args:
        file_path: Path to file

    Returns:
        Set of node types (e.g., {"function_definition", "class_definition"})
    """
    config = get_config(file_path)
    if config:
        return config.function_def_types
    return set()


__all__ = [
    "LanguageConfig",
    "LANGUAGES",
    "get_config",
    "get_language",
    "get_complexity_branch_types",
    "get_call_node_type",
    "get_function_def_types",
    "is_entry_point",
    "is_nested_helper",
    "supported_extensions",
]
