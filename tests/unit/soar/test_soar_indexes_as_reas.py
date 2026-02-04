"""Tests for SOAR conversation log indexing as 'reas' type.

Verifies that SOAR results are indexed with type='reas' (reasoning traces)
instead of 'kb' (knowledge base), allowing them to be filtered separately.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from aurora_soar.orchestrator import SOAROrchestrator


@pytest.fixture
def mock_store():
    """Mock Store for testing."""
    return MagicMock()


@pytest.fixture
def mock_config():
    """Mock Config for testing."""
    config = MagicMock()
    config.get.return_value = {"conversation_logging_enabled": False}
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


@pytest.fixture
def temp_conversation_log():
    """Create a temporary conversation log file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# SOAR Conversation Log\n\n")
        f.write("## Query\n\n")
        f.write("What is 2+2?\n\n")
        f.write("## Response\n\n")
        f.write("The answer is 4.\n\n")
        f.write("## Metadata\n\n")
        f.write("Execution time: 100ms\n")
        f.flush()
        yield Path(f.name)

    Path(f.name).unlink(missing_ok=True)


class TestSOARIndexesAsReas:
    """Tests for SOAR indexing with 'reas' type."""

    def test_conversation_log_chunks_have_reas_type(self, orchestrator, temp_conversation_log):
        """SOAR conversation log chunks should have type='reas'."""
        # Capture chunks saved to store
        saved_chunks = []
        orchestrator.store.save_chunk = MagicMock(side_effect=lambda c: saved_chunks.append(c))

        # Mock embedding provider to avoid actual embedding computation
        with patch("aurora_context_code.semantic.EmbeddingProvider") as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.embed_chunk.return_value = b"\x00" * 384  # Fake embedding
            mock_provider_class.return_value = mock_provider

            # Call the real method
            orchestrator._index_conversation_log(temp_conversation_log)

        # Verify chunks were saved with 'reas' type
        assert len(saved_chunks) >= 1, "Should have saved at least one chunk"
        for chunk in saved_chunks:
            assert chunk.type == "reas", f"Chunk {chunk.id} should have type 'reas', got '{chunk.type}'"

    def test_soar_context_overrides_md_extension(self, orchestrator):
        """SOAR context should override .md extension type ('kb' -> 'reas')."""
        from aurora_core.chunk_types import get_chunk_type

        # Even though file is .md, context should win
        chunk_type = get_chunk_type(file_path="conversation.md", context="soar_result")
        assert chunk_type == "reas"

    def test_reas_type_distinct_from_kb(self):
        """'reas' type should be distinct from 'kb' for filtering purposes."""
        from aurora_core.chunk_types import get_chunk_type

        md_type = get_chunk_type(file_path="readme.md")  # No context
        soar_type = get_chunk_type(file_path="conversation.md", context="soar_result")

        assert md_type == "kb"
        assert soar_type == "reas"
        assert md_type != soar_type
