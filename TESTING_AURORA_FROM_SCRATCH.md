# Testing Aurora CLI From Scratch - New User Guide

**Purpose**: Verify Aurora installation and all CLI features work correctly for a new user.

---

## Prerequisites

- Python 3.10, 3.11, or 3.12
- pip installed
- Anthropic API key (for LLM features)

---

## Step 1: Clean Installation

### 1.1 Create Fresh Virtual Environment

```bash
# Create new directory for testing
mkdir ~/aurora-test
cd ~/aurora-test

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Verify Python version
python --version  # Should be 3.10+
```

### 1.2 Install Aurora

**IMPORTANT**: Choose ONE installation method:

#### Option A: Install from Local Build (Testing Latest Code)

```bash
# Navigate to Aurora source directory
cd /home/hamr/PycharmProjects/aurora

# Build distribution packages
python3 -m pip install --upgrade build
python3 -m build

# Install from local build
pip install dist/aurora_actr-0.2.0-py3-none-any.whl[all]

# Verify installation
aur --version  # Should show 0.2.0
aur --help
```

**Use this when**: Testing latest code changes before publishing to PyPI.

#### Option B: Install from PyPI (Stable Release)

```bash
# Install from PyPI
pip install aurora-actr[all]

# Verify installation
aur --version
aur --help
```

**Use this when**: Testing the public release that end users would install.

**Note**: PyPI may have an older version (last published version). Check current version:
```bash
pip index versions aurora-actr
```

**Expected**: Shows version and help text without errors.

---

## Step 2: Initialize Aurora

### 2.1 First-Time Setup

```bash
# Initialize Aurora (creates ~/.aurora/ directory and config)
aur init

# What happens:
# - Prompts for ANTHROPIC_API_KEY
# - Creates ~/.aurora/memory.db
# - Creates ~/.aurora/config.json
# - Creates ~/.aurora/budget_tracker.json
```

**Test checklist**:
- [ ] Prompts for API key if not in environment
- [ ] Creates `~/.aurora/` directory
- [ ] Creates empty `memory.db` file
- [ ] Creates `config.json` with default settings
- [ ] No errors or crashes

### 2.2 Verify Installation Health

```bash
# Check if all components are working
aur --verify

# Expected output:
# ✓ Database accessible
# ✓ Embeddings provider initialized
# ✓ API key configured
# ✓ Budget tracker initialized
```

**Test checklist**:
- [ ] All checks pass
- [ ] No missing dependencies
- [ ] No permission errors

---

## Step 3: Test Indexing (Feature 1)

### 3.1 Index Sample Code

```bash
# Clone or create a simple Python project for testing
mkdir sample-project
cd sample-project

# Create sample Python files
cat > example.py << 'EOF'
def hello(name):
    """Greet a person by name."""
    return f"Hello, {name}!"

class Calculator:
    """Simple calculator class."""

    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b
EOF

cat > utils.py << 'EOF'
def square(x):
    """Calculate the square of a number."""
    return x * x

def cube(x):
    """Calculate the cube of a number."""
    return x * x * x
EOF

# Index the project
aur mem index .

# Expected output:
# Indexing directory: /path/to/sample-project
# Found 2 files
# Parsing example.py...
# Parsing utils.py...
# Indexed 6 chunks
# ✓ Indexing complete
```

**Test checklist**:
- [ ] Finds all `.py` files
- [ ] Parses files without errors
- [ ] Shows progress/summary
- [ ] Creates chunks in database
- [ ] No crashes or exceptions

### 3.2 Verify Indexed Data

```bash
# Check database statistics
aur mem stats

# Expected output:
# Database: /home/user/.aurora/memory.db
# Total chunks: 6
# Code chunks: 6
# Reasoning chunks: 0
# Knowledge chunks: 0
# Average activation: 0.0 (not accessed yet)
```

**Test checklist**:
- [ ] Shows correct chunk counts
- [ ] Shows database path
- [ ] No SQL errors

---

## Step 4: Test Search (Feature 2)

### 4.1 Simple Search

```bash
# Search for specific function
aur mem search "square function"

# Expected output:
# Found 1 result:
#
# 1. utils.py:square (score: 0.XX)
#    def square(x):
#        """Calculate the square of a number."""
#        return x * x
```

**Test checklist**:
- [ ] Returns relevant results
- [ ] Shows file path and function name
- [ ] Shows code snippet
- [ ] Shows relevance score
- [ ] No errors

### 4.2 Search with Multiple Results

```bash
# Search for broader term
aur mem search "calculator"

# Expected output:
# Found 2 results:
#
# 1. example.py:Calculator (score: 0.XX)
#    class Calculator:
#        """Simple calculator class."""
#
# 2. example.py:Calculator.add (score: 0.XX)
#    def add(self, a, b):
#        """Add two numbers."""
```

**Test checklist**:
- [ ] Returns multiple results
- [ ] Ranked by relevance
- [ ] Results make sense

### 4.3 Search with No Results

```bash
# Search for non-existent term
aur mem search "nonexistent function"

# Expected output:
# No results found for: nonexistent function
```

**Test checklist**:
- [ ] Handles gracefully (no crash)
- [ ] Clear message about no results

---

## Step 5: Test Query (Feature 3 - Simple Mode)

### 5.1 Simple Query (No SOAR)

```bash
# Ask simple question about indexed code
aur query "what does the square function do?"

# Expected behavior:
# - Assesses as SIMPLE
# - Retrieves relevant chunks
# - Returns direct answer (no LLM call)
# - Shows minimal output

# Expected output:
# The square function calculates the square of a number by multiplying it by itself.
#
# Source: utils.py:square
```

**Test checklist**:
- [ ] Answers correctly
- [ ] Fast response (< 2s)
- [ ] Shows source information
- [ ] No API costs (simple path)

---

## Step 6: Test Query (Feature 4 - SOAR Pipeline)

### 6.1 Complex Query (Triggers SOAR)

```bash
# Ask complex question requiring reasoning
aur query "explain how the Calculator class works and compare its add and multiply methods"

# Expected behavior:
# - Assesses as COMPLEX
# - Triggers 9-phase SOAR pipeline
# - Calls LLM for reasoning
# - Shows phase execution
# - Returns comprehensive answer

# Expected output:
# [SOAR Pipeline Execution]
# Phase 1 - Assess: Complexity 0.72 (COMPLEX) → Using SOAR
# Phase 2 - Retrieve: Found 3 chunks (confidence: 0.89)
# Phase 3 - Decompose: 2 subgoals identified
# ...
# Phase 9 - Respond: Answer formatted
#
# The Calculator class is a simple implementation that provides basic
# arithmetic operations. It has two methods:
#
# 1. add(a, b): Returns the sum of two numbers
# 2. multiply(a, b): Returns the product of two numbers
#
# Both methods follow the same pattern: they accept two parameters
# and return the result of the operation directly.
#
# Cost: $0.0123 | Duration: 3.2s
```

**Test checklist**:
- [ ] Detects query as COMPLEX
- [ ] Shows SOAR phases
- [ ] Calls LLM (costs money)
- [ ] Returns comprehensive answer
- [ ] Shows cost and duration
- [ ] No crashes

---

## Step 7: Test Auto-Escalation (Feature 5)

### 7.1 Query That Auto-Escalates

```bash
# Ask medium-complexity question
aur query "list all functions in the codebase" --non-interactive

# Expected behavior:
# - Starts as MEDIUM
# - Simple retrieval returns low confidence
# - Auto-escalates to SOAR
# - Completes successfully

# Expected output:
# [Auto-escalation: LOW confidence → Using SOAR]
#
# The codebase contains the following functions:
# 1. hello(name) - in example.py
# 2. Calculator.add(a, b) - in example.py
# 3. Calculator.multiply(a, b) - in example.py
# 4. square(x) - in utils.py
# 5. cube(x) - in utils.py
```

**Test checklist**:
- [ ] Shows auto-escalation message
- [ ] Falls back to SOAR
- [ ] Returns complete answer
- [ ] `--non-interactive` flag works (no prompts)

---

## Step 8: Test Cost Tracking (Feature 6)

### 8.1 Check Budget

```bash
# View current budget and spending
aur budget

# Expected output:
# Budget Tracker: /home/user/.aurora/budget_tracker.json
#
# Total spent: $0.0234
# Total budget: $10.00
# Remaining: $9.9766
#
# Recent queries:
# - 2025-12-28 14:23:15 | Query: "explain Calculator" | Cost: $0.0123
# - 2025-12-28 14:25:42 | Query: "list all functions" | Cost: $0.0111
```

**Test checklist**:
- [ ] Shows total spent
- [ ] Shows remaining budget
- [ ] Lists recent queries with costs
- [ ] No errors reading budget file

### 8.2 Test Budget Limit

```bash
# Set very low budget for testing
echo '{"total_budget": 0.001, "spent": 0.0}' > ~/.aurora/budget_tracker.json

# Try expensive query
aur query "analyze the entire codebase architecture in detail"

# Expected output:
# ERROR: Budget exceeded
# Estimated cost: $0.05
# Remaining budget: $0.001
#
# Please increase your budget in ~/.aurora/budget_tracker.json
```

**Test checklist**:
- [ ] Detects budget exceeded
- [ ] Shows clear error message
- [ ] Does NOT charge API (stops before call)
- [ ] Suggests how to fix

---

## Step 9: Test Error Handling

### 9.1 Invalid API Key

```bash
# Temporarily use invalid key
export ANTHROPIC_API_KEY="invalid-key"

# Try query requiring LLM
aur query "explain everything"

# Expected output:
# ERROR: Invalid API key
# Please check your ANTHROPIC_API_KEY environment variable
# or run: aur init
```

**Test checklist**:
- [ ] Detects invalid key
- [ ] Shows clear error message
- [ ] Suggests fix
- [ ] No crashes

### 9.2 Database Corruption

```bash
# Remove database
rm ~/.aurora/memory.db

# Try search
aur mem search "test"

# Expected output:
# ERROR: Database not found
# Please run: aur init
# Then index your codebase: aur mem index /path/to/code
```

**Test checklist**:
- [ ] Detects missing database
- [ ] Shows clear error message
- [ ] Suggests recovery steps

### 9.3 Invalid Path

```bash
# Try indexing non-existent path
aur mem index /nonexistent/path

# Expected output:
# ERROR: Path not found: /nonexistent/path
# Please provide a valid directory path
```

**Test checklist**:
- [ ] Detects invalid path
- [ ] Shows clear error
- [ ] No crash

---

## Step 10: Test All CLI Commands

### 10.1 Help Commands

```bash
# Main help
aur --help

# Command-specific help
aur mem --help
aur query --help
aur budget --help
```

**Test checklist**:
- [ ] All help text displays correctly
- [ ] Shows available commands
- [ ] Shows options and flags

### 10.2 Mem Subcommands

```bash
# Already tested:
# aur mem index <path>
# aur mem search <query>
# aur mem stats

# Test clearing memory (WARNING: destructive)
aur mem clear

# Expected: Prompts for confirmation, then clears database
```

**Test checklist**:
- [ ] All subcommands work
- [ ] No missing commands

---

## Test Summary Checklist

**Installation**:
- [ ] `pip install aurora-actr[all]` succeeds
- [ ] `aur --version` shows version
- [ ] `aur --help` shows help text

**Initialization**:
- [ ] `aur init` creates config files
- [ ] `aur --verify` passes all checks

**Indexing**:
- [ ] `aur mem index .` indexes files
- [ ] `aur mem stats` shows correct counts

**Search**:
- [ ] `aur mem search` returns results
- [ ] Results are relevant
- [ ] Handles no results gracefully

**Query - Simple**:
- [ ] Simple queries work (no SOAR)
- [ ] Fast response (< 2s)
- [ ] No API costs

**Query - Complex**:
- [ ] Complex queries trigger SOAR
- [ ] Shows 9 phases
- [ ] Returns comprehensive answer
- [ ] Tracks costs

**Auto-Escalation**:
- [ ] Low confidence triggers escalation
- [ ] `--non-interactive` flag works

**Budget Tracking**:
- [ ] `aur budget` shows spending
- [ ] Budget limits enforced

**Error Handling**:
- [ ] Invalid API key caught
- [ ] Missing database caught
- [ ] Invalid paths caught
- [ ] All errors show helpful messages

**No Crashes**:
- [ ] All features work without crashes
- [ ] No Python exceptions shown to user
- [ ] Graceful degradation on errors

---

## Expected Timeline

- **Installation**: 2 minutes
- **Initialization**: 1 minute
- **Indexing test**: 2 minutes
- **Search tests**: 3 minutes
- **Query tests (simple)**: 2 minutes
- **Query tests (complex/SOAR)**: 5 minutes
- **Auto-escalation test**: 3 minutes
- **Budget tests**: 2 minutes
- **Error handling tests**: 5 minutes
- **All commands review**: 5 minutes

**Total**: ~30 minutes for complete testing

---

## Success Criteria

All checklist items pass with:
- ✅ No crashes or exceptions
- ✅ Clear error messages when things fail
- ✅ Fast response times (simple < 2s, complex < 10s)
- ✅ Accurate results from search/query
- ✅ Cost tracking working correctly
- ✅ Help text is clear and accurate

---

## Common Issues & Fixes

**Issue**: `aur: command not found`
- **Fix**: Virtual environment not activated, or pip install failed
- **Check**: `which aur`, `pip list | grep aurora`

**Issue**: `ModuleNotFoundError: No module named 'aurora_core'`
- **Fix**: Namespace packages not installed correctly
- **Check**: `pip install --force-reinstall aurora-actr[all]`

**Issue**: All activation scores are 0.0
- **Fix**: Known bug (PRIORITY 0 fix in progress)
- **Workaround**: Search still works, just with suboptimal ranking

**Issue**: Budget tracker not found
- **Fix**: Run `aur init` to create config files
- **Check**: `ls ~/.aurora/`

**Issue**: API key errors
- **Fix**: Set environment variable: `export ANTHROPIC_API_KEY=sk-ant-...`
- **Or**: Run `aur init` and enter key when prompted
