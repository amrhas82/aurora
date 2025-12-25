# AURORA Publishing Guide

This guide covers the process of building and publishing AURORA packages to PyPI (Python Package Index).

## Table of Contents

- [Prerequisites](#prerequisites)
- [Build Configuration](#build-configuration)
- [Building Packages](#building-packages)
- [Testing on TestPyPI](#testing-on-testpypi)
- [Publishing to Production PyPI](#publishing-to-production-pypi)
- [Version Management](#version-management)
- [Automated Publishing](#automated-publishing)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. PyPI Account

Create accounts on both TestPyPI (for testing) and production PyPI:

- **TestPyPI** (testing): https://test.pypi.org/account/register/
- **Production PyPI**: https://pypi.org/account/register/

### 2. API Tokens

After creating accounts, generate API tokens (recommended over passwords):

1. Log in to PyPI/TestPyPI
2. Go to Account Settings → API Tokens
3. Click "Add API Token"
4. Set scope to "Entire account" or specific project
5. Copy the token (starts with `pypi-`)

**Important**: Save tokens securely - they are only shown once!

### 3. Configure `.pypirc`

Create `~/.pypirc` in your home directory (NOT in the repository):

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

**Security**: The `.pypirc` file is already in `.gitignore` to prevent accidental commits.

### 4. Install Build Tools

```bash
pip install --upgrade build twine
```

---

## Build Configuration

AURORA uses modern Python packaging standards with `pyproject.toml`:

### Key Configuration Files

1. **`pyproject.toml`**: Project metadata, dependencies, build system
2. **`setup.py`**: Meta-package setup with post-install hooks
3. **`README.md`**: Long description for PyPI page
4. **`CHANGELOG.md`**: Version history (linked from PyPI)

### Verify Configuration

Before building, ensure:

- ✅ Version number is correct in `pyproject.toml` (e.g., `version = "0.2.0"`)
- ✅ Dependencies are up-to-date in `dependencies` list
- ✅ `README.md` is complete and formatted
- ✅ `CHANGELOG.md` has entry for current version
- ✅ All URLs in `[project.urls]` are correct

---

## Building Packages

### 1. Clean Previous Builds

```bash
rm -rf dist/ build/ src/*.egg-info
```

### 2. Build Distribution Packages

```bash
python3 -m build --no-isolation
```

This creates:
- `dist/aurora-X.Y.Z.tar.gz` - Source distribution (sdist)
- `dist/aurora-X.Y.Z-py3-none-any.whl` - Wheel distribution (bdist_wheel)

### 3. Inspect Package Contents

```bash
# View tarball contents
tar -tzf dist/aurora-0.2.0.tar.gz

# View wheel contents
unzip -l dist/aurora-0.2.0-py3-none-any.whl

# Check package metadata
twine check dist/*
```

**Expected output**: `Checking dist/aurora-X.Y.Z.tar.gz: PASSED`

---

## Testing on TestPyPI

**Always test on TestPyPI before publishing to production PyPI!**

### 1. Upload to TestPyPI

```bash
twine upload --repository testpypi dist/*
```

You'll see output like:
```
Uploading distributions to https://test.pypi.org/legacy/
Uploading aurora-0.2.0-py3-none-any.whl
Uploading aurora-0.2.0.tar.gz
View at: https://test.pypi.org/project/aurora/0.2.0/
```

### 2. Test Installation

Create a fresh virtual environment:

```bash
python3 -m venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple aurora
```

**Note**: `--extra-index-url https://pypi.org/simple` is needed because AURORA's dependencies (e.g., `sentence-transformers`) are on production PyPI, not TestPyPI.

### 3. Verify Installation

```bash
# Check version
pip show aurora

# Run verification command
aur --verify

# Test basic functionality
aur --help
aur init
aur mem index .
```

### 4. Clean Up Test Environment

```bash
deactivate
rm -rf test-env
```

---

## Publishing to Production PyPI

**Only proceed after successful TestPyPI testing!**

### 1. Final Pre-Publish Checklist

- ✅ All tests pass (`pytest tests/`)
- ✅ Version bumped correctly in `pyproject.toml`
- ✅ `CHANGELOG.md` updated with release notes
- ✅ `README.md` is complete and accurate
- ✅ TestPyPI installation verified successfully
- ✅ Git tag created for version (e.g., `git tag v0.2.0`)

### 2. Upload to Production PyPI

```bash
twine upload dist/*
```

You'll see output like:
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading aurora-0.2.0-py3-none-any.whl
Uploading aurora-0.2.0.tar.gz
View at: https://pypi.org/project/aurora/0.2.0/
```

### 3. Verify on PyPI

Visit: https://pypi.org/project/aurora/

Check:
- ✅ README renders correctly
- ✅ Version is correct
- ✅ Links work (Homepage, Documentation, Issues)
- ✅ Classifiers are correct
- ✅ Dependencies are listed

### 4. Test Production Installation

```bash
python3 -m venv prod-test
source prod-test/bin/activate

pip install aurora
aur --verify

deactivate
rm -rf prod-test
```

### 5. Push Git Tag

```bash
git push origin v0.2.0
```

This triggers GitHub release and makes version discoverable.

---

## Version Management

### Semantic Versioning

AURORA follows [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., `0.2.0`)
  - **MAJOR**: Breaking changes
  - **MINOR**: New features (backwards compatible)
  - **PATCH**: Bug fixes (backwards compatible)

### Version Bump Process

1. **Update `pyproject.toml`**:
   ```toml
   version = "0.3.0"  # Bump from 0.2.0
   ```

2. **Update `CHANGELOG.md`**:
   ```markdown
   ## [0.3.0] - 2025-01-30

   ### Added
   - New feature X
   - New feature Y

   ### Fixed
   - Bug fix Z
   ```

3. **Update `README.md`** (if version mentioned):
   - Update installation instructions if needed
   - Update feature list for new functionality

4. **Commit Changes**:
   ```bash
   git add pyproject.toml CHANGELOG.md README.md
   git commit -m "chore: bump version to 0.3.0"
   ```

5. **Create Git Tag**:
   ```bash
   git tag -a v0.3.0 -m "Release v0.3.0"
   git push origin main
   git push origin v0.3.0
   ```

---

## Automated Publishing

### GitHub Actions Workflow (Optional)

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install build tools
        run: |
          pip install build twine

      - name: Build distributions
        run: python -m build

      - name: Check distributions
        run: twine check dist/*

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

### Setup GitHub Secrets

1. Go to GitHub repository → Settings → Secrets → Actions
2. Add new secret: `PYPI_API_TOKEN`
3. Paste your PyPI API token

### Automated Workflow

1. Update version in `pyproject.toml`
2. Commit and push changes
3. Create and push git tag: `git tag v0.3.0 && git push origin v0.3.0`
4. GitHub Actions automatically builds and publishes to PyPI

---

## Troubleshooting

### Common Issues

#### 1. Package Name Already Exists

**Error**: `The name 'aurora' is already taken`

**Solution**: Choose a different package name in `pyproject.toml`:
```toml
name = "aurora-framework"  # or "aurora-ai", "aurora-actr", etc.
```

#### 2. Invalid Credentials

**Error**: `Invalid or non-existent authentication information`

**Solution**:
- Verify `~/.pypirc` has correct token (starts with `pypi-`)
- Regenerate token on PyPI if needed
- Ensure username is `__token__` (not your actual username)

#### 3. Version Already Exists

**Error**: `File already exists`

**Solution**:
- PyPI doesn't allow overwriting versions
- Bump version number in `pyproject.toml`
- Rebuild and upload: `python -m build && twine upload dist/*`

#### 4. Missing README

**Error**: `long_description is not valid reStructuredText`

**Solution**:
- Ensure `README.md` exists and is well-formed
- Check `pyproject.toml` has: `readme = "README.md"`

#### 5. Missing Dependencies

**Error**: `aurora-core not found` when installing

**Solution**:
- Publish component packages first (aurora-core, aurora-cli, etc.)
- Or remove them from `dependencies` in `pyproject.toml` for testing

#### 6. Build Warnings

**Warning**: `keywords defined outside of pyproject.toml is ignored`

**Solution**: Already fixed - keywords now in `pyproject.toml`

#### 7. Network Errors

**Error**: `HTTPSConnectionPool` or `Connection timeout`

**Solution**:
- Check internet connection
- PyPI may be temporarily down (check https://status.python.org/)
- Try again in a few minutes

---

## Best Practices

### Before Every Release

1. ✅ Run full test suite: `pytest tests/ -v`
2. ✅ Run type checking: `mypy packages/`
3. ✅ Run linting: `ruff check packages/`
4. ✅ Update `CHANGELOG.md` with all changes
5. ✅ Test installation from TestPyPI
6. ✅ Create git tag matching version

### Security

- ✅ **Never commit `.pypirc`** to version control
- ✅ Use API tokens (not passwords) for PyPI authentication
- ✅ Rotate tokens periodically
- ✅ Use GitHub Secrets for CI/CD tokens

### Documentation

- ✅ Keep `README.md` comprehensive and up-to-date
- ✅ Document breaking changes in `CHANGELOG.md`
- ✅ Update examples when APIs change
- ✅ Link to documentation from PyPI page

### Testing

- ✅ Always test on TestPyPI first
- ✅ Test installation in clean virtual environment
- ✅ Verify all console scripts work (`aur`, `aurora-mcp`, etc.)
- ✅ Test optional dependencies (`pip install aurora[ml]`)

---

## Resources

- **PyPI**: https://pypi.org/
- **TestPyPI**: https://test.pypi.org/
- **Python Packaging Guide**: https://packaging.python.org/
- **Twine Documentation**: https://twine.readthedocs.io/
- **Semantic Versioning**: https://semver.org/
- **PEP 517 (Build System)**: https://peps.python.org/pep-0517/
- **PEP 639 (License)**: https://peps.python.org/pep-0639/

---

## Quick Reference

### Build and Test Locally

```bash
rm -rf dist/ build/ src/*.egg-info
python3 -m build --no-isolation
twine check dist/*
```

### Upload to TestPyPI

```bash
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple aurora
```

### Upload to Production PyPI

```bash
twine upload dist/*
pip install aurora
```

### Create Release Tag

```bash
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

---

**Last Updated**: 2025-12-25
**AURORA Version**: 0.2.0
