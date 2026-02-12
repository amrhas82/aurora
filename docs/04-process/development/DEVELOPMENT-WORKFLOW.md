# Aurora Development Workflow

## Your Daily Workflow (Direct-to-Main)

### 1. Before You Start Coding

```bash
# Make sure you're on latest main
git pull origin main

# Optional: Run quick health check to see baseline
./scripts/quick-check.sh
```

### 2. While Coding

**Just code normally!** No special steps needed.

### 3. Before Committing

```bash
# Option A: Quick check (30 seconds - recommended)
./scripts/quick-check.sh

# Option B: Full check (3-5 minutes - before important commits)
./scripts/run-local-ci.sh
```

**What these do:**
- `quick-check.sh` - Runs tests only (fast feedback)
- `run-local-ci.sh` - Runs tests + pre-commit hooks (exactly what CI does)

### 4. Committing Your Changes

```bash
# Stage your changes
git add .

# Commit (pre-commit hooks will run automatically)
git commit -m "your message"

# If hooks modify files, review and re-commit:
git add .
git commit --amend --no-edit
```

**What happens during commit:**
- Pre-commit hooks run automatically
- They may **modify your files** (formatting, import sorting)
- If files are modified, you'll need to `git add` and commit again

### 5. Pushing to Main

```bash
# Push to main
git push origin main

# CI will run automatically (~5-10 minutes)
# Check status: https://github.com/hamr0/aurora/actions
```

### 6. If CI Fails

```bash
# Option 1: Run local CI to debug
./scripts/run-local-ci.sh

# Option 2: Check CI logs on GitHub
gh run view --log-failed

# Fix issues, then commit and push again
```

---

## Understanding Your CI Setup

### What CI Does (GitHub Actions)

```yaml
Trigger: Every push to main
Runtime: ~5-10 minutes
Python: 3.10 only
Tests: pytest -m "not ml and not real_api" --cov=packages -v
```

**Key Points:**
- ✅ Runs on Python 3.10 (matches your local environment)
- ✅ Excludes ML tests (too slow/heavy for CI)
- ✅ Excludes real_api tests (need external services)
- ✅ Generates coverage report
- ⚠️  Tests must pass for green checkmark

### What Pre-commit Hooks Do (Local)

```yaml
Trigger: Every git commit
Runtime: ~10-30 seconds
Tools:
  - Black: Reformats code
  - isort: Sorts imports
  - flake8: Checks style
  - Custom validators: Aurora-specific rules
  - bandit: Security checks
  - pydocstyle: Docstring checks
```

**Key Points:**
- ⚠️  **Modifies your files automatically**
- ✅ Catches style issues before CI
- ✅ Enforces consistent formatting
- ⚠️  May fail if issues can't be auto-fixed

---

## Common Scenarios

### Scenario 1: "Pre-commit hooks modified my files"

**This is normal!** Black and isort reformat code.

```bash
# Review what changed
git diff

# If changes look good, add and commit
git add .
git commit --amend --no-edit

# Push
git push
```

### Scenario 2: "Tests pass locally but fail in CI"

**Possible causes:**
1. Pre-commit hooks modified code differently
2. Environment differences (packages, Python version)
3. Timing/race conditions in tests

**Solution:**
```bash
# Run local CI (exactly matches GitHub CI)
./scripts/run-local-ci.sh

# This runs pre-commit hooks + tests
# Should reveal the issue
```

### Scenario 3: "Pre-commit hooks are failing"

**Common issues:**
- flake8: Style violations (unused imports, long lines)
- bandit: Security issues (pickle usage, etc.)
- pydocstyle: Missing/incorrect docstrings

**Solution:**
```bash
# See what's failing
pre-commit run --all-files

# Fix issues manually, or skip hooks temporarily:
git commit --no-verify -m "message"

# Note: Skipping hooks means CI might fail!
```

### Scenario 4: "I want to skip CI for a minor change"

**You can't skip CI**, but you can:
1. Use `[skip ci]` in commit message (doesn't work with our config)
2. Push to a branch instead of main (no CI trigger)
3. Accept that CI will run and possibly fail

**Recommendation:** If it's truly minor (docs, comments), just let CI run.

### Scenario 5: "CI is taking too long / I need fast iteration"

**Options:**
1. Use local scripts instead: `./scripts/quick-check.sh`
2. Commit multiple times locally, push once
3. Work on a branch, push to main when stable

---

## Project Structure

```
aurora/
├── .github/
│   └── workflows/
│       └── testing-infrastructure-new.yml  # CI config (Python 3.10, ~5-10min)
├── scripts/
│   ├── run-local-ci.sh        # Full CI equivalent (local)
│   └── quick-check.sh         # Fast test runner
├── docs/
│   ├── CI-OPTIONS.md          # CI configuration explained
│   └── DEVELOPMENT-WORKFLOW.md # This file
├── tests/
│   ├── unit/                  # Fast, isolated tests
│   ├── integration/           # Multi-component tests
│   └── e2e/                   # End-to-end workflows
└── .pre-commit-config.yaml    # Pre-commit hooks config
```

---

## Quick Command Reference

```bash
# Run tests (fast)
./scripts/quick-check.sh

# Run full CI locally (slow but thorough)
./scripts/run-local-ci.sh

# Run tests manually
pytest -m "not ml and not real_api" -v

# Run specific test file
pytest tests/unit/path/to/test_file.py -v

# Run pre-commit hooks manually
pre-commit run --all-files

# Check CI status
gh run list --limit 5
gh run view --log-failed

# Skip pre-commit hooks (not recommended)
git commit --no-verify -m "message"
```

---

## Troubleshooting

### "I don't understand why tests are failing"

1. **Check if tests pass locally:**
   ```bash
   ./scripts/run-local-ci.sh
   ```

2. **Check CI logs:**
   ```bash
   gh run view --log-failed
   ```

3. **Compare local vs CI:**
   - Local: Your environment
   - CI: Fresh Ubuntu, Python 3.10, clean install

### "Pre-commit hooks are frustrating"

Pre-commit hooks are **helping you**:
- Catch issues before CI (saves time)
- Enforce consistent style (easier to review)
- Prevent security issues (bandit)

**If truly stuck:**
```bash
# Disable pre-commit hooks temporarily
pre-commit uninstall

# Re-enable later
pre-commit install
```

### "CI keeps failing on random things"

This is the "rabbit hole" problem. Common causes:
1. **MCP tests** - Skipped (dormant functionality)
2. **Style issues** - Pre-commit hooks fix these
3. **Real failures** - Need investigation

**Strategy:**
1. Fix real failures first (product bugs)
2. Ignore style issues temporarily (commit with --no-verify)
3. Clean up style in a separate commit

---

## Philosophy

### Why This Workflow?

**Goals:**
- ✅ Fast local iteration (don't wait for CI)
- ✅ Catch issues early (pre-commit hooks)
- ✅ Reliable CI signal (Python 3.10, essential tests)
- ✅ Minimal overhead (no multi-version matrix)

**Trade-offs:**
- ❌ Not testing Python 3.11-3.13 (acceptable for now)
- ❌ Not catching cross-platform issues (Linux only)
- ✅ Fast feedback loop (5-10min vs 80min)

### When to Tighten CI

**Later, when ready for production:**
1. Add back Python version matrix (3.10-3.13)
2. Enable stricter coverage requirements
3. Add deployment checks
4. Run on multiple OSes (Linux, macOS, Windows)

**For now:** Keep it simple, focus on product development.

---

## Getting Help

- **CI fails:** Check `gh run view --log-failed`
- **Local tests fail:** Run `./scripts/run-local-ci.sh`
- **Pre-commit issues:** Run `pre-commit run --all-files`
- **General confusion:** Read this file again!

---

## Summary

**Your workflow in 4 steps:**

1. **Code** - Write your changes
2. **Check** - `./scripts/quick-check.sh` (optional but recommended)
3. **Commit** - `git commit -m "message"` (hooks run automatically)
4. **Push** - `git push` (CI runs automatically)

**That's it!** The tools handle the rest.
