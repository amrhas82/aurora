# PRD: Dependency-Aware Execution

**PRD ID**: 0030
**Status**: Draft
**Author**: Claude + User
**Created**: 2026-01-20

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
| G3 | Handle failures gracefully | Failed subgoal's direct dependents are skipped; independent subgoals continue |
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
**I want** independent subgoals to continue executing
**So that** I get partial results rather than complete failure

**Example**:
- Subgoal 1 succeeds
- Subgoal 2 fails (timeout)
- Subgoal 3 (depends on 2) is skipped
- Subgoal 4 (depends on 1) executes with subgoal 1's output

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
- **FR2.2**: Accumulated context must include outputs from all successful dependencies
- **FR2.3**: Format each dependency output as `[sg-{index}]: {output}`
- **FR2.4**: Pass full outputs (no truncation in initial implementation)

### FR3: Failure Handling
The system must handle subgoal failures gracefully:
- **FR3.1**: When a subgoal fails (after `spawn_parallel_tracked` exhausts retries and fallback), mark it as failed
- **FR3.2**: Skip only direct dependents of failed subgoals
- **FR3.3**: Continue executing independent subgoals in subsequent waves
- **FR3.4**: Timeout is treated as failure after retry/fallback exhaustion (existing behavior)

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
- **FR5.3**: Show skipped subgoals with reason (dependency failed)

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

Execution:
  Wave 1: [sg-1] → spawn_parallel_tracked([sg-1])
  Wave 2: [sg-2, sg-3] → spawn_parallel_tracked([sg-2, sg-3]) with sg-1 output in context
  Wave 3: [sg-4] → spawn_parallel_tracked([sg-4]) with sg-2, sg-3 outputs in context

If sg-2 fails:
  Wave 3: sg-4 is SKIPPED (depends on sg-2)
  Result: sg-1 (success), sg-2 (failed), sg-3 (success), sg-4 (skipped)
```

### 6.3 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Parallel execution per wave | Reuse `spawn_parallel_tracked` | Don't reinvent parallel execution; leverage existing retry/fallback |
| Context format | Reuse `spawn_sequential` format | Consistency with existing patterns |
| Dependency validation | Strengthen `verify_lite` | Plan-time validation, not runtime |
| Failure handling | Skip only direct dependents | Maximize completion while respecting dependencies |
| Wave-level retry | None | `spawn_parallel_tracked` handles retries within each wave |

---

## 7. Technical Considerations

### 7.1 Implementation Scope (~50 LOC)

#### collect.py changes (~45 LOC)

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

    # Skip subgoals whose dependencies failed
    executable = [sg for sg in wave
                  if not any(d in failed_subgoals for d in sg.get("depends_on", []))]

    # Inject previous outputs using spawn_sequential format
    for sg in executable:
        deps = sg.get("depends_on", [])
        if deps:
            dep_outputs = [f"[sg-{idx}]: {outputs[idx].output}"
                          for idx in deps if idx in outputs and outputs[idx].success]
            if dep_outputs:
                accumulated = "\n".join(dep_outputs)
                # Modify prompt with context (similar to spawn_sequential)

    # Execute wave using EXISTING spawn_parallel_tracked
    results, meta = await spawn_parallel_tracked(wave_tasks, max_concurrent=4, ...)

    # Track results and failures
    for sg, result in zip(executable, results):
        idx = sg["subgoal_index"]
        outputs[idx] = result
        if not result.success:
            failed_subgoals.add(idx)
            logger.warning(f"Subgoal {idx} failed, dependents will be skipped")
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
| `packages/soar/src/aurora_soar/phases/collect.py` | Add `topological_sort()`, modify `execute_agents()` | ~45 |
| `packages/soar/src/aurora_soar/phases/verify.py` | Add missing dependency validation in `_check_circular_deps` | ~5 |
| `packages/soar/tests/test_phases/test_collect.py` | New test cases | ~100 |
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
| `test_failure_skips_dependents` | Failed subgoal causes dependent to skip |
| `test_independent_subgoals_continue` | Non-dependent subgoals execute despite failures |
| `test_no_deps_single_wave` | Performance baseline - no regression |

### Validation Tests

| Test | Description |
|------|-------------|
| `test_verify_lite_invalid_dependency_ref` | Invalid `depends_on` reference caught |
| `test_verify_lite_valid_deps_pass` | Valid dependencies pass verification |

### Performance Tests

| Test | Description |
|------|-------------|
| `test_no_deps_performance_regression` | Queries without dependencies complete within 5% of baseline |

---

## 10. Open Questions

1. **Context size limits**: Should we set a max size for accumulated context to prevent prompt overflow?
   - **Current answer**: Start with full outputs, optimize if needed

2. **Partial dependency success**: If sg-1 succeeds and sg-2 fails, should sg-3 (depends on both) receive sg-1's output or be skipped entirely?
   - **Current answer**: Skip entirely (any failed dependency causes skip)

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
3. [ ] Failed subgoal's direct dependents are skipped with appropriate log message
4. [ ] Independent subgoals continue executing despite failures in other chains
5. [ ] Performance: Queries without dependencies complete within 5% of current baseline
6. [ ] Progress display shows "Wave X/Y (N subgoals)..."
7. [ ] Logging: INFO for waves, DEBUG for sort details
8. [ ] `verify_lite` rejects plans with invalid `depends_on` references
9. [ ] All existing collect.py tests continue to pass

---

## 13. References

- **spawn_sequential**: `packages/spawner/src/aurora_spawner/spawner.py:849-893`
- **spawn_parallel_tracked**: `packages/spawner/src/aurora_spawner/spawner.py:896+`
- **verify_lite**: `packages/soar/src/aurora_soar/phases/verify.py:19-198`
- **execute_agents**: `packages/soar/src/aurora_soar/phases/collect.py:180-362`
- **Kahn's algorithm**: https://en.wikipedia.org/wiki/Topological_sorting#Kahn's_algorithm
