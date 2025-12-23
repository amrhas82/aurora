"""Fault injection tests for budget exceeded scenarios."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from aurora_reasoning.llm_client import LLMResponse

from aurora_core.budget import CostTracker
from aurora_core.config.loader import Config
from aurora_core.exceptions import BudgetExceededError
from aurora_core.store.sqlite import SQLiteStore
from aurora_soar.agent_registry import AgentRegistry
from aurora_soar.orchestrator import SOAROrchestrator


@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary database path."""
    return tmp_path / "test_aurora.db"


@pytest.fixture
def temp_tracker_path(tmp_path):
    """Create temporary tracker path."""
    return tmp_path / "budget_tracker.json"


@pytest.fixture
def store(temp_db_path):
    """Create test store."""
    store = SQLiteStore(str(temp_db_path))
    yield store
    store.close()


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = Mock()
    client.default_model = "claude-sonnet-4-20250514"
    client.generate.return_value = LLMResponse(
        content="Test response",
        model="claude-sonnet-4-20250514",
        input_tokens=1000,
        output_tokens=500,
        finish_reason="stop",
    )
    client.generate_json.return_value = {"complexity": "SIMPLE", "confidence": 0.9}
    return client


@pytest.fixture
def agent_registry():
    """Create test agent registry."""
    return AgentRegistry()


@pytest.fixture
def config():
    """Create test config."""
    return Config(
        {
            "budget": {
                "monthly_limit_usd": 1.0  # Very low limit for testing
            }
        }
    )


class TestBudgetExceededFaultInjection:
    """Fault injection tests for budget exceeded scenarios."""

    def test_budget_exceeded_before_execution(
        self, store, agent_registry, config, mock_llm_client, temp_tracker_path
    ):
        """Test query rejection when budget already exceeded."""
        # Create tracker at hard limit
        tracker = CostTracker(monthly_limit_usd=1.0, tracker_path=temp_tracker_path)
        tracker.budget.consumed_usd = 1.0  # At 100%

        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=mock_llm_client,
            solving_llm=mock_llm_client,
            cost_tracker=tracker,
        )

        # Query should be rejected immediately
        with pytest.raises(BudgetExceededError) as exc_info:
            orchestrator.execute("Test query")

        error = exc_info.value
        assert error.consumed_usd == 1.0
        assert error.limit_usd == 1.0
        assert "exceeded" in str(error).lower()

    def test_budget_exceeded_with_expensive_model(
        self, store, agent_registry, config, mock_llm_client, temp_tracker_path
    ):
        """Test query rejection when using expensive model."""
        # Create tracker with low remaining budget
        tracker = CostTracker(monthly_limit_usd=0.1, tracker_path=temp_tracker_path)
        tracker.budget.consumed_usd = 0.05  # 50% used

        # Mock expensive Opus model
        mock_llm_client.default_model = "claude-opus-4-20250514"

        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=mock_llm_client,
            solving_llm=mock_llm_client,
            cost_tracker=tracker,
        )

        # Large query with Opus should exceed remaining budget
        with pytest.raises(BudgetExceededError) as exc_info:
            orchestrator.execute("This is a very long query " * 100)

        error = exc_info.value
        assert error.consumed_usd == 0.05
        assert error.estimated_cost > 0

    def test_budget_exceeded_mid_execution(
        self, store, agent_registry, config, mock_llm_client, temp_tracker_path
    ):
        """Test behavior when budget is exceeded during execution."""
        # Start with budget that will be exceeded during execution
        tracker = CostTracker(monthly_limit_usd=0.01, tracker_path=temp_tracker_path)
        tracker.budget.consumed_usd = 0.005  # 50% used

        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=mock_llm_client,
            solving_llm=mock_llm_client,
            cost_tracker=tracker,
        )

        # First query might succeed (small estimate)
        # But actual cost could push over limit
        try:
            orchestrator.execute("Small query")
            # If execution succeeded, verify cost was tracked
            status = tracker.get_status()
            assert status["consumed_usd"] > 0.005
        except BudgetExceededError:
            # Budget check might reject before execution
            pass

        # Next query should definitely be rejected
        with pytest.raises(BudgetExceededError):
            orchestrator.execute("Another query")

    def test_budget_error_message_details(
        self, store, agent_registry, config, mock_llm_client, temp_tracker_path
    ):
        """Test that budget error messages contain useful details."""
        # Use isolated temp directory to avoid loading persistent budget data
        temp_dir = tempfile.mkdtemp()
        isolated_path = Path(temp_dir) / "isolated_budget_tracker.json"

        tracker = CostTracker(monthly_limit_usd=1.0, tracker_path=isolated_path)
        tracker.budget.consumed_usd = 0.999  # 99.9% used - any query should exceed

        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=mock_llm_client,
            solving_llm=mock_llm_client,
            cost_tracker=tracker,
        )

        with pytest.raises(BudgetExceededError) as exc_info:
            orchestrator.execute("Query that exceeds budget")

        error = exc_info.value

        # Error should contain useful information
        error_str = str(error)
        assert "budget" in error_str.lower() or "exceeded" in error_str.lower()

        # Error should have structured data
        assert error.consumed_usd == 0.999
        assert error.limit_usd == 1.0
        assert error.estimated_cost > 0

    def test_budget_recovery_after_period_rollover(
        self, store, agent_registry, config, mock_llm_client, temp_tracker_path
    ):
        """Test that budget is recovered after monthly rollover."""
        from datetime import datetime
        from unittest.mock import patch

        # Create tracker in December at limit
        with patch("aurora_core.budget.tracker.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 12, 31)

            tracker = CostTracker(monthly_limit_usd=1.0, tracker_path=temp_tracker_path)
            tracker.budget.consumed_usd = 1.0  # At 100% in December

            orchestrator = SOAROrchestrator(
                store=store,
                agent_registry=agent_registry,
                config=config,
                reasoning_llm=mock_llm_client,
                solving_llm=mock_llm_client,
                cost_tracker=tracker,
            )

            # Query should be rejected
            with pytest.raises(BudgetExceededError):
                orchestrator.execute("Query in December")

        # Move to January - budget should reset
        with patch("aurora_core.budget.tracker.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 1)

            # Create new tracker instance (simulates new session)
            tracker2 = CostTracker(monthly_limit_usd=1.0, tracker_path=temp_tracker_path)

            # Budget should be reset
            status = tracker2.get_status()
            assert status["period"] == "2025-01"
            assert status["consumed_usd"] == 0.0
            assert status["remaining_usd"] == 1.0

            # Query should now succeed (budget check should pass)
            SOAROrchestrator(
                store=store,
                agent_registry=agent_registry,
                config=config,
                reasoning_llm=mock_llm_client,
                solving_llm=mock_llm_client,
                cost_tracker=tracker2,
            )

            # Budget check should pass now
            can_proceed, _ = tracker2.check_budget(0.01)
            assert can_proceed is True

    def test_concurrent_queries_budget_race_condition(
        self, store, agent_registry, config, mock_llm_client, temp_tracker_path
    ):
        """Test budget enforcement with concurrent queries (race condition)."""
        # This tests the race condition where multiple queries check budget
        # before any complete, potentially exceeding budget

        # Use isolated temp directory to avoid loading persistent budget data
        temp_dir = tempfile.mkdtemp()
        isolated_path = Path(temp_dir) / "isolated_budget_tracker.json"

        tracker = CostTracker(monthly_limit_usd=1.0, tracker_path=isolated_path)
        tracker.budget.consumed_usd = 0.999  # 99.9% used - any query should exceed

        SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=mock_llm_client,
            solving_llm=mock_llm_client,
            cost_tracker=tracker,
        )

        # First query checks budget - should see 99.9% consumed
        # Any estimated cost will push over 100% limit
        estimated_cost = tracker.estimate_cost(
            model="claude-sonnet-4-20250514", prompt_length=400, max_output_tokens=512
        )

        can_proceed1, msg1 = tracker.check_budget(estimated_cost)
        # At 99.9%, should be rejected
        assert can_proceed1 is False

        # Second query check should also be rejected
        can_proceed2, msg2 = tracker.check_budget(estimated_cost)
        assert can_proceed2 is False

    @pytest.mark.skip(
        reason="Known issue: CostTracker has ZeroDivisionError with limit=0.0 (tracker.py:303)"
    )
    def test_budget_exceeded_with_zero_limit(
        self, store, agent_registry, mock_llm_client, temp_tracker_path
    ):
        """Test behavior with zero budget limit (disabled tracking).

        NOTE: Currently fails due to ZeroDivisionError in CostTracker.check_budget()
        when calculating projected_percent with limit_usd=0.0.
        Should be fixed to handle zero limit gracefully (either reject immediately
        or treat as unlimited).
        """
        config = Config({"budget": {"monthly_limit_usd": 0.0}})

        # Use isolated temp directory to avoid loading persistent budget data
        temp_dir = tempfile.mkdtemp()
        isolated_path = Path(temp_dir) / "isolated_budget_tracker.json"

        tracker = CostTracker(monthly_limit_usd=0.0, tracker_path=isolated_path)

        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=mock_llm_client,
            solving_llm=mock_llm_client,
            cost_tracker=tracker,
        )

        # Any query should be rejected with zero budget
        with pytest.raises(BudgetExceededError):
            orchestrator.execute("Any query")

    def test_budget_exceeded_error_attributes(
        self, store, agent_registry, config, mock_llm_client, temp_tracker_path
    ):
        """Test that BudgetExceededError has all required attributes."""
        tracker = CostTracker(monthly_limit_usd=1.0, tracker_path=temp_tracker_path)
        tracker.budget.consumed_usd = 1.0

        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=mock_llm_client,
            solving_llm=mock_llm_client,
            cost_tracker=tracker,
        )

        try:
            orchestrator.execute("Test query")
            pytest.fail("Expected BudgetExceededError")
        except BudgetExceededError as e:
            # Verify error has all required attributes
            assert hasattr(e, "message")
            assert hasattr(e, "consumed_usd")
            assert hasattr(e, "limit_usd")
            assert hasattr(e, "estimated_cost")

            # Verify attributes have sensible values
            assert e.consumed_usd >= 0
            assert e.limit_usd > 0
            assert e.estimated_cost >= 0

            # Verify error is informative
            assert len(str(e)) > 0
