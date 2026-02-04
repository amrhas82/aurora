# ML Dependencies

Aurora includes `sentence-transformers` as a required dependency for semantic search. It is installed automatically with Aurora.

## What's Included

When you install Aurora, you get:
- `sentence-transformers` - For generating text embeddings
- Embedding model auto-downloads on first use (~88MB)

## First Run

On first use of memory indexing, the embedding model will download automatically:

```bash
$ aur init
# ...
Step 2/3: Memory Indexing
Downloading embedding model: sentence-transformers/all-MiniLM-L6-v2 (~88MB)
✓ Download complete!
```

## CPU vs GPU

By default, PyTorch installs with CPU support only. This is fine for Aurora's use case.

**If you want GPU acceleration** (NVIDIA GPU only):

```bash
# Uninstall CPU version
pip uninstall torch -y

# Install CUDA version (~3GB)
pip install torch
```

GPU only helps for very large codebases. CPU is fast enough for most projects.

## Troubleshooting

### Package not found after install

If you installed Aurora but `sentence-transformers` is missing:

```bash
# Reinstall Aurora
pip install -e . --force-reinstall

# Or install directly
pip install sentence-transformers
```

### Model download failed

If the model fails to download:

```bash
# Manual download
aur doctor --fix-ml

# Or directly via Python
python -c 'from sentence_transformers import SentenceTransformer; SentenceTransformer("all-MiniLM-L6-v2")'
```

### Verify installation

```bash
aur doctor --fix-ml
# Should output:
# ✓ sentence-transformers is installed
# ✓ Embedding model already cached
# ✓ ML setup complete!
```
