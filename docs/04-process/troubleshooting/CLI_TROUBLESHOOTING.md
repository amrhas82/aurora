# AURORA CLI Troubleshooting Guide

Practical solutions for common issues and debugging techniques.

**Version**: 1.1.0
**Last Updated**: 2024-12-24

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [API and Authentication](#api-and-authentication)
3. [Memory Store Issues](#memory-store-issues)
4. [Performance Problems](#performance-problems)
5. [Query Issues](#query-issues)
6. [Configuration Problems](#configuration-problems)
7. [Debugging Techniques](#debugging-techniques)
8. [Platform-Specific Issues](#platform-specific-issues)

---

## Installation Issues

### pip install fails

**Symptom**:
```bash
pip install -e packages/cli
ERROR: Could not find a version that satisfies requirement...
```

**Solutions**:

1. **Check Python version**:
   ```bash
   python --version
   # Must be 3.10 or higher
   ```

2. **Upgrade pip**:
   ```bash
   python -m pip install --upgrade pip
   ```

3. **Install from project root**:
   ```bash
   # Must be in aurora/ directory
   cd /path/to/aurora
   pip install -e packages/cli
   ```

4. **Check dependencies**:
   ```bash
   # Install core first
   pip install -e packages/core
   pip install -e packages/cli
   ```

---

### Command not found: aur

**Symptom**:
```bash
aur --version
bash: aur: command not found
```

**Solutions**:

1. **Check installation**:
   ```bash
   pip show aurora-cli
   # Should show installed package
   ```

2. **Check PATH**:
   ```bash
   echo $PATH
   # Should include Python scripts directory
   ```

3. **Find binary location**:
   ```bash
   which aur
   find ~ -name "aur" -type f 2>/dev/null
   ```

4. **Add to PATH** (if needed):
   ```bash
   # Find Python scripts directory
   python -m site --user-base

   # Add to PATH
   export PATH="$HOME/.local/bin:$PATH"
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

5. **Use Python module directly**:
   ```bash
   # Alternative if PATH doesn't work
   python -m aurora_cli query "test"
   ```

---

### Rate limiting too aggressive

**Symptom**:
```
[API] Rate limit exceeded.
```

**Diagnosis**:
```bash
# Check request frequency
tail -f ~/.aurora/aurora.log | grep -i "rate"

# Count recent requests
grep "$(date +%Y-%m-%d)" ~/.aurora/aurora.log | grep -c "API request"
```

**Solutions**:

1. **Wait for rate limit reset**:
   - Tier 1: 50 requests/minute
   - Tier 2: 1000 requests/minute
   - Tier 3: 2000 requests/minute

2. **Add delays between queries**:
   ```bash
   # In scripts
   for query in "${queries[@]}"; do
       aur query "$query"
       sleep 2  # 2-second delay
   done
   ```

3. **Use direct LLM mode**:
   ```bash
   # Single API call instead of multiple
   aur query "question" --force-direct
   ```

4. **Batch queries**:
   ```bash
   # Combine related queries
   aur query "Explain authentication and authorization systems"
   # Instead of two separate queries
   ```

5. **Check for runaway processes**:
   ```bash
   ps aux | grep aur
   # Kill any stuck processes
   ```

---

## Memory Store Issues

### Database corruption after crash

**Symptom**:
```
[Memory] Memory store is corrupted.
sqlite3.DatabaseError: database disk image is malformed
```

**Diagnosis**:
```bash
# Check database integrity
sqlite3 aurora.db "PRAGMA integrity_check;"

# Check file size
ls -lh aurora.db
```

**Solutions**:

1. **Try recovery**:
   ```bash
   # Export and reimport
   sqlite3 aurora.db ".dump" > dump.sql
   sqlite3 aurora_new.db < dump.sql
   mv aurora.db aurora.db.corrupted
   mv aurora_new.db aurora.db
   ```

2. **Check for partial writes**:
   ```bash
   # Look for incomplete transactions
   sqlite3 aurora.db "SELECT name FROM sqlite_master WHERE type='table';"
   ```

3. **Reset and re-index** (last resort):
   ```bash
   # Backup first
   mv aurora.db aurora.db.backup

   # Re-index
   aur mem index
   ```

4. **Enable WAL mode** (prevention):
   ```bash
   # More crash-resistant
   sqlite3 aurora.db "PRAGMA journal_mode=WAL;"
   ```

---

### Slow indexing (>10 seconds for 100 files)

**Symptom**:
```
Indexing . ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  45%
(Progress stalls)
```

**Diagnosis**:
```bash
# Check file count
find . -name "*.py" | wc -l

# Check file sizes
find . -name "*.py" -exec ls -lh {} \; | sort -k5 -rh | head -10

# Monitor disk I/O
iostat -x 1
```

**Solutions**:

1. **Exclude large directories**:
   ```bash
   # Don't index generated code
   # Skip: node_modules/, venv/, .venv/, __pycache__/, build/, dist/

   # Manual selective indexing
   aur mem index src/
   aur mem index lib/
   ```

2. **Reduce chunk size**:
   ```json
   // In ~/.aurora/config.json
   {
     "memory": {
       "chunk_size": 500,  // Default: 1000
       "overlap": 50       // Default: 200
     }
   }
   ```

3. **Check disk performance**:
   ```bash
   # SSD should be >100 MB/s
   # HDD may be slow for many small files

   # Test disk speed
   dd if=/dev/zero of=testfile bs=1M count=1000
   ```

4. **Use SSD if available**:
   ```bash
   # Move database to faster disk
   aur mem index --db-path /ssd/aurora.db
   ```

---

### Search returns no results

**Symptom**:
```
Found 0 results for 'authentication'
```

**Diagnosis**:
```bash
# Check database exists
ls -lh aurora.db

# Check chunk count
aur mem stats

# Try broad search
aur mem search "def"  # Should match many functions
```

**Solutions**:

1. **Verify indexing completed**:
   ```bash
   aur mem stats
   # Total Chunks should be > 0
   ```

2. **Re-index if empty**:
   ```bash
   aur mem index
   ```

3. **Try broader search terms**:
   ```bash
   # Too specific: "validate_user_authentication_token"
   # Better: "authentication"
   # Even broader: "auth"
   ```

4. **Check file types indexed**:
   ```bash
   # Only Python files by default
   # JavaScript, TypeScript, etc. not yet supported
   ```

5. **Search with JSON output**:
   ```bash
   # See raw results
   aur mem search "test" --format json
   ```

---

## Performance Problems

### Queries take >30 seconds

**Symptom**:
```
aur query "question"
(Hangs for 30+ seconds)
```

**Diagnosis**:
```bash
# Enable verbose mode
aur query "question" --verbose

# Check which phase is slow
# Look for: Phase X: Y.XXs

# Monitor network
ping api.anthropic.com
```

**Solutions**:

1. **Check network latency**:
   ```bash
   ping -c 5 api.anthropic.com
   # Should be <100ms
   ```

2. **Use direct LLM**:
   ```bash
   # Skip SOAR overhead
   aur query "question" --force-direct
   ```

3. **Reduce max tokens**:
   ```json
   // In ~/.aurora/config.json
   {
     "llm": {
       "max_tokens": 1024  // Default: 4096
     }
   }
   ```

4. **Check for memory bottleneck**:
   ```bash
   # Monitor memory usage
   free -h  # Linux
   vm_stat  # macOS

   # Large database may be slow
   aur mem stats
   ```

---

### High API costs

**Symptom**:
Unexpected charges for simple queries.

**Diagnosis**:
```bash
# Use dry-run to estimate
aur query "question" --dry-run

# Check what mode is used
aur query "question" --show-reasoning

# Monitor costs in logs
grep "cost" ~/.aurora/aurora.log
```

**Solutions**:

1. **Prefer direct LLM**:
   ```bash
   # For simple queries
   aur query "What is X?" --force-direct
   ```

2. **Increase escalation threshold**:
   ```json
   // In ~/.aurora/config.json
   {
     "escalation": {
       "threshold": 0.8  // Default: 0.7
       // Higher = more queries use direct LLM
     }
   }
   ```

3. **Use smaller model** (when supported):
   ```json
   {
     "llm": {
       "model": "claude-3-haiku-20240307"  // Cheaper
     }
   }
   ```

---

## Query Issues

### Answers lack context

**Symptom**:
AURORA doesn't use knowledge from indexed codebase.

**Diagnosis**:
```bash
# Check memory is indexed
aur mem stats

# Check query uses AURORA
aur query "question" --show-reasoning

# Verify relevant chunks exist
aur mem search "relevant term"
```

**Solutions**:

1. **Force AURORA mode**:
   ```bash
   aur query "question" --force-aurora
   ```

2. **Re-index with project context**:
   ```bash
   # Index from project root
   cd /path/to/project
   aur mem index
   ```

3. **Use specific queries**:
   ```bash
   # Too vague: "How does this work?"
   # Better: "How does the login function in auth.py work?"
   ```

4. **Check search results first**:
   ```bash
   # See what context would be retrieved
   aur mem search "login authentication"
   ```

---

### Incorrect escalation decisions

**Symptom**:
Simple query uses AURORA (slow/expensive), or complex query uses direct LLM (poor answer).

**Diagnosis**:
```bash
# See escalation reasoning
aur query "question" --show-reasoning

# Check threshold
cat ~/.aurora/config.json | grep threshold
```

**Solutions**:

1. **Adjust threshold**:
   ```json
   // In ~/.aurora/config.json
   {
     "escalation": {
       "threshold": 0.6  // Lower = more AURORA
       // Range: 0.0 (always AURORA) to 1.0 (always direct)
     }
   }
   ```

2. **Force mode when needed**:
   ```bash
   # For this query only
   aur query "question" --force-aurora
   aur query "question" --force-direct
   ```

3. **Tune keyword detection**:
   ```json
   {
     "escalation": {
       "enable_keyword_only": true  // Faster assessment
     }
   }
   ```

---

## Configuration Problems

### Config file not loading

**Symptom**:
Changes to config.json have no effect.

**Diagnosis**:
```bash
# Check config is loaded
aur query "test" --dry-run
# Should show: "Configuration loaded from: ..."

# Check file location
ls -l ~/.aurora/config.json
ls -l ./aurora.config.json

# Validate JSON
python -m json.tool ~/.aurora/config.json
```

**Solutions**:

1. **Check search order**:
   ```bash
   # AURORA searches in order:
   # 1. ./aurora.config.json (project)
   # 2. ~/.aurora/config.json (user)

   # Remove project config to use user config
   rm ./aurora.config.json
   ```

2. **Verify JSON syntax**:
   ```bash
   python -m json.tool ~/.aurora/config.json
   # Should print formatted JSON
   # If error, shows line number
   ```

3. **Use environment variables** (override):
   ```bash
   # These take precedence
   export AURORA_ESCALATION_THRESHOLD=0.8
   export AURORA_LOGGING_LEVEL=DEBUG
   ```

4. **Recreate config**:
   ```bash
   mv ~/.aurora/config.json ~/.aurora/config.json.backup
   aur init
   ```

---

## Debugging Techniques

### Enable debug logging

```bash
# Global debug mode
aur --debug query "test"

# Or set in config
export AURORA_LOGGING_LEVEL=DEBUG

# View logs
tail -f ~/.aurora/aurora.log
```

### Trace API calls

```bash
# Show full request/response
export AURORA_LOG_API_CALLS=1
aur query "test" --verbose
```

### Inspect database

```bash
# SQLite shell
sqlite3 aurora.db

# Useful queries:
# Count chunks
SELECT COUNT(*) FROM chunks;

# Show recent chunks
SELECT chunk_id, file_path, type FROM chunks LIMIT 10;

# Check activations
SELECT chunk_id, activation, last_accessed FROM activations ORDER BY activation DESC LIMIT 10;

# Database size
.dbinfo

# Exit
.quit
```

### Test without API calls

```bash
# Dry-run shows configuration
aur query "test" --dry-run

# Shows escalation decision without executing
aur query "complex query" --dry-run --show-reasoning
```

### Profile performance

```bash
# Time command execution
time aur query "test"

# Verbose shows phase timing
aur query "test" --force-aurora --verbose

# System monitoring
# Terminal 1:
top -p $(pgrep -f aur)
# Terminal 2:
aur query "test"
```

---

## Platform-Specific Issues

### Linux: Permission denied

**Symptom**:
```
PermissionError: [Errno 13] Permission denied: '/home/user/.aurora/config.json'
```

**Solutions**:
```bash
# Fix directory permissions
chmod 700 ~/.aurora/

# Fix file permissions
chmod 600 ~/.aurora/config.json
chmod 644 ~/.aurora/aurora.db

# Check ownership
ls -la ~/.aurora/
sudo chown -R $USER:$USER ~/.aurora/
```

### macOS: Command not found after install

**Symptom**:
```
zsh: command not found: aur
```

**Solutions**:
```bash
# Add Python bin to PATH
echo 'export PATH="$HOME/Library/Python/3.10/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Or use Python directly
python3 -m aurora_cli query "test"

# Install with homebrew Python (alternative)
brew install python
pip3 install -e packages/cli
```

### Windows: Path issues

**Symptom**:
```
'aur' is not recognized as an internal or external command
```

**Solutions**:
```powershell
# Add Python Scripts to PATH
# 1. Find Python Scripts directory
python -m site --user-site
# Example: C:\Users\Name\AppData\Roaming\Python\Python310\Scripts

# 2. Add to PATH (PowerShell as admin)
$env:Path += ";C:\Users\Name\AppData\Roaming\Python\Python310\Scripts"

# 3. Make permanent (System Properties > Environment Variables)

# Or use Python directly
python -m aurora_cli query "test"
```

### Docker: Network isolation

**Symptom**:
```
[Network] Cannot reach external services.
```

**Solutions**:
```bash
# Mount config directory
docker run -v ~/.aurora:/root/.aurora aurora

# Use host network
docker run --network host aurora
```

---

## Getting More Help

### Collect diagnostic information

```bash
#!/bin/bash
# Create diagnostic report

echo "=== System Info ==="
uname -a
python --version
pip --version

echo -e "\n=== AURORA Version ==="
aur --version

echo -e "\n=== Configuration ==="
aur query "test" --dry-run 2>&1

echo -e "\n=== Recent Logs ==="
tail -n 50 ~/.aurora/aurora.log

echo -e "\n=== Database Stats ==="
aur mem stats 2>&1

echo -e "\n=== Environment ==="
env | grep AURORA
```

Save as `aurora-diagnostics.sh` and run:
```bash
chmod +x aurora-diagnostics.sh
./aurora-diagnostics.sh > diagnostic-report.txt
```

### Report issue

1. **Redact sensitive data** from diagnostic report
2. **Create minimal reproduction** (if possible)
3. **Open GitHub issue**: https://github.com/aurora-project/aurora/issues
4. **Include**:
   - Diagnostic report
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages (full traceback)

---

## Related Documentation

- **CLI Usage Guide**: [CLI_USAGE_GUIDE.md](CLI_USAGE_GUIDE.md) - Comprehensive command reference
- **Error Catalog**: [ERROR_CATALOG.md](ERROR_CATALOG.md) - All error codes and solutions
- **Quick Start**: [QUICK_START.md](QUICK_START.md) - Get started in 5 minutes
- **Main README**: [../../README.md](../../README.md) - Project overview

---

**Still having issues?**

- Check closed issues: https://github.com/aurora-project/aurora/issues?q=is%3Aissue+is%3Aclosed
- Ask in discussions: https://github.com/aurora-project/aurora/discussions
- Join Discord: https://discord.gg/aurora
