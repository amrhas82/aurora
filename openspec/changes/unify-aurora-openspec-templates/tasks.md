# Tasks: Unify Aurora and OpenSpec Templates

**Total**: 12 tasks across 5 phases

---

## Phase 1: Delete aur:proposal (2 tasks)

**Goal**: Clean removal of duplicate command

- [x] 1. Remove aur:proposal from ALL_COMMANDS and templates
  <!-- @agent: @code-developer -->
  - Edit `packages/cli/src/aurora_cli/configurators/slash/base.py`:
    - Remove "proposal" from `ALL_COMMANDS`
  - Edit `packages/cli/src/aurora_cli/configurators/slash/claude.py`:
    - Remove "proposal" from `FILE_PATHS`
    - Remove "proposal" from `FRONTMATTER`
  - Edit `packages/cli/src/aurora_cli/templates/slash_commands.py`:
    - Remove `PROPOSAL_TEMPLATE` and related constants
    - Remove "proposal" from `COMMAND_TEMPLATES`
  - **Validation**: `grep -r "proposal" packages/cli/src/aurora_cli/configurators/slash/` returns no matches

- [x] 2. Remove aur:proposal documentation references
  <!-- @agent: @code-developer -->
  - Search: `grep -r "aur:proposal" docs/ .aurora/`
  - Remove or redirect to `aur:plan`
  - Delete `.claude/commands/aur/proposal.md` if exists
  - **Validation**: No references remain

---

## Phase 2: Align aur:plan Templates (3 tasks)

**Goal**: Match OpenSpec section structure exactly

- [x] 3. Update aur:plan plan.md template sections
  <!-- @agent: @code-developer -->
  - Edit `packages/cli/src/aurora_cli/templates/slash_commands.py`:
  - Match OpenSpec sections exactly:
    ```markdown
    # Plan: [Title]
    ## Plan ID
    ## Summary
    ## Goals Context (if goals.json)
    ## Problem Statement
    ## Proposed Solution
    ## Benefits
    ## Scope (In/Out)
    ## Dependencies
    ## Implementation Strategy
    ## Risks and Mitigations
    ## Success Criteria
    ## Open Questions
    ```
  - **Validation**: Diff against openspec:proposal output

- [x] 4. Add goals.json parsing and Goals Context table
  <!-- @agent: @code-developer -->
  - Update PLAN_TEMPLATE in `slash_commands.py`:
    - Detect if input ends with `.json`
    - Parse goals.json and extract:
      - subgoals[].title -> Subgoal column
      - subgoals[].agent -> Agent column (if none, use LLM)
      - memory_context[].file -> Files column
      - subgoals[].dependencies -> Dependencies column
    - Insert table after Summary section
  - **Validation**: `aur:plan goals.json` shows populated table

- [x] 5. Add @agent field to tasks.md template
  <!-- @agent: @code-developer -->
  - Update tasks.md generation in plan template:
    - Add `<!-- @agent: @name -->` after each parent task
    - Agent assignment priority:
      1. goals.json `subgoals[].agent` if provided
      2. `aur agents list` keyword match
      3. LLM inference fallback
  - **Validation**: Each parent task has @agent comment

---

## Phase 3: Add specs/ Generation (2 tasks)

**Goal**: Generate component specs for multi-capability plans

- [x] 6. Detect multi-capability plans
  <!-- @agent: @code-developer -->
  - Analyze plan for >2 distinct components
  - Detection signals:
    - Multiple implementation phases with different focus
    - Multiple new files/modules
    - Separate functional areas
  - **Validation**: Correctly identifies capabilities

- [x] 7. Generate specs/ subdirectory
  <!-- @agent: @code-developer -->
  - Create `specs/{capability}/spec.md` per component
  - Match OpenSpec format exactly:
    ```markdown
    # Spec: {Capability}

    ## ADDED Requirements

    ### Requirement: {Feature}
    The system SHALL...

    #### Scenario: {Case}
    - **WHEN** condition
    - **THEN** result
    ```
  - **Validation**: specs/ matches OpenSpec structure

---

## Phase 4: Rebrand AGENTS.md and project.md (2 tasks)

**Goal**: Exact OpenSpec templates, Aurora branded

- [x] 8. Rebrand AGENTS.md from OpenSpec template
  <!-- @agent: @code-developer -->
  - Copy `openspec/AGENTS.md` structure exactly
  - Replace:
    - "OpenSpec" -> "Aurora"
    - "proposal" -> "plan"
    - "openspec/" -> ".aurora/"
    - "openspec:proposal" -> "aur:plan"
    - "openspec:apply" -> "aur:implement"
    - "openspec:archive" -> "aur:archive"
  - Update template file: `packages/cli/src/aurora_cli/planning/templates/claude.py` or equivalent
  - **Validation**: `.aurora/AGENTS.md` has same sections as `openspec/AGENTS.md`

- [x] 9. Rebrand project.md from OpenSpec template
  <!-- @agent: @code-developer -->
  - Copy `openspec/project.md` structure exactly (if it exists)
  - Same replacements as AGENTS.md
  - **Validation**: `.aurora/project.md` matches OpenSpec structure

---

## Phase 5: Fix Skill Descriptions (3 tasks)

**Goal**: Show meaningful descriptions instead of `<!-- AURORA:START -->`

- [x] 10. Update skill registration to use proper descriptions
  <!-- @agent: @code-developer -->
  - Find where skill descriptions are registered for Claude Code skill listing
  - Current: Shows `<!-- AURORA:START --> (project)`
  - Fix: Added description line before AURORA markers in slash command files
  - Added `get_description()` method to base configurator
  - Expected descriptions:
    ```
    aur:plan        Create plan with agent delegation [goal | goals.json]
    aur:implement   Execute plan tasks with checkpoints [plan-id]
    aur:checkpoint  Save session context ["name"]
    aur:search      Search indexed code ["query" --limit N]
    aur:get         Retrieve search result [N]
    aur:archive     Archive completed plan [plan-id]
    ```
  - **Validation**: `/aur:` shows proper descriptions

- [x] 11. Update aur:implement to read specs/
  <!-- @agent: @code-developer -->
  - Read plan.md + specs/ + tasks.md from plan directory
  - Execute tasks sequentially
  - Mark tasks complete (`- [x]`) in tasks.md
  - Save checkpoint after each task
  - Support `--resume` flag
  - **Validation**: `aur:implement` executes with checkpoint/resume

- [x] 12. Update documentation
  <!-- @agent: @code-developer -->
  - Update .aurora/AGENTS.md with new structure
  - Document Goals Context table
  - Document @agent field in tasks.md
  - Document specs/ generation
  - **Validation**: Docs accurate

---

## Dependency Graph

```
Phase 1 (Delete aur:proposal)
  └─> Phase 2 (Align templates)
      └─> Phase 3 (specs/ generation)
          └─> Phase 4 (Rebrand AGENTS.md/project.md)
              └─> Phase 5 (Fix skill descriptions + aur:implement)
```

---

## Definition of Done

- [x] aur:proposal removed from code and docs
- [x] aur:plan plan.md matches OpenSpec sections
- [x] goals.json -> Goals Context table working
- [x] tasks.md has `<!-- @agent: -->` per parent task
- [x] specs/ generated for multi-capability plans
- [x] .aurora/AGENTS.md rebranded from OpenSpec template
- [x] .aurora/project.md rebranded from OpenSpec template
- [x] Skill descriptions show meaningful text, not `<!-- AURORA:START -->`
- [x] aur:implement reads specs/, has checkpoint/resume
