"""Tests for refactored agent parser helper functions.

This module tests the extracted helper functions from parser.py
to ensure behavior is maintained after refactoring for complexity reduction.
"""

from __future__ import annotations

from pathlib import Path


class TestValidatePath:
    """Tests for _validate_path helper function."""

    def test_returns_none_for_nonexistent_path(self, tmp_path: Path) -> None:
        """Test that None is returned for non-existent paths."""
        from aurora_cli.agent_discovery.parser import _validate_path

        non_existent = tmp_path / "nonexistent.md"
        result = _validate_path(non_existent)
        assert result is None

    def test_returns_none_for_directory(self, tmp_path: Path) -> None:
        """Test that None is returned for directories."""
        from aurora_cli.agent_discovery.parser import _validate_path

        result = _validate_path(tmp_path)
        assert result is None

    def test_returns_resolved_path_for_valid_file(self, tmp_path: Path) -> None:
        """Test that resolved path is returned for valid files."""
        from aurora_cli.agent_discovery.parser import _validate_path

        test_file = tmp_path / "test.md"
        test_file.write_text("test content")

        result = _validate_path(test_file)
        assert result is not None
        assert result.exists()
        assert result.is_file()


class TestApplyFieldAliases:
    """Tests for _apply_field_aliases helper function."""

    def test_maps_name_to_id(self) -> None:
        """Test that 'name' is mapped to 'id'."""
        from aurora_cli.agent_discovery.parser import _apply_field_aliases

        metadata = {"name": "test-agent"}
        _apply_field_aliases(metadata)
        assert metadata.get("id") == "test-agent"

    def test_maps_description_to_goal(self) -> None:
        """Test that 'description' is mapped to 'goal'."""
        from aurora_cli.agent_discovery.parser import _apply_field_aliases

        metadata = {"description": "Test goal"}
        _apply_field_aliases(metadata)
        assert metadata.get("goal") == "Test goal"

    def test_maps_title_to_role(self) -> None:
        """Test that 'title' is mapped to 'role'."""
        from aurora_cli.agent_discovery.parser import _apply_field_aliases

        metadata = {"title": "Test Role"}
        _apply_field_aliases(metadata)
        assert metadata.get("role") == "Test Role"

    def test_does_not_override_existing_fields(self) -> None:
        """Test that existing canonical fields are not overridden."""
        from aurora_cli.agent_discovery.parser import _apply_field_aliases

        metadata = {"name": "old-name", "id": "new-id"}
        _apply_field_aliases(metadata)
        assert metadata.get("id") == "new-id"

    def test_derives_role_from_id(self) -> None:
        """Test that role is derived from id when missing."""
        from aurora_cli.agent_discovery.parser import _apply_field_aliases

        metadata = {"id": "test-agent-name"}
        _apply_field_aliases(metadata)
        assert metadata.get("role") == "Test Agent Name"


class TestFormatValidationErrors:
    """Tests for _format_validation_errors helper function."""

    def test_formats_missing_fields(self) -> None:
        """Test formatting of missing field errors."""
        from aurora_cli.agent_discovery.parser import _format_validation_errors

        errors = [
            {"loc": ("id",), "type": "missing", "msg": "Field required"},
            {"loc": ("role",), "type": "missing", "msg": "Field required"},
        ]

        result = _format_validation_errors(errors)
        assert "missing required fields" in result
        assert "id" in result
        assert "role" in result

    def test_formats_invalid_fields(self) -> None:
        """Test formatting of invalid field errors."""
        from aurora_cli.agent_discovery.parser import _format_validation_errors

        errors = [
            {"loc": ("category",), "type": "invalid_type", "msg": "Invalid value"},
        ]

        result = _format_validation_errors(errors)
        assert "invalid" in result.lower()
        assert "category" in result

    def test_handles_mixed_errors(self) -> None:
        """Test formatting of mixed missing and invalid errors."""
        from aurora_cli.agent_discovery.parser import _format_validation_errors

        errors = [
            {"loc": ("id",), "type": "missing", "msg": "Field required"},
            {"loc": ("category",), "type": "invalid_type", "msg": "Bad value"},
        ]

        result = _format_validation_errors(errors)
        assert "missing" in result.lower()
        assert "invalid" in result.lower()
