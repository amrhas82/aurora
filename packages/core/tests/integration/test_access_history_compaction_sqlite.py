"""End-to-end integration tests: SQLiteStore + access-history compaction.

The pure-function compactor is covered by unit tests in
packages/core/tests/unit/test_access_history_compaction.py. These tests
exercise the full SQLite write path behind the AURORA_COMPACT_ACCESS_HISTORY
feature flag, to verify:

1. With the flag OFF, record_access behaves exactly as before (no shape
   change, no compaction, byte-for-byte compatible).
2. With the flag ON, crossing the compaction threshold triggers bucketing
   and bounds the stored array.
3. BLA continues to reflect the access pattern after compaction happens.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from aurora_core.chunks.code_chunk import CodeChunk
from aurora_core.store.access_history import COMPACTION_TRIGGER_LENGTH
from aurora_core.store.sqlite import SQLiteStore


def _chunk(cid: str) -> CodeChunk:
    return CodeChunk(
        chunk_id=cid,
        file_path=f"/test/{cid}.py",
        element_type="function",
        name=cid,
        line_start=1,
        line_end=10,
    )


def _raw_history(db_path: str, chunk_id: str) -> list[dict]:
    """Read the access_history JSON column directly, bypassing any getters."""
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT access_history FROM activations WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchone()
    conn.close()
    return json.loads(row[0]) if row and row[0] else []


class TestCompactionFlagOff:
    """Default behavior — compaction disabled — must be bit-identical to pre-change."""

    def test_flag_off_does_not_compact(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AURORA_COMPACT_ACCESS_HISTORY", raising=False)
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(_chunk("c1"))

        # Push well past the trigger threshold — should NOT compact.
        now = datetime.now(timezone.utc)
        for i in range(COMPACTION_TRIGGER_LENGTH + 50):
            store.record_access("c1", access_time=now - timedelta(days=30 * (i + 1)))

        raw = _raw_history(str(tmp_path / "test.db"), "c1")
        assert len(raw) == COMPACTION_TRIGGER_LENGTH + 50
        # Pre-compaction shape: no "count" field required.
        assert all("timestamp" in entry for entry in raw)


class TestCompactionFlagOn:
    """With the flag on, crossing the threshold triggers bucketing."""

    def test_flag_on_triggers_compaction_above_threshold(self, tmp_path, monkeypatch):
        """Pre-populate a backdated history so a single real record_access
        crosses the trigger and compacts.

        This mirrors production: real record_access calls use the current
        time, and only chunks with existing long history get compacted.
        """
        monkeypatch.setenv("AURORA_COMPACT_ACCESS_HISTORY", "1")
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))
        store.save_chunk(_chunk("c1"))
        # Seed with one real access to create the activations row.
        store.record_access("c1")

        # Pre-populate access_history directly with 300 backdated entries
        # spanning 2 years — all in the past relative to "now".
        now = datetime.now(timezone.utc)
        backdated = []
        for i in range(COMPACTION_TRIGGER_LENGTH + 100):
            age_days = (720 * i) / (COMPACTION_TRIGGER_LENGTH + 100)
            ts = now - timedelta(days=age_days)
            backdated.append({"timestamp": ts.isoformat(), "context": None})

        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE activations SET access_history = ? WHERE chunk_id = 'c1'",
            (json.dumps(backdated),),
        )
        conn.commit()
        conn.close()

        # One real access at "now" — should trigger compaction on the path.
        store.record_access("c1")

        raw = _raw_history(str(db_path), "c1")
        # After crossing the threshold, the array should have been compacted.
        assert len(raw) < COMPACTION_TRIGGER_LENGTH + 100
        # Some entries should have count > 1 (bucketed from tier 2/3/4).
        bucketed = [e for e in raw if int(e.get("count", 1)) > 1]
        assert len(bucketed) > 0, f"no bucketed entries in {raw}"

    def test_flag_on_below_threshold_does_not_compact(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURORA_COMPACT_ACCESS_HISTORY", "1")
        store = SQLiteStore(str(tmp_path / "test.db"))
        store.save_chunk(_chunk("c1"))

        # 50 accesses — well below the trigger length.
        for _ in range(50):
            store.record_access("c1")

        raw = _raw_history(str(tmp_path / "test.db"), "c1")
        assert len(raw) == 50
        # None should have been bucketed.
        assert all(int(e.get("count", 1)) == 1 for e in raw)

    def test_bla_remains_sensible_after_compaction(self, tmp_path, monkeypatch):
        """A compacted chunk should still have a non-default base_level
        that reflects its access history.

        Uses the backdate-then-trigger pattern: seed the history column with
        a realistic 250-access 50-day spread, then make one real record_access
        to fire compaction on a natural "now".
        """
        monkeypatch.setenv("AURORA_COMPACT_ACCESS_HISTORY", "1")
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))
        store.save_chunk(_chunk("c1"))
        store.record_access("c1")

        now = datetime.now(timezone.utc)
        seeded = []
        for i in range(COMPACTION_TRIGGER_LENGTH + 50):
            ts = now - timedelta(hours=i * 6)
            seeded.append({"timestamp": ts.isoformat(), "context": None})

        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE activations SET access_history = ?, access_count = ? WHERE chunk_id = 'c1'",
            (json.dumps(seeded), len(seeded)),
        )
        conn.commit()
        conn.close()

        # Trigger compaction via a real access.
        store.record_access("c1")

        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT base_level, access_count FROM activations WHERE chunk_id = 'c1'",
        ).fetchone()
        conn.close()
        base_level, access_count = row
        # A chunk accessed 250+ times over 50 days should have a BLA well
        # above the default_activation of -5.0.
        assert base_level > -2.0, f"BLA too low after compaction: {base_level}"
        # access_count is just a counter, not the size of the array.
        assert access_count == COMPACTION_TRIGGER_LENGTH + 51  # +1 for the trigger
