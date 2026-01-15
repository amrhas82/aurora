# Aurora Instructions

Instructions for AI coding assistants using Aurora for plan-driven development.

## TL;DR Quick Checklist

- Search existing work: `aur plan list`, `aur mem search "<query>"`
- Decide scope: new plan vs modify existing plan
- Pick a unique `plan-id`: kebab-case, verb-led (`add-`, `update-`, `remove-`, `refactor-`)
- Scaffold: `plan.md`, `tasks.md`, `design.md` (only if needed), and spec deltas per affected capability
- Write deltas: use `## ADDED|MODIFIED|REMOVED Requirements`; include at least one `#### Scenario:` per requirement
- Validate: `aur plan validate [plan-id] --strict` and fix issues
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

Loose matching guidance:
- Contains one of: `plan`, `change`, `spec`
- With one of: `create`, `plan`, `make`, `start`, `help`

Skip plan for:
- Bug fixes (restore intended behavior)
- Typos, formatting, comments
- Dependency updates (non-breaking)
- Configuration changes
- Tests for existing behavior

**Workflow**
1. Review `.aurora/project.md`, `aur plan list`, and `aur plan list --specs` to understand current context.
2. Choose a unique verb-led `plan-id` and scaffold `plan.md`, `tasks.md`, optional `design.md`, and spec deltas under `.aurora/plans/active/<id>/`.
3. Draft spec deltas using `## ADDED|MODIFIED|REMOVED Requirements` with at least one `#### Scenario:` per requirement.
4. Run `aur plan validate <id> --strict` and resolve any issues before sharing the plan.

### Stage 2: Implementing Plans
Track these steps as TODOs and complete them one by one.
1. **Read plan.md** - Understand what's being built
2. **Read design.md** (if exists) - Review technical decisions
3. **Read tasks.md** - Get implementation checklist
4. **Implement tasks sequentially** - Complete in order
5. **Confirm completion** - Ensure every item in `tasks.md` is finished before updating statuses
6. **Update checklist** - After all work is done, set every task to `- [x]` so the list reflects reality
7. **Approval gate** - Do not start implementation until the plan is reviewed and approved

### Stage 3: Archiving Plans
After deployment, create separate PR to:
- Move `plans/active/[name]/` → `plans/archive/YYYY-MM-DD-[name]/`
- Update `specs/` if capabilities changed
- Use `aur plan archive <plan-id> --skip-specs --yes` for tooling-only changes (always pass the plan ID explicitly)
- Run `aur plan validate --strict` to confirm the archived plan passes checks

## Before Any Task

**Context Checklist:**
- [ ] Read relevant specs in `specs/[capability]/spec.md`
- [ ] Check pending plans in `plans/active/` for conflicts
- [ ] Read `.aurora/project.md` for conventions
- [ ] Run `aur plan list` to see active plans
- [ ] Run `aur plan list --specs` to see existing capabilities

**Before Creating Plans:**
- Always check if plan already exists
- Prefer modifying existing plans over creating duplicates
- Use `aur plan show [plan-id]` to review current state
- If request is ambiguous, ask 1–2 clarifying questions before scaffolding

### Search Guidance
- Enumerate plans: `aur plan list`
- Enumerate specs: `aur plan list --specs`
- Show details:
  - Plan: `aur plan show <plan-id>` (use `--json` for filters)
  - Spec: `aur plan show <spec-id> --type spec`
- Full-text search (use ripgrep): `rg -n "Requirement:|Scenario:" .aurora/specs`

## Quick Start

### CLI Commands

```bash
# Essential commands
aur plan list                  # List active plans
aur plan list --specs          # List specifications
aur plan show [item]           # Display plan or spec
aur plan validate [item]       # Validate plans or specs
aur plan archive <plan-id> [--yes|-y]   # Archive after deployment

# Memory/search commands
aur mem index .                # Index codebase
aur mem search "<query>"       # Search indexed code

# Project management
aur init [path]                # Initialize Aurora
aur init --config              # Update instruction files

# Interactive mode
aur plan show                  # Prompts for selection
aur plan validate              # Bulk validation mode

# Debugging
aur plan show [plan] --json --deltas-only
aur plan validate [plan] --strict
```

### Command Flags

- `--json` - Machine-readable output
- `--type plan|spec` - Disambiguate items
- `--strict` - Comprehensive validation
- `--no-interactive` - Disable prompts
- `--skip-specs` - Archive without spec updates
- `--yes`/`-y` - Skip confirmation prompts (non-interactive archive)

## Directory Structure

```
.aurora/
├── project.md              # Project conventions
├── specs/                  # Current truth - what IS built
│   └── [capability]/       # Single focused capability
│       ├── spec.md         # Requirements and scenarios
│       └── design.md       # Technical patterns
├── plans/                  # Plans - what SHOULD change
│   ├── active/
│   │   └── [plan-name]/
│   │       ├── plan.md     # Why, what, impact (OpenSpec sections)
│   │       ├── tasks.md    # Implementation checklist with @agent
│   │       ├── design.md   # Technical decisions (optional)
│   │       ├── goals.json  # From aur goals (if provided)
│   │       └── specs/      # Delta changes
│   │           └── [capability]/
│   │               └── spec.md # ADDED/MODIFIED/REMOVED
│   └── archive/            # Completed plans
├── memory.db               # Indexed code database
└── checkpoints/            # Session checkpoints
```

## Creating Plans

### Decision Tree

```
New request?
├─ Bug fix restoring spec behavior? → Fix directly
├─ Typo/format/comment? → Fix directly
├─ New feature/capability? → Create plan
├─ Breaking change? → Create plan
├─ Architecture change? → Create plan
└─ Unclear? → Create plan (safer)
```

### Plan Structure

1. **Create directory:** `plans/active/[plan-id]/` (kebab-case, verb-led, unique)

2. **Write plan.md** (OpenSpec sections):
```markdown
# Plan: [Brief description]

## Plan ID
`{plan-id}`

## Summary
[1-2 sentences]

## Goals Context
> Source: `goals.json` (if provided, otherwise omit)

| Subgoal | Agent | Files | Dependencies |
|---------|-------|-------|--------------|
| [title] | @agent-id | [files] | [deps] |

## Problem Statement
[Current state, pain points]

## Proposed Solution
[What changes]

## Benefits
[Why this helps]

## Scope
### In Scope
- [Included]

### Out of Scope
- [Excluded]

## Dependencies
[Systems, files, plans]

## Implementation Strategy
[Phased approach]

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|

## Success Criteria
- [ ] [Outcome]

## Open Questions
1. [Question] - **Recommendation**: [answer]
```

3. **Create spec deltas:** `specs/[capability]/spec.md`
```markdown
## ADDED Requirements
### Requirement: New Feature
The system SHALL provide...

#### Scenario: Success case
- **WHEN** user performs action
- **THEN** expected result

## MODIFIED Requirements
### Requirement: Existing Feature
[Complete modified requirement]

## REMOVED Requirements
### Requirement: Old Feature
**Reason**: [Why removing]
**Migration**: [How to handle]
```
If multiple capabilities are affected, create multiple delta files under `plans/active/[plan-id]/specs/<capability>/spec.md`—one per capability.

4. **Create tasks.md:**
```markdown
## Phase 1: [Name]
- [ ] 1.1 Task description
  <!-- @agent: @full-stack-dev -->
  - Details
  - **Validation**: How to verify

## Phase 2: [Name]
- [ ] 2.1 Next task
  <!-- @agent: @qa-test-architect -->
  - Details
```

5. **Create design.md when needed:**
Create `design.md` if any of the following apply; otherwise omit it:
- Cross-cutting change (multiple services/modules) or a new architectural pattern
- New external dependency or significant data model changes
- Security, performance, or migration complexity
- Ambiguity that benefits from technical decisions before coding

## Spec File Format

### Critical: Scenario Formatting

**CORRECT** (use #### headers):
```markdown
#### Scenario: User login success
- **WHEN** valid credentials provided
- **THEN** return JWT token
```

**WRONG** (don't use bullets or bold):
```markdown
- **Scenario: User login**  ❌
**Scenario**: User login     ❌
### Scenario: User login      ❌
```

Every requirement MUST have at least one scenario.

### Requirement Wording
- Use SHALL/MUST for normative requirements (avoid should/may unless intentionally non-normative)

### Delta Operations

- `## ADDED Requirements` - New capabilities
- `## MODIFIED Requirements` - Changed behavior
- `## REMOVED Requirements` - Deprecated features
- `## RENAMED Requirements` - Name changes

## Troubleshooting

### Common Errors

**"Plan must have at least one delta"**
- Check `plans/active/[name]/specs/` exists with .md files
- Verify files have operation prefixes (## ADDED Requirements)

**"Requirement must have at least one scenario"**
- Check scenarios use `#### Scenario:` format (4 hashtags)
- Don't use bullet points or bold for scenario headers

### Validation Tips

```bash
# Always use strict mode for comprehensive checks
aur plan validate [plan] --strict

# Debug delta parsing
aur plan show [plan] --json | jq '.deltas'
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
- Reference specs as `specs/auth/spec.md`
- Link related plans and PRs

### Capability Naming
- Use verb-noun: `user-auth`, `payment-capture`
- Single purpose per capability
- 10-minute understandability rule
- Split if description needs "AND"

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
2. Check for overlapping specs
3. Coordinate with plan owners
4. Consider combining plans

### Validation Failures
1. Run with `--strict` flag
2. Check JSON output for details
3. Verify spec file format
4. Ensure scenarios properly formatted

### Missing Context
1. Read project.md first
2. Check related specs
3. Review recent archives
4. Ask for clarification

## Quick Reference

### Stage Indicators
- `plans/active/` - Proposed, not yet built
- `specs/` - Built and deployed
- `plans/archive/` - Completed plans

### File Purposes
- `plan.md` - Why and what (OpenSpec sections)
- `tasks.md` - Implementation steps with @agent
- `design.md` - Technical decisions
- `spec.md` - Requirements and behavior
- `goals.json` - From aur goals (agent assignments, memory context)

### CLI Essentials
```bash
aur plan list              # What's in progress?
aur plan show [item]       # View details
aur plan validate --strict # Is it correct?
aur plan archive <plan-id> [--yes|-y]  # Mark complete
```

Remember: Specs are truth. Plans are proposals. Keep them in sync.
