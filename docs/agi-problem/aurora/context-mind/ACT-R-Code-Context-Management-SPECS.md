# ACT-R-Based Code Context Management System - SPECIFICATIONS

**Status**: Technical Specification (Input to PRD Process)
**Date**: December 8, 2025
**Version**: 1.0
**Purpose**: Define technical approach for intelligent code chunking using ACT-R + cAST

---

## 1. Problem Statement

### Core Challenge
Code context management systems face a fundamental bottleneck: **How to keep codebase context within LLM token budgets without losing critical code relationships.**

Current approaches:
- **AST/cAST-based chunking** (ChunkHound) solve structural integrity—chunks are well-defined, semantically meaningful
- **Embedding-based retrieval** (semantic search) solve finding relevant code
- **Neither solves prioritization under resource constraints**

When a codebase has 500 functions and a query is semantically similar to 50 of them:
- Include all 50? → 100k+ tokens, token budget explodes, LLM attention collapses
- Include top-10? → Which 10? Random? Similarity score? Both fail to capture true importance
- System should learn: "This developer always needs hash_password() with authenticate(), but rarely needs validate_password() in isolation"

### Why Current Approaches Fail

1. **Static Relevance Models**: Embedding-based similarity computed once; never changes
2. **No Learning Loop**: Retrieval failures don't improve future performance
3. **Attention Blindness**: LLMs show 13.9%-85% performance degradation with long context; recency bias ignores early code
4. **Dependency Explosion**: No graceful way to weight transitive dependencies (imports of imports of imports)
5. **Conversation Amnesia**: Each query treated independently; no session-level context

---

## 2. ACT-R Foundation: Cognitive Architecture Principles

### Core ACT-R Concepts

**Activation**: Each knowledge chunk has an activation level (range -2 to +1) determining retrieval speed and reliability.

**Base-Level Activation Decay**: Frequently used chunks have higher base activation. Unused chunks decay per power law (Ebbinghaus forgetting curve), modeling how humans forget.

**Context-Based Boosts**: Current context temporarily boosts related chunks' activation. Discussing "authentication" boosts all auth-related code.

**Spreading Activation**: Activated chunks boost related chunks via associative links. Activating "login function" spreads activation to "password validation," "user database," "session management."

### Why ACT-R is Ideal for Code Context

ACT-R was developed by John Robert Anderson (Carnegie Mellon) to model human information retrieval from memory. Code context management is *exactly* an information retrieval problem:

- Humans don't maintain static indexes of what they know
- They maintain activation levels that decay over time
- They boost activation based on context
- They spread activation via associations
- They learn from feedback

Code follows the same patterns:
- Frequently-used functions should stay "hot" in context
- Rarely-used code should "cool" and fade
- Current focus (auth module) should boost related code
- Dependencies should activate transitively
- System should learn which code tends to be needed together

---

## 3. Three-Layer Architecture

### Layer 1: cAST (Code Abstract Syntax Tree Chunking)

**Purpose**: Ensure chunks are meaningful semantic units; enable line-level change tracking via git

**Granularity**: FUNCTION-LEVEL (not file-level, not arbitrary tokens)

**Why Function-Level?**
- Large files (500+ lines) contain 10-20 unrelated functions
- File-level chunking destroys precision (includes unused code)
- Function-level enables token efficiency: query "password validation" → only `validate_password()`, not entire file
- Dependencies map to functions, not files
- Example: Python file with `authenticate()`, `deprecated_old_login()`, `reset_password()`, `validate_token()`. Query about auth needs only `authenticate()` + `validate_token()`, not deprecated code

**How it works**:
1. Parse source code into Abstract Syntax Tree (AST) using tree-sitter parser
2. Recursively traverse AST to identify function/class boundaries
3. Create chunks at syntactic boundaries (functions, classes, modules, imports)
4. For each chunk, extract: name, source code, start_line, end_line, start_column, end_column
5. Explicitly track dependencies: which chunks call/import which other chunks
6. Never split semantic units (function always in one chunk)

**Output**: Well-defined chunk set with metadata:
```python
{
  'chunks': [
    {
      'name': 'authenticate',
      'type': 'function',
      'start_line': 45,
      'end_line': 52,
      'source_code': '...',
      'dependencies': ['validate_credentials', 'create_session']
    },
    {
      'name': 'validate_credentials',
      'type': 'function',
      'start_line': 54,
      'end_line': 60,
      'source_code': '...',
      'dependencies': []
    }
  ],
  'dependency_graph': {
    'edges': [
      ('authenticate', 'validate_credentials', 'calls'),
      ('authenticate', 'create_session', 'calls')
    ]
  }
}
```

**Example**:
```python
# Source code (auth.py)
def authenticate(username, password):
    result = validate_credentials(username, password)
    if result:
        session = create_session(username)
        return session
    return None

def validate_credentials(u, p):
    # validation logic
    pass

def create_session(u):
    # session logic
    pass

def reset_password(user_id):
    # password reset logic
    pass
```

**cAST chunks**:
```
Chunk 1: authenticate() [lines 45-52] (complete, unbroken)
         Dependencies: validate_credentials, create_session

Chunk 2: validate_credentials() [lines 54-60]
         Dependencies: (none)

Chunk 3: create_session() [lines 62-65]
         Dependencies: (none)

Chunk 4: reset_password() [lines 67-70]
         Dependencies: (none)

Dependency graph: authenticate → validate_credentials
                  authenticate → create_session
```

**Implementation: cAST is a Wrapper (Not a Library)**

cAST is a Python module we develop (~500-700 lines) that wraps tree-sitter:

```python
# cAST module structure
cAST/
├── __init__.py                    (50 lines - exports)
├── core.py                        (200 lines - main parser)
├── extractors.py                  (150 lines - function extraction)
├── dependencies.py                (100 lines - call/import tracking)
├── languages/
│   ├── python.py                  (100 lines - Python-specific)
│   ├── javascript.py              (100 lines - JavaScript-specific)
│   ├── go.py                      (100 lines - Go-specific)
│   └── __init__.py                (10 lines)
└── tests/
    ├── test_extraction.py         (100 lines)
    └── test_dependencies.py       (100 lines)

Total for MVP (Python + JavaScript): ~700 lines
```

**Dependencies**:
- **tree-sitter** (existing open-source library): AST parsing, language support
- **tree-sitter-python, tree-sitter-javascript, etc.** (existing): Language grammars
- Python 3.8+

**What cAST Does**:
1. **Parse code** → Use tree-sitter to build AST
2. **Extract functions** → Find all `function_definition` nodes in AST
3. **Get line ranges** → Record start_line/end_line from AST node positions
4. **Extract source** → Slice original source code by line range
5. **Find calls** → Walk AST, find `call` nodes, resolve function names
6. **Find imports** → Walk AST, find `import` nodes
7. **Build graph** → Create edges: function A → function B

**Example Usage**:
```python
from cAST import cAST

# Initialize parser for Python
ast = cAST(language='python')

# Parse a file
result = ast.parse_file('auth.py')

# Access chunks
for chunk in result['chunks']:
    print(f"{chunk['name']} at lines {chunk['start_line']}-{chunk['end_line']}")
    print(f"  Dependencies: {chunk['dependencies']}")

# Output:
# authenticate at lines 45-52
#   Dependencies: ['validate_credentials', 'create_session']
# validate_credentials at lines 54-60
#   Dependencies: []
# create_session at lines 62-65
#   Dependencies: []
# reset_password at lines 67-70
#   Dependencies: []
```

**Git + cAST Integration: Line-Level Change Tracking**

When git changes are detected, cAST enables precise function-level activation:

```python
# Step 1: Get git diff
# $ git diff --cached auth.py
# Output:
# @@ -45,10 +45,12 @@
# - if result:
# + if result and not expired:
# (Lines 45-52 modified)

# Step 2: Parse cAST
cAST_chunks = ast.parse_file('auth.py')
# Returns line ranges for each function

# Step 3: Map git diff lines → functions
git_diff_lines = [45, 46, 47, 48, 49, 50, 51, 52]  # Changed lines

for chunk in cAST_chunks['chunks']:
  changed_in_chunk = len([
    line for line in git_diff_lines
    if chunk['start_line'] <= line <= chunk['end_line']
  ])

  if changed_in_chunk > 0:
    magnitude = changed_in_chunk / (chunk['end_line'] - chunk['start_line'])
    # magnitude = 8 lines changed / 8 total lines = 1.0 (entire function)

    activation_boost = 0.3 * magnitude
    chunk['BLA'] += activation_boost

    print(f"{chunk['name']}: {changed_in_chunk}/{chunk['end_line']-chunk['start_line']} lines changed")

# Output:
# authenticate: 8/8 lines changed → BLA += 0.30
# validate_credentials: 0/6 lines changed → BLA += 0.0
# create_session: 0/3 lines changed → BLA += 0.0
# reset_password: 0/4 lines changed → BLA += 0.0
```

**Extending to Other Languages**

Adding a new language is straightforward (~100 lines per language):

```python
# To add Go: create cAST/languages/go.py
class GoExtractor:
    def extract_functions(self, tree):
        # Go-specific: look for FunctionDeclaration nodes
        # Return same chunk structure as Python/JS
        pass

    def extract_calls(self, tree):
        # Go-specific: look for CallExpression nodes
        pass

# Register in core.py:
EXTRACTORS = {
    'python': PythonExtractor(),
    'javascript': JavaScriptExtractor(),
    'go': GoExtractor(),  # New
}
```

**Benefits**:
- ✅ Chunks are semantically correct (functions as atomic units)
- ✅ Dependencies are explicit (call graph extracted)
- ✅ Works across languages (Python, JS, Go, Rust, Java, C++ via tree-sitter)
- ✅ Precise git integration (line ranges enable function-level diff mapping)
- ✅ Validated: +4.3 Recall@5 improvement vs. semantic chunking (ChunkHound benchmarks)
- ✅ Lightweight implementation (~700 lines for MVP)

### Layer 2: Semantic Embedding

**Purpose**: Compute semantic similarity between chunks

**How it works**:
1. Embed each chunk (cAST chunk, not arbitrary tokens)
2. Build similarity graph: which chunks are semantically related
3. Enable multi-hop retrieval: "password hashing" connects to authentication-related chunks

**Output**: Semantic relationship graph; enables finding related code

**Note**: This layer exists in current systems. We're not changing it. But it works *better* with good chunks (from cAST).

### Layer 3: ACT-R Activation

**Purpose**: Dynamically prioritize chunks based on usage patterns, context, and learning

**How it works**:

For each chunk `ci`, compute activation:
```
A(ci) = BLA(ci) + CB(ci) + SA(ci) - decay(ci)
```

Where:
- **BLA(ci)** = Base-Level Activation
  - How frequently is this chunk used?
  - Source: git history, test coverage, IDE telemetry
  - Example: frequently-called functions have high BLA

- **CB(ci)** = Context Boost
  - Is this chunk relevant to current query/focus?
  - Source: parsed query, current file, recent edits
  - Example: if developer is in `auth.py`, all auth functions get boosted

- **SA(ci)** = Spreading Activation
  - Are related chunks activated?
  - Spreads via dependency graph `D`
  - Formula: `SA(ci) = sum(A(cj) * spread_factor^distance(i,j))` for all related `cj`
  - Example: activate `authenticate()` → spreads to `validate_credentials()` and `create_session()`
  - Decay by distance: direct dependency 0.7x boost, 2-hop 0.49x, etc.

- **decay(ci)** = Time-Based Decay
  - How long since chunk was accessed?
  - Formula: `decay(ci) = -0.5 * log10(days_since_access)`
  - Popular code stays hot; old code cools

### Three-Layer Interaction

```
         User Query
             │
             ↓
      [Layer 2: Embedding]
      Find semantically similar chunks
      semantic_score(query, chunk)
             │
             ↓
      Narrow down to top candidates
      (e.g., 50 candidate chunks)
             │
             ↓
      [Layer 3: ACT-R]
      For each candidate, compute activation:
        - BLA: How often used?
        - CB: Relevant to current context?
        - SA: Related to other activated chunks?
        - decay: How old is it?
             │
             ↓
      Rank candidates by activation level
             │
             ↓
      [Layer 1: cAST]
      Select top-K chunks
      Respect token budget
      Ensure chunks are well-structured
             │
             ↓
      Return ranked context
      with highest-activation chunks
```

---

## 4. State Model and Data Structures

### Persistent State (Per Codebase)

```python
code_unit_state = {
  "name": str,                          # function/class/file name
  "ast_path": str,                      # path in dependency tree
  "base_activation": float,             # fundamental importance
  "last_access": datetime,              # when was it used?
  "frequency_count": int,               # how often accessed?
  "access_history": [(timestamp, duration), ...],
  "associative_links": {
    "imports": [(unit_id, strength), ...],
    "imports_from": [(unit_id, strength), ...],
    "calls": [(unit_id, strength), ...],
    "called_by": [(unit_id, strength), ...],
  },
  "embedding": vector,                  # semantic representation
  "metadata": {
    "is_deprecated": bool,
    "test_coverage": float,
    "lines_of_code": int,
    "language": str,
  }
}
```

### Dependency Graph

```python
dependency_graph = {
  "edges": [
    ("authenticate", "validate_credentials", "calls"),
    ("authenticate", "create_session", "calls"),
    ("validate_credentials", "database", "imports"),
  ],
  "forward_edges": defaultdict(list),   # who does X call?
  "reverse_edges": defaultdict(list),   # who calls X?
}
```

---

## 5. Event-Driven Activation Updates

### Events That Modify Activation

| Event | Action | Impact |
|-------|--------|--------|
| **File opened in IDE** | Boost opened file + related imports | Context boost |
| **Function edited** | Increase base activation | Frequency increase |
| **Tests run** | Boost tested code | Frequency increase |
| **Query issued** | Boost retrieved chunks | Context boost |
| **Code generated** | Boost chunks used in generation | Positive feedback |
| **Generated code is correct** | Further boost used chunks | Reinforce |
| **Generated code is buggy** | Penalize missed chunks | Negative feedback |
| **Chunk retrieved but unused** | Decrease activation | False positive penalty |
| **Time passes** | Apply decay to all chunks | Natural forgetting |
| **Deprecation signal** | Accelerate decay | Manual reset |

### Learning Loop

```
Query arrives
    ↓
Retrieve context using Layer 1-3
    ↓
LLM generates code
    ↓
Code is executed/tested
    ↓
Did it work? ← Measure success
    ├─ YES: Reinforce chunks that were retrieved
    │       └─ Increase their base activation
    │       └─ Strengthen associative links
    │
    └─ NO: Identify missing chunks
            └─ Increase their base activation
            └─ Learn why they weren't retrieved
            └─ Adjust future retrieval
    ↓
Update activation state
    ↓
Next query benefits from learning
```

---

## 6. Retrieval Algorithm

### Input
- **query**: User question or code context
- **token_limit**: Available tokens for context
- **codebase**: All chunks + activation state
- **current_focus**: File/module user is viewing

### Algorithm

```python
def retrieve_context(query, token_limit, codebase, current_focus):

  # Step 1: Semantic candidate generation
  candidates = semantic_search(query, codebase.embeddings, top_k=100)
  # Returns: 100 most similar chunks by embedding

  # Step 2: Compute activation for each candidate
  activations = {}
  for chunk in candidates:

    # Base-level activation: how fundamental?
    bla = chunk.base_activation

    # Context boost: relevant to what user is doing?
    cb = context_boost(chunk, query, current_focus)

    # Spreading activation: related chunks activated?
    sa = 0
    for related_chunk in chunk.associative_links:
      related_activation = activations.get(related_chunk.id, 0)
      spread_distance = dependency_distance(chunk, related_chunk)
      sa += related_activation * (0.7 ** spread_distance)

    # Time-based decay: how old?
    time_decay = -0.5 * log10(days_since_access(chunk))

    # Total activation
    activations[chunk.id] = bla + cb + sa - time_decay

  # Step 3: Select chunks respecting token limit
  selected = []
  sorted_chunks = sort(candidates, by=activations, descending=True)

  for chunk in sorted_chunks:
    tokens_if_added = count_tokens(selected + chunk)

    if tokens_if_added <= token_limit:
      selected.append(chunk)
    else:
      # Can't add more; respect token budget
      break

  # Step 4: Respect cAST structure
  # Ensure all chunks in selection are complete units
  # (cAST guarantees this, but validate)

  return selected
```

### Key Properties

- **Deterministic**: Same query + state → same result (reproducible)
- **Parametric**: Can tune spread_factor (0.7), decay rate (-0.5), etc.
- **Explainable**: Every chunk has activation trace: "1.2 base + 0.3 context + 0.15 spread - 0.05 decay = 1.65"
- **Token-aware**: Respects budget; graceful degradation

---

## 7. Learning Mechanisms

### Feedback Types

**Positive Feedback** (chunk was needed):
- Chunk was retrieved AND used in correct generation
- Action: increase base activation by +0.1-0.2
- Rationale: this chunk matters; keep it hot

**Negative Feedback** (chunk was spurious):
- Chunk was retrieved but NOT used
- Action: decrease base activation by -0.05-0.1
- Rationale: this chunk doesn't actually matter; let it cool

**Discovery Feedback** (missed chunk):
- Chunk was needed but NOT retrieved
- Action: increase base activation by +0.15-0.3 (higher penalty for missing)
- Action: strengthen associative link with retrieved chunks
- Rationale: system failed; learn for next time

**Context Feedback** (chunk was marginally used):
- Chunk was retrieved and helped but wasn't critical
- Action: keep base activation; strengthen context link
- Rationale: useful in some contexts but not fundamental

### Learning Parameters (Tunable)

```python
learning_rates = {
  "positive_feedback": 0.15,      # chunk was needed and retrieved
  "negative_feedback": -0.075,    # chunk was retrieved but unused
  "discovery_feedback": 0.25,     # chunk was needed but missed
  "spread_factor": 0.7,           # how much spreading activation spreads
  "time_decay_rate": -0.5,        # forgetting curve rate
  "context_boost_magnitude": 0.3, # how much context boosts
}
```

These are learned via offline evaluation:
- Replay git history
- For each commit, predict what chunks were needed
- Measure retrieval accuracy
- Tune parameters for best accuracy

---

## 8. Integration Points

### Data Sources for Initialization

**1. Git History**
- Parse commits
- Identify which files changed together (high association strength)
- Identify which functions are frequently modified (high base activation)
- Extract temporal patterns (which code is old vs. new)

**2. IDE Telemetry**
- Track file opens, edits, cursor position
- Boost activation when file is opened
- Learn user patterns (does this developer always look at X before Y?)

**3. Test Execution**
- Track which code paths are executed in tests
- Boost tested code (it's important, validated by tests)
- Penalize code with zero test coverage (probably not critical path)

**4. LLM API Interactions**
- Track which chunks are included in successful completions
- Track which chunks are included in failed completions
- Implement learning feedback loop

**5. Code Analysis**
- Parse imports: what does this chunk depend on?
- Parse function calls: what does it call?
- Build dependency graph programmatically

### Output: Context Injected into LLM Prompt

```
System: You are a code assistant. Context below:

[LAYER 1 - STRUCTURE]
=== Chunk 1: authenticate() (activation: 1.65) ===
def authenticate(username, password):
    result = validate_credentials(username, password)
    ...

[LAYER 2 - RELATED CODE]
=== Chunk 2: validate_credentials() (activation: 1.55) ===
def validate_credentials(u, p):
    ...

[LAYER 3 - REFERENCE INDEX (lower priority, ask if needed)]
Other related code available:
  - create_session() [activation: 0.82]
  - password_hash() [activation: 0.75]
  - user_database_schema [activation: 0.65]

User Query: How do we hash passwords in authentication?
```

---

## 9. Performance and Cost Characteristics

### Computational Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| **Semantic search** | O(n) where n = chunks | Vector similarity search |
| **Spreading activation** | O(k*d) where k=activated, d=depth | Depth-limited (usually 2-3 hops) |
| **Activation update** | O(n) | Linear pass; can batch |
| **Retrieval** | O(k log k) | Sorting + token counting |

### Memory Usage

- Per-chunk state: ~1KB (activation, metadata, links)
- For 10,000 functions: ~10MB activation state
- For 100,000 functions: ~100MB
- Embeddings: depends on model (768-dim: 3MB per 10k chunks)
- **Total for reasonable codebase**: <500MB (one-time, then memory-efficient)

### Token Savings

| Scenario | Current (Embedding-based) | With ACT-R | Savings |
|----------|---------------------------|-----------|---------|
| Simple query | 5k tokens | 3k tokens | 40% |
| Medium query | 20k tokens | 12k tokens | 40% |
| Complex query | 50k tokens | 30k tokens | 40% |

Target: **40% token reduction at same or better accuracy**

---

## 10. Handling Edge Cases

### Cold Start (New Codebase)

**Problem**: Freshly-uploaded codebase has no history. Default activation is shallow.

**Solution**:
1. Initialize base activation from static analysis:
   - Frequently-called functions → higher activation
   - Heavily-imported modules → higher activation
   - Large classes → higher activation
   - Deprecated code → lower activation
2. First 5-10 queries: system performs at baseline (embedding-based)
3. After 10+ queries: system rapidly improves as it learns patterns

### Circular Dependencies

**Problem**: A→B→A→... spreading activation loops infinitely.

**Solution**:
- Detect cycles in dependency graph pre-analysis
- Apply "spreading ceiling": activation can't exceed original + 1.0
- Decay spreading by 70% per hop: spreads matter for 2-3 hops, not 10+ hops

### Per-Developer Profiles

**Optional Enhancement**: Learn user-specific activation patterns
- Developer A frequently accesses auth + database code
- Developer B frequently accesses UI + styling code
- Maintain per-developer activation boosts
- Periodic merging to share insights across team

### Concept Drift

**Problem**: Codebase architecture changes. Old activation patterns become outdated.

**Solution**:
- Monitor deprecation patterns: if chunk frequency drops to near-zero, accelerate decay
- Implement "epoch resets" on major refactors
- Allow manual signals: "module X is deprecated globally"

---

## 11. Metrics and Validation

### Offline Evaluation

```python
def evaluate_system(codebase, historical_queries):

  correct = 0
  total = 0

  for query, query_result in historical_queries:
    # What chunks did the developer actually need?
    needed_chunks = extract_chunks_from(query_result)

    # What did our system retrieve?
    retrieved_chunks = retrieve_context(query, token_budget=50k)

    # Did we get it right?
    if needed_chunks ⊆ retrieved_chunks:
      correct += 1

    total += 1

  accuracy = correct / total
  return accuracy
```

### Online Metrics (Production)

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| **Context Efficiency** | Correctness at fixed token budget | ≥92% accuracy @ 50k tokens |
| **Token Consumption** | Tokens per successful task | 40% reduction vs. baseline |
| **Learning Curve** | Improvement over sessions | 2-5% per session for first 20 |
| **Precision@Budget** | % of needed chunks retrieved | ≥90% with 40k tokens |
| **Developer Satisfaction** | Qualitative "does it understand the code?" | ≥80% satisfaction |
| **False Positive Rate** | % of retrieved chunks never used | <15% |

---

## 12. Timeline and Phasing

### Not for MVP

This is **post-AURORA MVP** work, fitting into WS3-5 (optimization and sophistication phases).

**Phase 1 (WS3)**: Integrate cAST + basic ACT-R
- Implement cAST chunking
- Build activation state model
- Integrate base-level activation
- Measure baseline improvements

**Phase 2 (WS4)**: Spreading activation + learning loop
- Implement spreading activation over dependency graph
- Build feedback mechanisms
- Implement learning loop from LLM outcomes
- Measure learning curve improvements

**Phase 3 (WS5)**: Per-developer profiles and transfer learning
- Implement per-developer activation profiles
- Multi-codebase transfer learning
- IDE telemetry integration
- Advanced learning mechanisms

---

## 13. Assumptions and Dependencies

### Assumptions

- Codebase is parseable (has a grammar; language is supported by tree-sitter)
- Sufficient historical data available for learning (≥50 queries, git history)
- LLM API provides usage feedback (which code was in successful vs. failed generations)
- Token budget is the primary constraint (not compute)

### Dependencies

- **tree-sitter**: For AST parsing (existing library)
- **Embedding model**: For semantic similarity (e.g., OpenAI embeddings, local models)
- **LLM API**: For code generation and evaluation
- **Git data**: For historical patterns
- **IDE/runtime telemetry**: For activation event data (optional but valuable)

---

## 14. Risk Mitigation

### Risk: Gaming the System

**Mitigation**:
- Weight activation by change magnitude, not just frequency
- Track utility, not just frequency (used ≠ needed)
- Quarterly decay audits to reset accumulated errors

### Risk: Context Bias

**Mitigation**:
- Occasionally suppress high-activation chunks to explore
- Random sampling to discover low-activation but valuable code

### Risk: Parameter Sensitivity

**Mitigation**:
- Learn parameters from offline evaluation
- Validate with A/B testing on small user subset
- Allow easy parameter adjustment without code changes

---

## 15. Reporting and Analytics (Future Development - WS4+)

### Overview

Beyond intelligent code retrieval, the system enables rich reporting and analytics on codebase evolution, activity patterns, and developer behavior. Reporting leverages cAST structure (function-level chunks) and ACT-R activation data (frequency, recency, importance scores).

### Core Reporting Use Cases

**1. Activation Change Reports**

Show which functions are becoming more/less important over time.

```
Report: "Top 10 Most Increased Activation (Past 30 Days)"

Function                    | File          | Activation Change | Reason
---------------------------|---------------|-------------------|---------------------------
authenticate()             | auth.py       | +0.45 (0.35→0.80) | Git: 12 edits, 8 test passes
validate_token()           | auth.py       | +0.32 (0.48→0.80) | Git: 8 edits, spreading from auth
session_manager()          | session.py    | +0.28 (0.52→0.80) | Git: 6 edits, LLM queries: 15
hash_password()            | crypto.py     | +0.22 (0.58→0.80) | LLM usage: 12 generations
reset_password()           | auth.py       | -0.15 (0.65→0.50) | Git: 0 edits (30 days), decay
deprecated_login()         | auth.py       | -0.35 (0.55→0.20) | Marked deprecated; automatic decay
format_response()          | utils.py      | -0.12 (0.42→0.30) | Declining git activity
old_cache_system()         | cache.py      | -0.48 (0.80→0.32) | Replaced by new_cache_v2

Insights:
- authenticate() & validate_token() are hotly developed (increased activation)
- reset_password() & deprecated_login() cooling naturally (no recent edits)
- session_manager() gaining importance via spreading activation
- old_cache_system() correctly decaying as it's replaced

Recommendations:
- Review deprecated_login() for complete removal
- Test reset_password() thoroughly (not recently edited)
- Consider documenting session_manager() (rapidly increasing complexity)
```

**2. File-Level Activation Summary**

Aggregate function-level activation to file-level view.

```
Report: "File Activation Summary (Hottest Files)"

File              | Functions | Avg Activation | Max Activation | Activity Level | Days Since Edit
-----------------|-----------|----------------|----------------|----------------|-----------------
auth.py          | 8         | 0.68           | 0.92           | 🔴 CRITICAL   | 2 days ago
session.py       | 5         | 0.64           | 0.81           | 🔴 CRITICAL   | 1 day ago
crypto.py        | 6         | 0.59           | 0.78           | 🟠 HIGH      | 3 days ago
models.py        | 12        | 0.42           | 0.68           | 🟡 MODERATE  | 1 week ago
cache.py         | 4         | 0.35           | 0.52           | 🟡 MODERATE  | 2 weeks ago
utils.py         | 15        | 0.28           | 0.45           | 🟢 LOW       | 3 weeks ago
legacy/old.py    | 3         | 0.12           | 0.18           | ⚪ DORMANT    | 6 months ago

Insights:
- auth.py and session.py are core focus (high activity, high activation)
- crypto.py & models.py provide important infrastructure
- legacy/old.py is completely dormant (candidate for removal/archival)
```

**3. Developer/Team Activity Patterns**

Show which developers focus on which parts of codebase.

```
Report: "Developer Focus Areas (Past 30 Days)"

Developer      | Primary Files      | Activity | Functions Modified | Activation Impact
---------------|-------------------|----------|-------------------|-------------------
alice          | auth.py, session.py | 47 edits | authenticate(+0.45)| +1.82 total
               |                   |          | validate_token(+0.32)|
               |                   |          | session_init(+0.05)|
               |                   |          |                     |
bob            | crypto.py, models.py| 28 edits | hash_password(+0.22)| +0.98 total
               |                   |          | user_model(+0.18)|
               |                   |          | encode(+0.12)|
               |                   |          |                     |
carol          | cache.py, utils.py  | 12 edits | get_cache(-0.08)   | -0.15 total
               |                   |          | format_util(-0.07)|
               |                   |          |                     |

Insights:
- alice is primary auth system developer (clear ownership)
- bob focuses on data/crypto layer (complementary)
- carol working on deprecation/cleanup (negative activation expected)
- No duplication; clear division of labor
```

**4. Dependency Change Analysis**

Track how function dependencies evolve.

```
Report: "Dependency Changes (Spreading Activation Shifts)"

Function              | Dependency Chains Changed | New Dependencies | Removed Dependencies | Stability
----------------------|---------------------------|------------------|----------------------|----------
authenticate()       | 3 → 5                     | [validate_token]  | (none)              | 🟠 Increasing
session_init()       | 2 → 3                     | [cache_get]       | (none)              | 🟡 Stable
cache_get()          | 4 → 2                     | (none)            | [old_cache, legacy] | 🟢 Simplifying
database_query()     | 6 → 6                     | [pool_manager]    | [direct_connection] | 🟢 Stable

Insights:
- authenticate() growing dependencies (sign of increasing complexity)
- cache_get() removing legacy dependencies (cleanup/refactor)
- database_query() maintaining stable interface (good sign)
- spreading_activation will shift as dependencies change
```

**5. Historical Activation Trends**

Show activation evolution over time (baseline for seasonal/architectural patterns).

```
Report: "Activation Trend Analysis (Past 90 Days)"

Function           | Day 1  | Day 30 | Day 60 | Day 90 | Trend     | Velocity
-------------------|--------|--------|--------|--------|-----------|----------
authenticate()     | 0.35   | 0.52   | 0.68   | 0.80   | 📈 RISING | +0.15/mo
validate_token()   | 0.48   | 0.55   | 0.65   | 0.80   | 📈 RISING | +0.11/mo
session_init()     | 0.42   | 0.45   | 0.48   | 0.52   | 📈 SLOW   | +0.03/mo
cache_get()        | 0.65   | 0.58   | 0.48   | 0.35   | 📉 FALLING| -0.10/mo
old_auth_v1()      | 0.42   | 0.35   | 0.22   | 0.08   | 📉 DEPRECATED| -0.11/mo

Insights:
- authenticate() & validate_token() in growth phase (increasing complexity)
- cache_get() in decline (planned deprecation/replacement)
- old_auth_v1() near complete deprecation (good trajectory)
- Predictable trends enable capacity planning
```

**6. Query Performance and Impact Analysis**

Track which code is actually used in LLM interactions.

```
Report: "Query Impact Analysis (Code Retrieval Effectiveness)"

Query Type                       | Avg Functions Retrieved | Hit Rate | False Positive | Learning Impact
--------------------------------|------------------------|----------|----------------|-------------------
"How do we authenticate?"        | 5                      | 92%      | 8%            | 🟢 HIGH
"Validate user credentials"      | 4                      | 88%      | 12%           | 🟢 HIGH
"Hash passwords securely?"       | 3                      | 94%      | 6%            | 🟢 HIGH
"Session management flow"        | 7                      | 86%      | 14%           | 🟡 MEDIUM
"Cache implementation"           | 9                      | 72%      | 28%           | 🟡 MEDIUM
"Old API usage" (legacy)        | 12                     | 58%      | 42%           | 🔴 LOW

Insights:
- Authentication queries are highly effective (92-94% hit rate)
- Cache queries need refinement (high false positive rate)
- Legacy code queries are problematic (58% hit rate; old code is ambiguous)
- Learning impact correlates with hit rate (high hit → effective learning)

Recommendations:
- Refactor cache module or improve chunking/dependencies
- Consider deprecating or completely removing legacy API
- Double-check spreading activation for cache functions
```

**7. Codebase Health Dashboard**

High-level view of codebase quality and evolution.

```
Report: "Codebase Health Score"

Metric                              | Score | Trend | Status
------------------------------------|-------|-------|--------
Average Activation (functions)      | 0.54  | ↑    | 🟡 HEALTHY
High-Activation Functions (>0.7)    | 12    | ↑    | 🟢 GOOD (focused development)
Low-Activation Functions (<0.2)     | 8     | ↓    | 🟢 DECLINING (good, cleanup)
Deprecated Functions (marked)       | 3     | ↓    | 🟢 GOOD (proper removal)
Orphaned Functions (no deps)        | 2     | →    | 🟡 WATCH (decide fate)
Function Churn (changes/month)      | 47    | →    | 🟡 MODERATE (healthy)
New Functions (90 days)             | 5     | ↑    | 🟢 GROWING
Dependency Complexity (avg hops)    | 2.3   | →    | 🟢 MANAGEABLE
Test Coverage (by activation)       | 84%   | ↑    | 🟢 GOOD

Overall Health: 🟢 HEALTHY
- Code is actively maintained (high churn, new functions)
- Cleanup happening naturally (deprecated functions declining)
- Dependency structure manageable (avg 2.3 hops)
- Test coverage good for active code
```

### Implementation Plan (WS4+)

**Phase 1 (WS4): Basic Reports**
- Activation change reports (most/least changed)
- File-level summary
- Historical trends
- Query effectiveness analysis

**Phase 2 (WS5): Advanced Analytics**
- Developer activity patterns
- Dependency change analysis
- Codebase health dashboard
- Predictive analysis (which functions will need attention)

**Phase 3 (Future): Integration**
- Dashboard visualization
- Export to CSV/JSON
- Alerts (activation drops, new dependencies, deprecation warnings)
- Recommendations engine (refactor candidates, cleanup priorities)

### Technical Requirements

**Data Collection**:
- Activation snapshots (daily/weekly)
- Git commit metadata (author, timestamp, changed functions)
- LLM query logs (what was retrieved, what was used)
- Test execution data (coverage by function)

**Storage**:
- Time-series database (activation over time)
- Query logs (for analysis)
- Snapshots (to enable historical reports)

**Query Language**:
- SQL-like queries for activation data
- Time-range filters
- Aggregation functions (sum, avg, max, min)
- Grouping (by file, developer, activation range)

---

## Summary

**ACT-R + cAST solves the code context problem by combining**:

1. **cAST**: Well-defined, meaningful chunks (no arbitrary splits)
2. **Embedding**: Semantic similarity (find related code)
3. **ACT-R**: Dynamic prioritization (what matters now)
4. **Learning**: Feedback loops (improve over time)

Result: **40% token reduction at same/better accuracy, improving over time as system learns**

This is the technical foundation for creating a PRD that describes the product, user value, and business outcomes.
