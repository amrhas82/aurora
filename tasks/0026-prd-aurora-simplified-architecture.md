# PRD 0026: Aurora Simplified Execution Layer

**Version**: 2.0 (Merged)
**Date**: 2026-01-09
**Status**: Draft
**Priority**: High
**Author**: Aurora Team
**Dependencies**: PRD-0021 (Agent Discovery), PRD-0025 (aur soar Terminal Orchestrator)

---

## 1. Introduction/Overview

### Problem Statement

Aurora has a solid foundation with memory (ACT-R), planning (OpenSpec), and agent discovery, but lacks the execution layer to actually run agents. The current SOAR orchestrator has stub implementations (`_mock_agent_execution()`) where real agent spawning should occur.

After evaluating Zeroshot's complex orchestration (message bus, triggers, hooks, conductors - 5,000+ lines), we determined that **imperative parallel spawning** (~100 lines) is sufficient for Aurora's needs.

**Complexity avoided from Zeroshot:**
- Message bus (~800 lines) - unnecessary for simple spawning
- Triggers/hooks (~600 lines) - over-engineered event system
- Conductors (~500 lines) - complex coordination for simple tasks
- Completion detectors (~400 lines) - overkill for subprocess tracking
- SQLite message persistence (~300 lines) - not needed
- PTY sockets (~400 lines) - interactive features unused
- Watch TUI (~500 lines) - complex UI for simple workflows

### Solution Overview

Five execution tracks with clean separation:

| Track | Command | Where | Execution Model | Purpose |
|-------|---------|-------|-----------------|---------|
| 1 | `aur soar` | Terminal | Parallel spawn | Research/Questions |
| 2 | `aur goals` | Terminal | No execution | High-level decomposition, create plan directory |
| 3 | `/plan` | Claude Code | Sequential | Generate PRD, tasks.md, specs in existing directory |
| 4 | `aur implement` | Claude Code | Sequential (Task tool) | Execute tasks with agent dispatch |
| 5 | `aur spawn` | Terminal | Parallel (subprocess) | Parallel task execution |

### Business Value

- **90%+ reduction** in orchestration code (5,000 -> ~700 lines)
- **Maintainability**: Small, focused packages instead of monolithic orchestrator
- **Flexibility**: Choose execution model per use case

---

## 2. Goals

### Goal 1: Create aurora-spawner Package
Create minimal package (~100 lines) providing core spawning primitive.

**Success Criteria**:
- `spawn_claude(prompt, model)` spawns Claude CLI and returns output
- `spawn_parallel(tasks)` runs multiple tasks concurrently with limit
- `spawn_sequential(tasks)` runs tasks with context accumulation
- Full TDD test coverage with mocked subprocess calls

### Goal 2: Create implement Package
Port implementation logic (~200 lines) for in-Claude execution.

**Success Criteria**:
- Parses `tasks.md` with agent metadata comments (`<!-- agent: X -->`)
- Executes tasks sequentially using Claude's Task tool
- Spawns appropriate subagent per task
- Modified apply prompt handles agent dispatch

### Goal 3: Wire Spawner to SOAR Collect Phase
Replace `_mock_agent_execution()` stub with real spawning.

**Success Criteria**:
- SOAR collect phase uses aurora-spawner
- Parallel execution for independent subgoals
- Results properly converted to AgentOutput format

### Goal 4: Deprecate AgentRegistry
Remove duplicate agent discovery. Use `aurora_cli/agent_discovery/` everywhere.

**Success Criteria**:
- SOAR orchestrator uses agent_discovery module
- Route phase uses agent_discovery module
- AgentRegistry marked deprecated with warning
- All tests passing with new discovery

### Goal 5: Implement aur spawn Command
Add CLI command for parallel task execution from terminal.

**Success Criteria**:
- Reads `tasks.md` with agent metadata
- Parallel spawns Claude CLI per task
- Reports completion status

### Goal 6: Enhance aur soar Command
Wire parallel spawning for research queries.

**Success Criteria**:
- Uses `spawn_parallel()` for research sub-questions
- Assess phase routes trivial/complex appropriately
- Parallel spawning improves response time

### Goal 7: Implement aur goals Command (rename from aur plan)
Create plan directory with high-level goals and agent assignments. This is the **entry point** for implementation workflows.

**Success Criteria**:
- **Uses CLIPipeLLMClient** (same as `aur soar`) - NOT API-based LLMClient
- Tool resolution: CLI flag → env var → config → default (consistent with spawner)
- Memory search finds relevant context
- Goal decomposed into subgoals with agent matching
- Gap detection with LLM fallback
- User review before output
- Creates plan directory: `.aurora/plans/NNNN-slug/`
- Outputs `goals.json` with subgoals and agent assignments
- `/plan` skill reads this directory and adds PRD, tasks.md, specs

**Current gap**: `aur plan` uses API-based `LLMClient()`. Must switch to `CLIPipeLLMClient` for CLI-agnostic operation.

### Goal 8: Update /plan Skill
Modify `/plan` to read existing goals directory instead of creating new one.

**Success Criteria**:
- Reads `goals.json` from directory created by `aur goals`
- Generates `prd.md` in same directory
- Generates `tasks.md` with agent metadata from goals.json
- Generates `specs/` subdirectory with detailed specs
- Does NOT create new directory (uses existing from aur goals)

---

## 3. User Stories

### Track 1: Research (aur soar)

**US-1: Research Question with Parallel Sub-queries**
```
AS A developer
I WANT to run `aur soar "What are the best practices for async Python?"`
SO THAT Aurora decomposes my question and researches in parallel
```

**Acceptance Criteria**:
- Assess phase determines trivial/complex
- Trivial questions answered directly (no spawning)
- Complex questions decomposed into sub-questions
- Sub-questions researched in parallel via `spawn_parallel()`
- Results synthesized into comprehensive answer

### Track 2: Goal Decomposition (aur goals)

**US-2: Create Goals with Agent Assignments**
```
AS A developer
I WANT to run `aur goals "Add OAuth2 authentication"`
SO THAT Aurora creates a plan directory with goals and agent assignments
```

**Acceptance Criteria**:
- Memory search finds relevant existing files
- Goal decomposed into subgoals
- Agents matched to subgoals (with gap detection)
- User reviews before output
- Creates directory `.aurora/plans/0001-add-oauth2/`
- `goals.json` generated with subgoals and assignments

### Track 3: Detailed Planning (/plan)

**US-3: Generate PRD and Tasks from Goals**
```
AS A developer in Claude Code
I WANT to run `/plan` in a goals directory
SO THAT Aurora generates PRD, tasks.md, and specs from my goals
```

**Acceptance Criteria**:
- Reads `goals.json` from current directory (created by `aur goals`)
- Generates `prd.md` with full requirements
- Generates `tasks.md` with agent metadata from goals
- Generates `specs/` with detailed specifications
- All files created in same directory as goals.json

### Track 4: In-Claude Execution (aur implement)

**US-4: Execute Tasks with Agent Dispatch**
```
AS A developer in Claude Code
I WANT to run `aur implement`
SO THAT tasks are executed with appropriate agent spawning
```

**Acceptance Criteria**:
- Reads `tasks.md` with agent metadata
- For `agent != "self"`: spawns subagent via Task tool
- For `agent == "self"`: executes directly
- Marks task `[x]` after verified completion

### Track 5: Terminal Parallel Execution (aur spawn)

**US-5: Parallel Task Execution**
```
AS A developer
I WANT to run `aur spawn tasks.md`
SO THAT tasks are executed in parallel using Claude CLI
```

**Acceptance Criteria**:
- Reads `tasks.md` with agent metadata
- Spawns Claude CLI per task in parallel
- Collects and reports results

---

## 4. Functional Requirements

### FR-1: aurora-spawner Package

#### FR-1.1: CLI-Agnostic Spawner (follows aur soar pattern)

Reuse existing `CLIPipeLLMClient` pattern from `aur soar`:

```python
async def spawn(
    prompt: str,
    tool: str | None = None,
    model: str | None = None,
    agent: str | None = None,
    timeout: int = 300,
    on_output: Callable[[str], None] | None = None,
) -> SpawnResult:
    """Spawn CLI tool - follows same pattern as aur soar.

    Tool resolution: CLI flag → env var → config → default
    Same as CLIPipeLLMClient in aurora_cli/llm/cli_pipe_client.py
    """
    # Resolve tool (same logic as aur soar)
    if tool is None:
        tool = os.environ.get(
            "AURORA_SPAWN_TOOL",
            config.soar_default_tool if config else "claude",
        )

    # Resolve model
    if model is None:
        model = os.environ.get(
            "AURORA_SPAWN_MODEL",
            config.soar_default_model if config else "sonnet",
        )

    # Validate tool exists
    if not shutil.which(tool):
        raise ValueError(f"Tool '{tool}' not found in PATH")

    # Build command - pipe prompt via stdin (same as CLIPipeLLMClient)
    cmd = [tool, "-p", "--model", model]
    if agent:
        cmd.extend(["--agent", agent])

    # Spawn with streaming
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Write prompt to stdin
    proc.stdin.write(prompt.encode())
    await proc.stdin.drain()
    proc.stdin.close()

    # Stream output
    output_lines = []
    async for line in proc.stdout:
        text = line.decode()
        output_lines.append(text)
        if on_output:
            on_output(text)
        else:
            print(text, end="")

    await proc.wait()
    stderr = await proc.stderr.read()

    return SpawnResult(
        success=proc.returncode == 0,
        output="".join(output_lines),
        error=stderr.decode() if stderr else None,
        exit_code=proc.returncode,
    )
```

**Notes**:
- **Same pattern as `aur soar`** - uses `CLIPipeLLMClient` approach
- Tool resolution: CLI flag → `AURORA_SPAWN_TOOL` env → config → "claude"
- Model resolution: CLI flag → `AURORA_SPAWN_MODEL` env → config → "sonnet"
- Prompt piped via stdin (like existing `subprocess.run(..., input=prompt)`)
- Works with any CLI tool that accepts `-p` flag (claude, cursor, etc.)
- Agent flag only added if tool supports it

#### FR-1.2: spawn_parallel Function
```python
async def spawn_parallel(
    tasks: list[SpawnTask],
    max_concurrent: int = 5,
) -> list[SpawnResult]:
```

**Behavior**:
- Use `asyncio.Semaphore` for concurrency limiting
- Best-effort execution (continue on failure)
- Return results in input order

#### FR-1.3: spawn_sequential Function
```python
async def spawn_sequential(
    tasks: list[SpawnTask],
    pass_context: bool = True,
) -> list[SpawnResult]:
```

**Behavior**:
- Execute in order, append previous outputs as context
- Format: `"\n\nPrevious context:\n{accumulated}"`

#### FR-1.4: Models
```python
@dataclass
class SpawnTask:
    prompt: str
    agent: str | None = None
    timeout: int = 300

@dataclass
class SpawnResult:
    success: bool
    output: str
    error: str | None
    exit_code: int
```

---

### FR-2: implement Package

#### FR-2.1: Task Parser
Parse tasks.md format:
```markdown
- [ ] 1. Implement auth endpoint
  <!-- agent: full-stack-dev -->
  <!-- model: sonnet -->
```

Output `ParsedTask` with: `id`, `description`, `agent`, `model`, `completed`

#### FR-2.2: Modified Apply Prompt
```
For each uncompleted task in tasks.md:
1. Read agent assignment from <!-- agent: X --> comment
2. If agent != "self":
   - Use Task tool with subagent_type = agent
   - Pass task description as prompt
   - Wait for completion
3. If agent == "self":
   - Execute directly
4. Mark task [x] after verified completion
5. Continue until all complete
```

---

### FR-3: SOAR Collect Phase Wiring

#### FR-3.1: Replace Mock Execution
```python
# Before (stub):
async def _mock_agent_execution(...) -> AgentOutput:
    return AgentOutput(success=True, summary="Mock result...")

# After (real):
async def _execute_agent(agent_info, subgoal, context) -> AgentOutput:
    prompt = build_agent_prompt(agent_info, subgoal, context)
    result = await spawn_claude(prompt, model=agent_info.model)
    return AgentOutput(success=result.success, ...)
```

#### FR-3.2: Parallel Mode
```python
async def collect_parallel(assignments: list[AgentAssignment]) -> CollectResult:
    tasks = [SpawnTask(prompt=..., agent=a.agent.id) for a in assignments]
    results = await spawn_parallel(tasks, max_concurrent=5)
    return CollectResult(agent_outputs=[...])
```

---

### FR-4: AgentRegistry Deprecation

#### FR-4.1: Update SOAR Orchestrator
```python
# Before:
from aurora_soar.agent_registry import AgentRegistry

# After:
from aurora_cli.agent_discovery import ManifestManager
manifest = ManifestManager().get_or_refresh()
```

#### FR-4.2: Deprecation Warning
```python
# aurora_soar/agent_registry.py
import warnings

class AgentRegistry:
    def __init__(self, ...):
        warnings.warn(
            "AgentRegistry is deprecated. Use aurora_cli.agent_discovery.",
            DeprecationWarning,
        )
```

---

### FR-5: Agent Matching with Gap Detection

#### FR-5.1: Enhanced AgentRecommender
Existing `AgentRecommender` in `aurora_cli/planning/agents.py` needs:

```python
def recommend_for_subgoal(self, subgoal: Subgoal) -> tuple[str, float]:
    # 1. Try keyword matching (existing)
    agent_id, score = self._keyword_match(subgoal)

    if score >= self.score_threshold:
        return (agent_id, score)

    # 2. Try LLM-based classification (NEW)
    if self.llm_client:
        agent_id, score = self._llm_classify(subgoal)
        if score >= self.score_threshold:
            return (agent_id, score)

    # 3. Return fallback with gap flag
    return (self.default_fallback, score)

def _llm_classify(self, subgoal: Subgoal) -> tuple[str, float]:
    """Use LLM to suggest agent when keyword matching fails."""
    prompt = f"""
    Given this task: {subgoal.description}

    Available agents: {self._format_agents()}

    Which agent is best suited? Return JSON:
    {{"agent_id": "...", "confidence": 0.0-1.0, "reasoning": "..."}}
    """
    # Call LLM, parse response
    ...
```

#### FR-5.2: Gap Reporting
When no good match found:
```python
gaps = recommender.detect_gaps(subgoals, recommendations)
for gap in gaps:
    print(f"WARNING: No good agent for '{gap.subgoal_id}'")
    print(f"  Suggested: Create agent with capabilities: {gap.suggested_capabilities}")
    print(f"  Using fallback: {gap.fallback}")
```

---

### FR-6: aur goals Command

#### FR-6.1: Directory Creation
```python
def create_plan_directory(title: str) -> Path:
    """Create numbered plan directory."""
    plans_dir = Path(".aurora/plans")
    plans_dir.mkdir(parents=True, exist_ok=True)

    # Find next number
    existing = sorted(plans_dir.glob("????-*"))
    next_num = len(existing) + 1

    # Create slug from title
    slug = slugify(title)[:50]
    dir_name = f"{next_num:04d}-{slug}"

    plan_dir = plans_dir / dir_name
    plan_dir.mkdir()
    return plan_dir
```

#### FR-6.2: goals.json Format
```json
{
  "id": "0001-add-oauth2",
  "title": "Add OAuth2 Authentication",
  "created_at": "2026-01-09T12:00:00Z",
  "status": "ready_for_planning",
  "memory_context": [
    {"file": "src/auth/login.py", "relevance": 0.85},
    {"file": "docs/auth-design.md", "relevance": 0.72}
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Implement OAuth provider integration",
      "description": "Add Google/GitHub OAuth providers",
      "agent": "@full-stack-dev",
      "confidence": 0.85,
      "dependencies": []
    },
    {
      "id": "sg-2",
      "title": "Write OAuth integration tests",
      "description": "Test OAuth flow end-to-end",
      "agent": "@qa-test-architect",
      "confidence": 0.92,
      "dependencies": ["sg-1"]
    }
  ],
  "gaps": [
    {
      "subgoal_id": "sg-3",
      "suggested_capabilities": ["security", "audit"],
      "fallback": "@full-stack-dev"
    }
  ]
}
```

#### FR-6.3: User Review Flow
```
$ aur goals "Add OAuth2 authentication"

🔍 Searching memory for relevant context...
   Found 3 relevant files

📋 Decomposing goal into subgoals...
   Created 4 subgoals

🤖 Matching agents to subgoals...
   sg-1: @full-stack-dev (0.85)
   sg-2: @qa-test-architect (0.92)
   sg-3: @full-stack-dev (0.45) ⚠️ gap detected
   sg-4: @full-stack-dev (0.78)

📁 Plan directory: .aurora/plans/0001-add-oauth2/

Review goals? [Y/n]: y
<opens goals.json in editor>

Proceed? [Y/n]: y
✅ Goals saved. Run `/plan` in Claude Code to generate PRD and tasks.
```

---

### FR-7: /plan Skill Updates

#### FR-7.1: Read Existing Goals
```python
def load_goals(plan_dir: Path) -> Goals:
    """Load goals.json from plan directory."""
    goals_file = plan_dir / "goals.json"
    if not goals_file.exists():
        raise ValueError(
            f"No goals.json found in {plan_dir}. "
            "Run 'aur goals' first to create the plan directory."
        )
    return Goals.from_json(goals_file.read_text())
```

#### FR-7.2: Generate in Same Directory
```python
def generate_plan_artifacts(plan_dir: Path, goals: Goals):
    """Generate PRD, tasks, specs in existing plan directory."""
    # Generate PRD
    prd_content = generate_prd(goals)
    (plan_dir / "prd.md").write_text(prd_content)

    # Generate tasks with agent metadata
    tasks_content = generate_tasks(goals)
    (plan_dir / "tasks.md").write_text(tasks_content)

    # Generate specs
    specs_dir = plan_dir / "specs"
    specs_dir.mkdir(exist_ok=True)
    for spec in generate_specs(goals):
        (specs_dir / spec.filename).write_text(spec.content)
```

---

## 5. Architecture

### 5.1 Package Structure
```
packages/
├── spawner/                      # NEW: aurora-spawner
│   ├── src/aurora_spawner/
│   │   ├── __init__.py
│   │   ├── spawner.py           # spawn_claude, spawn_parallel, spawn_sequential
│   │   └── models.py            # SpawnTask, SpawnResult
│   └── tests/
│
├── implement/                    # NEW: implement
│   ├── src/implement/
│   │   ├── __init__.py
│   │   ├── executor.py          # Task executor with agent dispatch
│   │   ├── parser.py            # tasks.md parser
│   │   └── prompts/
│   │       └── apply.md         # Modified apply prompt
│   └── tests/
│
├── cli/                          # ENHANCE: aurora-cli
│   └── src/aurora_cli/
│       ├── commands/
│       │   ├── spawn.py         # NEW: aur spawn command
│       │   ├── goals.py         # RENAME: aur plan → aur goals
│       │   └── soar.py          # ENHANCE: + spawner
│       ├── agent_discovery/
│       │   └── matcher.py       # ENHANCE: + LLM fallback
│       └── planning/
│           └── agents.py        # ENHANCE: + LLM classification
│
└── soar/                         # ENHANCE: aurora-soar
    └── src/aurora_soar/
        ├── phases/
        │   ├── collect.py       # ENHANCE: wire spawner
        │   └── route.py         # ENHANCE: use agent_discovery
        └── agent_registry.py    # DEPRECATE
```

### 5.2 Flow Diagram
```
                         Aurora Simplified Architecture
                         ==============================

    TERMINAL                                           CLAUDE CODE
    --------                                           -----------

    ┌─────────────────┐
    │   aur soar      │
    │   "question"    │
    │                 │
    │ 1. Assess       │
    │ 2. Memory       │
    │ 3. Decompose    │
    │ 4. spawn_parallel
    │ 5. Synthesize   │
    └─────────────────┘


    ┌─────────────────┐
    │   aur goals     │ ──────────────┐
    │   "goal"        │               │
    │                 │               │  Creates:
    │ 1. Memory       │               │  .aurora/plans/0001-slug/
    │ 2. Decompose    │               │  └── goals.json
    │ 3. Agent Match  │               │
    │ 4. USER REVIEW  │               │
    │ 5. Create dir   │               │
    └─────────────────┘               │
                                      │
            goals.json ◄──────────────┘
                                      │
                                      ▼
                          ┌─────────────────────────┐
                          │   /plan                 │
                          │   (reads goals.json)    │
                          │                         │
                          │ Creates in same dir:    │
                          │ - prd.md                │
                          │ - tasks.md              │
                          │ - specs/                │
                          └───────────┬─────────────┘
                                      │
                                      ▼
                          ┌─────────────────────────┐
                          │   aur implement         │
                          │   (reads tasks.md)      │
                          │                         │
                          │ - Task tool (agent)     │
                          │ - Mark [x] complete     │
                          └───────────┬─────────────┘
                                      │
                                      │ tasks.md
                                      │
                                      ▼
    ┌─────────────────┐   ┌─────────────────────────┐
    │   aur spawn     │ ◀─│   (alternative path)    │
    │   <tasks.md>    │   │                         │
    │                 │   │ Parallel subprocess     │
    │ spawn_parallel  │   │ spawning from terminal  │
    └─────────────────┘   └─────────────────────────┘
```

### 5.3 Plan Directory Structure
```
.aurora/plans/0001-add-oauth2/
├── goals.json          # Created by: aur goals
├── prd.md              # Created by: /plan
├── tasks.md            # Created by: /plan
├── specs/              # Created by: /plan
│   ├── api-spec.md
│   └── auth-flow.md
└── agents.json         # Created by: aur goals (optional, agent assignments)
```

### 5.4 tasks.md Format
```markdown
## Tasks

- [ ] 1. Implement user authentication endpoint
  <!-- agent: full-stack-dev -->

- [ ] 2. Write integration tests for auth
  <!-- agent: qa-test-architect -->

- [ ] 3. Update API documentation
  <!-- agent: self -->
```

---

## 6. Sprint Plan (TDD)

### Sprint 1: Core Infrastructure (Est: 8-12 hours)

**Phase 1: aurora-spawner package**
- [ ] Write tests for `spawn_claude()` (TDD)
- [ ] Implement `spawn_claude()`
- [ ] Write tests for `spawn_parallel()` (TDD)
- [ ] Implement `spawn_parallel()`
- [ ] Write tests for `spawn_sequential()` (TDD)
- [ ] Implement `spawn_sequential()`
- [ ] Manual verification with real Claude CLI

**Phase 2: implement package**
- [ ] Write tests for task parser (TDD)
- [ ] Implement task parser
- [ ] Write tests for executor (TDD)
- [ ] Implement executor with agent dispatch
- [ ] Create modified apply.md prompt

**Gate**: Both packages have 90%+ test coverage

---

### Sprint 2: SOAR Integration (Est: 6-8 hours)

**Phase 3: Wire spawner to SOAR collect**
- [ ] Write tests for `_execute_agent()` (TDD)
- [ ] Replace `_mock_agent_execution()` with real spawner
- [ ] Write tests for parallel collect mode (TDD)
- [ ] Implement parallel collect
- [ ] Update existing SOAR tests

**Phase 4: Deprecate AgentRegistry**
- [ ] Write migration tests (TDD)
- [ ] Update SOAR orchestrator imports
- [ ] Update route phase imports
- [ ] Add deprecation warning to AgentRegistry
- [ ] Verify all tests pass

**Gate**: SOAR uses agent_discovery, AgentRegistry deprecated

---

### Sprint 3: CLI Commands (Est: 8-10 hours)

**Phase 5: aur spawn command**
- [ ] Write tests for argument parsing (TDD)
- [ ] Write tests for task loading (TDD)
- [ ] Write tests for parallel execution (TDD)
- [ ] Implement command with Rich progress display

**Phase 6: aur soar enhancements**
- [ ] Write tests for parallel research spawning (TDD)
- [ ] Wire spawner to research sub-questions
- [ ] Update synthesis to handle parallel results
- [ ] Manual E2E testing

**Gate**: Both commands work with real Claude CLI

---

### Sprint 4: Planning Flow (Est: 8-10 hours)

**Phase 7: aur goals command (rename from aur plan)**
- [ ] Rename plan.py → goals.py
- [ ] **Switch from LLMClient to CLIPipeLLMClient** (critical - CLI-agnostic)
- [ ] Add `--tool` flag (same as `aur soar`)
- [ ] Write tests for directory creation (TDD)
- [ ] Write tests for goals.json output (TDD)
- [ ] Write tests for memory search integration (TDD)
- [ ] Write tests for agent matching with LLM fallback (TDD)
- [ ] Write tests for gap detection (TDD)
- [ ] Implement user review flow

**Phase 8: /plan skill updates**
- [ ] Write tests for goals.json loading (TDD)
- [ ] Write tests for generating in existing directory (TDD)
- [ ] Update /plan to read goals.json instead of creating directory
- [ ] Generate tasks.md with agent metadata from goals

**E2E Testing**
- [ ] Full flow: aur goals → /plan → aur implement
- [ ] Full flow: aur goals → /plan → aur spawn
- [ ] aur soar complex query with parallel research

**Gate**: All flows work end-to-end

---

## 7. Testing Strategy

### Unit Tests (TDD - Tests First)
```python
# Example: Test spawn_claude before implementing
@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_spawn_claude_success(mock_exec):
    # Arrange
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"output", b"")
    mock_proc.returncode = 0
    mock_exec.return_value = mock_proc

    # Act
    result = await spawn_claude("test prompt")

    # Assert
    assert result.success is True
    assert result.output == "output"
    mock_exec.assert_called_once_with(
        "claude", "-p", "test prompt", "--model", "sonnet", ...
    )
```

### Integration Tests
- End-to-end with mocked Claude CLI (environment variable `AURORA_MOCK_CLAUDE=1`)
- Real Claude CLI tests (manual, not in CI)

### Coverage Requirements
- All new code: 90%+ coverage
- No PR merged without passing tests

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| aurora-spawner lines | < 150 |
| implement lines | < 250 |
| Total new code | < 700 lines |
| Test coverage | >= 90% |
| Spawn success rate | >= 95% |
| Parallel speedup | >= 3x vs sequential |

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Claude CLI API changes | Pin version, abstract interface |
| Subprocess timeout issues | Configurable timeout, graceful handling |
| Agent discovery mismatch | Comprehensive adapter testing |
| Task tool behavior changes | Mock-based tests, version pinning |

---

## 10. Open Questions

### Q1: Claude CLI Arguments ✅ RESOLVED
**Answer**: Verified via `claude --help`:
- `--agent <agent>` - Invoke specific agent
- `-p` / `--print` - Non-interactive output
- `--model <model>` - Model selection

### Q2: Concurrency Limits ✅ RESOLVED
**Answer**: Default of 5 concurrent spawns is good. Configurable via:
- `max_concurrent` parameter in `spawn_parallel()`
- Config option for CLI commands
- Can be adjusted based on system resources and API rate limits

### Q3: Model Resolution Flow ✅ DOCUMENTED
**Question**: Where/how does model decision happen for `aur plan` (now `aur goals`) and `aur soar`?

**Answer**: All CLI commands follow the same resolution pattern (priority order):
1. **CLI flag** (highest priority): `--model opus` or `-m sonnet`
2. **Environment variable**: `AURORA_SOAR_MODEL` / `AURORA_SPAWN_MODEL`
3. **Config file**: `soar_default_model` in aurora config
4. **Default value** (lowest priority): `"sonnet"`

**Reference implementation** (from `aur soar` in `soar.py:343-349`):
```python
if model == "sonnet":  # Check if it's the Click default
    env_model = os.environ.get("AURORA_SOAR_MODEL")
    if env_model and env_model.lower() in ("sonnet", "opus"):
        model = env_model.lower()
    elif cli_config and cli_config.soar_default_model:
        model = cli_config.soar_default_model
```

**Tool resolution** follows same pattern:
1. CLI flag: `--tool cursor` or `-t claude`
2. Environment variable: `AURORA_SOAR_TOOL` / `AURORA_SPAWN_TOOL`
3. Config file: `soar_default_tool`
4. Default: `"claude"`

This ensures:
- Users can override per-invocation via CLI flags
- Teams can set defaults via environment/config
- Works with 20+ supported CLI tools (claude, cursor, etc.)

---

## Appendix A: What We Learned from Zeroshot

**Analyzed**: https://github.com/covibes/zeroshot

**NOT NEEDED** (adds complexity without benefit for our use case):
- Message bus between agents (~800 lines)
- Trigger/hook event system (~600 lines)
- Conductor pattern with two-tier models
- SQLite message persistence
- Stream-JSON output format (chaotic for parallel)
- Docker/worktree isolation
- Context truncation strategies

**CONFIRMED** (our simple approach is correct):
- Subprocess spawning with `asyncio.create_subprocess_exec()`
- `asyncio.gather()` for parallelism with semaphore limiting
- Capture stdout/stderr, handle timeouts
- CLI-agnostic: tool + flags from config (supports 20+ tools)
- Stream text output to keep user informed

**Total spawner code**: ~50 lines (vs Zeroshot's 5,000+)

---

## Appendix B: Agent Discovery Clarification

**Two systems exist:**

| System | Location | Status |
|--------|----------|--------|
| `aurora_cli/agent_discovery/` | PRD-0021 | **KEEP** |
| `aurora_soar/agent_registry.py` | Original | **DEPRECATE** |

The CLI agent_discovery module is more capable:
- Multi-source scanning (multiple directories)
- Markdown file parsing with frontmatter
- Cached manifest with auto-refresh
- `AgentRecommender` for capability matching

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-09 | Initial PRD |
| 2.0 | 2026-01-09 | Merged with execution PRD, added SOAR wiring, AgentRegistry deprecation, LLM fallback for matching, TDD requirement, sprint structure |
| 2.1 | 2026-01-09 | Renamed `aur plan` → `aur goals`, clarified workflow: aur goals creates directory + goals.json, /plan reads goals and generates PRD/tasks/specs in same directory |
| 2.2 | 2026-01-09 | Simplified after Zeroshot analysis: removed stream-json complexity, model from config not hardcoded, added real-time text streaming, confirmed ~50 line spawner approach |
| 2.3 | 2026-01-09 | CLI-agnostic: follows `aur soar` pattern with `CLIPipeLLMClient` - tool resolved from flag/env/config, prompt piped via stdin, works with 20+ tools |
| 2.4 | 2026-01-09 | Resolved open questions: Q2 (concurrency=5, configurable), Q3 (model resolution flow documented) |

---

**Next Steps**:
1. Review and approve this PRD
2. Delete duplicate PRD file
3. Generate tasks with `@2-generate-tasks`
4. Begin Sprint 1 following TDD workflow
