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
- **Session Checkpoints** - Save and resume session context

```bash
# PyPI
pip install aurora-actr

# From source
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
aur mem search "authentication"

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
$ aur goals "Add payment processing"

Memory matches: 3 files found
Subgoals: 4
  sg-1: Set up Stripe SDK (@code-developer)
  sg-2: Create payment endpoints (@code-developer)
  sg-3: Implement checkout UI (@ui-designer)
  sg-4: Configure PCI compliance (@security-engineer -> NOT FOUND)

Gaps detected:
  - Missing @security-engineer
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
aur soar "How does the payment flow work?"
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

### Checkpoints (Slash Command)

`aur:checkpoint` - Create digest of current session to resume later.

```bash
/aur:checkpoint

# Output: .aurora/checkpoints/session-2026-01-15.md
# Contains: goals, progress, decisions, next steps
```

---

## Planning Workflow

OpenSpec-based flow from goal to implementation:

```
Terminal                    Slash Command            Slash Command
┌─────────────────┐        ┌─────────────────┐      ┌─────────────────┐
│   aur goals     │   ->   │  /aur:plan      │  ->  │  /aur:implement │
│   "Add feature" │        │  goals.json     │      │                 │
└─────────────────┘        └─────────────────┘      └─────────────────┘
        │                          │                        │
        v                          v                        v
   goals.json               PRD + tasks.md            Implemented
   - subgoals               - specs/                  - checkpoints
   - agent assignments      - file hints              - validation
   - capability gaps
```

---

## Quick Start

```bash
# Install
pip install aurora-actr

# Initialize project
cd your-project/
aur init

# Index codebase for memory
aur mem index .

# Plan with memory context
aur goals "Add user authentication"

# In your CLI tool (Claude Code, Cursor, etc.):
/aur:plan goals.json
/aur:implement
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
| `/aur:plan goals.json` | Slash | Generate PRD + tasks |
| `/aur:implement` | Slash | Execute plan |
| `/aur:checkpoint` | Slash | Save session context |
| `/aur:archive plan-id` | Slash | Archive completed plan |

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
