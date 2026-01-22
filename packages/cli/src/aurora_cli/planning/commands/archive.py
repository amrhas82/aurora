"""Archive command for Aurora planning system.

Ported from OpenSpec src/core/archive.ts
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from aurora_cli.planning.parsers.requirements import (
    RequirementBlock,
    extract_requirements_section,
    normalize_requirement_name,
    parse_modification_spec,
)
from aurora_cli.planning.validation.validator import Validator


# Import manifest functions for tracking
try:
    from aurora_cli.planning.core import _update_manifest

    MANIFEST_AVAILABLE = True
except ImportError:
    MANIFEST_AVAILABLE = False
    _update_manifest = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class SpecUpdate:
    """Represents a spec update operation."""

    source: Path
    target: Path
    exists: bool


@dataclass
class OperationCounts:
    """Counts of operations performed."""

    added: int = 0
    modified: int = 0
    removed: int = 0
    renamed: int = 0


class ArchiveCommand:
    """Command to archive a plan/change."""

    def execute(
        self,
        plan_name: str | None = None,
        target_path: str = ".",
        yes: bool = False,
        skip_specs: bool = False,
        no_validate: bool = False,
        validate: bool | None = None,
    ) -> None:
        """Execute the archive command.

        Args:
            plan_name: Name of the plan to archive (prompts if None)
            target_path: Target directory path (default: current directory)
            yes: Skip confirmation prompts
            skip_specs: Skip spec updates
            no_validate: Skip validation (alias for validate=False)
            validate: Explicit validation flag

        """
        target = Path(target_path)
        changes_dir = target / ".aurora" / "plans" / "active"
        archive_dir = target / ".aurora" / "plans" / "archive"
        main_specs_dir = target / ".aurora" / "capabilities"

        # Check if changes directory exists
        if not changes_dir.exists():
            raise RuntimeError("No Aurora plans directory found. Run 'aur plan init' first.")

        # Get plan name interactively if not provided
        if not plan_name:
            selected_plan = self._select_plan(changes_dir)
            if not selected_plan:
                print("No change selected. Aborting.")
                return
            plan_name = selected_plan

        change_dir = changes_dir / plan_name

        # Verify change exists
        if not change_dir.is_dir():
            raise RuntimeError(f"Change '{plan_name}' not found.")

        # Determine if validation should be skipped
        skip_validation = validate is False or no_validate is True

        # Validate specs and change before archiving
        if not skip_validation:
            validator = Validator()
            has_validation_errors = False

            # Validate proposal.md (non-blocking unless strict mode)
            change_file = change_dir / "proposal.md"
            if change_file.exists():
                change_report = validator.validate_plan(str(change_file))
                # Proposal validation is informative only
                if not change_report.valid:
                    print("\033[33m")  # Yellow
                    print("Proposal warnings in proposal.md (non-blocking):")
                    for issue in change_report.issues:
                        symbol = "⚠" if issue.level in ["ERROR", "WARNING"] else "ℹ"
                        print(f"  {symbol} {issue.message}")
                    print("\033[0m")  # Reset

            # Validate delta-formatted spec files
            change_specs_dir = change_dir / "specs"
            has_delta_specs = False
            if change_specs_dir.exists():
                for candidate in change_specs_dir.iterdir():
                    if candidate.is_dir():
                        candidate_path = candidate / "spec.md"
                        if candidate_path.exists():
                            content = candidate_path.read_text()
                            if (
                                "## ADDED Requirements" in content
                                or "## MODIFIED Requirements" in content
                                or "## REMOVED Requirements" in content
                                or "## RENAMED Requirements" in content
                            ):
                                has_delta_specs = True
                                break

            if has_delta_specs:
                delta_report = validator.validate_plan_modification_specs(str(change_dir))
                if not delta_report.valid:
                    has_validation_errors = True
                    print("\033[31m")  # Red
                    print("Validation errors in change delta specs:")
                    for issue in delta_report.issues:
                        if issue.level == "ERROR":
                            print(f"  ✗ {issue.message}")
                        elif issue.level == "WARNING":
                            print(f"\033[33m  ⚠ {issue.message}\033[31m")
                    print("\033[0m")  # Reset

            if has_validation_errors:
                print("\033[31m")
                print("Validation failed. Please fix the errors before archiving.")
                print(
                    "\033[33mTo skip validation (not recommended), use --no-validate flag.\033[0m",
                )
                return
        else:
            # Log warning when validation is skipped
            timestamp = datetime.now().isoformat()

            if not yes:
                response = input(
                    "\033[33m⚠️  WARNING: Skipping validation may archive invalid specs. Continue? (y/N) \033[0m",
                )
                if response.lower() != "y":
                    print("Archive cancelled.")
                    return
            else:
                print("\033[33m")
                print("⚠️  WARNING: Skipping validation may archive invalid specs.")
                print("\033[0m")

            print(f"\033[33m[{timestamp}] Validation skipped for change: {plan_name}")
            print(f"Affected files: {change_dir}\033[0m")

        # Show progress and check for incomplete tasks
        progress = self._get_task_progress(changes_dir, plan_name)
        status = self._format_task_status(progress)
        print(f"Task status: {status}")

        incomplete_tasks = max(progress["total"] - progress["completed"], 0)
        if incomplete_tasks > 0:
            if not yes:
                response = input(
                    f"Warning: {incomplete_tasks} incomplete task(s) found. Continue? (y/N) ",
                )
                if response.lower() != "y":
                    print("Archive cancelled.")
                    return
            else:
                print(
                    f"Warning: {incomplete_tasks} incomplete task(s) found. Continuing due to --yes flag.",
                )

        # Handle spec updates unless skipSpecs flag is set
        if skip_specs:
            print("Skipping spec updates (--skip-specs flag provided).")
        else:
            # Find specs to update
            spec_updates = self._find_spec_updates(change_dir, main_specs_dir)

            if spec_updates:
                print("\nSpecs to update:")
                for update in spec_updates:
                    status_str = "update" if update.exists else "create"
                    capability = update.target.parent.name
                    print(f"  {capability}: {status_str}")

                should_update_specs = True
                if not yes:
                    response = input("Proceed with spec updates? [Y/n]: ")
                    should_update_specs = response.lower() != "n"
                    if not should_update_specs:
                        print("Skipping spec updates. Proceeding with archive.")

                if should_update_specs:
                    # Prepare all updates first (validation pass, no writes)
                    prepared = []
                    try:
                        for update in spec_updates:
                            built = self._build_updated_spec(update, plan_name)
                            prepared.append(
                                {
                                    "update": update,
                                    "rebuilt": built["rebuilt"],
                                    "counts": built["counts"],
                                },
                            )
                    except Exception as err:
                        print(str(err))
                        print("Aborted. No files were changed.")
                        return

                    # All validations passed; pre-validate rebuilt full spec then write
                    totals = OperationCounts()
                    for p in prepared:
                        spec_name = p["update"].target.parent.name
                        if not skip_validation:
                            report = Validator().validate_capability_content(
                                spec_name,
                                p["rebuilt"],
                            )
                            if not report.valid:
                                print("\033[31m")
                                print(
                                    f"Validation errors in rebuilt spec for {spec_name} (will not write changes):",
                                )
                                for issue in report.issues:
                                    if issue.level == "ERROR":
                                        print(f"  ✗ {issue.message}")
                                    elif issue.level == "WARNING":
                                        print(f"\033[33m  ⚠ {issue.message}\033[31m")
                                print("\033[0m")
                                print("Aborted. No files were changed.")
                                return

                        self._write_updated_spec(p["update"], p["rebuilt"], p["counts"])
                        totals.added += p["counts"].added
                        totals.modified += p["counts"].modified
                        totals.removed += p["counts"].removed
                        totals.renamed += p["counts"].renamed

                    print(
                        f"Totals: + {totals.added}, ~ {totals.modified}, - {totals.removed}, → {totals.renamed}",
                    )
                    print("Specs updated successfully.")

        # Create archive directory with date prefix
        archive_name = f"{self._get_archive_date()}-{plan_name}"
        archive_path = archive_dir / archive_name

        # Check if archive already exists
        if archive_path.exists():
            raise RuntimeError(f"Archive '{archive_name}' already exists.")

        # Create archive directory if needed
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Move change to archive (atomic operation)
        change_dir.rename(archive_path)

        # Update manifest to track archived plan
        if MANIFEST_AVAILABLE and _update_manifest:
            try:
                plans_root = target / ".aurora" / "plans"
                _update_manifest(plans_root, plan_name, "archive", archive_name)
                logger.info(f"Updated manifest: {plan_name} -> archived as {archive_name}")
            except Exception as e:
                # Log error but don't fail the archive operation
                logger.warning(f"Failed to update manifest: {e}")
                print(f"\033[33mWarning: Could not update manifest: {e}\033[0m")

        print(f"Change '{plan_name}' archived as '{archive_name}'.")

    def _select_plan(self, changes_dir: Path) -> str | None:
        """Select a plan interactively."""
        # Get all directories in changes (excluding archive)
        entries = list(changes_dir.iterdir())
        change_dirs = sorted([e.name for e in entries if e.is_dir() and e.name != "archive"])

        if not change_dirs:
            print("No active changes found.")
            return None

        # Build choices with progress
        choices = []
        try:
            progress_list = []
            for plan_id in change_dirs:
                progress = self._get_task_progress(changes_dir, plan_id)
                status = self._format_task_status(progress)
                progress_list.append({"id": plan_id, "status": status})

            name_width = max(len(p["id"]) for p in progress_list)
            for p in progress_list:
                choice_name = f"{p['id'].ljust(name_width)}     {p['status']}"
                choices.append(choice_name)
        except Exception:
            # If anything fails, fall back to simple names
            choices = change_dirs

        # Display options
        print("Select a change to archive:")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")

        # Get user selection
        try:
            selection = input("Enter number: ")
            idx = int(selection) - 1
            if 0 <= idx < len(change_dirs):
                return change_dirs[idx]
        except (ValueError, KeyboardInterrupt):
            pass

        return None

    def _get_task_progress(self, changes_dir: Path, plan_id: str) -> dict[str, int]:
        """Get task progress for a plan."""
        tasks_path = changes_dir / plan_id / "tasks.md"
        if not tasks_path.exists():
            return {"total": 0, "completed": 0}

        content = tasks_path.read_text()
        lines = content.split("\n")

        total = 0
        completed = 0
        for line in lines:
            line = line.strip()
            if line.startswith("- ["):
                total += 1
                if line.startswith("- [x]") or line.startswith("- [X]"):
                    completed += 1

        return {"total": total, "completed": completed}

    def _format_task_status(self, progress: dict[str, int]) -> str:
        """Format task status string."""
        total = progress["total"]
        completed = progress["completed"]

        if total == 0:
            return "No tasks"

        percent = int((completed / total) * 100) if total > 0 else 0
        return f"{completed}/{total} ({percent}%)"

    def _find_spec_updates(self, change_dir: Path, main_specs_dir: Path) -> list[SpecUpdate]:
        """Find specs that need updating."""
        updates: list[SpecUpdate] = []
        change_specs_dir = change_dir / "specs"

        if not change_specs_dir.exists():
            return updates

        for entry in change_specs_dir.iterdir():
            if entry.is_dir():
                spec_file = entry / "spec.md"
                target_file = main_specs_dir / entry.name / "spec.md"

                if spec_file.exists():
                    exists = target_file.exists()
                    updates.append(SpecUpdate(source=spec_file, target=target_file, exists=exists))

        return updates

    def _build_updated_spec(self, update: SpecUpdate, plan_name: str) -> dict[str, Any]:
        """Build updated spec content."""
        # Read change spec content (delta-format expected)
        change_content = update.source.read_text()

        # Parse deltas from the change spec file
        plan = parse_modification_spec(change_content)
        spec_name = update.target.parent.name

        # Pre-validate duplicates within sections
        added_names = set()
        for add in plan.added:
            name = normalize_requirement_name(add.name)
            if name in added_names:
                raise RuntimeError(
                    f"{spec_name} validation failed - duplicate requirement in ADDED for header '### Requirement: {add.name}'",
                )
            added_names.add(name)

        modified_names = set()
        for mod in plan.modified:
            name = normalize_requirement_name(mod.name)
            if name in modified_names:
                raise RuntimeError(
                    f"{spec_name} validation failed - duplicate requirement in MODIFIED for header '### Requirement: {mod.name}'",
                )
            modified_names.add(name)

        removed_names_set = set()
        for rem in plan.removed:
            name = normalize_requirement_name(rem)
            if name in removed_names_set:
                raise RuntimeError(
                    f"{spec_name} validation failed - duplicate requirement in REMOVED for header '### Requirement: {rem}'",
                )
            removed_names_set.add(name)

        renamed_from_set = set()
        renamed_to_set = set()
        for rename in plan.renamed:
            from_norm = normalize_requirement_name(rename["from"])
            to_norm = normalize_requirement_name(rename["to"])
            if from_norm in renamed_from_set:
                raise RuntimeError(
                    f"{spec_name} validation failed - duplicate FROM in RENAMED for header '### Requirement: {rename['from']}'",
                )
            if to_norm in renamed_to_set:
                raise RuntimeError(
                    f"{spec_name} validation failed - duplicate TO in RENAMED for header '### Requirement: {rename['to']}'",
                )
            renamed_from_set.add(from_norm)
            renamed_to_set.add(to_norm)

        # Pre-validate cross-section conflicts
        conflicts = []
        for n in modified_names:
            if n in removed_names_set:
                conflicts.append({"name": n, "a": "MODIFIED", "b": "REMOVED"})
            if n in added_names:
                conflicts.append({"name": n, "a": "MODIFIED", "b": "ADDED"})
        for n in added_names:
            if n in removed_names_set:
                conflicts.append({"name": n, "a": "ADDED", "b": "REMOVED"})

        # Renamed interplay: MODIFIED must reference the NEW header, not FROM
        for rename in plan.renamed:
            from_norm = normalize_requirement_name(rename["from"])
            to_norm = normalize_requirement_name(rename["to"])
            if from_norm in modified_names:
                raise RuntimeError(
                    f"{spec_name} validation failed - when a rename exists, MODIFIED must reference the NEW header '### Requirement: {rename['to']}'",
                )
            # Detect ADDED colliding with a RENAMED TO
            if to_norm in added_names:
                raise RuntimeError(
                    f"{spec_name} validation failed - RENAMED TO header collides with ADDED for '### Requirement: {rename['to']}'",
                )

        if conflicts:
            c = conflicts[0]
            raise RuntimeError(
                f"{spec_name} validation failed - requirement present in multiple sections ({c['a']} and {c['b']}) for header '### Requirement: {c['name']}'",
            )

        has_any_delta = (
            len(plan.added) + len(plan.modified) + len(plan.removed) + len(plan.renamed)
        ) > 0
        if not has_any_delta:
            raise RuntimeError(
                f"Delta parsing found no operations for {update.source.parent.name}. "
                "Provide ADDED/MODIFIED/REMOVED/RENAMED sections in change spec.",
            )

        # Load or create base target content
        is_new_spec = False
        try:
            target_content = update.target.read_text()
        except FileNotFoundError:
            # Target spec does not exist
            if plan.modified or plan.renamed:
                raise RuntimeError(
                    f"{spec_name}: target spec does not exist; only ADDED requirements are allowed for new specs. "
                    "MODIFIED and RENAMED operations require an existing spec.",
                )
            # Warn about REMOVED requirements being ignored for new specs
            if plan.removed:
                print(
                    f"\033[33m⚠️  Warning: {spec_name} - {len(plan.removed)} REMOVED requirement(s) ignored for new spec (nothing to remove).\033[0m",
                )
            is_new_spec = True
            target_content = self._build_spec_skeleton(spec_name, plan_name)

        # Extract requirements section and build name->block map
        parts = extract_requirements_section(target_content)
        name_to_block = {}
        for block in parts.body_blocks:
            name_to_block[normalize_requirement_name(block.name)] = block

        # Apply operations in order: RENAMED → REMOVED → MODIFIED → ADDED
        # RENAMED
        for rename in plan.renamed:
            from_key = normalize_requirement_name(rename["from"])
            to_key = normalize_requirement_name(rename["to"])
            if from_key not in name_to_block:
                raise RuntimeError(
                    f"{spec_name} RENAMED failed for header '### Requirement: {rename['from']}' - source not found",
                )
            if to_key in name_to_block:
                raise RuntimeError(
                    f"{spec_name} RENAMED failed for header '### Requirement: {rename['to']}' - target already exists",
                )
            block = name_to_block[from_key]
            new_header = f"### Requirement: {to_key}"
            raw_lines = block.raw.split("\n")
            raw_lines[0] = new_header
            renamed_block = RequirementBlock(
                header_line=new_header,
                name=to_key,
                raw="\n".join(raw_lines),
            )
            del name_to_block[from_key]
            name_to_block[to_key] = renamed_block

        # REMOVED
        for name in plan.removed:
            key = normalize_requirement_name(name)
            if key not in name_to_block:
                if not is_new_spec:
                    raise RuntimeError(
                        f"{spec_name} REMOVED failed for header '### Requirement: {name}' - not found",
                    )
                continue
            del name_to_block[key]

        # MODIFIED
        for mod in plan.modified:
            key = normalize_requirement_name(mod.name)
            if key not in name_to_block:
                raise RuntimeError(
                    f"{spec_name} MODIFIED failed for header '### Requirement: {mod.name}' - not found",
                )
            # Replace block with provided raw
            mod_header_match = mod.raw.split("\n")[0]
            if not mod_header_match.startswith("### Requirement:"):
                raise RuntimeError(
                    f"{spec_name} MODIFIED failed for header '### Requirement: {mod.name}' - header mismatch in content",
                )
            name_to_block[key] = mod

        # ADDED
        for add in plan.added:
            key = normalize_requirement_name(add.name)
            if key in name_to_block:
                raise RuntimeError(
                    f"{spec_name} ADDED failed for header '### Requirement: {add.name}' - already exists",
                )
            name_to_block[key] = add

        # Recompose requirements section preserving original ordering
        kept_order = []
        seen = set()
        for block in parts.body_blocks:
            key = normalize_requirement_name(block.name)
            replacement = name_to_block.get(key)
            if replacement:
                kept_order.append(replacement)
                seen.add(key)

        # Append any newly added that were not in original order
        for key, block in name_to_block.items():
            if key not in seen:
                kept_order.append(block)

        # Build requirements body
        req_parts = []
        if parts.preamble and parts.preamble.strip():
            req_parts.append(parts.preamble.rstrip())
        req_parts.extend([b.raw for b in kept_order])
        req_body = "\n\n".join(req_parts).rstrip()

        # Rebuild full content
        rebuild_parts = []
        if parts.before.strip():
            rebuild_parts.append(parts.before.rstrip())
        rebuild_parts.append(parts.header_line)
        rebuild_parts.append(req_body)
        if parts.after:
            rebuild_parts.append(parts.after)

        rebuilt = "\n".join(rebuild_parts)
        # Clean up excessive newlines
        while "\n\n\n" in rebuilt:
            rebuilt = rebuilt.replace("\n\n\n", "\n\n")

        counts = OperationCounts(
            added=len(plan.added),
            modified=len(plan.modified),
            removed=len(plan.removed),
            renamed=len(plan.renamed),
        )

        return {"rebuilt": rebuilt, "counts": counts}

    def _write_updated_spec(
        self,
        update: SpecUpdate,
        rebuilt: str,
        counts: OperationCounts,
    ) -> None:
        """Write updated spec to disk."""
        # Create target directory if needed
        update.target.parent.mkdir(parents=True, exist_ok=True)
        update.target.write_text(rebuilt)

        spec_name = update.target.parent.name
        print(f"Applying changes to .aurora/capabilities/{spec_name}/spec.md:")
        if counts.added:
            print(f"  + {counts.added} added")
        if counts.modified:
            print(f"  ~ {counts.modified} modified")
        if counts.removed:
            print(f"  - {counts.removed} removed")
        if counts.renamed:
            print(f"  → {counts.renamed} renamed")

    def _build_spec_skeleton(self, spec_folder_name: str, plan_name: str) -> str:
        """Build a capability spec skeleton for new specs."""
        return f"""# {spec_folder_name} Capability Specification

## Purpose
TBD - created by archiving plan {plan_name}. Update Purpose after archive.

## Requirements
"""

    def _get_archive_date(self) -> str:
        """Get archive date in YYYY-MM-DD format."""
        return datetime.now().strftime("%Y-%m-%d")
