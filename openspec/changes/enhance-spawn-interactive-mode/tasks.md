# Tasks: Interactive Multi-Turn Mode for aur spawn

## Overview
Implementation tasks for adding interactive REPL mode to `aur spawn`, enabling multi-turn conversations with agents that maintain context across turns.

## Task Breakdown

### Phase 1: Foundation (Est: 4-6 hours)

- [ ] 1. Create conversation context module
  - Create `packages/cli/src/aurora_cli/interactive/context.py`
  - Implement `Turn` dataclass with role, content, timestamp, tokens
  - Implement `ConversationContext` class with history tracking
  - Add `add_turn()`, `to_prompt_context()`, `to_markdown()` methods
  - Add context trimming logic (keep first 2 + last 18 turns)
  - Add token estimation (4 chars ≈ 1 token)
  - **Validation**: Can add turns, trim correctly, serialize/deserialize
  - **Test coverage**: Unit tests in `tests/unit/cli/interactive/test_context.py`

- [ ] 2. Create command parser
  - Create `packages/cli/src/aurora_cli/interactive/commands.py`
  - Implement `Command` dataclass with name and args
  - Implement `CommandParser` class with parse() method
  - Define command registry with arg counts and descriptions
  - Add validation logic for command arguments
  - **Validation**: Parses all slash commands correctly
  - **Test coverage**: Unit tests in `tests/unit/cli/interactive/test_commands.py`

- [ ] 3. Create session manager
  - Create `packages/cli/src/aurora_cli/interactive/session.py`
  - Implement `SessionManager` class
  - Add `save_session()` method (saves to ~/.aurora/spawn/sessions/)
  - Add `load_session()` method (deserialize from JSON)
  - Add `list_sessions()` method
  - Add `cleanup_old_sessions()` method
  - **Validation**: Sessions saved/loaded correctly
  - **Test coverage**: Unit tests in `tests/unit/cli/interactive/test_session.py`
  - **Dependencies**: Requires task 1 (ConversationContext)

### Phase 2: REPL Implementation (Est: 6-8 hours)

- [ ] 4. Create basic REPL structure
  - Create `packages/cli/src/aurora_cli/interactive/repl.py`
  - Implement `InteractiveREPL` class with `__init__`
  - Add `display_welcome()` method with banner
  - Add `run_loop()` with basic prompt/response cycle
  - Add `_prompt_user()` using prompt_toolkit
  - **Validation**: REPL launches, shows prompt, accepts input
  - **Test coverage**: Unit tests for REPL structure
  - **Dependencies**: Requires tasks 1, 2, 3

- [ ] 5. Implement query handling
  - Add `_handle_query()` method to InteractiveREPL
  - Build `SpawnTask` with current query
  - Pass conversation history as context to spawn
  - Display "Agent thinking..." spinner during spawn
  - Add turn to context after response
  - Handle spawn errors gracefully
  - **Validation**: Queries spawn correctly, context accumulates
  - **Test coverage**: Integration tests with mocked spawn
  - **Dependencies**: Requires task 4

- [ ] 6. Implement command handling
  - Add `_handle_command()` method to InteractiveREPL
  - Implement /help command (show command list)
  - Implement /exit command (save and quit)
  - Implement /save command (export to Markdown)
  - Implement /history command (display turns)
  - Implement /clear command (reset context)
  - Implement /agent command (switch agent)
  - Implement /stats command (show session info)
  - **Validation**: All commands work as specified
  - **Test coverage**: Unit tests for each command
  - **Dependencies**: Requires task 5

- [ ] 7. Add rich output formatting
  - Integrate rich Console for Markdown rendering
  - Add syntax highlighting for code blocks
  - Add progress spinner for agent thinking
  - Format /history output with colors
  - Format /stats output in table
  - **Validation**: Output is visually formatted correctly
  - **Test coverage**: Visual tests with snapshots
  - **Dependencies**: Requires task 6

### Phase 3: CLI Integration (Est: 2-3 hours)

- [ ] 8. Add --interactive flag to spawn command
  - Update `packages/cli/src/aurora_cli/commands/spawn.py`
  - Add `--interactive` / `-i` flag
  - Add `--agent` flag (optional, for specifying agent)
  - Update command docstring with interactive mode docs
  - **Validation**: Flags recognized and parsed
  - **Test coverage**: Unit tests for flag parsing

- [ ] 9. Wire REPL into spawn command
  - Add conditional branch: if interactive → InteractiveREPL
  - Import InteractiveREPL in spawn command
  - Pass agent_id from --agent flag to REPL
  - Ensure task-based mode still works when --interactive not set
  - **Validation**: Both modes work independently
  - **Test coverage**: Integration tests for both modes
  - **Dependencies**: Requires task 8

- [ ] 10. Add error handling and interrupts
  - Handle KeyboardInterrupt (Ctrl+C) gracefully
  - Handle EOFError (Ctrl+D) as exit
  - Add try/except around spawn calls
  - Display user-friendly error messages
  - Ensure session saves on any exit path
  - **Validation**: Errors handled gracefully, no crashes
  - **Test coverage**: Error scenario tests
  - **Dependencies**: Requires task 9

### Phase 4: Context Management (Est: 2-3 hours)

- [ ] 11. Implement context window trimming
  - Add max_turns config (default: 20)
  - Add max_tokens config (default: 100000)
  - Implement sliding window trimming strategy
  - Add warning when approaching token limit
  - **Validation**: Context trims correctly, warnings shown
  - **Test coverage**: Unit tests for trimming logic

- [ ] 12. Add token tracking and statistics
  - Track token count per turn (estimation)
  - Calculate cumulative tokens in conversation
  - Add `/stats` command output with token info
  - Display tokens in conversation exports
  - **Validation**: Token counts are accurate (+/- 10%)
  - **Test coverage**: Token estimation tests
  - **Dependencies**: Requires task 11

- [ ] 13. Implement session auto-save
  - Save session every N turns (configurable)
  - Save session on /exit command
  - Save session on Ctrl+C/Ctrl+D
  - Create sessions directory if not exists
  - Display save confirmation to user
  - **Validation**: Sessions saved at correct times
  - **Test coverage**: Integration tests for auto-save
  - **Dependencies**: Requires task 12

### Phase 5: Testing & Documentation (Est: 4-5 hours)

- [ ] 14. Write comprehensive unit tests
  - Test ConversationContext (add, trim, serialize)
  - Test CommandParser (parse, validate)
  - Test SessionManager (save, load, list, cleanup)
  - Test InteractiveREPL (loop, commands, query handling)
  - Mock spawn calls for deterministic tests
  - **Validation**: 90%+ coverage for new modules
  - **Test coverage**: ~30 unit tests across all modules

- [ ] 15. Write integration tests
  - Test full interactive session (multiple turns)
  - Test context accumulation across turns
  - Test session save and restore
  - Test error handling scenarios
  - Test command execution in sequence
  - **Validation**: All integration tests pass
  - **Test coverage**: ~10 integration tests

- [ ] 16. Write E2E tests
  - Test real interactive session with agent
  - Test all slash commands end-to-end
  - Test graceful exit scenarios
  - Test context window trimming in practice
  - **Validation**: Real-world usage works
  - **Test coverage**: 3-5 E2E tests

- [ ] 17. Update documentation
  - Update `docs/commands/aur-spawn.md` with interactive mode section
  - Add examples of interactive usage
  - Document all slash commands
  - Add troubleshooting section
  - Create tutorial for first-time users
  - **Validation**: Documentation is clear and complete

- [ ] 18. Create interactive mode examples
  - Create `examples/spawn/interactive-example.md` with sample session
  - Create example showing context accumulation
  - Create example showing agent switching
  - Add README explaining interactive features
  - **Validation**: Examples run successfully

- [ ] 19. Update CHANGELOG
  - Add entry for "Interactive Multi-Turn Mode" feature
  - Document new --interactive and --agent flags
  - Note: feature is opt-in, existing behavior unchanged
  - Include usage examples in changelog
  - **Validation**: CHANGELOG follows project conventions

### Phase 6: Polish & Review (Est: 2-3 hours)

- [ ] 20. Run full test suite
  - Execute `make test` and verify all tests pass
  - Fix any regressions or test failures
  - Ensure no breaking changes to task-based spawning
  - **Validation**: 0 test failures, no coverage regression

- [ ] 21. Run type checking
  - Execute `make type-check` (mypy)
  - Fix any type errors in new code
  - **Validation**: 0 type errors

- [ ] 22. Run linting
  - Execute `make lint` (ruff)
  - Fix any linting violations
  - **Validation**: 0 linting errors

- [ ] 23. Manual testing session
  - Test interactive mode with real agents
  - Verify all slash commands work
  - Test long conversations (20+ turns)
  - Test error scenarios manually
  - **Validation**: All manual scenarios pass

- [ ] 24. Performance validation
  - Measure prompt response time (target: <100ms)
  - Measure context trimming time (target: <10ms)
  - Measure session save time (target: <50ms)
  - Test with long conversations (50+ turns)
  - **Validation**: Performance meets targets

- [ ] 25. Update project.md
  - Add interactive mode to feature list in `openspec/project.md`
  - Document new interactive module location
  - Update command reference
  - **Validation**: project.md accurately reflects changes

## Task Parallelization

**Can run in parallel**:
- Tasks 1, 2, 3 (foundation modules are independent)
- Tasks 14, 15, 16 (different test types)
- Tasks 17, 18, 19 (different documentation)
- Tasks 21, 22 (type checking and linting)

**Must run sequentially**:
- Tasks 4-7 (REPL implementation builds on previous)
- Tasks 8-10 (CLI integration is sequential)
- Tasks 11-13 (context management depends on each other)
- Tasks 20, 23, 24, 25 (polish phase is sequential)

## Estimated Timeline

- **Phase 1**: 4-6 hours
- **Phase 2**: 6-8 hours
- **Phase 3**: 2-3 hours
- **Phase 4**: 2-3 hours
- **Phase 5**: 4-5 hours
- **Phase 6**: 2-3 hours

**Total**: 20-28 hours of development time

## Success Metrics

- [ ] All 25 tasks completed
- [ ] 90%+ test coverage for new modules
- [ ] 0 breaking changes to existing spawn behavior
- [ ] Prompt response <100ms
- [ ] Context trimming <10ms
- [ ] Session save <50ms
- [ ] Documentation complete and clear
- [ ] All tests pass (unit, integration, E2E)
- [ ] 0 type errors, 0 linting violations
- [ ] Manual testing scenarios pass

## Dependencies

**External Packages** (need to add to requirements):
- `prompt-toolkit` - Enhanced REPL input
- `rich` - Formatted output

**Existing Packages**:
- `aurora-spawner` - Agent spawning
- `click` - CLI framework
