"""Relationship Graph Caching for Spreading Activation

This module provides efficient caching of relationship graphs to avoid
rebuilding the graph on every spreading activation calculation. The cache
automatically rebuilds when the underlying relationships change or after
a configurable number of retrievals.

Caching Strategy:
- Build graph once from database relationships
- Reuse graph for multiple spreading calculations
- Rebuild every N retrievals (default 100) to pick up new relationships
- Limit graph size to prevent memory bloat (default 1000 edges max)
- Thread-safe operations for concurrent access

Benefits:
- Reduces database queries (build once, use many times)
- Improves spreading activation performance
- Balances freshness vs. performance
- Memory-bounded (won't grow indefinitely)
"""

import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Protocol

from aurora_core.activation.spreading import RelationshipGraph
from aurora_core.types import ChunkID


if TYPE_CHECKING:
    from aurora_core.activation.spreading import SpreadingActivation


class RelationshipProvider(Protocol):
    """Protocol for objects that can provide relationships.

    This allows the cache to work with different storage backends
    without tight coupling to a specific Store implementation.
    """

    def get_all_relationships(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Get all relationships from storage.

        Args:
            limit: Maximum number of relationships to return

        Returns:
            List of relationship dictionaries with keys:
                - from_chunk: Source chunk ID
                - to_chunk: Target chunk ID
                - relationship_type: Type of relationship
                - weight: Relationship weight (default 1.0)

        """
        ...


class GraphCacheConfig:
    """Configuration for relationship graph caching.

    Attributes:
        rebuild_interval: Number of retrievals before rebuilding graph
        max_edges: Maximum edges to include in cached graph
        cache_enabled: Whether caching is enabled (True by default)
        ttl_seconds: Optional time-to-live in seconds (None = no expiry)

    """

    def __init__(
        self,
        rebuild_interval: int = 100,
        max_edges: int = 1000,
        cache_enabled: bool = True,
        ttl_seconds: int | None = None,
    ):
        """Initialize graph cache configuration.

        Args:
            rebuild_interval: Retrievals before rebuild (default 100)
            max_edges: Maximum edges in cache (default 1000)
            cache_enabled: Enable/disable caching (default True)
            ttl_seconds: Cache TTL in seconds (None = no expiry)

        """
        self.rebuild_interval = rebuild_interval
        self.max_edges = max_edges
        self.cache_enabled = cache_enabled
        self.ttl_seconds = ttl_seconds


class RelationshipGraphCache:
    """Thread-safe cache for relationship graphs.

    This cache maintains a pre-built RelationshipGraph to avoid repeated
    database queries during spreading activation calculations.

    The cache automatically:
    - Rebuilds after N retrievals (configurable)
    - Limits graph size to prevent memory issues
    - Expires after TTL (if configured)
    - Handles concurrent access safely

    Examples:
        >>> cache = RelationshipGraphCache(provider, config)
        >>> graph = cache.get_graph()  # First call builds
        >>> graph = cache.get_graph()  # Subsequent calls reuse
        >>> # After 100 retrievals, automatically rebuilds
        >>> graph = cache.get_graph()

    """

    def __init__(self, provider: RelationshipProvider, config: GraphCacheConfig | None = None):
        """Initialize the graph cache.

        Args:
            provider: Object that provides relationship data
            config: Cache configuration (uses defaults if None)

        """
        self.provider = provider
        self.config = config or GraphCacheConfig()

        # Cache state
        self._graph: RelationshipGraph | None = None
        self._retrieval_count = 0
        self._build_time: datetime | None = None
        self._lock = threading.RLock()

        # Statistics
        self._cache_hits = 0
        self._cache_misses = 0
        self._rebuilds = 0

    def get_graph(self) -> RelationshipGraph:
        """Get the cached relationship graph.

        Returns a cached graph if valid, otherwise rebuilds and caches.

        Returns:
            RelationshipGraph instance

        Thread-safe: Multiple threads can safely call this method.

        """
        with self._lock:
            # Check if cache is disabled
            if not self.config.cache_enabled:
                self._cache_misses += 1
                return self._build_graph()

            # Check if we need to rebuild
            if self._should_rebuild():
                self._cache_misses += 1
                self._graph = self._build_graph()
                self._build_time = datetime.now(timezone.utc)
                self._retrieval_count = 0
                self._rebuilds += 1
            else:
                self._cache_hits += 1

            # Increment retrieval count
            self._retrieval_count += 1

            assert self._graph is not None, "Graph should be built by this point"
            return self._graph

    def _should_rebuild(self) -> bool:
        """Determine if the cache should be rebuilt.

        Returns:
            True if rebuild is needed, False otherwise

        """
        # No graph exists
        if self._graph is None:
            return True

        # Exceeded retrieval interval
        if self._retrieval_count >= self.config.rebuild_interval:
            return True

        # TTL expired
        if self.config.ttl_seconds is not None and self._build_time is not None:
            age_seconds = (datetime.now(timezone.utc) - self._build_time).total_seconds()
            if age_seconds >= self.config.ttl_seconds:
                return True

        return False

    def _build_graph(self) -> RelationshipGraph:
        """Build a new relationship graph from the provider.

        Returns:
            Newly constructed RelationshipGraph

        Notes:
            - Limited to max_edges relationships
            - Most recent relationships prioritized if limit exceeded

        """
        graph = RelationshipGraph()

        # Get relationships from provider
        relationships = self.provider.get_all_relationships(limit=self.config.max_edges)

        # Add to graph
        for rel in relationships:
            from_chunk = rel.get("from_chunk")
            to_chunk = rel.get("to_chunk")
            if from_chunk is not None and to_chunk is not None:
                graph.add_relationship(
                    from_chunk=from_chunk,
                    to_chunk=to_chunk,
                    rel_type=rel.get("relationship_type", "unknown"),
                    weight=rel.get("weight", 1.0),
                )

        return graph

    def invalidate(self) -> None:
        """Invalidate the cache, forcing a rebuild on next access.

        Thread-safe: Can be called from any thread.
        """
        with self._lock:
            self._graph = None
            self._retrieval_count = 0
            self._build_time = None

    def force_rebuild(self) -> RelationshipGraph:
        """Force an immediate cache rebuild.

        Returns:
            Newly built RelationshipGraph

        Thread-safe: Can be called from any thread.

        """
        with self._lock:
            self.invalidate()
            return self.get_graph()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache performance metrics:
                - cache_hits: Number of cache hits
                - cache_misses: Number of cache misses
                - hit_rate: Cache hit rate (0.0 to 1.0)
                - rebuilds: Total number of rebuilds
                - retrieval_count: Retrievals since last rebuild
                - build_time: When cache was last built
                - edge_count: Number of edges in cached graph
                - chunk_count: Number of chunks in cached graph

        """
        with self._lock:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0

            return {
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "hit_rate": hit_rate,
                "rebuilds": self._rebuilds,
                "retrieval_count": self._retrieval_count,
                "build_time": self._build_time.isoformat() if self._build_time else None,
                "edge_count": self._graph.edge_count() if self._graph else 0,
                "chunk_count": self._graph.chunk_count() if self._graph else 0,
            }

    def reset_stats(self) -> None:
        """Reset cache statistics counters.

        Thread-safe: Can be called from any thread.
        """
        with self._lock:
            self._cache_hits = 0
            self._cache_misses = 0
            self._rebuilds = 0


class CachedSpreadingActivation:
    """Spreading activation calculator with integrated graph caching.

    This class wraps SpreadingActivation with automatic graph caching,
    providing better performance for repeated calculations.

    Examples:
        >>> from aurora_core.activation.spreading import SpreadingActivation
        >>>
        >>> spreading_calc = SpreadingActivation()
        >>> cached_calc = CachedSpreadingActivation(
        ...     provider=my_store,
        ...     spreading_activation=spreading_calc
        ... )
        >>>
        >>> # First call builds graph
        >>> result1 = cached_calc.calculate(['chunk_a'])
        >>>
        >>> # Subsequent calls reuse cached graph
        >>> result2 = cached_calc.calculate(['chunk_b'])

    """

    def __init__(
        self,
        provider: RelationshipProvider,
        spreading_activation: "SpreadingActivation",
        cache_config: GraphCacheConfig | None = None,
    ):
        """Initialize cached spreading activation.

        Args:
            provider: Object that provides relationship data
            spreading_activation: SpreadingActivation calculator instance
            cache_config: Cache configuration (uses defaults if None)

        """
        self.spreading_activation = spreading_activation
        self.cache = RelationshipGraphCache(provider, cache_config)

    def calculate(
        self,
        source_chunks: list[ChunkID],
        bidirectional: bool = True,
    ) -> dict[str, float]:
        """Calculate spreading activation with caching.

        Args:
            source_chunks: List of chunk IDs to spread from
            bidirectional: Spread along both incoming/outgoing edges

        Returns:
            Dictionary mapping chunk_id -> spreading_activation_score

        """
        graph = self.cache.get_graph()
        # Convert ChunkIDs to strings for spreading calculation
        source_chunk_strs: list[str] = [str(chunk_id) for chunk_id in source_chunks]
        result: dict[str, float] = self.spreading_activation.calculate(
            source_chunks=source_chunk_strs,
            graph=graph,
            bidirectional=bidirectional,
        )
        return result

    def get_related_chunks(
        self,
        source_chunks: list[ChunkID],
        min_activation: float = 0.0,
        bidirectional: bool = True,
    ) -> list[tuple[str, float]]:
        """Get related chunks sorted by spreading activation.

        Args:
            source_chunks: List of chunk IDs to spread from
            min_activation: Minimum activation threshold
            bidirectional: Spread along both directions

        Returns:
            List of (chunk_id, activation) tuples, sorted descending

        """
        graph = self.cache.get_graph()
        # Convert ChunkIDs to strings for spreading calculation
        source_chunk_strs: list[str] = [str(chunk_id) for chunk_id in source_chunks]
        result: list[tuple[str, float]] = self.spreading_activation.get_related_chunks(
            source_chunks=source_chunk_strs,
            graph=graph,
            min_activation=min_activation,
            bidirectional=bidirectional,
        )
        return result

    def invalidate_cache(self) -> None:
        """Invalidate the relationship graph cache."""
        self.cache.invalidate()

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache performance statistics.

        Returns:
            Dictionary with cache metrics

        """
        return self.cache.get_stats()


__all__ = [
    "RelationshipProvider",
    "GraphCacheConfig",
    "RelationshipGraphCache",
    "CachedSpreadingActivation",
]
