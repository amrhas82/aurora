# PRD 0004: AURORA Advanced Memory & Features
## Product Requirements Document

**Version**: 1.0
**Date**: December 20, 2025
**Status**: Ready for Implementation
**Phase**: MVP Phase 3 of 3 (Advanced Memory & Features)
**Product**: AURORA-Context Framework
**Dependencies**: Phase 1 (0002-prd-aurora-foundation.md), Phase 2 (0003-prd-aurora-soar-pipeline.md)

---

## DOCUMENT PURPOSE

This PRD defines **Phase 3: Advanced Memory & Features** for the AURORA-Context framework. This phase implements full ACT-R memory with activation formulas, headless reasoning mode, performance optimization, and production hardening.

**Success Criteria**: This phase is complete when ACT-R activation calculations are operational, headless mode functions autonomously, performance meets targets, and the system is production-ready.

**Related Documents**:
- Source Specification: `/tasks/0001-prd-aurora-context.md` (Sections 6, 9.8, 9.9)
- Previous Phase 1: `/tasks/0002-prd-aurora-foundation.md` (MUST be complete)
- Previous Phase 2: `/tasks/0003-prd-aurora-soar-pipeline.md` (MUST be complete)

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Goals & Success Metrics](#2-goals--success-metrics)
3. [User Stories](#3-user-stories)
4. [Functional Requirements](#4-functional-requirements)
5. [Architecture & Design](#5-architecture--design)
6. [Quality Gates & Acceptance Criteria](#6-quality-gates--acceptance-criteria)
7. [Testing Strategy](#7-testing-strategy)
8. [Inter-Phase Dependencies](#8-inter-phase-dependencies)
9. [Non-Goals (Out of Scope)](#9-non-goals-out-of-scope)
10. [Technical Considerations](#10-technical-considerations)
11. [Delivery Verification Checklist](#11-delivery-verification-checklist)
12. [Open Questions](#12-open-questions)

---

## 1. EXECUTIVE SUMMARY

### 1.1 What is Phase 3?

Phase 3 completes the AURORA-Context MVP by implementing:
1. **Full ACT-R Memory**: Activation formulas (BLA, spreading, decay) for intelligent retrieval
2. **Enhanced Context Awareness**: Semantic embeddings and vector similarity search
3. **Headless Reasoning Mode**: Autonomous background reasoning without user queries
4. **Performance Optimization**: Query optimization for large codebases, parallel execution improvements
5. **Production Hardening**: Error recovery, monitoring, rate limiting, alerting

**The Critical Enabler**: ACT-R activation transforms AURORA from keyword-based retrieval to cognitive-inspired intelligent context selection.

### 1.2 Key Components (Phase 3)

1. **ACT-R Activation Engine**: Base-level, spreading, context boost, decay formulas (using pyactr)
2. **Semantic Context**: Embeddings for better retrieval beyond keywords
3. **Headless Mode**: Autonomous experiments with goal-based termination
4. **Optimization**: Parallel agent improvements, advanced caching, query optimization
5. **Production Features**: Error recovery, monitoring, alerting, rate limiting
6. **Memory Commands**: `aur mem` for explicit recall, auto-escalation mode

### 1.3 Why Phase 3 Matters

Without ACT-R activation:
- Context retrieval is purely keyword-based (Phase 1 limitation)
- No learning from usage patterns
- No decay of stale information
- No spreading activation through relationships

With Phase 3:
- **Intelligent retrieval**: "What's useful to recall right now?" vs "What's similar?"
- **Learning**: Frequently-used patterns get activation boost
- **Decay**: Old, unused patterns fade away
- **Relationships**: Related chunks activate together
- **Autonomous mode**: Background reasoning without blocking workflow
- **Production-ready**: Reliable, monitored, resilient

---

## 2. GOALS & SUCCESS METRICS

### 2.1 Primary Goals

1. **Implement full ACT-R activation formulas** (BLA, spreading, context boost, decay)
2. **Enable semantic context retrieval** with embeddings
3. **Deliver headless reasoning mode** with autonomous experiments
4. **Optimize performance** for large codebases (10K+ chunks)
5. **Harden for production** with error recovery and monitoring
6. **Establish memory commands** for explicit recall and auto-escalation

### 2.2 Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Retrieval Precision** | ≥85% (relevant chunks / retrieved) | Ground truth benchmark |
| **Activation Correlation** | ≥0.7 (activation vs actual usefulness) | User feedback tracking |
| **Learning Improvement** | ≥5% accuracy increase over 20 sessions | Longitudinal study |
| **Cache Hit Rate** | ≥30% after 1000 queries | Telemetry data |
| **Headless Success Rate** | ≥80% goal completion | Headless benchmark suite |
| **Query Latency (10K chunks)** | <500ms retrieval | Performance benchmark |
| **Memory Footprint (10K chunks)** | <100MB | Memory profiler |
| **Error Recovery Rate** | ≥95% transient errors recovered | Fault injection tests |

### 2.3 Phase Completion Criteria

Phase 3 is **COMPLETE** when:
- ✅ ACT-R activation formulas implemented and validated
- ✅ Spreading activation traverses relationships correctly
- ✅ Semantic embeddings improve retrieval precision
- ✅ Headless mode runs autonomous experiments reliably
- ✅ Performance targets met (10K chunks)
- ✅ Error recovery handles transient failures
- ✅ Monitoring and alerting operational
- ✅ All quality gates passed (≥85% coverage)
- ✅ Documentation complete with production deployment guide

---

## 3. USER STORIES

### 3.1 Developer with Large Codebase

**As a** developer working on a 10K+ function codebase,
**I want** AURORA to retrieve relevant context efficiently using activation-based ranking,
**So that** I get accurate results without keyword-matching limitations.

**Acceptance Criteria**:
- Retrieval completes in <500ms for 10K cached chunks
- Top-5 results include ≥4 relevant chunks (≥80% precision)
- Related chunks activate together (spreading activation works)
- Frequently-used patterns rank higher (BLA learning works)
- Old, unused chunks decay over time (don't pollute results)

---

### 3.2 Personal User Running Experiments

**As a** personal developer experimenting with AURORA,
**I want** headless mode to run autonomous reasoning loops without blocking my workflow,
**So that** I can validate system behavior or test pipelines in the background.

**Acceptance Criteria**:
- Headless mode starts with `aurora --headless --prompt=prompt.md`
- Iterates until goal achieved or max iterations reached
- Writes progress to scratchpad.md after each iteration
- Isolates work on "headless" git branch (enforced)
- Respects budget limits ($5 default per experiment)
- Terminates cleanly on goal completion

---

### 3.3 Production Team Lead

**As a** team lead deploying AURORA in production,
**I want** robust error recovery and monitoring,
**So that** transient failures don't disrupt service and issues are visible.

**Acceptance Criteria**:
- Transient errors (network, timeout) retry with exponential backoff
- Monitoring dashboard shows query latency, error rates, cache hit rate
- Alerting triggers on high error rate (>5%) or slow queries (>10s p95)
- Rate limiting prevents runaway API calls (configurable limits)
- Graceful degradation: partial results on non-critical failures

---

### 3.4 Developer Extending Memory System

**As a** developer adding custom context providers,
**I want** clear activation interfaces and spreading activation hooks,
**So that** my custom chunks participate in ACT-R activation.

**Acceptance Criteria**:
- Activation interface documented with examples
- Custom chunks can register relationships (dependencies, calls, imports)
- Spreading activation traverses custom relationships
- Custom activation boosting supported
- Testing utilities available for activation validation

---

## 4. FUNCTIONAL REQUIREMENTS

### 4.1 ACT-R Activation Engine (Core Package)

**Package**: `packages/core/src/aurora_core/activation/`

#### 4.1.1 Activation Formula Implementation

**MUST** implement activation formula from spec Section 6.3:

```
Activation = Base-Level + Spreading + Context-Boost - Decay
```

**Dependencies**: Use `pyactr` library for formula implementations

**Implementation**:
```python
from typing import List, Dict, Any, Tuple
from datetime import datetime
import math

class ActivationEngine:
    """ACT-R activation calculation engine."""

    def __init__(self, decay_rate: float = 0.5, spread_factor: float = 0.7, max_hops: int = 3):
        self.decay_rate = decay_rate
        self.spread_factor = spread_factor
        self.max_hops = max_hops

    def calculate_activation(self, chunk_id: str, context: Dict[str, Any]) -> float:
        """
        Calculate total activation for a chunk.

        Args:
            chunk_id: Chunk identifier
            context: Current query context (for spreading and context boost)

        Returns:
            Total activation score
        """
        base_level = self._calculate_base_level(chunk_id)
        spreading = self._calculate_spreading_activation(chunk_id, context)
        context_boost = self._calculate_context_boost(chunk_id, context)
        decay = self._calculate_decay(chunk_id)

        return base_level + spreading + context_boost - decay
```

#### 4.1.2 Base-Level Activation (BLA)

**Formula** (from spec Section 6.3):
```
B = ln(Σ t_j^(-d))
```
where:
- `t_j` = time since j-th access (in seconds)
- `d` = decay rate (default: 0.5)

**Implementation**:
```python
def _calculate_base_level(self, chunk_id: str) -> float:
    """
    Calculate base-level activation (frequency + recency).

    Uses pyactr formula: B = ln(Σ t_j^(-d))

    Returns:
        Base-level activation score
    """
    # Get access history from store
    access_times = self.store.get_access_history(chunk_id)

    if not access_times:
        return 0.0  # Never accessed

    current_time = datetime.utcnow()
    total = 0.0

    for access_time in access_times:
        time_since = (current_time - access_time).total_seconds()
        if time_since > 0:
            total += time_since ** (-self.decay_rate)

    return math.log(total) if total > 0 else 0.0
```

**Storage Requirements**:
- `activations` table must store:
  - `access_history`: JSON array of ISO 8601 timestamps
  - `access_count`: Integer (for optimization)
  - `last_access`: Timestamp (most recent)

**Performance Optimization**:
- Limit history to last 100 accesses (configurable)
- Use sampling for very old accesses (>90 days)

---

#### 4.1.3 Spreading Activation

**Formula** (from spec Section 6.3):
```
Spreading = 0.7^(hop_count) per hop, max 3 hops
```

**Algorithm**:
1. Start from active chunks in current context
2. Traverse relationships (dependencies, calls, imports)
3. Apply decay factor: 0.7 per hop (configurable)
4. Max depth: 3 hops (configurable)
5. Accumulate activation across all paths

**Implementation**:
```python
def _calculate_spreading_activation(self, chunk_id: str, context: Dict[str, Any]) -> float:
    """
    Calculate spreading activation via relationships.

    Args:
        chunk_id: Target chunk
        context: Current context (contains active chunks)

    Returns:
        Spreading activation contribution
    """
    active_chunks = context.get("active_chunks", [])
    if not active_chunks:
        return 0.0

    total_spread = 0.0

    for source_id in active_chunks:
        # BFS to find paths from source to target
        paths = self._find_paths(source_id, chunk_id, self.max_hops)

        for path in paths:
            # Apply decay: 0.7^(hop_count)
            hop_count = len(path) - 1
            spread_amount = self.spread_factor ** hop_count
            total_spread += spread_amount

    return total_spread

def _find_paths(self, source: str, target: str, max_depth: int) -> List[List[str]]:
    """
    Find all paths from source to target within max_depth.

    Uses BFS with relationship traversal.
    """
    # Implementation: BFS through relationships table
    pass
```

**Relationship Types** (from Phase 1):
- `depends_on`: Code dependency
- `calls`: Function call
- `imports`: Module import
- Custom types supported

**Performance Optimization**:
- Cache relationship graph in memory (rebuild every 100 retrievals)
- Limit path search to 1000 edges max
- Use bidirectional BFS for faster path finding

---

#### 4.1.4 Context Boost

**Formula** (from spec Section 6.3):
```
Context-Boost = overlap_score × 0.5 (max)
```

**Algorithm**:
1. Extract keywords from current query
2. Extract keywords from chunk (name, docstring, metadata)
3. Calculate overlap: `matching_keywords / total_query_keywords`
4. Scale to max 0.5

**Implementation**:
```python
def _calculate_context_boost(self, chunk_id: str, context: Dict[str, Any]) -> float:
    """
    Calculate context boost based on query overlap.

    Args:
        chunk_id: Target chunk
        context: Current context (contains query keywords)

    Returns:
        Context boost (0.0 - 0.5)
    """
    query_keywords = context.get("query_keywords", [])
    if not query_keywords:
        return 0.0

    chunk = self.store.get_chunk(chunk_id)
    if not chunk:
        return 0.0

    # Extract chunk keywords
    chunk_keywords = self._extract_chunk_keywords(chunk)

    # Calculate overlap
    matching = set(query_keywords) & set(chunk_keywords)
    overlap_score = len(matching) / len(query_keywords) if query_keywords else 0.0

    # Scale to max 0.5
    return overlap_score * 0.5

def _extract_chunk_keywords(self, chunk: Chunk) -> List[str]:
    """Extract keywords from chunk for matching."""
    keywords = []

    # From name/signature
    if hasattr(chunk, 'name'):
        keywords.extend(chunk.name.lower().split('_'))

    # From docstring
    if hasattr(chunk, 'docstring') and chunk.docstring:
        keywords.extend(chunk.docstring.lower().split())

    # From metadata keywords (if present)
    if hasattr(chunk, 'metadata') and 'keywords' in chunk.metadata:
        keywords.extend(chunk.metadata['keywords'])

    # Deduplicate and remove stopwords
    return list(set(kw for kw in keywords if len(kw) > 2))
```

---

#### 4.1.5 Decay

**Formula** (from spec Section 6.3):
```
Decay = -0.5 × log10(days_since_access)
```

**Implementation**:
```python
def _calculate_decay(self, chunk_id: str) -> float:
    """
    Calculate decay based on time since last access.

    Formula: -0.5 × log10(days_since_access)

    Returns:
        Decay penalty (negative value)
    """
    last_access = self.store.get_last_access(chunk_id)
    if not last_access:
        return 0.5  # Never accessed, full decay

    current_time = datetime.utcnow()
    days_since = (current_time - last_access).total_seconds() / 86400.0

    if days_since <= 0:
        return 0.0  # Just accessed, no decay

    # Cap at 90 days to prevent extreme decay
    days_since = min(days_since, 90.0)

    return -0.5 * math.log10(days_since)
```

**Decay Curve**:
- 1 day: -0.0 decay (no penalty)
- 7 days: -0.42 decay (small penalty)
- 30 days: -0.74 decay (medium penalty)
- 90 days: -0.98 decay (high penalty, capped)

---

### 4.2 Semantic Context Awareness

**Package**: `packages/context-code/src/aurora_context_code/semantic/`

#### 4.2.1 Embedding Generation

**MUST** support embeddings for semantic similarity:

```python
from typing import List, Dict, Any
import numpy as np

class EmbeddingProvider:
    """Generate embeddings for code chunks."""

    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        # Use sentence-transformers or similar
        self.model = model

    def embed_chunk(self, chunk: Chunk) -> np.ndarray:
        """
        Generate embedding for a chunk.

        Combines: name + docstring + signature

        Returns:
            768-dim embedding vector
        """
        pass

    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for user query."""
        pass

    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity."""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
```

**Model Choice**:
- Default: `all-MiniLM-L6-v2` (fast, 384-dim, good for code)
- Alternative: `CodeBERT` (code-specific)
- Configurable via `context.code.embedding_model`

**Storage**:
- Add `embedding` column to `chunks` table (BLOB)
- Store as numpy array bytes
- Index for fast similarity search (if using vector DB in future)

---

#### 4.2.2 Hybrid Retrieval

**MUST** combine activation + semantic similarity:

```python
class HybridRetriever:
    """Combine ACT-R activation with semantic similarity."""

    def __init__(self, activation_engine: ActivationEngine, embedding_provider: EmbeddingProvider):
        self.activation_engine = activation_engine
        self.embedding_provider = embedding_provider

    def retrieve(self, query: str, budget: int = 10) -> List[Chunk]:
        """
        Retrieve chunks using hybrid scoring.

        Score = 0.6 × activation + 0.4 × semantic_similarity

        Args:
            query: User query
            budget: Max chunks to return

        Returns:
            Top-N chunks sorted by hybrid score
        """
        # 1. Get query embedding
        query_emb = self.embedding_provider.embed_query(query)

        # 2. Extract query keywords for context
        query_keywords = self._extract_keywords(query)
        context = {"query_keywords": query_keywords}

        # 3. Get candidate chunks (top 100 by activation)
        candidates = self.store.retrieve_by_activation(min_activation=0.0, limit=100)

        # 4. Calculate hybrid scores
        scored_chunks = []
        for chunk in candidates:
            # Activation score
            activation = self.activation_engine.calculate_activation(chunk.id, context)

            # Semantic similarity
            chunk_emb = self.embedding_provider.embed_chunk(chunk)
            semantic_sim = self.embedding_provider.similarity(query_emb, chunk_emb)

            # Hybrid score: 60% activation, 40% semantic
            hybrid_score = 0.6 * activation + 0.4 * semantic_sim

            scored_chunks.append((chunk, hybrid_score))

        # 5. Sort by hybrid score, return top-N
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, score in scored_chunks[:budget]]
```

**Weighting Rationale**:
- 60% activation: Prioritize learned patterns and recency
- 40% semantic: Catch synonyms and semantic matches
- Configurable via `context.code.hybrid_weights`

---

### 4.3 Headless Reasoning Mode

**Package**: `packages/soar/src/aurora_soar/headless/`

#### 4.3.1 Headless Orchestrator

**MUST** implement autonomous reasoning loop:

```python
from pathlib import Path
from typing import Optional, Dict, Any

class HeadlessOrchestrator:
    """Autonomous reasoning without user interaction."""

    def __init__(self, soar: SOAROrchestrator, config: Config):
        self.soar = soar
        self.config = config
        self.max_iterations = config.get("headless.default_max_iterations", 10)
        self.budget_limit = config.get("headless.default_budget_limit_usd", 5.00)

    def execute(self, prompt_file: Path, scratchpad_file: Path) -> Dict[str, Any]:
        """
        Run autonomous reasoning loop.

        Args:
            prompt_file: Path to prompt.md (goal definition)
            scratchpad_file: Path to scratchpad.md (iteration memory)

        Returns:
            {
                "status": "goal_achieved" | "max_iterations" | "budget_exceeded",
                "iterations": int,
                "cost_usd": float,
                "goal_reason": str
            }
        """
        # 1. Validate git branch
        self._enforce_headless_branch()

        # 2. Load prompt (goal definition)
        goal = self._load_prompt(prompt_file)

        # 3. Initialize scratchpad
        scratchpad = self._load_scratchpad(scratchpad_file)

        iteration = 1
        total_cost = 0.0

        while iteration <= self.max_iterations:
            # 4. Construct query from prompt + scratchpad context
            query = self._construct_query(goal, scratchpad, iteration)

            # 5. Execute SOAR pipeline
            result = self.soar.execute(query, verbosity="quiet")
            total_cost += result["metadata"]["estimated_cost_usd"]

            # 6. Write results to scratchpad
            self._update_scratchpad(scratchpad_file, iteration, result)

            # 7. Check termination criteria
            if self._check_goal_achieved(scratchpad_file):
                return {
                    "status": "goal_achieved",
                    "iterations": iteration,
                    "cost_usd": total_cost,
                    "goal_reason": self._extract_goal_reason(scratchpad_file)
                }

            if total_cost >= self.budget_limit:
                self._write_budget_exceeded(scratchpad_file)
                return {
                    "status": "budget_exceeded",
                    "iterations": iteration,
                    "cost_usd": total_cost,
                    "goal_reason": f"Budget limit ${self.budget_limit} exceeded"
                }

            iteration += 1

        # Max iterations reached
        return {
            "status": "max_iterations",
            "iterations": self.max_iterations,
            "cost_usd": total_cost,
            "goal_reason": f"Reached max iterations ({self.max_iterations})"
        }
```

#### 4.3.2 Git Branch Enforcement

**MUST** enforce "headless" branch isolation:

```python
def _enforce_headless_branch(self) -> None:
    """
    Ensure current branch is "headless", not main/master.

    Raises:
        ValueError: If on main/master branch
    """
    import subprocess

    # Get current branch
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True
    )
    current_branch = result.stdout.strip()

    # Check if on main/master
    if current_branch in ["main", "master"]:
        raise ValueError(
            "Headless mode requires 'headless' branch.\n"
            "Run: git checkout -b headless"
        )

    # If not on headless branch, warn (but allow)
    if current_branch != "headless":
        self.logger.warning(
            f"Running headless on branch '{current_branch}' (recommended: 'headless')"
        )
```

**Safety Rules** (from spec Section 9.8):
1. CREATE AND USE HEADLESS BRANCH: All work on "headless" only
2. ALLOWED OPERATIONS: Read any file, edit/create on headless, git add/commit
3. FORBIDDEN OPERATIONS: NO git merge, NO git push, NO destructive commands

---

#### 4.3.3 Scratchpad Format

**Scratchpad Structure** (`scratchpad.md`):
```markdown
# Headless Experiment Scratchpad

**Experiment:** [Brief description from prompt.md]
**Started:** 2025-12-20 14:30:00
**Current Iteration:** 3 / 10
**Cost So Far:** $0.45 / $5.00

---

## Iteration 1 (14:30:00)
**Action:** Created test file test_aurora.py
**Observation:** File created successfully
**Next Step:** Run tests to verify behavior

## Iteration 2 (14:31:15)
**Action:** Ran pytest tests/
**Observation:** 329/329 tests passing
**Next Step:** Check if goal is met

## Iteration 3 (14:32:30)
**Action:** Verified all tests pass, checked output matches expected
**Observation:** Goal criteria satisfied (all tests pass, output correct)
**Decision:** GOAL_ACHIEVED: All tests passing, validation complete

---

**STATUS:** GOAL_ACHIEVED
**Reason:** Successfully validated that all 329 tests pass with correct output
**Total Cost:** $0.45
**Total Iterations:** 3
```

**Termination Signals**:
- `GOAL_ACHIEVED: [reason]` - Goal completed
- `BUDGET_EXCEEDED` - Cost limit reached
- Max iterations - Hard limit

---

### 4.4 Performance Optimization

**Package**: `packages/core/src/aurora_core/optimization/`

#### 4.4.1 Query Optimization for Large Codebases

**MUST** optimize for 10K+ chunks:

```python
class QueryOptimizer:
    """Optimize retrieval for large codebases."""

    def __init__(self, store: Store):
        self.store = store
        self.cache = {}  # In-memory chunk cache
        self.relationship_graph = None  # Cached relationship graph

    def optimize_retrieval(self, query: str, budget: int) -> List[Chunk]:
        """
        Optimized retrieval for large codebases.

        Optimizations:
        1. Pre-filter by chunk type (if query hints at type)
        2. Use activation threshold to skip low-activation chunks
        3. Cache frequently-accessed chunks in memory
        4. Batch relationship queries

        Returns:
            Top-N chunks within latency target
        """
        # 1. Pre-filter by type (if applicable)
        type_hint = self._infer_type_hint(query)
        if type_hint:
            candidates = self.store.get_chunks_by_type(type_hint, limit=1000)
        else:
            candidates = self.store.get_all_chunks(limit=1000)

        # 2. Calculate activations (batch mode)
        activations = self._batch_calculate_activations(candidates, query)

        # 3. Filter by threshold (skip low activations)
        threshold = 0.3  # Configurable
        filtered = [
            (chunk, act) for chunk, act in activations if act >= threshold
        ]

        # 4. Sort and return top-N
        filtered.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, act in filtered[:budget]]

    def _batch_calculate_activations(self, chunks: List[Chunk], query: str) -> List[Tuple[Chunk, float]]:
        """
        Calculate activations in batch for efficiency.

        Optimizations:
        - Load all access histories in single query
        - Cache relationship graph
        - Vectorize keyword matching
        """
        pass
```

**Performance Targets** (10K chunks):
- Retrieval: <500ms (p95)
- Activation calculation: <100ms for top 100 candidates
- Memory usage: <100MB

---

#### 4.4.2 Parallel Agent Execution Improvements

**MUST** optimize parallel execution:

```python
class ParallelAgentExecutor:
    """Optimized parallel agent execution."""

    def __init__(self, max_concurrency: int = 5):
        self.max_concurrency = max_concurrency

    async def execute_parallel(self, agent_tasks: List[Dict]) -> List[Dict]:
        """
        Execute agents in parallel with optimizations.

        Optimizations:
        1. Dynamic concurrency (scale based on agent response time)
        2. Early termination (if critical agent fails)
        3. Result streaming (start synthesis as results arrive)

        Args:
            agent_tasks: List of agent execution tasks

        Returns:
            List of agent outputs
        """
        import asyncio

        # Create semaphore for concurrency control
        sem = asyncio.Semaphore(self.max_concurrency)

        async def execute_with_semaphore(task):
            async with sem:
                return await self._execute_agent(task)

        # Execute all tasks in parallel (limited by semaphore)
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in agent_tasks],
            return_exceptions=True
        )

        return results
```

---

#### 4.4.3 Advanced Caching Strategies

**MUST** implement multi-tier caching:

```python
class CacheManager:
    """Multi-tier caching for performance."""

    def __init__(self, config: Config):
        # Tier 1: In-memory LRU cache (hot chunks)
        self.hot_cache = {}  # LRU cache, max 1000 chunks

        # Tier 2: SQLite cache (all chunks)
        self.persistent_cache = Store()

        # Tier 3: Activation scores cache (recent calculations)
        self.activation_cache = {}  # TTL: 10 minutes

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """
        Get chunk with multi-tier caching.

        Check order: hot_cache → SQLite → None
        """
        # Tier 1: Hot cache
        if chunk_id in self.hot_cache:
            return self.hot_cache[chunk_id]

        # Tier 2: SQLite
        chunk = self.persistent_cache.get_chunk(chunk_id)
        if chunk:
            # Promote to hot cache
            self._add_to_hot_cache(chunk_id, chunk)

        return chunk

    def _add_to_hot_cache(self, chunk_id: str, chunk: Chunk) -> None:
        """Add chunk to hot cache (LRU eviction)."""
        if len(self.hot_cache) >= 1000:
            # Evict least recently used
            lru_key = min(self.hot_cache, key=lambda k: self.hot_cache[k].last_accessed)
            del self.hot_cache[lru_key]

        self.hot_cache[chunk_id] = chunk
```

---

### 4.5 Production Hardening

**Package**: `packages/core/src/aurora_core/resilience/`

#### 4.5.1 Error Recovery

**MUST** implement retry with exponential backoff:

```python
from typing import Callable, Any, Optional
import time

class RetryHandler:
    """Retry logic with exponential backoff."""

    def __init__(self, max_attempts: int = 3, base_delay: float = 0.1):
        self.max_attempts = max_attempts
        self.base_delay = base_delay

    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Retry function with exponential backoff.

        Backoff: 100ms, 200ms, 400ms

        Raises:
            Exception: If all attempts fail
        """
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_attempts - 1:
                    raise  # Last attempt, propagate error

                # Calculate backoff delay
                delay = self.base_delay * (2 ** attempt)
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                )
                time.sleep(delay)
```

**Recoverable Errors**:
- Network timeouts
- LLM API rate limits
- Database lock contention
- Agent temporary unavailability

**Non-Recoverable Errors**:
- Invalid configuration
- Budget exceeded
- Malformed input
- All agents failed

---

#### 4.5.2 Monitoring & Alerting

**MUST** implement metrics collection:

```python
from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MetricsCollector:
    """Collect performance and reliability metrics."""

    def __init__(self):
        self.metrics = {
            "queries_total": 0,
            "queries_success": 0,
            "queries_failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "error_rate": 0.0
        }

    def record_query(self, result: Dict[str, Any]) -> None:
        """Record query execution metrics."""
        self.metrics["queries_total"] += 1

        if result.get("success"):
            self.metrics["queries_success"] += 1
        else:
            self.metrics["queries_failed"] += 1

        # Update latency stats
        latency = result["metadata"]["total_duration_ms"]
        self._update_latency_stats(latency)

    def record_cache_hit(self) -> None:
        """Record cache hit."""
        self.metrics["cache_hits"] += 1

    def record_cache_miss(self) -> None:
        """Record cache miss."""
        self.metrics["cache_misses"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        return self.metrics.copy()
```

**Alerting Rules** (configurable):
- Error rate >5% → Alert
- P95 latency >10s → Warning
- Cache hit rate <20% → Info
- Budget usage >80% → Warning

---

#### 4.5.3 Rate Limiting

**MUST** implement rate limiting for API calls:

```python
import time
from collections import deque

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.tokens = requests_per_minute
        self.last_refill = time.time()
        self.requests = deque()

    def acquire(self) -> bool:
        """
        Acquire token for API call.

        Returns:
            True if allowed, False if rate limit exceeded
        """
        self._refill_tokens()

        if self.tokens > 0:
            self.tokens -= 1
            self.requests.append(time.time())
            return True

        return False

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Refill tokens (1 per second)
        tokens_to_add = int(elapsed * (self.requests_per_minute / 60))
        self.tokens = min(self.tokens + tokens_to_add, self.requests_per_minute)

        if tokens_to_add > 0:
            self.last_refill = now

    def wait_if_needed(self) -> None:
        """Block until token available (with timeout)."""
        max_wait = 60.0  # Max 60 seconds
        start = time.time()

        while not self.acquire():
            if time.time() - start > max_wait:
                raise TimeoutError("Rate limit wait timeout exceeded")
            time.sleep(0.1)
```

**Configuration**:
```json
{
  "rate_limiting": {
    "enabled": true,
    "requests_per_minute": 60,
    "burst_size": 10
  }
}
```

---

### 4.6 Memory Commands & Integration Modes

**Package**: `packages/cli/src/aurora_cli/commands/memory.py`

#### 4.6.1 Explicit Memory Recall (`aur mem`)

**MUST** implement memory search command:

```bash
# Search reasoning patterns
aur mem "how did we solve authentication bugs?"

# Search code patterns
aur mem "functions related to user login"

# Search domain knowledge
aur mem "AWS Polly configuration patterns"

# Short form
aur m "search query"
```

**Implementation**:
```python
def command_memory(query: str, max_results: int = 10) -> None:
    """
    Search ACT-R memory directly.

    Args:
        query: Search query
        max_results: Max chunks to return
    """
    # 1. Initialize retriever
    retriever = HybridRetriever(activation_engine, embedding_provider)

    # 2. Retrieve chunks
    chunks = retriever.retrieve(query, budget=max_results)

    # 3. Format output
    print(f"Memory Search Results for: \"{query}\"\n")
    print(f"Found {len(chunks)} relevant patterns (sorted by activation):\n")

    for i, chunk in enumerate(chunks, 1):
        activation = activation_engine.calculate_activation(chunk.id, {})
        last_used = chunk.metadata.get("last_modified", "Unknown")

        print(f"{i}. [{chunk.type.upper()}] ID: {chunk.id}")
        print(f"   Activation: {activation:.2f} | Last used: {last_used}")

        if chunk.type == "reasoning":
            print(f"   Context: {chunk.content.get('pattern', 'N/A')}")
        elif chunk.type == "code":
            print(f"   Function: {chunk.content.get('function', 'N/A')}")

        print()
```

**Output Format**:
```
Memory Search Results for: "authentication bugs"

Found 5 relevant patterns (sorted by activation):

1. [REASONING] ID: reas:auth-token-expiry-2024-11
   Activation: 0.89 | Last used: 2 days ago
   Context: "Fixed token expiry bug by checking refresh window"

2. [CODE] ID: code:src/auth/token_manager.py:validate_token
   Activation: 0.78 | Last modified: 5 days ago
   Function: validate_token(token: str) -> bool

...
```

---

#### 4.6.2 Auto-Escalation Mode

**MUST** implement smart auto-escalation:

```python
class AutoEscalationHandler:
    """Automatically escalate complex queries to full AURORA."""

    def __init__(self, config: Config):
        self.config = config
        self.threshold = config.get("memory_modes.auto_escalation.threshold", 0.6)

    def should_escalate(self, query: str) -> bool:
        """
        Determine if query should escalate to full AURORA.

        Simple queries: Direct LLM + passive memory retrieval
        Complex queries: Full SOAR pipeline

        Args:
            query: User query

        Returns:
            True if should escalate to AURORA
        """
        # 1. Quick keyword complexity check
        complexity_score = self._assess_complexity_quick(query)

        # 2. If score > threshold: escalate
        return complexity_score > self.threshold

    def _assess_complexity_quick(self, query: str) -> float:
        """
        Quick complexity assessment (keyword-based).

        Returns score 0.0-1.0 (simple to complex)
        """
        # Reuse keyword classifier from Phase 2
        from aurora_reasoning.assessment import keyword_classifier
        _, score, _ = keyword_classifier(query)
        return score
```

**User Experience**:
```bash
# User just types query to Claude Code (normal behavior)
claude "how do I implement authentication?"

# If simple: Direct LLM + memory boost (passive)
# If complex: Auto-escalate to full AURORA (transparent)
# User doesn't need to think about it
```

---

## 5. ARCHITECTURE & DESIGN

### 5.1 Package Dependencies (Phase 3)

```
packages/
├── core/
│   ├── src/aurora_core/
│   │   ├── activation/                  # NEW
│   │   │   ├── engine.py                # Main activation calculator
│   │   │   ├── base_level.py            # Frequency + recency decay
│   │   │   ├── spreading.py             # Context spreading (BFS)
│   │   │   └── retrieval.py             # Threshold-based retrieval
│   │   ├── optimization/                # NEW
│   │   │   ├── query_optimizer.py
│   │   │   ├── cache_manager.py
│   │   │   └── parallel_executor.py
│   │   ├── resilience/                  # NEW
│   │   │   ├── retry_handler.py
│   │   │   ├── metrics_collector.py
│   │   │   ├── rate_limiter.py
│   │   │   └── alerting.py
│   │   └── (from Phase 1+2)
│
├── context-code/
│   ├── src/aurora_context_code/
│   │   ├── semantic/                    # NEW
│   │   │   ├── embedding_provider.py
│   │   │   └── hybrid_retriever.py
│   │   └── (from Phase 1)
│
├── soar/
│   ├── src/aurora_soar/
│   │   ├── headless/                    # NEW
│   │   │   ├── orchestrator.py
│   │   │   ├── prompt_loader.py
│   │   │   └── scratchpad_manager.py
│   │   └── (from Phase 2)
│
└── cli/
    ├── src/aurora_cli/
    │   ├── commands/
    │   │   ├── memory.py                # NEW (aur mem)
    │   │   └── headless.py              # NEW (aurora --headless)
    │   └── (from Phase 1+2)
```

### 5.2 ACT-R Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    ACT-R ACTIVATION FLOW                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 2 (RETRIEVE)                                         │
│  ├── User query arrives                                     │
│  ├── Extract query keywords                                 │
│  └── Build context (for activation calculation)            │
│                                                              │
│  Activation Calculation (for each chunk):                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Base-Level (BLA): Frequency + Recency             │   │
│  │    - Load access_history from activations table      │   │
│  │    - Apply formula: ln(Σ t_j^(-d))                   │   │
│  │                                                       │   │
│  │ 2. Spreading Activation: Relationship Traversal      │   │
│  │    - Find paths to active chunks (BFS, max 3 hops)   │   │
│  │    - Apply decay: 0.7^(hop_count)                    │   │
│  │                                                       │   │
│  │ 3. Context Boost: Keyword Overlap                    │   │
│  │    - Match query keywords with chunk keywords        │   │
│  │    - Scale to max 0.5                                │   │
│  │                                                       │   │
│  │ 4. Decay Penalty: Time Since Last Access             │   │
│  │    - Calculate: -0.5 × log10(days_since_access)      │   │
│  │                                                       │   │
│  │ Total = BLA + Spreading + Context - Decay            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Retrieval Ranking:                                         │
│  ├── Filter: activation >= 0.3 (threshold)                 │
│  ├── Sort: by activation (descending)                      │
│  └── Return: top-N chunks (budget)                         │
│                                                              │
│  Phase 8 (RECORD)                                           │
│  ├── Update access_history (append timestamp)              │
│  ├── Update activation scores                              │
│  └── Apply learning updates (+0.2, -0.1, etc.)             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Headless Mode Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    HEADLESS MODE FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  START HEADLESS LOOP (iteration = 1)                        │
│      ↓                                                       │
│  Validate Git Branch (must be "headless", not main/master)  │
│      ↓                                                       │
│  Read prompt.md (goal definition + constraints)             │
│  Read scratchpad.md (previous iteration memory)             │
│      ↓                                                       │
│  USER QUERY (from prompt + scratchpad context)              │
│      ↓                                                       │
│  [Normal AURORA flow: ASSESS → ... → SYNTHESIZE]            │
│      ↓                                                       │
│  Write results to scratchpad.md (append iteration log)      │
│      ↓                                                       │
│  Check termination:                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Goal achieved? (LLM evaluates from scratchpad)    │   │
│  │ 2. Max iterations reached?                           │   │
│  │ 3. Budget exceeded?                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│      ↓                                                       │
│  If NOT terminated:                                         │
│    → INCREMENT iteration                                    │
│    → LOOP BACK to start                                     │
│      ↓                                                       │
│  If TERMINATED:                                             │
│    → Write final status to scratchpad.md                    │
│    → EXIT with code 0 (success) or 1 (failure/timeout)     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. QUALITY GATES & ACCEPTANCE CRITERIA

### 6.1 Code Quality Gates

| Gate | Requirement | Tool | Blocker |
|------|-------------|------|---------|
| **Code Coverage** | ≥85% for activation/, ≥80% for headless/ | pytest-cov | YES |
| **Type Checking** | 0 mypy errors (strict mode) | mypy | YES |
| **Linting** | 0 critical issues | ruff | YES |
| **Security** | 0 high/critical vulnerabilities | bandit | YES |
| **Performance** | Retrieval <500ms for 10K chunks | Benchmark | YES |

### 6.2 Performance Gates

| Metric | Target | Measurement | Blocker |
|--------|--------|-------------|---------|
| **Retrieval (10K chunks)** | <500ms (p95) | Benchmark suite | YES |
| **Activation Calculation** | <100ms for top 100 candidates | Benchmark | YES |
| **Spreading Activation** | <200ms (3 hops, 1000 edges) | Benchmark | YES |
| **Memory Footprint (10K)** | <100MB | Memory profiler | YES |
| **Cache Hit Rate** | ≥30% after 1000 queries | Telemetry | NO (warning) |

### 6.3 Functional Acceptance Tests

**Each scenario MUST pass**:

#### Test Scenario 1: ACT-R Activation Works

```python
def test_actr_activation():
    """ACT-R activation formula produces expected results."""
    # GIVEN: 3 chunks with different access patterns
    chunk_a = create_chunk("A")  # Accessed frequently (10x, last 1 day ago)
    chunk_b = create_chunk("B")  # Accessed once (1x, last 30 days ago)
    chunk_c = create_chunk("C")  # Never accessed

    # WHEN: Calculate activations
    activation_a = engine.calculate_activation(chunk_a.id, context)
    activation_b = engine.calculate_activation(chunk_b.id, context)
    activation_c = engine.calculate_activation(chunk_c.id, context)

    # THEN: Frequent recent chunk has highest activation
    assert activation_a > activation_b > activation_c
    assert activation_a >= 0.8  # High activation
    assert activation_b >= 0.3  # Medium activation
    assert activation_c <= 0.1  # Low activation
```

#### Test Scenario 2: Spreading Activation Traverses Relationships

```python
def test_spreading_activation():
    """Spreading activation follows relationship graph."""
    # GIVEN: Chunks with dependencies: A → B → C
    chunk_a = create_chunk("A")
    chunk_b = create_chunk("B")
    chunk_c = create_chunk("C")
    store.add_relationship(chunk_a.id, chunk_b.id, "depends_on")
    store.add_relationship(chunk_b.id, chunk_c.id, "depends_on")

    # Active context: A is active
    context = {"active_chunks": [chunk_a.id]}

    # WHEN: Calculate activation for C
    activation_c = engine.calculate_activation(chunk_c.id, context)

    # THEN: C receives spreading activation (2 hops: 0.7^2 = 0.49)
    assert activation_c >= 0.4  # Should have spreading contribution
```

#### Test Scenario 3: Semantic Retrieval Improves Precision

```python
def test_semantic_retrieval():
    """Semantic embeddings improve retrieval precision."""
    # GIVEN: 10 chunks, 2 semantically related to "OAuth2"
    chunks = create_test_chunks(10)
    oauth_chunks = [chunks[0], chunks[5]]  # Semantically related

    # WHEN: Retrieve with query "OAuth2 authentication"
    retriever = HybridRetriever(engine, embedding_provider)
    results = retriever.retrieve("OAuth2 authentication", budget=5)

    # THEN: OAuth-related chunks rank higher
    assert oauth_chunks[0] in results[:3]  # Top 3
    assert oauth_chunks[1] in results[:3]
```

#### Test Scenario 4: Headless Mode Reaches Goal

```python
def test_headless_goal_completion():
    """Headless mode iterates until goal achieved."""
    # GIVEN: Prompt with clear goal
    prompt = Path("tests/fixtures/headless/validate_tests.md")
    scratchpad = Path("/tmp/scratchpad.md")

    # WHEN: Run headless
    headless = HeadlessOrchestrator(soar, config)
    result = headless.execute(prompt, scratchpad)

    # THEN: Goal achieved within max iterations
    assert result["status"] == "goal_achieved"
    assert result["iterations"] <= 10
    assert "GOAL_ACHIEVED" in scratchpad.read_text()
```

#### Test Scenario 5: Error Recovery Works

```python
def test_error_recovery():
    """Transient errors are retried successfully."""
    # GIVEN: Mock LLM that fails twice, then succeeds
    mock_llm = MockLLMWithFailures(fail_count=2)

    # WHEN: Execute query with retry handler
    retry_handler = RetryHandler(max_attempts=3)
    result = retry_handler.retry(soar.execute, "Test query")

    # THEN: Query succeeds after retries
    assert result["success"] == True
    assert mock_llm.call_count == 3  # Failed twice, succeeded on 3rd
```

---

## 7. TESTING STRATEGY

### 7.1 Unit Tests

**MUST test each component in isolation**:

**Activation Package**:
- `test_base_level.py`: BLA formula accuracy
- `test_spreading.py`: Relationship traversal
- `test_context_boost.py`: Keyword overlap calculation
- `test_decay.py`: Decay penalty calculation
- `test_engine.py`: Full activation formula

**Semantic Package**:
- `test_embedding_provider.py`: Embedding generation
- `test_hybrid_retriever.py`: Hybrid scoring

**Headless Package**:
- `test_orchestrator.py`: Headless loop logic
- `test_branch_enforcement.py`: Git branch checks
- `test_scratchpad.py`: Scratchpad parsing

**Optimization Package**:
- `test_query_optimizer.py`: Query optimization
- `test_cache_manager.py`: Multi-tier caching
- `test_parallel_executor.py`: Parallel execution

**Resilience Package**:
- `test_retry_handler.py`: Retry logic
- `test_metrics_collector.py`: Metrics collection
- `test_rate_limiter.py`: Rate limiting

### 7.2 Integration Tests

**MUST test end-to-end flows**:

1. **ACT-R Retrieval E2E**: Parse code → Store → Update activations → Retrieve → Verify ranking
2. **Semantic Retrieval E2E**: Generate embeddings → Hybrid retrieval → Verify precision
3. **Headless E2E**: Prompt → Loop → Scratchpad updates → Goal termination
4. **Error Recovery E2E**: Inject transient errors → Retry → Succeed
5. **Performance Under Load**: 10K chunks → Parallel queries → Verify latency

### 7.3 Performance Benchmarks

**MUST establish baselines**:

```python
def test_activation_performance(benchmark_fixture):
    """Benchmark activation calculation at scale."""

    test_cases = [
        ("100_chunks", 100, 100),      # 100 chunks, max 100ms
        ("1000_chunks", 1000, 200),    # 1000 chunks, max 200ms
        ("10000_chunks", 10000, 500),  # 10K chunks, max 500ms
    ]

    for name, chunk_count, max_ms in test_cases:
        # Setup: Create chunks with access history
        chunks = create_test_chunks_with_history(chunk_count)

        with benchmark_fixture.measure(f"activation_{name}"):
            results = retriever.retrieve("test query", budget=10)

        benchmark_fixture.assert_performance(
            f"activation_{name}",
            max_ms=max_ms
        )

        assert len(results) > 0
```

### 7.4 Fault Injection Tests

**MUST test resilience**:

1. **LLM Timeout**: Simulate timeout → Retry → Succeed
2. **Database Lock**: Simulate lock contention → Backoff → Retry
3. **Budget Exceeded**: Force budget limit → Block query
4. **Headless Max Iterations**: Exceed max iterations → Terminate gracefully
5. **Malformed Embedding**: Invalid embedding → Fallback to keyword-only

---

## 8. INTER-PHASE DEPENDENCIES

### 8.1 What Phase 3 Depends On

| Component | Phase 1+2 Interface | Usage |
|-----------|-------------------|-------|
| **Store** | `get_access_history()`, `get_last_access()` | BLA calculation |
| **Relationships Table** | `relationships` table populated | Spreading activation |
| **ReasoningChunk** | Full implementation with tool tracking | Learning updates |
| **SOAR Orchestrator** | `execute()` API | Headless mode |
| **Budget Tracker** | Cost tracking operational | Headless budget enforcement |

### 8.2 Post-MVP Features (Phase 4+)

**Not in MVP, but enabled by Phase 3**:
- Option C verification (debate mode)
- Knowledge context provider (API/schema retrieval)
- Multi-language parsing (Go, Rust, Java)
- Distributed storage (PostgreSQL, vector DB)
- Real-time streaming responses

---

## 9. NON-GOALS (OUT OF SCOPE)

### 9.1 Explicitly NOT in Phase 3

| Feature | Why Not Now | When |
|---------|-------------|------|
| **Option C Verification** | Requires debate infrastructure | Post-MVP |
| **Knowledge Context Provider** | API/schema retrieval complex | Post-MVP |
| **Multi-language Parsing** | Python sufficient for MVP | Phase 1.5 (Go) or Post-MVP |
| **Vector Database** | SQLite sufficient, avoid complexity | Post-MVP |
| **Distributed Execution** | Single-process acceptable for MVP | Post-MVP |
| **Real-time Streaming** | Batch responses sufficient | Post-MVP |
| **Fine-tuning** | LLM APIs sufficient | Post-MVP |

### 9.2 Technical Constraints (Accepted for Phase 3)

- **No distributed activation**: Single-process calculation only
- **No real-time embeddings**: Pre-compute on storage, not query-time
- **No advanced graph algorithms**: BFS sufficient for spreading activation
- **No custom embedding models**: Use pre-trained sentence-transformers
- **No embedding index**: Sequential similarity search acceptable for MVP

---

## 10. TECHNICAL CONSIDERATIONS

### 10.1 ACT-R Formula Accuracy

**Critical Requirements**:
- Use `pyactr` library for BLA formula (proven correct)
- Validate against ACT-R literature examples
- Test edge cases: never-accessed chunks, very old chunks, circular dependencies
- Calibrate decay rate (default 0.5) with real usage data

**Validation Strategy**:
- Unit tests with known input/output pairs
- Compare against ACT-R reference implementation
- Longitudinal study: track retrieval precision over time

---

### 10.2 Embedding Model Selection

**Model Requirements**:
- Fast inference (<50ms per chunk)
- Good code understanding (trained on code or general text)
- Reasonable size (<500MB model file)
- Open-source and freely usable

**Recommended Models**:
1. **all-MiniLM-L6-v2** (default): Fast, 384-dim, general-purpose
2. **CodeBERT**: Code-specific, but slower
3. **all-mpnet-base-v2**: Higher quality, but larger/slower

**Fallback**: If embeddings unavailable, use keyword-only retrieval (Phase 1 mode)

---

### 10.3 Headless Safety Mechanisms

**Critical Safety Measures**:
1. **Git branch enforcement**: Block main/master branches
2. **Budget limits**: Hard stop at configured limit
3. **Max iterations**: Prevent infinite loops
4. **Goal validation**: LLM evaluates goal achievement (not heuristic)
5. **Scratchpad logging**: Full audit trail of autonomous actions

**Risk Mitigation**:
- Headless branch easy to discard: `git branch -D headless`
- No merge, no push: isolated experiments
- Budget per-experiment: prevent runaway costs
- Transparent: scratchpad shows all actions

---

### 10.4 Performance Optimization Strategies

**Query Optimization**:
- Pre-filter by chunk type (if query hints at type)
- Use activation threshold (skip low-activation chunks early)
- Cache relationship graph (rebuild every 100 retrievals)
- Batch activation calculations (single SQL query)

**Caching**:
- Hot cache: 1000 most-accessed chunks (LRU eviction)
- Persistent cache: SQLite (all chunks)
- Activation cache: 10-minute TTL (avoid recalculation)

**Parallelization**:
- Parallel agent execution (Phase 2 improvement)
- Parallel embedding generation (batch mode)
- Parallel activation calculation (vectorized)

---

## 11. DELIVERY VERIFICATION CHECKLIST

**Phase 3 is complete when ALL items checked**:

### 11.1 Implementation Complete
- [ ] ACT-R activation formulas implemented (BLA, spreading, decay)
- [ ] Semantic embeddings integrated
- [ ] Headless mode operational (goal termination works)
- [ ] Query optimization for 10K+ chunks
- [ ] Error recovery with exponential backoff
- [ ] Monitoring and alerting functional
- [ ] Memory commands (`aur mem`) implemented
- [ ] Auto-escalation mode works

### 11.2 Testing Complete
- [ ] Unit test coverage ≥85% for activation/, ≥80% for headless/
- [ ] All integration tests pass (5 scenarios)
- [ ] Performance benchmarks met (10K chunks <500ms)
- [ ] Fault injection tests pass (5 scenarios)
- [ ] Retrieval precision ≥85% on benchmark suite
- [ ] Headless success rate ≥80% on benchmark suite

### 11.3 Documentation Complete
- [ ] ACT-R activation formulas documented with examples
- [ ] Headless mode usage guide written
- [ ] Performance tuning guide written
- [ ] Production deployment guide written
- [ ] Troubleshooting guide for advanced features

### 11.4 Quality Assurance
- [ ] Code review completed (2+ reviewers)
- [ ] Security audit passed
- [ ] ACT-R formula validation completed
- [ ] Performance profiling completed (no bottlenecks)
- [ ] Memory leak testing passed

### 11.5 Production Readiness
- [ ] Error recovery tested under load
- [ ] Monitoring dashboard operational
- [ ] Alerting rules configured
- [ ] Rate limiting tested
- [ ] Graceful degradation verified

---

## 12. OPEN QUESTIONS

### 12.1 Design Decisions

1. **Embedding Model Choice**
   - **Question**: all-MiniLM-L6-v2 vs CodeBERT?
   - **Impact**: Speed vs code-specific accuracy
   - **Recommendation**: all-MiniLM-L6-v2 (faster, good enough for MVP)

2. **Activation Threshold**
   - **Question**: Default threshold 0.3 or 0.5?
   - **Impact**: Retrieval precision vs recall
   - **Recommendation**: 0.3 (configurable), favor recall initially

3. **Headless Max Iterations**
   - **Question**: Default max iterations 10 or 20?
   - **Impact**: Safety vs experiment flexibility
   - **Recommendation**: 10 (configurable), safer default

### 12.2 Performance Tradeoffs

1. **Embedding Pre-computation**
   - **Question**: Pre-compute all embeddings or lazy-generate?
   - **Tradeoff**: Storage cost vs query latency
   - **Recommendation**: Pre-compute on storage (Phase 8), amortize cost

2. **Spreading Activation Depth**
   - **Question**: Max 3 hops or allow 5?
   - **Tradeoff**: Context coverage vs computation cost
   - **Recommendation**: Max 3 hops (spec-compliant), configurable

3. **Cache Size**
   - **Question**: Hot cache 1000 chunks or 5000?
   - **Tradeoff**: Memory usage vs cache hit rate
   - **Recommendation**: 1000 (configurable), <100MB target

---

## APPENDIX A: ACT-R FORMULA EXAMPLES

### Example 1: Base-Level Activation

**Scenario**: Chunk accessed 3 times (10 days ago, 5 days ago, 1 day ago)

**Calculation**:
```python
decay_rate = 0.5

t_1 = 10 * 86400  # 10 days in seconds
t_2 = 5 * 86400   # 5 days
t_3 = 1 * 86400   # 1 day

sum_term = (t_1 ** -0.5) + (t_2 ** -0.5) + (t_3 ** -0.5)
sum_term = 0.0034 + 0.0048 + 0.0107 = 0.0189

base_level = ln(0.0189) = -3.97
```

**Result**: BLA = -3.97 (negative due to time decay, but frequent recent access)

---

### Example 2: Spreading Activation

**Scenario**: Query activates chunk A, which depends on B, which depends on C

**Calculation**:
```python
spread_factor = 0.7

# Path A → B → C (2 hops)
spreading_activation = 0.7 ** 2 = 0.49
```

**Result**: Chunk C receives +0.49 activation boost from spreading

---

### Example 3: Total Activation

**Scenario**: Chunk with BLA=-3.0, spreading=0.5, context=0.3, decay=-0.4

**Calculation**:
```python
total = base_level + spreading + context_boost - decay
total = -3.0 + 0.5 + 0.3 - (-0.4)
total = -3.0 + 0.5 + 0.3 + 0.4
total = -1.8
```

**Result**: Total activation = -1.8 (above threshold 0.3? No, not retrieved)

---

## APPENDIX B: HEADLESS MODE EXAMPLE

**Prompt File** (`headless/prompt.md`):
```markdown
# Headless Experiment: Validate Test Suite

## Goal
Verify that all 329 tests in the test suite pass with correct output.

## Success Criteria
1. Run `pytest tests/`
2. All tests pass (329/329)
3. Output matches expected results

## Constraints
- Budget limit: $5.00
- Max iterations: 10
- Work on "headless" branch only

## Safety Rules
1. CREATE AND USE HEADLESS BRANCH: All work on "headless" only
2. ALLOWED: Read files, run tests, check output
3. FORBIDDEN: NO git merge, NO git push, NO destructive commands
```

**Scratchpad Output** (`headless/scratchpad.md`):
```markdown
# Headless Experiment Scratchpad

**Experiment:** Validate Test Suite
**Started:** 2025-12-20 14:30:00
**Current Iteration:** 3 / 10
**Cost So Far:** $0.45 / $5.00

---

## Iteration 1 (14:30:00)
**Action:** Created test file test_aurora.py
**Observation:** File created successfully
**Next Step:** Run tests to verify behavior

## Iteration 2 (14:31:15)
**Action:** Ran pytest tests/
**Observation:** 329/329 tests passing
**Next Step:** Check if goal is met

## Iteration 3 (14:32:30)
**Action:** Verified all tests pass, checked output matches expected
**Observation:** Goal criteria satisfied (all tests pass, output correct)
**Decision:** GOAL_ACHIEVED: All tests passing, validation complete

---

**STATUS:** GOAL_ACHIEVED
**Reason:** Successfully validated that all 329 tests pass with correct output
**Total Cost:** $0.45
**Total Iterations:** 3
```

---

## APPENDIX C: PERFORMANCE OPTIMIZATION EXAMPLES

### Example 1: Query Optimization

**Before** (naive):
```python
# Load all 10K chunks, calculate activation for each
chunks = store.get_all_chunks()
activations = [engine.calculate_activation(c.id, context) for c in chunks]
```
**Time**: ~2000ms

**After** (optimized):
```python
# Pre-filter by type, batch calculate, early threshold
chunks = store.get_chunks_by_type("code", limit=1000)  # Pre-filter
activations = engine.batch_calculate(chunks, context)   # Batch mode
filtered = [c for c, a in activations if a >= 0.3]      # Threshold
```
**Time**: ~400ms (5x faster)

---

### Example 2: Caching Strategy

**Before** (no caching):
```python
# Every retrieval hits database
chunk = store.get_chunk(chunk_id)
```
**Cache miss rate**: 100%

**After** (multi-tier cache):
```python
# Hot cache (1000 chunks) → SQLite → Not found
chunk = cache_manager.get_chunk(chunk_id)
```
**Cache hit rate**: 35% (after 1000 queries)
**Latency reduction**: 80% for cache hits

---

## DOCUMENT HISTORY

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-20 | Initial PRD for Phase 3 Advanced Memory & Features | Product Team |

---

**END OF PRD 0004: AURORA Advanced Memory & Features**
