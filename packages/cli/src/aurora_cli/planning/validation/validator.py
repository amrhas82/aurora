"""Validator for capabilities and plans in Aurora Planning System.

This is the CRITICAL validation component that enforces all business rules for:
- Capability (system capability specification) markdown files
- Plan (proposal for changes) markdown files
- Modification spec files (ADDED/MODIFIED/REMOVED/RENAMED requirements)

The validator implements a comprehensive rule set including:
- Schema-level validation (required sections, data types)
- Business rules (SHALL/MUST keywords, scenario counts, length limits)
- Cross-section conflict detection (no requirement in both ADDED and REMOVED)
- Duplicate detection within sections
- RENAMED collision detection with ADDED/MODIFIED sections

Validation is performed in two phases:
1. Schema validation: Structural requirements (sections, fields)
2. Business rules: Domain-specific constraints and relationships
"""

from __future__ import annotations

import re
from pathlib import Path

from aurora_cli.planning.parsers.markdown import MarkdownParser, ParsedCapability, ParsedPlan
from aurora_cli.planning.parsers.plan import PlanParser
from aurora_cli.planning.parsers.requirements import (
    normalize_requirement_name,
    parse_modification_spec,
)
from aurora_cli.planning.validation.constants import (
    MAX_REQUIREMENT_TEXT_LENGTH,
    MIN_MODIFICATION_DESCRIPTION_LENGTH,
    MIN_PURPOSE_LENGTH,
    VALIDATION_MESSAGES,
)
from aurora_cli.planning.validation.types import ValidationIssue, ValidationLevel, ValidationReport


class Validator:
    """Validator for capability and plan documents.

    Ported from: Validator class in TypeScript
    """

    def __init__(self, strict_mode: bool = False) -> None:
        """Initialize validator.

        Args:
            strict_mode: If True, warnings cause validation to fail

        """
        self._strict_mode = strict_mode

    def validate_capability(self, file_path: str) -> ValidationReport:
        """Validate a capability (spec) file.

        Args:
            file_path: Path to the capability markdown file

        Returns:
            ValidationReport with issues and validity status

        """
        issues: list[ValidationIssue] = []
        capability_name = self._extract_name_from_path(file_path)

        try:
            content = Path(file_path).read_text()
            parser = MarkdownParser(content)
            capability = parser.parse_capability(capability_name)

            # Apply schema-like validation
            schema_issues = self._validate_capability_schema(capability)
            issues.extend(schema_issues)

            # Apply additional rules
            rule_issues = self._apply_capability_rules(capability, content)
            issues.extend(rule_issues)

        except ValueError as e:
            # Parser errors (missing sections, etc.)
            enriched = self._enrich_top_level_error(capability_name, str(e))
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="file",
                    message=enriched,
                ),
            )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="file",
                    message=str(e),
                ),
            )

        return self._create_report(issues)

    def validate_capability_content(self, capability_name: str, content: str) -> ValidationReport:
        """Validate capability content from a string.

        Used for pre-write validation of rebuilt capabilities.

        Args:
            capability_name: Name of the capability
            content: Markdown content

        Returns:
            ValidationReport with issues and validity status

        """
        issues: list[ValidationIssue] = []

        try:
            parser = MarkdownParser(content)
            capability = parser.parse_capability(capability_name)

            schema_issues = self._validate_capability_schema(capability)
            issues.extend(schema_issues)

            rule_issues = self._apply_capability_rules(capability, content)
            issues.extend(rule_issues)

        except ValueError as e:
            enriched = self._enrich_top_level_error(capability_name, str(e))
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="file",
                    message=enriched,
                ),
            )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="file",
                    message=str(e),
                ),
            )

        return self._create_report(issues)

    def validate_plan(self, file_path: str) -> ValidationReport:
        """Validate a plan (change) file.

        Args:
            file_path: Path to the plan markdown file

        Returns:
            ValidationReport with issues and validity status

        """
        issues: list[ValidationIssue] = []
        plan_name = self._extract_name_from_path(file_path)

        try:
            content = Path(file_path).read_text()
            plan_dir = str(Path(file_path).parent)
            parser = PlanParser(content, plan_dir)
            plan = parser.parse_plan_with_modifications(plan_name)

            # Apply schema-like validation
            schema_issues = self._validate_plan_schema(plan)
            issues.extend(schema_issues)

            # Apply additional rules
            rule_issues = self._apply_plan_rules(plan, content)
            issues.extend(rule_issues)

        except ValueError as e:
            enriched = self._enrich_top_level_error(plan_name, str(e))
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="file",
                    message=enriched,
                ),
            )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="file",
                    message=str(e),
                ),
            )

        return self._create_report(issues)

    def validate_plan_modification_specs(self, plan_dir: str) -> ValidationReport:
        """Validate delta-formatted spec files under a plan directory.

        Enforces:
        - At least one modification across all files
        - ADDED/MODIFIED: each requirement has SHALL/MUST and at least one scenario
        - REMOVED: names only; no scenario/description required
        - RENAMED: pairs well-formed
        - No duplicates within sections; no cross-section conflicts per spec

        Args:
            plan_dir: Path to plan directory containing specs/

        Returns:
            ValidationReport with issues and validity status

        """
        issues: list[ValidationIssue] = []
        specs_dir = Path(plan_dir) / "specs"
        total_modifications = 0
        missing_header_specs: list[str] = []
        empty_section_specs: list[dict[str, str | list[str]]] = []

        try:
            if not specs_dir.exists():
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        path="file",
                        message=self._enrich_top_level_error(
                            "plan",
                            VALIDATION_MESSAGES.PLAN_NO_MODIFICATIONS,
                        ),
                    ),
                )
                return self._create_report(issues)

            for entry in specs_dir.iterdir():
                if not entry.is_dir():
                    continue

                spec_name = entry.name
                spec_file = entry / "spec.md"

                if not spec_file.exists():
                    continue

                try:
                    content = spec_file.read_text()
                except OSError:
                    continue

                plan = parse_modification_spec(content)
                entry_path = f"{spec_name}/spec.md"

                # Check for section presence
                section_names: list[str] = []
                if plan.section_presence["added"]:
                    section_names.append("## ADDED Requirements")
                if plan.section_presence["modified"]:
                    section_names.append("## MODIFIED Requirements")
                if plan.section_presence["removed"]:
                    section_names.append("## REMOVED Requirements")
                if plan.section_presence["renamed"]:
                    section_names.append("## RENAMED Requirements")

                has_sections = len(section_names) > 0
                has_entries = (
                    len(plan.added) + len(plan.modified) + len(plan.removed) + len(plan.renamed)
                ) > 0

                if not has_entries:
                    if has_sections:
                        empty_section_specs.append({"path": entry_path, "sections": section_names})
                    else:
                        missing_header_specs.append(entry_path)

                # Track names for duplicate/conflict detection
                added_names: set[str] = set()
                modified_names: set[str] = set()
                removed_names: set[str] = set()
                renamed_from: set[str] = set()
                renamed_to: set[str] = set()

                # Validate ADDED
                for block in plan.added:
                    key = normalize_requirement_name(block.name)
                    total_modifications += 1

                    if key in added_names:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'Duplicate requirement in ADDED: "{block.name}"',
                            ),
                        )
                    else:
                        added_names.add(key)

                    req_text = self._extract_requirement_text(block.raw)
                    if not req_text:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'ADDED "{block.name}" is missing requirement text',
                            ),
                        )
                    elif not self._contains_shall_or_must(req_text):
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'ADDED "{block.name}" must contain SHALL or MUST',
                            ),
                        )

                    scenario_count = self._count_scenarios(block.raw)
                    if scenario_count < 1:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'ADDED "{block.name}" must include at least one scenario',
                            ),
                        )

                # Validate MODIFIED
                for block in plan.modified:
                    key = normalize_requirement_name(block.name)
                    total_modifications += 1

                    if key in modified_names:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'Duplicate requirement in MODIFIED: "{block.name}"',
                            ),
                        )
                    else:
                        modified_names.add(key)

                    req_text = self._extract_requirement_text(block.raw)
                    if not req_text:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'MODIFIED "{block.name}" is missing requirement text',
                            ),
                        )
                    elif not self._contains_shall_or_must(req_text):
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'MODIFIED "{block.name}" must contain SHALL or MUST',
                            ),
                        )

                    scenario_count = self._count_scenarios(block.raw)
                    if scenario_count < 1:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'MODIFIED "{block.name}" must include at least one scenario',
                            ),
                        )

                # Validate REMOVED
                for name in plan.removed:
                    key = normalize_requirement_name(name)
                    total_modifications += 1

                    if key in removed_names:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'Duplicate requirement in REMOVED: "{name}"',
                            ),
                        )
                    else:
                        removed_names.add(key)

                # Validate RENAMED
                for rename in plan.renamed:
                    from_key = normalize_requirement_name(rename["from"])
                    to_key = normalize_requirement_name(rename["to"])
                    total_modifications += 1

                    if from_key in renamed_from:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'Duplicate FROM in RENAMED: "{rename["from"]}"',
                            ),
                        )
                    else:
                        renamed_from.add(from_key)

                    if to_key in renamed_to:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'Duplicate TO in RENAMED: "{rename["to"]}"',
                            ),
                        )
                    else:
                        renamed_to.add(to_key)

                # Cross-section conflicts
                for n in modified_names:
                    if n in removed_names:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'Requirement present in both MODIFIED and REMOVED: "{n}"',
                            ),
                        )
                    if n in added_names:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'Requirement present in both MODIFIED and ADDED: "{n}"',
                            ),
                        )

                for n in added_names:
                    if n in removed_names:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'Requirement present in both ADDED and REMOVED: "{n}"',
                            ),
                        )

                for rename in plan.renamed:
                    from_key = normalize_requirement_name(rename["from"])
                    to_key = normalize_requirement_name(rename["to"])

                    if from_key in modified_names:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'MODIFIED references old name from RENAMED. Use new header for "{rename["to"]}"',
                            ),
                        )
                    if to_key in added_names:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                path=entry_path,
                                message=f'RENAMED TO collides with ADDED for "{rename["to"]}"',
                            ),
                        )

        except OSError:
            # If specs dir can't be read, treat as no modifications
            pass

        # Report empty sections
        for spec in empty_section_specs:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path=str(spec["path"]),
                    message=(
                        f"Delta sections {self._format_section_list(list(spec['sections']))} were found, "
                        f"but no requirement entries parsed. Ensure each section includes at least one "
                        f'"### Requirement:" block (REMOVED may use bullet list syntax).'
                    ),
                ),
            )

        # Report missing headers
        for path in missing_header_specs:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path=path,
                    message=(
                        'No delta sections found. Add headers such as "## ADDED Requirements" '
                        "or move non-delta notes outside specs/."
                    ),
                ),
            )

        # Check for at least one modification
        if total_modifications == 0:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="file",
                    message=self._enrich_top_level_error(
                        "plan",
                        VALIDATION_MESSAGES.PLAN_NO_MODIFICATIONS,
                    ),
                ),
            )

        return self._create_report(issues)

    def _validate_capability_schema(self, capability: ParsedCapability) -> list[ValidationIssue]:
        """Validate capability against schema rules.

        Validates that parsed capability meets schema requirements without
        importing Pydantic models (which would re-validate).

        Args:
            capability: Parsed capability to validate

        Returns:
            List of validation issues

        """
        issues: list[ValidationIssue] = []

        # Name validation
        if not capability.name or not capability.name.strip():
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="name",
                    message=VALIDATION_MESSAGES.CAPABILITY_NAME_EMPTY,
                ),
            )

        # Overview validation
        if not capability.overview or not capability.overview.strip():
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="overview",
                    message=VALIDATION_MESSAGES.CAPABILITY_PURPOSE_EMPTY,
                ),
            )

        # Requirements validation
        if not capability.requirements:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="requirements",
                    message=VALIDATION_MESSAGES.CAPABILITY_NO_REQUIREMENTS,
                ),
            )
        else:
            for i, req in enumerate(capability.requirements):
                # Check SHALL/MUST
                if "SHALL" not in req.text and "MUST" not in req.text:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            path=f"requirements[{i}].text",
                            message=VALIDATION_MESSAGES.REQUIREMENT_NO_SHALL,
                        ),
                    )

                # Check scenarios
                if not req.scenarios:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            path=f"requirements[{i}].scenarios",
                            message=VALIDATION_MESSAGES.REQUIREMENT_NO_SCENARIOS,
                        ),
                    )

        return issues

    def _validate_plan_schema(self, plan: ParsedPlan) -> list[ValidationIssue]:
        """Validate plan against schema rules.

        Args:
            plan: Parsed plan to validate

        Returns:
            List of validation issues

        """
        issues: list[ValidationIssue] = []

        # Name validation
        if not plan.name or not plan.name.strip():
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="name",
                    message=VALIDATION_MESSAGES.PLAN_NAME_EMPTY,
                ),
            )

        # Why validation (length check)
        from aurora_cli.planning.validation.constants import (
            MAX_WHY_SECTION_LENGTH,
            MIN_WHY_SECTION_LENGTH,
        )

        if len(plan.why) < MIN_WHY_SECTION_LENGTH:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="why",
                    message=VALIDATION_MESSAGES.PLAN_WHY_TOO_SHORT,
                ),
            )
        elif len(plan.why) > MAX_WHY_SECTION_LENGTH:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="why",
                    message=VALIDATION_MESSAGES.PLAN_WHY_TOO_LONG,
                ),
            )

        # What changes validation
        if not plan.what_changes or not plan.what_changes.strip():
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    path="what_changes",
                    message=VALIDATION_MESSAGES.PLAN_WHAT_EMPTY,
                ),
            )

        return issues

    def _apply_capability_rules(
        self,
        capability: ParsedCapability,
        _content: str,
    ) -> list[ValidationIssue]:
        """Apply additional validation rules to capability.

        Args:
            capability: Parsed capability
            content: Original markdown content

        Returns:
            List of validation issues (mostly warnings)

        """
        issues: list[ValidationIssue] = []

        # Warn about brief purpose
        if len(capability.overview) < MIN_PURPOSE_LENGTH:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.WARNING,
                    path="overview",
                    message=VALIDATION_MESSAGES.PURPOSE_TOO_BRIEF,
                ),
            )

        # Check requirements
        for i, req in enumerate(capability.requirements):
            # Info about long requirements
            if len(req.text) > MAX_REQUIREMENT_TEXT_LENGTH:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.INFO,
                        path=f"requirements[{i}]",
                        message=VALIDATION_MESSAGES.REQUIREMENT_TOO_LONG,
                    ),
                )

            # Warn about missing scenarios
            if not req.scenarios:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.WARNING,
                        path=f"requirements[{i}].scenarios",
                        message=(
                            f"{VALIDATION_MESSAGES.REQUIREMENT_NO_SCENARIOS}. "
                            f"{VALIDATION_MESSAGES.GUIDE_SCENARIO_FORMAT}"
                        ),
                    ),
                )

        return issues

    def _apply_plan_rules(self, plan: ParsedPlan, _content: str) -> list[ValidationIssue]:
        """Apply additional validation rules to plan.

        Args:
            plan: Parsed plan
            content: Original markdown content

        Returns:
            List of validation issues (mostly warnings)

        """
        issues: list[ValidationIssue] = []

        for i, mod in enumerate(plan.modifications):
            # Check modification description length
            if not mod.description or len(mod.description) < MIN_MODIFICATION_DESCRIPTION_LENGTH:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.WARNING,
                        path=f"modifications[{i}].description",
                        message=VALIDATION_MESSAGES.MODIFICATION_DESCRIPTION_TOO_BRIEF,
                    ),
                )

            # Check for requirements on ADDED/MODIFIED
            from aurora_cli.planning.schemas.plan import ModificationOperation

            if mod.operation in (ModificationOperation.ADDED, ModificationOperation.MODIFIED):
                if not mod.requirements or len(mod.requirements) == 0:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.WARNING,
                            path=f"modifications[{i}].requirements",
                            message=(
                                f"{mod.operation.value} "
                                f"{VALIDATION_MESSAGES.MODIFICATION_MISSING_REQUIREMENTS}"
                            ),
                        ),
                    )

        return issues

    def _enrich_top_level_error(self, _item_id: str, base_message: str) -> str:
        """Enrich error message with guidance.

        Args:
            item_id: Item identifier (capability/plan name)
            base_message: Base error message

        Returns:
            Enriched error message

        """
        msg = base_message.strip()

        if msg == VALIDATION_MESSAGES.PLAN_NO_MODIFICATIONS:
            return f"{msg}. {VALIDATION_MESSAGES.GUIDE_NO_MODIFICATIONS}"

        if (
            "Capability must have a Purpose section" in msg
            or "Capability must have a Requirements section" in msg
        ):
            return f"{msg}. {VALIDATION_MESSAGES.GUIDE_MISSING_CAPABILITY_SECTIONS}"

        if "Plan must have a Why section" in msg or "Plan must have a What Changes section" in msg:
            return f"{msg}. {VALIDATION_MESSAGES.GUIDE_MISSING_PLAN_SECTIONS}"

        return msg

    def _extract_name_from_path(self, file_path: str) -> str:
        """Extract item name from file path.

        Looks for directory name after 'specs', 'capabilities', 'changes', or 'plans'.

        Args:
            file_path: File path

        Returns:
            Extracted name

        """
        path = Path(file_path)
        parts = path.parts

        # Look for known directory markers
        for i, part in enumerate(parts):
            if part in ("specs", "capabilities", "changes", "plans"):
                if i + 1 < len(parts):
                    return parts[i + 1]

        # Fallback to filename without extension
        return path.stem

    def _create_report(self, issues: list[ValidationIssue]) -> ValidationReport:
        """Create validation report from issues.

        Args:
            issues: List of validation issues

        Returns:
            ValidationReport

        """
        errors = sum(1 for i in issues if i.level == ValidationLevel.ERROR)
        warnings = sum(1 for i in issues if i.level == ValidationLevel.WARNING)

        if self._strict_mode:
            valid = errors == 0 and warnings == 0
        else:
            valid = errors == 0

        return ValidationReport(valid=valid, issues=issues)

    def _extract_requirement_text(self, block_raw: str) -> str | None:
        """Extract requirement text from block, skipping metadata.

        Args:
            block_raw: Raw requirement block content

        Returns:
            Requirement text or None

        """
        lines = block_raw.split("\n")
        # Skip header line (index 0)
        for i in range(1, len(lines)):
            line = lines[i]

            # Stop at scenario headers
            if re.match(r"^####\s+", line):
                break

            trimmed = line.strip()

            # Skip blank lines
            if not trimmed:
                continue

            # Skip metadata lines (like **ID**: value)
            if re.match(r"^\*\*[^*]+\*\*:", trimmed):
                continue

            # Found first non-metadata, non-blank line
            return trimmed

        return None

    def _contains_shall_or_must(self, text: str) -> bool:
        """Check if text contains SHALL or MUST keyword.

        Args:
            text: Text to check

        Returns:
            True if contains SHALL or MUST

        """
        return bool(re.search(r"\b(SHALL|MUST)\b", text))

    def _count_scenarios(self, block_raw: str) -> int:
        """Count scenario headers in block.

        Args:
            block_raw: Raw block content

        Returns:
            Number of scenarios

        """
        matches = re.findall(r"^####\s+", block_raw, re.MULTILINE)
        return len(matches)

    def _format_section_list(self, sections: list[str]) -> str:
        """Format section list for display.

        Args:
            sections: List of section names

        Returns:
            Formatted string

        """
        if not sections:
            return ""
        if len(sections) == 1:
            return sections[0]

        head = sections[:-1]
        last = sections[-1]
        return f"{', '.join(head)} and {last}"

    def is_valid(self, report: ValidationReport) -> bool:
        """Check if a validation report indicates validity.

        Args:
            report: Validation report

        Returns:
            True if valid

        """
        return report.valid
