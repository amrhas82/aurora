# Aurora Planning: 3 Simple Steps

Turn any goal into implemented code with **memory-aware planning**.

**Time Required**: 10-30 minutes depending on complexity
**Prerequisites**: Project initialized with `aur init`

---

## Why This Flow?

| Approach | Code-Aware | File Mapping | Best For |
|----------|------------|--------------|----------|
| **`aur goals` → `/aur:plan` → `/aur:implement`** | ✓ Yes | Automatic (source_file per subgoal) | Production work, complex features |
| `/aur:plan` → `/aur:implement` (skip goals) | ✗ No | Manual (agent searches on the fly) | Quick prototypes, simple tasks |

**`aur goals` searches your indexed codebase** and maps each subgoal to relevant source files. This context flows through the entire pipeline, making implementation more accurate.

---

## Before You Start: Initialize Project (Once)

Run this once per project to set up Aurora:

```bash
cd your-project/
aur init
```

**What it creates:**
- `.aurora/project.md` - Project context (edit this to describe your project)
- `.aurora/memory.db` - Memory database
- `.aurora/config.json` - Project configuration

**Important:** Edit `.aurora/project.md` to describe your project's purpose, architecture, and conventions. This context is used by planning commands to generate better plans.

```bash
# Index your codebase for memory-aware planning
aur mem index .
```

---

## The Flow

```
Step 1                    Step 2                   Step 3
Terminal                  Slash Command            Slash Command
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   aur goals     │  ->  │   /aur:plan     │  ->  │  /aur:implement │
│   "Add feature" │      │   [plan-id]     │      │   [plan-id]     │
└─────────────────┘      └─────────────────┘      └─────────────────┘
        │                        │                        │
        v                        v                        v
   goals.json               5 artifacts:            Code changes
   - subgoals               - plan.md               - validated
   - agent assignments      - prd.md                - tested
   - capability gaps        - design.md
   - source files           - agents.json
                            - tasks.md
                                 │
                                 v (optional)
                        ┌─────────────────┐
                        │   /aur:tasks    │  <- Edit prd.md, regenerate tasks
                        │   [plan-id]     │
                        └─────────────────┘
```

---

## Step 1: Decompose Your Goal (Terminal)

Use `aur goals` to break down any goal into subgoals with agent assignments.

```bash
aur goals "Add user authentication with JWT tokens" -t claude
```

**What happens:**
1. Aurora searches your codebase for relevant context
2. Decomposes the goal into actionable subgoals
3. Matches each subgoal to your existing agents
4. Detects capability gaps (missing agents)
5. Identifies relevant source files per subgoal

**Output:**
```
╭─────────────────────── Plan Decomposition Summary ────────────────────────╮
│ Subgoals: 4                                                               │
│                                                                           │
│   [++] Create JWT token generation utility: @code-developer               │
│        Source: packages/auth/src/token.py                                 │
│   [++] Add authentication middleware: @code-developer                     │
│        Source: packages/api/src/middleware.py                             │
│   [+] Design token refresh flow: @system-architect                        │
│        Source: docs/architecture/auth.md                                  │
│   [++] Write authentication tests: @quality-assurance                     │
│        Source: tests/unit/auth/                                           │
╰───────────────────────────────────────────────────────────────────────────╯

╭───────────────────────────── Summary ─────────────────────────────────────╮
│ Agent Matching: 3 excellent, 1 acceptable                                 │
│ Gaps Detected: 0 subgoals need attention                                  │
│ Context: 12 files (avg relevance: 0.75)                                   │
│ Complexity: COMPLEX                                                       │
│                                                                           │
│ Created: .aurora/plans/active/add-user-authentication/goals.json          │
╰───────────────────────────────────────────────────────────────────────────╯
```

**Result:** `goals.json` created in `.aurora/plans/active/<plan-id>/`

---

## Step 2: Generate Plan Artifacts (Slash Command)

Run `/aur:plan` in your AI coding tool (Claude Code, Cursor, etc.).

```
/aur:plan add-user-authentication
```

Or if you have `goals.json` open:

```
/aur:plan goals.json
```

**What happens:**
1. Reads the goals.json decomposition
2. Generates 5 plan artifacts in order:
   - `plan.md` - High-level implementation plan
   - `prd.md` - Product requirements document
   - `design.md` - Technical design decisions
   - `agents.json` - Agent assignments with status
   - `tasks.md` - Ordered task list for implementation

**Artifacts generated:**
```
.aurora/plans/active/add-user-authentication/
├── goals.json      # From Step 1
├── plan.md         # Implementation overview
├── prd.md          # Requirements & acceptance criteria
├── design.md       # Architecture decisions
├── agents.json     # Agent routing
└── tasks.md        # Task breakdown
```

---

## Step 2.5: Iterate on PRD (Optional)

Need to refine the requirements? Edit `prd.md` directly, then regenerate tasks:

```
/aur:tasks add-user-authentication
```

**What happens:**
1. Reads your edited `prd.md`
2. Reads `goals.json` and `agents.json` for context
3. Regenerates `tasks.md` to match updated requirements

**When to use:**
- After stakeholder feedback on PRD
- When requirements change mid-planning
- To add/remove scope before implementation

This avoids regenerating all artifacts - just updates the task list.

---

## Step 3: Implement the Plan (Slash Command)

Run `/aur:implement` to execute tasks with validation.

```
/aur:implement add-user-authentication
```

**What happens:**
1. Reads `tasks.md` for ordered task list
2. Executes each task sequentially
3. Validates changes against acceptance criteria
4. Updates `agents.json` status as tasks complete

**Features:**
- Stop gates for feature creep detection
- Dangerous command warnings
- Progress tracking in agents.json
- Rollback on validation failure

---

## Step 4: Archive When Done

After implementation is complete:

```
/aur:archive add-user-authentication
```

**What happens:**
- Moves plan from `active/` to `archived/`
- Preserves all artifacts for reference
- Clears the active plan slot

---

## Quick Reference

| Step | Command | Location | Output |
|------|---------|----------|--------|
| 1 | `aur goals "goal" -t <tool>` | Terminal | goals.json |
| 2 | `/aur:plan <plan-id>` | Slash | 5 artifacts |
| 2.5 | `/aur:tasks <plan-id>` | Slash | tasks.md (regenerated) |
| 3 | `/aur:implement <plan-id>` | Slash | Code changes |
| 4 | `/aur:archive <plan-id>` | Slash | Archived plan |

---

## Example: Full Workflow

```bash
# Terminal: Decompose goal with memory context
$ aur goals "Add rate limiting to API endpoints" -t claude
  Created: .aurora/plans/active/add-rate-limiting/goals.json

# Slash command: Generate plan artifacts
/aur:plan add-rate-limiting
  Generated: plan.md, prd.md, design.md, agents.json, tasks.md

# (Optional) Edit prd.md to adjust requirements...
# Then regenerate tasks:
/aur:tasks add-rate-limiting
  Regenerated: tasks.md

# Slash command: Implement with validation
/aur:implement add-rate-limiting
  Completed: 8/8 tasks

# Slash command: Archive completed plan
/aur:archive add-rate-limiting
  Archived to: .aurora/plans/archived/add-rate-limiting/
```

---

## Tips

1. **Index first**: Always run `aur mem index .` before planning for best context matching

2. **Check agent gaps**: If `aur goals` shows capability gaps, create the missing agents before `/aur:plan`

3. **Iterate early**: Use `/aur:tasks` to refine requirements before starting implementation

4. **Review tasks.md**: Check the generated task order makes sense before `/aur:implement`

5. **Plan IDs are slugs**: Use the folder name (e.g., `add-rate-limiting`) as the plan-id

---

## Related Guides

- [Commands Reference](./COMMANDS.md) - Full CLI reference
- [SOAR Architecture](../reference/SOAR_ARCHITECTURE.md) - How decomposition works
- [Tools Guide](./TOOLS_GUIDE.md) - Supported AI coding tools
