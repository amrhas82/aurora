"""AuroraLSP - High-level facade for LSP integration.

Provides a simple, synchronous API for Aurora CLI and MCP.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from aurora_lsp.client import AuroraLSPClient
from aurora_lsp.analysis import CodeAnalyzer
from aurora_lsp.diagnostics import DiagnosticsFormatter

logger = logging.getLogger(__name__)


class AuroraLSP:
    """High-level LSP interface for Aurora.

    Provides synchronous methods that wrap async LSP operations.
    Designed for use in CLI commands and MCP tools.

    Example:
        lsp = AuroraLSP("/path/to/workspace")

        # Find usages (excluding imports)
        result = lsp.find_usages("src/main.py", 10, 5)
        print(f"Found {result['total_usages']} usages")

        # Find dead code
        dead = lsp.find_dead_code()
        for item in dead:
            print(f"Unused: {item['name']} in {item['file']}")

        # Get linting diagnostics
        diags = lsp.lint("src/")
        print(f"Found {diags['total_errors']} errors")

        lsp.close()
    """

    def __init__(self, workspace: str | Path | None = None):
        """Initialize AuroraLSP.

        Args:
            workspace: Workspace root directory. Defaults to current directory.
        """
        self.workspace = Path(workspace or Path.cwd()).resolve()
        self._client: AuroraLSPClient | None = None
        self._analyzer: CodeAnalyzer | None = None
        self._diagnostics: DiagnosticsFormatter | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def client(self) -> AuroraLSPClient:
        """Get or create LSP client."""
        if self._client is None:
            self._client = AuroraLSPClient(self.workspace)
        return self._client

    @property
    def analyzer(self) -> CodeAnalyzer:
        """Get or create code analyzer."""
        if self._analyzer is None:
            self._analyzer = CodeAnalyzer(self.client, self.workspace)
        return self._analyzer

    @property
    def diagnostics(self) -> DiagnosticsFormatter:
        """Get or create diagnostics formatter."""
        if self._diagnostics is None:
            self._diagnostics = DiagnosticsFormatter(self.client, self.workspace)
        return self._diagnostics

    def _run_async(self, coro) -> Any:
        """Run an async coroutine synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    # =========================================================================
    # VITAL: Import vs Usage
    # =========================================================================

    def find_usages(
        self,
        file_path: str | Path,
        line: int,
        col: int = 0,
        include_imports: bool = False,
    ) -> dict:
        """Find usages of a symbol (excluding imports by default).

        Args:
            file_path: Path to file containing the symbol.
            line: Line number (0-indexed).
            col: Column number (0-indexed).
            include_imports: Whether to include import statements.

        Returns:
            Dict with:
            - usages: List of usage locations with context
            - imports: List of import locations with context
            - total_usages: Count of actual usages
            - total_imports: Count of import statements
        """
        return self._run_async(
            self.analyzer.find_usages(file_path, line, col, include_imports)
        )

    def get_usage_summary(
        self,
        file_path: str | Path,
        line: int,
        col: int = 0,
        symbol_name: str | None = None,
    ) -> dict:
        """Get comprehensive usage summary for a symbol.

        Args:
            file_path: Path to file containing the symbol.
            line: Line number (0-indexed).
            col: Column number (0-indexed).
            symbol_name: Optional symbol name for display.

        Returns:
            Dict with:
            - symbol: Symbol name
            - total_usages: Count of actual usages
            - total_imports: Count of imports
            - impact: 'low', 'medium', or 'high'
            - files_affected: Number of files with usages
            - usages_by_file: Usages grouped by file
            - usages: Top 20 usage locations
            - imports: All import locations
        """
        return self._run_async(
            self.analyzer.get_usage_summary(file_path, line, col, symbol_name)
        )

    # =========================================================================
    # IMPORTANT: Dead Code Detection
    # =========================================================================

    def find_dead_code(
        self,
        path: str | Path | None = None,
        include_private: bool = False,
    ) -> list[dict]:
        """Find functions/classes with 0 usages.

        Args:
            path: Directory or file to analyze. Defaults to workspace.
            include_private: Whether to include private symbols (_name).

        Returns:
            List of dead code items, each with:
            - file: File path
            - line: Line number
            - name: Symbol name
            - kind: 'function', 'class', or 'method'
            - imports: Number of times imported (but never used)
        """
        return self._run_async(
            self.analyzer.find_dead_code(path, include_private)
        )

    # =========================================================================
    # IMPORTANT: Linting
    # =========================================================================

    def lint(
        self,
        path: str | Path | None = None,
        severity_filter: int | None = None,
    ) -> dict:
        """Get linting diagnostics for file(s).

        Args:
            path: File or directory to lint. Defaults to workspace.
            severity_filter: Minimum severity (1=error, 2=warning, etc.).

        Returns:
            Dict with:
            - errors: List of errors
            - warnings: List of warnings
            - hints: List of hints
            - total_errors: Error count
            - total_warnings: Warning count
            - total_hints: Hint count
        """
        return self._run_async(
            self.diagnostics.get_all_diagnostics(path, severity_filter)
        )

    def lint_file(self, file_path: str | Path) -> dict:
        """Get linting diagnostics for a single file.

        Args:
            file_path: Path to file.

        Returns:
            Dict with errors, warnings, hints lists.
        """
        return self._run_async(
            self.diagnostics.get_file_diagnostics(file_path)
        )

    # =========================================================================
    # OPTIONAL: Call Hierarchy (callers/callees)
    # =========================================================================

    def get_callers(
        self,
        file_path: str | Path,
        line: int,
        col: int = 0,
    ) -> list[dict]:
        """Find functions that call this symbol.

        Args:
            file_path: Path to file containing the symbol.
            line: Line number (0-indexed).
            col: Column number (0-indexed).

        Returns:
            List of caller functions, each with:
            - file: File path
            - line: Line number
            - name: Function name
            - kind: 'function' or 'method'
        """
        return self._run_async(
            self.analyzer.get_callers(file_path, line, col)
        )

    def get_callees(
        self,
        file_path: str | Path,
        line: int,
        col: int = 0,
    ) -> list[dict]:
        """Find functions called by this symbol.

        Note: Limited support. May return empty list.

        Args:
            file_path: Path to file containing the symbol.
            line: Line number (0-indexed).
            col: Column number (0-indexed).

        Returns:
            List of called functions (may be empty).
        """
        return self._run_async(
            self.analyzer.get_callees(file_path, line, col)
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def find_symbol(self, name: str, path: str | Path | None = None) -> dict | None:
        """Find a symbol by name in the workspace.

        Args:
            name: Symbol name to find.
            path: Limit search to this path.

        Returns:
            Dict with file, line, col if found, or None.
        """
        # Get all source files
        target = Path(path) if path else self.workspace
        if target.is_file():
            files = [target]
        else:
            extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"}
            files = []
            for ext in extensions:
                files.extend(target.rglob(f"*{ext}"))

        # Search for symbol
        for file_path in files:
            try:
                symbols = self._run_async(
                    self.client.request_document_symbols(file_path)
                )
                for symbol in self._flatten_symbols(symbols or []):
                    if symbol.get("name") == name:
                        range_info = symbol.get("range", {})
                        start = range_info.get("start", {})
                        return {
                            "file": str(file_path),
                            "line": start.get("line", 0),
                            "col": start.get("character", 0),
                            "kind": symbol.get("kind"),
                        }
            except Exception:
                continue

        return None

    def _flatten_symbols(self, symbols: list) -> list[dict]:
        """Flatten nested symbol tree."""
        result = []
        for s in symbols:
            result.append(s)
            children = s.get("children", [])
            if children:
                result.extend(self._flatten_symbols(children))
        return result

    def close(self) -> None:
        """Close all language server connections."""
        if self._client:
            self._run_async(self._client.close())
            self._client = None
            self._analyzer = None
            self._diagnostics = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# =========================================================================
# Convenience Functions
# =========================================================================

def find_usages(
    file_path: str | Path,
    line: int,
    col: int = 0,
    workspace: str | Path | None = None,
) -> dict:
    """Find usages of a symbol (excluding imports).

    Convenience function that creates a temporary AuroraLSP instance.

    Args:
        file_path: Path to file containing the symbol.
        line: Line number (0-indexed).
        col: Column number (0-indexed).
        workspace: Workspace root. Defaults to file's parent.

    Returns:
        Dict with usages, imports, and counts.
    """
    ws = workspace or Path(file_path).parent
    with AuroraLSP(ws) as lsp:
        return lsp.find_usages(file_path, line, col)


def find_dead_code(
    path: str | Path | None = None,
    workspace: str | Path | None = None,
) -> list[dict]:
    """Find dead code in a directory.

    Convenience function that creates a temporary AuroraLSP instance.

    Args:
        path: Directory to analyze.
        workspace: Workspace root. Defaults to path.

    Returns:
        List of dead code items.
    """
    ws = workspace or path or Path.cwd()
    with AuroraLSP(ws) as lsp:
        return lsp.find_dead_code(path)


def lint(
    path: str | Path | None = None,
    workspace: str | Path | None = None,
) -> dict:
    """Lint a directory.

    Convenience function that creates a temporary AuroraLSP instance.

    Args:
        path: Directory to lint.
        workspace: Workspace root. Defaults to path.

    Returns:
        Dict with errors, warnings, hints.
    """
    ws = workspace or path or Path.cwd()
    with AuroraLSP(ws) as lsp:
        return lsp.lint(path)
