# Spec Delta: CLI Integration

**Capability**: `cli-integration`
**Type**: MODIFIED
**Related**: `session-management`, `interactive-repl`

---

## MODIFIED Requirements

### Requirement: Spawn Command Options

The `aur spawn` command SHALL support new flags for multi-turn mode.

**Rationale**: Provide entry points for interactive sessions and resumption.

#### Scenario: Interactive Flag

**Given** a user wants to enter interactive mode
**When** they run `aur spawn --interactive`
**Then** the interactive REPL SHALL start
**And** the task file parameter SHALL be optional (not required)
**And** the REPL SHALL use default agent (or prompt for agent)

#### Scenario: Interactive with Agent

**Given** a user wants a specific agent
**When** they run `aur spawn --interactive --agent qa-test`
**Then** the REPL SHALL start with the qa-test agent
**And** all turns SHALL use the specified agent
**And** the agent SHALL be shown in the prompt

#### Scenario: Interactive with Session ID

**Given** a user wants a named session for later resume
**When** they run `aur spawn --interactive --session my-review`
**Then** the session SHALL be created with ID "my-review"
**And** the session file SHALL be named `my-review.jsonl`
**And** the user can later resume with `--resume my-review`

#### Scenario: Short Flag Alias

**Given** a user wants concise syntax
**When** they run `aur spawn -i`
**Then** it SHALL behave identically to `aur spawn --interactive`

---

### Requirement: Session Resume

The `aur spawn` command SHALL support resuming saved sessions.

**Rationale**: Allow users to continue conversations across CLI invocations.

#### Scenario: Resume by Session ID

**Given** a saved session exists with ID "qa-review-001"
**When** a user runs `aur spawn --resume qa-review-001`
**Then** the session SHALL be loaded from disk
**And** all historical turns SHALL be restored to context
**And** the REPL SHALL start with the previous agent
**And** the prompt SHALL indicate session is resumed

#### Scenario: Resume Nonexistent Session

**Given** no session exists with ID "invalid-123"
**When** a user runs `aur spawn --resume invalid-123`
**Then** an error SHALL be displayed: "Session not found: invalid-123"
**And** available sessions SHALL be listed
**And** the CLI SHALL exit with code 1

#### Scenario: Resume Completed Session

**Given** a session with status "completed"
**When** a user resumes it
**Then** a warning SHALL be shown: "Resuming completed session"
**And** the REPL SHALL start normally
**And** the user can continue the conversation

---

### Requirement: Session Utility Commands

The `aur spawn` command SHALL provide utility flags for session management.

**Rationale**: Allow users to manage sessions from CLI without entering REPL.

#### Scenario: List Sessions

**Given** multiple saved sessions exist
**When** a user runs `aur spawn --list-sessions`
**Then** all sessions SHALL be displayed in a table
**And** the table SHALL include: ID, agent, turns, created, status
**And** the output SHALL be sorted by most recent
**And** the CLI SHALL exit after display (not enter REPL)

#### Scenario: List Sessions with Filter

**Given** sessions exist for multiple agents
**When** a user runs `aur spawn --list-sessions --agent qa-test`
**Then** only sessions for "qa-test" agent SHALL be shown
**And** the count of filtered sessions SHALL be displayed

#### Scenario: Delete Session

**Given** a session exists with ID "old-session"
**When** a user runs `aur spawn --delete-session old-session`
**Then** a confirmation prompt SHALL appear: "Delete session 'old-session'? [y/N]"
**And** if user confirms, the session file SHALL be deleted
**And** a success message SHALL be shown
**And** the CLI SHALL exit

#### Scenario: Clean Old Sessions

**Given** sessions exist with various ages
**When** a user runs `aur spawn --clean-sessions 30`
**Then** sessions older than 30 days SHALL be deleted
**And** the count of deleted sessions SHALL be reported
**And** no confirmation SHALL be required (batch operation)

---

### Requirement: Backward Compatibility

The `aur spawn` command SHALL maintain existing task-based behavior.

**Rationale**: Ensure no breaking changes for current users.

#### Scenario: Default Task-Based Behavior

**Given** a user has a task file `tasks.md`
**When** they run `aur spawn` (no flags)
**Then** the task file SHALL be loaded
**And** tasks SHALL be executed in parallel (existing behavior)
**And** the interactive mode SHALL NOT activate
**And** the command SHALL behave identically to previous version

#### Scenario: Explicit Task File

**Given** a user specifies a task file
**When** they run `aur spawn my-tasks.md`
**Then** the specified file SHALL be loaded
**And** tasks SHALL be executed (existing behavior)
**And** the interactive mode SHALL NOT activate

#### Scenario: Task Mode with Interactive Flag Error

**Given** a user provides both task file and interactive flag
**When** they run `aur spawn tasks.md --interactive`
**Then** an error SHALL be displayed: "Cannot use --interactive with task file"
**And** a hint SHALL suggest: "Use either task file OR --interactive"
**And** the CLI SHALL exit with code 1

---

### Requirement: Help Text and Documentation

The `aur spawn` command help SHALL clearly document multi-turn features.

**Rationale**: Make new functionality discoverable.

#### Scenario: Show Help with New Options

**Given** a user wants to see available options
**When** they run `aur spawn --help`
**Then** the help text SHALL include:
- `--interactive, -i`: Enter interactive multi-turn mode
- `--agent AGENT`: Specify agent for interactive session
- `--session ID`: Named session for resumption
- `--resume ID`: Resume saved session
- `--list-sessions`: List all saved sessions
- `--delete-session ID`: Delete a session
- `--clean-sessions DAYS`: Clean sessions older than DAYS

#### Scenario: Help Shows Usage Examples

**Given** a user runs `aur spawn --help`
**When** the help text is displayed
**Then** it SHALL include example commands:
```
Examples:
  aur spawn                    # Execute tasks from tasks.md (default)
  aur spawn -i                 # Start interactive mode
  aur spawn -i --agent qa-test # Interactive with specific agent
  aur spawn --resume my-session # Continue previous session
  aur spawn --list-sessions    # View all sessions
```

---

## Cross-References

- **Depends on**: `session-management`, `interactive-repl`
- **Modifies**: Existing `aur spawn` command (backward compatible)
- **Enables**: User-facing multi-turn functionality
