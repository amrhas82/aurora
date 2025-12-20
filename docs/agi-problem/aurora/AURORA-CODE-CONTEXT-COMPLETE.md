# ACT-R Code Context Management - Complete Specification

**Status**: ✅ COMPLETE - Ready for Implementation Planning
**Date**: December 9, 2025
**Version**: 2.0 (Specs + PRD with Reporting)

---

## Executive Summary

**ACT-R Code Context Management** is a post-AURORA MVP feature that solves the code context bottleneck for large codebases. It combines:

1. **cAST** - Parse code into function-level semantic units (not file-level)
2. **Git Integration** - Continuous activation signals via git history + polling
3. **ACT-R** - Dynamic ranking by actual importance (frequency, recency, dependencies)
4. **Learning Loop** - Improve accuracy over time (2-5% per session)
5. **Reporting** - Rich analytics on codebase evolution and team patterns

**Result**: 40% token reduction @ 92% accuracy + 7 detailed reporting capabilities

---

## Documents

### Primary Documents

| Document | Location | Size | Purpose |
|----------|----------|------|---------|
| **SPECS** | `/research/solution-development/ACT-R-Code-Context-Management-SPECS.md` | 1065 lines | 15 technical sections + algorithms |
| **PRD** | `/research/solution-development/ACT-R-Code-Context-Management-PRD.md` | ~2000 lines | 16 product sections + 5 personas |
| **Summary** | `/ACT-R-CODE-CONTEXT-MGMT-SUMMARY.md` | 200 lines | Quick reference guide |

### What Each Document Contains

**SPECS.md**:
- 15 Sections covering technical architecture
- Algorithms (retrieval, learning, spreading activation)
- Data structures (state models)
- Integration points (git, IDE, LLM API)
- Edge cases (cold start, cycles, drift)
- Performance characteristics
- **NEW**: Section 15 - Reporting & Analytics (225 lines, 7 use cases)

**PRD.md**:
- Executive summary
- Product overview + vision
- Critical architectural decisions (5 decisions documented)
- Problem statement with 3 scenarios
- 5 detailed user personas
- 4 core value propositions
- 8+ functional requirements
- Non-functional requirements (performance, accuracy, reliability)
- 5 user stories
- Success metrics & validation plan
- Competitive positioning
- Go-to-market strategy
- **Updated**: Roadmap phases (WS4-5 include reporting)

**Summary.md**:
- 30-second solution overview
- Three-layer architecture
- Git integration explanation
- Architectural decisions table
- Implementation scope
- Success metrics
- Quick answers to key questions

---

## Key Decisions Documented

### 1. Function-Level Chunking (Not File-Level)

**Why**:
- Large files (500+ lines) contain 10-20 unrelated functions
- File-level destroys precision; function-level enables token efficiency
- Dependencies map to functions, not files
- Enables git line-range mapping to functions

**Implementation**:
- ~700-line wrapper around tree-sitter
- Module structure: core, extractors, dependencies, languages
- Straightforward extension (~100 lines per language)

### 2. Git as Integral Signal Source

**Why**:
- Already tracks everything (frequency, recency)
- Daily/weekly polling via `git add .`
- No additional tools or privacy concerns needed
- Provides validation signals for learning loop

**How**:
- Initialization: Parse git log for frequency per function
- Continuous: Poll git diff (file-level) + map to functions (cAST line ranges)
- Validation: Check if LLM-modified code matches git changes

### 3. Line-Level Change Tracking Algorithm

**How it works**:
```
Git diff lines: 45-52 (file-level)
cAST function: authenticate() [lines 45-52]
Overlap: 100% → boost magnitude = 0.30
Result: Only authenticate() boosted, not entire file
```

### 4. cAST Is a Wrapper (Not a Library)

**Why**:
- tree-sitter is the library (AST parsing)
- cAST is our extraction layer (~700 lines)
- Focused on: extraction, line ranges, dependency tracking

**Structure**:
- Core: Main parser (~200 lines)
- Extractors: Function/class identification (~150 lines)
- Dependencies: Call/import tracking (~100 lines)
- Languages: Language-specific logic (~100 lines each)
- Tests: Full coverage (~200 lines)

### 5. Learning-Driven Evolution (Start Simple)

**MVP (WS3)**: Core ACT-R + cAST (no spreading activation, no SOAR-Assist)
**WS4**: Add learning loop + spreading activation
**WS5**: Add advanced analytics + reporting
**Future**: Advanced features based on learnings

---

## Core Features

### Layer 1: cAST Chunking
- Function-level chunks with precise line ranges
- Language support: Python, JS, Go, Rust, Java, C++
- Dependency graph extraction
- ~700 lines for MVP (Python + JavaScript)

### Layer 2: Semantic Embedding
- Find semantically similar functions
- Works better with good chunks (from cAST)
- Reuse existing embedding models

### Layer 3: ACT-R Activation
- Formula: A(chunk) = BLA + CB + SA - decay
- BLA: frequency from git history
- CB: relevance to current query
- SA: spreading via dependency graph
- decay: time-based forgetting

### Learning Loop
- Positive feedback: chunk was used (+0.15 activation)
- Discovery feedback: chunk was missing (+0.25 activation)
- Negative feedback: chunk was unused (-0.075 activation)
- Result: 2-5% accuracy improvement per session

### Reporting & Analytics
- 7 core reporting use cases
- 3-phase implementation (WS4-5 + future)
- Dashboard, exports, alerts, recommendations

---

## Reporting Capabilities

### WS4 Phase 2 (Basic Reporting)
1. **Activation Change Reports** - Top 10 most/least increased functions
2. **File-Level Summary** - Aggregate view of file importance
3. **Historical Trends** - 90-day activation evolution
4. **Query Effectiveness** - Hit rates by query type

### WS5 Phase 3 (Advanced Analytics)
5. **Developer Activity Patterns** - Who focuses on which code
6. **Dependency Analysis** - How dependencies evolve
7. **Codebase Health Dashboard** - Overall metrics + recommendations

---

## Timeline & Effort

### Phase 1: MVP (WS3) - 12 weeks
- cAST chunking (Python, JavaScript)
- Git initialization + polling
- Basic ACT-R (BLA + CB)
- Token budget-aware selection
- **Team**: 2 engineers, 1 PM
- **Goal**: 40% token reduction, 85% accuracy

### Phase 2: Learning & Reporting (WS4) - 12 weeks
- Spreading activation
- Learning feedback loops
- Basic reporting (4 types)
- Time-series database
- **Team**: 2 engineers, 1 PM, 1 Data Scientist, 1 Analytics Engineer
- **Goal**: 92% accuracy, visible learning curve, reports available

### Phase 3: Advanced Analytics (WS5) - 12 weeks
- Per-developer profiles
- Advanced reporting (7 total)
- Dashboard + exports
- Alerts & recommendations
- **Team**: 2-3 engineers, 1 PM, 1 Data Scientist, 1 Analytics Engineer
- **Goal**: Actionable insights, 80%+ team satisfaction

### Phase 4: Scale & Optimization (Post-WS5) - Ongoing
- Additional languages
- Performance optimization
- Partner integrations
- Research publication

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Token Reduction | 40% | Tokens per query with ACT-R vs. baseline |
| Accuracy | ≥92% | % of retrieved chunks actually used |
| Learning Velocity | 2-5%/session | Accuracy improvement over first 20 sessions |
| False Positive Rate | <15% | Retrieved but unused |
| Polling Latency | <1 sec | Daily/weekly git polling time |
| Retrieval Latency | <500ms | For 100k+ functions |
| Hit Rate | >90% | Needed chunks in top-100 candidates |

---

## Integration Points

### With AURORA
- ACT-R Code Context is post-MVP feature for AURORA
- Complements SOAR-Assist orchestration
- Shares activation state storage
- Uses AURORA logging for feedback

### With Development Tools
- Git (native integration)
- LLM APIs (Claude, GPT-4, etc.)
- Test frameworks (via coverage data)
- IDEs (via telemetry, future phase)

---

## Files in This Solution

### Core Specifications
- `/research/solution-development/ACT-R-Code-Context-Management-SPECS.md` - 1065 lines
- `/research/solution-development/ACT-R-Code-Context-Management-PRD.md` - ~2000 lines

### Quick Reference
- `/ACT-R-CODE-CONTEXT-MGMT-SUMMARY.md` - 200 lines

### Related
- `/aurora/AURORA-Framework-SPECS.md` - Parent framework
- `/CONTINUATION.md` - Project status
- `/START-HERE.md` - Navigation guide

---

## Implementation Readiness

### ✅ Complete & Documented
- Technical architecture (3 layers + git integration)
- Implementation details (700 lines, module structure)
- Functional requirements (8+ detailed requirements)
- Success criteria (measurable metrics)
- Timeline & phasing (WS3-5)
- Risk mitigation (7 identified risks)
- Reporting & analytics (7 use cases)
- Team structure (phase-by-phase staffing)

### ✅ Ready For
- Task generation via 2-generate-tasks agent
- Development planning
- Team review & feedback
- Developer handoff

### 🔄 Next Step
Generate implementation tasks using 2-generate-tasks agent with PRD as input

---

## Quick Reference: What's Where

**For a 30-minute overview**:
1. Read: `/ACT-R-CODE-CONTEXT-MGMT-SUMMARY.md`
2. Scan: `/research/solution-development/ACT-R-Code-Context-Management-PRD.md` sections 1-1.5

**For implementation planning**:
1. Read: Summary.md (10 min)
2. Read: PRD sections 1-5 (1 hour)
3. Read: SPECS section 3 (40 min)
4. Review: PRD Functional Requirements (30 min)

**For task generation**:
- Use 2-generate-tasks agent with PRD as input
- Agent will break into actionable development tasks

**For deep technical details**:
- SPECS sections 6-15 (retrieval algorithm, learning, reporting, risks, performance)

---

## Competitive Advantages

1. **Only learning system** - 2-5% improvement per session
2. **Explainable** - Every retrieval shows activation breakdown
3. **Zero config** - Works immediately on any codebase
4. **Cost-effective** - 40% token reduction is industry-leading
5. **Integrated** - Uses existing git infrastructure
6. **Extensible** - Add languages in ~100 lines each
7. **Observable** - Rich reporting & analytics (7 report types)

---

## Created By

- **Author**: Claude Code (with human guidance)
- **Phase**: Interactive elicitation (Dec 8-9, 2025)
- **Input**: 
  - Technical specs from research phase
  - Architectural decision clarifications
  - Reporting & analytics vision
- **Output**: 
  - Complete SPECS document (15 sections)
  - Complete PRD (16 sections + 5 personas)
  - Quick reference guide
  - This summary document

---

**Status**: ✅ READY FOR IMPLEMENTATION PLANNING

**Next Action**: Generate development tasks via 2-generate-tasks agent

**Questions?** Consult `/ACT-R-CODE-CONTEXT-MGMT-SUMMARY.md` or individual spec/PRD sections
