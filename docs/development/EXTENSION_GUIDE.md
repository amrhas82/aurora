# AURORA Extension Guide

This guide explains how to extend AURORA with custom implementations of parsers, storage backends, context providers, and agents.

## Table of Contents

- [Custom Code Parsers](#custom-code-parsers)
- [Custom Storage Backends](#custom-storage-backends)
- [Custom Context Providers](#custom-context-providers)
- [Custom Agent Implementations](#custom-agent-implementations)
- [Best Practices](#best-practices)

---

## Custom Code Parsers

Create custom parsers to add support for additional programming languages.

### 1. Implement the CodeParser Interface

```python
from aurora_context_code.parser import CodeParser
from aurora_core.chunks import CodeChunk
from typing import List

class JavaScriptParser(CodeParser):
    """Parser for JavaScript source files."""

    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the file.

        Args:
            file_path: Path to the file to check

        Returns:
            True if file has .js or .jsx extension
        """
        return file_path.endswith(('.js', '.jsx'))

    def parse(self, content: str, file_path: str) -> List[CodeChunk]:
        """Parse JavaScript content into chunks.

        Args:
            content: Source code content
            file_path: Path to the source file

        Returns:
            List of CodeChunk objects representing functions, classes, etc.
        """
        chunks = []

        # Your parsing logic here
        # Example: use tree-sitter-javascript or custom parser

        return chunks
```

### 2. Using Tree-sitter for Parsing

Tree-sitter provides robust AST parsing for many languages:

```python
import tree_sitter
from tree_sitter import Language, Parser as TSParser
from aurora_context_code.parser import CodeParser
from aurora_core.chunks import CodeChunk

class JavaScriptParser(CodeParser):
    """JavaScript parser using tree-sitter."""

    def __init__(self):
        # Load tree-sitter JavaScript grammar
        # You'll need: pip install tree-sitter-javascript
        JS_LANGUAGE = Language('path/to/languages.so', 'javascript')
        self.parser = TSParser()
        self.parser.set_language(JS_LANGUAGE)

    def can_parse(self, file_path: str) -> bool:
        return file_path.endswith(('.js', '.jsx'))

    def parse(self, content: str, file_path: str) -> List[CodeChunk]:
        tree = self.parser.parse(bytes(content, 'utf8'))
        root_node = tree.root_node

        chunks = []

        # Extract function declarations
        for node in self._find_nodes_by_type(root_node, 'function_declaration'):
            chunk = self._create_chunk_from_node(node, content, file_path)
            if chunk:
                chunks.append(chunk)

        # Extract class declarations
        for node in self._find_nodes_by_type(root_node, 'class_declaration'):
            chunk = self._create_chunk_from_node(node, content, file_path)
            if chunk:
                chunks.append(chunk)

        return chunks

    def _find_nodes_by_type(self, node, node_type: str):
        """Recursively find all nodes of a given type."""
        if node.type == node_type:
            yield node
        for child in node.children:
            yield from self._find_nodes_by_type(child, node_type)

    def _create_chunk_from_node(self, node, content: str, file_path: str) -> CodeChunk:
        """Create a CodeChunk from a tree-sitter node."""
        lines = content.split('\n')
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1

        # Extract name
        name_node = node.child_by_field_name('name')
        name = content[name_node.start_byte:name_node.end_byte] if name_node else 'anonymous'

        # Calculate complexity (count branch points)
        complexity = self._calculate_complexity(node)

        return CodeChunk(
            content=content[node.start_byte:node.end_byte],
            chunk_type='code',
            start_line=start_line,
            end_line=end_line,
            metadata={
                'language': 'javascript',
                'name': name,
                'file_path': file_path,
                'complexity': complexity,
                'node_type': node.type
            }
        )

    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity
        branch_types = {'if_statement', 'while_statement', 'for_statement',
                       'switch_case', 'catch_clause', 'conditional_expression'}

        for child in node.children:
            if child.type in branch_types:
                complexity += 1
            complexity += self._calculate_complexity(child) - 1

        return complexity
```

### 3. Register the Parser

```python
from aurora_context_code.registry import ParserRegistry

# Manual registration
registry = ParserRegistry()
registry.register(JavaScriptParser())

# Or use auto-registration on import
# In your __init__.py:
from .javascript import JavaScriptParser
ParserRegistry().register(JavaScriptParser())
```

### 4. Test Your Parser

```python
import pytest
from your_package.javascript import JavaScriptParser
from aurora_core.chunks import CodeChunk

def test_javascript_parser_functions():
    parser = JavaScriptParser()

    content = """
    function calculateSum(a, b) {
        if (a < 0 || b < 0) {
            throw new Error('Negative numbers not allowed');
        }
        return a + b;
    }
    """

    chunks = parser.parse(content, 'test.js')

    assert len(chunks) == 1
    assert chunks[0].metadata['name'] == 'calculateSum'
    assert chunks[0].metadata['language'] == 'javascript'
    assert chunks[0].metadata['complexity'] >= 2  # if statement adds complexity
    assert chunks[0].start_line == 2
    assert 'function calculateSum' in chunks[0].content
```

---

## Custom Storage Backends

Extend AURORA with alternative storage backends (PostgreSQL, MongoDB, Redis, etc.).

### 1. Implement the Store Interface

```python
from aurora_core.store.base import Store
from aurora_core.chunks import Chunk
from aurora_core.types import ChunkID, Activation
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
import psycopg2
from psycopg2.extras import Json

class PostgreSQLStore(Store):
    """PostgreSQL-based chunk storage."""

    def __init__(self, connection_string: str):
        """Initialize PostgreSQL store.

        Args:
            connection_string: PostgreSQL connection string
                (e.g., 'postgresql://user:pass@localhost/aurora')
        """
        self.conn = psycopg2.connect(connection_string)
        self._initialize_schema()

    def _initialize_schema(self):
        """Create tables if they don't exist."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id VARCHAR(255) PRIMARY KEY,
                    content TEXT NOT NULL,
                    chunk_type VARCHAR(50) NOT NULL,
                    start_line INTEGER,
                    end_line INTEGER,
                    metadata JSONB,
                    created_at TIMESTAMP NOT NULL,
                    last_accessed TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunk_type
                ON chunks(chunk_type)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata
                ON chunks USING GIN(metadata)
            """)

            self.conn.commit()

    def save_chunk(self, chunk: Chunk) -> None:
        """Save a chunk to PostgreSQL."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chunks
                (chunk_id, content, chunk_type, start_line, end_line,
                 metadata, created_at, last_accessed, access_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    chunk_type = EXCLUDED.chunk_type,
                    start_line = EXCLUDED.start_line,
                    end_line = EXCLUDED.end_line,
                    metadata = EXCLUDED.metadata
            """, (
                chunk.chunk_id,
                chunk.content,
                chunk.chunk_type,
                chunk.start_line,
                chunk.end_line,
                Json(chunk.metadata),
                datetime.now(UTC),
                datetime.now(UTC),
                0
            ))
            self.conn.commit()

    def get_chunk(self, chunk_id: ChunkID) -> Optional[Chunk]:
        """Retrieve a chunk by ID."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT content, chunk_type, start_line, end_line, metadata
                FROM chunks
                WHERE chunk_id = %s
            """, (chunk_id,))

            row = cursor.fetchone()
            if not row:
                return None

            # Import the appropriate Chunk subclass
            from aurora_core.chunks import CodeChunk

            return CodeChunk(
                chunk_id=chunk_id,
                content=row[0],
                chunk_type=row[1],
                start_line=row[2],
                end_line=row[3],
                metadata=row[4]
            )

    def list_chunks(
        self,
        chunk_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Chunk]:
        """List chunks with optional filtering."""
        with self.conn.cursor() as cursor:
            if chunk_type:
                cursor.execute("""
                    SELECT chunk_id, content, chunk_type, start_line,
                           end_line, metadata
                    FROM chunks
                    WHERE chunk_type = %s
                    ORDER BY last_accessed DESC
                    LIMIT %s OFFSET %s
                """, (chunk_type, limit, offset))
            else:
                cursor.execute("""
                    SELECT chunk_id, content, chunk_type, start_line,
                           end_line, metadata
                    FROM chunks
                    ORDER BY last_accessed DESC
                    LIMIT %s OFFSET %s
                """, (limit, offset))

            from aurora_core.chunks import CodeChunk

            chunks = []
            for row in cursor.fetchall():
                chunk = CodeChunk(
                    chunk_id=row[0],
                    content=row[1],
                    chunk_type=row[2],
                    start_line=row[3],
                    end_line=row[4],
                    metadata=row[5]
                )
                chunks.append(chunk)

            return chunks

    def delete_chunk(self, chunk_id: ChunkID) -> bool:
        """Delete a chunk."""
        with self.conn.cursor() as cursor:
            cursor.execute("DELETE FROM chunks WHERE chunk_id = %s", (chunk_id,))
            self.conn.commit()
            return cursor.rowcount > 0

    def update_activation(self, chunk_id: ChunkID) -> None:
        """Update chunk access tracking."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE chunks
                SET last_accessed = %s,
                    access_count = access_count + 1
                WHERE chunk_id = %s
            """, (datetime.now(UTC), chunk_id))
            self.conn.commit()

    def get_activation(self, chunk_id: ChunkID) -> Optional[Activation]:
        """Get activation metrics for a chunk."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT last_accessed, access_count
                FROM chunks
                WHERE chunk_id = %s
            """, (chunk_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return Activation(
                last_accessed=row[0],
                access_count=row[1]
            )

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
```

### 2. Test Your Storage Backend

```python
import pytest
from your_package.postgres_store import PostgreSQLStore
from aurora_core.chunks import CodeChunk

@pytest.fixture
def postgres_store():
    """Create a test PostgreSQL store."""
    store = PostgreSQLStore("postgresql://test:test@localhost/test_aurora")
    yield store
    # Cleanup
    with store.conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE chunks")
        store.conn.commit()
    store.close()

def test_postgres_save_and_retrieve(postgres_store):
    chunk = CodeChunk(
        content="def test(): pass",
        chunk_type="code",
        start_line=1,
        end_line=1,
        metadata={"name": "test", "language": "python"}
    )

    postgres_store.save_chunk(chunk)
    retrieved = postgres_store.get_chunk(chunk.chunk_id)

    assert retrieved is not None
    assert retrieved.content == chunk.content
    assert retrieved.metadata["name"] == "test"

def test_postgres_activation_tracking(postgres_store):
    chunk = CodeChunk(
        content="def test(): pass",
        chunk_type="code",
        start_line=1,
        end_line=1,
        metadata={"name": "test"}
    )

    postgres_store.save_chunk(chunk)
    postgres_store.update_activation(chunk.chunk_id)
    postgres_store.update_activation(chunk.chunk_id)

    activation = postgres_store.get_activation(chunk.chunk_id)
    assert activation.access_count == 2
```

---

## Custom Context Providers

Create specialized context providers for different retrieval strategies.

### 1. Implement the ContextProvider Interface

```python
from aurora_core.context.provider import ContextProvider
from aurora_core.store.base import Store
from aurora_core.chunks import Chunk
from typing import List, Dict, Any

class SemanticContextProvider(ContextProvider):
    """Context provider using semantic embeddings for retrieval."""

    def __init__(self, store: Store, embedding_model):
        """Initialize semantic provider.

        Args:
            store: Storage backend for chunks
            embedding_model: Model for generating embeddings (e.g., sentence-transformers)
        """
        self.store = store
        self.embedding_model = embedding_model
        self.cache = {}

    def retrieve(
        self,
        query: str,
        max_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Retrieve chunks using semantic similarity.

        Args:
            query: Natural language query
            max_results: Maximum number of results
            filters: Optional metadata filters

        Returns:
            List of relevant chunks, ranked by semantic similarity
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query)

        # Get all chunks (or filtered subset)
        chunks = self.store.list_chunks(
            chunk_type=filters.get('chunk_type') if filters else None
        )

        # Calculate semantic similarity
        scored_chunks = []
        for chunk in chunks:
            # Generate chunk embedding (cache if possible)
            chunk_embedding = self._get_or_create_embedding(chunk)

            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_embedding, chunk_embedding)

            # Add score to metadata
            chunk.metadata['_score'] = similarity
            scored_chunks.append((similarity, chunk))

        # Sort by similarity and return top results
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored_chunks[:max_results]]

    def update(self, chunk_id: str) -> None:
        """Update activation tracking."""
        self.store.update_activation(chunk_id)

    def refresh(self) -> None:
        """Clear embedding cache."""
        self.cache.clear()

    def _get_or_create_embedding(self, chunk: Chunk):
        """Get cached embedding or generate new one."""
        if chunk.chunk_id not in self.cache:
            self.cache[chunk.chunk_id] = self.embedding_model.encode(chunk.content)
        return self.cache[chunk.chunk_id]

    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors."""
        import numpy as np
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
```

---

## Custom Agent Implementations

Implement custom agents for the SOAR agent registry.

### 1. Create Agent Configuration

```json
{
  "agents": [
    {
      "id": "custom-code-analyzer",
      "name": "Custom Code Analyzer",
      "type": "local",
      "path": "/usr/local/bin/custom-analyzer",
      "capabilities": [
        "code-analysis",
        "security-scanning",
        "performance-profiling"
      ],
      "domains": ["python", "javascript"],
      "metadata": {
        "version": "2.1.0",
        "provider": "CustomAnalyzer Inc",
        "max_file_size": 10485760
      }
    }
  ]
}
```

### 2. Implement Agent Protocol

Your agent should accept JSON input via stdin and output JSON via stdout:

```python
#!/usr/bin/env python3
"""Custom code analyzer agent."""
import json
import sys

def analyze_code(request: dict) -> dict:
    """Analyze code and return results."""
    code = request.get('code', '')
    language = request.get('language', 'python')

    # Your analysis logic here
    results = {
        'issues': [],
        'metrics': {},
        'suggestions': []
    }

    return results

if __name__ == '__main__':
    # Read request from stdin
    request = json.load(sys.stdin)

    # Process request
    response = analyze_code(request)

    # Write response to stdout
    json.dump(response, sys.stdout)
    sys.exit(0)
```

---

## Best Practices

### General Guidelines

1. **Follow Interface Contracts**: Implement all required methods from abstract base classes
2. **Handle Errors Gracefully**: Use AURORA's exception hierarchy for error handling
3. **Add Comprehensive Tests**: Include unit and integration tests for extensions
4. **Document Your Code**: Follow Google-style docstrings
5. **Validate Inputs**: Check preconditions and validate data before processing
6. **Use Type Hints**: Leverage Python type hints for better IDE support

### Performance Considerations

1. **Implement Caching**: Cache expensive operations (embeddings, parsed ASTs)
2. **Use Connection Pooling**: For database-backed stores
3. **Batch Operations**: Process multiple items when possible
4. **Profile Your Code**: Use AURORA's benchmarking utilities to measure performance
5. **Set Reasonable Limits**: Add configurable limits for queries, batch sizes, etc.

### Testing Extensions

```python
import pytest
from aurora_testing import (
    sample_store,
    sample_code_chunk,
    performance_benchmark
)

def test_custom_parser_with_fixtures(sample_code_chunk):
    """Use AURORA's testing fixtures."""
    parser = MyCustomParser()
    chunks = parser.parse(sample_code_chunk.content, 'test.js')
    assert len(chunks) > 0

def test_custom_store_performance(performance_benchmark):
    """Benchmark custom storage backend."""
    store = MyCustomStore()

    with performance_benchmark('save_chunk') as bench:
        for i in range(1000):
            chunk = create_test_chunk(i)
            store.save_chunk(chunk)

    assert bench.avg_time < 0.050  # <50ms target
```

### Integration with Configuration

Make your extensions configurable:

```python
from aurora_core.config import Config

class MyCustomParser(CodeParser):
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self.max_complexity = self.config.get_int('parser.max_complexity', 50)
        self.timeout = self.config.get_int('parser.timeout', 30)
```

### Distribution

Package your extension for easy installation:

```toml
# pyproject.toml
[project]
name = "aurora-javascript-parser"
version = "1.0.0"
dependencies = [
    "aurora-core>=1.0.0",
    "aurora-context-code>=1.0.0",
    "tree-sitter-javascript>=0.20.0"
]

[project.entry-points."aurora.parsers"]
javascript = "aurora_javascript:JavaScriptParser"
```

---

## Additional Resources

- [AURORA Architecture Documentation](../README.md#architecture)
- [API Reference](#) (Coming soon)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [Test Framework Documentation](../packages/testing/README.md)

For questions or support, please open an issue on GitHub.
