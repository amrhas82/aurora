# aur spawn

Execute tasks from markdown task files in parallel or sequentially.

## Synopsis

```bash
aur spawn [OPTIONS] [TASK_FILE]
```

## Description

The `aur spawn` command loads tasks from a markdown checklist file and executes them using the aurora-spawner package. Tasks can be executed in parallel (default) or sequentially, with support for agent assignment and dependency management.

**Shared Infrastructure**: Uses `spawn_parallel_tracked()` - the same mature spawning infrastructure as `aur soar`. This ensures consistent behavior for stagger delays, heartbeat monitoring, circuit breaker protection, and timeout policies across all Aurora commands.

## Usage

### Basic Usage

```bash
# Execute tasks.md in current directory
aur spawn

# Execute specific task file
aur spawn path/to/tasks.md

# Execute with options
aur spawn tasks.md --sequential --verbose
```

### Task File Format

Tasks follow standard markdown checklist format with HTML comment metadata:

```markdown
# Task List

- [ ] 1. Task description
<!-- agent: agent-name -->
<!-- depends: previous-task-id -->

- [x] 2. Completed task
<!-- agent: self -->
```

**Task Format Elements:**

- `- [ ]` or `- [x]` - Checkbox (pending or completed)
- `ID` - Task identifier (e.g., `1`, `1.1`, `1.2.3`)
- `Description` - Natural language task description
- `<!-- agent: name -->` - Agent assignment (optional)
- `<!-- depends: id -->` - Task dependency (optional)

## Options

### `[TASK_FILE]`

Path to task file (default: `tasks.md` in current directory)

**Examples:**
```bash
aur spawn                          # Use ./tasks.md
aur spawn mytasks.md               # Use ./mytasks.md
aur spawn /path/to/tasks.md        # Absolute path
aur spawn ../other/tasks.md        # Relative path
```

### `--parallel` / `--no-parallel`

Execute tasks in parallel (default: `--parallel`)

- **Parallel mode**: Executes up to 4 tasks concurrently (configurable via `--max-concurrent`)
- **Sequential mode**: Executes one task at a time

```bash
aur spawn --parallel              # Parallel execution (default)
aur spawn --no-parallel           # Sequential execution
```

### `--max-concurrent`

Maximum number of concurrent tasks (default: 4).

```bash
aur spawn --max-concurrent 2      # Conservative parallelism
aur spawn --max-concurrent 6      # Higher throughput
```

### `--stagger-delay`

Delay in seconds between starting tasks (default: 5.0). Prevents API rate limit bursts.

```bash
aur spawn --stagger-delay 3       # Faster start
aur spawn --stagger-delay 10      # More conservative
```

### `--policy`

Timeout policy preset (default: `patient`).

| Policy | Initial | Max | Use Case |
|--------|---------|-----|----------|
| `patient` | 120s | 600s | Complex tasks (default) |
| `default` | 60s | 300s | Balanced |
| `fast_fail` | 60s | 60s | Quick feedback |
| `production` | 120s | 600s | Production workloads |
| `development` | 1800s | 1800s | Debugging |

```bash
aur spawn --policy patient        # Default - complex tasks
aur spawn --policy fast_fail      # Quick validation
```

### `--no-fallback`

Disable LLM fallback when agents fail. By default, failed agents retry then fall back to direct LLM execution.

```bash
aur spawn --no-fallback           # Fail if agent fails (no LLM fallback)
```

### `--sequential`

Force sequential execution (overrides `--parallel`)

```bash
aur spawn --sequential            # Execute one at a time
```

**Use when:**
- Tasks have implicit dependencies
- Resources are limited
- Debugging execution order issues

### `--verbose`, `-v`

Show detailed output during execution

```bash
aur spawn --verbose               # Show progress details
aur spawn -v                      # Short form
```

**Output includes:**
- Task loading confirmation
- Execution mode (parallel/sequential)
- Per-task progress updates
- Completion status for each task
- Final summary statistics

### `--dry-run`

Parse and validate tasks without executing them

```bash
aur spawn --dry-run               # Validate only
```

**Use for:**
- Verifying task file syntax
- Checking agent assignments
- Previewing task list before execution
- Testing task file changes

## Examples

### Example 1: Basic Parallel Execution

```bash
aur spawn tasks.md
```

Executes all tasks in `tasks.md` in parallel (up to 4 concurrent, 5s stagger delay).

### Example 2: Sequential with Verbose Output

```bash
aur spawn tasks.md --sequential --verbose
```

Executes tasks one at a time with detailed progress output.

### Example 3: Dry-Run Validation

```bash
aur spawn complex-tasks.md --dry-run
```

Validates task file format and shows what would be executed.

### Example 4: Custom Task File

```bash
aur spawn ~/projects/myapp/implementation-tasks.md --verbose
```

Executes tasks from a specific location with progress details.

### Example 5: Production Configuration

```bash
aur spawn tasks.md --max-concurrent 2 --stagger-delay 10 --policy production
```

Conservative settings for production workloads.

### Example 6: Fast Validation

```bash
aur spawn tasks.md --policy fast_fail --no-fallback --dry-run
```

Quick validation with strict failure handling.

## Agent Assignment

Tasks can specify which agent should handle them using HTML comments:

```markdown
- [ ] 1. Research topic
<!-- agent: researcher -->

- [ ] 2. Implement feature
<!-- agent: developer -->

- [ ] 3. Write tests
<!-- agent: test-engineer -->

- [ ] 4. Update docs
<!-- agent: self -->
```

**Agent Types:**

- `self` - Execute in current context (no spawning)
- `agent-id` - Spawn specific agent from your agent registry

**View Available Agents:**

```bash
aur agents list
```

## Task Dependencies

Tasks can declare dependencies using HTML comments:

```markdown
- [ ] 1. Setup database
<!-- agent: self -->

- [ ] 2. Run migrations
<!-- agent: self -->
<!-- depends: 1 -->

- [ ] 3. Seed test data
<!-- agent: self -->
<!-- depends: 2 -->
```

**Dependency Behavior:**

- Tasks with dependencies execute after their dependencies complete
- Tasks without dependencies can run in parallel
- Circular dependencies are not supported
- Failed dependencies block dependent tasks

## Exit Status

- `0` - All tasks completed successfully
- `1` - One or more tasks failed
- `2` - Invalid task file or command error

## Output Format

### Standard Output

```
Loaded 5 tasks from tasks.md
Executing tasks in parallel...

[cyan]✓[/] Task 1: Success
[cyan]✓[/] Task 2: Success
[red]✗[/] Task 3: Failed - timeout
[cyan]✓[/] Task 4: Success
[cyan]✓[/] Task 5: Success

[bold green]Completed:[/] 4/5
[bold red]Failed:[/] 1
```

### Verbose Output

```
Loaded 4 tasks from tasks.md
Executing 4 tasks in parallel (max_concurrent=4, policy=patient, stagger=5.0s)...

[green]✓[/] Task 1: Success
[green]✓[/] Task 2: Success (fallback)
[red]✗[/] Task 3: Failed - timeout
[green]✓[/] Task 4: Success

Fallbacks used: 1
```

## Task File Examples

### Simple Task List

```markdown
# Daily Tasks

- [ ] 1. Review pull requests
<!-- agent: self -->

- [ ] 2. Update documentation
<!-- agent: self -->

- [ ] 3. Run security scan
<!-- agent: self -->
```

### Complex Workflow

```markdown
# Feature Implementation

- [ ] 1. Design API endpoints
<!-- agent: architect -->

- [ ] 2. Implement endpoints
<!-- agent: backend-dev -->
<!-- depends: 1 -->

- [ ] 3. Write API tests
<!-- agent: test-engineer -->
<!-- depends: 2 -->

- [ ] 4. Create frontend components
<!-- agent: frontend-dev -->
<!-- depends: 1 -->

- [ ] 5. Write E2E tests
<!-- agent: test-engineer -->
<!-- depends: 3,4 -->

- [ ] 6. Update documentation
<!-- agent: doc-writer -->
<!-- depends: 2,4 -->
```

## Integration

### With aur soar

Use soar to plan tasks, then execute with spawn:

```bash
# Generate task plan
aur soar "Plan tasks for user authentication" > auth-tasks.md

# Execute planned tasks
aur spawn auth-tasks.md --verbose
```

### With aur agents

Discover available agents before writing task files:

```bash
# List agents
aur agents list

# Use discovered agents in task file
cat > tasks.md << 'EOF'
- [ ] 1. Research authentication methods
<!-- agent: researcher -->
EOF

aur spawn tasks.md
```

## Architecture

### Shared Infrastructure with aur soar

Both `aur spawn` and `aur soar` use `spawn_parallel_tracked()` from `aurora_spawner`:

```
┌─────────────┐     ┌─────────────┐
│  aur spawn  │     │  aur soar   │
│  (CLI)      │     │  (CLI)      │
└──────┬──────┘     └──────┬──────┘
       │                   │
       ▼                   ▼
┌────────────────────────────────────┐
│     spawn_parallel_tracked()       │
│     (aurora_spawner.spawner)       │
├────────────────────────────────────┤
│ - Stagger delays (5s default)      │
│ - Per-task heartbeat monitoring    │
│ - Global timeout calculation       │
│ - Circuit breaker pre-checks       │
│ - Retry + LLM fallback             │
│ - Execution metadata tracking      │
└────────────────────────────────────┘
```

**Benefits**:
- Single source of truth for spawning logic
- Bug fixes and improvements apply to both commands
- Consistent behavior across all Aurora parallel execution

### Execution Flow

```
1. Parse tasks from markdown file
2. Convert to SpawnTask objects
3. Circuit breaker pre-check (skip known-failing agents)
4. Start tasks with stagger delay (idx * 5s)
5. Per-task heartbeat monitoring (detect stuck/failed agents)
6. Global timeout = (waves * policy_max) + stagger_total + 120s buffer
7. Retry failed tasks (max 2 attempts)
8. Fallback to LLM if agent exhausts retries
9. Return results + metadata
```

### Key Parameters

| Parameter | Default | Source |
|-----------|---------|--------|
| `max_concurrent` | 4 | CLI `--max-concurrent` |
| `stagger_delay` | 5.0s | CLI `--stagger-delay` |
| `policy` | patient | CLI `--policy` |
| `fallback_to_llm` | true | CLI `--no-fallback` to disable |
| `max_retries` | 2 | Config only |

## Performance

**Parallel Execution:**
- Max 4 concurrent tasks by default (configurable via `--max-concurrent`)
- 5s stagger delay prevents API rate limits
- Ideal for independent tasks

**Sequential Execution:**
- One task at a time (`--sequential`)
- No stagger delay
- Predictable resource usage

**Benchmarks:**

```
4 independent tasks (patient policy):
  Parallel:   ~15s (4 concurrent, 5s stagger)
  Sequential: ~40s (1 at a time)
  Speedup:    ~2.7x
```

## Troubleshooting

### Problem: Task file not found

```
Error: Task file not found: tasks.md
```

**Solution:** Create tasks.md or specify correct path

### Problem: Invalid task format

```
Error: Task missing required fields: task 1 has empty description
```

**Solution:** Ensure format: `- [ ] ID. Description`

### Problem: Agent not found

```
Warning: Agent 'unknown' not found, defaulting to self
```

**Solutions:**
1. Check agent exists: `aur agents list`
2. Fix agent name in task file
3. Remove agent comment to use `self`

### Problem: Tasks not executing in parallel

**Check:**
1. Not using `--sequential` flag
2. Tasks don't have dependencies
3. Enough independent tasks to parallelize

### Problem: Dependency cycle

```
Error: Circular dependency detected: 1 -> 2 -> 1
```

**Solution:** Review and fix task dependencies

## Advanced Usage

### Custom Max Concurrent

Edit `packages/cli/src/aurora_cli/commands/spawn.py`:

```python
# Change max_concurrent value
results = await spawn_parallel(spawn_tasks, max_concurrent=10)
```

### Task State Tracking

The spawn command can update task files with completion:

```markdown
# Before
- [ ] 1. Task description

# After
- [x] 1. Task description
```

*(Feature in development)*

### Progress Callbacks

Implement custom progress tracking:

```python
def progress_callback(task_id, status, result):
    """Custom progress handler."""
    print(f"Task {task_id}: {status}")

# Use in spawn implementation
```

*(Feature in development)*

## Configuration

### Config File

Add to `.aurora/config.json`:

```json
{
  "spawner": {
    "max_concurrent": 4,
    "stagger_delay": 5.0,
    "default_policy": "patient"
  }
}
```

CLI flags override config values.

## Agent Recovery

Agent recovery provides automatic retry and fallback mechanisms when agents fail during parallel execution.

### Recovery Flow Overview

```
Task Execution
     │
     ▼
┌─────────────┐
│  Execute    │
│   Agent     │
└─────────────┘
     │
     ▼
┌─────────────┐    Success
│  Success?   │───────────────────────────────────────▶ Done
└─────────────┘
     │ Failure
     ▼
┌─────────────┐    Permanent Error (auth, invalid config)
│  Classify   │───────────────────────────────────────▶ Fail (no retry)
│   Error     │
└─────────────┘
     │ Transient/Timeout/Resource
     ▼
┌─────────────┐    Retries < max_retries
│   Retry?    │───────────────────────────────────────▶ Retry with backoff
└─────────────┘
     │ Retries exhausted
     ▼
┌─────────────┐    fallback_to_llm=true
│  Fallback?  │───────────────────────────────────────▶ Execute via LLM
└─────────────┘
     │ No fallback
     ▼
   Fail
```

### Quick Start

Enable recovery via `.aurora/config.json`:

```json
{
  "spawner": {
    "max_retries": 2,
    "fallback_to_llm": true
  }
}
```

That's it. Failed agents retry twice with backoff, then fall back to direct LLM.

### Recovery Strategies

Choose a strategy based on your use case:

| Strategy | Retries | Fallback | Use Case |
|----------|---------|----------|----------|
| `retry_then_fallback` | 2 | Yes | Default - balanced reliability |
| `retry_same` | 5 | No | Critical agents that must succeed |
| `fallback_only` | 0 | Yes | Fast failure, let LLM handle it |
| `no_recovery` | 0 | No | Fail-fast for debugging |
| `patient` | 3 | Yes | Complex tasks, longer delays |

### Recovery Presets

Use preset policies for common scenarios:

```python
from aurora_spawner.recovery import RecoveryPolicy

# Default: 2 retries, then fallback
policy = RecoveryPolicy.default()

# Aggressive: 5 retries, no fallback (agent must succeed)
policy = RecoveryPolicy.aggressive_retry()

# Fast: skip retries, immediate LLM fallback
policy = RecoveryPolicy.fast_fallback()

# Patient: 3 retries with longer delays (2s base, 3x backoff)
policy = RecoveryPolicy.patient()

# No recovery: fail immediately on first error
policy = RecoveryPolicy.no_recovery()
```

### Error Classification

Recovery decisions are based on error classification:

| Category | Pattern Examples | Behavior |
|----------|------------------|----------|
| `transient` | Rate limit, 429, connection reset | Retry with backoff |
| `timeout` | Timed out, deadline exceeded | Retry with longer timeout |
| `resource` | Quota exceeded, out of memory | Retry after delay |
| `permanent` | Auth failed, 401, invalid API key | Fail immediately |
| `unknown` | Unclassified errors | Use default behavior |

### Config File Options

```json
{
  "spawner": {
    "tool": "claude",
    "model": "sonnet",
    "recovery": {
      "strategy": "retry_then_fallback",
      "max_retries": 2,
      "fallback_to_llm": true,
      "base_delay": 1.0,
      "max_delay": 30.0,
      "backoff_factor": 2.0,
      "jitter": true,
      "circuit_breaker_enabled": true,
      "agent_overrides": {
        "slow-agent": {
          "max_retries": 5,
          "base_delay": 2.0
        }
      }
    }
  }
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `strategy` | string | `"retry_then_fallback"` | Recovery strategy (see table above) |
| `max_retries` | int | `2` | Maximum retry attempts per task |
| `fallback_to_llm` | bool | `true` | Fall back to direct LLM if agent fails |
| `base_delay` | float | `1.0` | Initial delay between retries (seconds) |
| `max_delay` | float | `30.0` | Maximum delay cap (seconds) |
| `backoff_factor` | float | `2.0` | Exponential backoff multiplier |
| `jitter` | bool | `true` | Add randomness to prevent thundering herd |
| `circuit_breaker_enabled` | bool | `true` | Enable circuit breaker protection |
| `agent_overrides` | object | `{}` | Per-agent policy overrides |

### Using Preset in Config

Reference a preset by name and optionally override specific values:

```json
{
  "spawner": {
    "recovery": {
      "preset": "patient",
      "max_retries": 4
    }
  }
}
```

### Programmatic Usage

#### Simple Usage

```python
from aurora_spawner import spawn_parallel_with_recovery, SpawnTask

results = await spawn_parallel_with_recovery(
    tasks=[SpawnTask(prompt="Implement feature X", agent="coder")],
    max_retries=2,
    fallback_to_llm=True,
)

# Check recovery stats
recovered = sum(1 for r in results if r.retry_count > 0)
fallbacks = sum(1 for r in results if r.fallback)
print(f"Recovered: {recovered}, Fallbacks: {fallbacks}")
```

#### Using RecoveryPolicy

```python
from aurora_spawner import spawn_parallel_with_recovery, SpawnTask
from aurora_spawner.recovery import RecoveryPolicy

# Use a preset policy
policy = RecoveryPolicy.patient()
results = await spawn_parallel_with_recovery(
    tasks=tasks,
    recovery_policy=policy,
)

# Or customize specific agents
policy = RecoveryPolicy.default().with_override(
    "slow-agent",
    max_retries=5,
    base_delay=2.0,
)
results = await spawn_parallel_with_recovery(
    tasks=tasks,
    recovery_policy=policy,
)
```

#### With Progress Callbacks

```python
def on_recovery(idx, agent_id, retry_count, used_fallback):
    if used_fallback:
        print(f"Task {idx}: Fell back to LLM (agent {agent_id} failed)")
    else:
        print(f"Task {idx}: Recovered after {retry_count} retries")

results = await spawn_parallel_with_recovery(
    tasks=tasks,
    max_retries=2,
    fallback_to_llm=True,
    on_recovery=on_recovery,
)
```

#### Load Policy from Config

```python
from aurora_spawner.recovery import RecoveryPolicy

# Load from Aurora config dict
config = {"spawner": {"recovery": {"max_retries": 3}}}
policy = RecoveryPolicy.from_config(config)

# Or from dict directly
policy = RecoveryPolicy.from_dict({
    "strategy": "retry_then_fallback",
    "max_retries": 3,
    "fallback_to_llm": True,
})
```

### Recovery Metrics

Track recovery statistics for monitoring:

```python
from aurora_spawner.recovery import get_recovery_metrics, reset_recovery_metrics

# Get global metrics
metrics = get_recovery_metrics()

# After running tasks, check stats
print(f"Success rate: {metrics.success_rate():.1f}%")
print(f"Recovery rate: {metrics.recovery_rate():.1f}%")
print(f"Avg recovery time: {metrics.avg_recovery_time():.2f}s")

# Per-agent stats
for agent_id in metrics._attempts:
    print(f"  {agent_id}: {metrics.success_rate(agent_id):.1f}%")

# Reset for new batch
reset_recovery_metrics()
```

### Result Metadata

Each `SpawnResult` includes recovery metadata:

| Field | Type | Description |
|-------|------|-------------|
| `retry_count` | int | Number of retries before success/failure |
| `fallback` | bool | Whether LLM fallback was used |
| `original_agent` | str | Original agent if fallback was used |

### Circuit Breaker

The circuit breaker prevents repeated attempts to failing agents:

```
      ┌──────────────────────────────────────────────┐
      │                                              │
      ▼                                              │
┌─────────┐    failure_threshold    ┌──────────┐    │
│ CLOSED  │───────reached──────────▶│   OPEN   │    │
│ (allow) │                         │ (reject) │    │
└─────────┘                         └──────────┘    │
      ▲                                   │         │
      │         success                   │         │
      │◀─────────────────┐                │         │
      │                  │                ▼         │
      │             ┌─────────┐    reset_timeout    │
      │             │ HALF-   │◀────────────────────┘
      └─────────────│  OPEN   │
        failure     │ (test)  │
                    └─────────┘
```

- **Closed**: Normal operation, all requests allowed
- **Open**: Agent failing, requests rejected for `reset_timeout` seconds
- **Half-Open**: Testing recovery, one request allowed

Configure via config:

```json
{
  "spawner": {
    "circuit_breaker": {
      "failure_threshold": 2,
      "reset_timeout": 120,
      "failure_window": 300
    }
  }
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `failure_threshold` | int | `2` | Failures to open circuit |
| `reset_timeout` | int | `120` | Seconds before testing recovery |
| `failure_window` | int | `300` | Time window for counting failures |

## Timeout Policies

Choose timeout behavior based on your use case:

| Policy | Initial | Max | No-Activity | Use Case |
|--------|---------|-----|-------------|----------|
| `default` | 60s | 300s | 30s | Balanced |
| `patient` | 120s | 600s | 120s | Complex tasks |
| `fast_fail` | 60s | 60s | 15s | Quick feedback |
| `production` | 120s | 600s | 60s | Production workloads |
| `development` | 1800s | 1800s | 300s | Debugging |
| `test` | 30s | 30s | 10s | Unit tests |

```bash
# Use patient policy for complex agents
aur spawn tasks.md --policy patient

# Fast fail for quick validation
aur spawn tasks.md --policy fast_fail
```

## Early Failure Detection

Detect failures before full timeout by monitoring:

- **Error patterns**: Rate limits, auth failures, API errors
- **No activity**: Stuck agents with no output
- **Stall detection**: Output progress stopped

Configure via config:

```json
{
  "soar": {
    "enable_early_failure_detection": true
  }
}
```

Detection reduces failure time from 60-300s to 5-15s.

## See Also

- [`aur agents list`](./aur-agents.md) - List available agents
- [`aur soar`](./aur-soar.md) - SOAR orchestrator for complex queries
- [Task File Examples](../../examples/spawn/README.md) - Example task files
- [Spawner Package](../../packages/spawner/README.md) - Low-level spawner API
- [Config Reference](../reference/CONFIG_REFERENCE.md) - Full configuration options

## Source

- Command: `packages/cli/src/aurora_cli/commands/spawn.py`
- Spawner: `packages/spawner/src/aurora_spawner/spawner.py`
- Circuit Breaker: `packages/spawner/src/aurora_spawner/circuit_breaker.py`
- Timeout Policies: `packages/spawner/src/aurora_spawner/timeout_policy.py`
- Tests: `packages/cli/tests/test_commands/test_spawn.py`
- E2E Tests: `tests/e2e/test_spawn_command.py`
