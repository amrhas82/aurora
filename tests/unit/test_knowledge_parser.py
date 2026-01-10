"""
Unit tests for KnowledgeParser (knowledge chunk parsing and indexing).

Tests:
- UT-KNOW-01: Parse markdown sections test
- UT-KNOW-02: Extract metadata test (keywords, date)
- UT-KNOW-03: Chunk splitting test
- UT-KNOW-04: Empty file handling
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from aurora_context_code.knowledge_parser import KnowledgeChunk, KnowledgeParser


@pytest.fixture
def sample_conversation_log():
    """Create a sample conversation log for testing."""
    content = """# Semantic Search Discussion

## Context
Discussed implementing BM25 for exact match retrieval to complement semantic search.

## Key Points
- BM25 is better for exact matches (e.g., "SoarOrchestrator")
- Semantic embeddings are better for conceptual queries
- Hybrid approach combines both strengths

## Decision
Implement tri-hybrid: BM25 + Semantic + Activation scoring

## References
- Okapi BM25 parameters: k1=1.5, b=0.75
- Stage 1: BM25 filter (top-100)
- Stage 2: Re-rank with semantic + activation
"""
    return content


@pytest.fixture
def temp_knowledge_file(sample_conversation_log):
    """Create a temporary knowledge file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_semantic_search_bm25.md", delete=False
    ) as f:
        f.write(sample_conversation_log)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


def test_parse_markdown_sections(temp_knowledge_file):
    """UT-KNOW-01: Parse markdown sections into separate chunks."""
    parser = KnowledgeParser()
    chunks = parser.parse_conversation_log(temp_knowledge_file)

    # Should have multiple sections
    assert len(chunks) > 0

    # Each chunk should have content
    for chunk in chunks:
        assert chunk.content
        assert isinstance(chunk, KnowledgeChunk)

    # Should capture section titles
    sections = [chunk.metadata.get("section") for chunk in chunks if chunk.metadata.get("section")]
    assert any("Context" in s or "Key Points" in s or "Decision" in s for s in sections)


def test_extract_metadata_from_filename(temp_knowledge_file):
    """UT-KNOW-02: Extract metadata (keywords, date) from filename."""
    parser = KnowledgeParser()
    chunks = parser.parse_conversation_log(temp_knowledge_file)

    assert len(chunks) > 0

    # Check first chunk has metadata
    first_chunk = chunks[0]
    assert first_chunk.metadata is not None

    # Should extract keywords from filename
    keywords = first_chunk.metadata.get("keywords", [])
    assert isinstance(keywords, list)
    # Filename contains "semantic_search_bm25"
    assert any(kw in ["semantic", "search", "bm25", "semantic_search_bm25"] for kw in keywords)

    # Should have source file
    assert first_chunk.metadata.get("source_file") is not None


def test_chunk_splitting_by_headers(temp_knowledge_file):
    """UT-KNOW-03: Split content by markdown headers (## sections)."""
    parser = KnowledgeParser()
    chunks = parser.parse_conversation_log(temp_knowledge_file)

    # Should have multiple chunks (one per ## section)
    assert len(chunks) >= 3  # At least Context, Key Points, Decision

    # Each chunk should contain only its section content
    for chunk in chunks:
        # Content shouldn't contain multiple ##  headers (each chunk is one section)
        section_count = chunk.content.count("\n## ")
        assert section_count <= 1, f"Chunk has {section_count} sections, should be 1 or 0"


def test_empty_file_handling():
    """UT-KNOW-04: Handle empty files gracefully."""
    parser = KnowledgeParser()

    # Create empty temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        temp_path = Path(f.name)

    try:
        chunks = parser.parse_conversation_log(temp_path)

        # Should return empty list or single empty chunk
        assert isinstance(chunks, list)
        assert len(chunks) == 0 or (len(chunks) == 1 and not chunks[0].content.strip())

    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_knowledge_chunk_structure():
    """Verify KnowledgeChunk has required fields."""
    chunk = KnowledgeChunk(
        content="Test content",
        metadata={
            "keywords": ["test", "knowledge"],
            "source_file": "test.md",
            "section": "Test Section",
        },
    )

    assert chunk.content == "Test content"
    assert chunk.metadata["keywords"] == ["test", "knowledge"]
    assert chunk.metadata["source_file"] == "test.md"
    assert chunk.metadata["section"] == "Test Section"


def test_multiple_files_parsing():
    """Test parsing multiple knowledge files."""
    parser = KnowledgeParser()

    # Create two temp files
    files = []
    try:
        for i, content in enumerate(
            ["# File 1\n## Section A\nContent A", "# File 2\n## Section B\nContent B"]
        ):
            with tempfile.NamedTemporaryFile(mode="w", suffix=f"_file{i}.md", delete=False) as f:
                f.write(content)
                files.append(Path(f.name))

        # Parse each file
        all_chunks = []
        for file_path in files:
            chunks = parser.parse_conversation_log(file_path)
            all_chunks.extend(chunks)

        # Should have chunks from both files
        assert len(all_chunks) >= 2

        # Each chunk should track its source
        sources = set(chunk.metadata.get("source_file") for chunk in all_chunks)
        assert len(sources) == 2

    finally:
        for file_path in files:
            if file_path.exists():
                file_path.unlink()
