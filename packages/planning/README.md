# Aurora Planning System

**Structured plan creation and management for AI-assisted development workflows.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Overview

Aurora Planning provides a comprehensive system for breaking down complex development goals into structured, actionable plans. It integrates with the Aurora cognitive architecture to enable AI agents to work systematically through multi-step projects.

**Key Features:**
- **Structured Planning**: Eight-file plan structure (4 base files + 4 capability specs)
- **Auto-Increment IDs**: Automatic plan numbering with slug-based naming (`0001-oauth-auth`)
- **Archive Management**: Timestamp-based archiving with atomic operations
- **Rich CLI**: Beautiful terminal UI with tables, panels, and progress indicators
- **Flexible Configuration**: Environment variables and config file support
- **Template-Based**: Jinja2 templates for consistent plan generation
- **Full Validation**: JSON Schema and Pydantic model validation

## Installation

### From Source (Development)

```bash
# Clone the repository
cd packages/planning

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### From PyPI (Future)

```bash
pip install aurora-planning
```

## Quick Start

Get started with Aurora Planning in 5 commands:

### 1. Initialize Planning Directory

```bash
# Initialize .aurora/plans/ directory structure
aur plan init
```

This creates:
```
.aurora/
├── plans/
│   ├── active/     # Active plans
│   └── archive/    # Archived plans
└── config/
    └── tools/      # Tool configurations
```

### 2. Create Your First Plan

```bash
# Create a plan with automatic goal decomposition
aur plan create "Implement OAuth2 authentication with JWT tokens"
```

This generates a plan with ID `0001-oauth2-authentication` containing 8 files:
- `plan.md` - High-level plan overview with subgoals
- `prd.md` - Product requirements document
- `tasks.md` - Implementation task checklist
- `agents.json` - Machine-readable metadata
- `specs/` - Four capability specifications (planning, commands, validation, schemas)

### 3. List Active Plans

```bash
# Show all active plans
aur plan list

# Show archived plans
aur plan list --archived

# Show both active and archived
aur plan list --all
```

### 4. View Plan Details

```bash
# View plan dashboard with rich formatting
aur plan view 0001

# View in JSON format
aur plan view 0001 --format json

# Partial ID matching works too
aur plan view oauth2
```

### 5. Archive Completed Plans

```bash
# Archive a completed plan (with confirmation prompt)
aur plan archive 0001

# Skip confirmation
aur plan archive 0001 --yes
```

## Commands

### `aur plan init`

Initialize the Aurora planning directory structure.

```bash
aur plan init [--path <directory>]
```

**Options:**
- `--path` - Custom directory path (default: current directory)

**Creates:**
- `.aurora/plans/active/` - Active plans directory
- `.aurora/plans/archive/` - Archived plans directory
- `.aurora/config/tools/` - Tool configuration directory
- `.aurora/project.md` - Project context template

### `aur plan create`

Create a new structured plan with automatic ID generation.

```bash
aur plan create <goal> [options]
```

**Arguments:**
- `goal` - Clear description of what to achieve (10-500 characters)

**Options:**
- `--context, -c <file>` - Context files for informed decomposition (multiple allowed)
- `--no-decompose` - Skip SOAR decomposition (create single-task plan)
- `--format, -f <rich|json>` - Output format (default: rich)
- `--no-auto-init` - Disable automatic initialization

**Examples:**

```bash
# Simple plan creation
aur plan create "Add user registration with email verification"

# With context files
aur plan create "Add caching layer" \
  --context src/api.py \
  --context src/database.py

# Skip decomposition for simple tasks
aur plan create "Fix typo in README" --no-decompose

# JSON output for scripting
aur plan create "Implement logging system" --format json
```

### `aur plan list`

List active and/or archived plans with filtering and formatting options.

```bash
aur plan list [options]
```

**Options:**
- `--archived` - Show archived plans only
- `--all` - Show both active and archived plans
- `--format, -f <rich|json>` - Output format (default: rich)

**Examples:**

```bash
# List active plans (default)
aur plan list

# List archived plans
aur plan list --archived

# List all plans
aur plan list --all

# JSON output for scripting
aur plan list --format json
```

### `aur plan view`

Display detailed plan information with file status and progress tracking.

```bash
aur plan view <plan_id> [options]
```

**Arguments:**
- `plan_id` - Plan ID (full or partial, e.g., `0001` or `oauth2`)

**Options:**
- `--archived` - Include archived plans in search
- `--format, -f <rich|json>` - Output format (default: rich)

**Examples:**

```bash
# View active plan
aur plan view 0001

# View with partial ID
aur plan view oauth

# Include archived plans in search
aur plan view 0001 --archived

# JSON output
aur plan view 0001 --format json
```

### `aur plan archive`

Archive a completed plan with automatic timestamp naming.

```bash
aur plan archive <plan_id> [options]
```

**Arguments:**
- `plan_id` - Plan ID to archive (full or partial)

**Options:**
- `--yes, -y` - Skip confirmation prompt

**Examples:**

```bash
# Archive with confirmation
aur plan archive 0001

# Skip confirmation
aur plan archive 0001 --yes

# Archive using partial ID
aur plan archive oauth --yes
```

**Archive Behavior:**
- Moves plan from `active/0001-oauth-auth/` to `archive/2026-01-15-0001-oauth-auth/`
- Updates `agents.json` with `status: archived` and `archived_at` timestamp
- Uses atomic file operations with automatic rollback on error
- Preserves all plan files and directory structure

## Examples

### Example 1: OAuth2 Authentication Implementation

```bash
# Step 1: Create plan
aur plan create "Implement OAuth2 authentication with JWT tokens"

# Output shows:
# ✓ Plan created: 0001-oauth2-authentication
# └─ Location: .aurora/plans/active/0001-oauth2-authentication/
# └─ Files generated: 8 (plan.md, prd.md, tasks.md, agents.json, + 4 specs)

# Step 2: View plan details
aur plan view 0001

# Output shows:
# Plan: 0001-oauth2-authentication
# Goal: Implement OAuth2 authentication with JWT tokens
# Status: pending
# Subgoals:
#   1. [sg-1] Design OAuth2 flow → @architect
#   2. [sg-2] Implement JWT generation → @backend-dev
#   3. [sg-3] Add refresh token logic → @backend-dev

# Step 3: Work on the plan (edit files, complete tasks)
# ... development work ...

# Step 4: Archive when complete
aur plan archive 0001 --yes

# Output shows:
# ✓ Plan archived: 0001-oauth2-authentication
# └─ Location: .aurora/plans/archive/2026-01-15-0001-oauth2-authentication/
```

### Example 2: User Registration System

```bash
# Create plan with context files
aur plan create "Add user registration with email verification" \
  --context src/models/user.py \
  --context src/api/routes.py

# List all plans to see status
aur plan list

# Output:
# ┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
# ┃ Plan ID ┃ Title                         ┃ Progress  ┃ Last Modified  ┃
# ┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
# │ 0002    │ User registration system      │ 3/12      │ 2 hours ago    │
# │ 0001    │ OAuth2 authentication         │ 5/8       │ 1 day ago      │
# └─────────┴───────────────────────────────┴───────────┴────────────────┘
```

### Example 3: Quick Bug Fix (No Decomposition)

```bash
# For simple tasks, skip decomposition
aur plan create "Fix login form validation error" --no-decompose

# Creates simple plan with single task
aur plan view 0003

# Output shows:
# Plan: 0003-fix-login-form-validation
# Goal: Fix login form validation error
# Subgoals: 1 (single task)
```

## Configuration

Aurora Planning can be configured via environment variables or config files.

### Environment Variables

```bash
# Custom plans directory
export AURORA_PLANS_DIR=/path/to/plans

# Custom template directory
export AURORA_TEMPLATE_DIR=/path/to/templates

# Auto-increment behavior
export AURORA_PLANNING_AUTO_INCREMENT=true

# Auto-archive on completion
export AURORA_PLANNING_ARCHIVE_ON_COMPLETE=false
```

### Config File

Edit `~/.aurora/config.yaml` or project `.aurora/config/planning.yaml`:

```yaml
planning:
  base_dir: ~/.aurora/plans
  template_dir: <package>/templates
  auto_increment: true
  archive_on_complete: false
```

### Configuration Precedence

1. Environment variables (highest priority)
2. Project-level config file (`.aurora/config/planning.yaml`)
3. User-level config file (`~/.aurora/config.yaml`)
4. Package defaults (lowest priority)

## File Structure

### Plan Directory Layout

Each plan has an eight-file structure:

```
.aurora/plans/active/0001-oauth-auth/
├── plan.md                           # Human-readable plan overview
├── prd.md                            # Product requirements document
├── tasks.md                          # Implementation task checklist
├── agents.json                       # Machine-readable metadata
└── specs/                            # Capability specifications
    ├── planning/
    │   └── oauth-auth-planning.md    # Planning capability spec
    ├── commands/
    │   └── oauth-auth-commands.md    # Command schemas
    ├── validation/
    │   └── oauth-auth-validation.md  # Validation rules
    └── schemas/
        └── oauth-auth-schemas.md     # Data schemas
```

### File Descriptions

| File | Purpose | Format |
|------|---------|--------|
| `plan.md` | High-level plan overview with subgoals and dependencies | Markdown |
| `prd.md` | Detailed product requirements with acceptance criteria | Markdown |
| `tasks.md` | Implementation task checklist with GFM checkboxes | Markdown |
| `agents.json` | Machine-readable metadata (IDs, status, dates) | JSON |
| `specs/planning/*.md` | Planning capability specification | Markdown |
| `specs/commands/*.md` | Command schemas and examples | Markdown |
| `specs/validation/*.md` | Validation rules and test scenarios | Markdown |
| `specs/schemas/*.md` | Data schemas and constraints | Markdown |

### agents.json Schema

```json
{
  "plan_id": "0001-oauth-auth",
  "goal": "Implement OAuth2 authentication with JWT tokens",
  "status": "pending",
  "created_at": "2026-01-15T10:30:00Z",
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Design OAuth2 flow",
      "description": "Design authorization and token exchange flow",
      "agent_id": "@architect",
      "status": "pending",
      "dependencies": []
    }
  ]
}
```

## Architecture

### Core Components

- **ID Generator** (`id_generator.py`) - Auto-increment plan IDs with collision handling
- **Renderer** (`renderer.py`) - Jinja2-based template rendering for all 8 files
- **Config Manager** (`planning_config.py`) - Configuration loading with env var overrides
- **Validators** (`validators/`) - JSON Schema and Pydantic validation
- **Parsers** (`parsers/`) - Markdown and JSON parsing utilities
- **Archive Utils** (`archive_utils.py`) - Atomic archive operations with rollback

### Command Architecture

```
aurora_cli.commands.plan
├── create_command()  → aurora_planning.renderer.render_plan_files()
├── list_command()    → aurora_planning.commands.list.list_plans()
├── view_command()    → aurora_planning.commands.view.show_plan()
└── archive_command() → aurora_planning.archive_utils.archive_plan_atomic()
```

### Data Flow

```
User Input (CLI)
  ↓
Command Handler (aurora_cli)
  ↓
Core Logic (aurora_planning)
  ↓
Template Renderer → Files Written
  ↓
Validation (JSON Schema + Pydantic)
  ↓
Rich Output (CLI)
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/aurora-project/aurora.git
cd aurora/packages/planning

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aurora_planning --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m acceptance    # Acceptance tests only

# Run fast tests only (skip slow benchmarks)
pytest -m "not slow"
```

### Code Quality

```bash
# Lint code
ruff check src/

# Format code
ruff format src/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

### Building Documentation

```bash
# Generate API documentation
make docs

# View documentation
open docs/planning/api/index.html
```

## Troubleshooting

### Common Issues

**Issue**: `Planning directory not initialized`

```bash
# Solution: Run init command
aur plan init
```

**Issue**: `Plan ID collision detected`

```bash
# This is rare but handled automatically
# The system will retry with the next available ID
# Check logs for details: ~/.aurora/logs/planning.log
```

**Issue**: `Template rendering failed`

```bash
# Solution: Verify template directory exists
ls $(python -c "from aurora_planning.planning_config import get_template_dir; print(get_template_dir())")

# Or use custom template directory
export AURORA_TEMPLATE_DIR=/path/to/templates
```

**Issue**: `Permission denied when creating plan`

```bash
# Solution: Check directory permissions
ls -ld ~/.aurora/plans/active/

# Fix permissions
chmod 755 ~/.aurora/plans/active/
```

### Debug Mode

Enable verbose logging:

```bash
# Set log level
export AURORA_LOG_LEVEL=DEBUG

# Run command
aur plan create "Test" 2>&1 | tee debug.log
```

## Performance

### Benchmarks (Aspirational Targets)

| Operation | Target | Typical | Notes |
|-----------|--------|---------|-------|
| Plan creation | <5s | ~2s | 8 files with template rendering |
| Plan listing (50 plans) | <500ms | ~200ms | Uses cached manifest |
| Plan viewing | <200ms | ~100ms | Single directory read |
| Archive operation | <1s | ~500ms | Atomic move + JSON update |

### Optimization Tips

1. **Use manifest caching**: Enabled by default for list operations
2. **Batch operations**: Create multiple plans in a script for efficiency
3. **Minimal context files**: Only include essential files with `--context`
4. **JSON output**: Use `--format json` in scripts (faster than rich formatting)

## Resources

### Documentation

- **User Guide**: [docs/planning/user-guide.md](../../docs/planning/user-guide.md) - Comprehensive workflow guide
- **API Reference**: [docs/planning/api/](../../docs/planning/api/) - Full API documentation
- **Cheat Sheet**: [docs/planning/cheat-sheet.md](../../docs/planning/cheat-sheet.md) - Quick reference
- **Architecture**: [docs/architecture/PLANNING_ARCHITECTURE.md](../../docs/architecture/PLANNING_ARCHITECTURE.md) - System design

### Links

- **Homepage**: https://github.com/aurora-project/aurora
- **Documentation**: https://aurora-docs.example.com
- **Issue Tracker**: https://github.com/aurora-project/aurora/issues
- **Changelog**: [CHANGELOG.md](../../CHANGELOG.md)

### Support

- **Questions**: Open a [GitHub Discussion](https://github.com/aurora-project/aurora/discussions)
- **Bug Reports**: File an [Issue](https://github.com/aurora-project/aurora/issues)
- **Contributing**: See [CONTRIBUTING.md](../../CONTRIBUTING.md)

## License

MIT License - see [LICENSE](../../LICENSE) for details.

## Related Packages

- **aurora-core** - Core storage and chunk types
- **aurora-cli** - Command-line interface
- **aurora-soar** - Agent orchestration
- **aurora-reasoning** - LLM integration

## Acknowledgments

Built with:
- [Click](https://click.palletsprojects.com/) - Command-line interface
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal output
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine

---

**Aurora Planning System** - Part of the Aurora Cognitive Architecture Project
