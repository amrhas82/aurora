"""Integration tests for FTS5 full-text search in SQLiteStore.

Tests use real SQLite databases (tmp_path), no mocks.
"""

import pytest

from aurora_core.store.sqlite import SQLiteStore


def _make_code_chunk(chunk_id, name, signature, docstring, file_path, chunk_type="code"):
    """Create a minimal chunk object for testing."""
    from aurora_core.chunks import CodeChunk

    chunk = CodeChunk(
        chunk_id=chunk_id,
        name=name,
        element_type="function",
        signature=signature,
        docstring=docstring,
        file_path=file_path,
        line_start=1,
        line_end=10,
        language="python",
    )
    # CodeChunk hardcodes type="code"; override for KB chunks
    if chunk_type != "code":
        chunk.type = chunk_type
    return chunk


class TestFTS5SaveAndRetrieve:
    """Test that save_chunk populates FTS5 and retrieve_by_fts finds it."""

    def test_save_chunk_populates_fts5(self, tmp_path):
        """save_chunk() should populate FTS5 index, retrieve_by_fts finds it."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteStore(db_path)

        chunk = _make_code_chunk(
            "code:test.py:authenticate",
            "authenticate",
            "def authenticate(user, password):",
            "Authenticate a user with password.",
            "/test/src/auth.py",
        )
        store.save_chunk(chunk)

        results = store.retrieve_by_fts("authenticate", limit=10)
        assert len(results) >= 1
        assert any(c.id == "code:test.py:authenticate" for c in results)

    def test_fts5_finds_by_docstring(self, tmp_path):
        """FTS5 should match on docstring content."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteStore(db_path)

        chunk = _make_code_chunk(
            "code:test.py:parse_config",
            "parse_config",
            "def parse_config(path):",
            "Parse YAML configuration file and return settings dictionary.",
            "/test/src/config.py",
        )
        store.save_chunk(chunk)

        results = store.retrieve_by_fts("YAML configuration", limit=10)
        assert len(results) >= 1
        assert results[0].id == "code:test.py:parse_config"

    def test_fts5_finds_by_file_path(self, tmp_path):
        """FTS5 should match on file path."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteStore(db_path)

        chunk = _make_code_chunk(
            "code:auth.py:login",
            "login",
            "def login():",
            "Log in.",
            "/test/packages/auth/handler.py",
        )
        store.save_chunk(chunk)

        results = store.retrieve_by_fts("handler", limit=10)
        assert len(results) >= 1

    def test_fts5_rank_attached(self, tmp_path):
        """Retrieved chunks should have fts_rank attribute."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteStore(db_path)

        chunk = _make_code_chunk(
            "code:test.py:func1",
            "func1",
            "def func1():",
            "A test function.",
            "/test/test.py",
        )
        store.save_chunk(chunk)

        results = store.retrieve_by_fts("func1", limit=10)
        assert len(results) >= 1
        assert hasattr(results[0], "fts_rank")
        # FTS5 rank is negative (lower=better)
        assert results[0].fts_rank < 0


class TestFTS5TypeFiltering:
    """Test chunk_type filtering in retrieve_by_fts."""

    def test_type_filter_code(self, tmp_path):
        """Should only return code chunks when type='code'."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteStore(db_path)

        code_chunk = _make_code_chunk(
            "code:test.py:search",
            "search",
            "def search():",
            "Search for items.",
            "/test/search.py",
            chunk_type="code",
        )
        kb_chunk = _make_code_chunk(
            "kb:guide.md:search_section",
            "search_section",
            "## Search",
            "How to search for items in the system.",
            "/test/GUIDE.md",
            chunk_type="kb",
        )
        store.save_chunk(code_chunk)
        store.save_chunk(kb_chunk)

        code_results = store.retrieve_by_fts("search", chunk_type="code")
        assert all(c.type == "code" for c in code_results)

        kb_results = store.retrieve_by_fts("search", chunk_type="kb")
        assert all(c.type == "kb" for c in kb_results)


class TestFTS5Migration:
    """Test auto-migration of existing chunks to FTS5."""

    def test_migration_populates_fts5(self, tmp_path):
        """Chunks created before FTS5 should be migrated on schema init."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteStore(db_path)

        # Save a chunk (populates FTS5 via save_chunk)
        chunk = _make_code_chunk(
            "code:old.py:legacy_func",
            "legacy_func",
            "def legacy_func():",
            "A legacy function.",
            "/test/old.py",
        )
        store.save_chunk(chunk)

        # Manually delete FTS5 data to simulate pre-migration state
        conn = store._get_connection()
        conn.execute("DELETE FROM chunks_fts")
        conn.commit()

        # Verify FTS5 is empty
        cursor = conn.execute("SELECT COUNT(*) FROM chunks_fts")
        assert cursor.fetchone()[0] == 0

        # Trigger migration
        store._migrate_to_fts5()

        # Verify FTS5 is populated
        results = store.retrieve_by_fts("legacy_func", limit=10)
        assert len(results) >= 1
        assert results[0].id == "code:old.py:legacy_func"


class TestFTS5SpecialCharacters:
    """Test that special characters in queries don't crash FTS5."""

    @pytest.mark.parametrize(
        "query",
        [
            "test*query",
            "test-query",
            "test:query",
            "test(query)",
            'test"query',
            "test AND query",
            "test OR query",
            "test NOT query",
            "",
            "   ",
            "a",  # Single char
        ],
    )
    def test_special_chars_dont_crash(self, tmp_path, query):
        """Queries with special characters should not raise exceptions."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteStore(db_path)

        # Should not raise
        results = store.retrieve_by_fts(query, limit=10)
        assert isinstance(results, list)


class TestFTS5Update:
    """Test that updating a chunk updates FTS5."""

    def test_update_chunk_updates_fts(self, tmp_path):
        """Saving a chunk with same ID should update FTS5 entry."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteStore(db_path)

        # Save initial chunk
        chunk1 = _make_code_chunk(
            "code:test.py:myfunc",
            "myfunc",
            "def myfunc():",
            "Original docstring about authentication.",
            "/test/test.py",
        )
        store.save_chunk(chunk1)

        # Update with new content
        chunk2 = _make_code_chunk(
            "code:test.py:myfunc",
            "myfunc",
            "def myfunc():",
            "Updated docstring about database migrations.",
            "/test/test.py",
        )
        store.save_chunk(chunk2)

        # Should find by new content
        results = store.retrieve_by_fts("migrations", limit=10)
        assert len(results) >= 1
        assert results[0].id == "code:test.py:myfunc"

        # Should NOT find by old content (authentication was replaced)
        old_results = store.retrieve_by_fts("authentication", limit=10)
        matching = [c for c in old_results if c.id == "code:test.py:myfunc"]
        assert len(matching) == 0
