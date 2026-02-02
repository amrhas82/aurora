# ACT-R Activation System in AURORA

**Version**: 1.1 (Type-Specific Decay + MMR)
**Date**: January 31, 2026
**Status**: Production Ready

---

## Executive Summary

AURORA implements a cognitively-inspired memory system based on ACT-R (Adaptive Control of Thought-Rational), a unified theory of human cognition developed by John Anderson at Carnegie Mellon University. This document provides comprehensive coverage of the activation formulas, their theoretical foundations, implementation details, and practical usage.

**Key Benefits**:
- **Cognitive Fidelity**: Memory retrieval mirrors human cognitive patterns (frequency, recency, context, associations)
- **Code-Aware Intelligence** (NEW v1.1): Type-specific decay rates model how different code artifacts are remembered differently
- **Stability Tracking** (NEW v1.1): Git churn factor penalizes volatile code that changes frequently
- **Diversity Control** (NEW v1.1): MMR reranking prevents "echo chamber" results
- **Validated Implementation**: All formulas match published ACT-R literature within <5% deviation
- **Production Ready**: 291+ passing tests, 86.99% coverage, comprehensive benchmarks
- **Flexible Configuration**: 5 preset configs + custom tuning for any use case

**What's New in v1.1**:
- 🆕 Type-specific decay: KB chunks decay 8× slower than functions
- 🆕 Churn factor: High-commit code decays faster (stability penalty)
- 🆕 MMR diversity reranking: Get varied results covering multiple aspects
- 🆕 Enhanced configuration: Customizable decay maps and diversity controls

**Quick Links**:
- [Formula Reference](#formula-reference) - Mathematical definitions
- [Type-Specific Decay](#type-specific-decay-v11) - NEW: Code-aware forgetting
- [Churn Factor](#churn-factor-stability-penalty-v11) - NEW: Stability tracking
- [MMR Diversity](#mmr-diversity-reranking-v11) - NEW: Avoid redundant results
- [Calculation Examples](#calculation-examples) - Step-by-step walkthroughs
- [Usage Guide](#usage-guide) - Code examples
- [Configuration](#configuration) - Tuning activation behavior
- [Validation](#validation) - Literature verification

---

## Table of Contents

1. [Introduction to ACT-R](#introduction-to-actr)
2. [Theoretical Foundation](#theoretical-foundation)
3. [Formula Reference](#formula-reference)
   - [Type-Specific Decay (v1.1)](#type-specific-decay-v11)
   - [Churn Factor / Stability Penalty (v1.1)](#churn-factor-stability-penalty-v11)
   - [MMR Diversity Reranking (v1.1)](#mmr-diversity-reranking-v11)
4. [Component Details](#component-details)
5. [Calculation Examples](#calculation-examples)
   - [Type-Specific Decay Examples (v1.1)](#example-5-type-specific-decay-v11)
   - [Churn Factor Examples (v1.1)](#example-6-churn-factor-stability-v11)
   - [MMR Diversity Examples (v1.1)](#example-7-mmr-diversity-reranking-v11)
6. [Integration Formula](#integration-formula)
7. [Usage Guide](#usage-guide)
   - [MMR Diversity Usage (v1.1)](#5-mmr-diversity-reranking-v11)
8. [Configuration](#configuration)
   - [Type-Specific Decay Configuration (v1.1)](#type-specific-decay-configuration-v11)
   - [MMR Configuration (v1.1)](#mmr-configuration-v11)
9. [Performance](#performance)
10. [Validation](#validation)
11. [Troubleshooting](#troubleshooting)
12. [References](#references)
13. [Changelog](#changelog)

---

## Introduction to ACT-R

### What is ACT-R?

ACT-R (Adaptive Control of Thought-Rational) is a cognitive architecture that models how human memory and cognition work. Developed over 40+ years of research, ACT-R explains how humans:
- Learn from experience
- Remember and forget information
- Retrieve relevant memories in context
- Make decisions under uncertainty

### Why Use ACT-R for Code Memory?

Programming involves cognitive processes similar to human memory:
- **Frequency**: Functions you use often should be easier to recall
- **Recency**: Recently edited code is more relevant
- **Context**: Code matching your current task should surface first
- **Associations**: Related code (imports, calls, inheritance) activates together

AURORA's ACT-R implementation makes code retrieval feel natural and cognitively aligned with how developers think.

### Core Principles

**1. Activation-Based Retrieval**
Every chunk of code has an activation level that determines its availability in memory. Higher activation = more likely to be retrieved.

**2. Multi-Factor Activation**
Activation combines four independent factors:
- Base-Level Activation (BLA): Usage frequency and recency
- Spreading Activation: Relationships to active code
- Context Boost: Keyword relevance to current query
- Decay Penalty: Staleness from lack of use

**3. Power-Law Behavior**
Memory follows power-law curves observed in human cognition:
- Power law of practice: More practice → diminishing returns on activation gain
- Power law of forgetting: Memory decays rapidly at first, then slowly

---

## Theoretical Foundation

### Anderson's Memory Equation

The total activation of a chunk *i* in ACT-R is:

```
A_i = B_i + Σ_j W_j S_ji + C_i - D_i
```

Where:
- **A_i**: Total activation of chunk *i*
- **B_i**: Base-level activation (frequency + recency)
- **Σ_j W_j S_ji**: Spreading activation from related chunks *j*
- **C_i**: Context boost from environmental match
- **D_i**: Decay penalty for staleness

AURORA implements this equation with four corresponding components:

| ACT-R Term | AURORA Component | Implementation |
|------------|------------------|----------------|
| B_i | Base-Level Activation | `activation/base_level.py` |
| Σ_j W_j S_ji | Spreading Activation | `activation/spreading.py` |
| C_i | Context Boost | `activation/context_boost.py` |
| D_i | Decay Penalty | `activation/decay.py` |

### Cognitive Justification

**Base-Level Activation** reflects the *need probability* - chunks used frequently and recently are likely to be needed again.

**Spreading Activation** reflects *associative memory* - thinking about one concept activates related concepts.

**Context Boost** reflects *environmental cuing* - external cues (keywords) make relevant memories more accessible.

**Decay Penalty** reflects *interference and forgetting* - unused memories become harder to access over time.

---

## Formula Reference

### 1. Base-Level Activation (BLA)

**Formula**:
```
BLA = ln(Σ_j t_j^(-d))
```

**Parameters**:
- `t_j`: Time since jth access (seconds)
- `d`: Decay rate (default 0.5, standard ACT-R value)
- `ln`: Natural logarithm

**Special Cases**:
- Empty access history: Returns 0.0 (neutral baseline)
- Single access: `ln(t^(-d))`
- Multiple accesses: Logarithm of sum of power-law terms

**Literature Source**: Anderson (2007), *How Can the Human Mind Occur in the Physical Universe?*, p. 74

**Code Location**: `packages/core/src/aurora_core/activation/base_level.py`

---

### 2. Spreading Activation

**Formula**:
```
S_i = Σ_j (W_j × F^(d_ij))
```

**Parameters**:
- `S_i`: Total spreading to chunk *i*
- `W_j`: Weight of source chunk *j* (default 1.0)
- `F`: Spread factor (default 0.7)
- `d_ij`: Distance in hops from *j* to *i*

**Algorithm**:
- BFS traversal from active chunks to target
- Shortest path distance used if multiple paths exist
- Maximum 3 hops (configurable)
- Activation additive across multiple sources

**Special Cases**:
- No path to target: Returns 0.0
- Circular dependencies: Handled by visited tracking, uses shortest path
- Multiple paths: Sum activation from all source chunks

**Literature Source**: Anderson (1983), *A spreading activation theory of memory*, Journal of Verbal Learning and Verbal Behavior, 22(3), 261-295

**Code Location**: `packages/core/src/aurora_core/activation/spreading.py`

---

### 3. Context Boost

**Formula**:
```
Context = boost_factor × (|keywords_chunk ∩ keywords_query| / |keywords_query|)
```

**Parameters**:
- `boost_factor`: Maximum boost (default 0.5)
- `keywords_chunk`: Set of keywords extracted from chunk
- `keywords_query`: Set of keywords from user query
- `∩`: Set intersection (matching keywords)
- `| |`: Set cardinality (count)

**Keyword Extraction**:
- Lowercase, alphanumeric only
- Stop words removed ('the', 'a', 'an', etc.)
- Programming terms retained ('if', 'for', 'class', 'def', 'return')

**Special Cases**:
- Perfect match (100% overlap): Returns `boost_factor`
- No match: Returns 0.0
- Empty query keywords: Returns 0.0

**Code Location**: `packages/core/src/aurora_core/activation/context_boost.py`

---

### 4. Decay Penalty

**Formula**:
```
Decay = -decay_factor × log10(max(grace_period, days_since_access))
```

**Parameters**:
- `decay_factor`: Penalty strength (default 0.5)
- `grace_period`: Days with no penalty (default 1 day)
- `days_since_access`: Days since last access
- `max_days`: Maximum days to consider (default 365, caps penalty)

**Behavior**:
- Logarithmic penalty (log10 scale)
- Grace period: No penalty within first N days
- Capped: Penalty stops increasing after max_days

**Special Cases**:
- Never accessed (`last_access=None`): Returns 0.0
- Within grace period: Returns 0.0
- Very old (>max_days): Penalty capped at `-decay_factor × log10(max_days)`

**Code Location**: `packages/core/src/aurora_core/activation/decay.py`

---

### 5. Type-Specific Decay (v1.1)

**Formula**:
```
effective_decay = base_decay(chunk_type) + churn_factor
Decay = -effective_decay × log10(days_since_access)
```

**Motivation**: Different types of code are remembered differently in human cognition:
- **Documentation** (KB): Stable "background radiation" - rarely forgotten
- **Class structures**: Architectural - moderately stable
- **Functions**: Behavioral - volatile, changes frequently
- **Reasoning traces**: Intermediate stability

**Type-Specific Base Decay Rates**:

| Chunk Type | Base Decay (d) | Cognitive Model | Example |
|------------|----------------|-----------------|---------|
| `kb` / `knowledge` | **0.05** | Declarative memory (sticky) | README.md, API docs |
| `class` | **0.20** | Structural memory (stable) | Class definitions |
| `function` / `method` | **0.40** | Procedural memory (volatile) | Function implementations |
| `code` | **0.40** | Generic code (volatile) | Untyped code chunks |
| `soar` | **0.30** | Reasoning traces (moderate) | Cached SOAR outputs |

**Behavior**:
- KB chunks decay **8× slower** than functions (0.05 vs 0.40)
- Classes are **2× more stable** than functions
- Unknown types fall back to global `decay_factor` (0.5)

**Example Impact** (30 days since access):
```
KB chunk:       -0.05 × log10(30) = -0.074  (very light penalty)
Class chunk:    -0.20 × log10(30) = -0.295  (light penalty)
Function chunk: -0.40 × log10(30) = -0.590  (moderate penalty)
```

**Configuration**:
```python
from aurora_core.activation.decay import DECAY_BY_TYPE

# Default map (customizable in config)
DECAY_BY_TYPE = {
    "kb": 0.05,
    "knowledge": 0.05,
    "class": 0.20,
    "function": 0.40,
    "method": 0.40,
    "code": 0.40,
    "soar": 0.30,
}
```

**Usage**:
```python
from aurora_core.activation.decay import DecayCalculator

decay = DecayCalculator()

# Type-aware decay
penalty = decay.calculate_with_metadata(
    last_access=some_timestamp,
    chunk_type="kb",  # Will use 0.05 decay rate
    commit_count=5
)
```

**Literature Basis**: While type-specific decay rates are an Aurora extension, they align with ACT-R's distinction between declarative memory (facts, slowly changing) and procedural memory (skills, rapidly updated).

**Code Location**: `packages/core/src/aurora_core/activation/decay.py` (lines 31-42)

---

### 6. Churn Factor (Stability Penalty) (v1.1)

**Formula**:
```
churn_factor = 0.1 × log10(commit_count + 1)
effective_decay = base_decay + churn_factor
```

**Motivation**: Code that changes frequently (high git commit count) is less stable and should decay faster. This models cognitive reality: volatile information is harder to remember reliably.

**Parameters**:
- `commit_count`: Number of git commits touching this chunk (from git blame)
- `CHURN_COEFFICIENT`: Multiplier for churn impact (default 0.1)

**Behavior**:
- Logarithmic relationship: 10× commits ≈ +0.1 additional decay
- Adds to base decay rate, making high-churn code decay faster
- Zero commits (new code): No churn penalty

**Churn Impact Examples**:

| Commit Count | Churn Factor | Interpretation |
|--------------|-------------|----------------|
| 5 commits | +0.070 | Low churn, stable code |
| 10 commits | +0.100 | Moderate churn |
| 50 commits | +0.170 | High churn, actively developed |
| 100 commits | +0.200 | Very high churn, volatile |
| 500 commits | +0.270 | Extreme churn, core infrastructure |

**Combined Example** (Function with 50 commits, 30 days old):
```
base_decay = 0.40 (function type)
churn_factor = 0.1 × log10(51) = 0.171
effective_decay = 0.40 + 0.171 = 0.571

Penalty = -0.571 × log10(30) = -0.843
```

Compare to low-churn function (5 commits):
```
effective_decay = 0.40 + 0.070 = 0.470
Penalty = -0.470 × log10(30) = -0.694
```

**Difference**: High-churn code gets -0.149 additional penalty (~21% more decay).

**Why This Works**:
- **Cognitive Model**: Unstable information (frequently changing code) interferes with long-term memory consolidation
- **Practical Benefit**: Recent stable code outranks old volatile code
- **Prevents Noise**: Legacy code with hundreds of commits doesn't dominate results

**Configuration**:
```python
from aurora_core.activation.decay import CHURN_COEFFICIENT

# Default: 0.1 (customizable in config)
# Higher values = stronger churn penalty
# Lower values = weaker churn impact
```

**Usage**:
```python
decay = DecayCalculator()

# Include churn factor in decay calculation
penalty = decay.calculate_with_metadata(
    last_access=last_access,
    chunk_type="function",
    commit_count=100  # High churn
)
```

**Code Location**: `packages/core/src/aurora_core/activation/decay.py` (lines 41, 283-287)

---

### 7. MMR Diversity Reranking (v1.1)

**Formula (Maximal Marginal Relevance)**:
```
MMR(d) = λ × relevance(d) - (1-λ) × max_similarity(d, selected)
```

**Motivation**: Prevent "echo chamber" where all top results are semantically similar. MMR balances relevance with diversity to cover multiple aspects of a query.

**Parameters**:
- `λ` (lambda): Diversity parameter (default 0.5)
  - λ=1.0: Pure relevance (no diversity)
  - λ=0.5: Balanced (default)
  - λ=0.0: Pure diversity (maximum variety)
- `relevance(d)`: Normalized hybrid score from tri-hybrid retrieval
- `max_similarity(d, selected)`: Highest cosine similarity to already-selected results

**Algorithm**:
1. Sort all candidates by hybrid score (BM25 + activation + semantic)
2. Select top result (highest hybrid score)
3. For remaining slots:
   - Calculate MMR score for each candidate
   - MMR = λ × hybrid_score - (1-λ) × max_cosine_similarity
   - Select candidate with highest MMR score
   - Repeat until k results selected

**Behavior**:
- **λ=1.0**: Identical to standard retrieval (pure relevance)
- **λ=0.5**: Second result is chosen to balance relevance AND dissimilarity to first
- **λ=0.0**: Maximally diverse results (may sacrifice relevance)

**Example Scenario**:

Query: "authentication"

**Without MMR** (pure relevance):
1. `auth/login.py::authenticate()` (score 0.95)
2. `auth/login.py::verify_password()` (score 0.93)
3. `auth/login.py::hash_password()` (score 0.91)
4. `auth/session.py::create_session()` (score 0.89)
5. `auth/oauth.py::oauth_login()` (score 0.87)

*Problem*: First 3 results are all from same file, same topic (password handling).

**With MMR** (λ=0.5):
1. `auth/login.py::authenticate()` (score 0.95, selected first)
2. `auth/session.py::create_session()` (score 0.89, diverse from #1)
3. `auth/oauth.py::oauth_login()` (score 0.87, diverse from #1 and #2)
4. `middleware/auth_middleware.py::check_auth()` (score 0.85, diverse perspective)
5. `models/user.py::User.permissions` (score 0.83, data model view)

*Benefit*: Results cover login, sessions, OAuth, middleware, and data models.

**Performance**:
- Computational cost: O(k²) where k = top_k results (typically 10-20)
- Requires embeddings (cosine similarity calculation)
- For k=10: ~45 similarity comparisons (negligible)

**Usage**:
```python
from aurora_context_code.semantic import HybridRetriever

retriever = HybridRetriever(store, engine, provider)

# Enable diversity
results = retriever.retrieve(
    query="authentication",
    top_k=10,
    diverse=True,      # Enable MMR reranking
    mmr_lambda=0.5     # Balance relevance and diversity
)
```

**Configuration**:
```python
from aurora_context_code.semantic import HybridConfig

config = HybridConfig(
    mmr_lambda=0.5  # Default diversity parameter
)
```

**Code Location**: `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` (lines 835-939)

**Literature Basis**: Carbonell & Goldstein (1998). "The use of MMR, diversity-based reranking for reordering documents and producing summaries." SIGIR '98.

---

### 5. Total Activation

**Formula**:
```
Total = BLA + Spreading + Context Boost - Decay
```

**Notes**:
- All components are additive (spreading) or subtractive (decay)
- Components can be individually enabled/disabled
- Each component is independently calculated
- Total can be positive or negative (logarithmic scale)

**Interpretation**:
- Higher (less negative) = More activated
- Typical range: -10.0 (very low) to +2.0 (very high)
- Retrieval threshold: ~0.3 (configurable)
- Comparison matters more than absolute value

---

## Component Details

### Base-Level Activation (BLA)

#### Mathematical Derivation

The BLA formula derives from the *declarative memory equation* in ACT-R theory:

```
BLA = ln(Σ_j t_j^(-d))
```

This represents the log odds that a memory trace will be needed, based on:
1. **Practice effect**: More presentations → higher activation
2. **Recency effect**: Recent presentations → higher activation
3. **Power-law decay**: Activation decays as t^(-d), not exponentially

#### Example Calculation

**Scenario**: Chunk accessed 3 times:
- 1 hour ago (3,600 seconds)
- 1 day ago (86,400 seconds)
- 7 days ago (604,800 seconds)

**Calculation** (d = 0.5):
```
t_1 = 3,600      → t_1^(-0.5) = 3,600^(-0.5) ≈ 0.01667
t_2 = 86,400     → t_2^(-0.5) = 86,400^(-0.5) ≈ 0.00340
t_3 = 604,800    → t_3^(-0.5) = 604,800^(-0.5) ≈ 0.00129

Sum = 0.01667 + 0.00340 + 0.00129 = 0.02136

BLA = ln(0.02136) ≈ -3.846
```

**Interpretation**:
- Negative activation is normal (logarithmic scale)
- Recent access (1 hour) dominates the sum
- Multiple accesses compound to raise activation

#### Configuration Parameters

```python
from aurora_core.activation.base_level import BLAConfig

config = BLAConfig(
    decay_rate=0.5  # Standard ACT-R decay
    # Higher decay_rate → faster forgetting
    # Lower decay_rate → longer memory retention
)
```

**Decay Rate Effects**:
- `d = 0.3`: Slow decay, values long-term patterns
- `d = 0.5`: Standard ACT-R decay, balanced
- `d = 0.7`: Fast decay, prioritizes very recent access

---

### Spreading Activation

#### Graph-Based Propagation

Spreading activation models how thinking about one concept activates related concepts in semantic memory. In code:
- Viewing a function activates functions it calls
- Editing a class activates its parent classes
- Debugging activates code in the call stack

**Relationship Types**:
- `calls`: Function A calls function B
- `imports`: Module A imports module B
- `inherits`: Class A inherits from class B
- `defines`: File A defines class B
- `uses`: Function A uses variable B

#### Example Calculation

**Scenario**: Relationship graph:
```
chunk_A --[calls]--> chunk_B --[imports]--> chunk_C
```

**Calculate spreading from A to C** (F = 0.7):
```
Path: A → B → C
Distance: 2 hops

Spreading = W_A × F^2 = 1.0 × 0.7^2 = 0.49
```

**Multiple Sources**:
```
chunk_A --[1 hop]--> chunk_D
chunk_B --[2 hops]--> chunk_D

Active chunks: {A, B}

Spreading to D = W_A × 0.7^1 + W_B × 0.7^2
               = 1.0 × 0.7 + 1.0 × 0.49
               = 0.7 + 0.49
               = 1.19
```

#### Configuration Parameters

```python
from aurora_core.activation.spreading import SpreadingConfig

config = SpreadingConfig(
    spread_factor=0.7,  # Decay per hop
    max_hops=3,         # Maximum distance
    max_edges=1000      # Limit graph size
)
```

**Spread Factor Effects**:
- `F = 0.8`: Strong spreading, distant relationships matter
- `F = 0.7`: Balanced spreading (standard)
- `F = 0.5`: Weak spreading, only immediate neighbors matter

---

### Context Boost

#### Keyword-Based Relevance

Context boost captures how external cues (query keywords) make relevant memories more accessible. This mirrors how asking "Where did I put my keys?" activates memories associated with keys.

In code retrieval:
- Query: "database performance" → Activates chunks containing 'database', 'query', 'index', 'optimize'
- Current file: `auth.py` → Activates chunks containing 'auth', 'login', 'user', 'session'

#### Example Calculation

**Scenario**:
- Query keywords: `{'database', 'performance', 'optimize'}`
- Chunk keywords: `{'database', 'query', 'index', 'performance'}`

**Calculation** (boost_factor = 0.5):
```
Query keywords: 3 total
Matching keywords: {'database', 'performance'} = 2
Overlap ratio: 2 / 3 = 0.667

Context Boost = 0.5 × 0.667 ≈ 0.333
```

**Interpretation**:
- 67% of query keywords found in chunk
- Context boost adds 0.333 to total activation
- Higher overlap → higher boost

#### Configuration Parameters

```python
from aurora_core.activation.context_boost import ContextBoostConfig

config = ContextBoostConfig(
    boost_factor=0.5,              # Maximum boost
    enable_stop_words=True,        # Remove common words
    stop_words={'the', 'a', 'is'}, # Custom stop words
    programming_terms={'if', 'for', 'def'}  # Keep programming keywords
)
```

**Boost Factor Effects**:
- `boost = 0.3`: Low boost, prefer usage patterns over relevance
- `boost = 0.5`: Balanced boost (default)
- `boost = 1.0`: High boost, prioritize semantic match

---

### Decay Penalty

#### Staleness and Forgetting

Decay penalty models memory interference and forgetting. Chunks that haven't been accessed recently become harder to retrieve, reflecting:
- Code drift: Old code may be obsolete
- Context shift: Old code less relevant to current work
- Cognitive cost: Retrieving stale memories requires effort

#### Example Calculation

**Scenario**: Chunk last accessed 30 days ago

**Calculation** (decay_factor = 0.5, grace_period = 1 day):
```
Days since access: 30
Grace period: 1 day (no penalty if < 1 day)

Since 30 > 1:
Decay = -0.5 × log10(30)
      = -0.5 × 1.477
      ≈ -0.739
```

**Comparison**:
```
1 day:    -0.5 × log10(1) = 0.0   (within grace period)
10 days:  -0.5 × log10(10) = -0.5
100 days: -0.5 × log10(100) = -1.0
365 days: -0.5 × log10(365) = -1.28 (capped at max_days)
```

**Interpretation**:
- Logarithmic decay: Penalty grows slowly
- 1 day → 10 days: -0.5 penalty
- 10 days → 100 days: Additional -0.5 penalty (same change for 10× time)
- Capped at max_days to prevent extreme penalties

#### Configuration Parameters

```python
from aurora_core.activation.decay import DecayConfig

config = DecayConfig(
    decay_factor=0.5,        # Penalty strength
    grace_period_days=1,     # Days with no penalty
    max_days=365             # Cap penalty
)
```

**Decay Factor Effects**:
- `factor = 0.3`: Light penalty, tolerate stale code
- `factor = 0.5`: Moderate penalty (default)
- `factor = 0.8`: Heavy penalty, strongly prefer recent code

---

## Calculation Examples

### Example 1: High-Activation Chunk

**Scenario**: Frequently used, recent, relevant chunk
- **Access history**: 4 times (2h, 1d, 3d, 7d ago)
- **Last access**: 2 hours ago
- **Relationships**: 1 hop from active chunk
- **Keywords**: 50% match with query

**Step-by-Step Calculation**:

**1. Base-Level Activation**:
```
t_1 = 7,200 sec    → t_1^(-0.5) = 0.01179
t_2 = 86,400 sec   → t_2^(-0.5) = 0.00340
t_3 = 259,200 sec  → t_3^(-0.5) = 0.00196
t_4 = 604,800 sec  → t_4^(-0.5) = 0.00129

Sum = 0.01844
BLA = ln(0.01844) = -3.992
```

**2. Spreading Activation**:
```
Distance: 1 hop
Spreading = 1.0 × 0.7^1 = 0.700
```

**3. Context Boost**:
```
Overlap: 50%
Context = 0.5 × 0.5 = 0.250
```

**4. Decay Penalty**:
```
Days since access: 0.083 (2 hours)
Within grace period (1 day): No penalty
Decay = 0.0
```

**5. Total Activation**:
```
Total = -3.992 + 0.700 + 0.250 - 0.0
      = -3.042
```

**Result**: Activation of -3.042 is moderately high. This chunk will likely be retrieved (well above typical threshold of 0.3).

---

### Example 2: Low-Activation Chunk

**Scenario**: Rarely used, old, distant chunk
- **Access history**: 1 time (100 days ago)
- **Last access**: 100 days ago
- **Relationships**: 3 hops from active chunk
- **Keywords**: 25% match with query

**Step-by-Step Calculation**:

**1. Base-Level Activation**:
```
t_1 = 8,640,000 sec  → t_1^(-0.5) = 0.000340
BLA = ln(0.000340) = -8.292
```

**2. Spreading Activation**:
```
Distance: 3 hops
Spreading = 1.0 × 0.7^3 = 0.343
```

**3. Context Boost**:
```
Overlap: 25%
Context = 0.5 × 0.25 = 0.125
```

**4. Decay Penalty**:
```
Days since access: 100
Decay = -0.5 × log10(100) = -1.0
```

**5. Total Activation**:
```
Total = -8.292 + 0.343 + 0.125 - 1.0
      = -8.824
```

**Result**: Activation of -8.824 is very low. This chunk will not be retrieved unless the threshold is extremely permissive.

---

### Example 3: Comparison - Recency vs. Relevance

**Chunk A**: Recent but irrelevant
- Access history: 1 time (1 hour ago)
- Spreading: 0.0 (no relationships)
- Context: 0.0 (0% keyword match)
- Decay: 0.0 (within grace period)

**Calculation**:
```
BLA = ln(3600^(-0.5)) = -5.686
Total = -5.686 + 0.0 + 0.0 - 0.0 = -5.686
```

**Chunk B**: Older but relevant and connected
- Access history: 2 times (3 days, 10 days ago)
- Spreading: 1.4 (two 1-hop paths: 0.7 + 0.7)
- Context: 0.5 (100% keyword match)
- Decay: -0.239 (3 days old)

**Calculation**:
```
BLA = ln((259200^(-0.5)) + (864000^(-0.5))) = -5.658
Total = -5.658 + 1.4 + 0.5 - 0.239 = -3.997
```

**Winner**: Chunk B (-3.997 > -5.686)

**Lesson**: Relationships and relevance can outweigh recency. ACT-R balances multiple cognitive factors rather than relying on a single heuristic.

---

### Example 4: Cold Start (Never Accessed)

**Scenario**: New chunk with no access history
- **Access history**: Empty
- **Last access**: None
- **Relationships**: 2 hops from active chunk
- **Keywords**: 75% match with query

**Step-by-Step Calculation**:

**1. Base-Level Activation**:
```
No access history → BLA = 0.0 (neutral baseline)
```

**2. Spreading Activation**:
```
Distance: 2 hops
Spreading = 1.0 × 0.7^2 = 0.490
```

**3. Context Boost**:
```
Overlap: 75%
Context = 0.5 × 0.75 = 0.375
```

**4. Decay Penalty**:
```
Never accessed → Decay = 0.0
```

**5. Total Activation**:
```
Total = 0.0 + 0.490 + 0.375 - 0.0
      = 0.865
```

**Result**: Activation of 0.865 is quite high! Even without usage history, strong context match and relationships can bootstrap a chunk into retrieval.

**Best Practice**: Ensure new code has good docstrings (for keywords) and proper imports/calls (for relationships) to enable cold-start retrieval.

---

### Example 5: Type-Specific Decay (v1.1)

**Scenario**: Compare KB chunk vs Function chunk with same age

**KB Chunk** (`README.md`):
- Type: `kb`
- Last access: 30 days ago
- Access history: 2 times (30d, 90d ago)
- Commit count: 3

**Function Chunk** (`auth.py::login()`):
- Type: `function`
- Last access: 30 days ago
- Access history: 2 times (30d, 90d ago)
- Commit count: 3

**Calculation for KB Chunk**:
```
Type: kb → base_decay = 0.05
Churn: 0.1 × log10(4) = 0.060
Effective decay: 0.05 + 0.060 = 0.110

Decay = -0.110 × log10(30) = -0.162
```

**Calculation for Function Chunk**:
```
Type: function → base_decay = 0.40
Churn: 0.1 × log10(4) = 0.060
Effective decay: 0.40 + 0.060 = 0.460

Decay = -0.460 × log10(30) = -0.679
```

**Comparison**:
- KB penalty: -0.162
- Function penalty: -0.679
- **Difference**: Function has 4.2× heavier decay penalty

**Result**: Even with identical access patterns, the KB chunk decays much slower, reflecting its role as stable reference material.

---

### Example 6: Churn Factor (Stability) (v1.1)

**Scenario**: Two functions, same type and age, different commit histories

**Stable Function** (`utils.py::format_date()`):
- Type: `function`
- Last access: 30 days ago
- Commit count: 5

**Volatile Function** (`api.py::handle_request()`):
- Type: `function`
- Last access: 30 days ago
- Commit count: 100

**Stable Function Calculation**:
```
base_decay = 0.40 (function)
churn_factor = 0.1 × log10(6) = 0.078
effective_decay = 0.40 + 0.078 = 0.478

Decay = -0.478 × log10(30) = -0.706
```

**Volatile Function Calculation**:
```
base_decay = 0.40 (function)
churn_factor = 0.1 × log10(101) = 0.200
effective_decay = 0.40 + 0.200 = 0.600

Decay = -0.600 × log10(30) = -0.886
```

**Comparison**:
- Stable penalty: -0.706
- Volatile penalty: -0.886
- **Difference**: -0.180 additional penalty for volatile code

**Interpretation**: The volatile function decays ~25% faster due to churn. If both are accessed equally, the stable function will rank higher.

**Real-World Impact**:
- Stable utility functions stay accessible longer
- Rapidly changing API endpoints decay faster (reflects their volatility)
- Core infrastructure with hundreds of commits doesn't dominate results

---

### Example 7: MMR Diversity Reranking (v1.1)

**Scenario**: Search for "database optimization"

**Standard Retrieval** (sorted by hybrid score):
1. `db/query.py::optimize_query()` - Score 0.95, Embedding [0.9, 0.1, 0.0]
2. `db/query.py::analyze_plan()` - Score 0.93, Embedding [0.88, 0.12, 0.02] (very similar to #1)
3. `db/index.py::create_index()` - Score 0.85, Embedding [0.3, 0.7, 0.1] (different topic)
4. `db/cache.py::cache_results()` - Score 0.82, Embedding [0.1, 0.2, 0.9] (different topic)

**Problem**: Top 2 results are nearly identical (cosine similarity ≈ 0.98).

**MMR Reranking** (λ=0.5):

**Step 1**: Select #1 (highest score)
```
Selected: [optimize_query]
```

**Step 2**: Calculate MMR for remaining candidates

For `analyze_plan()`:
```
Relevance: 0.93
Similarity to selected: cosine([0.88, 0.12, 0.02], [0.9, 0.1, 0.0]) ≈ 0.98
Diversity: 1 - 0.98 = 0.02

MMR = 0.5 × 0.93 + 0.5 × 0.02 = 0.465 + 0.010 = 0.475
```

For `create_index()`:
```
Relevance: 0.85
Similarity to selected: cosine([0.3, 0.7, 0.1], [0.9, 0.1, 0.0]) ≈ 0.35
Diversity: 1 - 0.35 = 0.65

MMR = 0.5 × 0.85 + 0.5 × 0.65 = 0.425 + 0.325 = 0.750
```

For `cache_results()`:
```
Relevance: 0.82
Similarity to selected: cosine([0.1, 0.2, 0.9], [0.9, 0.1, 0.0]) ≈ 0.12
Diversity: 1 - 0.12 = 0.88

MMR = 0.5 × 0.82 + 0.5 × 0.88 = 0.410 + 0.440 = 0.850
```

**Step 2 Winner**: `cache_results()` (MMR=0.850)

**Final MMR-Reranked Results**:
1. `db/query.py::optimize_query()` (selected first)
2. `db/cache.py::cache_results()` (diverse perspective on optimization)
3. `db/index.py::create_index()` (another diverse approach)
4. `db/query.py::analyze_plan()` (selected last, too similar to #1)

**Benefit**: Results now cover query optimization, caching, and indexing - three different approaches to database optimization.

**Lambda Effect**:
- λ=1.0 (pure relevance): Standard order (1, 2, 3, 4)
- λ=0.5 (balanced): Reranked order (1, 4, 3, 2)
- λ=0.0 (pure diversity): Would maximize dissimilarity (1, 4, 3, 2 but stronger preference for diverse)

---

## Integration Formula

### Combined Activation Equation

AURORA calculates total activation by integrating all four components:

```
Total(chunk, query, active_chunks, time) =
    BLA(chunk.access_history, time, d)
  + Spreading(chunk, active_chunks, graph, F, max_hops)
  + Context(chunk.keywords, query.keywords, boost)
  - Decay(chunk.last_access, time, factor, grace, max_days)
```

### Component Weights

All components have equal weight by default, but you can adjust relative importance through configuration:

| Component | Default Weight | Adjust By | Effect |
|-----------|---------------|-----------|--------|
| BLA | 1.0× | Decay rate `d` | Lower d → higher BLA → more weight |
| Spreading | 1.0× | Spread factor `F` | Higher F → stronger spread → more weight |
| Context | 1.0× | Boost factor | Higher boost → more weight on relevance |
| Decay | -1.0× | Decay factor | Higher factor → heavier penalty |

### Configuration Philosophy

**Balanced (DEFAULT)**: Equal weight to all factors
```python
BLA weight ≈ Spreading ≈ Context ≈ Decay
```

**Recency-Biased (AGGRESSIVE)**: Prioritize recent activity
```python
BLA weight > Decay >> Context > Spreading
(Lower d, higher decay factor, higher context boost)
```

**Relationship-Focused**: Prioritize code structure
```python
Spreading >> BLA ≈ Context > Decay
(Higher F, more hops, lower decay penalty)
```

**Semantic-Focused (CONTEXT_FOCUSED)**: Prioritize keyword match
```python
Context >> BLA ≈ Spreading > Decay
(Higher boost factor, keep d/F moderate)
```

---

## Usage Guide

### Basic Usage

#### 1. Calculate Activation for a Single Chunk

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

#### 2. Retrieve Top-N Activated Chunks

```python
from aurora_core.activation.retrieval import ActivationRetriever, RetrievalConfig
from aurora_core.activation.spreading import RelationshipGraph, Relationship

# Setup retriever
config = RetrievalConfig(
    threshold=0.0,      # No filtering
    max_results=10,     # Top 10 chunks
    include_components=True
)
retriever = ActivationRetriever(engine, config)

# Build relationship graph
relationships = [
    Relationship(source="chunk_1", target="chunk_2", rel_type="calls"),
    Relationship(source="chunk_2", target="chunk_3", rel_type="imports"),
]
graph = RelationshipGraph(relationships=relationships)

# Retrieve top chunks
results = retriever.retrieve(
    chunks=all_chunks,                      # List of chunks from store
    query_keywords={'database', 'optimize'},
    active_chunk_ids={'chunk_1'},           # Currently viewing
    graph=graph,
    reference_time=now
)

# Display results
for i, result in enumerate(results, 1):
    print(f"{i}. {result.chunk_id} → {result.activation:.3f}")
```

### Advanced Usage

#### 3. Custom Configuration

```python
from aurora_core.activation.engine import ActivationEngine, ActivationConfig
from aurora_core.activation.base_level import BLAConfig
from aurora_core.activation.spreading import SpreadingConfig
from aurora_core.activation.context_boost import ContextBoostConfig
from aurora_core.activation.decay import DecayConfig

# Build custom configuration
config = ActivationConfig(
    bla_config=BLAConfig(decay_rate=0.4),
    spreading_config=SpreadingConfig(
        spread_factor=0.75,
        max_hops=4,
        max_edges=2000
    ),
    context_config=ContextBoostConfig(
        boost_factor=0.6,
        enable_stop_words=True
    ),
    decay_config=DecayConfig(
        decay_factor=0.3,
        grace_period_days=7,
        max_days=730
    ),
    enable_bla=True,
    enable_spreading=True,
    enable_context=True,
    enable_decay=True
)

engine = ActivationEngine(config)
```

#### 4. Explain Activation Scores

```python
# Calculate activation
result = engine.calculate_total(
    access_history=access_history,
    last_access=last_access,
    spreading_activation=0.7,
    chunk_keywords=chunk_keywords,
    query_keywords=query_keywords,
    reference_time=now
)

# Get explanation
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
    - Overlap: 50.0% (2/4 keywords match)
    - Formula: 0.5 * 0.5 = 0.250

  Decay Penalty: 0.000
    - Last access: 1.0 hours ago
    - Within grace period: No penalty

  Total Activation: -2.562
```

---

#### 5. MMR Diversity Reranking (v1.1)

```python
from aurora_context_code.semantic import HybridRetriever, HybridConfig

# Create retriever with MMR support
config = HybridConfig(mmr_lambda=0.5)  # Balanced diversity
retriever = HybridRetriever(store, engine, provider, config)

# Standard retrieval (no diversity)
standard_results = retriever.retrieve(
    query="authentication",
    top_k=10
)

# Diverse retrieval (MMR reranking)
diverse_results = retriever.retrieve(
    query="authentication",
    top_k=10,
    diverse=True  # Enable MMR reranking
)

# Custom diversity control
very_diverse_results = retriever.retrieve(
    query="authentication",
    top_k=10,
    diverse=True,
    mmr_lambda=0.3  # More diversity, less relevance weight
)

print("Standard results (may have redundancy):")
for r in standard_results[:5]:
    print(f"  {r['chunk_id']} - {r['hybrid_score']:.3f}")

print("\nDiverse results (covers multiple aspects):")
for r in diverse_results[:5]:
    print(f"  {r['chunk_id']} - {r['hybrid_score']:.3f}")
```

**When to Use MMR**:
- ✅ Exploratory queries: "How does auth work?" (want varied perspectives)
- ✅ Research tasks: "database optimization techniques" (want multiple approaches)
- ✅ Debugging unknown issues: "memory leak" (want different potential causes)
- ❌ Specific searches: "UserManager.login function" (want exact match, not variety)
- ❌ Follow-up queries: Already know what you need

---

#### 6. Type-Specific Decay with Churn (v1.1)

```python
from aurora_core.activation.decay import DecayCalculator, DECAY_BY_TYPE
from datetime import datetime, timedelta, timezone

decay_calc = DecayCalculator()

# Calculate decay for different chunk types
now = datetime.now(timezone.utc)
last_access = now - timedelta(days=30)

# KB chunk (stable documentation)
kb_decay = decay_calc.calculate_with_metadata(
    last_access=last_access,
    chunk_type="kb",
    commit_count=5
)

# Function chunk (volatile code)
func_decay = decay_calc.calculate_with_metadata(
    last_access=last_access,
    chunk_type="function",
    commit_count=50  # High churn
)

# Class chunk (structural, moderate stability)
class_decay = decay_calc.calculate_with_metadata(
    last_access=last_access,
    chunk_type="class",
    commit_count=15
)

print(f"KB decay:       {kb_decay:.3f}")      # -0.189
print(f"Function decay: {func_decay:.3f}")     # -0.843
print(f"Class decay:    {class_decay:.3f}")    # -0.351

# Get detailed explanation
explanation = decay_calc.explain_decay_with_metadata(
    last_access=last_access,
    chunk_type="function",
    commit_count=50
)

print(f"\nDecay Breakdown:")
print(f"  Base decay (function): {explanation['base_decay']:.3f}")
print(f"  Churn penalty: {explanation['churn_penalty']:.3f}")
print(f"  Effective decay: {explanation['effective_decay']:.3f}")
print(f"  Final penalty: {explanation['penalty']:.3f}")
```

**Custom Decay Maps**:
```python
# Define custom type-specific decay rates
custom_decay_map = {
    "kb": 0.03,        # Even stickier docs
    "api": 0.60,       # APIs change frequently
    "test": 0.70,      # Tests are very volatile
    "config": 0.10,    # Config is relatively stable
}

# Use custom map
penalty = decay_calc.calculate_with_metadata(
    last_access=last_access,
    chunk_type="api",
    commit_count=100,
    decay_by_type=custom_decay_map  # Override defaults
)
```

---

## Configuration

### Preset Configurations

AURORA provides 5 preset configurations optimized for common use cases:

#### 1. DEFAULT (Balanced)

```python
from aurora_core.activation.engine import DEFAULT_CONFIG, ActivationEngine

engine = ActivationEngine(DEFAULT_CONFIG)
```

**Parameters**:
- BLA decay: 0.5 (standard ACT-R)
- Spread factor: 0.7, max 3 hops
- Context boost: 0.5
- Decay: -0.5 × log10(days), 1-day grace

**Best For**: General-purpose coding, balanced memory/relevance

---

#### 2. AGGRESSIVE (Recency-Biased)

```python
from aurora_core.activation.engine import AGGRESSIVE_CONFIG

engine = ActivationEngine(AGGRESSIVE_CONFIG)
```

**Parameters**:
- BLA decay: 0.3 (slower decay, favors recent)
- Spread factor: 0.8 (stronger spread)
- Context boost: 0.8 (high relevance)
- Decay: -0.8 × log10(days) (heavy staleness penalty)

**Best For**: Real-time coding, active development, prioritize recent edits

---

#### 3. CONSERVATIVE (Stability)

```python
from aurora_core.activation.engine import CONSERVATIVE_CONFIG

engine = ActivationEngine(CONSERVATIVE_CONFIG)
```

**Parameters**:
- BLA decay: 0.7 (faster decay, penalizes infrequent)
- Spread factor: 0.6 (weaker spread)
- Context boost: 0.3 (lower relevance)
- Decay: -0.3 × log10(days) (gentle penalty)

**Best For**: Stable codebases, avoid over-retrieval, maintenance mode

---

#### 4. BLA_FOCUSED (Usage History)

```python
from aurora_core.activation.engine import BLA_FOCUSED_CONFIG

engine = ActivationEngine(BLA_FOCUSED_CONFIG)
```

**Parameters**:
- BLA decay: 0.4
- Spreading: **DISABLED**
- Context boost: 0.3
- Decay: -0.6 × log10(days)

**Best For**: Simple projects, flat file structures, no complex relationships

---

#### 5. CONTEXT_FOCUSED (Semantic Match)

```python
from aurora_core.activation.engine import CONTEXT_FOCUSED_CONFIG

engine = ActivationEngine(CONTEXT_FOCUSED_CONFIG)
```

**Parameters**:
- BLA decay: 0.6
- Spread factor: 0.5 (weak spread)
- Context boost: **1.0** (double normal)
- Decay: -0.4 × log10(days)

**Best For**: Documentation search, keyword-heavy queries, semantic similarity

---

### Tuning Guidelines

| Use Case | Recommended Config | Key Adjustments |
|----------|-------------------|-----------------|
| Active development | AGGRESSIVE | Low d, high decay factor |
| Mature codebase | CONSERVATIVE | High d, low decay factor |
| Debugging (follow call chain) | AGGRESSIVE | High spread factor, more hops |
| Documentation search | CONTEXT_FOCUSED | High context boost |
| Flat project structure | BLA_FOCUSED | Disable spreading |
| Long-term project memory | Custom | Low d, low decay factor, long grace period |

---

### Type-Specific Decay Configuration (v1.1)

#### Default Type-Decay Map

```python
from aurora_core.activation.decay import DECAY_BY_TYPE, CHURN_COEFFICIENT

# Built-in default rates
print(DECAY_BY_TYPE)
# {
#     "kb": 0.05,
#     "knowledge": 0.05,
#     "class": 0.20,
#     "function": 0.40,
#     "method": 0.40,
#     "code": 0.40,
#     "soar": 0.30,
# }

print(f"Churn coefficient: {CHURN_COEFFICIENT}")  # 0.1
```

#### Customizing Decay Rates

**Via Configuration File** (`~/.aurora/config.json` or `.aurora/config.json`):
```json
{
  "activation": {
    "decay_by_type": {
      "kb": 0.03,
      "class": 0.15,
      "function": 0.50,
      "api": 0.60,
      "test": 0.70
    },
    "churn_coefficient": 0.15
  }
}
```

**Programmatically**:
```python
from aurora_core.activation.decay import DecayCalculator

# Pass custom decay map to each calculation
custom_map = {
    "kb": 0.03,
    "function": 0.50,
    "test": 0.70,
}

decay = DecayCalculator()
penalty = decay.calculate_with_metadata(
    last_access=timestamp,
    chunk_type="test",
    commit_count=20,
    decay_by_type=custom_map  # Use custom map
)
```

#### Tuning Guidelines

| Use Case | Decay Map Adjustments |
|----------|----------------------|
| Prioritize documentation | Lower `kb` rate (0.03), keep functions high |
| Stable codebase | Lower all rates by 20-30% |
| Rapid development | Higher function/method rates (0.60-0.80) |
| Ignore churn | Set `churn_coefficient = 0.0` |
| Strong stability penalty | Set `churn_coefficient = 0.2` |

**Effect of Adjustments**:
- **Lower decay rate**: Chunk stays active longer after last access
- **Higher decay rate**: Chunk decays faster, prioritizes recent usage
- **Higher churn coefficient**: Git commit history has stronger influence
- **Lower churn coefficient**: Git history has weaker influence

---

### MMR Configuration (v1.1)

#### Global MMR Settings

**Via Configuration File**:
```json
{
  "activation": {
    "mmr_lambda": 0.5
  },
  "context": {
    "code": {
      "hybrid_weights": {
        "bm25": 0.3,
        "activation": 0.3,
        "semantic": 0.4
      }
    }
  }
}
```

**Programmatically**:
```python
from aurora_context_code.semantic import HybridConfig, HybridRetriever

# Set default MMR lambda in config
config = HybridConfig(
    mmr_lambda=0.7  # Favor relevance over diversity
)

retriever = HybridRetriever(store, engine, provider, config)

# Uses config default (0.7) when diverse=True
results = retriever.retrieve(query, top_k=10, diverse=True)
```

#### Per-Query MMR Control

```python
# Override MMR lambda per query
results = retriever.retrieve(
    query="authentication",
    top_k=10,
    diverse=True,
    mmr_lambda=0.3  # High diversity for this query
)
```

#### Lambda Tuning Guide

| Lambda (λ) | Behavior | Use When |
|------------|----------|----------|
| **1.0** | Pure relevance (no diversity) | Specific searches, known target |
| **0.7-0.9** | Light diversity | Prefer accuracy, tolerate some redundancy |
| **0.5** (default) | Balanced | General exploration, balanced coverage |
| **0.3-0.4** | High diversity | Research tasks, brainstorming |
| **0.0-0.2** | Maximum diversity | Discovering unknown patterns, broad coverage |

**Recommendations**:
- **Default (0.5)**: Good for most use cases
- **Debugging**: 0.3-0.4 (want varied potential causes)
- **Code review**: 0.7-0.8 (want relevant code, some variety)
- **Learning new codebase**: 0.3-0.5 (want broad understanding)
- **Finding specific function**: 1.0 or `diverse=False` (no need for diversity)

---

## Performance

### Benchmarks

AURORA's activation system is optimized for large codebases:

| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| Single activation calculation | <1ms | ~0.3ms | ✓ |
| Batch 100 chunks | <10ms | ~8ms | ✓ |
| Batch 1K chunks | <50ms | ~42ms | ✓ |
| Batch 10K chunks | <500ms | ~380ms | ✓ |
| Graph cache hit | <1ms | <1ms | ✓ |

**Test Environment**: Standard laptop (Intel i7, 16GB RAM)

### Optimization Strategies

**1. Threshold Filtering**: Skip low-activation chunks early
```python
config = RetrievalConfig(threshold=-2.0)  # Only chunks with activation > -2.0
```

**2. Graph Caching**: Rebuild relationship graph every N retrievals
```python
from aurora_core.activation.graph_cache import GraphCache
cache = GraphCache(rebuild_interval=100)
```

**3. Batch Processing**: Calculate activations in batches
```python
results = retriever.retrieve(chunks=large_list, batch_size=1000)
```

**4. Component Disabling**: Turn off unused components
```python
config = ActivationConfig(enable_spreading=False)  # No relationships
```

### Memory Usage

| Data | Memory per 10K Chunks | Notes |
|------|----------------------|-------|
| Access history | ~5MB | JSON arrays in SQLite |
| Relationship graph | ~15MB | Adjacency list |
| Cached activations | ~2MB | LRU cache (10-min TTL) |
| **Total** | **~22MB** | Well under 100MB target |

---

## Validation

### Literature Verification

AURORA's implementation has been validated against published ACT-R examples:

**Validation Report**: [docs/actr-formula-validation.md](./actr-formula-validation.md)

**Summary**:
- 20 literature validation tests
- 100% pass rate
- <5% deviation from published values
- 5 primary references (Anderson 2007, Anderson & Lebiere 1998, Anderson 1983)

### Test Coverage

| Module | Tests | Coverage | Status |
|--------|-------|----------|--------|
| base_level.py | 24 | 90.91% | ✓ |
| spreading.py | 57 | 98.91% | ✓ |
| context_boost.py | 19 | 98.92% | ✓ |
| decay.py | 18 | 93.83% | ✓ |
| engine.py | 48 | 100% | ✓ |
| retrieval.py | 41 | 94.29% | ✓ |
| **Total** | **291** | **86.99%** | ✓ |

**Target**: ≥85% coverage ✓ **ACHIEVED**

### Cognitive Principles Validated

1. **Frequency Principle** ✓: More practice → higher activation
2. **Recency Principle** ✓: Recent access → higher activation
3. **Context Principle** ✓: Relevance → higher activation
4. **Associative Principle** ✓: Related chunks → spreading boost

---

## Troubleshooting

### Common Issues

#### Issue 1: All Activations Are Negative

**Symptom**: Every chunk has negative activation scores.

**Explanation**: This is **normal and expected**. ACT-R uses logarithmic scales, where negative values are common. What matters is **relative comparison**.

**Solution**: Compare activations to find the highest (least negative) chunks. Set retrieval threshold based on your needs (e.g., -2.0).

---

#### Issue 2: Spreading Activation Always Zero

**Symptom**: `result.spreading == 0.0` for all chunks.

**Possible Causes**:
1. No relationships in graph
2. Target chunk not connected to active chunks
3. Distance exceeds `max_hops`
4. Spreading disabled in configuration

**Solution**:
```python
# Check graph has relationships
print(f"Graph has {len(graph.relationships)} relationships")

# Check active chunk IDs are valid
print(f"Active chunks: {active_chunk_ids}")

# Check max_hops is sufficient
config = SpreadingConfig(max_hops=5)  # Increase if needed

# Verify spreading is enabled
config = ActivationConfig(enable_spreading=True)
```

---

#### Issue 3: Context Boost Always Zero

**Symptom**: `result.context_boost == 0.0` for all chunks.

**Possible Causes**:
1. No keyword overlap between chunk and query
2. Keywords not extracted properly
3. Stop words removed all keywords
4. Context boost disabled

**Solution**:
```python
# Debug keyword extraction
print(f"Chunk keywords: {chunk_keywords}")
print(f"Query keywords: {query_keywords}")
print(f"Overlap: {chunk_keywords & query_keywords}")

# Verify context is enabled
config = ActivationConfig(enable_context=True)

# Adjust boost factor if needed
config = ContextBoostConfig(boost_factor=1.0)  # Increase boost
```

---

#### Issue 4: Activation Scores Too Low

**Symptom**: All chunks have very low activation (e.g., < -8.0), nothing retrieved.

**Possible Causes**:
1. Chunks rarely accessed (low BLA)
2. Heavy decay penalty (old chunks)
3. Threshold too strict

**Solution**:
```python
# Lower retrieval threshold
config = RetrievalConfig(threshold=-5.0)  # More permissive

# Reduce decay penalty
decay_config = DecayConfig(decay_factor=0.3)  # Lighter penalty

# Increase grace period
decay_config = DecayConfig(grace_period_days=7)  # Longer grace

# Use AGGRESSIVE config
engine = ActivationEngine(AGGRESSIVE_CONFIG)
```

---

#### Issue 5: Activation Scores Too High

**Symptom**: Too many chunks retrieved, low precision.

**Possible Causes**:
1. Very frequent access (high BLA)
2. Weak decay penalty
3. Threshold too permissive

**Solution**:
```python
# Raise retrieval threshold
config = RetrievalConfig(threshold=0.0)  # Stricter

# Increase decay penalty
decay_config = DecayConfig(decay_factor=0.8)  # Heavier penalty

# Use CONSERVATIVE config
engine = ActivationEngine(CONSERVATIVE_CONFIG)
```

---

### Debugging Techniques

#### 1. Use explain() Method

```python
result = engine.calculate_total(...)
explanation = engine.explain(result)
print(explanation)  # Shows detailed breakdown
```

#### 2. Inspect Components Individually

```python
# Calculate each component separately
from aurora_core.activation.base_level import BaseLevelActivation
from aurora_core.activation.spreading import SpreadingActivation
from aurora_core.activation.context_boost import ContextBoost
from aurora_core.activation.decay import DecayCalculator

bla_calc = BaseLevelActivation(BLAConfig())
bla = bla_calc.calculate(access_history, now)
print(f"BLA alone: {bla}")

# ... repeat for other components
```

#### 3. Compare Configurations

```python
# Test different configs side-by-side
configs = [DEFAULT_CONFIG, AGGRESSIVE_CONFIG, CONSERVATIVE_CONFIG]
for config in configs:
    engine = ActivationEngine(config)
    result = engine.calculate_total(...)
    print(f"{config.name}: {result.total:.3f}")
```

#### 4. Validate Input Data

```python
# Check access history is non-empty
assert len(access_history) > 0, "Access history is empty"

# Check timestamps are in the past
assert all(entry.timestamp < now for entry in access_history)

# Check keywords are extracted
assert len(chunk_keywords) > 0, "No chunk keywords"
assert len(query_keywords) > 0, "No query keywords"
```

---

## References

### Primary Literature

1. **Anderson, J. R. (2007)**. *How Can the Human Mind Occur in the Physical Universe?*
   Oxford University Press. ISBN: 978-0195324259
   - Chapter 3: The Adaptive Character of Thought
   - Base-level activation formula (p. 74)
   - Power law of practice and forgetting (p. 76)

2. **Anderson, J. R., & Lebiere, C. (1998)**. *The Atomic Components of Thought*.
   Lawrence Erlbaum Associates. ISBN: 978-0805824346
   - Chapter 2: The Activation Mechanism (p. 47)
   - Multiple access patterns and context effects

3. **Anderson, J. R. (1983)**. *A spreading activation theory of memory*.
   Journal of Verbal Learning and Verbal Behavior, 22(3), 261-295.
   DOI: 10.1016/S0022-5371(83)90201-3
   - Spreading activation mechanism (Figure 2, p. 272)
   - Distance-dependent decay (p. 275)

4. **Anderson, J. R., Bothell, D., Byrne, M. D., Douglass, S., Lebiere, C., & Qin, Y. (2004)**.
   *An integrated theory of the mind*.
   Psychological Review, 111(4), 1036-1060.
   DOI: 10.1037/0033-295X.111.4.1036
   - Unified ACT-R architecture
   - Cognitive principles and validation

### AURORA Documentation

- [ACT-R Formula Validation Report](./actr-formula-validation.md) - Literature verification
- [Activation Usage Examples](./examples/activation_usage.md) - 30 practical code examples
- [Performance Benchmarks](./performance/benchmark-results.md) - Scalability analysis
- [SOAR Architecture](./SOAR_ARCHITECTURE.md) - Integration with reasoning pipeline

### External Resources

- [ACT-R Website](http://act-r.psy.cmu.edu/) - Official ACT-R project at CMU
- [ACT-R Tutorial](http://act-r.psy.cmu.edu/software/) - Getting started with ACT-R
- [ACT-R Publications](http://act-r.psy.cmu.edu/publications/) - Research papers and books

---

## Appendices

### Appendix A: Formula Quick Reference

| Component | Formula | Key Parameters |
|-----------|---------|----------------|
| **BLA** | `ln(Σ t_j^(-d))` | d=0.5 (decay rate) |
| **Spreading** | `Σ (W_j × F^d_ij)` | F=0.7 (spread factor), max 3 hops |
| **Context** | `boost × (overlap / total)` | boost=0.5 |
| **Decay (Basic)** | `-factor × log10(days)` | factor=0.5, grace=1 day |
| **Type Decay (v1.1)** | `-[base(type) + churn] × log10(days)` | base: 0.05-0.40, churn=0.1×log10(commits+1) |
| **MMR (v1.1)** | `λ×relevance - (1-λ)×max_sim` | λ=0.5 (diversity parameter) |
| **Total** | `BLA + Spread + Context - Decay` | All additive/subtractive |

### Appendix B: Configuration Cheat Sheet

```python
# Balanced
DEFAULT_CONFIG

# Favor recent code
AGGRESSIVE_CONFIG  # Low d, high decay

# Favor stable patterns
CONSERVATIVE_CONFIG  # High d, low decay

# No relationships
BLA_FOCUSED_CONFIG  # Spreading disabled

# Keyword-heavy
CONTEXT_FOCUSED_CONFIG  # High context boost
```

### Appendix C: Typical Activation Ranges

| Range | Interpretation | Retrieval |
|-------|----------------|-----------|
| > +1.0 | Very high | Always retrieved |
| 0.0 to +1.0 | High | Usually retrieved |
| -2.0 to 0.0 | Moderate | Depends on threshold |
| -5.0 to -2.0 | Low | Rarely retrieved |
| < -5.0 | Very low | Almost never retrieved |

### Appendix D: Component Contribution Examples

**Typical Contributions**:
- BLA: -10.0 to -2.0 (negative, but less negative with more/recent access)
- Spreading: 0.0 to +2.0 (positive boost, 0.7^hop for each hop)
- Context: 0.0 to +0.5 (positive boost, 0.5 max for 100% match)
- Decay (standard): 0.0 to -2.0 (negative penalty, logarithmic with days)
- Decay (KB, v1.1): 0.0 to -0.5 (lighter penalty, sticky memory)
- Decay (function, v1.1): 0.0 to -2.5 (heavier penalty, volatile code)
- Churn Factor (v1.1): +0.07 to +0.27 (adds to decay, log scale)

**Example Breakdown (v1.0)**:
```
High Activation: BLA=-3.0, Spread=+1.4, Context=+0.5, Decay=-0.2 → Total=-1.3
Low Activation:  BLA=-8.0, Spread=+0.0, Context=+0.1, Decay=-1.0 → Total=-8.9
```

**Example Breakdown with Type-Specific Decay (v1.1)**:
```
KB (stable):     BLA=-3.0, Spread=+1.4, Context=+0.5, Decay=-0.16 (type:kb, 5 commits) → Total=-1.26
Function (low churn):   BLA=-3.0, Spread=+1.4, Context=+0.5, Decay=-0.71 (type:func, 5 commits) → Total=-1.81
Function (high churn):  BLA=-3.0, Spread=+1.4, Context=+0.5, Decay=-0.89 (type:func, 100 commits) → Total=-1.99
```

**MMR Impact (v1.1)**:
- Without MMR: Results 1-5 may have 0.95+ cosine similarity (redundant)
- With MMR (λ=0.5): Results 1-5 selected for diversity, typically <0.7 max similarity

---

## Changelog

### Version 1.1 (January 31, 2026)

**New Features**:
- ✨ **Type-Specific Decay**: Different decay rates for KB, classes, functions, etc.
  - KB chunks decay 8× slower than functions (0.05 vs 0.40)
  - Configurable via `DECAY_BY_TYPE` map
  - Falls back to global decay for unknown types

- ✨ **Churn Factor (Stability Penalty)**: Git commit history affects decay
  - Formula: `churn_factor = 0.1 × log10(commit_count + 1)`
  - High-churn code (100+ commits) decays ~25% faster
  - Models cognitive reality: volatile information harder to remember

- ✨ **MMR Diversity Reranking**: Prevent redundant results
  - Balances relevance and diversity (configurable λ parameter)
  - Opt-in via `diverse=True` parameter
  - Prevents "echo chamber" of similar results

**API Changes**:
- `DecayCalculator.calculate_with_metadata()` - New method for type-aware decay
- `DecayCalculator.explain_decay_with_metadata()` - Explanation with type/churn info
- `HybridRetriever.retrieve(..., diverse=True, mmr_lambda=0.5)` - MMR support
- `HybridConfig.mmr_lambda` - New configuration parameter

**Configuration**:
- New config section: `activation.decay_by_type`
- New config section: `activation.churn_coefficient`
- New config section: `activation.mmr_lambda`

**Documentation**:
- Added 3 new calculation examples (type decay, churn, MMR)
- Added usage examples for all new features
- Added configuration guides for type maps and MMR
- Updated formula reference with comprehensive coverage

**Code Locations**:
- `packages/core/src/aurora_core/activation/decay.py` - Type-specific decay implementation
- `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` - MMR implementation
- `packages/cli/src/aurora_cli/defaults.json` - Configuration schema

**Backward Compatibility**: ✅ Fully backward compatible
- Existing code continues to work unchanged
- New features are opt-in
- Default behavior preserves existing retrieval

---

### Version 1.0 (December 23, 2025)

**Initial Release**:
- ACT-R activation system implementation
- Base-level activation (BLA)
- Spreading activation
- Context boost
- Decay penalty
- 5 preset configurations
- 291 tests, 86.99% coverage
- Validated against ACT-R literature

---

**Document Version**: 1.1
**Status**: Production Ready
**Last Updated**: January 31, 2026
**Related Tasks**: Task 8.1, Task 8.2, v0.11.0 Memory Enhancement
**Validation Status**: ✅ Verified against ACT-R literature
**Test Coverage**: ✅ 291+ tests, 86.99%+ coverage

---

*For questions or feedback on this documentation, please refer to the AURORA project team.*
