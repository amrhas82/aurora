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

**Step 3: Agent Recommendation and Gap Detection**
```python
def recommend_agents_for_subgoals(
    plan: Plan,
    agents: list[AgentInfo]
) -> tuple[Plan, list[AgentGap]]:
    """
    Recommend agents for each subgoal and detect gaps.

    Algorithm:
    1. For each subgoal, extract capability keywords from description
    2. Search agents by capability match (skills field)
    3. Rank by keyword overlap
    4. Assign top-ranked agent to subgoal
    5. If no good match (score < 0.5), mark as gap

    Gap Detection:
    - Identifies missing agent types (e.g., technical-writer)
    - Suggests required capabilities for missing agent
    - Provides fallback recommendations
    - This is the "golden discovery feature" for agent ecosystem
    """
    agent_gaps = []

    for subgoal in plan.subgoals:
        # Extract capability keywords from subgoal description
        keywords = extract_capability_keywords(subgoal.description)

        # Find best matching agent
        best_match, score = find_best_agent_match(keywords, agents)

        if score >= 0.5:
            # Good match found
            subgoal.recommended_agent = f"@{best_match.id}"
            subgoal.agent_exists = True
        else:
            # Gap detected - no suitable agent exists
            gap = AgentGap(
                subgoal_id=subgoal.id,
                subgoal_title=subgoal.title,
                recommended_agent=infer_agent_name(keywords),
                agent_exists=False,
                reason=f"No agent found with required capabilities: {keywords}",
                suggested_capabilities=keywords,
                fallback=suggest_fallback_agent(keywords, agents)
            )
            agent_gaps.append(gap)

            # Mark in subgoal
            subgoal.recommended_agent = gap.recommended_agent
            subgoal.agent_exists = False

    return plan, agent_gaps
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

**Plan Schema** (with subgoals and agent gaps):
```json
{
  "plan_id": "0001-oauth-authentication",
  "goal": "Implement OAuth2 authentication",
  "complexity": "complex",
  "generated_at": "2025-12-31T23:59:59Z",
  "context_sources": ["indexed_memory", "src/auth.py"],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Research and Decision",
      "description": "Evaluate OAuth2 providers and make architectural decisions",
      "recommended_agent": "@business-analyst",
      "agent_exists": true,
      "tasks": [
        {
          "id": "1.1",
          "description": "Research OAuth2 providers (Auth0, Okta, Custom)",
          "expected_output": "Comparison table with recommendations"
        },
        {
          "id": "1.2",
          "description": "Evaluate security implications",
          "expected_output": "Security assessment document"
        }
      ]
    },
    {
      "id": "sg-2",
      "title": "Database Design",
      "description": "Design and implement user model with OAuth fields",
      "recommended_agent": "@full-stack-dev",
      "agent_exists": true,
      "dependencies": ["sg-1"],
      "tasks": [
        {
          "id": "2.1",
          "description": "Design user model schema with OAuth fields",
          "expected_output": "Database migration with oauth_provider, oauth_id, tokens"
        },
        {
          "id": "2.2",
          "description": "Implement user model with OAuth methods",
          "expected_output": "User model code with OAuth integration"
        }
      ]
    }
  ],
  "agent_gaps": [
    {
      "subgoal_id": "sg-3",
      "subgoal_title": "API Documentation",
      "recommended_agent": "@technical-writer",
      "agent_exists": false,
      "reason": "No agent found with technical writing capabilities",
      "suggested_capabilities": ["technical-writing", "api-documentation", "user-guides"],
      "fallback": "Use @full-stack-dev or @business-analyst with documentation focus"
    }
  ],
  "validation": {
    "all_agents_exist": false,
    "missing_agent_count": 1,
    "total_subgoals": 3,
    "warnings": ["Consider creating technical-writer agent for documentation tasks"]
  }
}
```

**Markdown Output Format** (with subgoals):
```markdown
# Execution Plan: Implement OAuth2 authentication

**Plan ID**: 0001-oauth-authentication
**Generated**: 2025-12-31 23:59:59
**Complexity**: complex
**Context**: 5 code files from indexed memory

---

## Subgoal 1: Research and Decision
**Recommended Agent**: @business-analyst ✓

Research OAuth2 providers and make architectural decisions.

### Tasks:
1. **Task 1.1**: Research OAuth2 providers (Auth0, Okta, Custom)
   - Expected Output: Comparison table with recommendations

2. **Task 1.2**: Evaluate security implications
   - Expected Output: Security assessment document

---

## Subgoal 2: Database Design
**Recommended Agent**: @full-stack-dev ✓
**Dependencies**: Subgoal 1

Design and implement user model with OAuth fields.

### Tasks:
1. **Task 2.1**: Design user model schema with OAuth fields
   - Expected Output: Database migration with oauth_provider, oauth_id, tokens

2. **Task 2.2**: Implement user model with OAuth methods
   - Expected Output: User model code with OAuth integration

---

## Subgoal 3: API Documentation
**Recommended Agent**: @technical-writer ⚠️ (NOT FOUND)
**Dependencies**: Subgoal 2

Document OAuth2 API endpoints and integration guide.

### Tasks:
1. **Task 3.1**: Write API endpoint documentation
   - Expected Output: OpenAPI spec for OAuth endpoints

2. **Task 3.2**: Create integration guide for developers
   - Expected Output: Step-by-step OAuth integration guide

**⚠️ Agent Gap Detected**:
- No agent found with technical writing capabilities
- Suggested capabilities: technical-writing, api-documentation, user-guides
- Fallback: Use @business-analyst with documentation focus
- Consider creating a technical-writer agent for future documentation tasks

---

## Agent Gaps Summary

1 missing agent type detected:
- **@technical-writer**: Required for Subgoal 3 (API Documentation)

**Next Steps**:
1. Review plan for accuracy
2. Create missing @technical-writer agent (or use fallback)
3. Execute subgoals sequentially using specialized agents
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

### 9.1 Explicitly NOT in MVP (Phase 1)

This MVP focuses on **planning and agent gap discovery** only. Execution is intentionally deferred.

| Feature | Why Not Now | When |
|---------|-------------|------|
| **Plan Execution** | Need to validate planning value first | Phase 2 |
| **Streaming Progress** | Requires subprocess orchestration | Phase 2 |
| **Pause/Resume** | Requires state management | Phase 2 |
| **Parallel Execution** | Requires complex coordination | Phase 2 |
| **CrewAI Adapters** | Requires CrewAI-specific agent format | Future (if needed) |
| **80+ Tools Library** | Focus on discovery, not tooling | Future |
| **Agent Versioning** | Adds complexity, defer | Future |
| **Multi-Repo Discovery** | Single-machine focus for MVP | Future |
| **Agent Marketplace** | Too early, need adoption first | Future |
| **GUI for Planning** | CLI-first approach | Future |

### 9.2 Phase 2: Execution (Future Work)

**Vision**: `aur execute-plan` command that delegates to specialized agents

**Key Features**:
- Read plan JSON from `~/.aurora/plans/` directory
- Execute subgoals sequentially (respecting dependencies)
- Spawn specialized agents in subprocesses based on recommendations
- Track state in JSON (current subgoal, completed tasks)
- Stream progress updates to coordinator
- Handle agent gaps (prompt user or use fallback)

**Implementation Approach**:
```python
# Phase 2 - NOT in current PRD scope
def execute_plan(plan_path: Path):
    """
    Execute a generated plan by delegating to specialized agents.

    For each subgoal:
    1. Check if recommended agent exists
    2. If gap: prompt user for fallback or skip
    3. Spawn agent subprocess with subgoal context
    4. Collect results and update state
    5. Move to next subgoal
    """
    plan = load_plan(plan_path)

    for subgoal in plan.subgoals:
        if not subgoal.agent_exists:
            # Handle gap: prompt or use fallback
            agent = prompt_for_fallback(subgoal)
        else:
            agent = get_agent(subgoal.recommended_agent)

        # Spawn agent subprocess
        result = spawn_agent_for_subgoal(agent, subgoal)

        # Update state
        update_plan_state(plan_path, subgoal.id, "completed")
```

**Why Deferred**:
- Subprocess orchestration adds significant complexity
- Need to validate that planning output is valuable first
- State management requires careful design
- Want user feedback on plan structure before execution
- Streaming and pause/resume need robust error handling

**Name Change**: `process-task-list` → `execute-plan` (better reflects functionality)

### 9.3 Technical Constraints (Accepted)

- **No agent sandboxing**: Discovery only, trust local files
- **No distributed manifest**: Single-machine manifest cache
- **No real-time refresh**: Interval-based or manual refresh
- **No plan execution in MVP**: Generate plans only, validate value first

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

## APPENDIX C: SAMPLE PLAN OUTPUT (MARKDOWN - SIMPLE)

```markdown
# Execution Plan: Add Logging to Auth Module

**Plan ID**: 0002-add-auth-logging
**Generated**: 2025-12-31 23:59:59
**Complexity**: simple
**Context**: 2 code files (src/auth.py, src/utils.py)

---

## Subgoal 1: Implement Logging
**Recommended Agent**: @full-stack-dev ✓

Add structured logging to authentication module.

### Tasks:
1. **Task 1.1**: Add logging imports and configure logger
   - Expected Output: Logger configured with appropriate level and format

2. **Task 1.2**: Add log statements for authentication events
   - Expected Output: Login attempts, failures, and successes logged

3. **Task 1.3**: Add log statements for token operations
   - Expected Output: Token generation and validation logged

---

## Validation

✓ All agents exist in registry
✓ No circular dependencies
✓ Plan is executable

---

**Next Steps**:
1. Review plan for accuracy
2. Execute using specialized agent: `aur execute-plan 0002-add-auth-logging` (Phase 2 feature)
```

---

## APPENDIX D: COMPLETE PLAN EXAMPLE (JSON - WITH AGENT GAPS)

**File**: `~/.aurora/plans/0001-oauth-authentication.json`

This example demonstrates the full plan structure including subgoals, tasks, agent recommendations, and **agent gap detection** (the golden discovery feature).

```json
{
  "plan_id": "0001-oauth-authentication",
  "goal": "Implement OAuth2 authentication with Auth0",
  "complexity": "complex",
  "generated_at": "2025-12-31T23:59:59Z",
  "context_sources": [
    "src/auth.py",
    "src/models/user.py",
    "src/api/routes.py",
    "docs/architecture.md",
    "tests/test_auth.py"
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Research and Architecture",
      "description": "Research OAuth2 providers and design authentication architecture",
      "recommended_agent": "@business-analyst",
      "agent_exists": true,
      "dependencies": [],
      "tasks": [
        {
          "id": "1.1",
          "description": "Research OAuth2 providers (Auth0, Okta, Custom)",
          "expected_output": "Comparison table with Auth0 recommendation"
        },
        {
          "id": "1.2",
          "description": "Design authentication flow diagram",
          "expected_output": "Sequence diagram showing OAuth2 flow"
        },
        {
          "id": "1.3",
          "description": "Evaluate security implications and compliance",
          "expected_output": "Security assessment with GDPR/SOC2 considerations"
        }
      ]
    },
    {
      "id": "sg-2",
      "title": "System Architecture Design",
      "description": "Design technical architecture for OAuth2 integration",
      "recommended_agent": "@holistic-architect",
      "agent_exists": true,
      "dependencies": ["sg-1"],
      "tasks": [
        {
          "id": "2.1",
          "description": "Design database schema with OAuth fields",
          "expected_output": "Migration file with oauth_provider, oauth_id, access_token, refresh_token, expires_at"
        },
        {
          "id": "2.2",
          "description": "Design API endpoints for OAuth flow",
          "expected_output": "OpenAPI spec for /auth/login, /auth/callback, /auth/refresh, /auth/logout"
        },
        {
          "id": "2.3",
          "description": "Design error handling and edge cases",
          "expected_output": "Error taxonomy with handling strategies"
        }
      ]
    },
    {
      "id": "sg-3",
      "title": "Backend Implementation",
      "description": "Implement OAuth2 authentication backend",
      "recommended_agent": "@full-stack-dev",
      "agent_exists": true,
      "dependencies": ["sg-2"],
      "tasks": [
        {
          "id": "3.1",
          "description": "Implement user model with OAuth methods",
          "expected_output": "User model with get_oauth_token(), refresh_token(), revoke_token()"
        },
        {
          "id": "3.2",
          "description": "Implement Auth0 SDK integration",
          "expected_output": "Auth0 client wrapper with error handling"
        },
        {
          "id": "3.3",
          "description": "Implement authentication middleware",
          "expected_output": "Middleware that validates OAuth tokens on protected routes"
        },
        {
          "id": "3.4",
          "description": "Implement token refresh background job",
          "expected_output": "Cron job that refreshes expiring tokens"
        }
      ]
    },
    {
      "id": "sg-4",
      "title": "Quality Assurance",
      "description": "Comprehensive testing and quality validation",
      "recommended_agent": "@qa-test-architect",
      "agent_exists": true,
      "dependencies": ["sg-3"],
      "tasks": [
        {
          "id": "4.1",
          "description": "Design test strategy for OAuth flow",
          "expected_output": "Test plan covering unit, integration, e2e, security tests"
        },
        {
          "id": "4.2",
          "description": "Write integration tests for OAuth endpoints",
          "expected_output": "Passing tests for login, callback, refresh, logout flows"
        },
        {
          "id": "4.3",
          "description": "Write security tests for token handling",
          "expected_output": "Tests for token expiration, revocation, CSRF protection"
        },
        {
          "id": "4.4",
          "description": "Conduct code review and quality gate",
          "expected_output": "PASS/CONCERNS/FAIL decision with improvement recommendations"
        }
      ]
    }
  ],
  "agent_gaps": [],
  "validation": {
    "all_agents_exist": true,
    "missing_agent_count": 0,
    "total_subgoals": 4,
    "warnings": []
  },
  "metadata": {
    "estimated_time_hours": "8-12",
    "complexity_factors": [
      "External service integration (Auth0)",
      "Security-critical feature",
      "Database schema changes",
      "Multiple API endpoints"
    ],
    "risks": [
      "Auth0 API rate limits",
      "Token storage security",
      "Migration complexity"
    ]
  }
}
```

**Example with Agent Gap** (documentation subgoal removed from above, shown here):

```json
{
  "subgoals": [
    {
      "id": "sg-5",
      "title": "Documentation and Onboarding",
      "description": "Create comprehensive documentation for OAuth2 integration",
      "recommended_agent": "@technical-writer",
      "agent_exists": false,
      "dependencies": ["sg-4"],
      "tasks": [
        {
          "id": "5.1",
          "description": "Write API documentation for OAuth endpoints",
          "expected_output": "Complete OpenAPI spec with examples"
        },
        {
          "id": "5.2",
          "description": "Create developer integration guide",
          "expected_output": "Step-by-step guide with code snippets"
        },
        {
          "id": "5.3",
          "description": "Create troubleshooting guide",
          "expected_output": "Common issues and solutions document"
        }
      ]
    }
  ],
  "agent_gaps": [
    {
      "subgoal_id": "sg-5",
      "subgoal_title": "Documentation and Onboarding",
      "recommended_agent": "@technical-writer",
      "agent_exists": false,
      "reason": "No agent found with technical writing and API documentation capabilities",
      "suggested_capabilities": [
        "technical-writing",
        "api-documentation",
        "developer-guides",
        "troubleshooting-docs"
      ],
      "fallback": "Use @business-analyst with documentation focus, or @full-stack-dev for technical accuracy",
      "impact": "Medium - Documentation quality may be lower without specialized writer",
      "recommendation": "Consider creating @technical-writer agent for future documentation tasks"
    }
  ],
  "validation": {
    "all_agents_exist": false,
    "missing_agent_count": 1,
    "total_subgoals": 5,
    "warnings": [
      "Agent gap detected for Subgoal 5: @technical-writer not found",
      "Consider creating technical-writer agent before execution"
    ]
  }
}
```

**Key Features Demonstrated**:
1. ✅ **Hierarchical structure**: Subgoals contain multiple tasks
2. ✅ **Agent recommendations per subgoal**: Not per task (1 subgoal = 1 agent)
3. ✅ **Agent gap detection**: Identifies missing @technical-writer
4. ✅ **Suggested capabilities**: Shows what the missing agent should have
5. ✅ **Fallback recommendations**: Suggests alternatives
6. ✅ **Context tracking**: Shows which files informed the plan
7. ✅ **Dependencies**: Sequential subgoal execution

---

## DOCUMENT HISTORY

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-31 | Initial PRD for Agent Discovery and Planning CLI | Product Team |
| 1.1 | 2026-01-01 | Updated with subgoals structure, agent gaps, Phase 2 vision | Product Team |

---

**END OF PRD 0016: Aurora Agent Discovery and Planning CLI**
