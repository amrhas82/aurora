---
name: Aurora: Plan
description: Create implementation plan with agent delegation [goal]
argument-hint: request or feature description
category: Aurora
tags: [aurora, planning]
---
<!-- AURORA:START -->
**Guardrails**
- Favor straightforward, minimal implementations first and add complexity only when requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `.aurora/AGENTS.md` if you need additional Aurora conventions or clarifications.
- Identify any vague or ambiguous details and ask the necessary follow-up questions before editing files.
- Do not write any code during the planning stage. Only create design documents (plan.md, tasks.md, design.md, and spec deltas). Implementation happens in the implement stage after approval.

**Steps**
1. Review `.aurora/project.md`, run `aur plan list` and `aur plan list --specs`, and inspect related code or docs (e.g., via `rg`/`ls`) to ground the plan in current behaviour; note any gaps that require clarification.
   - **If input is a `goals.json` file**: Read it and populate the Goals Context table with subgoals, agents, files, and dependencies.
   - **If input is a prompt**: Run `aur agents list` to see available agents. Assign agents to tasks as you plan.
2. Choose a unique verb-led `plan-id` and scaffold `plan.md`, `tasks.md`, and `design.md` (when needed) under `.aurora/plans/active/<id>/`.
3. Map the change into concrete capabilities or requirements, breaking multi-scope efforts into distinct spec deltas with clear relationships and sequencing.
4. Capture architectural reasoning in `design.md` when the solution spans multiple systems, introduces new patterns, or demands trade-off discussion before committing to specs.
5. Draft spec deltas in `.aurora/plans/active/<id>/specs/<capability>/spec.md` (one folder per capability) using `## ADDED|MODIFIED|REMOVED Requirements` with at least one `#### Scenario:` per requirement and cross-reference related capabilities when relevant.
6. Draft `tasks.md` with `<!-- @agent: @name -->` comment after each parent task. Agent assignment priority: goals.json > agent registry match > LLM inference.
7. Validate with `aur plan validate <id> --strict` and resolve every issue before sharing the plan.

**Reference**
- Use `aur plan show <id> --json --deltas-only` or `aur plan show <spec> --type spec` to inspect details when validation fails.
- Search existing requirements with `rg -n "Requirement:|Scenario:" .aurora/specs` before writing new ones.
- Explore the codebase with `rg <keyword>`, `ls`, or direct file reads so plans align with current implementation realities.

**plan.md Template** (matches OpenSpec proposal.md sections):
```markdown
# Plan: [Brief description]

## Plan ID
`{plan-id}`

## Summary
[1-2 sentences]

## Goals Context
> Source: `goals.json` (if provided, otherwise omit this section)

| Subgoal | Agent | Files | Dependencies |
|---------|-------|-------|--------------|
| [title] | @agent-id | [memory_context files] | [dependencies] |

## Problem Statement
[Current state, pain points]

## Proposed Solution
[What changes]

## Benefits
[Why this helps]

## Scope
### In Scope
- [What's included]

### Out of Scope
- [What's excluded]

## Dependencies
[Systems, files, or other plans this depends on]

## Implementation Strategy
[Phased approach with task counts]

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|

## Success Criteria
- [ ] [Measurable outcome]

## Open Questions
1. [Question] - **Recommendation**: [answer]
```

**tasks.md Template** (with @agent per task):
```markdown
## Phase N: [Name]
- [ ] N.1 Task description
  <!-- @agent: @full-stack-dev -->
  - Details
  - **Validation**: How to verify
```

$ARGUMENTS
<!-- AURORA:END -->
