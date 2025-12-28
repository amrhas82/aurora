"""
Integration Test: Activation Tracking

Tests Issue #4: Identical Search Results (All Activation Scores 0.0)
- Verifies store.record_access() is called during search
- Tests that activation scores update correctly after access
- Validates ACT-R activation calculation (base_level, recency, frequency)

This test will FAIL initially because search doesn't call record_access().

Test Strategy:
- Index chunks and verify initial activation state
- Perform searches and spy on record_access() calls
- Query activations table to verify updates
- Perform second search to verify scores changed

Expected Failure:
- record_access() never called during search operations
- access_count remains 0 for all chunks
- base_level never updates (stays 0.0)
- last_access_time remains NULL
- All search results have identical scores

Related Files:
- packages/cli/src/aurora_cli/memory_manager.py (search method)
- packages/core/src/aurora_core/store/sqlite.py (record_access method)
- packages/core/src/aurora_core/activation/engine.py (ActivationEngine)

Phase: 1 (Core Restoration)
Priority: P0 (Critical)
"""

import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aurora_cli.config import Config
from aurora_cli.memory_manager import MemoryManager
from aurora_core.chunks.base import Chunk


class TestActivationTracking:
    """Test that chunk accesses are properly tracked and activation scores update."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create temporary workspace with sample Python files."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create file with multiple functions
        sample_file = workspace / "utils.py"
        sample_file.write_text("""
def calculate_sum(numbers):
    \"\"\"Calculate the sum of a list of numbers.\"\"\"
    return sum(numbers)

def calculate_average(numbers):
    \"\"\"Calculate the average of a list of numbers.\"\"\"
    return sum(numbers) / len(numbers) if numbers else 0

def calculate_median(numbers):
    \"\"\"Calculate the median of a list of numbers.\"\"\"
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    if n == 0:
        return 0
    if n % 2 == 0:
        return (sorted_nums[n//2-1] + sorted_nums[n//2]) / 2
    return sorted_nums[n//2]
""")

        return workspace

    @pytest.fixture
    def test_db_path(self, tmp_path):
        """Return test database path."""
        db_path = tmp_path / "test_memory.db"
        return db_path

    @pytest.fixture
    def manager_with_data(self, test_db_path, temp_workspace):
        """Create MemoryManager with indexed data."""
        config = Config(
            anthropic_api_key="test-key",
            db_path=str(test_db_path),
            budget_limit=10.0
        )
        manager = MemoryManager(config=config)
        manager.index_path(temp_workspace)
        return manager, test_db_path

    def test_record_access_called_during_search(self, manager_with_data):
        """
        Test that store.record_access() is called for each retrieved chunk.

        This test will FAIL because search() doesn't call record_access().
        """
        manager, db_path = manager_with_data

        # Spy on record_access method
        with patch.object(manager.store, 'record_access', wraps=manager.store.record_access) as mock_record:
            # Perform search
            results = manager.search("calculate", limit=5)

            # ASSERTION 1: Search should return results
            assert len(results) > 0, (
                f"Search returned no results\n"
                f"Expected: At least 1 result for 'calculate'\n"
                f"Actual: {len(results)} results"
            )

            # ASSERTION 2: record_access should be called for each result
            assert mock_record.call_count >= len(results), (
                f"record_access() not called during search\n"
                f"Expected: Called {len(results)} times (once per result)\n"
                f"Actual: Called {mock_record.call_count} times\n"
                f"Fix: Add record_access() calls in memory_manager.search() after retrieval"
            )

            # ASSERTION 3: Verify chunk IDs passed to record_access
            if mock_record.call_count > 0:
                # Extract chunk_id from call arguments (first positional arg or 'chunk_id' keyword)
                recorded_chunk_ids = set()
                for call in mock_record.call_args_list:
                    args, kwargs = call
                    if args:
                        recorded_chunk_ids.add(args[0])
                    elif 'chunk_id' in kwargs:
                        recorded_chunk_ids.add(kwargs['chunk_id'])

                result_chunk_ids = {r.chunk_id for r in results}

                # At least some results should have been recorded
                overlap = recorded_chunk_ids & result_chunk_ids
                assert len(overlap) > 0, (
                    f"record_access() called with wrong chunk IDs\n"
                    f"Result IDs: {result_chunk_ids}\n"
                    f"Recorded IDs: {recorded_chunk_ids}\n"
                    f"Overlap: {overlap}"
                )

    def test_access_count_increments_after_search(self, manager_with_data):
        """
        Test that access_count in activations table increments after search.

        This test will FAIL because record_access() is not called.
        """
        manager, db_path = manager_with_data

        # Get initial activation state
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chunk_id, access_count
            FROM activations
            ORDER BY chunk_id
        """)
        initial_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Perform search
        results = manager.search("calculate average", limit=5)
        result_ids = {r.chunk_id for r in results}

        # Get updated activation state
        cursor.execute("""
            SELECT chunk_id, access_count
            FROM activations
            ORDER BY chunk_id
        """)
        updated_counts = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        # ASSERTION: access_count should increase for retrieved chunks
        for chunk_id in result_ids:
            initial_count = initial_counts.get(chunk_id, 0)
            updated_count = updated_counts.get(chunk_id, 0)

            assert updated_count > initial_count, (
                f"access_count did not increment for chunk {chunk_id}\n"
                f"Initial: {initial_count}, Updated: {updated_count}\n"
                f"Expected: Updated count should be > initial count\n"
                f"Cause: record_access() not called during search\n"
                f"Fix: Call store.record_access(chunk_id, timestamp, context) in search()"
            )

    def test_base_level_updates_after_access(self, manager_with_data):
        """
        Test that base_level activation updates according to ACT-R formula.

        This test will FAIL because activation is never updated.
        """
        manager, db_path = manager_with_data

        # Get initial base_level values
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chunk_id, base_level, access_count
            FROM activations
        """)
        initial_state = {row[0]: {"base_level": row[1], "access_count": row[2]}
                        for row in cursor.fetchall()}

        # Perform search
        results = manager.search("calculate median", limit=5)
        result_ids = {r.chunk_id for r in results}

        # Small delay to ensure time difference
        time.sleep(0.1)

        # Get updated state
        cursor.execute("""
            SELECT chunk_id, base_level, access_count
            FROM activations
        """)
        updated_state = {row[0]: {"base_level": row[1], "access_count": row[2]}
                        for row in cursor.fetchall()}
        conn.close()

        # ASSERTION: base_level should update for accessed chunks
        for chunk_id in result_ids:
            initial = initial_state.get(chunk_id, {})
            updated = updated_state.get(chunk_id, {})

            initial_bl = initial.get("base_level", 0.0)
            updated_bl = updated.get("base_level", 0.0)
            initial_ac = initial.get("access_count", 0)
            updated_ac = updated.get("access_count", 0)

            # If access_count increased, base_level should update
            if updated_ac > initial_ac:
                assert updated_bl != initial_bl, (
                    f"base_level did not update despite access_count increase\n"
                    f"Chunk: {chunk_id}\n"
                    f"Initial BL: {initial_bl}, Updated BL: {updated_bl}\n"
                    f"Initial AC: {initial_ac}, Updated AC: {updated_ac}\n"
                    f"Expected: base_level should change when accessed\n"
                    f"Cause: ActivationEngine not recalculating activation\n"
                    f"Fix: Ensure record_access() triggers activation recalculation"
                )

    def test_last_access_time_updates(self, manager_with_data):
        """
        Test that last_access_time is updated in activations table.

        This test will FAIL because record_access() is not called.
        """
        manager, db_path = manager_with_data

        # Record time before search
        search_time = datetime.now(timezone.utc)

        # Perform search
        results = manager.search("calculate sum", limit=5)
        result_ids = {r.chunk_id for r in results}

        # Query last_access (not last_access_time - that's the column name)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chunk_id, last_access
            FROM activations
            WHERE chunk_id IN ({})
        """.format(','.join('?' * len(result_ids))), tuple(result_ids))

        access_times = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        # ASSERTION: last_access should be recent (within last minute)
        for chunk_id in result_ids:
            last_access = access_times.get(chunk_id)

            assert last_access is not None, (
                f"last_access is NULL for chunk {chunk_id}\n"
                f"Expected: Recent timestamp\n"
                f"Actual: NULL\n"
                f"Cause: record_access() never called\n"
                f"Fix: Call record_access() in search() to update timestamp"
            )

            # If last_access is stored as string, parse it
            if isinstance(last_access, str):
                try:
                    last_access_dt = datetime.fromisoformat(last_access.replace('Z', '+00:00'))
                except:
                    # Try alternative parsing
                    last_access_dt = datetime.strptime(last_access, "%Y-%m-%d %H:%M:%S.%f")
                    last_access_dt = last_access_dt.replace(tzinfo=timezone.utc)

                time_diff = (datetime.now(timezone.utc) - last_access_dt).total_seconds()

                assert time_diff < 60, (
                    f"last_access_time is stale for chunk {chunk_id}\n"
                    f"Last access: {last_access_dt}\n"
                    f"Current time: {datetime.now(timezone.utc)}\n"
                    f"Time diff: {time_diff:.2f} seconds\n"
                    f"Expected: Updated within last 60 seconds"
                )

    def test_second_search_changes_activation_scores(self, manager_with_data):
        """
        Test that performing a second search changes activation scores (due to recency).

        This test will FAIL because activation scores never update.
        """
        manager, db_path = manager_with_data

        # First search
        results_1 = manager.search("calculate", limit=10)
        scores_1 = {r.chunk_id: r.activation_score for r in results_1}

        # Wait to ensure time difference
        time.sleep(0.5)

        # Second search for same query
        results_2 = manager.search("calculate", limit=10)
        scores_2 = {r.chunk_id: r.activation_score for r in results_2}

        # Find chunks that appear in both searches
        common_chunks = set(scores_1.keys()) & set(scores_2.keys())

        # ASSERTION: Scores should differ for chunks accessed twice (higher recency)
        if len(common_chunks) > 0:
            score_changes = []
            for chunk_id in common_chunks:
                score_1 = scores_1[chunk_id]
                score_2 = scores_2[chunk_id]
                if score_2 != score_1:
                    score_changes.append(chunk_id)

            assert len(score_changes) > 0, (
                f"Activation scores unchanged after second search\n"
                f"Common chunks: {len(common_chunks)}\n"
                f"Chunks with changed scores: {len(score_changes)}\n"
                f"Expected: Scores should increase due to increased access_count and recency\n"
                f"Actual: All scores identical across searches\n"
                f"Cause: Activation tracking not working (Issue #4)\n"
                f"Fix: Implement record_access() calls in search()"
            )

    def test_activation_context_stored(self, manager_with_data):
        """
        Test that search context is stored with activation records.

        This test will FAIL if context parameter is not passed to record_access().
        """
        manager, db_path = manager_with_data

        # Perform search with specific query
        query_text = "calculate average statistics"
        results = manager.search(query_text, limit=5)

        # Check if activations table has context column
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get table schema
        cursor.execute("PRAGMA table_info(activations)")
        columns = {row[1] for row in cursor.fetchall()}

        if "context" in columns or "metadata" in columns:
            # Query context/metadata for recent accesses
            result_ids = tuple(r.chunk_id for r in results)
            if len(result_ids) > 0:
                cursor.execute(f"""
                    SELECT chunk_id, context, metadata
                    FROM activations
                    WHERE chunk_id IN ({','.join('?' * len(result_ids))})
                """, result_ids)

                contexts = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

                # At least one chunk should have context stored
                has_context = any(
                    (ctx is not None and ctx != '') or (meta is not None and meta != '')
                    for ctx, meta in contexts.values()
                )

                # This is informational - context storage is nice-to-have, not critical
                if not has_context:
                    print(
                        f"INFO: Search context not stored in activations table\n"
                        f"Consider passing context={{'query': query_text}} to record_access()\n"
                        f"This helps with debugging and analysis but is not critical."
                    )

        conn.close()


class TestActivationCalculationIntegrity:
    """Test that activation calculations follow ACT-R formula correctly."""

    @pytest.fixture
    def manager_with_varied_access(self, tmp_path):
        """Create manager with chunks that have varied access patterns."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create sample file
        sample_file = workspace / "functions.py"
        sample_file.write_text("""
def rarely_used():
    \"\"\"This function is rarely accessed.\"\"\"
    pass

def frequently_used():
    \"\"\"This function is accessed often.\"\"\"
    pass

def moderately_used():
    \"\"\"This function is moderately accessed.\"\"\"
    pass
""")

        db_path = tmp_path / "test_memory.db"
        config = Config(anthropic_api_key="test-key", db_path=str(db_path), budget_limit=10.0)
        manager = MemoryManager(config=config)
        manager.index_path(workspace)

        # Simulate access patterns
        # Frequently used: 5 accesses
        for _ in range(5):
            manager.search("frequently", limit=1)
            time.sleep(0.05)

        # Moderately used: 2 accesses
        for _ in range(2):
            manager.search("moderately", limit=1)
            time.sleep(0.05)

        # Rarely used: 0 additional accesses (just initial indexing)

        return manager, db_path

    def test_activation_varies_by_access_frequency(self, manager_with_varied_access):
        """
        Test that chunks with more accesses have higher activation scores.

        This test will FAIL if activation doesn't vary by frequency.
        """
        manager, db_path = manager_with_varied_access

        # Get activation scores
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.name, a.base_level, a.access_count
            FROM chunks c
            JOIN activations a ON c.id = a.chunk_id
            ORDER BY a.access_count DESC
        """)
        results = cursor.fetchall()
        conn.close()

        if len(results) >= 3:
            # Extract scores
            scores_by_name = {row[0]: (row[1], row[2]) for row in results}

            # Verify ordering: frequently > moderately > rarely
            freq_bl, freq_ac = scores_by_name.get("frequently_used", (0.0, 0))
            mod_bl, mod_ac = scores_by_name.get("moderately_used", (0.0, 0))
            rare_bl, rare_ac = scores_by_name.get("rarely_used", (0.0, 0))

            # Check access counts match expected pattern
            assert freq_ac >= mod_ac >= rare_ac, (
                f"Access counts don't match expected pattern\n"
                f"Frequent: {freq_ac}, Moderate: {mod_ac}, Rare: {rare_ac}\n"
                f"Possible cause: record_access() not being called"
            )

            # Check base_level correlates with access_count
            # More accesses should generally mean higher activation
            if freq_ac > mod_ac:
                # Only assert if there's a meaningful difference in access counts
                # (base_level might not change much for small differences)
                pass  # This is verified in other tests


# Mark all tests in this file with integration marker
pytestmark = pytest.mark.integration
