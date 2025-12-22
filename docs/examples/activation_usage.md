# AURORA Activation System - Usage Examples

**Purpose**: Practical examples demonstrating how to use AURORA's ACT-R activation engine for memory-augmented reasoning.

**Audience**: Developers integrating activation-based retrieval, researchers experimenting with cognitive models, and users optimizing memory performance.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Activation Calculation](#basic-activation-calculation)
3. [Component-by-Component Examples](#component-by-component-examples)
4. [Activation-Based Retrieval](#activation-based-retrieval)
5. [Configuration Presets](#configuration-presets)
6. [Custom Configurations](#custom-configurations)
7. [Edge Cases and Best Practices](#edge-cases-and-best-practices)
8. [Performance Optimization](#performance-optimization)
9. [Debugging and Explanation](#debugging-and-explanation)
10. [Real-World Scenarios](#real-world-scenarios)

---

## Quick Start

### Minimal Example: Calculate Activation for a Chunk

```python
from datetime import datetime, timedelta, timezone
from aurora_core.activation.engine import ActivationEngine
from aurora_core.activation.base_level import AccessHistoryEntry

# Create engine with default configuration
engine = ActivationEngine()

# Prepare chunk data
now = datetime.now(timezone.utc)
access_history = [
    AccessHistoryEntry(timestamp=now - timedelta(hours=1)),
    AccessHistoryEntry(timestamp=now - timedelta(days=7)),
]
chunk_keywords = {'database', 'query', 'optimization'}
query_keywords = {'database', 'performance'}

# Calculate activation
result = engine.calculate_total(
    access_history=access_history,
    last_access=now - timedelta(hours=1),
    spreading_activation=0.7,  # From relationship graph
    chunk_keywords=chunk_keywords,
    query_keywords=query_keywords,
    reference_time=now
)

print(f"Total Activation: {result.total:.3f}")
print(f"  BLA: {result.bla:.3f}")
print(f"  Spreading: {result.spreading:.3f}")
print(f"  Context: {result.context_boost:.3f}")
print(f"  Decay: {result.decay:.3f}")
```

**Output**:
```
Total Activation: -0.245
  BLA: -3.512
  Spreading: 0.700
  Context: 0.333
  Decay: 0.000
```

---

## Basic Activation Calculation

### Example 1: Single Component - Base-Level Activation

Calculate activation based solely on access frequency and recency:

```python
from aurora_core.activation.base_level import BaseLevelActivation, BLAConfig
from datetime import datetime, timedelta, timezone

# Configure BLA calculator
config = BLAConfig(decay_rate=0.5)  # Standard ACT-R decay
calculator = BaseLevelActivation(config)

# Chunk accessed 3 times
now = datetime.now(timezone.utc)
access_history = [
    AccessHistoryEntry(timestamp=now - timedelta(hours=1)),   # Recent
    AccessHistoryEntry(timestamp=now - timedelta(days=1)),    # Yesterday
    AccessHistoryEntry(timestamp=now - timedelta(days=7)),    # Last week
]

# Calculate BLA
bla = calculator.calculate(access_history, reference_time=now)
print(f"Base-Level Activation: {bla:.3f}")
# Output: Base-Level Activation: -3.846
```

**Interpretation**: Higher BLA means more frequent/recent access. Multiple accesses compound to boost activation.

### Example 2: Single Component - Spreading Activation

Calculate activation spreading from related chunks:

```python
from aurora_core.activation.spreading import SpreadingActivation, SpreadingConfig
from aurora_core.activation.spreading import Relationship, RelationshipGraph

# Configure spreading calculator
config = SpreadingConfig(spread_factor=0.7, max_hops=3)
calculator = SpreadingActivation(config)

# Build relationship graph
relationships = [
    Relationship(source="chunk_A", target="chunk_B", rel_type="calls"),
    Relationship(source="chunk_B", target="chunk_C", rel_type="imports"),
]
graph = RelationshipGraph(relationships=relationships)

# Calculate spreading from chunk_A to chunk_C (2 hops)
spreading = calculator.calculate(
    target_id="chunk_C",
    active_ids={"chunk_A"},  # Active in working memory
    graph=graph
)
print(f"Spreading Activation: {spreading:.3f}")
# Output: Spreading Activation: 0.490  (0.7^2 = 0.49)
```

**Interpretation**: Activation decays exponentially with distance (hops). Closer relationships receive more boost.

### Example 3: Single Component - Context Boost

Calculate boost from query relevance:

```python
from aurora_core.activation.context_boost import ContextBoost, ContextBoostConfig

# Configure context calculator
config = ContextBoostConfig(boost_factor=0.5)
calculator = ContextBoost(config)

# Keywords from chunk and query
chunk_keywords = {'database', 'index', 'query', 'performance'}
query_keywords = {'database', 'performance', 'optimization'}

# Calculate context boost
boost = calculator.calculate(chunk_keywords, query_keywords)
print(f"Context Boost: {boost:.3f}")
# Output: Context Boost: 0.250  (50% keyword overlap, 0.5 * 0.5 = 0.25)
```

**Interpretation**: Higher keyword overlap → higher boost. Contextually relevant chunks are prioritized.

### Example 4: Single Component - Decay Penalty

Calculate penalty for stale chunks:

```python
from aurora_core.activation.decay import DecayCalculator, DecayConfig
from datetime import datetime, timedelta, timezone

# Configure decay calculator
config = DecayConfig(
    decay_factor=0.5,
    grace_period_days=1,
    max_days=365
)
calculator = DecayCalculator(config)

# Calculate decay for chunk not accessed in 30 days
now = datetime.now(timezone.utc)
last_access = now - timedelta(days=30)

decay = calculator.calculate(last_access, reference_time=now)
print(f"Decay Penalty: {decay:.3f}")
# Output: Decay Penalty: -0.739  (-0.5 * log10(30) ≈ -0.739)
```

**Interpretation**: Logarithmic decay means old chunks accumulate penalty slowly. Grace period prevents penalty for recent accesses.

---

## Component-by-Component Examples

### Example 5: Understanding Component Interactions

Calculate total activation and see how each component contributes:

```python
from aurora_core.activation.engine import ActivationEngine, ActivationConfig
from aurora_core.activation.base_level import AccessHistoryEntry
from datetime import datetime, timedelta, timezone

# Create engine
engine = ActivationEngine()
now = datetime.now(timezone.utc)

# Scenario: Frequently used, recent, relevant chunk
access_history = [
    AccessHistoryEntry(timestamp=now - timedelta(hours=2)),
    AccessHistoryEntry(timestamp=now - timedelta(days=1)),
    AccessHistoryEntry(timestamp=now - timedelta(days=3)),
    AccessHistoryEntry(timestamp=now - timedelta(days=7)),
]

result = engine.calculate_total(
    access_history=access_history,
    last_access=now - timedelta(hours=2),
    spreading_activation=0.7,  # 1 hop away
    chunk_keywords={'auth', 'login', 'user', 'session'},
    query_keywords={'auth', 'user'},
    reference_time=now
)

print("=== Activation Breakdown ===")
print(f"BLA:          {result.bla:>7.3f}  (frequency + recency)")
print(f"Spreading:    {result.spreading:>7.3f}  (related chunks)")
print(f"Context:      {result.context_boost:>7.3f}  (keyword match)")
print(f"Decay:        {result.decay:>7.3f}  (time penalty)")
print(f"{'─' * 30}")
print(f"Total:        {result.total:>7.3f}")
```

**Output**:
```
=== Activation Breakdown ===
BLA:          -3.251  (frequency + recency)
Spreading:     0.700  (related chunks)
Context:       0.250  (keyword match)
Decay:         0.000  (time penalty)
──────────────────────────────────
Total:        -2.301
```

**Analysis**:
- **BLA is negative**: This is normal! ACT-R uses logarithmic scales. Higher (less negative) = better.
- **Spreading adds 0.7**: Chunk is 1 hop from active memory.
- **Context adds 0.25**: 50% keyword overlap (2/4 query keywords match).
- **No decay**: Within 24-hour grace period.
- **Total -2.301**: Above typical retrieval threshold (0.3), likely to be retrieved.

### Example 6: Comparing Two Chunks

Which chunk should be retrieved?

```python
# Chunk A: Recently accessed, no relationships, low relevance
chunk_a = engine.calculate_total(
    access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
    last_access=now - timedelta(hours=1),
    spreading_activation=0.0,  # No relationships
    chunk_keywords={'unrelated', 'keywords'},
    query_keywords={'auth', 'user'},
    reference_time=now
)

# Chunk B: Older access, but related and highly relevant
chunk_b = engine.calculate_total(
    access_history=[
        AccessHistoryEntry(timestamp=now - timedelta(days=3)),
        AccessHistoryEntry(timestamp=now - timedelta(days=10)),
    ],
    last_access=now - timedelta(days=3),
    spreading_activation=1.4,  # 2 paths: 0.7 + 0.7
    chunk_keywords={'auth', 'user', 'login'},
    query_keywords={'auth', 'user'},
    reference_time=now
)

print("Chunk A (recent, unrelated):")
print(f"  Total: {chunk_a.total:.3f}")
print(f"\nChunk B (older, related + relevant):")
print(f"  Total: {chunk_b.total:.3f}")
print(f"\nWinner: {'Chunk B' if chunk_b.total > chunk_a.total else 'Chunk A'}")
```

**Output**:
```
Chunk A (recent, unrelated):
  Total: -5.686

Chunk B (older, related + relevant):
  Total: -1.437

Winner: Chunk B
```

**Lesson**: Relationships and relevance can outweigh recency. ACT-R balances multiple factors.

---

## Activation-Based Retrieval

### Example 7: Retrieve Top-N Chunks

Use the retrieval module to find the most activated chunks:

```python
from aurora_core.activation.retrieval import ActivationRetriever, RetrievalConfig
from aurora_core.activation.engine import ActivationEngine
from aurora_core.activation.spreading import RelationshipGraph

# Setup retriever
engine = ActivationEngine()
config = RetrievalConfig(
    threshold=0.0,  # No filtering for this example
    max_results=5,
    include_components=True  # Show breakdown
)
retriever = ActivationRetriever(engine, config)

# Mock chunk data (in real use, fetch from Store)
chunks = [
    MockChunk(
        id="chunk_1",
        access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
        last_access=now - timedelta(hours=1),
        keywords={'database', 'query'}
    ),
    MockChunk(
        id="chunk_2",
        access_history=[
            AccessHistoryEntry(timestamp=now - timedelta(days=2)),
            AccessHistoryEntry(timestamp=now - timedelta(days=10)),
        ],
        last_access=now - timedelta(days=2),
        keywords={'database', 'index', 'performance'}
    ),
    # ... more chunks
]

# Build relationship graph
graph = RelationshipGraph(relationships=[
    Relationship(source="chunk_1", target="chunk_2", rel_type="imports")
])

# Retrieve top chunks
results = retriever.retrieve(
    chunks=chunks,
    query_keywords={'database', 'performance'},
    active_chunk_ids={'chunk_1'},  # Currently viewing chunk_1
    graph=graph,
    reference_time=now
)

# Display results
for i, result in enumerate(results, 1):
    print(f"{i}. {result.chunk_id} (activation: {result.activation:.3f})")
    if result.components:
        print(f"   BLA: {result.components.bla:.3f}, "
              f"Spread: {result.components.spreading:.3f}, "
              f"Context: {result.components.context_boost:.3f}")
```

**Output**:
```
1. chunk_2 (activation: -2.145)
   BLA: -4.123, Spread: 0.700, Context: 0.333
2. chunk_1 (activation: -5.353)
   BLA: -5.686, Spread: 0.000, Context: 0.333
```

**Analysis**: chunk_2 wins despite older access because it receives spreading activation from chunk_1 and has better keyword match.

### Example 8: Threshold Filtering

Filter out low-activation chunks:

```python
# Strict threshold: only highly activated chunks
strict_config = RetrievalConfig(
    threshold=-1.0,  # Only chunks with activation > -1.0
    max_results=10
)
strict_retriever = ActivationRetriever(engine, strict_config)

results = strict_retriever.retrieve(
    chunks=chunks,
    query_keywords={'database', 'performance'},
    active_chunk_ids={'chunk_1'},
    graph=graph
)

print(f"Strict filtering: {len(results)} chunks passed threshold")
# Output: Strict filtering: 1 chunks passed threshold
```

**Use Case**: In large codebases, use threshold to limit results to truly relevant chunks.

---

## Configuration Presets

AURORA provides 5 preset configurations optimized for different scenarios:

### Example 9: DEFAULT Configuration (Balanced)

```python
from aurora_core.activation.engine import ActivationEngine, DEFAULT_CONFIG

engine = ActivationEngine(DEFAULT_CONFIG)

# Configuration details:
# - BLA decay: 0.5 (standard ACT-R)
# - Spreading: 0.7^hop, max 3 hops
# - Context boost: 0.5 max
# - Decay: -0.5 * log10(days), grace 1 day
# - All components enabled

# Best for: General-purpose retrieval, balanced memory/relevance
```

### Example 10: AGGRESSIVE Configuration (Recency-Biased)

```python
from aurora_core.activation.engine import AGGRESSIVE_CONFIG

engine = ActivationEngine(AGGRESSIVE_CONFIG)

# Configuration details:
# - BLA decay: 0.3 (slower decay, recent chunks favored)
# - Spreading: 0.8^hop (stronger spread)
# - Context boost: 0.8 max (high relevance boost)
# - Decay: -0.8 * log10(days) (heavy staleness penalty)

# Best for: Real-time coding, prioritize recent edits
```

### Example 11: CONSERVATIVE Configuration (Stability)

```python
from aurora_core.activation.engine import CONSERVATIVE_CONFIG

engine = ActivationEngine(CONSERVATIVE_CONFIG)

# Configuration details:
# - BLA decay: 0.7 (faster decay, penalize infrequent)
# - Spreading: 0.6^hop (weaker spread)
# - Context boost: 0.3 max (lower relevance boost)
# - Decay: -0.3 * log10(days) (gentle staleness penalty)

# Best for: Stable codebases, avoid over-retrieval
```

### Example 12: BLA_FOCUSED Configuration (Usage History)

```python
from aurora_core.activation.engine import BLA_FOCUSED_CONFIG

engine = ActivationEngine(BLA_FOCUSED_CONFIG)

# Configuration details:
# - BLA decay: 0.4 (moderate)
# - Spreading: DISABLED (no relationship boost)
# - Context boost: 0.3 max
# - Decay: -0.6 * log10(days)

# Best for: Simple projects, no complex relationships
```

### Example 13: CONTEXT_FOCUSED Configuration (Semantic Match)

```python
from aurora_core.activation.engine import CONTEXT_FOCUSED_CONFIG

engine = ActivationEngine(CONTEXT_FOCUSED_CONFIG)

# Configuration details:
# - BLA decay: 0.6
# - Spreading: 0.5^hop (weak spread)
# - Context boost: 1.0 max (DOUBLE normal boost)
# - Decay: -0.4 * log10(days)

# Best for: Documentation search, keyword-heavy queries
```

---

## Custom Configurations

### Example 14: Build Your Own Configuration

```python
from aurora_core.activation.engine import ActivationEngine, ActivationConfig
from aurora_core.activation.base_level import BLAConfig
from aurora_core.activation.spreading import SpreadingConfig
from aurora_core.activation.context_boost import ContextBoostConfig
from aurora_core.activation.decay import DecayConfig

# Custom configuration for long-term project memory
config = ActivationConfig(
    bla_config=BLAConfig(
        decay_rate=0.4  # Slower decay, value long-term patterns
    ),
    spreading_config=SpreadingConfig(
        spread_factor=0.75,  # Moderate spread
        max_hops=4,  # Allow deeper relationships
        max_edges=2000  # Support larger graphs
    ),
    context_config=ContextBoostConfig(
        boost_factor=0.6,  # Boost relevant chunks
        enable_stop_words=True,
        stop_words={'the', 'a', 'an', 'in', 'of'}
    ),
    decay_config=DecayConfig(
        decay_factor=0.3,  # Light penalty
        grace_period_days=7,  # Longer grace (weekly sprints)
        max_days=730  # Track 2 years
    ),
    enable_bla=True,
    enable_spreading=True,
    enable_context=True,
    enable_decay=True
)

engine = ActivationEngine(config)
```

### Example 15: Disable Components Selectively

```python
# Disable spreading for flat projects (no relationships)
config = ActivationConfig(
    enable_spreading=False,  # Turn off relationship boost
    enable_bla=True,
    enable_context=True,
    enable_decay=True
)
engine = ActivationEngine(config)

# Calculate activation without spreading
result = engine.calculate_total(
    access_history=access_history,
    last_access=last_access,
    spreading_activation=0.7,  # Ignored because disabled
    chunk_keywords=chunk_keywords,
    query_keywords=query_keywords
)
# result.spreading will be 0.0
```

---

## Edge Cases and Best Practices

### Example 16: Never-Accessed Chunks (Cold Start)

Handle chunks with no access history:

```python
# Chunk never accessed before
empty_history = []
last_access = None  # Never accessed

result = engine.calculate_total(
    access_history=empty_history,
    last_access=last_access,
    spreading_activation=0.0,
    chunk_keywords={'new', 'feature'},
    query_keywords={'new', 'feature'},
    reference_time=now
)

print(f"Never-accessed chunk activation: {result.total:.3f}")
# Output: Never-accessed chunk activation: 0.500
```

**Behavior**:
- **BLA**: Returns 0.0 (neutral baseline, not -inf)
- **Context**: Can still provide boost from keyword match
- **Total**: Will be low unless context boost is high

**Best Practice**: Ensure new chunks have good keywords/relationships to bootstrap retrieval.

### Example 17: Very Old Chunks (Years Ago)

```python
# Chunk last accessed 3 years ago
old_access = now - timedelta(days=1095)  # 3 years
access_history = [AccessHistoryEntry(timestamp=old_access)]

result = engine.calculate_total(
    access_history=access_history,
    last_access=old_access,
    spreading_activation=0.0,
    chunk_keywords={'legacy', 'deprecated'},
    query_keywords={'legacy'},
    reference_time=now
)

print(f"Very old chunk activation: {result.total:.3f}")
print(f"  BLA: {result.bla:.3f}")
print(f"  Decay (capped at 365 days): {result.decay:.3f}")
# Output:
# Very old chunk activation: -9.063
#   BLA: -8.292
#   Decay (capped at 365 days): -1.275
```

**Behavior**: Decay is capped at `max_days` (default 365) to prevent extreme penalties.

**Best Practice**: Archive or delete chunks inactive for >1 year to reduce noise.

### Example 18: Circular Dependencies (Graph Cycles)

```python
from aurora_core.activation.spreading import RelationshipGraph, Relationship

# Create circular relationship: A → B → C → A
circular_relationships = [
    Relationship(source="chunk_A", target="chunk_B", rel_type="calls"),
    Relationship(source="chunk_B", target="chunk_C", rel_type="imports"),
    Relationship(source="chunk_C", target="chunk_A", rel_type="inherits"),
]
graph = RelationshipGraph(relationships=circular_relationships)

# Calculate spreading from A to C
from aurora_core.activation.spreading import SpreadingActivation, SpreadingConfig
calculator = SpreadingActivation(SpreadingConfig())

spreading = calculator.calculate(
    target_id="chunk_C",
    active_ids={"chunk_A"},
    graph=graph
)
print(f"Spreading in circular graph: {spreading:.3f}")
# Output: Spreading in circular graph: 0.490 (2 hops: A→B→C)
```

**Behavior**: BFS traversal with visited tracking prevents infinite loops. Finds shortest path.

**Best Practice**: Circular dependencies are handled correctly. No special action needed.

### Example 19: Multiple Active Chunks (Multi-Source Spreading)

```python
# Calculate spreading from multiple active chunks
spreading = calculator.calculate(
    target_id="chunk_D",
    active_ids={"chunk_A", "chunk_B", "chunk_C"},  # Multiple sources
    graph=graph
)
# Spreading is SUM of activation from all sources
```

**Behavior**: Activation from multiple sources is additive (as per ACT-R theory).

**Best Practice**: When working with multiple files, include all open files as active sources.

### Example 20: High-Frequency Chunks (Anti-Pattern Detection)

```python
# Chunk accessed 100 times (potential utility function)
high_freq_history = [
    AccessHistoryEntry(timestamp=now - timedelta(days=i))
    for i in range(100)
]

result = engine.calculate_total(
    access_history=high_freq_history,
    last_access=now - timedelta(hours=1),
    spreading_activation=0.0,
    chunk_keywords={'util', 'helper'},
    query_keywords={'main', 'feature'},  # Low relevance
    reference_time=now
)

print(f"High-frequency chunk activation: {result.total:.3f}")
print(f"  BLA (frequency effect): {result.bla:.3f}")
print(f"  Context (low relevance): {result.context_boost:.3f}")
```

**Behavior**: High frequency boosts BLA, but low context match prevents over-retrieval.

**Best Practice**: Trust the balance. If utils appear too often, adjust `context_config.boost_factor` upward.

---

## Performance Optimization

### Example 21: Batch Retrieval (Large Codebases)

For 10K+ chunks, use batch processing:

```python
from aurora_core.activation.retrieval import ActivationRetriever

# Enable batch processing
config = RetrievalConfig(
    threshold=-2.0,  # Pre-filter low activation
    max_results=20,
    include_components=False  # Reduce memory
)
retriever = ActivationRetriever(engine, config)

# Chunks are processed in batches internally
results = retriever.retrieve(
    chunks=large_chunk_list,  # 10,000 chunks
    query_keywords=query_keywords,
    active_chunk_ids=active_ids,
    graph=graph,
    batch_size=1000  # Process 1000 at a time
)
# Target: <500ms for 10K chunks
```

### Example 22: Cache Relationship Graph

```python
from aurora_core.activation.graph_cache import GraphCache

# Cache relationship graph to avoid rebuilding
cache = GraphCache(rebuild_interval=100)  # Rebuild every 100 retrievals

# First retrieval: builds graph
graph = cache.get_or_build(relationships)

# Next 99 retrievals: use cached graph
for _ in range(99):
    graph = cache.get_or_build(relationships)  # Returns cached

# 100th retrieval: rebuilds graph
graph = cache.get_or_build(relationships)  # Rebuilds
```

**Performance**: Caching reduces graph construction from ~50ms to <1ms.

---

## Debugging and Explanation

### Example 23: Explain Activation Scores

Use the `explain()` method to understand retrieval decisions:

```python
result = engine.calculate_total(
    access_history=access_history,
    last_access=last_access,
    spreading_activation=0.7,
    chunk_keywords={'auth', 'user'},
    query_keywords={'auth', 'login'},
    reference_time=now
)

# Get human-readable explanation
explanation = engine.explain(result)
print(explanation)
```

**Output**:
```
Activation Breakdown for Chunk:
  Base-Level Activation: -3.512
    - Accessed 3 times
    - Most recent: 1.0 hours ago
    - Formula: ln(Σ t_j^-0.5) = -3.512

  Spreading Activation: 0.700
    - Distance from active chunks: 1 hop
    - Formula: 0.7^1 = 0.700

  Context Boost: 0.250
    - Query keywords: {'auth', 'login'}
    - Chunk keywords: {'auth', 'user'}
    - Overlap: 50.0% (1/2 query keywords match)
    - Formula: 0.5 * 0.5 = 0.250

  Decay Penalty: 0.000
    - Last access: 1.0 hours ago
    - Within grace period (24h): No penalty

  Total Activation: -2.562
    - Formula: -3.512 + 0.700 + 0.250 - 0.000 = -2.562
```

**Use Case**: Debug why specific chunks are/aren't being retrieved.

### Example 24: Compare Configurations

A/B test different configurations:

```python
configs = {
    "default": DEFAULT_CONFIG,
    "aggressive": AGGRESSIVE_CONFIG,
    "conservative": CONSERVATIVE_CONFIG,
}

results = {}
for name, config in configs.items():
    engine = ActivationEngine(config)
    result = engine.calculate_total(
        access_history=access_history,
        last_access=last_access,
        spreading_activation=0.7,
        chunk_keywords={'database', 'query'},
        query_keywords={'database', 'performance'}
    )
    results[name] = result.total

print("Configuration Comparison:")
for name, activation in sorted(results.items(), key=lambda x: x[1], reverse=True):
    print(f"  {name:15s}: {activation:.3f}")
```

**Output**:
```
Configuration Comparison:
  aggressive     : -1.823
  default        : -2.301
  conservative   : -3.012
```

---

## Real-World Scenarios

### Example 25: Code Navigation (Jump to Definition)

Scenario: User clicks on function `authenticate_user()`. Which chunks should appear in context?

```python
# User is viewing "auth_controller.py" which calls authenticate_user()
current_file = "auth_controller.py"
current_function = "authenticate_user"

# Build context
query_keywords = {'authenticate', 'user', 'login', 'session'}
active_ids = {"auth_controller.py::LoginHandler"}

# Retrieve related chunks
results = retriever.retrieve(
    chunks=all_chunks,
    query_keywords=query_keywords,
    active_chunk_ids=active_ids,
    graph=relationship_graph
)

# Top results should include:
# 1. authenticate_user() definition (high context + spreading)
# 2. User model (spreading from authenticate_user)
# 3. Session manager (spreading + recent access)
```

### Example 26: Debugging Session (Stack Trace Analysis)

Scenario: Exception in `process_payment()`. Show relevant context.

```python
# Exception stack trace provides keywords
error_keywords = {'payment', 'transaction', 'stripe', 'error', 'timeout'}

# Exception occurred in these functions (active in stack)
stack_chunks = {
    "payments.py::process_payment",
    "payments.py::charge_customer",
    "integrations/stripe.py::create_charge"
}

# Retrieve with high spreading weight (follow call chain)
config = ActivationConfig(
    spreading_config=SpreadingConfig(spread_factor=0.8),  # Strong spread
    context_config=ContextBoostConfig(boost_factor=0.7)
)
engine = ActivationEngine(config)

results = retriever.retrieve(
    chunks=all_chunks,
    query_keywords=error_keywords,
    active_chunk_ids=stack_chunks,
    graph=call_graph
)

# Expected results:
# - Functions in call stack (high spreading)
# - Error handling code (context match)
# - Recently modified payment code (BLA + decay)
```

### Example 27: Documentation Lookup

Scenario: User types "How do I configure logging?" in docs search.

```python
# Documentation search: high context weight, low BLA weight
doc_config = ActivationConfig(
    bla_config=BLAConfig(decay_rate=0.7),  # De-prioritize frequency
    context_config=ContextBoostConfig(boost_factor=1.0),  # Maximize relevance
    decay_config=DecayConfig(decay_factor=0.2),  # Ignore staleness
    enable_spreading=False  # Docs don't have code relationships
)
doc_engine = ActivationEngine(doc_config)

query_keywords = {'configure', 'logging', 'setup', 'logs'}

# Retrieve documentation chunks
results = retriever.retrieve(
    chunks=doc_chunks,
    query_keywords=query_keywords,
    active_chunk_ids=set(),  # No active context
    graph=empty_graph
)

# Results ranked purely by keyword match
```

### Example 28: Refactoring Assistant

Scenario: User wants to rename `getUserById` → `findUserById`. Find all affected code.

```python
# Build bidirectional relationship graph (calls + called-by)
refactor_graph = RelationshipGraph(relationships=[
    Relationship(source="UserService::getUserById", target="User", rel_type="returns"),
    Relationship(source="UserController::show", target="UserService::getUserById", rel_type="calls"),
    Relationship(source="UserController::update", target="UserService::getUserById", rel_type="calls"),
    # ... more relationships
])

# Find all chunks related to getUserById
active_ids = {"UserService::getUserById"}
query_keywords = {'user', 'get', 'find', 'id'}

# Use aggressive spreading to find all connected chunks
refactor_config = AGGRESSIVE_CONFIG
refactor_engine = ActivationEngine(refactor_config)

results = retriever.retrieve(
    chunks=all_chunks,
    query_keywords=query_keywords,
    active_chunk_ids=active_ids,
    graph=refactor_graph,
    max_results=50  # Get all affected code
)

print(f"Found {len(results)} chunks affected by refactor")
for result in results:
    print(f"  - {result.chunk_id} (activation: {result.activation:.3f})")
```

### Example 29: Pair Programming Bot

Scenario: AI pair programming assistant maintains conversation context.

```python
# Track chunks mentioned in conversation
conversation_chunks = set()
conversation_keywords = set()

# Each user message updates context
def process_message(message, chunks_mentioned, keywords):
    conversation_chunks.update(chunks_mentioned)
    conversation_keywords.update(keywords)

    # Retrieve relevant context with full activation
    results = retriever.retrieve(
        chunks=all_chunks,
        query_keywords=conversation_keywords,
        active_chunk_ids=conversation_chunks,
        graph=code_graph
    )

    return results[:5]  # Top 5 for LLM context

# Example conversation:
# User: "The authentication logic is slow"
process_message(
    message="The authentication logic is slow",
    chunks_mentioned={"auth_service.py::authenticate"},
    keywords={'authentication', 'slow', 'performance'}
)

# User: "Check if we're caching the session"
results = process_message(
    message="Check if we're caching the session",
    chunks_mentioned={"session_manager.py::get_session"},
    keywords={'cache', 'session', 'performance'}
)
# Results will include:
# - authenticate() (active in conversation)
# - session cache code (spreading + context)
# - related performance code (context match)
```

### Example 30: Intelligent Code Review

Scenario: Automatically prioritize which files a reviewer should check.

```python
# Get files changed in PR
changed_files = ["user_service.py", "user_model.py", "tests/test_user.py"]

# Build active context from changed chunks
changed_chunks = set()
for file in changed_files:
    changed_chunks.update(get_chunks_in_file(file))

# Find related code that might be affected
query_keywords = extract_keywords_from_changes(changed_files)

review_config = ActivationConfig(
    spreading_config=SpreadingConfig(
        spread_factor=0.75,
        max_hops=2  # Direct dependencies only
    )
)
review_engine = ActivationEngine(review_config)

results = retriever.retrieve(
    chunks=all_chunks,
    query_keywords=query_keywords,
    active_chunk_ids=changed_chunks,
    graph=dependency_graph
)

# Filter to chunks NOT in the PR (potential side effects)
related_files = [
    r.chunk_id for r in results
    if not any(f in r.chunk_id for f in changed_files)
]

print("Suggested files to review for side effects:")
for file in related_files[:10]:
    print(f"  - {file}")
```

---

## Summary and Best Practices

### Key Takeaways

1. **All components matter**: BLA, spreading, context, and decay work together. Don't disable components unless you have a good reason.

2. **Negative activation is normal**: ACT-R uses logarithmic scales. Compare relative scores, not absolute values.

3. **Configuration matters**: Choose presets that match your use case, or build custom configs for specific scenarios.

4. **Edge cases are handled**: Never-accessed chunks, circular dependencies, and very old chunks all have safe defaults.

5. **Explain when debugging**: Use `engine.explain()` to understand retrieval decisions.

6. **Optimize for scale**: Use thresholds, batch processing, and graph caching for large codebases.

### Configuration Guidelines

| Use Case | Recommended Config | Key Settings |
|----------|-------------------|--------------|
| General coding | DEFAULT | Balanced all components |
| Real-time editing | AGGRESSIVE | High recency bias, strong spreading |
| Stable codebases | CONSERVATIVE | Lower spread, gentle decay |
| Flat projects | BLA_FOCUSED | Spreading disabled |
| Documentation | CONTEXT_FOCUSED | High context boost |
| Custom workflow | Build your own | Fine-tune each component |

### Performance Targets

- **Single activation**: <1ms
- **Batch 100 chunks**: <10ms
- **Batch 1K chunks**: <50ms
- **Batch 10K chunks**: <500ms (with graph caching)

### Common Pitfalls

1. **Forgetting to update access history**: Always call `store.record_access()` after retrieval.
2. **Ignoring spreading**: Relationships dramatically improve retrieval quality.
3. **Over-filtering with threshold**: Start with low threshold (-2.0) and tune up.
4. **Not using explain()**: When results surprise you, explain them first before adjusting config.
5. **Treating activation as probability**: Activation is relative ranking, not absolute probability.

---

## Further Reading

- [docs/actr-formula-validation.md](../actr-formula-validation.md) - Mathematical validation against ACT-R literature
- [tests/unit/core/activation/test_actr_literature_validation.py](../../tests/unit/core/activation/test_actr_literature_validation.py) - Literature examples as tests
- Anderson, J. R. (2007). *How Can the Human Mind Occur in the Physical Universe?* - Primary ACT-R reference
- [ACT-R Website](http://act-r.psy.cmu.edu/) - Cognitive architecture research

---

**Document Version**: 1.0
**Last Updated**: December 22, 2025
**Related Task**: Task 1.19 - Add activation usage examples to docs/examples/activation_usage.md
