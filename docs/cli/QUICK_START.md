# AURORA CLI Quick Start Guide

Get started with AURORA in 5 minutes. This guide walks you through installation, setup, and your first query.

**Time Required**: 5 minutes
**Prerequisites**: Python 3.10+, pip

**Note:** This guide covers standalone CLI usage. For Claude Code CLI integration (no API key required), see [MCP Setup Guide](../MCP_SETUP.md).

---

## Step 1: Install (1 minute)

```bash
# Install AURORA CLI
pip install -e packages/cli

# Verify installation
aur --version
```

**Expected Output**:
```
aurora, version 0.1.0
```

---

## Step 2: Get API Key (2 minutes)

**Required for:** Standalone CLI commands (`aur query`, `aur headless`)
**Not required for:** MCP tools inside Claude Code CLI

1. **Visit Anthropic Console**: https://console.anthropic.com

2. **Sign in** or create account

3. **Navigate to API Keys section**

4. **Click "Create Key"**

5. **Copy the API key** (starts with `sk-ant-`)

6. **Set environment variable**:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...

   # Make it permanent (optional)
   echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> ~/.bashrc
   source ~/.bashrc
   ```

**Skip this step?** Use AURORA with Claude Code CLI instead - no API key needed. See [MCP Setup Guide](../MCP_SETUP.md).

---

## Step 3: Run Your First Query (30 seconds)

```bash
# Simple informational query
aur query "What is a Python decorator?"
```

**What Happens**:
- AURORA assesses query complexity
- Chooses direct LLM (fast mode)
- Returns answer in <2 seconds

**Expected Output**:
```
→ Using Direct LLM (fast mode)

Response:
┌──────────────────────────────────────────────────────────┐
│ A Python decorator is a function that modifies the       │
│ behavior of another function. It's a way to add          │
│ functionality to existing functions without modifying    │
│ their source code directly.                              │
│                                                          │
│ Example:                                                 │
│ @timer                                                   │
│ def my_function():                                       │
│     # function body                                      │
└──────────────────────────────────────────────────────────┘
```

---

## Step 4: Index Your Codebase (1 minute)

```bash
# Navigate to your project
cd /path/to/your/project

# Index Python files
aur mem index
```

**What Happens**:
- Recursively scans directory
- Parses Python files
- Extracts functions, classes, methods
- Stores in `aurora.db`

**Expected Output**:
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

---

## Step 5: Query with Context (30 seconds)

```bash
# Complex query using indexed codebase
aur query "How does the authentication system work?"
```

**What Happens**:
- AURORA assesses query complexity
- Detects need for code context
- Searches indexed memory
- Retrieves relevant code chunks
- Uses full SOAR pipeline
- Returns comprehensive answer

**Expected Output**:
```
→ Using AURORA (full pipeline)

Response:
┌──────────────────────────────────────────────────────────┐
│ Based on your codebase, the authentication system uses:  │
│                                                          │
│ 1. JWT tokens (auth/tokens.py)                          │
│ 2. Session middleware (middleware/auth.py)               │
│ 3. User model (models/user.py)                          │
│                                                          │
│ Flow:                                                    │
│ - Login: authenticate_user() validates credentials       │
│ - Token: generate_jwt() creates signed token            │
│ - Validation: AuthMiddleware.validate() checks token    │
│ - Permissions: check_permission() enforces access        │
└──────────────────────────────────────────────────────────┘
```

---

## Next Steps

### Try Different Query Modes

**Force Direct LLM** (fastest):
```bash
aur query "Explain list comprehensions" --force-direct
```

**Force AURORA** (most comprehensive):
```bash
aur query "What is recursion?" --force-aurora --verbose
```

**Show Reasoning** (see decision process):
```bash
aur query "Design API endpoints" --show-reasoning
```

**Dry Run** (test without API calls):
```bash
aur query "test" --dry-run
```

### Search Your Codebase

```bash
# Search for specific functionality
aur mem search "authentication"

# View statistics
aur mem stats

# Search with more results
aur mem search "database" --limit 10 --show-content
```

### Explore Headless Mode

```bash
# Create experiment prompt
cat > experiment.md <<EOF
## Goal
Add docstrings to all functions in auth.py

## Success Criteria
- All functions have docstrings
- Docstrings follow Google style

## Constraints
- Budget: $2.00
- Max iterations: 5
EOF

# Run headless experiment
aur headless experiment.md --dry-run
```

---

## Common Workflows

### Workflow 1: Understand Existing Code

```bash
# 1. Index codebase
cd /path/to/project
aur mem index

# 2. Ask about architecture
aur query "Explain the overall architecture"

# 3. Search for specific patterns
aur mem search "database queries"

# 4. Deep dive into components
aur query "How does the caching layer work?"
```

### Workflow 2: Generate New Code

```bash
# 1. Describe what you need
aur query "Create a REST API endpoint for user registration" --force-aurora

# 2. Review response
# (AURORA provides code with context from your project)

# 3. Ask follow-ups
aur query "Add input validation to the registration endpoint"
```

### Workflow 3: Debug Issues

```bash
# 1. Index recent changes
aur mem index src/

# 2. Query about the bug
aur query "Why is the login endpoint returning 401?"

# 3. Get context-aware suggestions
# (AURORA analyzes your auth code and suggests fixes)
```

---

## Quick Reference

### Essential Commands

```bash
# Setup
aur init                              # Interactive setup

# Queries
aur query "your question"             # Basic query
aur query "question" --verbose        # Show SOAR phases
aur query "question" --dry-run        # Test without API calls

# Memory
aur mem index                         # Index current directory
aur mem search "term"                 # Search memory
aur mem stats                         # View statistics

# Headless
aur headless experiment.md            # Run autonomous experiment
```

### Configuration Files

```bash
~/.aurora/config.json                 # User config
./aurora.config.json                  # Project config
./aurora.db                           # Memory database
```

### Environment Variables

```bash
ANTHROPIC_API_KEY                     # API key (required)
AURORA_ESCALATION_THRESHOLD           # Complexity threshold
AURORA_LOGGING_LEVEL                  # Log verbosity
```

---

## Troubleshooting Quick Fixes

### "ANTHROPIC_API_KEY not found"

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### "Database locked"

```bash
ps aux | grep aur
kill <pid>
rm aurora.db-wal aurora.db-shm
```

### "Rate limit exceeded"

```bash
# Wait 5 seconds (auto-retry enabled)
# Or use direct mode:
aur query "question" --force-direct
```

### "No results found"

```bash
# Re-index
aur mem index

# Verify
aur mem stats
```

---

## Learning Resources

### Documentation

- **Full CLI Guide**: [CLI_USAGE_GUIDE.md](CLI_USAGE_GUIDE.md)
- **Error Reference**: [ERROR_CATALOG.md](ERROR_CATALOG.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Main README**: [../../README.md](../../README.md)

### Examples

See `packages/examples/` for:
- Smoke tests showing API usage
- Integration test examples
- Common workflow patterns

### Community

- **GitHub**: https://github.com/aurora-project/aurora
- **Issues**: https://github.com/aurora-project/aurora/issues
- **Discussions**: https://github.com/aurora-project/aurora/discussions

---

## Tips for Success

1. **Index before querying**: Better context = better answers
2. **Use dry-run**: Test configuration without costs
3. **Start simple**: Use `--force-direct` for quick questions
4. **Use verbose**: Learn how AURORA reasons with `--verbose`
5. **Check costs**: Use `--dry-run` to estimate expenses

---

**Congratulations!** You've completed the quick start guide.

You can now:
- ✓ Run queries against LLM
- ✓ Index and search your codebase
- ✓ Get context-aware answers
- ✓ Understand escalation behavior

**Next**: Explore the [CLI Usage Guide](CLI_USAGE_GUIDE.md) for advanced features.
