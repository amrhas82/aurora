# Plan: Unify aur goals with SOAR Pipeline

## Problem Statement

`aur goals` and `aur soar` duplicate significant logic with different quality:

| Step | SOAR | Goals | Gap |
|------|------|-------|-----|
| Memory search | `retrieve_by_activation()` → CodeChunk | `search_memory_for_goal()` → paths only | Goals gets no code |
| Context building | `_build_context_summary()` reads files | Passes file paths as strings | LLM blind to code |
| Decomposition | `decompose_query()` with code context | `PlanDecomposer.decompose()` tries SOAR | Context lost in translation |
| Agent assignment | `verify_lite()` integrated | `AgentRecommender` separate class | Duplicated logic |
| File resolution | N/A (has code chunks) | `FilePathResolver` post-hoc | Redundant, low quality |

**Result**: Goals decomposition is inferior because LLM doesn't see actual code.

## Proposed Solution

Make `aur goals` use SOAR phases 1-4 directly, stopping before execution:

```
Current Goals Flow:
  search_memory_for_goal() ──► PlanDecomposer ──► AgentRecommender ──► FilePathResolver ──► goals.json
       ▲                           ▲                    ▲                    ▲
       │                           │                    │                    │
  [paths only]              [no code context]     [duplicate]           [low quality]

Unified Flow:
  SOAROrchestrator.plan_only()
       │
       ├── Phase 1: Assess (complexity)
       ├── Phase 2: Retrieve (code chunks with content)
       ├── Phase 3: Decompose (LLM sees actual code)
       ├── Phase 4: Verify (agent assignment)
       └── Output: goals.json with file_resolutions from Phase 2
```

## Architecture

### New SOAR Method: `plan_only()`

```python
class SOAROrchestrator:
    def plan_only(
        self,
        query: str,
        context_files: list[Path] | None = None,
    ) -> PlanResult:
        """Execute phases 1-4 and return plan without execution.

        Returns:
            PlanResult with subgoals, agent assignments, and file resolutions
        """
        # Phase 1: Assess complexity
        phase1 = self._phase1_assess(query)

        # Phase 2: Retrieve context (code chunks with content)
        phase2 = self._phase2_retrieve(query, phase1["complexity"])
        if context_files:
            phase2 = self._inject_context_files(phase2, context_files)

        # Phase 3: Decompose with code context
        phase3 = self._phase3_decompose(query, phase2, phase1["complexity"])

        # Phase 4: Verify + agent assignment
        phase4 = self._phase4_verify(phase3["decomposition"])

        # Build file resolutions from phase 2 code chunks
        file_resolutions = self._build_file_resolutions(phase2, phase4)

        return PlanResult(
            subgoals=phase4["subgoals"],
            agent_assignments=phase4["agent_assignments"],
            file_resolutions=file_resolutions,
            complexity=phase1["complexity"],
            context_summary=phase3.get("context_summary"),
        )
```

### Simplified Goals Command

```python
# Before: 1200+ lines in planning/core.py
# After: ~50 lines

def goals_command(goal: str, context_files: list[Path], ...):
    orchestrator = SOAROrchestrator(store=store, config=config)

    plan_result = orchestrator.plan_only(goal, context_files)

    # Convert to goals.json format
    write_goals_json(plan_result, output_path)
```

## Benefits

1. **Code context**: LLM sees actual code during decomposition
2. **Single source of truth**: No duplicate decomposition/assignment logic
3. **Consistent quality**: Goals gets same context as SOAR queries
4. **Simpler codebase**: Delete ~800 lines from planning/core.py
5. **File resolutions from retrieval**: High-quality, not post-hoc guessing

## Scope

### In Scope
- Add `plan_only()` method to SOAROrchestrator
- Refactor `aur goals` to use SOAR phases 1-4
- Delete redundant code: `PlanDecomposer`, `AgentRecommender`, `FilePathResolver`
- Update goals.json format to include code context metadata
- Maintain backward compatibility for goals.json consumers

### Out of Scope
- Changing SOAR phase implementations
- Modifying `aur spawn` (consumes goals.json, unchanged)
- Adding new SOAR phases

## Files to Change

| File | Change |
|------|--------|
| `packages/soar/src/aurora_soar/orchestrator.py` | Add `plan_only()` method |
| `packages/cli/src/aurora_cli/commands/goals.py` | Use orchestrator.plan_only() |
| `packages/cli/src/aurora_cli/planning/core.py` | Delete most of `create_plan()` |
| `packages/cli/src/aurora_cli/planning/decompose.py` | Delete (use SOAR decompose) |
| `packages/cli/src/aurora_cli/planning/agents.py` | Delete (use SOAR verify) |
| `packages/cli/src/aurora_cli/planning/memory.py` | Keep `FilePathResolver` for spawn compatibility |

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking goals.json format | Keep same schema, enrich with context |
| SOAR dependency in CLI | Already exists via `--no-decompose` flag |
| Performance regression | Phase 2 already optimized, no extra LLM calls |
| Test coverage gaps | Reuse SOAR phase tests |

## Success Criteria

- [ ] `aur goals` uses SOAR phases 1-4
- [ ] LLM sees actual code during decomposition (verify in verbose output)
- [ ] File resolutions come from Phase 2 retrieval (higher confidence)
- [ ] goals.json format unchanged for consumers
- [ ] ~800 lines deleted from planning/
- [ ] All existing tests pass
- [ ] New integration test: goals decomposition quality improved
