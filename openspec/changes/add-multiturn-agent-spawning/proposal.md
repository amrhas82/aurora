# Proposal: Add Multi-Turn Agent Spawning to aur spawn

## Change ID
`add-multiturn-agent-spawning`

## Summary
Enhance `aur spawn` with multi-turn conversation capability, allowing agents to maintain context across multiple interactions within a single spawned session. This enables iterative refinement, follow-up questions, and exploratory workflows without re-spawning agents.

## Problem Statement

Currently, `aur spawn` operates in a single-shot model:
- User creates task file
- Agent spawned for task
- Agent completes task and exits
- Context lost

**Pain points**:
1. **Lost context**: Follow-up questions require complete re-spawn with no memory
2. **File overhead**: Every interaction needs a new task file
3. **Workflow interruption**: Manual context management between spawns
4. **Inefficient exploration**: Cannot iteratively refine or explore topics with same agent

**Current workaround**:
```bash
# First interaction
echo "- [ ] 1. Analyze authentication flow" > task1.md
aur spawn task1.md

# Follow-up requires new file, loses previous context
echo "- [ ] 1. Now add rate limiting" > task2.md
aur spawn task2.md  # Agent doesn't remember first analysis
```

## Proposed Solution

Add multi-turn capability to `aur spawn` that allows continuing conversations with spawned agents while preserving full context.

### Core Capabilities

1. **Context Persistence**: Agents remember entire conversation history
2. **Session Management**: Save/resume conversation sessions
3. **Interactive REPL**: Optional interactive mode for exploratory work
4. **Backward Compatible**: Existing task-based spawning unchanged

### Usage Patterns

#### Pattern 1: Interactive REPL Mode
```bash
# Spawn agent in interactive mode
$ aur spawn --interactive --agent qa-test-architect

Aurora Spawn Interactive (qa-test-architect)
Type /help for commands, /exit to quit

> Analyze test coverage for authentication module

[Agent analyzes and responds with coverage report...]

> What specific gaps did you find?

[Agent references previous analysis, details specific gaps...]

> Create a test plan for the top 3 gaps

[Agent creates plan using full conversation context...]

> /save auth-test-plan.md
Saved to auth-test-plan.md

> /exit
Session saved: ~/.aurora/spawn/sessions/2026-01-14-qa-test-123456.json
```

#### Pattern 2: Multi-Turn Task Files
```markdown
<!-- tasks-with-context.md -->
- [ ] 1. Analyze authentication code for security issues
  <!-- agent: security-expert -->
  <!-- turns: 3 -->

  Turn 1: Initial analysis
  Turn 2: Deep dive on JWT handling
  Turn 3: Generate remediation plan
```

```bash
$ aur spawn tasks-with-context.md --multi-turn
# Agent completes all 3 turns with accumulated context
```

#### Pattern 3: Session Resume
```bash
# Start session
$ aur spawn -i --agent architect --session arch-review-001

# Later, resume same session
$ aur spawn --resume arch-review-001
# Context automatically restored
```

## Benefits

1. **Natural Conversations**: Ask follow-ups without repeating context
2. **Efficient**: Reuse spawned agent instead of cold starts
3. **Exploratory Workflows**: Investigate topics through multi-turn dialogue
4. **Session History**: Review and resume past conversations
5. **Cost Effective**: Single spawn for multiple interactions

## Scope

### In Scope
- Interactive REPL mode (`--interactive`, `-i`)
- Multi-turn task syntax in markdown files
- Session persistence and resume (`--session`, `--resume`)
- Context management (history, trimming, reset)
- Session commands (`/help`, `/exit`, `/save`, `/history`, `/clear`)
- Backward compatible with existing spawn behavior

### Out of Scope
- Agent switching mid-session (future enhancement)
- Multi-agent collaboration in single session
- Voice input/output
- Streaming token-by-token responses
- Session branching/forking

## Dependencies

**Existing Systems**:
- `packages/spawner/spawner.py` - Core spawn logic
- `packages/cli/commands/spawn.py` - CLI command
- `packages/reasoning` - LLM client
- `packages/core` - Memory/context management

**New Components Required**:
- `packages/spawner/session.py` - Session state management
- `packages/spawner/interactive.py` - REPL controller
- `packages/spawner/context.py` - Context accumulation/trimming
- `packages/cli/commands/spawn_helpers.py` - Session utilities (extend existing)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Context window overflow** | High | - Sliding window: keep first 2 + last 10 turns<br>- `/clear` command to reset<br>- Warn at 80% capacity |
| **Token cost explosion** | Medium | - Display running token count<br>- Config for max turns/tokens<br>- Auto-save every N turns |
| **State corruption** | Medium | - Validate session files on load<br>- Atomic writes<br>- Backup before mutations |
| **UX confusion** | Low | - Clear mode indicators<br>- Comprehensive help<br>- Separate docs for modes |
| **Performance degradation** | Low | - Async I/O for session saves<br>- Lazy load history<br>- Background cleanup |

## Alternatives Considered

### Alternative 1: Separate `aur chat` command
**Pros**: Clear separation of concerns
**Cons**: Code duplication, confusing command taxonomy
**Why rejected**: Adds cognitive load, fragments spawn functionality

### Alternative 2: Always multi-turn (no flag)
**Pros**: Simpler UX, no mode switching
**Cons**: Breaking change, breaks scripting
**Why rejected**: Not backward compatible

### Alternative 3: External session manager
**Pros**: Decoupled from spawn
**Cons**: More complex, requires coordination
**Why rejected**: Over-engineered for current needs

**Our approach**: Opt-in flag (`--interactive`) preserves backward compatibility while adding powerful new capability. Reuses existing spawn infrastructure.

## Open Questions

1. **Context trimming strategy**: Sliding window vs summarization vs hybrid?
   - **Recommendation**: Start with sliding window (simpler), add summarization in v2

2. **Session file format**: JSON vs JSONL vs SQLite?
   - **Recommendation**: JSONL for append-only writes, easy parsing

3. **Agent state isolation**: Should sessions share memory or isolate?
   - **Recommendation**: Isolate by default, add shared context as opt-in

4. **Interrupt handling**: Ctrl+C during agent response?
   - **Recommendation**: Save partial response, return to prompt gracefully

5. **Session expiration**: Auto-clean old sessions?
   - **Recommendation**: Config option (default: 30 days), `--clean-sessions` flag

## Success Criteria

- [ ] `aur spawn -i` launches interactive REPL
- [ ] `aur spawn -i --agent <name>` spawns specific agent
- [ ] Multi-turn tasks execute with context preservation
- [ ] Session save/resume works reliably
- [ ] Context trimming prevents window overflow
- [ ] Token tracking and display functional
- [ ] Session commands operational: `/help`, `/exit`, `/save`, `/history`, `/clear`
- [ ] Backward compatibility: existing spawn usage unchanged
- [ ] Error handling: network failures, invalid input, etc.
- [ ] Documentation covers all modes
- [ ] 95%+ test coverage for new components

## Related Changes

**Builds on**:
- Current `aur spawn` implementation (no breaking changes)
- Existing checkpoint system (extends for session state)

**Enables future**:
- Session resumption with context summarization
- Multi-agent collaboration
- Agent switching mid-session
- Context search within sessions

**Similar to**:
- `enhance-spawn-interactive-mode` (overlapping scope, different implementation approach)
