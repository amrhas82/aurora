# Aurora Features Backlog

## Strategic Focus

**Aurora's value**: Planning layer (gap detection, pre-execution review) that LangChain/CrewAI/ADK don't provide.

**Differentiator:**
- They solve: "How to coordinate agents talking"
- Aurora solves: "How to reliably execute agent plans with oversight and recovery"

---

## TODO: Dependency-Aware Execution

**Problem:** Subgoals have `depends_on` field but execution ignores it. All agents spawn in parallel. Output from agent A not passed to dependent agent B.

**What exists:**
- `depends_on` field in subgoal schema
- `verify.py` validates no circular dependencies
- `spawn_sequential` with `pass_context=True` (accumulates outputs)

**What's missing:**
- `collect.py` ignores `depends_on`, spawns all parallel
- No topological sort by dependency level
- No output passing between dependent subgoals

**Example:**
```
sg-1 (no deps)             <- Wave 1
sg-2 (depends on sg-1)     <- Wave 2: gets sg-1 output
sg-3 (depends on sg-1)     <- Wave 2: parallel with sg-2
sg-4 (depends on sg-2, sg-3) <- Wave 3: gets both outputs
```

**Solution (~50 LOC in collect.py):**
```python
waves = topological_sort(subgoals)
outputs = {}

for wave in waves:
    wave_outputs = await spawn_parallel_tracked(wave_tasks, max_concurrent=4)
    for idx, output in zip(wave_indices, wave_outputs):
        outputs[idx] = output
    # Inject outputs into next wave's context
```

**Effort:** Low. Infrastructure exists, needs wiring.

---

## Not Building

| Feature | Why |
|---------|-----|
| Generic flow configs | Over-engineering trap |
| Graph DSL | Aurora rejects framework feature parity |
| Complex state objects | Subgoal outputs as strings is sufficient |
| Multi-turn conversation | MCP is stateless by design |

---

**Last Updated:** January 19, 2026
