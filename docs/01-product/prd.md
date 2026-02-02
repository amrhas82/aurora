# Aurora Product Requirements

## Overview

Aurora is a memory-first planning and multi-agent orchestration framework for AI coding assistants.

## Core Features

### 1. Memory System

**Goal**: Intelligent code retrieval with cognitive memory

**Capabilities**:
- Index codebases using tree-sitter parsing
- Store chunks in SQLite with activation metadata
- Hybrid retrieval: BM25 (40%) + ACT-R (30%) + Git signals (30%)
- Optional: Semantic search with embeddings

**Commands**:
- `aur init` - Initialize project
- `aur mem index .` - Index codebase
- `aur mem search "query"` - Search memory

### 2. SOAR Pipeline

**Goal**: Systematic query processing and goal decomposition

**Capabilities**:
- 9-phase orchestration (Assess → Respond)
- Query mode for answering questions
- Goals mode for planning

**Commands**:
- `aur soar "question"` - Process query through pipeline
- `aur goals "objective"` - Decompose into actionable goals

### 3. Agent Orchestration

**Goal**: Multi-tool execution coordination

**Capabilities**:
- Discover agents from multiple sources
- Match capabilities to tasks
- Execute in parallel or sequential mode

**Commands**:
- `aur spawn` - Execute tasks in parallel
- `aur agents list` - List discovered agents

### 4. Planning System

**Goal**: Structured implementation planning

**Capabilities**:
- Generate PRDs from goals
- Create task lists
- Track plan progress

**Commands**:
- `/aur:plan "goal"` - Create implementation plan
- `/aur:implement` - Execute plan tasks

## Non-Functional Requirements

### Performance
- CLI startup: <3s
- Memory search: <500ms
- Incremental indexing: <5s

### Reliability
- Graceful degradation without ML
- Offline operation (no cloud required)
- Atomic database operations

### Usability
- Clear error messages with suggestions
- Progress indicators for long operations
- Verbose mode for debugging

## Package Structure

```
packages/
  core/         - Models, store, config
  context-code/ - Code parsing, retrieval
  context-doc/  - Document parsing
  reasoning/    - LLM clients
  soar/         - 9-phase pipeline
  planning/     - Plan generation
  spawner/      - Parallel execution
  implement/    - Sequential execution
  cli/          - CLI commands
  testing/      - Test utilities
```

## Configuration

Hierarchical resolution (highest to lowest):
1. CLI flags
2. Environment variables
3. Project config (`.aurora/config.json`)
4. Global config (`~/.aurora/config.json`)
5. Built-in defaults
