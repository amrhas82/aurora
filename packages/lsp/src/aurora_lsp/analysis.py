"""Code analysis layer - dead code detection, usage summary, call hierarchy.

Built on top of LSP client and import filtering.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING

from aurora_lsp.filters import get_filter_for_file
from aurora_lsp.languages import (
    get_call_node_type,
    get_callback_methods,
    get_config,
    get_function_def_types,
    get_skip_deadcode_names,
    is_entry_point,
    is_nested_helper,
)

if TYPE_CHECKING:
    from aurora_lsp.client import AuroraLSPClient

logger = logging.getLogger(__name__)


class SymbolKind(IntEnum):
    """LSP SymbolKind values (from LSP specification)."""

    FILE = 1
    MODULE = 2
    NAMESPACE = 3
    PACKAGE = 4
    CLASS = 5
    METHOD = 6
    PROPERTY = 7
    FIELD = 8
    CONSTRUCTOR = 9
    ENUM = 10
    INTERFACE = 11
    FUNCTION = 12
    VARIABLE = 13
    CONSTANT = 14
    STRING = 15
    NUMBER = 16
    BOOLEAN = 17
    ARRAY = 18
    OBJECT = 19
    KEY = 20
    NULL = 21
    ENUM_MEMBER = 22
    STRUCT = 23
    EVENT = 24
    OPERATOR = 25
    TYPE_PARAMETER = 26


def _ext_to_rg_type(ext: str) -> str:
    """Map file extension to ripgrep --type value."""
    return {
        ".py": "py",
        ".pyi": "py",
        ".js": "js",
        ".jsx": "js",
        ".mjs": "js",
        ".ts": "ts",
        ".tsx": "ts",
        ".go": "go",
        ".java": "java",
    }.get(ext, "py")


def _batched_ripgrep_search(
    symbols: list[str],
    workspace: Path,
    file_types: list[str] | None = None,
) -> dict[str, list[str]]:
    """Run single ripgrep call to find files containing each symbol.

    24x faster than per-symbol grep calls.

    Args:
        symbols: List of symbol names to search
        workspace: Workspace root directory
        file_types: File type filters (default: ["py"])

    Returns:
        Dict mapping symbol name to list of files containing it
    """
    if not symbols:
        return {}

    if file_types is None:
        file_types = ["py"]

    unique_symbols = list(set(symbols))

    # Create temp file with patterns (one per line)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for sym in unique_symbols:
            f.write(f"{sym}\n")
        patterns_file = f.name

    try:
        # Build type flags: -t py -t js -t ts
        type_flags = []
        for ft in file_types:
            type_flags.extend(["-t", ft])

        # Single ripgrep call with JSON output
        result = subprocess.run(
            ["rg", "--json", "-w", "-f", patterns_file, *type_flags, "."],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Parse JSON output to map symbols to files
        usage_map: dict[str, list[str]] = {sym: [] for sym in unique_symbols}

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("type") == "match":
                    match_data = data.get("data", {})
                    file_path = match_data.get("path", {}).get("text", "")
                    submatches = match_data.get("submatches", [])
                    for submatch in submatches:
                        matched_text = submatch.get("match", {}).get("text", "")
                        if matched_text in usage_map:
                            if file_path not in usage_map[matched_text]:
                                usage_map[matched_text].append(file_path)
            except json.JSONDecodeError:
                continue

        return usage_map

    except subprocess.TimeoutExpired:
        logger.warning("Ripgrep search timed out, falling back to empty results")
        return {sym: [] for sym in unique_symbols}
    except FileNotFoundError:
        logger.warning("ripgrep (rg) not found, falling back to per-symbol grep")
        return _fallback_grep_search(unique_symbols, workspace, file_types=file_types)
    finally:
        Path(patterns_file).unlink(missing_ok=True)


def _fallback_grep_search(
    symbols: list[str], workspace: Path, file_types: list[str] | None = None
) -> dict[str, list[str]]:
    """Fallback to grep if ripgrep not available (slower)."""
    if file_types is None:
        file_types = ["py"]

    # Map rg types to grep --include patterns
    _type_to_exts = {
        "py": ["*.py"],
        "js": ["*.js", "*.jsx", "*.mjs"],
        "ts": ["*.ts", "*.tsx"],
        "go": ["*.go"],
        "java": ["*.java"],
    }
    include_flags = []
    for ft in file_types:
        for ext in _type_to_exts.get(ft, [f"*.{ft}"]):
            include_flags.extend([f"--include={ext}"])

    usage_map = {sym: [] for sym in symbols}

    for sym in symbols:
        try:
            result = subprocess.run(
                ["grep", "-r", *include_flags, "-l", "-w", sym, "."],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.stdout.strip():
                usage_map[sym] = [f for f in result.stdout.strip().split("\n") if f]
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            continue

    return usage_map


def _get_skip_names(language: str) -> set[str]:
    """Get built-in/common names to skip in callee analysis for a language."""
    if language in ("javascript", "typescript"):
        from aurora_lsp.languages.javascript import JS_SKIP_NAMES

        return JS_SKIP_NAMES

    if language == "go":
        from aurora_lsp.languages.go import GO_SKIP_NAMES

        return GO_SKIP_NAMES

    if language == "java":
        from aurora_lsp.languages.java import JAVA_SKIP_NAMES

        return JAVA_SKIP_NAMES

    # Python built-ins and common methods
    return {
        "int",
        "str",
        "float",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "len",
        "range",
        "enumerate",
        "zip",
        "map",
        "filter",
        "sorted",
        "print",
        "isinstance",
        "hasattr",
        "getattr",
        "setattr",
        "min",
        "max",
        "sum",
        "abs",
        "round",
        "type",
        "id",
        "hash",
        "open",
        "super",
        "next",
        "iter",
        "get",
        "items",
        "keys",
        "values",
        "update",
        "pop",
        "append",
        "extend",
        "insert",
        "remove",
        "clear",
        "copy",
        "format",
        "join",
        "split",
        "strip",
        "replace",
        "lower",
        "upper",
        "startswith",
        "endswith",
    }


class CodeAnalyzer:
    """High-level code analysis using LSP.

    Provides:
    - Find usages (excluding imports)
    - Dead code detection
    - Usage summary with impact assessment
    - Call hierarchy (callers/callees)
    """

    # Symbol kinds that can have usages (functions, classes, methods)
    ANALYZABLE_KINDS = {
        SymbolKind.FUNCTION,
        SymbolKind.CLASS,
        SymbolKind.METHOD,
        SymbolKind.INTERFACE,
        SymbolKind.ENUM,
    }

    # Entry point and nested function patterns moved to aurora_lsp.languages.python
    # Use is_entry_point() and is_nested_helper() from languages module

    def __init__(self, client: AuroraLSPClient, workspace: Path | str):
        """Initialize analyzer.

        Args:
            client: LSP client for making requests.
            workspace: Workspace root directory.
        """
        self.client = client
        self.workspace = Path(workspace).resolve()
        self._file_cache: dict[str, list[str]] = {}

    def _is_entry_point_or_nested(
        self, name: str, file_path: str | Path = "", line_content: str = ""
    ) -> bool:
        """Check if a symbol is an entry point or nested function.

        These are excluded from dead code detection because they're called
        externally (CLI, MCP, frameworks) or are local to their parent function.

        Uses language-specific patterns from aurora_lsp.languages module.

        Args:
            name: Symbol name
            file_path: Path to file (for language detection)
            line_content: The line where the symbol is defined

        Returns:
            True if should be excluded from dead code detection
        """
        # Use language-specific config
        if is_entry_point(file_path, name):
            return True

        if is_nested_helper(file_path, name):
            return True

        # Check if decorated (decorators often indicate external entry points)
        # Look for @ on previous lines - simple heuristic
        if line_content.strip().startswith("@"):
            return True

        return False

    @staticmethod
    def _is_callback_context(line_content: str, callback_methods: set[str]) -> bool:
        """Check if a symbol is defined inside a callback to a known method.

        Detects patterns like: .map(function name(...)), .then(handler), etc.
        """
        if not line_content:
            return False
        for method in callback_methods:
            if f".{method}(" in line_content:
                return True
        return False

    async def find_usages(
        self,
        file_path: str | Path,
        line: int,
        col: int,
        include_imports: bool = False,
    ) -> dict:
        """Find usages of a symbol, optionally filtering imports.

        Args:
            file_path: Path to file containing the symbol.
            line: Line number (0-indexed).
            col: Column number (0-indexed).
            include_imports: Whether to include import statements.

        Returns:
            Dict with 'usages', 'imports', 'total_usages', 'total_imports'.
        """
        # Get all references from LSP
        refs = await self.client.request_references(file_path, line, col)

        if not refs:
            return {
                "usages": [],
                "imports": [],
                "total_usages": 0,
                "total_imports": 0,
            }

        # Filter imports
        import_filter = get_filter_for_file(file_path)
        usages, imports = await import_filter.filter_references(refs, self._read_line)

        # Filter out the definition itself (LSP includes it in references)
        def_file = str(Path(file_path).resolve())
        usages = [u for u in usages if not (u.get("file") == def_file and u.get("line") == line)]

        if not include_imports:
            return {
                "usages": usages,
                "imports": imports,
                "total_usages": len(usages),
                "total_imports": len(imports),
            }

        return {
            "usages": usages + imports,
            "imports": imports,
            "total_usages": len(usages) + len(imports),
            "total_imports": len(imports),
        }

    async def get_usage_summary(
        self,
        file_path: str | Path,
        line: int,
        col: int,
        symbol_name: str | None = None,
    ) -> dict:
        """Get comprehensive usage summary for a symbol.

        Args:
            file_path: Path to file containing the symbol.
            line: Line number (0-indexed).
            col: Column number (0-indexed).
            symbol_name: Optional symbol name for display.

        Returns:
            Dict with usage counts, impact level, and grouped usages.
        """
        result = await self.find_usages(file_path, line, col, include_imports=False)
        usages = result["usages"]
        imports = result["imports"]

        # Calculate impact
        count = len(usages)
        if count > 10:
            impact = "high"
        elif count >= 3:
            impact = "medium"
        else:
            impact = "low"

        # Group by file
        by_file: dict[str, list[dict]] = {}
        for u in usages:
            f = u.get("file", "unknown")
            if f not in by_file:
                by_file[f] = []
            by_file[f].append(u)

        return {
            "symbol": symbol_name,
            "total_usages": count,
            "total_imports": len(imports),
            "impact": impact,
            "files_affected": len(by_file),
            "usages_by_file": by_file,
            "usages": usages[:20],  # Limit for display
            "imports": imports,
        }

    async def find_dead_code(
        self,
        path: str | Path | None = None,
        include_private: bool = False,
        accurate: bool = False,
    ) -> list[dict]:
        """Find functions/classes with 0 usages (excluding imports).

        TWO MODES:
        - Fast (default): Batched ripgrep + within-file check
          - Speed: ~2s for 50 symbols
          - Accuracy: 85%
          - Languages: ALL (text search)
          - Use for: Daily dev, CI/CD, large codebases

        - Accurate (accurate=True): LSP references per symbol
          - Speed: ~20s for 50 symbols
          - Accuracy: 95%+
          - Languages: Python (tested), others via multilspy (untested)
          - Use for: Before deleting code, before major refactor

        LANGUAGE SUPPORT:
        - Python: Full (LSP + import filtering + entry point detection)
        - JS/TS/Go/Rust/Java: Partial (ripgrep works, LSP untested)

        To scale to other languages (3-4 days each):
        1. Already works: LSP refs (multilspy), ripgrep deadcode
        2. Need to add: tree-sitter-{lang} complexity, import filter patterns

        IMPLEMENTATION FILES:
        - This file: packages/lsp/src/aurora_lsp/analysis.py
        - Ripgrep search: _batched_ripgrep_search() in this file
        - Import filters: packages/lsp/src/aurora_lsp/filters.py (Python only)
        - LSP client: packages/lsp/src/aurora_lsp/client.py

        Args:
            path: Directory or file to analyze. Defaults to workspace.
            include_private: Whether to include private symbols (_name).
            accurate: If True, use LSP references (95%+ accuracy, ~20s).
                     If False (default), use batched ripgrep (85% accuracy, ~2s).

        Returns:
            List of dead code items with file, line, name, kind, imports.
        """
        # Phase 1: Collect ALL symbols from ALL files
        all_symbols: list[dict] = []  # {name, kind, line, file}
        files = self._get_source_files(path)

        for file_path in files:
            try:
                symbols = await self.client.request_document_symbols(file_path)
                if not symbols:
                    continue

                import_filter = get_filter_for_file(file_path)

                for symbol in self._flatten_symbols(symbols):
                    kind = symbol.get("kind")
                    if kind not in self.ANALYZABLE_KINDS:
                        continue

                    name = symbol.get("name", "")

                    if not include_private and name.startswith("_"):
                        continue

                    if name.startswith("test_"):
                        continue

                    if len(name) < 3:
                        continue

                    # Skip anonymous/synthetic names from LSP
                    # LSP labels anonymous callbacks as "router.get('/') callback"
                    # and unnamed arrow functions as "<function>"
                    if "callback" in name.lower() or name.startswith("<"):
                        continue

                    # Skip language-specific framework symbol names
                    # (e.g., queryFn, onSuccess, headers — consumed by frameworks)
                    skip_names = get_skip_deadcode_names(str(file_path))
                    if name in skip_names:
                        continue

                    sel_range = symbol.get("selectionRange", symbol.get("range", {}))
                    start = sel_range.get("start", {})
                    sym_line = start.get("line", 0)

                    line_content = await self._read_line(str(file_path), sym_line)
                    if import_filter.is_import_line(line_content):
                        continue

                    # Skip functions defined as callbacks to known methods
                    # e.g., arr.map(function myMapper(...)) or .then(handler)
                    cb_methods = get_callback_methods(str(file_path))
                    if cb_methods and self._is_callback_context(line_content, cb_methods):
                        continue

                    # Python-only: skip stdlib type imports (TS handles via `import type`)
                    ext = Path(str(file_path)).suffix.lower()
                    if kind == SymbolKind.CLASS and sym_line < 50 and ext in (".py", ".pyi"):
                        type_import_names = {
                            "Any",
                            "Optional",
                            "Union",
                            "List",
                            "Dict",
                            "Set",
                            "Tuple",
                            "Callable",
                            "Iterator",
                            "Iterable",
                            "Generator",
                            "Sequence",
                            "Mapping",
                            "MutableMapping",
                            "Type",
                            "TypeVar",
                            "Generic",
                            "Protocol",
                            "Path",
                            "datetime",
                            "timezone",
                            "timedelta",
                            "cast",
                            "overload",
                            "TYPE_CHECKING",
                        }
                        if name in type_import_names:
                            continue

                    # Skip entry points and nested functions
                    # Check line above for decorator
                    prev_line = ""
                    if sym_line > 0:
                        prev_line = await self._read_line(str(file_path), sym_line - 1)
                    if self._is_entry_point_or_nested(name, file_path, prev_line):
                        continue

                    all_symbols.append(
                        {
                            "name": name,
                            "kind": kind,
                            "line": sym_line,
                            "col": start.get("character", 0),
                            "file": str(file_path),
                        }
                    )

            except Exception as e:
                logger.warning(f"Error getting symbols from {file_path}: {e}")
                continue

        if not all_symbols:
            return []

        dead = []

        if accurate:
            # Phase 2 (accurate): LSP references for each symbol (95%+ accuracy, slower)
            logger.info(f"Accurate mode: checking {len(all_symbols)} symbols via LSP references")
            for sym in all_symbols:
                try:
                    # Get usages via LSP (excludes imports automatically)
                    result = await self.find_usages(
                        sym["file"], sym["line"], sym.get("col", 10), include_imports=False
                    )
                    usage_count = result.get("total_usages", 0)

                    # Dead if 0 usages (definition itself is not counted as usage)
                    if usage_count == 0:
                        dead.append(
                            {
                                "file": sym["file"],
                                "line": sym["line"],
                                "name": sym["name"],
                                "kind": SymbolKind(sym["kind"]).name.lower(),
                                "imports": result.get("total_imports", 0),
                            }
                        )
                except Exception as e:
                    logger.debug(f"LSP reference check failed for {sym['name']}: {e}")
                    continue
        else:
            # Phase 2 (fast): ONE batched ripgrep call for ALL symbols (80-85% accuracy)
            symbol_names = list(set(s["name"] for s in all_symbols))
            # Derive ripgrep file types from the files being analyzed
            rg_types = set()
            for s in all_symbols:
                ext = Path(s["file"]).suffix.lower()
                rg_types.add(_ext_to_rg_type(ext))
            file_types = sorted(rg_types) if rg_types else ["py"]
            usage_map = _batched_ripgrep_search(symbol_names, self.workspace, file_types=file_types)

            # Phase 3: Check which symbols have no external usages
            for sym in all_symbols:
                files_containing = usage_map.get(sym["name"], [])

                # Normalize definition file path for comparison
                sym_file = Path(sym["file"])
                if sym_file.is_absolute():
                    try:
                        def_file = "./" + str(sym_file.relative_to(self.workspace))
                    except ValueError:
                        def_file = "./" + str(sym_file)
                else:
                    def_file = "./" + str(sym_file)

                # Remove definition file from matches
                other_files = [f for f in files_containing if f != def_file]

                # Also check for usages WITHIN the same file (nested functions, local calls)
                # If the symbol appears more than once in its own file, it's being used
                within_file_usages = 0
                if def_file in files_containing:
                    try:
                        # Count occurrences in the definition file
                        file_content = await self._read_file(sym["file"])
                        # Count word-boundary matches (simple approximation)
                        import re

                        within_file_usages = len(
                            re.findall(rf"\b{re.escape(sym['name'])}\b", file_content)
                        )
                        # Subtract 1 for the definition itself
                        within_file_usages = max(0, within_file_usages - 1)
                    except Exception:
                        pass

                # Dead if no other files AND no usages within own file
                if len(other_files) == 0 and within_file_usages == 0:
                    dead.append(
                        {
                            "file": sym["file"],
                            "line": sym["line"],
                            "name": sym["name"],
                            "kind": SymbolKind(sym["kind"]).name.lower(),
                            "imports": 0,
                        }
                    )

        return dead

    async def get_callers(
        self,
        file_path: str | Path,
        line: int,
        col: int,
    ) -> list[dict]:
        """Find functions that call this symbol (incoming calls).

        Uses references and determines containing function for each.

        Args:
            file_path: Path to file containing the symbol.
            line: Line number (0-indexed).
            col: Column number (0-indexed).

        Returns:
            List of caller functions with file, line, name.
        """
        # Get usages (excluding imports)
        usage_result = await self.find_usages(file_path, line, col, include_imports=False)
        usages = usage_result["usages"]

        callers = []
        seen = set()

        for ref in usages:
            ref_file = ref.get("file", "")
            ref_line = ref.get("line", 0)

            # Skip the definition itself
            if self._is_same_location(ref, file_path, line):
                continue

            # Get containing symbol
            container = await self._get_containing_symbol(ref_file, ref_line)
            if container:
                # Deduplicate by container
                key = (container["file"], container["line"], container["name"])
                if key not in seen:
                    seen.add(key)
                    callers.append(container)

        return callers

    async def get_callees(
        self,
        file_path: str | Path,
        line: int,
        col: int,
    ) -> list[dict]:
        """Find functions called by this symbol (outgoing calls).

        Uses tree-sitter to parse the function body and find all call expressions.

        LANGUAGE SUPPORT:
        - Python: Full (tree-sitter-python)
        - Others: Not yet implemented (returns empty)

        Args:
            file_path: Path to file containing the symbol.
            line: Line number (0-indexed).
            col: Column number (0-indexed).

        Returns:
            List of called functions with name, file (if local), line.
        """
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.workspace / file_path

        # Check language support
        call_node_type = get_call_node_type(str(file_path))
        func_def_types = get_function_def_types(str(file_path))

        if not call_node_type or not func_def_types:
            return []  # Language not supported

        try:
            import importlib

            import tree_sitter

            # Get language config for dynamic parser loading
            config = get_config(str(file_path))
            if config is None or config.tree_sitter_module is None:
                return []

            ts_module = importlib.import_module(config.tree_sitter_module)

            # Handle tree_sitter_typescript which exposes language_typescript()/language_tsx()
            if config.tree_sitter_module == "tree_sitter_typescript":
                if file_path.suffix == ".tsx":
                    lang = tree_sitter.Language(ts_module.language_tsx())
                else:
                    lang = tree_sitter.Language(ts_module.language_typescript())
            else:
                lang = tree_sitter.Language(ts_module.language())

            parser = tree_sitter.Parser(lang)

            # Read and parse file
            source = file_path.read_bytes()
            tree = parser.parse(source)
            source_text = source.decode("utf-8")

            # Find the function/class at the given line
            target_node = None
            target_line = line  # 0-indexed

            def find_containing_def(node):
                nonlocal target_node
                node_start = node.start_point[0]
                node_end = node.end_point[0]

                if node.type in func_def_types:
                    if node_start <= target_line <= node_end:
                        # This def contains our line - check if there's a more specific one
                        target_node = node
                        for child in node.children:
                            find_containing_def(child)
                        return

                for child in node.children:
                    find_containing_def(child)

            find_containing_def(tree.root_node)

            if target_node is None:
                return []

            # Find all call expressions within the target function
            callees = []
            seen_names = set()

            # Language-specific built-ins and common methods to skip
            skip_names = _get_skip_names(config.name)

            def find_calls(node):
                if node.type == call_node_type:
                    # Extract the function name being called
                    call_name = None
                    func_node = node.child_by_field_name("function")
                    if func_node:
                        call_name = source_text[func_node.start_byte : func_node.end_byte]
                    else:
                        # Java method_invocation: object.name(args)
                        name_node = node.child_by_field_name("name")
                        if name_node:
                            method_name = source_text[name_node.start_byte : name_node.end_byte]
                            obj_node = node.child_by_field_name("object")
                            if obj_node:
                                obj_name = source_text[obj_node.start_byte : obj_node.end_byte]
                                call_name = f"{obj_name}.{method_name}"
                            else:
                                call_name = method_name

                    if call_name:
                        # Clean up the name
                        # For "self.method()" / "this.method()", extract "method"
                        # For "obj.method()", extract "obj.method" or just method
                        base_name = call_name
                        if "." in call_name:
                            parts = call_name.split(".")
                            if parts[0] in ("self", "this"):
                                base_name = parts[-1]  # Just the method name
                            else:
                                base_name = parts[-1]  # Last part for filtering

                        # Skip duplicates, built-ins, and dunder methods
                        if (
                            call_name not in seen_names
                            and base_name not in skip_names
                            and not base_name.startswith("__")
                        ):
                            seen_names.add(call_name)
                            callees.append(
                                {
                                    "name": call_name,
                                    "line": node.start_point[0] + 1,  # 1-indexed for output
                                }
                            )

                for child in node.children:
                    find_calls(child)

            find_calls(target_node)

            return callees[:20]  # Limit to 20 callees

        except ImportError:
            logger.debug("tree-sitter not available for get_callees")
            return []
        except Exception as e:
            logger.debug(f"get_callees failed: {e}")
            return []

    async def _get_containing_symbol(
        self,
        file_path: str | Path,
        line: int,
    ) -> dict | None:
        """Get the function/method containing a line.

        Args:
            file_path: Path to file.
            line: Line number to find container for.

        Returns:
            Symbol dict with file, line, name, or None.
        """
        try:
            symbols = await self.client.request_document_symbols(file_path)
            if not symbols:
                return None

            # Find deepest symbol containing the line
            containing = None

            for symbol in self._flatten_symbols(symbols):
                kind = symbol.get("kind")
                if kind not in {SymbolKind.FUNCTION, SymbolKind.METHOD}:
                    continue

                range_info = symbol.get("range", {})
                start = range_info.get("start", {}).get("line", 0)
                end = range_info.get("end", {}).get("line", 0)

                if start <= line <= end:
                    # Prefer the most specific (deepest) container
                    if containing is None or start > containing.get("line", 0):
                        containing = {
                            "file": str(file_path),
                            "line": start,
                            "name": symbol.get("name", ""),
                            "kind": SymbolKind(kind).name.lower(),
                        }

            return containing

        except Exception as e:
            logger.debug(f"Error getting containing symbol: {e}")
            return None

    def _flatten_symbols(self, symbols: list) -> list[dict]:
        """Flatten nested symbol tree from LSP.

        Args:
            symbols: Nested symbol list from document_symbols.

        Returns:
            Flat list of all symbols.
        """
        result = []
        for s in symbols:
            result.append(s)
            children = s.get("children", [])
            if children:
                result.extend(self._flatten_symbols(children))
        return result

    def _get_source_files(self, path: str | Path | None = None) -> list[Path]:
        """Get all source files in a directory.

        Args:
            path: Directory or file path. Defaults to workspace.

        Returns:
            List of source file paths.
        """
        target = Path(path) if path else self.workspace

        if target.is_file():
            return [target]

        # Supported extensions
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb"}

        files = []
        for ext in extensions:
            files.extend(target.rglob(f"*{ext}"))

        # Filter out common non-source directories
        exclude_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}
        files = [f for f in files if not any(d in f.parts for d in exclude_dirs)]

        return sorted(files)

    def _is_same_location(
        self,
        ref: dict,
        file_path: str | Path,
        line: int,
    ) -> bool:
        """Check if a reference is at the same location as given file/line."""
        ref_file = Path(ref.get("file", ""))
        target_file = Path(file_path)

        # Normalize paths
        try:
            ref_file = ref_file.resolve()
            target_file = target_file.resolve()
        except Exception:
            pass

        return ref_file == target_file and ref.get("line") == line

    async def _read_line(self, file_path: str, line: int) -> str:
        """Read a specific line from a file (async wrapper).

        Args:
            file_path: Path to file.
            line: Line number (0-indexed).

        Returns:
            Line content.
        """
        # Use cached file content if available
        if file_path not in self._file_cache:
            try:
                path = Path(file_path)
                if not path.is_absolute():
                    path = self.workspace / path
                content = path.read_text(encoding="utf-8", errors="replace")
                self._file_cache[file_path] = content.splitlines()
            except Exception:
                return ""

        lines = self._file_cache[file_path]
        if 0 <= line < len(lines):
            return lines[line]
        return ""

    async def _read_file(self, file_path: str) -> str:
        """Read full file content (async wrapper, cached).

        Args:
            file_path: Path to file.

        Returns:
            Full file content as string.
        """
        # Ensure file is in cache
        if file_path not in self._file_cache:
            try:
                path = Path(file_path)
                if not path.is_absolute():
                    path = self.workspace / path
                content = path.read_text(encoding="utf-8", errors="replace")
                self._file_cache[file_path] = content.splitlines()
            except Exception:
                return ""

        # Join cached lines back to full content
        return "\n".join(self._file_cache[file_path])
