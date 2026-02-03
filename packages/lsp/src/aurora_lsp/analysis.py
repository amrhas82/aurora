"""Code analysis layer - dead code detection, usage summary, call hierarchy.

Built on top of LSP client and import filtering.
"""

from __future__ import annotations

import logging
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING

from aurora_lsp.filters import ImportFilter, get_filter_for_file

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

    def __init__(self, client: AuroraLSPClient, workspace: Path | str):
        """Initialize analyzer.

        Args:
            client: LSP client for making requests.
            workspace: Workspace root directory.
        """
        self.client = client
        self.workspace = Path(workspace).resolve()
        self._file_cache: dict[str, list[str]] = {}

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
        usages, imports = await import_filter.filter_references(
            refs, self._read_line
        )

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
    ) -> list[dict]:
        """Find functions/classes with 0 usages (excluding imports).

        Args:
            path: Directory or file to analyze. Defaults to workspace.
            include_private: Whether to include private symbols (_name).

        Returns:
            List of dead code items with file, line, name, kind.
        """
        dead = []
        files = self._get_source_files(path)

        for file_path in files:
            try:
                symbols = await self.client.request_document_symbols(file_path)
                if not symbols:
                    continue

                # Get import filter for this file type
                import_filter = get_filter_for_file(file_path)

                for symbol in self._flatten_symbols(symbols):
                    # Only check analyzable symbol kinds
                    kind = symbol.get("kind")
                    if kind not in self.ANALYZABLE_KINDS:
                        continue

                    name = symbol.get("name", "")

                    # Skip private/dunder unless requested
                    if not include_private and name.startswith("_"):
                        continue

                    # Skip test functions
                    if name.startswith("test_"):
                        continue

                    # Get symbol location - prefer selectionRange for accurate position
                    # selectionRange gives the actual symbol name position,
                    # while range gives the full extent (often starts at column 0)
                    sel_range = symbol.get("selectionRange", symbol.get("range", {}))
                    start = sel_range.get("start", {})
                    sym_line = start.get("line", 0)
                    sym_col = start.get("character", 0)

                    # Skip imported symbols (not actual definitions in this file)
                    # These appear when pyright reports imported names as symbols
                    line_content = await self._read_line(str(file_path), sym_line)
                    if import_filter.is_import_line(line_content):
                        continue

                    # Skip symbols that look like type imports (common pattern)
                    # These often appear at the top of files and are single-word classes
                    if kind == SymbolKind.CLASS and sym_line < 50:
                        # Check if this is a well-known type import name
                        type_import_names = {
                            "Any", "Optional", "Union", "List", "Dict", "Set", "Tuple",
                            "Callable", "Iterator", "Iterable", "Generator", "Sequence",
                            "Mapping", "MutableMapping", "Type", "TypeVar", "Generic",
                            "Protocol", "Path", "datetime", "timezone", "timedelta",
                            "cast", "overload", "TYPE_CHECKING",
                        }
                        if name in type_import_names:
                            continue

                    # Find usages
                    usage_result = await self.find_usages(
                        file_path, sym_line, sym_col, include_imports=False
                    )
                    usages = usage_result["usages"]

                    # Exclude the definition itself
                    usages = [
                        u for u in usages
                        if not self._is_same_location(u, file_path, sym_line)
                    ]

                    if len(usages) == 0:
                        dead.append({
                            "file": str(file_path),
                            "line": sym_line,
                            "name": name,
                            "kind": SymbolKind(kind).name.lower(),
                            "imports": usage_result["total_imports"],
                        })

            except Exception as e:
                logger.warning(f"Error analyzing {file_path}: {e}")
                continue

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

        Note: This is limited without full AST parsing. Returns empty
        list if call hierarchy is not supported by the language server.

        Args:
            file_path: Path to file containing the symbol.
            line: Line number (0-indexed).
            col: Column number (0-indexed).

        Returns:
            List of called functions (may be empty).
        """
        # Outgoing calls require parsing the function body
        # which is beyond basic LSP. Return empty for now.
        # Could be implemented with tree-sitter in the future.
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
        files = [
            f for f in files
            if not any(d in f.parts for d in exclude_dirs)
        ]

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
