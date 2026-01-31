"""Unit tests for DocChunk model."""

from datetime import datetime, timezone

import pytest

from aurora_core.chunks import DocChunk


class TestDocChunkCreation:
    """Test DocChunk creation and validation."""

    def test_create_minimal_doc_chunk(self):
        """Test creating a DocChunk with minimal required fields."""
        chunk = DocChunk(
            chunk_id="doc-1",
            file_path="/path/to/manual.pdf",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert chunk.chunk_id == "doc-1"
        assert chunk.type == "doc"
        assert chunk.file_path == "/path/to/manual.pdf"
        assert chunk.page_start == 0
        assert chunk.page_end == 0
        assert chunk.element_type == "section"
        assert chunk.section_level == 0
        assert chunk.document_type == "pdf"

    def test_create_full_doc_chunk(self):
        """Test creating a DocChunk with all fields."""
        timestamp = datetime.now(timezone.utc)

        chunk = DocChunk(
            chunk_id="doc-2",
            file_path="/path/to/manual.pdf",
            page_start=5,
            page_end=7,
            element_type="toc_entry",
            name="2.1 Installation",
            content="To install the software...",
            parent_chunk_id="doc-1",
            section_path=["Chapter 2", "2.1 Installation"],
            section_level=2,
            document_type="pdf",
            embeddings=b"\x00\x01\x02\x03",
            metadata={"author": "John Doe"},
            created_at=timestamp,
            updated_at=timestamp,
        )

        assert chunk.chunk_id == "doc-2"
        assert chunk.type == "doc"
        assert chunk.file_path == "/path/to/manual.pdf"
        assert chunk.page_start == 5
        assert chunk.page_end == 7
        assert chunk.element_type == "toc_entry"
        assert chunk.name == "2.1 Installation"
        assert chunk.content == "To install the software..."
        assert chunk.parent_chunk_id == "doc-1"
        assert chunk.section_path == ["Chapter 2", "2.1 Installation"]
        assert chunk.section_level == 2
        assert chunk.document_type == "pdf"
        assert chunk.embeddings == b"\x00\x01\x02\x03"
        assert chunk.metadata == {"author": "John Doe"}
        assert chunk.created_at == timestamp
        assert chunk.updated_at == timestamp


class TestDocChunkValidation:
    """Test DocChunk validation rules."""

    def test_invalid_element_type(self):
        """Test that invalid element_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid element_type"):
            DocChunk(
                chunk_id="doc-1",
                file_path="/path/to/manual.pdf",
                element_type="invalid_type",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    def test_invalid_document_type(self):
        """Test that invalid document_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid document_type"):
            DocChunk(
                chunk_id="doc-1",
                file_path="/path/to/manual.pdf",
                document_type="invalid_type",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    def test_negative_page_start(self):
        """Test that negative page_start raises ValueError."""
        with pytest.raises(ValueError, match="page_start must be >= 0"):
            DocChunk(
                chunk_id="doc-1",
                file_path="/path/to/manual.pdf",
                page_start=-1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    def test_negative_page_end(self):
        """Test that negative page_end raises ValueError."""
        with pytest.raises(ValueError, match="page_end must be >= 0"):
            DocChunk(
                chunk_id="doc-1",
                file_path="/path/to/manual.pdf",
                page_end=-1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    def test_page_start_greater_than_page_end(self):
        """Test that page_start > page_end raises ValueError."""
        with pytest.raises(ValueError, match="page_start.*must be <= page_end"):
            DocChunk(
                chunk_id="doc-1",
                file_path="/path/to/manual.pdf",
                page_start=10,
                page_end=5,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    def test_negative_section_level(self):
        """Test that negative section_level raises ValueError."""
        with pytest.raises(ValueError, match="section_level must be >= 0"):
            DocChunk(
                chunk_id="doc-1",
                file_path="/path/to/manual.pdf",
                section_level=-1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    def test_valid_element_types(self):
        """Test that all valid element types are accepted."""
        valid_types = ["toc_entry", "section", "paragraph", "table"]
        timestamp = datetime.now(timezone.utc)

        for element_type in valid_types:
            chunk = DocChunk(
                chunk_id=f"doc-{element_type}",
                file_path="/path/to/manual.pdf",
                element_type=element_type,
                created_at=timestamp,
                updated_at=timestamp,
            )
            assert chunk.element_type == element_type

    def test_valid_document_types(self):
        """Test that all valid document types are accepted."""
        valid_types = ["pdf", "docx", "markdown"]
        timestamp = datetime.now(timezone.utc)

        for doc_type in valid_types:
            chunk = DocChunk(
                chunk_id=f"doc-{doc_type}",
                file_path=f"/path/to/file.{doc_type}",
                document_type=doc_type,
                created_at=timestamp,
                updated_at=timestamp,
            )
            assert chunk.document_type == doc_type


class TestDocChunkSerialization:
    """Test DocChunk serialization to/from JSON."""

    def test_to_json_minimal(self):
        """Test serializing minimal DocChunk to JSON."""
        timestamp = datetime.now(timezone.utc)

        chunk = DocChunk(
            chunk_id="doc-1",
            file_path="/path/to/manual.pdf",
            created_at=timestamp,
            updated_at=timestamp,
        )

        json_data = chunk.to_json()

        assert json_data["chunk_id"] == "doc-1"
        assert json_data["type"] == "doc"
        assert json_data["file_path"] == "/path/to/manual.pdf"
        assert json_data["page_start"] == 0
        assert json_data["page_end"] == 0
        assert json_data["element_type"] == "section"
        assert json_data["section_level"] == 0
        assert json_data["document_type"] == "pdf"
        assert json_data["created_at"] == timestamp.isoformat()
        assert json_data["updated_at"] == timestamp.isoformat()

    def test_to_json_full(self):
        """Test serializing full DocChunk to JSON."""
        timestamp = datetime.now(timezone.utc)
        embeddings = b"\x00\x01\x02\x03\x04\x05"

        chunk = DocChunk(
            chunk_id="doc-2",
            file_path="/path/to/manual.pdf",
            page_start=5,
            page_end=7,
            element_type="toc_entry",
            name="2.1 Installation",
            content="Installation instructions...",
            parent_chunk_id="doc-1",
            section_path=["Chapter 2", "2.1 Installation"],
            section_level=2,
            document_type="pdf",
            embeddings=embeddings,
            metadata={"author": "Jane Doe"},
            created_at=timestamp,
            updated_at=timestamp,
        )

        json_data = chunk.to_json()

        assert json_data["chunk_id"] == "doc-2"
        assert json_data["type"] == "doc"
        assert json_data["element_type"] == "toc_entry"
        assert json_data["name"] == "2.1 Installation"
        assert json_data["parent_chunk_id"] == "doc-1"
        assert json_data["section_path"] == ["Chapter 2", "2.1 Installation"]
        assert json_data["section_level"] == 2
        assert json_data["embeddings"] == embeddings.hex()
        assert json_data["metadata"] == {"author": "Jane Doe"}

    def test_from_json_roundtrip(self):
        """Test serialization roundtrip (to_json -> from_json)."""
        timestamp = datetime.now(timezone.utc)

        original_chunk = DocChunk(
            chunk_id="doc-3",
            file_path="/path/to/manual.pdf",
            page_start=10,
            page_end=12,
            element_type="section",
            name="3.1 Configuration",
            content="Configuration details...",
            parent_chunk_id="doc-2",
            section_path=["Chapter 3", "3.1 Configuration"],
            section_level=2,
            document_type="pdf",
            embeddings=b"\x01\x02\x03",
            metadata={"version": "1.0"},
            created_at=timestamp,
            updated_at=timestamp,
        )

        # Serialize to JSON
        json_data = original_chunk.to_json()

        # Deserialize from JSON
        restored_chunk = DocChunk.from_json(json_data)

        # Verify all fields match
        assert restored_chunk.chunk_id == original_chunk.chunk_id
        assert restored_chunk.type == original_chunk.type
        assert restored_chunk.file_path == original_chunk.file_path
        assert restored_chunk.page_start == original_chunk.page_start
        assert restored_chunk.page_end == original_chunk.page_end
        assert restored_chunk.element_type == original_chunk.element_type
        assert restored_chunk.name == original_chunk.name
        assert restored_chunk.content == original_chunk.content
        assert restored_chunk.parent_chunk_id == original_chunk.parent_chunk_id
        assert restored_chunk.section_path == original_chunk.section_path
        assert restored_chunk.section_level == original_chunk.section_level
        assert restored_chunk.document_type == original_chunk.document_type
        assert restored_chunk.embeddings == original_chunk.embeddings
        assert restored_chunk.metadata == original_chunk.metadata
        assert restored_chunk.created_at == original_chunk.created_at
        assert restored_chunk.updated_at == original_chunk.updated_at


class TestDocChunkBreadcrumb:
    """Test DocChunk breadcrumb functionality."""

    def test_get_breadcrumb_with_section_path(self):
        """Test get_breadcrumb with populated section_path."""
        chunk = DocChunk(
            chunk_id="doc-1",
            file_path="/path/to/manual.pdf",
            name="2.1.3 Requirements",
            section_path=["Chapter 2", "2.1 Installation", "2.1.3 Requirements"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        breadcrumb = chunk.get_breadcrumb()
        assert breadcrumb == "Chapter 2 > 2.1 Installation > 2.1.3 Requirements"

    def test_get_breadcrumb_empty_section_path(self):
        """Test get_breadcrumb with empty section_path."""
        chunk = DocChunk(
            chunk_id="doc-1",
            file_path="/path/to/manual.pdf",
            name="Introduction",
            section_path=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        breadcrumb = chunk.get_breadcrumb()
        assert breadcrumb == "Introduction"

    def test_get_breadcrumb_single_level(self):
        """Test get_breadcrumb with single-level section_path."""
        chunk = DocChunk(
            chunk_id="doc-1",
            file_path="/path/to/manual.pdf",
            name="Chapter 1",
            section_path=["Chapter 1"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        breadcrumb = chunk.get_breadcrumb()
        assert breadcrumb == "Chapter 1"


class TestDocChunkRepr:
    """Test DocChunk string representation."""

    def test_repr(self):
        """Test __repr__ output."""
        chunk = DocChunk(
            chunk_id="doc-1",
            file_path="/path/to/manual.pdf",
            page_start=5,
            page_end=10,
            element_type="section",
            name="Installation",
            section_path=["Chapter 2", "Installation"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        repr_str = repr(chunk)
        assert "doc-1" in repr_str
        assert "section" in repr_str
        assert "Chapter 2 > Installation" in repr_str
        assert "5-10" in repr_str
