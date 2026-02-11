"""JavaScript language configuration for LSP tools.

Defines JavaScript-specific patterns for:
- Complexity calculation (branch types)
- Deadcode detection (entry points, nested functions)
- Import filtering (already in filters.py, referenced here for completeness)
"""

from aurora_lsp.languages.base import LanguageConfig


JS_BRANCH_TYPES = {
    "if_statement",
    "for_statement",
    "for_in_statement",
    "while_statement",
    "do_statement",
    "switch_case",
    "catch_clause",
    "ternary_expression",
    "binary_expression",  # && / || short-circuit
}

JS_ENTRY_POINTS = {
    "default",  # default export
    "handler",  # AWS Lambda, Express
    "middleware",  # Express middleware
    "getServerSideProps",  # Next.js
    "getStaticProps",  # Next.js
    "getStaticPaths",  # Next.js
    "loader",  # Remix
    "action",  # Remix
}

JS_ENTRY_PATTERNS = {
    "test*",
    "spec*",
    "it",
    "describe",
    "before*",
    "after*",
}

JS_ENTRY_DECORATORS: set[str] = set()

JS_NESTED_PATTERNS = {
    "callback",
    "handler",
    "wrapper",
    "resolve",
    "reject",
    "next",
    "inner",
    "helper",
    "on_*",
    "_*",
}

JS_IMPORT_PATTERNS = [
    r"^\s*import\s+",
    r"^\s*import\s*\{",
    r"^\s*import\s+\*\s+as\s+",
    r"^\s*(const|let|var)\s+.*\s*=\s*require\s*\(",
]

JS_FUNCTION_DEF_TYPES = {
    "function_declaration",
    "method_definition",
    "arrow_function",
    "class_declaration",
    "generator_function_declaration",
}

# Built-in names to skip in callee analysis
JS_SKIP_NAMES = {
    "console",
    "Promise",
    "Array",
    "Object",
    "JSON",
    "Math",
    "setTimeout",
    "setInterval",
    "clearTimeout",
    "clearInterval",
    "parseInt",
    "parseFloat",
    "String",
    "Number",
    "Boolean",
    "RegExp",
    "Error",
    "Map",
    "Set",
    "Date",
    "Symbol",
    "Buffer",
    "require",
    "module",
    "exports",
    # Common methods (too noisy)
    "log",
    "warn",
    "error",
    "info",
    "debug",
    "push",
    "pop",
    "shift",
    "unshift",
    "splice",
    "slice",
    "concat",
    "map",
    "filter",
    "reduce",
    "forEach",
    "find",
    "findIndex",
    "includes",
    "indexOf",
    "join",
    "split",
    "replace",
    "trim",
    "toLowerCase",
    "toUpperCase",
    "toString",
    "valueOf",
    "keys",
    "values",
    "entries",
    "assign",
    "freeze",
    "stringify",
    "parse",
    "resolve",
    "reject",
    "then",
    "catch",
    "finally",
}

JAVASCRIPT = LanguageConfig(
    name="javascript",
    extensions=[".js", ".jsx", ".mjs"],
    tree_sitter_module="tree_sitter_javascript",
    branch_types=JS_BRANCH_TYPES,
    entry_points=JS_ENTRY_POINTS,
    entry_patterns=JS_ENTRY_PATTERNS,
    entry_decorators=JS_ENTRY_DECORATORS,
    nested_patterns=JS_NESTED_PATTERNS,
    import_patterns=JS_IMPORT_PATTERNS,
    call_node_type="call_expression",
    function_def_types=JS_FUNCTION_DEF_TYPES,
)
