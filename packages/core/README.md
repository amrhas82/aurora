# AURORA Core

Core components for the AURORA framework including storage, chunk types, and context management.

## Installation

```bash
pip install -e .
```

## Components

- **Storage Layer**: SQLite and in-memory storage implementations
- **Chunk Types**: Base chunk class and concrete implementations (CodeChunk, ReasoningChunk)
- **Context Management**: Interfaces for context retrieval and management
- **Configuration**: Configuration loader with validation

## Usage

```python
from aurora_core.chunks import CodeChunk
from aurora_core.store import MemoryStore

# Create a code chunk
chunk = CodeChunk(
    chunk_id="code:example.py:my_func",
    file_path="/absolute/path/example.py",
    element_type="function",
    name="my_func",
    line_start=10,
    line_end=20,
)

# Store it
store = MemoryStore()
store.save_chunk(chunk)

# Retrieve it
retrieved = store.get_chunk("code:example.py:my_func")
```

## Development

Run tests:
```bash
pytest tests/
```

Run type checking:
```bash
mypy src/
```

Format code:
```bash
ruff format src/
```
