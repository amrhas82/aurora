# Aurora Features Backlog

## Strategic Focus

**Aurora's unique value**: Planning layer (gap detection, pre-execution review) that frameworks like LangChain/CrewAI/ADK don't provide.

**Core differentiator:**
- They solve: "How to coordinate agents talking"
- Aurora solves: "How to reliably execute agent plans with human oversight and automatic recovery"

**What to build**: Context-aware decomposition, approval gates, execution recovery
**What NOT to build**: Generic flow configs, multi-turn conversation state, framework feature parity

---

## The 5 Infrastructure Pillars

These are the core execution infrastructure components. Two parallel work streams.

### Priority & Status

| Priority | Pillar | Status | Effort | Stream |
|----------|--------|--------|--------|--------|
| **1st** | Context Injection | **COMPLETE** | Low | 1 |
| **2nd** | Memory-Informed Decomposition | **COMPLETE** | Medium | 1 |
| **3rd** | Approval Gates | 20% exists | High | 2 |
| **4th** | Exception Policies | 10% exists | High | 2 |
| **5th** | Execution Recovery | 30% exists | High | 2 |

### Dependency Graph

```
Stream 1 (quick wins):     Stream 2 (new infrastructure):
Context ──► Decomposition  Gates ──► Policies
                                └──► Recovery
```

---

## Stream 1: Context & Decomposition

### Pillar 1: Context Injection

**Status:** COMPLETE (Jan 2026)

**What was fixed:**
- `--context` flag now works on `aur soar` command
- `_build_context()` loads context files via `MemoryRetriever.load_context_files()`
- Context files are injected into phase 2 results in SOAR orchestrator
- `CodeChunk` objects properly handled in simple query path
- JSON serialization fixed for conversation logging

**Files modified:**
- `packages/cli/src/aurora_cli/planning/decompose.py` - wired context loading
- `packages/cli/src/aurora_cli/commands/soar.py` - added --context flag
- `packages/soar/src/aurora_soar/orchestrator.py` - context injection + CodeChunk handling
- `packages/core/src/aurora_core/logging/conversation_logger.py` - ChunkAwareEncoder

---

### Pillar 2: Memory-Informed Decomposition

**Status:** COMPLETE (Jan 2026)

**What was fixed:**
- `_build_context()` ALWAYS queries memory (not just as fallback)
- `_build_context_summary()` reads ACTUAL CODE from files (top 7 chunks)
- Remaining chunks get docstrings/signatures
- LLM sees real implementation, not just file names

**Context summary now includes:**
```
### code: PlanDecomposer
File: planning/decompose.py
\`\`\`python
class PlanDecomposer:
    def __init__(self, config=None, store=None):
        self.config = config
        self.store = store
        # ... actual code
\`\`\`
```

**Files modified:**
- `packages/cli/src/aurora_cli/planning/decompose.py` - always query memory
- `packages/soar/src/aurora_soar/phases/decompose.py` - read actual file content

---

## Stream 2: Gates, Policies, Recovery

### Pillar 3: Approval Gates

**Status:** 20% exists (plan checkpoint only)

**Problem:** Execution is all-or-nothing. No pause points between phases.

**What exists:**
- `prompt_for_confirmation()` in `planning/checkpoint.py`
- `--yes` / `--non-interactive` flags

**What's missing:**
- No gates during SOAR execution
- No destructive operation detection
- No anomaly detection

**What matters: Phased Execution with Approval Gates**

Current flow:
```
goals → approve → execute all
```

Better flow:
```
goals → approve → execute sg-1 → approve → sg-2 → approve → sg-3
```

**Implementation:**
```bash
aur spawn tasks.md --checkpoint-after-each
  → Agent 1 completes
  → Shows output
  → "Approve to continue? [Y/n]"
  → Agent 2 starts
```

**Gates needed:**

| Location | Default | Description |
|----------|---------|-------------|
| After decomposition | ON | Review plan before execution |
| Before destructive ops | ON | "About to delete file. Proceed?" |
| On anomaly | ON | "Found 47 files, expected ~10. Continue?" |
| Between phases | Optional | Phase-by-phase approval |

**CLI:**
```bash
aur soar "goal" --approve=all|destructive|none
aur spawn tasks.md --checkpoint-after-each
```

**This is approval gates, not conversation** - infrastructure already exists in spawner.

---

### Pillar 4: Exception Policies

**Status:** 10% exists (budget only)

**Problem:** No guardrails for dangerous operations.

**What exists:**
- Budget hard limit at 100%

**What's missing:**
- No "never rm -rf" rules
- No user-configurable policies
- No boundary enforcement

**Solution:**
```yaml
# .aurora/policies.yaml
destructive_operations:
  file_delete: prompt
  git_force_push: deny
boundaries:
  - "Never modify /vendor"
  - "Never modify /.git"
thresholds:
  max_files_modified: 20
  max_files_deleted: 5
```

**Validation points:**
- Before agent execution
- During spawner task processing
- At quality gates

---

### Pillar 5: Execution Recovery

**Status:** 30% exists

**Problem:** If step 7 fails, lose all progress. No way to resume partial work.

**What exists:**
- Plan lifecycle states (ACTIVE/ARCHIVED)
- Spawner retry/fallback
- Task status tracking

**What's missing:**
- No mid-execution checkpoint persistence
- No `--resume` flag
- No failure analysis

**Recovery strategies when agent fails:**

```
Agent execution failure:
├─ Save partial progress (what worked so far)
├─ Analyze failure (what went wrong)
├─ Recovery options:
│   ├─ Retry same agent (transient error)
│   ├─ Try different agent (capability mismatch)
│   ├─ Re-decompose subgoal (task too complex)
│   └─ Skip and continue (non-blocking failure)
```

**Dependency-aware recovery:**

```
Subgoal graph:
sg-1 (no deps)
sg-2 (depends on sg-1)
sg-3 (depends on sg-1)
sg-4 (depends on sg-2, sg-3)

If sg-2 fails:
├─ sg-3 can still run (independent)
├─ sg-4 is blocked (dependency)
├─ Options: retry sg-2 or re-plan sg-4 to not need sg-2
```

**Quality gates integration:**

```
Agent completes subgoal:
├─ Validate output exists
├─ Check against acceptance criteria
├─ Run tests if applicable
├─ Decision:
│   ├─ PASS → continue
│   ├─ FAIL → retry or re-plan
```

**Requires:** Pillar 3 (gates define checkpoint locations)

**CLI:**
```bash
aur soar --resume <execution-id>
aur soar --status <execution-id>
aur spawn tasks.md --checkpoint-after-each --resume-from=3
```

**This is automatic recovery, not human-in-loop questions** - smart orchestration, not conversation.

---

## Problem Statement (Refined)

**Version 2 - What Aurora Actually Solves:**

"Reliable phased execution of multi-agent plans with:
- Approval gates between phases (not mid-work questions)
- Automatic recovery on failures (not manual intervention)
- Partial progress preservation (save what worked)
- Plan adaptation when blocked (re-decompose, not ask user)"

**What we're RIGHT about:**
1. ✅ Agent routing & gap detection - Valuable and unique
2. ✅ Flow understanding & pre-execution review - Better than frameworks
3. ✅ Recovery + guardrails - Critical missing piece

**What we're WRONG about:**
1. ❌ Multi-turn interactive conversation - Weak use cases, solution seeking problem
2. ❌ Generic flow configs - Over-engineering trap

---

## Not Building

| Feature | Why Rejected |
|---------|--------------|
| Generic flow configs | Over-engineering trap, adds complexity without value |
| Multi-turn conversation state | Weak use cases, MCP is stateless by design |
| Framework feature parity | Competing on integrations is losing game |
| Interactive debugging mid-task | Approval gates solve this better |

---

## Completed

### Agent Gap Detection ✅ (Jan 2026)

Binary comparison: `ideal_agent != assigned_agent` → gap detected.
- Single LLM call outputs both ideal and assigned
- Ad-hoc spawning when ideal agent missing
- Infrastructure working in production

---

**Last Updated:** January 13, 2026
