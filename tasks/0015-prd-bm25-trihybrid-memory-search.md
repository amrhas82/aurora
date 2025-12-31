# PRD-0015: Production-Grade Memory Search with BM25 Tri-Hybrid Retrieval

**Version**: 1.0
**Status**: Draft
**Created**: 2025-12-31
**Owner**: Product Manager
**Target Release**: Sprint 3 (8-10 hours implementation)

---

## 1. Introduction/Overview

### Problem Statement

The current Aurora memory search system (`aur mem search`) uses a semantic + activation dual-hybrid retrieval (60/40 weighting) that suffers from critical quality issues:

1. **Exact matches don't rank first**: Queries for specific identifiers like "SOAROrchestrator" can return partial matches ranked higher than exact matches due to min-max normalization conflicts
2. **No keyword precision**: Pure semantic search misses exact term matches that developers expect
3. **Limited chunk types**: Only code chunks are indexed; reasoning and knowledge chunks are stored but not searchable
4. **Poor discoverability**: Search results lack context about chunk types, git history, and score transparency

**Example of Current Failure**:
```
Query: "SOAROrchestrator"
Current Results:
  1. soar_patterns.py (partial match, high activation) - Score: 0.931
  2. orchestrator.py (EXACT match, low activation) - Score: 0.700
  ^^^^ WRONG ORDER
```

### Proposed Solution

Implement a **BM25 tri-hybrid retrieval system** with staged retrieval architecture:

- **Stage 1 (BM25 Filter)**: Code-aware keyword search returns top 100 candidates
- **Stage 2 (Semantic + Activation Re-rank)**: Dense retrieval + recency/frequency scoring within top-100
- **Tri-Hybrid Weights**: BM25 (30%) + Semantic (40%) + Activation (30%)

This approach follows industry-standard patterns (used by Elasticsearch, Pinecone Hybrid Search, Weaviate) and guarantees exact matches rank highly while preserving semantic understanding.

### High-Level Goals

1. **Search Quality**: Exact matches rank #1 in ≥90% of test queries
2. **Comprehensive Coverage**: Search across code, reasoning, and knowledge chunks
3. **Developer UX**: Transparent scoring, type filtering, git metadata in results
4. **Performance**: Simple queries <2s, complex queries <10s, BM25 build <30s (10K chunks)
5. **Maintainability**: Clear separation of concerns, testable components, documented algorithms

---

## 2. Goals

### Primary Goals

1. **Implement BM25 Tri-Hybrid Retrieval**
   - Code-aware tokenization (camelCase, snake_case, dot notation)
   - Staged retrieval architecture (BM25 filter → Semantic+Activation re-rank)
   - Configurable weights and parameters via `~/.aurora/config.yml`

2. **Enable Multi-Type Memory Search**
   - Index knowledge chunks from conversation logs (`~/.aurora/logs/conversations/**/*.md`)
   - Index reasoning chunks (already stored, add embeddings)
   - Support type filtering: `--type function,class,reasoning,knowledge`

3. **Enhance Search Result UX**
   - Display git metadata (commit count, last modified date)
   - Add `--show-scores` flag for score breakdown visualization
   - Implement `--legacy` flag for backward compatibility

4. **Ensure Production Readiness**
   - BM25 index caching with auto-detection and manual rebuild
   - Graceful error handling for missing logs, corrupted indexes, embedding failures
   - Comprehensive test suite (20 manual QA queries + 90% exact match rate)

### Secondary Goals

1. Allow tuning of BM25/hybrid parameters without code changes
2. Provide clear migration path for existing users (opt-out new format)
3. Document scoring algorithms and retrieval stages for future maintainers

---

## 3. User Stories

### US-1: Developer Searching for Exact Code Identifiers
**As a** developer using Aurora memory search
**I want** exact identifier matches (class names, function names) to rank first
**So that** I can quickly locate specific code elements without scrolling through semantic matches

**Acceptance Criteria**:
- Given query "SOAROrchestrator", chunk with exact class name ranks #1
- Given query "authenticate_user", chunk with exact function name ranks #1
- BM25 score visibly boosts exact matches in `--show-scores` output

---

### US-2: AI Agent Searching Across All Memory Types
**As an** AI agent orchestrating tasks
**I want** to search across code, reasoning patterns, and knowledge from past conversations
**So that** I can retrieve relevant context regardless of chunk type

**Acceptance Criteria**:
- `aur mem search "authentication flow"` returns results from:
  - Code chunks (auth functions)
  - Reasoning chunks (cached auth patterns, success_score ≥ 0.5)
  - Knowledge chunks (conversation logs about auth implementation)
- `--type` flag filters results to specific chunk types
- Results table shows chunk type in dedicated column

---

### US-3: Developer Understanding Search Result Relevance
**As a** developer reviewing search results
**I want** to see why each result was ranked where it is
**So that** I can trust the search system and debug poor results

**Acceptance Criteria**:
- `--show-scores` flag displays:
  - BM25 score with explanation (e.g., "exact keyword match on 'authenticate'")
  - Semantic score (conceptual relevance)
  - Activation score (frequency, recency, commit history)
  - Final weighted score
- Visual box-drawing format for readability
- Each score component normalized to [0,1] scale

---

### US-4: Developer Tracking Code Evolution
**As a** developer reviewing search results
**I want** to see git metadata for each code chunk
**So that** I can assess code stability and maturity

**Acceptance Criteria**:
- Search results table includes:
  - "Commits" column (total commit count affecting lines)
  - "Last Modified" column (relative time: "2 days ago")
- For untracked files, display "- (untracked)"
- For git failures, display "- (unavailable)"
- `--legacy` flag hides these columns for backward compatibility

---

### US-5: Developer Searching with Type Constraints
**As a** developer looking for specific code constructs
**I want** to filter search results by chunk type
**So that** I can focus on relevant code elements (e.g., only classes)

**Acceptance Criteria**:
- `--type function` returns only FunctionChunk and MethodChunk
- `--type class` returns only ClassChunk
- `--type reasoning` returns only ReasoningChunk
- `--type knowledge` returns only KnowledgeChunk
- `--type function,class` returns union of both types (exact matches only, no related types)
- Invalid types produce clear error message

---

### US-6: System Maintaining Fresh BM25 Index
**As the** Aurora system
**I want** to automatically detect stale BM25 indexes
**So that** search results reflect newly indexed chunks without manual intervention

**Acceptance Criteria**:
- On first search after `aur mem index`, BM25 index auto-rebuilds if chunk count differs
- Rebuild displays progress: "Rebuilding BM25 index (1234 chunks)..."
- Manual rebuild available: `aur mem rebuild-bm25`
- Corrupted index triggers warning + auto-rebuild
- BM25 index stored at `~/.aurora/indexes/bm25_index.pkl`

---

### US-7: System Handling Missing/Invalid Data Gracefully
**As the** Aurora system
**I want** to continue operating when optional data is missing
**So that** users get partial results instead of hard failures

**Acceptance Criteria**:
- No conversation logs exist → Warning "No knowledge chunks found" + continue with code/reasoning
- Embedding generation fails for 1 chunk → Skip chunk + warning + continue indexing
- Git blame fails for 1 file → Display "- (unavailable)" + continue search
- BM25 index corrupted → Warning "Rebuilding corrupted BM25 index" + auto-rebuild

---

### US-8: Developer Configuring Search Behavior
**As a** developer tuning search for my codebase
**I want** to adjust BM25 and hybrid retrieval parameters
**So that** I can optimize search quality for my corpus characteristics

**Acceptance Criteria**:
- `~/.aurora/config.yml` supports:
  ```yaml
  search:
    bm25:
      k1: 1.5          # Term frequency saturation (default 1.5)
      b: 0.75          # Length normalization (default 0.75)
    hybrid:
      stage1_top_k: 100         # BM25 candidates (default 100)
      stage2_weights:
        semantic: 0.5            # Semantic weight (default 0.5)
        activation: 0.5          # Activation weight (default 0.5)
  ```
- Invalid values (e.g., negative k1) produce validation errors
- Missing config falls back to hardcoded defaults
- Config changes take effect on next search (no restart required)

---

## 4. Functional Requirements

### FR-1: BM25 Core Implementation

**FR-1.1**: The system MUST implement a BM25Scorer class in `packages/context-code/src/aurora_context_code/semantic/bm25_scorer.py` with methods:
- `tokenize(text: str) -> List[str]`: Code-aware tokenization supporting:
  - camelCase splitting: "getUserData" → ["get", "User", "Data"]
  - snake_case splitting: "user_manager" → ["user", "manager"]
  - Dot notation splitting: "auth.oauth.client" → ["auth", "oauth", "client"]
  - Preservation of acronyms: "HTTPRequest" → ["HTTP", "Request"]
- `build_index(chunks: List[BaseChunk]) -> None`: Compute IDF scores and document statistics
- `score(query: str, chunk: BaseChunk) -> float`: Return BM25 score in range [0, ∞)

**FR-1.2**: The BM25 algorithm MUST use Okapi BM25 formula:
```
score(Q, D) = Σ IDF(qi) · (f(qi, D) · (k1 + 1)) / (f(qi, D) + k1 · (1 - b + b · |D| / avgdl))
```
Where:
- `IDF(qi) = log((N - n(qi) + 0.5) / (n(qi) + 0.5 + 1))`
- `f(qi, D)` = frequency of term qi in document D
- `|D|` = length of document D in tokens
- `avgdl` = average document length in corpus
- `k1` = term frequency saturation (default 1.5, configurable)
- `b` = length normalization (default 0.75, configurable)

**FR-1.3**: The system MUST persist BM25 index to `~/.aurora/indexes/bm25_index.pkl` containing:
- IDF scores for all terms in corpus
- Document length statistics (per-chunk token count, average length)
- Corpus metadata (total chunks, index creation timestamp)

**FR-1.4**: The system MUST validate BM25 index on load:
- Check file format version compatibility
- Verify pickle integrity (catch `pickle.UnpicklingError`)
- Compare indexed chunk count vs. current chunk count
- If validation fails: warn user + trigger rebuild

---

### FR-2: Staged Retrieval Architecture

**FR-2.1**: The system MUST implement HybridRetriever in `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` with two-stage retrieval:

**Stage 1 (BM25 Filter)**:
- Compute BM25 scores for ALL chunks in corpus
- Sort by BM25 score descending
- Select top K candidates (K = `stage1_top_k` from config, default 100)
- If corpus < K chunks, use all chunks

**Stage 2 (Semantic + Activation Re-rank)**:
- For each of K candidates:
  - Compute semantic similarity score (cosine similarity of embeddings)
  - Compute activation score (from ACT-R activation calculation)
- Normalize semantic and activation scores to [0, 1] within K candidates using min-max
- Compute final score: `semantic_weight × semantic + activation_weight × activation`
- Sort by final score descending
- Return top N results (N = user-specified limit, default 10)

**FR-2.2**: The system MUST NOT normalize BM25 scores (preserve raw scores for filtering).

**FR-2.3**: The system MUST apply Stage 2 normalization ONLY within Stage 1 candidates to prevent cross-stage score conflicts.

---

### FR-3: Knowledge Chunk Implementation

**FR-3.1**: The system MUST implement KnowledgeParser in `packages/context-code/src/aurora_context_code/parsers/knowledge_parser.py` to extract chunks from conversation logs.

**FR-3.2**: The system MUST scan `~/.aurora/logs/conversations/YYYY/MM/*.md` files recursively for all years/months.

**FR-3.3**: The system MUST parse conversation logs with structure:
```markdown
# Conversation: <topic>
Date: YYYY-MM-DD
Query: <user query>

## Phase 1: Assessment
<content>

## Phase 2: Retrieval
<content>

...

## Phase 9: Response
<content>
```

**FR-3.4**: For each Phase section, the system MUST create a KnowledgeChunk with:
- `chunk_id`: `"conv-{filename}-phase{N}"` (e.g., "conv-auth-impl-2025-12-15-phase3")
- `content`: Full phase section text (Markdown preserved)
- `metadata`:
  - `source_file`: Absolute path to conversation log
  - `phase_number`: 1-9
  - `phase_name`: e.g., "Assessment", "Retrieval"
  - `conversation_date`: Parsed from log filename or Date field
  - `query`: Extracted from log header

**FR-3.5**: The system MUST generate embeddings for each KnowledgeChunk's content and store in ACT-R memory.

**FR-3.6**: If no conversation logs exist, the system MUST display warning: `"Warning: No conversation logs found in ~/.aurora/logs/conversations/"` and continue indexing other chunk types.

---

### FR-4: Reasoning Chunk Indexing

**FR-4.1**: The system MUST index existing ReasoningChunks stored in ACT-R memory with `success_score ≥ 0.5`.

**FR-4.2**: The system MUST generate embeddings for ReasoningChunk content (pattern description + context) if not already present.

**FR-4.3**: ReasoningChunk MUST include metadata:
- `pattern_type`: e.g., "decomposition", "verification"
- `success_score`: Float [0.0, 1.0]
- `usage_count`: Number of times pattern was successfully applied
- `created_at`: Timestamp when pattern was stored

**FR-4.4**: The system MUST NOT index failed reasoning attempts (`success_score < 0.5`).

---

### FR-5: Enhanced Search Results Display

**FR-5.1**: The system MUST display search results in tabular format with columns:
```
File            | Type     | Name              | Lines  | Score | Commits | Last Modified
auth_manager.py | function | authenticate_user | 45-67  | 0.856 | 23      | 2 days ago
oauth-impl.md   | know     | OAuth Setup       | -      | 0.654 | -       | 2025-12-15
auth-pattern    | reas     | Auth Flow         | -      | 0.621 | -       | 2025-12-20
```

**FR-5.2**: The "Type" column MUST use abbreviations:
- `function`: FunctionChunk
- `method`: MethodChunk
- `class`: ClassChunk
- `code`: Generic CodeChunk
- `reas`: ReasoningChunk
- `know`: KnowledgeChunk

**FR-5.3**: The "Commits" column MUST display:
- Integer count of commits affecting chunk lines (from `git blame -L`)
- `"-"` for non-code chunks (reasoning, knowledge)
- `"- (untracked)"` for files not in git
- `"- (unavailable)"` if `git blame` fails

**FR-5.4**: The "Last Modified" column MUST display:
- Relative time (e.g., "2 days ago", "3 weeks ago") for code chunks
- Absolute date (YYYY-MM-DD) for knowledge chunks (from conversation date)
- Absolute date (YYYY-MM-DD) for reasoning chunks (from `created_at`)
- `"- (untracked)"` for files not in git
- `"- (unavailable)"` if git fails

**FR-5.5**: The `--legacy` flag MUST revert to original output format:
```
File            | Type     | Name              | Lines  | Score
auth_manager.py | function | authenticate_user | 45-67  | 0.856
```
(No Commits or Last Modified columns)

---

### FR-6: Score Transparency

**FR-6.1**: The `--show-scores` flag MUST display detailed score breakdown using box-drawing characters:
```
┌─ auth_manager.py | function | authenticate_user (Lines 45-67) ─────────────┐
│ Final Score: 0.856                                                          │
│   ├─ BM25:       0.950 ⭐ (exact keyword match on "authenticate")          │
│   ├─ Semantic:   0.820    (high conceptual relevance)                      │
│   └─ Activation: 0.650    (accessed 3x, 23 commits, last used 2 days ago)  │
│ Git: 23 commits, last modified 2 days ago                                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

**FR-6.2**: BM25 explanations MUST indicate:
- `"exact keyword match on <term>"` if query term found verbatim in chunk
- `"strong term overlap"` if ≥50% query terms present
- `"partial match"` if <50% query terms present

**FR-6.3**: Semantic explanations MUST use thresholds:
- ≥0.9: "very high conceptual relevance"
- 0.8-0.89: "high conceptual relevance"
- 0.7-0.79: "moderate conceptual relevance"
- <0.7: "low conceptual relevance"

**FR-6.4**: Activation explanations MUST include:
- Access count (e.g., "accessed 3x")
- Git commit count if available (e.g., "23 commits")
- Recency (e.g., "last used 2 days ago")

**FR-6.5**: The `--show-scores` output MUST work with `--legacy` flag (show scores in legacy table format).

---

### FR-7: Type Filtering

**FR-7.1**: The `--type` flag MUST accept comma-separated chunk types:
- Valid values: `function`, `method`, `class`, `code`, `reasoning`, `knowledge`
- Case-insensitive matching

**FR-7.2**: The system MUST filter results to ONLY exact type matches:
- `--type function`: Return ONLY FunctionChunk
- `--type function,class`: Return FunctionChunk OR ClassChunk
- NO related types (e.g., `--type class` excludes methods inside classes)

**FR-7.3**: Invalid types MUST produce error:
```
Error: Invalid chunk type 'functon'. Valid types: function, method, class, code, reasoning, knowledge
```

**FR-7.4**: The system MUST apply type filtering AFTER Stage 2 re-ranking to avoid skewing relevance scores.

---

### FR-8: BM25 Index Management

**FR-8.1**: The system MUST auto-detect stale BM25 index on first search by comparing:
- Indexed chunk count (from `bm25_index.pkl` metadata)
- Current chunk count (from ACT-R memory)

**FR-8.2**: If chunk counts differ, the system MUST:
1. Display: `"Rebuilding BM25 index (detected X new chunks)..."`
2. Rebuild index with progress updates every 1000 chunks
3. Save to `~/.aurora/indexes/bm25_index.pkl`
4. Proceed with search

**FR-8.3**: The `aur mem rebuild-bm25` command MUST:
- Force rebuild regardless of staleness detection
- Display progress: `"Rebuilding BM25 index for X chunks..."`
- Validate rebuild success (chunk count matches)

**FR-8.4**: If BM25 index is corrupted (`pickle.UnpicklingError`), the system MUST:
1. Display: `"Warning: BM25 index corrupted, rebuilding..."`
2. Delete corrupted file
3. Rebuild fresh index
4. Proceed with search

**FR-8.5**: If BM25 index directory does not exist, the system MUST create `~/.aurora/indexes/` recursively.

---

### FR-9: Configuration Management

**FR-9.1**: The system MUST read search configuration from `~/.aurora/config.yml`:
```yaml
search:
  bm25:
    k1: 1.5          # Term frequency saturation (default 1.5)
    b: 0.75          # Length normalization (default 0.75)
  hybrid:
    stage1_top_k: 100         # BM25 candidates (default 100)
    stage2_weights:
      semantic: 0.5            # Semantic weight in Stage 2 (default 0.5)
      activation: 0.5          # Activation weight in Stage 2 (default 0.5)
```

**FR-9.2**: The system MUST validate config values:
- `k1`: Float ≥ 0.0 (typical range 1.2-2.0)
- `b`: Float in [0.0, 1.0]
- `stage1_top_k`: Integer ≥ 10
- `stage2_weights.semantic`: Float in [0.0, 1.0]
- `stage2_weights.activation`: Float in [0.0, 1.0]
- `stage2_weights.semantic + activation` MUST equal 1.0

**FR-9.3**: Invalid config values MUST produce error:
```
Error: Invalid config in ~/.aurora/config.yml:
  - search.bm25.k1: Must be ≥ 0.0 (got -1.5)
  - search.hybrid.stage2_weights: Must sum to 1.0 (got 0.7)
```

**FR-9.4**: If `~/.aurora/config.yml` does not exist, the system MUST use hardcoded defaults (no error).

**FR-9.5**: Config changes MUST take effect immediately on next search (no process restart required).

---

### FR-10: Error Handling

**FR-10.1**: When no conversation logs exist (`~/.aurora/logs/conversations/` empty or missing):
- Display: `"Warning: No conversation logs found in ~/.aurora/logs/conversations/"`
- Continue indexing code and reasoning chunks
- Search proceeds normally (no knowledge chunks in results)

**FR-10.2**: When embedding generation fails for a chunk during indexing:
- Display: `"Warning: Failed to generate embedding for chunk {chunk_id}: {error_message}"`
- Skip the failed chunk
- Continue indexing remaining chunks
- Final summary: `"Indexed X/Y chunks (Y-X failed)"`

**FR-10.3**: When `git blame` fails for a file during search display:
- Display `"- (unavailable)"` in Commits and Last Modified columns for that result
- Log warning to `~/.aurora/logs/aurora.log`: `"Git blame failed for {file_path}: {error}"`
- Continue displaying remaining results

**FR-10.4**: When BM25 index is corrupted:
- Display: `"Warning: BM25 index corrupted, rebuilding..."`
- Delete corrupted file at `~/.aurora/indexes/bm25_index.pkl`
- Rebuild fresh index
- Proceed with search
- Log error to `~/.aurora/logs/aurora.log`

**FR-10.5**: When Stage 1 returns zero candidates (no BM25 matches):
- Fall back to pure semantic search (skip Stage 2, use all chunks)
- Display: `"Note: No keyword matches found, falling back to semantic search"`
- Proceed with top N semantic results

---

### FR-11: Indexing Summary Display

**FR-11.1**: The `aur mem index` command MUST display a summary showing chunk counts by type:
```
Indexing complete!

Summary:
  Files scanned: 103
  Code chunks: 456
  Reasoning chunks: 23
  Knowledge chunks: 18
  Total chunks: 497

  Errors: 0
  Warnings: 2
```

**FR-11.2**: The summary MUST include separate counts for:
- **Code chunks**: Function, method, class chunks extracted from code files
- **Reasoning chunks**: Patterns from ACT-R store (success_score ≥ 0.5)
- **Knowledge chunks**: Chunks extracted from conversation logs

**FR-11.3**: The "Warnings" count MUST include:
- Parse errors/warnings from code files
- Missing conversation logs (if `~/.aurora/logs/conversations/` doesn't exist)
- Embedding generation failures (skipped chunks)

**FR-11.4**: The "Errors" count MUST include:
- Fatal failures that prevented indexing completion
- Invalid configuration errors
- Database connection errors

**FR-11.5**: After indexing, the summary MUST display BM25 index status:
```
BM25 index: Built (497 chunks indexed, saved to ~/.aurora/indexes/bm25_index.pkl)
```

**FR-11.6**: If knowledge chunks are not found, display informational note:
```
Note: No conversation logs found. Run SOAR queries to generate knowledge chunks.
```

---

## 5. Non-Goals (Out of Scope)

### Explicitly Excluded Features

1. **Multi-language code parsing**: Only Python code chunks are parsed via tree-sitter. Other languages (JavaScript, Go, etc.) are out of scope.

2. **Full-text search in file contents**: BM25 operates on chunk-level content only. Searching arbitrary text across entire files (grep-style) is not supported.

3. **Fuzzy matching / Typo tolerance**: Queries must match tokens exactly. "authenticat" will not match "authenticate". Implementing fuzzy matching (Levenshtein distance, phonetic matching) is out of scope.

4. **Real-time index updates**: BM25 index is rebuilt on-demand (auto-detection or manual). Live incremental updates during `aur mem index` are not supported.

5. **Query syntax / Boolean operators**: No support for `"exact phrase"`, `AND`, `OR`, `NOT`, wildcards, or regex in queries. All queries are treated as bag-of-words.

6. **Result clustering / Grouping**: Results are a flat ranked list. Grouping by file, type, or topic is not implemented.

7. **Personalized ranking**: No user-specific ranking adjustments based on past clicks or preferences. All users see identical results for the same query.

8. **Distributed search**: Single-node architecture only. Searching across multiple Aurora instances or sharded indexes is out of scope.

9. **Search analytics / Telemetry**: No tracking of query logs, click-through rates, or search performance metrics beyond manual QA testing.

10. **Vector database integration**: Embeddings are stored in ACT-R memory (SQLite). Integrating external vector databases (Pinecone, Weaviate, Qdrant) is not planned.

---

## 6. Design Considerations

### 6.1 Tokenization Strategy

**Code-Aware Splitting**:
- Use regex patterns to split identifiers:
  - `camelCase`: `"getUserData"` → `["get", "User", "Data"]`
  - `snake_case`: `"user_manager"` → `["user", "manager"]`
  - `dot.notation`: `"auth.oauth"` → `["auth", "oauth"]`
- Preserve acronyms: `"HTTPSConnection"` → `["HTTPS", "Connection"]` (detect consecutive uppercase)

**Stop Words**: Do NOT remove common words (e.g., "the", "a") as they may be significant in code contexts (e.g., method name `"get_the_user"`).

**Stemming**: Do NOT apply stemming (e.g., "running" → "run") as code identifiers are exact and stemming breaks matches.

### 6.2 Score Normalization Approach

**Stage 1 (BM25)**:
- Use raw BM25 scores for filtering (no normalization)
- BM25 scores are unbounded [0, ∞), which is acceptable for ranking

**Stage 2 (Semantic + Activation)**:
- Apply min-max normalization ONLY within Stage 1 candidates (top-100)
- Formula: `normalized = (score - min_score) / (max_score - min_score + ε)`
- ε = 1e-8 to prevent division by zero
- This prevents cross-stage normalization conflicts

### 6.3 Visual Design (Box-Drawing)

Use Unicode box-drawing characters for `--show-scores`:
```
┌─ <title> ─┐
│ <content> │
└───────────┘
```

**Character Set**:
- Top-left: `┌` (U+250C)
- Top-right: `┐` (U+2510)
- Bottom-left: `└` (U+2514)
- Bottom-right: `┘` (U+2518)
- Horizontal: `─` (U+2500)
- Vertical: `│` (U+2502)
- Tree branch: `├─` (U+251C + U+2500)
- Tree end: `└─` (U+2514 + U+2500)

**Width**: Auto-size to terminal width (default 80 chars, max 120 chars).

### 6.4 Git Metadata Caching

**Avoid Repeated `git blame` Calls**:
- Store commit count and last modified date in chunk metadata during indexing
- Refresh git metadata only during `aur mem index` runs (not during search)
- If metadata is stale (>7 days old), display warning: `"(metadata may be stale)"`

### 6.5 Conversation Log Format

**Expected Structure**:
```markdown
# Conversation: Authentication Implementation
Date: 2025-12-15
Query: How do I implement OAuth2 authentication?

## Phase 1: Assessment
Aurora assessed the query complexity as HIGH due to security requirements...

## Phase 2: Retrieval
Retrieved 12 relevant chunks from codebase:
- auth_manager.py (lines 45-67): authenticate_user()
...

## Phase 9: Response
Final response synthesized with confidence score 0.89...
```

**Fallback Parsing**:
- If phase headers are missing, treat entire log as single KnowledgeChunk
- Extract metadata from filename: `auth-oauth-impl-2025-12-15.md` → topic="auth-oauth-impl", date=2025-12-15

---

## 7. Technical Considerations

### 7.1 Dependencies

**New Dependencies**:
- None (use existing libraries)

**Existing Dependencies Used**:
- `rank_bm25`: Consider using for reference implementation (MIT license) - OPTIONAL
- `scikit-learn`: Already in project, use for cosine similarity if needed
- `tree-sitter`: Already in project for code parsing

**Decision**: Implement BM25 from scratch to:
1. Control tokenization logic (code-aware splitting)
2. Avoid external dependency for core feature
3. Optimize for Aurora's chunk structure

### 7.2 Performance Optimization

**BM25 Index Structure**:
```python
{
  "version": "1.0",
  "created_at": "2025-12-31T10:30:00Z",
  "corpus_stats": {
    "total_chunks": 1234,
    "avg_doc_length": 150.5
  },
  "idf_scores": {
    "authenticate": 2.35,
    "user": 1.82,
    ...
  },
  "doc_lengths": {
    "chunk-001": 145,
    "chunk-002": 203,
    ...
  }
}
```

**Caching Strategy**:
- Cache BM25 scores for frequent queries? NO - computation is fast (<50ms for 10K chunks)
- Cache embeddings? YES - already implemented in ACT-R storage

**Expected Performance**:
- BM25 scoring: O(n × m) where n = chunks, m = avg query terms
- For 10K chunks, 5-term query: ~10K × 5 = 50K operations ≈ 50ms
- Stage 2 semantic search: O(k × d) where k = stage1_top_k (100), d = embedding dim (1536)
- Total expected: <500ms for simple queries, <2s for complex

### 7.3 Storage Requirements

**BM25 Index Size Estimate**:
- IDF scores: ~50K unique terms × 8 bytes (float64) = 400 KB
- Doc lengths: 10K chunks × 8 bytes = 80 KB
- Metadata: ~10 KB
- Total: ~500 KB for 10K chunks

**Conversation Logs**:
- Average log size: 10 KB (10 phases × 1 KB each)
- 100 conversations = 1 MB
- 1000 conversations = 10 MB
- Acceptable storage overhead

### 7.4 Integration Points

**Modified Files**:
1. `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
   - Add `bm25_scorer` attribute
   - Implement staged retrieval in `retrieve()` method
   - Add `_load_bm25_index()` and `_save_bm25_index()` methods

2. `packages/cli/src/aurora_cli/commands/memory.py`
   - Add `--type`, `--show-scores`, `--legacy` flags to `search` subcommand
   - Modify `_display_results()` to show git metadata
   - Add `rebuild-bm25` subcommand

3. `packages/context-code/src/aurora_context_code/memory_manager.py`
   - Add `index_knowledge_chunks()` method
   - Add `index_reasoning_chunks()` method
   - Modify `index_directory()` to call both methods

4. `packages/core/src/aurora_core/config.py`
   - Add `SearchConfig` dataclass
   - Load from `~/.aurora/config.yml`

**New Files**:
1. `packages/context-code/src/aurora_context_code/semantic/bm25_scorer.py`
2. `packages/context-code/src/aurora_context_code/parsers/knowledge_parser.py`
3. `packages/context-code/tests/test_bm25_scorer.py`
4. `packages/context-code/tests/test_knowledge_parser.py`

### 7.5 Backward Compatibility Strategy

**Default Behavior Change**:
- New format becomes default (with git columns)
- Users who want old format use `--legacy` flag

**Migration Communication**:
- Add note to CHANGELOG.md: "Breaking: `aur mem search` output format changed. Use `--legacy` for old format."
- Display one-time message on first search after upgrade:
  ```
  Note: Search output format has changed. Use --legacy for old format.
  See CHANGELOG.md for details. (This message won't show again)
  ```
- Store flag in `~/.aurora/config.yml`:
  ```yaml
  ui:
    shown_search_format_notice: true
  ```

---

## 8. Success Metrics

### 8.1 Quantitative Metrics

**Primary Metric: Exact Match Ranking**
- **Goal**: Exact identifier matches rank #1 in ≥90% of test queries
- **Measurement**:
  - Test suite of 20 queries with known ground truth
  - Query examples:
    - "SOAROrchestrator" → must rank `orchestrator.py:SOAROrchestrator` #1
    - "authenticate_user" → must rank `auth_manager.py:authenticate_user()` #1
    - "BM25Scorer" → must rank `bm25_scorer.py:BM25Scorer` #1
  - Pass criteria: ≥18/20 queries (90%) have exact match as top result

**Secondary Metric: Performance**
- **Goal**: Simple query <2s, complex query <10s
- **Measurement**:
  - Simple query: 1-2 word query (e.g., "authentication")
  - Complex query: 5+ word query (e.g., "how to implement oauth2 authentication flow")
  - Measure end-to-end latency from CLI invocation to results display
  - Test with 10K chunks corpus
  - Pass criteria: 95th percentile meets targets

**Tertiary Metric: BM25 Index Build Time**
- **Goal**: <30s for 10K chunks
- **Measurement**: Time from `aur mem index` start to BM25 index save
- Pass criteria: Median time <30s over 5 runs

### 8.2 Qualitative Metrics

**Manual QA Test Suite**
- **Goal**: 20 diverse test queries covering:
  - Exact identifier matches (5 queries)
  - Semantic concept searches (5 queries)
  - Multi-type searches (code + reasoning + knowledge) (5 queries)
  - Edge cases (no results, ambiguous terms, acronyms) (5 queries)
- **Pass Criteria**: All 20 queries return "reasonable" results as judged by developer
- **Documentation**: Each query documented in `tests/qa/search_quality_tests.md` with:
  - Query text
  - Expected top-3 results
  - Actual top-3 results
  - Pass/Fail judgment + rationale

**User Acceptance**
- **Goal**: Developers prefer new search over old search
- **Measurement**: Informal poll of 3-5 Aurora users after 1 week of use
- **Pass Criteria**: ≥4/5 users report "search quality improved" or "search is now usable"

---

## 9. Open Questions

### Q1: Should we support phrase search (e.g., `"exact phrase"` in quotes)?
**Context**: BM25 is bag-of-words by default. Adding phrase search requires position tracking.
**Impact**: Moderate complexity increase (+2 hours implementation, +10% index size).
**Decision**: Deferred to future iteration. Track as enhancement request.

### Q2: Should Stage 2 weights be auto-tuned based on corpus characteristics?
**Context**: Different codebases may benefit from different semantic/activation weights.
**Impact**: Significant complexity (requires benchmark suite, optimization algorithm).
**Decision**: Use fixed defaults (50/50), allow manual tuning via config. Auto-tuning is future work.

### Q3: How to handle very large conversation logs (>100 MB)?
**Context**: Knowledge chunks grow unbounded over time.
**Impact**: May exceed memory limits for embedding generation.
**Mitigation Options**:
1. Implement pagination (parse logs in batches)
2. Set max log age (only index logs from last 6 months)
3. Compress old logs (reduce storage but skip indexing)
**Decision**: Implement option 1 (pagination) in initial release. Revisit retention policy if logs exceed 1 GB.

### Q4: Should we expose tri-hybrid weights (BM25/Semantic/Activation) to users?
**Context**: Current design uses fixed 30/40/30 weights. Some users may want to tune.
**Impact**: Adds config complexity, potential for poor user choices breaking search.
**Decision**: Keep tri-hybrid weights hardcoded in v1. Only expose Stage 2 weights (semantic/activation). Revisit if users request tri-hybrid tuning.

### Q5: How to handle chunks with no embeddings (e.g., embedding service down during indexing)?
**Context**: Currently, failed embedding skips chunk entirely.
**Impact**: Chunks are invisible to search, even for keyword (BM25) matches.
**Alternative**: Store chunks without embeddings, allow BM25-only search for them.
**Decision**: Implement alternative (BM25-only fallback for chunks missing embeddings). Display warning in `--show-scores`: "No semantic score available (embedding missing)".

---

## 10. Implementation Plan (High-Level)

### Phase 1: BM25 Core (3 hours)
1. Implement `BM25Scorer` class with code-aware tokenization
2. Implement Okapi BM25 algorithm
3. Add index persistence (save/load from pickle)
4. Unit tests (10 test cases)

### Phase 2: Staged Retrieval (2 hours)
1. Refactor `HybridRetriever` for two-stage architecture
2. Integrate BM25Scorer into Stage 1
3. Update Stage 2 normalization (within candidates only)
4. Integration tests (5 test cases)

### Phase 3: Knowledge Chunks (2 hours)
1. Implement `KnowledgeParser` for conversation logs
2. Add `index_knowledge_chunks()` to MemoryManager
3. Handle missing logs gracefully
4. Unit tests (8 test cases)

### Phase 4: Enhanced Display (1 hour)
1. Add git metadata columns to results table
2. Implement `--legacy` flag
3. Handle git edge cases (untracked, unavailable)
4. Visual regression tests

### Phase 5: Score Transparency (1 hour)
1. Implement `--show-scores` with box-drawing
2. Add score explanations (BM25/semantic/activation)
3. Format tests

### Phase 6: Type Filtering (30 minutes)
1. Add `--type` flag to CLI
2. Implement exact type matching in retriever
3. Add validation + error messages
4. Unit tests (6 test cases)

### Phase 7: Reasoning Chunks (30 minutes)
1. Add `index_reasoning_chunks()` to MemoryManager
2. Generate embeddings for existing ReasoningChunks
3. Integration tests

### Phase 8: Configuration (1 hour)
1. Add `SearchConfig` to config.py
2. Load from `~/.aurora/config.yml`
3. Implement validation
4. Config tests (5 test cases)

### Phase 9: Testing & QA (2 hours)
1. Run 20-query manual QA suite
2. Fix any failures discovered
3. Performance benchmarks (verify <2s/<10s targets)
4. Update documentation

---

## 11. Risks & Mitigations

### Risk 1: BM25 Scoring Too Aggressive (Exact Matches Dominate)
**Likelihood**: Medium
**Impact**: High (semantic matches invisible, poor recall)
**Mitigation**:
- Use conservative tri-hybrid weights (BM25 30%, not 50%)
- Implement Stage 1 top-k=100 (wide enough net for semantic re-ranking)
- Add `--show-scores` for debugging
- Allow config tuning if users report issues

### Risk 2: Performance Degrades with Large Corpora (>10K Chunks)
**Likelihood**: Medium
**Impact**: High (violates <2s target)
**Mitigation**:
- Profile BM25 scoring with 50K chunks in test environment
- Optimize hot paths (tokenization, IDF lookup)
- If needed, implement inverted index for BM25 (Stage 1 optimization)
- Document scaling limits in README

### Risk 3: Conversation Log Format Changes Break Parsing
**Likelihood**: Low
**Impact**: Medium (knowledge chunks fail to index)
**Mitigation**:
- Implement fallback parsing (treat entire log as single chunk if phases not found)
- Add format version detection (check for "Phase 1:" header)
- Log parsing failures with file paths for debugging
- Ensure indexing continues for other chunk types

### Risk 4: Users Confused by New Output Format
**Likelihood**: Medium
**Impact**: Low (usability issue, not functional)
**Mitigation**:
- Provide `--legacy` flag for easy revert
- Show one-time migration notice on first use
- Document format changes in CHANGELOG.md
- Include example output in CLI help (`aur mem search --help`)

### Risk 5: Git Metadata Retrieval Slows Down Search
**Likelihood**: Low
**Impact**: Medium (violates <2s target)
**Mitigation**:
- Cache git metadata in chunk storage during indexing (not during search)
- Only refresh metadata on `aur mem index` runs
- If git is slow, display results immediately + append git columns asynchronously
- Add `--no-git` flag to skip git columns entirely

---

## 12. Dependencies

### Internal Dependencies
- `aurora-core`: Config management, chunk base classes
- `aurora-context-code`: Existing semantic retriever, tree-sitter parsing
- `aurora-cli`: Command infrastructure, result display

### External Dependencies (No New Ones)
- Python 3.9+ (existing requirement)
- NumPy (existing, for vector operations)
- PyYAML (existing, for config parsing)

### Optional Dependencies
- `rank_bm25` library (reference implementation, not required)

---

## 13. Testing Strategy

### Test-Driven Development Approach

This feature MUST be implemented using TDD with three test layers:
1. **Shell Tests (20)** - Acceptance tests written FIRST from Appendix D
2. **Unit Tests (60)** - Pure functions written FIRST with TDD
3. **Integration Tests (15)** - Complex behavior validated AFTER implementation

**Rationale**: Shell tests ensure user-facing behavior is correct. Unit tests ensure algorithms work. Integration tests lock in system behavior.

---

### Shell Tests (20 total) - WRITE FIRST

**Location**: `tests/shell/` directory

**Purpose**: Acceptance tests that Claude can run to verify implementation. Each test from Appendix D becomes a standalone shell script.

**Test Template**:
```bash
#!/bin/bash
# Test ID: test_NN_description.sh
# Expected: <behavior>

set -e  # Exit on error

# Setup
aur mem index <path>

# Execute
OUTPUT=$(aur mem search "<query>" <flags>)

# Validate
if echo "$OUTPUT" | grep -q "<expected_pattern>"; then
    echo "✅ PASS: <test_name>"
    exit 0
else
    echo "❌ FAIL: <test_name>"
    echo "Expected: <expected>"
    echo "Got: $OUTPUT"
    exit 1
fi
```

#### Shell Test Specifications

**ST-1: Exact Match - SOAROrchestrator**
```bash
# tests/shell/test_01_exact_soarorchestrator.sh
# Expected: orchestrator.py:SOAROrchestrator ranks #1
aur mem search "SOAROrchestrator"
# Validate: First result contains "orchestrator.py.*SOAROrchestrator"
```

**ST-2: Exact Match - authenticate_user**
```bash
# tests/shell/test_02_exact_authenticate_user.sh
# Expected: auth_manager.py:authenticate_user() ranks #1
aur mem search "authenticate_user"
# Validate: First result contains "auth_manager.py.*authenticate_user"
```

**ST-3: Exact Match - BM25Scorer**
```bash
# tests/shell/test_03_exact_bm25scorer.sh
# Expected: bm25_scorer.py:BM25Scorer ranks #1
aur mem search "BM25Scorer"
# Validate: First result contains "bm25_scorer.py.*BM25Scorer"
```

**ST-4: Exact Match - chunk_id**
```bash
# tests/shell/test_04_exact_chunk_id.sh
# Expected: base_chunk.py:BaseChunk.chunk_id ranks #1
aur mem search "chunk_id"
# Validate: First result contains "chunk_id"
```

**ST-5: Exact Match - HybridRetriever**
```bash
# tests/shell/test_05_exact_hybrid_retriever.sh
# Expected: hybrid_retriever.py:HybridRetriever ranks #1
aur mem search "HybridRetriever"
# Validate: First result contains "hybrid_retriever.py.*HybridRetriever"
```

**ST-6: Semantic Concept - authentication flow**
```bash
# tests/shell/test_06_semantic_auth_flow.sh
# Expected: Mix of auth code + knowledge + reasoning
aur mem search "authentication flow"
# Validate: Results contain "auth" AND (Type: function OR Type: know OR Type: reas)
```

**ST-7: Semantic Concept - memory indexing**
```bash
# tests/shell/test_07_semantic_memory_indexing.sh
# Expected: Indexing-related chunks (code + reasoning + knowledge)
aur mem search "memory indexing"
# Validate: Results contain "index" or "memory"
```

**ST-8: Semantic Concept - error handling**
```bash
# tests/shell/test_08_semantic_error_handling.sh
# Expected: Exception handling code, error patterns
aur mem search "error handling"
# Validate: Results contain "error" or "exception"
```

**ST-9: Semantic Concept - configuration management**
```bash
# tests/shell/test_09_semantic_config.sh
# Expected: Config code + config knowledge
aur mem search "configuration management"
# Validate: Results contain "config"
```

**ST-10: Semantic Concept - git integration**
```bash
# tests/shell/test_10_semantic_git.sh
# Expected: Git metadata code + git usage knowledge
aur mem search "git integration"
# Validate: Results contain "git"
```

**ST-11: Type Filter - function,class**
```bash
# tests/shell/test_11_type_filter_code.sh
# Expected: Only functions and classes, no reasoning/knowledge
aur mem search "user management" --type function,class
# Validate: All results have Type: function OR Type: class (no "reas" or "know")
```

**ST-12: Type Filter - knowledge**
```bash
# tests/shell/test_12_type_filter_knowledge.sh
# Expected: Only conversation log chunks
aur mem search "oauth setup" --type knowledge
# Validate: All results have Type: know
```

**ST-13: Type Filter - reasoning**
```bash
# tests/shell/test_13_type_filter_reasoning.sh
# Expected: Only reasoning pattern chunks
aur mem search "decomposition pattern" --type reasoning
# Validate: All results have Type: reas
```

**ST-14: Multi-Type Results**
```bash
# tests/shell/test_14_multi_type_mix.sh
# Expected: Code + reasoning + knowledge in results
aur mem search "search algorithm"
# Validate: Results contain at least 2 different Type values
```

**ST-15: Type Filter - function only**
```bash
# tests/shell/test_15_type_filter_function.sh
# Expected: Only function chunks, no methods/classes
aur mem search "performance optimization" --type function
# Validate: All results have Type: function
```

**ST-16: Edge Case - No Results**
```bash
# tests/shell/test_16_edge_no_results.sh
# Expected: Graceful "No results" message
aur mem search "xyzabc123"
# Validate: Output contains "No results" or "No relevant results"
```

**ST-17: Edge Case - Acronym Tokenization**
```bash
# tests/shell/test_17_edge_acronym.sh
# Expected: HTTPSConnection found via acronym splitting
aur mem search "HTTPSConnection"
# Validate: Results contain "HTTPS" or "Connection"
```

**ST-18: Edge Case - Dot Notation**
```bash
# tests/shell/test_18_edge_dot_notation.sh
# Expected: Dot notation splitting works
aur mem search "get.user.data"
# Validate: Results contain "get" AND "user" AND "data"
```

**ST-19: Edge Case - camelCase**
```bash
# tests/shell/test_19_edge_camelcase.sh
# Expected: camelCase splitting works
aur mem search "getUserData"
# Validate: Results contain "get" or "user" or "data"
```

**ST-20: Edge Case - Empty Query**
```bash
# tests/shell/test_20_edge_empty_query.sh
# Expected: Error message or help text
aur mem search ""
# Validate: Output contains "Error" or "Usage" or returns all results
```

**Shell Test Execution**:
```bash
# Run all shell tests
cd tests/shell
for test in test_*.sh; do
    bash "$test"
done
```

---

### Unit Tests (60 total) - WRITE FIRST (TDD)

**Location**: `packages/context-code/tests/unit/semantic/test_bm25_scorer.py`

#### BM25Scorer Tests (15 tests)

**UT-BM25-01: Tokenize camelCase**
```python
def test_tokenize_camelcase():
    """getUserData → [get, user, data, getuserdata]"""
    result = tokenize("getUserData")
    assert "get" in result
    assert "user" in result
    assert "data" in result
    assert "getuserdata" in result.lower()
```

**UT-BM25-02: Tokenize snake_case**
```python
def test_tokenize_snake_case():
    """user_manager → [user, manager, user_manager]"""
    result = tokenize("user_manager")
    assert "user" in result
    assert "manager" in result
    assert "user_manager" in result
```

**UT-BM25-03: Tokenize dot notation**
```python
def test_tokenize_dot_notation():
    """auth.oauth.client → [auth, oauth, client, auth.oauth.client]"""
    result = tokenize("auth.oauth.client")
    assert "auth" in result
    assert "oauth" in result
    assert "client" in result
    # Optionally preserve full path
```

**UT-BM25-04: Tokenize acronyms**
```python
def test_tokenize_acronyms():
    """HTTPRequest → [http, request, httprequest]"""
    result = tokenize("HTTPRequest")
    assert "http" in [t.lower() for t in result]
    assert "request" in [t.lower() for t in result]
```

**UT-BM25-05: Tokenize mixed case**
```python
def test_tokenize_mixed():
    """getUserData.auth_token → splits both camelCase and snake_case"""
    result = tokenize("getUserData.auth_token")
    assert "get" in result
    assert "auth" in result
    assert "token" in result
```

**UT-BM25-06: Tokenize empty string**
```python
def test_tokenize_empty():
    """Empty string → empty list"""
    result = tokenize("")
    assert result == []
```

**UT-BM25-07: Tokenize special characters**
```python
def test_tokenize_special_chars():
    """user@email.com → splits on special chars"""
    result = tokenize("user@email.com")
    assert "user" in result
    assert "email" in result
    assert "com" in result
```

**UT-BM25-08: BM25 IDF calculation**
```python
def test_bm25_idf_calculation():
    """IDF formula: log((N - n(t) + 0.5) / (n(t) + 0.5))"""
    scorer = BM25Scorer()
    # Corpus: 3 docs, term "auth" in 2 docs
    docs = [("d1", "auth user"), ("d2", "auth token"), ("d3", "config")]
    scorer.build_index(docs)

    # n(auth) = 2, N = 3
    # IDF = log((3 - 2 + 0.5) / (2 + 0.5)) = log(1.5 / 2.5) = log(0.6)
    expected_idf = math.log(0.6)
    assert abs(scorer.idf["auth"] - expected_idf) < 0.01
```

**UT-BM25-09: BM25 score exact match**
```python
def test_bm25_score_exact_match():
    """Query term in doc scores > 0"""
    scorer = BM25Scorer(k1=1.5, b=0.75)
    docs = [("d1", "authenticate user")]
    scorer.build_index(docs)

    score = scorer.score("authenticate", "authenticate user")
    assert score > 0
```

**UT-BM25-10: BM25 score no match**
```python
def test_bm25_score_no_match():
    """Query term not in doc scores 0"""
    scorer = BM25Scorer()
    docs = [("d1", "authenticate user")]
    scorer.build_index(docs)

    score = scorer.score("oauth", "authenticate user")
    assert score == 0
```

**UT-BM25-11: BM25 length normalization**
```python
def test_bm25_length_normalization():
    """Shorter doc with term scores higher than longer doc (b parameter)"""
    scorer = BM25Scorer(k1=1.5, b=0.75)
    docs = [
        ("short", "auth"),
        ("long", "auth " + " ".join(["word"] * 100))
    ]
    scorer.build_index(docs)

    score_short = scorer.score("auth", "auth")
    score_long = scorer.score("auth", "auth " + " ".join(["word"] * 100))

    # Shorter doc should score higher
    assert score_short > score_long
```

**UT-BM25-12: BM25 saturation (k1)**
```python
def test_bm25_saturation():
    """Term frequency saturates (doesn't explode with high k1)"""
    scorer = BM25Scorer(k1=1.5, b=0.0)  # No length norm

    # Doc with 1 occurrence vs 100 occurrences
    doc1 = "auth"
    doc100 = " ".join(["auth"] * 100)

    scorer.build_index([("d1", doc1), ("d100", doc100)])

    score1 = scorer.score("auth", doc1)
    score100 = scorer.score("auth", doc100)

    # Score increase should saturate (not 100x)
    assert score100 / score1 < 10  # Less than 10x increase for 100x frequency
```

**UT-BM25-13: BM25 index save**
```python
def test_bm25_index_save(tmp_path):
    """Index saves to pickle file"""
    scorer = BM25Scorer()
    docs = [("d1", "auth user"), ("d2", "config")]
    scorer.build_index(docs)

    index_path = tmp_path / "bm25_index.pkl"
    scorer.save_index(index_path)

    assert index_path.exists()
```

**UT-BM25-14: BM25 index load**
```python
def test_bm25_index_load(tmp_path):
    """Index loads from pickle file correctly"""
    scorer1 = BM25Scorer()
    docs = [("d1", "auth user"), ("d2", "config")]
    scorer1.build_index(docs)

    index_path = tmp_path / "bm25_index.pkl"
    scorer1.save_index(index_path)

    scorer2 = BM25Scorer()
    scorer2.load_index(index_path)

    # Scores should match
    score1 = scorer1.score("auth", "auth user")
    score2 = scorer2.score("auth", "auth user")
    assert abs(score1 - score2) < 0.01
```

**UT-BM25-15: BM25 index corruption detection**
```python
def test_bm25_index_corruption(tmp_path):
    """Corrupted pickle raises error"""
    index_path = tmp_path / "corrupted.pkl"
    index_path.write_bytes(b"not a pickle")

    scorer = BM25Scorer()
    with pytest.raises(pickle.UnpicklingError):
        scorer.load_index(index_path)
```

#### HybridRetriever Tests (12 tests)

**UT-HYBRID-01: Staged retrieval Stage 1 filtering**
```python
def test_staged_retrieval_stage1():
    """Stage 1 returns top-K by BM25 score"""
    # Setup: 200 chunks, top-100 by BM25
    # Validate: Stage 1 returns exactly 100 chunks sorted by BM25
```

**UT-HYBRID-02: Staged retrieval Stage 2 reranking**
```python
def test_staged_retrieval_stage2():
    """Stage 2 re-ranks Stage 1 candidates by semantic+activation"""
    # Setup: 100 candidates from Stage 1
    # Validate: Final scores use semantic+activation, not BM25
```

**UT-HYBRID-03: No BM25 normalization**
```python
def test_no_bm25_normalization():
    """BM25 scores are NOT normalized (raw scores preserved)"""
    # Validate: Stage 1 candidates have raw BM25 scores
```

**UT-HYBRID-04: Stage 2 normalization within-candidates**
```python
def test_stage2_normalization_within_candidates():
    """Semantic/activation normalized ONLY within Stage 1 candidates"""
    # Validate: Min-max normalization applied to 100 candidates, not all chunks
```

**UT-HYBRID-05: Zero BM25 matches fallback**
```python
def test_zero_bm25_matches():
    """If no BM25 matches, fall back to pure semantic"""
    # Setup: Query with no keyword matches
    # Validate: Returns semantic-only results
```

**UT-HYBRID-06: Corpus smaller than top-K**
```python
def test_corpus_smaller_than_k():
    """If corpus has 50 chunks but K=100, use all 50"""
    # Validate: Stage 1 returns 50, not 100
```

**UT-HYBRID-07: Custom weights from config**
```python
def test_custom_weights():
    """Config weights applied correctly"""
    # Setup: config with semantic=0.7, activation=0.3
    # Validate: Final scores use custom weights
```

**UT-HYBRID-08: Invalid weights rejection**
```python
def test_invalid_weights():
    """Weights not summing to 1.0 raise error"""
    # Setup: config with semantic=0.6, activation=0.6
    # Validate: Raises ValueError
```

**UT-HYBRID-09: Empty query handling**
```python
def test_empty_query():
    """Empty query returns error or all results"""
    # Validate: Graceful handling
```

**UT-HYBRID-10: Search result format**
```python
def test_search_result_format():
    """Results include chunk, scores (bm25, semantic, activation, final)"""
    # Validate: Result dict has all required fields
```

**UT-HYBRID-11: Top-N limiting**
```python
def test_top_n_limiting():
    """Search returns exactly N results (default 10)"""
    # Validate: len(results) == 10 (or fewer if corpus smaller)
```

**UT-HYBRID-12: Exact match ranks first**
```python
def test_exact_match_priority():
    """Exact keyword match ranks higher than semantic-only match"""
    # Setup: "SOAROrchestrator" exact vs "orchestrator pattern" semantic
    # Validate: Exact match is #1
```

#### KnowledgeParser Tests (10 tests)

**UT-KNOW-01: Parse all phases**
```python
def test_parse_all_phases():
    """Extracts all 9 phases from conversation log"""
    # Setup: Log with ## Phase 1-9 headers
    # Validate: 9 KnowledgeChunks created
```

**UT-KNOW-02: Parse missing phases**
```python
def test_parse_missing_phases():
    """Handles logs with only some phases"""
    # Setup: Log with only Phase 1, 3, 7
    # Validate: 3 KnowledgeChunks created, no errors
```

**UT-KNOW-03: Parse malformed headers**
```python
def test_parse_malformed_headers():
    """Handles malformed phase headers gracefully"""
    # Setup: Log with "## Phas 1" (typo)
    # Validate: Skips malformed, continues parsing
```

**UT-KNOW-04: Extract date from filename**
```python
def test_extract_date_from_filename():
    """Parses date from oauth-impl-2025-12-15.md"""
    # Validate: conversation_date = "2025-12-15"
```

**UT-KNOW-05: Extract date from content**
```python
def test_extract_date_from_content():
    """Falls back to Date: field in log header"""
    # Setup: Log with "Date: 2025-12-20"
    # Validate: conversation_date = "2025-12-20"
```

**UT-KNOW-06: Handle empty log**
```python
def test_handle_empty_log():
    """Empty log file returns empty list"""
    # Validate: [] returned, no exceptions
```

**UT-KNOW-07: Handle no logs directory**
```python
def test_no_logs_directory():
    """Missing logs directory returns empty list + warning"""
    # Validate: [] returned, warning logged
```

**UT-KNOW-08: UTF-8 encoding**
```python
def test_utf8_encoding():
    """Handles UTF-8 special characters correctly"""
    # Setup: Log with émojis, accents
    # Validate: Content preserved
```

**UT-KNOW-09: Extract query from header**
```python
def test_extract_query():
    """Extracts user query from log header"""
    # Setup: Log with "Query: implement oauth"
    # Validate: metadata["query"] = "implement oauth"
```

**UT-KNOW-10: Chunk ID format**
```python
def test_chunk_id_format():
    """Chunk IDs follow convention: conv-{filename}-phase{N}"""
    # Validate: chunk_id = "conv-oauth-impl-2025-12-15-phase3"
```

#### Type Filtering Tests (6 tests)

**UT-FILTER-01: Single type exact match**
```python
def test_filter_single_type():
    """--type function returns only FunctionChunk"""
    # Validate: All results have element_type="function"
```

**UT-FILTER-02: Multiple types**
```python
def test_filter_multiple_types():
    """--type function,class returns union"""
    # Validate: Results have element_type in ["function", "class"]
```

**UT-FILTER-03: Invalid type error**
```python
def test_filter_invalid_type():
    """--type invalid raises clear error"""
    # Validate: Error message lists valid types
```

**UT-FILTER-04: Case insensitive**
```python
def test_filter_case_insensitive():
    """--type Function works (case insensitive)"""
    # Validate: "Function" == "function"
```

**UT-FILTER-05: No results after filter**
```python
def test_filter_no_results():
    """Type filter removes all results gracefully"""
    # Setup: Search with --type reasoning but no reasoning chunks
    # Validate: "No results" message
```

**UT-FILTER-06: Reasoning and knowledge types**
```python
def test_filter_reas_know():
    """--type reasoning,knowledge works"""
    # Validate: Results are ReasoningChunk or KnowledgeChunk
```

#### Configuration Tests (7 tests)

**UT-CONFIG-01: Load valid config**
```python
def test_load_valid_config():
    """Loads config from ~/.aurora/config.yml"""
    # Validate: k1, b, weights loaded correctly
```

**UT-CONFIG-02: Missing config fallback**
```python
def test_missing_config():
    """Missing config uses hardcoded defaults (no error)"""
    # Validate: k1=1.5, b=0.75, semantic=0.5, activation=0.5
```

**UT-CONFIG-03: Invalid YAML**
```python
def test_invalid_yaml():
    """Malformed YAML raises clear error"""
    # Setup: config with syntax error
    # Validate: YAMLError with helpful message
```

**UT-CONFIG-04: Out-of-range k1**
```python
def test_out_of_range_k1():
    """k1 < 0 raises validation error"""
    # Validate: Error message: "k1 must be ≥ 0.0"
```

**UT-CONFIG-05: Out-of-range b**
```python
def test_out_of_range_b():
    """b not in [0, 1] raises validation error"""
    # Validate: Error message: "b must be in [0, 1]"
```

**UT-CONFIG-06: Weights not summing to 1**
```python
def test_weights_not_sum_to_1():
    """semantic + activation ≠ 1.0 raises error"""
    # Validate: Error message: "Weights must sum to 1.0"
```

**UT-CONFIG-07: Config changes immediate**
```python
def test_config_changes_immediate():
    """Config changes take effect on next search (no restart)"""
    # Setup: Modify config file
    # Validate: Next search uses new config
```

#### Display Tests (10 tests)

**UT-DISPLAY-01: Table alignment**
```python
def test_table_alignment():
    """Columns align correctly with Rich Table"""
    # Validate: File, Type, Name, Lines, Score, Commits, Last Modified align
```

**UT-DISPLAY-02: Git tracked file**
```python
def test_display_git_tracked():
    """Tracked file shows commit count + last modified"""
    # Validate: "23" in Commits, "2 days ago" in Last Modified
```

**UT-DISPLAY-03: Git untracked file**
```python
def test_display_git_untracked():
    """Untracked file shows '- (untracked)'"""
    # Validate: "- (untracked)" in both columns
```

**UT-DISPLAY-04: Git unavailable**
```python
def test_display_git_unavailable():
    """Git failure shows '- (unavailable)'"""
    # Validate: "- (unavailable)" in both columns
```

**UT-DISPLAY-05: Legacy mode**
```python
def test_display_legacy_mode():
    """--legacy flag hides git columns"""
    # Validate: Only File, Type, Name, Lines, Score columns
```

**UT-DISPLAY-06: Show scores box drawing**
```python
def test_display_show_scores():
    """--show-scores uses box-drawing characters"""
    # Validate: Output contains "┌", "├", "└", "│"
```

**UT-DISPLAY-07: Score explanations**
```python
def test_display_score_explanations():
    """Score breakdown includes explanations"""
    # Validate: "exact keyword match on 'auth'" appears
```

**UT-DISPLAY-08: Knowledge chunk display**
```python
def test_display_knowledge_chunk():
    """Knowledge chunks show Type: know, source log"""
    # Validate: Type column = "know", Lines = "-"
```

**UT-DISPLAY-09: Reasoning chunk display**
```python
def test_display_reasoning_chunk():
    """Reasoning chunks show Type: reas, created date"""
    # Validate: Type column = "reas", Last Modified = date
```

**UT-DISPLAY-10: Empty results**
```python
def test_display_empty_results():
    """No results shows helpful message"""
    # Validate: "No relevant results found" + suggestions
```

---

### Integration Tests (15 total) - WRITE AFTER IMPLEMENTATION

**Location**: `tests/integration/test_bm25_integration.py`

#### End-to-End Search Tests (5 tests)

**IT-E2E-01: Mixed chunk types**
```python
def test_e2e_mixed_chunk_types():
    """Search returns code + reasoning + knowledge chunks"""
    # Setup: Index code, create reasoning chunk, parse logs
    # Execute: aur mem search "authentication"
    # Validate: Results include all 3 types
```

**IT-E2E-02: Type filtering applied**
```python
def test_e2e_type_filtering():
    """--type flag correctly filters results"""
    # Execute: aur mem search "auth" --type function
    # Validate: Only function chunks in results
```

**IT-E2E-03: Score ranking correctness**
```python
def test_e2e_score_ranking():
    """Results ranked by final score (staged retrieval)"""
    # Validate: result[0].score > result[1].score > result[2].score
```

**IT-E2E-04: Git metadata displayed**
```python
def test_e2e_git_metadata():
    """Git commits and last modified shown in results"""
    # Validate: Table has Commits and Last Modified columns with data
```

**IT-E2E-05: Score transparency**
```python
def test_e2e_show_scores():
    """--show-scores displays breakdown correctly"""
    # Execute: aur mem search "auth" --show-scores
    # Validate: BM25, Semantic, Activation scores shown
```

#### Index Rebuild Tests (3 tests)

**IT-REBUILD-01: Auto-detection**
```python
def test_rebuild_auto_detection():
    """BM25 index auto-rebuilds when chunk count changes"""
    # Setup: Build index with 100 chunks
    # Add 50 more chunks
    # Execute: aur mem search "query"
    # Validate: Index rebuilt to 150 chunks
```

**IT-REBUILD-02: Manual rebuild**
```python
def test_rebuild_manual():
    """aur mem rebuild-bm25 command works"""
    # Execute: aur mem rebuild-bm25
    # Validate: Index rebuilt, success message displayed
```

**IT-REBUILD-03: Corrupted index recovery**
```python
def test_rebuild_corrupted():
    """Corrupted index triggers auto-rebuild"""
    # Setup: Corrupt ~/.aurora/indexes/bm25_index.pkl
    # Execute: aur mem search "query"
    # Validate: Warning displayed, index rebuilt
```

#### Error Handling Tests (7 tests)

**IT-ERROR-01: Missing logs warning**
```python
def test_error_missing_logs():
    """No conversation logs displays warning + continues"""
    # Setup: Delete ~/.aurora/logs/conversations/
    # Execute: aur mem index
    # Validate: Warning displayed, code chunks indexed
```

**IT-ERROR-02: Embedding failure skip**
```python
def test_error_embedding_failure():
    """Embedding failure skips chunk + continues"""
    # Setup: Mock embedding provider to fail for 1 chunk
    # Execute: aur mem index
    # Validate: Warning displayed, other chunks indexed
```

**IT-ERROR-03: Git failure unavailable**
```python
def test_error_git_failure():
    """Git blame failure shows '- (unavailable)' + continues"""
    # Setup: Mock git to fail
    # Execute: aur mem search "query"
    # Validate: "- (unavailable)" in results, search completes
```

**IT-ERROR-04: BM25 corruption rebuild**
```python
def test_error_bm25_corruption():
    """Corrupted BM25 index rebuilds + search continues"""
    # Setup: Corrupt index file
    # Execute: aur mem search "query"
    # Validate: Warning, rebuild, results returned
```

**IT-ERROR-05: Invalid config error**
```python
def test_error_invalid_config():
    """Invalid config values produce clear error"""
    # Setup: config with k1=-1.5
    # Execute: aur mem search "query"
    # Validate: Error message with validation failure
```

**IT-ERROR-06: Zero BM25 matches fallback**
```python
def test_error_zero_bm25_matches():
    """Query with no keyword matches falls back to semantic"""
    # Execute: aur mem search "xyzabc123"
    # Validate: Note message, semantic results returned
```

**IT-ERROR-07: Empty query handling**
```python
def test_error_empty_query():
    """Empty query handled gracefully"""
    # Execute: aur mem search ""
    # Validate: Error message or all results
```

---

### Manual QA Tests (20 queries)
See **Section 8.2** for detailed test suite.

### Performance Benchmarks (3 tests)
1. Simple query latency (<2s target)
2. Complex query latency (<10s target)
3. BM25 index build time (<30s target)

---

## 14. Documentation Requirements

### User-Facing Documentation
1. **CLI Help Text**: Update `aur mem search --help` with new flags:
   - `--type`: Filter by chunk type
   - `--show-scores`: Display score breakdown
   - `--legacy`: Use old output format

2. **CHANGELOG.md**: Document breaking change:
   ```markdown
   ## [0.3.0] - 2025-01-XX
   ### Added
   - BM25 tri-hybrid retrieval for improved search quality
   - Knowledge chunk indexing from conversation logs
   - Reasoning chunk search support
   - Git metadata (commits, last modified) in search results
   - `--show-scores` flag for score transparency
   - `--type` flag for filtering by chunk type

   ### Changed
   - **BREAKING**: Search result output format now includes git metadata by default
     - Use `--legacy` flag to revert to old format
   - BM25 index auto-rebuilds when stale (detected by chunk count)
   ```

3. **README.md**: Add "Search Quality" section explaining:
   - Tri-hybrid retrieval architecture
   - When to use `--type` filtering
   - How to interpret `--show-scores` output
   - Config tuning guide (k1, b, weights)

### Developer Documentation
1. **docs/architecture/SEARCH_ARCHITECTURE.md**: New document covering:
   - Staged retrieval flow diagram
   - BM25 algorithm explanation
   - Score normalization approach
   - Index structure and caching

2. **Docstrings**: All new classes/methods must have:
   - Single-line summary
   - Args/Returns with types
   - Example usage
   - Raises (error conditions)

3. **Code Comments**: Explain non-obvious decisions:
   - Why no BM25 normalization (preserve raw scores)
   - Why Stage 2 normalization is within-candidates
   - Tokenization regex patterns

---

## 15. Acceptance Criteria Summary

### Feature Complete When:
- [ ] BM25Scorer implemented with code-aware tokenization
- [ ] Staged retrieval (BM25 filter → Semantic+Activation re-rank) working
- [ ] Knowledge chunks indexed from conversation logs
- [ ] Reasoning chunks searchable (success_score ≥ 0.5)
- [ ] Git metadata (commits, last modified) displayed in results
- [ ] `--show-scores` flag shows breakdown with box-drawing
- [ ] `--type` flag filters by exact chunk types
- [ ] `--legacy` flag reverts to old output format
- [ ] Config loaded from `~/.aurora/config.yml` with validation
- [ ] BM25 index auto-detects staleness and rebuilds
- [ ] `aur mem rebuild-bm25` command works
- [ ] Error handling graceful (missing logs, corrupted index, git failures)
- [ ] **Indexing summary displays code/reasoning/knowledge chunk counts separately** (FR-11)

### Tests Pass When:
- [ ] 60 unit tests pass (100% coverage for new code)
- [ ] 15 integration tests pass
- [ ] 20/20 manual QA queries pass
- [ ] Performance benchmarks meet targets (simple <2s, complex <10s, build <30s)
- [ ] ≥18/20 exact match queries rank #1 (90% success rate)

### Documentation Complete When:
- [ ] CLI help text updated
- [ ] CHANGELOG.md entry written
- [ ] README.md search section added
- [ ] SEARCH_ARCHITECTURE.md created
- [ ] All public APIs have docstrings
- [ ] Migration notice implemented (one-time message)

---

## Appendix A: Example Queries & Expected Results

### Query 1: Exact Class Name
**Query**: `"SOAROrchestrator"`
**Expected Top Result**: `orchestrator.py:SOAROrchestrator` (class definition)
**Score Breakdown**:
- BM25: 0.95 (exact match on "SOAROrchestrator")
- Semantic: 0.82 (high relevance to orchestration concepts)
- Activation: 0.65 (frequently accessed, 45 commits)

### Query 2: Concept Search
**Query**: `"authentication flow"`
**Expected Top Results**:
1. `auth_manager.py:authenticate_user()` (code chunk)
2. `oauth-implementation.md` (knowledge chunk from conversation)
3. `auth-decomposition-pattern` (reasoning chunk)

**Score Breakdown** (Top Result):
- BM25: 0.70 (partial match on "authentication")
- Semantic: 0.91 (very high conceptual relevance)
- Activation: 0.55 (recent use, 12 commits)

### Query 3: Multi-Type Filtered
**Query**: `"user management" --type function,class`
**Expected Results**: Only FunctionChunk and ClassChunk (no reasoning or knowledge)
**Top Result**: `user_manager.py:UserManager` (class)

### Query 4: Knowledge-Only Search
**Query**: `"oauth setup steps" --type knowledge`
**Expected Results**: Only KnowledgeChunk from conversation logs
**Top Result**: `oauth-impl-2025-12-15.md:Phase 3` (knowledge chunk explaining OAuth setup)

---

## Appendix B: BM25 Algorithm Pseudocode

```python
def bm25_score(query: str, document: str, corpus: List[str]) -> float:
    """
    Compute BM25 score for document given query.

    Args:
        query: Search query (e.g., "authenticate user")
        document: Chunk content to score
        corpus: All chunks in index (for IDF calculation)

    Returns:
        BM25 score (unbounded, typically 0-20 range)
    """
    # Tokenize
    query_terms = tokenize(query)
    doc_terms = tokenize(document)

    # Compute IDF for each query term
    N = len(corpus)
    idf = {}
    for term in query_terms:
        n_t = count_documents_containing(term, corpus)
        idf[term] = log((N - n_t + 0.5) / (n_t + 0.5) + 1)

    # Compute document length normalization
    doc_length = len(doc_terms)
    avg_doc_length = mean([len(tokenize(doc)) for doc in corpus])

    # BM25 scoring
    score = 0.0
    for term in query_terms:
        if term not in doc_terms:
            continue

        freq = doc_terms.count(term)
        numerator = freq * (k1 + 1)
        denominator = freq + k1 * (1 - b + b * doc_length / avg_doc_length)

        score += idf[term] * (numerator / denominator)

    return score
```

---

## Appendix C: Configuration Example

**File**: `~/.aurora/config.yml`

```yaml
# Aurora Configuration
version: "1.0"

# Search Configuration
search:
  # BM25 Parameters
  bm25:
    k1: 1.5          # Term frequency saturation (1.2-2.0 typical)
    b: 0.75          # Length normalization (0.0-1.0)

  # Hybrid Retrieval Parameters
  hybrid:
    stage1_top_k: 100         # Number of BM25 candidates for Stage 2
    stage2_weights:
      semantic: 0.5            # Semantic similarity weight (must sum to 1.0)
      activation: 0.5          # ACT-R activation weight

# UI Preferences
ui:
  shown_search_format_notice: true  # One-time migration notice shown
  default_search_format: "enhanced"  # "enhanced" or "legacy"
```

**Validation Rules**:
- `k1 ≥ 0.0`
- `0.0 ≤ b ≤ 1.0`
- `stage1_top_k ≥ 10`
- `semantic + activation = 1.0`

---

## Appendix D: Test Query Suite (20 Queries)

### Exact Match Queries (5)
1. `"SOAROrchestrator"` → Expect: `orchestrator.py:SOAROrchestrator` #1
2. `"authenticate_user"` → Expect: `auth_manager.py:authenticate_user()` #1
3. `"BM25Scorer"` → Expect: `bm25_scorer.py:BM25Scorer` #1
4. `"chunk_id"` → Expect: `base_chunk.py:BaseChunk.chunk_id` #1
5. `"HybridRetriever"` → Expect: `hybrid_retriever.py:HybridRetriever` #1

### Semantic Concept Queries (5)
6. `"authentication flow"` → Expect: auth-related code/knowledge/reasoning
7. `"memory indexing"` → Expect: indexing code, reasoning patterns, knowledge
8. `"error handling"` → Expect: exception handling code, error patterns
9. `"configuration management"` → Expect: config code, config knowledge
10. `"git integration"` → Expect: git metadata code, git usage knowledge

### Multi-Type Queries (5)
11. `"user management" --type function,class` → Expect: Only code chunks
12. `"oauth setup" --type knowledge` → Expect: Only conversation logs
13. `"decomposition pattern" --type reasoning` → Expect: Only reasoning chunks
14. `"search algorithm"` → Expect: Code + reasoning + knowledge mix
15. `"performance optimization" --type function` → Expect: Only functions

### Edge Case Queries (5)
16. `"xyzabc123"` → Expect: No results (graceful handling)
17. `"HTTPSConnection"` → Expect: Acronym tokenization works
18. `"get.user.data"` → Expect: Dot notation splitting works
19. `"getUserData"` → Expect: camelCase splitting works
20. `""` (empty query) → Expect: Error message or all results

---

**End of PRD-0015**
