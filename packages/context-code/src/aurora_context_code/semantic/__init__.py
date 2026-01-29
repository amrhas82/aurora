"""Semantic context awareness with embeddings and hybrid retrieval.

This module provides semantic understanding capabilities for AURORA's context
retrieval system. It implements:

1. **EmbeddingProvider**: Generates vector embeddings for code chunks and queries
   using sentence-transformers (all-MiniLM-L6-v2 by default).

2. **HybridRetriever**: Combines activation-based retrieval (60%) with semantic
   similarity (40%) for improved precision.

3. **OptimizedEmbeddingLoader**: Advanced loading strategies for faster startup.

4. **Cosine Similarity**: Vector comparison for semantic matching.

Example:
    >>> from aurora_context_code.semantic import get_embedding_provider
    >>>
    >>> # Get provider with optimized loading
    >>> provider = get_embedding_provider()
    >>>
    >>> # Generate embeddings for a code chunk
    >>> text = "def calculate_total(items): return sum(item.price for item in items)"
    >>> embedding = provider.embed_chunk(text)
    >>>
    >>> # Use hybrid retrieval
    >>> retriever = HybridRetriever(store, activation_engine, provider)
    >>> results = retriever.retrieve("calculate sum of prices", top_k=5)

Optimized Loading:
    >>> from aurora_context_code.semantic import preload_embeddings, LoadingStrategy
    >>>
    >>> # Preload in background (recommended for CLI startup)
    >>> preload_embeddings(strategy=LoadingStrategy.PROGRESSIVE)
    >>>
    >>> # Later, get the provider (returns immediately if already loaded)
    >>> provider = get_embedding_provider()

Performance:
    - Embedding generation: <50ms per chunk (target)
    - Vector dimension: 384 (all-MiniLM-L6-v2)
    - Hybrid retrieval: ≥85% precision target (P@5)
    - Model loading: <3s (warm start with progressive loading)

See Also:
    - docs/semantic-retrieval.md: Semantic retrieval architecture
    - docs/performance/embedding_load_profiling.md: Loading optimization
    - tests/unit/context_code/semantic/: Unit tests
    - tests/integration/test_semantic_retrieval.py: Integration tests

"""

from aurora_context_code.semantic.embedding_provider import EmbeddingProvider, cosine_similarity
from aurora_context_code.semantic.hybrid_retriever import HybridConfig, HybridRetriever
from aurora_context_code.semantic.model_utils import (
    DEFAULT_MODEL,
    BackgroundModelLoader,
    MLDependencyError,
    ensure_model_downloaded,
    is_model_cached,
    validate_ml_ready,
)
from aurora_context_code.semantic.optimized_loader import (
    LoadingStrategy,
    ModelMetadata,
    OptimizedEmbeddingLoader,
    ResourceProfile,
)

__all__ = [
    # Core classes
    "EmbeddingProvider",
    "HybridRetriever",
    "BackgroundModelLoader",
    "OptimizedEmbeddingLoader",
    # Config
    "HybridConfig",
    # Enums
    "LoadingStrategy",
    # Data classes
    "ModelMetadata",
    "ResourceProfile",
    # Exceptions
    "MLDependencyError",
    # Functions
    "cosine_similarity",
    "ensure_model_downloaded",
    "get_embedding_provider",
    "is_model_cached",
    "preload_embeddings",
    "validate_ml_ready",
    # Constants
    "DEFAULT_MODEL",
]


# Default singleton instance
_default_loader: OptimizedEmbeddingLoader | None = None


def get_embedding_provider(
    model_name: str = "all-MiniLM-L6-v2",
    strategy: LoadingStrategy = LoadingStrategy.PROGRESSIVE,
    timeout: float = 60.0,
) -> EmbeddingProvider | None:
    """Get an EmbeddingProvider using optimized loading.

    This is the recommended way to get an embedding provider. It uses
    the OptimizedEmbeddingLoader with a singleton pattern for efficiency.

    Args:
        model_name: Model name (default: all-MiniLM-L6-v2)
        strategy: Loading strategy (default: PROGRESSIVE for best startup time)
        timeout: Maximum time to wait for loading (seconds)

    Returns:
        EmbeddingProvider if loaded successfully, None if failed

    Example:
        >>> provider = get_embedding_provider()
        >>> if provider:
        ...     embedding = provider.embed_query("search query")
    """
    global _default_loader

    if _default_loader is None:
        _default_loader = OptimizedEmbeddingLoader.get_instance(
            model_name=model_name,
            strategy=strategy,
        )
        _default_loader.start_loading()

    return _default_loader.get_provider(timeout=timeout)


def preload_embeddings(
    model_name: str = "all-MiniLM-L6-v2",
    strategy: LoadingStrategy = LoadingStrategy.BACKGROUND,
) -> None:
    """Start loading embeddings in the background.

    Call this early in application startup to pre-warm the embedding model.
    The model will be ready by the time you need it.

    Args:
        model_name: Model name to load
        strategy: Loading strategy (default: BACKGROUND)

    Example:
        >>> # At application startup
        >>> preload_embeddings()
        >>>
        >>> # Later, when needed
        >>> provider = get_embedding_provider()
    """
    global _default_loader

    if _default_loader is None:
        _default_loader = OptimizedEmbeddingLoader.get_instance(
            model_name=model_name,
            strategy=strategy,
        )
        _default_loader.start_loading()
