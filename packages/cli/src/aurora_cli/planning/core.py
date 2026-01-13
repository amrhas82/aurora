"""Core planning logic for Aurora Planning System.

This module provides the core functions for plan management:
- init_planning_directory: Initialize planning directory structure
- create_plan: Create a new plan with SOAR decomposition
- list_plans: List active and/or archived plans
- show_plan: Show plan details with file status
- archive_plan: Archive a completed plan with rollback

All functions return Result types for graceful degradation.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aurora_cli.planning.errors import VALIDATION_MESSAGES
from aurora_cli.planning.models import Complexity, Plan, PlanManifest, PlanStatus, Subgoal
from aurora_cli.planning.results import (
    ArchiveResult,
    InitResult,
    ListResult,
    PlanResult,
    PlanSummary,
    ShowResult,
)

logger = logging.getLogger(__name__)

# Import renderer for template-based file generation
try:
    from aurora_cli.planning.renderer import render_plan_files

    USE_TEMPLATES = True
except ImportError:
    USE_TEMPLATES = False
    logger.warning("Template renderer not available, using fallback generation")

if TYPE_CHECKING:
    from aurora_cli.config import Config


def get_default_plans_path() -> Path:
    """Get the default plans directory path.

    Returns:
        Path to ./.aurora/plans (project-local)
    """
    return Path.cwd() / ".aurora" / "plans"


def validate_plan_structure(plan_dir: Path, plan_id: str) -> tuple[list[str], list[str]]:
    """Validate plan directory structure and files.

    Checks for required and optional files, validates agents.json structure.

    Args:
        plan_dir: Path to plan directory
        plan_id: Plan ID for validation messages

    Returns:
        Tuple of (errors, warnings):
        - errors: Critical issues that block operations
        - warnings: Non-critical issues (missing optional files)

    Example:
        >>> errors, warnings = validate_plan_structure(Path("/path/to/plan"), "0001-test")
        >>> if errors:
        ...     print("Validation failed:", errors)
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check required files
    required_files = [
        ("plan.md", "Base plan overview"),
        ("prd.md", "Product requirements document"),
        ("tasks.md", "Task checklist"),
        ("agents.json", "Machine-readable plan data"),
    ]

    for filename, description in required_files:
        file_path = plan_dir / filename
        if not file_path.exists():
            errors.append(f"Missing required file: {filename} ({description})")

    # Check optional capability spec files
    optional_files = [
        (f"specs/{plan_id}-planning.md", "Planning capability spec"),
        (f"specs/{plan_id}-commands.md", "Commands capability spec"),
        (f"specs/{plan_id}-validation.md", "Validation capability spec"),
        (f"specs/{plan_id}-schemas.md", "Schemas capability spec"),
    ]

    for filename, description in optional_files:
        file_path = plan_dir / filename
        if not file_path.exists():
            warnings.append(f"Missing optional file: {filename} ({description})")

    # Validate agents.json if it exists
    agents_json = plan_dir / "agents.json"
    if agents_json.exists():
        try:
            content = agents_json.read_text()
            plan = Plan.model_validate_json(content)

            # Validate plan ID matches directory name
            if plan.plan_id != plan_id and not plan_id.startswith(plan.plan_id):
                errors.append(
                    f"Plan ID mismatch: agents.json has '{plan.plan_id}' "
                    f"but directory is '{plan_id}'"
                )

        except Exception as e:
            errors.append(f"Invalid agents.json: {e}")

    return errors, warnings


def init_planning_directory(
    path: Path | None = None,
    force: bool = False,
) -> InitResult:
    """Initialize planning directory with graceful degradation.

    Creates the planning directory structure:
    - active/ - Directory for active plans
    - archive/ - Directory for archived plans
    - templates/ - Directory for custom templates
    - manifest.json - Manifest file for fast listing

    Args:
        path: Custom directory path (default: ~/.aurora/plans)
        force: Force reinitialize even if exists

    Returns:
        InitResult with success status and path or error message

    Example:
        >>> result = init_planning_directory()
        >>> if result.success:
        ...     print(f"Initialized at {result.path}")
    """
    target = path or get_default_plans_path()
    target = Path(target).expanduser().resolve()

    # Check if already initialized (active dir exists)
    active_dir = target / "active"
    if active_dir.exists() and not force:
        return InitResult(
            success=True,
            path=target,
            created=False,
            warning="Planning directory already exists. No changes made.",
        )

    # Check parent directory exists or can be created
    parent = target.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return InitResult(
                success=False,
                path=target,
                error=VALIDATION_MESSAGES["PLANS_DIR_NO_WRITE_PERMISSION"].format(path=str(parent)),
            )
        except OSError as e:
            return InitResult(
                success=False,
                path=target,
                error=f"Failed to create parent directory: {e}",
            )

    # Check write permissions on parent
    if not os.access(parent, os.W_OK):
        return InitResult(
            success=False,
            path=target,
            error=VALIDATION_MESSAGES["PLANS_DIR_NO_WRITE_PERMISSION"].format(path=str(parent)),
        )

    try:
        # Create directories
        (target / "active").mkdir(parents=True, exist_ok=True)
        (target / "archive").mkdir(parents=True, exist_ok=True)
        (target / "templates").mkdir(parents=True, exist_ok=True)

        # Create manifest
        manifest = PlanManifest()
        manifest_path = target / "manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2))

        return InitResult(
            success=True,
            path=target,
            created=True,
            message=f"Planning directory initialized at {target}",
        )

    except PermissionError:
        return InitResult(
            success=False,
            path=target,
            error=VALIDATION_MESSAGES["PLANS_DIR_NO_WRITE_PERMISSION"].format(path=str(target)),
        )
    except OSError as e:
        return InitResult(
            success=False,
            path=target,
            error=f"Failed to create planning directory: {e}",
        )


def _get_plans_dir(config: Config | None = None) -> Path:
    """Get plans directory from config or default.

    Args:
        config: Optional CLI configuration

    Returns:
        Path to plans directory
    """
    if config is not None and hasattr(config, "get_plans_path"):
        return Path(config.get_plans_path()).expanduser().resolve()
    return get_default_plans_path()


def _load_manifest(plans_dir: Path) -> PlanManifest:
    """Load manifest from plans directory.

    Args:
        plans_dir: Path to plans directory

    Returns:
        PlanManifest instance (new if not found)
    """
    manifest_path = plans_dir / "manifest.json"
    if manifest_path.exists():
        try:
            return PlanManifest.model_validate_json(manifest_path.read_text())
        except Exception:
            pass
    return PlanManifest()


def _save_manifest(plans_dir: Path, manifest: PlanManifest) -> None:
    """Save manifest to plans directory.

    Args:
        plans_dir: Path to plans directory
        manifest: Manifest to save
    """
    manifest_path = plans_dir / "manifest.json"
    manifest.updated_at = datetime.utcnow()
    manifest_path.write_text(manifest.model_dump_json(indent=2))


def _update_manifest(
    plans_dir: Path,
    plan_id: str,
    action: str,
    archived_id: str | None = None,
) -> None:
    """Update manifest after plan operation.

    Args:
        plans_dir: Path to plans directory
        plan_id: Plan ID being modified
        action: Action type ("active", "archive", "remove")
        archived_id: New ID after archiving (for archive action)
    """
    manifest = _load_manifest(plans_dir)

    if action == "active":
        manifest.add_active_plan(plan_id)
    elif action == "archive":
        manifest.archive_plan(plan_id, archived_id)
    elif action == "remove":
        if plan_id in manifest.active_plans:
            manifest.active_plans.remove(plan_id)
        if plan_id in manifest.archived_plans:
            manifest.archived_plans.remove(plan_id)

    _save_manifest(plans_dir, manifest)


def rebuild_manifest(plans_dir: Path) -> PlanManifest:
    """Rebuild manifest by scanning filesystem.

    This is called when manifest is missing or out of sync.

    Args:
        plans_dir: Path to plans directory

    Returns:
        Newly rebuilt PlanManifest
    """
    manifest = PlanManifest()

    # Scan active plans
    active_dir = plans_dir / "active"
    if active_dir.exists():
        for plan_path in active_dir.iterdir():
            if plan_path.is_dir():
                manifest.add_active_plan(plan_path.name)

    # Scan archived plans
    archive_dir = plans_dir / "archive"
    if archive_dir.exists():
        for plan_path in archive_dir.iterdir():
            if plan_path.is_dir():
                manifest.archived_plans.append(plan_path.name)

    _save_manifest(plans_dir, manifest)
    logger.info(
        "Rebuilt manifest with %d active and %d archived plans",
        len(manifest.active_plans),
        len(manifest.archived_plans),
    )
    return manifest


def _get_existing_plan_ids(plans_dir: Path) -> list[str]:
    """Get list of existing plan IDs.

    Args:
        plans_dir: Path to plans directory

    Returns:
        List of plan ID strings
    """
    ids = []
    active_dir = plans_dir / "active"
    archive_dir = plans_dir / "archive"

    for scan_dir in [active_dir, archive_dir]:
        if scan_dir.exists():
            for plan_path in scan_dir.iterdir():
                if plan_path.is_dir():
                    ids.append(plan_path.name)

    return ids


def list_plans(
    archived: bool = False,
    all_plans: bool = False,
    config: Config | None = None,
    use_manifest: bool = True,
) -> ListResult:
    """List plans with filtering.

    Returns empty list with warning if not initialized.

    Args:
        archived: Show archived plans only
        all_plans: Show all plans (active and archived)
        config: Optional CLI configuration
        use_manifest: Use manifest for fast listing (default: True)

    Returns:
        ListResult with plan summaries or warning/errors
    """
    plans_dir = _get_plans_dir(config)

    if not plans_dir.exists():
        return ListResult(
            plans=[],
            warning=VALIDATION_MESSAGES["PLANS_DIR_NOT_INITIALIZED"],
        )

    plans: list[PlanSummary] = []
    errors: list[str] = []

    # Try to use manifest for fast listing
    manifest = _load_manifest(plans_dir) if use_manifest else None
    manifest_valid = manifest is not None and (manifest.active_plans or manifest.archived_plans)

    # If manifest doesn't exist or is empty, rebuild it
    if use_manifest and not manifest_valid:
        try:
            manifest = rebuild_manifest(plans_dir)
        except Exception as e:
            logger.warning("Failed to rebuild manifest, falling back to filesystem scan: %s", e)
            manifest = None

    # Get plan IDs to load (from manifest or filesystem)
    plan_ids_to_load: list[tuple[str, str]] = []  # (plan_id, status)

    if manifest and use_manifest:
        # Use manifest
        if all_plans or not archived:
            plan_ids_to_load.extend((pid, "active") for pid in manifest.active_plans)
        if all_plans or archived:
            plan_ids_to_load.extend((pid, "archived") for pid in manifest.archived_plans)
    else:
        # Fallback to filesystem scan
        dirs_to_scan: list[tuple[str, Path]] = []
        if all_plans or not archived:
            dirs_to_scan.append(("active", plans_dir / "active"))
        if all_plans or archived:
            dirs_to_scan.append(("archived", plans_dir / "archive"))

        for status, scan_dir in dirs_to_scan:
            if not scan_dir.exists():
                continue
            for plan_path in scan_dir.iterdir():
                if plan_path.is_dir():
                    plan_ids_to_load.append((plan_path.name, status))

    # Load plan data
    for plan_id, status in plan_ids_to_load:
        # Determine plan directory
        if status == "active":
            plan_dir = plans_dir / "active" / plan_id
        else:
            plan_dir = plans_dir / "archive" / plan_id

        if not plan_dir.exists():
            errors.append(f"Plan {plan_id} in manifest but not found on disk")
            continue

        # Validate plan structure
        plan_errors, plan_warnings = validate_plan_structure(plan_dir, plan_id)
        if plan_errors:
            errors.append(f"Plan {plan_id}: {', '.join(plan_errors)}")
            continue

        # Load plan data
        agents_json = plan_dir / "agents.json"
        try:
            plan = Plan.model_validate_json(agents_json.read_text())
            plans.append(PlanSummary.from_plan(plan, status))
        except Exception as e:
            errors.append(f"Invalid plan {plan_id}: {e}")

    # Sort by creation date (newest first)
    plans.sort(key=lambda p: p.created_at, reverse=True)

    return ListResult(
        plans=plans,
        errors=errors if errors else None,
    )


def show_plan(
    plan_id: str,
    archived: bool = False,
    config: Config | None = None,
) -> ShowResult:
    """Show plan details with file status.

    Args:
        plan_id: Plan ID to show (supports partial match)
        archived: Search in archived plans
        config: Optional CLI configuration

    Returns:
        ShowResult with plan details or error message
    """
    plans_dir = _get_plans_dir(config)

    if not plans_dir.exists():
        return ShowResult(
            success=False,
            error=VALIDATION_MESSAGES["PLANS_DIR_NOT_INITIALIZED"],
        )

    # Search for plan
    search_dir = plans_dir / ("archive" if archived else "active")
    if not search_dir.exists():
        return ShowResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_NOT_FOUND"].format(plan_id=plan_id),
        )

    plan_dirs = list(search_dir.glob(f"*{plan_id}*"))

    if not plan_dirs:
        # Check other location
        other_dir = plans_dir / ("active" if archived else "archive")
        if other_dir.exists():
            other_matches = list(other_dir.glob(f"*{plan_id}*"))
            if other_matches:
                hint = "--archived" if not archived else "without --archived"
                location = "archive" if not archived else "active"
                return ShowResult(
                    success=False,
                    error=f"Plan '{plan_id}' found in {location}. Use {hint}.",
                )

        return ShowResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_NOT_FOUND"].format(plan_id=plan_id),
        )

    plan_dir = plan_dirs[0]

    # Validate plan structure
    validation_errors, validation_warnings = validate_plan_structure(plan_dir, plan_dir.name)
    if validation_errors:
        return ShowResult(
            success=False,
            error=f"Plan validation failed: {', '.join(validation_errors)}",
        )

    agents_json = plan_dir / "agents.json"
    try:
        plan = Plan.model_validate_json(agents_json.read_text())
    except Exception:
        return ShowResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_FILE_CORRUPT"].format(file=str(agents_json)),
        )

    # Check file status (all 8 files)
    files_status = {
        # Base files
        "plan.md": (plan_dir / "plan.md").exists(),
        "prd.md": (plan_dir / "prd.md").exists(),
        "tasks.md": (plan_dir / "tasks.md").exists(),
        "agents.json": True,
        # Capability specs
        f"specs/{plan.plan_id}-planning.md": (
            plan_dir / "specs" / f"{plan.plan_id}-planning.md"
        ).exists(),
        f"specs/{plan.plan_id}-commands.md": (
            plan_dir / "specs" / f"{plan.plan_id}-commands.md"
        ).exists(),
        f"specs/{plan.plan_id}-validation.md": (
            plan_dir / "specs" / f"{plan.plan_id}-validation.md"
        ).exists(),
        f"specs/{plan.plan_id}-schemas.md": (
            plan_dir / "specs" / f"{plan.plan_id}-schemas.md"
        ).exists(),
    }

    return ShowResult(
        success=True,
        plan=plan,
        plan_dir=plan_dir,
        files_status=files_status,
    )


def archive_plan(
    plan_id: str,
    force: bool = False,
    config: Config | None = None,
) -> ArchiveResult:
    """Archive plan with atomic move and rollback on failure.

    Args:
        plan_id: Plan ID to archive
        force: Skip confirmation (for programmatic use)
        config: Optional CLI configuration

    Returns:
        ArchiveResult with archive details or error message
    """
    plans_dir = _get_plans_dir(config)
    active_dir = plans_dir / "active"
    archive_dir = plans_dir / "archive"

    # Check initialized
    if not plans_dir.exists():
        return ArchiveResult(
            success=False,
            error=VALIDATION_MESSAGES["PLANS_DIR_NOT_INITIALIZED"],
        )

    # Find the plan
    plan_dirs = list(active_dir.glob(f"*{plan_id}*"))
    if not plan_dirs:
        return ArchiveResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_NOT_FOUND"].format(plan_id=plan_id),
        )

    source_dir = plan_dirs[0]
    plan_name = source_dir.name

    # Load and validate plan
    agents_json = source_dir / "agents.json"
    if not agents_json.exists():
        return ArchiveResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_FILE_MISSING"].format(file="agents.json"),
        )

    try:
        plan = Plan.model_validate_json(agents_json.read_text())
    except Exception:
        return ArchiveResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_FILE_CORRUPT"].format(file=str(agents_json)),
        )

    # Check if already archived
    if plan.status == PlanStatus.ARCHIVED:
        return ArchiveResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_ALREADY_ARCHIVED"].format(plan_id=plan_id),
        )

    # Calculate archive path
    timestamp = datetime.now().strftime("%Y-%m-%d")
    target_dir = archive_dir / f"{timestamp}-{plan_name}"

    # Atomic archive with rollback
    backup_json = agents_json.read_text()

    try:
        # Update plan metadata
        plan.status = PlanStatus.ARCHIVED
        plan.archived_at = datetime.utcnow()
        plan.duration_days = (plan.archived_at - plan.created_at).days

        # Write updated agents.json
        agents_json.write_text(plan.model_dump_json(indent=2))

        # Move directory
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_dir), str(target_dir))

        # Update manifest
        _update_manifest(plans_dir, plan_name, "archive", f"{timestamp}-{plan_name}")

        return ArchiveResult(
            success=True,
            plan=plan,
            source_dir=source_dir,
            target_dir=target_dir,
            duration_days=plan.duration_days,
        )

    except Exception as e:
        # Rollback
        if agents_json.exists():
            agents_json.write_text(backup_json)
        if target_dir.exists() and not source_dir.exists():
            shutil.move(str(target_dir), str(source_dir))

        return ArchiveResult(
            success=False,
            error=VALIDATION_MESSAGES["ARCHIVE_ROLLBACK"].format(error=str(e)),
        )


def _generate_plan_id(goal: str, plans_dir: Path) -> str:
    """Generate a unique plan ID from goal.

    Format: NNNN-slug where NNNN is sequential number and slug
    is derived from goal (lowercase, hyphenated, truncated).

    Args:
        goal: The plan goal text
        plans_dir: Plans directory to check for existing IDs

    Returns:
        Unique plan ID string
    """
    existing_ids = _get_existing_plan_ids(plans_dir)

    # Find next number
    max_num = 0
    for plan_id in existing_ids:
        match = re.match(r"^(\d+)-", plan_id)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    next_num = max_num + 1

    # Generate slug from goal - extract 3-4 meaningful words
    words = goal.lower()
    words = re.sub(r"[^a-z0-9\s]", "", words)  # Remove special chars
    words = words.split()

    # Filter out common stop words to get meaningful words
    stop_words = {
        "i",
        "want",
        "to",
        "the",
        "a",
        "an",
        "and",
        "or",
        "for",
        "of",
        "in",
        "on",
        "is",
        "are",
        "how",
        "do",
        "does",
        "can",
        "could",
        "would",
        "should",
        "will",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "this",
        "that",
        "these",
        "those",
        "my",
        "your",
        "our",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "when",
        "where",
        "why",
        "with",
    }
    meaningful = [w for w in words if w not in stop_words and len(w) > 1]

    # Take first 3-4 meaningful words
    slug_words = meaningful[:4] if meaningful else ["plan"]
    slug = "-".join(slug_words)

    # Ensure reasonable length
    if len(slug) > 40:
        slug = "-".join(slug_words[:3])

    if not slug:
        slug = "plan"

    return f"{next_num:04d}-{slug}"


def _validate_goal(goal: str) -> tuple[bool, str | None]:
    """Validate goal text.

    Args:
        goal: The plan goal text

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(goal) < 10:
        return False, VALIDATION_MESSAGES["GOAL_TOO_SHORT"]
    if len(goal) > 500:
        return False, VALIDATION_MESSAGES["GOAL_TOO_LONG"]
    return True, None


def _assess_complexity(goal: str, subgoals: list[Subgoal]) -> Complexity:
    """Assess plan complexity based on goal and subgoals.

    Args:
        goal: The plan goal text
        subgoals: List of subgoals

    Returns:
        Complexity enum value
    """
    # Heuristic: count dependencies and keywords
    total_deps = sum(len(sg.dependencies) for sg in subgoals)
    complex_keywords = ["refactor", "migrate", "architecture", "integrate", "security"]
    has_complex_keyword = any(kw in goal.lower() for kw in complex_keywords)

    if len(subgoals) >= 5 or total_deps >= 5 or has_complex_keyword:
        return Complexity.COMPLEX
    elif len(subgoals) >= 3 or total_deps >= 2:
        return Complexity.MODERATE
    else:
        return Complexity.SIMPLE


def _check_agent_availability(agent: str) -> bool:
    """Check if an agent is available in the manifest.

    Args:
        agent: Agent ID (e.g., "@full-stack-dev")

    Returns:
        True if agent exists, False otherwise
    """
    try:
        # Try to load agent manifest
        import io

        # Silent config load
        import sys

        from aurora_cli.agent_discovery import AgentManifest, AgentScanner, ManifestManager
        from aurora_cli.config import load_config

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            config = load_config()
        finally:
            sys.stdout = old_stdout

        manifest_path = Path(config.get_manifest_path())
        scanner = AgentScanner(config.agents_discovery_paths)
        manager = ManifestManager(scanner=scanner)

        manifest = manager.get_or_refresh(
            manifest_path,
            auto_refresh=config.agents_auto_refresh,
            refresh_interval_hours=config.agents_refresh_interval_hours,
        )

        # Remove @ prefix for search
        agent_id = agent.lstrip("@")
        return manifest.get_agent(agent_id) is not None

    except Exception as e:
        logger.warning("Could not check agent availability: %s", e)
        return True  # Assume available if can't check


def _write_goals_only(
    plan: Plan,
    plan_dir: Path,
    memory_context: list[tuple[str, float]],
    agent_gaps: list["AgentGap"] | None = None,
) -> None:
    """Write only goals.json to disk (for aur goals command).

    Per PRD-0026, aur goals creates ONLY goals.json. The /plan skill
    will later read this and generate prd.md, tasks.md, and specs/.

    Args:
        plan: Plan object with subgoals and agent assignments
        plan_dir: Directory to create and write goals.json to
        memory_context: List of (file_path, relevance) tuples from memory search
        agent_gaps: List of AgentGap objects (new format with ideal_agent, assigned_agent)

    Raises:
        OSError: If directory creation or file write fails
    """
    from aurora_cli.planning.models import AgentGap

    # Create directory
    plan_dir.mkdir(parents=True, exist_ok=True)

    # Use provided agent_gaps or fallback to legacy format from plan.agent_gaps
    gaps_to_write = agent_gaps or []
    if not gaps_to_write and plan.agent_gaps:
        # Legacy fallback: convert string list to AgentGap objects
        gaps_to_write = [
            AgentGap(
                subgoal_id="",
                recommended_agent=gap,
                agent_exists=False,
                fallback="@full-stack-dev",
                suggested_capabilities=[],
            )
            for gap in plan.agent_gaps
        ]

    # Generate goals.json content
    goals_data = generate_goals_json(
        plan_id=plan.plan_id,
        goal=plan.goal,
        subgoals=plan.subgoals,
        memory_context=memory_context,
        gaps=gaps_to_write,
    )

    # Write goals.json
    goals_file = plan_dir / "goals.json"
    goals_file.write_text(goals_data.model_dump_json(indent=2))

    logger.info("Created goals.json at %s (aur goals mode)", plan_dir)


def _write_plan_files(plan: Plan, plan_dir: Path) -> None:
    """Write all 8 plan files to disk using templates with atomic operation.

    Generates files in a temporary directory first, then atomically moves
    them to the final location. This ensures users never see partial plans.

    Generates:
    - 4 base files: plan.md, prd.md, tasks.md, agents.json
    - 4 capability specs: specs/{plan-id}-{planning,commands,validation,schemas}.md

    Args:
        plan: Plan to write
        plan_dir: Directory to write files to

    Raises:
        OSError: If file write or move fails
    """
    # Use atomic file generation with templates
    if USE_TEMPLATES:
        temp_dir = plan_dir.parent / ".tmp" / plan.plan_id

        try:
            # Clean up any leftover temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            # Create temp directory
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Render all files to temp directory
            created_files = render_plan_files(plan, temp_dir)
            logger.debug(
                "Generated %d files using templates for plan %s", len(created_files), plan.plan_id
            )

            # Validate all files were created and have content
            for file_path in created_files:
                if not file_path.exists():
                    raise OSError(f"File not created: {file_path}")
                if file_path.stat().st_size == 0:
                    raise OSError(f"File is empty: {file_path}")
                # Validate JSON if it's agents.json
                if file_path.name == "agents.json":
                    import json

                    try:
                        json.loads(file_path.read_text())
                    except json.JSONDecodeError as e:
                        raise OSError(f"Invalid JSON in agents.json: {e}")

            # Atomic move: rename temp dir to final location
            if plan_dir.exists():
                # Backup existing directory if it exists (shouldn't happen normally)
                backup_dir = (
                    plan_dir.parent
                    / f".backup-{plan.plan_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                )
                shutil.move(str(plan_dir), str(backup_dir))
                logger.warning("Backed up existing plan to %s", backup_dir)

            shutil.move(str(temp_dir), str(plan_dir))
            logger.info("Atomically created plan at %s", plan_dir)
            return

        except Exception as e:
            logger.warning("Template rendering failed: %s", e)
            # Clean up temp directory on error
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise

    # Fallback: Write the four base plan files manually (without capability specs)
    # (only used if USE_TEMPLATES is False)
    plan_dir.mkdir(parents=True, exist_ok=True)
    # Write agents.json (machine-readable)
    agents_json = plan_dir / "agents.json"
    agents_json.write_text(plan.model_dump_json(indent=2))

    # Write plan.md (human-readable overview)
    plan_md = plan_dir / "plan.md"
    plan_md_content = _generate_plan_md(plan)
    plan_md.write_text(plan_md_content)

    # Write prd.md (product requirements placeholder)
    prd_md = plan_dir / "prd.md"
    prd_md_content = _generate_prd_md(plan)
    prd_md.write_text(prd_md_content)

    # Write tasks.md (implementation task list)
    tasks_md = plan_dir / "tasks.md"
    tasks_md_content = _generate_tasks_md(plan)
    tasks_md.write_text(tasks_md_content)

    logger.warning("Only 4 base files generated (templates not available)")


def _generate_plan_md(plan: Plan) -> str:
    """Generate plan.md content.

    Args:
        plan: Plan to generate from

    Returns:
        Markdown content string
    """
    lines = [
        f"# Plan: {plan.plan_id}",
        "",
        f"**Goal:** {plan.goal}",
        "",
        f"**Status:** {plan.status.value}",
        f"**Complexity:** {plan.complexity.value}",
        f"**Created:** {plan.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Subgoals",
        "",
    ]

    for i, sg in enumerate(plan.subgoals, 1):
        lines.append(f"### {i}. {sg.title}")
        lines.append("")
        lines.append(f"**Agent:** {sg.recommended_agent}")
        if sg.dependencies:
            lines.append(f"**Dependencies:** {', '.join(sg.dependencies)}")
        lines.append("")
        lines.append(sg.description)
        lines.append("")

    if plan.agent_gaps:
        lines.append("## Agent Gaps")
        lines.append("")
        lines.append("The following agents were not found in the manifest:")
        for gap in plan.agent_gaps:
            lines.append(f"- {gap}")
        lines.append("")
        lines.append("Consider using fallback agents or installing missing agents.")
        lines.append("")

    return "\n".join(lines)


def _generate_prd_md(plan: Plan) -> str:
    """Generate prd.md content (placeholder).

    Args:
        plan: Plan to generate from

    Returns:
        Markdown content string
    """
    return f"""# Product Requirements: {plan.plan_id}

## Overview

{plan.goal}

## User Stories

<!-- Add user stories here -->

## Functional Requirements

<!-- Add functional requirements here -->

## Non-Functional Requirements

<!-- Add non-functional requirements here -->

## Acceptance Criteria

<!-- Add acceptance criteria here -->

---
*Generated by Aurora Planning System*
"""


def _generate_tasks_md(plan: Plan) -> str:
    """Generate tasks.md content.

    Args:
        plan: Plan to generate from

    Returns:
        Markdown content string
    """
    lines = [
        f"# Tasks: {plan.plan_id}",
        "",
        f"Goal: {plan.goal}",
        "",
        "## Implementation Tasks",
        "",
    ]

    for i, sg in enumerate(plan.subgoals, 1):
        lines.append(f"- [ ] {i}.0 {sg.title}")
        lines.append(f"  - Agent: {sg.recommended_agent}")
        if sg.dependencies:
            lines.append(f"  - Dependencies: {', '.join(sg.dependencies)}")
        lines.append("")

    lines.append("## Relevant Files")
    lines.append("")
    lines.append("<!-- Add relevant files as you work -->")
    lines.append("")

    return "\n".join(lines)


def generate_goals_json(
    plan_id: str,
    goal: str,
    subgoals: list[Subgoal],
    memory_context: list[tuple[str, float]],
    gaps: list["AgentGap"],
) -> "Goals":
    """Generate Goals object for goals.json output.

    Converts plan data into the Goals format matching FR-6.2 from PRD-0026.

    Args:
        plan_id: Plan ID (NNNN-slug format)
        goal: High-level goal description
        subgoals: List of Subgoal objects
        memory_context: List of (file_path, relevance) tuples
        gaps: List of AgentGap objects

    Returns:
        Goals object ready for JSON serialization

    Example:
        >>> subgoals = [Subgoal(id="sg-1", title="Task", ...)]
        >>> memory = [("src/api.py", 0.85)]
        >>> goals = generate_goals_json("0001-test", "Test goal", subgoals, memory, [])
        >>> print(goals.model_dump_json(indent=2))
    """
    from aurora_cli.planning.models import Goals, MemoryContext, SubgoalData

    # Convert memory context tuples to MemoryContext objects
    memory_objects = [
        MemoryContext(file=file_path, relevance=score) for file_path, score in memory_context
    ]

    # Convert Subgoal objects to SubgoalData for goals.json format
    # Include ideal_agent and ideal_agent_desc for gap detection
    subgoal_objects = []
    for sg in subgoals:
        # Sanitize dependencies - remove self-references and invalid IDs
        clean_deps = [dep for dep in sg.dependencies if dep != sg.id]  # Remove self-dependency

        # Get ideal_agent (may be empty for legacy decompositions)
        ideal_agent = getattr(sg, "ideal_agent", None) or None
        ideal_agent_desc = getattr(sg, "ideal_agent_desc", None) or None

        subgoal_objects.append(
            SubgoalData(
                id=sg.id,
                title=sg.title,
                description=sg.description,
                ideal_agent=ideal_agent,
                ideal_agent_desc=ideal_agent_desc,
                agent=sg.assigned_agent,
                dependencies=clean_deps,
            )
        )

    # Create Goals object
    goals = Goals(
        id=plan_id,
        title=goal,
        created_at=datetime.utcnow(),
        status="ready_for_planning",
        memory_context=memory_objects,
        subgoals=subgoal_objects,
        gaps=gaps,
    )

    return goals


def create_plan(
    goal: str,
    context_files: list[Path] | None = None,
    auto_decompose: bool = True,
    config: Config | None = None,
    yes: bool = False,
    non_interactive: bool = False,
    goals_only: bool = False,
) -> PlanResult:
    """Create a new plan with SOAR-based goal decomposition.

    This is the main entry point for plan creation. When goals_only=True,
    creates only goals.json (for aur goals command). When goals_only=False,
    creates full plan with PRD, tasks, and specs (for /plan skill).

    Args:
        goal: The high-level goal to decompose
        context_files: Optional list of context files for informed decomposition
        auto_decompose: Whether to use SOAR for automatic subgoal generation
        config: Optional CLI configuration
        yes: Skip confirmation prompt and proceed automatically
        non_interactive: Alias for yes flag (skip confirmation prompt)
        goals_only: If True, only create goals.json (aur goals behavior per PRD-0026)

    Returns:
        PlanResult with plan details or error message

    Example:
        >>> result = create_plan("Implement OAuth2 authentication", goals_only=True)
        >>> if result.success:
        ...     print(f"Created plan: {result.plan.plan_id}")
    """
    plans_dir = _get_plans_dir(config)

    # Validate goal
    is_valid, error_msg = _validate_goal(goal)
    if not is_valid:
        return PlanResult(success=False, error=error_msg)

    # Check initialized
    if not plans_dir.exists():
        # Auto-initialize
        init_result = init_planning_directory(path=plans_dir)
        if not init_result.success:
            return PlanResult(success=False, error=init_result.error)

    # Generate plan ID
    plan_id = _generate_plan_id(goal, plans_dir)

    # Assess complexity
    complexity = _assess_complexity(goal, [])  # Initial assessment before decomposition

    # Search memory for goal-level context (NEW - for Task 2.2)
    from aurora_cli.planning.memory import search_memory_for_goal

    memory_context = search_memory_for_goal(goal, config=config, limit=10, threshold=0.3)

    # Display memory search results (NEW - for Task 2.2)
    if memory_context:
        from rich.console import Console

        console = Console()
        console.print(f"\n[bold]🔍 Found {len(memory_context)} relevant context files:[/]")
        for file_path, score in memory_context:
            # Color code by relevance
            if score >= 0.8:
                color = "green"
            elif score >= 0.6:
                color = "yellow"
            else:
                color = "dim"
            console.print(f"   [{color}]{file_path} ({score:.2f})[/{color}]")
        console.print("")
    else:
        from rich.console import Console

        console = Console()
        console.print(
            "[dim]No memory index found. For code-aware planning, run: aur mem index .[/]\n"
        )

    # Generate subgoals using PlanDecomposer
    if auto_decompose:
        from aurora_cli.planning.decompose import PlanDecomposer
        from aurora_cli.planning.models import AgentGap

        decomposer = PlanDecomposer(config=config)

        # Get store for file resolution
        store = None
        try:
            from aurora_cli.memory import get_default_db_path
            from aurora_core.store.sqlite import SQLiteStore

            db_path = get_default_db_path(config)
            if db_path.exists():
                store = SQLiteStore(str(db_path))
        except Exception:
            pass

        # Decompose with file resolution
        subgoals, file_resolutions, decomposition_source = decomposer.decompose_with_files(
            goal=goal,
            complexity=complexity,
            context_files=[str(f) for f in context_files] if context_files else None,
            store=store,
        )
    else:
        # Single subgoal fallback
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Implement goal",
                description=goal,
                recommended_agent="@full-stack-dev",
            )
        ]
        file_resolutions = {}
        decomposition_source = "heuristic"

    # Reassess complexity now that we have actual subgoals
    complexity = _assess_complexity(goal, subgoals)

    # Sanitize dependencies - remove self-references that break validation
    for sg in subgoals:
        if sg.dependencies:
            sg.dependencies = [dep for dep in sg.dependencies if dep != sg.id]

    # Collect agent gaps using ideal vs assigned comparison
    from aurora_cli.planning.agents import AgentMatcher, AgentRecommender
    from aurora_cli.planning.models import AgentGap

    recommender = AgentRecommender(config=config)
    agent_gaps: list[AgentGap] = []
    agents_assigned = 0

    for sg in subgoals:
        # Gap detection: ideal_agent != assigned_agent
        # If ideal_agent is empty, assume it equals assigned_agent (no gap)
        ideal = sg.ideal_agent or sg.assigned_agent
        assigned = sg.assigned_agent

        is_gap = ideal != assigned

        if is_gap:
            # Gap detected - create AgentGap
            agent_gaps.append(
                AgentGap(
                    subgoal_id=sg.id,
                    ideal_agent=ideal,
                    ideal_agent_desc=sg.ideal_agent_desc or "",
                    assigned_agent=assigned,
                )
            )
        else:
            agents_assigned += 1

    # Calculate file resolution statistics
    files_resolved = sum(len(resolutions) for resolutions in file_resolutions.values())
    all_confidences = [
        res.confidence for resolutions in file_resolutions.values() for res in resolutions
    ]
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

    # Build warnings
    warnings = []
    if agent_gaps:
        warnings.append(f"Agent gaps detected: {len(agent_gaps)} subgoals need attention")
    if not file_resolutions:
        warnings.append("No file paths resolved. Consider running 'aur mem index .'")

    # Build decomposition summary for checkpoint
    from aurora_cli.planning.models import DecompositionSummary

    summary = DecompositionSummary(
        goal=goal,
        subgoals=subgoals,
        agents_assigned=agents_assigned,
        agent_gaps=agent_gaps,
        files_resolved=files_resolved,
        avg_confidence=avg_confidence,
        complexity=complexity,
        decomposition_source=decomposition_source,
        warnings=warnings,
    )

    # Display summary
    summary.display()

    # Prompt for confirmation (unless yes flag is set)
    if not (yes or non_interactive):
        from aurora_cli.planning.checkpoint import prompt_for_confirmation

        if not prompt_for_confirmation():
            return PlanResult(
                success=False,
                error="Plan creation cancelled by user.",
            )

    # Determine context sources
    context_sources = []
    if context_files:
        context_sources.append("context_files")
    if files_resolved > 0:
        context_sources.append("indexed_memory")

    # Convert file_resolutions to dict format for Plan model
    file_resolutions_dict: dict[str, list[dict[str, Any]]] = {}
    for subgoal_id, resolutions in file_resolutions.items():
        file_resolutions_dict[subgoal_id] = [
            {
                "path": res.path,
                "line_start": res.line_start,
                "line_end": res.line_end,
                "confidence": res.confidence,
            }
            for res in resolutions
        ]

    # Convert memory_context tuples to MemoryContext objects
    from aurora_cli.planning.models import MemoryContext

    memory_context_objects = [
        MemoryContext(file=file_path, relevance=score)
        for file_path, score in (memory_context or [])
    ]

    # Create plan
    plan = Plan(
        plan_id=plan_id,
        goal=goal,
        subgoals=subgoals,
        status=PlanStatus.ACTIVE,
        complexity=complexity,
        agent_gaps=[gap.ideal_agent for gap in agent_gaps],  # Ideal agents that are missing
        context_sources=context_sources,
        decomposition_source=decomposition_source,
        file_resolutions=file_resolutions_dict,
        memory_context=memory_context_objects,
    )

    # Write files
    plan_path = plans_dir / "active" / plan_id
    try:
        if goals_only:
            # aur goals: Only create directory and goals.json (per PRD-0026)
            # /plan skill will later add prd.md, tasks.md, specs/
            _write_goals_only(plan, plan_path, memory_context or [], agent_gaps=agent_gaps)
        else:
            # Full plan creation (for /plan skill or legacy mode)
            _write_plan_files(plan, plan_path)
    except Exception as e:
        return PlanResult(
            success=False,
            error=f"Failed to write plan files: {e}",
        )

    # Update manifest
    _update_manifest(plans_dir, plan_id, "active")

    # Build warnings
    warnings = []
    if agent_gaps:
        # Extract agent IDs from AgentGap objects for warning message
        gap_agents = [gap.ideal_agent for gap in agent_gaps]
        warnings.append(f"Agent gaps detected: {', '.join(gap_agents)}")
    if not context_sources:
        warnings.append("No context available. Consider running 'aur mem index .'")

    return PlanResult(
        success=True,
        plan=plan,
        plan_dir=plan_path,
        warnings=warnings if warnings else None,
    )


def _decompose_goal_soar(
    goal: str,
    context_files: list[Path] | None = None,
) -> list[Subgoal]:
    """Decompose goal into subgoals using SOAR-inspired heuristics.

    This is a rule-based decomposition that identifies common patterns
    in the goal text. For full LLM-powered decomposition, see the
    /aur:plan slash command.

    Args:
        goal: The high-level goal to decompose
        context_files: Optional context files for informed decomposition

    Returns:
        List of Subgoal objects
    """
    subgoals = []
    goal_lower = goal.lower()

    # Pattern matching for common goal types
    if any(kw in goal_lower for kw in ["auth", "login", "authentication", "oauth"]):
        subgoals = _decompose_auth_goal(goal)
    elif any(kw in goal_lower for kw in ["api", "endpoint", "rest"]):
        subgoals = _decompose_api_goal(goal)
    elif any(kw in goal_lower for kw in ["test", "testing"]):
        subgoals = _decompose_testing_goal(goal)
    elif any(kw in goal_lower for kw in ["refactor", "migrate", "upgrade"]):
        subgoals = _decompose_refactor_goal(goal)
    elif any(kw in goal_lower for kw in ["ui", "frontend", "component", "interface"]):
        subgoals = _decompose_ui_goal(goal)
    else:
        # Generic decomposition
        subgoals = _decompose_generic_goal(goal)

    return subgoals


def _decompose_auth_goal(goal: str) -> list[Subgoal]:
    """Decompose authentication-related goal."""
    return [
        Subgoal(
            id="sg-1",
            title="Design authentication architecture",
            description=f"Design the authentication system architecture for: {goal}",
            recommended_agent="@holistic-architect",
        ),
        Subgoal(
            id="sg-2",
            title="Implement authentication logic",
            description="Implement the core authentication flow including login, logout, session management",
            recommended_agent="@full-stack-dev",
            dependencies=["sg-1"],
        ),
        Subgoal(
            id="sg-3",
            title="Add security measures",
            description="Add security measures: rate limiting, token validation, secure storage",
            recommended_agent="@full-stack-dev",
            dependencies=["sg-2"],
        ),
        Subgoal(
            id="sg-4",
            title="Write authentication tests",
            description="Write comprehensive tests for authentication flows",
            recommended_agent="@qa-test-architect",
            dependencies=["sg-2", "sg-3"],
        ),
    ]


def _decompose_api_goal(goal: str) -> list[Subgoal]:
    """Decompose API-related goal."""
    return [
        Subgoal(
            id="sg-1",
            title="Design API contract",
            description=f"Design the API contract and endpoints for: {goal}",
            recommended_agent="@holistic-architect",
        ),
        Subgoal(
            id="sg-2",
            title="Implement API endpoints",
            description="Implement the API endpoints with proper validation and error handling",
            recommended_agent="@full-stack-dev",
            dependencies=["sg-1"],
        ),
        Subgoal(
            id="sg-3",
            title="Write API tests",
            description="Write API integration tests and documentation",
            recommended_agent="@qa-test-architect",
            dependencies=["sg-2"],
        ),
    ]


def _decompose_testing_goal(goal: str) -> list[Subgoal]:
    """Decompose testing-related goal."""
    return [
        Subgoal(
            id="sg-1",
            title="Analyze test requirements",
            description=f"Analyze and document test requirements for: {goal}",
            recommended_agent="@qa-test-architect",
        ),
        Subgoal(
            id="sg-2",
            title="Implement test infrastructure",
            description="Set up test infrastructure, fixtures, and utilities",
            recommended_agent="@full-stack-dev",
            dependencies=["sg-1"],
        ),
        Subgoal(
            id="sg-3",
            title="Write test cases",
            description="Implement the test cases according to test plan",
            recommended_agent="@qa-test-architect",
            dependencies=["sg-2"],
        ),
    ]


def _decompose_refactor_goal(goal: str) -> list[Subgoal]:
    """Decompose refactoring-related goal."""
    return [
        Subgoal(
            id="sg-1",
            title="Analyze current implementation",
            description=f"Analyze the current implementation and identify improvement areas for: {goal}",
            recommended_agent="@holistic-architect",
        ),
        Subgoal(
            id="sg-2",
            title="Create refactoring plan",
            description="Create detailed refactoring plan with incremental steps",
            recommended_agent="@holistic-architect",
            dependencies=["sg-1"],
        ),
        Subgoal(
            id="sg-3",
            title="Add tests for existing behavior",
            description="Add tests to capture existing behavior before refactoring",
            recommended_agent="@qa-test-architect",
            dependencies=["sg-1"],
        ),
        Subgoal(
            id="sg-4",
            title="Execute refactoring",
            description="Execute refactoring in incremental steps, maintaining test coverage",
            recommended_agent="@full-stack-dev",
            dependencies=["sg-2", "sg-3"],
        ),
        Subgoal(
            id="sg-5",
            title="Verify refactoring",
            description="Verify all tests pass and no regressions introduced",
            recommended_agent="@qa-test-architect",
            dependencies=["sg-4"],
        ),
    ]


def _decompose_ui_goal(goal: str) -> list[Subgoal]:
    """Decompose UI-related goal."""
    return [
        Subgoal(
            id="sg-1",
            title="Design UI components",
            description=f"Design UI/UX for: {goal}",
            recommended_agent="@ux-expert",
        ),
        Subgoal(
            id="sg-2",
            title="Implement UI components",
            description="Implement the UI components following the design",
            recommended_agent="@full-stack-dev",
            dependencies=["sg-1"],
        ),
        Subgoal(
            id="sg-3",
            title="Write UI tests",
            description="Write UI tests including visual regression tests",
            recommended_agent="@qa-test-architect",
            dependencies=["sg-2"],
        ),
    ]


def _decompose_generic_goal(goal: str) -> list[Subgoal]:
    """Decompose a generic goal."""
    return [
        Subgoal(
            id="sg-1",
            title="Analyze requirements",
            description=f"Analyze and document requirements for: {goal}",
            recommended_agent="@business-analyst",
        ),
        Subgoal(
            id="sg-2",
            title="Design solution",
            description="Design the solution architecture",
            recommended_agent="@holistic-architect",
            dependencies=["sg-1"],
        ),
        Subgoal(
            id="sg-3",
            title="Implement solution",
            description="Implement the solution according to design",
            recommended_agent="@full-stack-dev",
            dependencies=["sg-2"],
        ),
        Subgoal(
            id="sg-4",
            title="Test implementation",
            description="Write tests and verify implementation",
            recommended_agent="@qa-test-architect",
            dependencies=["sg-3"],
        ),
    ]


async def decompose_goal(
    goal: str,
    context_files: list[tuple[str, float]],
    llm_client: Any,  # CLIPipeLLMClient
) -> list[Subgoal]:
    """Decompose goal into subgoals using LLM.

    This function uses an LLM to intelligently decompose a high-level goal
    into 2-7 concrete, actionable subgoals with proper dependencies.

    Args:
        goal: High-level goal description (10-500 chars)
        context_files: Relevant files from memory search [(path, score), ...]
        llm_client: CLI-agnostic LLM client (CLIPipeLLMClient)

    Returns:
        List of Subgoal objects with dependencies

    Raises:
        ValueError: If LLM output is invalid or missing required fields
        KeyError: If JSON parsing fails

    Example:
        >>> from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient
        >>> client = CLIPipeLLMClient(tool="claude", model="sonnet")
        >>> context = [("src/auth.py", 0.85), ("tests/test_auth.py", 0.72)]
        >>> subgoals = await decompose_goal("Add OAuth2", context, client)
        >>> len(subgoals)
        4
    """
    # Build context section
    context_section = ""
    if context_files:
        context_section = "\n\nRelevant context files:\n"
        for path, score in context_files[:10]:  # Top 10 only
            context_section += f"- {path} (relevance: {score:.2f})\n"

    # Build decomposition prompt
    prompt = f"""Goal: {goal}
{context_section}

Decompose this goal into 2-7 concrete subgoals. Each subgoal should:
- Have a clear, actionable title (5-100 chars)
- Include detailed description (10-500 chars)
- Specify recommended agent in @agent-id format
- List dependencies on other subgoals (if any)

Available agents:
- @full-stack-dev: General development tasks
- @holistic-architect: System design and architecture
- @qa-test-architect: Testing and quality assurance
- @ux-expert: UI/UX design
- @business-analyst: Requirements analysis
- @product-manager: Product strategy
- @product-owner: Backlog management

Return ONLY a JSON array with this exact structure:
[
  {{
    "id": "sg-1",
    "title": "Short title",
    "description": "Detailed description of what this subgoal accomplishes",
    "recommended_agent": "@agent-id",
    "dependencies": []
  }},
  {{
    "id": "sg-2",
    "title": "Another title",
    "description": "Another description",
    "recommended_agent": "@agent-id",
    "dependencies": ["sg-1"]
  }}
]

Important:
- IDs must be sg-1, sg-2, sg-3, etc. (sequential)
- Dependencies must reference valid subgoal IDs
- No circular dependencies
- Agent IDs must start with @
- Return ONLY valid JSON, no markdown formatting"""

    # Call LLM via CLI pipe
    response = await llm_client.generate(prompt, phase_name="decompose")

    # Parse JSON response
    try:
        # Clean up response text (remove markdown if present)
        text = response.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Parse JSON
        import json

        subgoals_data = json.loads(text)

        if not isinstance(subgoals_data, list):
            raise ValueError("LLM response must be a JSON array")

        # Validate and construct Subgoal objects
        subgoals = []
        for sg_data in subgoals_data:
            # Validate required fields
            if "id" not in sg_data:
                raise KeyError("Subgoal missing required field: id")
            if "title" not in sg_data:
                raise KeyError("Subgoal missing required field: title")
            if "description" not in sg_data:
                raise KeyError("Subgoal missing required field: description")
            if "recommended_agent" not in sg_data:
                raise KeyError("Subgoal missing required field: recommended_agent")

            # Create Subgoal (Pydantic will validate)
            subgoal = Subgoal(
                id=sg_data["id"],
                title=sg_data["title"],
                description=sg_data["description"],
                recommended_agent=sg_data["recommended_agent"],
                dependencies=sg_data.get("dependencies", []),
            )
            subgoals.append(subgoal)

        # Validate we got 2-7 subgoals
        if len(subgoals) < 2:
            logger.warning("LLM returned only %d subgoal(s), expected 2-7", len(subgoals))
        if len(subgoals) > 7:
            logger.warning("LLM returned %d subgoals, expected 2-7. Using first 7.", len(subgoals))
            subgoals = subgoals[:7]

        return subgoals

    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON: %s", e)
        logger.debug("LLM response content: %s", response.content[:500])
        raise ValueError(f"Invalid JSON in LLM response: {e}")
    except KeyError as e:
        logger.error("LLM response missing required field: %s", e)
        raise
    except Exception as e:
        logger.error("Failed to decompose goal: %s", e)
        raise ValueError(f"Goal decomposition failed: {e}")
