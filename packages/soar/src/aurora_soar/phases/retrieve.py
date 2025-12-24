"""Phase 2: Context Retrieval.

This module implements the Retrieve phase of the SOAR pipeline, which retrieves
relevant context from ACT-R memory based on query keywords and complexity.

Budget allocation by complexity:
- SIMPLE: 5 chunks
- MEDIUM: 10 chunks
- COMPLEX: 15 chunks
- CRITICAL: 20 chunks

For Phase 2, we use basic activation-based retrieval. Phase 3 will add:
- Spreading activation from query keywords
- Base-level learning decay
- Semantic similarity scoring
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from aurora.core.store.base import Store


__all__ = ["retrieve_context"]


logger = logging.getLogger(__name__)


# Budget allocation by complexity level
RETRIEVAL_BUDGETS = {
    "SIMPLE": 5,
    "MEDIUM": 10,
    "COMPLEX": 15,
    "CRITICAL": 20,
}


def retrieve_context(query: str, complexity: str, store: Store) -> dict[str, Any]:
    """Retrieve relevant context from ACT-R memory.

    This function retrieves the most relevant chunks from memory based on
    activation scores. The number of chunks retrieved depends on query complexity.

    Phase 2 Implementation (Basic):
    - Use Store.retrieve_by_activation() for basic retrieval
    - No spreading activation yet (Phase 3)
    - No semantic similarity yet (Phase 3)
    - Just get top-N most activated chunks

    Args:
        query: User query string (currently unused, will be used in Phase 3 for spreading activation)
        complexity: Complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
        store: Store instance for retrieval

    Returns:
        Dict with keys:
            - code_chunks: list of CodeChunk objects
            - reasoning_chunks: list of ReasoningChunk objects
            - total_retrieved: int (total number of chunks)
            - retrieval_time_ms: float (retrieval duration)
            - budget: int (max chunks allocated)
            - budget_used: int (actual chunks retrieved)
    """
    start_time = time.time()

    # Determine retrieval budget based on complexity
    budget = RETRIEVAL_BUDGETS.get(complexity, 10)  # Default to MEDIUM if unknown

    logger.info(f"Retrieving context for {complexity} query (budget={budget} chunks)")

    try:
        # Phase 2: Basic activation-based retrieval
        # For now, retrieve chunks with any activation > 0
        # Phase 3 will add spreading activation from query keywords
        retrieved_chunks = store.retrieve_by_activation(
            min_activation=0.0,  # Get any activated chunks
            limit=budget,
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

        elapsed_ms = (time.time() - start_time) * 1000
        total_retrieved = len(retrieved_chunks)

        logger.info(
            f"Retrieved {total_retrieved} chunks "
            f"(code={len(code_chunks)}, reasoning={len(reasoning_chunks)}) "
            f"in {elapsed_ms:.1f}ms"
        )

        return {
            "code_chunks": code_chunks,
            "reasoning_chunks": reasoning_chunks,
            "total_retrieved": total_retrieved,
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
            "retrieval_time_ms": elapsed_ms,
            "budget": budget,
            "budget_used": 0,
            "error": str(e),
        }
