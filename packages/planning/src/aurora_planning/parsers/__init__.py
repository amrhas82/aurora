"""Aurora Parsers.

Provides markdown parsing for capabilities and plans.
Ported from: src/core/parsers/

Note: Parsed* classes are unvalidated dataclasses.
Validation happens separately via the Validator class.
"""

from aurora_planning.parsers.markdown import (
    MarkdownParser,
    ParsedCapability,
    ParsedCapabilityMetadata,
    ParsedModification,
    ParsedPlan,
    ParsedPlanMetadata,
    ParsedRequirement,
    ParsedScenario,
    Section,
)
from aurora_planning.parsers.plan_parser import PlanParser
from aurora_planning.parsers.requirements import (
    ModificationPlan,
    RequirementBlock,
    RequirementsSectionParts,
    extract_requirements_section,
    normalize_requirement_name,
    parse_modification_spec,
)

__all__ = [
    "MarkdownParser",
    "ModificationPlan",
    "ParsedCapability",
    "ParsedCapabilityMetadata",
    "ParsedModification",
    "ParsedPlan",
    "ParsedPlanMetadata",
    "ParsedRequirement",
    "ParsedScenario",
    "PlanParser",
    "RequirementBlock",
    "RequirementsSectionParts",
    "Section",
    "extract_requirements_section",
    "normalize_requirement_name",
    "parse_modification_spec",
]
