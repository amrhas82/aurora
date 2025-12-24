# AURORA Advanced Troubleshooting Guide

**Version**: 1.0
**Date**: December 23, 2025
**Status**: Production Ready

---

## Common Issues

### 1. Activation Calculation Errors

#### Issue: All activations are negative

**Symptom**: Every chunk has negative activation (e.g., -5.686, -8.292)

**Cause**: This is **normal behavior**. ACT-R uses logarithmic scales where negative values are expected.

**Solution**:
- Compare **relative** activations, not absolute values
- Higher (less negative) = better
- Set appropriate retrieval threshold (e.g., -2.0)

```python
# Correct approach
results = sorted(chunks, key=lambda c: c.activation, reverse=True)
top_chunks = results[:10]  # Get 10 highest activations
```

---

#### Issue: Activation calculations are very slow

**Symptom**: Each activation calculation takes >100ms

**Diagnosis**:
```python
import time
start = time.time()
result = engine.calculate_total(...)
elapsed_ms = (time.time() - start) * 1000
print(f"Activation time: {elapsed_ms:.1f}ms")
```

**Solutions**:
1. **Enable activation caching**:
   ```python
   config = CacheConfig(activation_cache_enabled=True, activation_cache_ttl=600)
   ```

2. **Reduce spreading computation**:
   ```python
   config = SpreadingConfig(max_hops=2, max_edges=500)
   ```

3. **Use batch processing**:
   ```python
   results = retriever.retrieve(chunks, batch_size=1000)
   ```

---

#### Issue: Spreading activation always returns 0.0

**Symptom**: `result.spreading == 0.0` for all chunks

**Diagnosis**:
```python
# Check graph has relationships
print(f"Graph edges: {len(graph.relationships)}")

# Check target is connected to active chunks
paths = graph.find_paths(active_ids, target_id, max_hops=3)
print(f"Paths found: {len(paths)}")
```

**Common Causes**:
1. **Empty relationship graph**: No relationships loaded
2. **Disconnected chunks**: Target not reachable from active chunks
3. **max_hops too low**: Distance exceeds limit
4. **Spreading disabled**: Check `enable_spreading=True`

**Solutions**:
```python
# Verify spreading enabled
config = ActivationConfig(enable_spreading=True)

# Increase max hops if needed
spreading_config = SpreadingConfig(max_hops=5)

# Check graph is built correctly
print(f"Total nodes: {graph.node_count}")
print(f"Total edges: {graph.edge_count}")
```

---

### 2. Embedding Failures

#### Issue: Embedding generation fails with OutOfMemoryError

**Symptom**: Process crashes when generating embeddings for large batches

**Solutions**:
1. **Reduce batch size**:
   ```python
   provider = EmbeddingProvider()
   embeddings = provider.embed_batch(texts, batch_size=16)  # Reduce from 32
   ```

2. **Enable gradient checkpointing** (if using GPU):
   ```python
   model = SentenceTransformer(model_name)
   model.eval()  # Disable training mode
   ```

3. **Clear CUDA cache** (GPU):
   ```python
   import torch
   torch.cuda.empty_cache()
   ```

---

#### Issue: Semantic search returns irrelevant results

**Symptom**: Hybrid retrieval performs worse than activation-only

**Diagnosis**:
```python
# Check embedding quality
query_embedding = provider.embed_query("test query")
chunk_embedding = chunks[0].embedding

similarity = cosine_similarity(query_embedding, chunk_embedding)
print(f"Similarity: {similarity:.3f}")  # Should be >0.3 for relevant chunks
```

**Solutions**:
1. **Adjust hybrid weights**:
   ```python
   config = HybridConfig(
       activation_weight=0.7,  # Increase activation influence
       semantic_weight=0.3     # Reduce semantic influence
   )
   ```

2. **Use better embedding model**:
   ```python
   provider = EmbeddingProvider(model_name="all-mpnet-base-v2")  # Better than MiniLM
   ```

3. **Re-generate embeddings** if model changed:
   ```python
   for chunk in chunks:
       chunk.embedding = provider.embed_chunk(chunk.content)
       store.update_chunk(chunk)
   ```

---

#### Issue: Embedding fallback not working

**Symptom**: System crashes when embedding provider fails, instead of falling back to keyword-only

**Diagnosis**:
```python
# Check fallback is enabled
config = HybridConfig(enable_fallback=True)

# Simulate failure
try:
    results = retriever.retrieve(chunks, query)
except Exception as e:
    print(f"No fallback: {e}")
```

**Solution**: Ensure fallback is properly configured:
```python
retriever = HybridRetriever(
    store=store,
    engine=engine,
    provider=provider,
    config=HybridConfig(
        enable_fallback=True,  # Required
        fallback_threshold=0.6  # Confidence threshold
    )
)
```

---

### 3. Headless Mode Issues

#### Issue: Headless execution gets stuck in infinite loop

**Symptom**: Reaches max_iterations without making progress

**Diagnosis**:
```bash
# Check scratchpad for repeated actions
$ grep "Action:" scratchpad.md | sort | uniq -c
  5 Action: Ran tests
  5 Action: Fixed import error
  5 Action: Ran tests  # ← Stuck in loop
```

**Solutions**:
1. **Improve success criteria specificity**:
   ```markdown
   # Bad
   - [ ] Tests pass

   # Good
   - [ ] Running `pytest tests/` exits with code 0
   - [ ] All 47 tests show PASSED status
   - [ ] No FAILED or ERROR in test output
   ```

2. **Add more context**:
   ```markdown
   # Context
   The failing test is in tests/test_auth.py line 45.
   It expects response status 200 but gets 404.
   The endpoint is /api/auth/login in app/api/auth.py.
   ```

3. **Reduce scope**:
   ```markdown
   # Goal (too broad)
   Implement full authentication system

   # Goal (better)
   Implement user login endpoint that validates credentials
   ```

---

#### Issue: Headless mode terminates with GIT_SAFETY_ERROR

**Symptom**: Execution never starts, exits immediately with git error

**Diagnosis**:
```bash
$ git branch
* main  # ← Problem: on main branch

$ aur headless experiment.md
Error: Cannot run headless mode on branch 'main'
```

**Solution**: Create and switch to safety branch:
```bash
$ git checkout -b headless
$ aur headless experiment.md
✓ Running on branch 'headless'
```

---

#### Issue: Budget exceeded before goal achieved

**Symptom**: Terminates with BUDGET_EXCEEDED after 3-4 iterations

**Diagnosis**:
```bash
$ grep "Cost:" scratchpad.md
Cost: $1.20
Cost: $1.35
Cost: $1.50
Cost: $1.25  # Total: $5.30 (exceeded $5.00 budget)
```

**Solutions**:
1. **Increase budget**:
   ```bash
   $ aur headless experiment.md --budget 10.0
   ```

2. **Use cheaper model**:
   ```python
   config = SOARConfig(model="gpt-3.5-turbo")  # $0.15/iteration vs $0.50
   ```

3. **Simplify goal**: Break into smaller tasks
   ```markdown
   # Instead of one big goal
   Goal: Implement authentication system with login, registration, password reset

   # Split into 3 separate headless runs
   Goal: Implement user registration endpoint
   Goal: Implement user login endpoint
   Goal: Implement password reset flow
   ```

---

### 4. Performance Issues

#### Issue: Retrieval is very slow (>2 seconds for 5K chunks)

**Diagnosis**:
```python
from aurora_core.profiling import profile_retrieval

profile = profile_retrieval(retriever, chunks, query)
print(profile.breakdown)
```

**Output**:
```
Stage                      Time
--------------------------------
Candidate selection        50ms
Activation calculation     1800ms ← Bottleneck
Semantic similarity        120ms
Sorting & filtering        30ms
Total                      2000ms
```

**Solutions** (see [Performance Tuning Guide](./performance-tuning.md)):
1. Enable multi-tier caching
2. Use type pre-filtering
3. Increase activation threshold
4. Reduce graph size
5. Enable batch processing

---

#### Issue: Memory usage grows unbounded

**Symptom**: Process memory increases continuously, eventually crashes

**Diagnosis**:
```python
import tracemalloc
tracemalloc.start()

# Run queries
for i in range(1000):
    retriever.retrieve(chunks, query)
    if i % 100 == 0:
        current, peak = tracemalloc.get_traced_memory()
        print(f"Iteration {i}: {current / 1024 / 1024:.1f} MB")
```

**Common Causes**:
1. **Cache not evicting**: LRU cache size too large or not working
2. **Embeddings accumulating**: Not releasing after use
3. **Graph not rebuilding**: Old references not garbage collected

**Solutions**:
```python
# Limit cache size
config = CacheConfig(
    hot_cache_size=1000,  # Limit to 1000 chunks
    activation_cache_size=2000  # Limit activation scores
)

# Periodically clear caches
if query_count % 1000 == 0:
    cache_manager.clear_expired()

# Force garbage collection
import gc
gc.collect()
```

---

### 5. Integration Issues

#### Issue: SOAR pipeline fails with "Context too large"

**Symptom**: LLM API returns 400 error about context size

**Solutions**:
1. **Reduce max_results**:
   ```python
   config = RetrievalConfig(max_results=10)  # Down from 20
   ```

2. **Use summarization**:
   ```python
   def summarize_chunk(chunk):
       # Return only function signature, not full implementation
       return f"{chunk.name}: {chunk.signature}"

   context = [summarize_chunk(c) for c in results[:15]]
   ```

3. **Implement sliding window**:
   ```python
   # Process in batches
   for batch in chunk_batches(results, size=10):
       process_batch(batch)
   ```

---

## Error Messages Reference

### "RetryError: Failed after 3 attempts"

**Meaning**: Retry handler exhausted all retry attempts

**Check**:
```python
# Get last error details
try:
    result = handler.execute_with_retry(func)
except RetryError as e:
    print(f"Attempts: {e.attempts}")
    print(f"Last error: {e.last_error}")
    print(f"Error type: {type(e.last_error)}")
```

**Solutions**:
- Check if error is actually recoverable
- Increase max_retries if transient
- Fix underlying issue if non-recoverable

---

### "RateLimitError: Too many requests"

**Meaning**: Exceeded LLM API rate limit

**Solutions**:
```python
# Configure rate limiter
limiter = RateLimiter(requests_per_minute=50)  # Below provider limit

# Add to all API calls
with limiter:
    response = llm_client.call(...)
```

---

### "PromptValidationError: Missing 'Goal' section"

**Meaning**: Headless prompt file is invalid

**Solution**: Ensure prompt has all required sections:
```markdown
# Goal
[Required]

# Success Criteria
[Required - at least one item]

# Constraints
[Required - can be empty]

# Context
[Optional]
```

---

## Debug Mode

Enable verbose logging for troubleshooting:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Per-module logging
logging.getLogger("aurora_core.activation").setLevel(logging.DEBUG)
logging.getLogger("aurora_soar.headless").setLevel(logging.DEBUG)
```

Enable explain mode for activation debugging:

```python
result = engine.calculate_total(...)
explanation = engine.explain(result)
print(explanation)  # Detailed breakdown
```

---

## Getting Help

1. **Check logs**: `~/.aurora/logs/aurora.log`
2. **Run diagnostics**: `aur diagnose`
3. **Check metrics**: `aur metrics`
4. **Collect debug info**: `aur debug-info > debug.txt`
5. **File issue**: Include debug.txt in GitHub issue

---

**Document Version**: 1.0
**Last Updated**: December 23, 2025
**Related Tasks**: Task 8.9, Task 8.10
