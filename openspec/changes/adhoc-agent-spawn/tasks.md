# Tasks: Ad-hoc Agent Spawning

## Overview
Implementation tasks for adding ad-hoc agent inference to `aur spawn`, enabling automatic agent definition generation for missing agents.

## Task Breakdown

### Phase 1: Core Inference Infrastructure (Est: 4-6 hours)

- [ ] 1. Create inference prompt template
  - Create `packages/reasoning/src/aurora_reasoning/prompts/infer_agent.py`
  - Define `INFER_AGENT_PROMPT` for single agent inference
  - Define `INFER_BATCH_PROMPT` for batch inference
  - Add helper function `format_infer_agent_prompt(task_desc, agent_id)`
  - **Validation**: Prompts generate valid JSON with role + goal fields
  - **Test coverage**: Unit tests in `tests/unit/reasoning/test_infer_agent_prompts.py`

- [ ] 2. Implement InferredAgent model
  - Create `packages/spawner/src/aurora_spawner/models.py::InferredAgent` dataclass
  - Fields: `id`, `role`, `goal`, `confidence`
  - Add `to_dict()` and `from_dict()` serialization methods
  - Add `to_agent_info()` conversion to AgentInfo model
  - **Validation**: Model validates role (≤200 chars) and goal (≤500 chars)
  - **Test coverage**: Unit tests in `tests/unit/spawner/test_models_adhoc.py`

- [ ] 3. Implement AdHocAgentInferrer
  - Create `packages/spawner/src/aurora_spawner/adhoc_inference.py`
  - Implement `AdHocAgentInferrer` class with `__init__(llm_client)`
  - Implement `infer_agent(task_desc, agent_id)` → `InferredAgent`
  - Implement `infer_batch(tasks)` → `dict[agent_id, InferredAgent]`
  - Implement `validate_agent(agent)` → `bool`
  - Add error handling for LLM failures
  - **Validation**: Successfully infers agents from sample tasks
  - **Test coverage**: Unit tests with mocked LLM responses
  - **Dependencies**: Requires task 1 (prompts) and task 2 (model)

- [ ] 4. Implement AdHocAgentCache
  - Create `packages/spawner/src/aurora_spawner/adhoc_cache.py`
  - Implement `AdHocAgentCache` class
  - Methods: `store()`, `get()`, `has()`, `clear()`, `size()`
  - Session-scoped lifecycle
  - **Validation**: Cache correctly stores and retrieves agents
  - **Test coverage**: Unit tests in `tests/unit/spawner/test_adhoc_cache.py`

### Phase 2: CLI Integration (Est: 3-4 hours)

- [ ] 5. Add CLI flags to spawn command
  - Update `packages/cli/src/aurora_cli/commands/spawn.py`
  - Add `--adhoc` flag (boolean, default=False)
  - Add `--adhoc-log` flag (path, optional)
  - Update docstring and help text
  - **Validation**: Flags are recognized and parsed correctly
  - **Test coverage**: Unit tests in `tests/unit/cli/test_spawn_adhoc_flags.py`

- [ ] 6. Implement missing agent detection
  - Create helper `detect_missing_agents(tasks, manifest)` → `list[str]`
  - Compare task.agent against manifest.agents
  - Exclude "self" from detection
  - Handle None/empty agent gracefully
  - **Validation**: Correctly identifies missing agents from task list
  - **Test coverage**: Unit tests with various task/manifest combinations
  - **Dependencies**: Requires task 5 (CLI flags)

- [ ] 7. Implement inference orchestration
  - Create helper `infer_missing_agents(tasks, missing_ids)` → `dict[str, InferredAgent]`
  - Initialize AdHocAgentInferrer with LLM client
  - Build task→agent mapping
  - Call batch inference for efficiency
  - Handle inference failures gracefully
  - Log inferred agents to console (verbose mode)
  - **Validation**: Successfully infers multiple agents in one call
  - **Test coverage**: Integration tests with mocked LLM
  - **Dependencies**: Requires task 3 (inferrer) and task 6 (detection)

- [ ] 8. Implement ad-hoc log export
  - Create helper `save_inferred_agents(inferred, output_path)`
  - Export inferred agents to JSON file
  - Include role, goal, confidence, timestamp
  - Create parent directory if needed
  - **Validation**: JSON file is valid and contains all agents
  - **Test coverage**: Unit tests in `tests/unit/cli/test_adhoc_log.py`

- [ ] 9. Wire spawn command with ad-hoc workflow
  - Update `spawn_command()` main logic
  - Call `detect_missing_agents()` after loading tasks
  - If missing and not --adhoc: fail fast with clear error
  - If missing and --adhoc: call `infer_missing_agents()`
  - Pass inferred agents to `execute_tasks()`
  - If --adhoc-log: call `save_inferred_agents()`
  - **Validation**: Full workflow executes without errors
  - **Test coverage**: Integration tests with real task files
  - **Dependencies**: Requires tasks 6, 7, 8

### Phase 3: Spawner Integration (Est: 2-3 hours)

- [ ] 10. Update spawn() function signature
  - Update `packages/spawner/src/aurora_spawner/spawner.py::spawn()`
  - Add parameter `agent_info: InferredAgent | None = None`
  - Update docstring with agent_info documentation
  - **Validation**: Function signature is backward compatible
  - **Test coverage**: Unit tests verify parameter handling

- [ ] 11. Implement agent context passing
  - In `spawn()`, check if `agent_info` is provided
  - If provided, inject role/goal into prompt as system message
  - Format: "Acting as {role} ({goal})\n\n{original_prompt}"
  - Ensure proper escaping of role/goal text
  - **Validation**: Spawned tasks receive agent context in prompt
  - **Test coverage**: Integration tests verify context injection
  - **Dependencies**: Requires task 10

- [ ] 12. Update spawn_parallel() and spawn_sequential()
  - Add `agent_info_map: dict[int, InferredAgent]` parameter
  - Pass `agent_info` to individual `spawn()` calls
  - Update docstrings
  - **Validation**: Parallel/sequential execution works with ad-hoc agents
  - **Test coverage**: Integration tests with multiple ad-hoc agents
  - **Dependencies**: Requires task 11

- [ ] 13. Update execute_tasks() helpers
  - Update `_execute_parallel()` and `_execute_sequential()`
  - Build agent_info_map from inferred agents
  - Pass map to spawn_parallel/spawn_sequential
  - **Validation**: Tasks with ad-hoc agents execute correctly
  - **Test coverage**: Integration tests in spawn command
  - **Dependencies**: Requires task 12

### Phase 4: Testing & Documentation (Est: 2-3 hours)

- [ ] 14. Write comprehensive unit tests
  - Test inference with various task descriptions
  - Test cache hit/miss scenarios
  - Test validation edge cases (empty role, long goal, etc.)
  - Test error handling (LLM timeout, invalid JSON)
  - Mock LLM responses for deterministic testing
  - **Validation**: 95%+ coverage for new modules
  - **Test coverage**: ~15 unit tests across all modules

- [ ] 15. Write integration tests
  - Test end-to-end workflow: task file → inference → execution
  - Test batch inference with 3+ missing agents
  - Test --adhoc-log export
  - Test failure modes: inference fails, validation fails
  - Test cache prevents duplicate inferences
  - **Validation**: All integration tests pass
  - **Test coverage**: ~5 integration tests in `tests/integration/`

- [ ] 16. Write E2E tests
  - Create `tests/e2e/test_spawn_adhoc_e2e.py`
  - Test real task file with missing agents
  - Test --adhoc flag behavior
  - Test error messages without --adhoc
  - **Validation**: Real-world scenario works end-to-end
  - **Test coverage**: 2-3 E2E tests

- [ ] 17. Update documentation
  - Update `docs/commands/aur-spawn.md` with --adhoc flag docs
  - Add "Ad-hoc Agent Inference" section explaining workflow
  - Add examples showing missing agent detection
  - Document --adhoc-log flag and JSON format
  - Add troubleshooting section for common issues
  - **Validation**: Documentation is clear and complete

- [ ] 18. Create example task files
  - Create `examples/spawn/adhoc-tasks.md` with missing agents
  - Create `examples/spawn/adhoc-output.json` showing inferred agents
  - Add README explaining ad-hoc workflow
  - **Validation**: Examples run successfully with --adhoc

- [ ] 19. Update CHANGELOG
  - Add entry for "Ad-hoc Agent Inference" feature
  - Document new --adhoc and --adhoc-log flags
  - Note: feature is opt-in, existing behavior unchanged
  - **Validation**: CHANGELOG follows project conventions

### Phase 5: Polish & Review (Est: 1-2 hours)

- [ ] 20. Run full test suite
  - Execute `make test` and verify all tests pass
  - Fix any regressions or test failures
  - Ensure no breaking changes to existing spawn behavior
  - **Validation**: 0 test failures, no coverage regression

- [ ] 21. Run type checking
  - Execute `make type-check` (mypy)
  - Fix any type errors in new code
  - **Validation**: 0 type errors

- [ ] 22. Run linting
  - Execute `make lint` (ruff)
  - Fix any linting violations
  - **Validation**: 0 linting errors

- [ ] 23. Performance validation
  - Measure inference time for single agent (target: <2s)
  - Measure batch inference for 5 agents (target: <3s)
  - Verify cache reduces duplicate inferences
  - **Validation**: Performance meets targets

- [ ] 24. Update project.md
  - Add ad-hoc inference to feature list in `openspec/project.md`
  - Document new inference module location
  - **Validation**: project.md accurately reflects changes

## Task Parallelization

**Can run in parallel**:
- Tasks 1, 2, 4 (independent infrastructure)
- Tasks 14, 15, 16 (different test types)
- Tasks 17, 18, 19 (different documentation)

**Must run sequentially**:
- Task 3 depends on 1, 2
- Task 7 depends on 3, 6
- Task 9 depends on 6, 7, 8
- Tasks 10-13 are sequential (spawner integration)
- Tasks 20-24 are sequential (polish phase)

## Estimated Timeline

- **Phase 1**: 4-6 hours
- **Phase 2**: 3-4 hours
- **Phase 3**: 2-3 hours
- **Phase 4**: 2-3 hours
- **Phase 5**: 1-2 hours

**Total**: 12-18 hours of development time

## Success Metrics

- [ ] All 24 tasks completed
- [ ] 95%+ test coverage for new modules
- [ ] 0 breaking changes to existing spawn behavior
- [ ] Inference completes in <2s per agent
- [ ] Documentation complete and clear
- [ ] All tests pass (unit, integration, E2E)
- [ ] 0 type errors, 0 linting violations
