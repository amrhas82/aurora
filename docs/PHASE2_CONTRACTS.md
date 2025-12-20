# Phase 2 Dependency Contracts

This document defines the stable interfaces, contracts, and extension points that Phase 2 (SOAR Pipeline) developers can rely on from Phase 1 (Foundation).

**Document Version**: 1.0
**Phase 1 Version**: v1.0.0-phase1
**Last Updated**: December 20, 2025

---

## Table of Contents

- [Guaranteed Stable Interfaces](#guaranteed-stable-interfaces)
- [Storage Layer Contract](#storage-layer-contract)
- [Chunk System Contract](#chunk-system-contract)
- [Context Provider Contract](#context-provider-contract)
- [Parser System Contract](#parser-system-contract)
- [Configuration System Contract](#configuration-system-contract)
- [Agent Registry Contract](#agent-registry-contract)
- [Testing Utilities Contract](#testing-utilities-contract)
- [Extension Points for Phase 2](#extension-points-for-phase-2)
- [Breaking Change Policy](#breaking-change-policy)

---

## Guaranteed Stable Interfaces

The following interfaces are **guaranteed stable** for Phase 2. Any changes to these will be accompanied by deprecation warnings and migration guides.

### Core Stable Interfaces

```python
# Storage Layer
aurora_core.store.base.Store
aurora_core.store.SQLiteStore
aurora_core.store.MemoryStore

# Chunk System
aurora_core.chunks.base.Chunk
aurora_core.chunks.CodeChunk
aurora_core.chunks.ReasoningChunk  # Stub for Phase 2 to complete

# Context Management
aurora_core.context.provider.ContextProvider
aurora_core.context.CodeContextProvider

# Configuration
aurora_core.config.Config
aurora_core.config.loader.ConfigLoader
aurora_core.config.schema.get_schema

# Types and Exceptions
aurora_core.types.ChunkID
aurora_core.types.Activation
aurora_core.exceptions.*  # All exception classes

# Parser System
aurora_context_code.parser.CodeParser
aurora_context_code.registry.ParserRegistry
aurora_context_code.languages.python.PythonParser

# Agent Registry
aurora_soar.agent_registry.AgentInfo
aurora_soar.agent_registry.AgentRegistry

# Testing Framework
aurora_testing.fixtures.*  # All fixtures
aurora_testing.mocks.*     # All mock classes
aurora_testing.benchmarks.*  # Performance utilities
```

---

## Storage Layer Contract

### Store Interface Guarantees

Phase 2 can rely on these `Store` interface methods remaining stable:

```python
from aurora_core.store.base import Store
from aurora_core.chunks import Chunk
from aurora_core.types import ChunkID, Activation

class Store(ABC):
    """Abstract storage interface - STABLE API"""

    @abstractmethod
    def save_chunk(self, chunk: Chunk) -> None:
        """Save or update a chunk.

        CONTRACT:
        - Must be idempotent (multiple saves of same chunk_id allowed)
        - Must preserve all chunk metadata
        - Must update last_modified timestamp
        - Must raise StorageError on failure
        """

    @abstractmethod
    def get_chunk(self, chunk_id: ChunkID) -> Optional[Chunk]:
        """Retrieve a chunk by ID.

        CONTRACT:
        - Returns None if chunk not found (never raises KeyError)
        - Returns exact chunk with all metadata preserved
        - Must be fast (<50ms for SQLite, <10ms for in-memory)
        """

    @abstractmethod
    def list_chunks(
        self,
        chunk_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Chunk]:
        """List chunks with optional filtering.

        CONTRACT:
        - Default limit=100 if not specified
        - chunk_type filter is optional (None = all types)
        - Must support pagination via offset
        - Results ordered by last_accessed DESC
        - Empty list if no results (never raises)
        """

    @abstractmethod
    def delete_chunk(self, chunk_id: ChunkID) -> bool:
        """Delete a chunk.

        CONTRACT:
        - Returns True if deleted, False if not found
        - Must cascade delete related data (activations, relationships)
        - Must never raise on non-existent chunk
        """

    @abstractmethod
    def update_activation(self, chunk_id: ChunkID) -> None:
        """Update chunk activation (usage tracking).

        CONTRACT:
        - Increments access_count
        - Updates last_accessed timestamp
        - Creates activation record if chunk exists
        - Raises StorageError if chunk doesn't exist
        """

    @abstractmethod
    def get_activation(self, chunk_id: ChunkID) -> Optional[Activation]:
        """Get activation metrics.

        CONTRACT:
        - Returns Activation with last_accessed and access_count
        - Returns None if chunk not found or never accessed
        - Never raises KeyError
        """
```

### Storage Performance Guarantees

Phase 2 can expect these performance characteristics:

| Operation | SQLiteStore | MemoryStore |
|-----------|-------------|-------------|
| `save_chunk()` | <50ms | <1ms |
| `get_chunk()` | <50ms | <1ms |
| `list_chunks(limit=100)` | <100ms | <10ms |
| `delete_chunk()` | <50ms | <1ms |
| `update_activation()` | <20ms | <1ms |
| Cold start | <200ms | <10ms |

### Database Schema Stability

The SQLite schema is **stable** for Phase 1. Phase 2 can add new tables but must not modify these:

```sql
-- STABLE SCHEMA (v1.0)
CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    chunk_type TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    metadata TEXT,  -- JSON
    created_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL,
    access_count INTEGER DEFAULT 0
);

CREATE INDEX idx_chunk_type ON chunks(chunk_type);
CREATE INDEX idx_file_path ON chunks(json_extract(metadata, '$.file_path'));
```

**Phase 2 Migration Path**: If Phase 2 needs schema changes:
1. Create new tables (e.g., `reasoning_links`, `soar_productions`)
2. Use `metadata` JSON field for lightweight extensions
3. For major changes, request Phase 1.1 schema migration

---

## Chunk System Contract

### Chunk Base Class Contract

```python
from aurora_core.chunks.base import Chunk

class Chunk(ABC):
    """Abstract chunk base class - STABLE API"""

    def __init__(
        self,
        content: str,
        chunk_type: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_id: Optional[ChunkID] = None
    ):
        """Initialize chunk.

        CONTRACT:
        - chunk_id auto-generated if not provided (stable UUID4)
        - metadata defaults to empty dict (never None)
        - content and chunk_type are required
        - start_line/end_line optional (None for non-file chunks)
        """

    @abstractmethod
    def validate(self) -> None:
        """Validate chunk data.

        CONTRACT:
        - Raises ValidationError with descriptive message
        - Never modifies chunk data (validation is read-only)
        - Called automatically before saving to store
        """

    def to_json(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict.

        CONTRACT:
        - Returns dict with keys: chunk_id, content, chunk_type,
          start_line, end_line, metadata
        - Output is JSON-serializable (no custom objects)
        - Includes all data needed for from_json reconstruction
        """

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Chunk":
        """Deserialize from JSON dict.

        CONTRACT:
        - Inverse of to_json (round-trip guaranteed)
        - Validates data during reconstruction
        - Returns appropriate subclass (CodeChunk, ReasoningChunk)
        """
```

### CodeChunk Contract

```python
from aurora_core.chunks import CodeChunk

class CodeChunk(Chunk):
    """Code chunk implementation - STABLE API"""

    chunk_type = "code"  # CONSTANT

    # Guaranteed metadata fields (Phase 2 can add more):
    # - name: str (function/class/method name)
    # - signature: str (full signature with types)
    # - language: str (e.g., "python", "javascript")
    # - file_path: str (absolute path)
    # - complexity: int (cyclomatic complexity, 1-100+)
    # - docstring: Optional[str] (if present)
    # - dependencies: List[str] (imports, calls)
```

### ReasoningChunk Contract (Phase 2 Implementation)

Phase 1 provides a **stub** that Phase 2 must complete:

```python
from aurora_core.chunks import ReasoningChunk

class ReasoningChunk(Chunk):
    """Reasoning chunk - PHASE 2 TO IMPLEMENT

    CONTRACT for Phase 2:
    - Must set chunk_type = "reasoning"
    - Must implement validate() method
    - Suggested metadata fields:
      - goal: str (reasoning goal)
      - premises: List[str] (input facts)
      - conclusion: str (derived result)
      - confidence: float (0.0-1.0)
      - reasoning_type: str (deductive, inductive, abductive)
      - source_chunk_ids: List[ChunkID] (provenance)
    """

    chunk_type = "reasoning"

    def validate(self) -> None:
        """PHASE 2: Implement validation logic."""
        raise NotImplementedError("Phase 2 must implement")
```

**Phase 2 Requirements**:
1. Complete `ReasoningChunk.validate()` implementation
2. Define required metadata schema
3. Add serialization helpers if needed
4. Write comprehensive tests

---

## Context Provider Contract

### ContextProvider Interface

```python
from aurora_core.context.provider import ContextProvider

class ContextProvider(ABC):
    """Abstract context provider - STABLE API"""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        max_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Retrieve relevant chunks.

        CONTRACT:
        - Returns up to max_results chunks
        - Results ordered by relevance (descending)
        - Adds '_score' to chunk.metadata (0.0-1.0)
        - Empty list if no results (never None)
        - filters applied before scoring (exact match)

        PERFORMANCE:
        - Must complete in <500ms for 10K chunk database
        - Must support caching for repeated queries
        """

    @abstractmethod
    def update(self, chunk_id: ChunkID) -> None:
        """Track chunk usage.

        CONTRACT:
        - Updates activation in store
        - May update internal caches
        - Never raises if chunk not found (silent fail)
        """

    @abstractmethod
    def refresh(self) -> None:
        """Invalidate caches.

        CONTRACT:
        - Clears all internal caches
        - Re-scans data sources if applicable
        - Next retrieve() will rebuild cache
        """
```

### CodeContextProvider Contract

```python
from aurora_core.context import CodeContextProvider

# GUARANTEED BEHAVIOR:
# 1. Keyword-based scoring (case-insensitive)
# 2. Score = (matching_keywords / total_keywords)
# 3. File modification time-based cache invalidation
# 4. Integration with ParserRegistry for multi-language support

# Phase 2 can extend by:
# - Implementing SemanticContextProvider with embeddings
# - Implementing ReasoningContextProvider for logic chains
# - Custom scoring algorithms (inherit and override _score_chunk)
```

---

## Parser System Contract

### CodeParser Interface

```python
from aurora_context_code.parser import CodeParser

class CodeParser(ABC):
    """Abstract parser interface - STABLE API"""

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Check if parser handles this file.

        CONTRACT:
        - Must be fast (<1ms)
        - Based on file extension or content sniffing
        - Returns boolean (never raises)
        """

    @abstractmethod
    def parse(self, content: str, file_path: str) -> List[CodeChunk]:
        """Parse content into chunks.

        CONTRACT:
        - Returns list of CodeChunk objects
        - Empty list if no parseable structures (never None)
        - Each chunk has valid metadata (name, language, complexity)
        - Raises ParseError on fatal errors (syntax errors logged but don't raise)

        PERFORMANCE:
        - Must complete in <1000ms for 1000-line file
        - Should cache AST parsing results when possible
        """
```

### ParserRegistry Contract

```python
from aurora_context_code.registry import ParserRegistry

registry = ParserRegistry()

# GUARANTEED METHODS:
# - register(parser: CodeParser) -> None
# - get_parser(file_path: str) -> Optional[CodeParser]
# - list_parsers() -> List[str]  # Returns language names

# BEHAVIOR:
# - Parsers auto-registered on import
# - First registered parser for extension wins
# - Thread-safe registration
```

---

## Configuration System Contract

### Config Class Contract

```python
from aurora_core.config import Config

class Config:
    """Configuration loader - STABLE API"""

    @staticmethod
    def load(
        config_files: Optional[List[str]] = None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ) -> Config:
        """Load configuration with override hierarchy.

        CONTRACT:
        Override precedence (highest to lowest):
        1. cli_overrides parameter
        2. Environment variables (AURORA_*)
        3. config_files (last file wins)
        4. Built-in defaults

        VALIDATION:
        - Validates against JSON schema
        - Raises ConfigurationError with clear message
        - Expands ~ in paths to home directory
        """

    def get_string(self, key: str, default: Optional[str] = None) -> str:
        """Get string value. Raises ConfigurationError if not found and no default."""

    def get_int(self, key: str, default: Optional[int] = None) -> int:
        """Get integer value. Raises ConfigurationError if not found and no default."""

    def get_bool(self, key: str, default: Optional[bool] = None) -> bool:
        """Get boolean value. Raises ConfigurationError if not found and no default."""

    def get_dict(self, key: str, default: Optional[Dict] = None) -> Dict[str, Any]:
        """Get nested dict. Raises ConfigurationError if not found and no default."""

    # Additional methods in implementation (see source)
```

### Configuration Schema Stability

**Guaranteed config keys** (Phase 2 can rely on these):

```json
{
  "storage": {
    "path": "string (file path)",
    "timeout": "number (seconds)",
    "pool_size": "integer"
  },
  "parser": {
    "languages": "array of strings",
    "cache_ttl": "integer (seconds)",
    "max_file_size": "integer (bytes)"
  },
  "logging": {
    "level": "string (DEBUG, INFO, WARNING, ERROR)",
    "format": "string (log format)",
    "output": "string (file path or 'stdout')"
  }
}
```

**Phase 2 can add** (without breaking Phase 1):
- New top-level sections: `"soar": {...}`, `"reasoning": {...}`
- New keys in existing sections (use prefix): `"parser.reasoning_mode"`

---

## Agent Registry Contract

### AgentRegistry Contract

```python
from aurora_soar import AgentRegistry, AgentInfo

class AgentRegistry:
    """Agent registry - STABLE API"""

    def __init__(self, discovery_paths: Optional[List[str]] = None):
        """Initialize registry.

        CONTRACT:
        - Scans discovery_paths for agent JSON configs
        - Default paths: ./config/agents, ~/.aurora/agents, /etc/aurora/agents
        - Validates agent configs on load
        - Creates fallback agent if none found
        """

    def list_agents(self) -> List[AgentInfo]:
        """List all registered agents. Always returns list (never None)."""

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent by ID. Returns None if not found."""

    def find_by_capability(self, capability: str) -> List[AgentInfo]:
        """Find agents with specific capability. Returns empty list if none."""

    def get_agent_for_domain(self, domain: str) -> Optional[AgentInfo]:
        """Get best agent for domain (e.g., 'python'). Returns None if none."""

    def refresh(self) -> None:
        """Rescan config files. Reloads all agent definitions."""
```

### AgentInfo Dataclass Contract

```python
@dataclass
class AgentInfo:
    """Agent metadata - STABLE SCHEMA"""

    id: str              # Unique identifier
    name: str            # Display name
    agent_type: str      # "local" or "remote"
    capabilities: List[str]  # e.g., ["code-generation", "reasoning"]
    domains: List[str]   # e.g., ["python", "general"]
    path: Optional[str]  # For local agents
    endpoint: Optional[str]  # For remote agents
    metadata: Dict[str, Any]  # Flexible extension point

    # Phase 2 can add new capabilities without breaking Phase 1:
    # capabilities = ["reasoning", "goal-selection", "impasse-resolution"]
```

---

## Testing Utilities Contract

### Pytest Fixtures (Stable)

```python
# Available fixtures for Phase 2 tests:
from aurora_testing import (
    # Store fixtures
    sqlite_store,    # Temporary SQLite store
    memory_store,    # In-memory store
    sample_store,    # Store pre-populated with test data

    # Chunk fixtures
    sample_code_chunk,       # Simple function chunk
    sample_complex_chunk,    # High complexity chunk
    sample_chunks,           # List of various chunks

    # Parser fixtures
    python_parser,           # PythonParser instance
    parser_registry,         # ParserRegistry with Python
    sample_python_file,      # Temporary .py file

    # Config fixtures
    default_config,          # Config with defaults
    custom_config,           # Config with test overrides
    temp_config_file,        # Temporary config JSON file

    # Agent fixtures
    sample_agent_info,       # AgentInfo instance
    agent_registry,          # AgentRegistry with test agents
)
```

### Mock Classes (Stable)

```python
from aurora_testing.mocks import (
    MockLLM,        # Rule-based LLM for deterministic testing
    MockAgent,      # Agent with configurable responses
    MockParser,     # Parser for custom test languages
    MockStore,      # Store with controllable behavior
)

# Example usage:
mock_llm = MockLLM()
mock_llm.add_rule("explain this code", "This code does X")
response = mock_llm.generate("explain this code")
assert response == "This code does X"
```

### Performance Benchmarking (Stable)

```python
from aurora_testing.benchmarks import (
    PerformanceBenchmark,  # Context manager for timing
    MemoryProfiler,        # Memory usage tracking
    BenchmarkSuite,        # Collection of benchmarks
)

# Example usage:
with PerformanceBenchmark("operation") as bench:
    # Your code here
    result = expensive_operation()

assert bench.duration_ms < 100  # Assert performance target
```

---

## Extension Points for Phase 2

Phase 2 developers should implement these components:

### 1. ReasoningChunk Implementation

```python
# Location: packages/core/src/aurora_core/chunks/reasoning_chunk.py

class ReasoningChunk(Chunk):
    """Complete the stub implementation from Phase 1."""

    chunk_type = "reasoning"

    def validate(self) -> None:
        # Implement validation for reasoning data
        pass

    # Add Phase 2-specific methods:
    # - link_to_source(chunk_id: ChunkID)
    # - get_provenance() -> List[ChunkID]
    # - evaluate_confidence() -> float
```

### 2. SOAR Production System

```python
# Location: packages/soar/src/aurora_soar/productions.py

class Production:
    """SOAR production rule."""
    pass

class ProductionMemory:
    """Storage for production rules."""
    pass
```

### 3. Working Memory

```python
# Location: packages/soar/src/aurora_soar/working_memory.py

class WorkingMemory:
    """SOAR working memory (short-term context)."""

    def __init__(self, store: Store):
        self.store = store  # Use Phase 1 store

    def get_active_chunks(self) -> List[Chunk]:
        """Get chunks in working memory (high activation)."""
        pass
```

### 4. Reasoning Context Provider

```python
# Location: packages/core/src/aurora_core/context/reasoning_provider.py

from aurora_core.context.provider import ContextProvider

class ReasoningContextProvider(ContextProvider):
    """Context provider for reasoning chains."""

    def retrieve(
        self,
        query: str,
        max_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Retrieve reasoning chunks with inference."""
        pass
```

---

## Breaking Change Policy

### Versioning

Phase 1 follows semantic versioning:
- **Major version** (v2.0.0): Breaking changes to stable APIs
- **Minor version** (v1.1.0): New features, backward compatible
- **Patch version** (v1.0.1): Bug fixes, backward compatible

### Deprecation Process

If Phase 2 requires changes to stable interfaces:

1. **Phase 1.x**: Mark old API as deprecated with warning
   ```python
   import warnings
   warnings.warn("Method X deprecated, use Y instead", DeprecationWarning)
   ```

2. **Wait 1 minor version**: Allow migration period

3. **Phase 1.(x+2)**: Remove deprecated API with migration guide

### Compatibility Testing

Phase 2 must include compatibility tests:

```python
def test_phase1_store_contract():
    """Verify Phase 1 Store contract still works."""
    from aurora_core.store import SQLiteStore
    from aurora_core.chunks import CodeChunk

    store = SQLiteStore(":memory:")
    chunk = CodeChunk(content="test", chunk_type="code")

    # Phase 1 contract
    store.save_chunk(chunk)
    retrieved = store.get_chunk(chunk.chunk_id)
    assert retrieved.content == "test"
```

---

## Migration Support

### Phase 1.0 → Phase 2.0 Migration

Phase 2 deliverables should include:

1. **Migration Guide**: Document for upgrading from Phase 1
2. **Compatibility Shim**: Temporary adapters for deprecated APIs
3. **Migration Script**: Automated tool for schema/data migration
4. **Test Suite**: Verify Phase 1 functionality still works

Example migration script structure:
```python
# scripts/migrate_phase1_to_phase2.py

def migrate_database(db_path: str):
    """Migrate Phase 1 database to Phase 2 schema."""
    # Add new tables (reasoning_links, productions)
    # Preserve existing chunks table
    # Add migration metadata
    pass

def migrate_config(config_path: str):
    """Migrate Phase 1 config to Phase 2 format."""
    # Add SOAR configuration section
    # Preserve existing settings
    pass
```

---

## Contact & Support

For questions about Phase 1 contracts:

1. **Documentation**: See [README](../README.md), [Extension Guide](EXTENSION_GUIDE.md)
2. **Issues**: Open GitHub issue with tag `phase-2-contract`
3. **Discussion**: Use GitHub Discussions for design questions

**Contract Review Process**:
- Phase 2 developers should review this document before starting
- Propose contract changes via RFC (Request for Comments)
- Breaking changes require Phase 1 maintainer approval

---

**End of Phase 2 Dependency Contracts v1.0**
