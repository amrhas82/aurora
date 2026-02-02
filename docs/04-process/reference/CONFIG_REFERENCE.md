# Aurora Configuration Reference

Complete reference for Aurora's configuration system, including defaults, customization, file locations, and environment variables.

**Version:** 1.4.0
**Last Updated:** 2026-01-16
**Config System:** Simplified dict-based (v0.7.0+)

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration Architecture](#configuration-architecture)
3. [File Locations](#file-locations)
4. [Precedence Rules](#precedence-rules)
5. [Configuration Sections](#configuration-sections)
6. [Environment Variables](#environment-variables)
7. [Customization Guide](#customization-guide)
8. [Migration Notes](#migration-notes)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Aurora uses a **dict-based JSON configuration system** that merges:
- **Built-in defaults** (`defaults.json` in the CLI package)
- **User config** (`~/.aurora/config.json` or `./.aurora/config.json`)
- **Environment variables** (highest priority)

**Key principles:**
- **Project-local by default** - `aur init` creates `.aurora/` for project isolation
- **Sensible defaults** - Works out-of-the-box with minimal configuration
- **Hierarchical override** - CLI flags > env vars > config file > defaults

---

## Configuration Architecture

### System Overview

```
┌─────────────────────────────────────────────┐
│  CLI Command (aur soar, aur goals, etc.)   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│         Config Loading (config.py)          │
│                                             │
│  1. Load defaults.json (built-in)          │
│  2. Merge user config (if exists)          │
│  3. Apply environment overrides            │
│  4. Return dict or Config wrapper          │
└─────────────────────────────────────────────┘
```

### Built-in Defaults

Location: `packages/cli/src/aurora_cli/defaults.json`

This file contains **all** default configuration values. You never need to edit this file - it's part of the Aurora package. Your customizations go in your user config file.

**Why dict-based?**
- Simple to read and modify
- Supports nested structure naturally
- Easy to merge user overrides
- No schema validation overhead
- Direct JSON mapping

### Config Class Wrapper

For backward compatibility, Aurora provides a `Config` class that wraps the dict:

```python
from aurora_cli.config import Config, load_config

# Dict access (new way)
config_dict = load_config()
db_path = config_dict["storage"]["path"]

# Wrapper access (backward compat)
config = Config()
db_path = config.db_path
```

---

## File Locations

### Project Mode (Recommended)

After running `aur init` in a project directory:

| File | Purpose | Scope |
|------|---------|-------|
| `./.aurora/config.json` | Project-specific settings | This project only |
| `./.aurora/memory.db` | Project code index | This project only |
| `./.aurora/plans/` | Project plans | This project only |
| `~/.aurora/budget_tracker.json` | API usage tracking | **Global** (shared) |

### Global Mode

Without `aur init`, Aurora uses:

| Priority | Location | Purpose |
|----------|----------|---------|
| 1 | `./aurora.config.json` | Current directory config |
| 2 | `~/.aurora/config.json` | User-wide settings |
| 3 | Built-in defaults | Package defaults |

### Special Paths

- **`AURORA_HOME`** environment variable can override `~/.aurora` location
- **Budget tracker** is always global to track total API usage across all projects
- **Agent discovery** searches multiple global paths (see `agents.discovery_paths`)

---

## Precedence Rules

Configuration values are resolved in this order (highest to lowest priority):

```
1. CLI Flags           (e.g., aur soar "query" --tool opencode)
2. Environment Vars    (e.g., AURORA_SOAR_TOOL=gemini)
3. User Config File    (e.g., ~/.aurora/config.json)
4. Built-in Defaults   (e.g., packages/cli/src/aurora_cli/defaults.json)
```

**Example Resolution:**

```bash
# defaults.json has: soar.default_tool = "claude"
# ~/.aurora/config.json has: soar.default_tool = "cursor"
# Environment has: AURORA_SOAR_TOOL=gemini
# CLI has: --tool opencode

aur soar "query"              # Uses cursor (from config file)
AURORA_SOAR_TOOL=gemini aur soar "query"  # Uses gemini (env var)
aur soar "query" --tool opencode          # Uses opencode (CLI flag wins)
```

---

## Configuration Sections

### Storage

Controls where Aurora stores its database and how it connects.

```json
{
  "storage": {
    "type": "sqlite",
    "path": "./.aurora/memory.db",
    "max_connections": 10,
    "timeout_seconds": 5
  }
}
```

**Fields:**
- `type` - Database type (currently only "sqlite" supported)
- `path` - Database file location (project-local by default)
- `max_connections` - SQLite connection pool size
- `timeout_seconds` - Query timeout

**Project-local pattern:**
- `./.aurora/memory.db` - Keeps index with your project
- `~/.aurora/memory.db` - Global index (not recommended)

---

### LLM Settings

Configure language model behavior for reasoning and decomposition.

```json
{
  "llm": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "base_url": null,
    "timeout_seconds": 30,
    "temperature": 0.7,
    "max_tokens": 4096
  }
}
```

**Fields:**
- `provider` - LLM provider (currently "anthropic")
- `model` - Default Claude model
- `base_url` - Override API endpoint (null = use default)
- `timeout_seconds` - API request timeout
- `temperature` - Sampling temperature (0.0-2.0)
- `max_tokens` - Maximum response length

---

### Search Settings

Configure semantic search and retrieval thresholds.

```json
{
  "search": {
    "min_semantic_score": 0.70,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
  }
}
```

**Fields:**
- `min_semantic_score` - Minimum similarity score (0.0-1.0)
- `embedding_model` - HuggingFace model for embeddings

**Tuning:**
- Lower score (0.5) - More results, less precise
- Higher score (0.8) - Fewer results, more precise

**Environment:** Set `HF_HUB_OFFLINE=1` to use cached models only.

---

### SOAR Settings

Configure the SOAR (State, Operator, And Result) reasoning system.

```json
{
  "soar": {
    "default_tool": "claude",
    "default_model": "sonnet"
  }
}
```

**Fields:**
- `default_tool` - CLI tool for SOAR phases ("claude", "cursor", "opencode", etc.)
- `default_model` - Model tier ("sonnet" or "opus")

**Override:**
```bash
# Via environment
AURORA_SOAR_TOOL=opencode aur soar "query"

# Via CLI flag
aur soar "query" --tool cursor --model opus
```

---

### Memory Settings

Configure automatic code indexing behavior.

```json
{
  "memory": {
    "auto_index": true,
    "index_paths": ["."],
    "chunk_size": 1000,
    "overlap": 200
  }
}
```

**Fields:**
- `auto_index` - Automatically index files on `aur mem index`
- `index_paths` - Directories to index (relative to project root)
- `chunk_size` - Characters per chunk (affects retrieval granularity)
- `overlap` - Overlap between chunks (preserves context)

**Tuning:**
- Larger chunks (1500) - Better context, slower search
- Smaller chunks (500) - Faster search, less context
- Overlap (200) - Prevents splitting concepts

---

### Planning Settings

Configure plan storage and templates.

```json
{
  "planning": {
    "base_dir": "./.aurora/plans",
    "template_dir": null,
    "auto_increment": true,
    "archive_on_complete": false
  }
}
```

**Fields:**
- `base_dir` - Where to store plans
- `template_dir` - Custom plan templates (null = use built-in)
- `auto_increment` - Auto-generate plan IDs (0001, 0002, etc.)
- `archive_on_complete` - Move completed plans to archive/

**Structure:**
```
.aurora/plans/
├── active/
│   └── 0001-feature-name/
│       ├── plan.md
│       ├── prd.md
│       ├── tasks.md
│       └── agents.json
└── archive/
    └── 0001-feature-name/
```

---

### Agents Settings

Configure agent discovery and caching.

```json
{
  "agents": {
    "discovery_paths": [],
    "manifest_path": "./.aurora/cache/agent_manifest.json",
    "refresh_interval_days": 1,
    "fallback_mode": "llm_only"
  }
}
```

**Fields:**
- `discovery_paths` - Optional custom paths to agent directories. If empty/not specified, automatically uses all 20 tool paths from `paths.py` registry (recommended default)
- `manifest_path` - Cached agent registry location
- `refresh_interval_days` - How often to rescan agent directories
- `fallback_mode` - Behavior when no agents found ("llm_only" or other)

**Discovery:**
Aurora searches for agent `.md` files in directories for all 20 supported tools by default. Agent discovery works **without requiring tool configuration** - agents from any supported tool directory will be discovered automatically.

**Default behavior (empty discovery_paths):**
Automatically scans all 20 tool directories defined in `packages/cli/src/aurora_cli/configurators/slash/paths.py`:
- `~/.claude/agents`, `~/.cursor/agents`, `~/.cline/agents`
- `~/.windsurf/agents`, `~/.factory/droids`, `~/.codex/agents`
- `~/.config/opencode/agent`, `~/.config/gemini-cli/agents`
- And 12 more tool directories...

**Custom paths:**
```json
{
  "agents": {
    "discovery_paths": ["~/.claude/agents", "~/my-custom-agents"]
  }
}
```
When specified, **only** the custom paths are used (default tool paths are not included).

---

### Budget Settings

Configure API cost tracking and limits.

```json
{
  "budget": {
    "limit": 10.0,
    "tracker_path": "~/.aurora/budget_tracker.json"
  }
}
```

**Fields:**
- `limit` - Monthly budget in USD
- `tracker_path` - Where to store usage data (always global)

**Check usage:**
```bash
aur budget show        # View current usage
aur budget set 25.0    # Update monthly limit
```

**Budget tracker format:**
```json
{
  "2026-01": {
    "spent": 5.23,
    "limit": 10.0
  }
}
```

---

### Logging Settings

Configure log levels and file locations.

```json
{
  "logging": {
    "level": "INFO",
    "path": "./.aurora/logs/",
    "max_size_mb": 100,
    "max_files": 10
  }
}
```

**Fields:**
- `level` - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `path` - Log directory
- `max_size_mb` - Max size per log file
- `max_files` - Max number of rotated logs

**Environment:** `AURORA_LOGGING_LEVEL=DEBUG`

---

### Context Settings

Configure code analysis and hybrid retrieval.

```json
{
  "context": {
    "code": {
      "enabled": true,
      "languages": ["python"],
      "max_file_size_kb": 500,
      "cache_ttl_hours": 24,
      "hybrid_weights": {
        "activation": 0.6,
        "semantic": 0.4,
        "top_k": 100,
        "fallback_to_activation": true
      }
    }
  }
}
```

**Fields:**
- `enabled` - Enable code context extraction
- `languages` - Supported languages for parsing
- `max_file_size_kb` - Skip files larger than this
- `hybrid_weights` - ACT-R vs semantic search balance

---

### Early Detection Settings

Configure proactive error detection during execution.

```json
{
  "early_detection": {
    "enabled": true,
    "check_interval": 2.0,
    "stall_threshold": 15.0,
    "min_output_bytes": 100,
    "stderr_pattern_check": true,
    "memory_limit_mb": null
  }
}
```

**Fields:**
- `enabled` - Enable early detection
- `check_interval` - How often to check (seconds)
- `stall_threshold` - No output = stalled (seconds)
- `min_output_bytes` - Minimum output to consider progress
- `stderr_pattern_check` - Look for error patterns
- `memory_limit_mb` - Kill if exceeds (null = no limit)

---

## Environment Variables

Aurora supports environment variable overrides for common settings:

### LLM Configuration

| Variable | Config Path | Example |
|----------|-------------|---------|
| `AURORA_LLM_MODEL` | `llm.model` | `claude-3-5-sonnet-20241022` |

### SOAR Configuration

| Variable | Config Path | Example |
|----------|-------------|---------|
| `AURORA_SOAR_TOOL` | `soar.default_tool` | `cursor`, `opencode` |
| `AURORA_SOAR_MODEL` | `soar.default_model` | `sonnet`, `opus` |

### Planning Configuration

| Variable | Config Path | Example |
|----------|-------------|---------|
| `AURORA_PLANS_DIR` | `planning.base_dir` | `./my-plans` |
| `AURORA_TEMPLATE_DIR` | `planning.template_dir` | `./templates` |

### Logging Configuration

| Variable | Config Path | Example |
|----------|-------------|---------|
| `AURORA_LOGGING_LEVEL` | `logging.level` | `DEBUG`, `INFO` |

### Paths Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `AURORA_HOME` | Override global .aurora directory | `~/.aurora` |
| `HF_HUB_OFFLINE` | Use cached models only | `0` (download) |

---

## Customization Guide

### Creating Your Config File

1. **Check current config:**
   ```bash
   aur doctor  # Shows config file location
   ```

2. **Create user config:**
   ```bash
   # Global config (affects all projects)
   mkdir -p ~/.aurora
   nano ~/.aurora/config.json

   # Project config (this project only)
   aur init  # Creates .aurora/
   nano .aurora/config.json
   ```

3. **Start with minimal overrides:**
   ```json
   {
     "soar": {
       "default_tool": "cursor"
     },
     "budget": {
       "limit": 25.0
     }
   }
   ```

### Common Customizations

**Change default tool:**
```json
{
  "soar": {
    "default_tool": "opencode",
    "default_model": "opus"
  }
}
```

**Increase budget:**
```json
{
  "budget": {
    "limit": 50.0
  }
}
```

**Debug logging:**
```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

**Custom agent paths:**
```json
{
  "agents": {
    "discovery_paths": [
      "~/.claude/agents",
      "~/my-agents"
    ]
  }
}
```

### Validation

Aurora validates config on load. Invalid values will show an error:

```bash
$ aur doctor
Config error: budget.limit must be positive, got -5.0
```

**Common validation rules:**
- `budget.limit` > 0
- `logging.level` in [DEBUG, INFO, WARNING, ERROR, CRITICAL]
- `escalation.threshold` between 0.0-1.0
- `search.min_semantic_score` between 0.0-1.0

---

## Migration Notes

### From v0.6.x to v0.7.0+

**Breaking changes:**
- `database.path` → `storage.path`
- Removed `aurora_core/config/` package
- Config now returns dict instead of dataclass

**What you need to do:**

1. Update config files:
   ```json
   // Old (v0.6.x)
   {
     "database": {
       "path": "./.aurora/memory.db"
     }
   }

   // New (v0.7.0+)
   {
     "storage": {
       "path": "./.aurora/memory.db"
     }
   }
   ```

2. Code using config:
   ```python
   # Old
   from aurora_core.config import load_config
   config = load_config()  # Returns dataclass

   # New
   from aurora_cli.config import Config
   config = Config()  # Returns wrapper with same API
   ```

**Backward compatibility:**
The `Config` class wrapper maintains the same property accessors, so most code continues to work without changes.

---

## Troubleshooting

### Config Not Loading

**Symptom:** Aurora uses defaults instead of your config.

**Check:**
```bash
aur doctor  # Shows which config file is loaded
ls -la ~/.aurora/config.json
ls -la ./.aurora/config.json
```

**Common causes:**
- Config file doesn't exist
- Invalid JSON syntax
- Wrong file location (global vs project)

### Environment Variables Not Working

**Check precedence:**
```bash
# Set and test
export AURORA_SOAR_TOOL=cursor
aur soar "test query"  # Should show cursor in output

# Verify it's set
echo $AURORA_SOAR_TOOL
```

### Validation Errors

**Symptom:** Config loads but values rejected.

```bash
$ aur doctor
Config error: budget.limit must be positive, got 0.0
```

**Fix:** Check value ranges in validation rules above.

### Budget Not Tracking

**Check tracker file:**
```bash
cat ~/.aurora/budget_tracker.json
```

**Reset if corrupted:**
```bash
rm ~/.aurora/budget_tracker.json
aur budget set 10.0
```

### Tool Not Found

**Symptom:** `Tool 'cursor' not found in PATH`

**Check:**
```bash
which cursor
echo $PATH
```

**Fix:** Install the tool or use a different one.

---

## See Also

- [QUICK_START.md](../guides/QUICK_START.md) - Getting started with Aurora
- [CLI_USAGE_GUIDE.md](../guides/CLI_USAGE_GUIDE.md) - Command reference
- [SOAR.md](../guides/SOAR.md) - SOAR reasoning system
- [TOOLS_CONFIG_GUIDE.md](../guides/TOOLS_CONFIG_GUIDE.md) - Multi-tool setup
