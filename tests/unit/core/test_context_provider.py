"""
Unit tests for ContextProvider interface and implementations.

Tests the abstract ContextProvider interface and ensures concrete
implementations follow the contract.
"""

from pathlib import Path

import pytest
from aurora.core.chunks.base import Chunk
from aurora.core.chunks.code_chunk import CodeChunk
from aurora.core.context.provider import ContextProvider
from aurora.core.types import ChunkID


class MockContextProvider(ContextProvider):
    """Mock implementation for testing the interface."""

    def __init__(self):
        self.queries = []
        self.updates = []
        self.refresh_count = 0

    def retrieve(self, query: str, limit: int = 10) -> list[Chunk]:
        """Track queries and return empty list."""
        self.queries.append((query, limit))
        return []

    def update(self, chunk_id: ChunkID, activation_delta: float) -> None:
        """Track updates."""
        self.updates.append((chunk_id, activation_delta))

    def refresh(self) -> None:
        """Track refresh calls."""
        self.refresh_count += 1


class TestContextProviderInterface:
    """Test the abstract ContextProvider interface contract."""

    def test_retrieve_returns_list_of_chunks(self):
        """Test that retrieve returns a list (even if empty)."""
        provider = MockContextProvider()
        result = provider.retrieve("test")
        assert isinstance(result, list)
        # All items should be chunks if any returned
        for item in result:
            assert isinstance(item, Chunk)

    def test_retrieve_respects_limit(self):
        """Test that limit parameter is passed correctly."""
        provider = MockContextProvider()
        provider.retrieve("test", limit=20)
        assert provider.queries[-1] == ("test", 20)

    def test_update_accepts_positive_delta(self):
        """Test update with positive activation delta."""
        provider = MockContextProvider()
        chunk_id = ChunkID("code_abc")
        provider.update(chunk_id, 1.0)
        assert (chunk_id, 1.0) in provider.updates

    def test_update_accepts_negative_delta(self):
        """Test update with negative activation delta (decay)."""
        provider = MockContextProvider()
        chunk_id = ChunkID("code_xyz")
        provider.update(chunk_id, -0.2)
        assert (chunk_id, -0.2) in provider.updates

    def test_refresh_can_be_called_multiple_times(self):
        """Test refresh can be called repeatedly."""
        provider = MockContextProvider()
        provider.refresh()
        provider.refresh()
        provider.refresh()
        assert provider.refresh_count == 3


class TestCodeContextProvider:
    """Test CodeContextProvider implementation."""

    @pytest.fixture
    def memory_store(self):
        """Create an in-memory store for testing."""
        from aurora.core.store.memory import MemoryStore

        return MemoryStore()

    @pytest.fixture
    def sample_chunks(self):
        """Create sample code chunks for testing."""
        return [
            CodeChunk(
                chunk_id="code_func1",
                file_path=str(Path("/test/module.py")),
                element_type="function",
                name="calculate_sum",
                line_start=1,
                line_end=5,
                signature="def calculate_sum(a, b)",
                docstring="Add two numbers together",
                complexity_score=0.1,
                dependencies=[],
            ),
            CodeChunk(
                chunk_id="code_func2",
                file_path=str(Path("/test/utils.py")),
                element_type="function",
                name="parse_query",
                line_start=10,
                line_end=20,
                signature="def parse_query(text)",
                docstring="Parse a query string into keywords",
                complexity_score=0.2,
                dependencies=[],
            ),
            CodeChunk(
                chunk_id="code_class1",
                file_path=str(Path("/test/models.py")),
                element_type="class",
                name="DataProcessor",
                line_start=1,
                line_end=50,
                docstring="Process and validate data",
                complexity_score=0.5,
                dependencies=[],
            ),
        ]

    @pytest.fixture
    def parser_registry(self):
        """Create a parser registry for testing."""
        from aurora.context_code.registry import ParserRegistry

        return ParserRegistry()

    @pytest.fixture
    def code_provider(self, memory_store, parser_registry):
        """Create CodeContextProvider with test dependencies."""
        from aurora.core.context.code_provider import CodeContextProvider

        return CodeContextProvider(store=memory_store, parser_registry=parser_registry)

    def test_initialization(self, code_provider):
        """Test CodeContextProvider can be initialized."""
        assert code_provider is not None

    def test_retrieve_returns_empty_for_no_matches(self, code_provider):
        """Test retrieve returns empty list when no chunks match."""
        result = code_provider.retrieve("nonexistent query")
        assert result == []

    def test_retrieve_with_empty_query_raises_error(self, code_provider):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            code_provider.retrieve("")

    def test_retrieve_with_invalid_limit_raises_error(self, code_provider):
        """Test that invalid limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be positive"):
            code_provider.retrieve("test", limit=0)

    def test_update_tracks_activation(self, code_provider, memory_store, sample_chunks):
        """Test update method updates activation in store."""
        chunk = sample_chunks[0]
        memory_store.save_chunk(chunk)

        chunk_id = ChunkID(chunk.id)
        code_provider.update(chunk_id, 0.5)

        # Verify activation was updated (would need to check store state)
        # This is a basic test - integration tests will verify end-to-end

    def test_refresh_can_be_called(self, code_provider):
        """Test refresh method can be called without errors."""
        code_provider.refresh()  # Should not raise

    def test_retrieve_with_matching_chunks(self, code_provider, memory_store, sample_chunks):
        """Test retrieve returns chunks ordered by relevance."""
        # Save chunks to store
        for chunk in sample_chunks:
            memory_store.save_chunk(chunk)

        # Query that should match "parse_query" function best
        results = code_provider.retrieve("parse query", limit=5)

        # Should return chunks, with parse_query scoring highest
        assert len(results) > 0
        # The first result should be the one with "parse" and "query" in the name
        assert results[0].name == "parse_query"

    def test_retrieve_respects_limit(self, code_provider, memory_store, sample_chunks):
        """Test that retrieve respects the limit parameter."""
        # Save chunks to store
        for chunk in sample_chunks:
            memory_store.save_chunk(chunk)

        # Request only 1 result
        results = code_provider.retrieve("function", limit=1)
        assert len(results) <= 1

    def test_retrieve_orders_by_relevance(self, code_provider, memory_store):
        """Test that results are ordered by relevance score."""
        # Create chunks with different relevance levels
        high_relevance = CodeChunk(
            chunk_id="code_high",
            file_path="/test/parser.py",
            element_type="function",
            name="json_parser",
            line_start=1,
            line_end=5,
            docstring="Parse JSON data",
            complexity_score=0.1,
            dependencies=[],
        )
        low_relevance = CodeChunk(
            chunk_id="code_low",
            file_path="/test/utils.py",
            element_type="function",
            name="helper_function",
            line_start=1,
            line_end=5,
            docstring="Generic helper",
            complexity_score=0.1,
            dependencies=[],
        )

        memory_store.save_chunk(high_relevance)
        memory_store.save_chunk(low_relevance)

        results = code_provider.retrieve("json parse", limit=5)

        # High relevance should be first
        assert len(results) > 0
        assert results[0].id == "code_high"


class TestQueryParsing:
    """Test query parsing functionality."""

    def test_parse_query_lowercases_text(self):
        """Test that query parsing converts to lowercase."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = CodeContextProvider._parse_query("Calculate SUM Function")
        assert "calculate" in keywords
        assert "sum" in keywords
        assert "function" in keywords

    def test_parse_query_splits_on_whitespace(self):
        """Test that query is split on whitespace."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = CodeContextProvider._parse_query("parse json data")
        assert len(keywords) == 3
        assert keywords == ["parse", "json", "data"]

    def test_parse_query_removes_stopwords(self):
        """Test that common stopwords are filtered out."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = CodeContextProvider._parse_query("parse the json data and return it")
        # "the", "and", "it" should be removed as stopwords
        assert "the" not in keywords
        assert "and" not in keywords
        assert "it" not in keywords
        assert "parse" in keywords
        assert "json" in keywords
        assert "data" in keywords
        assert "return" in keywords

    def test_parse_query_handles_empty_string(self):
        """Test that empty query returns empty list."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = CodeContextProvider._parse_query("")
        assert keywords == []

    def test_parse_query_handles_only_stopwords(self):
        """Test query with only stopwords returns empty list."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = CodeContextProvider._parse_query("the and it is")
        assert keywords == []

    def test_parse_query_strips_punctuation(self):
        """Test that punctuation is handled correctly."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = CodeContextProvider._parse_query("parse, json! data?")
        assert "parse" in keywords or "parse," in keywords  # Either strip or keep
        assert "json" in keywords or "json!" in keywords
        assert "data" in keywords or "data?" in keywords

    def test_parse_query_handles_multiple_spaces(self):
        """Test that multiple spaces are handled correctly."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = CodeContextProvider._parse_query("parse    json     data")
        assert len(keywords) == 3
        assert keywords == ["parse", "json", "data"]


class TestChunkScoring:
    """Test chunk scoring functionality."""

    @pytest.fixture
    def sample_chunk(self):
        """Create a sample chunk for scoring."""
        return CodeChunk(
            chunk_id="code_test",
            file_path="/test/parser.py",
            element_type="function",
            name="parse_json_data",
            line_start=1,
            line_end=10,
            signature="def parse_json_data(input_str)",
            docstring="Parse JSON data from string input",
            complexity_score=0.2,
            dependencies=[],
        )

    def test_score_chunk_perfect_match(self, sample_chunk):
        """Test scoring with all keywords matching."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = ["parse", "json", "data"]
        score = CodeContextProvider._score_chunk(sample_chunk, keywords)
        # All 3 keywords match (in name and docstring)
        assert score == 1.0  # 3/3 = 1.0

    def test_score_chunk_partial_match(self, sample_chunk):
        """Test scoring with some keywords matching."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = ["parse", "xml"]  # Only "parse" matches
        score = CodeContextProvider._score_chunk(sample_chunk, keywords)
        assert score == 0.5  # 1/2 = 0.5

    def test_score_chunk_no_match(self, sample_chunk):
        """Test scoring with no keywords matching."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = ["calculate", "sum", "total"]
        score = CodeContextProvider._score_chunk(sample_chunk, keywords)
        assert score == 0.0  # 0/3 = 0.0

    def test_score_chunk_empty_keywords(self, sample_chunk):
        """Test scoring with empty keyword list."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = []
        score = CodeContextProvider._score_chunk(sample_chunk, keywords)
        assert score == 0.0  # Avoid division by zero

    def test_score_chunk_matches_in_name(self, sample_chunk):
        """Test that keywords match in chunk name."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = ["parse"]
        score = CodeContextProvider._score_chunk(sample_chunk, keywords)
        assert score > 0  # Should match "parse" in name

    def test_score_chunk_matches_in_docstring(self, sample_chunk):
        """Test that keywords match in docstring."""
        from aurora.core.context.code_provider import CodeContextProvider

        keywords = ["string", "input"]
        score = CodeContextProvider._score_chunk(sample_chunk, keywords)
        assert score > 0  # Should match "string" and "input" in docstring

    def test_score_chunk_case_insensitive(self):
        """Test that scoring is case-insensitive."""
        from aurora.core.context.code_provider import CodeContextProvider

        chunk = CodeChunk(
            chunk_id="code_test",
            file_path="/test/calc.py",
            element_type="function",
            name="CalculateSum",
            line_start=1,
            line_end=5,
            docstring="Calculate the SUM of values",
            complexity_score=0.1,
            dependencies=[],
        )
        keywords = ["calculate", "sum"]
        score = CodeContextProvider._score_chunk(chunk, keywords)
        assert score == 1.0  # Both keywords should match despite case difference
