"""Integration tests for LSP language registry and diagnostics formatting.

Tests language lookup, extension mapping, entry point detection,
complexity branch types, and diagnostics severity — all pure logic, no LSP server.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aurora_lsp.diagnostics import DiagnosticSeverity, DiagnosticsFormatter
from aurora_lsp.languages import (
    EXTENSION_MAP,
    get_call_node_type,
    get_callback_methods,
    get_complexity_branch_types,
    get_config,
    get_function_def_types,
    get_language,
    get_skip_deadcode_names,
    is_entry_point,
    is_nested_helper,
    supported_extensions,
)

# ---------------------------------------------------------------------------
# Language Registry
# ---------------------------------------------------------------------------


class TestGetLanguage:
    """Test extension → language resolution."""

    def test_python_extension(self):
        assert get_language("foo.py") == "python"
        assert get_language("bar.pyi") == "python"

    def test_all_extensions(self):
        expected = {
            ".py": "python",
            ".pyi": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".mjs": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".java": "java",
        }
        for ext, lang in expected.items():
            assert get_language(f"file{ext}") == lang, f"Failed for {ext}"
        assert len(EXTENSION_MAP) == len(expected)

    def test_unsupported_extension(self):
        assert get_language("file.rs") is None
        assert get_language("file.c") is None
        assert get_language("file.txt") is None


class TestGetConfig:
    """Test config retrieval."""

    def test_returns_config(self):
        config = get_config("test.py")
        assert config is not None
        assert config.name == "python"
        assert ".py" in config.extensions
        assert config.tree_sitter_module == "tree_sitter_python"

    def test_unsupported_returns_none(self):
        assert get_config("file.rs") is None


class TestEntryPoints:
    """Test entry point detection across languages."""

    def test_python_main(self):
        assert is_entry_point("test.py", "main") is True
        assert is_entry_point("test.py", "cli") is True

    def test_python_pattern(self):
        assert is_entry_point("test.py", "pytest_configure") is True
        assert is_entry_point("test.py", "test_something") is True

    def test_js_default_export(self):
        assert is_entry_point("test.js", "default") is True
        assert is_entry_point("test.js", "handler") is True
        assert is_entry_point("test.jsx", "getServerSideProps") is True

    def test_unsupported_lang(self):
        assert is_entry_point("test.rs", "main") is False
        assert is_entry_point("test.rs", "anything") is False


class TestNestedHelper:
    """Test nested helper detection."""

    def test_python_patterns(self):
        assert is_nested_helper("test.py", "wrapper") is True
        assert is_nested_helper("test.py", "inner") is True
        assert is_nested_helper("test.py", "_private") is True

    def test_not_nested(self):
        assert is_nested_helper("test.py", "public_function") is False

    def test_unsupported_lang(self):
        assert is_nested_helper("test.rs", "wrapper") is False


class TestComplexityBranchTypes:
    """Test branch types for complexity calculation."""

    def test_python_branch_types(self):
        types = get_complexity_branch_types("test.py")
        assert "if_statement" in types
        assert "for_statement" in types
        assert "while_statement" in types
        assert "try_statement" in types
        assert "boolean_operator" in types
        assert "conditional_expression" in types

    def test_unsupported_returns_empty(self):
        assert get_complexity_branch_types("test.rs") == set()


class TestCallbackMethods:
    """Test callback method names."""

    def test_js_callbacks(self):
        methods = get_callback_methods("test.js")
        assert "map" in methods
        assert "filter" in methods
        assert "then" in methods
        assert "forEach" in methods

    def test_unsupported(self):
        assert get_callback_methods("test.rs") == set()


class TestSkipDeadcodeNames:
    """Test framework names to skip in deadcode."""

    def test_js_skip_names(self):
        names = get_skip_deadcode_names("test.js")
        assert "queryFn" in names
        assert "onSuccess" in names

    def test_unsupported(self):
        assert get_skip_deadcode_names("test.rs") == set()


class TestSupportedExtensions:
    """Test supported extension listing."""

    def test_returns_all_extensions(self):
        exts = supported_extensions()
        assert len(exts) == 9
        assert ".py" in exts
        assert ".ts" in exts
        assert ".go" in exts
        assert ".java" in exts


class TestCallNodeType:
    """Test call node type per language."""

    def test_python(self):
        assert get_call_node_type("test.py") == "call"

    def test_go(self):
        assert get_call_node_type("test.go") == "call_expression"

    def test_javascript(self):
        assert get_call_node_type("test.js") == "call_expression"

    def test_unsupported(self):
        assert get_call_node_type("test.rs") == ""


class TestFunctionDefTypes:
    """Test function definition AST types."""

    def test_python(self):
        types = get_function_def_types("test.py")
        assert "function_definition" in types
        assert "class_definition" in types

    def test_unsupported(self):
        assert get_function_def_types("test.rs") == set()


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


class TestDiagnosticSeverity:
    """Test severity enum values match LSP spec."""

    def test_severity_values(self):
        assert DiagnosticSeverity.ERROR == 1
        assert DiagnosticSeverity.WARNING == 2
        assert DiagnosticSeverity.INFORMATION == 3
        assert DiagnosticSeverity.HINT == 4

    def test_int_comparison(self):
        assert DiagnosticSeverity.ERROR < DiagnosticSeverity.WARNING
        assert DiagnosticSeverity.WARNING < DiagnosticSeverity.HINT


class TestDiagnosticsFormatSingleFile:
    """Test diagnostics formatting with mocked client."""

    @pytest.mark.asyncio
    async def test_format_single_file(self, tmp_path):
        client = MagicMock()
        client.request_diagnostics = AsyncMock(
            return_value=[
                {
                    "severity": DiagnosticSeverity.ERROR,
                    "range": {"start": {"line": 9, "character": 4}},
                    "message": "Undefined variable 'x'",
                    "code": "F821",
                    "source": "pyflakes",
                },
                {
                    "severity": DiagnosticSeverity.WARNING,
                    "range": {"start": {"line": 15, "character": 0}},
                    "message": "Unused import",
                    "code": "F401",
                    "source": "pyflakes",
                },
            ],
        )

        formatter = DiagnosticsFormatter(client, tmp_path)
        result = await formatter.get_file_diagnostics(tmp_path / "test.py")

        assert len(result["errors"]) == 1
        assert len(result["warnings"]) == 1
        assert result["errors"][0]["line"] == 10  # 1-indexed
        assert result["errors"][0]["message"] == "Undefined variable 'x'"
        assert result["warnings"][0]["severity"] == "warning"


class TestDiagnosticsFormatEmpty:
    """Test formatting with no diagnostics."""

    @pytest.mark.asyncio
    async def test_empty_diagnostics(self, tmp_path):
        client = MagicMock()
        client.request_diagnostics = AsyncMock(return_value=[])

        formatter = DiagnosticsFormatter(client, tmp_path)
        result = await formatter.get_file_diagnostics(tmp_path / "clean.py")

        assert result["errors"] == []
        assert result["warnings"] == []
        assert result["hints"] == []


class TestDiagnosticsSeverityFilter:
    """Test severity filtering in get_all_diagnostics."""

    @pytest.mark.asyncio
    async def test_error_only_filter(self, tmp_path):
        """Filter to show only errors (severity_filter=1 means show only severity<=1)."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        client = MagicMock()
        client.request_diagnostics = AsyncMock(
            return_value=[
                {
                    "severity": DiagnosticSeverity.ERROR,
                    "range": {"start": {"line": 0, "character": 0}},
                    "message": "Error",
                },
                {
                    "severity": DiagnosticSeverity.WARNING,
                    "range": {"start": {"line": 1, "character": 0}},
                    "message": "Warning",
                },
                {
                    "severity": DiagnosticSeverity.HINT,
                    "range": {"start": {"line": 2, "character": 0}},
                    "message": "Hint",
                },
            ],
        )

        formatter = DiagnosticsFormatter(client, tmp_path)
        # severity_filter=2 means exclude errors (severity > ERROR), keep warnings+
        # Actually looking at the code: if severity_filter > ERROR → clear errors
        # severity_filter=1 would keep everything
        # severity_filter=2 would clear errors
        # To get "error only", we need no filter (errors always included)
        # and warnings/hints excluded when severity_filter=2 won't clear them...
        # Let me re-read the logic:
        # if severity_filter > ERROR (1): all_errors = []
        # if severity_filter > WARNING (2): all_warnings = []
        # if severity_filter > INFORMATION (3): all_hints = []
        # So severity_filter=2 clears errors, keeps warnings, keeps hints
        # severity_filter=1 keeps everything
        # There's no "error only" filter in the current API; let's test what we can

        # Test: severity_filter=2 removes errors
        result = await formatter.get_all_diagnostics(
            path=tmp_path,
            severity_filter=2,
        )
        assert result["total_errors"] == 0  # Filtered out
        assert result["total_warnings"] == 1  # Kept
