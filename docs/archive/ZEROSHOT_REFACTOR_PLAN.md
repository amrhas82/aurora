# Zeroshot → Aurora Python Refactor Plan

## Overview

Port Zeroshot's agent spawning and orchestration capabilities from JavaScript to Python, integrating with Aurora's existing architecture.

**Repository:** https://github.com/amrhas82/zeroshot
**Target Branch:** `refactored`
**Output Directory:** `/aurora_refac_zeroshot/`
**Timeline:** 4-6 weeks
**Total Lines:** ~2100 lines JavaScript → Python

---

## What We're Porting

### Priority 2: Agent Spawning (~1300 lines)

| Source File | Lines | Target File | Purpose |
|-------------|-------|-------------|---------|
| `src/agent/agent-task-executor.js` | 300 | `executor.py` | Execute tasks with Claude CLI |
| `src/claude-task-runner.js` | 200 | `runner.py` | Spawn subprocess, capture output |
| `src/agent/agent-lifecycle.js` | 250 | `lifecycle.py` | Start/stop/retry/state management |
| `src/agent-wrapper.js` | 150 | `wrapper.py` | Agent abstraction layer |
| `src/ledger.js` | 250 | `ledger.py` | SQLite persistence for pause/resume |
| `src/agent/agent-stuck-detector.js` | 150 | `health.py` | Process health monitoring |

### Priority 3: Plan Executor (~800 lines)

| Source File | Lines | Target File | Purpose |
|-------------|-------|-------------|---------|
| `src/orchestrator.js` | 500 | `orchestrator.py` | Multi-agent coordination |
| `src/agent/agent-context-builder.js` | 100 | `context.py` | Build agent context/prompts |
| `src/config-validator.js` | 100 | `validator.py` | Config validation |
| `src/preflight.js` | 100 | `preflight.py` | Pre-execution safety checks |

### Optional: Message Bus (~300 lines)

| Source File | Lines | Target File | Purpose |
|-------------|-------|-------------|---------|
| `src/message-bus.js` | 300 | `bus.py` | Pub/sub for parallel agents |

**Decision:** Port message bus in Phase 2 if parallel execution is needed.

---

## Output Structure

```
aurora_refac_zeroshot/
├── src/
│   ├── agent_spawning/
│   │   ├── __init__.py
│   │   ├── executor.py          # agent-task-executor.js
│   │   ├── runner.py             # claude-task-runner.js
│   │   ├── lifecycle.py          # agent-lifecycle.js
│   │   ├── wrapper.py            # agent-wrapper.js
│   │   ├── ledger.py             # ledger.js
│   │   └── health.py             # agent-stuck-detector.js
│   │
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # orchestrator.js
│   │   ├── context.py            # agent-context-builder.js
│   │   ├── validator.py          # config-validator.js
│   │   └── preflight.py          # preflight.js
│   │
│   ├── bus/                      # Optional Phase 2
│   │   ├── __init__.py
│   │   └── bus.py                # message-bus.js
│   │
│   └── models/
│       ├── __init__.py
│       ├── agent.py              # Agent models
│       ├── task.py               # Task models
│       └── result.py             # Result models
│
├── tests/
│   ├── unit/
│   │   ├── test_executor.py
│   │   ├── test_runner.py
│   │   ├── test_lifecycle.py
│   │   ├── test_wrapper.py
│   │   ├── test_ledger.py
│   │   ├── test_health.py
│   │   ├── test_orchestrator.py
│   │   ├── test_context.py
│   │   ├── test_validator.py
│   │   └── test_preflight.py
│   │
│   ├── integration/
│   │   ├── test_agent_spawning.py
│   │   ├── test_orchestration.py
│   │   └── test_pause_resume.py
│   │
│   └── fixtures/
│       ├── test_agents.json
│       ├── test_tasks.json
│       └── mock_claude_output.txt
│
├── docs/
│   ├── PORTING_NOTES.md
│   ├── API.md
│   └── ARCHITECTURE.md
│
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## Phase 1: Agent Spawning Core (Week 1-2)

### Step 1.1: Repository Setup (Day 1)

**Tasks:**
- [x] Fork zeroshot → https://github.com/amrhas82/zeroshot
- [ ] Create `refactored` branch
- [ ] Create `/aurora_refac_zeroshot/` directory structure
- [ ] Setup pyproject.toml with dependencies
- [ ] Setup pytest configuration
- [ ] Create initial README.md

**Dependencies:**
```toml
[tool.poetry.dependencies]
python = "^3.10"
pydantic = "^2.0"
click = "^8.1"
psutil = "^6.0"  # For process monitoring
```

### Step 1.2: Port Claude Task Runner (Day 2-3)

**Source:** `src/claude-task-runner.js` (200 lines)
**Target:** `src/agent_spawning/runner.py`

**Key Functions:**
```python
class ClaudeTaskRunner:
    """Spawns Claude CLI and captures output."""

    def spawn_task(
        self,
        task: str,
        model: str = "sonnet",
        output_format: str = "json",
        timeout: int = 3600
    ) -> TaskResult:
        """Spawn Claude CLI subprocess."""
        pass

    def follow_logs(self, task_id: str) -> Generator[str, None, None]:
        """Stream task logs in real-time."""
        pass

    def parse_result(self, output: str) -> dict:
        """Parse NDJSON output from Claude."""
        pass
```

**Tests:**
- `tests/unit/test_runner.py`
- Mock subprocess.run
- Test output parsing
- Test timeout handling

### Step 1.3: Port Agent Task Executor (Day 4-5)

**Source:** `src/agent/agent-task-executor.js` (300 lines)
**Target:** `src/agent_spawning/executor.py`

**Key Functions:**
```python
class AgentTaskExecutor:
    """Executes tasks with retry logic."""

    def execute_task(
        self,
        agent: AgentInfo,
        task: Task,
        context: dict,
        max_retries: int = 2
    ) -> ExecutionResult:
        """Execute task with exponential backoff retry."""
        pass

    def validate_result(
        self,
        result: ExecutionResult,
        schema: dict | None = None
    ) -> bool:
        """Validate result against JSON schema."""
        pass
```

**Tests:**
- `tests/unit/test_executor.py`
- Test retry logic
- Test schema validation
- Test error handling

### Step 1.4: Port Agent Lifecycle (Day 6-7)

**Source:** `src/agent/agent-lifecycle.js` (250 lines)
**Target:** `src/agent_spawning/lifecycle.py`

**Key Functions:**
```python
class AgentLifecycle:
    """Manages agent state transitions."""

    def start(self, agent: Agent) -> None:
        """Start agent, set state to idle."""
        pass

    def execute(self, agent: Agent, task: Task) -> None:
        """Execute task, set state to executing."""
        pass

    def stop(self, agent: Agent, timeout: int = 5) -> None:
        """Gracefully stop agent."""
        pass
```

**Tests:**
- `tests/unit/test_lifecycle.py`
- Test state transitions
- Test graceful shutdown
- Test timeout handling

### Step 1.5: Port Agent Wrapper (Day 8)

**Source:** `src/agent-wrapper.js` (150 lines)
**Target:** `src/agent_spawning/wrapper.py`

**Key Classes:**
```python
class AgentWrapper:
    """Wraps agent with config and context."""

    def __init__(
        self,
        agent_info: AgentInfo,
        executor: AgentTaskExecutor,
        lifecycle: AgentLifecycle
    ):
        pass

    def execute(self, task: Task) -> ExecutionResult:
        """Execute task through lifecycle."""
        pass
```

**Tests:**
- `tests/unit/test_wrapper.py`
- Test config injection
- Test execution flow

### Step 1.6: Port State Ledger (Day 9-10)

**Source:** `src/ledger.js` (250 lines)
**Target:** `src/agent_spawning/ledger.py`

**Key Functions:**
```python
class StateLedger:
    """SQLite persistence for pause/resume."""

    def __init__(self, db_path: Path):
        """Initialize with WAL mode."""
        pass

    def record_event(
        self,
        event_type: str,
        data: dict,
        timestamp: float | None = None
    ) -> None:
        """Record event to ledger."""
        pass

    def query_events(
        self,
        event_type: str | None = None,
        since: float | None = None
    ) -> list[dict]:
        """Query events with filters."""
        pass

    def get_last_checkpoint(self) -> dict | None:
        """Get last execution checkpoint for resume."""
        pass
```

**Tests:**
- `tests/unit/test_ledger.py`
- Test WAL mode
- Test event recording
- Test resume queries
- Integration test: `tests/integration/test_pause_resume.py`

### Step 1.7: Port Health Monitor (Day 11)

**Source:** `src/agent/agent-stuck-detector.js` (150 lines)
**Target:** `src/agent_spawning/health.py`

**Key Functions:**
```python
class AgentHealthMonitor:
    """Monitors agent process health."""

    def check_health(self, pid: int) -> HealthStatus:
        """Check process CPU, I/O, context switches."""
        pass

    def is_stuck(
        self,
        pid: int,
        threshold_seconds: int = 300
    ) -> bool:
        """Detect hung processes."""
        pass
```

**Tests:**
- `tests/unit/test_health.py`
- Mock psutil
- Test stuck detection

### Step 1.8: Integration Testing (Day 12-14)

**Tests:**
- `tests/integration/test_agent_spawning.py`
  - End-to-end: spawn agent, execute task, capture result
  - Test with actual `claude` CLI (if available)
  - Test pause/resume with ledger
  - Test retry logic
  - Test timeout handling
  - Test error scenarios

---

## Phase 2: Orchestration (Week 3-4)

### Step 2.1: Port Orchestrator (Day 15-18)

**Source:** `src/orchestrator.js` (500 lines)
**Target:** `src/execution/orchestrator.py`

**Key Functions:**
```python
class Orchestrator:
    """Coordinates multiple agents."""

    def __init__(
        self,
        agents: list[Agent],
        ledger: StateLedger
    ):
        pass

    def execute_plan(
        self,
        plan: Plan,
        sequential: bool = True
    ) -> OrchestrationResult:
        """Execute plan tasks with agents."""
        pass

    def resume_execution(
        self,
        checkpoint: dict
    ) -> OrchestrationResult:
        """Resume from last checkpoint."""
        pass
```

**Tests:**
- `tests/unit/test_orchestrator.py`
- `tests/integration/test_orchestration.py`

### Step 2.2: Port Context Builder (Day 19)

**Source:** `src/agent/agent-context-builder.js` (100 lines)
**Target:** `src/execution/context.py`

**Key Functions:**
```python
class ContextBuilder:
    """Builds agent execution context."""

    def build_context(
        self,
        agent: AgentInfo,
        task: Task,
        memory_chunks: list[Chunk]
    ) -> str:
        """Build system prompt with context."""
        pass
```

**Tests:**
- `tests/unit/test_context.py`

### Step 2.3: Port Config Validator (Day 20)

**Source:** `src/config-validator.js` (100 lines)
**Target:** `src/execution/validator.py`

**Tests:**
- `tests/unit/test_validator.py`

### Step 2.4: Port Preflight Checks (Day 21)

**Source:** `src/preflight.js` (100 lines)
**Target:** `src/execution/preflight.py`

**Tests:**
- `tests/unit/test_preflight.py`

### Step 2.5: Integration Testing (Day 22-24)

**Tests:**
- End-to-end orchestration test
- Multi-agent coordination
- Sequential vs parallel execution (if bus added)

---

## Phase 3: Optional Message Bus (Week 5)

**Decision Point:** Do we need parallel execution?

If YES:
- Port `src/message-bus.js` → `src/bus/bus.py`
- Add pub/sub capabilities
- Update orchestrator to use bus

If NO:
- Skip to Phase 4

---

## Phase 4: Integration with Aurora (Week 6)

### Step 4.1: Create Bridge Module

```python
# packages/cli/src/aurora_cli/execution/zeroshot_bridge.py

from aurora_refac_zeroshot.src.execution import Orchestrator
from aurora_refac_zeroshot.src.agent_spawning import AgentWrapper

def execute_aurora_plan(
    plan_id: str,
    manifest: AgentManifest,
    memory_chunks: list[Chunk]
) -> ExecutionResult:
    """Execute Aurora plan using refactored Zeroshot."""

    # Load plan
    plan = load_plan(plan_id)

    # Match agents
    agents = match_agents(plan.tasks, manifest)

    # Create orchestrator
    orchestrator = Orchestrator(
        agents=agents,
        ledger=StateLedger(Path(f".aurora/execution/{plan_id}/ledger.db"))
    )

    # Execute
    return orchestrator.execute_plan(plan)
```

### Step 4.2: Add CLI Command

```python
# packages/cli/src/aurora_cli/commands/plan_execute.py

@click.command()
@click.argument("plan_id")
def execute_command(plan_id: str):
    """Execute plan with agent spawning."""
    result = execute_aurora_plan(plan_id, manifest, chunks)
    # Display results
```

### Step 4.3: End-to-End Testing

- Create test plan in `.aurora/plans/`
- Execute with `aur plan execute`
- Verify agent spawning
- Verify pause/resume
- Verify results cached to memory

---

## Testing Strategy

### Unit Tests (Target: 80% coverage)

For each ported file:
- Test all public functions
- Mock external dependencies (subprocess, SQLite)
- Test error paths
- Test edge cases

### Integration Tests

- Agent spawning end-to-end
- Orchestration with multiple agents
- Pause/resume functionality
- Error recovery

### Test Data

Port relevant fixtures from Zeroshot:
- `tests/fixtures/` → Mock agent configs, task outputs

---

## Success Criteria

### Phase 1 Complete
- [ ] All agent spawning modules ported
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration test: spawn agent, execute task, get result
- [ ] Pause/resume works (ledger test)

### Phase 2 Complete
- [ ] Orchestrator ported
- [ ] Can execute multi-task plan
- [ ] Context builder integrates with Aurora memory

### Phase 3 Complete (if needed)
- [ ] Message bus ported
- [ ] Parallel execution works

### Phase 4 Complete
- [ ] Aurora integration working
- [ ] `aur plan execute` command works
- [ ] End-to-end test passes

---

## Risk Mitigation

### Risk 1: Claude CLI differences
**Mitigation:** Mock subprocess in tests, document assumptions

### Risk 2: SQLite incompatibilities
**Mitigation:** Test on multiple platforms, use standard WAL mode

### Risk 3: Process monitoring varies by OS
**Mitigation:** Use psutil for cross-platform compatibility

### Risk 4: Missing edge cases
**Mitigation:** Port Zeroshot's test suite patterns

---

## Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.10"
pydantic = "^2.0"
click = "^8.1"
psutil = "^6.0"
sqlalchemy = "^2.0"  # For SQLite
pytest = "^8.0"
pytest-asyncio = "^0.23"
pytest-mock = "^3.12"
```

---

## Next Steps

1. **Review this plan** - Approve or request changes
2. **Create refactored branch** - In forked repo
3. **Setup skeleton** - Create directory structure, pyproject.toml
4. **Start Phase 1** - Begin with Claude Task Runner

**Ready to start? Should I:**
- A) Create the refactored branch structure?
- B) Start with Step 1.1 (Repository Setup)?
- C) Refine the plan first?
