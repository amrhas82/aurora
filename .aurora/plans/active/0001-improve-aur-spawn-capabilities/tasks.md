# Tasks: Improve aur spawn with Adhoc Agent Spawning

**Total**: 11 tasks across 4 phases
**Agent assignments**: Based on goals.json subgoals
**Estimated effort**: ~1 week

---

## Phase 1: Gap Loading & Validation (3 tasks)

**Goal**: Read and validate agent gaps from goals.json

**Agent**: @holistic-architect (design), @full-stack-dev (implementation)

- [ ] 1. Add goals.json loading to spawn command
  - Modify `packages/cli/src/aurora_cli/commands/spawn.py`
  - Add function `load_goals_json(plan_path: Path) -> Goals | None`
  - Handle missing file gracefully (return None)
  - **Validation**: Unit test loads valid goals.json, handles missing file

- [ ] 2. Extract agent gaps from Goals model
  - Use existing `Goals.gaps: list[AgentGap]` from `planning/models.py`
  - Filter gaps with confidence < 0.5
  - **Validation**: Unit test extracts gaps correctly from Goals object

- [ ] 3. Map gaps to task IDs
  - Create `gap_map: dict[task_id, AgentGap]` for O(1) lookup
  - Handle subgoal_id → task_id mapping
  - **Validation**: Unit test verifies gap_map creation from sample goals.json

---

## Phase 2: Adhoc Agent Generation (3 tasks)

**Goal**: Generate agent prompts from gap metadata

**Agent**: @full-stack-dev

- [ ] 4. Create adhoc agent prompt builder
  - New file: `packages/spawner/src/aurora_spawner/adhoc.py`
  - Function: `build_adhoc_prompt(gap: AgentGap, task: str, context: str) -> str`
  - Template format:
    ```
    You are {gap.ideal_agent}. {gap.ideal_agent_desc}

    Task: {task}

    Context: {context}

    Provide a specialized response based on your expertise.
    ```
  - **Validation**: Unit test generates prompt from AgentGap sample

- [ ] 5. Implement adhoc agent caching
  - Add `AdhocAgentCache` class in `adhoc.py`
  - Cache key: `gap.ideal_agent` (agent ID)
  - Cache value: generated prompt template
  - **Validation**: Unit test verifies cache hit/miss behavior

- [ ] 6. Integrate adhoc prompt into SpawnTask
  - Modify `packages/spawner/src/aurora_spawner/models.py`
  - Add `adhoc_prompt: str | None` field to `SpawnTask`
  - If adhoc_prompt set, use it instead of default agent
  - **Validation**: Unit test creates SpawnTask with adhoc_prompt

---

## Phase 3: Dynamic Routing & Execution (3 tasks)

**Goal**: Route tasks to adhoc agents when gaps detected

**Agent**: @full-stack-dev

- [ ] 7. Modify spawn execution to check for gaps
  - In `packages/cli/src/aurora_cli/commands/spawn.py`
  - Before spawning each task:
    1. Check if task_id in gap_map
    2. If yes, build adhoc prompt from gap
    3. Set `spawn_task.adhoc_prompt`
  - **Validation**: Integration test spawns task with adhoc agent

- [ ] 8. Update spawner to use adhoc prompts
  - Modify `packages/spawner/src/aurora_spawner/spawner.py`
  - In `spawn()` function:
    - If `task.adhoc_prompt` is set, use it as prompt
    - Otherwise, use task.prompt as before
  - **Validation**: Unit test verifies adhoc prompt usage in spawn

- [ ] 9. Add adhoc agent tracking
  - Track which tasks used adhoc agents: `adhoc_agents_used: list[str]`
  - Store in spawn result metadata
  - **Validation**: Integration test verifies tracking

---

## Phase 4: Reporting & Testing (2 tasks)

**Goal**: User-visible reporting and comprehensive tests

**Agent**: @qa-test-architect (testing), @full-stack-dev (reporting)

- [ ] 10. Add adhoc agent reporting to spawn output
  - Display after execution summary:
    ```
    Adhoc Agents Used:
      - @specialized-qa (sg-1: Test authentication flow)
      - @domain-expert (sg-3: Validate business logic)
    ```
  - Color code: yellow for adhoc agents
  - **Validation**: Manual test verifies output format

- [ ] 11. Write comprehensive test suite
  - Unit tests:
    - `test_load_goals_json()` - Gap loading
    - `test_build_adhoc_prompt()` - Prompt generation
    - `test_adhoc_cache()` - Caching behavior
    - `test_gap_routing()` - Task routing logic
  - Integration tests:
    - `test_spawn_with_gaps_e2e()` - Full workflow
    - `test_spawn_without_gaps()` - No regression
    - `test_spawn_missing_goals()` - Graceful fallback
  - **Validation**: `pytest packages/cli/tests/test_spawn_adhoc.py` - all pass, 95%+ coverage

---

## Dependency Graph

```
Phase 1 (Gap Loading)
  ├─> Phase 2 (Adhoc Generation)
  │   └─> Phase 3 (Dynamic Routing)
  │       └─> Phase 4 (Reporting & Tests)

Parallelizable:
- Tasks 1-2 (both read-only operations)
- Tasks 4-5 (independent utilities)
```

---

## Validation Commands

After each phase:

```bash
# Type checking
mypy packages/spawner packages/cli --strict

# Unit tests
pytest tests/unit/spawner/test_adhoc.py -v
pytest tests/unit/cli/test_spawn_gaps.py -v

# Integration tests
pytest tests/integration/test_spawn_with_gaps.py -v

# Coverage check
pytest --cov=aurora_spawner --cov=aurora_cli.commands.spawn --cov-report=term-missing

# E2E test (manual)
aur goals "Add authentication"  # Creates goals.json with gaps
aur spawn                       # Should use adhoc agents for gaps
```

---

## Example Execution Flow

**Before** (current behavior):
```bash
$ aur goals "Add specialized security audit"
✓ Goals created: 3 subgoals
⚠ Agent gaps detected: @security-auditor not found

$ aur spawn
Task 1: ❌ Failed - agent @security-auditor not available
```

**After** (with adhoc spawning):
```bash
$ aur goals "Add specialized security audit"
✓ Goals created: 3 subgoals
⚠ Agent gaps detected: @security-auditor not found

$ aur spawn
Reading gaps from goals.json...
Found 1 gap: @security-auditor
Creating adhoc agent from gap metadata...

Task 1: ✓ Completed (using adhoc @security-auditor)
Task 2: ✓ Completed (using @full-stack-dev)
Task 3: ✓ Completed (using adhoc @security-auditor)

Adhoc Agents Used:
  - @security-auditor (2 tasks): "Expert in security auditing..."

Execution complete: 3/3 tasks successful
```

---

## Definition of Done

Each task is complete when:
- [ ] Code written and type-checked (mypy --strict)
- [ ] Unit tests added (95%+ coverage)
- [ ] Integration tests where applicable
- [ ] Manual testing performed for user-facing features
- [ ] Code reviewed (self-review checklist)
- [ ] Documentation comments updated

---

## Testing Checklist

**Unit Tests** (per task):
- [ ] Happy path works
- [ ] Edge cases handled (None, empty, invalid input)
- [ ] Error cases return clear messages
- [ ] Type signatures correct

**Integration Tests** (Phase 4):
- [ ] Full workflow: goals → gaps → spawn → adhoc execution
- [ ] Backward compatibility: spawn without gaps unchanged
- [ ] Error recovery: missing goals.json doesn't break spawn
- [ ] Performance: gap loading adds <100ms overhead

---

## Risk Mitigation

**Risk: Adhoc agent quality lower than registry agents**
- Mitigation: Use detailed `ideal_agent_desc` from gap metadata
- Test: Compare output quality manually for sample tasks

**Risk: goals.json schema mismatch**
- Mitigation: Validate with pydantic Goals model
- Test: Unit tests with various schema versions

**Risk: Performance degradation**
- Mitigation: Cache adhoc prompts, lazy load gaps
- Test: Benchmark spawn time with/without gaps
