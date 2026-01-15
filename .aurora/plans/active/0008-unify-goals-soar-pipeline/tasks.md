# Tasks: Unify Goals with SOAR Pipeline

**Total**: 14 tasks across 4 phases
**Estimated code change**: +300 lines, -1200 lines (net -900)

---

## Phase 1: Add plan_only() to SOAR (4 tasks)

**Goal**: Add planning-only method to SOAROrchestrator

- [ ] 1. Create PlanResult dataclass
  <!-- agent: @full-stack-dev -->
  - Location: `packages/soar/src/aurora_soar/models.py`
  - Fields: complexity, code_chunks, file_resolutions, subgoals, agent_assignments, agent_gaps, context_summary, decomposition_source, timing_ms
  - **Validation**: `mypy packages/soar --strict`

- [ ] 2. Implement _build_file_resolutions() helper
  <!-- agent: @full-stack-dev -->
  - Location: `packages/soar/src/aurora_soar/orchestrator.py`
  - Maps Phase 2 code chunks to subgoals by relevance
  - Uses keyword overlap + activation scores
  - Returns `dict[str, list[FileResolution]]`
  - **Validation**: Unit test with mock chunks

- [ ] 3. Implement plan_only() method
  <!-- agent: @full-stack-dev -->
  - Location: `packages/soar/src/aurora_soar/orchestrator.py`
  - Calls phases 1-4: assess, retrieve, decompose, verify
  - Stops before collect (execution)
  - Returns PlanResult
  - **Validation**: Integration test with indexed memory

- [ ] 4. Write unit tests for plan_only()
  <!-- agent: @qa-test-architect -->
  - Location: `packages/soar/tests/test_orchestrator_plan.py`
  - Test: returns code chunks from Phase 2
  - Test: file resolutions derived from chunks
  - Test: context_files injection works
  - **Validation**: `pytest packages/soar/tests/test_orchestrator_plan.py -v`

---

## Phase 2: Wire Goals to SOAR (4 tasks)

**Goal**: Refactor aur goals to use plan_only()

- [ ] 5. Create _convert_to_goals_json() helper
  <!-- agent: @full-stack-dev -->
  - Location: `packages/cli/src/aurora_cli/commands/goals.py`
  - Converts PlanResult to existing goals.json schema
  - Preserves backward compatibility
  - **Validation**: Compare output with old goals.json format

- [ ] 6. Refactor goals_command() to use plan_only()
  <!-- agent: @full-stack-dev -->
  - Replace PlanDecomposer/AgentRecommender with orchestrator.plan_only()
  - Keep CLI flags unchanged (--context, --verbose, --format)
  - Pass context_files to plan_only()
  - **Validation**: `aur goals "test goal" -v` shows code chunks

- [ ] 7. Update verbose output to show code context
  <!-- agent: @full-stack-dev -->
  - Display number of code chunks retrieved
  - Show context summary from Phase 3
  - Display timing breakdown by phase
  - **Validation**: Manual verification of verbose output

- [ ] 8. Write integration tests for new goals flow
  <!-- agent: @qa-test-architect -->
  - Test: goals output format unchanged
  - Test: file resolutions have higher confidence
  - Test: --context flag works with plan_only()
  - **Validation**: `pytest tests/integration/test_goals.py -v`

---

## Phase 3: Delete Redundant Code (3 tasks)

**Goal**: Remove code superseded by SOAR integration

- [ ] 9. Delete PlanDecomposer class
  <!-- agent: @full-stack-dev -->
  - Remove `packages/cli/src/aurora_cli/planning/decompose.py`
  - Update imports in dependent files
  - **Validation**: `make lint` passes, no import errors

- [ ] 10. Delete AgentRecommender class
  <!-- agent: @full-stack-dev -->
  - Remove agent assignment code from `planning/agents.py`
  - Keep AgentGap model (used by SOAR verify)
  - Update imports
  - **Validation**: `make lint` passes

- [ ] 11. Simplify planning/core.py
  <!-- agent: @full-stack-dev -->
  - Remove `create_plan()` complex logic
  - Keep only format conversion utilities
  - Remove memory search (done by SOAR retrieve)
  - **Validation**: Goals command still works, tests pass

---

## Phase 4: Quality Improvements (3 tasks)

**Goal**: Improve file resolution and add documentation

- [ ] 12. Enhance file resolution relevance scoring
  <!-- agent: @full-stack-dev -->
  - Improve `_build_file_resolutions()` algorithm
  - Add semantic similarity if embeddings available
  - Weight by activation score from memory
  - **Validation**: File resolutions more accurate (manual review)

- [ ] 13. Add verbose context display
  <!-- agent: @full-stack-dev -->
  - Show actual code snippets in very verbose mode (-vv)
  - Display which chunks matched which subgoals
  - **Validation**: `aur goals "test" -vv` shows code

- [ ] 14. Update documentation
  <!-- agent: @full-stack-dev -->
  - Update `docs/commands/aur-goals.md`
  - Document that goals now uses SOAR phases
  - Add troubleshooting for memory indexing
  - **Validation**: Docs accurate and complete

---

## Validation Commands

After each phase:

```bash
# Type check
mypy packages/soar packages/cli --strict

# Unit tests
pytest packages/soar/tests/ -v
pytest tests/unit/cli/ -v

# Integration tests
pytest tests/integration/test_goals.py -v

# Full test suite
make test-unit

# Lint
ruff check packages/soar packages/cli

# Manual verification
aur goals "Add authentication" -v  # Should show code chunks
```

---

## Dependency Graph

```
Phase 1 (SOAR plan_only)
  1 → 2 → 3 → 4
              │
              ▼
Phase 2 (Wire goals)
  5 → 6 → 7 → 8
              │
              ▼
Phase 3 (Delete code)
  9, 10, 11 (parallel)
              │
              ▼
Phase 4 (Polish)
  12 → 13 → 14
```

---

## Definition of Done

- [ ] `aur goals` uses SOAR phases 1-4 via `plan_only()`
- [ ] LLM sees actual code during decomposition
- [ ] File resolutions derived from Phase 2 retrieval
- [ ] goals.json format unchanged (backward compatible)
- [ ] ~1200 lines deleted from planning/
- [ ] All tests pass
- [ ] Documentation updated
