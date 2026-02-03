"""Python language configuration for LSP tools.

This module defines Python-specific patterns for:
- Complexity calculation (branch types)
- Deadcode detection (entry points, nested functions)
- Import filtering (already in filters.py, referenced here for completeness)

To add another language, copy this file and modify the config values.
"""

from aurora_lsp.languages.base import LanguageConfig


# Python branch types for complexity calculation
# These AST node types represent decision points in control flow
PYTHON_BRANCH_TYPES = {
    "if_statement",
    "for_statement",
    "while_statement",
    "try_statement",
    "with_statement",
    "match_statement",      # Python 3.10+
    "elif_clause",
    "except_clause",
    "boolean_operator",     # and/or operators
    "conditional_expression",  # ternary operator
}

# Entry point names - functions called externally, not via Python imports
# These are excluded from dead code detection
PYTHON_ENTRY_POINTS = {
    "main",           # CLI entry points
    "cli",            # Click CLI
    "app",            # Flask/FastAPI
    "run",            # Common runner
    "setup",          # setuptools
    "teardown",       # pytest fixtures
}

# Entry point patterns (glob-style)
PYTHON_ENTRY_PATTERNS = {
    "pytest_*",       # pytest hooks
    "test_*",         # test functions
}

# Decorators that mark entry points
PYTHON_ENTRY_DECORATORS = {
    "@click.command",
    "@click.group",
    "@app.route",
    "@router.get",
    "@router.post",
    "@pytest.fixture",
    "@property",
}

# Nested function patterns - local helpers that appear unused but are called within parent
PYTHON_NESTED_PATTERNS = {
    "wrapper",        # Decorator wrappers
    "inner",          # Inner functions
    "helper",         # Local helpers
    "callback",       # Callbacks
    "handler",        # Event handlers
    "find_node",      # Tree traversal helpers
    "traverse",       # Tree traversal
    "visit",          # Visitor pattern
    "on_*",           # Event handlers (pattern)
    "count_*",        # Counter helpers (pattern)
    "process_*",      # Processing helpers (pattern)
    "_*",             # Private nested functions (pattern)
}

# Import patterns for reference filtering
# Note: These are also defined in filters.py - kept here for documentation
PYTHON_IMPORT_PATTERNS = [
    r"^\s*import\s+",
    r"^\s*from\s+[\w.]+\s+import\s+",
]

# Function definition types for AST parsing
PYTHON_FUNCTION_DEF_TYPES = {
    "function_definition",
    "class_definition",
}


# The Python language configuration
PYTHON = LanguageConfig(
    name="python",
    extensions=[".py", ".pyi"],
    tree_sitter_module="tree_sitter_python",

    # Complexity
    branch_types=PYTHON_BRANCH_TYPES,

    # Deadcode filtering
    entry_points=PYTHON_ENTRY_POINTS,
    entry_patterns=PYTHON_ENTRY_PATTERNS,
    entry_decorators=PYTHON_ENTRY_DECORATORS,
    nested_patterns=PYTHON_NESTED_PATTERNS,

    # Import filtering (for reference, actual patterns in filters.py)
    import_patterns=PYTHON_IMPORT_PATTERNS,

    # Call graph analysis
    call_node_type="call",  # Python call expressions
    function_def_types=PYTHON_FUNCTION_DEF_TYPES,
)
