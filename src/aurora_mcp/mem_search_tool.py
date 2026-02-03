"""Memory search MCP tool - Search indexed code with LSP enrichment.

Provides enhanced search with call relationships and git info.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

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
        from aurora_cli.memory.retrieval import MemoryRetriever
        from aurora_cli.config import Config

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


def _enrich_with_lsp(result: dict[str, Any], workspace: Path) -> dict[str, Any]:
    """Enrich search result with LSP call relationship data.

    Args:
        result: Search result dict with metadata
        workspace: Workspace root directory

    Returns:
        Enriched result with used_by, called_by, calling fields
    """
    metadata = result.get("metadata", {})
    chunk_type = metadata.get("type", "")

    # Only enrich code chunks
    if chunk_type != "code":
        result["used_by"] = "-"
        result["called_by"] = []
        result["calling"] = []
        return result

    lsp = _get_lsp(workspace)
    if lsp is None:
        # No LSP available
        result["used_by"] = "-"
        result["called_by"] = []
        result["calling"] = []
        return result

    # Get file and line from metadata
    file_path = metadata.get("file", "")
    line_range = metadata.get("lines", "")

    if not file_path or not line_range:
        result["used_by"] = "-"
        result["called_by"] = []
        result["calling"] = []
        return result

    # Parse line range (e.g., "68-2447")
    try:
        if "-" in line_range:
            start_line = int(line_range.split("-")[0])
        else:
            start_line = int(line_range)
    except ValueError:
        result["used_by"] = "-"
        result["called_by"] = []
        result["calling"] = []
        return result

    # LSP uses 0-indexed lines
    line_0indexed = start_line - 1

    try:
        # Get usage summary for used_by count
        summary = lsp.get_usage_summary(file_path, line_0indexed, col=0)
        total_usages = summary.get("total_usages", 0)
        files_affected = summary.get("files_affected", 0)

        # Format as "N files(M)"
        result["used_by"] = f"{files_affected} files({total_usages})"

        # Get callers (functions that call this symbol)
        callers = lsp.get_callers(file_path, line_0indexed, col=0)
        result["called_by"] = [caller.get("name", "") for caller in callers[:5]]  # Top 5

        # Get callees (functions this symbol calls)
        callees = lsp.get_callees(file_path, line_0indexed, col=0)
        result["calling"] = [callee.get("name", "") for callee in callees[:5]]  # Top 5

    except Exception as e:
        logger.debug(f"LSP enrichment failed for {file_path}:{start_line}: {e}")
        result["used_by"] = "-"
        result["called_by"] = []
        result["calling"] = []

    return result


def mem_search(query: str, limit: int = 5) -> list[dict]:
    """Search indexed code and knowledge base with LSP context.

    Searches Aurora's memory (code chunks, knowledge base entries) and enriches
    results with LSP usage data for code symbols.

    Natural language triggers: "search code", "find symbols", "where is", "usage of"

    Args:
        query: Search query string
        limit: Maximum results to return (default 5)

    Returns:
        List of search results with:
        - file: File path
        - type: "code" or "kb"
        - symbol: Symbol/section name
        - lines: Line range (e.g., "68-2447")
        - score: Relevance score (0-1)
        - used_by: LSP usage info for code (e.g., "12 files(74)"), "-" for non-code
        - called_by: List of caller functions/methods
        - calling: List of called functions/methods (where LSP supports it)
        - git: Git info (commits, modified time)
    """
    workspace = Path.cwd()

    # Get retriever
    retriever = _get_retriever(workspace)
    if retriever is None:
        logger.warning("Memory database not initialized - returning empty results")
        return []

    # Perform search
    try:
        raw_results = retriever.retrieve(
            query,
            limit=limit,
            wait_for_model=True,  # Wait for embeddings if loading
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

        # Extract fields
        enriched = {
            "file": metadata.get("file", "unknown"),
            "type": metadata.get("type", "code"),
            "symbol": metadata.get("name", ""),
            "lines": metadata.get("lines", ""),
            "score": round(result.get("hybrid_score", 0.0), 3),
        }

        # Enrich with LSP data (adds used_by, called_by, calling)
        enriched = _enrich_with_lsp(enriched, workspace)

        # Add git info
        enriched["git"] = _get_git_info(enriched["file"], workspace)

        enriched_results.append(enriched)

    return enriched_results[:limit]  # Ensure limit
