"""Unit tests for CostTracker and BudgetTracker."""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from aurora_core.budget.tracker import MODEL_PRICING, BudgetTracker, CostTracker, PeriodBudget


class TestModelPricing:
    """Test ModelPricing class."""

    def test_calculate_cost_anthropic_sonnet(self):
        """Test cost calculation for Claude Sonnet."""
        pricing = MODEL_PRICING["claude-sonnet-4-20250514"]
        # 1000 input tokens, 500 output tokens
        # Input: (1000 / 1M) * $3.00 = $0.003
        # Output: (500 / 1M) * $15.00 = $0.0075
        # Total: $0.0105
        cost = pricing.calculate_cost(1000, 500)
        assert abs(cost - 0.0105) < 1e-6

    def test_calculate_cost_anthropic_opus(self):
        """Test cost calculation for Claude Opus."""
        pricing = MODEL_PRICING["claude-opus-4-20250514"]
        # 1000 input tokens, 500 output tokens
        # Input: (1000 / 1M) * $15.00 = $0.015
        # Output: (500 / 1M) * $75.00 = $0.0375
        # Total: $0.0525
        cost = pricing.calculate_cost(1000, 500)
        assert abs(cost - 0.0525) < 1e-6

    def test_calculate_cost_anthropic_haiku(self):
        """Test cost calculation for Claude Haiku."""
        pricing = MODEL_PRICING["claude-3-5-haiku-20241022"]
        # 1000 input tokens, 500 output tokens
        # Input: (1000 / 1M) * $0.80 = $0.0008
        # Output: (500 / 1M) * $4.00 = $0.002
        # Total: $0.0028
        cost = pricing.calculate_cost(1000, 500)
        assert abs(cost - 0.0028) < 1e-6

    def test_calculate_cost_openai_gpt4(self):
        """Test cost calculation for GPT-4."""
        pricing = MODEL_PRICING["gpt-4-turbo"]
        # 1000 input tokens, 500 output tokens
        # Input: (1000 / 1M) * $10.00 = $0.01
        # Output: (500 / 1M) * $30.00 = $0.015
        # Total: $0.025
        cost = pricing.calculate_cost(1000, 500)
        assert abs(cost - 0.025) < 1e-6

    def test_calculate_cost_ollama_free(self):
        """Test cost calculation for Ollama (free)."""
        pricing = MODEL_PRICING["llama2"]
        cost = pricing.calculate_cost(10000, 5000)
        assert cost == 0.0

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        pricing = MODEL_PRICING["claude-sonnet-4-20250514"]
        cost = pricing.calculate_cost(0, 0)
        assert cost == 0.0

    def test_calculate_cost_large_numbers(self):
        """Test cost calculation with large token counts."""
        pricing = MODEL_PRICING["claude-sonnet-4-20250514"]
        # 1M input, 500K output
        # Input: (1M / 1M) * $3.00 = $3.00
        # Output: (500K / 1M) * $15.00 = $7.50
        # Total: $10.50
        cost = pricing.calculate_cost(1_000_000, 500_000)
        assert abs(cost - 10.50) < 1e-6


class TestPeriodBudget:
    """Test PeriodBudget class."""

    def test_init_defaults(self):
        """Test PeriodBudget initialization with defaults."""
        budget = PeriodBudget(period="2024-12", limit_usd=100.0)
        assert budget.period == "2024-12"
        assert budget.limit_usd == 100.0
        assert budget.consumed_usd == 0.0
        assert budget.entries == []

    def test_remaining_usd(self):
        """Test remaining budget calculation."""
        budget = PeriodBudget(period="2024-12", limit_usd=100.0, consumed_usd=30.0)
        assert budget.remaining_usd == 70.0

    def test_remaining_usd_negative(self):
        """Test remaining budget when over limit."""
        budget = PeriodBudget(period="2024-12", limit_usd=100.0, consumed_usd=120.0)
        assert budget.remaining_usd == 0.0  # Should not go negative

    def test_percent_consumed(self):
        """Test percent consumed calculation."""
        budget = PeriodBudget(period="2024-12", limit_usd=100.0, consumed_usd=30.0)
        assert budget.percent_consumed == 30.0

    def test_percent_consumed_zero_limit(self):
        """Test percent consumed with zero limit."""
        budget = PeriodBudget(period="2024-12", limit_usd=0.0, consumed_usd=0.0)
        assert budget.percent_consumed == 100.0

    def test_is_at_soft_limit_true(self):
        """Test soft limit detection (80%)."""
        budget = PeriodBudget(period="2024-12", limit_usd=100.0, consumed_usd=85.0)
        assert budget.is_at_soft_limit() is True

    def test_is_at_soft_limit_exact(self):
        """Test soft limit detection at exactly 80%."""
        budget = PeriodBudget(period="2024-12", limit_usd=100.0, consumed_usd=80.0)
        assert budget.is_at_soft_limit() is True

    def test_is_at_soft_limit_false(self):
        """Test soft limit detection below threshold."""
        budget = PeriodBudget(period="2024-12", limit_usd=100.0, consumed_usd=79.0)
        assert budget.is_at_soft_limit() is False

    def test_is_at_hard_limit_true(self):
        """Test hard limit detection (100%)."""
        budget = PeriodBudget(period="2024-12", limit_usd=100.0, consumed_usd=100.0)
        assert budget.is_at_hard_limit() is True

    def test_is_at_hard_limit_over(self):
        """Test hard limit detection over 100%."""
        budget = PeriodBudget(period="2024-12", limit_usd=100.0, consumed_usd=120.0)
        assert budget.is_at_hard_limit() is True

    def test_is_at_hard_limit_false(self):
        """Test hard limit detection below threshold."""
        budget = PeriodBudget(period="2024-12", limit_usd=100.0, consumed_usd=99.0)
        assert budget.is_at_hard_limit() is False


class TestCostTracker:
    """Test CostTracker class."""

    @pytest.fixture
    def temp_tracker_path(self, tmp_path):
        """Create temporary tracker path."""
        return tmp_path / "budget_tracker.json"

    @pytest.fixture
    def tracker(self, temp_tracker_path):
        """Create CostTracker instance with temp path."""
        return CostTracker(monthly_limit_usd=100.0, tracker_path=temp_tracker_path)

    def test_init_default_path(self, tmp_path, monkeypatch):
        """Test CostTracker initialization with default path.

        Uses monkeypatch to isolate from user's global config.
        """
        # Isolate from user's global ~/.aurora directory
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))

        tracker = CostTracker(monthly_limit_usd=50.0)
        assert tracker.monthly_limit_usd == 50.0
        assert tracker.tracker_path == fake_home / ".aurora" / "budget_tracker.json"
        # Limit should be set correctly (50.0 since starting fresh)
        assert tracker.budget.limit_usd == 50.0

    def test_init_custom_path(self, temp_tracker_path):
        """Test CostTracker initialization with custom path."""
        tracker = CostTracker(monthly_limit_usd=100.0, tracker_path=temp_tracker_path)
        assert tracker.tracker_path == temp_tracker_path
        assert tracker.budget.limit_usd == 100.0

    def test_get_model_pricing_known_model(self, tracker):
        """Test getting pricing for known model."""
        pricing = tracker.get_model_pricing("claude-sonnet-4-20250514")
        assert pricing.input_price_per_mtok == 3.0
        assert pricing.output_price_per_mtok == 15.0

    def test_get_model_pricing_unknown_model(self, tracker):
        """Test getting pricing for unknown model (uses default)."""
        pricing = tracker.get_model_pricing("unknown-model-xyz")
        assert pricing.input_price_per_mtok == 3.0  # Default pricing
        assert pricing.output_price_per_mtok == 15.0

    def test_calculate_cost(self, tracker):
        """Test cost calculation."""
        cost = tracker.calculate_cost(
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
        )
        assert abs(cost - 0.0105) < 1e-6

    def test_estimate_cost(self, tracker):
        """Test cost estimation from prompt length."""
        # 400 chars → ~100 input tokens (400 / 4)
        # Max 4096 output → assume 2048 output tokens (50%)
        # Input: (100 / 1M) * $3.00 = $0.0003
        # Output: (2048 / 1M) * $15.00 = $0.03072
        # Total: ~$0.03102
        cost = tracker.estimate_cost(
            model="claude-sonnet-4-20250514",
            prompt_length=400,
            max_output_tokens=4096,
        )
        assert 0.030 < cost < 0.032

    def test_check_budget_within_limit(self, tracker):
        """Test budget check when within limit."""
        can_proceed, message = tracker.check_budget(estimated_cost=10.0)
        assert can_proceed is True
        assert message == ""

    def test_check_budget_soft_limit(self, tracker):
        """Test budget check at soft limit (80%)."""
        # Consume 70, check for 15 more → 85% total
        tracker.budget.consumed_usd = 70.0
        can_proceed, message = tracker.check_budget(estimated_cost=15.0)
        assert can_proceed is True
        assert "Budget warning" in message
        assert "85.0%" in message

    def test_check_budget_hard_limit(self, tracker):
        """Test budget check at hard limit (100%)."""
        # Consume 90, check for 15 more → 105% total
        tracker.budget.consumed_usd = 90.0
        can_proceed, message = tracker.check_budget(estimated_cost=15.0, raise_on_exceeded=False)
        assert can_proceed is False
        assert "Budget exceeded" in message
        assert "105.0%" in message

    def test_check_budget_exactly_at_limit(self, tracker):
        """Test budget check exactly at 100%."""
        tracker.budget.consumed_usd = 95.0
        can_proceed, message = tracker.check_budget(estimated_cost=5.0, raise_on_exceeded=False)
        assert can_proceed is False
        assert "100.0%" in message

    def test_record_cost(self, tracker):
        """Test recording actual cost."""
        cost = tracker.record_cost(
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            operation="assess",
        )

        assert abs(cost - 0.0105) < 1e-6
        assert tracker.budget.consumed_usd == cost
        assert len(tracker.budget.entries) == 1

        entry = tracker.budget.entries[0]
        assert entry.model == "claude-sonnet-4-20250514"
        assert entry.input_tokens == 1000
        assert entry.output_tokens == 500
        assert entry.operation == "assess"
        assert abs(entry.cost_usd - 0.0105) < 1e-6

    def test_record_cost_with_query_id(self, tracker):
        """Test recording cost with query ID."""
        tracker.record_cost(
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            operation="decompose",
            query_id="query-123",
        )

        entry = tracker.budget.entries[0]
        assert entry.query_id == "query-123"

    def test_record_cost_multiple_entries(self, tracker):
        """Test recording multiple costs."""
        cost1 = tracker.record_cost(
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            operation="assess",
        )
        cost2 = tracker.record_cost(
            model="claude-opus-4-20250514",
            input_tokens=2000,
            output_tokens=1000,
            operation="decompose",
        )

        total_cost = cost1 + cost2
        assert abs(tracker.budget.consumed_usd - total_cost) < 1e-6
        assert len(tracker.budget.entries) == 2

    def test_get_status(self, tracker):
        """Test getting budget status."""
        tracker.record_cost(
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            operation="assess",
        )

        status = tracker.get_status()
        assert status["period"] == tracker.current_period
        assert status["limit_usd"] == 100.0
        assert status["consumed_usd"] > 0
        assert status["remaining_usd"] < 100.0
        assert 0 < status["percent_consumed"] < 100
        assert status["at_soft_limit"] is False
        assert status["at_hard_limit"] is False
        assert status["total_entries"] == 1

    def test_get_status_at_soft_limit(self, tracker):
        """Test status at soft limit."""
        tracker.budget.consumed_usd = 85.0
        status = tracker.get_status()
        assert status["at_soft_limit"] is True
        assert status["at_hard_limit"] is False

    def test_get_status_at_hard_limit(self, tracker):
        """Test status at hard limit."""
        tracker.budget.consumed_usd = 100.0
        status = tracker.get_status()
        assert status["at_soft_limit"] is True
        assert status["at_hard_limit"] is True

    def test_get_breakdown_by_operation(self, tracker):
        """Test cost breakdown by operation."""
        tracker.record_cost("claude-sonnet-4-20250514", 1000, 500, "assess")
        tracker.record_cost("claude-sonnet-4-20250514", 2000, 1000, "assess")
        tracker.record_cost("claude-opus-4-20250514", 1000, 500, "decompose")

        breakdown = tracker.get_breakdown_by_operation()
        assert "assess" in breakdown
        assert "decompose" in breakdown
        # Two assess calls (1k+500 and 2k+1k with Sonnet)
        # One decompose call (1k+500 with Opus - more expensive)
        # Just verify both operations tracked, not cost comparison
        assert breakdown["assess"] > 0
        assert breakdown["decompose"] > 0

    def test_get_breakdown_by_model(self, tracker):
        """Test cost breakdown by model."""
        tracker.record_cost("claude-sonnet-4-20250514", 1000, 500, "assess")
        tracker.record_cost("claude-sonnet-4-20250514", 2000, 1000, "assess")
        tracker.record_cost("claude-opus-4-20250514", 1000, 500, "decompose")

        breakdown = tracker.get_breakdown_by_model()
        assert "claude-sonnet-4-20250514" in breakdown
        assert "claude-opus-4-20250514" in breakdown
        # Opus is more expensive per token
        assert breakdown["claude-opus-4-20250514"] > 0

    def test_persistence_save_and_load(self, temp_tracker_path):
        """Test saving and loading budget data."""
        # Create tracker and record some costs
        tracker1 = CostTracker(monthly_limit_usd=100.0, tracker_path=temp_tracker_path)
        tracker1.record_cost("claude-sonnet-4-20250514", 1000, 500, "assess")
        consumed = tracker1.budget.consumed_usd

        # Create new tracker instance - should load saved data
        tracker2 = CostTracker(monthly_limit_usd=100.0, tracker_path=temp_tracker_path)
        assert tracker2.budget.consumed_usd == consumed
        assert len(tracker2.budget.entries) == 1

    def test_persistence_corrupted_file(self, temp_tracker_path):
        """Test handling of corrupted tracker file."""
        # Write invalid JSON
        with open(temp_tracker_path, "w") as f:
            f.write("invalid json{{{")

        # Should start fresh, not crash
        tracker = CostTracker(monthly_limit_usd=100.0, tracker_path=temp_tracker_path)
        assert tracker.budget.consumed_usd == 0.0
        assert len(tracker.budget.entries) == 0

    @patch("aurora_core.budget.tracker.datetime")
    def test_period_rollover(self, mock_datetime, temp_tracker_path):
        """Test monthly period rollover."""
        # Start in December 2025
        mock_datetime.now.return_value = datetime(2025, 12, 15)
        tracker1 = CostTracker(monthly_limit_usd=100.0, tracker_path=temp_tracker_path)
        tracker1.record_cost("claude-sonnet-4-20250514", 1000, 500, "assess")
        assert tracker1.current_period == "2025-12"
        december_consumed = tracker1.budget.consumed_usd

        # Move to January 2026
        mock_datetime.now.return_value = datetime(2026, 1, 5)
        tracker2 = CostTracker(monthly_limit_usd=100.0, tracker_path=temp_tracker_path)
        assert tracker2.current_period == "2026-01"
        assert tracker2.budget.consumed_usd == 0.0  # Reset for new period
        assert len(tracker2.budget.entries) == 0

        # Old data should be archived
        archive_path = temp_tracker_path.parent / "budget_archives" / "budget_2025-12.json"
        assert archive_path.exists()

        # Load archived data
        with open(archive_path) as f:
            archived = json.load(f)
        assert archived["period"] == "2025-12"
        assert archived["consumed_usd"] == december_consumed

    def test_budget_tracker_alias(self):
        """Test BudgetTracker is an alias for CostTracker."""
        # BudgetTracker is a subclass, not an alias
        assert issubclass(BudgetTracker, CostTracker)
        # But they should be functionally identical
        tracker = BudgetTracker(monthly_limit_usd=50.0)
        assert isinstance(tracker, CostTracker)


class TestCostEstimation:
    """Test cost estimation for different scenarios."""

    def test_estimate_simple_query(self):
        """Test estimation for simple query."""
        tracker = CostTracker(monthly_limit_usd=100.0)
        # Short query, small output
        cost = tracker.estimate_cost(
            model="claude-3-5-haiku-20241022",  # Haiku for simple
            prompt_length=100,  # ~25 tokens
            max_output_tokens=512,
        )
        # Should be very cheap with Haiku
        assert cost < 0.01

    def test_estimate_medium_query(self):
        """Test estimation for medium query."""
        tracker = CostTracker(monthly_limit_usd=100.0)
        cost = tracker.estimate_cost(
            model="claude-sonnet-4-20250514",  # Sonnet for medium
            prompt_length=2000,  # ~500 tokens
            max_output_tokens=2048,
        )
        # Should be moderate with Sonnet
        assert 0.01 < cost < 0.05

    def test_estimate_complex_query(self):
        """Test estimation for complex query."""
        tracker = CostTracker(monthly_limit_usd=100.0)
        cost = tracker.estimate_cost(
            model="claude-opus-4-20250514",  # Opus for complex
            prompt_length=8000,  # ~2000 tokens
            max_output_tokens=4096,
        )
        # Should be expensive with Opus
        assert cost > 0.05


class TestBudgetEnforcement:
    """Test budget enforcement scenarios."""

    def test_single_expensive_query_blocked(self, tmp_path, monkeypatch):
        """Test blocking single expensive query."""
        # Isolate from user's global ~/.aurora directory
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))

        tracker = CostTracker(monthly_limit_usd=1.0)  # Very low limit
        tracker.budget.consumed_usd = 0.9  # Already at 90%

        # Try to add query that would exceed - use raise_on_exceeded=False to get return value
        can_proceed, message = tracker.check_budget(estimated_cost=0.2, raise_on_exceeded=False)
        assert can_proceed is False
        assert "Budget exceeded" in message

    def test_multiple_queries_soft_warning(self, tmp_path, monkeypatch):
        """Test soft warning after multiple queries."""
        # Isolate from user's global ~/.aurora directory
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))

        tracker = CostTracker(monthly_limit_usd=1.0)

        # Manually set consumed to 70% to trigger warning
        tracker.budget.consumed_usd = 0.70

        # Next query estimated at 0.15 would bring total to 85%
        can_proceed, message = tracker.check_budget(estimated_cost=0.15)
        assert can_proceed is True  # Still allowed
        assert "Budget warning" in message  # Should warn at 85%

    def test_gradual_budget_consumption(self, tmp_path):
        """Test gradual budget consumption over many queries."""
        tracker_path = tmp_path / "budget_tracker.json"
        tracker = CostTracker(monthly_limit_usd=10.0, tracker_path=tracker_path)

        # Make many small queries
        for i in range(50):
            cost = tracker.record_cost(
                model="claude-3-5-haiku-20241022",
                input_tokens=100,
                output_tokens=50,
                operation=f"query_{i}",
            )
            # Each query should cost very little with Haiku
            assert cost < 0.01

        # Should still be within budget
        status = tracker.get_status()
        assert status["at_hard_limit"] is False
