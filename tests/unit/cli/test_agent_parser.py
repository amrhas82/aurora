"""Unit tests for AgentParser module.

Tests frontmatter extraction, Pydantic validation, and graceful
degradation for malformed agent files.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from aurora_cli.agent_discovery.models import AgentCategory
from aurora_cli.agent_discovery.parser import AgentParser


class TestAgentParserParseFile:
    """Tests for parse_file method."""

    def test_parse_valid_agent(self, tmp_path: Path) -> None:
        """Parses valid agent file with all fields."""
        agent_file = tmp_path / "agent.md"
        agent_file.write_text(
            """---
id: test-agent
role: Test Agent Role
goal: Test the parser functionality
category: eng
skills:
  - testing
  - parsing
examples:
  - "Test example"
when_to_use: Use for testing
dependencies:
  - other-agent
---

# Test Agent

This is the agent content.
""",
        )

        parser = AgentParser()
        agent = parser.parse_file(agent_file)

        assert agent is not None
        assert agent.id == "test-agent"
        assert agent.role == "Test Agent Role"
        assert agent.goal == "Test the parser functionality"
        assert agent.category == AgentCategory.ENG
        assert agent.skills == ["testing", "parsing"]
        assert agent.examples == ["Test example"]
        assert agent.when_to_use == "Use for testing"
        assert agent.dependencies == ["other-agent"]
        assert agent.source_file == str(agent_file)

    def test_parse_minimal_agent(self, tmp_path: Path) -> None:
        """Parses agent with only required fields."""
        agent_file = tmp_path / "minimal.md"
        agent_file.write_text(
            """---
id: minimal-agent
role: Minimal Role
goal: Minimal goal
---

# Minimal Agent
""",
        )

        parser = AgentParser()
        agent = parser.parse_file(agent_file)

        assert agent is not None
        assert agent.id == "minimal-agent"
        assert agent.category == AgentCategory.GENERAL  # Default
        assert agent.skills == []  # Default
        assert agent.when_to_use is None  # Default

    def test_returns_none_for_missing_file(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Returns None and warns for missing file."""
        missing_file = tmp_path / "nonexistent.md"

        parser = AgentParser()

        with caplog.at_level(logging.WARNING):
            result = parser.parse_file(missing_file)

        assert result is None
        assert "not found" in caplog.text

    def test_returns_none_for_directory(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Returns None and warns when path is directory."""
        parser = AgentParser()

        with caplog.at_level(logging.WARNING):
            result = parser.parse_file(tmp_path)

        assert result is None
        assert "not a file" in caplog.text

    def test_returns_none_for_no_frontmatter(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Returns None and warns when no frontmatter present."""
        agent_file = tmp_path / "no_frontmatter.md"
        agent_file.write_text("# Just a regular markdown file")

        parser = AgentParser()

        with caplog.at_level(logging.WARNING):
            result = parser.parse_file(agent_file)

        assert result is None
        assert "No frontmatter found" in caplog.text

    def test_returns_none_for_missing_required_fields(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Returns None and warns when required fields missing.

        Note: 'role' is auto-derived from 'id' if missing, so only 'goal'
        will be reported as missing when id is provided.
        """
        agent_file = tmp_path / "incomplete.md"
        agent_file.write_text(
            """---
id: incomplete-agent
# Missing goal (role auto-derived from id)
---

# Incomplete
""",
        )

        parser = AgentParser()

        with caplog.at_level(logging.WARNING):
            result = parser.parse_file(agent_file)

        assert result is None
        assert "missing required fields" in caplog.text
        assert "goal" in caplog.text

    def test_returns_none_for_invalid_id(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Returns None and warns for invalid kebab-case ID."""
        agent_file = tmp_path / "bad_id.md"
        agent_file.write_text(
            """---
id: Invalid_ID_With_Underscores
role: Bad Agent
goal: Test invalid ID
---
""",
        )

        parser = AgentParser()

        with caplog.at_level(logging.WARNING):
            result = parser.parse_file(agent_file)

        assert result is None
        assert "Validation failed" in caplog.text

    def test_returns_none_for_invalid_yaml(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Returns None and warns for invalid YAML syntax."""
        agent_file = tmp_path / "bad_yaml.md"
        agent_file.write_text(
            """---
id: test
role: : : invalid yaml syntax
---
""",
        )

        parser = AgentParser()

        with caplog.at_level(logging.WARNING):
            result = parser.parse_file(agent_file)

        assert result is None
        assert "Failed to parse frontmatter" in caplog.text

    def test_handles_extra_fields(self, tmp_path: Path) -> None:
        """Ignores extra fields not in schema."""
        agent_file = tmp_path / "extra_fields.md"
        agent_file.write_text(
            """---
id: extra-agent
role: Extra Role
goal: Test extra fields
custom_field: should be ignored
another_unknown: also ignored
---
""",
        )

        parser = AgentParser()
        agent = parser.parse_file(agent_file)

        assert agent is not None
        assert agent.id == "extra-agent"
        # Extra fields should be ignored, not cause errors

    def test_normalizes_category(self, tmp_path: Path) -> None:
        """Normalizes various category values."""
        agent_file = tmp_path / "category.md"

        # Test various category variations
        for category_input, expected in [
            ("engineering", AgentCategory.ENG),
            ("dev", AgentCategory.ENG),
            ("quality", AgentCategory.QA),
            ("testing", AgentCategory.QA),
            ("pm", AgentCategory.PRODUCT),
            ("other", AgentCategory.GENERAL),
        ]:
            agent_file.write_text(
                f"""---
id: category-test
role: Category Test
goal: Test category normalization
category: {category_input}
---
""",
            )

            parser = AgentParser()
            agent = parser.parse_file(agent_file)

            assert agent is not None, f"Failed for category: {category_input}"
            assert agent.category == expected, (
                f"Expected {expected} for {category_input}, got {agent.category}"
            )


class TestAgentParserParseContent:
    """Tests for parse_content method."""

    def test_parse_valid_content(self) -> None:
        """Parses valid content string."""
        content = """---
id: content-agent
role: Content Role
goal: Parse from string
---

# Content Agent
"""

        parser = AgentParser()
        agent = parser.parse_content(content)

        assert agent is not None
        assert agent.id == "content-agent"
        assert agent.source_file is None

    def test_parse_content_with_source_file(self) -> None:
        """Includes source_file when provided."""
        content = """---
id: sourced-agent
role: Sourced Role
goal: Has source file
---
"""

        parser = AgentParser()
        agent = parser.parse_content(content, source_file="/path/to/agent.md")

        assert agent is not None
        assert agent.source_file == "/path/to/agent.md"

    def test_returns_none_for_missing_frontmatter(self, caplog: pytest.LogCaptureFixture) -> None:
        """Returns None for content without frontmatter."""
        content = "# Just markdown\n\nNo frontmatter here."

        parser = AgentParser()

        with caplog.at_level(logging.WARNING):
            result = parser.parse_content(content)

        assert result is None
        assert "No frontmatter found" in caplog.text


class TestAgentParserExtractFrontmatter:
    """Tests for extract_frontmatter method."""

    def test_extract_raw_frontmatter(self, tmp_path: Path) -> None:
        """Extracts raw frontmatter dict without validation."""
        agent_file = tmp_path / "raw.md"
        agent_file.write_text(
            """---
id: raw-agent
role: Raw Role
custom_field: custom value
---
""",
        )

        parser = AgentParser()
        raw = parser.extract_frontmatter(agent_file)

        assert raw is not None
        assert raw["id"] == "raw-agent"
        assert raw["role"] == "Raw Role"
        assert raw["custom_field"] == "custom value"

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        """Returns None for missing file."""
        parser = AgentParser()
        result = parser.extract_frontmatter(tmp_path / "nonexistent.md")

        assert result is None

    def test_returns_none_for_no_frontmatter(self, tmp_path: Path) -> None:
        """Returns None when no frontmatter present."""
        agent_file = tmp_path / "plain.md"
        agent_file.write_text("# Plain markdown")

        parser = AgentParser()
        result = parser.extract_frontmatter(agent_file)

        assert result is None


class TestAgentParserEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_handles_unicode_content(self, tmp_path: Path) -> None:
        """Handles Unicode characters in agent content."""
        agent_file = tmp_path / "unicode.md"
        agent_file.write_text(
            """---
id: unicode-agent
role: Unic\u00f6de R\u00f4le
goal: Test \u4e2d\u6587 content
skills:
  - \u65e5\u672c\u8a9e skill
---
""",
        )

        parser = AgentParser()
        agent = parser.parse_file(agent_file)

        assert agent is not None
        assert "Unicode" in agent.role or "\u00f6" in agent.role

    def test_handles_multiline_goal(self, tmp_path: Path) -> None:
        """Handles multiline goal field."""
        agent_file = tmp_path / "multiline.md"
        agent_file.write_text(
            """---
id: multiline-agent
role: Multiline Role
goal: |
  This is a multiline
  goal that spans
  multiple lines
---
""",
        )

        parser = AgentParser()
        agent = parser.parse_file(agent_file)

        assert agent is not None
        assert "multiline" in agent.goal.lower()

    def test_handles_empty_skills_list(self, tmp_path: Path) -> None:
        """Handles explicitly empty skills list."""
        agent_file = tmp_path / "empty_skills.md"
        agent_file.write_text(
            """---
id: empty-skills
role: Empty Skills Role
goal: Test empty skills
skills: []
---
""",
        )

        parser = AgentParser()
        agent = parser.parse_file(agent_file)

        assert agent is not None
        assert agent.skills == []

    def test_normalizes_single_skill_string(self, tmp_path: Path) -> None:
        """Converts single skill string to list."""
        agent_file = tmp_path / "single_skill.md"
        agent_file.write_text(
            """---
id: single-skill
role: Single Skill Role
goal: Test single skill
skills: just-one-skill
---
""",
        )

        parser = AgentParser()
        agent = parser.parse_file(agent_file)

        assert agent is not None
        assert agent.skills == ["just-one-skill"]

    def test_normalizes_id_to_lowercase(self, tmp_path: Path) -> None:
        """Normalizes ID to lowercase."""
        agent_file = tmp_path / "uppercase.md"
        agent_file.write_text(
            """---
id: MY-UPPERCASE-ID
role: Uppercase ID Role
goal: Test ID normalization
---
""",
        )

        parser = AgentParser()
        agent = parser.parse_file(agent_file)

        assert agent is not None
        assert agent.id == "my-uppercase-id"
