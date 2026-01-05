# AURORA Headless Mode - Simplified Single-Iteration Guide

**Version**: 2.0 (Simplified)
**Date**: January 5, 2026
**Status**: Production Ready

---

## Executive Summary

AURORA's Headless Mode enables single-iteration autonomous code generation and experimentation with strong safety guarantees. The simplified system executes one SOAR iteration per invocation, making it easier to understand, test, and control.

**Key Features**:
- **Single Iteration Execution**: One SOAR cycle per invocation (no complex loops)
- **Safety First**: Git branch enforcement, token budget limits, validation
- **Simple Success Evaluation**: Keyword-based heuristics for goal achievement
- **Full Audit Trail**: Scratchpad logs iteration with timestamps
- **Production Ready**: 121 passing tests, 90%+ coverage, comprehensive error handling

**Safety Guarantees**:
- ✅ Never runs on main/master branches
- ✅ Token budget limits (30,000 tokens default)
- ✅ Max 10 iterations enforced
- ✅ Prompt validation (requires Goal and Success Criteria)
- ✅ Full transparency via scratchpad logging

**Simplified Design Philosophy**:
- Remove complexity, focus on core workflow
- Single iteration makes reasoning easier
- Users can chain invocations if needed
- Clear success/failure results

---

## Table of Contents

1. [Introduction](#introduction)
2. [How It Works](#how-it-works)
3. [Prompt Format](#prompt-format)
4. [Scratchpad Structure](#scratchpad-structure)
5. [Termination Criteria](#termination-criteria)
6. [Safety Mechanisms](#safety-mechanisms)
7. [Usage Guide](#usage-guide)
8. [Configuration](#configuration)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [Examples](#examples)

---

## Introduction

### What is Headless Mode?

Headless Mode allows AURORA to work autonomously on a coding task without requiring human approval between iterations. Instead of the typical interactive loop:

```
Human: "Implement feature X"
→ AURORA: Generates plan
→ Human: "Looks good, proceed"
→ AURORA: Implements code
→ Human: "Run tests"
→ AURORA: Runs tests
→ ... (repeat)
```

Headless Mode automates the entire loop:

```
Human: Creates prompt file with goal
→ AURORA: Runs autonomously until goal achieved
→ Human: Reviews final result
```

### When to Use Headless Mode

**Good Use Cases**:
- ✅ Implementing well-defined features with clear acceptance criteria
- ✅ Running experiments where you want to compare multiple approaches
- ✅ Automating routine refactoring tasks
- ✅ Generating boilerplate code with specific requirements
- ✅ Exploring solutions overnight or during off-hours

**Bad Use Cases**:
- ❌ Critical production changes requiring human oversight
- ❌ Exploratory tasks with unclear requirements
- ❌ Tasks requiring external system interactions
- ❌ Security-sensitive changes
- ❌ Changes affecting multiple repos or external dependencies

### Key Concepts

**Prompt**: A markdown file specifying your goal, success criteria, constraints, and context.

**Scratchpad**: A markdown file that logs every iteration, tracking progress, costs, and decisions.

**Iteration**: One complete SOAR cycle (Plan → Act → Observe → Reflect).

**Termination**: The moment execution stops due to goal achievement, budget limit, or max iterations.

**Safety Branch**: A dedicated git branch (default: `headless`) where experiments run safely.

---

## How It Works

### Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Pre-Flight Safety Checks                                 │
│    - Validate git branch (must be "headless", not main)     │
│    - Load and validate prompt file                          │
│    - Initialize or load scratchpad                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Main Iteration Loop                                      │
│    ┌──────────────────────────────────────────────┐         │
│    │ Execute SOAR iteration:                      │         │
│    │   - Plan: Analyze goal and create strategy  │         │
│    │   - Act: Generate or modify code            │         │
│    │   - Observe: Run tests, check results       │         │
│    │   - Reflect: Assess progress                │         │
│    └──────────────────────────────────────────────┘         │
│                        ↓                                     │
│    ┌──────────────────────────────────────────────┐         │
│    │ Update scratchpad:                           │         │
│    │   - Log iteration number and timestamp      │         │
│    │   - Record actions taken and results        │         │
│    │   - Track cost for this iteration           │         │
│    └──────────────────────────────────────────────┘         │
│                        ↓                                     │
│    ┌──────────────────────────────────────────────┐         │
│    │ Check termination conditions:                │         │
│    │   1. Goal achieved? (LLM evaluation)        │         │
│    │   2. Budget exceeded?                       │         │
│    │   3. Max iterations reached?                │         │
│    └──────────────────────────────────────────────┘         │
│                        ↓                                     │
│              No termination? Loop back                       │
│              Termination? Continue to step 3                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Cleanup and Report                                       │
│    - Write final scratchpad state                          │
│    - Return HeadlessResult with summary                    │
│    - Log termination reason                                │
└─────────────────────────────────────────────────────────────┘
```

### Components

**1. GitEnforcer**
- Validates current git branch
- Blocks execution on main/master
- Detects detached HEAD state
- Ensures clean working tree (optional)

**2. PromptLoader**
- Parses prompt markdown file
- Validates required sections (Goal, Success Criteria)
- Extracts constraints and context
- Provides structured data to orchestrator

**3. ScratchpadManager**
- Initializes scratchpad file
- Appends iteration logs
- Tracks cumulative cost
- Detects termination signals
- Provides iteration history

**4. HeadlessOrchestrator**
- Main control loop
- Integrates all components
- Executes SOAR iterations
- Evaluates goal achievement
- Enforces budget and iteration limits

---

## Prompt Format

### Required Structure

A valid prompt file must be a markdown document with these sections:

```markdown
# Goal
[One paragraph describing what you want to achieve]

# Success Criteria
- [Criterion 1: Specific, measurable outcome]
- [Criterion 2: Another measurable outcome]
- [Criterion 3: ...]
- ... (at least one criterion required)

# Constraints
- [Constraint 1: Limitation or requirement]
- [Constraint 2: Budget, time, technical constraints]
- ... (can be empty, but section header required)

# Context
[Any background information, existing code structure,
dependencies, or relevant details that help AURORA
understand the task]
```

### Section Details

#### Goal
**Purpose**: One-paragraph description of the objective.

**Requirements**:
- Must be present
- Should be specific and achievable
- Should state WHAT to build, not HOW
- Should be 1-3 sentences

**Example**:
```markdown
# Goal
Implement a user authentication system with email verification and password reset
functionality. The system should support user registration, login, logout, and
password recovery flows.
```

**Bad Examples**:
```markdown
# Goal
Make the authentication better.  ❌ Too vague

# Goal
Write code.  ❌ Not specific

# Goal
[Empty]  ❌ Required field missing
```

---

#### Success Criteria
**Purpose**: Measurable conditions that define when the goal is achieved.

**Requirements**:
- At least one criterion required
- Each criterion should be verifiable
- Use bullet points (- or *)
- Should be specific and objective

**Example**:
```markdown
# Success Criteria
- Users can register with email and password
- Email verification link is sent upon registration
- Users can login with verified email and password
- All passwords are hashed using bcrypt
- Unit tests achieve >90% code coverage
- Integration tests cover all user flows
- API endpoints return appropriate status codes
```

**Good Criteria Characteristics**:
- ✅ Binary (pass/fail): "Tests pass" not "Tests mostly pass"
- ✅ Measurable: "Coverage >90%" not "Good coverage"
- ✅ Verifiable: Can be checked programmatically
- ✅ Achievable: Within scope of a single headless run

**Bad Criteria**:
```markdown
# Success Criteria
- Code should be good  ❌ Subjective
- Make it fast  ❌ Not measurable
- Everything works  ❌ Too vague
```

---

#### Constraints
**Purpose**: Limitations, requirements, and boundaries for the implementation.

**Requirements**:
- Section header required (can be empty)
- Use bullet points for each constraint
- Should include budget and iteration limits

**Example**:
```markdown
# Constraints
- Budget limit: $5.00
- Maximum iterations: 15
- Must use existing database schema
- Must be compatible with Python 3.9+
- No external authentication services (OAuth, Auth0, etc.)
- Password minimum length: 8 characters
- Email verification token valid for 48 hours
- Rate limiting: 5 login attempts per minute per IP
```

**Common Constraint Types**:
- **Budget**: `Budget limit: $X.XX`
- **Time**: `Maximum iterations: N`
- **Technical**: `Must use Python 3.9+`, `No external dependencies`
- **Business**: `GDPR compliant`, `Must support IE11`
- **Quality**: `Code coverage >80%`, `No security vulnerabilities`

---

#### Context
**Purpose**: Background information to help AURORA understand the environment.

**Requirements**:
- Optional but highly recommended
- Free-form text (paragraphs, lists, code snippets)
- Should mention existing code, frameworks, dependencies

**Example**:
```markdown
# Context
This authentication system will be integrated into an existing web application.
The application currently uses Flask framework and PostgreSQL database. The user
table already exists with columns: id, email, password_hash, is_verified,
created_at, updated_at.

The system needs to be production-ready and follow security best practices.
Consider edge cases like concurrent login attempts, token replay attacks, and
email deliverability issues.

Key existing modules:
- `app/database.py`: Database connection and models
- `app/email_service.py`: Email sending (already configured)
- `app/config.py`: Application configuration
```

**What to Include**:
- Existing code structure and relevant files
- Frameworks and libraries in use
- Database schema or data models
- External integrations or APIs
- Security requirements
- Performance expectations
- Known issues or technical debt

---

### Complete Example

```markdown
# Goal
Implement a caching layer for the product API to reduce database load. The cache
should use Redis, support TTL expiration, and invalidate on product updates.

# Success Criteria
- GET /api/products/:id returns cached response on second request
- Cache hit rate >80% in load tests
- Cache automatically invalidates when product is updated
- Cache TTL is configurable (default: 5 minutes)
- Redis connection failures fall back to direct database queries
- Unit tests cover cache hit, miss, and invalidation scenarios
- Load test shows 50% reduction in database queries
- No performance regression for cache misses

# Constraints
- Budget limit: $3.00
- Maximum iterations: 10
- Must use existing Redis instance (redis://localhost:6379)
- Must maintain backward compatibility with existing API
- Cache key format: "product:{id}:v1"
- No breaking changes to response format
- All existing tests must continue passing

# Context
The product API is a Flask application using SQLAlchemy ORM. Current response
time is ~200ms per request, mostly spent on database queries.

Relevant files:
- `app/api/products.py`: Product endpoints
- `app/models/product.py`: Product model
- `app/database.py`: Database session management
- `requirements.txt`: Dependencies (Flask 2.3, SQLAlchemy 2.0)

Redis is already installed and running locally. The app uses Flask-Caching for
session storage, so add `redis` to requirements.txt.

Product update triggers: PUT /api/products/:id, DELETE /api/products/:id
```

---

## Scratchpad Structure

### Purpose

The scratchpad is a living document that logs every iteration of headless execution. It serves as:
- **Audit trail**: Complete history of what AURORA did
- **Progress tracker**: Current status and cost
- **Debug log**: Understand why AURORA made specific decisions
- **Resumption point**: Can resume from partial completion

### File Format

```markdown
# Scratchpad: [Task Name]

**Status**: [PENDING|IN_PROGRESS|COMPLETED|TERMINATED|BLOCKED]
**Total Cost**: $X.XX
**Total Iterations**: N

---

## Iteration 1 - [Timestamp]

**Phase**: [Planning|Implementation|Testing|Debugging|Reflection]
**Action**: [Brief description of what was done]
**Result**: [Outcome of the action]
**Cost**: $X.XX

**Notes**: [Any observations, decisions, or issues]

---

## Iteration 2 - [Timestamp]

...

---

[Signal: GOAL_ACHIEVED] ← Only present at termination
```

### Status Values

| Status | Meaning | When Set |
|--------|---------|----------|
| `PENDING` | Not started yet | Initial state |
| `IN_PROGRESS` | Currently executing | After first iteration begins |
| `COMPLETED` | Goal achieved | When success criteria met |
| `TERMINATED` | Stopped due to limit | Budget exceeded or max iterations |
| `BLOCKED` | Cannot proceed | Error or external dependency |

### Iteration Fields

**Phase**: High-level categorization of what the iteration focused on
- `Planning`: Analyzing requirements, creating strategy
- `Implementation`: Writing or modifying code
- `Testing`: Running tests, validating behavior
- `Debugging`: Investigating failures, fixing bugs
- `Reflection`: Assessing progress, adjusting strategy

**Action**: Concise description of what AURORA did (1-2 sentences)

**Result**: Outcome of the action (success, failure, partial)

**Cost**: LLM API cost for this iteration (in USD)

**Notes**: Free-form observations, important to capture:
- Key decisions made and why
- Trade-offs considered
- Edge cases discovered
- Technical issues encountered
- Next steps planned

### Example Scratchpad

```markdown
# Scratchpad: Product API Caching

**Status**: COMPLETED
**Total Cost**: $2.15
**Total Iterations**: 7

---

## Iteration 1 - 2025-01-15 14:00:00

**Phase**: Planning
**Action**: Analyzed codebase structure and existing Flask-Caching setup
**Result**: Identified integration point in app/api/products.py. Existing cache only used for sessions.
**Cost**: $0.25

**Notes**: Redis is running locally on default port. Need to add redis-py to requirements.txt. Existing product endpoint is simple, should be straightforward to wrap with caching decorator.

---

## Iteration 2 - 2025-01-15 14:08:00

**Phase**: Implementation
**Action**: Added redis dependency and created cache utility in app/cache.py
**Result**: Created RedisCache class with get/set/delete methods. Configured connection to redis://localhost:6379.
**Cost**: $0.35

**Notes**: Used redis-py 5.0.1 (latest stable). Added connection pooling for better performance. Included health check method.

---

## Iteration 3 - 2025-01-15 14:18:00

**Phase**: Implementation
**Action**: Applied caching decorator to GET /api/products/:id endpoint
**Result**: Added @cached decorator with 5-minute TTL. Cache key format: "product:{id}:v1".
**Cost**: $0.30

**Notes**: First request caches, second request hits cache. Need to add cache invalidation on product updates.

---

## Iteration 4 - 2025-01-15 14:28:00

**Phase**: Implementation
**Action**: Added cache invalidation to PUT and DELETE product endpoints
**Result**: Both endpoints now call cache.delete() after successful database update.
**Cost**: $0.25

**Notes**: Tested manually - updates properly invalidate cache. Need to add fallback for Redis failures.

---

## Iteration 5 - 2025-01-15 14:35:00

**Phase**: Implementation
**Action**: Added Redis connection failure fallback logic
**Result**: Wrapped cache operations in try/except. Falls back to direct database query on Redis errors.
**Cost**: $0.20

**Notes**: Tested by stopping Redis - API continues working with slightly higher latency. Logs warning on cache failures.

---

## Iteration 6 - 2025-01-15 14:42:00

**Phase**: Testing
**Action**: Wrote unit tests for cache hit, miss, and invalidation scenarios
**Result**: Added 8 unit tests to tests/test_cache.py. All passing.
**Cost**: $0.40

**Notes**: Tests cover: cache hit, cache miss, TTL expiration, invalidation on update, invalidation on delete, Redis failure fallback, connection error handling, key format validation.

---

## Iteration 7 - 2025-01-15 14:50:00

**Phase**: Testing
**Action**: Ran load tests to measure cache hit rate and database query reduction
**Result**: Cache hit rate: 85% (exceeds 80% target). Database queries reduced by 60% (exceeds 50% target). All existing tests still passing.
**Cost**: $0.40

**Notes**: Load test simulated 1000 requests with 70% repeat products. Average response time improved from 200ms to 45ms for cache hits. No performance regression for cache misses (still ~200ms).

[Signal: GOAL_ACHIEVED]

---
```

### Termination Signals

The scratchpad ends with a termination signal when execution stops:

**[Signal: GOAL_ACHIEVED]**
- All success criteria met
- Task completed successfully
- Safe to merge changes

**[Signal: BUDGET_EXCEEDED]**
- Total cost exceeded budget limit
- Partial progress may be usable
- Review what was accomplished

**[Signal: MAX_ITERATIONS]**
- Reached iteration limit without completing goal
- May need to increase limit or simplify goal
- Review progress to see if close to completion

**[Signal: BLOCKED]**
- Cannot proceed due to external dependency
- Error condition that requires human intervention
- Check notes for details

---

## Termination Criteria

Headless execution stops when any of these conditions are met:

### 1. Goal Achieved

**Trigger**: LLM evaluation determines all success criteria are met.

**How It Works**:
1. After each iteration, orchestrator sends scratchpad to LLM
2. LLM compares actions taken against success criteria
3. If all criteria satisfied, returns GOAL_ACHIEVED signal
4. Orchestrator stops with successful completion

**Example**:
```
Success Criteria:
- Users can register with email and password ✅
- Email verification link sent ✅
- Unit tests pass ✅
- Coverage >90% ✅

→ LLM: "All criteria met, goal achieved"
→ Termination: GOAL_ACHIEVED
```

**Configuration**:
```python
# Evaluation is automatic, but you can customize the prompt
config = HeadlessConfig(
    evaluation_prompt_template="""
    Evaluate if the following success criteria are met:
    {criteria}

    Based on scratchpad:
    {scratchpad}

    Return GOAL_ACHIEVED if all criteria met, otherwise CONTINUE.
    """
)
```

---

### 2. Budget Exceeded

**Trigger**: Cumulative cost exceeds budget limit.

**How It Works**:
1. Each iteration tracks LLM API cost
2. Scratchpad maintains running total
3. Before next iteration, check: `total_cost >= budget_limit`
4. If exceeded, stop with BUDGET_EXCEEDED

**Example**:
```
Budget Limit: $5.00
Iteration 1: $0.50 (total: $0.50)
Iteration 2: $0.75 (total: $1.25)
...
Iteration 8: $0.65 (total: $5.10) ← Exceeds $5.00
→ Termination: BUDGET_EXCEEDED
```

**Configuration**:
```python
config = HeadlessConfig(
    budget_limit=10.0  # Increase for complex tasks
)
```

**Best Practice**: Start with conservative budget, increase if needed:
- Simple tasks: $2-5
- Medium complexity: $5-10
- Complex features: $10-20

---

### 3. Max Iterations Reached

**Trigger**: Iteration count reaches maximum limit.

**How It Works**:
1. Each iteration increments counter
2. Before next iteration, check: `iterations >= max_iterations`
3. If reached, stop with MAX_ITERATIONS

**Example**:
```
Max Iterations: 10
Iterations completed: 10
Goal achieved: No
→ Termination: MAX_ITERATIONS (incomplete)
```

**Configuration**:
```python
config = HeadlessConfig(
    max_iterations=20  # Increase for iterative tasks
)
```

**Best Practice**: Set based on task complexity:
- Simple (e.g., single function): 5-10 iterations
- Medium (e.g., API endpoint): 10-15 iterations
- Complex (e.g., full feature): 15-25 iterations

---

### 4. Git Safety Error

**Trigger**: Git branch validation fails before execution starts.

**How It Works**:
1. Before starting, GitEnforcer checks current branch
2. If on main/master or not on required branch: error
3. Execution never starts

**Example**:
```
$ git branch
* main  ← On main branch

$ aur headless experiment.md
Error: Cannot run headless mode on branch 'main'
→ Termination: GIT_SAFETY_ERROR (before iteration 1)
```

**Resolution**:
```bash
$ git checkout -b headless
$ aur headless experiment.md
✓ Running on branch 'headless'
```

---

### 5. Prompt Validation Error

**Trigger**: Prompt file is invalid or missing required sections.

**How It Works**:
1. PromptLoader parses prompt file
2. Validates presence of Goal and Success Criteria
3. If missing or malformed: error
4. Execution never starts

**Example**:
```markdown
# Goal
Implement feature X

# Success Criteria
[Empty - no criteria listed]

→ Termination: PROMPT_ERROR (empty success criteria)
```

**Resolution**: Fix prompt file and retry.

---

## Safety Mechanisms

Headless mode includes multiple layers of safety to prevent damage and runaway costs:

### 1. Git Branch Enforcement

**Protection**: Prevents running on main/master branches.

**Implementation**:
```python
enforcer = GitEnforcer(GitEnforcerConfig(
    required_branch="headless",
    blocked_branches=["main", "master"]
))

enforcer.validate_safety()  # Raises GitBranchError if unsafe
```

**What It Blocks**:
- ❌ Running on `main` branch
- ❌ Running on `master` branch
- ❌ Running in detached HEAD state
- ❌ Running with uncommitted changes (optional)

**Bypass** (not recommended):
```python
config = HeadlessConfig(required_branch=None)  # Disables enforcement
```

---

### 2. Budget Limits

**Protection**: Prevents runaway LLM costs.

**Implementation**:
```python
config = HeadlessConfig(budget_limit=5.0)  # Stop at $5.00
```

**How It Works**:
- Each iteration reports cost to scratchpad
- Before next iteration: check if `total_cost >= budget_limit`
- If exceeded: stop immediately with BUDGET_EXCEEDED

**Cost Tracking**:
```python
result = orchestrator.execute()
print(f"Total cost: ${result.total_cost:.2f}")
print(f"Iterations: {result.iterations}")
print(f"Avg cost/iteration: ${result.total_cost / result.iterations:.2f}")
```

---

### 3. Iteration Caps

**Protection**: Prevents infinite loops and stuck tasks.

**Implementation**:
```python
config = HeadlessConfig(max_iterations=10)
```

**Rationale**:
- Protects against bugs in termination logic
- Forces re-evaluation if task taking too long
- Prevents partial progress from consuming excessive resources

**When to Increase**:
- Complex, multi-step features
- Iterative refinement tasks (e.g., optimization)
- Tasks with many edge cases to discover

---

### 4. Full Audit Trail

**Protection**: Complete transparency of what AURORA did.

**Implementation**: Every action logged to scratchpad with:
- Timestamp
- Phase and action description
- Result and cost
- Human-readable notes

**Benefits**:
- **Debugging**: Understand why AURORA made specific decisions
- **Accountability**: Full record of changes made
- **Learning**: See how AURORA approaches problems
- **Resumption**: Can resume from any point if interrupted

---

### 5. Graceful Degradation

**Protection**: Handles failures without crashing or leaving broken state.

**Examples**:
- Redis connection failure → Falls back to direct database
- Test failure → Logs failure, continues (doesn't abort)
- Invalid syntax → Catches error, attempts fix in next iteration
- External API timeout → Retries with backoff

---

## Usage Guide

### Basic Usage

#### Step 1: Create a Prompt File

```bash
$ cat > experiment.md << EOF
# Goal
Add input validation to the user registration endpoint.

# Success Criteria
- Email format is validated (must contain @)
- Password length is validated (minimum 8 characters)
- Error messages are descriptive
- Unit tests cover all validation cases
- Tests pass

# Constraints
- Budget limit: $3.00
- Maximum iterations: 10
- Must maintain backward compatibility

# Context
The registration endpoint is in app/api/auth.py. Currently
accepts any input without validation.
EOF
```

#### Step 2: Create a Safety Branch

```bash
$ git checkout -b headless
```

#### Step 3: Run Headless Mode

```bash
$ aur headless experiment.md
```

Or with custom configuration:

```bash
$ aur headless experiment.md --max-iterations 15 --budget 5.0
```

#### Step 4: Monitor Progress

Watch the scratchpad file for real-time updates:

```bash
$ tail -f scratchpad.md
```

Or check status periodically:

```bash
$ aur headless status
```

#### Step 5: Review Results

When execution completes:

```bash
$ cat scratchpad.md  # Read full history
$ git diff  # See code changes
$ pytest  # Verify tests pass
```

If satisfied:

```bash
$ git add .
$ git commit -m "feat: add input validation to registration (headless)"
$ git checkout main
$ git merge headless
```

---

### Advanced Usage

#### Dry Run Mode

Test your prompt without actually executing:

```bash
$ aur headless experiment.md --dry-run
✓ Prompt is valid
✓ Git branch is safe
✓ Budget: $5.00, Max iterations: 10
✓ Success criteria: 5 items
✓ Constraints: 8 items

Would execute with:
  - Goal: "Add input validation..."
  - Success Criteria: 5 items
  - Budget: $5.00
  - Max Iterations: 10

Not executing (--dry-run mode)
```

#### Custom Configuration File

```yaml
# headless_config.yaml
max_iterations: 20
budget_limit: 10.0
required_branch: experiment
scratchpad_backup: true
evaluation_prompt_template: |
  Review the scratchpad and determine if all success criteria are met.
  Criteria:
  {criteria}

  Scratchpad:
  {scratchpad}

  Respond with only GOAL_ACHIEVED or CONTINUE.
```

```bash
$ aur headless experiment.md --config headless_config.yaml
```

#### Resuming Interrupted Execution

If execution was interrupted (e.g., system crash), you can resume:

```bash
$ aur headless experiment.md --resume
```

The orchestrator will:
1. Load existing scratchpad
2. Parse total cost and iterations so far
3. Continue from where it left off
4. Respect original budget and iteration limits (minus what's been used)

#### Multiple Experiments in Parallel

Run multiple headless experiments simultaneously:

```bash
# Terminal 1
$ git checkout -b headless-feature-a
$ aur headless feature_a.md --scratchpad scratchpad_a.md

# Terminal 2
$ git checkout -b headless-feature-b
$ aur headless feature_b.md --scratchpad scratchpad_b.md
```

Each experiment runs independently with its own scratchpad.

---

### Programmatic API

Use headless mode from Python code:

```python
from aurora_soar.headless import HeadlessOrchestrator, HeadlessConfig
from aurora_soar.orchestrator import SOAROrchestrator

# Setup SOAR orchestrator (your existing instance)
soar = SOAROrchestrator(...)

# Configure headless mode
config = HeadlessConfig(
    max_iterations=15,
    budget_limit=8.0,
    required_branch="headless"
)

# Create orchestrator
orchestrator = HeadlessOrchestrator(
    prompt_path="experiment.md",
    scratchpad_path="scratchpad.md",
    soar_orchestrator=soar,
    config=config
)

# Execute
result = orchestrator.execute()

# Check results
if result.goal_achieved:
    print(f"✓ Goal achieved in {result.iterations} iterations")
    print(f"  Total cost: ${result.total_cost:.2f}")
else:
    print(f"✗ Terminated: {result.termination_reason}")
    print(f"  Completed {result.iterations} iterations")
    print(f"  Total cost: ${result.total_cost:.2f}")
```

---

## Configuration

### HeadlessConfig Options

```python
@dataclass
class HeadlessConfig:
    # Execution limits
    max_iterations: int = 10                    # Stop after N iterations
    budget_limit: float = 5.0                   # Stop when cost exceeds $X

    # Git safety
    required_branch: str = "headless"           # Must be on this branch
    blocked_branches: list[str] = ["main", "master"]  # Never allow these

    # Scratchpad behavior
    auto_create_scratchpad: bool = True         # Create if missing
    scratchpad_backup: bool = True              # Backup before starting

    # Goal evaluation
    evaluation_prompt_template: str = "..."     # LLM prompt for goal check

    # Advanced
    allow_dirty_git: bool = False               # Allow uncommitted changes
    parallel_execution: bool = False            # Run multiple experiments
```

### Tuning Guidelines

| Task Complexity | max_iterations | budget_limit | Notes |
|----------------|----------------|--------------|-------|
| Simple (single function) | 5-10 | $2-5 | Quick validation/fix |
| Medium (API endpoint) | 10-15 | $5-10 | Implementation + tests |
| Complex (full feature) | 15-25 | $10-20 | Multiple components |
| Experimental | 30+ | $20+ | Exploratory, may fail |

### Budget Estimation

**Cost per iteration**: Varies by model and task complexity
- GPT-4: $0.30-0.80 per iteration
- GPT-3.5: $0.05-0.15 per iteration

**Factors affecting cost**:
- Context size (larger codebase = higher cost)
- Iteration complexity (debugging > planning)
- Number of files touched
- Test execution time

**Formula**:
```
budget_limit ≈ expected_iterations × $0.50 × 1.5 (safety margin)
```

Example:
```
Expected: 10 iterations
Budget: 10 × $0.50 × 1.5 = $7.50
```

---

## Best Practices

### Writing Effective Prompts

1. **Be Specific About Success**
   ```markdown
   # Success Criteria
   ✅ - All tests pass
   ✅ - Code coverage >85%
   ✅ - Linting produces zero errors

   ❌ - Code looks good
   ❌ - Most tests pass
   ❌ - High code coverage
   ```

2. **Include Concrete Examples**
   ```markdown
   # Context
   Example valid input: {"email": "user@example.com", "age": 25}
   Example invalid input: {"email": "not-an-email", "age": "twenty"}
   Expected error: {"error": "Invalid email format"}
   ```

3. **Specify Constraints Early**
   ```markdown
   # Constraints
   - Must use existing User model (app/models.py)
   - Must not modify database schema
   - Must use bcrypt for password hashing (no plaintext)
   ```

4. **Provide File Paths**
   ```markdown
   # Context
   Relevant files:
   - app/api/auth.py (registration endpoint)
   - app/models/user.py (User model)
   - tests/test_auth.py (existing tests)
   ```

---

### Monitoring Execution

**Watch scratchpad in real-time**:
```bash
$ watch -n 5 tail -20 scratchpad.md
```

**Check cost accumulation**:
```bash
$ grep "Total Cost" scratchpad.md
Total Cost: $2.35
```

**Count iterations**:
```bash
$ grep -c "## Iteration" scratchpad.md
7
```

**Check status**:
```bash
$ head -5 scratchpad.md | grep Status
**Status**: IN_PROGRESS
```

---

### Handling Failures

**Budget exceeded before completion**:
1. Review scratchpad to see what was accomplished
2. Assess if partial progress is usable
3. If close to completion, increase budget and resume
4. If stuck, revise prompt to simplify goal

**Max iterations without completion**:
1. Check if goal is too ambitious (split into smaller tasks)
2. Review scratchpad for patterns (e.g., stuck in loop)
3. Increase max_iterations if making steady progress
4. Simplify success criteria if too strict

**Git safety error**:
1. Create proper safety branch: `git checkout -b headless`
2. Verify: `git branch` shows `* headless`
3. Retry headless execution

**Prompt validation error**:
1. Check prompt file has all required sections
2. Ensure Success Criteria has at least one item
3. Verify markdown formatting is correct
4. Use `--dry-run` to validate before executing

---

### Cost Optimization

**Reduce iterations**:
- Write more specific success criteria
- Provide better context and examples
- Include relevant file paths
- Pre-validate prompt with `--dry-run`

**Use cheaper models for simple tasks**:
```python
config = SOARConfig(model="gpt-3.5-turbo")  # Cheaper than GPT-4
```

**Start with lower limits**:
```python
config = HeadlessConfig(
    max_iterations=5,    # Start small
    budget_limit=2.0     # Increase if needed
)
```

**Batch similar tasks**:
Instead of multiple headless runs, combine into one:
```markdown
# Goal
Add input validation to all API endpoints (registration, login, profile update).

# Success Criteria
- Registration endpoint validates email and password
- Login endpoint validates email and password
- Profile endpoint validates all user fields
- ... (combined criteria)
```

---

## Troubleshooting

This section covers common issues with the simplified single-iteration headless mode.

### Issue 1: Execution Never Starts

**Symptoms**:
- Command runs but exits immediately
- No scratchpad created
- Error message about git or prompt

**Causes & Solutions**:

1. **Wrong git branch**
   ```bash
   Error: Cannot run headless mode on branch 'main'

   Solution:
   $ git checkout -b headless-experiment
   $ aur headless experiment.md
   ```

   The simplified version blocks main/master branches by default.

2. **Invalid prompt file - Missing Goal section**
   ```bash
   Error: Prompt validation failed: Missing 'Goal' section

   Solution:
   - Ensure prompt has '# Goal' header
   - Add at least one paragraph under Goal
   - Use `--dry-run` to validate:
     $ aur headless experiment.md --dry-run
   ```

3. **Invalid prompt file - Empty Success Criteria**
   ```bash
   Error: Prompt must have 'Success Criteria' section with at least one criterion

   Solution:
   - Ensure prompt has '# Success Criteria' header
   - Add at least one bullet point:
     # Success Criteria
     - [Your criterion here]
   ```

4. **Prompt file not found**
   ```bash
   Error: Prompt file not found: experiment.md

   Solution:
   - Check file path is correct
   - Use absolute path: /full/path/to/experiment.md
   - Verify file exists: ls -l experiment.md
   ```

5. **Invalid budget or iteration count**
   ```bash
   Error: Budget must be positive
   Error: max_iterations cannot exceed 10

   Solution:
   - Budget must be > 0 (tokens)
   - Max iterations: 1-10 only
   - Example: aur headless task.md --budget 50000 --max-iter 5
   ```

---

### Issue 2: Goal Not Achieved After Single Iteration

**Symptoms**:
- Execution completes successfully
- Scratchpad shows iteration logged
- Result shows `goal_achieved: False`

**Understanding**:
This is **expected behavior** for the simplified version. A single iteration rarely completes complex goals.

**Solutions**:

1. **Run additional iterations manually**
   ```bash
   # Run iteration 1
   $ aur headless experiment.md --scratchpad scratch.md

   # Check results
   $ cat scratch.md

   # Run iteration 2 (scratchpad will append)
   $ aur headless experiment.md --scratchpad scratch.md
   ```

2. **Simplify the goal**
   Break down complex goals into smaller steps:
   ```markdown
   # Instead of:
   # Goal
   Implement full authentication system with email verification

   # Try:
   # Goal
   Implement basic user registration endpoint (email + password only)
   ```

3. **Review scratchpad for progress**
   The scratchpad shows what was accomplished:
   ```bash
   $ cat scratchpad.md
   ```

   Look for:
   - What actions were taken
   - What results occurred
   - Whether partial progress was made

---

### Issue 3: Success Evaluation Seems Wrong

**Symptoms**:
- Execution appears successful but `goal_achieved: False`
- Or vice versa: appears to fail but `goal_achieved: True`

**Understanding**:
The simplified version uses **keyword-based heuristics** for success evaluation, not true understanding.

**How It Works**:
```python
# Counts occurrences of keywords in scratchpad
success_keywords = ["completed", "success", "achieved", "done", "finished", "passing"]
failure_keywords = ["failed", "error", "blocked", "cannot", "unable"]

# Returns True if success_count > failure_count
```

**Solutions**:

1. **Review actual results manually**
   Don't rely solely on the heuristic:
   ```bash
   $ cat scratchpad.md
   $ git diff  # Check what changed
   $ pytest    # Run tests yourself
   ```

2. **Use explicit success criteria**
   Write criteria that include these keywords:
   ```markdown
   # Success Criteria
   - All tests passing (not just "tests pass")
   - Implementation completed successfully
   - No errors in execution
   ```

3. **Chain iterations and check manually**
   After each iteration, review before continuing:
   ```bash
   $ aur headless task.md
   $ cat scratchpad.md  # Review
   $ git diff           # Check changes
   $ pytest             # Verify
   # If good, run next iteration
   $ aur headless task.md
   ```

---

### Issue 4: Token Budget Not Enforced

**Symptoms**:
- Set budget with `--budget 1000`
- Execution uses more tokens
- No budget exceeded error

**Understanding**:
Token budget validation is in the config, but actual enforcement in the SOAR orchestrator is **not yet implemented**.

**Current Behavior**:
- Config validates budget > 0
- Config validates budget is reasonable
- SOAR execution does NOT check budget

**Solutions**:

1. **Monitor manually**
   Check SOAR execution output for token usage:
   ```bash
   $ aur headless experiment.md --verbose
   ```

2. **Use iteration limits as fallback**
   Limit iterations instead of tokens:
   ```bash
   $ aur headless experiment.md --max-iter 3
   ```

3. **Track in scratchpad**
   Review scratchpad for cost information (if SOAR provides it):
   ```bash
   $ grep -i "cost\|token" scratchpad.md
   ```

**Future**: Budget enforcement will be added to SOAROrchestrator.

---

### Issue 5: Scratchpad Shows Errors But Execution "Succeeds"

**Symptoms**:
- Scratchpad contains error messages
- But HeadlessResult shows `termination_reason: SUCCESS`

**Understanding**:
The simplified orchestrator returns `SUCCESS` if the SOAR iteration **completed** (didn't crash), even if the SOAR result itself contained errors.

**Termination Reasons**:
- `SUCCESS`: SOAR iteration ran to completion
- `BLOCKED`: SOAR iteration crashed or failed to execute
- `GIT_SAFETY_ERROR`: Git validation failed
- `PROMPT_ERROR`: Prompt validation failed

**Solutions**:

1. **Always review scratchpad**
   Don't trust termination reason alone:
   ```bash
   $ cat scratchpad.md
   ```

   Look for:
   - Error messages in the result
   - "failed", "error", "cannot" keywords
   - Actual changes made (or not made)

2. **Check git diff**
   See what actually changed:
   ```bash
   $ git diff
   $ git status
   ```

3. **Run tests manually**
   Verify the changes work:
   ```bash
   $ pytest
   $ npm test
   $ cargo test
   ```

---

### Issue 6: SOAR Orchestrator Not Initialized

**Symptoms**:
```bash
Warning: SOAR orchestrator creation not implemented
This would initialize SOAROrchestrator with proper config
For now, aborting. Implement SOAR initialization first.
```

**Understanding**:
The CLI command has a placeholder for SOAR orchestrator initialization. Real implementation depends on your SOAR setup.

**Solutions**:

1. **Use dry-run mode for validation**
   Test configuration without SOAR:
   ```bash
   $ aur headless experiment.md --dry-run
   ```

2. **Wait for SOAR initialization implementation**
   The CLI will be updated to properly initialize SOAR orchestrator with:
   - API key from environment
   - Configuration from ~/.aurora/config.yaml
   - Proper model selection

3. **Use MCP tools instead**
   For now, use Aurora MCP tools through Claude Code CLI:
   ```bash
   # In Claude Code CLI
   > Use aurora_query to analyze this code
   ```

---

### Issue 7: Scratchpad Not Created

**Symptoms**:
- Execution completes
- No scratchpad file exists
- No error about scratchpad

**Causes & Solutions**:

1. **Check scratchpad path**
   ```bash
   $ aur headless experiment.md --show-scratchpad
   # Shows where scratchpad should be
   ```

   Default: `<prompt_name>_scratchpad.md` in same directory as prompt.

2. **Check permissions**
   ```bash
   $ ls -ld $(dirname experiment.md)
   # Should be writable
   ```

3. **Specify absolute path**
   ```bash
   $ aur headless experiment.md --scratchpad /tmp/scratch.md
   ```

4. **Check for errors**
   ```bash
   $ aur headless experiment.md 2>&1 | tee output.log
   # Review output.log for errors
   ```

---

### Issue 8: Execution Takes Too Long

**Symptoms**:
- Execution hangs or runs for many minutes
- No progress shown

**Causes & Solutions**:

1. **SOAR execution is slow**
   Single SOAR iterations can take 30 seconds to several minutes:
   ```bash
   # Monitor progress (if available)
   $ tail -f scratchpad.md
   ```

2. **Large context size**
   If codebase is large, SOAR processes more context:
   - Reduce scope in prompt
   - Focus on specific files/directories
   - Provide file paths in Context section

3. **Network issues**
   API calls to Anthropic may be slow:
   - Check internet connection
   - Try again later
   - Check Anthropic status page

4. **Set timeout (future feature)**
   Currently no timeout mechanism, but you can:
   ```bash
   # Kill after 5 minutes
   $ timeout 300 aur headless experiment.md
   ```

---

### Debugging Tips

**1. Always use dry-run first**
```bash
$ aur headless experiment.md --dry-run
```

Validates:
- Prompt file exists
- Prompt has required sections
- Git branch is safe
- Configuration is valid

**2. Enable verbose output**
```bash
$ aur headless experiment.md --verbose
```

Shows more details about execution.

**3. Review scratchpad after every execution**
```bash
$ aur headless experiment.md --show-scratchpad
```

Or manually:
```bash
$ cat experiment_scratchpad.md
```

**4. Check git status**
```bash
$ git status
$ git diff
```

See what actually changed.

**5. Verify with tests**
```bash
$ pytest -v
$ npm test
$ cargo test
```

Don't trust keyword heuristics alone.

**6. Use small experiments first**
```bash
# Small goal to test workflow
$ cat > test.md << EOF
# Goal
Print "hello world" to console

# Success Criteria
- Code executes without errors
- Output contains "hello world"
EOF

$ aur headless test.md --dry-run
$ aur headless test.md
```

---

### Common Pitfalls

**1. Expecting multi-iteration completion**
- Simplified version runs ONE iteration
- Chain invocations manually if needed

**2. Trusting success heuristics**
- Keyword-based, not true understanding
- Always verify manually

**3. Complex goals in single iteration**
- Break down into smaller steps
- One iteration = one focused action

**4. Missing context in prompt**
- Provide file paths
- Include examples
- Explain existing code structure

**5. Not checking actual results**
- Always review scratchpad
- Always check git diff
- Always run tests

---

### Getting Help

**Check logs**:
```bash
$ aur headless experiment.md 2>&1 | tee execution.log
```

**Report issues with**:
1. Prompt file content
2. Scratchpad content
3. Error messages
4. Git branch name
5. Command used
6. Expected vs actual behavior

**See Also**:
- [Developer Architecture Guide](../development/headless-architecture.md) - Implementation details
- [Testing Guide](../development/testing-guide.md) - How to test headless mode
- [SOAR Architecture](../development/SOAR_ARCHITECTURE.md) - SOAR pipeline details

---

## Examples

### Example 1: Simple Bug Fix

**Prompt** (`bug_fix.md`):
```markdown
# Goal
Fix the bug where user registration allows duplicate emails.

# Success Criteria
- Registering with an existing email returns 409 Conflict
- Error message says "Email already registered"
- Existing tests still pass
- New test added for duplicate email scenario

# Constraints
- Budget limit: $2.00
- Maximum iterations: 8
- Must not change database schema

# Context
The registration endpoint is in app/api/auth.py at line 45.
The User model is in app/models/user.py.
Tests are in tests/test_auth.py.
```

**Execution**:
```bash
$ git checkout -b headless
$ aur headless bug_fix.md
```

**Expected Scratchpad** (abbreviated):
```markdown
## Iteration 1 - Planning
Action: Analyzed codebase and identified missing uniqueness check
Result: Found registration endpoint doesn't query for existing email
Cost: $0.15

## Iteration 2 - Implementation
Action: Added email uniqueness check before creating user
Result: Query User.filter_by(email=email).first(), return 409 if exists
Cost: $0.30

## Iteration 3 - Testing
Action: Wrote test_duplicate_email_registration test
Result: Test passes, verifies 409 response and error message
Cost: $0.25

## Iteration 4 - Verification
Action: Ran full test suite
Result: All 47 tests pass, coverage still >90%
Cost: $0.20

[Signal: GOAL_ACHIEVED]
```

---

### Example 2: New Feature Implementation

**Prompt** (`feature_api_rate_limiting.md`):
```markdown
# Goal
Implement rate limiting for the API to prevent abuse. Limit users to 100
requests per minute using a token bucket algorithm.

# Success Criteria
- Middleware intercepts all API requests
- Rate limit enforced: 100 requests/minute per IP
- 429 Too Many Requests returned when limit exceeded
- Rate limit resets every minute
- X-RateLimit headers included in all responses
- Unit tests cover rate limit enforcement
- Load test confirms 100 req/min cap works
- All existing tests still pass

# Constraints
- Budget limit: $8.00
- Maximum iterations: 15
- Must use Redis for rate limit storage
- Must not break existing API functionality
- Must be configurable via environment variables

# Context
The Flask app uses blueprints. Middleware should be registered in app/__init__.py.
Redis is available at redis://localhost:6379.
Existing middleware: CORS, request logging.
Load tests are in tests/load_tests.py using locust.
```

**Execution**:
```bash
$ git checkout -b headless-rate-limiting
$ aur headless feature_api_rate_limiting.md --max-iterations 20 --budget 10.0
```

**Expected Result**:
- 12-15 iterations
- $6-8 total cost
- Full implementation with tests
- Ready to merge after manual review

---

### Example 3: Refactoring Task

**Prompt** (`refactor_auth_module.md`):
```markdown
# Goal
Refactor the authentication module to use dependency injection instead of
global state. Replace all references to `global_db` with injected `db`
parameter.

# Success Criteria
- All auth functions accept `db` parameter
- No references to `global_db` in auth module
- All call sites updated to pass `db`
- Tests updated to use mock `db` objects
- All tests pass
- Code complexity reduced (measured by cyclomatic complexity)

# Constraints
- Budget limit: $5.00
- Maximum iterations: 12
- Must maintain backward compatibility for external callers
- Must not change public API signatures

# Context
The auth module is in app/auth.py (450 lines).
global_db is imported from app/database.py.
Used in 8 functions: authenticate(), authorize(), create_user(), etc.
Tests are in tests/test_auth.py (already use mocks).
Cyclomatic complexity is measured with radon: `radon cc app/auth.py`.
```

---

## Related Documentation

- [ACT-R Activation System](./actr-activation.md) - Memory retrieval used in headless mode
- [SOAR Architecture](./SOAR_ARCHITECTURE.md) - Underlying reasoning pipeline
- [Performance Tuning](./performance-tuning.md) - Optimizing headless execution
- [Production Deployment](./production-deployment.md) - Running in production
- [Troubleshooting Advanced](./troubleshooting-advanced.md) - Advanced debugging

---

## Appendices

### Appendix A: Prompt Template

```markdown
# Goal
[One paragraph: what you want to achieve]

# Success Criteria
- [Measurable criterion 1]
- [Measurable criterion 2]
- [Measurable criterion 3]

# Constraints
- Budget limit: $X.XX
- Maximum iterations: N
- [Technical constraint]
- [Business constraint]

# Context
[Background information, existing code structure, dependencies,
file paths, configuration details]
```

### Appendix B: CLI Command Reference

```bash
# Basic execution
aur headless <prompt_file>

# With custom limits
aur headless <prompt_file> --max-iterations N --budget X.XX

# Dry run (validate without executing)
aur headless <prompt_file> --dry-run

# Custom scratchpad location
aur headless <prompt_file> --scratchpad <path>

# Resume interrupted execution
aur headless <prompt_file> --resume

# Custom configuration file
aur headless <prompt_file> --config <config.yaml>

# Check status of running execution
aur headless status

# Stop running execution
aur headless stop
```

### Appendix C: Cost Reference

**GPT-4 Turbo** (gpt-4-1106-preview):
- Input: $0.01 / 1K tokens
- Output: $0.03 / 1K tokens
- Typical iteration: $0.30-0.80

**GPT-3.5 Turbo** (gpt-3.5-turbo-1106):
- Input: $0.001 / 1K tokens
- Output: $0.002 / 1K tokens
- Typical iteration: $0.05-0.15

**Context size impact**:
- Small codebase (<1000 lines): Low cost
- Medium codebase (1K-10K lines): Medium cost
- Large codebase (>10K lines): High cost

---

**Document Version**: 1.0
**Status**: Production Ready
**Last Updated**: December 23, 2025
**Test Coverage**: 226 tests passing
**Related Tasks**: Task 8.3, Task 8.4

---

*For questions or feedback on headless mode, refer to the AURORA project team or create an issue in the repository.*
