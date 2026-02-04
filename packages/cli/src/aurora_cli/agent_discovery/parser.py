"""Agent frontmatter parsing with Pydantic validation for AURORA CLI.

This module provides the AgentParser class for extracting and validating
agent metadata from markdown frontmatter. Uses python-frontmatter for
YAML extraction and Pydantic for validation.

The parser follows a graceful degradation pattern - malformed files return
None with detailed warning logs rather than raising exceptions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import frontmatter
from pydantic import ValidationError

from aurora_cli.agent_discovery.models import AgentInfo

logger = logging.getLogger(__name__)


# Field aliases for backward compatibility
_FIELD_ALIASES = {
    "name": "id",  # name -> id
    "description": "goal",  # description -> goal
    "title": "role",  # title -> role (alternative)
}


def _validate_path(path: Path) -> Path | None:
    """Validate and resolve a file path.

    Args:
        path: Path to validate

    Returns:
        Resolved Path if valid, None otherwise

    """
    resolved = Path(path).expanduser().resolve()

    if not resolved.exists():
        logger.warning("Agent file not found: %s", path)
        return None

    if not resolved.is_file():
        logger.warning("Path is not a file: %s", path)
        return None

    return resolved


def _apply_field_aliases(metadata: dict[str, Any]) -> None:
    """Apply field aliases to metadata for backward compatibility.

    Modifies metadata in place to map alternative field names to canonical names.
    Also derives role from id if role is missing.

    Args:
        metadata: Metadata dictionary to modify

    """
    # Map alternative field names to canonical names
    for old_name, new_name in _FIELD_ALIASES.items():
        if old_name in metadata and new_name not in metadata:
            metadata[new_name] = metadata[old_name]

    # Derive role from id if missing
    if "role" not in metadata and "id" in metadata:
        metadata["role"] = metadata["id"].replace("-", " ").title()


def _format_validation_errors(errors: list[dict[str, Any]]) -> str:
    """Format Pydantic validation errors into a readable string.

    Args:
        errors: List of error dictionaries from ValidationError.errors()

    Returns:
        Formatted error string

    """
    missing_fields = [err["loc"][0] for err in errors if err["type"] == "missing"]
    invalid_fields = [(err["loc"][0], err["msg"]) for err in errors if err["type"] != "missing"]

    error_details = []
    if missing_fields:
        error_details.append(
            f"missing required fields: {', '.join(str(f) for f in missing_fields)}",
        )
    for field, msg in invalid_fields:
        error_details.append(f"invalid '{field}': {msg}")

    return "; ".join(error_details) if error_details else "validation failed"


class AgentParser:
    """Parser for agent markdown files with frontmatter.

    Extracts YAML frontmatter from markdown files and validates against
    the AgentInfo Pydantic model. Returns None for malformed files with
    detailed warning logs.

    Example:
        >>> parser = AgentParser()
        >>> agent = parser.parse_file(Path("~/.claude/agents/quality-assurance.md"))
        >>> if agent:
        ...     print(f"Agent: {agent.id} - {agent.role}")
        Agent: quality-assurance - Test Architect & Quality Advisor

        >>> # Malformed file returns None
        >>> bad_agent = parser.parse_file(Path("malformed.md"))
        >>> print(bad_agent)
        None

    """

    def __init__(self) -> None:
        """Initialize the AgentParser."""
        # No initialization needed currently

    def parse_file(self, path: Path) -> AgentInfo | None:
        """Parse an agent markdown file and extract validated metadata.

        Extracts YAML frontmatter from the markdown file, validates against
        AgentInfo schema, and returns the validated model. On any error,
        logs a detailed warning and returns None. Uses extracted helper
        functions for reduced complexity.

        Args:
            path: Path to the agent markdown file

        Returns:
            AgentInfo if successfully parsed and validated, None otherwise

        Example:
            >>> parser = AgentParser()
            >>> agent = parser.parse_file(Path("agent.md"))
            >>> if agent:
            ...     print(agent.role)

        """
        # Validate path
        resolved_path = _validate_path(path)
        if resolved_path is None:
            return None

        # Read and parse frontmatter
        try:
            post = frontmatter.load(resolved_path)
        except Exception as e:
            logger.warning(
                "Failed to parse frontmatter in %s: %s (%s)",
                path,
                type(e).__name__,
                str(e),
            )
            return None

        # Check if frontmatter exists
        if not post.metadata:
            logger.warning(
                "No frontmatter found in %s - expected YAML between --- delimiters",
                path,
            )
            return None

        # Prepare metadata
        metadata = dict(post.metadata)
        metadata["source_file"] = str(resolved_path)
        _apply_field_aliases(metadata)

        # Validate with Pydantic
        try:
            agent = AgentInfo.model_validate(metadata)
            logger.debug("Successfully parsed agent %s from %s", agent.id, path)
            return agent

        except ValidationError as e:
            error_msg = _format_validation_errors(e.errors())
            logger.warning("Validation failed for %s - %s", path, error_msg)
            return None

    def parse_content(self, content: str, source_file: str | None = None) -> AgentInfo | None:
        """Parse agent metadata from a string containing frontmatter.

        Useful for testing or when agent content is provided directly
        rather than from a file.

        Args:
            content: String containing markdown with YAML frontmatter
            source_file: Optional source file path to include in metadata

        Returns:
            AgentInfo if successfully parsed and validated, None otherwise

        Example:
            >>> parser = AgentParser()
            >>> content = '''---
            ... id: test-agent
            ... role: Test Agent
            ... goal: Testing purposes
            ... ---
            ... # Test Agent
            ... '''
            >>> agent = parser.parse_content(content)
            >>> print(agent.id)
            test-agent

        """
        try:
            post = frontmatter.loads(content)
        except Exception as e:
            logger.warning(
                "Failed to parse frontmatter from content: %s (%s)",
                type(e).__name__,
                str(e),
            )
            return None

        if not post.metadata:
            logger.warning("No frontmatter found in content - expected YAML between --- delimiters")
            return None

        # Add source_file if provided
        metadata = dict(post.metadata)
        if source_file:
            metadata["source_file"] = source_file

        try:
            agent = AgentInfo.model_validate(metadata)
            logger.debug("Successfully parsed agent %s from content", agent.id)
            return agent

        except ValidationError as e:
            errors = e.errors()
            missing_fields = [err["loc"][0] for err in errors if err["type"] == "missing"]

            if missing_fields:
                logger.warning(
                    "Validation failed for content - missing required fields: %s",
                    ", ".join(str(f) for f in missing_fields),
                )
            else:
                logger.warning(
                    "Validation failed for content: %s",
                    str(e),
                )
            return None

    def extract_frontmatter(self, path: Path) -> dict[str, Any] | None:
        """Extract raw frontmatter without validation.

        Useful for debugging or when you need the raw metadata without
        Pydantic validation.

        Args:
            path: Path to the agent markdown file

        Returns:
            Dictionary of frontmatter metadata, or None if extraction fails

        Example:
            >>> parser = AgentParser()
            >>> raw = parser.extract_frontmatter(Path("agent.md"))
            >>> print(raw)
            {'id': 'my-agent', 'role': 'My Role', ...}

        """
        resolved_path = Path(path).expanduser().resolve()

        if not resolved_path.exists() or not resolved_path.is_file():
            return None

        try:
            post = frontmatter.load(resolved_path)
            return dict(post.metadata) if post.metadata else None
        except Exception:
            return None
