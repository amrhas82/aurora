"""Tests for _split_large_chunk_by_sections preserving chunk type.

Regression test for the bug where split chunks lost their parent's type,
causing markdown files indexed as 'kb' to become 'code' after splitting.
"""

from unittest.mock import MagicMock, patch

import pytest

from aurora_core.chunks import CodeChunk
from aurora_soar.orchestrator import SOAROrchestrator


@pytest.fixture
def mock_store():
    """Mock Store for testing."""
    return MagicMock()


@pytest.fixture
def mock_config():
    """Mock Config for testing."""
    config = MagicMock()
    config.get.return_value = {}
    return config


@pytest.fixture
def mock_llm():
    """Mock LLMClient for testing."""
    return MagicMock()


@pytest.fixture
def orchestrator(mock_store, mock_config, mock_llm):
    """Create SOAROrchestrator instance for testing."""
    return SOAROrchestrator(
        store=mock_store,
        config=mock_config,
        reasoning_llm=mock_llm,
        solving_llm=mock_llm,
    )


class TestSplitPreservesType:
    """Tests for _split_large_chunk_by_sections type preservation."""

    def test_split_preserves_kb_type(self, orchestrator):
        """Split chunks should preserve parent's 'kb' type."""
        # Create a parent chunk with 'kb' type (like markdown)
        parent = CodeChunk(
            chunk_id="test_kb_chunk",
            file_path="/path/to/doc.md",
            element_type="knowledge",
            name="Test Knowledge",
            line_start=1,
            line_end=100,
            docstring="## Section 1\nContent 1\n\n## Section 2\nContent 2\n\n## Section 3\nContent 3",
            language="markdown",
        )
        parent.type = "kb"  # Override default 'code' type

        # Split into sections
        sections = orchestrator._split_large_chunk_by_sections(parent, max_chars=50)

        # All sections must preserve parent type
        assert len(sections) >= 2, "Should create multiple sections"
        for section in sections:
            assert section.type == "kb", f"Section {section.id} should have type 'kb', got '{section.type}'"

    def test_split_preserves_reas_type(self, orchestrator):
        """Split chunks should preserve parent's 'reas' type."""
        # Create a parent chunk with 'reas' type (SOAR reasoning)
        parent = CodeChunk(
            chunk_id="test_reas_chunk",
            file_path="/path/to/conversation.md",
            element_type="knowledge",
            name="SOAR Conversation",
            line_start=1,
            line_end=100,
            docstring="## Query\nWhat is 2+2?\n\n## Response\nThe answer is 4.\n\n## Metadata\nTiming info",
            language="markdown",
        )
        parent.type = "reas"

        sections = orchestrator._split_large_chunk_by_sections(parent, max_chars=50)

        assert len(sections) >= 2, "Should create multiple sections"
        for section in sections:
            assert section.type == "reas", f"Section {section.id} should have type 'reas', got '{section.type}'"

    def test_split_preserves_code_type(self, orchestrator):
        """Split chunks should preserve parent's 'code' type (default)."""
        parent = CodeChunk(
            chunk_id="test_code_chunk",
            file_path="/path/to/module.py",
            element_type="function",
            name="large_function",
            line_start=1,
            line_end=100,
            docstring="## Part 1\nThis is the first section with enough content to trigger splitting.\n\n## Part 2\nThis is the second section with enough content as well.",
            language="python",
        )
        # Default type is 'code', don't override

        sections = orchestrator._split_large_chunk_by_sections(parent, max_chars=80)

        assert len(sections) >= 2, "Should create multiple sections"
        for section in sections:
            assert section.type == "code", f"Section {section.id} should have type 'code', got '{section.type}'"

    def test_small_chunk_returns_unchanged(self, orchestrator):
        """Chunks under max_chars should return unchanged with original type."""
        parent = CodeChunk(
            chunk_id="small_chunk",
            file_path="/path/to/small.md",
            element_type="knowledge",
            name="Small Doc",
            line_start=1,
            line_end=5,
            docstring="Short content",
            language="markdown",
        )
        parent.type = "kb"

        result = orchestrator._split_large_chunk_by_sections(parent, max_chars=2048)

        assert len(result) == 1
        assert result[0].type == "kb"
        assert result[0] is parent  # Should be same object
