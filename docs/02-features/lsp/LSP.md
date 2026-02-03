# Aurora LSP - Code Intelligence Package

LSP integration for Aurora providing semantic code analysis, dead code detection, and impact assessment.

## Overview

The `aurora-lsp` package wraps [multilspy](https://github.com/microsoft/multilspy) (Microsoft) with custom layers for:

- **Import vs Usage Distinction** - Separates actual code usage from import statements
- **Dead Code Detection** - Finds functions/classes with zero usages
- **Usage Impact Analysis** - Assesses change impact (low/medium/high)
- **Caller Detection** - Identifies which functions call a given symbol

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  AuroraLSP (facade.py)                                  │  Sync API
├─────────────────────────────────────────────────────────┤
│  CodeAnalyzer (analysis.py)                             │  Dead code, impact
│  ImportFilter (filters.py)                              │  Import vs usage
│  DiagnosticsFormatter (diagnostics.py)                  │  Linting
├─────────────────────────────────────────────────────────┤
│  AuroraLSPClient (client.py)                            │  Async LSP ops
├─────────────────────────────────────────────────────────┤
│  multilspy (Microsoft)                                  │  LSP management
└─────────────────────────────────────────────────────────┘
```

## Accuracy Metrics

### Summary

| Metric | Value | Notes |
|--------|-------|-------|
| **Symbol Detection Recall** | 99.3% | 147/148 symbols found |
| **Dead Code Recall** | 100% | 2/2 known dead code detected |
| **Dead Code Specificity** | 100% | 0 false positives |
| **Import/Usage Separation** | Working | 74.5% usages, 25.5% imports |

### Python Testing (Aurora Codebase)

Tested against 6 files, 148 manually-verified symbols:

#### Symbol Detection

| Metric | Value | Notes |
|--------|-------|-------|
| **Recall** | 99.3% | LSP found 147/148 manually-identified symbols |
| **Precision** | 64.5% | LSP reports imported types as symbols (expected) |

#### Reference Finding

| Symbol | Grep | LSP | Usages | Imports | Analysis |
|--------|------|-----|--------|---------|----------|
| SQLiteStore | 76 | 171 | 116 | 55 | LSP resolves re-exports |
| Store | 247 | 32 | 28 | 4 | Grep overcounts partials |
| AuroraError | 28 | 9 | 9 | 0 | LSP ignores docstrings |
| AuroraBaseError | 2 | 19 | 19 | 0 | LSP finds subclasses |
| **TOTAL** | 396 | 231 | 172 | 59 | |

**Key Insight**: LSP < Grep means **more accurate** (ignores comments, strings, partial words).

#### Import vs Usage Separation

```
Total References:  231
├── Usages:        172 (74.5%)  ← Actual code usage
└── Imports:        59 (25.5%)  ← Import statements filtered
```

This distinction is **not available** from grep or basic text search.

#### Dead Code Detection

| Metric | Value |
|--------|-------|
| **Recall** | 100% (ParseError, FatalError correctly identified) |
| **Specificity** | 100% (AuroraError, SQLiteStore, Chunk not flagged) |
| **False Positives** | 0 |

### JavaScript Testing (liteagents)

Tested against https://github.com/amrhas82/liteagents (10 files):

| Metric | Value |
|--------|-------|
| Files Tested | 10 |
| Symbols Found | 2,541 |
| Avg Symbols/File | 254.1 |
| Grep Matches | 346 |
| LSP References | 56 |
| False Positives Avoided | 17 |

Sample results:
- `InstallationEngine`: Grep 20 (6 in comments) → LSP 1 usage
- `InteractiveInstaller`: Grep 145 (3 in comments) → LSP 2 usages
- `PackageManager`: Grep 48 (8 in comments) → LSP 1 usage

### TypeScript Testing (OpenSpec)

Tested against https://github.com/amrhas82/OpenSpec (10 files):

| Metric | Value |
|--------|-------|
| Files Tested | 10 |
| Symbols Found | 2,212 |
| Avg Symbols/File | 221.2 |
| LSP References | 18 |
| Imports Identified | 6 |
| Usages Identified | 12 |

Sample results:
- `Validator`: 10 refs = 4 imports + 6 usages
- `ArchiveCommand`: 2 refs = 1 import + 1 usage
- `ZshInstaller`: 2 refs = 1 import + 1 usage

### Cross-Language Summary

| Language | Files | Symbols | Grep | LSP Refs | Imports | Usages |
|----------|-------|---------|------|----------|---------|--------|
| Python | 6 | 148 | 396 | 231 | 59 | 172 |
| JavaScript | 10 | 2,541 | 346 | 56 | 0 | 56 |
| TypeScript | 10 | 2,212 | 76 | 18 | 6 | 12 |

**Limitation**: Methods called through base class interfaces (polymorphism) may show as "unused" because LSP tracks the base class, not implementations.

## Language Support

| Language | LSP Server | Import Filtering | Status |
|----------|------------|------------------|--------|
| Python | Pyright/Jedi | Full | ✅ Tested |
| TypeScript | tsserver | Full | ✅ Tested |
| JavaScript | tsserver | Full | ✅ Tested |
| Rust | rust-analyzer | Full | Ready |
| Go | gopls | Full | Ready |
| Java | Eclipse JDT | Full | Ready |
| Ruby | Solargraph | Full | Ready |
| C# | OmniSharp | Full | Ready |
| Dart | Dart Analysis | Full | Ready |
| Kotlin | kotlin-lsp | Full | Ready |

## Usage

### Basic API

```python
from aurora_lsp import AuroraLSP

with AuroraLSP("/path/to/project") as lsp:
    # Find usages (excluding imports)
    result = lsp.find_usages("src/main.py", line=10, col=5)
    print(f"{result['total_usages']} usages, {result['total_imports']} imports filtered")

    # Dead code detection
    dead = lsp.find_dead_code()
    for item in dead:
        print(f"Unused: {item['name']} in {item['file']}:{item['line']}")

    # Impact assessment
    summary = lsp.get_usage_summary("src/main.py", line=10, col=5)
    print(f"Impact: {summary['impact']} ({summary['files_affected']} files)")

    # Find callers
    callers = lsp.get_callers("src/utils.py", line=25, col=0)
    for c in callers:
        print(f"Called by: {c['name']} in {c['file']}")
```

### Async API

```python
from aurora_lsp.client import AuroraLSPClient
from aurora_lsp.analysis import CodeAnalyzer

async with AuroraLSPClient(workspace) as client:
    analyzer = CodeAnalyzer(client, workspace)
    result = await analyzer.find_usages(file, line, col)
```

## Key Features

### 1. Import vs Usage Distinction

The primary value-add over raw LSP tools:

```python
# Raw LSP returns ALL references (171 for SQLiteStore)
refs = await client.request_references(file, line, col)

# Filtered results separate imports from actual usage
result = await analyzer.find_usages(file, line, col, include_imports=False)
# → 116 usages + 55 imports
```

### 2. Dead Code Detection

Finds symbols with zero usages (excluding imports):

```python
dead = await analyzer.find_dead_code("src/", include_private=False)
# Returns: [{"name": "ParseError", "kind": "class", "line": 45, "imports": 0}]
```

**Filters out**:
- Private symbols (`_name`) unless requested
- Test functions (`test_*`)
- Imported type hints (Any, Optional, Path, etc.)

### 3. Impact Assessment

Categorizes change impact:

| Usages | Impact Level |
|--------|--------------|
| 0-2 | Low |
| 3-10 | Medium |
| 11+ | High |

### 4. Caller Detection

Identifies which functions call a symbol:

```python
callers = await analyzer.get_callers(file, line, col)
# Returns: [{"name": "save_doc_chunk", "file": "sqlite.py", "line": 1015}]
```

## Limitations

1. **Polymorphism**: Methods called through base class interfaces show as "unused" at the implementation level. The LSP tracks references to the base class method, not overrides.

2. **Server Warmup**: Initial requests may fail while the language server initializes. The client handles this gracefully.

3. **Type-Only Imports**: `TYPE_CHECKING` imports are correctly identified but may appear in both usage and import counts depending on context.

4. **Linting**: Not in scope. Each language has mature linters (ruff for Python, ESLint for JS/TS, Clippy for Rust). Use those directly - no need to wrap them.

## Future CLI Workflow

The recommended workflow for `aur:lsp` commands is **analyze-annotate-review**:

```
# Phase 1: Analyze (read-only)
aur:lsp analyze src/
# → Generates report: .aurora/lsp-report.md

# Phase 2: Annotate (comments only, no code changes)
aur:lsp annotate --from-report
# → Adds: # AURORA:DEAD_CODE - No usages found

# Phase 3: Review (interactive, one-by-one)
aur:lsp fix --interactive
# → [1/5] ParseError - 0 usages. Action: [k]eep / [d]elete / [s]kip?
```

This workflow ensures:
- Human review before any code changes
- Intentional dead code (public API) is preserved
- Clear audit trail via comments

## Package Location

```
packages/lsp/
├── src/aurora_lsp/
│   ├── __init__.py
│   ├── client.py       # Low-level multilspy wrapper
│   ├── filters.py      # Import pattern matching (10 languages)
│   ├── analysis.py     # Dead code, usage summary, callers
│   ├── diagnostics.py  # Linting support
│   └── facade.py       # High-level sync API
├── tests/
│   └── test_filters.py # 7 passing unit tests
├── test_accuracy.py              # Symbol detection accuracy
├── test_references_accuracy.py   # Reference finding accuracy
├── test_final_accuracy.py        # Comprehensive Python tests
├── test_js_ts_repos.py           # JavaScript/TypeScript testing
├── test_before_after.py          # Grep vs LSP comparison
├── test_10_files_comparison.py   # 10-file comparison report
├── pyproject.toml
└── README.md
```

## Running Accuracy Tests

```bash
cd packages/lsp

# Unit tests (filters)
python -m pytest tests/ -v

# Symbol detection accuracy (Python)
python test_accuracy.py

# Reference finding accuracy
python test_references_accuracy.py

# JavaScript/TypeScript testing (requires cloning repos)
git clone https://github.com/amrhas82/liteagents /tmp/liteagents
git clone https://github.com/amrhas82/OpenSpec /tmp/OpenSpec
python test_js_ts_repos.py

# Before/After comparison (grep vs LSP)
python test_before_after.py
```

## Dependencies

- `multilspy>=0.0.15` - Microsoft's multi-language LSP client
- Python 3.10+

## See Also

- [multilspy](https://github.com/microsoft/multilspy) - Underlying LSP library
- [LSP Specification](https://microsoft.github.io/language-server-protocol/) - Protocol reference
