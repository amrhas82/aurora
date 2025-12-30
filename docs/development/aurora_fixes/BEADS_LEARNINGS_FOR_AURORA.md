# What Aurora Can Learn from Beads

> A practical guide to improving Aurora's MCP, context efficiency, and Claude integration based on the beads issue tracker.

## Table of Contents

1. [What is Beads?](#what-is-beads)
2. [The Big Ideas (Simple Version)](#the-big-ideas-simple-version)
3. [Lesson 1: Don't Waste Tokens](#lesson-1-dont-waste-tokens)
4. [Lesson 2: The Prime Command](#lesson-2-the-prime-command)
5. [Lesson 3: Slash Commands via Plugin](#lesson-3-slash-commands-via-plugin)
6. [Lesson 4: Skills for Claude](#lesson-4-skills-for-claude)
7. [Lesson 5: Git-Backed Memory](#lesson-5-git-backed-memory)
8. [Lesson 6: Workspace Context](#lesson-6-workspace-context)
9. [Implementation Roadmap](#implementation-roadmap)
10. [File References](#file-references)

---

## What is Beads?

Beads (`bd`) is an issue tracker designed for AI coding agents. Think of it as "memory that survives conversation compaction."

**Key insight**: When Claude's context gets full, old messages are compressed/deleted. Beads stores important work state *outside* the conversation, so nothing is lost.

**Why Aurora should care**: Aurora is a memory/retrieval system. Beads solved the same problem of "how do we help Claude remember things across sessions" - just for task tracking instead of code context.

---

## The Big Ideas (Simple Version)

| Beads Concept | What It Means | Aurora Equivalent |
|---------------|---------------|-------------------|
| **Context Engineering** | Don't send more data than needed | Return chunk summaries, not full content |
| **Prime Command** | Inject workflow context at session start | `aur prime` to show memory stats |
| **Plugin System** | Slash commands like `/bd-ready` | Slash commands like `/aur-search` |
| **Skills** | Teach Claude how to use the tool | Teach Claude when/how to use Aurora |
| **Git Sync** | SQLite locally, JSONL in git | Export chunks to portable format |
| **Workspace Context** | Know which project we're in | Know which index to use |

---

## Lesson 1: Don't Waste Tokens

### The Problem

Every token in Claude's context costs compute time and money. MCP tools can add **10-50k tokens** just from tool schemas!

### How Beads Solves It

**Before**: Return full issue with all fields
```json
{
  "id": "bd-a1b2",
  "title": "Fix auth bug",
  "description": "Long description with all the details...",
  "design": "Design notes here...",
  "acceptance_criteria": "...",
  "notes": "...",
  "status": "open",
  "priority": 1,
  "dependencies": [/* full dependency objects */],
  "dependents": [/* full dependent objects */],
  "created_at": "2024-01-01T...",
  "updated_at": "2024-01-02T..."
}
```
**Size**: ~400 bytes per issue

**After**: Return minimal model for lists
```json
{
  "id": "bd-a1b2",
  "title": "Fix auth bug",
  "status": "open",
  "priority": 1,
  "dependency_count": 2
}
```
**Size**: ~80 bytes per issue (80% reduction!)

### Aurora Should Do This

**Current**: `aur mem search` returns full chunks with embeddings and content

**Better**: Return `ChunkMinimal` for search results:
```python
class ChunkMinimal:
    id: str              # "aur-abc123"
    file_path: str       # "src/auth.py"
    symbol_name: str     # "authenticate_user"
    relevance: float     # 0.92
    preview: str         # "def authenticate_user(token):..."  (first 100 chars)
```

Use `aur show <chunk-id>` to get full content when needed.

### Three Techniques

#### 1. Lazy Tool Schema Loading

Instead of loading all tool schemas at startup:

```python
# BEFORE: All schemas loaded upfront = 15,000+ bytes

# AFTER: Two-step discovery
@mcp.tool("discover_tools")
async def discover_tools():
    """List available tools (names only)."""
    return {
        "mem_search": "Search indexed code",
        "mem_index": "Index codebase",
        "query": "Query with reasoning"
    }  # ~200 bytes

@mcp.tool("get_tool_info")
async def get_tool_info(tool_name: str):
    """Get full schema for one tool."""
    # Return detailed params only when needed
```

**Savings**: 97% reduction in initial schema overhead

#### 2. Result Compaction

When you have too many results, don't return all of them:

```python
COMPACTION_THRESHOLD = 20
PREVIEW_COUNT = 5

async def search(query: str):
    results = await semantic_search(query)

    if len(results) > COMPACTION_THRESHOLD:
        return {
            "compacted": True,
            "total_count": len(results),
            "preview": results[:PREVIEW_COUNT],
            "hint": "Use 'aur show <id>' for full details"
        }

    return results
```

#### 3. Brief Mode by Default

```python
@mcp.tool("search")
async def search(query: str, brief: bool = True):
    results = await semantic_search(query)

    if brief:
        return [to_minimal(r) for r in results]

    return results  # Full details only when explicitly requested
```

---

## Lesson 2: The Prime Command

### The Problem

Claude forgets everything when context is compacted. How do you remind it about your tool's workflow?

### How Beads Solves It

The `bd prime` command outputs **workflow context** that Claude should know:

```bash
$ bd prime

# Beads Issue Tracker Active

# SESSION CLOSE PROTOCOL
Before saying "done": git status -> git add -> bd sync -> git commit -> git push

## Core Rules
- Track strategic work in beads (multi-session, dependencies)
- TodoWrite is fine for simple single-session linear tasks

Start: Check `ready` tool for available work.
```

**Key features**:
- Runs automatically on **SessionStart** hook
- Runs before **PreCompact** (so Claude remembers workflow after compaction)
- Adapts output based on context (MCP mode = shorter, CLI mode = longer)

### Aurora Should Do This

Create `aur prime` command:

```python
# aurora_cli/commands/prime.py

def prime():
    """Output AI-optimized context at session start."""
    stats = get_index_stats()

    output = f"""# Aurora Memory Active

## Current Index
- Chunks: {stats.chunk_count:,} from {stats.file_count} files
- Last indexed: {stats.last_index_time}
- Coverage: {stats.coverage_percent:.0f}% of codebase

## Quick Commands
- `aur query "your question"` - Semantic search with reasoning
- `aur mem search "text"` - Direct chunk search
- `aur mem index .` - Re-index current directory

## Retrieval Quality
- Average groundedness: {stats.avg_groundedness:.1%}
- Use --non-interactive for CI/automated usage

Start: Use `aur query` for semantic search.
"""
    print(output)
```

**Token cost**: ~200-500 tokens (vs 10k+ for full MCP schemas)

---

## Lesson 3: Slash Commands via Plugin

### The Problem

Typing full commands is tedious. Users want shortcuts like `/bd-ready` instead of running bash commands.

### How Beads Solves It

Beads uses a **Claude Code Plugin** that registers slash commands:

```
.claude-plugin/
├── plugin.json      # Plugin metadata + hooks
├── marketplace.json # For plugin discovery
└── agents/          # Optional agent definitions
```

**plugin.json**:
```json
{
  "name": "beads",
  "description": "AI-supervised issue tracker for coding workflows",
  "version": "0.41.0",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "bd prime" }]
      }
    ],
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "bd prime" }]
      }
    ]
  }
}
```

The plugin also provides slash commands through the MCP server:
- `/bd-init` - Initialize beads
- `/bd-ready` - Find ready tasks
- `/bd-create` - Create new issue
- `/bd-show` - Show issue details
- `/bd-update` - Update issue
- `/bd-close` - Close issue

### Aurora Should Do This

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "aurora",
  "description": "Cognitive memory and semantic retrieval for coding agents",
  "version": "0.2.0",
  "author": {
    "name": "Aurora Team",
    "url": "https://github.com/your-org/aurora"
  },
  "repository": "https://github.com/your-org/aurora",
  "license": "MIT",
  "keywords": [
    "memory",
    "semantic-search",
    "code-retrieval",
    "agent-memory"
  ],
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "aur prime" }]
      }
    ],
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "aur prime" }]
      }
    ]
  }
}
```

**Slash commands to implement**:

| Command | Action | Example |
|---------|--------|---------|
| `/aur-query` | Semantic search with reasoning | `/aur-query "how does auth work"` |
| `/aur-search` | Direct chunk search | `/aur-search "authenticate_user"` |
| `/aur-index` | Index current directory | `/aur-index` |
| `/aur-stats` | Show index statistics | `/aur-stats` |
| `/aur-show` | Show chunk details | `/aur-show aur-abc123` |

### Installation Flow

```bash
# User installs Aurora
pip install aurora-actr[all]

# User tells Claude about it
/plugin marketplace add your-org/aurora
/plugin install aurora

# Claude can now use /aur-* commands
```

---

## Lesson 4: Skills for Claude

### The Problem

Even with good tools, Claude needs to know *when* and *how* to use them effectively.

### How Beads Solves It

Beads provides a **Skill** - a structured document that teaches Claude the tool's workflow:

```
skills/beads/
├── SKILL.md          # Main skill file (Claude reads this)
├── README.md         # For humans
└── references/       # Detailed docs (loaded on demand)
    ├── WORKFLOWS.md
    ├── DEPENDENCIES.md
    └── ...
```

**SKILL.md structure**:
```markdown
---
name: beads
description: >
  Tracks complex, multi-session work using dependency graphs...
allowed-tools: "Read,Bash(bd:*)"
version: "0.34.0"
---

# Beads - Persistent Task Memory

## Overview
[What the tool does]

## Prerequisites
[What needs to be installed]

## Instructions
[Step-by-step usage]

## Examples
[Concrete examples]

## Error Handling
[Common problems and solutions]

## Resources
[Links to detailed docs]
```

### Aurora Should Do This

Create `skills/aurora/SKILL.md`:

```markdown
---
name: aurora
description: >
  Semantic code search and retrieval. Use when user asks about code,
  needs to find implementations, or wants context about the codebase.
  Trigger with "search for", "find code", "how does X work", "where is".
allowed-tools: "Read,Bash(aur:*)"
version: "0.2.0"
---

# Aurora - Semantic Code Memory

## Overview

Aurora provides semantic search over your codebase. Instead of grep/find,
it understands code meaning and retrieves relevant chunks.

**Use Aurora when**:
- User asks "how does X work?"
- User says "find the code that handles Y"
- User needs context before making changes
- Code search by meaning, not just text

**Don't use Aurora when**:
- Looking for a specific file by name (use Glob)
- Exact text search (use Grep)
- Simple questions that don't need code context

## Prerequisites

- Aurora CLI installed: `pip install aurora-actr[all]`
- Index created: `aur mem index .` (humans run once)

## Instructions

### Finding Code

```bash
# Semantic search
aur query "how does user authentication work"

# Direct chunk search
aur mem search "authenticate"

# Show chunk details
aur show aur-abc123
```

### Understanding Results

Results include:
- **Relevance score**: 0.0-1.0 (higher = more relevant)
- **File path**: Where the code lives
- **Symbol name**: Function/class name
- **Preview**: First 100 chars

### Session Protocol

1. **Start**: Check if index exists with `aur --verify`
2. **Search**: Use `aur query` for questions about code
3. **Deep dive**: Use `aur show <id>` for full chunk content

## Examples

### Example 1: Understanding a Feature

**User**: "How does the login flow work?"

```bash
aur query "login authentication flow"
# Returns relevant chunks from auth code

aur show aur-abc123  # Get full details of top result
```

### Example 2: Finding Implementation

**User**: "Where do we handle rate limiting?"

```bash
aur mem search "rate limit"
# Returns chunks containing rate limiting code
```

## Error Handling

### "No index found"
Run `aur mem index .` to create the index.

### "Low relevance results"
Try different query terms or use `aur mem search` for exact text.

## Resources

- Full docs: docs/cli/CLI_USAGE_GUIDE.md
- Architecture: docs/architecture/SOAR_ARCHITECTURE.md
```

---

## Lesson 5: Git-Backed Memory

### The Problem

Local SQLite is fast, but how do you share memory across machines or team members?

### How Beads Solves It

Three-layer architecture:

```
CLI ──> SQLite (fast, local) ──> JSONL (git-tracked) ──> Git Remote
```

- **SQLite**: Local working copy (gitignored), fast queries
- **JSONL**: One JSON line per entity, merge-friendly, git-tracked
- **Git**: Distribution without a central server

**Sync flow**:
```bash
bd sync
# 1. Export dirty SQLite rows to JSONL
# 2. Commit JSONL changes
# 3. Pull from remote
# 4. Import new JSONL lines to SQLite
# 5. Push to remote
```

### Aurora Should Consider This

For team/multi-machine scenarios:

```
.aurora/
├── chunks.db        # SQLite (gitignored) - fast local queries
├── chunks.jsonl     # Git-tracked - portable chunk metadata
└── embeddings.bin   # Binary (gitignored) - too large for git
```

**Export format** (chunks.jsonl):
```json
{"id": "aur-abc", "file": "src/auth.py", "symbol": "authenticate", "hash": "sha256...", "chunk_type": "function"}
{"id": "aur-def", "file": "src/auth.py", "symbol": "validate_token", "hash": "sha256...", "chunk_type": "function"}
```

Embeddings stay local (regenerated on each machine).

---

## Lesson 6: Workspace Context

### The Problem

MCP servers run as separate processes. How do they know which project/directory to use?

### How Beads Solves It

**Persistent workspace context** that survives across MCP tool calls:

```python
# Module-level storage (not os.environ, which doesn't persist)
_workspace_context: dict[str, str] = {}

@mcp.tool("context")
async def context(action: str = "show", workspace_root: str = None):
    """Set or show workspace context."""

    if action == "set":
        # Resolve to git repo root
        resolved = resolve_git_root(workspace_root)

        # Store persistently
        _workspace_context["WORKSPACE"] = resolved
        _workspace_context["DB_PATH"] = find_database(resolved)

        return f"Context set: {resolved}"

    elif action == "show":
        return f"Workspace: {_workspace_context.get('WORKSPACE', 'NOT SET')}"
```

**Usage pattern**:
```
# First call: set context
context(workspace_root="/home/user/myproject")

# Subsequent calls: context persists
ready()  # Uses /home/user/myproject automatically
create("New task")  # Same workspace
```

### Aurora Should Do This

```python
# aurora_mcp/server.py

_aurora_context = {
    "workspace": None,
    "index_path": None,
    "config": None
}

@mcp.tool("context")
async def aurora_context(
    action: str = "show",
    workspace: str = None
):
    """Manage Aurora workspace context."""

    if action == "set" and workspace:
        resolved = resolve_workspace(workspace)
        _aurora_context["workspace"] = resolved
        _aurora_context["index_path"] = find_aurora_index(resolved)

        return f"Aurora context set:\n  Workspace: {resolved}\n  Index: {_aurora_context['index_path']}"

    return f"Workspace: {_aurora_context.get('workspace', 'NOT SET')}"
```

---

## Implementation Roadmap

### Phase 1: Context Optimization (Quick Wins)

**Goal**: Reduce token usage by 80%

1. **Add `ChunkMinimal` model**
   - File: `packages/core/src/aurora_core/types.py`
   - Fields: id, file_path, symbol_name, relevance, preview

2. **Implement result compaction**
   - File: `packages/mcp/src/aurora_mcp/server.py`
   - Compact when >20 results

3. **Add lazy tool schema loading**
   - Add `discover_tools()` and `get_tool_info()` MCP tools

### Phase 2: Prime Command & Hooks

**Goal**: Auto-inject context at session start

1. **Create `aur prime` command**
   - File: `packages/cli/src/aurora_cli/commands/prime.py`
   - Output: Memory stats, quick commands, quality metrics

2. **Create plugin.json**
   - File: `.claude-plugin/plugin.json`
   - Hooks: SessionStart, PreCompact

### Phase 3: Slash Commands

**Goal**: Easy-to-use shortcuts

1. **Register MCP slash commands**
   - `/aur-query`, `/aur-search`, `/aur-index`, `/aur-stats`, `/aur-show`

2. **Publish to Claude marketplace**
   - Create marketplace.json
   - Test installation flow

### Phase 4: Skills

**Goal**: Teach Claude when/how to use Aurora

1. **Create skill structure**
   ```
   skills/aurora/
   ├── SKILL.md
   ├── README.md
   └── references/
   ```

2. **Document workflows and examples**

### Phase 5: Advanced Features

**Goal**: Multi-machine support

1. **JSONL export/import**
   - Export chunk metadata (not embeddings)
   - Import and regenerate embeddings locally

2. **Workspace context management**
   - Persistent context across MCP calls

---

## File References

### Beads Files Studied

| File | Purpose | Key Learning |
|------|---------|--------------|
| `docs/ARCHITECTURE.md` | System design | Three-layer sync model |
| `docs/PLUGIN.md` | Claude integration | Plugin + hooks pattern |
| `docs/CLAUDE_INTEGRATION.md` | Integration philosophy | CLI + hooks > MCP |
| `integrations/beads-mcp/server.py` | MCP implementation | Context engineering |
| `integrations/beads-mcp/CONTEXT_ENGINEERING.md` | Token optimization | Compaction patterns |
| `cmd/bd/prime.go` | Prime command | Adaptive context injection |
| `cmd/bd/setup/claude.go` | Hook installation | Settings.json modification |
| `skills/beads/SKILL.md` | Claude skill | Structured teaching format |
| `.claude-plugin/plugin.json` | Plugin definition | Hook registration |

### Aurora Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `packages/core/src/aurora_core/types.py` | Add | ChunkMinimal model |
| `packages/mcp/src/aurora_mcp/server.py` | Modify | Add context engineering |
| `packages/cli/src/aurora_cli/commands/prime.py` | Add | Prime command |
| `.claude-plugin/plugin.json` | Add | Plugin definition |
| `.claude-plugin/marketplace.json` | Add | Marketplace entry |
| `skills/aurora/SKILL.md` | Add | Claude skill |
| `skills/aurora/README.md` | Add | Human documentation |

---

## Summary: Key Takeaways

1. **Tokens are precious** - Return minimal data by default, full details on demand
2. **Hooks beat MCP** for context injection - `aur prime` at ~500 tokens vs tool schemas at ~15k
3. **Slash commands improve UX** - `/aur-query` is faster than explaining bash commands
4. **Skills teach Claude** - Structured docs help Claude know when/how to use your tool
5. **Workspace context matters** - Know which project you're working on
6. **Git enables portability** - JSONL is merge-friendly for distributed teams

The core philosophy: **Make it easy for Claude to use your tool efficiently.**
