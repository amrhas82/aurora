"""Plan ID generation with auto-increment.

Generates unique plan IDs in the format NNNN-slug (e.g., 0001-oauth-auth).
Scans existing plans in active and archive directories to find the next available number.
"""

import re
from pathlib import Path

from slugify import slugify

from aurora_planning.planning_config import get_plans_dir

# Pattern for matching plan IDs: NNNN-slug or YYYY-MM-DD-NNNN-slug
PLAN_ID_PATTERN = re.compile(r"(?:\d{4}-\d{2}-\d{2}-)?(\d{4})-(.+)")
PLAN_ID_FORMAT = "{:04d}-{}"


def extract_plan_number(directory_name: str) -> int | None:
    """Extract the plan number from a directory name.

    Handles both active format (NNNN-slug) and archived format (YYYY-MM-DD-NNNN-slug).

    Args:
        directory_name: Name of the plan directory

    Returns:
        Plan number as integer, or None if not a valid plan directory

    Examples:
        >>> extract_plan_number("0001-oauth-auth")
        1
        >>> extract_plan_number("2026-01-03-0042-user-registration")
        42
        >>> extract_plan_number("not-a-plan")
        None

    """
    match = PLAN_ID_PATTERN.match(directory_name)
    if match:
        return int(match.group(1))
    return None


def scan_existing_plans(plans_dir: Path | None = None) -> int:
    """Scan existing plan directories to find the highest plan number.

    Args:
        plans_dir: Base plans directory (default: from get_plans_dir())

    Returns:
        Highest plan number found, or 0 if no plans exist

    Examples:
        >>> # With plans 0001-*, 0002-*, 0005-*
        >>> scan_existing_plans()
        5

    """
    if plans_dir is None:
        plans_dir = get_plans_dir()

    highest_number = 0

    # Scan active plans
    active_dir = plans_dir / "active"
    if active_dir.exists() and active_dir.is_dir():
        for plan_dir in active_dir.iterdir():
            if plan_dir.is_dir():
                number = extract_plan_number(plan_dir.name)
                if number is not None and number > highest_number:
                    highest_number = number

    # Scan archived plans
    archive_dir = plans_dir / "archive"
    if archive_dir.exists() and archive_dir.is_dir():
        for plan_dir in archive_dir.iterdir():
            if plan_dir.is_dir():
                number = extract_plan_number(plan_dir.name)
                if number is not None and number > highest_number:
                    highest_number = number

    return highest_number


def generate_slug(goal: str, max_length: int = 30) -> str:
    """Generate a URL-safe slug from a goal string.

    Args:
        goal: Goal text to slugify
        max_length: Maximum slug length (default: 30)

    Returns:
        Slugified string

    Examples:
        >>> generate_slug("Implement OAuth 2.0 Authentication")
        'implement-oauth-2-0-authentication'
        >>> generate_slug("A very long goal that exceeds the maximum length allowed", max_length=20)
        'very-long-goal-that'

    """
    slug = slugify(goal, max_length=max_length, word_boundary=True)

    # If slug is empty (e.g., non-Latin characters), use generic slug
    if not slug:
        slug = "plan"

    return slug


def generate_plan_id(
    goal: str,
    plans_dir: Path | None = None,
    max_retries: int = 10,
) -> str:
    """Generate a unique plan ID in format NNNN-slug.

    Scans existing plans to find the next available number and combines it
    with a slugified version of the goal.

    Args:
        goal: Goal text to create ID from
        plans_dir: Base plans directory (default: from get_plans_dir())
        max_retries: Maximum collision retry attempts (default: 10)

    Returns:
        Generated plan ID (e.g., "0001-oauth-auth")

    Raises:
        ValueError: If unable to generate unique ID after max_retries
        ValueError: If goal is empty or too short

    Examples:
        >>> generate_plan_id("Implement OAuth Authentication")
        '0001-implement-oauth-authentication'
        >>> # If 0001-* already exists:
        '0002-implement-oauth-authentication'

    """
    if not goal or len(goal.strip()) < 3:
        raise ValueError("Goal must be at least 3 characters")

    if plans_dir is None:
        plans_dir = get_plans_dir()

    # Generate slug from goal
    slug = generate_slug(goal)

    # Find next available plan number
    highest_number = scan_existing_plans(plans_dir)
    next_number = highest_number + 1

    # Try to create unique ID
    for attempt in range(max_retries):
        plan_id = PLAN_ID_FORMAT.format(next_number + attempt, slug)

        # Check if this ID already exists
        active_path = plans_dir / "active" / plan_id
        archive_pattern = f"*-{plan_id}"
        archived_paths = list((plans_dir / "archive").glob(archive_pattern))

        if not active_path.exists() and not archived_paths:
            return plan_id

    # If we exhausted retries, raise error
    raise ValueError(
        f"Unable to generate unique plan ID after {max_retries} attempts. Last tried: {plan_id}",
    )


def validate_plan_id_format(plan_id: str) -> bool:
    """Validate that a plan ID matches the expected format.

    Args:
        plan_id: Plan ID to validate

    Returns:
        True if valid format, False otherwise

    Examples:
        >>> validate_plan_id_format("0001-oauth-auth")
        True
        >>> validate_plan_id_format("1-oauth")
        False
        >>> validate_plan_id_format("not-a-plan-id")
        False

    """
    # Check format: NNNN-slug (exactly 4 digits, hyphen, then slug)
    pattern = re.compile(r"^\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")
    return bool(pattern.match(plan_id))


def parse_plan_id(plan_id: str) -> tuple[int, str]:
    """Parse a plan ID into its number and slug components.

    Args:
        plan_id: Plan ID to parse (NNNN-slug format)

    Returns:
        Tuple of (number, slug)

    Raises:
        ValueError: If plan ID format is invalid

    Examples:
        >>> parse_plan_id("0001-oauth-auth")
        (1, 'oauth-auth')
        >>> parse_plan_id("0042-user-registration")
        (42, 'user-registration')

    """
    if not validate_plan_id_format(plan_id):
        raise ValueError(f"Invalid plan ID format: {plan_id}")

    parts = plan_id.split("-", 1)
    number = int(parts[0])
    slug = parts[1]

    return number, slug
