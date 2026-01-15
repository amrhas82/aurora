# Design: Adhoc Agent Spawning for Gap Resolution

## Architecture Overview

This design extends `aur spawn` to automatically create and use adhoc agents when agent gaps are detected. The system reads gap metadata from `goals.json` and generates specialized agent prompts dynamically.

```
┌─────────────────────────────────────────────────────────┐
│                   aur goals                              │
│  Decomposes goal → Detects gaps → Writes goals.json    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓ goals.json (with gaps array)
                       │
┌──────────────────────┴──────────────────────────────────┐
│                   aur spawn                              │
│  ┌─────────────────────────────────────────────┐       │
│  │ 1. Load goals.json                          │       │
│  │ 2. Extract agent gaps                       │       │
│  │ 3. Build gap_map: task_id → AgentGap       │       │
│  └─────────────────┬───────────────────────────┘       │
│                    │                                     │
│  ┌─────────────────▼──────────────────────────┐        │
│  │ For each task:                              │        │
│  │   if task_id in gap_map:                    │        │
│  │     gap = gap_map[task_id]                  │        │
│  │     adhoc_prompt = build_adhoc_prompt(gap)  │        │
│  │     spawn_task.adhoc_prompt = adhoc_prompt  │        │
│  │   else:                                     │        │
│  │     spawn_task.agent = registry_agent       │        │
│  └─────────────────┬───────────────────────────┘        │
│                    │                                     │
│                    ↓                                     │
│  ┌─────────────────────────────────────────────┐       │
│  │ Spawner: Execute with adhoc or registry     │       │
│  │   - If adhoc_prompt set → use it           │       │
│  │   - Else → use registry agent               │       │
│  └─────────────────┬───────────────────────────┘       │
│                    │                                     │
│                    ↓                                     │
│  ┌─────────────────────────────────────────────┐       │
│  │ Report Results:                              │       │
│  │   - Task completion summary                  │       │
│  │   - Adhoc agents used (yellow highlight)    │       │
│  └─────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Gap Loading (`spawn.py` additions)

**Responsibility**: Load and parse agent gaps from goals.json

```python
def load_goals_json(plan_path: Path) -> Goals | None:
    """Load goals.json from plan directory.

    Args:
        plan_path: Path to active plan directory

    Returns:
        Goals object or None if file doesn't exist/is invalid

    Example:
        >>> goals = load_goals_json(Path(".aurora/plans/active/0001"))
        >>> if goals and goals.gaps:
        ...     print(f"Found {len(goals.gaps)} gaps")
    """
    goals_file = plan_path / "goals.json"

    if not goals_file.exists():
        logger.debug(f"No goals.json found at {goals_file}")
        return None

    try:
        with goals_file.open() as f:
            data = json.load(f)
            return Goals(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse goals.json: {e}")
        return None


def build_gap_map(goals: Goals) -> dict[str, AgentGap]:
    """Build task_id → AgentGap mapping for O(1) lookups.

    Args:
        goals: Goals object from goals.json

    Returns:
        Dictionary mapping task IDs to their AgentGap

    Example:
        >>> gap_map = build_gap_map(goals)
        >>> if "sg-1" in gap_map:
        ...     gap = gap_map["sg-1"]
        ...     print(f"Gap: {gap.ideal_agent}")
    """
    gap_map = {}

    for gap in goals.gaps:
        # Map subgoal_id to gap
        # Assumes subgoal_id equals task_id (standard convention)
        gap_map[gap.subgoal_id] = gap

    return gap_map
```

**Integration Point**: Called at start of `spawn_command()`

### 2. Adhoc Agent Prompt Builder (`spawner/adhoc.py`)

**Responsibility**: Generate specialized agent prompts from gap metadata

```python
"""Adhoc agent generation for gap resolution in aurora-spawner."""

from dataclasses import dataclass

from aurora_cli.planning.models import AgentGap


@dataclass
class AdhocPromptTemplate:
    """Template for adhoc agent prompts."""

    system_prefix: str = "You are a specialized AI assistant with expertise in:"
    capability_intro: str = "Your specific capabilities include:"
    task_intro: str = "Current Task:"
    context_intro: str = "Project Context:"


def build_adhoc_prompt(
    gap: AgentGap,
    task_description: str,
    project_context: str = "",
    template: AdhocPromptTemplate | None = None,
) -> str:
    """Build specialized agent prompt from gap metadata.

    Args:
        gap: AgentGap with ideal_agent and ideal_agent_desc
        task_description: Description of task to perform
        project_context: Optional project-specific context
        template: Optional custom template (uses default if not provided)

    Returns:
        Formatted prompt string for adhoc agent

    Example:
        >>> gap = AgentGap(
        ...     subgoal_id="sg-1",
        ...     ideal_agent="@security-auditor",
        ...     ideal_agent_desc="Expert in security auditing, penetration testing, and vulnerability analysis",
        ...     assigned_agent="@full-stack-dev"
        ... )
        >>> task = "Audit authentication flow for SQL injection vulnerabilities"
        >>> prompt = build_adhoc_prompt(gap, task)
        >>> print(prompt)
        You are @security-auditor, a specialized AI assistant.

        Your expertise: Expert in security auditing, penetration testing, and vulnerability analysis

        Current Task: Audit authentication flow for SQL injection vulnerabilities

        Provide a specialized response leveraging your domain expertise.
    """
    if template is None:
        template = AdhocPromptTemplate()

    # Extract agent name (remove @ prefix if present)
    agent_name = gap.ideal_agent.lstrip("@")

    # Build prompt sections
    sections = [
        f"You are {gap.ideal_agent}, a specialized AI assistant.",
        f"\nYour expertise: {gap.ideal_agent_desc}",
        f"\n{template.task_intro} {task_description}",
    ]

    if project_context:
        sections.append(f"\n{template.context_intro}\n{project_context}")

    sections.append("\nProvide a specialized response leveraging your domain expertise.")

    return "\n".join(sections)


class AdhocAgentCache:
    """Cache for adhoc agent prompts within spawn session."""

    def __init__(self):
        """Initialize empty cache."""
        self._cache: dict[str, str] = {}

    def get(self, agent_id: str) -> str | None:
        """Get cached prompt for agent ID.

        Args:
            agent_id: Agent identifier (e.g., "@security-auditor")

        Returns:
            Cached prompt or None if not found
        """
        return self._cache.get(agent_id)

    def set(self, agent_id: str, prompt_template: str) -> None:
        """Cache prompt template for agent ID.

        Args:
            agent_id: Agent identifier
            prompt_template: Base prompt template for this agent
        """
        self._cache[agent_id] = prompt_template

    def clear(self) -> None:
        """Clear all cached prompts."""
        self._cache.clear()
```

### 3. Modified Spawn Execution Flow

**Changes to `packages/cli/src/aurora_cli/commands/spawn.py`**:

```python
async def _execute_parallel(
    tasks: list[ParsedTask],
    verbose: bool,
    checkpoint_mgr=None,
    gap_map: dict[str, AgentGap] | None = None,  # NEW
    adhoc_cache: AdhocAgentCache | None = None,  # NEW
) -> dict[str, int]:
    """Execute tasks in parallel with adhoc agent support.

    Args:
        tasks: List of tasks to execute
        verbose: Show detailed output
        checkpoint_mgr: Optional CheckpointManager
        gap_map: Optional mapping of task_id → AgentGap
        adhoc_cache: Optional cache for adhoc prompts

    Returns:
        Execution summary with adhoc_agents_used count
    """
    if not tasks:
        return {"total": 0, "completed": 0, "failed": 0, "adhoc_agents_used": 0}

    # Initialize adhoc tracking
    gap_map = gap_map or {}
    adhoc_cache = adhoc_cache or AdhocAgentCache()
    adhoc_used = set()

    # Convert ParsedTask to SpawnTask with adhoc support
    spawn_tasks = []
    for task in tasks:
        spawn_task = SpawnTask(
            prompt=task.description,
            agent=task.agent if task.agent != "self" else None,
            timeout=300,
        )

        # Check for agent gap
        if task.id in gap_map:
            gap = gap_map[task.id]

            # Check cache first
            cached_prompt = adhoc_cache.get(gap.ideal_agent)
            if cached_prompt:
                # Reuse cached template, add task-specific details
                adhoc_prompt = f"{cached_prompt}\n\nCurrent Task: {task.description}"
            else:
                # Build new adhoc prompt
                adhoc_prompt = build_adhoc_prompt(gap, task.description)
                # Cache the base template
                adhoc_cache.set(gap.ideal_agent, adhoc_prompt)

            spawn_task.adhoc_prompt = adhoc_prompt
            adhoc_used.add(gap.ideal_agent)

            if verbose:
                console.print(
                    f"[yellow]Using adhoc agent {gap.ideal_agent} for task {task.id}[/]"
                )

        spawn_tasks.append(spawn_task)

    # Execute with adhoc support
    results = await spawn_parallel(spawn_tasks, max_concurrent=5)

    # Count results
    total = len(results)
    completed = sum(1 for r in results if r.success)
    failed = total - completed

    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "adhoc_agents_used": len(adhoc_used),
        "adhoc_agents": list(adhoc_used),  # For reporting
    }
```

**Changes to `spawn_command()`**:

```python
def spawn_command(...):
    """Execute tasks with adhoc agent support for gaps."""

    # ... existing code ...

    # NEW: Load goals.json and extract gaps
    gap_map = {}
    adhoc_cache = AdhocAgentCache()

    # Determine plan directory (heuristic: look for .aurora/plans/active/*)
    plan_dir = Path.cwd() / ".aurora" / "plans" / "active"
    if plan_dir.exists():
        # Find most recent plan directory
        plan_dirs = sorted(plan_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if plan_dirs:
            goals = load_goals_json(plan_dirs[0])
            if goals and goals.gaps:
                gap_map = build_gap_map(goals)
                console.print(f"[dim]Found {len(gap_map)} agent gaps to resolve[/]")

    # ... existing task loading ...

    # Execute with gap awareness
    if use_parallel:
        result = asyncio.run(
            _execute_parallel(tasks, verbose, checkpoint_mgr, gap_map, adhoc_cache)
        )
    else:
        result = asyncio.run(
            _execute_sequential(tasks, verbose, checkpoint_mgr, gap_map, adhoc_cache)
        )

    # Display summary with adhoc reporting
    console.print(f"\n[bold green]Completed:[/] {result['completed']}/{result['total']}")
    if result["failed"] > 0:
        console.print(f"[bold red]Failed:[/] {result['failed']}")

    # NEW: Report adhoc agents used
    if result.get("adhoc_agents_used", 0) > 0:
        console.print(f"\n[bold yellow]Adhoc Agents Used:[/]")
        for agent_id in result.get("adhoc_agents", []):
            console.print(f"  - {agent_id}")
```

### 4. SpawnTask Model Extension

**Changes to `packages/spawner/src/aurora_spawner/models.py`**:

```python
@dataclass
class SpawnTask:
    """Task for subprocess spawning with adhoc agent support."""

    prompt: str
    agent: str | None = None
    timeout: int = 300
    adhoc_prompt: str | None = None  # NEW: Override prompt if set

    def get_effective_prompt(self) -> str:
        """Get the prompt to use (adhoc takes precedence).

        Returns:
            adhoc_prompt if set, otherwise regular prompt
        """
        return self.adhoc_prompt if self.adhoc_prompt else self.prompt
```

**Changes to `packages/spawner/src/aurora_spawner/spawner.py`**:

```python
async def spawn(
    task: SpawnTask,
    tool: str | None = None,
    model: str | None = None,
    config: dict[str, Any] | None = None,
    on_output: Callable[[str], None] | None = None,
) -> SpawnResult:
    """Spawn subprocess with adhoc agent support.

    If task.adhoc_prompt is set, uses it instead of task.prompt.
    This allows dynamic agent specialization at spawn time.
    """
    # ... existing tool/model resolution ...

    # Build command
    cmd = [resolved_tool, "-p", "--model", resolved_model]

    # Add --agent flag if agent specified
    if task.agent:
        cmd.extend(["--agent", task.agent])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Write effective prompt to stdin (adhoc takes precedence)
        if process.stdin:
            effective_prompt = task.get_effective_prompt()  # NEW
            process.stdin.write(effective_prompt.encode())
            await process.stdin.drain()
            process.stdin.close()

        # ... rest of spawn logic unchanged ...
```

## Data Flow

### Spawn with Gaps Flow

```
1. User runs: aur spawn

2. spawn_command() starts:
   ├─ Look for .aurora/plans/active/*/goals.json
   ├─ Load goals.json → Goals object
   ├─ Extract gaps: Goals.gaps
   └─ Build gap_map: {task_id: AgentGap}

3. For each task:
   ├─ Check if task.id in gap_map
   │  ├─ YES → Gap detected
   │  │  ├─ Get gap: gap_map[task.id]
   │  │  ├─ Check adhoc_cache for prompt
   │  │  │  ├─ Hit → Reuse template + add task details
   │  │  │  └─ Miss → Build new prompt from gap metadata
   │  │  ├─ Set spawn_task.adhoc_prompt
   │  │  └─ Track adhoc agent usage
   │  └─ NO → Use registry agent
   └─ Add to spawn_tasks list

4. Execute spawn_tasks:
   └─ For each task:
      ├─ spawner.spawn(task)
      ├─ If task.adhoc_prompt → use it
      └─ Else → use task.prompt

5. Report results:
   ├─ Task summary (completed/failed)
   └─ Adhoc agents used (highlighted)
```

### Example goals.json Structure

```json
{
  "id": "0001-add-auth",
  "title": "Add authentication system",
  "subgoals": [...],
  "gaps": [
    {
      "subgoal_id": "sg-1",
      "ideal_agent": "@security-auditor",
      "ideal_agent_desc": "Expert in security auditing, penetration testing, and vulnerability analysis",
      "assigned_agent": "@full-stack-dev",
      "recommended_agent": "@qa-test-architect",
      "confidence": 0.3
    },
    {
      "subgoal_id": "sg-3",
      "ideal_agent": "@compliance-expert",
      "ideal_agent_desc": "Specialist in GDPR, SOC2, and regulatory compliance for authentication systems",
      "assigned_agent": "@full-stack-dev",
      "recommended_agent": "@product-manager",
      "confidence": 0.25
    }
  ]
}
```

## Error Handling

| Error Scenario | Handling Strategy |
|----------------|-------------------|
| **goals.json missing** | Log debug message, proceed without gaps (backward compatible) |
| **goals.json malformed** | Log error, proceed without gaps, show warning to user |
| **Empty gaps array** | Normal operation, no adhoc agents needed |
| **Gap metadata incomplete** | Use fallback: `ideal_agent_desc = "Specialized agent for {subgoal.title}"` |
| **Adhoc prompt generation fails** | Fall back to assigned_agent, log warning |
| **Spawn with adhoc fails** | Same error handling as normal spawn failures |

## Performance Considerations

1. **Gap Loading**: O(1) file read at spawn start (~5ms)
2. **Gap Map**: O(n) build, O(1) lookup per task
3. **Adhoc Cache**: O(1) lookup/insert, reduces prompt generation
4. **Total Overhead**: <50ms for typical 5-10 task spawns

## Security

- **Prompt injection**: Gap metadata from goals.json (trusted source, generated by Aurora)
- **File access**: Only reads from `.aurora/plans/active/` (project-scoped)
- **Subprocess spawning**: Same security model as existing spawn

## Testing Strategy

### Unit Tests
- `test_load_goals_json()`: Valid/invalid/missing files
- `test_build_gap_map()`: Mapping correctness
- `test_build_adhoc_prompt()`: Prompt generation with various inputs
- `test_adhoc_cache()`: Cache hit/miss/clear

### Integration Tests
- `test_spawn_with_one_gap()`: Single gap resolution
- `test_spawn_with_multiple_gaps()`: Multiple concurrent gaps
- `test_spawn_without_gaps()`: Backward compatibility
- `test_spawn_missing_goals()`: Graceful degradation

### E2E Test
```python
def test_full_workflow_with_gaps():
    """Test complete workflow: goals → gaps → spawn with adhoc."""
    # 1. Create goals.json with gaps
    goals = Goals(
        id="test-plan",
        subgoals=[...],
        gaps=[
            AgentGap(
                subgoal_id="sg-1",
                ideal_agent="@security-auditor",
                ideal_agent_desc="Expert in security auditing",
                assigned_agent="@full-stack-dev",
            )
        ],
    )
    goals_path = Path(".aurora/plans/active/test-plan/goals.json")
    goals_path.parent.mkdir(parents=True, exist_ok=True)
    goals_path.write_text(goals.model_dump_json())

    # 2. Run spawn
    result = runner.invoke(spawn_command, ["tasks.md"])

    # 3. Verify
    assert result.exit_code == 0
    assert "Adhoc Agents Used" in result.output
    assert "@security-auditor" in result.output
```

## Migration Path

**Phase 1** (This plan):
- Basic adhoc agent spawning
- Simple prompt generation
- Session-scoped caching

**Phase 2** (Future):
- Persist adhoc agents to registry after successful use
- Interactive gap resolution (user chooses fallback or adhoc)
- Adhoc agent quality feedback loop

**Phase 3** (Future):
- Multi-agent collaboration for complex gaps
- Context sharing between adhoc and registry agents
- Learning from adhoc agent patterns to improve registry
