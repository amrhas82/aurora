# AURORA CLI - Complete Testing Guide

**Purpose**: Test every CLI command and option to identify what works without API keys

---

## Installation Check

### Test: Verify CLI is installed
```bash
# Should show version and help
aur --version
aur --help

# Expected: Shows 0.1.0 and command list
# Tests: Basic CLI availability
```

---

## Command 1: `aur init` - Configuration Setup

### Test 1.1: First-time initialization
```bash
# Remove existing config
rm -rf ~/.aurora

# Run init
aur init

# Prompts:
# - Enter API key (press Enter to skip)
# - Index current directory? (Y/n)

# Expected behavior:
# ✓ Creates ~/.aurora/config.json
# ✓ Sets file permissions to 0600 (user read/write only)
# ✓ If you skip API key, shows "API key: Not configured"
# ✓ If you choose to index, attempts to index current directory
# ⚠ KNOWN ISSUE: Indexing is currently broken

# What to test:
# - Does config file get created?
# - Are permissions correct? (ls -la ~/.aurora/config.json)
# - Does it handle "skip API key" gracefully?
# - What happens when you choose to index?
```

### Test 1.2: Re-initialization (config exists)
```bash
# Run init again
aur init

# Expected:
# - Asks "Config file already exists. Overwrite? [y/N]"
# - If N: Keeps existing config
# - If Y: Overwrites and prompts again
```

### Test 1.3: Config file contents
```bash
# Check what was created
cat ~/.aurora/config.json | python3 -m json.tool

# Expected structure:
{
  "llm": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "anthropic_api_key": null,  # or your key if provided
    "temperature": 0.7,
    "max_tokens": 4000
  },
  "memory": {
    "db_path": "~/.aurora/memory.db",
    "context_window": 10
  },
  "soar": {
    "max_iterations": 5,
    "enable_verification": true
  }
}
```

**Record**: Does this work? Any errors?

---

## Command 2: `aur mem` - Memory Management (NO API NEEDED)

These commands work WITHOUT an API key - they're local database operations.

### Test 2.1: Index current directory
```bash
# Go to a directory with Python files
cd /home/hamr/PycharmProjects/aurora

# Index the packages directory
aur mem index packages/

# Expected:
# ✓ Shows progress bar
# ✓ Reports "Indexed X files, Y chunks in Z.XXs"
# ✓ Creates aurora.db in current directory
# ⚠ KNOWN ISSUE: Currently broken (add_chunk error)

# What to check:
# - Does it find Python files?
# - Does progress bar appear?
# - Does aurora.db get created?
# - Any error messages?
```

### Test 2.2: Index with specific path
```bash
# Index a specific package
aur mem index packages/core/src/aurora_core/

# Try with .py file pattern
aur mem index packages/ --pattern "*.py"

# Expected:
# - Indexes only matching files
# - Shows count of files processed
```

### Test 2.3: Search memory (requires indexed data)
```bash
# After indexing, search for something
aur mem search "SQLiteStore"
aur mem search "activation"
aur mem search "chunk"

# Expected:
# ✓ Shows ranked results
# ✓ Displays file path, function name, relevance score
# ✓ Limits to top 10 by default
# ⚠ DEPENDS ON: Indexing working first

# Test variations:
aur mem search "error handling" --limit 5
aur mem search "config" --limit 20
```

### Test 2.4: Memory statistics
```bash
# Get stats about indexed memory
aur mem stats

# Expected output:
# - Total chunks: XXX
# - Total files: XXX
# - Database size: X.XX MB
# - Average chunks per file: X.X

# What to check:
# - Does it show stats without errors?
# - Are numbers reasonable?
```

**Record**: Which memory commands work? Which fail?

---

## Command 3: `aur query` - Query Execution (REQUIRES API)

These commands NEED an API key, but we can test their error handling.

### Test 3.1: Query without API key
```bash
# Make sure API key is not set
unset ANTHROPIC_API_KEY

# Try a simple query
aur query "What is a function?"

# Expected:
# ✗ Error message: "ANTHROPIC_API_KEY environment variable not set"
# - Should show helpful message
# - Should suggest: export ANTHROPIC_API_KEY=sk-ant-...
# - Should show URL: https://console.anthropic.com

# Test: Is error message clear and helpful?
```

### Test 3.2: Dry-run mode (no API needed)
```bash
# Dry run shows what WOULD happen without making API calls
aur query "How do I implement authentication?" --dry-run

# Expected:
# ✓ Shows "DRY RUN MODE - No API calls will be made"
# ✓ Shows configuration (model, provider, API key status)
# ✓ Shows memory store status (chunks indexed)
# ✓ Shows escalation decision (would use AURORA or Direct LLM)
# ✓ Shows estimated cost
# ✓ NO actual API call made

# What to verify:
# - Does it run without API key?
# - Does it show escalation reasoning?
# - Does it detect indexed memory?
# - Are cost estimates shown?
```

### Test 3.3: Dry-run with different options
```bash
# Test escalation decisions
aur query "What is 2+2?" --dry-run
# Expected: Decides "Direct LLM" (simple query)

aur query "Refactor the authentication system to use OAuth2" --dry-run
# Expected: Decides "AURORA" (complex query)

# Test force modes
aur query "simple question" --dry-run --force-aurora
# Expected: Shows "Would use: AURORA" (forced)

aur query "complex task" --dry-run --force-direct
# Expected: Shows "Would use: Direct LLM" (forced)

# Test reasoning display
aur query "design microservices" --dry-run --show-reasoning
# Expected: Shows complexity score, confidence, reasoning
```

### Test 3.4: Query with API key (if you have one)
```bash
# Set API key (skip if you don't have one)
export ANTHROPIC_API_KEY=sk-ant-...

# Simple query
aur query "What is 2+2?"

# Expected:
# → Using Direct LLM (fast mode)
# Response: [LLM answer]

# Complex query
aur query "Explain how the AURORA SOAR pipeline works"

# Expected:
# → Using AURORA (full pipeline)
# [If memory indexed: uses memory context]
# [If --verbose: shows phase trace]

# With verbose
aur query "How does activation spreading work?" --verbose

# Expected:
# - Shows phase-by-phase execution
# - Shows SOAR Phase Trace table
# - Shows duration, cost, confidence
```

**Record**: Do API-requiring commands fail gracefully without API? Does dry-run work?

---

## Command 4: `aur --headless` - Headless Mode (REQUIRES API)

### Test 4.1: Headless without API
```bash
# Create a test prompt file
cat > test_prompt.md << 'EOF'
# Test Prompt

Please explain what headless mode does.
EOF

# Try without API
unset ANTHROPIC_API_KEY
aur --headless test_prompt.md

# Expected:
# ✗ Error about missing API key
# Should fail gracefully
```

### Test 4.2: Headless with invalid file
```bash
# Try non-existent file
aur --headless nonexistent.md

# Expected:
# ✗ Error: File not found
# Should have clear error message
```

### Test 4.3: Headless with API (if available)
```bash
# With API key set
export ANTHROPIC_API_KEY=sk-ant-...

# Run headless mode
aur --headless test_prompt.md

# Expected:
# - Loads prompt from file
# - Executes SOAR pipeline
# - Saves results to scratchpad
# - Shows summary
```

**Record**: Does headless fail gracefully? Is error handling good?

---

## Global Options Testing

### Test: Verbose and Debug flags
```bash
# Test verbose output
aur --verbose mem stats
aur -v mem stats

# Expected:
# - Shows INFO level logs
# - More detailed output

# Test debug output
aur --debug mem stats

# Expected:
# - Shows DEBUG level logs
# - Very detailed output

# Test on multiple commands
aur --verbose query "test" --dry-run
aur --debug init
```

### Test: Version display
```bash
aur --version

# Expected: "aurora, version 0.1.0"
```

### Test: Help for each command
```bash
aur --help
aur init --help
aur mem --help
aur mem index --help
aur mem search --help
aur mem stats --help
aur query --help
aur --headless --help
```

**Record**: Is help clear? Are all options documented?

---

## Edge Cases and Error Handling

### Test: Bad inputs
```bash
# Invalid options
aur --invalid-option
aur query
aur mem index
aur mem search

# Expected: Clear error messages

# Invalid threshold
aur query "test" --threshold 2.0  # Should be 0.0-1.0
aur query "test" --threshold -1.0

# Both force flags
aur query "test" --force-aurora --force-direct --dry-run

# Invalid paths
aur mem index /nonexistent/path
```

### Test: Permissions
```bash
# Try to create config without permissions
chmod 000 ~/.aurora
aur init
# Expected: Permission error with clear message

# Fix permissions
chmod 755 ~/.aurora
```

### Test: Corrupted database
```bash
# Create invalid database
echo "garbage" > aurora.db

# Try to use it
aur mem stats
aur mem search "test"

# Expected: Error message, suggestion to reset
```

**Record**: Are error messages helpful? Do they suggest solutions?

---

## Summary Checklist

### Commands That Should Work WITHOUT API:
- [ ] `aur --version` - Show version
- [ ] `aur --help` - Show help
- [ ] `aur init` - Create config (skip API key)
- [ ] `aur mem index <path>` - Index Python files ⚠ BROKEN
- [ ] `aur mem search <query>` - Search indexed code ⚠ DEPENDS ON INDEX
- [ ] `aur mem stats` - Show memory stats ⚠ DEPENDS ON INDEX
- [ ] `aur query <query> --dry-run` - Show what would execute

### Commands That REQUIRE API Key:
- [ ] `aur query <query>` - Execute query
- [ ] `aur query <query> --force-aurora` - Force AURORA mode
- [ ] `aur query <query> --force-direct` - Force direct LLM
- [ ] `aur query <query> --verbose` - Show phase trace
- [ ] `aur --headless <file>` - Execute headless mode

### What to Document for Each Test:
1. ✓ Works perfectly
2. ⚠ Works with issues (describe)
3. ✗ Completely broken (error message)
4. ? Untested (need API / setup)

---

## Test Environment Setup

```bash
# Clean slate
rm -rf ~/.aurora
rm -f aurora.db

# Verify AURORA is accessible
which aur
aur --version

# For testing without API
unset ANTHROPIC_API_KEY

# For testing with API (if you have one)
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

## Next Steps After Testing

1. Fill in results for each test above
2. Document every error message you see
3. Note which commands you couldn't test (need API)
4. Share findings so we can create a fix PRD
