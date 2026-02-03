"""Memory search MCP tool - Search indexed code with LSP enrichment.

Provides enhanced search with call relationships, complexity, and risk assessment.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# Lazy-loaded tree-sitter parser
_ts_parser = None


def _get_complexity(file_path: str, line_start: int, line_end: int) -> int:
    """Calculate complexity for a code region using tree-sitter.

    Args:
        file_path: Path to source file
        line_start: Start line (1-indexed)
        line_end: End line (1-indexed)

    Returns:
        Complexity percentage (0-100), or -1 if unavailable
    """
    global _ts_parser

    try:
        path = Path(file_path)
        if not path.exists() or path.suffix != ".py":
            return -1

        # Lazy init tree-sitter
        if _ts_parser is None:
            try:
                import tree_sitter
                import tree_sitter_python
                python_lang = tree_sitter.Language(tree_sitter_python.language())
                _ts_parser = tree_sitter.Parser(python_lang)
            except ImportError:
                logger.debug("tree-sitter not available for complexity")
                return -1

        # Parse file
        source = path.read_bytes()
        tree = _ts_parser.parse(source)

        # Find node at line_start
        target_node = None
        def find_node(node):
            nonlocal target_node
            # tree-sitter uses 0-indexed lines
            node_start = node.start_point[0] + 1
            node_end = node.end_point[0] + 1
            if node_start == line_start and node.type in ("function_definition", "class_definition"):
                target_node = node
                return
            for child in node.children:
                find_node(child)

        find_node(tree.root_node)

        if target_node is None:
            return -1

        # Count branch points
        branch_types = {
            "if_statement", "for_statement", "while_statement",
            "try_statement", "with_statement", "match_statement",
            "elif_clause", "except_clause", "boolean_operator",
            "conditional_expression",
        }

        branch_count = 0
        def count_branches(node):
            nonlocal branch_count
            if node.type in branch_types:
                branch_count += 1
            for child in node.children:
                count_branches(child)

        count_branches(target_node)

        # Normalize to percentage: score = branches / (branches + 10) * 100
        if branch_count == 0:
            return 0
        complexity_pct = int(branch_count / (branch_count + 10) * 100)
        return min(complexity_pct, 99)

    except Exception as e:
        logger.debug(f"Complexity calculation failed: {e}")
        return -1


def _calculate_risk(files: int, refs: int, complexity: int) -> str:
    """Calculate risk level from usage and complexity.

    Args:
        files: Number of files using this symbol
        refs: Total reference count
        complexity: Complexity percentage (0-100)

    Returns:
        Risk level: "HIGH", "MED", "LOW", or "-"
    """
    if complexity < 0:
        complexity = 0

    # HIGH: widespread use OR very complex
    if files >= 10 or refs >= 50 or complexity >= 60:
        return "HIGH"
    # MED: moderate use OR moderate complexity
    if files >= 3 or refs >= 10 or complexity >= 30:
        return "MED"
    # LOW: localized and simple
    return "LOW"

# Lazy-loaded instances
_store = None
_retriever = None
_lsp_instance = None


def _get_store(workspace: Path | None = None):
    """Get or create SQLite store instance."""
    global _store

    if _store is None:
        from aurora_core.store.sqlite import SQLiteStore

        ws = workspace or Path.cwd()
        db_path = ws / ".aurora" / "memory.db"

        if not db_path.exists():
            logger.warning(f"Memory database not found at {db_path}")
            # Return None - will return empty results
            return None

        _store = SQLiteStore(str(db_path))
        logger.info(f"Initialized memory store: {db_path}")

    return _store


def _get_retriever(workspace: Path | None = None):
    """Get or create retriever instance."""
    global _retriever

    if _retriever is None:
        from aurora_cli.config import Config
        from aurora_cli.memory.retrieval import MemoryRetriever

        store = _get_store(workspace)
        if store is None:
            return None

        config = Config()
        _retriever = MemoryRetriever(store=store, config=config)
        logger.info("Initialized memory retriever")

    return _retriever


def _get_lsp(workspace: Path | None = None):
    """Get or create LSP instance for code enrichment."""
    global _lsp_instance

    if _lsp_instance is None:
        try:
            from aurora_lsp.facade import AuroraLSP
            ws = workspace or Path.cwd()
            _lsp_instance = AuroraLSP(ws)
            logger.info(f"Initialized LSP for workspace: {ws}")
        except ImportError:
            logger.warning("aurora-lsp not available - results will not include LSP enrichment")
            return None

    return _lsp_instance


def _get_git_info(file_path: str, workspace: Path) -> str:
    """Get git commit count and last modified time for a file.

    Args:
        file_path: Relative file path
        workspace: Workspace root directory

    Returns:
        Git info string like "41 commits, 11h ago" or "-"
    """
    try:
        full_path = workspace / file_path
        if not full_path.exists():
            return "-"

        # Get commit count
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD", "--", str(full_path)],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=2,
        )

        if result.returncode != 0:
            return "-"

        commit_count = result.stdout.strip()

        # Get last modified time
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(full_path)],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=2,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return f"{commit_count} commits"

        timestamp = int(result.stdout.strip())
        now = datetime.now().timestamp()
        delta_seconds = int(now - timestamp)

        # Format time ago
        if delta_seconds < 3600:  # < 1 hour
            minutes = delta_seconds // 60
            time_ago = f"{minutes}m ago" if minutes > 0 else "just now"
        elif delta_seconds < 86400:  # < 1 day
            hours = delta_seconds // 3600
            time_ago = f"{hours}h ago"
        else:  # days
            days = delta_seconds // 86400
            time_ago = f"{days}d ago"

        return f"{commit_count} commits, {time_ago}"

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError):
        return "-"


def _get_usage_only(result: dict[str, Any], workspace: Path) -> dict[str, Any]:
    """Get usage count, complexity, and risk (fast).

    Args:
        result: Search result dict with metadata
        workspace: Workspace root directory

    Returns:
        Result with usage, risk fields added.
        Format: "19f 43r c:74" where f=files, r=refs, c=complexity%
    """
    metadata = result.get("metadata", {})
    chunk_type = metadata.get("type", "")

    # Only enrich code chunks
    if chunk_type != "code":
        result["used_by"] = "-"
        result["risk"] = "-"
        return result

    file_path = metadata.get("file_path", "")
    line_start = metadata.get("line_start")
    line_end = metadata.get("line_end")

    if not file_path or not line_start:
        result["used_by"] = "-"
        result["risk"] = "-"
        return result

    try:
        start_line = int(line_start)
        end_line = int(line_end) if line_end else start_line + 50
    except (ValueError, TypeError):
        result["used_by"] = "-"
        result["risk"] = "-"
        return result

    # Get complexity from tree-sitter (fast, ~10ms)
    complexity = _get_complexity(file_path, start_line, end_line)

    # Get usage from LSP
    lsp = _get_lsp(workspace)
    files_affected = 0
    total_usages = 0

    if lsp is not None:
        try:
            line_0indexed = start_line - 1
            col = 10  # Hit symbol names after 'class ', 'def '
            summary = lsp.get_usage_summary(file_path, line_0indexed, col=col)
            total_usages = summary.get("total_usages", 0)
            files_affected = summary.get("files_affected", 0)
        except Exception as e:
            logger.debug(f"LSP usage check failed for {file_path}:{start_line}: {e}")

    # Format: "19f 43r c:74"
    if files_affected > 0 or complexity >= 0:
        parts = []
        if files_affected > 0:
            parts.append(f"{files_affected}f {total_usages}r")
        if complexity >= 0:
            parts.append(f"c:{complexity}")
        result["used_by"] = " ".join(parts) if parts else "-"
    else:
        result["used_by"] = "-"

    # Calculate risk
    result["risk"] = _calculate_risk(files_affected, total_usages, complexity)

    return result


def _enrich_full(result: dict[str, Any], workspace: Path) -> dict[str, Any]:
    """Full enrichment with callers/callees/git (slow).

    Assumes _get_usage_only was already called.

    Args:
        result: Search result dict with metadata (already has used_by)
        workspace: Workspace root directory

    Returns:
        Enriched result with called_by, calling, git fields added
    """
    metadata = result.get("metadata", {})
    chunk_type = metadata.get("type", "")

    if chunk_type != "code":
        result["called_by"] = []
        result["calling"] = []
        result["git"] = "-"
        return result

    lsp = _get_lsp(workspace)
    file_path = metadata.get("file_path", "")
    line_start = metadata.get("line_start")

    if lsp is None or not file_path or not line_start:
        result["called_by"] = []
        result["calling"] = []
        result["git"] = _get_git_info(file_path, workspace) if file_path else "-"
        return result

    try:
        start_line = int(line_start)
        line_0indexed = start_line - 1
        col = 10

        # Get callers (functions that call this symbol)
        callers = lsp.get_callers(file_path, line_0indexed, col=col)
        result["called_by"] = [caller.get("name", "") for caller in callers[:5]]

        # Get callees (functions this symbol calls)
        callees = lsp.get_callees(file_path, line_0indexed, col=col)
        result["calling"] = [callee.get("name", "") for callee in callees[:5]]

    except Exception as e:
        logger.debug(f"LSP callers/callees failed for {file_path}:{line_start}: {e}")
        result["called_by"] = []
        result["calling"] = []

    # Add git info
    result["git"] = _get_git_info(file_path, workspace)
    return result


def mem_search(query: str, limit: int = 5, enrich: bool = False) -> list[dict]:
    """Search codebase for symbols, functions, classes with LSP-enriched results.

    WHEN TO USE:
    - "where is X defined" → search for symbol name
    - "find functions that handle Y" → search by functionality
    - "what calls Z" → search then check called_by field
    - Understanding codebase structure → broad search, check used_by counts

    USE THIS FIRST before lsp tool - mem_search finds the file:line, then use lsp for deeper analysis.

    Args:
        query: Symbol name, function name, or description (e.g., "SOAROrchestrator", "handle errors")
        limit: Max results (default 5, increase for broader search)
        enrich: Add full enrichment - callers, callees, git info (slower). Default False.

    Returns:
        List of matches with LSP context:
        - type: "code" or "kb" (knowledge base)
        - file: Filename (where)
        - name: Function/class name (what)
        - lines: Line range
        - used_by: "19f 43r c:74" (files, refs, complexity%)
        - risk: "HIGH" | "MED" | "LOW" | "-"
        - score: Relevance (0-1)
        When enrich=True, also includes:
        - called_by: Functions that call this symbol
        - calling: Functions this symbol calls
        - git: Recent commit info
    """
    workspace = Path.cwd()

    # Get retriever
    retriever = _get_retriever(workspace)
    if retriever is None:
        logger.warning("Memory database not initialized - returning empty results")
        return []

    # Perform search (fast path - don't block on embedding model)
    try:
        raw_results = retriever.retrieve(
            query,
            limit=limit,
            wait_for_model=False,  # Fast: BM25+Activation if model not loaded (85% quality)
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

    # Convert and enrich results
    enriched_results = []
    for result in raw_results:
        if not isinstance(result, dict):
            continue

        metadata = result.get("metadata", {})

        # Build lines string from line_start/line_end
        line_start = metadata.get("line_start")
        line_end = metadata.get("line_end")
        if line_start and line_end:
            lines_str = f"{line_start}-{line_end}"
        elif line_start:
            lines_str = str(line_start)
        else:
            lines_str = ""

        # Extract fields (metadata uses file_path, line_start, line_end)
        full_path = metadata.get("file_path", "unknown")
        enriched = {
            "type": metadata.get("type", "code"),
            "file": Path(full_path).name if full_path != "unknown" else "unknown",
            "name": metadata.get("name", ""),  # Function/class name
            "lines": lines_str,
            "used_by": "-",  # Will be set by _get_usage_only
            "risk": "-",     # Will be set by _get_usage_only
            "score": round(result.get("hybrid_score", 0.0), 3),
            "metadata": metadata,  # Include metadata for LSP enrichment
        }

        # Always get usage count (fast, matches CLI behavior)
        enriched = _get_usage_only(enriched, workspace)

        # Optional full enrichment (slow - adds callers, callees, git)
        if enrich:
            enriched = _enrich_full(enriched, workspace)

        # Remove metadata from final output (internal use only)
        enriched.pop("metadata", None)

        enriched_results.append(enriched)

    return enriched_results[:limit]  # Ensure limit
