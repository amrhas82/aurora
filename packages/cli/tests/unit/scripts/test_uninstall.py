"""Tests for aurora-uninstall script."""

import sys
from unittest.mock import MagicMock, patch

import pytest


def test_uninstall_import():
    """Test that uninstall module can be imported."""
    from aurora.scripts.uninstall import main

    assert callable(main)


def test_uninstall_help(capsys):
    """Test that uninstall script shows help."""
    from aurora.scripts.uninstall import main

    with pytest.raises(SystemExit) as exc_info:
        with patch.object(sys, "argv", ["aurora-uninstall", "--help"]):
            main()

    # Help text should exit with code 0
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "Uninstall all AURORA packages" in captured.out


def test_uninstall_cancel(monkeypatch):
    """Test that uninstall can be cancelled."""
    from aurora.scripts.uninstall import main

    # Mock user input to cancel
    monkeypatch.setattr("builtins.input", lambda _: "n")

    with pytest.raises(SystemExit) as exc_info:
        with patch.object(sys, "argv", ["aurora-uninstall"]):
            main()

    # Should exit with code 0 when cancelled
    assert exc_info.value.code == 0


def test_uninstall_with_yes_flag(capsys):
    """Test uninstall with --yes flag (dry run, mock subprocess)."""
    from aurora.scripts.uninstall import main

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Successfully uninstalled"
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result):
        with patch.object(sys, "argv", ["aurora-uninstall", "--yes", "--keep-config"]):
            main()

    captured = capsys.readouterr()
    assert "AURORA uninstall complete" in captured.out


def test_uninstall_handles_missing_packages(capsys):
    """Test that uninstall handles missing packages gracefully."""
    from aurora.scripts.uninstall import main

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "WARNING: aurora-core not installed"
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result):
        with patch.object(sys, "argv", ["aurora-uninstall", "--yes", "--keep-config"]):
            main()

    captured = capsys.readouterr()
    # Should not raise exception, should complete successfully
    assert "AURORA uninstall complete" in captured.out
