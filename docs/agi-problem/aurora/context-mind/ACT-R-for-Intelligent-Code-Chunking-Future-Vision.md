# Ultrathink: ACT-R for Intelligent Code Chunking

**Classification**: Future Vision / Post-MVP Research (WS3-5)
**Date**: December 8, 2025
**Category**: Context Management at Scale
**Status**: Exploratory Analysis - Not For Immediate Implementation

---

## Executive Summary

The problem of keeping codebase context within reach without losing context windows is fundamentally a **memory management problem**, not a retrieval problem. Current approaches (embeddings, semantic search, cAST chunking) excel at *finding* relevant code but fail at *prioritizing* it under resource constraints.

We propose applying **ACT-R** (Adaptive Control of Thought - Rational), a cognitive architecture from psychology, to transform code chunking from static retrieval into a dynamic, learning-based system that:

- Prioritizes code by real-time **activation** (not static embeddings)
- Models code relationships via **spreading activation** over dependency graphs
- Improves through **learning feedback loops** from developer behavior
- Achieves **graceful degradation** under context limits
- Provides **explainability** at every decision point

**Key Finding**: No existing tool combines these capabilities. This represents a true technical frontier.

---

## 1. Current State of Code Chunking

### Evolution of Approaches

**Token-Based Chunking** (Naive)
- Split at fixed token boundaries or line counts
- Catastrophically inappropriate for code
- Routinely destroys semantic units (functions, classes)
- Represents abandoned baseline

**Semantic Chunking** (Intermediate)
- Groups by sentence-level topic coherence
- Better than tokens, but misses code structure
- Works for prose; inadequate for executable syntax

**AST-Based Chunking / cAST** (Current State-of-the-Art)
- Recursively traverses Abstract Syntax Tree
- Respects syntactic boundaries (classes, functions, methods)
- **Validated results**:
  - 4.3 point improvement in Recall@5 on RepoEval benchmark
  - 2.67 point improvement in Pass@1 on SWE-bench generation
  - Cross-language consistency via tree-sitter universal parsing
- **Current Implementation Examples**: ChunkHound implements this approach

### Key Players and Their Approaches

**ChunkHound** (github.com/chunkhound/chunkhound)
- Implements cAST (chunking via AST)
- Embeds chunks semantically
- Multi-hop semantic search for relationships
- Smart content diffs (only re-embed changed portions)
- **Strength**: Structurally sound chunks
- **Limitation**: Retrieval is still stateless and reactive

**c7score** (github.com/upstash/c7score)
- Focuses on *external library documentation* (33k+ libraries)
- Scores snippet quality via 5 metrics:
  - LLM relevance evaluation
  - Formatting quality
  - Project metadata
  - Initialization context
  - Code completeness
- **Strength**: Documentation retrieval
- **Limitation**: Not about in-repo code understanding

**Sourcebot** (github.com/sourcebot-dev/sourcebot)
- Trigram indexing for massive codebases
- Boolean logic + regex query support
- Optimized for "find all instances of X"
- **Strength**: Scalable pattern matching
- **Limitation**: Pattern-based not semantic; doesn't rank by relevance

**Wispbit** (github.com/wispbit-ai/wispbit)
- Learns *codebase consistency patterns*
- Enforces learned patterns in new generations
- Quality gate rather than retrieval mechanism
- **Strength**: Maintains code style/patterns
- **Limitation**: Not a context selection tool

### Fundamental Limitations

**1. Static Relevance Models**
- Relevance decided at chunk creation time via embeddings
- Never changes unless code changes
- Ignores dynamic context: "What am I working on now?"
- No concept of "warm" vs. "cold" code in current session

**2. No Learning from Context**
- Retrieval failure = lost opportunity
- Each query treated identically regardless of history
- System never improves through feedback
- Zero transfer learning between sessions/developers

**3. Attention Blindness**
- LLMs exhibit "context collapse" with long contexts
- Performance degrades 13.9%-85% with increasing input length
- Recency bias: early (critical) code deprioritized
- No graceful degradation—sharp cliff, not smooth tradeoff

**4. Dependency Management**
- AST respects syntax but doesn't deeply model semantics
- "Include both chunks" = same priority; treats them independently
- No principled way to weight "this dependency matters more"
- Import explosion: 50 functions → 50 chunks → exponential combinations

**5. Cost of Safety**
- Exhaustive inclusion to avoid missing code
- Single module with 50 functions = 50 retrievable chunks
- "Safe" retrieval easily consumes 100k+ tokens
- Prohibitively expensive; token efficiency plummets

### Current Evaluation Metrics and Their Blind Spots

| Metric | What It Measures | What It Misses |
|--------|-----------------|----------------|
| **Precision@k, Recall@k** | "Did we retrieve the right chunks?" | *Token efficiency*: Perfect recall at 500k tokens is useless |
| **Pass@1 (SWE-bench)** | "Did the model solve the task?" | Conflates retrieval + generation quality |
| **MRR (Mean Reciprocal Rank)** | Relevance ranking of results | Context constraints; token budget limitations |

**Core Gap**: No metric captures *effective context utilization under resource constraints*.

---

## 2. Gap Analysis: Problem vs. Solution Mismatch

### The Conceptual Mismatch

The field conceptualizes the problem as:
> "Given a query, find the most semantically similar chunks"

This is an **information retrieval problem** → stateless, query-driven, reactive systems.

The actual problem is:
> "Given limited context (tokens), developer patterns (behavioral), and repository structure (graph), predict which code units the developer will need and maximize probability they're available when needed"

This is a **memory management problem** → requires state, learning, prediction, temporal awareness.

### Where Current Approaches Fail

**1. The Recency Bias Problem**
- Chroma Research's "Context Rot" study: relevant info in first 20% of context is ignored
- No amount of perfect retrieval solves this if chunks are simply concatenated
- System needs to *refresh* relevance based on LLM attention patterns
- Current solutions: "just put important stuff at the end" (ad-hoc)
- ACT-R solution: dynamic activation re-ranking in real-time

**2. The Cold Start Problem**
- New developer = no historical context
- System makes identical decisions for all developers
- Expert auth specialist should get different context than newcomer
- Current solutions: per-user metadata (expensive)
- ACT-R solution: personalized activation profiles with rapid learning

**3. The False Precision Trap**
- High semantic similarity ≠ usefulness
- 0.95 cosine similarity might be "almost but wrong"
- 0.7 similarity chunk might be exactly what's needed
- Current systems can't distinguish
- ACT-R solution: activation incorporates feedback, not just similarity

**4. The Import Chain Explosion**
```
function X imports {module A, module B, module C}
each of those imports {5 more modules}
exponential branching → token bloat or missing context
```
- Current solutions: arbitrary heuristics ("2 levels deep")
- ACT-R solution: gracefully weight activation by dependency depth

**5. The Conversation Amnesia Problem**
- Developer explores code → asks questions → makes edits
- Each query treated as independent
- Zero learning: "this developer is investigating auth flow"
- Current solutions: hack with conversation summaries
- ACT-R solution: context boosts within session; learning across sessions

### The Missing Piece: Dynamic Learning

Current systems are **static indices**:
- Update when code changes
- Never learn from query success/failure
- No feedback loop saying "you missed chunk X in this situation"

**This is where ACT-R becomes essential.**

---

## 3. ACT-R as Solution: Principles and Mapping

### ACT-R Fundamentals

**ACT-R** developed by John Robert Anderson (Carnegie Mellon) models how humans retrieve information from memory. Core insight:

> Memory retrieval is governed by **activation levels**, not discrete retrieval rules

**Key Principles**:

| Principle | Definition |
|-----------|-----------|
| **Activation** | Real number (range -2 to +1) determining retrieval speed/reliability. Higher = faster, more reliable. |
| **Base-Level Activation** | Frequently used chunks have higher base activation. Unused chunks decay per power law (Ebbinghaus curve). |
| **Context-Based Boosts** | Current context temporarily boosts related chunks. Discussing "authentication" boosts auth-related chunks. |
| **Spreading Activation** | Activated chunks boost related chunks via associative links. Mention "login" → password validation, user DB, session mgmt all receive boosts. |

### Mapping to Code Context

| ACT-R Concept | Code Mapping | Example |
|---|---|---|
| **Knowledge Chunk** | Code unit (function, class, file, API) | `authenticate()` function |
| **Base-level Activation** | Frequency of use (git history, IDE logs, test coverage) | Frequently imported file = high base activation |
| **Activation Decay** | Time since last access (power law) | Unused module for 3 months → activation drops |
| **Context Boosts** | Currently viewing file; recent edits; actively debugging | Currently in `auth.py` → boost all auth functions |
| **Associative Links** | Dependency graph (imports, calls, shared classes) | `login()` calls `validate_password()` |
| **Spreading Activation** | Transitive dependency activation | If `X` calls `Y`, activating `X` boosts `Y` |

### How ACT-R Addresses Each Gap

**1. Dynamic Relevance Scoring**
- Instead of static embeddings, activation computed in real-time
- Factors: base frequency + recency + current context + dependencies
- Relevance is *live*, adapts as developer navigates
- Score formula: `A(t) = BLA + context_boost + spreading_boost - time_decay`

**2. Conversation Threading**
- Context boosts naturally model session state
- Early session: "How does authentication work?" boosts auth chunks
- Later query: "How do we validate tokens?" benefits from sustained auth activation
- System remembers implicit context without explicit prompting

**3. Graceful Degradation**
- No sharp boundaries; activation provides continuum
- Rank chunks by activation; include top-K
- If context tight → drop low-activation chunks
- If context available → include more
- Probability of including chunk ∝ its activation level

**4. Dependency Activation**
- Spreading activation solves import explosion
- When activating function, direct dependencies get 0.7x boost
- Their dependencies get 0.7²x boost
- Natural decay: distant code matters less than close

**5. Learning from Failure**
- When chunk should have been retrieved but wasn't:
  - Increase its base-level activation
  - Adjust associative strength with related chunks
  - Tune decay rates
- System learns which chunks tend to be needed together
- Improves over time with feedback

### Advantages Over Current Approaches

| Advantage | Mechanism | Impact |
|-----------|-----------|--------|
| **Unified Metric** | Single activation score vs. multiple heuristics | More interpretable; easier to compose |
| **Explicit Dependencies** | Parametric spreading vs. semantic search | Testable; fine-tunable; transparent |
| **Temporal Dynamics** | Decay functions model time explicitly | Popular code stays "hot"; rare code "cools" |
| **Transfer Learning** | Learn once, apply to multiple codebases | New codebase starts good; improves rapidly |
| **Explainability** | Each activation has clear justification | "Why was X included?" → "base 1.2 + context 0.3 + dependency 0.15 = 1.65" |

---

## 4. Implementation Vision

### Architecture Components

**1. State Layer: Persistent Activation Table**
```python
code_unit → {
  name: str,
  base_activation: float,           # How fundamental is this?
  last_access: datetime,            # How recent?
  frequency_count: int,             # How often used?
  associative_links: dict,          # {other_unit: strength_weight}
  activation_history: list,         # Track activation over time
}
```

**2. Event Handlers: Update Activation on Events**
```
Developer opens file          → boost file activation
Developer edits function      → boost function activation
Developer runs tests          → boost tested code activation
Query issued to LLM          → boost retrieved chunks
Chunk used in generation     → strong positive reinforcement
Generated code is correct    → reinforce decision
Generated code is buggy      → penalize missed chunks
```

**3. Retrieval Engine: Compute Activation + Select Top-K**
```python
def retrieve_context(query, token_limit, codebase):
  activations = {}

  for unit in codebase.code_units:
    a = base_level_activation(unit)
    a += context_boost(unit, query, current_focus)
    a += spreading_activation(unit, recently_active, dependency_graph)
    a -= time_decay(unit.last_access)
    activations[unit] = a

  # Greedily select by activation, respecting token limit
  selected = []
  for unit in sorted(activations.values(), reverse=True):
    if token_count(selected + unit) <= token_limit:
      selected.append(unit)

  return selected
```

**4. Learning Loop: Feedback for Improvement**
```python
def learn_from_outcome(query, retrieved_chunks, generated_code, success):
  needed_chunks = extract_chunks_from_generated_code(generated_code)
  missed_chunks = needed_chunks - retrieved_chunks
  spurious_chunks = retrieved_chunks - needed_chunks

  for chunk in missed_chunks:
    # Increase activation for future
    base_activation[chunk] += 0.1
    # Strengthen links with retrieved chunks
    for retrieved in retrieved_chunks:
      strengthen_association(chunk, retrieved, weight=0.05)

  for chunk in spurious_chunks:
    # Decrease activation
    base_activation[chunk] -= 0.05
```

**5. Integration Points**
- **IDE Extension**: File opens, edits, cursor position
- **Git Hooks**: Track which files change together
- **LLM API**: Track query success/failure; which chunks used
- **Test Runner**: Which code paths executed
- **Developer Feedback**: "That was helpful" / "You missed important code"

### How It Integrates with LLM Context Windows

**Phase 1: Pre-Prompt Ranking**
- Compute activation for all code units
- Ranking replaces embedding-based similarity entirely

**Phase 2: Dynamic Context Packing** (Novel Strategy)
```
Include immediately (high activation):
  └─ Necessary chunks (activation > 0.8)

Include probably (medium activation):
  └─ 1-2 transitive dependencies (activation 0.5-0.8)

Create reference index (low activation):
  └─ "Other related code: [unit1, unit2]. Ask if needed."
  └─ Not expanded inline; creates "handles" for exploration
```

Helps with recency bias: important code highlighted; less critical code accessible but not verbose.

**Phase 3: Feedback Loop**
```
After LLM generation:
  └─ Which chunks did it actually use? (trace references)
  └─ Which chunks should it have used? (analyze misses)
  └─ Update activations
```

### Metrics to Prove It Works

**1. Context Efficiency** (core metric)
- Fixed token budget → what % of generated code is correct?
- Baseline: 65% correctness with 50k tokens (current method)
- ACT-R: 85% correctness with 50k tokens (learning-enabled)
- Target: 20-40% improvement for same budget

**2. Token Consumption Reduction**
- Fixed correctness target → how many tokens needed?
- Current: 50k tokens to solve complex task
- ACT-R: 20k tokens for same correctness
- Metric: tokens per successful task

**3. Learning Curve**
- Sessions 1-5: baseline (no history)
- Sessions 10-20: noticeably better (system learning)
- Sessions 50+: asymptotic (learned patterns)
- Measure improvement rate per session

**4. Precision@Budget** (novel metric)
- Given K tokens, retrieve what % of necessary chunks?
- Example: "With 5K tokens, 85% of necessary chunks" vs. "With 20K, 95%"
- Optimizes precision under constraint (not absolute)

**5. Developer Satisfaction** (qualitative)
- Does AI feel like it "understands" the codebase?
- Can it make suggestions without explicit pointers?
- Does it improve over time?

---

## 5. Risks and Mitigations

### Risk 1: Cold Start / New Codebases

**Problem**: Freshly-uploaded codebase has no history. Activation defaults to shallow heuristics; system starts dumb.

**Mitigation**:
- Pre-compute base activation from static analysis
  - Frequently called functions → higher activation
  - Highly imported modules → higher activation
  - Large classes → higher activation
- Learn from similar public codebases (if permissible) for transfer learning
- Accept lower early performance; improve rapidly after 5-10 sessions

### Risk 2: Gaming the System

**Problem**: Developer exploits learning. Edits file without substance to boost activation. System learns spurious patterns.

**Mitigation**:
- Weight activation by *change magnitude*, not frequency
  - 5-character edit ≠ 100-line refactor
- Track *utility* of retrievals, not just frequency
  - If chunk retrieved often but rarely used → decrease activation
- Quarterly decay audits: recompute base activation from git history

### Risk 3: Context Bias

**Problem**: Always-retrieved chunks always get boosted. System biased toward central code; peripheral code harder to discover.

**Mitigation**:
- Occasionally suppress high-activation chunks to explore alternatives
- Implement "activation resets" → sample more randomly periodically
- Force-include never-retrieved chunks; measure if useful

### Risk 4: Dependency Cycle Explosions

**Problem**: Circular dependencies cause spreading activation to loop infinitely. A→B→A→B→...

**Mitigation**:
- Detect cycles in dependency graph pre-analysis
- Apply "spreading ceiling": activation can't exceed original + 1.0
- After each spreading level, decay by 70% (2-3 hops matter; 10 hops don't)

### Risk 5: Model Divergence

**Problem**: Different developers use codebase differently. Global activation converges to mediocre average.

**Mitigation**:
- Implement per-developer activation profiles
- Track which code units each developer touches
- Use personalized activation when retrieving for specific developer
- Periodically merge insights between developers

### Risk 6: Concept Drift

**Problem**: Codebase architecture changes over time. Old activation patterns become outdated.

**Mitigation**:
- Monitor for deprecation patterns
  - Frequency suddenly drops to near-zero → accelerate decay
- Implement "epoch resets" on major refactors
- Allow manual reset signals: "module X deprecated globally"

### Validation Strategy

**Offline Evaluation**:
- Replay git history
- For each commit, predict what code developer needed
- Did ACT-R retrieve it?

**A/B Testing**:
- Run on 10% of users
- Measure: code correctness, token consumption, developer satisfaction

**Failure Analysis**:
- When generated code is buggy:
  - Did LLM have necessary context? → blame retrieval
  - Did LLM have context but not use it? → blame generation

**Cost-Benefit**:
- Compute cost of maintaining activation state
- vs. tokens saved
- Ensure net positive

---

## 6. Connection to AURORA

### AURORA's Core Challenge

AURORA (cognitive architecture combining SOAR reasoning, ACT-R learning, agent orchestration) needs to maintain productive context without infinite token budgets. **This is exactly what ACT-R addresses.**

Your problem statement: "Keep codebase context within reach without losing context windows"

**ACT-R solves this directly.**

### Integration Points in AURORA

**As Internal Subsystem**:
If AURORA reasons over codebases, it needs intelligent chunking internally:
1. Parse codebase into AST-based chunks (cAST)
2. Initialize ACT-R activation based on task description
3. Maintain activation during multi-step reasoning
4. Prioritize chunks in reasoning based on activation
5. Learn from multi-step outcomes to improve future activation

Result: Reason about large codebases without context bloat.

**As Developer-Facing Feature**:
AURORA could expose ACT-R context as user-facing tool:
```
Developer: "How does authentication work?"
    ↓
AURORA: Returns activated context with interactive drill-down
    ↓
Developer explores; AURORA updates activation in real-time
    ↓
Related code becomes more discoverable
    ↓
Developer gets dynamic context experience, not static search results
```

**In Conversation Threading**:
Your insight: "conversation history with codebase = edit history"

ACT-R models this naturally:
```
Session = conversation with codebase
Within session:
  ├─ ACT-R maintains activation of discussed code
  ├─ Subsequent queries benefit from context boosts
  ├─ If developer pivots → new module activation rises
  ├─ If developer returns → residual activation helps remember
  └─ System learns patterns across sessions
```

### Long-Term Roadmap Integration

**WS1-2 (MVP)**:
- Basic cAST chunking
- Simple embedding-based retrieval
- Proof-of-concept code generation
- **No ACT-R yet** — establish baseline

**WS3-4 (Optimization)**:
- Integrate ACT-R activation model
- Build feedback loops for learning
- Implement spreading activation over dependency graphs
- Measure token efficiency improvements
- **This is where ACT-R adds value**

**WS5+ (Sophistication)**:
- Per-developer activation profiles
- Multi-codebase transfer learning
- IDE telemetry integration
- Multi-turn conversation with persistent context

### Competitive Advantage

Other tools:
- **Cursor/Claude Code**: Embedding-based retrieval (good semantic search, no learning)
- **Cody**: Some pattern learning (ad-hoc, no unified model)
- **AURORA with ACT-R**: Principled, learnable, explainable, improves over time

The difference between *search* (find relevant code) and *understanding* (remember what matters, learn from patterns, adapt to context).

---

## Synthesis: Why ACT-R, Why Now

### The Conceptual Shift Required

Code chunking has been framed as:
- **Retrieval problem**: Find most similar chunks (solved by embeddings)
- **Ranking problem**: Sort by relevance (solved by semantic search)

Neither addresses the actual bottleneck: **context management under resource constraints**.

ACT-R reframes it as a **memory problem**:
- What's important *right now*?
- What patterns matter for *future needs*?
- How do we improve predictions through *feedback*?

This shift is necessary because:
1. Retrieval is *solved* (embeddings work well)
2. The bottleneck is *now context management*
3. Learning changes everything (systems get better over time)

### The Cognitive Science Bridge

ACT-R exists in psychology because *human memory works this way*:
- We don't maintain static indexes of everything
- We maintain activation levels that decay, get boosted, spread via associations
- Code is information; using a cognitive architecture for information retrieval makes sense

### The Next Frontier

Current tools are in the **lexical retrieval phase**: Find code by keywords/similarity

Next frontier is **episodic retrieval**: Remember what you did before in similar situations

> When a developer says "this is like the auth refactor we did 3 months ago," an ACT-R system could activate chunks from that past session, compute new activation based on current context, and suggest the old solution as a starting point.

This requires memory, learning, temporal reasoning — exactly what ACT-R provides.

---

## Conclusion

The problem of keeping codebase context within reach is **fundamentally a memory management problem**, not a retrieval problem.

Current systems fail because they treat it as the former.

**ACT-R provides principles for solving the latter**:

✅ **Activation-based prioritization**: What matters now gets priority
✅ **Spreading activation**: Related code gets boosted
✅ **Decay and learning**: Unused code fades; feedback improves
✅ **Temporal dynamics**: Time matters; recent is more relevant
✅ **Explainability**: Every decision has a clear trace

For AURORA and similar tools, ACT-R offers a path beyond "search engines for code" to "understanding systems that learn."

The bleeding edge isn't finding more relevant code faster—it's using *less* code more intelligently, learning what matters for each context, and adapting in real-time.

**This is feasible, measurable, and represents true advance over current approaches.**

---

## References

- [ChunkHound Repository](https://github.com/chunkhound/chunkhound)
- [cAST: Enhancing Code Retrieval via Structural Chunking](https://arxiv.org/html/2506.15655v1)
- [Upstash c7score](https://github.com/upstash/c7score)
- [Sourcebot Code Understanding Tool](https://github.com/sourcebot-dev/sourcebot)
- [Wispbit Codebase Standards](https://github.com/wispbit-ai/wispbit)
- [ACT-R Cognitive Architecture](http://act-r.psy.cmu.edu/)
- [Spreading Activation Theory](https://en.wikipedia.org/wiki/Spreading_activation)
- [Context Rot in LLMs - Chroma Research](https://research.trychroma.com/context-rot)
- [Context Window Performance Degradation Analysis](https://arxiv.org/html/2510.05381v1)
- [Ebbinghaus Forgetting Curve](https://en.wikipedia.org/wiki/Forgetting_curve)
- [RAG Code Generation Survey](https://arxiv.org/html/2510.04905)

---

**Classification**: WS3-5 Future Work / Post-MVP Research
**Status**: Speculative Analysis - Not Ready for Implementation
**Next Review**: After AURORA MVP launch (WS2 completion)
