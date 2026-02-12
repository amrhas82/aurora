"""Java language configuration for LSP tools.

Defines Java-specific patterns for:
- Complexity calculation (branch types)
- Deadcode detection (entry points, nested functions)
- Import filtering (already in filters.py, referenced here for completeness)
"""

from aurora_lsp.languages.base import LanguageConfig


JAVA_BRANCH_TYPES = {
    "if_statement",
    "for_statement",
    "enhanced_for_statement",
    "while_statement",
    "do_statement",
    "switch_expression",
    "switch_block_statement_group",
    "catch_clause",
    "ternary_expression",
    "binary_expression",  # && / ||
    "throw_statement",
    "assert_statement",
}

JAVA_ENTRY_POINTS = {
    "main",
    "run",  # Runnable
    "call",  # Callable
    "init",  # Servlet
    "destroy",  # Servlet
    "doGet",  # HttpServlet
    "doPost",  # HttpServlet
    "doPut",  # HttpServlet
    "doDelete",  # HttpServlet
    "configure",  # Spring Security
    "contextLoads",  # Spring Boot test
}

JAVA_ENTRY_PATTERNS = {
    "test*",
    "Test*",
    "setup*",
    "tearDown*",
    "before*",
    "after*",
}

JAVA_ENTRY_DECORATORS = {
    "@Override",
    "@Bean",
    "@GetMapping",
    "@PostMapping",
    "@PutMapping",
    "@DeleteMapping",
    "@PatchMapping",
    "@RequestMapping",
    "@EventListener",
    "@Scheduled",
    "@Test",
    "@BeforeEach",
    "@AfterEach",
    "@BeforeAll",
    "@AfterAll",
    "@ExceptionHandler",
    "@RestController",
    "@Controller",
    "@Service",
    "@Repository",
    "@Component",
    "@Configuration",
}

JAVA_NESTED_PATTERNS = {
    "handler",
    "callback",
    "wrapper",
    "helper",
    "inner",
    "lambda$*",
}

JAVA_CALLBACK_METHODS = {
    # Collections/Streams
    "map", "filter", "flatMap", "forEach", "reduce",
    "collect", "sorted", "peek", "anyMatch", "allMatch", "noneMatch",
    "findFirst", "findAny",
    # CompletableFuture
    "thenApply", "thenAccept", "thenRun", "thenCompose",
    "whenComplete", "handle", "exceptionally",
    "thenApplyAsync", "thenAcceptAsync", "thenRunAsync",
    # Optional
    "ifPresent", "orElseGet", "orElseThrow",
    # Threading
    "submit", "execute", "schedule", "scheduleAtFixedRate",
    "scheduleWithFixedDelay",
    # Event listeners
    "addListener", "addEventListener", "addObserver",
    "setOnClickListener", "setOnAction",
    # Common callback patterns
    "registerCallback", "setCallback", "addCallback",
    "subscribe", "on",
}

# Framework/interface methods that are not dead code
JAVA_SKIP_DEADCODE_NAMES = {
    # Spring lifecycle
    "afterPropertiesSet", "destroy", "onApplicationEvent",
    # Serialization
    "readObject", "writeObject", "readResolve", "writeReplace",
    # JPA/Hibernate lifecycle
    "prePersist", "postPersist", "preUpdate", "postUpdate",
    "preRemove", "postRemove", "postLoad",
    # Common interface implementations
    "compareTo", "compare", "accept", "apply", "test", "get", "supply",
    "onSuccess", "onFailure", "onError", "onComplete",
    # Android lifecycle
    "onCreate", "onStart", "onResume", "onPause", "onStop", "onDestroy",
    "onCreateView", "onViewCreated",
}

JAVA_IMPORT_PATTERNS = [
    r"^\s*import\s+",
    r"^\s*import\s+static\s+",
]

JAVA_FUNCTION_DEF_TYPES = {
    "method_declaration",
    "class_declaration",
    "interface_declaration",
    "enum_declaration",
    "constructor_declaration",
    "record_declaration",  # Java 16+
}

# Built-in names to skip in callee analysis
JAVA_SKIP_NAMES = {
    # Object methods
    "toString", "hashCode", "equals", "getClass", "clone",
    "notify", "notifyAll", "wait", "finalize",
    # Common collections
    "get", "set", "put", "add", "remove", "contains", "containsKey",
    "size", "isEmpty", "clear", "iterator", "stream",
    "toArray", "addAll", "removeAll", "retainAll",
    # String methods
    "length", "charAt", "substring", "trim", "strip",
    "toLowerCase", "toUpperCase", "replace", "split",
    "startsWith", "endsWith", "contains", "indexOf",
    "format", "valueOf", "concat",
    # Stream/Optional
    "of", "ofNullable", "orElse", "orElseThrow", "orElseGet",
    "map", "filter", "flatMap", "collect", "forEach",
    "findFirst", "findAny", "isPresent", "ifPresent",
    "toList", "toSet",
    # Logging
    "info", "debug", "warn", "error", "trace",
    # Common builders
    "build", "builder",
    # Printing
    "println", "printf", "print",
}


JAVA = LanguageConfig(
    name="java",
    extensions=[".java"],
    tree_sitter_module="tree_sitter_java",
    branch_types=JAVA_BRANCH_TYPES,
    entry_points=JAVA_ENTRY_POINTS,
    entry_patterns=JAVA_ENTRY_PATTERNS,
    entry_decorators=JAVA_ENTRY_DECORATORS,
    nested_patterns=JAVA_NESTED_PATTERNS,
    callback_methods=JAVA_CALLBACK_METHODS,
    skip_deadcode_names=JAVA_SKIP_DEADCODE_NAMES,
    import_patterns=JAVA_IMPORT_PATTERNS,
    call_node_type="method_invocation",
    function_def_types=JAVA_FUNCTION_DEF_TYPES,
)
