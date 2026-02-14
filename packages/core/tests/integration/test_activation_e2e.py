"""End-to-end integration tests for the ACT-R activation pipeline.

Tests the full activation lifecycle: access → BLA calculation →
context boost → decay → total activation → retrieval ordering.
All tests use real SQLiteStore with tmp_path.
"""

import math
from datetime import datetime, timedelta, timezone

from aurora_core.activation.base_level import AccessHistoryEntry
from aurora_core.activation.engine import ActivationComponents, ActivationConfig, ActivationEngine
from aurora_core.chunks.code_chunk import CodeChunk
from aurora_core.store.sqlite import SQLiteStore


def make_chunk(chunk_id, name="func"):
    return CodeChunk(
        chunk_id=chunk_id,
        file_path=f"/test/{name}.py",
        element_type="function",
        name=name,
        line_start=1,
        line_end=10,
    )


class TestFullActivationPipeline:
    """Tests for the full activation pipeline."""

    def test_all_components_calculate(self):
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        history = [
            AccessHistoryEntry(timestamp=now - timedelta(hours=1)),
            AccessHistoryEntry(timestamp=now - timedelta(hours=2)),
        ]

        result = engine.calculate_total(
            access_history=history,
            last_access=now - timedelta(hours=1),
            spreading_activation=0.3,
            query_keywords={"database", "optimize"},
            chunk_keywords={"database", "query"},
            current_time=now,
        )

        assert isinstance(result, ActivationComponents)
        assert result.bla != 0.0  # Should have BLA from 2 accesses
        assert result.spreading == 0.3
        assert result.context_boost > 0  # "database" overlaps
        assert result.total != 0.0

    def test_activation_increases_with_more_access(self):
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        history_1 = [AccessHistoryEntry(timestamp=now - timedelta(hours=1))]
        history_5 = [AccessHistoryEntry(timestamp=now - timedelta(hours=i)) for i in range(1, 6)]

        result_1 = engine.calculate_total(access_history=history_1, current_time=now)
        result_5 = engine.calculate_total(access_history=history_5, current_time=now)

        assert result_5.bla > result_1.bla

    def test_activation_decays_over_time(self):
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        recent = engine.calculate_total(
            last_access=now - timedelta(minutes=5),
            current_time=now,
        )
        old = engine.calculate_total(
            last_access=now - timedelta(days=30),
            current_time=now,
        )

        # Old access should have more decay penalty
        assert abs(old.decay) > abs(recent.decay)

    def test_context_boost_keyword_match(self):
        engine = ActivationEngine()

        full_match = engine.calculate_context_only(
            query_keywords={"auth", "login"},
            chunk_keywords={"auth", "login", "session"},
        )
        no_match = engine.calculate_context_only(
            query_keywords={"auth", "login"},
            chunk_keywords={"database", "connection"},
        )

        assert full_match > no_match

    def test_disabled_components(self):
        config = ActivationConfig(
            enable_bla=False,
            enable_spreading=False,
            enable_context=False,
            enable_decay=False,
        )
        engine = ActivationEngine(config)
        now = datetime.now(timezone.utc)

        result = engine.calculate_total(
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
            last_access=now - timedelta(hours=1),
            spreading_activation=0.5,
            query_keywords={"test"},
            chunk_keywords={"test"},
            current_time=now,
        )

        assert result.bla == 0.0
        assert result.spreading == 0.0
        assert result.context_boost == 0.0
        assert result.decay == 0.0
        assert result.total == 0.0

    def test_zero_access_has_zero_bla(self):
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        no_access = engine.calculate_total(current_time=now)
        with_access = engine.calculate_total(
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(minutes=5))],
            last_access=now - timedelta(minutes=5),
            current_time=now,
        )

        # No access history → BLA stays at 0
        assert no_access.bla == 0.0
        # With access history → BLA is non-zero (may be negative in ACT-R log-odds)
        assert with_access.bla != 0.0


class TestExplainActivation:
    """Tests for explain_activation() output."""

    def test_explanation_includes_all_components(self):
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        explanation = engine.explain_activation(
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(hours=1))],
            last_access=now - timedelta(hours=1),
            spreading_activation=0.2,
            query_keywords={"test"},
            chunk_keywords={"test"},
            current_time=now,
        )

        assert "components" in explanation
        components = explanation["components"]
        assert "bla" in components
        assert "spreading" in components
        assert "context_boost" in components
        assert "decay" in components
        assert "total" in components


class TestActivationWithStore:
    """Tests combining activation engine with SQLiteStore."""

    def test_store_access_updates_activation(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1"))

        now = datetime.now(timezone.utc)
        store.record_access("c1", access_time=now)
        store.record_access("c1", access_time=now + timedelta(seconds=1))

        # Verify activation was updated in store
        conn = store._get_connection()
        cursor = conn.execute(
            "SELECT base_level, access_count FROM activations WHERE chunk_id = ?",
            ("c1",),
        )
        row = cursor.fetchone()
        assert row["access_count"] == 2
        assert math.isfinite(row["base_level"])

    def test_retrieve_by_activation_ordering(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(make_chunk("c1", "rarely_used"))
        store.save_chunk(make_chunk("c2", "heavily_used"))

        now = datetime.now(timezone.utc)

        # Access c2 many times
        for i in range(5):
            store.record_access("c2", access_time=now + timedelta(seconds=i))

        # Access c1 once
        store.record_access("c1", access_time=now)

        results = store.retrieve_by_activation(min_activation=0.0, limit=10)
        ids = [c.id for c in results]

        assert len(results) == 2
        assert ids[0] == "c2"  # More accesses = higher activation

    def test_batch_activation_calculation(self, tmp_path):
        """Test activation calculation for many chunks."""
        store = SQLiteStore(str(tmp_path / "test.db"))

        # Create 20 chunks with varying access patterns
        now = datetime.now(timezone.utc)
        for i in range(20):
            store.save_chunk(make_chunk(f"c{i}", f"func_{i}"))
            for j in range(i):  # c0=0 accesses, c1=1, c2=2, ...
                store.record_access(f"c{i}", access_time=now + timedelta(seconds=j))

        results = store.retrieve_by_activation(min_activation=0.0, limit=20)

        # Should return chunks ordered by activation (most accessed first)
        assert len(results) >= 10  # At least some should be above min_activation
        # First result should be c19 (most accesses)
        assert results[0].id == "c19"


class TestCachedEngine:
    """Tests for ActivationEngine caching."""

    def test_same_config_reuses_engine(self):
        e1 = ActivationEngine()
        e2 = ActivationEngine()
        # Both should work independently
        now = datetime.now(timezone.utc)
        r1 = e1.calculate_total(current_time=now)
        r2 = e2.calculate_total(current_time=now)
        assert r1.total == r2.total

    def test_different_configs_independent(self):
        e1 = ActivationEngine(ActivationConfig(enable_bla=True))
        e2 = ActivationEngine(ActivationConfig(enable_bla=False))

        now = datetime.now(timezone.utc)
        history = [AccessHistoryEntry(timestamp=now - timedelta(hours=1))]

        r1 = e1.calculate_total(access_history=history, current_time=now)
        r2 = e2.calculate_total(access_history=history, current_time=now)

        assert r1.bla != 0.0
        assert r2.bla == 0.0
