"""Tests for TypeScript parser None handling."""

from unittest.mock import MagicMock

from aurora_context_code.languages.typescript import TypeScriptParser


def test_parse_handles_none_parser(tmp_path):
    """Test that parser handles None tsx_parser gracefully for .tsx files.

    When tree-sitter is unavailable, tsx_parser is None. The parser should
    check for None before calling .parse() and return fallback chunks.

    This test ensures mypy's union-attr error on line 94 is fixed.
    """
    # Create a .tsx test file
    tsx_file = tmp_path / "test.tsx"
    tsx_file.write_text(
        """
        function Hello() {
            return <div>Hello World</div>;
        }
    """
    )

    # Create parser instance
    parser = TypeScriptParser()

    # Mock scenario: self.parser is not None (passes line 89 check)
    # but tsx_parser is None (line 93 would select None for .tsx files)
    parser.parser = MagicMock()  # Line 89 check passes
    parser.tsx_parser = None  # Line 93 selects None for .tsx

    # This should handle None gracefully, not crash with AttributeError
    chunks = parser.parse(tsx_file)

    # Should get fallback chunks since selected parser is None
    assert len(chunks) > 0
    assert all(chunk.language == "typescript" for chunk in chunks)
    # Parser should detect None and use fallback
    assert all("fallback" in chunk.name for chunk in chunks)
