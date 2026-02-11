"""Go language configuration for LSP tools.

Defines Go-specific patterns for:
- Complexity calculation (branch types)
- Deadcode detection (entry points, nested functions)
- Import filtering (already in filters.py, referenced here for completeness)
"""

from aurora_lsp.languages.base import LanguageConfig


GO_BRANCH_TYPES = {
    "if_statement",
    "for_statement",
    "expression_switch_statement",
    "type_switch_statement",
    "select_statement",
    "communication_case",  # case in select
    "expression_case",  # case in switch
    "default_case",
    "binary_expression",  # && / ||
    "go_statement",  # goroutine launch
    "defer_statement",
}

GO_ENTRY_POINTS = {
    "main",
    "init",  # package initializer
    "TestMain",
    "ServeHTTP",  # http.Handler interface
}

GO_ENTRY_PATTERNS = {
    "Test*",  # testing functions
    "Benchmark*",  # benchmark functions
    "Example*",  # example functions
    "Fuzz*",  # fuzz tests (Go 1.18+)
}

GO_ENTRY_DECORATORS: set[str] = set()  # Go has no decorators

GO_NESTED_PATTERNS = {
    "handler",
    "wrapper",
    "callback",
    "helper",
    "inner",
    "_*",
}

GO_IMPORT_PATTERNS = [
    r"^\s*import\s+",
    r"^\s*import\s*\(",
    r'^\s*"[\w/.-]+"',  # inside import block
]

GO_FUNCTION_DEF_TYPES = {
    "function_declaration",
    "method_declaration",
    "type_declaration",  # type X struct{} / type X interface{}
    "func_literal",  # anonymous functions (closures)
}

# Built-in names to skip in callee analysis
GO_SKIP_NAMES = {
    # Built-in functions
    "len", "cap", "make", "new", "append", "copy", "delete",
    "close", "panic", "recover", "print", "println",
    "complex", "real", "imag",
    "min", "max", "clear",  # Go 1.21+
    # Type conversions
    "int", "int8", "int16", "int32", "int64",
    "uint", "uint8", "uint16", "uint32", "uint64",
    "float32", "float64", "complex64", "complex128",
    "string", "byte", "rune", "bool", "error",
    # Common noisy methods
    "Error", "String", "Unwrap",
}


GO = LanguageConfig(
    name="go",
    extensions=[".go"],
    tree_sitter_module="tree_sitter_go",
    branch_types=GO_BRANCH_TYPES,
    entry_points=GO_ENTRY_POINTS,
    entry_patterns=GO_ENTRY_PATTERNS,
    entry_decorators=GO_ENTRY_DECORATORS,
    nested_patterns=GO_NESTED_PATTERNS,
    import_patterns=GO_IMPORT_PATTERNS,
    call_node_type="call_expression",
    function_def_types=GO_FUNCTION_DEF_TYPES,
)
