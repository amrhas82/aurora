# Example Task File for Aurora Spawn

This example demonstrates how to structure tasks for parallel execution using `aur spawn`.

## Task Format

Tasks follow standard markdown checklist format with HTML comment metadata:

```markdown
- [ ] Task ID. Task description
<!-- agent: agent-name -->
```

## Example Tasks

- [ ] 1. Analyze project structure and identify main entry points
<!-- agent: self -->

- [ ] 2. Review package.json dependencies and check for vulnerabilities
<!-- agent: self -->

- [ ] 3. Generate test coverage report for existing tests
<!-- agent: self -->
<!-- depends: 1 -->

- [ ] 4. Create documentation for undocumented functions
<!-- agent: self -->
<!-- depends: 1 -->

## Task Dependencies

Tasks with `<!-- depends: X -->` comments will be executed after task X completes.
Tasks without dependencies can run in parallel.

## Agent Assignment

- `self`: Use the current session/context without spawning
- `agent-name`: Spawn a specific agent by ID from your agent registry

## Usage

```bash
# Run all tasks in parallel (default)
aur spawn tasks-example.md

# Run tasks sequentially
aur spawn tasks-example.md --sequential

# Validate without executing
aur spawn tasks-example.md --dry-run

# Show detailed output
aur spawn tasks-example.md --verbose
```
