# Aurora Planning System: Strategic Specifications

**Purpose**: Define WHAT we're building across 3 phases (not implementation details). Each phase = 1 sprint with its own PRD.

**Version**: 2.0 (Refactored based on OpenSpec port reality)
**Date**: January 2, 2026
**Status**: Planning

---

## CONTEXT: What We Have Now

### ✅ Completed (PRD 0016)
- Agent Discovery: Multi-source scanning (`~/.claude/agents/`, etc.)
- Agent Manifest: Cached, auto-refreshed, searchable
- Memory Infrastructure: `MemoryRetriever` with `--context` support
- CLI Commands: `aur agents list/search/show/refresh`
- **91 tests pass, 85%+ coverage**

### ✅ Completed (PH0.5 OpenSpec Port)
- **284 tests passing** in `/tmp/openspec-source/`
- Core systems: Schemas, Validation, Parsers, Commands (archive/update/list/view/init)
- Templates: AGENTS.md, project.md
- Slash commands: `/openspec:*` for Claude Code
- **Repository**: `https://github.com/amrhas82/OpenSpec` branch `refactored`

### ❌ Missing (Critical Gaps)
1. **Slash commands for aur**: No `/aur:query`, `/aur:plan`, `/aur:implement`
2. **Multi-tool configurators**: OpenCode, AmpCode, Claude Code configs
3. **Planning integration**: OpenSpec refactored code NOT integrated into Aurora
4. **Execution system**: No agent orchestration for plan execution

---

## THE 3-PHASE STRATEGY

### Overview

| Phase | Name | Sprint Goal | Key Deliverable |
|-------|------|-------------|-----------------|
| **Phase 1** | Foundation | Slash commands + Planning basics | `/aur:plan` generates 4 files |
| **Phase 2** | Intelligence | Code-aware tasks + Tool configs | Tasks with file paths from memory |
| **Phase 3** | Execution | Agent orchestration + Tracking | `/aur:implement` delegates to agents |

**Each phase gets its own PRD** with detailed requirements, testing strategy, acceptance criteria.

---

## PHASE 1: SLASH COMMANDS & PLANNING FOUNDATION

### Goals

1. **Slash command infrastructure**: `/aur:*` commands working in Claude Code, OpenCode, AmpCode
2. **Planning basics**: Generate structured plans with 4-file workflow
3. **OpenSpec integration**: Port refactored OpenSpec as `aurora.planning` package

### What We're Building

#### 1.1 Slash Command System

**Problem**: aur commands require CLI context switching. MCP integration failed.

**Solution**: Slash commands for ALL aur operations

**Commands to Support**:
- `/aur:query` - Memory retrieval with `--context` flag
- `/aur:plan` - Generate plan from goal
- `/aur:archive` - Archive completed plan
- `/aur:list` - List active/archived plans
- `/aur:view` - Show plan dashboard
- `/aur:implement` - Execute plan (Phase 3)

**Tool Configurators** (from OpenSpec refactored):
- Claude Code: `~/.config/Claude/claude_desktop_config.json` (Linux)
- OpenCode: Configuration file format TBD
- AmpCode: Configuration file format TBD

**Design Principles**:
- Slash commands delegate to CLI (`/aur:query` → `aur query`)
- Arguments passed through (e.g., `/aur:query --context file.py "search term"`)
- Streaming output to chat interface
- Error messages with actionable suggestions

#### 1.2 Planning Package Integration

**Problem**: OpenSpec refactored code sits in `/tmp/openspec-source/`, not integrated

**Solution**: Create `aurora.planning` package from refactored OpenSpec

**Package Structure**:
```
packages/planning/
├── src/aurora_planning/
│   ├── commands/        # archive, init, list, update, view
│   ├── parsers/         # markdown, requirements, metadata
│   ├── schemas/         # plan, spec, validation
│   ├── templates/       # AGENTS.md, project.md
│   ├── validators/      # plan validators, requirement validators
│   └── config.py        # Planning-specific config
└── tests/
    └── unit/            # 284 tests from OpenSpec port
```

**Integration Points**:
- CLI: `aur plan create/list/view/archive` commands
- Slash: `/aur:plan`, `/aur:list`, `/aur:view`, `/aur:archive`
- Config: Extend `aurora_cli/config.py` with planning settings

**Naming Changes from OpenSpec**:
- `openspec/` → `.aurora/plans/`
- `changes/` → `active/`
- `specs/` → `capabilities/` (future - NOT Phase 1)
- Keep: `archive/` with `YYYY-MM-DD-plan-id` format

#### 1.3 The 4-File Workflow

**Files Generated per Plan**:

1. **plan.md**: High-level decomposition (SOAR output in Phase 2, manual in Phase 1)
   - Goal statement
   - Subgoals (numbered, with descriptions)
   - Agent assignments (manual in Phase 1, auto in Phase 2)
   - Dependencies between subgoals

2. **prd.md**: Detailed requirements (OpenSpec format)
   - Executive summary
   - Functional requirements (FR-N.M format)
   - Acceptance criteria per requirement
   - Testing strategy

3. **tasks.md**: Implementation checklist
   - Tasks grouped by subgoal
   - Checkbox format: `- [ ] Task description`
   - File paths (generic in Phase 1, memory-aware in Phase 2)

4. **agents.json**: Machine-readable metadata
   ```json
   {
     "plan_id": "0001-oauth-auth",
     "goal": "Implement OAuth2 authentication",
     "status": "active",
     "created_at": "2026-01-15T10:00:00Z",
     "subgoals": [
       {
         "id": "sg-1",
         "title": "Research OAuth providers",
         "agent_id": "@market-researcher",
         "status": "pending"
       }
     ]
   }
   ```

**Plan ID Format**: `NNNN-slug` (e.g., `0001-oauth-auth`)
- NNNN: Auto-incrementing 4-digit number
- slug: Kebab-case from goal (max 30 chars)

**Lifecycle States**: `active` → `archived`

#### 1.4 Commands to Implement

**`/aur:plan` (or `aur plan create`)**:
```bash
/aur:plan "Implement OAuth2 authentication"
# Generates: ~/.aurora/plans/active/0001-oauth-auth/
#   - plan.md (template-based in Phase 1)
#   - prd.md (OpenSpec format)
#   - tasks.md (generic tasks)
#   - agents.json (metadata)
```

**`/aur:list` (or `aur plan list`)**:
```bash
/aur:list
# Output:
# Active Plans:
#   0001-oauth-auth     2/5 tasks (40%)    2h ago
#   0002-logging-system 0/8 tasks (0%)     1d ago
# Archived: 3 plans
```

**`/aur:view` (or `aur plan view <plan-id>`)**:
```bash
/aur:view 0001
# Output: Dashboard with:
#   - Summary (goal, status, progress)
#   - Subgoals with task counts
#   - Agent assignments
```

**`/aur:archive` (or `aur plan archive <plan-id>`)**:
```bash
/aur:archive 0001
# Moves: active/0001-oauth-auth/ → archive/2026-01-15-0001-oauth-auth/
# Updates: agents.json with archived_at timestamp
```

### Phase 1 Success Criteria

- [ ] Slash commands work in Claude Code, OpenCode, AmpCode
- [ ] `/aur:query` delegates to `aur query` with all flags
- [ ] `/aur:plan` generates 4-file structure
- [ ] `aurora.planning` package integrated with 284 tests passing
- [ ] Plan ID auto-increment works (finds next available number)
- [ ] Archive preserves timestamp and plan ID
- [ ] Configuration files generated for all 3 tools

### Phase 1 Non-Goals (Deferred to Phase 2/3)

- ❌ SOAR decomposition (plan.md is manual template in Phase 1)
- ❌ Agent discovery integration (agents assigned manually)
- ❌ Memory-aware file paths (tasks use generic paths)
- ❌ Code-aware task generation
- ❌ Plan execution/implementation

---

## PHASE 2: CODE-AWARE TASKS & MULTI-TOOL CONFIG

### Goals

1. **SOAR integration**: Automatic goal decomposition
2. **Memory integration**: File path resolution from memory index
3. **Agent recommendations**: Auto-assign agents to subgoals
4. **Multi-tool configs**: Complete configurators for OpenCode, AmpCode

### What We're Building

#### 2.1 SOAR-Powered Planning

**Enhancement**: `/aur:plan` uses SOAR orchestrator for decomposition

**Flow**:
```
User: /aur:plan "Implement OAuth2 authentication"
  ↓
Step 1: SOAR Decomposition
  - Load context (memory retrieval OR --context files)
  - Call SOAROrchestrator.decompose(goal, context)
  - Generate subgoals with dependencies
  - Match agents to subgoals (from PRD 0016 manifest)
  - Detect agent gaps, suggest fallbacks
  ↓
Output: plan.md with SOAR subgoals + agent assignments
```

**Agent Recommendation**:
- Extract keywords from subgoal description
- Search agent manifest for capability matches
- Rank by keyword overlap score
- If score ≥ 0.5 → assign agent
- If score < 0.5 → mark as gap, suggest fallback

**Gap Detection**:
```json
{
  "subgoal_id": "sg-4",
  "recommended_agent": "@technical-writer",
  "agent_exists": false,
  "fallback": "@market-researcher",
  "suggested_capabilities": ["technical-writing", "api-docs"]
}
```

#### 2.2 Memory-Aware File Paths

**Enhancement**: tasks.md includes actual file paths from memory index

**Resolution Strategy**:
1. Parse requirement text for entities (class names, endpoints)
2. Query `MemoryRetriever` with tri-hybrid search
3. Return top-3 files with confidence scores
4. Suggest line ranges from file structure analysis

**Example Output**:
```markdown
## Subgoal 2: Backend Implementation (@code-developer)
- [ ] 2.1 Modify User model with OAuth fields
  - **File**: `src/models/user.py` lines 15-30 (confidence: 0.92)
  - **Changes**: Add oauth_provider, oauth_id, tokens columns
  - **Tests**: `tests/models/test_user_oauth.py` (NEW)
```

**Graceful Degradation**:
- If memory not indexed → warn, generate generic paths
- If low confidence (<0.6) → mark path with "(suggested)"
- If no match → task lacks file reference, warn user

#### 2.3 PRD Expansion Integration

**Two-Step Workflow**:

```
Step 1: Quick Plan Generation
/aur:plan "goal"
  → Generates plan.md + agents.json
  → Shows preview of subgoals

───────────── CHECKPOINT ─────────────────
"Expand to detailed PRD with tasks? (Y/n)"
───────────────────────────────────────────

Step 2 (if confirmed): Full Expansion
  → Generates prd.md (detailed requirements per subgoal)
  → Generates tasks.md (code-aware tasks with file paths)
  → Updates agents.json with all metadata
```

**Why Checkpoint?**
- User validates decomposition before expensive expansion
- Can abort if SOAR got wrong subgoals
- Single command with pause (not 3 separate commands)

#### 2.4 Complete Multi-Tool Configurators

**Status Tracking**:
- Claude Code: ✅ Done (from OpenSpec port)
- OpenCode: ❌ Need configurator
- AmpCode: ❌ Need configurator

**Configuration Files**:
- Claude Code: `~/.config/Claude/claude_desktop_config.json`
- OpenCode: `~/.config/opencode/config.json` (TBD format)
- AmpCode: `~/.config/ampcode/config.json` (TBD format)

**Commands to Configure**:
- All aur commands: query, mem index, mem search, plan, list, view, archive, implement
- Format: Slash command name, description, argument schema

### Phase 2 Success Criteria

- [ ] `/aur:plan` uses SOAR for decomposition
- [ ] Agent recommendations based on manifest (PRD 0016)
- [ ] Agent gaps detected and logged in agents.json
- [ ] tasks.md includes file paths from memory (≥80% confidence)
- [ ] Two-step workflow with checkpoint works
- [ ] OpenCode and AmpCode configurators complete
- [ ] All 3 tools have identical slash command experience

### Phase 2 Non-Goals (Deferred to Phase 3)

- ❌ Plan execution (tasks still manual)
- ❌ Agent orchestration
- ❌ Progress tracking beyond checkbox state

---

## PHASE 3: EXECUTION & AGENT ORCHESTRATION

### Goals

1. **Generic execution**: Execute tasks.md sequentially
2. **Agent orchestration**: SOAR spawns agents per subgoal
3. **Progress tracking**: Checkpoint state, pause/resume capability
4. **Results collection**: Per-subgoal output aggregation

### What We're Building

#### 3.1 Generic Task Execution (Baseline)

**Command**: `/aur:implement <plan-id>`

**Process** (Simple Version):
1. Load plan from `active/<plan-id>/`
2. Parse tasks.md for unchecked tasks
3. For each task:
   - Show task description to user
   - Prompt: "Implement this task? (Y/n/skip)"
   - If yes: User implements (manual or Claude assists)
   - Mark checkbox: `[ ]` → `[x]`
   - Save tasks.md
4. When all tasks done → prompt to archive

**State Tracking**:
```json
{
  "plan_id": "0001-oauth-auth",
  "status": "in_progress",
  "current_task": "2.3",
  "completed_tasks": ["1.1", "1.2", "2.1", "2.2"],
  "started_at": "2026-01-15T10:00:00Z"
}
```

#### 3.2 Agent-Orchestrated Execution (Advanced)

**Enhancement**: SOAR orchestrator spawns agents per subgoal

**Process**:
1. Load plan + agents.json
2. For each subgoal (respecting dependencies):
   - Check: All dependencies completed?
   - Resolve agent: Use recommended or prompt for fallback if gap
   - Spawn agent subprocess:
     ```bash
     aur agent run <agent-id> \
       --goal "<subgoal-description>" \
       --context <files> \
       --output results/sg-2/ \
       --timeout 3600
     ```
   - Collect results: `results/sg-2/implementation_log.md`, `modified_files.json`
   - Update checkboxes: Mark all tasks under subgoal as complete
   - Save checkpoint: Update state.json
3. After all subgoals → show summary, prompt to archive

**Agent Gap Handling**:
```
⚠ Agent @technical-writer not found for Subgoal 4

Options:
1) Use fallback: @market-researcher
2) Skip this subgoal
3) Abort execution

Choice: _
```

**Dependency Blocking**:
- If Subgoal 2 depends on Subgoal 1, execution waits
- If Subgoal 1 fails, Subgoal 2 is blocked (user prompted)

#### 3.3 Checkpoint & Resume

**State File**: `.aurora/plans/active/<plan-id>/state.json`

**Resume Logic**:
1. Load state.json
2. Find current_subgoal index
3. Verify dependencies still met
4. Continue from that index

**Use Cases**:
- Multi-day plans (pause overnight, resume next day)
- Failure recovery (subprocess crashes, resume from last checkpoint)
- User abort (Ctrl+C, can resume later)

#### 3.4 Execution Summary

**Output After Completion**:
```
Execution Complete!

Total Duration: 1 hour 30 minutes
Subgoals: 4 / 4 ✓
Tasks: 12 / 12 ✓
Agent Gaps: 1 (Subgoal 4 used fallback @market-researcher)

Results: ~/.aurora/plans/active/0001-oauth-auth/results/

Next steps:
1. Review agent outputs in results/
2. Run tests: pytest
3. Archive plan: /aur:archive 0001
```

### Phase 3 Success Criteria

- [ ] Generic execution: tasks.md processed sequentially
- [ ] Agent orchestration: SOAR spawns agents per subgoal
- [ ] Agent gaps handled interactively (fallback prompts)
- [ ] Dependency blocking works (Subgoal 2 waits for Subgoal 1)
- [ ] Checkpoint/resume: Can pause and resume execution
- [ ] Results collected per subgoal in `results/` directory
- [ ] Execution summary shows duration, gaps, next steps

### Phase 3 Non-Goals (Future Work)

- ❌ Parallel execution (sequential only in Phase 3)
- ❌ Advanced retry logic (simple fail = block)
- ❌ Real-time progress UI (terminal output only)

---

## CRITICAL DESIGN DECISIONS

### 1. Why Slash Commands Instead of MCP?

**MCP Issues**:
- Failed integration with Aurora
- Complex setup, unreliable connections
- Limited tool support (only Claude Code stable)

**Slash Command Benefits**:
- Native to Claude Code, OpenCode, AmpCode
- Simple delegation to CLI commands
- Streaming output works reliably
- Easy to configure (JSON config files)

**Decision**: Deprecate MCP, fully invest in slash commands

### 2. Why 4 Files (Not 1 or 2)?

**Alternatives Considered**:
- 1 file: All content in single plan.md → Rejected (hard to parse, no machine-readable metadata)
- 2 files: proposal.md + tasks.md (OpenSpec) → Rejected (no separate strategy vs requirements)

**4-File Rationale**:
- **plan.md**: Strategy (SOAR decomposition output)
- **prd.md**: Requirements (OpenSpec format, detailed)
- **tasks.md**: Tactics (implementation checklist)
- **agents.json**: Metadata (machine-readable for tooling)

**Separation of Concerns**: Human-readable (md) + Machine-readable (json)

### 3. Why Phase 1 Without SOAR?

**Rationale**:
- Validate file structure, slash commands, OpenSpec integration FIRST
- SOAR integration is complex, isolate risk to Phase 2
- Phase 1 delivers value: Manual planning with structured workflow

**Progression**:
- Phase 1: Template-based planning (validate structure)
- Phase 2: SOAR-automated planning (validate intelligence)
- Phase 3: Agent-orchestrated execution (validate automation)

### 4. Why Sequential Execution (Not Parallel)?

**Rationale**:
- Simplicity: Sequential easier to implement and debug
- Dependencies: Most subgoals have dependencies (limits parallelism)
- Resource control: Parallel agents may conflict (file locks, DB)

**Decision**: Phase 3 = sequential, parallel deferred to future work

### 5. Why Checkpoint After Decomposition?

**User Control**: Validate SOAR output before expensive PRD generation

**Workflow**:
```
Quick decomposition (5-10s) → User reviews → Confirm → Full expansion (20-30s)
```

**Avoids**: Wasted 30s on bad decomposition that user would reject

---

## INTEGRATION WITH EXISTING SYSTEMS

### PRD 0016 (Agent Discovery)

**What We Reuse**:
- `AgentManifest` API for agent validation
- `recommend_agents_for_subgoals()` for capability matching
- `detect_gaps()` for gap detection
- Agent discovery from `~/.claude/agents/`, etc.

**Integration Points**:
- Phase 2: Plan generation loads manifest, assigns agents
- Phase 3: Execution validates agents before spawning

### SOAR Orchestrator

**What We Reuse**:
- `SOAROrchestrator.decompose(goal, context, agents)` for subgoal generation
- Complexity assessment (simple/moderate/complex)
- Dependency graph validation

**Integration Points**:
- Phase 2: Plan generation calls SOAR for decomposition
- Phase 3: Execution respects SOAR dependency ordering

### Memory System

**What We Reuse**:
- `MemoryRetriever.retrieve(query, limit, mode)` for context
- `MemoryRetriever.load_context_files()` for custom files
- Tri-hybrid search (BM25 + semantic + activation)

**Integration Points**:
- Phase 2: Plan generation retrieves context for SOAR
- Phase 2: Task generation resolves file paths via memory
- All phases: `--context` flag for custom file loading

### OpenSpec Refactored Code

**Source**: `/tmp/openspec-source/` (284 tests passing)

**Migration Path**:
1. Copy to `packages/planning/src/aurora_planning/`
2. Update imports: `from aurora.planning import *`
3. Integrate with CLI: `aur plan` command group
4. Integrate with slash: `/aur:plan` configurators
5. Verify all 284 tests still pass

**Naming Changes**:
- `openspec/` → `.aurora/plans/`
- `changes/` → `active/`
- Keep: `archive/`, `YYYY-MM-DD-` prefix

---

## WHAT'S NOT IN SCOPE

### Removed from Original PRD 0017

- ❌ **Full OpenSpec refactoring**: OpenSpec port is PH0.5 (separate track, nearly complete)
- ❌ **PRD 0016 Phase 0**: Agent discovery complete (91 tests passing)
- ❌ **Detailed implementation**: Each phase gets own PRD with impl details
- ❌ **Parallel execution**: Sequential only (Phase 3), parallel = future
- ❌ **Advanced retry logic**: Simple fail = block (Phase 3)
- ❌ **Real-time UI**: Terminal output only (Phase 3)

### Future Work (Beyond Phase 3)

- Parallel subgoal execution (when dependencies allow)
- Advanced error recovery (retries, rollback)
- Real-time progress dashboard (web UI)
- Plan templates library (common patterns)
- Plan analytics (time tracking, success rates)

---

## PACKAGE AWARENESS MAP

### What Exists in `/tmp/openspec-source/aurora/`

**Must Port to Aurora**:
```
aurora/
├── commands/          # archive, init, list, update, view ✅ DONE
├── parsers/           # markdown, requirements, metadata ✅ DONE
├── schemas/           # plan, spec ✅ DONE
├── templates/         # AGENTS.md, project.md ✅ DONE
├── validators/        # plan, requirement validators ✅ DONE
├── configurators/     # slash command configs ✅ DONE (Claude)
├── converters/        # format converters ✅ DONE
└── utils/             # file operations, formatting ✅ DONE
```

**Test Status**: 284 tests passing in OpenSpec refactored

**Integration Checklist for Phase 1**:
- [ ] Copy packages to `packages/planning/src/aurora_planning/`
- [ ] Update imports throughout codebase
- [ ] Register CLI commands in `aurora_cli/main.py`
- [ ] Create slash command configurators (all 3 tools)
- [ ] Verify 284 tests pass in new location
- [ ] Add integration tests for Aurora-specific features

---

## NEXT STEPS

### Before Phase 1 PRD

1. **Complete PH0.5 refactoring** (Phase 14: Finalize)
   - Integration guide
   - API reference
   - Push to GitHub

2. **Review this specs doc**
   - Confirm approach with stakeholders
   - Identify any missing requirements
   - Validate 3-phase breakdown

3. **Create Phase 1 PRD**
   - Detailed requirements for slash commands
   - OpenSpec integration acceptance criteria
   - Test plan with coverage targets
   - Timeline: 1 sprint

### During Phase 1

- Sprint planning from Phase 1 PRD
- Daily development with TDD
- Weekly demos of `/aur:plan` progress
- Sprint review + Phase 2 planning

---

## DOCUMENT HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-02 | Initial comprehensive specs (too detailed) |
| 2.0 | 2026-01-02 | Refactored: Removed PRD 0016 complete items, focused on 3-phase strategy, added OpenSpec port awareness, emphasized slash commands |

---

**END OF SPECIFICATIONS**

**Next Document**: Phase 1 PRD (detailed requirements, test plan, acceptance criteria)
