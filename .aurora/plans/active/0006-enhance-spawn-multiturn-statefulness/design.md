# Design: Spawn Multi-Turn Statefulness

## Current Architecture

```
aur spawn tasks.md
      │
      ▼
┌──────────────────┐
│ load_tasks()     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐      ┌─────────────────────┐
│ _execute_*()     │──────│ CheckpointManager   │
│ parallel/seq     │      │ (task state only)   │
└────────┬─────────┘      └─────────────────────┘
         │
         ▼
┌──────────────────┐
│ spawn_parallel() │
│ or spawn_seq()   │
└────────┬─────────┘
         │ context = output + "\n"  ← naive concatenation
         ▼
┌──────────────────┐
│ subprocess exec  │
└──────────────────┘
```

**Problem**: Context is raw string concat, no structure, no trimming, no persistence.

---

## Proposed Architecture

```
aur spawn tasks.md [--resume <id>]
      │
      ▼
┌──────────────────┐
│ load_tasks()     │
│ OR load_session()│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐      ┌─────────────────────────┐
│ SpawnOrchestrator│──────│ SessionState            │
│                  │      │ ├─ tasks: TaskState[]   │
│                  │      │ └─ conversation: Turn[] │
└────────┬─────────┘      └─────────────────────────┘
         │                           │
         │    ┌──────────────────────┘
         ▼    ▼
┌──────────────────┐
│ ContextAccumulator│
│ ├─ add_turn()     │
│ ├─ get_prompt()   │
│ └─ trim_if_needed()│
└────────┬─────────┘
         │ structured prompt with context
         ▼
┌──────────────────┐
│ spawn()          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ subprocess exec  │
└──────────────────┘
         │
         ▼
┌──────────────────┐
│ SessionManager   │
│ .save_checkpoint()│ ← auto-save after each turn
└──────────────────┘
```

---

## Component Design

### 1. ContextAccumulator

**Purpose**: Manage conversation history with windowing.

```python
@dataclass
class Turn:
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class ContextAccumulator:
    def __init__(
        self,
        max_tokens: int = 100_000,  # Claude Sonnet
        trim_strategy: str = "sliding",
    ):
        self.turns: list[Turn] = []
        self.max_tokens = max_tokens
        self.trim_strategy = trim_strategy

    def add_turn(self, role: str, content: str) -> Turn:
        """Add turn, auto-trim if near limit."""
        turn = Turn(
            role=role,
            content=content,
            timestamp=datetime.now(),
            tokens=self._estimate_tokens(content),
        )
        self.turns.append(turn)

        if self._total_tokens() > self.max_tokens * 0.8:
            self._trim()

        return turn

    def get_prompt(self) -> str:
        """Build prompt with conversation history."""
        parts = []
        for turn in self.turns:
            prefix = {"user": "User", "assistant": "Assistant", "system": "System"}[turn.role]
            parts.append(f"[{prefix}]\n{turn.content}")
        return "\n\n".join(parts)

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate: 4 chars ≈ 1 token."""
        return len(text) // 4

    def _total_tokens(self) -> int:
        return sum(t.tokens or 0 for t in self.turns)

    def _trim(self) -> None:
        """Sliding window: keep first 2 + last 10 turns."""
        if len(self.turns) > 12:
            self.turns = self.turns[:2] + self.turns[-10:]

    def clear(self) -> None:
        self.turns = []

    def to_dict(self) -> list[dict]:
        """Serialize for checkpoint."""
        return [asdict(t) for t in self.turns]

    @classmethod
    def from_dict(cls, data: list[dict]) -> "ContextAccumulator":
        """Deserialize from checkpoint."""
        acc = cls()
        for d in data:
            acc.turns.append(Turn(**d))
        return acc
```

### 2. Extended CheckpointState

**Change**: Add conversation field to existing checkpoint.

```python
@dataclass
class CheckpointState:
    execution_id: str
    plan_id: str | None
    started_at: str
    tasks: list[TaskState]
    last_checkpoint: str
    interrupted: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    # NEW
    conversation: list[dict] = field(default_factory=list)  # Turn dicts
```

**Migration**: Empty `conversation` for existing checkpoints (backward compatible).

### 3. Modified spawn_sequential

```python
async def spawn_sequential(
    tasks: list[SpawnTask],
    pass_context: bool = True,
    stop_on_failure: bool = False,
    context: ContextAccumulator | None = None,  # NEW
    **kwargs: Any,
) -> tuple[list[SpawnResult], ContextAccumulator]:
    """Spawn sequentially with structured context."""

    if context is None:
        context = ContextAccumulator()

    results = []

    for task in tasks:
        # Build prompt with accumulated context
        if pass_context and context.turns:
            full_prompt = f"{context.get_prompt()}\n\n[Current Task]\n{task.prompt}"
        else:
            full_prompt = task.prompt

        # Add user turn (task description)
        context.add_turn("user", task.prompt)

        # Execute
        modified_task = SpawnTask(
            prompt=full_prompt,
            agent=task.agent,
            timeout=task.timeout,
        )
        result = await spawn(modified_task, **kwargs)
        results.append(result)

        # Add assistant turn (response)
        if result.success and result.output:
            context.add_turn("assistant", result.output)

        if stop_on_failure and not result.success:
            break

    return results, context
```

### 4. CLI Integration

```python
@click.option(
    "--resume",
    type=str,
    help="Resume session by checkpoint ID",
)
@click.option(
    "--save-conversation/--no-save-conversation",
    default=True,
    help="Persist conversation to checkpoint (default: True)",
)
def spawn_command(
    task_file: Path,
    resume: str | None,
    save_conversation: bool,
    # ... existing options
):
    # Resume existing session
    if resume:
        checkpoint = CheckpointManager(resume).load()
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {resume}")

        # Restore context from checkpoint
        context = ContextAccumulator.from_dict(checkpoint.conversation)
        tasks = _reconstruct_remaining_tasks(checkpoint)

        console.print(f"[cyan]Resuming {resume} with {len(context.turns)} turns of context[/]")
    else:
        context = None
        tasks = load_tasks(task_file)

    # Execute with context
    results, final_context = asyncio.run(
        _execute_sequential(tasks, context=context, verbose=verbose)
    )

    # Save checkpoint with conversation
    if save_conversation:
        checkpoint_mgr.save(
            tasks=task_states,
            conversation=final_context.to_dict(),
        )
```

---

## Data Flow

### Sequential with Context

```
Task 1: "Analyze auth module"
         │
         ▼
┌─────────────────────────┐
│ ContextAccumulator      │
│ turns: [                │
│   {user: "Analyze..."}  │
│ ]                       │
└─────────┬───────────────┘
          │
          ▼ Prompt: "[User]\nAnalyze auth module"
┌─────────────────────────┐
│ spawn() → Agent         │
└─────────┬───────────────┘
          │
          ▼ Response: "Auth uses JWT..."
┌─────────────────────────┐
│ ContextAccumulator      │
│ turns: [                │
│   {user: "Analyze..."},│
│   {assistant: "Auth..."│
│ ]                       │
└─────────┬───────────────┘
          │
          ▼
Task 2: "What security issues?"
         │
         ▼
┌─────────────────────────┐
│ Prompt:                 │
│ "[User]                 │
│ Analyze auth module     │
│                         │
│ [Assistant]             │
│ Auth uses JWT...        │
│                         │
│ [Current Task]          │
│ What security issues?"  │
└─────────────────────────┘
```

### Resume Flow

```
aur spawn --resume spawn-123
         │
         ▼
┌─────────────────────────┐
│ CheckpointManager.load()│
│ → checkpoint.json       │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│ Restore:                │
│ - Remaining tasks       │
│ - Conversation history  │
└─────────┬───────────────┘
          │
          ▼
┌─────────────────────────┐
│ Continue execution      │
│ with full context       │
└─────────────────────────┘
```

---

## File Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `spawner/context.py` | **NEW** | ContextAccumulator class |
| `spawner/models.py` | **MODIFY** | Add Turn dataclass |
| `spawner/spawner.py` | **MODIFY** | Update spawn_sequential() |
| `execution/checkpoint.py` | **MODIFY** | Add conversation field |
| `commands/spawn.py` | **MODIFY** | Add --resume, context passing |
| `commands/spawn_helpers.py` | **MODIFY** | Session resume helper |

---

## Backward Compatibility

1. **Checkpoints**: Existing checkpoints work (empty conversation)
2. **spawn_parallel()**: Unchanged
3. **spawn_sequential()**: New param optional, defaults maintain old behavior
4. **CLI**: New flags optional, default behavior unchanged

---

## Testing Strategy

| Test Type | Scope | Location |
|-----------|-------|----------|
| Unit | ContextAccumulator | `tests/unit/spawner/test_context.py` |
| Unit | Turn serialization | `tests/unit/spawner/test_models.py` |
| Integration | Sequential w/ context | `tests/integration/test_spawn_sequential.py` |
| Integration | Resume flow | `tests/integration/test_spawn_resume.py` |
| E2E | Full workflow | `tests/e2e/test_spawn_multiturn.py` |

---

## Future Extensions

Once core statefulness works:

1. **Interactive REPL**: Add `--interactive` flag (Phase 3 from plan)
2. **Summarization trimming**: LLM-based context compression
3. **Session branching**: Fork conversations
4. **Multi-agent context**: Shared context across agents
