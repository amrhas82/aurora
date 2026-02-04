"""Central chunk type registry - single source of truth.

This module provides extension-based and context-based type determination
for chunks. All type decisions should flow through get_chunk_type().

Type Taxonomy:
- code: Source code files (py, js, ts, etc.) - tree-sitter parsed
- kb: Knowledge base files (md) - human-written documentation
- doc: Document files (pdf, docx, txt) - paginated documents
- reas: Reasoning traces - Aurora-generated content (SOAR, goals)
"""

from pathlib import Path
from typing import Union

# Extension-based type mapping
EXTENSION_TYPE_MAP: dict[str, str] = {
    # Code (tree-sitter parsed)
    ".py": "code",
    ".pyi": "code",
    ".js": "code",
    ".jsx": "code",
    ".ts": "code",
    ".tsx": "code",
    # Knowledge Base (markdown documentation)
    ".md": "kb",
    ".markdown": "kb",
    # Documents (paginated)
    ".pdf": "doc",
    ".docx": "doc",
    ".txt": "doc",
}

# Context-based types (Aurora-generated content)
CONTEXT_TYPE_MAP: dict[str, str] = {
    "soar_result": "reas",  # SOAR conversation logs
    "goals_output": "reas",  # Goals execution results
}

# Valid chunk types (immutable)
VALID_TYPES: frozenset[str] = frozenset({"code", "kb", "doc", "reas"})


def get_chunk_type(
    file_path: Union[Path, str, None] = None,
    context: str | None = None,
) -> str:
    """Determine chunk type from file extension or context.

    Context takes precedence over extension, allowing Aurora-generated
    content (like SOAR conversation logs) to be typed as 'reas' even
    though they may have .md extension.

    Args:
        file_path: Path to file (for extension-based lookup)
        context: Context string ('soar_result', 'goals_output')

    Returns:
        Chunk type: 'code', 'kb', 'doc', or 'reas'

    Examples:
        >>> get_chunk_type(file_path="main.py")
        'code'
        >>> get_chunk_type(file_path="README.md")
        'kb'
        >>> get_chunk_type(context="soar_result")
        'reas'
        >>> get_chunk_type(file_path="log.md", context="soar_result")
        'reas'  # Context overrides extension

    """
    # Context takes precedence (Aurora-generated content)
    if context and context in CONTEXT_TYPE_MAP:
        return CONTEXT_TYPE_MAP[context]

    # Extension-based lookup
    if file_path:
        path = Path(file_path) if isinstance(file_path, str) else file_path
        ext = path.suffix.lower()
        return EXTENSION_TYPE_MAP.get(ext, "code")

    return "code"  # Default


__all__ = [
    "EXTENSION_TYPE_MAP",
    "CONTEXT_TYPE_MAP",
    "VALID_TYPES",
    "get_chunk_type",
]
