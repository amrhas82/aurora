"""
Unit tests for simplified PromptLoader.

Following TDD RED-GREEN-REFACTOR cycle:
- Task 2.1-2.5: RED phase - write failing tests
- Task 2.6-2.9: GREEN phase - implement to pass tests
- Task 2.10-2.11: REFACTOR phase - improve code quality
"""

import pytest
from pathlib import Path
from aurora_soar.headless.prompt_loader_simplified import PromptLoader, PromptData, PromptValidationError


class TestPromptLoaderValidPrompt:
    """Test PromptLoader with valid prompt files - Task 2.1."""

    def test_load_prompt_with_all_sections(self, tmp_path):
        """Test loading a valid prompt file with all required sections."""
        prompt_file = tmp_path / "valid_prompt.md"
        prompt_file.write_text("""# Goal
Build a simple calculator

# Success Criteria
- Calculator can add two numbers
- Calculator can subtract two numbers
- All tests pass

# Constraints
- Use Python standard library only
- No external dependencies

# Context
This is for a tutorial project demonstrating basic Python.
""")

        loader = PromptLoader(str(prompt_file))
        data = loader.load()

        assert isinstance(data, PromptData)
        assert data.goal == "Build a simple calculator"
        assert "Calculator can add two numbers" in data.success_criteria
        assert "Calculator can subtract two numbers" in data.success_criteria
        assert "All tests pass" in data.success_criteria
        assert "Use Python standard library only" in data.constraints
        assert "No external dependencies" in data.constraints
        assert "This is for a tutorial project" in data.context

    def test_load_prompt_without_optional_sections(self, tmp_path):
        """Test loading prompt with only required sections (no Context/Constraints)."""
        prompt_file = tmp_path / "minimal_prompt.md"
        prompt_file.write_text("""# Goal
Create a README file

# Success Criteria
- README contains project title
- README contains installation instructions
""")

        loader = PromptLoader(str(prompt_file))
        data = loader.load()

        assert data.goal == "Create a README file"
        assert len(data.success_criteria) == 2
        assert data.constraints == []  # Optional, should be empty list
        assert data.context == ""  # Optional, should be empty string


class TestPromptLoaderMissingSections:
    """Test PromptLoader rejects prompts with missing required sections - Task 2.2-2.3."""

    def test_missing_goal_section_raises_error(self, tmp_path):
        """Test that prompt missing Goal section raises PromptValidationError."""
        prompt_file = tmp_path / "no_goal.md"
        prompt_file.write_text("""# Success Criteria
- Criterion 1
- Criterion 2
""")

        loader = PromptLoader(str(prompt_file))

        with pytest.raises(PromptValidationError, match="Goal section is required"):
            loader.load()

    def test_missing_success_criteria_raises_error(self, tmp_path):
        """Test that prompt missing Success Criteria section raises PromptValidationError."""
        prompt_file = tmp_path / "no_criteria.md"
        prompt_file.write_text("""# Goal
Do something important
""")

        loader = PromptLoader(str(prompt_file))

        with pytest.raises(PromptValidationError, match="Success Criteria section is required"):
            loader.load()

    def test_empty_goal_section_raises_error(self, tmp_path):
        """Test that empty Goal section raises PromptValidationError."""
        prompt_file = tmp_path / "empty_goal.md"
        prompt_file.write_text("""# Goal

# Success Criteria
- Criterion 1
""")

        loader = PromptLoader(str(prompt_file))

        with pytest.raises(PromptValidationError, match="Goal cannot be empty"):
            loader.load()

    def test_empty_success_criteria_raises_error(self, tmp_path):
        """Test that empty Success Criteria section raises PromptValidationError."""
        prompt_file = tmp_path / "empty_criteria.md"
        prompt_file.write_text("""# Goal
Do something

# Success Criteria
""")

        loader = PromptLoader(str(prompt_file))

        with pytest.raises(PromptValidationError, match="Success Criteria cannot be empty"):
            loader.load()


class TestPromptLoaderOptionalSections:
    """Test PromptLoader handles optional Context section - Task 2.4."""

    def test_context_section_is_optional(self, tmp_path):
        """Test that Context section is optional and defaults to empty string."""
        prompt_file = tmp_path / "no_context.md"
        prompt_file.write_text("""# Goal
Test goal

# Success Criteria
- Test criterion
""")

        loader = PromptLoader(str(prompt_file))
        data = loader.load()

        assert data.context == ""

    def test_constraints_section_is_optional(self, tmp_path):
        """Test that Constraints section is optional and defaults to empty list."""
        prompt_file = tmp_path / "no_constraints.md"
        prompt_file.write_text("""# Goal
Test goal

# Success Criteria
- Test criterion
""")

        loader = PromptLoader(str(prompt_file))
        data = loader.load()

        assert data.constraints == []


class TestPromptLoaderFileHandling:
    """Test PromptLoader file existence and error handling - Task 2.5."""

    def test_non_existent_file_raises_error(self):
        """Test that loading non-existent file raises PromptValidationError."""
        loader = PromptLoader("/path/to/nonexistent/prompt.md")

        with pytest.raises(PromptValidationError, match="Prompt file not found"):
            loader.load()

    def test_directory_instead_of_file_raises_error(self, tmp_path):
        """Test that providing a directory instead of file raises PromptValidationError."""
        loader = PromptLoader(str(tmp_path))

        with pytest.raises(PromptValidationError, match="Prompt file not found|is a directory"):
            loader.load()


class TestPromptDataStructure:
    """Test PromptData dataclass structure."""

    def test_prompt_data_has_required_fields(self):
        """Test that PromptData has all required fields."""
        data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1", "Criterion 2"],
            constraints=["Constraint 1"],
            context="Test context"
        )

        assert data.goal == "Test goal"
        assert len(data.success_criteria) == 2
        assert len(data.constraints) == 1
        assert data.context == "Test context"

    def test_prompt_data_with_defaults(self):
        """Test that PromptData works with optional fields as defaults."""
        data = PromptData(
            goal="Test goal",
            success_criteria=["Criterion 1"]
        )

        # Should have defaults for optional fields
        assert data.goal == "Test goal"
        assert data.success_criteria == ["Criterion 1"]
