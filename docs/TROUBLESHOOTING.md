# AURORA Troubleshooting Guide

This guide covers common issues, error messages, and solutions for AURORA.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Storage and Database Errors](#storage-and-database-errors)
- [Parser Errors](#parser-errors)
- [Configuration Errors](#configuration-errors)
- [Context Provider Issues](#context-provider-issues)
- [Agent Registry Problems](#agent-registry-problems)
- [Performance Issues](#performance-issues)
- [Testing Problems](#testing-problems)
- [SOAR Pipeline Issues (Phase 2)](#soar-pipeline-issues-phase-2)
  - [Verification Failures](#verification-failures)
  - [Agent Timeouts](#agent-timeouts)
  - [Budget Exceeded Errors](#budget-exceeded-errors)
  - [LLM Client Issues](#llm-client-issues)
  - [Synthesis Failures](#synthesis-failures)

---

## Installation Issues

### Error: `ModuleNotFoundError: No module named 'aurora_core'`

**Cause**: Package not installed or not in editable mode.

**Solution**:
```bash
# Install in development mode
cd /path/to/aurora
pip install -e packages/core
pip install -e packages/context-code
pip install -e packages/soar

# Or use the Makefile
make install-dev
```

**Verify installation**:
```bash
python -c "import aurora_core; print(aurora_core.__version__)"
```

### Error: `tree-sitter` Build Failure

**Cause**: Missing system dependencies for building tree-sitter grammars.

**Solution (Ubuntu/Debian)**:
```bash
sudo apt-get update
sudo apt-get install build-essential
pip install --upgrade tree-sitter
```

**Solution (macOS)**:
```bash
xcode-select --install
pip install --upgrade tree-sitter
```

**Solution (Windows)**:
- Install Visual Studio Build Tools
- Ensure Python is added to PATH
- Run: `pip install --upgrade tree-sitter`

### Error: `ImportError: cannot import name 'SQLiteStore'`

**Cause**: Circular import or incorrect import path.

**Solution**: Use correct import paths:
```python
# Correct
from aurora_core.store import SQLiteStore

# Incorrect
from aurora_core.store.sqlite import SQLiteStore  # May cause circular import
```

---

## Storage and Database Errors

### Error: `StorageError: Database is locked`

**Cause**: Multiple processes accessing SQLite database without proper timeout.

**Solution 1**: Increase timeout in SQLiteStore initialization:
```python
from aurora_core.store import SQLiteStore

store = SQLiteStore(
    db_path="aurora.db",
    timeout=30.0  # Increase from default 5.0 seconds
)
```

**Solution 2**: Use WAL mode (enabled by default in AURORA):
```python
# WAL mode allows concurrent reads
# Verify it's enabled:
import sqlite3
conn = sqlite3.connect("aurora.db")
cursor = conn.execute("PRAGMA journal_mode")
print(cursor.fetchone())  # Should be ('wal',)
```

**Solution 3**: Use PostgreSQL for production (see [Extension Guide](EXTENSION_GUIDE.md#custom-storage-backends))

### Error: `ValidationError: Invalid chunk data`

**Cause**: Chunk validation failed (invalid line numbers, paths, or metadata).

**Solution**: Check chunk data before saving:
```python
from aurora_core.chunks import CodeChunk

# Invalid: end_line < start_line
chunk = CodeChunk(
    content="def test(): pass",
    chunk_type="code",
    start_line=10,
    end_line=5,  # ERROR: end_line < start_line
    metadata={"name": "test"}
)

# Correct
chunk = CodeChunk(
    content="def test(): pass",
    chunk_type="code",
    start_line=5,
    end_line=10,
    metadata={"name": "test"}
)

# Validate before saving
try:
    chunk.validate()
    store.save_chunk(chunk)
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Error: `OperationalError: no such table: chunks`

**Cause**: Database schema not initialized.

**Solution**: SQLiteStore should auto-initialize, but you can force it:
```python
from aurora_core.store import SQLiteStore

store = SQLiteStore("aurora.db")
# Schema is automatically created in __init__

# Or manually run migrations:
from aurora_core.store.migrations import run_migrations
run_migrations("aurora.db")
```

### Error: `MemoryError: Out of memory`

**Cause**: Loading too many chunks into memory at once.

**Solution**: Use pagination:
```python
# Bad: Load all chunks
chunks = store.list_chunks(limit=1000000)  # May exhaust memory

# Good: Paginate
def process_all_chunks(store, batch_size=1000):
    offset = 0
    while True:
        chunks = store.list_chunks(limit=batch_size, offset=offset)
        if not chunks:
            break

        for chunk in chunks:
            # Process chunk
            pass

        offset += batch_size

process_all_chunks(store)
```

---

## Parser Errors

### Error: `ParseError: Failed to parse Python file`

**Cause**: Syntax error in source file or parser issue.

**Solution 1**: Check file syntax:
```bash
python -m py_compile problematic_file.py
```

**Solution 2**: Handle parse errors gracefully:
```python
from aurora_context_code import PythonParser
from aurora_core.exceptions import ParseError

parser = PythonParser()

try:
    chunks = parser.parse_file("file.py")
except ParseError as e:
    print(f"Parse failed: {e}")
    # Continue with other files
```

**Solution 3**: Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

chunks = parser.parse_file("file.py")
# Will show detailed tree-sitter AST traversal
```

### Error: `RuntimeError: tree-sitter grammar not found`

**Cause**: Tree-sitter language grammar not built or path incorrect.

**Solution**: Rebuild grammars:
```bash
# For development
cd packages/context-code
python scripts/build_grammars.py  # If available

# Or reinstall with build
pip install --force-reinstall --no-binary :all: tree-sitter-python
```

### Error: `UnicodeDecodeError` when parsing files

**Cause**: File encoding not UTF-8.

**Solution**: Specify encoding or handle encoding errors:
```python
def safe_parse_file(parser, file_path):
    """Parse file with encoding fallback."""
    encodings = ['utf-8', 'latin-1', 'cp1252']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            return parser.parse(content, file_path)
        except UnicodeDecodeError:
            continue

    raise ParseError(f"Could not decode {file_path} with any known encoding")
```

### Error: Parser returns empty list for valid code

**Cause**: Parser not registered or file extension not recognized.

**Solution**: Check parser registration:
```python
from aurora_context_code.registry import ParserRegistry

registry = ParserRegistry()

# Check if parser exists for file
file_path = "test.py"
parser = registry.get_parser(file_path)

if not parser:
    print(f"No parser found for {file_path}")
    print(f"Registered parsers: {registry.list_parsers()}")
else:
    chunks = parser.parse_file(file_path)
    print(f"Parsed {len(chunks)} chunks")
```

---

## Configuration Errors

### Error: `ConfigurationError: Invalid configuration schema`

**Cause**: Configuration file doesn't match JSON schema.

**Solution**: Validate configuration:
```bash
# Check your config against schema
python -c "
from aurora_core.config import Config
config = Config.load(config_files=['./aurora.config.json'])
print('Configuration valid!')
"
```

**Common schema violations**:
```json
{
  "storage": {
    "path": "~/aurora.db",  // Must expand ~ to absolute path
    "timeout": "5.0"        // Should be number, not string
  },
  "parser": {
    "languages": "python"   // Should be array: ["python"]
  }
}
```

**Correct format**:
```json
{
  "storage": {
    "path": "/home/user/aurora.db",
    "timeout": 5.0
  },
  "parser": {
    "languages": ["python"]
  }
}
```

### Error: `FileNotFoundError: Config file not found`

**Cause**: Configuration file path incorrect or file doesn't exist.

**Solution**: Use default configuration or create config file:
```python
from aurora_core.config import Config

# Load with defaults if config doesn't exist
try:
    config = Config.load(config_files=['./aurora.config.json'])
except FileNotFoundError:
    print("Config not found, using defaults")
    config = Config.load()  # Uses built-in defaults

# Or create a basic config
import json
default_config = {
    "storage": {"path": "./aurora.db"},
    "parser": {"languages": ["python"]},
    "logging": {"level": "INFO"}
}

with open("aurora.config.json", "w") as f:
    json.dump(default_config, f, indent=2)
```

### Error: Environment variable override not working

**Cause**: Incorrect environment variable name or format.

**Solution**: Use correct naming convention:
```bash
# Correct: Use AURORA_ prefix and uppercase with underscores
export AURORA_STORAGE_PATH="/custom/path/aurora.db"
export AURORA_LOGGING_LEVEL="DEBUG"

# Incorrect (won't work)
export storage.path="/custom/path/aurora.db"
export STORAGE_PATH="/custom/path/aurora.db"
```

**Verify overrides**:
```python
import os
from aurora_core.config import Config

os.environ['AURORA_STORAGE_PATH'] = '/tmp/test.db'
config = Config.load()

print(config.get_string('storage.path'))
# Should print: /tmp/test.db
```

---

## Context Provider Issues

### Error: `No results returned for query`

**Cause**: Query terms not matching chunk content, or empty store.

**Solution 1**: Check if chunks exist:
```python
from aurora_core.context import CodeContextProvider

provider = CodeContextProvider(store, parser_registry)

# Check total chunks
all_chunks = store.list_chunks(limit=10)
print(f"Total chunks in store: {len(all_chunks)}")

if len(all_chunks) == 0:
    print("Store is empty! Parse files first.")
```

**Solution 2**: Try broader queries:
```python
# Too specific (may not match)
results = provider.retrieve("exact_function_name_123")

# Better: Use keywords
results = provider.retrieve("authentication user login")

# Debug: Show all chunk names
all_chunks = store.list_chunks(limit=100)
for chunk in all_chunks:
    print(chunk.metadata.get('name', 'unknown'))
```

**Solution 3**: Check scoring threshold:
```python
# Lower the score threshold in custom retrieval
results = provider.retrieve(query="auth", max_results=20)

for chunk in results:
    score = chunk.metadata.get('_score', 0.0)
    name = chunk.metadata.get('name', 'unknown')
    print(f"{name}: {score:.3f}")
```

### Error: `Cache invalidation not working`

**Cause**: File modification time not updated or cache logic error.

**Solution**: Force cache refresh:
```python
# Force refresh
provider.refresh()

# Or verify mtime-based invalidation
import os
from pathlib import Path

file_path = Path("myfile.py")
print(f"File mtime: {file_path.stat().st_mtime}")

# Modify file to trigger cache invalidation
file_path.touch()
```

### Error: `KeyError: '_score'` in results

**Cause**: Accessing score before it's set by provider.

**Solution**: Use safe access:
```python
results = provider.retrieve("query")

for chunk in results:
    # Safe access with default
    score = chunk.metadata.get('_score', 0.0)

    # Or check existence
    if '_score' in chunk.metadata:
        score = chunk.metadata['_score']
    else:
        score = 0.0
```

---

## Agent Registry Problems

### Error: `AgentError: No agents found`

**Cause**: No agent configuration files in discovery paths.

**Solution**: Check discovery paths and create agent config:
```python
from aurora_soar import AgentRegistry

registry = AgentRegistry(
    discovery_paths=[
        "./config/agents",
        "~/.aurora/agents"
    ]
)

agents = registry.list_agents()
print(f"Found {len(agents)} agents")

if len(agents) == 0:
    print("No agents found. Create agent config file:")
    print("See: docs/EXTENSION_GUIDE.md#custom-agent-implementations")
```

**Create basic agent config** (`./config/agents/agents.json`):
```json
{
  "agents": [
    {
      "id": "default-llm",
      "name": "Default LLM",
      "type": "remote",
      "endpoint": "http://localhost:8000/api/v1",
      "capabilities": ["code-generation", "explanation"],
      "domains": ["python"]
    }
  ]
}
```

### Error: `ValidationError: Invalid agent configuration`

**Cause**: Agent config missing required fields or has invalid values.

**Solution**: Validate against schema:
```python
# Required fields for agent config:
# - id (string)
# - name (string)
# - type ("local" or "remote")
# - capabilities (array of strings)
# - path (for local) OR endpoint (for remote)

# Valid config
{
    "id": "my-agent",
    "name": "My Agent",
    "type": "local",
    "path": "/usr/local/bin/my-agent",
    "capabilities": ["code-analysis"],
    "domains": ["python", "javascript"]
}

# Invalid: missing 'capabilities'
{
    "id": "my-agent",
    "name": "My Agent",
    "type": "local",
    "path": "/usr/local/bin/my-agent"
    # ERROR: 'capabilities' required
}
```

### Error: Agent not responding

**Cause**: Agent endpoint unreachable or agent process not running.

**Solution**: Verify agent status:
```bash
# For remote agents
curl http://localhost:8000/api/v1/health

# For local agents
/usr/local/bin/my-agent --version

# Check agent logs
tail -f /var/log/aurora/agents/*.log
```

---

## Performance Issues

### Slow chunk retrieval (>100ms)

**Cause**: Database not indexed or too many chunks to scan.

**Solution 1**: Verify indexes exist:
```python
import sqlite3

conn = sqlite3.connect("aurora.db")
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
indexes = cursor.fetchall()
print(f"Indexes: {indexes}")

# Should see: idx_chunk_type, idx_file_path, etc.
```

**Solution 2**: Use filters to narrow search:
```python
# Slow: scan all chunks
results = provider.retrieve("auth", max_results=10)

# Faster: filter by type
results = provider.retrieve(
    "auth",
    max_results=10,
    filters={'chunk_type': 'code'}
)
```

**Solution 3**: Profile the query:
```python
from aurora_testing.benchmarks import PerformanceBenchmark

with PerformanceBenchmark("retrieval") as bench:
    results = provider.retrieve("query", max_results=10)

print(f"Retrieval took: {bench.duration_ms:.2f}ms")
```

### Parser taking too long (>1 second for 1000 lines)

**Cause**: Complex file or inefficient AST traversal.

**Solution**: Profile parser performance:
```python
from aurora_testing.benchmarks import PerformanceBenchmark

with PerformanceBenchmark("parse_large_file") as bench:
    chunks = parser.parse_file("large_file.py")

print(f"Parsed {len(chunks)} chunks in {bench.duration_ms:.2f}ms")

if bench.duration_ms > 1000:
    print("Warning: Parser slower than expected")
    print("Consider: file size reduction, caching, or optimization")
```

### High memory usage

**Cause**: Too many chunks cached in memory.

**Solution**: Limit cache size:
```python
from aurora_core.context import CodeContextProvider

# Limit cache entries
provider = CodeContextProvider(
    store,
    parser_registry,
    max_cache_entries=1000  # Limit cache size
)

# Or clear cache periodically
provider.refresh()  # Clears cache
```

---

## Testing Problems

### Error: `pytest: command not found`

**Cause**: pytest not installed.

**Solution**:
```bash
pip install pytest pytest-cov
# Or
make install-dev
```

### Tests fail with `FileNotFoundError: test fixtures`

**Cause**: Tests running from wrong directory or fixtures not installed.

**Solution**:
```bash
# Run tests from project root
cd /path/to/aurora
pytest tests/

# Or use Makefile
make test
```

### Coverage report shows 0% coverage

**Cause**: Source not included in coverage measurement.

**Solution**:
```bash
# Run with explicit source
pytest tests/ --cov=packages/core/src --cov=packages/context-code/src

# Or use Makefile
make coverage
```

### Tests pass locally but fail in CI

**Cause**: Environment differences (dependencies, Python version, OS).

**Solution 1**: Check CI Python version matches local:
```bash
# Local
python --version

# CI (check .github/workflows/ci.yml)
# Should match or be compatible
```

**Solution 2**: Reproduce CI environment locally:
```bash
# Use same Python version as CI
pyenv install 3.10.12
pyenv local 3.10.12

# Fresh virtual environment
python -m venv ci_test_env
source ci_test_env/bin/activate
pip install -e packages/core[dev]
pytest tests/
```

---

## Getting More Help

### Enable Debug Logging

```python
import logging

# Enable debug logging for all AURORA components
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Or specific components
logging.getLogger('aurora_core.store').setLevel(logging.DEBUG)
logging.getLogger('aurora_context_code').setLevel(logging.DEBUG)
```

### Common Debug Commands

```bash
# Check installed packages
pip list | grep aurora

# Verify package structure
python -c "import aurora_core; print(aurora_core.__file__)"

# Run tests with verbose output
pytest tests/ -v -s

# Run single test file
pytest tests/unit/core/test_store_sqlite.py -v

# Check database schema
sqlite3 aurora.db ".schema"

# Monitor file changes
inotifywait -m -r --format '%w%f %e' packages/
```

### Report Issues

If you've tried the solutions above and still have problems:

1. **Check existing issues**: https://github.com/aurora-project/aurora/issues
2. **Create detailed bug report** with:
   - AURORA version
   - Python version
   - Operating system
   - Full error traceback
   - Minimal reproduction code
   - Steps to reproduce

3. **Include diagnostic info**:
```bash
python -c "
import sys
import aurora_core
print(f'Python: {sys.version}')
print(f'AURORA Core: {aurora_core.__version__}')
print(f'Platform: {sys.platform}')
"
```

---

## SOAR Pipeline Issues (Phase 2)

### Verification Failures

#### Error: `Decomposition verification failed with score 0.45`

**Cause**: Decomposition quality below threshold (0.5).

**Symptoms**:
```json
{
  "error": "Decomposition verification failed",
  "verdict": "FAIL",
  "overall_score": 0.45,
  "issues": [
    "Missing key aspects: error handling, testing",
    "Subgoal 2 and 4 have contradictory approaches"
  ]
}
```

**Solutions**:
1. **Rephrase query more specifically**:
   ```
   Before: "Build authentication"
   After: "Implement JWT-based authentication with token refresh and email verification"
   ```

2. **Break into smaller queries**:
   ```
   Query 1: "Analyze existing auth structure"
   Query 2: "Implement JWT token generation"
   Query 3: "Add token refresh endpoint"
   ```

3. **Provide more context**:
   - Include relevant file paths
   - Mention existing patterns ("similar to user-service auth")
   - Specify constraints ("must use existing database schema")

**Debug**:
```bash
# Check verification scores
grep "verification" ~/.aurora/logs/conversations/*/your-query*.md

# Review decomposition quality
cat ~/.aurora/logs/conversations/*/your-query*.md | grep -A 20 "Phase 4: VERIFY"
```

#### Error: `Verification retry exhausted (2/2 attempts)`

**Cause**: Decomposition still below threshold after 2 retries with feedback.

**Symptoms**:
- Score improves but stays in RETRY range (0.5-0.7)
- Similar issues persist across retries

**Solutions**:
1. **Query too complex for automatic decomposition**:
   - Break into multiple simpler queries
   - Provide step-by-step breakdown manually

2. **Domain too specialized**:
   - Add domain context to query
   - Reference similar completed work
   - Consider manual decomposition

3. **Contradictory requirements**:
   - Clarify requirements
   - Resolve contradictions in query
   - Prioritize requirements explicitly

**Example**:
```
Query: "Migrate to microservices and maintain monolith compatibility"
Issue: Contradictory (cannot do both)

Solution: Break into phases
- Query 1: "Analyze monolith for service boundaries"
- Query 2: "Extract user service while maintaining API compatibility"
- Query 3: "Test extracted service with existing clients"
```

---

### Agent Timeouts

#### Error: `Agent execution timed out after 60s`

**Cause**: Agent exceeded per-agent timeout (default: 60s).

**Symptoms**:
```json
{
  "subgoal_id": "sg3",
  "summary": "Execution timed out after 60s. Partial results may be incomplete.",
  "confidence": 0.3,
  "metadata": {
    "timeout": true,
    "timeout_seconds": 60
  }
}
```

**Solutions**:
1. **Increase timeout** (if subgoal is inherently slow):
   ```python
   config = {
       "agent_timeout_seconds": 120  # 2 minutes
   }
   ```

2. **Break subgoal into smaller pieces**:
   ```
   Before: "Run all integration tests"
   After:
     - "Run auth integration tests"
     - "Run billing integration tests"
     - "Run user integration tests"
   ```

3. **Optimize agent implementation**:
   - Check for slow operations (database queries, file I/O)
   - Use parallel operations where possible
   - Cache expensive computations

**Debug**:
```bash
# Check agent execution times
grep "duration_ms" ~/.aurora/logs/conversations/*/your-query*.md

# Identify slow agents
grep -A 5 "timeout" ~/.aurora/logs/conversations/*/your-query*.md
```

#### Error: `Query timeout exceeded (300s)`

**Cause**: Overall query exceeded 5-minute timeout.

**Symptoms**:
- Some subgoals incomplete
- Partial synthesis returned
- Multiple agent timeouts

**Solutions**:
1. **Reduce query complexity**:
   - Break into multiple queries
   - Reduce number of subgoals

2. **Increase overall timeout**:
   ```python
   config = {
       "query_timeout_seconds": 600  # 10 minutes
   }
   ```

3. **Optimize execution order**:
   - More parallelization
   - Remove unnecessary dependencies
   - Skip non-critical subgoals

---

### Budget Exceeded Errors

#### Error: `BudgetExceededError: Monthly limit $100 exceeded`

**Cause**: Estimated query cost would exceed monthly budget.

**Symptoms**:
```
ERROR: Budget limit exceeded ($100 / $100)
Estimated cost: $0.50
Current usage: $99.60
Query rejected to prevent overspending
```

**Solutions**:
1. **Increase monthly limit**:
   ```python
   from aurora_core.budget import CostTracker
   tracker = CostTracker()
   tracker.set_monthly_limit(200.0)  # $200/month
   ```

2. **Wait for new period** (auto-resets monthly):
   ```bash
   # Check current period
   cat ~/.aurora/budget_tracker.json | grep current_period
   # Will reset on first day of next month
   ```

3. **Use local models** (free):
   ```python
   from aurora_reasoning import OllamaClient
   llm_client = OllamaClient(model="llama3")
   ```

4. **Optimize query to reduce cost**:
   - Use SIMPLE queries when possible (keyword assessment only)
   - Avoid CRITICAL complexity (uses expensive Opus 4 model)
   - Phrase queries clearly to reduce retry loops

**Check budget status**:
```python
from aurora_core.budget import CostTracker
tracker = CostTracker()
status = tracker.get_status()
print(f"Used: ${status['used']:.2f} / ${status['limit']:.2f} ({status['percentage']:.1f}%)")
print(f"Remaining: ${status['remaining']:.2f}")
```

#### Warning: `Budget at 85%, approaching limit`

**Cause**: Soft limit (80%) exceeded, approaching hard limit (100%).

**Action**:
- Monitor remaining queries
- Increase limit if needed
- Review high-cost queries

**Analyze spending**:
```python
# Find expensive operations
history = tracker.get_history("2025-01")
expensive = sorted(history, key=lambda x: x.cost_usd, reverse=True)[:10]
for entry in expensive:
    print(f"{entry.operation}: ${entry.cost_usd:.4f} ({entry.model})")
```

---

### LLM Client Issues

#### Error: `AnthropicAPIError: Invalid API key`

**Cause**: Missing or invalid Anthropic API key.

**Solution**:
```bash
# Set API key in environment
export ANTHROPIC_API_KEY="sk-ant-..."

# Or in .env file
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env

# Verify
python -c "import os; print('Key set:', bool(os.getenv('ANTHROPIC_API_KEY')))"
```

#### Error: `RateLimitError: Too many requests`

**Cause**: Exceeded API rate limits.

**Solutions**:
1. **Add delay between requests** (automatic with tenacity retry):
   - Default: exponential backoff (100ms, 200ms, 400ms)

2. **Reduce concurrent queries**:
   - Limit parallel agent execution
   - Add queuing layer

3. **Use local models for development**:
   ```python
   from aurora_reasoning import OllamaClient
   llm = OllamaClient(model="llama3", base_url="http://localhost:11434")
   ```

#### Error: `TimeoutError: LLM call timed out after 30s`

**Cause**: LLM response took too long.

**Solutions**:
1. **Increase LLM timeout**:
   ```python
   llm_client.generate(prompt, timeout=60)  # 60 seconds
   ```

2. **Reduce prompt size**:
   - Fewer few-shot examples
   - Trim context
   - Simplify query

3. **Check network connectivity**:
   ```bash
   curl -I https://api.anthropic.com
   ```

#### Error: `JSONDecodeError: Failed to parse LLM response`

**Cause**: LLM didn't return valid JSON.

**Symptoms**:
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
Raw response: "Here is the decomposition:\n```json\n{...}\n```"
```

**Solutions**:
1. **JSON extraction** (automatic with `generate_json()`):
   - Extracts JSON from markdown code blocks
   - Handles extra text before/after JSON

2. **Improve prompt**:
   ```python
   prompt += "\n\nIMPORTANT: Return ONLY valid JSON, no markdown, no explanations."
   ```

3. **Validate response**:
   ```python
   response = llm_client.generate_json(prompt)
   # Automatically validates and extracts JSON
   ```

---

### Synthesis Failures

#### Error: `Synthesis verification failed: Low traceability (0.55)`

**Cause**: Synthesized answer contains claims not supported by agent outputs.

**Symptoms**:
```json
{
  "issues": [
    "Claim 'all tests passing' not supported by any agent output",
    "Reference to 'performance improvements' without agent evidence"
  ]
}
```

**Solutions**:
1. **Retry with stricter constraints** (automatic, max 2 retries):
   - Synthesis includes feedback
   - Stronger traceability requirements

2. **Check agent outputs**:
   - Verify agents completed successfully
   - Check confidence scores (low confidence = unreliable)
   - Review agent summaries for missing information

3. **Manual synthesis** (if retry fails):
   - Review agent outputs directly
   - Construct answer manually from evidence
   - Use query logs to see what agents actually did

**Debug**:
```bash
# Check synthesis traceability
cat ~/.aurora/logs/conversations/*/your-query*.md | grep -A 30 "Phase 7: SYNTHESIZE"

# Review agent outputs
cat ~/.aurora/logs/conversations/*/your-query*.md | grep -A 20 "Phase 6: COLLECT"
```

#### Error: `No agent outputs available for synthesis`

**Cause**: All agents failed or returned low confidence results.

**Symptoms**:
- Empty synthesis
- Error: "Cannot synthesize with no inputs"

**Solutions**:
1. **Check agent failures**:
   - Review Phase 6 (Collect) outputs
   - Identify which agents failed and why
   - Fix agent issues or retry

2. **Lower confidence threshold** (if appropriate):
   ```python
   config = {
       "min_confidence_for_synthesis": 0.5  # Default: 0.7
   }
   ```

3. **Reduce subgoal count**:
   - Simplify query
   - Remove optional subgoals
   - Focus on critical subgoals only

---

### Common Patterns and Quick Fixes

#### Pattern: High Verification Retry Rate

**Symptom**: Many queries require 2+ retries in Phase 4.

**Root Cause**: Vague queries or poor few-shot examples.

**Fix**:
1. Improve query clarity
2. Update few-shot examples in `packages/reasoning/examples/example_decompositions.json`
3. Review verification prompts for clarity

#### Pattern: Frequent Agent Timeouts

**Symptom**: 10%+ of agent executions timeout.

**Root Cause**: Unrealistic timeouts or slow agents.

**Fix**:
1. Profile agent execution times
2. Increase timeout for slow agents
3. Optimize agent implementations
4. Break complex subgoals into smaller ones

#### Pattern: Budget Exhausted Mid-Month

**Symptom**: Hit budget limit before month end.

**Root Cause**: Underestimated usage or high-cost queries.

**Fix**:
1. Increase monthly limit
2. Analyze spending patterns (find expensive operations)
3. Use keyword assessment (saves 70% on Phase 1)
4. Switch to local models for development

#### Pattern: Synthesis Quality Issues

**Symptom**: Low traceability scores, contradictory answers.

**Root Cause**: Poor agent outputs or synthesis prompt issues.

**Fix**:
1. Improve agent output quality (clearer summaries)
2. Review synthesis prompt for clarity
3. Add more synthesis examples to calibration
4. Lower confidence threshold if accepting partial results

---

## Additional Resources

- [README](../README.md)
- [Extension Guide](EXTENSION_GUIDE.md)
- [Architecture Documentation](../README.md#architecture)
- [SOAR Architecture](SOAR_ARCHITECTURE.md)
- [Verification Checkpoints](VERIFICATION_CHECKPOINTS.md)
- [Cost Tracking Guide](COST_TRACKING_GUIDE.md)
- [Agent Integration Guide](AGENT_INTEGRATION.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
