"""Base language configuration for LSP tools.

This module defines the LanguageConfig dataclass that holds all language-specific
settings for code intelligence features (deadcode detection, complexity, etc.).

To add a new language:
1. Create a new file (e.g., languages/go.py)
2. Define a LanguageConfig instance
3. Register it in languages/__init__.py

See languages/python.py for a complete example.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LanguageConfig:
    """Configuration for language-specific code intelligence.

    Attributes:
        name: Language identifier (e.g., "python", "javascript")
        extensions: File extensions for this language (e.g., [".py", ".pyi"])
        tree_sitter_module: Module name for tree-sitter parser (e.g., "tree_sitter_python")

        branch_types: AST node types that represent branch points for complexity calculation
        entry_points: Function/class names to skip in deadcode detection (e.g., "main", "cli")
        entry_patterns: Glob patterns for entry points (e.g., "pytest_*", "test_*")
        entry_decorators: Decorators that mark entry points (e.g., "@click.command")
        nested_patterns: Names of nested functions to skip (e.g., "wrapper", "inner")

        import_patterns: Regex patterns to detect import statements.
                        Use {symbol} as placeholder for the symbol name.
    """

    name: str
    extensions: list[str]
    tree_sitter_module: str | None = None

    # Complexity calculation - AST node types that are branch points
    branch_types: set[str] = field(default_factory=set)

    # Deadcode filtering - skip these in deadcode detection
    entry_points: set[str] = field(default_factory=set)
    entry_patterns: set[str] = field(default_factory=set)  # Glob patterns like "pytest_*"
    entry_decorators: set[str] = field(default_factory=set)
    nested_patterns: set[str] = field(default_factory=set)

    # Import filtering - regex patterns with {symbol} placeholder
    import_patterns: list[str] = field(default_factory=list)

    # Call graph analysis - AST node types
    call_node_type: str = ""  # Node type for function calls (e.g., "call" in Python)
    function_def_types: set[str] = field(default_factory=set)  # Node types for function defs

    def matches_extension(self, file_path: str) -> bool:
        """Check if file path matches this language's extensions."""
        from pathlib import Path
        return Path(file_path).suffix in self.extensions

    def is_entry_point(self, name: str) -> bool:
        """Check if a symbol name is an entry point (should skip in deadcode)."""
        import fnmatch

        # Direct match
        if name in self.entry_points:
            return True

        # Pattern match (e.g., pytest_* matches pytest_configure)
        for pattern in self.entry_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True

        return False

    def is_nested_helper(self, name: str) -> bool:
        """Check if a symbol name is a nested helper function."""
        import fnmatch

        # Direct match
        if name in self.nested_patterns:
            return True

        # Pattern match
        for pattern in self.nested_patterns:
            if "*" in pattern and fnmatch.fnmatch(name, pattern):
                return True

        return False
