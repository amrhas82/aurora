# Product Requirements Document: Sprint 2 - Developer Experience & Diagnostics

**Document ID**: PRD-SPRINT2-002
**Date**: 2025-12-30
**Status**: Ready for Implementation
**Target Audience**: Agent Executor
**Sprint Duration**: 2-3 days (16-24 hours)
**Priority**: P2 (High - Quality of Life)

---

## 1. Introduction/Overview

### Problem Statement

Aurora's core functionality works (Sprint 1 completed search scoring fixes), but the developer experience when things go wrong is poor. Common issues include:

1. **No health diagnostics** - When Aurora doesn't work, users have no systematic way to diagnose what's wrong (missing config, stale index, API key issues, etc.)

2. **Manual issue resolution** - Users must manually fix common problems (recreate config, re-index, clear cache) without guidance

3. **Cryptic error messages** - Errors like "No index found" don't explain how to fix them or where to look

4. **Difficult initial setup** - New users must manually configure embeddings, API keys, and indexing without step-by-step guidance

5. **Hard failures for optional components** - Aurora crashes when tree-sitter or Git aren't available, even though it could continue with reduced functionality

This creates friction for both new users (difficult setup) and experienced users (time-consuming troubleshooting).

### High-Level Goal

Improve Aurora's developer experience by implementing comprehensive diagnostics, auto-repair capabilities, better error messages, interactive setup, and graceful degradation. Inspired by `bd doctor` from the beads CLI tool.

After this sprint:
- Users can run `aur doctor` to diagnose all issues in <2 seconds
- Common problems are auto-fixable with `aur doctor --fix`
- Error messages explain what went wrong and how to fix it
- New users can complete setup in <2 minutes with interactive wizard
- Aurora runs in degraded mode when optional components are missing

---

## 2. Goals

1. **Comprehensive health checks** - Implement `aur doctor` command that reports status of all system components
2. **Auto-repair common issues** - Implement `aur doctor --fix` to automatically resolve fixable problems
3. **Improve error messages** - Replace cryptic errors with actionable guidance
4. **Interactive setup wizard** - Implement `aur init --interactive` for guided first-time setup
5. **Graceful degradation** - Continue operation with reduced functionality when components are missing
6. **Improve installation experience** - Add post-install message, version command, and first-run guidance
7. **Preserve existing functionality** - No regressions in Sprint 1 fixes or other CLI features
8. **Consolidate documentation** - Update single CLI guide with all new commands

---

## 3. User Stories

### Story 1: New User Sets Up Aurora
**As a** developer installing Aurora for the first time
**I want** a step-by-step wizard that guides me through configuration
**So that** I can get started quickly without reading extensive documentation

**Acceptance Criteria**:
- `aur init --interactive` runs interactive setup wizard
- Wizard detects environment (Git repo, Python version)
- Wizard prompts for embeddings provider (OpenAI/Anthropic/Ollama)
- Wizard validates API keys before saving
- Wizard optionally runs initial index
- Setup completes in <2 minutes
- User can immediately run `aur query` after setup

### Story 2: Experienced User Diagnoses Issues
**As a** developer whose Aurora installation stopped working
**I want** to run a single command that checks all system components
**So that** I can quickly identify what's broken without manual investigation

**Acceptance Criteria**:
- `aur doctor` runs comprehensive health checks
- Health checks categorized (CORE SYSTEM, CODE ANALYSIS, SEARCH & RETRIEVAL, CONFIGURATION)
- Output shows color-coded status (pass/warn/fail)
- Health check completes in <2 seconds
- Summary line shows totals: "10 passed, 3 warnings, 0 failed"
- Exit code indicates status (0=all pass, 1=warnings, 2=failures)

### Story 3: Developer Auto-Repairs Issues
**As a** developer with Aurora issues identified by doctor
**I want** to automatically fix common problems with one command
**So that** I don't have to manually recreate configs or re-index

**Acceptance Criteria**:
- `aur doctor --fix` prompts user before making changes
- Fixable issues clearly separated from manual actions
- Auto-fixes: missing config, stale index, missing directories, cache limits exceeded
- Manual issues show clear instructions (e.g., "Set OPENAI_API_KEY environment variable")
- User can decline fix prompt and see manual instructions
- Idempotent (safe to run multiple times)

### Story 4: User Gets Clear Error Messages
**As a** developer using Aurora CLI
**I want** error messages that explain the problem and how to fix it
**So that** I can resolve issues without debugging Python code

**Acceptance Criteria**:
- "No index found" shows: "Run 'aur mem index .' to create one"
- "API key not set" shows: "Set OPENAI_API_KEY environment variable"
- All errors follow format: "Problem" + "Solution"
- Errors reference `aur doctor` for diagnostics
- One-line messages (not verbose stack traces)

### Story 5: Developer Works Without Optional Components
**As a** developer using Aurora in a non-Git directory or without tree-sitter
**I want** Aurora to continue working with reduced functionality
**So that** I can use core features even without all dependencies

**Acceptance Criteria**:
- Aurora runs in non-Git directories (BLA disabled with warning)
- Aurora runs without tree-sitter (text chunking fallback with warning)
- Warnings are clear but not blocking
- Environment variables can disable components (`AURORA_SKIP_GIT=1`)
- Degraded modes logged clearly

### Story 6: Developer Installs Aurora
**As a** developer installing Aurora for the first time
**I want** clear guidance after installation
**So that** I know what to do next without reading documentation

**Acceptance Criteria**:
- Post-install message displays after `pip install aurora-actr[all]`
- Message shows Aurora version and success confirmation
- Message provides clear next steps (init, index, query)
- `aur version` command shows version + git commit hash
- First `aur` command shows welcome message (only once)
- Messages are friendly and actionable

---

## 4. Functional Requirements

### FR-1: Implement `aur doctor` Health Checks

**The system must**:

1.1. Create new command: `packages/cli/src/aurora_cli/commands/doctor.py`

1.2. Implement CORE SYSTEM checks:
- Aurora CLI version (display installed version)
- Database existence and accessibility (check `~/.aurora/memory.db` exists and is readable)
- Database schema version (verify correct column count)
- API key configuration (check OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables)
- Permissions on `.aurora` directory (verify read/write access)

1.3. Implement CODE ANALYSIS checks:
- Tree-sitter parser availability (check if Python parser loads)
- Index age (calculate days since last index, warn if >7 days)
- Coverage percentage (files indexed vs total files in directory)
- Chunk quality metrics (average chunk size, total chunk count)

1.4. Implement SEARCH & RETRIEVAL checks:
- Vector store health (verify embeddings table exists and has data)
- Git BLA availability (check if in Git repo)
- Cache size and limits (check cache directory size)
- Embeddings dimension validation (verify embedding vectors are correct size)

1.5. Implement CONFIGURATION checks:
- Config file existence (check `.aurora/config.yaml` or `~/.aurora/config.json`)
- Config file validity (YAML/JSON parse without errors)
- Git repository detection (check if current directory is Git repo)
- MCP server status (check if MCP server process is running, if applicable)

1.6. Format output with color-coded indicators:
- Pass: Green checkmark
- Warning: Yellow warning icon
- Fail: Red X
- Use plain ASCII characters for compatibility: pass=checkmark, warn=!, fail=X

1.7. Display summary line: "X passed Y warnings Z failed"

1.8. Return exit codes:
- 0 if all checks pass
- 1 if warnings present
- 2 if failures present

1.9. Health check must complete in <2 seconds

**Example Output**:
```
CORE SYSTEM
  checkmark Installation: Aurora CLI v0.2.0
  checkmark Database: ~/.aurora/memory.db (2,500 chunks)
  checkmark Embeddings: OpenAI API configured
  ! Index Age: 3 days old (recommend re-index)

CODE ANALYSIS
  checkmark Tree-sitter: Python parser loaded
  ! Coverage: 65% of files indexed (35% skipped)
  checkmark Chunk Quality: Avg size 450 tokens

SEARCH & RETRIEVAL
  checkmark Semantic Search: Vector store healthy
  checkmark BLA Integration: Git blame available
  checkmark Cache: 150 MB (within limits)

CONFIGURATION
  checkmark Config File: .aurora/config.yaml
  checkmark Git Integration: Repo detected
  ! MCP Server: Not running

---------------------------------
checkmark 10 passed  ! 3 warnings  X 0 failed
```

**Implementation File**: `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/doctor.py`

**Success Criteria**: `aur doctor` runs without errors, displays categorized health checks, completes in <2s, returns correct exit code.

---

### FR-2: Implement `aur doctor --fix` Auto-Repair

**The system must**:

2.1. Add `--fix` flag to doctor command

2.2. Categorize issues as FIXABLE or MANUAL:
- FIXABLE: Missing directories, missing config files, stale index, cache exceeded
- MANUAL: API keys not set, permission errors, database corruption

2.3. Implement auto-fixes for:
- **Missing `.aurora/` directory**: Create directory with correct permissions
- **Missing config file**: Create default `config.yaml` with template values
- **Database missing/corrupted**: Initialize new database with correct schema
- **Stale index (>7 days old)**: Re-index current directory
- **Cache exceeds limits**: Clear cache directory

2.4. For MANUAL issues, display clear instructions:
- Format: "Issue: [problem]" + "Solution: [step-by-step instructions]"
- Example: "API key not set" → "Set OPENAI_API_KEY environment variable: export OPENAI_API_KEY=sk-..."

2.5. Prompt user before making changes:
- Display: "Fix X issues automatically? (Y/n):"
- If user declines (n), display manual instructions for all issues
- If user accepts (Y or Enter), proceed with fixes

2.6. Show fix progress:
- Display: "Fixing [issue name]..."
- On success: "checkmark [issue name] fixed"
- On failure: "X [issue name] failed: [error message]"

2.7. Display summary: "X fixed, Y manual actions needed"

2.8. Must be idempotent (safe to run multiple times without side effects)

**Example Output**:
```
Fixable issues:
  1. Index outdated (last indexed 3 days ago)
  2. Missing .aurora/config.yaml

Manual issues:
  3. Embeddings API key not set
     → Set OPENAI_API_KEY environment variable

Fix 2 issues automatically? (Y/n): y

Fixing Index outdated...
  checkmark Re-indexed 2,500 chunks from 150 files (took 8.3s)
Fixing Missing config...
  checkmark Created .aurora/config.yaml with defaults

Fix summary: 2 fixed, 1 manual action needed
```

**Implementation File**: `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/doctor.py` (extend with `--fix` flag)

**Success Criteria**: `aur doctor --fix` prompts before changes, fixes common issues, provides clear manual instructions, runs multiple times safely.

---

### FR-3: Improve Error Messages with Next Steps

**The system must**:

3.1. Audit current error messages in CLI commands:
- `packages/cli/src/aurora_cli/memory_manager.py`
- `packages/cli/src/aurora_cli/commands/memory.py`
- `packages/cli/src/aurora_cli/main.py`

3.2. Replace cryptic errors with actionable guidance:

| Current Error | New Error Message |
|---------------|-------------------|
| "No index found" | "No index found<newline>Run 'aur mem index .' to create one" |
| "API key not set" | "OpenAI API key not configured<newline>Set OPENAI_API_KEY environment variable" |
| "Database error" | "Database error occurred<newline>Run 'aur doctor' for diagnostics" |
| "File not found: {path}" | "File not found: {path}<newline>Check the path exists and is readable" |
| "Permission denied" | "Permission denied: {path}<newline>Check file permissions or run 'aur doctor'" |

3.3. Error message format requirements:
- One-liner explaining problem
- One-liner explaining solution
- No verbose stack traces in normal operation
- Reference `aur doctor` for complex issues

3.4. Add generic error fallback:
- For unhandled exceptions: "An error occurred<newline>Run 'aur doctor' for diagnostics or report issue on GitHub"

3.5. Update exception handling in key commands:
- `aur mem index` - handle no files found, permission errors
- `aur mem search` - handle no index, no results
- `aur query` - handle all error types

**Implementation Files**:
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/memory_manager.py`
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/memory.py`
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/main.py`

**Success Criteria**: All user-facing errors include next steps, follow one-line format, reference `aur doctor` when appropriate.

---

### FR-4: Add `aur init --interactive` Wizard

**The system must**:

4.1. Add `--interactive` flag to existing `init` command

4.2. Implement wizard flow:

**Step 1: Welcome & Environment Detection**
- Display: "Aurora Interactive Setup"
- Auto-detect: Git repository status
- Auto-detect: Python version
- Display detected environment

**Step 2: Indexing Prompt**
- Prompt: "Index current directory? (Y/n):"
- Default: Y
- If Y: proceed to step 3
- If n: skip to step 5

**Step 3: Embeddings Provider Selection**
- Prompt: "Choose embeddings provider:"
- Options:
  ```
  1. OpenAI (recommended, requires API key)
  2. Anthropic (requires API key)
  3. Ollama (local, no API key needed)
  Choice [1]:
  ```
- Validate input is 1, 2, or 3

**Step 4: API Key Input (if OpenAI or Anthropic selected)**
- Prompt: "Enter API key (starts with sk- for OpenAI, or claude- for Anthropic):"
- Validate format:
  - OpenAI: starts with `sk-`
  - Anthropic: starts with `claude-` or `sk-ant-`
- Mask input (show as asterisks if possible, else plaintext)
- Test API key validity before proceeding

**Step 5: MCP Server Prompt (Optional)**
- Prompt: "Enable MCP server for Claude Code integration? (Y/n):"
- Default: n
- If Y: note that user needs to configure Claude Desktop separately

**Step 6: Create Configuration**
- Display: "Creating configuration..."
- Create `.aurora/config.yaml` with user choices
- Initialize database with correct schema
- Display: "checkmark Configuration created"

**Step 7: Run Initial Index (if user confirmed in Step 2)**
- Display: "Indexing codebase..."
- Run index operation with progress indication
- Display: "checkmark Indexed X chunks from Y files (took Zs)"

**Step 8: Completion Summary**
- Display: "checkmark Aurora is ready!"
- Display next steps:
  ```
  Next steps:
    • Search code: aur query "your question"
    • Check health: aur doctor
    • Re-index: aur mem index .
  ```

4.3. Validation requirements:
- API keys must match provider format
- Directories must exist and be readable
- Database creation must succeed before proceeding

4.4. Error handling:
- If validation fails, re-prompt user (don't exit)
- Allow user to skip optional steps
- If fatal error: display message and suggest `aur doctor`

**Example Flow**:
```
Aurora Interactive Setup

==> Detecting environment...
  checkmark Git repository: /home/user/myproject
  checkmark Python 3.10.5
  checkmark Aurora v0.2.0

Index current directory? (Y/n): y

Choose embeddings provider:
  1. OpenAI (recommended, requires API key)
  2. Anthropic (requires API key)
  3. Ollama (local, no API key needed)
Choice [1]: 1

OpenAI API key (starts with sk-): sk-***
  checkmark API key validated

Enable MCP server for Claude Code? (Y/n): n

==> Creating configuration...
  checkmark Created .aurora/config.yaml
  checkmark Initialized database

==> Indexing codebase...
  checkmark Indexed 2,500 chunks from 150 files (took 12.3s)

checkmark Aurora is ready!

Next steps:
  • Search code: aur query "your question"
  • Check health: aur doctor
  • Re-index: aur mem index .
```

**Implementation Files**:
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init.py` (modify existing, add `--interactive` flag)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/wizard.py` (NEW: wizard logic)

**Success Criteria**: `aur init --interactive` runs step-by-step wizard, validates inputs, creates working configuration, completes in <2 minutes.

---

### FR-5: Implement Graceful Degradation

**The system must**:

5.1. Make tree-sitter parser optional:
- Detect if tree-sitter not installed or parser fails to load
- Display warning: "Tree-sitter unavailable, using text-based chunking"
- Continue operation with text-based chunking fallback
- Log degraded mode to console

5.2. Make Git optional for non-BLA operations:
- Detect if not in Git repository
- Display warning: "Not a git repository - BLA disabled"
- Continue with default activation scores (base_level=0.5)
- Log: "BLA disabled (not a git repository)"

5.3. Add test mode for embeddings:
- Support `--no-embeddings` flag for testing
- Skip embedding generation
- Use text similarity instead of semantic search
- Display warning: "Running in test mode (no embeddings)"

5.4. Add environment variable overrides:
- `AURORA_SKIP_GIT=1` - disable BLA, use default activation
- `AURORA_SKIP_EMBEDDINGS=1` - disable embeddings, use text similarity
- `AURORA_SKIP_TREESITTER=1` - disable tree-sitter, use text chunking

5.5. Warning message format:
- Display as single line with clear indication
- Format: "! [Component] unavailable - [consequence]"
- Example: "! Tree-sitter unavailable - using text chunking (reduced quality)"
- Suggest fix: "→ Install with: pip install tree-sitter"

5.6. Graceful degradation priorities:
- NEVER crash due to missing optional component
- ALWAYS warn user about degraded functionality
- ALWAYS suggest how to enable full functionality
- CONTINUE with reduced features rather than abort

**Example Warning**:
```
aur mem index .

! Not a git repository - BLA disabled
  → Run 'git init' to enable commit-based activation
  → Continuing with default activation scores

Indexing...
  checkmark Indexed 2,500 chunks (no BLA)
```

**Implementation Files**:
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/parsers/python_parser.py` (tree-sitter fallback)
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/git.py` (Git fallback)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/memory_manager.py` (handle degraded modes)

**Success Criteria**: Aurora runs in non-Git directories, without tree-sitter, without embeddings (test mode), with clear warnings, no crashes.

---

### FR-6: Improve Installation Experience

**The system must**:

6.1. Add post-install message to setup.py:
- Display after `pip install aurora-actr[all]` completes
- Show Aurora version and installation success
- Provide clear next steps (init, index, query)
- Format similar to beads installer output

6.2. Create `aur version` command:
- Display Aurora version number
- Show git commit hash if available
- Show Python version
- Show installation path
- Format: `Aurora v0.2.0 (commit-hash: abc123ef)`

6.3. Improve first-run experience:
- Add welcome message on first `aur` command
- Detect if `.aurora/` directory doesn't exist
- Suggest running `aur init` or `aur init --interactive`
- Only show once (create marker file after display)

6.4. Add "Getting Started" guidance:
- Clear next steps after installation
- Format with progress indicators (==>, checkmark)
- Friendly messaging ("Aurora is installed and ready!")
- Reference key commands (init, index, query)

**Example Post-Install Message**:
```
🔗 Aurora Installer

==> Installation complete!
==> Aurora v0.2.0 installed successfully

Aurora is installed and ready!

Get started:
  aur init              # Initialize Aurora in your project
  aur mem index .       # Index your codebase
  aur query "question"  # Search with natural language

For interactive setup:
  aur init --interactive

Check installation health:
  aur doctor
```

**Example `aur version` Output**:
```
Aurora v0.2.0 (abc123ef: HEAD@abc123ef)
Python 3.10.5
Installed at: /home/user/.local/lib/python3.10/site-packages/aurora
```

**Implementation Files**:
- `setup.py` or `pyproject.toml` (add post-install script)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/version.py` (new command)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/main.py` (first-run check)

**Success Criteria**:
- Post-install message displays after pip install
- `aur version` shows version + git hash
- First-run welcome message appears once
- Messages are friendly and actionable

---

### FR-7: Update CLI Documentation

**The system must**:

7.1. Update single consolidated CLI guide:
- File: `/home/hamr/PycharmProjects/aurora/docs/cli/CLI_USAGE_GUIDE.md`
- Add section: "Health Checks & Diagnostics"
- Add section: "Interactive Setup"
- Add section: "Graceful Degradation"

7.2. Document `aur doctor` command:
- Syntax: `aur doctor [--fix]`
- Description: "Check system health and diagnose issues"
- Examples: Basic usage, with --fix flag
- Output format explanation
- Exit codes (0/1/2)

7.3. Document `aur doctor --fix` command:
- Description: "Automatically fix common issues"
- List of fixable issues
- List of manual issues with instructions
- Safety notes (idempotent, prompts before changes)

7.4. Document `aur init --interactive` command:
- Description: "Interactive setup wizard for first-time users"
- Step-by-step flow explanation
- Configuration options
- Example session

7.5. Document graceful degradation:
- Conditions triggering degraded mode
- Warning message examples
- Environment variable overrides
- How to restore full functionality

7.6. Update troubleshooting section:
- Reference `aur doctor` as first diagnostic step
- Common issues and fixes
- Link to GitHub issues for complex problems

7.7. Documentation requirements:
- Clear examples for each command
- Copy-pasteable commands
- Explanation of output format
- Error message examples with solutions

**Implementation File**: `/home/hamr/PycharmProjects/aurora/docs/cli/CLI_USAGE_GUIDE.md` (consolidate all CLI docs here)

**Success Criteria**: Single consolidated CLI guide updated with all new commands, clear examples, troubleshooting section references `aur doctor`.

---

### FR-8: Testing & Verification

**The system must**:

8.1. Manual testing on fresh Aurora installation:
- Test performed by user on fresh install
- Test real issues (not mocked): missing config, stale index, no API key
- Verify commands work correctly through shell

8.2. Test `aur doctor` command:
- Run on fresh install (expect warnings for missing config/index)
- Run after setup (expect all checks pass)
- Verify output formatting
- Verify exit codes (0/1/2)
- Verify performance (<2 seconds)

8.3. Test `aur doctor --fix` command:
- Create broken state (delete config, stale index)
- Run `aur doctor --fix`
- Verify user prompt appears
- Accept prompt and verify fixes applied
- Verify idempotency (run again, no changes)
- Decline prompt and verify manual instructions shown

8.4. Test `aur init --interactive` wizard:
- Run on fresh install
- Test all prompt options (different providers, with/without MCP)
- Test input validation (invalid API key format)
- Verify working configuration created
- Verify can immediately run `aur query` after setup

8.5. Test error message improvements:
- Trigger each error scenario (no index, no API key, permission denied)
- Verify one-line error format
- Verify actionable guidance provided
- Verify `aur doctor` referenced appropriately

8.6. Test graceful degradation:
- Test in non-Git directory (verify BLA disabled warning)
- Test without tree-sitter (verify text chunking fallback)
- Test environment variable overrides
- Verify no crashes, only warnings

8.7. Regression testing:
- Run `make test` to ensure no test failures
- Verify Sprint 1 search scoring still works (varied scores)
- Verify existing CLI commands unchanged

8.8. Manual acceptance criteria:
- All commands work correctly when tested by user
- No crashes or unexpected errors
- Warnings are clear and actionable
- Setup completes in <2 minutes
- Health checks complete in <2 seconds

**Success Criteria**: User manually verifies all commands work on fresh install with real issues, no test failures, Sprint 1 functionality preserved.

---

## 5. Non-Goals (Out of Scope)

The following are explicitly excluded from this sprint:

1. **Database Schema Migration Bug** - Covered in PRD-SPRINT2-001, not duplicated here
2. **Search Quality Improvements** - Threshold filtering covered in PRD-SPRINT2-001
3. **Activation Score Variance** - Investigation covered in PRD-SPRINT2-001
4. **Complexity Assessment Bug** - Deferred to future sprint
5. **Single File Indexing Bug** - Deferred to future sprint
6. **MCP Integration** - MCP wizard asks if user wants it, but actual MCP setup is manual
7. **Performance Optimization** - Health checks must be fast, but no general performance work
8. **New Features** - No new search modes, scoring algorithms, or major features
9. **Automated Testing** - Manual testing by user is acceptance criteria, no E2E test suite needed for this sprint
10. **Config Command** - `aur config show` not in scope

**Scope Management**: If encountering other issues during implementation, document them as GitHub issues but do not fix. This sprint focuses only on the five developer experience improvements.

---

## 6. Design Considerations

### 6.1 Health Check Architecture

**Doctor Command Structure**:
```
aur doctor [--fix]
    ↓
health_checks.py
    ├── CoreSystemChecks
    │   ├── check_cli_version()
    │   ├── check_database()
    │   ├── check_api_keys()
    │   └── check_permissions()
    ├── CodeAnalysisChecks
    │   ├── check_treesitter()
    │   ├── check_index_age()
    │   ├── check_coverage()
    │   └── check_chunk_quality()
    ├── SearchRetrievalChecks
    │   ├── check_vector_store()
    │   ├── check_git_bla()
    │   ├── check_cache()
    │   └── check_embeddings_dim()
    └── ConfigurationChecks
        ├── check_config_file()
        ├── check_config_validity()
        ├── check_git_repo()
        └── check_mcp_server()
```

**Output Format**:
- Categorized sections (CORE SYSTEM, CODE ANALYSIS, etc.)
- Color-coded status indicators (ASCII compatible)
- Summary line with counts
- Exit codes: 0=all pass, 1=warnings, 2=failures

### 6.2 Auto-Repair Strategy

**Fix Categories**:
- **FIXABLE**: Can be automatically resolved (create files, re-index, clear cache)
- **MANUAL**: Requires user action (set API keys, fix permissions, external dependencies)

**Fix Flow**:
```
aur doctor --fix
    ↓
Categorize issues → Display fixable vs manual
    ↓
Prompt user → "Fix X issues? (Y/n)"
    ↓
If Y: Apply fixes sequentially with progress
    ↓
If n: Display manual instructions for all issues
    ↓
Summary: "X fixed, Y manual actions needed"
```

**Safety Principles**:
- Always prompt before destructive operations
- Idempotent (safe to run multiple times)
- Clear progress indication for slow operations (re-indexing)
- Rollback not implemented (user should backup first if concerned)

### 6.3 Interactive Wizard Design

**Wizard Principles**:
- Linear flow (no complex branching)
- Skip optional steps easily
- Validate inputs before proceeding
- Test API keys before saving
- Show progress and success indicators
- Complete summary with next steps

**User Experience**:
- Clear prompts with default values shown [default]
- Numbered options for multiple choice (1/2/3)
- Y/n prompts for yes/no questions
- Validation errors re-prompt (don't exit)
- Success indicators (checkmark) after each step

### 6.4 Graceful Degradation Strategy

**Degradation Levels**:
1. **Full Functionality**: All components available
2. **BLA Disabled**: No Git repo, use default activation scores
3. **Tree-sitter Fallback**: Parser unavailable, use text chunking
4. **Test Mode**: No embeddings, use text similarity

**Warning Strategy**:
- Display warning once at start of operation
- Suggest how to enable full functionality
- Continue with reduced features
- Log degraded mode for debugging

**Environment Overrides**:
- `AURORA_SKIP_GIT=1` - useful for testing non-Git directories
- `AURORA_SKIP_EMBEDDINGS=1` - useful for CI/CD without API keys
- `AURORA_SKIP_TREESITTER=1` - useful when tree-sitter not installed

---

## 7. Technical Considerations

### 7.1 Implementation Constraints

- **No Breaking Changes**: Existing CLI commands must work unchanged
- **Performance**: Health checks <2s, wizard <2 minutes
- **Compatibility**: ASCII output for cross-platform support
- **Safety**: Always prompt before destructive operations
- **Documentation**: Single consolidated CLI guide

### 7.2 Files to Create/Modify

**NEW Files**:
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/doctor.py` - Health check command
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/health_checks.py` - Health check logic
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/wizard.py` - Interactive wizard logic
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/version.py` - Version command

**MODIFY Files**:
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/init.py` - Add `--interactive` flag
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/memory_manager.py` - Improve error messages
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/memory.py` - Improve error messages
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/main.py` - Register commands, add first-run welcome
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/parsers/python_parser.py` - Tree-sitter fallback
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/git.py` - Git fallback
- `/home/hamr/PycharmProjects/aurora/setup.py` or `pyproject.toml` - Add post-install message
- `/home/hamr/PycharmProjects/aurora/docs/cli/CLI_USAGE_GUIDE.md` - Consolidate all CLI documentation

### 7.3 Testing Requirements

**Test-Driven Development (TDD) Approach**:
- Write tests FIRST before implementing each feature
- Tests must cover all functional requirements
- Tests run in isolated environment with fresh Aurora installation
- Tests use real scenarios (not mocked): missing config, stale index, no API key

**Agent Self-Verification Protocol**:
At the end of the implementation session, the agent MUST:
1. Run all created tests: `pytest tests/unit/cli/ tests/e2e/`
2. Run actual shell commands to verify behavior:
   - `aur doctor` (check output format, exit codes, performance)
   - `aur doctor --fix` (verify auto-repair with real broken state)
   - `aur init --interactive` (test wizard flow)
   - `aur version` (verify output format)
   - Trigger error conditions and verify messages
   - Test graceful degradation (non-git directory, missing tree-sitter)
3. Document test results in session notes
4. Sprint is NOT successful unless all tests pass AND shell commands work correctly

**Manual Testing Focus**:
- User tests on fresh Aurora installation
- Real issues (not mocked): missing config, stale index, no API key
- Verify commands work through shell
- Verify error messages are helpful
- Verify warnings are clear

**Regression Testing**:
- Run `make test` to ensure no test failures
- Verify Sprint 1 search scoring still works
- Verify existing CLI commands unchanged

**Acceptance Criteria**:
- **CRITICAL**: Agent runs shell commands and verifies responses at session end
- Tests written BEFORE implementation (TDD)
- All tests pass (unit + E2E)
- Shell commands work correctly when executed by agent
- User manually verifies all six features work correctly
- No crashes or unexpected errors
- Setup completes in <2 minutes
- Health checks complete in <2 seconds
- Sprint 1 functionality preserved

### 7.4 Suggested Implementation Order

1. **FR-1: `aur doctor` Health Checks** (Core feature, enables diagnostics)
2. **FR-2: `aur doctor --fix` Auto-Repair** (Extends FR-1 naturally)
3. **FR-3: Improve Error Messages** (Quick wins, improves UX immediately)
4. **FR-6: Installation Experience** (Quick wins, sets friendly tone)
5. **FR-4: `aur init --interactive` Wizard** (Independent, can be done in parallel with FR-5)
6. **FR-5: Graceful Degradation** (Independent, can be done in parallel with FR-4)
7. **FR-7: Update Documentation** (Final step after all features implemented)
8. **FR-8: Testing & Verification** (User manually tests all features on fresh install)

---

## 8. Success Metrics

### 8.1 Quantitative Metrics

**Setup Time**:
- Baseline: Unknown (manual setup)
- Target: <2 minutes with interactive wizard

**Health Check Performance**:
- Target: <2 seconds for `aur doctor`

**Issue Resolution Time**:
- Baseline: Manual troubleshooting (10-30 minutes)
- Target: <5 minutes with `aur doctor --fix`

**Error Clarity**:
- Baseline: Cryptic errors (no guidance)
- Target: 100% of errors include actionable next steps

### 8.2 Qualitative Metrics

**User Experience**:
- New users can set up Aurora without reading docs
- Experienced users can diagnose issues with one command
- Error messages are helpful, not frustrating
- Degraded modes are clear and non-blocking

**Code Quality**:
- No regressions in existing functionality
- Clean separation of concerns (health checks, wizard, error handling)
- Well-documented code

### 8.3 Acceptance Criteria Checklist

**FR-1: Health Checks**:
- [ ] `aur doctor` command runs without errors
- [ ] Outputs categorized health checks (CORE, CODE ANALYSIS, etc.)
- [ ] Color-coded status indicators (pass/warn/fail)
- [ ] Summary line shows counts
- [ ] Returns correct exit code (0/1/2)
- [ ] Completes in <2 seconds
- [ ] User manually verifies output is helpful

**FR-2: Auto-Repair**:
- [ ] `aur doctor --fix` prompts before changes
- [ ] Fixable issues clearly separated from manual
- [ ] Auto-fixes common problems (missing config, stale index)
- [ ] Manual issues show clear instructions
- [ ] User can decline prompt and see instructions
- [ ] Idempotent (safe to run multiple times)
- [ ] User manually verifies fixes work

**FR-3: Error Messages**:
- [ ] "No index found" includes fix instructions
- [ ] "API key not set" includes fix instructions
- [ ] All errors follow one-line format
- [ ] Errors reference `aur doctor` appropriately
- [ ] User manually verifies error messages are helpful

**FR-4: Interactive Wizard**:
- [ ] `aur init --interactive` runs wizard
- [ ] Wizard detects environment
- [ ] Wizard prompts for all required config
- [ ] Wizard validates inputs (API keys, etc.)
- [ ] Wizard creates working configuration
- [ ] Wizard optionally runs initial index
- [ ] Completes in <2 minutes
- [ ] User can immediately run `aur query` after setup
- [ ] User manually verifies wizard works

**FR-5: Graceful Degradation**:
- [ ] Aurora runs in non-Git directory (BLA disabled warning)
- [ ] Aurora runs without tree-sitter (text chunking fallback)
- [ ] Environment variables disable components
- [ ] Warnings are clear and non-blocking
- [ ] No crashes for missing components
- [ ] User manually verifies degraded modes work

**FR-6: Installation Experience**:
- [ ] Post-install message displays after pip install
- [ ] Message shows version and next steps
- [ ] `aur version` command shows version + git hash
- [ ] First-run welcome message appears once
- [ ] Messages are friendly and actionable
- [ ] User manually verifies installation messages

**FR-7: Documentation**:
- [ ] Single consolidated CLI guide updated
- [ ] All new commands documented with examples
- [ ] Troubleshooting section references `aur doctor`
- [ ] Documentation is clear and accurate

**FR-8: Testing**:
- [ ] User manually tests all features on fresh install
- [ ] All commands work correctly through shell
- [ ] No crashes or unexpected errors
- [ ] `make test` passes (no regressions)
- [ ] Sprint 1 search scoring still works

### 8.4 Evidence Required Before Sprint Completion

**Evidence 1: Health Checks Work**
```bash
aur doctor
# Expected: Categorized output, color-coded status, summary line, <2s execution
```

**Evidence 2: Auto-Repair Works**
```bash
# Create broken state (delete config)
rm -f ~/.aurora/config.yaml
aur doctor --fix
# Expected: Prompt shown, config recreated, summary displayed
```

**Evidence 3: Interactive Wizard Works**
```bash
aur init --interactive
# Expected: Step-by-step prompts, validation, working config, <2min completion
```

**Evidence 4: Error Messages Improved**
```bash
# Trigger error (no index)
rm -rf ~/.aurora/memory.db
aur mem search "test"
# Expected: Clear error with fix instructions (not cryptic error)
```

**Evidence 5: Graceful Degradation Works**
```bash
# Test in non-Git directory
mkdir /tmp/no-git-test && cd /tmp/no-git-test
echo "def test(): pass" > test.py
aur mem index .
# Expected: Warning about BLA disabled, but indexing succeeds
```

**Evidence 6: Installation Experience Works**
```bash
# Test post-install message (need fresh install or check setup.py output)
pip install -e .
# Expected: Post-install message with version and next steps

# Test version command
aur version
# Expected: Aurora v0.2.0 (commit-hash: abc123ef), Python version, install path

# Test first-run welcome (on fresh user)
aur
# Expected: Welcome message shown once, then marker file created
```

**Evidence 7: No Regressions**
```bash
make test
# Expected: All tests pass (same as baseline)

aur mem search "SOAR"
# Expected: Varied scores (Sprint 1 fix preserved)
```

**Evidence 8: Agent Self-Verification Complete**
```
Agent session notes documenting:
- All tests passed (pytest output)
- Shell command verification results for each feature
- Any issues encountered and resolved
- Confirmation that sprint success criteria met
```

---

## 9. Test-Driven Development (TDD) Protocol

### 9.1 Implementation Workflow

**For each feature, follow this strict order**:

1. **Write Test First**
   - Create test file: `tests/unit/cli/test_[feature].py` or `tests/e2e/test_[feature].py`
   - Write test cases covering all functional requirements
   - Test should FAIL initially (red phase)
   - Example: Write `test_aur_doctor_shows_health_checks()` before implementing doctor command

2. **Implement Minimal Code**
   - Write just enough code to make tests pass
   - Don't add extra features not covered by tests
   - Follow existing Aurora patterns and conventions

3. **Verify Tests Pass**
   - Run: `pytest tests/unit/cli/test_[feature].py -v`
   - Run: `pytest tests/e2e/test_[feature].py -v`
   - All tests must pass (green phase)

4. **Refactor (if needed)**
   - Clean up code while keeping tests passing
   - Improve readability, remove duplication
   - Tests continue to pass after refactoring

5. **Agent Self-Test**
   - Run actual shell command: `aur [command]`
   - Verify output matches expected behavior
   - Document results

### 9.2 Agent Responsibilities at Session End

**MANDATORY: Agent must perform these steps before marking sprint complete**

1. **Run All Tests**
   ```bash
   # Unit tests
   pytest tests/unit/cli/ -v

   # E2E tests
   pytest tests/e2e/ -v

   # Full suite
   make test
   ```

2. **Execute Shell Commands**
   ```bash
   # Health checks
   aur doctor
   aur doctor --fix

   # Installation UX
   aur version

   # Interactive wizard
   aur init --interactive

   # Error messages (trigger errors)
   aur mem search "test"  # with no index

   # Graceful degradation
   cd /tmp/no-git && aur mem index .
   ```

3. **Document Results**
   - Create session notes file documenting:
     - All test results (pass/fail counts)
     - Shell command outputs
     - Any issues encountered
     - Confirmation of success criteria

4. **Verify Success Criteria**
   - [ ] All tests pass (unit + E2E)
   - [ ] All shell commands work correctly
   - [ ] No regressions (`make test` passes)
   - [ ] Sprint 1 functionality preserved
   - [ ] Performance targets met (<2s for doctor, <2min for wizard)

**Sprint is NOT successful until all four verification steps complete successfully.**

---

## 10. Open Questions

### 10.1 Technical Questions

**Q1**: Should health checks run in parallel or sequential?
- **Recommendation**: Sequential for simplicity, parallel if needed for <2s target
- **Decision**: Start sequential, optimize if too slow

**Q2**: Should `aur doctor --fix` have a dry-run mode?
- **Recommendation**: Not needed for MVP, user can always decline prompt
- **Decision**: Skip for this sprint

**Q3**: How to handle API key validation without making actual API calls?
- **Recommendation**: Format validation only (starts with `sk-`), don't test actual call
- **Decision**: Format validation sufficient for wizard

**Q4**: Should graceful degradation be opt-in or opt-out?
- **Recommendation**: Opt-out (enabled by default, disable with env vars)
- **Decision**: Auto-detect and warn, user can disable via env vars

### 9.2 Process Questions

**Q5**: Should this be a feature branch or direct to main?
- **Recommendation**: Feature branch `feat/developer-experience`
- **Rationale**: Multiple changes, safer to review before merge

**Q6**: Who performs manual testing?
- **Answer**: User tests on fresh Aurora installation after implementation
- **Rationale**: Real-world testing catches issues mocks miss

**Q7**: What if implementation takes longer than 2-3 days?
- **Recommendation**: Complete core features (FR-1, FR-2, FR-3) first, defer others if needed
- **Priority**: Doctor command + auto-repair + error messages are highest value

---

## 10. Sprint Execution Checklist

### Pre-Sprint
- [ ] Read full PRD
- [ ] Understand all six developer experience improvements (health checks, auto-repair, error messages, installation UX, interactive setup, graceful degradation)
- [ ] Review related code files
- [ ] Create feature branch: `feat/developer-experience`

### FR-1: Health Checks
- [ ] Create `packages/cli/src/aurora_cli/commands/doctor.py`
- [ ] Create `packages/cli/src/aurora_cli/health_checks.py`
- [ ] Implement CORE SYSTEM checks (5 checks)
- [ ] Implement CODE ANALYSIS checks (4 checks)
- [ ] Implement SEARCH & RETRIEVAL checks (4 checks)
- [ ] Implement CONFIGURATION checks (4 checks)
- [ ] Format output with color-coded indicators
- [ ] Add summary line and exit codes
- [ ] Register command in main.py
- [ ] Verify performance (<2 seconds)

### FR-2: Auto-Repair
- [ ] Add `--fix` flag to doctor command
- [ ] Categorize issues as FIXABLE vs MANUAL
- [ ] Implement auto-fixes (5 fixes: directory, config, database, index, cache)
- [ ] Implement user prompt
- [ ] Show fix progress with status
- [ ] Display summary
- [ ] Verify idempotency

### FR-3: Error Messages
- [ ] Audit current error messages
- [ ] Replace "No index found" with actionable message
- [ ] Replace "API key not set" with actionable message
- [ ] Replace "Database error" with actionable message
- [ ] Add generic fallback error
- [ ] Update exception handling in all CLI commands

### FR-4: Interactive Wizard
- [ ] Create `packages/cli/src/aurora_cli/wizard.py`
- [ ] Add `--interactive` flag to init command
- [ ] Implement Step 1: Welcome & environment detection
- [ ] Implement Step 2: Indexing prompt
- [ ] Implement Step 3: Embeddings provider selection
- [ ] Implement Step 4: API key input and validation
- [ ] Implement Step 5: MCP server prompt
- [ ] Implement Step 6: Create configuration
- [ ] Implement Step 7: Run initial index
- [ ] Implement Step 8: Completion summary

### FR-5: Graceful Degradation
- [ ] Make tree-sitter optional with fallback
- [ ] Make Git optional for non-BLA operations
- [ ] Add `--no-embeddings` test mode
- [ ] Add environment variable overrides (3 vars)
- [ ] Format warning messages clearly
- [ ] Test all degraded modes

### FR-6: Installation Experience
- [ ] Add post-install message to setup.py/pyproject.toml
- [ ] Create `packages/cli/src/aurora_cli/commands/version.py`
- [ ] Implement `aur version` command (version + git hash + Python version)
- [ ] Add first-run welcome message to main.py
- [ ] Create marker file to show welcome only once
- [ ] Format messages with beads-style indicators (==>, checkmark)
- [ ] Test post-install message displays after pip install
- [ ] Test `aur version` shows correct information

### FR-7: Documentation
- [ ] Update CLI_USAGE_GUIDE.md with health checks section
- [ ] Document `aur doctor` command with examples
- [ ] Document `aur doctor --fix` with examples
- [ ] Document `aur init --interactive` with examples
- [ ] Document `aur version` command
- [ ] Document graceful degradation
- [ ] Update troubleshooting section

### FR-8: Testing & Verification (TDD + Agent Self-Test)

**CRITICAL: Follow TDD - Write tests FIRST, then implement**

- [ ] Write unit tests for `aur doctor` health checks
- [ ] Write E2E test for `aur doctor` command
- [ ] Implement `aur doctor` functionality
- [ ] Write unit tests for `aur doctor --fix` auto-repair
- [ ] Write E2E test for `aur doctor --fix` command
- [ ] Implement `aur doctor --fix` functionality
- [ ] Write tests for error message improvements
- [ ] Implement error message improvements
- [ ] Write tests for `aur version` command
- [ ] Implement `aur version` functionality
- [ ] Write tests for interactive wizard
- [ ] Implement interactive wizard
- [ ] Write tests for graceful degradation
- [ ] Implement graceful degradation
- [ ] Run all tests: `pytest tests/unit/cli/ tests/e2e/` (must pass)
- [ ] Run `make test` and verify no regressions

**Agent Self-Verification (MANDATORY)**:
- [ ] Agent runs `aur doctor` and verifies output format
- [ ] Agent runs `aur doctor --fix` with broken state and verifies repairs
- [ ] Agent runs `aur init --interactive` and tests wizard flow
- [ ] Agent runs `aur version` and verifies output
- [ ] Agent triggers error conditions and verifies messages
- [ ] Agent tests graceful degradation (non-git dir, no tree-sitter)
- [ ] Agent documents all test results in session notes
- [ ] **Sprint marked successful ONLY if all shell commands work correctly**

**User Manual Testing**:
- [ ] User manually tests `aur doctor` on fresh install
- [ ] User manually tests `aur doctor --fix` with broken state
- [ ] User manually tests `aur init --interactive` wizard
- [ ] User manually tests error messages
- [ ] User manually tests graceful degradation
- [ ] Verify Sprint 1 search scoring still works

### Completion Phase
- [ ] Collect all evidence items (7 evidence points)
- [ ] Verify all acceptance criteria met
- [ ] Commit with clear message: `feat(cli): add developer experience improvements`
- [ ] Update sprint status
- [ ] Merge feature branch to main

---

## 11. Red Flags (Sprint Failure Indicators)

**STOP immediately and reassess if ANY of these occur**:

- Modifying existing CLI commands in breaking ways (not backward compatible)
- Health checks take >2 seconds to run
- Interactive wizard requires >2 minutes to complete
- Auto-repair causes data loss or corruption
- Graceful degradation causes crashes instead of warnings
- Error messages are still cryptic after changes
- Documentation scattered across multiple files (not consolidated)
- Expanding scope to include schema migration or search quality (those are in PRD-SPRINT2-001)
- Skipping manual verification step
- Tests pass but features don't work when user tests them

**If a red flag is raised**: Document the situation, stop work, and re-evaluate the approach. Consider splitting sprint into smaller phases if scope is too large.

---

## 12. Context References

### Related Documents
- **Sprint 1 PRD**: `/home/hamr/PycharmProjects/aurora/tasks/0012-prd-sprint1-fix-search-scoring.md` (completed)
- **Sprint 2 Part A PRD**: `/home/hamr/PycharmProjects/aurora/tasks/0013-prd-sprint2-cli-robustness-search-quality.md` (separate concerns)
- **Source Document**: `/home/hamr/Documents/PycharmProjects/aurora/docs/development/aurora_fixes/SPRINT2-add-on.md`
- **Beads Learnings**: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/BEADS_LEARNINGS_FOR_AURORA.md` (inspiration for `bd doctor`)
- **CLI Guide**: `/home/hamr/PycharmProjects/aurora/docs/cli/CLI_USAGE_GUIDE.md` (to be updated)

### Key Files
- `packages/cli/src/aurora_cli/commands/doctor.py` (NEW)
- `packages/cli/src/aurora_cli/health_checks.py` (NEW)
- `packages/cli/src/aurora_cli/wizard.py` (NEW)
- `packages/cli/src/aurora_cli/commands/init.py` (MODIFY)
- `packages/cli/src/aurora_cli/memory_manager.py` (MODIFY)
- `packages/context-code/src/aurora_context_code/parsers/python_parser.py` (MODIFY)
- `packages/context-code/src/aurora_context_code/git.py` (MODIFY)

### Inspiration
This sprint is inspired by `bd doctor` from beads CLI tool, which provides:
- Comprehensive health checks (44 checks)
- Auto-repair with `--fix` flag
- Clear categorization (CORE, GIT, INTEGRATIONS, etc.)
- Color-coded output
- Graceful degradation with warnings

**Key differences from beads**:
- Aurora doesn't need git hooks (not an issue tracker)
- Aurora doesn't need sync-branch (not distributed)
- Aurora needs embeddings/API validation (code search specific)

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-30 | Claude Sonnet 4.5 | Initial PRD creation based on SPRINT2-add-on.md |

---

**END OF DOCUMENT**
