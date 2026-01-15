# Spec Delta: Session Management

**Capability**: `session-management`
**Type**: ADDED
**Related**: `context-accumulation`, `interactive-repl`

---

## ADDED Requirements

### Requirement: Session Creation and Persistence

The system SHALL provide session management for multi-turn agent conversations.

**Rationale**: Enable context preservation across multiple turns and support session resumption.

#### Scenario: Create New Session

**Given** a user wants to start a multi-turn conversation
**When** they invoke `aur spawn --interactive`
**Then** a new session SHALL be created with a unique ID
**And** the session SHALL be persisted to `~/.aurora/spawn/sessions/{id}.jsonl`
**And** the session metadata SHALL include: id, agent, created timestamp, status

#### Scenario: Save Session State

**Given** an active interactive session
**When** a user completes a turn (sends message, receives response)
**Then** the turn SHALL be appended to the session file in JSONL format
**And** the write SHALL be atomic (no partial writes)
**And** the file SHALL be readable by other processes

#### Scenario: Load Existing Session

**Given** a saved session exists at `~/.aurora/spawn/sessions/session-123.jsonl`
**When** a user runs `aur spawn --resume session-123`
**Then** the session state SHALL be loaded from disk
**And** all turns SHALL be restored in order
**And** the conversation context SHALL be populated with historical turns

---

### Requirement: Session Listing and Filtering

The system SHALL allow users to discover and filter existing sessions.

**Rationale**: Users need to find past conversations quickly.

#### Scenario: List All Sessions

**Given** multiple saved sessions exist
**When** a user runs `aur spawn --list-sessions`
**Then** all sessions SHALL be displayed in a table
**And** the table SHALL include: session_id, agent, turn_count, created_at, status
**And** sessions SHALL be sorted by most recent first

#### Scenario: Filter Sessions by Agent

**Given** sessions exist for multiple agents (qa-test, architect, etc.)
**When** a user runs `aur spawn --list-sessions --agent qa-test`
**Then** only sessions with agent "qa-test" SHALL be displayed

#### Scenario: Filter Sessions by Status

**Given** sessions exist with statuses: active, completed, interrupted
**When** a user runs `aur spawn --list-sessions --status active`
**Then** only sessions with status "active" SHALL be displayed

---

### Requirement: Session Cleanup

The system SHALL provide mechanisms to clean up old sessions.

**Rationale**: Prevent disk space accumulation from abandoned sessions.

#### Scenario: Delete Single Session

**Given** a session exists with id "session-123"
**When** a user runs `aur spawn --delete-session session-123`
**Then** the session file SHALL be deleted
**And** a confirmation message SHALL be displayed
**And** the session SHALL no longer appear in listings

#### Scenario: Clean Old Sessions

**Given** sessions exist with various ages
**When** a user runs `aur spawn --clean-sessions 30`
**Then** all sessions older than 30 days SHALL be deleted
**And** recent sessions (< 30 days) SHALL be preserved
**And** the number of deleted sessions SHALL be reported

#### Scenario: Automatic Cleanup

**Given** the config sets `spawner.interactive.session_expiry_days` to 30
**When** the CLI starts
**Then** sessions older than 30 days SHALL be automatically cleaned
**And** this SHALL happen in the background (non-blocking)

---

### Requirement: Session File Format

The system SHALL store sessions in JSONL format for efficient append operations.

**Rationale**: JSONL allows streaming writes and easy parsing.

#### Scenario: JSONL Format Structure

**Given** an interactive session with 2 turns
**When** the session is saved
**Then** the file SHALL contain one JSON object per line
**And** the first line SHALL be metadata: `{"type": "metadata", "session_id": ..., "agent": ..., "created_at": ...}`
**And** subsequent lines SHALL be turns: `{"type": "turn", "role": "user|assistant", "content": ..., "timestamp": ..., "tokens": ...}`

#### Scenario: Parse JSONL on Load

**Given** a valid JSONL session file
**When** the session is loaded
**Then** each line SHALL be parsed as JSON
**And** metadata SHALL be extracted from the first line
**And** turns SHALL be reconstructed from subsequent lines
**And** parsing errors SHALL result in clear error messages

#### Scenario: Handle Corrupted Session File

**Given** a session file with malformed JSON
**When** the session is loaded
**Then** an error message SHALL be displayed
**And** the user SHALL be prompted to delete or recover the file
**And** the CLI SHALL not crash

---

### Requirement: Concurrent Session Access

The system SHALL handle concurrent access to session files safely.

**Rationale**: Prevent data corruption from simultaneous writes.

#### Scenario: Write Lock During Save

**Given** a session is being saved
**When** another process attempts to write to the same session
**Then** the second write SHALL wait for the first to complete
**Or** the second write SHALL fail with a clear error message

#### Scenario: Read During Active Session

**Given** an active interactive session
**When** another process reads the session file (e.g., for listing)
**Then** the read SHALL succeed
**And** the read SHALL see the current state (up to last saved turn)

---

## Cross-References

- **Depends on**: None (foundational capability)
- **Enables**: `context-accumulation` (sessions provide storage), `interactive-repl` (sessions enable resume)
- **Related**: `cli-integration` (commands for session management)
