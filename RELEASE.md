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
1. Reinstalls all aurora packages in editable mode
2. Updates package metadata
3. Shows installed versions

**Usage:**
```bash
sudo ./install.sh
```

### `scripts/release.sh` - Production Release
**Use when:** You're ready to release a new version

**What it does:**
1. ✓ Bumps version numbers (main + all sub-packages)
2. ✓ Updates CLI version in main.py
3. ✓ Reinstalls all packages locally
4. ✓ Verifies installation
5. ✓ Runs test suite
6. ✓ Updates CHANGELOG.md with release date
7. ✓ Creates git commit and tag
8. ✓ Builds distribution packages
9. ✓ Optionally publishes to PyPI

**Usage:**
```bash
# Patch release (bug fixes)
./scripts/release.sh patch

# Minor release (new features)
./scripts/release.sh minor

# Major release (breaking changes)
./scripts/release.sh major

# Publish immediately
./scripts/release.sh patch --publish
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

### First-Time Setup
```bash
# Install build tools
pip install build twine

# Configure PyPI credentials
python -m twine upload dist/* --repository testpypi  # Test first
python -m twine upload dist/*                         # Production
```

### Authentication
Create `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-xxxxxxxxxxxx

[testpypi]
username = __token__
password = pypi-xxxxxxxxxxxx
```

## Troubleshooting

### "Permission denied" during install
```bash
sudo ./install.sh
```

### Version not updating
```bash
# Force reinstall
pip uninstall -y aurora-actr
./install.sh
```

### Tests failing
```bash
# Run tests with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/unit/cli/test_doctor.py -v
```

### PyPI upload fails
```bash
# Check credentials
cat ~/.pypirc

# Use test PyPI first
python -m twine upload --repository testpypi dist/*
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
