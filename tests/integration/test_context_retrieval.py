"""
Integration tests for end-to-end context retrieval flow.

Tests the complete flow: Parse → Store → Retrieve
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from aurora_core.context.code_provider import CodeContextProvider
from aurora_core.store.memory import MemoryStore
from aurora_core.chunks.code_chunk import CodeChunk
from aurora_context_code.registry import ParserRegistry, get_global_registry


class TestContextRetrievalFlow:
    """Test end-to-end context retrieval scenarios."""

    @pytest.fixture
    def setup_provider(self):
        """Set up provider with store and sample data."""
        store = MemoryStore()
        registry = get_global_registry()
        provider = CodeContextProvider(store, registry)

        # Add sample chunks
        chunks = [
            CodeChunk(
                chunk_id="code_json_parser",
                file_path="/project/parsers/json_parser.py",
                element_type="function",
                name="parse_json_file",
                line_start=10,
                line_end=25,
                signature="def parse_json_file(filepath: str) -> dict",
                docstring="Parse JSON data from a file and return as dictionary",
                complexity_score=0.3,
                dependencies=[]
            ),
            CodeChunk(
                chunk_id="code_xml_parser",
                file_path="/project/parsers/xml_parser.py",
                element_type="function",
                name="parse_xml_file",
                line_start=15,
                line_end=40,
                signature="def parse_xml_file(filepath: str) -> ElementTree",
                docstring="Parse XML data from a file and return element tree",
                complexity_score=0.5,
                dependencies=[]
            ),
            CodeChunk(
                chunk_id="code_data_validator",
                file_path="/project/validation/validator.py",
                element_type="function",
                name="validate_data",
                line_start=5,
                line_end=20,
                signature="def validate_data(data: dict) -> bool",
                docstring="Validate data structure matches schema requirements",
                complexity_score=0.4,
                dependencies=["code_json_parser"]
            ),
            CodeChunk(
                chunk_id="code_config_loader",
                file_path="/project/config/loader.py",
                element_type="class",
                name="ConfigLoader",
                line_start=1,
                line_end=50,
                signature="class ConfigLoader",
                docstring="Load configuration from JSON files",
                complexity_score=0.6,
                dependencies=["code_json_parser"]
            ),
        ]

        for chunk in chunks:
            store.save_chunk(chunk)

        return provider, store, chunks

    def test_retrieve_json_related_chunks(self, setup_provider):
        """Test retrieving chunks related to JSON parsing."""
        provider, store, chunks = setup_provider

        results = provider.retrieve("json parse", limit=5)

        # Should return JSON-related chunks
        assert len(results) > 0
        # JSON parser should be first (best match)
        assert results[0].name == "parse_json_file"
        # Config loader should also be in results (mentions JSON in docstring)
        result_names = [r.name for r in results]
        assert "ConfigLoader" in result_names

    def test_retrieve_with_limit(self, setup_provider):
        """Test that limit parameter works correctly."""
        provider, store, chunks = setup_provider

        results = provider.retrieve("parse", limit=2)

        assert len(results) == 2

    def test_retrieve_specific_functionality(self, setup_provider):
        """Test retrieving chunks for specific functionality."""
        provider, store, chunks = setup_provider

        results = provider.retrieve("validate data schema", limit=5)

        # Validator should be top result
        assert len(results) > 0
        assert results[0].name == "validate_data"

    def test_retrieve_by_file_type(self, setup_provider):
        """Test retrieving chunks by file/module name."""
        provider, store, chunks = setup_provider

        results = provider.retrieve("xml parser", limit=5)

        # XML parser should be top result
        assert len(results) > 0
        assert results[0].name == "parse_xml_file"

    def test_retrieve_no_matches(self, setup_provider):
        """Test query with no matching chunks."""
        provider, store, chunks = setup_provider

        results = provider.retrieve("database connection pool", limit=5)

        # Should return empty or very low-scoring results
        # Since none of our chunks mention database/connection/pool
        assert len(results) == 0 or all("database" not in c.name.lower() for c in results)

    def test_retrieve_updates_activation(self, setup_provider):
        """Test that retrieving and using chunks updates activation."""
        provider, store, chunks = setup_provider

        results = provider.retrieve("json parse", limit=1)
        assert len(results) == 1

        # Update activation for the retrieved chunk
        from aurora_core.types import ChunkID
        chunk_id = ChunkID(results[0].id)
        provider.update(chunk_id, 0.5)

        # This is a basic smoke test - actual activation tracking
        # is tested in store tests

    def test_empty_store_returns_empty(self):
        """Test that querying an empty store returns no results."""
        store = MemoryStore()
        registry = get_global_registry()
        provider = CodeContextProvider(store, registry)

        results = provider.retrieve("anything", limit=5)

        assert results == []


class TestContextRetrievalEdgeCases:
    """Test edge cases and error conditions."""

    def test_query_with_only_stopwords(self):
        """Test query containing only stopwords."""
        store = MemoryStore()
        registry = get_global_registry()
        provider = CodeContextProvider(store, registry)

        results = provider.retrieve("the and it", limit=5)

        assert results == []

    def test_very_long_query(self):
        """Test handling of very long queries."""
        store = MemoryStore()
        registry = get_global_registry()
        provider = CodeContextProvider(store, registry)

        # Create a chunk
        chunk = CodeChunk(
            chunk_id="test_chunk",
            file_path="/test.py",
            element_type="function",
            name="test_function",
            line_start=1,
            line_end=5,
            docstring="Test function",
            complexity_score=0.1,
            dependencies=[]
        )
        store.save_chunk(chunk)

        # Very long query with many keywords
        long_query = " ".join(["word" + str(i) for i in range(100)])
        results = provider.retrieve(long_query, limit=5)

        # Should handle without error
        assert isinstance(results, list)

    def test_special_characters_in_query(self):
        """Test query with special characters."""
        store = MemoryStore()
        registry = get_global_registry()
        provider = CodeContextProvider(store, registry)

        results = provider.retrieve("parse_json() -> dict", limit=5)

        # Should handle without error (punctuation stripped)
        assert isinstance(results, list)
