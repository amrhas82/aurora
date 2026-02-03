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
Aurora gives AI coding assistants persistent memory and code intelligence.
Index once, search semantically, plan with context.
</pre>

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/aurora-actr.svg)](https://pypi.org/project/aurora-actr/)

</div>

---

## Summary

### Aurora - Memory & Code Intelligence for AI Assistants

- **Works everywhere** - No API keys needed. Works with Claude Code, Cursor, Aider, and 20+ tools
- **Smart Memory** - Indexes your code and docs. Remembers what you accessed recently, ranks by relevance
- **Code Intelligence** - Find unused code, check impact before refactoring, search with LSP context
- **Planning** - Break goals into tasks, match to agents, detect capability gaps
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

```

---

### MCP Tools

Aurora exposes these tools to AI assistants via Model Context Protocol:

| Tool | Purpose |
|------|---------|
| `lsp deadcode` | Find unused functions, classes, variables. Generates CODE_QUALITY_REPORT.md |
| `lsp impact` | See all callers before changing a symbol. Shows risk level (low/medium/high) |
| `lsp check` | Quick "is this used?" lookup before editing |
| `mem_search` | Semantic search across indexed code. Returns snippets with LSP context (used_by, called_by) and git info |

**Supported:** Python, TypeScript, Java, Go, Rust, C/C++, and more (10+ languages via multilspy)

**When to use:**
- Before editing: `lsp check` to see what depends on it
- Before refactoring: `lsp impact` to assess risk
- Finding code: `mem_search` instead of grep for semantic results
- After changes: `lsp deadcode` to clean up orphaned code

See [MCP Tools Documentation](docs/02-features/mcp/MCP.md) for details.

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

### MCP Tools (for AI assistants)

| Tool | Description |
|------|-------------|
| `lsp deadcode` | Find unused symbols, generate report |
| `lsp impact` | Analyze callers and refactoring risk |
| `lsp check` | Quick usage check before editing |
| `mem_search` | Semantic search with LSP enrichment |

---

## Supported Tools

Works with 20+ CLI tools: Claude Code, Cursor, Aider, Cline, Windsurf, Gemini CLI, and more.

```bash
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
