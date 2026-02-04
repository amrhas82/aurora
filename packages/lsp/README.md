# Aurora LSP

LSP integration for Aurora - code intelligence, dead code detection, and impact analysis.

Built on [multilspy](https://github.com/microsoft/multilspy) (Microsoft) with custom layers for import filtering and code analysis.

## Features

- **Find Usages (excluding imports)** - Distinguish actual code usage from import statements
- **Dead Code Detection** - Find functions/classes with 0 usages
- **Linting** - Get errors, warnings, hints via LSP diagnostics
- **Call Hierarchy** - Find callers of a function (where supported)

## Supported Languages

| Language | LSP Server | Import Filtering | Call Hierarchy |
|----------|------------|------------------|----------------|
| Python | Pyright | ✓ | Limited |
| TypeScript | tsserver | ✓ | ✓ |
| JavaScript | tsserver | ✓ | ✓ |
| Rust | rust-analyzer | ✓ | ✓ |
| Go | gopls | ✓ | ✓ |
| Java | Eclipse JDT | ✓ | ✓ |
| Ruby | Solargraph | ✓ | Limited |
| C# | OmniSharp | ✓ | ✓ |
| Dart | Dart Analysis | ✓ | ✓ |
| Kotlin | kotlin-lsp | ✓ | Limited |

## Installation

```bash
pip install aurora-lsp
```

## Usage

### Basic Usage

```python
from aurora_lsp import AuroraLSP

# Initialize with workspace path
lsp = AuroraLSP("/path/to/project")

# Find usages of a symbol (excluding imports)
result = lsp.find_usages("src/main.py", line=10, col=5)
print(f"Found {result['total_usages']} usages ({result['total_imports']} imports filtered)")

# Get usage summary with impact assessment
summary = lsp.get_usage_summary("src/main.py", line=10, col=5, symbol_name="MyClass")
print(f"Impact: {summary['impact']} ({summary['files_affected']} files affected)")

# Find dead code
dead = lsp.find_dead_code()
for item in dead:
    print(f"Unused: {item['name']} ({item['kind']}) in {item['file']}:{item['line']}")

# Lint a directory
diags = lsp.lint("src/")
print(f"{diags['total_errors']} errors, {diags['total_warnings']} warnings")

# Find callers of a function
callers = lsp.get_callers("src/utils.py", line=25, col=0)
for caller in callers:
    print(f"Called by: {caller['name']} in {caller['file']}")

# Clean up
lsp.close()
```

### Context Manager

```python
from aurora_lsp import AuroraLSP

with AuroraLSP("/path/to/project") as lsp:
    dead = lsp.find_dead_code()
    print(f"Found {len(dead)} dead code items")
# Server connections closed automatically
```

### Convenience Functions

```python
from aurora_lsp import find_usages, find_dead_code, lint

# One-off operations (creates temporary LSP instance)
result = find_usages("src/main.py", line=10, col=5)
dead = find_dead_code("src/")
diags = lint("src/")
```

## API Reference

### AuroraLSP

Main facade class providing synchronous API.

#### `find_usages(file_path, line, col, include_imports=False) -> dict`

Find usages of a symbol.

**Returns:**
- `usages`: List of usage locations with context
- `imports`: List of import locations
- `total_usages`: Count of actual usages
- `total_imports`: Count of import statements

#### `get_usage_summary(file_path, line, col, symbol_name=None) -> dict`

Get comprehensive usage summary.

**Returns:**
- `symbol`: Symbol name
- `total_usages`: Usage count
- `total_imports`: Import count
- `impact`: 'low' (<3), 'medium' (3-10), 'high' (>10)
- `files_affected`: Number of files with usages
- `usages_by_file`: Usages grouped by file

#### `find_dead_code(path=None, include_private=False) -> list[dict]`

Find functions/classes with 0 usages.

**Returns:** List of items with:
- `file`: File path
- `line`: Line number
- `name`: Symbol name
- `kind`: 'function', 'class', or 'method'
- `imports`: Number of times imported but never used

#### `lint(path=None, severity_filter=None) -> dict`

Get linting diagnostics.

**Returns:**
- `errors`: List of errors
- `warnings`: List of warnings
- `hints`: List of hints
- `total_errors`, `total_warnings`, `total_hints`: Counts

#### `get_callers(file_path, line, col) -> list[dict]`

Find functions that call this symbol.

**Returns:** List of items with:
- `file`: File path
- `line`: Line number
- `name`: Function name

## Architecture

```
┌─────────────────────────────────────────┐
│  AuroraLSP (facade.py)                  │  High-level sync API
├─────────────────────────────────────────┤
│  CodeAnalyzer (analysis.py)             │  Dead code, usage summary
│  DiagnosticsFormatter (diagnostics.py)  │  Linting
│  ImportFilter (filters.py)              │  Import vs usage
├─────────────────────────────────────────┤
│  AuroraLSPClient (client.py)            │  Async LSP operations
├─────────────────────────────────────────┤
│  multilspy (Microsoft)                  │  LSP server management
└─────────────────────────────────────────┘
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Type checking
mypy src/
```

## Claude Code Pre-Edit Hook

For Claude Code users, Aurora can automatically run `lsp check` before every file edit. This is configured automatically when you run:

```bash
aur init --tools=claude
```

This creates:
- `.claude/hooks/pre-edit-lsp-check.py` - Hook script
- `.claude/settings.json` - Project-local settings with PreToolUse hook

Before every Edit, Claude sees:
```
LSP CHECK: 'MyClass' @ line 26 | 3 LSP refs | Risk: MEDIUM
```

See [LSP.md](../../docs/02-features/lsp/LSP.md) for manual setup instructions.

## License

MIT
