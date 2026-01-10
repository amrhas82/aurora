# Aurora Planning - API Reference

**Complete API documentation for aurora_planning package**

Version: 0.1.0 | Last Updated: 2026-01-03

---

## Table of Contents

- [Overview](#overview)
- [Core Modules](#core-modules)
  - [planning_config](#planning_config)
  - [id_generator](#id_generator)
  - [renderer](#renderer)
  - [archive_utils](#archive_utils)
- [Commands](#commands)
- [Schemas](#schemas)
- [Validators](#validators)
- [Parsers](#parsers)
- [Utilities](#utilities)

---

## Overview

The `aurora_planning` package provides structured plan creation and management functionality. All modules follow these conventions:

- **Return Types**: Functions return `Result` objects for graceful error handling
- **Type Hints**: Full type annotations on all public functions
- **Docstrings**: Google-style docstrings with examples
- **Validation**: Pydantic models for all data structures

### Installation

```python
# Import the package
from aurora_planning import (
    planning_config,
    id_generator,
    renderer,
    archive_utils,
)
```

---

## Core Modules

### planning_config

Configuration management with environment variable overrides.

#### Functions

##### `get_plans_dir()`

Get the base directory for plans with environment variable override support.

```python
def get_plans_dir() -> Path:
    """Get the base directory for plans.

    Returns:
        Path: Absolute path to plans directory (default: ~/.aurora/plans)

    Environment Variables:
        AURORA_PLANS_DIR: Override default plans directory

    Examples:
        >>> from aurora_planning.planning_config import get_plans_dir
        >>> plans_dir = get_plans_dir()
        >>> print(plans_dir)
        /home/user/.aurora/plans

        >>> import os
        >>> os.environ['AURORA_PLANS_DIR'] = '/custom/plans'
        >>> print(get_plans_dir())
        /custom/plans
    """
```

**Returns:**
- `Path` - Absolute path to plans directory

**Environment Variables:**
- `AURORA_PLANS_DIR` - Override default directory

**Default:** `~/.aurora/plans`

---

##### `get_template_dir()`

Get the directory containing Jinja2 templates.

```python
def get_template_dir() -> Path:
    """Get the directory containing Jinja2 templates.

    Returns:
        Path: Absolute path to templates directory

    Environment Variables:
        AURORA_TEMPLATE_DIR: Override default template directory

    Examples:
        >>> from aurora_planning.planning_config import get_template_dir
        >>> template_dir = get_template_dir()
        >>> print(template_dir)
        /path/to/aurora_planning/templates
    """
```

**Returns:**
- `Path` - Absolute path to templates directory (package default)

**Environment Variables:**
- `AURORA_TEMPLATE_DIR` - Override default directory

**Default:** `<package>/templates`

---

##### `validate_plans_dir()`

Validate that plans directory exists and is writable.

```python
def validate_plans_dir(plans_dir: Path) -> tuple[bool, str]:
    """Validate that plans directory exists and is writable.

    Args:
        plans_dir: Path to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if directory exists and is writable
        - error_message: Empty string if valid, error description otherwise

    Examples:
        >>> from pathlib import Path
        >>> from aurora_planning.planning_config import validate_plans_dir
        >>> is_valid, error = validate_plans_dir(Path("/tmp/plans"))
        >>> if not is_valid:
        ...     print(f"Error: {error}")
        Error: Directory does not exist: /tmp/plans
    """
```

**Parameters:**
- `plans_dir` (Path) - Path to validate

**Returns:**
- `tuple[bool, str]` - (is_valid, error_message)

**Validation Checks:**
1. Directory exists
2. Path is a directory (not a file)
3. Directory is writable by current user

---

### id_generator

Auto-incrementing plan ID generation with collision handling.

#### Functions

##### `generate_plan_id()`

Generate a unique plan ID with auto-increment and slug.

```python
def generate_plan_id(
    goal: str,
    plans_dir: Path | None = None,
    max_retries: int = 10
) -> str:
    """Generate a unique plan ID from goal text.

    Format: NNNN-slug
    - NNNN: Zero-padded 4-digit number (auto-incremented)
    - slug: URL-safe slug from goal text (max 30 chars)

    Args:
        goal: Goal text to generate slug from
        plans_dir: Base directory for plans (default: from config)
        max_retries: Maximum collision retry attempts (default: 10)

    Returns:
        Plan ID string (e.g., "0001-oauth2-authentication")

    Raises:
        ValueError: If max_retries exceeded or goal is empty

    Examples:
        >>> from aurora_planning.id_generator import generate_plan_id
        >>> plan_id = generate_plan_id("Implement OAuth2 authentication")
        >>> print(plan_id)
        0001-oauth2-authentication

        >>> # With custom plans directory
        >>> from pathlib import Path
        >>> plan_id = generate_plan_id(
        ...     "Add caching layer",
        ...     plans_dir=Path("/custom/plans")
        ... )
        >>> print(plan_id)
        0002-add-caching-layer
    """
```

**Parameters:**
- `goal` (str) - Goal text to generate slug from
- `plans_dir` (Path | None) - Base directory for plans
- `max_retries` (int) - Maximum collision retry attempts

**Returns:**
- `str` - Plan ID in format `NNNN-slug`

**Raises:**
- `ValueError` - If max_retries exceeded or goal is empty

**Algorithm:**
1. Scan both `active/` and `archive/` directories
2. Extract all existing numeric IDs
3. Find highest ID and increment
4. Generate slug from goal text (pythonized)
5. Check for collisions, retry if needed

---

##### `extract_plan_number()`

Extract numeric ID from plan directory name.

```python
def extract_plan_number(dirname: str) -> int | None:
    """Extract numeric plan ID from directory name.

    Supports two formats:
    - Active: "0001-oauth-auth"
    - Archived: "2026-01-15-0001-oauth-auth"

    Args:
        dirname: Directory name to parse

    Returns:
        Numeric ID as integer, or None if not found

    Examples:
        >>> from aurora_planning.id_generator import extract_plan_number
        >>> extract_plan_number("0001-oauth-auth")
        1
        >>> extract_plan_number("2026-01-15-0042-user-system")
        42
        >>> extract_plan_number("invalid-name")
        None
    """
```

**Parameters:**
- `dirname` (str) - Directory name to parse

**Returns:**
- `int | None` - Numeric ID or None if not found

**Supported Formats:**
- Active plans: `NNNN-slug`
- Archived plans: `YYYY-MM-DD-NNNN-slug`

---

### renderer

Template rendering engine for plan file generation.

#### Functions

##### `render_plan_files()`

Render all 8 plan files from Jinja2 templates.

```python
def render_plan_files(
    plan_id: str,
    goal: str,
    subgoals: list[dict[str, Any]],
    output_dir: Path,
    template_dir: Path | None = None
) -> dict[str, Path]:
    """Render all plan files from templates.

    Generates 8 files:
    - 4 base files: plan.md, prd.md, tasks.md, agents.json
    - 4 capability specs: planning, commands, validation, schemas

    Args:
        plan_id: Plan ID (e.g., "0001-oauth-auth")
        goal: Goal description
        subgoals: List of subgoal dictionaries
        output_dir: Directory to write files
        template_dir: Template directory (default: from config)

    Returns:
        Dictionary mapping file type to file path

    Raises:
        FileNotFoundError: If template files not found
        PermissionError: If output directory not writable

    Examples:
        >>> from pathlib import Path
        >>> from aurora_planning.renderer import render_plan_files
        >>>
        >>> subgoals = [
        ...     {
        ...         "id": "sg-1",
        ...         "title": "Design OAuth flow",
        ...         "agent_id": "@architect",
        ...         "status": "pending"
        ...     }
        ... ]
        >>>
        >>> files = render_plan_files(
        ...     plan_id="0001-oauth-auth",
        ...     goal="Implement OAuth2 authentication",
        ...     subgoals=subgoals,
        ...     output_dir=Path(".aurora/plans/active/0001-oauth-auth")
        ... )
        >>>
        >>> print(files.keys())
        dict_keys(['plan', 'prd', 'tasks', 'agents',
                   'planning', 'commands', 'validation', 'schemas'])
    """
```

**Parameters:**
- `plan_id` (str) - Plan identifier
- `goal` (str) - Goal description
- `subgoals` (list[dict]) - List of subgoal dictionaries
- `output_dir` (Path) - Output directory
- `template_dir` (Path | None) - Template directory override

**Returns:**
- `dict[str, Path]` - Mapping of file type to generated file path

**Generated Files:**
1. `plan.md` - Plan overview
2. `prd.md` - Product requirements
3. `tasks.md` - Task checklist
4. `agents.json` - Metadata
5. `specs/planning/*.md` - Planning spec
6. `specs/commands/*.md` - Commands spec
7. `specs/validation/*.md` - Validation spec
8. `specs/schemas/*.md` - Schemas spec

---

##### `build_context()`

Build Jinja2 template context from plan data.

```python
def build_context(
    plan_id: str,
    goal: str,
    subgoals: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build template context dictionary.

    Creates context with all variables needed for rendering:
    - Basic: plan_id, goal, created_at
    - Derived: plan_name (slug), subgoal_count
    - Collections: subgoals list

    Args:
        plan_id: Plan identifier
        goal: Goal description
        subgoals: List of subgoal dictionaries

    Returns:
        Context dictionary for Jinja2 rendering

    Examples:
        >>> from aurora_planning.renderer import build_context
        >>> context = build_context(
        ...     plan_id="0001-oauth-auth",
        ...     goal="Implement OAuth2",
        ...     subgoals=[{"id": "sg-1", "title": "Design flow"}]
        ... )
        >>> print(context['plan_name'])
        oauth-auth
        >>> print(context['subgoal_count'])
        1
    """
```

**Parameters:**
- `plan_id` (str) - Plan identifier
- `goal` (str) - Goal description
- `subgoals` (list[dict]) - Subgoals list

**Returns:**
- `dict[str, Any]` - Template context dictionary

**Context Variables:**
- `plan_id` - Plan identifier
- `plan_name` - Slug portion of plan_id
- `goal` - Goal description
- `created_at` - ISO 8601 timestamp
- `subgoals` - Subgoals list
- `subgoal_count` - Number of subgoals

---

### archive_utils

Atomic archive operations with rollback support.

#### Functions

##### `archive_plan_atomic()`

Archive a plan with atomic file operations.

```python
def archive_plan_atomic(
    plan_id: str,
    plans_dir: Path | None = None,
    force: bool = False
) -> tuple[bool, Path | None, str]:
    """Archive a plan atomically.

    Moves plan from active/ to archive/ with timestamp prefix.
    Updates agents.json with archived status and timestamp.

    Format: YYYY-MM-DD-NNNN-slug

    Args:
        plan_id: Plan ID to archive (full or partial)
        plans_dir: Base plans directory (default: from config)
        force: Skip confirmation prompts (default: False)

    Returns:
        Tuple of (success, archive_path, message)

    Raises:
        FileNotFoundError: If plan not found
        PermissionError: If insufficient permissions

    Examples:
        >>> from aurora_planning.archive_utils import archive_plan_atomic
        >>> success, path, msg = archive_plan_atomic("0001-oauth-auth")
        >>> if success:
        ...     print(f"Archived to: {path}")
        Archived to: .aurora/plans/archive/2026-01-15-0001-oauth-auth

        >>> # Force archive without confirmation
        >>> success, path, msg = archive_plan_atomic("0002", force=True)
    """
```

**Parameters:**
- `plan_id` (str) - Plan ID (full or partial)
- `plans_dir` (Path | None) - Base plans directory
- `force` (bool) - Skip confirmation prompts

**Returns:**
- `tuple[bool, Path | None, str]` - (success, archive_path, message)

**Archive Process:**
1. Validate plan exists in active/
2. Create temp copy in `.tmp/`
3. Update agents.json with archived status
4. Atomic move to archive/ with timestamp
5. Remove original from active/
6. Rollback on any error

**Error Handling:**
- Automatic rollback if any step fails
- Preserves original plan in active/ on error
- Returns descriptive error messages

---

##### `generate_archive_name()`

Generate timestamped archive directory name.

```python
def generate_archive_name(plan_id: str) -> str:
    """Generate archive directory name with timestamp.

    Format: YYYY-MM-DD-NNNN-slug
    Uses current date (not plan creation date).

    Args:
        plan_id: Original plan ID

    Returns:
        Archive directory name

    Examples:
        >>> from aurora_planning.archive_utils import generate_archive_name
        >>> name = generate_archive_name("0001-oauth-auth")
        >>> print(name)  # Assuming today is 2026-01-15
        2026-01-15-0001-oauth-auth
    """
```

**Parameters:**
- `plan_id` (str) - Original plan ID

**Returns:**
- `str` - Archive directory name with timestamp prefix

**Format:** `YYYY-MM-DD-NNNN-slug`

---

## Commands

Commands are implemented in `aurora_planning.commands` but typically invoked via CLI.

### Command Module Structure

```
aurora_planning.commands/
├── init.py         # Initialize planning directory
├── list.py         # List active/archived plans
├── view.py         # View plan details
├── archive.py      # Archive completed plans
└── update.py       # Update plan metadata
```

Each command module exports a main function that can be called programmatically:

```python
from aurora_planning.commands.list import list_plans

plans = list_plans(plans_dir=Path(".aurora/plans"), archived=False)
for plan in plans:
    print(f"{plan['plan_id']}: {plan['goal']}")
```

---

## Schemas

Pydantic models for data validation.

### Plan

Main plan data model.

```python
from pydantic import BaseModel, Field
from datetime import datetime

class Plan(BaseModel):
    """Plan data model.

    Attributes:
        plan_id: Unique plan identifier (NNNN-slug format)
        goal: Goal description (10-500 chars)
        status: Plan status (pending, in_progress, complete, archived)
        created_at: Creation timestamp (ISO 8601)
        archived_at: Archive timestamp (optional, ISO 8601)
        subgoals: List of subgoals

    Examples:
        >>> from aurora_planning.schemas.plan import Plan, Subgoal
        >>>
        >>> plan = Plan(
        ...     plan_id="0001-oauth-auth",
        ...     goal="Implement OAuth2 authentication",
        ...     status="pending",
        ...     created_at=datetime.now(),
        ...     subgoals=[
        ...         Subgoal(
        ...             id="sg-1",
        ...             title="Design flow",
        ...             agent_id="@architect",
        ...             status="pending"
        ...         )
        ...     ]
        ... )
        >>>
        >>> # Validate from JSON
        >>> plan_json = plan.model_dump_json()
        >>> loaded = Plan.model_validate_json(plan_json)
    """

    plan_id: str = Field(pattern=r'^\d{4}-[a-z0-9-]+$')
    goal: str = Field(min_length=10, max_length=500)
    status: str = Field(pattern=r'^(pending|in_progress|complete|archived)$')
    created_at: datetime
    archived_at: datetime | None = None
    subgoals: list[Subgoal] = []
```

**Validators:**
- `plan_id` - Must match `NNNN-slug` format
- `goal` - 10-500 characters
- `status` - Must be valid status value
- `created_at` - Valid ISO 8601 datetime
- `subgoals` - List of valid Subgoal objects

---

### Subgoal

Subgoal data model.

```python
class Subgoal(BaseModel):
    """Subgoal data model.

    Attributes:
        id: Subgoal identifier (sg-N format)
        title: Subgoal title (3-200 chars)
        description: Detailed description (optional)
        agent_id: Assigned agent ID (@agent-name format)
        status: Subgoal status
        dependencies: List of subgoal IDs this depends on

    Examples:
        >>> from aurora_planning.schemas.plan import Subgoal
        >>>
        >>> subgoal = Subgoal(
        ...     id="sg-1",
        ...     title="Design OAuth2 flow",
        ...     description="Design authorization and token exchange",
        ...     agent_id="@architect",
        ...     status="pending",
        ...     dependencies=[]
        ... )
        >>>
        >>> # With dependencies
        >>> subgoal2 = Subgoal(
        ...     id="sg-2",
        ...     title="Implement endpoints",
        ...     agent_id="@backend-dev",
        ...     status="pending",
        ...     dependencies=["sg-1"]  # Depends on sg-1
        ... )
    """

    id: str = Field(pattern=r'^sg-\d+$')
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    agent_id: str = Field(pattern=r'^@[a-z0-9-]+$')
    status: str = Field(pattern=r'^(pending|in_progress|complete)$')
    dependencies: list[str] = []
```

**Validators:**
- `id` - Must match `sg-N` format
- `title` - 3-200 characters
- `agent_id` - Must match `@agent-name` format
- `status` - Must be valid status value
- `dependencies` - List of valid subgoal IDs

**Dependency Validation:**
- Circular dependencies detected and rejected
- Invalid dependency IDs rejected
- Self-dependencies rejected

---

## Validators

### validate_plan_structure()

Validate plan directory structure and files.

```python
def validate_plan_structure(plan_dir: Path) -> tuple[bool, list[str], list[str]]:
    """Validate plan directory structure.

    Checks:
    - Required files exist (plan.md, prd.md, tasks.md, agents.json)
    - Optional files (capability specs)
    - agents.json schema validity
    - Plan ID matches directory name

    Args:
        plan_dir: Path to plan directory

    Returns:
        Tuple of (is_valid, errors, warnings)
        - is_valid: True if all required files present and valid
        - errors: List of error messages (block operations)
        - warnings: List of warning messages (informational)

    Examples:
        >>> from pathlib import Path
        >>> from aurora_planning.validators import validate_plan_structure
        >>>
        >>> plan_dir = Path(".aurora/plans/active/0001-oauth-auth")
        >>> is_valid, errors, warnings = validate_plan_structure(plan_dir)
        >>>
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(f"ERROR: {error}")
        >>>
        >>> for warning in warnings:
        ...     print(f"WARNING: {warning}")
    """
```

**Parameters:**
- `plan_dir` (Path) - Plan directory to validate

**Returns:**
- `tuple[bool, list[str], list[str]]` - (is_valid, errors, warnings)

**Validation Rules:**

**Required Files (errors if missing):**
- `plan.md` - Plan overview
- `prd.md` - Requirements document
- `tasks.md` - Task checklist
- `agents.json` - Metadata file

**Optional Files (warnings if missing):**
- `specs/planning/*.md`
- `specs/commands/*.md`
- `specs/validation/*.md`
- `specs/schemas/*.md`

**agents.json Validation:**
- Valid JSON syntax
- Conforms to JSON Schema
- Pydantic model validation passes

---

## Parsers

### parse_tasks()

Parse GFM task checkboxes from tasks.md.

```python
def parse_tasks(tasks_file: Path) -> dict[str, Any]:
    """Parse task checklist from tasks.md.

    Extracts:
    - Total task count
    - Completed task count
    - Progress percentage
    - Task hierarchy

    Args:
        tasks_file: Path to tasks.md file

    Returns:
        Dictionary with task statistics and parsed structure

    Examples:
        >>> from pathlib import Path
        >>> from aurora_planning.parsers.markdown import parse_tasks
        >>>
        >>> tasks = parse_tasks(Path("tasks.md"))
        >>> print(f"Progress: {tasks['completed']}/{tasks['total']}")
        Progress: 12/24
        >>> print(f"Percentage: {tasks['percentage']}%")
        Percentage: 50%
    """
```

**Parameters:**
- `tasks_file` (Path) - Path to tasks.md

**Returns:**
- `dict[str, Any]` - Task statistics and structure

**Return Dictionary Keys:**
- `total` (int) - Total task count
- `completed` (int) - Completed task count
- `percentage` (float) - Completion percentage
- `tasks` (list) - Parsed task hierarchy

---

## Utilities

### Filesystem Utilities

Helper functions for file operations.

```python
from aurora_planning.utils.filesystem import (
    atomic_write,
    safe_delete,
    ensure_directory,
)

# Atomic file write with rollback
atomic_write(
    file_path=Path("data.json"),
    content='{"key": "value"}',
    mode=0o644
)

# Safe delete with confirmation
safe_delete(
    path=Path("old-plan/"),
    recursive=True,
    confirm=True
)

# Ensure directory exists with permissions
ensure_directory(
    path=Path(".aurora/plans/active"),
    mode=0o755
)
```

### Interactive Utilities

Terminal interaction helpers.

```python
from aurora_planning.utils.interactive import (
    confirm,
    select_one,
    select_many,
)

# Simple yes/no confirmation
if confirm("Archive this plan?", default=False):
    # Archive the plan
    pass

# Select one option
tool = select_one(
    "Select tool:",
    choices=["Claude Code", "OpenCode", "AmpCode"],
    default="Claude Code"
)

# Select multiple options
tools = select_many(
    "Select tools to configure:",
    choices=["Claude Code", "OpenCode", "AmpCode", "Droid"],
    defaults=["Claude Code"]
)
```

---

## Type Definitions

### Common Type Aliases

```python
from typing import TypeAlias
from pathlib import Path

# Plan ID type (validated format)
PlanID: TypeAlias = str  # Format: NNNN-slug

# Subgoal ID type
SubgoalID: TypeAlias = str  # Format: sg-N

# Agent ID type
AgentID: TypeAlias = str  # Format: @agent-name

# Status type
PlanStatus: TypeAlias = str  # pending | in_progress | complete | archived
SubgoalStatus: TypeAlias = str  # pending | in_progress | complete

# Result tuple for validation functions
ValidationResult: TypeAlias = tuple[bool, list[str], list[str]]
# (is_valid, errors, warnings)

# Archive result tuple
ArchiveResult: TypeAlias = tuple[bool, Path | None, str]
# (success, archive_path, message)
```

---

## Error Handling

### Exception Hierarchy

```python
class PlanningError(Exception):
    """Base exception for aurora_planning errors."""
    pass

class PlanNotFoundError(PlanningError):
    """Plan ID not found in active or archive."""
    pass

class ValidationError(PlanningError):
    """Plan validation failed."""
    pass

class TemplateError(PlanningError):
    """Template rendering failed."""
    pass

class ArchiveError(PlanningError):
    """Archive operation failed."""
    pass
```

### Error Codes

See [Error Code Reference](error-codes.md) for complete list.

| Code | Description |
|------|-------------|
| E001 | Planning directory not initialized |
| E002 | Plan not found |
| E003 | Invalid plan ID format |
| E004 | Template rendering failed |
| E005 | Validation failed |
| E006 | Archive operation failed |

---

## Examples

### Example 1: Programmatic Plan Creation

```python
from pathlib import Path
from aurora_planning import (
    id_generator,
    renderer,
    planning_config,
)

# Generate plan ID
plan_id = id_generator.generate_plan_id(
    goal="Implement OAuth2 authentication"
)
print(f"Generated ID: {plan_id}")  # 0001-oauth2-authentication

# Prepare plan data
subgoals = [
    {
        "id": "sg-1",
        "title": "Design OAuth2 flow",
        "agent_id": "@architect",
        "status": "pending",
        "dependencies": []
    },
    {
        "id": "sg-2",
        "title": "Implement token endpoints",
        "agent_id": "@backend-dev",
        "status": "pending",
        "dependencies": ["sg-1"]
    }
]

# Render files
plans_dir = planning_config.get_plans_dir()
output_dir = plans_dir / "active" / plan_id
output_dir.mkdir(parents=True, exist_ok=True)

files = renderer.render_plan_files(
    plan_id=plan_id,
    goal="Implement OAuth2 authentication",
    subgoals=subgoals,
    output_dir=output_dir
)

print(f"Created {len(files)} files:")
for file_type, file_path in files.items():
    print(f"  - {file_type}: {file_path}")
```

### Example 2: List and Filter Plans

```python
from pathlib import Path
from aurora_planning.commands.list import list_plans
from aurora_planning.parsers.markdown import parse_tasks

# List all active plans
plans = list_plans(
    plans_dir=Path(".aurora/plans"),
    archived=False
)

# Filter by completion status
incomplete_plans = [
    p for p in plans
    if p['progress']['percentage'] < 100
]

print(f"Found {len(incomplete_plans)} incomplete plans:")
for plan in incomplete_plans:
    print(f"  {plan['plan_id']}: {plan['progress']['completed']}/{plan['progress']['total']} tasks")
```

### Example 3: Archive with Validation

```python
from pathlib import Path
from aurora_planning.archive_utils import archive_plan_atomic
from aurora_planning.validators import validate_plan_structure

plan_id = "0001-oauth-auth"
plans_dir = Path(".aurora/plans")
plan_dir = plans_dir / "active" / plan_id

# Validate before archiving
is_valid, errors, warnings = validate_plan_structure(plan_dir)

if not is_valid:
    print("Cannot archive: Plan has errors")
    for error in errors:
        print(f"  ERROR: {error}")
else:
    # Archive the plan
    success, archive_path, message = archive_plan_atomic(
        plan_id=plan_id,
        plans_dir=plans_dir,
        force=True
    )

    if success:
        print(f"Archived to: {archive_path}")
    else:
        print(f"Archive failed: {message}")
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/unit/planning/

# Run with coverage
pytest --cov=aurora_planning tests/unit/planning/

# Run specific test module
pytest tests/unit/planning/test_id_generator.py -v
```

### Test Utilities

```python
from aurora_planning.testing import (
    create_test_plan,
    create_test_config,
    temp_plans_dir,
)

# Create temporary test plan
with temp_plans_dir() as plans_dir:
    plan_id = create_test_plan(
        plans_dir=plans_dir,
        goal="Test OAuth implementation",
        subgoals=2
    )

    # Test operations
    assert (plans_dir / "active" / plan_id).exists()
```

---

## Resources

### Related Documentation

- [User Guide](user-guide.md) - Comprehensive workflow guide
- [Command Cheat Sheet](cheat-sheet.md) - Quick command reference
- [Package README](../../packages/planning/README.md) - Package overview

### External Resources

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Click Documentation](https://click.palletsprojects.com/)

---

**Aurora Planning API Reference** - Version 0.1.0
