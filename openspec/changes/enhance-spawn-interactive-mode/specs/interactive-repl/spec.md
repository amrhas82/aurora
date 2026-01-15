# Capability: Interactive REPL Mode

## Overview
Add interactive conversation mode to `aur spawn` that allows users to have multi-turn conversations with agents, maintaining context across turns in a REPL-style interface.

## ADDED Requirements

### Requirement: Launch Interactive Mode
**ID**: `spawn-interactive-launch-001`
**Priority**: HIGH
**Status**: New

The system MUST support launching interactive mode via `--interactive` flag.

#### Scenario: Launch with specific agent
**Given** user runs `aur spawn --interactive --agent qa-test-architect`
**When** command executes
**Then** interactive REPL launches with @qa-test-architect
**And** displays welcome banner
**And** shows prompt for user input

#### Scenario: Launch without agent (direct LLM)
**Given** user runs `aur spawn --interactive`
**When** command executes
**Then** interactive REPL launches without specific agent
**And** queries go directly to LLM

#### Scenario: Short flag alias
**Given** user runs `aur spawn -i`
**When** command executes
**Then** interactive mode launches (equivalent to --interactive)

---

### Requirement: REPL Loop
**ID**: `spawn-interactive-repl-001`
**Priority**: HIGH
**Status**: New

The system MUST provide a REPL loop that prompts for input, processes queries, and displays responses.

#### Scenario: Basic query-response cycle
**Given** interactive mode is active
**When** user enters "Analyze test coverage"
**Then** system spawns agent with query
**And** displays agent response
**And** returns to prompt for next input

#### Scenario: Empty input handling
**Given** interactive mode is active
**When** user presses Enter without text
**Then** prompt reappears without error

#### Scenario: Multi-line input support
**Given** interactive mode is active
**When** user enters multi-line text
**Then** all lines are captured and sent to agent

---

### Requirement: Context Accumulation
**ID**: `spawn-interactive-context-001`
**Priority**: HIGH
**Status**: New

The system MUST maintain conversation context across multiple turns.

#### Scenario: Second turn uses context from first
**Given** user asked "What is authentication?"
**And** agent responded with explanation
**When** user asks "Show me the login function"
**Then** agent has access to previous conversation
**And** understands "the login function" refers to authentication context

#### Scenario: Context includes all previous turns
**Given** 5 turns of conversation have occurred
**When** user enters 6th query
**Then** agent receives all 5 previous turns as context

---

### Requirement: Context Window Management
**ID**: `spawn-interactive-window-001`
**Priority**: MEDIUM
**Status**: New

The system MUST trim conversation history when it exceeds configured limits.

#### Scenario: Trim old turns when limit exceeded
**Given** max_turns is set to 20
**And** 21 turns have occurred
**When** context is trimmed
**Then** first 2 turns are kept (initial context)
**And** last 18 turns are kept (recent conversation)
**And** turns 3-3 are removed

#### Scenario: Warn when approaching token limit
**Given** max_tokens is set to 100000
**And** current conversation is at 95000 tokens
**When** user adds new query
**Then** system displays warning about approaching limit

---

### Requirement: Session Commands
**ID**: `spawn-interactive-commands-001`
**Priority**: HIGH
**Status**: New

The system MUST support slash commands for session management.

#### Scenario: /help command shows available commands
**Given** interactive mode is active
**When** user enters "/help"
**Then** system displays list of all commands with descriptions

#### Scenario: /exit command terminates session
**Given** interactive mode is active
**When** user enters "/exit"
**Then** session is saved to disk
**And** REPL exits gracefully
**And** displays session save location

#### Scenario: /save command exports conversation
**Given** 5 turns of conversation have occurred
**When** user enters "/save myfile.md"
**Then** conversation is exported to myfile.md in Markdown format

#### Scenario: /save without filename uses auto-generated name
**Given** user enters "/save"
**When** command executes
**Then** filename is auto-generated with timestamp and agent name

#### Scenario: /history command shows conversation
**Given** 3 turns of conversation have occurred
**When** user enters "/history"
**Then** all 3 turns are displayed with role labels

#### Scenario: /clear command resets context
**Given** 5 turns of conversation have occurred
**When** user enters "/clear"
**Then** conversation history is cleared
**And** next query starts fresh conversation

#### Scenario: /agent command switches agent
**Given** currently using @qa-expert
**When** user enters "/agent full-stack-dev"
**Then** agent switches to @full-stack-dev
**And** context is cleared (fresh conversation)

#### Scenario: /stats command shows session info
**Given** 10 turns with estimated 5000 tokens
**When** user enters "/stats"
**Then** displays turn count: 10
**And** displays estimated tokens: 5000
**And** displays current agent

---

### Requirement: Session Persistence
**ID**: `spawn-interactive-persistence-001`
**Priority**: MEDIUM
**Status**: New

The system MUST save conversation sessions to disk on exit.

#### Scenario: Auto-save on exit
**Given** interactive session with 5 turns
**When** user exits with /exit
**Then** session is saved to ~/.aurora/spawn/sessions/<timestamp>.json
**And** displays save confirmation

#### Scenario: Session includes all metadata
**Given** session is saved
**When** session file is inspected
**Then** contains session_id
**And** contains created_at timestamp
**And** contains agent_id
**And** contains all conversation turns with timestamps

---

### Requirement: Rich Output Formatting
**ID**: `spawn-interactive-formatting-001`
**Priority**: MEDIUM
**Status**: New

The system MUST display agent responses with rich formatting.

#### Scenario: Markdown rendering
**Given** agent response contains Markdown
**When** response is displayed
**Then** Markdown is rendered (headings, lists, code blocks)

#### Scenario: Syntax highlighting for code
**Given** agent response contains code blocks
**When** response is displayed
**Then** code has syntax highlighting for the language

#### Scenario: Progress indicator during thinking
**Given** user submits query
**When** agent is processing
**Then** displays "Agent thinking..." spinner

---

### Requirement: Graceful Error Handling
**ID**: `spawn-interactive-errors-001`
**Priority**: HIGH
**Status**: New

The system MUST handle errors gracefully and allow recovery.

#### Scenario: Network error during spawn
**Given** user submits query
**When** network error occurs during spawn
**Then** displays error message
**And** returns to prompt (session continues)

#### Scenario: Invalid command handling
**Given** user enters "/unknown"
**When** command is parsed
**Then** displays "Unknown command: unknown"
**And** suggests "/help" for command list

#### Scenario: Ctrl+C during response
**Given** agent is responding
**When** user presses Ctrl+C
**Then** response is cancelled
**And** displays "Interrupted" message
**And** returns to prompt

#### Scenario: EOF handling
**Given** user presses Ctrl+D
**When** REPL loop processes EOF
**Then** session exits gracefully (equivalent to /exit)

---

### Requirement: Agent Specification
**ID**: `spawn-interactive-agent-001`
**Priority**: HIGH
**Status**: New

The system MUST support specifying agent via --agent flag.

#### Scenario: Valid agent ID
**Given** user runs `aur spawn -i --agent qa-expert`
**When** interactive mode launches
**Then** all queries use @qa-expert agent

#### Scenario: Invalid agent ID
**Given** user runs `aur spawn -i --agent nonexistent`
**When** interactive mode launches
**Then** displays warning about unknown agent
**And** proceeds with direct LLM (no agent)

---

### Requirement: Backward Compatibility
**ID**: `spawn-interactive-compat-001`
**Priority**: HIGH
**Status**: New

The system MUST preserve existing task-based spawn behavior when --interactive is not specified.

#### Scenario: Task file execution without --interactive
**Given** user runs `aur spawn tasks.md`
**When** command executes
**Then** tasks are executed in task-based mode (existing behavior)
**And** interactive mode does NOT launch

#### Scenario: No breaking changes to existing flags
**Given** user runs `aur spawn tasks.md --parallel --verbose`
**When** command executes
**Then** all existing flags work as before

---

## MODIFIED Requirements

_None - This is a new capability with no modifications to existing requirements._

---

## REMOVED Requirements

_None - This is a new capability with no removals._

---

## Dependencies

**Internal**:
- `spawn-command`: Core spawn command infrastructure
- `aurora-spawner`: Agent spawning and execution

**External**:
- `prompt-toolkit`: For enhanced REPL input (auto-completion, history)
- `rich`: For formatted output and progress indicators

---

## Non-Functional Requirements

**Performance**:
- Prompt response: <100ms
- Context trimming: <10ms
- Session save: <50ms

**Usability**:
- Clear mode indicator in prompt
- Helpful error messages
- Intuitive command syntax

**Reliability**:
- Session data preserved on crashes
- Graceful handling of network issues
- No data loss on Ctrl+C

---

## Testing Requirements

**Unit Tests**:
- REPL loop logic
- Context accumulation and trimming
- Command parsing and validation
- Session save/load

**Integration Tests**:
- Full interactive session with mocked agent
- Multi-turn conversations
- Session persistence
- Error recovery

**E2E Tests**:
- Real interactive session with agent
- All slash commands
- Context accumulation verification

**Coverage Target**: 90%+ for new interactive components

---

## Acceptance Criteria

- [ ] `aur spawn -i` launches interactive REPL
- [ ] `aur spawn -i --agent <id>` uses specified agent
- [ ] Multiple turns maintain shared context
- [ ] All slash commands work: /help, /exit, /save, /history, /clear, /agent, /stats
- [ ] Sessions saved to ~/.aurora/spawn/sessions/ on exit
- [ ] Rich formatting (Markdown, syntax highlighting)
- [ ] Graceful error handling (network, Ctrl+C, invalid commands)
- [ ] Context trimming when limits exceeded
- [ ] Zero breaking changes to existing task-based spawning
- [ ] Documentation covers interactive mode with examples
- [ ] 90%+ test coverage
