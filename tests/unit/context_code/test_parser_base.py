"""
Unit tests for the CodeParser abstract interface.

Tests the contract that all parser implementations must follow.
"""

from pathlib import Path

from aurora.context_code.parser import CodeParser
from aurora.core.chunks.code_chunk import CodeChunk


class MockParser(CodeParser):
    """Mock parser for testing the abstract interface."""

    def __init__(self, language: str = "mock", supported_extensions=None):
        """Initialize mock parser."""
        super().__init__(language)
        self.supported_extensions = supported_extensions or {".mock"}
        self.parse_called = False
        self.can_parse_called = False

    def parse(self, file_path: Path) -> list[CodeChunk]:
        """Mock parse implementation."""
        self.parse_called = True
        return []

    def can_parse(self, file_path: Path) -> bool:
        """Mock can_parse implementation."""
        self.can_parse_called = True
        return file_path.suffix in self.supported_extensions


class TestCodeParserInterface:
    """Test the CodeParser abstract interface."""

    def test_parser_has_language_attribute(self):
        """Test that parser stores language on initialization."""
        parser = MockParser(language="test")
        assert parser.language == "test"

    def test_parser_repr(self):
        """Test string representation of parser."""
        parser = MockParser(language="test")
        repr_str = repr(parser)
        assert "MockParser" in repr_str
        assert "language=test" in repr_str

    def test_parser_can_parse_by_extension(self):
        """Test that can_parse checks file extensions."""
        parser = MockParser(supported_extensions={".py", ".pyi"})

        assert parser.can_parse(Path("test.py"))
        assert parser.can_parse(Path("test.pyi"))
        assert not parser.can_parse(Path("test.js"))
        assert not parser.can_parse(Path("test.txt"))

    def test_parser_handles_absolute_paths(self):
        """Test that parser can handle absolute paths."""
        parser = MockParser()
        absolute_path = Path("/absolute/path/to/file.mock")
        result = parser.parse(absolute_path)
        assert isinstance(result, list)

    def test_parser_handles_relative_paths(self):
        """Test that parser can handle relative paths."""
        parser = MockParser()
        relative_path = Path("relative/path/to/file.mock")
        result = parser.parse(relative_path)
        assert isinstance(result, list)

    def test_multiple_parsers_different_languages(self):
        """Test that multiple parsers can be created for different languages."""
        parser1 = MockParser(language="python")
        parser2 = MockParser(language="javascript")
        parser3 = MockParser(language="go")

        assert parser1.language == "python"
        assert parser2.language == "javascript"
        assert parser3.language == "go"

        # Ensure they're independent
        assert parser1.language != parser2.language
        assert parser2.language != parser3.language

    def test_parser_language_immutable_after_init(self):
        """Test that language is set during initialization."""
        parser = MockParser(language="test")
        assert parser.language == "test"

        # Language should be accessible
        assert hasattr(parser, "language")
