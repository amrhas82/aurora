"""Unit tests for tree-sitter parser fallback behavior.

Tests that parser gracefully falls back to text chunking when tree-sitter is unavailable.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestTreeSitterFallback:
    """Test tree-sitter import failure and fallback."""

    def test_parser_handles_import_failure(self):
        """Test parser handles tree-sitter import failure gracefully."""
        # Temporarily disable tree-sitter
        import os

        old_value = os.environ.get("AURORA_SKIP_TREESITTER")
        os.environ["AURORA_SKIP_TREESITTER"] = "1"

        try:
            # Force reimport
            import importlib

            import aurora_context_code.languages.python as python_module

            importlib.reload(python_module)

            # Check that TREE_SITTER_AVAILABLE is False
            assert python_module.TREE_SITTER_AVAILABLE is False

            # Parser should initialize without crashing
            from aurora_context_code.languages.python import PythonParser

            parser = PythonParser()
            assert parser.parser is None
        finally:
            # Restore environment
            if old_value is None:
                os.environ.pop("AURORA_SKIP_TREESITTER", None)
            else:
                os.environ["AURORA_SKIP_TREESITTER"] = old_value

            # Reload to restore normal state
            importlib.reload(python_module)

    def test_fallback_chunks_created(self):
        """Test fallback chunking creates valid chunks."""
        import os
        import tempfile

        # Temporarily disable tree-sitter
        old_value = os.environ.get("AURORA_SKIP_TREESITTER")
        os.environ["AURORA_SKIP_TREESITTER"] = "1"

        try:
            # Force reimport
            import importlib

            import aurora_context_code.languages.python as python_module

            importlib.reload(python_module)

            from aurora_context_code.languages.python import PythonParser

            parser = PythonParser()

            # Create test file with 100 lines
            test_code = "\n".join([f"# Line {i}" for i in range(100)])
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(test_code)
                test_file = Path(f.name)

            try:
                # Parse should use fallback
                chunks = parser.parse(test_file)

                # Should have created chunks (100 lines / 50 = 2 chunks)
                assert len(chunks) >= 2
                assert all(chunk.element_type == "function" for chunk in chunks)
                assert all(chunk.name.startswith("fallback_lines_") for chunk in chunks)
                assert all(
                    chunk.docstring == "Fallback text chunk (tree-sitter unavailable)"
                    for chunk in chunks
                )
            finally:
                test_file.unlink()
        finally:
            # Restore environment
            if old_value is None:
                os.environ.pop("AURORA_SKIP_TREESITTER", None)
            else:
                os.environ["AURORA_SKIP_TREESITTER"] = old_value

            # Reload to restore normal state
            importlib.reload(python_module)

    def test_fallback_warning_logged(self, caplog):
        """Test warning is logged when using fallback."""
        import logging
        import os

        # Temporarily disable tree-sitter
        old_value = os.environ.get("AURORA_SKIP_TREESITTER")
        os.environ["AURORA_SKIP_TREESITTER"] = "1"

        try:
            # Force reimport
            import importlib

            import aurora_context_code.languages.python as python_module

            importlib.reload(python_module)

            # Capture logs at WARNING level
            with caplog.at_level(logging.WARNING):
                from aurora_context_code.languages.python import PythonParser

                parser = PythonParser()

            # Should have logged warning about fallback
            assert any("Tree-sitter unavailable" in record.message for record in caplog.records)
            assert any("text chunking" in record.message for record in caplog.records)
        finally:
            # Restore environment
            if old_value is None:
                os.environ.pop("AURORA_SKIP_TREESITTER", None)
            else:
                os.environ["AURORA_SKIP_TREESITTER"] = old_value

            # Reload to restore normal state
            importlib.reload(python_module)


class TestEnvironmentVariableOverride:
    """Test AURORA_SKIP_TREESITTER environment variable."""

    def test_skip_treesitter_env_var(self):
        """Test AURORA_SKIP_TREESITTER forces fallback mode."""
        import os

        # Set environment variable
        old_value = os.environ.get("AURORA_SKIP_TREESITTER")
        os.environ["AURORA_SKIP_TREESITTER"] = "1"

        try:
            # Force reimport
            import importlib

            import aurora_context_code.languages.python as python_module

            importlib.reload(python_module)

            # Should be disabled
            assert python_module.TREE_SITTER_AVAILABLE is False

            from aurora_context_code.languages.python import PythonParser

            parser = PythonParser()
            assert parser.parser is None
        finally:
            # Restore environment
            if old_value is None:
                os.environ.pop("AURORA_SKIP_TREESITTER", None)
            else:
                os.environ["AURORA_SKIP_TREESITTER"] = old_value

            # Reload to restore normal state
            importlib.reload(python_module)

    def test_skip_treesitter_various_values(self):
        """Test various truthy values for AURORA_SKIP_TREESITTER."""
        import os

        test_values = ["true", "True", "TRUE", "yes", "1", "anything"]

        for value in test_values:
            # Set environment variable
            old_value = os.environ.get("AURORA_SKIP_TREESITTER")
            os.environ["AURORA_SKIP_TREESITTER"] = value

            try:
                # Force reimport
                import importlib

                import aurora_context_code.languages.python as python_module

                importlib.reload(python_module)

                # Should be disabled for any truthy value
                assert python_module.TREE_SITTER_AVAILABLE is False, f"Failed for value: {value}"

                from aurora_context_code.languages.python import PythonParser

                parser = PythonParser()
                assert parser.parser is None, f"Failed for value: {value}"
            finally:
                # Restore environment
                if old_value is None:
                    os.environ.pop("AURORA_SKIP_TREESITTER", None)
                else:
                    os.environ["AURORA_SKIP_TREESITTER"] = old_value

                # Reload to restore normal state
                importlib.reload(python_module)
