# AURORA Phase 2 Migration Guide

**Version**: 1.0.0
**Target Audience**: Phase 2 (SOAR Pipeline) Developers
**Phase 1 Release**: v1.0.0-phase1
**Last Updated**: December 20, 2025

---

## Overview

This guide helps Phase 2 developers integrate with the stable Phase 1 foundation. It covers:
- How to consume Phase 1 interfaces
- Extending with custom implementations
- Integration patterns and best practices
- Common pitfalls and solutions

**Prerequisites**: Familiarity with Python 3.10+, async programming, and AURORA architecture.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Stable Interfaces](#stable-interfaces)
3. [Storage Integration](#storage-integration)
4. [Parser Integration](#parser-integration)
5. [Context Provider Integration](#context-provider-integration)
6. [Agent Registry Integration](#agent-registry-integration)
7. [Configuration Integration](#configuration-integration)
8. [Testing with Phase 1](#testing-with-phase-1)
9. [Common Patterns](#common-patterns)
10. [Migration Checklist](#migration-checklist)
11. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

Phase 1 packages are available as a monorepo:

```bash
# Clone the repository
git clone <repository-url>
cd aurora

# Check out the Phase 1 stable release
git checkout v1.0.0-phase1

# Install in editable mode for development
pip install -e .
```

### Verify Installation

```python
# Test imports
from aurora_core.store import SQLiteStore
from aurora_core.chunks import CodeChunk
from aurora_core.context import CodeContextProvider
from aurora_soar import AgentRegistry
from aurora_core.config import Config

print("✓ Phase 1 components imported successfully")
```

### First Integration

```python
# Example: Store and retrieve a reasoning chunk (Phase 2 implementation)
from pathlib import Path
from aurora_core.store import SQLiteStore
from aurora_core.chunks import ReasoningChunk

# Initialize store
store = SQLiteStore("memory.db")

# Your Phase 2 ReasoningChunk implementation
reasoning_chunk = ReasoningChunk(
    chunk_id="reas:oauth-impl-20251213",
    # ... your ReasoningChunk fields
)

# Store using Phase 1 interface
store.save_chunk(reasoning_chunk)

# Retrieve
retrieved = store.get_chunk("reas:oauth-impl-20251213")
assert retrieved is not None

store.close()
```

---

## Stable Interfaces

### Interface Stability Guarantees

Phase 1 interfaces are **frozen at v1.0.0**. Breaking changes require v2.0.0.

**Stable Interfaces**:
- `Store` (7 methods)
- `Chunk` (3 abstract methods)
- `CodeParser` (2 methods)
- `ContextProvider` (2 methods)
- `AgentRegistry` (12 methods)
- `Config` (15 methods)

**Versioning Policy**:
```
MAJOR.MINOR.PATCH
  │     │      └─ Bug fixes only
  │     └──────── New backward-compatible features
  └────────────── Breaking changes (requires migration)
```

### What You Can Rely On

✅ **Safe to Depend On**:
- Method signatures won't change
- Return types won't change
- Required parameters won't be added
- Existing behavior won't break

⚠️ **May Change** (non-breaking):
- New optional parameters (with defaults)
- New methods added to interfaces
- Performance improvements
- Bug fixes

❌ **Don't Depend On**:
- Internal implementation details
- Private methods (`_method`)
- Undocumented behavior
- Module structure (import from public API only)

---

## Storage Integration

### Using the Store Interface

The `Store` interface provides CRUD operations for all chunk types.

**Basic Usage**:
```python
from pathlib import Path
from aurora_core.store import SQLiteStore
from aurora_core.chunks import CodeChunk

# Initialize
db_path = Path("~/.aurora/memory.db").expanduser()
store = SQLiteStore(str(db_path))

# Save
chunk = CodeChunk(
    chunk_id="code:main.py:main:1-10",
    file_path="/path/to/main.py",
    element_type="function",
    name="main",
    line_start=1,
    line_end=10,
    signature="def main():",
    docstring="Main entry point",
    dependencies=[],
    complexity_score=0.2,
    language="python"
)
store.save_chunk(chunk)

# Retrieve
retrieved = store.get_chunk("code:main.py:main:1-10")

# Update activation (for Phase 3 spreading activation)
store.update_activation("code:main.py:main:1-10", delta=0.5)

# Query by activation
top_chunks = store.retrieve_by_activation(min_activation=0.5, limit=10)

# Cleanup
store.close()
```

### Working with Relationships

```python
# Add relationships for spreading activation (Phase 3)
store.add_relationship(
    from_id="code:auth.py:login:10-30",
    to_id="code:db.py:query_user:45-60",
    rel_type="calls",
    weight=1.0
)

# Retrieve related chunks (BFS traversal)
related = store.get_related_chunks(
    chunk_id="code:auth.py:login:10-30",
    max_depth=2  # Two hops away
)
```

### Transaction Safety

```python
# SQLiteStore uses transactions internally
try:
    for chunk in chunks:
        store.save_chunk(chunk)  # Atomic per-chunk
except Exception as e:
    # Individual save failures don't corrupt database
    print(f"Save failed: {e}")
```

### Memory Store for Testing

```python
from aurora_core.store import MemoryStore

# Fast in-memory store for tests
def test_my_feature():
    store = MemoryStore()  # No disk I/O
    # ... your test code
    store.close()  # Cleanup (no-op for MemoryStore)
```

---

## Parser Integration

### Using Existing Parsers

```python
from pathlib import Path
from aurora_context_code.registry import get_global_registry

# Get the global parser registry
registry = get_global_registry()

# Parse a Python file
file_path = Path("src/example.py")
parser = registry.get_parser_for_file(file_path)

if parser:
    chunks = parser.parse(file_path)
    for chunk in chunks:
        print(f"Found: {chunk.name} at lines {chunk.line_start}-{chunk.line_end}")
else:
    print(f"No parser for {file_path.suffix}")
```

### Creating Custom Parsers

```python
from pathlib import Path
from typing import List
from aurora_context_code.parser import CodeParser
from aurora_core.chunks import CodeChunk

class TypeScriptParser(CodeParser):
    """Custom TypeScript parser for Phase 2."""

    def __init__(self):
        super().__init__(language="typescript")

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix in [".ts", ".tsx"]

    def parse(self, file_path: Path) -> List[CodeChunk]:
        # Your parsing logic here
        # Return list of CodeChunk objects
        pass

# Register with global registry
from aurora_context_code.registry import get_global_registry

registry = get_global_registry()
registry.register(TypeScriptParser())
```

---

## Context Provider Integration

### Using CodeContextProvider

```python
from pathlib import Path
from aurora_core.context import CodeContextProvider
from aurora_core.store import SQLiteStore
from aurora_context_code.registry import get_global_registry

# Setup
store = SQLiteStore("memory.db")
registry = get_global_registry()
provider = CodeContextProvider(store, registry)

# Index a codebase
project_root = Path("/path/to/project")
for py_file in project_root.rglob("*.py"):
    provider.index_file(py_file)

# Query for relevant context
query = "authentication login user"
relevant_chunks = provider.retrieve(query, budget=10)

for chunk in relevant_chunks:
    print(f"Relevance: {chunk.score}")
    print(f"Function: {chunk.name}")
    print(f"File: {chunk.file_path}")

# Track usage (updates activation)
provider.update(relevant_chunks[0], success=True)

store.close()
```

### Creating Custom Context Providers

```python
from typing import List
from aurora_core.context import ContextProvider
from aurora_core.chunks import Chunk

class VectorContextProvider(ContextProvider):
    """Custom provider using embeddings (Phase 2 enhancement)."""

    def __init__(self, store, embedding_model):
        self.store = store
        self.model = embedding_model

    def retrieve(self, query: str, budget: int = 10) -> List[Chunk]:
        # 1. Generate query embedding
        query_embedding = self.model.embed(query)

        # 2. Search vector store
        # 3. Return top N results
        pass

    def update(self, chunk: Chunk, success: bool = True) -> None:
        # Track usage, update activation
        self.store.update_activation(chunk.id, delta=0.1 if success else -0.05)
```

---

## Agent Registry Integration

### Discovering Agents

```python
from pathlib import Path
from aurora_soar import AgentRegistry

# Initialize registry with discovery paths
paths = [
    Path(".aurora/agents.json"),      # Project-local
    Path("~/.aurora/agents.json"),    # User global
]
registry = AgentRegistry(paths)

# List all available agents
agents = registry.list_agents()
for agent in agents:
    print(f"Agent: {agent.id}")
    print(f"  Type: {agent.type}")
    print(f"  Capabilities: {agent.capabilities}")
    print(f"  Domains: {agent.domains}")

# Find agents by capability
coders = registry.find_by_capability("code_implementation")
print(f"Found {len(coders)} coding agents")

# Get specific agent
qa_agent = registry.get_agent("quality-assurance")
if qa_agent:
    print(f"QA agent available: {qa_agent.availability}")
```

### Agent Config Format

Create `.aurora/agents.json`:
```json
{
  "agents": [
    {
      "id": "reasoning-agent",
      "type": "local",
      "path": "/path/to/reasoning_agent",
      "capabilities": ["reasoning", "problem_decomposition"],
      "domains": ["general"],
      "availability": "always"
    }
  ]
}
```

### Refreshing Agent Discovery

```python
# Re-scan config files if they've changed
new_count = registry.refresh()
print(f"Found {new_count} new agents")
```

---

## Configuration Integration

### Loading Configuration

```python
from pathlib import Path
from aurora_core.config import Config

# Load with default hierarchy
config = Config.load(
    project_path=Path("."),
    cli_overrides={"storage.path": "/custom/memory.db"}
)

# Access config values
storage_path = config.get("storage.path")
llm_provider = config.get("llm.reasoning_provider")
log_level = config.get("logging.level", default="INFO")

# Typed accessors
storage_path = config.storage_path()  # Returns Path
llm_config = config.llm_config()      # Returns Dict[str, Any]
```

### Configuration Override Hierarchy

```
1. CLI overrides (highest priority)
   ↓
2. Environment variables (AURORA_*)
   ↓
3. Project config (.aurora/config.json)
   ↓
4. Global config (~/.aurora/config.json)
   ↓
5. Package defaults (lowest priority)
```

### Environment Variables

```bash
# Override storage location
export AURORA_STORAGE_PATH="/custom/path/memory.db"

# Override LLM provider
export AURORA_LLM_PROVIDER="openai"

# Override log level
export AURORA_LOG_LEVEL="DEBUG"
```

### Custom Configuration

```json
// .aurora/config.json
{
  "version": "1.0",
  "mode": "soar_orchestrator",  // Phase 2 mode
  "storage": {
    "type": "sqlite",
    "path": "~/.aurora/phase2_memory.db"
  },
  "soar": {
    "max_subgoals": 10,
    "verification_threshold": 0.8
  }
}
```

---

## Testing with Phase 1

### Using Test Fixtures

```python
import pytest
from aurora_testing import memory_store, temp_sqlite_store, sample_code_chunk

def test_my_phase2_feature(memory_store, sample_code_chunk):
    """Test using Phase 1 fixtures."""
    # memory_store is a clean MemoryStore
    # sample_code_chunk is a valid CodeChunk

    # Your Phase 2 logic
    memory_store.save_chunk(sample_code_chunk)

    # Assertions
    retrieved = memory_store.get_chunk(sample_code_chunk.id)
    assert retrieved is not None
```

### Mock Utilities

```python
from aurora_testing.mocks import MockLLM

def test_reasoning_with_mock_llm():
    """Test Phase 2 reasoning with predictable LLM."""
    mock_llm = MockLLM()

    # Configure expected responses
    mock_llm.set_response(
        prompt_key="decompose task",
        response='{"subgoals": ["goal1", "goal2"]}'
    )

    # Your Phase 2 code using the mock
    result = my_reasoning_function(mock_llm)

    assert len(result.subgoals) == 2
    assert mock_llm.call_count == 1
```

### Performance Benchmarking

```python
from aurora_testing.benchmarks import PerformanceBenchmark

def test_phase2_performance():
    """Benchmark Phase 2 SOAR orchestration."""
    benchmark = PerformanceBenchmark()

    with benchmark.measure("soar_orchestration"):
        # Your Phase 2 SOAR logic
        result = orchestrate_task(task)

    # Verify performance
    benchmark.assert_performance("soar_orchestration", max_ms=1000)
```

---

## Common Patterns

### Pattern 1: Parse → Store → Retrieve

```python
from pathlib import Path
from aurora_core.store import SQLiteStore
from aurora_context_code.registry import get_global_registry

def index_codebase(root_path: Path) -> SQLiteStore:
    """Index a codebase for later retrieval."""
    store = SQLiteStore("codebase.db")
    registry = get_global_registry()

    for file_path in root_path.rglob("*.py"):
        parser = registry.get_parser_for_file(file_path)
        if parser:
            chunks = parser.parse(file_path)
            for chunk in chunks:
                store.save_chunk(chunk)

    return store
```

### Pattern 2: Context-Aware Query

```python
def get_relevant_context(query: str, store: SQLiteStore) -> List[CodeChunk]:
    """Retrieve relevant code context for a query."""
    from aurora_core.context import CodeContextProvider
    from aurora_context_code.registry import get_global_registry

    provider = CodeContextProvider(store, get_global_registry())
    return provider.retrieve(query, budget=10)
```

### Pattern 3: Agent Selection

```python
def select_agent_for_task(task: str, registry: AgentRegistry):
    """Select best agent for a task."""
    # Analyze task requirements
    if "implement" in task.lower():
        agents = registry.find_by_capability("code_implementation")
    elif "debug" in task.lower():
        agents = registry.find_by_capability("debugging")
    elif "test" in task.lower():
        agents = registry.find_by_capability("testing")
    else:
        agents = registry.list_agents()

    # Return highest success rate
    return max(agents, key=lambda a: a.success_rate, default=None)
```

### Pattern 4: Configuration-Driven Behavior

```python
def initialize_soar_pipeline(config: Config):
    """Initialize SOAR pipeline from config."""
    # Get config values
    max_subgoals = config.get("soar.max_subgoals", default=10)
    verification_threshold = config.get("soar.verification_threshold", default=0.8)

    # Initialize components
    store = SQLiteStore(str(config.storage_path()))
    registry = AgentRegistry(config.get("agents.discovery_paths", default=[]))

    return SOARPipeline(
        store=store,
        registry=registry,
        max_subgoals=max_subgoals,
        verification_threshold=verification_threshold
    )
```

---

## Migration Checklist

### Phase 2 Integration Checklist

- [ ] **Install Phase 1**
  - [ ] Clone repository and checkout v1.0.0-phase1
  - [ ] Run `pip install -e .`
  - [ ] Verify imports work

- [ ] **Understand Interfaces**
  - [ ] Read `docs/PHASE2_CONTRACTS.md`
  - [ ] Review interface documentation
  - [ ] Understand stability guarantees

- [ ] **Implement ReasoningChunk**
  - [ ] Extend `Chunk` base class
  - [ ] Implement `to_json()`, `from_json()`, `validate()`
  - [ ] Follow JSON schema in PRD Section 6.3.5
  - [ ] Add tests

- [ ] **Storage Integration**
  - [ ] Use `Store` interface for all persistence
  - [ ] Test with both SQLiteStore and MemoryStore
  - [ ] Handle activation updates
  - [ ] Add relationship tracking

- [ ] **Context Integration**
  - [ ] Use `CodeContextProvider` for code retrieval
  - [ ] Consider custom provider for reasoning chunks
  - [ ] Implement caching strategy
  - [ ] Track usage with `update()`

- [ ] **Agent Integration**
  - [ ] Use `AgentRegistry` for discovery
  - [ ] Create agent config files
  - [ ] Implement agent selection logic
  - [ ] Handle fallback scenarios

- [ ] **Configuration**
  - [ ] Define Phase 2 config keys in schema
  - [ ] Test override hierarchy
  - [ ] Document new config options
  - [ ] Handle backward compatibility

- [ ] **Testing**
  - [ ] Use Phase 1 test fixtures
  - [ ] Write integration tests with Phase 1
  - [ ] Performance benchmarks
  - [ ] Memory profiling

- [ ] **Documentation**
  - [ ] Document Phase 2 interfaces
  - [ ] Update architecture diagrams
  - [ ] Create Phase 3 contracts
  - [ ] Migration guide for Phase 3

---

## Troubleshooting

### Issue: Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'aurora_core'`

**Solution**:
```bash
# Ensure packages installed in editable mode
pip install -e .

# Verify installation
pip list | grep aurora
```

### Issue: Store Initialization Fails

**Symptom**: `StorageError: Failed to initialize database`

**Solutions**:
1. Check database path exists and is writable
2. Ensure parent directory exists
3. Check file permissions
4. Try in-memory database first: `SQLiteStore(":memory:")`

### Issue: Parser Not Found

**Symptom**: `registry.get_parser_for_file()` returns `None`

**Solutions**:
```python
# Check file extension supported
from aurora_context_code.registry import get_global_registry

registry = get_global_registry()
print(f"Supported languages: {list(registry._parsers.keys())}")

# Verify Python parser registered
python_parser = registry.get_parser("python")
assert python_parser is not None
```

### Issue: Configuration Not Loading

**Symptom**: Config values are defaults, not custom values

**Solutions**:
1. Check config file location (`.aurora/config.json`)
2. Verify JSON is valid (`jq . .aurora/config.json`)
3. Check file permissions
4. Enable debug logging: `export AURORA_LOG_LEVEL=DEBUG`

### Issue: Tests Failing

**Symptom**: Phase 2 tests fail with Phase 1 interfaces

**Solutions**:
1. Ensure using Phase 1 fixtures correctly
2. Check Phase 1 version: `git describe --tags`
3. Verify no breaking changes: Read `CHANGELOG.md`
4. Check test isolation (use fixtures, not global state)

---

## Getting Help

### Resources

- **Documentation**: `/docs` directory
- **Phase 2 Contracts**: `docs/PHASE2_CONTRACTS.md`
- **Extension Guide**: `docs/EXTENSION_GUIDE.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`

### Support

- **Issues**: Report bugs on issue tracker
- **Questions**: Ask in developer forum
- **API Documentation**: Run `pydoc aurora_core.store`

### Version Information

- **Phase 1 Version**: v1.0.0-phase1
- **Release Date**: December 20, 2025
- **Stability**: Production-ready
- **Support**: LTS (Long-term support)

---

## Conclusion

Phase 1 provides a solid, tested foundation for Phase 2 development. All interfaces are stable, well-documented, and production-ready.

**Key Takeaways**:
1. Use stable interfaces (`Store`, `Chunk`, `Parser`, etc.)
2. Don't depend on internal implementation details
3. Test with Phase 1 fixtures for integration confidence
4. Follow configuration hierarchy for flexibility
5. Consult `PHASE2_CONTRACTS.md` for stability guarantees

**Happy Building! 🚀**

---

**Guide Version**: 1.0
**Last Updated**: December 20, 2025
**Maintainer**: AURORA Core Team
**Feedback**: Open an issue with tag `phase2-migration`
