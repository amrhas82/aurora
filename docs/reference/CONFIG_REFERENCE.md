# Aurora Configuration Reference

Complete reference for Aurora's configuration system, including all settings, file locations, and environment variables.

**Version:** 1.3.0
**Last Updated:** 2026-01-15

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration File Locations](#configuration-file-locations)
3. [Precedence Rules](#precedence-rules)
4. [Complete Configuration Example](#complete-configuration-example)
5. [Configuration Sections](#configuration-sections)
   - [LLM Settings](#llm-settings)
   - [Escalation Settings](#escalation-settings)
   - [Memory Settings](#memory-settings)
   - [Database Settings](#database-settings)
   - [Search Settings](#search-settings)
   - [SOAR Settings](#soar-settings)
   - [Spawner Settings](#spawner-settings)
   - [Headless Settings](#headless-settings)
   - [Planning Settings](#planning-settings)
   - [Agents Settings](#agents-settings)
   - [Budget Settings](#budget-settings)
   - [Logging Settings](#logging-settings)
   - [MCP Settings](#mcp-settings-dormant)
6. [Tool Paths Reference](#tool-paths-reference)
7. [Environment Variables](#environment-variables)
8. [Project vs Global Mode](#project-vs-global-mode)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Aurora uses a JSON-based configuration system that controls:

- **LLM behavior** - API keys, model selection, temperature
- **Memory indexing** - Chunk sizes, paths, auto-indexing
- **SOAR reasoning** - Default tools and models for `aur soar`
- **Planning** - Plan storage, templates, auto-increment
- **Agent discovery** - Where to find agents, refresh intervals
- **Budget tracking** - API cost limits
- **Logging** - Log levels and file locations

**Key principle:** Aurora is project-local by default. When you run `aur init` in a project, it creates a `.aurora/` directory that isolates all project-specific data.

---

## Configuration File Locations

Aurora looks for configuration in these locations (in order):

### Project Mode (when `.aurora/` exists)

| Priority | Location | Purpose |
|----------|----------|---------|
| 1 | `.aurora/config.json` | Project-specific settings |
| 2 | Built-in defaults | Fallback values |

### Global Mode (no `.aurora/` directory)

| Priority | Location | Purpose |
|----------|----------|---------|
| 1 | `./aurora.config.json` | Current directory config |
| 2 | `~/.aurora/config.json` | User-wide settings |
| 3 | Built-in defaults | Fallback values |

### Special Paths

| Path | Purpose | Scope |
|------|---------|-------|
| `~/.aurora/config.json` | Global user configuration | User-wide |
| `.aurora/config.json` | Project configuration | Project-only |
| `~/.aurora/budget_tracker.json` | API usage tracking | **Always global** |

**Note:** The `AURORA_HOME` environment variable can override `~/.aurora` to a custom location.

---

## Precedence Rules

Configuration values are resolved in this order (highest to lowest):

```
1. CLI flags           (e.g., --tool cursor)
2. Environment vars    (e.g., AURORA_SOAR_TOOL=cursor)
3. Config file         (e.g., soar.default_tool in config.json)
4. Built-in defaults   (e.g., "claude")
```

**Example:**
```bash
# Config file has: soar.default_tool = "cursor"
# Environment has: AURORA_SOAR_TOOL=gemini
# CLI has: --tool claude

aur soar "query"           # Uses gemini (env var)
aur soar "query" -t claude # Uses claude (CLI flag wins)
```

---

## Complete Configuration Example

Here's a fully documented `config.json` with all available settings:

```json
{
  "version": "1.1.0",

  "llm": {
    "provider": "anthropic",
    "anthropic_api_key": null,
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.7,
    "max_tokens": 4096
  },

  "escalation": {
    "threshold": 0.7,
    "enable_keyword_only": false,
    "force_mode": null
  },

  "memory": {
    "auto_index": true,
    "index_paths": ["."],
    "chunk_size": 1000,
    "overlap": 200
  },

  "database": {
    "path": "./.aurora/memory.db"
  },

  "search": {
    "min_semantic_score": 0.70
  },

  "soar": {
    "default_tool": "claude",
    "default_model": "sonnet"
  },

  "spawner": {
    "tool": "claude",
    "model": "sonnet",
    "max_retries": 2,
    "fallback_to_llm": true
  },

  "headless": {
    "tools": ["claude"],
    "strategy": "first_success",
    "parallel": true,
    "max_iterations": 10,
    "timeout": 600,
    "tool_configs": {
      "claude": {
        "priority": 1,
        "timeout": 600,
        "flags": ["--print", "--dangerously-skip-permissions"],
        "input_method": "argument",
        "env": {},
        "enabled": true,
        "max_retries": 2,
        "retry_delay": 1.0
      },
      "opencode": {
        "priority": 2,
        "timeout": 600,
        "flags": [],
        "input_method": "stdin",
        "env": {},
        "enabled": true,
        "max_retries": 2,
        "retry_delay": 1.0
      }
    },
    "routing_rules": []
  },

  "planning": {
    "base_dir": "./.aurora/plans",
    "template_dir": null,
    "auto_increment": true,
    "archive_on_complete": false
  },

  "agents": {
    "auto_refresh": true,
    "refresh_interval_hours": 24,
    "discovery_paths": [
      "~/.claude/agents",
      "~/.cursor/agents",
      "~/.factory/droids",
      "~/.config/opencode/agent"
    ],
    "manifest_path": "./.aurora/cache/agent_manifest.json"
  },

  "budget": {
    "limit": 10.0,
    "tracker_path": "~/.aurora/budget_tracker.json"
  },

  "logging": {
    "level": "INFO",
    "file": "./.aurora/logs/aurora.log"
  },

  "mcp": {
    "always_on": false,
    "log_file": "./.aurora/logs/mcp.log",
    "max_results": 10
  }
}
```

---

## Configuration Sections

### LLM Settings

Controls the Language Model used for SOAR reasoning phases.

```json
"llm": {
  "provider": "anthropic",
  "anthropic_api_key": null,
  "model": "claude-3-5-sonnet-20241022",
  "temperature": 0.7,
  "max_tokens": 4096
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `provider` | string | `"anthropic"` | LLM provider. Currently only `"anthropic"` is supported. |
| `anthropic_api_key` | string\|null | `null` | API key for Anthropic. **Recommended:** Use `ANTHROPIC_API_KEY` env var instead for security. |
| `model` | string | `"claude-3-5-sonnet-20241022"` | Model ID for API calls. Used by internal SOAR phases. |
| `temperature` | float | `0.7` | Response randomness (0.0 = deterministic, 1.0 = creative). Range: 0.0-1.0. |
| `max_tokens` | int | `4096` | Maximum tokens in LLM response. Must be positive. |

**Security note:** Never commit API keys to version control. Use environment variables:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

---

### Escalation Settings

Controls when Aurora escalates queries to full SOAR reasoning vs. direct LLM calls.

```json
"escalation": {
  "threshold": 0.7,
  "enable_keyword_only": false,
  "force_mode": null
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `threshold` | float | `0.7` | Complexity score threshold for SOAR escalation. Queries scoring above this use full 9-phase pipeline. Range: 0.0-1.0. |
| `enable_keyword_only` | bool | `false` | If `true`, only use keyword matching for escalation (faster but less accurate). |
| `force_mode` | string\|null | `null` | Force all queries to specific mode. Values: `"direct"` (skip SOAR), `"aurora"` (always use SOAR), or `null` (auto-detect). |

**When to adjust:**
- Lower `threshold` (e.g., 0.5) → More queries use full SOAR (slower, more thorough)
- Higher `threshold` (e.g., 0.9) → Fewer queries use SOAR (faster, simpler answers)
- Set `force_mode: "direct"` → Bypass SOAR entirely for speed

---

### Memory Settings

Controls how Aurora indexes and chunks your codebase.

```json
"memory": {
  "auto_index": true,
  "index_paths": ["."],
  "chunk_size": 1000,
  "overlap": 200
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `auto_index` | bool | `true` | Automatically index on `aur init`. Set `false` for manual control. |
| `index_paths` | string[] | `["."]` | Directories to index. Relative to project root. |
| `chunk_size` | int | `1000` | Maximum characters per chunk. Must be >= 100. |
| `overlap` | int | `200` | Characters of overlap between chunks for context continuity. Must be >= 0. |

**How chunking works:**
- Code files are parsed with tree-sitter into functions/classes
- Documentation is split at section boundaries
- `chunk_size` limits each chunk's length
- `overlap` ensures context isn't lost at boundaries

**Example: Index only src/ and docs/**
```json
"memory": {
  "index_paths": ["src/", "docs/"]
}
```

---

### Database Settings

Controls where Aurora stores the memory database.

```json
"database": {
  "path": "./.aurora/memory.db"
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `path` | string | `"./.aurora/memory.db"` | SQLite database path. Supports `~` expansion. |

**Path patterns:**
- `./.aurora/memory.db` → Project-local (recommended)
- `~/.aurora/memory.db` → Global/shared across projects
- `/absolute/path/memory.db` → Explicit location

**Override per-command:**
```bash
aur mem search "query" --db-path /tmp/test.db
```

---

### Search Settings

Controls search result filtering.

```json
"search": {
  "min_semantic_score": 0.70
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `min_semantic_score` | float | `0.70` | Minimum score for search results. Range: 0.0-1.0. Higher = stricter filtering. |

**Score interpretation:**
- `0.70` = Moderate match (default, balanced precision/recall)
- `0.85` = High confidence matches only
- `0.50` = Include more potential matches

---

### SOAR Settings

Controls defaults for `aur soar` command and agent execution behavior.

```json
"soar": {
  "default_tool": "claude",
  "default_model": "sonnet",
  "agent_timeout_seconds": 300,
  "max_concurrent_agents": 5,
  "enable_early_failure_detection": true,
  "timeout_policy": "default"
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `default_tool` | string | `"claude"` | CLI tool to pipe SOAR queries to. Must be installed and in PATH. Examples: `"claude"`, `"cursor"`, `"gemini"`. |
| `default_model` | string | `"sonnet"` | Model to use. Values: `"sonnet"` or `"opus"`. |
| `agent_timeout_seconds` | int | `300` | Maximum execution time for spawned agents (5 minutes). Range: 60-600s. |
| `max_concurrent_agents` | int | `5` | Maximum parallel agent spawns. Range: 1-10. |
| `enable_early_failure_detection` | bool | `true` | Enable early failure detection for faster error handling. |
| `timeout_policy` | string | `"default"` | Timeout policy: `"default"`, `"patient"`, or `"fast_fail"`. |

**Timeout Policies:**
- `"default"`: 60s initial, 300s max, 30s no-activity (balanced)
- `"patient"`: 120s initial, 600s max, 120s no-activity (large tasks)
- `"fast_fail"`: 60s fixed, 15s no-activity (fast feedback)

**Early Failure Detection:**
When enabled, SOAR detects agent failures in 5-15s vs 60-300s timeout by monitoring:
- Error patterns: rate limits, auth failures, API errors
- No-activity: detects stuck agents based on policy
- Immediate circuit breaker updates

**Override per-command:**
```bash
aur soar "query" --tool cursor --model opus
```

**Environment variables:**
```bash
export AURORA_SOAR_TOOL=cursor
export AURORA_SOAR_MODEL=opus
export AURORA_SOAR_TIMEOUT=300
export AURORA_SOAR_TIMEOUT_POLICY=fast_fail
```

**Monitoring:**
```bash
# View early terminations
aur soar "query" --verbose 2>&1 | grep "early termination"

# Check logs for detection times
cat .aurora/logs/soar-*.log | grep "detection_time"
```

---

### Spawner Settings

Controls agent spawning behavior, recovery, and circuit breaker.

```json
"spawner": {
  "tool": "claude",
  "model": "sonnet",
  "recovery": {
    "strategy": "retry_then_fallback",
    "max_retries": 2,
    "fallback_to_llm": true,
    "base_delay": 1.0,
    "max_delay": 30.0,
    "backoff_factor": 2.0,
    "jitter": true,
    "circuit_breaker_enabled": true,
    "agent_overrides": {}
  },
  "circuit_breaker": {
    "failure_threshold": 2,
    "reset_timeout": 120,
    "failure_window": 300
  }
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `tool` | string | `"claude"` | CLI tool for spawning agents. Must be in PATH. |
| `model` | string | `"sonnet"` | Model to pass to the tool. |

**Recovery Settings (`spawner.recovery`):**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `strategy` | string | `"retry_then_fallback"` | Recovery strategy: `retry_then_fallback`, `retry_same`, `fallback_only`, `no_recovery` |
| `preset` | string | - | Use preset: `default`, `aggressive_retry`, `fast_fallback`, `patient`, `no_recovery` |
| `max_retries` | int | `2` | Maximum retry attempts per task |
| `fallback_to_llm` | bool | `true` | Fall back to direct LLM if agent fails |
| `base_delay` | float | `1.0` | Initial delay between retries (seconds) |
| `max_delay` | float | `30.0` | Maximum delay cap (seconds) |
| `backoff_factor` | float | `2.0` | Exponential backoff multiplier |
| `jitter` | bool | `true` | Add randomness to prevent thundering herd |
| `circuit_breaker_enabled` | bool | `true` | Enable circuit breaker protection |
| `agent_overrides` | object | `{}` | Per-agent policy overrides |

**Recovery Strategies:**

| Strategy | Retries | Fallback | Use Case |
|----------|---------|----------|----------|
| `retry_then_fallback` | 2 | Yes | Default - balanced reliability |
| `retry_same` | 5 | No | Critical agents that must succeed |
| `fallback_only` | 0 | Yes | Fast failure, let LLM handle it |
| `no_recovery` | 0 | No | Fail-fast for debugging |

**Recovery Presets:**

| Preset | Retries | Fallback | Base Delay | Backoff |
|--------|---------|----------|------------|---------|
| `default` | 2 | Yes | 1.0s | 2x |
| `aggressive_retry` | 5 | No | 0.5s | 2x |
| `fast_fallback` | 0 | Yes | - | - |
| `patient` | 3 | Yes | 2.0s | 3x |
| `no_recovery` | 0 | No | - | - |

**Per-Agent Overrides:**

```json
"spawner": {
  "recovery": {
    "agent_overrides": {
      "slow-agent": {
        "max_retries": 5,
        "base_delay": 2.0
      },
      "critical-agent": {
        "strategy": "retry_same",
        "max_retries": 10
      }
    }
  }
}
```

**Circuit Breaker Settings (`spawner.circuit_breaker`):**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `failure_threshold` | int | `2` | Failures to open circuit |
| `reset_timeout` | int | `120` | Seconds before testing recovery |
| `failure_window` | int | `300` | Time window for counting failures |

**How recovery works:**

1. Task fails → classify error (transient/permanent/timeout/resource)
2. Permanent errors → fail immediately (no retry)
3. Transient errors → retry with exponential backoff (1s, 2s, 4s)
4. After `max_retries` exhausted → fall back to direct LLM (if enabled)
5. After `failure_threshold` failures within `failure_window` → circuit opens, agent skipped

**Error Categories:**

| Category | Pattern Examples | Behavior |
|----------|------------------|----------|
| `transient` | Rate limit, 429, connection reset | Retry with backoff |
| `timeout` | Timed out, deadline exceeded | Retry with longer timeout |
| `resource` | Quota exceeded, out of memory | Retry after delay |
| `permanent` | Auth failed, 401, invalid API key | Fail immediately |

**Environment variables:**
```bash
export AURORA_SPAWN_TOOL=cursor
export AURORA_SPAWN_MODEL=opus
```

---

### Headless Settings

Controls the `aur headless` autonomous execution loop with multi-tool support.

```json
"headless": {
  "tools": ["claude", "opencode"],
  "strategy": "first_success",
  "parallel": true,
  "max_iterations": 10,
  "timeout": 600,
  "tool_configs": {
    "claude": {
      "priority": 1,
      "timeout": 600,
      "flags": ["--print", "--dangerously-skip-permissions"],
      "input_method": "argument",
      "env": {},
      "working_dir": null,
      "enabled": true,
      "max_retries": 2,
      "retry_delay": 1.0
    },
    "opencode": {
      "priority": 2,
      "timeout": 600,
      "flags": [],
      "input_method": "stdin",
      "env": {},
      "working_dir": null,
      "enabled": true,
      "max_retries": 2,
      "retry_delay": 1.0
    }
  },
  "routing_rules": []
}
```

**General Settings:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `tools` | string[] | `["claude"]` | Default tools to use. Can specify multiple for multi-tool mode. |
| `strategy` | string | `"first_success"` | Aggregation strategy: `first_success`, `all_complete`, `voting`, `best_score`, `merge`. |
| `parallel` | bool | `true` | Run multiple tools in parallel (true) or sequentially (false). |
| `max_iterations` | int | `10` | Maximum execution loop iterations. |
| `timeout` | int | `600` | Global per-tool timeout in seconds (can be overridden per-tool). |
| `tool_configs` | object | *(see below)* | Per-tool configuration settings. |
| `routing_rules` | array | `[]` | Task-based routing rules for tool selection. |

**Per-Tool Configuration (`tool_configs.<tool>`):**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `priority` | int | `1-N` | Lower = higher priority in multi-tool mode. |
| `timeout` | int | `600` | Tool-specific timeout (overrides global). |
| `flags` | string[] | `[]` | Command-line flags passed to the tool. |
| `input_method` | string | `"stdin"` | How to pass context: `argument`, `stdin`, `file`, `pipe`. |
| `env` | object | `{}` | Tool-specific environment variables. |
| `working_dir` | string\|null | `null` | Working directory override (`null` = use cwd). |
| `enabled` | bool | `true` | Enable/disable tool without removing config. |
| `max_retries` | int | `2` | Tool-specific retry count on failure. |
| `retry_delay` | float | `1.0` | Base delay between retries (seconds). |

**Aggregation Strategies:**

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `first_success` | Return first successful result, cancel others | Fast completion, redundancy |
| `all_complete` | Wait for all tools, return best result | Thorough comparison |
| `voting` | Consensus from 3+ tools (majority wins) | High confidence tasks |
| `best_score` | Score by success, output length, speed | Quality optimization |
| `merge` | Combine outputs from all tools | Comprehensive output |

**Adding a New Tool:**

```json
"headless": {
  "tools": ["claude", "opencode", "cursor"],
  "tool_configs": {
    "cursor": {
      "priority": 3,
      "timeout": 300,
      "flags": ["--no-tty"],
      "input_method": "stdin",
      "env": {"CURSOR_API_KEY": "..."},
      "enabled": true
    }
  }
}
```

**Task-Based Routing Rules:**

Route specific tasks to specific tools:

```json
"routing_rules": [
  {
    "pattern": ".*test.*",
    "tools": ["claude"]
  },
  {
    "condition": "file_type == 'python'",
    "tools": ["opencode", "claude"]
  }
]
```

**Environment Variables:**

```bash
export AURORA_HEADLESS_TOOLS=claude,opencode
export AURORA_HEADLESS_STRATEGY=all_complete
export AURORA_HEADLESS_PARALLEL=true
export AURORA_HEADLESS_MAX_ITERATIONS=15
export AURORA_HEADLESS_TIMEOUT=300
```

**CLI Usage:**

```bash
# Single tool
aur headless -t claude --max=10

# Multiple tools in parallel
aur headless -t claude -t opencode --max=10

# Multiple tools with voting
aur headless -t claude -t opencode -t cursor --strategy voting

# Sequential multi-tool (round-robin)
aur headless -t claude -t opencode --sequential

# Show effective configuration
aur headless --show-config

# List available tools
aur headless --list-tools
```

---

### Planning Settings

Controls plan storage and behavior.

```json
"planning": {
  "base_dir": "./.aurora/plans",
  "template_dir": null,
  "auto_increment": true,
  "archive_on_complete": false
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `base_dir` | string | `"./.aurora/plans"` | Directory for plan files. |
| `template_dir` | string\|null | `null` | Custom templates directory. `null` = use package defaults. |
| `auto_increment` | bool | `true` | Auto-generate sequential plan IDs (plan-001, plan-002, etc.). |
| `archive_on_complete` | bool | `false` | Automatically archive plans when completed. |

**Environment variables:**
```bash
export AURORA_PLANS_DIR=/custom/plans
export AURORA_TEMPLATE_DIR=/custom/templates
export AURORA_PLANNING_AUTO_INCREMENT=false
export AURORA_PLANNING_ARCHIVE_ON_COMPLETE=true
```

---

### Agents Settings

Controls agent discovery and caching. Aurora now supports **20 AI coding tools** with automatic discovery from their conventional agent locations.

```json
"agents": {
  "auto_refresh": true,
  "refresh_interval_hours": 24,
  "discovery_paths": [
    "~/.claude/agents",
    "~/.cursor/agents",
    "~/.factory/droids",
    "~/.config/opencode/agent"
  ],
  "manifest_path": "./.aurora/cache/agent_manifest.json"
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `auto_refresh` | bool | `true` | Automatically refresh agent manifest when stale. |
| `refresh_interval_hours` | int | `24` | Hours between manifest refreshes. Must be >= 1. |
| `discovery_paths` | string[] | *(all 20 tools)* | Directories to scan for agent definitions. See [Tool Paths Reference](#tool-paths-reference) for complete list. |
| `manifest_path` | string | `"./.aurora/cache/agent_manifest.json"` | Cached agent manifest location. |

**What agents are:** Agents are specialized AI personas defined in markdown files. Aurora discovers them from standard locations used by Claude Code, Cursor, Factory Droid, OpenCode, and 16 other supported tools.

**Agent discovery during init:** When you run `aur init --tools=<tool>`, Aurora automatically discovers agents from that tool's conventional location and reports the count.

**Custom discovery paths:** Add your own agent directories:
```json
"agents": {
  "discovery_paths": [
    "~/.claude/agents",
    "~/my-custom-agents"
  ]
}
```

---

### Budget Settings

Controls API usage tracking and limits.

```json
"budget": {
  "limit": 10.0,
  "tracker_path": "~/.aurora/budget_tracker.json"
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `limit` | float | `10.0` | Budget limit in USD. Aurora warns when approaching limit. Must be >= 0. |
| `tracker_path` | string | `"~/.aurora/budget_tracker.json"` | **Always global** - tracks usage across all projects. |

**Note:** The budget tracker is intentionally global so you have one view of total API spending across all projects.

**Check usage:**
```bash
aur budget status
```

---

### Logging Settings

Controls log output.

```json
"logging": {
  "level": "INFO",
  "file": "./.aurora/logs/aurora.log"
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `level` | string | `"INFO"` | Log verbosity. Values: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`. |
| `file` | string | `"./.aurora/logs/aurora.log"` | Log file path. |

**Environment variable:**
```bash
export AURORA_LOGGING_LEVEL=DEBUG
```

---

### MCP Settings (Dormant)

MCP (Model Context Protocol) support is **dormant** as of v0.5.0. These settings are preserved for potential future use.

```json
"mcp": {
  "always_on": false,
  "log_file": "./.aurora/logs/mcp.log",
  "max_results": 10
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `always_on` | bool | `false` | Enable MCP server (dormant). |
| `log_file` | string | `"./.aurora/logs/mcp.log"` | MCP-specific log file. |
| `max_results` | int | `10` | Maximum results returned by MCP queries. Must be >= 1. |

See [MCP Deprecation](MCP_DEPRECATION.md) for details on why MCP was deprecated.

---

## Tool Paths Reference

Aurora maintains a centralized registry of conventional paths for all **20 supported AI coding tools**. Each tool has four path types:

| Path Type | Description | Example |
|-----------|-------------|---------|
| `agents` | Global directory for agent persona files | `~/.claude/agents` |
| `commands` | Global directory for user commands | `~/.claude/commands` |
| `slash_commands` | Project-local Aurora slash commands | `.claude/commands/aur` |
| `mcp` | MCP server configuration file | `~/.claude/mcp_servers.json` |

### Complete Tool Paths Table

| Tool ID | Agents Path | Slash Commands Path | MCP Config |
|---------|-------------|---------------------|------------|
| `amazon-q` | `~/.aws/amazonq/cli-agents` | `.amazonq/prompts` | `~/.aws/amazonq/mcp.json` |
| `antigravity` | `~/.config/antigravity/agents` | `.agent/workflows` | — |
| `auggie` | `~/.config/auggie/agents` | `.augment/commands` | — |
| `claude` | `~/.claude/agents` | `.claude/commands/aur` | `~/.claude/mcp_servers.json` |
| `cline` | `~/.cline/agents` | `.clinerules/workflows` | `~/.cline/mcp_settings.json` |
| `codebuddy` | `~/.config/codebuddy/agents` | `.codebuddy/commands/aurora` | — |
| `codex` | `~/.codex/agents` | `.codex/prompts` | — |
| `costrict` | `~/.config/costrict/agents` | `.cospec/aurora/commands` | — |
| `crush` | `~/.config/crush/agents` | `.crush/commands/aurora` | — |
| `cursor` | `~/.cursor/agents` | `.cursor/commands` | — |
| `factory` | `~/.factory/droids` | `.factory/commands` | — |
| `gemini` | `~/.config/gemini-cli/agents` | `.gemini/commands/aurora` | — |
| `github-copilot` | `~/.config/github-copilot/agents` | `.github/prompts` | — |
| `iflow` | `~/.config/iflow/agents` | `.iflow/commands` | — |
| `kilocode` | `~/.config/kilocode/agents` | `.kilocode/workflows` | — |
| `opencode` | `~/.config/opencode/agent` | `.opencode/command` | — |
| `qoder` | `~/.config/qoder/agents` | `.qoder/commands/aurora` | — |
| `qwen` | `~/.config/qwen-coder/agents` | `.qwen/commands` | — |
| `roocode` | `~/.config/roocode/agents` | `.roo/commands` | — |
| `windsurf` | `~/.windsurf/agents` | `.windsurf/workflows` | — |

### Path Type Details

#### Agents Path (Global)
Where agent persona markdown files are stored globally for each tool:
- Used by Aurora's agent discovery system
- Scanned during `aur init` and `aur agents list`
- Contains `.md` files with agent definitions

#### Commands Path (Global)
Where user-defined slash commands are stored globally:
- Tool-specific location for custom commands
- Not used by Aurora directly (for reference)

#### Slash Commands Path (Project-Local)
Where Aurora writes its project-local slash commands:
- Created during `aur init --tools=<tool>`
- Contains Aurora commands like `search`, `plan`, `get`, etc.
- Relative to project root (no `~` prefix)

#### MCP Config (Global)
Where MCP server configuration is stored:
- Only configured for tools with known MCP support
- MCP is currently dormant in Aurora

### Programmatic Access

Access tool paths programmatically:

```python
from aurora_cli.configurators.slash.paths import (
    get_tool_paths,
    get_all_agent_paths,
    get_all_tools,
    TOOL_PATHS,
)

# Get paths for a specific tool
claude_paths = get_tool_paths("claude")
print(claude_paths.agents)         # ~/.claude/agents
print(claude_paths.slash_commands) # .claude/commands/aur
print(claude_paths.mcp)            # ~/.claude/mcp_servers.json

# Get all agent discovery paths (all 20 tools)
all_agent_paths = get_all_agent_paths()
# Returns: ['~/.aws/amazonq/cli-agents', '~/.config/antigravity/agents', ...]

# List all tool IDs
tools = get_all_tools()
# Returns: ['amazon-q', 'antigravity', 'auggie', 'claude', ...]
```

### Sources

Path information was researched from official documentation:
- **OpenCode**: https://opencode.ai/docs/config/
- **Factory Droid**: https://docs.factory.ai/cli/configuration/custom-droids
- **Cline**: https://docs.cline.bot/cline-cli/cli-reference
- **Cursor**: https://cursor.com/docs/cli/reference/configuration
- **Codex**: https://developers.openai.com/codex/config-advanced/
- **Amazon Q**: https://docs.aws.amazon.com/amazonq/

---

## Environment Variables

All supported environment variables:

| Variable | Config Equivalent | Description |
|----------|-------------------|-------------|
| `AURORA_HOME` | *(config location)* | Override `~/.aurora` directory |
| `ANTHROPIC_API_KEY` | `llm.anthropic_api_key` | Anthropic API key (recommended) |
| `AURORA_ESCALATION_THRESHOLD` | `escalation.threshold` | Float 0.0-1.0 |
| `AURORA_LOGGING_LEVEL` | `logging.level` | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `AURORA_PLANS_DIR` | `planning.base_dir` | Plans directory path |
| `AURORA_TEMPLATE_DIR` | `planning.template_dir` | Templates directory path |
| `AURORA_PLANNING_AUTO_INCREMENT` | `planning.auto_increment` | true/false |
| `AURORA_PLANNING_ARCHIVE_ON_COMPLETE` | `planning.archive_on_complete` | true/false |
| `AURORA_SOAR_TOOL` | `soar.default_tool` | CLI tool name |
| `AURORA_SOAR_MODEL` | `soar.default_model` | sonnet/opus |
| `AURORA_SPAWN_TOOL` | `spawner.tool` | CLI tool for spawning |
| `AURORA_SPAWN_MODEL` | `spawner.model` | Model for spawning |
| `AURORA_HEADLESS_TOOLS` | `headless.tools` | Comma-separated tool names |
| `AURORA_HEADLESS_STRATEGY` | `headless.strategy` | Aggregation strategy |
| `AURORA_HEADLESS_PARALLEL` | `headless.parallel` | true/false |
| `AURORA_HEADLESS_MAX_ITERATIONS` | `headless.max_iterations` | Max loop iterations |
| `AURORA_HEADLESS_TIMEOUT` | `headless.timeout` | Per-tool timeout (seconds) |

**Example .bashrc/.zshrc:**
```bash
# Aurora configuration
export ANTHROPIC_API_KEY=sk-ant-...
export AURORA_SOAR_TOOL=cursor
export AURORA_LOGGING_LEVEL=DEBUG
```

---

## Project vs Global Mode

Aurora operates in two modes based on whether `.aurora/` exists:

### Project Mode (Recommended)

When `.aurora/` directory exists in current directory:

```
your-project/
├── .aurora/
│   ├── config.json      ← Project config (optional)
│   ├── memory.db        ← Project memory
│   ├── plans/           ← Project plans
│   ├── cache/           ← Project cache
│   └── logs/            ← Project logs
├── src/
└── ...
```

**Benefits:**
- Complete project isolation
- Config travels with project (can be committed)
- No interference between projects

**Create project mode:**
```bash
cd your-project
aur init
```

### Global Mode

When no `.aurora/` exists, Aurora uses global configuration:

```
~/.aurora/
├── config.json          ← Global config
├── memory.db            ← Shared memory (if configured)
├── budget_tracker.json  ← Always global
└── logs/
```

**When to use global:**
- Quick queries without project setup
- Shared settings across projects
- Testing Aurora features

---

## Troubleshooting

### Config file not loading

**Check location:**
```bash
# See which config file Aurora finds
cat .aurora/config.json 2>/dev/null || cat ~/.aurora/config.json
```

**Validate JSON syntax:**
```bash
python -m json.tool .aurora/config.json
```

### Environment variable not working

**Check it's exported:**
```bash
echo $AURORA_SOAR_TOOL
# Should show value, not empty
```

**Check spelling:**
```bash
env | grep AURORA
```

### API key issues

**Verify key is set:**
```bash
echo $ANTHROPIC_API_KEY | head -c 20
# Should show: sk-ant-...
```

**Never put API keys in config files that might be committed:**
```bash
# Good: environment variable
export ANTHROPIC_API_KEY=sk-ant-...

# Bad: in config.json (might be committed)
"anthropic_api_key": "sk-ant-..."
```

### Reset to defaults

**Remove project config:**
```bash
rm .aurora/config.json
```

**Remove global config:**
```bash
rm ~/.aurora/config.json
```

Aurora will use built-in defaults.

---

## See Also

- [Commands Reference](../COMMANDS.md) - CLI command documentation
- [SOAR Reasoning](SOAR.md) - 9-phase cognitive pipeline
- [ML Models Guide](ML_MODELS.md) - Custom embedding models
- [MCP Deprecation](MCP_DEPRECATION.md) - Why MCP was deprecated
- [Error Catalog](cli/ERROR_CATALOG.md) - Error codes and solutions
