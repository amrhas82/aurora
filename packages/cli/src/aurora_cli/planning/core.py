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
        Path to ~/.aurora/plans
    """
    return Path.home() / ".aurora" / "plans"


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
                error=VALIDATION_MESSAGES["PLANS_DIR_NO_WRITE_PERMISSION"].format(
                    path=str(parent)
                ),
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
            error=VALIDATION_MESSAGES["PLANS_DIR_NO_WRITE_PERMISSION"].format(
                path=str(parent)
            ),
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
            error=VALIDATION_MESSAGES["PLANS_DIR_NO_WRITE_PERMISSION"].format(
                path=str(target)
            ),
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
    logger.info("Rebuilt manifest with %d active and %d archived plans",
                len(manifest.active_plans), len(manifest.archived_plans))
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
        f"specs/{plan.plan_id}-planning.md": (plan_dir / "specs" / f"{plan.plan_id}-planning.md").exists(),
        f"specs/{plan.plan_id}-commands.md": (plan_dir / "specs" / f"{plan.plan_id}-commands.md").exists(),
        f"specs/{plan.plan_id}-validation.md": (plan_dir / "specs" / f"{plan.plan_id}-validation.md").exists(),
        f"specs/{plan.plan_id}-schemas.md": (plan_dir / "specs" / f"{plan.plan_id}-schemas.md").exists(),
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

    # Generate slug from goal
    slug = goal.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)  # Remove special chars
    slug = re.sub(r"\s+", "-", slug)  # Spaces to hyphens
    slug = re.sub(r"-+", "-", slug)  # Collapse multiple hyphens
    slug = slug.strip("-")[:30]  # Truncate

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
            logger.debug("Generated %d files using templates for plan %s", len(created_files), plan.plan_id)

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
                backup_dir = plan_dir.parent / f".backup-{plan.plan_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
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


def create_plan(
    goal: str,
    context_files: list[Path] | None = None,
    auto_decompose: bool = True,
    config: Config | None = None,
) -> PlanResult:
    """Create a new plan with SOAR-based goal decomposition.

    This is the main entry point for /aur:plan slash command.

    Args:
        goal: The high-level goal to decompose
        context_files: Optional list of context files for informed decomposition
        auto_decompose: Whether to use SOAR for automatic subgoal generation
        config: Optional CLI configuration

    Returns:
        PlanResult with plan details or error message

    Example:
        >>> result = create_plan("Implement OAuth2 authentication")
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

    # Generate subgoals
    if auto_decompose:
        subgoals = _decompose_goal_soar(goal, context_files)
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

    # Assess complexity
    complexity = _assess_complexity(goal, subgoals)

    # Check agent availability
    agent_gaps = []
    for sg in subgoals:
        if not _check_agent_availability(sg.recommended_agent):
            agent_gaps.append(sg.recommended_agent)
            sg.agent_exists = False
        else:
            sg.agent_exists = True

    # Determine context sources
    context_sources = []
    if context_files:
        context_sources.append("context_files")
    else:
        # Check if indexed memory exists
        try:
            from aurora_cli.memory import MemoryRetriever
            retriever = MemoryRetriever(config=config)
            if retriever.has_indexed_memory():
                context_sources.append("indexed_memory")
        except Exception:
            pass

    # Create plan
    plan = Plan(
        plan_id=plan_id,
        goal=goal,
        subgoals=subgoals,
        status=PlanStatus.ACTIVE,
        complexity=complexity,
        agent_gaps=agent_gaps,
        context_sources=context_sources,
    )

    # Write files
    plan_path = plans_dir / "active" / plan_id
    try:
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
        warnings.append(f"Agent gaps detected: {', '.join(agent_gaps)}")
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
