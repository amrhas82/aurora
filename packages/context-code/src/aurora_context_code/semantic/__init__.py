"""Semantic context awareness with embeddings and hybrid retrieval.

This module provides semantic understanding capabilities for AURORA's context
retrieval system. It implements:

1. **EmbeddingProvider**: Generates vector embeddings for code chunks and queries
   using sentence-transformers (all-MiniLM-L6-v2 by default).

2. **HybridRetriever**: Combines activation-based retrieval (60%) with semantic
   similarity (40%) for improved precision.

3. **Cosine Similarity**: Vector comparison for semantic matching.

Example:
    >>> from aurora_context_code.semantic import EmbeddingProvider, HybridRetriever
    >>>
    >>> # Initialize embedding provider
    >>> provider = EmbeddingProvider()
    >>>
    >>> # Generate embeddings for a code chunk
    >>> text = "def calculate_total(items): return sum(item.price for item in items)"
    >>> embedding = provider.embed_chunk(text)
    >>>
    >>> # Use hybrid retrieval
    >>> retriever = HybridRetriever(store, activation_engine, provider)
    >>> results = retriever.retrieve("calculate sum of prices", top_k=5)

Performance:
    - Embedding generation: <50ms per chunk (target)
    - Vector dimension: 384 (all-MiniLM-L6-v2)
    - Hybrid retrieval: ≥85% precision target (P@5)

See Also:
    - docs/semantic-retrieval.md: Semantic retrieval architecture
    - tests/unit/context_code/semantic/: Unit tests
    - tests/integration/test_semantic_retrieval.py: Integration tests

"""

from aurora_context_code.semantic.embedding_provider import EmbeddingProvider, cosine_similarity
from aurora_context_code.semantic.hybrid_retriever import HybridConfig, HybridRetriever
from aurora_context_code.semantic.model_utils import (
    DEFAULT_MODEL,
    BackgroundModelLoader,
    ensure_model_downloaded,
    is_model_cached,
)


__all__ = [
    "EmbeddingProvider",
    "cosine_similarity",
    "HybridRetriever",
    "HybridConfig",
    "DEFAULT_MODEL",
    "BackgroundModelLoader",
    "ensure_model_downloaded",
    "is_model_cached",
]
