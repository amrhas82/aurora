"""Unit tests for slash command templates."""

import pytest

from aurora_cli.templates.slash_commands import COMMAND_TEMPLATES, get_command_body


def test_command_templates_count():
    """Verify COMMAND_TEMPLATES has exactly 5 entries."""
    assert (
        len(COMMAND_TEMPLATES) == 5
    ), f"Expected 5 commands, got {len(COMMAND_TEMPLATES)}: {list(COMMAND_TEMPLATES.keys())}"


def test_checkpoint_not_in_templates():
    """Verify checkpoint is not in COMMAND_TEMPLATES."""
    assert "checkpoint" not in COMMAND_TEMPLATES, "checkpoint should not be in COMMAND_TEMPLATES"


def test_get_command_body_checkpoint_raises():
    """Verify get_command_body('checkpoint') raises KeyError."""
    with pytest.raises(KeyError, match="Unknown command: checkpoint"):
        get_command_body("checkpoint")


def test_all_expected_commands_present():
    """Verify all expected commands are present."""
    expected_commands = {"search", "get", "plan", "implement", "archive"}
    actual_commands = set(COMMAND_TEMPLATES.keys())

    assert (
        actual_commands == expected_commands
    ), f"Command mismatch. Expected: {expected_commands}, Got: {actual_commands}"


def test_get_command_body_valid_commands():
    """Verify get_command_body works for all valid commands."""
    for command_id in COMMAND_TEMPLATES.keys():
        body = get_command_body(command_id)
        assert isinstance(body, str), f"{command_id} body should be string"
        assert len(body) > 0, f"{command_id} body should not be empty"
