# ACT-R Code Context Management - Quick Reference

**Status**: Specifications & PRD Complete | Ready for Task Generation
**Date**: December 9, 2025
**Location**: `/research/solution-development/`

---

## The Solution in 30 Seconds

**Problem**: Large codebases exceed token budgets; LLMs see 50 semantically similar functions and can't prioritize.

**Solution**:
1. **cAST** (Code Abstract Syntax Tree) - chunk at FUNCTION-level with line ranges
2. **Git integration** - track file changes, map to functions, boost activation
3. **ACT-R** (Adaptive Control of Thought) - dynamically rank by activation (BLA + CB + SA - decay)
4. **Learning loop** - improve activation based on successes/failures

**Result**: 40% token reduction @ 92% accuracy

---

## Three-Layer Architecture

### Layer 1: cAST (Code Chunking at Function-Level)
- **What**: Wrapper (~700 lines) around tree-sitter AST parser
- **Granularity**: FUNCTION-LEVEL (not file-level)
- **Why function-level**:
  - Precision (file has 10 unrelated functions; function is atomic unit)
  - Token efficiency (include only `validate_password()`, not entire file)
  - Git integration (cAST line ranges enable git diff mapping)
- **Output**: Functions with metadata (name, lines, dependencies)
- **Languages**: Python, JavaScript, Go, Rust, Java (via tree-sitter)

### Layer 2: Semantic Embedding
- Find semantically similar functions to user query
- Reuse existing embedding models (OpenAI, local)
- Works better with good chunks (from cAST) than arbitrary tokens

### Layer 3: ACT-R Activation Prioritization
- **Formula**: A(chunk) = BLA + CB + SA - decay
  - **BLA**: Base-Level Activation (frequency from git + learning)
  - **CB**: Context Boost (relevance to current query)
  - **SA**: Spreading Activation (related functions via dependency graph)
  - **decay**: Time-based forgetting (old code naturally cools)
- **Learning**: 2-5% accuracy improvement per session

---

## Git Integration (Core to Solution)

### Why Git?
- Already tracks everything → why duplicate?
- Provides three critical signals:

### Three Signals

| Signal | Source | Example |
|--------|--------|---------|
| **Initialization** | `git log --all` | authenticate() edited 47 times → BLA=0.8 |
| **Continuous** | `git diff` (daily/weekly polling) | Lines 45-52 changed → boost authenticate() |
| **Validation** | LLM outcomes + git changes | LLM modified X; git confirms X changed → learning |

### Line-Level Mapping (cAST + Git)

```
Git diff: lines 45-52 changed in auth.py
cAST: authenticate() is lines 45-52

Overlap: 100% → BLA += 0.30 (8 lines changed / 8 total lines)

Result: Only authenticate() boosted, not entire file
```

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **Function-level chunks** | Files too coarse; functions are atomic units |
| **Git as signal source** | Already tracks everything; daily/weekly polling only |
| **Decay is a feature** | Old unused code should cool; helps manage context |
| **cAST is a wrapper** | ~700 lines; wraps tree-sitter; focused on extraction + line ranges |
| **Learning-driven evolution** | Start simple; only add complexity if needed (SOAR-Assist later) |

---

## Implementation Scope

### MVP (WS3): 4-6 weeks
- cAST parsing (Python + JavaScript)
- Git initialization + periodic polling
- Basic activation (BLA + CB)
- Retrieval ranking and token-aware selection
- Integration with LLM prompts

**Code**: ~700 lines total (cAST module)

### WS4: Sophistication Phase
- Spreading activation over dependency graph
- Learning loop (feedback collection + parameter tuning)
- Time-based decay implementation

### WS5: Optimization Phase
- Per-developer activation profiles
- Transfer learning across codebases
- IDE telemetry integration (optional)

---

## Key Documents

| Document | Location | Purpose |
|----------|----------|---------|
| **SPECS** | `ACT-R-Code-Context-Management-SPECS.md` | Technical foundation (14 sections) |
| **PRD** | `ACT-R-Code-Context-Management-PRD.md` | Product requirements (16 sections + personas) |
| **This** | `ACT-R-CODE-CONTEXT-MGMT-SUMMARY.md` | Quick reference (you are here) |

All in: `/home/hamr/Documents/PycharmProjects/OneNote/smol/agi-problem/research/solution-development/`

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Token reduction | 40% (baseline: 50k tokens → target: 30k tokens) |
| Accuracy | ≥92% (chunks actually used in generation) |
| Learning curve | 2-5% improvement per session for first 20 |
| False positive rate | <15% (retrieved but unused) |
| Polling latency | <1 second |

---

## Questions Answered During Elicitation

**Q1: Is git integral to the solution?**
- YES. Without git, we lose frequency/recency/validation signals.

**Q2: How capture line-level changes per function?**
- Git diff (file-level lines) + cAST line ranges (functions) → overlap = affected functions.
- Magnitude = lines_changed / total_lines_in_function.

**Q3: Is cAST a library?**
- We develop it (~700 lines wrapper around tree-sitter).
- tree-sitter is the library; cAST is our extraction layer.

---

## Ready for Task Generation

✅ Specifications complete
✅ Product requirements documented
✅ Architectural decisions clarified
✅ Implementation scope defined
✅ Success metrics established
✅ Phasing planned (WS3-5)

**Next Step**: Invoke `2-generate-tasks` agent to break PRD into development tasks.

---

**Created**: December 9, 2025
**For**: ACT-R-Based Code Context Management System (Post-AURORA MVP)
**Status**: Ready for implementation planning
