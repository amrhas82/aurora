"""Unit tests for planning error handling.

Tests VALIDATION_MESSAGES dictionary and exception classes
to ensure all error codes produce valid messages.
"""

from __future__ import annotations

import pytest

from aurora_cli.planning.errors import (
    VALIDATION_MESSAGES,
    ContextError,
    PlanArchiveError,
    PlanDirectoryError,
    PlanFileError,
    PlanningError,
    PlanNotFoundError,
    PlanValidationError,
)


class TestValidationMessages:
    """Tests for VALIDATION_MESSAGES dictionary."""

    def test_all_expected_codes_exist(self) -> None:
        """All expected error codes are defined."""
        expected_codes = [
            "PLAN_ID_INVALID_FORMAT",
            "PLAN_ID_ALREADY_EXISTS",
            "PLAN_NOT_FOUND",
            "PLAN_ALREADY_ARCHIVED",
            "GOAL_TOO_SHORT",
            "GOAL_TOO_LONG",
            "SUBGOAL_ID_INVALID",
            "SUBGOAL_DEPENDENCY_INVALID",
            "SUBGOAL_CIRCULAR_DEPENDENCY",
            "TOO_MANY_SUBGOALS",
            "AGENT_FORMAT_INVALID",
            "AGENT_NOT_FOUND",
            "PLANS_DIR_NOT_INITIALIZED",
            "PLANS_DIR_NO_WRITE_PERMISSION",
            "PLANS_DIR_ALREADY_EXISTS",
            "PLAN_FILE_CORRUPT",
            "PLAN_FILE_MISSING",
            "CONTEXT_FILE_NOT_FOUND",
            "NO_INDEXED_MEMORY",
            "ARCHIVE_FAILED",
            "ARCHIVE_ROLLBACK",
        ]

        for code in expected_codes:
            assert code in VALIDATION_MESSAGES, f"Missing error code: {code}"

    def test_all_messages_are_non_empty_strings(self) -> None:
        """All messages are non-empty strings."""
        for code, message in VALIDATION_MESSAGES.items():
            assert isinstance(message, str), f"{code} message is not a string"
            assert len(message) > 0, f"{code} message is empty"

    def test_messages_with_placeholders_format_correctly(self) -> None:
        """Messages with placeholders can be formatted."""
        test_cases = [
            ("PLAN_ID_INVALID_FORMAT", {"value": "bad-id"}),
            ("PLAN_ID_ALREADY_EXISTS", {"plan_id": "0001-test"}),
            ("PLAN_NOT_FOUND", {"plan_id": "0001-test"}),
            ("PLAN_ALREADY_ARCHIVED", {"plan_id": "0001-test"}),
            ("SUBGOAL_ID_INVALID", {"value": "bad-id"}),
            ("SUBGOAL_DEPENDENCY_INVALID", {"subgoal_id": "sg-1", "dependency": "sg-99"}),
            ("SUBGOAL_CIRCULAR_DEPENDENCY", {"cycle": "sg-1 -> sg-2 -> sg-1"}),
            ("TOO_MANY_SUBGOALS", {"count": 15}),
            ("AGENT_FORMAT_INVALID", {"value": "bad-agent"}),
            ("AGENT_NOT_FOUND", {"agent": "@missing-agent"}),
            ("PLANS_DIR_NO_WRITE_PERMISSION", {"path": "/some/path"}),
            ("PLANS_DIR_ALREADY_EXISTS", {"path": "/some/path"}),
            ("PLAN_FILE_CORRUPT", {"file": "agents.json"}),
            ("PLAN_FILE_MISSING", {"file": "plan.md"}),
            ("CONTEXT_FILE_NOT_FOUND", {"file": "auth.py"}),
            ("ARCHIVE_FAILED", {"error": "disk full"}),
            ("ARCHIVE_ROLLBACK", {"error": "permission denied"}),
        ]

        for code, kwargs in test_cases:
            message = VALIDATION_MESSAGES[code]
            formatted = message.format(**kwargs)
            assert len(formatted) > 0, f"Formatted message for {code} is empty"
            # Verify placeholder was replaced
            for key, value in kwargs.items():
                assert str(value) in formatted, f"{key} not found in formatted message for {code}"

    def test_messages_without_placeholders_are_valid(self) -> None:
        """Messages without placeholders are valid strings."""
        no_placeholder_codes = [
            "GOAL_TOO_SHORT",
            "GOAL_TOO_LONG",
            "PLANS_DIR_NOT_INITIALIZED",
            "NO_INDEXED_MEMORY",
        ]

        for code in no_placeholder_codes:
            message = VALIDATION_MESSAGES[code]
            # Should not raise when formatting with empty kwargs
            formatted = message.format()
            assert len(formatted) > 0


class TestPlanningError:
    """Tests for PlanningError base exception."""

    def test_basic_initialization(self) -> None:
        """PlanningError initializes with code and message."""
        error = PlanningError("GOAL_TOO_SHORT")

        assert error.code == "GOAL_TOO_SHORT"
        assert "10 characters" in error.message

    def test_message_formatting_with_kwargs(self) -> None:
        """PlanningError formats message with kwargs."""
        error = PlanningError("PLAN_NOT_FOUND", plan_id="0001-oauth")

        assert error.code == "PLAN_NOT_FOUND"
        assert "0001-oauth" in error.message
        assert "aur plan list" in error.message

    def test_str_returns_formatted_message(self) -> None:
        """str(error) returns the formatted message."""
        error = PlanningError("PLAN_NOT_FOUND", plan_id="0001-test")

        assert str(error) == error.message
        assert "0001-test" in str(error)

    def test_unknown_code_uses_code_as_message(self) -> None:
        """Unknown error code uses the code as message."""
        error = PlanningError("UNKNOWN_ERROR_CODE")

        assert error.code == "UNKNOWN_ERROR_CODE"
        assert error.message == "UNKNOWN_ERROR_CODE"

    def test_missing_kwargs_handled_gracefully(self) -> None:
        """Missing format kwargs are handled gracefully."""
        # This should not crash, even though plan_id is not provided
        error = PlanningError("PLAN_NOT_FOUND")

        assert error.code == "PLAN_NOT_FOUND"
        # Message should mention format issue
        assert "format args" in error.message or "{plan_id}" in error.message


class TestPlanNotFoundError:
    """Tests for PlanNotFoundError."""

    def test_initialization_with_plan_id(self) -> None:
        """PlanNotFoundError includes plan_id in message."""
        error = PlanNotFoundError("0001-oauth-auth")

        assert error.code == "PLAN_NOT_FOUND"
        assert "0001-oauth-auth" in error.message
        assert "aur plan list" in error.message

    def test_is_planning_error_subclass(self) -> None:
        """PlanNotFoundError is a PlanningError subclass."""
        error = PlanNotFoundError("test-plan")

        assert isinstance(error, PlanningError)
        assert isinstance(error, Exception)


class TestPlanValidationError:
    """Tests for PlanValidationError."""

    def test_with_goal_too_short(self) -> None:
        """PlanValidationError works with GOAL_TOO_SHORT."""
        error = PlanValidationError("GOAL_TOO_SHORT")

        assert "10 characters" in error.message

    def test_with_too_many_subgoals(self) -> None:
        """PlanValidationError works with TOO_MANY_SUBGOALS."""
        error = PlanValidationError("TOO_MANY_SUBGOALS", count=15)

        assert "15 subgoals" in error.message
        assert "max 10" in error.message

    def test_is_planning_error_subclass(self) -> None:
        """PlanValidationError is a PlanningError subclass."""
        error = PlanValidationError("GOAL_TOO_SHORT")

        assert isinstance(error, PlanningError)


class TestPlanDirectoryError:
    """Tests for PlanDirectoryError."""

    def test_with_not_initialized(self) -> None:
        """PlanDirectoryError works with PLANS_DIR_NOT_INITIALIZED."""
        error = PlanDirectoryError("PLANS_DIR_NOT_INITIALIZED")

        assert "aur plan init" in error.message

    def test_with_no_write_permission(self) -> None:
        """PlanDirectoryError works with PLANS_DIR_NO_WRITE_PERMISSION."""
        error = PlanDirectoryError("PLANS_DIR_NO_WRITE_PERMISSION", path="/test/path")

        assert "/test/path" in error.message
        assert "permissions" in error.message.lower()

    def test_is_planning_error_subclass(self) -> None:
        """PlanDirectoryError is a PlanningError subclass."""
        error = PlanDirectoryError("PLANS_DIR_NOT_INITIALIZED")

        assert isinstance(error, PlanningError)


class TestPlanArchiveError:
    """Tests for PlanArchiveError."""

    def test_with_archive_failed(self) -> None:
        """PlanArchiveError works with ARCHIVE_FAILED."""
        error = PlanArchiveError("ARCHIVE_FAILED", error="disk full")

        assert "disk full" in error.message
        assert "active state" in error.message

    def test_with_archive_rollback(self) -> None:
        """PlanArchiveError works with ARCHIVE_ROLLBACK."""
        error = PlanArchiveError("ARCHIVE_ROLLBACK", error="permission denied")

        assert "permission denied" in error.message
        assert "rolled back" in error.message

    def test_is_planning_error_subclass(self) -> None:
        """PlanArchiveError is a PlanningError subclass."""
        error = PlanArchiveError("ARCHIVE_FAILED", error="test")

        assert isinstance(error, PlanningError)


class TestPlanFileError:
    """Tests for PlanFileError."""

    def test_with_corrupt_file(self) -> None:
        """PlanFileError works with PLAN_FILE_CORRUPT."""
        error = PlanFileError("PLAN_FILE_CORRUPT", file="agents.json")

        assert "agents.json" in error.message
        assert "corrupt" in error.message.lower() or "invalid" in error.message.lower()

    def test_with_missing_file(self) -> None:
        """PlanFileError works with PLAN_FILE_MISSING."""
        error = PlanFileError("PLAN_FILE_MISSING", file="plan.md")

        assert "plan.md" in error.message
        assert "not found" in error.message.lower()

    def test_is_planning_error_subclass(self) -> None:
        """PlanFileError is a PlanningError subclass."""
        error = PlanFileError("PLAN_FILE_CORRUPT", file="test.json")

        assert isinstance(error, PlanningError)


class TestContextError:
    """Tests for ContextError."""

    def test_with_file_not_found(self) -> None:
        """ContextError works with CONTEXT_FILE_NOT_FOUND."""
        error = ContextError("CONTEXT_FILE_NOT_FOUND", file="auth.py")

        assert "auth.py" in error.message
        assert "not found" in error.message.lower()

    def test_with_no_indexed_memory(self) -> None:
        """ContextError works with NO_INDEXED_MEMORY."""
        error = ContextError("NO_INDEXED_MEMORY")

        assert "aur mem index" in error.message

    def test_is_planning_error_subclass(self) -> None:
        """ContextError is a PlanningError subclass."""
        error = ContextError("NO_INDEXED_MEMORY")

        assert isinstance(error, PlanningError)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_all_exceptions_inherit_from_planning_error(self) -> None:
        """All custom exceptions inherit from PlanningError."""
        exception_classes = [
            PlanNotFoundError,
            PlanValidationError,
            PlanDirectoryError,
            PlanArchiveError,
            PlanFileError,
            ContextError,
        ]

        for exc_class in exception_classes:
            assert issubclass(
                exc_class, PlanningError
            ), f"{exc_class.__name__} does not inherit from PlanningError"

    def test_all_exceptions_inherit_from_exception(self) -> None:
        """All custom exceptions inherit from Exception."""
        exception_classes = [
            PlanningError,
            PlanNotFoundError,
            PlanValidationError,
            PlanDirectoryError,
            PlanArchiveError,
            PlanFileError,
            ContextError,
        ]

        for exc_class in exception_classes:
            assert issubclass(
                exc_class, Exception
            ), f"{exc_class.__name__} does not inherit from Exception"

    def test_exceptions_can_be_caught_by_planning_error(self) -> None:
        """All specific exceptions can be caught by PlanningError."""
        test_exceptions = [
            PlanNotFoundError("test"),
            PlanValidationError("GOAL_TOO_SHORT"),
            PlanDirectoryError("PLANS_DIR_NOT_INITIALIZED"),
            PlanArchiveError("ARCHIVE_FAILED", error="test"),
            PlanFileError("PLAN_FILE_CORRUPT", file="test.json"),
            ContextError("NO_INDEXED_MEMORY"),
        ]

        for exc in test_exceptions:
            with pytest.raises(PlanningError):
                raise exc


class TestAllCodesProduceValidMessages:
    """Ensure every code in VALIDATION_MESSAGES produces a valid error."""

    def test_every_code_can_be_used_in_planning_error(self) -> None:
        """Every error code can be used with PlanningError."""
        # Define required kwargs for each code
        required_kwargs: dict[str, dict[str, str | int]] = {
            "PLAN_ID_INVALID_FORMAT": {"value": "test"},
            "PLAN_ID_ALREADY_EXISTS": {"plan_id": "test"},
            "PLAN_NOT_FOUND": {"plan_id": "test"},
            "PLAN_ALREADY_ARCHIVED": {"plan_id": "test"},
            "GOAL_TOO_SHORT": {},
            "GOAL_TOO_LONG": {},
            "SUBGOAL_ID_INVALID": {"value": "test"},
            "SUBGOAL_DEPENDENCY_INVALID": {"subgoal_id": "sg-1", "dependency": "sg-2"},
            "SUBGOAL_CIRCULAR_DEPENDENCY": {"cycle": "sg-1 -> sg-2"},
            "TOO_MANY_SUBGOALS": {"count": 15},
            "AGENT_FORMAT_INVALID": {"value": "test"},
            "AGENT_NOT_FOUND": {"agent": "@test"},
            "PLANS_DIR_NOT_INITIALIZED": {},
            "PLANS_DIR_NO_WRITE_PERMISSION": {"path": "/test"},
            "PLANS_DIR_ALREADY_EXISTS": {"path": "/test"},
            "PLAN_FILE_CORRUPT": {"file": "test.json"},
            "PLAN_FILE_MISSING": {"file": "test.md"},
            "CONTEXT_FILE_NOT_FOUND": {"file": "test.py"},
            "NO_INDEXED_MEMORY": {},
            "ARCHIVE_FAILED": {"error": "test error"},
            "ARCHIVE_ROLLBACK": {"error": "test error"},
        }

        for code in VALIDATION_MESSAGES:
            kwargs = required_kwargs.get(code, {})
            error = PlanningError(code, **kwargs)
            assert len(error.message) > 0, f"Empty message for {code}"
            assert error.code == code
