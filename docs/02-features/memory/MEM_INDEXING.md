# Memory Indexing System

This document describes Aurora's memory indexing pipeline from file discovery to storage.

## Overview

Aurora's memory system indexes code and documents for semantic search. The pipeline:

1. **Discovers** files respecting ignore patterns
2. **Incrementally** detects changes (git-based)
3. **Parses** language-specific AST structures
4. **Extracts** git signals for activation scoring
5. **Generates** embeddings for semantic search
6. **Stores** chunks in SQLite with metadata

## Quick Start

```bash
# Index current directory
aur mem index .

# Index specific path
aur mem index src/

# Search indexed memory
aur mem search "authentication"

# View statistics
aur mem stats
```

---

## Pipeline Stages

### 1. File Discovery

**File:** `packages/cli/src/aurora_cli/memory_manager.py` - `_discover_files()`

The indexer recursively scans directories, filtering:

- **Skip directories**: `.git`, `node_modules`, `__pycache__`, `.venv`, `dist/`, `build/`
- **Custom patterns**: `.auroraignore` file (gitignore syntax)
- **Parser availability**: Only files with registered parsers

```python
# Skip directories (hardcoded)
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'dist', 'build', ...}
```

### 2. Incremental Change Detection

**File:** `packages/cli/src/aurora_cli/memory_manager.py` - `index_path()`

Three-tier strategy (fastest to slowest):

| Tier | Method | Speed | When Used |
|------|--------|-------|-----------|
| 1 | Git status | ~100ms | Git repo with clean working tree |
| 2 | File mtime | ~10ms/file | File timestamp changed |
| 3 | Content hash | ~50ms/file | Verify actual content change |

```sql
-- File index tracking table
CREATE TABLE file_index (
    file_path TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,    -- SHA-256
    mtime REAL NOT NULL,           -- Unix timestamp
    indexed_at TIMESTAMP NOT NULL,
    chunk_count INTEGER DEFAULT 0
);
```

**Result**: Typically skips 95%+ of files on re-index.

### 3. Language-Specific Parsing

**Directory:** `packages/context-code/src/aurora_context_code/languages/`

Each language has a dedicated parser using tree-sitter for AST parsing:

| Language | Parser | Extracts |
|----------|--------|----------|
| Python | `PythonParser` | functions, classes, methods, imports |
| JavaScript | `JavaScriptParser` | functions, classes, arrow functions |
| TypeScript | `TypeScriptParser` | functions, classes, interfaces, types |
| Go | `GoParser` | functions, methods, structs, interfaces |
| Java | `JavaParser` | classes, interfaces, methods, enums |
| Markdown | `MarkdownParser` | sections by `##` headers |

**Parser Interface:**
```python
class CodeParser(ABC):
    def can_parse(self, file_path: Path) -> bool: ...
    def parse(self, file_path: Path) -> list[CodeChunk]: ...
```

**Python Example:**
```python
# Input: my_module.py
def authenticate(user: str, password: str) -> bool:
    """Authenticate user with password."""
    return check_credentials(user, password)

# Output: CodeChunk
CodeChunk(
    chunk_id="my_module_authenticate_a1b2c3",
    file_path="/path/to/my_module.py",
    element_type="function",
    name="authenticate",
    line_start=1,
    line_end=4,
    signature="def authenticate(user: str, password: str) -> bool:",
    docstring="Authenticate user with password.",
    dependencies=["check_credentials"],
    complexity_score=0.15,
    language="python"
)
```

### 4. Chunk Type System

**File:** `packages/core/src/aurora_core/chunk_types.py`

Chunks are categorized by source:

| Type | Extensions | Description |
|------|------------|-------------|
| `code` | `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.go`, `.java` | Source code (tree-sitter parsed) |
| `kb` | `.md`, `.markdown` | Knowledge base (documentation) |
| `doc` | `.pdf`, `.docx`, `.txt` | Documents |
| `reas` | context-based | Reasoning traces (SOAR/goals output) |

```python
# Extension-based type mapping
EXTENSION_TYPE_MAP = {
    ".py": "code", ".pyi": "code",
    ".js": "code", ".jsx": "code",
    ".ts": "code", ".tsx": "code",
    ".go": "code", ".java": "code",
    ".md": "kb", ".markdown": "kb",
    ".pdf": "doc", ".docx": "doc", ".txt": "doc",
}

# Context-based override (takes precedence)
CONTEXT_TYPE_MAP = {
    "soar_result": "reas",
    "goals_output": "reas",
}

def get_chunk_type(file_path=None, context=None) -> str:
    """Determine chunk type from file extension or context."""
    if context and context in CONTEXT_TYPE_MAP:
        return CONTEXT_TYPE_MAP[context]
    if file_path:
        ext = Path(file_path).suffix.lower()
        return EXTENSION_TYPE_MAP.get(ext, "code")
    return "code"
```

### 5. Git Signal Extraction

**File:** `packages/context-code/src/aurora_context_code/git.py`

Extracts commit history for activation scoring:

```bash
# One git blame per file (optimized)
git blame --line-porcelain file.py
```

**Extracted signals:**
- Commit timestamps (when was this code last touched?)
- Commit count (how many times modified?)
- Author information
- Latest commit hash

**Base-Level Activation (BLA):**
```python
# Decay function: recently modified code has higher activation
BLA = 0.5 ^ (age_in_years)

# Example: Code modified 6 months ago
BLA = 0.5 ^ 0.5 = 0.707
```

### 6. Embedding Generation

**File:** `packages/context-code/src/aurora_context_code/semantic/embedding_provider.py`

Uses `sentence-transformers/all-MiniLM-L6-v2`:

| Property | Value |
|----------|-------|
| Dimensions | 384 |
| Speed | ~1000 texts/sec (GPU) |
| Normalization | L2 normalized |
| Batch size | 32 (configurable) |

**Content for embedding:**
```
{signature}

{docstring}

{element_type} {name}
```

**Fallback**: If ML dependencies unavailable, uses BM25-only retrieval (~85% quality).

### 7. BM25 Keyword Indexing

**File:** `packages/context-code/src/aurora_context_code/semantic/bm25_scorer.py`

Code-aware tokenization splits identifiers:

```python
# Input
"getUserData"

# Output tokens
["get", "User", "Data", "getuserdata"]
```

**BM25 Parameters:**
- `k1 = 1.5` (term frequency saturation)
- `b = 0.75` (length normalization)

**Persistence:** `.aurora/indexes/bm25_index.pkl`

### 8. SQLite Storage

**File:** `packages/core/src/aurora_core/store/sqlite.py`

**Database:** `.aurora/memory.db`

```sql
-- Main chunks table
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,      -- "code", "kb", "doc", "reas"
    content TEXT NOT NULL,   -- JSON blob
    metadata TEXT NOT NULL,  -- JSON blob
    embeddings BLOB,         -- 384-dim float32 numpy array
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Activation tracking
CREATE TABLE activations (
    chunk_id TEXT PRIMARY KEY,
    base_level REAL,         -- Git-based BLA
    access_count INTEGER,    -- Session access count
    last_access TIMESTAMP
);

-- File change tracking
CREATE TABLE file_index (
    file_path TEXT PRIMARY KEY,
    content_hash TEXT,
    mtime REAL,
    indexed_at TIMESTAMP,
    chunk_count INTEGER
);
```

**Content JSON schema:**
```json
{
    "file": "/absolute/path/to/file.py",
    "function": "authenticate",
    "line_start": 42,
    "line_end": 67,
    "signature": "def authenticate(user: str) -> bool:",
    "docstring": "Authenticate user.",
    "dependencies": ["check_credentials"],
    "ast_summary": {
        "complexity": 0.15,
        "element_type": "function"
    }
}
```

---

## Data Flow Diagram

```
FILES
  │
  ▼
┌─────────────────────────────┐
│ [1] DISCOVER FILES          │
│     - Recursive scan        │
│     - .auroraignore filter  │
│     - Parser availability   │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ [2] INCREMENTAL CHECK       │
│     - Git status (fast)     │
│     - mtime comparison      │
│     - Content hash          │
└──────────────┬──────────────┘
               │ (changed files only)
               ▼
┌─────────────────────────────┐
│ [3] PARALLEL PARSING        │
│     - Tree-sitter AST       │
│     - Extract functions     │
│     - 4-8 worker threads    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ [4] GIT SIGNALS             │
│     - git blame (per file)  │
│     - Commit timestamps     │
│     - Calculate BLA         │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ [5] CHUNK CREATION          │
│     - CodeChunk objects     │
│     - Set chunk type        │
│     - Build embed content   │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ [6] BATCH EMBEDDING         │
│     - all-MiniLM-L6-v2      │
│     - Batch size: 32        │
│     - 384-dim vectors       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ [7] STORAGE                 │
│     - SQLite (WAL mode)     │
│     - Chunks table          │
│     - Activations table     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ [8] BM25 INDEX              │
│     - Build inverted index  │
│     - Persist to disk       │
└─────────────────────────────┘
               │
               ▼
        SEARCHABLE MEMORY
```

---

## Hybrid Retrieval

**File:** `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`

Search combines three signals:

```
Final Score = BM25 × 0.3 + Semantic × 0.4 + Activation × 0.3
```

| Component | Weight | Description |
|-----------|--------|-------------|
| BM25 | 30% | Keyword exact match |
| Semantic | 40% | Embedding cosine similarity |
| Activation | 30% | Recency + frequency from git/access |

**Search flow:**
1. BM25 filters to top 100 candidates
2. Tri-hybrid re-ranks with all three scores
3. Returns top k results

---

## Performance Characteristics

| Operation | Typical Time | Notes |
|-----------|--------------|-------|
| File discovery | O(n) files | Respects .auroraignore |
| Incremental check | ~100ms total | Git-based, skips 95% |
| Parsing | ~100 files/sec | 4-8 parallel workers |
| Embedding | ~1000 texts/sec | GPU, batched |
| Storage | ~500 chunks/sec | SQLite WAL mode |
| Search | ~200ms | BM25 + semantic + activation |

**Re-indexing optimization**: After initial index, re-index typically processes only changed files (~5%).

---

## Key Files Reference

| Component | File |
|-----------|------|
| CLI command | `packages/cli/src/aurora_cli/commands/memory.py` |
| Indexing orchestrator | `packages/cli/src/aurora_cli/memory_manager.py` |
| Python parser | `packages/context-code/src/aurora_context_code/languages/python.py` |
| JavaScript parser | `packages/context-code/src/aurora_context_code/languages/javascript.py` |
| TypeScript parser | `packages/context-code/src/aurora_context_code/languages/typescript.py` |
| Go parser | `packages/context-code/src/aurora_context_code/languages/go.py` |
| Java parser | `packages/context-code/src/aurora_context_code/languages/java.py` |
| Markdown parser | `packages/context-code/src/aurora_context_code/languages/markdown.py` |
| Embedding provider | `packages/context-code/src/aurora_context_code/semantic/embedding_provider.py` |
| Hybrid retriever | `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` |
| BM25 scorer | `packages/context-code/src/aurora_context_code/semantic/bm25_scorer.py` |
| Chunk types | `packages/core/src/aurora_core/chunk_types.py` |
| CodeChunk model | `packages/core/src/aurora_core/chunks/code_chunk.py` |
| SQLite store | `packages/core/src/aurora_core/store/sqlite.py` |
| Git extractor | `packages/context-code/src/aurora_context_code/git.py` |

---

## Adding a New Language

When adding support for a new language, follow this checklist. Each layer is independent
but they build on each other — indexing works without LSP, but LSP tools need indexing first.

### Layer 1: Tree-sitter Indexing (required)

1. **Add parser** in `packages/context-code/src/aurora_context_code/languages/`
   - Implement `CodeParser` with `can_parse()` and `parse()`
   - Install tree-sitter grammar: `pip install tree-sitter-<language>`
   - Extract functions, classes, methods with signatures and docstrings
   - Register parser in `__init__.py`

2. **Add language config** in `packages/lsp/src/aurora_lsp/languages/`
   - Define branch types (for complexity), entry points, callback methods
   - Define `skip_deadcode_names` for framework-specific patterns
   - Define `function_def_types` and `call_node_type` for tree-sitter queries

3. **Update chunk types** in `packages/core/src/aurora_core/chunk_types.py`
   - Add file extensions to `EXTENSION_TYPE_MAP`

4. **Warning filter** in `packages/cli/src/aurora_cli/commands/memory.py`
   - Add the new logger name to `_LANGUAGE_LOGGER_NAMES` (e.g., `"aurora_context_code.languages.rust"`)
   - Python logging filters do NOT propagate to child loggers — each must be listed explicitly

### Layer 2: LSP Language Config (required for lsp tools)

1. **Add language mapping** in `packages/lsp/src/aurora_lsp/client.py`
   - Map file extensions to `Language.*` enum in `LANGUAGE_MAP`

2. **Add import filter patterns** in `packages/lsp/src/aurora_lsp/filters.py`
   - Define regex patterns to filter import lines from reference results

### Layer 3: LSP Language Server (needed for accurate results)

Without this, `impact`, `related`, and accurate `deadcode` fall back to ripgrep text search.

1. **Verify language server binary** is installed and in PATH
   - Python: `pylsp` or `pyright` (multilspy handles this)
   - JS/TS: `typescript-language-server` (needs `npm install -g typescript-language-server typescript`)
   - Go: `gopls`
   - Java: `jdtls`
   - Rust: `rust-analyzer`

2. **Test that multilspy starts the server** for your language
   - Check logs: `Starting <LANGUAGE> language server for <workspace>`
   - If startup fails, errors are logged at WARNING level

3. **Check if multilspy's `initialize_params.json` is correct** for your language
   - Located at `site-packages/multilspy/language_servers/<name>/initialize_params.json`
   - TS had 400 lines of Rust-analyzer config in `initializationOptions` — check for copy-paste errors
   - If wrong, add a monkey-patch in `packages/lsp/src/aurora_lsp/multilspy_patches.py`
   - We can't modify multilspy's installed package (pip reinstall would overwrite)

4. **Check if the language server needs workspace file discovery**
   - Some servers (gopls, rust-analyzer) discover files via `go.mod`/`Cargo.toml` automatically
   - Others (TS) need explicit `didChangeWatchedFiles` notifications — see `multilspy_patches.py`
   - Test by running `lsp impact` on a symbol with known cross-file references
   - If only within-file refs are returned, add file discovery in `multilspy_patches.py`

### Common Mistakes (learned from JS/TS testing)

| Mistake | What Happens | Fix |
|---------|-------------|-----|
| multilspy's `initialize_params.json` has wrong language config | Server starts but returns only within-file refs (TS had Rust-analyzer settings) | Monkey-patch `_get_initialize_params` in `multilspy_patches.py` |
| Calling `server.open_file(path)` without entering the context manager | `didOpen` never sent, LSP server doesn't know about the file | Must call `ctx = server.open_file(path); ctx.__enter__()` — it's a `@contextmanager` |
| Language server has no workspace file discovery | Cross-file references return 0 results; only the opened file is analyzed | Send `didChangeWatchedFiles` with discovered project files (see TS patch) |
| Assuming all language servers need the same fix | Wasted effort patching servers that work fine | Test first: gopls discovers files via `go.mod` automatically, rust-analyzer uses `Cargo.toml` |
| Only wiring tree-sitter + ripgrep fallback, not the actual LSP server | `impact` returns 1 file instead of 6, `related` returns 0 calls | Install and verify the language server binary |
| Not adding timer/scheduler callbacks to `JS_CALLBACK_METHODS` | `setInterval(fn, 1000)` callbacks flagged as dead code | Add `setTimeout`, `setInterval`, `setImmediate`, `requestAnimationFrame` |
| Not adding framework event patterns to `JS_SKIP_DEADCODE_NAMES` | `bot.on('message', handler)` → handler flagged dead | Add framework-specific callback names |
| Missing `skip_names` for built-in methods | Callee analysis (`related`) returns noisy results with `console.log`, `Array.push` | Add language built-ins to `JS_SKIP_NAMES` |
| BM25 content too sparse for languages without docstrings | Descriptive queries like "DocumentStore search FTS5" return 0 results | Include `dependencies` and `file_path` in BM25 content |
| Silent LSP failures (debug-level logging) | User sees empty results with no explanation | Log server startup failures at WARNING, empty references at INFO |
| Not testing with a real project | Unit tests pass but real-world results are wrong | Test with a real project; check `mem_search`, `lsp impact`, `lsp related`, `lsp deadcode` |
| Stale `.pyc` files after editing aurora_lsp | MCP server loads old bytecode, filters don't apply | Delete `*.cpython-*.pyc`, `touch` source files, kill ALL MCP processes |
| Multiple MCP server processes across sessions | Killing one doesn't fix it — tool calls may hit another | `ps aux \| grep aurora_mcp` and kill all, or restart Claude Code |
| `.mcp.json` changes mid-session | Claude Code reads config at startup only | Restart Claude Code for config changes (e.g., adding `-B` flag) |

### Effort Estimate

| Layer | Effort | Result |
|-------|--------|--------|
| Tree-sitter indexing | 1-2 days | `mem_search` works, basic `lsp check` via ripgrep |
| LSP language config | 0.5 day | `lsp deadcode` (fast mode), `lsp imports` |
| LSP language server | 2-3 days | Full `lsp impact`, `lsp related`, accurate `lsp deadcode` |

**Rust-specific notes:** multilspy already has a Rust language server class, and ironically
the TS `initialize_params.json` already contained rust-analyzer settings (that's the bug we
fixed for TS). rust-analyzer discovers workspace via `Cargo.toml` like gopls uses `go.mod`,
so it likely needs no file discovery patches. The main work is Layer 1 (tree-sitter-rust parser)
and Layer 2 (language config with Rust-specific branch types, skip names). Test cross-file refs
early — if they work out of the box like Go, skip monkey-patching entirely.

---

## See Also

- [ACTR_ACTIVATION.md](ACTR_ACTIVATION.md) - Activation scoring details
- [ML_MODELS.md](ML_MODELS.md) - Embedding model configuration
- [CACHING_GUIDE.md](CACHING_GUIDE.md) - Query caching strategies
- [/docs/lsp/JS_IMPROVEMENTS.md](/docs/lsp/JS_IMPROVEMENTS.md) - JS-specific LSP improvements plan
