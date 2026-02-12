"""AuroraLSP - High-level facade for LSP integration.

Provides a simple, synchronous API for Aurora CLI and MCP.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import nest_asyncio

from aurora_lsp.analysis import CodeAnalyzer
from aurora_lsp.client import AuroraLSPClient
from aurora_lsp.diagnostics import DiagnosticsFormatter


# Allow nested event loops (needed when called from MCP server)
nest_asyncio.apply()

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
        return self._run_async(self.analyzer.find_usages(file_path, line, col, include_imports))

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
        return self._run_async(self.analyzer.get_usage_summary(file_path, line, col, symbol_name))

    # =========================================================================
    # IMPORTANT: Dead Code Detection
    # =========================================================================

    def find_dead_code(
        self,
        path: str | Path | None = None,
        include_private: bool = False,
        accurate: bool = False,
    ) -> list[dict]:
        """Find functions/classes with 0 usages.

        TWO MODES:
        - Fast (default): ~2s, 85% accuracy, ALL languages (ripgrep)
        - Accurate: ~20s, 95%+ accuracy, Python tested (LSP refs)

        Use fast for daily dev/CI, accurate before deleting code.

        LANGUAGE SUPPORT:
        - Python: Full (LSP + filters)
        - Others: Partial (ripgrep works, LSP untested)

        Implementation: packages/lsp/src/aurora_lsp/analysis.py

        Args:
            path: Directory or file to analyze. Defaults to workspace.
            include_private: Whether to include private symbols (_name).
            accurate: If True, use LSP references (95%+ accuracy, ~20s).
                     If False (default), use batched ripgrep (85% accuracy, ~2s).

        Returns:
            List of dead code items, each with:
            - file: File path
            - line: Line number
            - name: Symbol name
            - kind: 'function', 'class', or 'method'
            - imports: Number of times imported (but never used)
        """
        return self._run_async(self.analyzer.find_dead_code(path, include_private, accurate))

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
        return self._run_async(self.diagnostics.get_all_diagnostics(path, severity_filter))

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
        return self._run_async(self.analyzer.get_callers(file_path, line, col))

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
        return self._run_async(self.analyzer.get_callees(file_path, line, col))

    # =========================================================================
    # Import Analysis
    # =========================================================================

    def get_imported_by(self, module_path: str | Path) -> dict:
        """Find all files that import a given module.

        Uses ripgrep for fast text search across the codebase.
        Supports Python (.py) and JS/TS (.js/.jsx/.ts/.tsx) imports.

        Args:
            module_path: Path to module file (e.g., "src/utils.py" or "src/utils.ts")

        Returns:
            Dict with:
            - module: The queried module name
            - imported_by: List of files that import this module
            - import_count: Total number of importing files
        """
        import re
        import subprocess

        module_path = Path(module_path)
        if not module_path.is_absolute():
            module_path = self.workspace / module_path

        ext = module_path.suffix.lower()
        is_js_ts = ext in (".js", ".jsx", ".mjs", ".ts", ".tsx")

        if is_js_ts:
            return self._get_imported_by_js_ts(module_path)

        if ext == ".go":
            return self._get_imported_by_go(module_path)

        if ext == ".java":
            return self._get_imported_by_java(module_path)

        # Python module resolution
        # "src/aurora_lsp/analysis.py" -> "aurora_lsp.analysis"
        if module_path.suffix == ".py":
            parts = module_path.with_suffix("").parts
            module_name = None
            for i, part in enumerate(parts):
                if part == "src" and i + 1 < len(parts):
                    remaining = parts[i + 1 :]
                    if remaining:
                        module_name = ".".join(remaining)
                        break
            if module_name is None:
                module_name = module_path.stem
        else:
            module_name = module_path.stem

        module_base = module_name.split(".")[-1] if "." in module_name else module_name

        patterns = [
            f"^\\s*from {re.escape(module_name)} import",
            f"^\\s*import {re.escape(module_name)}\\b",
        ]

        if "." in module_name:
            parent = ".".join(module_name.split(".")[:-1])
            patterns.append(f"^from {re.escape(parent)} import.*\\b{re.escape(module_base)}\\b")

        combined_pattern = "|".join(f"({p})" for p in patterns)

        try:
            result = subprocess.run(
                ["rg", "-l", "--type", "py", "-e", combined_pattern, str(self.workspace)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            importing_files = []
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    file_path = Path(line)
                    if file_path.resolve() != module_path.resolve():
                        try:
                            rel_path = file_path.relative_to(self.workspace)
                            importing_files.append(str(rel_path))
                        except ValueError:
                            importing_files.append(str(file_path))

            return {
                "module": module_name,
                "imported_by": sorted(importing_files),
                "import_count": len(importing_files),
            }

        except subprocess.TimeoutExpired:
            return {"module": module_name, "imported_by": [], "import_count": 0, "error": "Search timed out"}
        except FileNotFoundError:
            return {"module": module_name, "imported_by": [], "import_count": 0, "error": "ripgrep not installed"}

    def _get_imported_by_js_ts(self, module_path: Path) -> dict:
        """Find JS/TS files that import a given module.

        Handles ESM imports, require(), and index file resolution.

        Args:
            module_path: Absolute path to the module file.

        Returns:
            Dict with module, imported_by, import_count.
        """
        import re
        import subprocess

        # Build the relative module path without extension
        # e.g., /workspace/src/utils/auth.ts -> src/utils/auth
        try:
            rel_path = module_path.relative_to(self.workspace)
        except ValueError:
            rel_path = module_path

        # Strip extension for matching (imports usually omit it)
        module_stem = str(rel_path.with_suffix(""))
        module_name = module_stem  # For display

        # Handle index files: src/utils/index.ts can be imported as src/utils
        is_index = rel_path.stem == "index"
        module_dir = str(rel_path.parent) if is_index else None

        # Build patterns to match various import styles
        # We need to match relative paths like './utils/auth' or '../utils/auth'
        # The exact relative path depends on the importing file, so we search for
        # the basename and key path segments
        base_name = rel_path.stem  # "auth"
        parent_name = rel_path.parent.name  # "utils"

        patterns = []

        # Match the module name in import/require statements
        # Pattern: from '...<path_segment>/<basename>' or require('...<path_segment>/<basename>')
        if parent_name and parent_name != ".":
            # Match: from './utils/auth' or from '../utils/auth' etc.
            path_fragment = re.escape(f"{parent_name}/{base_name}")
            patterns.append(f"(?:from|require)\\s*\\(?\\s*['\"].*{path_fragment}['\"]")
        else:
            path_fragment = re.escape(base_name)
            patterns.append(f"(?:from|require)\\s*\\(?\\s*['\"].*/{path_fragment}['\"]")

        # For index files, also match imports of the directory
        if is_index and module_dir:
            dir_name = re.escape(rel_path.parent.name)
            patterns.append(f"(?:from|require)\\s*\\(?\\s*['\"].*/{dir_name}['\"]")

        # Determine ripgrep file types
        ext = module_path.suffix.lower()
        rg_types = ["ts", "js"] if ext in (".ts", ".tsx") else ["js", "ts"]

        combined_pattern = "|".join(f"({p})" for p in patterns)
        type_flags = []
        for t in rg_types:
            type_flags.extend(["-t", t])

        try:
            result = subprocess.run(
                ["rg", "-l", *type_flags, "-e", combined_pattern, str(self.workspace)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            importing_files = []
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    file_path = Path(line)
                    if file_path.resolve() != module_path.resolve():
                        try:
                            rel = file_path.relative_to(self.workspace)
                            importing_files.append(str(rel))
                        except ValueError:
                            importing_files.append(str(file_path))

            return {
                "module": module_name,
                "imported_by": sorted(importing_files),
                "import_count": len(importing_files),
            }

        except subprocess.TimeoutExpired:
            return {"module": module_name, "imported_by": [], "import_count": 0, "error": "Search timed out"}
        except FileNotFoundError:
            return {"module": module_name, "imported_by": [], "import_count": 0, "error": "ripgrep not installed"}

    def _get_imported_by_java(self, module_path: Path) -> dict:
        """Find Java files that import the class in this file.

        Java imports are fully-qualified class names derived from
        the package declaration + class name.

        Args:
            module_path: Absolute path to the Java source file.

        Returns:
            Dict with module, imported_by, import_count.
        """
        import re
        import subprocess

        # Extract package name from the file's package declaration
        # e.g., "package com.sopromadze.blogapi.service.impl;" -> com.sopromadze.blogapi.service.impl
        package_name = ""
        try:
            for line in module_path.read_text(errors="replace").splitlines():
                match = re.match(r"^\s*package\s+([\w.]+)\s*;", line)
                if match:
                    package_name = match.group(1)
                    break
        except Exception:
            pass

        # Full class import path = package + filename (without .java)
        class_name = module_path.stem
        if package_name:
            fq_class = f"{package_name}.{class_name}"
        else:
            fq_class = class_name

        module_name = fq_class

        # Search for import statements containing this class
        # Matches: import com.example.MyClass; or import com.example.*;
        patterns = [
            rf"^\s*import\s+{re.escape(fq_class)}\s*;",
            rf"^\s*import\s+static\s+{re.escape(fq_class)}\.",
        ]
        # Also match wildcard imports of the package
        if package_name:
            patterns.append(rf"^\s*import\s+{re.escape(package_name)}\.\*\s*;")

        combined_pattern = "|".join(f"({p})" for p in patterns)

        try:
            result = subprocess.run(
                ["rg", "-l", "--type", "java", "-e", combined_pattern, str(self.workspace)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            importing_files = []
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    file_path = Path(line)
                    if file_path.resolve() != module_path.resolve():
                        try:
                            rel = file_path.relative_to(self.workspace)
                            importing_files.append(str(rel))
                        except ValueError:
                            importing_files.append(str(file_path))

            return {
                "module": module_name,
                "imported_by": sorted(importing_files),
                "import_count": len(importing_files),
            }

        except subprocess.TimeoutExpired:
            return {"module": module_name, "imported_by": [], "import_count": 0, "error": "Search timed out"}
        except FileNotFoundError:
            return {"module": module_name, "imported_by": [], "import_count": 0, "error": "ripgrep not installed"}

    def _get_imported_by_go(self, module_path: Path) -> dict:
        """Find Go files that import the package containing this file.

        Go imports are package-level, so we find the package import path
        and search for it in import statements.

        Args:
            module_path: Absolute path to the Go source file.

        Returns:
            Dict with module, imported_by, import_count.
        """
        import re
        import subprocess

        # Determine the Go package import path from go.mod + relative path
        # e.g., if go.mod has "module github.com/user/repo" and file is at
        # internal/album/api.go, the import path is "github.com/user/repo/internal/album"
        try:
            rel_path = module_path.relative_to(self.workspace)
        except ValueError:
            rel_path = module_path

        # Find go.mod to get module name
        go_mod = self.workspace / "go.mod"
        module_prefix = ""
        if go_mod.exists():
            for line in go_mod.read_text().splitlines():
                if line.startswith("module "):
                    module_prefix = line.split("module ", 1)[1].strip()
                    break

        # Package path = module_prefix + directory of the file
        pkg_dir = str(rel_path.parent)
        if pkg_dir == ".":
            pkg_import = module_prefix
        elif module_prefix:
            pkg_import = f"{module_prefix}/{pkg_dir}"
        else:
            pkg_import = pkg_dir

        module_name = pkg_import

        # Also get just the package directory name for local imports
        pkg_name = rel_path.parent.name

        # Build pattern: match import lines containing the package path
        # Go imports: import "pkg/path" or within import ( ... ) blocks
        pattern = re.escape(pkg_import)

        try:
            result = subprocess.run(
                ["rg", "-l", "--type", "go", "-e", pattern, str(self.workspace)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            importing_files = []
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    file_path = Path(line)
                    # Exclude files in the same package directory
                    if file_path.resolve().parent != module_path.resolve().parent:
                        try:
                            rel = file_path.relative_to(self.workspace)
                            importing_files.append(str(rel))
                        except ValueError:
                            importing_files.append(str(file_path))

            return {
                "module": module_name,
                "imported_by": sorted(importing_files),
                "import_count": len(importing_files),
            }

        except subprocess.TimeoutExpired:
            return {"module": module_name, "imported_by": [], "import_count": 0, "error": "Search timed out"}
        except FileNotFoundError:
            return {"module": module_name, "imported_by": [], "import_count": 0, "error": "ripgrep not installed"}

    # =========================================================================
    # Utility Methods
    # =========================================================================

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
