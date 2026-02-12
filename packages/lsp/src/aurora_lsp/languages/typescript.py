"""TypeScript language configuration for LSP tools.

Extends JavaScript config with TypeScript-specific additions:
- `import type` pattern
- Interface and type alias declarations
- TSX handling via tree_sitter_typescript's language_tsx()
"""

from aurora_lsp.languages.base import LanguageConfig
from aurora_lsp.languages.javascript import (
    JS_BRANCH_TYPES,
    JS_CALLBACK_METHODS,
    JS_ENTRY_DECORATORS,
    JS_ENTRY_PATTERNS,
    JS_ENTRY_POINTS,
    JS_FUNCTION_DEF_TYPES,
    JS_NESTED_PATTERNS,
    JS_SKIP_DEADCODE_NAMES,
)


TS_IMPORT_PATTERNS = [
    r"^\s*import\s+",
    r"^\s*import\s*\{",
    r"^\s*import\s+\*\s+as\s+",
    r"^\s*import\s+type\s+",
    r"^\s*(const|let|var)\s+.*\s*=\s*require\s*\(",
]

TS_FUNCTION_DEF_TYPES = JS_FUNCTION_DEF_TYPES | {
    "type_alias_declaration",
    "interface_declaration",
}

TYPESCRIPT = LanguageConfig(
    name="typescript",
    extensions=[".ts", ".tsx"],
    tree_sitter_module="tree_sitter_typescript",
    branch_types=JS_BRANCH_TYPES,
    entry_points=JS_ENTRY_POINTS,
    entry_patterns=JS_ENTRY_PATTERNS,
    entry_decorators=JS_ENTRY_DECORATORS,
    nested_patterns=JS_NESTED_PATTERNS,
    callback_methods=JS_CALLBACK_METHODS,
    skip_deadcode_names=JS_SKIP_DEADCODE_NAMES,
    import_patterns=TS_IMPORT_PATTERNS,
    call_node_type="call_expression",
    function_def_types=TS_FUNCTION_DEF_TYPES,
)
