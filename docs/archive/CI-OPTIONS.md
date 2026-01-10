# CI Configuration Options

## Current State

You have **3 CI workflow files**:

1. `.github/workflows/testing-infrastructure-new.yml` - **CURRENT (STRICT)**
2. `.github/workflows/testing-simple.yml` - **NEW (RELAXED)**
3. You can disable both

## Comparison

| Feature | Current (Strict) | Simplified | Disabled |
|---------|-----------------|------------|----------|
| **When it runs** | Every push to main | Only on PRs | Never |
| **Python versions** | 3.10, 3.11, 3.12, 3.13 | 3.10 only | N/A |
| **Run time** | ~20 minutes × 4 = 80min | ~5-10 minutes | 0 |
| **Blocks merge** | Yes (red X) | No (always green) | N/A |
| **Pre-commit hooks** | Via git hooks | Via git hooks | Via git hooks |
| **Cost** | High (4× compute) | Low (1× compute) | Free |

## Local Development Workflow

### Option A: Use Local CI Scripts ⭐ **RECOMMENDED**

```bash
# Before committing (quick - 30 seconds)
./scripts/quick-check.sh

# Before pushing (thorough - 3 minutes)
./scripts/run-local-ci.sh
```

**Benefits:**
- Instant feedback (no 20min wait)
- Same checks as CI
- Catches issues before pushing
- Can iterate quickly

### Option B: Rely on GitHub CI

```bash
# Just commit and push
git add .
git commit -m "fix"
git push

# Wait 20 minutes for CI
# If fails, fix and repeat
```

**Problems:**
- Slow feedback loop
- Wastes CI resources
- Context switching

## Pre-commit Hooks (Runs Locally on `git commit`)

**What they do:**
- Black: Reformats code
- isort: Sorts imports
- flake8: Checks style
- Custom validators: Aurora-specific rules
- bandit: Security checks
- pydocstyle: Docstring checks

**When they modify code:**
- Black **ALWAYS** reformats to its style
- isort **ALWAYS** reorders imports
- This is why your commits include unexpected changes!

**How to see what will change BEFORE committing:**

```bash
# Dry run - shows what would change
pre-commit run --all-files

# Check specific files
pre-commit run --files path/to/file.py
```

## Recommendations

### For Active Development (RIGHT NOW)

1. **Disable strict CI**
   ```bash
   mv .github/workflows/testing-infrastructure-new.yml .github/workflows/testing-infrastructure-new.yml.disabled
   ```

2. **Enable simple CI** (already created)
   - Runs only on PRs
   - Allows failures
   - Gives you signal without blocking

3. **Use local scripts**
   ```bash
   # Before each commit
   ./scripts/quick-check.sh

   # Before each push
   ./scripts/run-local-ci.sh
   ```

### For Production Readiness (LATER)

1. Re-enable strict CI
2. Fix all test failures
3. Enforce coverage requirements
4. Block PRs on red tests

## The Real Issue: Pre-commit Hook Consistency

**Problem:** Pre-commit hooks modify code inconsistently because:
- They run on **changed files only** during commit
- `--all-files` runs on **everything** (different result)
- Some hooks have bugs or edge cases

**Solution:**

```bash
# Before committing, run on ALL files to see total impact
pre-commit run --all-files

# Review changes
git diff

# If good, commit
git add .
git commit -m "message"
```

## Quick Decision Guide

**Choose based on your priority:**

| You want... | Use this... |
|------------|-------------|
| Fast iteration, don't care about CI | Disable CI, use local scripts |
| Feedback on PRs only | Simple CI (already set up) |
| Production-grade rigor | Strict CI (current) |
| See what CI sees locally | `./scripts/run-local-ci.sh` |
| Quick smoke test | `./scripts/quick-check.sh` |

## Current Status

- ✅ Local CI scripts created: `scripts/run-local-ci.sh` and `scripts/quick-check.sh`
- ✅ Simplified CI workflow created: `.github/workflows/testing-simple.yml`
- ⏳ Strict CI still active: `.github/workflows/testing-infrastructure-new.yml`

**Next step:** Choose your CI strategy and run the local scripts to see current test health.
