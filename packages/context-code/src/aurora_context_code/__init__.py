"""
AURORA Context-Code Package

Provides code parsing, analysis, and semantic understanding capabilities:
- Abstract CodeParser interface
- Parser registry for language-specific parsers
- Python parser using tree-sitter
- Semantic embeddings and hybrid retrieval
"""

__version__ = "0.1.0"

# Re-export semantic components for convenience
from aurora_context_code.semantic import (
    EmbeddingProvider,
    HybridRetriever,
    HybridConfig,
    cosine_similarity,
)

__all__ = [
    "EmbeddingProvider",
    "HybridRetriever",
    "HybridConfig",
    "cosine_similarity",
]
