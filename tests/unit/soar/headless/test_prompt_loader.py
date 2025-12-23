"""
Unit tests for PromptLoader.

Tests prompt file parsing and validation including:
- File existence and readability
- Section extraction (Goal, Success Criteria, Constraints, Context)
- List item parsing (markdown format)
- Format validation with helpful error messages
- Summary generation
- Edge cases and error handling
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from aurora_soar.headless.prompt_loader import (
    PromptData,
    PromptLoader,
    PromptValidationError,
)


class TestPromptData:
    """Test PromptData dataclass."""

    def test_prompt_data_creation(self):
        """Test creating PromptData with all fields."""
        data = PromptData(
            goal="Implement feature X",
            success_criteria=["All tests pass", "Code coverage > 80%"],
            constraints=["Budget limit: $5.00"],
            context="Additional background info",
            raw_content="# Goal\nImplement feature X",
        )
        assert data.goal == "Implement feature X"
        assert len(data.success_criteria) == 2
        assert len(data.constraints) == 1
        assert data.context == "Additional background info"
        assert data.raw_content == "# Goal\nImplement feature X"

    def test_prompt_data_minimal(self):
        """Test creating PromptData with required fields only."""
        data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"],
            constraints=[],
        )
        assert data.goal == "Test goal"
        assert data.success_criteria == ["Criterion 1"]
        assert data.constraints == []
        assert data.context is None
        assert data.raw_content == ""

    def test_prompt_data_optional_defaults(self):
        """Test PromptData optional field defaults."""
        data = PromptData(
            goal="Test", success_criteria=["A"], constraints=[]
        )
        assert data.context is None
        assert data.raw_content == ""


class TestPromptValidationError:
    """Test PromptValidationError exception."""

    def test_validation_error_message(self):
        """Test PromptValidationError with custom message."""
        error = PromptValidationError("Custom error message")
        assert str(error) == "Custom error message"

    def test_validation_error_is_exception(self):
        """Test PromptValidationError is an Exception."""
        error = PromptValidationError("Test")
        assert isinstance(error, Exception)


class TestPromptLoaderInit:
    """Test PromptLoader initialization."""

    def test_init_with_string_path(self):
        """Test initialization with string path."""
        loader = PromptLoader("/path/to/prompt.md")
        assert loader.prompt_path == Path("/path/to/prompt.md")

    def test_init_with_path_object(self):
        """Test initialization with Path object."""
        path = Path("/path/to/prompt.md")
        loader = PromptLoader(path)
        assert loader.prompt_path == path

    def test_init_converts_to_path(self):
        """Test path is always converted to Path object."""
        loader = PromptLoader("prompt.md")
        assert isinstance(loader.prompt_path, Path)


class TestFileExists:
    """Test file_exists method."""

    def test_file_exists_true(self):
        """Test file_exists returns True for existing file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Goal\nTest")
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            assert loader.file_exists() is True
        finally:
            Path(temp_path).unlink()

    def test_file_exists_false_missing(self):
        """Test file_exists returns False for missing file."""
        loader = PromptLoader("/nonexistent/path/prompt.md")
        assert loader.file_exists() is False

    def test_file_exists_false_directory(self):
        """Test file_exists returns False for directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = PromptLoader(tmpdir)
            assert loader.file_exists() is False


class TestReadFile:
    """Test _read_file method."""

    def test_read_file_success(self):
        """Test reading valid UTF-8 file."""
        content = "# Goal\nImplement feature X\n\n# Success Criteria\n- Test 1"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            result = loader._read_file()
            assert result == content
        finally:
            Path(temp_path).unlink()

    def test_read_file_missing(self):
        """Test reading missing file raises PromptValidationError."""
        loader = PromptLoader("/nonexistent/prompt.md")
        with pytest.raises(PromptValidationError) as exc_info:
            loader._read_file()
        assert "Prompt file not found" in str(exc_info.value)
        assert "Please create a prompt file" in str(exc_info.value)

    def test_read_file_unicode_error(self):
        """Test reading non-UTF-8 file raises PromptValidationError."""
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".md", delete=False
        ) as f:
            # Write invalid UTF-8 bytes
            f.write(b"\xff\xfe Invalid UTF-8")
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            with pytest.raises(PromptValidationError) as exc_info:
                loader._read_file()
            assert "not valid UTF-8" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()

    @patch("pathlib.Path.read_text")
    def test_read_file_permission_error(self, mock_read):
        """Test reading file with permission error."""
        mock_read.side_effect = PermissionError("Access denied")

        # Create actual file so file_exists() passes
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            with pytest.raises(PromptValidationError) as exc_info:
                loader._read_file()
            assert "Permission denied" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()

    @patch("pathlib.Path.read_text")
    def test_read_file_generic_error(self, mock_read):
        """Test reading file with generic error."""
        mock_read.side_effect = OSError("Disk error")

        # Create actual file so file_exists() passes
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            with pytest.raises(PromptValidationError) as exc_info:
                loader._read_file()
            assert "Error reading prompt file" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()


class TestExtractSectionContent:
    """Test _extract_section_content method."""

    def test_extract_goal_section(self):
        """Test extracting Goal section content."""
        content = """# Goal
Implement feature X with tests

# Success Criteria
- Test 1"""
        loader = PromptLoader("test.md")
        result = loader._extract_section_content(content, loader.GOAL_HEADER)
        assert result == "Implement feature X with tests"

    def test_extract_section_missing(self):
        """Test extracting missing section returns empty string."""
        content = "# Goal\nTest goal"
        loader = PromptLoader("test.md")
        result = loader._extract_section_content(
            content, loader.SUCCESS_CRITERIA_HEADER
        )
        assert result == ""

    def test_extract_section_at_end(self):
        """Test extracting section at end of file."""
        content = """# Goal
Test goal

# Context
This is the last section with some content."""
        loader = PromptLoader("test.md")
        result = loader._extract_section_content(content, loader.CONTEXT_HEADER)
        assert result == "This is the last section with some content."

    def test_extract_section_with_whitespace(self):
        """Test section extraction trims whitespace."""
        content = """# Goal


  Implement feature X


# Success Criteria"""
        loader = PromptLoader("test.md")
        result = loader._extract_section_content(content, loader.GOAL_HEADER)
        assert result == "Implement feature X"

    def test_extract_section_case_insensitive(self):
        """Test section extraction is case-insensitive."""
        content = """# GOAL
Test goal

# success criteria
- Test"""
        loader = PromptLoader("test.md")
        result = loader._extract_section_content(content, loader.GOAL_HEADER)
        assert result == "Test goal"


class TestParseListItems:
    """Test _parse_list_items method."""

    def test_parse_list_dash_format(self):
        """Test parsing list with '- item' format."""
        content = """- Item 1
- Item 2
- Item 3"""
        loader = PromptLoader("test.md")
        result = loader._parse_list_items(content)
        assert result == ["Item 1", "Item 2", "Item 3"]

    def test_parse_list_asterisk_format(self):
        """Test parsing list with '* item' format."""
        content = """* Item 1
* Item 2"""
        loader = PromptLoader("test.md")
        result = loader._parse_list_items(content)
        assert result == ["Item 1", "Item 2"]

    def test_parse_list_mixed_format(self):
        """Test parsing list with mixed '- ' and '* ' format."""
        content = """- Item 1
* Item 2
- Item 3"""
        loader = PromptLoader("test.md")
        result = loader._parse_list_items(content)
        assert result == ["Item 1", "Item 2", "Item 3"]

    def test_parse_list_with_whitespace(self):
        """Test parsing list items trims whitespace."""
        content = """  - Item 1
-   Item 2
-  Item 3   """
        loader = PromptLoader("test.md")
        result = loader._parse_list_items(content)
        assert result == ["Item 1", "Item 2", "Item 3"]

    def test_parse_list_empty_items_skipped(self):
        """Test empty list items are skipped."""
        content = """- Item 1
-
- Item 2
*
- Item 3"""
        loader = PromptLoader("test.md")
        result = loader._parse_list_items(content)
        assert result == ["Item 1", "Item 2", "Item 3"]

    def test_parse_list_no_items(self):
        """Test parsing content with no list items."""
        content = "Just some text without list markers"
        loader = PromptLoader("test.md")
        result = loader._parse_list_items(content)
        assert result == []

    def test_parse_list_multiline_text(self):
        """Test list parsing with multiline content."""
        content = """Some text before
- Item 1
More text
- Item 2
Text after"""
        loader = PromptLoader("test.md")
        result = loader._parse_list_items(content)
        assert result == ["Item 1", "Item 2"]


class TestFindAllSections:
    """Test _find_all_sections method."""

    def test_find_all_sections_complete(self):
        """Test finding all required sections."""
        content = """# Goal
Test

# Success Criteria
- Test

# Constraints
- Test

# Context
Info"""
        loader = PromptLoader("test.md")
        sections = loader._find_all_sections(content)
        assert "goal" in sections
        assert "success criteria" in sections
        assert "constraints" in sections
        assert "context" in sections

    def test_find_sections_positions(self):
        """Test section positions are returned."""
        content = """# Goal
Test

# Success Criteria
- Test"""
        loader = PromptLoader("test.md")
        sections = loader._find_all_sections(content)
        assert sections["goal"] < sections["success criteria"]

    def test_find_sections_case_normalized(self):
        """Test section names are normalized to lowercase."""
        content = """# GOAL
Test

# Success Criteria"""
        loader = PromptLoader("test.md")
        sections = loader._find_all_sections(content)
        assert "goal" in sections
        assert "success criteria" in sections


class TestParse:
    """Test parse method."""

    def test_parse_valid_complete(self):
        """Test parsing valid prompt with all sections."""
        content = """# Goal
Implement feature X with comprehensive tests

# Success Criteria
- All tests pass
- Code coverage > 80%
- Documentation updated

# Constraints
- Budget limit: $5.00
- Max iterations: 10

# Context
This is additional background information."""
        loader = PromptLoader("test.md")
        result = loader.parse(content)

        assert result.goal == "Implement feature X with comprehensive tests"
        assert len(result.success_criteria) == 3
        assert "All tests pass" in result.success_criteria
        assert len(result.constraints) == 2
        assert "Budget limit: $5.00" in result.constraints
        assert result.context == "This is additional background information."
        assert result.raw_content == content

    def test_parse_valid_minimal(self):
        """Test parsing valid prompt with minimal required sections."""
        content = """# Goal
Simple goal

# Success Criteria
- Criterion 1

# Constraints"""
        loader = PromptLoader("test.md")
        result = loader.parse(content)

        assert result.goal == "Simple goal"
        assert result.success_criteria == ["Criterion 1"]
        assert result.constraints == []
        assert result.context is None

    def test_parse_missing_goal(self):
        """Test parsing fails without Goal section."""
        content = """# Success Criteria
- Test

# Constraints
- Test"""
        loader = PromptLoader("test.md")
        with pytest.raises(PromptValidationError) as exc_info:
            loader.parse(content)
        assert "missing required '# Goal' section" in str(exc_info.value)
        assert "Example format:" in str(exc_info.value)

    def test_parse_missing_success_criteria(self):
        """Test parsing fails without Success Criteria section."""
        content = """# Goal
Test goal

# Constraints
- Test"""
        loader = PromptLoader("test.md")
        with pytest.raises(PromptValidationError) as exc_info:
            loader.parse(content)
        assert "missing required '# Success Criteria' section" in str(exc_info.value)

    def test_parse_missing_constraints(self):
        """Test parsing fails without Constraints section."""
        content = """# Goal
Test goal

# Success Criteria
- Test"""
        loader = PromptLoader("test.md")
        with pytest.raises(PromptValidationError) as exc_info:
            loader.parse(content)
        assert "missing required '# Constraints' section" in str(exc_info.value)

    def test_parse_empty_goal(self):
        """Test parsing fails with empty Goal section."""
        content = """# Goal

# Success Criteria
- Test

# Constraints
- Test"""
        loader = PromptLoader("test.md")
        with pytest.raises(PromptValidationError) as exc_info:
            loader.parse(content)
        assert "missing required '# Goal' section" in str(exc_info.value)

    def test_parse_empty_success_criteria(self):
        """Test parsing fails with empty Success Criteria list."""
        content = """# Goal
Test goal

# Success Criteria
Some text but no list items

# Constraints
- Test"""
        loader = PromptLoader("test.md")
        with pytest.raises(PromptValidationError) as exc_info:
            loader.parse(content)
        assert "Success Criteria section must contain at least one item" in str(
            exc_info.value
        )

    def test_parse_empty_constraints_allowed(self):
        """Test parsing succeeds with empty Constraints section."""
        content = """# Goal
Test goal

# Success Criteria
- Criterion 1

# Constraints"""
        loader = PromptLoader("test.md")
        result = loader.parse(content)
        assert result.constraints == []

    def test_parse_context_optional(self):
        """Test Context section is optional."""
        content = """# Goal
Test goal

# Success Criteria
- Criterion 1

# Constraints
- Constraint 1"""
        loader = PromptLoader("test.md")
        result = loader.parse(content)
        assert result.context is None

    def test_parse_case_insensitive_headers(self):
        """Test parsing works with different header cases."""
        content = """# GOAL
Test goal

# success criteria
- Criterion 1

# CONSTRAINTS
- Constraint 1"""
        loader = PromptLoader("test.md")
        result = loader.parse(content)
        assert result.goal == "Test goal"
        assert result.success_criteria == ["Criterion 1"]

    def test_parse_constraint_singular(self):
        """Test parsing accepts singular 'Constraint' header."""
        content = """# Goal
Test goal

# Success Criteria
- Criterion 1

# Constraint
- Constraint 1"""
        loader = PromptLoader("test.md")
        result = loader.parse(content)
        assert result.constraints == ["Constraint 1"]


class TestLoad:
    """Test load method."""

    def test_load_success(self):
        """Test load reads and parses file successfully."""
        content = """# Goal
Implement feature X

# Success Criteria
- All tests pass

# Constraints
- Budget: $5.00"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            result = loader.load()
            assert result.goal == "Implement feature X"
            assert result.success_criteria == ["All tests pass"]
            assert result.constraints == ["Budget: $5.00"]
        finally:
            Path(temp_path).unlink()

    def test_load_missing_file(self):
        """Test load raises error for missing file."""
        loader = PromptLoader("/nonexistent/prompt.md")
        with pytest.raises(PromptValidationError) as exc_info:
            loader.load()
        assert "Prompt file not found" in str(exc_info.value)

    def test_load_invalid_format(self):
        """Test load raises error for invalid format."""
        content = "# Goal\nTest goal\n# Success Criteria\n- Test"
        # Missing Constraints section
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            with pytest.raises(PromptValidationError):
                loader.load()
        finally:
            Path(temp_path).unlink()


class TestValidateFormat:
    """Test validate_format method."""

    def test_validate_format_valid(self):
        """Test validate_format returns True for valid file."""
        content = """# Goal
Test goal

# Success Criteria
- Criterion 1

# Constraints
- Constraint 1"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            is_valid, errors = loader.validate_format()
            assert is_valid is True
            assert errors == []
        finally:
            Path(temp_path).unlink()

    def test_validate_format_missing_file(self):
        """Test validate_format returns False for missing file."""
        loader = PromptLoader("/nonexistent/prompt.md")
        is_valid, errors = loader.validate_format()
        assert is_valid is False
        assert len(errors) == 1
        assert "File not found" in errors[0]

    def test_validate_format_missing_goal(self):
        """Test validate_format catches missing Goal section."""
        content = """# Success Criteria
- Test

# Constraints
- Test"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            is_valid, errors = loader.validate_format()
            assert is_valid is False
            assert any("Missing required section: # Goal" in e for e in errors)
        finally:
            Path(temp_path).unlink()

    def test_validate_format_missing_success_criteria(self):
        """Test validate_format catches missing Success Criteria section."""
        content = """# Goal
Test

# Constraints
- Test"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            is_valid, errors = loader.validate_format()
            assert is_valid is False
            assert any(
                "Missing required section: # Success Criteria" in e for e in errors
            )
        finally:
            Path(temp_path).unlink()

    def test_validate_format_missing_constraints(self):
        """Test validate_format catches missing Constraints section."""
        content = """# Goal
Test

# Success Criteria
- Test"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            is_valid, errors = loader.validate_format()
            assert is_valid is False
            assert any("Missing required section: # Constraints" in e for e in errors)
        finally:
            Path(temp_path).unlink()

    def test_validate_format_empty_success_criteria(self):
        """Test validate_format catches empty Success Criteria."""
        content = """# Goal
Test goal

# Success Criteria
Some text but no list items

# Constraints
- Test"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            is_valid, errors = loader.validate_format()
            assert is_valid is False
            assert any(
                "Success Criteria section must contain at least one item" in e
                for e in errors
            )
        finally:
            Path(temp_path).unlink()

    def test_validate_format_multiple_errors(self):
        """Test validate_format reports multiple errors."""
        content = """# Success Criteria
- Test"""
        # Missing Goal and Constraints
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            is_valid, errors = loader.validate_format()
            assert is_valid is False
            assert len(errors) >= 2
        finally:
            Path(temp_path).unlink()


class TestGetSummary:
    """Test get_summary method."""

    def test_get_summary_valid_file(self):
        """Test get_summary returns complete information for valid file."""
        content = """# Goal
Test goal

# Success Criteria
- Criterion 1

# Constraints
- Constraint 1

# Context
Background info"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            summary = loader.get_summary()
            assert summary["file_path"] == str(temp_path)
            assert summary["exists"] is True
            assert summary["has_goal"] is True
            assert summary["has_success_criteria"] is True
            assert summary["has_constraints"] is True
            assert summary["has_context"] is True
            assert summary["is_valid"] is True
        finally:
            Path(temp_path).unlink()

    def test_get_summary_missing_file(self):
        """Test get_summary for missing file."""
        loader = PromptLoader("/nonexistent/prompt.md")
        summary = loader.get_summary()
        assert summary["exists"] is False
        assert summary["has_goal"] is False
        assert summary["has_success_criteria"] is False
        assert summary["has_constraints"] is False
        assert summary["has_context"] is False
        assert summary["is_valid"] is False

    def test_get_summary_no_context(self):
        """Test get_summary shows has_context=False when missing."""
        content = """# Goal
Test goal

# Success Criteria
- Criterion 1

# Constraints
- Constraint 1"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            summary = loader.get_summary()
            assert summary["has_context"] is False
            assert summary["is_valid"] is True
        finally:
            Path(temp_path).unlink()

    def test_get_summary_invalid_format(self):
        """Test get_summary shows is_valid=False for invalid format."""
        content = """# Goal
Test goal

# Success Criteria"""
        # Missing Constraints section
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            summary = loader.get_summary()
            assert summary["exists"] is True
            assert summary["has_goal"] is True
            assert summary["has_success_criteria"] is True
            assert summary["has_constraints"] is False
            assert summary["is_valid"] is False
        finally:
            Path(temp_path).unlink()


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_multiline_goal(self):
        """Test parsing goal with multiple lines."""
        content = """# Goal
Implement feature X with comprehensive tests.
The implementation should follow best practices
and include documentation.

# Success Criteria
- All tests pass

# Constraints
- Budget: $5.00"""
        loader = PromptLoader("test.md")
        result = loader.parse(content)
        assert "Implement feature X" in result.goal
        assert "best practices" in result.goal
        assert "documentation" in result.goal

    def test_extra_whitespace_in_sections(self):
        """Test parsing handles extra whitespace gracefully."""
        content = """# Goal


   Implement feature X


# Success Criteria

   - All tests pass
   - Coverage > 80%

# Constraints

   - Budget: $5.00   """
        loader = PromptLoader("test.md")
        result = loader.parse(content)
        assert result.goal == "Implement feature X"
        assert "All tests pass" in result.success_criteria
        assert "Coverage > 80%" in result.success_criteria

    def test_complex_list_items(self):
        """Test parsing complex list items with special characters."""
        content = """# Goal
Test

# Success Criteria
- Test with "quotes"
- Test with (parentheses)
- Test with $5.00 cost
- Test with 100% coverage

# Constraints
- Limit: ≤$10.00"""
        loader = PromptLoader("test.md")
        result = loader.parse(content)
        assert len(result.success_criteria) == 4
        assert 'Test with "quotes"' in result.success_criteria
        assert "Test with $5.00 cost" in result.success_criteria

    def test_section_order_independence(self):
        """Test sections can appear in any order."""
        content = """# Constraints
- Budget: $5.00

# Goal
Test goal

# Success Criteria
- Criterion 1"""
        loader = PromptLoader("test.md")
        result = loader.parse(content)
        assert result.goal == "Test goal"
        assert result.success_criteria == ["Criterion 1"]
        assert result.constraints == ["Budget: $5.00"]

    def test_unicode_content(self):
        """Test parsing content with unicode characters."""
        content = """# Goal
Implement feature with émoji 🚀

# Success Criteria
- Test résultat ✓

# Constraints
- Budget: €5.00"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            loader = PromptLoader(temp_path)
            result = loader.load()
            assert "émoji 🚀" in result.goal
            assert "résultat ✓" in result.success_criteria[0]
        finally:
            Path(temp_path).unlink()

    def test_large_prompt_file(self):
        """Test parsing large prompt file with many items."""
        criteria = "\n".join([f"- Criterion {i}" for i in range(100)])
        constraints = "\n".join([f"- Constraint {i}" for i in range(50)])
        content = f"""# Goal
Large test with many criteria and constraints

# Success Criteria
{criteria}

# Constraints
{constraints}

# Context
{'Very long context. ' * 100}"""
        loader = PromptLoader("test.md")
        result = loader.parse(content)
        assert len(result.success_criteria) == 100
        assert len(result.constraints) == 50
        assert len(result.context) > 1000

    def test_header_with_extra_spaces(self):
        """Test parsing handles headers with extra spaces."""
        content = """#  Goal
Test goal

#   Success Criteria
- Test

#  Constraints """
        loader = PromptLoader("test.md")
        result = loader.parse(content)
        assert result.goal == "Test goal"
        assert result.success_criteria == ["Test"]

    def test_list_with_indentation(self):
        """Test list items with various indentation levels."""
        content = """# Goal
Test

# Success Criteria
   - Indented item 1
- Normal item 2
     - Extra indented item 3

# Constraints
- Constraint 1"""
        loader = PromptLoader("test.md")
        result = loader.parse(content)
        assert len(result.success_criteria) == 3
        assert "Indented item 1" in result.success_criteria
