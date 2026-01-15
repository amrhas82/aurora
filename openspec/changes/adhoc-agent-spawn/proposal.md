# Proposal: Ad-hoc Agent Spawning

## Change ID
`adhoc-agent-spawn`

## Summary
Enable `aur spawn` to automatically detect missing agents and dynamically generate agent definitions (role + goal) for tasks that reference non-existent agents, eliminating the need for pre-defined agent markdown files for one-off or specialized tasks.

## Problem Statement

Currently, `aur spawn` requires all agents to be pre-defined in markdown files and registered in the agent manifest. When a task references an agent that doesn't exist (e.g., `<!-- agent: data-migration-specialist -->`), the system either:
1. Falls back to `agent=None` (direct LLM)
2. Fails with an error

This creates friction for:
- **One-off specialized tasks**: Tasks requiring domain-specific expertise that doesn't warrant a permanent agent definition
- **Exploratory workflows**: Users experimenting with different agent personas without committing to full agent files
- **Dynamic task generation**: SOAR or other systems generating tasks that reference specialized agents not in the manifest

## Proposed Solution

Extend `aur spawn` with **ad-hoc agent inference** that:

1. **Detects missing agents**: When a task specifies `<!-- agent: unknown-agent -->` and the agent isn't in the manifest, trigger ad-hoc agent generation instead of failing
2. **Infers agent definition**: Use LLM to analyze the task description and generate:
   - `role`: Human-readable agent title (e.g., "Data Migration Specialist")
   - `goal`: Brief description of agent's purpose based on task context
3. **Spawns ephemeral agent**: Execute the task with the inferred agent definition, passing role/goal as context to the spawned CLI tool
4. **Optional caching**: Store inferred agent definitions for reuse within the same spawn session (not persisted to manifest)

### Example Workflow

**Before (current behavior)**:
```bash
# Task file: tasks.md
- [ ] 1. Migrate legacy database schema to PostgreSQL 14
<!-- agent: db-migration-expert -->

# Execute
$ aur spawn tasks.md
Warning: Agent 'db-migration-expert' not found, defaulting to self
```

**After (with ad-hoc agents)**:
```bash
# Same task file
$ aur spawn tasks.md --adhoc
Loaded 1 tasks from tasks.md
Agent 'db-migration-expert' not found - generating ad-hoc definition...
  → Role: Database Migration Specialist
  → Goal: Execute database schema migrations with PostgreSQL expertise
Executing tasks in parallel...
✓ Task 1: Success (using ad-hoc agent)
```

## Benefits

1. **Lower barrier to entry**: Users can reference specialized agents without creating full agent files
2. **SOAR integration**: Decompose phase can generate tasks with domain-specific agents without pre-registration
3. **Flexible workflows**: Support dynamic task generation where agent types aren't known upfront
4. **Graceful degradation**: If ad-hoc generation fails, fall back to direct LLM execution

## Scope

### In Scope
- Ad-hoc agent role/goal inference from task descriptions
- Integration with existing spawn command via `--adhoc` flag
- Session-level caching of inferred agents (not persisted)
- Validation of inferred agent definitions
- Fallback behavior when inference fails

### Out of Scope
- Permanent storage of ad-hoc agents in manifest (future: `aur spawn promote-agent`)
- Multi-task agent inference (inferring same agent across multiple tasks)
- Custom agent templates for inference
- Agent capability inference beyond role/goal

## Dependencies

**Existing Systems**:
- `packages/spawner` - Core spawning logic
- `packages/cli/commands/spawn.py` - CLI command implementation
- `packages/cli/agent_discovery/` - Agent manifest system
- `packages/reasoning` - LLM client for inference

**New Components**:
- Ad-hoc agent inference module
- Agent definition validator
- Session-level agent cache

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Inference quality**: Generated agents may not match task requirements | Medium | - Provide task context to inference prompt<br>- Validate inferred definitions<br>- Allow manual override with `--agent-role` and `--agent-goal` flags |
| **Token costs**: Every missing agent triggers LLM call | Low | - Session-level caching of inferred agents<br>- Opt-in via `--adhoc` flag (default: fail fast)<br>- Batch inference for multiple missing agents |
| **Confusion**: Users may not realize they're using ad-hoc agents | Medium | - Clear console output showing ad-hoc generation<br>- Log inferred definitions for review<br>- Add `--adhoc-log` flag to save definitions |
| **Breaking changes**: Existing behavior assumes agents exist | Low | - Feature is opt-in via `--adhoc` flag<br>- Existing behavior preserved by default |

## Alternatives Considered

### Alternative 1: Fail fast (current behavior)
**Pros**: Clear error messaging, forces users to define agents
**Cons**: High friction for one-off tasks, blocks SOAR-generated tasks

### Alternative 2: Always use direct LLM for missing agents
**Pros**: No inference cost, simple implementation
**Cons**: Loses agent context/persona, all tasks become generic

### Alternative 3: Pre-generate agent library
**Pros**: No runtime inference cost, curated quality
**Cons**: Limited to pre-defined domains, doesn't support dynamic tasks

**Why our approach is better**: Balances flexibility (supports any agent) with quality (generates domain-specific context) while remaining opt-in.

## Open Questions

1. **Inference prompt design**: Should we use a specialized prompt template or inline generation?
   - **Recommendation**: Specialized template in `packages/reasoning/prompts/infer_agent.py`

2. **Caching strategy**: How long should inferred agents be cached?
   - **Recommendation**: Session-level only (cleared after spawn completes)

3. **Validation rules**: What makes a valid ad-hoc agent definition?
   - **Recommendation**: Must have non-empty role (max 200 chars) and goal (max 500 chars)

4. **Batch inference**: Should we infer multiple missing agents in one LLM call?
   - **Recommendation**: Yes, if >1 missing agent detected, batch inference for cost efficiency

## Success Criteria

- [ ] `aur spawn --adhoc` successfully generates agent definitions for missing agents
- [ ] Generated agents produce relevant, domain-specific responses
- [ ] Inference cost is <5% of total spawn execution cost
- [ ] Zero breaking changes to existing spawn behavior
- [ ] Documentation clearly explains ad-hoc agent workflow
- [ ] 95%+ test coverage for new inference module

## Related Changes

**Future enhancements** (not in this change):
- `aur spawn promote-agent <agent-id>` - Convert ad-hoc agent to permanent agent file
- `--adhoc-template` flag - Use custom template for inference
- Multi-task agent inference - Detect when same ad-hoc agent is needed across tasks
