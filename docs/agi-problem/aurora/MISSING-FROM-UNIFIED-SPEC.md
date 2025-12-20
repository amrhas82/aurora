# What's Missing from AURORA-MVP-UNIFIED-SPEC.md

**Date:** December 20, 2025
**Based on:** Scan of all Aurora PRD/spec documents
**Status:** Gaps identified - needs user confirmation before integration

---

## Critical Missing Components

### 1. **ACT-R Code Context Management (ContextMind) - ENTIRE SUBSYSTEM**

**Source Documents:**
- `context-mind/ACT-R-Code-Context-Management-PRD.md` (2000 lines)
- `context-mind/ACT-R-Code-Context-Management-SPECS.md` (1065 lines)
- `AURORA-CODE-CONTEXT-COMPLETE.md`

**What's Missing:**

#### 1.1 cAST (Code Abstract Syntax Tree) Chunking
- **Function-level chunking** (not file-level)
- Tree-sitter integration (~700 lines of wrapper code)
- Language support: Python, JS, Go, Rust, Java, C++
- Dependency graph extraction (call graph, imports)
- Line-range mapping (git diff lines → functions)

**Why it matters:** Enables precise code context retrieval (40% token reduction)

#### 1.2 Git Integration Layer
- **Continuous activation signals** from git history
- Daily/weekly polling of `git add .` for staged changes
- Initialization: Parse git log for frequency per function
- Line-level change tracking: Map git diff to specific functions
- Validation signals: Check if LLM-modified code matches git changes

**Why it matters:** Provides automatic learning signals without manual annotation

#### 1.3 ACT-R Activation Formula (Code-Specific)
```
A(function) = BLA + CB + SA - decay

BLA (Base-Level Activation): frequency from git history
CB (Context Boost): relevance to current query/file
SA (Spreading Activation): related functions already activated (via call graph)
decay: time since last access
```

**Why it matters:** Ranks code chunks by actual importance, not just similarity

#### 1.4 Code Context Retrieval Pipeline
```
Query → Semantic Search (find candidates)
      → ACT-R Activation (rank by importance)
      → Top-K Selection (5-10 functions)
      → LLM Context (inject into prompt)
```

#### 1.5 Learning Loop (Replay HER for Code)
- **Success feedback:** Functions in successful generation → +0.25 activation
- **Discovery feedback:** Functions generated but not used → +0.15 (hindsight relabel)
- **Negative feedback:** Functions in failed attempts → -0.075 activation
- **Validation:** Compare LLM-modified code with git changes

**Why it matters:** System improves 2-5% accuracy per session

#### 1.6 Reporting & Analytics (7 Use Cases)
1. Codebase heat map (which functions most active)
2. Developer activity patterns
3. Code coupling analysis (dependency graphs)
4. Dead code detection (low activation functions)
5. Knowledge transfer metrics (team collaboration)
6. Refactoring impact prediction
7. Code quality trends over time

**Why it matters:** Provides visibility into codebase evolution

---

### 2. **Repository Structure - ENTIRE SECTION**

**What's Missing:**

```
aurora/
├── src/
│   ├── core/
│   │   ├── orchestrator.py         # SOAR orchestration loop
│   │   ├── complexity_assessment.py # Keyword + LLM assessment
│   │   ├── decomposition.py         # JSON decomposition
│   │   ├── verification.py          # Options A, B, C
│   │   ├── synthesis.py             # Final result assembly
│   │   └── self_correction.py       # Retry with feedback
│   │
│   ├── memory/
│   │   ├── actr.py                  # ACT-R activation engine
│   │   ├── replay_buffer.py         # Replay HER storage
│   │   ├── pattern_cache.py         # Cached verified patterns
│   │   └── sqlite_store.py          # Persistent memory (SQLite)
│   │
│   ├── agents/
│   │   ├── registry.py              # Agent discovery + routing
│   │   ├── executor.py              # Agent execution wrapper
│   │   └── llm_fallback.py          # LLM-only executor
│   │
│   ├── context/                     # ← NEW: ContextMind subsystem
│   │   ├── cast/
│   │   │   ├── parser.py            # Tree-sitter wrapper
│   │   │   ├── extractors.py        # Function/class extraction
│   │   │   ├── dependencies.py      # Call graph tracking
│   │   │   └── languages/
│   │   │       ├── python.py
│   │   │       ├── javascript.py
│   │   │       └── ...
│   │   │
│   │   ├── git_integration.py       # Git polling + signals
│   │   ├── activation.py            # Code-specific ACT-R
│   │   ├── retrieval.py             # Context retrieval pipeline
│   │   └── learning.py              # Code learning loop
│   │
│   ├── llm/
│   │   ├── router.py                # LLM preference routing
│   │   ├── providers.py             # Anthropic, OpenAI, etc.
│   │   └── cost_tracker.py          # Budget enforcement
│   │
│   ├── safety/
│   │   ├── guardrails.py            # Input/output validation
│   │   ├── budget.py                # Cost limits
│   │   └── validators.py            # Format validators
│   │
│   ├── headless/
│   │   ├── executor.py              # Headless loop
│   │   ├── goal_validator.py        # Success criteria check
│   │   └── scratchpad.py            # Scratchpad management
│   │
│   └── cli/
│       ├── main.py                  # CLI entry point
│       ├── commands.py              # Command handlers
│       └── output.py                # Formatted output
│
├── config/
│   ├── config.json                  # Main config file
│   ├── agents.json                  # Agent registry
│   └── prompts/                     # LLM prompt templates
│       ├── decomposition.txt
│       ├── verification_a.txt
│       ├── verification_b.txt
│       └── synthesis.txt
│
├── data/
│   ├── memory/                      # ACT-R persistent storage
│   │   ├── actr.db                  # SQLite database
│   │   └── cache/                   # Pattern cache
│   │
│   ├── context/                     # Code context data
│   │   ├── cast_index.db            # Function index
│   │   ├── git_signals.json         # Git activation data
│   │   └── embeddings/              # Code embeddings
│   │
│   ├── tasks/                       # Task execution logs
│   │   └── YYYY/MM/DD/
│   │       └── task-{uuid}.json
│   │
│   └── budget/                      # Cost tracking
│       └── spending.json
│
├── logs/
│   └── aurora.log
│
├── tests/
│   ├── unit/
│   │   ├── test_orchestrator.py
│   │   ├── test_verification.py
│   │   ├── test_actr.py
│   │   ├── test_cast.py             # ← NEW: cAST tests
│   │   └── ...
│   │
│   ├── integration/
│   │   ├── test_full_pipeline.py
│   │   ├── test_code_context.py     # ← NEW: Context tests
│   │   └── ...
│   │
│   └── fixtures/
│       ├── test_queries.json
│       └── test_codebases/          # ← NEW: Code samples
│           ├── python_sample/
│           └── javascript_sample/
│
└── docs/
    ├── README.md
    ├── ARCHITECTURE.md
    ├── CONFIGURATION.md
    ├── CODE_CONTEXT.md              # ← NEW: ContextMind docs
    └── API.md
```

**Why it matters:** Developers need clear structure to navigate codebase

---

### 3. **AURORA Refined Architecture - LEARNING LAYER**

**Source Document:** `AURORA-REFINED-ARCHITECTURE.md`

**What's Missing:**

#### 3.1 Replay Buffer Management
- **Storage:** All outcomes (success, failure, discovery)
- **Hindsight Experience Replay (HER):** Relabel failures as successes for alternative goals
- **Sampling:** Random batch sampling for offline learning
- **Metadata:** Execution time, memory used, quality scores

#### 3.2 QLoRA Fine-Tuning (Phase 2)
- **Purpose:** Learn patterns from replay buffer
- **Method:** QLoRA (quantized low-rank adaptation)
- **Deployment:** Cost-effective, runs on edge
- **Trade-off:** -2% accuracy vs full fine-tuning, but much cheaper

#### 3.3 Learning Signal Flow
```
Agent Execution Result
  ↓
Classify Outcome:
  ├─ SUCCESS → +0.25 activation to used agents
  ├─ DISCOVERY → +0.15 activation (hindsight relabel)
  └─ FAILURE → -0.075 activation (explicit negative learning)
  ↓
Store in Replay Buffer
  ↓
Offline Batch Learning (daily/weekly):
  ├─ Update ACT-R BLA from git
  ├─ Fine-tune model with QLoRA (optional)
  └─ Adjust activation thresholds
```

**Why it matters:** Enables continuous improvement from all interactions

---

### 4. **Layer Architecture - MISSING LAYER DETAILS**

**What's Missing:**

The unified spec has "DECOMPOSE → VERIFY → AGENTS → VERIFY → RESPOND" but missing **detailed layer breakdown:**

#### Layer 0: Input Processing (NEW)
- Guardrails (PII detection, length limits)
- Cost budget pre-check
- Query normalization

#### Layer 1: Assessment & Discovery
- Complexity assessment (keyword + optional LLM)
- Agent discovery from registry
- ContextMind activation (if code query)

#### Layer 2: ACT-R Memory Retrieval
- **Two types:**
  1. **General patterns** (stored verified decompositions)
  2. **Code context** (cAST + git signals) ← MISSING

#### Layer 3: SOAR Problem-Space Reasoning
- Decomposition (JSON structure)
- Verification (Option A/B/C)
- Retry with feedback if score < 0.7

#### Layer 4: Agent Orchestration
- Parallel/sequential execution
- Self-correction with complexity-based retries
- Timing logs for each agent

#### Layer 5: LLM Integration
- LLM preference routing
- Provider abstraction (Anthropic, OpenAI, etc.)
- Cost tracking

#### Layer 6: Learning & Feedback (NEW)
- Replay buffer storage
- ACT-R activation updates
- Git signal updates (for code context)
- Pattern caching (score ≥ 0.8)

**Why it matters:** Clear separation of concerns, easier to implement/test

---

### 5. **Integration Points - MISSING DETAILS**

#### 5.1 MCP (Model Context Protocol) Integration
- **Purpose:** Standard protocol for context providers
- **Use case:** ContextMind as MCP server
- **Interface:** Standardized JSON-RPC API

#### 5.2 IDE Integration Hooks
- **File open events:** Boost activation for currently viewed functions
- **Cursor position:** Track which functions developer is working on
- **Copy/paste tracking:** Learn from developer's manual context gathering
- **Phase:** Post-MVP (WS5)

#### 5.3 Git Hooks
- **Post-commit:** Update activation signals
- **Pre-push:** Validate code quality before push
- **Phase:** MVP (basic), WS4 (advanced)

---

### 6. **Performance Characteristics - MISSING BENCHMARKS**

**What's Missing:**

#### 6.1 Code Context Retrieval Performance
- **cAST parsing:** ~50ms for 1000-line file
- **Git signal update:** ~100ms for 100 changed files
- **ACT-R activation:** ~10ms for 5000 functions
- **Total overhead:** ~200ms added to query

#### 6.2 Memory Footprint
- **cAST index:** ~10MB per 10k functions
- **Git signals:** ~5MB per 1000 commits
- **Replay buffer:** ~50MB per 1000 queries
- **Total:** ~100MB for medium codebase (10k functions, 1000 commits)

#### 6.3 Accuracy Targets
- **Token reduction:** 40% (from 50k to 30k tokens)
- **Context accuracy:** 92% (include correct functions)
- **Learning velocity:** +2-5% per session
- **Code quality:** No degradation vs full context

---

### 7. **Configuration Schema - MISSING CODE CONTEXT SECTION**

**What's Missing in config.json:**

```json
{
  "code_context": {
    "enabled": true,
    "cast": {
      "languages": ["python", "javascript", "go"],
      "chunk_level": "function",
      "max_chunk_size": 500,
      "include_dependencies": true
    },
    "git_integration": {
      "polling_interval_hours": 24,
      "track_staged_changes": true,
      "track_commits": true,
      "max_history_days": 180
    },
    "actr_params": {
      "bla_weight": 0.4,
      "cb_weight": 0.3,
      "sa_weight": 0.2,
      "decay_rate": 0.5
    },
    "retrieval": {
      "top_k": 10,
      "min_activation": 0.3,
      "max_tokens": 10000
    },
    "learning": {
      "success_boost": 0.25,
      "discovery_boost": 0.15,
      "failure_penalty": -0.075,
      "replay_buffer_size": 1000
    }
  }
}
```

---

### 8. **CLI Commands - MISSING CODE CONTEXT COMMANDS**

**What's Missing:**

```bash
# Code context initialization
aurora context init [--path /path/to/repo]
aurora context scan  # Parse codebase with cAST
aurora context status  # Show index stats

# Git integration
aurora context git-update  # Manual git signal update
aurora context git-status  # Show git signal stats

# Function activation queries
aurora context activate "authentication"  # Show function activation scores
aurora context search "password validation"  # Semantic + ACT-R search
aurora context graph auth.py:login  # Show dependency graph

# Analytics
aurora context heatmap  # Show most active functions
aurora context dead-code  # Find low-activation functions
aurora context coupling  # Show tight coupling

# Learning
aurora context learn  # Trigger offline learning
aurora context replay-stats  # Show replay buffer stats
```

---

### 9. **Testing Strategy - MISSING CODE CONTEXT TESTS**

**What's Missing:**

#### 9.1 cAST Tests
- Parse 10 real-world codebases (Python, JS, Go)
- Verify function extraction accuracy (>95%)
- Test dependency graph correctness
- Validate line-range mapping

#### 9.2 Git Integration Tests
- Mock git history with known patterns
- Verify activation updates from git diff
- Test line-level change tracking
- Validate signal accuracy

#### 9.3 Code Context Retrieval Tests
- 100 code queries with ground truth (manual annotation)
- Measure token reduction (target: 40%)
- Measure accuracy (target: 92%)
- Compare vs embedding-only baseline

#### 9.4 Learning Loop Tests
- Track activation changes over 50 queries
- Verify +2-5% accuracy improvement
- Test hindsight relabeling (discovery)
- Validate negative learning (failures)

---

### 10. **Documentation - MISSING SECTIONS**

**What's Missing:**

#### 10.1 CODE_CONTEXT.md (entire document)
- Overview of ContextMind subsystem
- How cAST works (tree-sitter integration)
- Git integration explained
- ACT-R activation formula for code
- Learning loop mechanics
- Reporting capabilities
- Setup guide

#### 10.2 ARCHITECTURE.md updates
- Add Layer 2b: Code Context Retrieval (between ACT-R and SOAR)
- Add data flow diagram showing ContextMind integration
- Add decision tree: When to use code context vs general patterns

#### 10.3 API.md updates
- Code context API endpoints
- Programmatic access to function activation scores
- Integration points for IDEs/tools

---

## Summary: What Needs to Be Added

### Absolutely Critical (MVP Blockers)
1. **ContextMind subsystem** - Entire architecture (cAST + git + ACT-R for code)
2. **Repository structure** - Clear folder hierarchy with all modules
3. **Layer 6: Learning & Feedback** - Replay buffer + activation updates
4. **Config schema** - code_context section
5. **CLI commands** - Code context management

### Important (MVP Nice-to-Have)
6. **Performance benchmarks** - Overhead, memory, accuracy targets
7. **Integration points** - MCP, IDE hooks, git hooks
8. **Testing strategy** - Code context test coverage

### Can Defer (Post-MVP)
9. **Reporting & analytics** - 7 use cases for codebase insights
10. **QLoRA fine-tuning** - Advanced learning (WS4)
11. **IDE integration** - Advanced signals (WS5)

---

## Questions for User

Before integrating these missing components into the unified spec, I need clarification:

### Q1: ContextMind Scope
**Question:** Is ContextMind (code context management) part of MVP or Phase 2?

**Context from docs:**
- `ACT-R-Code-Context-Management-PRD.md` says "Phase: Post-AURORA MVP (WS3-5)"
- But `AURORA-REFINED-ARCHITECTURE.md` includes it in "WS3 MVP Architecture"

**Options:**
- A) Include basic cAST + git in MVP (retrieval only, no learning)
- B) Defer entire ContextMind to Phase 2
- C) Include full ContextMind in MVP

### Q2: Repository Structure Detail Level
**Question:** How detailed should the repo structure be in the unified spec?

**Options:**
- A) High-level only (src/, config/, data/)
- B) Module-level (src/core/, src/memory/, src/context/)
- C) File-level (every .py file listed)

### Q3: Learning Layer Emphasis
**Question:** Should Replay HER + QLoRA be prominently featured in MVP spec or mentioned as "Phase 2"?

**Context from docs:**
- `AURORA-REFINED-ARCHITECTURE.md` includes full learning layer
- But unified spec currently focuses on verification, not learning

**Options:**
- A) MVP = verification only, defer learning to Phase 2
- B) MVP = verification + basic learning (activation updates)
- C) MVP = full learning layer (Replay HER + QLoRA)

### Q4: Configuration Complexity
**Question:** How much configuration should be exposed in MVP?

**Current unified spec:** ~100 lines of config
**With ContextMind added:** ~300+ lines of config

**Options:**
- A) Keep config minimal, add ContextMind config in Phase 2
- B) Include full config now with good defaults
- C) Split config into multiple files (core.json, context.json, etc.)

### Q5: Documentation Priority
**Question:** Which missing documentation sections are MUST-HAVE for MVP handoff?

**Missing docs:**
- CODE_CONTEXT.md (40 pages)
- Repository structure section (5 pages)
- Layer architecture updates (10 pages)
- Performance benchmarks (5 pages)
- Testing strategy updates (5 pages)

**Options:**
- A) Just add repo structure + layer updates (15 pages)
- B) Add repo + layers + CODE_CONTEXT.md (55 pages)
- C) Add everything (65 pages)

---

## Recommendation

Based on document analysis, I recommend:

**For MVP (AURORA-MVP-UNIFIED-SPEC v3.1):**
1. ✅ Add **repository structure** (module-level detail)
2. ✅ Add **Layer 6: Learning & Feedback** (basic activation updates)
3. ✅ Add **ContextMind overview** (architecture only, defer full implementation to Phase 2)
4. ✅ Add **config schema** for code_context (with "enabled: false" by default)
5. ✅ Add **performance benchmarks** (targets, not implementation)

**Defer to Phase 2:**
- Full ContextMind implementation (cAST + git)
- Reporting & analytics
- QLoRA fine-tuning
- IDE integration

**Rationale:** Keep MVP focused on verification-driven reasoning. Add ContextMind as architecture placeholder so structure is ready, but implement in Phase 2 after core is validated.

---

**Next step:** Please answer Q1-Q5 so I can integrate the right components into the unified spec.
