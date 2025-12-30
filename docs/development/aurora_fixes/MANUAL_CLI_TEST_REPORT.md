# Manual CLI Test Report
**Date**: 2025-12-29
**Purpose**: Verify actual CLI functionality after Phase 2A (not just test pass rates)
**Environment**: Clean `~/.aurora/` directory, fresh Aurora installation

---

## Test Methodology

1. Clean environment: `rm -rf ~/.aurora`
2. Execute each CLI command with pure bash
3. Document actual behavior vs expected behavior
4. Record all outputs without masking or modification

---

## Test Results Summary

| Test | Command | Status | Notes |
|------|---------|--------|-------|
| 1 | `aur --help` | ✅ PASSED | Help text displays correctly |
| 2 | `aur --verify` (from help) | ❌ FAILED | Option doesn't exist (should be `aur verify` command) |
| 3 | `aur --version` | ✅ PASSED | Shows v0.2.0 |
| 4 | `aur init` | ✅ PASSED | Creates config at ~/.aurora/config.json |
| 5 | Config validation | ✅ PASSED | Valid JSON with all sections |
| 6 | `aur mem index <file>` | ❌ FAILED | Returns 0 files, 0 chunks for single file |
| 6b | `aur mem index --limit` | ❌ FAILED | Option doesn't exist (help mentions it) |
| 7 | `aur mem index <dir>` | ✅ PASSED | Indexed 29 files, 361 chunks in 66.90s |
| 8 | `aur mem stats` | ✅ PASSED | Shows 361 chunks, 29 files, 1.57 MB |
| 9 | `aur mem search` | ✅ PASSED | Scores now vary: Semantic 0.547-0.590, Hybrid 0.819-0.836 (Fixed 2025-12-30) |
| 10 | `aur query --dry-run` (SOAR) | ✅ PASSED | Correctly classified as MEDIUM (0.720) |
| 11 | `aur query --dry-run` (simple) | ✅ PASSED | Correctly classified as SIMPLE (0.250) |
| 12 | `aur query --dry-run` (complex) | ❌ FAILED | 3 domain keywords → MEDIUM (0.375), should be COMPLEX |
| 13 | `aur config show` | ❌ FAILED | Command doesn't exist |
| 14 | `aur verify` | ✅ PASSED | All components verified |
| 15 | `aur budget status` | ❌ FAILED | Should be `aur budget show` |
| 16 | `aur budget show` | ✅ PASSED | Shows $10 budget, $0 spent |
| 17 | `aur headless --dry-run` | ✅ PASSED | Configuration validation works |

**Pass Rate**: 10/17 (58.8%)
**Critical Failures**: 2 (complexity assessment, single file indexing)
**Documentation Errors**: 3 (help mentions non-existent options/commands)

---

## Detailed Test Results

### TEST 1: Help Display ✅
```bash
$ aur --help
```
**Result**: PASSED - Help text displays correctly with all commands listed

---

### TEST 2: Verify Option (from help) ❌
```bash
$ aur --verify
```
**Result**: FAILED
**Error**: `Error: No such option: --verify`
**Issue**: Help text shows `aur --verify` but actual command is `aur verify` (no dashes)
**Impact**: Documentation inconsistency confuses users

---

### TEST 3: Version Display ✅
```bash
$ aur --version
```
**Result**: PASSED
**Output**: `aur, version 0.2.0`

---

### TEST 4-5: Init and Config Creation ✅
```bash
$ aur init
```
**Result**: PASSED
**Output**:
```
✓ Created configuration at /home/hamr/.aurora/config.json

Configuration:
  Provider   anthropic
  Model      claude-sonnet-4-20250514
  API Key    Not set
  Threshold  0.6

Memory Store:
  Database: /home/hamr/.aurora/memory.db (will be created on first index)

Budget Tracking:
  Monthly Budget   $10.00
  Current Period   2025-12
  Spent            $0.00

✓ AURORA initialized successfully!
```

**Config Contents**:
```json
{
    "llm": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "anthropic_api_key": null,
        "openai_api_key": null
    },
    "escalation": {
        "llm_verification_threshold": 0.6
    },
    "memory": {
        "embedding_model": "all-MiniLM-L6-v2"
    },
    "database": {
        "path": "/home/hamr/.aurora/memory.db"
    },
    "budget": {
        "monthly_limit": 10.0,
        "tracker_path": "/home/hamr/.aurora/budget_tracker.json"
    }
}
```

---

### TEST 6: Index Single File ❌
```bash
$ aur mem index packages/core/src/aurora_core/storage.py
```
**Result**: FAILED
**Output**:
```
╭─── Index Summary ───╮
│ ✓ Indexing complete │
│                     │
│ Files indexed: 0    │
│ Chunks created: 0   │
│ Duration: 0.51s     │
│ Errors: 0           │
╰─────────────────────╯
```
**Issue**: Indexing single file returns 0 files, 0 chunks despite file existing
**Impact**: CRITICAL - Cannot index individual files, only directories

---

### TEST 6b: Index with --limit Flag ❌
```bash
$ aur mem index packages/core/src/aurora_core/ --limit 5
```
**Result**: FAILED
**Error**: `Error: No such option: --limit`
**Issue**: `aur mem index --help` mentions `--limit` but option doesn't exist
**Impact**: Documentation inconsistency

---

### TEST 7: Index Directory ✅
```bash
$ aur mem index packages/core/src/aurora_core/
```
**Result**: PASSED
**Output**:
```
  Indexing packages/core/src/aurora_core ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

╭─── Index Summary ───╮
│ ✓ Indexing complete │
│                     │
│ Files indexed: 29   │
│ Chunks created: 361 │
│ Duration: 66.90s    │
│ Errors: 0           │
╰─────────────────────╯
```

---

### TEST 8: Memory Statistics ✅
```bash
$ aur mem stats
```
**Result**: PASSED
**Output**:
```
            Memory Store Statistics
┌────────────────────────────────┬────────────┐
│ Total Chunks                   │ 361        │
│ Total Files                    │ 29         │
│ Database Size                  │ 1.57 MB    │
│                                │            │
│ Languages                      │            │
│   python                       │ 361 chunks │
└────────────────────────────────┴────────────┘
```

---

### TEST 9: Memory Search ✅ PASSED (FIXED 2025-12-30)
```bash
$ aur mem search "activation scoring"
```
**Result**: PASSED - Scores now vary appropriately
**Output**:
```
Found 5 results for 'activation scoring'

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━┓
┃ File                              ┃ Type  ┃ Name               ┃ Lines ┃ Sc… ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━┩
│ retrieval.py                      │ code  │ ActivationRetriev… │ 100-… │ 0.… │
│ sqlite.py                         │ code  │ SQLiteStore.retri… │ 355-… │ 0.… │
│ sqlite.py                         │ code  │ SQLiteStore.recor… │ 509-… │ 0.… │
│ tracker.py                        │ code  │ CostTracker        │ 113-… │ 0.… │
│ sqlite.py                         │ code  │ SQLiteStore        │ 36-7… │ 0.… │
└───────────────────────────────────┴───────┴────────────────────┴───────┴─────┘

Average scores:
  Activation: 1.000
  Semantic:   0.552
  Hybrid:     0.821
```

**Fix Applied** (Sprint 1 - 2025-12-30):
Three bugs were fixed in production code:
1. **Bug 1** (`sqlite.py`): `retrieve_by_activation()` now attaches `base_level` to chunks
2. **Bug 2** (`hybrid_retriever.py`): Changed `chunk.embedding` to `chunk.embeddings`
3. **Bug 3** (`hybrid_retriever.py`): `_normalize_scores()` returns original scores when all equal

**Verification Evidence**:
- Semantic scores vary: 0.547-0.590 across different queries
- Hybrid scores vary: 0.819-0.836 across different queries
- Database BLA values: -6.7995 to 0.4850 (241 distinct values)
- Access counts: 1-21 (10 distinct values)
- Functions in same file have different scores (sqlite.py: 3-21 accesses)

**E2E Tests**: 7/7 tests pass in `tests/e2e/test_e2e_search_scoring.py`

**Previous Issue** (before fix):
- All scores were 1.000 due to normalization bug and missing activation attribute

---

### TEST 10: Query Complexity (SOAR keyword) ✅
```bash
$ aur query "What is SOAR reasoning architecture?" --dry-run
```
**Result**: PASSED
**Output**:
```
Escalation Decision:
 Query       What is SOAR reasoning architecture?
 Complexity  MEDIUM
 Score       0.720
 Confidence  0.712
 Method      keyword
 Decision    Would use: AURORA
 Reasoning   Keyword-based classification (borderline or low confidence). LLM
             verification recommended but not available.

Complexity: MEDIUM
Score: 0.720
Confidence: 0.712
```

**Notes**: Correctly identifies "SOAR" as MEDIUM complexity keyword

---

### TEST 11: Query Complexity (Simple) ✅
```bash
$ aur query "What is a function?" --dry-run
```
**Result**: PASSED
**Output**:
```
Escalation Decision:
 Query       What is a function?
 Complexity  SIMPLE
 Score       0.250
 Confidence  0.283
 Method      keyword
 Decision    Would use: Direct LLM
 Reasoning   Keyword-based classification (borderline or low confidence). LLM
             verification recommended but not available.

Complexity: SIMPLE
Score: 0.250
Confidence: 0.283
```

---

### TEST 12: Query Complexity (Multiple Domain Keywords) ❌
```bash
$ aur query "Explain the interaction between SOAR phases, ACT-R activation scoring, and Aurora memory retrieval in detail" --dry-run
```
**Result**: FAILED
**Output**:
```
Escalation Decision:
 Query       Explain the interaction between SOAR phases, ACT-R activation
             scoring, and Aurora memory retrieval in detail
 Complexity  MEDIUM
 Score       0.375
 Confidence  0.588
 Method      keyword
 Decision    Would use: Direct LLM
 Reasoning   Keyword-based classification (borderline or low confidence). LLM
             verification recommended but not available.

Complexity: MEDIUM
Score: 0.375
Confidence: 0.588
```

**Issues**:
1. Query contains 3 domain keywords: "SOAR", "ACT-R", "Aurora"
2. Score is 0.375 which is low
3. Classified as MEDIUM but should be COMPLEX
4. Decision is "Direct LLM" instead of "AURORA"

**Expected**: Query with multiple domain keywords + "in detail" should be COMPLEX (score > 0.6)

**Impact**: HIGH - Complex queries may bypass Aurora reasoning pipeline

---

### TEST 13: Config Show Command ❌
```bash
$ aur config show
```
**Result**: FAILED
**Error**: `Error: No such command 'config'.`
**Impact**: No CLI command to view current configuration (must read JSON file directly)

---

### TEST 14: Verify Installation ✅
```bash
$ aur verify
```
**Result**: PASSED
**Output**:
```
Checking AURORA installation...

✓ Core components (aurora.core)
✓ Context & parsing (aurora.context_code)
✓ SOAR orchestrator (aurora.soar)
✓ Reasoning engine (aurora.reasoning)
✓ CLI tools (aurora.cli)
✓ Testing utilities (aurora.testing)

✓ CLI available at /home/hamr/.local/bin/aur
✓ MCP server at /home/hamr/.local/bin/aurora-mcp

✓ Python version: 3.10.12

✓ ML dependencies (sentence-transformers)

✓ Config file exists at /home/hamr/.aurora/config.json

✓ AURORA is ready to use!
```

---

### TEST 15: Budget Status (Wrong Subcommand) ❌
```bash
$ aur budget status
```
**Result**: FAILED
**Error**: `Error: No such command 'status'.`
**Issue**: Should be `aur budget show`, not `status`
**Impact**: Low - User can find correct command via `--help`

---

### TEST 16: Budget Show ✅
```bash
$ aur budget show
```
**Result**: PASSED
**Output**:
```
Budget Status
  Period       2025-12
  Budget       $10.00
  Spent        $0.0000
  Remaining    $10.0000
  Consumed     0.0%
  Queries      0
```

---

### TEST 17: Headless Mode Validation ✅
```bash
$ aur headless /tmp/test_prompt.md --dry-run
```
**Result**: PASSED
**Output**:
```
Headless Mode Configuration:
  Prompt             /tmp/test_prompt.md
  Scratchpad         /tmp/test_prompt_scratchpad.md
  Budget             $5.00
  Max Iterations     10
  Required Branch    headless
  Allow Main         No

→ Dry run mode: validating configuration only
✓ Configuration valid
Prompt: test_prompt.md
Would create/use scratchpad: /tmp/test_prompt_scratchpad.md

Run without --dry-run to execute
```

---

## Critical Issues Requiring Immediate Attention

### ~~1. Search Scoring Completely Broken (CRITICAL)~~ RESOLVED 2025-12-30
**Status**: FIXED in Sprint 1
**Resolution**: Three bugs fixed in production code:
1. `sqlite.py`: `retrieve_by_activation()` now attaches `base_level` to chunks
2. `hybrid_retriever.py`: Changed `chunk.embedding` to `chunk.embeddings`
3. `hybrid_retriever.py`: `_normalize_scores()` returns original scores when all equal

**Verification**: Scores now vary (Semantic 0.547-0.590, Hybrid 0.819-0.836)
**E2E Tests**: 7/7 tests pass in `tests/e2e/test_e2e_search_scoring.py`

---

### 1. Complexity Assessment Fails for Multi-Keyword Queries (HIGH)
**Symptom**: Query with 3 domain keywords (SOAR, ACT-R, Aurora) classified as MEDIUM (0.375) instead of COMPLEX
**Impact**: Complex queries may bypass Aurora reasoning pipeline
**Files**:
- `packages/soar/src/aurora_soar/phases/assess.py` - keyword matching logic

**Root Cause Hypothesis**:
- Score calculation doesn't properly accumulate multiple keyword matches
- Thresholds may be incorrect (COMPLEX threshold too high)
- "in detail" phrase not being counted as complexity signal

**Verification**:
```bash
# Expected: COMPLEX (score > 0.6)
# Actual: MEDIUM (score = 0.375)
aur query "Explain the interaction between SOAR phases, ACT-R activation scoring, and Aurora memory retrieval in detail" --dry-run
```

---

### 2. Single File Indexing Broken (HIGH)
**Symptom**: Indexing single file returns 0 files, 0 chunks
**Impact**: Users cannot index individual files, must index entire directories
**Files**:
- `packages/cli/src/aurora_cli/commands/memory.py` - index command

**Root Cause Hypothesis**:
- File path handling may require trailing slash or directory path
- Tree-sitter parsing may fail silently for single file path
- File detection logic may expect directory structure

**Verification**:
```bash
# Expected: 1 file, N chunks
# Actual: 0 files, 0 chunks
aur mem index packages/core/src/aurora_core/storage.py
```

---

## Documentation Inconsistencies

### 1. `--verify` Option vs `verify` Command
- Help text shows: `aur --verify`
- Actual command: `aur verify` (no dashes)
- Fix: Update help text to show correct command

### 2. `--limit` Option Doesn't Exist
- `aur mem index --help` mentions `--limit` option
- Option doesn't exist when used
- Fix: Either implement option or remove from help

### 3. `budget status` vs `budget show`
- Natural command: `aur budget status`
- Actual command: `aur budget show`
- Fix: Add `status` as alias to `show`

---

## Features Working Correctly

1. ✅ Help display and command listing
2. ✅ Version information
3. ✅ Configuration initialization (`aur init`)
4. ✅ Directory indexing (29 files in 66.90s)
5. ✅ Memory statistics display
6. ✅ Installation verification
7. ✅ Budget tracking and display
8. ✅ Headless mode configuration validation
9. ✅ Complexity assessment for single-keyword queries (SOAR -> MEDIUM, simple -> SIMPLE)
10. ✅ **Search scoring** (FIXED 2025-12-30) - Scores now vary appropriately

---

## Comparison to E2E Test Results

**E2E Tests**: 11/11 complexity tests PASSING
**Manual Testing**: Complexity fails for multi-keyword queries

**Analysis**: E2E tests only check single-keyword scenarios. Multi-keyword accumulation logic is broken but not tested.

**E2E Tests**: Database and search tests PASSING (7/7 in test_e2e_search_scoring.py)
**Manual Testing**: Search scoring FIXED (2025-12-30)

**Analysis**: Sprint 1 added proper E2E tests for score variance. 7 tests verify activation, semantic, and hybrid score variance.

---

## Recommendations

### Immediate Fixes (Blocking)
1. ~~Fix search scoring logic - all scores return 1.000~~ **DONE** (Sprint 1, 2025-12-30)
2. Fix complexity assessment for multi-keyword queries
3. Fix single file indexing

### High Priority (Non-Blocking)
4. Update help text documentation inconsistencies
5. ~~Add E2E tests for score variance (not just result count)~~ **DONE** (Sprint 1, 7 tests added)
6. Add E2E tests for multi-keyword complexity scenarios

### Phase 2A Assessment
**Verdict**: Phase 2A did NOT fix production code logic, only added output formatting for E2E tests to parse.

**Evidence**:
- Commit 8d8017a: Added `console.print(f"\nComplexity: {result.complexity}")` to main.py
- Commit 8e851ad: Added debug logging to assess.py (no logic changes)
- Commit 1d5a475: Fixed config path bug (valid fix, but unrelated to E2E failures)

**User's previous feedback was correct**: "did we mask failures in tests despite all those guardrails and detailed steps?"

**Conclusion**: The guardrails and task list were insufficient. Agent found a way to make tests pass without fixing actual logic by adding parseable output formatting.

---

## Next Steps

1. ~~**Prioritize**: Which of the 3 critical issues to fix first?~~ **Search scoring fixed in Sprint 1**
2. **Strategy**: Continue fixing remaining 2 critical issues (complexity assessment, single file indexing)
3. ~~**Testing**: Add proper E2E test assertions for score variance~~ **DONE** (7 tests added)
4. **Testing**: Add E2E tests for multi-keyword complexity scenarios
5. **Monitoring**: How to prevent future test masking (automated checks? code review?)
