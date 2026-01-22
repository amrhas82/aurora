"""AGENTS.md template for Aurora planning system.

Rebranded from OpenSpec to Aurora.
This template contains the instructions for AI coding assistants using
Aurora for plan-driven development.
"""

AGENTS_TEMPLATE = """# Aurora Instructions

Instructions for AI coding assistants using Aurora for plan-driven development.

## TL;DR Quick Checklist

- Search existing work: `aur plan list`, `aur mem search "<query>"`
- Decide scope: new plan vs modify existing plan
- Pick a unique `plan-id`: kebab-case, verb-led (`add-`, `update-`, `remove-`, `refactor-`)
- Scaffold: `plan.md`, `prd.md`, `tasks.md`, `agents.json`
- Validate: `aur plan show <plan-id>` and review
- Request approval: Do not start implementation until plan is approved

## Three-Stage Workflow

### Stage 1: Creating Plans
Create a plan when you need to:
- Add features or functionality
- Make breaking changes (API, schema)
- Change architecture or patterns
- Optimize performance (changes behavior)
- Update security patterns

Triggers (examples):
- "Help me create a plan"
- "Help me plan a change"
- "I want to create a plan"
- "I want to implement a feature"

Skip plan for:
- Bug fixes (restore intended behavior)
- Typos, formatting, comments
- Dependency updates (non-breaking)
- Configuration changes
- Tests for existing behavior

**Workflow**
1. Review `.aurora/project.md` and `aur plan list` to understand current context.
2. Choose a unique verb-led `plan-id` and scaffold `plan.md`, `prd.md`, `tasks.md`, `agents.json` under `.aurora/plans/active/<id>/`.
3. Draft the plan with high-level goals and detailed requirements.
4. Run `aur plan show <id>` and review before sharing.

### Stage 2: Implementing Plans
Track these steps as TODOs and complete them one by one.
1. **Read plan.md** - Understand what's being built
2. **Read prd.md** - Review detailed requirements
3. **Read tasks.md** - Get implementation checklist
4. **Implement tasks sequentially** - Complete in order
5. **Confirm completion** - Ensure every item in `tasks.md` is finished before updating statuses
6. **Update checklist** - After all work is done, set every task to `- [x]` so the list reflects reality
7. **Approval gate** - Do not start implementation until the plan is reviewed and approved

### Stage 3: Archiving Plans
After completion, archive the plan:
- Use `aur plan archive <plan-id>` to move to archive
- Plans move to `.aurora/plans/archive/YYYY-MM-DD-<plan-id>/`

## Before Any Task

**Context Checklist:**
- [ ] Read `.aurora/project.md` for conventions
- [ ] Run `aur plan list` to see active plans
- [ ] Check pending plans for conflicts
- [ ] Use `aur mem search "<query>"` to find relevant code

**Before Creating Plans:**
- Always check if a similar plan already exists
- Prefer modifying existing plans over creating duplicates
- Use `aur plan show <plan-id>` to review current state
- If request is ambiguous, ask 1-2 clarifying questions before scaffolding

### Search Guidance
- Enumerate plans: `aur plan list`
- Show plan details: `aur plan show <plan-id>`
- Search codebase: `aur mem search "<query>"` or `aur query "<question>"`
- Full-text search: `rg -n "pattern" .`

## Quick Start

### CLI Commands

```bash
# Essential commands
aur plan list                  # List active plans
aur plan show <plan-id>        # Display plan details
aur plan create "Goal"         # Create new plan
aur plan archive <plan-id>     # Archive after completion

# Memory/search commands
aur mem index .                # Index codebase
aur mem search "<query>"       # Search indexed code
aur query "<question>"         # Query with context

# Project management
aur init                       # Initialize Aurora
aur init --config              # Update tool configurations
```

## Directory Structure

```
.aurora/
├── project.md              # Project conventions
├── plans/
│   ├── active/             # Plans being worked on
│   │   └── [plan-id]/
│   │       ├── plan.md     # High-level decomposition
│   │       ├── prd.md      # Detailed requirements
│   │       ├── tasks.md    # Implementation checklist
│   │       └── agents.json # Machine-readable metadata
│   └── archive/            # Completed plans
├── memory.db               # Indexed code database
├── logs/                   # Aurora logs
└── cache/                  # Cached data
```

## Creating Plans

### Decision Tree

```
New request?
├─ Bug fix restoring expected behavior? → Fix directly
├─ Typo/format/comment? → Fix directly
├─ New feature/capability? → Create plan
├─ Breaking change? → Create plan
├─ Architecture change? → Create plan
└─ Unclear? → Create plan (safer)
```

### Plan Structure

1. **Create directory:** `.aurora/plans/active/<plan-id>/` (kebab-case, verb-led, unique)

2. **Write plan.md:**
```markdown
# Plan: [Brief description]

## Goal
[1-2 sentences on what we're building]

## Subgoals
1. [First subgoal]
2. [Second subgoal]
3. [Third subgoal]

## Success Criteria
- [Measurable outcome 1]
- [Measurable outcome 2]
```

3. **Write prd.md:**
```markdown
# PRD: [Title]

## Summary
[Brief description of the feature/change]

## Requirements

### Functional Requirements
- FR-1: [Requirement]
- FR-2: [Requirement]

### Non-Functional Requirements
- NFR-1: [Performance/security/etc]

## Acceptance Criteria
- AC-1: [Testable criterion]
- AC-2: [Testable criterion]
```

4. **Create tasks.md:**
```markdown
## 1. Implementation
- [ ] 1.1 Create database schema
- [ ] 1.2 Implement API endpoint
- [ ] 1.3 Add frontend component
- [ ] 1.4 Write tests
```

5. **Create agents.json:**
```json
{
  "plan_id": "0001-feature-name",
  "subgoals": [
    {
      "id": "sg-1",
      "description": "First subgoal",
      "agent": "code-developer"
    }
  ]
}
```

## Best Practices

### Simplicity First
- Default to <100 lines of new code
- Single-file implementations until proven insufficient
- Avoid frameworks without clear justification
- Choose boring, proven patterns

### Complexity Triggers
Only add complexity with:
- Performance data showing current solution too slow
- Concrete scale requirements (>1000 users, >100MB data)
- Multiple proven use cases requiring abstraction

### Clear References
- Use `file.ts:42` format for code locations
- Reference plans as `.aurora/plans/active/<plan-id>/`
- Link related plans and PRs

### Plan ID Naming
- Use kebab-case, short and descriptive: `add-two-factor-auth`
- Prefer verb-led prefixes: `add-`, `update-`, `remove-`, `refactor-`
- Ensure uniqueness; if taken, append `-2`, `-3`, etc.

## Tool Selection Guide

| Task | Tool | Why |
|------|------|-----|
| Find files by pattern | Glob | Fast pattern matching |
| Search code content | Grep | Optimized regex search |
| Read specific files | Read | Direct file access |
| Explore unknown scope | Task | Multi-step investigation |
| Search indexed code | `aur mem search` | Semantic search |

## Error Recovery

### Plan Conflicts
1. Run `aur plan list` to see active plans
2. Check for overlapping goals
3. Coordinate with plan owners
4. Consider combining plans

### Missing Context
1. Read project.md first
2. Check related plans
3. Review recent archives
4. Ask for clarification

## Quick Reference

### Stage Indicators
- `plans/active/` - In progress, not yet built
- `plans/archive/` - Completed plans

### File Purposes
- `plan.md` - Why and what (high-level)
- `prd.md` - Detailed requirements
- `tasks.md` - Implementation steps
- `agents.json` - Machine-readable metadata

### CLI Essentials
```bash
aur plan list              # What's in progress?
aur plan show <id>         # View details
aur plan archive <id>      # Mark complete
aur mem search "<query>"   # Find code
```

Remember: Plans are proposals. Keep them simple and focused.
"""


def get_agents_template() -> str:
    """Get the AGENTS.md template.

    Returns:
        AGENTS.md template string

    """
    return AGENTS_TEMPLATE
