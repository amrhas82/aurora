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
1. Review `.aurora/project.md`, run `aur plan list` to see existing plans, and inspect related code or docs (e.g., via `rg`/`ls`) to ground the plan in current behaviour; note any gaps that require clarification.
   - **If input is a `goals.json` file (recommended for code-aware planning)**: Read it and populate the Goals Context table with subgoals, agents, files, and dependencies. Goals.json provides code-aware context including source_file mappings for each subgoal.
   - **If input is a prompt (valid but less structured)**: Continue with prompt-based planning. Run `aur agents list` to see available agents. Assign agents to tasks as you plan. Note: Agent searches will happen on-the-fly during implementation rather than upfront.
   - Both paths are valid; goals.json is recommended for production work as it grounds planning in actual codebase structure.
2. Choose a unique verb-led `plan-id` and generate artifacts in this order under `.aurora/plans/active/<id>/`:
   - First: `plan.md` (overview and strategy)
   - Second: `prd.md` (detailed product requirements)
   - Third: `design.md` (when needed - technical architecture)
   - Fourth: `agents.json` (agent assignments)
   - Last: `tasks.md` (depends on PRD content, generated after all other artifacts)
   Note: tasks.md is generated last because it needs complete PRD details to create accurate task breakdowns.
3. Map the change into concrete capabilities or requirements, breaking multi-scope efforts into distinct spec deltas with clear relationships and sequencing.
4. Capture architectural reasoning in `design.md` when the solution spans multiple systems, introduces new patterns, or demands trade-off discussion before committing to specs.
5. Draft spec deltas in `.aurora/plans/active/<id>/specs/<capability>/spec.md` (one folder per capability) using `## ADDED|MODIFIED|REMOVED Requirements` with at least one `#### Scenario:` per requirement and cross-reference related capabilities when relevant.
6. Draft `tasks.md` with `<!-- @agent: @name -->` comment after each parent task. Agent assignment priority: goals.json > agent registry match > LLM inference.
7. Review plan with `aur plan view <id>` and ensure all tasks are well-defined before sharing the plan.

**Reference**
- Use `aur plan view <id> --format json` to inspect plan details in JSON format.
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

**agents.json Template** (plan metadata with subgoals):
```json
{
  "plan_id": "unique-plan-identifier",
  "goal": "Original goal statement describing what needs to be achieved",
  "status": "active",
  "complexity": "moderate",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Brief subgoal title",
      "description": "Detailed subgoal description explaining what needs to be done",
      "agent_id": "@code-developer",
      "status": "pending",
      "dependencies": []
    }
  ]
}
```

**agents.json Schema:**
- **plan_id** (required): Unique identifier for the plan
- **goal** (required): Original goal statement (10-500 chars)
- **status** (required): One of: active, completed, archived, failed
- **complexity** (optional): One of: simple, moderate, complex
- **created_at** (required): ISO 8601 timestamp (UTC)
- **updated_at** (required): ISO 8601 timestamp (UTC)
- **subgoals** (required): Array of subgoal objects (1-20 items)
  - **id**: Subgoal identifier (format: sg-N)
  - **title**: Brief subgoal title (5-100 chars, imperative form)
  - **description**: Detailed description (10-500 chars)
  - **agent_id**: Recommended agent (format: @agent-name)
  - **status**: One of: pending, in_progress, completed, blocked
  - **dependencies**: Array of subgoal IDs that must complete first

**Full schema reference:** `packages/planning/src/aurora_planning/schemas/agents.schema.json`


$ARGUMENTS
<!-- AURORA:END -->
