<div align="center">

<pre>
   █████╗ ██╗   ██╗██████╗  ██████╗ ██████╗  █████╗
  ██╔══██╗██║   ██║██╔══██╗██╔═══██╗██╔══██╗██╔══██╗
  ███████║██║   ██║██████╔╝██║   ██║██████╔╝███████║
  ██╔══██║██║   ██║██╔══██╗██║   ██║██╔══██╗██╔══██║
  ██║  ██║╚██████╔╝██║  ██║╚██████╔╝██║  ██║██║  ██║
  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
Code-aware memory and intelligence for AI coding assistants.
</pre>

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/aurora-actr.svg)](https://pypi.org/project/aurora-actr/)

</div>

---

## What Aurora Does

Aurora indexes your codebase, tracks what's hot (recently/frequently used), warm, or cool (decaying), and gives you LSP-powered code intelligence — dead code detection, impact analysis, usage tracking — as MCP tools your AI assistant can call.

It's not an orchestration framework. It's the memory and code intelligence layer that makes any AI coding assistant smarter about your specific codebase.

- **Code-aware memory** — Indexes code as structured chunks (classes, methods, functions). Ranks by recency, frequency, and relevance using ACT-R activation decay. What you use stays hot. What you don't fades.
- **LSP intelligence** — Dead code detection, impact analysis, usage tracking, import mapping. Exposed as MCP tools — your AI assistant calls them directly.
- **Private and local** — No API keys for core features. No data leaves your machine. SQLite storage.
- **Works with any AI tool** — Claude Code, Cursor, or anything that supports MCP.

```bash
pip install aurora-actr
```

---

## Memory

`aur mem` — Index your codebase and search it with activation-based ranking.

**What gets indexed:**
- **Code** — Tree-sitter parses Python, JS/TS, Go, Java into class/method/function chunks
- **Git signals** — Recent changes rank higher
- **LSP enrichment** — Usage count, complexity, risk level per symbol
- **Docs** — Markdown files indexed for semantic search

```bash
# Index your project
aur mem index .

# Search with activation-based ranking
aur mem search "soar reasoning" --show-scores
```

```
Found 5 results for 'soar reasoning'

┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┳━━━━━┳━━━━━━━━━┓
┃ Type   ┃ File                   ┃ Name                 ┃ Lines      ┃ Risk   ┃ Git ┃   Score ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━╇━━━━━╇━━━━━━━━━┩
│ code   │ core.py                │ generate_goals_json  │ 1091-1175  │ MED    │ 8d  │   0.619 │
│ code   │ soar.py                │ <chunk>              │ 1473-1855  │ -      │ 1d  │   0.589 │
│ code   │ orchestrator.py        │ SOAROrchestrator._c… │ 2141-2257  │ HIGH   │ 1d  │   0.532 │
│ code   │ test_goals_startup_pe… │ TestGoalsCommandSta… │ 190-273    │ LOW    │ 1d  │   0.517 │
│ code   │ goals.py               │ <chunk>              │ 437-544    │ -      │ 7d  │   0.486 │
└────────┴────────────────────────┴──────────────────────┴────────────┴────────┴─────┴─────────┘
Avg scores: Activation 0.916 | Semantic 0.867 | Hybrid 0.801
```

**Score breakdown** — each result shows exactly why it ranked where it did:

```
┌─ core.py | code | generate_goals_json (Lines 1091-1175) ─────────────────────────────────────┐
│ Final Score: 0.619                                                                           │
│  ├─ BM25:       0.895 * (exact keyword match on 'goals')                                     │
│  ├─ Semantic:   0.865 (high conceptual relevance)                                            │
│  ├─ Activation: 0.014 (accessed 7x, 7 commits, last used 1 week ago)                         │
│  ├─ Git:        7 commits, modified 8d ago, 1769419365                                       │
│  ├─ Files:      core.py, test_goals_json.py                                                  │
│  └─ Used by:    2 files, 2 refs, complexity 44%, risk MED                                    │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Code Intelligence (MCP)

Aurora exposes code intelligence as MCP tools. Your AI assistant calls these directly — no terminal needed.

| Tool | Action | Speed | What it does |
|------|--------|-------|-------------|
| `lsp` | `check` | ~1s | How many things depend on this symbol? Check before editing. |
| `lsp` | `impact` | ~2s | Full impact analysis — who calls it, from where, risk level |
| `lsp` | `deadcode` | 2-20s | Find unused symbols in a directory |
| `lsp` | `imports` | <1s | What files import this module? |
| `lsp` | `related` | ~50ms | What does this function call? (outgoing dependencies) |
| `mem_search` | - | <1s | Semantic search with LSP enrichment |

**Risk levels:** LOW (0-2 refs) | MED (3-10) | HIGH (11+)

**When to use:**
- Before editing: `lsp check` to see what depends on it
- Before refactoring: `lsp impact` to assess blast radius
- After changes: `lsp deadcode` to clean up orphaned code
- Finding code: `mem_search` for semantic results instead of grep

**Language support:** Python (full), JavaScript/TypeScript, Go, Java (LSP refs + tree-sitter indexing).

See [Code Intelligence Guide](docs/02-features/lsp/CODE_INTELLIGENCE_STATUS.md) for details.

---

## Friction Analysis

`aur friction` — Analyze your coding sessions to find where you get stuck.

```bash
aur friction ~/.claude/projects
Per-Project:
my-app         56% BAD (40/72)  median: 16.0
api-service    40% BAD (2/5)    median: 0.5
web-client      0% BAD (0/1)    median: 0.0

Session Extremes:
WORST: aurora/0203-1630-11eb903a  peak=225  turns=127
BEST:  liteagents/0202-2121-8d8608e1  peak=0  turns=4

Verdict: USEFUL
Intervention predictability: 93%
```

Identifies sessions where you got stuck and extracts learned rules to add to CLAUDE.md or your AI tool's instructions — preventing the same mistakes.

---

## Goal Decomposition

`aur goals` — Break a goal into subgoals, matched to agents:

```bash
$ aur goals "improve the speed of aur mem search" -t claude
╭──────────────────────────────── Plan Decomposition Summary ─────────────────────────────────╮
│ Subgoals: 5                                                                                 │
│                                                                                             │
│   [++] Locate and identify the 'aur mem search' code: @code-developer                      │
│   [+] Analyze startup logic for bottlenecks: @code-developer (ideal: @performance-engineer) │
│   [++] Review architecture for lazy loading, caching: @system-architect                     │
│   [++] Implement optimizations: @code-developer                                             │
│   [++] Measure and validate with benchmarks: @quality-assurance                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
```

---

## Quick Start

```bash
# Install
pip install aurora-actr

# Initialize project (once)
cd your-project/
aur init

# Index codebase
aur mem index .

# Search your code
aur mem search "authentication flow"

# Check usage before editing
# (via MCP in Claude Code / Cursor — aurora auto-registers as MCP server)
```

**MCP setup:** Aurora registers as an MCP server during `aur init`. Your AI tool can call `lsp` and `mem_search` directly.

---

## Orchestration

Memory and code intelligence feed into Aurora's orchestration layer. Goals get decomposed into subgoals, routed to agents, and executed with circuit breakers and recovery. The SOAR pipeline runs eight phases — assess, retrieve, decompose, verify, collect, synthesize, record, respond — using your indexed codebase as context for every decision.

```bash
# Research with memory-aware orchestration
aur soar "what would break if I removed the retry module?" -t claude

# Execute task lists with guardrails
aur spawn tasks.md --verbose
```

Works with Claude Code, Cursor, Aider, Cline, Windsurf, Gemini CLI, and 20+ other AI coding tools. Configuration is per-project:

```bash
aur init --tools=claude,cursor
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `aur init` | Initialize Aurora in project |
| `aur doctor` | Check installation and dependencies |
| `aur mem index .` | Index code and docs |
| `aur mem search "query"` | Search memory with activation ranking |
| `aur goals "goal"` | Decompose goal, match agents |
| `aur soar "question"` | Multi-agent research with memory context |
| `aur spawn tasks.md` | Execute task list with guardrails |
| `aur friction <dir>` | Analyze session friction patterns |

---

## Documentation

- [Commands Reference](docs/02-features/cli/COMMANDS.md)
- [Code Intelligence Guide](docs/02-features/lsp/CODE_INTELLIGENCE_STATUS.md)
- [Tools Guide](docs/02-features/agents/TOOLS_GUIDE.md)
- [Previous README (full feature reference)](docs/01-product/README-v0.17.md)

---

## License

MIT License — See [LICENSE](LICENSE)
