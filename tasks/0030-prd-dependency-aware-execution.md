# PRD: Dependency-Aware Execution

**PRD ID**: 0030
**Status**: Approved
**Author**: Claude + User
**Created**: 2026-01-20
**Updated**: 2026-01-21 (Revision 3)

**Revision 3 Changes**:
- Added FR2.7: Final execution summary after all waves
- Updated FR5.3: Clarified emoji markers without colors + rationale
- Added FR5.5: `--verbose` flag support for DEBUG logs
- Added Section 6.5: Impact on SOAR vs standalone spawn
- Added Section 6.6: Streaming output examples (default + verbose modes)
- Added E2E streaming output test scenarios
- Updated acceptance criteria (15 total, added #13-15 for summary and verbosity)
- Added non-goals: Terminal colors and quiet mode explicitly out of scope

---

## Design Decisions Summary

Answers from discovery session mapped to implementation choices:

| # | Question | Answer | Implementation |
|---|----------|--------|----------------|
| 1 | Wave Parallelism | **1A** - Parallel within wave, wait for completion | `spawn_parallel_tracked(wave_tasks, max_concurrent=4)` per wave |
| 2 | Failure Handling | **2C** - Partial context for dependents, continue independents | Track `failed_subgoals` set, pass partial context with failure markers |
| 3 | Output Format | **3C** - Use spawn_sequential format | `f"{prompt}\n\nPrevious context:\n{accumulated}"` |
| 4 | Output Size | **4A** - Pass full outputs | No truncation; optimize later if needed |
| 5 | Missing Dependencies | **5A** - Strengthen verify_lite | Add ~5 LOC to `_check_circular_deps` |
| 6 | Circular Dependencies | **6A** - Trust verify_lite | Already implemented, no changes |
| 7 | Timeout Behavior | **7A** - Treat as failure after retries | `spawn_parallel_tracked` handles; then apply 2C |
| 8 | Progress Display | **8A** - Show wave counts | `"Wave {n}/{total} ({count} subgoals)..."` + ✓/✗/⚠ markers (no colors) + final summary |
| 9 | Logging | **9D** - All levels | INFO: waves, DEBUG: topo sort (via --verbose), SOAR trace |
| 10 | Acceptance Criteria | **10D** - Full suite + perf regression | See Section 12 (15 criteria) |

---

## 1. Introduction/Overview

Aurora's SOAR pipeline decomposes complex queries into subgoals, each with an optional `depends_on` field indicating which subgoals must complete first. However, the current collect phase (`execute_agents`) ignores these dependencies entirely, spawning all agents in parallel regardless of their dependency relationships.

This feature enhances the collect phase to execute subgoals in topological waves, respecting dependency ordering and passing outputs from completed subgoals to their dependents.

### Problem Statement

1. **Dependencies ignored**: Subgoals have `depends_on` field but `execute_agents()` spawns all agents simultaneously
2. **No output passing**: Output from agent A is not passed to dependent agent B, losing valuable context
3. **Missing validation**: `verify_lite` checks for circular dependencies but does not validate that `depends_on` references point to existing subgoals

### High-Level Goal

Enable dependency-aware execution where subgoals execute in topological order (waves), with outputs from earlier waves passed as context to dependent subgoals in subsequent waves.

---

## 2. Goals

| ID | Goal | Measurable Outcome |
|----|------|-------------------|
| G1 | Execute subgoals respecting `depends_on` ordering | Subgoals with dependencies execute only after their dependencies complete |
| G2 | Pass outputs between dependent subgoals | Dependent subgoals receive accumulated context from their dependencies |
| G3 | Handle failures gracefully | Failed subgoal's direct dependents run with partial context (successful deps + failure markers); independent subgoals continue |
| G4 | Validate dependency references at plan-time | `verify_lite` rejects plans with invalid `depends_on` references |
| G5 | No performance regression for simple queries | Queries without dependencies execute as fast as before (single wave) |

---

## 3. User Stories

### US1: Developer with Multi-Step Research Query
**As a** developer asking a complex question
**I want** subgoal outputs to flow to dependent subgoals
**So that** later research builds on earlier findings rather than starting from scratch

**Example**: Query "How should I architect a caching layer for Aurora's memory system?"
- Subgoal 1: Research current memory architecture (no deps)
- Subgoal 2: Analyze caching patterns used in similar systems (no deps)
- Subgoal 3: Design caching integration (depends on 1, 2) - receives outputs from both

### US2: User with Partial Failure
**As a** user whose query has a failing subgoal
**I want** dependent subgoals to run with available context and independent subgoals to continue
**So that** I get maximum results rather than cascade failures

**Example**:
- Subgoal 1 succeeds
- Subgoal 2 fails (timeout after retries)
- Subgoal 3 (depends on 1, 2) executes with PARTIAL context: ✓ sg-1 output + ✗ sg-2 failure marker
- Subgoal 4 (depends on 1 only) executes normally with subgoal 1's output

### US3: User Monitoring Progress
**As a** user watching execution
**I want** to see which wave is currently executing
**So that** I understand the progress and structure of the query

---

## 4. Functional Requirements

### FR1: Topological Sorting
The system must group subgoals into execution waves using topological sort (Kahn's algorithm):
- **FR1.1**: Wave 1 contains all subgoals with no dependencies
- **FR1.2**: Wave N contains subgoals whose dependencies are all in waves 1 through N-1
- **FR1.3**: Subgoals within a wave execute in parallel (up to `max_concurrent=4`)
- **FR1.4**: The system must complete all subgoals in wave N before starting wave N+1

### FR2: Context Passing Between Waves
The system must pass outputs from completed subgoals to their dependents:
- **FR2.1**: Use the existing `spawn_sequential` format: `f"{task.prompt}\n\nPrevious context:\n{accumulated_context}"`
- **FR2.2**: Accumulated context must include outputs from all successful dependencies AND failure markers for failed dependencies
- **FR2.3**: Format successful dependency as `✓ [sg-{index}]: {output}`
- **FR2.4**: Format failed dependency as `✗ [sg-{index}]: FAILED - {error_summary}`
- **FR2.5**: Add warning footer when partial context: `"WARNING: X/Y dependencies failed. Proceed with available context."`
- **FR2.6**: Pass full outputs (no truncation in initial implementation)
- **FR2.7**: Display final execution summary after all waves complete: `"EXECUTION COMPLETE: X/N succeeded, Y failed, Z partial"`

### FR3: Failure Handling
The system must handle subgoal failures gracefully:
- **FR3.1**: When a subgoal fails, it has already exhausted the full retry chain:
  - Primary execution attempt
  - Retry attempt (default: 2 retries, configurable via spawn policy)
  - LLM fallback attempt (different model)
  - Circuit breaker checks before each attempt
  - Only after ALL retries exhausted is `SpawnResult.success=False` returned
- **FR3.2**: Dependents with ANY failed dependencies receive partial context (both successful outputs and failure markers)
- **FR3.3**: Continue executing independent subgoals in subsequent waves
- **FR3.4**: Timeout is treated as failure after retry/fallback exhaustion (existing behavior)
- **FR3.5**: Mark subgoals with partial context for traceability (status: "partial")
- **FR3.6**: Include failure summary (error type, retry count, timeout info) in context for partial deps

### FR4: Dependency Validation
The system must validate dependency references at plan-time in `verify_lite`:
- **FR4.1**: Build set of valid subgoal indices from decomposition
- **FR4.2**: For each subgoal's `depends_on` list, verify all referenced indices exist
- **FR4.3**: Add issue string for invalid references: `"Subgoal {X} depends on non-existent subgoals: {invalid_list}"`
- **FR4.4**: Existing circular dependency detection remains unchanged

### FR5: Progress Display
The system must show wave-based progress:
- **FR5.1**: Display format: `"Wave {current}/{total} ({count} subgoals)..."`
- **FR5.2**: Highlight current wave being executed
- **FR5.3**: Show status with semantic emoji markers (no colors):
  - `✓` for successful subgoals
  - `✗` for failed subgoals
  - `⚠` for subgoals with partial context (some dependencies failed)
  - **Rationale**: Emoji markers are terminal-agnostic, accessible (screen readers), grep-friendly, and sufficient for visual scanning without color complexity
- **FR5.4**: Display summary: `"✓ Received: sg-1, sg-3  ✗ Missing: sg-2 (timeout)"` for partial subgoals
- **FR5.5**: Support existing `--verbose` flag for DEBUG-level details (topological sort, context assembly); default mode shows user-friendly progress only

### FR6: Logging
The system must log execution details at appropriate levels:
- **FR6.1**: INFO level: Wave start/completion, subgoals in wave
- **FR6.2**: DEBUG level: Topological sort details, context assembly
- **FR6.3**: Store execution trace in SOAR trace storage (existing infrastructure)

---

## 5. Non-Goals (Out of Scope)

- **Generic flow configs**: No YAML/JSON-based flow definition language
- **Graph DSL**: No custom graph definition syntax
- **Complex state objects**: String outputs are sufficient; no structured state machine
- **Multi-turn conversation**: Dependencies are single-pass, not interactive
- **Wave-level retry**: `spawn_parallel_tracked` handles retries within each task; no additional wave-level retry
- **Output truncation**: Pass full outputs; optimize later if needed
- **Dynamic dependency modification**: Dependencies are fixed at decomposition time
- **Terminal colors**: Semantic emoji markers (✓/✗/⚠) are sufficient; colors add complexity (color libraries, accessibility concerns, terminal compatibility) for minimal UX gain
- **Quiet mode**: Aurora uses `--verbose` pattern (default + verbose); no need for third verbosity level

---

## 6. Design Considerations

### 6.1 Existing Infrastructure to Leverage

#### spawn_sequential (spawner.py:849-893)
Provides the context accumulation pattern to reuse:
```python
# Context format to adopt:
accumulated_context += result.output + "\n"
modified_prompt = f"{task.prompt}\n\nPrevious context:\n{accumulated_context}"
```

#### spawn_parallel_tracked (spawner.py:896+)
Provides wave execution infrastructure:
- Wave calculation: `num_waves = math.ceil(total_tasks / max_concurrent)`
- Handles: stagger delays (5s), circuit breaker, retry (default 2), fallback to LLM
- Returns: `tuple[list[SpawnResult], dict[str, Any]]`

**Key insight**: Reuse `spawn_parallel_tracked` per wave rather than reimplementing parallel execution.

#### verify_lite (verify.py:19-198)
Existing validation framework:
- Validates: structure, agent existence, circular dependencies
- `_check_circular_deps` (lines 147-198) builds dependency graph
- **Missing**: validation that `depends_on` refs point to existing subgoals

#### execute_agents (collect.py:180-362)
Current implementation to modify:
- Calls `spawn_parallel_tracked` for ALL agents at once
- Ignores `depends_on` field entirely
- Has `AgentOutput` with `subgoal_index` for result mapping

### 6.2 Example Execution Flow

```
Input subgoals:
  sg-1 (no deps)
  sg-2 (depends on sg-1)
  sg-3 (depends on sg-1)
  sg-4 (depends on sg-2, sg-3)

Execution (Success Case):
  Wave 1: [sg-1] → spawn_parallel_tracked([sg-1])
  Wave 2: [sg-2, sg-3] → spawn_parallel_tracked([sg-2, sg-3]) with sg-1 output in context
  Wave 3: [sg-4] → spawn_parallel_tracked([sg-4]) with sg-2, sg-3 outputs in context

Execution (Partial Failure Case):
  Wave 1: [sg-1] ✓ success
  Wave 2:
    [sg-2] ✗ failed (timeout after 3 retries + fallback)
    [sg-3] ✓ success (received sg-1 output)
  Wave 3: [sg-4] ⚠ PARTIAL (received context with both successes and failures):
    Context passed to sg-4:
      "Original task: Integrate caching layer

      Previous context (1/2 dependencies):
      ✓ [sg-1]: <output from sg-1>
      ✗ [sg-2]: FAILED (timeout after 180s, 3 retries exhausted)

      WARNING: 1/2 dependencies failed. Proceed with available context."

  Result: sg-1 ✓, sg-2 ✗, sg-3 ✓, sg-4 ⚠ (partial)
```

### 6.3 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Parallel execution per wave | Reuse `spawn_parallel_tracked` | Don't reinvent parallel execution; leverage existing retry/fallback |
| Context format | Reuse `spawn_sequential` format | Consistency with existing patterns |
| Dependency validation | Strengthen `verify_lite` | Plan-time validation, not runtime |
| Failure handling | Partial context model | Maximize completion while informing LLM of missing context |
| Wave-level retry | None | `spawn_parallel_tracked` handles retries within each wave |
| Wave terminology | Topological waves (dependencies) vs Execution waves (parallelism) | Clear distinction avoids confusion in timeout calculations |

### 6.4 Wave Terminology

**Critical distinction for implementation:**

| Term | Definition | Example |
|------|------------|---------|
| **Topological Wave** | Group of subgoals at same dependency level (theoretically parallel) | 10 subgoals all depending on sg-1 = 1 topological wave |
| **Execution Wave** | Up to 4 tasks running simultaneously (limited by `max_concurrent=4`) | 10 tasks split into 3 execution waves: 4+4+2 |

**How it works:**
```python
# Each topological wave is passed to spawn_parallel_tracked
topo_waves = topological_sort(subgoals)  # e.g., 3 topological waves

for topo_wave in topo_waves:
    # spawn_parallel_tracked AUTOMATICALLY chunks into execution waves
    # if topo_wave has 10 tasks: ceil(10/4) = 3 execution waves
    # timeout = 3 * policy_max_timeout (calculated internally)
    results = await spawn_parallel_tracked(
        topo_wave,
        max_concurrent=4  # Execution wave size limit
    )
```

**Timeout Calculation:**
- Timeout is calculated PER topological wave based on how many execution waves it requires
- Formula in `spawn_parallel_tracked`: `num_waves = ceil(tasks / max_concurrent)`
- No changes needed to existing timeout formula - it already handles this correctly

### 6.5 Impact on SOAR vs Standalone Spawn

**This feature directly affects SOAR collect phase (phase 5 of 7):**

```
aur soar <query>
  ↓
SOAR 7-phase pipeline
  ↓
Phase 5: COLLECT (collect.py:execute_agents)
  ↓
spawn_parallel_tracked() ← Enhanced with wave-based execution
```

**Scope of impact:**
- ✅ **SOAR queries**: All SOAR executions use `execute_agents()` which will be enhanced for dependency-aware execution
- ❌ **Standalone `aur spawn`**: NOT affected - uses `aurora_spawner` directly without SOAR orchestration
- ❌ **Direct spawner usage**: NOT affected - `spawn_parallel_tracked()` behavior unchanged

**Why this is correct:** SOAR's decompose phase is the only component that generates `depends_on` relationships. Standalone `aur spawn` operates on task files without dependency metadata, so wave-based execution wouldn't apply.

### 6.6 Streaming Output Examples

Following Aurora's existing verbosity pattern (`--verbose` flag), progress output will have two modes:

#### Default Mode (User-Friendly)
```bash
$ aur soar "How should I architect a caching layer for Aurora's memory system?"

[Phase 1: ASSESS] Complexity: COMPLEX (score: 32)
[Phase 2: RETRIEVE] Found 15 relevant chunks
[Phase 3: DECOMPOSE] Generated 4 subgoals
[Phase 4: VERIFY] ✓ Plan validated (no issues)

[Phase 5: COLLECT] Executing dependency-aware...

Wave 1/3 (1 subgoal)...
  ✓ [sg-1] Research current memory architecture
    └─ Agent: technical-researcher (180s)

Wave 2/3 (2 subgoals)...
  ✓ [sg-2] Analyze caching patterns in similar systems
    └─ Agent: pattern-analyzer (145s)
  ✗ [sg-3] Review Aurora's performance bottlenecks
    └─ Agent: performance-auditor (timeout after 300s, 2 retries exhausted)

Wave 3/3 (1 subgoal)...
  ⚠ [sg-4] Design caching integration strategy
    └─ Agent: system-architect (210s)
    └─ Context: 2/3 dependencies (✓ sg-1, ✓ sg-2, ✗ sg-3)
    └─ WARNING: 1/3 dependencies failed, proceeding with partial context

EXECUTION COMPLETE: 3/4 succeeded, 1 failed, 1 partial

[Phase 6: SYNTHESIZE] Combining results...
[Phase 7: RECORD] Stored reasoning trace

=== Answer ===
[Combined synthesis from successful subgoals, noting sg-3 gap]
```

#### Verbose Mode (`--verbose` flag)
```bash
$ aur soar "query" --verbose

[DEBUG] Topological sort: 3 waves from 4 subgoals
[DEBUG] Wave 1: dependencies={}, subgoals=[sg-1]
[DEBUG] Wave 2: dependencies={sg-1}, subgoals=[sg-2, sg-3]
[DEBUG] Wave 3: dependencies={sg-2, sg-3}, subgoals=[sg-4]

[INFO] Wave 1/3 (1 subgoal)...
[DEBUG] Building context for sg-1: no dependencies
  ✓ [sg-1] Research current memory architecture (180s)
[DEBUG] SpawnResult: success=True, output=1847 chars

[INFO] Wave 2/3 (2 subgoals)...
[DEBUG] Building context for sg-2: deps=[sg-1], accumulated=1847 chars
[DEBUG] Building context for sg-3: deps=[sg-1], accumulated=1847 chars
  ✓ [sg-2] Analyze patterns (145s)
[DEBUG] SpawnResult: success=True, output=2103 chars
  ✗ [sg-3] Performance audit (timeout after 300s)
[DEBUG] SpawnResult: success=False, error="Timeout after 3 retries"
[DEBUG] Marking sg-3 as failed, dependents will receive partial context

[INFO] Wave 3/3 (1 subgoal)...
[DEBUG] Building context for sg-4: deps=[sg-2, sg-3]
[DEBUG] Partial context: 1 success (sg-2), 1 failure (sg-3)
[DEBUG] Adding WARNING footer for partial dependencies
  ⚠ [sg-4] Design integration (210s)
[DEBUG] SpawnResult: success=True, output=1654 chars, partial_context=True

[INFO] EXECUTION COMPLETE: 3/4 succeeded, 1 failed, 1 partial
```

**Key differences:**
- Default: User-focused, clean output with essential progress
- Verbose: DEBUG logs showing internal mechanics (topological sort, context assembly, spawn results)

---

## 7. Technical Considerations

### 7.1 Implementation Scope (~60 LOC)

#### collect.py changes (~55 LOC)

```python
def topological_sort(subgoals: list[dict]) -> list[list[dict]]:
    """Group subgoals into dependency waves using Kahn's algorithm.

    Args:
        subgoals: List of subgoal dicts with 'subgoal_index' and 'depends_on'

    Returns:
        List of waves, where each wave is a list of subgoals that can execute in parallel
    """
    # ~15 LOC implementation

# In execute_agents, replace single spawn_parallel_tracked call with:
waves = topological_sort(subgoals)
outputs: dict[int, SpawnResult] = {}
failed_subgoals: set[int] = set()

for wave_num, wave in enumerate(waves, 1):
    logger.info(f"Wave {wave_num}/{len(waves)} ({len(wave)} subgoals)...")

    # All subgoals are executable (no skipping, use partial context instead)
    executable = wave

    # Inject previous outputs using spawn_sequential format with partial context support
    for sg in executable:
        deps = sg.get("depends_on", [])
        if deps:
            successful_deps = [idx for idx in deps if idx in outputs and outputs[idx].success]
            failed_deps = [idx for idx in deps if idx in outputs and not outputs[idx].success]

            dep_outputs = []
            # Add successful outputs with ✓ marker
            for idx in successful_deps:
                dep_outputs.append(f"✓ [sg-{idx}]: {outputs[idx].output}")

            # Add failure markers with ✗
            for idx in failed_deps:
                error_summary = outputs[idx].error or "Unknown error"
                dep_outputs.append(f"✗ [sg-{idx}]: FAILED - {error_summary}")

            if dep_outputs:
                accumulated = "\n".join(dep_outputs)
                warning = ""
                if failed_deps:
                    warning = f"\n\nWARNING: {len(failed_deps)}/{len(deps)} dependencies failed. Proceed with available context."

                modified_prompt = f"{sg['prompt']}\n\nPrevious context ({len(successful_deps)}/{len(deps)} dependencies):\n{accumulated}{warning}"
                sg['prompt'] = modified_prompt
                sg['has_partial_context'] = len(failed_deps) > 0

    # Execute wave using EXISTING spawn_parallel_tracked
    # spawn_parallel_tracked handles:
    # - Primary execution attempt
    # - Retry attempts (default 2, configurable)
    # - LLM fallback (different model)
    # - Circuit breaker checks
    # Only returns success=False after ALL retries exhausted
    results, meta = await spawn_parallel_tracked(wave_tasks, max_concurrent=4, ...)

    # Track results and failures
    for sg, result in zip(executable, results):
        idx = sg["subgoal_index"]
        outputs[idx] = result
        if not result.success:
            failed_subgoals.add(idx)
            logger.warning(f"Subgoal {idx} failed after retries, dependents will receive partial context")
        elif sg.get('has_partial_context'):
            logger.info(f"Subgoal {idx} completed with partial context (⚠)")
```

#### verify.py changes (~5 LOC)

```python
# In _check_circular_deps after building graph (line 165):
valid_indices = set(graph.keys())
for subgoal_index, deps in graph.items():
    invalid_deps = [d for d in deps if d not in valid_indices]
    if invalid_deps:
        issues.append(f"Subgoal {subgoal_index} depends on non-existent subgoals: {invalid_deps}")
```

### 7.2 Files to Modify

| File | Changes | LOC |
|------|---------|-----|
| `packages/soar/src/aurora_soar/phases/collect.py` | Add `topological_sort()`, modify `execute_agents()` with partial context handling | ~55 |
| `packages/soar/src/aurora_soar/phases/verify.py` | Add missing dependency validation in `_check_circular_deps` | ~5 |
| `packages/soar/tests/test_phases/test_collect.py` | New test cases including partial context tests | ~120 |
| `packages/soar/tests/test_phases/test_verify.py` | Test for invalid dependency detection | ~20 |

### 7.3 Dependencies

- **aurora_spawner**: `spawn_parallel_tracked`, `SpawnTask`, `SpawnResult`
- **No new dependencies required**

---

## 8. Success Metrics

| Metric | Current State | Target |
|--------|--------------|--------|
| Dependency ordering | Ignored | 100% respected |
| Context passing | None | Dependents receive all dependency outputs |
| Partial dependency handling | N/A | Dependent receives available context + failure markers when some deps fail |
| Independent subgoal completion | N/A | Continue despite other failures |
| Invalid dependency detection | Not caught | 100% caught at plan-time |
| Performance (no deps) | Baseline | No regression (within 5%) |

---

## 9. Test Scenarios

Following existing patterns in `test_collect.py`:

### Unit Tests

| Test | Description |
|------|-------------|
| `test_topological_sort_no_deps` | All subgoals in single wave when no dependencies |
| `test_topological_sort_linear_deps` | A -> B -> C produces 3 waves of 1 each |
| `test_topological_sort_diamond_deps` | A -> (B, C) -> D produces correct 3 waves |
| `test_topological_sort_parallel_chains` | Independent chains sorted correctly |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_wave_execution_order` | Verify waves execute in correct order |
| `test_context_passing_between_waves` | Verify dependent gets predecessor output |
| `test_partial_context_with_failed_dependency` | Dependent receives partial context with both ✓ and ✗ markers when some deps fail |
| `test_partial_context_warning_footer` | Verify WARNING message appended when partial context |
| `test_all_dependencies_failed` | Dependent receives context with all failure markers |
| `test_independent_subgoals_continue` | Non-dependent subgoals execute despite failures |
| `test_no_deps_single_wave` | Performance baseline - no regression |
| `test_retry_chain_before_failure` | Verify spawn_parallel_tracked exhausts retries before marking as failed |

### Validation Tests

| Test | Description |
|------|-------------|
| `test_verify_lite_invalid_dependency_ref` | Invalid `depends_on` reference caught |
| `test_verify_lite_valid_deps_pass` | Valid dependencies pass verification |

### Performance Tests

| Test | Description |
|------|-------------|
| `test_no_deps_performance_regression` | Queries without dependencies complete within 5% of baseline |

### E2E Streaming Output Tests

| Test | Description |
|------|-------------|
| `test_default_mode_streaming_output` | Verify default mode shows wave progress, ✓/✗/⚠ markers, final summary without DEBUG logs |
| `test_verbose_mode_streaming_output` | Verify `--verbose` flag adds DEBUG logs (topological sort, context assembly, spawn results) |
| `test_final_summary_appears_after_waves` | Verify "EXECUTION COMPLETE: X/N succeeded, Y failed, Z partial" appears after all waves |
| `test_partial_context_warning_in_output` | Verify WARNING footer appears in output when dependencies fail |

---

## 10. Open Questions

1. **Context size limits**: Should we set a max size for accumulated context to prevent prompt overflow?
   - **Current answer**: Start with full outputs, optimize if needed

2. **Partial dependency success**: If sg-1 succeeds and sg-2 fails, should sg-3 (depends on both) receive sg-1's output or be skipped entirely?
   - **✅ RESOLVED**: Use partial context model (Option B)
   - **Rationale**:
     - Better UX - maximizes completion rather than cascade failures
     - Modern LLMs handle partial context well with proper warnings
     - Transparent - shows cascade: sg1✓ → sg2✗ → sg3⚠
     - Aligns with graceful degradation principle
   - **Implementation**: Pass both successful outputs (✓ markers) and failure summaries (✗ markers) with WARNING footer

3. **Progress callback format**: Should wave info be added to existing `on_progress` callback or use separate mechanism?
   - **Current answer**: Use existing callback with wave prefix

---

## 11. Implementation Plan

### Phase 1: Core Implementation (1 day)
- [ ] Add `topological_sort()` function to collect.py
- [ ] Modify `execute_agents()` for wave-based execution
- [ ] Add context passing between waves
- [ ] Add failure tracking and dependent skipping

### Phase 2: Validation Enhancement (0.5 day)
- [ ] Add invalid dependency reference check to `_check_circular_deps`
- [ ] Add tests for validation

### Phase 3: Testing (1 day)
- [ ] Unit tests for topological sort
- [ ] Integration tests for wave execution
- [ ] Integration tests for context passing
- [ ] Integration tests for failure handling
- [ ] Performance regression tests

### Phase 4: Progress Display (0.5 day)
- [ ] Add wave info to progress callback
- [ ] Add logging at INFO/DEBUG levels

---

## 12. Acceptance Criteria

1. [ ] Basic 3-wave example (A -> B, C -> D) executes in correct order
2. [ ] Dependent subgoal prompt contains predecessor output in spawn_sequential format
3. [ ] Partial context: Subgoal with 1 success + 1 failed dependency receives both ✓ and ✗ markers
4. [ ] Partial context: WARNING footer appended when any dependencies fail
5. [ ] Partial context: Subgoals marked with ⚠ status in progress display
6. [ ] Independent subgoals continue executing despite failures in other chains
7. [ ] Retry chain: Failures only marked after spawn_parallel_tracked exhausts all retries (primary + retry + fallback)
8. [ ] Performance: Queries without dependencies complete within 5% of current baseline
9. [ ] Progress display shows "Wave X/Y (N subgoals)..." with ✓/✗/⚠ status markers (emoji only, no colors)
10. [ ] Logging: INFO for waves, DEBUG for sort details (via `--verbose` flag)
11. [ ] `verify_lite` rejects plans with invalid `depends_on` references
12. [ ] All existing collect.py tests continue to pass
13. [ ] Final summary: "EXECUTION COMPLETE: X/N succeeded, Y failed, Z partial" appears after all waves
14. [ ] Verbose mode: `--verbose` flag shows DEBUG logs for topological sort and context assembly
15. [ ] Default mode: Clean user-friendly output without DEBUG logs

---

## 13. References

- **spawn_sequential**: `packages/spawner/src/aurora_spawner/spawner.py:849-893`
- **spawn_parallel_tracked**: `packages/spawner/src/aurora_spawner/spawner.py:896+`
- **verify_lite**: `packages/soar/src/aurora_soar/phases/verify.py:19-198`
- **execute_agents**: `packages/soar/src/aurora_soar/phases/collect.py:180-362`
- **Kahn's algorithm**: https://en.wikipedia.org/wiki/Topological_sorting#Kahn's_algorithm
