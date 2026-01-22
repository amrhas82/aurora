# Tasks: Phase 2 Code Quality Improvements

**Generated:** 2026-01-22
**Source PRD:** `/home/hamr/PycharmProjects/aurora/tasks/prd-phase2-code-quality.md`
**Target:** Fix 47 type errors + refactor 10 complex functions + remove 264 unused args + delete 79 commented blocks

---

## Relevant Files

### Phase 2A: Type Errors & Complexity Reduction

**packages/context-code (10 type errors):**
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/languages/typescript.py` - None check before .parse() call
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/embedding_provider.py` - None check before function call
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` - dict type parameters (lines 493, 610)
- `/home/hamr/PycharmProjects/aurora/packages/context-code/src/aurora_context_code/__init__.py` - Missing type annotations (line 20)
- `/home/hamr/PycharmProjects/aurora/tests/unit/context_code/test_typescript_parser.py` - Tests for None handling
- `/home/hamr/PycharmProjects/aurora/tests/unit/context_code/test_embedding_provider.py` - Tests for None handling

**packages/soar (13 type errors):**
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/assess.py` - Complexity scoring types (lines 415, 429, 55, 57, 871)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/retrieve.py` - Store compatibility (line 126)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/phases/collect.py` - dict types + annotations (lines 35, 46, 94)
- `/home/hamr/PycharmProjects/aurora/packages/soar/src/aurora_soar/orchestrator.py` - Helper annotations (lines 209, 220, 234, 1618)
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/test_assess_types.py` - Tests for type consistency
- `/home/hamr/PycharmProjects/aurora/tests/unit/soar/test_retrieve_types.py` - Tests for Store compatibility

**packages/core (remaining type errors):**
- `/home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/store/sqlite.py` - Store base class compatibility
- `/home/hamr/PycharmProjects/aurora/packages/core/src/aurora_core/models.py` - Model type annotations
- `/home/hamr/PycharmProjects/aurora/tests/unit/core/test_store_types.py` - Tests for Store compatibility

**Complex Functions (C90 > 15):**
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/headless.py` - headless_command (C90=53 → ≤15)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/goals.py` - goals_command (C90=26 → ≤15)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/doctor.py` - _handle_auto_fix (C90=12 → ≤10)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/agents.py` - list_command (C90=12 → ≤10)
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/agent_discovery/parser.py` - parse_file (C90=11 → ≤10)
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/commands/test_headless_refactored.py` - Tests for extracted functions
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/commands/test_goals_refactored.py` - Tests for extracted functions
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/commands/test_doctor_refactored.py` - Tests for extracted functions
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/commands/test_agents_refactored.py` - Tests for extracted functions
- `/home/hamr/PycharmProjects/aurora/tests/unit/cli/agent_discovery/test_parser_refactored.py` - Tests for extracted functions

### Phase 2B: Cleanup

**Unused Arguments (264 issues):**
- Multiple files across `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/` - ARG001 (function args)
- Multiple files across all packages - ARG002 (method args)
- Multiple files across all packages - ARG005 (lambda args)

**Commented Code (79 issues):**
- Multiple files identified by `ruff check packages/ tests/ --select ERA001`
- `/home/hamr/PycharmProjects/aurora/packages/cli/src/aurora_cli/commands/doctor.py` - Lines 114-117 (MCP checks - create issue if needed)

### Configuration & Testing
- `/home/hamr/PycharmProjects/aurora/Makefile` - Build, test, and benchmark commands
- `/home/hamr/PycharmProjects/aurora/pytest.ini` - Test configuration
- `/home/hamr/PycharmProjects/aurora/pyproject.toml` - Root project configuration
- `/home/hamr/PycharmProjects/aurora/.github/workflows/` - CI configuration (if mypy strict mode added)
- `/home/hamr/PycharmProjects/aurora/docs/CODE_QUALITY_REPORT.md` - Results documentation

---

## Notes

### Testing Framework
- **Unit tests:** Use `@pytest.mark.unit` marker
- **Integration tests:** Use `@pytest.mark.integration` marker
- **Run tests:** `make test` or `pytest tests/unit/` for unit only
- **Coverage:** `make coverage` generates HTML report
- **Test fixtures:** Available in `tests/fixtures/`

### Type Checking
- **Tool:** mypy with `--strict` mode for packages/context-code, packages/soar, packages/core
- **Run:** `make type-check` or `mypy packages/{package}/src --strict`
- **No type: ignore:** All type errors must be properly fixed, not suppressed

### Performance Benchmarks
- **Baseline:** Capture before Phase 2A: `make benchmark-startup > phase2a_baseline_perf.txt`
- **Regression guard:** MAX_TOTAL_STARTUP_TIME ≤ 3.0s, MAX_IMPORT_TIME ≤ 2.0s
- **Run benchmarks:** `make benchmark-startup` or `make benchmark-soar`
- **Full suite:** `make benchmark` (~5 min)

### Complexity Analysis
- **Tool:** ruff with C90 (cyclomatic complexity) rule
- **Identify complex functions:** `ruff check packages/ --select C90 | grep "C901" | sort -k3 -n -r | head -10`
- **Target:** All functions ≤ 15 complexity, CLI entry points ideally ≤ 10
- **Refactoring pattern:** Extract validation → extract parsing → extract execution

### Code Quality Commands
- **Lint:** `make lint` (ruff check)
- **Format:** `make format` (ruff check --fix + ruff format)
- **Quality check:** `make quality-check` (lint + type + test)

### Architectural Patterns
- **Extracted functions:** Use `_validate_*`, `_parse_*`, `_execute_*` naming
- **None handling:** Always check before method calls: `if parser is not None: parser.parse()`
- **Type parameters:** Use explicit types: `dict[str, Any]`, not bare `dict`
- **Interface args:** Prefix unused but required args with `_`: `def callback(_ctx, value)`

### Git Workflow
- **Branch naming:** `feature/phase2a-type-errors-complexity` and `feature/phase2b-cleanup`
- **Commit style:** `fix:`, `refactor:`, `test:`, `docs:` prefixes
- **No co-author:** Use default git settings, do not add Claude as co-author
- **Incremental merges:** Phase 2A merges before Phase 2B starts

### Risk Mitigation
- **Type fixes:** Add tests BEFORE fixing to ensure behavior unchanged
- **Complexity refactoring:** Extract pure functions first, maintain orchestrator pattern
- **Unused args:** Check for ABC/Protocol implementations before removal
- **Performance:** Profile with cProfile if benchmark regression > 5%, revert if needed

---

## Tasks

- [x] 0.0 Create feature branch for Phase 2A
  - [x] 0.1 Create and checkout branch `feature/phase2a-type-errors-complexity`
    - tdd: no
    - verify: `git branch --show-current`
  - [x] 0.2 Capture baseline performance benchmarks
    - tdd: no
    - verify: `cat phase2a_baseline_perf.txt | grep "MAX_TOTAL_STARTUP_TIME"`
  - [x] 0.3 Capture baseline test results
    - tdd: no
    - verify: `cat phase2a_baseline_tests.txt | grep "passed"`

- [x] 1.0 Fix type errors in packages/context-code (10 errors)
  - [x] 1.1 Add test for typescript.py None handling before fixing
    - tdd: yes
    - verify: `pytest tests/unit/context_code/test_typescript_parser.py::test_parse_handles_none_parser -v`
  - [x] 1.2 Fix typescript.py:94 - Add None check before .parse() call
    - tdd: yes
    - verify: `mypy packages/context-code/src/aurora_context_code/languages/typescript.py --strict`
  - [x] 1.3 Add test for embedding_provider.py None handling before fixing
    - tdd: yes
    - verify: `pytest tests/unit/context_code/test_embedding_provider.py::test_handles_none_provider -v`
  - [x] 1.4 Fix embedding_provider.py:252 - Add None check before function call
    - tdd: yes
    - verify: `mypy packages/context-code/src/aurora_context_code/semantic/embedding_provider.py --strict`
  - [x] 1.5 Fix hybrid_retriever.py:493,610 - Add type parameters to dict (dict[str, Any])
    - tdd: no
    - verify: `mypy packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py --strict`
  - [x] 1.6 Fix __init__.py:20 - Add missing type annotations
    - tdd: no
    - verify: `mypy packages/context-code/src/aurora_context_code/__init__.py --strict`
  - [x] 1.7 Run all context-code tests to ensure no regressions
    - tdd: no
    - verify: `pytest tests/unit/context_code/ -v`
  - [x] 1.8 Verify: `mypy packages/context-code/src --strict` - zero errors

- [ ] 2.0 Fix type errors in packages/soar (13 errors)
  - [ ] 2.1 Add test for assess.py type consistency before fixing
    - tdd: yes
    - verify: `pytest tests/unit/soar/test_assess_types.py::test_complexity_score_type -v`
  - [ ] 2.2 Fix assess.py:415 - Cast float to int or change target type for complexity scoring
    - tdd: yes
    - verify: `mypy packages/soar/src/aurora_soar/phases/assess.py --strict | grep -c "line 415" || echo "0"`
  - [ ] 2.3 Fix assess.py:429 - Validate string value or use proper Literal type for assessment levels
    - tdd: yes
    - verify: `mypy packages/soar/src/aurora_soar/phases/assess.py --strict | grep -c "line 429" || echo "0"`
  - [ ] 2.4 Fix assess.py:55,57,871 - Add type parameters: dict[str, Any]
    - tdd: no
    - verify: `mypy packages/soar/src/aurora_soar/phases/assess.py --strict`
  - [ ] 2.5 Add test for retrieve.py Store compatibility before fixing
    - tdd: yes
    - verify: `pytest tests/unit/soar/test_retrieve_types.py::test_store_compatibility -v`
  - [ ] 2.6 Fix retrieve.py:126 - Accept base Store type or cast properly for type compatibility
    - tdd: yes
    - verify: `mypy packages/soar/src/aurora_soar/phases/retrieve.py --strict`
  - [ ] 2.7 Fix collect.py:35,46 - Add type parameters: dict[str, Any]
    - tdd: no
    - verify: `mypy packages/soar/src/aurora_soar/phases/collect.py --strict | grep -c "line 35\|line 46" || echo "0"`
  - [ ] 2.8 Fix collect.py:94 - Add type annotations to _get_agent_matcher
    - tdd: no
    - verify: `mypy packages/soar/src/aurora_soar/phases/collect.py --strict`
  - [ ] 2.9 Fix orchestrator.py:209,220,234,1618 - Add type annotations to helper methods
    - tdd: no
    - verify: `mypy packages/soar/src/aurora_soar/orchestrator.py --strict`
  - [ ] 2.10 Run all soar tests to ensure no regressions
    - tdd: no
    - verify: `pytest tests/unit/soar/ tests/integration/soar/ -v`
  - [ ] 2.11 Verify: `mypy packages/soar/src --strict` - zero errors

- [ ] 3.0 Fix type errors in packages/core (remaining errors)
  - [ ] 3.1 Add test for Store base class compatibility before fixing
    - tdd: yes
    - verify: `pytest tests/unit/core/test_store_types.py::test_base_store_compatibility -v`
  - [ ] 3.2 Fix Store base class compatibility issues in sqlite.py
    - tdd: yes
    - verify: `mypy packages/core/src/aurora_core/store/sqlite.py --strict`
  - [ ] 3.3 Fix remaining type errors in core models
    - tdd: no
    - verify: `mypy packages/core/src/aurora_core/models.py --strict`
  - [ ] 3.4 Run all core tests to ensure no regressions
    - tdd: no
    - verify: `pytest tests/unit/core/ tests/integration/core/ -v`
  - [ ] 3.5 Verify: `mypy packages/core/src --strict` - zero errors

- [ ] 4.0 Verify Phase 2A type error fixes complete
  - [ ] 4.1 Run full type check across all packages
    - tdd: no
    - verify: `make type-check`
  - [ ] 4.2 Verify all new None-handling tests pass
    - tdd: no
    - verify: `pytest tests/unit/ -k "none" -v`
  - [ ] 4.3 Verify: `make type-check` - zero errors in context-code, soar, core

- [ ] 5.0 Identify top 10 complex functions (C90 > 15)
  - [ ] 5.1 Generate complexity report for all packages
    - tdd: no
    - verify: `ruff check packages/ --select C90 | grep "C901" | wc -l`
  - [ ] 5.2 Extract and document top 10 functions by complexity
    - tdd: no
    - verify: `ruff check packages/ --select C90 | grep "C901" | sort -k3 -n -r | head -10 > complex_functions.txt && cat complex_functions.txt`
  - [ ] 5.3 Verify headless_command is in top 10 (expected C90=53)
    - tdd: no
    - verify: `grep "headless_command" complex_functions.txt`

- [ ] 6.0 Refactor headless_command (C90=53 → ≤15)
  - [ ] 6.1 Add integration test for headless_command current behavior
    - tdd: yes
    - verify: `pytest tests/integration/cli/test_headless_integration.py -v`
  - [ ] 6.2 Extract argument parsing logic into _parse_headless_args function
    - tdd: yes
    - verify: `pytest tests/unit/cli/commands/test_headless_refactored.py::test_parse_headless_args -v`
  - [ ] 6.3 Extract validation logic into _validate_headless_config function
    - tdd: yes
    - verify: `pytest tests/unit/cli/commands/test_headless_refactored.py::test_validate_headless_config -v`
  - [ ] 6.4 Extract execution loop into _execute_headless_loop function
    - tdd: yes
    - verify: `pytest tests/unit/cli/commands/test_headless_refactored.py::test_execute_headless_loop -v`
  - [ ] 6.5 Refactor headless_command to use extracted functions (thin orchestrator)
    - tdd: yes
    - verify: `ruff check packages/cli/src/aurora_cli/commands/headless.py --select C90 | grep "headless_command"`
  - [ ] 6.6 Update docstrings for headless_command and extracted functions
    - tdd: no
    - verify: `grep -A 5 "def headless_command" packages/cli/src/aurora_cli/commands/headless.py`
  - [ ] 6.7 Verify: headless_command C90 ≤ 15 and all tests pass

- [ ] 7.0 Refactor goals_command (C90=26 → ≤15)
  - [ ] 7.1 Add integration test for goals_command current behavior
    - tdd: yes
    - verify: `pytest tests/integration/cli/test_goals_integration.py -v`
  - [ ] 7.2 Extract planning logic into _generate_goals_plan function
    - tdd: yes
    - verify: `pytest tests/unit/cli/commands/test_goals_refactored.py::test_generate_goals_plan -v`
  - [ ] 7.3 Extract SOAR pipeline invocation into _invoke_soar_pipeline function
    - tdd: yes
    - verify: `pytest tests/unit/cli/commands/test_goals_refactored.py::test_invoke_soar_pipeline -v`
  - [ ] 7.4 Simplify error handling paths using extracted functions
    - tdd: yes
    - verify: `pytest tests/unit/cli/commands/test_goals_refactored.py::test_error_handling -v`
  - [ ] 7.5 Refactor goals_command to use extracted functions (thin orchestrator)
    - tdd: yes
    - verify: `ruff check packages/cli/src/aurora_cli/commands/goals.py --select C90 | grep "goals_command"`
  - [ ] 7.6 Update docstrings for goals_command and extracted functions
    - tdd: no
    - verify: `grep -A 5 "def goals_command" packages/cli/src/aurora_cli/commands/goals.py`
  - [ ] 7.7 Verify: goals_command C90 ≤ 15 and all tests pass

- [ ] 8.0 Refactor remaining top 8 complex functions (functions 3-10)
  - [ ] 8.1 Refactor _handle_auto_fix in doctor.py (C90=12 → ≤10)
    - tdd: yes
    - verify: `ruff check packages/cli/src/aurora_cli/commands/doctor.py --select C90 | grep "_handle_auto_fix"`
  - [ ] 8.2 Refactor list_command in agents.py (C90=12 → ≤10)
    - tdd: yes
    - verify: `ruff check packages/cli/src/aurora_cli/commands/agents.py --select C90 | grep "list_command"`
  - [ ] 8.3 Refactor parse_file in agent_discovery/parser.py (C90=11 → ≤10)
    - tdd: yes
    - verify: `ruff check packages/cli/src/aurora_cli/agent_discovery/parser.py --select C90 | grep "parse_file"`
  - [ ] 8.4 Identify and refactor functions 6-10 from complex_functions.txt
    - tdd: yes
    - verify: `ruff check packages/ --select C90 | grep "C901" | awk -F: '$3 > 15' | wc -l`
  - [ ] 8.5 Add unit tests for all newly extracted functions (100% coverage)
    - tdd: yes
    - verify: `pytest tests/unit/cli/ --cov=packages/cli/src/aurora_cli/commands --cov-report=term-missing | grep "100%"`
  - [ ] 8.6 Verify: All targeted functions C90 ≤ 15

- [ ] 9.0 Verify Phase 2A complexity reduction complete
  - [ ] 9.1 Run complexity check on all packages
    - tdd: no
    - verify: `ruff check packages/ --select C90 | grep "C901" | sort -k3 -n -r | head -10`
  - [ ] 9.2 Confirm zero functions with C90 > 15 in targeted list
    - tdd: no
    - verify: `ruff check packages/ --select C90 | grep "C901" | awk -F: '$3 > 15' | wc -l`
  - [ ] 9.3 Run full test suite to ensure no regressions
    - tdd: no
    - verify: `make test`
  - [ ] 9.4 Run performance benchmarks and compare to baseline
    - tdd: no
    - verify: `make benchmark-startup > phase2a_final_perf.txt && diff phase2a_baseline_perf.txt phase2a_final_perf.txt`
  - [ ] 9.5 Verify: All tests pass, performance maintained or improved

- [ ] 10.0 Phase 2A final validation and merge
  - [ ] 10.1 Run full quality check
    - tdd: no
    - verify: `make quality-check`
  - [ ] 10.2 Verify all docstrings updated for refactored functions
    - tdd: no
    - verify: `grep -r "def _validate_\|def _parse_\|def _execute_" packages/cli/src/aurora_cli/commands/ | wc -l`
  - [ ] 10.3 Create Phase 2A PR with detailed description and benchmark results
    - tdd: no
    - verify: `git log --oneline feature/phase2a-type-errors-complexity | head -5`
  - [ ] 10.4 Update CODE_QUALITY_REPORT.md with Phase 2A results
    - tdd: no
    - verify: `grep "Phase 2A" /home/hamr/PycharmProjects/aurora/docs/CODE_QUALITY_REPORT.md`
  - [ ] 10.5 Verify: Phase 2A PR merged to main

- [ ] 11.0 Create feature branch for Phase 2B
  - [ ] 11.1 Create and checkout branch `feature/phase2b-cleanup` from main
    - tdd: no
    - verify: `git branch --show-current`
  - [ ] 11.2 Capture baseline performance benchmarks for Phase 2B
    - tdd: no
    - verify: `make benchmark-startup > phase2b_baseline_perf.txt && cat phase2b_baseline_perf.txt | grep "MAX_TOTAL_STARTUP_TIME"`
  - [ ] 11.3 Capture baseline test results for Phase 2B
    - tdd: no
    - verify: `make test > phase2b_baseline_tests.txt && cat phase2b_baseline_tests.txt | grep "passed"`

- [ ] 12.0 Remove commented code (79 issues)
  - [ ] 12.1 Generate full report of commented code blocks
    - tdd: no
    - verify: `ruff check packages/ tests/ --select ERA001 > commented_code_report.txt && wc -l commented_code_report.txt`
  - [ ] 12.2 Review doctor.py:114-117 MCP checks for valuable context
    - tdd: no
    - verify: `grep -A 5 "line 114" commented_code_report.txt`
  - [ ] 12.3 Create GitHub issue for MCP feature if context is valuable
    - tdd: no
    - verify: `gh issue list --search "MCP checks" | wc -l`
  - [ ] 12.4 Delete all commented code blocks in packages/cli
    - tdd: no
    - verify: `ruff check packages/cli/ --select ERA001 | wc -l`
  - [ ] 12.5 Delete all commented code blocks in packages/soar
    - tdd: no
    - verify: `ruff check packages/soar/ --select ERA001 | wc -l`
  - [ ] 12.6 Delete all commented code blocks in packages/context-code
    - tdd: no
    - verify: `ruff check packages/context-code/ --select ERA001 | wc -l`
  - [ ] 12.7 Delete all commented code blocks in remaining packages
    - tdd: no
    - verify: `ruff check packages/ --select ERA001 | wc -l`
  - [ ] 12.8 Delete all commented code blocks in tests/
    - tdd: no
    - verify: `ruff check tests/ --select ERA001 | wc -l`
  - [ ] 12.9 Run full test suite to ensure no functionality lost
    - tdd: no
    - verify: `make test`
  - [ ] 12.10 Verify: `ruff check packages/ tests/ --select ERA001` - zero violations

- [ ] 13.0 Fix unused arguments (264 issues)
  - [ ] 13.1 Generate full report categorized by ARG type
    - tdd: no
    - verify: `ruff check packages/ tests/ --select ARG > unused_args_report.txt && cat unused_args_report.txt | wc -l`
  - [ ] 13.2 Fix ARG001 issues (100 function arguments) - Phase 1
    - tdd: no
    - verify: `ruff check packages/ tests/ --select ARG001 | wc -l`
  - [ ] 13.3 Fix ARG002 issues (104 method arguments) - Review ABC implementations carefully
    - tdd: no
    - verify: `ruff check packages/ tests/ --select ARG002 | wc -l`
  - [ ] 13.4 Fix ARG005 issues (59 lambda arguments) - Use _ for unused lambda args
    - tdd: no
    - verify: `ruff check packages/ tests/ --select ARG005 | wc -l`
  - [ ] 13.5 Fix ARG004 issues (1 static method argument)
    - tdd: no
    - verify: `ruff check packages/ tests/ --select ARG004 | wc -l`
  - [ ] 13.6 Update docstrings for all functions with changed signatures
    - tdd: no
    - verify: `git diff feature/phase2b-cleanup main -- "*.py" | grep "def " | wc -l`
  - [ ] 13.7 Run full test suite to ensure no regressions
    - tdd: no
    - verify: `make test`
  - [ ] 13.8 Verify: `ruff check packages/ tests/ --select ARG` - zero violations or documented

- [ ] 14.0 Verify Phase 2B cleanup complete
  - [ ] 14.1 Run full ruff check on all rules
    - tdd: no
    - verify: `make lint`
  - [ ] 14.2 Verify commented code removal complete (ERA001)
    - tdd: no
    - verify: `ruff check packages/ tests/ --select ERA001`
  - [ ] 14.3 Verify unused arguments resolved (ARG)
    - tdd: no
    - verify: `ruff check packages/ tests/ --select ARG`
  - [ ] 14.4 Run performance benchmarks and compare to baseline
    - tdd: no
    - verify: `make benchmark-startup > phase2b_final_perf.txt && diff phase2b_baseline_perf.txt phase2b_final_perf.txt`
  - [ ] 14.5 Verify: All quality gates pass, no regressions

- [ ] 15.0 Phase 2B final validation and merge
  - [ ] 15.1 Run full quality check
    - tdd: no
    - verify: `make quality-check`
  - [ ] 15.2 Review all removed arguments in commit messages for documentation
    - tdd: no
    - verify: `git log --oneline feature/phase2b-cleanup | grep "fix: remove unused" | wc -l`
  - [ ] 15.3 Create Phase 2B PR with detailed description
    - tdd: no
    - verify: `git log --oneline feature/phase2b-cleanup | head -5`
  - [ ] 15.4 Update CODE_QUALITY_REPORT.md with Phase 2B results
    - tdd: no
    - verify: `grep "Phase 2B" /home/hamr/PycharmProjects/aurora/docs/CODE_QUALITY_REPORT.md`
  - [ ] 15.5 Verify: Phase 2B PR merged to main

- [ ] 16.0 Phase 2 Overall Final Validation
  - [ ] 16.1 Run full benchmark suite on main after both merges
    - tdd: no
    - verify: `make benchmark`
  - [ ] 16.2 Compare Phase 2 final performance vs Phase 0/1 baseline
    - tdd: no
    - verify: `cat phase2_final_benchmark.txt | grep "improvement"`
  - [ ] 16.3 Verify total issues resolved: 47 type + 10 complex + 264 unused + 79 commented = 400
    - tdd: no
    - verify: `grep "400 critical issues resolved" /home/hamr/PycharmProjects/aurora/docs/CODE_QUALITY_REPORT.md`
  - [ ] 16.4 Document lessons learned and patterns for Phase 3
    - tdd: no
    - verify: `grep "Lessons Learned" /home/hamr/PycharmProjects/aurora/docs/CODE_QUALITY_REPORT.md`
  - [ ] 16.5 Verify: All Phase 2 success criteria met, ready for Phase 3 planning
