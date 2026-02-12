# OpenSpec → Aurora Port Mapping

**Source**: https://github.com/hamr0/OpenSpec (v0.17.2)
**Target**: Aurora Planning System (Python)
**Created**: 2026-01-02

---

## Executive Summary

**TypeScript Source** (reference only): 92 files, 11,396 lines at `/tmp/openspec-source/src/`
**Distributed Package** (port from this): 83 files, 8,015 lines at `/usr/lib/node_modules/@fission-ai/openspec/dist/`
**Files to Port**: ~25 files (P0-P2 priority)
**Files to Skip**: ~58 files (completions, configurators, templates we don't need)

**Strategy**:
- Read TypeScript source for understanding (types, comments, clean logic)
- Port from distributed JavaScript (actual runtime code, tree-shaken)

---

## Terminology Mapping

| OpenSpec (TypeScript) | Aurora (Python) | Notes |
|----------------------|-----------------|-------|
| `openspec` | `aurora` | Package name |
| `change` | `plan` | A proposal for changes |
| `spec` | `capability` | A system capability |
| `delta` | `modification` | A change to a requirement |
| `proposal.md` | `plan.md` | Main plan file |
| `Change` | `Plan` | Class/type name |
| `Spec` | `Capability` | Class/type name |
| `Delta` | `Modification` | Class/type name |

---

## Stack Translation

| TypeScript | Python | Notes |
|-----------|--------|-------|
| Zod | Pydantic | Schema validation |
| `z.object()` | `BaseModel` | Class definition |
| `z.string().min(1)` | `str = Field(min_length=1)` | String constraints |
| `z.array()` | `list[]` | Array types |
| `z.enum()` | `Enum` | Enum types |
| `z.infer<typeof X>` | Type annotation from model | Type inference |
| Commander.js | Click | CLI framework |
| Inquirer.js | `Rich.prompt` | Interactive prompts |
| Chalk | `Rich.console` | Terminal colors |
| `fs` / `path` | `pathlib` | File system |
| `process.cwd()` | `Path.cwd()` | Current directory |
| `async/await` | `async/await` | Same in Python |

---

## File-to-File Translation Map

### P0: Critical Core (Port First)

| Read for Understanding | Port From (dist/) | Lines | Aurora Python | Priority | Notes |
|------------------------|-------------------|-------|---------------|----------|-------|
| `src/core/validation/validator.ts` | `dist/core/validation/validator.js` | 407 | `planning/validation/validator.py` | P0 | CRITICAL - 20+ methods |
| `src/core/validation/constants.ts` | `dist/core/validation/constants.js` | 40 | `planning/validation/constants.py` | P0 | 5 thresholds, 22 messages |
| `src/core/validation/types.ts` | `dist/core/validation/types.js` | 18 | `planning/validation/types.py` | P0 | ValidationIssue, ValidationReport |
| `src/core/parsers/markdown-parser.ts` | `dist/core/parsers/markdown-parser.js` | 186 | `planning/parsers/markdown.py` | P0 | CRITICAL - MarkdownParser class |
| `src/core/parsers/change-parser.ts` | `dist/core/parsers/change-parser.js` | 192 | `planning/parsers/plan.py` | P0 | ChangeParser → PlanParser |
| `src/core/parsers/requirement-blocks.ts` | `dist/core/parsers/requirement-blocks.js` | 200 | `planning/parsers/requirements.py` | P0 | CRITICAL - Delta parsing |
| `src/core/schemas/base.schema.ts` | `dist/core/schemas/base.schema.js` | 13 | `planning/schemas/base.py` | P0 | Scenario, Requirement |
| `src/core/schemas/change.schema.ts` | `dist/core/schemas/change.schema.js` | 31 | `planning/schemas/plan.py` | P0 | DeltaOperation, Delta, Change |
| `src/core/schemas/spec.schema.ts` | `dist/core/schemas/spec.schema.js` | 15 | `planning/schemas/capability.py` | P0 | Spec schema |

### P1: Commands (Port Second)

| OpenSpec TypeScript | Lines | Aurora Python | Priority | Notes |
|---------------------|-------|---------------|----------|-------|
| `src/core/archive.ts` | 625 | `planning/archive.py` | P1 | Complex archive workflow |
| `src/core/init.ts` | 986 | `planning/init_cmd.py` | P1 | LARGEST - directory setup |
| `src/core/list.ts` | 193 | `planning/list_cmd.py` | P1 | List changes/specs |
| `src/core/view.ts` | 218 | `planning/view.py` | P1 | Dashboard display |
| `src/core/update.ts` | 129 | `planning/update.py` | P1 | Update management |
| `src/commands/validate.ts` | 326 | `commands/validate.py` | P1 | CLI validate command |
| `src/commands/change.ts` | 292 | `commands/plan.py` | P1 | CLI change command |
| `src/commands/spec.ts` | 251 | `commands/capability.py` | P1 | CLI spec command |
| `src/commands/show.ts` | 138 | Integrate into plan.py/capability.py | P1 | Show command logic |

### P2: Configuration & Utilities (Port Third)

| OpenSpec TypeScript | Lines | Aurora Python | Priority | Notes |
|---------------------|-------|---------------|----------|-------|
| `src/core/config.ts` | 41 | `planning/config.py` | P2 | Configuration loading |
| `src/core/config-schema.ts` | 230 | `planning/config_schema.py` | P2 | Config Zod schemas |
| `src/core/global-config.ts` | 136 | `planning/global_config.py` | P2 | Global config management |
| `src/utils/file-system.ts` | 209 | `planning/utils/filesystem.py` | P2 | File operations |
| `src/utils/task-progress.ts` | 43 | `planning/utils/progress.py` | P2 | Task counting |
| `src/core/converters/json-converter.ts` | 62 | `planning/converters/json.py` | P2 | JSON conversion |
| `src/utils/change-utils.ts` | 102 | `planning/utils/plan_utils.py` | P2 | Change utilities |
| `src/utils/item-discovery.ts` | 66 | `planning/utils/discovery.py` | P2 | Item discovery |

### P3: Templates (Port Fourth)

| OpenSpec TypeScript | Lines | Aurora Python | Priority | Notes |
|---------------------|-------|---------------|----------|-------|
| `src/core/templates/agents-template.ts` | 457 | `planning/templates/agents.py` | P3 | AGENTS.md template |
| `src/core/templates/project-template.ts` | 37 | `planning/templates/project.py` | P3 | Project template |
| `src/core/templates/slash-command-templates.ts` | 60 | `planning/templates/slash.py` | P3 | Slash commands |

### SKIP: Out of Scope

| OpenSpec TypeScript | Lines | Reason to Skip |
|---------------------|-------|----------------|
| `src/core/completions/*` | ~1500 | Use Click's built-in completions |
| `src/core/configurators/*` | ~1000 | Aurora has own config system |
| `src/core/artifact-graph/*` | ~1000 | New feature, not in original scope |
| `src/commands/artifact-workflow.ts` | 595 | New feature, not in original scope |
| `src/cli/index.ts` | 326 | Integrate into existing main.py |

---

## Function-to-Function Translation: validator.ts

**Source**: `src/core/validation/validator.ts` (449 lines)
**Target**: `planning/validation/validator.py`

### Class Structure

```typescript
export class Validator {
  private strictMode: boolean;

  constructor(strictMode = false) {
    this.strictMode = strictMode;
  }
```

```python
class Validator:
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
```

### Method Mapping

| TypeScript Method | Python Method | Lines | Purpose |
|-------------------|---------------|-------|---------|
| `validateSpec(filePath: string)` | `validate_capability(file_path: str)` | ~30 | Validate capability file |
| `validateSpecContent(specName: string, content: string)` | `validate_capability_content(name: str, content: str)` | ~20 | Validate capability string |
| `validateChange(filePath: string)` | `validate_plan(file_path: str)` | ~30 | Validate plan file |
| `validateChangeDeltaSpecs(changeDir: string)` | `validate_plan_delta_specs(plan_dir: str)` | ~150 | CRITICAL - Validate all delta specs |
| `convertZodErrors(error: ZodError)` | `_convert_pydantic_errors(error: ValidationError)` | ~10 | Convert Pydantic errors to issues |
| `applySpecRules(spec: Spec, content: string)` | `_apply_capability_rules(capability: Capability, content: str)` | ~25 | Apply business rules |
| `applyChangeRules(change: Change, content: string)` | `_apply_plan_rules(plan: Plan, content: str)` | ~20 | Apply business rules |
| `enrichTopLevelError(itemId: string, baseMessage: string)` | `_enrich_top_level_error(item_id: str, base_message: str)` | ~15 | Add guidance to errors |
| `extractRequirementText(blockRaw: string)` | `_extract_requirement_text(block_raw: str)` | ~20 | Extract first non-metadata line |
| `containsShallOrMust(text: string)` | `_contains_shall_or_must(text: str)` | ~2 | Check SHALL/MUST keywords |
| `countScenarios(blockRaw: string)` | `_count_scenarios(block_raw: str)` | ~3 | Count #### headers |
| `extractNameFromPath(filePath: string)` | `_extract_name_from_path(file_path: str)` | ~15 | Extract name from path |
| `createReport(issues: ValidationIssue[])` | `_create_report(issues: list[ValidationIssue])` | ~10 | Build validation report |
| `isValid(report: ValidationReport)` | N/A | ~1 | Simple property access |
| `formatSectionList(sections: string[])` | `_format_section_list(sections: list[str])` | ~5 | Format section names |

### Critical Logic: validateChangeDeltaSpecs

**TypeScript** (150 lines):
```typescript
async validateChangeDeltaSpecs(changeDir: string): Promise<ValidationReport> {
  const issues: ValidationIssue[] = [];
  const specsDir = path.join(changeDir, 'specs');
  let totalDeltas = 0;

  // Track sections with headers but no entries
  const missingHeaderSpecs: string[] = [];
  const emptySectionSpecs: Array<{path: string; sections: string[]}> = [];

  // For each spec directory under specs/
  // Parse delta spec with parseDeltaSpec()
  // Validate ADDED: must have SHALL/MUST + scenarios
  // Validate MODIFIED: must have SHALL/MUST + scenarios
  // Validate REMOVED: names only
  // Validate RENAMED: FROM/TO pairs
  // Check duplicates within sections
  // Check cross-section conflicts

  if (totalDeltas === 0) {
    issues.push({ level: 'ERROR', path: 'file', message: VALIDATION_MESSAGES.CHANGE_NO_DELTAS });
  }

  return this.createReport(issues);
}
```

**Python Translation**:
```python
async def validate_plan_delta_specs(self, plan_dir: str) -> ValidationReport:
    """Validate all delta-formatted spec files under a plan directory."""
    issues: list[ValidationIssue] = []
    specs_dir = Path(plan_dir) / 'specs'
    total_deltas = 0

    missing_header_specs: list[str] = []
    empty_section_specs: list[dict] = []

    # Same logic as TypeScript
    # Use parsers.requirements.parse_delta_spec()
    # Apply ALL validation rules

    if total_deltas == 0:
        issues.append(ValidationIssue(
            level='ERROR',
            path='file',
            message=VALIDATION_MESSAGES['CHANGE_NO_DELTAS']
        ))

    return self._create_report(issues)
```

---

## Function-to-Function Translation: parsers/requirement-blocks.ts

**Source**: `src/core/parsers/requirement-blocks.ts` (234 lines)
**Target**: `planning/parsers/requirements.py`

### Key Functions

| TypeScript Function | Python Function | Purpose |
|---------------------|-----------------|---------|
| `parseDeltaSpec(content: string)` | `parse_delta_spec(content: str)` | Parse delta spec into added, modified, removed, renamed |
| `extractRequirementsSection(content: string, headerText: string)` | `extract_requirements_section(content: str, header_text: str)` | Extract section with before/after preservation |
| `normalizeRequirementName(name: string)` | `normalize_requirement_name(name: str)` | Normalize for comparison |
| `parseAddedBlock(raw: string)` | `_parse_added_block(raw: str)` | Parse ADDED requirement block |
| `parseModifiedBlock(raw: string)` | `_parse_modified_block(raw: str)` | Parse MODIFIED requirement block |
| `parseRemovedList(sectionBody: string)` | `_parse_removed_list(section_body: str)` | Parse REMOVED requirements |
| `parseRenamedList(sectionBody: string)` | `_parse_renamed_list(section_body: str)` | Parse RENAMED pairs (FROM/TO) |

### Critical Pattern: FROM/TO Parsing

**TypeScript**:
```typescript
// Parse RENAMED section for FROM/TO pairs
const renamedMatches = sectionBody.matchAll(
  /FROM:\s*`([^`]+)`[\s\S]*?TO:\s*`([^`]+)`/gi
);
for (const match of renamedMatches) {
  const from = extractRequirementName(match[1]);
  const to = extractRequirementName(match[2]);
  if (from && to) {
    renamed.push({ from, to });
  }
}
```

**Python**:
```python
# Parse RENAMED section for FROM/TO pairs
renamed_pattern = r"FROM:\s*`([^`]+)`[\s\S]*?TO:\s*`([^`]+)`"
for match in re.finditer(renamed_pattern, section_body, re.IGNORECASE):
    from_name = _extract_requirement_name(match.group(1))
    to_name = _extract_requirement_name(match.group(2))
    if from_name and to_name:
        renamed.append({"from": from_name, "to": to_name})
```

---

## Function-to-Function Translation: archive.ts

**Source**: `src/core/archive.ts` (625 lines)
**Target**: `planning/archive.py`

### Critical Workflow: Operation Ordering

**TypeScript** (archive.ts:350-450):
```typescript
// CRITICAL: Operations must be applied in this order to avoid conflicts
// 1. RENAMED - renames must happen first before other operations reference new names
// 2. REMOVED - remove requirements before modifying others
// 3. MODIFIED - modify existing requirements
// 4. ADDED - add new requirements last

for (const { from, to } of renamed) {
  // Find requirement with old name, rename header
}

for (const name of removed) {
  // Find and remove requirement block
}

for (const block of modified) {
  // Find requirement, replace entire block
}

for (const block of added) {
  // Append to end of Requirements section
}
```

**Python Translation**:
```python
# CRITICAL: Operations must be applied in this exact order
# 1. RENAMED - renames must happen first
# 2. REMOVED - remove requirements
# 3. MODIFIED - modify existing requirements
# 4. ADDED - add new requirements last

for rename in renamed:
    # Find requirement with old name, rename header

for name in removed:
    # Find and remove requirement block

for block in modified:
    # Find requirement, replace entire block

for block in added:
    # Append to end of Requirements section
```

---

## Edge Cases & Business Logic Patterns

### 1. Cross-Section Conflict Detection

**Rule**: A requirement CANNOT appear in multiple delta sections (ADDED + REMOVED, MODIFIED + REMOVED, etc.)

**Implementation** (validator.ts:209-232):
```typescript
// Cross-section conflicts (within the same spec file)
for (const n of modifiedNames) {
  if (removedNames.has(n)) {
    issues.push({ level: 'ERROR', path: entryPath, message: `Requirement present in both MODIFIED and REMOVED: "${n}"` });
  }
  if (addedNames.has(n)) {
    issues.push({ level: 'ERROR', path: entryPath, message: `Requirement present in both MODIFIED and ADDED: "${n}"` });
  }
}

for (const n of addedNames) {
  if (removedNames.has(n)) {
    issues.push({ level: 'ERROR', path: entryPath, message: `Requirement present in both ADDED and REMOVED: "${n}"` });
  }
}
```

### 2. RENAMED Collision Detection

**Rule**: RENAMED TO cannot collide with ADDED, MODIFIED cannot reference old name from RENAMED

**Implementation** (validator.ts:223-232):
```typescript
for (const { from, to } of plan.renamed) {
  const fromKey = normalizeRequirementName(from);
  const toKey = normalizeRequirementName(to);

  if (modifiedNames.has(fromKey)) {
    issues.push({ level: 'ERROR', path: entryPath, message: `MODIFIED references old name from RENAMED. Use new header for "${to}"` });
  }

  if (addedNames.has(toKey)) {
    issues.push({ level: 'ERROR', path: entryPath, message: `RENAMED TO collides with ADDED for "${to}"` });
  }
}
```

### 3. Duplicate Detection Within Sections

**Rule**: Duplicate requirement names within same section (ADDED, MODIFIED, REMOVED, RENAMED) are errors

**Implementation**: Use `Set<string>` to track normalized names per section

### 4. SHALL/MUST Enforcement

**Rule**: ADDED and MODIFIED requirements MUST contain "SHALL" or "MUST" keyword (case-sensitive)

**Implementation** (validator.ts:368-372):
```typescript
extractRequirementText(blockRaw: string): string | undefined {
  // Skip header (line 0), metadata lines (**ID**:, **Priority**:), blank lines
  // Return first substantial text line
  // Stop at scenario headers (#### )
}

containsShallOrMust(text: string): boolean {
  return /\b(SHALL|MUST)\b/.test(text);  // Word boundaries, case-sensitive
}
```

### 5. Scenario Count Validation

**Rule**: ADDED and MODIFIED requirements MUST have at least one scenario

**Implementation** (validator.ts:388-391):
```typescript
countScenarios(blockRaw: string): number {
  const matches = blockRaw.match(/^####\s+/gm);
  return matches ? matches.length : 0;
}
```

---

## Validation Rules That Must Not Be Missed

### For Capabilities (Specs)

1. ✅ Must have "## Purpose" section
2. ✅ Must have "## Requirements" section
3. ✅ Purpose must be >= 50 chars (WARNING if < 50)
4. ✅ Each requirement must contain "SHALL" or "MUST"
5. ✅ Each requirement must have at least one scenario (WARNING if 0)
6. ✅ Requirement text > 500 chars is INFO warning

### For Plans (Changes)

1. ✅ Must have "## Why" section
2. ✅ Must have "## What Changes" section
3. ✅ Why must be 50-1000 chars
4. ✅ Must have at least 1 delta/modification
5. ✅ Max 10 deltas (WARNING if > 10)
6. ✅ Delta description must be >= 10 chars (WARNING if < 10)
7. ✅ ADDED/MODIFIED deltas should have requirements (WARNING if missing)

### For Delta Specs

1. ✅ Must have at least ONE delta across ALL spec files
2. ✅ ADDED requirements: MUST have SHALL/MUST + at least 1 scenario
3. ✅ MODIFIED requirements: MUST have SHALL/MUST + at least 1 scenario
4. ✅ REMOVED requirements: names only (no text/scenarios needed)
5. ✅ RENAMED requirements: FROM/TO pairs well-formed
6. ✅ NO duplicates within sections
7. ✅ NO cross-section conflicts (same name in ADDED + REMOVED, etc.)
8. ✅ RENAMED TO cannot collide with ADDED
9. ✅ MODIFIED cannot reference old name from RENAMED

---

## TypeScript → Python Pattern Translations

### 1. Zod Schema → Pydantic Model

**TypeScript**:
```typescript
export const ScenarioSchema = z.object({
  rawText: z.string().min(1, VALIDATION_MESSAGES.SCENARIO_EMPTY),
});

export const RequirementSchema = z.object({
  text: z.string()
    .min(1, VALIDATION_MESSAGES.REQUIREMENT_EMPTY)
    .refine(
      (text) => text.includes('SHALL') || text.includes('MUST'),
      VALIDATION_MESSAGES.REQUIREMENT_NO_SHALL
    ),
  scenarios: z.array(ScenarioSchema)
    .min(1, VALIDATION_MESSAGES.REQUIREMENT_NO_SCENARIOS),
});
```

**Python**:
```python
from pydantic import BaseModel, Field, field_validator

class Scenario(BaseModel):
    raw_text: str = Field(min_length=1, description=VALIDATION_MESSAGES['SCENARIO_EMPTY'])

class Requirement(BaseModel):
    text: str = Field(min_length=1, description=VALIDATION_MESSAGES['REQUIREMENT_EMPTY'])
    scenarios: list[Scenario] = Field(min_length=1, description=VALIDATION_MESSAGES['REQUIREMENT_NO_SCENARIOS'])

    @field_validator('text')
    @classmethod
    def must_contain_shall_or_must(cls, v: str) -> str:
        if 'SHALL' not in v and 'MUST' not in v:
            raise ValueError(VALIDATION_MESSAGES['REQUIREMENT_NO_SHALL'])
        return v
```

### 2. Enum Translation

**TypeScript**:
```typescript
export const DeltaOperationType = z.enum(['ADDED', 'MODIFIED', 'REMOVED', 'RENAMED']);
export type DeltaOperation = z.infer<typeof DeltaOperationType>;
```

**Python**:
```python
from enum import Enum

class ModificationOperation(str, Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    REMOVED = "REMOVED"
    RENAMED = "RENAMED"
```

### 3. Optional Fields

**TypeScript**:
```typescript
requirement: RequirementSchema.optional(),
requirements: z.array(RequirementSchema).optional(),
```

**Python**:
```python
requirement: Requirement | None = None
requirements: list[Requirement] | None = None
```

### 4. File Operations

**TypeScript**:
```typescript
import { readFileSync } from 'fs';
import path from 'path';

const content = readFileSync(filePath, 'utf-8');
const changeDir = path.dirname(filePath);
```

**Python**:
```python
from pathlib import Path

content = Path(file_path).read_text(encoding='utf-8')
plan_dir = Path(file_path).parent
```

### 5. Regex Patterns

**TypeScript**:
```typescript
const matches = blockRaw.match(/^####\s+/gm);
const isValid = /\b(SHALL|MUST)\b/.test(text);
```

**Python**:
```python
import re

matches = re.findall(r'^####\s+', block_raw, re.MULTILINE)
is_valid = bool(re.search(r'\b(SHALL|MUST)\b', text))
```

---

## Dependencies Between Modules

```
Schemas (base, plan, capability)
  ↓
Parsers (markdown, plan, requirements)
  ↓
Validator
  ↓
Commands (archive, init, list, view, validate)
  ↓
CLI (main.py integration)
```

**Port Order**:
1. Constants & Types first (no dependencies)
2. Schemas (depend on constants)
3. Parsers (depend on schemas)
4. Validator (depends on parsers, schemas)
5. Utils (depend on basic types)
6. Commands (depend on validator, parsers, utils)
7. CLI integration (depends on commands)

---

## Test Strategy

### Unit Tests (Per Module)

- **Schemas**: Test Pydantic validation rules
- **Parsers**: Test markdown parsing, section extraction, delta parsing
- **Validator**: Test all validation rules, error messages, strict mode
- **Utils**: Test file operations, progress tracking
- **Commands**: Test command logic with mocks

### Integration Tests

- **CLI**: Test end-to-end command execution
- **Shell**: Test actual CLI commands with temp directories

### Behavior Parity Tests

- Create same test case in both OpenSpec and Aurora
- Validate same files with both tools
- Compare JSON outputs for exact match

---

## Summary Statistics

**Total Files to Port**: 25 files (from dist/)
**Total Lines to Port**: ~3,000 lines (compiled JS)
**Estimated Effort**: 20-28 hours

**Priority Breakdown**:
- P0 (Critical): 9 files, ~900 lines (compiled)
- P1 (Commands): 8 files, ~2,000 lines (compiled)
- P2 (Utils): 6 files, ~700 lines (compiled)
- P3 (Templates): 2 files, ~400 lines (compiled, may skip complex ones)

**Files to Skip**: 58 files (~5,000 lines) - completions, configurators, artifact-graph, complex templates

---

*Generated from OpenSpec v0.17.2 source analysis*
*Ready for Phase 1 implementation*
