# Spec Delta: Interactive REPL

**Capability**: `interactive-repl`
**Type**: ADDED
**Related**: `session-management`, `context-accumulation`, `cli-integration`

---

## ADDED Requirements

### Requirement: REPL Lifecycle

The system SHALL provide a REPL (Read-Eval-Print Loop) for interactive agent conversations.

**Rationale**: Enable natural, exploratory conversations with agents.

#### Scenario: Start Interactive Session

**Given** a user wants to interact with an agent
**When** they run `aur spawn --interactive --agent qa-test`
**Then** the REPL SHALL start
**And** a welcome banner SHALL be displayed
**And** the prompt SHALL show the agent name: `qa-test>`
**And** the prompt SHALL be ready for user input

#### Scenario: Display Welcome Banner

**Given** the REPL starts
**When** the welcome banner is displayed
**Then** it SHALL include: "Aurora Spawn Interactive Mode"
**And** it SHALL show the active agent name
**And** it SHALL show available commands: "Type /help for commands, /exit to quit"
**And** the banner SHALL be visually distinct (e.g., colored or boxed)

#### Scenario: Accept User Input

**Given** the REPL is running
**When** the prompt is displayed
**Then** the user SHALL be able to type a message
**And** pressing Enter SHALL submit the message
**And** empty input SHALL be ignored (re-prompt)
**And** whitespace-only input SHALL be ignored

#### Scenario: Exit REPL Gracefully

**Given** the REPL is running
**When** a user types `/exit`
**Then** the session SHALL be saved
**And** the session file path SHALL be displayed
**And** the REPL SHALL terminate cleanly
**And** the exit code SHALL be 0

---

### Requirement: User Message Handling

The system SHALL process user messages and return agent responses with full context.

**Rationale**: Core conversation functionality.

#### Scenario: Process User Message

**Given** a REPL session with 2 previous turns
**When** the user types "What about error handling?"
**Then** the message SHALL be added to context
**And** a prompt SHALL be built including all 3 turns (2 previous + 1 new)
**And** the agent SHALL be spawned with the full context prompt
**And** the response SHALL be displayed to the user
**And** the response SHALL be added to context

#### Scenario: Display Agent Response

**Given** an agent has responded
**When** the response is ready
**Then** it SHALL be displayed immediately
**And** syntax highlighting SHALL be applied (if response contains code)
**And** the prompt SHALL return when response is complete
**And** the user SHALL be able to continue the conversation

#### Scenario: Handle Long Response

**Given** an agent response exceeds 1000 lines
**When** the response is displayed
**Then** it SHALL be paginated or scrollable
**And** the user SHALL be able to read the full response
**And** the prompt SHALL not be obscured

---

### Requirement: Session Commands

The system SHALL support slash commands for session management.

**Rationale**: Provide in-REPL utilities without exiting.

#### Scenario: Display Help Command

**Given** the REPL is running
**When** a user types `/help`
**Then** a list of all commands SHALL be displayed
**And** each command SHALL include: name, description, usage example
**And** the help text SHALL fit on one screen
**And** the prompt SHALL return after display

#### Scenario: Save Conversation to File

**Given** a session with 5 turns
**When** a user types `/save conversation.md`
**Then** the conversation SHALL be exported to markdown format
**And** the file SHALL include: session metadata, all turns with roles, timestamps
**And** a success message SHALL be displayed: "Saved to conversation.md"
**And** the file SHALL be writable and readable

#### Scenario: Show Conversation History

**Given** a session with 10 turns
**When** a user types `/history`
**Then** all turns SHALL be displayed in order
**And** each turn SHALL show: role, abbreviated content (first 100 chars), timestamp
**And** the display SHALL be numbered
**And** the user SHALL be able to scroll through history

#### Scenario: Show Last N Turns

**Given** a session with 10 turns
**When** a user types `/history 3`
**Then** only the last 3 turns SHALL be displayed
**And** the numbering SHALL reflect actual position (e.g., 8, 9, 10)

#### Scenario: Display Session Statistics

**Given** a session with accumulated turns
**When** a user types `/stats`
**Then** the following SHALL be displayed:
- Session ID
- Agent name
- Total turns
- Estimated tokens (user + assistant)
- Context usage percentage (current / max)
**And** the statistics SHALL be formatted as a table

---

### Requirement: Error Handling

The system SHALL handle errors gracefully without crashing the REPL.

**Rationale**: Provide robust user experience.

#### Scenario: Handle Unknown Command

**Given** the REPL is running
**When** a user types `/unknown`
**Then** an error message SHALL be displayed: "Unknown command: /unknown"
**And** a hint SHALL be shown: "Type /help for available commands"
**And** the REPL SHALL remain active (not crash)
**And** the prompt SHALL return

#### Scenario: Handle Network Failure

**Given** the REPL spawns an agent
**When** the network fails during agent execution
**Then** an error message SHALL be displayed: "Network error: <details>"
**And** the turn SHALL not be added to context
**And** the user SHALL be able to retry or continue
**And** the REPL SHALL remain active

#### Scenario: Handle Keyboard Interrupt

**Given** an agent is processing a request
**When** the user presses Ctrl+C
**Then** the agent subprocess SHALL be terminated
**And** a message SHALL be displayed: "Interrupted. Returning to prompt."
**And** the partial response (if any) SHALL be discarded
**And** the REPL SHALL return to the prompt
**And** the session SHALL remain intact

#### Scenario: Handle Invalid Agent

**Given** a user specifies an invalid agent
**When** they run `aur spawn -i --agent nonexistent`
**Then** an error SHALL be displayed before REPL starts
**And** available agents SHALL be listed
**And** the user SHALL be prompted to choose a valid agent or continue without agent

---

### Requirement: Command Completion and UX

The system SHALL provide a polished REPL experience.

**Rationale**: Make the REPL intuitive and efficient.

#### Scenario: Indicate Busy State

**Given** an agent is processing
**When** waiting for response
**Then** a spinner or progress indicator SHALL be displayed
**And** the indicator SHALL animate to show activity
**And** the user SHALL know the system is working (not frozen)

#### Scenario: Multi-Line Input Support

**Given** the user wants to enter a multi-line message
**When** they type a backslash at end of line: `This is line 1 \`
**Then** the prompt SHALL continue on the next line
**And** the user can type additional lines
**And** pressing Enter without backslash SHALL submit the full message

#### Scenario: Command History (Arrow Keys)

**Given** the user has entered multiple messages
**When** they press Up Arrow
**Then** the previous command SHALL be recalled
**And** pressing Down Arrow SHALL move forward in history
**And** the user can edit and re-submit previous commands

---

## Cross-References

- **Depends on**: `session-management` (for state persistence), `context-accumulation` (for multi-turn context)
- **Enables**: Interactive workflows for exploratory tasks
- **Related**: `cli-integration` (REPL invoked from CLI)
