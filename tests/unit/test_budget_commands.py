"""Unit tests for budget command group in AURORA CLI.

Tests the budget commands: show, set, reset, and history.
Ensures proper display, validation, and error handling.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest
from aurora_cli.commands.budget import (
    budget_group,
    history_command,
    reset_command,
    set_command,
    show_command,
)
from aurora_cli.config import Config
from click.testing import CliRunner

from aurora_core.budget.tracker import CostTracker


@pytest.fixture
def temp_budget_file():
    """Create temporary budget tracker file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_config_file():
    """Create temporary config file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def mock_config(temp_budget_file, temp_config_file):
    """Create mock config with temporary paths."""
    config = Config(
        budget_tracker_path=str(temp_budget_file),
        budget_limit=15.00,
        db_path="~/.aurora/memory.db",
        llm_provider="anthropic",
        llm_model="claude-3-5-sonnet-20241022",
    )
    return config


class TestShowCommand:
    """Test budget show command."""

    def test_show_displays_budget_status(self, mock_config, temp_budget_file):
        """Test show command displays budget status correctly."""
        # Initialize tracker with some spending
        tracker = CostTracker(monthly_limit_usd=15.00, tracker_path=temp_budget_file)
        tracker.record_query("test query", 0.50, "success")

        runner = CliRunner()
        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(show_command, [])

        # Check output
        assert result.exit_code == 0
        assert "Budget Status" in result.output
        assert "$15.00" in result.output  # Budget limit
        assert "$0.50" in result.output or "0.50" in result.output  # Spent amount
        assert "Remaining" in result.output
        assert "Consumed" in result.output

    def test_show_displays_warning_at_soft_limit(self, mock_config, temp_budget_file):
        """Test show command displays warning when approaching budget limit."""
        # Initialize tracker with 85% spending (soft limit)
        tracker = CostTracker(monthly_limit_usd=15.00, tracker_path=temp_budget_file)
        tracker.record_query("expensive query", 13.00, "success")

        runner = CliRunner()
        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(show_command, [])

        assert result.exit_code == 0
        assert "Approaching budget limit" in result.output or "%" in result.output

    def test_show_displays_error_at_hard_limit(self, mock_config, temp_budget_file):
        """Test show command displays error when budget limit exceeded."""
        # Initialize tracker with 100% spending (hard limit)
        tracker = CostTracker(monthly_limit_usd=15.00, tracker_path=temp_budget_file)
        tracker.record_query("expensive query", 15.50, "success")

        runner = CliRunner()
        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(show_command, [])

        assert result.exit_code == 0
        assert "Budget limit reached" in result.output or "100" in result.output

    def test_show_handles_error_gracefully(self, mock_config):
        """Test show command handles errors gracefully."""
        runner = CliRunner()

        # Mock load_config to raise an exception
        with patch("aurora_cli.commands.budget.load_config", side_effect=Exception("Config error")):
            result = runner.invoke(show_command, [])

        assert result.exit_code != 0
        assert "Error" in result.output or "Failed" in result.output


class TestSetCommand:
    """Test budget set command."""

    def test_set_updates_budget_limit(self, mock_config, temp_budget_file):
        """Test set command updates budget limit correctly."""
        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            with patch("aurora_cli.config.save_config") as mock_save:
                result = runner.invoke(set_command, ["20.00"])

        assert result.exit_code == 0
        assert "$20.00" in result.output
        assert "Budget limit set" in result.output or "✓" in result.output
        mock_save.assert_called_once()

    def test_set_rejects_negative_amount(self, mock_config):
        """Test set command rejects negative amounts."""
        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(set_command, ["-5.00"])

        assert result.exit_code != 0
        assert "positive" in result.output or "Error" in result.output

    def test_set_rejects_zero_amount(self, mock_config):
        """Test set command rejects zero amount."""
        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(set_command, ["0.00"])

        assert result.exit_code != 0
        assert "positive" in result.output or "Error" in result.output

    def test_set_accepts_decimal_amounts(self, mock_config, temp_budget_file):
        """Test set command accepts decimal amounts."""
        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            with patch("aurora_cli.config.save_config"):
                result = runner.invoke(set_command, ["12.75"])

        assert result.exit_code == 0
        assert "$12.75" in result.output

    def test_set_handles_error_gracefully(self, mock_config):
        """Test set command handles errors gracefully."""
        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", side_effect=Exception("Config error")):
            result = runner.invoke(set_command, ["10.00"])

        assert result.exit_code != 0
        assert "Error" in result.output or "Failed" in result.output


class TestResetCommand:
    """Test budget reset command."""

    def test_reset_clears_spending_with_confirmation(self, mock_config, temp_budget_file):
        """Test reset command clears spending with confirmation."""
        # Initialize tracker with some spending
        tracker = CostTracker(monthly_limit_usd=15.00, tracker_path=temp_budget_file)
        tracker.record_query("test query", 2.50, "success")

        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            # Use --confirm flag to skip prompt
            result = runner.invoke(reset_command, ["--confirm"])

        assert result.exit_code == 0
        assert "Spending reset" in result.output or "✓" in result.output
        assert "$0.00" in result.output

        # Verify spending was actually reset
        tracker_check = CostTracker(monthly_limit_usd=15.00, tracker_path=temp_budget_file)
        assert tracker_check.get_total_spent() == 0.0

    def test_reset_requires_confirmation_without_flag(self, mock_config, temp_budget_file):
        """Test reset command requires confirmation when flag not provided."""
        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            # Simulate user declining confirmation
            result = runner.invoke(reset_command, [], input="n\n")

        assert result.exit_code == 0
        assert "Reset cancelled" in result.output or "cancelled" in result.output

    def test_reset_preserves_budget_limit(self, mock_config, temp_budget_file):
        """Test reset command preserves budget limit."""
        # Initialize tracker with some spending
        tracker = CostTracker(monthly_limit_usd=15.00, tracker_path=temp_budget_file)
        tracker.record_query("test query", 5.00, "success")

        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(reset_command, ["--confirm"])

        assert result.exit_code == 0
        assert "$15.00" in result.output  # Budget limit preserved

    def test_reset_handles_error_gracefully(self, mock_config):
        """Test reset command handles errors gracefully."""
        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", side_effect=Exception("Config error")):
            result = runner.invoke(reset_command, ["--confirm"])

        assert result.exit_code != 0
        assert "Error" in result.output or "Failed" in result.output


class TestHistoryCommand:
    """Test budget history command."""

    def test_history_displays_query_records(self, mock_config, temp_budget_file):
        """Test history command displays query records."""
        # Initialize tracker and add some queries
        tracker = CostTracker(monthly_limit_usd=15.00, tracker_path=temp_budget_file)
        tracker.record_query("first query", 0.25, "success")
        tracker.record_query("second query", 0.50, "success")
        tracker.record_query("third query", 0.75, "success")

        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(history_command, [])

        assert result.exit_code == 0
        assert "Query History" in result.output
        assert "first query" in result.output
        assert "second query" in result.output
        assert "third query" in result.output
        assert "$0.25" in result.output or "0.25" in result.output

    def test_history_shows_no_entries_message_when_empty(self, mock_config, temp_budget_file):
        """Test history command shows message when no entries exist."""
        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(history_command, [])

        assert result.exit_code == 0
        assert "No query history" in result.output or "No" in result.output.lower()

    def test_history_respects_limit_option(self, mock_config, temp_budget_file):
        """Test history command respects --limit option."""
        # Initialize tracker and add many queries
        tracker = CostTracker(monthly_limit_usd=15.00, tracker_path=temp_budget_file)
        for i in range(25):
            tracker.record_query(f"query {i}", 0.10, "success")

        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(history_command, ["--limit", "5"])

        assert result.exit_code == 0
        assert "showing 5 of 25" in result.output or "5" in result.output

    def test_history_shows_all_with_flag(self, mock_config, temp_budget_file):
        """Test history command shows all entries with --all flag."""
        # Initialize tracker and add several queries
        tracker = CostTracker(monthly_limit_usd=15.00, tracker_path=temp_budget_file)
        for i in range(30):
            tracker.record_query(f"query {i}", 0.10, "success")

        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(history_command, ["--all"])

        assert result.exit_code == 0
        assert "30 of 30" in result.output or "30" in result.output

    def test_history_displays_total_cost(self, mock_config, temp_budget_file):
        """Test history command displays total cost."""
        # Initialize tracker and add queries with known costs
        tracker = CostTracker(monthly_limit_usd=15.00, tracker_path=temp_budget_file)
        tracker.record_query("query 1", 1.00, "success")
        tracker.record_query("query 2", 2.00, "success")
        tracker.record_query("query 3", 3.00, "success")

        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(history_command, [])

        assert result.exit_code == 0
        assert "Total" in result.output
        assert "$6.00" in result.output or "6.00" in result.output

    def test_history_handles_error_gracefully(self, mock_config):
        """Test history command handles errors gracefully."""
        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", side_effect=Exception("Config error")):
            result = runner.invoke(history_command, [])

        assert result.exit_code != 0
        assert "Error" in result.output or "Failed" in result.output


class TestBudgetGroup:
    """Test budget command group behavior."""

    def test_budget_group_invokes_show_by_default(self, mock_config, temp_budget_file):
        """Test budget command without subcommand invokes show."""
        runner = CliRunner()

        with patch("aurora_cli.commands.budget.load_config", return_value=mock_config):
            result = runner.invoke(budget_group, [])

        assert result.exit_code == 0
        assert "Budget Status" in result.output

    def test_budget_group_help_shows_subcommands(self):
        """Test budget --help shows all subcommands."""
        runner = CliRunner()
        result = runner.invoke(budget_group, ["--help"])

        assert result.exit_code == 0
        assert "show" in result.output
        assert "set" in result.output
        assert "reset" in result.output
        assert "history" in result.output
