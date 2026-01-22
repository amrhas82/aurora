"""Archive utility functions for Aurora Planning System.

Handles archiving plans with timestamp-based directory naming and atomic operations.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from aurora_planning.planning_config import get_plans_dir


def generate_archive_name(plan_id: str, archive_date: datetime | None = None) -> str:
    """Generate archive directory name with timestamp.

    Format: YYYY-MM-DD-NNNN-slug (e.g., 2026-01-03-0001-oauth-auth)

    Args:
        plan_id: Original plan ID (NNNN-slug format)
        archive_date: Date to use for timestamp (default: current date)

    Returns:
        Archive directory name

    Examples:
        >>> generate_archive_name("0001-oauth-auth", datetime(2026, 1, 3))
        '2026-01-03-0001-oauth-auth'

    """
    if archive_date is None:
        archive_date = datetime.now()

    date_prefix = archive_date.strftime("%Y-%m-%d")
    return f"{date_prefix}-{plan_id}"


def archive_plan(
    plan_id: str,
    plans_dir: Path | None = None,
    archive_date: datetime | None = None,
) -> Path:
    """Archive a plan by moving it from active to archive directory.

    This is an atomic operation - if any step fails, changes are rolled back.

    Args:
        plan_id: Plan ID to archive (NNNN-slug format)
        plans_dir: Base plans directory (default: from get_plans_dir())
        archive_date: Date to use for archive timestamp (default: current date)

    Returns:
        Path to archived plan directory

    Raises:
        FileNotFoundError: If plan doesn't exist in active directory
        ValueError: If plan directory is invalid
        OSError: If archive operation fails

    Examples:
        >>> archive_plan("0001-oauth-auth")
        PosixPath('/home/user/.aurora/plans/archive/2026-01-03-0001-oauth-auth')

    """
    if plans_dir is None:
        plans_dir = get_plans_dir()

    if archive_date is None:
        archive_date = datetime.now()

    # Validate source path
    source_dir = plans_dir / "active" / plan_id
    if not source_dir.exists():
        raise FileNotFoundError(f"Plan {plan_id} not found in active directory: {source_dir}")

    if not source_dir.is_dir():
        raise ValueError(f"Path exists but is not a directory: {source_dir}")

    # Generate archive name and destination path
    archive_name = generate_archive_name(plan_id, archive_date)
    dest_dir = plans_dir / "archive" / archive_name

    # Check if archive destination already exists
    if dest_dir.exists():
        raise FileExistsError(f"Archive destination already exists: {dest_dir}")

    # Ensure archive directory exists
    (plans_dir / "archive").mkdir(parents=True, exist_ok=True)

    # Update agents.json with archive metadata
    agents_file = source_dir / "agents.json"
    if agents_file.exists():
        try:
            with agents_file.open("r", encoding="utf-8") as f:
                agents_data = json.load(f)

            # Add archive metadata
            agents_data["status"] = "archived"
            agents_data["archived_at"] = archive_date.isoformat()

            # Write updated metadata (this is safe because we haven't moved yet)
            with agents_file.open("w", encoding="utf-8") as f:
                json.dump(agents_data, f, indent=2)

        except (json.JSONDecodeError, OSError) as e:
            raise OSError(f"Failed to update agents.json metadata: {e}") from e

    # Perform atomic move
    try:
        shutil.move(str(source_dir), str(dest_dir))
    except (OSError, shutil.Error) as e:
        # If move fails, the source directory is still intact
        raise OSError(f"Failed to move plan to archive: {e}") from e

    return dest_dir


def restore_plan(
    archive_name: str,
    plans_dir: Path | None = None,
) -> Path:
    """Restore an archived plan back to active directory.

    Args:
        archive_name: Archive directory name (YYYY-MM-DD-NNNN-slug format)
        plans_dir: Base plans directory (default: from get_plans_dir())

    Returns:
        Path to restored plan directory

    Raises:
        FileNotFoundError: If archived plan doesn't exist
        FileExistsError: If plan already exists in active directory
        OSError: If restore operation fails

    Examples:
        >>> restore_plan("2026-01-03-0001-oauth-auth")
        PosixPath('/home/user/.aurora/plans/active/0001-oauth-auth')

    """
    if plans_dir is None:
        plans_dir = get_plans_dir()

    # Extract original plan ID from archive name
    # Format: YYYY-MM-DD-NNNN-slug -> NNNN-slug
    parts = archive_name.split("-", 3)  # Split into [YYYY, MM, DD, NNNN-slug]
    if len(parts) != 4:
        raise ValueError(f"Invalid archive name format: {archive_name}")

    plan_id = parts[3]  # NNNN-slug

    # Validate source path
    source_dir = plans_dir / "archive" / archive_name
    if not source_dir.exists():
        raise FileNotFoundError(f"Archived plan not found: {source_dir}")

    # Check destination
    dest_dir = plans_dir / "active" / plan_id
    if dest_dir.exists():
        raise FileExistsError(f"Plan {plan_id} already exists in active directory: {dest_dir}")

    # Ensure active directory exists
    (plans_dir / "active").mkdir(parents=True, exist_ok=True)

    # Update agents.json to remove archive metadata
    agents_file = source_dir / "agents.json"
    if agents_file.exists():
        try:
            with agents_file.open("r", encoding="utf-8") as f:
                agents_data = json.load(f)

            # Remove archive metadata
            agents_data["status"] = "active"
            agents_data.pop("archived_at", None)

            # Write updated metadata
            with agents_file.open("w", encoding="utf-8") as f:
                json.dump(agents_data, f, indent=2)

        except (json.JSONDecodeError, OSError) as e:
            raise OSError(f"Failed to update agents.json metadata: {e}") from e

    # Perform atomic move
    try:
        shutil.move(str(source_dir), str(dest_dir))
    except (OSError, shutil.Error) as e:
        raise OSError(f"Failed to restore plan from archive: {e}") from e

    return dest_dir


def list_archived_plans(plans_dir: Path | None = None) -> list[tuple[str, str, datetime]]:
    """List all archived plans with their metadata.

    Args:
        plans_dir: Base plans directory (default: from get_plans_dir())

    Returns:
        List of tuples (archive_name, plan_id, archive_date)

    Examples:
        >>> list_archived_plans()
        [('2026-01-03-0001-oauth-auth', '0001-oauth-auth', datetime(2026, 1, 3))]

    """
    if plans_dir is None:
        plans_dir = get_plans_dir()

    archive_dir = plans_dir / "archive"
    if not archive_dir.exists():
        return []

    archived = []
    for plan_dir in archive_dir.iterdir():
        if not plan_dir.is_dir():
            continue

        # Parse archive name: YYYY-MM-DD-NNNN-slug
        parts = plan_dir.name.split("-", 3)
        if len(parts) != 4:
            continue  # Skip invalid format

        try:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            archive_date = datetime(year, month, day)
            plan_id = parts[3]

            archived.append((plan_dir.name, plan_id, archive_date))
        except (ValueError, TypeError):
            continue  # Skip if date parsing fails

    # Sort by archive date (most recent first)
    archived.sort(key=lambda x: x[2], reverse=True)

    return archived
