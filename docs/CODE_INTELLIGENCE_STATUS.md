# Code Intelligence Status Report

> Generated: 2024-02-03
> Purpose: Track all code intelligence features, their implementation status, performance, and priority.

## Executive Summary

| Category | Live | POC | Missing | Total |
|----------|------|-----|---------|-------|
| Reference Analysis | 3 | 1 | 2 | 6 |
| Code Quality Markers | 2 | 2 | 2 | 6 |
| File Relationships | 0 | 0 | 3 | 3 |
| Auto-Triggers | 0 | 0 | 1 | 1 |
| **Total** | **5** | **3** | **8** | **16** |

> Last updated: 2026-02-03 - Added complexity (`c:95`) and risk (HIGH/MED/LOW) to mem_search

---

## Feature Status Matrix

### Reference Analysis (Who uses what)

| Feature | Status | Tool | Speed | Accuracy | Priority | Notes |
|---------|--------|------|-------|----------|----------|-------|
| **used_by** (usage count) | ✅ LIVE | `mem_search` + LSP | ~1000ms/symbol | 90%+ | **HIGH** - Users check before refactoring | Returns "N files(M)" format |
| **called_by** (incoming calls) | ✅ LIVE | `mem_search --enrich` + LSP | ~1500ms/symbol | 90%+ | **HIGH** - Critical for impact analysis | Functions that call this symbol |
| **calling** (outgoing calls) | ❌ STUB | LSP `get_callees()` | - | 0% | **MEDIUM** - Useful for understanding flow | Returns `[]` - not implemented |
| **references** (all usages) | ✅ LIVE | LSP `request_references` | ~800ms/symbol | 95%+ | **HIGH** - Core LSP feature | Raw list of all references |
| **definition** (go to def) | ⚠️ LIVE (unused) | LSP `request_definition` | ~200ms | 95%+ | **LOW** - IDE feature, not MCP | Implemented but not exposed |
| **hover** (type info) | ⚠️ LIVE (unused) | LSP `request_hover` | ~200ms | 90%+ | **LOW** - IDE feature, not MCP | Implemented but not exposed |

### Code Quality Markers

| Feature | Status | Tool | Speed | Accuracy | Priority | Notes |
|---------|--------|------|-------|----------|----------|-------|
| **#DEADCODE** (fast) | ✅ LIVE | `lsp deadcode` + batched ripgrep | ~2s/dir | 85% | **HIGH** - Quick cleanup scan | Checks within-file usages |
| **#DEADCODE** (accurate) | ✅ LIVE | `lsp deadcode --accurate` + LSP refs | ~20s/dir | 95%+ | **HIGH** - Before deletions | Slower but more reliable |
| **#REFAC** (high usage) | ✅ LIVE | `lsp check/impact` | ~1000ms/symbol | 90%+ | **HIGH** - Shows refactoring risk | Returns risk: low/medium/high |
| **#REFAC** | ✅ POC | `analysis_poc.py` + batched ripgrep | ~100ms/50 symbols | 90% | **HIGH** | Batch version, not merged |
| **#UNUSED** (imports/vars) | ❌ MISSING | - | - | - | **MEDIUM** - Code hygiene | Tree-sitter can detect imports |
| **#COMPLEX** | ✅ LIVE | Tree-sitter `_get_complexity` | <10ms/file | 95% | **MEDIUM** - Identifies risky code | Shown in mem_search as `c:95` |
| **#TYPE** | ❌ MISSING | - | - | - | **LOW** - Needs per-language type checker | jedi-language-server doesn't provide diagnostics |

### File Relationships

| Feature | Status | Tool | Speed | Accuracy | Priority | Notes |
|---------|--------|------|-------|----------|----------|-------|
| **imports** (what this file imports) | ✅ INDEXED | Tree-sitter `_extract_imports` | <10ms/file | 95% | **MEDIUM** | Extracted during indexing, not queryable via MCP |
| **imported_by** (who imports this file) | ❌ MISSING | - | - | - | **HIGH** - Critical for understanding dependencies | Need reverse lookup of imports |
| **calls_files** (files this calls into) | ❌ MISSING | - | - | - | **MEDIUM** | Derive from outgoing calls |
| **called_by_files** (files that call this) | ⚠️ PARTIAL | LSP `get_callers` | ~1500ms | 85% | **HIGH** | Have callers, need to group by file |

### Auto-Triggers (Proactive Intelligence)

| Feature | Status | Tool | Speed | Accuracy | Priority | Notes |
|---------|--------|------|-------|----------|----------|-------|
| **pre-edit check** | ❌ MISSING | - | - | - | **HIGH** - Prevent breaking changes | Show related files before Claude edits |

---

## Implementation Details

### What's Actually Used by MCP Tools

#### `lsp` MCP Tool (src/aurora_mcp/lsp_tool.py)

| Action | What It Does | LSP Methods Used | Performance |
|--------|--------------|------------------|-------------|
| `check` | Quick usage count before editing | `get_usage_summary()` | ~1000ms |
| `impact` | Full analysis with callers | `get_usage_summary()` + `get_callers()` | ~2000ms |
| `deadcode` | Find all unused symbols | `request_document_symbols()` + grep per symbol | ~3000ms/file (SLOW) |

#### `mem_search` MCP Tool (src/aurora_mcp/mem_search_tool.py)

| Field | What It Returns | Source | Performance |
|-------|-----------------|--------|-------------|
| `used_by` | "19f 43r c:95" (files, refs, complexity%) | LSP + Tree-sitter | ~1000ms/result |
| `risk` | "HIGH" / "MED" / "LOW" / "-" | Calculated from files/refs/complexity | <1ms |
| `called_by` | List of caller function names | LSP `get_callers()` | ~500ms/result (with enrich) |
| `calling` | List of callee function names | LSP `get_callees()` | 0ms (returns `[]`) |
| `git` | Relative time ("2d ago") | `last_modified` from index | <1ms |

**CLI Output Modes:**
- Quick mode: `Type | File | Name | Lines | Risk | Git | Score`
- Detailed mode (`--show-scores`): Box format with BM25/Semantic/Activation breakdown, Files list, full Used by

### What's Built But Not Exposed

#### Tree-sitter Parsers (packages/context-code)

| Parser | Languages | Features Extracted |
|--------|-----------|-------------------|
| `PythonParser` | .py, .pyi | functions, classes, methods, imports, complexity |
| `TypeScriptParser` | .ts, .tsx | functions, classes, methods |
| `JavaScriptParser` | .js, .jsx | functions, classes, methods |
| `MarkdownParser` | .md | sections |

#### PythonParser Capabilities (packages/context-code/src/aurora_context_code/languages/python.py)

| Method | Line | Status | Output |
|--------|------|--------|--------|
| `_extract_functions()` | 152 | ✅ Working | List of function chunks |
| `_extract_classes_and_methods()` | 229 | ✅ Working | List of class/method chunks |
| `_extract_imports()` | 554 | ✅ Working | Set of imported names |
| `_calculate_complexity()` | 502 | ✅ Working | Normalized score 0.0-1.0 |
| `_identify_dependencies()` | 592 | ❌ STUB | Returns `[]` |

### What's in POC (Not Merged)

#### analysis_poc.py (packages/lsp/src/aurora_lsp/analysis_poc.py)

| Feature | Function | Performance | Status |
|---------|----------|-------------|--------|
| Batched symbol search | `batched_ripgrep_search()` | 100ms/50 symbols | ✅ Working |
| Fast dead code detection | `FastCodeAnalyzer.find_dead_code_fast()` | 2.3s total (vs 5s+ old) | ✅ Working |
| Marker generation | `generate_inline_markers()` | <10ms | ✅ Working |
| #DEADCODE marker | - | - | ✅ Working |
| #REFAC marker | - | - | ✅ Working |
| #UNUSED marker | - | - | ❌ Not implemented |

---

## Performance Benchmarks

### Reference Counting

| Approach | Symbols | Time | Per Symbol | Notes |
|----------|---------|------|------------|-------|
| LSP references (old) | 1 | ~1000ms | 1000ms | Accurate but slow |
| Grep per symbol (old) | 50 | 2800ms | 56ms | O(n) subprocess calls |
| Batched ripgrep (POC) | 50 | 113ms | 2.3ms | **24x faster** |

### Document Symbols (LSP)

| Files | Time | Per File | Notes |
|-------|------|----------|-------|
| 7 | 2230ms | 318ms | Main bottleneck for deadcode |

### Diagnostics (LSP)

| Tool | Files | Time | Issues Found | Notes |
|------|-------|------|--------------|-------|
| jedi-language-server | 7 | 0ms | 0 | **Does not support diagnostics** |
| ruff (external) | 7 | 22ms | 2 | Fast but single-language |
| mypy (external) | 7 | ~5000ms | varies | Slow, full type checking |

---

## Priority Ranking

### P0 - Critical (Users depend on these daily)

1. **used_by** - ✅ LIVE - Check before refactoring
2. **called_by** - ✅ LIVE - Impact analysis
3. **#DEADCODE** - ⚠️ LIVE but SLOW - Code cleanup
4. **#REFAC** - ✅ LIVE - Refactoring risk

### P1 - High Value (Would significantly improve UX)

5. **imported_by** - ❌ MISSING - Understanding dependencies
6. **pre-edit check** - ❌ MISSING - Proactive safety
7. **#DEADCODE (fast)** - ✅ POC - Merge batched ripgrep

### P2 - Medium Value (Nice to have)

8. **calling** (outgoing) - ❌ STUB - Code flow understanding
9. **#UNUSED** - ❌ MISSING - Code hygiene
10. **#COMPLEX** - ✅ LIVE - Risk identification (shown as `c:95` in mem_search)

### P3 - Low Priority

11. **#TYPE** - ❌ MISSING - Requires language-specific tools
12. **definition** - ⚠️ LIVE (unused) - IDE feature
13. **hover** - ⚠️ LIVE (unused) - IDE feature

---

## Recommended Actions

### Quick Wins (< 1 day each)

| Action | Effort | Impact | Status |
|--------|--------|--------|--------|
| Merge batched ripgrep POC into `lsp deadcode` | Low | High - 24x faster | ❌ TODO |
| Expose `complexity_score` from indexed chunks | Low | Medium - #COMPLEX marker | ✅ DONE - shown as `c:95` |
| Add `risk` calculation (files/refs/complexity) | Low | High - quick safety check | ✅ DONE - HIGH/MED/LOW |
| Implement `_identify_dependencies()` in tree-sitter | Medium | Medium - enables `calling` | ❌ TODO |

### Medium Term (1-3 days each)

| Action | Effort | Impact | Ticket |
|--------|--------|--------|--------|
| Build `imported_by` reverse lookup | Medium | High - dependency analysis | - |
| Add pre-edit hook for related files | Medium | High - proactive safety | - |
| Implement #UNUSED via tree-sitter import/usage comparison | Medium | Medium - code hygiene | - |

### Long Term (Research needed)

| Action | Effort | Impact | Ticket |
|--------|--------|--------|--------|
| Multi-language type checking (#TYPE) | High | Low - complex problem | - |
| LSP warm-up / persistent daemon | High | Medium - faster cold start | - |

---

## Architecture Notes

### Current Data Flow

```
User Query
    │
    ▼
┌─────────────────┐
│  MCP Tool       │  (lsp / mem_search)
│  - lsp_tool.py  │
│  - mem_search_  │
│    tool.py      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LSP Facade     │  (packages/lsp/src/aurora_lsp/facade.py)
│  - Sync wrapper │
│  - get_usage_   │
│    summary()    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LSP Client     │  (packages/lsp/src/aurora_lsp/client.py)
│  - Async        │
│  - jedi-lang-   │
│    server       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Language       │  (jedi-language-server subprocess)
│  Server         │
│  - references   │
│  - symbols      │
│  - NO diagnostics│
└─────────────────┘
```

### Tree-sitter Data Flow (Separate, during indexing)

```
aur index
    │
    ▼
┌─────────────────┐
│  ParserRegistry │  (packages/context-code)
│  - PythonParser │
│  - TSParser     │
│  - JSParser     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CodeChunk      │  Contains:
│                 │  - name, signature
│                 │  - complexity_score ← NOT USED
│                 │  - dependencies ← EMPTY
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite DB      │  (.aurora/memory.db)
│  - chunks table │
└─────────────────┘
```

### Gap: Tree-sitter data partially used by MCP tools

~~The `complexity_score` is calculated during indexing but not exposed.~~

**FIXED (2026-02-03):** Complexity is now calculated on-the-fly via tree-sitter in `mem_search` and `_get_lsp_usage()`:
- Shown as `c:95` in compact format
- Shown as `complexity 95%` in detailed format
- Used to calculate `risk` level (HIGH if complexity >= 60%)

**Still missing:**
1. `dependencies` from `_identify_dependencies()` - returns `[]`
2. `imports` reverse lookup (`imported_by`)

---

## Appendix: Test Commands

```bash
# Test mem_search MCP tool
echo '{"query": "SOAROrchestrator", "limit": 3}' | python -c "
import sys, json
sys.path.insert(0, 'src')
from aurora_mcp.mem_search_tool import mem_search
result = mem_search(**json.load(sys.stdin))
print(json.dumps(result, indent=2))
"

# Test lsp MCP tool
python -c "
import sys
sys.path.insert(0, 'src')
from aurora_mcp.lsp_tool import lsp
result = lsp(action='check', path='packages/lsp/src/aurora_lsp/analysis.py', line=54)
print(result)
"

# Test batched ripgrep POC
python -m aurora_lsp.analysis_poc packages/lsp/src

# Benchmark old vs new deadcode
python -c "
import asyncio, time, sys
sys.path.insert(0, 'packages/lsp/src')
from pathlib import Path
from aurora_lsp.client import AuroraLSPClient
from aurora_lsp.analysis import CodeAnalyzer
from aurora_lsp.analysis_poc import FastCodeAnalyzer

async def bench():
    workspace = Path.cwd()
    async with AuroraLSPClient(workspace) as client:
        old = CodeAnalyzer(client, workspace)
        new = FastCodeAnalyzer(client, workspace)

        t1 = time.perf_counter()
        await old.find_dead_code(workspace / 'packages/lsp/src')
        old_time = time.perf_counter() - t1

        t2 = time.perf_counter()
        await new.find_dead_code_fast(workspace / 'packages/lsp/src')
        new_time = time.perf_counter() - t2

        print(f'Old: {old_time:.2f}s, New: {new_time:.2f}s, Speedup: {old_time/new_time:.1f}x')

asyncio.run(bench())
"
```
