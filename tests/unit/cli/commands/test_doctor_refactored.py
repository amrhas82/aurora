"""Tests for refactored doctor command helper functions.

This module tests the extracted helper functions from doctor.py
to ensure behavior is maintained after refactoring for complexity reduction.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestCollectIssues:
    """Tests for _collect_issues helper function."""

    def test_collects_fixable_issues(self) -> None:
        """Test that fixable issues are collected from checks."""
        from aurora_cli.commands.doctor import _collect_issues

        mock_check = MagicMock()
        mock_check.get_fixable_issues.return_value = [
            {"name": "issue1", "fix_func": lambda: None},
        ]
        mock_check.get_manual_issues.return_value = []

        fixable, manual = _collect_issues([mock_check])

        assert len(fixable) == 1
        assert fixable[0]["name"] == "issue1"
        assert len(manual) == 0

    def test_collects_manual_issues(self) -> None:
        """Test that manual issues are collected from checks."""
        from aurora_cli.commands.doctor import _collect_issues

        mock_check = MagicMock()
        mock_check.get_fixable_issues.return_value = []
        mock_check.get_manual_issues.return_value = [
            {"name": "manual1", "solution": "fix manually"},
        ]

        fixable, manual = _collect_issues([mock_check])

        assert len(fixable) == 0
        assert len(manual) == 1
        assert manual[0]["name"] == "manual1"

    def test_handles_checks_without_methods(self) -> None:
        """Test that checks without get_fixable/manual_issues methods are handled."""
        from aurora_cli.commands.doctor import _collect_issues

        mock_check = MagicMock(spec=[])  # No attributes

        fixable, manual = _collect_issues([mock_check])

        assert len(fixable) == 0
        assert len(manual) == 0

    def test_aggregates_from_multiple_checks(self) -> None:
        """Test that issues are aggregated from multiple check instances."""
        from aurora_cli.commands.doctor import _collect_issues

        mock_check1 = MagicMock()
        mock_check1.get_fixable_issues.return_value = [{"name": "issue1", "fix_func": lambda: None}]
        mock_check1.get_manual_issues.return_value = []

        mock_check2 = MagicMock()
        mock_check2.get_fixable_issues.return_value = [{"name": "issue2", "fix_func": lambda: None}]
        mock_check2.get_manual_issues.return_value = [{"name": "manual1", "solution": "fix"}]

        fixable, manual = _collect_issues([mock_check1, mock_check2])

        assert len(fixable) == 2
        assert len(manual) == 1


class TestApplyFixes:
    """Tests for _apply_fixes helper function."""

    def test_applies_fixes_successfully(self) -> None:
        """Test that fixes are applied and counted correctly."""
        from aurora_cli.commands.doctor import _apply_fixes

        fix_called = []
        issues = [
            {"name": "issue1", "fix_func": lambda: fix_called.append(1)},
            {"name": "issue2", "fix_func": lambda: fix_called.append(2)},
        ]

        with patch("aurora_cli.commands.doctor.console") as mock_console:
            fixed_count = _apply_fixes(issues)

        assert fixed_count == 2
        assert len(fix_called) == 2

    def test_handles_fix_failure(self) -> None:
        """Test that fix failures are handled gracefully."""
        from aurora_cli.commands.doctor import _apply_fixes

        def failing_fix() -> None:
            raise ValueError("Fix failed")

        issues = [
            {"name": "issue1", "fix_func": failing_fix},
            {"name": "issue2", "fix_func": lambda: None},
        ]

        with patch("aurora_cli.commands.doctor.console"):
            fixed_count = _apply_fixes(issues)

        # Only the second fix should succeed
        assert fixed_count == 1

    def test_returns_zero_for_empty_list(self) -> None:
        """Test that empty issue list returns zero fixed."""
        from aurora_cli.commands.doctor import _apply_fixes

        with patch("aurora_cli.commands.doctor.console"):
            fixed_count = _apply_fixes([])

        assert fixed_count == 0


class TestDisplayIssues:
    """Tests for _display_fixable_issues and _display_manual_issues helpers."""

    def test_display_fixable_issues(self) -> None:
        """Test display of fixable issues."""
        from aurora_cli.commands.doctor import _display_fixable_issues

        issues = [
            {"name": "issue1"},
            {"name": "issue2"},
        ]

        with patch("aurora_cli.commands.doctor.console") as mock_console:
            _display_fixable_issues(issues)

        # Should print header and each issue
        assert mock_console.print.call_count >= 3

    def test_display_fixable_issues_empty(self) -> None:
        """Test that empty fixable issues prints nothing."""
        from aurora_cli.commands.doctor import _display_fixable_issues

        with patch("aurora_cli.commands.doctor.console") as mock_console:
            _display_fixable_issues([])

        mock_console.print.assert_not_called()

    def test_display_manual_issues(self) -> None:
        """Test display of manual issues."""
        from aurora_cli.commands.doctor import _display_manual_issues

        issues = [
            {"name": "manual1", "solution": "fix manually"},
        ]

        with patch("aurora_cli.commands.doctor.console") as mock_console:
            _display_manual_issues(issues)

        # Should print header, issue name, and solution
        assert mock_console.print.call_count >= 3

    def test_display_manual_issues_empty(self) -> None:
        """Test that empty manual issues prints nothing."""
        from aurora_cli.commands.doctor import _display_manual_issues

        with patch("aurora_cli.commands.doctor.console") as mock_console:
            _display_manual_issues([])

        mock_console.print.assert_not_called()
