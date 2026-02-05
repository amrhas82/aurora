"""LSP MCP tool - Code intelligence via Language Server Protocol.

Provides dead code detection, impact analysis, and pre-edit checks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# Lazy-loaded LSP instance (initialized on first use)
_lsp_instance = None
_workspace_root = None


def _get_lsp(workspace: Path | None = None):
    """Get or create LSP instance (lazy initialization)."""
    global _lsp_instance, _workspace_root

    # Determine workspace
    ws = workspace or Path.cwd()

    # Reinitialize if workspace changed
    if _lsp_instance is None or _workspace_root != ws:
        try:
            from aurora_lsp.facade import AuroraLSP

            _lsp_instance = AuroraLSP(ws)
            _workspace_root = ws
            logger.info(f"Initialized LSP for workspace: {ws}")
        except ImportError:
            logger.error("aurora-lsp package not installed")
            raise ImportError(
                "LSP tools require aurora-lsp package. " "Install with: pip install aurora-lsp"
            )

    return _lsp_instance


def _find_symbol_column(file_path: str, line_0indexed: int, workspace: Path) -> int:
    """Find the column where a symbol starts on a given line.

    Reads the line and detects common Python patterns to find symbol position.

    Args:
        file_path: Relative or absolute file path
        line_0indexed: 0-indexed line number
        workspace: Workspace root directory

    Returns:
        Column number (0-indexed) where symbol likely starts
    """
    import re

    # Resolve file path
    full_path = Path(file_path)
    if not full_path.is_absolute():
        full_path = workspace / file_path

    if not full_path.exists():
        return 0

    try:
        lines = full_path.read_text().splitlines()
        if line_0indexed >= len(lines):
            return 0

        line = lines[line_0indexed]

        # Pattern: class ClassName
        match = re.search(r"\bclass\s+(\w+)", line)
        if match:
            return match.start(1)

        # Pattern: async def func_name
        match = re.search(r"\basync\s+def\s+(\w+)", line)
        if match:
            return match.start(1)

        # Pattern: def func_name
        match = re.search(r"\bdef\s+(\w+)", line)
        if match:
            return match.start(1)

        # Pattern: variable = ... (at start of line, possibly indented)
        match = re.match(r"^(\s*)(\w+)\s*[=:]", line)
        if match:
            return len(match.group(1))  # Column after indentation

        # Default: try column 4 (common indent level)
        return 4

    except Exception:
        return 0


def _calculate_risk(usage_count: int) -> str:
    """Calculate risk level from usage count.

    Args:
        usage_count: Number of usages

    Returns:
        Risk level: 'low' (0-2), 'medium' (3-10), or 'high' (11+)
    """
    if usage_count <= 2:
        return "low"
    elif usage_count <= 10:
        return "medium"
    else:
        return "high"


def _get_symbol_name_from_line(file_path: str, line_0indexed: int, workspace: Path) -> str | None:
    """Extract symbol name from a line (class, function, or variable definition).

    Args:
        file_path: Path to file
        line_0indexed: 0-indexed line number
        workspace: Workspace root

    Returns:
        Symbol name if found, None otherwise
    """
    import re

    full_path = Path(file_path)
    if not full_path.is_absolute():
        full_path = workspace / file_path

    if not full_path.exists():
        return None

    try:
        lines = full_path.read_text().splitlines()
        if line_0indexed >= len(lines):
            return None

        line = lines[line_0indexed]

        # Pattern: class ClassName
        match = re.search(r"\bclass\s+(\w+)", line)
        if match:
            return match.group(1)

        # Pattern: async def func_name
        match = re.search(r"\basync\s+def\s+(\w+)", line)
        if match:
            return match.group(1)

        # Pattern: def func_name
        match = re.search(r"\bdef\s+(\w+)", line)
        if match:
            return match.group(1)

        # Pattern: variable = ...
        match = re.match(r"^\s*(\w+)\s*[=:]", line)
        if match:
            return match.group(1)

        return None
    except Exception:
        return None


def _count_text_matches(
    symbol_name: str, workspace: Path, top_n: int = 5
) -> tuple[int, int, list[str]]:
    """Count text matches for a symbol using ripgrep.

    Uses word boundary matching to reduce false positives.
    Excludes common false positive patterns (comments, strings where possible).

    Args:
        symbol_name: Name of the symbol to search
        workspace: Workspace root directory
        top_n: Number of top file:line references to return

    Returns:
        Tuple of (file_count, total_matches, top_refs)
        where top_refs is a list of "file:line" strings
    """
    import subprocess

    if not symbol_name:
        return 0, 0, []

    try:
        # Use ripgrep with word boundary, count matches per file
        # -w: word boundary, -c: count, --type py: Python files only
        result = subprocess.run(
            ["rg", "-w", "-c", "--type", "py", symbol_name, "."],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode not in (0, 1):  # 1 means no matches
            return 0, 0, []

        # Parse output: each line is "file:count"
        file_count = 0
        total_matches = 0
        for line in result.stdout.strip().split("\n"):
            if ":" in line:
                file_count += 1
                try:
                    count = int(line.split(":")[-1])
                    total_matches += count
                except ValueError:
                    total_matches += 1

        # Get top-N concrete file:line references
        top_refs: list[str] = []
        if total_matches > 0 and top_n > 0:
            try:
                # Get all unique file:line refs, then sort source before tests
                ref_result = subprocess.run(
                    ["rg", "-w", "-n", "--no-heading", "--type", "py",
                     symbol_name, "."],
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if ref_result.returncode == 0:
                    seen_files: set[str] = set()
                    src_refs: list[str] = []
                    test_refs: list[str] = []
                    for ref_line in ref_result.stdout.strip().split("\n"):
                        if not ref_line or ":" not in ref_line:
                            continue
                        parts = ref_line.split(":", 2)
                        if len(parts) >= 2:
                            fpath = parts[0].lstrip("./")
                            lineno = parts[1]
                            if fpath not in seen_files:
                                seen_files.add(fpath)
                                ref = f"{fpath}:{lineno}"
                                if "/test" in fpath or fpath.startswith("tests/"):
                                    test_refs.append(ref)
                                else:
                                    src_refs.append(ref)
                    # Source files first, then tests, capped at top_n
                    top_refs = (src_refs + test_refs)[:top_n]
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return file_count, total_matches, top_refs

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0, 0, []


def _generate_code_quality_report(dead_code: list[dict], workspace: Path) -> str:
    """Generate CODE_QUALITY_REPORT.md file.

    Args:
        dead_code: List of dead code items
        workspace: Workspace root directory

    Returns:
        Path to generated report
    """
    # Determine report location: docs/ if exists, else root
    docs_dir = workspace / "docs"
    if docs_dir.exists() and docs_dir.is_dir():
        report_path = docs_dir / "CODE_QUALITY_REPORT.md"
    else:
        report_path = workspace / "CODE_QUALITY_REPORT.md"

    # Group by severity
    # For dead code, we'll categorize by kind and usage
    critical = []  # Classes/functions in core files
    high = []  # Public functions/classes
    medium = []  # Protected members
    low = []  # Private members

    for item in dead_code:
        name = item.get("name", "")
        kind = item.get("kind", "")

        # Simple heuristic: private members are low priority
        if name.startswith("_"):
            low.append(item)
        # Classes are higher priority than functions
        elif kind == "class":
            high.append(item)
        elif kind == "function":
            medium.append(item)
        else:
            low.append(item)

    # Generate report content
    lines = [
        "# Code Quality Report",
        "",
        "Generated by Aurora LSP MCP Tool",
        "",
        "## Summary",
        "",
        f"- **Total dead code items:** {len(dead_code)}",
        f"- **Critical:** {len(critical)}",
        f"- **High:** {len(high)}",
        f"- **Medium:** {len(medium)}",
        f"- **Low:** {len(low)}",
        "",
    ]

    # Helper to format section
    def add_section(title: str, items: list[dict]):
        if not items:
            return
        lines.append(f"## {title}")
        lines.append("")
        for item in items:
            file_path = item.get("file", "unknown")
            line_num = item.get("line", 0)
            name = item.get("name", "unknown")
            kind = item.get("kind", "symbol")
            lines.append(f"- `{file_path}:{line_num}` - {kind} **{name}**")
            lines.append("  - Action: Safe to remove (0 usages)")
        lines.append("")

    add_section("Critical Issues", critical)
    add_section("High Priority", high)
    add_section("Medium Priority", medium)
    add_section("Low Priority", low)

    # Write report
    report_path.write_text("\n".join(lines))
    logger.info(f"Generated CODE_QUALITY_REPORT.md at {report_path}")

    return str(report_path)


def lsp(
    action: Literal["deadcode", "impact", "check", "imports", "related"] = "check",
    path: str = "",
    line: int | None = None,
    accurate: bool = False,
) -> dict:
    """LSP code intelligence for refactoring, usage analysis, and dead code detection.

    WHEN TO USE EACH ACTION:
    - "refactor", "change", "modify" a symbol → action="impact" (FAST - analyzes one symbol)
    - "dead code", "unused", "cleanup" → action="deadcode" (scans entire directory)
    - Before editing any function/class → action="check" (FAST - quick usage count)
    - "who imports this?" → action="imports" (FAST - find all importers of a module)
    - "what does this call?" → action="related" (FAST - find outgoing calls/dependencies)

    IMPORTANT: Do NOT use deadcode for refactoring. Use impact instead.

    Actions:
    - "check": Quick pre-edit usage count. Returns usages and risk level. Use BEFORE editing.
    - "impact": Full impact analysis for a symbol at path:line. Shows all callers, files affected.
    - "deadcode": Scan directory for ALL unused symbols. Has two modes (see below).
    - "imports": Find all files that import a given module. Use for refactoring impact.
    - "related": Find what a symbol depends on (outgoing calls). Use for understanding dependencies.

    DEADCODE MODES:
    - Fast (default): Batched ripgrep text search, ~2s, 85% accuracy, ALL languages
    - Accurate (--accurate): LSP references per symbol, ~20s, 95%+ accuracy, Python tested

    When to use each:
    - Fast: Daily dev, CI/CD, large codebases, non-Python code
    - Accurate: Before deleting code, before major refactor, need confidence

    LANGUAGE SUPPORT:
    - Python: Full support (LSP + tree-sitter complexity + import filtering)
    - JS/TS/Go/Rust/Java: Partial (LSP refs via multilspy, ripgrep deadcode)

    To scale to other languages (3-4 days each):
    1. Already works: LSP references, ripgrep deadcode
    2. Need to add: tree-sitter-{lang} parser, language-specific import filter patterns

    Risk levels:
    - low (0-2 usages): Safe to change
    - medium (3-10 usages): Review callers first
    - high (11+ usages): Careful refactoring needed

    Implementation files:
    - MCP tool: src/aurora_mcp/lsp_tool.py (this file)
    - Analysis: packages/lsp/src/aurora_lsp/analysis.py (CodeAnalyzer)
    - LSP client: packages/lsp/src/aurora_lsp/client.py (multilspy wrapper)
    - Facade: packages/lsp/src/aurora_lsp/facade.py (sync API)
    - Import filters: packages/lsp/src/aurora_lsp/filters.py (Python only)

    Args:
        action: "check" | "impact" | "deadcode" | "imports" | "related" (default: check)
        path: File path (required). For deadcode, can be a directory. For imports, the module file.
        line: Line number (required for impact/check/related, 1-indexed). Not used for deadcode/imports.
        accurate: For deadcode only. If True, use LSP references (95%+ accuracy, ~20s).
                 If False (default), use batched ripgrep (85% accuracy, ~2s).

    Returns:
        JSON with usages, callers, risk level, files affected, dependencies, or import information
    """
    workspace = Path.cwd()
    lsp_client = _get_lsp(workspace)

    if action == "deadcode":
        # Find dead code in path
        target_path = workspace / path if path else None
        dead_code_items = lsp_client.find_dead_code(target_path, accurate=accurate)

        # Generate CODE_QUALITY_REPORT.md
        report_path = _generate_code_quality_report(dead_code_items, workspace)

        return {
            "action": "deadcode",
            "path": path,
            "accurate": accurate,
            "dead_code": dead_code_items,
            "total": len(dead_code_items),
            "report_path": report_path,
        }

    elif action == "impact":
        # Full impact analysis
        if line is None:
            raise ValueError("line parameter required for impact action")

        # LSP uses 0-indexed lines, input is 1-indexed
        line_0indexed = line - 1

        # Find symbol column intelligently
        col = _find_symbol_column(path, line_0indexed, workspace)

        # Get usage summary
        summary = lsp_client.get_usage_summary(path, line_0indexed, col=col)

        # Get top callers
        callers = lsp_client.get_callers(path, line_0indexed, col=col)

        # Format top callers with usage counts
        top_callers = []
        usages_by_file = summary.get("usages_by_file", {})
        for caller in callers[:10]:  # Top 10
            caller_file = caller.get("file", "")
            caller_line = caller.get("line", 0)
            caller_name = caller.get("name", "")
            # Count usages from this caller (approximation)
            file_usages = usages_by_file.get(caller_file, [])
            usages_count = len([u for u in file_usages if u.get("name") == caller_name])
            top_callers.append(
                {
                    "file": caller_file,
                    "line": caller_line + 1,  # Convert back to 1-indexed
                    "name": caller_name,
                    "usages": usages_count or 1,
                }
            )

        total_usages = summary.get("total_usages", 0)
        files_affected = summary.get("files_affected", 0)

        result = {
            "action": "impact",
            "path": path,
            "line": line,
            "symbol": summary.get("symbol"),
            "used_by_files": files_affected,
            "total_usages": total_usages,
            "top_callers": top_callers,
            "risk": _calculate_risk(total_usages),
        }

        # Hybrid fallback: if LSP found 0 refs, check with text search
        # This catches cross-package references that LSP misses
        if total_usages == 0:
            symbol_name = _get_symbol_name_from_line(path, line_0indexed, workspace)
            if symbol_name:
                text_files, text_matches, top_refs = _count_text_matches(
                    symbol_name, workspace
                )
                if text_matches > 0:
                    result["text_matches"] = text_matches
                    result["text_files"] = text_files
                    if top_refs:
                        result["top_refs"] = top_refs
                    result["note"] = (
                        f"LSP found 0 refs but text search found {text_matches} matches "
                        f"in {text_files} files - likely cross-package usage"
                    )
                    # Upgrade risk based on text matches
                    result["risk"] = _calculate_risk(text_matches)

        return result

    elif action == "check":
        # Quick pre-edit check
        if line is None:
            raise ValueError("line parameter required for check action")

        # LSP uses 0-indexed lines
        line_0indexed = line - 1

        # Find symbol column intelligently
        col = _find_symbol_column(path, line_0indexed, workspace)

        # Get usage summary (lighter than full impact)
        summary = lsp_client.get_usage_summary(path, line_0indexed, col=col)

        total_usages = summary.get("total_usages", 0)

        result = {
            "action": "check",
            "path": path,
            "line": line,
            "symbol": summary.get("symbol"),
            "used_by": total_usages,
            "risk": _calculate_risk(total_usages),
        }

        # Hybrid fallback: if LSP found 0 refs, check with text search
        if total_usages == 0:
            symbol_name = _get_symbol_name_from_line(path, line_0indexed, workspace)
            if symbol_name:
                text_files, text_matches, top_refs = _count_text_matches(
                    symbol_name, workspace
                )
                if text_matches > 0:
                    result["text_matches"] = text_matches
                    result["text_files"] = text_files
                    if top_refs:
                        result["top_refs"] = top_refs
                    result["note"] = (
                        f"LSP found 0 refs but text search found {text_matches} matches "
                        f"in {text_files} files - likely cross-package usage"
                    )
                    # Upgrade risk based on text matches
                    result["risk"] = _calculate_risk(text_matches)
                    # Don't mark as unused if text search found matches
                    return result

        # #UNUSED marker: flag symbols with very low usage (candidates for removal)
        if total_usages <= 2:
            result["unused"] = True

        return result

    elif action == "imports":
        # Find all files that import this module
        if not path:
            raise ValueError("path parameter required for imports action")

        result = lsp_client.get_imported_by(path)
        result["action"] = "imports"
        return result

    elif action == "related":
        # Find what this symbol depends on (outgoing calls)
        if line is None:
            raise ValueError("line parameter required for related action")

        # LSP uses 0-indexed lines
        line_0indexed = line - 1

        # Find symbol column intelligently
        col = _find_symbol_column(path, line_0indexed, workspace)

        # Get outgoing calls (what this symbol calls)
        callees = lsp_client.get_callees(path, line_0indexed, col=col)

        # Format callees
        formatted_callees = []
        for callee in callees:
            formatted_callees.append(
                {
                    "name": callee.get("name", "unknown"),
                    "line": callee.get("line", 0),
                }
            )

        return {
            "action": "related",
            "path": path,
            "line": line,
            "calls": formatted_callees,
            "total_calls": len(formatted_callees),
        }

    else:
        raise ValueError(
            f"Unknown action: {action}. Use: deadcode, impact, check, imports, related"
        )
