---
name: Aurora: Tasks
description: Regenerate tasks from PRD [plan-id]
argument-hint: plan ID to regenerate tasks for
category: Aurora
tags: [aurora, planning]
---
<!-- AURORA:START -->
**Guardrails**
- Favor straightforward, minimal implementations first and add complexity only when requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `.aurora/AGENTS.md` if you need additional Aurora conventions or clarifications.
- Only regenerate tasks.md. Do not modify plan.md, prd.md, design.md, or agents.json.
- Read prd.md to understand requirements. Read agents.json for agent assignments. Read goals.json for source_file mappings if available.

**Steps**
1. Read `.aurora/plans/active/<plan-id>/prd.md` to understand requirements
2. Read `.aurora/plans/active/<plan-id>/agents.json` for agent assignments
3. Read `.aurora/plans/active/<plan-id>/goals.json` (if exists) for source_file mappings
4. Generate tasks.md with:
   - Task breakdown matching PRD requirements
   - Agent assignments from agents.json (use `<!-- @agent: @name -->` comment after each parent task)
   - TDD hints (tdd: yes|no, verify: command) matching format below
   - Validation steps per task
5. Save updated tasks.md (replaces existing)

**tasks.md Template** (with @agent per task and TDD hints):
```markdown
## Phase N: [Name]
- [ ] N.1 Task description
  <!-- @agent: @code-developer -->
  - tdd: yes|no
  - verify: `command to verify`
  - Details
  - **Validation**: How to verify

**TDD Detection Guidelines:**
- tdd: yes - For models, API endpoints, bug fixes, business logic, data transformations
- tdd: no - For docs, config files, migrations, pure refactors (no behavior change)
- Default: When unsure, use tdd: yes
```

**Purpose**
Regenerate tasks.md after user edits PRD. The PRD is the source of truth for requirements; tasks.md must always reflect current PRD state.

**When to use**
- After editing prd.md to add/remove requirements
- After changing requirement scope or acceptance criteria
- When task breakdown no longer matches PRD structure

$ARGUMENTS
<!-- AURORA:END -->
