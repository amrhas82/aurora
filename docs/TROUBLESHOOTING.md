# AURORA Troubleshooting Guide

This guide provides solutions to common issues you might encounter when using AURORA.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [CLI Issues](#cli-issues)
3. [MCP Server Issues](#mcp-server-issues)
4. [Memory/Indexing Issues](#memoryindexing-issues)
5. [Query Issues](#query-issues)
6. [Weak Match Warnings and Retrieval Quality](#weak-match-warnings-and-retrieval-quality)
7. [MCP Query Errors](#mcp-query-errors)
8. [Diagnostic Commands](#diagnostic-commands)
9. [Getting Help](#getting-help)

---

## Installation Issues

### Permission Errors During Installation

**Error:**
```
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**Solution:**
- Don't use `sudo pip` (installs to system Python, can break your system)
- Use a virtual environment:
  ```bash
  python3 -m venv aurora-env
  source aurora-env/bin/activate  # On Windows: aurora-env\Scripts\activate
  pip install aurora
  ```
- Or install for current user only:
  ```bash
  pip install --user aurora
  ```

### Missing Dependencies

**Error:**
```
ModuleNotFoundError: No module named 'sentence_transformers'
```

**Solution:**
Install ML dependencies explicitly:
```bash
pip install aurora[ml]
```

Or install all optional dependencies:
```bash
pip install aurora[all]
```

### Python Version Too Old

**Error:**
```
ERROR: Package 'aurora' requires a different Python: 3.8.0 not in '>=3.10'
```

**Solution:**
AURORA requires Python 3.10 or higher. Check your version:
```bash
python --version
```

Install Python 3.10+ from [python.org](https://www.python.org/downloads/) or use a version manager like [pyenv](https://github.com/pyenv/pyenv).

### CLI Command Not Found After Installation

**Error:**
```bash
aur --help
# bash: aur: command not found
```

**Solution:**
1. Verify installation:
   ```bash
   pip show aurora-cli
   ```

2. Check if CLI scripts directory is in your PATH:
   ```bash
   # Linux/macOS
   echo $PATH | grep -q "$(python -m site --user-base)/bin" && echo "In PATH" || echo "Not in PATH"

   # Windows PowerShell
   $env:PATH -split ';' | Where-Object { $_ -like "*Scripts*" }
   ```

3. Add to PATH if missing:
   ```bash
   # Linux/macOS - Add to ~/.bashrc or ~/.zshrc
   export PATH="$(python -m site --user-base)/bin:$PATH"

   # Windows PowerShell - Add to $PROFILE
   $env:PATH += ";$(python -m site --user-site)\Scripts"
   ```

4. Or use the full path:
   ```bash
   python -m aurora_cli --help
   ```

---

## CLI Issues

### Config File Not Found

**Error:**
```
Error: Config file not found at ~/.aurora/config.json
```

**Solution:**
Initialize AURORA configuration:
```bash
aur init
```

Follow the prompts to set up your API keys and preferences.

### Invalid Config File

**Error:**
```
Error: Invalid config format
```

**Solution:**
1. Backup existing config:
   ```bash
   cp ~/.aurora/config.json ~/.aurora/config.json.backup
   ```

2. Reinitialize:
   ```bash
   aur init
   ```

3. Or manually validate JSON syntax:
   ```bash
   python -m json.tool ~/.aurora/config.json
   ```

### "aur init" Creates Config in Wrong Location

**Issue:**
`aur init` creates config in current directory instead of `~/.aurora/`

**Solution:**
This was a bug fixed in v0.2.0. Update AURORA:
```bash
pip install --upgrade aurora
```

If you have a local config file, move it:
```bash
mkdir -p ~/.aurora
mv config.json ~/.aurora/
```

### Headless Mode Not Working

**Error:**
```bash
aur --headless test.md
# Error: unrecognized arguments: --headless
```

**Solution:**
Update to AURORA v0.2.0+ which includes the flexible `--headless` flag:
```bash
pip install --upgrade aurora
```

Verify version:
```bash
aur --version
```

### Command Completes But No Output

**Issue:**
Commands like `aur mem search "function"` run without errors but display no results.

**Solution:**
1. Verify database has indexed chunks:
   ```bash
   aur mem stats
   ```

2. If no chunks, index your codebase:
   ```bash
   aur mem index /path/to/your/code
   ```

3. Check database location:
   ```bash
   aur --verify
   ```

---

## MCP Server Issues

### Claude Code CLI Can't Find AURORA Tools

**Symptom:**
Ask Claude "Search my codebase for authentication", Claude responds "I don't have access to codebase search tools"

**Solution:**
1. Verify MCP server is configured:
   ```bash
   aurora-mcp status
   ```

2. Check configuration file exists:
   - **macOS**: `~/Library/Application Support/Claude/~/.claude/plugins/aurora/.mcp.json`
   - **Linux**: `~/.config/Claude/~/.claude/plugins/aurora/.mcp.json`
   - **Windows**: `%APPDATA%\Claude\~/.claude/plugins/aurora/.mcp.json`

3. Verify configuration format (see [MCP_SETUP.md](MCP_SETUP.md#configuration)):
   ```json
   {
     "mcpServers": {
       "aurora": {
         "command": "python",
         "args": ["-m", "aurora.mcp.server"]
       }
     }
   }
   ```

4. Restart Claude Code CLI completely (Quit, not just close window)

5. Check MCP logs for errors:
   ```bash
   tail -f ~/.aurora/mcp.log
   ```

### MCP Server Fails to Start

**Error in logs:**
```
ModuleNotFoundError: No module named 'fastmcp'
```

**Solution:**
Install MCP dependencies:
```bash
pip install aurora[mcp]
# Or
pip install fastmcp
```

### MCP Server Can't Find Database

**Error in logs:**
```
Error: Database not found at ~/.aurora/memory.db
```

**Solution:**
1. Index your codebase first:
   ```bash
   aur mem index /path/to/your/code
   ```

2. Verify database exists:
   ```bash
   ls -lh ~/.aurora/memory.db
   ```

3. Or specify custom database path in config:
   ```json
   {
     "mcpServers": {
       "aurora": {
         "command": "python",
         "args": [
           "-m", "aurora.mcp.server",
           "--db-path", "/custom/path/memory.db"
         ]
       }
     }
   }
   ```

### MCP Tools Return Errors

**Error in Claude:**
"Error executing aurora_search: [Errno 13] Permission denied"

**Solution:**
1. Check database file permissions:
   ```bash
   ls -l ~/.aurora/memory.db
   chmod 644 ~/.aurora/memory.db
   ```

2. Check Python environment matches:
   ```bash
   # Which Python does Claude Code CLI use?
   which python

   # Which Python has aurora installed?
   python -c "import aurora; print(aurora.__file__)"
   ```

3. Use absolute path in MCP config:
   ```json
   {
     "command": "/full/path/to/python",
     "args": ["-m", "aurora.mcp.server"]
   }
   ```

### MCP Server Performance Issues

**Symptom:**
Search queries take >10 seconds to return results

**Solution:**
1. Check database size and fragmentation:
   ```bash
   aur mem stats
   ```

2. If database is very large (>500MB), consider:
   - Indexing only relevant directories
   - Excluding test files and vendor code
   - Using file patterns: `aur mem index src/ --pattern "*.py"`

3. Optimize database:
   ```bash
   sqlite3 ~/.aurora/memory.db "VACUUM;"
   ```

4. Increase performance logging:
   ```bash
   # Check logs for slow operations
   grep "latency=[0-9]*ms" ~/.aurora/mcp.log | sort -t= -k2 -n | tail -20
   ```

---

## Memory/Indexing Issues

### "aur mem index" Fails with Import Error

**Error:**
```
ModuleNotFoundError: No module named 'aurora_core'
```

**Solution:**
This indicates old import paths. Update to v0.2.0:
```bash
pip install --upgrade aurora
```

If still occurring, verify installation:
```bash
aur --verify
```

### Indexing Takes Very Long

**Symptom:**
`aur mem index` runs for >30 minutes on medium codebase (~1000 files)

**Solution:**
1. Use more specific paths:
   ```bash
   aur mem index src/  # Instead of entire repo
   ```

2. Exclude common directories:
   ```bash
   # Create .aurorignore file (similar to .gitignore)
   echo "node_modules/" >> .aurorignore
   echo "venv/" >> .aurorignore
   echo "__pycache__/" >> .aurorignore
   ```

3. Limit file size (skip large generated files):
   ```bash
   find src/ -name "*.py" -size -1M | xargs aur mem index
   ```

### Embeddings Generation Fails

**Error:**
```
RuntimeError: Failed to generate embeddings
```

**Solution:**
1. Verify ML dependencies:
   ```bash
   python -c "from sentence_transformers import SentenceTransformer; print('OK')"
   ```

2. Install/reinstall ML dependencies:
   ```bash
   pip install --upgrade sentence-transformers torch
   ```

3. Check available memory (embeddings require ~500MB RAM):
   ```bash
   free -h  # Linux
   vm_stat  # macOS
   ```

4. Use smaller model if memory constrained (edit config):
   ```json
   {
     "embeddings": {
       "model": "sentence-transformers/all-MiniLM-L6-v2"
     }
   }
   ```

### Database Corruption

**Error:**
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solution:**
1. Backup database:
   ```bash
   cp ~/.aurora/memory.db ~/.aurora/memory.db.backup
   ```

2. Try repair:
   ```bash
   sqlite3 ~/.aurora/memory.db ".recover" | sqlite3 ~/.aurora/memory_recovered.db
   mv ~/.aurora/memory_recovered.db ~/.aurora/memory.db
   ```

3. If repair fails, rebuild index:
   ```bash
   rm ~/.aurora/memory.db
   aur mem index /path/to/your/code
   ```

---

## Query Issues

### API Key Errors

**Error:**
```
Error: OpenAI API key not found
```

**Solution:**
1. Set API key during init:
   ```bash
   aur init
   ```

2. Or set environment variable:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

3. Or edit config directly:
   ```json
   {
     "api_keys": {
       "openai": "sk-..."
     }
   }
   ```

---

## Weak Match Warnings and Retrieval Quality

AURORA's retrieval quality system helps you understand when your indexed memory might not have enough relevant information for a query. This section explains the warnings you might see and how to respond.

### Understanding Retrieval Quality

When you run `aur query`, AURORA assesses the quality of retrieved context using two metrics:

1. **Groundedness Score** (≥0.7 is good): Measures how well the decomposed query is supported by retrieved chunks
2. **High-Quality Chunks** (≥3 needed): Chunks with activation score ≥0.3 are considered high-quality

**Three Quality Levels:**

| Quality | Chunks | Groundedness | High-Quality | Behavior |
|---------|--------|--------------|--------------|----------|
| **NONE** | 0 | N/A | 0 | Auto-proceeds with LLM general knowledge |
| **WEAK** | >0 | <0.7 OR | <3 | **Interactive prompt** (3 options) |
| **GOOD** | >0 | ≥0.7 AND | ≥3 | Auto-proceeds with chunks |

### Weak Match Warning

When retrieval quality is **WEAK**, you'll see an interactive prompt:

```
⚠ Weak Match Warning
═══════════════════════════════════════════════════════════
Retrieved context has low quality:
  • Groundedness: 0.55 (threshold: 0.7)
  • High-quality chunks: 2/5 (need: 3+)

The indexed memory may not have enough relevant information for this query.
═══════════════════════════════════════════════════════════

How would you like to proceed?

  1. Start anew - Clear weak chunks and use LLM general knowledge
  2. Start over - Rephrase your query and try again
  3. Continue - Proceed with available chunks (may be incomplete)

Choice [1-3]:
```

### When to Choose Each Option

**Option 1: Start anew (use general knowledge)**
- Best when: Query is outside your indexed codebase domain
- Example: You ask "How does OAuth2 work?" but your codebase doesn't implement OAuth
- Result: Clears weak chunks, proceeds with LLM's general knowledge

**Option 2: Start over (rephrase query)**
- Best when: Your phrasing might not match how code is written
- Example: You ask "authentication" but code uses "auth" or "login"
- Result: Exits so you can rephrase and try again
- Tips for better queries:
  - Use exact function/class names from your code
  - Include file names if you know them
  - Use technical terms from your domain
  - Try broader terms (e.g., "user login" instead of "JWT validation")

**Option 3: Continue (use weak chunks)**
- Best when: Partial context is better than none
- Example: Query about a feature that's partially implemented
- Result: Proceeds with available chunks, but answer may be incomplete
- When to use: You understand the limitations and want to see what's available

### Common Scenarios

#### Scenario 1: Empty Index (0 Chunks)

```bash
aur query "how does authentication work?"
```

**What happens:**
- No interactive prompt shown
- Message: "No indexed context available. Using LLM general knowledge."
- Query proceeds normally with LLM's base knowledge

**Solution:**
Index your codebase first:
```bash
aur mem index /path/to/your/code
aur mem stats  # Verify chunks were indexed
```

#### Scenario 2: Low Groundedness (<0.7)

**What causes this:**
- Query decomposition doesn't align well with retrieved chunks
- Chunks are tangentially related but not directly relevant
- Query is too broad or abstract

**Example:**
```bash
aur query "explain the architecture"
# Retrieved chunks about individual functions (groundedness: 0.6)
```

**Solution:**
- Be more specific: `aur query "explain the authentication architecture"`
- Use concrete terms: `aur query "how do the User and Auth classes interact?"`
- Reference specific files: `aur query "what does auth_manager.py do?"`

#### Scenario 3: Insufficient High-Quality Chunks (<3)

**What causes this:**
- Only a few chunks have high activation (≥0.3)
- Most retrieved chunks have low relevance scores
- Your query term appears rarely in the codebase

**Example:**
```bash
aur query "database migration"
# Only 2 chunks mention "migration" (high-quality: 2)
```

**Solution:**
- Check if feature exists: `aur mem search "migration"`
- Use broader terms: `aur query "database schema changes"`
- Verify indexing: `aur mem stats` to ensure all files are indexed

#### Scenario 4: Query Outside Codebase Domain

**What causes this:**
- Asking about concepts not implemented in your code
- Generic programming questions unrelated to your project

**Example:**
```bash
# Your project: web scraper in Python
aur query "how do React hooks work?"
# Weak match: Python code doesn't mention React
```

**Solution:**
- Choose **Option 1 (Start anew)** to use LLM general knowledge
- Or rephrase to relate to your codebase: `aur query "how does the scraper handle state?"`

### Disabling Interactive Prompts

For automation, CI/CD, or scripting, use `--non-interactive`:

```bash
aur query "test query" --non-interactive
```

**Behavior with `--non-interactive`:**
- No prompts shown (silent execution)
- WEAK matches auto-continue with available chunks
- Logs quality metadata for debugging
- Suitable for batch processing or scripts

**When to use:**
- CI/CD pipelines
- Automated documentation generation
- Batch query processing
- Scripting workflows

### Interpreting Quality Metrics

**Groundedness Score:**
- **0.8-1.0**: Excellent - Retrieved chunks strongly support the query
- **0.7-0.8**: Good - Adequate support with minor gaps
- **0.5-0.7**: Weak - Chunks are tangentially related
- **<0.5**: Poor - Chunks don't align well with query

**Activation Threshold (0.3):**
- Based on ACT-R cognitive architecture
- Chunks with activation ≥0.3 are considered "readily accessible" in memory
- Lower activation = less relevant or less frequently accessed
- Formula: Base-level activation (frequency + recency) + spreading activation + context boost

### Troubleshooting Persistent Weak Matches

If you consistently see weak match warnings:

1. **Check index status:**
   ```bash
   aur mem stats
   ```
   Verify chunks are indexed and count looks reasonable

2. **Verify query domain match:**
   ```bash
   aur mem search "key terms from your query"
   ```
   Confirms those terms exist in indexed code

3. **Reindex with updated files:**
   ```bash
   aur mem index /path/to/code --force
   ```
   Refreshes index with latest code changes

4. **Check activation scores:**
   Use `--show-reasoning` to see which chunks were retrieved and their scores:
   ```bash
   aur query "your query" --show-reasoning
   ```

5. **Adjust query phrasing:**
   - Match terminology used in your code
   - Use exact class/function names
   - Be more specific or more general depending on results

### Example Workflows

**Good Match (No Prompt):**
```bash
$ aur query "how does UserAuth.login work?"

# Retrieves 5 chunks with groundedness=0.85, high-quality=5
# No prompt shown, proceeds automatically

The UserAuth.login method in auth_manager.py:42 validates credentials
by checking the password hash against the database...
```

**Weak Match (Interactive):**
```bash
$ aur query "authentication flow"

⚠ Weak Match Warning
  • Groundedness: 0.62 (threshold: 0.7)
  • High-quality chunks: 2/8 (need: 3+)

How would you like to proceed?
Choice [1-3]: 2

# User rephrases:
$ aur query "how does login authentication work in auth_manager.py?"

# Better match - proceeds with good quality chunks
```

**No Match (Auto-Proceed):**
```bash
$ aur query "what is OAuth2?"

No indexed context available. Using LLM general knowledge.

OAuth2 is an authorization framework that enables applications to obtain
limited access to user accounts...
```

### Related Documentation

- [CLI Usage Guide - Retrieval Quality Section](cli/CLI_USAGE_GUIDE.md#retrieval-quality-handling) - Detailed interactive prompt documentation
- [SOAR Architecture](architecture/SOAR_ARCHITECTURE.md) - How retrieval quality fits into the 9-phase pipeline
- [API Contracts](architecture/API_CONTRACTS_v1.0.md) - VerifyPhaseResult.retrieval_quality field

---

## MCP Query Errors

**Important:** MCP tools do NOT require API keys. The errors below only apply to standalone CLI usage (`aur query`).

MCP tools return structured JSON errors with actionable suggestions. Here are error types and their solutions:

### BudgetExceeded (CLI only)

**Error:**
```json
{
  "error": {
    "type": "BudgetExceeded",
    "message": "Monthly budget limit reached. Cannot execute query.",
    "suggestion": "To fix this:\n1. Increase your monthly limit...",
    "details": {
      "current_usage_usd": 49.50,
      "monthly_limit_usd": 50.00,
      "estimated_query_cost_usd": 0.05
    }
  }
}
```

**Solution:**
1. Increase monthly limit in `~/.aurora/config.json`:
   ```json
   {
     "budget": {
       "monthly_limit_usd": 100.0
     }
   }
   ```

2. Wait until next month for budget reset

3. Reset usage manually by editing `~/.aurora/budget_tracker.json`:
   ```json
   {
     "monthly_usage_usd": 0.0,
     "monthly_limit_usd": 50.0
   }
   ```

### InvalidParameter

**Error:**
```json
{
  "error": {
    "type": "InvalidParameter",
    "message": "Temperature must be between 0.0 and 1.0, got 1.5",
    "suggestion": "Please check parameter values and try again..."
  }
}
```

**Valid parameter ranges:**
- `query`: Non-empty string (required)
- `temperature`: 0.0 to 1.0
- `max_tokens`: Positive integer (e.g., 100-8000)
- `model`: Valid model string (e.g., "claude-sonnet-4-20250514")

### SOARPhaseFailed

**Error:**
```json
{
  "error": {
    "type": "SOARPhaseFailed",
    "message": "SOAR pipeline failed at Retrieve phase",
    "suggestion": "Check memory index and retry..."
  }
}
```

**Solution:**
1. Check if codebase is indexed:
   ```bash
   aur mem stats
   ```

2. Reindex if needed:
   ```bash
   aur mem index /path/to/code
   ```

3. Check MCP logs for details:
   ```bash
   tail -f ~/.aurora/logs/mcp.log
   ```

### MemoryUnavailable

**Note:** This is logged as a warning, not returned as an error. Queries continue with LLM base knowledge.

**Log message:**
```
WARNING: Memory store not available. Answering from base knowledge.
```

**Solution:**
1. Index your codebase:
   ```bash
   aur mem index /path/to/code
   ```

2. Verify database exists:
   ```bash
   ls -lh ~/.aurora/memory.db
   ```

### LLMAPIFailure

**Error:**
```json
{
  "error": {
    "type": "LLMAPIFailure",
    "message": "LLM API request failed after 3 retries",
    "suggestion": "Check API status and retry..."
  }
}
```

**Solution:**
1. Check Anthropic API status: https://status.anthropic.com/

2. Verify API key is valid:
   ```bash
   curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -d '{"model": "claude-sonnet-4-20250514", "max_tokens": 10, "messages": [{"role": "user", "content": "Hi"}]}'
   ```

3. Check for rate limiting (wait and retry)

4. Check network connectivity

### UnexpectedError

**Error:**
```json
{
  "error": {
    "type": "UnexpectedError",
    "message": "An unexpected error occurred: [details]",
    "suggestion": "Please check the logs at ~/.aurora/logs/mcp.log for details."
  }
}
```

**Solution:**
1. Check MCP logs:
   ```bash
   tail -100 ~/.aurora/logs/mcp.log
   ```

2. Look for stack traces and error details

3. Report issue with logs if problem persists

### Checking MCP Query Logs

All aurora_query errors are logged to `~/.aurora/logs/mcp.log`:

```bash
# View recent errors
grep "ERROR" ~/.aurora/logs/mcp.log | tail -20

# Watch logs in real-time
tail -f ~/.aurora/logs/mcp.log

# Filter for specific error type
grep "APIKeyMissing\|BudgetExceeded" ~/.aurora/logs/mcp.log
```

### Dry-Run Import Error

**Error:**
```
ImportError: cannot import name 'HybridRetriever' from 'aurora_context_code.semantic'
```

**Solution:**
Fixed in v0.2.0. Update AURORA:
```bash
pip install --upgrade aurora
```

### Query Returns No Results

**Issue:**
`aur query "how does X work?"` completes but returns empty response

**Solution:**
1. Verify chunks indexed:
   ```bash
   aur mem stats
   ```

2. Try search first to verify retrieval works:
   ```bash
   aur mem search "relevant term"
   ```

3. Lower similarity threshold:
   ```bash
   aur query "how does X work?" --threshold 0.3
   ```

4. Use `--show-reasoning` to debug:
   ```bash
   aur query "how does X work?" --show-reasoning
   ```

---

## Diagnostic Commands

Use these commands to diagnose issues:

### Installation Verification
```bash
aur --verify
```
**Checks:**
- All 6 AURORA packages installed
- CLI available in PATH
- MCP server binary exists
- Python version >= 3.10
- ML dependencies (warns if missing)
- Config file exists (warns if missing)

**Exit codes:**
- 0: All checks pass
- 1: Warnings (non-critical issues)
- 2: Critical failures

### MCP Server Status
```bash
aurora-mcp status
```
**Shows:**
- Current mode (always-on vs on-demand)
- Configuration file location
- Database location and size
- Recent log entries
- Platform-specific setup instructions

### Memory Statistics
```bash
aur mem stats
```
**Shows:**
- Total chunks indexed
- Total files indexed
- Database size (MB)
- Last indexed timestamp

### Check Logs

**CLI logs:**
```bash
# If using --log-file flag
tail -f ~/.aurora/aurora.log
```

**MCP logs:**
```bash
tail -f ~/.aurora/mcp.log
```

**Filter for errors:**
```bash
grep "ERROR\|error" ~/.aurora/mcp.log | tail -20
```

### Test Basic Functionality

**Quick smoke test:**
```bash
# Create test directory
mkdir -p /tmp/aurora-test
echo "def test(): pass" > /tmp/aurora-test/test.py

# Index
aur mem index /tmp/aurora-test

# Search
aur mem search "test"

# Stats
aur mem stats

# Cleanup
rm -rf /tmp/aurora-test
```

---

## Getting Help

### Check Documentation
- [MCP Setup Guide](MCP_SETUP.md) - Detailed MCP configuration
- [README](../README.md) - Quick start and features
- [CHANGELOG](../CHANGELOG.md) - Version history and breaking changes

### Common Error Messages Reference

| Error Message | Likely Cause | Quick Fix |
|--------------|--------------|-----------|
| `ModuleNotFoundError: No module named 'aurora_core'` | Old import paths | `pip install --upgrade aurora` |
| `Config file not found` | Not initialized | `aur init` |
| `Permission denied` | Wrong permissions | `chmod 644 ~/.aurora/*.db` |
| `Database locked` | Concurrent access | Wait and retry |
| `API key not found` | Not configured | `aur init` |
| `Embeddings generation failed` | Missing ML deps | `pip install aurora[ml]` |

### Report Issues

If you're experiencing an issue not covered here:

1. **Collect diagnostic information:**
   ```bash
   aur --verify > aurora-diagnostic.txt
   aurora-mcp status >> aurora-diagnostic.txt
   python --version >> aurora-diagnostic.txt
   pip show aurora aurora-cli aurora-core >> aurora-diagnostic.txt
   ```

2. **Check recent logs:**
   ```bash
   tail -100 ~/.aurora/mcp.log > aurora-logs.txt
   ```

3. **Create a minimal reproduction:**
   - What command did you run?
   - What was the expected behavior?
   - What actually happened?
   - Can you reproduce it consistently?

4. **Open a GitHub issue:**
   - Repository: [github.com/yourusername/aurora](https://github.com/yourusername/aurora) (update with actual repo URL)
   - Include: diagnostic output, logs, reproduction steps
   - Redact any sensitive information (API keys, file paths)

### Community Support

- **GitHub Discussions**: Ask questions, share tips
- **GitHub Issues**: Report bugs, request features
- **Documentation**: Comprehensive guides and API reference

---

## Platform-Specific Notes

### Windows

**PowerShell execution policy:**
If scripts are blocked, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Path separators:**
Use forward slashes or raw strings:
```powershell
aur mem index C:/projects/mycode
# Or
aur mem index "C:\projects\mycode"
```

**Claude Code CLI config location:**
```
%APPDATA%\Claude\~/.claude/plugins/aurora/.mcp.json
```

### macOS

**Gatekeeper warnings:**
If you see "python can't be opened because it is from an unidentified developer":
```bash
xattr -d com.apple.quarantine $(which python)
```

**Apple Silicon (M1/M2):**
Some ML dependencies may require Rosetta 2 or native ARM builds. Use:
```bash
pip install --upgrade sentence-transformers torch
```

**Claude Code CLI config location:**
```
~/Library/Application Support/Claude/~/.claude/plugins/aurora/.mcp.json
```

### Linux

**AppArmor/SELinux:**
If seeing permission errors despite correct file permissions:
```bash
# Check for denials
sudo ausearch -m avc -ts recent
```

**Python version conflicts:**
Use `python3` explicitly:
```bash
python3 -m pip install aurora
python3 -m aurora_cli --help
```

**Claude Code CLI config location:**
```
~/.config/Claude/~/.claude/plugins/aurora/.mcp.json
```

---

## Frequently Asked Questions

### Q: Do I need an API key to use AURORA?

**A:**
- **MCP tools (inside Claude Code CLI):** No API key required
- **Standalone CLI `aur query`:** Requires `ANTHROPIC_API_KEY`
- **Memory commands (`aur mem`):** No API key required

For most users, MCP integration is recommended (no API key, seamless workflow).

### Q: How much disk space does indexing use?

**A:** Roughly 10-20MB per 1000 Python files (including embeddings). A medium codebase (~5000 files) typically uses ~100MB.

### Q: Can I use AURORA with non-Python code?

**A:** Currently optimized for Python. Other languages work for basic search but may lack advanced features (function extraction, AST parsing).

### Q: How often should I reindex?

**A:** After significant code changes. MCP tools use existing index, so reindex when:
- Adding new files
- Major refactoring
- Switching branches with different code

### Q: Can multiple projects use the same database?

**A:** Yes, but recommended to use separate databases for clarity:
```bash
aur mem index ~/project1 --db ~/.aurora/project1.db
aur mem index ~/project2 --db ~/.aurora/project2.db
```

### Q: Is AURORA safe to use with proprietary code?

**A:** Yes. All indexing and search happens locally. Only `aur query` sends data to external APIs (OpenAI/Anthropic), and you can use `--dry-run` to see what would be sent before actual API calls.

---

**Last Updated:** 2025-01-24 (AURORA v0.2.0)
