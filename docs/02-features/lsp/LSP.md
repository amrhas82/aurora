# Aurora LSP - Code Intelligence Package

LSP integration for Aurora providing semantic code analysis, dead code detection, and impact assessment.

> **📊 For comprehensive feature status, language support matrix, and implementation details, see [Code Intelligence Status](CODE_INTELLIGENCE_STATUS.md).**

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

Tested against https://github.com/hamr0/liteagents (10 files):

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

Tested against https://github.com/hamr0/OpenSpec (10 files):

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

### 5. Hybrid LSP Fallback (v0.13.4+)

Automatic text search fallback when LSP returns 0 references:

```python
# MCP tool call
result = lsp(action="check", path="src/soar/orchestrator.py", line=25)

# If LSP finds references:
# {"used_by": 12, "risk": "high"}

# If LSP finds 0 but text search finds matches:
# {
#   "used_by": 0,
#   "text_matches": 15,
#   "text_files": 6,
#   "note": "LSP found 0 refs but text search found 15 matches in 6 files - likely cross-package usage",
#   "risk": "high"  # Adjusted based on text_matches
# }
```

**Implementation Details:**
1. When LSP returns 0 references, extract symbol name from source line
2. Use ripgrep with word boundaries (`rg -w`) to find text matches
3. Count files and total matches
4. If matches found, add `text_matches`, `text_files`, and `note` to response
5. Recalculate risk based on text match count

This catches cross-package references that LSP misses due to:
- Installed packages (site-packages) vs source files
- Lazy imports (`if TYPE_CHECKING:` blocks)
- Dynamic imports (`importlib.import_module()`)

## Limitations

1. **Polymorphism**: Methods called through base class interfaces show as "unused" at the implementation level. The LSP tracks references to the base class method, not overrides.

2. **Server Warmup**: Initial requests may fail while the language server initializes. The client handles this gracefully.

3. **Type-Only Imports**: `TYPE_CHECKING` imports are correctly identified but may appear in both usage and import counts depending on context.

4. **Linting**: Not in scope. Each language has mature linters (ruff for Python, ESLint for JS/TS, Clippy for Rust). Use those directly - no need to wrap them.

5. **Cross-Package References**: LSP may return 0 refs for symbols used across packages (installed vs source). **Mitigated in v0.13.4** with hybrid fallback using ripgrep text search.

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
git clone https://github.com/hamr0/liteagents /tmp/liteagents
git clone https://github.com/hamr0/OpenSpec /tmp/OpenSpec
python test_js_ts_repos.py

# Before/After comparison (grep vs LSP)
python test_before_after.py
```

## Dependencies

- `multilspy>=0.0.15` - Microsoft's multi-language LSP client
- Python 3.10+

## MCP Integration

Aurora-LSP is integrated into Aurora's MCP server as the `lsp` tool, providing code intelligence to AI coding assistants.

**Available via MCP:**
- Claude Desktop
- Cursor
- Cline (VS Code)
- Continue (VS Code)

**MCP Actions:**

| Action | Parameters | Speed | Purpose |
|--------|------------|-------|---------|
| `check` | `path`, `line` | ~1s | Quick usage count before editing |
| `impact` | `path`, `line` | ~2s | Full impact analysis with top callers |
| `deadcode` | `path` (optional) | 2-20s | Find all unused symbols, generate report |
| `imports` | `path` | <1s | Find all files that import a module |
| `related` | `path`, `line` | ~50ms | Find outgoing calls (Python only) |

**Speed Note:** Many operations use ripgrep (~2ms/symbol) instead of traditional LSP (~300ms/symbol).

**Benefits:**
- Dead code detection with CODE_QUALITY_REPORT.md generation
- Impact analysis before refactoring
- Risk assessment (low/medium/high based on usage count)
- Import dependency tracking
- Outgoing call analysis (what does this function call?)
- **Hybrid fallback** for cross-package reference detection (v0.13.4+)
- Integrated with Aurora's hybrid search (mem_search tool)

See [MCP Tools Documentation](../mcp/MCP.md) for complete MCP integration details.
See [Code Intelligence Status](CODE_INTELLIGENCE_STATUS.md) for all 16 features and implementation status.

## Claude Code Pre-Edit Hook

For tools that support hooks (like Claude Code), you can automatically run `lsp check` before every file edit. This ensures Claude always sees usage impact before making changes.

### Setup (Claude Code)

The hook is automatically configured when you run `aur init --tools=claude`. It creates:

- `.claude/hooks/pre-edit-lsp-check.py` - Hook script that calls LSP check
- `.claude/settings.json` - Project-local settings with PreToolUse hook

### Manual Setup

If you want to configure manually or for user-wide settings:

1. Create the hook script at `~/.claude/hooks/pre-edit-lsp-check.py`:

```python
#!/usr/bin/env python3
"""Pre-Edit hook that runs LSP check before file edits."""
import json
import os
import sys
from pathlib import Path

def main():
    input_data = json.load(sys.stdin)
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    cwd = input_data.get("cwd", "")

    # Skip non-code files
    if not any(file_path.endswith(ext) for ext in [".py", ".js", ".ts", ".go", ".rs"]):
        sys.exit(0)

    # Find workspace and call LSP
    workspace = Path(cwd) if cwd else Path.cwd()
    sys.path.insert(0, str(workspace / "src"))
    sys.path.insert(0, str(workspace / "packages/lsp/src"))

    from aurora_mcp.lsp_tool import lsp
    os.chdir(workspace)

    # Find line number from old_string
    with open(file_path) as f:
        content = f.read()
    old_string = tool_input.get("old_string", "")
    if old_string not in content:
        sys.exit(0)
    line = content[:content.find(old_string)].count('\n') + 1

    result = lsp(action="check", path=file_path, line=line)

    # Return context to Claude
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "additionalContext": f"LSP CHECK: {result.get('used_by', 0)} refs | Risk: {result.get('risk', 'low').upper()}"
        }
    }
    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
```

2. Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/pre-edit-lsp-check.py"
          }
        ]
      }
    ]
  }
}
```

### What It Does

Before every Edit tool call on code files, Claude sees:

```
LSP CHECK: 'AuroraLSP' @ line 26 | 3 LSP refs | Risk: MEDIUM
```

This helps Claude understand the impact of changes before making them, without relying on Claude's attention to remember to call `lsp check` manually.

## See Also

- [Code Intelligence Status](CODE_INTELLIGENCE_STATUS.md) - All 16 features, language matrix, benchmarks
- [MCP Tools](../mcp/MCP.md) - Aurora MCP integration
- [multilspy](https://github.com/microsoft/multilspy) - Underlying LSP library
- [LSP Specification](https://microsoft.github.io/language-server-protocol/) - Protocol reference
