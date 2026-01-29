# aur goals

Decompose high-level goals into actionable subgoals with agent assignments.

## Synopsis

```bash
aur goals GOAL [OPTIONS]
```

## Description

The `aur goals` command analyzes a high-level goal and decomposes it into concrete subgoals with recommended agent assignments. It creates a `goals.json` file in `.aurora/plans/NNNN-slug/` that serves as input for the `/plan` skill in Claude Code.

**Shared Infrastructure**: Uses `SOAROrchestrator` (same as `aur soar`) with `stop_after_verify=True` to run phases 1-4 only (Memory, Search, Decompose, Verify). This ensures consistent decomposition quality across all Aurora planning commands.

**Workflow Position**: This is step 1 of the planning flow:
1. **aur goals** - Decompose goal (this command)
2. **/plan** - Generate PRD and tasks (Claude Code skill)
3. **aur implement** or **aur spawn** - Execute tasks

## Arguments

### GOAL (required)

High-level goal description. Must be 10-500 characters.

**Examples**:
- ✅ "Implement OAuth2 authentication"
- ✅ "Add caching layer for API performance"
- ❌ "Fix bug" (too short - minimum 10 characters)
- ❌ Very long descriptions over 500 characters

## Options

### --tool, -t TOOL

CLI tool to use for LLM operations.

**Default**: Resolved in order:
1. CLI flag value (this option)
2. `AURORA_GOALS_TOOL` environment variable
3. `goals_default_tool` from config file
4. `"claude"` (fallback)

**Examples**:
```bash
aur goals "Add feature" --tool claude
aur goals "Add feature" --tool cursor
aur goals "Add feature" -t windsurf
```

**Validation**: Tool must exist in PATH.

### --model, -m {sonnet|opus}

Model to use for LLM operations.

**Default**: Resolved in order:
1. CLI flag value (this option)
2. `AURORA_GOALS_MODEL` environment variable
3. `goals_default_model` from config file
4. `"sonnet"` (fallback)

**Examples**:
```bash
aur goals "Complex task" --model opus
aur goals "Simple task" --model sonnet
aur goals "Feature" -m opus
```

### --context, -c FILE

Context files for informed decomposition. Can be specified multiple times.

**Usage**:
```bash
aur goals "Optimize queries" --context src/db/queries.py
aur goals "Add API" -c src/api/routes.py -c src/models/user.py
```

**Purpose**: Provides relevant code context to improve goal decomposition quality.

### --no-decompose

Skip SOAR decomposition and create a single-task plan.

**Usage**:
```bash
aur goals "Fix validation bug" --no-decompose
```

**When to use**: For simple tasks that don't need to be broken down.

### --format, -f {rich|json}

Output format.

**Default**: `rich` (human-readable terminal output)

**Options**:
- `rich`: Colored terminal output with tables
- `json`: Machine-readable JSON (for programmatic use)

**Examples**:
```bash
aur goals "Add feature" --format json > plan.json
aur goals "Add feature" -f rich
```

### --yes, -y

Skip confirmation prompts and proceed automatically.

**Usage**:
```bash
aur goals "Add feature" --yes
aur goals "Add feature" -y
```

**Behavior**: Skips:
- Review goals in editor prompt
- Proceed with saving prompt

### --non-interactive

Alias for `--yes`. Non-interactive mode.

### --no-auto-init

Disable automatic `.aurora` initialization if it doesn't exist.

**Default**: Auto-initializes if `.aurora` directory missing

### --verbose, -v

Show detailed progress information.

**Usage**:
```bash
aur goals "Add feature" --verbose
```

**Output includes**:
- Tool and model being used
- Decomposition progress
- Agent matching details
- Memory search results

## Examples

### Basic Usage

```bash
# Simple goal decomposition
aur goals "Implement OAuth2 authentication"

# With yes flag (skip prompts)
aur goals "Add caching layer" --yes
```

### With Context Files

```bash
# Provide context for better decomposition
aur goals "Optimize database queries" \
  --context src/database/queries.py \
  --context src/models/user.py \
  --context docs/performance.md
```

### Single Task (No Decomposition)

```bash
# Don't break down simple tasks
aur goals "Fix email validation regex" --no-decompose --yes
```

### Different Tools and Models

```bash
# Use Cursor with Opus model
aur goals "Complex system design" --tool cursor --model opus

# Use environment variable
export AURORA_GOALS_TOOL=windsurf
aur goals "Add feature"
```

### JSON Output for Automation

```bash
# Get JSON output for scripts
PLAN=$(aur goals "Deploy to staging" --format json --yes)
echo "$PLAN" | jq '.subgoals[].title'
```

### Verbose Mode

```bash
# See detailed progress
aur goals "Add user dashboard" --verbose
```

## Output

### Directory Structure

Creates:
```
.aurora/plans/NNNN-slug/
└── goals.json          # Subgoals with agent assignments
```

Where:
- `NNNN`: Sequential plan number (e.g., 0001, 0002)
- `slug`: URL-friendly version of goal title (e.g., `add-oauth2`)

### goals.json Format

```json
{
  "id": "0001-add-oauth2",
  "title": "Implement OAuth2 authentication",
  "created_at": "2026-01-10T12:00:00Z",
  "status": "ready_for_planning",
  "memory_context": [
    {"file": "src/auth/login.py", "relevance": 0.85}
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Implement OAuth provider integration",
      "description": "Add Google/GitHub OAuth providers",
      "agent": "@code-developer",
      "confidence": 0.85,
      "dependencies": []
    }
  ],
  "gaps": []
}
```

See [examples/goals/](../../examples/goals/) for complete examples.

## Workflow Integration

### Step 1: Create Goals (Terminal)

```bash
aur goals "Implement OAuth2 authentication"
```

Output:
- Creates `.aurora/plans/0001-add-oauth2/goals.json`
- Shows subgoals with agent assignments
- Reports any agent capability gaps

### Step 2: Generate PRD (Claude Code)

```bash
cd .aurora/plans/0001-add-oauth2/
/plan
```

Reads `goals.json` and creates:
- `prd.md` - Product Requirements Document
- `tasks.md` - Task list with agent metadata
- `specs/` - Detailed specifications

### Step 3: Execute Tasks

**Option A - Sequential**:
```bash
aur implement
```

**Option B - Parallel**:
```bash
aur spawn tasks.md
```

See [Planning Flow](../workflows/planning-flow.md) for complete workflow documentation.

## Configuration

### Environment Variables

```bash
# Set default tool
export AURORA_GOALS_TOOL=claude

# Set default model
export AURORA_GOALS_MODEL=opus
```

### Config File

Add to `.aurora/config.toml`:

```toml
[goals]
default_tool = "claude"
default_model = "sonnet"
```

### Resolution Order

Both tool and model follow this resolution order:
1. CLI flag (`--tool`, `--model`)
2. Environment variable (`AURORA_GOALS_TOOL`, `AURORA_GOALS_MODEL`)
3. Config file (`goals_default_tool`, `goals_default_model`)
4. Default (`"claude"`, `"sonnet"`)

## How It Works

### Architecture

Uses SOAROrchestrator with `stop_after_verify=True`:

```
┌─────────────┐     ┌─────────────┐
│  aur goals  │     │  aur soar   │
│  (CLI)      │     │  (CLI)      │
└──────┬──────┘     └──────┬──────┘
       │                   │
       ▼                   ▼
┌────────────────────────────────────┐
│        SOAROrchestrator            │
├────────────────────────────────────┤
│ Phase 1: Memory (ACT-R search)     │
│ Phase 2: Search (context)          │
│ Phase 3: Decompose (LLM)           │
│ Phase 4: Verify (validate plan)    │
├────────────────────────────────────┤
│ Phase 5: Assign (agents)     ←── aur goals stops here
│ Phase 6: Collect (execute)   ←── aur soar continues
│ Phase 7: Synthesize (answer) │
└────────────────────────────────────┘
```

### 1. Memory Search (Phase 1-2)

Searches indexed codebase for relevant context using complexity-based retrieval budgets.

**Complexity-Based Retrieval:**

| Complexity | Code Chunks | KB Chunks | Total Retrieved | Context Limit |
|------------|-------------|-----------|-----------------|---------------|
| SIMPLE     | 3           | 2         | 5               | skip          |
| MEDIUM     | 5           | 5         | 10              | 5 code, 8 total |
| COMPLEX    | 7           | 8         | 15              | 7 code, 12 total |
| CRITICAL   | 10          | 10        | 20              | 10 code, 15 total |

**Type-Aware Retrieval:** Queries code and KB (knowledge base) chunks separately to ensure both types are represented.

### 2. Goal Decomposition (Phase 3)

Uses LLM to break down the goal with complexity-aware constraints.

**Complexity-Based Decomposition (v0.10.0):**

| Complexity | Few-Shot Examples | Max Subgoals | Execution Preference |
|------------|-------------------|--------------|----------------------|
| SIMPLE     | 0                 | 0 (bypass)   | skip                 |
| MEDIUM     | 1                 | 2            | sequential           |
| COMPLEX    | 1                 | 5            | mixed                |
| CRITICAL   | 2                 | 8            | parallel             |

**Optimization:**
- Reduced few-shot examples (50% reduction for COMPLEX/CRITICAL)
- Explicit subgoal limits in LLM prompt with enforcement rules
- Execution preferences guide parallelization strategy
- Chunk deduplication reduces context redundancy

**Result:** MEDIUM goals now generate 2 focused subgoals instead of 7 (71% reduction).

### 3. Plan Verification (Phase 4)

Validates decomposition quality using `verify_lite()` with complexity-based enforcement.

**Verification Checks:**
1. Structural validation (required fields, valid dependencies)
2. **Subgoal count enforcement** - Rejects decompositions exceeding complexity limits
3. Agent assignment and capability matching
4. Circular dependency detection

**Subgoal Limits:**

| Complexity | Max Allowed | Action if Exceeded |
|------------|-------------|-------------------|
| MEDIUM     | 2           | FAIL → Retry with feedback |
| COMPLEX    | 5           | FAIL → Retry with feedback |
| CRITICAL   | 8           | FAIL → Retry with feedback |

**Auto-Retry:** Verification failures trigger automatic retry with specific feedback to guide LLM toward consolidation.

### 4. Agent Matching (Phase 5)

3-tier LLM-based agent matching:

| Tier | Confidence | Behavior |
|------|------------|----------|
| **Excellent** | > 0.7 | Direct assignment, high fit |
| **Acceptable** | 0.5-0.7 | Assignment with note |
| **Insufficient** | < 0.5 | Gap reported, fallback used |

Matching process:
- **LLM Analysis**: Evaluates task requirements vs agent capabilities
- **Confidence Scoring**: Returns match quality tier
- **Gap Detection**: Reports missing agent capabilities

### 5. User Review

Allows you to review and edit:
- Opens goals.json in `$EDITOR` (default: nano)
- Waits for confirmation
- Can abort before saving

Skip with `--yes` flag.

## Cache System

`aur goals` shares the same **3-layer cache architecture** as `aur soar` to avoid redundant decompositions.

### Cache Layers

**1. In-Memory SOAR Cache**
- **Key**: SHA256(`query|complexity`)
- **Lifetime**: Current session
- **Speed**: <1ms

**2. goals.json File Cache**
- **Key**: Normalized query string (lowercase + whitespace collapsed)
- **Lifetime**: Persistent
- **Speed**: ~50ms
- **Match**: Exact after normalization

Example:
```
Query: "Implement OAuth2  Authentication"
Normalized: "implement oauth2 authentication"

goals.json title: "implement oauth2 authentication" → MATCH
goals.json title: "implement oauth authentication" → NO MATCH
```

**3. Conversation Log Cache**
- **Key**: Hybrid score (BM25 + Activation + Semantic)
- **Threshold**: 0.90
- **Lifetime**: Persistent
- **Speed**: ~100ms
- **Match**: Fuzzy semantic matching

### Cache Display

**v0.10.0 - Unified indicators:**
```bash
Phase 3: ✓ 2 subgoals loaded  # In-memory or file cache

✓ Using cached decomposition from goals.json (use --no-cache for fresh)
✓ Using cached decomposition from previous SOAR conversation (use --no-cache for fresh)
```

**No duplicate messages** - consolidated into single source-attributed indicator.

### Cache Invalidation

```bash
# Force fresh decomposition
aur goals "goal" --no-cache

# Manual clearing
rm -rf .aurora/plans/active/*           # Clear goals.json cache
rm -rf .aurora/logs/conversations/*     # Clear conversation cache
```

### Performance Impact

| Scenario | First Run | Cached Run | Savings |
|----------|-----------|------------|---------|
| MEDIUM goal | 8-12s | <1ms (in-memory) | ~8-12s |
| COMPLEX goal | 15-25s | 50ms (goals.json) | ~15-25s |

## Agent Capabilities

Common agents and their specializations:

| Agent | Best For |
|-------|----------|
| `@code-developer` | General development, APIs, full-stack |
| `@quality-assurance` | Testing, quality assurance, test design |
| `@ui-designer` | UI/UX, design, frontend specs |
| `@system-architect` | System design, architecture decisions |
| `@feature-planner` | Requirements, PRDs, feature specs |
| `@market-researcher` | Research, analysis, documentation |

### Agent Gaps

When no suitable agent found (confidence < 0.5):

```json
{
  "gaps": [
    {
      "subgoal_id": "sg-3",
      "suggested_capabilities": ["blockchain", "web3"],
      "fallback": "@code-developer"
    }
  ]
}
```

**Options**:
1. Accept fallback agent
2. Create custom agent with suggested capabilities
3. Refine subgoal description

## Troubleshooting

### Tool Not Found

**Error**: `CLI tool 'xyz' not found in PATH`

**Solutions**:
1. Install the tool: `npm install -g @anthropic/claude-cli`
2. Use a different tool: `--tool claude`
3. Check PATH: `which claude`

### Goal Too Short

**Error**: `String should have at least 10 characters`

**Solution**: Provide more descriptive goal (minimum 10 characters)

### No Memory Context

**Warning**: `No relevant context found in memory`

**Solution**: Index your codebase:
```bash
aur mem index .
```

### Validation Error

**Error**: `List should have at least 1 item after validation`

**Cause**: Goal decomposition resulted in empty subgoals list

**Solutions**:
1. Retry the command
2. Provide context files with `--context`
3. Use `--verbose` to see decomposition details

### Directory Already Exists

If plan directory exists, goal creation fails.

**Solutions**:
1. Use a different goal title
2. Archive existing plan: `aur plan archive NNNN-slug`
3. Delete existing directory manually

## Performance

### Typical Execution Time

- **Simple goal** (1-2 subgoals): 5-10 seconds
- **Moderate goal** (3-5 subgoals): 10-20 seconds
- **Complex goal** (5-7 subgoals): 20-30 seconds

Time includes:
- Memory search
- LLM decomposition
- Agent matching
- User review (if not using `--yes`)

### Optimization Tips

1. **Use `--yes`** for automation to skip review
2. **Provide `--context`** files to improve decomposition quality
3. **Use `--no-decompose`** for simple single-task goals
4. **Index memory** regularly for faster context search

## Exit Codes

- `0`: Success
- `1`: Error (validation, tool not found, etc.)

## Recent Changes

### v0.10.0 - Decomposition Optimization & Cache Improvements

**Complexity-Based Configuration:**
- Reduced few-shot examples: COMPLEX 2→1, CRITICAL 3→2 (50% reduction)
- Complexity-based retrieval budgets: MEDIUM 5+5=10, COMPLEX 7+8=15, CRITICAL 10+10=20
- Complexity-based context limits to optimize LLM context window usage

**Subgoal Enforcement:**
- `verify_lite()` enforces complexity-based subgoal limits
- MEDIUM=2, COMPLEX=5, CRITICAL=8 max subgoals
- Auto-retry with feedback when limits exceeded
- **Result**: MEDIUM goals now generate 2 subgoals instead of 7 (71% reduction)

**Cache System Improvements:**
- 3-layer cache (in-memory, goals.json, conversation logs) now documented
- Unified cache display with source attribution
- No more duplicate cache messages
- Clear indicators: "from goals.json" vs "from previous SOAR conversation"

**Context Optimization:**
- Chunk deduplication by file_path reduces redundancy
- Explicit execution preferences in prompts (sequential/mixed/parallel)
- Consolidation guidance for LLM

**Shared Infrastructure:**
- Same SOAROrchestrator as `aur soar` (phases 1-4)
- Same cache layers and matching mechanisms
- Consistent decomposition quality

## See Also

- [aur soar Command](./aur-soar.md) - Full SOAR pipeline (shares phases 1-4 with aur goals)
- [aur spawn Command](./aur-spawn.md) - Parallel task execution (shares spawner with aur soar)
- [Planning Flow Workflow](../workflows/planning-flow.md)
- [Example goals.json Files](../../examples/goals/)
- [aur implement Command](./aur-implement.md)
- [Agent System Documentation](../agents/README.md)

## Version

Added in Aurora v1.0.0 (PRD-0026 Sprint 4)
