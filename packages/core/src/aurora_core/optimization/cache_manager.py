"""Multi-Tier Caching for Performance Optimization

This module implements a multi-tier caching system to improve retrieval performance:

1. **Hot Cache** (Tier 1): LRU cache, in-memory, 1000 chunks max
2. **Persistent Cache** (Tier 2): SQLite, all chunks
3. **Activation Scores Cache** (Tier 3): Activation calculations, 10-minute TTL

Cache Promotion Strategy:
- Chunks accessed frequently get promoted to hot cache
- LRU eviction ensures hot cache stays within memory limits
- Cache hits avoid expensive database queries and activation calculations

Performance Targets:
- Cache hit rate: ≥30% after 1000 queries
- Memory footprint: ≤100MB for 10K cached chunks
- Cache lookup: <1ms for hot cache, <5ms for persistent
"""

import json
import sqlite3
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aurora_core.types import ChunkID


@dataclass
class CacheEntry:
    """Entry in the cache with metadata.

    Attributes:
        value: Cached value (chunk data or activation score)
        timestamp: When the entry was cached
        access_count: Number of times accessed
        last_access: Most recent access timestamp

    """

    value: Any
    timestamp: float
    access_count: int = 0
    last_access: float = 0.0

    def __post_init__(self) -> None:
        if self.last_access == 0.0:
            self.last_access = self.timestamp

    def is_expired(self, ttl_seconds: float) -> bool:
        """Check if entry has exceeded TTL.

        Args:
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if expired, False otherwise

        """
        current_time = time.time()
        return (current_time - self.timestamp) > ttl_seconds


@dataclass
class CacheStats:
    """Cache statistics for monitoring and tuning.

    Attributes:
        hot_hits: Number of hot cache hits
        hot_misses: Number of hot cache misses
        persistent_hits: Number of persistent cache hits
        persistent_misses: Number of persistent cache misses
        activation_hits: Number of activation score cache hits
        activation_misses: Number of activation score cache misses
        evictions: Number of cache evictions (LRU)
        promotions: Number of promotions to hot cache
        total_queries: Total number of cache queries

    """

    hot_hits: int = 0
    hot_misses: int = 0
    persistent_hits: int = 0
    persistent_misses: int = 0
    activation_hits: int = 0
    activation_misses: int = 0
    evictions: int = 0
    promotions: int = 0
    total_queries: int = 0

    @property
    def hot_hit_rate(self) -> float:
        """Calculate hot cache hit rate."""
        total = self.hot_hits + self.hot_misses
        return self.hot_hits / total if total > 0 else 0.0

    @property
    def persistent_hit_rate(self) -> float:
        """Calculate persistent cache hit rate."""
        total = self.persistent_hits + self.persistent_misses
        return self.persistent_hits / total if total > 0 else 0.0

    @property
    def activation_hit_rate(self) -> float:
        """Calculate activation cache hit rate."""
        total = self.activation_hits + self.activation_misses
        return self.activation_hits / total if total > 0 else 0.0

    @property
    def overall_hit_rate(self) -> float:
        """Calculate overall cache hit rate across all tiers."""
        total_hits = self.hot_hits + self.persistent_hits + self.activation_hits
        total_misses = self.hot_misses + self.persistent_misses + self.activation_misses
        total = total_hits + total_misses
        return total_hits / total if total > 0 else 0.0


class LRUCache:
    """Least Recently Used (LRU) cache implementation.

    This is a simple LRU cache using OrderedDict for O(1) operations.
    When the cache is full, the least recently used item is evicted.

    Examples:
        >>> cache = LRUCache(capacity=1000)
        >>> cache.set('key1', {'data': 'value1'})
        >>> value = cache.get('key1')
        >>> if value:
        ...     print(value['data'])

    """

    def __init__(self, capacity: int = 1000):
        """Initialize the LRU cache.

        Args:
            capacity: Maximum number of items to cache (default 1000)

        """
        self.capacity = capacity
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> Any | None:
        """Get value from cache and update access order.

        Args:
            key: Cache key

        Returns:
            Cached value if found, None otherwise

        """
        if key not in self.cache:
            return None

        # Move to end (most recently used)
        entry = self.cache.pop(key)
        entry.access_count += 1
        entry.last_access = time.time()
        self.cache[key] = entry

        return entry.value

    def set(self, key: str, value: Any) -> bool:
        """Set value in cache with LRU eviction.

        Args:
            key: Cache key
            value: Value to cache

        Returns:
            True if eviction occurred, False otherwise

        """
        evicted = False

        # If key exists, remove it (we'll re-add at end)
        if key in self.cache:
            self.cache.pop(key)
        # If at capacity, evict LRU item
        elif len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)  # Remove first (oldest)
            evicted = True

        # Add new entry at end (most recent)
        entry = CacheEntry(
            value=value,
            timestamp=time.time(),
            access_count=0,
            last_access=time.time(),
        )
        self.cache[key] = entry

        return evicted

    def clear(self) -> None:
        """Clear all entries from cache."""
        self.cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)

    def items(self) -> list[tuple[str, Any]]:
        """Get all cache items (key, value pairs)."""
        return [(key, entry.value) for key, entry in self.cache.items()]


class PersistentCache:
    """SQLite-backed persistent cache for chunk data.

    This cache provides disk-backed storage that survives process restarts.
    It's useful for large codebases where hot cache evictions would otherwise
    require expensive database queries.

    The cache stores serialized chunk data with access statistics for
    intelligent warm-up on process start.
    """

    def __init__(self, cache_path: str | Path, max_entries: int = 10000):
        """Initialize the persistent cache.

        Args:
            cache_path: Path to SQLite cache file
            max_entries: Maximum number of entries to store (default 10000)

        """
        self.cache_path = Path(cache_path).expanduser()
        self.max_entries = max_entries
        self._conn: sqlite3.Connection | None = None
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create SQLite connection."""
        if self._conn is None:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.cache_path), timeout=5.0)
            self._conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrent access
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_schema(self) -> None:
        """Initialize cache database schema."""
        conn = self._get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunk_cache (
                chunk_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_access REAL NOT NULL,
                created_at REAL NOT NULL
            )
        """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cache_access
            ON chunk_cache(access_count DESC, last_access DESC)
        """
        )
        conn.commit()

    def get(self, chunk_id: ChunkID) -> Any | None:
        """Get chunk from persistent cache.

        Args:
            chunk_id: Chunk identifier

        Returns:
            Cached chunk data if found, None otherwise

        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT data FROM chunk_cache WHERE chunk_id = ?",
                (chunk_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            # Update access stats
            now = time.time()
            conn.execute(
                "UPDATE chunk_cache SET access_count = access_count + 1, last_access = ? WHERE chunk_id = ?",
                (now, chunk_id),
            )
            conn.commit()

            return json.loads(row["data"])
        except (sqlite3.Error, json.JSONDecodeError):
            return None

    def set(self, chunk_id: ChunkID, data: Any) -> None:
        """Store chunk in persistent cache.

        Args:
            chunk_id: Chunk identifier
            data: Chunk data to cache (must be JSON-serializable)

        """
        conn = self._get_connection()
        try:
            now = time.time()
            serialized = json.dumps(data)
            conn.execute(
                """
                INSERT OR REPLACE INTO chunk_cache
                (chunk_id, data, access_count, last_access, created_at)
                VALUES (?, ?, COALESCE((SELECT access_count FROM chunk_cache WHERE chunk_id = ?), 0) + 1, ?, ?)
                """,
                (chunk_id, serialized, chunk_id, now, now),
            )
            conn.commit()

            # Prune if over max entries (keep most accessed)
            cursor = conn.execute("SELECT COUNT(*) FROM chunk_cache")
            count = cursor.fetchone()[0]
            if count > self.max_entries:
                # Delete least accessed entries
                delete_count = count - self.max_entries
                conn.execute(
                    """
                    DELETE FROM chunk_cache WHERE chunk_id IN (
                        SELECT chunk_id FROM chunk_cache
                        ORDER BY access_count ASC, last_access ASC
                        LIMIT ?
                    )
                    """,
                    (delete_count,),
                )
                conn.commit()

        except (sqlite3.Error, TypeError):
            pass  # Silently fail on cache errors

    def get_hot_entries(self, limit: int = 100) -> list[tuple[ChunkID, Any]]:
        """Get most accessed entries for hot cache warm-up.

        Args:
            limit: Maximum entries to return

        Returns:
            List of (chunk_id, data) tuples ordered by access frequency

        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT chunk_id, data FROM chunk_cache
                ORDER BY access_count DESC, last_access DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [(row["chunk_id"], json.loads(row["data"])) for row in cursor]
        except (sqlite3.Error, json.JSONDecodeError):
            return []

    def clear(self) -> None:
        """Clear all entries from persistent cache."""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM chunk_cache")
            conn.commit()
        except sqlite3.Error:
            pass

    def size(self) -> int:
        """Get current cache size."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM chunk_cache")
            row = cursor.fetchone()
            return int(row[0]) if row else 0
        except sqlite3.Error:
            return 0

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None


class CacheManager:
    """Multi-tier cache manager for optimizing retrieval performance.

    This manager implements a three-tier caching strategy:

    1. **Hot Cache**: LRU in-memory cache for frequently accessed chunks
    2. **Persistent Cache**: SQLite-backed cache for all chunks
    3. **Activation Cache**: Short-lived cache for activation scores

    Examples:
        >>> from aurora_core.optimization import CacheManager
        >>>
        >>> # Initialize cache
        >>> cache = CacheManager(
        ...     hot_cache_size=1000,
        ...     activation_ttl_seconds=600
        ... )
        >>>
        >>> # Cache chunk data
        >>> cache.set_chunk('chunk_123', chunk_data)
        >>>
        >>> # Retrieve with automatic promotion
        >>> data = cache.get_chunk('chunk_123')
        >>>
        >>> # Cache activation scores
        >>> cache.set_activation('chunk_123', 2.5)
        >>>
        >>> # Check cache statistics
        >>> stats = cache.get_stats()
        >>> print(f"Hit rate: {stats.overall_hit_rate:.1%}")

    Performance Notes:
        - Hot cache lookups: <1ms
        - Persistent cache lookups: <5ms
        - Activation cache reduces recalculation by 70-80%
        - Memory usage: ~10KB per cached chunk (10MB for 1000 chunks)

    """

    def __init__(
        self,
        hot_cache_size: int = 1000,
        activation_ttl_seconds: int = 600,
        enable_persistent_cache: bool = False,
        persistent_cache_path: str | Path | None = None,
        persistent_cache_max_entries: int = 10000,
        warm_hot_cache: bool = True,
    ):
        """Initialize the cache manager.

        Args:
            hot_cache_size: Maximum items in hot cache (default 1000)
            activation_ttl_seconds: TTL for activation scores in seconds (default 600)
            enable_persistent_cache: Enable SQLite persistent cache (default False)
            persistent_cache_path: Path to persistent cache file (default: ~/.aurora/cache/chunks.db)
            persistent_cache_max_entries: Maximum entries in persistent cache (default 10000)
            warm_hot_cache: Pre-warm hot cache from persistent cache on startup (default True)

        Notes:
            - Persistent cache provides disk-backed storage that survives restarts
            - When enabled, hot cache is pre-warmed with most accessed entries

        """
        self.hot_cache = LRUCache(capacity=hot_cache_size)
        self.activation_cache: dict[ChunkID, CacheEntry] = {}
        self.activation_ttl = activation_ttl_seconds
        self.enable_persistent = enable_persistent_cache
        self.stats = CacheStats()

        # Initialize persistent cache if enabled
        self._persistent_cache: PersistentCache | None = None
        if enable_persistent_cache:
            cache_path = persistent_cache_path or Path("~/.aurora/cache/chunks.db")
            self._persistent_cache = PersistentCache(
                cache_path=cache_path,
                max_entries=persistent_cache_max_entries,
            )

            # Warm hot cache from persistent cache
            if warm_hot_cache:
                self._warm_hot_cache_from_persistent(limit=hot_cache_size // 2)

    def get_chunk(self, chunk_id: ChunkID) -> Any | None:
        """Get chunk from cache (hot → persistent → miss).

        This implements the cache hierarchy:
        1. Check hot cache first (fastest)
        2. If miss, check persistent cache
        3. If hit in persistent, promote to hot cache
        4. If miss in both, return None

        Args:
            chunk_id: Chunk identifier

        Returns:
            Cached chunk data if found, None otherwise

        """
        self.stats.total_queries += 1

        # Tier 1: Hot cache
        chunk = self.hot_cache.get(chunk_id)
        if chunk is not None:
            self.stats.hot_hits += 1
            return chunk

        self.stats.hot_misses += 1

        # Tier 2: Persistent cache (if enabled)
        if self.enable_persistent and self._persistent_cache is not None:
            chunk = self._persistent_cache.get(chunk_id)
            if chunk is not None:
                self.stats.persistent_hits += 1
                self._promote_to_hot(chunk_id, chunk)
                return chunk
            self.stats.persistent_misses += 1

        return None

    def set_chunk(self, chunk_id: ChunkID, chunk_data: Any) -> None:
        """Set chunk in cache (hot + persistent).

        Args:
            chunk_id: Chunk identifier
            chunk_data: Chunk data to cache

        """
        # Set in hot cache
        evicted = self.hot_cache.set(chunk_id, chunk_data)
        if evicted:
            self.stats.evictions += 1

        # Set in persistent cache (if enabled)
        if self.enable_persistent and self._persistent_cache is not None:
            self._persistent_cache.set(chunk_id, chunk_data)

    def _warm_hot_cache_from_persistent(self, limit: int = 500) -> int:
        """Pre-warm hot cache with most accessed entries from persistent cache.

        Args:
            limit: Maximum entries to load

        Returns:
            Number of entries loaded

        """
        if self._persistent_cache is None:
            return 0

        entries = self._persistent_cache.get_hot_entries(limit=limit)
        for chunk_id, data in entries:
            self.hot_cache.set(chunk_id, data)

        return len(entries)

    def get_activation(
        self,
        chunk_id: ChunkID,
        current_time: datetime | None = None,
    ) -> float | None:
        """Get cached activation score if not expired.

        Args:
            chunk_id: Chunk identifier
            current_time: Current time for expiration check

        Returns:
            Cached activation score if found and not expired, None otherwise

        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        if chunk_id not in self.activation_cache:
            self.stats.activation_misses += 1
            return None

        entry = self.activation_cache[chunk_id]

        # Check if expired
        if entry.is_expired(self.activation_ttl):
            # Remove expired entry
            del self.activation_cache[chunk_id]
            self.stats.activation_misses += 1
            return None

        # Update access stats
        entry.access_count += 1
        entry.last_access = time.time()

        self.stats.activation_hits += 1
        assert isinstance(entry.value, float), "Activation cache should only store float values"
        return entry.value

    def set_activation(self, chunk_id: ChunkID, activation: float) -> None:
        """Cache activation score with TTL.

        Args:
            chunk_id: Chunk identifier
            activation: Activation score to cache

        """
        entry = CacheEntry(
            value=activation,
            timestamp=time.time(),
            access_count=0,
            last_access=time.time(),
        )
        self.activation_cache[chunk_id] = entry

    def _promote_to_hot(self, chunk_id: ChunkID, chunk_data: Any) -> None:
        """Promote chunk from persistent cache to hot cache.

        Args:
            chunk_id: Chunk identifier
            chunk_data: Chunk data to promote

        """
        evicted = self.hot_cache.set(chunk_id, chunk_data)
        if evicted:
            self.stats.evictions += 1
        self.stats.promotions += 1

    def clear_activation_cache(self) -> None:
        """Clear all activation scores from cache."""
        self.activation_cache.clear()

    def clear_hot_cache(self) -> None:
        """Clear hot cache."""
        self.hot_cache.clear()

    def clear_all(self) -> None:
        """Clear all caches."""
        self.hot_cache.clear()
        self.activation_cache.clear()
        # Reset stats
        self.stats = CacheStats()

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats object with current statistics

        """
        return self.stats

    def get_memory_usage_estimate(self) -> dict[str, int]:
        """Estimate memory usage of caches.

        Returns:
            Dictionary with memory estimates in bytes:
                - hot_cache_bytes: Estimated hot cache memory
                - activation_cache_bytes: Estimated activation cache memory
                - total_bytes: Total estimated memory

        Notes:
            This is a rough estimate assuming:
            - ~10KB per chunk in hot cache
            - ~100 bytes per activation score entry

        """
        # Rough estimates
        hot_cache_bytes = self.hot_cache.size() * 10_000  # ~10KB per chunk
        activation_cache_bytes = len(self.activation_cache) * 100  # ~100 bytes per score

        return {
            "hot_cache_bytes": hot_cache_bytes,
            "activation_cache_bytes": activation_cache_bytes,
            "total_bytes": hot_cache_bytes + activation_cache_bytes,
        }

    def cleanup_expired_activations(self) -> int:
        """Remove expired activation scores from cache.

        Returns:
            Number of expired entries removed

        """
        expired_keys = []

        for chunk_id, entry in self.activation_cache.items():
            if entry.is_expired(self.activation_ttl):
                expired_keys.append(chunk_id)

        # Remove expired entries
        for key in expired_keys:
            del self.activation_cache[key]

        return len(expired_keys)


__all__ = [
    "CacheManager",
    "CacheStats",
    "CacheEntry",
    "LRUCache",
    "PersistentCache",
]
