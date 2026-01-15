# Proposal: Interactive Multi-Turn Mode for aur spawn

## Change ID
`enhance-spawn-interactive-mode`

## Summary
Add an interactive conversation mode (`--interactive` / `-i`) to `aur spawn` that allows users to continue chatting with a spawned agent in a REPL-style interface, maintaining context across multiple turns until the user exits.

## Problem Statement

Currently, `aur spawn` executes tasks in a one-shot manner:
1. Load tasks from file
2. Spawn agents for each task
3. Execute tasks
4. Return results and exit

This creates friction for:
- **Iterative refinement**: Users who want to ask follow-up questions or refine their request
- **Exploratory workflows**: Investigating a topic through multiple related queries with the same agent
- **Debugging assistance**: Getting clarification and additional context without re-spawning
- **Ad-hoc agent interaction**: Users who want to spawn a single agent and have a conversation

**Example pain point**:
```bash
# Current: Need to create a task file for every interaction
echo "- [ ] 1. Analyze this code" > task.md
aur spawn task.md

# Follow-up requires another file
echo "- [ ] 1. Now optimize it" > task2.md
aur spawn task2.md

# Context from first spawn is lost
```

## Proposed Solution

Add `--interactive` mode that:

1. **Spawns an agent interactively**: User specifies agent and gets a REPL
2. **Maintains conversation context**: All turns share accumulated history
3. **Supports session commands**: Built-in commands for context management, history, saving
4. **Integrates with existing spawn**: Works alongside task-based spawning

### Example Workflow

```bash
# Start interactive session with specific agent
$ aur spawn --interactive --agent qa-test-architect

Aurora Spawn Interactive Mode
Agent: @qa-test-architect
Type /help for commands, /exit to quit

> Analyze test coverage for packages/cli

[Agent analyzes and responds...]

> What's missing in the authentication tests?

[Agent provides specific gaps based on previous context...]

> Generate a test plan for those gaps

[Agent creates plan using full conversation context...]

> /save test-plan.md

Saved conversation to test-plan.md

> /exit

Session saved to ~/.aurora/spawn/sessions/2026-01-14-123456.json
```

### Without Agent (Quick Mode)

```bash
# No agent specified - prompts for direct query
$ aur spawn -i

Aurora Spawn Interactive Mode
Type /help for commands, /exit to quit

> What files handle authentication?

[LLM searches and responds...]

> Show me the login function

[Continues conversation...]
```

## Benefits

1. **Reduces friction**: No task file needed for ad-hoc conversations
2. **Preserves context**: Agent remembers the entire conversation
3. **Supports iteration**: Refine queries and explore topics naturally
4. **Saves sessions**: Conversation history for future reference
5. **Familiar UX**: REPL interface like Python/Node interactive shells

## Scope

### In Scope
- `--interactive` / `-i` flag for interactive mode
- REPL loop with prompt/response
- Session commands: `/help`, `/exit`, `/save`, `/history`, `/clear`, `/agent`
- Context accumulation across turns
- Session persistence to `~/.aurora/spawn/sessions/`
- Agent specification via `--agent` flag
- Rich formatting for output (syntax highlighting, tables)

### Out of Scope
- Multi-agent switching within same session (future: `/switch <agent>`)
- Voice input/output
- Collaborative sessions (multiple users)
- Session branching/forking
- Integration with external tools beyond CLI

## Dependencies

**Existing Systems**:
- `packages/spawner` - Core spawning logic
- `packages/cli/commands/spawn.py` - CLI command
- `packages/reasoning` - LLM client for responses

**New Components**:
- Interactive REPL controller
- Session manager for context persistence
- Command parser for `/` commands
- History tracker

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Context window overflow**: Long conversations exceed model limits | Medium | - Implement context trimming (keep first/last N turns)<br>- Add `/clear` to reset context<br>- Warn user when approaching limit |
| **Session cost**: Long interactive sessions consume many tokens | Medium | - Display token count with `/stats` command<br>- Config for max turns/tokens per session<br>- Auto-save every N turns |
| **Confusing UX**: Users don't understand interactive vs task mode | Low | - Clear mode indicator in prompt<br>- Help text on entry<br>- Document both modes separately |
| **Incomplete responses**: Agent cuts off mid-response | Low | - Stream responses with progress indicator<br>- Detect truncation and allow continuation<br>- `/continue` command |

## Alternatives Considered

### Alternative 1: Extend task files with conversation syntax
**Example**:
```markdown
- [ ] 1. Analyze code
  - [ ] 1.1 Now optimize it
  - [ ] 1.2 Explain the changes
```
**Pros**: No new mode, reuses task syntax
**Cons**: Awkward for ad-hoc chat, requires file editing between turns

### Alternative 2: Separate `aur chat` command
**Example**: `aur chat --agent qa-expert`
**Pros**: Clear separation from spawn semantics
**Cons**: Code duplication, confusing command structure

### Alternative 3: Always interactive (no flag)
**Example**: Detect terminal and auto-enter REPL
**Pros**: Simple, no flags needed
**Cons**: Breaking change, breaks scripting

**Why our approach is better**: Opt-in via flag preserves backward compatibility while adding powerful new capability. Reuses spawn infrastructure and fits naturally with agent paradigm.

## Open Questions

1. **Context trimming strategy**: Should we use sliding window, summarization, or hybrid?
   - **Recommendation**: Start with sliding window (keep first 2 + last 10 turns), add summarization in v2

2. **Agent switching**: Should `/agent <new-agent>` start fresh or transfer context?
   - **Recommendation**: Start fresh (simpler), add context transfer in v2

3. **Session format**: JSON, JSONL, or Markdown?
   - **Recommendation**: JSONL for streaming, with Markdown export via `/export`

4. **Interrupt handling**: How to handle Ctrl+C during agent response?
   - **Recommendation**: Graceful cancellation, save partial response, return to prompt

## Success Criteria

- [ ] `aur spawn -i` launches interactive REPL successfully
- [ ] `aur spawn -i --agent qa-expert` spawns specific agent
- [ ] Multiple turns maintain context (tested with 3+ turn conversations)
- [ ] Session commands work: `/help`, `/exit`, `/save`, `/history`, `/clear`
- [ ] Sessions saved to `~/.aurora/spawn/sessions/`
- [ ] Token usage tracked and displayed with `/stats`
- [ ] Context trimming prevents window overflow
- [ ] Graceful error handling (network issues, invalid commands, etc.)
- [ ] Documentation covers both task-based and interactive modes
- [ ] 90%+ test coverage for new interactive components

## Related Changes

**This change**:
- Adds interactive mode to existing `aur spawn` command
- No breaking changes to task-based spawning
- New flag `--interactive` is opt-in

**Future enhancements** (not in this change):
- Session resumption: `aur spawn -i --resume <session-id>`
- Agent switching: `/switch <agent>` command
- Context summarization for long sessions
- Multi-modal input (files, images)
- Collaborative sessions
