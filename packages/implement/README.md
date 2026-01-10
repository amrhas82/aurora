# Implement Package

Task parser and executor for Aurora framework.

## Features

- Parse tasks.md files with agent metadata
- Extract task completion status
- Dispatch tasks to agents via Task tool
- Support for agent and model metadata in HTML comments

## Installation

```bash
pip install -e packages/implement/
```

## Usage

```python
from implement import TaskParser, TaskExecutor, ParsedTask

# Parse tasks from tasks.md
parser = TaskParser()
with open("tasks.md") as f:
    tasks = parser.parse(f.read())

# Execute tasks
executor = TaskExecutor()
results = await executor.execute(tasks, Path("tasks.md"))
```

## Development

```bash
# Install dev dependencies
pip install -e "packages/implement/[dev]"

# Run tests
pytest packages/implement/tests/

# Run tests with coverage
pytest packages/implement/tests/ --cov=implement --cov-report=term-missing
```
