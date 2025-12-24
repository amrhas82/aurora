# AURORA API Contracts - v1.0.0-phase3

**Version**: 1.0.0-phase3
**Status**: Stable
**Effective Date**: December 23, 2025
**Revision Policy**: Major versions only (breaking changes require v2.0)

---

## Overview

This document defines the stable public API contracts for AURORA Phase 3 (MVP). These interfaces are guaranteed to remain backward compatible within the v1.x series. Breaking changes will only occur in major version updates (v2.0+).

**Stability Guarantees**:
- Public APIs will not change signatures within v1.x
- New optional parameters may be added (backward compatible)
- Deprecation warnings will be issued 6 months before removal
- Internal implementation may change without notice

---

## 1. ACT-R Activation Engine

### 1.1 ActivationEngine

**Module**: `aurora_core.activation.engine`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
class ActivationEngine:
    """Main activation calculation engine integrating all ACT-R formulas."""

    def __init__(
        self,
        config: Optional[ActivationConfig] = None,
        *,
        decay_rate: float = 0.5,
        spread_factor: float = 0.7,
        max_hops: int = 3,
        context_weight: float = 0.5,
        decay_cap_days: int = 90,
        grace_period_days: int = 1
    ) -> None:
        """
        Initialize activation engine with configuration.

        Parameters:
            config: Optional pre-configured ActivationConfig
            decay_rate: BLA decay exponent (default: 0.5)
            spread_factor: Spreading activation decay per hop (default: 0.7)
            max_hops: Maximum spreading activation hops (default: 3)
            context_weight: Context boost maximum weight (default: 0.5)
            decay_cap_days: Maximum decay penalty days (default: 90)
            grace_period_days: Decay grace period (default: 1)

        Contract:
            - All parameters are optional with sensible defaults
            - config overrides individual parameters if provided
            - Parameters remain stable in v1.x
        """

    def calculate_activation(
        self,
        chunk_id: str,
        access_history: List[Dict[str, Any]],
        relationships: Optional[List[Tuple[str, str, float]]] = None,
        context_keywords: Optional[Set[str]] = None,
        chunk_keywords: Optional[Set[str]] = None,
        current_time: Optional[datetime] = None
    ) -> float:
        """
        Calculate total activation for a chunk.

        Parameters:
            chunk_id: Unique chunk identifier
            access_history: List of access events with 'timestamp' keys
            relationships: Optional list of (source_id, target_id, weight) tuples
            context_keywords: Optional set of query keywords
            chunk_keywords: Optional set of chunk keywords
            current_time: Optional timestamp for calculation (default: now)

        Returns:
            Total activation score (float, typically -10.0 to +10.0)

        Contract:
            - Return type is always float
            - Returns 0.0 for empty access_history
            - Negative scores indicate low activation
            - Score increases with frequency and recency
            - Stable formula in v1.x (ACT-R validated)
        """

    @staticmethod
    def create_preset(preset: str) -> "ActivationEngine":
        """
        Create engine with preset configuration.

        Parameters:
            preset: Preset name ("default", "aggressive_recall", "conservative",
                   "semantic_only", "balanced")

        Returns:
            Configured ActivationEngine instance

        Contract:
            - All v1.0 presets remain available in v1.x
            - New presets may be added without breaking changes
            - Preset configurations remain stable

        Raises:
            ValueError: If preset name is unknown
        """
```

### 1.2 ActivationRetriever

**Module**: `aurora_core.activation.retrieval`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
class ActivationRetriever:
    """Activation-based chunk retrieval with threshold filtering."""

    def __init__(
        self,
        store: "ChunkStore",
        engine: ActivationEngine,
        *,
        threshold: float = 0.3,
        batch_size: int = 100
    ) -> None:
        """
        Initialize activation-based retriever.

        Parameters:
            store: Chunk storage backend
            engine: Activation calculation engine
            threshold: Minimum activation threshold (default: 0.3)
            batch_size: Batch size for retrieval (default: 100)

        Contract:
            - store must implement ChunkStore interface
            - Parameters remain stable in v1.x
        """

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 10,
        chunk_type: Optional[str] = None,
        min_activation: Optional[float] = None,
        explain: bool = False
    ) -> List[RetrievalResult]:
        """
        Retrieve chunks ranked by activation score.

        Parameters:
            query: User query string
            top_k: Number of results to return (default: 10)
            chunk_type: Optional chunk type filter
            min_activation: Optional minimum activation override
            explain: Include activation breakdown (default: False)

        Returns:
            List of RetrievalResult objects sorted by activation (descending)

        Contract:
            - Return type is always List[RetrievalResult]
            - Results are sorted by activation (highest first)
            - Empty list if no chunks meet threshold
            - explain adds breakdown without changing order
            - Stable ranking algorithm in v1.x
        """
```

---

## 2. Semantic Context Awareness

### 2.1 EmbeddingProvider

**Module**: `aurora_context_code.semantic.embedding_provider`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
class EmbeddingProvider:
    """Sentence-transformers based embedding generation."""

    def __init__(
        self,
        *,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ) -> None:
        """
        Initialize embedding provider.

        Parameters:
            model_name: Hugging Face model name (default: all-MiniLM-L6-v2)
            device: Device for inference ("cpu", "cuda", None=auto)
            cache_dir: Model cache directory (default: ~/.cache)

        Contract:
            - Default model remains stable in v1.x
            - Model dimensions: 384 (stable)
            - All parameters optional with defaults
        """

    def embed_chunk(
        self,
        name: str,
        docstring: Optional[str] = None,
        signature: Optional[str] = None
    ) -> np.ndarray:
        """
        Generate embedding for code chunk.

        Parameters:
            name: Chunk name (function, class, variable)
            docstring: Optional docstring text
            signature: Optional function/class signature

        Returns:
            Normalized embedding vector (384-dim float32 numpy array)

        Contract:
            - Return shape is always (384,) for v1.x
            - Vector is L2-normalized
            - Deterministic for same input
            - Performance: <50ms per chunk (target)

        Raises:
            ValueError: If name is empty
            RuntimeError: If model fails to load
        """

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for user query.

        Parameters:
            query: User query string

        Returns:
            Normalized embedding vector (384-dim float32 numpy array)

        Contract:
            - Return shape is always (384,) for v1.x
            - Vector is L2-normalized
            - Performance: <50ms per query (target)

        Raises:
            ValueError: If query is empty
        """
```

### 2.2 HybridRetriever

**Module**: `aurora_context_code.semantic.hybrid_retriever`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
class HybridRetriever:
    """Hybrid activation + semantic retrieval with configurable weights."""

    def __init__(
        self,
        store: "ChunkStore",
        activation_engine: ActivationEngine,
        embedding_provider: EmbeddingProvider,
        *,
        config: Optional[HybridConfig] = None,
        activation_weight: float = 0.6,
        semantic_weight: float = 0.4
    ) -> None:
        """
        Initialize hybrid retriever.

        Parameters:
            store: Chunk storage backend
            activation_engine: Activation calculation engine
            embedding_provider: Embedding generation provider
            config: Optional pre-configured HybridConfig
            activation_weight: Activation score weight (default: 0.6)
            semantic_weight: Semantic similarity weight (default: 0.4)

        Contract:
            - Weights must sum to 1.0 (validated)
            - Default weights remain stable in v1.x
            - All components must be provided

        Raises:
            ValueError: If weights don't sum to 1.0
        """

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 10,
        activation_threshold: float = 0.3,
        fallback_on_error: bool = True
    ) -> List[HybridResult]:
        """
        Retrieve chunks using hybrid scoring.

        Parameters:
            query: User query string
            top_k: Number of results to return (default: 10)
            activation_threshold: Minimum activation for candidates (default: 0.3)
            fallback_on_error: Fall back to activation-only on embedding errors

        Returns:
            List of HybridResult objects sorted by hybrid score (descending)

        Contract:
            - Return type is always List[HybridResult]
            - Results sorted by: activation_weight * act + semantic_weight * sem
            - Falls back to activation-only if fallback_on_error=True
            - Empty list if no chunks meet threshold
            - Stable scoring formula in v1.x

        Raises:
            RuntimeError: If embeddings fail and fallback_on_error=False
        """
```

---

## 3. Headless Reasoning Mode

### 3.1 HeadlessOrchestrator

**Module**: `aurora_soar.headless.orchestrator`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
class HeadlessOrchestrator:
    """Autonomous goal-driven execution with safety constraints."""

    def __init__(
        self,
        config: "AuroraConfig",
        *,
        soar_orchestrator: Optional["SOAROrchestrator"] = None,
        git_enforcer: Optional[GitEnforcer] = None,
        prompt_loader: Optional[PromptLoader] = None,
        scratchpad_manager: Optional[ScratchpadManager] = None
    ) -> None:
        """
        Initialize headless orchestrator.

        Parameters:
            config: AURORA configuration object
            soar_orchestrator: Optional SOAR orchestrator (default: creates new)
            git_enforcer: Optional git enforcer (default: creates new)
            prompt_loader: Optional prompt loader (default: creates new)
            scratchpad_manager: Optional scratchpad manager (default: creates new)

        Contract:
            - config is required
            - All other parameters are optional with defaults
            - Components can be injected for testing
        """

    def run(
        self,
        prompt_path: str,
        *,
        max_iterations: int = 10,
        budget_limit: float = 5.0,
        dry_run: bool = False
    ) -> HeadlessResult:
        """
        Execute headless reasoning loop.

        Parameters:
            prompt_path: Path to prompt markdown file
            max_iterations: Maximum iteration limit (default: 10)
            budget_limit: Budget limit in USD (default: 5.0)
            dry_run: Validate without execution (default: False)

        Returns:
            HeadlessResult with status, iterations, cost, scratchpad_path

        Contract:
            - Validates git branch (must be "headless" or custom)
            - Validates prompt format before execution
            - Tracks cost and stops at budget_limit
            - Tracks iterations and stops at max_iterations
            - Returns result object (never raises in normal operation)
            - Termination reasons: GOAL_ACHIEVED, BUDGET_EXCEEDED,
              MAX_ITERATIONS, GIT_SAFETY_ERROR, PROMPT_ERROR

        Raises:
            FileNotFoundError: If prompt_path doesn't exist
        """
```

### 3.2 HeadlessResult

**Module**: `aurora_soar.headless.orchestrator`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
@dataclass
class HeadlessResult:
    """Result of headless execution."""

    success: bool
    """Whether goal was achieved."""

    termination_reason: str
    """Why execution stopped (GOAL_ACHIEVED, BUDGET_EXCEEDED, etc.)."""

    iterations: int
    """Number of iterations completed."""

    total_cost: float
    """Total cost in USD."""

    scratchpad_path: str
    """Path to scratchpad file."""

    goal: str
    """Goal from prompt."""

    timestamp: datetime
    """Execution start timestamp."""

    # Contract: All fields are required and immutable (dataclass)
    # Additional fields may be added in v1.x (backward compatible)
```

---

## 4. Performance Optimization

### 4.1 CacheManager

**Module**: `aurora_core.optimization.cache_manager`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
class CacheManager:
    """Multi-tier caching with hot cache, persistent cache, activation scores."""

    def __init__(
        self,
        store: "ChunkStore",
        *,
        hot_cache_size: int = 1000,
        activation_cache_ttl: int = 600
    ) -> None:
        """
        Initialize cache manager.

        Parameters:
            store: Chunk storage backend
            hot_cache_size: Hot cache LRU size (default: 1000)
            activation_cache_ttl: Activation scores TTL in seconds (default: 600)

        Contract:
            - hot_cache_size must be > 0
            - activation_cache_ttl must be > 0
            - Parameters remain stable in v1.x
        """

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get chunk from cache hierarchy.

        Parameters:
            chunk_id: Unique chunk identifier

        Returns:
            Chunk data dictionary or None if not found

        Contract:
            - Checks hot cache → persistent cache → miss
            - Promotes to hot cache on access
            - Return type is always Optional[Dict[str, Any]]
            - None indicates cache miss
        """

    def get_metrics(self) -> CacheMetrics:
        """
        Get cache performance metrics.

        Returns:
            CacheMetrics with hits, misses, hit_rate

        Contract:
            - Return type is always CacheMetrics
            - Metrics are cumulative since initialization
            - hit_rate = hits / (hits + misses)
        """
```

---

## 5. Production Hardening

### 5.1 RetryHandler

**Module**: `aurora_core.resilience.retry_handler`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
class RetryHandler:
    """Exponential backoff retry logic for transient errors."""

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        delays: List[int] = [100, 200, 400],
        recoverable_exceptions: Optional[List[Type[Exception]]] = None
    ) -> None:
        """
        Initialize retry handler.

        Parameters:
            max_attempts: Maximum retry attempts (default: 3)
            delays: Backoff delays in milliseconds (default: [100, 200, 400])
            recoverable_exceptions: Exception types to retry (default: common transient errors)

        Contract:
            - max_attempts must be > 0
            - delays must have at least one value
            - Uses last delay for attempts beyond delays list
            - Default recoverable: TimeoutError, ConnectionError, OSError
        """

    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        Execute function with retry logic.

        Parameters:
            func: Callable to execute
            args: Positional arguments for func
            kwargs: Keyword arguments for func

        Returns:
            Result of successful func execution

        Contract:
            - Retries only on recoverable_exceptions
            - Fails immediately on non-recoverable exceptions
            - Raises last exception after max_attempts
            - Applies exponential backoff between attempts

        Raises:
            Exception: Re-raises last exception after all retries exhausted
        """
```

### 5.2 MetricsCollector

**Module**: `aurora_core.resilience.metrics_collector`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
class MetricsCollector:
    """Performance and reliability metrics tracking."""

    def __init__(self) -> None:
        """
        Initialize metrics collector.

        Contract:
            - Thread-safe for concurrent access
            - Cumulative metrics (no automatic reset)
        """

    def record_query(
        self,
        success: bool,
        latency_ms: float,
        cache_hit: bool = False
    ) -> None:
        """
        Record query execution metrics.

        Parameters:
            success: Whether query succeeded
            latency_ms: Query latency in milliseconds
            cache_hit: Whether result was from cache

        Contract:
            - All parameters are required
            - Updates internal counters atomically
            - No return value (fire-and-forget)
        """

    def get_metrics(self) -> MetricsSnapshot:
        """
        Get snapshot of current metrics.

        Returns:
            MetricsSnapshot with query/cache/error statistics

        Contract:
            - Return type is always MetricsSnapshot
            - Snapshot is consistent (atomic read)
            - Includes: total_queries, successful_queries, failed_queries,
              avg_latency_ms, p95_latency_ms, cache_hits, cache_misses,
              cache_hit_rate, error_rate
        """
```

### 5.3 RateLimiter

**Module**: `aurora_core.resilience.rate_limiter`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
class RateLimiter:
    """Token bucket rate limiting."""

    def __init__(
        self,
        *,
        requests_per_minute: int = 60,
        burst_size: Optional[int] = None
    ) -> None:
        """
        Initialize rate limiter.

        Parameters:
            requests_per_minute: Rate limit (default: 60)
            burst_size: Max burst tokens (default: requests_per_minute)

        Contract:
            - requests_per_minute must be > 0
            - burst_size defaults to requests_per_minute
            - Thread-safe for concurrent access
        """

    def wait_if_needed(self, timeout: float = 60.0) -> bool:
        """
        Wait for rate limit token.

        Parameters:
            timeout: Maximum wait time in seconds (default: 60.0)

        Returns:
            True if token acquired, False if timeout

        Contract:
            - Blocks until token available or timeout
            - Consumes one token on success
            - Returns False on timeout (no token consumed)
            - Thread-safe: multiple threads can call concurrently
        """
```

---

## 6. Memory Commands & CLI

### 6.1 Memory Command

**Module**: `aurora_cli.commands.memory`
**Status**: Stable
**Since**: v1.0.0-phase3

**CLI Interface**:
```bash
aur mem <query> [OPTIONS]

Options:
  --max-results INTEGER   Maximum results to return (default: 10)
  --type TEXT            Filter by chunk type
  --min-activation FLOAT Minimum activation threshold
  --config PATH          Config file path
  --help                 Show help message
```

**Contract**:
- Command remains `aur mem` in v1.x
- All options remain backward compatible
- New options may be added (optional)
- Output format remains stable (ID, type, activation, last_used, context)

### 6.2 Headless Command

**Module**: `aurora_cli.commands.headless`
**Status**: Stable
**Since**: v1.0.0-phase3

**CLI Interface**:
```bash
aur headless <prompt_path> [OPTIONS]

Options:
  --max-iterations INTEGER  Maximum iterations (default: 10)
  --budget-limit FLOAT      Budget limit in USD (default: 5.0)
  --dry-run                 Validate without execution
  --config PATH             Config file path
  --help                    Show help message
```

**Contract**:
- Command remains `aur headless` in v1.x
- All options remain backward compatible
- Safety features remain mandatory (git enforcement)
- Exit codes: 0=success, 1=goal not achieved, 2=error

---

## 7. Configuration Schema

### 7.1 Configuration File Format

**Format**: YAML
**Status**: Stable
**Since**: v1.0.0-phase3

```yaml
# Activation engine configuration
activation:
  decay_rate: 0.5
  spread_factor: 0.7
  max_hops: 3
  context_weight: 0.5
  decay_cap_days: 90
  grace_period_days: 1

# Hybrid retrieval configuration
context:
  code:
    hybrid_weights:
      activation: 0.6
      semantic: 0.4

# Headless mode configuration
headless:
  budget_limit: 5.0
  max_iterations: 10
  branch_name: "headless"

# Resilience configuration
resilience:
  retry:
    max_attempts: 3
    delays: [100, 200, 400]
  rate_limit:
    requests_per_minute: 60
  alerting:
    error_rate_threshold: 0.05
    p95_latency_threshold: 10000
    cache_hit_rate_threshold: 0.20

# Cache configuration
optimization:
  hot_cache_size: 1000
  activation_cache_ttl: 600
```

**Contract**:
- All fields are optional with defaults
- New fields may be added (backward compatible)
- Existing fields will not change meaning in v1.x
- Schema validation available via `AuroraConfig.validate()`

---

## 8. Data Structures

### 8.1 RetrievalResult

**Module**: `aurora_core.activation.retrieval`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
@dataclass
class RetrievalResult:
    """Result from activation-based retrieval."""

    chunk_id: str
    """Unique chunk identifier."""

    chunk_type: str
    """Chunk type (function, class, variable, etc.)."""

    activation: float
    """Total activation score."""

    name: str
    """Chunk name."""

    context: str
    """Chunk context snippet."""

    last_accessed: datetime
    """Last access timestamp."""

    breakdown: Optional[Dict[str, float]] = None
    """Optional activation breakdown (if explain=True)."""

    # Contract: All required fields are immutable
    # breakdown is optional and may be None
```

### 8.2 HybridResult

**Module**: `aurora_context_code.semantic.hybrid_retriever`
**Status**: Stable
**Since**: v1.0.0-phase3

```python
@dataclass
class HybridResult:
    """Result from hybrid retrieval."""

    chunk_id: str
    """Unique chunk identifier."""

    chunk_type: str
    """Chunk type."""

    hybrid_score: float
    """Combined activation + semantic score."""

    activation_score: float
    """Activation component score."""

    semantic_score: float
    """Semantic similarity component score."""

    name: str
    """Chunk name."""

    context: str
    """Chunk context snippet."""

    # Contract: All fields are required and immutable
```

---

## 9. Error Handling

### 9.1 Exception Hierarchy

**Status**: Stable
**Since**: v1.0.0-phase3

```python
# Base exception
class AuroraError(Exception):
    """Base exception for all AURORA errors."""

# Configuration errors
class ConfigurationError(AuroraError):
    """Invalid configuration."""

# Retrieval errors
class RetrievalError(AuroraError):
    """Error during chunk retrieval."""

# Headless mode errors
class HeadlessError(AuroraError):
    """Error during headless execution."""

class GitBranchError(HeadlessError):
    """Git branch validation failed."""

class PromptFormatError(HeadlessError):
    """Prompt file format invalid."""

class BudgetExceededError(HeadlessError):
    """Budget limit exceeded."""

# Resilience errors
class RetryExhaustedError(AuroraError):
    """All retry attempts exhausted."""

class RateLimitError(AuroraError):
    """Rate limit exceeded."""
```

**Contract**:
- All AURORA exceptions inherit from AuroraError
- Exception hierarchy remains stable in v1.x
- New exceptions may be added (subclass appropriately)
- Exception messages are informative but may change

---

## 10. Deprecation Policy

### 10.1 Deprecation Process

1. **Warning Period**: 6 months minimum before removal
2. **Documentation**: Mark as deprecated in docstrings and release notes
3. **Runtime Warnings**: Issue DeprecationWarning when deprecated APIs are used
4. **Migration Guide**: Provide clear migration path to new APIs
5. **Version Removal**: Only remove in next major version (v2.0+)

### 10.2 Stability Levels

- **Stable**: Guaranteed backward compatibility in v1.x
- **Beta**: May change in minor versions (will be documented)
- **Experimental**: May change or be removed without notice (opt-in only)

All APIs in this document are **Stable** unless marked otherwise.

---

## 11. Versioning

**Semantic Versioning**: MAJOR.MINOR.PATCH

- **MAJOR** (v1 → v2): Breaking changes to public APIs
- **MINOR** (v1.0 → v1.1): New features, backward compatible
- **PATCH** (v1.0.0 → v1.0.1): Bug fixes, backward compatible

**Current Version**: v1.0.0-phase3

---

## 12. Contact & Support

- **API Questions**: GitHub Issues
- **Breaking Changes**: Announced 6 months in advance
- **Feature Requests**: GitHub Discussions
- **Bug Reports**: GitHub Issues

---

**Document Version**: 1.0
**Last Updated**: December 23, 2025
**Next Review**: v1.1.0 release

---

**END OF API CONTRACTS**
