"""Hybrid retrieval combining BM25, semantic similarity, and activation.

This module implements tri-hybrid retrieval with staged architecture:
- Stage 1: BM25 filtering (keyword exact match, top_k=100)
- Stage 2: Re-ranking with tri-hybrid scoring:
  * BM25 keyword matching (30% weight by default)
  * Semantic similarity (40% weight by default)
  * Activation-based ranking (30% weight by default)

Performance optimizations:
- Query embedding cache (LRU, configurable size)
- Persistent BM25 index (load once, rebuild on reindex)
- Activation score caching via CacheManager

Classes:
    HybridConfig: Configuration for hybrid retrieval weights
    HybridRetriever: Main hybrid retrieval implementation with BM25
"""

import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)


@dataclass
class HybridConfig:
    """Configuration for tri-hybrid retrieval.

    Supports two modes:
    1. Dual-hybrid (legacy): activation + semantic (weights sum to 1.0)
    2. Tri-hybrid (default): BM25 + activation + semantic (weights sum to 1.0)

    Attributes:
        bm25_weight: Weight for BM25 keyword score (default 0.3, use 0.0 for dual-hybrid)
        activation_weight: Weight for activation score (default 0.3, or 0.6 for dual-hybrid)
        semantic_weight: Weight for semantic similarity (default 0.4)
        activation_top_k: Number of top chunks to retrieve by activation (default 100)
        stage1_top_k: Number of candidates to pass from Stage 1 BM25 filter (default 100)
        fallback_to_activation: If True, fall back to activation-only if embeddings unavailable
        use_staged_retrieval: Enable staged retrieval (BM25 filter → re-rank)

    Example (tri-hybrid):
        >>> config = HybridConfig(bm25_weight=0.3, activation_weight=0.3, semantic_weight=0.4)
        >>> retriever = HybridRetriever(store, engine, provider, config)

    Example (dual-hybrid, legacy):
        >>> config = HybridConfig(bm25_weight=0.0, activation_weight=0.6, semantic_weight=0.4)
        >>> retriever = HybridRetriever(store, engine, provider, config)
    """

    bm25_weight: float = 0.3
    activation_weight: float = 0.3
    semantic_weight: float = 0.4
    activation_top_k: int = 500  # Increased from 100 to improve recall on large repos
    stage1_top_k: int = 100
    fallback_to_activation: bool = True
    use_staged_retrieval: bool = True
    # Caching configuration
    enable_query_cache: bool = True
    query_cache_size: int = 100
    query_cache_ttl_seconds: int = 1800  # 30 minutes
    bm25_index_path: str | None = None

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not (0.0 <= self.bm25_weight <= 1.0):
            raise ValueError(f"bm25_weight must be in [0, 1], got {self.bm25_weight}")
        if not (0.0 <= self.activation_weight <= 1.0):
            raise ValueError(f"activation_weight must be in [0, 1], got {self.activation_weight}")
        if not (0.0 <= self.semantic_weight <= 1.0):
            raise ValueError(f"semantic_weight must be in [0, 1], got {self.semantic_weight}")

        total_weight = self.bm25_weight + self.activation_weight + self.semantic_weight
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(
                f"Weights must sum to 1.0, got {total_weight} "
                f"(bm25={self.bm25_weight}, activation={self.activation_weight}, semantic={self.semantic_weight})"
            )

        if self.activation_top_k < 1:
            raise ValueError(f"activation_top_k must be >= 1, got {self.activation_top_k}")
        if self.stage1_top_k < 1:
            raise ValueError(f"stage1_top_k must be >= 1, got {self.stage1_top_k}")
        if self.query_cache_size < 1:
            raise ValueError(f"query_cache_size must be >= 1, got {self.query_cache_size}")
        if self.query_cache_ttl_seconds < 0:
            raise ValueError(
                f"query_cache_ttl_seconds must be >= 0, got {self.query_cache_ttl_seconds}"
            )


@dataclass
class CacheStats:
    """Statistics for query embedding cache."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class QueryEmbeddingCache:
    """LRU cache for query embeddings with TTL support.

    Caches query embeddings to avoid repeated embedding generation for
    identical or similar queries. Uses normalized query as key.

    Attributes:
        capacity: Maximum number of cached embeddings
        ttl_seconds: Time-to-live for cached entries
        stats: Cache statistics (hits, misses, evictions)
    """

    def __init__(self, capacity: int = 100, ttl_seconds: int = 1800):
        """Initialize query embedding cache.

        Args:
            capacity: Maximum cached embeddings (default 100)
            ttl_seconds: TTL in seconds (default 1800 = 30 min)
        """
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[npt.NDArray[np.float32], float]] = OrderedDict()
        self.stats = CacheStats()

    def _normalize_query(self, query: str) -> str:
        """Normalize query for cache key.

        Args:
            query: Raw query string

        Returns:
            Normalized query (lowercase, stripped, single spaces)
        """
        return " ".join(query.lower().split())

    def _make_key(self, query: str) -> str:
        """Create cache key from query.

        Args:
            query: Query string

        Returns:
            Hash-based cache key
        """
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, query: str) -> npt.NDArray[np.float32] | None:
        """Get cached embedding for query.

        Args:
            query: Query string

        Returns:
            Cached embedding if found and not expired, None otherwise
        """
        key = self._make_key(query)

        if key not in self._cache:
            self.stats.misses += 1
            return None

        embedding, timestamp = self._cache[key]

        # Check TTL
        if time.time() - timestamp > self.ttl_seconds:
            del self._cache[key]
            self.stats.misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self.stats.hits += 1
        return embedding

    def set(self, query: str, embedding: npt.NDArray[np.float32]) -> None:
        """Cache embedding for query.

        Args:
            query: Query string
            embedding: Query embedding to cache
        """
        key = self._make_key(query)

        # Remove if exists (will re-add at end)
        if key in self._cache:
            del self._cache[key]
        # Evict LRU if at capacity
        elif len(self._cache) >= self.capacity:
            self._cache.popitem(last=False)
            self.stats.evictions += 1

        self._cache[key] = (embedding, time.time())

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self._cache.clear()
        self.stats = CacheStats()

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class HybridRetriever:
    """Tri-hybrid retrieval combining BM25, semantic similarity, and activation.

    Retrieval process (staged architecture):
    1. Stage 1: BM25 Filtering
       - Retrieve top-K chunks by activation (default K=100)
       - Build BM25 index from candidates
       - Score candidates with BM25 keyword matching
       - Select top stage1_top_k candidates (default 100)
    2. Stage 2: Tri-hybrid Re-ranking
       - Calculate semantic similarity for Stage 1 candidates
       - Normalize BM25, semantic, and activation scores independently
       - Combine scores: 30% BM25 + 40% semantic + 30% activation (configurable)
       - Return top-N results by tri-hybrid score

    Attributes:
        store: Storage backend for chunks
        activation_engine: ACT-R activation engine
        embedding_provider: Provider for generating embeddings
        config: Hybrid retrieval configuration
        bm25_scorer: BM25 scorer for keyword matching (lazy-initialized)

    Example (tri-hybrid):
        >>> from aurora_core.store import SQLiteStore
        >>> from aurora_core.activation import ActivationEngine
        >>> from aurora_context_code.semantic import EmbeddingProvider, HybridRetriever
        >>>
        >>> store = SQLiteStore(":memory:")
        >>> engine = ActivationEngine(store)
        >>> provider = EmbeddingProvider()
        >>> retriever = HybridRetriever(store, engine, provider)
        >>>
        >>> results = retriever.retrieve("SoarOrchestrator", top_k=5)
        >>> # Results will favor exact keyword matches with tri-hybrid scoring
    """

    def __init__(
        self,
        store: Any,  # aurora_core.store.Store
        activation_engine: Any,  # aurora_core.activation.ActivationEngine
        embedding_provider: Any,  # EmbeddingProvider
        config: HybridConfig | None = None,
        aurora_config: Any | None = None,  # aurora_core.config.Config
    ):
        """Initialize tri-hybrid retriever.

        Args:
            store: Storage backend
            activation_engine: ACT-R activation engine
            embedding_provider: Embedding provider
            config: Hybrid configuration (takes precedence if provided)
            aurora_config: Global AURORA Config object (loads hybrid_weights from context.code.hybrid_weights)

        Note:
            If both config and aurora_config are provided, config takes precedence.
            If neither is provided, uses default HybridConfig values (tri-hybrid: 30/40/30).
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

        # BM25 scorer (lazy-initialized in retrieve())
        self.bm25_scorer: Any = None  # BM25Scorer from aurora_context_code.semantic.bm25_scorer

        # Query embedding cache
        if self.config.enable_query_cache:
            self._query_cache = QueryEmbeddingCache(
                capacity=self.config.query_cache_size,
                ttl_seconds=self.config.query_cache_ttl_seconds,
            )
            logger.debug(
                f"Query cache enabled: size={self.config.query_cache_size}, "
                f"ttl={self.config.query_cache_ttl_seconds}s"
            )
        else:
            self._query_cache = None

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        context_keywords: list[str] | None = None,
        min_semantic_score: float | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve chunks using tri-hybrid scoring with staged architecture.

        Args:
            query: User query string
            top_k: Number of results to return
            context_keywords: Optional keywords for context boost (not yet implemented)
            min_semantic_score: Minimum semantic score threshold (0.0-1.0). Results below this will be filtered out.

        Returns:
            List of dicts with keys:
            - chunk_id: Chunk identifier
            - content: Chunk content
            - bm25_score: BM25 keyword component (0-1 normalized)
            - activation_score: Activation component (0-1 normalized)
            - semantic_score: Semantic similarity component (0-1 normalized)
            - hybrid_score: Combined tri-hybrid score (0-1 range)
            - metadata: Additional chunk metadata

        Raises:
            ValueError: If query is empty or top_k < 1

        Example:
            >>> results = retriever.retrieve("SoarOrchestrator", top_k=5)
            >>> for result in results:
            ...     print(f"{result['chunk_id']}: {result['hybrid_score']:.3f}")
            ...     print(f"  BM25: {result['bm25_score']:.3f}")
            ...     print(f"  Semantic: {result['semantic_score']:.3f}")
            ...     print(f"  Activation: {result['activation_score']:.3f}")
        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")

        # Step 1: Retrieve top-K chunks by activation (candidates for Stage 1)
        activation_candidates = self.store.retrieve_by_activation(
            min_activation=0.0,  # Get all chunks, we'll filter by score
            limit=self.config.activation_top_k,
        )

        # If no chunks available, return empty list
        if not activation_candidates:
            return []

        # Step 2: Generate query embedding for semantic similarity (with caching)
        query_embedding = None
        cache_hit = False

        # Try cache first
        if self._query_cache is not None:
            query_embedding = self._query_cache.get(query)
            if query_embedding is not None:
                cache_hit = True
                logger.debug(f"Query cache hit for: {query[:50]}...")

        # Generate embedding if not cached
        if query_embedding is None:
            try:
                query_embedding = self.embedding_provider.embed_query(query)
                # Cache the embedding
                if self._query_cache is not None:
                    self._query_cache.set(query, query_embedding)
                    logger.debug(f"Cached embedding for: {query[:50]}...")
            except Exception as e:
                # If embedding fails and fallback is enabled, use activation-only
                if self.config.fallback_to_activation:
                    return self._fallback_to_activation_only(activation_candidates, top_k)
                raise ValueError(f"Failed to generate query embedding: {e}") from e

        # ========== STAGE 1: BM25 FILTERING ==========
        if self.config.use_staged_retrieval and self.config.bm25_weight > 0:
            stage1_candidates = self._stage1_bm25_filter(query, activation_candidates)
        else:
            # Skip Stage 1 if staged retrieval disabled or BM25 weight is 0
            stage1_candidates = activation_candidates

        # ========== STAGE 2: TRI-HYBRID RE-RANKING ==========
        results = []

        for chunk in stage1_candidates:
            # Get activation score (from chunk's activation attribute)
            activation_score = getattr(chunk, "activation", 0.0)

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

            # Calculate BM25 score (if enabled)
            if self.config.bm25_weight > 0 and self.bm25_scorer is not None:
                # Get chunk content for BM25 scoring
                chunk_content = self._get_chunk_content_for_bm25(chunk)
                bm25_score = self.bm25_scorer.score(query, chunk_content)
            else:
                bm25_score = 0.0

            # Store for later normalization
            results.append(
                {
                    "chunk": chunk,
                    "raw_activation": activation_score,
                    "raw_semantic": semantic_score,
                    "raw_bm25": bm25_score,
                }
            )

        # If no valid results, return empty
        if not results:
            return []

        # NOTE: Semantic threshold filtering is disabled when BM25 is enabled (tri-hybrid mode)
        # to allow keyword matches with low semantic similarity to be retrieved.
        # In tri-hybrid mode, the hybrid score (BM25 + semantic + activation) determines relevance.
        # Only filter by semantic score in dual-hybrid mode (when bm25_weight == 0)
        if min_semantic_score is not None and self.config.bm25_weight == 0.0:
            results = [r for r in results if r["raw_semantic"] >= min_semantic_score]
            if not results:
                return []  # All results below threshold

        # Normalize scores independently to [0, 1] range
        activation_scores_normalized = self._normalize_scores(
            [r["raw_activation"] for r in results]
        )
        semantic_scores_normalized = self._normalize_scores([r["raw_semantic"] for r in results])
        bm25_scores_normalized = self._normalize_scores([r["raw_bm25"] for r in results])

        # Calculate tri-hybrid scores and prepare output
        final_results = []
        for i, result_data in enumerate(results):
            chunk = result_data["chunk"]
            activation_norm = activation_scores_normalized[i]
            semantic_norm = semantic_scores_normalized[i]
            bm25_norm = bm25_scores_normalized[i]

            # Tri-hybrid scoring formula: weights × normalized scores
            hybrid_score = (
                self.config.bm25_weight * bm25_norm
                + self.config.activation_weight * activation_norm
                + self.config.semantic_weight * semantic_norm
            )

            # Extract content and metadata from chunk
            content, metadata = self._extract_chunk_content_metadata(chunk)

            final_results.append(
                {
                    "chunk_id": chunk.id,
                    "content": content,
                    "bm25_score": bm25_norm,
                    "activation_score": activation_norm,
                    "semantic_score": semantic_norm,
                    "hybrid_score": hybrid_score,
                    "metadata": metadata,
                }
            )

        # Sort by hybrid score (descending)
        final_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

        # Return top K results
        return final_results[:top_k]

    def _stage1_bm25_filter(self, query: str, candidates: list[Any]) -> list[Any]:
        """Stage 1: Filter candidates using BM25 keyword matching.

        Args:
            query: User query string
            candidates: Chunks retrieved by activation

        Returns:
            Top stage1_top_k candidates by BM25 score
        """
        # Build BM25 index from candidates
        from aurora_context_code.semantic.bm25_scorer import BM25Scorer

        self.bm25_scorer = BM25Scorer(k1=1.5, b=0.75)

        # Prepare documents for BM25 indexing
        documents = []
        for chunk in candidates:
            chunk_content = self._get_chunk_content_for_bm25(chunk)
            documents.append((chunk.id, chunk_content))

        # Build BM25 index
        self.bm25_scorer.build_index(documents)

        # Score all candidates with BM25
        scored_candidates = []
        for chunk in candidates:
            chunk_content = self._get_chunk_content_for_bm25(chunk)
            bm25_score = self.bm25_scorer.score(query, chunk_content)
            scored_candidates.append((bm25_score, chunk))

        # Sort by BM25 score (descending) and take top stage1_top_k
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [chunk for _, chunk in scored_candidates[: self.config.stage1_top_k]]

        return top_candidates

    def _get_chunk_content_for_bm25(self, chunk: Any) -> str:
        """Get chunk content suitable for BM25 tokenization.

        Args:
            chunk: Chunk object

        Returns:
            Content string (signature + docstring + name for CodeChunk)
        """
        # For CodeChunk: combine signature, docstring, and name
        if hasattr(chunk, "signature"):
            parts = []
            if getattr(chunk, "name", None):
                parts.append(chunk.name)
            if getattr(chunk, "signature", None):
                parts.append(chunk.signature)
            if getattr(chunk, "docstring", None):
                parts.append(chunk.docstring)
            return " ".join(parts) if parts else ""
        else:
            # For other chunk types, use to_json() content
            chunk_json = chunk.to_json() if hasattr(chunk, "to_json") else {}
            return str(chunk_json.get("content", ""))

    def _extract_chunk_content_metadata(self, chunk: Any) -> tuple[str, dict[str, Any]]:
        """Extract content and metadata from chunk.

        Args:
            chunk: Chunk object

        Returns:
            Tuple of (content, metadata)
        """
        # For CodeChunk: content is signature + docstring
        if hasattr(chunk, "signature") and hasattr(chunk, "docstring"):
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

            # Include access count from activation stats
            try:
                access_stats = self.store.get_access_stats(chunk.id)
                metadata["access_count"] = access_stats.get("access_count", 0)
            except Exception:
                # If access stats unavailable, default to 0
                metadata["access_count"] = 0

            # Include git metadata if available
            if hasattr(chunk, "metadata") and chunk.metadata:
                if "commit_count" in chunk.metadata:
                    metadata["commit_count"] = chunk.metadata["commit_count"]
                if "last_modified" in chunk.metadata:
                    metadata["last_modified"] = chunk.metadata["last_modified"]
                if "git_hash" in chunk.metadata:
                    metadata["git_hash"] = chunk.metadata["git_hash"]
        else:
            # Other chunk types - use to_json() to get content
            chunk_json = chunk.to_json() if hasattr(chunk, "to_json") else {}
            content = str(chunk_json.get("content", ""))
            metadata = {
                "type": getattr(chunk, "type", "unknown"),
                "name": getattr(chunk, "name", ""),
                "file_path": getattr(chunk, "file_path", ""),
            }

            # Include access count from activation stats
            try:
                access_stats = self.store.get_access_stats(chunk.id)
                metadata["access_count"] = access_stats.get("access_count", 0)
            except Exception:
                # If access stats unavailable, default to 0
                metadata["access_count"] = 0

            # Include git metadata if available
            if hasattr(chunk, "metadata") and chunk.metadata:
                if "commit_count" in chunk.metadata:
                    metadata["commit_count"] = chunk.metadata["commit_count"]
                if "last_modified" in chunk.metadata:
                    metadata["last_modified"] = chunk.metadata["last_modified"]
                if "git_hash" in chunk.metadata:
                    metadata["git_hash"] = chunk.metadata["git_hash"]

        return content, metadata

    def _fallback_to_activation_only(self, chunks: list[Any], top_k: int) -> list[dict[str, Any]]:
        """Fallback to activation-only retrieval when embeddings unavailable.

        Args:
            chunks: Chunks retrieved by activation
            top_k: Number of results to return

        Returns:
            List of results with activation scores only (tri-hybrid format)
        """
        results = []
        for chunk in chunks[:top_k]:
            activation_score = getattr(chunk, "activation", 0.0)
            content, metadata = self._extract_chunk_content_metadata(chunk)
            results.append(
                {
                    "chunk_id": chunk.id,
                    "content": content,
                    "bm25_score": 0.0,
                    "activation_score": activation_score,
                    "semantic_score": 0.0,
                    "hybrid_score": activation_score,  # Pure activation
                    "metadata": metadata,
                }
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
        """Load tri-hybrid configuration from global AURORA Config.

        Args:
            aurora_config: AURORA Config object with context.code.hybrid_weights

        Returns:
            HybridConfig loaded from config

        Raises:
            ValueError: If config values are invalid
        """
        # Load from context.code.hybrid_weights section
        weights = aurora_config.get("context.code.hybrid_weights", {})

        # Extract values with fallback to tri-hybrid defaults
        bm25_weight = weights.get("bm25", 0.3)
        activation_weight = weights.get("activation", 0.3)
        semantic_weight = weights.get("semantic", 0.4)
        activation_top_k = weights.get("top_k", 500)  # Match HybridConfig default
        stage1_top_k = weights.get("stage1_top_k", 100)
        fallback_to_activation = weights.get("fallback_to_activation", True)
        use_staged_retrieval = weights.get("use_staged_retrieval", True)

        # Create and validate HybridConfig (validation happens in __post_init__)
        return HybridConfig(
            bm25_weight=bm25_weight,
            activation_weight=activation_weight,
            semantic_weight=semantic_weight,
            activation_top_k=activation_top_k,
            stage1_top_k=stage1_top_k,
            fallback_to_activation=fallback_to_activation,
            use_staged_retrieval=use_staged_retrieval,
        )

    def get_cache_stats(self) -> dict[str, Any]:
        """Get query embedding cache statistics.

        Returns:
            Dictionary with cache stats:
            - enabled: Whether cache is enabled
            - size: Current number of cached embeddings
            - capacity: Maximum cache capacity
            - hits: Number of cache hits
            - misses: Number of cache misses
            - hit_rate: Cache hit rate (0.0-1.0)
            - evictions: Number of LRU evictions
        """
        if self._query_cache is None:
            return {"enabled": False}

        return {
            "enabled": True,
            "size": self._query_cache.size(),
            "capacity": self._query_cache.capacity,
            "hits": self._query_cache.stats.hits,
            "misses": self._query_cache.stats.misses,
            "hit_rate": self._query_cache.stats.hit_rate,
            "evictions": self._query_cache.stats.evictions,
        }

    def clear_cache(self) -> None:
        """Clear the query embedding cache."""
        if self._query_cache is not None:
            self._query_cache.clear()
            logger.debug("Query embedding cache cleared")
