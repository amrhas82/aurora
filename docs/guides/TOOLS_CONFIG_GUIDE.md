# Aurora Tools Configuration Guide

Complete reference for Aurora's slash command and MCP server configurator system.

**Last Updated:** 2026-01-07
**Version:** 0.5.0+

---

## Table of Contents

1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Architecture](#architecture)
4. [Supported Tools](#supported-tools)
5. [Adding a New Tool](#adding-a-new-tool)
6. [Modifying Command Templates](#modifying-command-templates)
7. [Testing Changes](#testing-changes)
8. [Release Checklist](#release-checklist)
9. [Common Patterns](#common-patterns)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Aurora's configurator system automatically generates slash commands for **20 AI coding tools** (Claude Code, Cursor, Windsurf, etc.) and maintains (dormant) MCP server configurations for 4 tools.

**Key Features:**
- Single source of truth: templates in `slash_commands.py`
- Automatic generation during `aur init`
- Managed block system with `<!-- AURORA:START/END -->` markers
- Support for both Markdown (YAML frontmatter) and TOML formats
- Update existing files without overwriting user changes outside markers

**Design Philosophy:**
- **DRY**: All tools use same template bodies from `templates/slash_commands.py`
- **Separation**: Tool-specific metadata (paths, frontmatter) vs shared logic (command bodies)
- **Managed Blocks**: User can add content outside `AURORA:START/END` markers

---

## Directory Structure

```
packages/cli/src/aurora_cli/
├── commands/
│   └── init.py                          # aur init command (calls configurators)
├── configurators/
│   ├── __init__.py
│   ├── base.py                          # (Legacy, not used)
│   ├── registry.py                      # (Legacy, not used)
│   ├── mcp/                            # MCP configurators (DORMANT)
│   │   ├── __init__.py
│   │   ├── base.py                      # MCPConfigurator base class
│   │   ├── claude.py                    # Claude Desktop MCP
│   │   ├── cline.py                     # Cline MCP
│   │   ├── continue_.py                 # Continue MCP
│   │   ├── cursor.py                    # Cursor MCP
│   │   └── registry.py                  # MCPConfigRegistry (4 tools)
│   └── slash/                          # Slash command configurators
│       ├── __init__.py
│       ├── base.py                      # SlashCommandConfigurator base class
│       ├── toml_base.py                 # TomlSlashCommandConfigurator base
│       ├── registry.py                  # SlashCommandRegistry (20 tools)
│       ├── factory.py                   # Factory pattern helper
│       ├── claude.py                    # Claude Code (.claude/commands/aur/)
│       ├── cursor.py                    # Cursor (.cursor/commands/)
│       ├── windsurf.py                  # Windsurf (.windsurf/commands/)
│       ├── cline.py                     # Cline (.cline/commands/)
│       ├── gemini.py                    # Gemini CLI (.gemini/commands/aurora/) [TOML]
│       ├── github_copilot.py            # GitHub Copilot (.github/copilot/)
│       ├── codex.py                     # Codex (.codex/commands/)
│       ├── qwen.py                      # Qwen (.qwen/commands/) [TOML]
│       ├── kilocode.py                  # KiloCode (.kilocode/commands/) [TOML]
│       ├── roocode.py                   # RooCode (.roocode/commands/) [TOML]
│       ├── qoder.py                     # Qoder (.qoder/commands/) [TOML]
│       ├── iflow.py                     # iFlow (.iflow/commands/) [TOML]
│       ├── amazon_q.py                  # Amazon Q (.amazonq/commands/)
│       ├── codebuddy.py                 # CodeBuddy (.codebuddy/commands/)
│       ├── auggie.py                    # Auggie (.auggie/commands/)
│       ├── costrict.py                  # Costrict (.costrict/commands/)
│       ├── crush.py                     # Crush (.crush/commands/)
│       ├── antigravity.py               # Antigravity (.antigravity/commands/)
│       └── opencode.py                  # OpenCode (.opencode/commands/)
└── templates/
    └── slash_commands.py                # SINGLE SOURCE OF TRUTH for command bodies

tests/
└── unit/cli/configurators/
    ├── slash/                           # Slash configurator tests
    │   ├── test_cursor.py
    │   ├── test_windsurf.py
    │   ├── test_codex.py
    │   ├── test_gemini.py
    │   └── ...
    └── mcp/                            # MCP configurator tests
        ├── test_base.py
        ├── test_claude.py
        └── test_registry.py
```

### Key Locations

| Purpose | Location | Description |
|---------|----------|-------------|
| **Command templates** | `templates/slash_commands.py` | Single source for all command bodies |
| **Slash registry** | `configurators/slash/registry.py` | Registers all 20 tools |
| **MCP registry** | `configurators/mcp/registry.py` | Registers 4 MCP tools (dormant) |
| **Base classes** | `configurators/slash/base.py`, `toml_base.py` | Abstract interfaces |
| **Tool configs** | `configurators/slash/*.py` | One file per tool |

---

## Architecture

### 1. Template System

**Single Source of Truth:** `templates/slash_commands.py`

```python
# Defines 6 Aurora commands:
ALL_COMMANDS = ["search", "get", "plan", "checkpoint", "implement", "archive"]

# Each command has a template:
COMMAND_TEMPLATES = {
    "search": SEARCH_TEMPLATE,
    "get": GET_TEMPLATE,
    "plan": PLAN_TEMPLATE,
    "checkpoint": CHECKPOINT_TEMPLATE,
    "implement": IMPLEMENT_TEMPLATE,
    "archive": ARCHIVE_TEMPLATE,
}

# Templates include:
# - BASE_GUARDRAILS (common to all)
# - Command-specific usage instructions
# - Output format rules (MANDATORY - NEVER DEVIATE)
# - Examples
```

**All 20 tools use the same template bodies via `get_command_body(command_id)`.**

### 2. Base Classes

#### SlashCommandConfigurator (Markdown format)

Located: `configurators/slash/base.py`

```python
class SlashCommandConfigurator(ABC):
    @property
    @abstractmethod
    def tool_id(self) -> str:
        """Tool identifier (e.g., "claude", "cursor")"""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether tool is detected/available"""

    @abstractmethod
    def get_relative_path(self, command_id: str) -> str:
        """File path (e.g., ".claude/commands/aur/search.md")"""

    @abstractmethod
    def get_frontmatter(self, command_id: str) -> str | None:
        """YAML frontmatter (name, description, tags)"""

    @abstractmethod
    def get_body(self, command_id: str) -> str:
        """Command body from templates"""

    # Provided methods:
    def generate_all(...) -> list[str]:
        """Generate all 6 commands for this tool"""

    def update_existing(...) -> list[str]:
        """Update existing files only"""
```

**Managed Block System:**
```markdown
---
name: Aurora: Search
---
<!-- AURORA:START -->
[Template body goes here - managed by Aurora]
<!-- AURORA:END -->

User can add custom content here (not managed)
```

#### TomlSlashCommandConfigurator (TOML format)

Located: `configurators/slash/toml_base.py`

Extends `SlashCommandConfigurator` for tools that use TOML format.

```python
class TomlSlashCommandConfigurator(SlashCommandConfigurator):
    def get_frontmatter(self, command_id: str) -> str | None:
        """Always returns None (TOML doesn't use frontmatter)"""

    @abstractmethod
    def get_description(self, command_id: str) -> str:
        """Description for TOML description field"""

    # Overrides generate_all to create TOML format:
    # description = "..."
    # prompt = """
    # <!-- AURORA:START -->
    # [body]
    # <!-- AURORA:END -->
    # """
```

**Tools using TOML:**
- Gemini CLI
- Qwen
- KiloCode
- RooCode
- Qoder
- iFlow

### 3. Registries

#### SlashCommandRegistry

Located: `configurators/slash/registry.py`

**Registers all 20 tools:**

```python
class SlashCommandRegistry:
    @classmethod
    def get_all() -> list[SlashCommandConfigurator]:
        """Get all 20 registered configurators"""

    @classmethod
    def get(tool_id: str) -> SlashCommandConfigurator | None:
        """Get specific tool configurator"""

    @classmethod
    def get_available() -> list[SlashCommandConfigurator]:
        """Get only available tools (is_available=True)"""
```

#### MCPConfigRegistry (Dormant)

Located: `configurators/mcp/registry.py`

**Registers 4 MCP-capable tools:**
- Claude Desktop
- Cursor
- Cline
- Continue

**Status:** MCP support is dormant as of v0.5.0 (see `docs/MCP_DEPRECATION.md`).

---

## Supported Tools

### Complete Tool List (20 Slash Configurators)

| # | Tool | tool_id | Directory | Format | Naming Pattern |
|---|------|---------|-----------|--------|----------------|
| 1 | Claude Code | `claude` | `.claude/commands/aur/` | Markdown | `{command}.md` |
| 2 | Cursor | `cursor` | `.cursor/commands/` | Markdown | `aurora-{command}.md` |
| 3 | Windsurf | `windsurf` | `.windsurf/commands/` | Markdown | `aurora-{command}.md` |
| 4 | Cline | `cline` | `.cline/commands/` | Markdown | `aurora-{command}.md` |
| 5 | GitHub Copilot | `github-copilot` | `.github/copilot/` | Markdown | `aurora-{command}.md` |
| 6 | Codex | `codex` | `.codex/commands/` | Markdown | `aurora-{command}.md` |
| 7 | OpenCode | `opencode` | `.opencode/commands/` | Markdown | `aurora-{command}.md` |
| 8 | Amazon Q | `amazon-q` | `.amazonq/commands/` | Markdown | `aurora-{command}.md` |
| 9 | CodeBuddy | `codebuddy` | `.codebuddy/commands/` | Markdown | `aurora-{command}.md` |
| 10 | Auggie | `auggie` | `.auggie/commands/` | Markdown | `aurora-{command}.md` |
| 11 | Costrict | `costrict` | `.costrict/commands/` | Markdown | `aurora-{command}.md` |
| 12 | Crush | `crush` | `.crush/commands/` | Markdown | `aurora-{command}.md` |
| 13 | Antigravity | `antigravity` | `.antigravity/commands/` | Markdown | `aurora-{command}.md` |
| 14 | Gemini CLI | `gemini` | `.gemini/commands/aurora/` | **TOML** | `{command}.toml` |
| 15 | Qwen | `qwen` | `.qwen/commands/` | **TOML** | `aurora-{command}.toml` |
| 16 | KiloCode | `kilocode` | `.kilocode/commands/` | **TOML** | `aurora-{command}.toml` |
| 17 | RooCode | `roocode` | `.roocode/commands/` | **TOML** | `aurora-{command}.toml` |
| 18 | Qoder | `qoder` | `.qoder/commands/` | **TOML** | `aurora-{command}.toml` |
| 19 | iFlow | `iflow` | `.iflow/commands/` | **TOML** | `aurora-{command}.toml` |
| 20 | Factory | `factory` | `.factory/commands/` | Markdown | `aurora-{command}.md` |

### MCP Configurators (4 tools - Dormant)

| Tool | tool_id | Config Location |
|------|---------|-----------------|
| Claude Desktop | `claude` | `~/Library/Application Support/Claude/` or `%APPDATA%/Claude/` |
| Cursor | `cursor` | `.cursor/mcp.json` |
| Cline | `cline` | `.cline/mcp.json` |
| Continue | `continue` | `.continue/config.json` |

---

## Adding a New Tool

### Step 1: Create Configurator Class

Choose format: **Markdown** or **TOML**

#### Option A: Markdown Format (Most tools)

Create `configurators/slash/newtool.py`:

```python
"""NewTool slash command configurator."""

from aurora_cli.configurators.slash.base import SlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

# File paths for each command
FILE_PATHS: dict[str, str] = {
    "search": ".newtool/commands/aurora-search.md",
    "get": ".newtool/commands/aurora-get.md",
    "plan": ".newtool/commands/aurora-plan.md",
    "checkpoint": ".newtool/commands/aurora-checkpoint.md",
    "implement": ".newtool/commands/aurora-implement.md",
    "archive": ".newtool/commands/aurora-archive.md",
}

# Frontmatter for each command
FRONTMATTER: dict[str, str] = {
    "search": """---
name: Aurora: Search
description: Search indexed code and documentation
category: Aurora
tags: [aurora, search, memory]
---""",
    "get": """---
name: Aurora: Get
description: Get full chunk content by index
category: Aurora
tags: [aurora, search, memory]
---""",
    # ... (repeat for all 6 commands)
}


class NewToolSlashCommandConfigurator(SlashCommandConfigurator):
    """Slash command configurator for NewTool."""

    @property
    def tool_id(self) -> str:
        return "newtool"

    @property
    def is_available(self) -> bool:
        # Always True, or add detection logic
        return True

    def get_relative_path(self, command_id: str) -> str:
        return FILE_PATHS[command_id]

    def get_frontmatter(self, command_id: str) -> str | None:
        return FRONTMATTER[command_id]

    def get_body(self, command_id: str) -> str:
        return get_command_body(command_id)  # Uses shared templates
```

#### Option B: TOML Format

Create `configurators/slash/newtool.py`:

```python
"""NewTool slash command configurator (TOML format)."""

from aurora_cli.configurators.slash.toml_base import TomlSlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body

FILE_PATHS: dict[str, str] = {
    "search": ".newtool/commands/aurora-search.toml",
    "get": ".newtool/commands/aurora-get.toml",
    # ... (6 commands)
}

DESCRIPTIONS: dict[str, str] = {
    "search": "Search indexed code and documentation",
    "get": "Get full chunk content by index",
    # ... (6 commands)
}


class NewToolSlashCommandConfigurator(TomlSlashCommandConfigurator):
    """Slash command configurator for NewTool (TOML)."""

    @property
    def tool_id(self) -> str:
        return "newtool"

    @property
    def is_available(self) -> bool:
        return True

    def get_relative_path(self, command_id: str) -> str:
        return FILE_PATHS[command_id]

    def get_description(self, command_id: str) -> str:
        return DESCRIPTIONS[command_id]

    def get_body(self, command_id: str) -> str:
        return get_command_body(command_id)
```

### Step 2: Register in Registry

Edit `configurators/slash/registry.py`:

```python
# Add import
from aurora_cli.configurators.slash.newtool import NewToolSlashCommandConfigurator

# Add to configurators list in _ensure_initialized()
configurators = [
    # ... existing tools ...
    NewToolSlashCommandConfigurator(),  # Add this line
]
```

**Update count in docstring:** Change `"""All 20 supported AI coding tools"""` to `"""All 21 supported AI coding tools"""`.

### Step 3: Create Tests

Create `tests/unit/cli/configurators/slash/test_newtool.py`:

```python
"""Unit tests for NewTool slash command configurator."""

import pytest
from pathlib import Path
from aurora_cli.configurators.slash.newtool import NewToolSlashCommandConfigurator


def test_tool_id():
    """Test tool_id property."""
    config = NewToolSlashCommandConfigurator()
    assert config.tool_id == "newtool"


def test_is_available():
    """Test is_available property."""
    config = NewToolSlashCommandConfigurator()
    assert config.is_available is True


def test_get_relative_path():
    """Test file path generation."""
    config = NewToolSlashCommandConfigurator()
    assert config.get_relative_path("search") == ".newtool/commands/aurora-search.md"
    assert config.get_relative_path("get") == ".newtool/commands/aurora-get.md"


def test_get_body_returns_template():
    """Test get_body returns template content."""
    config = NewToolSlashCommandConfigurator()
    body = config.get_body("search")
    assert "Guardrails" in body
    assert "aur mem search" in body


def test_generate_all(tmp_path):
    """Test generate_all creates all 6 command files."""
    config = NewToolSlashCommandConfigurator()
    created = config.generate_all(str(tmp_path), ".aurora")

    assert len(created) == 6
    assert Path(tmp_path / ".newtool/commands/aurora-search.md").exists()
    assert Path(tmp_path / ".newtool/commands/aurora-get.md").exists()
```

### Step 4: Update Documentation

1. **Update this guide** - Add tool to [Supported Tools](#supported-tools) table
2. **Update COMMANDS.md** - Add tool to slash command examples if relevant
3. **Update README.md** - Add to supported tools list if it's a major tool

### Step 5: Test

```bash
# Run tests
pytest tests/unit/cli/configurators/slash/test_newtool.py -v

# Test in real project
cd /tmp/test-project
aur init --tools=newtool

# Verify files created
ls .newtool/commands/
```

### Step 6: Update Tool Count

**Files to update:**
1. `configurators/slash/registry.py` - Docstring
2. `TOOLS_CONFIG_GUIDE.md` - This file (Supported Tools section)
3. `README.md` - If listing tool counts

---

## Modifying Command Templates

### Updating Default Templates

**Location:** `packages/cli/src/aurora_cli/templates/slash_commands.py`

**Impact:** All 20 tools use these templates via `get_command_body(command_id)`.

#### Example: Update `/aur:search` output format

```python
# Edit templates/slash_commands.py

SEARCH_TEMPLATE = f"""{BASE_GUARDRAILS}

**Usage**
Run `aur mem search "<query>"` to search indexed code.

**Argument Parsing**
User can provide search terms with optional flags in natural order:
- `/aur:search bm25 limit 5` → `aur mem search "bm25" --limit 5`
- `/aur:search "exact phrase" type function` → `aur mem search "exact phrase" --type function`

**Output Format (MANDATORY - NEVER DEVIATE)**

Every response MUST follow this exact structure:

1. Execute `aur mem search` with parsed args
2. Display the **FULL TABLE** - never collapse
3. Create simplified table showing ALL results
4. Add exactly 2 sentences of guidance
5. Single line: `Next: /aur:get N`

NO additional explanations or questions beyond these 2 sentences."""
```

**After editing:**
```bash
# Test locally
./install.sh

# Test in a project
cd /tmp/test-project
aur init --config --tools=claude  # Regenerate commands

# Verify changes
cat .claude/commands/aur/search.md
```

### Updating Single Tool (Override)

If you need tool-specific customization (rare), override `get_body()`:

```python
# In configurators/slash/special_tool.py

class SpecialToolSlashCommandConfigurator(SlashCommandConfigurator):
    # ... standard methods ...

    def get_body(self, command_id: str) -> str:
        """Custom body for special tool."""
        if command_id == "search":
            # Return custom search template for this tool only
            return """
**Special Tool Search**
This tool has unique search behavior...
"""
        else:
            # Use standard templates for other commands
            return get_command_body(command_id)
```

**⚠️ Warning:** Avoid tool-specific overrides. They break the "single source of truth" principle and make maintenance harder.

---

## Testing Changes

### Unit Tests

```bash
# Test all configurators
pytest tests/unit/cli/configurators/ -v

# Test specific tool
pytest tests/unit/cli/configurators/slash/test_claude.py -v

# Test templates
pytest tests/unit/cli/test_templates.py -v  # (if exists)
```

### Integration Tests

```bash
# Create test project
mkdir -p /tmp/test-aurora
cd /tmp/test-aurora
git init

# Test init
aur init --tools=claude

# Verify files created
ls -la .claude/commands/aur/

# Check content
cat .claude/commands/aur/search.md

# Test update
aur init --config --tools=claude

# Verify Aurora markers preserved
grep -A 5 "AURORA:START" .claude/commands/aur/search.md
```

### Testing Template Changes

After modifying `templates/slash_commands.py`:

```bash
# 1. Reinstall locally
./install.sh

# 2. Test in fresh project
cd /tmp/test-aurora
rm -rf .claude .cursor .windsurf  # Remove old configs

# 3. Regenerate for all tools
aur init --config --tools=all

# 4. Spot check multiple tools
cat .claude/commands/aur/search.md
cat .cursor/commands/aurora-search.md
cat .gemini/commands/aurora/search.toml

# 5. Verify consistency
# All should have same body content between markers
```

### Manual Testing Checklist

- [ ] Markdown tools generate correct frontmatter
- [ ] TOML tools generate valid TOML syntax
- [ ] Aurora markers present in all files
- [ ] All 6 commands generated (search, get, plan, checkpoint, implement, archive)
- [ ] File paths follow tool's naming convention
- [ ] Update existing files preserves user content outside markers
- [ ] Body content matches template from `slash_commands.py`

---

## Release Checklist

When releasing changes to tool configurators, follow this checklist. Cross-reference with `RELEASE.md`.

### Pre-Release

#### 1. Code Quality (from RELEASE.md § Pre-Release Checklist)

```bash
# Run full local CI
./scripts/run-local-ci.sh
```

**Must pass:**
- ✅ All tests (including configurator tests)
- ✅ No security issues (bandit)
- ✅ Code properly formatted (black, isort)
- ✅ Test coverage meets standards

#### 2. Configurator-Specific Checks

**For ALL changes:**
- [ ] Updated `templates/slash_commands.py`? Test with 3+ different tool formats (Markdown + TOML)
- [ ] Added new tool? Updated count in registry docstring
- [ ] Modified base class? Run all configurator tests
- [ ] Changed file paths? Test `aur init --tools=<tool>`

**For template changes:**
- [ ] Test search command output format with `/aur:search test limit 5`
- [ ] Test get command output format with `/aur:get 1`
- [ ] Verify "MANDATORY - NEVER DEVIATE" sections are clear
- [ ] Check all 6 commands render correctly

**For new tool additions:**
- [ ] Tool added to `configurators/slash/registry.py`
- [ ] Unit tests created in `tests/unit/cli/configurators/slash/test_<tool>.py`
- [ ] Tool listed in this guide's [Supported Tools](#supported-tools)
- [ ] README.md updated (if major tool)

#### 3. Cross-Tool Consistency

```bash
# Generate configs for multiple tools
cd /tmp/test-consistency
aur init --tools=claude,cursor,windsurf,gemini

# Verify body content is identical (ignoring format differences)
# Extract body between markers for each:
sed -n '/AURORA:START/,/AURORA:END/p' .claude/commands/aur/search.md > /tmp/claude-body
sed -n '/AURORA:START/,/AURORA:END/p' .cursor/commands/aurora-search.md > /tmp/cursor-body
sed -n '/AURORA:START/,/AURORA:END/p' .gemini/commands/aurora/search.toml > /tmp/gemini-body

# Bodies should be identical
diff /tmp/claude-body /tmp/cursor-body
diff /tmp/claude-body /tmp/gemini-body
```

### Release

Follow standard release process from `RELEASE.md`:

```bash
# After all checks pass
./scripts/release.sh <version>
```

### Post-Release

- [ ] Test install from PyPI: `pip install --upgrade aurora-actr`
- [ ] Verify `aur init` works in fresh project
- [ ] Smoke test 2-3 different tools (e.g., Claude, Cursor, Gemini)
- [ ] Check GitHub release notes mention configurator changes

### Critical Files Checklist

When making configurator changes, these files may need updates:

| File | When to Update |
|------|----------------|
| `templates/slash_commands.py` | Changing any command behavior/format |
| `configurators/slash/registry.py` | Adding/removing tools |
| `configurators/slash/base.py` | Changing base interface |
| `configurators/slash/toml_base.py` | Changing TOML format behavior |
| `TOOLS_CONFIG_GUIDE.md` | Any configurator change |
| `COMMANDS.md` | Template format changes affecting user-visible behavior |
| `README.md` | Major tool additions |
| `tests/unit/cli/configurators/slash/test_*.py` | Adding tools or changing behavior |

---

## Common Patterns

### Pattern 1: Markdown with YAML Frontmatter (14 tools)

**Example:** Claude, Cursor, Windsurf, Cline, OpenCode, etc.

**Output format:**
```markdown
---
name: Aurora: Search
description: Search indexed code and documentation
category: Aurora
tags: [aurora, search, memory]
---
<!-- AURORA:START -->
**Guardrails**
- ...

**Usage**
...
<!-- AURORA:END -->

User's custom notes here (not managed by Aurora)
```

**Configurator structure:**
```python
FILE_PATHS = {
    "search": ".tool/commands/aurora-search.md",
    # ...
}

FRONTMATTER = {
    "search": """---
name: Aurora: Search
description: ...
---""",
    # ...
}

def get_relative_path(self, command_id: str) -> str:
    return FILE_PATHS[command_id]

def get_frontmatter(self, command_id: str) -> str | None:
    return FRONTMATTER[command_id]

def get_body(self, command_id: str) -> str:
    return get_command_body(command_id)
```

### Pattern 2: TOML Format (6 tools)

**Example:** Gemini CLI, Qwen, KiloCode, RooCode, Qoder, iFlow

**Output format:**
```toml
description = "Search indexed code and documentation"

prompt = """
<!-- AURORA:START -->
**Guardrails**
- ...

**Usage**
...
<!-- AURORA:END -->
"""
```

**Configurator structure:**
```python
from aurora_cli.configurators.slash.toml_base import TomlSlashCommandConfigurator

FILE_PATHS = {
    "search": ".tool/commands/aurora-search.toml",
    # ...
}

DESCRIPTIONS = {
    "search": "Search indexed code and documentation",
    # ...
}

class ToolSlashCommandConfigurator(TomlSlashCommandConfigurator):
    def get_relative_path(self, command_id: str) -> str:
        return FILE_PATHS[command_id]

    def get_description(self, command_id: str) -> str:
        return DESCRIPTIONS[command_id]

    def get_body(self, command_id: str) -> str:
        return get_command_body(command_id)
```

### Pattern 3: Tool Detection (Optional)

Most tools return `is_available = True` (always available). For tools requiring detection:

```python
from pathlib import Path

@property
def is_available(self) -> bool:
    """Check if tool config directory exists."""
    # Check for tool-specific marker
    return (Path.home() / ".tool-config").exists()
```

### Pattern 4: Naming Conventions

**Claude pattern:** `.claude/commands/aur/{command}.md`
- No "aurora-" prefix
- Commands grouped under `aur/` subdirectory

**Most tools pattern:** `.tool/commands/aurora-{command}.md`
- "aurora-" prefix on each file
- Flat structure in commands directory

**Gemini pattern:** `.gemini/commands/aurora/{command}.toml`
- TOML extension
- Commands grouped under `aurora/` subdirectory

---

## Troubleshooting

### Issue: "Aurora markers missing" error

**Cause:** File was manually edited and markers were removed.

**Solution:**
```bash
# Delete the file and regenerate
rm .claude/commands/aur/search.md
aur init --config --tools=claude
```

### Issue: Template changes not appearing

**Cause:** Local install didn't update package.

**Solution:**
```bash
# Reinstall package
./install.sh

# Force regenerate configs
cd /tmp/test-project
rm -rf .claude
aur init --config --tools=claude
```

### Issue: Tool not registered

**Cause:** Missing from registry's `_ensure_initialized()`.

**Solution:**
```python
# In configurators/slash/registry.py
from aurora_cli.configurators.slash.newtool import NewToolSlashCommandConfigurator

configurators = [
    # ... existing ...
    NewToolSlashCommandConfigurator(),  # Add this
]
```

### Issue: TOML syntax error

**Cause:** Invalid TOML generation, likely missing triple quotes.

**Check:**
```python
# In toml_base.py _generate_toml()
prompt = """
{AURORA_MARKERS["start"]}
{body}
{AURORA_MARKERS["end"]}
"""
```

### Issue: Inconsistent bodies across tools

**Cause:** One tool has custom `get_body()` override.

**Solution:**
- Remove custom override
- Update shared template in `templates/slash_commands.py` instead
- If truly tool-specific, document why in comments

### Issue: Tests failing after template change

**Common causes:**
1. Test hardcoded to expect old format
2. Test doesn't account for flexible argument parsing
3. Aurora markers changed but test still expects old markers

**Solution:**
```python
# Update test to check for key phrases instead of exact match
assert "aur mem search" in body
assert "MANDATORY - NEVER DEVIATE" in body
# Don't check exact formatting
```

### Issue: Command not working in tool after init

**Debug steps:**
1. Check file was created: `ls .tool/commands/`
2. Check content has Aurora markers: `cat .tool/commands/aurora-search.md`
3. Check tool recognizes the file (tool-specific, consult tool docs)
4. Try regenerating: `aur init --config --tools=<tool>`

### Issue: MCP configurator errors

**Note:** MCP is dormant as of v0.5.0. See `docs/MCP_DEPRECATION.md`.

If you need to work with MCP configurators:
- They follow similar pattern to slash configurators
- Located in `configurators/mcp/`
- Only 4 tools supported
- Tests in `tests/unit/cli/configurators/mcp/`

---

## Quick Reference

### Add New Tool (Checklist)

1. ✅ Create `configurators/slash/newtool.py`
2. ✅ Choose format (SlashCommandConfigurator or TomlSlashCommandConfigurator)
3. ✅ Define FILE_PATHS (6 commands)
4. ✅ Define FRONTMATTER or DESCRIPTIONS (6 commands)
5. ✅ Implement 5 required methods (tool_id, is_available, get_relative_path, get_frontmatter/get_description, get_body)
6. ✅ Register in `configurators/slash/registry.py`
7. ✅ Create tests `tests/unit/cli/configurators/slash/test_newtool.py`
8. ✅ Run tests: `pytest tests/unit/cli/configurators/slash/test_newtool.py -v`
9. ✅ Update tool count in registry docstring
10. ✅ Update this guide (Supported Tools table)
11. ✅ Test: `aur init --tools=newtool`

### Modify Template (Checklist)

1. ✅ Edit `templates/slash_commands.py`
2. ✅ Reinstall: `./install.sh`
3. ✅ Test with 3+ tools (mix of Markdown/TOML)
4. ✅ Run tests: `pytest tests/unit/cli/configurators/ -v`
5. ✅ Update COMMANDS.md if user-visible behavior changed
6. ✅ Run pre-commit: `pre-commit run --all-files`
7. ✅ Run local CI: `./scripts/run-local-ci.sh`
8. ✅ Release: `./scripts/release.sh <version>`

### Test Configurator Changes

```bash
# Unit tests
pytest tests/unit/cli/configurators/slash/ -v

# Integration test
cd /tmp/test-config
aur init --tools=claude,cursor,gemini
cat .claude/commands/aur/search.md
cat .cursor/commands/aurora-search.md
cat .gemini/commands/aurora/search.toml

# Verify consistency
# All bodies between AURORA:START/END should match
```

---

## See Also

- **RELEASE.md** - Release workflow and PyPI deployment
- **COMMANDS.md** - User-facing command documentation
- **docs/MCP_DEPRECATION.md** - MCP feature deprecation notes
- **README.md** - Project overview and installation
- **tests/unit/cli/configurators/** - Configurator test examples

---

**Maintained by:** Aurora Core Team
**Questions?** Open an issue at https://github.com/your-repo/aurora/issues
