"""Tests for MarkdownParser type determination using central registry.

Verifies that MarkdownParser uses get_chunk_type() from aurora_core.chunk_types
to determine chunk type based on file extension.
"""

import tempfile
from pathlib import Path

import pytest

from aurora_context_code.languages.markdown import MarkdownParser


@pytest.fixture
def parser():
    """Create MarkdownParser instance."""
    return MarkdownParser()


@pytest.fixture
def temp_md_file():
    """Create a temporary markdown file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Test Document\n\n")
        f.write("## Section 1\n\n")
        f.write("This is section 1 content.\n\n")
        f.write("## Section 2\n\n")
        f.write("This is section 2 content.\n")
        f.flush()
        yield Path(f.name)

    # Cleanup
    Path(f.name).unlink(missing_ok=True)


class TestMarkdownParserType:
    """Tests for MarkdownParser chunk type assignment."""

    def test_markdown_chunks_have_kb_type(self, parser, temp_md_file):
        """All chunks from .md files should have type='kb'."""
        chunks = parser.parse(temp_md_file)

        assert len(chunks) >= 1, "Should parse at least one chunk"
        for chunk in chunks:
            assert chunk.type == "kb", f"Chunk {chunk.id} should have type 'kb', got '{chunk.type}'"

    def test_markdown_extension_determines_type(self, parser):
        """File extension should determine chunk type via registry."""
        # Create temp file with .markdown extension
        with tempfile.NamedTemporaryFile(mode="w", suffix=".markdown", delete=False) as f:
            f.write("# Markdown Test\n\n## Content\n\nSome content here.\n")
            f.flush()
            temp_path = Path(f.name)

        try:
            chunks = parser.parse(temp_path)
            assert len(chunks) >= 1
            for chunk in chunks:
                assert chunk.type == "kb"
        finally:
            temp_path.unlink(missing_ok=True)

    def test_type_is_kb_not_code(self, parser, temp_md_file):
        """Markdown chunks should NOT have type='code' (the CodeChunk default)."""
        chunks = parser.parse(temp_md_file)

        for chunk in chunks:
            assert chunk.type != "code", f"Chunk {chunk.id} should not have default type 'code'"

    def test_chunk_metadata_indicates_knowledge(self, parser, temp_md_file):
        """Chunk metadata should indicate it's knowledge content."""
        chunks = parser.parse(temp_md_file)

        for chunk in chunks:
            # Should have is_knowledge flag in metadata
            assert chunk.metadata.get("is_knowledge") is True
            # Should have element_type = 'knowledge'
            assert chunk.element_type == "knowledge"
