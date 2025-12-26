# Pre-Push CI/CD Validation Guide

## Overview

This guide explains how to validate your code locally before pushing to ensure GitHub Actions CI/CD will pass. Running these checks locally saves time and prevents failed CI/CD runs.

## Quick Start

```bash
# Quick validation (~30 seconds) - linting, formatting, type-checking
./scripts/pre-push-checks.sh --quick

# Full validation (~2-3 minutes) - includes all tests
./scripts/pre-push-checks.sh
```

## The Problem

After task 0008 (LLM mockups removal), we encountered CI/CD failures that could have been prevented:

- **9 files** needed reformatting (`ruff format` not run)
- **67 test failures** on Python 3.10 (missing config section)
- **102 test failures** on Python 3.11/3.12 (appeared worse than reality)

These issues passed local development but failed in CI because:
1. No local pre-push validation script existed
2. Developer didn't run the same checks as CI before pushing
3. Refactoring exposed hidden dependencies not caught by existing tests

## The Solution: Pre-Push Validation Script

The `scripts/pre-push-checks.sh` script mirrors the GitHub Actions workflow exactly.

### What It Checks

The script runs 5 checks in sequence (matches CI/CD pipeline):

1. **Code Formatting** (`ruff format --check .`)
   - Ensures consistent code style
   - Fast (~2 seconds)

2. **Linting** (`ruff check .`)
   - Catches code quality issues
   - Fast (~3 seconds)

3. **Type Checking** (`make type-check`)
   - MyPy strict mode validation
   - Medium (~15 seconds)

4. **Unit Tests** (`pytest tests/unit/ -m "not ml"`)
   - Fast tests for core functionality
   - Medium (~30 seconds)
   - **Skipped in --quick mode**

5. **Integration Tests** (`pytest tests/integration/ -m "not ml"`)
   - Tests for component integration
   - Slower (~60 seconds)
   - **Skipped in --quick mode**

### Usage

#### Quick Mode (Recommended for frequent commits)

```bash
./scripts/pre-push-checks.sh --quick
```

Use this:
- Before each commit
- During active development
- When you need fast feedback

Checks: formatting, linting, type-checking only (~30 seconds)

#### Full Mode (Recommended before pushing)

```bash
./scripts/pre-push-checks.sh
```

Use this:
- Before pushing to remote
- After completing a feature
- Before creating a PR

Checks: all 5 validations (~2-3 minutes)

### Example Output

```
=========================================
AURORA Pre-Push CI/CD Validation
=========================================

[1/5] Checking code formatting...
✓ Code formatting passed

[2/5] Running linter...
✓ Linting passed

[3/5] Running type checker...
✓ Type checking passed

[4/5] Running unit tests...
✓ Unit tests passed

[5/5] Running integration tests...
✓ Integration tests passed

=========================================
✓ ALL CHECKS PASSED!
=========================================

Your code is ready to push.
```

### Handling Failures

If a check fails, the script exits immediately with a helpful error message:

```bash
✗ Code formatting failed. Run: ruff format .
```

Fix the issue and re-run the script.

## Automated Validation (Optional)

### Git Pre-Push Hook

Add automatic validation before every push:

```bash
# Create symbolic link to hook
ln -sf ../../scripts/pre-push-checks.sh .git/hooks/pre-push

# Now validation runs automatically on 'git push'
```

**Warning**: This will block pushes if validation fails. You can bypass with:

```bash
git push --no-verify  # Skip pre-push hook (use sparingly!)
```

### Git Pre-Commit Hook (More Aggressive)

For maximum safety, validate before each commit:

```bash
# Create pre-commit hook for quick checks only
cat > .git/hooks/pre-commit << 'EOF'
#!/usr/bin/env bash
./scripts/pre-push-checks.sh --quick
EOF

chmod +x .git/hooks/pre-commit
```

## Recommended Workflow

### Standard Development Cycle

```bash
# 1. Make changes
vim src/aurora/mcp/tools.py

# 2. Quick check before commit
./scripts/pre-push-checks.sh --quick

# 3. Fix any issues
ruff format .
ruff check . --fix

# 4. Commit
git add .
git commit -m "feat: add new feature"

# 5. Full check before push
./scripts/pre-push-checks.sh

# 6. Push with confidence
git push
```

### Emergency Fixes (Time-Sensitive)

```bash
# 1. Make hotfix
vim src/aurora/mcp/tools.py

# 2. Run quick check only
./scripts/pre-push-checks.sh --quick

# 3. Push (CI will run full tests)
git push
```

## Why This Matters

### Time Savings

| Scenario | Without Script | With Script |
|----------|---------------|-------------|
| Failed CI run | 10-15 min | 2-3 min (caught locally) |
| Debugging CI failure | 30-60 min | 5-10 min (reproduce locally) |
| Total iteration time | 40-75 min | 7-13 min |

**Savings**: ~30-60 minutes per failed CI run

### Quality Improvements

1. **Catch issues earlier** - Before they reach CI
2. **Faster iteration** - Immediate feedback vs waiting for CI
3. **Better debugging** - Local environment easier to debug than CI
4. **Consistent standards** - Same checks as CI, guaranteed

### Team Benefits

- **Reviewers**: Fewer "fix formatting" comments
- **Contributors**: Confidence that PRs will pass CI
- **Maintainers**: Less time fixing broken CI builds

## Common Issues

### Issue: "Permission denied" when running script

**Solution**:
```bash
chmod +x scripts/pre-push-checks.sh
```

### Issue: Script passes but CI fails

**Possible causes**:
1. Different Python version (CI uses 3.10, 3.11, 3.12)
2. Missing dependencies (check `pyproject.toml`)
3. Environment-specific issue (check CI logs)

**Solution**:
```bash
# Test with specific Python version
python3.10 -m pytest tests/unit/
python3.11 -m pytest tests/unit/
python3.12 -m pytest tests/unit/
```

### Issue: Tests pass locally but fail in CI

**Common causes**:
1. **Import paths**: CI uses package names (`aurora_core`), not relative imports
2. **Dependencies**: CI installs from `pyproject.toml`, not local editable installs
3. **File paths**: CI runs from repo root, tests may assume different CWD

**Debugging**:
```bash
# Replicate CI environment
pip uninstall aurora-actr -y
pip install -e ".[dev,test]"
pytest tests/
```

## Advanced Usage

### Running Specific Checks

```bash
# Just formatting
ruff format --check .

# Just linting
ruff check .

# Just type checking
make type-check

# Just unit tests
pytest tests/unit/ -m "not ml" -v

# Just integration tests
pytest tests/integration/ -m "not ml" -v
```

### Testing Multiple Python Versions

```bash
# Python 3.10
python3.10 -m pytest tests/

# Python 3.11
python3.11 -m pytest tests/

# Python 3.12
python3.12 -m pytest tests/
```

### Parallel Testing (Faster)

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/ -n 4
```

## Case Study: Task 0008 Post-Mortem

### What Happened

After removing LLM mockups (task 0008), CI failed with:
- 9 formatting errors
- 67 Python 3.10 test failures
- 102 Python 3.11/3.12 test failures

### Root Cause

1. **Missing config section**: `_load_config()` in `tools.py` was missing `"memory"` defaults
2. **Formatting not run**: Developer didn't run `ruff format` before committing
3. **No local validation**: No script to catch these issues before pushing

### Resolution

1. Added missing `"memory": {"default_limit": 10}` to config defaults
2. Ran `ruff format .` to fix formatting
3. Created `scripts/pre-push-checks.sh` to prevent recurrence

### Lessons Learned

1. **Always validate locally** before pushing
2. **Refactoring is risky** - search for related code (e.g., grep for config usage)
3. **Formatting should be automated** - add to pre-commit hook
4. **Test coverage gaps** - config defaults should have dedicated tests

### Prevention

If `scripts/pre-push-checks.sh` had existed and been run, this would have been caught in ~30 seconds locally instead of failing CI.

## Contributing

When modifying the validation script:

1. Keep it fast (target: <3 minutes for full run)
2. Match GitHub Actions workflow exactly
3. Provide clear error messages with fix suggestions
4. Test on all supported Python versions

## Related Documentation

- [Testing Guide](./TESTING.md) - Comprehensive testing documentation
- [Development Setup](./DEVELOPMENT_SETUP.md) - Environment configuration
- [GitHub Actions Workflow](../../.github/workflows/) - CI/CD configuration
- [Quality Standards](./QUALITY_STANDARDS.md) - Code quality requirements

## Support

If you encounter issues:

1. Check this guide for common issues
2. Review GitHub Actions logs for CI failures
3. Run script with `bash -x` for debugging:
   ```bash
   bash -x scripts/pre-push-checks.sh --quick
   ```
4. Ask in team chat or open an issue

## Summary

**Key Takeaways**:
- ✅ Run `./scripts/pre-push-checks.sh --quick` before commits
- ✅ Run `./scripts/pre-push-checks.sh` before pushes
- ✅ Consider adding as git pre-push hook for automation
- ✅ Saves 30-60 minutes per prevented CI failure
- ✅ Matches GitHub Actions workflow exactly
