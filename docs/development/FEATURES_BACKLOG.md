# Aurora Features Backlog

Strategic features and capabilities planned for future development. Organized by priority and dependencies.

---

## Interactive Agent Sessions (`aur interact`)

**Status:** Backlog
**Priority:** High
**Complexity:** Medium-High
**Depends On:** Conditions below

### Description

Separate interactive command for multi-turn agent conversations with resume capabilities.

```bash
aur interact "help me write a fantasy novel"
```

Key differences from `aur soar` (one-shot):
- Multi-turn conversations with agents
- Agents can ask clarifying questions mid-execution
- Stateful sessions with resume support
- Conversation logs persisted per agent/session
- Interactive prompt-response loops

### Use Cases

1. **Creative tasks** need back-and-forth
   - "Help me write a novel" → agent asks about tone/genre/POV/audience → better output
   - Editorial feedback on prose → iterative refinement

2. **Complex decomposition** benefits from clarification
   - Agent finds ambiguity in task → asks user for specifics
   - Refines understanding before execution

3. **Long-running work** needs audit trails and recovery
   - Resume interrupted sessions: `aur interact --resume <session-id>`
   - Inspect conversation history for debugging
   - Replay or continue from any point

### Implementation Notes

**Architecture:**
- Reuse SOAR decomposition (initial planning)
- Spawn agents in **interactive mode** (not one-shot)
- Each agent manages its own session state
- Orchestrator uses fire-and-forget with callbacks (loose coupling)
- Async execution with proper session management

**Data model:**
```
Session
├── goal
├── decomposition (from SOAR)
├── agents[]
│   ├── id
│   ├── status (running, paused, completed)
│   ├── conversation[]
│   │   ├── role (user, agent)
│   │   ├── content
│   │   └── timestamp
│   └── state (for resume)
└── created_at, resumed_at, completed_at
```

**CLI enhancements:**
- `aur interact <goal> [--mode interactive|batch]`
- `aur interact --resume <session-id>`
- `aur interact --list` (show active/paused sessions)
- `aur interact --log <session-id>` (inspect conversation)

### Preconditions (Must Complete First)

#### 1. ✅ Agent Gap Detection & Ad-hoc Spawning
- **Status:** DONE (completed Jan 2026)
- **What:** Binary gap detection (ideal vs assigned), spawning missing agents
- **Used by:** Agent selection in interactive mode

#### 2. ⏳ Robust Task Execution & Error Recovery
- **Status:** In Progress
- **What:** Reliable execution recovery, error handling, retry logic
- **Why:** Interactive sessions need strong guarantees
- **Blocker:** If agent crashes mid-conversation, recovery must be seamless

#### 3. ⏳ Reliable Decomposition
- **Status:** Mostly stable, edge cases remain
- **What:** SOAR decomposition handles ambiguous goals gracefully
- **Why:** Interactive decomposition queries require clarity

#### 4. ⏳ Agent Composition for Complex Workflows
- **Status:** Early stage
- **What:** Multiple agents working together (orchestration, handoff, state passing)
- **Why:** Interactive sessions will involve dependent tasks and agent chains

### Why Not Now?

**Cost-to-value analysis:**

**Cost (Implementation):**
- Conversation persistence (database, versioning)
- Agent question formulation (LLM prompt tuning — agents asking good questions is hard)
- Async orchestration (concurrent sessions, timeouts, cleanup)
- State merging (resume logic for multi-agent sessions)
- UI/UX for multi-turn dialogs

**Value (Realized only if core is solid):**
- If execution recovery is fragile, interactive sessions fail mid-conversation
- If decomposition is flaky, users can't resume reliably
- If agent composition doesn't work, handoff between agents breaks
- Adds significant operational complexity (session management, cleanup)

**Decision:** Ship this **after** execution guarantees strengthen. Better to have a boring-but-reliable one-shot system (`aur soar`) than a fancy-but-flaky interactive one.

### Success Criteria

When conditions are met:
- [ ] Execution recovery handles agent failures gracefully (no data loss)
- [ ] SOAR decomposition >95% success rate on diverse goals
- [ ] Agent composition tested in production workflows
- [ ] Session persistence layer designed and validated
- [ ] Agent question prompts tuned (agents ask helpful questions)

### Related Issues/PRs

- (Link to execution recovery epic when created)
- (Link to decomposition hardening when created)
- (Link to agent composition work when created)

---

## Future Enhancements (Tentative)

### Real-time Agent Monitoring

Stream agent progress, sub-task completion, and logs to user in real-time.

### Agent Composition Patterns

Built-in patterns for common multi-agent workflows:
- Sequential (A → B → C)
- Parallel with merge (A, B → C)
- Map-reduce (many A → B)
- Hierarchical (coordinator → specialists)

### Knowledge Persistence Across Sessions

Agents retain learned context across sessions (with user consent).

### Human-in-the-Loop Approval

For critical decisions, agents can escalate to user for approval before proceeding.

---

## Completed Features

### Agent Gap Detection & Ad-hoc Spawning ✅

**Completed:** January 2026

Binary comparison: `ideal_agent != assigned_agent` → gap detected.
- Single LLM call outputs both ideal and assigned agents
- No confidence thresholds (simplified to binary)
- Ad-hoc spawning when ideal agent doesn't exist in manifest
- Used by `aur soar` (spawning) and `aur goals` (reporting gaps)

**Removed fields:** confidence, recommended_agent, agent_exists, fallback, suggested_capabilities, suggested_specialty

**Files modified:**
- `packages/cli/src/aurora_cli/planning/models.py`
- `packages/cli/src/aurora_cli/planning/decompose.py`
- `packages/cli/src/aurora_cli/planning/core.py`
- `packages/cli/src/aurora_cli/commands/goals.py`

---

**Last Updated:** January 13, 2026
**Maintained By:** Aurora Development Team
