"""Error handling for Aurora Planning System.

This module defines the VALIDATION_MESSAGES dictionary and custom exceptions
for the planning system, providing actionable error messages to users.

VALIDATION_MESSAGES contains all error codes with {placeholder} syntax
for dynamic value substitution.

Exceptions:
    - PlanningError: Base exception with error code and message formatting
    - PlanNotFoundError: Plan not found in active or archive
    - PlanValidationError: Plan data fails validation
    - PlanDirectoryError: Planning directory issues (init, permissions)
    - PlanArchiveError: Archive operation failures
"""

from __future__ import annotations


# All error codes with actionable message templates
VALIDATION_MESSAGES: dict[str, str] = {
    # Plan ID errors
    "PLAN_ID_INVALID_FORMAT": (
        "Plan ID must be 'NNNN-slug' format (e.g., '0001-oauth-auth'). Got: {value}"
    ),
    "PLAN_ID_ALREADY_EXISTS": (
        "Plan ID '{plan_id}' already exists. Use 'aur plan show {plan_id}' to view it."
    ),
    # Plan lifecycle errors
    "PLAN_NOT_FOUND": ("Plan '{plan_id}' not found. Use 'aur plan list' to see available plans."),
    "PLAN_ALREADY_ARCHIVED": (
        "Plan '{plan_id}' is already archived. Use 'aur plan list --archived' to view."
    ),
    # Goal validation errors
    "GOAL_TOO_SHORT": ("Goal must be at least 10 characters. Provide a clear description."),
    "GOAL_TOO_LONG": ("Goal exceeds 500 characters. Consider breaking into multiple plans."),
    # Subgoal errors
    "SUBGOAL_ID_INVALID": ("Subgoal ID must be 'sg-N' format (e.g., 'sg-1'). Got: {value}"),
    "SUBGOAL_DEPENDENCY_INVALID": (
        "Subgoal '{subgoal_id}' references unknown dependency: {dependency}"
    ),
    "SUBGOAL_CIRCULAR_DEPENDENCY": ("Circular dependency detected: {cycle}"),
    "TOO_MANY_SUBGOALS": ("Plan has {count} subgoals (max 10). Consider splitting."),
    # Agent errors
    "AGENT_FORMAT_INVALID": ("Agent must start with '@' (e.g., '@code-developer'). Got: {value}"),
    "AGENT_NOT_FOUND": (
        "Agent '{agent}' not found. Use 'aur agents list' to see available agents."
    ),
    # Directory errors
    "PLANS_DIR_NOT_INITIALIZED": ("Planning directory not initialized. Run 'aur plan init' first."),
    "PLANS_DIR_NO_WRITE_PERMISSION": ("Cannot write to {path}. Check directory permissions."),
    "PLANS_DIR_ALREADY_EXISTS": (
        "Planning directory already exists at {path}. Use --force to reinitialize."
    ),
    # File errors
    "PLAN_FILE_CORRUPT": ("Plan file '{file}' is corrupt or invalid JSON. Try regenerating."),
    "PLAN_FILE_MISSING": ("Expected file '{file}' not found in plan directory."),
    # Context errors
    "CONTEXT_FILE_NOT_FOUND": ("Context file '{file}' not found. Check the path."),
    "NO_INDEXED_MEMORY": (
        "No indexed memory available. Run 'aur mem index .' or use '--context <file>'."
    ),
    # Archive errors
    "ARCHIVE_FAILED": ("Failed to archive plan: {error}. Plan remains in active state."),
    "ARCHIVE_ROLLBACK": ("Archive failed, rolled back to original state. Error: {error}"),
}


class PlanningError(Exception):
    """Base exception for all planning system errors.

    Formats error messages using VALIDATION_MESSAGES dictionary with
    placeholder substitution for dynamic values.

    Attributes:
        code: Error code from VALIDATION_MESSAGES
        message: Formatted error message with substituted values

    Example:
        >>> raise PlanningError("PLAN_NOT_FOUND", plan_id="0001-oauth")
        PlanningError: Plan '0001-oauth' not found. Use 'aur plan list' to see available plans.

    """

    def __init__(self, code: str, **kwargs: str | int) -> None:
        """Initialize PlanningError with error code and format arguments.

        Args:
            code: Error code from VALIDATION_MESSAGES
            **kwargs: Format arguments for message placeholders

        """
        self.code = code
        template = VALIDATION_MESSAGES.get(code, code)
        try:
            self.message = template.format(**kwargs)
        except KeyError:
            # If format fails, use template as-is with note
            self.message = f"{template} (format args: {kwargs})"
        super().__init__(self.message)


class PlanNotFoundError(PlanningError):
    """Raised when a plan cannot be found.

    Used when searching for a plan by ID in either active or archive
    directories fails.

    Example:
        >>> raise PlanNotFoundError("0001-oauth-auth")
        PlanNotFoundError: Plan '0001-oauth-auth' not found. Use 'aur plan list'...

    """

    def __init__(self, plan_id: str) -> None:
        """Initialize with the missing plan ID.

        Args:
            plan_id: ID of the plan that was not found

        """
        super().__init__("PLAN_NOT_FOUND", plan_id=plan_id)


class PlanValidationError(PlanningError):
    """Raised when plan data fails validation.

    Used for various validation failures including:
    - Invalid plan_id format
    - Goal length constraints
    - Subgoal count limits
    - Invalid dependency references

    Example:
        >>> raise PlanValidationError("GOAL_TOO_SHORT")
        PlanValidationError: Goal must be at least 10 characters...

    """

    # Uses any validation error code from VALIDATION_MESSAGES


class PlanDirectoryError(PlanningError):
    """Raised for planning directory issues.

    Used for:
    - Directory not initialized
    - Permission denied
    - Directory already exists (without --force)

    Example:
        >>> raise PlanDirectoryError("PLANS_DIR_NOT_INITIALIZED")
        PlanDirectoryError: Planning directory not initialized...

    """

    # Uses directory-related error codes


class PlanArchiveError(PlanningError):
    """Raised when archive operations fail.

    Used for:
    - Plan already archived
    - Archive move failure
    - Rollback scenarios

    Example:
        >>> raise PlanArchiveError("ARCHIVE_FAILED", error="disk full")
        PlanArchiveError: Failed to archive plan: disk full...

    """

    # Uses archive-related error codes


class PlanFileError(PlanningError):
    """Raised when plan file operations fail.

    Used for:
    - Corrupt or invalid JSON files
    - Missing expected files

    Example:
        >>> raise PlanFileError("PLAN_FILE_CORRUPT", file="agents.json")
        PlanFileError: Plan file 'agents.json' is corrupt or invalid JSON...

    """

    # Uses file-related error codes


class ContextError(PlanningError):
    """Raised when context retrieval fails.

    Used for:
    - Context files not found
    - No indexed memory available

    Example:
        >>> raise ContextError("CONTEXT_FILE_NOT_FOUND", file="auth.py")
        ContextError: Context file 'auth.py' not found...

    """

    # Uses context-related error codes
