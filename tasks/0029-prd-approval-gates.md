# PRD: Approval Gates, Policies & Recovery

**PRD ID**: 0029
**Status**: Draft
**Author**: Claude + User
**Created**: 2026-01-14

---

## 1. Problem Statement

Aurora's execution pipeline lacks proper control mechanisms:

1. **No visibility before execution**: `aur spawn` executes immediately without showing what will happen
2. **Poor agent failure handling**: 300s timeout, retry, another 300s, then fallback - wastes 10+ minutes
3. **No policy enforcement**: No guardrails for destructive operations (rm, force push, drop table)
4. **No checkpoint/resume**: If execution fails at step 7 of 10, must restart from scratch
5. **Scattered budget logic**: Budget tracking exists but not integrated with policies

## 2. Goals

- **G1**: Shared decomposition review for `aur goals` and `aur spawn`
- **G2**: Shared agent recovery module for `aur soar` and `aur spawn`
- **G3**: Unified policies engine (`policies.yaml`) covering budget + destructive ops + safety
- **G4**: Checkpoint/resume system for `aur spawn`
- **G5**: Stop on exceptions (not every task) - anomalies, gaps, policy violations

## 3. Non-Goals

- Interactive plan editing (too complex, limited value)
- Stop after every task for approval (annoying, no value)
- Real-time streaming of agent output (separate feature)
- Multi-user approval workflows (enterprise feature)

---

## 4. Design

### 4.1 Shared Modules Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED MODULES                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────┐    Used by: aur goals, aur spawn      │
│  │ DecompositionReview  │    - Display subgoals summary          │
│  │                      │    - Show agent assignments + gaps     │
│  └──────────────────────┘    - Proceed/abort/spawn-agents menu   │
│                                                                  │
│  ┌──────────────────────┐    Used by: aur soar, aur spawn       │
│  │ AgentRecovery        │    - Configurable timeout (default 120s)│
│  │                      │    - Max retries (default 2)           │
│  └──────────────────────┘    - Fallback to LLM on failure        │
│                                                                  │
│  ┌──────────────────────┐    Used by: all commands               │
│  │ PoliciesEngine       │    - Load .aurora/policies.yaml        │
│  │                      │    - Validate operations against rules │
│  └──────────────────────┘    - Budget integration                │
│                                                                  │
│  ┌──────────────────────┐    Used by: aur spawn                  │
│  │ CheckpointManager    │    - Save state after each task        │
│  │                      │    - Resume from checkpoint            │
│  └──────────────────────┘    - Handle Ctrl+C gracefully          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Module: DecompositionReview

**Purpose**: Show user what will happen before execution starts.

**Used by**:
- `aur goals` (existing, enhance)
- `aur spawn` (new - show before executing)

**Display format**:
```
╭──────────────────── Decomposition Summary ────────────────────╮
│ Goal: Improve memory indexing performance                     │
│                                                               │
│ Subgoals: 6                                                   │
│                                                               │
│  1. Profile current indexing performance                      │
│     Agent: @code-developer                                    │
│                                                               │
│  2. Identify bottlenecks in BM25 scoring                      │
│     Agent: @code-developer                                    │
│                                                               │
│  3. Optimize embedding generation                             │
│     Agent: performance-engineer ⚠ GAP                         │
│                                                               │
│  4. Implement parallel indexing                               │
│     Agent: @code-developer                                    │
│                                                               │
│ Summary:                                                      │
│   ✓ 5 subgoals assigned to available agents                   │
│   ⚠ 1 agent gap (will spawn ad-hoc or fallback)               │
│                                                               │
╰───────────────────────────────────────────────────────────────╯

Options:
  [P]roceed   - Execute (try ad-hoc agents → fallback to LLM)
  [F]allback  - Execute (LLM directly for gaps, faster)
  [A]bort     - Cancel and restart

Choice [P/f/a]:
```

**API**:
```python
class ReviewDecision(Enum):
    PROCEED = "proceed"    # Try ad-hoc agents → fallback to LLM
    FALLBACK = "fallback"  # LLM directly for gaps (faster)
    ABORT = "abort"        # Cancel and restart

class DecompositionReview:
    def __init__(self, subgoals: list[Subgoal], agent_gaps: list[AgentGap]):
        ...

    def display(self) -> None:
        """Display summary to terminal."""

    def prompt(self) -> ReviewDecision:
        """Prompt user for decision. Returns PROCEED|FALLBACK|ABORT."""
```

### 4.2.1 aur spawn Execution Preview

**Purpose**: Show what tasks will execute before running.

**Display format**:
```
╭─────────────── Execution Preview ───────────────╮
│ Tasks: 6                                        │
│                                                 │
│  1. [ ] Investigate current memory indexing     │
│     Agent: @code-developer                      │
│                                                 │
│  2. [ ] Analyze codebase architecture           │
│     Agent: performance-engineer ⚠ GAP           │
│                                                 │
│  3. [ ] Research best practices                 │
│     Agent: @market-researcher                    │
│  ...                                            │
│                                                 │
│ Summary:                                        │
│   ✓ 4 tasks with available agents               │
│   ⚠ 2 gaps (will spawn ad-hoc or fallback)      │
╰─────────────────────────────────────────────────╯

Options:
  [P]roceed   - Execute (try ad-hoc agents → fallback to LLM)
  [F]allback  - Execute (LLM directly for gaps, faster)
  [A]bort     - Cancel and restart

Choice [P/f/a]:
```

### 4.3 Module: AgentRecovery

**Purpose**: Handle agent execution failures consistently.

**Used by**:
- `aur soar` (Phase 5: Collect)
- `aur spawn` (task execution)

**Recovery flow**:
```
Agent execution requested
    │
    ▼
┌─────────────────────┐
│ Attempt 1 (120s)    │
└─────────────────────┘
    │
    ├─ Success ──────────────────────────────▶ Return result
    │
    ▼ Timeout/Error
┌─────────────────────┐
│ Attempt 2 (120s)    │
└─────────────────────┘
    │
    ├─ Success ──────────────────────────────▶ Return result
    │
    ▼ Timeout/Error
┌─────────────────────┐
│ Fallback to LLM     │  Direct LLM call, no agent
└─────────────────────┘
    │
    ▼
Return result (marked as fallback)
```

**Configuration** (in policies.yaml):
```yaml
agent_recovery:
  timeout_seconds: 120      # Per-attempt timeout
  max_retries: 2            # Total attempts before fallback
  fallback_to_llm: true     # Use LLM if all attempts fail
```

**API**:
```python
class AgentRecovery:
    def __init__(self, config: RecoveryConfig):
        self.timeout = config.timeout_seconds
        self.max_retries = config.max_retries
        self.fallback_enabled = config.fallback_to_llm

    def execute_with_recovery(
        self,
        agent_id: str,
        task: str,
        llm_client: LLMClient
    ) -> RecoveryResult:
        """Execute agent with retry and fallback logic."""

    def execute_fallback(self, task: str, llm_client: LLMClient) -> str:
        """Direct LLM call as last resort."""
```

### 4.4 Module: PoliciesEngine

**Purpose**: Unified policy enforcement for all commands.

**Config file**: `.aurora/policies.yaml`

```yaml
# .aurora/policies.yaml

# Budget policies (migrated from existing budget config)
budget:
  monthly_limit_usd: 100.0
  warn_at_percent: 80
  hard_limit_action: reject  # reject | warn

# Agent recovery policies
agent_recovery:
  timeout_seconds: 120
  max_retries: 2
  fallback_to_llm: true

# Destructive operation policies
destructive:
  file_delete:
    action: prompt           # prompt | allow | deny
    max_files: 5             # Prompt if deleting more than N files

  git_force_push:
    action: deny             # Never allow force push

  git_push_main:
    action: prompt           # Prompt before pushing to main/master

  drop_table:
    action: deny             # Never allow DROP TABLE

  truncate:
    action: prompt           # Prompt before TRUNCATE

# Safety policies
safety:
  auto_branch: true          # Create feature branch before changes
  branch_prefix: "aurora/"   # Branch naming: aurora/goal-slug

  max_files_modified: 20     # Anomaly if exceeds
  max_lines_changed: 1000    # Anomaly if exceeds

  protected_paths:           # Never modify these
    - ".git/"
    - "node_modules/"
    - "vendor/"
    - ".env"
    - "*.pem"
    - "*.key"

# Anomaly detection
anomalies:
  scope_multiplier: 3        # Alert if scope > 3x expected
  unexpected_file_types:     # Alert if modifying these
    - "*.sql"
    - "*.sh"
    - "Dockerfile"
```

**API**:
```python
class PoliciesEngine:
    def __init__(self, policies_path: Path | None = None):
        """Load policies from .aurora/policies.yaml or defaults."""

    def check_operation(self, operation: Operation) -> PolicyResult:
        """Check if operation is allowed.

        Returns:
            PolicyResult with action (ALLOW|PROMPT|DENY) and reason
        """

    def check_budget(self, estimated_cost: float) -> PolicyResult:
        """Check if cost is within budget."""

    def check_scope(self, files_modified: int, lines_changed: int) -> PolicyResult:
        """Check if scope is within limits."""

    def get_protected_paths(self) -> list[str]:
        """Return list of protected path patterns."""
```

**Operation types**:
```python
@dataclass
class Operation:
    type: OperationType  # FILE_DELETE | GIT_PUSH | GIT_FORCE_PUSH | SQL_DROP | etc.
    target: str          # File path, branch name, table name
    count: int = 1       # Number of items affected
    metadata: dict = field(default_factory=dict)
```

### 4.5 Module: CheckpointManager

**Purpose**: Save execution state for resume after interruption.

**Used by**: `aur spawn`

**Checkpoint file**: `.aurora/checkpoints/<execution-id>.json`

```json
{
  "execution_id": "spawn-1705234567",
  "plan_id": "0004-add-caching-plandecomposer",
  "started_at": "2026-01-14T10:30:00Z",
  "tasks": [
    {"id": "sg-1", "status": "completed", "result": "..."},
    {"id": "sg-2", "status": "completed", "result": "..."},
    {"id": "sg-3", "status": "in_progress", "started_at": "..."},
    {"id": "sg-4", "status": "pending"},
    {"id": "sg-5", "status": "pending"}
  ],
  "last_checkpoint": "2026-01-14T10:35:00Z",
  "interrupted": false
}
```

**API**:
```python
class CheckpointManager:
    def __init__(self, execution_id: str, plan_id: str):
        ...

    def save(self, tasks: list[TaskState]) -> None:
        """Save current state to checkpoint file."""

    def load(self, execution_id: str) -> CheckpointState | None:
        """Load checkpoint if exists."""

    def mark_interrupted(self) -> None:
        """Mark execution as interrupted (Ctrl+C handler)."""

    def get_resume_point(self) -> int:
        """Return index of first non-completed task."""

    @classmethod
    def list_resumable(cls) -> list[CheckpointState]:
        """List all checkpoints that can be resumed."""
```

**CLI integration**:
```bash
# Normal execution (creates checkpoint)
aur spawn tasks.md

# Resume from checkpoint
aur spawn --resume spawn-1705234567

# List resumable executions
aur spawn --list-checkpoints

# Clean old checkpoints
aur spawn --clean-checkpoints
```

### 4.6 Task Execution & Failure Handling

**Purpose**: Show real-time status during execution and handle failures with user prompts.

#### 4.6.1 Streaming Status Display

During execution, show parent task context and current progress:

```
╭──────────────────── Executing ────────────────────╮
│ Parent: Improve memory indexing performance       │
│                                                   │
│ Progress: [████████░░░░░░░░░░░░] 2/6              │
│                                                   │
│ Current: Identify bottlenecks in BM25 scoring     │
│ Agent: @code-developer                            │
│ Status: Running (45s)                             │
╰───────────────────────────────────────────────────╯
```

On completion, update in place:
```
│ Current: Identify bottlenecks in BM25 scoring     │
│ Agent: @code-developer                            │
│ Status: Completed (67s)                           │
```

#### 4.6.2 Failure Handling

When a task fails (timeout, error, agent unavailable), pause execution and prompt:

```
╭──────────────────── Task Failed ────────────────────╮
│ Parent: Improve memory indexing performance         │
│                                                     │
│ Failed: Optimize embedding generation               │
│ Agent: performance-engineer                         │
│ Error: Agent timeout after 120s (attempt 2/2)       │
│                                                     │
│ Completed: 2/6                                      │
│ Remaining: 3 tasks (depend on this task: 1)         │
╰─────────────────────────────────────────────────────╯

Options:
  [R]etry    - Retry with same agent
  [S]kip     - Skip and continue (may break dependents)
  [F]allback - Use LLM directly for this task
  [A]bort    - Save checkpoint and exit

Choice [R/s/f/a]:
```

#### 4.6.3 Implementation: Pause-on-Failure Pattern

Use ThreadPoolExecutor with synchronized failure handling:

```python
class TaskExecutor:
    def __init__(self, policies: PoliciesEngine, checkpoint: CheckpointManager):
        self.policies = policies
        self.checkpoint = checkpoint
        self.pending_failures: list[FailedTask] = []
        self._failure_lock = threading.Lock()

    def execute_tasks(self, tasks: list[Task], max_parallel: int = 5) -> ExecutionResult:
        """Execute tasks with parallel processing and synchronized failure handling."""
        executor = ThreadPoolExecutor(max_workers=max_parallel)
        pending_tasks = list(tasks)
        futures: dict[Future, Task] = {}
        results: list[TaskResult] = []

        while pending_tasks or futures:
            # Don't start new tasks if failure pending user decision
            if not self.pending_failures:
                # Submit tasks up to max_parallel
                while len(futures) < max_parallel and pending_tasks:
                    task = pending_tasks.pop(0)
                    future = executor.submit(self._execute_single, task)
                    futures[future] = task

            # Wait for any task to complete
            if futures:
                done, _ = wait(futures.keys(), timeout=1.0, return_when=FIRST_COMPLETED)

                for future in done:
                    task = futures.pop(future)
                    try:
                        result = future.result()
                        results.append(result)
                        self.checkpoint.save(tasks)
                    except TaskFailure as e:
                        with self._failure_lock:
                            self.pending_failures.append(FailedTask(task, e))

            # Handle failures when queue is empty (all running tasks finished)
            if self.pending_failures and not futures:
                decision = self._prompt_failure(self.pending_failures[0])

                if decision == FailureDecision.RETRY:
                    pending_tasks.insert(0, self.pending_failures[0].task)
                elif decision == FailureDecision.SKIP:
                    results.append(TaskResult(task, status="skipped"))
                elif decision == FailureDecision.FALLBACK:
                    # Execute with LLM directly
                    result = self._execute_fallback(self.pending_failures[0].task)
                    results.append(result)
                elif decision == FailureDecision.ABORT:
                    self.checkpoint.mark_interrupted()
                    raise ExecutionAborted(results)

                self.pending_failures.pop(0)

        return ExecutionResult(results)

    def _execute_single(self, task: Task) -> TaskResult:
        """Execute single task with recovery."""
        recovery = AgentRecovery(self.policies.agent_recovery)
        return recovery.execute_with_recovery(task.agent, task.description)

    def _execute_fallback(self, task: Task) -> TaskResult:
        """Execute task with direct LLM call."""
        # ... direct LLM invocation

    def _prompt_failure(self, failed: FailedTask) -> FailureDecision:
        """Display failure and prompt user for decision."""
        self._display_failure(failed)
        return self._read_decision()
```

**Key behaviors**:
- Running tasks finish before prompting (no orphan processes)
- New tasks paused while failure pending
- Synchronous prompt ensures single user interaction at a time
- Checkpoint saved after each successful task

---

## 5. Integration Points

### 5.1 aur goals

```python
# Current flow (keep):
decompose() → display_summary() → prompt_for_confirmation() → write_files()

# Enhanced flow:
decompose()
  → DecompositionReview(subgoals, gaps).display()
  → DecompositionReview.prompt()  # Returns PROCEED|SPAWN|ABORT
  → if SPAWN: spawn_missing_agents()
  → write_files()
```

### 5.2 aur soar

```python
# Current flow:
phase5_collect():
    for subgoal in subgoals:
        result = execute_agent(agent_id, task)  # 300s timeout, retry, fallback

# Enhanced flow:
phase5_collect():
    recovery = AgentRecovery(policies.agent_recovery)
    for subgoal in subgoals:
        result = recovery.execute_with_recovery(agent_id, task, llm_client)
```

### 5.3 aur spawn

```python
# Current flow:
for task in tasks:
    execute_task(task)  # No checkpoints, no policies

# Enhanced flow:
def spawn_with_controls(tasks_file: Path, resume_from: str | None = None):
    policies = PoliciesEngine()
    checkpoint = CheckpointManager(execution_id, plan_id)
    recovery = AgentRecovery(policies.agent_recovery)

    # Show decomposition review first
    review = DecompositionReview(subgoals, agent_gaps)
    review.display()
    decision = review.prompt()
    if decision == ABORT:
        return
    if decision == SPAWN:
        spawn_missing_agents(agent_gaps)

    # Resume from checkpoint if specified
    start_index = 0
    if resume_from:
        state = checkpoint.load(resume_from)
        start_index = state.get_resume_point()

    # Execute with checkpoints and policies
    try:
        for i, task in enumerate(tasks[start_index:], start_index):
            # Check policies
            policy_result = policies.check_operation(task.operation)
            if policy_result.action == DENY:
                raise PolicyViolation(policy_result.reason)
            if policy_result.action == PROMPT:
                if not prompt_user(policy_result.reason):
                    continue  # Skip this task

            # Execute with recovery
            result = recovery.execute_with_recovery(task.agent, task.description, llm)

            # Save checkpoint
            checkpoint.save(tasks)

    except KeyboardInterrupt:
        checkpoint.mark_interrupted()
        print(f"\nInterrupted. Resume with: aur spawn --resume {execution_id}")
```

---

## 6. CLI Changes

### 6.1 aur spawn

```bash
# New flags
aur spawn tasks.md [OPTIONS]

Options:
  --yes, -y              Skip decomposition review prompt
  --resume ID            Resume from checkpoint
  --list-checkpoints     List resumable executions
  --clean-checkpoints    Remove old checkpoint files
  --no-checkpoint        Disable checkpoint creation
  --policy FILE          Use custom policies file
```

### 6.2 aur soar

```bash
# No new flags needed - uses policies.yaml automatically
# Agent recovery configured via policies.yaml
```

### 6.3 aur goals

```bash
# Enhanced display, no new flags needed
# DecompositionReview replaces current summary display
```

---

## 7. File Structure

```
packages/
├── cli/src/aurora_cli/
│   ├── policies/                    # NEW: Policies module
│   │   ├── __init__.py
│   │   ├── engine.py                # PoliciesEngine
│   │   ├── models.py                # Operation, PolicyResult
│   │   └── defaults.py              # Default policies
│   │
│   ├── execution/                   # NEW: Execution control
│   │   ├── __init__.py
│   │   ├── checkpoint.py            # CheckpointManager
│   │   ├── recovery.py              # AgentRecovery
│   │   └── review.py                # DecompositionReview
│   │
│   └── commands/
│       ├── goals.py                 # Use DecompositionReview
│       ├── soar.py                  # Use AgentRecovery
│       └── spawn.py                 # Use all modules
│
└── .aurora/
    ├── policies.yaml                # User policies config
    └── checkpoints/                 # Checkpoint files
        └── spawn-*.json
```

---

## 8. Migration

### 8.1 Budget Migration

Current budget config in `.aurora/config.yaml`:
```yaml
budget:
  monthly_limit_usd: 100
```

Migrate to `.aurora/policies.yaml`:
```yaml
budget:
  monthly_limit_usd: 100
  warn_at_percent: 80
  hard_limit_action: reject
```

**Migration strategy**:
- Check for old config location
- Auto-migrate on first run
- Log deprecation warning

### 8.2 Backward Compatibility

- `--yes` flag continues to work (skips all prompts)
- Existing `aur goals` flow unchanged if no gaps
- `aur spawn` without flags works as before (but with checkpoints)

---

## 9. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Agent failure recovery time | 600s+ | <300s |
| Execution visibility | None | Full decomposition review |
| Resume after Ctrl+C | Not possible | Resume from last task |
| Policy violations caught | 0% | 100% (blocked or prompted) |

---

## 10. Implementation Phases

### Phase 1: Agent Recovery (High Impact, Low Effort)
- [ ] Create `AgentRecovery` module
- [ ] Integrate with `aur soar` Phase 5
- [ ] Add recovery config to policies.yaml
- [ ] Test: 120s timeout, 2 retries, fallback

### Phase 2: Policies Engine (Foundation)
- [ ] Create `PoliciesEngine` module
- [ ] Define default policies
- [ ] Migrate budget to policies.yaml
- [ ] Add destructive operation checks

### Phase 3: Decomposition Review (User Visibility)
- [ ] Create `DecompositionReview` module
- [ ] Replace current `aur goals` summary
- [ ] Add to `aur spawn` before execution
- [ ] Add spawn-on-fly option for gaps

### Phase 4: Checkpoint/Resume (Reliability)
- [ ] Create `CheckpointManager` module
- [ ] Integrate with `aur spawn`
- [ ] Add --resume flag
- [ ] Handle Ctrl+C gracefully

### Phase 5: Integration & Polish
- [ ] End-to-end testing
- [ ] Documentation
- [ ] Migration tooling
- [ ] Performance validation

---

## 11. Open Questions

1. **Checkpoint storage**: JSON files vs SQLite vs same memory.db?
2. **Policy inheritance**: Global (~/.aurora/policies.yaml) + project-level merge?
3. **Anomaly thresholds**: What are sensible defaults for scope limits?
4. **Agent spawn timeout**: 120s enough for ad-hoc agent creation?

---

## 12. References

- FEATURES_BACKLOG.md: Pillar 3, 4, 5 definitions
- Current checkpoint.py: Existing confirmation logic
- Current budget.py: Existing budget tracking
