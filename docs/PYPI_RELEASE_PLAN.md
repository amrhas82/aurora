# PyPI Release Plan: No Bloat Strategy

## Problem
Current optional dependency `[ml]` installs GPU version of PyTorch by default (~3GB).

## Solution for 0.10.1 Release

### Option A: CPU-Only Extra (Recommended)
```toml
# pyproject.toml
[project.optional-dependencies]
ml = [
    "torch>=2.0.0; platform_machine != 'x86_64'",  # GPU for non-x86
    "torch>=2.0.0+cpu; platform_machine == 'x86_64'",  # CPU for x86
    "sentence-transformers>=2.2.0",
]
```

**Issues:**
- CPU index URLs not directly supported in pyproject.toml
- Would still default to GPU version

### Option B: Separate CPU/GPU Extras (Better)
```toml
[project.optional-dependencies]
ml-cpu = [
    "sentence-transformers>=2.2.0",
]
ml-gpu = [
    "sentence-transformers>=2.2.0",
]
```

**Installation:**
```bash
# CPU-only (recommended, ~200MB)
pip install aurora-actr[ml-cpu]
pip install torch --index-url https://download.pytorch.org/whl/cpu

# GPU version (~3GB)
pip install aurora-actr[ml-gpu]
```

**Documentation in README:**
```markdown
## Installation

### Basic (no ML features)
```bash
pip install aurora-actr
```

### With ML features (CPU - recommended)
```bash
pip install aurora-actr[ml-cpu]
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### With ML features (GPU)
Only if you have NVIDIA GPU:
```bash
pip install aurora-actr[ml-gpu]
```
```

### Option C: Post-Install Message (Simplest)
Keep current structure, add post-install guidance:

```python
# setup.py or __init__.py
def _check_ml_deps():
    try:
        import torch
        import sentence_transformers
    except ImportError:
        print("""
╔════════════════════════════════════════════════════════════╗
║  Aurora ML features require additional dependencies        ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  CPU-only (recommended, ~200MB):                           ║
║    pip install torch --index-url https://... /cpu          ║
║    pip install sentence-transformers                       ║
║    aur doctor --fix-ml                                     ║
║                                                            ║
║  Or use: ./install.sh (includes ML by default)             ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
        """)
```

## Recommendation: Option B + Option C

**pyproject.toml:**
```toml
[project.optional-dependencies]
ml-cpu = [
    "sentence-transformers>=2.2.0",
]
ml-gpu = [
    "sentence-transformers>=2.2.0",
]
ml = [
    "sentence-transformers>=2.2.0",  # Keep for backward compatibility
]
```

**README.md:**
```markdown
## Quick Start

### From GitHub (includes ML)
```bash
git clone https://github.com/your-org/aurora
cd aurora
./install.sh  # Installs everything including ML (CPU-only)
```

### From PyPI

#### Basic install
```bash
pip install aurora-actr
```

#### With ML features (CPU - recommended)
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install aurora-actr[ml-cpu]
aur doctor --fix-ml  # Download embedding model
```

#### With ML features (GPU)
Only if you have NVIDIA GPU:
```bash
pip install aurora-actr[ml-gpu]
aur doctor --fix-ml
```

## Why CPU-only?

| Version | Size | Speed | Use Case |
|---------|------|-------|----------|
| CPU | ~200MB | Fast enough | 99% of users |
| GPU | ~3GB | Slightly faster | NVIDIA GPU owners |

Aurora's embedding model (all-MiniLM-L6-v2) is tiny and runs great on CPU.
```

## Changes Needed for 0.10.1

1. **Update pyproject.toml:**
   - Add `ml-cpu` and `ml-gpu` extras
   - Keep `ml` for backward compatibility

2. **Update README.md:**
   - Add installation section with CPU/GPU options
   - Explain why CPU is recommended
   - Show PyPI install commands

3. **Add post-install message:**
   - Show in CLI on first run if ML deps missing
   - Guide users to install CPU version

4. **Update ./install.sh:** (DONE ✅)
   - Install ML dependencies by default (CPU-only)

5. **Update docs:**
   - Add ML_INSTALL.md to docs/
   - Reference from main README

## Testing Plan

Before 0.10.1 release:

```bash
# Test 1: PyPI install without ML
pip install aurora-actr
aur mem index .  # Should fail with helpful message

# Test 2: PyPI install with ML (CPU)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install aurora-actr[ml-cpu]
aur doctor --fix-ml
aur mem index .  # Should work

# Test 3: GitHub install
git clone ...
./install.sh  # Should install ML (CPU) by default
aur mem index .  # Should work

# Test 4: Verify no GPU bloat
pip show torch | grep Version  # Should show +cpu suffix
```

## Release Checklist

- [ ] Update pyproject.toml with ml-cpu/ml-gpu extras
- [ ] Update README.md with installation instructions
- [ ] Add post-install message
- [ ] Update ML_INSTALL.md
- [ ] Test all installation methods
- [ ] Update CHANGELOG.md
- [ ] Tag release: 0.10.1
- [ ] Push to PyPI
- [ ] Update GitHub release notes

## Version Numbering

- 0.10.1 - ML install improvements (this release)
- 0.10.2+ - Future features

## Timeline

- Code changes: 1 day
- Testing: 1 day
- Release: 0.10.1 ready in ~2 days
