"""Phase 3: Query Decomposition.

This module implements the Decompose phase of the SOAR pipeline, which breaks
down complex queries into executable subgoals using LLM-based reasoning.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aurora_reasoning import LLMClient
    from aurora_reasoning.decompose import DecompositionResult

__all__ = ["decompose_query", "DecomposePhaseResult"]


class DecomposePhaseResult:
    """Result of decompose phase execution.

    Attributes:
        decomposition: The decomposition result from reasoning logic
        cached: Whether result was retrieved from cache
        query_hash: Hash of query for cache lookup
        timing_ms: Time taken in milliseconds

    """

    def __init__(
        self,
        decomposition: DecompositionResult,
        cached: bool = False,
        query_hash: str = "",
        timing_ms: float = 0.0,
    ):
        self.decomposition = decomposition
        self.cached = cached
        self.query_hash = query_hash
        self.timing_ms = timing_ms

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "decomposition": self.decomposition.to_dict(),
            "cached": self.cached,
            "query_hash": self.query_hash,
            "timing_ms": self.timing_ms,
        }


# Cache for decomposition results (in-memory, keyed by query hash)
_decomposition_cache: dict[str, DecompositionResult] = {}


def _compute_query_hash(query: str, complexity: str) -> str:
    """Compute hash of query and complexity for caching.

    Args:
        query: User query string
        complexity: Complexity level

    Returns:
        SHA256 hash as hex string

    """
    content = f"{query}|{complexity}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def decompose_query(
    query: str,
    context: dict[str, Any],
    complexity: str,
    llm_client: LLMClient,
    available_agents: list[str] | None = None,
    retry_feedback: str | None = None,
    use_cache: bool = True,
) -> DecomposePhaseResult:
    """Decompose query into subgoals using LLM reasoning with caching.

    This phase:
    1. Checks cache for identical query/complexity combination
    2. If not cached, builds context summary from retrieved chunks
    3. Calls reasoning.decompose_query with LLM client
    4. Caches result for future identical queries
    5. Returns DecomposePhaseResult with timing and cache status

    Args:
        query: User query string
        context: Retrieved context from Phase 2 (code_chunks, reasoning_chunks)
        complexity: Complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
        llm_client: LLM client for decomposition
        available_agents: Optional list of available agent names from registry
        retry_feedback: Optional feedback from previous decomposition attempt
        use_cache: Whether to use cached results (default: True)

    Returns:
        DecomposePhaseResult with decomposition and metadata

    Raises:
        ValueError: If complexity is invalid or decomposition fails validation
        RuntimeError: If LLM call fails

    """
    import time

    from aurora_reasoning.decompose import decompose_query as reasoning_decompose
    from aurora_reasoning.prompts.examples import Complexity

    start_time = time.perf_counter()

    # Compute query hash for caching
    query_hash = _compute_query_hash(query, complexity)

    # Check cache if enabled and no retry feedback
    if use_cache and not retry_feedback and query_hash in _decomposition_cache:
        cached_result = _decomposition_cache[query_hash]
        timing_ms = (time.perf_counter() - start_time) * 1000
        return DecomposePhaseResult(
            decomposition=cached_result,
            cached=True,
            query_hash=query_hash,
            timing_ms=timing_ms,
        )

    # Build context summary from retrieved chunks
    context_summary = _build_context_summary(context, complexity)

    # Convert complexity string to enum
    try:
        complexity_enum = Complexity[complexity.upper()]
    except KeyError:
        raise ValueError(f"Invalid complexity level: {complexity}")

    # Call reasoning decomposition logic
    decomposition = reasoning_decompose(
        llm_client=llm_client,
        query=query,
        complexity=complexity_enum,
        context_summary=context_summary,
        available_agents=available_agents,
        retry_feedback=retry_feedback,
    )

    # Cache result (unless retry feedback was provided)
    if not retry_feedback:
        _decomposition_cache[query_hash] = decomposition

    timing_ms = (time.perf_counter() - start_time) * 1000

    return DecomposePhaseResult(
        decomposition=decomposition,
        cached=False,
        query_hash=query_hash,
        timing_ms=timing_ms,
    )


def _read_file_lines(file_path: str, line_start: int, line_end: int, max_lines: int = 50) -> str:
    """Read specific lines from a file.

    Args:
        file_path: Path to the file
        line_start: Starting line (1-indexed)
        line_end: Ending line (inclusive)
        max_lines: Maximum lines to read (truncate if longer)

    Returns:
        File content or empty string if read fails

    """
    try:
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            return ""

        with open(path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        # Convert to 0-indexed
        start_idx = max(0, line_start - 1)
        end_idx = min(len(lines), line_end)

        # Limit lines to prevent huge context
        if end_idx - start_idx > max_lines:
            end_idx = start_idx + max_lines

        return "".join(lines[start_idx:end_idx])
    except Exception:
        return ""


def _build_context_summary(context: dict[str, Any], complexity: str = "MEDIUM") -> str:
    """Build actionable context summary with actual code content.

    For top chunks, reads actual file content so the LLM can see real code.
    For remaining chunks, includes docstrings/signatures as fallback.

    Args:
        context: Context dict with code_chunks and reasoning_chunks
        complexity: Complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)

    Returns:
        Summary string with actual code the LLM can use for decomposition.

    """
    code_chunks = context.get("code_chunks", [])
    reasoning_chunks = context.get("reasoning_chunks", [])

    # Filter out conversation log chunks to prevent failed SOAR runs from polluting context
    def _get_chunk_path(chunk: Any) -> str:
        if hasattr(chunk, "file_path"):
            return chunk.file_path or ""
        if isinstance(chunk, dict):
            return chunk.get("file_path") or chunk.get("metadata", {}).get("file_path", "")
        return ""

    code_chunks = [c for c in code_chunks if "/logs/conversations/" not in _get_chunk_path(c)]

    # Deduplicate chunks by file_path to avoid redundancy
    # Only dedupe chunks with valid file_path (non-empty)
    seen_files = set()
    deduped_chunks = []
    for chunk in code_chunks:
        fp = _get_chunk_path(chunk)
        # Keep chunks without file_path, only dedupe those with valid paths
        if not fp or fp not in seen_files:
            if fp:  # Only track non-empty paths
                seen_files.add(fp)
            deduped_chunks.append(chunk)
    code_chunks = deduped_chunks

    summary_parts = []

    if code_chunks:
        # Complexity-based chunk limits
        CHUNK_LIMITS = {
            "MEDIUM": (5, 8),
            "COMPLEX": (7, 12),
            "CRITICAL": (10, 15),
        }
        TOP_N_WITH_CODE, MAX_CHUNKS = CHUNK_LIMITS.get(complexity, (5, 8))

        # List available file paths for source_file matching
        file_paths = []
        for chunk in code_chunks[:MAX_CHUNKS]:
            if hasattr(chunk, "file_path"):
                file_paths.append(chunk.file_path)
            elif isinstance(chunk, dict):
                fp = chunk.get("metadata", {}).get("file_path") or chunk.get("file_path", "")
                if fp:
                    file_paths.append(fp)
        unique_files = list(dict.fromkeys(file_paths))  # Preserve order, remove dups
        if unique_files:
            summary_parts.append("## Available Source Files (use for source_file field)\n")
            for fp in unique_files[:10]:
                summary_parts.append(f"- {fp}")
            summary_parts.append("")

        summary_parts.append(f"## Relevant Code ({len(code_chunks)} elements found)\n")

        for i, chunk in enumerate(code_chunks[:MAX_CHUNKS]):
            # Extract chunk info (handle both objects and dicts)
            if hasattr(chunk, "file_path"):
                # CodeChunk object
                file_path = chunk.file_path
                name = getattr(chunk, "name", "unknown")
                element_type = getattr(chunk, "element_type", "")
                line_start = getattr(chunk, "line_start", 0)
                line_end = getattr(chunk, "line_end", 0)
                docstring = getattr(chunk, "docstring", "") or ""
            elif isinstance(chunk, dict):
                metadata = chunk.get("metadata", {})
                if metadata:
                    file_path = metadata.get("file_path", "unknown")
                    name = metadata.get("name", "unknown")
                    element_type = metadata.get("type", "")
                    line_start = metadata.get("line_start", 0)
                    line_end = metadata.get("line_end", 0)
                else:
                    file_path = chunk.get("file_path", "unknown")
                    name = chunk.get("name", "unknown")
                    element_type = chunk.get("element_type", "")
                    line_start = chunk.get("line_start", 0)
                    line_end = chunk.get("line_end", 0)
                docstring = chunk.get("content", "")
            else:
                continue

            short_path = "/".join(file_path.split("/")[-2:]) if "/" in file_path else file_path
            entry_parts = [f"### {element_type}: {name}", f"File: {short_path}"]

            # For top N chunks, read actual code
            if i < TOP_N_WITH_CODE and line_start and line_end:
                code_content = _read_file_lines(file_path, line_start, line_end)
                if code_content:
                    entry_parts.append(f"```python\n{code_content.rstrip()}\n```")
                elif docstring:
                    entry_parts.append(f"Description: {docstring[:300]}...")
            elif docstring:
                # Fallback to docstring for remaining chunks
                doc_preview = docstring[:200] + "..." if len(docstring) > 200 else docstring
                entry_parts.append(f"Description: {doc_preview}")

            summary_parts.append("\n".join(entry_parts))

        if len(code_chunks) > MAX_CHUNKS:
            summary_parts.append(f"\n... and {len(code_chunks) - MAX_CHUNKS} more elements")

    if reasoning_chunks:
        summary_parts.append(
            f"\n## Previous Solutions: {len(reasoning_chunks)} relevant patterns available",
        )

    if not summary_parts:
        return "No indexed context available. Using LLM general knowledge."

    return "\n\n".join(summary_parts)


def clear_cache() -> None:
    """Clear the decomposition cache.

    Useful for testing or when memory constraints require cache clearing.
    """
    global _decomposition_cache
    _decomposition_cache.clear()
