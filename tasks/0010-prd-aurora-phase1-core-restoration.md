# PRD-0010: Aurora Phase 1 - Core Restoration

**Version**: v0.2.1
**Status**: Draft
**Priority**: P0 (CRITICAL - System Unusable)
**Target Sprint**: Sprint 1 (6 days)
**Estimated Effort**: 54 hours (36h coding + 18h testing)
**Created**: 2025-12-28
**Updated**: 2025-12-28 (Added Issue #16: Git-Based BLA Initialization)
**Updated**: 2025-12-28 (Changed to FUNCTION-level Git tracking via git blame)

---

## 1. Introduction/Overview

### Problem Statement

Following comprehensive end-to-end testing of Aurora v0.2.0, **16 critical failures** were identified that render the system largely non-functional for real-world use. Despite 2,369 passing unit tests (97% pass rate), the **integrated CLI workflow** that users actually experience is broken due to missing E2E and integration test coverage.

User feedback: *"after fully testing, we almost have nothing working properly... this is detailed specs document that we will use in our major fixes... i am honestly disappointed, as the repo now looks like a spaghetti and makes me doubt all the useless tests you created and said they run perfectly"*

### High-Level Goal

**Restore core Aurora CLI functionality** by fixing all P0 (blocking) and P1 (critical) issues, enabling users to complete the basic workflow: initialize → index → search → query without errors.

This PRD focuses on **Phase 1 only** - the 8 most critical issues that must be fixed first. Phase 2 (MCP integration and polish) will be addressed in a separate PRD after v0.2.1 release.

### Context

**What's Broken**:
- Database path confusion creates multiple DBs (data loss risk)
- Search returns identical results regardless of query
- Query doesn't retrieve from indexed data (renders indexing useless)
- All chunks start with zero activation (ignores Git commit history)
- SOAR complexity assessment completely broken (always says SIMPLE)
- Auto-escalation doesn't work (low confidence never triggers SOAR)
- Budget management command missing (documented but not implemented)
- Stack traces on errors (poor user experience)

**Root Cause**: Unit tests passed in isolation, but **no E2E or integration tests** verified the complete user workflows.

---

## 2. Goals

**Primary Objective**: Make Aurora CLI actually work for basic operations

**Specific, Measurable Goals**:

1. **Single Database Source of Truth** - All commands use `~/.aurora/memory.db`, never create local `aurora.db` files
2. **Functional Search** - Search returns relevant, varied results with proper activation scores (not identical results)
3. **Query Uses Index** - Queries retrieve from indexed codebase and pass context to LLM
4. **Git-Based BLA Initialization** - Chunks initialized with activation based on Git commit history (frequency + recency)
5. **Working Complexity Assessment** - Domain-specific queries (SOAR, ACT-R, agentic AI) correctly classified as MEDIUM/COMPLEX
6. **Auto-Escalation Logic** - Low confidence queries (< 0.6) automatically escalate to SOAR or prompt user
7. **Budget Management** - `aur budget` command implemented with show/set/history subcommands
8. **Clean Error Messages** - Authentication errors show user-friendly messages, not stack traces (unless `--debug` flag used)

**Success Metric**: User can complete `/home/hamr/PycharmProjects/aurora/docs/testing/TESTING_AURORA_FROM_SCRATCH.md` workflow without any errors.

---

## 3. User Stories

### US-1: Single Database Location (P0)
**As a** new Aurora user
**I want to** have all my indexed data stored in one predictable location
**So that** I don't lose data or get confused by multiple databases

**Acceptance Criteria**:
- `aur init` creates `~/.aurora/memory.db` only
- `aur mem index .` writes to `~/.aurora/memory.db`
- `aur mem search` reads from `~/.aurora/memory.db`
- `aur query` reads from `~/.aurora/memory.db`
- `aur mem stats` shows correct chunk count from `~/.aurora/memory.db`
- No local `aurora.db` files created in project directories
- Config file (`~/.aurora/config.json`) specifies DB path and all commands respect it

**Test Scenario**:
```bash
# Clean start
rm -rf ~/.aurora
cd /home/hamr/PycharmProjects/aurora
aur init  # Creates ~/.aurora/memory.db

# Index current directory
aur mem index .  # Writes to ~/.aurora/memory.db

# Verify data persists
aur mem stats  # Shows > 0 chunks from ~/.aurora/memory.db

# Delete local files (should not affect Aurora)
rm -f ./aurora.db  # If exists, should be harmless

# Search still works
aur mem search "function"  # Returns results from ~/.aurora/memory.db
```

---

### US-2: Accurate Search Results (P0)
**As a** developer using Aurora
**I want to** get relevant, varied search results based on my query
**So that** I can find the code I'm actually looking for

**Acceptance Criteria**:
- Different queries return different results (not identical top 5 every time)
- Activation scores vary across chunks (not all 1.000)
- Semantic scores vary based on query relevance (not all 1.000)
- Line ranges show correct values (not `0-0`)
- More frequently accessed chunks score higher over time
- Related code ranks higher than unrelated code

**Test Scenario**:
```bash
# Index codebase
aur init
aur mem index .

# Different searches should return different results
aur mem search "hybrid retrieval" --output json > search1.json
aur mem search "sqlite database" --output json > search2.json
aur mem search "complexity assessment" --output json > search3.json

# Verify results differ
python3 << EOF
import json
s1 = json.load(open('search1.json'))
s2 = json.load(open('search2.json'))
s3 = json.load(open('search3.json'))

# Check that top results are different files
assert s1[0]['file_path'] != s2[0]['file_path'], "Search 1 and 2 return same file"
assert s2[0]['file_path'] != s3[0]['file_path'], "Search 2 and 3 return same file"

# Check that scores vary
assert len(set([r['score'] for r in s1])) > 1, "All scores identical in search 1"
print("✓ Search results are varied and relevant")
EOF
```

---

### US-3: Query Retrieves from Index (P0)
**As a** user with indexed code
**I want to** get answers based on my actual codebase
**So that** indexing is actually useful

**Acceptance Criteria**:
- `aur query` retrieves relevant chunks from memory store before calling LLM
- Retrieved chunks are passed to LLM as context
- LLM answer references actual code from the codebase
- Query output shows which files/chunks were used
- Queries about indexed code return accurate answers (not generic responses)

**Test Scenario**:
```bash
# Index Aurora codebase
aur init
aur mem index .

# Query about specific code that exists
aur query "list all functions in HybridRetriever class" --verbose

# Expected output should show:
# - Retrieved chunks from hybrid_retriever.py
# - Actual function names from the codebase
# - File paths and line ranges used

# Should NOT return generic answer like:
# "To list functions, you can use grep or IDE search..."
```

---

### US-8: Git-Based BLA Initialization (P0)
**As a** developer indexing a Git repository
**I want to** have chunks initialized with activation scores based on commit history AT FUNCTION LEVEL
**So that** frequently/recently modified functions are prioritized in search results from the start

**Acceptance Criteria**:
- During indexing, system extracts Git commit history for each FUNCTION (not entire file)
- Uses `git blame -L <start>,<end>` to track commits that touched each function's line range
- Base-level activation (BLA) calculated using ACT-R formula: `B = ln(Σ t_j^(-d))`
- Each commit that touched the function's lines treated as a "fake access" at commit time
- `access_count` initialized to number of commits touching this function (not 0)
- `base_level` initialized to calculated BLA (not 0.0)
- `git_hash` stored in chunk metadata (current commit SHA)
- `last_modified` stored in chunk metadata (last commit timestamp)
- `commit_count` stored in chunk metadata (number of commits touching this function)
- Functions in the SAME file have DIFFERENT activation scores based on their individual edit history
- Frequently-edited functions (many commits touching their lines) have higher BLA than rarely-edited functions
- git blame line ranges match tree-sitter chunk boundaries (line_start to line_end)
- Works gracefully for non-Git directories (falls back to base_level=0.5)

**Test Scenario**:
```bash
# Index a Git repository
cd /home/hamr/PycharmProjects/aurora  # Has Git history
aur init
aur mem index .

# Check activation scores in database (FUNCTION-LEVEL)
sqlite3 ~/.aurora/memory.db << EOF
SELECT
  c.file_path,
  c.name,
  a.base_level,
  a.access_count,
  c.metadata->>'git_hash' as git_hash,
  c.metadata->>'commit_count' as commit_count
FROM chunks c
JOIN activations a ON c.chunk_id = a.chunk_id
ORDER BY a.base_level DESC
LIMIT 10;
EOF

# Expected:
# - base_level varies (not all 0.0)
# - access_count > 0 for functions with commits
# - git_hash present (40-char SHA)
# - commit_count varies per function (not all same)
# - Frequently committed functions have higher base_level
# - Recently committed functions have higher base_level

# CRITICAL: Check functions in SAME file have DIFFERENT scores
sqlite3 ~/.aurora/memory.db "
  SELECT
    c.name,
    a.base_level,
    a.access_count
  FROM chunks c
  JOIN activations a ON c.chunk_id = a.chunk_id
  WHERE c.file_path LIKE '%memory_manager.py'
  ORDER BY a.base_level DESC;
"

# Expected output (functions in same file have DIFFERENT scores):
# index_file          | 2.45 | 8  (edited in 8 commits - frequently changed)
# search              | 1.82 | 5  (edited in 5 commits - moderate)
# get_stats           | 0.91 | 2  (edited in 2 commits - rarely touched)
# _validate_path      | 0.50 | 1  (edited in 1 commit - barely touched)

# Verify Git signals used correctly
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect("/home/user/.aurora/memory.db")
cursor = conn.cursor()

# Get activation statistics
cursor.execute("SELECT AVG(base_level), STDDEV(base_level), MIN(base_level), MAX(base_level) FROM activations WHERE base_level > 0")
avg, stddev, min_val, max_val = cursor.fetchone()

print(f"Activation Stats:")
print(f"  Average: {avg:.4f} (should be > 0)")
print(f"  StdDev:  {stddev:.4f} (should be > 0.1)")
print(f"  Range:   [{min_val:.4f}, {max_val:.4f}]")

# Verify Git metadata present
cursor.execute("SELECT COUNT(*) FROM chunks WHERE metadata->>'git_hash' IS NOT NULL")
with_git = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM chunks")
total = cursor.fetchone()[0]

print(f"Git metadata: {with_git}/{total} chunks ({100*with_git/total:.1f}%)")
assert avg > 0, "Average activation still 0.0 (Git not used)"
assert stddev > 0.1, "Activation scores too similar (not varied)"
assert with_git > 0, "No Git metadata stored"

# CRITICAL: Verify function-level tracking
cursor.execute("""
    SELECT COUNT(DISTINCT a.base_level)
    FROM chunks c
    JOIN activations a ON c.chunk_id = a.chunk_id
    WHERE c.file_path LIKE '%memory_manager.py'
""")
unique_bla_in_file = cursor.fetchone()[0]
assert unique_bla_in_file > 1, "All functions in same file have identical BLA (not function-level)"

print("✓ Git-based BLA initialization working (FUNCTION-LEVEL)")
PYEOF

# Test non-Git directory (graceful fallback)
mkdir /tmp/test-no-git
echo "def test(): pass" > /tmp/test-no-git/file.py
aur mem index /tmp/test-no-git

# Should not crash, chunks get base_level=0.5 (default)
```

---

### US-4: Accurate Complexity Assessment (P1)
**As a** user asking technical questions
**I want to** have Aurora correctly identify complex queries
**So that** SOAR pipeline is triggered when appropriate

**Acceptance Criteria**:
- Multi-part questions classified as MEDIUM or COMPLEX (not SIMPLE)
- Domain-specific terms (SOAR, ACT-R, agentic, marketplace) boost complexity score
- Scope keywords (research, analyze, compare, design) boost complexity score
- Queries with 2+ question marks boost complexity score
- Simple lookups remain SIMPLE
- Confidence scores reflect keyword match quality

**Test Scenario**:
```bash
# Complex multi-part question
aur query "research agentic ai market? who are the top players? what features every one?" --dry-run

# Expected: Complexity: MEDIUM or COMPLEX (not SIMPLE)
# Expected: Score >= 0.4
# Expected: Decision: Would use SOAR pipeline

# Domain-specific query
aur query "explain SOAR reasoning phases in Aurora" --dry-run

# Expected: Complexity: MEDIUM (not SIMPLE)
# Expected: Keywords matched: soar, reasoning, phases

# Simple query (should stay simple)
aur query "what is Python?" --dry-run

# Expected: Complexity: SIMPLE
```

---

### US-5: Auto-Escalation Logic (P1)
**As a** user in non-interactive mode
**I want to** have low-confidence queries automatically escalate to SOAR
**So that** I get accurate answers even when Aurora isn't confident

**Acceptance Criteria**:
- Confidence < 0.6 triggers escalation logic
- In `--non-interactive` mode: automatically escalate to SOAR without prompt
- In interactive mode: prompt user with "Low confidence. Use SOAR? [y/N]"
- User can choose to escalate or continue with direct LLM
- Escalation decision logged for transparency

**Test Scenario**:
```bash
# Non-interactive mode with borderline query
aur query "list all functions in the codebase" --non-interactive --verbose

# Expected flow:
# 1. Assess complexity → SIMPLE, confidence 0.45 (low)
# 2. Detect confidence < 0.6
# 3. Auto-escalate to SOAR (no prompt in non-interactive)
# 4. Execute SOAR 9-phase pipeline
# 5. Return answer with retrieval from indexed codebase

# Interactive mode
aur query "list all functions in the codebase"

# Expected:
# Assessing query...
# Complexity: SIMPLE (confidence: 0.45)
# ⚠ Low confidence detected. Use SOAR 9-phase pipeline for better accuracy? [y/N]: _
# (waits for user input)
```

---

### US-6: Budget Management (P1)
**As a** cost-conscious user
**I want to** set and monitor my API spending
**So that** I don't accidentally exceed my budget

**Acceptance Criteria**:
- `aur budget` shows current spending, budget limit, and remaining balance
- `aur budget set <amount>` updates budget limit in `~/.aurora/budget_tracker.json`
- `aur budget reset` sets spending back to $0.00
- `aur budget history` shows table of past queries with costs
- Queries blocked before API call if budget exceeded
- Clear error message when budget limit reached

**Test Scenario**:
```bash
# Check initial budget
aur budget
# Output:
# Spent: $0.0000
# Budget: $10.0000 (default)
# Remaining: $10.0000

# Set low budget for testing
aur budget set 0.01

# Run expensive query (will fail)
aur query "explain everything about Aurora in extreme detail"
# Expected error:
# ✗ Budget limit exceeded
# Spent: $0.0000 | Budget: $0.0100 | Estimated cost: $0.0234
# To continue, increase budget: aur budget set <amount>

# View history
aur budget history
# Output:
# Timestamp             | Query                | Cost     | Status
# 2025-12-28 10:30:45  | "explain SOAR"       | $0.0089  | completed
# 2025-12-28 10:31:12  | "explain everything" | $0.0000  | blocked (budget)
```

---

### US-7: Clean Error Messages (P1)
**As a** user who encounters errors
**I want to** see helpful error messages (not stack traces)
**So that** I understand what went wrong and how to fix it

**Acceptance Criteria**:
- Authentication errors show user-friendly message with solutions
- No Python tracebacks shown by default
- `--debug` flag enables full stack traces when needed
- Error messages include actionable next steps
- Errors categorized by type (auth, API, network, config)

**Test Scenario**:
```bash
# Invalid API key
export ANTHROPIC_API_KEY="invalid-key-123"
aur query "test query"

# Expected output (NO STACK TRACE):
# ✗ Authentication failed
#
# Invalid API key.
#
# Solutions:
#   1. Check your API key: export ANTHROPIC_API_KEY=sk-ant-...
#   2. Get a new key at: https://console.anthropic.com
#   3. Update config: aur init
#
# Run with --debug for technical details

# With --debug flag
aur query "test query" --debug

# Expected: Shows full Python traceback for debugging
```

---

## 4. Functional Requirements

### FR-1: Database Path Management (Issue #2)

**FR-1.1**: The system MUST always use `~/.aurora/memory.db` as the single database location for all operations.

**FR-1.2**: The system MUST create `~/.aurora/config.json` during `aur init` with the database path specification.

**FR-1.3**: All CLI commands MUST read database path from config file and respect it.

**FR-1.4**: The system MUST NOT create `aurora.db` files in the current working directory or project directories.

**FR-1.5**: If a local `aurora.db` file exists, the system MUST ignore it and warn the user on first use.

**FR-1.6**: The `aur init` command MUST offer to migrate data from local `aurora.db` to `~/.aurora/memory.db` if found.

**Implementation Files**:
- `packages/cli/src/aurora_cli/config.py` - Add `get_db_path()` method
- `packages/cli/src/aurora_cli/commands/memory.py` - Update to use config.get_db_path()
- `packages/cli/src/aurora_cli/commands/query.py` - Update to use config.get_db_path()
- `packages/cli/src/aurora_cli/main.py` - Update init command, add migration logic

---

### FR-2: Activation Tracking (Issue #4)

**FR-2.1**: The system MUST call `store.record_access(chunk_id, access_time, context)` whenever a chunk is retrieved during search.

**FR-2.2**: The system MUST increment `access_count` in the activations table for each chunk retrieval.

**FR-2.3**: The system MUST update `base_level` activation score using ACT-R decay formula.

**FR-2.4**: The system MUST update `last_access_time` timestamp for each chunk access.

**FR-2.5**: Activation scores MUST vary across chunks (not all 0.0 or all 1.0).

**FR-2.6**: The `HybridRetriever` MUST use updated activation scores in the hybrid scoring formula (60% activation + 40% semantic).

**Implementation Files**:
- `packages/cli/src/aurora_cli/memory_manager.py` - Add record_access() calls in search() method
- `packages/core/src/aurora_core/store/sqlite.py` - Verify record_access() implementation
- `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` - Verify activation integration

---

### FR-3: Query Retrieval Integration (Issue #15)

**FR-3.1**: The system MUST retrieve relevant chunks from memory store BEFORE calling the LLM during query execution.

**FR-3.2**: The system MUST use `memory_manager.search(query, limit=10)` to retrieve context chunks.

**FR-3.3**: The system MUST format retrieved chunks as structured context for the LLM prompt.

**FR-3.4**: The LLM prompt MUST include chunk content, file paths, and line ranges.

**FR-3.5**: The system MUST pass the formatted context to the LLM along with the user query.

**FR-3.6**: Query output MUST indicate which chunks/files were used (in verbose mode).

**Implementation Files**:
- `packages/cli/src/aurora_cli/execution.py` - Add retrieval step in execute_direct_llm() method

**Code Example**:
```python
def execute_direct_llm(self, query: str):
    # ADD THIS: Retrieve context BEFORE calling LLM
    context_chunks = self.memory_manager.search(query, limit=10)

    # Format context for LLM
    context = "\n\n".join([
        f"## {c.file_path}:{c.name} (lines {c.line_start}-{c.line_end})\n{c.content}"
        for c in context_chunks
    ])

    # Pass context to LLM
    response = llm.generate(
        prompt=f"Context from codebase:\n{context}\n\nUser Query: {query}"
    )
```

---

### FR-8: Git-Based BLA Initialization (Issue #16)

**FR-8.1**: The system MUST extract Git commit history during indexing for files in Git repositories AT FUNCTION LEVEL.

**FR-8.2**: The system MUST use `git blame -L <start>,<end> <file> --line-porcelain` to track commits that touched each FUNCTION (not entire file).

**FR-8.2.1**: For each function chunk (defined by line_start to line_end from tree-sitter):
- Run `git blame` on that specific line range
- Extract unique commit SHAs from blame output
- Get commit timestamps for each SHA via `git show -s --format=%ct <sha>`
- Result: List of commit times specific to THIS function

**FR-8.2.2**: Files with multiple functions MUST have DIFFERENT BLA scores per function based on which commits touched which functions.

**FR-8.3**: The system MUST extract unique commit SHAs from git blame output and get their timestamps.

**FR-8.4**: The system MUST calculate initial base-level activation using ACT-R formula: `B = ln(Σ t_j^(-d))` where:
- `t_j` = time since each commit that touched THIS FUNCTION'S lines (in seconds)
- `d` = decay rate (0.5 default)
- Each commit treated as a "fake access" at commit time

**IMPORTANT**: BLA is calculated PER FUNCTION based on which commits modified that function's line range, NOT from all commits to the entire file. This ensures frequently-edited functions have higher activation than rarely-touched functions in the same file.

**FR-8.5**: The system MUST initialize `base_level` with calculated BLA (not 0.0).

**FR-8.6**: The system MUST initialize `access_count` with number of commits (not 0).

**FR-8.7**: The system MUST store `git_hash` (most recent commit SHA touching this function) in chunk metadata.

**FR-8.8**: The system MUST store `last_modified` (most recent commit Unix timestamp for this function) in chunk metadata.

**FR-8.8.1**: The system MUST store `commit_count` (number of commits that touched this function's lines) in chunk metadata.

**FR-8.9**: For non-Git directories, the system MUST gracefully fall back to `base_level=0.5` and `access_count=1`.

**FR-8.10**: The system MUST NOT crash or fail indexing if Git operations fail (network issues, permissions, etc.).

**Implementation Files**:
- `packages/context-code/src/aurora_context_code/git.py` - New module for Git signal extraction (FUNCTION-level via git blame)
- `packages/cli/src/aurora_cli/memory_manager.py` - Pass line_start/line_end to Git extractor
- `packages/core/src/aurora_core/activation/engine.py` - Use function-specific BLA
- `packages/core/src/aurora_core/models/chunk.py` - Ensure line_start/line_end stored from tree-sitter; add git_hash, last_modified, commit_count to metadata

**Code Example**:
```python
# File: packages/context-code/src/aurora_context_code/git.py
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
import math

class GitSignalExtractor:
    """Extract Git signals for BLA initialization at FUNCTION level."""

    def get_function_commit_times(
        self,
        file_path: Path,
        start_line: int,
        end_line: int
    ) -> List[int]:
        """Get Unix timestamps for commits that touched this specific function.

        Args:
            file_path: Path to source file
            start_line: Function start line (from tree-sitter)
            end_line: Function end line (from tree-sitter)

        Returns:
            List of Unix timestamps for commits touching these lines,
            newest first. Empty list if not in Git or no history.
        """
        try:
            # Get git blame for function's line range
            result = subprocess.run(
                [
                    "git", "blame",
                    "-L", f"{start_line},{end_line}",
                    str(file_path),
                    "--line-porcelain"
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )

            if result.returncode != 0:
                return []

            # Extract unique commit SHAs from blame output
            commit_shas = set()
            for line in result.stdout.splitlines():
                # git blame --line-porcelain format: first 40 chars of line is SHA
                if len(line) >= 40 and not line.startswith('\t'):
                    potential_sha = line.split()[0]
                    if len(potential_sha) == 40:
                        try:
                            int(potential_sha, 16)  # Verify it's hex
                            commit_shas.add(potential_sha)
                        except ValueError:
                            continue

            # Get timestamp for each commit
            timestamps = []
            for sha in commit_shas:
                ts = self._get_commit_timestamp(sha)
                if ts:
                    timestamps.append(ts)

            return sorted(timestamps, reverse=True)  # Newest first

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def _get_commit_timestamp(self, commit_sha: str) -> Optional[int]:
        """Get Unix timestamp for a specific commit."""
        try:
            result = subprocess.run(
                ["git", "show", "-s", "--format=%ct", commit_sha],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip())
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            return None

    def calculate_bla(self, commit_times: List[int], decay: float = 0.5) -> float:
        """Calculate base-level activation from commit history.

        Args:
            commit_times: Unix timestamps of commits
            decay: Decay rate (default 0.5)

        Returns:
            BLA score using ACT-R formula: B = ln(Σ t_j^(-d))
        """
        if not commit_times:
            return 0.5  # Default for non-Git files

        now = datetime.now(timezone.utc).timestamp()

        # Calculate sum of decayed accesses
        sum_decayed = 0.0
        for commit_time in commit_times:
            time_since = max(now - commit_time, 1.0)  # Avoid division by zero
            sum_decayed += time_since ** (-decay)

        # BLA = ln(sum)
        bla = math.log(sum_decayed) if sum_decayed > 0 else 0.5
        return bla

# Usage in memory_manager.py:
def index_file(self, file_path: Path) -> List[Chunk]:
    # Parse file to get chunks (each has line_start, line_end from tree-sitter)
    chunks = self.parser.parse_file(file_path)

    # NEW: Extract Git signals PER FUNCTION
    git_extractor = GitSignalExtractor()

    for chunk in chunks:
        # Get commits specific to THIS function's line range
        commit_times = git_extractor.get_function_commit_times(
            file_path=file_path,
            start_line=chunk.line_start,
            end_line=chunk.line_end
        )

        # Calculate BLA from THIS function's commit history
        initial_bla = git_extractor.calculate_bla(commit_times)

        # Store metadata (function-specific)
        chunk.metadata["git_hash"] = commit_times[0] if commit_times else None
        chunk.metadata["last_modified"] = commit_times[0] if commit_times else None
        chunk.metadata["commit_count"] = len(commit_times)

        # Initialize activation with FUNCTION-SPECIFIC BLA
        self.store.store_chunk(chunk)
        self.store.initialize_activation(
            chunk_id=chunk.chunk_id,
            base_level=initial_bla,
            access_count=len(commit_times)
        )
```

---

### FR-4: Complexity Assessment Enhancement (Issue #6)

**FR-4.1**: The system MUST include domain-specific keywords in complexity assessment:
- MEDIUM keywords: soar, actr, activation, retrieval, reasoning, agentic, marketplace, aurora, research, analyze, compare, design, architecture
- COMPLEX keywords: pipeline, orchestration, phase, assessment, spreading activation

**FR-4.2**: The system MUST detect multi-question queries by counting question marks.

**FR-4.3**: The system MUST boost complexity score by +0.3 (capped at 1.0) if query contains 2+ question marks.

**FR-4.4**: Complexity thresholds MUST be: SIMPLE (< 0.4), MEDIUM (0.4-0.7), COMPLEX (>= 0.7).

**FR-4.5**: Confidence score MUST reflect number and quality of keyword matches.

**Implementation Files**:
- `packages/soar/src/aurora_soar/phases/assess.py` - Update MEDIUM_KEYWORDS and COMPLEX_KEYWORDS sets

**Code Example**:
```python
MEDIUM_KEYWORDS.update({
    # Domain terms
    "soar", "actr", "activation", "retrieval", "reasoning",
    "agentic", "marketplace", "aurora",
    # Scope indicators
    "research", "analyze", "compare", "design", "architecture",
    # Multi-part indicators
    "list all", "find all", "explain how", "show me"
})

# Add multi-question detection
def _count_questions(query: str) -> int:
    return query.count("?")

# Boost score if multiple questions
if _count_questions(query) >= 2:
    score = min(score + 0.3, 1.0)  # MEDIUM or COMPLEX
```

---

### FR-5: Auto-Escalation Logic (Issue #9)

**FR-5.1**: The system MUST check complexity assessment confidence after initial assessment.

**FR-5.2**: If confidence < 0.6, the system MUST trigger escalation logic.

**FR-5.3**: In `--non-interactive` mode, the system MUST automatically escalate to SOAR without user prompt.

**FR-5.4**: In interactive mode (default), the system MUST prompt user: "Low confidence. Use SOAR 9-phase pipeline? [y/N]"

**FR-5.5**: If user confirms (y), the system MUST execute SOAR pipeline regardless of complexity score.

**FR-5.6**: If user declines (N), the system MUST continue with assessed complexity level.

**FR-5.7**: The system MUST log escalation decisions for transparency.

**Implementation Files**:
- `packages/cli/src/aurora_cli/execution.py` - Add confidence check in execute_with_auto_escalation() method

**Code Example**:
```python
def execute_with_auto_escalation(self, query: str):
    assessment = self._assess_complexity(query)

    # NEW: Check confidence threshold
    if assessment.confidence < 0.6:
        if self.interactive:
            # Prompt user
            choice = click.confirm(
                f"Low confidence ({assessment.confidence:.2f}). Use SOAR 9-phase pipeline for better accuracy?",
                default=False
            )
            if choice:
                return self.execute_soar(query)
        else:
            # Auto-escalate in non-interactive mode
            logger.info(f"Auto-escalating to SOAR (low confidence: {assessment.confidence:.2f})")
            return self.execute_soar(query)

    # Continue with assessed complexity
    if assessment.complexity == "COMPLEX":
        return self.execute_soar(query)
    else:
        return self.execute_direct_llm(query)
```

---

### FR-6: Budget Management Commands (Issue #10)

**FR-6.1**: The system MUST implement `aur budget` command group with subcommands.

**FR-6.2**: `aur budget` (no subcommand) MUST show current spending, budget limit, and remaining balance.

**FR-6.3**: `aur budget set <amount>` MUST update budget limit in `~/.aurora/budget_tracker.json`.

**FR-6.4**: `aur budget reset` MUST set total spent back to $0.00.

**FR-6.5**: `aur budget history` MUST display table of past queries with timestamps, query text, cost, and status.

**FR-6.6**: The system MUST check budget before making API calls during query execution.

**FR-6.7**: If estimated cost exceeds remaining budget, the system MUST block the query and show clear error.

**Implementation Files**:
- `packages/cli/src/aurora_cli/commands/budget.py` - New file with budget command group
- `packages/cli/src/aurora_cli/main.py` - Register budget command group
- `packages/cli/src/aurora_cli/execution.py` - Add budget check before LLM calls

**Code Example**:
```python
# File: packages/cli/src/aurora_cli/commands/budget.py
@click.group()
def budget():
    """Manage cost budget and spending."""
    pass

@budget.command()
def show():
    """Show current budget and spending."""
    tracker = CostTracker()
    click.echo(f"Spent: ${tracker.total_spent:.4f}")
    click.echo(f"Budget: ${tracker.budget:.4f}")
    click.echo(f"Remaining: ${tracker.budget - tracker.total_spent:.4f}")

@budget.command()
@click.argument("amount", type=float)
def set(amount):
    """Set budget limit."""
    tracker = CostTracker()
    tracker.set_budget(amount)
    click.echo(f"✓ Budget limit set to ${amount:.4f}")

@budget.command()
def reset():
    """Reset spending to $0."""
    tracker = CostTracker()
    tracker.reset_spending()
    click.echo("✓ Spending reset to $0.0000")

@budget.command()
def history():
    """Show query history with costs."""
    tracker = CostTracker()
    history = tracker.get_history()
    # Display table with rich formatting
```

---

### FR-7: Error Handling with Debug Mode (Issue #11)

**FR-7.1**: The system MUST implement `--debug` global flag for all commands.

**FR-7.2**: By default (no --debug), the system MUST catch all exceptions and show user-friendly error messages.

**FR-7.3**: Error messages MUST categorize errors by type: authentication, API, network, configuration, or unexpected.

**FR-7.4**: Error messages MUST include actionable solutions or next steps.

**FR-7.5**: When `--debug` flag is used, the system MUST display full Python stack traces.

**FR-7.6**: Authentication errors MUST show clear message with link to get API key.

**FR-7.7**: Network errors MUST suggest checking internet connection and API status.

**Implementation Files**:
- `packages/cli/src/aurora_cli/main.py` - Add --debug flag, implement error wrapper decorator
- All command files - Wrap command functions with error handler

**Code Example**:
```python
# File: packages/cli/src/aurora_cli/main.py
@click.group()
@click.option('--debug', is_flag=True, help='Show full stack traces on errors')
@click.pass_context
def cli(ctx, debug):
    ctx.obj = {'debug': debug}

# Wrap all commands with error handler
def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AuthenticationError as e:
            click.echo("✗ Authentication failed\n")
            click.echo("Invalid API key.\n")
            click.echo("Solutions:")
            click.echo("  1. Check your API key: export ANTHROPIC_API_KEY=sk-ant-...")
            click.echo("  2. Get a new key at: https://console.anthropic.com")
            click.echo("  3. Update config: aur init\n")
            if click.get_current_context().obj.get('debug'):
                raise
            else:
                click.echo("Run with --debug for technical details")
                sys.exit(1)
        except Exception as e:
            click.echo(f"✗ Unexpected error: {e}")
            if click.get_current_context().obj.get('debug'):
                raise
            click.echo("Run with --debug for details")
            sys.exit(1)
    return wrapper
```

---

## 5. Non-Goals (Out of Scope for Phase 1)

**Explicitly NOT included in this PRD** (deferred to Phase 2 - separate PRD):

1. **MCP auto-configuration** (Issue #14) - Manual MCP setup acceptable for v0.2.1
2. **MCP tool routing improvements** - Phase 2 will address natural language routing
3. **Output polish and logging cleanup** (Issue #8) - Functional output sufficient for Phase 1
4. **Parse error summaries** (Issue #5) - Warnings don't block functionality
5. **`aur mem clear` command** (Issue #12) - Workaround exists (delete DB file)
6. **Post-install verification** (Issue #1) - Nice-to-have UX improvement
7. **Uninstall documentation** (Issue #13) - Low priority documentation task
8. **Real SOAR implementation in MCP** - Requires 16-24 hours, separate effort
9. **Git history integration for activation** - Future enhancement
10. **Multi-language tree-sitter support** - Python-only acceptable for now

**Phase Boundary**: Phase 1 ends when all P0-P1 issues are fixed and basic CLI workflow works. Phase 2 begins after v0.2.1 release.

---

## 6. Design Considerations

### Database Migration Strategy

**Problem**: Users may have existing `aurora.db` files in project directories.

**Solution**: During `aur init`, detect and offer migration:
```bash
aur init
# Output:
# ⚠ Found existing database: /home/user/project/aurora.db
# Migrate data to ~/.aurora/memory.db? [Y/n]: _
```

If user confirms:
- Copy all chunks and activations to new location
- Rename old DB to `aurora.db.backup`
- Show migration summary (X chunks migrated)

---

### Activation Score Initialization

**Problem**: Newly indexed chunks have base_level=0.0, causing normalization issues.

**Solution**: Initialize with frequency-based activation:
- Parse history: Use term frequency in code as initial activation
- First access: Set base_level to 0.5 (baseline activation)
- Subsequent accesses: Use ACT-R decay formula

This ensures varied activation scores from the start.

---

### Budget Enforcement Point

**Problem**: When should budget checks occur?

**Solution**: Check at two points:
1. **Before query execution**: Estimate cost based on query length + expected retrieval
2. **After LLM call**: Record actual cost, update budget tracker

If pre-check fails → block immediately with clear message
If post-check reveals overage → warn but complete the query (already paid)

---

### Error Message Hierarchy

**Levels**:
1. **User-facing** (default): Clear, actionable, no technical jargon
2. **Technical** (--debug): Full stack traces, variable values, system state

**Categories**:
- Authentication: API key issues → Show key format, link to provider
- API: Rate limits, quotas → Suggest retry, check status page
- Network: Timeouts, connection errors → Check internet, retry
- Configuration: Missing files, invalid config → Show expected format
- Unexpected: Unknown errors → Collect logs, report issue

---

## 7. Technical Considerations

### Architecture Impact

**Current Architecture**:
```
CLI Commands → Memory Manager → Store/Retriever/Activation Engine
            ↓
         Query Executor → LLM Client
                      ↓
                 SOAR Orchestrator (9 phases)
```

**Changes Required**:
- Add config layer between CLI and Memory Manager (database path)
- Add retrieval step before LLM calls in Query Executor
- Add budget check before LLM calls
- Add error handler wrapper around all commands

**No breaking changes** - all changes are additions or fixes, not API redesigns.

---

### Test Strategy

**Critical Insight**: Unit tests passed, but E2E/integration tests missing.

**New Test Layers Required**:

1. **E2E Tests** (15 tests) - Full user workflows
   - `test_e2e_new_user_workflow.py` - Init → index → search → query
   - `test_e2e_database_persistence.py` - Data survives commands
   - `test_e2e_search_accuracy.py` - Search returns relevant results
   - `test_e2e_query_uses_index.py` - Query retrieves indexed data
   - `test_e2e_complexity_assessment.py` - SOAR triggers correctly

2. **Integration Tests** (10 tests) - Multi-component interactions
   - `test_integration_db_path_consistency.py` - All commands use same DB
   - `test_integration_activation_tracking.py` - record_access() called
   - `test_integration_retrieval_before_llm.py` - Context passed to LLM
   - `test_integration_budget_enforcement.py` - Queries blocked on limit
   - `test_integration_auto_escalation.py` - Low confidence → SOAR

**Test-Driven Development Approach**:
- Day 1-2: Write all E2E and integration tests (they FAIL initially)
- Day 3-6: Fix code until tests PASS
- Never regress again (tests in CI/CD)

---

### Dependencies

**Required Packages** (already in dependencies):
- `click` (CLI framework)
- `rich` (output formatting)
- `sqlite3` (database)
- `anthropic` or `openai` (LLM clients)

**No new dependencies required** - all fixes use existing packages.

---

### Performance Targets

**No performance regression** - these are fixes, not optimizations:
- Database path unification: No performance impact
- Activation tracking: ~1-2ms overhead per search (acceptable)
- Query retrieval: Adds 50-200ms for 10 chunks (acceptable)
- Budget checks: <1ms (file read)
- Error handling: No performance impact

**Expected improvements**:
- Search accuracy improves (correct activation scores)
- Query accuracy improves (uses indexed data)

---

### Backward Compatibility

**Config File Changes**:
- New `~/.aurora/config.json` format includes `db_path` field
- Old configs (if exist) will be migrated automatically during `aur init`

**Database Schema**:
- No schema changes required
- Existing activations table works as-is (just need to update values)

**API/CLI Interface**:
- All existing commands work the same
- New `aur budget` command added (no breaking changes)
- New `--debug` flag added (optional, doesn't break existing usage)

---

## 8. Success Metrics

### Quantitative Metrics

1. **Test Pass Rate**: 100% of new E2E and integration tests PASS
2. **Search Variety**: At least 80% of search results differ for different queries (measured by comparing top 5 results)
3. **Activation Score Distribution**: Standard deviation of activation scores > 0.1 (not all equal)
4. **Query Retrieval Rate**: 100% of queries retrieve at least 1 chunk from indexed data when relevant
5. **Complexity Assessment Accuracy**: Domain queries (SOAR, ACT-R, agentic) score >= 0.4 (MEDIUM or COMPLEX)
6. **Error Handling Coverage**: 0 stack traces shown without --debug flag

### Qualitative Metrics

1. **User Workflow Completion**: User can complete `TESTING_AURORA_FROM_SCRATCH.md` without errors
2. **Error Message Clarity**: Non-technical users understand what went wrong and how to fix it
3. **Budget Transparency**: Users can see and control API spending
4. **Database Reliability**: No confusion about data location, no data loss

### Sprint Checkpoints

**Day 2 Checkpoint**:
- ✅ 15 E2E tests written and FAILING (proves bugs exist)
- ✅ 10 integration tests written and FAILING

**Day 4 Checkpoint**:
- ✅ P0 tests PASSING (database, search, query retrieval)
- ✅ `aur init → index → search → query` works end-to-end

**Day 6 Checkpoint** (Sprint Completion):
- ✅ All P0 + P1 tests PASSING
- ✅ SOAR triggers on complex queries
- ✅ Budget enforced
- ✅ Clean error messages
- ✅ Ready for v0.2.1 release

---

## 9. Open Questions

### Q1: Should we preserve local `aurora.db` files?

**Options**:
- A) Always migrate to `~/.aurora/memory.db`, delete local
- B) Keep as backup, warn user
- C) Let user choose during `aur init`

**Recommendation**: Option C (user choice) - safest, respects user data

**Resolution Needed By**: Day 1 (before implementation starts)

---

### Q2: What should default budget limit be?

**Options**:
- A) $10.00 (conservative)
- B) $50.00 (moderate)
- C) Unlimited (no default limit)

**Recommendation**: Option A ($10.00) - prevents surprise charges, easy to increase

**Resolution Needed By**: Day 5 (before budget command implementation)

---

### Q3: Should --debug be persistent across commands?

**Options**:
- A) Always require flag for each command
- B) Save preference in config file
- C) Environment variable `AURORA_DEBUG=1`

**Recommendation**: Option A + C (flag takes precedence, env var for persistent debugging)

**Resolution Needed By**: Day 6 (before error handling implementation)

---

### Q4: How verbose should complexity assessment be by default?

**Options**:
- A) Silent (only show final decision)
- B) Brief (one line: "Complexity: SIMPLE, using direct LLM")
- C) Detailed (show score, confidence, keywords matched)

**Recommendation**: Option B for default, Option C with `--verbose` flag

**Resolution Needed By**: Day 5 (before complexity fixes)

---

## 10. Testing & Verification Strategy

### Test Pyramid (Fixed)

**New test structure** (proper pyramid):
```
E2E Tests (15 tests)           ← Full user workflows
  ├─ test_new_user_onboarding
  ├─ test_database_persistence
  ├─ test_search_accuracy
  ├─ test_query_uses_index
  └─ test_complexity_triggers_soar

Integration Tests (50 tests)   ← Multi-component interactions
  ├─ test_db_path_consistency
  ├─ test_activation_tracking
  ├─ test_retrieval_before_llm
  ├─ test_budget_enforcement
  └─ test_auto_escalation

Unit Tests (2,369 tests)       ← Isolated component tests
  └─ (existing tests, mostly good)
```

---

### E2E Test Specifications

**Test 1: New User Workflow** (test_e2e_new_user_workflow.py)
```python
def test_new_user_complete_workflow():
    """Simulate full new user experience"""
    # Clean slate
    shutil.rmtree(Path.home() / ".aurora", ignore_errors=True)

    # 1. Initialize Aurora
    result = subprocess.run(["aur", "init"], input="test-key\n", text=True)
    assert result.returncode == 0
    assert (Path.home() / ".aurora" / "memory.db").exists()

    # 2. Index codebase
    result = subprocess.run(["aur", "mem", "index", "."], capture_output=True)
    assert result.returncode == 0
    assert "chunks" in result.stdout

    # 3. Check stats
    result = subprocess.run(["aur", "mem", "stats"], capture_output=True)
    assert "Total Chunks: " in result.stdout
    chunk_count = int(re.search(r"Total Chunks: (\d+)", result.stdout).group(1))
    assert chunk_count > 0, "No chunks indexed"

    # 4. Search
    result = subprocess.run(["aur", "mem", "search", "function"], capture_output=True)
    assert result.returncode == 0
    assert len(result.stdout.splitlines()) > 0, "No search results"

    # 5. Query
    result = subprocess.run(["aur", "query", "what is a HybridRetriever?"], capture_output=True)
    assert result.returncode == 0
    assert "HybridRetriever" in result.stdout, "Query didn't use indexed data"
```

---

### Integration Test Specifications

**Test 2: Database Path Consistency** (test_integration_db_path_consistency.py)
```python
def test_all_commands_use_same_database(tmp_path):
    """Verify index, search, query all use config DB path"""
    db_path = tmp_path / "test.db"
    config_path = tmp_path / "config.json"

    # Create config with specific DB path
    config = {"db_path": str(db_path)}
    config_path.write_text(json.dumps(config))

    # Initialize components with config
    config_obj = Config(config_path)
    store = SQLiteStore(config_obj.get_db_path())
    manager = MemoryManager(store, registry, embeddings)

    # Index files
    manager.index_directory("/path/to/code")

    # Verify DB file exists at correct location
    assert db_path.exists(), f"DB not created at {db_path}"

    # Verify stats use same DB
    stats = manager.get_stats()
    assert stats.total_chunks > 0

    # Verify search uses same DB
    results = manager.search("test")
    assert len(results) > 0

    # Verify all data came from same DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM chunks")
    db_chunk_count = cursor.fetchone()[0]
    assert db_chunk_count == stats.total_chunks
```

---

### Unit Test Updates

**Existing unit tests** need minimal updates:
- Replace hardcoded DB paths with config-based paths
- Mock `record_access()` calls in retriever tests
- Add tests for new budget commands
- Add tests for error handling decorators

**Estimated test update effort**: 3 hours (most tests don't need changes)

---

### Manual Testing Checklist

After all automated tests pass, perform manual verification:

**Smoke Test Checklist**:
- [ ] Fresh install works (`pip install -e .`)
- [ ] `aur --help` shows all commands
- [ ] `aur init` creates config and DB in correct location
- [ ] `aur mem index .` indexes current directory without errors
- [ ] Activation scores initialized from Git history at FUNCTION level (not all 0.0)
- [ ] Functions in same file have DIFFERENT activation scores based on edit history
- [ ] Git metadata (git_hash, last_modified, commit_count) stored in chunks
- [ ] `aur mem stats` shows correct chunk count
- [ ] `aur mem search "query"` returns varied results for different queries
- [ ] `aur query "question"` uses indexed data in answer
- [ ] Complex query triggers SOAR pipeline
- [ ] `aur budget` shows spending
- [ ] Invalid API key shows clean error (no stack trace)
- [ ] `aur query "test" --debug` shows stack trace with debug flag

---

## 11. Implementation Plan (6 Days)

### Day 1-2: Write Failing Tests (16 hours)

**Goal**: Document all broken behavior with tests that FAIL

**Tasks**:
1. **E2E Tests** (9 hours):
   - `test_e2e_new_user_workflow.py` - Full onboarding (fails on DB path)
   - `test_e2e_database_persistence.py` - Data survives commands (fails)
   - `test_e2e_search_accuracy.py` - Search returns relevant results (fails)
   - `test_e2e_query_uses_index.py` - Query retrieves indexed data (fails)
   - `test_e2e_complexity_assessment.py` - SOAR triggers correctly (fails)
   - `test_e2e_git_bla_initialization.py` - Git history used for BLA (fails)

2. **Integration Tests** (9 hours):
   - `test_integration_db_path_consistency.py` - All commands use same DB
   - `test_integration_activation_tracking.py` - record_access() called
   - `test_integration_retrieval_before_llm.py` - Context passed to LLM
   - `test_integration_budget_enforcement.py` - Queries blocked on limit
   - `test_integration_auto_escalation.py` - Low confidence → SOAR
   - `test_integration_git_signal_extraction.py` - Git signals extracted correctly

**Deliverable**: Test suite that FAILS comprehensively (proves bugs exist)

**Verification**: `pytest tests/e2e/ tests/integration/` shows 28 FAILED tests

---

### Day 3-4: P0 Fixes (18 hours)

**Goal**: Make basic functionality work (search, query, Git-based activation)

**Task 1: Database Path Unification** (5 hours)
- Update `Config` class with `get_db_path()` method
- Update all commands to use `config.get_db_path()`
- Add migration logic to `aur init`
- Test: P0 DB path tests PASS

**Task 2: Git-Based BLA Initialization (FUNCTION-LEVEL)** (6 hours)
- Create `git.py` module with `GitSignalExtractor` class
- Implement `get_function_commit_times()` using `git blame -L <start>,<end>`
- Implement `_get_commit_timestamp()` to get timestamps for commit SHAs
- Implement `calculate_bla()` with ACT-R formula
- Update `memory_manager.index_file()` to extract Git signals PER FUNCTION
- Pass `line_start` and `line_end` from tree-sitter chunks to Git extractor
- Update chunk metadata to store `git_hash`, `last_modified`, and `commit_count`
- Update activation initialization to use function-specific BLA
- Handle non-Git directories gracefully (fallback to base_level=0.5)
- Test: Activation scores vary, functions in same file have DIFFERENT scores, Git metadata present

**Task 3: Activation Tracking Fix** (2 hours)
- Add `record_access()` calls in `memory_manager.search()`
- Verify activation scores update in database
- Test: Search results vary, activation scores increase with access

**Task 4: Query Retrieval Integration** (3 hours)
- Add retrieval step in `execute_direct_llm()`
- Format chunks as LLM context
- Pass context to LLM prompt
- Test: Query answers reference indexed code

**Task 5: Fix Tests** (2 hours)
- Update existing unit tests with new DB paths
- Ensure E2E tests for P0 now PASS

**Checkpoint**: Run `aur init → index → search → query` - should work ✓

**Verification**:
- `pytest tests/e2e/test_e2e_new_user_workflow.py` PASSES
- `pytest tests/e2e/test_e2e_search_accuracy.py` PASSES
- `pytest tests/e2e/test_e2e_query_uses_index.py` PASSES
- `pytest tests/e2e/test_e2e_git_bla_initialization.py` PASSES
- `pytest tests/integration/test_integration_git_signal_extraction.py` PASSES

---

### Day 5-6: P1 Fixes (16 hours)

**Goal**: SOAR triggers, budget works, errors clean

**Task 1: Complexity Assessment** (4 hours)
- Add domain keywords to `assess.py`
- Add multi-question detection
- Update complexity thresholds
- Test: Domain queries score MEDIUM/COMPLEX

**Task 2: Auto-Escalation Logic** (3 hours)
- Implement confidence threshold check
- Add interactive prompt for escalation
- Add auto-escalation in non-interactive mode
- Test: Low confidence queries escalate

**Task 3: Budget Command** (4 hours)
- Implement `aur budget` command group
- Add show/set/reset/history subcommands
- Add budget check before LLM calls
- Test: Budget enforced, commands work

**Task 4: Error Handling** (5 hours)
- Add `--debug` flag to CLI
- Implement error handler decorator
- Wrap all commands with error handler
- Categorize errors and add helpful messages
- Test: Clean errors without --debug, traces with --debug

**Checkpoint**: SOAR triggers, budget enforced, clean errors ✓

**Verification**:
- `pytest tests/e2e/test_e2e_complexity_assessment.py` PASSES
- `pytest tests/integration/test_integration_auto_escalation.py` PASSES
- `pytest tests/integration/test_integration_budget_enforcement.py` PASSES
- All P0 + P1 tests PASS (25/25)

---

## 12. Release Criteria (v0.2.1)

### Must Have (Blocking Release)

- ✅ All 28 E2E and integration tests PASS
- ✅ User can complete `TESTING_AURORA_FROM_SCRATCH.md` without errors
- ✅ Database path unified (all commands use `~/.aurora/memory.db`)
- ✅ Git-based BLA initialization working at FUNCTION level (activation scores vary from start)
- ✅ Functions in same file have DIFFERENT activation scores based on their individual edit history
- ✅ Git metadata (git_hash, last_modified, commit_count) stored in chunks
- ✅ Search returns varied results (not identical for all queries)
- ✅ Query retrieves from indexed data
- ✅ Complexity assessment uses domain keywords
- ✅ Auto-escalation works in non-interactive mode
- ✅ `aur budget` command implemented
- ✅ Clean error messages (no stack traces by default)
- ✅ Documentation updated (CHANGELOG, troubleshooting)

### Should Have (Important but not blocking)

- ✅ Migration tool for local `aurora.db` files
- ✅ Budget history shows useful information
- ✅ Error messages include actionable solutions
- ✅ Verbose mode shows complexity assessment details

### Nice to Have (Defer if needed)

- ⚠️ Parse error summaries (Issue #5) - Phase 2
- ⚠️ Post-install verification (Issue #1) - Phase 2
- ⚠️ Output polish (Issue #8) - Phase 2

---

## Appendix A: Issue Cross-Reference

| Issue # | Priority | Description | Functional Requirements |
|---------|----------|-------------|------------------------|
| #2 | P0 | Database path confusion | FR-1.1 - FR-1.6 |
| #4 | P0 | Search returns identical results | FR-2.1 - FR-2.6 |
| #15 | P0 | Query doesn't use indexed data | FR-3.1 - FR-3.6 |
| #16 | P0 | Git-based BLA initialization missing | FR-8.1 - FR-8.10 |
| #6 | P1 | Complexity assessment broken | FR-4.1 - FR-4.5 |
| #9 | P1 | Auto-escalation not working | FR-5.1 - FR-5.7 |
| #10 | P1 | Budget command missing | FR-6.1 - FR-6.7 |
| #11 | P1 | Stack traces on errors | FR-7.1 - FR-7.7 |

---

## Appendix B: Test File Locations

**E2E Tests**: `tests/e2e/`
- `test_e2e_new_user_workflow.py`
- `test_e2e_database_persistence.py`
- `test_e2e_search_accuracy.py`
- `test_e2e_query_uses_index.py`
- `test_e2e_complexity_assessment.py`
- `test_e2e_git_bla_initialization.py`

**Integration Tests**: `tests/integration/`
- `test_integration_db_path_consistency.py`
- `test_integration_activation_tracking.py`
- `test_integration_retrieval_before_llm.py`
- `test_integration_budget_enforcement.py`
- `test_integration_auto_escalation.py`
- `test_integration_git_signal_extraction.py`

**Unit Tests** (updates only): `tests/unit/`
- `test_config.py` - Add DB path tests
- `test_memory_manager.py` - Add record_access tests
- `test_git.py` - Add Git signal extraction tests (new)
- `test_budget.py` - Add budget command tests
- `test_error_handling.py` - Add error decorator tests

---

## Appendix C: Configuration File Format

**Location**: `~/.aurora/config.json`

**Format**:
```json
{
  "version": "0.2.1",
  "db_path": "/home/user/.aurora/memory.db",
  "default_provider": "anthropic",
  "budget_limit": 10.00,
  "auto_escalation": true,
  "interactive": true
}
```

**Fields**:
- `version`: Aurora version that created config
- `db_path`: Absolute path to SQLite database
- `default_provider`: LLM provider (anthropic, openai, ollama)
- `budget_limit`: Default budget in USD
- `auto_escalation`: Enable low-confidence escalation
- `interactive`: Show prompts (false in CI/CD)

---

## Appendix D: Error Message Templates

**Authentication Error**:
```
✗ Authentication failed

Invalid API key.

Solutions:
  1. Check your API key: export ANTHROPIC_API_KEY=sk-ant-...
  2. Get a new key at: https://console.anthropic.com
  3. Update config: aur init

Run with --debug for technical details
```

**Budget Exceeded Error**:
```
✗ Budget limit exceeded

Spent: $9.98 | Budget: $10.00 | Estimated cost: $0.23

To continue, increase your budget:
  aur budget set 20.00

Or reset spending:
  aur budget reset
```

**Database Not Found Error**:
```
✗ Database not found

Aurora database not initialized.

Run:
  aur init

This will create ~/.aurora/memory.db and set up configuration.
```

---

**END OF PRD-0010**
