# Aurora Features Backlog

## Strategic Focus

**Aurora's value**: Planning layer (gap detection, pre-execution review) that LangChain/CrewAI/ADK don't provide.

**Differentiator:**
- They solve: "How to coordinate agents talking"
- Aurora solves: "How to reliably execute agent plans with oversight and recovery"

---


## Ideas to Steal: subtask

**Repo:** https://github.com/zippoxer/subtask

**What it does:** Parallel task management for Claude Code using Git worktrees, interactive agent communication, and TUI for progress visualization.

**Limitation:** Claude Code-only (not multi-tool compatible) - significant loss for Aurora's 20+ tool support.

**Ideas worth stealing (if adaptable to multi-tool):**

1. **Git Worktree Isolation** (~150 LOC)
   - Each parallel task gets isolated worktree: `git worktree add ../task-{id} -b task-{id}`
   - Prevents file conflicts during parallel execution
   - Selective merge per task (better code review)
   - Could add `--worktree` flag to `aur spawn`

2. **Interactive Agent Communication** (~100 LOC)
   - Main agent can interrupt and communicate with running subagents
   - Progress callbacks: check status, provide feedback, course-correct
   - Huge improvement over fire-and-forget spawning
   - Could add `--interactive` flag to `spawn_parallel_tracked`

3. **Task State Persistence** (~50 LOC)
   - Tasks survive crashes/restarts
   - Stored in folders: `.aurora/tasks/{task_id}/state.json`
   - Track: status, conversation, output, timestamps
   - Critical for long-running (hours/days) workflows

4. **Terminal UI (TUI)** (~150 LOC)
   - Visual progress across all parallel tasks
   - Show diffs, conversations, status at-a-glance
   - Better than streaming CLI logs
   - Could use Rich or Textual library

**Compatibility with Aurora:**
- ✅ Works with dependency-aware execution (PRD 0030)
- ✅ Could enhance wave-based spawning with worktree isolation
- ✅ Interactive communication fits SOAR collect phase
- ❌ Requires adaptation for multi-tool support (not just Claude Code)

**Effort:** Medium-High (~400-450 LOC total if adapted for multi-tool)

**Decision:** Only consider if we can adapt to work with cursor, aider, gemini, etc. Claude Code-only is a non-starter.

---

## Not Building

| Feature | Why |
|---------|-----|
| Generic flow configs | Over-engineering trap |
| Graph DSL | Aurora rejects framework feature parity |
| Complex state objects | Subgoal outputs as strings is sufficient |
| Multi-turn conversation | MCP is stateless by design |

---

**Last Updated:** January 21, 2026
