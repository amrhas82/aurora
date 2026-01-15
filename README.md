# Aurora

**Memory-Aware LLM Planning Framework**

Lightweight, LLM-agnostic, no-API framework that uses your existing CLI tools and agent configurations.

```bash
pip install aurora-actr
```

---

## What Aurora Does

Aurora answers planning questions without implementing anything:

**"What agents do I need?"** - `aur goals` decomposes any goal into subgoals, assigns agents you have, and identifies capability gaps.

**"How does X work?"** - `aur soar` researches questions by spawning ad-hoc agents with lightweight recovery, synthesizing answers from parallel research.

**"Execute my plan"** - `aur spawn` runs tasks with gate checks for scope creep and safeguards (budget limits, dangerous command detection).

**"Run unattended agent"** - `aur headless` executes agent tasks unattended (Ralph Wiggum mode with max retries).

**"Search my code"** - `aur mem search` searches your indexed codebase using BM25, ACT-R activation, and git signals.

---

## Memory System

Aurora's memory combines multiple signals for intelligent retrieval:

- **BM25 keyword search** - Fast, reliable, local
- **ACT-R activation decay** - Frequently accessed code stays "hot"
- **Git commit history** - Recent changes rank higher
- **Tree-sitter AST** - Understands code structure (functions, classes)
- **SOAR reasoning traces** - Stores past questions and answers

No cloud APIs required for core functionality.

---

## Key Commands

| Command | What It Does |
|---------|--------------|
| `aur goals "Add auth"` | Decompose goal, assign agents, detect gaps |
| `aur soar "How does X work?"` | Research with parallel ad-hoc agents |
| `aur spawn tasks.md` | Execute tasks with safeguards |
| `aur headless tasks.md` | Run unattended (Ralph Wiggum mode with max retries) |
| `aur mem search "query"` | Search indexed memory |
| `aur mem index .` | Index codebase for memory search |

**Slash Commands (Claude Code):**

| Command | What It Does |
|---------|--------------|
| `/aur:plan goals.json` | Generate PRD + tasks from goals |
| `/aur:implement` | Execute tasks with checkpoints |
| `/aur:checkpoint` | Save session context for recovery |
| `/aur:search "query"` | Search memory, use `/aur:get` to read chunks |

---

## Workflows

### Optimum Plan (Memory-Informed)

```
Terminal                    Claude Code              Claude Code
┌─────────────────┐        ┌─────────────────┐      ┌─────────────────┐
│   aur goals     │   ->   │  /aur:plan      │  ->  │  /aur:implement │
│   "Add feature" │        │  goals.json     │      │                 │
└─────────────────┘        └─────────────────┘      └─────────────────┘
        │                          │                        │
        v                          v                        v
   goals.json               PRD + tasks.md            Implemented
   - subgoals               - specs/                  - checkpoints
   - agent assignments      - agent hints             - validation
   - capability gaps        - file hints
```

**When to use:** Large features, complex refactors, anything needing upfront analysis.

### Regular Plan (Direct)

```
Claude Code                          Claude Code
┌─────────────────────────┐         ┌─────────────────┐
│  /aur:plan              │    ->   │  /aur:implement │
│  "Add logout button"    │         │                 │
└─────────────────────────┘         └─────────────────┘
```

**When to use:** Quick features, simple changes, already know what you want.

### Research Flow

```
Terminal
┌─────────────────────────────────────────┐
│  aur soar "How does payment flow work?" │
└─────────────────────────────────────────┘
                    │
                    v
            ┌───────────────┐
            │ Spawns ad-hoc │
            │ agents for    │
            │ parallel      │
            │ research      │
            └───────────────┘
                    │
                    v
        Synthesized answer with citations
```

**When to use:** Understanding codebases, architectural questions, research.

### Execution Flow

```
Terminal
┌───────────────────────────────────────────────────┐
│  aur spawn tasks.md --verbose                     │
└───────────────────────────────────────────────────┘
                        │
                        v
        ┌───────────────────────────────┐
        │ Gate checks:                  │
        │ - Scope creep detection       │
        │ - Budget limits               │
        │ - Dangerous command blocking  │
        └───────────────────────────────┘
                        │
                        v
            Parallel task execution
```

**When to use:** Running generated task lists, batch operations.

---

## Quick Start

```bash
# Install
pip install aurora-actr

# Initialize project
cd your-project/
aur init

# Index codebase
aur mem index .

# Optimum workflow
aur goals "Add user authentication"
# Output: .aurora/plans/0001-add-user-auth/goals.json

# In Claude Code:
/aur:plan goals.json
/aur:implement

# Or research first
aur soar "How is auth currently handled?"
```

---

## Agent Gap Detection

Aurora tells you what specialists you need:

```bash
$ aur goals "Add payment processing"

Subgoals: 5
  sg-1: Set up Stripe SDK (@full-stack-dev)
  sg-2: Create payment endpoints (@full-stack-dev)
  sg-3: Implement checkout UI (@ux-expert)
  sg-4: Configure PCI compliance (@security-engineer -> NOT FOUND)

Gaps detected:
  - Missing @security-engineer
  - Suggested capabilities: ["PCI DSS", "security audit"]
  - Fallback: @full-stack-dev (review required)
```

Works for any goal, not just code:

```bash
$ aur goals "Write a sci-fi novel"

Subgoals: 6
  sg-1: Develop world-building (@worldbuilder -> NOT FOUND)
  sg-2: Create character arcs (@character-designer -> NOT FOUND)
  sg-3: Write plot outline (@story-architect -> NOT FOUND)
  ...

Gaps: 6 specialists needed
```

---

## Memory-Aware Planning

Unlike generic decomposition, Aurora uses your indexed codebase:

```bash
$ aur goals "Add OAuth support" --context src/auth/

Memory search found relevant files:
  - src/auth/login.py (0.92)
  - src/auth/session.py (0.85)
  - src/models/user.py (0.78)

Planning informed by:
  - Existing auth patterns
  - Current session handling
  - User model structure
```

---

## OpenSpec Integration

Aurora extends OpenSpec planning with:

- **File hints** - Suggests files to examine for each task
- **Agent assignments** - Maps tasks to specialists
- **Spec deltas** - Tracks changes to specs across implementation

```
goals.json       ->  /aur:plan  ->  PRD + tasks.md + specs/
(from aur goals)      (OpenSpec)     (with agent + file hints)
```

---

## Session Recovery

`/aur:checkpoint` saves succinct session context:

```bash
# Before compaction or handoff
/aur:checkpoint

# Output: .aurora/checkpoints/session-2026-01-15.md
# Contains: goals, progress, decisions, next steps
```

---

## Configuration

Works with 20+ CLI tools out of the box:

```bash
# Use any tool
aur goals "Add feature" --tool claude
aur goals "Add feature" --tool cursor
aur goals "Add feature" --tool aider

# Set defaults
export AURORA_GOALS_TOOL=claude
export AURORA_GOALS_MODEL=sonnet
```

---

## Installation

**Standard:**
```bash
pip install aurora-actr  # ~520KB
```

**With ML features:**
```bash
pip install aurora-actr[ml]  # +1.9GB for semantic search
```

---

## Documentation

- [Commands Reference](docs/guides/COMMANDS.md) - Full CLI documentation
- [Tools Guide](docs/guides/TOOLS_GUIDE.md) - Architecture and workflows
- [Flows Guide](docs/guides/FLOWS.md) - All workflow patterns
- [Configuration](docs/reference/CONFIG_REFERENCE.md) - Settings reference

---

## Design Philosophy

1. **Query, don't implement** - Analyze and plan before coding
2. **Memory-first** - Use codebase context for informed decisions
3. **Agent-aware** - Match tasks to specialists, detect gaps
4. **LLM-agnostic** - Works with any CLI tool, no vendor lock-in
5. **Local-first** - No cloud APIs required for core features

---

## License

MIT License - See [LICENSE](LICENSE)
