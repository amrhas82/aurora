"""AURORA Context-Code Package

Provides code parsing, analysis, and semantic understanding capabilities:
- Abstract CodeParser interface
- Parser registry for language-specific parsers
- Python parser using tree-sitter
- Semantic embeddings and hybrid retrieval

Note: Semantic components (EmbeddingProvider, HybridRetriever) are available
but not imported at package load time to avoid 20+ second torch import delay.
Import them explicitly when needed:
    from aurora_context_code.semantic import EmbeddingProvider
"""

from typing import Any

__version__ = "0.1.0"


# Lazy imports for semantic components to avoid 20+ second torch import on package load.
# These are only loaded when actually accessed, not at import time.
def __getattr__(name: str) -> Any:
    """Lazy import semantic components only when accessed."""
    if name in ("EmbeddingProvider", "HybridConfig", "HybridRetriever", "cosine_similarity"):
        from aurora_context_code.semantic import (
            EmbeddingProvider,
            HybridConfig,
            HybridRetriever,
            cosine_similarity,
        )

        # Return the requested item
        return {
            "EmbeddingProvider": EmbeddingProvider,
            "HybridConfig": HybridConfig,
            "HybridRetriever": HybridRetriever,
            "cosine_similarity": cosine_similarity,
        }[name]
    raise AttributeError(f"module 'aurora_context_code' has no attribute {name!r}")


__all__ = [
    "EmbeddingProvider",
    "HybridRetriever",
    "HybridConfig",
    "cosine_similarity",
]
