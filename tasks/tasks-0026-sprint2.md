# Sprint 2: SOAR Integration Tasks

**Estimated Time:** 6-8 hours
**Goal:** Wire spawner to SOAR collect phase and deprecate AgentRegistry

## Relevant Files

- `packages/soar/src/aurora_soar/phases/collect.py` - Contains `_mock_agent_execution()` stub to replace with real spawner
- `packages/soar/src/aurora_soar/phases/route.py` - Uses AgentRegistry, needs to use agent_discovery
- `packages/soar/src/aurora_soar/orchestrator.py` - Creates AgentRegistry instance in __init__
- `packages/soar/src/aurora_soar/agent_registry.py` - To be deprecated with warning
- `packages/spawner/src/aurora_spawner/spawner.py` - New spawner functions to integrate
- `packages/spawner/src/aurora_spawner/models.py` - SpawnTask and SpawnResult models
- `packages/cli/src/aurora_cli/agent_discovery/manifest.py` - ManifestManager for agent discovery
- `packages/cli/src/aurora_cli/agent_discovery/models.py` - AgentInfo, AgentManifest models
- `packages/soar/tests/test_phases/test_collect.py` - Existing collect phase tests to update
- `packages/soar/tests/test_phases/test_route.py` - Existing route phase tests to update
- `packages/soar/tests/test_orchestrator.py` - Orchestrator tests to update
- `packages/soar/tests/test_integration/test_soar_e2e.py` - E2E tests to verify integration

### Notes

- **TDD Approach:** Write tests first, watch them fail, implement minimal code to pass
- **Testing Framework:** pytest with pytest-asyncio for async tests
- **Mocking Strategy:** Use unittest.mock for subprocess calls and external dependencies
- **Integration Tests:** Create new integration tests that verify spawner + agent_discovery work together
- **Backward Compatibility:** AgentRegistry marked deprecated but not removed (deprecation warning only)
- **Error Handling:** Spawner failures should gracefully degrade (return AgentOutput with success=False)

## Tasks

- [x] 0.0 Create SOAR Test Infrastructure
  - [x] 0.1 Create test directory structure
    - Create `packages/soar/tests/` directory
    - Create `packages/soar/tests/__init__.py`
    - Create `packages/soar/tests/test_phases/` directory
    - Create `packages/soar/tests/test_phases/__init__.py`
    - Create `packages/soar/tests/test_integration/` directory
    - Create `packages/soar/tests/test_integration/__init__.py`
  - [x] 0.2 Create initial test files with basic structure
    - Create `packages/soar/tests/test_phases/test_collect.py` with imports and fixtures
    - Create `packages/soar/tests/test_phases/test_route.py` with imports and fixtures
    - Create `packages/soar/tests/test_orchestrator.py` with imports and fixtures
    - Add pytest configuration if needed
  - [x] 0.3 Verify test infrastructure works
    - Run `pytest packages/soar/tests/ -v` to verify structure
    - Add basic smoke tests that import the modules
    - Ensure all imports resolve correctly
    - **Run after completion**:
      - `ls -la packages/soar/tests/test_phases/` (verify __init__.py exists)
      - `ls -la packages/soar/tests/test_integration/` (verify __init__.py exists)
      - `pytest packages/soar/tests/ -v --collect-only` (should collect tests without errors)
      - `python3 -c "from aurora_soar.phases import collect; from aurora_soar import orchestrator"` (verify imports work)

- [x] 1.0 Phase 3: Wire Spawner to SOAR Collect Phase
  - [x] 1.1 Write tests for spawner integration in collect phase (TDD)
    - Create `test_execute_agent_with_spawner()` test that mocks spawner.spawn()
    - Create `test_execute_agent_spawner_timeout()` test for timeout handling
    - Create `test_execute_agent_spawner_failure()` test for graceful degradation
    - Create `test_convert_spawn_result_to_agent_output()` test for result conversion
    - Verify tests fail with current mock implementation
    - **Run after completion**:
      - `pytest packages/soar/tests/test_phases/test_collect.py::test_execute_agent_with_spawner -xvs` (should FAIL - we're in TDD RED phase)
      - `grep -c "def test_execute_agent" packages/soar/tests/test_phases/test_collect.py` (should be >= 4 tests)
  - [x] 1.2 Implement `_execute_agent()` function to replace `_mock_agent_execution()`
    - Add import at top: `from aurora_spawner import spawn, SpawnTask, SpawnResult`
    - Create new `_execute_agent()` function in `collect.py`
    - Build agent prompt from subgoal description and context
    - Create SpawnTask with prompt, agent ID, and timeout
    - Call `spawn()` function (imported from aurora_spawner)
    - Convert SpawnResult to AgentOutput format
    - Handle spawner errors gracefully (return failed AgentOutput)
    - Preserve execution metadata (duration_ms, tools_used, model_used)
    - **Run after completion**:
      - `python3 -c "from aurora_soar.phases.collect import _execute_agent"` (verify function exists)
      - `grep "from aurora_spawner import.*spawn" packages/soar/src/aurora_soar/phases/collect.py` (verify import added)
  - [x] 1.3 Replace `_mock_agent_execution()` call in `_execute_single_subgoal()`
    - Find the line calling `_mock_agent_execution(idx, subgoal, agent, context)`
    - Replace with `_execute_agent(agent, subgoal, context)` (updated signature)
    - Pass through agent_info, subgoal, and context
    - Verify timeout parameter is respected
    - Note: Import already added in task 1.2
    - **Run after completion**:
      - `! grep "_mock_agent_execution" packages/soar/src/aurora_soar/phases/collect.py` (should find nothing - mock removed)
      - `grep "_execute_agent" packages/soar/src/aurora_soar/phases/collect.py` (should find the call)
      - `pytest packages/soar/tests/test_phases/test_collect.py::test_execute_agent_with_spawner -xvs` (should PASS - TDD GREEN phase)
  - [x] 1.4 Write tests for parallel collect mode with real spawner (TDD)
    - Create `test_collect_parallel_with_spawner()` integration test
    - Mock spawner.spawn_parallel() with multiple concurrent calls
    - Verify semaphore limiting (max 5 concurrent)
    - Test that results maintain input order
    - Verify all AgentOutput objects have correct subgoal_index
    - **Run after completion**:
      - `pytest packages/soar/tests/test_phases/test_collect.py::test_collect_parallel_with_spawner -xvs` (should FAIL - TDD RED phase)
      - `grep -c "spawn_parallel" packages/soar/tests/test_phases/test_collect.py` (should be >= 1)
  - [x] 1.5 Implement parallel spawning in collect phase
    - Create `_build_agent_prompt()` helper function
    - In `_execute_parallel_subgoals()`, build SpawnTask list for all subgoals
    - Call `spawn_parallel()` (not spawner.spawn_parallel) with max_concurrent=5
    - Convert all SpawnResults to AgentOutputs
    - Handle partial failures (some agents succeed, some fail)
    - Update execution metadata with parallel timing
    - **Run after completion**:
      - `grep "def _build_agent_prompt" packages/soar/src/aurora_soar/phases/collect.py` (verify helper exists)
      - `grep "spawn_parallel.*max_concurrent" packages/soar/src/aurora_soar/phases/collect.py` (verify parallel call)
      - `pytest packages/soar/tests/test_phases/test_collect.py::test_collect_parallel_with_spawner -xvs` (should PASS - TDD GREEN)
  - [x] 1.6 Add tests for collect phase with spawner (extend test_collect.py)
    - Add tests for `_execute_agent()` function with various scenarios
    - Add proper mocking for `spawn()` calls (mock at aurora_spawner.spawn)
    - Test timeout handling with spawner
    - Test error handling when spawner fails
    - Test successful spawner execution and AgentOutput conversion
    - Verify all edge cases are covered
    - **Run after completion**:
      - `pytest packages/soar/tests/test_phases/test_collect.py -v` (all tests should pass)
      - `pytest packages/soar/tests/test_phases/test_collect.py --co -q | wc -l` (count collected tests, should be >= 7)
  - [x] 1.7 Create integration test for end-to-end spawner execution
    - Create new test file `test_spawner_integration.py` in `packages/soar/tests/`
    - Write `test_soar_with_spawner_mock()` that mocks subprocess but uses real spawner
    - Verify complete flow: orchestrator → collect → spawn → AgentOutput
    - Test both parallel and sequential execution modes
    - Verify cost tracking includes spawner operations
    - **Run after completion**:
      - `test -f packages/soar/tests/test_spawner_integration.py && echo "File exists"` (verify file created)
      - `pytest packages/soar/tests/test_spawner_integration.py -xvs` (integration test should pass)
      - `grep -c "def test_" packages/soar/tests/test_spawner_integration.py` (should have >= 2 tests)

- [x] 2.0 Phase 4: Deprecate AgentRegistry
  - [x] 2.1 Write tests for ManifestManager adapter (TDD)
    - Create `test_agent_discovery_adapter.py` in `packages/soar/tests/`
    - Write `test_load_agents_from_manifest()` that loads real agent files
    - Write `test_get_agent_by_id()` using ManifestManager
    - Write `test_list_all_agents()` using ManifestManager
    - Write `test_create_fallback_agent()` for missing agents
    - Verify tests fail without adapter implementation
    - **Run after completion**:
      - `test -f packages/soar/tests/test_agent_discovery_adapter.py && echo "File exists"` (verify created)
      - `pytest packages/soar/tests/test_agent_discovery_adapter.py -xvs` (should FAIL - TDD RED phase)
      - `pytest packages/soar/tests/test_agent_discovery_adapter.py --co -q | wc -l` (should have >= 4 tests)
  - [x] 2.2 Create adapter module for agent_discovery in SOAR package
    - Create `packages/soar/src/aurora_soar/discovery_adapter.py`
    - Implement `get_manifest_manager()` function that returns ManifestManager instance
    - Implement `convert_agent_info()` to convert AgentInfo → AgentRegistry.AgentInfo
    - Implement `get_agent()` function using ManifestManager.get_agent()
    - Implement `list_agents()` function using ManifestManager.manifest.agents
    - Add proper error handling for missing manifest
    - **Run after completion**:
      - `python3 -c "from aurora_soar.discovery_adapter import get_manifest_manager, convert_agent_info"` (verify imports)
      - `pytest packages/soar/tests/test_agent_discovery_adapter.py -xvs` (should PASS - TDD GREEN phase)
  - [x] 2.3 Update SOAR orchestrator to use agent_discovery (TDD first)
    - Write test `test_orchestrator_uses_manifest_manager()` in `test_orchestrator.py`
    - Write test `test_orchestrator_fallback_agent_from_discovery()`
    - Update `orchestrator.py` __init__ to accept optional ManifestManager
    - Remove AgentRegistry instantiation from __init__
    - Import discovery_adapter module
    - Call `get_manifest_manager()` to initialize agent discovery
    - Update all agent lookups to use adapter functions
    - Verify backward compatibility with existing tests
    - **Run after completion**:
      - `! grep "AgentRegistry()" packages/soar/src/aurora_soar/orchestrator.py` (no instantiation - should find nothing)
      - `grep "discovery_adapter" packages/soar/src/aurora_soar/orchestrator.py` (verify adapter imported)
      - `pytest packages/soar/tests/test_orchestrator.py -xvs` (all tests should pass)
  - [x] 2.4 Update route phase to use agent_discovery (TDD first)
    - Write test `test_route_with_manifest_manager()` in `test_route.py`
    - Update `route.py` imports to use discovery_adapter
    - Modify `route_subgoals()` signature to accept ManifestManager instead of AgentRegistry
    - Update `_route_single_subgoal()` to use adapter.get_agent()
    - Update capability search to use ManifestManager.agents filtering
    - Update fallback agent creation to use discovery system
    - Verify all route tests pass with new discovery system
    - **Run after completion**:
      - `grep "discovery_adapter" packages/soar/src/aurora_soar/phases/route.py` (verify adapter used)
      - `! grep -E "AgentRegistry\(" packages/soar/src/aurora_soar/phases/route.py` (no instantiation)
      - `pytest packages/soar/tests/test_phases/test_route.py -xvs` (all tests pass)
  - [x] 2.5 Add deprecation warning to AgentRegistry
    - Add `import warnings` to `agent_registry.py`
    - In `AgentRegistry.__init__()`, add deprecation warning:
      ```python
      warnings.warn(
          "AgentRegistry is deprecated. Use aurora_cli.agent_discovery.ManifestManager instead.",
          DeprecationWarning,
          stacklevel=2
      )
      ```
    - Add deprecation notice to AgentRegistry docstring
    - Create migration guide comment explaining how to switch to agent_discovery
    - **Run after completion**:
      - `grep "import warnings" packages/soar/src/aurora_soar/agent_registry.py` (verify import added)
      - `grep "DeprecationWarning" packages/soar/src/aurora_soar/agent_registry.py` (verify warning added)
      - `python3 -W default::DeprecationWarning -c "from aurora_soar.agent_registry import AgentRegistry; AgentRegistry()" 2>&1 | grep -i deprecat` (test warning fires)
  - [x] 2.6 Update all SOAR tests to work with new discovery system
    - Update `test_orchestrator.py` to mock ManifestManager instead of AgentRegistry
    - Update `test_route.py` to use ManifestManager in fixtures
    - Update any E2E tests that create AgentRegistry directly
    - Add assertions to verify deprecation warnings are raised
    - Verify test coverage remains >= 90%
    - **Run after completion**:
      - `grep -c "ManifestManager" packages/soar/tests/test_orchestrator.py` (should find multiple references)
      - `pytest packages/soar/tests/ -xvs` (all tests should pass)
      - `pytest packages/soar/tests/ --cov=aurora_soar --cov-report=term | tail -1` (check coverage >= 90%)
  - [x] 2.7 Create migration integration test
    - Create `test_agent_registry_deprecation.py`
    - Write test that uses old AgentRegistry and verifies warning
    - Write test that uses new ManifestManager and verifies no warning
    - Write test comparing results from both systems (should be equivalent)
    - Document migration path in test comments
    - **Run after completion**:
      - `test -f packages/soar/tests/test_agent_registry_deprecation.py && echo "File exists"` (verify created)
      - `pytest packages/soar/tests/test_agent_registry_deprecation.py -xvs -W default::DeprecationWarning` (all tests pass)
      - `pytest packages/soar/tests/test_agent_registry_deprecation.py --co -q | wc -l` (should have >= 3 tests)

## Verification Steps

After completing all tasks:

1. **Run SOAR unit tests**: `pytest packages/soar/tests/test_phases/test_collect.py -v`
2. **Run SOAR integration tests**: `pytest packages/soar/tests/test_integration/ -v`
3. **Run orchestrator tests**: `pytest packages/soar/tests/test_orchestrator.py -v`
4. **Check test coverage**: `pytest packages/soar/tests/ --cov=aurora_soar --cov-report=term-missing`
   - Target: >= 90% coverage for modified files
5. **Verify deprecation warnings**: `pytest packages/soar/tests/ -W default::DeprecationWarning`
6. **End-to-end verification** (run these commands to verify complete integration):
   - `grep -c "from aurora_spawner import" packages/soar/src/aurora_soar/phases/collect.py` (should be 1 - spawner imported)
   - `! grep "_mock_agent_execution" packages/soar/src/aurora_soar/phases/collect.py` (should find nothing - mock removed)
   - `grep "discovery_adapter" packages/soar/src/aurora_soar/orchestrator.py` (adapter used in orchestrator)
   - `grep "DeprecationWarning" packages/soar/src/aurora_soar/agent_registry.py` (warning added)
   - `python3 -c "from aurora_soar.discovery_adapter import get_manifest_manager; print('✓ Adapter imports work')"` (verify adapter works)
   - `pytest packages/soar/tests/ -v --tb=short` (all tests pass)
   - `pytest packages/soar/tests/ --cov=aurora_soar --cov-report=term | grep TOTAL` (coverage >= 90%)

## Success Criteria

- [x] Test infrastructure created (task 0.0 complete)
- [x] All tests in `test_collect.py` pass with spawner integration
- [x] All tests in `test_route.py` pass with ManifestManager
- [x] All tests in `test_orchestrator.py` pass with agent_discovery
- [x] Deprecation warning appears when AgentRegistry is instantiated
- [x] Test coverage >= 90% for all modified files
- [x] No breaking changes to existing SOAR API
- [x] Integration test demonstrates end-to-end spawner + discovery flow
- [ ] `aur soar` command works with new spawner (manual test)
