# Tasks: Sprint 2 - Developer Experience & Diagnostics

**Generated from**: Beads CLI UX analysis
**Date**: 2025-12-30
**Sprint Duration**: 2-3 days
**Priority**: P2 (High - Quality of Life)

---

## Overview

Improve Aurora's developer experience by implementing comprehensive health checks, auto-repair capabilities, and better error messages. Inspired by `bd doctor` from beads CLI.

### Sprint Goals

1. Add comprehensive health diagnostics (`aur doctor`)
2. Implement auto-repair for common issues (`aur doctor --fix`)
3. Improve error messages with actionable next steps
4. Add interactive setup wizard
5. Implement graceful degradation for missing dependencies

---

## Relevant Files

### CLI Commands
- `packages/cli/src/aurora_cli/commands/doctor.py` - NEW: Health check command
- `packages/cli/src/aurora_cli/commands/init.py` - MODIFY: Add interactive mode
- `packages/cli/src/aurora_cli/main.py` - MODIFY: Register new commands

### Existing Commands to Enhance
- `packages/cli/src/aurora_cli/commands/verify.py` - Current `--verify` command (reference)
- `packages/cli/src/aurora_cli/memory_manager.py` - MODIFY: Better error messages

### Core Systems to Check
- `packages/core/src/aurora_core/store/sqlite.py` - Database health checks
- `packages/context-code/src/aurora_context_code/semantic/embedding_provider.py` - API key validation
- `packages/context-code/src/aurora_context_code/parsers/python_parser.py` - Tree-sitter parser checks

### Configuration
- `packages/core/src/aurora_core/config.py` - Config file management
- `.aurora/config.yaml` - User config file (check existence, validity)

### Test Files
- `tests/unit/cli/test_doctor_command.py` - NEW: Unit tests for doctor command
- `tests/e2e/test_cli_doctor.py` - NEW: E2E tests for health checks

### Documentation
- `docs/cli/CLI_USAGE_GUIDE.md` - MODIFY: Add doctor command docs
- `docs/TROUBLESHOOTING.md` - MODIFY: Reference doctor for diagnostics

---

## Tasks

### Task 2.1: Implement `aur doctor` Health Checks

**Goal**: Create comprehensive health check command that reports system status

**Sub-tasks**:
- [ ] 2.1.1 Create `packages/cli/src/aurora_cli/commands/doctor.py`
- [ ] 2.1.2 Implement CORE SYSTEM checks:
  - [ ] Aurora CLI version
  - [ ] Database existence and accessibility
  - [ ] Database schema version
  - [ ] API key configuration (OpenAI/Anthropic)
  - [ ] Permissions on .aurora directory
- [ ] 2.1.3 Implement CODE ANALYSIS checks:
  - [ ] Tree-sitter parser availability
  - [ ] Index age (warn if >7 days old)
  - [ ] Coverage percentage (files indexed vs total)
  - [ ] Chunk quality metrics (avg size, count)
- [ ] 2.1.4 Implement SEARCH & RETRIEVAL checks:
  - [ ] Vector store health
  - [ ] Git BLA availability
  - [ ] Cache size and limits
  - [ ] Embeddings dimension validation
- [ ] 2.1.5 Implement CONFIGURATION checks:
  - [ ] Config file existence
  - [ ] Config file validity (YAML parse)
  - [ ] Git repository detection
  - [ ] MCP server status (if running)
- [ ] 2.1.6 Add color-coded output: ✓ (green), ⚠ (yellow), ✖ (red)
- [ ] 2.1.7 Add summary line: "✓ X passed ⚠ Y warnings ✖ Z failed"
- [ ] 2.1.8 Register command in `main.py`

**Acceptance Criteria**:
- `aur doctor` runs without errors
- Outputs categorized health checks (CORE, CODE ANALYSIS, etc.)
- Returns exit code 0 if all pass, 1 if warnings, 2 if failures
- Takes <2 seconds to run

**Example Output**:
```
aur doctor

CORE SYSTEM
  ✓ Installation: Aurora CLI v0.2.0
  ✓ Database: ~/.aurora/chunks.db (2,500 chunks)
  ✓ Embeddings: OpenAI API configured
  ⚠ Index Age: 3 days old (recommend re-index)

CODE ANALYSIS
  ✓ Tree-sitter: Python parser loaded
  ⚠ Coverage: 65% of files indexed (35% skipped)
  ✓ Chunk Quality: Avg size 450 tokens

SEARCH & RETRIEVAL
  ✓ Semantic Search: Vector store healthy
  ✓ BLA Integration: Git blame available
  ✓ Cache: 150 MB (within limits)

CONFIGURATION
  ✓ Config File: .aurora/config.yaml
  ✓ Git Integration: Repo detected
  ⚠ MCP Server: Not running

─────────────────────────────
✓ 10 passed  ⚠ 3 warnings  ✖ 0 failed
```

---

### Task 2.2: Implement `aur doctor --fix` Auto-Repair

**Goal**: Automatically fix common issues detected by health checks

**Sub-tasks**:
- [ ] 2.2.1 Add `--fix` flag to doctor command
- [ ] 2.2.2 Categorize issues as: FIXABLE vs MANUAL
- [ ] 2.2.3 Implement auto-fixes for:
  - [ ] Create missing `.aurora/` directory
  - [ ] Create default `config.yaml`
  - [ ] Initialize database schema if missing
  - [ ] Re-index if index is stale (>7 days)
  - [ ] Clear cache if exceeds limits
- [ ] 2.2.4 For MANUAL issues, provide clear instructions
- [ ] 2.2.5 Add confirmation prompt: "Fix X issues? (Y/n)"
- [ ] 2.2.6 Show fix progress with status indicators
- [ ] 2.2.7 Display summary: "X fixed, Y manual actions needed"

**Acceptance Criteria**:
- `aur doctor --fix` prompts user before making changes
- Successfully fixes common issues (missing config, stale index)
- Provides clear instructions for manual fixes (API keys, permissions)
- Idempotent (safe to run multiple times)

**Example Output**:
```
aur doctor --fix

Fixable issues:
  1. Index outdated (last indexed 3 days ago)
  2. Missing .aurora/config.yaml

Manual issues:
  3. Embeddings API key not set
     → Set OPENAI_API_KEY environment variable

Fix 2 issues automatically? (Y/n): y

Fixing Index outdated...
  ✓ Re-indexed 2,500 chunks from 150 files (took 8.3s)
Fixing Missing config...
  ✓ Created .aurora/config.yaml with defaults

Fix summary: 2 fixed, 1 manual action needed
```

---

### Task 2.3: Improve Error Messages with Next Steps

**Goal**: Replace cryptic errors with actionable guidance

**Sub-tasks**:
- [ ] 2.3.1 Audit current error messages in `memory_manager.py`
- [ ] 2.3.2 Replace "No index found" with:
  ```
  ⚠ No index found
    Run 'aur mem index .' to create one
    Or: aur init --with-index
  ```
- [ ] 2.3.3 Replace "API key not set" with:
  ```
  ⚠ OpenAI API key not configured
    Set environment variable: export OPENAI_API_KEY=sk-...
    Or add to .aurora/config.yaml:
      embeddings:
        provider: openai
        api_key: sk-...
  ```
- [ ] 2.3.4 Add error codes for programmatic handling:
  ```
  ERROR [AUR001]: No index found
  ```
- [ ] 2.3.5 Add "Run 'aur doctor' for diagnostics" to generic errors
- [ ] 2.3.6 Update exception handling in search/index commands

**Acceptance Criteria**:
- All user-facing errors include next steps
- Error messages follow format: "⚠ Problem" + "→ Solution"
- Generic errors reference `aur doctor` for diagnostics
- No bare exceptions without helpful context

---

### Task 2.4: Add `aur init --interactive` Wizard

**Goal**: Guide users through initial setup with prompts

**Sub-tasks**:
- [ ] 2.4.1 Add `--interactive` flag to `init` command
- [ ] 2.4.2 Implement wizard flow:
  - [ ] Welcome message
  - [ ] Detect git repo (show status)
  - [ ] Ask: "Index current directory? (Y/n)"
  - [ ] Ask: "Embeddings provider? (openai/anthropic/ollama)"
  - [ ] Ask: "API key?" (if openai/anthropic)
  - [ ] Ask: "Enable MCP server? (Y/n)"
- [ ] 2.4.3 Validate inputs (API key format, directory exists)
- [ ] 2.4.4 Create config file with user choices
- [ ] 2.4.5 Run initial index if user confirmed
- [ ] 2.4.6 Show summary: "✓ Aurora initialized" + next steps

**Acceptance Criteria**:
- `aur init --interactive` runs step-by-step wizard
- Validates user inputs before saving
- Creates working config.yaml from wizard inputs
- Optionally runs initial index
- Shows clear next steps after completion

**Example Flow**:
```
aur init --interactive

🔗 Aurora Interactive Setup

==> Detecting environment...
  ✓ Git repository: /home/user/myproject
  ✓ Python 3.10.5
  ✓ Aurora v0.2.0

Index current directory? (Y/n): y

Choose embeddings provider:
  1. OpenAI (recommended, requires API key)
  2. Anthropic
  3. Ollama (local, no API key needed)
Choice [1]: 1

OpenAI API key (starts with sk-): sk-...
  ✓ API key validated

Enable MCP server for Claude Code? (Y/n): y

==> Creating configuration...
  ✓ Created .aurora/config.yaml
  ✓ Initialized database

==> Indexing codebase...
  ✓ Indexed 2,500 chunks from 150 files (took 12.3s)

✓ Aurora is ready!

Next steps:
  • Search code: aur query "your question"
  • Check health: aur doctor
  • Re-index: aur mem index .
```

---

### Task 2.5: Implement Graceful Degradation

**Goal**: Continue operation with reduced functionality when components are missing

**Sub-tasks**:
- [ ] 2.5.1 Make tree-sitter parser optional:
  - [ ] Detect if tree-sitter not installed
  - [ ] Warn user but continue with text-based chunking
  - [ ] Log degraded mode: "Using text chunking (tree-sitter unavailable)"
- [ ] 2.5.2 Make git optional for non-BLA operations:
  - [ ] Detect if not a git repo
  - [ ] Warn but continue with default activation scores
  - [ ] Log: "BLA disabled (not a git repository)"
- [ ] 2.5.3 Add `--no-embeddings` mode for testing:
  - [ ] Skip embedding generation
  - [ ] Use text similarity instead
  - [ ] Warn: "Running in test mode (no embeddings)"
- [ ] 2.5.4 Add environment variable overrides:
  - [ ] `AURORA_SKIP_GIT=1` - disable BLA
  - [ ] `AURORA_SKIP_EMBEDDINGS=1` - disable embeddings
  - [ ] `AURORA_SKIP_TREESITTER=1` - disable parser

**Acceptance Criteria**:
- Aurora runs in non-git directories (without BLA)
- Aurora runs without tree-sitter (text chunking fallback)
- Degraded modes log clear warnings
- No hard failures for optional components
- Test mode (`--no-embeddings`) works for CI

**Example Warning**:
```
aur mem index .

⚠ Not a git repository - BLA disabled
  → Run 'git init' to enable commit-based activation
  → Continuing with default activation scores

Indexing...
  ✓ Indexed 2,500 chunks (no BLA)
```

---

## Testing Strategy

### Unit Tests
- [ ] `tests/unit/cli/test_doctor_command.py`
  - Test each health check function independently
  - Mock database, config, API calls
  - Verify exit codes (0/1/2)

### Integration Tests
- [ ] `tests/e2e/test_cli_doctor.py`
  - Test `aur doctor` with real Aurora installation
  - Test `aur doctor --fix` repairs issues
  - Test interactive init wizard

### Manual Testing Checklist
- [ ] Run `aur doctor` on fresh install (expect warnings)
- [ ] Run `aur doctor --fix` to repair issues
- [ ] Run `aur init --interactive` wizard
- [ ] Test graceful degradation (non-git directory)
- [ ] Test error messages show next steps

---

## Success Metrics

1. **Health Checks**: `aur doctor` runs <2s, reports 10+ checks
2. **Auto-Repair**: `aur doctor --fix` fixes 80% of common issues
3. **Error Clarity**: 100% of user-facing errors include next steps
4. **Setup Time**: New users complete setup in <2 minutes with wizard
5. **Degradation**: Aurora runs in degraded mode without tree-sitter/git

---

## Documentation Updates

- [ ] Add `aur doctor` to CLI_USAGE_GUIDE.md
- [ ] Document `--fix` flag and fixable issues
- [ ] Document `--interactive` wizard flow
- [ ] Add troubleshooting section referencing `aur doctor`
- [ ] Document graceful degradation modes
- [ ] Update TROUBLESHOOTING.md with common issues

---

## Notes

**Inspired by `bd doctor` from beads**:
- Comprehensive health checks (44 checks in bd)
- Auto-repair with `--fix` flag
- Clear categorization (CORE, GIT, INTEGRATIONS, etc.)
- Color-coded output (✓/⚠/✖)
- Graceful degradation with warnings

**Key differences from beads**:
- Aurora doesn't need git hooks (not an issue tracker)
- Aurora doesn't need sync-branch (not distributed)
- Aurora needs embeddings/API validation (code search specific)

**Implementation Philosophy**:
- Fail soft, warn loud
- Always provide next steps
- Automation where safe, guidance where not
- Measure twice, cut once (confirm before destructive ops)
