# PRD-0027: Aurora SOAR Pipeline Simplification

**Version:** 1.0
**Created:** 2026-01-10
**Status:** Draft
**Author:** Product Manager (via Claude Code)

---

## 1. Introduction/Overview

### Problem Statement

The Aurora SOAR (Sense-Orient-Adapt-Respond) pipeline has grown to approximately 4,800 lines of code across 9 phases, with significant complexity that creates maintenance burden, reliability issues, and poor user experience. Key problems include:

1. **Redundant Phases**: The Route phase (369 lines) duplicates functionality already present in Decompose phase, which assigns agents to subgoals
2. **Over-Engineered Verification**: The Verify phase (396 lines) includes complex LLM-based scoring that adds latency without proportional value
3. **Silent Failures**: Agents fail without user visibility; 60-second timeout is insufficient for complex tasks
4. **No Progress Feedback**: Users see no output during agent execution, leading to perceived hangs
5. **Heavyweight Pattern Caching**: Record phase stores full 2048+ character chunks, causing truncation and storage bloat

### High-Level Goal

Simplify the SOAR pipeline from 9 phases to 7 phases (for MEDIUM/COMPLEX queries) and 4 phases (for SIMPLE queries), reducing total codebase from ~4,800 lines to ~2,500 lines while improving:
- **Latency**: Faster response times by eliminating redundant phases
- **Reliability**: Retry logic and LLM fallback prevent silent failures
- **User Experience**: Streaming progress output keeps users informed

---

## 2. Goals

### Primary Goals (Ranked by Priority)

| Priority | Goal | Success Metric |
|----------|------|----------------|
| 1 | **Performance Improvement** | 30%+ reduction in average latency for MEDIUM complexity queries |
| 2 | **Reliability Improvement** | 90%+ of agent executions complete successfully (vs current ~70% estimated) |
| 3 | **Test Coverage** | Maintain or improve test coverage (target: 85%+ line coverage on modified files) |
| 4 | **Code Reduction** | Reduce codebase from ~4,800 to ~2,500 lines (~48% reduction) |

**Note:** The line count target (~2,500 lines) is guidance to inspire simplicity, not a hard requirement. The focus is on removing unnecessary complexity while maintaining functionality.

### Secondary Goals

- Improve developer experience through clearer code structure
- Enable future extensibility with cleaner interfaces
- Reduce LLM API costs by eliminating unnecessary verification calls

---

## 3. User Stories

### US-1: Progress Visibility
**As a** developer using Aurora SOAR,
**I want to** see real-time progress as agents execute,
**So that** I know the system is working and can estimate completion time.

**Acceptance Criteria:**
- Structured progress output shows "[Agent 1/3] agent-name: Processing..."
- Multiple lines displayed for parallel agent execution
- Progress updates at least every 5 seconds during long-running tasks

### US-2: Reliable Agent Execution
**As a** developer using Aurora SOAR,
**I want to** have agents automatically retry on failure and fall back to direct LLM if needed,
**So that** I get results even when individual agents have transient failures.

**Acceptance Criteria:**
- Each agent retries once on failure before falling back
- Fallback to direct LLM (Claude) produces valid results
- User is informed when fallback occurs via metadata

### US-3: Fast Simple Queries
**As a** developer asking a simple question,
**I want to** get a quick response without unnecessary processing,
**So that** I'm not waiting for decomposition/verification on trivial queries.

**Acceptance Criteria:**
- SIMPLE queries bypass decomposition entirely
- Direct LLM (Claude) response within 5 seconds for SIMPLE queries
- Same LLM used as for agent spawning (Claude)
- Context retrieval still occurs for grounded answers

### US-4: Lightweight Pattern Caching
**As a** system administrator,
**I want to** have pattern caching that doesn't bloat storage,
**So that** the system remains performant over time.

**Acceptance Criteria:**
- Summary records are <500 characters with link to full log
- High-confidence patterns (>0.8) are marked for future retrieval
- Low-confidence results (<0.5) skip caching entirely

---

## 4. Technical Design

### 4.1 Current Architecture (BEFORE)

```
                           CURRENT 9-PHASE PIPELINE (~4,800 lines)
    ┌────────────────────────────────────────────────────────────────────────┐
    │                                                                        │
    │  1. Assess        → Determine complexity (assess.py)                   │
    │  2. Retrieve      → Memory search (retrieve.py)                        │
    │  3. Decompose     → Break into subgoals + suggest agents (decompose.py)│
    │  4. Verify        → 396 lines of LLM validation + scoring (verify.py)  │
    │  5. Route         → 369 lines agent lookup by ID (route.py)            │
    │  6. Collect       → spawn_parallel, no streaming, 60s timeout          │
    │  7. Synthesize    → Combine results (synthesize.py)                    │
    │  8. Record        → Store FULL chunks + embeddings (record.py)         │
    │  9. Respond       → Format output (respond.py)                         │
    │                                                                        │
    └────────────────────────────────────────────────────────────────────────┘

    PROBLEMS:
    - Route is redundant (Decompose already assigns agents)
    - Verify is over-engineered (396 lines, LLM calls for scoring)
    - Collect has no streaming, no retry, 60s timeout too short
    - Record stores huge chunks (2048+ chars, truncation issues)
    - Agents fail silently with no user feedback
```

### 4.2 Proposed Architecture (AFTER)

```
                        NEW SIMPLIFIED PIPELINE (~2,500 lines)
    ┌────────────────────────────────────────────────────────────────────────┐
    │                                                                        │
    │  SIMPLE queries (4 phases):                                            │
    │  ────────────────────────────                                          │
    │  1. Assess → SIMPLE detected                                           │
    │  2. Retrieve → Get context                                             │
    │  3. Direct LLM → Answer immediately (skip decompose)                   │
    │  4. Respond → Format output                                            │
    │                                                                        │
    │  MEDIUM/COMPLEX queries (7 phases):                                    │
    │  ─────────────────────────────────                                     │
    │  1. Assess       → Determine complexity                                │
    │  2. Retrieve     → Memory search                                       │
    │  3. Decompose    → Break into subgoals + assign agents                 │
    │  4. Verify Lite  → <100 lines:                                         │
    │                    - Check agents exist                                │
    │                    - Check no circular deps                            │
    │                    - Auto-retry ONCE with feedback                     │
    │                    - Create agent assignments (was Route)              │
    │  5. Collect      → spawn_with_retry_and_fallback:                      │
    │                    - Streaming output (user sees progress)             │
    │                    - Retry once per agent                              │
    │                    - Fallback to LLM if agent fails                    │
    │                    - 300s timeout (was 60s)                            │
    │  6. Synthesize   → Combine results                                     │
    │  7. Record       → Lightweight summary + link to log file              │
    │                    (skip if confidence < 0.5)                          │
    │  8. Respond      → Format output                                       │
    │                                                                        │
    │  Route phase: REMOVED (merged into Verify Lite)                        │
    │                                                                        │
    └────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Component Changes

#### 4.3.1 aurora_spawner Package

**File:** `packages/spawner/src/aurora_spawner/spawner.py`

**New Function: `spawn_with_retry_and_fallback()`**

```python
async def spawn_with_retry_and_fallback(
    task: SpawnTask,
    on_progress: Callable[[str], None] | None = None,
    **kwargs
) -> SpawnResult:
    """Spawn with single retry, fallback to direct LLM on failure.

    Execution flow:
    1. Attempt spawn with specified agent
    2. If failure, retry same agent once
    3. If still failing, fallback to direct LLM (no agent)

    Args:
        task: SpawnTask with prompt, agent, and timeout
        on_progress: Optional callback for progress updates
        **kwargs: Additional arguments passed to spawn()

    Returns:
        SpawnResult with success status and output
        - metadata.fallback=True if LLM fallback was used
        - metadata.original_agent set to failed agent ID
    """
```

**Modified Function: `spawn_parallel()`**

Add `on_progress` callback parameter to enable streaming output:

```python
async def spawn_parallel(
    tasks: list[SpawnTask],
    max_concurrent: int = 5,
    on_progress: Callable[[int, int, str, str], None] | None = None,
    **kwargs
) -> list[SpawnResult]:
    """Spawn subprocesses in parallel with progress callback.

    Args:
        on_progress: Callback(current_idx, total, agent_id, status)
                     Called when each agent starts/completes
    """
```

#### 4.3.2 aurora_soar/phases/verify.py (Verify Lite)

**Current:** 396 lines with LLM-based scoring, adversarial verification, retry feedback generation

**Target:** ~100 lines with fast structural validation

```python
def verify_lite(
    decomposition: dict,
    available_agents: list[str],
) -> tuple[bool, list[tuple[int, AgentInfo]], list[str]]:
    """Fast verification + agent assignment (replaces Route).

    Checks:
    1. All suggested agents exist in registry
    2. No circular dependencies in subgoals
    3. At least one subgoal generated
    4. Subgoal structure is valid (has required fields)

    Returns:
        (passed: bool, agent_assignments: list, issues: list[str])

    Note: This function now ALSO creates agent assignments,
          eliminating the need for a separate Route phase.
    """
```

**Removed:**
- `verify_decomposition()` with LLM scoring
- `_select_verification_option()` (SELF vs ADVERSARIAL)
- `_generate_retry_feedback()` using LLM
- `_prompt_user_for_weak_match()` (CLI interaction)
- `assess_retrieval_quality()` (move to Retrieve if needed)
- `VerifyPhaseResult` class (replace with simple tuple)
- `RetrievalQuality` enum

#### 4.3.3 aurora_soar/phases/route.py (DEPRECATED - DELETE)

**Current:** 369 lines handling agent lookup, capability-based fallback, circular dependency checking

**Target:** DELETE ENTIRELY

**Migration:**
1. Agent lookup by ID -> Move to `verify_lite()`
2. Capability-based fallback -> Move to `spawn_with_retry_and_fallback()`
3. Circular dependency check -> Move to `verify_lite()`
4. Execution plan parsing -> Simplify in `verify_lite()`

**Removed Classes/Functions:**
- `RouteResult` class
- `route_subgoals()` function
- `_validate_decomposition()` (duplicate of verify)
- `_route_single_subgoal()`
- `_extract_capability_from_agent_id()`
- `_validate_routing()`
- `_check_circular_dependencies()` (move to verify_lite)
- `_parse_execution_plan()`

#### 4.3.4 aurora_soar/phases/collect.py

**Current:** 657 lines, no streaming, 60s default timeout, no retry logic

**Changes:**

```python
# Constants
DEFAULT_AGENT_TIMEOUT = 300  # Was 60 seconds

async def execute_agents(
    agent_assignments: list[tuple[int, AgentInfo]],  # Changed from RouteResult
    context: dict[str, Any],
    agent_timeout: float = DEFAULT_AGENT_TIMEOUT,
    query_timeout: float = DEFAULT_QUERY_TIMEOUT,
    on_progress: Callable[[str], None] | None = None,  # NEW
) -> CollectResult:
    """Execute agents with streaming progress and retry logic.

    Changes from current:
    - Takes agent_assignments directly (no RouteResult)
    - Uses spawn_with_retry_and_fallback() for each task
    - Reports progress via on_progress callback
    - 300s default timeout (was 60s)
    """
```

**Progress Output Format:**
```
[Agent 1/3] code-analyzer: Starting...
[Agent 2/3] test-generator: Starting...
[Agent 1/3] code-analyzer: Completed (1.2s)
[Agent 3/3] doc-writer: Starting...
[Agent 2/3] test-generator: Completed (2.5s)
[Agent 3/3] doc-writer: Fallback to LLM (agent timeout)
[Agent 3/3] doc-writer: Completed via fallback (4.1s)
```

#### 4.3.5 aurora_soar/phases/record.py (Lightweight)

**Current:** 197 lines, stores full ReasoningChunk with 2048+ character content

**Changes:**

```python
def record_pattern_lightweight(
    store: Store,
    query: str,
    synthesis_result: SynthesisResult,
    log_path: Path,
) -> RecordResult:
    """Record minimal summary with link to full log.

    Caching Policy:
    - confidence >= 0.8: Cache + mark as pattern (activation +0.2)
    - confidence >= 0.5: Cache for learning (activation +0.05)
    - confidence < 0.5: Skip caching entirely

    Record Structure:
    - query: First 200 characters
    - summary: First 500 characters of answer
    - confidence: Float 0-1
    - log_file: Path to full conversation log
    - keywords: Extracted keywords for retrieval
    - timestamp: Unix timestamp
    """
```

**New Data Structure:**
```python
@dataclass
class SummaryRecord:
    """Lightweight summary record for pattern caching."""
    id: str
    query: str  # max 200 chars
    summary: str  # max 500 chars
    confidence: float
    log_file: str
    keywords: list[str]
    timestamp: float
```

**Storage:** The summary record should be filed under the existing `ReasoningChunk` storage mechanism to maintain compatibility with the memory retrieval system.

#### 4.3.6 aurora_soar/orchestrator.py

**Changes:**

1. **Remove Route Phase Call:**
```python
# BEFORE
phase5_result_obj = self._phase5_route(decomposition_dict)
phase6_result_obj = self._phase6_collect(phase5_result_obj, phase2_result)

# AFTER
passed, agent_assignments, issues = verify_lite(
    decomposition_dict,
    available_agents=self._list_agent_ids(),
)
if not passed:
    # Auto-retry decomposition once with feedback
    phase3_result = self._phase3_decompose(..., retry_feedback="\n".join(issues))
    passed, agent_assignments, issues = verify_lite(...)
    if not passed:
        return self._handle_verification_failure(...)

phase5_result = self._phase5_collect(agent_assignments, phase2_result, on_progress=...)
```

2. **Add Streaming Callback:**
```python
def _get_progress_callback(self) -> Callable[[str], None]:
    """Return callback for streaming progress to user."""
    def on_progress(message: str) -> None:
        # Print structured progress
        print(message)
    return on_progress
```

3. **Use Lightweight Record:**
```python
phase7_result = self._phase7_record_lightweight(
    query=query,
    synthesis_result=phase6_result,
    log_path=self.conversation_logger.current_log_path,
)
```

#### 4.3.7 aurora_cli/commands/soar.py (Minor Changes)

**File:** `packages/cli/src/aurora_cli/commands/soar.py`

**Impact:** Minimal - this file uses the updated SOAR packages and will automatically benefit from the changes. No code modifications required in the CLI command itself, but the file should be verified to work correctly with the updated orchestrator.

**Verification:**
- Ensure CLI properly passes through streaming output to terminal
- Verify timeout changes are respected when invoked via CLI
- Confirm fallback metadata is displayed in verbose mode

---

## 5. Non-Goals (Out of Scope)

1. **Memory Store Changes**: No changes to the ACT-R store implementation or tri-hybrid search
2. **Assess Phase Changes**: Complexity assessment logic remains unchanged
3. **Synthesize Phase Changes**: Result synthesis logic remains unchanged
4. **Agent Registry Changes**: Agent discovery and manifest management unchanged
5. **LLM Client Changes**: No modifications to LLM client interfaces
6. **CLI Changes**: No changes to CLI argument parsing; minor verification that streaming output works correctly (see Section 4.3.7)
7. **Configuration Schema Changes**: No new configuration options required
8. **Backward Compatibility**: route.py is internal; no public API backward compatibility needed

---

## 6. Design Considerations

### 6.1 Streaming Output Implementation

The streaming output uses a callback-based approach:

```python
def on_progress(current: int, total: int, agent_id: str, status: str):
    """Progress callback format.

    Args:
        current: Current agent index (1-based)
        total: Total number of agents
        agent_id: Agent identifier being executed
        status: One of "Starting", "Completed (Xs)", "Failed", "Fallback"
    """
    print(f"[Agent {current}/{total}] {agent_id}: {status}")
```

For parallel execution, multiple "Starting" messages may appear before "Completed" messages.

### 6.2 LLM Fallback Behavior

When an agent fails twice:
1. Create a new SpawnTask with `agent=None`
2. Use the same prompt
3. Direct LLM (Claude) responds without agent persona
4. Mark result with `metadata.fallback=True`
5. Include `metadata.original_agent` for debugging

### 6.3 Deprecation Strategy for route.py

Since route.py is an internal module with no external consumers:
1. No deprecation warning period required
2. Delete file after migration complete
3. Update imports in orchestrator.py
4. Update any tests referencing RouteResult

---

## 7. Technical Considerations

### 7.1 Dependencies

- **aurora_spawner**: Must be modified first (retry/fallback logic)
- **aurora_soar.phases.verify**: Depends on spawner changes
- **aurora_soar.phases.collect**: Depends on spawner changes
- **aurora_soar.orchestrator**: Depends on all phase changes

### 7.2 Migration Order

```
Phase 1: aurora_spawner (spawn_with_retry_and_fallback)
    ↓
Phase 2: aurora_soar/phases/verify.py (Verify Lite)
    ↓
Phase 3: aurora_soar/phases/collect.py (streaming, new timeout)
    ↓
Phase 4: aurora_soar/phases/record.py (lightweight)
    ↓
Phase 5: aurora_soar/orchestrator.py (remove Route, update flow)
    ↓
Phase 6: Delete aurora_soar/phases/route.py
```

### 7.3 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | High | Medium | Run full test suite after each phase |
| Performance regression | Low | High | Benchmark before/after each phase |
| Agent fallback produces poor results | Medium | Medium | Log fallback usage for monitoring |
| Streaming output causes I/O issues | Low | Low | Use non-blocking writes |

### 7.4 Rollback Plan

Each phase can be rolled back independently:
1. Git revert the phase's commits
2. Re-run tests to verify
3. Previous functionality restored

---

## 8. Success Metrics

### 8.1 Performance Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Average latency (MEDIUM) | ~15s | <10s | Time from query to response |
| P95 latency (MEDIUM) | ~45s | <30s | 95th percentile response time |
| SIMPLE query latency | ~8s | <5s | Time for SIMPLE complexity |

### 8.2 Reliability Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Agent success rate | ~70% | >90% | Successful completions / total attempts |
| Silent failure rate | ~15% | <2% | Failures without user notification |
| Fallback usage | N/A | <10% | Percentage using LLM fallback |

### 8.3 Code Quality Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Total lines (SOAR phases) | ~4,800 | ~2,500 | wc -l on phase files |
| Test coverage | ~78% | >85% | pytest-cov on modified files |
| Cyclomatic complexity | High | Reduced | radon cc analysis |

---

## 9. TDD Requirements

This PRD mandates Test-Driven Development (TDD) for all implementation work.

### 9.1 TDD Workflow

For each component change:

1. **RED**: Write failing test first
   - Test the expected behavior
   - Verify test fails for the right reason

2. **GREEN**: Write minimal code to pass
   - Implement just enough to make test pass
   - No optimization or cleanup yet

3. **REFACTOR**: Improve code while keeping tests green
   - Clean up implementation
   - Optimize if needed
   - All tests must still pass

### 9.2 Required Test Categories

#### Unit Tests (Required for Each Function)

```python
# Example: spawn_with_retry_and_fallback tests
class TestSpawnWithRetryAndFallback:
    def test_success_on_first_attempt(self): ...
    def test_success_on_retry(self): ...
    def test_fallback_after_two_failures(self): ...
    def test_fallback_preserves_original_agent(self): ...
    def test_progress_callback_called(self): ...
    def test_timeout_triggers_retry(self): ...
```

```python
# Example: verify_lite tests
class TestVerifyLite:
    def test_valid_decomposition_passes(self): ...
    def test_missing_agent_fails(self): ...
    def test_circular_dependency_detected(self): ...
    def test_empty_subgoals_fails(self): ...
    def test_agent_assignments_created(self): ...
```

#### Integration Tests (Required for Phase Interactions)

```python
class TestSOARPipelineIntegration:
    def test_simple_query_bypasses_decompose(self): ...
    def test_medium_query_uses_verify_lite(self): ...
    def test_agent_failure_triggers_fallback(self): ...
    def test_streaming_output_received(self): ...
    def test_lightweight_record_created(self): ...
```

#### E2E Tests (Required for Full Pipeline)

```python
class TestSOAREndToEnd:
    def test_simple_query_complete_flow(self): ...
    def test_medium_query_complete_flow(self): ...
    def test_complex_query_with_fallback(self): ...
    def test_progress_output_format(self): ...
```

### 9.3 Test Coverage Requirements

| Component | Minimum Coverage |
|-----------|-----------------|
| spawn_with_retry_and_fallback | 95% |
| verify_lite | 95% |
| collect.execute_agents | 90% |
| record_pattern_lightweight | 90% |
| orchestrator changes | 85% |

---

## 10. Implementation Plan

### Phase 1: Spawner Enhancement (Day 1-2)

**Goal:** Add retry and fallback logic to aurora_spawner

**Tasks:**
1. Write tests for `spawn_with_retry_and_fallback()` (TDD)
2. Implement `spawn_with_retry_and_fallback()`
3. Add `on_progress` callback to `spawn_parallel()`
4. Update spawner exports in `__init__.py`

**Files Modified:**
- `packages/spawner/src/aurora_spawner/spawner.py`
- `packages/spawner/src/aurora_spawner/__init__.py`
- `packages/spawner/tests/test_spawner.py` (new tests)

**Verification:**
- All spawner tests pass
- New function properly retries and falls back

**Verification Commands (run by Claude):**
```bash
cd packages/spawner && pytest tests/ -v
cd packages/spawner && pytest tests/test_spawner.py -k "retry" -v
```

### Phase 2: Verify Lite Implementation (Day 2-3)

**Goal:** Replace complex verification with lightweight structural checks

**Tasks:**
1. Write tests for `verify_lite()` (TDD)
2. Implement `verify_lite()` function
3. Keep old `verify_decomposition()` temporarily for comparison
4. Add agent assignment logic (from route.py)

**Files Modified:**
- `packages/soar/src/aurora_soar/phases/verify.py`
- `packages/soar/tests/phases/test_verify.py` (new tests)

**Verification:**
- verify_lite tests pass
- No regression in existing verify tests

**Verification Commands (run by Claude):**
```bash
cd packages/soar && pytest tests/phases/test_verify.py -v
cd packages/soar && pytest tests/ -v --tb=short
```

### Phase 3: Collect Phase Updates (Day 3-4)

**Goal:** Add streaming output, new timeout, use retry logic

**Tasks:**
1. Write tests for updated `execute_agents()` (TDD)
2. Update timeout to 300s
3. Add `on_progress` callback parameter
4. Switch to `spawn_with_retry_and_fallback()`
5. Update CollectResult to include fallback metadata

**Files Modified:**
- `packages/soar/src/aurora_soar/phases/collect.py`
- `packages/soar/tests/phases/test_collect.py` (new tests)

**Verification:**
- Collect tests pass with new timeout
- Progress callback fires correctly
- Fallback metadata included in results

**Verification Commands (run by Claude):**
```bash
cd packages/soar && pytest tests/phases/test_collect.py -v
cd packages/soar && pytest tests/phases/test_collect.py -k "timeout" -v
cd packages/soar && pytest tests/phases/test_collect.py -k "progress" -v
```

### Phase 4: Lightweight Record (Day 4-5)

**Goal:** Implement summary-based pattern caching

**Tasks:**
1. Write tests for `record_pattern_lightweight()` (TDD)
2. Implement `SummaryRecord` dataclass
3. Implement `record_pattern_lightweight()`
4. Add keyword extraction helper
5. Keep old `record_pattern()` temporarily

**Files Modified:**
- `packages/soar/src/aurora_soar/phases/record.py`
- `packages/soar/tests/phases/test_record.py` (new tests)

**Verification:**
- Lightweight record tests pass
- Summary length limits enforced
- Low confidence results skipped

**Verification Commands (run by Claude):**
```bash
cd packages/soar && pytest tests/phases/test_record.py -v
cd packages/soar && pytest tests/phases/test_record.py -k "lightweight" -v
```

### Phase 5: Orchestrator Integration (Day 5-6)

**Goal:** Remove Route phase, integrate new components

**Tasks:**
1. Write integration tests (TDD)
2. Update orchestrator to skip Route phase
3. Use verify_lite for agent assignments
4. Add streaming progress callback
5. Use lightweight record
6. Update phase metadata structure

**Files Modified:**
- `packages/soar/src/aurora_soar/orchestrator.py`
- `packages/soar/tests/test_orchestrator.py` (new tests)

**Verification:**
- All orchestrator tests pass
- E2E tests pass
- No Route phase in execution trace

**Verification Commands (run by Claude):**
```bash
cd packages/soar && pytest tests/test_orchestrator.py -v
cd packages/soar && pytest tests/ -v --tb=short
# E2E test with real SOAR execution
aur soar "What is 2+2?" --verbose
aur soar "Explain the SOAR pipeline architecture" --verbose
```

### Phase 6: Cleanup and Deletion (Day 6-7)

**Goal:** Remove deprecated code and tests, final verification

**Tasks:**
1. Delete `route.py` file
2. Remove old `verify_decomposition()` function
3. Remove old `record_pattern()` function
4. Update all imports
5. Delete/deprecate obsolete tests (see Test Deprecation below)
6. Run full test suite
7. Performance benchmarking
8. Update SOAR documentation (SOAR.md and architecture docs)

**Test Deprecation:**
The following test files/classes should be deleted or significantly refactored as the underlying code is being replaced:

| Test File | Action | Reason |
|-----------|--------|--------|
| `tests/phases/test_route.py` | DELETE | Route phase removed entirely |
| `tests/phases/test_verify.py` (old tests) | DELETE/REPLACE | Old `verify_decomposition()` tests replaced by `verify_lite()` tests |
| `tests/phases/test_record.py` (old tests) | DELETE/REPLACE | Old `record_pattern()` tests replaced by `record_pattern_lightweight()` tests |
| `tests/test_orchestrator.py` (Route-related) | REFACTOR | Remove tests that reference Route phase or RouteResult |

**Note:** New TDD tests written in Phases 1-5 replace these deprecated tests. Ensure new test coverage meets or exceeds previous coverage before deletion.

**Files Deleted:**
- `packages/soar/src/aurora_soar/phases/route.py`

**Files Modified:**
- `packages/soar/src/aurora_soar/phases/__init__.py`
- `packages/soar/src/aurora_soar/orchestrator.py` (import cleanup)

**Documentation to Update:**
- `docs/SOAR.md` - Update phase descriptions, remove Route phase, document new flow
- `docs/architecture/SOAR_ARCHITECTURE.md` (or equivalent) - Update architecture diagrams and component descriptions

**Verification:**
- Full test suite passes
- No imports of deleted modules
- Performance meets targets
- Documentation accurately reflects new implementation

**Verification Commands (run by Claude):**
```bash
# Full test suite
pytest packages/spawner/tests/ packages/soar/tests/ -v --tb=short

# Verify no references to deleted route.py
grep -r "from.*route import" packages/soar/src/ || echo "No route imports found - OK"
grep -r "RouteResult" packages/soar/src/ || echo "No RouteResult references found - OK"

# Verify deprecated tests are removed
test ! -f packages/soar/tests/phases/test_route.py && echo "test_route.py deleted - OK"
grep -r "verify_decomposition" packages/soar/tests/ || echo "No verify_decomposition test refs - OK"
grep -r "RouteResult" packages/soar/tests/ || echo "No RouteResult test refs - OK"

# Verify test coverage meets targets
pytest packages/soar/tests/ --cov=aurora_soar --cov-report=term-missing | grep -E "TOTAL|verify|collect|record"

# Line count verification
wc -l packages/soar/src/aurora_soar/phases/*.py packages/soar/src/aurora_soar/orchestrator.py

# E2E smoke tests
aur soar "What is 2+2?" --verbose
aur soar "How does the Aurora memory system work?" --verbose
aur soar "Analyze the test coverage in packages/soar" --verbose

# Performance timing (manual observation)
time aur soar "Explain SOAR phases" --verbose
```

---

## 11. Documentation Requirements

After implementation is complete, the following documentation **must** be updated to reflect the new SOAR architecture:

### 11.1 Required Documentation Updates

| Document | Location | Changes Required |
|----------|----------|------------------|
| **SOAR.md** | `docs/SOAR.md` | Update phase descriptions, remove Route phase, document SIMPLE vs MEDIUM/COMPLEX paths, add streaming progress info |
| **SOAR Architecture** | `docs/architecture/SOAR_ARCHITECTURE.md` | Update architecture diagrams, component relationships, data flow |
| **API Reference** | (if exists) | Update function signatures for verify_lite, spawn_with_retry_and_fallback |

### 11.2 Documentation Checklist

- [ ] Remove all references to Route phase
- [ ] Document Verify Lite function and its dual role (verification + agent assignment)
- [ ] Document new streaming progress output format
- [ ] Document retry and fallback behavior
- [ ] Document lightweight record caching policy (confidence thresholds)
- [ ] Update phase count (9 → 7 for MEDIUM/COMPLEX, 4 for SIMPLE)
- [ ] Update timeout documentation (60s → 300s)
- [ ] Add architecture diagram showing new simplified flow

---

## 12. Resolved Questions

The following questions have been resolved:

| # | Question | Decision |
|---|----------|----------|
| 1 | **Fallback Quality Monitoring** | Use existing `aur mem stats` - simplify to show: queries by complexity, spawned agents count, fallback to LLM count, average/max/min SOAR query times |
| 2 | **Progress Output Destination** | Output to same CLI window - keep it simple, no complexity |
| 3 | **Keyword Extraction** | Simple approach: extract from question + first few lines of answer (no LLM/TF-IDF) |
| 4 | **Retry Backoff** | Immediate retry (no exponential backoff) |
| 5 | **Parallel Progress Format** | Multiple lines (one per agent when running in parallel) |

---

## 13. Appendix

### A. Current File Line Counts

| File | Lines | After |
|------|-------|-------|
| verify.py | 396 | ~100 |
| route.py | 369 | 0 (deleted) |
| collect.py | 657 | ~550 |
| record.py | 197 | ~150 |
| orchestrator.py | 1,096 | ~1,000 |
| decompose.py | 201 | 201 (unchanged) |
| assess.py | ~200 | ~200 (unchanged) |
| retrieve.py | ~200 | ~200 (unchanged) |
| synthesize.py | ~300 | ~300 (unchanged) |
| respond.py | ~200 | ~200 (unchanged) |
| **Total** | **~4,816** | **~2,501** |

### B. Related PRDs

- PRD-0026: Aurora Simplified Architecture (parent initiative)
- PRD-0025: Rewire AUR SOAR Terminal Orchestrator
- PRD-0003: Aurora SOAR Pipeline (original design)

### C. Source Documents

- `/home/hamr/PycharmProjects/aurora/docs/development/aur_simplify/aur_soar.txt` - Original requirements discussion
