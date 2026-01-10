# aur spawn

Execute tasks from markdown task files in parallel or sequentially.

## Synopsis

```bash
aur spawn [OPTIONS] [TASK_FILE]
```

## Description

The `aur spawn` command loads tasks from a markdown checklist file and executes them using the aurora-spawner package. Tasks can be executed in parallel (default) or sequentially, with support for agent assignment and dependency management.

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

- **Parallel mode**: Executes up to 5 tasks concurrently
- **Sequential mode**: Executes one task at a time

```bash
aur spawn --parallel              # Parallel execution (default)
aur spawn --no-parallel           # Sequential execution
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

Executes all tasks in `tasks.md` in parallel (up to 5 concurrent).

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
Loaded 5 tasks from tasks.md
Executing tasks in parallel...
[cyan]Spawning 5 tasks in parallel (max_concurrent=5)...[/]

[green]✓[/] Task 1: Success
  Duration: 1234ms
  Agent: researcher

[green]✓[/] Task 2: Success
  Duration: 2341ms
  Agent: developer

...
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

## Performance

**Parallel Execution:**
- Max 5 concurrent tasks (configurable in source)
- Ideal for independent tasks
- Reduces total execution time

**Sequential Execution:**
- One task at a time
- Ideal for dependent tasks
- Predictable resource usage

**Benchmarks:**

```
5 independent tasks:
  Parallel:   8.2s (5 concurrent)
  Sequential: 35.1s (1 at a time)
  Speedup:    4.3x
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

### Environment Variables

- `AURORA_SPAWN_MAX_CONCURRENT` - Max parallel tasks (default: 5)
- `AURORA_SPAWN_TIMEOUT` - Task timeout in seconds (default: 300)

*(Configuration support in development)*

### Config File

```json
{
  "spawn": {
    "max_concurrent": 10,
    "default_timeout": 600,
    "auto_update_file": true
  }
}
```

*(Configuration support in development)*

## See Also

- [`aur agents list`](./aur-agents.md) - List available agents
- [`aur soar`](./aur-soar.md) - SOAR orchestrator for complex queries
- [Task File Examples](../../examples/spawn/README.md) - Example task files
- [Spawner Package](../../packages/spawner/README.md) - Low-level spawner API

## Source

- Command: `packages/cli/src/aurora_cli/commands/spawn.py`
- Tests: `packages/cli/tests/test_commands/test_spawn.py`
- E2E Tests: `tests/e2e/test_spawn_command.py`
