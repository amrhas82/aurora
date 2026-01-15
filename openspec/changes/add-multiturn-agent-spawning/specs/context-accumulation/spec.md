# Spec Delta: Context Accumulation

**Capability**: `context-accumulation`
**Type**: ADDED
**Related**: `session-management`, `interactive-repl`

---

## ADDED Requirements

### Requirement: Context Window Management

The system SHALL accumulate conversation turns and manage context window limits.

**Rationale**: Maintain conversation history while respecting model token limits.

#### Scenario: Add Turn to Context

**Given** an active interactive session
**When** a user sends a message
**Then** the message SHALL be added to the context as a "user" turn
**And** when the agent responds
**Then** the response SHALL be added as an "assistant" turn
**And** both turns SHALL be available for subsequent interactions

#### Scenario: Retrieve Full Context

**Given** a session with 5 accumulated turns
**When** the system needs to build a prompt for the next turn
**Then** all 5 turns SHALL be included in the prompt
**And** turns SHALL be ordered chronologically
**And** each turn SHALL be clearly marked with role (user/assistant)

#### Scenario: Clear Context

**Given** a session with accumulated context
**When** a user executes `/clear` command
**Then** all turns SHALL be removed from context
**And** the next prompt SHALL start fresh (no historical context)
**And** session metadata SHALL be preserved

---

### Requirement: Token Estimation

The system SHALL estimate token usage to prevent context window overflow.

**Rationale**: Provide early warning before hitting model limits.

#### Scenario: Estimate Token Count

**Given** a context with multiple turns
**When** the token count is requested
**Then** the system SHALL estimate tokens using 4-characters-per-token heuristic
**And** the estimate SHALL be within ±20% of actual token count
**And** the estimation SHALL complete in <10ms

#### Scenario: Track Running Token Total

**Given** an active session
**When** turns are added to context
**Then** the system SHALL maintain a running total of estimated tokens
**And** the total SHALL be updated incrementally (not recalculated from scratch)
**And** the total SHALL be accessible via `/stats` command

---

### Requirement: Context Trimming (Sliding Window)

The system SHALL automatically trim context when approaching token limits.

**Rationale**: Prevent context window overflow without user intervention.

#### Scenario: Trigger Trimming at 80% Threshold

**Given** a session with max_tokens set to 100,000
**When** the context reaches 80,000 estimated tokens
**Then** the system SHALL automatically trigger trimming
**And** a warning message SHALL be displayed to the user
**And** the trimming SHALL complete before the next turn

#### Scenario: Sliding Window Strategy

**Given** a context with 20 turns that exceeds 80% of max_tokens
**When** trimming is triggered
**Then** the system SHALL keep the first 2 turns (for context establishment)
**And** the system SHALL keep the last 10 turns (for recent context)
**And** turns 3-10 SHALL be discarded
**And** a marker SHALL be added indicating turns were trimmed

#### Scenario: Preserve Important Turns

**Given** a context being trimmed
**When** the sliding window is applied
**Then** the first turn (initial query) SHALL always be preserved
**And** the second turn (initial response) SHALL always be preserved
**And** the most recent turns SHALL be preserved
**And** metadata turns (e.g., system messages) SHALL be preserved

---

### Requirement: Context Window Warnings

The system SHALL warn users as they approach context limits.

**Rationale**: Give users opportunity to save or clear context before auto-trimming.

#### Scenario: Warn at 80% Capacity

**Given** a session approaching token limit
**When** context reaches 80% of max_tokens
**Then** a yellow warning SHALL be displayed: "Context at 80% capacity. Consider /clear or /save."
**And** the warning SHALL appear after the next agent response
**And** the warning SHALL not block interaction

#### Scenario: Warn at 90% Capacity

**Given** a session nearing token limit
**When** context reaches 90% of max_tokens
**Then** an orange warning SHALL be displayed: "Context at 90% capacity. Auto-trimming soon."
**And** the warning SHALL suggest immediate action
**And** the user SHALL have one more turn before auto-trim

#### Scenario: Notify After Auto-Trim

**Given** context was automatically trimmed
**When** the next prompt is displayed
**Then** an info message SHALL be shown: "Context trimmed. Kept first 2 and last 10 turns."
**And** the message SHALL indicate what was preserved
**And** the user SHALL be able to continue normally

---

### Requirement: Context Portability

The system SHALL support exporting and importing context.

**Rationale**: Allow users to transfer context between sessions or tools.

#### Scenario: Export Context to JSON

**Given** a session with accumulated context
**When** a user executes `/export context.json`
**Then** all turns SHALL be exported to a JSON file
**And** the export SHALL include metadata (session_id, agent, timestamps)
**And** the export SHALL be in a standard format (JSON array of turn objects)

#### Scenario: Import Context from JSON

**Given** a valid context export file
**When** a user executes `/import context.json`
**Then** the turns SHALL be loaded into the current session
**And** the context accumulator SHALL be populated
**And** subsequent interactions SHALL include the imported context

---

## Cross-References

- **Depends on**: `session-management` (for persistence)
- **Enables**: `interactive-repl` (provides context for prompts)
- **Related**: None
