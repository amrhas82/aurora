# Plan: Enhance aur spawn Multi-Turn and Statefulness

## Available Agents

| Agent | Capability |
|-------|------------|
| @holistic-architect | System design, architecture |
| @full-stack-dev | Code implementation |
| @qa-test-architect | Test design, quality gates |

---

## Current State

You already have substantial infrastructure:

| Component | Status | Location |
|-----------|--------|----------|
| Checkpoint system | **Working** | `execution/checkpoint.py` |
| Recovery handler | **Working** | `execution/recovery.py` |
| Context passing | **Partial** | `spawn_sequential()` passes output |
| Session storage | **Partial** | Checkpoints exist, no REPL sessions |
| Interactive REPL | **Missing** | Proposed in OpenSpec |
| Multi-turn context | **Missing** | Only sequential pass_context |

### Existing OpenSpecs

1. `add-multiturn-agent-spawning` - 35 tasks, comprehensive REPL design
2. `enhance-spawn-interactive-mode` - Similar scope, different approach
3. Aurora plan `0001-improve-aur-spawn-capabilities` - Adhoc agent gaps

---

## Problem Statement

`aur spawn` currently:
- Executes single-shot tasks with no conversation memory
- Sequential mode passes context as raw text concatenation (naive)
- No interactive REPL for exploratory work
- Checkpoints track task progress, not conversation state

**User pain**:
1. Can't ask follow-up questions without re-spawning
2. Context lost between spawn invocations
3. No session persistence for later resume
4. No interactive exploration mode

---

## Recommended Approach

**Prioritize by immediate value**: Don't implement full OpenSpec (35 tasks). Focus on core capabilities that unblock multi-turn workflows.

### Phase 1: Stateful Context (Lowest Effort, Highest Impact)

Enhance existing `spawn_sequential()` with proper context management:

```python
# Current: naive string concatenation
accumulated_context += result.output + "\n"

# Improved: structured context with trimming
class ContextAccumulator:
    turns: list[Turn]
    max_tokens: int
    def add_turn(self, role, content): ...
    def get_prompt(self) -> str: ...
    def trim_if_needed(self): ...
```

**Benefits**: Existing sequential spawning becomes stateful.

### Phase 2: Session Persistence

Extend checkpoints to persist conversation state:

```python
# Extend CheckpointState with conversation
@dataclass
class CheckpointState:
    execution_id: str
    tasks: list[TaskState]
    conversation: list[Turn]  # NEW
    metadata: dict[str, Any]
```

**Benefits**: Resume conversations after interruption.

### Phase 3: Interactive REPL (If Needed)

Add `--interactive` flag with minimal REPL:
- Prompt loop with agent
- Context accumulated per turn
- Session auto-saved on exit

**Consider**: Do you need full REPL, or is stateful sequential enough?

---

## Implementation Options

### Option A: Minimal Statefulness (Recommended)

Focus on making existing spawn modes stateful. Reuse checkpoint infrastructure.

| Task | Effort | Impact |
|------|--------|--------|
| Add `ContextAccumulator` class | Small | High |
| Integrate into `spawn_sequential()` | Small | High |
| Extend checkpoints with conversation | Medium | Medium |
| Add `--resume` for conversation resume | Small | High |

**Total**: ~8-10 tasks

### Option B: Full OpenSpec Implementation

Implement `add-multiturn-agent-spawning` (35 tasks).

**Pros**: Complete solution
**Cons**: Large effort, may over-engineer for current needs

### Option C: Hybrid

Phase 1 from Option A, then evaluate if REPL is needed.

---

## Questions Before Proceeding

1. **Primary use case**: Sequential task chains with context, or interactive exploration?

2. **Context trimming**: Sliding window (keep first 2 + last 10 turns) sufficient?

3. **Session format**: Extend existing checkpoints, or separate session files?

4. **REPL priority**: Nice-to-have, or critical path?

---

## Related Specs

- `openspec/changes/add-multiturn-agent-spawning/` - Full design
- `openspec/changes/enhance-spawn-interactive-mode/` - Alternative approach
- `.aurora/plans/active/0001-improve-aur-spawn-capabilities/` - Adhoc agents

---

## Success Criteria

- [ ] `aur spawn --sequential` preserves structured context between tasks
- [ ] Context trimmed automatically to prevent overflow
- [ ] `aur spawn --resume <id>` restores conversation state
- [ ] Token usage tracked and reported
- [ ] Backward compatible with existing spawn usage

---

## Next Steps

1. **Clarify requirements**: Answer questions above
2. **Choose option**: A (minimal), B (full), or C (hybrid)
3. **Generate tasks.md**: Based on chosen option
4. **Create spec deltas**: If new capabilities required
