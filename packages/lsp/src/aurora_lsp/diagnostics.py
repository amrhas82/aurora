"""Diagnostics (linting) wrapper for LSP.

Formats LSP diagnostics into Aurora-friendly output.
"""

from __future__ import annotations

from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from aurora_lsp.client import AuroraLSPClient


class DiagnosticSeverity(IntEnum):
    """LSP DiagnosticSeverity values."""

    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


class DiagnosticsFormatter:
    """Format and filter LSP diagnostics."""

    SEVERITY_NAMES = {
        DiagnosticSeverity.ERROR: "error",
        DiagnosticSeverity.WARNING: "warning",
        DiagnosticSeverity.INFORMATION: "info",
        DiagnosticSeverity.HINT: "hint",
    }

    def __init__(self, client: AuroraLSPClient, workspace: Path | str):
        """Initialize diagnostics formatter.

        Args:
            client: LSP client for making requests.
            workspace: Workspace root directory.
        """
        self.client = client
        self.workspace = Path(workspace).resolve()

    async def get_file_diagnostics(self, file_path: str | Path) -> dict:
        """Get diagnostics for a single file.

        Args:
            file_path: Path to file.

        Returns:
            Dict with errors, warnings, hints lists.
        """
        diags = await self.client.request_diagnostics(file_path)
        return self._format_diagnostics(diags, file_path)

    async def get_all_diagnostics(
        self,
        path: str | Path | None = None,
        severity_filter: int | None = None,
    ) -> dict:
        """Get diagnostics for all files in a directory.

        Args:
            path: Directory to scan. Defaults to workspace.
            severity_filter: Minimum severity (1=error, 2=warning, etc.).

        Returns:
            Dict with errors, warnings, hints lists and summary.
        """
        target = Path(path) if path else self.workspace

        if target.is_file():
            files = [target]
        else:
            # Get all source files
            extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"}
            files = []
            for ext in extensions:
                files.extend(target.rglob(f"*{ext}"))

            # Filter out common non-source directories
            exclude_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv"}
            files = [f for f in files if not any(d in f.parts for d in exclude_dirs)]

        all_errors = []
        all_warnings = []
        all_hints = []

        for file_path in sorted(files):
            try:
                diags = await self.client.request_diagnostics(file_path)
                formatted = self._format_diagnostics(diags, file_path)

                all_errors.extend(formatted["errors"])
                all_warnings.extend(formatted["warnings"])
                all_hints.extend(formatted["hints"])
            except Exception:
                continue

        # Apply severity filter
        if severity_filter:
            if severity_filter > DiagnosticSeverity.ERROR:
                all_errors = []
            if severity_filter > DiagnosticSeverity.WARNING:
                all_warnings = []
            if severity_filter > DiagnosticSeverity.INFORMATION:
                all_hints = []

        return {
            "errors": all_errors,
            "warnings": all_warnings,
            "hints": all_hints,
            "total_errors": len(all_errors),
            "total_warnings": len(all_warnings),
            "total_hints": len(all_hints),
        }

    def _format_diagnostics(
        self,
        diags: list[dict],
        file_path: str | Path,
    ) -> dict:
        """Format raw LSP diagnostics.

        Args:
            diags: Raw diagnostics from LSP.
            file_path: Source file path.

        Returns:
            Dict with errors, warnings, hints lists.
        """
        errors = []
        warnings = []
        hints = []

        # Make path relative for display
        try:
            rel_path = Path(file_path).relative_to(self.workspace)
        except ValueError:
            rel_path = Path(file_path)

        for d in diags:
            severity = d.get("severity", DiagnosticSeverity.HINT)
            range_info = d.get("range", {})
            start = range_info.get("start", {})

            entry = {
                "file": str(rel_path),
                "line": start.get("line", 0) + 1,  # Convert to 1-indexed
                "col": start.get("character", 0) + 1,
                "message": d.get("message", ""),
                "code": d.get("code", ""),
                "source": d.get("source", ""),
                "severity": self.SEVERITY_NAMES.get(severity, "unknown"),
            }

            if severity == DiagnosticSeverity.ERROR:
                errors.append(entry)
            elif severity == DiagnosticSeverity.WARNING:
                warnings.append(entry)
            else:
                hints.append(entry)

        return {
            "errors": errors,
            "warnings": warnings,
            "hints": hints,
        }

    def format_for_display(self, diagnostics: dict, max_items: int = 10) -> str:
        """Format diagnostics for CLI display.

        Args:
            diagnostics: Diagnostics dict from get_all_diagnostics.
            max_items: Maximum items per category to show.

        Returns:
            Formatted string for display.
        """
        lines = []

        total_errors = diagnostics.get("total_errors", len(diagnostics.get("errors", [])))
        total_warnings = diagnostics.get("total_warnings", len(diagnostics.get("warnings", [])))

        lines.append(f"{total_errors} errors, {total_warnings} warnings")
        lines.append("")

        errors = diagnostics.get("errors", [])
        if errors:
            lines.append("Errors:")
            for e in errors[:max_items]:
                lines.append(f"  {e['file']}:{e['line']}  {e['message']}")
            if len(errors) > max_items:
                lines.append(f"  ... ({len(errors) - max_items} more)")
            lines.append("")

        warnings = diagnostics.get("warnings", [])
        if warnings:
            lines.append("Warnings:")
            for w in warnings[:max_items]:
                lines.append(f"  {w['file']}:{w['line']}  {w['message']}")
            if len(warnings) > max_items:
                lines.append(f"  ... ({len(warnings) - max_items} more)")

        return "\n".join(lines)
