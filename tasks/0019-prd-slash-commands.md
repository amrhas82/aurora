# PRD-0019: Full OpenSpec Tool Configurator Port for Aurora CLI

## 1. Introduction/Overview

This PRD expands the scope of the slash command system to port the **complete OpenSpec tool configurator framework** to Aurora CLI. OpenSpec supports **20 AI coding tools** with native slash command integration, and Aurora CLI should provide the same multi-tool experience.

**Current State**:
- OpenSpec TypeScript has 20 tool configurators at `/openspec-source/src/core/configurators/slash/`
- Aurora has partial Python ports at `/openspec-source/aurora/configurators/slash/`:
  - `base.py` (ported)
  - `registry.py` (ported)
  - `claude.py` (ported)
  - `opencode.py` (ported)
- 16 configurators remain to be ported

**Problem Statement**: When users run `openspec init`, they see a comprehensive tool selection menu with all 20 supported AI tools. Aurora's `aur init` currently only supports Claude Code, missing the multi-tool experience that makes OpenSpec valuable.

**High-Level Goal**: Port the complete OpenSpec slash command configurator system so that `aur init` presents the same tool selection experience as `openspec init`, supporting all 20 AI coding tools.

---

## 2. Goals

- **G1**: Port all 20 AI tool configurators from OpenSpec TypeScript to Aurora Python
- **G2**: Implement tool selection UI in `aur init` matching OpenSpec's checkbox-based wizard
- **G3**: Create slash commands during Step 1 of `aur init` for all selected tools
- **G4**: Achieve >90% test coverage for all configurator code (TDD approach)
- **G5**: Support both markdown and TOML slash command formats
- **G6**: Handle tool-specific paths (per-project vs global directories)
- **G7**: Maintain idempotent behavior (safe to re-run without losing custom content)

---

## 3. Supported AI Tools (20 Total)

The following tools must be supported, matching OpenSpec's `AI_TOOLS` configuration:

| # | Tool Name | Tool ID | Config Path Pattern | Format |
|---|-----------|---------|---------------------|--------|
| 1 | Amazon Q Developer | `amazon-q` | `.amazonq/prompts/` | Markdown |
| 2 | Antigravity | `antigravity` | `.antigravity/commands/` | Markdown |
| 3 | Auggie (Augment CLI) | `auggie` | `.augment/prompts/` | Markdown |
| 4 | Claude Code | `claude` | `.claude/commands/aur/` | Markdown (YAML frontmatter) |
| 5 | Cline | `cline` | `.clinerules/workflows/` | Markdown |
| 6 | Codex | `codex` | `~/.codex/prompts/` (global) | Markdown |
| 7 | CodeBuddy Code (CLI) | `codebuddy` | `.codebuddy/prompts/` | Markdown |
| 8 | CoStrict | `costrict` | `.costrict/prompts/` | Markdown |
| 9 | Crush | `crush` | `.crush/prompts/` | Markdown |
| 10 | Cursor | `cursor` | `.cursor/commands/` | Markdown (YAML frontmatter) |
| 11 | Factory Droid | `factory` | `.factory/commands/` | Markdown |
| 12 | Gemini CLI | `gemini` | `.gemini/commands/aurora/` | TOML |
| 13 | GitHub Copilot | `github-copilot` | `.github/copilot-instructions/` | Markdown |
| 14 | iFlow | `iflow` | `.iflow/prompts/` | Markdown |
| 15 | Kilo Code | `kilocode` | `.kilocode/commands/` | Markdown |
| 16 | OpenCode | `opencode` | `.opencode/prompts/` | Markdown |
| 17 | Qoder (CLI) | `qoder` | `.qoder/prompts/` | Markdown |
| 18 | Qwen Code | `qwen` | `.qwen/prompts/` | Markdown |
| 19 | RooCode | `roocode` | `.roo/commands/` | Markdown |
| 20 | Windsurf | `windsurf` | `.windsurf/workflows/` | Markdown (auto_execution_mode) |

---

## 4. User Stories

### US-1: Developer selects AI tools during init
**As a** developer,
**I want** to see a checkbox menu of all supported AI tools when running `aur init`,
**So that** I can configure Aurora for the specific tools I use.

**Acceptance Criteria**:
- `aur init` displays a tool selection wizard with all 20 tools
- Tools are grouped into "Natively supported" and "Universal AGENTS.md"
- Previously configured tools are pre-selected (in extend mode)
- User can toggle tools with Space, confirm with Enter

### US-2: Developer uses Claude Code with Aurora
**As a** Claude Code user,
**I want** `/aur:plan`, `/aur:query`, etc. to appear in my command palette,
**So that** I can use Aurora's planning features directly from Claude.

**Acceptance Criteria**:
- Slash commands created at `.claude/commands/aur/*.md`
- Commands have YAML frontmatter for Claude discovery
- 7 commands: plan, query, index, search, init, doctor, agents

### US-3: Developer uses Cursor with Aurora
**As a** Cursor user,
**I want** Aurora slash commands to work in Cursor's command system,
**So that** I can use Aurora regardless of which IDE I prefer.

**Acceptance Criteria**:
- Slash commands created at `.cursor/commands/aurora-*.md`
- Commands use Cursor's frontmatter format

### US-4: Developer uses Gemini CLI with Aurora
**As a** Gemini CLI user,
**I want** Aurora prompts in TOML format,
**So that** Gemini can discover and execute them.

**Acceptance Criteria**:
- Commands created at `.gemini/commands/aurora/*.toml`
- TOML format with `description` and `prompt` fields
- Aurora markers inside the prompt value

### US-5: Developer uses Codex with Aurora (global prompts)
**As a** Codex user,
**I want** Aurora prompts installed to my global `~/.codex/prompts/` directory,
**So that** they're available across all my projects.

**Acceptance Criteria**:
- Commands created at `~/.codex/prompts/` (or `$CODEX_HOME/prompts`)
- Respects CODEX_HOME environment variable
- Works independently of project directory

### US-6: Developer re-runs init to add tools
**As a** developer who initially selected only Claude,
**I want** to re-run `aur init` and add Cursor support,
**So that** I can expand my tool coverage without losing existing config.

**Acceptance Criteria**:
- `aur init` detects existing Aurora markers in tool files
- Pre-selects previously configured tools
- Creates new tool configs while preserving existing ones

### US-7: Developer uses CLI non-interactively
**As a** CI/CD pipeline author,
**I want** to specify tools via `--tools` flag,
**So that** I can automate Aurora setup.

**Acceptance Criteria**:
- `aur init --tools=claude,cursor` works without prompts
- `aur init --tools=all` configures all 20 tools
- `aur init --tools=none` skips tool configuration

---

## 5. Functional Requirements

### 5.1 Tool Configurator Architecture

**FR-1**: The system must implement a `SlashCommandConfigurator` base class at `aurora_cli/configurators/slash/base.py` with:
- Abstract `tool_id` property
- Abstract `is_available` property
- Abstract `get_relative_path(command_id)` method
- Abstract `get_frontmatter(command_id)` method
- Abstract `get_body(command_id)` method
- Concrete `generate_all(project_path, aurora_dir)` method
- Concrete `update_existing(project_path, aurora_dir)` method
- Concrete `_update_body(file_path, body)` method with marker handling

**FR-2**: The system must implement a `TomlSlashCommandConfigurator` base class for TOML-format tools (Gemini):
- Overrides `generate_all` to produce TOML format
- Wraps markers inside the `prompt` field
- Uses `description = "..."` and `prompt = """..."""` format

**FR-3**: The system must implement 20 tool-specific configurators:
- Each configurator extends `SlashCommandConfigurator` or `TomlSlashCommandConfigurator`
- Each defines tool-specific paths and frontmatter formats
- Codex configurator overrides to use global `~/.codex/prompts/`

**FR-4**: The system must implement a `SlashCommandRegistry` class with:
- `register(configurator)` method
- `get(tool_id)` method returning configurator or None
- `get_all()` returning list of all configurators
- `get_available()` returning only available configurators
- Auto-registration of all 20 configurators on module import

### 5.2 Init Flow Integration

**FR-5**: The `aur init` command must present a 3-step wizard:
- Step 1: Configure directories + select tools (checkbox UI)
- Step 2: Memory indexing
- Step 3: Completion summary

**FR-6**: The tool selection UI must match OpenSpec's design:
- Heading: "Natively supported providers (checkmark OpenSpec custom slash commands available)"
- List of 20 tools with toggle indicators
- Heading: "Other tools (use Universal AGENTS.md for Amp, VS Code, ...)"
- Universal AGENTS.md option (always available)

**FR-7**: The system must support `--tools` flag for non-interactive mode:
- `--tools=all` selects all 20 tools
- `--tools=none` skips tool selection
- `--tools=claude,cursor,gemini` selects specific tools
- Validation for invalid tool IDs

**FR-8**: The system must detect previously configured tools by checking for Aurora markers in expected file locations.

### 5.3 Slash Command Files

**FR-9**: Each slash command file must contain Aurora markers:
- Start: `<!-- AURORA:START -->`
- End: `<!-- AURORA:END -->`
- Content between markers is managed by Aurora

**FR-10**: Content outside markers must be preserved during updates:
- Frontmatter (YAML, markdown headings)
- Custom user notes
- Tool-specific metadata

**FR-11**: Aurora slash commands must include these 7 commands:
| Command | Description |
|---------|-------------|
| plan | Create and manage planning workflows |
| query | Query codebase with AI assistance |
| index | Index code for semantic search |
| search | Search indexed code |
| init | Initialize Aurora in project |
| doctor | Run health diagnostics |
| agents | Discover available agents |

### 5.4 Format-Specific Requirements

**FR-12**: Markdown-format configurators must:
- Support YAML frontmatter (Claude, Cursor) or markdown headings (Cline, RooCode)
- Include tool-specific fields (e.g., Windsurf's `auto_execution_mode: 3`)
- Use `.md` extension

**FR-13**: TOML-format configurators must:
- Generate valid TOML syntax
- Use triple-quoted strings for multi-line prompts
- Include markers inside the `prompt` value
- Use `.toml` extension

**FR-14**: Global-path configurators (Codex) must:
- Respect environment variables (`$CODEX_HOME`)
- Default to `~/.codex/prompts/` if not set
- Create global directory if needed
- Report global paths in output

### 5.5 Error Handling

**FR-15**: The system must handle missing markers gracefully:
- Skip update if markers not found
- Log warning with file path
- Continue with other files

**FR-16**: The system must handle permission errors:
- Check write permissions before attempting writes
- Display actionable error messages
- Suggest fixes (e.g., "Run with sudo" or "Check directory permissions")

**FR-17**: The system must handle invalid tool IDs in `--tools` flag:
- List invalid IDs in error message
- Show available tool IDs
- Exit with non-zero status

---

## 6. Non-Goals (Out of Scope)

- **NG-1**: Custom slash command builder UI - Users can manually create commands
- **NG-2**: Slash command versioning/migration - All commands are idempotent
- **NG-3**: Global slash commands for all tools - Only Codex uses global paths
- **NG-4**: Tool availability detection - All 20 tools always shown as options
- **NG-5**: Automatic IDE restart - User responsibility after config changes
- **NG-6**: Tool-specific configuration files (beyond slash commands) - Focus on slash commands only

---

## 7. Design Considerations

### 7.1 Directory Structure (Target)

```
aurora_cli/
├── configurators/
│   └── slash/
│       ├── __init__.py           # Public API, auto-registration
│       ├── base.py               # SlashCommandConfigurator ABC
│       ├── toml_base.py          # TomlSlashCommandConfigurator
│       ├── registry.py           # SlashCommandRegistry
│       ├── amazon_q.py           # Amazon Q Developer
│       ├── antigravity.py        # Antigravity
│       ├── auggie.py             # Auggie (Augment CLI)
│       ├── claude.py             # Claude Code
│       ├── cline.py              # Cline
│       ├── codex.py              # Codex (global paths)
│       ├── codebuddy.py          # CodeBuddy Code
│       ├── costrict.py           # CoStrict
│       ├── crush.py              # Crush
│       ├── cursor.py             # Cursor
│       ├── factory.py            # Factory Droid
│       ├── gemini.py             # Gemini CLI (TOML)
│       ├── github_copilot.py     # GitHub Copilot
│       ├── iflow.py              # iFlow
│       ├── kilocode.py           # Kilo Code
│       ├── opencode.py           # OpenCode
│       ├── qoder.py              # Qoder (CLI)
│       ├── qwen.py               # Qwen Code
│       ├── roocode.py            # RooCode
│       └── windsurf.py           # Windsurf
└── templates/
    └── slash_commands.py         # Shared template content
```

### 7.2 Component Interaction

```
aur init
    │
    ├─> renderBanner()
    │       Display AURORA ASCII art
    │
    ├─> validate()
    │       Check write permissions, detect extend mode
    │
    ├─> Step 1: Tool Selection Wizard
    │       │
    │       ├─> getExistingToolStates()
    │       │       Check markers in all 20 tool paths
    │       │
    │       ├─> toolSelectionWizard()
    │       │       Display checkbox UI (or parse --tools flag)
    │       │
    │       └─> create_directory_structure()
    │               Creates .aurora/plans/, logs/, cache/
    │
    ├─> Step 2: Configure AI Tools
    │       │
    │       ├─> For each selected tool:
    │       │       SlashCommandRegistry.get(tool_id)
    │       │       configurator.generate_all()
    │       │
    │       └─> configureRootAgentsStub()
    │               Create/update AGENTS.md
    │
    ├─> Step 3: Memory Indexing (optional)
    │       │
    │       └─> run_memory_indexing()
    │
    └─> displaySuccessMessage()
            Show created/refreshed/skipped tools
```

---

## 8. Technical Considerations

### 8.1 Dependencies

- No new external dependencies required
- Uses `pathlib`, `os`, `typing` from standard library
- May use `rich` for checkbox UI (already a dependency)

### 8.2 TypeScript to Python Port Guide

| TypeScript Pattern | Python Equivalent |
|-------------------|-------------------|
| `readonly toolId = 'claude'` | `@property def tool_id(self) -> str: return 'claude'` |
| `async generateAll()` | `def generate_all()` (sync is fine for file I/O) |
| `Record<SlashCommandId, string>` | `dict[str, str]` |
| `path.join()` | `Path() / "..."` or `str(Path(...))` |
| `os.homedir()` | `Path.home()` |
| `process.env.CODEX_HOME` | `os.environ.get('CODEX_HOME')` |

### 8.3 Files to Create

| File | Purpose | Priority |
|------|---------|----------|
| `configurators/slash/toml_base.py` | TOML format base class | High |
| `configurators/slash/amazon_q.py` | Amazon Q Developer | Medium |
| `configurators/slash/antigravity.py` | Antigravity | Medium |
| `configurators/slash/auggie.py` | Auggie | Medium |
| `configurators/slash/cline.py` | Cline | Medium |
| `configurators/slash/codex.py` | Codex (global paths) | High |
| `configurators/slash/codebuddy.py` | CodeBuddy | Medium |
| `configurators/slash/costrict.py` | CoStrict | Medium |
| `configurators/slash/crush.py` | Crush | Medium |
| `configurators/slash/cursor.py` | Cursor | High |
| `configurators/slash/factory.py` | Factory Droid | Medium |
| `configurators/slash/gemini.py` | Gemini CLI (TOML) | High |
| `configurators/slash/github_copilot.py` | GitHub Copilot | Medium |
| `configurators/slash/iflow.py` | iFlow | Medium |
| `configurators/slash/kilocode.py` | Kilo Code | Medium |
| `configurators/slash/qoder.py` | Qoder | Medium |
| `configurators/slash/qwen.py` | Qwen Code | Medium |
| `configurators/slash/roocode.py` | RooCode | Medium |
| `configurators/slash/windsurf.py` | Windsurf | Medium |
| `tests/unit/cli/configurators/` | Unit tests per configurator | High |

### 8.4 Files to Modify

| File | Changes |
|------|---------|
| `aurora_cli/commands/init.py` | Add tool selection wizard |
| `aurora_cli/commands/init_helpers.py` | Add `prompt_for_ai_tools()`, `configure_ai_tools()` |
| `aurora_cli/configurators/slash/__init__.py` | Export all configurators, auto-register |
| `aurora_cli/config.py` | Add `AI_TOOLS` list matching OpenSpec |

### 8.5 Suggested Implementation Approach (TDD)

**Phase A: Foundation (Week 1)**
1. Write tests for `TomlSlashCommandConfigurator`
2. Implement `toml_base.py`
3. Write tests for tool selection wizard
4. Implement wizard in `init.py`

**Phase B: High-Priority Tools (Week 1-2)**
5. Port `cursor.py` (popular IDE)
6. Port `codex.py` (global paths are tricky)
7. Port `gemini.py` (TOML format)
8. Port `windsurf.py` (special frontmatter)

**Phase C: Remaining Tools (Week 2-3)**
9. Port remaining 12 markdown-based configurators
10. Update `__init__.py` with auto-registration
11. Add `AI_TOOLS` to config

**Phase D: Integration (Week 3)**
12. Integrate wizard into `aur init`
13. Add `--tools` flag support
14. Integration tests for full flow

**Phase E: Polish (Week 3-4)**
15. Add extend mode detection
16. Improve error messages
17. Documentation updates

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Tool Configurators | 20 ported | Count Python files in `slash/` |
| Test Coverage | >90% for slash package | `pytest --cov` |
| Tool Selection UI | Matches OpenSpec | Visual comparison |
| Init Time | <2s for tool config | Benchmark |
| Idempotency | Re-run creates no duplicates | Manual test |
| Non-interactive Mode | `--tools` flag works | CI test |

---

## 10. Testing Requirements

### 10.1 Unit Tests (per configurator)

```python
# tests/unit/cli/configurators/slash/test_cursor.py
class TestCursorSlashCommandConfigurator:
    def test_tool_id_is_cursor(self): ...
    def test_is_available_returns_true(self): ...
    def test_get_relative_path_returns_cursor_path(self): ...
    def test_get_frontmatter_includes_yaml(self): ...
    def test_generate_all_creates_files(self, tmp_path): ...
    def test_update_existing_preserves_custom_content(self, tmp_path): ...

# tests/unit/cli/configurators/slash/test_gemini.py
class TestGeminiSlashCommandConfigurator:
    def test_generates_toml_format(self, tmp_path): ...
    def test_toml_has_description_field(self): ...
    def test_markers_inside_prompt_value(self): ...

# tests/unit/cli/configurators/slash/test_codex.py
class TestCodexSlashCommandConfigurator:
    def test_uses_global_directory(self): ...
    def test_respects_codex_home_env(self, monkeypatch): ...
    def test_resolves_absolute_path_globally(self): ...
```

### 10.2 Integration Tests

```python
# tests/integration/cli/test_init_tool_selection.py
class TestToolSelectionIntegration:
    def test_init_creates_slash_commands_for_selected_tools(self): ...
    def test_init_with_tools_flag_all(self): ...
    def test_init_with_tools_flag_specific(self): ...
    def test_init_extend_mode_detects_existing(self): ...
    def test_reinit_preserves_user_customizations(self): ...
```

### 10.3 Shell Commands for Verification

```bash
# Run all configurator tests
pytest tests/unit/cli/configurators/slash/ -v

# Run with coverage
pytest tests/unit/cli/configurators/slash/ --cov=aurora_cli.configurators.slash --cov-report=term-missing

# Test specific tool
pytest tests/unit/cli/configurators/slash/test_cursor.py -v

# Integration tests
pytest tests/integration/cli/test_init_tool_selection.py -v

# Manual verification
rm -rf /tmp/test-tools && mkdir /tmp/test-tools && cd /tmp/test-tools && git init
aur init --tools=claude,cursor,gemini
ls -la .claude/commands/aur/
ls -la .cursor/commands/
ls -la .gemini/commands/aurora/

# Test all tools
aur init --tools=all
find . -name "*.md" -o -name "*.toml" | head -50
```

---

## 11. Open Questions

1. **Q1**: Should we add tool availability detection (e.g., check if Cursor is installed)?
   - **Recommendation**: No, show all tools. Users know what they have installed.

2. **Q2**: Should Codex prompts also be created per-project (in addition to global)?
   - **Recommendation**: No, match OpenSpec behavior (global only).

3. **Q3**: Should we support `aur tools add cursor` as a separate command?
   - **Recommendation**: Out of scope. Users can re-run `aur init`.

4. **Q4**: What if a tool changes its slash command format in the future?
   - **Recommendation**: Track tool versions in markers, handle migration in future PRD.

5. **Q5**: Should we validate that tool config directories exist before creating?
   - **Decision**: Create directories if needed (mkdir -p equivalent).

---

## Appendix A: OpenSpec TypeScript Reference

Source files at `/home/hamr/PycharmProjects/aurora/openspec-source/src/core/configurators/slash/`:

- `base.ts` - Abstract SlashCommandConfigurator
- `toml-base.ts` - TOML format base class
- `registry.ts` - SlashCommandRegistry with all 20 tools
- Tool-specific files: `amazon-q.ts`, `antigravity.ts`, `auggie.ts`, `claude.ts`, `cline.ts`, `codex.ts`, `codebuddy.ts`, `costrict.ts`, `crush.ts`, `cursor.ts`, `factory.ts`, `gemini.ts`, `github-copilot.ts`, `iflow.ts`, `kilocode.ts`, `opencode.ts`, `qoder.ts`, `qwen.ts`, `roocode.ts`, `windsurf.ts`

## Appendix B: Existing Python Ports

Already ported at `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/configurators/slash/`:

- `base.py` - SlashCommandConfigurator ABC
- `registry.py` - SlashCommandRegistry
- `claude.py` - Claude Code configurator
- `opencode.py` - OpenCode configurator

## Appendix C: AI_TOOLS Configuration

```python
# aurora_cli/config.py
AI_TOOLS = [
    {"name": "Amazon Q Developer", "value": "amazon-q", "available": True},
    {"name": "Antigravity", "value": "antigravity", "available": True},
    {"name": "Auggie (Augment CLI)", "value": "auggie", "available": True},
    {"name": "Claude Code", "value": "claude", "available": True},
    {"name": "Cline", "value": "cline", "available": True},
    {"name": "Codex", "value": "codex", "available": True},
    {"name": "CodeBuddy Code (CLI)", "value": "codebuddy", "available": True},
    {"name": "CoStrict", "value": "costrict", "available": True},
    {"name": "Crush", "value": "crush", "available": True},
    {"name": "Cursor", "value": "cursor", "available": True},
    {"name": "Factory Droid", "value": "factory", "available": True},
    {"name": "Gemini CLI", "value": "gemini", "available": True},
    {"name": "GitHub Copilot", "value": "github-copilot", "available": True},
    {"name": "iFlow", "value": "iflow", "available": True},
    {"name": "Kilo Code", "value": "kilocode", "available": True},
    {"name": "OpenCode", "value": "opencode", "available": True},
    {"name": "Qoder (CLI)", "value": "qoder", "available": True},
    {"name": "Qwen Code", "value": "qwen", "available": True},
    {"name": "RooCode", "value": "roocode", "available": True},
    {"name": "Windsurf", "value": "windsurf", "available": True},
]
```
