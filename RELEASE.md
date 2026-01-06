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

## Pre-Release Checklist

Before releasing, ensure quality by running local CI checks:

### 1. Quick Health Check (30 seconds)
```bash
./scripts/quick-check.sh
```

This runs the test suite quickly to catch obvious issues.

### 2. Full CI Check (3-5 minutes) - **REQUIRED BEFORE RELEASE**
```bash
./scripts/run-local-ci.sh
```

This runs:
- All tests (same as GitHub CI)
- Pre-commit hooks (formatting, linting, security)
- Coverage reporting

**Release Criteria:**
- ✅ All tests passing
- ✅ No security issues (bandit)
- ✅ Code properly formatted (black, isort)
- ✅ Test coverage meets standards

### 3. Then Release
```bash
./scripts/release.sh <version>
```

**Typical pre-release workflow:**
```bash
# 1. Run full local CI
./scripts/run-local-ci.sh

# 2. If all checks pass, release
./scripts/release.sh 0.5.1

# 3. Verify on PyPI
pip install --upgrade aurora-actr
```

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
