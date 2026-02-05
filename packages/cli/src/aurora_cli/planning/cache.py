"""Plan decomposition caching layer.

This module provides a specialized caching system for plan decomposition results
to avoid redundant LLM calls and expensive SOAR operations.

Cache Strategy:
- LRU eviction with configurable capacity (default: 100 decompositions)
- TTL-based expiration (default: 24 hours)
- Hash-based keys incorporating goal, complexity, and context files
- Optional persistent storage via SQLite

Performance Targets:
- Cache hit rate: ≥40% for typical workflows
- Memory footprint: ≤5MB for 100 cached decompositions
- Cache lookup: <1ms

Observability:
- Detailed metrics for hit/miss rates, latency, and evictions
- Structured logging for cache operations
- Performance tracking per cache key
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aurora_cli.planning.models import Complexity, Subgoal


# Configure logger for cache operations
logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Cache performance metrics for observability.

    Tracks detailed statistics about cache operations for monitoring
    and optimization purposes.
    """

    hits: int = 0
    misses: int = 0
    expired_hits: int = 0  # Hits that were expired
    persistent_hits: int = 0  # Hits from persistent storage
    memory_hits: int = 0  # Hits from in-memory cache
    evictions: int = 0
    write_operations: int = 0
    total_get_latency_ms: float = 0.0
    total_set_latency_ms: float = 0.0
    max_get_latency_ms: float = 0.0
    max_set_latency_ms: float = 0.0

    def record_hit(self, latency_ms: float, source: str) -> None:
        """Record a cache hit with latency tracking.

        Args:
            latency_ms: Operation latency in milliseconds
            source: Hit source ("memory" or "persistent")

        """
        self.hits += 1
        self.total_get_latency_ms += latency_ms
        self.max_get_latency_ms = max(self.max_get_latency_ms, latency_ms)

        if source == "memory":
            self.memory_hits += 1
        elif source == "persistent":
            self.persistent_hits += 1

    def record_miss(self, latency_ms: float) -> None:
        """Record a cache miss with latency tracking.

        Args:
            latency_ms: Operation latency in milliseconds

        """
        self.misses += 1
        self.total_get_latency_ms += latency_ms
        self.max_get_latency_ms = max(self.max_get_latency_ms, latency_ms)

    def record_expired(self) -> None:
        """Record an expired cache entry."""
        self.expired_hits += 1

    def record_eviction(self) -> None:
        """Record a cache eviction."""
        self.evictions += 1

    def record_write(self, latency_ms: float) -> None:
        """Record a cache write operation.

        Args:
            latency_ms: Operation latency in milliseconds

        """
        self.write_operations += 1
        self.total_set_latency_ms += latency_ms
        self.max_set_latency_ms = max(self.max_set_latency_ms, latency_ms)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate (0.0-1.0)."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def avg_get_latency_ms(self) -> float:
        """Calculate average GET operation latency."""
        total_gets = self.hits + self.misses
        return self.total_get_latency_ms / total_gets if total_gets > 0 else 0.0

    @property
    def avg_set_latency_ms(self) -> float:
        """Calculate average SET operation latency."""
        return (
            self.total_set_latency_ms / self.write_operations if self.write_operations > 0 else 0.0
        )


@dataclass
class DecompositionCacheEntry:
    """Cached decomposition result with metadata.

    Attributes:
        subgoals: List of decomposed subgoals
        source: Decomposition source ("soar" or "heuristic")
        timestamp: Unix timestamp when cached
        access_count: Number of times accessed
        last_access: Unix timestamp of last access
        goal_hash: Hash of the goal for verification

    """

    subgoals: list[dict[str, Any]]  # Serialized Subgoal objects
    source: str
    timestamp: float
    access_count: int
    last_access: float
    goal_hash: str

    def is_expired(self, ttl_seconds: float) -> bool:
        """Check if entry has exceeded TTL.

        Args:
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if expired, False otherwise

        """
        current_time = time.time()
        return (current_time - self.timestamp) > ttl_seconds


class PlanDecompositionCache:
    """LRU + TTL cache for plan decomposition results.

    This cache uses:
    1. In-memory LRU cache for fast lookups
    2. TTL-based expiration to handle stale results
    3. Optional SQLite persistence for cross-session caching

    Examples:
        >>> cache = PlanDecompositionCache(capacity=100, ttl_hours=24)
        >>> cache.set("Add auth", Complexity.MODERATE, subgoals, "soar")
        >>> result = cache.get("Add auth", Complexity.MODERATE)
        >>> if result:
        ...     subgoals, source = result

    """

    def __init__(
        self,
        capacity: int = 100,
        ttl_hours: int = 24,
        persistent_path: Path | None = None,
        enable_metrics: bool = True,
    ):
        """Initialize plan decomposition cache.

        Args:
            capacity: Maximum number of decompositions to cache (default: 100)
            ttl_hours: Time-to-live for cache entries in hours (default: 24)
            persistent_path: Optional path to SQLite database for persistence
            enable_metrics: Enable detailed metrics tracking (default: True)

        """
        self.capacity = capacity
        self.ttl_seconds = ttl_hours * 3600
        self.persistent_path = persistent_path
        self.enable_metrics = enable_metrics

        # In-memory LRU cache
        self._cache: OrderedDict[str, DecompositionCacheEntry] = OrderedDict()

        # Metrics tracking
        self._metrics = CacheMetrics()

        # Legacy statistics (deprecated, kept for backwards compatibility)
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Initialize persistent storage if path provided
        if persistent_path:
            self._init_persistent_storage()
            logger.info(
                "Cache initialized",
                extra={
                    "capacity": capacity,
                    "ttl_hours": ttl_hours,
                    "persistent_enabled": True,
                    "persistent_path": str(persistent_path),
                },
            )

    def get(
        self,
        goal: str,
        complexity: Complexity,
        context_files: list[str] | None = None,
    ) -> tuple[list[Subgoal], str] | None:
        """Get cached decomposition result.

        Args:
            goal: The goal string
            complexity: Complexity level
            context_files: Optional list of context file paths

        Returns:
            Tuple of (subgoals, source) if cache hit, None otherwise

        """
        start_time = time.perf_counter()
        cache_key = self._compute_cache_key(goal, complexity, context_files)

        logger.debug(
            "Cache GET operation",
            extra={
                "cache_key": cache_key[:16],
                "goal_preview": goal[:50],
                "complexity": complexity.value,
            },
        )

        # Try in-memory cache first
        if cache_key in self._cache:
            entry = self._cache[cache_key]

            # Check expiration
            if entry.is_expired(self.ttl_seconds):
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                # Remove expired entry
                self._cache.pop(cache_key)
                self._misses += 1
                if self.enable_metrics:
                    self._metrics.record_expired()
                    self._metrics.record_miss(elapsed_ms)

                logger.debug(
                    "Cache MISS - expired",
                    extra={
                        "cache_key": cache_key[:16],
                        "age_hours": (time.time() - entry.timestamp) / 3600,
                        "latency_ms": elapsed_ms,
                    },
                )
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            entry.access_count += 1
            entry.last_access = time.time()

            # Deserialize subgoals
            subgoals = [self._deserialize_subgoal(sg) for sg in entry.subgoals]

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._hits += 1
            if self.enable_metrics:
                self._metrics.record_hit(elapsed_ms, "memory")

            logger.info(
                "Cache HIT - memory",
                extra={
                    "cache_key": cache_key[:16],
                    "source": entry.source,
                    "age_hours": (time.time() - entry.timestamp) / 3600,
                    "access_count": entry.access_count,
                    "latency_ms": elapsed_ms,
                    "subgoal_count": len(subgoals),
                },
            )

            return (subgoals, entry.source)

        # Try persistent storage if enabled
        if self.persistent_path:
            result = self._get_from_persistent(cache_key)
            if result:
                # Promote to in-memory cache
                subgoals, source = result
                self._set_in_memory(cache_key, goal, subgoals, source)

                elapsed_ms = (time.perf_counter() - start_time) * 1000
                self._hits += 1
                if self.enable_metrics:
                    self._metrics.record_hit(elapsed_ms, "persistent")

                logger.info(
                    "Cache HIT - persistent",
                    extra={
                        "cache_key": cache_key[:16],
                        "source": source,
                        "latency_ms": elapsed_ms,
                        "subgoal_count": len(subgoals),
                    },
                )
                return result

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._misses += 1
        if self.enable_metrics:
            self._metrics.record_miss(elapsed_ms)

        logger.info(
            "Cache MISS",
            extra={
                "cache_key": cache_key[:16],
                "goal_preview": goal[:50],
                "complexity": complexity.value,
                "latency_ms": elapsed_ms,
            },
        )

        return None

    def set(
        self,
        goal: str,
        complexity: Complexity,
        subgoals: list[Subgoal],
        source: str,
        context_files: list[str] | None = None,
    ) -> None:
        """Cache decomposition result.

        Args:
            goal: The goal string
            complexity: Complexity level
            subgoals: List of decomposed subgoals
            source: Decomposition source ("soar" or "heuristic")
            context_files: Optional list of context file paths

        """
        start_time = time.perf_counter()
        cache_key = self._compute_cache_key(goal, complexity, context_files)

        logger.debug(
            "Cache SET operation",
            extra={
                "cache_key": cache_key[:16],
                "goal_preview": goal[:50],
                "complexity": complexity.value,
                "source": source,
                "subgoal_count": len(subgoals),
            },
        )

        # Set in memory cache
        self._set_in_memory(cache_key, goal, subgoals, source)

        # Set in persistent storage if enabled
        if self.persistent_path:
            self._set_in_persistent(cache_key, goal, subgoals, source)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        if self.enable_metrics:
            self._metrics.record_write(elapsed_ms)

        logger.info(
            "Cache SET complete",
            extra={
                "cache_key": cache_key[:16],
                "source": source,
                "latency_ms": elapsed_ms,
                "cache_size": len(self._cache),
                "capacity": self.capacity,
            },
        )

    def _set_in_memory(
        self,
        cache_key: str,
        goal: str,
        subgoals: list[Subgoal],
        source: str,
    ) -> None:
        """Set entry in in-memory cache with LRU eviction.

        Args:
            cache_key: Cache key
            goal: Original goal for hash verification
            subgoals: List of subgoals
            source: Decomposition source

        """
        # Evict LRU if at capacity
        if cache_key not in self._cache and len(self._cache) >= self.capacity:
            evicted_key, evicted_entry = self._cache.popitem(last=False)
            self._evictions += 1
            if self.enable_metrics:
                self._metrics.record_eviction()

            logger.debug(
                "Cache eviction - LRU",
                extra={
                    "evicted_key": evicted_key[:16],
                    "evicted_source": evicted_entry.source,
                    "evicted_age_hours": (time.time() - evicted_entry.timestamp) / 3600,
                    "access_count": evicted_entry.access_count,
                },
            )

        # Remove if exists (will re-add at end)
        if cache_key in self._cache:
            self._cache.pop(cache_key)

        # Create entry with serialized subgoals
        entry = DecompositionCacheEntry(
            subgoals=[self._serialize_subgoal(sg) for sg in subgoals],
            source=source,
            timestamp=time.time(),
            access_count=0,
            last_access=time.time(),
            goal_hash=self._hash_string(goal),
        )

        # Add at end (most recent)
        self._cache[cache_key] = entry

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        if self.persistent_path and self.persistent_path.exists():
            try:
                conn = sqlite3.connect(self.persistent_path)
                conn.execute("DELETE FROM decomposition_cache")
                conn.commit()
                conn.close()
            except sqlite3.Error:
                pass

    def clear_hot_cache(self) -> None:
        """Clear only in-memory cache, preserving persistent storage."""
        self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics with comprehensive metrics.

        Returns:
            Dictionary with cache statistics including:
                - Basic counters: size, capacity, hits, misses, evictions
                - Performance: hit_rate, avg_get_latency_ms, avg_set_latency_ms
                - Detailed metrics: memory_hits, persistent_hits, expired_hits
                - Legacy fields for backwards compatibility

        """
        if self.enable_metrics:
            return {
                # Basic metrics
                "size": len(self._cache),
                "capacity": self.capacity,
                "hits": self._metrics.hits,
                "misses": self._metrics.misses,
                "hit_rate": self._metrics.hit_rate,
                "evictions": self._metrics.evictions,
                # Performance metrics
                "avg_get_latency_ms": round(self._metrics.avg_get_latency_ms, 3),
                "max_get_latency_ms": round(self._metrics.max_get_latency_ms, 3),
                "avg_set_latency_ms": round(self._metrics.avg_set_latency_ms, 3),
                "max_set_latency_ms": round(self._metrics.max_set_latency_ms, 3),
                # Detailed metrics
                "memory_hits": self._metrics.memory_hits,
                "persistent_hits": self._metrics.persistent_hits,
                "expired_hits": self._metrics.expired_hits,
                "write_operations": self._metrics.write_operations,
                # Derived metrics
                "memory_hit_rate": (
                    self._metrics.memory_hits / self._metrics.hits
                    if self._metrics.hits > 0
                    else 0.0
                ),
                "persistent_hit_rate": (
                    self._metrics.persistent_hits / self._metrics.hits
                    if self._metrics.hits > 0
                    else 0.0
                ),
                "total_operations": self._metrics.hits + self._metrics.misses,
            }
        # Legacy mode - minimal statistics
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "capacity": self.capacity,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "evictions": self._evictions,
        }

    def get_metrics(self) -> CacheMetrics:
        """Get detailed cache metrics object.

        Returns:
            CacheMetrics object with comprehensive statistics

        Raises:
            RuntimeError: If metrics are disabled

        """
        if not self.enable_metrics:
            raise RuntimeError("Metrics are disabled for this cache instance")
        return self._metrics

    def log_performance_summary(self) -> None:
        """Log comprehensive performance summary for monitoring."""
        stats = self.get_stats()

        logger.info(
            "Cache performance summary",
            extra={
                "cache_size": stats["size"],
                "capacity": stats["capacity"],
                "hit_rate": f"{stats['hit_rate']:.1%}",
                "total_operations": stats.get("total_operations", 0),
                **stats,
            },
        )

    def _compute_cache_key(
        self,
        goal: str,
        complexity: Complexity,
        context_files: list[str] | None = None,
    ) -> str:
        """Compute cache key from goal, complexity, and context files.

        Args:
            goal: The goal string
            complexity: Complexity level
            context_files: Optional list of context file paths

        Returns:
            Hash-based cache key (32 chars)

        """
        # Include context files in key to handle context-dependent decompositions
        context_key = ""
        if context_files:
            # Sort for consistent ordering
            sorted_files = sorted(context_files)
            context_key = "|".join(sorted_files)

        content = f"{goal}::{complexity.value}::{context_key}"
        return self._hash_string(content)[:32]

    def _hash_string(self, content: str) -> str:
        """Hash string using SHA256.

        Args:
            content: Content to hash

        Returns:
            Hex digest of SHA256 hash

        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _serialize_subgoal(self, subgoal: Subgoal) -> dict[str, Any]:
        """Serialize Subgoal to dictionary.

        Args:
            subgoal: Subgoal object (Pydantic BaseModel)

        Returns:
            Dictionary representation

        """
        return subgoal.model_dump()

    def _deserialize_subgoal(self, data: dict[str, Any]) -> Subgoal:
        """Deserialize dictionary to Subgoal.

        Args:
            data: Dictionary representation

        Returns:
            Subgoal object (Pydantic BaseModel)

        """
        return Subgoal.model_validate(data)

    def _init_persistent_storage(self) -> None:
        """Initialize SQLite persistent storage."""
        if not self.persistent_path:
            return

        try:
            # Ensure parent directory exists
            self.persistent_path.parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(self.persistent_path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decomposition_cache (
                    cache_key TEXT PRIMARY KEY,
                    goal_hash TEXT NOT NULL,
                    subgoals TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_access REAL NOT NULL
                )
                """,
            )
            # Index on timestamp for TTL cleanup
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON decomposition_cache(timestamp)
                """,
            )
            conn.commit()
            conn.close()
        except sqlite3.Error:
            # Silently fail if persistent storage can't be initialized
            # Cache will still work in-memory
            pass

    def _get_from_persistent(self, cache_key: str) -> tuple[list[Subgoal], str] | None:
        """Get entry from persistent storage.

        Args:
            cache_key: Cache key

        Returns:
            Tuple of (subgoals, source) if found and not expired, None otherwise

        """
        if not self.persistent_path or not self.persistent_path.exists():
            return None

        try:
            conn = sqlite3.connect(self.persistent_path)
            cursor = conn.execute(
                """
                SELECT subgoals, source, timestamp
                FROM decomposition_cache
                WHERE cache_key = ?
                """,
                (cache_key,),
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            subgoals_json, source, timestamp = row

            # Check expiration
            if (time.time() - timestamp) > self.ttl_seconds:
                # Remove expired entry
                self._remove_from_persistent(cache_key)
                return None

            # Deserialize subgoals
            subgoals_data = json.loads(subgoals_json)
            subgoals = [self._deserialize_subgoal(sg) for sg in subgoals_data]

            # Update access stats
            self._update_persistent_access(cache_key)

            return (subgoals, source)

        except (sqlite3.Error, json.JSONDecodeError):
            return None

    def _set_in_persistent(
        self,
        cache_key: str,
        goal: str,
        subgoals: list[Subgoal],
        source: str,
    ) -> None:
        """Set entry in persistent storage.

        Args:
            cache_key: Cache key
            goal: Original goal
            subgoals: List of subgoals
            source: Decomposition source

        """
        if not self.persistent_path:
            return

        try:
            # Serialize subgoals
            subgoals_json = json.dumps([self._serialize_subgoal(sg) for sg in subgoals])

            conn = sqlite3.connect(self.persistent_path)
            conn.execute(
                """
                INSERT OR REPLACE INTO decomposition_cache
                (cache_key, goal_hash, subgoals, source, timestamp, access_count, last_access)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    cache_key,
                    self._hash_string(goal),
                    subgoals_json,
                    source,
                    time.time(),
                    time.time(),
                ),
            )
            conn.commit()
            conn.close()
        except (sqlite3.Error, json.JSONDecodeError):
            pass

    def _update_persistent_access(self, cache_key: str) -> None:
        """Update access stats in persistent storage.

        Args:
            cache_key: Cache key

        """
        if not self.persistent_path or not self.persistent_path.exists():
            return

        try:
            conn = sqlite3.connect(self.persistent_path)
            conn.execute(
                """
                UPDATE decomposition_cache
                SET access_count = access_count + 1,
                    last_access = ?
                WHERE cache_key = ?
                """,
                (time.time(), cache_key),
            )
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

    def _remove_from_persistent(self, cache_key: str) -> None:
        """Remove entry from persistent storage.

        Args:
            cache_key: Cache key

        """
        if not self.persistent_path or not self.persistent_path.exists():
            return

        try:
            conn = sqlite3.connect(self.persistent_path)
            conn.execute("DELETE FROM decomposition_cache WHERE cache_key = ?", (cache_key,))
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

    def cleanup_expired(self) -> int:
        """Remove expired entries from persistent storage.

        Returns:
            Number of expired entries removed

        """
        if not self.persistent_path or not self.persistent_path.exists():
            return 0

        try:
            cutoff_time = time.time() - self.ttl_seconds

            conn = sqlite3.connect(self.persistent_path)
            cursor = conn.execute(
                "DELETE FROM decomposition_cache WHERE timestamp < ?",
                (cutoff_time,),
            )
            removed = cursor.rowcount
            conn.commit()
            conn.close()

            return removed
        except sqlite3.Error:
            return 0


__all__ = ["PlanDecompositionCache", "DecompositionCacheEntry", "CacheMetrics"]
