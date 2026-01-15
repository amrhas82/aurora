# Plan: Unify Aurora and OpenSpec Templates

## Plan ID
`unify-aurora-openspec-templates`

## Summary
Align Aurora's planning templates (`aur:plan`, `aur:implement`) with OpenSpec's template structure. Remove `aur:proposal`. Keep Aurora branding but match OpenSpec's proven document formats exactly.

## Goals Context
> If goals.json provided, extract and display here

| Subgoal | Agent | Files | Dependencies |
|---------|-------|-------|--------------|
| (extracted from goals.json subgoals[].title) | (subgoals[].agent or LLM) | (memory_context[].file) | (subgoals[].dependencies) |

## Problem Statement

Current state has template divergence:

| Command | Output | Template Quality |
|---------|--------|------------------|
| `aur:plan` | plan.md, tasks.md, design.md | Consultative, asks questions |
| `openspec:proposal` | proposal.md, tasks.md, design.md, specs/ | Comprehensive PRD format |
| `aur:proposal` | Duplicate | Redundant with aur:plan |

**Issues**:
1. `aur:plan` templates don't match OpenSpec's proven structure
2. goals.json from `aur goals` not integrated into planning workflow
3. No specs/ subdirectory for formal requirements
4. No @agent assignment in tasks.md
5. `aur:proposal` duplicates `aur:plan` functionality

## Proposed Solution

### 1. Delete `aur:proposal`
Remove immediately - functionality covered by `aur:plan`.

### 2. Align `aur:plan` Templates with OpenSpec

**Input modes**:
- `aur:plan "prompt"` - Free-form prompt, LLM generates plan
- `aur:plan path/to/goals.json` - Read goals.json, use subgoals + memory_context

**Output structure** (matches OpenSpec, Aurora branded):
```
.aurora/plans/active/{id}/
├── plan.md          # Keep name, match OpenSpec sections
├── design.md        # Technical decisions (when needed)
├── tasks.md         # With <!-- @agent: --> per parent task
├── goals.json       # Preserved from aur goals (if provided)
└── specs/           # NEW: component specifications
    └── {capability}/spec.md
```

**plan.md template** (match OpenSpec sections, Aurora branding):
```markdown
# Plan: [Brief description]

## Plan ID
`{plan-id}`

## Summary
[1-2 sentences]

## Goals Context
> Source: `goals.json` (if provided)

| Subgoal | Agent | Files | Dependencies |
|---------|-------|-------|--------------|

## Problem Statement
[Current state, pain points]

## Proposed Solution
[What changes]

## Benefits
[Why this helps]

## Scope
### In Scope
### Out of Scope

## Dependencies

## Implementation Strategy

## Risks and Mitigations

## Success Criteria

## Open Questions
```

**tasks.md template** (add @agent field):
```markdown
- [ ] 1. Create StructuralAnalyzer
  <!-- @agent: @full-stack-dev -->
  - File: `packages/cli/src/aurora_cli/planning/structural.py`
  - **Validation**: Unit test passes
```

**Agent assignment priority**:
1. From goals.json `subgoals[].agent` if provided
2. From agent registry (`aur agents list`) based on task keywords
3. LLM inference as fallback

**specs/ generation** (match OpenSpec format exactly):
```markdown
# Spec: {Capability Name}

## ADDED Requirements

### Requirement: {Feature Name}
The system SHALL...

#### Scenario: Success case
- **WHEN** user performs action
- **THEN** expected result
```

### 3. Update `aur:implement` to Match OpenSpec

Align with `openspec:apply`:
- Read plan.md + specs/ + tasks.md from plan directory
- Execute tasks sequentially with checkpoints
- Validate completed work against spec scenarios
- Support `--resume` for interrupted execution
- Mark tasks complete in tasks.md as they finish

### 4. Rebrand AGENTS.md and project.md from OpenSpec

Copy exact structure from `openspec/AGENTS.md` and `openspec/project.md`, rebrand to Aurora:
- Replace "OpenSpec" with "Aurora"
- Replace "proposal" terminology with "plan"
- Replace "openspec/" paths with ".aurora/"
- Keep all sections, formatting, and workflow patterns identical

### 5. Fix Slash Command Skill Descriptions

**Current Problem**: Skills show `<!-- AURORA:START --> (project)` instead of meaningful descriptions.

**Expected Display**:
```
/aur:plan        Create plan with agent delegation [goal | goals.json]
/aur:implement   Execute plan tasks with checkpoints [plan-id]
/aur:checkpoint  Save session context ["name"]
/aur:search      Search indexed code ["query" --limit N]
/aur:get         Retrieve search result [N]
/aur:archive     Archive completed plan [plan-id]
```

**Fix**: Update skill registration to use description from frontmatter, not marker comment.

## Benefits

1. **Consistent templates**: Same quality structure as OpenSpec
2. **Better agent assignment**: goals.json provides pre-computed agents + files
3. **Spec-driven implementation**: specs/ enable formal requirements
4. **Reduced confusion**: One less command (aur:proposal removed)

## Scope

### In Scope
- Delete `aur:proposal` skill
- Update `aur:plan` templates to match OpenSpec sections exactly
- Add Goals Context section to plan.md (extracted from goals.json)
- Add `<!-- @agent: @name -->` to tasks.md per parent task
- Add specs/ subdirectory generation for multi-capability plans
- Update `aur:implement` to match openspec:apply
- **Rebrand `.aurora/AGENTS.md` from OpenSpec template** (exact structure, Aurora naming)
- **Rebrand `.aurora/project.md` from OpenSpec template** (exact structure, Aurora naming)
- **Fix slash command skill descriptions** (currently show `<!-- AURORA:START -->`)

### Out of Scope
- Changes to `openspec:proposal` or `openspec:apply` templates
- Changes to `aur goals` decomposition logic
- Changes to agent registry structure
- Merging `.aurora/` and `openspec/` directories

## Dependencies

**Existing Systems**:
- `.aurora/AGENTS.md` - Aurora workflow documentation
- `openspec/AGENTS.md` - OpenSpec templates (source of truth)
- `aur:plan` skill - To be modified
- `aur:implement` skill - To be modified

**Deleted Components**:
- `aur:proposal` skill - Remove entirely

## Implementation Strategy

### Phase 1: Delete aur:proposal (2 tasks)
Remove slash command cleanly.

### Phase 2: Align aur:plan Templates (3 tasks)
Update plan.md and tasks.md templates to match OpenSpec, add goals.json support.

### Phase 3: Add specs/ Generation (2 tasks)
Generate component specs for multi-capability plans.

### Phase 4: Update aur:implement (2 tasks)
Align with openspec:apply behavior.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Breaking existing workflows** | Low | Templates change, filenames stay same |
| **Agent assignment errors** | Low | Fallback chain: goals.json → registry → LLM |
| **specs/ over-generation** | Low | Only generate when >2 components detected |

## Success Criteria

- [ ] `aur:proposal` removed from code and docs
- [ ] `aur:plan` plan.md matches OpenSpec section structure
- [ ] `aur:plan goals.json` extracts and displays Goals Context table
- [ ] tasks.md includes `<!-- @agent: @name -->` for parent tasks
- [ ] specs/ subdirectory generated for multi-capability plans
- [ ] `.aurora/AGENTS.md` rebranded from `openspec/AGENTS.md` template
- [ ] `.aurora/project.md` rebranded from OpenSpec template
- [ ] Skill descriptions show meaningful text (not `<!-- AURORA:START -->`)
- [ ] `aur:implement` reads specs/, supports checkpoint/resume

## Open Questions

1. **Spec generation threshold**: Generate specs/ when >2 capabilities detected?
   - **Recommendation**: Yes

2. **Goals Context when no goals.json**: Show empty table or omit section?
   - **Recommendation**: Omit section entirely

3. **Skill description source**: Where are skill descriptions for `/aur:` registered?
   - **Needs Investigation**: Find registration mechanism to fix `<!-- AURORA:START -->` display
