# Product Requirements Document: Sprint 2 - CLI Robustness and Search Quality

**Document ID**: PRD-SPRINT2-001
**Date**: 2025-12-30
**Status**: Ready for Implementation
**Target Audience**: Agent Executor
**Sprint Duration**: 1-2 days (8-16 hours)
**Priority**: CRITICAL (P0/P1 issues)

---

## 1. Introduction/Overview

### Problem Statement

Sprint 1 successfully fixed the core search scoring bugs (activation/semantic scores now vary). However, during post-sprint testing and real-world usage, four additional issues were discovered that significantly impact CLI reliability and search quality:

1. **Database Schema Migration Bug (P0)**: Users with old `aurora.db` (7 columns) encounter fatal errors when new code expects 9 columns. The migration fails silently, and subsequent operations display raw Python tracebacks.

2. **CLI Error Handling (P1)**: Full Python tracebacks are displayed for common errors instead of user-friendly messages with actionable guidance.

3. **Semantic Search False Positives (P1)**: Searching for non-existent terms (e.g., "payment", "enterprise") returns high-confidence results (0.88-0.93) because embedding similarity always finds "closest" vectors regardless of actual relevance.

4. **Activation Score Uniformity (P2)**: Top search results often show identical activation scores (all 1.000) after normalization, reducing ranking effectiveness.

### High-Level Goal

Improve Aurora CLI robustness and search quality so that:
- Database schema mismatches are handled gracefully with clear user guidance
- CLI errors display user-friendly messages (not Python tracebacks)
- Semantic search filters out low-relevance results
- Activation scores provide meaningful ranking differentiation

---

## 2. Goals

1. **Handle schema evolution** - Detect old database schemas and provide graceful migration or reset options
2. **Improve error UX** - Replace Python tracebacks with user-friendly error messages and actionable guidance
3. **Filter irrelevant results** - Add minimum semantic similarity threshold to prevent false positives
4. **Investigate activation variance** - Determine why activation scores cluster at same value and fix if possible
5. **Preserve existing functionality** - No regressions in Sprint 1 fixes or other CLI features
6. **Add regression protection** - Create E2E tests for each fix

---

## 3. User Stories

### Story 1: User with Old Database Upgrades Aurora
**As a** returning Aurora user with an existing database
**I want** the CLI to detect my old database schema and guide me through migration
**So that** I can continue using Aurora without data loss or confusing errors

**Acceptance Criteria**:
- Old aurora.db (7 columns) detected automatically
- User prompted: "Database schema outdated. Reset database? [Y/n]"
- No Python tracebacks shown for schema errors
- Clean error message with actionable steps displayed
- User can choose to backup before reset

### Story 2: Developer Encounters CLI Error
**As a** developer using Aurora CLI
**I want** error messages to explain what went wrong and how to fix it
**So that** I can resolve issues quickly without debugging Python code

**Acceptance Criteria**:
- StorageError exceptions display user-friendly message
- Error format: "Error: [problem]" + "Hint: [solution]"
- Full tracebacks only shown with `--debug` flag or `AURORA_DEBUG=1`
- Exit codes follow convention: 0=success, 1=user error, 2=system error
- All major CLI commands have try/catch with clean error display

### Story 3: User Searches for Non-Existent Term
**As a** developer searching the codebase
**I want** search to indicate when no truly relevant results exist
**So that** I don't waste time reviewing false positives

**Acceptance Criteria**:
- Minimum semantic threshold configurable (default 0.35)
- Results below threshold filtered out OR flagged as "low confidence"
- "No relevant results found" message when all scores below threshold
- Config option: `search.min_semantic_score` in config.json

### Story 4: QA Engineer Investigates Activation Variance
**As a** QA engineer validating search quality
**I want** to understand why activation scores are often identical
**So that** we can determine if this is a bug or expected behavior

**Acceptance Criteria**:
- Investigation report documenting findings
- If bug: implement fix and verify variance
- If by design: document why and update documentation

---

## 4. Functional Requirements

### FR-1: Database Schema Migration Handling (P0)

**The system must**:

1.1. Detect schema version during database initialization:
   - Check column count in `chunks` table
   - Compare against expected schema (currently 9 columns)
   - Store schema version in database metadata table

1.2. Handle schema mismatch gracefully:
   - If old schema detected (e.g., 7 columns), do NOT attempt direct INSERT
   - Display user-friendly message: "Database schema outdated (v1 found, v2 required)"
   - Prompt user: "Reset database and re-index? [Y/n]"
   - Offer backup option: "Create backup before reset? [Y/n]"

1.3. Implement backup mechanism:
   - Copy `aurora.db` to `aurora.db.bak.{timestamp}`
   - Display backup location to user

1.4. Implement reset mechanism:
   - Drop all tables and recreate with current schema
   - Display: "Database reset complete. Run 'aur mem index .' to re-index."

1.5. Never show raw Python tracebacks for schema errors:
   - Catch `OperationalError` with "table chunks has N columns but M values were supplied"
   - Catch `OperationalError` with "no such column"
   - Display clean error message with next steps

**Implementation Location**: `/home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/store/sqlite.py`

**Success Criteria**: User with old database sees helpful prompts, not Python errors.

---

### FR-2: CLI Error Handling Improvements (P1)

**The system must**:

2.1. Create centralized error handler:
   - Create `packages/cli/src/aurora_cli/error_handler.py`
   - Define error types: `UserError`, `SystemError`, `ConfigError`
   - Map exceptions to user-friendly messages

2.2. Implement error display function:
   ```python
   def display_error(error: Exception, context: str = "") -> None:
       """Display user-friendly error message.

       Format:
         Error: [problem description]
         Hint: [actionable solution]

       Full traceback only if AURORA_DEBUG=1 or --debug flag.
       """
   ```

2.3. Wrap all CLI command handlers with error catching:
   - `memory.py` - index, search, stats commands
   - `main.py` - query, init, verify commands
   - `budget.py` - budget commands

2.4. Define error messages for common scenarios:
   | Exception | User Message | Hint |
   |-----------|--------------|------|
   | `StorageError` | "Database error occurred" | "Run 'aur init --reset' to reinitialize" |
   | `FileNotFoundError` | "File not found: {path}" | "Check the path exists and is readable" |
   | `PermissionError` | "Permission denied: {path}" | "Check file permissions or run with sudo" |
   | `ConnectionError` | "Cannot connect to embedding service" | "Check OPENAI_API_KEY is set" |
   | `JSONDecodeError` | "Invalid configuration file" | "Run 'aur init' to recreate config" |

2.5. Implement exit code conventions:
   - 0: Success
   - 1: User error (bad input, missing file, etc.)
   - 2: System error (database corruption, service unavailable)

2.6. Add `--debug` global flag:
   - When set, display full Python traceback
   - Also enabled via `AURORA_DEBUG=1` environment variable

**Implementation Location**: `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/`

**Success Criteria**: No raw Python tracebacks in normal operation.

---

### FR-3: Semantic Search Threshold Filtering (P1)

**The system must**:

3.1. Add configurable minimum semantic score threshold:
   - Config key: `search.min_semantic_score`
   - Default value: 0.35
   - Valid range: 0.0 to 1.0

3.2. Update config schema:
   - Add `search` section to config.json
   - Include `min_semantic_score` parameter
   - Validate value is within range

3.3. Modify `hybrid_retriever.py` to filter results:
   ```python
   def retrieve(self, query: str, top_k: int = 10) -> List[SearchResult]:
       results = self._retrieve_raw(query, top_k * 2)  # Over-fetch

       # Filter by semantic threshold
       min_score = self.config.get("search.min_semantic_score", 0.35)
       filtered = [r for r in results if r.semantic_score >= min_score]

       if not filtered:
           return []  # Return empty, let caller handle "no results" message

       return filtered[:top_k]
   ```

3.4. Update search command output:
   - If no results after filtering: "No relevant results found for '{query}'"
   - If results filtered: "Found {N} results ({M} filtered as low relevance)"

3.5. Add CLI flag to override threshold:
   - `aur mem search "query" --min-score 0.5`
   - Overrides config value for this search only

3.6. Add "low confidence" indicator for borderline results:
   - Results with score between threshold and threshold+0.1 marked as "(low confidence)"
   - Example: `file.py (0.38) - low confidence`

**Implementation Locations**:
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/config.py`
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py`
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/memory.py`

**Success Criteria**: Searching "payment" (non-existent) returns zero or flagged low-confidence results.

---

### FR-4: Activation Score Variance Investigation (P2)

**The system must**:

4.1. Investigate current activation score behavior:
   - Query database: `SELECT base_level, access_count FROM activations`
   - Analyze distribution of raw activation scores
   - Check if normalization is causing uniform output

4.2. Document findings in investigation report:
   - Location: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/activation_variance_investigation.md`
   - Include database query results
   - Include analysis of normalization logic
   - Include recommendation (fix or document as expected)

4.3. IF bug identified:
   - Implement fix in relevant file(s)
   - Add unit test verifying variance
   - Verify with manual testing

4.4. IF expected behavior:
   - Document why activation scores cluster
   - Update user documentation explaining ranking
   - Close as "working as intended"

4.5. Potential root causes to investigate:
   - All chunks have same number of accesses (access_count = 1)
   - BLA initialization not creating variance
   - Normalization converting varied inputs to uniform outputs
   - Activation component being overshadowed by semantic

**Implementation Location**: TBD based on investigation

**Success Criteria**: Investigation report completed with actionable conclusion.

---

### FR-5: E2E Test Implementation

**The system must**:

5.1. Create schema migration tests:
   - File: `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_schema_migration.py`
   - Test: Create old-schema DB, run `aur init`, verify graceful handling
   - Test: Verify backup creation works
   - Test: Verify reset creates valid new schema

5.2. Create error handling tests:
   - File: `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_error_handling.py`
   - Test: Trigger StorageError, verify no traceback shown
   - Test: Verify exit codes are correct (0, 1, 2)
   - Test: Verify `--debug` shows full traceback

5.3. Create semantic threshold tests:
   - File: `/home/hamr/PycharmProjects/aurora/tests/e2e/test_e2e_search_threshold.py`
   - Test: Search non-existent term, verify low/no results
   - Test: Search with `--min-score` flag, verify filtering
   - Test: Verify config value is respected

5.4. Tests must fail before fix and pass after fix

**Success Criteria**: All E2E tests pass, provide regression protection.

---

### FR-6: Regression Testing

**The system must**:

6.1. Run full test suite:
   ```bash
   make test
   ```
   Expected: All existing tests pass (no regressions)

6.2. Run type checking:
   ```bash
   make type-check
   ```
   Expected: No new mypy errors introduced

6.3. Run quality gates:
   ```bash
   make quality-check
   ```
   Expected: Linting, formatting, and type checks pass

6.4. Verify Sprint 1 fixes still work:
   - Search scores still vary (not all 1.000)
   - E2E search scoring tests still pass
   - Manual verification of `aur mem search` output

**Success Criteria**: 2,369+ existing tests pass, Sprint 1 functionality preserved.

---

## 5. Non-Goals (Out of Scope)

The following are explicitly excluded from this sprint:

1. **Complexity Assessment Bug** - Multi-keyword query classification (TEST 12 failure) deferred to Sprint 3
2. **Single File Indexing Bug** - File indexing returning 0 chunks (TEST 6 failure) deferred to Sprint 3
3. **Documentation Inconsistencies** - Help text errors (`--verify`, `--limit`, `budget status`) deferred
4. **Config Show Command** - `aur config show` command absence deferred
5. **Developer Experience Features** - `aur doctor`, `aur init --interactive` (separate sprint)
6. **MCP Integration** - SOAR integration in MCP tools deferred
7. **Performance Optimization** - Search latency improvements not in scope
8. **New Features** - No new search modes or scoring algorithms

**Scope Management**: If encountering other issues during implementation, document them but do not fix. This sprint focuses on the four specified problems.

---

## 6. Design Considerations

### 6.1 Schema Migration Architecture

**Current State**:
```
User has aurora.db (7 columns)
    ↓
New code expects 9 columns
    ↓
INSERT fails with column mismatch
    ↓
Python traceback displayed
```

**Target State**:
```
User has aurora.db
    ↓
_init_schema() checks column count
    ↓
If mismatch:
    ├── Display: "Schema outdated (v1 → v2 required)"
    ├── Prompt: "Reset database? [Y/n]"
    ├── If Y: backup → drop → recreate
    └── If N: Exit with instructions
```

### 6.2 Error Handler Design

**Error Flow**:
```
CLI Command → raises Exception
    ↓
@error_handler decorator
    ↓
Map exception to UserError/SystemError
    ↓
Display: "Error: {message}\nHint: {solution}"
    ↓
Exit with appropriate code
```

**Debug Mode**:
```
if os.environ.get("AURORA_DEBUG") or args.debug:
    traceback.print_exc()
```

### 6.3 Search Threshold Flow

**Current Flow**:
```
Query → Embed → Find top-k similar → Return all
```

**New Flow**:
```
Query → Embed → Find top-k*2 similar → Filter by threshold → Return top-k
                                              ↓
                                    If empty: "No relevant results"
```

### 6.4 Config Schema Extension

**Current config.json**:
```json
{
    "llm": {...},
    "escalation": {...},
    "memory": {...},
    "database": {...},
    "budget": {...}
}
```

**New config.json**:
```json
{
    "llm": {...},
    "escalation": {...},
    "memory": {...},
    "database": {...},
    "budget": {...},
    "search": {
        "min_semantic_score": 0.35
    }
}
```

---

## 7. Technical Considerations

### 7.1 Implementation Constraints

- **Backward Compatibility**: Old config.json files must still work (new section is optional)
- **Database Safety**: Always backup before destructive operations
- **No Breaking Changes**: Existing CLI interface unchanged (only additions)
- **Performance**: Error handling must not add noticeable latency

### 7.2 Files to Modify

| File | Changes |
|------|---------|
| `packages/core/src/aurora_core/store/sqlite.py` | Schema detection, migration logic |
| `packages/cli/src/aurora_cli/error_handler.py` | NEW: Centralized error handling |
| `packages/cli/src/aurora_cli/commands/*.py` | Add error handler decorators |
| `packages/cli/src/aurora_cli/config.py` | Add search section |
| `packages/context-code/.../hybrid_retriever.py` | Add threshold filtering |
| `packages/cli/src/aurora_cli/commands/memory.py` | Add --min-score flag |

### 7.3 Testing Requirements

**Test Coverage**:
- Unit tests for schema detection logic
- Unit tests for error handler
- Unit tests for threshold filtering
- E2E tests for each acceptance criterion
- Manual verification of all four problems

**Test Isolation**:
- E2E tests must use temporary databases
- Must not pollute `~/.aurora/` directory
- Each test cleans up after itself

### 7.4 Suggested Implementation Order

1. **FR-1: Schema Migration** (P0) - Blocks usage for existing users
2. **FR-2: Error Handling** (P1) - Improves UX for all errors including FR-1
3. **FR-3: Search Threshold** (P1) - Independent, can be done in parallel
4. **FR-4: Activation Investigation** (P2) - Investigation only, low effort
5. **FR-5: E2E Tests** - Written alongside each feature
6. **FR-6: Regression Testing** - Final validation

---

## 8. Success Metrics

### 8.1 Quantitative Metrics

**Schema Migration**:
- Baseline: 100% of users with old DB see Python traceback
- Target: 0% see Python traceback, 100% see helpful prompt

**Error Handling**:
- Baseline: ~50% of errors show raw tracebacks
- Target: 0% show tracebacks in normal mode

**Search Quality**:
- Baseline: "payment" search returns 0.88 score (false positive)
- Target: "payment" search returns 0 results or "low confidence" flag

**Activation Variance**:
- Baseline: Unknown (investigation required)
- Target: Investigation report completed

### 8.2 Acceptance Criteria Checklist

**Problem 1 - Schema Migration (P0)**:
- [ ] Old aurora.db (7 columns) detected and handled gracefully
- [ ] User prompted: "Database schema outdated. Reset database? [Y/n]"
- [ ] No Python tracebacks shown for schema errors
- [ ] Clean error message with actionable steps
- [ ] E2E test: Create old-schema DB, run `aur init`, verify graceful handling

**Problem 2 - Error Handling (P1)**:
- [ ] StorageError caught and displayed as user-friendly message
- [ ] All CLI commands have try/catch with clean error display
- [ ] Tracebacks only in debug mode (`--debug` flag or `AURORA_DEBUG=1`)
- [ ] Exit codes: 0=success, 1=user error, 2=system error
- [ ] E2E test: Trigger common errors, verify no tracebacks shown

**Problem 3 - Search Quality (P1)**:
- [ ] Minimum semantic threshold configurable (default 0.35)
- [ ] Results below threshold filtered out or flagged
- [ ] "No relevant results" message when nothing above threshold
- [ ] Config option: `search.min_semantic_score` in config.json
- [ ] E2E test: Search non-existent term, verify low/no results

**Problem 4 - Activation Variance (P2)**:
- [ ] Investigation report completed
- [ ] If fixable: implement fix and verify variance
- [ ] If by design: document why and close as "working as intended"

### 8.3 Evidence Required Before Sprint Completion

**Evidence 1: Schema Migration Works**
```bash
# Create old-schema database (7 columns)
# Run aur init
# Verify: helpful prompt shown, no traceback
```

**Evidence 2: Error Handling Works**
```bash
# Trigger StorageError
# Verify: "Error: Database error" message shown
# Verify: No Python traceback unless AURORA_DEBUG=1
```

**Evidence 3: Search Threshold Works**
```bash
aur mem search "payment"
# Expected: "No relevant results found" OR results flagged low confidence
# NOT: Results with 0.88 score
```

**Evidence 4: E2E Tests Pass**
```bash
pytest tests/e2e/test_e2e_schema_migration.py -v
pytest tests/e2e/test_e2e_error_handling.py -v
pytest tests/e2e/test_e2e_search_threshold.py -v
# All PASSED
```

**Evidence 5: No Regressions**
```bash
make test
# 2,369+ passed, 14 skipped
```

---

## 9. Open Questions

### 9.1 Technical Questions

**Q1**: What should the default semantic threshold be?
- **Options**: 0.3, 0.35, 0.4
- **Recommendation**: 0.35 (balance between filtering noise and preserving results)
- **Decision Needed**: Before implementing FR-3

**Q2**: Should we migrate old schema or require reset?
- **Options**: A) Auto-migrate, B) Require reset, C) Offer both
- **Recommendation**: C) Offer both - try migrate, fall back to reset
- **Decision Needed**: Before implementing FR-1

**Q3**: How should "low confidence" results be displayed?
- **Options**: A) Separate section, B) Inline annotation, C) Filter out entirely
- **Recommendation**: B) Inline annotation "(low confidence)"
- **Decision Needed**: Before implementing FR-3

**Q4**: What exit codes should we use?
- **Options**: Standard Unix (0/1), Detailed (0/1/2/3+)
- **Recommendation**: 0=success, 1=user error, 2=system error
- **Decision Needed**: Before implementing FR-2

### 9.2 Process Questions

**Q5**: Should this be a feature branch or direct to main?
- **Recommendation**: Feature branch `fix/sprint2-robustness`
- **Rationale**: Multiple changes, safer to review before merge

**Q6**: If activation variance is "by design", should we skip P2?
- **Recommendation**: Investigation still valuable, document findings regardless
- **Rationale**: Helps future developers understand the system

---

## 10. Sprint Execution Checklist

### Pre-Sprint
- [ ] Read full PRD
- [ ] Understand all four problems
- [ ] Review related code files
- [ ] Create feature branch: `fix/sprint2-robustness`

### Problem 1: Schema Migration (P0)
- [ ] Review current `_init_schema()` implementation
- [ ] Implement schema version detection
- [ ] Implement user prompt for reset
- [ ] Implement backup mechanism
- [ ] Catch and handle schema-related exceptions
- [ ] Create E2E test
- [ ] Manual verification

### Problem 2: Error Handling (P1)
- [ ] Create `error_handler.py`
- [ ] Define error types and messages
- [ ] Add decorator to CLI commands
- [ ] Implement `--debug` flag
- [ ] Create E2E test
- [ ] Manual verification

### Problem 3: Search Threshold (P1)
- [ ] Add config section for search settings
- [ ] Modify hybrid_retriever.py for filtering
- [ ] Add `--min-score` CLI flag
- [ ] Update search output messages
- [ ] Create E2E test
- [ ] Manual verification

### Problem 4: Activation Investigation (P2)
- [ ] Query database for activation distribution
- [ ] Analyze normalization logic
- [ ] Document findings
- [ ] Implement fix OR document as expected
- [ ] Update investigation report

### Verification Phase
- [ ] Run full test suite
- [ ] Run type checking
- [ ] Run quality checks
- [ ] Collect all evidence items
- [ ] Verify Sprint 1 fixes still work

### Completion Phase
- [ ] Commit with clear message
- [ ] Update sprint status in AURORA_MAJOR_FIXES.md
- [ ] Merge feature branch to main

---

## 11. Red Flags (Sprint Failure Indicators)

**STOP immediately and reassess if ANY of these occur**:

- Modifying test assertions instead of production code
- Adding `|| true` or similar to mask failures
- Removing tests instead of fixing the underlying issue
- Tests pass but feature doesn't work when tested manually
- Expanding scope to include other issues (complexity, single file indexing)
- Skipping manual verification step
- Making changes to help tests parse output (without fixing actual logic)

**If a red flag is raised**: Document the situation, stop work, and re-evaluate the approach.

---

## 12. Context References

### Related Documents
- **Sprint 1 PRD**: `/home/hamr/PycharmProjects/aurora/tasks/0012-prd-sprint1-fix-search-scoring.md`
- **Manual Test Report**: `/home/hamr/PycharmProjects/aurora/docs/development/aurora_fixes/MANUAL_CLI_TEST_REPORT.md`
- **Developer Experience Sprint**: `/home/hamr/PycharmProjects/aurora/tasks/tasks-0013-sprint2-developer-experience.md` (separate sprint)

### Key Files
- `packages/core/src/aurora_core/store/sqlite.py` - Database operations
- `packages/cli/src/aurora_cli/commands/memory.py` - Search command
- `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` - Search logic
- `packages/cli/src/aurora_cli/config.py` - Configuration management

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-30 | Claude Opus 4.5 | Initial PRD creation |

---

**END OF DOCUMENT**
