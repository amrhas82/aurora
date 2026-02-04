<div align="center">

<pre>
   █████╗ ██╗   ██╗██████╗  ██████╗ ██████╗  █████╗
  ██╔══██╗██║   ██║██╔══██╗██╔═══██╗██╔══██╗██╔══██╗
  ███████║██║   ██║██████╔╝██║   ██║██████╔╝███████║
  ██╔══██║██║   ██║██╔══██╗██║   ██║██╔══██╗██╔══██║
  ██║  ██║╚██████╔╝██║  ██║╚██████╔╝██║  ██║██║  ██║
  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
 ┳┳┓┏┓┳┳┓┏┓┳┓┓┏  ┏┓┓ ┏┏┓┳┓┏┓  ┏┓┳┓┏┓┳┳┓┏┓┓ ┏┏┓┳┓┓┏
 ┃┃┃┣ ┃┃┃┃┃┣┫┗┫━━┣┫┃┃┃┣┫┣┫┣ ━━┣ ┣┫┣┫┃┃┃┣ ┃┃┃┃┃┣┫┃┫
 ┛ ┗┗┛┛ ┗┗┛┛┗┗┛  ┛┗┗┻┛┛┗┛┗┗┛  ┻ ┛┗┛┗┛ ┗┗┛┗┻┛┗┛┛┗┛┗
Lightweight, private memory and code intelligence for AI coding assistants.
Multi-agent orchestration that runs locally.
</pre>

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/aurora-actr.svg)](https://pypi.org/project/aurora-actr/)

</div>

---

## Summary

### Aurora - Lightweight Private Memory & Multi-Agent Orchestration

- **Private & local** - No API keys, no data leaves your machine. Works with Claude Code, Cursor, 20+ tools
- **Smart Memory** - Indexes code and docs locally. Ranks by recency, relevance, and access patterns
- **Code Intelligence** - LSP-powered: find unused code, check impact before refactoring, semantic search
- **Multi-Agent Orchestration** - Decompose goals, spawn agents, coordinate with recovery and state
- **Execution** - Run task lists with guardrails against dangerous commands and scope creep
- **Friction Analysis** - Extract learned rules from stuck patterns in past sessions

```bash
# New installation
pip install aurora-actr

# Upgrading?
pip install --upgrade aurora-actr
aur --version  # Should show 0.13.2

# Uninstall
pip uninstall aurora-actr

# From source (development)
git clone https://github.com/amrhas82/aurora.git
cd aurora && ./install.sh
```

---

## Core Features

### Smart Memory

`aur mem search` - Memory with activation decay. Indexes your code using:

- **BM25** - Keyword search
- **Git signals** - Recent changes rank higher
- **Tree-sitter/cAST** - Code stored as class/method (Python, TypeScript, Java)
- **LSP enrichment** - Risk level, usage count, complexity (see Code Intelligence below)
- **Markdown indexing** - Search docs, save tokens

```bash
# Terminal
aur mem index .
aur mem search "soar reasoning" --show-scores
Searching memory from /project/.aurora/memory.db...
Found 5 results for 'soar reasoning'

┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Type   ┃ File                   ┃ Name                 ┃ Lines      ┃ Risk   ┃ Git      ┃   Score ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ code   │ core.py                │ generate_goals_json  │ 1091-1175  │ MED    │ 8d ago   │   0.619 │
│ code   │ core.py                │ <chunk>              │ 1473-1855  │ -      │ 1d ago   │   0.589 │
│ code   │ orchestrator.py        │ SOAROrchestrator._c… │ 2141-2257  │ HIGH   │ 1d ago   │   0.532 │
│ code   │ test_goals_startup_pe… │ TestGoalsCommandSta… │ 190-273    │ LOW    │ 1d ago   │   0.517 │
│ code   │ goals.py               │ <chunk>              │ 437-544    │ -      │ 7d ago   │   0.486 │
└────────┴────────────────────────┴──────────────────────┴────────────┴────────┴──────────┴─────────┘
Avg scores: Activation 0.916 | Semantic 0.867 | Hybrid 0.801
Risk: LOW (0-2 refs) | MED (3-10) | HIGH (11+) · MCP: lsp check/impact/related

Refine your search:
  --show-scores    Detailed score breakdown (BM25, semantic, activation)
  --show-content   Preview code snippets
  --limit N        More results (e.g., --limit 20)
  --type TYPE      Filter: function, class, method, kb, code
  --min-score 0.5  Higher relevance threshold
  
Detailed Score Breakdown:

┌─ core.py | code | generate_goals_json (Lines 1091-1175) ───────────────────────────────────────────┐
│ Final Score: 0.619                                                                                 │
│  ├─ BM25:       0.895 * (exact keyword match on 'goals')                                           │
│  ├─ Semantic:   0.865 (high conceptual relevance)                                                  │
│  ├─ Activation: 0.014 (accessed 7x, 7 commits, last used 1 week ago)                               │
│  ├─ Git:        7 commits, modified 8d ago, 1769419365                                             │
│  ├─ Files:      core.py, test_goals_json.py                                                        │
│  └─ Used by:    2 files, 2 refs, complexity 44%, risk MED                                          │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Code Intelligence (MCP)

Aurora provides fast code intelligence via MCP tools - many operations use ripgrep instead of LSP for 100x speed.

| Tool | Action | Speed | Purpose |
|------|--------|-------|---------|
| `lsp` | `check` | ~1s | Quick usage count before editing |
| `lsp` | `impact` | ~2s | Full impact analysis with top callers |
| `lsp` | `deadcode` | 2-20s | Find all unused symbols in directory |
| `lsp` | `imports` | <1s | Find all files that import a module |
| `lsp` | `related` | ~50ms | Find outgoing calls (dependencies) |
| `mem_search` | - | <1s | Semantic search with LSP enrichment |

**Risk levels:** LOW (0-2 refs) → MED (3-10) → HIGH (11+)

**When to use:**
- Before editing: `lsp check` to see what depends on it
- Before refactoring: `lsp impact` to assess risk
- Understanding dependencies: `lsp related` to see what a function calls
- Finding importers: `lsp imports` to see who imports a module
- Finding code: `mem_search` instead of grep for semantic results
- After changes: `lsp deadcode` to clean up orphaned code

**Language support:**
- **Python:** Full (LSP + tree-sitter complexity + import filtering)
- **JS/TS/Go/Rust/Java:** Partial (LSP refs, ripgrep deadcode)

See [Code Intelligence Guide](docs/02-features/lsp/CODE_INTELLIGENCE_STATUS.md) for all 16 features and implementation details.

---

### Memory-Aware Planning (Terminal)

`aur goals` - Decomposes any goal into subgoals:

1. Looks up existing memory for matches
2. Breaks down into subgoals
3. Assigns your existing subagents to each subgoal
4. Detects capability gaps - tells you what agents to create

Works across any domain (code, writing, research).

```bash
$ aur goals "how can i improve the speed of aur mem search that takes 30 seconds loading when
it starts" -t claude
╭──────────────────────────────────────── Aurora Goals ───────────────────────────────────────╮
│ how can i improve the speed of aur mem search that takes 30 seconds loading when it starts  │
╰─────────────────────────────────────── Tool: claude ────────────────────────────────────────╯
╭──────────────────────────────── Plan Decomposition Summary ─────────────────────────────────╮
│ Subgoals: 5                                                                                 │
│                                                                                             │
│   [++] Locate and identify the 'aur mem search' code in the codebase: @code-developer       │
│   [+] Analyze the startup/initialization logic to identify performance bottlenecks:         │
│ @code-developer (ideal: @performance-engineer)                                              │
│   [++] Review system architecture for potential design improvements (lazy loading, caching, │
│ indexing): @system-architect                                                                │
│   [++] Implement optimization strategies (lazy loading, caching, indexing, parallel         │
│ processing): @code-developer                                                                │
│   [++] Measure and validate performance improvements with benchmarks: @quality-assurance    │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯

╭────────────────────────────────────────── Summary ──────────────────────────────────────────╮
│ Agent Matching: 4 excellent, 1 acceptable                                                   │
│ Gaps Detected: 1 subgoals need attention                                                    │
│ Context: 1 files (avg relevance: 0.60)                                                      │
│ Complexity: COMPLEX                                                                         │
│ Source: soar                                                                                │
│                                                                                             │
│ Warnings:                                                                                   │
│   ! Agent gaps detected: 1 subgoals need attention                                          │
│                                                                                             │
│ Legend: [++] excellent | [+] acceptable | [-] insufficient                                  │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯

```

---

### Memory-Aware Research (Terminal)

`aur soar` - Research questions using your codebase:

1. Looks up existing memory for matches
2. Decomposes question into sub-questions
3. Utilizes existing subagents
4. Spawns agents on the fly
5. Simple multi-orchestration with agent recovery (stateful)

```bash
aur soar "write a 3 paragraph sci-fi story about a bug the gained llm conscsiousness" -t claude
╭──────────────────────────────────────── Aurora SOAR ────────────────────────────────────────╮
│ write a 3 paragraph sci-fi story about a bug the gained llm conscsiousness                  │
╰─────────────────────────────────────── Tool: claude ────────────────────────────────────────╯
Initializing...


[ORCHESTRATOR] Phase 1: Assess
  Analyzing query complexity...
  Complexity: MEDIUM

[ORCHESTRATOR] Phase 2: Retrieve
  Looking up memory index...
  Matched: 10 chunks from memory

[LLM → claude] Phase 3: Decompose
  Breaking query into subgoals...
  ✓ 1 subgoals identified

[LLM → claude] Phase 4: Verify
  Validating decomposition and assigning agents...
  ✓ PASS (1 subgoals routed)

                                      Plan Decomposition
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ #    ┃ Subgoal                                       ┃ Agent                ┃ Match        ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ 1    │ Write a 3-paragraph sci-fi short story about  │ @creative-writer*    │ ✗ Spawned    │
└──────┴───────────────────────────────────────────────┴──────────────────────┴──────────────┘
╭────────────────────────────────────────── Summary ──────────────────────────────────────────╮
│ 1 subgoal • 0 assigned • 1 spawned                                                          │
│                                                                                             │
│ Spawned (no matching agent): @creative-writer                                               │
╰─────────────────────────────────────────────────────────────────────────────────────────────
```

---

### Task Execution (Terminal)

`aur spawn` - Takes predefined task list and executes with:

- Stop gates for feature creep
- Dangerous command detection (rm -rf, etc.)
- Budget limits

```bash
aur spawn tasks.md --verbose
```

---

### Friction Analysis (Terminal)

`aur friction` - Analyze stuck patterns across your coding sessions:

```bash
aur friction ~/.claude/projects
Per-Project:
aurora        56% BAD (40/72)  median: 16.0  🔴
mcp-gov       40% BAD (2/5)    median: 0.5   🟡
liteagents     0% BAD (0/1)    median: 0.0   ✅

Session Extremes:
WORST: aurora/0203-1630-11eb903a  peak=225  turns=127
BEST:  liteagents/0202-2121-8d8608e1  peak=0  turns=4

Last 2 Weeks:
2026-02-02  15 sessions  10 BAD  ██████░░░░  67%
2026-02-03  29 sessions  12 BAD  ████░░░░░░  41%
2026-02-04   6 sessions   2 BAD  ███░░░░░░░  33%

Verdict: ✓ USEFUL
Intervention predictability: 93%
```

Identifies sessions where you got stuck, measures improvement over time.

---

## Planning Workflow

3 simple steps from goal to implementation.

**Code-aware planning:** `aur goals` searches your indexed codebase and maps each subgoal to relevant source files (`source_file`). This context flows through `/aur:plan` → `/aur:implement`, making implementation more accurate.

> **Quick prototype?** Skip `aur goals` and run `/aur:plan` directly - the agent will search on the fly (less structured).

```
Setup (once)             Step 1: Decompose        Step 2: Plan             Step 3: Implement
Terminal                 Terminal                 Slash Command            Slash Command
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐      ┌─────────────────┐
│   aur init      │     │   aur goals     │ ->  │   /aur:plan     │  ->  │  /aur:implement │
│   Complete      │     │   "Add feature" │     │   [plan-id]     │      │   [plan-id]     │
│   project.md*   │     │                 │     │                 │      │                 │
│   aur mem index │     │                 │     │                 │      │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘      └─────────────────┘
        │                       │                       │                        │
        v                       v                       v                        v
   .aurora/                goals.json              5 artifacts:            Code changes
   - project.md*           - subgoals              - plan.md               - validated
   - memory.db             - agents                - prd.md                - tested
                           - source files          - design.md
                                                   - agents.json
                                                   - tasks.md
                                                        │
                                                 ┌──────┴──────┐
                                                 │ /aur:tasks  │  <- Optional: regenerate
                                                 │ [plan-id]   │     tasks after PRD edits
                                                 └─────────────┘

* Ask your agent to complete project.md: "Please fill out .aurora/project.md with our
  architecture, conventions, and key patterns." This improves planning accuracy.
```

See [3 Simple Steps Guide](docs/04-process/getting-started/3-SIMPLE-STEPS.md) for detailed walkthrough.

---

## Quick Start

```bash
# Install (or upgrade with --upgrade flag)
pip install aurora-actr

# Initialize project (once per project)
cd your-project/
aur init                        # Creates .aurora/project.md

# IMPORTANT: Complete .aurora/project.md manually
# Ask your agent: "Please complete the project.md with our architecture and conventions"
# This context improves planning accuracy

# Index codebase for memory
aur mem index .

# Plan with memory context
aur goals "Add user authentication"

# In your CLI tool (Claude Code, Cursor, etc.):
/aur:plan add-user-authentication
/aur:implement add-user-authentication
```

---

## Commands Reference

### Terminal

| Command | Description |
|---------|-------------|
| `aur init` | Initialize Aurora in project |
| `aur doctor` | Check installation and dependencies |
| `aur mem index .` | Index code and docs |
| `aur mem search "query"` | Search memory from terminal |
| `aur goals "goal"` | Decompose goal, match agents, find gaps |
| `aur soar "question"` | Multi-agent research with memory |
| `aur spawn tasks.md` | Execute task list with guardrails |
| `aur friction <dir>` | Analyze session friction patterns |

### Slash Commands (in AI tools)

| Command | Description |
|---------|-------------|
| `/aur:plan [id]` | Generate PRD, design, tasks from goal |
| `/aur:tasks [id]` | Regenerate tasks after PRD edits |
| `/aur:implement [id]` | Execute plan tasks sequentially |
| `/aur:archive [id]` | Archive completed plan |

---

## Supported Tools

Works with 20+ CLI tools: Claude Code, Cursor, Aider, Cline, Windsurf, Gemini CLI, and more.

Configuration is per-project (not global) to keep your CLI clean:

```bash
cd /path/to/project
aur init --tools=claude,cursor
```

---

## Documentation

- [Commands Reference](docs/02-features/cli/COMMANDS.md)
- [Tools Guide](docs/02-features/agents/TOOLS_GUIDE.md)
- [Flows Guide](docs/02-features/FLOWS.md)
- [Troubleshooting](docs/04-process/troubleshooting/TROUBLESHOOTING.md)

---

## License

MIT License - See [LICENSE](LICENSE)
