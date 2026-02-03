# LSP Integration - Implementation Plan v4

**Created:** 2026-02-02
**Updated:** 2026-02-03
**Status:** POC COMPLETE - Ready for MCP integration

**Changes in v4:**
- Dropped `mem_get` MCP tool (Claude uses `Read` with file+lines from `mem_search`)
- Dropped slash commands - users interact naturally, Claude invokes MCP
- Clarified `mem_search` internally calls LSP for "used_by" enrichment
- 2 MCP tools total: `lsp`, `mem_search`

**Documentation:** [docs/02-features/lsp/LSP.md](../../docs/02-features/lsp/LSP.md)

---

## Executive Summary

Add LSP integration to Aurora for **import vs usage distinction**, **dead code detection**, and **caller analysis**. Built on **multilspy** (Microsoft) with custom filtering layers.

**POC Status:** PASSED - See [Accuracy Metrics](#poc-results)

---

## POC Results (2026-02-03)

### What Was Built

```
packages/lsp/
├── src/aurora_lsp/
│   ├── __init__.py
│   ├── client.py       # multilspy wrapper (80 lines)
│   ├── filters.py      # Import filtering (60 lines)
│   ├── analysis.py     # Dead code, callers (150 lines)
│   ├── diagnostics.py  # Linting (skipped - see below)
│   └── facade.py       # Sync API wrapper
├── tests/
│   └── test_filters.py # 7 passing tests
└── pyproject.toml
```

### Accuracy Metrics

| Feature | Metric | Result |
|---------|--------|--------|
| **Symbol Detection** | Recall | 99.3% (147/148) |
| **Import vs Usage** | Separation | 302 usages / 103 imports |
| **Dead Code** | Accuracy | 100% (2/2 verified) |
| **Callers** | Found | 28 callers for save_chunk |

### Reference Finding vs Grep

| Symbol | Grep | LSP | Analysis |
|--------|------|-----|----------|
| SQLiteStore | 75 | 171 | +128% (LSP resolves re-exports) |
| Store | 78 | 32 | -59% (grep overcounts - comments, partial matches) |
| SOAROrchestrator | 3 | 74 | +2367% (LSP follows type aliases) |
| StorageError | 112 | 70 | -38% (LSP ignores strings) |

**Key insight:** LSP < Grep = **more accurate** (ignores comments, strings, partial words).

### Dead Code Verified

```
ParseError (class)  - Only in __all__, never imported → TRUE DEAD CODE
FatalError (class)  - Only in __all__, never imported → TRUE DEAD CODE
```

---

## What We Learned

### Works Well

| Feature | Status | Notes |
|---------|--------|-------|
| Import vs Usage | ✅ WORKING | 74.6% usages / 25.4% imports |
| Dead Code | ✅ WORKING | 100% accuracy on tested symbols |
| Callers | ✅ WORKING | Finds containing functions |
| Multi-language patterns | ✅ READY | 10 languages in filters.py |

### Skipped: Linting

**Decision:** Do not implement linting wrapper.

**Reasons:**
1. multilspy uses **push-based diagnostics** (server sends when ready) - cannot pull on demand
2. Each language has **mature linters**: ruff (Python), ESLint (JS/TS), Clippy (Rust)
3. No unique value-add - just use `ruff check` directly

See: [LSP Specification - Push vs Pull](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/)

### Limitations Discovered

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **Polymorphism** | Methods called via base class show as "dead" | Check base class usages manually |
| **Server warmup** | Initial requests may fail | Retry logic in client |
| **selectionRange required** | Must use `selectionRange.start`, not `range.start` | Fixed in POC |
| **Outgoing calls** | Not supported by multilspy | Would need tree-sitter |

---

## Devil's Advocate

### Why This Might Fail

| Risk | Severity | Mitigation |
|------|----------|------------|
| **cclsp already exists** | HIGH | cclsp is Claude-only; aurora-lsp is standalone/CI-ready |
| **Only tested Python** | MEDIUM | Other languages have patterns but not validated |
| **Polymorphism false positives** | MEDIUM | Document as known limitation |
| **Server startup time** | LOW | Lazy init, cache servers |
| **multilspy maintenance** | LOW | Microsoft-maintained, active repo |

### When NOT to Use This

1. **For linting** → Use ruff, eslint, clippy directly
2. **For one-off queries** → Use cclsp (already in Claude Code)
3. **For outgoing calls** → Not supported, use tree-sitter
4. **For dynamic languages** → LSP struggles with Ruby/Python duck typing

### Honest Assessment

| Claim | Reality |
|-------|---------|
| "99.3% symbol detection" | True for Python; other languages untested |
| "100% dead code accuracy" | On 2 symbols; polymorphism is a real gap |
| "10 language support" | Patterns exist; only Python LSP tested |
| "Better than grep" | True for semantic analysis; grep is faster for text search |

---

## Architecture (Validated)

```
┌─────────────────────────────────────────────────────────────┐
│  Aurora CLI / MCP                                           │
│  aur lsp analyze | aur lsp deadcode | aur lsp callers      │
├─────────────────────────────────────────────────────────────┤
│  AuroraLSP (packages/lsp/)                    ~350 lines    │
│  - Import filtering (regex patterns, 10 languages)          │
│  - Dead code detection (0 usages after filtering)           │
│  - Caller detection (containing function lookup)            │
│  - NO linting (use ruff/eslint directly)                    │
├─────────────────────────────────────────────────────────────┤
│  multilspy (Microsoft)                        pip install   │
│  - Manages language server processes                        │
│  - 10 languages: Python, Rust, Java, Go, JS, TS, Ruby,     │
│    C#, Dart, Kotlin                                         │
├─────────────────────────────────────────────────────────────┤
│  Language Servers (community-maintained)                    │
│  Python: Pyright | Rust: rust-analyzer | Go: gopls         │
└─────────────────────────────────────────────────────────────┘
```

---

## Recommended Workflow

### Analyze → Annotate → Review

```bash
# Phase 1: ANALYZE (read-only, generates report)
aur lsp analyze src/
# Output: .aurora/lsp-report.md

# Phase 2: ANNOTATE (adds comments, no code changes)
aur lsp annotate --from-report
# Adds: # AURORA:DEAD_CODE - 0 usages found

# Phase 3: REVIEW (interactive, one-by-one)
aur lsp fix --interactive
# [1/5] ParseError - 0 usages. Action: [k]eep / [d]elete / [s]kip?
```

**Why this workflow:**
- Dead code might be intentional (public API, future use)
- Human judgment required before deletion
- Audit trail via comments

---

## Integration with `aur mem search`

### Layout Change

LSP "Used by" data integrates into memory search results:

**Main Table (default):**
```
┃ Type ┃ File              ┃ Name              ┃ Lines    ┃ Used by      ┃ Score ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━┩
│ code │ orchestrator.py   │ SOAROrchestrator  │ 68-2447  │ 12 files(74) │ 0.564 │
│ code │ sqlite.py         │ SQLiteStore       │ 38-1200  │ 29 files(171)│ 0.523 │
│ kb   │ KNOWLEDGE_BASE.md │ Key Entry Points  │ 1-8      │ -            │ 0.697 │
```

**With --show-scores:**
```
┌─ orchestrator.py | code | SOAROrchestrator (Lines 68-2447) ─────────────────┐
│ Score: 0.564                                                                │
│  ├─ BM25:       0.702 (exact match)                                         │
│  ├─ Semantic:   0.983 (high relevance)                                      │
│  ├─ Activation: 0.038                                                       │
│  ├─ Git:        41 commits, modified 11h ago, 1769726267                    │
│  └─ Used by:    12 files (run.py, executor.py, runner.py +9)                │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Changes from current layout:**
- Type column moves to first position
- Commits + Modified → move to `--show-scores` only
- "Used by" replaces them in main table
- Same column count (6)

### "Used by" Format

`{file_count} files({usage_count})`

- **file_count**: Number of files affected (breadth)
- **usage_count**: Total call sites (depth/coupling)
- Example: `12 files(74)` = 12 files, 74 total usages (~6 per file avg)

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Don't index LSP data** | Must be live - any code change invalidates cached counts |
| **Compute on-demand** | ~500ms overhead acceptable; cache in-memory for session only |
| **LSP doesn't affect score** | Score = relevance to query; Used by = change impact. Different metrics. |
| **"-" for non-code** | KB articles, docs don't have callers |

---

## MCP Tool Specifications

**Design principle:** MCP tools return compact JSON. Claude uses existing tools (Read) to get content.

### Tool 1: `mem_search`

```yaml
tool: mem_search
description: Search indexed code and knowledge base with LSP context
params:
  query: string (required)
  limit: int (default 5)
returns: compact JSON ≈150-200 tokens
```

**Returns:**
```json
[
  {"file": "orchestrator.py", "type": "code", "symbol": "SOAROrchestrator",
   "lines": "68-2447", "score": 0.564, "used_by": "12 files(74)",
   "git": "41 commits, 11h ago, 1769726267"},
  {"file": "KNOWLEDGE_BASE.md", "type": "kb", "symbol": "Entry Points",
   "lines": "1-8", "score": 0.489, "used_by": "-", "git": "-"}
]
```

**Underlying code:**
```python
# packages/core/src/aurora_core/mcp/tools.py
def mem_search(query: str, limit: int = 5) -> list[dict]:
    # 1. Call memory store directly (same code as CLI, not shelling out)
    results = memory_store.search(query, limit)

    # 2. Enrich with LSP usage counts (code results only)
    for r in results:
        if r.type == "code":
            r.used_by = aurora_lsp.get_usage_count(r.file, r.line)

    # 3. Return compact JSON (Claude uses Read tool to get full content)
    return [r.to_dict() for r in results]
```

**Key point:** `mem_search` internally calls LSP to populate "used_by" field. This is automatic - no separate `lsp` call needed for search results.

---

### Tool 2: `lsp`

```yaml
tool: lsp
description: Code intelligence - dead code, impact analysis, pre-edit checks
params:
  action: "deadcode" | "impact" | "check" (default: check)
  path: string (required)
  line: int (optional, required for impact/check)
returns: action-specific JSON
```

**Underlying code:**
```python
# packages/lsp/src/aurora_lsp/mcp.py
def lsp(action: str, path: str, line: int = None) -> dict:
    if action == "deadcode":
        # Scan for unused code
        return aurora_lsp.find_dead_code(path)
        # → [{"name": "ParseError", "file": "exceptions.py", "line": 45}]

    elif action == "impact":
        # Full impact analysis
        return aurora_lsp.get_usage_summary(path, line)
        # → {"symbol": "X", "used_by_files": 12, "total_usages": 74,
        #    "top_callers": [...], "risk": "high"}

    elif action == "check":
        # Quick pre-edit check
        return aurora_lsp.get_usage_count(path, line)
        # → {"symbol": "X", "used_by": 12, "risk": "high"}
```

---

### Summary

| MCP Tool | Underlying Code | CLI Equivalent |
|----------|-----------------|----------------|
| `mem_search` | `memory_store.search()` + `aurora_lsp.get_usage_count()` | `aur mem search` |
| `lsp` | `aurora_lsp.*` | `aur lsp <action>` |

**Total: 2 MCP tools.**

### Interface Summary

| Interface | Command | Notes |
|-----------|---------|-------|
| **MCP** | `mem_search` | Claude invokes; returns JSON with "used_by" from LSP |
| **MCP** | `lsp` | Claude invokes; explicit code analysis |
| **CLI** | `aur mem search` | User runs; vital for shell/CI |
| **CLI** | `aur lsp <action>` | User runs; optional |
| ~~Slash~~ | ~~`/search`, `/get`~~ | **Dropped** - natural language instead |
| ~~MCP~~ | ~~`mem_get`~~ | **Dropped** - Claude uses `Read` tool |

**No slash commands** - Users interact naturally ("search for X") and Claude invokes MCP tools. For full content, Claude uses `Read` tool with file path + line range from `mem_search` results.

---

### Auto-Invoke Behavior

Claude should call `lsp(action="check")` before edits:

| Edit Type | Action |
|-----------|--------|
| Typo, comment, formatting | Skip |
| Modify function/class body | `lsp(action="check")` |
| Rename symbol | `lsp(action="impact")` |
| Delete code | `lsp(action="check")` |

System prompt addition:
> "Before modifying or deleting functions/classes, call `lsp` tool to check usage impact."

### Risk Levels

| Usages | Risk | Guidance |
|--------|------|----------|
| 0-2 | low | Safe to change |
| 3-10 | medium | Review callers |
| 11+ | high | Careful refactoring |

### Learnings from Serena

Reviewed [Serena MCP](https://github.com/oraios/serena) patterns:

| Serena Pattern | Our Adaptation |
|----------------|----------------|
| `find_referencing_symbols` | `lsp(action="impact")` |
| Separate read/edit markers | Add `readOnlyHint: true` annotation |
| Name-path lookup (`Class/method`) | We use `file:line` (simpler) |
| Many focused tools | Single unified `lsp` tool (simpler) |
| No dead code detection | **We add this** - unique value |
| Tool registry auto-discovery | Not needed for single tool |

**Key differences:**
- Serena: Many tools (`find_symbol`, `find_referencing_symbols`, `replace_symbol_body`, etc.)
- Aurora: One `lsp` tool with `action` param (simpler, less cognitive load)
- Aurora adds `deadcode` action which Serena lacks

**MCP Annotations (from Serena):**
```python
annotations = ToolAnnotations(
    title="LSP Code Intelligence",
    readOnlyHint=True,  # deadcode, impact, check don't modify
    destructiveHint=False,
)
```

---

## CLI Commands (Proposed)

```bash
# Find usages of symbol (excluding imports)
aur lsp usages SQLiteStore
# SQLiteStore: 116 usages (55 imports filtered)

# Show callers
aur lsp callers save_chunk
# 28 callers found:
#   _save_chunk_with_retry() in memory_manager.py:1375
#   save_doc_chunk() in sqlite.py:1015
#   ...

# Find dead code
aur lsp deadcode packages/core/
# Dead Code: 2 items
#   ParseError (class) at exceptions.py:45 - 0 usages
#   FatalError (class) at exceptions.py:142 - 0 usages

# Analyze with report
aur lsp analyze src/ --output .aurora/lsp-report.md
```

---

## Files Status

| File | Status | Lines |
|------|--------|-------|
| `packages/lsp/src/aurora_lsp/__init__.py` | ✅ Done | 15 |
| `packages/lsp/src/aurora_lsp/client.py` | ✅ Done | 95 |
| `packages/lsp/src/aurora_lsp/filters.py` | ✅ Done | 65 |
| `packages/lsp/src/aurora_lsp/analysis.py` | ✅ Done | 160 |
| `packages/lsp/src/aurora_lsp/diagnostics.py` | ⏭️ Skipped | N/A |
| `packages/lsp/src/aurora_lsp/facade.py` | ✅ Done | 40 |
| `packages/lsp/tests/test_filters.py` | ✅ Done | 7 tests |
| `packages/lsp/pyproject.toml` | ✅ Done | 25 |
| `packages/cli/.../lsp.py` | ❌ TODO | ~100 |
| **Total** | | ~400 lines |

---

## Remaining Work

### Phase 1: MCP Tools

- [ ] Create `lsp` MCP tool with actions: deadcode, impact, check
- [ ] Create `mem_search` MCP tool (wrap existing search + LSP enrichment)
- [ ] Wire to existing packages
- [ ] Add to Claude system prompt for auto-invoke guidance

### Phase 2: CLI Memory Search (`aur mem search`)

- [ ] Add "Used by" column to output (calls LSP internally)
- [ ] Move Commits/Modified to `--show-scores` only
- [ ] Compute LSP data on-demand (not indexed)

### Phase 3: CLI Commands (`aur lsp`)

- [ ] `aur lsp deadcode [path]` - Find dead code
- [ ] `aur lsp impact [file:line]` - Show change impact
- [ ] `aur lsp check [file:line]` - Quick usage check
- [ ] `--json` output option for all commands

### Phase 4: Testing

- [x] Test Python (99.3% symbol recall)
- [x] Test JavaScript (liteagents repo)
- [x] Test TypeScript (OpenSpec repo)
- [ ] Integration tests for MCP tool

---

## Success Criteria

| Metric | Target | Current |
|--------|--------|---------|
| Symbol detection recall | >95% | 99.3% ✅ |
| Dead code accuracy | >90% | 100% ✅ |
| Import/usage separation | Working | Yes ✅ |
| Languages tested | ≥2 | 3 (Python, JS, TS) ✅ |
| MCP tools | 2 (lsp, mem_search) | 0 |
| Memory search integration | "Used by" column | 0 |
| Unit tests | >10 | 7 |

---

## Dependencies

```toml
# packages/lsp/pyproject.toml
[project]
name = "aurora-lsp"
version = "0.1.0"
dependencies = [
    "multilspy>=0.0.15",  # Microsoft's multi-language LSP client
    "mcp>=1.0.0",         # MCP server framework
]
```

---

## References

- [Full Documentation](../../docs/02-features/lsp/LSP.md)
- [multilspy GitHub](https://github.com/microsoft/multilspy)
- [LSP Specification](https://microsoft.github.io/language-server-protocol/)

---

**End of Plan**
