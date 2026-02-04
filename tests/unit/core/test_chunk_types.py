"""Unit tests for chunk type registry.

Tests the central type determination logic for chunks.
"""

from pathlib import Path

from aurora_core.chunk_types import (
    CONTEXT_TYPE_MAP,
    EXTENSION_TYPE_MAP,
    VALID_TYPES,
    get_chunk_type,
)


class TestExtensionTypeMap:
    """Tests for extension-based type mapping."""

    def test_python_files_are_code(self):
        """Python files should be type 'code'."""
        assert get_chunk_type(file_path="test.py") == "code"
        assert get_chunk_type(file_path="module.pyi") == "code"
        assert get_chunk_type(file_path=Path("src/main.py")) == "code"

    def test_javascript_files_are_code(self):
        """JavaScript files should be type 'code'."""
        assert get_chunk_type(file_path="app.js") == "code"
        assert get_chunk_type(file_path="component.jsx") == "code"

    def test_typescript_files_are_code(self):
        """TypeScript files should be type 'code'."""
        assert get_chunk_type(file_path="app.ts") == "code"
        assert get_chunk_type(file_path="component.tsx") == "code"

    def test_markdown_files_are_kb(self):
        """Markdown files should be type 'kb'."""
        assert get_chunk_type(file_path="readme.md") == "kb"
        assert get_chunk_type(file_path="docs/guide.markdown") == "kb"
        assert get_chunk_type(file_path=Path("CHANGELOG.md")) == "kb"

    def test_document_files_are_doc(self):
        """PDF, DOCX, TXT files should be type 'doc'."""
        assert get_chunk_type(file_path="manual.pdf") == "doc"
        assert get_chunk_type(file_path="report.docx") == "doc"
        assert get_chunk_type(file_path="notes.txt") == "doc"

    def test_unknown_extension_defaults_to_code(self):
        """Unknown extensions should default to 'code'."""
        assert get_chunk_type(file_path="config.yaml") == "code"
        assert get_chunk_type(file_path="data.json") == "code"
        assert get_chunk_type(file_path="script.sh") == "code"

    def test_case_insensitive_extensions(self):
        """Extension matching should be case-insensitive."""
        assert get_chunk_type(file_path="README.MD") == "kb"
        assert get_chunk_type(file_path="test.PY") == "code"
        assert get_chunk_type(file_path="doc.PDF") == "doc"


class TestContextTypeMap:
    """Tests for context-based type mapping."""

    def test_soar_result_context_is_reas(self):
        """SOAR results should be type 'reas'."""
        assert get_chunk_type(context="soar_result") == "reas"

    def test_goals_output_context_is_reas(self):
        """Goals output should be type 'reas'."""
        assert get_chunk_type(context="goals_output") == "reas"

    def test_context_overrides_extension(self):
        """Context should override extension-based type."""
        # .md file with soar context should be 'reas', not 'kb'
        assert get_chunk_type(file_path="conversation.md", context="soar_result") == "reas"
        assert get_chunk_type(file_path="goals-log.md", context="goals_output") == "reas"

    def test_unknown_context_falls_back_to_extension(self):
        """Unknown context should fall back to extension-based type."""
        assert get_chunk_type(file_path="test.py", context="unknown_context") == "code"
        assert get_chunk_type(file_path="readme.md", context="invalid") == "kb"


class TestEdgeCases:
    """Tests for edge cases and defaults."""

    def test_no_arguments_returns_code(self):
        """No arguments should return 'code' as default."""
        assert get_chunk_type() == "code"

    def test_none_file_path_returns_code(self):
        """None file_path should return 'code' as default."""
        assert get_chunk_type(file_path=None) == "code"

    def test_empty_string_file_path(self):
        """Empty string file_path should return 'code' as default."""
        assert get_chunk_type(file_path="") == "code"

    def test_file_path_with_no_extension(self):
        """File with no extension should return 'code' as default."""
        assert get_chunk_type(file_path="Makefile") == "code"
        assert get_chunk_type(file_path="Dockerfile") == "code"

    def test_path_object_works(self):
        """Path objects should work same as strings."""
        assert get_chunk_type(file_path=Path("src/module.py")) == "code"
        assert get_chunk_type(file_path=Path("docs/README.md")) == "kb"


class TestValidTypes:
    """Tests for VALID_TYPES constant."""

    def test_valid_types_contains_all_types(self):
        """VALID_TYPES should contain all expected types."""
        assert "code" in VALID_TYPES
        assert "kb" in VALID_TYPES
        assert "doc" in VALID_TYPES
        assert "reas" in VALID_TYPES

    def test_valid_types_is_frozen(self):
        """VALID_TYPES should be a frozenset (immutable)."""
        assert isinstance(VALID_TYPES, frozenset)


class TestMapsCompleteness:
    """Tests to ensure maps are complete and consistent."""

    def test_extension_map_has_expected_entries(self):
        """Extension map should have all expected entries."""
        expected_extensions = {
            ".py",
            ".pyi",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".md",
            ".markdown",
            ".pdf",
            ".docx",
            ".txt",
        }
        assert expected_extensions.issubset(set(EXTENSION_TYPE_MAP.keys()))

    def test_all_extension_types_are_valid(self):
        """All types in extension map should be valid types."""
        for ext_type in EXTENSION_TYPE_MAP.values():
            assert ext_type in VALID_TYPES

    def test_all_context_types_are_valid(self):
        """All types in context map should be valid types."""
        for ctx_type in CONTEXT_TYPE_MAP.values():
            assert ctx_type in VALID_TYPES
