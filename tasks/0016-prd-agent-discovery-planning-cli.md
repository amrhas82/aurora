# PRD 0016: Aurora Agent Discovery & Memory Infrastructure
## Product Requirements Document

**Version**: 2.0
**Date**: January 2, 2026
**Status**: Ready for Implementation
**Phase**: Sprint 3 - Infrastructure Foundations
**Product**: AURORA CLI
**Dependencies**: Existing AgentRegistry (aurora_soar), Memory Commands (aur query)

---

## DOCUMENT PURPOSE

This PRD defines **Aurora Agent Discovery & Memory Infrastructure** - foundational infrastructure that provides agent manifest generation and shared memory retrieval APIs for the Aurora ecosystem.

**Success Criteria**: This phase is complete when developers can discover agents in <500ms, memory retrieval is refactored into reusable API, and both systems are fully tested with <2s memory access latency.

**Related Documents**:
- Previous Phase: `/tasks/0015-prd-bm25-trihybrid-memory-search.md` (Search foundations)
- Architecture: `packages/soar/src/aurora_soar/agent_registry.py` (Existing agent system)
- CLI Guide: `docs/cli/CLI_USAGE_GUIDE.md` (CLI patterns)

---

## TABLE OF CONTENTS

1. [Out of Scope](#out-of-scope)
2. [Executive Summary](#1-executive-summary)
3. [Goals & Success Metrics](#2-goals--success-metrics)
4. [User Stories](#3-user-stories)
5. [Functional Requirements](#4-functional-requirements)
6. [Architecture & Design](#5-architecture--design)
7. [Quality Gates & Acceptance Criteria](#6-quality-gates--acceptance-criteria)
8. [Testing Strategy](#7-testing-strategy)
9. [Dependencies](#8-dependencies)
10. [Non-Goals](#9-non-goals)
11. [Technical Considerations](#10-technical-considerations)
12. [Delivery Verification Checklist](#11-delivery-verification-checklist)

---

## OUT OF SCOPE

**⚠️ CRITICAL FOR TASK GENERATION**: Planning commands are **NOT part of this PRD's implementation scope**.

### What is Out of Scope?

**Planning System (moved to PRD 0017)**:
- ❌ `aur plan` command (any form)
- ❌ Plan generation from natural language goals
- ❌ SOAR integration for goal decomposition
- ❌ Plan file creation (plan.md, prd.md, tasks.md, agents.json)
- ❌ Plan lifecycle management (create, list, show, archive)
- ❌ Agent assignment to tasks
- ❌ `/aur:plan` slash command

### Why is Planning Out of Scope?

1. **Moved to PRD 0017**: All planning features are now in `/tasks/0017-prd-aurora-planning-system.md`
2. **Infrastructure first**: This PRD provides the foundations (agent discovery + memory API)
3. **PRD 0017 depends on this**: Advanced planning needs agent manifest and memory APIs first
4. **Single responsibility**: This PRD = infrastructure only

### What THIS PRD Provides (Infrastructure)

**Agent Discovery**:
- ✅ Agent manifest generation (`~/.aurora/cache/agent_manifest.json`)
- ✅ Agent discovery commands: `aur agents list/search/show/refresh`
- ✅ `AgentInfo` model and `AgentManifest` schema
- ✅ Multi-source agent scanning (claude, ampcode, droid, opencode)

**Shared Memory Infrastructure**:
- ✅ Refactored `MemoryManager` class (extracted from `aur query`)
- ✅ Reusable memory retrieval API for SOAR, planning, query commands
- ✅ Support for `--context` file overrides
- ✅ Context loading with <2s latency

### Task Generation Instructions

**When generating tasks from this PRD**:
- ✅ **DO** generate tasks for agent discovery (manifest, search, list, show)
- ✅ **DO** generate tasks for memory refactoring (extract MemoryManager)
- ❌ **DO NOT** generate any planning tasks (`aur plan`, plan generation, etc.)
- ❌ **DO NOT** include SOAR integration for planning (only for future use by PRD 0017)
- ❌ **DO NOT** implement plan file creation or management

**Planning Task Reference**: For planning implementation tasks, generate them from `/tasks/0017-prd-aurora-planning-system.md` instead.

---

## 1. EXECUTIVE SUMMARY

### 1.1 What is Aurora Agent Discovery & Memory Infrastructure?

A single-sprint infrastructure implementation (4-5 hours) that provides:

**Agent Discovery Infrastructure**:
- Discover agents from multiple configuration sources
- Search agents by keyword, category, or capability
- Display detailed agent information
- Cache agent metadata for fast access (<500ms)

**Shared Memory Infrastructure**:
- Refactor memory retrieval into reusable `MemoryManager` class
- Extract from `aur query` into shared module
- Provide clean API for SOAR orchestrator and planning commands
- Support `--context` file overrides for custom contexts

### 1.2 Key Components

1. **Agent Discovery System** (`aurora_cli.agents`):
   - Multi-source agent manifest generation (`~/.claude/agents/`, `~/.config/ampcode/agents/`, etc.)
   - Frontmatter metadata extraction from `.md` agent files
   - Fast keyword search and category filtering (<500ms)
   - Auto-refresh with configurable intervals
   - CLI commands: `aur agents list/search/show/refresh`

2. **Shared Memory Infrastructure** (`aurora_cli.memory`):
   - Refactored `MemoryManager` class extracted from `aur query`
   - Reusable API for memory retrieval (SOAR, planning, query commands)
   - Context strategy: `--context` file overrides OR indexed memory
   - Clean separation: memory logic vs command logic
   - Performance: <2s context loading for typical queries

3. **Configuration System**:
   - Agent discovery settings in `~/.aurora/config.json`
   - Memory cache configuration
   - Auto-refresh intervals
   - Error handling and graceful degradation

### 1.3 Why This Matters

**Current Pain Points**:
- No centralized agent discovery across different CLI tools (Claude, AmpCode, Droid, OpenCode)
- Memory retrieval logic embedded in `aur query` command (not reusable)
- SOAR orchestrator and future planning features can't access memory retrieval
- No consistent API for context loading

**After This Feature** (Infrastructure Foundations):
- **Agent Discovery**: Developers discover agents in <500ms across all sources
- **Shared Memory API**: SOAR, planning, and query commands share same memory retrieval logic
- **Reusability**: `MemoryManager` class provides clean API for all features
- **Future Ready**: PRD 0017 planning system can build on these foundations

---

## 2. GOALS & SUCCESS METRICS

### 2.1 Primary Goals

1. **Enable fast agent discovery** across multiple configuration sources (<500ms)
2. **Refactor memory retrieval** into reusable `MemoryManager` class
3. **Provide shared memory API** for SOAR, planning, and query commands
4. **Support context overrides** with `--context` file parameter
5. **Maintain backwards compatibility** with existing `aur query` command
6. **Prepare foundations** for PRD 0017 planning system

### 2.2 Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Agent Discovery Latency** | <500ms | Benchmark manifest loading |
| **Memory Retrieval Latency** | <2s for 20 chunks | Performance benchmarks |
| **Manifest Accuracy** | 100% valid agents | Schema validation tests |
| **API Reusability** | Used by 3+ features | Integration verification (query, SOAR, planning) |
| **Context Override** | <2s custom files | Benchmark --context loading |
| **Test Coverage** | ≥85% | pytest-cov |
| **Type Safety** | 0 mypy errors (strict) | mypy |
| **Backward Compatibility** | `aur query` unchanged | Regression tests |

### 2.3 Sprint Completion Criteria

Sprint is **COMPLETE** when:
- ✅ Agent discovery commands implemented: `list`, `search`, `show`, `refresh`
- ✅ Agent manifest generation working (<500ms from 4 sources)
- ✅ `MemoryManager` class extracted from `aur query` into shared module
- ✅ Memory API provides clean interface for context loading
- ✅ `--context` file override parameter functional
- ✅ `aur query` command still works (backward compatibility)
- ✅ Configuration system supports agent discovery settings
- ✅ All quality gates passed (≥85% coverage, 0 mypy errors)
- ✅ Shell tests pass (agent discovery + memory retrieval)
- ✅ Documentation complete with API usage examples

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

### 3.2 Developer Using Shared Memory Infrastructure

**As a** developer building features that need memory retrieval,
**I want** a reusable `MemoryManager` API that handles context loading,
**So that** I don't reimplement memory retrieval in every command.

**Acceptance Criteria**:
- `MemoryManager` class available in `aurora_cli.memory` module
- Clean API: `manager.retrieve(query, limit, mode='hybrid')`
- Supports indexed memory retrieval (<2s for 20 chunks)
- Supports `--context` file overrides (<2s for 10 files)
- `aur query` command refactored to use `MemoryManager` (backward compatible)
- No behavior changes to existing `aur query` command

**Testing Requirements**:
- Unit tests for `MemoryManager` class methods
- Integration test verifying `aur query` still works
- Regression tests for `aur query` output format
- Performance benchmarks for memory retrieval

---

### 3.3 SOAR Orchestrator Using Memory for Context

**As a** SOAR orchestrator developer,
**I want** to access memory retrieval for goal decomposition context,
**So that** I can provide relevant codebase chunks when planning subgoals.

**Acceptance Criteria**:
- SOAR can import and use `MemoryManager` class
- `manager.retrieve(goal, limit=20)` returns relevant code chunks
- Memory retrieval completes in <2s
- Context chunks include file paths and content
- No tight coupling to CLI commands

**Testing Requirements**:
- Unit test SOAR calling `MemoryManager.retrieve()`
- Integration test verifying SOAR + memory flow
- Mock tests for memory retrieval errors

---

### 3.4 Future Planning System Using Memory API

**As a** planning system developer (PRD 0017),
**I want** the memory infrastructure ready before I start implementation,
**So that** I can build on proven foundations instead of reinventing.

**Acceptance Criteria**:
- `MemoryManager` documented with usage examples
- API stable and tested (≥85% coverage)
- Performance verified (<2s retrieval)
- `--context` override pattern established
- Agent manifest available for agent recommendations

**Testing Requirements**:
- API documentation with code examples
- Load testing with large codebases
- Verify agent manifest + memory work together

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
   - `~/.config/droid/agent/*.md`  # Note: droid uses 'agent' (singular)
   - `~/.config/opencode/agent/*.md`  # Note: opencode uses 'agent' (singular)

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

3. Validate required fields: `id`, `role`, `goal` (see Pydantic schema below)
4. Skip files with invalid/missing frontmatter (log warning with file path)
5. Write manifest to `~/.aurora/cache/agent_manifest.json` (atomic write)

**Error Handling Pattern** (OpenSpec lesson - graceful degradation):
```python
def parse_agent_file(file_path: Path) -> AgentInfo | None:
    """
    Parse agent file with OpenSpec-style graceful degradation.
    Returns None for malformed files, logs detailed warnings.
    NEVER crashes - always returns None on error.
    """
    try:
        with open(file_path) as f:
            post = frontmatter.load(f)

        if not post.metadata:
            logger.warning(
                f"No frontmatter in {file_path} - skipping",
                extra={"file": str(file_path), "error_type": "missing_frontmatter"}
            )
            return None

        # Pydantic validation with explicit error messages
        agent = AgentInfo(**post.metadata, source_file=str(file_path))
        return agent

    except yaml.YAMLError as e:
        logger.warning(f"Invalid YAML in {file_path}: {e} - skipping")
        return None
    except ValidationError as e:
        error_fields = [err['loc'][0] for err in e.errors()]
        logger.warning(f"Validation failed for {file_path}: {', '.join(error_fields)} - skipping")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in {file_path}: {e} - skipping", exc_info=True)
        return None
```

**Benefits**: Never crashes, detailed logs, users can fix and re-run `aur agents refresh`.

**Manifest Schema**:
```json
{
  "version": "1.0",
  "generated_at": "2025-12-31T23:59:59Z",
  "sources": [
    "~/.claude/agents",
    "~/.config/ampcode/agents",
    "~/.config/droid/agent",
    "~/.config/opencode/agent"
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

**Pydantic Schema (OpenSpec-inspired validation)**:
```python
class AgentInfo(BaseModel):
    """
    Agent metadata from frontmatter.
    Validation follows OpenSpec patterns: explicit messages, field constraints.
    """
    # Required fields
    id: str = Field(
        min_length=1,
        max_length=50,
        pattern=r'^[a-z0-9-]+$',
        description="Kebab-case agent identifier"
    )
    role: str = Field(
        min_length=5,
        max_length=100,
        description="Human-readable agent role"
    )
    goal: str = Field(
        min_length=20,
        max_length=500,
        description="Primary agent goal/purpose"
    )

    # Optional fields with defaults
    category: str = Field(
        default="general",
        pattern=r'^(eng|qa|product|general)$',
        description="Agent category for filtering"
    )
    skills: list[str] = Field(
        default_factory=list,
        max_length=20,  # max 20 skills
        description="Agent capabilities"
    )
    examples: list[str] = Field(default_factory=list)
    when_to_use: str = Field(default="", max_length=300)
    dependencies: list[str] = Field(default_factory=list)
    source_file: str = Field(...)

    @field_validator('id')
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError(
                f"Agent ID must be kebab-case (lowercase, numbers, hyphens only). Got: {v}"
            )
        return v
```

**Validation Error Messages** (OpenSpec lesson):
```python
VALIDATION_MESSAGES = {
    "AGENT_ID_EMPTY": "Agent 'id' field is required and cannot be empty",
    "AGENT_ID_INVALID_FORMAT": "Agent 'id' must be kebab-case (e.g., 'qa-test-architect')",
    "AGENT_ROLE_TOO_SHORT": "Agent 'role' must be at least 5 characters",
    "AGENT_GOAL_TOO_SHORT": "Agent 'goal' must be at least 20 characters (describe purpose)",
    "AGENT_CATEGORY_INVALID": "Agent 'category' must be one of: eng, qa, product, general",
    "AGENT_TOO_MANY_SKILLS": "Agent can have maximum 20 skills",
    "FRONTMATTER_MISSING": "File {file} has no YAML frontmatter (---...---)",
    "FRONTMATTER_INVALID_YAML": "File {file} has invalid YAML: {error}",
}
```

**Requirements**:
- Multi-source discovery (4 sources)
- Frontmatter parsing with `python-frontmatter` library
- **Pydantic validation** with explicit error messages
- **Graceful degradation**: Skip malformed files, log warnings with file path
- Atomic write (temp file + rename)
- Latency target: <2s for 50 agents
- **Track malformed files** in manifest stats

---


### 4.2 Shared Memory Infrastructure

**Package**: `packages/cli/src/aurora_cli/memory.py`

**MUST** refactor memory retrieval from `aur query` into reusable infrastructure.

#### 4.2.1 MemoryManager Class

```python
class MemoryManager:
    """
    Shared memory retrieval infrastructure for Aurora ecosystem.

    Used by:
    - aur query command (existing)
    - SOAR orchestrator (goal decomposition context)
    - Planning system (PRD 0017)
    - Future features requiring codebase context
    """

    def __init__(self, store: Store, config: Config):
        self.store = store
        self.config = config

    def has_indexed_memory(self) -> bool:
        """Check if indexed memory available."""
        return self.store.chunk_count() > 0

    def retrieve(
        self,
        query: str,
        limit: int = 20,
        mode: str = 'hybrid'
    ) -> list[CodeChunk]:
        """
        Retrieve context from indexed memory.

        Args:
            query: Search query or goal description
            limit: Maximum chunks to return
            mode: 'hybrid' | 'semantic' | 'bm25'

        Returns:
            List of CodeChunk objects with file paths and content

        Performance: <2s for limit=20
        """
        pass

    def load_context_files(self, paths: list[Path]) -> list[CodeChunk]:
        """
        Load context from custom files (--context override).

        Args:
            paths: List of file paths to load

        Returns:
            List of CodeChunk objects

        Performance: <2s for 10 files
        """
        pass

    def format_for_prompt(self, chunks: list[CodeChunk]) -> str:
        """
        Format context chunks for LLM prompt.

        Returns:
            Formatted string ready for LLM consumption
        """
        pass
```

#### 4.2.2 Context Strategy

**Priority** (in order):
1. If `--context` provided: Use ONLY those files (no indexed memory)
2. Else if indexed memory exists: Use indexed memory retrieval
3. Else: Error - no context available

**Example Usage** (from `aur query`):
```python
# Refactored aur query command
def query_command(query_text: str, context_files: list[Path] = None):
    manager = MemoryManager(store, config)

    if context_files:
        # Override with custom context
        chunks = manager.load_context_files(context_files)
    elif manager.has_indexed_memory():
        # Use indexed memory
        chunks = manager.retrieve(query_text, limit=20)
    else:
        raise Error("No context available. Run 'aur mem index' first.")

    # Rest of query logic unchanged
    ...
```

#### 4.2.3 Backward Compatibility

**CRITICAL**: `aur query` command MUST NOT change behavior:
- Same CLI arguments
- Same output format
- Same performance characteristics
- Only internal refactoring to use `MemoryManager`

**Testing**:
- Regression tests for all `aur query` scenarios
- Verify output byte-for-byte identical (except timestamps)

#### 4.2.4 Requirements

- ✅ Extract memory logic from `packages/cli/src/aurora_cli/commands/query.py`
- ✅ Create reusable `MemoryManager` class
- ✅ Support both indexed memory and `--context` file overrides
- ✅ Maintain `aur query` backward compatibility
- ✅ Clean API for SOAR and planning system integration
- ✅ Performance: <2s retrieval for 20 chunks
- ✅ Unit tests ≥85% coverage
- ✅ Integration tests verifying SOAR can use the API

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
      "~/.config/droid/agent",
      "~/.config/opencode/agent"
    ],
    "manifest_path": "~/.aurora/cache/agent_manifest.json"
  },
  "memory": {
    "default_retrieval_limit": 20,
    "default_mode": "hybrid",
    "context_loading_timeout_seconds": 5
  }
}
```

**Note**: Planning configuration moved to PRD 0017

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
- Retrieval limit must be positive integer
- Discovery paths must be directories (warn if missing)
- Memory mode must be one of: hybrid, semantic, bm25

---

## 5. ARCHITECTURE & DESIGN

### 5.1 Package Structure

```
packages/
├── cli/
│   ├── src/aurora_cli/
│   │   ├── commands/
│   │   │   ├── agents.py          # NEW: Agent discovery commands
│   │   │   └── query.py           # REFACTOR: Use shared memory module
│   │   ├── memory/
│   │   │   └── retrieval.py       # NEW: Shared memory retrieval
│   │   ├── agent_discovery/       # NEW
│   │   │   ├── scanner.py         # Multi-source agent discovery
│   │   │   ├── parser.py          # Frontmatter extraction
│   │   │   └── manifest.py        # Manifest generation
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
│  │  ├─ Scan ~/.config/droid/agent/*.md                 │   │
│  │  └─ Scan ~/.config/opencode/agent/*.md              │   │
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

---

## 6. QUALITY GATES & ACCEPTANCE CRITERIA

### 6.1 Code Quality Gates

| Gate | Requirement | Tool | Blocker |
|------|-------------|------|---------|
| **Code Coverage** | ≥85% for agent_discovery/, memory/ | pytest-cov | YES |
| **Type Checking** | 0 mypy errors (strict mode) | mypy | YES |
| **Linting** | 0 critical issues | ruff | YES |
| **Security** | 0 high/critical vulnerabilities | bandit | YES |

### 6.2 Performance Gates

| Metric | Target | Measurement | Blocker |
|--------|--------|-------------|---------|
| **Agent Discovery** | <500ms | Benchmark manifest load | YES |
| **Agent Search** | <500ms | Benchmark keyword search | NO (warning) |
| **Memory Retrieval** | <2s for 20 chunks | Benchmark MemoryManager.retrieve() | YES |
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
    create_agent_file("~/.config/droid/agent/scrum-master.md")
    create_agent_file("~/.config/opencode/agent/ux-expert.md")

    # WHEN: Run agent refresh
    result = runner.invoke(cli, ["agents", "refresh"])

    # THEN: All 4 agents in manifest
    manifest = load_manifest()
    assert len(manifest["agents"]) == 4
    assert "qa-test-architect" in agent_ids(manifest)
    assert "full-stack-dev" in agent_ids(manifest)
    assert result.exit_code == 0
```

#### Test Scenario 2: Memory Manager API Integration

```python
def test_memory_manager_retrieve():
    """MemoryManager provides reusable retrieval API."""
    # GIVEN: Indexed memory exists with code chunks
    store.index_directory(".")
    assert store.chunk_count() > 0

    # WHEN: Use MemoryManager API directly
    manager = MemoryManager(store, config)
    chunks = manager.retrieve("authentication", limit=5)

    # THEN: Returns relevant chunks with file paths
    assert len(chunks) <= 5
    for chunk in chunks:
        assert chunk.file_path is not None
        assert chunk.content is not None
```

#### Test Scenario 3: Context Override Replaces Memory

```python
def test_context_override_replaces_memory():
    """--context replaces indexed memory (no merging)."""
    # GIVEN: Indexed memory exists with 100 chunks
    store.index_directory(".")
    assert store.chunk_count() == 100

    # AND: Custom context files
    custom_files = [Path("src/auth.py"), Path("src/utils.py")]

    # WHEN: Load context via MemoryManager
    manager = MemoryManager(store, config)
    chunks = manager.load_context_files(custom_files)

    # THEN: Uses ONLY custom files (not indexed memory)
    file_paths = {c.file_path for c in chunks}
    assert all("auth.py" in str(p) or "utils.py" in str(p) for p in file_paths)
```

#### Test Scenario 4: Backward Compatibility with aur query

```python
def test_aur_query_backward_compatible():
    """aur query behavior unchanged after MemoryManager refactor."""
    # GIVEN: Indexed memory exists
    store.index_directory(".")

    # WHEN: Run aur query command
    result = runner.invoke(cli, ["query", "SOAROrchestrator"])

    # THEN: Same output format as before
    assert result.exit_code == 0
    assert "Retrieved" in result.output or "chunks" in result.output.lower()
```

---

## 7. TESTING STRATEGY

### 7.1 Unit Tests

**Agent Discovery** (`tests/unit/test_agents_*.py`):
- `test_scanner.py`: Multi-source directory scanning
- `test_parser.py`: Frontmatter extraction, validation
- `test_manifest.py`: Manifest generation, de-duplication
- `test_commands_agents.py`: CLI commands (list, search, show, refresh)

**Memory Infrastructure** (`tests/unit/test_memory_*.py`):
- `test_memory_manager.py`: MemoryManager class methods
- `test_memory_retrieval.py`: Indexed memory retrieval
- `test_memory_context_files.py`: --context file loading
- `test_memory_backward_compat.py`: aur query unchanged

**Configuration** (`tests/unit/test_config_*.py`):
- `test_config.py`: Configuration schema, validation
- `test_auto_refresh.py`: Auto-refresh logic

### 7.2 Integration Tests

**MUST test end-to-end workflows**:

1. **Agent Discovery E2E**: Scan 4 sources → Parse frontmatter → Generate manifest → Query agents
2. **Memory Refactoring E2E**: aur query before/after (output identical)
3. **Context Override E2E**: Verify `--context` replaces indexed memory
4. **Auto-Refresh E2E**: Trigger auto-refresh on stale manifest
5. **SOAR Integration E2E**: SOAR calls MemoryManager.retrieve()

### 7.3 Shell Tests (following `tests/shell/test_*.sh` pattern)

**Agent Discovery Shell Tests** (5 tests):

1. **test_34_agent_list.sh**
   - Run `aur agents list`
   - Verify all 4 sources scanned
   - Check output format (categories, agent IDs)
   - **Pass criteria**: <500ms, all agents shown

2. **test_35_agent_search_keyword.sh**
   - Run `aur agents search "code review"`
   - Verify keyword matching works
   - Check relevant agents returned
   - **Pass criteria**: <500ms, qa-test-architect found

3. **test_36_agent_show_details.sh**
   - Run `aur agents show qa-test-architect`
   - Verify full details displayed
   - Check skills, category, description present
   - **Pass criteria**: Complete agent info shown

4. **test_37_agent_refresh.sh**
   - Run `aur agents refresh`
   - Verify manifest regenerated
   - Check timestamp updated
   - **Pass criteria**: <500ms, manifest file updated

5. **test_38_agent_multi_source.sh**
   - Create test agents in all 4 sources (claude, ampcode, droid, opencode)
   - Run `aur agents list`
   - Verify all sources discovered
   - **Pass criteria**: All 4 test agents found

**Memory Infrastructure Shell Tests** (5 tests):

6. **test_39_memory_manager_api.sh**
   - Python script imports MemoryManager
   - Call `manager.retrieve("test", limit=5)`
   - Verify API works outside CLI context
   - **Pass criteria**: API accessible, chunks returned

7. **test_40_aur_query_unchanged.sh**
   - Run `aur query "SOAROrchestrator"` before refactoring (baseline)
   - Run same query after refactoring
   - Compare outputs byte-for-byte (except timestamps)
   - **Pass criteria**: Output identical (backward compatible)

8. **test_41_context_override.sh**
   - Create custom files: test1.py, test2.py
   - Run `aur query "test" --context test1.py test2.py`
   - Verify ONLY custom files used (not indexed memory)
   - **Pass criteria**: Only test1.py, test2.py in results

9. **test_42_memory_performance.sh**
   - Run `aur query "complex query"` with 20 chunk limit
   - Measure execution time
   - **Pass criteria**: <2s for retrieval

10. **test_43_soar_memory_integration.sh**
    - Python script: SOAR calls MemoryManager.retrieve()
    - Verify SOAR can access memory for context
    - Check chunks returned with file paths
    - **Pass criteria**: SOAR successfully retrieves context

**Test Execution**:
```bash
# Run all agent discovery tests
bash tests/shell/test_34_agent_*.sh
bash tests/shell/test_38_agent_multi_source.sh

# Run all memory tests
bash tests/shell/test_39_memory_*.sh
bash tests/shell/test_43_soar_memory_integration.sh
```

### 7.4 Performance Benchmarks

```python
def test_performance_benchmarks(benchmark_fixture):
    """Benchmark agent discovery and memory retrieval."""

    test_cases = [
        ("agent_list", "agents list", 500),
        ("agent_search", "agents search test", 500),
        ("agent_refresh", "agents refresh", 500),
        ("memory_retrieve_10", "query 'test' --limit 10", 1500),
        ("memory_retrieve_20", "query 'test' --limit 20", 2000),
        ("context_override", "query 'test' --context file.py", 2000),
    ]

    for name, command, max_ms in test_cases:
        with benchmark_fixture.measure(name):
            runner.invoke(cli, command.split())

        benchmark_fixture.assert_performance(name, max_ms=max_ms)
```

### 7.5 Acceptance Tests

**MUST match user stories exactly**:

- User Story 3.1: Developer discovering agents
- User Story 3.2: Developer using shared memory infrastructure
- User Story 3.3: SOAR orchestrator using memory for context
- User Story 3.4: Future planning system using memory API

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
| **Store** | aurora_core | Memory index queries |
| **Config** | aurora_core | Configuration system |
| **aur query** | aurora_cli | Refactor to use MemoryManager (internal) |

### 8.2 External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| **pyyaml** | ≥6.0 | Frontmatter parsing |
| **python-frontmatter** | ≥1.0 | Agent metadata extraction |
| **click** | ≥8.0 | CLI framework (existing) |
| **pydantic** | ≥2.0 | Schema validation |

### 8.3 Breaking Changes

**None**. This feature:
- ✅ Adds new commands (`aur agents list/search/show/refresh`)
- ✅ Refactors shared memory logic (internal only, `aur query` unchanged)
- ✅ Does NOT change existing command behavior or outputs

---

## 9. NON-GOALS (OUT OF SCOPE)

### 9.1 Planning System (Moved to PRD 0017)

**⚠️ CRITICAL**: All planning features are OUT OF SCOPE for this PRD.

| Feature | Moved To | Reason |
|---------|----------|--------|
| **`aur plan` command** | PRD 0017 Phase 1 | Planning requires agent + memory infrastructure first |
| **Plan generation** | PRD 0017 Phase 1 | Natural language → structured plans |
| **Plan file creation** | PRD 0017 Phase 1 | 4-file workflow (plan/prd/tasks/agents.json) |
| **SOAR integration for planning** | PRD 0017 Phase 1 | Goal decomposition |
| **Plan lifecycle** | PRD 0017 Phase 1 | create, list, show, archive |
| **Agent assignment** | PRD 0017 Phase 2 | Agent recommendations per subgoal |
| **Plan execution** | PRD 0017 Phase 3 | Agent delegation, progress tracking |
| **Pause/Resume** | PRD 0017 Phase 3 | State persistence |

**See**: `/tasks/0017-prd-aurora-planning-system.md` for complete planning specifications.

### 9.2 Future Enhancements (Not Prioritized)

| Feature | Why Not Now | When |
|---------|-------------|------|
| **CrewAI Adapters** | Non-standard agent format | Future (if needed) |
| **80+ Tools Library** | Focus on infrastructure first | Future |
| **Agent Versioning** | Adds complexity, minimal value | Future |
| **Multi-Repo Discovery** | Single-machine focus for MVP | Future |
| **Agent Marketplace** | Too early, need adoption first | Future |
| **GUI for Agent Discovery** | CLI-first approach | Future |
| **Agent Performance Metrics** | Need baseline usage first | Future |

### 9.3 Technical Constraints (Accepted)

- **No agent sandboxing**: Discovery only, trust local agent files
- **No distributed manifest**: Single-machine manifest cache
- **No real-time refresh**: Interval-based or manual refresh
- **No advanced caching**: Simple file-based manifest cache

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

### 10.2 Manifest Caching Strategy

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
- [ ] Frontmatter parser with validation
- [ ] Manifest generation with multi-source discovery
- [ ] MemoryManager class extracted from `aur query`
- [ ] Shared memory retrieval module with clean API
- [ ] `--context` file override support
- [ ] Configuration schema extended for agents
- [ ] Auto-refresh logic operational
- [ ] Backward compatibility with `aur query` maintained

### 11.2 Testing Complete

- [ ] Unit test coverage ≥85% for new modules
- [ ] All integration tests pass (5 scenarios)
- [ ] All acceptance tests match user stories
- [ ] Performance benchmarks meet targets
- [ ] Edge cases tested (malformed files, missing agents)

### 11.3 Documentation Complete

- [ ] CLI help text for all commands with examples
- [ ] `docs/cli/CLI_USAGE_GUIDE.md` updated with agent discovery commands
- [ ] MemoryManager API documentation with code examples
- [ ] Configuration schema documented
- [ ] Troubleshooting section for common errors
- [ ] Example workflows (agent discovery, memory retrieval)

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
    "/home/user/.config/droid/agent",
    "/home/user/.config/opencode/agent"
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

## DOCUMENT HISTORY

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-31 | Initial PRD for Agent Discovery and Planning CLI | Product Team |
| 1.1 | 2026-01-01 | Updated with subgoals structure, agent gaps, Phase 2 vision | Product Team |
| 2.0 | 2026-01-02 | Refactored: Removed planning content (moved to PRD 0017), focused on infrastructure only | Product Team |

---

**END OF PRD 0016: Aurora Agent Discovery & Memory Infrastructure**
