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
Planning & Multi-Agent Orchestration
</pre>

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/aurora-actr.svg)](https://pypi.org/project/aurora-actr/)

</div>

---

## Summary

### Aurora - Memory-aware Planning & Multi-Agent Orchestration Framework

- **LLM-agnostic** - No API keys, works with 20+ CLI tools (Claude Code, Cursor, Aider, etc.)
- **Smart Memory** - ACT-R activation decay, BM25, tree-sitter/cAST, git signals
- **Memory-Aware Planning** - Decompose goals, assign agents, detect capability gaps
- **Memory-Aware Research** - Multi-agent orchestration with recovery and state
- **Task Execution** - Stop gates for feature creep and dangerous commands
- **Headless Mode** - Isolated branch execution with max retries

```bash
# New installation
pip install aurora-actr

# Upgrading from older version (0.9.x → 0.10.0)?
# Use --upgrade flag to pull latest release
pip install --upgrade aurora-actr
aur --version  # Should show 0.10.0

# Uninstall
pip uninstall aurora-actr

# From source (development)
git clone https://github.com/amrhas82/aurora.git
cd aurora && ./install.sh
```

---

## Core Features

### Smart Memory (Slash Commands)

`aur:search` - Memory with activation decay from ACT-R. Indexes your code using:

- **BM25** - Keyword search
- **Git signals** - Recent changes rank higher
- **Tree-sitter/cAST** - Code stored as class/method (Python, TypeScript, Java)
- **Markdown indexing** - Search docs, save tokens

```bash
# Terminal
aur mem index .
aur mem search "soar reasoning" --show-scores
Found 5 results for 'soar reasoning'

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━┓
┃ File                       ┃ Type   ┃ Name             ┃ Lines   ┃ Comm… ┃ Modifi… ┃  Score ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━┩
│ orchestrator.py            │ code   │ SOAROrchestrator │ 69-1884 │    30 │ recent  │  0.922 │
│ TOKEN-PREDICTION-VS-AGENT… │ kb     │ Connection to    │ 1-40    │     2 │ recent  │  0.892 │
│                            │        │ You...           │         │       │         │        │
│ decompose.py               │ code   │ PlanDecomposer   │ 55-658  │    12 │ recent  │  0.755 │
│ decompose.py               │ code   │ PlanDecomposer.… │ 460-566 │     5 │ recent  │  0.731 │
│ test_agent_matching_quali… │ code   │ TestDecompositi… │ 663-707 │     2 │ recent  │  0.703 │
└────────────────────────────┴────────┴──────────────────┴─────────┴───────┴─────────┴────────┘

Average scores:
  Activation: 0.916
  Semantic:   0.867
  Hybrid:     0.801

Refine your search:
  --show-scores    Detailed score breakdown (BM25, semantic, activation)
  --show-content   Preview code snippets
  --limit N        More results (e.g., --limit 20)
  --type TYPE      Filter: function, class, method, kb, code
  --min-score 0.5  Higher relevance threshold

Detailed Score Breakdown:

┌─ orchestrator.py | code | SOAROrchestrator (Lines 69-1884) ────────────────────────────────┐
│ Final Score: 0.922                                                                         │
│  ├─ BM25:       1.000 * (exact keyword match on 'reasoning', 'soar')                       │
│  ├─ Semantic:   0.869 (high conceptual relevance)                                          │
│  └─ Activation: 0.916 (accessed 31x, 30 commits, last used 19 minutes ago)                 │
│ Git: 30 commits, last modified 1768838464                                                  │
└────────────────────────────────────────────────────────────────────────────────────────────┘

# Slash command
/aur:search "authentication"
/aur:get 1  # Read chunk
```

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

### Headless Mode (Terminal)

`aur headless` - Ralph Wiggum mode:

- Runs in isolated branch
- Max retries on failure
- Unattended execution

```bash
aur headless prompt.md
```

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

See [3 Simple Steps Guide](docs/guides/3-SIMPLE-STEPS.md) for detailed walkthrough.

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

| Command | Type | Description |
|---------|------|-------------|
| `aur init` | Terminal | Initialize Aurora in project |
| `aur doctor` | Terminal | Check installation and dependencies |
| `aur mem index .` | Terminal | Index codebase |
| `aur mem search "query"` | Terminal | Search memory |
| `aur goals "goal"` | Terminal | Memory-aware planning |
| `aur soar "question"` | Terminal | Memory-aware research |
| `aur spawn tasks.md` | Terminal | Execute with safeguards |
| `aur headless prompt.md` | Terminal | Unattended execution |
| `/aur:search "query"` | Slash | Search indexed memory |
| `/aur:get N` | Slash | Read chunk from search |
| `/aur:plan [plan-id]` | Slash | Generate plan artifacts |
| `/aur:tasks [plan-id]` | Slash | Regenerate tasks from PRD |
| `/aur:implement [plan-id]` | Slash | Execute plan |
| `/aur:archive [plan-id]` | Slash | Archive completed plan |

---

## Supported Tools

Works with 20+ CLI tools: Claude Code, Cursor, Aider, Cline, Windsurf, Gemini CLI, and more.

```bash
aur init --tools=claude,cursor
```

---

## Documentation

- [Commands Reference](docs/guides/COMMANDS.md)
- [Tools Guide](docs/guides/TOOLS_GUIDE.md)
- [Flows Guide](docs/guides/FLOWS.md)

---

## License

MIT License - See [LICENSE](LICENSE)
