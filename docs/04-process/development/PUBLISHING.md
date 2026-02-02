# Aurora Publishing Guide

## Published to PyPI ✓

Aurora is now available on PyPI: https://pypi.org/project/aurora-actr/

**Latest Version:** 0.3.1 (January 5, 2026)

## Quick Publish

```bash
./scripts/release.sh patch --publish   # Bug fixes
./scripts/release.sh minor --publish   # New features  
./scripts/release.sh major --publish   # Breaking changes
```

## Prerequisites

```bash
# System dependency
sudo apt install python3.10-venv

# Python tools (already installed)
pip install --user build twine
```

## PyPI Credentials

Configured in `~/.pypirc` (already set up)

## What Happened Today

✅ Published aurora-actr 0.3.1 to PyPI
✅ View at: https://pypi.org/project/aurora-actr/0.3.1/
✅ Release script now checks dependencies
✅ Build process working

## Next Release

Just run: `./scripts/release.sh patch --publish`

Full guide in `RELEASE.md`
