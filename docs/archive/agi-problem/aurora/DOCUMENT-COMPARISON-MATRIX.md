# Aurora Document Comparison Matrix

**Purpose:** Map what's in each document to design unified structure

---

## Document Inventory

| Document | Size | Focus | Key Contribution |
|----------|------|-------|------------------|
| **AURORA-Framework-PRD.md** | 1783 lines | Product requirements for AURORA orchestration | User stories, personas, capabilities, original 5-layer design |
| **AURORA-Framework-SPECS.md** | 1535 lines | Technical specs for AURORA orchestration | Layer algorithms, pseudocode, execution flows, CLI |
| **AURORA-MVP-Correction.md** | 2700 lines | Critical correction adding verification | Verification layer (Options A/B/C), JSON contracts, scoring, repo structure |
| **ContextMind-PRD.md** | 2331 lines | Product requirements for code context | cAST, git integration, code-specific ACT-R, learning loop |
| **ContextMind-SPECS.md** | 1064 lines | Technical specs for code context | Algorithms, retrieval, learning, reporting, integration |

**Total:** 9,413 lines across 5 documents

---

## Content Mapping by Topic

### 1. Executive Summary & Problem Statement

| Topic | AURORA PRD | AURORA SPECS | MVP Correction | ContextMind PRD | ContextMind SPECS |
|-------|------------|--------------|----------------|-----------------|-------------------|
| **Problem definition** | ✅ LLM reasoning failures | ✅ 25-30% accuracy | ✅ Why orchestration alone fails | ✅ Code context bottleneck | ✅ Token budget limits |
| **Solution overview** | ✅ 5-layer framework | ✅ SOAR + ACT-R | ✅ + Verification layer | ✅ cAST + git + ACT-R | ✅ 3-layer architecture |
| **Value proposition** | ✅ Cost + accuracy | - | ✅ Catches reasoning errors | ✅ 40% token reduction | - |
| **Target users** | ✅ 5 personas | - | - | ✅ 5 personas (different) | - |

**Consolidation:** Need ONE problem statement covering both AURORA orchestration + ContextMind code context.

---

### 2. Architecture & Layers

| Component | AURORA PRD | AURORA SPECS | MVP Correction | ContextMind PRD | ContextMind SPECS |
|-----------|------------|--------------|----------------|-----------------|-------------------|
| **Layer 1: Assessment** | ✅ Hybrid assessment | ✅ Keyword + LLM | - | - | - |
| **Layer 2: ACT-R Memory** | ✅ General patterns | ✅ Activation formula | ✅ Dual ACT-R (Part 21) | ✅ Code-specific ACT-R | ✅ BLA + CB + SA - decay |
| **Layer 3: SOAR Reasoning** | ✅ Decomposition | ✅ Impasse detection | ✅ + Verification | - | - |
| **Layer 4: Orchestration** | ✅ Agent routing | ✅ Execution order | ✅ + Self-correction | - | - |
| **Layer 5: LLM Integration** | ✅ Pluggable LLMs | ✅ Synthesis | - | - | - |
| **Layer 6: Learning** | - | ✅ Partial | ✅ Replay HER (Part 12) | ✅ Learning loop | ✅ Hindsight relabel |
| **ContextMind Layers** | - | - | ✅ Integration (Part 13) | ✅ cAST + Git + Retrieval | ✅ Full algorithm |

**Consolidation:** Need UNIFIED layer model showing where ContextMind fits.

---

### 3. Verification Layer (Critical Addition)

| Aspect | AURORA PRD | AURORA SPECS | MVP Correction | ContextMind PRD | ContextMind SPECS |
|--------|------------|--------------|----------------|-----------------|-------------------|
| **Problem analysis** | - | - | ✅ Part 1-2 (orchestration ≠ reasoning) | - | - |
| **Verification architecture** | - | - | ✅ DECOMPOSE → VERIFY → AGENTS → VERIFY | - | - |
| **Option A: Self-verify** | - | - | ✅ Same LLM checks itself | - | - |
| **Option B: Adversarial** | - | - | ✅ Second LLM critiques | - | - |
| **Option C: Deep reasoning** | - | - | ✅ Multi-step with RAG (Phase 2) | - | - |
| **Scoring system** | - | - | ✅ 0-1 scale, thresholds | - | - |
| **JSON contracts** | - | - | ✅ Decomposition, verification, results | - | - |
| **Self-correction** | - | - | ✅ Retry with feedback | - | - |

**Consolidation:** Verification is THE core innovation. Must be front-and-center.

---

### 4. Code Context Management (ContextMind)

| Component | AURORA PRD | AURORA SPECS | MVP Correction | ContextMind PRD | ContextMind SPECS |
|-----------|------------|--------------|----------------|-----------------|-------------------|
| **cAST chunking** | - | - | ✅ Mention (Part 13) | ✅ Function-level | ✅ Tree-sitter wrapper |
| **Git integration** | - | - | ✅ Mention (Part 13) | ✅ Polling + signals | ✅ Line-level tracking |
| **Code ACT-R** | - | - | ✅ Part 21 (dual activation) | ✅ Full formula | ✅ Algorithm |
| **Retrieval pipeline** | - | - | - | ✅ Semantic + ACT-R | ✅ Top-K selection |
| **Learning loop** | - | - | - | ✅ Success/discovery/failure | ✅ Replay HER |
| **Reporting** | - | - | - | ✅ 7 use cases | ✅ Analytics details |

**Consolidation:** ContextMind is a SUBSYSTEM of AURORA. Needs clear integration point.

---

### 5. Implementation Details

| Aspect | AURORA PRD | AURORA SPECS | MVP Correction | ContextMind PRD | ContextMind SPECS |
|--------|------------|--------------|----------------|-----------------|-------------------|
| **Repository structure** | - | - | ✅ Part 26 (detailed) | - | - |
| **CLI commands** | ✅ Basic | ✅ Detailed | - | - | - |
| **Pseudocode** | - | ✅ 4 implementations | - | - | ✅ Retrieval algorithm |
| **Execution flows** | - | ✅ 3 scenarios | ✅ Simple/medium/complex | - | - |
| **Testing strategy** | - | ✅ Unit + integration | - | - | ✅ Code context tests |
| **Performance targets** | ✅ <8s, 90% success | - | - | ✅ 40% token reduction | ✅ 50ms cAST, 10ms ACT-R |

**Consolidation:** Combine implementation details from both systems.

---

### 6. Configuration & Setup

| Aspect | AURORA PRD | AURORA SPECS | MVP Correction | ContextMind PRD | ContextMind SPECS |
|--------|------------|--------------|----------------|-----------------|-------------------|
| **Config file** | - | - | ✅ Complete schema (Appendix C) | - | - |
| **LLM providers** | ✅ Pluggable | ✅ Abstraction | ✅ Dual LLM (reasoning + solving) | - | - |
| **Agent registry** | ✅ Discovery | ✅ JSON schema | - | - | - |
| **Code context config** | - | - | - | ✅ Languages, polling | ✅ Parameters |
| **Installation** | - | - | ✅ Part 25 (pip, git, docker) | - | - |

**Consolidation:** Single config.json with all settings.

---

### 7. User Stories & Acceptance Criteria

| Category | AURORA PRD | AURORA SPECS | MVP Correction | ContextMind PRD | ContextMind SPECS |
|----------|------------|--------------|----------------|-----------------|-------------------|
| **Epics** | ✅ 7 epics, 23 stories | - | - | ✅ 5 user stories | - |
| **Assessment** | ✅ Story 1.1-1.3 | - | - | - | - |
| **Memory** | ✅ Story 2.1-2.3 | - | - | - | - |
| **Reasoning** | ✅ Story 3.1-3.3 | - | - | - | - |
| **Orchestration** | ✅ Story 4.1-4.5 | - | - | - | - |
| **Multi-turn** | ✅ Story 5.1-5.3 | - | - | - | - |
| **Transparency** | ✅ Story 6.1-6.3 | - | - | - | - |
| **Code context** | - | - | - | ✅ Story about retrieval | - |

**Consolidation:** Keep AURORA stories, add ContextMind stories.

---

### 8. Success Metrics & KPIs

| Metric | AURORA PRD | AURORA SPECS | MVP Correction | ContextMind PRD | ContextMind SPECS |
|--------|------------|--------------|----------------|-----------------|-------------------|
| **Reasoning accuracy** | ✅ >90% | - | ✅ >85% corrected | - | - |
| **Cost efficiency** | ✅ 40% lower | - | - | - | - |
| **Response time** | ✅ <8s | - | - | - | - |
| **Token reduction** | - | - | - | ✅ 40% | ✅ From 50k to 30k |
| **Code accuracy** | - | - | - | ✅ 92% | - |
| **Learning velocity** | ✅ +5% per week | - | - | ✅ +2-5% per session | - |

**Consolidation:** Unified metrics covering both reasoning + code context.

---

### 9. Roadmap & Phasing

| Phase | AURORA PRD | AURORA SPECS | MVP Correction | ContextMind PRD | ContextMind SPECS |
|-------|------------|--------------|----------------|-----------------|-------------------|
| **MVP (WS3)** | ✅ Full 5-layer | - | ✅ + Verification | ✅ cAST + git + basic ACT-R | ✅ Retrieval only |
| **Phase 2 (WS4)** | ✅ RAG, multi-agent | - | ✅ Option C, reporting | ✅ Learning loop, spreading | ✅ Advanced analytics |
| **Phase 3 (WS5)** | - | - | - | ✅ IDE integration, transfer learning | - |
| **Timeline** | - | - | ✅ Part 16 (4-week MVP, 4-week Phase 2) | ✅ WS3-5 breakdown | ✅ 12 weeks total |

**Consolidation:** Single roadmap showing both AURORA core + ContextMind integration.

---

## Key Insights from Comparison

### What's Unique in Each Document

**AURORA-Framework-PRD.md:**
- ✅ User personas (5 detailed personas)
- ✅ User stories (23 stories across 7 epics)
- ✅ Competitive positioning
- ✅ Non-functional requirements (performance, scalability, security)

**AURORA-Framework-SPECS.md:**
- ✅ Keyword taxonomy (detailed complexity keywords)
- ✅ Execution flow pseudocode (4 implementations)
- ✅ SOAR-LLM integration details
- ✅ CLI interface spec

**AURORA-MVP-Correction.md:**
- ✅ **THE CORE INSIGHT:** Orchestration alone doesn't solve reasoning
- ✅ Verification layer (Options A/B/C) - CRITICAL
- ✅ JSON contracts (structured reasoning)
- ✅ Scoring system (0-1 scale, pass/retry/fail)
- ✅ Repository structure (Part 26)
- ✅ Dual ACT-R (reasoning vs code)
- ✅ Complete config.json schema
- ✅ Feedback handling matrix
- ✅ Integration with AI agents (Claude Code, etc.)

**ContextMind-PRD.md:**
- ✅ Code context problem (token budget bottleneck)
- ✅ cAST architecture (function-level chunking)
- ✅ Git integration strategy
- ✅ Code-specific personas
- ✅ Learning loop (Replay HER)
- ✅ Reporting & analytics (7 use cases)
- ✅ Financial projections

**ContextMind-SPECS.md:**
- ✅ cAST algorithms (tree-sitter wrapper)
- ✅ Git line-level tracking algorithm
- ✅ Code ACT-R retrieval algorithm
- ✅ Learning mechanisms (hindsight relabel)
- ✅ Edge cases (cold start, cycles, drift)
- ✅ Performance characteristics

### What's Duplicated (Needs Merging)

1. **ACT-R memory:** Covered in all 5 documents with different emphasis
2. **Architecture overview:** Each doc has its own view
3. **Success metrics:** Different but overlapping
4. **Roadmap:** Inconsistent phasing across documents

### What's Missing Entirely

1. **LLM preference routing** (from our discussion)
2. **Cost budget enforcement** (from our discussion)
3. **Guardrails** (from our discussion)
4. **Headless mode** (from our discussion)
5. **Timing logs** (from our discussion)

---

## Proposed Unified Structure

I propose organizing the unified spec into **4 major parts:**

### **PART A: PRODUCT FOUNDATION** (Who, What, Why)
1. Executive Summary
2. Problem Statement (reasoning + code context)
3. Solution Overview (AURORA = verification + orchestration + ContextMind)
4. Target Users & Personas (merge 10 personas)
5. Value Propositions (cost, accuracy, learning)
6. Competitive Positioning

### **PART B: ARCHITECTURE & DESIGN** (How It Works)
7. Complete Layer Architecture
   - Layer 0: Input Processing (guardrails, budget)
   - Layer 1: Assessment & Discovery
   - Layer 2: ACT-R Memory (general + code)
   - Layer 3: SOAR Reasoning + Verification ← CORE
   - Layer 4: Agent Orchestration + Self-Correction
   - Layer 5: LLM Integration + Routing
   - Layer 6: Learning & Feedback

8. ContextMind Subsystem (detailed)
   - cAST: Function-level chunking
   - Git Integration: Continuous signals
   - Code ACT-R: Activation formula
   - Retrieval Pipeline: Semantic + ranking
   - Learning Loop: Replay HER

9. Verification Layer (Options A/B/C) ← CRITICAL
10. JSON Contracts & Data Structures
11. Scoring System & Thresholds
12. Self-Correction & Retry Logic

### **PART C: IMPLEMENTATION** (How to Build)
13. Repository Structure
14. Configuration Schema
15. CLI Interface
16. Algorithms & Pseudocode
17. Execution Flows (3 scenarios)
18. Integration Points (MCP, IDE, git hooks)
19. Performance Characteristics

### **PART D: DELIVERY** (How to Ship)
20. User Stories & Acceptance Criteria (30+ stories)
21. Functional Requirements
22. Non-Functional Requirements
23. Success Metrics & KPIs
24. Testing Strategy
25. Roadmap & Phasing
26. Installation & Deployment
27. Risk Mitigation

---

## Next Steps

**Option 1: I build the unified spec section-by-section**
- You review each part as I complete it
- Allows for adjustments along the way
- ~8-10 hours of work

**Option 2: I create a detailed outline first**
- Expand the 4-part structure above with subsections
- You approve the outline
- Then I write the full doc
- ~10-12 hours of work

**Option 3: Priority-driven approach**
- You tell me which sections are MUST-HAVE for MVP
- I consolidate only those sections first
- Defer nice-to-have sections
- ~4-6 hours of work

**Which option do you prefer?**

Or do you have a different approach in mind?
