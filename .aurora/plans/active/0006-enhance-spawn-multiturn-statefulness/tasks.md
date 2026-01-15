# Tasks: Enhance aur spawn Multi-Turn and Statefulness

**Option A: Minimal Statefulness** (Recommended)
**Total**: 12 tasks across 3 phases

---

## Phase 1: Context Management (5 tasks)

**Goal**: Add structured context accumulation to spawn

- [ ] 1. Create `packages/spawner/src/aurora_spawner/context.py`
  <!-- agent: @full-stack-dev -->
  - Add `Turn` dataclass to models.py
  - Implement `ContextAccumulator` class
  - Methods: `add_turn()`, `get_prompt()`, `to_dict()`, `from_dict()`
  - **Validation**: `pytest tests/unit/spawner/test_context.py`

- [ ] 2. Implement token estimation and trimming
  <!-- agent: @full-stack-dev -->
  - `_estimate_tokens()`: 4 chars = 1 token heuristic
  - `_trim()`: Sliding window (first 2 + last 10 turns)
  - Trigger trim at 80% of max_tokens
  - **Validation**: Unit tests verify window behavior

- [ ] 3. Update `spawn_sequential()` to use ContextAccumulator
  <!-- agent: @full-stack-dev -->
  - Add optional `context: ContextAccumulator` parameter
  - Build structured prompts with conversation history
  - Return context alongside results
  - **Validation**: Integration test with mock agent

- [ ] 4. Add context stats and warnings
  <!-- agent: @full-stack-dev -->
  - Track token usage per turn
  - Emit warning at 80%, 90% capacity
  - Display in verbose output
  - **Validation**: Integration test triggers warnings

- [ ] 5. Write unit tests for ContextAccumulator
  <!-- agent: @qa-test-architect -->
  - Test add_turn, get_prompt
  - Test trimming at threshold
  - Test serialization round-trip
  - **Validation**: 95%+ coverage

---

## Phase 2: Session Persistence (4 tasks)

**Goal**: Persist conversation state in checkpoints

- [ ] 6. Extend CheckpointState with conversation
  <!-- agent: @full-stack-dev -->
  - Add `conversation: list[dict]` field
  - Update `_to_dict()` and `_from_dict()`
  - Backward compatible with empty conversation
  - **Validation**: Existing checkpoint tests pass

- [ ] 7. Modify CheckpointManager.save() for conversation
  <!-- agent: @full-stack-dev -->
  - Accept optional conversation parameter
  - Serialize ContextAccumulator.to_dict()
  - **Validation**: Integration test saves/loads conversation

- [ ] 8. Implement session resume from checkpoint
  <!-- agent: @full-stack-dev -->
  - Load checkpoint with conversation
  - Reconstruct ContextAccumulator from data
  - Continue execution with restored context
  - **Validation**: Resume test with context

- [ ] 9. Write integration tests for session persistence
  <!-- agent: @qa-test-architect -->
  - Test save checkpoint with conversation
  - Test load and restore context
  - Test resume mid-execution
  - **Validation**: All persistence tests pass

---

## Phase 3: CLI Integration (3 tasks)

**Goal**: Wire up multi-turn in CLI

- [ ] 10. Update spawn.py with context support
  <!-- agent: @full-stack-dev -->
  - Pass ContextAccumulator to _execute_sequential()
  - Save conversation to checkpoint after each task
  - Display context stats in verbose mode
  - **Validation**: `aur spawn --sequential -v` shows context info

- [ ] 11. Implement --resume with conversation restore
  <!-- agent: @full-stack-dev -->
  - Load checkpoint including conversation
  - Restore context before continuing
  - Show resume info: "Resuming with N turns of context"
  - **Validation**: `aur spawn --resume <id>` works

- [ ] 12. Add --no-context flag for opt-out
  <!-- agent: @full-stack-dev -->
  - Allow users to disable context accumulation
  - Backward compatible default (context enabled)
  - **Validation**: Flag works as expected

---

## Validation Commands

After each task:

```bash
# Type check
mypy packages/spawner packages/cli --strict

# Unit tests
pytest tests/unit/spawner/ -v

# Integration tests
pytest tests/integration/spawner/ -v

# Full test suite
make test-unit

# Lint
ruff check packages/spawner packages/cli
```

---

## Definition of Done

- [ ] Code written with type hints
- [ ] Unit tests pass (95%+ coverage)
- [ ] Integration tests pass
- [ ] mypy --strict passes
- [ ] ruff passes
- [ ] Backward compatible with existing spawn usage

---

## Optional Extension Tasks (Phase 4: Interactive REPL)

If interactive mode is needed after Phase 1-3:

- [ ] E1. Create InteractiveREPL class
  <!-- agent: @full-stack-dev -->
  - Prompt loop with agent
  - Command parsing (/help, /exit, /clear, /save)
  - Context accumulated per turn

- [ ] E2. Add --interactive CLI flag
  <!-- agent: @full-stack-dev -->
  - Launch REPL instead of task execution
  - Auto-save session on exit

- [ ] E3. Implement session commands
  <!-- agent: @full-stack-dev -->
  - /history: Show turns
  - /stats: Show token usage
  - /save: Export to markdown

---

## Dependency Graph

```
Phase 1 (Context)
  1 → 2 → 3 → 4 → 5
            │
            ▼
Phase 2 (Persistence)
  6 → 7 → 8 → 9
            │
            ▼
Phase 3 (CLI)
  10 → 11 → 12
```
