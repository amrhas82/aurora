---
description: Execute plan tasks [plan-id]
---
The user wants to implement a plan. Use the aurora instructions for implementation.
<UserRequest>
  $ARGUMENTS
</UserRequest>
<!-- AURORA:START -->
**Guardrails**
- Favor straightforward, minimal implementations first and add complexity only when requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `.aurora/AGENTS.md` if you need additional Aurora conventions or clarifications.

**Usage**
Execute plan tasks sequentially with checkpoint support.

**What it does**
1. Reads plan.md, tasks.md, and specs/ from plan directory
2. Executes tasks in order, marking each `- [x]` when complete
3. Saves checkpoint after each task for resume capability
4. Validates completed work against spec scenarios when available

**Commands**
```bash
# Implement specific plan
/aur:implement 0001-add-auth

# Resume interrupted implementation
/aur:implement 0001-add-auth --resume

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
   - Save checkpoint to `.aurora/checkpoints/`
5. On completion: suggest `/aur:archive <plan-id>`

**Resume Mode**
When `--resume` is passed:
1. Read latest checkpoint from `.aurora/checkpoints/`
2. Skip already-completed tasks (marked `- [x]`)
3. Continue from first incomplete task

**Validation**
- If `specs/<capability>/spec.md` exists, use scenarios as acceptance criteria
- Mark validation pass/fail in task completion notes
- Warn if spec scenarios not fully covered

**Reference**
- `aur plan list` - See active plans
- `aur plan show <id>` - View plan details
- Checkpoints stored in `.aurora/checkpoints/<plan-id>/`
<!-- AURORA:END -->
