# Aurora Spawn Examples

This directory contains example task files for the `aur spawn` command.

## Overview

The `aur spawn` command enables parallel execution of tasks from markdown checklist files. It's designed for:

- Breaking down complex workflows into discrete, parallelizable tasks
- Coordinating multiple agents working on different aspects of a problem
- Tracking progress of multi-step implementations
- Automating repetitive task execution

## Example Files

### tasks-example.md

A basic example showing:
- Standard task format with agent metadata
- Task dependencies using HTML comments
- Mix of parallel and sequential tasks
- Common use cases (analysis, testing, documentation)

## Task File Format

### Basic Structure

```markdown
# Task List Title

- [ ] 1. Task description
<!-- agent: agent-name -->
<!-- depends: previous-task-id -->
```

### Metadata Comments

- `<!-- agent: agent-name -->` - Specifies which agent should handle this task
  - `self` - Execute in current context (no spawning)
  - `agent-id` - Spawn specific agent from registry

- `<!-- depends: task-id -->` - Declares dependency on another task
  - Tasks with dependencies execute after their dependencies complete
  - Tasks without dependencies can run in parallel

### Task States

- `[ ]` - Pending (not started)
- `[x]` - Completed
- Task state is updated automatically by spawn command

## Usage Examples

### Basic Execution

```bash
# Execute tasks.md in current directory
aur spawn

# Execute specific task file
aur spawn path/to/tasks.md

# Execute with absolute path
aur spawn /home/user/project/tasks.md
```

### Execution Modes

```bash
# Parallel execution (default, max 5 concurrent)
aur spawn tasks-example.md --parallel

# Sequential execution (one at a time)
aur spawn tasks-example.md --sequential

# Validate without executing
aur spawn tasks-example.md --dry-run
```

### Verbosity

```bash
# Show detailed progress
aur spawn tasks-example.md --verbose

# Quiet mode (errors only)
aur spawn tasks-example.md
```

## Best Practices

### 1. Use Clear Task IDs

```markdown
✓ Good: - [ ] 1.1 Implement authentication
✗ Bad:  - [ ] Fix stuff
```

### 2. Specify Agent Assignments

```markdown
✓ Good:
- [ ] 1. Task description
<!-- agent: researcher -->

✗ Bad:
- [ ] 1. Task description
(No agent metadata - will default to self)
```

### 3. Document Dependencies

```markdown
✓ Good:
- [ ] 1. Write tests
<!-- agent: test-agent -->
- [ ] 2. Run tests
<!-- agent: self -->
<!-- depends: 1 -->

✗ Bad:
- [ ] 1. Write tests
- [ ] 2. Run tests
(No dependency - might run before tests exist)
```

### 4. Keep Tasks Focused

```markdown
✓ Good:
- [ ] 1. Parse configuration file
- [ ] 2. Validate configuration schema
- [ ] 3. Apply configuration settings

✗ Bad:
- [ ] 1. Do everything related to configuration
```

## Integration with Other Commands

### With aur soar

The spawn command works well with soar for complex multi-agent workflows:

```bash
# Use soar to plan tasks, then execute with spawn
aur soar "Plan tasks for implementing user authentication" > tasks.md
aur spawn tasks.md
```

### With Agent Discovery

Spawn automatically discovers available agents using the same system as `aur agents list`:

```bash
# List available agents
aur agents list

# Use agent in task file
# - [ ] 1. Research topic
# <!-- agent: researcher -->
```

## Troubleshooting

### Task File Not Found

```
Error: Task file not found: tasks.md
```

**Solution**: Create a tasks.md file in the current directory or specify a path

### Invalid Task Format

```
Error: Task missing required fields: task 1 has empty or missing description
```

**Solution**: Ensure all tasks have format: `- [ ] ID. Description`

### Agent Not Found

```
Warning: Agent 'unknown-agent' not found, defaulting to self
```

**Solution**: Check available agents with `aur agents list` and use valid agent IDs

## Performance Tips

1. **Parallel by Default**: Use parallel execution for independent tasks
2. **Declare Dependencies**: Only use `depends` when truly needed
3. **Batch Similar Tasks**: Group related tasks to minimize context switching
4. **Monitor Progress**: Use `--verbose` to see real-time execution status

## Advanced Usage

### Custom Max Concurrent

Currently fixed at 5, but can be modified in source:

```python
# packages/cli/src/aurora_cli/commands/spawn.py
results = await spawn_parallel(spawn_tasks, max_concurrent=10)  # Increase limit
```

### Task File Updates

The spawn command can update task files with completion status:

```markdown
# Before execution
- [ ] 1. Task description

# After completion
- [x] 1. Task description
```

## Examples from Real Workflows

### Code Review Workflow

```markdown
# Code Review Tasks

- [ ] 1. Run static analysis
<!-- agent: self -->

- [ ] 2. Check test coverage
<!-- agent: self -->

- [ ] 3. Review security concerns
<!-- agent: security-reviewer -->

- [ ] 4. Verify documentation
<!-- agent: doc-reviewer -->

- [ ] 5. Compile review report
<!-- agent: self -->
<!-- depends: 1,2,3,4 -->
```

### Feature Implementation

```markdown
# Feature: User Authentication

- [ ] 1. Design database schema
<!-- agent: architect -->

- [ ] 2. Write migration scripts
<!-- agent: self -->
<!-- depends: 1 -->

- [ ] 3. Implement API endpoints
<!-- agent: backend-dev -->
<!-- depends: 2 -->

- [ ] 4. Write API tests
<!-- agent: test-engineer -->
<!-- depends: 3 -->

- [ ] 5. Create frontend components
<!-- agent: frontend-dev -->
<!-- depends: 3 -->

- [ ] 6. Write E2E tests
<!-- agent: test-engineer -->
<!-- depends: 4,5 -->
```

## See Also

- `aur spawn --help` - Command help
- `aur agents list` - View available agents
- `aur soar --help` - SOAR orchestrator help
- [Spawn Command Documentation](../../docs/commands/aur-spawn.md)
