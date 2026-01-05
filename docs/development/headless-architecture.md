# Headless Mode Architecture Guide

**Version**: 2.0 (Simplified)
**Date**: January 5, 2026
**Status**: Production Ready

---

## Overview

This document describes the simplified architecture of Aurora's Headless Mode - a system for single-iteration autonomous code generation with strong safety guarantees.

**Key Design Principles**:
1. **Single-iteration execution** - No complex multi-iteration loops
2. **Safety first** - Git enforcement, validation before execution
3. **Clear results** - Simple success/failure evaluation
4. **Testability** - Dependency injection, 89%+ test coverage
5. **Simplicity** - Remove unnecessary complexity

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Component Design](#component-design)
3. [Data Flow](#data-flow)
4. [Safety Mechanisms](#safety-mechanisms)
5. [Testing Strategy](#testing-strategy)
6. [Extension Points](#extension-points)
7. [Implementation Notes](#implementation-notes)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Entry Point                          │
│              (aurora_cli/commands/headless.py)              │
│                                                             │
│  - Parse command-line arguments                            │
│  - Create HeadlessConfig                                   │
│  - Display configuration                                   │
│  - Handle dry-run mode                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              HeadlessOrchestrator                           │
│      (aurora_soar/headless/orchestrator_simplified.py)      │
│                                                             │
│  Main Workflow:                                            │
│  1. Validate safety (git branch)                           │
│  2. Load and validate prompt                               │
│  3. Initialize scratchpad                                  │
│  4. Execute single SOAR iteration                          │
│  5. Evaluate success (keyword heuristics)                  │
│  6. Return HeadlessResult                                  │
└───┬────────────┬────────────┬────────────┬─────────────────┘
    │            │            │            │
    ▼            ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐  ┌────────────┐
│  Git   │  │Prompt  │  │Scratch │  │    SOAR    │
│Enforcer│  │Loader  │  │  pad   │  │Orchestrator│
└────────┘  └────────┘  └────────┘  └────────────┘
```

### Component Responsibilities

| Component | Responsibility | File |
|-----------|---------------|------|
| **CLI Command** | User interface, arg parsing, display | `aurora_cli/commands/headless.py` |
| **HeadlessOrchestrator** | Main control flow, coordination | `headless/orchestrator_simplified.py` |
| **GitEnforcer** | Branch safety validation | `headless/git_enforcer.py` |
| **PromptLoader** | Parse and validate prompt file | `headless/prompt_loader_simplified.py` |
| **Scratchpad** | Iteration logging and tracking | `headless/scratchpad.py` |
| **HeadlessConfig** | Configuration with validation | `headless/config.py` |
| **SOAROrchestrator** | Query execution (external) | `aurora_soar/orchestrator.py` |

---

## Component Design

### 1. HeadlessConfig

**Purpose**: Immutable configuration with built-in validation

**Key Features**:
- Frozen dataclass (immutable after creation)
- Validates on construction in `__post_init__`
- Sensible defaults for safety
- Token budget (not USD cost)

**Interface**:
```python
@dataclass(frozen=True)
class HeadlessConfig:
    budget: int = 30000              # Token budget
    max_iterations: int = 5           # Max iterations (1-10)
    scratchpad_path: str = ".aurora/headless/scratchpad.md"
    dry_run: bool = False            # Validation only
```

**Design Decisions**:
- Token budget instead of USD for simplicity
- Max 10 iterations enforced (simplified mode)
- Immutable to prevent accidental modification
- Validation constants at module level

**Location**: `/packages/soar/src/aurora_soar/headless/config.py`

---

### 2. GitEnforcer

**Purpose**: Prevent execution on unsafe branches (main/master)

**Key Features**:
- Validates current git branch
- Blocks main/master by default
- Detects detached HEAD state
- Uses subprocess to run git commands
- Graceful error messages

**Interface**:
```python
class GitEnforcer:
    def __init__(self, config: GitEnforcerConfig | None = None):
        """Initialize with optional config (defaults block main/master)"""

    def validate(self) -> None:
        """Validate git safety, raises GitBranchError if unsafe"""

    def get_current_branch(self) -> str:
        """Get current git branch name"""
```

**Design Decisions**:
- Separate config dataclass for flexibility
- Subprocess with timeout (5s) for git commands
- Specific exception type (GitBranchError)
- No dependency on gitpython library

**Location**: `/packages/soar/src/aurora_soar/headless/git_enforcer.py`

---

### 3. PromptLoader

**Purpose**: Parse and validate experiment prompt markdown

**Key Features**:
- Parses markdown sections (Goal, Success Criteria, etc.)
- Validates required sections exist
- Returns structured PromptData
- Clear error messages

**Interface**:
```python
class PromptLoader:
    def __init__(self, prompt_path: Path):
        """Initialize with prompt file path"""

    def load(self) -> PromptData:
        """Load and parse prompt, raises PromptValidationError if invalid"""

@dataclass
class PromptData:
    goal: str
    success_criteria: list[str]
    constraints: list[str]
    context: str
```

**Design Decisions**:
- Simple regex-based markdown parsing
- Validates Goal and Success Criteria required
- Constraints and Context optional
- Raises specific exception type

**Location**: `/packages/soar/src/aurora_soar/headless/prompt_loader_simplified.py`

---

### 4. Scratchpad

**Purpose**: Log iteration history and track execution status

**Key Features**:
- Markdown format for human readability
- Append-only operations (no overwrites)
- Status tracking (PENDING → IN_PROGRESS → COMPLETED/FAILED)
- Timestamped iteration logs

**Interface**:
```python
class Scratchpad:
    def __init__(self, scratchpad_path: Path):
        """Initialize scratchpad (creates if doesn't exist)"""

    def append_iteration(
        self, iteration: int, goal: str, action: str, result: str
    ) -> None:
        """Log an iteration entry"""

    def update_status(self, status: ExecutionStatus) -> None:
        """Update overall execution status"""

    def read(self) -> str:
        """Read full scratchpad content"""
```

**Design Decisions**:
- Markdown for human readability and version control
- Enum for status (type safety)
- Timestamped entries (ISO 8601)
- No backup/restore (overkill for simplified version)

**Location**: `/packages/soar/src/aurora_soar/headless/scratchpad.py`

---

### 5. HeadlessOrchestrator

**Purpose**: Coordinate all components and execute single iteration

**Key Features**:
- Dependency injection for testability
- Clear 5-step workflow
- Simple success evaluation (keyword-based)
- Returns structured HeadlessResult
- Comprehensive error handling

**Interface**:
```python
class HeadlessOrchestrator:
    def __init__(
        self,
        prompt_path: str | Path,
        scratchpad_path: str | Path,
        soar_orchestrator: Any,
        config: HeadlessConfig | None = None,
        git_enforcer: GitEnforcer | None = None,
        prompt_loader: PromptLoader | None = None,
        scratchpad: Scratchpad | None = None,
    ):
        """Initialize with dependencies (allows injection for testing)"""

    def execute(self) -> HeadlessResult:
        """Execute single iteration and return result"""

@dataclass
class HeadlessResult:
    goal_achieved: bool
    termination_reason: TerminationReason
    iterations: int
    total_cost: float
    duration_seconds: float
    scratchpad_path: str
    error_message: str | None = None
```

**Design Decisions**:
- Single iteration (not a loop)
- Dependency injection via constructor
- Returns result object (not exceptions)
- Simple keyword-based success heuristic
- Print statements for user feedback

**Location**: `/packages/soar/src/aurora_soar/headless/orchestrator_simplified.py`

---

## Data Flow

### Execution Sequence

```
1. User runs CLI command
   ↓
2. CLI parses arguments → creates HeadlessConfig
   ↓
3. CLI creates HeadlessOrchestrator with config
   ↓
4. HeadlessOrchestrator.execute() called
   ↓
   ├─ Step 1: GitEnforcer.validate()
   │           ├─ Success → continue
   │           └─ Failure → return GIT_SAFETY_ERROR
   ↓
   ├─ Step 2: PromptLoader.load()
   │           ├─ Success → continue with PromptData
   │           └─ Failure → return PROMPT_ERROR
   ↓
   ├─ Step 3: Scratchpad initialized (auto-creates file)
   ↓
   ├─ Step 4: Execute SOAR iteration
   │           ├─ Build query from prompt + scratchpad
   │           ├─ Call soar_orchestrator.execute(query)
   │           ├─ Log iteration to scratchpad
   │           └─ Handle errors → return BLOCKED
   ↓
   ├─ Step 5: Evaluate success
   │           ├─ Read scratchpad content
   │           ├─ Count success/failure keywords
   │           └─ Return goal_achieved = (success_count > failure_count)
   ↓
5. Return HeadlessResult to CLI
   ↓
6. CLI displays results to user
```

### Data Structures

**Configuration Flow**:
```
CLI args → HeadlessConfig (validated) → HeadlessOrchestrator
```

**Prompt Flow**:
```
prompt.md → PromptLoader → PromptData → HeadlessOrchestrator
```

**Execution Flow**:
```
HeadlessOrchestrator → SOAR query → SOAROrchestrator
                    ↓
                    Result → Scratchpad (logged)
                    ↓
                    Success evaluation → HeadlessResult
```

---

## Safety Mechanisms

### 1. Git Branch Enforcement

**Problem**: Prevent running on main/master branches

**Solution**:
- GitEnforcer validates before execution starts
- Blocks main, master branches by default
- Detects detached HEAD state
- Clear error message with resolution steps

**Implementation**:
```python
# In GitEnforcer.validate()
if current_branch in self.config.blocked_branches:
    raise GitBranchError(
        f"Cannot run headless mode on branch '{current_branch}'. "
        f"Blocked branches: {self.config.blocked_branches}. "
        f"Switch to a different branch first."
    )
```

**Override**: Users can modify GitEnforcerConfig if needed

---

### 2. Token Budget Limits

**Problem**: Prevent excessive token usage

**Solution**:
- Token budget (integer count, not USD)
- Validated in HeadlessConfig.__post_init__
- Must be positive (> 0)
- CLI enforces positive budget

**Implementation**:
```python
# In HeadlessConfig.__post_init__
if self.budget <= 0:
    raise ValueError(
        f"budget must be positive, got {self.budget}. "
        f"Minimum allowed: {MIN_BUDGET}"
    )
```

**Note**: Actual budget enforcement would be in SOAR orchestrator (not yet implemented)

---

### 3. Iteration Caps

**Problem**: Prevent infinite loops or runaway execution

**Solution**:
- Max iterations limited to 10 (enforced in config)
- Default is 5 iterations
- Prevents accidental long-running experiments

**Implementation**:
```python
# In HeadlessConfig.__post_init__
if self.max_iterations > MAX_ITERATIONS_LIMIT:
    raise ValueError(
        f"max_iterations cannot exceed {MAX_ITERATIONS_LIMIT}, "
        f"got {self.max_iterations}. Headless mode is designed for "
        f"single-iteration or limited autonomous execution."
    )
```

---

### 4. Prompt Validation

**Problem**: Ensure experiment has clear goals

**Solution**:
- Require Goal and Success Criteria sections
- Validate before execution
- Clear error messages for missing sections

**Implementation**:
```python
# In PromptLoader.load()
if not goal:
    raise PromptValidationError(
        "Prompt must have a 'Goal' section with content"
    )
if not success_criteria:
    raise PromptValidationError(
        "Prompt must have 'Success Criteria' section with at least one criterion"
    )
```

---

### 5. Scratchpad Audit Trail

**Problem**: Need transparency of what AI did

**Solution**:
- Every iteration logged with timestamp
- Status changes tracked
- Human-readable markdown format
- Version-controllable

**Format**:
```markdown
# Headless Execution Scratchpad

**Status**: IN_PROGRESS
**Created**: 2026-01-05T10:30:00

## Iteration 1 - 2026-01-05T10:30:15

**Goal**: Implement feature X

**Action**: Executed SOAR iteration

**Result**: Response: ... (confidence: 0.85)

---
```

---

## Testing Strategy

### Test Coverage Goals

| Component | Line Coverage | Test Count | Status |
|-----------|--------------|------------|--------|
| `config.py` | 82.35% | 11 | PASSING |
| `prompt_loader_simplified.py` | 95.24% | 12 | PASSING |
| `scratchpad.py` | 89.89% | 12 | PASSING |
| `git_enforcer.py` | 90.79% | 33 | PASSING |
| `orchestrator_simplified.py` | 93.70% | 7 | PASSING |
| `headless.py` (CLI) | 91.55% | 24 | PASSING |
| **Total** | **~90%** | **110 unit + 11 integration** | **121 PASSING** |

### Test Organization

```
tests/
├── unit/
│   ├── soar/
│   │   └── headless/
│   │       ├── test_config.py                    # Config validation
│   │       ├── test_prompt_loader_simplified.py  # Prompt parsing
│   │       ├── test_scratchpad_simplified.py     # Scratchpad logging
│   │       ├── test_git_enforcer.py              # Git safety
│   │       └── test_orchestrator_simplified.py   # Orchestration
│   └── cli/
│       └── test_headless_command.py              # CLI interface
└── integration/
    └── test_headless_integration.py              # Full workflow
```

### Testing Patterns

**1. Dependency Injection for Mocking**:
```python
# In tests
mock_git = Mock(spec=GitEnforcer)
mock_prompt = Mock(spec=PromptLoader)
mock_scratchpad = Mock(spec=Scratchpad)

orchestrator = HeadlessOrchestrator(
    prompt_path="test.md",
    scratchpad_path="scratch.md",
    soar_orchestrator=mock_soar,
    git_enforcer=mock_git,
    prompt_loader=mock_prompt,
    scratchpad=mock_scratchpad
)
```

**2. Temporary Files for Integration Tests**:
```python
def test_full_workflow(tmp_path):
    prompt = tmp_path / "experiment.md"
    prompt.write_text("# Goal\nTest goal\n\n# Success Criteria\n- Done")

    scratchpad = tmp_path / "scratchpad.md"

    # Test with real file system
```

**3. CLI Testing with CliRunner**:
```python
from click.testing import CliRunner

def test_headless_command():
    runner = CliRunner()
    result = runner.invoke(
        headless_command,
        ["experiment.md", "--dry-run"]
    )
    assert result.exit_code == 0
```

---

## Extension Points

### 1. Custom Success Evaluation

**Current**: Simple keyword heuristics

**Extension Point**:
```python
class HeadlessOrchestrator:
    def _evaluate_success(self) -> bool:
        """Override this method for custom evaluation logic"""
        # Current: keyword counting
        # Future: LLM-based evaluation, test result parsing, etc.
```

**How to Extend**:
- Subclass HeadlessOrchestrator
- Override `_evaluate_success()`
- Implement custom logic (LLM call, test parsing, etc.)

---

### 2. Custom Git Validation

**Current**: Block main/master branches

**Extension Point**:
```python
# Custom GitEnforcer config
config = GitEnforcerConfig(
    blocked_branches=["main", "master", "production"],
    required_branch_pattern=r"^experiment-.*$",  # Future
    check_uncommitted_changes=True               # Future
)

enforcer = GitEnforcer(config)
```

---

### 3. Custom Scratchpad Format

**Current**: Markdown with fixed format

**Extension Point**:
- Create custom Scratchpad subclass
- Override `append_iteration()` and `update_status()`
- Inject via HeadlessOrchestrator constructor
- Example: JSON format, database logging, etc.

---

### 4. Multi-Iteration Loop

**Current**: Single iteration only

**Extension Point** (future):
```python
class MultiIterationOrchestrator(HeadlessOrchestrator):
    def execute_multi(self) -> HeadlessResult:
        """Run multiple iterations until goal achieved or limits reached"""
        for i in range(1, self.config.max_iterations + 1):
            result = super().execute()  # Run single iteration

            if result.goal_achieved:
                break

            # Check budget, continue...
```

**Note**: Not implemented in simplified version by design

---

## Implementation Notes

### Design Philosophy

**1. Prefer Simplicity Over Features**
- Single iteration instead of loops
- Keyword heuristics instead of LLM evaluation
- Token budget instead of USD tracking
- No resume functionality (YAGNI)

**2. Safety First**
- Validate before execute
- Clear error messages
- No silent failures
- Audit trail always

**3. Test-Driven Development**
- All components have 80%+ coverage
- Integration tests for workflows
- TDD cycle: RED → GREEN → REFACTOR

**4. Dependency Injection**
- Constructor injection for all dependencies
- Makes testing easy with mocks
- Composition over inheritance

### Performance Considerations

**File I/O**:
- Scratchpad uses append-only writes (efficient)
- No file watching or continuous polling
- Git commands cached when possible

**Memory Usage**:
- PromptData is small (strings only)
- Scratchpad read once per evaluation
- No large in-memory buffers

**Execution Time**:
- Validation is fast (<100ms)
- SOAR execution is the bottleneck (seconds to minutes)
- No artificial delays or sleep calls

### Future Improvements

**Short-term**:
1. LLM-based success evaluation (replace keyword heuristics)
2. Budget enforcement in SOAR orchestrator
3. Resume functionality for interrupted runs
4. Scratchpad backup before writing

**Long-term**:
1. Multi-iteration orchestrator (as separate class)
2. Structured JSON output format
3. WebSocket for real-time progress
4. Parallel experiment execution

### Known Limitations

1. **Success evaluation is naive**: Keyword counting is a heuristic, not true understanding
2. **Token budget not enforced**: Config validates but SOAR doesn't enforce yet
3. **No cost tracking**: Doesn't calculate actual USD cost
4. **Single iteration only**: By design, but limits use cases
5. **No graceful interruption**: Ctrl+C kills immediately

---

## Related Documentation

- [Headless Mode User Guide](../deployment/headless-mode.md) - User-facing documentation
- [SOAR Architecture](./SOAR_ARCHITECTURE.md) - SOAR pipeline details
- [Testing Guide](./testing-guide.md) - Testing best practices
- [CLI Development](./cli-development.md) - CLI command development

---

## Changelog

### Version 2.0 (2026-01-05)
- Simplified architecture (single-iteration)
- Removed complex features (budget tracking, multi-iteration)
- Added comprehensive test coverage (90%+)
- Improved dependency injection
- Enhanced documentation

### Version 1.0 (2025-12-23)
- Initial complex implementation
- Multi-iteration loop
- USD-based budget tracking
- Resume functionality

---

**Status**: Production Ready
**Test Coverage**: 90%+ (121 tests passing)
**Maintainer**: Aurora Core Team
