# AURORA CLI Usage Guide

Complete guide to using the AURORA command-line interface for intelligent code querying, memory management, and autonomous reasoning.

**Version**: 1.1.0
**Last Updated**: 2024-12-24

---

## Table of Contents

1. [Installation Verification](#installation-verification)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [Basic Queries](#basic-queries)
5. [Memory Management](#memory-management)
6. [Headless Mode](#headless-mode)
7. [Troubleshooting](#troubleshooting)
8. [Command Reference](#command-reference)

---

## Installation Verification

### Install AURORA CLI

```bash
# Install from monorepo (development)
pip install -e packages/cli

# Or install standalone
pip install aurora-cli
```

### Verify Installation

```bash
# Check version
aur --version

# Expected output:
# aurora, version 0.1.0

# Show help
aur --help
```

---

## Initial Setup

### Run Interactive Setup

The `aur init` command guides you through initial configuration:

```bash
aur init
```

**Interactive Prompts:**

1. **API Key Setup** (optional):
   ```
   Enter Anthropic API key (or press Enter to skip):
   ```
   - Enter your API key: `sk-ant-...`
   - Or press Enter to skip and use environment variable later

2. **Index Current Directory** (optional):
   ```
   Index current directory? [Y/n]:
   ```
   - `Y` or Enter: Index Python files in current directory
   - `n`: Skip indexing

**What It Creates:**

- Config file: `~/.aurora/config.json`
- Database: `./aurora.db` (if indexed)
- Directory: `~/.aurora/` (if not exists)

**Example Output:**

```
✓ Configuration created at ~/.aurora/config.json
✓ Indexed 47 files, 234 chunks in 3.4s

Next: Run 'aur query "your question"' to start
```

---

## Configuration

AURORA uses a hierarchical configuration system with multiple sources.

### Configuration Precedence

Configuration is loaded in this order (highest to lowest priority):

1. **CLI flags** (per-command options)
2. **Environment variables** (`ANTHROPIC_API_KEY`, `AURORA_*`)
3. **Config file** (`~/.aurora/config.json` or `./aurora.config.json`)
4. **Default values** (built-in defaults)

### Environment Variables

```bash
# API key (required for queries)
export ANTHROPIC_API_KEY=sk-ant-...

# Escalation threshold (optional)
export AURORA_ESCALATION_THRESHOLD=0.7

# Logging level (optional)
export AURORA_LOGGING_LEVEL=INFO
```

### Config File Structure

**Location**: `~/.aurora/config.json` or `./aurora.config.json`

```json
{
  "version": "1.1.0",
  "llm": {
    "provider": "anthropic",
    "anthropic_api_key": "sk-ant-...",
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "escalation": {
    "threshold": 0.7,
    "enable_keyword_only": false,
    "force_mode": null
  },
  "memory": {
    "auto_index": true,
    "index_paths": ["."],
    "chunk_size": 1000,
    "overlap": 200
  },
  "logging": {
    "level": "INFO",
    "file": "~/.aurora/aurora.log"
  }
}
```

**Configuration Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `llm.provider` | string | `"anthropic"` | LLM provider (only anthropic supported) |
| `llm.anthropic_api_key` | string | `null` | API key (prefer env var) |
| `llm.model` | string | `"claude-3-5-sonnet-20241022"` | Model identifier |
| `llm.temperature` | float | `0.7` | Response randomness (0.0-1.0) |
| `llm.max_tokens` | integer | `4096` | Maximum response tokens |
| `escalation.threshold` | float | `0.7` | Complexity threshold for AURORA (0.0-1.0) |
| `escalation.enable_keyword_only` | boolean | `false` | Use keyword-only escalation |
| `escalation.force_mode` | string | `null` | Force mode: `"direct"` or `"aurora"` |
| `memory.auto_index` | boolean | `true` | Prompt to index on first query |
| `memory.index_paths` | array | `["."]` | Paths to index automatically |
| `memory.chunk_size` | integer | `1000` | Size of code chunks (characters) |
| `memory.overlap` | integer | `200` | Overlap between chunks (characters) |
| `logging.level` | string | `"INFO"` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `logging.file` | string | `"~/.aurora/aurora.log"` | Log file path |

### Create Custom Config File

```bash
# Manual creation
mkdir -p ~/.aurora
nano ~/.aurora/config.json

# Or copy and edit
cp ~/.aurora/config.json ./aurora.config.json
nano ./aurora.config.json
```

---

## Basic Queries

### Simple Query (Direct LLM)

For simple questions, AURORA automatically uses direct LLM mode:

```bash
aur query "What is a Python decorator?"
```

**Output:**
```
→ Using Direct LLM (fast mode)

Response:
┌──────────────────────────────────────────────────────────┐
│ A Python decorator is a function that modifies the       │
│ behavior of another function...                          │
└──────────────────────────────────────────────────────────┘
```

### Complex Query (AURORA Pipeline)

For complex questions, AURORA automatically escalates to full pipeline:

```bash
aur query "Refactor the authentication system to use OAuth2"
```

**Output:**
```
→ Using AURORA (full pipeline)

Response:
┌──────────────────────────────────────────────────────────┐
│ Based on analysis of your authentication system, here    │
│ are the steps to implement OAuth2:                       │
│ 1. Install authlib package                               │
│ 2. Create OAuth2 configuration...                        │
└──────────────────────────────────────────────────────────┘
```

### Force Direct LLM

Skip escalation assessment and use direct LLM:

```bash
aur query "Explain classes" --force-direct
```

**Use Case:**
- You know the query is simple
- Faster response needed
- Lower cost acceptable

### Force AURORA Pipeline

Skip escalation assessment and use full AURORA:

```bash
aur query "What is Python?" --force-aurora
```

**Use Case:**
- Want memory context even for simple queries
- Need SOAR reasoning trace
- Testing AURORA behavior

### Show Escalation Reasoning

See why AURORA chose direct LLM or full pipeline:

```bash
aur query "Design a microservices architecture" --show-reasoning
```

**Output:**
```
Escalation Analysis:
  Query: Design a microservices architecture
  Complexity: COMPLEX
  Score: 0.843
  Confidence: 0.920
  Method: keyword_assessment
  Decision: AURORA
  Reasoning: Query contains architectural planning keywords
```

### Verbose Mode

Show detailed SOAR phase trace:

```bash
aur query "Refactor auth" --force-aurora --verbose
```

**Output:**
```
SOAR Phase Trace:
┌───────────┬──────────┬────────────────────────────────────┐
│ Phase     │ Duration │ Summary                            │
├───────────┼──────────┼────────────────────────────────────┤
│ Assess    │   0.15s  │ Complexity: COMPLEX                │
│ Retrieve  │   0.42s  │ Retrieved 15 relevant chunks       │
│ Decompose │   1.23s  │ Created 3 subgoals                 │
│ Verify    │   0.87s  │ Self-verification passed           │
│ Route     │   0.34s  │ Selected 2 agents                  │
│ Collect   │   2.45s  │ Executed subgoals                  │
│ Synthesize│   1.12s  │ Synthesized final response         │
│ Record    │   0.05s  │ Cached reasoning pattern           │
│ Respond   │   0.02s  │ Formatted response                 │
└───────────┴──────────┴────────────────────────────────────┘

Summary:
  Total Duration: 6.65s
  Estimated Cost: $0.0234
  Confidence: 0.87
  Overall Score: 0.91
```

### Dry-Run Mode

Test configuration without making API calls:

```bash
aur query "test query" --dry-run
```

**Output:**
```
DRY RUN MODE - No API calls will be made

Configuration:
  Provider:  anthropic
  Model:     claude-sonnet-4-20250514
  API Key:   sk-ant-...xyz ✓
  Threshold: 0.6

Memory Store:
  Database:  /home/user/project/aurora.db ✓
  Chunks:    ~234

Escalation Decision:
  Query:      test query
  Complexity: SIMPLE
  Score:      0.245
  Confidence: 0.872
  Method:     keyword_assessment
  Decision:   Would use: Direct LLM
  Reasoning:  Query is a simple informational question

Estimated Cost:
  ~$0.002-0.005 (Direct LLM)

Exiting without API calls
```

**Use Case:**
- Verify API key is configured
- Check database state
- Test escalation logic
- Estimate costs before running

---

## Memory Management

AURORA uses a persistent memory store to provide context for queries.

### Index Current Directory

```bash
aur mem index
```

**What It Does:**
- Scans current directory recursively
- Parses Python files (extensible to other languages)
- Extracts functions, classes, methods
- Stores code chunks with metadata
- Creates embeddings for semantic search

**Output:**
```
Using database: ./aurora.db
Indexing . ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

┌────────────────────────────────────────────────┐
│ ✓ Indexing complete                            │
│                                                │
│ Files indexed:  47                             │
│ Chunks created: 234                            │
│ Duration:       3.42s                          │
│ Errors:         0                              │
└────────────────────────────────────────────────┘
```

### Index Specific Directory

```bash
aur mem index /path/to/project
```

### Index with Custom Database

```bash
aur mem index . --db-path ~/.aurora/memory.db
```

### Search Memory

```bash
aur mem search "authentication"
```

**Output:**
```
Searching memory from ./aurora.db...

Found 8 results for 'authentication'

┌──────────────────┬──────────┬──────────────────┬──────────┬────────┐
│ File             │ Type     │ Name             │ Lines    │  Score │
├──────────────────┼──────────┼──────────────────┼──────────┼────────┤
│ auth_manager.py  │ function │ authenticate_user│ 45-67    │  0.856 │
│ tokens.py        │ function │ validate_token   │ 23-41    │  0.782 │
│ middleware.py    │ class    │ AuthMiddleware   │ 89-145   │  0.734 │
│ decorators.py    │ function │ require_auth     │ 12-28    │  0.689 │
│ models.py        │ class    │ User             │ 34-78    │  0.645 │
│ permissions.py   │ function │ check_permission │ 56-72    │  0.612 │
│ session.py       │ class    │ SessionManager   │ 23-89    │  0.587 │
│ oauth.py         │ function │ oauth_callback   │ 123-156  │  0.534 │
└──────────────────┴──────────┴──────────────────┴──────────┴────────┘

Average scores:
  Activation: 0.245
  Semantic:   0.673
  Hybrid:     0.654
```

### Search with More Results

```bash
aur mem search "database" --limit 10
```

### Search with Content Preview

```bash
aur mem search "calculate" --show-content
```

### Search with JSON Output

```bash
aur mem search "login" --format json > results.json
```

**JSON Format:**
```json
[
  {
    "chunk_id": "abc123...",
    "file_path": "/home/user/project/auth.py",
    "line_start": 45,
    "line_end": 67,
    "content": "def authenticate_user(username, password):\n    ...",
    "activation_score": 0.245,
    "semantic_score": 0.673,
    "hybrid_score": 0.856,
    "metadata": {
      "type": "function",
      "name": "authenticate_user",
      "complexity": 5
    }
  }
]
```

### View Memory Statistics

```bash
aur mem stats
```

**Output:**
```
Loading statistics from ./aurora.db...

    Memory Store Statistics
┌─────────────────────┬──────────────┐
│ Total Chunks        │ 234          │
│ Total Files         │ 47           │
│ Database Size       │ 12.45 MB     │
│                     │              │
│ Languages           │              │
│   python            │ 234 chunks   │
└─────────────────────┴──────────────┘
```

### Auto-Index Prompt

On first query with empty memory, AURORA prompts:

```bash
aur query "How does login work?"
```

**Prompt:**
```
Memory is empty. Index current directory?
This will index Python files in the current directory [Y/n]: _
```

- **Y** or Enter: Index current directory
- **n**: Skip and continue without memory context

---

## Headless Mode

Run autonomous experiments without human intervention.

### Basic Usage

```bash
aur headless experiment.md
```

### Custom Budget and Iterations

```bash
aur headless experiment.md --budget 10.0 --max-iter 20
```

### Custom Branch and Scratchpad

```bash
aur headless experiment.md --branch test-1 --scratchpad log.md
```

### Dry Run (Validation Only)

```bash
aur headless experiment.md --dry-run
```

### Show Scratchpad After Completion

```bash
aur headless experiment.md --show-scratchpad
```

### Prompt File Format

Create a markdown file with this structure:

**experiment.md:**
```markdown
## Goal
Refactor the authentication system to use JWT tokens instead of session cookies.

## Success Criteria
- JWT token generation implemented
- Token validation middleware created
- All tests passing
- No breaking changes to API

## Constraints
- Must maintain backward compatibility for 2 weeks
- Budget: $5.00
- Max iterations: 10

## Context
The current system uses server-side sessions stored in Redis.
Migration plan should include:
1. Implement JWT generation
2. Add token validation
3. Update tests
4. Document migration guide
```

### Safety Features

**Git Branch Enforcement:**
- Default: Requires `headless` branch (not `main`/`master`)
- Override: Use `--allow-main` (⚠️ DANGEROUS)

**Budget Limits:**
- Default: $5.00
- Stops execution when exceeded
- Prevents runaway costs

**Max Iterations:**
- Default: 10 iterations
- Prevents infinite loops
- Each iteration tracked in scratchpad

**Scratchpad Audit Trail:**
- Full execution history
- Iteration-by-iteration progress
- Cost tracking
- Decision rationale

---

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY not found"

**Symptom:**
```
Error: ANTHROPIC_API_KEY not found.
```

**Solution:**
```bash
# Option 1: Set environment variable
export ANTHROPIC_API_KEY=sk-ant-...

# Option 2: Run init command
aur init

# Option 3: Add to config file
nano ~/.aurora/config.json
```

**Get API Key:**
- Visit: https://console.anthropic.com
- Generate new API key
- Copy and store securely

---

### Issue: "Memory store is locked"

**Symptom:**
```
Error: Memory store is locked.
```

**Cause:**
Another AURORA process is using the database.

**Solution:**
```bash
# 1. Check for other AURORA processes
ps aux | grep aur

# 2. Kill hung processes
kill <pid>

# 3. If stuck, remove lock file
rm aurora.db-wal
rm aurora.db-shm
```

---

### Issue: "Rate limit exceeded"

**Symptom:**
```
Error: Rate limit exceeded. Retry in 5s or upgrade API tier.
```

**Cause:**
Too many API requests in short time period.

**Solution:**
```bash
# 1. Wait a few seconds (automatic retry enabled)
# AURORA will retry with exponential backoff

# 2. For simple queries, use direct mode
aur query "question" --force-direct

# 3. Upgrade API tier at console.anthropic.com
```

---

### Issue: Slow queries

**Symptom:**
Queries take >10 seconds to complete.

**Solution:**
```bash
# 1. Use direct LLM for simple queries
aur query "simple question" --force-direct

# 2. Check escalation threshold (increase to prefer direct)
export AURORA_ESCALATION_THRESHOLD=0.8

# 3. Index memory for faster context retrieval
aur mem index

# 4. Check memory database size
aur mem stats
```

---

### Issue: No memory results

**Symptom:**
```
Found 0 results for 'query'
```

**Cause:**
Memory not indexed or query too specific.

**Solution:**
```bash
# 1. Index codebase
aur mem index .

# 2. Verify indexing worked
aur mem stats

# 3. Try broader search query
aur mem search "login"  # Instead of "validate_login_credentials"

# 4. Check database exists
ls -lh aurora.db
```

---

### Issue: Configuration errors

**Symptom:**
```
Error: Configuration file syntax error.
```

**Solution:**
```bash
# 1. Validate JSON syntax
python -m json.tool ~/.aurora/config.json

# 2. Use online validator
# Visit: https://jsonlint.com

# 3. Recreate config
rm ~/.aurora/config.json
aur init

# 4. Check file permissions
chmod 600 ~/.aurora/config.json
chmod 700 ~/.aurora/
```

---

## Command Reference

### Global Options

```bash
aur --verbose    # Enable verbose logging
aur --debug      # Enable debug logging
aur --version    # Show version
aur --help       # Show help
```

### Commands

#### `aur init`

Initialize configuration and optionally index codebase.

```bash
aur init
```

**Options:** None

**Interactive:**
- Prompts for API key
- Prompts to index directory
- Creates `~/.aurora/config.json`

---

#### `aur query`

Execute a query with automatic escalation.

```bash
aur query QUERY_TEXT [OPTIONS]
```

**Arguments:**
- `QUERY_TEXT`: Question or command (required)

**Options:**
- `--force-aurora`: Force AURORA pipeline
- `--force-direct`: Force direct LLM
- `--threshold FLOAT`: Escalation threshold (0.0-1.0, default: 0.6)
- `--show-reasoning`: Show escalation analysis
- `--verbose`: Show SOAR phase trace
- `--dry-run`: Validate without API calls

**Examples:**
```bash
aur query "What is a decorator?"
aur query "Refactor auth" --force-aurora --verbose
aur query "test" --dry-run
```

---

#### `aur mem index`

Index code files into memory store.

```bash
aur mem index [PATH] [OPTIONS]
```

**Arguments:**
- `PATH`: Directory to index (default: `.`)

**Options:**
- `--db-path PATH`: Database location (default: `./aurora.db`)

**Examples:**
```bash
aur mem index
aur mem index /path/to/project
aur mem index . --db-path ~/.aurora/memory.db
```

---

#### `aur mem search`

Search memory for relevant chunks.

```bash
aur mem search QUERY [OPTIONS]
```

**Arguments:**
- `QUERY`: Search query (required)

**Options:**
- `--limit N, -n N`: Max results (default: 5)
- `--format FORMAT, -f FORMAT`: Output format: `rich`, `json` (default: `rich`)
- `--show-content, -c`: Show content preview
- `--db-path PATH`: Database location (default: `./aurora.db`)

**Examples:**
```bash
aur mem search "authentication"
aur mem search "database" --limit 10 --show-content
aur mem search "login" --format json
```

---

#### `aur mem stats`

Display memory store statistics.

```bash
aur mem stats [OPTIONS]
```

**Options:**
- `--db-path PATH`: Database location (default: `./aurora.db`)

**Examples:**
```bash
aur mem stats
aur mem stats --db-path ~/.aurora/memory.db
```

---

#### `aur headless`

Run autonomous experiment in headless mode.

```bash
aur headless PROMPT_PATH [OPTIONS]
```

**Arguments:**
- `PROMPT_PATH`: Path to experiment prompt file (required)

**Options:**
- `--scratchpad PATH, -s PATH`: Scratchpad file location
- `--budget FLOAT, -b FLOAT`: Max budget in USD (default: 5.0)
- `--max-iter INT, -m INT`: Max iterations (default: 10)
- `--branch NAME`: Required git branch (default: `headless`)
- `--allow-main`: ⚠️ DANGEROUS: Allow running on main/master
- `--dry-run`: Validate configuration only
- `--show-scratchpad`: Display scratchpad after completion

**Examples:**
```bash
aur headless experiment.md
aur headless experiment.md --budget 10.0 --max-iter 20
aur headless experiment.md --dry-run
aur headless experiment.md --show-scratchpad
```

---

## Performance Expectations

### Direct LLM Queries

- **Latency**: <2 seconds
- **Cost**: ~$0.002-0.005 per query
- **Use Case**: Simple informational queries

### AURORA Queries (Simple)

- **Latency**: <5 seconds
- **Cost**: ~$0.005-0.015 per query
- **Use Case**: Queries requiring memory context

### AURORA Queries (Complex)

- **Latency**: <15 seconds
- **Cost**: ~$0.015-0.050 per query
- **Use Case**: Multi-step reasoning, code generation

### Indexing

- **100 files**: <30 seconds
- **1,000 files**: <5 minutes
- **Database size**: ~50KB per file

---

## Best Practices

### 1. Index Before Querying

```bash
# Index project first
aur mem index

# Then query with full context
aur query "Explain the auth flow"
```

### 2. Use Dry-Run for Testing

```bash
# Test configuration without costs
aur query "test" --dry-run

# Verify escalation behavior
aur query "complex task" --dry-run --show-reasoning
```

### 3. Prefer Environment Variables for API Keys

```bash
# Secure: Doesn't persist key in files
export ANTHROPIC_API_KEY=sk-ant-...

# Less secure: Key stored in config file
aur init  # Enter API key when prompted
```

### 4. Use Direct LLM When Possible

```bash
# Fast and cheap for simple queries
aur query "What is a list comprehension?" --force-direct
```

### 5. Monitor Costs in Headless Mode

```bash
# Set conservative budget
aur headless experiment.md --budget 5.0 --max-iter 10

# Review scratchpad for cost tracking
cat experiment_scratchpad.md
```

---

## Next Steps

- **Learn More**: See [ERROR_CATALOG.md](ERROR_CATALOG.md) for detailed error solutions
- **Quick Start**: See [QUICK_START.md](QUICK_START.md) for a 5-minute tutorial
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- **API Reference**: See main [README.md](../../README.md) for Python API documentation

---

**Questions or Issues?**

- GitHub Issues: https://github.com/aurora-project/aurora/issues
- Documentation: https://docs.aurora.ai
- Community: https://discord.gg/aurora
