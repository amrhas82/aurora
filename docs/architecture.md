# Aurora Architecture

## System Overview

Aurora is a memory-first planning and multi-agent orchestration framework that combines:
- ACT-R cognitive memory model for intelligent code retrieval
- SOAR 9-phase pipeline for systematic goal decomposition
- CLI-agnostic agent orchestration for multi-tool execution

## Package Architecture

```
aurora-actr (monorepo)
  packages/
    core/         aurora_core      Pydantic models, SQLite store, config
    context-code/ aurora_context_code  Tree-sitter parsing, BM25, embeddings
    reasoning/    aurora_reasoning LLM clients (Anthropic, OpenAI, Ollama)
    soar/         aurora_soar      9-phase orchestration pipeline
    planning/     aurora_planning  OpenSpec-inspired plan generation
    spawner/      aurora_spawner   Parallel task execution
    implement/    aurora_implement Sequential task execution
    cli/          aurora_cli       Click-based CLI (aur command)
    testing/      aurora_testing   Test utilities and fixtures
```

## Data Flow

```
User Query/Goal
      |
      v
+------------------+
|   aurora_cli     |  Entry point: aur command
+------------------+
      |
      v
+------------------+
| aurora_context   |  Index codebase, search memory
|     _code        |  BM25 + ACT-R activation + optional embeddings
+------------------+
      |
      v
+------------------+
|   aurora_soar    |  9-phase SOAR pipeline
+------------------+  Assess -> Retrieve -> Decompose -> Verify -> Route
      |              -> Collect -> Synthesize -> Record -> Respond
      v
+------------------+
| aurora_planning  |  Generate PRD, tasks.md, goals.json
+------------------+
      |
      v
+------------------+
| aurora_spawner   |  Execute tasks via CLI tools
| aurora_implement |  (parallel or sequential)
+------------------+
```

## Memory System (ACT-R)

### Chunk Types
- `code` - Functions, classes, methods (tree-sitter parsed)
- `kb` - Markdown documentation chunks
- `soar` - Cached reasoning patterns

### Activation Scoring
```
Activation = Base_Level + Spreading_Activation + Noise

Base_Level = ln(sum(t_j^-d)) where t_j = time since access j
             d = decay rate (default 0.5)

Spreading_Activation = sum(W_j * S_ji)
                       W_j = source activation weight
                       S_ji = association strength
```

### Hybrid Retrieval (Default)
| Component | Weight | Purpose |
|-----------|--------|---------|
| BM25 | 40% | Keyword matching, identifier search |
| ACT-R Activation | 30% | Usage frequency + recency |
| Git Signals | 30% | Modification patterns |

### With ML Option
| Component | Weight | Purpose |
|-----------|--------|---------|
| BM25 | 30% | Keyword matching |
| Semantic | 40% | Embedding similarity |
| ACT-R | 30% | Cognitive activation |

## SOAR Pipeline (9 Phases)

### Query Mode (aur soar)
All 9 phases execute to answer questions about code.

### Goals Mode (aur goals)
Phases 1-5, 8-9 (skips execution/synthesis) for planning.

### Phase Details

| Phase | Purpose | Output |
|-------|---------|--------|
| 1. Assess | Complexity classification | simple/moderate/complex |
| 2. Retrieve | Memory search | Relevant chunks |
| 3. Decompose | Break into subgoals | Subgoal list |
| 4. Verify | Validate decomposition | Confidence scores |
| 5. Route | Match agents | Agent assignments |
| 6. Collect | Execute agents | Agent outputs |
| 7. Synthesize | Combine results | Unified response |
| 8. Record | Cache patterns | Stored in memory |
| 9. Respond | Format output | Answer/goals.json |

## Agent System

### Discovery Sources
- `~/.claude/agents/` - Claude Code agents
- `~/.config/ampcode/agents/` - AMP Code agents
- `.aurora/agents/` - Project-specific agents

### Agent Matching
1. Keyword-based capability matching (fast)
2. LLM fallback for complex classification
3. Confidence scores (0.0-1.0)
4. Gap detection for missing capabilities

### Execution Modes
- Sequential (`aur implement`, `/implement`) - Task by task with review
- Parallel (`aur spawn`) - Concurrent execution (max 5 default)

## Storage

### SQLite Database (.aurora/memory.db)
```sql
chunks: id, type, content, file_path, start_line, end_line,
        metadata, embedding, activation, last_access, access_count

associations: source_id, target_id, strength, type
```

### Plan Directory (.aurora/plans/)
```
.aurora/plans/
  0001-feature-name/
    goals.json    Structured subgoals with agents
    plan.md       Plan overview
    prd.md        Product requirements
    tasks.md      Executable task list
    agents.json   Agent assignments
    specs/        Detailed specifications
```

## Configuration Resolution

```
CLI flags (--tool, --model)
    |
    v
Environment variables (AURORA_GOALS_TOOL)
    |
    v
Project config (.aurora/config.json)
    |
    v
Global config (~/.aurora/config.json)
    |
    v
Defaults (claude, sonnet)
```

## Key Interfaces

### Memory Store (aurora_core.store)
```python
class MemoryStore:
    def store_chunk(chunk: Chunk) -> str
    def search(query: str, limit: int, chunk_type: str) -> List[SearchResult]
    def update_activation(chunk_id: str) -> None
    def get_associations(chunk_id: str) -> List[Association]
```

### SOAR Orchestrator (aurora_soar.orchestrator)
```python
class SOAROrchestrator:
    def process_query(query: str, mode: str) -> SOARResult
    def decompose_goal(goal: str, context: List[str]) -> GoalDecomposition
```

### Agent Registry (aurora_cli.agent_discovery)
```python
class AgentManifest:
    def list_agents() -> List[AgentInfo]
    def find_agent(agent_id: str) -> Optional[AgentInfo]
    def match_capabilities(required: List[str]) -> List[AgentMatch]
```

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Memory search | <500ms | On 10K+ chunks |
| Index (incremental) | <5s | Changed files only |
| Index (full) | <60s | 10K files |
| Goal decomposition | <30s | With LLM |
| Agent matching | <100ms | Keyword-based |

## External Dependencies

### Required
- Python 3.10+
- Git (for git-aware indexing)
- One CLI tool (claude, cursor, aider, etc.)

### Optional
- `[ml]` extra: sentence-transformers, torch (~1.9GB)
- Anthropic API key (for LLM features)

## Extension Points

### Custom Parsers
Add tree-sitter grammars in `aurora_context_code/parsers/`

### Custom Agents
Add agent definitions in `~/.aurora/agents/` or `.aurora/agents/`

### Custom LLM Providers
Extend `aurora_reasoning/providers/` with new clients
