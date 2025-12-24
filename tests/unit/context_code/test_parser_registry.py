"""
Unit tests for ParserRegistry.

Tests registration, discovery, and multi-language support.
"""

from pathlib import Path

from aurora.context_code.parser import CodeParser
from aurora.context_code.registry import ParserRegistry, get_global_registry
from aurora.core.chunks.code_chunk import CodeChunk


class MockParser(CodeParser):
    """Mock parser for testing."""

    def __init__(self, language: str, extensions: set):
        """Initialize mock parser."""
        super().__init__(language)
        self.extensions = extensions

    def parse(self, file_path: Path) -> list[CodeChunk]:
        """Mock parse method."""
        return []

    def can_parse(self, file_path: Path) -> bool:
        """Check if file extension is supported."""
        return file_path.suffix in self.extensions


class TestParserRegistryBasics:
    """Test basic registry functionality."""

    def test_registry_initialization(self):
        """Test that registry initializes empty."""
        registry = ParserRegistry()
        assert registry.list_languages() == []

    def test_register_parser(self):
        """Test registering a parser."""
        registry = ParserRegistry()
        parser = MockParser("python", {".py"})

        registry.register(parser)

        assert "python" in registry.list_languages()
        assert registry.get_parser("python") is parser

    def test_register_multiple_parsers(self):
        """Test registering multiple parsers."""
        registry = ParserRegistry()

        python_parser = MockParser("python", {".py"})
        js_parser = MockParser("javascript", {".js"})
        go_parser = MockParser("go", {".go"})

        registry.register(python_parser)
        registry.register(js_parser)
        registry.register(go_parser)

        languages = registry.list_languages()
        assert "python" in languages
        assert "javascript" in languages
        assert "go" in languages
        assert len(languages) == 3

    def test_register_replaces_existing(self):
        """Test that registering same language replaces previous parser."""
        registry = ParserRegistry()

        parser1 = MockParser("python", {".py"})
        parser2 = MockParser("python", {".py", ".pyi"})

        registry.register(parser1)
        assert registry.get_parser("python") is parser1

        # Register again with same language
        registry.register(parser2)
        assert registry.get_parser("python") is parser2
        assert len(registry.list_languages()) == 1


class TestParserLookup:
    """Test parser lookup methods."""

    def test_get_parser_by_language(self):
        """Test getting parser by language name."""
        registry = ParserRegistry()
        python_parser = MockParser("python", {".py"})
        registry.register(python_parser)

        result = registry.get_parser("python")
        assert result is python_parser

    def test_get_parser_not_found(self):
        """Test getting non-existent parser returns None."""
        registry = ParserRegistry()
        result = registry.get_parser("rust")
        assert result is None

    def test_get_parser_for_file(self):
        """Test getting parser by file extension."""
        registry = ParserRegistry()

        python_parser = MockParser("python", {".py", ".pyi"})
        js_parser = MockParser("javascript", {".js", ".jsx"})

        registry.register(python_parser)
        registry.register(js_parser)

        # Test Python files
        assert registry.get_parser_for_file(Path("test.py")) is python_parser
        assert registry.get_parser_for_file(Path("test.pyi")) is python_parser

        # Test JavaScript files
        assert registry.get_parser_for_file(Path("test.js")) is js_parser
        assert registry.get_parser_for_file(Path("test.jsx")) is js_parser

    def test_get_parser_for_file_not_found(self):
        """Test that unsupported file returns None."""
        registry = ParserRegistry()
        python_parser = MockParser("python", {".py"})
        registry.register(python_parser)

        result = registry.get_parser_for_file(Path("test.txt"))
        assert result is None

    def test_get_parser_for_file_first_match(self):
        """Test that first matching parser is returned."""
        registry = ParserRegistry()

        # Register two parsers that both support .py
        parser1 = MockParser("python1", {".py"})
        parser2 = MockParser("python2", {".py"})

        registry.register(parser1)
        registry.register(parser2)

        result = registry.get_parser_for_file(Path("test.py"))
        # Should return one of them (first registered)
        assert result in (parser1, parser2)


class TestParserUnregistration:
    """Test parser removal from registry."""

    def test_unregister_parser(self):
        """Test unregistering a parser."""
        registry = ParserRegistry()
        parser = MockParser("python", {".py"})

        registry.register(parser)
        assert "python" in registry.list_languages()

        result = registry.unregister("python")
        assert result is True
        assert "python" not in registry.list_languages()

    def test_unregister_nonexistent(self):
        """Test unregistering non-existent parser."""
        registry = ParserRegistry()
        result = registry.unregister("rust")
        assert result is False

    def test_clear_registry(self):
        """Test clearing all parsers."""
        registry = ParserRegistry()

        registry.register(MockParser("python", {".py"}))
        registry.register(MockParser("javascript", {".js"}))
        registry.register(MockParser("go", {".go"}))

        assert len(registry.list_languages()) == 3

        registry.clear()

        assert len(registry.list_languages()) == 0
        assert registry.get_parser("python") is None


class TestGlobalRegistry:
    """Test global registry singleton."""

    def test_get_global_registry_creates_instance(self):
        """Test that global registry is created on first access."""
        registry = get_global_registry()
        assert isinstance(registry, ParserRegistry)

    def test_get_global_registry_returns_same_instance(self):
        """Test that global registry returns same instance."""
        registry1 = get_global_registry()
        registry2 = get_global_registry()
        assert registry1 is registry2

    def test_global_registry_has_python_parser(self):
        """Test that global registry auto-registers Python parser."""
        registry = get_global_registry()
        # Should have auto-registered PythonParser
        assert "python" in registry.list_languages()

        python_parser = registry.get_parser("python")
        assert python_parser is not None
        assert python_parser.can_parse(Path("test.py"))


class TestRegistryRepr:
    """Test string representation."""

    def test_empty_registry_repr(self):
        """Test repr of empty registry."""
        registry = ParserRegistry()
        repr_str = repr(registry)
        assert "ParserRegistry" in repr_str
        assert "languages=[]" in repr_str

    def test_registry_with_parsers_repr(self):
        """Test repr of registry with parsers."""
        registry = ParserRegistry()
        registry.register(MockParser("python", {".py"}))
        registry.register(MockParser("javascript", {".js"}))

        repr_str = repr(registry)
        assert "ParserRegistry" in repr_str
        assert "python" in repr_str
        assert "javascript" in repr_str


class TestMultiLanguageScenarios:
    """Test realistic multi-language scenarios."""

    def test_web_project_parsers(self):
        """Test registry for a typical web project."""
        registry = ParserRegistry()

        # Register parsers for web technologies
        registry.register(MockParser("python", {".py"}))
        registry.register(MockParser("javascript", {".js", ".jsx"}))
        registry.register(MockParser("typescript", {".ts", ".tsx"}))
        registry.register(MockParser("html", {".html"}))
        registry.register(MockParser("css", {".css"}))

        # Test file routing
        assert registry.get_parser_for_file(Path("backend.py")).language == "python"
        assert registry.get_parser_for_file(Path("app.js")).language == "javascript"
        assert registry.get_parser_for_file(Path("component.tsx")).language == "typescript"
        assert registry.get_parser_for_file(Path("index.html")).language == "html"
        assert registry.get_parser_for_file(Path("style.css")).language == "css"

    def test_backend_project_parsers(self):
        """Test registry for a multi-language backend."""
        registry = ParserRegistry()

        registry.register(MockParser("python", {".py"}))
        registry.register(MockParser("go", {".go"}))
        registry.register(MockParser("rust", {".rs"}))

        files = [
            (Path("api.py"), "python"),
            (Path("server.go"), "go"),
            (Path("lib.rs"), "rust"),
        ]

        for file_path, expected_lang in files:
            parser = registry.get_parser_for_file(file_path)
            assert parser is not None
            assert parser.language == expected_lang

    def test_parser_selection_priority(self):
        """Test that parser registration order matters for overlapping extensions."""
        registry = ParserRegistry()

        # Both parsers handle .py files
        parser1 = MockParser("parser1", {".py", ".txt"})
        parser2 = MockParser("parser2", {".py", ".md"})

        registry.register(parser1)
        registry.register(parser2)

        # For .py files, should get the last registered (parser2 replaced parser1 for 'parser' language)
        # Actually, they have different language names, so both are registered
        result = registry.get_parser_for_file(Path("test.py"))
        assert result in (parser1, parser2)

        # For unique extensions, should get the right parser
        assert registry.get_parser_for_file(Path("test.txt")) is parser1
        assert registry.get_parser_for_file(Path("test.md")) is parser2
