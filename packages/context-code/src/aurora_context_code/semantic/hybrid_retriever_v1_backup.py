"""BACKUP: Hybrid retrieval combining activation and semantic similarity (pre-BM25).

This is a backup of the original hybrid retriever implementation before adding BM25 tri-hybrid search.

Original Implementation (v1):
- Activation-based ranking (60% weight by default)
- Semantic similarity (40% weight by default)
- No BM25 keyword matching

This backup was created before implementing:
- BM25 tri-hybrid search (30% BM25 + 40% Semantic + 30% Activation)
- Staged retrieval architecture (BM25 filter → re-rank)
- Code-aware tokenization for exact keyword matching

Date: 2025-12-31
PRD: tasks/0015-prd-bm25-trihybrid-memory-search.md
Task: 2.3 - Backup Current HybridRetriever

Classes:
    HybridConfig: Configuration for hybrid retrieval weights
    HybridRetriever: Main hybrid retrieval implementation
"""

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class HybridConfig:
    """Configuration for hybrid retrieval.

    Attributes:
        activation_weight: Weight for activation score (default 0.6)
        semantic_weight: Weight for semantic similarity (default 0.4)
        activation_top_k: Number of top chunks to retrieve by activation (default 100)
        fallback_to_activation: If True, fall back to activation-only if embeddings unavailable

    Example:
        >>> config = HybridConfig(activation_weight=0.7, semantic_weight=0.3)
        >>> retriever = HybridRetriever(store, engine, provider, config)

    """

    activation_weight: float = 0.6
    semantic_weight: float = 0.4
    activation_top_k: int = 100
    fallback_to_activation: bool = True

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not (0.0 <= self.activation_weight <= 1.0):
            raise ValueError(f"activation_weight must be in [0, 1], got {self.activation_weight}")
        if not (0.0 <= self.semantic_weight <= 1.0):
            raise ValueError(f"semantic_weight must be in [0, 1], got {self.semantic_weight}")
        if abs(self.activation_weight + self.semantic_weight - 1.0) > 1e-6:
            raise ValueError(
                f"Weights must sum to 1.0, got {self.activation_weight + self.semantic_weight}",
            )
        if self.activation_top_k < 1:
            raise ValueError(f"activation_top_k must be >= 1, got {self.activation_top_k}")


class HybridRetriever:
    """Hybrid retrieval combining activation and semantic similarity.

    Retrieval process:
    1. Retrieve top-K chunks by activation (default K=100)
    2. Calculate semantic similarity for these chunks
    3. Combine scores: 0.6 * activation + 0.4 * semantic
    4. Return top-N results by hybrid score

    Attributes:
        store: Storage backend for chunks
        activation_engine: ACT-R activation engine
        embedding_provider: Provider for generating embeddings
        config: Hybrid retrieval configuration

    Example:
        >>> from aurora_core.store import SQLiteStore
        >>> from aurora_core.activation import ActivationEngine
        >>> from aurora_context_code.semantic import EmbeddingProvider, HybridRetriever
        >>>
        >>> store = SQLiteStore(":memory:")
        >>> engine = ActivationEngine(store)
        >>> provider = EmbeddingProvider()
        >>> retriever = HybridRetriever(store, engine, provider)
        >>>
        >>> results = retriever.retrieve("calculate total price", top_k=5)

    """

    def __init__(
        self,
        store: Any,  # aurora_core.store.Store
        activation_engine: Any,  # aurora_core.activation.ActivationEngine
        embedding_provider: Any,  # EmbeddingProvider
        config: HybridConfig | None = None,
        aurora_config: Any | None = None,  # aurora_core.config.Config
    ):
        """Initialize hybrid retriever.

        Args:
            store: Storage backend
            activation_engine: ACT-R activation engine
            embedding_provider: Embedding provider
            config: Hybrid configuration (takes precedence if provided)
            aurora_config: Global AURORA Config object (loads hybrid_weights from context.code.hybrid_weights)

        Note:
            If both config and aurora_config are provided, config takes precedence.
            If neither is provided, uses default HybridConfig values.

        """
        self.store = store
        self.activation_engine = activation_engine
        self.embedding_provider = embedding_provider

        # Load configuration with precedence: explicit config > aurora_config > defaults
        if config is not None:
            self.config = config
        elif aurora_config is not None:
            self.config = self._load_from_aurora_config(aurora_config)
        else:
            self.config = HybridConfig()

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        _context_keywords: list[str] | None = None,
        min_semantic_score: float | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve chunks using hybrid scoring.

        Args:
            query: User query string
            top_k: Number of results to return
            context_keywords: Optional keywords for context boost
            min_semantic_score: Minimum semantic score threshold (0.0-1.0). Results below this will be filtered out.

        Returns:
            List of dicts with keys:
            - chunk_id: Chunk identifier
            - content: Chunk content
            - activation_score: Activation component (0-1 normalized)
            - semantic_score: Semantic similarity component (0-1 normalized)
            - hybrid_score: Combined score (0-1 range)
            - metadata: Additional chunk metadata

        Raises:
            ValueError: If query is empty or top_k < 1

        Example:
            >>> results = retriever.retrieve("how to calculate totals", top_k=5)
            >>> for result in results:
            ...     print(f"{result['chunk_id']}: {result['hybrid_score']:.3f}")

        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")

        # Step 1: Retrieve top-K chunks by activation
        # Use activation_top_k from config (default 100)
        activation_candidates = self.store.retrieve_by_activation(
            min_activation=0.0,  # Get all chunks, we'll filter by score
            limit=self.config.activation_top_k,
        )

        # If no chunks available, return empty list
        if not activation_candidates:
            return []

        # Step 2: Generate query embedding for semantic similarity
        try:
            query_embedding = self.embedding_provider.embed_query(query)
        except Exception as e:
            # If embedding fails and fallback is enabled, use activation-only
            if self.config.fallback_to_activation:
                return self._fallback_to_activation_only(activation_candidates, top_k)
            raise ValueError(f"Failed to generate query embedding: {e}") from e

        # Step 3: Calculate hybrid scores for each candidate
        results = []
        activation_scores = []
        semantic_scores = []

        for chunk in activation_candidates:
            # Get activation score (from chunk's activation attribute)
            activation_score = getattr(chunk, "activation", 0.0)
            activation_scores.append(activation_score)

            # Calculate semantic similarity
            chunk_embedding = getattr(chunk, "embeddings", None)
            if chunk_embedding is not None:
                from aurora_context_code.semantic.embedding_provider import cosine_similarity

                # Convert embedding bytes to numpy array if needed
                if isinstance(chunk_embedding, bytes):
                    chunk_embedding = np.frombuffer(chunk_embedding, dtype=np.float32)

                semantic_score = cosine_similarity(query_embedding, chunk_embedding)
                # Cosine similarity is in [-1, 1], normalize to [0, 1]
                semantic_score = (semantic_score + 1.0) / 2.0
            # No embedding available, use 0 or fallback
            elif self.config.fallback_to_activation:
                semantic_score = 0.0
            else:
                continue  # Skip chunks without embeddings

            semantic_scores.append(semantic_score)

            # Store for later normalization
            results.append(
                {
                    "chunk": chunk,
                    "raw_activation": activation_score,
                    "raw_semantic": semantic_score,
                },
            )

        # If no valid results, return empty
        if not results:
            return []

        # Step 3.5: Filter by RAW semantic score threshold BEFORE normalization
        # This ensures we filter by absolute similarity, not relative ranking
        if min_semantic_score is not None:
            # Filter results where raw_semantic >= threshold
            # raw_semantic is already normalized to [0,1] from cosine similarity
            results = [r for r in results if r["raw_semantic"] >= min_semantic_score]
            if not results:
                return []  # All results below threshold

        # Step 4: Normalize scores to [0, 1] range
        activation_scores_normalized = self._normalize_scores(
            [r["raw_activation"] for r in results],
        )
        semantic_scores_normalized = self._normalize_scores([r["raw_semantic"] for r in results])

        # Step 5: Calculate hybrid scores and prepare output
        final_results = []
        for i, result_data in enumerate(results):
            chunk = result_data["chunk"]
            activation_norm = activation_scores_normalized[i]
            semantic_norm = semantic_scores_normalized[i]

            # Hybrid scoring formula: 0.6 × activation + 0.4 × semantic
            hybrid_score = (
                self.config.activation_weight * activation_norm
                + self.config.semantic_weight * semantic_norm
            )

            # Extract content and metadata from chunk
            # For CodeChunk: content is signature + docstring
            # For other types: use to_json()
            if hasattr(chunk, "signature") and hasattr(chunk, "docstring"):
                # CodeChunk
                content_parts = []
                if getattr(chunk, "signature", None):
                    content_parts.append(chunk.signature)
                if getattr(chunk, "docstring", None):
                    content_parts.append(chunk.docstring)
                content = "\n".join(content_parts) if content_parts else ""

                metadata = {
                    "type": getattr(chunk, "type", "unknown"),
                    "name": getattr(chunk, "name", ""),
                    "file_path": getattr(chunk, "file_path", ""),
                    "line_start": getattr(chunk, "line_start", 0),
                    "line_end": getattr(chunk, "line_end", 0),
                }
            else:
                # Other chunk types - use to_json() to get content
                chunk_json = chunk.to_json() if hasattr(chunk, "to_json") else {}
                content = str(chunk_json.get("content", ""))
                metadata = {
                    "type": getattr(chunk, "type", "unknown"),
                    "name": getattr(chunk, "name", ""),
                    "file_path": getattr(chunk, "file_path", ""),
                }

            final_results.append(
                {
                    "chunk_id": chunk.id,
                    "content": content,
                    "activation_score": activation_norm,
                    "semantic_score": semantic_norm,
                    "hybrid_score": hybrid_score,
                    "metadata": metadata,
                },
            )

        # Step 6: Sort by hybrid score (descending)
        final_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

        # Step 7: Return top K results (filtering already done in Step 3.5)
        return final_results[:top_k]

    def _fallback_to_activation_only(self, chunks: list[Any], top_k: int) -> list[dict[str, Any]]:
        """Fallback to activation-only retrieval when embeddings unavailable.

        Args:
            chunks: Chunks retrieved by activation
            top_k: Number of results to return

        Returns:
            List of results with activation scores only

        """
        results = []
        for chunk in chunks[:top_k]:
            activation_score = getattr(chunk, "activation", 0.0)
            results.append(
                {
                    "chunk_id": chunk.id,
                    "content": getattr(chunk, "content", ""),
                    "activation_score": activation_score,
                    "semantic_score": 0.0,
                    "hybrid_score": activation_score,  # Pure activation
                    "metadata": {
                        "type": getattr(chunk, "type", "unknown"),
                        "name": getattr(chunk, "name", ""),
                        "file_path": getattr(chunk, "file_path", ""),
                    },
                },
            )
        return results

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        """Normalize scores to [0, 1] range using min-max scaling.

        Args:
            scores: Raw scores to normalize

        Returns:
            Normalized scores in [0, 1] range

        Note:
            When all scores are equal, returns original scores unchanged
            to preserve meaningful zero values rather than inflating to 1.0.

        """
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)

        if max_score - min_score < 1e-9:
            # All scores equal - preserve original values
            # This prevents [0.0, 0.0, 0.0] from becoming [1.0, 1.0, 1.0]
            return list(scores)

        return [(s - min_score) / (max_score - min_score) for s in scores]

    def _load_from_aurora_config(self, aurora_config: Any) -> HybridConfig:
        """Load hybrid configuration from global AURORA Config.

        Args:
            aurora_config: AURORA Config object with context.code.hybrid_weights

        Returns:
            HybridConfig loaded from config

        Raises:
            ValueError: If config values are invalid

        """
        # Load from context.code.hybrid_weights section
        weights = aurora_config.get("context.code.hybrid_weights", {})

        # Extract values with fallback to defaults
        activation_weight = weights.get("activation", 0.6)
        semantic_weight = weights.get("semantic", 0.4)
        activation_top_k = weights.get("top_k", 100)
        fallback_to_activation = weights.get("fallback_to_activation", True)

        # Create and validate HybridConfig (validation happens in __post_init__)
        return HybridConfig(
            activation_weight=activation_weight,
            semantic_weight=semantic_weight,
            activation_top_k=activation_top_k,
            fallback_to_activation=fallback_to_activation,
        )
