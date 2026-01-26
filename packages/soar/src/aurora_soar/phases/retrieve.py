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

        # Retrieve chunks using hybrid retrieval (BM25 + semantic + activation)
        # Use lower threshold to get more candidates for complex queries
        min_score = 0.3 if complexity in ("COMPLEX", "CRITICAL") else 0.5
        retrieved_chunks = retriever.retrieve(
            query,
            limit=budget,
            min_semantic_score=min_score,
        )

        # Separate chunks by type
        code_chunks = []
        reasoning_chunks = []

        for chunk in retrieved_chunks:
            # Get chunk type from metadata if available, otherwise use class name
            if hasattr(chunk, "metadata") and isinstance(chunk.metadata, dict):
                chunk_type = chunk.metadata.get("chunk_type", chunk.__class__.__name__)
            else:
                chunk_type = chunk.__class__.__name__

            if "Code" in chunk_type:
                code_chunks.append(chunk)
            elif "Reasoning" in chunk_type:
                reasoning_chunks.append(chunk)
            else:
                # Unknown type, put in code_chunks by default
                code_chunks.append(chunk)

        # Count high-quality chunks (those with good scores)
        high_quality_count = sum(
            1
            for chunk in retrieved_chunks
            if getattr(chunk, "score", getattr(chunk, "hybrid_score", 0.0)) >= 0.6
        )

        elapsed_ms = (time.time() - start_time) * 1000
        total_retrieved = len(retrieved_chunks)

        logger.info(
            f"Retrieved {total_retrieved} chunks "
            f"(code={len(code_chunks)}, reasoning={len(reasoning_chunks)}, "
            f"high_quality={high_quality_count}) "
            f"in {elapsed_ms:.1f}ms",
        )

        return {
            "code_chunks": code_chunks,
            "reasoning_chunks": reasoning_chunks,
            "total_retrieved": total_retrieved,
            "chunks_retrieved": total_retrieved,  # For CLI display
            "high_quality_count": high_quality_count,
            "retrieval_time_ms": elapsed_ms,
            "budget": budget,
            "budget_used": total_retrieved,
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
