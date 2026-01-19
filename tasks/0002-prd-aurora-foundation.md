# PRD 0002: AURORA Foundation & Infrastructure
## Product Requirements Document

**Version**: 1.0
**Date**: December 20, 2025
**Status**: Ready for Implementation
**Phase**: MVP Phase 1 of 3 (Foundation)
**Product**: AURORA-Context Framework
**Dependencies**: None (foundational phase)

---

## DOCUMENT PURPOSE

This PRD defines **Phase 1: Foundation & Infrastructure** for the AURORA-Context framework. This phase establishes the core architectural components that Phases 2 (SOAR Pipeline) and 3 (Advanced Memory) depend on.

**Success Criteria**: This phase is complete when all foundational components pass their acceptance tests, quality gates, and delivery verification checklist.

**Related Documents**:
- Source Specification: `/tasks/0001-prd-aurora-context.md`
- Next Phase: `/tasks/0003-prd-aurora-soar-pipeline.md` (depends on this)
- Final Phase: `/tasks/0004-prd-aurora-advanced-features.md` (depends on 0002+0003)

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Goals & Success Metrics](#2-goals--success-metrics)
3. [User Stories](#3-user-stories)
4. [Functional Requirements](#4-functional-requirements)
5. [Architecture & Design](#5-architecture--design)
6. [Quality Gates & Acceptance Criteria](#6-quality-gates--acceptance-criteria)
7. [Testing Strategy](#7-testing-strategy)
8. [Inter-Phase Dependencies](#8-inter-phase-dependencies)
9. [Non-Goals (Out of Scope)](#9-non-goals-out-of-scope)
10. [Technical Considerations](#10-technical-considerations)
11. [Delivery Verification Checklist](#11-delivery-verification-checklist)
12. [Open Questions](#12-open-questions)

---

## 1. EXECUTIVE SUMMARY

### 1.1 What is AURORA Foundation?

AURORA Foundation establishes the core infrastructure for a reasoning architecture framework that enables intelligent context retrieval and agent orchestration. This phase focuses on building **stable, testable, extensible** foundational components.

### 1.2 Key Components (Phase 1)

1. **Storage Layer**: SQLite + JSON persistence with activation tracking
2. **Code Context Provider**: cAST parser for Python code analysis
3. **Context Management**: Retrieval interfaces and chunk management
4. **Agent Registry**: Discovery and registration of available agents
5. **Configuration System**: Multi-layer config with validation
6. **Testing Framework**: Reusable test utilities and harness

### 1.3 Why This Phase First?

Phase 2 (SOAR Pipeline) and Phase 3 (Advanced Memory) cannot function without:
- A working storage layer for caching reasoning patterns
- Code parsing capabilities for context retrieval
- Agent registry for subgoal routing
- Configuration system for LLM integration

**This phase establishes the architectural foundation that makes SOAR orchestration possible.**

---

## 2. GOALS & SUCCESS METRICS

### 2.1 Primary Goals

1. **Establish stable storage architecture** that Phase 2 can rely on
2. **Implement Python code parsing** with function-level chunking
3. **Create extensible context interfaces** for future providers
4. **Build agent discovery system** that Phase 2 can route to
5. **Deliver comprehensive testing framework** for all subsequent phases

### 2.2 Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Code Coverage** | ≥85% for core components | pytest-cov report |
| **Parser Performance** | Parse 1000-line file in <200ms | Benchmark suite |
| **Storage Latency** | Retrieve chunk in <50ms (cold start <200ms) | Performance tests |
| **Memory Footprint** | <100MB for 10K cached chunks | Memory profiler |
| **API Stability** | Zero breaking changes after v1.0 | Interface versioning |
| **Test Execution** | Full suite completes in <5 minutes | CI/CD pipeline |
| **Documentation** | 100% of public APIs documented | Doc coverage tool |

### 2.3 Phase Completion Criteria

Phase 1 is **COMPLETE** when:
- ✅ All functional requirements implemented
- ✅ All quality gates passed
- ✅ All acceptance test scenarios pass
- ✅ Delivery verification checklist signed off
- ✅ Phase 2 dependency contracts documented
- ✅ Performance benchmarks met
- ✅ Documentation complete and reviewed

---

## 3. USER STORIES

### 3.1 Developer Using AURORA (Phase 2+ User)

**As a** developer building the SOAR pipeline (Phase 2),
**I want** stable storage and context retrieval APIs,
**So that** I can implement reasoning orchestration without worrying about infrastructure failures.

**Acceptance Criteria**:
- Storage API has <5% failure rate under load
- Context retrieval returns results in <200ms p95
- All interfaces are documented with examples
- Breaking changes require major version bump

---

### 3.2 Framework Extension Developer

**As a** developer extending AURORA with new parsers,
**I want** clear extension points and plugin interfaces,
**So that** I can add support for new languages without modifying core code.

**Acceptance Criteria**:
- Parser interface is abstract and well-documented
- Example custom parser implementation included
- Plugin registration mechanism works
- Extension can be added without recompiling core

---

### 3.3 QA Engineer

**As a** QA engineer validating AURORA phases,
**I want** a comprehensive testing framework with reusable utilities,
**So that** I can write consistent tests across all phases.

**Acceptance Criteria**:
- Test harness supports mocking LLM responses
- Storage fixtures available for test isolation
- Performance benchmarking utilities included
- Test examples cover common scenarios

---

### 3.4 End User (Future - Phase 2+)

**As a** developer using Claude Code with AURORA,
**I want** fast, relevant code context retrieval,
**So that** my queries get answered with accurate project-specific information.

**Acceptance Criteria** (tested via Phase 1 components):
- Python code parsed into function-level chunks
- Chunks stored with metadata (file, line range, dependencies)
- Retrieval finds relevant chunks based on query
- Cache persists across sessions

---

## 4. FUNCTIONAL REQUIREMENTS

### 4.1 Storage Layer (Core Package)

**Package**: `packages/core/src/aurora_core/store/`

#### 4.1.1 SQLite Schema

**MUST** implement three tables:

**Table: `chunks`**
```sql
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,              -- Format: "code:file:func" or "reas:pattern-id"
    type TEXT NOT NULL,               -- "code" | "reasoning" | "knowledge"
    content JSON NOT NULL,            -- Chunk-specific JSON structure
    metadata JSON,                    -- Optional metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_chunks_type ON chunks(type);
CREATE INDEX idx_chunks_created ON chunks(created_at);
```

**Table: `activations`**
```sql
CREATE TABLE activations (
    chunk_id TEXT PRIMARY KEY,
    base_level REAL NOT NULL,         -- Base-level activation (BLA)
    last_access TIMESTAMP NOT NULL,
    access_count INTEGER DEFAULT 1,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);
CREATE INDEX idx_activations_base ON activations(base_level DESC);
```

**Table: `relationships`**
```sql
CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_chunk TEXT NOT NULL,
    to_chunk TEXT NOT NULL,
    relationship_type TEXT NOT NULL,  -- "depends_on" | "calls" | "imports"
    weight REAL DEFAULT 1.0,
    FOREIGN KEY (from_chunk) REFERENCES chunks(id) ON DELETE CASCADE,
    FOREIGN KEY (to_chunk) REFERENCES chunks(id) ON DELETE CASCADE
);
CREATE INDEX idx_rel_from ON relationships(from_chunk);
CREATE INDEX idx_rel_to ON relationships(to_chunk);
```

#### 4.1.2 Storage Interface

**MUST** provide abstract `Store` interface:

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from aurora_core.types import ChunkID, Chunk, Activation

class Store(ABC):
    """Abstract storage interface for AURORA chunks."""

    @abstractmethod
    def save_chunk(self, chunk: Chunk) -> bool:
        """Save a chunk to storage. Returns True on success."""
        pass

    @abstractmethod
    def get_chunk(self, chunk_id: ChunkID) -> Optional[Chunk]:
        """Retrieve a chunk by ID. Returns None if not found."""
        pass

    @abstractmethod
    def update_activation(self, chunk_id: ChunkID, delta: float) -> None:
        """Update activation score for a chunk."""
        pass

    @abstractmethod
    def retrieve_by_activation(self, min_activation: float, limit: int) -> List[Chunk]:
        """Retrieve top N chunks above activation threshold."""
        pass

    @abstractmethod
    def add_relationship(self, from_id: ChunkID, to_id: ChunkID,
                        rel_type: str, weight: float = 1.0) -> bool:
        """Add a relationship between two chunks."""
        pass

    @abstractmethod
    def get_related_chunks(self, chunk_id: ChunkID, max_depth: int = 2) -> List[Chunk]:
        """Get related chunks via relationships (for spreading activation)."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close storage connection and cleanup."""
        pass
```

#### 4.1.3 SQLite Implementation

**MUST** implement `SQLiteStore(Store)`:
- Thread-safe connection pooling (use `sqlite3` with connection per thread)
- Automatic schema migration on version upgrades
- JSON validation before storage (reject malformed chunks)
- Transaction support for atomic operations
- Connection timeout: 5 seconds
- Max connections: 10 (configurable)

#### 4.1.4 In-Memory Implementation (Testing)

**MUST** implement `MemoryStore(Store)` for testing:
- Same interface as SQLiteStore
- No file I/O (pure in-memory dictionaries)
- Fast reset between tests
- Useful for CI/CD where SQLite file access is restricted

---

### 4.2 Chunk Types (Core Package)

**Package**: `packages/core/src/aurora_core/chunks/`

#### 4.2.1 Base Chunk Interface

**MUST** define abstract `Chunk` class:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class Chunk(ABC):
    """Base class for all AURORA chunks."""

    def __init__(self, chunk_id: str, chunk_type: str):
        self.id = chunk_id
        self.type = chunk_type
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    @abstractmethod
    def to_json(self) -> Dict[str, Any]:
        """Serialize chunk to JSON-compatible dict."""
        pass

    @abstractmethod
    def from_json(cls, data: Dict[str, Any]) -> 'Chunk':
        """Deserialize chunk from JSON dict."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate chunk structure. Raises ValueError if invalid."""
        pass
```

#### 4.2.2 CodeChunk Implementation

**MUST** implement `CodeChunk(Chunk)`:

```python
@dataclass
class CodeChunk(Chunk):
    """Represents a parsed code element (function, class, method)."""

    file_path: str                    # Absolute path to source file
    element_type: str                 # "function" | "class" | "method"
    name: str                         # Function/class name
    line_start: int                   # Starting line number
    line_end: int                     # Ending line number
    signature: Optional[str]          # Function signature if applicable
    docstring: Optional[str]          # Extracted docstring
    dependencies: List[str]           # List of chunk IDs this depends on
    complexity_score: float           # Cyclomatic complexity (0.0-1.0)
    language: str                     # "python" | "typescript" | "go"

    def to_json(self) -> Dict[str, Any]:
        """Serialize to JSON matching schema in spec Section 6.3.5."""
        return {
            "id": self.id,
            "type": "code",
            "content": {
                "file": self.file_path,
                "function": self.name,
                "line_start": self.line_start,
                "line_end": self.line_end,
                "signature": self.signature,
                "dependencies": self.dependencies,
                "ast_summary": {
                    "complexity": self.complexity_score,
                    "element_type": self.element_type
                }
            },
            "metadata": {
                "language": self.language,
                "last_modified": self.updated_at.isoformat()
            }
        }
```

**Validation Rules**:
- `line_start` must be > 0
- `line_end` must be >= `line_start`
- `file_path` must be absolute
- `complexity_score` must be in [0.0, 1.0]
- `language` must be in supported languages list

#### 4.2.3 ReasoningChunk (Stub for Phase 2)

**MUST** define `ReasoningChunk(Chunk)` interface (no implementation yet):
- JSON schema defined (see spec Section 6.3.5)
- Class stub with `to_json()` / `from_json()` signatures
- Phase 2 will implement full functionality

---

### 4.3 Code Context Provider (Context-Code Package)

**Package**: `packages/context-code/src/aurora_context_code/`

#### 4.3.1 Parser Interface

**MUST** define abstract `CodeParser` interface:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pathlib import Path
from aurora_core.chunks import CodeChunk

class CodeParser(ABC):
    """Abstract interface for language-specific code parsers."""

    @abstractmethod
    def parse_file(self, file_path: Path) -> List[CodeChunk]:
        """Parse a source file into code chunks."""
        pass

    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions (e.g., ['.py'])."""
        pass

    @abstractmethod
    def get_dependencies(self, chunk: CodeChunk) -> List[str]:
        """Extract dependencies for a code chunk."""
        pass
```

#### 4.3.2 Python Parser Implementation

**MUST** implement `PythonParser(CodeParser)` using tree-sitter:

**Dependencies**:
- `tree-sitter` (v0.21+)
- `tree-sitter-python` (latest)

**Parsing Capabilities**:
- Extract top-level functions
- Extract classes and methods
- Extract function signatures (name, args, return type)
- Extract docstrings (first string literal after definition)
- Calculate cyclomatic complexity (basic: count branches)
- Identify imports and function calls

**Algorithm**:
1. Parse file with tree-sitter into AST
2. Traverse AST for function/class definitions
3. For each definition:
   - Extract name, line range, signature
   - Find docstring (first string child node)
   - Count branch points (if/for/while/try) for complexity
   - Identify called functions (for dependencies)
4. Create `CodeChunk` for each element
5. Return list of chunks

**Error Handling**:
- If parse fails: log error, return empty list (don't crash)
- If file not found: raise `FileNotFoundError`
- If file too large (>50K lines): log warning, parse anyway

**Performance Target**: <200ms for 1000-line file

#### 4.3.3 Parser Registry

**MUST** implement `ParserRegistry` for multi-language support:

```python
class ParserRegistry:
    """Registry for code parsers by language."""

    def __init__(self):
        self._parsers: Dict[str, CodeParser] = {}

    def register(self, parser: CodeParser) -> None:
        """Register a parser for its supported extensions."""
        for ext in parser.supported_extensions():
            self._parsers[ext] = parser

    def get_parser(self, file_path: Path) -> Optional[CodeParser]:
        """Get parser for a file based on extension."""
        ext = file_path.suffix
        return self._parsers.get(ext)

    def parse_file(self, file_path: Path) -> List[CodeChunk]:
        """Auto-select parser and parse file."""
        parser = self.get_parser(file_path)
        if not parser:
            raise ValueError(f"No parser for {file_path.suffix}")
        return parser.parse_file(file_path)
```

**Default Registration**: Auto-register `PythonParser` on import

---

### 4.4 Context Management (Core Package)

**Package**: `packages/core/src/aurora_core/context/`

#### 4.4.1 Context Provider Interface

**MUST** define abstract `ContextProvider` interface:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from aurora_core.chunks import Chunk

class ContextProvider(ABC):
    """Abstract interface for context retrieval providers."""

    @abstractmethod
    def retrieve(self, query: str, budget: int = 10) -> List[Chunk]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: User query string
            budget: Max number of chunks to return

        Returns:
            List of relevant chunks, sorted by relevance (highest first)
        """
        pass

    @abstractmethod
    def update(self, chunk: Chunk, success: bool = True) -> None:
        """
        Update provider state based on usage outcome.

        Args:
            chunk: The chunk that was used
            success: Whether usage was successful (for learning)
        """
        pass
```

#### 4.4.2 Code Context Provider

**MUST** implement `CodeContextProvider(ContextProvider)`:

**Dependencies**:
- Uses `ParserRegistry` to parse code
- Uses `Store` to cache/retrieve chunks
- Uses basic keyword matching for retrieval (Phase 1)

**Retrieval Algorithm (Simple for Phase 1)**:
1. Parse query into keywords (lowercase, split on whitespace)
2. Search cached chunks for keyword matches:
   - Match against function/class names
   - Match against docstrings
   - Match against file paths
3. Score each chunk: `score = keyword_matches / total_keywords`
4. Return top N chunks sorted by score

**Caching Strategy**:
- On first parse: Cache all chunks to storage
- On subsequent queries: Retrieve from cache
- Update `last_access` timestamp on retrieval
- Invalidate cache if source file modified (check mtime)

**Phase 2 Upgrade Path**: Replace keyword matching with activation-based retrieval

---

### 4.5 Agent Registry (SOAR Package Stub)

**Package**: `packages/soar/src/aurora_soar/agent_registry.py`

**Note**: Full SOAR orchestrator is Phase 2. This phase creates the **registry only**.

#### 4.5.1 Agent Registry Interface

**MUST** implement `AgentRegistry` class:

```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class AgentInfo:
    """Information about a registered agent."""
    id: str                          # Unique agent ID
    type: str                        # "mcp" | "executable" | "http" | "builtin"
    path: Optional[Path]             # File path for mcp/executable
    endpoint: Optional[str]          # URL for http agents
    capabilities: List[str]          # ["code_implementation", "debugging", ...]
    domains: List[str]               # ["python", "typescript", ...]
    availability: str                # "always" | "depends_on_network"
    success_rate: float = 0.0        # Historical success rate (0.0-1.0)

class AgentRegistry:
    """Registry for discovering and managing available agents."""

    def __init__(self, config_paths: List[Path]):
        self._agents: Dict[str, AgentInfo] = {}
        self._load_agents(config_paths)

    def register(self, agent: AgentInfo) -> None:
        """Register an agent manually."""
        self._agents[agent.id] = agent

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent info by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentInfo]:
        """List all registered agents."""
        return list(self._agents.values())

    def find_by_capability(self, capability: str) -> List[AgentInfo]:
        """Find agents with a specific capability."""
        return [a for a in self._agents.values() if capability in a.capabilities]

    def refresh(self) -> int:
        """Re-scan config files for new agents. Returns count of new agents."""
        # Check config file mtimes, reload if changed
        pass
```

#### 4.5.2 Agent Discovery

**Discovery Paths** (in order):
1. `<project>/.aurora/agents.json` (project-specific)
2. `~/.aurora/agents.json` (global user agents)
3. MCP server config (if available)

**Agent Config Format** (`agents.json`):
```json
{
  "agents": [
    {
      "id": "code-developer",
      "type": "mcp",
      "path": "~/.claude/agents/code-developer",
      "capabilities": ["code_implementation", "debugging", "refactoring"],
      "domains": ["python", "typescript"],
      "availability": "always"
    },
    {
      "id": "research-agent",
      "type": "executable",
      "path": "/usr/local/bin/research-agent",
      "capabilities": ["web_search", "documentation_lookup"],
      "domains": ["general"],
      "availability": "always"
    }
  ]
}
```

**Validation**:
- Required fields: `id`, `type`, `capabilities`, `domains`
- `type` must be in: `["mcp", "executable", "http", "builtin"]`
- If `type == "mcp"` or `"executable"`: `path` is required
- If `type == "http"`: `endpoint` is required
- Reject invalid entries with clear error message

**Fallback**: If no agents found, register default built-in agent:
```python
AgentInfo(
    id="llm-executor",
    type="builtin",
    path=None,
    endpoint=None,
    capabilities=["all"],
    domains=["general"],
    availability="always"
)
```

---

### 4.6 Configuration System (Core Package)

**Package**: `packages/core/src/aurora_core/config/`

#### 4.6.1 Configuration Schema

**MUST** define JSON schema for configuration (see spec Appendix C for full schema):

**Core Configuration Structure**:
```json
{
  "version": "1.0",
  "mode": "mcp_integrated",
  "storage": {
    "type": "sqlite",
    "path": "~/.aurora/memory.db",
    "max_connections": 10,
    "timeout_seconds": 5
  },
  "llm": {
    "reasoning_provider": "anthropic",
    "reasoning_model": "claude-3-5-sonnet-20241022",
    "solving_provider": "anthropic",
    "solving_model": "claude-opus-4-5-20251101",
    "api_key_env": "ANTHROPIC_API_KEY",
    "base_url": null,
    "timeout_seconds": 30
  },
  "context": {
    "code": {
      "enabled": true,
      "languages": ["python"],
      "max_file_size_kb": 500,
      "cache_ttl_hours": 24
    }
  },
  "agents": {
    "discovery_paths": [
      ".aurora/agents.json",
      "~/.aurora/agents.json"
    ],
    "refresh_interval_days": 15,
    "fallback_mode": "llm_only"
  },
  "logging": {
    "level": "INFO",
    "path": "~/.aurora/logs/",
    "max_size_mb": 100,
    "max_files": 10
  }
}
```

#### 4.6.2 Configuration Loading

**MUST** implement `ConfigLoader` class:

**Override Hierarchy** (highest priority first):
1. CLI flags (e.g., `--storage-path=/custom/path`)
2. Environment variables (e.g., `AURORA_STORAGE_PATH`)
3. Project config: `<project>/.aurora/config.json`
4. Global config: `~/.aurora/config.json`
5. Package defaults: `aurora_core/config/defaults.json`

**Environment Variable Mapping**:
- `AURORA_STORAGE_PATH` → `storage.path`
- `AURORA_LLM_PROVIDER` → `llm.reasoning_provider`
- `AURORA_API_KEY` → Used if `llm.api_key_env` not set
- `AURORA_LOG_LEVEL` → `logging.level`

**Validation**:
- Validate against JSON schema on load
- Expand tilde paths (`~`) to absolute paths
- Check file existence for required files (storage path parent dir)
- Validate enum values (mode, provider, log level)
- Raise `ConfigurationError` with clear message on failure

#### 4.6.3 Configuration API

```python
from typing import Any, Optional
from pathlib import Path

class Config:
    """Typed configuration access."""

    @staticmethod
    def load(project_path: Optional[Path] = None,
             cli_overrides: Optional[Dict[str, Any]] = None) -> 'Config':
        """Load configuration with override hierarchy."""
        pass

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key (e.g., 'storage.path')."""
        pass

    def storage_path(self) -> Path:
        """Get storage path (expanded to absolute)."""
        pass

    def llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        pass

    def validate(self) -> bool:
        """Validate configuration. Raises ConfigurationError if invalid."""
        pass
```

---

### 4.7 Testing Framework (Test Utilities)

**Package**: `packages/testing/` (new package)

#### 4.7.1 Test Utilities

**MUST** provide reusable test utilities:

```python
# packages/testing/src/aurora_testing/fixtures.py

import pytest
from pathlib import Path
from aurora_core.store import MemoryStore, SQLiteStore
from aurora_core.chunks import CodeChunk

@pytest.fixture
def memory_store():
    """Provide clean in-memory store for testing."""
    store = MemoryStore()
    yield store
    store.close()

@pytest.fixture
def temp_sqlite_store(tmp_path):
    """Provide temporary SQLite store for testing."""
    db_path = tmp_path / "test.db"
    store = SQLiteStore(db_path)
    yield store
    store.close()
    if db_path.exists():
        db_path.unlink()

@pytest.fixture
def sample_code_chunk():
    """Provide sample CodeChunk for testing."""
    return CodeChunk(
        chunk_id="code:test.py:sample_func",
        chunk_type="code",
        file_path="/path/to/test.py",
        element_type="function",
        name="sample_func",
        line_start=10,
        line_end=20,
        signature="def sample_func(x: int) -> str:",
        docstring="Sample function for testing.",
        dependencies=[],
        complexity_score=0.3,
        language="python"
    )
```

#### 4.7.2 Mock LLM Responses

```python
# packages/testing/src/aurora_testing/mocks.py

from typing import Dict, Any, Callable
from unittest.mock import Mock

class MockLLM:
    """Mock LLM for predictable testing."""

    def __init__(self):
        self.call_count = 0
        self.responses: Dict[str, Any] = {}

    def set_response(self, prompt_key: str, response: Any) -> None:
        """Configure response for a specific prompt."""
        self.responses[prompt_key] = response

    def generate(self, prompt: str, **kwargs) -> str:
        """Mock generation (matches real LLM API)."""
        self.call_count += 1
        for key, response in self.responses.items():
            if key in prompt:
                return response
        return '{"error": "No mock response configured"}'
```

#### 4.7.3 Performance Benchmarking

```python
# packages/testing/src/aurora_testing/benchmarks.py

import time
from typing import Callable, Dict, Any
from contextlib import contextmanager

class PerformanceBenchmark:
    """Utility for performance testing."""

    @contextmanager
    def measure(self, operation: str):
        """Context manager to measure operation time."""
        start = time.perf_counter()
        yield
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.results[operation] = elapsed_ms

    def assert_performance(self, operation: str, max_ms: float) -> None:
        """Assert operation completed within time limit."""
        actual = self.results.get(operation)
        assert actual is not None, f"No timing for {operation}"
        assert actual <= max_ms, f"{operation} took {actual:.2f}ms (limit: {max_ms}ms)"
```

---

## 5. ARCHITECTURE & DESIGN

### 5.1 Package Structure

```
aurora-context/
├── packages/
│   ├── core/                          # Core foundation (no external deps except pyactr)
│   │   ├── pyproject.toml
│   │   └── src/aurora_core/
│   │       ├── __init__.py
│   │       ├── chunks/                # Chunk type definitions
│   │       │   ├── __init__.py
│   │       │   ├── base.py            # Abstract Chunk class
│   │       │   ├── code_chunk.py      # CodeChunk implementation
│   │       │   └── reasoning_chunk.py # Stub for Phase 2
│   │       ├── store/                 # Storage layer
│   │       │   ├── __init__.py
│   │       │   ├── base.py            # Abstract Store interface
│   │       │   ├── sqlite.py          # SQLiteStore implementation
│   │       │   └── memory.py          # MemoryStore (testing)
│   │       ├── context/               # Context management
│   │       │   ├── __init__.py
│   │       │   ├── provider.py        # Abstract ContextProvider
│   │       │   └── code_provider.py   # CodeContextProvider
│   │       ├── config/                # Configuration system
│   │       │   ├── __init__.py
│   │       │   ├── loader.py          # ConfigLoader
│   │       │   ├── schema.py          # JSON schema validation
│   │       │   └── defaults.json      # Default configuration
│   │       └── types.py               # Shared types (ChunkID, Activation, etc.)
│   │
│   ├── context-code/                  # Code context provider
│   │   ├── pyproject.toml
│   │   └── src/aurora_context_code/
│   │       ├── __init__.py
│   │       ├── parser.py              # Abstract CodeParser
│   │       ├── registry.py            # ParserRegistry
│   │       └── languages/
│   │           ├── __init__.py
│   │           └── python.py          # PythonParser (tree-sitter)
│   │
│   ├── soar/                          # SOAR orchestrator (stub for Phase 2)
│   │   ├── pyproject.toml
│   │   └── src/aurora_soar/
│   │       ├── __init__.py
│   │       └── agent_registry.py      # AgentRegistry only (Phase 1)
│   │
│   └── testing/                       # Test utilities (NEW)
│       ├── pyproject.toml
│       └── src/aurora_testing/
│           ├── __init__.py
│           ├── fixtures.py            # Pytest fixtures
│           ├── mocks.py               # Mock LLM, agents
│           └── benchmarks.py          # Performance utilities
│
├── tests/                             # Test suites
│   ├── unit/                          # Unit tests per package
│   │   ├── test_core_store.py
│   │   ├── test_core_chunks.py
│   │   ├── test_context_code.py
│   │   └── test_agent_registry.py
│   ├── integration/                   # Integration tests
│   │   ├── test_parse_and_store.py   # Parse → Store → Retrieve
│   │   └── test_context_retrieval.py # Context provider end-to-end
│   └── performance/                   # Performance benchmarks
│       ├── test_parser_speed.py
│       └── test_storage_latency.py
│
├── pyproject.toml                     # Root project config
├── Makefile                           # Common commands
└── README.md
```

### 5.2 Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                      PHASE 1 DEPENDENCIES                    │
└─────────────────────────────────────────────────────────────┘

context-code/
    └── depends on → core/ (chunks, store, config)

soar/ (agent_registry only)
    └── depends on → core/ (config)

testing/
    └── depends on → core/, context-code/ (for fixtures)

EXTERNAL DEPENDENCIES:
├── tree-sitter (for PythonParser)
├── tree-sitter-python (language grammar)
└── pyactr (for activation formulas - Phase 2+, stub only in Phase 1)
```

### 5.3 Extension Points (Plugin Architecture)

**Designed for extensibility**:

1. **Custom Parsers**: Implement `CodeParser` interface
   ```python
   class GoParser(CodeParser):
       def parse_file(self, file_path: Path) -> List[CodeChunk]:
           # Custom Go parsing logic
           pass

   # Register with ParserRegistry
   registry.register(GoParser())
   ```

2. **Custom Storage Backends**: Implement `Store` interface
   ```python
   class PostgresStore(Store):
       # PostgreSQL backend instead of SQLite
       pass
   ```

3. **Custom Context Providers**: Implement `ContextProvider` interface
   ```python
   class VectorDBContextProvider(ContextProvider):
       # Use vector embeddings for retrieval
       pass
   ```

**Interface Stability Guarantees**:
- `Store`, `CodeParser`, `ContextProvider` interfaces are **stable** in Phase 1
- Major version bump required for breaking changes
- Deprecation warnings for 2 minor versions before removal

---

## 6. QUALITY GATES & ACCEPTANCE CRITERIA

### 6.1 Code Quality Gates

| Gate | Requirement | Tool | Blocker |
|------|-------------|------|---------|
| **Code Coverage** | ≥85% for core/, ≥80% for context-code/ | pytest-cov | YES |
| **Type Checking** | 0 mypy errors (strict mode) | mypy | YES |
| **Linting** | 0 critical issues, <10 warnings | ruff | YES |
| **Security** | 0 high/critical vulnerabilities | bandit | YES |
| **Complexity** | Cyclomatic complexity <10 per function | radon | NO (warning) |
| **Documentation** | 100% of public APIs documented | pydocstyle | NO (warning) |

### 6.2 Performance Gates

| Metric | Target | Measurement | Blocker |
|--------|--------|-------------|---------|
| **Parser Speed** | <200ms for 1000-line Python file | Benchmark suite | YES |
| **Storage Write** | <50ms per chunk (cold start <200ms) | Benchmark suite | YES |
| **Storage Read** | <50ms per chunk (cold start <200ms) | Benchmark suite | YES |
| **Bulk Retrieval** | <500ms for 100 chunks | Benchmark suite | NO (warning) |
| **Memory Usage** | <100MB for 10K cached chunks | Memory profiler | YES |
| **Startup Time** | <2s to initialize system | Integration test | NO (warning) |

### 6.3 Functional Acceptance Tests

**Each scenario MUST pass before phase completion**:

#### Test Scenario 1: Parse and Store Python File
```python
def test_parse_and_store():
    """Parse Python file, store chunks, verify retrieval."""
    # GIVEN: A sample Python file with 3 functions
    sample_file = Path("samples/auth.py")

    # WHEN: Parse and store
    parser = PythonParser()
    chunks = parser.parse_file(sample_file)

    store = SQLiteStore(":memory:")
    for chunk in chunks:
        store.save_chunk(chunk)

    # THEN: All chunks stored and retrievable
    assert len(chunks) == 3
    retrieved = store.get_chunk(chunks[0].id)
    assert retrieved is not None
    assert retrieved.name == chunks[0].name
```

#### Test Scenario 2: Context Retrieval
```python
def test_context_retrieval():
    """Retrieve relevant code chunks for a query."""
    # GIVEN: 10 cached code chunks (various functions)
    provider = CodeContextProvider(store, parser_registry)

    # WHEN: Query for "authentication"
    results = provider.retrieve("authentication", budget=5)

    # THEN: Top 5 most relevant chunks returned
    assert len(results) <= 5
    assert all(isinstance(c, CodeChunk) for c in results)
    # Verify relevance (e.g., "auth" in function name or docstring)
```

#### Test Scenario 3: Agent Registry Discovery
```python
def test_agent_discovery():
    """Discover agents from config files."""
    # GIVEN: agents.json in project directory
    config_path = Path(".aurora/agents.json")

    # WHEN: Initialize registry
    registry = AgentRegistry([config_path])

    # THEN: Agents loaded and queryable
    agents = registry.list_agents()
    assert len(agents) > 0

    coder = registry.get_agent("code-developer")
    assert coder is not None
    assert "code_implementation" in coder.capabilities
```

#### Test Scenario 4: Configuration Override Hierarchy
```python
def test_config_override():
    """Verify configuration override hierarchy."""
    # GIVEN: Default config + global config + env var
    os.environ["AURORA_STORAGE_PATH"] = "/custom/path"

    # WHEN: Load config
    config = Config.load()

    # THEN: Env var overrides defaults
    assert config.storage_path() == Path("/custom/path")
```

#### Test Scenario 5: Performance Under Load
```python
def test_storage_performance():
    """Verify storage performance with 1000 chunks."""
    # GIVEN: 1000 code chunks
    store = SQLiteStore(":memory:")
    chunks = [create_test_chunk(i) for i in range(1000)]

    # WHEN: Bulk insert
    with benchmark.measure("bulk_insert"):
        for chunk in chunks:
            store.save_chunk(chunk)

    # THEN: Completed within time limit
    benchmark.assert_performance("bulk_insert", max_ms=5000)  # 5s for 1000 chunks

    # AND: Retrieval is fast
    with benchmark.measure("single_read"):
        store.get_chunk(chunks[500].id)

    benchmark.assert_performance("single_read", max_ms=50)
```

---

## 7. TESTING STRATEGY

### 7.1 Test Pyramid

```
        /\
       /  \         E2E Tests (5%)
      /    \        - Full parse → store → retrieve flows
     /------\       - Real file parsing scenarios
    /        \
   /  INTEG.  \     Integration Tests (25%)
  /------------\    - Multi-component interactions
 /              \   - Storage + Parser + Provider
/   UNIT TESTS  \   Unit Tests (70%)
------------------  - Individual classes/functions
```

### 7.2 Unit Test Coverage

**MUST test each component in isolation**:

**Core Package Tests**:
- `test_store_sqlite.py`: All SQLiteStore methods
- `test_store_memory.py`: MemoryStore functionality
- `test_chunk_code.py`: CodeChunk serialization/validation
- `test_config_loader.py`: Configuration loading and overrides

**Context-Code Package Tests**:
- `test_python_parser.py`: Parse various Python constructs
- `test_parser_registry.py`: Registry and auto-selection
- `test_code_provider.py`: Context retrieval logic

**SOAR Package Tests**:
- `test_agent_registry.py`: Agent discovery and queries

### 7.3 Integration Test Scenarios

**MUST test component interactions**:

1. **Parse → Store → Retrieve**
   - Parse Python file → Store chunks → Retrieve by ID → Verify content

2. **Context Provider End-to-End**
   - Parse multiple files → Cache to storage → Query for context → Verify relevance

3. **Configuration → Storage**
   - Load config → Initialize storage with custom path → Verify DB created

4. **Agent Registry → Config**
   - Load agent config → Register agents → Query by capability

### 7.4 Performance Benchmarks

**MUST establish baseline performance**:

```python
# tests/performance/test_parser_benchmarks.py

def test_parser_performance(benchmark_fixture):
    """Benchmark Python parser on real files."""

    test_cases = [
        ("small.py", 100, 100),    # 100 lines, max 100ms
        ("medium.py", 500, 150),   # 500 lines, max 150ms
        ("large.py", 1000, 200),   # 1000 lines, max 200ms
    ]

    parser = PythonParser()

    for filename, lines, max_ms in test_cases:
        file_path = TEST_DATA / filename

        with benchmark_fixture.measure(f"parse_{lines}_lines"):
            chunks = parser.parse_file(file_path)

        benchmark_fixture.assert_performance(
            f"parse_{lines}_lines",
            max_ms=max_ms
        )

        assert len(chunks) > 0, f"No chunks parsed from {filename}"
```

### 7.5 Regression Testing

**MUST prevent regressions**:

1. **Golden File Tests**: Store expected parse outputs, compare on changes
2. **Performance Baselines**: Track performance over time, alert on >10% degradation
3. **API Compatibility**: Versioned interface tests ensure no breaking changes

---

## 8. INTER-PHASE DEPENDENCIES

### 8.1 What Phase 2 (SOAR Pipeline) Depends On

**From Phase 1, Phase 2 requires**:

| Component | Interface | Stability |
|-----------|-----------|-----------|
| **Storage Layer** | `Store.save_chunk()`, `Store.get_chunk()`, `Store.retrieve_by_activation()` | STABLE - no breaking changes |
| **CodeChunk** | `to_json()`, `from_json()`, `validate()` | STABLE - schema frozen |
| **ReasoningChunk** | JSON schema defined (stub implementation OK) | SCHEMA STABLE - implementation in Phase 2 |
| **ContextProvider** | `retrieve()`, `update()` | STABLE - interface frozen |
| **AgentRegistry** | `list_agents()`, `get_agent()`, `find_by_capability()` | STABLE - interface frozen |
| **Config** | `load()`, `get()`, `llm_config()` | STABLE - keys may be added, not removed |

**Guaranteed Contracts**:
- Storage writes are atomic (transaction support)
- Chunk IDs are unique and stable (same file + function = same ID)
- Agent registry returns consistent results (no random order)
- Configuration loading is deterministic (same inputs → same output)

### 8.2 What Phase 3 (Advanced Memory) Depends On

**From Phase 1+2, Phase 3 requires**:

| Component | What Phase 3 Needs |
|-----------|-------------------|
| **Activation System** | Phase 1 provides storage schema, Phase 3 implements ACT-R formulas |
| **Spreading Activation** | Phase 1 provides `relationships` table, Phase 3 implements traversal |
| **Learning Updates** | Phase 1 provides `update_activation()` API, Phase 3 implements logic |

### 8.3 Versioning Strategy

**Semantic Versioning** (`MAJOR.MINOR.PATCH`):

- **MAJOR**: Breaking changes to public interfaces
  - Example: Changing `Store.save_chunk()` signature
  - Requires: Migration guide, deprecation notices

- **MINOR**: New features, backward-compatible changes
  - Example: Adding new method to `Store` interface
  - Requires: Documentation update

- **PATCH**: Bug fixes, no interface changes
  - Example: Fixing parser edge case
  - Requires: Changelog entry

**Phase 1 Versioning**:
- Released as `v1.0.0` when all quality gates pass
- Interfaces locked after `v1.0.0` (breaking changes require `v2.0.0`)
- Phase 2 development starts from `v1.0.0` tag

---

## 9. NON-GOALS (OUT OF SCOPE)

### 9.1 Explicitly NOT in Phase 1

| Feature | Why Not Now | When |
|---------|-------------|------|
| **SOAR Orchestration** | Requires working foundation first | Phase 2 |
| **Verification System** | LLM-based verification needs SOAR pipeline | Phase 2 |
| **ACT-R Activation** | Complex logic, foundation first | Phase 3 |
| **Multi-language Parsing** | Python proves concept, expand later | Phase 1.5+ |
| **Distributed Storage** | SQLite sufficient for MVP | Post-MVP |
| **UI/Dashboard** | CLI focus for MVP | Post-MVP |
| **Cloud Sync** | Local-first for MVP | Post-MVP |
| **Enterprise Features** | Individual developers first | Post-MVP |

### 9.2 Technical Constraints (Accepted for Phase 1)

- **No vector embeddings**: Keyword matching for context retrieval (simple, fast)
- **No semantic search**: Basic string matching acceptable
- **No performance optimization**: Meet targets, don't over-optimize
- **No caching strategies**: Simple cache invalidation (mtime check)
- **No distributed locking**: Single-user/single-process assumption

---

## 10. TECHNICAL CONSIDERATIONS

### 10.1 Error Handling Philosophy

**Three Error Categories**:

1. **Validation Errors** (user-fixable)
   - Invalid configuration
   - Malformed agent config
   - **Response**: Clear error message with fix suggestion
   - **Example**: `ConfigurationError: Invalid LLM provider 'foo'. Valid: ['anthropic', 'openai', 'ollama']`

2. **System Errors** (transient, retry-able)
   - Network timeouts
   - Database lock contention
   - **Response**: Log warning, retry with exponential backoff (max 3 attempts)
   - **Example**: SQLite locked → wait 100ms → retry

3. **Fatal Errors** (unrecoverable)
   - Corrupted database
   - Out of disk space
   - **Response**: Log error, fail fast with actionable message
   - **Example**: `FatalError: Storage corrupted. Backup ~/.aurora/memory.db and run 'aurora init --reset'`

**Error Propagation**:
- Use custom exceptions: `AuroraError` (base), `StorageError`, `ParseError`, `ConfigurationError`
- Don't catch generic `Exception` (let bugs surface)
- Log stack traces for system/fatal errors
- User-facing errors: friendly message only (no stack trace)

### 10.2 Observability & Debugging

**Logging Strategy**:

| Level | When to Use | Example |
|-------|-------------|---------|
| **DEBUG** | Internal state changes | "Parsed 15 chunks from auth.py" |
| **INFO** | User-visible operations | "Initialized storage at ~/.aurora/memory.db" |
| **WARN** | Recoverable issues | "Cache miss for chunk code:foo.py:bar, parsing fresh" |
| **ERROR** | Operation failures | "Failed to parse broken.py: SyntaxError at line 42" |

**Structured Logging** (JSON in log files):
```json
{
  "timestamp": "2025-12-20T14:30:00.123Z",
  "level": "INFO",
  "component": "PythonParser",
  "operation": "parse_file",
  "file": "/path/to/auth.py",
  "duration_ms": 145,
  "chunks_extracted": 8
}
```

**Debug Mode** (`AURORA_DEBUG=1`):
- Enable verbose logging (DEBUG level)
- Print SQL queries
- Disable caching (always parse fresh)
- Log timing for each operation

**Tracing** (Phase 1 - basic):
- Log operation start/end with correlation ID
- Format: `[req-uuid-123] Operation: parse_file started`
- Enables tracing single request through all components

### 10.3 Configuration Management Details

**Secrets Management**:
- API keys: NEVER in config files, always from environment variables
- Config specifies env var name: `"api_key_env": "ANTHROPIC_API_KEY"`
- Validation: Error if required env var missing

**Schema Evolution**:
- Config version number: `"version": "1.0"`
- Parser checks version, applies migrations if needed
- Unknown fields: Log warning, ignore (forward compatibility)
- Missing required fields: Error with default suggestion

**Multi-Environment Support**:
- Use `AURORA_ENV` to select config: `config.{env}.json`
- Example: `AURORA_ENV=test` loads `config.test.json`
- Default: `config.json` (production)

### 10.4 Performance Considerations

**SQLite Optimizations**:
```python
# Connection settings for performance
conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
conn.execute("PRAGMA cache_size=10000")  # 10MB cache
conn.execute("PRAGMA temp_store=MEMORY")  # In-memory temp tables
```

**Caching Strategy**:
- Parse results cached until source file mtime changes
- Activation values cached in memory (refresh every 100 retrievals)
- Config cached on load (reload on SIGHUP)

**Lazy Loading**:
- Don't parse all files on startup
- Parse on-demand (first query for a file)
- Background indexing (optional, Phase 2+)

### 10.5 Security Considerations

**Input Validation**:
- Validate all file paths (no path traversal: `../../../etc/passwd`)
- Sanitize chunk IDs (alphanumeric + `:-._` only)
- SQL injection: Use parameterized queries ALWAYS

**Dependency Security**:
- Pin direct dependencies with `==` (not `>=`)
- Run `pip-audit` in CI for known vulnerabilities
- Update tree-sitter if security patches released

**Secrets Handling**:
- API keys from environment only (never log)
- Don't store API keys in SQLite
- Mask secrets in logs: `api_key=***` (not full key)

---

## 11. DELIVERY VERIFICATION CHECKLIST

**Phase 1 is complete when ALL items checked**:

### 11.1 Implementation Complete
- [ ] All functional requirements implemented (Section 4)
- [ ] All quality gates passed (Section 6.1)
- [ ] All acceptance tests pass (Section 6.3)
- [ ] Performance benchmarks met (Section 6.2)
- [ ] No known critical bugs (P0/P1)

### 11.2 Testing Complete
- [ ] Unit test coverage ≥85% for core packages
- [ ] All integration tests pass
- [ ] Performance benchmarks run and recorded
- [ ] Regression test suite established
- [ ] Test framework documented with examples

### 11.3 Documentation Complete
- [ ] All public APIs documented (docstrings)
- [ ] README with quick start guide
- [ ] Architecture documentation (Section 5)
- [ ] Extension guide (custom parsers, storage)
- [ ] Troubleshooting guide (common errors)

### 11.4 Phase 2 Readiness
- [ ] Inter-phase dependency contracts documented (Section 8.1)
- [ ] Stable interface versions tagged (`v1.0.0`)
- [ ] Breaking change policy defined (Section 8.3)
- [ ] Migration examples for Phase 2 developers

### 11.5 Quality Assurance
- [ ] Code review completed (2+ reviewers)
- [ ] Security audit passed (bandit, pip-audit)
- [ ] Performance profiling completed (no bottlenecks)
- [ ] Memory leak testing passed (valgrind/memray)
- [ ] Type checking clean (mypy strict mode)

### 11.6 Deployment Ready
- [ ] Package builds successfully (`pip install -e .`)
- [ ] All dependencies pinned and audited
- [ ] CI/CD pipeline configured (GitHub Actions)
- [ ] Release notes drafted
- [ ] Git tag created: `v1.0.0-phase1`

---

## 12. OPEN QUESTIONS

### 12.1 Design Decisions (Requires Input)

1. **Parser Complexity Calculation**
   - **Question**: Should we use basic cyclomatic complexity (count branches) or more sophisticated metrics (Halstead, Maintainability Index)?
   - **Impact**: Affects CodeChunk schema and performance
   - **Recommendation**: Start simple (branch count), expand in Phase 2 if needed

2. **Cache Invalidation Strategy**
   - **Question**: Should cache invalidation be immediate (on mtime change) or lazy (on next query)?
   - **Impact**: Performance vs freshness tradeoff
   - **Recommendation**: Lazy (check mtime on retrieval), less I/O overhead

3. **Agent Registry Refresh Policy**
   - **Question**: Should registry auto-refresh on file changes (inotify) or periodic (every N hours)?
   - **Impact**: Responsiveness vs system resource usage
   - **Recommendation**: Periodic (configurable interval), manual refresh available

### 12.2 Performance Tradeoffs

1. **SQLite vs In-Memory for Testing**
   - **Question**: Should integration tests use SQLite or MemoryStore?
   - **Tradeoff**: SQLite = realistic, slower; Memory = fast, less realistic
   - **Recommendation**: Both - quick tests use Memory, thorough tests use SQLite

2. **Parser Caching Granularity**
   - **Question**: Cache entire file parse result or per-function chunks?
   - **Tradeoff**: Coarse = faster storage, fine = more flexible retrieval
   - **Recommendation**: Per-function (fine-grained), enables partial updates

### 12.3 Future Phase Considerations

1. **Activation Storage**
   - **Question**: Should Phase 1 create `activations` table even though Phase 3 uses it?
   - **Answer**: YES - create schema now, Phase 3 implements logic (avoid migration)

2. **ReasoningChunk Implementation**
   - **Question**: Should Phase 1 implement basic ReasoningChunk or just stub?
   - **Answer**: Stub + schema only (Phase 2 implements when SOAR pipeline exists)

3. **Context Provider Extensibility**
   - **Question**: Should Phase 1 support multiple context providers simultaneously?
   - **Answer**: Design interface for multiple, implement single (CodeContextProvider)

---

## APPENDIX A: SAMPLE CODE STRUCTURES

### A.1 Chunk ID Format Specification

**Format**: `{type}:{identifier}`

**Examples**:
```
code:src/auth.py:login:45-78
code:utils/helpers.py:format_date:12-25
reas:oauth-impl-20251213-143215
reas:payment-flow-v3
know:stripe-api:charges:create
```

**Rules**:
- Type prefix: `code:`, `reas:`, `know:`
- Identifier: File path + function name + line range (for code)
- No spaces, use hyphens for separators
- Case-sensitive (preserve file case)
- Max length: 255 characters

### A.2 Configuration File Examples

**Minimal Config** (`~/.aurora/config.json`):
```json
{
  "version": "1.0",
  "mode": "standalone",
  "storage": {
    "type": "sqlite",
    "path": "~/.aurora/memory.db"
  },
  "llm": {
    "reasoning_provider": "anthropic",
    "api_key_env": "ANTHROPIC_API_KEY"
  }
}
```

**Full Config** (see spec Appendix C for complete schema)

### A.3 Agent Registry Config

**Example** (`~/.aurora/agents.json`):
```json
{
  "agents": [
    {
      "id": "code-developer",
      "type": "mcp",
      "path": "~/.claude/agents/code-developer",
      "capabilities": ["code_implementation", "debugging", "refactoring"],
      "domains": ["python", "typescript"],
      "availability": "always"
    },
    {
      "id": "research-agent",
      "type": "executable",
      "path": "/usr/local/bin/research-agent",
      "capabilities": ["web_search", "documentation_lookup"],
      "domains": ["general"],
      "availability": "always"
    },
    {
      "id": "remote-analyzer",
      "type": "http",
      "endpoint": "https://api.example.com/analyze",
      "capabilities": ["code_analysis", "security_audit"],
      "domains": ["python", "javascript"],
      "availability": "depends_on_network"
    }
  ]
}
```

---

## APPENDIX B: TEST DATA REQUIREMENTS

### B.1 Sample Python Files for Testing

**Create these test files** in `tests/fixtures/`:

1. **simple.py** (100 lines, 3 functions, no classes)
   - Test basic parsing
   - Verify function extraction
   - Check docstring parsing

2. **medium.py** (500 lines, 10 functions, 3 classes)
   - Test class/method parsing
   - Verify dependency extraction
   - Check complexity calculation

3. **complex.py** (1000 lines, 20 functions, 5 classes, nested structures)
   - Test performance at scale
   - Verify nested class handling
   - Check edge cases (decorators, async, etc.)

4. **broken.py** (syntax errors)
   - Test error handling
   - Verify graceful failure
   - Check error messages

### B.2 Performance Test Datasets

**Generate synthetic test data**:
- 10 files × 100 functions each = 1,000 chunks (small)
- 100 files × 100 functions each = 10,000 chunks (large)
- Measure: parse time, storage time, retrieval time

---

## APPENDIX C: GLOSSARY

| Term | Definition |
|------|------------|
| **Chunk** | Atomic unit of retrievable context (function, class, reasoning pattern) |
| **CodeChunk** | Chunk representing parsed code element |
| **ReasoningChunk** | Chunk representing reasoning pattern (Phase 2+) |
| **Activation** | Numeric score determining retrieval priority (Phase 3) |
| **Context Provider** | Component that retrieves relevant chunks for a query |
| **Parser** | Component that extracts code chunks from source files |
| **Store** | Persistent storage layer (SQLite) |
| **Agent Registry** | Discovery and management of available agents |
| **cAST** | Code Abstract Syntax Tree (tree-sitter based) |
| **MCP** | Model Context Protocol (agent integration standard) |

---

## DOCUMENT HISTORY

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-20 | Initial PRD for Phase 1 Foundation | Product Team |

---

**END OF PRD 0002: AURORA Foundation & Infrastructure**
