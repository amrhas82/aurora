"""
Unit tests for PythonParser.

Tests all extraction features:
- Function extraction
- Class extraction
- Method extraction
- Docstring extraction
- Complexity calculation
- Error handling
"""

from pathlib import Path

import pytest

from aurora_context_code.languages.python import PythonParser


class TestPythonParserBasics:
    """Test basic PythonParser functionality."""

    def test_parser_initialization(self):
        """Test that parser initializes correctly."""
        parser = PythonParser()
        assert parser.language == "python"

    def test_can_parse_py_files(self):
        """Test that parser recognizes .py files."""
        parser = PythonParser()
        assert parser.can_parse(Path("test.py"))
        assert parser.can_parse(Path("module.py"))
        assert parser.can_parse(Path("/absolute/path/to/file.py"))

    def test_can_parse_pyi_files(self):
        """Test that parser recognizes .pyi stub files."""
        parser = PythonParser()
        assert parser.can_parse(Path("test.pyi"))
        assert parser.can_parse(Path("stubs.pyi"))

    def test_cannot_parse_non_python_files(self):
        """Test that parser rejects non-Python files."""
        parser = PythonParser()
        assert not parser.can_parse(Path("test.js"))
        assert not parser.can_parse(Path("test.txt"))
        assert not parser.can_parse(Path("test.md"))
        assert not parser.can_parse(Path("test.pyc"))

    def test_parse_requires_absolute_path(self):
        """Test that parse() returns empty list for relative paths."""
        parser = PythonParser()
        # Relative path should log error and return empty
        result = parser.parse(Path("relative/path.py"))
        assert result == []

    def test_parse_nonexistent_file(self):
        """Test that parser handles missing files gracefully."""
        parser = PythonParser()
        result = parser.parse(Path("/nonexistent/file.py"))
        assert result == []


class TestFunctionExtraction:
    """Test function extraction from Python files."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PythonParser()

    @pytest.fixture
    def simple_file(self, tmp_path):
        """Create a simple test file with functions."""
        test_file = tmp_path / "test_simple.py"
        test_file.write_text("""
def greet(name):
    \"\"\"Say hello.\"\"\"
    return f"Hello, {name}"

def add(a, b):
    return a + b
""")
        return test_file

    def test_extract_simple_functions(self, parser, simple_file):
        """Test extraction of simple functions."""
        chunks = parser.parse(simple_file)
        assert len(chunks) == 2

        # Check first function
        greet = chunks[0]
        assert greet.element_type == "function"
        assert greet.name == "greet"
        assert "greet(name)" in greet.signature
        assert greet.docstring == "Say hello."
        assert greet.line_start > 0
        assert greet.line_end >= greet.line_start

        # Check second function
        add_func = chunks[1]
        assert add_func.element_type == "function"
        assert add_func.name == "add"
        assert "add(a, b)" in add_func.signature

    def test_function_without_docstring(self, parser, tmp_path):
        """Test extraction of function without docstring."""
        test_file = tmp_path / "no_docstring.py"
        test_file.write_text("""
def simple():
    return 42
""")
        chunks = parser.parse(test_file)
        assert len(chunks) == 1
        assert chunks[0].docstring is None


class TestClassExtraction:
    """Test class and method extraction."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PythonParser()

    @pytest.fixture
    def class_file(self, tmp_path):
        """Create a test file with a class."""
        test_file = tmp_path / "test_class.py"
        test_file.write_text("""
class Calculator:
    \"\"\"A simple calculator.\"\"\"

    def add(self, x, y):
        \"\"\"Add two numbers.\"\"\"
        return x + y

    def subtract(self, x, y):
        \"\"\"Subtract two numbers.\"\"\"
        return x - y
""")
        return test_file

    def test_extract_class(self, parser, class_file):
        """Test extraction of class definition."""
        chunks = parser.parse(class_file)

        # Should extract 1 class + 2 methods = 3 chunks
        assert len(chunks) == 3

        # Find the class chunk
        class_chunk = next(c for c in chunks if c.element_type == "class")
        assert class_chunk.name == "Calculator"
        assert class_chunk.docstring == "A simple calculator."

    def test_extract_methods(self, parser, class_file):
        """Test extraction of class methods."""
        chunks = parser.parse(class_file)

        # Find method chunks
        methods = [c for c in chunks if c.element_type == "method"]
        assert len(methods) == 2

        # Check method names are qualified
        method_names = {m.name for m in methods}
        assert "Calculator.add" in method_names
        assert "Calculator.subtract" in method_names

        # Check method docstrings
        add_method = next(m for m in methods if m.name == "Calculator.add")
        assert add_method.docstring == "Add two numbers."

    def test_class_with_inheritance(self, parser, tmp_path):
        """Test extraction of class with inheritance."""
        test_file = tmp_path / "inheritance.py"
        test_file.write_text("""
class Parent:
    pass

class Child(Parent):
    \"\"\"A child class.\"\"\"
    pass
""")
        chunks = parser.parse(test_file)

        # Should have 2 classes
        classes = [c for c in chunks if c.element_type == "class"]
        assert len(classes) == 2

        # Check child class signature includes parent
        child = next(c for c in classes if c.name == "Child")
        assert "Parent" in child.signature


class TestDocstringExtraction:
    """Test docstring extraction."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PythonParser()

    def test_single_quote_docstring(self, parser, tmp_path):
        """Test extraction of single-quoted docstring."""
        test_file = tmp_path / "single_quote.py"
        test_file.write_text("""
def func():
    'Single quote docstring'
    pass
""")
        chunks = parser.parse(test_file)
        assert len(chunks) == 1
        assert chunks[0].docstring == "Single quote docstring"

    def test_triple_quote_docstring(self, parser, tmp_path):
        """Test extraction of triple-quoted docstring."""
        test_file = tmp_path / "triple_quote.py"
        test_file.write_text('''
def func():
    """Triple quote docstring"""
    pass
''')
        chunks = parser.parse(test_file)
        assert len(chunks) == 1
        assert chunks[0].docstring == "Triple quote docstring"

    def test_multiline_docstring(self, parser, tmp_path):
        """Test extraction of multiline docstring."""
        test_file = tmp_path / "multiline.py"
        test_file.write_text('''
def func():
    """
    This is a
    multiline docstring.
    """
    pass
''')
        chunks = parser.parse(test_file)
        assert len(chunks) == 1
        # Docstring should be cleaned (whitespace normalized)
        assert chunks[0].docstring is not None
        assert "multiline docstring" in chunks[0].docstring


class TestComplexityCalculation:
    """Test cyclomatic complexity calculation."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PythonParser()

    def test_simple_function_zero_complexity(self, parser, tmp_path):
        """Test that simple function has zero complexity."""
        test_file = tmp_path / "simple.py"
        test_file.write_text("""
def simple():
    x = 1
    y = 2
    return x + y
""")
        chunks = parser.parse(test_file)
        assert len(chunks) == 1
        assert chunks[0].complexity_score == 0.0

    def test_function_with_if_statement(self, parser, tmp_path):
        """Test that if statement increases complexity."""
        test_file = tmp_path / "with_if.py"
        test_file.write_text("""
def with_if(x):
    if x > 0:
        return x
    return 0
""")
        chunks = parser.parse(test_file)
        assert len(chunks) == 1
        assert chunks[0].complexity_score > 0.0

    def test_function_with_multiple_branches(self, parser, tmp_path):
        """Test that multiple branches increase complexity."""
        test_file = tmp_path / "branches.py"
        test_file.write_text("""
def complex_func(x, y):
    if x > 0:
        for i in range(10):
            if i % 2 == 0:
                while y > 0:
                    y -= 1
                    try:
                        result = x / y
                    except ZeroDivisionError:
                        pass
    return x + y
""")
        chunks = parser.parse(test_file)
        assert len(chunks) == 1
        # Should have high complexity due to many branches
        assert chunks[0].complexity_score > 0.3

    def test_complexity_normalized_to_one(self, parser, tmp_path):
        """Test that complexity is normalized to [0.0, 1.0]."""
        test_file = tmp_path / "very_complex.py"
        # Create a function with many branches
        branches = "\n".join([f"    if x > {i}: pass" for i in range(50)])
        test_file.write_text(f"def very_complex(x):\n{branches}\n    return x")

        chunks = parser.parse(test_file)
        assert len(chunks) == 1
        assert 0.0 <= chunks[0].complexity_score <= 1.0


class TestErrorHandling:
    """Test error handling for broken files."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PythonParser()

    def test_parse_broken_syntax(self, parser, tmp_path):
        """Test that parser handles syntax errors gracefully."""
        test_file = tmp_path / "broken.py"
        test_file.write_text("""
def broken_function(:  # Syntax error
    return "broken"
""")
        # Should not raise exception, return partial results or empty
        chunks = parser.parse(test_file)
        assert isinstance(chunks, list)

    def test_parse_empty_file(self, parser, tmp_path):
        """Test that parser handles empty files."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        chunks = parser.parse(test_file)
        assert chunks == []

    def test_parse_file_with_only_comments(self, parser, tmp_path):
        """Test that parser handles files with only comments."""
        test_file = tmp_path / "comments.py"
        test_file.write_text("""
# This is a comment
# Another comment
""")
        chunks = parser.parse(test_file)
        assert chunks == []


class TestIntegrationWithFixtures:
    """Test parser with fixture files."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PythonParser()

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path."""
        return Path("/home/hamr/PycharmProjects/aurora/tests/fixtures/sample_python_files")

    def test_parse_simple_fixture(self, parser, fixtures_dir):
        """Test parsing simple.py fixture."""
        simple_file = fixtures_dir / "simple.py"
        if not simple_file.exists():
            pytest.skip("Fixture file not found")

        chunks = parser.parse(simple_file)
        assert len(chunks) == 2  # greet and add functions
        assert all(c.element_type == "function" for c in chunks)

    def test_parse_medium_fixture(self, parser, fixtures_dir):
        """Test parsing medium.py fixture."""
        medium_file = fixtures_dir / "medium.py"
        if not medium_file.exists():
            pytest.skip("Fixture file not found")

        chunks = parser.parse(medium_file)
        # Should have Calculator class + methods + process_file function
        assert len(chunks) > 5

        # Check we have both class and methods
        types = {c.element_type for c in chunks}
        assert "class" in types
        assert "method" in types
        assert "function" in types

    def test_parse_complex_fixture(self, parser, fixtures_dir):
        """Test parsing complex.py fixture."""
        complex_file = fixtures_dir / "complex.py"
        if not complex_file.exists():
            pytest.skip("Fixture file not found")

        chunks = parser.parse(complex_file)
        # Should extract many elements from complex file
        assert len(chunks) > 10

        # Check complexity scores vary
        complexities = [c.complexity_score for c in chunks]
        assert min(complexities) < max(complexities)

    def test_parse_broken_fixture(self, parser, fixtures_dir):
        """Test parsing broken.py fixture with syntax errors."""
        broken_file = fixtures_dir / "broken.py"
        if not broken_file.exists():
            pytest.skip("Fixture file not found")

        # Should not crash, return whatever it can parse
        chunks = parser.parse(broken_file)
        assert isinstance(chunks, list)
