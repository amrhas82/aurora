# PRD 0016: Aurora Agent Discovery and Planning CLI
## Product Requirements Document

**Version**: 1.0
**Date**: December 31, 2025
**Status**: Ready for Implementation
**Phase**: Sprint 3 - Agent Discovery & Planning
**Product**: AURORA CLI
**Dependencies**: Existing AgentRegistry (aurora_soar), Memory Commands (aur query)

---

## DOCUMENT PURPOSE

This PRD defines **Aurora Agent Discovery and Planning CLI** - a comprehensive command-line interface for discovering agents from multiple sources and generating actionable execution plans directly from natural language goals.

**Success Criteria**: This phase is complete when developers can discover agents in <500ms, generate execution plans in <10s, and integrate planning seamlessly with existing memory retrieval.

**Related Documents**:
- Previous Phase: `/tasks/0015-prd-bm25-trihybrid-memory-search.md` (Search foundations)
- Architecture: `packages/soar/src/aurora_soar/agent_registry.py` (Existing agent system)
- CLI Guide: `docs/cli/CLI_USAGE_GUIDE.md` (CLI patterns)

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Goals & Success Metrics](#2-goals--success-metrics)
3. [User Stories](#3-user-stories)
4. [Functional Requirements](#4-functional-requirements)
5. [Architecture & Design](#5-architecture--design)
6. [Quality Gates & Acceptance Criteria](#6-quality-gates--acceptance-criteria)
7. [Testing Strategy](#7-testing-strategy)
8. [Dependencies](#8-dependencies)
9. [Non-Goals (Out of Scope)](#9-non-goals-out-of-scope)
10. [Technical Considerations](#10-technical-considerations)
11. [Delivery Verification Checklist](#11-delivery-verification-checklist)

---

## 1. EXECUTIVE SUMMARY

### 1.1 What is Aurora Agent Discovery and Planning CLI?

A two-phase CLI enhancement that enables:

**Phase 1: Agent Discovery** (2-3 hours)
- Discover agents from multiple configuration sources
- Search agents by keyword, category, or capability
- Display detailed agent information
- Cache agent metadata for fast access

**Phase 2: Direct Planning** (4-6 hours)
- Generate execution plans from natural language goals
- Integrate with existing memory retrieval system
- Validate plans against available agents
- Export plans in multiple formats (Markdown, JSON, YAML)

### 1.2 Key Components

1. **Agent Discovery System**:
   - Multi-source agent manifest generation (`~/.claude/agents/`, `~/.config/ampcode/agents/`, etc.)
   - Frontmatter metadata extraction from `.md` agent files
   - Fast keyword search and category filtering
   - Auto-refresh with configurable intervals

2. **Planning Pipeline**:
   - Goal decomposition using SOAR Phase 3 logic
   - Agent validation and suggestion system
   - Context strategy: `--context` overrides indexed memory
   - Interactive mode with clarifying questions

3. **Shared Infrastructure**:
   - Common memory module shared with `aur query`
   - Configuration via `~/.aurora/config.json`
   - Error handling and graceful degradation

### 1.3 Why This Matters

**Current Pain Points**:
- No centralized agent discovery across different CLI tools
- No way to generate execution plans without full SOAR pipeline
- `aur query` requires indexed memory, but planning often needs custom context

**After This Feature**:
- Developers discover agents in <500ms (vs manual README scanning)
- Plans generated in <10s (vs 30s+ full SOAR)
- Context flexibility: use indexed memory OR provide custom files
- Seamless integration with existing Aurora CLI workflows

---

## 2. GOALS & SUCCESS METRICS

### 2.1 Primary Goals

1. **Enable fast agent discovery** across multiple configuration sources
2. **Generate actionable plans** from natural language goals in <10s
3. **Share memory logic** between query and planning commands
4. **Validate plans** against available agents with suggestions
5. **Support CI/CD workflows** with `--non-interactive` mode
6. **Maintain backwards compatibility** with existing CLI

### 2.2 Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Agent Discovery Latency** | <500ms | Benchmark manifest loading |
| **Plan Generation Latency** | <10s end-to-end | Benchmark full planning pipeline |
| **Manifest Accuracy** | 100% valid agents | Schema validation tests |
| **Agent Validation** | ≥90% catch missing agents | Test with invalid agent references |
| **Context Retrieval** | <2s indexed memory | Performance benchmarks |
| **Test Coverage** | ≥85% | pytest-cov |
| **Type Safety** | 0 mypy errors (strict) | mypy |

### 2.3 Phase Completion Criteria

Phase is **COMPLETE** when:
- ✅ All 8 agent discovery commands implemented and tested
- ✅ Planning pipeline operational with context strategy
- ✅ Agent validation suggests alternatives for missing agents
- ✅ Shared memory module refactored from `aur query`
- ✅ Configuration system supports auto-refresh settings
- ✅ All quality gates passed (≥85% coverage, 0 mypy errors)
- ✅ Documentation complete with examples and troubleshooting
- ✅ Integration tests pass for end-to-end workflows

---

## 3. USER STORIES

### 3.1 Developer Discovering Available Agents

**As a** developer new to Aurora,
**I want** to quickly discover what agents are available and their capabilities,
**So that** I can understand what automation is available without reading multiple README files.

**Acceptance Criteria**:
- `aur agents list` shows all agents with categories in <500ms
- `aur agents search "code review"` finds relevant agents
- `aur agents show qa-test-architect` displays full agent details
- Agents from multiple sources (claude, ampcode, droid, opencode) appear in one list
- Malformed agent files logged as warnings, don't crash command

**Testing Requirements**:
- Unit tests for manifest generation from multiple sources
- Integration test verifying discovery from all 4 directories
- Performance benchmark ensuring <500ms latency

---

### 3.2 Developer Planning Feature Implementation

**As a** developer planning a new feature,
**I want** to generate an execution plan from a natural language goal,
**So that** I have a structured breakdown of tasks before starting implementation.

**Acceptance Criteria**:
- `aur plan "Implement OAuth2 authentication"` generates multi-step plan
- Plan includes agent assignments, dependencies, execution order
- Plan references valid agents from manifest
- If agent missing, suggests similar agents
- Plan generated in <10s
- `--format markdown` outputs readable task list

**Testing Requirements**:
- Unit tests for plan generation logic
- Integration test with mock LLM responses
- Acceptance test matching user story exactly

---

### 3.3 Developer Using Custom Context for Planning

**As a** developer working on a specific feature,
**I want** to provide custom context files for planning instead of using indexed memory,
**So that** the plan focuses only on relevant code without noise from full codebase.

**Acceptance Criteria**:
- `aur plan "Add logging" --context src/auth.py src/utils.py` uses ONLY those files
- No merging with indexed memory when `--context` provided
- Warning shown if neither `--context` nor indexed memory available
- Context loading completes in <2s for 10 files

**Testing Requirements**:
- Unit test verifying context replacement (not merging)
- Integration test with indexed memory present but overridden
- Test warning displays when neither available

---

### 3.4 CI/CD Pipeline Using Planning for Validation

**As a** DevOps engineer,
**I want** to run planning in non-interactive mode for automated workflows,
**So that** CI/CD pipelines can validate feature feasibility without human input.

**Acceptance Criteria**:
- `aur plan "goal" --non-interactive` never prompts for input
- Exit code 0 on success, non-zero on failure
- JSON output via `--format json` machine-parseable
- Agent validation failures return structured error
- Budget checks enforced (no runaway costs)

**Testing Requirements**:
- Integration test simulating CI/CD environment
- Test exit codes for success/failure scenarios
- Validate JSON schema for machine parsing

---

## 4. FUNCTIONAL REQUIREMENTS

### 4.1 Agent Discovery Commands

**Package**: `packages/cli/src/aurora_cli/commands/agents.py`

#### 4.1.1 Command: `aur agents list`

**MUST** list all discovered agents with optional filtering:

```bash
# List all agents
aur agents list

# Filter by category
aur agents list --category eng
aur agents list --category qa
aur agents list --category product
```

**Output Format**:
```
Available Agents (15 total):

Engineering:
  • full-stack-dev          Full Stack Developer
  • holistic-architect      System Architect
  • context-initializer     Context Initializer

QA:
  • qa-test-architect       Test Architect & Quality Advisor

Product:
  • product-manager         Product Manager
  • product-owner           Product Owner
  • scrum-master            Scrum Master

Use 'aur agents show <agent-id>' for details
```

**Requirements**:
- Load from manifest at `~/.aurora/agents/manifest.json`
- Support category filtering (`eng`, `qa`, `product`)
- Display in alphabetical order within categories
- Show count of total agents
- Latency target: <500ms

---

#### 4.1.2 Command: `aur agents search`

**MUST** search agents by keyword:

```bash
# Search by keyword
aur agents search "test"
aur agents search "code review"
```

**Search Algorithm**:
1. Keyword matching in: `id`, `role`, `goal`, `skills`, `examples`, `when_to_use`
2. Case-insensitive matching
3. Rank by: exact match > partial match in role > partial match elsewhere
4. Return top 10 results

**Output Format**:
```
Search results for "test" (3 matches):

1. qa-test-architect (QA)
   Test Architect & Quality Advisor
   Skills: test-architecture, quality-gates, code-review

2. full-stack-dev (Engineering)
   Full Stack Developer
   Skills: testing, debugging, refactoring

3. scrum-master (Product)
   Scrum Master
   Skills: story-creation, retrospectives, testing-coordination
```

**Requirements**:
- Fuzzy keyword matching across metadata fields
- Highlight matching terms (optional)
- Ranked by relevance
- Latency target: <500ms

---

#### 4.1.3 Command: `aur agents show`

**MUST** display detailed agent information:

```bash
# Show specific agent
aur agents show qa-test-architect
```

**Output Format**:
```
Agent: qa-test-architect
================================================================================
Role:        Test Architect & Quality Advisor
Category:    QA
Goal:        Provide comprehensive test architecture review, quality gate
             decisions, and code improvement

Skills:
  • test-architecture
  • quality-gates
  • code-review
  • requirements-traceability
  • risk-assessment

When to Use:
  Use for comprehensive test architecture review, quality gate decisions,
  and code improvement. Provides thorough analysis including requirements
  traceability, risk assessment, and test strategy.

Examples:
  • Review PR before merge
  • Design test strategy for new feature
  • Assess technical debt and quality metrics

Dependencies:
  • full-stack-dev (for implementation context)
  • product-owner (for acceptance criteria)

Source: ~/.claude/agents/qa-test-architect.md
```

**Requirements**:
- Load agent metadata from manifest
- Display all metadata fields (required + optional)
- Format for readability (wrapping, indentation)
- Show source file location
- Error if agent not found with suggestions

---

#### 4.1.4 Command: `aur agents refresh`

**MUST** rebuild agent manifest from discovery sources:

```bash
# Force refresh
aur agents refresh

# Refresh happens automatically if:
# - Manifest doesn't exist
# - Auto-refresh enabled and interval exceeded
```

**Discovery Algorithm**:
1. Scan discovery locations:
   - `~/.claude/agents/*.md`
   - `~/.config/ampcode/agents/*.md`
   - `~/.config/droid/agents/*.md`
   - `~/.config/opencode/agents/*.md`

2. Extract frontmatter from each `.md` file:
```yaml
---
id: qa-test-architect
role: Test Architect & Quality Advisor
goal: Provide comprehensive test architecture review...
category: qa
skills:
  - test-architecture
  - quality-gates
examples:
  - Review PR before merge
when_to_use: Use for comprehensive test architecture review...
dependencies:
  - full-stack-dev
  - product-owner
---
```

3. Validate required fields: `id`, `role`, `goal`, `category`, `skills`
4. Skip files with invalid/missing frontmatter (log warning)
5. Write manifest to `~/.aurora/agents/manifest.json`

**Manifest Schema**:
```json
{
  "version": "1.0",
  "generated_at": "2025-12-31T23:59:59Z",
  "sources": [
    "~/.claude/agents",
    "~/.config/ampcode/agents",
    "~/.config/droid/agents",
    "~/.config/opencode/agents"
  ],
  "agents": [
    {
      "id": "qa-test-architect",
      "role": "Test Architect & Quality Advisor",
      "goal": "Provide comprehensive test architecture review...",
      "category": "qa",
      "skills": ["test-architecture", "quality-gates", "code-review"],
      "examples": ["Review PR before merge"],
      "when_to_use": "Use for comprehensive test architecture review...",
      "dependencies": ["full-stack-dev", "product-owner"],
      "source_file": "~/.claude/agents/qa-test-architect.md"
    }
  ],
  "stats": {
    "total_agents": 15,
    "by_category": {"eng": 7, "qa": 3, "product": 5},
    "malformed_files": 2
  }
}
```

**Requirements**:
- Multi-source discovery
- Frontmatter parsing with `pyyaml`
- Schema validation
- Error handling: skip malformed, log warnings
- Atomic write (temp file + rename)
- Latency target: <2s for 50 agents

---

### 4.2 Planning Commands

**Package**: `packages/cli/src/aurora_cli/commands/plan.py`

#### 4.2.1 Command: `aur plan`

**MUST** generate execution plan from natural language goal:

```bash
# Basic planning
aur plan "Implement OAuth2 authentication"

# With output file
aur plan "Add logging to auth module" --output tasks.md

# With format
aur plan "Refactor database layer" --format json
aur plan "Refactor database layer" --format yaml
aur plan "Refactor database layer" --format markdown  # default

# Interactive mode (asks clarifying questions)
aur plan "Build user dashboard" --interactive

# Non-interactive (no prompts, for CI/CD)
aur plan "Validate API endpoints" --non-interactive

# Custom context (overrides indexed memory)
aur plan "Add auth" --context src/auth.py src/utils.py

# Verbosity control
aur plan "goal" -v     # verbose
aur plan "goal" -vv    # very verbose (debug)
```

**Planning Pipeline**:

**Step 1: Context Retrieval**
```python
def retrieve_context(goal: str, context_paths: list[Path] | None) -> ContextData:
    """
    Retrieve context for planning.

    Strategy:
    1. If --context provided: use ONLY those files (no merging)
    2. Else if indexed memory available: use retrieval
    3. Else: warn and proceed with no context
    """
    if context_paths:
        # Load from files (no merging)
        return load_files(context_paths)

    if memory_index_exists():
        # Use existing retrieval logic (shared module)
        return retrieve_from_memory(goal, budget=15)

    warn("No context available. Use --context or run 'aur mem index .'")
    return ContextData.empty()
```

**Step 2: Goal Decomposition**
```python
def decompose_goal(goal: str, context: ContextData, agents: list[AgentInfo]) -> Plan:
    """
    Decompose goal into execution plan using SOAR Phase 3 logic.

    Reuses:
    - Decomposition prompts from aurora_soar.phases.decompose
    - LLM client from aurora_reasoning
    - Complexity assessment (simple goals skip decomposition)
    """
    # Assess complexity
    complexity = assess_complexity(goal)

    if complexity == "simple":
        # Single-step plan, direct LLM
        return create_simple_plan(goal, context)

    # Complex goal: full decomposition
    return create_complex_plan(goal, context, agents, complexity)
```

**Step 3: Agent Validation**
```python
def validate_plan(plan: Plan, agents: list[AgentInfo]) -> ValidationResult:
    """
    Validate that all referenced agents exist.

    For missing agents, suggest similar agents:
    1. Search by capability keywords
    2. Search by role similarity
    3. Offer fallback "llm-executor"
    """
    issues = []

    for task in plan.tasks:
        if task.agent_id not in agent_ids:
            suggestions = find_similar_agents(task.agent_id, agents)
            issues.append(AgentNotFoundIssue(
                task_id=task.id,
                agent_id=task.agent_id,
                suggestions=suggestions
            ))

    return ValidationResult(issues=issues, suggestions=suggestions)
```

**Step 4: Output Formatting**
```python
def format_plan(plan: Plan, format: str, output_file: Path | None) -> str:
    """
    Format plan for output.

    Formats:
    - markdown: Human-readable task list with agent assignments
    - json: Machine-readable for CI/CD
    - yaml: Machine-readable, more human-friendly than JSON
    """
    if format == "markdown":
        return format_markdown(plan)
    elif format == "json":
        return format_json(plan)
    elif format == "yaml":
        return format_yaml(plan)
```

**Plan Schema**:
```json
{
  "goal": "Implement OAuth2 authentication",
  "complexity": "complex",
  "generated_at": "2025-12-31T23:59:59Z",
  "context_sources": ["indexed_memory", "src/auth.py"],
  "tasks": [
    {
      "id": "task-1",
      "description": "Research OAuth2 providers (Auth0, Okta, Custom)",
      "agent_id": "business-analyst",
      "agent_exists": true,
      "dependencies": [],
      "expected_output": "Comparison of providers with recommendation"
    },
    {
      "id": "task-2",
      "description": "Design user model with OAuth fields",
      "agent_id": "full-stack-dev",
      "agent_exists": true,
      "dependencies": ["task-1"],
      "expected_output": "User model schema with OAuth fields"
    }
  ],
  "execution_order": ["task-1", "task-2", "task-3"],
  "parallelizable": [],
  "validation": {
    "all_agents_exist": true,
    "missing_agents": [],
    "warnings": []
  }
}
```

**Markdown Output Format**:
```markdown
# Execution Plan: Implement OAuth2 authentication

**Generated**: 2025-12-31 23:59:59
**Complexity**: complex
**Context**: 5 code files, 2 reasoning patterns

## Tasks

### Task 1: Research OAuth2 providers
- **Agent**: business-analyst
- **Dependencies**: None
- **Expected Output**: Comparison of providers with recommendation

### Task 2: Design user model with OAuth fields
- **Agent**: full-stack-dev
- **Dependencies**: Task 1
- **Expected Output**: User model schema with OAuth fields

### Task 3: Implement token generation
- **Agent**: full-stack-dev
- **Dependencies**: Task 2
- **Expected Output**: Working token generation and validation

---

**Execution Order**: task-1 → task-2 → task-3
**Parallelizable**: None
```

**Requirements**:
- Reuse SOAR decomposition logic (shared module)
- Context strategy: `--context` overrides indexed memory
- Agent validation with suggestions
- Multiple output formats (markdown, json, yaml)
- Interactive mode asks clarifying questions
- Non-interactive mode never prompts
- Latency target: <10s end-to-end

---

### 4.3 Configuration System

**File**: `~/.aurora/config.json`

**Agent Configuration Schema**:
```json
{
  "agents": {
    "auto_refresh": true,
    "refresh_interval_hours": 24,
    "discovery_paths": [
      "~/.claude/agents",
      "~/.config/ampcode/agents",
      "~/.config/droid/agents",
      "~/.config/opencode/agents"
    ],
    "manifest_path": "~/.aurora/agents/manifest.json"
  },
  "planning": {
    "default_format": "markdown",
    "default_complexity": "auto",
    "enable_interactive": true,
    "max_tasks": 20,
    "llm_provider": "anthropic",
    "llm_model": "claude-sonnet-4.5"
  }
}
```

**Auto-Refresh Logic**:
```python
def should_refresh_manifest(manifest_path: Path, config: Config) -> bool:
    """
    Determine if manifest needs refresh.

    Refresh if:
    1. Manifest doesn't exist
    2. Auto-refresh enabled AND interval exceeded
    """
    if not manifest_path.exists():
        return True

    if not config.get("agents.auto_refresh"):
        return False

    interval_hours = config.get("agents.refresh_interval_hours")
    manifest_age_hours = get_file_age_hours(manifest_path)

    return manifest_age_hours >= interval_hours
```

**Configuration Validation**:
- All paths must be absolute (expand `~`)
- Interval must be positive integer
- Default format must be one of: markdown, json, yaml
- Discovery paths must be directories (warn if missing)

---

### 4.4 Shared Memory Module

**Package**: `packages/cli/src/aurora_cli/memory/retrieval.py`

**MUST** refactor memory retrieval from `aur query` into shared module:

```python
class MemoryRetrieval:
    """
    Shared memory retrieval logic for query and planning commands.

    Provides unified interface for:
    - Checking if indexed memory exists
    - Retrieving context by query/goal
    - Loading custom context files
    - Formatting context for LLM consumption
    """

    def __init__(self, store: Store, config: Config):
        self.store = store
        self.config = config

    def exists(self) -> bool:
        """Check if indexed memory available."""
        return self.store.chunk_count() > 0

    def retrieve(self, query: str, budget: int = 15) -> ContextData:
        """Retrieve context from indexed memory."""
        # Reuse existing retrieval logic from aur query
        pass

    def load_files(self, paths: list[Path]) -> ContextData:
        """Load context from custom files."""
        # Parse files, extract relevant content
        pass

    def format_for_llm(self, context: ContextData) -> str:
        """Format context for LLM prompt."""
        # Convert to LLM-consumable format
        pass
```

**Requirements**:
- Extract from existing `aur query` implementation
- Support both indexed memory and file loading
- Consistent error handling
- Performance: <2s for 15 chunks

---

## 5. ARCHITECTURE & DESIGN

### 5.1 Package Structure

```
packages/
├── cli/
│   ├── src/aurora_cli/
│   │   ├── commands/
│   │   │   ├── agents.py          # NEW: Agent discovery commands
│   │   │   ├── plan.py            # NEW: Planning commands
│   │   │   └── query.py           # REFACTOR: Use shared memory module
│   │   ├── memory/
│   │   │   └── retrieval.py       # NEW: Shared memory retrieval
│   │   ├── agent_discovery/       # NEW
│   │   │   ├── scanner.py         # Multi-source agent discovery
│   │   │   ├── parser.py          # Frontmatter extraction
│   │   │   └── manifest.py        # Manifest generation
│   │   ├── planning/              # NEW
│   │   │   ├── pipeline.py        # Planning pipeline orchestration
│   │   │   ├── decompose.py       # Goal decomposition (reuses SOAR)
│   │   │   ├── validation.py      # Agent validation
│   │   │   └── formatters.py      # Output formatters (md/json/yaml)
│   │   └── config.py              # EXTEND: Agent config schema
│   └── depends on → soar/, reasoning/, core/
│
├── soar/
│   ├── src/aurora_soar/
│   │   ├── agent_registry.py      # EXISTING: Keep unchanged
│   │   └── phases/
│   │       └── decompose.py       # REUSE: Decomposition logic
│   └── depends on → reasoning/, core/
```

### 5.2 Agent Discovery Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│               AGENT DISCOVERY PIPELINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: Multi-Source Scanning                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Scanner.discover_agents()                            │   │
│  │  ├─ Scan ~/.claude/agents/*.md                       │   │
│  │  ├─ Scan ~/.config/ampcode/agents/*.md               │   │
│  │  ├─ Scan ~/.config/droid/agents/*.md                 │   │
│  │  └─ Scan ~/.config/opencode/agents/*.md              │   │
│  └──────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  Step 2: Frontmatter Extraction                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Parser.extract_metadata(file)                        │   │
│  │  ├─ Parse YAML frontmatter                           │   │
│  │  ├─ Validate required fields                         │   │
│  │  ├─ Extract optional fields                          │   │
│  │  └─ Skip malformed (log warning)                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  Step 3: Manifest Generation                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Manifest.generate(agents)                            │   │
│  │  ├─ Aggregate agents from all sources               │   │
│  │  ├─ De-duplicate by ID (warn on conflict)           │   │
│  │  ├─ Build category index                            │   │
│  │  ├─ Generate stats                                  │   │
│  │  └─ Write to ~/.aurora/agents/manifest.json         │   │
│  └──────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  Step 4: Query Interface                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Commands use manifest for:                           │   │
│  │  ├─ aur agents list [--category]                     │   │
│  │  ├─ aur agents search <keyword>                      │   │
│  │  ├─ aur agents show <id>                             │   │
│  │  └─ Auto-refresh if needed                           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Planning Pipeline Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  PLANNING PIPELINE                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input: aur plan "goal" [--context files] [--format fmt]    │
│                         ↓                                    │
│  Step 1: Context Retrieval                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ MemoryRetrieval.get_context()                        │   │
│  │  ├─ If --context: load ONLY those files              │   │
│  │  ├─ Else if indexed memory: retrieve by goal         │   │
│  │  └─ Else: warn, proceed with no context              │   │
│  └──────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  Step 2: Load Agent Manifest                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ AgentDiscovery.load_manifest()                       │   │
│  │  ├─ Check if manifest exists                         │   │
│  │  ├─ Auto-refresh if needed (config)                  │   │
│  │  └─ Return list of available agents                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  Step 3: Complexity Assessment                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ assess_complexity(goal)  [REUSE SOAR]                │   │
│  │  ├─ Simple: single-step plan                         │   │
│  │  └─ Complex: full decomposition                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  Step 4: Goal Decomposition                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ decompose_goal(goal, context, agents)  [REUSE SOAR]  │   │
│  │  ├─ Use SOAR Phase 3 decomposition prompts           │   │
│  │  ├─ Include available agents in prompt               │   │
│  │  ├─ LLM generates task breakdown                     │   │
│  │  └─ Return Plan with tasks + agent assignments       │   │
│  └──────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  Step 5: Agent Validation                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ validate_plan(plan, agents)                          │   │
│  │  ├─ Check each task's agent_id exists               │   │
│  │  ├─ If missing: find similar agents                 │   │
│  │  ├─ Suggest alternatives                             │   │
│  │  └─ Return ValidationResult                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  Step 6: Output Formatting                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ format_plan(plan, format)                            │   │
│  │  ├─ markdown: Human-readable task list               │   │
│  │  ├─ json: Machine-readable for CI/CD                 │   │
│  │  └─ yaml: Human-friendly machine-readable            │   │
│  └──────────────────────────────────────────────────────┘   │
│                         ↓                                    │
│  Output: Plan written to stdout or --output file            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.4 Context Strategy Decision Tree

```
User runs: aur plan "goal" [--context files]
                    ↓
          ┌─────────┴─────────┐
          │  --context flag?  │
          └─────────┬─────────┘
              Yes ↙   ↘ No
                /       \
               /         \
    Load custom files   Check indexed memory
    (NO MERGING)              ↓
         ↓            ┌────────┴────────┐
         │            │  Memory exists?  │
         │            └────────┬────────┘
         │               Yes ↙   ↘ No
         │                 /       \
         │                /         \
         │        Retrieve from     Warn user
         │        indexed memory    (no context)
         │               ↓               ↓
         └───────────────┴───────────────┘
                         ↓
              Use context for planning
```

**Critical Decision**: `--context` COMPLETELY REPLACES indexed memory (no merging)

**Rationale**:
- User provides `--context` when they want focused planning
- Merging would add noise from unrelated code
- Explicit is better than implicit (Zen of Python)

---

## 6. QUALITY GATES & ACCEPTANCE CRITERIA

### 6.1 Code Quality Gates

| Gate | Requirement | Tool | Blocker |
|------|-------------|------|---------|
| **Code Coverage** | ≥85% for agent_discovery/, planning/ | pytest-cov | YES |
| **Type Checking** | 0 mypy errors (strict mode) | mypy | YES |
| **Linting** | 0 critical issues | ruff | YES |
| **Security** | 0 high/critical vulnerabilities | bandit | YES |

### 6.2 Performance Gates

| Metric | Target | Measurement | Blocker |
|--------|--------|-------------|---------|
| **Agent Discovery** | <500ms | Benchmark manifest load | YES |
| **Agent Search** | <500ms | Benchmark keyword search | NO (warning) |
| **Plan Generation** | <10s end-to-end | Benchmark full pipeline | YES |
| **Context Loading** | <2s for 10 files | Benchmark file loading | NO (warning) |
| **Manifest Refresh** | <2s for 50 agents | Benchmark full refresh | NO (warning) |

### 6.3 Functional Acceptance Tests

**Each scenario MUST pass**:

#### Test Scenario 1: Multi-Source Agent Discovery

```python
def test_agent_discovery_multisource():
    """Discover agents from multiple sources."""
    # GIVEN: Agent files in 4 different directories
    create_agent_file("~/.claude/agents/qa-test-architect.md")
    create_agent_file("~/.config/ampcode/agents/full-stack-dev.md")
    create_agent_file("~/.config/droid/agents/scrum-master.md")
    create_agent_file("~/.config/opencode/agents/ux-expert.md")

    # WHEN: Run agent refresh
    result = runner.invoke(cli, ["agents", "refresh"])

    # THEN: All 4 agents in manifest
    manifest = load_manifest()
    assert len(manifest["agents"]) == 4
    assert "qa-test-architect" in agent_ids(manifest)
    assert "full-stack-dev" in agent_ids(manifest)
    assert result.exit_code == 0
```

#### Test Scenario 2: Agent Validation with Suggestions

```python
def test_plan_agent_validation():
    """Plan validation suggests similar agents for missing ones."""
    # GIVEN: Plan references non-existent agent
    manifest = load_manifest_with_agents([
        "full-stack-dev", "qa-test-architect", "business-analyst"
    ])

    # WHEN: Generate plan that references "code-reviewer"
    result = runner.invoke(cli, [
        "plan", "Review code for security issues"
    ])

    # THEN: Validation suggests "qa-test-architect"
    assert "Agent 'code-reviewer' not found" in result.output
    assert "Did you mean: qa-test-architect?" in result.output
    assert result.exit_code == 0  # Warning, not error
```

#### Test Scenario 3: Context Strategy (Override)

```python
def test_plan_context_override():
    """--context overrides indexed memory."""
    # GIVEN: Indexed memory exists with 100 chunks
    store.index_directory(".")
    assert store.chunk_count() == 100

    # AND: Custom context files
    custom_files = ["src/auth.py", "src/utils.py"]

    # WHEN: Plan with --context
    result = runner.invoke(cli, [
        "plan", "Add logging",
        "--context", *custom_files
    ])

    # THEN: Uses ONLY custom files (not indexed memory)
    plan = json.loads(result.output)
    assert plan["context_sources"] == custom_files
    assert "indexed_memory" not in plan["context_sources"]
```

#### Test Scenario 4: Non-Interactive Mode

```python
def test_plan_non_interactive():
    """Non-interactive mode never prompts."""
    # GIVEN: Goal that would normally trigger questions
    goal = "Build complex feature"

    # WHEN: Run in non-interactive mode
    result = runner.invoke(cli, [
        "plan", goal, "--non-interactive"
    ], input="")  # No input provided

    # THEN: Completes without prompts
    assert result.exit_code == 0
    assert "?" not in result.output  # No questions asked
```

#### Test Scenario 5: Format Output Variations

```python
def test_plan_output_formats():
    """Plan supports multiple output formats."""
    goal = "Implement authentication"

    # Test markdown (default)
    md_result = runner.invoke(cli, ["plan", goal])
    assert md_result.output.startswith("# Execution Plan")

    # Test JSON
    json_result = runner.invoke(cli, ["plan", goal, "--format", "json"])
    plan = json.loads(json_result.output)
    assert "tasks" in plan
    assert "goal" in plan

    # Test YAML
    yaml_result = runner.invoke(cli, ["plan", goal, "--format", "yaml"])
    plan = yaml.safe_load(yaml_result.output)
    assert "tasks" in plan
```

---

## 7. TESTING STRATEGY

### 7.1 Unit Tests

**Agent Discovery**:
- `test_scanner.py`: Multi-source directory scanning
- `test_parser.py`: Frontmatter extraction, validation
- `test_manifest.py`: Manifest generation, de-duplication
- `test_commands_agents.py`: CLI commands (list, search, show, refresh)

**Planning**:
- `test_pipeline.py`: Planning pipeline orchestration
- `test_decompose.py`: Goal decomposition (mocks SOAR)
- `test_validation.py`: Agent validation, suggestions
- `test_formatters.py`: Output formatting (md/json/yaml)
- `test_commands_plan.py`: CLI commands

**Shared**:
- `test_memory_retrieval.py`: Memory retrieval module
- `test_config.py`: Configuration schema, auto-refresh logic

### 7.2 Integration Tests

**MUST test end-to-end workflows**:

1. **Agent Discovery E2E**: Scan → Parse → Generate manifest → Query
2. **Planning E2E**: Context retrieval → Decomposition → Validation → Format
3. **Context Override**: Verify `--context` replaces indexed memory
4. **Auto-Refresh**: Trigger auto-refresh on stale manifest
5. **Multi-Format**: Generate plans in all 3 formats (md/json/yaml)

### 7.3 Performance Benchmarks

```python
def test_performance_benchmarks(benchmark_fixture):
    """Benchmark discovery and planning performance."""

    test_cases = [
        ("agent_discovery", "agents refresh", 500),
        ("agent_search", "agents search test", 500),
        ("plan_simple", "plan 'simple goal'", 5000),
        ("plan_complex", "plan 'complex goal'", 10000),
    ]

    for name, command, max_ms in test_cases:
        with benchmark_fixture.measure(name):
            runner.invoke(cli, command.split())

        benchmark_fixture.assert_performance(name, max_ms=max_ms)
```

### 7.4 Acceptance Tests

**MUST match user stories exactly**:

- User Story 3.1: Developer discovering agents
- User Story 3.2: Developer planning feature
- User Story 3.3: Custom context for planning
- User Story 3.4: CI/CD non-interactive mode

Each acceptance test should:
1. Use exact commands from user story
2. Verify exact acceptance criteria
3. Measure against performance targets

---

## 8. DEPENDENCIES

### 8.1 Existing Aurora Components

| Component | Package | Usage |
|-----------|---------|-------|
| **AgentRegistry** | aurora_soar | Reference architecture (not modified) |
| **SOAR Decomposition** | aurora_soar.phases.decompose | Reuse decomposition logic |
| **LLM Client** | aurora_reasoning | LLM integration |
| **Store** | aurora_core | Memory retrieval |
| **Config** | aurora_core | Configuration system |

### 8.2 External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| **pyyaml** | ≥6.0 | Frontmatter parsing |
| **click** | ≥8.0 | CLI framework (existing) |
| **pydantic** | ≥2.0 | Schema validation |

### 8.3 Breaking Changes

**None**. This feature:
- Adds new commands (`aur agents`, `aur plan`)
- Refactors shared logic (internal only)
- Does NOT change existing command behavior

---

## 9. NON-GOALS (OUT OF SCOPE)

### 9.1 Explicitly NOT in This Phase

| Feature | Why Not Now | When |
|---------|-------------|------|
| **CrewAI Adapters** | Requires CrewAI-specific agent format | Future (if needed) |
| **Agent Execution** | Planning only, not execution | Future (Phase 3?) |
| **80+ Tools Library** | Focus on discovery, not tooling | Future |
| **Agent Versioning** | Adds complexity, defer | Future |
| **Multi-Repo Discovery** | Single-machine focus for MVP | Future |
| **Agent Marketplace** | Too early, need adoption first | Future |
| **GUI for Planning** | CLI-first approach | Future |

### 9.2 Technical Constraints (Accepted)

- **No agent sandboxing**: Discovery only, trust local files
- **No distributed manifest**: Single-machine manifest cache
- **No real-time refresh**: Interval-based or manual refresh
- **No plan execution**: Generate plans, don't run them

---

## 10. TECHNICAL CONSIDERATIONS

### 10.1 Frontmatter Parsing

**Critical Requirements**:
- Support YAML frontmatter only (not TOML, JSON)
- Strict schema validation (required fields)
- Graceful degradation: skip malformed, log warnings
- No partial parsing: all-or-nothing per file

**Example Valid Frontmatter**:
```yaml
---
id: qa-test-architect
role: Test Architect & Quality Advisor
goal: Provide comprehensive test architecture review
category: qa
skills:
  - test-architecture
  - quality-gates
examples:
  - Review PR before merge
when_to_use: Use for comprehensive test architecture review
dependencies:
  - full-stack-dev
---
```

**Invalid Cases** (skip with warning):
- Missing required field (`id`, `role`, `goal`, `category`, `skills`)
- Invalid YAML syntax
- Non-list `skills` or `dependencies`
- Empty `id` or `role`

### 10.2 Agent Suggestion Algorithm

**When agent not found, suggest similar agents**:

```python
def find_similar_agents(
    missing_id: str,
    available_agents: list[AgentInfo]
) -> list[AgentInfo]:
    """
    Find similar agents using multi-strategy matching.

    Strategies (in order):
    1. Fuzzy ID match (edit distance <3)
    2. Capability keyword match
    3. Role keyword match
    4. Category match

    Returns top 3 suggestions.
    """
    candidates = []

    # Strategy 1: Fuzzy ID match
    for agent in available_agents:
        distance = levenshtein_distance(missing_id, agent.id)
        if distance <= 3:
            candidates.append((agent, 1.0 / (distance + 1)))

    # Strategy 2: Capability match
    missing_keywords = extract_keywords(missing_id)
    for agent in available_agents:
        overlap = len(set(missing_keywords) & set(agent.capabilities))
        if overlap > 0:
            candidates.append((agent, overlap / len(missing_keywords)))

    # Strategy 3: Role match
    for agent in available_agents:
        if any(kw in agent.role.lower() for kw in missing_keywords):
            candidates.append((agent, 0.5))

    # Deduplicate and rank
    ranked = deduplicate_and_rank(candidates)
    return ranked[:3]  # Top 3
```

### 10.3 Context Replacement Strategy

**Why replacement (not merging)?**

**Problem with merging**:
```python
# User provides specific context
aur plan "Add logging" --context src/auth.py

# WRONG: Merge with indexed memory
context = load_files(["src/auth.py"]) + retrieve_from_memory("Add logging")
# Result: auth.py + 15 unrelated chunks (noise)
```

**Correct: Complete replacement**:
```python
# RIGHT: Use ONLY provided context
if --context:
    context = load_files(["src/auth.py"])  # ONLY this
else:
    context = retrieve_from_memory("Add logging")  # OR this
```

**Rationale**:
- User provides `--context` when indexed memory is wrong/noisy
- Explicit override matches user expectations
- Simpler to understand and test
- Follows principle of least surprise

### 10.4 Manifest Caching Strategy

**Tradeoffs**:

| Approach | Pros | Cons |
|----------|------|------|
| **No caching** | Always fresh | Slow (2s every command) |
| **Cache forever** | Fast (<50ms) | Stale data |
| **Auto-refresh (interval)** | Balance | Config complexity |

**Chosen: Auto-refresh with interval**

**Implementation**:
```python
def load_manifest(config: Config) -> Manifest:
    """
    Load manifest with auto-refresh logic.

    1. Check if manifest exists
    2. If not, refresh
    3. If yes, check age vs interval
    4. If stale, refresh
    5. Return manifest
    """
    manifest_path = Path(config.get("agents.manifest_path"))

    if not manifest_path.exists():
        refresh_manifest(config)
    elif should_refresh_manifest(manifest_path, config):
        refresh_manifest(config)

    return Manifest.load(manifest_path)
```

**Default Interval**: 24 hours (configurable)

---

## 11. DELIVERY VERIFICATION CHECKLIST

**Phase is complete when ALL items checked**:

### 11.1 Implementation Complete

- [ ] Agent discovery commands implemented (`list`, `search`, `show`, `refresh`)
- [ ] Planning command implemented with all flags
- [ ] Frontmatter parser with validation
- [ ] Manifest generation with multi-source discovery
- [ ] Agent validation with suggestions
- [ ] Output formatters (markdown, json, yaml)
- [ ] Shared memory retrieval module
- [ ] Configuration schema extended for agents
- [ ] Auto-refresh logic operational

### 11.2 Testing Complete

- [ ] Unit test coverage ≥85% for new modules
- [ ] All integration tests pass (5 scenarios)
- [ ] All acceptance tests match user stories
- [ ] Performance benchmarks meet targets
- [ ] Edge cases tested (malformed files, missing agents)

### 11.3 Documentation Complete

- [ ] CLI help text for all commands with examples
- [ ] `docs/cli/CLI_USAGE_GUIDE.md` updated with agent commands
- [ ] `docs/cli/CLI_USAGE_GUIDE.md` updated with planning commands
- [ ] Configuration schema documented
- [ ] Troubleshooting section for common errors
- [ ] Example workflows (discovery → planning → execution)

### 11.4 Quality Assurance

- [ ] Code review completed (2+ reviewers)
- [ ] MyPy strict mode passes (0 errors)
- [ ] Ruff linting passes (0 critical)
- [ ] Security audit passed (bandit)
- [ ] Performance profiling completed

### 11.5 Integration Verification

- [ ] Existing `aur query` still works (no regression)
- [ ] Existing `aur mem` commands still work
- [ ] MCP integration unaffected
- [ ] Configuration backward compatible

---

## APPENDIX A: SAMPLE AGENT FILE

**File**: `~/.claude/agents/qa-test-architect.md`

```markdown
---
id: qa-test-architect
role: Test Architect & Quality Advisor
goal: Provide comprehensive test architecture review, quality gate decisions, and code improvement
category: qa
skills:
  - test-architecture
  - quality-gates
  - code-review
  - requirements-traceability
  - risk-assessment
examples:
  - Review PR before merge
  - Design test strategy for new feature
  - Assess technical debt and quality metrics
when_to_use: Use for comprehensive test architecture review, quality gate decisions, and code improvement. Provides thorough analysis including requirements traceability, risk assessment, and test strategy. Advisory only - teams choose their quality bar.
dependencies:
  - full-stack-dev
  - product-owner
---

# QA Test Architect & Quality Advisor

## Overview

The QA Test Architect provides comprehensive test architecture review and quality guidance...

[Rest of agent documentation...]
```

---

## APPENDIX B: SAMPLE MANIFEST

**File**: `~/.aurora/agents/manifest.json`

```json
{
  "version": "1.0",
  "generated_at": "2025-12-31T23:59:59Z",
  "sources": [
    "/home/user/.claude/agents",
    "/home/user/.config/ampcode/agents",
    "/home/user/.config/droid/agents",
    "/home/user/.config/opencode/agents"
  ],
  "agents": [
    {
      "id": "qa-test-architect",
      "role": "Test Architect & Quality Advisor",
      "goal": "Provide comprehensive test architecture review, quality gate decisions, and code improvement",
      "category": "qa",
      "skills": [
        "test-architecture",
        "quality-gates",
        "code-review",
        "requirements-traceability",
        "risk-assessment"
      ],
      "examples": [
        "Review PR before merge",
        "Design test strategy for new feature",
        "Assess technical debt and quality metrics"
      ],
      "when_to_use": "Use for comprehensive test architecture review, quality gate decisions, and code improvement. Provides thorough analysis including requirements traceability, risk assessment, and test strategy. Advisory only - teams choose their quality bar.",
      "dependencies": [
        "full-stack-dev",
        "product-owner"
      ],
      "source_file": "/home/user/.claude/agents/qa-test-architect.md"
    }
  ],
  "stats": {
    "total_agents": 15,
    "by_category": {
      "eng": 7,
      "qa": 3,
      "product": 5
    },
    "malformed_files": 2,
    "last_refresh": "2025-12-31T23:59:59Z"
  }
}
```

---

## APPENDIX C: SAMPLE PLAN OUTPUT (MARKDOWN)

```markdown
# Execution Plan: Implement OAuth2 Authentication

**Generated**: 2025-12-31 23:59:59
**Complexity**: complex
**Context**: 5 code files, 2 reasoning patterns
**Estimated Time**: 4-6 hours

---

## Tasks

### Task 1: Research OAuth2 Providers
- **ID**: task-1
- **Agent**: business-analyst ✓
- **Dependencies**: None
- **Expected Output**: Comparison of Auth0, Okta, and custom implementation with recommendation

### Task 2: Design User Model with OAuth Fields
- **ID**: task-2
- **Agent**: full-stack-dev ✓
- **Dependencies**: task-1
- **Expected Output**: Database schema with user table including oauth_provider, oauth_id, access_token, refresh_token fields

### Task 3: Implement Token Generation and Validation
- **ID**: task-3
- **Agent**: full-stack-dev ✓
- **Dependencies**: task-2
- **Expected Output**: Working token generation endpoint (/auth/token) and validation middleware

### Task 4: Write Integration Tests for OAuth Flow
- **ID**: task-4
- **Agent**: qa-test-architect ✓
- **Dependencies**: task-3
- **Expected Output**: Passing integration tests covering login flow, token refresh, and error cases

---

## Execution Strategy

**Execution Order**: task-1 → task-2 → task-3 → task-4

**Parallelizable**: None (sequential dependencies)

**Critical Path**: All tasks (each depends on previous)

---

## Validation

✓ All agents exist in registry
✓ No circular dependencies
✓ Execution order satisfies dependencies

---

**Next Steps**:
1. Review plan for accuracy
2. Execute tasks in order using `aur execute` (future feature)
3. Track progress in task management system
```

---

## DOCUMENT HISTORY

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-31 | Initial PRD for Agent Discovery and Planning CLI | Product Team |

---

**END OF PRD 0016: Aurora Agent Discovery and Planning CLI**
