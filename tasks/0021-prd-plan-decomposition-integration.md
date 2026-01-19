# PRD 0021: Plan Decomposition & Integration

**Version**: 1.0
**Date**: 2026-01-05
**Status**: Draft
**Sprint**: Phase 2 of 3
**Parent Spec**: `/tasks/0017-planning-specs-v2.md`
**Dependencies**: PRD 0016 (Agent Discovery), PRD 0017 Phase 1 (Planning Foundation)

---

## 1. Introduction/Overview

### Problem Statement

Aurora's planning system currently uses rule-based heuristic decomposition (`_decompose_goal_soar()` in `core.py`) that pattern-matches keywords like "auth", "api", "refactor" to generate static subgoal templates. This approach:

1. **Lacks Intelligence**: Cannot adapt to project-specific context or code structure
2. **No Memory Integration**: Generated tasks reference generic file paths instead of actual codebase locations
3. **Limited Agent Matching**: Agent recommendations are hardcoded per pattern, not based on capability scoring
4. **Missing Archive Sophistication**: Current `archive_plan()` lacks spec delta processing, validation, and interactive selection
5. **No User Checkpoint**: Plans generate immediately without opportunity to review decomposition before file generation

### Solution Overview

PRD 0021 integrates Aurora's existing intelligence systems into the planning workflow:

1. **SOAR Integration**: Replace heuristic decomposition with `decompose_query()` from `aurora_soar.phases.decompose` for LLM-powered subgoal generation
2. **Memory Integration**: Use `MemoryRetriever` to resolve actual file paths with confidence scores for code-aware task generation
3. **Agent Discovery Integration**: Leverage `AgentManifest` and `ManifestManager` for capability-based agent recommendations with gap detection
4. **Enhanced Archive Command**: Port the full-featured `ArchiveCommand` from OpenSpec with spec delta processing
5. **User Checkpoint**: Add a confirmation step after decomposition, before plan file generation

### High-Level Goal

Transform Aurora planning from static template generation into an intelligent, context-aware system that:
- Decomposes goals using LLM reasoning with codebase context
- Resolves actual file paths from indexed memory
- Recommends agents based on capability matching
- Validates and confirms with users before committing to plan files
- Archives plans with proper spec evolution tracking

### Business Value

- **Time Savings**: Intelligent decomposition reduces manual plan refinement from hours to minutes
- **Accuracy**: Memory-aware file paths eliminate guesswork about which files to modify
- **Confidence**: User checkpoint prevents wasted effort on incorrect decompositions
- **Traceability**: Spec delta processing maintains capability documentation through plan lifecycle

---

## 2. Goals

### Goal 1: SOAR-Powered Decomposition
**Integrate** the SOAR orchestrator's decompose phase for intelligent goal breakdown.

**Success Criteria**:
- `/aur:plan` uses `decompose_query()` instead of pattern-matching heuristics
- Subgoals include dependencies derived from LLM analysis
- Complexity assessment comes from SOAR (SIMPLE/MEDIUM/COMPLEX/CRITICAL)
- Graceful fallback to heuristics if LLM unavailable

### Goal 2: Memory-Aware File Resolution
**Integrate** `MemoryRetriever` for resolving file paths in generated tasks.

**Success Criteria**:
- Tasks include actual file paths from indexed memory
- Each file reference includes confidence score (0.0-1.0)
- Line number ranges suggested where possible
- Warning when memory not indexed (graceful degradation)

### Goal 3: Agent Capability Matching
**Integrate** `AgentManifest` for capability-based agent recommendations.

**Success Criteria**:
- Agents recommended based on keyword matching against capabilities
- Agent gaps detected and recorded in `agents.json`
- Fallback suggestions provided for missing agents
- Agent existence verified against manifest

### Goal 4: User Checkpoint Before Generation
**Add** confirmation step between decomposition and file generation.

**Success Criteria**:
- Summary displayed after decomposition (subgoals, agents, files, gaps)
- User can confirm, abort, or request adjustment
- Non-interactive mode available for scripted usage
- Clear display of what will be generated

### Goal 5: Enhanced Archive Command
**Port** the full `ArchiveCommand` from OpenSpec with spec delta processing.

**Success Criteria**:
- Spec updates with ADDED/MODIFIED/REMOVED/RENAMED delta processing
- Task completion validation with incomplete warnings
- Interactive plan selection when no plan-id provided
- Atomic move with timestamp prefix (YYYY-MM-DD-<plan-id>)
- `--yes`, `--skip-specs`, `--no-validate` flags supported

---

## 3. User Stories

### Decomposition Stories

**US-3.1: Intelligent Goal Decomposition**
```
AS A developer
I WANT to run `/aur:plan "Implement OAuth2 authentication"`
SO THAT Aurora uses LLM reasoning to decompose my goal into context-aware subgoals
```

**Acceptance Criteria**:
- SOAR `decompose_query()` called with goal and available context
- Subgoals reflect actual project structure (not generic templates)
- Dependencies between subgoals determined by analysis
- Execution pauses after decomposition for user review

**US-3.2: Memory-Aware Task Generation**
```
AS A developer
I WANT generated tasks to include actual file paths
SO THAT I know exactly which files to modify for each task
```

**Acceptance Criteria**:
- `MemoryRetriever.retrieve()` called for each subgoal
- File paths shown with confidence scores (e.g., `src/auth.py (0.92)`)
- Line ranges included when structure analysis possible
- Warning displayed if memory not indexed

**US-3.3: Agent Recommendations with Gaps**
```
AS A developer
I WANT agents recommended based on capabilities
SO THAT each subgoal is assigned to the most suitable agent
```

**Acceptance Criteria**:
- `AgentManifest` searched for capability matches
- Agents with score >= 0.5 assigned
- Agents with score < 0.5 marked as gaps with fallback
- Gaps recorded in `agents.json` for future resolution

**US-3.4: Confirm Before Commit**
```
AS A developer
I WANT to review the decomposition before plan files are generated
SO THAT I can abort or adjust if the decomposition is incorrect
```

**Acceptance Criteria**:
- Summary displayed: subgoals (count, titles), agents (assigned, gaps), files (resolved, confidence)
- Prompt: "Proceed with plan generation? (Y/n/adjust)"
- "n" aborts with no files created
- "adjust" allows goal refinement (stretch goal)
- `--yes` flag skips confirmation

### Archive Stories

**US-3.5: Archive with Spec Updates**
```
AS A developer
I WANT to run `/aur:archive 0001`
SO THAT my completed plan is archived and capability specs are updated
```

**Acceptance Criteria**:
- Validates plan structure before archiving
- Warns if tasks incomplete (X/Y tasks done)
- Processes spec deltas (ADDED/MODIFIED/REMOVED/RENAMED)
- Moves to `archive/YYYY-MM-DD-<plan-id>/`
- Updates `agents.json` with `archived_at` timestamp

**US-3.6: Interactive Plan Selection**
```
AS A developer
I WANT to run `/aur:archive` without arguments
SO THAT I can select which plan to archive from a list
```

**Acceptance Criteria**:
- Lists active plans with task progress
- Numbered selection prompt
- Shows plan ID and completion status
- Handles empty list gracefully

**US-3.7: Skip Validations When Needed**
```
AS A developer
I WANT to use flags like `--skip-specs` and `--no-validate`
SO THAT I can archive plans quickly when I know the state is valid
```

**Acceptance Criteria**:
- `--skip-specs` skips spec delta processing
- `--no-validate` skips structure validation
- `--yes` skips all confirmation prompts
- Warning displayed when skipping validation

---

## 4. Functional Requirements

### FR-1: Archive Command Port

#### FR-1.1: Task Completion Validation

**Description**: Validate task completion status before archiving.

**The system must**:
1. Parse `tasks.md` for checkbox patterns (`- [x]` and `- [ ]`)
2. Calculate completion percentage (completed/total tasks)
3. Display status: "X/Y tasks (Z%)"
4. Warn user if incomplete tasks exist (< 100%)
5. Prompt for confirmation when tasks incomplete (unless `--yes`)
6. Allow archiving incomplete plans with explicit confirmation

**Acceptance Criteria**:
- Completion calculated correctly for all checkbox formats
- Warning message includes count of incomplete tasks
- `--yes` flag suppresses confirmation prompt
- Incomplete plan still archivable after confirmation

#### FR-1.2: Spec Delta Processing

**Description**: Process capability specification deltas during archive.

**The system must**:
1. Scan `<plan-dir>/specs/` for delta-formatted spec files
2. Detect delta sections: `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements`, `## RENAMED Requirements`
3. Parse delta content using `parse_modification_spec()`
4. Validate deltas for duplicates and conflicts
5. Build updated spec by applying deltas to existing spec (or create new)
6. Write updated specs to `.aurora/capabilities/<capability>/spec.md`
7. Display operation counts: `+ N added, ~ N modified, - N removed, -> N renamed`

**Acceptance Criteria**:
- All four delta types processed correctly
- Duplicate detection within sections
- Cross-section conflict detection (e.g., same requirement in ADDED and REMOVED)
- Atomic operation (all or nothing)
- `--skip-specs` bypasses this step

#### FR-1.3: Atomic Move Operation

**Description**: Move plan directory atomically with timestamp prefix.

**The system must**:
1. Generate archive directory name: `YYYY-MM-DD-<plan-id>`
2. Create archive directory if not exists: `.aurora/plans/archive/`
3. Perform atomic move (rename operation)
4. Rollback on failure (restore original location)
5. Update `agents.json` with `archived_at` timestamp before move
6. Update manifest after successful move

**Acceptance Criteria**:
- Archive directory name follows format exactly
- Move is atomic (no partial state)
- Original location empty after success
- Rollback restores original state on failure

#### FR-1.4: Interactive Plan Selection

**Description**: Allow interactive selection when no plan-id provided.

**The system must**:
1. List all directories in `.aurora/plans/active/` (excluding `archive/`)
2. Calculate task progress for each plan
3. Display formatted list: `<plan-id>  <progress>`
4. Accept numeric input for selection
5. Handle empty list gracefully
6. Support keyboard interrupt (Ctrl+C) for abort

**Acceptance Criteria**:
- Plans sorted alphabetically
- Progress shown as "X/Y (Z%)" or "No tasks"
- Invalid input prompts for retry
- Empty directory shows message and exits

#### FR-1.5: Archive Command Flags

**Description**: Support configuration flags for archive behavior.

**The system must**:
1. `--yes` / `-y`: Skip all confirmation prompts
2. `--skip-specs`: Skip spec delta processing
3. `--no-validate`: Skip validation checks (with warning)
4. Flags can be combined
5. Help text documents each flag

**Acceptance Criteria**:
- Each flag works independently
- Combined flags work correctly
- Warning shown when validation skipped
- Help text accurate and complete

---

### FR-2: SOAR Integration

#### FR-2.1: Decompose Query Integration

**Description**: Use SOAR's decompose phase for goal breakdown.

**The system must**:
1. Import `decompose_query` from `aurora_soar.phases.decompose`
2. Build context from memory retrieval or context files
3. Call `decompose_query(query, context, complexity, llm_client, available_agents)`
4. Convert `DecompositionResult` to `Subgoal` list
5. Respect caching behavior (same goal/complexity returns cached result)
6. Handle LLM failures gracefully (fallback to heuristics)

**Acceptance Criteria**:
- SOAR decomposition used when LLM available
- Heuristic fallback when LLM unavailable
- Cache hit returns immediately (<100ms)
- LLM timeout handled gracefully (30s default)

#### FR-2.2: Context Summary Building

**Description**: Build context summary for SOAR decomposition.

**The system must**:
1. Use `_build_context_summary()` from decompose module
2. Include code chunk count and coverage description
3. Include reasoning chunk count if available
4. Return "No indexed context available" when no chunks
5. Context summary limited to reasonable size for LLM

**Acceptance Criteria**:
- Summary accurately reflects available context
- Empty context returns special message
- Summary does not exceed 500 chars

#### FR-2.3: Available Agents List

**Description**: Provide available agents list to SOAR.

**The system must**:
1. Load `AgentManifest` via `ManifestManager.get_or_refresh()`
2. Extract agent IDs from manifest
3. Pass to `decompose_query()` as `available_agents` parameter
4. Handle manifest load failures gracefully (None)

**Acceptance Criteria**:
- Agent list reflects current manifest state
- Missing manifest does not block decomposition
- Agent IDs in correct format (`@agent-id`)

#### FR-2.4: Complexity Assessment

**Description**: Use SOAR complexity from decomposition result.

**The system must**:
1. Extract complexity from `DecompositionResult`
2. Map SOAR complexity (SIMPLE/MEDIUM/COMPLEX/CRITICAL) to `Complexity` enum
3. Override heuristic assessment when SOAR available
4. Fall back to heuristic when SOAR unavailable

**Acceptance Criteria**:
- SOAR complexity used when available
- Mapping handles all SOAR levels
- Heuristic fallback works correctly

---

### FR-3: Memory Integration

#### FR-3.1: File Path Resolution

**Description**: Resolve file paths from memory index for tasks.

**The system must**:
1. Create `MemoryRetriever` instance with store and config
2. For each subgoal, call `retriever.retrieve(subgoal.description, limit=5)`
3. Extract file paths from returned `CodeChunk` objects
4. Include line ranges from `chunk.line_start` and `chunk.line_end`
5. Calculate confidence score (semantic similarity score)
6. Store resolved paths in subgoal metadata

**Acceptance Criteria**:
- Retrieval called for each subgoal
- Paths include file location and line range
- Confidence scores between 0.0 and 1.0
- Results sorted by relevance

#### FR-3.2: Confidence Score Display

**Description**: Display confidence scores with file paths.

**The system must**:
1. Format: `<file-path> lines <start>-<end> (confidence: <score>)`
2. High confidence (>= 0.8): No annotation
3. Medium confidence (0.6-0.8): "(suggested)"
4. Low confidence (< 0.6): "(low confidence)"
5. No match: Task lacks file reference with warning

**Acceptance Criteria**:
- Confidence thresholds applied correctly
- Annotations visible in output
- Warning for low/no confidence paths

#### FR-3.3: Graceful Degradation

**Description**: Handle cases where memory is not indexed.

**The system must**:
1. Check `retriever.has_indexed_memory()` before retrieval
2. If not indexed: Display warning and generate generic paths
3. Warning: "Memory not indexed. Run 'aur mem index .' for code-aware tasks."
4. Generic paths use pattern: `src/<domain>/<task-slug>.py`
5. Mark tasks as "needs_file_resolution: true" in metadata

**Acceptance Criteria**:
- Warning displayed when memory not indexed
- Plan still generates (degraded mode)
- Generic paths follow consistent pattern
- Metadata indicates resolution needed

---

### FR-4: Agent Discovery Integration

#### FR-4.1: Agent Capability Matching

**Description**: Match agents to subgoals based on capabilities.

**The system must**:
1. Load `AgentManifest` via `ManifestManager`
2. For each subgoal, extract keywords from title and description
3. Search manifest: `manifest.search_by_capability(keywords)`
4. Score each agent by keyword overlap (0.0-1.0)
5. Select highest-scoring agent with score >= 0.5
6. Fall back to default agent if no match

**Acceptance Criteria**:
- Keywords extracted from subgoal text
- Scoring reflects capability match
- Threshold (0.5) configurable via config
- Default fallback: `@code-developer`

#### FR-4.2: Gap Detection and Recording

**Description**: Detect and record agent gaps for unmatched subgoals.

**The system must**:
1. If no agent scores >= 0.5, mark as gap
2. Record gap in `agents.json`: `{ "subgoal_id": "sg-X", "recommended_agent": "@<best-match>", "agent_exists": false, "fallback": "@code-developer", "suggested_capabilities": ["keyword1", "keyword2"] }`
3. Display gap warning during plan creation
4. Suggest creating missing agent or using fallback

**Acceptance Criteria**:
- Gaps recorded with full metadata
- Best-match agent recommended even if low score
- Fallback agent assigned
- Suggested capabilities for future agent creation

#### FR-4.3: Agent Existence Verification

**Description**: Verify recommended agents exist in manifest.

**The system must**:
1. For each recommended agent, call `manifest.get_agent(agent_id)`
2. Set `subgoal.agent_exists = True/False`
3. Non-existent agents added to `agent_gaps` list
4. Display warning for non-existent agents

**Acceptance Criteria**:
- All agent assignments verified
- `agent_exists` field accurate
- Gaps list complete
- Warning visible in output

---

### FR-5: User Checkpoint

#### FR-5.1: Decomposition Summary Display

**Description**: Display comprehensive summary after decomposition.

**The system must**:
1. Display goal echo: "Goal: <goal-text>"
2. Display subgoal summary: "Subgoals: N"
3. List each subgoal: "  [sg-N] <title> (@<agent>)"
4. Display agent summary: "Agents: X assigned, Y gaps"
5. Display file summary: "Files: X resolved (avg confidence: 0.XX)"
6. Display dependencies: "Dependencies: X (N total edges)"
7. Display complexity: "Complexity: <SIMPLE/MODERATE/COMPLEX>"
8. Format with Rich panels/colors

**Acceptance Criteria**:
- All summary sections displayed
- Subgoals listed with agents
- Gaps highlighted (different color)
- Rich formatting applied

#### FR-5.2: Confirmation Prompt

**Description**: Prompt user to confirm before file generation.

**The system must**:
1. Display prompt: "Proceed with plan generation? (Y/n)"
2. "Y" or Enter: Proceed with file generation
3. "n" or "N": Abort with message "Plan creation cancelled."
4. Invalid input: Repeat prompt
5. Ctrl+C: Abort gracefully

**Acceptance Criteria**:
- Default action is proceed (Enter)
- Abort leaves no files created
- Invalid input handled
- Graceful interrupt handling

#### FR-5.3: Non-Interactive Mode

**Description**: Support non-interactive mode for scripted usage.

**The system must**:
1. `--yes` flag bypasses confirmation
2. `--non-interactive` as alias for `--yes`
3. Summary still displayed (for logging)
4. Exit code 0 on success, non-zero on failure

**Acceptance Criteria**:
- Both flags work identically
- Output suitable for logging
- Exit codes correct

---

### FR-6: Plan File Generation Enhancement

#### FR-6.1: Enhanced tasks.md Generation

**Description**: Generate tasks.md with resolved file paths.

**The system must**:
1. Include file path for each task (when resolved)
2. Format: `- [ ] <task> **File**: <path> lines <range> (confidence: <score>)`
3. Group tasks by subgoal
4. Include agent assignment per group
5. Mark unresolved files: "**File**: TBD - run 'aur mem index' for resolution"

**Acceptance Criteria**:
- File paths from memory retrieval included
- Confidence scores visible
- Grouping by subgoal clear
- TBD markers for unresolved

#### FR-6.2: Enhanced agents.json Generation

**Description**: Generate comprehensive agents.json with gap information.

**The system must**:
1. Include existing fields (plan_id, goal, status, subgoals, etc.)
2. Add `agent_gaps` array with gap details
3. Add `file_resolutions` map: `{ "sg-1": { "files": [...], "confidence": 0.XX } }`
4. Add `decomposition_source`: "soar" or "heuristic"
5. Add `context_summary`: Summary used for decomposition

**Acceptance Criteria**:
- All new fields present
- Gap details complete
- File resolution metadata preserved
- Source documented

#### FR-6.3: Dependency Graph in plan.md

**Description**: Include visual dependency graph in plan.md.

**The system must**:
1. Generate ASCII dependency graph
2. Format: `sg-1 -> sg-2 -> sg-4` (linear)
3. Format: `sg-1 -> sg-3, sg-2 -> sg-3` (parallel)
4. Show blocked subgoals clearly
5. Include legend for symbols

**Acceptance Criteria**:
- Graph accurately represents dependencies
- Parallel dependencies visible
- Legend included
- ASCII renders correctly

---

## 5. Non-Goals (Deferred to PRD 0022)

The following items are explicitly **out of scope** for this PRD and deferred to PRD 0022: Agent Execution:

### Deferred: `aur plan implement` Command
- Plan execution with agent delegation
- Agent spawning per subgoal
- Sequential execution respecting dependencies
- Checkpoint/resume capability during execution
- Results collection per subgoal

### Deferred: Execution Orchestration
- Agent subprocess spawning: `aur agent run <agent-id> --goal <subgoal>`
- Dependency-based execution ordering
- Progress tracking with `state.json`
- Interactive gap resolution during execution
- Execution summary and rollback

### Deferred: Advanced Features
- Parallel subgoal execution
- Advanced retry logic
- Real-time progress UI
- Plan adjustment after checkpoint (editing decomposition)

---

## 6. Design Considerations

### Architecture Principles

1. **Integration-First**: Leverage existing systems (SOAR, Memory, AgentDiscovery) rather than reimplementing
2. **Graceful Degradation**: Each integration should fail gracefully (LLM down, memory not indexed, no agents)
3. **User Control**: Checkpoint allows users to abort before committing resources
4. **Atomic Operations**: File generation and archive operations are all-or-nothing

### Component Architecture

```
PlanDecomposer (NEW: aurora_planning/decompose.py)
├── Uses: SOAROrchestrator.decompose_query()
├── Uses: MemoryRetriever.retrieve()
├── Uses: AgentManifest.search_by_capability()
└── Returns: DecompositionSummary

FilePathResolver (NEW: aurora_planning/memory.py)
├── Wraps: MemoryRetriever
├── Provides: resolve_paths_for_subgoal()
└── Provides: format_path_with_confidence()

AgentRecommender (NEW: aurora_planning/agents.py)
├── Wraps: ManifestManager, AgentManifest
├── Provides: recommend_agent_for_subgoal()
├── Provides: detect_gaps()
└── Provides: get_fallback_agent()

ArchiveCommand (PORT: aurora_planning/commands/archive.py)
├── Port from: openspec-source/aurora/commands/archive.py
├── Updates: Paths to .aurora/plans/
├── Adds: Integration with Aurora validation
└── Preserves: Delta processing, atomic move
```

### Data Flow

```
User: /aur:plan "Implement OAuth2"
         │
         ▼
   ┌─────────────────────────────────────────────┐
   │ Phase 1: INTELLIGENT DECOMPOSITION          │
   │                                             │
   │  1. Load context (Memory or --context)      │
   │  2. Load available agents (AgentManifest)   │
   │  3. Call SOAR decompose_query()             │
   │  4. Resolve file paths (MemoryRetriever)    │
   │  5. Recommend agents (AgentManifest)        │
   │  6. Detect gaps, assign fallbacks           │
   └─────────────────────────────────────────────┘
         │
         ▼
   ┌─────────────────────────────────────────────┐
   │ CHECKPOINT: Display Summary                 │
   │                                             │
   │  Goal: Implement OAuth2                     │
   │  Subgoals: 4                                │
   │    [sg-1] Design auth architecture          │
   │           @system-architect               │
   │    [sg-2] Implement auth flow               │
   │           @code-developer                   │
   │           depends: sg-1                     │
   │    [sg-3] Add security measures             │
   │           @code-developer                   │
   │           depends: sg-2                     │
   │    [sg-4] Write auth tests                  │
   │           @quality-assurance (gap!)         │
   │           depends: sg-2, sg-3               │
   │                                             │
   │  Files: 8 resolved (avg: 0.85)              │
   │  Agents: 3 assigned, 1 gap                  │
   │  Complexity: MODERATE                       │
   │                                             │
   │  Proceed with plan generation? (Y/n)        │
   └─────────────────────────────────────────────┘
         │
         ▼ (user confirms: Y)
   ┌─────────────────────────────────────────────┐
   │ Phase 2: GENERATE PLAN FILES                │
   │                                             │
   │  Creates: .aurora/plans/active/0001-oauth/  │
   │    - plan.md (with dependency graph)        │
   │    - prd.md (OpenSpec format)               │
   │    - tasks.md (with file paths)             │
   │    - agents.json (with gaps, resolutions)   │
   │    - specs/*.md (capability specs)          │
   └─────────────────────────────────────────────┘
```

### Integration Points

| System | Module | Integration |
|--------|--------|-------------|
| SOAR | `aurora_soar.phases.decompose` | `decompose_query()` for LLM decomposition |
| Memory | `aurora_cli.memory.retrieval` | `MemoryRetriever.retrieve()` for file paths |
| AgentDiscovery | `aurora_cli.agent_discovery.manifest` | `ManifestManager`, `AgentManifest` |
| OpenSpec Archive | `openspec-source/aurora/commands/archive.py` | Port with path updates |
| Planning Core | `aurora_cli.planning.core` | Modify `create_plan()` to use new decomposer |

### Error Handling

| Error Condition | Behavior | User Message |
|-----------------|----------|--------------|
| LLM unavailable | Fallback to heuristics | "Using rule-based decomposition (LLM unavailable)" |
| Memory not indexed | Generic paths, warning | "Memory not indexed. Run 'aur mem index .'" |
| No agents found | Use default agent | "No agents in manifest. Using @code-developer" |
| Manifest load failure | Skip agent recommendations | "Agent manifest unavailable. Skipping recommendations." |
| Archive validation failure | Abort with details | "Validation failed: <details>. Fix or use --no-validate." |

---

## 7. Technical Considerations

### Dependencies

**Required (existing)**:
- `aurora_soar` package with `phases.decompose` module
- `aurora_cli.memory.retrieval` with `MemoryRetriever`
- `aurora_cli.agent_discovery` with `ManifestManager`, `AgentManifest`
- `aurora_cli.planning` with existing models and core functions

**Required (to port)**:
- `openspec-source/aurora/commands/archive.py` (638 lines)
- `openspec-source/aurora/parsers/requirements.py` (for delta parsing)
- `openspec-source/aurora/validation/validator.py` (for spec validation)

**New modules to create**:
- `aurora_planning/decompose.py` - PlanDecomposer class
- `aurora_planning/memory.py` - FilePathResolver class
- `aurora_planning/agents.py` - AgentRecommender class
- `aurora_planning/commands/archive.py` - ArchiveCommand port

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| SOAR decomposition | <10s | LLM call dominates |
| Memory retrieval | <2s per subgoal | Existing target |
| Agent matching | <500ms total | In-memory operation |
| Checkpoint display | <100ms | Formatting only |
| File generation | <5s total | Existing target |
| Archive operation | <3s | Atomic move + metadata |

### Configuration Options

```python
# In aurora_cli/config.py planning section
planning:
  decomposition:
    use_soar: true  # Enable SOAR decomposition
    fallback_to_heuristics: true  # Fallback when LLM unavailable
    llm_timeout_seconds: 30  # Timeout for LLM calls

  file_resolution:
    enabled: true  # Enable memory-based file resolution
    confidence_threshold: 0.6  # Minimum confidence for inclusion
    max_files_per_subgoal: 5  # Limit files per subgoal

  agent_matching:
    enabled: true  # Enable agent capability matching
    score_threshold: 0.5  # Minimum score for match
    default_fallback: "@code-developer"  # Default fallback agent

  checkpoint:
    enabled: true  # Enable user checkpoint
    non_interactive: false  # Default to interactive mode
```

---

## 8. Testing Strategy

### Test Coverage Targets

| Module | Target | Rationale |
|--------|--------|-----------|
| `decompose.py` | >= 90% | Core decomposition logic |
| `memory.py` | >= 90% | File resolution logic |
| `agents.py` | >= 90% | Agent matching logic |
| `commands/archive.py` | >= 95% | Ported from OpenSpec (maintain coverage) |
| Integration tests | >= 80% | End-to-end workflows |

### Test Categories

#### Unit Tests

**PlanDecomposer tests**:
- `test_decompose_with_soar_success`
- `test_decompose_soar_unavailable_fallback`
- `test_decompose_soar_timeout`
- `test_decompose_with_context_files`
- `test_decompose_without_context`
- `test_decompose_caching`

**FilePathResolver tests**:
- `test_resolve_paths_with_indexed_memory`
- `test_resolve_paths_memory_not_indexed`
- `test_confidence_score_formatting`
- `test_graceful_degradation`
- `test_line_range_extraction`

**AgentRecommender tests**:
- `test_recommend_agent_high_score`
- `test_recommend_agent_no_match_fallback`
- `test_detect_gaps`
- `test_agent_existence_check`
- `test_keyword_extraction`

**ArchiveCommand tests** (port from OpenSpec):
- `test_archive_complete_plan`
- `test_archive_incomplete_warns`
- `test_archive_with_spec_deltas`
- `test_archive_interactive_selection`
- `test_archive_atomic_rollback`
- `test_archive_flags_skip_specs`
- `test_archive_flags_no_validate`
- `test_archive_flags_yes`

#### Integration Tests

**End-to-end flow tests**:
- `test_plan_create_with_soar_and_checkpoint`
- `test_plan_create_graceful_degradation`
- `test_archive_with_full_spec_updates`
- `test_checkpoint_abort_no_files`
- `test_non_interactive_mode`

#### TDD Workflow

```bash
# For each new feature:
1. Write failing test
2. Run: pytest tests/unit/planning/test_decompose.py::test_decompose_with_soar_success -v
3. Implement feature
4. Run test: Green
5. Verify with shell: aur plan create "Test goal" --yes
6. Refactor
7. Commit
```

---

## 9. Success Metrics

### Quantitative Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| SOAR usage rate | >= 80% of plans | Plans with `decomposition_source: "soar"` |
| File resolution rate | >= 70% of tasks | Tasks with resolved file paths (confidence >= 0.6) |
| Agent match rate | >= 60% of subgoals | Subgoals with `agent_exists: true` |
| Checkpoint confirmation rate | >= 90% | Users who proceed after checkpoint |
| Archive success rate | >= 95% | Archives completing without error |
| Test coverage | >= 90% overall | pytest-cov report |

### Qualitative Metrics

- **User Feedback**: "Decomposition feels intelligent" - survey after 2 weeks
- **File Accuracy**: Users report file paths are correct >= 80% of time
- **Agent Fit**: Users report recommended agents are appropriate >= 70% of time

### Acceptance Gates

**Gate 1: Unit Tests** (Day 3)
- All unit tests passing
- Coverage >= 90% per module

**Gate 2: Integration Tests** (Day 5)
- All integration tests passing
- E2E flow working

**Gate 3: Manual Verification** (Day 6)
- `aur plan create "Test goal"` shows SOAR decomposition
- `aur archive 0001` processes spec deltas
- Checkpoint prompts correctly

---

## 10. Open Questions

1. **LLM Provider**: Which LLM should SOAR use for decomposition? (Claude, GPT-4, Ollama local?)
   - **Proposed**: Use configured LLM from `aurora_reasoning` package

2. **Spec Location**: Where should updated specs live after archive?
   - **Proposed**: `.aurora/capabilities/<capability>/spec.md` (new structure)
   - **Alternative**: Keep in archive directory only

3. **Checkpoint Adjustment**: Should checkpoint allow editing decomposition?
   - **Proposed**: Defer to PRD 0022 (complexity)
   - **Alternative**: Simple "adjust goal" option

4. **Agent Manifest Refresh**: Should manifest auto-refresh during plan creation?
   - **Proposed**: Use cached manifest (refresh in background)
   - **Alternative**: Always refresh for accuracy

5. **Confidence Threshold**: What's the right threshold for "suggested" vs "low confidence"?
   - **Proposed**: 0.8 (high), 0.6-0.8 (medium), <0.6 (low)
   - **Needs**: User testing to calibrate

---

## Appendices

### Appendix A: Archive Command Port Changes

**Original path mappings**:
- `openspec/changes/` -> `.aurora/plans/active/`
- `openspec/changes/archive/` -> `.aurora/plans/archive/`
- `openspec/specs/` -> `.aurora/capabilities/`

**Import changes**:
```python
# Original (OpenSpec)
from aurora.parsers.requirements import ...
from aurora.validation.validator import Validator

# Aurora port
from aurora_cli.planning.parsers.requirements import ...
from aurora_cli.planning.validation.validator import Validator
```

### Appendix B: DecompositionSummary Model

```python
@dataclass
class DecompositionSummary:
    """Summary of decomposition for checkpoint display."""

    goal: str
    subgoals: list[Subgoal]
    agents_assigned: int
    agent_gaps: list[str]
    files_resolved: int
    avg_confidence: float
    complexity: Complexity
    context_source: str  # "soar", "heuristic"
    warnings: list[str]

    def display(self) -> None:
        """Display formatted summary using Rich."""
        ...
```

### Appendix C: Enhanced agents.json Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Aurora Plan Agents Manifest v2",
  "type": "object",
  "required": ["plan_id", "goal", "status", "subgoals", "decomposition_source"],
  "properties": {
    "plan_id": { "type": "string", "pattern": "^[0-9]{4}-[a-z0-9-]+$" },
    "goal": { "type": "string" },
    "status": { "enum": ["active", "archived", "failed"] },
    "created_at": { "type": "string", "format": "date-time" },
    "archived_at": { "type": "string", "format": "date-time" },
    "decomposition_source": { "enum": ["soar", "heuristic"] },
    "context_summary": { "type": "string" },
    "complexity": { "enum": ["simple", "moderate", "complex"] },
    "subgoals": {
      "type": "array",
      "items": { "$ref": "#/definitions/Subgoal" }
    },
    "agent_gaps": {
      "type": "array",
      "items": { "$ref": "#/definitions/AgentGap" }
    },
    "file_resolutions": {
      "type": "object",
      "additionalProperties": { "$ref": "#/definitions/FileResolution" }
    }
  },
  "definitions": {
    "Subgoal": {
      "type": "object",
      "properties": {
        "id": { "type": "string", "pattern": "^sg-[0-9]+$" },
        "title": { "type": "string" },
        "description": { "type": "string" },
        "recommended_agent": { "type": "string", "pattern": "^@[a-z0-9-]+$" },
        "agent_exists": { "type": "boolean" },
        "dependencies": { "type": "array", "items": { "type": "string" } },
        "status": { "enum": ["pending", "in_progress", "completed", "blocked"] }
      }
    },
    "AgentGap": {
      "type": "object",
      "properties": {
        "subgoal_id": { "type": "string" },
        "recommended_agent": { "type": "string" },
        "agent_exists": { "type": "boolean" },
        "fallback": { "type": "string" },
        "suggested_capabilities": { "type": "array", "items": { "type": "string" } }
      }
    },
    "FileResolution": {
      "type": "object",
      "properties": {
        "files": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "path": { "type": "string" },
              "line_start": { "type": "integer" },
              "line_end": { "type": "integer" },
              "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
            }
          }
        },
        "avg_confidence": { "type": "number" }
      }
    }
  }
}
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-05 | Initial PRD with FR-1 through FR-6, comprehensive requirements for SOAR, Memory, AgentDiscovery integration, ArchiveCommand port, and user checkpoint |

---

**END OF PRD**

**Next Steps**:
1. Review and approve this PRD
2. Generate task list using `@2-generate-tasks` agent
3. Begin implementation following TDD workflow
4. Track progress in `/tasks/tasks-0021-plan-decomposition.md`
