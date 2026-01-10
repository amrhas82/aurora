# Aurora Tools Guide

Comprehensive guide to Aurora's tooling ecosystem, architecture, and workflows.

## Table of Contents

- [Overview](#overview)
- [Tool Ecosystem](#tool-ecosystem)
- [Core Systems](#core-systems)
- [Command-Line Interface](#command-line-interface)
- [Planning Flow](#planning-flow)
- [Agent System](#agent-system)
- [Memory System](#memory-system)
- [CLI Tool Integration](#cli-tool-integration)
- [Advanced Workflows](#advanced-workflows)
- [Configuration Deep Dive](#configuration-deep-dive)
- [Debugging & Troubleshooting](#debugging--troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

Aurora is a cognitive architecture system that combines memory, reasoning, and agent orchestration for AI-powered development workflows. It provides:

- **Memory System**: ACT-R-based code indexing and retrieval
- **Reasoning Engine**: SOAR 9-phase reasoning pipeline
- **Agent Orchestration**: Multi-agent task execution
- **Planning Tools**: Goal decomposition and task generation
- **CLI Integration**: Works with 20+ CLI tools (claude, cursor, etc.)

### Architecture Components

```
+-------------------------------------------------------------+
|                     Aurora Tooling Stack                     |
+-------------------------------------------------------------+
|  CLI Commands (aur)                                          |
|    +- aur goals     -+                                       |
|    +- aur soar      -+- Use CLIPipeLLMClient                |
|    +- aur spawn     -+                                       |
|    +- aur mem       -+                                       |
|    +- aur agents                                             |
+-------------------------------------------------------------+
|  Core Systems                                                |
|    +- Memory (ACT-R): Code indexing & retrieval             |
|    +- SOAR: 9-phase reasoning pipeline                      |
|    +- Spawner: Parallel agent execution                     |
|    +- Planning: Goal decomposition & agent matching         |
|    +- Discovery: Agent capability matching                  |
+-------------------------------------------------------------+
|  Integration Layer                                           |
|    +- CLIPipeLLMClient: CLI-agnostic LLM interface          |
|    +- ManifestManager: Agent discovery & registration       |
|    +- TaskParser: Markdown task file parsing                |
|    +- ConfigManager: Multi-tier configuration               |
+-------------------------------------------------------------+
|  External Tools (20+ supported)                              |
|    +- claude (CLI)                                           |
|    +- cursor                                                 |
|    +- aider                                                  |
|    +- ... (any tool supporting -p flag)                     |
+-------------------------------------------------------------+
```

---

## Tool Ecosystem

### Command Overview

| Tool | Type | Purpose | Integration |
|------|------|---------|-------------|
| `aur goals` | Planning | Goal decomposition | CLIPipeLLMClient |
| `aur soar` | Reasoning | SOAR research pipeline | CLIPipeLLMClient |
| `aur spawn` | Execution | Parallel task execution | Spawner + CLI tools |
| `aur mem` | Memory | Code indexing/search | ACT-R + SQLite |
| `aur agents` | Discovery | Agent management | ManifestManager |
| `aur plan` | Legacy | OpenSpec planning | Legacy system |

### Tool Selection Matrix

Choose the right tool for your task:

```
Task: "I have a complex question"
  +-> Use: aur soar
      Why: SOAR handles research, decomposition, parallel agents

Task: "I want to plan a feature"
  +-> Use: aur goals -> /plan -> aur implement
      Why: Planning flow provides structured approach

Task: "I have a task list to execute"
  +-> Use: aur spawn
      Why: Parallel execution for independent tasks

Task: "I need to find code"
  +-> Use: aur mem search
      Why: Semantic + keyword search of indexed code

Task: "I want to understand agent capabilities"
  +-> Use: aur agents list
      Why: Shows all available agents and their skills
```

---

## Core Systems

### 1. Memory System (ACT-R)

**Purpose**: Index and retrieve code with semantic understanding.

**Architecture**:
```
+----------------------------------------------+
|           Memory System (ACT-R)              |
+----------------------------------------------+
|  Indexing Pipeline:                          |
|    1. File scanning (recursive)              |
|    2. Chunking (semantic + structural)       |
|    3. Embedding generation (local or API)    |
|    4. SQLite storage (.aurora/memory.db)     |
|                                              |
|  Retrieval Pipeline:                         |
|    1. Query embedding                        |
|    2. Hybrid search (vector + keyword)       |
|    3. Relevance scoring (0.0-1.0)            |
|    4. Result ranking                         |
+----------------------------------------------+
```

**Commands**:
```bash
# Index entire project
aur mem index .

# Index specific directory
aur mem index packages/cli/

# Force rebuild (clears cache)
aur mem index . --force

# Search indexed code
aur mem search "authentication flow"

# Search with limit
aur mem search "payment" --limit 10

# Search with relevance threshold
aur mem search "config" --threshold 0.7
```

**Storage Location**:
- Database: `.aurora/memory.db`
- Cache: `~/.aurora/cache/`
- Embeddings: Stored in SQLite

**Configuration**:
```json
{
  "memory": {
    "embedding_model": "local",  // or "openai"
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "index_patterns": ["*.py", "*.js", "*.md"],
    "exclude_patterns": ["node_modules", ".git"]
  }
}
```

### 2. SOAR Reasoning Engine

**Purpose**: 9-phase reasoning for complex queries with parallel research.

**The 9 Phases**:
```
1. ASSESS     -> Determine query complexity (SIMPLE/MEDIUM/COMPLEX/CRITICAL)
2. RETRIEVE   -> Search memory for relevant context
3. DECOMPOSE  -> Break into sub-questions (if complex)
4. VERIFY     -> Validate decomposition quality
5. ROUTE      -> Assign agents to sub-questions
6. COLLECT    -> Execute agents in parallel (spawn_parallel)
7. SYNTHESIZE -> Combine results coherently
8. RECORD     -> Store reasoning trace
9. RESPOND    -> Format final answer
```

**Complexity Routing**:
```python
SIMPLE (score ≤ 11):
  -> Single-step reasoning, no spawning

MEDIUM (score 12-28):
  -> Multi-step with subgoals, some spawning

COMPLEX (score ≥ 29):
  -> Full decomposition, parallel research (spawn_parallel)

CRITICAL (score ≥ 35):
  -> High-stakes with adversarial verification
```

**Usage Examples**:
```bash
# Simple query (no parallel spawning)
aur soar "What is ACT-R?"

# Medium query (some spawning)
aur soar "How does authentication work in this codebase?"

# Complex query (full parallel research)
aur soar "Compare React, Vue, and Angular for SPAs"

# With tool selection
aur soar "Explain microservices" --tool cursor

# With model selection
aur soar "Optimize database queries" --model opus

# Verbose mode (show all phases)
aur soar "Complex question" --verbose
```

**Parallel Execution in COLLECT Phase**:
```python
# When complexity = COMPLEX, SOAR uses:
results = await spawn_parallel(tasks, max_concurrent=5)

# This spawns up to 5 agents concurrently
# Each agent researches a sub-question independently
# Results are synthesized in phase 7
```

**Log Files**:
```bash
# SOAR logs stored in:
~/.aurora/soar/

# View latest log:
ls -t ~/.aurora/soar/*.log | head -1 | xargs cat

# Follow live execution:
tail -f ~/.aurora/soar/soar-*.log
```

### 3. Spawner System

**Purpose**: Parallel and sequential agent execution with CLI tool integration.

**Functions**:
```python
# Single agent spawn
result = await spawn(
    prompt="Task description",
    tool="claude",
    model="sonnet",
    agent="@full-stack-dev",
    timeout=300
)

# Parallel spawning (up to max_concurrent)
results = await spawn_parallel(
    tasks=[SpawnTask(...), SpawnTask(...), ...],
    max_concurrent=5
)

# Sequential spawning (with context accumulation)
results = await spawn_sequential(
    tasks=[SpawnTask(...), ...],
    pass_context=True
)
```

**Tool Resolution Order**:
```
1. CLI flag: --tool cursor
   ↓ (if not provided)
2. Environment variable: AURORA_SPAWN_TOOL=cursor
   ↓ (if not set)
3. Config file: spawn.default_tool = "cursor"
   ↓ (if not set)
4. Default: "claude"
```

**Model Resolution Order**:
```
1. CLI flag: --model opus
   ↓ (if not provided)
2. Environment variable: AURORA_SPAWN_MODEL=opus
   ↓ (if not set)
3. Config file: spawn.default_model = "opus"
   ↓ (if not set)
4. Default: "sonnet"
```

**Supported CLI Tools**:
```
✓ claude (Anthropic CLI)
✓ cursor
✓ aider
✓ open-interpreter
✓ gpt-engineer
✓ fabric
✓ shell_gpt
✓ chatgpt-cli
✓ llm (Simon Willison's LLM)
✓ ... any tool with -p flag for piping
```

**Task File Format**:
```markdown
# My Tasks

- [ ] 1. Implement authentication endpoint
<!-- agent: full-stack-dev -->
<!-- timeout: 600 -->

- [ ] 2. Write integration tests
<!-- agent: qa-test-architect -->
<!-- depends: 1 -->

- [ ] 3. Update API documentation
<!-- agent: self -->
```

### 4. Planning System

**Purpose**: Structured goal decomposition and task generation.

**Components**:
```
GoalDecomposer
  +- Memory search (find relevant context)
  +- LLM decomposition (via CLIPipeLLMClient)
  +- AgentRecommender (keyword + LLM fallback)
  +- GapDetector (missing agent capabilities)
  +- goals.json generator

TaskGenerator (/plan skill)
  +- goals.json reader
  +- PRD generator
  +- tasks.md generator (with agent metadata)
  +- specs/ generator
```

**AgentRecommender Algorithm**:
```python
def recommend_for_subgoal(subgoal):
    # 1. Try keyword matching
    agent, score = keyword_match(subgoal)
    if score >= 0.5:
        return agent, score

    # 2. Try LLM classification (fallback)
    if llm_client:
        agent, score = llm_classify(subgoal)
        if score >= 0.5:
            return agent, score

    # 3. Return default fallback
    return "full-stack-dev", score
```

**Gap Detection**:
```python
def detect_gaps(subgoals, recommendations):
    gaps = []
    for sg, (agent, confidence) in zip(subgoals, recommendations):
        if confidence < 0.5:
            capabilities = extract_capabilities(sg)
            gaps.append(AgentGap(
                subgoal_id=sg.id,
                suggested_capabilities=capabilities,
                fallback=default_agent
            ))
    return gaps
```

---

## Command-Line Interface

### aur goals - Goal Decomposition

**Full Syntax**:
```bash
aur goals [OPTIONS] GOAL
```

**Options**:
```
--tool, -t TEXT         CLI tool to use (default: from env or config or 'claude')
--model, -m [sonnet|opus] Model to use (default: sonnet)
--context PATH          Add context file (can be used multiple times)
--no-decompose          Skip decomposition (single task goal)
--yes, -y               Skip confirmation prompts
--verbose, -v           Show detailed progress
--help                  Show help message
```

**Examples**:

```bash
# Basic usage
aur goals "Implement OAuth2 authentication with JWT tokens"

# With context files
aur goals "Add caching layer" \
  --context src/api.py \
  --context src/database.py

# Skip confirmation (CI/CD)
aur goals "Fix login bug" --yes

# Simple goal without decomposition
aur goals "Update README" --no-decompose

# Use specific tool and model
aur goals "Optimize database queries" \
  --tool cursor \
  --model opus

# Verbose mode (see all steps)
aur goals "Build user dashboard" --verbose
```

**Output**:
```
🔍 Searching memory for relevant context...
   Found 3 relevant files
   - src/auth/login.py (0.85)
   - src/auth/middleware.py (0.72)
   - docs/auth-design.md (0.68)

📋 Decomposing goal into subgoals...
   Created 4 subgoals

🤖 Matching agents to subgoals...
   ✓ sg-1: @full-stack-dev (0.89)
   ✓ sg-2: @qa-test-architect (0.92)
   ✓ sg-3: @full-stack-dev (0.78)
   ⚠️  sg-4: @full-stack-dev (0.45) - gap detected

⚠️  1 agent gap detected:
   sg-4 needs capabilities: ["security", "audit"]
   Using fallback: @full-stack-dev

📁 Plan directory: .aurora/plans/0001-implement-oauth2-authentication/

Review goals? [Y/n]: y
<opens goals.json in $EDITOR>

Proceed? [Y/n]: y

✅ Goals saved. Run /plan in Claude Code to generate PRD and tasks.
```

**Environment Variables**:
```bash
export AURORA_GOALS_TOOL=cursor    # Default tool
export AURORA_GOALS_MODEL=opus     # Default model
```

**Config File** (`~/.aurora/config.json`):
```json
{
  "goals": {
    "default_tool": "claude",
    "default_model": "sonnet",
    "memory_threshold": 0.3,
    "max_subgoals": 7
  }
}
```

### aur soar - SOAR Reasoning

**Full Syntax**:
```bash
aur soar [OPTIONS] QUERY
```

**Options**:
```
--tool, -t TEXT         CLI tool to use (default: claude)
--model, -m [sonnet|opus] Model to use (default: sonnet)
--verbose, -v           Show all 9 phases
--stream                Stream output in real-time
--save PATH             Save result to file
--help                  Show help message
```

**Examples**:

```bash
# Simple query
aur soar "How does the authentication system work?"

# Complex research (triggers parallel agents)
aur soar "Compare React, Vue, and Angular for building SPAs"

# With tool selection
aur soar "Explain microservices architecture" --tool cursor

# With model selection
aur soar "Optimize database performance" --model opus

# Verbose mode (see all 9 phases)
aur soar "How does ACT-R memory work?" --verbose

# Stream output (see results as they come)
aur soar "Analyze this codebase" --stream

# Save to file
aur soar "Document the API" --save api-docs.md
```

**Verbose Output** (shows all phases):
```
[PHASE 1: ASSESS] Analyzing query complexity...
  Complexity: COMPLEX (score: 32)
  Routing: Full decomposition with parallel research

[PHASE 2: RETRIEVE] Searching memory...
  Found 5 relevant chunks (avg relevance: 0.78)

[PHASE 3: DECOMPOSE] Breaking into sub-questions...
  Sub-question 1: What is React's component model?
  Sub-question 2: How does Vue's reactivity system work?
  Sub-question 3: What is Angular's dependency injection?

[PHASE 4: VERIFY] Validating decomposition...
  Quality score: 0.92 (good)

[PHASE 5: ROUTE] Assigning agents...
  Sub-Q1 -> @researcher (0.85)
  Sub-Q2 -> @researcher (0.88)
  Sub-Q3 -> @researcher (0.91)

[PHASE 6: COLLECT] Executing agents in parallel...
  Spawning 3 agents (max_concurrent=5)
  ✓ Agent 1 completed (12.3s)
  ✓ Agent 2 completed (14.1s)
  ✓ Agent 3 completed (11.8s)

[PHASE 7: SYNTHESIZE] Combining results...
  Synthesized 3 agent outputs
  Confidence: 0.87

[PHASE 8: RECORD] Storing reasoning trace...
  Saved to ~/.aurora/soar/soar-20260110-123456.log

[PHASE 9: RESPOND] Formatting answer...

<Final synthesized answer here>
```

**Environment Variables**:
```bash
export AURORA_SOAR_TOOL=cursor     # Default tool
export AURORA_SOAR_MODEL=opus      # Default model
```

### aur spawn - Parallel Task Execution

**Full Syntax**:
```bash
aur spawn [OPTIONS] [TASK_FILE]
```

**Options**:
```
--parallel/--no-parallel  Enable/disable parallel execution (default: parallel)
--sequential             Force sequential execution
--dry-run                Validate without executing
--verbose, -v            Show detailed progress
--max-concurrent INT     Maximum parallel tasks (default: 5)
--timeout INT            Task timeout in seconds (default: 300)
--help                   Show help message
```

**Examples**:

```bash
# Execute tasks.md in parallel (default)
aur spawn

# Execute specific file
aur spawn my-tasks.md

# Dry run (validate only)
aur spawn tasks.md --dry-run

# Sequential execution
aur spawn tasks.md --sequential

# Limit parallelism
aur spawn tasks.md --max-concurrent 3

# Custom timeout
aur spawn tasks.md --timeout 600

# Verbose output
aur spawn tasks.md --verbose
```

**Progress Output**:
```
Loaded 5 tasks from tasks.md

Executing in parallel (max_concurrent=5)...

[1/5] Task 1: Implement auth endpoint ... ✓ (12.3s)
[2/5] Task 2: Write tests          ... ✓ (14.1s)
[3/5] Task 3: Update docs          ... ✓ (8.2s)
[4/5] Task 4: Deploy to staging    ... ✓ (18.7s)
[5/5] Task 5: Send notification    ... ✓ (3.1s)

Summary:
  Total: 5
  Completed: 5
  Failed: 0
  Duration: 18.7s
```

**Environment Variables**:
```bash
export AURORA_SPAWN_MAX_CONCURRENT=10  # Max parallel
export AURORA_SPAWN_TIMEOUT=600        # Timeout (sec)
```

### aur mem - Memory Commands

**Index Command**:
```bash
# Index current directory
aur mem index .

# Index specific directory
aur mem index packages/

# Force rebuild
aur mem index . --force

# Index with pattern
aur mem index . --include "*.py" --include "*.md"

# Exclude patterns
aur mem index . --exclude "node_modules" --exclude ".git"
```

**Search Command**:
```bash
# Basic search
aur mem search "authentication"

# Limit results
aur mem search "payment" --limit 10

# Relevance threshold
aur mem search "config" --threshold 0.7

# JSON output
aur mem search "api" --json
```

### aur agents - Agent Management

**List Command**:
```bash
# List all agents
aur agents list

# Show agent details
aur agents show full-stack-dev

# List by capability
aur agents list --capability testing

# JSON output
aur agents list --json
```

**Agent Manifest Format**:
```json
{
  "agents": [
    {
      "id": "full-stack-dev",
      "name": "Full Stack Developer",
      "capabilities": ["frontend", "backend", "api", "database"],
      "description": "Implements full-stack features with tests"
    }
  ]
}
```

---

## Planning Flow

Complete workflow from goal to execution.

### Stage 1: Goal Decomposition (Terminal)

```bash
# Start with a high-level goal
aur goals "Implement user authentication system"
```

**What happens**:
1. Memory search finds relevant context (existing auth code, docs)
2. Goal decomposed into 3-7 subgoals using LLM
3. Agents matched to each subgoal (keyword + LLM fallback)
4. Gaps detected (missing agent capabilities)
5. User reviews goals.json in editor
6. Directory created: `.aurora/plans/0001-implement-user-auth/`
7. `goals.json` saved with subgoals and agent assignments

**goals.json Output**:
```json
{
  "id": "0001-implement-user-auth",
  "title": "Implement user authentication system",
  "created_at": "2026-01-10T12:00:00Z",
  "status": "ready_for_planning",
  "memory_context": [
    {"file": "src/auth/login.py", "relevance": 0.85},
    {"file": "src/models/user.py", "relevance": 0.78}
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Implement JWT token generation",
      "description": "Add function to generate and sign JWT tokens",
      "agent": "@full-stack-dev",
      "confidence": 0.89,
      "dependencies": []
    },
    {
      "id": "sg-2",
      "title": "Create login endpoint",
      "description": "Add POST /api/login endpoint with validation",
      "agent": "@full-stack-dev",
      "confidence": 0.92,
      "dependencies": ["sg-1"]
    },
    {
      "id": "sg-3",
      "title": "Write authentication tests",
      "description": "Add unit and integration tests for auth flow",
      "agent": "@qa-test-architect",
      "confidence": 0.95,
      "dependencies": ["sg-1", "sg-2"]
    }
  ],
  "gaps": []
}
```

### Stage 2: PRD and Task Generation (Claude Code)

```bash
# Navigate to plan directory
cd .aurora/plans/0001-implement-user-auth/

# Run /plan skill in Claude Code
/plan
```

**What happens**:
1. `/plan` skill reads `goals.json`
2. Generates `prd.md` with full requirements
3. Generates `tasks.md` with agent metadata from goals.json
4. Generates `specs/` directory with detailed specifications

**Generated Files**:
```
.aurora/plans/0001-implement-user-auth/
+-- goals.json              # Created by: aur goals
+-- prd.md                  # Created by: /plan
+-- tasks.md                # Created by: /plan
+-- specs/                  # Created by: /plan
    +-- api-spec.md
    +-- auth-flow.md
    +-- test-plan.md
```

**tasks.md Format**:
```markdown
# Implementation Tasks

- [ ] 1. Implement JWT token generation
<!-- agent: full-stack-dev -->
<!-- goal: sg-1 -->

- [ ] 2. Create login endpoint
<!-- agent: full-stack-dev -->
<!-- goal: sg-2 -->
<!-- depends: 1 -->

- [ ] 3. Write authentication tests
<!-- agent: qa-test-architect -->
<!-- goal: sg-3 -->
<!-- depends: 1,2 -->
```

### Stage 3: Task Execution

**Option A: Sequential Execution (Claude Code)**:
```bash
# In Claude Code, run:
aur implement

# This executes tasks one at a time
# Uses Task tool to spawn subagents
# Marks tasks [x] as completed
```

**Option B: Parallel Execution (Terminal)**:
```bash
# From terminal:
aur spawn tasks.md --verbose

# This executes tasks in parallel
# Respects dependencies
# Max 5 concurrent by default
```

**Complete Workflow Example**:
```bash
# 1. Decompose goal (Terminal)
aur goals "Add user authentication" --verbose

# 2. Review and edit goals
cd .aurora/plans/0001-add-user-auth/
$EDITOR goals.json

# 3. Generate PRD and tasks (Claude Code)
# In Claude Code, run: /plan

# 4a. Execute sequentially (Claude Code)
# In Claude Code, run: aur implement

# OR

# 4b. Execute in parallel (Terminal)
aur spawn tasks.md --verbose

# 5. Re-index updated code
aur mem index .

# 6. Verify implementation
aur soar "Explain the authentication system"
```

---

## Agent System

### Agent Discovery

**Manifest Manager**:
```python
from aurora_cli.agent_discovery import ManifestManager

manager = ManifestManager()
manifest = manager.get_or_refresh()

# List all agents
for agent in manifest.agents:
    print(f"{agent.id}: {agent.name}")
    print(f"  Capabilities: {agent.capabilities}")

# Get specific agent
agent = manager.get_agent("full-stack-dev")
```

**Discovery Paths**:
```
1. Project agents: .aurora/agents/
2. Global agents: ~/.aurora/agents/
3. Package agents: aurora_cli/agents/
```

**Agent Manifest Format**:
```markdown
---
id: full-stack-dev
name: Full Stack Developer
capabilities:
  - frontend
  - backend
  - api
  - database
  - testing
---

# Full Stack Developer Agent

Implements full-stack features with comprehensive testing.

## Capabilities
- Frontend: React, Vue, Angular
- Backend: Python, Node.js, Go
- Database: PostgreSQL, MongoDB
- Testing: pytest, Jest, Cypress

## Usage
Assign to tasks requiring end-to-end implementation.
```

### Agent Matching

**Keyword-Based Matching**:
```python
keywords = {
    "full-stack-dev": ["implement", "build", "create", "api", "endpoint"],
    "qa-test-architect": ["test", "verify", "validate", "qa", "quality"],
    "researcher": ["research", "investigate", "analyze", "explain"]
}

def keyword_match(task_description):
    scores = {}
    for agent, keywords in keywords.items():
        score = sum(1 for kw in keywords if kw in task_description.lower())
        scores[agent] = score / len(keywords)
    return max(scores.items(), key=lambda x: x[1])
```

**LLM Fallback**:
```python
def llm_classify(task_description, available_agents):
    prompt = f"""
    Task: {task_description}

    Available agents:
    {format_agents(available_agents)}

    Which agent is best suited for this task?
    Return JSON: {{"agent_id": "...", "confidence": 0.85}}
    """

    response = llm_client.generate(prompt)
    return parse_agent_recommendation(response)
```

**Combined Approach**:
```
1. Try keyword matching
   +- If score >= 0.5: Use that agent
   +- If score < 0.5: Continue to step 2

2. Try LLM classification
   +- If score >= 0.5: Use that agent
   +- If score < 0.5: Continue to step 3

3. Use default fallback agent
   +- Return: "full-stack-dev" with low confidence
```

### Gap Detection

**What are gaps?**
Gaps occur when no suitable agent exists for a subgoal (confidence < 0.5).

**Gap Report**:
```json
{
  "gaps": [
    {
      "subgoal_id": "sg-4",
      "suggested_capabilities": ["security", "penetration-testing", "audit"],
      "fallback": "@full-stack-dev"
    }
  ]
}
```

**User Action**:
1. Create new agent with suggested capabilities
2. Use fallback agent (may not be optimal)
3. Modify subgoal to match existing agents

---

## Memory System

### Indexing

**What gets indexed**:
- Python files (*.py)
- JavaScript files (*.js, *.jsx, *.ts, *.tsx)
- Markdown files (*.md)
- Configuration files (*.json, *.yaml, *.toml)

**Chunking Strategy**:
```python
# Semantic chunking (respects code structure)
chunks = semantic_chunk(file_content, chunk_size=1000, overlap=200)

# Structural chunking (functions, classes)
chunks = structural_chunk(ast_tree)

# Combined approach
final_chunks = merge(semantic_chunks, structural_chunks)
```

**Embedding Models**:
```python
# Local model (default)
embeddings = LocalEmbedder().embed(chunks)

# OpenAI model
embeddings = OpenAIEmbedder(api_key).embed(chunks)

# Custom model
embeddings = CustomEmbedder(model_path).embed(chunks)
```

### Retrieval

**Hybrid Search**:
```python
# Vector search (semantic similarity)
vector_results = cosine_similarity(query_embedding, chunk_embeddings)

# Keyword search (BM25)
keyword_results = bm25_search(query_tokens, chunk_tokens)

# Combine with weights
final_results = (
    0.7 * vector_results +
    0.3 * keyword_results
)
```

**Relevance Scoring**:
```
Score range: 0.0 - 1.0

0.9 - 1.0: Highly relevant (exact match)
0.7 - 0.9: Very relevant (strong semantic match)
0.5 - 0.7: Relevant (partial match)
0.3 - 0.5: Somewhat relevant (weak match)
0.0 - 0.3: Not relevant (filtered out)
```

**Memory Context in goals.json**:
```json
{
  "memory_context": [
    {"file": "src/auth/login.py", "relevance": 0.92},
    {"file": "src/auth/middleware.py", "relevance": 0.85},
    {"file": "src/models/user.py", "relevance": 0.78},
    {"file": "docs/auth-design.md", "relevance": 0.71}
  ]
}
```

---

## CLI Tool Integration

### CLIPipeLLMClient

**Purpose**: CLI-agnostic LLM interface that works with 20+ tools.

**Architecture**:
```python
class CLIPipeLLMClient:
    def __init__(self, tool: str, model: str):
        self.tool = tool      # "claude", "cursor", etc.
        self.model = model    # "sonnet", "opus", etc.

    async def generate(self, prompt: str, **kwargs):
        # 1. Build command: [tool, "-p", "--model", model]
        # 2. Spawn subprocess
        # 3. Pipe prompt to stdin
        # 4. Stream stdout back
        # 5. Return response
```

**Tool Requirements**:
```
Any CLI tool that supports:
  - `-p` or `--print` flag for non-interactive mode
  - Prompt via stdin
  - Output to stdout

Example compatible tools:
  ✓ claude -p --model sonnet
  ✓ cursor --print
  ✓ aider --yes --no-check-update
  ✓ open-interpreter --local
```

**Tool Validation**:
```python
def validate_tool(tool: str) -> bool:
    # Check if tool exists in PATH
    if not shutil.which(tool):
        raise ValueError(f"Tool '{tool}' not found in PATH")

    # Verify tool supports required flags
    result = subprocess.run([tool, "--help"], capture_output=True)
    if "-p" not in result.stdout.decode():
        warnings.warn(f"Tool '{tool}' may not support -p flag")

    return True
```

**Resolution Flow**:
```
User runs: aur goals "Goal text"

1. Check CLI flag: --tool cursor
   +- If provided: use cursor

2. Check environment variable: AURORA_GOALS_TOOL=cursor
   +- If set: use cursor

3. Check config file: goals.default_tool = "cursor"
   +- If set: use cursor

4. Use default: "claude"

Same process for model selection.
```

### Supported Tools Matrix

| Tool | Tested | Flags | Notes |
|------|--------|-------|-------|
| claude | ✅ | `-p --model` | Official Anthropic CLI |
| cursor | ✅ | `--print` | Cursor IDE CLI |
| aider | ✅ | `--yes --no-check-update` | AI pair programming |
| open-interpreter | ⚠️ | `--local` | May need additional setup |
| gpt-engineer | ⚠️ | Custom | Needs wrapper script |
| fabric | ✅ | `-p` | LLM framework |
| shell_gpt | ✅ | `--no-animation` | Terminal assistant |
| chatgpt-cli | ⚠️ | Custom | Needs configuration |
| llm | ✅ | `-p` | Simon Willison's tool |

### Custom Tool Integration

**Wrapper Script Example**:
```bash
#!/bin/bash
# custom-tool-wrapper.sh

# Read prompt from stdin
prompt=$(cat)

# Call your custom tool
your-custom-tool --prompt "$prompt" --model "$1" --output -

# Exit with tool's exit code
exit $?
```

**Register Custom Tool**:
```bash
# Make wrapper executable
chmod +x custom-tool-wrapper.sh

# Add to PATH
export PATH=$PATH:/path/to/wrappers

# Use with Aurora
aur goals "Goal" --tool custom-tool-wrapper
```

**Config for Custom Tool**:
```json
{
  "goals": {
    "default_tool": "custom-tool-wrapper"
  }
}
```

---

## Advanced Workflows

### Workflow 1: Feature Implementation with Full Traceability

```bash
# 1. Index current codebase
aur mem index .

# 2. Research existing patterns
aur soar "How is API routing currently implemented?" --verbose

# 3. Create goals with context
aur goals "Add new user profile API endpoint" \
  --context src/api/routes.py \
  --context src/models/user.py

# 4. Review goals.json
cd .aurora/plans/0001-add-user-profile-api/
cat goals.json

# 5. Generate PRD and tasks (Claude Code)
# Run: /plan

# 6. Execute with progress tracking
aur spawn tasks.md --verbose

# 7. Verify implementation
aur mem index .
aur soar "Explain the user profile API endpoint"

# 8. Document changes
aur soar "Summarize changes made in this branch" --save CHANGELOG.md
```

### Workflow 2: Bug Investigation and Fix

```bash
# 1. Search for bug context
aur mem search "login authentication error"

# 2. Investigate with SOAR
aur soar "Why might authentication fail intermittently?" --verbose

# 3. Create focused goal
aur goals "Fix intermittent authentication failures" \
  --context src/auth/login.py \
  --context src/auth/session.py \
  --no-decompose

# 4. Quick fix with spawn
aur spawn tasks.md --sequential

# 5. Verify fix
aur mem index .
aur soar "How does the authentication system handle session timeouts now?"
```

### Workflow 3: Research-Driven Development

```bash
# 1. Research options
aur soar "Compare WebSocket implementations: socket.io vs native WebSockets" \
  --model opus \
  --save research/websocket-comparison.md

# 2. Create goal based on research
aur goals "Implement WebSocket support using socket.io" \
  --context research/websocket-comparison.md

# 3. Generate detailed plan
cd .aurora/plans/0001-implement-websocket-support/
# Run /plan in Claude Code

# 4. Parallel execution
aur spawn tasks.md --max-concurrent 3

# 5. Document decision
aur soar "Why did we choose socket.io over native WebSockets?" \
  --save docs/decisions/websocket-choice.md
```

### Workflow 4: Multi-Agent Collaboration

```bash
# 1. List available agents
aur agents list

# 2. Create task file with explicit agent assignments
cat > tasks.md << 'EOF'
- [ ] 1. Research best practices for real-time updates
<!-- agent: researcher -->

- [ ] 2. Design WebSocket API
<!-- agent: architect -->

- [ ] 3. Implement WebSocket server
<!-- agent: full-stack-dev -->
<!-- depends: 2 -->

- [ ] 4. Add client-side WebSocket handler
<!-- agent: full-stack-dev -->
<!-- depends: 2 -->

- [ ] 5. Write integration tests
<!-- agent: qa-test-architect -->
<!-- depends: 3,4 -->

- [ ] 6. Create API documentation
<!-- agent: technical-writer -->
<!-- depends: 2,3,4 -->
EOF

# 3. Execute with parallel agents
aur spawn tasks.md --verbose

# 4. Review results
cat tasks.md  # See [x] for completed tasks
```

### Workflow 5: Continuous Integration

```bash
#!/bin/bash
# ci-workflow.sh

# 1. Index codebase
aur mem index . --force

# 2. Run SOAR quality check
aur soar "Analyze code quality and identify issues" \
  --model opus \
  --save reports/quality-check.md

# 3. Check for missing tests
aur soar "List all functions without tests" \
  --save reports/missing-tests.md

# 4. Generate test tasks
aur goals "Add missing test coverage" \
  --context reports/missing-tests.md \
  --yes

# 5. Execute test creation
cd .aurora/plans/*/
# Run /plan in Claude Code
aur spawn tasks.md --sequential

# 6. Re-index with new tests
aur mem index .

# 7. Verify coverage
aur soar "Summarize test coverage improvements" \
  --save reports/coverage-summary.md
```

---

## Configuration Deep Dive

### Multi-Tier Configuration

**Resolution Order** (highest to lowest priority):
```
1. CLI flags (--tool, --model)
2. Environment variables (AURORA_*_TOOL, AURORA_*_MODEL)
3. Project config (.aurora/config.json)
4. Global config (~/.aurora/config.json)
5. Built-in defaults
```

**Example Resolution**:
```bash
# Scenario: User runs
aur goals "Goal" --tool cursor

# Resolution:
1. CLI flag: --tool cursor ✓ USED
2. AURORA_GOALS_TOOL=claude ✗ IGNORED
3. Project config: "tool": "aider" ✗ IGNORED
4. Global config: "tool": "claude" ✗ IGNORED
5. Default: "claude" ✗ IGNORED

# Result: Uses cursor
```

### Global Configuration

**File**: `~/.aurora/config.json`

```json
{
  "goals": {
    "default_tool": "claude",
    "default_model": "sonnet",
    "memory_threshold": 0.3,
    "max_subgoals": 7,
    "enable_gaps": true
  },
  "soar": {
    "default_tool": "claude",
    "default_model": "sonnet",
    "enable_parallel": true,
    "max_concurrent": 5,
    "complexity_threshold": {
      "simple": 11,
      "medium": 28,
      "complex": 29
    }
  },
  "spawn": {
    "max_concurrent": 5,
    "default_timeout": 300,
    "enable_progress": true,
    "update_tasks_file": true
  },
  "memory": {
    "embedding_model": "local",
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "relevance_threshold": 0.3,
    "max_results": 10
  },
  "agents": {
    "discovery_paths": [
      "~/.aurora/agents",
      ".aurora/agents"
    ],
    "fallback_agent": "full-stack-dev",
    "confidence_threshold": 0.5
  },
  "logging": {
    "level": "INFO",
    "file": "~/.aurora/aurora.log",
    "max_size_mb": 100,
    "backup_count": 5
  }
}
```

### Project Configuration

**File**: `.aurora/config.json`

```json
{
  "goals": {
    "default_tool": "cursor",
    "memory_threshold": 0.5
  },
  "soar": {
    "default_model": "opus"
  },
  "memory": {
    "index_patterns": ["*.py", "*.js", "*.md"],
    "exclude_patterns": [
      "node_modules",
      ".git",
      "venv",
      "__pycache__"
    ]
  }
}
```

**Project config overrides global config** for matching keys.

### Environment Variables

**Goals Command**:
```bash
export AURORA_GOALS_TOOL=cursor
export AURORA_GOALS_MODEL=opus
```

**SOAR Command**:
```bash
export AURORA_SOAR_TOOL=claude
export AURORA_SOAR_MODEL=sonnet
```

**Spawn Command**:
```bash
export AURORA_SPAWN_MAX_CONCURRENT=10
export AURORA_SPAWN_TIMEOUT=600
```

**API Keys**:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
```

**Logging**:
```bash
export AURORA_LOGGING_LEVEL=DEBUG
export AURORA_LOG_FILE=/var/log/aurora.log
```

---

## Debugging & Troubleshooting

### Log Files

**SOAR Logs**:
```bash
# Location
~/.aurora/soar/soar-YYYYMMDD-HHMMSS.log

# View latest
ls -t ~/.aurora/soar/*.log | head -1 | xargs cat

# Follow live
tail -f ~/.aurora/soar/soar-*.log

# Filter by phase
grep "PHASE" ~/.aurora/soar/soar-*.log

# Check for errors
grep "ERROR" ~/.aurora/soar/soar-*.log
```

**Aurora Main Log**:
```bash
# Location
~/.aurora/aurora.log

# View with tail
tail -f ~/.aurora/aurora.log

# Filter by level
grep "ERROR" ~/.aurora/aurora.log
grep "WARNING" ~/.aurora/aurora.log

# Debug mode
export AURORA_LOGGING_LEVEL=DEBUG
aur goals "Goal" --verbose
```

**Spawn Execution Logs**:
```bash
# Verbose mode shows all subprocess output
aur spawn tasks.md --verbose

# Individual task logs (if tool supports it)
ls -la .aurora/spawn-logs/
```

### Common Issues

#### Issue: "Tool not found"

**Error**:
```
ValueError: Tool 'cursor' not found in PATH
```

**Solutions**:
```bash
# Check if tool is installed
which cursor

# Add tool to PATH
export PATH=$PATH:/path/to/cursor

# Use a different tool
aur goals "Goal" --tool claude

# Set default tool
cat >> ~/.aurora/config.json << 'EOF'
{
  "goals": {"default_tool": "claude"}
}
EOF
```

#### Issue: "No agent found for subgoal"

**Error**:
```
WARNING: No good agent for 'sg-3'
  Suggested: Create agent with capabilities: ["security", "audit"]
  Using fallback: @full-stack-dev
```

**Solutions**:
```bash
# 1. Create new agent with suggested capabilities
cat > .aurora/agents/security-expert.md << 'EOF'
---
id: security-expert
name: Security Expert
capabilities:
  - security
  - audit
  - penetration-testing
---

Security expert specializing in audits and testing.
EOF

# 2. Re-run goals command
aur goals "Goal" --verbose

# 3. Or accept fallback agent in goals.json
```

#### Issue: "Memory database locked"

**Error**:
```
sqlite3.OperationalError: database is locked
```

**Solutions**:
```bash
# Check for other Aurora processes
ps aux | grep aur

# Kill stale processes
pkill -f "aur mem"

# Rebuild index if corrupted
rm .aurora/memory.db
aur mem index . --force
```

#### Issue: "Spawn timeout"

**Error**:
```
Task 3 timed out after 300 seconds
```

**Solutions**:
```bash
# Increase timeout
aur spawn tasks.md --timeout 600

# Or per-task timeout in tasks.md
# - [ ] 1. Long running task
# <!-- timeout: 600 -->

# Or set default in config
cat >> ~/.aurora/config.json << 'EOF'
{
  "spawn": {"default_timeout": 600}
}
EOF
```

#### Issue: "goals.json validation error"

**Error**:
```
ValidationError: goals.json missing required field 'subgoals'
```

**Solutions**:
```bash
# Check JSON validity
python3 -m json.tool .aurora/plans/*/goals.json

# Regenerate goals.json
rm .aurora/plans/*/goals.json
aur goals "Goal" --yes

# Manually fix goals.json
$EDITOR .aurora/plans/*/goals.json
```

### Debug Mode

**Enable Debug Logging**:
```bash
# Environment variable
export AURORA_LOGGING_LEVEL=DEBUG

# Config file
{
  "logging": {"level": "DEBUG"}
}

# CLI flag
aur goals "Goal" --debug --verbose
```

**Debug Output Shows**:
```
[DEBUG] CLIPipeLLMClient: Resolving tool...
[DEBUG] Tool resolution: CLI flag -> None
[DEBUG] Tool resolution: Env var -> cursor
[DEBUG] Tool selected: cursor
[DEBUG] Model resolution: CLI flag -> sonnet
[DEBUG] Building command: ['cursor', '--print', '--model', 'sonnet']
[DEBUG] Spawning subprocess...
[DEBUG] Piping prompt (245 chars) to stdin...
[DEBUG] Reading stdout...
[DEBUG] Process completed with exit code 0
```

### Health Check

**Run Diagnostics**:
```bash
aur doctor

# Output:
✓ Aurora installation OK
✓ Config file valid
✓ Memory database accessible
✓ CLI tools: claude (found), cursor (found)
✓ Agents: 5 discovered
✗ SOAR logs: 15 files (recommend cleanup)

Recommendations:
  - Clean old SOAR logs: rm ~/.aurora/soar/*.log
  - Update Aurora: pip install --upgrade aurora-actr
```

**Auto-Fix Issues**:
```bash
aur doctor --fix
```

---

## Best Practices

### Memory Management

**Index Regularly**:
```bash
# After significant code changes
git commit && aur mem index .

# Daily in CI/CD
0 2 * * * cd /project && aur mem index . --force

# After pulling changes
git pull && aur mem index .
```

**Optimize Index Size**:
```json
{
  "memory": {
    "index_patterns": ["*.py", "*.js", "*.md"],
    "exclude_patterns": [
      "node_modules",
      ".git",
      "venv",
      "__pycache__",
      "*.min.js",
      "build",
      "dist"
    ]
  }
}
```

**Clean Old Data**:
```bash
# Rebuild from scratch
rm .aurora/memory.db
aur mem index . --force

# Clear cache
rm -rf ~/.aurora/cache/
```

### Goal Decomposition

**Good Goals** (specific, actionable):
```bash
✓ aur goals "Add OAuth2 authentication with JWT tokens"
✓ aur goals "Implement real-time WebSocket notifications"
✓ aur goals "Optimize database queries in user dashboard"
```

**Bad Goals** (vague, too broad):
```bash
✗ aur goals "Make it better"
✗ aur goals "Fix all bugs"
✗ aur goals "Improve performance"
```

**Use Context Files**:
```bash
# Provide relevant context for better decomposition
aur goals "Refactor authentication" \
  --context src/auth/login.py \
  --context src/auth/middleware.py \
  --context docs/auth-design.md
```

### Task Organization

**Task File Structure**:
```markdown
# Feature: User Authentication

## Phase 1: Core Implementation
- [ ] 1. Implement JWT generation
<!-- agent: full-stack-dev -->

- [ ] 2. Create login endpoint
<!-- agent: full-stack-dev -->
<!-- depends: 1 -->

## Phase 2: Testing
- [ ] 3. Write unit tests
<!-- agent: qa-test-architect -->
<!-- depends: 1,2 -->

- [ ] 4. Write integration tests
<!-- agent: qa-test-architect -->
<!-- depends: 1,2 -->

## Phase 3: Documentation
- [ ] 5. Update API docs
<!-- agent: technical-writer -->
<!-- depends: 2 -->
```

**Dependencies**:
```markdown
# Independent tasks (can run in parallel)
- [ ] 1. Task A
- [ ] 2. Task B
- [ ] 3. Task C

# Sequential tasks (must run in order)
- [ ] 1. Task A
- [ ] 2. Task B
<!-- depends: 1 -->
- [ ] 3. Task C
<!-- depends: 2 -->

# Diamond dependency (A -> B,C -> D)
- [ ] 1. Task A
- [ ] 2. Task B
<!-- depends: 1 -->
- [ ] 3. Task C
<!-- depends: 1 -->
- [ ] 4. Task D
<!-- depends: 2,3 -->
```

### Agent Assignment

**Let Aurora Decide** (default):
```bash
# Aurora matches agents automatically
aur goals "Implement feature"
```

**Manual Override** (when needed):
```markdown
- [ ] 1. Implement feature
<!-- agent: custom-agent-id -->
```

**Review Assignments**:
```bash
# Always review goals.json before proceeding
cd .aurora/plans/*/
cat goals.json
$EDITOR goals.json  # Fix any wrong assignments
```

### Performance Optimization

**Parallel Execution**:
```bash
# Use parallel for independent tasks
aur spawn tasks.md --max-concurrent 10

# Use sequential for dependent tasks
aur spawn tasks.md --sequential
```

**Resource Limits**:
```bash
# Don't overwhelm your system
export AURORA_SPAWN_MAX_CONCURRENT=5  # For laptops
export AURORA_SPAWN_MAX_CONCURRENT=20 # For servers

# Adjust timeouts for long-running tasks
export AURORA_SPAWN_TIMEOUT=600  # 10 minutes
```

**Memory Index Optimization**:
```bash
# Index only what you need
aur mem index packages/cli/ packages/core/

# Skip large files
aur mem index . --exclude "*.sqlite" --exclude "*.db"
```

### Security

**API Keys**:
```bash
# Use environment variables (not config files)
export ANTHROPIC_API_KEY=sk-ant-...

# Don't commit keys
echo "ANTHROPIC_API_KEY=*" >> .gitignore

# Use secrets management in production
export ANTHROPIC_API_KEY=$(vault read -field=api_key secret/anthropic)
```

**Config Files**:
```bash
# Project config should be committed
git add .aurora/config.json

# Global config should NOT be committed
# (already in ~/.aurora/, not in project)

# Sensitive data should use env vars
{
  "goals": {
    "default_tool": "claude"  # ✓ OK to commit
  }
}
```

**Task Files**:
```markdown
# Don't include sensitive data in task descriptions
- [ ] 1. Deploy to production
<!-- agent: devops -->
<!-- NOTE: Use env vars for credentials -->

# Use placeholders
- [ ] 1. Update API key to ${NEW_API_KEY}
<!-- agent: devops -->
```

---

## See Also

- [COMMANDS.md](COMMANDS.md) - Quick command reference
- [Configuration Reference](../reference/CONFIG_REFERENCE.md) - Detailed config guide
- [SOAR Architecture](../reference/SOAR_ARCHITECTURE.md) - SOAR pipeline internals
- [Planning Flow](../workflows/planning-flow.md) - Complete planning workflow
- [aur goals Documentation](../commands/aur-goals.md) - Goals command details
- [aur soar Documentation](../commands/aur-soar.md) - SOAR command details
- [aur spawn Documentation](../commands/aur-spawn.md) - Spawn command details

---

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for:
- Development setup
- Adding new commands
- Creating custom agents
- Testing guidelines

## License

MIT License - See [LICENSE](../../LICENSE) for details.
