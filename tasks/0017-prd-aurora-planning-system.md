# PRD 0017: Aurora Planning System (3-Phase Implementation + PRD 0016 Prerequisite)
## Product Requirements Document

**Version**: 1.1
**Date**: January 1, 2026
**Status**: Ready for Implementation
**Phase**: Sprint 4 - Planning System with Agent Delegation
**Product**: AURORA CLI
**Dependencies**: PRD 0016 (Agent Discovery & Memory Infrastructure - NOT YET BUILT), SOAR Orchestrator, OpenSpec Framework (MIT)

**⚠️ CRITICAL DEPENDENCY**: This PRD depends on **PRD 0016 (Agent Discovery & Memory Infrastructure)** which has NOT been built yet. Specifically:
- **Agent Discovery**: Agent manifest generation, `aur agents` commands
- **Memory Infrastructure**: Shared `MemoryManager` API for context retrieval

PRD 0016 must be completed first to provide the foundations for planning.

---

## DOCUMENT PURPOSE

This PRD defines the **Aurora Planning System** - a comprehensive 4-phase planning and execution framework that generates SOAR-powered plans, expands them into detailed PRDs, creates code-aware tasks, and delegates execution to specialized agents.

**Success Criteria**:
- **PRD 0016 Complete** (PREREQUISITE): Agent discovery + memory infrastructure implemented
- **Phase 1 Complete**: Advanced planning with 4-file workflow, lifecycle management
- **Phase 2 Complete**: PRD expansion, code-aware task generation with file paths
- **Phase 3 Complete**: Agent delegation, execution tracking, gap handling

**Related Documents**:
- Foundation: `/tasks/0016-prd-agent-discovery-planning-cli.md` (Agent discovery & memory retrieval)
- Architecture: `packages/soar/src/aurora_soar/orchestrator.py` (SOAR 9-phase pipeline)
- Inspiration: OpenSpec framework (MIT licensed, file structure patterns)
- Memory: `docs/cli/CLI_USAGE_GUIDE.md` (Memory retrieval system)

---

## TABLE OF CONTENTS

1. [Out of Scope: Phase 0](#out-of-scope-phase-0)
2. [Executive Summary](#1-executive-summary)
3. [Goals & Success Metrics](#2-goals--success-metrics)
4. [User Stories](#3-user-stories)
5. [Functional Requirements](#4-functional-requirements)
6. [File Formats & Examples](#5-file-formats--examples)
7. [Architecture & Design](#6-architecture--design)
8. [Quality Gates & Acceptance Criteria](#7-quality-gates--acceptance-criteria)
9. [Testing Strategy](#8-testing-strategy)
10. [Dependencies](#9-dependencies)
11. [Phase Breakdown](#10-phase-breakdown)
12. [Technical Considerations](#11-technical-considerations)
13. [Delivery Verification Checklist](#12-delivery-verification-checklist)

---

## OUT OF SCOPE: PRD 0016 (INFRASTRUCTURE FOUNDATIONS)

**⚠️ CRITICAL FOR TASK GENERATION**: PRD 0016 is **NOT part of this PRD's implementation scope**.

### What is PRD 0016?
PRD 0016 defines **Agent Discovery & Memory Infrastructure** - foundational infrastructure components:
- **Agent Discovery**: Agent manifest generation, discovery commands (`aur agents list/search/show/refresh`)
- **Memory Infrastructure**: Shared `MemoryManager` class for context retrieval

### Why is PRD 0016 Out of Scope?
1. **Already defined**: PRD 0016 is fully specified in `/tasks/0016-prd-agent-discovery-planning-cli.md`
2. **Separate implementation**: PRD 0016 has its own task list (generate from that PRD)
3. **Prerequisite only**: This PRD (0017) depends on PRD 0016 being complete, but does NOT implement it
4. **Infrastructure vs Features**: PRD 0016 = foundations, PRD 0017 = planning features

### What PRD 0016 Provides (Prerequisites for this PRD)

**Agent Discovery Infrastructure**:
- Agent manifest generation (`~/.aurora/cache/agent_manifest.json`)
- Agent discovery commands: `aur agents list/search/show/refresh`
- `AgentInfo` model and `AgentManifest` schema
- Multi-source agent scanning (claude, ampcode, droid, opencode)

**Shared Memory Infrastructure**:
- `MemoryManager` class with clean API (`retrieve()`, `load_context_files()`)
- Refactored from `aur query` command
- Support for `--context` file overrides
- Used by SOAR orchestrator, planning system, query commands

### Task Generation Instructions
**When generating tasks from this PRD (0017)**:
- ✅ **DO** generate tasks for Phase 1, 2, 3 of THIS PRD (Planning System)
- ❌ **DO NOT** generate tasks for agent discovery infrastructure
- ❌ **DO NOT** generate tasks for memory refactoring
- ❌ **DO NOT** include "build agent manifest" or "implement aur agents list" tasks
- ❌ **DO NOT** include "extract MemoryManager from aur query" tasks
- ✅ **DO** assume PRD 0016 APIs exist and are available (as dependencies):
  - `AgentManifest` API for agent recommendations
  - `MemoryManager` API for context retrieval
- ✅ **DO** generate tasks that BUILD ON these foundations:
  - 4-file workflow (plan.md, prd.md, tasks.md, agents.json)
  - PRD expansion with acceptance criteria
  - Code-aware task generation using MemoryManager
  - Agent delegation and execution tracking

**PRD 0016 Task Reference**: For infrastructure implementation tasks, generate them from `/tasks/0016-prd-agent-discovery-planning-cli.md` separately.

---

## 1. EXECUTIVE SUMMARY

### 1.1 What is Aurora Planning System?

A 3-phase planning and execution framework (with PRD 0016 as prerequisite) that bridges natural language goals to code-aware implementation tasks, powered by SOAR orchestration and specialized agent delegation.

**PRD 0016: Agent Discovery & Basic Planning (PREREQUISITE, NOT YET BUILT)**
- **Phase 1**: Agent manifest generation, discovery commands (`aur agents list/search/show`)
- **Phase 2**: Basic plan generation from goals with memory integration
- **Status**: Must be completed BEFORE Phase 1 of this PRD
- **Estimated Duration**: 6-9 hours (both phases)
- **Reference**: `/tasks/0016-prd-agent-discovery-planning-cli.md`

**Phase 1: Advanced Planning (Weeks 1-2, AFTER PRD 0016 complete)**
- Generate structured plans from natural language goals
- Four-file workflow: `plan.md` (SOAR output), `prd.md` (detailed requirements), `tasks.md` (code-aware tasks), `agents.json` (machine-readable data)
- Plan lifecycle management: init, create, list, show, archive
- Memory-integrated planning (reuses indexed codebase context)
- **Requires**: PRD 0016 (agent discovery + basic planning) complete

**Phase 2: PRD & Task Generation (Weeks 3-4)**
- Expand plans into detailed PRDs with acceptance criteria
- Generate code-aware tasks with specific file paths and line numbers
- Agent recommendation per subgoal (not per task)
- Slash commands: `/aur:plan`, `/aur:archive`

**Phase 3: Execution & Agent Delegation (Weeks 5-6)**
- Delegate subgoals to specialized agents from PRD 0016 agent registry
- Track progress via checkbox parsing in `tasks.md`
- Handle agent gaps (prompt for fallback or user decision)
- `/aur:implement` command for automated execution

### 1.2 Key Components

1. **Planning Pipeline** (`aurora-planning` package):
   - SOAR-powered goal decomposition
   - Memory retrieval integration from PRD 0016
   - Four-file generation: plan → prd → tasks + agents.json
   - Plan storage at `~/.aurora/plans/active/`

2. **Code-Aware Task Generator**:
   - File path resolution using memory index
   - Line number suggestions for modifications
   - Dependency ordering (sequential execution)

3. **Agent Delegation Engine**:
   - Agent selection from manifest (PRD 0016)
   - Gap detection and fallback prompting
   - Subprocess spawning per subgoal
   - Progress state persistence

4. **Slash Command Integration**:
   - `/aur:plan "goal"` - Generate plan from anywhere
   - `/aur:implement <plan-id>` - Execute with agents
   - `/aur:archive <plan-id>` - Archive completed plan

### 1.3 Why This Matters

**Current Pain Points**:
- No systematic planning workflow in Aurora (ad-hoc only)
- `aur plan` from PRD 0016 generates flat task lists (no hierarchy)
- No code-aware task generation (developers guess file paths)
- No agent delegation or execution tracking

**After This Feature**:
- Structured planning with clear subgoals and dependencies
- Code-aware tasks: "Modify `src/auth.py` lines 42-68 to add logging"
- Agent specialization: QA reviews, architects design, developers implement
- Progress tracking: checkbox state persisted, pause/resume capable

**Unique Value Propositions**:
1. **SOAR-Powered**: Automatic goal decomposition with cognitive architecture
2. **Memory-Aware**: Knows which files exist and how to modify them
3. **Agent-Delegated**: Spawns specialists per subgoal (not generic execution)
4. **Gap-Detecting**: Identifies missing agent types and suggests creation
5. **Code-Precise**: Tasks include file paths + line numbers from memory index

---

## 2. GOALS & SUCCESS METRICS

### 2.1 Primary Goals

**PRD 0016** (PREREQUISITE - NOT PART OF THIS PRD):
1. Agent manifest generation from multiple sources (PRD 0016 Phase 1)
2. Agent search and discovery commands (PRD 0016 Phase 1)
3. Basic plan generation from goals (PRD 0016 Phase 2)
4. **Status**: NOT YET BUILT - must complete first
5. **See**: `/tasks/0016-prd-agent-discovery-planning-cli.md` for implementation tasks

**Phase 1** (THIS PRD - AFTER PRD 0016):
1. Generate structured plans from natural language in <10s
2. Store plans in organized directory structure (`~/.aurora/plans/`)
3. Support plan lifecycle: create, list, show, archive
4. Integrate memory retrieval from PRD 0016 for context
5. Four-file workflow: plan.md, prd.md, tasks.md, agents.json

**Phase 2**:
6. Expand plans to detailed PRDs with acceptance criteria in <5s
7. Generate code-aware tasks with file paths from memory index
8. Recommend agents per subgoal (using PRD 0016 manifest)
9. Implement slash commands for Claude Code integration

**Phase 3**:
10. Execute plans by delegating to specialized agents
11. Track progress via checkbox parsing and state persistence
12. Handle agent gaps with user prompts or fallback recommendations
13. Enable pause/resume for long-running executions

### 2.2 Success Metrics

| Metric | PRD 0016 Target | Phase 1 Target | Phase 2 Target | Phase 3 Target | Measurement |
|--------|-----------------|----------------|----------------|----------------|-------------|
| **Agent Discovery** | <500ms | N/A | N/A | N/A | Benchmark manifest load |
| **Basic Planning** | <10s | N/A | N/A | N/A | PRD 0016 benchmark |
| **Advanced Planning** | N/A | <10s | <5s (PRD) | N/A | Benchmark end-to-end |
| **Memory Retrieval** | N/A | <2s | <2s | <2s | Benchmark context loading |
| **File Path Accuracy** | N/A | N/A | ≥90% | ≥90% | Test file existence |
| **Agent Matching** | N/A | N/A | ≥85% | ≥85% | Validate recommendations |
| **Execution Tracking** | N/A | N/A | N/A | 100% state save | Test checkpoint recovery |
| **Test Coverage** | ≥85% (PRD 0016) | ≥85% | ≥85% | ≥85% | pytest-cov |
| **Type Safety** | 0 mypy errors | 0 mypy errors | 0 mypy errors | mypy strict |

### 2.3 Phase Completion Criteria

**PRD 0016 COMPLETE** (PREREQUISITE - OUT OF SCOPE FOR THIS PRD) when:
- ✅ Agent manifest generation operational (PRD 0016 Phase 1)
- ✅ `aur agents list/search/show` commands functional (PRD 0016 Phase 1)
- ✅ Agent discovery <500ms latency (PRD 0016 Phase 1)
- ✅ Basic `aur plan` command operational (PRD 0016 Phase 2)
- ✅ Memory retrieval integration working (PRD 0016 Phase 2)
- ✅ All quality gates passed (≥85% coverage, 0 mypy errors)
- ✅ **This must be completed BEFORE starting Phase 1 of THIS PRD**
- 📄 **See PRD 0016 for complete criteria**: `/tasks/0016-prd-agent-discovery-planning-cli.md`

**Phase 1 COMPLETE** when:
- ✅ `aur plan init` scaffolds planning directory
- ✅ `/aur:plan "goal"` generates plan.md in <10s
- ✅ `aur plan list` shows active plans
- ✅ `aur plan show <id>` displays plan details
- ✅ `/aur:archive <id>` moves to archive with timestamp
- ✅ Four-file structure working: plan.md, prd.md, tasks.md, agents.json
- ✅ Memory integration operational (uses indexed codebase)
- ✅ All quality gates passed (≥85% coverage, 0 mypy errors)

**Phase 2 COMPLETE** when:
- ✅ `aur plan expand <id> --to-prd` generates detailed PRD
- ✅ `aur plan tasks <id>` generates code-aware tasks
- ✅ Tasks include file paths + line numbers from memory
- ✅ Agent recommendations per subgoal operational
- ✅ Slash commands working: `/aur:plan`, `/aur:archive`
- ✅ PRD format matches OpenSpec quality standards
- ✅ Integration tests pass for full workflow

**Phase 3 COMPLETE** when:
- ✅ `aur plan execute <id>` delegates to agents
- ✅ `/aur:implement` spawns subprocesses per subgoal
- ✅ Progress tracked via checkbox state + JSON persistence
- ✅ Agent gaps handled with user prompts
- ✅ Pause/resume works via state checkpoints
- ✅ Acceptance tests match all user stories

---

## 3. USER STORIES

### 3.1 Phase 1: Developer Planning Feature Implementation

**As a** developer planning a new feature,
**I want** to generate a structured plan with subgoals and dependencies,
**So that** I have a clear roadmap before starting implementation.

**Acceptance Criteria**:
- `aur plan create "Implement OAuth2 authentication"` generates plan in <10s
- Plan includes: goal, subgoals (research, design, implement, test), dependencies
- Plan stored at `~/.aurora/plans/active/0001-oauth-auth/plan.md`
- `aur plan list` shows the new plan with ID and timestamp
- `aur plan show 0001` displays full plan details
- Memory context retrieved from indexed codebase (if available)

**Testing Requirements**:
- Unit test plan generation with mock SOAR orchestrator
- Integration test with real memory retrieval
- Performance benchmark ensuring <10s latency

---

### 3.2 Phase 1: Developer Managing Plan Lifecycle

**As a** developer juggling multiple features,
**I want** to list active plans and archive completed ones,
**So that** I maintain a clean workspace and track progress.

**Acceptance Criteria**:
- `aur plan list` shows active plans sorted by creation date
- `aur plan list --archived` shows completed plans with archive timestamps
- `aur plan archive 0001` moves plan to `~/.aurora/plans/archive/2026-01-15-0001-oauth-auth/`
- Archive includes all 4 files: plan.md, prd.md, tasks.md, agents.json
- Re-listing active plans excludes archived items

**Testing Requirements**:
- Test archive workflow with file system verification
- Test list filtering (active vs archived)
- Test plan not found errors

---

### 3.3 Phase 2: Developer Expanding Plan to PRD

**As a** developer ready to implement a planned feature,
**I want** to expand the high-level plan into a detailed PRD,
**So that** I have complete acceptance criteria and technical specifications.

**Acceptance Criteria**:
- `aur plan expand 0001 --to-prd` generates detailed `prd.md` in <5s
- PRD includes: functional requirements, acceptance criteria per subgoal, testing strategy
- PRD references specific files from memory index (e.g., "Modify src/auth.py")
- Agent recommendations included per subgoal (e.g., "@full-stack-dev for Backend Implementation")
- PRD format follows OpenSpec standards (Requirements + Scenarios)

**Testing Requirements**:
- Unit test PRD generation with template validation
- Integration test with agent manifest from PRD 0016
- Validate PRD schema against OpenSpec conventions

---

### 3.4 Phase 2: Developer Generating Code-Aware Tasks

**As a** developer implementing a feature,
**I want** tasks that specify exact file paths and line numbers,
**So that** I know precisely where to make changes without guessing.

**Acceptance Criteria**:
- `aur plan tasks 0001` generates `tasks.md` with code-specific tasks
- Tasks include file paths: "Modify src/auth.py lines 42-68 to add logging"
- File paths resolved from memory index (verified to exist)
- Tasks grouped by subgoal with sequential ordering
- Checkboxes provided for progress tracking

**Example Task Output**:
```markdown
## Subgoal 2: Backend Implementation (@full-stack-dev)
- [ ] 2.1 Modify `src/models/user.py` lines 15-30: Add oauth_provider, oauth_id fields
- [ ] 2.2 Create `src/auth/oauth.py`: Implement Auth0 client wrapper
- [ ] 2.3 Modify `src/api/routes.py` lines 78-92: Add /auth/login, /auth/callback endpoints
```

**Testing Requirements**:
- Test file path resolution against memory index
- Test line number suggestions (mock git blame data)
- Test task generation for non-existent files (should warn)

---

### 3.5 Phase 3: Developer Executing Plan with Agent Delegation

**As a** developer with a complete plan,
**I want** to execute it by delegating subgoals to specialized agents,
**So that** each part of the implementation uses domain expertise.

**Acceptance Criteria**:
- `aur plan execute 0001` reads plan and delegates subgoals sequentially
- Subgoal 1 (Research) → spawns `@business-analyst` subprocess
- Subgoal 2 (Design) → spawns `@holistic-architect` subprocess
- Subgoal 3 (Implementation) → spawns `@full-stack-dev` subprocess
- Subgoal 4 (Testing) → spawns `@qa-test-architect` subprocess
- Progress saved to `~/.aurora/plans/active/0001-oauth-auth/state.json`
- Execution completes in <30 minutes for 4-subgoal plan

**Testing Requirements**:
- Integration test with mock agent subprocesses
- Test state persistence after each subgoal
- Test error recovery (agent failure, timeout)

---

### 3.6 Phase 3: Developer Handling Agent Gaps

**As a** developer executing a plan with missing agents,
**I want** to be prompted for fallback options or to skip the subgoal,
**So that** execution doesn't fail silently.

**Acceptance Criteria**:
- Plan references `@technical-writer` but agent doesn't exist
- Execution pauses with prompt: "Agent @technical-writer not found. Options: 1) Use @business-analyst, 2) Skip, 3) Abort"
- User selection persisted in state.json
- Execution continues with chosen fallback
- Gap logged for post-execution review

**Testing Requirements**:
- Test gap detection with missing agents
- Test user prompt in interactive mode
- Test auto-skip in `--non-interactive` mode

---

## 4. FUNCTIONAL REQUIREMENTS

### 4.1 Phase 1: Core Planning Commands

**Package**: `packages/planning/src/aurora_planning/commands/plan.py`

#### FR-1.1: Command: `aur plan init`

**MUST** initialize planning directory structure:

```bash
# Initialize planning system
aur plan init

# Custom directory (optional)
aur plan init --path ~/.custom/plans
```

**Directory Structure Created**:
```
~/.aurora/plans/
├── active/       # Currently planned features
├── archive/      # Completed plans (timestamped)
└── templates/    # Plan templates (optional)
```

**Output**:
```
Planning directory initialized at ~/.aurora/plans/
- Active plans: ~/.aurora/plans/active/
- Archived plans: ~/.aurora/plans/archive/
Ready to create plans with: aur plan create "goal"
```

**Requirements**:
- Create directories if they don't exist
- Skip with warning if already initialized
- Verify write permissions
- Latency target: <100ms

---

#### FR-1.2: Slash Command: `/aur:plan` (Claude Code Integration)

**MUST** generate structured plan from natural language goal via slash command:

```bash
# Basic plan creation (interactive)
/aur:plan

# From PRD file
/aur:plan --from-file tasks/0016-prd-agent-discovery-planning-cli.md

# From any markdown file
/aur:plan --from-file ~/Documents/feature-requirements.md

# With custom goal override
/aur:plan --from-file prd.md --goal "Implement Phase 1 only"
```

**Note**: This is a **slash command** for Claude Code, not a CLI command. For CLI usage, see `aur plan list` and `aur plan show`.

**Planning Pipeline**:

**Step 1: Generate Plan ID**
```python
def generate_plan_id(goal: str, existing_ids: list[str]) -> str:
    """
    Generate unique plan ID from goal.

    Format: 0001-oauth-auth (incremental number + slug)
    """
    base_slug = slugify(goal)[:30]  # Max 30 chars
    next_num = len(existing_ids) + 1
    return f"{next_num:04d}-{base_slug}"
```

**Step 2: Retrieve Context**
```python
def retrieve_context(goal: str, context_paths: list[Path] | None) -> ContextData:
    """
    Retrieve context for planning (REUSE from PRD 0016).

    Strategy:
    1. If --context provided: use ONLY those files (no merging)
    2. Else if indexed memory available: retrieve by goal
    3. Else: warn and proceed with no context
    """
    # Implementation from packages/cli/src/aurora_cli/memory/retrieval.py
```

**Step 3: SOAR Decomposition**
```python
def decompose_goal(
    goal: str,
    context: ContextData,
    agents: list[AgentInfo]
) -> Plan:
    """
    Decompose goal using SOAR orchestrator.

    Reuses:
    - SOAR Phase 3 (Decompose) logic
    - Complexity assessment (simple vs complex)
    - Subgoal dependency detection
    """
    orchestrator = SOAROrchestrator()
    result = orchestrator.decompose(goal, context, agents)
    return Plan.from_soar_result(result)
```

**Step 4: Generate Four Files**
```python
def generate_plan_files(plan: Plan, plan_dir: Path):
    """
    Generate plan.md, prd.md, tasks.md, agents.json in plan directory.

    Files:
    - plan.md: SOAR output (goal + subgoals + agents)
    - prd.md: Placeholder for Phase 2 expansion
    - tasks.md: Placeholder checklist (detailed in Phase 2)
    - agents.json: Machine-readable agent assignments
    """
    write_file(plan_dir / "plan.md", format_plan_md(plan))
    write_file(plan_dir / "prd.md", PRD_TEMPLATE)
    write_file(plan_dir / "tasks.md", TASKS_TEMPLATE)
    write_file(plan_dir / "agents.json", plan.to_json())
```

**Plan Schema** (agents.json):
```json
{
  "plan_id": "0001-oauth-auth",
  "goal": "Implement OAuth2 authentication",
  "created_at": "2026-01-15T10:30:00Z",
  "status": "active",
  "complexity": "complex",
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Research & Architecture",
      "description": "Evaluate OAuth2 providers and design system",
      "recommended_agent": "@business-analyst",
      "agent_exists": true,
      "dependencies": []
    },
    {
      "id": "sg-2",
      "title": "Backend Implementation",
      "description": "Implement Auth0 integration and API endpoints",
      "recommended_agent": "@full-stack-dev",
      "agent_exists": true,
      "dependencies": ["sg-1"]
    }
  ],
  "agent_gaps": [],
  "context_sources": ["indexed_memory"]
}
```

**Output** (Three-step process with checkpoint):
```
🔄 Decomposing goal with SOAR orchestrator...
✓ Retrieved 12 relevant files from memory
✓ Generated 4 subgoals with agent recommendations

📝 Plan created: ~/.aurora/plans/active/0001-oauth-auth/
   ├── plan.md       ✓ SOAR output (goal + 4 subgoals)
   └── agents.json   ✓ Agent recommendations

───────────────────────────────────────────
Preview: plan.md (first 3 subgoals)

1.1 Design OAuth 2.0 flow architecture
    Agent: @holistic-architect (exists)
    Context: src/auth/oauth.py, config/security.yaml

1.2 Implement token storage with encryption
    Agent: @security-specialist (missing)
    Fallback: @full-stack-dev
    Gap: Need crypto + secure storage expertise

1.3 Build authorization code flow handler
    Agent: @full-stack-dev (exists)
───────────────────────────────────────────

Continue to generate detailed PRD and tasks? (Y/n): _
[User presses Y]

✓ Expanded to prd.md (API specs, security requirements)
✓ Generated tasks.md (15 code-aware tasks with file paths)

📋 Plan complete: ~/.aurora/plans/active/0001-oauth-auth/
   ├── plan.md       # SOAR decomposition
   ├── prd.md        # Detailed requirements
   ├── tasks.md      # Implementation tasks
   └── agents.json   # Agent metadata

Next: /aur:implement 0001-oauth-auth
```

**Requirements**:
- Unique plan ID generation (auto-increment)
- Context retrieval from memory or custom files
- SOAR decomposition integration
- Four-file generation
- Agent recommendation per subgoal
- Latency target: <10s end-to-end

---

#### FR-1.3: Command: `aur plan list`

**MUST** list plans with filtering options:

```bash
# List active plans (default)
aur plan list

# List archived plans
aur plan list --archived

# List all plans
aur plan list --all

# JSON output
aur plan list --format json
```

**Output Format** (active):
```
Active Plans (3 total):

ID    Goal                          Created      Status    Subgoals  Agents
────────────────────────────────────────────────────────────────────────────
0001  Implement OAuth2 auth         2026-01-15   active    4         ✓ All found
0002  Add logging to auth module    2026-01-16   active    2         ✓ All found
0003  Refactor database layer       2026-01-17   active    5         ⚠ 1 gap

Use 'aur plan show <id>' for details
```

**Output Format** (archived):
```
Archived Plans (2 total):

ID    Goal                          Archived     Duration  Outcome
──────────────────────────────────────────────────────────────────
0001  Add user authentication       2026-01-10   3 days    ✓ Completed
0002  Fix login bug                 2026-01-12   1 day     ✓ Completed
```

**Requirements**:
- Sort by creation date (newest first)
- Show agent gap warnings
- Support filtering (active/archived/all)
- JSON output for scripting
- Latency target: <200ms

---

#### FR-1.4: Command: `aur plan show`

**MUST** display detailed plan information:

```bash
# Show active plan
aur plan show 0001

# Show archived plan
aur plan show 0001 --archived

# JSON output
aur plan show 0001 --format json
```

**Output Format**:
```
Plan: 0001-oauth-auth
================================================================================
Goal:        Implement OAuth2 authentication with Auth0
Created:     2026-01-15 10:30:00
Status:      active
Complexity:  complex
Context:     5 files from indexed memory

Subgoals (4):
──────────────────────────────────────────────────────────────────────────────

1. Research & Architecture (@business-analyst ✓)
   Evaluate OAuth2 providers and design authentication architecture
   Dependencies: None

2. Backend Implementation (@full-stack-dev ✓)
   Implement Auth0 SDK integration and API endpoints
   Dependencies: Subgoal 1

3. Testing & QA (@qa-test-architect ✓)
   Design test strategy and implement comprehensive tests
   Dependencies: Subgoal 2

4. Documentation (@technical-writer ⚠ NOT FOUND)
   Write API docs and integration guides
   Dependencies: Subgoal 3

   ⚠ Agent Gap Detected:
   - Missing: @technical-writer
   - Fallback: Use @business-analyst or @full-stack-dev
   - Recommendation: Create technical-writer agent

──────────────────────────────────────────────────────────────────────────────
Files:
  • plan.md      - High-level plan
  • prd.md       - Detailed requirements (not yet expanded)
  • tasks.md     - Implementation tasks (not yet generated)
  • agents.json  - Machine-readable data

Next Steps:
1. Review plan for accuracy
2. Expand to PRD: aur plan expand 0001 --to-prd
3. Generate tasks: aur plan tasks 0001
4. Execute: aur plan execute 0001
```

**Requirements**:
- Load from agents.json
- Display subgoals with dependencies
- Show agent recommendations and gaps
- Link to next actions
- Support JSON output
- Latency target: <500ms

---

#### FR-1.5: Slash Command: `/aur:archive` (Claude Code Integration)

**MUST** archive completed plan with timestamp via slash command:

```bash
# Archive plan
/aur:archive 0001-oauth-auth

# Archive by ID only
/aur:archive 0001
```

**Note**: This is a **slash command** for Claude Code, not a CLI command.

**Archive Process**:
1. Move `~/.aurora/plans/active/0001-oauth-auth/` to `~/.aurora/plans/archive/2026-01-15-0001-oauth-auth/`
2. Update `agents.json` with archive metadata:
   ```json
   {
     "status": "archived",
     "archived_at": "2026-01-15T14:30:00Z",
     "duration_days": 3
   }
   ```
3. Verify all 4 files moved successfully

**Output**:
```
Plan archived: 0001-oauth-auth

Archived to: ~/.aurora/plans/archive/2026-01-15-0001-oauth-auth/
Duration: 3 days
Files archived:
  ✓ plan.md
  ✓ prd.md
  ✓ tasks.md
  ✓ agents.json

View archived plans: aur plan list --archived
```

**Requirements**:
- Atomic move operation (rollback on failure)
- Timestamp format: YYYY-MM-DD prefix
- Preserve all plan files
- Update status in agents.json
- Confirmation prompt (skippable with --yes)
- Latency target: <1s

---

#### FR-1.6: Pydantic Schemas (OpenSpec-inspired validation)

**Package**: `packages/cli/src/aurora_cli/planning/models.py`

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
import re


class PlanStatus(str, Enum):
    """Plan lifecycle states."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    FAILED = "failed"


class Complexity(str, Enum):
    """Plan complexity assessment."""
    SIMPLE = "simple"      # 1-2 subgoals, no dependencies
    MODERATE = "moderate"  # 3-4 subgoals, linear dependencies
    COMPLEX = "complex"    # 5+ subgoals, complex dependencies


class Subgoal(BaseModel):
    """
    Individual subgoal within a plan.
    Validation follows OpenSpec patterns: explicit messages, field constraints.
    """
    id: str = Field(
        pattern=r'^sg-\d+$',
        description="Subgoal identifier (e.g., 'sg-1', 'sg-2')"
    )
    title: str = Field(
        min_length=5,
        max_length=100,
        description="Short subgoal title"
    )
    description: str = Field(
        min_length=10,
        max_length=500,
        description="Detailed subgoal description"
    )
    recommended_agent: str = Field(
        pattern=r'^@[a-z0-9-]+$',
        description="Recommended agent (e.g., '@full-stack-dev')"
    )
    agent_exists: bool = Field(
        default=True,
        description="Whether recommended agent exists in manifest"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of subgoal IDs this depends on"
    )

    @field_validator('id')
    @classmethod
    def validate_subgoal_id(cls, v: str) -> str:
        if not re.match(r'^sg-\d+$', v):
            raise ValueError(
                f"Subgoal ID must be 'sg-N' format (e.g., 'sg-1'). Got: {v}"
            )
        return v

    @field_validator('recommended_agent')
    @classmethod
    def validate_agent_format(cls, v: str) -> str:
        if not v.startswith('@'):
            raise ValueError(
                f"Agent must start with '@' (e.g., '@full-stack-dev'). Got: {v}"
            )
        return v


class Plan(BaseModel):
    """
    Complete plan with subgoals and metadata.
    Validation follows OpenSpec patterns: explicit messages, field constraints.
    """
    plan_id: str = Field(
        pattern=r'^\d{4}-[a-z0-9-]+$',
        description="Plan ID (e.g., '0001-oauth-auth')"
    )
    goal: str = Field(
        min_length=10,
        max_length=500,
        description="Natural language goal"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Plan creation timestamp"
    )
    status: PlanStatus = Field(
        default=PlanStatus.ACTIVE,
        description="Plan lifecycle status"
    )
    complexity: Complexity = Field(
        default=Complexity.MODERATE,
        description="Assessed complexity"
    )
    subgoals: list[Subgoal] = Field(
        min_length=1,
        max_length=10,
        description="List of subgoals (1-10)"
    )
    agent_gaps: list[str] = Field(
        default_factory=list,
        description="Agents referenced but not found in manifest"
    )
    context_sources: list[str] = Field(
        default_factory=list,
        description="Where context came from (indexed_memory, custom_files)"
    )

    # Archive metadata (populated on archive)
    archived_at: datetime | None = Field(default=None)
    duration_days: int | None = Field(default=None)

    @field_validator('plan_id')
    @classmethod
    def validate_plan_id(cls, v: str) -> str:
        if not re.match(r'^\d{4}-[a-z0-9-]+$', v):
            raise ValueError(
                f"Plan ID must be 'NNNN-slug' format (e.g., '0001-oauth-auth'). Got: {v}"
            )
        return v

    @field_validator('subgoals')
    @classmethod
    def validate_subgoal_dependencies(cls, v: list[Subgoal]) -> list[Subgoal]:
        """Ensure dependency references are valid."""
        valid_ids = {sg.id for sg in v}
        for sg in v:
            for dep in sg.dependencies:
                if dep not in valid_ids:
                    raise ValueError(
                        f"Subgoal {sg.id} references unknown dependency: {dep}"
                    )
        return v


class PlanManifest(BaseModel):
    """
    Manifest tracking all plans (for fast listing).
    Stored at ~/.aurora/plans/manifest.json
    """
    version: str = Field(default="1.0")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    active_plans: list[str] = Field(
        default_factory=list,
        description="List of active plan IDs"
    )
    archived_plans: list[str] = Field(
        default_factory=list,
        description="List of archived plan IDs"
    )
    stats: dict = Field(
        default_factory=lambda: {
            "total_created": 0,
            "total_archived": 0,
            "total_failed": 0
        }
    )
```

---

#### FR-1.7: Validation Error Messages (OpenSpec lesson)

**Package**: `packages/cli/src/aurora_cli/planning/errors.py`

```python
"""
Validation error messages for planning system.
OpenSpec pattern: explicit, actionable error messages.
"""

VALIDATION_MESSAGES = {
    # Plan ID errors
    "PLAN_ID_INVALID_FORMAT": (
        "Plan ID must be 'NNNN-slug' format (e.g., '0001-oauth-auth'). Got: {value}"
    ),
    "PLAN_ID_ALREADY_EXISTS": (
        "Plan ID '{plan_id}' already exists. Use 'aur plan show {plan_id}' to view it."
    ),
    "PLAN_NOT_FOUND": (
        "Plan '{plan_id}' not found. Use 'aur plan list' to see available plans."
    ),
    "PLAN_ALREADY_ARCHIVED": (
        "Plan '{plan_id}' is already archived. Use 'aur plan list --archived' to view."
    ),

    # Goal errors
    "GOAL_TOO_SHORT": (
        "Goal must be at least 10 characters. Provide a clear description of what to achieve."
    ),
    "GOAL_TOO_LONG": (
        "Goal exceeds 500 characters. Consider breaking into multiple plans."
    ),

    # Subgoal errors
    "SUBGOAL_ID_INVALID": (
        "Subgoal ID must be 'sg-N' format (e.g., 'sg-1'). Got: {value}"
    ),
    "SUBGOAL_DEPENDENCY_INVALID": (
        "Subgoal '{subgoal_id}' references unknown dependency: {dependency}"
    ),
    "SUBGOAL_CIRCULAR_DEPENDENCY": (
        "Circular dependency detected: {cycle}"
    ),
    "TOO_MANY_SUBGOALS": (
        "Plan has {count} subgoals (max 10). Consider splitting into multiple plans."
    ),

    # Agent errors
    "AGENT_FORMAT_INVALID": (
        "Agent must start with '@' (e.g., '@full-stack-dev'). Got: {value}"
    ),
    "AGENT_NOT_FOUND": (
        "Agent '{agent}' not found in manifest. "
        "Use 'aur agents list' to see available agents or 'aur agents refresh' to update."
    ),

    # Directory errors
    "PLANS_DIR_NOT_INITIALIZED": (
        "Planning directory not initialized. Run 'aur plan init' first."
    ),
    "PLANS_DIR_NO_WRITE_PERMISSION": (
        "Cannot write to {path}. Check directory permissions."
    ),
    "PLANS_DIR_ALREADY_EXISTS": (
        "Planning directory already exists at {path}. Use --force to reinitialize."
    ),

    # File errors
    "PLAN_FILE_CORRUPT": (
        "Plan file '{file}' is corrupt or invalid JSON. Try regenerating the plan."
    ),
    "PLAN_FILE_MISSING": (
        "Expected file '{file}' not found in plan directory."
    ),

    # Context errors
    "CONTEXT_FILE_NOT_FOUND": (
        "Context file '{file}' not found. Check the path and try again."
    ),
    "NO_INDEXED_MEMORY": (
        "No indexed memory available. Run 'aur mem index .' to index codebase, "
        "or use '--context <file>' to provide manual context."
    ),

    # Archive errors
    "ARCHIVE_FAILED": (
        "Failed to archive plan: {error}. Plan remains in active state."
    ),
    "ARCHIVE_ROLLBACK": (
        "Archive failed, rolled back to original state. Error: {error}"
    ),
}


class PlanningError(Exception):
    """Base exception for planning errors."""

    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = VALIDATION_MESSAGES.get(code, code).format(**kwargs)
        super().__init__(self.message)


class PlanNotFoundError(PlanningError):
    """Plan not found in active or archive."""

    def __init__(self, plan_id: str):
        super().__init__("PLAN_NOT_FOUND", plan_id=plan_id)


class PlanValidationError(PlanningError):
    """Plan validation failed."""
    pass


class PlanDirectoryError(PlanningError):
    """Plan directory operation failed."""
    pass
```

---

#### FR-1.8: Graceful Degradation Patterns (OpenSpec lesson)

**Error Handling for Each Command**:

**FR-1.1 `aur plan init` - Error Handling**:
```python
def init_planning_directory(path: Path | None = None) -> InitResult:
    """
    Initialize planning directory with OpenSpec-style graceful degradation.
    NEVER crashes - returns structured result with warnings.
    """
    target = path or Path.home() / ".aurora" / "plans"

    try:
        # Check if already initialized
        if (target / "active").exists():
            return InitResult(
                success=True,
                path=target,
                warning="Planning directory already exists. No changes made.",
                created=False
            )

        # Check write permissions
        if not os.access(target.parent, os.W_OK):
            return InitResult(
                success=False,
                path=target,
                error=VALIDATION_MESSAGES["PLANS_DIR_NO_WRITE_PERMISSION"].format(path=target),
                created=False
            )

        # Create directories
        (target / "active").mkdir(parents=True, exist_ok=True)
        (target / "archive").mkdir(parents=True, exist_ok=True)

        # Create manifest
        manifest = PlanManifest()
        (target / "manifest.json").write_text(manifest.model_dump_json(indent=2))

        return InitResult(
            success=True,
            path=target,
            created=True,
            message=f"Planning directory initialized at {target}"
        )

    except PermissionError as e:
        return InitResult(
            success=False,
            error=f"Permission denied: {e}",
            created=False
        )
    except Exception as e:
        logger.error(f"Unexpected error in init: {e}", exc_info=True)
        return InitResult(
            success=False,
            error=f"Unexpected error: {e}",
            created=False
        )
```

**FR-1.2 `/aur:plan` - Error Handling**:
```python
def create_plan(goal: str, context_paths: list[Path] | None = None) -> PlanResult:
    """
    Create plan with OpenSpec-style graceful degradation.
    Returns structured result, never crashes.
    """
    warnings = []

    # Validate goal
    if len(goal) < 10:
        return PlanResult(
            success=False,
            error=VALIDATION_MESSAGES["GOAL_TOO_SHORT"]
        )

    # Check planning directory
    plans_dir = Path.home() / ".aurora" / "plans"
    if not (plans_dir / "active").exists():
        return PlanResult(
            success=False,
            error=VALIDATION_MESSAGES["PLANS_DIR_NOT_INITIALIZED"]
        )

    # Retrieve context (graceful degradation)
    try:
        if context_paths:
            context = load_context_files(context_paths)
        elif has_indexed_memory():
            context = retrieve_from_memory(goal, limit=20)
        else:
            context = ContextData.empty()
            warnings.append(VALIDATION_MESSAGES["NO_INDEXED_MEMORY"])
    except Exception as e:
        logger.warning(f"Context retrieval failed: {e}")
        context = ContextData.empty()
        warnings.append(f"Context retrieval failed: {e}. Proceeding without context.")

    # Load agent manifest (graceful degradation)
    try:
        agents = load_agent_manifest()
    except Exception as e:
        logger.warning(f"Agent manifest load failed: {e}")
        agents = []
        warnings.append(f"Agent manifest unavailable: {e}. Agent recommendations disabled.")

    # SOAR decomposition
    try:
        plan = decompose_goal(goal, context, agents)
    except Exception as e:
        logger.error(f"SOAR decomposition failed: {e}", exc_info=True)
        return PlanResult(
            success=False,
            error=f"Goal decomposition failed: {e}"
        )

    # Validate plan
    try:
        validated_plan = Plan.model_validate(plan.to_dict())
    except ValidationError as e:
        errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        return PlanResult(
            success=False,
            error=f"Plan validation failed: {', '.join(errors)}"
        )

    # Detect agent gaps
    agent_ids = {a.id for a in agents}
    for subgoal in validated_plan.subgoals:
        agent_id = subgoal.recommended_agent.strip("@")
        if agent_id not in agent_ids:
            validated_plan.agent_gaps.append(agent_id)
            subgoal.agent_exists = False

    # Write plan files (atomic)
    try:
        plan_dir = write_plan_files(validated_plan, plans_dir / "active")
    except Exception as e:
        logger.error(f"Failed to write plan files: {e}", exc_info=True)
        return PlanResult(
            success=False,
            error=f"Failed to save plan: {e}"
        )

    return PlanResult(
        success=True,
        plan=validated_plan,
        plan_dir=plan_dir,
        warnings=warnings if warnings else None
    )
```

**FR-1.3 `aur plan list` - Error Handling**:
```python
def list_plans(archived: bool = False, all_plans: bool = False) -> ListResult:
    """
    List plans with graceful degradation.
    Returns empty list if directory not initialized (with warning).
    """
    plans_dir = Path.home() / ".aurora" / "plans"

    if not plans_dir.exists():
        return ListResult(
            plans=[],
            warning=VALIDATION_MESSAGES["PLANS_DIR_NOT_INITIALIZED"]
        )

    plans = []
    errors = []

    # Determine which directories to scan
    dirs_to_scan = []
    if all_plans or not archived:
        dirs_to_scan.append(("active", plans_dir / "active"))
    if all_plans or archived:
        dirs_to_scan.append(("archive", plans_dir / "archive"))

    for status, scan_dir in dirs_to_scan:
        if not scan_dir.exists():
            continue

        for plan_path in scan_dir.iterdir():
            if not plan_path.is_dir():
                continue

            agents_json = plan_path / "agents.json"
            if not agents_json.exists():
                errors.append(f"Missing agents.json in {plan_path.name}")
                continue

            try:
                plan = Plan.model_validate_json(agents_json.read_text())
                plans.append(PlanSummary.from_plan(plan, status))
            except Exception as e:
                errors.append(f"Invalid plan {plan_path.name}: {e}")
                continue

    return ListResult(
        plans=sorted(plans, key=lambda p: p.created_at, reverse=True),
        errors=errors if errors else None
    )
```

**FR-1.4 `aur plan show` - Error Handling**:
```python
def show_plan(plan_id: str, archived: bool = False) -> ShowResult:
    """
    Show plan details with graceful degradation.
    Returns structured error if plan not found.
    """
    plans_dir = Path.home() / ".aurora" / "plans"

    # Try to find plan
    search_dirs = []
    if archived:
        search_dirs = list((plans_dir / "archive").glob(f"*{plan_id}*"))
    else:
        search_dirs = list((plans_dir / "active").glob(f"*{plan_id}*"))

    if not search_dirs:
        # Try the other location as fallback
        fallback = "active" if archived else "archive"
        fallback_dirs = list((plans_dir / fallback).glob(f"*{plan_id}*"))
        if fallback_dirs:
            return ShowResult(
                success=False,
                error=f"Plan '{plan_id}' found in {fallback}, not {'archive' if archived else 'active'}. "
                      f"Use '--{'archived' if fallback == 'archive' else ''}' flag."
            )
        return ShowResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_NOT_FOUND"].format(plan_id=plan_id)
        )

    plan_dir = search_dirs[0]
    agents_json = plan_dir / "agents.json"

    if not agents_json.exists():
        return ShowResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_FILE_MISSING"].format(file="agents.json")
        )

    try:
        plan = Plan.model_validate_json(agents_json.read_text())
    except Exception as e:
        return ShowResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_FILE_CORRUPT"].format(file=agents_json)
        )

    # Check which files exist
    files_status = {
        "plan.md": (plan_dir / "plan.md").exists(),
        "prd.md": (plan_dir / "prd.md").exists(),
        "tasks.md": (plan_dir / "tasks.md").exists(),
        "agents.json": True  # We already loaded it
    }

    return ShowResult(
        success=True,
        plan=plan,
        plan_dir=plan_dir,
        files_status=files_status
    )
```

**FR-1.5 `/aur:archive` - Error Handling with Rollback**:
```python
def archive_plan(plan_id: str, force: bool = False) -> ArchiveResult:
    """
    Archive plan with atomic operation and rollback on failure.
    OpenSpec pattern: never leave system in inconsistent state.
    """
    plans_dir = Path.home() / ".aurora" / "plans"
    active_dir = plans_dir / "active"
    archive_dir = plans_dir / "archive"

    # Find the plan
    plan_dirs = list(active_dir.glob(f"*{plan_id}*"))
    if not plan_dirs:
        return ArchiveResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_NOT_FOUND"].format(plan_id=plan_id)
        )

    source_dir = plan_dirs[0]
    plan_name = source_dir.name

    # Load and validate plan
    try:
        agents_json = source_dir / "agents.json"
        plan = Plan.model_validate_json(agents_json.read_text())
    except Exception as e:
        return ArchiveResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_FILE_CORRUPT"].format(file=agents_json)
        )

    # Check if already archived
    if plan.status == PlanStatus.ARCHIVED:
        return ArchiveResult(
            success=False,
            error=VALIDATION_MESSAGES["PLAN_ALREADY_ARCHIVED"].format(plan_id=plan_id)
        )

    # Calculate archive path with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d")
    target_dir = archive_dir / f"{timestamp}-{plan_name}"

    # Atomic archive with rollback
    backup_json = None
    try:
        # Backup original agents.json for rollback
        backup_json = agents_json.read_text()

        # Update plan metadata
        plan.status = PlanStatus.ARCHIVED
        plan.archived_at = datetime.utcnow()
        plan.duration_days = (plan.archived_at - plan.created_at).days

        # Write updated agents.json
        agents_json.write_text(plan.model_dump_json(indent=2))

        # Move directory (atomic on same filesystem)
        shutil.move(str(source_dir), str(target_dir))

        # Update manifest
        update_manifest(remove_active=plan_name, add_archived=target_dir.name)

        return ArchiveResult(
            success=True,
            plan=plan,
            source_dir=source_dir,
            target_dir=target_dir,
            duration_days=plan.duration_days
        )

    except Exception as e:
        logger.error(f"Archive failed: {e}", exc_info=True)

        # Rollback: restore original agents.json if we modified it
        if backup_json and agents_json.exists():
            try:
                agents_json.write_text(backup_json)
            except Exception:
                pass  # Best effort rollback

        # Rollback: move directory back if it was moved
        if target_dir.exists() and not source_dir.exists():
            try:
                shutil.move(str(target_dir), str(source_dir))
            except Exception:
                pass  # Best effort rollback

        return ArchiveResult(
            success=False,
            error=VALIDATION_MESSAGES["ARCHIVE_ROLLBACK"].format(error=str(e))
        )
```

---

#### FR-1.9: Result Types (OpenSpec pattern - structured returns)

**Package**: `packages/cli/src/aurora_cli/planning/results.py`

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InitResult:
    """Result from plan init command."""
    success: bool
    path: Path | None = None
    created: bool = False
    message: str | None = None
    warning: str | None = None
    error: str | None = None


@dataclass
class PlanResult:
    """Result from plan create command."""
    success: bool
    plan: Plan | None = None
    plan_dir: Path | None = None
    warnings: list[str] | None = None
    error: str | None = None


@dataclass
class ListResult:
    """Result from plan list command."""
    plans: list[PlanSummary]
    warning: str | None = None
    errors: list[str] | None = None


@dataclass
class ShowResult:
    """Result from plan show command."""
    success: bool
    plan: Plan | None = None
    plan_dir: Path | None = None
    files_status: dict[str, bool] | None = None
    error: str | None = None


@dataclass
class ArchiveResult:
    """Result from plan archive command."""
    success: bool
    plan: Plan | None = None
    source_dir: Path | None = None
    target_dir: Path | None = None
    duration_days: int | None = None
    error: str | None = None


@dataclass
class PlanSummary:
    """Summary for plan listing."""
    plan_id: str
    goal: str
    created_at: datetime
    status: str
    subgoal_count: int
    agent_gaps: int

    @classmethod
    def from_plan(cls, plan: Plan, status: str) -> "PlanSummary":
        return cls(
            plan_id=plan.plan_id,
            goal=plan.goal[:50] + "..." if len(plan.goal) > 50 else plan.goal,
            created_at=plan.created_at,
            status=status,
            subgoal_count=len(plan.subgoals),
            agent_gaps=len(plan.agent_gaps)
        )
```

---

### 4.2 Phase 2: PRD & Task Generation (Integrated into `/aur:plan`)

**NOTE**: Phase 2 functionality (PRD expansion and task generation) is now integrated into the `/aur:plan` slash command as a single 3-step workflow with checkpoint. See FR-1.2 for details.

The original separate commands (`aur plan expand` and `aur plan tasks`) are **removed** in favor of the unified workflow:
1. SOAR decomposition → plan.md + agents.json
2. **Checkpoint** (user review)
3. PRD expansion → prd.md + tasks.md

#### FR-2.1: PRD Generation (Part of `/aur:plan`)

**Implementation details for PRD generation within `/aur:plan`:

**PRD Generation Pipeline** (runs after user confirms at checkpoint):

**Step 1: Load Plan**
```python
def load_plan(plan_id: str) -> Plan:
    """Load plan from agents.json."""
    plan_dir = Path(f"~/.aurora/plans/active/{plan_id}")
    return Plan.from_json(plan_dir / "agents.json")
```

**Step 2: Generate PRD per Subgoal**
```python
def generate_prd(plan: Plan, context: ContextData) -> PRD:
    """
    Generate detailed PRD using LLM.

    For each subgoal:
    1. Functional requirements with acceptance criteria
    2. Technical considerations (file paths, APIs)
    3. Testing strategy (unit, integration, e2e)
    4. Success metrics
    """
    prd_sections = []

    for subgoal in plan.subgoals:
        section = generate_subgoal_prd(
            subgoal=subgoal,
            context=context,
            dependencies=resolve_dependencies(subgoal)
        )
        prd_sections.append(section)

    return PRD(
        goal=plan.goal,
        sections=prd_sections,
        agent_assignments=plan.agent_assignments
    )
```

**Step 3: Format PRD (OpenSpec Style)**
```python
def format_prd(prd: PRD) -> str:
    """
    Format PRD following OpenSpec conventions.

    Structure:
    - Executive Summary
    - Goals & Success Metrics
    - Functional Requirements (per subgoal)
    - Testing Strategy
    - Agent Assignments
    """
    return PRD_TEMPLATE.format(**prd.to_dict())
```

**PRD Output Example** (prd.md):
```markdown
# PRD: Implement OAuth2 Authentication

## Executive Summary

Implement OAuth2 authentication using Auth0 to replace password-based login.
Provides secure authentication, token refresh, and logout flows.

## Goals

1. Replace password authentication with OAuth2
2. Integrate Auth0 as identity provider
3. Support token refresh and logout
4. Maintain backward compatibility for existing users

## Functional Requirements

### Subgoal 1: Research & Architecture (@business-analyst)

#### FR-1.1: OAuth2 Provider Evaluation
The system SHALL evaluate Auth0, Okta, and custom OAuth2 implementation.

**Acceptance Criteria**:
- Comparison table with cost, features, security
- Recommendation with rationale
- Risk assessment

#### FR-1.2: Authentication Flow Design
The system SHALL design complete OAuth2 flow diagram.

**Acceptance Criteria**:
- Sequence diagram showing login, callback, token refresh
- Error handling for each step
- Session management strategy

### Subgoal 2: Backend Implementation (@full-stack-dev)

#### FR-2.1: User Model with OAuth Fields
The system SHALL extend User model with OAuth fields.

**Files to Modify**:
- `src/models/user.py` lines 15-30: Add oauth_provider, oauth_id, access_token

**Acceptance Criteria**:
- Migration file creates oauth_* columns
- User model includes get_oauth_token(), refresh_token() methods
- Tests pass for OAuth user creation

[... more requirements ...]

## Testing Strategy

### Subgoal 2: Backend Implementation
- Unit tests: User model OAuth methods
- Integration tests: Auth0 SDK calls
- E2E tests: Full login flow
- Security tests: Token expiration, CSRF protection

## Agent Assignments

1. Research & Architecture: @business-analyst
2. Backend Implementation: @full-stack-dev
3. Testing & QA: @qa-test-architect
4. Documentation: @technical-writer (⚠ NOT FOUND - use @business-analyst)
```

**Requirements**:
- Load plan and context from memory
- Generate detailed requirements per subgoal
- Include file paths from memory index
- Follow OpenSpec PRD format
- Reference agent assignments
- Warn if PRD already exists (use --force to overwrite)
- Latency target: <5s

---

#### FR-2.2: Task Generation (Part of `/aur:plan`)

**Implementation details for task generation within `/aur:plan`:

**Task Generation Pipeline** (runs after PRD expansion, no user prompt):

**Step 1: Load PRD**
```python
def load_prd(plan_id: str) -> PRD:
    """Load PRD from prd.md."""
    plan_dir = Path(f"~/.aurora/plans/active/{plan_id}")
    return PRD.from_markdown(plan_dir / "prd.md")
```

**Step 2: Resolve File Paths from Memory**
```python
def resolve_file_paths(requirement: Requirement, memory: MemoryIndex) -> list[FilePath]:
    """
    Resolve file paths from memory index.

    Strategy:
    1. Extract entities from requirement (User model, Auth0 SDK, etc.)
    2. Query memory for matching files
    3. Return top-3 matches with confidence scores
    4. Include line number ranges (from git blame or structure analysis)
    """
    entities = extract_entities(requirement.description)
    file_matches = []

    for entity in entities:
        matches = memory.search_files(entity, top_k=3)
        file_matches.extend(matches)

    return deduplicate_and_rank(file_matches)
```

**Step 3: Generate Tasks per Subgoal**
```python
def generate_tasks(prd: PRD, memory: MemoryIndex) -> TaskList:
    """
    Generate code-aware tasks with file paths.

    For each functional requirement:
    1. Resolve file paths from memory
    2. Suggest line numbers (if available)
    3. Create actionable task with checkbox
    4. Group by subgoal
    """
    tasks = []

    for subgoal in prd.subgoals:
        for req in subgoal.requirements:
            file_paths = resolve_file_paths(req, memory)
            task = create_task(req, file_paths)
            tasks.append(task)

    return TaskList(tasks, grouped_by_subgoal=True)
```

**Task Output Example** (tasks.md):
```markdown
# Implementation Tasks: Implement OAuth2 Authentication

Plan ID: 0001-oauth-auth
Generated: 2026-01-15 14:00:00
Status: 0 / 12 tasks completed

---

## Subgoal 1: Research & Architecture (@business-analyst)

**Dependencies**: None
**Estimated Time**: 4-6 hours

- [ ] 1.1 Research OAuth2 providers (Auth0, Okta, Custom)
  - Deliverable: Comparison table in `docs/oauth-research.md`
  - Expected output: Recommendation with cost/security analysis

- [ ] 1.2 Design authentication flow diagram
  - Deliverable: Sequence diagram in `docs/auth-flow.md`
  - Expected output: Mermaid diagram showing login → callback → token refresh

- [ ] 1.3 Evaluate security implications
  - Deliverable: Security assessment in `docs/security-review.md`
  - Expected output: OWASP top-10 compliance checklist

---

## Subgoal 2: Backend Implementation (@full-stack-dev)

**Dependencies**: Subgoal 1 (Research & Architecture)
**Estimated Time**: 8-12 hours

- [ ] 2.1 Modify User model with OAuth fields
  - **File**: `src/models/user.py` lines 15-30
  - **Changes**: Add oauth_provider, oauth_id, access_token, refresh_token, expires_at columns
  - **Tests**: `tests/models/test_user_oauth.py`

- [ ] 2.2 Create Auth0 SDK wrapper
  - **File**: `src/auth/oauth.py` (NEW)
  - **Functions**: init_auth0_client(), exchange_code_for_token(), refresh_access_token()
  - **Dependencies**: pip install auth0-python

- [ ] 2.3 Implement /auth/login endpoint
  - **File**: `src/api/routes.py` lines 78-92
  - **Changes**: Add /auth/login route, redirect to Auth0
  - **Tests**: `tests/api/test_auth_endpoints.py`

- [ ] 2.4 Implement /auth/callback endpoint
  - **File**: `src/api/routes.py` lines 93-120
  - **Changes**: Handle Auth0 callback, exchange code, store tokens
  - **Tests**: `tests/api/test_auth_endpoints.py`

[... more tasks ...]

---

## Subgoal 3: Testing & QA (@qa-test-architect)

**Dependencies**: Subgoal 2 (Backend Implementation)
**Estimated Time**: 6-8 hours

- [ ] 3.1 Design test strategy
  - Deliverable: Test plan in `docs/test-strategy-oauth.md`
  - Coverage: Unit (models), Integration (Auth0), E2E (full flow), Security

- [ ] 3.2 Write unit tests for User model OAuth methods
  - **File**: `tests/models/test_user_oauth.py` (NEW)
  - **Coverage**: get_oauth_token(), refresh_token(), revoke_token()

- [ ] 3.3 Write integration tests for Auth0 SDK
  - **File**: `tests/integration/test_auth0_client.py` (NEW)
  - **Coverage**: Token exchange, refresh, error handling

[... more tasks ...]

---

## Progress Summary

- Total Tasks: 12
- Completed: 0
- In Progress: 0
- Blocked: 0

**Next Steps**:
1. Review tasks for accuracy and completeness
2. Start with Subgoal 1 (no dependencies)
3. Execute with: `aur plan execute 0001`
```

**Requirements**:
- Load PRD from prd.md
- Resolve file paths using memory index
- Include line numbers when available
- Group tasks by subgoal
- Add checkboxes for progress tracking
- Estimate time per subgoal
- Show dependencies clearly
- Warn if tasks.md already exists (use --force)
- Latency target: <3s

---

#### FR-2.3: Slash Commands

**MUST** implement slash commands for Claude Code integration:

**Command: `/aur:plan`**
```bash
# From anywhere in Claude Code
/aur:plan "Implement OAuth2 authentication"

# With context override
/aur:plan "Add logging" --context src/auth.py
```

**Implementation**:
```python
@slash_command("aur:plan")
def slash_plan(goal: str, **kwargs):
    """
    Generate plan from Claude Code.

    Delegates to: aur plan create
    """
    return subprocess.run([
        "aur", "plan", "create", goal,
        *parse_kwargs(kwargs)
    ])
```

**Command: `/aur:archive`**
```bash
# Archive from anywhere
/aur:archive 0001
```

**Requirements**:
- Register slash commands in Claude Code config
- Delegate to CLI commands
- Return formatted output to chat
- Error handling with user-friendly messages

---

#### FR-2.4: Pydantic Schemas for Phase 2 (OpenSpec-inspired validation)

**Package**: `packages/cli/src/aurora_cli/planning/prd_models.py`

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
import re


class RequirementType(str, Enum):
    """Functional requirement types."""
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    TECHNICAL = "technical"
    SECURITY = "security"


class TestType(str, Enum):
    """Test category types."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    SECURITY = "security"


class FilePath(BaseModel):
    """
    File path with optional line numbers from memory retrieval.
    """
    path: str = Field(
        min_length=1,
        description="Relative file path (e.g., 'src/auth/oauth.py')"
    )
    line_start: int | None = Field(
        default=None,
        ge=1,
        description="Starting line number (1-indexed)"
    )
    line_end: int | None = Field(
        default=None,
        ge=1,
        description="Ending line number (1-indexed)"
    )
    exists: bool = Field(
        default=True,
        description="Whether file exists in codebase"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score from memory retrieval"
    )

    @field_validator('line_end')
    @classmethod
    def validate_line_range(cls, v: int | None, info) -> int | None:
        if v is not None and info.data.get('line_start') is not None:
            if v < info.data['line_start']:
                raise ValueError(
                    f"line_end ({v}) must be >= line_start ({info.data['line_start']})"
                )
        return v

    def format(self) -> str:
        """Format as 'path:start-end' or 'path' if no lines."""
        if self.line_start and self.line_end:
            return f"{self.path}:{self.line_start}-{self.line_end}"
        elif self.line_start:
            return f"{self.path}:{self.line_start}"
        return self.path


class AcceptanceCriteria(BaseModel):
    """Single acceptance criterion."""
    description: str = Field(
        min_length=10,
        max_length=500,
        description="Clear, testable criterion"
    )
    testable: bool = Field(
        default=True,
        description="Whether criterion is objectively testable"
    )


class Requirement(BaseModel):
    """
    Single functional requirement within a PRD section.
    """
    id: str = Field(
        pattern=r'^FR-\d+\.\d+$',
        description="Requirement ID (e.g., 'FR-2.1')"
    )
    title: str = Field(
        min_length=5,
        max_length=100,
        description="Short requirement title"
    )
    description: str = Field(
        min_length=20,
        max_length=1000,
        description="Detailed requirement description"
    )
    type: RequirementType = Field(
        default=RequirementType.FUNCTIONAL,
        description="Requirement category"
    )
    acceptance_criteria: list[AcceptanceCriteria] = Field(
        min_length=1,
        max_length=10,
        description="Testable acceptance criteria"
    )
    files_to_modify: list[FilePath] = Field(
        default_factory=list,
        description="Files impacted by this requirement"
    )
    files_to_create: list[str] = Field(
        default_factory=list,
        description="New files to create"
    )


class PRDSection(BaseModel):
    """
    PRD section corresponding to one subgoal.
    """
    subgoal_id: str = Field(
        pattern=r'^sg-\d+$',
        description="Reference to plan subgoal"
    )
    title: str = Field(
        min_length=5,
        max_length=100,
        description="Section title"
    )
    agent: str = Field(
        pattern=r'^@[a-z0-9-]+$',
        description="Assigned agent"
    )
    requirements: list[Requirement] = Field(
        min_length=1,
        max_length=20,
        description="Functional requirements"
    )
    testing_strategy: dict[TestType, list[str]] = Field(
        default_factory=dict,
        description="Test plan per test type"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Subgoal IDs this depends on"
    )


class PRD(BaseModel):
    """
    Complete Product Requirements Document.
    Validation follows OpenSpec patterns.
    """
    plan_id: str = Field(
        pattern=r'^\d{4}-[a-z0-9-]+$',
        description="Reference to parent plan"
    )
    goal: str = Field(
        min_length=10,
        max_length=500,
        description="Goal from parent plan"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="PRD generation timestamp"
    )
    executive_summary: str = Field(
        min_length=50,
        max_length=2000,
        description="High-level summary"
    )
    sections: list[PRDSection] = Field(
        min_length=1,
        max_length=10,
        description="Sections per subgoal"
    )
    total_requirements: int = Field(
        default=0,
        description="Total FR count (computed)"
    )
    memory_context_used: bool = Field(
        default=False,
        description="Whether memory retrieval was used"
    )


class TaskStatus(str, Enum):
    """Task completion status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class Task(BaseModel):
    """
    Single implementation task with code awareness.
    """
    id: str = Field(
        pattern=r'^\d+\.\d+$',
        description="Task ID (e.g., '2.1')"
    )
    title: str = Field(
        min_length=10,
        max_length=200,
        description="Task description"
    )
    subgoal_id: str = Field(
        pattern=r'^sg-\d+$',
        description="Parent subgoal"
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Completion status"
    )
    files: list[FilePath] = Field(
        default_factory=list,
        description="Files to modify/create"
    )
    test_file: str | None = Field(
        default=None,
        description="Associated test file"
    )
    estimated_minutes: int | None = Field(
        default=None,
        ge=5,
        le=480,
        description="Time estimate (5 min - 8 hours)"
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Task IDs this depends on"
    )


class TaskList(BaseModel):
    """
    Complete task list for a plan.
    """
    plan_id: str = Field(
        pattern=r'^\d{4}-[a-z0-9-]+$',
        description="Reference to parent plan"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Task list generation timestamp"
    )
    tasks: list[Task] = Field(
        min_length=1,
        max_length=100,
        description="All tasks"
    )
    total_tasks: int = Field(
        default=0,
        description="Total task count"
    )
    completed_tasks: int = Field(
        default=0,
        description="Completed task count"
    )
    memory_paths_resolved: int = Field(
        default=0,
        description="File paths resolved from memory"
    )
    memory_paths_missing: int = Field(
        default=0,
        description="File paths not found"
    )

    def get_progress_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100
```

---

#### FR-2.5: Validation Error Messages for Phase 2 (OpenSpec lesson)

**Package**: `packages/cli/src/aurora_cli/planning/errors.py` (extend existing)

```python
# Add to existing VALIDATION_MESSAGES dictionary

VALIDATION_MESSAGES_PHASE2 = {
    # PRD errors
    "PRD_PLAN_NOT_FOUND": (
        "Cannot generate PRD: Plan '{plan_id}' not found. Create plan first with 'aur plan create'."
    ),
    "PRD_ALREADY_EXISTS": (
        "PRD already exists for plan '{plan_id}'. Use --force to overwrite."
    ),
    "PRD_NO_SUBGOALS": (
        "Plan '{plan_id}' has no subgoals. Cannot generate PRD from empty plan."
    ),
    "PRD_GENERATION_FAILED": (
        "PRD generation failed: {error}. Check plan.md for issues."
    ),
    "PRD_TEMPLATE_INVALID": (
        "PRD template validation failed: {errors}. Check template format."
    ),

    # Task generation errors
    "TASKS_PRD_NOT_FOUND": (
        "Cannot generate tasks: PRD not found for plan '{plan_id}'. Run PRD expansion first."
    ),
    "TASKS_ALREADY_EXIST": (
        "Tasks already exist for plan '{plan_id}'. Use --force to regenerate."
    ),
    "TASKS_NO_REQUIREMENTS": (
        "PRD has no requirements. Cannot generate tasks from empty PRD."
    ),
    "TASKS_GENERATION_FAILED": (
        "Task generation failed: {error}. Check prd.md for issues."
    ),

    # File path resolution errors
    "FILE_PATH_NOT_RESOLVED": (
        "Could not resolve file path for '{entity}'. Memory index may need refresh."
    ),
    "FILE_PATH_NOT_EXISTS": (
        "File '{path}' referenced in tasks does not exist. Path may be outdated."
    ),
    "FILE_PATH_LINE_INVALID": (
        "Line numbers {start}-{end} invalid for file '{path}' (file has {total} lines)."
    ),
    "MEMORY_INDEX_EMPTY": (
        "Memory index is empty. Run 'aur mem index .' to index codebase first."
    ),
    "MEMORY_SEARCH_FAILED": (
        "Memory search failed: {error}. File paths will be omitted."
    ),

    # Requirement errors
    "REQUIREMENT_ID_INVALID": (
        "Requirement ID must be 'FR-N.M' format (e.g., 'FR-2.1'). Got: {value}"
    ),
    "REQUIREMENT_NO_ACCEPTANCE_CRITERIA": (
        "Requirement '{req_id}' has no acceptance criteria. Each requirement needs testable criteria."
    ),
    "REQUIREMENT_DUPLICATE_ID": (
        "Duplicate requirement ID '{req_id}' found. IDs must be unique within PRD."
    ),

    # Expand/tasks command errors
    "EXPAND_NOT_READY": (
        "Plan '{plan_id}' not ready for expansion. Ensure plan.md exists and is valid."
    ),
    "EXPAND_CHECKPOINT_DECLINED": (
        "PRD expansion cancelled at checkpoint. Plan remains unchanged."
    ),
}

# Merge into main VALIDATION_MESSAGES
VALIDATION_MESSAGES.update(VALIDATION_MESSAGES_PHASE2)


class PRDGenerationError(PlanningError):
    """PRD generation failed."""
    pass


class TaskGenerationError(PlanningError):
    """Task generation failed."""
    pass


class FileResolutionError(PlanningError):
    """File path resolution failed."""
    pass
```

---

#### FR-2.6: Result Types for Phase 2 (OpenSpec pattern)

**Package**: `packages/cli/src/aurora_cli/planning/results.py` (extend existing)

```python
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime


@dataclass
class PRDResult:
    """Result from PRD generation."""
    success: bool
    prd: PRD | None = None
    prd_path: Path | None = None
    sections_generated: int = 0
    requirements_generated: int = 0
    memory_files_resolved: int = 0
    warnings: list[str] | None = None
    error: str | None = None


@dataclass
class TaskGenerationResult:
    """Result from task generation."""
    success: bool
    task_list: TaskList | None = None
    tasks_path: Path | None = None
    tasks_generated: int = 0
    files_resolved: int = 0
    files_missing: int = 0
    warnings: list[str] | None = None
    error: str | None = None


@dataclass
class ExpandResult:
    """Result from full expand operation (PRD + tasks)."""
    success: bool
    prd_result: PRDResult | None = None
    task_result: TaskGenerationResult | None = None
    plan_dir: Path | None = None
    checkpoint_confirmed: bool = False
    warnings: list[str] | None = None
    error: str | None = None


@dataclass
class FileResolutionResult:
    """Result from file path resolution."""
    success: bool
    resolved_paths: list[FilePath] | None = None
    missing_entities: list[str] | None = None
    confidence_avg: float = 0.0
    memory_queries: int = 0
    warning: str | None = None
```

---

#### FR-2.7: Graceful Degradation Patterns for Phase 2 (OpenSpec lesson)

**PRD Generation - Error Handling**:
```python
def generate_prd(plan_id: str, force: bool = False) -> PRDResult:
    """
    Generate PRD with OpenSpec-style graceful degradation.
    Returns structured result, never crashes.
    """
    warnings = []

    # Load plan
    show_result = show_plan(plan_id)
    if not show_result.success:
        return PRDResult(
            success=False,
            error=VALIDATION_MESSAGES["PRD_PLAN_NOT_FOUND"].format(plan_id=plan_id)
        )

    plan = show_result.plan
    plan_dir = show_result.plan_dir

    # Check existing PRD
    prd_path = plan_dir / "prd.md"
    if prd_path.exists() and not force:
        return PRDResult(
            success=False,
            error=VALIDATION_MESSAGES["PRD_ALREADY_EXISTS"].format(plan_id=plan_id)
        )

    # Validate plan has subgoals
    if not plan.subgoals:
        return PRDResult(
            success=False,
            error=VALIDATION_MESSAGES["PRD_NO_SUBGOALS"].format(plan_id=plan_id)
        )

    # Retrieve memory context (graceful degradation)
    try:
        memory_context = retrieve_memory_context(plan.goal)
        memory_used = True
    except Exception as e:
        logger.warning(f"Memory retrieval failed: {e}")
        memory_context = []
        memory_used = False
        warnings.append(f"Memory retrieval failed: {e}. PRD will lack file references.")

    # Generate PRD sections per subgoal
    sections = []
    total_requirements = 0

    for subgoal in plan.subgoals:
        try:
            section = generate_prd_section(subgoal, memory_context)
            sections.append(section)
            total_requirements += len(section.requirements)
        except Exception as e:
            logger.error(f"Section generation failed for {subgoal.id}: {e}")
            warnings.append(f"Section {subgoal.id} generation failed: {e}")
            # Create minimal section as fallback
            sections.append(PRDSection(
                subgoal_id=subgoal.id,
                title=subgoal.title,
                agent=subgoal.recommended_agent,
                requirements=[],
                testing_strategy={}
            ))

    # Build PRD
    try:
        prd = PRD(
            plan_id=plan.plan_id,
            goal=plan.goal,
            executive_summary=generate_executive_summary(plan),
            sections=sections,
            total_requirements=total_requirements,
            memory_context_used=memory_used
        )
    except ValidationError as e:
        return PRDResult(
            success=False,
            error=VALIDATION_MESSAGES["PRD_TEMPLATE_INVALID"].format(
                errors="; ".join(str(err) for err in e.errors())
            )
        )

    # Write PRD file
    try:
        prd_markdown = render_prd_markdown(prd)
        _atomic_write(prd_path, prd_markdown)
    except Exception as e:
        return PRDResult(
            success=False,
            error=f"Failed to write PRD: {e}"
        )

    return PRDResult(
        success=True,
        prd=prd,
        prd_path=prd_path,
        sections_generated=len(sections),
        requirements_generated=total_requirements,
        memory_files_resolved=len(memory_context),
        warnings=warnings if warnings else None
    )
```

**Task Generation - Error Handling**:
```python
def generate_tasks(plan_id: str, force: bool = False) -> TaskGenerationResult:
    """
    Generate code-aware tasks with graceful degradation.
    """
    warnings = []

    # Load PRD
    plan_dir = get_plan_dir(plan_id)
    prd_path = plan_dir / "prd.md"

    if not prd_path.exists():
        return TaskGenerationResult(
            success=False,
            error=VALIDATION_MESSAGES["TASKS_PRD_NOT_FOUND"].format(plan_id=plan_id)
        )

    # Check existing tasks
    tasks_path = plan_dir / "tasks.md"
    if tasks_path.exists() and not force:
        return TaskGenerationResult(
            success=False,
            error=VALIDATION_MESSAGES["TASKS_ALREADY_EXIST"].format(plan_id=plan_id)
        )

    # Parse PRD
    try:
        prd = PRD.from_markdown(prd_path.read_text())
    except Exception as e:
        return TaskGenerationResult(
            success=False,
            error=f"Failed to parse PRD: {e}"
        )

    # Resolve file paths from memory (graceful degradation)
    files_resolved = 0
    files_missing = 0
    tasks = []

    for section in prd.sections:
        for req in section.requirements:
            # Try to resolve file paths
            resolution = resolve_file_paths(req, warnings)
            files_resolved += resolution.resolved_count
            files_missing += resolution.missing_count

            # Create task
            task = Task(
                id=f"{section.subgoal_id.split('-')[1]}.{req.id.split('.')[1]}",
                title=req.title,
                subgoal_id=section.subgoal_id,
                files=resolution.paths,
                test_file=infer_test_file(req),
                depends_on=section.dependencies
            )
            tasks.append(task)

    if files_missing > 0:
        warnings.append(
            f"{files_missing} file paths could not be resolved. "
            "Run 'aur mem index .' to refresh memory index."
        )

    # Build task list
    task_list = TaskList(
        plan_id=plan_id,
        tasks=tasks,
        total_tasks=len(tasks),
        memory_paths_resolved=files_resolved,
        memory_paths_missing=files_missing
    )

    # Write tasks file
    try:
        tasks_markdown = render_tasks_markdown(task_list)
        _atomic_write(tasks_path, tasks_markdown)
    except Exception as e:
        return TaskGenerationResult(
            success=False,
            error=f"Failed to write tasks: {e}"
        )

    return TaskGenerationResult(
        success=True,
        task_list=task_list,
        tasks_path=tasks_path,
        tasks_generated=len(tasks),
        files_resolved=files_resolved,
        files_missing=files_missing,
        warnings=warnings if warnings else None
    )
```

---

#### FR-2.8: Shell Tests for Phase 2 (per parent task)

**Test File**: `tests/shell/test_27_prd_expansion.sh`

```bash
#!/bin/bash
# Test: PRD expansion from plan
set -e

echo "=== Test 27: PRD Expansion ==="

# Setup
aur plan init --force 2>/dev/null || true
PLAN_OUTPUT=$(aur plan create "Implement user authentication with OAuth2" --json)
PLAN_ID=$(echo "$PLAN_OUTPUT" | jq -r '.plan_id')
PLAN_DIR="$HOME/.aurora/plans/active/$PLAN_ID"

# Test: Expand to PRD
echo "Expanding plan to PRD..."
aur plan expand "$PLAN_ID" --to-prd

# Verify PRD exists
if [[ ! -f "$PLAN_DIR/prd.md" ]]; then
    echo "FAIL: prd.md not created"
    exit 1
fi

# Verify PRD has required sections
PRD_CONTENT=$(cat "$PLAN_DIR/prd.md")

if ! echo "$PRD_CONTENT" | grep -q "## Executive Summary"; then
    echo "FAIL: PRD missing Executive Summary"
    exit 1
fi

if ! echo "$PRD_CONTENT" | grep -q "## Functional Requirements"; then
    echo "FAIL: PRD missing Functional Requirements"
    exit 1
fi

if ! echo "$PRD_CONTENT" | grep -q "## Testing Strategy"; then
    echo "FAIL: PRD missing Testing Strategy"
    exit 1
fi

# Verify at least 5 sections
SECTION_COUNT=$(echo "$PRD_CONTENT" | grep -c "^## " || true)
if [[ $SECTION_COUNT -lt 5 ]]; then
    echo "FAIL: PRD has only $SECTION_COUNT sections (expected ≥5)"
    exit 1
fi

echo "PASS: PRD expansion complete with $SECTION_COUNT sections"

# Cleanup
rm -rf "$PLAN_DIR"
```

**Test File**: `tests/shell/test_28_task_generation.sh`

```bash
#!/bin/bash
# Test: Task generation with file paths
set -e

echo "=== Test 28: Task Generation ==="

# Setup
aur plan init --force 2>/dev/null || true
PLAN_OUTPUT=$(aur plan create "Add logging to authentication module" --json)
PLAN_ID=$(echo "$PLAN_OUTPUT" | jq -r '.plan_id')
PLAN_DIR="$HOME/.aurora/plans/active/$PLAN_ID"

# Expand to PRD first
aur plan expand "$PLAN_ID" --to-prd

# Generate tasks
echo "Generating tasks..."
aur plan tasks "$PLAN_ID"

# Verify tasks.md exists
if [[ ! -f "$PLAN_DIR/tasks.md" ]]; then
    echo "FAIL: tasks.md not created"
    exit 1
fi

TASKS_CONTENT=$(cat "$PLAN_DIR/tasks.md")

# Verify checkboxes present
if ! echo "$TASKS_CONTENT" | grep -q "\- \[ \]"; then
    echo "FAIL: tasks.md missing checkboxes"
    exit 1
fi

# Verify file paths included (if memory indexed)
if echo "$TASKS_CONTENT" | grep -qE "\*\*File\*\*:.*\.py"; then
    echo "PASS: File paths included in tasks"
else
    echo "WARN: No file paths found (memory may not be indexed)"
fi

# Verify dependencies noted
if echo "$TASKS_CONTENT" | grep -q "Dependencies:"; then
    echo "PASS: Dependencies documented"
fi

# Count tasks
TASK_COUNT=$(echo "$TASKS_CONTENT" | grep -c "\- \[ \]" || true)
echo "Generated $TASK_COUNT tasks"

if [[ $TASK_COUNT -lt 3 ]]; then
    echo "FAIL: Expected at least 3 tasks, got $TASK_COUNT"
    exit 1
fi

echo "PASS: Task generation complete"

# Cleanup
rm -rf "$PLAN_DIR"
```

**Test File**: `tests/shell/test_29_task_code_aware.sh`

```bash
#!/bin/bash
# Test: Code-aware tasks with memory integration
set -e

echo "=== Test 29: Code-Aware Tasks ==="

# This test requires indexed memory
if ! aur mem stats 2>/dev/null | grep -q "chunks:"; then
    echo "SKIP: Memory not indexed. Run 'aur mem index .' first"
    exit 0
fi

# Setup
aur plan init --force 2>/dev/null || true
PLAN_OUTPUT=$(aur plan create "Add error handling to aurora_cli.config module" --json)
PLAN_ID=$(echo "$PLAN_OUTPUT" | jq -r '.plan_id')
PLAN_DIR="$HOME/.aurora/plans/active/$PLAN_ID"

# Full expand
aur plan expand "$PLAN_ID" --to-prd
aur plan tasks "$PLAN_ID"

TASKS_CONTENT=$(cat "$PLAN_DIR/tasks.md")

# Verify file paths resolve to actual files
FILE_PATHS=$(echo "$TASKS_CONTENT" | grep -oE '\*\*File\*\*: `[^`]+`' | sed 's/.*`\([^`]*\)`.*/\1/' || true)

RESOLVED=0
MISSING=0

for fp in $FILE_PATHS; do
    # Extract path without line numbers
    CLEAN_PATH=$(echo "$fp" | sed 's/:.*//')
    if [[ -f "$CLEAN_PATH" ]]; then
        ((RESOLVED++))
    else
        echo "WARN: File not found: $CLEAN_PATH"
        ((MISSING++))
    fi
done

echo "File paths: $RESOLVED resolved, $MISSING missing"

if [[ $MISSING -gt $RESOLVED ]]; then
    echo "FAIL: More missing files than resolved"
    exit 1
fi

echo "PASS: Code-aware task generation verified"

# Cleanup
rm -rf "$PLAN_DIR"
```

**Test File**: `tests/shell/test_30_prd_template_validation.sh`

```bash
#!/bin/bash
# Test: PRD template and schema validation
set -e

echo "=== Test 30: PRD Template Validation ==="

# Setup
aur plan init --force 2>/dev/null || true
PLAN_OUTPUT=$(aur plan create "Implement caching layer for API responses" --json)
PLAN_ID=$(echo "$PLAN_OUTPUT" | jq -r '.plan_id')
PLAN_DIR="$HOME/.aurora/plans/active/$PLAN_ID"

# Expand to PRD
aur plan expand "$PLAN_ID" --to-prd

PRD_PATH="$PLAN_DIR/prd.md"
PRD_CONTENT=$(cat "$PRD_PATH")

# Validate frontmatter YAML
echo "Checking frontmatter..."
if ! head -20 "$PRD_PATH" | grep -q "plan_id:"; then
    echo "FAIL: Missing plan_id in frontmatter"
    exit 1
fi

if ! head -20 "$PRD_PATH" | grep -q "generated_at:"; then
    echo "FAIL: Missing generated_at in frontmatter"
    exit 1
fi

# Validate required sections
REQUIRED_SECTIONS=("Executive Summary" "Goals" "Functional Requirements" "Testing Strategy" "Agent Assignments")

for section in "${REQUIRED_SECTIONS[@]}"; do
    if ! echo "$PRD_CONTENT" | grep -qi "## $section"; then
        echo "FAIL: Missing required section: $section"
        exit 1
    fi
done

# Validate FR format (FR-N.M)
FR_COUNT=$(echo "$PRD_CONTENT" | grep -cE "#### FR-[0-9]+\.[0-9]+" || true)
if [[ $FR_COUNT -lt 2 ]]; then
    echo "FAIL: Expected at least 2 FRs, found $FR_COUNT"
    exit 1
fi

# Validate acceptance criteria present
if ! echo "$PRD_CONTENT" | grep -q "Acceptance Criteria"; then
    echo "FAIL: No acceptance criteria found"
    exit 1
fi

echo "PASS: PRD template validation complete"
echo "  - Frontmatter: Valid"
echo "  - Required sections: ${#REQUIRED_SECTIONS[@]} present"
echo "  - Functional requirements: $FR_COUNT"

# Cleanup
rm -rf "$PLAN_DIR"
```

---

#### FR-2.9: Unit Test Requirements (TDD approach)

**Test-First Development Pattern**:

For each Phase 2 function, write tests BEFORE implementation:

**File**: `tests/unit/cli/test_prd_generator.py`

```python
"""
Unit tests for PRD generation.
TDD: Write these tests first, then implement to make them pass.
"""
import pytest
from pathlib import Path
from datetime import datetime
from aurora_cli.planning.prd_models import (
    PRD, PRDSection, Requirement, AcceptanceCriteria, FilePath
)
from aurora_cli.planning.prd_generator import (
    generate_prd, generate_prd_section, generate_executive_summary
)
from aurora_cli.planning.results import PRDResult


class TestPRDModels:
    """Test Pydantic models for PRD."""

    def test_requirement_valid(self):
        """Valid requirement creates successfully."""
        req = Requirement(
            id="FR-2.1",
            title="Implement OAuth login",
            description="The system shall implement OAuth2 login flow",
            acceptance_criteria=[
                AcceptanceCriteria(description="User can log in via OAuth provider")
            ]
        )
        assert req.id == "FR-2.1"

    def test_requirement_invalid_id_format(self):
        """Requirement with invalid ID raises validation error."""
        with pytest.raises(ValueError, match="FR-N.M"):
            Requirement(
                id="invalid",  # Wrong format
                title="Test requirement",
                description="Test description here",
                acceptance_criteria=[]
            )

    def test_file_path_with_lines(self):
        """FilePath formats with line numbers."""
        fp = FilePath(path="src/auth.py", line_start=42, line_end=68)
        assert fp.format() == "src/auth.py:42-68"

    def test_file_path_invalid_line_range(self):
        """FilePath validates line_end >= line_start."""
        with pytest.raises(ValueError, match="line_end"):
            FilePath(path="src/auth.py", line_start=100, line_end=50)

    def test_prd_section_valid(self):
        """Valid PRD section creates successfully."""
        section = PRDSection(
            subgoal_id="sg-1",
            title="Authentication Architecture",
            agent="@holistic-architect",
            requirements=[
                Requirement(
                    id="FR-1.1",
                    title="Design auth flow",
                    description="Design complete authentication flow",
                    acceptance_criteria=[
                        AcceptanceCriteria(description="Flow diagram created")
                    ]
                )
            ]
        )
        assert len(section.requirements) == 1


class TestPRDGeneration:
    """Test PRD generation logic."""

    def test_generate_prd_plan_not_found(self, tmp_path, monkeypatch):
        """PRD generation fails gracefully when plan not found."""
        monkeypatch.setenv("AURORA_PLANS_DIR", str(tmp_path))

        result = generate_prd("0001-nonexistent")

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_generate_prd_already_exists(self, tmp_path, sample_plan):
        """PRD generation fails if PRD exists without --force."""
        # Setup: Create plan with existing PRD
        plan_dir = tmp_path / "active" / sample_plan.plan_id
        plan_dir.mkdir(parents=True)
        (plan_dir / "agents.json").write_text(sample_plan.model_dump_json())
        (plan_dir / "prd.md").write_text("# Existing PRD")

        result = generate_prd(sample_plan.plan_id)

        assert result.success is False
        assert "already exists" in result.error.lower()

    def test_generate_prd_success(self, tmp_path, sample_plan, mock_memory):
        """PRD generation succeeds with valid plan."""
        # Setup
        plan_dir = tmp_path / "active" / sample_plan.plan_id
        plan_dir.mkdir(parents=True)
        (plan_dir / "agents.json").write_text(sample_plan.model_dump_json())

        result = generate_prd(sample_plan.plan_id)

        assert result.success is True
        assert result.prd is not None
        assert result.sections_generated >= 1
        assert (plan_dir / "prd.md").exists()

    def test_generate_prd_memory_failure_graceful(self, tmp_path, sample_plan, failing_memory):
        """PRD generates with warning when memory fails."""
        plan_dir = tmp_path / "active" / sample_plan.plan_id
        plan_dir.mkdir(parents=True)
        (plan_dir / "agents.json").write_text(sample_plan.model_dump_json())

        result = generate_prd(sample_plan.plan_id)

        assert result.success is True  # Should still succeed
        assert result.warnings is not None
        assert any("memory" in w.lower() for w in result.warnings)


class TestTaskGeneration:
    """Test task generation logic."""

    def test_generate_tasks_prd_not_found(self, tmp_path):
        """Task generation fails when PRD missing."""
        plan_dir = tmp_path / "active" / "0001-test"
        plan_dir.mkdir(parents=True)
        (plan_dir / "agents.json").write_text("{}")  # No PRD

        result = generate_tasks("0001-test")

        assert result.success is False
        assert "prd not found" in result.error.lower()

    def test_generate_tasks_with_file_resolution(self, tmp_path, sample_prd, mock_memory):
        """Tasks include resolved file paths from memory."""
        plan_dir = tmp_path / "active" / sample_prd.plan_id
        plan_dir.mkdir(parents=True)
        (plan_dir / "prd.md").write_text(render_prd_markdown(sample_prd))

        result = generate_tasks(sample_prd.plan_id)

        assert result.success is True
        assert result.files_resolved > 0

    def test_generate_tasks_missing_files_warning(self, tmp_path, sample_prd, empty_memory):
        """Task generation warns about unresolved file paths."""
        plan_dir = tmp_path / "active" / sample_prd.plan_id
        plan_dir.mkdir(parents=True)
        (plan_dir / "prd.md").write_text(render_prd_markdown(sample_prd))

        result = generate_tasks(sample_prd.plan_id)

        assert result.success is True  # Should still succeed
        assert result.files_missing > 0
        assert result.warnings is not None


# Fixtures
@pytest.fixture
def sample_plan():
    """Sample plan for testing."""
    from aurora_cli.planning.models import Plan, Subgoal
    return Plan(
        plan_id="0001-test-auth",
        goal="Implement authentication system",
        subgoals=[
            Subgoal(
                id="sg-1",
                title="Design auth flow",
                description="Design the authentication flow",
                recommended_agent="@holistic-architect"
            ),
            Subgoal(
                id="sg-2",
                title="Implement auth",
                description="Implement authentication logic",
                recommended_agent="@full-stack-dev",
                dependencies=["sg-1"]
            )
        ]
    )


@pytest.fixture
def sample_prd():
    """Sample PRD for testing."""
    return PRD(
        plan_id="0001-test-auth",
        goal="Implement authentication system",
        executive_summary="Implement OAuth2 authentication...",
        sections=[
            PRDSection(
                subgoal_id="sg-1",
                title="Design auth flow",
                agent="@holistic-architect",
                requirements=[
                    Requirement(
                        id="FR-1.1",
                        title="Design OAuth flow",
                        description="Design complete OAuth2 flow",
                        acceptance_criteria=[
                            AcceptanceCriteria(description="Flow diagram exists")
                        ]
                    )
                ]
            )
        ]
    )


@pytest.fixture
def mock_memory(monkeypatch):
    """Mock memory retrieval that returns sample files."""
    def mock_retrieve(*args, **kwargs):
        return [
            {"path": "src/auth/oauth.py", "confidence": 0.9},
            {"path": "src/models/user.py", "confidence": 0.85}
        ]
    monkeypatch.setattr("aurora_cli.planning.prd_generator.retrieve_memory_context", mock_retrieve)


@pytest.fixture
def empty_memory(monkeypatch):
    """Mock memory that returns nothing."""
    def mock_retrieve(*args, **kwargs):
        return []
    monkeypatch.setattr("aurora_cli.planning.prd_generator.retrieve_memory_context", mock_retrieve)


@pytest.fixture
def failing_memory(monkeypatch):
    """Mock memory that fails."""
    def mock_retrieve(*args, **kwargs):
        raise Exception("Memory retrieval failed")
    monkeypatch.setattr("aurora_cli.planning.prd_generator.retrieve_memory_context", mock_retrieve)
```

---

### 4.3 Phase 3: Execution & Delegation

#### FR-3.1: Slash Command: `/aur:implement` (Claude Code Integration)

**MUST** execute plan by delegating to agents via slash command:

```bash
# Execute plan
/aur:implement 0001-oauth-auth

# Execute by ID only
/aur:implement 0001
```

**Note**: This is a **slash command** for Claude Code, not a CLI command. It spawns agent subprocesses for each subgoal.

**Execution Pipeline**:

**Step 1: Load Plan and State**
```python
def load_execution_state(plan_id: str) -> ExecutionState:
    """
    Load execution state from state.json.

    State includes:
    - Current subgoal index
    - Completed subgoals
    - Task completion checkboxes
    - Agent selections (for gaps)
    """
    plan_dir = Path(f"~/.aurora/plans/active/{plan_id}")
    state_file = plan_dir / "state.json"

    if state_file.exists():
        return ExecutionState.from_json(state_file)
    else:
        return ExecutionState.new(plan_id)
```

**Step 2: Validate Agents**
```python
def validate_agents(plan: Plan, agents: list[AgentInfo]) -> list[AgentGap]:
    """
    Validate all recommended agents exist.

    Returns list of gaps for user prompts.
    """
    gaps = []

    for subgoal in plan.subgoals:
        agent_id = subgoal.recommended_agent.strip("@")

        if not agent_exists(agent_id, agents):
            gap = AgentGap(
                subgoal_id=subgoal.id,
                missing_agent=agent_id,
                fallback_suggestions=find_similar_agents(agent_id, agents)
            )
            gaps.append(gap)

    return gaps
```

**Step 3: Prompt for Gap Resolution**
```python
def resolve_agent_gaps(
    gaps: list[AgentGap],
    interactive: bool
) -> dict[str, str]:
    """
    Resolve agent gaps via user prompts.

    Interactive mode: Prompt for each gap
    Non-interactive mode: Use first fallback
    """
    resolutions = {}

    for gap in gaps:
        if interactive:
            choice = prompt_user(
                f"Agent @{gap.missing_agent} not found for {gap.subgoal_id}. "
                f"Options:\n"
                f"1) Use fallback: @{gap.fallback_suggestions[0]}\n"
                f"2) Skip this subgoal\n"
                f"3) Abort execution\n"
                f"Choice: "
            )
            resolutions[gap.subgoal_id] = handle_choice(choice, gap)
        else:
            # Auto-select first fallback
            resolutions[gap.subgoal_id] = gap.fallback_suggestions[0]

    return resolutions
```

**Step 4: Execute Subgoals Sequentially**
```python
def execute_subgoals(
    plan: Plan,
    state: ExecutionState,
    agent_resolutions: dict[str, str]
) -> ExecutionResult:
    """
    Execute subgoals sequentially, respecting dependencies.

    For each subgoal:
    1. Check dependencies completed
    2. Spawn agent subprocess
    3. Collect results
    4. Update state and checkboxes
    5. Save checkpoint
    """
    for subgoal in plan.subgoals:
        # Skip if already completed
        if state.is_completed(subgoal.id):
            continue

        # Check dependencies
        if not state.dependencies_met(subgoal.dependencies):
            raise DependencyError(f"{subgoal.id} blocked by incomplete dependencies")

        # Resolve agent
        agent_id = agent_resolutions.get(
            subgoal.id,
            subgoal.recommended_agent.strip("@")
        )

        # Spawn agent subprocess
        result = spawn_agent(
            agent_id=agent_id,
            subgoal=subgoal,
            context=load_context(plan)
        )

        # Update state
        state.mark_completed(subgoal.id, result)
        update_task_checkboxes(plan.id, subgoal.id, completed=True)
        save_checkpoint(state)

        # Handle errors
        if result.status == "failed":
            return handle_failure(subgoal, result, state)

    return ExecutionResult(status="success", state=state)
```

**Step 5: Spawn Agent Subprocess**
```python
def spawn_agent(
    agent_id: str,
    subgoal: Subgoal,
    context: ContextData
) -> AgentResult:
    """
    Spawn specialized agent in subprocess.

    Subprocess command:
    aur agent run <agent-id> \
      --goal "<subgoal.description>" \
      --context <context-files> \
      --output <results-dir>

    Returns:
    - status: success | failed | timeout
    - output: Agent's deliverables
    - duration: Execution time
    """
    cmd = [
        "aur", "agent", "run", agent_id,
        "--goal", subgoal.description,
        "--context", *context.file_paths,
        "--output", f"~/.aurora/plans/active/{plan.id}/results/{subgoal.id}"
    ]

    result = subprocess.run(
        cmd,
        timeout=3600,  # 1 hour timeout
        capture_output=True
    )

    return AgentResult.from_subprocess(result)
```

**State Schema** (state.json):
```json
{
  "plan_id": "0001-oauth-auth",
  "status": "in_progress",
  "started_at": "2026-01-15T15:00:00Z",
  "current_subgoal": "sg-2",
  "completed_subgoals": ["sg-1"],
  "agent_resolutions": {
    "sg-4": "business-analyst"
  },
  "task_progress": {
    "sg-1": {"total": 3, "completed": 3},
    "sg-2": {"total": 4, "completed": 2}
  },
  "checkpoints": [
    {
      "subgoal_id": "sg-1",
      "completed_at": "2026-01-15T15:30:00Z",
      "duration_minutes": 30
    }
  ]
}
```

**Output** (during execution):
```
Executing Plan: 0001-oauth-auth
================================================================================

Subgoal 1: Research & Architecture (@business-analyst)
--------------------------------------------------------------------------------
[15:00:00] Starting agent subprocess...
[15:15:00] Agent completed research
[15:15:01] Results saved to results/sg-1/
[15:15:01] ✓ Subgoal 1 completed (15 minutes)

Subgoal 2: Backend Implementation (@full-stack-dev)
--------------------------------------------------------------------------------
[15:15:02] Starting agent subprocess...
[15:45:00] Agent completed implementation
[15:45:01] Results saved to results/sg-2/
[15:45:01] ✓ Subgoal 2 completed (30 minutes)

Subgoal 3: Testing & QA (@qa-test-architect)
--------------------------------------------------------------------------------
[15:45:02] Starting agent subprocess...
[16:10:00] Agent completed testing
[16:10:01] Results saved to results/sg-3/
[16:10:01] ✓ Subgoal 3 completed (25 minutes)

Subgoal 4: Documentation (@technical-writer)
--------------------------------------------------------------------------------
⚠ Agent @technical-writer not found

Options:
1) Use fallback: @business-analyst
2) Skip this subgoal
3) Abort execution

Choice: 1

[16:10:05] Using fallback: @business-analyst
[16:10:05] Starting agent subprocess...
[16:30:00] Agent completed documentation
[16:30:01] Results saved to results/sg-4/
[16:30:01] ✓ Subgoal 4 completed (20 minutes)

================================================================================
Execution Complete!

Total Duration: 1 hour 30 minutes
Subgoals Completed: 4 / 4
Tasks Completed: 12 / 12

Results: ~/.aurora/plans/active/0001-oauth-auth/results/

Next steps:
1. Review agent outputs in results/
2. Run tests: pytest
3. Archive plan: aur plan archive 0001
```

**Requirements**:
- Load plan and execution state
- Validate agents before execution
- Prompt for gap resolution (interactive) or auto-fallback
- Execute subgoals sequentially with dependency checking
- Spawn agent subprocesses with timeout
- Update task checkboxes in tasks.md
- Save state checkpoints after each subgoal
- Support resume from checkpoint
- Dry-run mode for validation
- Latency target: <5s to start, variable execution time

---

#### FR-3.2: Command: `/aur:implement`

**MUST** implement slash command for execution:

```bash
# Execute from Claude Code
/aur:implement 0001

# Resume execution
/aur:implement 0001 --resume
```

**Implementation**:
```python
@slash_command("aur:implement")
def slash_implement(plan_id: str, **kwargs):
    """
    Execute plan from Claude Code.

    Delegates to: aur plan execute
    Streams output to chat in real-time
    """
    process = subprocess.Popen([
        "aur", "plan", "execute", plan_id,
        *parse_kwargs(kwargs)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Stream output line by line
    for line in process.stdout:
        yield line.decode()

    return process.returncode
```

**Requirements**:
- Stream execution output to chat
- Support --resume flag
- Error handling with formatted messages
- Cancel support (Ctrl+C propagates to subprocess)

---

#### FR-3.3: Progress Tracking via Checkbox Parsing

**MUST** update task checkboxes during execution:

**tasks.md Before Execution**:
```markdown
## Subgoal 2: Backend Implementation (@full-stack-dev)

- [ ] 2.1 Modify User model with OAuth fields
- [ ] 2.2 Create Auth0 SDK wrapper
- [ ] 2.3 Implement /auth/login endpoint
- [ ] 2.4 Implement /auth/callback endpoint
```

**tasks.md During Execution** (after 2.1 and 2.2 complete):
```markdown
## Subgoal 2: Backend Implementation (@full-stack-dev)

- [x] 2.1 Modify User model with OAuth fields
- [x] 2.2 Create Auth0 SDK wrapper
- [ ] 2.3 Implement /auth/login endpoint
- [ ] 2.4 Implement /auth/callback endpoint
```

**Implementation**:
```python
def update_task_checkboxes(plan_id: str, subgoal_id: str, completed: bool):
    """
    Update checkboxes in tasks.md for completed subgoal.

    Strategy:
    1. Parse tasks.md to extract all tasks
    2. Find tasks belonging to subgoal_id
    3. Update checkbox state: [ ] → [x]
    4. Write back to tasks.md
    """
    tasks_file = Path(f"~/.aurora/plans/active/{plan_id}/tasks.md")
    content = tasks_file.read_text()

    # Parse markdown to extract tasks
    tasks = parse_markdown_tasks(content)

    # Update checkboxes for subgoal
    for task in tasks:
        if task.subgoal_id == subgoal_id:
            task.completed = completed

    # Write back
    updated_content = render_markdown_tasks(tasks)
    tasks_file.write_text(updated_content)
```

**Requirements**:
- Parse markdown checkboxes
- Update in-place without corrupting file
- Atomic write (temp file + rename)
- Preserve task descriptions and formatting

---

### 4.8 Integration with PRD 0016: Agent Discovery & Memory Retrieval

This section documents how Aurora Planning System **reuses** components from PRD 0016 (Agent Discovery & Planning CLI).

#### 4.8.1 Memory Retrieval Strategy (from PRD 0016, Section 5.2)

**Component**: `packages/cli/src/aurora_cli/memory/retrieval.py`

```python
# From PRD 0016: Section 5.2 "Memory Retrieval Integration"
def retrieve_context_for_planning(goal: str, limit: int = 20) -> list[CodeChunk]:
    """
    Uses Aurora's hybrid search (BM25 + semantic + ACT-R activation)
    to find relevant files for planning context.

    Called by: FR-1.2 Step 2 (Context Retrieval)
    """
    memory = MemoryManager()
    chunks = memory.search(
        query=goal,
        limit=limit,
        search_mode='hybrid'  # 60% semantic, 40% activation
    )
    return chunks
```

**Integration Points**:
- Called during `/aur:plan` SOAR decomposition
- Provides context files for agent recommendations
- Used for file path resolution in task generation (FR-2.2)

**Cross-Reference**: PRD 0016, Section 5.2 "Memory Retrieval Integration"

---

#### 4.8.2 Agent Recommendation Algorithm (from PRD 0016, Section 5.3.2)

**Component**: `packages/cli/src/aurora_cli/agents/recommendation.py`

```python
# From PRD 0016: Section 5.3.2 "Agent Recommendation"
def recommend_agents_for_subgoals(
    plan: Plan,
    agents: list[AgentInfo]
) -> tuple[Plan, list[AgentGap]]:
    """
    Algorithm:
    1. For each subgoal, extract capability keywords from description
    2. Search agents by capability match (skills field)
    3. Rank by keyword overlap
    4. Assign top-ranked agent to subgoal
    5. If no good match (score < 0.5), mark as gap

    Called by: FR-1.2 Step 4 (Generate Plan Files)
    """
    agent_gaps = []
    for subgoal in plan.subgoals:
        keywords = extract_capability_keywords(subgoal.description)
        best_match, score = find_best_agent_match(keywords, agents)

        if score >= 0.5:
            subgoal.recommended_agent = f"@{best_match.id}"
            subgoal.agent_exists = True
        else:
            gap = AgentGap(
                subgoal_id=subgoal.id,
                recommended_agent=infer_agent_name(keywords),
                agent_exists=False,
                suggested_capabilities=keywords,
                fallback=suggest_fallback_agent(keywords, agents)
            )
            agent_gaps.append(gap)
    return plan, agent_gaps
```

**Integration Points**:
- Called during plan generation (FR-1.2)
- Populates `recommended_agent` field in agents.json
- Used in gap detection UI (FR-3.2)

**Cross-Reference**: PRD 0016, Section 5.3.2 "Agent Recommendation"

---

#### 4.8.3 Gap Detection & Manifest Update (from PRD 0016, Section 5.3.4)

**Component**: `packages/cli/src/aurora_cli/agents/gap_detection.py`

```python
# From PRD 0016: Section 5.3.4 "Gap Detection"
class AgentGap(BaseModel):
    """
    Represents a missing agent type needed for a subgoal.
    Stored in agents.json for tooling visibility.
    """
    subgoal_id: str
    recommended_agent: str        # e.g., "@security-specialist"
    agent_exists: bool            # False
    suggested_capabilities: list[str]  # ["crypto", "secure-storage"]
    fallback: str                 # e.g., "@full-stack-dev"
    impact: str                   # "Medium - May lack specialized knowledge"

def detect_and_suggest_agents(plan: Plan, agents: list[AgentInfo]) -> list[AgentGap]:
    """
    Identifies missing agent types and suggests new manifest entries.
    Output used in agents.json for tooling visibility.

    Called by: FR-1.2 Step 4, FR-3.2 (Gap Prompting)
    """
    gaps = []
    for subgoal in plan.subgoals:
        if not subgoal.agent_exists:
            gap = AgentGap(
                subgoal_id=subgoal.id,
                recommended_agent=subgoal.recommended_agent,
                agent_exists=False,
                suggested_capabilities=extract_capability_keywords(subgoal.description),
                fallback=suggest_fallback_agent(subgoal, agents),
                impact=assess_impact(subgoal)
            )
            gaps.append(gap)
    return gaps
```

**Integration Points**:
- Called after agent recommendation (FR-1.2)
- Powers interactive gap prompts during `/aur:implement` (FR-3.2)
- Stored in `agent_gaps` array in agents.json

**Cross-Reference**: PRD 0016, Section 5.3.4 "Gap Detection"

---

#### 4.8.4 Reuse Summary Table

| PRD 0016 Component | Used In Aurora Planning | Section Reference |
|--------------------|------------------------|-------------------|
| Memory Retrieval (`MemoryManager.search`) | Context for SOAR decomposition, file path resolution | FR-1.2 Step 2, FR-2.2 Step 2 |
| Agent Recommendation (`recommend_agents_for_subgoals`) | Assign agents to subgoals | FR-1.2 Step 4 |
| Gap Detection (`detect_and_suggest_agents`) | Identify missing agents, power prompts | FR-1.2 Step 4, FR-3.2 |
| Agent Manifest (`AgentInfo` model) | Load available agents, match capabilities | FR-1.2, FR-3.1 |

**Key Principle**: **Don't reimplement what exists**. PRD 0016 already provides:
- Agent discovery from `~/.claude/agents/`
- Capability-based matching
- Gap detection logic
- Memory-integrated context retrieval

Aurora Planning System **orchestrates** these components into a cohesive planning workflow.

---

## 5. FILE FORMATS & EXAMPLES

### 5.1 plan.md (SOAR Output)

High-level plan with subgoals and agent assignments.

```markdown
# Plan: Implement OAuth2 Authentication

**Plan ID**: 0001-oauth-auth
**Created**: 2026-01-15 10:30:00
**Status**: active
**Complexity**: complex

## Goal

Implement OAuth2 authentication using Auth0 to replace password-based login system.

## Context

5 relevant files indexed:
- src/models/user.py (User model with password auth)
- src/api/routes.py (Login/logout endpoints)
- src/auth/password.py (Password hashing utilities)
- tests/test_auth.py (Authentication tests)
- docs/architecture.md (System architecture)

## Subgoals

### Subgoal 1: Research & Architecture
**Agent**: @business-analyst ✓
**Dependencies**: None
**Estimated Time**: 4-6 hours

Evaluate OAuth2 providers (Auth0, Okta, custom) and design authentication architecture including flow diagrams, security assessment, and migration strategy.

**Key Decisions**:
- OAuth2 provider selection
- Authentication flow design
- Security compliance (OWASP, GDPR)

---

### Subgoal 2: Backend Implementation
**Agent**: @full-stack-dev ✓
**Dependencies**: Subgoal 1
**Estimated Time**: 8-12 hours

Implement Auth0 SDK integration, extend User model with OAuth fields, create API endpoints for login/callback/refresh/logout flows.

**Key Tasks**:
- Extend User model with oauth_provider, oauth_id, tokens
- Integrate Auth0 SDK
- Implement /auth/login, /auth/callback, /auth/refresh, /auth/logout
- Handle token storage and refresh

---

### Subgoal 3: Testing & QA
**Agent**: @qa-test-architect ✓
**Dependencies**: Subgoal 2
**Estimated Time**: 6-8 hours

Design comprehensive test strategy and implement tests covering unit (models), integration (Auth0 SDK), end-to-end (full flow), and security (token handling).

**Test Coverage**:
- Unit: User model OAuth methods
- Integration: Auth0 client wrapper
- E2E: Full login flow
- Security: Token expiration, CSRF, revocation

---

### Subgoal 4: Documentation
**Agent**: @technical-writer ⚠ NOT FOUND
**Dependencies**: Subgoal 3
**Estimated Time**: 4-6 hours

Create API documentation, integration guides, and troubleshooting resources.

⚠ **Agent Gap Detected**:
- Missing agent: @technical-writer
- Suggested capabilities: technical-writing, api-documentation, user-guides
- Fallback options: @business-analyst, @full-stack-dev
- Recommendation: Consider creating technical-writer agent

**Documentation Deliverables**:
- API documentation (OpenAPI spec)
- Integration guide for developers
- Troubleshooting guide

---

## Agent Assignments

| Subgoal | Agent | Status |
|---------|-------|--------|
| 1. Research & Architecture | @business-analyst | ✓ Found |
| 2. Backend Implementation | @full-stack-dev | ✓ Found |
| 3. Testing & QA | @qa-test-architect | ✓ Found |
| 4. Documentation | @technical-writer | ⚠ Not found |

**Agent Gaps**: 1 (Documentation requires fallback)

## Next Steps

1. Review this plan for accuracy
2. Expand to detailed PRD: `aur plan expand 0001 --to-prd`
3. Generate code-aware tasks: `aur plan tasks 0001`
4. Execute with agent delegation: `aur plan execute 0001`
```

---

### 5.2 prd.md (Detailed Requirements)

Generated by `aur plan expand --to-prd`. Follows OpenSpec conventions.

```markdown
# PRD: Implement OAuth2 Authentication

**Plan ID**: 0001-oauth-auth
**Generated**: 2026-01-15 12:00:00
**Base Plan**: plan.md

## Executive Summary

Replace password-based authentication with OAuth2 using Auth0 as identity provider. Provides secure token-based authentication with automatic refresh and logout capabilities.

## Goals

1. **Security**: Eliminate password storage, use industry-standard OAuth2
2. **User Experience**: Single sign-on with Auth0, faster login
3. **Maintainability**: Reduce authentication code complexity
4. **Compliance**: OWASP security standards, GDPR-compliant token handling

## Success Metrics

- Login latency <2s (vs 3s password-based)
- Zero password breaches (down from potential risk)
- Test coverage ≥90% for auth code
- Zero critical security vulnerabilities

---

## Functional Requirements

### Subgoal 1: Research & Architecture (@business-analyst)

#### FR-1.1: OAuth2 Provider Evaluation

The system SHALL evaluate Auth0, Okta, and custom OAuth2 implementation.

**Acceptance Criteria**:
- Comparison table includes: cost, features, security, scalability
- Recommendation documented with rationale
- Risk assessment per provider
- Migration complexity analysis

**Deliverable**: `docs/oauth-research.md`

#### Scenario: Auth0 selected
- **GIVEN** evaluation complete
- **WHEN** Auth0 offers best cost/feature balance
- **THEN** recommendation documented with migration plan

---

#### FR-1.2: Authentication Flow Design

The system SHALL design complete OAuth2 flow diagram.

**Acceptance Criteria**:
- Sequence diagram shows: login → Auth0 redirect → callback → token exchange → session creation
- Error handling documented for each step
- Session management strategy defined
- Token refresh strategy documented

**Deliverable**: `docs/auth-flow.md` (Mermaid diagram)

#### Scenario: User login success
- **GIVEN** user clicks "Login with Auth0"
- **WHEN** user authenticates on Auth0
- **THEN** callback receives auth code, exchanges for tokens, creates session

#### Scenario: Token expired
- **GIVEN** user has expired access token
- **WHEN** API request made
- **THEN** system uses refresh token to get new access token

---

### Subgoal 2: Backend Implementation (@full-stack-dev)

#### FR-2.1: User Model Extension

The system SHALL extend User model with OAuth fields.

**Files to Modify**:
- `src/models/user.py` lines 15-30

**Changes Required**:
```python
class User(Base):
    # Existing fields...

    # NEW: OAuth fields
    oauth_provider: str | None  # "auth0", "okta", etc.
    oauth_id: str | None        # Provider's user ID
    access_token: str | None    # Encrypted access token
    refresh_token: str | None   # Encrypted refresh token
    token_expires_at: datetime | None

    def get_oauth_token(self) -> str:
        """Get decrypted access token."""
        pass

    def refresh_oauth_token(self) -> bool:
        """Refresh access token using refresh token."""
        pass
```

**Acceptance Criteria**:
- Migration file creates oauth_* columns (nullable for existing users)
- Tokens encrypted at rest using Fernet
- Methods implemented: get_oauth_token(), refresh_oauth_token(), revoke_oauth_token()
- Unit tests cover all OAuth methods

**Tests**: `tests/models/test_user_oauth.py`

#### Scenario: New OAuth user created
- **GIVEN** successful Auth0 callback
- **WHEN** user doesn't exist in database
- **THEN** User created with oauth_provider="auth0", oauth_id=<auth0_id>, tokens stored encrypted

#### Scenario: Existing user migrates to OAuth
- **GIVEN** user has password authentication
- **WHEN** user logs in with OAuth
- **THEN** User record updated with OAuth fields, password kept for backward compatibility

---

#### FR-2.2: Auth0 SDK Integration

The system SHALL create Auth0 client wrapper.

**Files to Create**:
- `src/auth/oauth.py` (NEW)

**Implementation**:
```python
from auth0 import Auth0  # pip install auth0-python

class OAuth2Client:
    def __init__(self, domain: str, client_id: str, client_secret: str):
        self.auth0 = Auth0(domain, client_id, client_secret)

    def get_authorization_url(self, redirect_uri: str) -> str:
        """Generate Auth0 authorization URL."""
        pass

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for access/refresh tokens."""
        pass

    def refresh_access_token(self, refresh_token: str) -> dict:
        """Use refresh token to get new access token."""
        pass

    def revoke_token(self, token: str):
        """Revoke access or refresh token."""
        pass
```

**Acceptance Criteria**:
- Auth0 SDK configured with environment variables (AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET)
- All methods handle Auth0 API errors gracefully
- Integration tests mock Auth0 responses
- Real Auth0 test runs in staging environment

**Tests**: `tests/integration/test_oauth_client.py`

#### Scenario: Token exchange success
- **GIVEN** valid authorization code
- **WHEN** exchange_code_for_token() called
- **THEN** returns dict with access_token, refresh_token, expires_in

#### Scenario: Auth0 API error
- **GIVEN** Auth0 API returns 500 error
- **WHEN** any OAuth method called
- **THEN** raises OAuth2Error with user-friendly message

---

#### FR-2.3: Authentication Endpoints

The system SHALL implement OAuth2 API endpoints.

**Files to Modify**:
- `src/api/routes.py` lines 78-150

**Endpoints to Add**:

**GET /auth/login**
```python
@app.get("/auth/login")
def login():
    """Redirect to Auth0 authorization page."""
    redirect_uri = f"{settings.BASE_URL}/auth/callback"
    auth_url = oauth_client.get_authorization_url(redirect_uri)
    return RedirectResponse(auth_url)
```

**GET /auth/callback**
```python
@app.get("/auth/callback")
def callback(code: str):
    """Handle Auth0 callback, exchange code for tokens."""
    tokens = oauth_client.exchange_code_for_token(code, redirect_uri)
    user = get_or_create_oauth_user(tokens)
    session = create_session(user, tokens)
    return RedirectResponse("/dashboard")
```

**POST /auth/refresh**
```python
@app.post("/auth/refresh")
def refresh(refresh_token: str):
    """Refresh access token."""
    tokens = oauth_client.refresh_access_token(refresh_token)
    return tokens
```

**POST /auth/logout**
```python
@app.post("/auth/logout")
def logout(access_token: str):
    """Revoke tokens and end session."""
    oauth_client.revoke_token(access_token)
    return {"status": "logged out"}
```

**Acceptance Criteria**:
- All endpoints return proper HTTP status codes (200, 302, 400, 500)
- CSRF protection enabled
- Rate limiting applied (10 req/min per IP)
- API tests cover success + error paths

**Tests**: `tests/api/test_auth_endpoints.py`

#### Scenario: Login flow
- **GIVEN** user visits /auth/login
- **WHEN** endpoint called
- **THEN** redirects to Auth0 with correct client_id and redirect_uri

#### Scenario: Callback with invalid code
- **GIVEN** Auth0 callback with invalid code
- **WHEN** /auth/callback called
- **THEN** returns 400 error with message "Invalid authorization code"

---

### Subgoal 3: Testing & QA (@qa-test-architect)

#### FR-3.1: Test Strategy Design

The system SHALL define comprehensive test strategy.

**Coverage Requirements**:
- Unit tests: 100% for User model OAuth methods
- Integration tests: Auth0 SDK wrapper with mocked responses
- E2E tests: Full login flow (login → callback → dashboard)
- Security tests: Token expiration, CSRF, SQL injection, XSS

**Deliverable**: `docs/test-strategy-oauth.md`

**Acceptance Criteria**:
- Test plan document includes: test types, coverage targets, tools, environments
- Risk assessment per test category
- Definition of done for testing phase

---

#### FR-3.2: Unit Tests Implementation

The system SHALL implement unit tests for OAuth components.

**Files to Create**:
- `tests/models/test_user_oauth.py`
- `tests/auth/test_oauth_client.py`

**Coverage**:
- User.get_oauth_token() - decrypt and return token
- User.refresh_oauth_token() - call Auth0, update tokens
- OAuth2Client.exchange_code_for_token() - mock Auth0 response
- OAuth2Client.refresh_access_token() - mock refresh flow

**Acceptance Criteria**:
- All tests pass
- Coverage ≥95% for oauth-related code
- Tests use pytest fixtures for setup/teardown
- No test flakiness (3 consecutive runs pass)

---

#### FR-3.3: Integration Tests Implementation

The system SHALL implement integration tests with Auth0 SDK.

**Files to Create**:
- `tests/integration/test_auth0_client.py`
- `tests/integration/test_auth_endpoints.py`

**Test Cases**:
- Token exchange with mocked Auth0 API
- Token refresh with mocked Auth0 API
- Error handling for Auth0 API failures
- Full endpoint flow: /auth/login → /auth/callback → session created

**Acceptance Criteria**:
- Tests use requests-mock for Auth0 API mocking
- All error scenarios covered (network error, 401, 500)
- Database state verified after each test
- Tests run in isolated database transactions

---

#### FR-3.4: Security Tests Implementation

The system SHALL implement security tests.

**Files to Create**:
- `tests/security/test_auth_security.py`

**Test Cases**:
- Token expiration handling (expired token → refresh → new token)
- CSRF token validation (missing CSRF → 403 error)
- SQL injection attempts in OAuth fields
- XSS attempts in user profile data from Auth0
- Token revocation (revoked token → 401 error)

**Acceptance Criteria**:
- All OWASP top-10 vulnerabilities tested
- Security scanner (bandit) passes with zero critical issues
- Penetration testing checklist completed
- No hardcoded secrets in tests (use environment variables)

---

### Subgoal 4: Documentation (@technical-writer - FALLBACK: @business-analyst)

#### FR-4.1: API Documentation

The system SHALL provide complete API documentation.

**Files to Create**:
- `docs/api/oauth-endpoints.md` (OpenAPI spec)

**Content Requirements**:
- All 4 endpoints documented: /auth/login, /auth/callback, /auth/refresh, /auth/logout
- Request/response schemas with examples
- Error codes and messages
- Authentication requirements
- Rate limiting details

**Acceptance Criteria**:
- OpenAPI spec validates with swagger-cli
- Examples executable via curl commands
- All error codes documented

---

#### FR-4.2: Integration Guide

The system SHALL provide developer integration guide.

**Files to Create**:
- `docs/guides/oauth-integration.md`

**Content Requirements**:
- Step-by-step setup instructions
- Environment variable configuration
- Auth0 dashboard setup guide
- Code examples for frontend integration
- Migration guide for existing password users

**Acceptance Criteria**:
- Guide tested by 2 developers (both successfully integrate)
- All code examples run without errors
- Screenshots included for Auth0 dashboard setup

---

## Testing Strategy Summary

| Test Type | Coverage Target | Tools | Owner |
|-----------|----------------|-------|-------|
| Unit | ≥95% | pytest, pytest-cov | @full-stack-dev |
| Integration | Key flows | pytest, requests-mock | @qa-test-architect |
| E2E | Full user journey | pytest, selenium | @qa-test-architect |
| Security | OWASP top-10 | bandit, safety | @qa-test-architect |

---

## Agent Assignments

1. **Research & Architecture**: @business-analyst
2. **Backend Implementation**: @full-stack-dev
3. **Testing & QA**: @qa-test-architect
4. **Documentation**: @technical-writer (⚠ NOT FOUND - use @business-analyst)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Auth0 API downtime | Users can't log in | Implement retry logic + fallback to cached tokens |
| Token leakage | Security breach | Encrypt tokens at rest, use HTTPS only, short expiration |
| Migration complexity | User confusion | Gradual rollout, support both password + OAuth for 3 months |

---

## Timeline Estimate

- Research & Architecture: 4-6 hours
- Backend Implementation: 8-12 hours
- Testing & QA: 6-8 hours
- Documentation: 4-6 hours

**Total**: 22-32 hours (3-4 days)

---

## Approval

- [ ] Product Manager reviewed
- [ ] Architect reviewed
- [ ] Security reviewed
- [ ] Ready for implementation

**Generated by**: Aurora Planning System v1.0
**Next**: Generate tasks with `aur plan tasks 0001`
```

---

### 5.3 tasks.md (Code-Aware Tasks)

Generated by `aur plan tasks`. Includes file paths, line numbers, checkboxes.

*(See FR-2.2 example above for complete tasks.md format)*

---

### 5.4 agents.json (Machine-Readable Plan)

```json
{
  "plan_id": "0001-oauth-auth",
  "goal": "Implement OAuth2 authentication",
  "created_at": "2026-01-15T10:30:00Z",
  "status": "active",
  "complexity": "complex",
  "context_sources": ["indexed_memory"],
  "context_files": [
    "src/models/user.py",
    "src/api/routes.py",
    "src/auth/password.py",
    "tests/test_auth.py",
    "docs/architecture.md"
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Research & Architecture",
      "description": "Evaluate OAuth2 providers and design authentication architecture",
      "recommended_agent": "@business-analyst",
      "agent_exists": true,
      "dependencies": [],
      "estimated_hours": "4-6",
      "deliverables": [
        "docs/oauth-research.md",
        "docs/auth-flow.md",
        "docs/security-review.md"
      ]
    },
    {
      "id": "sg-2",
      "title": "Backend Implementation",
      "description": "Implement Auth0 SDK integration and API endpoints",
      "recommended_agent": "@full-stack-dev",
      "agent_exists": true,
      "dependencies": ["sg-1"],
      "estimated_hours": "8-12",
      "files_to_modify": [
        {"path": "src/models/user.py", "lines": "15-30"},
        {"path": "src/api/routes.py", "lines": "78-150"}
      ],
      "files_to_create": [
        "src/auth/oauth.py"
      ],
      "deliverables": [
        "User model with OAuth fields",
        "Auth0 client wrapper",
        "OAuth API endpoints"
      ]
    },
    {
      "id": "sg-3",
      "title": "Testing & QA",
      "description": "Design test strategy and implement comprehensive tests",
      "recommended_agent": "@qa-test-architect",
      "agent_exists": true,
      "dependencies": ["sg-2"],
      "estimated_hours": "6-8",
      "files_to_create": [
        "tests/models/test_user_oauth.py",
        "tests/integration/test_oauth_client.py",
        "tests/api/test_auth_endpoints.py",
        "tests/security/test_auth_security.py",
        "docs/test-strategy-oauth.md"
      ],
      "deliverables": [
        "Test strategy document",
        "Unit tests (≥95% coverage)",
        "Integration tests",
        "Security tests"
      ]
    },
    {
      "id": "sg-4",
      "title": "Documentation",
      "description": "Create API docs and integration guides",
      "recommended_agent": "@technical-writer",
      "agent_exists": false,
      "dependencies": ["sg-3"],
      "estimated_hours": "4-6",
      "files_to_create": [
        "docs/api/oauth-endpoints.md",
        "docs/guides/oauth-integration.md"
      ],
      "deliverables": [
        "OpenAPI spec",
        "Integration guide"
      ]
    }
  ],
  "agent_gaps": [
    {
      "subgoal_id": "sg-4",
      "subgoal_title": "Documentation",
      "recommended_agent": "@technical-writer",
      "agent_exists": false,
      "reason": "No agent found with technical writing capabilities",
      "suggested_capabilities": [
        "technical-writing",
        "api-documentation",
        "developer-guides"
      ],
      "fallback_suggestions": [
        "@business-analyst",
        "@full-stack-dev"
      ],
      "impact": "Medium - Documentation quality may be lower without specialized writer"
    }
  ],
  "validation": {
    "all_agents_exist": false,
    "missing_agent_count": 1,
    "total_subgoals": 4
  },
  "metadata": {
    "estimated_time_hours": "22-32",
    "estimated_days": "3-4"
  }
}
```

---

### 5.5 state.json (Execution State)

```json
{
  "plan_id": "0001-oauth-auth",
  "status": "in_progress",
  "started_at": "2026-01-15T15:00:00Z",
  "current_subgoal": "sg-3",
  "completed_subgoals": ["sg-1", "sg-2"],
  "agent_resolutions": {
    "sg-4": "business-analyst"
  },
  "task_progress": {
    "sg-1": {"total": 3, "completed": 3},
    "sg-2": {"total": 4, "completed": 4},
    "sg-3": {"total": 4, "completed": 2},
    "sg-4": {"total": 2, "completed": 0}
  },
  "checkpoints": [
    {
      "subgoal_id": "sg-1",
      "agent_id": "business-analyst",
      "started_at": "2026-01-15T15:00:00Z",
      "completed_at": "2026-01-15T15:30:00Z",
      "duration_minutes": 30,
      "status": "success",
      "deliverables": [
        "results/sg-1/oauth-research.md",
        "results/sg-1/auth-flow.md"
      ]
    },
    {
      "subgoal_id": "sg-2",
      "agent_id": "full-stack-dev",
      "started_at": "2026-01-15T15:30:01Z",
      "completed_at": "2026-01-15T16:00:00Z",
      "duration_minutes": 30,
      "status": "success",
      "deliverables": [
        "src/models/user.py",
        "src/auth/oauth.py",
        "src/api/routes.py"
      ]
    }
  ],
  "errors": [],
  "last_checkpoint": "2026-01-15T16:00:00Z"
}
```

---

## 6. ARCHITECTURE & DESIGN

### 6.1 Package Structure

```
packages/
├── planning/                        # NEW PACKAGE
│   ├── src/aurora_planning/
│   │   ├── __init__.py
│   │   ├── commands/
│   │   │   ├── plan.py              # CLI commands
│   │   │   └── agent_run.py         # Agent execution helper
│   │   ├── core/
│   │   │   ├── plan_generator.py    # Plan generation pipeline
│   │   │   ├── prd_generator.py     # PRD expansion
│   │   │   ├── task_generator.py    # Code-aware task generation
│   │   │   └── executor.py          # Execution engine
│   │   ├── parsers/
│   │   │   ├── markdown.py          # Markdown parsing (plan/prd/tasks)
│   │   │   └── checkbox.py          # Checkbox state management
│   │   ├── models/
│   │   │   ├── plan.py              # Plan data model
│   │   │   ├── prd.py               # PRD data model
│   │   │   ├── task.py              # Task data model
│   │   │   └── execution_state.py   # Execution state model
│   │   ├── file_resolver.py         # File path resolution from memory
│   │   └── templates/
│   │       ├── plan.md.jinja2       # Plan template
│   │       ├── prd.md.jinja2        # PRD template
│   │       └── tasks.md.jinja2      # Tasks template
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   └── pyproject.toml
│
├── cli/                             # EXTENDED
│   ├── src/aurora_cli/
│   │   ├── commands/
│   │   │   ├── plan.py              # NEW: Plan commands
│   │   │   └── mem.py               # REUSE: Memory commands
│   │   ├── memory/
│   │   │   └── retrieval.py         # REUSE from PRD 0016
│   │   └── slash_commands/          # NEW
│   │       ├── aur_plan.py          # /aur:plan
│   │       ├── aur_implement.py     # /aur:implement
│   │       └── aur_archive.py       # /aur:archive
│   └── depends on → planning/, soar/, context-code/, core/
│
├── soar/                            # REUSED
│   ├── src/aurora_soar/
│   │   ├── orchestrator.py          # REUSE: SOAR 9-phase
│   │   ├── phases/
│   │   │   └── decompose.py         # REUSE: Goal decomposition
│   │   └── agent_registry.py        # REUSE from PRD 0016
│
├── context-code/                    # REUSED
│   ├── src/aurora_context_code/
│   │   └── semantic/
│   │       └── hybrid_retriever.py  # REUSE: Memory retrieval
│
└── core/                            # REUSED
    ├── src/aurora_core/
    │   ├── storage/store.py         # REUSE: Chunk storage
    │   └── chunks/                  # REUSE: Chunk models
```

### 6.2 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AURORA PLANNING SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 1: CORE PLANNING                                           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   User: aur plan create "goal"                                          │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 1: Context Retrieval                   │                       │
│   │  - Check --context flag                     │                       │
│   │  - Load from memory OR custom files         │                       │
│   │  (REUSE from PRD 0016)                      │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 2: SOAR Decomposition                  │                       │
│   │  - SOAROrchestrator.decompose()             │                       │
│   │  - Assess complexity (simple/complex)       │                       │
│   │  - Generate subgoals + dependencies         │                       │
│   │  (REUSE SOAR Phase 3)                       │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 3: Agent Recommendation                │                       │
│   │  - Load agent manifest                      │                       │
│   │  - Match subgoal → agent by capability      │                       │
│   │  - Detect gaps, suggest fallbacks           │                       │
│   │  (REUSE from PRD 0016)                      │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 4: Generate Files                      │                       │
│   │  - plan.md (SOAR output)                    │                       │
│   │  - prd.md (template placeholder)            │                       │
│   │  - tasks.md (template placeholder)          │                       │
│   │  - agents.json (machine-readable)           │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   ~/.aurora/plans/active/0001-oauth-auth/                               │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 2: PRD & TASK GENERATION                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   User: aur plan expand 0001 --to-prd                                   │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 1: Load Plan                           │                       │
│   │  - Read agents.json                         │                       │
│   │  - Load context files from memory           │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 2: Generate PRD per Subgoal            │                       │
│   │  - For each subgoal:                        │                       │
│   │    • Functional requirements                │                       │
│   │    • Acceptance criteria                    │                       │
│   │    • Testing strategy                       │                       │
│   │  - Follow OpenSpec format                   │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   prd.md written                                                         │
│                                                                          │
│   User: aur plan tasks 0001                                              │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 1: Load PRD                            │                       │
│   │  - Parse prd.md markdown                    │                       │
│   │  - Extract requirements per subgoal         │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 2: Resolve File Paths                  │                       │
│   │  - Extract entities from requirements       │                       │
│   │  - Query memory index for matches           │                       │
│   │  - Suggest line numbers (git blame)         │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 3: Generate Tasks                      │                       │
│   │  - Group by subgoal                         │                       │
│   │  - Add file paths + line numbers            │                       │
│   │  - Add checkboxes for progress tracking     │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   tasks.md written                                                       │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 3: EXECUTION & DELEGATION                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   User: aur plan execute 0001                                            │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 1: Load Plan & State                   │                       │
│   │  - Read agents.json                         │                       │
│   │  - Load state.json (if exists)              │                       │
│   │  - Determine current subgoal                │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 2: Validate Agents                     │                       │
│   │  - Check all agents exist in manifest       │                       │
│   │  - Detect gaps, build fallback list         │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 3: Resolve Agent Gaps                  │                       │
│   │  - Interactive: Prompt user for each gap    │                       │
│   │  - Non-interactive: Auto-select fallback    │                       │
│   │  - Save resolutions to state.json           │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────┐                       │
│   │ Step 4: Execute Subgoals Sequentially       │                       │
│   │  FOR EACH subgoal:                          │                       │
│   │    ├─ Check dependencies met                │                       │
│   │    ├─ Spawn agent subprocess                │                       │
│   │    ├─ Wait for completion                   │                       │
│   │    ├─ Update task checkboxes                │                       │
│   │    ├─ Save checkpoint to state.json         │                       │
│   │    └─ Handle errors (retry/skip/abort)      │                       │
│   └─────────────────────────────────────────────┘                       │
│       ↓                                                                  │
│   Execution complete → results/ + updated state.json                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Integration with PRD 0016

**Shared Components**:

1. **Agent Discovery** (from PRD 0016):
   - Agent manifest at `~/.aurora/agents/manifest.json`
   - Agent validation and gap detection
   - Fallback recommendation algorithm

2. **Memory Retrieval** (from PRD 0016):
   - Context retrieval from indexed memory
   - Custom file loading with `--context` flag
   - Memory index queries for file path resolution

3. **SOAR Orchestrator** (existing):
   - Phase 3 (Decompose) for goal decomposition
   - Complexity assessment logic
   - Subgoal dependency detection

**New Components** (Phase 1-3):

1. **Plan Generator** (Phase 1):
   - Four-file generation (plan/prd/tasks)
   - Plan lifecycle management (list/show/archive)
   - Directory structure management

2. **PRD Generator** (Phase 2):
   - PRD expansion from plan
   - OpenSpec-compliant formatting
   - Requirement + scenario generation

3. **Task Generator** (Phase 2):
   - Code-aware task generation
   - File path resolution from memory
   - Line number suggestions

4. **Execution Engine** (Phase 3):
   - Agent subprocess spawning
   - State persistence and checkpointing
   - Progress tracking via checkbox parsing

---

## 7. QUALITY GATES & ACCEPTANCE CRITERIA

### 7.1 Code Quality Gates

| Gate | Requirement | Tool | Blocker |
|------|-------------|------|---------|
| **Code Coverage** | ≥85% for aurora-planning package | pytest-cov | YES |
| **Type Checking** | 0 mypy errors (strict mode) | mypy | YES |
| **Linting** | 0 critical issues | ruff | YES |
| **Security** | 0 high/critical vulnerabilities | bandit | YES |

### 7.2 Performance Gates

| Metric | Phase 1 | Phase 2 | Phase 3 | Blocker |
|--------|---------|---------|---------|---------|
| **Plan Generation** | <10s | N/A | N/A | YES |
| **PRD Expansion** | N/A | <5s | N/A | YES |
| **Task Generation** | N/A | <3s | N/A | NO (warning) |
| **Memory Retrieval** | <2s | <2s | <2s | YES |
| **File Path Resolution** | N/A | <1s per requirement | N/A | NO (warning) |
| **Execution Start** | N/A | N/A | <5s to first subgoal | YES |

### 7.3 Functional Acceptance Tests

**Phase 1**:
- ✅ Plan created with 4 files (plan/prd/tasks/agents.json) in <10s
- ✅ Plan listed correctly (active vs archived)
- ✅ Plan shown with all metadata
- ✅ Plan archived to timestamped directory
- ✅ Memory context retrieved and used

**Phase 2**:
- ✅ PRD expanded with OpenSpec format
- ✅ Tasks generated with file paths from memory
- ✅ Agent recommendations per subgoal
- ✅ Slash commands functional in Claude Code

**Phase 3**:
- ✅ Plan executed with agent delegation
- ✅ Agent gaps prompted and resolved
- ✅ Progress tracked in state.json
- ✅ Checkboxes updated after each subgoal
- ✅ Execution resumable from checkpoint

---

### 7.4 Shell Tests (End-to-End CLI Validation)

Following the existing `tests/shell/test_*.sh` pattern, create comprehensive shell tests for each phase.

#### Phase 1 Shell Tests (8 tests)

**test_19_plan_create_interactive.sh**
- Create plan via `/aur:plan` with interactive prompts
- Verify plan.md + agents.json created at `~/.aurora/plans/active/<id>/`
- Check SOAR decomposition output format (goal, subgoals, agents)
- **Pass Criteria**: 4 files exist, plan.md contains subgoals

**test_20_plan_create_from_file.sh**
- Create plan with `--from-file tasks/0016-prd-agent-discovery-planning-cli.md`
- Verify goal extracted from PRD frontmatter or title
- Check context retrieval from memory (log shows "Retrieved X files")
- **Pass Criteria**: Plan created, context logged

**test_21_plan_checkpoint_continue.sh**
- Run `/aur:plan`, answer "Y" at checkpoint prompt
- Verify prd.md + tasks.md generated after confirmation
- Check file timestamps match (created within 5 seconds)
- **Pass Criteria**: All 4 files exist, tasks.md has checkboxes

**test_22_plan_checkpoint_abort.sh**
- Run `/aur:plan`, answer "n" at checkpoint prompt
- Verify only plan.md + agents.json exist (no prd.md/tasks.md)
- Check graceful exit (no errors)
- **Pass Criteria**: Only 2 files exist, exit code 0

**test_23_plan_list_active.sh**
- Create 3 plans, list with `aur plan list`
- Verify ID, name, status columns shown
- Check sorting by creation date (newest first)
- **Pass Criteria**: 3 rows shown, sorted correctly

**test_24_plan_show_details.sh**
- Show plan with `aur plan show 0001-oauth-auth`
- Verify subgoals, agents, file paths displayed
- Check gap detection warnings shown (if any)
- **Pass Criteria**: All subgoals listed, gaps highlighted

**test_25_plan_agent_recommendation.sh**
- Create plan with agent gaps (force missing agent scenario)
- Verify agents.json contains fallback agents
- Check gap detection in plan.md (⚠ warnings)
- **Pass Criteria**: agent_gaps array populated, fallback suggested

**test_26_plan_memory_retrieval.sh**
- Create plan, check memory queries logged (verbose mode)
- Verify retrieved files shown in context section
- Validate hybrid search used (BM25 + semantic log entries)
- **Pass Criteria**: Context section shows retrieved files

---

#### Phase 2 Shell Tests (4 tests)

**test_27_prd_expansion.sh**
- Expand plan.md to prd.md (automatic in `/aur:plan`)
- Verify API specs, security sections added
- Check PRD follows template structure (Executive Summary, Goals, FRs)
- **Pass Criteria**: prd.md has ≥5 sections, matches template

**test_28_task_generation.sh**
- Generate tasks.md from prd.md (automatic in `/aur:plan`)
- Verify file paths with line numbers (e.g., `src/auth.py:42-68`)
- Check dependency ordering (Subgoal 2 depends on Subgoal 1)
- **Pass Criteria**: tasks.md has file paths, dependencies noted

**test_29_task_code_aware.sh**
- Generate tasks, validate memory-retrieved paths exist
- Verify actual files at specified paths (no phantom references)
- Check line numbers are current (not stale references)
- **Pass Criteria**: All file paths resolve, files exist

**test_30_prd_template_validation.sh**
- Create PRD, validate against Pydantic schema
- Check required sections present (Goals, FRs, Testing)
- Verify frontmatter YAML valid (plan_id, generated_at)
- **Pass Criteria**: Schema validation passes, YAML parses

---

#### Phase 3 Shell Tests (3 tests)

**test_31_plan_archive.sh**
- Archive plan with `/aur:archive 0001-oauth-auth`
- Verify moved to `archive/YYYY-MM-DD-<id>/`
- Check all 4 files copied (plan/prd/tasks/agents.json)
- **Pass Criteria**: Directory moved, all files present

**test_32_plan_implement_delegate.sh**
- Run `/aur:implement 0001-oauth-auth` (with mock agents)
- Verify agent subprocess spawned (check process table)
- Check state.json tracks progress (current_subgoal field)
- **Pass Criteria**: state.json created, current_subgoal set

**test_33_plan_archive_validation.sh**
- Archive incomplete plan (tasks not all checked)
- Verify warning shown ("Tasks not complete")
- Check archive still succeeds (no blocking)
- **Pass Criteria**: Warning logged, archive completes

---

#### Test Execution

```bash
# Run all planning tests
bash tests/shell/test_19_plan_*.sh
bash tests/shell/test_20_plan_*.sh
# ... through test_33

# Run by phase
bash tests/shell/test_{19..26}_*.sh  # Phase 1
bash tests/shell/test_{27..30}_*.sh  # Phase 2
bash tests/shell/test_{31..33}_*.sh  # Phase 3

# CI integration (all tests)
make test-shell-planning
```

**Test Infrastructure Requirements**:
- Mock agent registry (simplified ~/.claude/agents/)
- Fixture plans (pre-generated for list/show tests)
- Memory index with sample codebase
- Cleanup after each test (delete ~/.aurora/plans/active/*)

---

## 8. TESTING STRATEGY

### 8.1 Unit Tests

**Phase 1**:
- `test_plan_generator.py`: Plan generation logic
- `test_file_structure.py`: Directory creation, file writing
- `test_plan_id_generation.py`: Unique ID generation
- `test_plan_archiver.py`: Archive logic with timestamps

**Phase 2**:
- `test_prd_generator.py`: PRD expansion logic
- `test_task_generator.py`: Code-aware task generation
- `test_file_resolver.py`: File path resolution from memory
- `test_markdown_parser.py`: Markdown parsing (PRD, tasks)

**Phase 3**:
- `test_executor.py`: Execution pipeline orchestration
- `test_agent_validator.py`: Agent gap detection
- `test_checkpoint_manager.py`: State persistence
- `test_checkbox_parser.py`: Checkbox state updates

### 8.2 Integration Tests

**Phase 1**:
- E2E plan creation: `aur plan create` → 4 files generated
- E2E plan listing: Multiple plans sorted correctly
- E2E plan archiving: Files moved to archive/

**Phase 2**:
- E2E PRD expansion: Plan → detailed PRD
- E2E task generation: PRD → code-aware tasks with file paths
- Memory integration: File paths resolved correctly

**Phase 3**:
- E2E execution: Full 4-subgoal plan with mocked agents
- E2E gap handling: Missing agent → prompt → fallback selection
- E2E checkpoint recovery: Kill execution → resume from checkpoint

### 8.3 Acceptance Tests

**Match User Stories Exactly**:

**User Story 3.1** (Phase 1: Plan Creation):
```python
def test_user_story_3_1_plan_creation():
    """Developer planning feature implementation."""
    # GIVEN: User wants to plan OAuth2 feature
    goal = "Implement OAuth2 authentication"

    # WHEN: User runs plan create
    result = runner.invoke(cli, ["plan", "create", goal])

    # THEN: Plan generated in <10s
    assert result.execution_time < 10.0

    # AND: Plan stored correctly
    plan_dir = Path("~/.aurora/plans/active/0001-oauth-auth")
    assert plan_dir.exists()
    assert (plan_dir / "plan.md").exists()
    assert (plan_dir / "prd.md").exists()
    assert (plan_dir / "tasks.md").exists()

    # AND: Plan includes subgoals
    plan = Plan.from_json(plan_dir / "agents.json")
    assert len(plan.subgoals) >= 3  # Research, Implement, Test

    # AND: Agent recommendations present
    assert all(sg.recommended_agent for sg in plan.subgoals)
```

*(Similar tests for all user stories)*

---

## 9. DEPENDENCIES

### 9.1 Existing Aurora Components

| Component | Package | Status | Usage |
|-----------|---------|--------|-------|
| **Agent Discovery** | aurora_cli (PRD 0016 Phase 0) | ⚠️ NOT YET BUILT | Agent manifest, validation, gaps |
| **Memory Retrieval** | aurora_cli (PRD 0016 Phase 2) | ⚠️ NOT YET BUILT | Context loading from memory |
| **SOAR Orchestrator** | aurora_soar | ✅ EXISTS | Goal decomposition |
| **Store** | aurora_core | ✅ EXISTS | Memory index queries |
| **LLM Client** | aurora_reasoning | ✅ EXISTS | PRD/task generation |

**⚠️ BLOCKING DEPENDENCIES**: PRD 0016 Phase 0 (Agent Discovery) and Phase 2 (Planning) are NOT YET BUILT. These must be completed first:
- **Phase 0** provides agent manifest infrastructure used in Phase 1 of this PRD
- **Phase 2** provides the initial planning logic that this PRD extends

### 9.2 External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| **click** | ≥8.0 | CLI framework (existing) |
| **pydantic** | ≥2.0 | Data models |
| **pyyaml** | ≥6.0 | YAML parsing (from PRD 0016) |
| **jinja2** | ≥3.1 | Template rendering |
| **python-frontmatter** | ≥1.0 | Markdown frontmatter parsing |

### 9.3 Breaking Changes

**None**. This feature:
- Adds new commands (`aur plan *`)
- Adds new slash commands (`/aur:plan`, `/aur:implement`, `/aur:archive`)
- Does NOT change existing command behavior
- Backward compatible with existing memory/agent systems

---

## 10. PHASE BREAKDOWN

### 10.0 PRD 0016: Agent Discovery & Basic Planning (PREREQUISITE, OUT OF SCOPE)

**⚠️ CRITICAL**: PRD 0016 is **OUT OF SCOPE** for this PRD (0017). It must be completed BEFORE Phase 1 of this PRD.

**⚠️ TASK GENERATION NOTE**: Do NOT generate implementation tasks for PRD 0016 from this PRD. Those tasks should be generated from `/tasks/0016-prd-agent-discovery-planning-cli.md` instead.

**Scope** (from PRD 0016):

**Phase 1: Agent Discovery**
- Agent manifest generation from 4 sources (claude, ampcode, droid, opencode)
- CLI commands: `aur agents list/search/show/refresh`
- Performance: <500ms for agent discovery

**Phase 2: Direct Planning**
- Basic `aur plan` command for goal decomposition
- Memory retrieval integration for context loading
- Simple plan validation against agent availability

**Status**: **NOT YET BUILT** - Must complete both PRD 0016 phases before starting Phase 1 of PRD 0017

**Reference**: See `/tasks/0016-prd-agent-discovery-planning-cli.md` for complete specifications and implementation tasks.

---

### 10.1 Phase 1: Core Planning (Weeks 1-2)

**Scope**:
- Directory structure creation (`~/.aurora/plans/`)
- Plan generation from natural language
- Four-file workflow: plan.md, prd.md (template), tasks.md (template), agents.json
- Plan lifecycle: init, create, list, show, archive
- Memory integration (REUSE from PRD 0016)

**Deliverables**:
- `aur plan init` functional
- `aur plan create` generates plans in <10s
- `aur plan list` shows active/archived plans
- `aur plan show` displays plan details
- `aur plan archive` moves to timestamped archive
- **4 files generated per plan**: plan.md, prd.md, tasks.md, agents.json
- Agent recommendations included

**Definition of Done**:
- ✅ All Phase 1 commands implemented
- ✅ Unit tests ≥85% coverage
- ✅ Integration tests pass (plan creation → archive)
- ✅ Performance: <10s plan generation
- ✅ Documentation: CLI help text + examples

---

### 10.2 Phase 2: PRD & Task Generation (Weeks 3-4)

**Scope**:
- PRD expansion from plan (OpenSpec format)
- Code-aware task generation with file paths
- File path resolution using memory index
- Agent recommendation per subgoal
- Slash command integration (`/aur:plan`, `/aur:archive`)

**Deliverables**:
- `aur plan expand --to-prd` functional
- `aur plan tasks` generates code-aware tasks
- PRD follows OpenSpec conventions
- Tasks include file paths + line numbers from memory
- Slash commands working in Claude Code

**Definition of Done**:
- ✅ PRD expansion working in <5s
- ✅ Tasks generated with ≥90% file path accuracy
- ✅ OpenSpec validation passes
- ✅ Slash commands registered and functional
- ✅ Integration tests pass (plan → PRD → tasks)
- ✅ Documentation: PRD format guide, task examples

---

### 10.3 Phase 3: Execution & Agent Delegation (Weeks 5-6)

**Scope**:
- Execution engine with agent subprocess spawning
- Sequential subgoal execution with dependency checking
- Agent gap handling (interactive prompts)
- Progress tracking via checkbox parsing + state.json
- Pause/resume capability
- `/aur:implement` slash command

**Deliverables**:
- `aur plan execute` functional
- Agent subprocesses spawned per subgoal
- State persistence and checkpoint recovery
- Checkbox updates in tasks.md
- Gap prompts working (interactive + non-interactive)
- `/aur:implement` slash command

**Definition of Done**:
- ✅ Execution working end-to-end
- ✅ Agent gaps handled with prompts
- ✅ Progress tracked in state.json
- ✅ Checkboxes updated after each subgoal
- ✅ Resume from checkpoint functional
- ✅ Acceptance tests pass for all user stories
- ✅ Documentation: Execution guide, troubleshooting

---

## 11. OPENSPEC ADAPTATION & REFACTORING

### 11.1 Why Reimplement in Python (vs Keep TypeScript)

**Decision: Full Python Rewrite**

| Factor | TypeScript (OpenSpec) | Python (Aurora) | Winner |
|--------|----------------------|-----------------|--------|
| **Integration** | Subprocess overhead (npm + pip) | Direct SOAR calls | Python |
| **Runtime** | npm + pip required | pip only | Python |
| **Customization** | Fork + maintain upstream | Full control | Python |
| **Dev Time** | 20h (integration + glue) | 10h (rewrite) | Python |
| **Memory Integration** | None (requires bridge) | Native (shared index) | Python |
| **Agent System** | None (would need glue) | Native (PRD 0016) | Python |

**Reasoning**:
- OpenSpec is an **inspiration**, not a dependency
- Python rewrite = cleaner integration with SOAR, memory, agents
- No TypeScript/Python bridge overhead
- Full control over plan format (SOAR output, agents.json)

---

### 11.2 Python Stack Replacements

| OpenSpec (TS) | Aurora (Python) | Purpose |
|---------------|-----------------|---------|
| Commander.js | Click | CLI framework |
| Inquirer.js | Rich.prompt | Interactive prompts |
| Chalk | Rich.console | Terminal styling |
| Zod | Pydantic | Schema validation |
| gray-matter | python-frontmatter | YAML frontmatter parsing |
| fs/path | pathlib | File operations |
| TypeScript | Python | Language |

---

### 11.3 Side-by-Side Translation Examples

#### Example 1: Markdown Section Parsing

**TypeScript (OpenSpec)**:
```typescript
parseSections(): Section[] {
    const sections = [];
    for (const line of this.lines) {
        const headerMatch = line.match(/^(#{1,6})\s+(.+)$/);
        if (headerMatch) {
            sections.push({
                level: headerMatch[1].length,
                title: headerMatch[2]
            });
        }
    }
    return sections;
}
```

**Python (Aurora)**:
```python
def parse_sections(lines: list[str]) -> list[Section]:
    sections = []
    for line in lines:
        if match := re.match(r'^(#{1,6})\s+(.+)$', line):
            sections.append(Section(
                level=len(match.group(1)),
                title=match.group(2)
            ))
    return sections
```

#### Example 2: Archive with Timestamp

**TypeScript (OpenSpec)**:
```typescript
async archive(changeId: string): Promise<void> {
    const timestamp = new Date().toISOString().split('T')[0];
    const archivePath = `archive/${timestamp}-${changeId}`;
    await fs.rename(`active/${changeId}`, archivePath);
}
```

**Python (Aurora)**:
```python
def archive_plan(plan_id: str) -> Path:
    timestamp = datetime.now().strftime('%Y-%m-%d')
    archive_path = PLANS_DIR / 'archive' / f'{timestamp}-{plan_id}'
    active_path = PLANS_DIR / 'active' / plan_id
    active_path.rename(archive_path)
    return archive_path
```

#### Example 3: Schema Validation

**TypeScript (Zod)**:
```typescript
const ChangeSchema = z.object({
    name: z.string().min(1),
    why: z.string().min(100).max(1000),
    deltas: z.array(DeltaSchema).min(1)
});
```

**Python (Pydantic)**:
```python
class Plan(BaseModel):
    name: str = Field(min_length=1)
    why: str = Field(min_length=100, max_length=1000)
    subgoals: list[Subgoal] = Field(min_length=1)
```

---

### 11.4 File-by-File Porting Strategy

| OpenSpec File | Aurora Module | Complexity | Est. Hours | Notes |
|---------------|---------------|------------|-----------|-------|
| archive.js | planning/archive.py | Low | 1h | Simple file move |
| markdown-parser.js | planning/parser.py | Medium | 2h | Regex patterns |
| change.schema.js | planning/models.py | Low | 1h | Pydantic models |
| interactive.js | planning/prompts.py | Medium | 2h | Rich prompts |
| execute.js | planning/executor.py | High | 4h | SOAR integration |

**Total Estimate: 10 hours** (vs 20h for TypeScript integration + maintenance burden)

---

### 11.5 File Path Resolution Strategy

**Challenge**: How to suggest exact file paths and line numbers for tasks?

**Solution**: Multi-strategy file resolution from memory index

**Strategy 1: Entity Extraction from Requirements**
```python
def extract_entities(requirement: str) -> list[str]:
    """
    Extract entities from requirement text.

    Examples:
    - "Extend User model" → ["User", "model"]
    - "Implement Auth0 SDK wrapper" → ["Auth0", "SDK", "wrapper"]
    - "Add /auth/login endpoint" → ["/auth/login", "endpoint"]
    """
    # Use NLP or regex patterns
    entities = []

    # Pattern 1: Class/model names (capitalized words)
    entities += re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', requirement)

    # Pattern 2: File paths
    entities += re.findall(r'[\w/]+\.py', requirement)

    # Pattern 3: API endpoints
    entities += re.findall(r'/[\w/]+', requirement)

    return deduplicate(entities)
```

**Strategy 2: Memory Index Query**
```python
def query_memory_for_files(entities: list[str], memory: MemoryIndex) -> list[FileMatch]:
    """
    Query memory index for matching files.

    Uses tri-hybrid search from PRD 0015:
    - BM25 for keyword matching
    - Semantic for conceptual similarity
    - Activation for recency/frequency
    """
    matches = []

    for entity in entities:
        results = memory.search(
            query=entity,
            top_k=3,
            filter_type="code"  # Only code chunks
        )
        matches.extend(results)

    # Deduplicate and rank by confidence
    return deduplicate_and_rank(matches)
```

**Strategy 3: Line Number Suggestion (Git Blame)**
```python
def suggest_line_numbers(file_path: Path, entity: str) -> tuple[int, int]:
    """
    Suggest line number range for modification.

    Uses git blame to find entity definition:
    1. Search file for entity (class/function name)
    2. Get line number of definition
    3. Expand to logical block (indentation-based)
    """
    content = file_path.read_text()

    # Find entity definition
    pattern = rf'(class|def)\s+{re.escape(entity)}'
    match = re.search(pattern, content)

    if match:
        start_line = content[:match.start()].count('\n') + 1
        end_line = find_block_end(content, start_line)
        return (start_line, end_line)
    else:
        # Entity not found - suggest file-level modification
        return (1, len(content.split('\n')))
```

**Fallback Strategy**: If no matches found
```python
def create_new_file_task(requirement: Requirement) -> Task:
    """
    If no existing files match, suggest creating new file.

    Example:
    - Requirement: "Create Auth0 SDK wrapper"
    - Suggested file: src/auth/oauth.py (NEW)
    """
    suggested_path = infer_file_path(requirement)
    return Task(
        description=requirement.description,
        file_path=suggested_path,
        file_status="NEW",
        line_numbers=None
    )
```

---

### 11.6 Agent Subprocess Spawning

**Challenge**: How to spawn specialized agents in separate processes?

**Solution**: `aur agent run` helper command

**Command Definition**:
```bash
aur agent run <agent-id> \
  --goal "<subgoal-description>" \
  --context <file1> <file2> \
  --output <results-dir> \
  --timeout 3600
```

**Implementation**:
```python
@click.command()
@click.argument("agent_id")
@click.option("--goal", required=True)
@click.option("--context", multiple=True)
@click.option("--output", type=Path)
@click.option("--timeout", default=3600)
def agent_run(agent_id: str, goal: str, context: tuple[str], output: Path, timeout: int):
    """
    Run specialized agent for a specific subgoal.

    Loads agent from manifest, configures with subgoal context,
    executes agent's workflow, saves results to output dir.
    """
    # Load agent
    agent = load_agent_from_manifest(agent_id)

    # Configure agent with subgoal
    agent.set_goal(goal)
    agent.set_context(load_context_files(context))

    # Execute agent workflow
    result = agent.execute(timeout=timeout)

    # Save results
    output.mkdir(parents=True, exist_ok=True)
    save_agent_results(result, output)

    # Report status
    if result.status == "success":
        click.echo(f"✓ Agent {agent_id} completed successfully")
        sys.exit(0)
    else:
        click.echo(f"✗ Agent {agent_id} failed: {result.error}")
        sys.exit(1)
```

**Agent Interface** (abstract):
```python
class AgentInterface(ABC):
    """Abstract interface for specialized agents."""

    @abstractmethod
    def set_goal(self, goal: str):
        """Set agent's goal for execution."""
        pass

    @abstractmethod
    def set_context(self, context: ContextData):
        """Provide context files for execution."""
        pass

    @abstractmethod
    def execute(self, timeout: int) -> AgentResult:
        """Execute agent's workflow, return result."""
        pass
```

**Note**: Phase 3 focuses on subprocess spawning. Full agent interface implementation may be deferred to future work if agents need custom workflows.

---

### 11.7 Checkpoint and Resume Strategy

**Challenge**: Long-running executions need pause/resume capability

**Solution**: Checkpoint state after each subgoal completion

**State Schema** (state.json):
```json
{
  "plan_id": "0001-oauth-auth",
  "status": "in_progress",
  "current_subgoal": "sg-3",
  "completed_subgoals": ["sg-1", "sg-2"],
  "checkpoints": [
    {
      "subgoal_id": "sg-1",
      "completed_at": "2026-01-15T15:30:00Z",
      "duration_minutes": 30
    }
  ]
}
```

**Checkpoint Logic**:
```python
def save_checkpoint(state: ExecutionState):
    """
    Save execution state after each subgoal.

    Atomic write: write to temp file, then rename.
    """
    state_file = Path(f"~/.aurora/plans/active/{state.plan_id}/state.json")
    temp_file = state_file.with_suffix(".json.tmp")

    # Write to temp
    temp_file.write_text(state.to_json())

    # Atomic rename
    temp_file.rename(state_file)
```

**Resume Logic**:
```python
def resume_execution(plan_id: str):
    """
    Resume execution from last checkpoint.

    1. Load state.json
    2. Find current_subgoal index
    3. Continue from that index
    """
    state = ExecutionState.from_json(
        Path(f"~/.aurora/plans/active/{plan_id}/state.json")
    )

    plan = Plan.from_json(
        Path(f"~/.aurora/plans/active/{plan_id}/agents.json")
    )

    # Find next subgoal to execute
    next_subgoal_idx = find_next_subgoal(state, plan)

    # Execute remaining subgoals
    execute_subgoals(plan.subgoals[next_subgoal_idx:], state)
```

---

## 12. DELIVERY VERIFICATION CHECKLIST

**Phase 1 is complete when ALL items checked**:

### 12.1 Phase 1: Implementation Complete

- [ ] `aur plan init` scaffolds planning directory
- [ ] `aur plan create` generates plan with 4 files in <10s
- [ ] `aur plan list` shows active/archived plans
- [ ] `aur plan show` displays full plan details
- [ ] `aur plan archive` moves to timestamped archive
- [ ] Memory integration operational (context retrieval)
- [ ] Agent recommendations per subgoal
- [ ] Plan ID generation (auto-increment, slug)

### 12.2 Phase 1: Testing Complete

- [ ] Unit test coverage ≥85% for planning package
- [ ] Integration tests pass (create → list → show → archive)
- [ ] Performance benchmarks meet <10s target
- [ ] Edge cases tested (no memory, malformed goals)

### 12.3 Phase 1: Documentation Complete

- [ ] CLI help text for all commands
- [ ] `docs/cli/CLI_USAGE_GUIDE.md` updated with planning section
- [ ] Example plan.md shown in docs
- [ ] Troubleshooting section added

---

**Phase 2 is complete when ALL items checked**:

### 12.4 Phase 2: Implementation Complete

- [ ] `aur plan expand --to-prd` generates detailed PRD
- [ ] `aur plan tasks` generates code-aware tasks
- [ ] PRD follows OpenSpec format (Requirements + Scenarios)
- [ ] Tasks include file paths from memory index
- [ ] Tasks include line number suggestions
- [ ] Slash commands working: `/aur:plan`, `/aur:archive`
- [ ] Agent recommendations per subgoal in PRD

### 12.5 Phase 2: Testing Complete

- [ ] PRD generation tests pass (template validation)
- [ ] Task generation tests pass (file path accuracy ≥90%)
- [ ] Memory integration tests pass (file resolution)
- [ ] Slash command tests pass (Claude Code integration)

### 12.6 Phase 2: Documentation Complete

- [ ] PRD format guide with examples
- [ ] Task format guide with file path examples
- [ ] Slash command usage documented
- [ ] OpenSpec alignment documented

---

**Phase 3 is complete when ALL items checked**:

### 12.7 Phase 3: Implementation Complete

- [ ] `aur plan execute` delegates to agents
- [ ] Agent subprocess spawning operational
- [ ] Sequential subgoal execution with dependencies
- [ ] Agent gap detection and user prompts
- [ ] State persistence (state.json checkpoints)
- [ ] Checkbox updates in tasks.md
- [ ] Resume from checkpoint functional
- [ ] `/aur:implement` slash command working
- [ ] Dry-run mode operational

### 12.8 Phase 3: Testing Complete

- [ ] Execution tests with mocked agents pass
- [ ] Gap handling tests pass (interactive + non-interactive)
- [ ] Checkpoint recovery tests pass
- [ ] Acceptance tests match all user stories

### 12.9 Phase 3: Documentation Complete

- [ ] Execution guide with examples
- [ ] Agent delegation explained
- [ ] Troubleshooting for common execution errors
- [ ] State.json schema documented

---

### 12.10 All Phases: Quality Assurance

- [ ] Code review completed (2+ reviewers)
- [ ] MyPy strict mode passes (0 errors)
- [ ] Ruff linting passes (0 critical)
- [ ] Security audit passed (bandit)
- [ ] Performance profiling completed
- [ ] Backward compatibility verified (existing commands unaffected)

---

## APPENDIX A: COMPARISON WITH OPENSPEC

| Aspect | OpenSpec (MIT) | Aurora Planning System |
|--------|---------------|------------------------|
| **Language** | TypeScript | Python |
| **File Structure** | `changes/`, `archive/`, `specs/` | `active/`, `archive/` |
| **Files per Change** | proposal.md, tasks.md, design.md (optional) | plan.md, prd.md, tasks.md, agents.json |
| **Archive Format** | `YYYY-MM-DD-<id>` | `YYYY-MM-DD-<id>` (SAME) |
| **Validation** | `openspec validate` | N/A (Aurora focuses on generation) |
| **Execution** | Manual (no execution engine) | Automated (agent delegation) |
| **Agent System** | None | Integrated (PRD 0016 manifest) |
| **Memory Integration** | None | Full (tri-hybrid search from PRD 0015) |
| **Code Awareness** | None | Tasks include file paths + line numbers |
| **Goal Decomposition** | Manual | Automated (SOAR orchestrator) |

**Key Insight**: Aurora Planning System adopts OpenSpec's proven file structure patterns but extends with:
1. SOAR-powered goal decomposition
2. Memory-integrated code awareness
3. Agent delegation for execution
4. Progress tracking and checkpointing

---

## APPENDIX B: AGENT SUBPROCESS EXECUTION FLOW

**Example: Execute Subgoal 2 (Backend Implementation)**

```
Subgoal: Backend Implementation
Agent: @full-stack-dev
Goal: "Implement Auth0 SDK integration and API endpoints"
Context: src/models/user.py, src/api/routes.py
Output: ~/.aurora/plans/active/0001-oauth-auth/results/sg-2/

Command:
  aur agent run full-stack-dev \
    --goal "Implement Auth0 SDK integration and API endpoints" \
    --context src/models/user.py src/api/routes.py \
    --output ~/.aurora/plans/active/0001-oauth-auth/results/sg-2/ \
    --timeout 3600

Agent Workflow:
  1. Load context files
  2. Generate implementation plan
  3. Modify src/models/user.py (add OAuth fields)
  4. Create src/auth/oauth.py (Auth0 wrapper)
  5. Modify src/api/routes.py (add endpoints)
  6. Run tests
  7. Save results to output/

Results Directory:
  results/sg-2/
  ├── implementation_log.md   # What was done
  ├── modified_files.json     # List of changes
  ├── test_results.json       # Test outcomes
  └── deliverables/
      ├── user.py.diff        # Diff of changes
      ├── oauth.py            # New file
      └── routes.py.diff      # Diff of changes

Execution Outcome:
  ✓ Subgoal 2 completed in 30 minutes
  → State updated: completed_subgoals += ["sg-2"]
  → Checkboxes updated in tasks.md
  → Checkpoint saved to state.json
```

---

## APPENDIX C: PHASE DEPENDENCIES DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│                    AURORA PLANNING SYSTEM                        │
│                     PHASE DEPENDENCIES                           │
└─────────────────────────────────────────────────────────────────┘

FOUNDATION (Already Built):
┌─────────────────────────────────────────────────────────────────┐
│ PRD 0016: Agent Discovery & Planning CLI                         │
│  - Agent manifest generation                                     │
│  - Memory retrieval (context loading)                            │
│  - Agent gap detection                                           │
└─────────────────────────────────────────────────────────────────┘
           ↓

PHASE 1: Core Planning (Weeks 1-2)
┌──────────────────────────────────────────────────────────────────────────┐
│ Commands: init, list, show (CLI) + /aur:plan, /aur:archive (slash)     │
│ Deliverables: plan.md, prd.md (template), tasks.md, agents.json        │
│ Integration: Memory retrieval, SOAR decomposition                       │
└──────────────────────────────────────────────────────────────────────────┘
           ↓

PHASE 2: PRD & Task Generation (Weeks 3-4)
┌─────────────────────────────────────────────────────────────────┐
│ Commands: expand --to-prd, tasks                                │
│ Deliverables: Detailed prd.md, Code-aware tasks.md              │
│ Integration: Memory index (file paths), OpenSpec format         │
│ New: Slash commands (/aur:plan, /aur:archive)                   │
└─────────────────────────────────────────────────────────────────┘
           ↓

PHASE 3: Execution & Delegation (Weeks 5-6)
┌─────────────────────────────────────────────────────────────────┐
│ Commands: execute                                                │
│ Integration: Agent subprocess spawning, state checkpoints        │
│ New: /aur:implement, progress tracking, pause/resume            │
└─────────────────────────────────────────────────────────────────┘

DEPENDENCIES:
- Phase 1 depends on: PRD 0016 (memory, agents), SOAR (decomposition)
- Phase 2 depends on: Phase 1 (plan.md exists), Memory (file paths)
- Phase 3 depends on: Phase 2 (prd.md, tasks.md exist), PRD 0016 (agents)
```

---

## DOCUMENT HISTORY

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-01-01 | Initial PRD for Aurora Planning System (3 phases) | Product Team |

---

**END OF PRD 0017: Aurora Planning System (3-Phase Implementation)**
