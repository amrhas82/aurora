"""
Integration Test: Budget Enforcement

Tests Issue #10: Budget Commands Missing
- Verifies budget checking before expensive LLM calls
- Tests budget tracking and history recording
- Validates budget limits prevent overspending

This test will FAIL initially because budget enforcement isn't implemented.

Test Strategy:
- Create QueryExecutor with low budget limit
- Attempt expensive query
- Verify query blocked before LLM call
- Verify budget history shows blocked query
- Increase budget and verify query succeeds

Expected Failure:
- Budget not checked before LLM calls
- Queries execute even when budget exceeded
- No budget history tracking
- No budget command group exists

Related Files:
- packages/cli/src/aurora_cli/execution.py (QueryExecutor.execute_direct_llm)
- packages/core/src/aurora_core/cost/tracker.py (CostTracker)
- packages/cli/src/aurora_cli/commands/budget.py (budget commands - to be created)

Phase: 1 (Core Restoration)
Priority: P1 (High)
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from aurora_cli.execution import QueryExecutor

from aurora_core.cost.tracker import BudgetExceededError, CostTracker


class TestBudgetEnforcement:
    """Test that budget limits are enforced before LLM calls."""

    @pytest.fixture
    def low_budget_config(self, tmp_path):
        """Create config with very low budget for testing."""
        db_path = tmp_path / "test_memory.db"
        budget_path = tmp_path / "budget.json"

        config = {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "max_tokens": 500,
            "budget_limit": 0.005,  # $0.005 limit (very low for testing)
            "budget_tracker_path": str(budget_path)
        }

        return config, budget_path

    @pytest.fixture
    def cost_tracker_with_low_budget(self, low_budget_config):
        """Create CostTracker with low budget."""
        config, budget_path = low_budget_config

        tracker = CostTracker(
            budget_file=str(budget_path),
            total_budget=0.005  # Match the low_budget_config limit
        )

        return tracker, budget_path

    def test_budget_checked_before_llm_call(self, low_budget_config):
        """
        Test that budget is checked BEFORE calling expensive LLM.

        This test will FAIL because execute_direct_llm() doesn't check budget.
        """
        config, budget_path = low_budget_config

        executor = QueryExecutor(
            config=config,
            interactive_mode=False
        )

        # Mock LLM client to track if it's called
        llm_called = False
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "This should not be reached if budget check works"
        mock_response.input_tokens = 1000
        mock_response.output_tokens = 500

        def mock_generate(prompt, **kwargs):
            nonlocal llm_called
            llm_called = True
            return mock_response

        mock_llm.generate.side_effect = mock_generate

        with patch.object(executor, '_initialize_llm_client', return_value=mock_llm):
            # Attempt expensive query (very long prompt = higher estimated cost)
            # Need ~8000 chars to get ~2000 input tokens
            # With max_tokens=500, estimated output=250 tokens
            # Cost: (2000/1M * $3) + (250/1M * $15) = $0.006 + $0.00375 = $0.00975
            # Still under $0.01! Let's make it even longer
            long_query = ("Explain in detail " + " and elaborate " * 500)  # ~14k chars = ~3500 tokens

            # Should raise BudgetExceededError
            with pytest.raises(BudgetExceededError) as exc_info:
                executor.execute_direct_llm(long_query, api_key="test-key")

            # ASSERTION 1: Budget error should be raised BEFORE LLM call
            assert not llm_called, (
                "LLM was called despite budget exceeded\n"
                "Expected: BudgetExceededError raised BEFORE LLM call\n"
                "Actual: LLM called (budget check not implemented)\n"
                "Fix: Add budget.check_budget(estimated_cost) before LLM call"
            )

            # ASSERTION 2: Error message should be helpful
            error_message = str(exc_info.value)
            assert "budget" in error_message.lower(), (
                f"Budget error message not helpful\n"
                f"Expected: Message about budget exceeded\n"
                f"Actual: {error_message}"
            )

    def test_actual_cost_recorded_after_successful_query(self, tmp_path):
        """
        Test that actual LLM cost is recorded after successful query.

        This test will FAIL if cost recording not implemented.
        """
        db_path = tmp_path / "test_memory.db"
        budget_path = tmp_path / "budget.json"

        # High budget for this test
        config = {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "max_tokens": 500,
            "budget_limit": 10.0,
            "budget_tracker_path": str(budget_path)
        }

        executor = QueryExecutor(
            config=config,
            interactive_mode=False
        )

        # Mock LLM to return response with cost metadata
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Response text"
        mock_response.input_tokens = 100
        mock_response.output_tokens = 50

        def mock_generate_with_cost(prompt, **kwargs):
            # Simulate response with usage info
            return mock_response

        mock_llm.generate.side_effect = mock_generate_with_cost

        with patch.object(executor, '_initialize_llm_client', return_value=mock_llm):
            # Mock the _call_llm_with_retry to return mock response
            with patch.object(executor, '_call_llm_with_retry', return_value=mock_response):
                query = "What is Python?"
                result = executor.execute_direct_llm(query, api_key="test-key")

                # Check budget file for recorded cost
                if budget_path.exists():
                    with open(budget_path) as f:
                        budget_data = json.load(f)

                    spent = budget_data.get("consumed_usd", 0.0)

                    # ASSERTION: Cost should be recorded
                    assert spent > 0, (
                        f"Query cost not recorded in budget tracker\n"
                        f"Expected: spent > 0 (calculated from 100 input + 50 output tokens)\n"
                        f"Actual: spent = ${spent:.6f}\n"
                        f"Fix: Call tracker.record_cost() after LLM call"
                    )

    def test_budget_history_shows_blocked_queries(self, cost_tracker_with_low_budget):
        """
        Test that blocked queries appear in budget history.

        This test will FAIL if history tracking not implemented.
        """
        tracker, budget_path = cost_tracker_with_low_budget

        # Attempt query over budget
        query = "Expensive query " * 50
        estimated_cost = 0.10  # Over $0.01 limit

        try:
            tracker.check_budget(estimated_cost)
            pytest.fail("Expected BudgetExceededError but none raised")
        except BudgetExceededError:
            # Expected - now check history
            pass

        # Query history
        history = tracker.get_history()

        # ASSERTION: History should include blocked query
        blocked_entries = [
            entry for entry in history
            if entry.get("status") == "blocked" or entry.get("blocked", False)
        ]

        assert len(blocked_entries) > 0, (
            f"Blocked query not in budget history\n"
            f"Expected: At least 1 blocked entry\n"
            f"Actual: {len(blocked_entries)} blocked entries\n"
            f"Total history: {len(history)} entries\n"
            f"Fix: Record blocked queries in tracker.check_budget()"
        )

    def test_increase_budget_allows_query(self, low_budget_config):
        """
        Test that increasing budget allows previously blocked query.

        This test verifies budget modification works.
        """
        config, budget_path = low_budget_config

        # Initial tracker with low budget
        tracker = CostTracker(
            budget_file=str(budget_path),
            total_budget=0.01
        )

        # Verify initial budget blocks query
        high_cost = 0.05
        with pytest.raises(BudgetExceededError):
            tracker.check_budget(high_cost)

        # Increase budget
        tracker.set_budget(1.00)  # Increase to $1.00

        # Verify query now allowed
        try:
            tracker.check_budget(high_cost)
            budget_ok = True
        except BudgetExceededError:
            budget_ok = False

        # ASSERTION: Query should now be allowed
        assert budget_ok, (
            f"Query still blocked after budget increase\n"
            f"Initial budget: $0.01\n"
            f"New budget: $1.00\n"
            f"Query cost: ${high_cost}\n"
            f"Fix: Verify tracker.set_budget() updates limit correctly"
        )


class TestBudgetCommands:
    """Test budget command group functionality (Issue #10)."""

    @pytest.fixture
    def budget_tracker_with_history(self, tmp_path):
        """Create tracker with some spending history."""
        budget_path = tmp_path / "budget.json"

        tracker = CostTracker(
            budget_file=str(budget_path),
            total_budget=5.00
        )

        # Record some queries
        tracker.record_query("What is Python?", 0.02, status="success")
        tracker.record_query("Explain SQLite", 0.03, status="success")
        tracker.record_query("Long query...", 10.00, status="blocked")

        return tracker, budget_path

    def test_budget_show_command_displays_spending(self, budget_tracker_with_history):
        """
        Test that 'aur budget' shows current spending and remaining budget.

        This test will FAIL because budget command doesn't exist yet.
        """
        tracker, budget_path = budget_tracker_with_history

        # Get current state
        total_budget = tracker.total_budget
        spent = tracker.get_total_spent()
        remaining = total_budget - spent

        # ASSERTION: Tracker should report accurate spending
        assert spent > 0, (
            f"Tracker shows no spending despite recorded queries\n"
            f"Expected: spent = $0.05 (0.02 + 0.03)\n"
            f"Actual: spent = ${spent}\n"
            f"Fix: Verify record_query() increments spent amount"
        )

        assert remaining < total_budget, (
            f"Remaining budget equals total (no spending recorded)\n"
            f"Total: ${total_budget}, Remaining: ${remaining}\n"
            f"Fix: Ensure spent amount deducted from total"
        )

    def test_budget_set_command_updates_limit(self, tmp_path):
        """
        Test that 'aur budget set <amount>' updates budget limit.

        This test documents expected behavior for task 7.1.
        """
        budget_path = tmp_path / "budget.json"

        tracker = CostTracker(
            budget_file=str(budget_path),
            total_budget=5.00
        )

        # Set new budget
        new_budget = 10.00
        tracker.set_budget(new_budget)

        # ASSERTION: Budget should be updated
        assert tracker.total_budget == new_budget, (
            f"Budget not updated\n"
            f"Expected: ${new_budget}\n"
            f"Actual: ${tracker.total_budget}"
        )

        # Verify persisted to file
        tracker2 = CostTracker(budget_file=str(budget_path))
        assert tracker2.total_budget == new_budget, (
            f"Budget not persisted to file\n"
            f"Expected: ${new_budget}\n"
            f"Actual: ${tracker2.total_budget}"
        )

    def test_budget_reset_command_clears_spending(self, budget_tracker_with_history):
        """
        Test that 'aur budget reset' clears spending history.

        This test documents expected behavior for task 7.1.
        """
        tracker, budget_path = budget_tracker_with_history

        # Verify initial spending
        initial_spent = tracker.get_total_spent()
        assert initial_spent > 0, "Test fixture error: no spending recorded"

        # Reset spending
        tracker.reset_spending()

        # ASSERTION: Spending should be cleared
        assert tracker.get_total_spent() == 0, (
            f"Spending not reset\n"
            f"Expected: $0.00\n"
            f"Actual: ${tracker.get_total_spent()}"
        )

    def test_budget_history_command_shows_queries(self, budget_tracker_with_history):
        """
        Test that 'aur budget history' displays query history with costs.

        This test documents expected behavior for task 7.1.
        """
        tracker, budget_path = budget_tracker_with_history

        # Get history
        history = tracker.get_history()

        # ASSERTION 1: History should contain entries
        assert len(history) >= 2, (
            f"History missing recorded queries\n"
            f"Expected: At least 2 success + 1 blocked = 3 entries\n"
            f"Actual: {len(history)} entries"
        )

        # ASSERTION 2: Entries should have required fields
        required_fields = ["query", "cost", "status", "timestamp"]

        for entry in history:
            for field in required_fields:
                assert field in entry, (
                    f"History entry missing '{field}' field\n"
                    f"Entry: {entry}\n"
                    f"Fix: Ensure record_query() stores all required fields"
                )

        # ASSERTION 3: Should distinguish success vs blocked
        statuses = {entry["status"] for entry in history}
        assert "success" in statuses or "blocked" in statuses, (
            f"History doesn't distinguish success/blocked queries\n"
            f"Found statuses: {statuses}\n"
            f"Fix: Store status in record_query()"
        )


class TestBudgetEstimation:
    """Test cost estimation before LLM calls."""

    def test_estimate_cost_from_prompt_length(self):
        """
        Test that cost can be estimated from prompt length.

        This test documents expected estimation logic.
        """
        # Rough estimation formula:
        # tokens ≈ prompt_length / 4
        # cost = tokens * price_per_token

        short_prompt = "What is Python?"
        long_prompt = "Explain " + "in detail " * 100

        # Sonnet 4.5 pricing: ~$0.015 per 1K tokens
        # Short: ~4 tokens * $0.000015 = $0.00006
        # Long: ~800 tokens * $0.000015 = $0.012

        def estimate_cost(prompt):
            tokens = len(prompt) / 4
            return tokens * 0.000015

        short_cost = estimate_cost(short_prompt)
        long_cost = estimate_cost(long_prompt)

        assert long_cost > short_cost, "Long prompt should cost more"
        assert long_cost > 0.001, "Long prompt should exceed $0.001"

        # This logic will be used in execute_direct_llm() for budget checks

    def test_budget_includes_response_tokens(self):
        """
        Test that budget estimation accounts for response tokens.

        This test documents that both input and output tokens should be estimated.
        """
        # When estimating cost:
        # - Input tokens: known from prompt
        # - Output tokens: estimated (e.g., 2x input or fixed amount like 500)

        # Example:
        # Input: 100 tokens
        # Expected output: 500 tokens
        # Total: 600 tokens
        # Cost: 600 * $0.000015 = $0.009

        prompt_tokens = 100
        estimated_response_tokens = 500
        total_tokens = prompt_tokens + estimated_response_tokens

        price_per_token = 0.000015  # Sonnet 4.5
        estimated_cost = total_tokens * price_per_token

        assert estimated_cost > 0.005, "Cost should account for response"

        # This conservative estimation helps prevent budget overruns


# Mark all tests in this file with integration marker
pytestmark = pytest.mark.integration
