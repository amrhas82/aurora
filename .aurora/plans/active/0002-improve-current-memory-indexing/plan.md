# Plan: Improve Memory Indexing System

**Plan ID:** 0002-improve-current-memory-indexing
**Status:** Draft
**Created:** 2026-01-12

## Executive Summary

This plan addresses improvements to Aurora's memory indexing system. After analyzing the current implementation, I've identified several areas for optimization across indexing performance, search quality, and storage efficiency.

## Current System Analysis

### Architecture Overview

The memory indexing system consists of:
1. **MemoryManager** (`aurora_cli/memory_manager.py`) - Orchestrates indexing and search
2. **SQLiteStore** (`aurora_core/store/sqlite.py`) - Persistent storage with ACT-R activation
3. **ParserRegistry** (`aurora_context_code/registry.py`) - Language parser management
4. **HybridRetriever** (`aurora_context_code/semantic/hybrid_retriever.py`) - Tri-hybrid search
5. **BM25Scorer** (`aurora_context_code/semantic/bm25_scorer.py`) - Keyword matching
6. **EmbeddingProvider** (`aurora_context_code/semantic/embedding_provider.py`) - ML embeddings

### Current Strengths
- Tri-hybrid scoring (BM25 30% + Semantic 40% + Activation 30%)
- Git-aware BLA (Base-Level Activation) calculation
- Batch embedding generation (32 chunks at a time)
- Code-aware tokenization (camelCase, snake_case, dot notation)
- Staged retrieval architecture (BM25 filter -> re-rank)

### Identified Bottlenecks & Limitations

1. **Indexing Performance**
   - BM25 index rebuilt from scratch on every search (no persistence)
   - Embeddings regenerated even for unchanged files
   - Git blame runs per-file (already optimized) but not cached across sessions
   - No incremental indexing - full reindex required for updates

2. **Search Quality**
   - Semantic threshold filtering disabled in tri-hybrid mode
   - Normalized scores can inflate low-quality results
   - No query expansion or synonym handling
   - Limited chunk types (code, kb) - no support for reasoning caching

3. **Storage Efficiency**
   - Embeddings stored as BLOBs (384-dim * 4 bytes = 1.5KB per chunk)
   - No embedding compression or quantization
   - Access history grows unbounded
   - No deduplication of similar chunks

4. **Language Support**
   - Only Python, JavaScript, TypeScript, Markdown supported
   - No Rust, Go, Java, C/C++ parsers
   - No cross-language relationship detection

## Improvement Categories

### Category A: Quick Wins (Low effort, High impact)

**A1. Persist BM25 Index**
- Save BM25 index to disk after indexing
- Load on search instead of rebuilding
- Expected speedup: ~200ms per search on large codebases

**A2. Incremental Indexing**
- Track file mtimes in metadata
- Only reindex files modified since last index
- Expected speedup: 10x for incremental updates

**A3. Configurable Scoring Weights**
- Expose tri-hybrid weights in config.json
- Allow per-project tuning without code changes

### Category B: Quality Improvements (Medium effort)

**B1. Query Expansion**
- Expand identifiers using same tokenization as BM25
- "getUserData" -> also search "get", "user", "data"
- Improves recall for partial matches

**B2. Semantic Threshold Tuning**
- Re-enable semantic threshold in tri-hybrid mode
- Apply as post-filter to remove noise
- Make threshold configurable

**B3. Chunk Relationship Graph**
- Track imports/calls between functions
- Use for spreading activation in search
- Improves context-aware retrieval

### Category C: Advanced Optimizations (Higher effort)

**C1. Embedding Compression**
- Use binary quantization (384 bits instead of 384 floats)
- 12x storage reduction with ~5% quality loss
- Alternative: PQ (Product Quantization) for 8x reduction

**C2. Access History Pruning**
- Limit history to last N accesses per chunk
- Or prune entries older than T days
- Prevents unbounded growth

**C3. Additional Language Parsers**
- Add Rust parser (tree-sitter-rust)
- Add Go parser (tree-sitter-go)
- Add Java parser (tree-sitter-java)

### Category D: Architecture Improvements (Significant effort)

**D1. Watch Mode for Indexing**
- Use filesystem watchers (watchdog)
- Auto-index on file changes
- Keep index always up-to-date

**D2. Distributed Index**
- Support for multi-workspace indexing
- Share indexes across related projects
- Central index server option

## Recommended Approach

Based on the user's question "how do I improve the current memory indexing", I recommend starting with **Category A** (Quick Wins) as they provide immediate value with minimal risk:

### Phase 1: Quick Wins (Recommended First)
1. **A2. Incremental Indexing** - Biggest impact on daily usage
2. **A1. Persist BM25 Index** - Improves search latency
3. **A3. Configurable Weights** - Enables experimentation

### Phase 2: Quality Improvements (If needed)
4. **B1. Query Expansion** - Improves recall
5. **B2. Semantic Threshold** - Reduces noise
6. **B3. Relationship Graph** - Better context

### Phase 3: Advanced (Based on scale)
7. **C1-C3** - Based on storage/performance needs

## Questions for Clarification

Before proceeding with detailed PRD and tasks, I need to understand:

1. **Primary Pain Point**: Is the main issue indexing speed, search quality, or storage size?
2. **Codebase Scale**: How many files/chunks are typically indexed? (affects optimization priorities)
3. **Language Needs**: Are additional language parsers needed (Rust, Go, Java)?
4. **ML Dependency**: Is the `[ml]` extra (sentence-transformers) always installed, or should improvements work without it?

## Next Steps

1. User confirms priority area (A, B, C, or D)
2. Create detailed PRD for selected improvements
3. Generate implementation tasks
4. Execute with validation at each step
