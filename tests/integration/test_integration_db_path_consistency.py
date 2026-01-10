"""
Integration Test: Database Path Consistency

Tests Issue #2: Database Path Confusion
- Verifies all commands use config-specified database path
- Tests config.get_db_path() is respected by MemoryManager
- Validates data persistence across operations using same DB

This test will FAIL initially because MemoryManager doesn't respect config db_path.

Test Strategy:
- Create custom config with specific db_path
- Initialize MemoryManager with config
- Index files and verify DB created at correct path
- Run stats, search, query operations
- Verify all operations use the SAME database

Expected Failure:
- MemoryManager creates DB at hardcoded path instead of config path
- Different commands may use different database paths
- Data doesn't persist across operations

Related Files:
- packages/cli/src/aurora_cli/config.py (Config class, get_db_path method)
- packages/cli/src/aurora_cli/memory_manager.py (MemoryManager initialization)
- packages/core/src/aurora_core/store/sqlite.py (SQLiteStore)

Phase: 1 (Core Restoration)
Priority: P0 (Critical)
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from aurora_cli.config import Config
from aurora_cli.memory_manager import MemoryManager


class TestDatabasePathConsistency:
    """Test that all operations use the config-specified database path."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create temporary workspace with sample Python files."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create sample Python file
        sample_file = workspace / "example.py"
        sample_file.write_text(
            """
def greet(name):
    \"\"\"Greet a person by name.\"\"\"
    return f"Hello, {name}!"

class Calculator:
    \"\"\"Simple calculator.\"\"\"

    def add(self, a, b):
        \"\"\"Add two numbers.\"\"\"
        return a + b
"""
        )

        return workspace

    @pytest.fixture
    def custom_db_path(self, tmp_path):
        """Return custom database path for testing."""
        db_path = tmp_path / "custom_location" / "test_memory.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path

    @pytest.fixture
    def config_with_custom_path(self, custom_db_path):
        """Create config with custom database path."""
        config = Config(api_key="test-key", db_path=str(custom_db_path), budget_limit=10.0)
        return config

    def test_memory_manager_respects_config_db_path(
        self, config_with_custom_path, custom_db_path, temp_workspace
    ):
        """
        Test that MemoryManager creates database at config-specified path.

        This test will FAIL because MemoryManager doesn't use config.get_db_path().
        Currently, it creates DB at hardcoded path (e.g., ~/.aurora/memory.db).
        """
        # Initialize MemoryManager with custom config
        manager = MemoryManager(config=config_with_custom_path)

        # Index sample files
        manager.index_directory(temp_workspace)

        # ASSERTION 1: Database should exist at custom path
        assert custom_db_path.exists(), (
            f"Database not found at custom path: {custom_db_path}\n"
            f"Expected: DB created at config-specified path\n"
            f"Actual: DB created elsewhere (likely hardcoded path)\n"
            f"Fix: Update MemoryManager.__init__() to use config.get_db_path()"
        )

        # ASSERTION 2: Database should contain indexed chunks
        conn = sqlite3.connect(str(custom_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]
        conn.close()

        assert chunk_count > 0, (
            f"No chunks found in database at {custom_db_path}\n"
            f"Expected: At least 3 chunks from example.py\n"
            f"Actual: {chunk_count} chunks\n"
            f"Possible cause: MemoryManager wrote to different database"
        )

    def test_all_operations_use_same_database(
        self, config_with_custom_path, custom_db_path, temp_workspace
    ):
        """
        Test that stats, search, and retrieval all use the same database.

        This test will FAIL if different operations use different databases.
        """
        # Initialize and index
        manager = MemoryManager(config=config_with_custom_path)
        manager.index_directory(temp_workspace)

        # Get stats (should read from custom DB)
        stats = manager.get_stats()
        stats_chunk_count = stats.get("total_chunks", 0)

        # Query database directly
        conn = sqlite3.connect(str(custom_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        actual_chunk_count = cursor.fetchone()[0]
        conn.close()

        # ASSERTION: Stats should match actual DB content
        assert stats_chunk_count == actual_chunk_count, (
            f"Chunk count mismatch between stats and database\n"
            f"Stats returned: {stats_chunk_count} chunks\n"
            f"Database contains: {actual_chunk_count} chunks\n"
            f"Possible cause: get_stats() reading from different database\n"
            f"Fix: Ensure all MemoryManager methods use same SQLiteStore instance"
        )

    def test_search_uses_config_database(
        self, config_with_custom_path, custom_db_path, temp_workspace
    ):
        """
        Test that search operation uses config-specified database.

        This test will FAIL if search reads from different database.
        """
        # Index data
        manager = MemoryManager(config=config_with_custom_path)
        manager.index_directory(temp_workspace)

        # Perform search
        results = manager.search("calculator", limit=10)

        # ASSERTION 1: Search should return results
        assert len(results) > 0, (
            f"Search returned no results\n"
            f"Expected: At least 1 result for 'calculator'\n"
            f"Actual: {len(results)} results\n"
            f"Possible cause: Search reading from wrong database (no indexed data)"
        )

        # ASSERTION 2: Results should be from indexed file
        found_calculator = any("calculator" in r.content.lower() for r in results)
        assert found_calculator, (
            f"Search results don't contain expected content\n"
            f"Expected: Results about Calculator class\n"
            f"Actual: {[r.name for r in results]}\n"
            f"Possible cause: Search using different database or embedding provider"
        )

    def test_multiple_configs_with_different_paths(self, tmp_path, temp_workspace):
        """
        Test that different configs can use different database paths without interference.

        This test will FAIL if there's a global singleton DB or hardcoded path.
        """
        # Create two different database paths
        db_path_1 = tmp_path / "db1" / "memory.db"
        db_path_2 = tmp_path / "db2" / "memory.db"
        db_path_1.parent.mkdir(parents=True)
        db_path_2.parent.mkdir(parents=True)

        # Create two configs
        config_1 = Config(api_key="test-key", db_path=str(db_path_1), budget_limit=10.0)
        config_2 = Config(api_key="test-key", db_path=str(db_path_2), budget_limit=10.0)

        # Create two managers
        manager_1 = MemoryManager(config=config_1)
        manager_2 = MemoryManager(config=config_2)

        # Index same data to both
        manager_1.index_directory(temp_workspace)
        manager_2.index_directory(temp_workspace)

        # ASSERTION 1: Both databases should exist at their respective paths
        assert db_path_1.exists(), f"Database 1 not found at {db_path_1}"
        assert db_path_2.exists(), f"Database 2 not found at {db_path_2}"

        # ASSERTION 2: Both databases should have data
        conn_1 = sqlite3.connect(str(db_path_1))
        cursor_1 = conn_1.cursor()
        cursor_1.execute("SELECT COUNT(*) FROM chunks")
        count_1 = cursor_1.fetchone()[0]
        conn_1.close()

        conn_2 = sqlite3.connect(str(db_path_2))
        cursor_2 = conn_2.cursor()
        cursor_2.execute("SELECT COUNT(*) FROM chunks")
        count_2 = cursor_2.fetchone()[0]
        conn_2.close()

        assert count_1 > 0, f"Database 1 has no chunks: {count_1}"
        assert count_2 > 0, f"Database 2 has no chunks: {count_2}"
        assert count_1 == count_2, (
            f"Databases should have same chunk count\n"
            f"DB1: {count_1}, DB2: {count_2}\n"
            f"Possible cause: Managers sharing state or using hardcoded path"
        )

    def test_config_get_db_path_expands_tilde(self, tmp_path):
        """
        Test that Config.get_db_path() properly expands ~ in paths.

        This test will FAIL if get_db_path() method doesn't exist or doesn't expand ~.
        """
        # Create config with tilde path
        config = Config(api_key="test-key", db_path="~/.aurora/test_memory.db", budget_limit=10.0)

        # Get expanded path
        expanded_path = config.get_db_path()

        # ASSERTION 1: Method should exist
        assert hasattr(config, "get_db_path"), (
            "Config class missing get_db_path() method\n"
            "Expected: Config.get_db_path() returns expanded absolute path\n"
            "Fix: Add get_db_path() method to Config class in config.py"
        )

        # ASSERTION 2: Path should be expanded (no tilde)
        assert "~" not in expanded_path, (
            f"Path not expanded: {expanded_path}\n"
            f"Expected: Absolute path without tilde\n"
            f"Fix: Use Path.expanduser() in get_db_path()"
        )

        # ASSERTION 3: Path should be absolute
        assert Path(expanded_path).is_absolute(), (
            f"Path not absolute: {expanded_path}\n"
            f"Expected: Absolute path\n"
            f"Fix: Use Path.resolve() or Path.absolute() in get_db_path()"
        )

    def test_config_validation_for_db_path(self):
        """
        Test that Config validates db_path during initialization.

        This test will FAIL if validation doesn't exist or is insufficient.
        """
        # Valid path should work
        config = Config(api_key="test-key", db_path="/tmp/valid/memory.db", budget_limit=10.0)
        assert config.db_path == "/tmp/valid/memory.db"

        # Path validation should accept common formats
        valid_paths = [
            "~/.aurora/memory.db",
            "/tmp/aurora.db",
            "./local_memory.db",
            "../parent_dir/memory.db",
        ]

        for path in valid_paths:
            config = Config(api_key="test-key", db_path=path, budget_limit=10.0)
            assert config.db_path == path, (
                f"Config rejected valid path: {path}\n"
                f"Expected: Path accepted\n"
                f"Fix: Update Config.validate() to accept standard path formats"
            )


class TestDatabaseMigration:
    """Test database migration from old to new paths (Issue #2 fix verification)."""

    @pytest.fixture
    def old_db_path(self, tmp_path):
        """Create old-style database (local aurora.db)."""
        old_db = tmp_path / "aurora.db"

        # Create database with sample data
        conn = sqlite3.connect(str(old_db))
        cursor = conn.cursor()

        # Create tables (simplified)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                name TEXT,
                content TEXT
            )
        """
        )

        # Insert sample data
        cursor.execute(
            "INSERT INTO chunks (id, name, content) VALUES (?, ?, ?)",
            ("chunk1", "test_function", "def test(): pass"),
        )
        conn.commit()
        conn.close()

        return old_db

    @pytest.fixture
    def new_db_path(self, tmp_path):
        """Path for new-style database (~/.aurora/memory.db)."""
        new_db = tmp_path / "new_location" / "memory.db"
        new_db.parent.mkdir(parents=True, exist_ok=True)
        return new_db

    @pytest.mark.skip(reason="Migration logic not yet implemented (task 3.5)")
    def test_detect_old_database(self, old_db_path):
        """
        Test that init command detects old aurora.db files.

        This test is SKIPPED until migration logic is implemented in task 3.5.
        """
        # This will be implemented in task 3.5
        pass

    @pytest.mark.skip(reason="Migration logic not yet implemented (task 3.5)")
    def test_migrate_data_to_new_location(self, old_db_path, new_db_path):
        """
        Test that data is properly migrated from old to new database.

        This test is SKIPPED until migration logic is implemented in task 3.5.
        """
        # This will be implemented in task 3.5
        pass


# Mark all tests in this file with integration marker
pytestmark = pytest.mark.integration
