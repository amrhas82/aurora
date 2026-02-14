# Aurora Release Workflow

## Quick Start

### Local Development
```bash
./install.sh
```

### Release to PyPI
```bash
./scripts/release.sh 0.4.3
```

## Scripts

### `install.sh` - Local Development
Installs aurora-actr in editable mode for development.

```bash
./install.sh           # Install current version
./install.sh 0.5.1     # Bump to 0.5.1 and install
```

**What it does:**
1. Optionally bumps version if parameter provided
2. Cleans stale egg-info metadata
3. Tries editable install (`pip install -e .`)
4. Falls back to wheel install if pip is old

### `scripts/bump-version.sh` - Version Bump (No Release)
Updates version in all files without releasing.

```bash
./scripts/bump-version.sh <version>
```

**Example:**
```bash
./scripts/bump-version.sh 0.5.1
```

**What it does:**
1. Updates version in pyproject.toml
2. Updates CLI version in main.py
3. Shows next steps (test, commit, release)

**Use when:** You want to bump version for testing without releasing to PyPI yet.

### `scripts/release.sh` - PyPI Release
Releases a specific version to PyPI.

```bash
./scripts/release.sh <version>
```

**Example:**
```bash
./scripts/release.sh 0.5.1
```

**What it does:**
1. Updates version in pyproject.toml
2. Updates CLI version in main.py
3. Cleans and builds distribution
4. Uploads to PyPI
5. Commits, tags, and pushes to git

**Use when:** You're ready to publish a new version to PyPI immediately.

## Complete Release Checklist

Follow these steps in order. **Never skip pre-commit hooks.**

**For configurator/template changes:** See `TOOLS_CONFIG_GUIDE.md` § Release Checklist for additional checks specific to slash command configurators and tool integrations.

### 1. Update CHANGELOG.md

Add entries for all changes since the last release under a new version heading:

```markdown
## [0.X.Y] - YYYY-MM-DD

### Added
- New features...

### Fixed
- Bug fixes...

### Changed
- Other changes...
```

### 2. Bump Version

```bash
./scripts/bump-version.sh 0.X.Y
```

This updates `pyproject.toml` and `packages/cli/src/aurora_cli/main.py`.

### 3. Run Pre-Commit Hooks (NEVER SKIP)

Stage all changes and run pre-commit. Fix any failures iteratively:

```bash
git add -A
pre-commit run --all-files
```

If hooks modify files (black, isort), re-stage and re-run until all pass.

### 4. Run Tests

```bash
make test
```

All tests must pass. Do not release with failures.

### 5. Commit

```bash
git commit -m "chore: release v0.X.Y"
```

Pre-commit hooks run again during commit — this is expected and must pass.

### 6. Build Distribution

```bash
rm -rf dist/ build/ src/*.egg-info
python3 -m build
```

### 7. Verify Build Contents

Check that the wheel includes all expected packages before uploading:

```bash
python3 -m zipfile -l dist/aurora_actr-*.whl | grep -E '/__init__\.py$' | sort
```

Expected packages: `aurora_cli`, `aurora_core`, `aurora_context_code`, `aurora_context_doc`, `aurora_lsp`, `aurora_reasoning`, `aurora_soar`, `aurora_spawner`, `aurora_testing`, `implement`, `aurora_mcp`.

If a package is missing, check the symlinks in `src/` and `pyproject.toml` `[tool.setuptools.packages.find]`.

### 8. Upload to PyPI

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=$(pass amr/pypi_api)
python3 -m twine upload dist/*
```

### 9. Refresh Local Install and Verify

```bash
pip install -e .
```

Verify the correct version is active and source paths point to the repo (not stale site-packages):

```bash
aur --version
python3 -c "import aurora_core; print(aurora_core.__file__)"
# Should show: /path/to/aurora/src/aurora_core/__init__.py (NOT site-packages)
```

If you see a `site-packages` path, the editable install is being shadowed by a stale non-editable install:

```bash
pip uninstall aurora-actr && pip install -e .
```

### 10. Tag and Push

```bash
git tag v0.X.Y
git push origin main --tags
```

### 11. Monitor CI

```bash
gh run list --limit 1
gh run watch        # Wait for completion
```

CI must be green. If it fails, investigate and fix immediately — do not leave main broken.

### 12. Verify on PyPI

```bash
pip install --upgrade aurora-actr  # From a clean venv if possible
```

Visit: `https://pypi.org/project/aurora-actr/0.X.Y/`

---

**Alternative: One-Command Release** (if all pre-checks already pass)

`release.sh` combines steps 2, 6, 5, 8 into one command. Only use it after steps 1, 3, 4 are already done:

```bash
./scripts/release.sh 0.X.Y
```

Note: `release.sh` uses `git add -A` — ensure no unwanted files are in the working tree.

## Version Strategy

[Semantic Versioning](https://semver.org/):
- **PATCH** (0.4.1 → 0.4.2): Bug fixes
- **MINOR** (0.4.2 → 0.5.0): New features, backward compatible
- **MAJOR** (0.5.0 → 1.0.0): Breaking changes

## PyPI Setup

### First-Time Authentication
Create `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-AgEN...your-token...
```

Get token from: https://pypi.org/manage/account/token/

## Troubleshooting

### egg-info permission error
```bash
sudo chown -R $USER:$USER src/
rm -rf src/*.egg-info
```

### Old pip (editable install fails)
The install.sh fallback handles this automatically by building a wheel.

Or upgrade pip:
```bash
pip install --upgrade pip
```

### PyPI upload "File already exists"
You can't re-upload the same version. Bump version and try again.

---

## See Also

- **TOOLS_CONFIG_GUIDE.md** - Complete guide for configurator system (slash commands, templates, adding tools)
- **COMMANDS.md** - User-facing command documentation
- **README.md** - Project overview and installation
