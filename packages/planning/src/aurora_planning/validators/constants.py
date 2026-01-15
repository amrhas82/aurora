"""Validation threshold constants and messages.

Ported from: src/core/validation/constants.ts
Terminology: openspec→aurora, change→plan, spec→capability, delta→modification
"""

# Minimum character lengths
MIN_WHY_SECTION_LENGTH = 50
MIN_PURPOSE_LENGTH = 50

# Maximum character/item limits
MAX_WHY_SECTION_LENGTH = 1000
MAX_REQUIREMENT_TEXT_LENGTH = 500
MAX_MODIFICATIONS_PER_PLAN = 10  # Was MAX_DELTAS_PER_CHANGE
MIN_MODIFICATION_DESCRIPTION_LENGTH = 20


class VALIDATION_MESSAGES:
    """Validation messages - class for namespace, matches TypeScript const object."""

    # Required content
    SCENARIO_EMPTY = "Scenario text cannot be empty"
    REQUIREMENT_EMPTY = "Requirement text cannot be empty"
    REQUIREMENT_NO_SHALL = "Requirement must contain SHALL or MUST keyword"
    REQUIREMENT_NO_SCENARIOS = "Requirement must have at least one scenario"
    CAPABILITY_NAME_EMPTY = "Capability name cannot be empty"  # Was SPEC_NAME_EMPTY
    CAPABILITY_PURPOSE_EMPTY = "Purpose section cannot be empty"  # Was SPEC_PURPOSE_EMPTY
    CAPABILITY_NO_REQUIREMENTS = (
        "Capability must have at least one requirement"  # Was SPEC_NO_REQUIREMENTS
    )
    PLAN_NAME_EMPTY = "Plan name cannot be empty"  # Was CHANGE_NAME_EMPTY
    PLAN_WHY_TOO_SHORT = f"Why section must be at least {MIN_WHY_SECTION_LENGTH} characters"
    PLAN_WHY_TOO_LONG = f"Why section should not exceed {MAX_WHY_SECTION_LENGTH} characters"
    PLAN_WHAT_EMPTY = "What Changes section cannot be empty"  # Was CHANGE_WHAT_EMPTY
    PLAN_NO_MODIFICATIONS = "Plan must have at least one modification"  # Was CHANGE_NO_DELTAS
    PLAN_TOO_MANY_MODIFICATIONS = (
        f"Consider splitting plans with more than {MAX_MODIFICATIONS_PER_PLAN} modifications"
    )
    MODIFICATION_CAPABILITY_EMPTY = "Capability name cannot be empty"  # Was DELTA_SPEC_EMPTY
    MODIFICATION_DESCRIPTION_EMPTY = "Modification description cannot be empty"

    # Warnings
    PURPOSE_TOO_BRIEF = f"Purpose section is too brief (less than {MIN_PURPOSE_LENGTH} characters)"
    REQUIREMENT_TOO_LONG = (
        f"Requirement text is very long (>{MAX_REQUIREMENT_TEXT_LENGTH} characters). "
        "Consider breaking it down."
    )
    MODIFICATION_DESCRIPTION_TOO_BRIEF = "Modification description is too brief"
    MODIFICATION_MISSING_REQUIREMENTS = "Modification should include requirements"

    # Guidance snippets (appended to primary messages for remediation)
    GUIDE_NO_MODIFICATIONS = (
        "No modifications found. Ensure your plan has a specs/ directory with capability "
        "folders (e.g. specs/http-server/spec.md) containing .md files that use modification "
        "headers (## ADDED/MODIFIED/REMOVED/RENAMED Requirements) and that each requirement "
        'includes at least one "#### Scenario:" block. Tip: run "aurora plan show <plan-id> '
        '--json --modifications-only" to inspect parsed modifications.'
    )
    GUIDE_MISSING_CAPABILITY_SECTIONS = (
        'Missing required sections. Expected headers: "## Purpose" and "## Requirements". '
        "Example:\n## Purpose\n[brief purpose]\n\n## Requirements\n### Requirement: Clear "
        "requirement statement\nUsers SHALL ...\n\n#### Scenario: Descriptive name\n"
        "- **WHEN** ...\n- **THEN** ..."
    )
    GUIDE_MISSING_PLAN_SECTIONS = (
        'Missing required sections. Expected headers: "## Why" and "## What Changes". '
        "Ensure modifications are documented in specs/ using modification headers."
    )
    GUIDE_SCENARIO_FORMAT = (
        "Scenarios must use level-4 headers. Convert bullet lists into:\n"
        "#### Scenario: Short name\n- **WHEN** ...\n- **THEN** ...\n- **AND** ..."
    )
