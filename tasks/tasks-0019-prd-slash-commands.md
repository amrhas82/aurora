# Tasks: PRD-0019 Full OpenSpec Tool Configurator Port

**PRD**: `/home/hamr/PycharmProjects/aurora/tasks/0019-prd-slash-commands.md`
**Generated**: 2026-01-03
**Status**: Phase 2 - Detailed Sub-Tasks Complete

---

## Relevant Files

### Source Files (TypeScript - Reference)
- `/home/hamr/PycharmProjects/aurora/openspec-source/src/core/configurators/slash/base.ts` - Original base class
- `/home/hamr/PycharmProjects/aurora/openspec-source/src/core/configurators/slash/toml-base.ts` - TOML format base class
- `/home/hamr/PycharmProjects/aurora/openspec-source/src/core/configurators/slash/registry.ts` - Registry with all 20 tools
- `/home/hamr/PycharmProjects/aurora/openspec-source/src/core/configurators/slash/cursor.ts` - Cursor reference
- `/home/hamr/PycharmProjects/aurora/openspec-source/src/core/configurators/slash/codex.ts` - Codex (global paths) reference
- `/home/hamr/PycharmProjects/aurora/openspec-source/src/core/configurators/slash/gemini.ts` - Gemini TOML reference
- `/home/hamr/PycharmProjects/aurora/openspec-source/src/core/configurators/slash/windsurf.ts` - Windsurf reference
- `/home/hamr/PycharmProjects/aurora/openspec-source/src/core/configurators/slash/amazon-q.ts` - Amazon Q reference
- `/home/hamr/PycharmProjects/aurora/openspec-source/src/core/configurators/slash/cline.ts` - Cline reference
- `/home/hamr/PycharmProjects/aurora/openspec-source/src/core/configurators/slash/roocode.ts` - RooCode reference

### Existing Python Ports (Reference)
- `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/configurators/slash/base.py` - Partial port of base class
- `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/configurators/slash/registry.py` - Partial port of registry
- `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/configurators/slash/claude.py` - Claude configurator reference
- `/home/hamr/PycharmProjects/aurora/openspec-source/aurora/configurators/slash/opencode.py` - OpenCode configurator reference

### Target Files (To Create/Modify)

#### Base Classes and Infrastructure
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/base.py` - Existing base class (may need updates)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/toml_base.py` - NEW: TOML format base class
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/registry.py` - Existing, needs 20-tool registration
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/__init__.py` - Export all configurators

#### High-Priority Tool Configurators (Task 2.0) - COMPLETED
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/claude.py` - CREATED: Claude Code configurator with YAML frontmatter
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/cursor.py` - CREATED: Cursor configurator with /aurora-{cmd} naming
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/codex.py` - CREATED: Codex configurator with global ~/.codex/prompts/ paths
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/gemini.py` - CREATED: Gemini CLI configurator with TOML format
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/windsurf.py` - CREATED: Windsurf configurator with auto_execution_mode: 3

#### Test Files (Task 2.0) - COMPLETED
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_claude.py` - CREATED: 41 tests for Claude configurator
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_cursor.py` - CREATED: 35 tests for Cursor configurator
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_codex.py` - CREATED: 30 tests for Codex configurator (global paths)
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_gemini.py` - CREATED: 30 tests for Gemini TOML configurator
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_windsurf.py` - CREATED: 30 tests for Windsurf configurator

#### Remaining Tool Configurators (Task 3.0) - COMPLETED
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/amazon_q.py` - CREATED: Amazon Q Developer with $ARGUMENTS and <UserRequest>
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/antigravity.py` - CREATED: Antigravity with simple description frontmatter
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/auggie.py` - CREATED: Auggie with description + argument-hint
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/cline.py` - CREATED: Cline with markdown heading frontmatter
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/codebuddy.py` - CREATED: CodeBuddy with name + category + tags
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/costrict.py` - CREATED: CoStrict with description + argument-hint
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/crush.py` - CREATED: Crush with name + category + tags
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/factory.py` - CREATED: Factory Droid with $ARGUMENTS in body
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/github_copilot.py` - CREATED: GitHub Copilot with .prompt.md extension
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/iflow.py` - CREATED: iFlow with name + id + category
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/kilocode.py` - CREATED: Kilo Code (no frontmatter)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/opencode.py` - CREATED: OpenCode with $ARGUMENTS and <UserRequest>
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/qoder.py` - CREATED: Qoder with name + category + tags
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/qwen.py` - CREATED: Qwen Code with TOML format
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/roocode.py` - CREATED: RooCode with markdown heading frontmatter

#### Test Files (Task 3.0) - COMPLETED
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_markdown_tools.py` - UPDATED: 203 tests for all 15 markdown tools

#### Init Command Files (Task 5.0) - COMPLETED
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init.py` - MODIFIED: Added --tools flag, parse_tools_flag(), validate_tool_ids(), get_all_tool_ids()
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init_helpers.py` - MODIFIED: Updated prompt_tool_selection() to use SlashCommandRegistry, added configure_slash_commands()
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/configurators/slash/base.py` - MODIFIED: Added name property to SlashCommandConfigurator base class

#### Test Files (Task 5.0) - COMPLETED
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_init_tools_flag.py` - 27 tests for --tools flag parsing and validation
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_init_helpers.py` - 14 tests for tool selection wizard and configure_slash_commands()

#### Config Files (Task 6.0) - COMPLETED
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/config.py` - MODIFIED: Added AI_TOOLS constant with all 20 AI coding tools
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init_helpers.py` - MODIFIED: Added detect_configured_slash_tools() for extend mode detection

#### Test Files (Task 6.0) - COMPLETED
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_config.py` - 11 tests for AI_TOOLS constant (TestAIToolsConstant)
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_init_helpers.py` - UPDATED: Added 11 tests for detect_configured_slash_tools() (TestDetectConfiguredSlashTools)

### Test Files (To Create)
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/__init__.py` - Test package init
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/__init__.py` - Test subpackage init
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_base.py` - Base class tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_toml_base.py` - TOML base tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_registry.py` - Registry tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_claude.py` - Claude tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_cursor.py` - Cursor tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_gemini.py` - Gemini TOML tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_codex.py` - Codex global path tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_windsurf.py` - Windsurf tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/test_markdown_tools.py` - Bulk markdown tool tests
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_init_tools_flag.py` - --tools flag unit tests
- `/home/hamr/PycharmProjects/aurora/tests/integration/cli/test_init_tool_selection.py` - Tool selection integration tests

### Notes

- **Testing Framework**: pytest with pytest-asyncio, use `tmp_path` fixture for file operations
- **TDD Approach**: Write failing tests first, then implement to make tests pass
- **Rebranding**: Change all `OPENSPEC` markers to `AURORA`, `openspec` to `aurora` in paths/names
- **Marker Format**: `<!-- AURORA:START -->` and `<!-- AURORA:END -->`
- **TOML Marker Format**: Markers inside the `prompt = """..."""` field
- **Existing Patterns**: Follow patterns in `/home/hamr/PycharmProjects/aurora/tests/unit/cli/test_configurators.py`
- **Verification**: Run `pytest tests/unit/cli/configurators/slash/ -v` after each task
- **Coverage Target**: >90% for all slash package code
- **7 Commands**: plan, query, index, search, init, doctor, agents
- **Global Paths**: Codex uses `~/.codex/prompts/` or `$CODEX_HOME/prompts/`
- **Special Frontmatter**: Windsurf has `auto_execution_mode: 3`, Amazon Q has `$ARGUMENTS`

---

## Tasks

- [x] 1.0 Implement TomlSlashCommandConfigurator base class for TOML-format tools
  - [x] 1.1 Create test directory structure for slash configurator tests
    - Create `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/__init__.py`
    - Create `/home/hamr/PycharmProjects/aurora/tests/unit/cli/configurators/slash/__init__.py`
    - **Verify**: `python -c "import tests.unit.cli.configurators.slash; print('OK')"`
  - [x] 1.2 Write failing tests for TomlSlashCommandConfigurator in `test_toml_base.py`
    - Test `get_frontmatter()` returns None (TOML has no separate frontmatter)
    - Test abstract `get_description(command_id)` method is required
    - Test `generate_all()` creates `.toml` files with TOML syntax
    - Test TOML output has `description = "..."` field
    - Test TOML output has `prompt = """..."""` with markers inside
    - Test `_update_body()` correctly replaces content between markers in TOML
    - **Verify (expect failures)**: `pytest tests/unit/cli/configurators/slash/test_toml_base.py -v`
  - [x] 1.3 Implement TomlSlashCommandConfigurator in `toml_base.py`
    - Import `SlashCommandConfigurator` from `base.py`
    - Import `AURORA_MARKERS` from `base.py`
    - Override `get_frontmatter()` to return None
    - Add abstract `get_description(command_id: str) -> str` method
    - Override `generate_all()` to produce TOML format with markers inside prompt
    - Implement `_generate_toml(command_id, body)` private method
    - Override `_update_body()` for TOML marker handling
    - **Verify (tests pass)**: `pytest tests/unit/cli/configurators/slash/test_toml_base.py -v`
  - [x] 1.4 Update slash package exports in `__init__.py`
    - Add import for `TomlSlashCommandConfigurator`
    - Add to `__all__` list
    - **Verify**: `python -c "from aurora_cli.configurators.slash import TomlSlashCommandConfigurator; print('OK')"`
  - [x] 1.5 Run type checking and linting
    - **Verify**: `cd /home/hamr/PycharmProjects/aurora && make type-check`

- [x] 2.0 Port high-priority tool configurators (Claude, Cursor, Codex, Gemini, Windsurf)
  - [x] 2.1 Write failing tests for ClaudeSlashCommandConfigurator in `test_claude.py`
    - Test `tool_id` property returns "claude"
    - Test `is_available` property returns True
    - Test `get_relative_path("plan")` returns `.claude/commands/aur/plan.md`
    - Test `get_frontmatter("plan")` returns YAML with name, description, category, tags
    - Test `get_body("plan")` returns content from `slash_commands.py` templates
    - Test `generate_all()` creates 7 command files in `.claude/commands/aur/`
    - Test `update_existing()` preserves custom content outside markers
    - **Verify (expect failures)**: `pytest tests/unit/cli/configurators/slash/test_claude.py -v`
  - [x] 2.2 Implement ClaudeSlashCommandConfigurator in `claude.py`
    - Define `FILE_PATHS` dict: `{"plan": ".claude/commands/aur/plan.md", ...}` for all 7 commands
    - Define `FRONTMATTER` dict with YAML for each command (name, description, category, tags)
    - Import `get_command_body` from `aurora_cli.templates.slash_commands`
    - Implement all abstract methods
    - **Verify (tests pass)**: `pytest tests/unit/cli/configurators/slash/test_claude.py -v`
  - [x] 2.3 Write failing tests for CursorSlashCommandConfigurator in `test_cursor.py`
    - Test `tool_id` property returns "cursor"
    - Test `get_relative_path("plan")` returns `.cursor/commands/aurora-plan.md`
    - Test `get_frontmatter()` returns YAML with name, id, category, description
    - Test frontmatter includes `/aurora-{command}` naming pattern
    - Test `generate_all()` creates files at `.cursor/commands/aurora-*.md`
    - **Verify (expect failures)**: `pytest tests/unit/cli/configurators/slash/test_cursor.py -v`
  - [x] 2.4 Implement CursorSlashCommandConfigurator in `cursor.py`
    - Define `FILE_PATHS` dict: `{"plan": ".cursor/commands/aurora-plan.md", ...}`
    - Define `FRONTMATTER` dict with Cursor-specific YAML (name, id, category, description)
    - **Verify (tests pass)**: `pytest tests/unit/cli/configurators/slash/test_cursor.py -v`
  - [x] 2.5 Write failing tests for CodexSlashCommandConfigurator in `test_codex.py`
    - Test `tool_id` property returns "codex"
    - Test `_get_global_prompts_dir()` returns `~/.codex/prompts/` by default
    - Test `_get_global_prompts_dir()` respects `CODEX_HOME` environment variable
    - Test `generate_all()` writes to global directory (not project-relative)
    - Test `resolve_absolute_path()` returns global path instead of project path
    - Test `get_frontmatter()` includes `$ARGUMENTS` placeholder and argument-hint
    - **Verify (expect failures)**: `pytest tests/unit/cli/configurators/slash/test_codex.py -v`
  - [x] 2.6 Implement CodexSlashCommandConfigurator in `codex.py`
    - Override `generate_all()` to use global `~/.codex/prompts/` directory
    - Override `update_existing()` to use global directory
    - Implement `_get_global_prompts_dir()` respecting `CODEX_HOME` env var
    - Override `resolve_absolute_path()` to return global path
    - Define `FRONTMATTER` with `$ARGUMENTS` placeholder and argument-hint
    - **Verify (tests pass)**: `pytest tests/unit/cli/configurators/slash/test_codex.py -v`
  - [x] 2.7 Write failing tests for GeminiSlashCommandConfigurator in `test_gemini.py`
    - Test `tool_id` property returns "gemini"
    - Test extends `TomlSlashCommandConfigurator` (not base)
    - Test `get_relative_path("plan")` returns `.gemini/commands/aurora/plan.toml`
    - Test `get_description("plan")` returns appropriate description string
    - Test `generate_all()` creates `.toml` files with valid TOML syntax
    - Test generated TOML has `description = "..."` and `prompt = """..."""`
    - Test markers are inside the prompt triple-quoted string
    - **Verify (expect failures)**: `pytest tests/unit/cli/configurators/slash/test_gemini.py -v`
  - [x] 2.8 Implement GeminiSlashCommandConfigurator in `gemini.py`
    - Extend `TomlSlashCommandConfigurator`
    - Define `FILE_PATHS` dict: `{"plan": ".gemini/commands/aurora/plan.toml", ...}`
    - Define `DESCRIPTIONS` dict with description for each command
    - Implement `get_description(command_id)` method
    - **Verify (tests pass)**: `pytest tests/unit/cli/configurators/slash/test_gemini.py -v`
  - [x] 2.9 Write failing tests for WindsurfSlashCommandConfigurator in `test_windsurf.py`
    - Test `tool_id` property returns "windsurf"
    - Test `get_relative_path("plan")` returns `.windsurf/workflows/aurora-plan.md`
    - Test `get_frontmatter()` includes `auto_execution_mode: 3` in YAML
    - Test `generate_all()` creates files at `.windsurf/workflows/aurora-*.md`
    - **Verify (expect failures)**: `pytest tests/unit/cli/configurators/slash/test_windsurf.py -v`
  - [x] 2.10 Implement WindsurfSlashCommandConfigurator in `windsurf.py`
    - Define `FILE_PATHS` dict: `{"plan": ".windsurf/workflows/aurora-plan.md", ...}`
    - Define `FRONTMATTER` with `description` and `auto_execution_mode: 3`
    - **Verify (tests pass)**: `pytest tests/unit/cli/configurators/slash/test_windsurf.py -v`
  - [x] 2.11 Run all high-priority tool tests together
    - **Verify**: `pytest tests/unit/cli/configurators/slash/test_claude.py tests/unit/cli/configurators/slash/test_cursor.py tests/unit/cli/configurators/slash/test_codex.py tests/unit/cli/configurators/slash/test_gemini.py tests/unit/cli/configurators/slash/test_windsurf.py -v`

- [x] 3.0 Port remaining 15 markdown-based tool configurators
  - [x] 3.1 Write parametrized tests for simple markdown tools in `test_markdown_tools.py`
    - Create parametrized test class for tools with similar patterns
    - Test tools: Antigravity, Auggie, CodeBuddy, CoStrict, Crush, iFlow, Qoder, Qwen
    - Parametrize by: tool_id, config_path_pattern, frontmatter_style
    - Test `tool_id` property for each
    - Test `get_relative_path()` returns correct pattern
    - Test `generate_all()` creates files in correct directory
    - **Verify (expect failures)**: `pytest tests/unit/cli/configurators/slash/test_markdown_tools.py -v`
  - [x] 3.2 Implement 8 simple markdown configurators (batch 1)
    - Create `antigravity.py`: `.agent/workflows/aurora-{cmd}.md`, simple description frontmatter
    - Create `auggie.py`: `.augment/commands/aurora-{cmd}.md`, description + argument-hint
    - Create `codebuddy.py`: `.codebuddy/commands/aurora/{cmd}.md`, name + description + category + tags
    - Create `costrict.py`: `.cospec/aurora/commands/aurora-{cmd}.md`, description + argument-hint
    - Create `crush.py`: `.crush/commands/aurora/{cmd}.md`, name + description + category + tags
    - Create `iflow.py`: `.iflow/commands/aurora-{cmd}.md`, name + id + category + description
    - Create `qoder.py`: `.qoder/commands/aurora/{cmd}.md`, name + description + category + tags
    - Create `qwen.py`: `.qwen/commands/aurora-{cmd}.toml`, TOML format
    - **Verify (tests pass)**: `pytest tests/unit/cli/configurators/slash/test_markdown_tools.py -v` (140 tests passing)
  - [x] 3.3 Write tests for tools with special frontmatter patterns
    - Test Amazon Q: `$ARGUMENTS` placeholder, `<UserRequest>` tags
    - Test Cline: Markdown heading frontmatter (`# Aurora: {Command}`)
    - Test RooCode: Markdown heading frontmatter (`# Aurora: {Command}`)
    - Test Factory: `.factory/commands/aurora-{cmd}.md`
    - Test GitHub Copilot: `.github/prompts/aurora-{cmd}.prompt.md`
    - Test Kilo Code: `.kilocode/workflows/aurora-{cmd}.md`
    - Test OpenCode: `.opencode/command/aurora-{cmd}.md`
    - **Verify**: Tests added to `test_markdown_tools.py`
  - [x] 3.4 Implement Amazon Q configurator in `amazon_q.py`
    - Define `FILE_PATHS`: `.amazonq/prompts/aurora-{cmd}.md`
    - Define `FRONTMATTER` with `$ARGUMENTS` and `<UserRequest>` pattern
    - **Verify (tests pass)**: Amazon Q tests passing
  - [x] 3.5 Implement Cline configurator in `cline.py`
    - Define `FILE_PATHS`: `.clinerules/workflows/aurora-{cmd}.md`
    - Define `FRONTMATTER` as markdown heading: `# Aurora: {Command}\n\n{description}`
    - **Verify (tests pass)**: Cline tests passing
  - [x] 3.6 Implement RooCode configurator in `roocode.py`
    - Define `FILE_PATHS`: `.roo/commands/aurora-{cmd}.md`
    - Define `FRONTMATTER` as markdown heading: `# Aurora: {Command}\n\n{description}`
    - **Verify (tests pass)**: RooCode tests passing
  - [x] 3.7 Implement remaining 4 configurators (Factory, GitHub Copilot, Kilo Code, OpenCode)
    - Create `factory.py`: `.factory/commands/aurora-{cmd}.md` with `$ARGUMENTS` in body
    - Create `github_copilot.py`: `.github/prompts/aurora-{cmd}.prompt.md` with `$ARGUMENTS`
    - Create `kilocode.py`: `.kilocode/workflows/aurora-{cmd}.md` (no frontmatter)
    - Create `opencode.py`: `.opencode/command/aurora-{cmd}.md` with `$ARGUMENTS` and `<UserRequest>`
    - **Verify (tests pass)**: All 4 configurator tests passing
  - [x] 3.8 Run complete markdown tools test suite
    - **Verify all 15 tools**: 203 tests passing in `test_markdown_tools.py`
    - **Verify no regressions**: 398 tests passing in full slash configurator suite
    - **Coverage**: 85.36% overall

- [x] 4.0 Update SlashCommandRegistry with all 20 tool auto-registration
  - [x] 4.1 Write failing tests for expanded registry in `test_registry.py`
    - Test `SlashCommandRegistry.get_all()` returns 20 configurators
    - Test `SlashCommandRegistry.get("claude")` returns ClaudeSlashCommandConfigurator
    - Test `SlashCommandRegistry.get("cursor")` returns CursorSlashCommandConfigurator
    - Test `SlashCommandRegistry.get("gemini")` returns GeminiSlashCommandConfigurator
    - Test `SlashCommandRegistry.get("codex")` returns CodexSlashCommandConfigurator
    - Test `SlashCommandRegistry.get("windsurf")` returns WindsurfSlashCommandConfigurator
    - Test all 20 tool IDs are retrievable
    - Test `get_available()` returns all 20 (all are always available per PRD)
    - **Verify (expect failures)**: `pytest tests/unit/cli/configurators/slash/test_registry.py -v`
  - [x] 4.2 Update `registry.py` with all 20 configurator imports and registration
    - Import all 20 configurator classes
    - Update `_ensure_initialized()` to register all 20 configurators
    - Ensure registration happens on first access (lazy loading)
    - **Verify (tests pass)**: `pytest tests/unit/cli/configurators/slash/test_registry.py -v`
  - [x] 4.3 Update slash `__init__.py` exports
    - Export all 20 configurator classes
    - Export `SlashCommandRegistry`
    - Export `SlashCommandConfigurator`, `TomlSlashCommandConfigurator`
    - Export `ALL_COMMANDS`, `AURORA_MARKERS`, `SlashCommandTarget`
    - **Verify**: `python -c "from aurora_cli.configurators.slash import SlashCommandRegistry; print(len(SlashCommandRegistry.get_all()))"`
  - [x] 4.4 Verify all configurators load without import errors
    - **Verify**: `python -c "from aurora_cli.configurators.slash import *; print('All imports OK')"`
    - **Verify**: `cd /home/hamr/PycharmProjects/aurora && make type-check`

- [x] 5.0 Integrate tool selection wizard into aur init with --tools flag
  - [x] 5.1 Write failing tests for --tools flag parsing in `test_init_tools_flag.py`
    - Test `--tools=all` parses to list of all 20 tool IDs
    - Test `--tools=none` parses to empty list
    - Test `--tools=claude,cursor` parses to `["claude", "cursor"]`
    - Test `--tools=invalid-tool` raises validation error with helpful message
    - Test `--tools=claude,invalid` shows invalid tool ID in error
    - Test error message lists available tool IDs
    - **Verify (expect failures)**: `pytest tests/unit/cli/test_init_tools_flag.py -v`
  - [x] 5.2 Add `--tools` option to init command in `init.py`
    - Add `@click.option("--tools", type=str, default=None, help="...")`
    - Add `parse_tools_flag(tools_str: str) -> list[str]` function
    - Add `validate_tool_ids(tool_ids: list[str]) -> None` function
    - Pass parsed tool IDs to tool configuration step
    - **Verify (tests pass)**: `pytest tests/unit/cli/test_init_tools_flag.py -v`
  - [x] 5.3 Write failing tests for tool selection wizard in `test_init_helpers.py`
    - Test `prompt_tool_selection()` returns list of selected tool IDs
    - Test pre-selection of already configured tools (extend mode)
    - Test grouping: "Natively supported" vs "Universal AGENTS.md"
    - Test all 20 tools appear in selection menu
    - **Verify (expect failures)**: `pytest tests/unit/cli/test_init_helpers.py -v -k "tool_selection"`
  - [x] 5.4 Update `prompt_tool_selection()` in `init_helpers.py`
    - Import `SlashCommandRegistry` to get all 20 tools
    - Build checkbox choices from registry (name, value, checked status)
    - Group tools into "Natively supported" section
    - Add "Universal AGENTS.md" as separate option
    - Return list of selected tool IDs
    - **Verify (tests pass)**: `pytest tests/unit/cli/test_init_helpers.py -v -k "tool_selection"`
  - [x] 5.5 Write failing tests for `configure_slash_commands()` helper
    - Test function accepts list of tool IDs
    - Test function calls `SlashCommandRegistry.get(tool_id).generate_all()` for each
    - Test function returns (created_tools, updated_tools) tuple
    - Test function handles missing/invalid tool IDs gracefully
    - **Verify (expect failures)**: `pytest tests/unit/cli/test_init_helpers.py -v -k "configure_slash"`
  - [x] 5.6 Implement `configure_slash_commands()` in `init_helpers.py`
    - Accept `project_path: Path, tool_ids: list[str]` parameters
    - Iterate through tool IDs, get configurator from registry
    - Call `generate_all()` for new tools, `update_existing()` for configured tools
    - Track created vs updated tools
    - Display progress with Rich console
    - **Verify (tests pass)**: `pytest tests/unit/cli/test_init_helpers.py -v -k "configure_slash"`
  - [x] 5.7 Integrate into `run_step_3_tool_configuration()` in `init.py`
    - Check if `--tools` flag was provided (non-interactive mode)
    - If provided, use parsed tool IDs directly
    - If not provided, call `prompt_tool_selection()`
    - Call `configure_slash_commands()` with selected tool IDs
    - Display summary of created/updated tools
    - **Verify**: `pytest tests/unit/cli/test_init_unified.py -v -k "step_3"`
  - [x] 5.8 Manual verification of --tools flag
    - **Verify all**: `rm -rf /tmp/test-all && mkdir /tmp/test-all && cd /tmp/test-all && git init && aur init --tools=all`
    - **Verify count**: `find /tmp/test-all -name "*.md" -o -name "*.toml" | wc -l` (expect 140: 20 tools x 7 commands)
    - **Verify specific**: `aur init --tools=claude,cursor,gemini`
    - **Verify none**: `aur init --tools=none` (should skip tool config)

- [x] 6.0 Add AI_TOOLS configuration and extend mode detection
  - [x] 6.1 Write failing tests for AI_TOOLS constant
    - Test `AI_TOOLS` is a list of 20 dicts
    - Test each dict has `name`, `value`, `available` keys
    - Test `value` matches registry tool IDs
    - Test all tools have `available: True`
    - **Verify (expect failures)**: `pytest tests/unit/cli/test_config.py -v -k "ai_tools"`
  - [x] 6.2 Add AI_TOOLS to `config.py`
    - Define `AI_TOOLS` list matching PRD Appendix C format
    - Include all 20 tools with name, value (tool_id), available
    - **Verify (tests pass)**: `pytest tests/unit/cli/test_config.py -v -k "ai_tools"`
  - [x] 6.3 Write failing tests for extend mode detection
    - Test `detect_configured_slash_tools(project_path)` returns dict[str, bool]
    - Test detection works by checking for Aurora markers in expected paths
    - Test Codex detection uses global path
    - Test returns False for tools with files but no markers
    - **Verify (expect failures)**: `pytest tests/unit/cli/test_init_helpers.py -v -k "detect_configured_slash"`
  - [x] 6.4 Implement `detect_configured_slash_tools()` in `init_helpers.py`
    - Iterate through all tools in `SlashCommandRegistry.get_all()`
    - For each tool, resolve expected file path
    - Check if file exists and contains Aurora markers
    - Return `{tool_id: is_configured}` dict
    - Handle Codex global path specially
    - **Verify (tests pass)**: `pytest tests/unit/cli/test_init_helpers.py -v -k "detect_configured_slash"`
  - [x] 6.5 Update `prompt_tool_selection()` to use extend mode detection
    - Call `detect_configured_slash_tools()` at start
    - Pre-check already configured tools in checkbox UI
    - Show "(already configured)" label for detected tools
    - **Verify**: `pytest tests/unit/cli/test_init_helpers.py -v -k "tool_selection"`
  - [x] 6.6 Manual verification of extend mode
    - **Setup**: `rm -rf /tmp/test-extend && mkdir /tmp/test-extend && cd /tmp/test-extend && git init && aur init --tools=claude`
    - **Verify Claude configured**: `ls /tmp/test-extend/.claude/commands/aur/`
    - **Re-run init**: `cd /tmp/test-extend && aur init` (Claude should be pre-checked)
    - **Add Cursor**: Select Cursor, deselect Claude
    - **Verify both exist**: `ls /tmp/test-extend/.claude/commands/aur/ /tmp/test-extend/.cursor/commands/`

- [x] 7.0 Create integration tests and verify full init flow
  - [x] 7.1 Create integration test file `test_init_tool_selection.py`
    - Test full `aur init` flow with tool selection
    - Test `aur init --tools=claude,cursor,gemini` creates correct files
    - Test `aur init --tools=all` creates all 140 files (20 x 7)
    - Test `aur init --tools=none` creates no slash command files
    - Test files have correct content (markers, frontmatter)
    - **Verify**: `pytest tests/integration/cli/test_init_tool_selection.py -v`
  - [x] 7.2 Write idempotency integration tests
    - Test running `aur init --tools=claude` twice produces same result
    - Test custom content outside markers is preserved
    - Test custom frontmatter modifications are preserved
    - Test adding new tools doesn't affect existing tool files
    - **Verify**: `pytest tests/integration/cli/test_init_tool_selection.py -v -k "idempotent"`
  - [x] 7.3 Write edge case integration tests
    - Test behavior when tool directory exists but no command files
    - Test behavior when command files exist but without Aurora markers
    - Test error handling for permission issues
    - Test Codex global path creation and updates
    - **Verify**: `pytest tests/integration/cli/test_init_tool_selection.py -v -k "edge"`
  - [x] 7.4 Verify coverage target achieved
    - **Verify coverage**: `pytest tests/unit/cli/configurators/slash/ --cov=aurora_cli.configurators.slash --cov-report=term-missing`
    - Target: >90% coverage for `aurora_cli.configurators.slash` package
    - **Result**: 98.39% coverage (549/558 lines covered, 9 lines uncovered)
    - Identify and add tests for any uncovered lines
  - [x] 7.5 Run full quality check suite
    - **Verify type checking**: `cd /home/hamr/PycharmProjects/aurora && make type-check` - PASSED (no issues)
    - **Verify linting**: Auto-fixed import sorting, 4 pre-existing issues in planning package
    - **Verify slash tests**: 527 tests passed (slash configurators + init helpers)
    - **Verify integration tests**: 35 passed (1 pre-existing failure in test_init_flow.py)
    - **Note**: Pre-existing test failures in planning/wizard tests unrelated to this PR
  - [x] 7.6 Final end-to-end verification
    - **Fresh init all tools**: All 20 tools configured successfully
    - **Count files**: 133 slash command files created (7 commands x 19 project-local tools + Codex global)
    - **Verify Claude**: plan.md has YAML frontmatter, Aurora markers, and correct template body
    - **Verify Gemini TOML**: Valid TOML format with markers inside prompt field
    - **Verify Windsurf**: auto_execution_mode: 3 present
    - **Verify Codex global**: 7 files created in CODEX_HOME/prompts/
    - **Test re-init idempotent**: 133 files after re-init (stable count)
  - [x] 7.7 Document completion and any deviations
    - **Status**: PRD-0019 IMPLEMENTED (2026-01-04)
    - **Architectural decisions**:
      - Existing files without Aurora markers raise error (protective behavior)
      - Files with markers are updated in-place, preserving content outside markers
      - Codex uses CODEX_HOME env var, defaults to ~/.codex/prompts/
    - **Deviations from PRD**:
      - File count is 133 (not exactly 140) due to some path variations
      - GitHub Copilot uses .github/prompts/ (not copilot-instructions)
    - **Test coverage**: 98.39% for slash package, 527 unit tests, 26 integration tests
    - **Final gate**: Type checking passed, linting auto-fixed

---

## Implementation Order & Dependencies

```
1.0 TomlSlashCommandConfigurator (foundation)
 │
 ├──> 2.0 High-Priority Tools (depends on 1.0 for Gemini)
 │     ├── 2.1-2.2 Claude
 │     ├── 2.3-2.4 Cursor
 │     ├── 2.5-2.6 Codex
 │     ├── 2.7-2.8 Gemini (uses TomlSlashCommandConfigurator)
 │     └── 2.9-2.10 Windsurf
 │
 ├──> 3.0 Remaining 15 Tools (can run parallel with 2.0 after 1.0)
 │
 └──> 4.0 Registry Update (depends on 2.0 and 3.0)
       │
       └──> 5.0 Init Integration (depends on 4.0)
             │
             └──> 6.0 AI_TOOLS & Extend Mode (depends on 5.0)
                   │
                   └──> 7.0 Integration Tests (depends on all)
```

## Verification Summary

After completing all tasks, run these commands:

```bash
# Unit tests for all slash configurators
pytest tests/unit/cli/configurators/slash/ -v

# Coverage check (target >90%)
pytest tests/unit/cli/configurators/slash/ --cov=aurora_cli.configurators.slash --cov-report=term-missing

# Integration tests
pytest tests/integration/cli/test_init_tool_selection.py -v

# Full CLI unit tests
pytest tests/unit/cli/ -v

# Type checking
make type-check

# Full quality check
make quality-check

# Manual E2E: All tools
rm -rf /tmp/final-test && mkdir /tmp/final-test && cd /tmp/final-test && git init
aur init --tools=all
find . -name "*.md" -path "*commands*" -o -name "*.toml" | wc -l  # Expect ~140

# Manual E2E: Specific tools
rm -rf /tmp/specific-test && mkdir /tmp/specific-test && cd /tmp/specific-test && git init
aur init --tools=claude,cursor,gemini
ls .claude/commands/aur/ .cursor/commands/ .gemini/commands/aurora/
```

---

## Tool Reference Table

| # | Tool ID | Config Path | Format | Special Notes |
|---|---------|-------------|--------|---------------|
| 1 | amazon-q | `.amazonq/prompts/aurora-*.md` | Markdown | `$ARGUMENTS`, `<UserRequest>` |
| 2 | antigravity | `.antigravity/commands/aurora-*.md` | Markdown | Simple YAML |
| 3 | auggie | `.augment/prompts/aurora-*.md` | Markdown | Simple YAML |
| 4 | claude | `.claude/commands/aur/*.md` | Markdown | YAML with tags |
| 5 | cline | `.clinerules/workflows/aurora-*.md` | Markdown | Heading frontmatter |
| 6 | codex | `~/.codex/prompts/aurora-*.md` | Markdown | **Global path** |
| 7 | codebuddy | `.codebuddy/prompts/aurora-*.md` | Markdown | Simple YAML |
| 8 | costrict | `.costrict/prompts/aurora-*.md` | Markdown | Simple YAML |
| 9 | crush | `.crush/prompts/aurora-*.md` | Markdown | Simple YAML |
| 10 | cursor | `.cursor/commands/aurora-*.md` | Markdown | YAML with id |
| 11 | factory | `.factory/commands/aurora-*.md` | Markdown | Simple YAML |
| 12 | gemini | `.gemini/commands/aurora/*.toml` | **TOML** | Markers in prompt |
| 13 | github-copilot | `.github/copilot-instructions/aurora-*.md` | Markdown | Simple YAML |
| 14 | iflow | `.iflow/prompts/aurora-*.md` | Markdown | Simple YAML |
| 15 | kilocode | `.kilocode/commands/aurora-*.md` | Markdown | Simple YAML |
| 16 | opencode | `.opencode/prompts/aurora-*.md` | Markdown | Simple YAML |
| 17 | qoder | `.qoder/prompts/aurora-*.md` | Markdown | Simple YAML |
| 18 | qwen | `.qwen/prompts/aurora-*.md` | Markdown | Simple YAML |
| 19 | roocode | `.roo/commands/aurora-*.md` | Markdown | Heading frontmatter |
| 20 | windsurf | `.windsurf/workflows/aurora-*.md` | Markdown | `auto_execution_mode: 3` |

---

*Generated from PRD-0019 on 2026-01-03*
