# Design: Interactive Multi-Turn Mode for aur spawn

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    aur spawn CLI                                │
│                                                                 │
│  1. Parse --interactive flag                                    │
│  2. If interactive: → InteractiveREPL                           │
│     Else: → TaskExecutor (existing)                             │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              InteractiveREPL (NEW)                              │
│                                                                 │
│  - display_welcome()                                            │
│  - run_loop() → prompt → CommandParser → handle_command()      │
│  - maintain ConversationContext                                 │
│  - stream responses from agent                                  │
└─────────────────────────────────────────────────────────────────┘
           │                           │
           ▼                           ▼
┌────────────────────┐       ┌──────────────────────────┐
│   CommandParser    │       │   ConversationContext    │
│                    │       │                          │
│  - parse("/cmd")   │       │  - history: list[Turn]   │
│  - Commands:       │       │  - agent_id: str         │
│    /help           │       │  - add_turn()            │
│    /exit           │       │  - to_prompt_context()   │
│    /save <file>    │       │  - trim_to_window()      │
│    /history        │       │  - serialize()           │
│    /clear          │       └──────────────────────────┘
│    /agent <id>     │
│    /stats          │
└────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SessionManager (NEW)                          │
│                                                                 │
│  - save_session(context, path)                                  │
│  - load_session(session_id) → ConversationContext               │
│  - list_sessions() → list[SessionInfo]                          │
│  - cleanup_old_sessions(days)                                   │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                aurora-spawner (EXISTING)                        │
│                                                                 │
│  - spawn(task, agent_id, context) → SpawnResult                 │
│  - Passes conversation history as context                       │
└─────────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. InteractiveREPL

**Location**: `packages/cli/src/aurora_cli/interactive/repl.py`

**Responsibilities**:
- Display welcome banner and instructions
- Run REPL loop: prompt → parse → execute → display
- Maintain conversation context
- Stream agent responses with rich formatting
- Handle graceful shutdown

**Interface**:
```python
from aurora_cli.interactive.context import ConversationContext
from aurora_cli.interactive.commands import CommandParser

class InteractiveREPL:
    """REPL interface for interactive agent conversations."""

    def __init__(
        self,
        agent_id: str | None = None,
        config: Config | None = None,
    ):
        self.agent_id = agent_id
        self.config = config or load_config()
        self.context = ConversationContext(agent_id=agent_id)
        self.command_parser = CommandParser()
        self.session_manager = SessionManager(config)

    def display_welcome(self) -> None:
        """Display welcome banner and instructions."""
        console.print()
        console.print("[bold cyan]Aurora Spawn Interactive Mode[/]")
        if self.agent_id:
            console.print(f"Agent: [green]@{self.agent_id}[/]")
        console.print("Type [yellow]/help[/] for commands, [yellow]/exit[/] to quit")
        console.print()

    async def run_loop(self) -> None:
        """Main REPL loop."""
        self.display_welcome()

        while True:
            try:
                # Prompt for input
                user_input = await self._prompt_user()

                if not user_input.strip():
                    continue

                # Check for command
                if user_input.startswith("/"):
                    should_continue = await self._handle_command(user_input)
                    if not should_continue:
                        break
                    continue

                # Regular query - spawn agent
                await self._handle_query(user_input)

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type /exit to quit.[/]")
                continue
            except EOFError:
                break

        # Save session on exit
        await self._cleanup()

    async def _prompt_user(self) -> str:
        """Prompt user for input with custom prompt."""
        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style

        style = Style.from_dict({
            'prompt': '#00aa00 bold',
        })

        session = PromptSession(style=style)
        return await session.prompt_async("> ")

    async def _handle_query(self, query: str) -> None:
        """Handle regular query by spawning agent."""
        # Add user turn to context
        self.context.add_turn(role="user", content=query)

        # Build spawn task with conversation context
        task = SpawnTask(
            prompt=query,
            agent=self.agent_id,
            timeout=300,
        )

        # Get conversation history as context
        history_context = self.context.to_prompt_context()

        # Spawn agent with streaming
        try:
            with console.status("[cyan]Agent thinking...[/]"):
                result = await spawn(
                    task=task,
                    context=history_context,  # Pass conversation history
                )

            if result.success:
                # Add assistant turn to context
                self.context.add_turn(role="assistant", content=result.output)

                # Display response with syntax highlighting
                console.print()
                console.print(Markdown(result.output))
                console.print()
            else:
                console.print(f"[red]Error:[/] {result.error}")

        except Exception as e:
            console.print(f"[red]Error:[/] {e}")

    async def _handle_command(self, command: str) -> bool:
        """Handle slash command. Returns False if should exit."""
        cmd = self.command_parser.parse(command)

        if cmd.name == "exit":
            return False
        elif cmd.name == "help":
            self._show_help()
        elif cmd.name == "save":
            await self._save_conversation(cmd.args[0] if cmd.args else None)
        elif cmd.name == "history":
            self._show_history()
        elif cmd.name == "clear":
            self.context.clear()
            console.print("[green]Context cleared.[/]")
        elif cmd.name == "agent":
            if cmd.args:
                self.agent_id = cmd.args[0]
                self.context = ConversationContext(agent_id=self.agent_id)
                console.print(f"[green]Switched to agent:[/] @{self.agent_id}")
            else:
                console.print("[red]Usage: /agent <agent-id>[/]")
        elif cmd.name == "stats":
            self._show_stats()
        else:
            console.print(f"[red]Unknown command:[/] {cmd.name}")

        return True

    def _show_help(self) -> None:
        """Display help text."""
        help_text = """
[bold]Available Commands:[/]

  [yellow]/help[/]             Show this help message
  [yellow]/exit[/]             Exit interactive mode
  [yellow]/save <file>[/]      Save conversation to file
  [yellow]/history[/]          Show conversation history
  [yellow]/clear[/]            Clear conversation context
  [yellow]/agent <id>[/]       Switch to different agent
  [yellow]/stats[/]            Show session statistics
        """
        console.print(help_text)

    async def _save_conversation(self, filepath: str | None) -> None:
        """Save conversation to file."""
        if not filepath:
            # Auto-generate filename
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            agent = self.agent_id or "direct"
            filepath = f"conversation-{agent}-{timestamp}.md"

        # Export as markdown
        content = self.context.to_markdown()
        Path(filepath).write_text(content)
        console.print(f"[green]Saved conversation to:[/] {filepath}")

    def _show_history(self) -> None:
        """Display conversation history."""
        if not self.context.history:
            console.print("[yellow]No conversation history.[/]")
            return

        console.print("\n[bold]Conversation History:[/]\n")
        for i, turn in enumerate(self.context.history, 1):
            role_color = "green" if turn.role == "user" else "cyan"
            console.print(f"[{role_color}]{turn.role}:[/{role_color}]")
            console.print(turn.content[:100] + "..." if len(turn.content) > 100 else turn.content)
            console.print()

    def _show_stats(self) -> None:
        """Display session statistics."""
        stats = self.context.get_stats()
        console.print("\n[bold]Session Statistics:[/]\n")
        console.print(f"  Turns: {stats['turns']}")
        console.print(f"  Agent: @{self.agent_id or 'direct'}")
        console.print(f"  Tokens (est): {stats['estimated_tokens']}")
        console.print()

    async def _cleanup(self) -> None:
        """Cleanup and save session on exit."""
        # Save session to disk
        session_id = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        session_path = self.session_manager.save_session(self.context, session_id)

        console.print(f"\n[green]Session saved to:[/] {session_path}")
        console.print("[cyan]Goodbye![/]")
```

### 2. ConversationContext

**Location**: `packages/cli/src/aurora_cli/interactive/context.py`

**Responsibilities**:
- Track conversation history (user/assistant turns)
- Manage context window (trim old turns)
- Serialize/deserialize for persistence
- Generate prompt context for spawning

**Interface**:
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Turn:
    """Single conversation turn."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    tokens: int | None = None  # Estimated token count

class ConversationContext:
    """Manages conversation state and history."""

    def __init__(
        self,
        agent_id: str | None = None,
        max_turns: int = 20,
        max_tokens: int = 100000,
    ):
        self.agent_id = agent_id
        self.history: list[Turn] = []
        self.max_turns = max_turns
        self.max_tokens = max_tokens

    def add_turn(self, role: str, content: str) -> None:
        """Add turn to history and trim if needed."""
        turn = Turn(
            role=role,
            content=content,
            timestamp=datetime.now(),
            tokens=self._estimate_tokens(content),
        )
        self.history.append(turn)

        # Trim if exceeded limits
        self._trim_if_needed()

    def _trim_if_needed(self) -> None:
        """Trim history to stay within limits."""
        # Keep first 2 turns (context) + last N turns (recent)
        if len(self.history) > self.max_turns:
            keep_first = 2
            keep_last = self.max_turns - keep_first
            self.history = self.history[:keep_first] + self.history[-keep_last:]

    def to_prompt_context(self) -> str:
        """Generate prompt context string for agent spawning."""
        if not self.history:
            return ""

        lines = ["Previous conversation:"]
        for turn in self.history:
            lines.append(f"{turn.role}: {turn.content}")

        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Export conversation as Markdown."""
        lines = [f"# Conversation with @{self.agent_id or 'Aurora'}", ""]

        for turn in self.history:
            if turn.role == "user":
                lines.append(f"## User")
            else:
                lines.append(f"## Agent")

            lines.append(turn.content)
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "history": [
                {
                    "role": t.role,
                    "content": t.content,
                    "timestamp": t.timestamp.isoformat(),
                    "tokens": t.tokens,
                }
                for t in self.history
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationContext":
        """Deserialize from dictionary."""
        ctx = cls(agent_id=data.get("agent_id"))
        for turn_data in data.get("history", []):
            ctx.history.append(
                Turn(
                    role=turn_data["role"],
                    content=turn_data["content"],
                    timestamp=datetime.fromisoformat(turn_data["timestamp"]),
                    tokens=turn_data.get("tokens"),
                )
            )
        return ctx

    def clear(self) -> None:
        """Clear all history."""
        self.history.clear()

    def get_stats(self) -> dict:
        """Get conversation statistics."""
        total_tokens = sum(t.tokens or 0 for t in self.history)
        return {
            "turns": len(self.history),
            "estimated_tokens": total_tokens,
        }

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        return len(text) // 4
```

### 3. CommandParser

**Location**: `packages/cli/src/aurora_cli/interactive/commands.py`

**Responsibilities**:
- Parse `/command arg1 arg2` syntax
- Validate command names and arguments
- Provide command metadata (help text, arg count)

**Interface**:
```python
from dataclasses import dataclass

@dataclass
class Command:
    """Parsed command."""
    name: str
    args: list[str]

class CommandParser:
    """Parse and validate slash commands."""

    COMMANDS = {
        "help": {"args": 0, "desc": "Show help message"},
        "exit": {"args": 0, "desc": "Exit interactive mode"},
        "save": {"args": "0-1", "desc": "Save conversation to file"},
        "history": {"args": 0, "desc": "Show conversation history"},
        "clear": {"args": 0, "desc": "Clear conversation context"},
        "agent": {"args": 1, "desc": "Switch to different agent"},
        "stats": {"args": 0, "desc": "Show session statistics"},
    }

    def parse(self, text: str) -> Command:
        """Parse command string."""
        # Remove leading /
        text = text.lstrip("/")

        # Split into name and args
        parts = text.split(maxsplit=1)
        name = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        return Command(name=name, args=args)

    def validate(self, command: Command) -> tuple[bool, str | None]:
        """Validate command. Returns (valid, error_message)."""
        if command.name not in self.COMMANDS:
            return False, f"Unknown command: {command.name}"

        cmd_info = self.COMMANDS[command.name]
        expected_args = cmd_info["args"]

        if isinstance(expected_args, int):
            if len(command.args) != expected_args:
                return False, f"Expected {expected_args} arguments, got {len(command.args)}"
        elif isinstance(expected_args, str) and "-" in expected_args:
            min_args, max_args = map(int, expected_args.split("-"))
            if not (min_args <= len(command.args) <= max_args):
                return False, f"Expected {min_args}-{max_args} arguments, got {len(command.args)}"

        return True, None
```

### 4. SessionManager

**Location**: `packages/cli/src/aurora_cli/interactive/session.py`

**Responsibilities**:
- Save conversation context to disk
- Load previous sessions
- List available sessions
- Cleanup old sessions

**Interface**:
```python
import json
from pathlib import Path

class SessionManager:
    """Manage interactive session persistence."""

    def __init__(self, config: Config):
        self.config = config
        self.sessions_dir = Path.home() / ".aurora" / "spawn" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, context: ConversationContext, session_id: str) -> Path:
        """Save session to disk."""
        session_path = self.sessions_dir / f"{session_id}.json"

        data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "context": context.to_dict(),
        }

        session_path.write_text(json.dumps(data, indent=2))
        return session_path

    def load_session(self, session_id: str) -> ConversationContext | None:
        """Load session from disk."""
        session_path = self.sessions_dir / f"{session_id}.json"

        if not session_path.exists():
            return None

        data = json.loads(session_path.read_text())
        return ConversationContext.from_dict(data["context"])

    def list_sessions(self) -> list[dict]:
        """List available sessions."""
        sessions = []
        for path in self.sessions_dir.glob("*.json"):
            data = json.loads(path.read_text())
            sessions.append({
                "session_id": data["session_id"],
                "created_at": data["created_at"],
                "agent_id": data["context"]["agent_id"],
                "turns": len(data["context"]["history"]),
            })
        return sorted(sessions, key=lambda s: s["created_at"], reverse=True)

    def cleanup_old_sessions(self, days: int) -> int:
        """Delete sessions older than N days. Returns count deleted."""
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0

        for path in self.sessions_dir.glob("*.json"):
            data = json.loads(path.read_text())
            created = datetime.fromisoformat(data["created_at"])

            if created < cutoff:
                path.unlink()
                deleted += 1

        return deleted
```

## CLI Integration

**File**: `packages/cli/src/aurora_cli/commands/spawn.py`

Add `--interactive` flag and entry point:

```python
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Enter interactive conversation mode with agent",
)
def spawn_command(
    task_file: Path,
    parallel: bool,
    sequential: bool,
    verbose: bool,
    dry_run: bool,
    interactive: bool,  # NEW
    agent: str | None,  # NEW - for --agent flag
    ...
) -> None:
    """Execute tasks or enter interactive mode."""

    # NEW: Interactive mode
    if interactive:
        from aurora_cli.interactive.repl import InteractiveREPL

        repl = InteractiveREPL(agent_id=agent)
        asyncio.run(repl.run_loop())
        return

    # Existing task-based logic
    ...
```

## Data Flow

### Interactive Query Flow

```
1. User enters: "Analyze test coverage"

2. InteractiveREPL.run_loop()
   → _handle_query("Analyze test coverage")
   → context.add_turn(role="user", content="...")

3. Build SpawnTask with conversation history
   → history_context = context.to_prompt_context()
   → spawn(task, context=history_context)

4. Agent receives:
   "Previous conversation:
    user: [previous query]
    assistant: [previous response]
    user: Analyze test coverage"

5. Agent responds with full context awareness

6. InteractiveREPL._handle_query()
   → context.add_turn(role="assistant", content=response)
   → Display response

7. Loop continues...
```

## Configuration

**Global Config** (`~/.aurora/config.json`):
```json
{
  "spawn": {
    "interactive": {
      "max_turns": 20,
      "max_tokens": 100000,
      "auto_save": true,
      "sessions_dir": "~/.aurora/spawn/sessions"
    }
  }
}
```

**Environment Variables**:
- `AURORA_SPAWN_INTERACTIVE_MAX_TURNS` - Override max turns
- `AURORA_SPAWN_INTERACTIVE_MAX_TOKENS` - Override max tokens

## Performance Considerations

**Context Window Management**:
- Keep first 2 turns (initial context)
- Keep last 18 turns (recent conversation)
- Trim middle turns to stay under limits

**Token Estimation**:
- Rough estimate: 1 token ≈ 4 characters
- Track cumulative tokens
- Warn when approaching model limits

**Session Storage**:
- JSON format for sessions (~1-10KB per session)
- Cleanup old sessions (default: 30 days)
- Target: <100MB total session storage

## Testing Strategy

**Unit Tests**:
- `test_interactive_repl.py` - REPL loop logic
- `test_conversation_context.py` - Context management
- `test_command_parser.py` - Command parsing
- `test_session_manager.py` - Session persistence

**Integration Tests**:
- `test_interactive_e2e.py` - Full interactive session
- Mock LLM responses for deterministic testing
- Test context accumulation across turns
- Test session save/load

**Manual Testing**:
- Interactive session with real agent
- Long conversations (20+ turns)
- Command execution (all `/` commands)
- Graceful shutdown and session restoration
