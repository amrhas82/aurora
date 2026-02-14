# Feature Backlog

Parked features and future work. Items here are validated ideas that aren't urgent.
When a real use case appears, promote to a PRD.

---

## SOAR: Dependency-Aware Collect Phase (PRD 0030 — unfinished)

**What:** SOAR's collect phase (`execute_agents()` in `collect.py`) ignores `depends_on` — spawns all subgoals in parallel regardless of dependencies.

**PRD:** `tasks/0030-prd-dependency-aware-execution.md` (fully specced, approved)

**What exists today:**
- `implement/topo_sort.py` — Kahn's algorithm returning parallel-safe waves (used by `aur spawn`)
- `collect.py:topological_sort()` — separate topo sort for SOAR subgoals (exists but `execute_agents` doesn't use it)

**What's missing (from PRD 0030):**
- Wire `topological_sort()` into `execute_agents()` for wave-based execution
- Context passing between waves (spawn_sequential format with ✓/✗ markers)
- Partial failure handling: dependents get partial context + WARNING footer when some deps fail
- `verify_lite` validation that `depends_on` refs point to existing subgoals (~5 LOC)
- Progress display: `Wave X/Y (N subgoals)...` with ✓/✗/⚠ markers
- All test scenarios from PRD Section 9

**Effort:** ~2 days (PRD estimates 60 LOC in collect.py + 5 LOC in verify.py + ~140 LOC tests)

**Trigger:** When SOAR queries regularly produce subgoals with `depends_on` and results suffer from missing context.

---

## aur spawn: Partial Failure Handling

**What:** When a dependency fails in wave execution, dependents currently get no failure context. PRD 0030 specced ✓/✗/⚠ markers and WARNING footers.

**Current behavior:** `_build_dependency_context()` in `spawn.py` only forwards successful outputs. Failed deps are silently missing.

**Desired behavior:**
- `✓ [Task 1.0]: <output>` for successes
- `✗ [Task 2.0]: FAILED - <error>` for failures
- `WARNING: 1/3 dependencies failed. Proceed with available context.` footer
- `⚠` marker in progress display for tasks running with partial context

**Effort:** ~0.5 day

**Trigger:** When spawn is used for real workflows where partial failure recovery matters.

---

## aur spawn: Scope Creep / Budget Tracking

**What:** Spawn has no cost awareness. Long-running waves can burn tokens without limits.

**Missing:**
- Per-run cost estimation before execution
- Budget cap that aborts remaining waves if exceeded
- Cost summary in `summary.json` persistence

**Related:** MVP Feature #4 (Cost Budgets) in `tasks/MVP-10-FEATURES.md`

**Trigger:** When spawn is used for expensive multi-agent workflows.

---

## aur spawn: Streaming Progress Display

**What:** PRD 0030 Section 6.6 specced detailed streaming output with agent names, timing, and dependency context info.

**Current:** Basic `✓ Task 1.0: Success` / `✗ Task 1.0: Failed` output.

**Desired (from PRD):**
```
Wave 2/3 (2 subgoals)...
  ✓ [2.0] Write unit tests
    └─ Agent: quality-assurance (45s)
  ⚠ [3.0] Create CLI wrapper
    └─ Agent: code-developer (74s)
    └─ Context: 1/1 dependencies (✓ 1.0)
```

**Effort:** ~0.5 day

**Trigger:** When spawn output feels too sparse for debugging real executions.

---

## SOAR as Execution Engine (Original Vision)

**What:** Make SOAR not just answer questions but execute multi-step workflows — the "brain + hands" combo.

**Current state:**
- SOAR decomposes, verifies, routes to agents, collects results, synthesizes an *answer*
- `aur spawn` executes tasks but has no brain (no memory, no verification, no reasoning)

**The gap:** No single command does "think about how to do X, then actually do X."

**What it would take:**
- SOAR's collect phase actually executes tasks (not just research agents)
- Action agents that can edit files, run commands, create PRs
- Verification loop after execution (did the action succeed?)
- Budget/scope controls (don't let it run wild)

**Effort:** Large (weeks). This is a product direction decision, not a feature.

**Trigger:** When the team decides Aurora should be an autonomous coding agent, not just a reasoning layer.

---

## MVP Features Not Yet Implemented

From `tasks/MVP-10-FEATURES.md`:

| # | Feature | Status | Effort |
|---|---------|--------|--------|
| 1 | LLM Preference Routing | Not started | Low-Medium |
| 2 | Timing Logs (% breakdown) | Not started | Low |
| 3 | Guardrails (PII, length, format) | Not started | Medium |
| 4 | Cost Budgets | Partial (`aur budget` exists) | Medium |
| 5 | Self-Correction Loop Clarification | Not started | Low (docs only) |
| 6 | Headless Mode | Removed (v0.16.0) | — |
| 7 | Memory Integration Modes | Partial (`aur mem search` exists) | Medium |
