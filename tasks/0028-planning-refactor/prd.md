# PRD: Aurora Planning System Refactor

## Overview

Fine-tune the existing OpenSpec-based planning system to simplify workflows and align with the 3-step planning flow. This is **NOT** a rewrite - we are refining existing templates and removing unused features.

**Key principle:** We keep the OpenSpec templates and fine-tune them to match our 3 simple steps workflow (aur goals → /aur:plan → /aur:implement).

Changes include: removing unused spec generation, fixing broken CLI command references, adding `/aur:tasks` for PRD iteration, and enhancing file matching in goals.json.

## Goals

1. **Remove dead code**: Drop spec generation entirely (no consumer, generates unused files)
2. **Fix broken references**: Remove CLI commands from skill instructions that don't exist
3. **Enable PRD iteration**: Add `/aur:tasks` skill to regenerate tasks.md after PRD edits
4. **Simplify plan IDs**: Remove number prefix from plan folders (use slug only)
5. **Fix bugs**: Resolve `aur plan view` schema mismatch error (agent_exists, recommended_agent)

## User Stories

1. As a developer using `/aur:plan`, I want clear skill instructions that reference only existing CLI commands, so I don't encounter errors
2. As a developer editing prd.md, I want to regenerate tasks.md without regenerating all artifacts, so I can iterate quickly
3. As a developer reviewing goals.json, I want to see which source file each subgoal relates to, so I can navigate the codebase efficiently

## Requirements

### R1: Remove Spec Generation (Cleanup)

**R1.1** System MUST NOT generate spec files in `.aurora/plans/active/<id>/specs/` directory
- File: `packages/cli/src/aurora_cli/planning/core.py`
- Method: `_write_plan_files()` (lines 911-1007)
- Change: Remove spec file generation from atomic file write logic

**R1.2** System MUST NOT reference spec files in validation
- File: `packages/cli/src/aurora_cli/planning/core.py`
- Method: `validate_plan_structure()` (lines 67-133)
- Change: Remove `optional_files` list and validation for `specs/{plan-id}-*.md`

**R1.3** System MUST NOT display spec files in CLI output
- File: `packages/cli/src/aurora_cli/commands/plan.py`
- Lines: 217-225 (create_command), 541-544 (archive_command)
- Change: Remove references to "8 files" and spec file listings, update to "5 files"

**R1.4** System MUST NOT reference specs in show_plan file status
- File: `packages/cli/src/aurora_cli/planning/core.py`
- Method: `show_plan()` (lines 543-562)
- Change: Remove spec entries from `files_status` dict

### R2: Fix Non-Existent Command References

**R2.1** System MUST remove `aur plan validate <id> --strict` from skill instructions
- File: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Line: 168 in PLAN_STEPS
- Change: Remove step 7 referencing validation, replace with `aur plan view <id>` for verification

**R2.2** System MUST remove `aur plan list --specs` from skill instructions
- File: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Line: 160 in PLAN_STEPS
- Change: Remove `--specs` flag reference, use `aur plan list` only

**R2.3** System MUST remove `aur plan show <id> --json --deltas-only` from skill instructions
- File: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Line: 171 in PLAN_REFERENCES
- Change: Remove reference, replace with `aur plan view <id> --format json`

### R3: Update Artifact Generation Order

**R3.1** Skill instructions MUST specify artifact generation order: plan.md, prd.md, design.md, agents.json, tasks.md
- File: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Section: PLAN_STEPS
- Change: Update step 2 to specify explicit file order, with tasks.md generated LAST

**R3.2** Instructions MUST note tasks.md depends on PRD content
- File: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Section: PLAN_STEPS
- Change: Add note that tasks.md is derived from PRD requirements and subgoals

**R3.3** PLAN_STEPS MUST emphasize goals.json as recommended but optional
- File: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Section: PLAN_STEPS Step 1
- Change: Update to clarify:
  - Check for `goals.json` first (recommended for code-aware planning)
  - If `goals.json` exists: use it for subgoals, agents, source_file mappings
  - If no `goals.json`: continue with prompt-based planning (less structured, agent searches on the fly)
- Note: Both paths are valid, goals.json is recommended not required

**R3.4** tasks.md template MUST include TDD hints (fine-tune existing template)
- File: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Section: PLAN_REFERENCES (tasks.md Template)
- Change: Add TDD fields to task format, matching 2-generate-tasks agent pattern:
  ```markdown
  ## Phase N: [Name]
  - [ ] N.1 Task description
    <!-- @agent: @code-developer -->
    - tdd: yes|no
    - verify: `command to verify`
    - **Validation**: How to verify
  ```
- Include TDD Detection guidance:
  - `tdd: yes` for: models, API endpoints, bug fixes, business logic
  - `tdd: no` for: docs, config, migrations, refactors (no behavior change)
  - Default: when unsure, use `tdd: yes`
- Note: This is a fine-tune of existing OpenSpec tasks.md template, not a replacement

### R4: Add agents.json Schema Documentation

**R4.1** Skill instructions MUST include agents.json schema reference
- File: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Section: PLAN_REFERENCES
- Change: Add agents.json template with required fields:
  - plan_id, goal, status, created_at, updated_at, subgoals[]
  - Each subgoal: id, title, description, agent_id, status, dependencies[]

**R4.2** Skill instructions MUST reference existing schema file
- File: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Change: Add reference to `packages/planning/src/aurora_planning/schemas/agents.schema.json`

### R5: New Skill - aur:tasks (Carve-out from aur:plan)

**R5.1** TASKS_TEMPLATE MUST be a carve-out of tasks.md generation from PLAN_TEMPLATE
- File: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Change: Extract the tasks.md generation instructions from PLAN_TEMPLATE into TASKS_TEMPLATE
- NO new code or logic - same exact instructions for tasks.md, just isolated
- Purpose: Regenerate tasks.md from prd.md after user edits PRD
- Reads: prd.md, goals.json, agents.json from plan directory
- Outputs: tasks.md (replaces existing)

**R5.2** System MUST add "tasks" to COMMAND_TEMPLATES dict
- File: `packages/cli/src/aurora_cli/templates/slash_commands.py`
- Line: ~279
- Change: Add `"tasks": TASKS_TEMPLATE` to dict

**R5.3** All 20 configurators MUST generate `/aur:tasks` command file
- Files: All configurators in `packages/cli/src/aurora_cli/configurators/slash/`
- Change: Add "tasks" to command list in `get_relative_path()`

**R5.4** aur:plan and aur:tasks MUST share the same tasks.md template/instructions
- Rationale: Single source of truth for tasks.md format
- aur:plan generates tasks.md as part of full flow
- aur:tasks regenerates tasks.md standalone (same instructions, same output format)

**R5.5** All 20 configurators MUST use consistent description for aur:tasks
- Description: `Regenerate tasks from PRD [plan-id]`
- Files: All configurators in `packages/cli/src/aurora_cli/configurators/slash/`
- Change: Add "tasks" entry to `get_description()` return dict

### R6: Enhanced File Matching in goals.json (Same LLM Call)

**R6.0** source_file is an addition to EXISTING LLM call, NOT a new call
- NO new LLM request - just add field to existing JSON response schema
- LLM already receives code snippets with file names (line 408: `File: {short_path}`)
- LLM already returns subgoals in JSON
- Change: Ask LLM to include `source_file` field per subgoal in SAME response

**R6.1** SubgoalData model MUST include optional source_file field
- File: `packages/cli/src/aurora_cli/planning/models.py`
- Class: SubgoalData (lines 986-1057)
- Change: Add `source_file: str | None = Field(default=None, description="Primary source file for this subgoal")`

**R6.2** Goals model MUST serialize source_file in JSON output
- File: `packages/cli/src/aurora_cli/planning/models.py`
- Automatic via Pydantic when field is added

**R6.3** Decomposition MUST resolve source_file from context we sent
- File: `packages/cli/src/aurora_cli/planning/decompose.py`
- Method: `_call_soar()` (lines 473-584)
- Change: When LLM references a file name in subgoal response:
  - If file name matches one we sent in context → resolve to full path
  - If file name doesn't match any we sent → `source_file: null` + warn (hallucination)
  - If LLM doesn't reference a file → `source_file: null` (no file for this subgoal)
- Applies to both code files AND markdown files (kb chunks)

**R6.4** Context summary already includes file paths - no change needed
- File: `packages/cli/src/aurora_cli/planning/decompose.py`
- Method: `_build_context_summary()` (lines 356-434)
- Current: Already includes file paths per chunk (line 408: `File: {short_path}`)
- Change: None - file paths already provided to LLM

**R6.5** generate_goals_json MUST include source_file in SubgoalData
- File: `packages/cli/src/aurora_cli/planning/core.py`
- Function: `generate_goals_json()` (lines 1127-1207)
- Change: Add `source_file=sg.source_file` when creating SubgoalData
- Result: Generated goals.json includes file path per subgoal:
  ```json
  {
    "subgoals": [{
      "id": "sg-1",
      "title": "Schema extension",
      "source_file": "packages/core/src/aurora_core/store/sqlite.py"
    }]
  }
  ```

**R6.6** SOAR DecomposePromptTemplate MUST include source_file in subgoal JSON schema
- File: `packages/reasoning/src/aurora_reasoning/prompts/decompose.py`
- Method: `build_system_prompt()` (lines 180-202)
- Change: Add `source_file` field to subgoal schema in JSON template:
  ```json
  {
    "description": "Specific subgoal description",
    "source_file": "path/to/relevant/file.py",
    ...
  }
  ```
- Same approach as R6.0: NO new LLM call, just add field to existing JSON response schema
- Context already includes file paths (line 251: `File: {short_path}`)

**R6.7** SOAR decompose MUST resolve source_file from context we sent
- File: `packages/reasoning/src/aurora_reasoning/decompose.py`
- Method: `decompose_query()` (lines 151-186)
- Change: When LLM references a file name in subgoal response:
  - If file name matches one we sent in context → resolve to full path
  - If file name doesn't match any we sent → `source_file: null` + warn (hallucination)
  - If LLM doesn't reference a file → `source_file: null` (no file for this subgoal)
- Applies to both code files AND markdown files (kb chunks)
- Same pattern as `ideal_agent`/`ideal_agent_desc` which are null when no gap
- Backward compatible: existing decompositions without source_file continue to work

**R6.8** Both `aur goals` and `aur soar` MUST use identical source_file approach
- Rationale: Consistent behavior across planning and SOAR pipelines
- Both pipelines:
  1. Provide code context with file paths to LLM
  2. Ask LLM to include `source_file` per subgoal in SAME response
  3. Extract `source_file` from LLM JSON response (optional field)
- NO separate LLM calls for file matching in either pipeline

### R7: Remove Slug Number Prefix from Plan Folders

**R7.1** Plan folder names MUST NOT include number prefix
- Current: `.aurora/plans/active/0005-improve-aur-mem-search/`
- New: `.aurora/plans/active/improve-aur-mem-search/`
- File: `packages/cli/src/aurora_cli/planning/core.py`
- Function: `_generate_plan_id()` or equivalent
- Change: Remove sequential number generation, use slug only

**R7.2** aur goals MUST override existing folder if same slug exists
- File: `packages/cli/src/aurora_cli/planning/core.py`
- Rationale: Re-running same goal = previous run failed, should replace not create new
- Change: Check if slug folder exists, if so overwrite instead of creating numbered variant

**R7.3** aur:plan without goals.json MUST create plan folder without number prefix
- File: `packages/cli/src/aurora_cli/planning/core.py`
- Change: When creating plan from scratch (no goals.json), generate slug from goal text without number

**R7.4** aur plan list MUST display plans without number prefix
- File: `packages/cli/src/aurora_cli/commands/plan.py`
- Function: `list_command()`
- Change: Display slug-only plan IDs (backward compatible with existing numbered plans)

### R8: Fix aur plan view Schema Mismatch

**R8.1** view_command MUST use correct Subgoal attribute names
- File: `packages/cli/src/aurora_cli/commands/plan.py`
- Lines: 469-479
- Current (broken):
  ```python
  status = "[green][/]" if sg.agent_exists else "[yellow]NOT FOUND[/]"
  console.print(f"\n{i}. {sg.title} ({sg.recommended_agent} {status})")
  ```
- Change:
  - `sg.recommended_agent` → `sg.assigned_agent`
  - `sg.agent_exists` → remove check or add property to Subgoal model

**R8.2** Subgoal display MUST show assigned_agent without existence check
- File: `packages/cli/src/aurora_cli/commands/plan.py`
- Change: Simplify to just show `sg.assigned_agent` without validation
- Alternative: Add `agent_exists` property to Subgoal model that checks agent registry

### R9: Documentation Updates

**R9.1** New guide MUST document the 3-step planning workflow
- File: `docs/guides/3-SIMPLE-STEPS.md`
- Content: Step-by-step guide for aur goals → /aur:plan → /aur:implement flow
- Include: "Why This Flow?" section explaining code-aware vs non-code-aware paths
- Include: "Before You Start" section for `aur init` and `project.md` setup (one-time)
- Include: Optional /aur:tasks for PRD iteration
- Include: Flow diagram, quick reference table, example walkthrough

**R9.2** README MUST include updated planning workflow diagram
- File: `README.md`
- Section: Planning Workflow
- Change: Emphasize `aur goals` as code-aware (searches codebase, maps source_file)
- Change: Note that skipping `aur goals` is valid but less structured
- Change: Update diagram to show "Setup (once)" step with `aur init` and `project.md`
- Change: Show 3 steps with /aur:tasks as optional
- Add: Link to 3-SIMPLE-STEPS.md guide

**R9.3** README Commands Reference MUST include /aur:tasks
- File: `README.md`
- Section: Commands Reference table
- Change: Add `/aur:tasks [plan-id]` with description "Regenerate tasks from PRD"

## Non-Goals

1. **No spec migration tool** - Users can manually delete old spec files if desired
2. **No automatic PRD content parsing** - tasks.md generation relies on user following PRD structure
3. **No multi-file source_file support** - Single file per subgoal is sufficient
4. **No changes to aur:implement** - Implementation skill remains unchanged
5. **No changes to aur:archive** - Archive skill remains unchanged (already doesn't require specs)
6. **No file field in tasks.md** - Code-awareness comes from `aur goals` (source_file in goals.json), not from tasks.md structure. Users who skip `aur goals` accept less structured file mapping.

## Constraints

- **Fine-tune, don't replace**: All template changes are refinements to existing OpenSpec templates, not rewrites
- Must maintain compatibility with all 20 AI coding tools (Claude, Cursor, Gemini, etc.)
- Must not break existing goals.json files (source_file is optional)
- Must keep existing COMMAND_TEMPLATES dict structure for configurator compatibility
- Template changes must be additive (new fields) not destructive (removing existing fields)

## Success Metrics

1. `aur init --config` generates `/aur:plan` and `/aur:tasks` commands
2. Generated skill instructions contain NO references to non-existent CLI commands
3. Plan creation produces 5 files (plan.md, prd.md, design.md, agents.json, tasks.md) - NO specs/
4. goals.json includes source_file field when LLM provides file matching

## File Change Summary

| File | Changes |
|------|---------|
| `packages/cli/src/aurora_cli/templates/slash_commands.py` | Add TASKS_TEMPLATE, fix command refs |
| `packages/cli/src/aurora_cli/planning/core.py` | Remove spec generation, remove slug numbers, override existing folders |
| `packages/cli/src/aurora_cli/planning/models.py` | Add source_file to SubgoalData |
| `packages/cli/src/aurora_cli/planning/decompose.py` | Extract source_file from LLM response |
| `packages/cli/src/aurora_cli/commands/plan.py` | Remove spec refs, fix agent_exists/recommended_agent bug |
| All configurators in `configurators/slash/` | Add "tasks" command |
| `packages/reasoning/src/aurora_reasoning/prompts/decompose.py` | Add source_file to subgoal JSON schema |
| `packages/reasoning/src/aurora_reasoning/decompose.py` | Accept optional source_file in validation |
| `docs/guides/3-SIMPLE-STEPS.md` | New guide for 3-step planning workflow |
| `README.md` | Updated planning workflow diagram, added /aur:tasks to commands |

## Acceptance Criteria

- [ ] `grep -r "aur plan validate" packages/` returns no results
- [ ] `grep -r "plan list --specs" packages/` returns no results
- [ ] `grep -r "show.*--deltas-only" packages/cli/` returns no results
- [ ] `COMMAND_TEMPLATES` contains "plan" and "tasks"
- [ ] `aur plan create "test"` creates 5 files in plan directory (no specs/)
- [ ] `aur plan view <id>` works without AttributeError (agent_exists fixed)
- [ ] SubgoalData has source_file field in Pydantic model
- [ ] SOAR DecomposePromptTemplate JSON schema includes source_file field
- [ ] SOAR decompose validation accepts optional source_file without error
- [ ] Running `aur init --config` creates aur:plan and aur:tasks command files
- [ ] New plan folders use slug only (no number prefix): `improve-aur-mem-search` not `0005-improve-aur-mem-search`
- [ ] Re-running `aur goals` with same query overwrites existing folder
- [ ] `docs/guides/3-SIMPLE-STEPS.md` exists with flow diagram and quick reference
- [ ] README Planning Workflow section shows "Setup (once)" with project.md + 3 steps + /aur:tasks as optional
- [ ] README Commands Reference includes /aur:tasks entry
- [ ] tasks.md template includes `tdd: yes|no` and `verify:` fields per task
- [ ] PLAN_STEPS Step 1 emphasizes goals.json as recommended but continues without it
