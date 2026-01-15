# Plan: Improve aur spawn Capabilities with Adhoc Agent Spawning

## Goals Context
> Source: `goals.json`

| Subgoal | Agent | Dependencies |
|---------|-------|--------------|
| Plan and design approach | @holistic-architect | - |
| Implement solution | @full-stack-dev | sg-1 |
| Test and verify | @qa-test-architect | sg-2 |

---

## Problem Statement

Aurora's agent discovery system currently detects **agent gaps** (when subgoals need specialized agents not in the registry), but `aur spawn` cannot act on these gaps. When gaps are detected:

1. Gaps are logged in `goals.json` under the `gaps` array
2. Users see warnings: "Agent gaps detected: 3 subgoals need attention"
3. **No automatic action**: Tasks fail or fall back to generic LLM

**Current behavior** (from `packages/cli/src/aurora_cli/planning/agents.py`):
```python
# Gap detection happens
gap = AgentGap(
    subgoal_id=subgoal.id,
    ideal_agent="@specialized-agent",
    assigned_agent="@generic-fallback"
)
# But spawn doesn't use this information!
```

**User pain point**: After running `aur goals`, gaps are identified but execution stalls because spawn can't create adhoc agents for missing specializations.

## Proposed Solution

Enhance `aur spawn` to automatically spawn adhoc agents when agent gaps are detected during execution. This involves:

1. **Gap-Aware Spawning**: Read gaps from `goals.json` during spawn execution
2. **Adhoc Agent Creation**: Generate agent prompts from gap metadata (ideal_agent_desc)
3. **Dynamic Agent Assignment**: Route gapped tasks to adhoc agents instead of fallback
4. **Validation & Feedback**: Report which tasks used adhoc agents

### Architecture Changes

```
Current Flow:
aur goals → gaps detected → goals.json written → aur spawn → ❌ ignores gaps

Improved Flow:
aur goals → gaps detected → goals.json written → aur spawn → ✓ reads gaps → creates adhoc agents → executes with specialized agents
```

## Benefits

1. **Seamless execution**: No manual intervention when specialized agents missing
2. **Better task quality**: Adhoc agents get specialized context from `ideal_agent_desc`
3. **User visibility**: Clear reporting of which agents were spawned adhoc
4. **Backward compatible**: Existing spawn behavior unchanged when no gaps

## Scope

### In Scope
- Modify `aur spawn` to read `goals.json` and detect agent gaps
- Implement adhoc agent spawning using gap metadata
- Dynamic task routing to adhoc vs registry agents
- Execution reporting for adhoc agent usage
- Unit + integration tests for gap-aware spawning

### Out of Scope
- Changing gap detection logic (already works)
- Persisting adhoc agents to registry (one-time use)
- Interactive gap resolution (future enhancement)
- Multi-agent coordination within spawn

## Dependencies

**Existing Systems**:
- `packages/cli/src/aurora_cli/planning/agents.py` - Gap detection (AgentGap model)
- `packages/cli/src/aurora_cli/planning/models.py` - AgentGap, Goals models
- `packages/cli/src/aurora_cli/commands/spawn.py` - Spawn command
- `packages/spawner/src/aurora_spawner/spawner.py` - Core spawn logic

**Modified Components**:
- `packages/cli/src/aurora_cli/commands/spawn.py` - Add gap awareness
- `packages/spawner/src/aurora_spawner/spawner.py` - Support adhoc agent prompts

**New Components**:
- `packages/cli/src/aurora_cli/commands/spawn_helpers.py` - Gap resolution utilities
- `packages/spawner/src/aurora_spawner/adhoc.py` - Adhoc agent generation

## Implementation Strategy

### Phase 1: Gap Loading (2 tasks)
Load and validate agent gaps from `goals.json` during spawn initialization.

### Phase 2: Adhoc Agent Generation (3 tasks)
Generate agent prompts from gap metadata for subprocess spawning.

### Phase 3: Dynamic Routing (3 tasks)
Route tasks to adhoc agents when gaps detected, fallback to registry agents otherwise.

### Phase 4: Reporting & Validation (3 tasks)
Display adhoc agent usage in spawn output, add comprehensive tests.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Adhoc agent quality** | Medium | Use detailed `ideal_agent_desc` from gap metadata |
| **goals.json missing** | Low | Graceful fallback to existing spawn behavior |
| **Parsing failures** | Low | Validate JSON schema, show clear error messages |
| **Performance overhead** | Low | Gap loading is one-time on spawn start |

## Success Criteria

- [ ] `aur spawn` reads `goals.json` and detects agent gaps
- [ ] Adhoc agents created from gap metadata (ideal_agent_desc)
- [ ] Tasks with gaps execute using adhoc agents
- [ ] Spawn output reports adhoc agent usage
- [ ] Existing spawn behavior unchanged when no gaps
- [ ] 95%+ test coverage for new functionality
- [ ] Integration test: goals → spawn with gaps → successful execution

## Open Questions

1. **Adhoc agent prompt format**: How detailed should the generated prompt be?
   - **Recommendation**: Use `ideal_agent_desc` + task description + project context

2. **Caching adhoc agents**: Should adhoc agents be reused within same spawn?
   - **Recommendation**: Yes, cache by ideal_agent ID for spawn session

3. **Error handling**: What if adhoc agent creation fails?
   - **Recommendation**: Fall back to assigned_agent, log warning

4. **User notification**: Should users be prompted before spawning adhoc agents?
   - **Recommendation**: No for MVP, add `--confirm-adhoc` flag in v2
