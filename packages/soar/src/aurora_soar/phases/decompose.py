"""Phase 3: Query Decomposition.

This module implements the Decompose phase of the SOAR pipeline, which breaks
down complex queries into executable subgoals using LLM-based reasoning.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aurora.reasoning import LLMClient
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
    context_summary = _build_context_summary(context)

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


def _build_context_summary(context: dict[str, Any]) -> str:
    """Build a concise summary of retrieved context for decomposition.

    Args:
        context: Context dict with code_chunks and reasoning_chunks

    Returns:
        Summary string describing available context. When no chunks are
        available (empty retrieval), returns a note indicating that LLM
        general knowledge will be used, signaling to downstream phases
        that retrieval failed.
    """
    code_chunks = context.get("code_chunks", [])
    reasoning_chunks = context.get("reasoning_chunks", [])

    summary_parts = []

    if code_chunks:
        summary_parts.append(
            f"Available code context: {len(code_chunks)} code chunks covering "
            f"relevant functions, classes, and modules"
        )

    if reasoning_chunks:
        summary_parts.append(
            f"Reasoning patterns: {len(reasoning_chunks)} previous successful "
            f"decompositions and solutions"
        )

    # When no context is available (0 code chunks AND 0 reasoning chunks),
    # return special message to signal retrieval failure to downstream phases
    if not summary_parts:
        return "No indexed context available. Using LLM general knowledge."

    return ". ".join(summary_parts) + "."


def clear_cache() -> None:
    """Clear the decomposition cache.

    Useful for testing or when memory constraints require cache clearing.
    """
    global _decomposition_cache
    _decomposition_cache.clear()
