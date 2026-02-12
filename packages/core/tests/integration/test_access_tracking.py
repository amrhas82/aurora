"""Integration tests for SQLiteStore access tracking.

Tests the full access lifecycle: record_access, get_access_history,
get_access_stats, get_access_stats_batch, save_doc_chunk, and
schema version detection. All tests use real SQLite with tmp_path.
"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from aurora_core.chunks.code_chunk import CodeChunk
from aurora_core.chunks.doc_chunk import DocChunk
from aurora_core.exceptions import ChunkNotFoundError, SchemaMismatchError
from aurora_core.store.sqlite import SQLiteStore


def make_chunk(chunk_id: str, name: str = "func") -> CodeChunk:
    """Helper to create a minimal CodeChunk."""
    return CodeChunk(
        chunk_id=chunk_id,
        file_path=f"/test/{name}.py",
        element_type="function",
        name=name,
        line_start=1,
        line_end=10,
    )


class TestRecordAccess:
    """Tests for SQLiteStore.record_access()."""

    def test_record_access_creates_history_entry(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        store.record_access("c1")

        history = store.get_access_history("c1")
        assert len(history) == 1
        assert "timestamp" in history[0]

    def test_record_access_increments_count(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        store.record_access("c1")
        store.record_access("c1")
        store.record_access("c1")

        stats = store.get_access_stats("c1")
        assert stats["access_count"] == 3

    def test_record_access_updates_last_access_time(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 2, tzinfo=timezone.utc)

        store.record_access("c1", access_time=t1)
        store.record_access("c1", access_time=t2)

        stats = store.get_access_stats("c1")
        # last_access should be the more recent timestamp
        assert "2026-01-02" in str(stats["last_access"])

    def test_record_access_updates_bla(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        now = datetime.now(timezone.utc)
        store.record_access("c1", access_time=now)

        # After one access, chunk should have activation in the activations table
        conn = store._get_connection()
        cursor = conn.execute(
            "SELECT base_level FROM activations WHERE chunk_id = ?", ("c1",)
        )
        row = cursor.fetchone()
        assert row is not None
        # BLA should be a finite number (could be negative in ACT-R log-odds)
        assert row["base_level"] is not None
        import math
        assert math.isfinite(row["base_level"])

    def test_record_access_with_context(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        store.record_access("c1", context="search query: activation")

        history = store.get_access_history("c1")
        assert history[0]["context"] == "search query: activation"

    def test_record_access_nonexistent_chunk_raises(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        # Force schema init by saving a chunk then testing with a different ID
        store.save_chunk(make_chunk("other"))

        with pytest.raises(ChunkNotFoundError):
            store.record_access("nonexistent")

    def test_record_access_multiple_updates_bla(self, tmp_path):
        """More accesses should increase BLA (more evidence = higher activation)."""
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        now = datetime.now(timezone.utc)
        store.record_access("c1", access_time=now)

        conn = store._get_connection()
        cursor = conn.execute(
            "SELECT base_level FROM activations WHERE chunk_id = ?", ("c1",)
        )
        bla_after_1 = cursor.fetchone()["base_level"]

        store.record_access("c1", access_time=now + timedelta(seconds=1))

        cursor = conn.execute(
            "SELECT base_level FROM activations WHERE chunk_id = ?", ("c1",)
        )
        bla_after_2 = cursor.fetchone()["base_level"]

        # More accesses should increase base level activation
        assert bla_after_2 > bla_after_1


class TestGetAccessHistory:
    """Tests for SQLiteStore.get_access_history()."""

    def test_returns_ordered_most_recent_first(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
        t3 = datetime(2026, 1, 3, tzinfo=timezone.utc)

        store.record_access("c1", access_time=t1)
        store.record_access("c1", access_time=t2)
        store.record_access("c1", access_time=t3)

        history = store.get_access_history("c1")
        assert len(history) == 3
        # Most recent first
        assert t3.isoformat() in history[0]["timestamp"]
        assert t1.isoformat() in history[2]["timestamp"]

    def test_with_limit(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        for i in range(5):
            store.record_access("c1")

        history = store.get_access_history("c1", limit=2)
        assert len(history) == 2

    def test_empty_history(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        history = store.get_access_history("c1")
        assert history == []

    def test_nonexistent_chunk_raises(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("other"))

        with pytest.raises(ChunkNotFoundError):
            store.get_access_history("nonexistent")


class TestGetAccessStats:
    """Tests for SQLiteStore.get_access_stats() and get_access_stats_batch()."""

    def test_all_fields_populated(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))
        store.record_access("c1")

        stats = store.get_access_stats("c1")
        assert stats["access_count"] == 1
        assert stats["last_access"] is not None
        assert stats["first_access"] is not None
        assert stats["created_at"] is not None

    def test_no_accesses_returns_zero_count(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        stats = store.get_access_stats("c1")
        assert stats["access_count"] == 0
        assert stats["last_access"] is None

    def test_nonexistent_chunk_raises(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("other"))

        with pytest.raises(ChunkNotFoundError):
            store.get_access_stats("nonexistent")

    def test_batch_returns_all_requested(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1", "func1"))
        store.save_chunk(make_chunk("c2", "func2"))
        store.save_chunk(make_chunk("c3", "func3"))

        store.record_access("c1")
        store.record_access("c2")

        stats = store.get_access_stats_batch(["c1", "c2", "c3"])
        assert len(stats) == 3
        assert stats["c1"]["access_count"] == 1
        assert stats["c2"]["access_count"] == 1
        assert stats["c3"]["access_count"] == 0

    def test_batch_missing_chunks_excluded(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        stats = store.get_access_stats_batch(["c1", "nonexistent"])
        assert "c1" in stats
        assert "nonexistent" not in stats

    def test_batch_empty_input(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        stats = store.get_access_stats_batch([])
        assert stats == {}


class TestAccessLifecycle:
    """End-to-end tests for the full access tracking lifecycle."""

    def test_save_access_retrieve_by_activation(self, tmp_path):
        """Full lifecycle: save chunks → access some → retrieve ordered by activation."""
        store = SQLiteStore(str(tmp_path / "test.db"))

        # Save 3 chunks
        store.save_chunk(make_chunk("c1", "rarely_used"))
        store.save_chunk(make_chunk("c2", "heavily_used"))
        store.save_chunk(make_chunk("c3", "moderately_used"))

        now = datetime.now(timezone.utc)

        # Access c2 many times (should have highest activation)
        for i in range(5):
            store.record_access("c2", access_time=now + timedelta(seconds=i))

        # Access c3 a few times
        for i in range(2):
            store.record_access("c3", access_time=now + timedelta(seconds=i))

        # Access c1 once
        store.record_access("c1", access_time=now)

        # Retrieve by activation — c2 should be first (most accesses)
        results = store.retrieve_by_activation(min_activation=0.0, limit=10)
        chunk_ids = [c.id for c in results]

        assert len(results) == 3
        # c2 (5 accesses) should rank highest
        assert chunk_ids[0] == "c2"


class TestSaveDocChunk:
    """Tests for SQLiteStore.save_doc_chunk()."""

    def test_saves_with_hierarchy_metadata(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))

        # Save parent chunk first (FK constraint)
        parent = DocChunk(
            chunk_id="doc:manual:ch2-root",
            file_path="/docs/manual.pdf",
            page_start=1,
            page_end=10,
            element_type="section",
            name="Chapter 2",
            content="Chapter 2 content",
            section_path=["Chapter 2"],
            section_level=1,
            document_type="pdf",
        )
        store.save_doc_chunk(parent)

        chunk = DocChunk(
            chunk_id="doc:manual:ch2",
            file_path="/docs/manual.pdf",
            page_start=5,
            page_end=7,
            element_type="section",
            name="2.1 Installation",
            content="To install the software, run pip install...",
            parent_chunk_id="doc:manual:ch2-root",
            section_path=["Chapter 2", "2.1 Installation"],
            section_level=2,
            document_type="pdf",
        )

        result = store.save_doc_chunk(chunk)
        assert result is True

        # Verify chunk is retrievable
        retrieved = store.get_chunk("doc:manual:ch2")
        assert retrieved is not None
        assert retrieved.id == "doc:manual:ch2"

        # Verify hierarchy metadata was stored
        conn = store._get_connection()
        cursor = conn.execute(
            "SELECT * FROM doc_hierarchy WHERE chunk_id = ?", ("doc:manual:ch2",)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["parent_chunk_id"] == "doc:manual:ch2-root"
        assert row["section_level"] == 2
        assert row["document_type"] == "pdf"

    def test_rejects_non_doc_chunk(self, tmp_path):
        from aurora_core.exceptions import ValidationError

        store = SQLiteStore(str(tmp_path / "test.db"))
        code_chunk = make_chunk("c1")

        with pytest.raises(ValidationError):
            store.save_doc_chunk(code_chunk)


class TestSchemaDetection:
    """Tests for schema version detection."""

    def test_fresh_db_returns_current_version(self, tmp_path):
        import sqlite3

        from aurora_core.store.schema import SCHEMA_VERSION

        store = SQLiteStore(str(tmp_path / "test.db"))
        # Trigger schema init
        store.save_chunk(make_chunk("c1"))

        version, cols = store._detect_schema_version()
        assert version == SCHEMA_VERSION
        assert cols > 0

    def test_legacy_7col_raises_schema_mismatch(self, tmp_path):
        import sqlite3

        db_path = tmp_path / "legacy.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE chunks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content JSON NOT NULL,
                metadata JSON,
                embeddings BLOB,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        store = SQLiteStore(str(db_path))
        with pytest.raises(SchemaMismatchError):
            store._get_connection()

    def test_no_chunks_table_initializes_fresh(self, tmp_path):
        import sqlite3

        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE other (id TEXT)")
        conn.commit()
        conn.close()

        # Should succeed - no chunks table means fresh DB, schema gets created
        store = SQLiteStore(str(db_path))
        store.save_chunk(make_chunk("c1"))
        retrieved = store.get_chunk("c1")
        assert retrieved is not None
