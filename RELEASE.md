# Aurora Release Workflow

## Quick Start

### For Local Development
After making changes, reinstall packages:
```bash
./install.sh
```

### For Release
Create a new release with automatic versioning:
```bash
# Patch release (0.3.0 → 0.3.1)
./scripts/release.sh patch

# Minor release (0.3.0 → 0.4.0)
./scripts/release.sh minor

# Major release (0.3.0 → 1.0.0)
./scripts/release.sh major

# Publish to PyPI immediately
./scripts/release.sh patch --publish
```

## What Each Script Does

### `install.sh` - Local Development
**Use when:** You've made code changes and want to test them

**What it does:**
1. Uninstalls all aurora packages
2. Cleans stale metadata (.egg-info, .dist-info, .pth files)
3. Reinstalls all aurora packages in editable mode from source
4. Verifies installation and shows versions

**Usage:**
```bash
sudo ./install.sh
```

**Run this after:**
- Modifying any Python code
- Updating pyproject.toml versions
- Adding new packages
- Fixing bugs or adding features

### `scripts/release.sh` - Production Release
**Use when:** You're ready to release a new version

**What it does:**
1. ✓ Checks dependencies (python3-venv, build, twine) - installs if missing
2. ✓ Bumps version numbers (main + all sub-packages)
3. ✓ Updates CLI version in main.py
4. ✓ Reinstalls all packages locally
5. ✓ Verifies installation
6. ✓ Runs test suite
7. ✓ Updates CHANGELOG.md with release date
8. ✓ Creates git commit and tag
9. ✓ Builds distribution packages (.tar.gz and .whl)
10. ✓ Optionally publishes to PyPI

**Usage:**
```bash
# Patch release (0.3.1 → 0.3.2) - Bug fixes only
./scripts/release.sh patch

# Minor release (0.3.1 → 0.4.0) - New features, backward compatible
./scripts/release.sh minor

# Major release (0.3.1 → 1.0.0) - Breaking changes
./scripts/release.sh major

# Publish to PyPI immediately (recommended for quick releases)
./scripts/release.sh patch --publish
./scripts/release.sh minor --publish
./scripts/release.sh major --publish
```

**Common Scenarios:**

1. **Quick bug fix release:**
```bash
# Fix bug in code
sudo ./install.sh              # Test locally
./scripts/release.sh patch --publish    # Release to PyPI
```

2. **Feature release with testing:**
```bash
# Add new feature
sudo ./install.sh              # Test locally
pytest tests/                  # Run full test suite
./scripts/release.sh minor     # Create release (no publish)
# Review git commit and CHANGELOG
git push origin main --tags    # Push to GitHub
python3 -m twine upload dist/* # Publish to PyPI manually
```

3. **Breaking change release:**
```bash
# Make breaking changes
# Update migration guide
sudo ./install.sh
./scripts/release.sh major
# Carefully review before publishing
python3 -m twine upload --repository testpypi dist/*  # Test first
python3 -m twine upload dist/*  # Publish for real
```

## Release Checklist

### Before Release
- [ ] All tests passing: `pytest tests/`
- [ ] Code formatted: `ruff check --fix .`
- [ ] Type checks: `mypy packages/*/src/`
- [ ] CHANGELOG.md updated with changes
- [ ] All features documented

### During Release
- [ ] Run `./scripts/release.sh [major|minor|patch]`
- [ ] Verify version numbers: `pip list | grep aurora`
- [ ] Test CLI: `aur --version && aur doctor`
- [ ] Review git commit and tag

### After Release
- [ ] Push to GitHub: `git push origin main && git push --tags`
- [ ] Publish to PyPI: `python -m twine upload dist/*`
- [ ] Create GitHub release with CHANGELOG excerpt
- [ ] Announce in relevant channels

## Version Strategy

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes, incompatible API changes
- **MINOR** (0.X.0): New features, backward compatible
- **PATCH** (0.0.X): Bug fixes, backward compatible

**Main Package vs Sub-Packages:**
- Main package (`aurora-actr`): Full version (e.g., 0.3.1)
- Sub-packages: Minor version only (e.g., 0.3.0)
  - This allows patches to main package without re-releasing all sub-packages

## PyPI Publishing

### Prerequisites (Automated by release.sh)

The release script automatically checks and installs:

1. **System dependency:**
```bash
sudo apt install python3.10-venv
```

2. **Python tools:**
```bash
pip install --user build twine
```

The script will prompt you to install missing dependencies.

### First-Time Authentication Setup

Create `~/.pypirc` with your PyPI API token:
```ini
[pypi]
username = __token__
password = pypi-AgEN...your-token-here...

[testpypi]
username = __token__
password = pypi-AgEN...your-test-token-here...
```

**Get tokens from:**
- Production: https://pypi.org/manage/account/token/
- Test: https://test.pypi.org/manage/account/token/

### Publishing Workflow

**Recommended (fully automated):**
```bash
./scripts/release.sh patch --publish
```

**Manual (more control):**
```bash
# 1. Create release locally
./scripts/release.sh patch

# 2. Review changes
git log -1
cat CHANGELOG.md | head -50
ls -lh dist/

# 3. Test on TestPyPI first (optional but recommended)
python3 -m twine upload --repository testpypi dist/*

# 4. Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ aurora-actr --upgrade

# 5. If good, upload to production PyPI
python3 -m twine upload dist/*

# 6. Push to GitHub
git push origin main --tags
```

## Troubleshooting

### Build fails with "ensurepip not available"
**Symptom:** `python3 -m build` fails with venv error
**Solution:**
```bash
sudo apt install python3.10-venv
```

### "Permission denied" during install
**Symptom:** install.sh fails with permission errors
**Solution:**
```bash
sudo ./install.sh
```

### Version not updating in pip list
**Symptom:** `pip list | grep aurora` shows old versions
**Solution:**
```bash
# install.sh now handles this automatically
sudo ./install.sh

# Or manually:
find packages/ -name "*.egg-info" -exec rm -rf {} +
rm -rf ~/.local/lib/python*/site-packages/aurora*.dist-info
pip uninstall -y aurora-actr aurora-cli aurora-core
sudo ./install.sh
```

### Tests failing after changes
**Solution:**
```bash
# Run tests with verbose output
pytest tests/ -v --tb=short

# Run specific test file
pytest tests/unit/cli/test_doctor.py -v

# Run with coverage
pytest tests/ --cov=aurora_cli --cov-report=term-missing
```

### PyPI upload fails with "Invalid credentials"
**Solution:**
```bash
# Check credentials file exists
cat ~/.pypirc

# Get new token from: https://pypi.org/manage/account/token/
# Update ~/.pypirc with new token
```

### PyPI upload fails with "File already exists"
**Symptom:** Can't upload same version twice
**Solution:**
```bash
# Bump version and rebuild
./scripts/release.sh patch
python3 -m twine upload dist/*
```

### Release script fails at build step
**Symptom:** Build step shows error about dependencies
**Solution:**
```bash
# Install missing system packages
sudo apt install python3.10-venv

# Install Python packages
pip install --user build twine

# Run release again
./scripts/release.sh patch
```

### Git push fails after release
**Symptom:** Can't push to GitHub after creating release
**Solution:**
```bash
# Push commit and tags separately
git push origin main
git push origin --tags

# Or force push if needed (careful!)
git push origin main --force-with-lease
```

## Package Structure

```
aurora/
├── install.sh              # Local development reinstall
├── scripts/
│   └── release.sh          # Production release automation
├── pyproject.toml          # Main package (aurora-actr)
├── packages/
│   ├── cli/                # aurora-cli
│   ├── core/               # aurora-core
│   ├── context-code/       # aurora-context-code
│   ├── soar/               # aurora-soar
│   ├── reasoning/          # aurora-reasoning
│   ├── planning/           # aurora-planning
│   └── testing/            # aurora-testing
└── CHANGELOG.md            # Release history
```

## Examples

### Patch Release (Bug Fix)
```bash
# Make bug fixes
git add -A
git commit -m "fix: correct memory leak in indexer"

# Release patch version
./scripts/release.sh patch

# Push to GitHub
git push origin main
git push --tags

# Publish to PyPI
python -m twine upload dist/*
```

### Minor Release (New Feature)
```bash
# Add new feature
git add -A
git commit -m "feat: add semantic search filters"

# Update CHANGELOG.md with feature description

# Release minor version
./scripts/release.sh minor --publish  # Publishes immediately
```

### Major Release (Breaking Changes)
```bash
# Make breaking changes
# Update migration guide

# Release major version
./scripts/release.sh major

# Manually review before publishing
git push origin main
git push --tags
python -m twine upload dist/*
```
