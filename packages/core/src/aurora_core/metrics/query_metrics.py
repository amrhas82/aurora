"""Query metrics tracking for SOAR pipeline.

Tracks query execution metrics including duration, complexity, success rate,
and monthly aggregations for `aur mem stats` display.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aurora_core.paths import get_db_path


logger = logging.getLogger(__name__)


@dataclass
class QueryMetricsSummary:
    """Summary of query metrics for display."""

    # Totals
    total_queries: int = 0
    total_soar_queries: int = 0
    total_simple_queries: int = 0

    # Monthly breakdown
    queries_this_month: int = 0
    soar_queries_this_month: int = 0

    # Timing
    avg_duration_ms: float = 0.0
    avg_soar_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0

    # Success
    success_rate: float = 1.0
    failed_queries: int = 0

    # By complexity (this month)
    complexity_breakdown: dict[str, int] = field(default_factory=dict)

    # By model (this month)
    model_breakdown: dict[str, int] = field(default_factory=dict)

    # Recent queries
    last_query_time: str | None = None


class QueryMetrics:
    """Track and aggregate query metrics in SQLite.

    Stores per-query metrics and provides aggregation for monthly reports.
    Uses same database as memory store for simplicity.
    """

    def __init__(self, db_path: str | Path | None = None):
        """Initialize query metrics tracker.

        Args:
            db_path: Path to SQLite database (default: project-local .aurora/memory.db)

        """
        if db_path is None:
            db_path = get_db_path()
        self.db_path = Path(db_path)
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create metrics table if not exists."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS query_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query_id TEXT NOT NULL,
                        query_type TEXT NOT NULL,  -- 'soar', 'simple', 'search'
                        query_text TEXT,
                        complexity TEXT,  -- 'SIMPLE', 'MEDIUM', 'COMPLEX', 'CRITICAL'
                        model TEXT,  -- 'sonnet', 'opus', etc.
                        duration_ms REAL NOT NULL,
                        success INTEGER NOT NULL DEFAULT 1,
                        error_message TEXT,
                        phase_count INTEGER,
                        claude_calls INTEGER,
                        timestamp TEXT NOT NULL,
                        year_month TEXT NOT NULL,  -- 'YYYY-MM' for fast monthly queries
                        metadata TEXT  -- JSON for extensibility
                    )
                """,
                )
                # Index for monthly aggregations
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_query_metrics_year_month
                    ON query_metrics(year_month)
                """,
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_query_metrics_query_type
                    ON query_metrics(query_type)
                """,
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to create query_metrics table: {e}")

    def record_query(
        self,
        query_id: str,
        query_type: str,
        duration_ms: float,
        query_text: str | None = None,
        complexity: str | None = None,
        model: str | None = None,
        success: bool = True,
        error_message: str | None = None,
        phase_count: int | None = None,
        claude_calls: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a query execution metric.

        Args:
            query_id: Unique query identifier
            query_type: Type of query ('soar', 'simple', 'search')
            duration_ms: Execution duration in milliseconds
            query_text: The query text (truncated for storage)
            complexity: Query complexity level
            model: Model used (sonnet, opus, etc.)
            success: Whether query succeeded
            error_message: Error message if failed
            phase_count: Number of SOAR phases executed
            claude_calls: Number of Claude API/CLI calls made
            metadata: Additional metadata as JSON

        """
        try:
            now = datetime.now()
            timestamp = now.isoformat()
            year_month = now.strftime("%Y-%m")

            # Truncate query text for storage
            if query_text and len(query_text) > 500:
                query_text = query_text[:500] + "..."

            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """
                    INSERT INTO query_metrics (
                        query_id, query_type, query_text, complexity, model,
                        duration_ms, success, error_message, phase_count,
                        claude_calls, timestamp, year_month, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        query_id,
                        query_type,
                        query_text,
                        complexity,
                        model,
                        duration_ms,
                        1 if success else 0,
                        error_message,
                        phase_count,
                        claude_calls,
                        timestamp,
                        year_month,
                        json.dumps(metadata) if metadata else None,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to record query metric: {e}")

    def get_summary(self, year_month: str | None = None) -> QueryMetricsSummary:
        """Get aggregated query metrics summary.

        Args:
            year_month: Specific month to query (default: current month)

        Returns:
            QueryMetricsSummary with aggregated stats

        """
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")

        summary = QueryMetricsSummary()

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row

                # Total counts (all time)
                row = conn.execute("SELECT COUNT(*) as total FROM query_metrics").fetchone()
                summary.total_queries = row["total"] if row else 0

                row = conn.execute(
                    "SELECT COUNT(*) as total FROM query_metrics WHERE query_type = 'soar'",
                ).fetchone()
                summary.total_soar_queries = row["total"] if row else 0

                row = conn.execute(
                    "SELECT COUNT(*) as total FROM query_metrics WHERE query_type = 'simple'",
                ).fetchone()
                summary.total_simple_queries = row["total"] if row else 0

                # This month counts
                row = conn.execute(
                    "SELECT COUNT(*) as total FROM query_metrics WHERE year_month = ?",
                    (year_month,),
                ).fetchone()
                summary.queries_this_month = row["total"] if row else 0

                row = conn.execute(
                    "SELECT COUNT(*) as total FROM query_metrics WHERE year_month = ? AND query_type = 'soar'",
                    (year_month,),
                ).fetchone()
                summary.soar_queries_this_month = row["total"] if row else 0

                # Timing stats (all time)
                row = conn.execute(
                    """
                    SELECT
                        AVG(duration_ms) as avg_duration,
                        MIN(duration_ms) as min_duration,
                        MAX(duration_ms) as max_duration
                    FROM query_metrics
                    """,
                ).fetchone()
                if row and row["avg_duration"]:
                    summary.avg_duration_ms = row["avg_duration"]
                    summary.min_duration_ms = row["min_duration"]
                    summary.max_duration_ms = row["max_duration"]

                # SOAR-specific timing
                row = conn.execute(
                    "SELECT AVG(duration_ms) as avg FROM query_metrics WHERE query_type = 'soar'",
                ).fetchone()
                if row and row["avg"]:
                    summary.avg_soar_duration_ms = row["avg"]

                # Success rate
                row = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                    FROM query_metrics
                    """,
                ).fetchone()
                if row and row["total"] > 0:
                    summary.failed_queries = row["failed"]
                    summary.success_rate = 1.0 - (row["failed"] / row["total"])

                # Complexity breakdown (this month)
                rows = conn.execute(
                    """
                    SELECT complexity, COUNT(*) as count
                    FROM query_metrics
                    WHERE year_month = ? AND complexity IS NOT NULL
                    GROUP BY complexity
                    """,
                    (year_month,),
                ).fetchall()
                summary.complexity_breakdown = {row["complexity"]: row["count"] for row in rows}

                # Model breakdown (this month)
                rows = conn.execute(
                    """
                    SELECT model, COUNT(*) as count
                    FROM query_metrics
                    WHERE year_month = ? AND model IS NOT NULL
                    GROUP BY model
                    """,
                    (year_month,),
                ).fetchall()
                summary.model_breakdown = {row["model"]: row["count"] for row in rows}

                # Last query time
                row = conn.execute(
                    "SELECT timestamp FROM query_metrics ORDER BY id DESC LIMIT 1",
                ).fetchone()
                if row:
                    summary.last_query_time = row["timestamp"]

        except Exception as e:
            logger.warning(f"Failed to get query metrics summary: {e}")

        return summary

    def get_monthly_trend(self, months: int = 6) -> list[dict[str, Any]]:
        """Get query counts by month for trend analysis.

        Args:
            months: Number of months to retrieve

        Returns:
            List of dicts with year_month and counts

        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT
                        year_month,
                        COUNT(*) as total,
                        SUM(CASE WHEN query_type = 'soar' THEN 1 ELSE 0 END) as soar_count,
                        AVG(duration_ms) as avg_duration
                    FROM query_metrics
                    GROUP BY year_month
                    ORDER BY year_month DESC
                    LIMIT ?
                    """,
                    (months,),
                ).fetchall()
                return [
                    {
                        "year_month": row["year_month"],
                        "total": row["total"],
                        "soar_count": row["soar_count"],
                        "avg_duration_ms": row["avg_duration"],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"Failed to get monthly trend: {e}")
            return []
