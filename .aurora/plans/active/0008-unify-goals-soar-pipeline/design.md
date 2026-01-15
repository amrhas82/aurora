# Design: Unify Goals with SOAR Pipeline

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         aur goals                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │search_memory_for │  │ PlanDecomposer   │  │ AgentRecommender │  │
│  │_goal()           │  │ .decompose()     │  │ .recommend()     │  │
│  │                  │  │                  │  │                  │  │
│  │ Returns:         │  │ Calls SOAR but   │  │ Separate logic   │  │
│  │ (path, score)    │  │ loses context    │  │ from verify      │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                     │             │
│           └─────────────────────┴─────────────────────┘             │
│                                 │                                   │
│                                 ▼                                   │
│                    ┌──────────────────────┐                        │
│                    │   FilePathResolver   │                        │
│                    │   (post-hoc, poor)   │                        │
│                    └──────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         aur soar                                     │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌─────────┐       │
│  │ Phase 1 │ │ Phase 2 │ │ Phase 3  │ │Phase 4 │ │ Phase 5 │ ...   │
│  │ Assess  │→│Retrieve │→│Decompose │→│ Verify │→│ Collect │       │
│  │         │ │         │ │          │ │        │ │         │       │
│  │complexity│ │CodeChunk│ │+context  │ │+agents │ │execute  │       │
│  └─────────┘ └─────────┘ └──────────┘ └────────┘ └─────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

**Problem**: Goals reimplements phases 2-4 with inferior results.

## Unified Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SOAROrchestrator                                  │
│                                                                      │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐                   │
│  │ Phase 1 │ │ Phase 2 │ │ Phase 3  │ │Phase 4 │                   │
│  │ Assess  │→│Retrieve │→│Decompose │→│ Verify │                   │
│  └─────────┘ └─────────┘ └──────────┘ └────────┘                   │
│       │           │            │            │                       │
│       │           │            │            │                       │
│       ▼           ▼            ▼            ▼                       │
│  ┌────────────────────────────────────────────────┐                │
│  │              plan_only() stops here            │                │
│  │                                                │                │
│  │  Returns: PlanResult                           │                │
│  │    - subgoals (from Phase 3)                   │                │
│  │    - agent_assignments (from Phase 4)          │                │
│  │    - file_resolutions (from Phase 2 chunks)    │                │
│  │    - complexity (from Phase 1)                 │                │
│  │    - code_context (from Phase 2)               │                │
│  └────────────────────────────────────────────────┘                │
│                          │                                          │
│       ┌──────────────────┼──────────────────┐                      │
│       │                  │                  │                      │
│       ▼                  ▼                  ▼                      │
│  ┌─────────┐       ┌──────────┐       ┌─────────┐                 │
│  │aur goals│       │aur soar  │       │aur spawn│                 │
│  │         │       │          │       │(future) │                 │
│  │plan_only│       │full pipe │       │plan_only│                 │
│  └─────────┘       └──────────┘       └─────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

## New Data Structures

### PlanResult

```python
@dataclass
class PlanResult:
    """Result from plan_only() - phases 1-4 without execution."""

    # From Phase 1
    complexity: str  # SIMPLE, MEDIUM, COMPLEX, CRITICAL

    # From Phase 2
    code_chunks: list[CodeChunk]  # Actual code context
    file_resolutions: dict[str, list[FileResolution]]  # Derived from chunks

    # From Phase 3
    subgoals: list[Subgoal]
    context_summary: str | None  # What LLM saw

    # From Phase 4
    agent_assignments: dict[str, str]  # subgoal_id -> agent_id
    agent_gaps: list[AgentGap]  # Missing specialists

    # Metadata
    decomposition_source: str  # "soar" or "heuristic"
    phases_completed: list[str]
    timing_ms: dict[str, float]
```

### FileResolution from CodeChunk

```python
def _build_file_resolutions(
    phase2: dict[str, Any],
    phase4: dict[str, Any],
) -> dict[str, list[FileResolution]]:
    """Build file resolutions from Phase 2 code chunks.

    Maps each subgoal to relevant code chunks based on:
    1. Keyword overlap between subgoal description and chunk content
    2. File path relevance
    3. Chunk activation scores
    """
    code_chunks = phase2.get("code_chunks", [])
    subgoals = phase4.get("subgoals", [])

    resolutions = {}
    for subgoal in subgoals:
        subgoal_id = subgoal.get("id", subgoal.get("subgoal_index"))
        description = subgoal.get("description", "")

        # Score each chunk against this subgoal
        scored_chunks = []
        for chunk in code_chunks:
            score = _compute_relevance(description, chunk)
            if score > 0.3:  # Threshold
                scored_chunks.append((chunk, score))

        # Convert top chunks to FileResolution
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        resolutions[subgoal_id] = [
            FileResolution(
                path=chunk.file_path,
                line_start=chunk.line_start,
                line_end=chunk.line_end,
                confidence=score,
            )
            for chunk, score in scored_chunks[:5]
        ]

    return resolutions
```

## Implementation

### SOAROrchestrator.plan_only()

```python
def plan_only(
    self,
    query: str,
    context_files: list[Path] | None = None,
    skip_phases: list[str] | None = None,
) -> PlanResult:
    """Execute planning phases (1-4) without agent execution.

    This method provides the same quality context and decomposition
    as full SOAR queries, but stops before executing agents.

    Args:
        query: Goal description
        context_files: Optional explicit context files
        skip_phases: Phases to skip (for testing)

    Returns:
        PlanResult with subgoals, agents, and file resolutions
    """
    timing = {}

    # Phase 1: Assess complexity
    if "assess" not in (skip_phases or []):
        start = time.time()
        phase1 = self._phase1_assess(query)
        timing["phase1_assess"] = (time.time() - start) * 1000
        complexity = phase1["complexity"]
    else:
        complexity = "MEDIUM"

    # Phase 2: Retrieve context
    if "retrieve" not in (skip_phases or []):
        start = time.time()
        phase2 = self._phase2_retrieve(query, complexity)
        timing["phase2_retrieve"] = (time.time() - start) * 1000

        # Inject explicit context files if provided
        if context_files:
            phase2 = self._inject_context_files(phase2, context_files)
    else:
        phase2 = {"code_chunks": [], "reasoning_chunks": []}

    # Phase 3: Decompose with full context
    start = time.time()
    phase3 = self._phase3_decompose(query, phase2, complexity)
    timing["phase3_decompose"] = (time.time() - start) * 1000

    # Phase 4: Verify + assign agents
    start = time.time()
    decomposition = phase3.get("decomposition", {})
    phase4 = self._phase4_verify(decomposition)
    timing["phase4_verify"] = (time.time() - start) * 1000

    # Build file resolutions from Phase 2 chunks
    file_resolutions = self._build_file_resolutions(phase2, phase4)

    return PlanResult(
        complexity=complexity,
        code_chunks=phase2.get("code_chunks", []),
        file_resolutions=file_resolutions,
        subgoals=phase4.get("subgoals", []),
        context_summary=phase3.get("context_summary"),
        agent_assignments=phase4.get("agent_assignments", {}),
        agent_gaps=phase4.get("agent_gaps", []),
        decomposition_source=phase3.get("source", "soar"),
        phases_completed=["assess", "retrieve", "decompose", "verify"],
        timing_ms=timing,
    )
```

### Simplified goals.py

```python
@click.command(name="goals")
@click.argument("goal")
@click.option("--context", "-c", "context_files", multiple=True, type=Path)
@click.option("--verbose", "-v", is_flag=True)
def goals_command(goal: str, context_files: tuple[Path], verbose: bool):
    """Decompose goal into subgoals with agent assignments."""

    config = load_config()

    # Initialize SOAR orchestrator
    store = _get_store(config)
    orchestrator = SOAROrchestrator(
        store=store,
        config=config,
        agent_registry=get_agent_registry(),
    )

    # Execute phases 1-4 only
    console.print(f"[bold]Planning:[/] {goal}")
    plan_result = orchestrator.plan_only(
        query=goal,
        context_files=list(context_files) if context_files else None,
    )

    if verbose:
        console.print(f"[dim]Complexity: {plan_result.complexity}[/]")
        console.print(f"[dim]Code chunks: {len(plan_result.code_chunks)}[/]")
        console.print(f"[dim]Subgoals: {len(plan_result.subgoals)}[/]")

    # Write goals.json
    goals_json = _convert_to_goals_json(plan_result)
    output_path = Path(".aurora/soar/goals.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(goals_json, indent=2))

    console.print(f"[green]Created {output_path}[/]")
```

## Code to Delete

After unification, these become dead code:

| File | Lines | Reason |
|------|-------|--------|
| `planning/decompose.py` | ~200 | Use SOAR decompose |
| `planning/agents.py` | ~300 | Use SOAR verify |
| `planning/memory.py` (partial) | ~100 | Keep FilePathResolver for spawn |
| `planning/core.py` (partial) | ~800 | Simplify to format conversion |

**Estimated deletion**: ~1200 lines

## Migration Path

### Phase 1: Add plan_only() to SOAR

1. Add `PlanResult` dataclass
2. Implement `plan_only()` method
3. Add `_build_file_resolutions()` helper
4. Unit tests for new method

### Phase 2: Wire goals to SOAR

1. Modify `goals_command()` to call `orchestrator.plan_only()`
2. Add format conversion `_convert_to_goals_json()`
3. Integration test: goals output unchanged

### Phase 3: Delete redundant code

1. Remove `PlanDecomposer` class
2. Remove `AgentRecommender` class
3. Simplify `planning/core.py`
4. Update imports

### Phase 4: Enhance file resolutions

1. Improve `_build_file_resolutions()` scoring
2. Add subgoal-to-chunk relevance matching
3. Integration test: file resolution quality

## Testing Strategy

### Existing Tests (Must Pass)

- `tests/unit/soar/` - SOAR phase tests
- `tests/integration/test_goals.py` - Goals output format

### New Tests

```python
def test_plan_only_returns_code_chunks():
    """plan_only() should return actual code chunks from Phase 2."""
    orchestrator = SOAROrchestrator(store=indexed_store)
    result = orchestrator.plan_only("Add authentication")

    assert len(result.code_chunks) > 0
    assert all(hasattr(c, "content") for c in result.code_chunks)


def test_goals_sees_code_context():
    """Goals decomposition should have access to code context."""
    # Run goals with verbose to see context summary
    result = runner.invoke(goals_command, ["Add auth", "-v"])

    assert "Code chunks:" in result.output
    assert "0" not in result.output  # Should have chunks


def test_file_resolutions_from_retrieval():
    """File resolutions should come from Phase 2, not post-hoc search."""
    orchestrator = SOAROrchestrator(store=indexed_store)
    result = orchestrator.plan_only("Refactor API")

    # Resolutions should have high confidence (from actual retrieval)
    for subgoal_id, resolutions in result.file_resolutions.items():
        assert all(r.confidence > 0.5 for r in resolutions)
```

## Rollback Plan

If issues arise:
1. `plan_only()` is additive - doesn't change existing SOAR
2. Goals can fall back to old path via feature flag
3. Old code preserved in git history
