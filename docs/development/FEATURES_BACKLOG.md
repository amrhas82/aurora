# Aurora Features Backlog

## Strategic Focus

**Aurora's value**: Planning layer (gap detection, pre-execution review) that LangChain/CrewAI/ADK don't provide.

**Differentiator:**
- They solve: "How to coordinate agents talking"
- Aurora solves: "How to reliably execute agent plans with oversight and recovery"

---

## Document Memory: PDF/DOCX Indexing

**Goal:** Make documents (PDFs, Word docs, markdown) accessible to AI chat agents via Aurora's memory system.

**CLI Interface:**
```bash
aur mem index /path/to/docs --type doc
aur mem index report.pdf --type doc
aur mem index ./manuals/ --type doc  # batch
```

**Architecture:** Fork early (parse), merge late (store/search)

```
Code Path                     Doc Path
─────────                     ────────
tree-sitter (cAST)            pymupdf / python-docx
   ↓                              ↓
AST → functions/classes       TOC/headers → sections
   ↓                              ↓
git blame/history             (skip - binary files)
   ↓                              ↓
CodeChunk                     DocChunk
   └──────────────┬───────────────┘
                  ▼
            SQLiteStore
                  ↓
          HybridRetriever (BM25 + ACT-R + semantic)
```

**Section Detection Strategy (Tiered):**

1. **Tier 1 - Explicit Structure (Best)**
   - PDF: TOC metadata (many PDFs have it embedded)
   - DOCX: Heading styles (Word's Heading 1/2/3)
   - Markdown: `#`, `##`, `###`

2. **Tier 2 - Inferred Structure (Fallback)**
   - PDF: Font size jumps, bold lines, numbered patterns (`1.0`, `1.1.2`)
   - DOCX: Font formatting if no heading styles used

3. **Tier 3 - Paragraph-Based (Last Resort)**
   - No structure detected → chunk by paragraph clusters
   - Use 10-20% overlap to preserve context at edges

**Chunk Model:**
```python
DocChunk(
    chunk_id="...",
    file_path="report.pdf",
    element_type="section",  # or "paragraph", "table"
    name="2.1 Installation Requirements",
    section_path=["Chapter 2", "2.1 Installation Requirements"],
    page_start=12,
    page_end=14,
    content="...",
    parent_chunk_id="...",  # hierarchy reference
)
```

**What docs reuse:**
- ✅ Same chunking infrastructure
- ✅ ACT-R activation/decay curves
- ✅ Hybrid retrieval (BM25 + activation + semantic)
- ✅ `section_path` metadata (like code has `class.method`)

**What docs skip:**
- ❌ tree-sitter / cAST
- ❌ git blame/history (binary files don't diff)

**Module Location:**
```
packages/context-doc/
  src/aurora_context_doc/
    parser/
      pdf.py      # PyMuPDF (fast, good TOC access)
      docx.py     # python-docx
    chunker.py    # section-aware splitting
    indexer.py    # orchestrates parse → chunk → store
```

**Libraries:**
- PDF: `pymupdf` (fast, good TOC) or `pdfplumber` (better tables)
- DOCX: `python-docx`

**Effort:** Medium (~300-400 LOC for core, more for edge cases)

**Status:** Proposed

---

## Ideas to Steal: subtask

**Repo:** https://github.com/zippoxer/subtask

**What it does:** Parallel task management for Claude Code using Git worktrees, interactive agent communication, and TUI for progress visualization.

**Limitation:** Claude Code-only (not multi-tool compatible) - significant loss for Aurora's 20+ tool support.

**Ideas worth stealing (if adaptable to multi-tool):**

1. **Git Worktree Isolation** (~150 LOC)
   - Each parallel task gets isolated worktree: `git worktree add ../task-{id} -b task-{id}`
   - Prevents file conflicts during parallel execution
   - Selective merge per task (better code review)
   - Could add `--worktree` flag to `aur spawn`

2. **Interactive Agent Communication** (~100 LOC)
   - Main agent can interrupt and communicate with running subagents
   - Progress callbacks: check status, provide feedback, course-correct
   - Huge improvement over fire-and-forget spawning
   - Could add `--interactive` flag to `spawn_parallel_tracked`

3. **Task State Persistence** (~50 LOC)
   - Tasks survive crashes/restarts
   - Stored in folders: `.aurora/tasks/{task_id}/state.json`
   - Track: status, conversation, output, timestamps
   - Critical for long-running (hours/days) workflows

4. **Terminal UI (TUI)** (~150 LOC)
   - Visual progress across all parallel tasks
   - Show diffs, conversations, status at-a-glance
   - Better than streaming CLI logs
   - Could use Rich or Textual library

**Compatibility with Aurora:**
- ✅ Works with dependency-aware execution (PRD 0030)
- ✅ Could enhance wave-based spawning with worktree isolation
- ✅ Interactive communication fits SOAR collect phase
- ❌ Requires adaptation for multi-tool support (not just Claude Code)

**Effort:** Medium-High (~400-450 LOC total if adapted for multi-tool)

**Decision:** Only consider if we can adapt to work with cursor, aider, gemini, etc. Claude Code-only is a non-starter.

---

## Not Building

| Feature | Why |
|---------|-----|
| Generic flow configs | Over-engineering trap |
| Graph DSL | Aurora rejects framework feature parity |
| Complex state objects | Subgoal outputs as strings is sufficient |
| Multi-turn conversation | MCP is stateless by design |

---

**Last Updated:** January 30, 2026
