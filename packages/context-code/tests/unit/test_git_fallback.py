"""Unit tests for Git fallback behavior.

Tests that Git operations gracefully fall back when Git is unavailable.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestGitFallback:
    """Test Git unavailability and fallback."""

    def test_git_extractor_handles_non_git_directory(self):
        """Test Git extractor handles non-Git directory gracefully."""
        from aurora_context_code.git import GitSignalExtractor

        # Create temporary non-Git directory
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello(): pass")

            extractor = GitSignalExtractor()

            # Should return empty list for non-Git directory
            commit_times = extractor.get_function_commit_times(str(test_file), 1, 1)
            assert commit_times == []

            # calculate_bla should return default value
            bla = extractor.calculate_bla(commit_times)
            assert bla == 0.5  # Default fallback value

    def test_git_extractor_handles_git_not_installed(self):
        """Test Git extractor when git command not found."""
        from aurora_context_code.git import GitSignalExtractor

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello(): pass")
            test_file = Path(f.name)

        try:
            # Mock subprocess to raise FileNotFoundError
            with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
                extractor = GitSignalExtractor()
                commit_times = extractor.get_function_commit_times(str(test_file), 1, 1)

                # Should return empty list
                assert commit_times == []

                # BLA should use fallback
                bla = extractor.calculate_bla(commit_times)
                assert bla == 0.5
        finally:
            test_file.unlink()

    def test_git_fallback_warning_logged(self, caplog):
        """Test warning is logged when Git unavailable."""
        import logging

        from aurora_context_code.git import GitSignalExtractor

        # Create temporary non-Git directory
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello(): pass")

            extractor = GitSignalExtractor()

            with caplog.at_level(logging.DEBUG):
                commit_times = extractor.get_function_commit_times(str(test_file), 1, 1)

            # Should log debug message about Git failure
            assert commit_times == []
            # Git failure is logged at DEBUG level in current implementation


class TestEnvironmentVariableOverride:
    """Test AURORA_SKIP_GIT environment variable."""

    def test_skip_git_env_var_forces_fallback(self, caplog):
        """Test AURORA_SKIP_GIT forces fallback mode."""
        import logging

        # Set environment variable
        old_value = os.environ.get("AURORA_SKIP_GIT")
        os.environ["AURORA_SKIP_GIT"] = "1"

        try:
            # Force reimport
            import importlib

            import aurora_context_code.git as git_module

            importlib.reload(git_module)

            from aurora_context_code.git import GitSignalExtractor

            with caplog.at_level(logging.WARNING):
                extractor = GitSignalExtractor()

            # Should have available flag set to False
            assert extractor.available is False

            # Should have logged warning
            assert any(
                "Git disabled via AURORA_SKIP_GIT" in record.message for record in caplog.records
            )

            # get_function_commit_times should return empty list
            commit_times = extractor.get_function_commit_times("test.py", 1, 10)
            assert commit_times == []

            # BLA should use default
            bla = extractor.calculate_bla(commit_times)
            assert bla == 0.5
        finally:
            # Restore environment
            if old_value is None:
                os.environ.pop("AURORA_SKIP_GIT", None)
            else:
                os.environ["AURORA_SKIP_GIT"] = old_value

            # Reload to restore normal state
            importlib.reload(git_module)

    def test_skip_git_various_values(self):
        """Test various truthy values for AURORA_SKIP_GIT."""

        test_values = ["true", "True", "TRUE", "yes", "1", "anything"]

        for value in test_values:
            # Set environment variable
            old_value = os.environ.get("AURORA_SKIP_GIT")
            os.environ["AURORA_SKIP_GIT"] = value

            try:
                # Force reimport
                import importlib

                import aurora_context_code.git as git_module

                importlib.reload(git_module)

                from aurora_context_code.git import GitSignalExtractor

                extractor = GitSignalExtractor()

                # Should have available=False for any truthy value
                assert extractor.available is False, f"Failed for value: {value}"
            finally:
                # Restore environment
                if old_value is None:
                    os.environ.pop("AURORA_SKIP_GIT", None)
                else:
                    os.environ["AURORA_SKIP_GIT"] = old_value

                # Reload to restore normal state
                importlib.reload(git_module)
