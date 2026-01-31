# ML Dependencies Installation Guide

Aurora uses optional ML dependencies for semantic search. You only need to install these if you plan to use:
- `aur mem index` - Code indexing with embeddings
- `aur mem search` - Semantic code search
- `aur init` - Project initialization with indexing
- `aur soar` - SOAR reasoning (uses memory retrieval)

## Quick Install (CPU-Only, Recommended)

**For most users without NVIDIA GPU:**

```bash
# 1. Install PyTorch (CPU version, ~100MB)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 2. Install sentence-transformers
pip install sentence-transformers

# 3. Download embedding model
aur doctor --fix-ml
```

**Total download:** ~200MB (vs 3GB+ for GPU version)

## Alternative: GPU Version

**Only if you have an NVIDIA GPU and want GPU acceleration:**

```bash
# Install with CUDA support (~3GB)
pip install sentence-transformers

# Download embedding model
aur doctor --fix-ml
```

⚠️ **Warning:** GPU version downloads ~3GB of CUDA libraries. Only install if you have an NVIDIA GPU.

## What Happens Without ML Dependencies?

Aurora will work fine for all non-ML commands. When you try to use ML features, you'll get a helpful error:

```
$ aur mem index .

[dim]Checking ML dependencies...[/]
[bold red]ML Setup Required[/]
sentence-transformers package not installed.

[bold]Solution:[/]
  1. Install PyTorch (CPU version):
     [cyan]pip install torch --index-url https://download.pytorch.org/whl/cpu[/]

  2. Install sentence-transformers:
     [cyan]pip install sentence-transformers[/]

  3. Download model:
     [cyan]aur doctor --fix-ml[/]
```

## Do You Need GPU for Development?

**No!** The CPU version is perfectly fine for:
- ✅ Development and testing
- ✅ Running Aurora CLI
- ✅ Embedding generation (fast enough on CPU for the small model)
- ✅ All Aurora features

GPU only helps if you're:
- ❌ Training large ML models (Aurora doesn't do this)
- ❌ Processing huge batches of embeddings (Aurora uses small batches)

## Uninstalling GPU Version

If you accidentally installed the GPU version:

```bash
# Remove GPU dependencies
pip uninstall torch torchvision torchaudio -y

# Install CPU version
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Verify size (should be ~100MB, not 3GB)
pip show torch
```

## Quick Reference

| Version | Download Size | Use Case |
|---------|---------------|----------|
| **CPU** (recommended) | ~200MB | Most users, dev work |
| **GPU** (optional) | ~3GB | Only if you have NVIDIA GPU |

## After Installation

Once ML dependencies are installed:

```bash
# Verify installation
aur doctor --fix-ml

# Should output:
# ✓ sentence-transformers is installed
# ✓ Embedding model already cached
# ✓ ML setup complete!
```
