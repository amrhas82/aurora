"""Phase 2: Context Retrieval.

This module implements the Retrieve phase of the SOAR pipeline, which retrieves
relevant context from memory using hybrid retrieval (BM25 + semantic + activation).

Budget allocation by complexity:
- SIMPLE: 5 chunks
- MEDIUM: 10 chunks
- COMPLEX: 15 chunks
- CRITICAL: 20 chunks

Uses MemoryRetriever with HybridRetriever for query-based retrieval,
combining keyword matching, semantic similarity, and activation scoring.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from aurora_core.store.base import Store
    from aurora_core.store.sqlite import SQLiteStore


__all__ = ["retrieve_context"]


logger = logging.getLogger(__name__)


# Budget allocation by complexity level
RETRIEVAL_BUDGETS = {
    "SIMPLE": 5,
    "MEDIUM": 10,
    "COMPLEX": 15,
    "CRITICAL": 20,
}

# Activation threshold for high-quality chunks
# Chunks with activation >= this threshold are considered high-quality
ACTIVATION_THRESHOLD = 0.3


def filter_by_activation(chunks: list[Any], store: Store | None = None) -> tuple[list[Any], int]:
    """Filter chunks by activation threshold and count high-quality chunks.

    Args:
        chunks: List of chunks to filter (CodeChunk or ReasoningChunk objects)
        store: Optional Store instance to query activation scores

    Returns:
        Tuple of (all_chunks, high_quality_count) where:
            - all_chunks: All chunks (unchanged, for backward compatibility)
            - high_quality_count: Count of chunks with activation >= ACTIVATION_THRESHOLD

    """
    high_quality_count = 0

    if not chunks:
        return chunks, 0

    # If we have a store, query activation scores from the database
    if store is not None:
        for chunk in chunks:
            try:
                # Query the activations table for this chunk's base_level
                # SQLiteStore has a _get_connection method but it's internal
                # We'll use get_activation if available, or fall back to attribute check
                if hasattr(store, "get_activation"):
                    activation = store.get_activation(chunk.id)
                else:
                    # Fallback: check if chunk has activation attribute
                    activation = getattr(chunk, "activation", 0.0)
            except Exception:
                # If we can't get activation, assume 0.0
                activation = 0.0

            if activation is not None and activation >= ACTIVATION_THRESHOLD:
                high_quality_count += 1
    else:
        # Fallback: try to get activation from chunk attributes
        for chunk in chunks:
            activation = getattr(chunk, "activation", 0.0)
            if activation is None:
                activation = 0.0

            if activation >= ACTIVATION_THRESHOLD:
                high_quality_count += 1

    return chunks, high_quality_count


def retrieve_context(query: str, complexity: str, store: Store) -> dict[str, Any]:
    """Retrieve relevant context from memory using hybrid retrieval.

    Uses MemoryRetriever with HybridRetriever to find chunks relevant to the query.
    Combines BM25 keyword matching, semantic similarity, and activation scoring.

    Args:
        query: User query string for retrieval matching
        complexity: Complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
        store: Store instance for retrieval

    Returns:
        Dict with keys:
            - code_chunks: list of CodeChunk objects
            - reasoning_chunks: list of ReasoningChunk objects
            - total_retrieved: int (total number of chunks)
            - high_quality_count: int (chunks with high relevance scores)
            - retrieval_time_ms: float (retrieval duration)
            - budget: int (max chunks allocated)
            - budget_used: int (actual chunks retrieved)

    """
    start_time = time.time()

    # Determine retrieval budget based on complexity
    budget = RETRIEVAL_BUDGETS.get(complexity, 10)  # Default to MEDIUM if unknown

    logger.info(f"Retrieving context for {complexity} query (budget={budget} chunks)")

    try:
        # Use MemoryRetriever with HybridRetriever for query-based retrieval
        from aurora_cli.memory.retrieval import MemoryRetriever

        # Cast Store to SQLiteStore as MemoryRetriever expects that specific type
        # The Store interface is compatible, but mypy needs the explicit cast
        sqlite_store = cast("SQLiteStore", store)
        retriever = MemoryRetriever(store=sqlite_store)

        # Check if memory is indexed
        if not retriever.has_indexed_memory():
            logger.warning("No memory index. Run 'aur mem index .' if in wrong directory")
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "code_chunks": [],
                "reasoning_chunks": [],
                "total_retrieved": 0,
                "chunks_retrieved": 0,
                "high_quality_count": 0,
                "retrieval_time_ms": elapsed_ms,
                "budget": budget,
                "budget_used": 0,
            }

        # Type-aware retrieval: query code and KB separately to ensure both are represented
        # This prevents natural language queries from returning only KB/logs
        CODE_SLOT_BUDGETS = {
            "SIMPLE": 3,
            "MEDIUM": 5,
            "COMPLEX": 7,
            "CRITICAL": 10,
        }
        CODE_SLOTS = CODE_SLOT_BUDGETS.get(complexity, 5)
        KB_SLOTS = max(0, budget - CODE_SLOTS)  # e.g., 15 - 7 = 8 for COMPLEX
        min_score = 0.3 if complexity in ("COMPLEX", "CRITICAL") else 0.5

        # Retrieve code chunks (type='code')
        code_results = retriever.retrieve(
            query,
            limit=CODE_SLOTS,
            min_semantic_score=min_score,
            chunk_type="code",
        )

        # Retrieve KB chunks (type='kb')
        kb_results = retriever.retrieve(
            query,
            limit=KB_SLOTS,
            min_semantic_score=min_score,
            chunk_type="kb",
        )

        # Combine: code first, then kb
        code_chunks = list(code_results) + list(kb_results)
        reasoning_chunks: list = []  # TODO: retrieve reasoning chunks if needed

        logger.info(f"Type-aware retrieval: {len(code_results)} code + {len(kb_results)} kb")

        # Count high-quality chunks (score >= 0.6)
        high_quality_count = sum(
            1 for c in code_results if getattr(c, "hybrid_score", getattr(c, "score", 0.0)) >= 0.6
        )

        elapsed_ms = (time.time() - start_time) * 1000
        total_selected = len(code_chunks) + len(reasoning_chunks)

        logger.info(
            f"Retrieved {total_selected} chunks "
            f"(code={len(code_results)}, kb={len(kb_results)}, reasoning={len(reasoning_chunks)}) "
            f"in {elapsed_ms:.1f}ms",
        )

        return {
            "code_chunks": code_chunks,
            "reasoning_chunks": reasoning_chunks,
            "total_retrieved": total_selected,
            "chunks_retrieved": total_selected,  # For CLI display
            "high_quality_count": high_quality_count,
            "retrieval_time_ms": elapsed_ms,
            "budget": budget,
            "budget_used": total_selected,
        }

    except Exception as e:
        logger.error(f"Context retrieval failed: {e}")
        # Return empty context on error
        elapsed_ms = (time.time() - start_time) * 1000
        return {
            "code_chunks": [],
            "reasoning_chunks": [],
            "total_retrieved": 0,
            "high_quality_count": 0,
            "retrieval_time_ms": elapsed_ms,
            "budget": budget,
            "budget_used": 0,
            "error": str(e),
        }
