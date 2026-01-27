---
name: Aurora: Implement
description: Execute plan tasks [plan-id]
argument-hint: plan ID to implement
category: Aurora
tags: [aurora, planning, implementation]
---
<!-- AURORA:START -->
**Guardrails**
- Favor straightforward, minimal implementations first and add complexity only when requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `.aurora/AGENTS.md` if you need additional Aurora conventions or clarifications.

**Usage**
Execute plan tasks sequentially with progress tracking.

**What it does**
1. Reads plan.md, tasks.md, and specs/ from plan directory
2. Executes tasks in order, marking each `- [x]` when complete
3. Validates completed work against spec scenarios when available

**Commands**
```bash
# Implement specific plan
/aur:implement 0001-add-auth

# Interactive selection (lists active plans)
/aur:implement
```

**Workflow**
1. Read `.aurora/plans/active/<plan-id>/plan.md` for context
2. Read `.aurora/plans/active/<plan-id>/tasks.md` for work items
3. Check `specs/` for formal requirements and scenarios (if exists)
4. For each task:
   - Execute the implementation
   - Run validation (tests, checks) from task description
   - Mark task complete: `- [ ]` → `- [x]`
5. On completion: suggest `/aur:archive <plan-id>`

**Validation**
- If `specs/<capability>/spec.md` exists, use scenarios as acceptance criteria
- Mark validation pass/fail in task completion notes
- Warn if spec scenarios not fully covered

**Reference**
- `aur plan list` - See active plans
- `aur plan show <id>` - View plan details

$ARGUMENTS
<!-- AURORA:END -->
