# Aurora Configuration Reference

Complete reference for Aurora's configuration system, including all settings, file locations, and environment variables.

**Version:** 1.1.0
**Last Updated:** 2026-01-07

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
   - [Planning Settings](#planning-settings)
   - [Agents Settings](#agents-settings)
   - [Budget Settings](#budget-settings)
   - [Logging Settings](#logging-settings)
   - [MCP Settings](#mcp-settings-dormant)
6. [Environment Variables](#environment-variables)
7. [Project vs Global Mode](#project-vs-global-mode)
8. [Troubleshooting](#troubleshooting)

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
      "~/.config/ampcode/agents",
      "~/.config/droid/agent",
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

Controls defaults for `aur soar` command.

```json
"soar": {
  "default_tool": "claude",
  "default_model": "sonnet"
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `default_tool` | string | `"claude"` | CLI tool to pipe SOAR queries to. Must be installed and in PATH. Examples: `"claude"`, `"cursor"`, `"gemini"`. |
| `default_model` | string | `"sonnet"` | Model to use. Values: `"sonnet"` or `"opus"`. |

**Supported tools:** Any CLI that accepts piped input (claude, cursor, gemini, etc.)

**Override per-command:**
```bash
aur soar "query" --tool cursor --model opus
```

**Environment variables:**
```bash
export AURORA_SOAR_TOOL=cursor
export AURORA_SOAR_MODEL=opus
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

Controls agent discovery and caching.

```json
"agents": {
  "auto_refresh": true,
  "refresh_interval_hours": 24,
  "discovery_paths": [
    "~/.claude/agents",
    "~/.config/ampcode/agents",
    "~/.config/droid/agent",
    "~/.config/opencode/agent"
  ],
  "manifest_path": "./.aurora/cache/agent_manifest.json"
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `auto_refresh` | bool | `true` | Automatically refresh agent manifest when stale. |
| `refresh_interval_hours` | int | `24` | Hours between manifest refreshes. Must be >= 1. |
| `discovery_paths` | string[] | *(see above)* | Directories to scan for agent definitions. |
| `manifest_path` | string | `"./.aurora/cache/agent_manifest.json"` | Cached agent manifest location. |

**What agents are:** Agents are specialized AI personas defined in markdown files. Aurora discovers them from standard locations used by Claude Code, Cursor, and other tools.

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
