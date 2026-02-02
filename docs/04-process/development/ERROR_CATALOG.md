# AURORA CLI Error Catalog

Comprehensive catalog of error messages, causes, and solutions for the AURORA CLI.

**Version**: 1.1.0
**Last Updated**: 2024-12-24

---

## Table of Contents

- [API Errors](#api-errors) (ERR-001 to ERR-004)
- [Configuration Errors](#configuration-errors) (ERR-005 to ERR-007)
- [Memory Store Errors](#memory-store-errors) (ERR-008 to ERR-011)
- [Common Patterns](#common-patterns)
- [Quick Reference](#quick-reference)

---

---

### ERR-002: Rate Limit Exceeded

**Message**:
```
[API] Rate limit exceeded.
Cause: Too many requests to Anthropic API.
```

**Cause**:
- Sending too many requests in short time period
- API tier has rate limits (requests per minute)
- Burst traffic exceeding quota
- Multiple AURORA instances running

**Solutions**:

1. **Wait and retry automatically**:
   - AURORA automatically retries with exponential backoff
   - Wait 5-30 seconds for rate limit to reset
   - Progress shown: "Retrying in 5s... (attempt 2/3)"

2. **Use direct LLM mode**:
   ```bash
   # Skip AURORA overhead for simple queries
   aur query "simple question" --force-direct
   ```

3. **Increase delay between queries**:
   ```bash
   # In scripts, add delays
   aur query "query 1"
   sleep 2
   aur query "query 2"
   ```

4. **Upgrade API tier**:
   - Visit: https://console.anthropic.com/settings/billing
   - Upgrade to higher tier for increased limits
   - Standard tiers have higher requests/minute

5. **Check for multiple processes**:
   ```bash
   ps aux | grep aur
   # Kill unnecessary processes
   kill <pid>
   ```

**Related**: None

---

### ERR-003: Network Error

**Message**:
```
[Network] Cannot reach Anthropic API.
Cause: Network connectivity issue.
```

**Cause**:
- No internet connection
- Firewall blocking HTTPS traffic
- Proxy configuration issues
- DNS resolution failure
- Anthropic API service down

**Solutions**:

1. **Check internet connection**:
   ```bash
   ping api.anthropic.com
   # Expected: Reply from api.anthropic.com
   ```

2. **Check DNS resolution**:
   ```bash
   nslookup api.anthropic.com
   # Should resolve to valid IP
   ```

3. **Check firewall/proxy settings**:
   ```bash
   # If behind corporate proxy
   export HTTPS_PROXY=http://proxy.company.com:8080
   export HTTP_PROXY=http://proxy.company.com:8080
   ```

4. **Check Anthropic status**:
   - Visit: https://status.anthropic.com
   - Check for service outages
   - View incident history

5. **Try again in a few moments**:
   ```bash
   # Temporary network issues usually resolve quickly
   sleep 5
   aur query "retry query"
   ```

6. **Check SSL/TLS certificates**:
   ```bash
   # Update CA certificates if expired
   sudo apt-get update && sudo apt-get upgrade ca-certificates
   ```

**Related**: ERR-002

---

### ERR-004: Model Not Found

**Message**:
```
[API] Model not found.
Cause: Specified model does not exist or is not accessible.
```

**Cause**:
- Model name misspelled in config
- Using deprecated or removed model
- Account doesn't have access to model
- Wrong model for API tier

**Solutions**:

1. **Check model name in config**:
   ```bash
   # View current config
   cat ~/.aurora/config.json | grep model
   ```

2. **Use default model**:
   ```bash
   # Edit config to use default
   nano ~/.aurora/config.json
   # Set: "model": "claude-3-5-sonnet-20241022"
   ```

3. **Verify available models**:
   - Visit: https://docs.anthropic.com/models
   - Check supported models for your API tier
   - Verify model naming format

4. **Check API access**:
   - Some models require specific API access
   - Verify your account tier at console.anthropic.com
   - Contact support if model should be accessible

5. **Recreate config with defaults**:
   ```bash
   rm ~/.aurora/config.json
   aur init
   ```

**Common Valid Models**:
- `claude-3-5-sonnet-20241022` (recommended)
- `claude-3-5-sonnet-20240620`
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

---

## Configuration Errors

### ERR-006: Invalid Config File

**Message**:
```
[Config] Configuration file syntax error.
File: ~/.aurora/config.json
Error: Unexpected token at line 5
```

**Cause**:
- Invalid JSON syntax
- Missing commas, brackets, or quotes
- Trailing commas (not allowed in JSON)
- Comments in JSON file (not allowed)
- File encoding issues
- Manually edited and introduced syntax error

**Solutions**:

1. **Validate JSON syntax**:
   ```bash
   python -m json.tool ~/.aurora/config.json
   # Shows exact syntax error location
   ```

2. **Use online validator**:
   - Visit: https://jsonlint.com
   - Copy/paste config content
   - View highlighted errors
   - Copy corrected JSON back

3. **Recreate config file**:
   ```bash
   # Backup current (if has custom values)
   cp ~/.aurora/config.json ~/.aurora/config.json.backup

   # Recreate with defaults
   rm ~/.aurora/config.json
   aur init
   ```

4. **Common JSON errors**:
   ```json
   // ✗ WRONG: Trailing comma
   {
     "key": "value",
   }

   // ✓ CORRECT: No trailing comma
   {
     "key": "value"
   }

   // ✗ WRONG: Comments not allowed
   {
     // This is a comment
     "key": "value"
   }

   // ✓ CORRECT: No comments
   {
     "key": "value"
   }

   // ✗ WRONG: Single quotes
   {
     'key': 'value'
   }

   // ✓ CORRECT: Double quotes
   {
     "key": "value"
   }
   ```

5. **Check file permissions**:
   ```bash
   # Should be readable
   chmod 600 ~/.aurora/config.json
   ls -l ~/.aurora/config.json
   ```

**Related**: ERR-005, ERR-007

---

### ERR-007: Invalid Config Values

**Message**:
```
[Config] Invalid configuration value.
Error: escalation_threshold must be 0.0-1.0, got 1.5
```

**Cause**:
- Configuration value outside valid range
- Wrong data type (string instead of number)
- Typo in boolean value
- Invalid choice for enum field

**Solutions**:

1. **Check value ranges**:
   ```json
   {
     "escalation": {
       "threshold": 0.7,           // Must be 0.0-1.0
       "enable_keyword_only": true // Must be boolean
     },
     "llm": {
       "temperature": 0.7,          // Must be 0.0-1.0
       "max_tokens": 4096           // Must be positive integer
     },
     "memory": {
       "chunk_size": 1000,          // Must be >= 100
       "overlap": 200               // Must be >= 0
     },
     "logging": {
       "level": "INFO"              // Must be DEBUG/INFO/WARNING/ERROR/CRITICAL
     }
   }
   ```

2. **Edit config manually**:
   ```bash
   nano ~/.aurora/config.json
   # Fix invalid value
   # Save and exit
   ```

3. **Recreate with defaults**:
   ```bash
   aur init
   # Use default values
   ```

4. **View example config**:
   ```bash
   # Show full valid config structure
   cat ~/.aurora/config.json.example
   # Or view in documentation
   ```

**Valid Ranges**:

| Field | Type | Range/Values |
|-------|------|--------------|
| `escalation.threshold` | float | 0.0 - 1.0 |
| `llm.temperature` | float | 0.0 - 1.0 |
| `llm.max_tokens` | integer | 1 - 100000 |
| `memory.chunk_size` | integer | >= 100 |
| `memory.overlap` | integer | >= 0 |
| `logging.level` | string | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `llm.provider` | string | anthropic |

**Related**: ERR-006

---

## Memory Store Errors

### ERR-008: Database Locked

**Message**:
```
[Memory] Memory store is locked.
Cause: Another AURORA process is using the database.
```

**Cause**:
- Multiple AURORA CLI instances accessing same database
- Previous process crashed without releasing lock
- SQLite WAL files not cleaned up
- Permissions preventing lock cleanup
- NFS/network filesystem issues

**Solutions**:

1. **Close other AURORA processes**:
   ```bash
   # Find all AURORA processes
   ps aux | grep aur

   # Kill specific process
   kill <pid>

   # Kill all AURORA processes (careful!)
   pkill -f "aur "
   ```

2. **Wait a few seconds and retry**:
   ```bash
   # SQLite lock timeout is 5 seconds
   sleep 5
   aur mem index
   ```

3. **Remove lock files** (if stuck):
   ```bash
   # Remove Write-Ahead Log (WAL) files
   rm aurora.db-wal
   rm aurora.db-shm

   # These files are recreated automatically
   ```

4. **Check file permissions**:
   ```bash
   # Database should be writable
   ls -l aurora.db*
   chmod 644 aurora.db
   chmod 700 $(dirname aurora.db)
   ```

5. **Check filesystem type**:
   ```bash
   # SQLite has issues on some network filesystems
   df -T .
   # Prefer local filesystems (ext4, xfs, apfs, ntfs)
   ```

**Prevention**:
```bash
# Use separate databases per project
aur mem index --db-path ./project1.db
aur mem index --db-path ./project2.db

# Or use process-specific databases
aur mem index --db-path /tmp/aurora-$$.db
```

**Related**: ERR-009, ERR-011

---

### ERR-009: Insufficient Permissions

**Message**:
```
[Memory] Cannot write to memory store.
Cause: Insufficient file permissions.
```

**Cause**:
- Database file is read-only
- Directory is read-only
- Owned by different user
- SELinux/AppArmor restrictions
- Parent directory doesn't exist

**Solutions**:

1. **Fix directory permissions**:
   ```bash
   chmod 700 ~/.aurora/
   # User: read+write+execute
   # Group: none
   # Other: none
   ```

2. **Fix database permissions**:
   ```bash
   chmod 600 ~/.aurora/memory.db
   # User: read+write
   # Group: none
   # Other: none
   ```

3. **Check ownership**:
   ```bash
   ls -l ~/.aurora/
   # Should be owned by your user

   # If wrong owner
   sudo chown -R $USER:$USER ~/.aurora/
   ```

4. **Check disk space**:
   ```bash
   df -h ~/.aurora/
   # Ensure available space
   ```

5. **Create directory if missing**:
   ```bash
   mkdir -p ~/.aurora
   chmod 700 ~/.aurora
   ```

6. **Check SELinux/AppArmor** (Linux):
   ```bash
   # Check SELinux status
   getenforce

   # If enforcing, may need policy adjustment
   # Or use different directory (/tmp/, /var/tmp/)
   ```

**Alternative**: Use custom database path with correct permissions:
```bash
aur mem index --db-path /tmp/aurora.db
```

**Related**: ERR-008, ERR-010

---

### ERR-010: Disk Full

**Message**:
```
[Memory] Disk full.
Cause: Not enough disk space for operation.
```

**Cause**:
- Disk partition at 100% capacity
- Indexing large codebase
- Database growing too large
- Quota exceeded (multi-user systems)
- Temporary files filling disk

**Solutions**:

1. **Check disk usage**:
   ```bash
   df -h
   # Check available space on relevant partition
   ```

2. **Check AURORA database size**:
   ```bash
   du -sh ~/.aurora/
   du -sh aurora.db
   ```

3. **Free up disk space**:
   ```bash
   # Remove old AURORA databases
   find ~ -name "aurora.db*" -mtime +30 -delete

   # Remove backup files
   rm ~/.aurora/*.db.backup

   # Clean system temporary files
   sudo apt-get clean  # Debian/Ubuntu
   brew cleanup         # macOS
   ```

4. **Use external storage**:
   ```bash
   # Move database to larger partition
   mv ~/.aurora/memory.db /mnt/data/aurora.db
   ln -s /mnt/data/aurora.db ~/.aurora/memory.db
   ```

5. **Reduce chunk size** (before indexing):
   ```json
   // In ~/.aurora/config.json
   {
     "memory": {
       "chunk_size": 500,  // Smaller chunks
       "overlap": 50       // Less overlap
     }
   }
   ```

6. **Index selectively**:
   ```bash
   # Don't index everything
   aur mem index src/  # Just source code
   # Skip test/, docs/, node_modules/, etc.
   ```

**Estimated Space Requirements**:
- 100 files: ~5 MB
- 1,000 files: ~50 MB
- 10,000 files: ~500 MB

**Related**: ERR-009

---

### ERR-011: Corrupted Database

**Message**:
```
[Memory] Memory store is corrupted.
Cause: Database file may be damaged.
```

**Cause**:
- Sudden power loss during write
- Disk hardware failure
- Process killed during transaction
- File system corruption
- Incomplete migration
- Manual file editing

**Solutions**:

1. **Backup current database** (try to recover):
   ```bash
   cp aurora.db aurora.db.corrupted
   cp ~/.aurora/memory.db ~/.aurora/memory.db.corrupted
   ```

2. **Try SQLite recovery**:
   ```bash
   # Dump and recreate
   sqlite3 aurora.db ".dump" | sqlite3 aurora_recovered.db
   mv aurora_recovered.db aurora.db
   ```

3. **Reset memory store** (last resort):
   ```bash
   # Remove corrupted database
   rm aurora.db
   rm ~/.aurora/memory.db

   # Re-index codebase
   aur mem index .
   ```

4. **Check disk health**:
   ```bash
   # Linux
   sudo smartctl -a /dev/sda

   # macOS
   diskutil verifyVolume /
   ```

5. **Prevent future corruption**:
   ```bash
   # Enable regular backups
   crontab -e
   # Add: 0 2 * * * cp ~/.aurora/memory.db ~/.aurora/backups/memory-$(date +\%Y\%m\%d).db

   # Use more reliable filesystem
   # - ext4 with journaling (Linux)
   # - APFS (macOS)
   # - NTFS (Windows)
   ```

**Data Recovery Tools**:
```bash
# Try sqlite3 recovery tools
sudo apt-get install sqlite3
sqlite3 aurora.db "PRAGMA integrity_check;"
```

**Prevention**:
- Don't forcefully kill AURORA processes (use Ctrl+C)
- Ensure reliable power supply (UPS)
- Use journaled filesystems
- Enable database backups

**Related**: ERR-008, ERR-009

---

## Common Patterns

### Pattern: Database Issues

**Errors**: ERR-008, ERR-009, ERR-010, ERR-011

**Common Workflow**:
```bash
# 1. Check database state
ls -lh aurora.db*
du -sh aurora.db

# 2. Check processes
ps aux | grep aur

# 3. Fix permissions
chmod 700 ~/.aurora/
chmod 600 ~/.aurora/memory.db

# 4. Remove locks if stuck
rm aurora.db-wal aurora.db-shm

# 5. Re-index if corrupted
rm aurora.db
aur mem index
```

---

### Pattern: Network Issues

**Errors**: ERR-002, ERR-003

**Common Workflow**:
```bash
# 1. Check connectivity
ping api.anthropic.com

# 2. Check service status
# Visit: https://status.anthropic.com

# 3. Wait and retry (automatic)
# AURORA retries with exponential backoff

# 4. Use direct mode if urgent
aur query "question" --force-direct
```

---

## Quick Reference

| Error Code | Category | Severity | Auto-Retry |
|------------|----------|----------|------------|
| ERR-002 | API | Medium | Yes (3x) |
| ERR-003 | Network | Medium | Yes (3x) |
| ERR-004 | API | High | No |
| ERR-006 | Config | High | No |
| ERR-007 | Config | Medium | No |
| ERR-008 | Memory | Medium | Yes (5x) |
| ERR-009 | Memory | High | No |
| ERR-010 | Memory | High | No |
| ERR-011 | Memory | High | No |

### Severity Levels

- **High**: Blocks all operations, requires user intervention
- **Medium**: Recoverable with retry or workaround
- **Low**: Warning only, operation continues

### Auto-Retry Behavior

- **API Errors**: 3 attempts with exponential backoff (100ms, 200ms, 400ms)
- **Network Errors**: 3 attempts with exponential backoff
- **Database Locked**: 5 attempts with 100ms delay
- **Configuration**: No retry (user must fix)
- **Permissions**: No retry (user must fix)

---

## Getting More Help

### Check Logs

```bash
# View AURORA logs
tail -f ~/.aurora/aurora.log

# Enable debug logging
aur --debug query "test"
```

### Diagnostic Commands

```bash
# System info
aur --version
python --version
sqlite3 --version

# Configuration status
aur query "test" --dry-run

# Database status
aur mem stats
sqlite3 aurora.db "PRAGMA integrity_check;"
```

### Report Issues

If error persists after trying solutions:

1. **Collect diagnostic info**:
   ```bash
   # System
   uname -a
   python --version

   # AURORA
   aur --version
   aur query "test" --dry-run 2>&1

   # Logs
   tail -n 50 ~/.aurora/aurora.log
   ```

2. **Redact sensitive data**:
   - Remove file paths with usernames
   - Remove any credentials or tokens
   - Remove private code snippets

3. **Open GitHub issue**:
   - Visit: https://github.com/aurora-project/aurora/issues
   - Use error code in title (e.g., "ERR-008: Database Locked on NFS")
   - Include diagnostic info
   - Describe steps to reproduce

---

## Related Documentation

- **CLI Usage Guide**: [CLI_USAGE_GUIDE.md](CLI_USAGE_GUIDE.md)
- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Main README**: [../../README.md](../../README.md)

---

**Document Version**: 1.1.0 (2024-12-24)
**Errors Documented**: 11
**Categories**: API (4), Configuration (3), Memory (4)
