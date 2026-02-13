"""Integration tests verifying production code integrity after deadcode cleanup.

After removing ~9,378 lines of dead code across 63 files (commit 0b47ef8),
these tests ensure the remaining production code still works correctly.

Focus areas:
1. Modified production code paths (engine.explain_activation, connection_pool.clear_pool)
2. Package __init__.py exports still resolve
3. Removed symbols no longer accessible (regression guard)
4. Core APIs that depend on modified modules
"""

import sqlite3
import threading
from datetime import datetime, timedelta, timezone

import pytest

from aurora_core.activation.decay import (
    AGGRESSIVE_DECAY,
    DECAY_BY_TYPE,
    GENTLE_DECAY,
    MODERATE_DECAY,
    DecayCalculator,
    DecayConfig,
    calculate_decay,
)
from aurora_core.activation.engine import (
    AGGRESSIVE_CONFIG,
    BLA_FOCUSED_CONFIG,
    CONSERVATIVE_CONFIG,
    CONTEXT_FOCUSED_CONFIG,
    DEFAULT_CONFIG,
    ActivationComponents,
    ActivationConfig,
    ActivationEngine,
    get_cached_engine,
)
from aurora_core.activation.base_level import AccessHistoryEntry
from aurora_core.store.connection_pool import ConnectionPool, get_connection_pool


# ============================================================
# 1. engine.explain_activation — decay_details uses calculate()
# ============================================================


class TestExplainActivationDecayDetails:
    """Verify explain_activation returns correct decay_details after cleanup.

    The cleanup changed decay_details from explain_decay() dict to
    {"penalty": decay_value} using calculate() directly.
    """

    def test_decay_details_has_penalty_key(self):
        """decay_details must contain 'penalty' key."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)
        last_access = now - timedelta(days=10)

        explanation = engine.explain_activation(
            last_access=last_access,
            current_time=now,
        )

        assert "decay_details" in explanation
        assert "penalty" in explanation["decay_details"]

    def test_decay_details_penalty_matches_calculate(self):
        """decay_details['penalty'] must match decay_calculator.calculate()."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)
        last_access = now - timedelta(days=10)

        explanation = engine.explain_activation(
            last_access=last_access,
            current_time=now,
        )

        expected = engine.decay_calculator.calculate(last_access, now)
        assert explanation["decay_details"]["penalty"] == pytest.approx(expected, abs=1e-9)

    def test_decay_details_penalty_is_negative_for_old_access(self):
        """penalty should be negative for accesses older than grace period + 1 day."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)
        last_access = now - timedelta(days=30)

        explanation = engine.explain_activation(
            last_access=last_access,
            current_time=now,
        )

        assert explanation["decay_details"]["penalty"] < 0.0

    def test_decay_details_penalty_zero_within_grace_period(self):
        """penalty should be 0.0 for very recent accesses."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)
        last_access = now - timedelta(minutes=30)  # within 1h grace

        explanation = engine.explain_activation(
            last_access=last_access,
            current_time=now,
        )

        assert explanation["decay_details"]["penalty"] == 0.0

    def test_explain_no_old_explain_decay_keys(self):
        """Ensure old explain_decay() dict keys are NOT in decay_details.

        Before cleanup, explain_decay() returned a richer dict with keys like
        'hours_since_access', 'days_since_access', 'formula', etc.
        After cleanup, only 'penalty' should exist.
        """
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)
        last_access = now - timedelta(days=5)

        explanation = engine.explain_activation(
            last_access=last_access,
            current_time=now,
        )

        details = explanation["decay_details"]
        assert set(details.keys()) == {"penalty"}


# ============================================================
# 2. ConnectionPool.clear_pool(db_path=None)
# ============================================================


class TestConnectionPoolClearPool:
    """Verify clear_pool works with optional db_path parameter."""

    def test_clear_pool_specific_db(self, tmp_path):
        """clear_pool(db_path) clears only that database's connections."""
        pool = ConnectionPool()
        db1 = str(tmp_path / "test1.db")
        db2 = str(tmp_path / "test2.db")

        conn1, _ = pool.get_connection(db1)
        conn2, _ = pool.get_connection(db2)
        pool._pools[db1] = [conn1]
        pool._pools[db2] = [conn2]

        pool.clear_pool(db1)

        assert db1 not in pool._pools
        assert db2 in pool._pools

    def test_clear_pool_all(self, tmp_path):
        """clear_pool(None) clears all connections."""
        pool = ConnectionPool()
        db1 = str(tmp_path / "test1.db")
        db2 = str(tmp_path / "test2.db")

        conn1, _ = pool.get_connection(db1)
        conn2, _ = pool.get_connection(db2)
        pool._pools[db1] = [conn1]
        pool._pools[db2] = [conn2]

        pool.clear_pool()

        assert len(pool._pools) == 0
        assert len(pool._locks) == 0

    def test_clear_pool_nonexistent_db(self):
        """clear_pool for nonexistent db_path is a no-op."""
        pool = ConnectionPool()
        pool.clear_pool("/nonexistent/path.db")  # Should not raise

    def test_get_connection_pool_singleton(self):
        """get_connection_pool returns same instance."""
        pool1 = get_connection_pool()
        pool2 = get_connection_pool()
        assert pool1 is pool2

    def test_connection_pool_get_and_clear_roundtrip(self, tmp_path):
        """Full roundtrip: get connection, return to pool, clear."""
        pool = ConnectionPool()
        db_path = str(tmp_path / "roundtrip.db")

        conn, is_new = pool.get_connection(db_path)
        assert is_new is True

        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()

        pool.clear_pool(db_path)

        conn2, is_new2 = pool.get_connection(db_path)
        assert is_new2 is True
        result = conn2.execute("SELECT * FROM test").fetchall()
        assert len(result) == 1


# ============================================================
# 3. Package __init__.py export integrity
# ============================================================


class TestActivationPackageExports:
    """Verify activation package exports all expected symbols."""

    def test_all_engine_exports_importable(self):
        from aurora_core.activation import (
            ActivationComponents,
            ActivationConfig,
            ActivationEngine,
            AGGRESSIVE_CONFIG,
            BLA_FOCUSED_CONFIG,
            CONSERVATIVE_CONFIG,
            CONTEXT_FOCUSED_CONFIG,
            DEFAULT_CONFIG,
        )
        assert ActivationEngine is not None

    def test_all_decay_exports_importable(self):
        from aurora_core.activation import (
            AGGRESSIVE_DECAY,
            DecayCalculator,
            DecayConfig,
            GENTLE_DECAY,
            MODERATE_DECAY,
            calculate_decay,
        )
        assert DecayCalculator is not None

    def test_all_retrieval_exports_importable(self):
        from aurora_core.activation import (
            ActivationRetriever,
            BatchRetriever,
            ChunkData,
            RetrievalConfig,
            RetrievalResult,
        )
        assert ActivationRetriever is not None

    def test_all_formula_exports_importable(self):
        from aurora_core.activation import (
            AccessHistoryEntry,
            BaseLevelActivation,
            BLAConfig,
            ContextBoost,
            ContextBoostConfig,
            KeywordExtractor,
            Relationship,
            RelationshipGraph,
            SpreadingActivation,
            SpreadingConfig,
            calculate_bla,
            calculate_context_boost,
            calculate_spreading,
        )
        assert BaseLevelActivation is not None


class TestOptimizationPackageExports:
    def test_optimization_empty_all(self):
        from aurora_core.optimization import __all__
        assert __all__ == []


class TestResiliencePackageExports:
    def test_resilience_exports_retry_handler(self):
        from aurora_core.resilience import RetryHandler, __all__
        assert __all__ == ["RetryHandler"]
        assert RetryHandler is not None

    def test_removed_modules_not_importable(self):
        with pytest.raises(ImportError):
            from aurora_core.resilience import alerting  # noqa: F401
        with pytest.raises(ImportError):
            from aurora_core.resilience import metrics_collector  # noqa: F401
        with pytest.raises(ImportError):
            from aurora_core.resilience import rate_limiter  # noqa: F401


class TestTemplatesPackageExports:
    def test_templates_exports(self):
        from aurora_cli.templates import (
            AGENTS_TEMPLATE,
            CLAUDE_TEMPLATE,
            COMMAND_TEMPLATES,
            PROJECT_TEMPLATE,
            get_agents_template,
            get_all_command_templates,
            get_claude_template,
        )
        assert AGENTS_TEMPLATE is not None
        assert callable(get_agents_template)
        assert callable(get_all_command_templates)
        assert callable(get_claude_template)


# ============================================================
# 4. Removed symbols regression guard
# ============================================================


class TestRemovedSymbolsNotAccessible:
    def test_decay_no_explain_decay_method(self):
        calc = DecayCalculator()
        assert not hasattr(calc, "explain_decay")

    def test_decay_no_calculate_with_metadata(self):
        calc = DecayCalculator()
        assert not hasattr(calc, "calculate_with_metadata")

    def test_decay_no_get_decay_curve(self):
        calc = DecayCalculator()
        assert not hasattr(calc, "get_decay_curve")

    def test_connection_pool_no_clear_connection_pool_function(self):
        from aurora_core.store import connection_pool as cp_module
        assert not hasattr(cp_module, "clear_connection_pool")

    def test_paths_no_get_budget_tracker_path(self):
        from aurora_core import paths
        assert not hasattr(paths, "get_budget_tracker_path")


# ============================================================
# 5. SOAR retrieve module integrity
# ============================================================


class TestSoarRetrieveIntegrity:
    def test_retrieval_budgets_accessible(self):
        from aurora_soar.phases.retrieve import RETRIEVAL_BUDGETS
        assert isinstance(RETRIEVAL_BUDGETS, dict)
        assert "SIMPLE" in RETRIEVAL_BUDGETS
        assert "MEDIUM" in RETRIEVAL_BUDGETS
        assert "COMPLEX" in RETRIEVAL_BUDGETS
        assert "CRITICAL" in RETRIEVAL_BUDGETS

    def test_retrieval_budgets_values(self):
        from aurora_soar.phases.retrieve import RETRIEVAL_BUDGETS
        assert RETRIEVAL_BUDGETS["SIMPLE"] < RETRIEVAL_BUDGETS["MEDIUM"]
        assert RETRIEVAL_BUDGETS["MEDIUM"] < RETRIEVAL_BUDGETS["COMPLEX"]
        assert RETRIEVAL_BUDGETS["COMPLEX"] < RETRIEVAL_BUDGETS["CRITICAL"]

    def test_no_filter_by_activation(self):
        from aurora_soar.phases import retrieve as ret_module
        assert not hasattr(ret_module, "filter_by_activation")
        assert not hasattr(ret_module, "ACTIVATION_THRESHOLD")

    def test_retrieve_context_importable(self):
        from aurora_soar.phases.retrieve import retrieve_context
        assert callable(retrieve_context)


# ============================================================
# 6. SOAR assess module integrity
# ============================================================


class TestSoarAssessIntegrity:
    def test_assessment_result_importable(self):
        from aurora_soar.phases.assess import AssessmentResult
        result = AssessmentResult(
            level="simple", score=5, confidence=0.9, signals=["short_query"]
        )
        assert result.level == "simple"
        assert result.score == 5

    def test_assessment_result_to_dict(self):
        from aurora_soar.phases.assess import AssessmentResult
        result = AssessmentResult(
            level="medium", score=15, confidence=0.85, signals=["multi_step"]
        )
        d = result.to_dict()
        assert d["level"] == "medium"
        assert d["score"] == 15
        assert d["confidence"] == 0.85

    def test_complexity_assessor_importable(self):
        from aurora_soar.phases.assess import ComplexityAssessor
        assessor = ComplexityAssessor()
        assert assessor is not None

    def test_no_complexity_level_enum(self):
        from aurora_soar.phases import assess as assess_module
        assert not hasattr(assess_module, "ComplexityLevel")


# ============================================================
# 7. Spawner recovery module integrity
# ============================================================


class TestSpawnerRecoveryIntegrity:
    def test_recovery_state_enum(self):
        from aurora_spawner.recovery import RecoveryState
        assert RecoveryState.INITIAL.value == "initial"
        assert RecoveryState.EXECUTING.value == "executing"
        assert RecoveryState.SUCCEEDED.value == "succeeded"
        assert RecoveryState.FAILED.value == "failed"
        assert RecoveryState.CIRCUIT_OPEN.value == "circuit_open"

    def test_recovery_state_transition_creation(self):
        from aurora_spawner.recovery import RecoveryState, RecoveryStateTransition
        t = RecoveryStateTransition(
            from_state=RecoveryState.INITIAL,
            to_state=RecoveryState.EXECUTING,
            timestamp=1234567890.0,
            reason="starting",
        )
        assert t.from_state == RecoveryState.INITIAL
        assert t.to_state == RecoveryState.EXECUTING

    def test_spawner_package_exports(self):
        from aurora_spawner import (
            CircuitBreaker,
            ErrorCategory,
            ErrorClassifier,
            HeartbeatEmitter,
            HeartbeatMonitor,
            RecoveryMetrics,
            RecoveryPolicy,
            RecoveryResult,
            RecoveryState,
            RecoveryStateMachine,
            RecoveryStrategy,
            RecoverySummary,
            SpawnResult,
            SpawnTask,
            TaskRecoveryState,
            get_circuit_breaker,
            get_recovery_metrics,
            reset_recovery_metrics,
            spawn,
            spawn_parallel,
        )
        assert RecoveryStateMachine is not None
        assert callable(spawn)


# ============================================================
# 8. Context-code module integrity
# ============================================================


class TestContextCodeIntegrity:
    def test_bm25_scorer_tokenize(self):
        from aurora_context_code.semantic.bm25_scorer import tokenize
        tokens = tokenize("getUserData")
        assert len(tokens) > 0
        assert any("get" in t.lower() for t in tokens)

    def test_bm25_scorer_class_importable(self):
        from aurora_context_code.semantic.bm25_scorer import BM25Scorer
        scorer = BM25Scorer()
        assert scorer is not None

    def test_bm25_no_standalone_functions(self):
        from aurora_context_code.semantic import bm25_scorer as bm25_module
        assert not hasattr(bm25_module, "calculate_idf")
        assert not hasattr(bm25_module, "calculate_bm25")

    def test_embedding_provider_importable(self):
        from aurora_context_code.semantic.embedding_provider import (
            EmbeddingProvider,
            cosine_similarity,
        )
        assert EmbeddingProvider is not None
        assert callable(cosine_similarity)

    def test_embedding_no_is_model_loaded(self):
        from aurora_context_code.semantic import embedding_provider as ep_module
        assert not hasattr(ep_module, "is_model_loaded")

    def test_git_signal_extractor_importable(self):
        from aurora_context_code.git import GitSignalExtractor
        extractor = GitSignalExtractor()
        assert extractor is not None

    def test_git_no_removed_methods(self):
        from aurora_context_code.git import GitSignalExtractor
        extractor = GitSignalExtractor()
        assert not hasattr(extractor, "clear_cache")
        assert not hasattr(extractor, "_parse_blame_output")
        assert not hasattr(extractor, "_get_commit_timestamp")


# ============================================================
# 9. End-to-end: ActivationEngine full workflow
# ============================================================


class TestActivationEngineEndToEnd:
    def test_full_workflow_calculate_and_explain(self):
        """Full workflow: create engine, calculate, explain, verify consistency."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        access_history = [
            AccessHistoryEntry(timestamp=now - timedelta(hours=2)),
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=7)),
        ]
        last_access = now - timedelta(hours=2)
        query_kw = {"database", "optimize"}
        chunk_kw = {"database", "query", "optimize"}

        components = engine.calculate_total(
            access_history=access_history,
            last_access=last_access,
            spreading_activation=0.5,
            query_keywords=query_kw,
            chunk_keywords=chunk_kw,
            current_time=now,
        )

        explanation = engine.explain_activation(
            access_history=access_history,
            last_access=last_access,
            spreading_activation=0.5,
            query_keywords=query_kw,
            chunk_keywords=chunk_kw,
            current_time=now,
        )

        exp_components = explanation["components"]
        assert exp_components["bla"] == pytest.approx(components.bla, abs=1e-6)
        assert exp_components["spreading"] == pytest.approx(components.spreading, abs=1e-6)
        assert exp_components["context_boost"] == pytest.approx(components.context_boost, abs=1e-6)
        assert exp_components["decay"] == pytest.approx(components.decay, abs=1e-6)
        assert exp_components["total"] == pytest.approx(components.total, abs=1e-6)

    def test_cached_engine_works(self):
        from unittest.mock import MagicMock
        mock_store = MagicMock()
        mock_store.db_path = ":memory:test_cached"

        engine = get_cached_engine(mock_store)
        assert isinstance(engine, ActivationEngine)

        components = engine.calculate_total(spreading_activation=0.3)
        assert components.total == pytest.approx(0.3, abs=1e-6)

    def test_decay_by_type_constants(self):
        assert "kb" in DECAY_BY_TYPE
        assert "function" in DECAY_BY_TYPE
        assert "doc" in DECAY_BY_TYPE
        assert DECAY_BY_TYPE["kb"] < DECAY_BY_TYPE["function"]
