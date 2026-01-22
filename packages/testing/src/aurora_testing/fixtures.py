"""Reusable pytest fixtures for AURORA testing.

Provides common fixtures for:
- Storage backends (SQLite, Memory)
- Code chunks with various configurations
- Parsers and parser registries
- Sample Python files for testing
- Temporary directories and file structures
"""

from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import pytest

from aurora_context_code.languages.python import PythonParser
from aurora_context_code.registry import get_global_registry
from aurora_core.chunks.code_chunk import CodeChunk
from aurora_core.context.code_provider import CodeContextProvider
from aurora_core.store.memory import MemoryStore

# Import core components
from aurora_core.store.sqlite import SQLiteStore


# ============================================================================
# Storage Fixtures
# ============================================================================


@pytest.fixture
def memory_store() -> Generator[MemoryStore, None, None]:
    """Create an in-memory store for testing.

    Yields:
        MemoryStore: Fresh memory store instance.

    """
    store = MemoryStore()
    yield store
    # No cleanup needed for memory store


@pytest.fixture
def sqlite_store() -> Generator[SQLiteStore, None, None]:
    """Create an in-memory SQLite store for testing.

    Yields:
        SQLiteStore: Fresh SQLite store with :memory: database.

    """
    store = SQLiteStore(db_path=":memory:")
    yield store
    store.close()


@pytest.fixture
def sqlite_file_store(tmp_path: Path) -> Generator[SQLiteStore, None, None]:
    """Create a file-based SQLite store for testing persistence.

    Args:
        tmp_path: pytest temporary path fixture.

    Yields:
        SQLiteStore: SQLite store backed by temporary file.

    """
    db_path = tmp_path / "test_aurora.db"
    store = SQLiteStore(db_path=str(db_path))
    yield store
    store.close()


# ============================================================================
# Chunk Fixtures
# ============================================================================


@pytest.fixture
def sample_code_chunk() -> CodeChunk:
    """Create a simple code chunk for testing.

    Returns:
        CodeChunk: Basic code chunk with minimal fields.

    """
    return CodeChunk(
        chunk_id="code:test.py:func",
        file_path="/absolute/path/test.py",
        element_type="function",
        name="test_function",
        line_start=10,
        line_end=20,
    )


@pytest.fixture
def sample_code_chunk_with_metadata() -> CodeChunk:
    """Create a code chunk with full metadata for testing.

    Returns:
        CodeChunk: Code chunk with all optional fields populated.

    """
    return CodeChunk(
        chunk_id="code:parser.py:parse_file",
        file_path="/project/src/parser.py",
        element_type="function",
        name="parse_file",
        line_start=100,
        line_end=150,
        signature="def parse_file(filepath: Path, encoding: str = 'utf-8') -> Dict[str, Any]",
        docstring="Parse a file and return structured data.\n\nArgs:\n    filepath: Path to file\n    encoding: File encoding\n\nReturns:\n    Parsed data as dictionary",
        complexity_score=0.6,
        dependencies=["code:validator.py:validate", "code:loader.py:load"],
        language="python",
    )


@pytest.fixture
def sample_class_chunk() -> CodeChunk:
    """Create a code chunk representing a class.

    Returns:
        CodeChunk: Class chunk with typical metadata.

    """
    return CodeChunk(
        chunk_id="code:models.py:UserModel",
        file_path="/project/models.py",
        element_type="class",
        name="UserModel",
        line_start=50,
        line_end=100,
        signature="class UserModel(BaseModel)",
        docstring="User data model with validation.",
        complexity_score=0.4,
        dependencies=["code:base.py:BaseModel"],
        language="python",
    )


@pytest.fixture
def sample_method_chunk() -> CodeChunk:
    """Create a code chunk representing a method.

    Returns:
        CodeChunk: Method chunk with parent class context.

    """
    return CodeChunk(
        chunk_id="code:service.py:ApiClient.fetch_data",
        file_path="/project/service.py",
        element_type="method",
        name="fetch_data",
        line_start=75,
        line_end=95,
        signature="def fetch_data(self, endpoint: str) -> Response",
        docstring="Fetch data from API endpoint.",
        complexity_score=0.5,
        dependencies=["code:http.py:make_request"],
        language="python",
    )


@pytest.fixture
def chunk_collection() -> list[CodeChunk]:
    """Create a collection of diverse chunks for testing retrieval.

    Returns:
        List[CodeChunk]: List of chunks with different characteristics.

    """
    return [
        CodeChunk(
            chunk_id="code:json_parser.py:parse_json",
            file_path="/project/parsers/json_parser.py",
            element_type="function",
            name="parse_json_file",
            line_start=10,
            line_end=25,
            signature="def parse_json_file(filepath: str) -> dict",
            docstring="Parse JSON data from a file and return as dictionary",
            complexity_score=0.3,
            dependencies=[],
        ),
        CodeChunk(
            chunk_id="code:xml_parser.py:parse_xml",
            file_path="/project/parsers/xml_parser.py",
            element_type="function",
            name="parse_xml_file",
            line_start=15,
            line_end=40,
            signature="def parse_xml_file(filepath: str) -> ElementTree",
            docstring="Parse XML data from a file and return element tree",
            complexity_score=0.5,
            dependencies=[],
        ),
        CodeChunk(
            chunk_id="code:validator.py:validate",
            file_path="/project/validation/validator.py",
            element_type="function",
            name="validate_data",
            line_start=5,
            line_end=20,
            signature="def validate_data(data: dict) -> bool",
            docstring="Validate data structure matches schema requirements",
            complexity_score=0.4,
            dependencies=["code:json_parser.py:parse_json"],
        ),
        CodeChunk(
            chunk_id="code:loader.py:ConfigLoader",
            file_path="/project/config/loader.py",
            element_type="class",
            name="ConfigLoader",
            line_start=1,
            line_end=50,
            signature="class ConfigLoader",
            docstring="Load configuration from JSON files",
            complexity_score=0.6,
            dependencies=["code:json_parser.py:parse_json"],
        ),
    ]


# ============================================================================
# Parser Fixtures
# ============================================================================


@pytest.fixture
def python_parser() -> PythonParser:
    """Create a PythonParser instance.

    Returns:
        PythonParser: Fresh parser instance.

    """
    return PythonParser()


@pytest.fixture
def parser_registry() -> Any:  # ParserRegistry type not imported
    """Create a fresh ParserRegistry with PythonParser registered.

    Returns:
        ParserRegistry: Registry with Python parser.

    """
    return get_global_registry()


# ============================================================================
# Context Provider Fixtures
# ============================================================================


@pytest.fixture
def code_context_provider(memory_store: MemoryStore, parser_registry: Any) -> CodeContextProvider:
    """Create a CodeContextProvider with memory store.

    Args:
        memory_store: Memory store fixture.
        parser_registry: Parser registry fixture.

    Returns:
        CodeContextProvider: Configured context provider.

    """
    return CodeContextProvider(memory_store, parser_registry)


@pytest.fixture
def populated_context_provider(
    memory_store: MemoryStore,
    parser_registry: Any,
    chunk_collection: list[CodeChunk],
) -> CodeContextProvider:
    """Create a CodeContextProvider pre-populated with sample chunks.

    Args:
        memory_store: Memory store fixture.
        parser_registry: Parser registry fixture.
        chunk_collection: Collection of sample chunks.

    Returns:
        CodeContextProvider: Context provider with data already stored.

    """
    provider = CodeContextProvider(memory_store, parser_registry)
    for chunk in chunk_collection:
        memory_store.save_chunk(chunk)
    return provider


# ============================================================================
# File and Directory Fixtures
# ============================================================================


@pytest.fixture
def sample_python_file(tmp_path: Path) -> Path:
    """Create a simple Python file for parsing tests.

    Args:
        tmp_path: pytest temporary path fixture.

    Returns:
        Path: Path to created Python file.

    """
    test_file = tmp_path / "sample.py"
    test_file.write_text(
        '''
def simple_function(x, y):
    """Add two numbers."""
    return x + y


class SimpleClass:
    """A simple class."""

    def method_one(self, value):
        """Process a value."""
        if value > 0:
            return value * 2
        return 0

    def method_two(self, items):
        """Process items."""
        result = []
        for item in items:
            if item:
                result.append(item)
        return result
''',
    )
    return test_file


@pytest.fixture
def complex_python_file(tmp_path: Path) -> Path:
    """Create a complex Python file with nested structures.

    Args:
        tmp_path: pytest temporary path fixture.

    Returns:
        Path: Path to created Python file.

    """
    test_file = tmp_path / "complex.py"
    test_file.write_text(
        '''
"""Module docstring."""

import os
import sys
from typing import List, Dict, Optional


class OuterClass:
    """Outer class with nested structures."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config
        self.data = []

    def process_data(self, items: List[Any]) -> List[Any]:
        """Process data with complex logic."""
        result = []
        for item in items:
            if item is None:
                continue

            try:
                processed = self._transform(item)
                if processed:
                    result.append(processed)
            except ValueError as e:
                self._handle_error(e)
                continue
            except Exception:
                raise

        return result

    def _transform(self, item: Any) -> Optional[Any]:
        """Transform a single item."""
        if isinstance(item, str):
            return item.upper()
        elif isinstance(item, int):
            return item * 2
        elif isinstance(item, list):
            return [self._transform(x) for x in item]
        return None

    def _handle_error(self, error: Exception) -> None:
        """Handle processing errors."""
        print(f"Error: {error}")

    class InnerClass:
        """Inner nested class."""

        def inner_method(self, x: int) -> int:
            """Process in inner class."""
            if x > 0:
                return x ** 2
            elif x < 0:
                return abs(x)
            else:
                return 0


def standalone_function(data: Dict[str, Any]) -> bool:
    """Standalone function with validation logic."""
    required_keys = ["id", "name", "value"]

    for key in required_keys:
        if key not in data:
            return False

    if not isinstance(data["value"], (int, float)):
        return False

    return True
''',
    )
    return test_file


@pytest.fixture
def broken_python_file(tmp_path: Path) -> Path:
    """Create a Python file with syntax errors.

    Args:
        tmp_path: pytest temporary path fixture.

    Returns:
        Path: Path to created Python file with syntax errors.

    """
    test_file = tmp_path / "broken.py"
    test_file.write_text(
        """
def broken_function(x, y)
    # Missing colon
    return x + y

class BrokenClass
    # Missing colon
    def method():
        pass

# Unclosed string
message = "this string is not closed
""",
    )
    return test_file


@pytest.fixture
def python_file_collection(tmp_path: Path) -> Path:
    """Create a collection of Python files in a directory structure.

    Args:
        tmp_path: pytest temporary path fixture.

    Returns:
        Path: Path to directory containing multiple Python files.

    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create module structure
    (project_dir / "__init__.py").write_text("")

    (project_dir / "utils.py").write_text(
        '''
def helper_function(x):
    """Helper utility."""
    return x * 2
''',
    )

    (project_dir / "models.py").write_text(
        '''
class DataModel:
    """Data model class."""

    def __init__(self, name):
        self.name = name

    def validate(self):
        return bool(self.name)
''',
    )

    subdir = project_dir / "submodule"
    subdir.mkdir()
    (subdir / "__init__.py").write_text("")
    (subdir / "processor.py").write_text(
        '''
def process(data):
    """Process data."""
    return [x for x in data if x]
''',
    )

    return project_dir


@pytest.fixture
def empty_python_file(tmp_path: Path) -> Path:
    """Create an empty Python file.

    Args:
        tmp_path: pytest temporary path fixture.

    Returns:
        Path: Path to empty Python file.

    """
    test_file = tmp_path / "empty.py"
    test_file.write_text("")
    return test_file


@pytest.fixture
def python_file_with_only_docstring(tmp_path: Path) -> Path:
    """Create a Python file with only module docstring.

    Args:
        tmp_path: pytest temporary path fixture.

    Returns:
        Path: Path to Python file with only docstring.

    """
    test_file = tmp_path / "docstring_only.py"
    test_file.write_text('"""This module has only a docstring."""\n')
    return test_file


# ============================================================================
# Performance Test Fixtures
# ============================================================================


@pytest.fixture
def large_python_file(tmp_path: Path) -> Path:
    """Create a large Python file for performance testing (~1000 lines).

    Args:
        tmp_path: pytest temporary path fixture.

    Returns:
        Path: Path to large Python file.

    """
    test_file = tmp_path / "large.py"
    lines = []

    for i in range(100):
        lines.append(
            f'''
class LargeClass_{i}:
    """Large class {i}."""

    def __init__(self, value):
        self.value = value

    def process(self, data):
        result = []
        for item in data:
            if item > 0:
                result.append(item * 2)
            elif item < 0:
                result.append(item / 2)
            else:
                result.append(0)
        return result
''',
        )

    test_file.write_text("\n".join(lines))
    return test_file


@pytest.fixture
def scalable_python_file_factory(tmp_path: Path) -> Callable[[int], Path]:
    """Factory to create Python files of various sizes for scaling tests.

    Args:
        tmp_path: pytest temporary path fixture.

    Returns:
        Callable: Function that creates Python file with N functions.

    """

    def create_file(num_functions: int) -> Path:
        """Create Python file with specified number of functions.

        Args:
            num_functions: Number of functions to generate.

        Returns:
            Path: Path to generated file.

        """
        test_file = tmp_path / f"scale_{num_functions}.py"
        lines = []

        for i in range(num_functions):
            lines.append(
                f'''
def function_{i}(x, y):
    """Function {i}."""
    if x > y:
        return x
    elif x < y:
        return y
    else:
        return 0
''',
            )

        test_file.write_text("\n".join(lines))
        return test_file

    return create_file


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with config files.

    Args:
        tmp_path: pytest temporary path fixture.

    Returns:
        Path: Path to config directory.

    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_agent_config(tmp_path: Path) -> Path:
    """Create a sample agent configuration file.

    Args:
        tmp_path: pytest temporary path fixture.

    Returns:
        Path: Path to agent config JSON file.

    """
    import json

    config_file = tmp_path / "agents.json"
    config_data = {
        "agents": [
            {
                "id": "test-agent-1",
                "name": "Test Agent 1",
                "type": "local",
                "path": "/usr/local/bin/agent1",
                "capabilities": ["code", "test"],
                "domains": ["python"],
            },
            {
                "id": "test-agent-2",
                "name": "Test Agent 2",
                "type": "remote",
                "endpoint": "http://localhost:8080/agent",
                "capabilities": ["analyze", "review"],
                "domains": ["python", "javascript"],
            },
        ],
    }

    config_file.write_text(json.dumps(config_data, indent=2))
    return config_file


@pytest.fixture
def fixtures_dir() -> Path:
    """Get the path to test fixtures directory.

    Returns:
        Path: Path to tests/fixtures directory.

    """
    return Path("/home/hamr/PycharmProjects/aurora/tests/fixtures")


@pytest.fixture
def sample_python_files_dir(fixtures_dir: Path) -> Path:
    """Get the path to sample Python files directory.

    Args:
        fixtures_dir: Fixtures directory fixture.

    Returns:
        Path: Path to sample_python_files directory.

    """
    return fixtures_dir / "sample_python_files"
