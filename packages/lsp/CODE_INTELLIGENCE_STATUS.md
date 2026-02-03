# Code Intelligence Status Report

> Last Updated: 2026-02-03
> Purpose: Track all code intelligence features, implementation details, and language support.

## Executive Summary

| Category | Live | Partial | Missing | Total |
|----------|------|---------|---------|-------|
| Reference Analysis | 4 | 1 | 1 | 6 |
| Code Quality Markers | 4 | 0 | 2 | 6 |
| File Relationships | 0 | 1 | 2 | 3 |
| Auto-Triggers | 0 | 0 | 1 | 1 |
| **Total** | **8** | **2** | **6** | **16** |

---

## Language Support Matrix

| Feature | Python | JS/TS | Go | Rust | Java | Ruby |
|---------|--------|-------|-----|------|------|------|
| **LSP references** | ✅ Full | ⚠️ Via multilspy | ⚠️ Via multilspy | ⚠️ Via multilspy | ⚠️ Via multilspy | ⚠️ Via multilspy |
| **Deadcode (fast)** | ✅ Full | ✅ ripgrep | ✅ ripgrep | ✅ ripgrep | ✅ ripgrep | ✅ ripgrep |
| **Deadcode (accurate)** | ✅ Full | ⚠️ Untested | ⚠️ Untested | ⚠️ Untested | ⚠️ Untested | ⚠️ Untested |
| **Complexity** | ✅ tree-sitter | ❌ Not impl | ❌ Not impl | ❌ Not impl | ❌ Not impl | ❌ Not impl |
| **Import filtering** | ✅ Custom | ❌ Not impl | ❌ Not impl | ❌ Not impl | ❌ Not impl | ❌ Not impl |
| **Risk calculation** | ✅ Full | ⚠️ No complexity | ⚠️ No complexity | ⚠️ No complexity | ⚠️ No complexity | ⚠️ No complexity |

**Legend:** ✅ Full support | ⚠️ Partial/Untested | ❌ Not implemented

---

## Feature Implementation Details

### Reference Analysis

| Feature | Status | Implementation | Languages | Speed | Notes |
|---------|--------|----------------|-----------|-------|-------|
| **used_by** (usage count) | ✅ LIVE | LSP `get_usage_summary()` via multilspy | Python (tested), others via multilspy | ~1000ms/symbol | Returns files + refs count |
| **called_by** (incoming) | ✅ LIVE | LSP `get_callers()` + import filtering | Python only (filter) | ~1500ms/symbol | Filters import statements |
| **calling** (outgoing) | ❌ STUB | Returns `[]` - needs tree-sitter AST | - | - | Would need per-language parsers |
| **references** (raw) | ✅ LIVE | LSP `request_references()` | All via multilspy | ~800ms/symbol | Raw LSP, no filtering |
| **definition** | ✅ LIVE (unused) | LSP `request_definition()` | All via multilspy | ~200ms | Not exposed via MCP |
| **hover** | ✅ LIVE (unused) | LSP `request_hover()` | All via multilspy | ~200ms | Not exposed via MCP |

### Code Quality Markers

| Feature | Status | Implementation | Languages | Speed | Notes |
|---------|--------|----------------|-----------|-------|-------|
| **#DEADCODE (fast)** | ✅ LIVE | Batched ripgrep + within-file check | All (text search) | ~2s/dir | 85% accuracy |
| **#DEADCODE (accurate)** | ✅ LIVE | LSP references per symbol | Python (tested) | ~20s/dir | 95%+ accuracy |
| **#REFAC** (high usage) | ✅ LIVE | Usage count > 10 = "high" risk | Python (tested) | ~1s/symbol | Part of `lsp impact` |
| **#COMPLEX** | ✅ LIVE | Tree-sitter branch counting | **Python only** | <10ms/file | Shown as `c:95` |
| **#UNUSED** (low usage) | ✅ LIVE | `unused: true` when refs <= 2 | All (uses LSP count) | ~1s/symbol | In mem_search + lsp check |
| **#TYPE** | ❌ MISSING | Would need type checker | - | - | Language-specific |

### File Relationships

| Feature | Status | Implementation | Languages | Speed | Notes |
|---------|--------|----------------|-----------|-------|-------|
| **imports** (outgoing) | ⚠️ INDEXED | Tree-sitter `_extract_imports()` | Python only | <10ms/file | Not queryable via MCP |
| **imported_by** (incoming) | ❌ MISSING | Would need reverse lookup | - | - | High value for refactoring |
| **calls_files** | ❌ MISSING | Would derive from `calling` | - | - | Needs `calling` first |

---

## Implementation Stack

### Current Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP Tools Layer                              │
│  lsp_tool.py              mem_search_tool.py                        │
│  - lsp(action, path)      - mem_search(query, limit)                │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                         Analysis Layer                               │
│  aurora_lsp/analysis.py                                              │
│  - CodeAnalyzer.find_dead_code(accurate=False)                       │
│  - CodeAnalyzer.find_usages()                                        │
│  - CodeAnalyzer.get_callers()                                        │
│  - _batched_ripgrep_search()          ← Language-agnostic            │
│  - _get_complexity()                  ← Python only (tree-sitter)    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                         LSP Client Layer                             │
│  aurora_lsp/client.py (multilspy wrapper)                            │
│  - request_references()                                              │
│  - request_document_symbols()                                        │
│  - request_definition()                                              │
│  Supported: Python, JS/TS, Go, Rust, Java, Ruby, C#, Dart, Kotlin   │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                      Language Servers (via multilspy)                │
│  Python: jedi-language-server                                        │
│  JS/TS: typescript-language-server                                   │
│  Go: gopls                                                           │
│  Rust: rust-analyzer                                                 │
│  Java: jdtls                                                         │
│  Ruby: solargraph                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Technology | Custom Code | Language Support |
|-----------|------------|-------------|------------------|
| **LSP client** | multilspy library | Thin wrapper | 10+ languages |
| **Reference search** | LSP protocol | None | All via LSP |
| **Import filtering** | Custom regex | `aurora_lsp/filters.py` | Multi-language patterns |
| **Deadcode (fast)** | ripgrep subprocess | `_batched_ripgrep_search()` | All languages |
| **Deadcode (accurate)** | LSP references | `find_usages()` loop | Python (tested) |
| **Complexity** | tree-sitter | `aurora_lsp/languages/` | **Python only** (config-based) |
| **Risk calculation** | Custom formula | `_calculate_risk()` | All (uses counts) |
| **Entry point filter** | Config patterns | `aurora_lsp/languages/python.py` | **Python** (extensible) |

### Language Abstraction Layer (NEW)

```
packages/lsp/src/aurora_lsp/languages/
  __init__.py       # Registry: get_config(), is_entry_point(), etc.
  base.py           # LanguageConfig dataclass
  python.py         # Python config (entry points, branch types, patterns)
```

**To add a new language:**
1. Create `languages/{lang}.py` with LanguageConfig
2. Register in `languages/__init__.py`
3. Add tree-sitter-{lang} dependency if complexity needed

---

## Scaling to Other Languages

### What Would Be Needed

| Feature | Current (Python) | To Add Language X |
|---------|------------------|-------------------|
| **LSP references** | ✅ Works | ✅ Already works (multilspy) |
| **Deadcode (fast)** | ✅ Works | ✅ Already works (ripgrep) |
| **Deadcode (accurate)** | ✅ Works | ⚠️ Needs testing with language X server |
| **Complexity** | tree-sitter-python | Need `tree-sitter-X` + parser code |
| **Import filtering** | Python regex | Need language-specific patterns |
| **Entry point filter** | Python patterns | Need language-specific patterns |

### Effort Estimate Per Language

| Language | LSP | Deadcode | Complexity | Import Filter | Total |
|----------|-----|----------|------------|---------------|-------|
| JavaScript/TS | ✅ Ready | ✅ Ready | 2 days | 1 day | **3 days** |
| Go | ✅ Ready | ✅ Ready | 2 days | 1 day | **3 days** |
| Rust | ✅ Ready | ✅ Ready | 2 days | 1 day | **3 days** |
| Java | ✅ Ready | ✅ Ready | 2 days | 2 days | **4 days** |

---

## MCP Tool Parameters

### `lsp` Tool

```python
lsp(
    action: "check" | "impact" | "deadcode",
    path: str,           # File or directory
    line: int | None,    # Required for check/impact (1-indexed)
    accurate: bool,      # For deadcode: True=LSP refs (slow), False=ripgrep (fast)
)
```

| Action | What It Does | Languages | Speed |
|--------|--------------|-----------|-------|
| `check` | Quick usage count before editing | Python (tested) | ~1s |
| `impact` | Full analysis with top callers | Python (tested) | ~2s |
| `deadcode` | Find all unused symbols | All (fast), Python (accurate) | 2-20s |

### `mem_search` Tool

```python
mem_search(
    query: str,          # Search query
    limit: int = 5,      # Max results
    enrich: bool = False # Add callers/callees/git
)
```

| Output Field | Source | Languages |
|--------------|--------|-----------|
| `type` | Indexed metadata | All |
| `file` | Indexed metadata | All |
| `name` | Indexed metadata | All |
| `lines` | Indexed metadata | All |
| `used_by` | LSP + tree-sitter | Python (full), others (no complexity) |
| `risk` | Calculated | Python (full), others (partial) |
| `score` | Hybrid retrieval | All |

---

## Performance Benchmarks

### Deadcode Detection

| Mode | Symbols | Time | Accuracy | Method |
|------|---------|------|----------|--------|
| Fast (default) | 50 | 2s | 85% | Batched ripgrep + within-file check |
| Accurate | 50 | 20s | 95%+ | LSP references per symbol |

### Reference Counting

| Approach | Symbols | Time | Per Symbol |
|----------|---------|------|------------|
| Ripgrep (batched) | 50 | 0.1s | 2ms |
| LSP references | 50 | 15s | 300ms |

### Complexity Calculation

| Method | Files | Time | Per File |
|--------|-------|------|----------|
| Tree-sitter (Python) | 10 | 0.1s | 10ms |

---

## Known Limitations

### Python-Only Features
1. **Complexity calculation** - Uses `tree-sitter-python`
2. **Import filtering** - Python regex patterns (`from X import`, `import X`)
3. **Entry point detection** - Python patterns (`main`, `pytest_*`, decorators)

### External Callers Not Detected
Both fast and accurate modes miss:
- MCP tool calls (`lsp_client.find_dead_code()`)
- CLI entry points called via `python -m`
- Framework callbacks (Flask routes, pytest fixtures)

### LSP Limitations
- `jedi-language-server` doesn't provide diagnostics (no linting)
- Outgoing calls (`calling`) not supported without AST parsing
- Some language servers (Ruby/solargraph) less reliable

---

## Recommended Next Steps

### Quick Wins (1 day each)
1. ✅ ~~Add `--accurate` flag to deadcode~~ DONE
2. ✅ ~~Add complexity to mem_search output~~ DONE
3. ✅ ~~Add risk calculation~~ DONE
4. ✅ ~~Add `#UNUSED` marker (usage <= 2)~~ DONE

### Medium Term (3-5 days each)
1. Add JavaScript/TypeScript complexity (tree-sitter-typescript)
2. Add JS/TS import filtering patterns
3. Build `imported_by` reverse lookup
4. Add pre-edit hook for related files

### Long Term
1. Multi-language complexity support
2. Type checking integration per language
3. LSP warm-up / persistent daemon for faster cold start
