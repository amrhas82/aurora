# Tasks: Add Multi-Turn Agent Spawning

**Total**: 35 tasks across 7 phases
**Dependencies**: Linear flow with some parallelizable tasks marked
**Estimated effort**: ~2-3 weeks

---

## Phase 1: Foundation (8 tasks)

**Goal**: Set up core data structures and session management

- [ ] 1. Create `packages/spawner/src/aurora_spawner/models.py` additions
  - Add `Turn` dataclass (role, content, timestamp, tokens)
  - Add `SessionState` dataclass (id, agent, context, metadata, status)
  - Add type aliases and enums
  - **Validation**: mypy passes, unit tests for dataclass validation

- [ ] 2. Create `packages/spawner/src/aurora_spawner/session.py`
  - Implement `SessionManager` class
  - Implement `create_session()`, `save_session()`, `load_session()`
  - Implement JSONL serialization/deserialization
  - **Validation**: Unit tests for CRUD operations

- [ ] 3. Add session storage directory setup
  - Create `~/.aurora/spawn/sessions/` on first use
  - Add directory initialization in SessionManager
  - **Validation**: Directory created on import, permissions correct

- [ ] 4. Implement `list_sessions()` with filtering
  - Filter by agent, status, date range
  - Return sorted by most recent
  - **Validation**: Unit tests with various filters

- [ ] 5. Implement `delete_session()` and `clean_old_sessions()`
  - Safe file deletion with validation
  - Age-based cleanup with configurable threshold
  - **Validation**: Integration tests for cleanup scenarios

- [ ] 6. Add session file validation
  - Validate JSONL format on load
  - Handle corrupted files gracefully
  - **Validation**: Unit tests with malformed input

- [ ] 7. Create configuration schema
  - Add `spawner.interactive` section to config
  - Define defaults (max_tokens, trim_strategy, etc.)
  - **Validation**: Config loads correctly, defaults applied

- [ ] 8. Write unit tests for SessionManager
  - Test all CRUD operations
  - Test concurrent access scenarios
  - **Validation**: 95%+ coverage, all tests pass

---

## Phase 2: Context Management (6 tasks)

**Goal**: Implement context accumulation and trimming

- [ ] 9. Create `packages/spawner/src/aurora_spawner/context.py`
  - Implement `ContextAccumulator` class
  - Implement `add_turn()` and `get_context()`
  - **Validation**: mypy passes, basic unit tests

- [ ] 10. Implement token estimation
  - Rough 4-char-per-token heuristic
  - Caching for performance
  - **Validation**: Unit tests compare to actual token counts (±20% accuracy)

- [ ] 11. Implement sliding window trimming
  - Keep first 2 + last 10 turns
  - Trigger at 80% of max_tokens
  - **Validation**: Unit tests verify window behavior

- [ ] 12. Add context window monitoring
  - Track current usage vs. limit
  - Emit warnings at thresholds (80%, 90%)
  - **Validation**: Integration tests trigger warnings

- [ ] 13. Implement `clear()` method
  - Reset context completely
  - Preserve metadata
  - **Validation**: Unit tests verify clean slate

- [ ] 14. Write unit tests for ContextAccumulator
  - Test trimming strategies
  - Test token estimation accuracy
  - **Validation**: 95%+ coverage, all tests pass

---

## Phase 3: Interactive REPL (8 tasks)

**Goal**: Build interactive interface

- [ ] 15. Create `packages/spawner/src/aurora_spawner/interactive.py`
  - Implement `InteractiveREPL` class skeleton
  - Implement `__init__()` and `run()` loop
  - **Validation**: mypy passes, REPL starts and exits

- [ ] 16. Implement user input prompt
  - Display agent name in prompt
  - Handle empty input gracefully
  - **Validation**: Manual test of prompt display

- [ ] 17. Implement `_handle_user_message()`
  - Add user turn to context
  - Build prompt from accumulated context
  - Spawn agent subprocess
  - Capture and display response
  - **Validation**: Integration test with mock agent

- [ ] 18. Implement command parser
  - Parse `/command [args]` format
  - Route to command handlers
  - **Validation**: Unit tests for parsing

- [ ] 19. Implement core commands: `/help`, `/exit`
  - `/help`: Display command reference
  - `/exit`: Clean shutdown, save session
  - **Validation**: Manual + integration tests

- [ ] 20. Implement utility commands: `/history`, `/clear`, `/stats`
  - `/history [N]`: Show last N turns
  - `/clear`: Reset context
  - `/stats`: Show token usage, turn count
  - **Validation**: Integration tests for each command

- [ ] 21. Implement `/save <file>` command
  - Export conversation to markdown
  - Include metadata header
  - Handle file I/O errors
  - **Validation**: Integration test verifies markdown output

- [ ] 22. Add error handling and interrupts
  - Keyboard interrupt (Ctrl+C): return to prompt
  - Network errors: retry with backoff
  - Invalid commands: show help
  - **Validation**: Integration tests for error scenarios

---

## Phase 4: CLI Integration (5 tasks)

**Goal**: Wire up interactive mode in CLI

- [ ] 23. Modify `packages/cli/src/aurora_cli/commands/spawn.py`
  - Add `--interactive`, `--agent`, `--session` options
  - Add conditional branch for interactive mode
  - **Validation**: `aur spawn --help` shows new options

- [ ] 24. Implement interactive mode entry point
  - Instantiate `InteractiveREPL`
  - Pass agent and session_id
  - Run REPL loop
  - **Validation**: `aur spawn -i` launches REPL

- [ ] 25. Implement `--resume <session-id>` option
  - Load session state from disk
  - Restore context and agent
  - Continue interactive REPL
  - **Validation**: Resume works after graceful exit

- [ ] 26. Add session list command helper
  - Extend `spawn_helpers.py` with `_list_sessions()`
  - Format output as table
  - **Validation**: `aur spawn --list-sessions` shows table

- [ ] 27. Ensure backward compatibility
  - Verify existing task-based spawn unchanged
  - Verify checkpoint system still works
  - **Validation**: Regression tests pass

---

## Phase 5: Testing & Quality (5 tasks)

**Goal**: Comprehensive test coverage

- [ ] 28. Write integration tests for interactive flow
  - Test full REPL lifecycle (start -> turns -> exit)
  - Test session persistence across runs
  - **Validation**: Tests pass, 90%+ coverage

- [ ] 29. Write E2E tests with real agents
  - Spawn real agent in interactive mode
  - Execute multi-turn conversation
  - Verify context preservation
  - **Validation**: E2E tests pass (may be slow)

- [ ] 30. Write tests for session resume
  - Save session mid-conversation
  - Resume and verify state restored
  - **Validation**: Tests pass

- [ ] 31. Add performance benchmarks
  - Measure REPL latency
  - Measure session save/load time
  - **Validation**: Metrics within targets (<100ms for I/O)

- [ ] 32. Add error scenario tests
  - Corrupted session files
  - Missing agents
  - Network failures
  - **Validation**: All error paths tested

---

## Phase 6: Documentation (2 tasks)

**Goal**: User-facing documentation

- [ ] 33. Update `docs/guides/COMMANDS.md`
  - Document `--interactive`, `--session`, `--resume` flags
  - Add usage examples for all modes
  - Document session commands
  - **Validation**: Docs reviewed and accurate

- [ ] 34. Create `docs/guides/INTERACTIVE_SPAWN.md`
  - Comprehensive guide to interactive mode
  - Example workflows and use cases
  - Troubleshooting section
  - **Validation**: Docs reviewed by user

---

## Phase 7: Polish & Release (1 task)

**Goal**: Final validation and release prep

- [ ] 35. Final validation and polish
  - Run full test suite (unit + integration + E2E)
  - Run `openspec validate add-multiturn-agent-spawning --strict`
  - Update CHANGELOG.md
  - Tag release candidate
  - **Validation**: All tests pass, validation clean

---

## Dependency Graph

```
Phase 1 (Foundation)
  ├─> Phase 2 (Context)
  │   └─> Phase 3 (REPL)
  │       └─> Phase 4 (CLI)
  │           └─> Phase 5 (Testing)
  │               └─> Phase 6 (Docs)
  │                   └─> Phase 7 (Release)

Parallelizable:
- Phase 1 tasks 1-6 (can work in parallel after models defined)
- Phase 2 tasks 9-13 (after ContextAccumulator skeleton)
- Phase 3 tasks 19-21 (after command parser works)
```

---

## Validation Commands

After each phase:

```bash
# Type checking
mypy packages/spawner packages/cli --strict

# Unit tests
pytest tests/unit/spawner/ -v

# Integration tests
pytest tests/integration/spawner/ -v

# Coverage check
pytest --cov=aurora_spawner --cov-report=term-missing

# Linting
ruff check packages/spawner packages/cli

# OpenSpec validation
openspec validate add-multiturn-agent-spawning --strict
```

---

## Definition of Done

Each task is complete when:
- [ ] Code written and reviewed
- [ ] Unit tests added (95%+ coverage)
- [ ] Integration/E2E tests added where applicable
- [ ] Type checking passes (mypy --strict)
- [ ] Linting passes (ruff)
- [ ] Documentation updated
- [ ] Manual testing performed
- [ ] Validated with shell command output (where applicable)

---

## Risk Mitigation

**High-risk tasks** (require extra care):
- Task 17: Core message handling (integration complexity)
- Task 22: Error handling (many edge cases)
- Task 25: Session resume (state consistency critical)
- Task 29: E2E tests (flaky test potential)

**Mitigation strategies**:
- Incremental implementation with frequent testing
- Pair review for high-risk tasks
- Comprehensive error scenario testing
- Mock agents for unit tests, real agents only for E2E
