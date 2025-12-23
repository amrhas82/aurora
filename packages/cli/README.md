# AURORA CLI

Command-line interface for the AURORA system.

## Features

- **Memory Commands**: Search AURORA memory with `aur mem`
- **Auto-Escalation**: Automatic routing between direct LLM and full AURORA
- **Query Commands**: Execute queries with transparent escalation

## Installation

```bash
pip install -e packages/cli
```

## Usage

### Memory Search

```bash
# Basic memory search
aur mem "authentication"

# With options
aur mem "calculate total" --max-results 20 --type function --show-content
```

### Query with Auto-Escalation

```bash
# Simple query (uses direct LLM)
aur query "What is a function?"

# Complex query (uses AURORA)
aur query "Design a microservices architecture"

# Show escalation reasoning
aur query "Refactor database" --show-reasoning
```

## Development

Run tests:

```bash
pytest tests/unit/cli/ -v
```
