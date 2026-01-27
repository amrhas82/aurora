# SOAR Query Decomposition - Optimization Recommendations

## Executive Summary

Current token usage for decomposition: **8-10K tokens per query**
Optimization potential: **Reduce by 40-60% to 3-5K tokens**

---

## Critical Issues

### 1. **Duplicate Context Chunks** (High Priority)
**Problem**: 4 identical conversation log metadata blocks + 5 duplicate KB entries
**Impact**: Wastes ~1.5-2K tokens (20% of context)
**Location**: `packages/soar/src/aurora_soar/phases/decompose.py:197-294`

**Fix**:
```python
def _build_context_summary(context: dict[str, Any]) -> str:
    """Build actionable context summary with deduplication."""
    code_chunks = context.get("code_chunks", [])

    # OPTIMIZATION 1: Deduplicate by file_path + name + line_start
    seen = set()
    unique_chunks = []
    for chunk in code_chunks:
        key = (chunk.file_path, getattr(chunk, "name", ""), chunk.line_start)
        if key not in seen:
            seen.add(key)
            unique_chunks.append(chunk)

    # OPTIMIZATION 2: Filter out conversation logs for code queries
    # (conversation logs are useful for retrieval, not decomposition)
    code_only_chunks = [
        c for c in unique_chunks
        if not c.file_path.endswith(".md") or "SOAR Conversation Log" not in getattr(c, "content", "")
    ]

    # Use filtered chunks for context building
    code_chunks = code_only_chunks[:MAX_CHUNKS]
```

**Expected savings**: 1.5-2K tokens (20%)

---

### 2. **Excessive Code Detail** (Medium Priority)
**Problem**: Sends 7 full code blocks (up to 50 lines each = 350 lines)
**Impact**: ~2-3K tokens for code that LLM may not need in full
**Location**: `packages/soar/src/aurora_soar/phases/decompose.py:216-273`

**Fix A: Reduce TOP_N_WITH_CODE**
```python
# Current
TOP_N_WITH_CODE = 7  # Too many for decomposition
MAX_CHUNKS = 12

# Proposed
TOP_N_WITH_CODE = 3  # Show full code for top 3 only
MAX_CHUNKS = 10      # Reduce total chunks
```

**Fix B: Smarter Code Truncation**
```python
def _read_file_lines(file_path: str, line_start: int, line_end: int, max_lines: int = 50) -> str:
    """Read specific lines from a file."""
    # Current max_lines=50 is too high for decomposition
    # Decomposition needs signatures + context, not full implementations
    max_lines = 20  # Reduce to 20 lines for decomposition
    # ...
```

**Expected savings**: 1-2K tokens (15%)

---

### 3. **Verbose System Prompt** (Low Priority)
**Problem**: System prompt includes exhaustive instructions + agent mappings
**Impact**: ~2-3K tokens (cannot be cached across queries)
**Location**: `packages/reasoning/src/aurora_reasoning/prompts/decompose.py:120-204`

**Fix**: Create two variants
```python
def build_system_prompt(self, **kwargs: Any) -> str:
    """Build system prompt with optional verbosity."""
    verbosity = kwargs.get("verbosity", "standard")  # "minimal" | "standard" | "verbose"

    if verbosity == "minimal":
        # Short version for experienced models (Opus, GPT-4)
        # Omit examples of match_quality, reduce agent descriptions
        # Save ~500-800 tokens
        pass
```

**Expected savings**: 500-800 tokens (8%)

---

### 4. **Example Optimization** (Already Done)
**Status**: ✅ Already optimized in recent commit
- COMPLEX: 4 examples → 2 examples
- CRITICAL: 6 examples → 3 examples

**Note**: Lines 109-110 in examples.py explain this optimization:
```python
# Note: Reduced from 4/6 to 2/3 to avoid exceeding context limits
# when piping to CLI tools (claude, cursor, etc.)
```

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 hours)
1. **Deduplication**: Add chunk deduplication logic
2. **Filter conversation logs**: Exclude SOAR logs from decomposition context
3. **Reduce TOP_N_WITH_CODE**: 7 → 3

**Expected savings**: 3-4K tokens (35-40%)

### Phase 2: Structural Improvements (2-4 hours)
4. **Smarter code truncation**: Reduce max_lines from 50 → 20
5. **Context relevance scoring**: Prioritize chunks by query type
6. **Minimal system prompt variant**: For capable models

**Expected savings**: Additional 1-2K tokens (10-15%)

### Phase 3: Advanced Optimization (Future)
7. **Prompt caching**: Use Anthropic's prompt caching for system prompts
8. **Dynamic chunk selection**: Adjust TOP_N based on complexity
9. **Semantic deduplication**: Use embeddings to detect similar chunks

---

## Testing Strategy

### Regression Tests
```python
# tests/performance/test_decompose_token_usage.py

def test_decomposition_token_budget():
    """Verify decomposition stays within token budget."""
    result = decompose_query(...)

    # Measure prompt tokens
    prompt_tokens = count_tokens(result.prompt_used)

    # Target: <5K tokens for COMPLEX queries
    assert prompt_tokens < 5000, f"Prompt too long: {prompt_tokens} tokens"

def test_no_duplicate_chunks():
    """Verify no duplicate chunks in context summary."""
    context_summary = _build_context_summary(...)

    # Check for duplicate code blocks
    code_blocks = re.findall(r"```python\n(.*?)\n```", context_summary, re.DOTALL)
    assert len(code_blocks) == len(set(code_blocks)), "Found duplicate code blocks"
```

### Quality Validation
```bash
# Before and after optimization
aur goals "how can i improve aur mem search speed?" > before.json
# Apply optimizations
aur goals "how can i improve aur mem search speed?" > after.json

# Compare decomposition quality (should be similar)
python scripts/compare_decompositions.py before.json after.json
```

---

## Code Locations

| File | Lines | Description |
|------|-------|-------------|
| `packages/soar/src/aurora_soar/phases/decompose.py` | 197-294 | Context summary builder (needs deduplication) |
| `packages/soar/src/aurora_soar/phases/decompose.py` | 161-194 | File reading (reduce max_lines) |
| `packages/reasoning/src/aurora_reasoning/prompts/decompose.py` | 120-204 | System prompt (create minimal variant) |
| `packages/reasoning/src/aurora_reasoning/prompts/examples.py` | 109-116 | Example counts (already optimized) |

---

## Metrics to Track

| Metric | Baseline | Target | Improvement |
|--------|----------|--------|-------------|
| Avg prompt tokens | 8-10K | 3-5K | 40-60% |
| Duplicate chunks | 4-9 | 0 | 100% |
| Full code blocks | 7 | 3 | 57% |
| Context quality | 100% | 95%+ | -5% acceptable |
| Decomposition accuracy | 100% | 95%+ | -5% acceptable |

---

## Related Work

- Epic 2 (Lazy Loading): Reduced HybridRetriever creation time from 150ms → <50ms
- Examples optimization (commit 13d08dc): Reduced examples from 4/6 → 2/3
- This optimization focuses on **context quality** and **token efficiency**
