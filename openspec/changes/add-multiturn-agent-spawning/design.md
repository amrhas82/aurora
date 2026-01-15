# Design: Multi-Turn Agent Spawning

## Architecture Overview

Multi-turn spawning extends the existing `aur spawn` architecture with session management and context accumulation. The design maintains backward compatibility while adding three new components:

```
┌─────────────────────────────────────────────────────────────┐
│                     aur spawn (CLI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Task Mode    │  │ Interactive  │  │ Resume Mode  │     │
│  │ (existing)   │  │ Mode (new)   │  │ (new)        │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            ↓                                 │
│              ┌─────────────────────────────┐                │
│              │   Spawn Orchestrator        │                │
│              │  (packages/spawner)         │                │
│              └──────────────┬──────────────┘                │
│                             │                                │
│         ┌───────────────────┼───────────────────┐           │
│         ↓                   ↓                   ↓           │
│  ┌──────────────┐  ┌────────────────┐  ┌───────────────┐  │
│  │ Session      │  │ Context        │  │ Interactive   │  │
│  │ Manager      │  │ Accumulator    │  │ REPL          │  │
│  │ (new)        │  │ (new)          │  │ (new)         │  │
│  └──────────────┘  └────────────────┘  └───────────────┘  │
│         │                   │                   │           │
│         └───────────────────┴───────────────────┘           │
│                             ↓                                │
│              ┌─────────────────────────────┐                │
│              │   Agent Subprocess          │                │
│              │   (existing spawn_parallel) │                │
│              └─────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Session Manager (`packages/spawner/session.py`)

**Responsibility**: Manage session lifecycle, persistence, and state.

```python
@dataclass
class SessionState:
    """Persisted state for multi-turn sessions."""
    session_id: str
    agent: str | None
    context: list[Turn]  # Accumulated conversation
    metadata: dict[str, Any]  # timestamps, token counts, etc.
    status: Literal["active", "completed", "interrupted"]

@dataclass
class Turn:
    """Single turn in conversation."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    tokens: int | None

class SessionManager:
    """Manages session persistence and lifecycle."""

    def create_session(
        self,
        agent: str | None = None,
        session_id: str | None = None
    ) -> SessionState:
        """Create new session with unique ID."""

    def save_session(self, session: SessionState) -> None:
        """Persist session to ~/.aurora/spawn/sessions/{id}.jsonl"""

    def load_session(self, session_id: str) -> SessionState:
        """Load session from disk."""

    def list_sessions(
        self,
        agent: str | None = None,
        status: str | None = None
    ) -> list[SessionState]:
        """List all sessions with optional filtering."""

    def delete_session(self, session_id: str) -> None:
        """Delete session and associated files."""

    def clean_old_sessions(self, days: int = 30) -> int:
        """Remove sessions older than N days."""
```

**Storage Format**: JSONL for append-only writes
```jsonl
{"type": "metadata", "session_id": "spawn-123", "agent": "qa-test", "created_at": "2026-01-14T10:00:00Z"}
{"type": "turn", "role": "user", "content": "Analyze coverage", "timestamp": "2026-01-14T10:00:05Z"}
{"type": "turn", "role": "assistant", "content": "Coverage is 87%...", "timestamp": "2026-01-14T10:00:12Z", "tokens": 245}
{"type": "turn", "role": "user", "content": "What's missing?", "timestamp": "2026-01-14T10:01:00Z"}
```

### 2. Context Accumulator (`packages/spawner/context.py`)

**Responsibility**: Accumulate conversation history and manage context window.

```python
class ContextAccumulator:
    """Manages conversation context with windowing."""

    def __init__(
        self,
        max_tokens: int = 100000,  # Claude Sonnet window
        trim_strategy: Literal["sliding", "summary"] = "sliding"
    ):
        self.max_tokens = max_tokens
        self.trim_strategy = trim_strategy
        self.turns: list[Turn] = []

    def add_turn(self, turn: Turn) -> None:
        """Add turn and trim if needed."""
        self.turns.append(turn)
        if self._estimate_tokens() > self.max_tokens * 0.8:
            self._trim_context()

    def get_context(self) -> list[Turn]:
        """Return current context for prompt."""
        return self.turns

    def clear(self) -> None:
        """Reset context."""
        self.turns = []

    def _estimate_tokens(self) -> int:
        """Rough token estimate (4 chars = 1 token)."""
        total_chars = sum(len(t.content) for t in self.turns)
        return total_chars // 4

    def _trim_context(self) -> None:
        """Trim using configured strategy."""
        if self.trim_strategy == "sliding":
            # Keep first 2 turns + last 10 turns
            if len(self.turns) > 12:
                self.turns = self.turns[:2] + self.turns[-10:]
        elif self.trim_strategy == "summary":
            # Future: LLM summarization of middle turns
            raise NotImplementedError("Summary strategy not yet implemented")
```

**Trimming Strategies**:

1. **Sliding Window** (v1):
   - Keep first 2 turns (context establishment)
   - Keep last 10 turns (recent context)
   - Drop middle turns when > 80% window

2. **Summarization** (v2, future):
   - Summarize middle turns into single context block
   - Preserve first/last turns verbatim

### 3. Interactive REPL (`packages/spawner/interactive.py`)

**Responsibility**: Handle user interaction loop, commands, and display.

```python
class InteractiveREPL:
    """REPL controller for interactive spawn sessions."""

    def __init__(
        self,
        agent: str | None = None,
        session_id: str | None = None
    ):
        self.agent = agent
        self.session = SessionManager().create_session(agent, session_id)
        self.context = ContextAccumulator()
        self.running = True

    async def run(self) -> None:
        """Main REPL loop."""
        self._show_banner()

        while self.running:
            try:
                user_input = self._prompt()

                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                else:
                    await self._handle_user_message(user_input)

            except KeyboardInterrupt:
                self._handle_interrupt()
            except Exception as e:
                self._handle_error(e)

        self._cleanup()

    def _prompt(self) -> str:
        """Display prompt and get user input."""
        agent_name = f"@{self.agent}" if self.agent else "spawn"
        return input(f"\n{agent_name}> ").strip()

    async def _handle_user_message(self, message: str) -> None:
        """Process user message and get agent response."""
        # Add user turn to context
        user_turn = Turn(
            role="user",
            content=message,
            timestamp=datetime.now(),
            tokens=None
        )
        self.context.add_turn(user_turn)

        # Build prompt with accumulated context
        prompt = self._build_prompt()

        # Spawn agent with context
        task = SpawnTask(prompt=prompt, agent=self.agent, timeout=300)
        result = await spawn(task)

        # Add assistant turn to context
        assistant_turn = Turn(
            role="assistant",
            content=result.output,
            timestamp=datetime.now(),
            tokens=self._estimate_tokens(result.output)
        )
        self.context.add_turn(assistant_turn)

        # Display response
        console.print(result.output)

        # Save session
        self.session.context = self.context.get_context()
        SessionManager().save_session(self.session)

    async def _handle_command(self, command: str) -> None:
        """Execute session command."""
        cmd_parts = command[1:].split(maxsplit=1)
        cmd_name = cmd_parts[0]
        cmd_args = cmd_parts[1] if len(cmd_parts) > 1 else ""

        handlers = {
            "help": self._cmd_help,
            "exit": self._cmd_exit,
            "save": self._cmd_save,
            "history": self._cmd_history,
            "clear": self._cmd_clear,
            "stats": self._cmd_stats,
            "agent": self._cmd_agent,
        }

        handler = handlers.get(cmd_name)
        if handler:
            await handler(cmd_args)
        else:
            console.print(f"[red]Unknown command: {command}[/]")
            console.print("[dim]Type /help for available commands[/]")

    def _build_prompt(self) -> str:
        """Build prompt with conversation context."""
        turns = self.context.get_context()

        prompt_parts = []
        for turn in turns:
            prefix = "User:" if turn.role == "user" else "Assistant:"
            prompt_parts.append(f"{prefix} {turn.content}")

        return "\n\n".join(prompt_parts)

    # Command implementations
    async def _cmd_help(self, args: str) -> None:
        """Show available commands."""
        help_text = """
Available commands:
  /help              Show this help message
  /exit              Exit interactive mode
  /save <file>       Save conversation to markdown file
  /history [N]       Show last N turns (default: all)
  /clear             Clear conversation context
  /stats             Show token usage and session stats
  /agent <name>      Switch to different agent (starts fresh)
"""
        console.print(help_text)

    async def _cmd_exit(self, args: str) -> None:
        """Exit REPL."""
        self.running = False
        session_path = f"~/.aurora/spawn/sessions/{self.session.session_id}.jsonl"
        console.print(f"[cyan]Session saved: {session_path}[/]")

    async def _cmd_save(self, args: str) -> None:
        """Export conversation to markdown."""
        if not args:
            console.print("[red]Usage: /save <filename>[/]")
            return

        output_path = Path(args)
        turns = self.context.get_context()

        markdown = []
        markdown.append(f"# Conversation with {self.agent or 'spawn'}\n")
        markdown.append(f"Session: {self.session.session_id}\n")
        markdown.append(f"Date: {datetime.now().isoformat()}\n\n")

        for turn in turns:
            role = "**User**" if turn.role == "user" else "**Assistant**"
            markdown.append(f"{role}:\n{turn.content}\n\n")

        output_path.write_text("\n".join(markdown))
        console.print(f"[green]Saved to {output_path}[/]")

    async def _cmd_history(self, args: str) -> None:
        """Show conversation history."""
        try:
            n = int(args) if args else None
        except ValueError:
            console.print("[red]Invalid number[/]")
            return

        turns = self.context.get_context()
        if n:
            turns = turns[-n:]

        for i, turn in enumerate(turns, 1):
            role = "User" if turn.role == "user" else "Assistant"
            console.print(f"[bold]{i}. {role}:[/] {turn.content[:100]}...")

    async def _cmd_clear(self, args: str) -> None:
        """Clear context."""
        self.context.clear()
        console.print("[yellow]Context cleared[/]")

    async def _cmd_stats(self, args: str) -> None:
        """Show session statistics."""
        turns = self.context.get_context()
        total_tokens = sum(t.tokens or 0 for t in turns)

        console.print(f"[cyan]Session Statistics[/]")
        console.print(f"  Session ID: {self.session.session_id}")
        console.print(f"  Agent: {self.agent or 'default'}")
        console.print(f"  Turns: {len(turns)}")
        console.print(f"  Tokens: ~{total_tokens}")
        console.print(f"  Context: {self.context._estimate_tokens()}/{self.context.max_tokens}")

    async def _cmd_agent(self, args: str) -> None:
        """Switch agent (starts fresh session)."""
        if not args:
            console.print("[red]Usage: /agent <name>[/]")
            return

        console.print(f"[yellow]Starting fresh session with @{args}[/]")
        self.agent = args
        self.session = SessionManager().create_session(args)
        self.context.clear()
```

### 4. CLI Integration (`packages/cli/commands/spawn.py`)

**Changes**:

```python
@click.command(name="spawn")
@click.argument("task_file", ...)
# ... existing options ...
@click.option(
    "--interactive", "-i",
    is_flag=True,
    help="Enter interactive multi-turn mode"
)
@click.option(
    "--agent",
    type=str,
    help="Agent to spawn (for interactive mode)"
)
@click.option(
    "--session",
    type=str,
    help="Session ID for resumable interactive sessions"
)
@click.option(
    "--resume",
    type=str,
    help="Resume existing session by ID"
)
def spawn_command(
    task_file: Path,
    interactive: bool,
    agent: str | None,
    session: str | None,
    resume: str | None,
    # ... existing params ...
) -> None:
    """Execute tasks with optional multi-turn mode."""

    # Handle interactive mode
    if interactive:
        from aurora_spawner.interactive import InteractiveREPL

        repl = InteractiveREPL(agent=agent, session_id=session)
        asyncio.run(repl.run())
        return

    # Handle resume
    if resume:
        from aurora_spawner.session import SessionManager

        session_state = SessionManager().load_session(resume)
        # Continue from saved state
        ...

    # Existing task-based logic unchanged
    tasks = load_tasks(task_file)
    ...
```

## Data Flow

### Interactive Mode Flow

```
User starts interactive session
         ↓
CLI creates SessionManager + ContextAccumulator + InteractiveREPL
         ↓
REPL displays banner and prompt
         ↓
┌─────────────────────────────────────────────┐
│  LOOP: User inputs message                  │
│         ↓                                   │
│  Add user turn to ContextAccumulator        │
│         ↓                                   │
│  Build prompt from accumulated context      │
│         ↓                                   │
│  Spawn agent subprocess with full context   │
│         ↓                                   │
│  Receive agent response                     │
│         ↓                                   │
│  Add assistant turn to ContextAccumulator   │
│         ↓                                   │
│  Save session to disk (JSONL append)        │
│         ↓                                   │
│  Display response to user                   │
│         ↓                                   │
│  Check context window (trim if needed)      │
│         ↓                                   │
│  Return to prompt                           │
└─────────────────────────────────────────────┘
         ↓
User types /exit
         ↓
SessionManager marks session complete
         ↓
Display session location
         ↓
Exit
```

### Session Resume Flow

```
User runs: aur spawn --resume session-123
         ↓
SessionManager loads session-123.jsonl
         ↓
Parse JSONL into SessionState
         ↓
Restore ContextAccumulator with turns
         ↓
Enter interactive REPL with restored state
         ↓
Continue as normal interactive session
```

## File Structure

```
packages/spawner/src/aurora_spawner/
├── __init__.py
├── spawner.py           # Existing spawn logic
├── models.py            # Existing models
├── session.py           # NEW: Session management
├── context.py           # NEW: Context accumulation
└── interactive.py       # NEW: REPL controller

packages/cli/src/aurora_cli/commands/
├── spawn.py             # MODIFIED: Add interactive/resume options
└── spawn_helpers.py     # MODIFIED: Add session utilities

~/.aurora/spawn/
└── sessions/
    ├── 2026-01-14-qa-test-123456.jsonl
    ├── 2026-01-14-arch-review-789012.jsonl
    └── ...
```

## Configuration

Add to `~/.aurora/config.json`:

```json
{
  "spawner": {
    "interactive": {
      "max_tokens": 100000,
      "trim_strategy": "sliding",
      "auto_save_turns": 5,
      "session_expiry_days": 30
    }
  }
}
```

## Error Handling

| Error Scenario | Handling Strategy |
|----------------|-------------------|
| **Session file corrupted** | Validate on load, fall back to empty session, warn user |
| **Agent not found** | Prompt for valid agent, show available agents |
| **Context window exceeded** | Auto-trim, warn user, suggest /clear |
| **Network failure during spawn** | Retry with exponential backoff, save partial response |
| **Keyboard interrupt (Ctrl+C)** | Save current state, return to prompt gracefully |
| **Invalid command** | Show error + help text |
| **Session not found (resume)** | List available sessions, prompt for valid ID |

## Testing Strategy

### Unit Tests
- `test_session_manager.py`: CRUD operations, JSONL parsing
- `test_context_accumulator.py`: Windowing, trimming, token estimation
- `test_interactive_repl.py`: Command parsing, state management

### Integration Tests
- `test_interactive_flow.py`: Full REPL session lifecycle
- `test_session_persistence.py`: Save/load/resume workflows
- `test_context_preservation.py`: Multi-turn context retention

### E2E Tests
- `test_spawn_interactive_e2e.py`: Real agent spawning in interactive mode
- `test_spawn_resume_e2e.py`: Resume functionality with real sessions

## Performance Considerations

1. **Session I/O**: Use async file writes to avoid blocking REPL
2. **Context estimation**: Cache token counts, recalculate only on add
3. **History display**: Lazy load, paginate for large histories
4. **Cleanup**: Background task for old session deletion

## Security

- **Session files**: Store in user home directory only (`~/.aurora/`)
- **No secret storage**: Never persist API keys or tokens
- **Input validation**: Sanitize user input before spawn
- **Path traversal**: Validate file paths for `/save` command

## Migration

No migration needed - this is a purely additive change. Existing `aur spawn` usage remains unchanged.

## Future Enhancements

1. **Context summarization**: LLM-based trimming strategy
2. **Agent switching**: `/switch <agent>` mid-session
3. **Session branching**: Fork conversation at specific turn
4. **Streaming responses**: Token-by-token display
5. **Multi-modal input**: File attachments, images
6. **Collaborative sessions**: Shared sessions across users
