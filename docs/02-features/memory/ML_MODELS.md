# ML Models Guide

How to customize semantic embedding models in AURORA.

## Default Model

AURORA uses `all-MiniLM-L6-v2` by default:
- General-purpose (code + docs + reasoning)
- 384 dimensions
- 80MB model size
- Fast inference (~50ms per chunk)

## When to Use ML

**Use ML features (install manually: `pip install sentence-transformers torch`):**
- Large codebases (10K+ files)
- Need conceptual search ("authentication" finds login(), verify_token())
- Searching documentation semantically
- Multi-language codebases

**Skip ML (use default BM25 + activation):**
- Small to medium projects
- Keyword search is sufficient
- Disk/bandwidth constraints
- CI/CD environments

## Changing the Model

### Method 1: Environment Variable

```bash
export AURORA_EMBEDDING_MODEL="microsoft/codebert-base"
aur mem index .
```

### Method 2: Python Configuration

Create `~/.aurora/config.json`:

```json
{
  "embedding_model": "microsoft/codebert-base"
}
```

### Method 3: Programmatic (Advanced)

```python
from aurora_context_code.semantic import EmbeddingProvider

# Initialize with custom model
provider = EmbeddingProvider(
    model_name="microsoft/codebert-base",
    device="cuda"  # or "cpu"
)

# Use in your code
embedding = provider.embed_chunk("def hello(): pass")
```

## Popular Models

### General Purpose

**all-MiniLM-L6-v2** (default)
- Size: 80MB
- Dims: 384
- Best for: Balanced performance across code, docs, reasoning
- Speed: Very fast

**all-MiniLM-L12-v2**
- Size: 120MB
- Dims: 384
- Best for: Better quality, slightly slower
- Speed: Fast

### Code-Specific

**microsoft/codebert-base**
- Size: 500MB
- Dims: 768
- Best for: Code understanding, API patterns
- Weakness: Less effective on general documentation
- Speed: Medium

**Salesforce/codet5-base**
- Size: 900MB
- Dims: 768
- Best for: Code generation patterns
- Weakness: Slower inference
- Speed: Slow

### Smaller/Faster

**paraphrase-MiniLM-L3-v2**
- Size: 60MB
- Dims: 384
- Best for: Speed-critical applications
- Trade-off: Slightly lower quality
- Speed: Very fast

### Multilingual

**paraphrase-multilingual-MiniLM-L12-v2**
- Size: 420MB
- Dims: 384
- Best for: Multi-language codebases (50+ languages)
- Speed: Fast

## Model Trade-offs

| Factor | Small Models | Large Models |
|--------|-------------|--------------|
| Size | 60-120MB | 500-900MB |
| Speed | <50ms | 100-300ms |
| Quality | Good | Better |
| Code-specific | General | Specialized |

## Recommendations

**For most projects:**
- Stick with default `all-MiniLM-L6-v2`
- Good balance of quality, speed, size
- Works well for code + docs + reasoning

**For code-heavy projects:**
- Use `microsoft/codebert-base`
- Better code semantics
- Keep default model for documentation search (requires dual setup)

**For speed-critical:**
- Use `paraphrase-MiniLM-L3-v2`
- 25% smaller, 20% faster
- Minimal quality loss

**For multi-language:**
- Use `paraphrase-multilingual-MiniLM-L12-v2`
- Supports 50+ languages
- Good quality

## Re-indexing After Model Change

After changing models, re-index your codebase:

```bash
# Clear existing embeddings (optional)
rm .aurora/memory.db

# Re-index with new model
aur mem index .
```

## Model Resources

- [Sentence-Transformers Model List](https://www.sbert.net/docs/pretrained_models.html)
- [HuggingFace Models](https://huggingface.co/models?library=sentence-transformers)
- [Model Benchmarks](https://www.sbert.net/docs/pretrained_models.html#model-overview)

## Troubleshooting

**Model not downloading:**
- Check internet connection
- Models download to `~/.cache/torch/sentence_transformers/`
- Verify disk space (~500MB-1GB per model)

**Out of memory:**
- Use smaller model (MiniLM-L3-v2)
- Reduce batch size (not configurable in current version)
- Use CPU instead of GPU

**Slow inference:**
- Check if GPU is being used: `torch.cuda.is_available()`
- Use smaller model
- Consider skipping ML entirely (BM25 + activation is fast)
