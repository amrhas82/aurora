# aur soar

Execute 9-phase SOAR (System for Orchestrated Analytical Reasoning) queries with terminal orchestration.

## Synopsis

```bash
aur soar [OPTIONS] QUERY
```

## Description

The `aur soar` command implements Aurora's 9-phase SOAR pipeline for complex query processing. It combines systematic reasoning, agent orchestration, and parallel research execution to provide well-researched, synthesized answers.

**Shared Infrastructure**:
- **Phases 1-5**: SOAROrchestrator shared with `aur goals` (with `stop_after_verify=True`)
- **Phase 6**: Uses `spawn_parallel_tracked()` shared with `aur spawn`

SOAR is designed for queries that require:
- Breaking down complex problems into subgoals
- Coordinating multiple research agents
- Combining findings from parallel investigations
- Providing traceable, high-confidence answers

## Usage

### Basic Usage

```bash
# Simple query
aur soar "What is SOAR orchestrator?"

# Complex research query
aur soar "Compare React, Vue, and Angular for enterprise apps"

# With specific model
aur soar "Explain microservices architecture" --model opus

# With verbose output
aur soar "State of AI in 2025" --verbose
```

## SOAR Pipeline (9 Phases)

### Phase 1: ASSESS (Orchestrator)
Analyzes query complexity using keyword-based classification (96% accuracy) with LLM fallback for borderline cases.

**Complexity Levels:**
- **SIMPLE**: Single-step queries, lookups, definitions (score ≤ 11)
- **MEDIUM**: Multi-step reasoning, moderate analysis (score 12-28)
- **COMPLEX**: Multi-agent coordination, deep analysis (score ≥ 29)
- **CRITICAL**: High-stakes, security-critical queries

### Phase 2: RETRIEVE (Orchestrator)
Queries memory index for relevant context using semantic search and hybrid retrieval.

### Phase 3: DECOMPOSE (LLM)
Breaks complex queries into manageable subgoals with clear success criteria.

**Example:**
```
Query: "Compare React, Vue, and Angular"

Subgoals:
1. Analyze React ecosystem and key features
2. Analyze Vue ecosystem and key features
3. Analyze Angular ecosystem and key features
4. Compare performance characteristics
5. Compare learning curves and developer experience
```

### Phase 4: VERIFY (LLM)
Validates decomposition quality with devil's advocate review (scores 0.6-1.0).

### Phase 5: ROUTE (Orchestrator)
Assigns agents to subgoals based on capabilities and creates execution plan.

**Execution Strategies:**
- **Parallel**: Independent subgoals execute concurrently
- **Sequential**: Dependent subgoals execute in order
- **Mixed**: Phases combine parallel and sequential execution

### Phase 6: COLLECT (LLM) - **Parallel Research + Early Failure Detection**
Executes agents to research subgoals, using parallel spawning and early failure detection.

**Shared Infrastructure**: Uses `spawn_parallel_tracked()` from `aurora_spawner` - the same mature spawning infrastructure as `aur spawn`. This ensures consistent behavior for stagger delays, heartbeat monitoring, circuit breaker protection, and timeout policies.

**Parallel Execution:**
- Max 4 concurrent agent spawns (configurable)
- 5s stagger delay between spawns (prevents API rate limits)
- Independent subgoals run simultaneously
- Reduces total research time by 2-4x
- Graceful failure handling with LLM fallback

**Early Failure Detection:**
- Non-blocking health checks every 2s
- Detects failures in 5-15s (vs 60-300s timeout)
- Stall detection: 15s no-output after 100 bytes (2 checks)
- Pattern matching: rate limits, auth, API errors
- Immediate circuit breaker updates
- Detailed termination logging with detection times

**Example Parallel Flow:**
```
Phase 6.1: Parallel Research (3 agents)
├─ Agent 1: Research React    ┐
├─ Agent 2: Research Vue      ├─ Parallel (with early detection)
└─ Agent 3: Research Angular  ┘

Phase 6.2: Sequential Analysis
└─ Agent 4: Compare performance (depends on 1,2,3)
```

### Phase 7: SYNTHESIZE (LLM)
Combines agent findings into coherent answer with traceability and confidence scoring.

### Phase 8: RECORD (Orchestrator)
Caches reasoning patterns for future similar queries.

### Phase 9: RESPOND (LLM)
Formats final answer with proper structure and citations.

## Options

### `QUERY`

The query string (required)

```bash
aur soar "Your query here"
```

### `--model`, `-m`

Model to use (default: `sonnet`)

**Options:**
- `sonnet` - Claude Sonnet 3.5 (faster, cost-effective)
- `opus` - Claude Opus 3 (higher quality, slower)

```bash
aur soar "Complex query" --model opus
aur soar "Simple query" -m sonnet
```

### `--tool`, `-t`

CLI tool to pipe to (default: `claude` or `AURORA_SOAR_TOOL` env var)

```bash
aur soar "Query" --tool cursor
aur soar "Query" -t windsurf
```

**Available Tools:**
- `claude` - Claude CLI
- `cursor` - Cursor AI
- `windsurf` - Windsurf AI
- Any CLI tool that accepts piped input

### `--verbose`, `-v`

Show verbose output with phase details

```bash
aur soar "Query" --verbose
```

**Verbose Output Includes:**
- Phase transitions
- Complexity assessment details
- Agent assignments
- Parallel execution logging
- Timing information
- Confidence scores

### `--early-detection-interval`

Check interval for early failure detection in seconds (default: 2.0)

```bash
aur soar "Query" --early-detection-interval 1.0
```

### `--early-detection-stall-threshold`

Stall threshold for early detection in seconds (default: 15.0)

```bash
aur soar "Query" --early-detection-stall-threshold 10.0
```

### `--early-detection-min-output`

Minimum output bytes before stall check (default: 100)

```bash
aur soar "Query" --early-detection-min-output 50
```

### `--disable-early-detection`

Disable early failure detection (use full timeout)

```bash
aur soar "Query" --disable-early-detection
```

## Parallel Research

SOAR automatically uses parallel research for complex queries with independent subgoals.

### When Parallel Execution is Used

**Automatically triggered when:**
1. Query assessed as COMPLEX (score ≥ 29)
2. Decomposition produces ≥ 2 independent subgoals
3. Route phase identifies parallelizable subgoals

**Example Queries:**
```bash
# Comparison queries (3+ parallel agents)
aur soar "Compare PostgreSQL, MySQL, and MongoDB"

# Multi-aspect analysis (parallel research)
aur soar "Analyze pros and cons of microservices"

# Comprehensive research (parallel + sequential)
aur soar "Best practices for React + TypeScript projects"
```

### Performance Improvements

**Benchmarks:**

```
Query: "Compare React, Vue, and Angular"
├─ Sequential: 45.2s (3 agents × 15s each)
└─ Parallel:   18.1s (3 agents concurrent)
    Speedup:   2.5x

Query: "Analyze microservices vs monolith vs serverless"
├─ Sequential: 67.8s (5 agents)
└─ Parallel:   22.4s (5 agents, max 5 concurrent)
    Speedup:   3.0x
```

**Factors Affecting Speedup:**
- Number of independent subgoals
- Agent execution time variability
- LLM API rate limits
- Network latency

### Parallel Execution Details

**Implementation:**
- Max concurrent spawns: 4 (semaphore limited)
- Stagger delay: 5s between agent starts
- Per-agent timeout: 600s max (patient policy, progressive)
- Graceful failure handling per agent

**Global Timeout Calculation:**

Global timeout accounts for concurrency waves since only 4 agents run simultaneously:

```
num_waves = ceil(num_agents / 4)
stagger = (num_agents - 1) × 5s
global_timeout = (num_waves × 600) + stagger + 120s buffer
```

| Agents | Waves | Stagger | Global Timeout |
|--------|-------|---------|----------------|
| 4      | 1     | 15s     | 735s (~12 min) |
| 6      | 2     | 25s     | 1345s (~22 min) |
| 8      | 2     | 35s     | 1355s (~23 min) |
| 12     | 3     | 55s     | 1975s (~33 min) |

## Examples

### Example 1: Simple Query

```bash
aur soar "What is SOAR orchestrator?"
```

**Expected Flow:**
```
Phase 1: ASSESS    → SIMPLE (score: 8)
Phase 2: RETRIEVE  → 0 chunks
Phase 9: RESPOND   → Direct answer
```

### Example 1b: Fast Failure Detection

```bash
# Aggressive early detection for development
aur soar "Complex query" \
  --early-detection-interval 1.0 \
  --early-detection-stall-threshold 10.0 \
  --early-detection-min-output 50
```

**Use case:** Development environment where you want to fail fast on stalled agents.

### Example 2: Complex Research Query

```bash
aur soar "Compare React, Vue, and Angular for enterprise apps" --verbose
```

**Expected Flow:**
```
Phase 1: ASSESS    → COMPLEX (score: 35)
Phase 2: RETRIEVE  → 12 chunks matched
Phase 3: DECOMPOSE → 5 subgoals identified
Phase 4: VERIFY    → PASS (score: 0.85)
Phase 5: ROUTE     → 3 agents assigned
Phase 6: COLLECT   → Parallel execution (3 concurrent)
  ├─ Agent 1: Research React     [8.2s]
  ├─ Agent 2: Research Vue        [7.9s]
  └─ Agent 3: Research Angular    [9.1s]
Phase 7: SYNTHESIZE → Combined findings (confidence: 0.92)
Phase 8: RECORD    → Pattern cached
Phase 9: RESPOND   → Formatted answer

Completed in 23.4s
```

### Example 3: With Specific Model

```bash
aur soar "Explain quantum computing for beginners" --model opus
```

Uses Claude Opus for higher quality decomposition and synthesis.

### Example 4: Multi-Tool Chain

```bash
# Generate task list with SOAR
aur soar "Plan tasks for implementing user auth" > auth-tasks.md

# Execute tasks with spawn
aur spawn auth-tasks.md --parallel
```

## Environment Variables

### `AURORA_SOAR_TOOL`

Default CLI tool to use (default: `claude`)

```bash
export AURORA_SOAR_TOOL=cursor
aur soar "Query"  # Uses cursor
```

### `AURORA_SOAR_MODEL`

Default model to use (default: `sonnet`)

```bash
export AURORA_SOAR_MODEL=opus
aur soar "Query"  # Uses opus
```

## Configuration

### Config File

Located at `~/.aurora/config.json`:

```json
{
  "soar": {
    "default_tool": "claude",
    "default_model": "sonnet",
    "max_concurrent_agents": 5,
    "agent_timeout_seconds": 300,
    "enable_early_failure_detection": true,
    "timeout_policy": "default"
  }
}
```

**Update config:**
```bash
aur init --config
```

### Early Failure Detection Configuration

Configure early detection behavior for faster failure recovery:

**Full Configuration:**
```json
{
  "soar": {
    "agent_timeout_seconds": 300,
    "enable_early_failure_detection": true,
    "timeout_policy": "default",
    "early_detection": {
      "enabled": true,
      "check_interval": 2.0,
      "stall_threshold": 15.0,
      "min_output_bytes": 100,
      "stderr_pattern_check": true,
      "memory_limit_mb": null
    }
  }
}
```

**Early Detection Options:**
- `enabled` - Enable/disable early detection (default: `true`)
- `check_interval` - Health check interval in seconds (default: `2.0`)
- `stall_threshold` - No-output threshold in seconds (default: `15.0`)
- `min_output_bytes` - Min bytes before stall check (default: `100`)
- `stderr_pattern_check` - Enable pattern matching (default: `true`)

**Timeout Policies** (spawner-level):
```json
{
  "timeout_policy": "default"    // 60s initial, 300s max, 30s no-activity
  "timeout_policy": "patient"    // 120s initial, 600s max, 120s no-activity
  "timeout_policy": "fast_fail"  // 60s fixed, 15s no-activity
}
```

**Error Patterns Detected:**
- Rate limits: `429`, `rate limit exceeded`, `quota exceeded`
- Auth: `invalid api key`, `authentication failed`, `unauthorized`
- API: `API error`, `model not available`, `connection refused`
- Stalls: No output for 15s+ (2 consecutive checks)

**Monitoring Early Failures:**

```bash
# Real-time early termination detection
aur soar "query" --verbose 2>&1 | grep -i "early termination"

# Watch health check activity
aur soar "query" --verbose 2>&1 | grep "Health check"

# View stall detections
aur soar "query" --verbose 2>&1 | grep "Stall detected"

# Analyze detection metrics from logs
cat .aurora/logs/soar-*.log | jq '.early_termination_details[] | {
  agent: .agent_id,
  reason: .reason,
  detection_time: .detection_time,
  stdout_size: .stdout_size,
  time_since_activity: .time_since_activity
}'

# Check recovery metrics
cat .aurora/logs/soar-*.log | jq '.recovery_metrics'

# Count early terminations by reason
cat .aurora/logs/soar-*.log | jq -r '.early_termination_details[].reason' | sort | uniq -c
```

**Tuning for Your Use Case:**

**Fast failure detection (development):**
```json
{
  "early_detection": {
    "check_interval": 1.0,
    "stall_threshold": 10.0,
    "min_output_bytes": 50
  },
  "timeout_policy": "fast_fail"
}
```

**Patient detection (production):**
```json
{
  "early_detection": {
    "check_interval": 5.0,
    "stall_threshold": 30.0,
    "min_output_bytes": 200
  },
  "timeout_policy": "patient"
}
```

**Disable early detection:**
```json
{
  "enable_early_failure_detection": false
}
```

### Agent Discovery

SOAR automatically discovers agents from:
- `~/.aurora/agents/` (global agents)
- `./.aurora/agents/` (project agents)
- Agent manifests in current project

**List discovered agents:**
```bash
aur agents list
```

## Output Format

### Standard Output

```
[Aurora SOAR]
Query: "Compare React, Vue, and Angular"
Tool: claude

[ORCHESTRATOR] Phase 1: Assess
  Complexity: COMPLEX

[ORCHESTRATOR] Phase 2: Retrieve
  Matched: 12 chunks from memory

[LLM → claude] Phase 3: Decompose
  ✓ 5 subgoals identified

[LLM → claude] Phase 4: Verify
  ✓ PASS

[ORCHESTRATOR] Phase 5: Route
  Assigned: agent1, agent2, agent3

[LLM → claude] Phase 6: Collect
  ✓ Research complete (5 findings)

[LLM → claude] Phase 7: Synthesize
  ✓ Answer ready (confidence: 92%)

[ORCHESTRATOR] Phase 8: Record
  ✓ Pattern cached

[LLM → claude] Phase 9: Respond
  ✓ Response formatted

[Final Answer]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
... synthesized answer ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Completed in 23.4s
Log: ~/.aurora/soar/query-20250110-143022.log
```

### Logs

Detailed logs saved to `~/.aurora/soar/`:

```bash
# View recent logs
ls -lt ~/.aurora/soar/*.log | head -5

# Check parallel execution in logs
grep -i "parallel" ~/.aurora/soar/*.log | tail -10
```

## Performance

### Complexity Assessment

- **Keyword classification**: <1ms (60-70% of queries)
- **LLM verification**: ~200ms (30-40% of queries)
- **Average**: <100ms per assessment

### Query Execution

| Complexity | Typical Time | Phases Used |
|------------|--------------|-------------|
| SIMPLE     | 2-5s         | 1, 2, 9     |
| MEDIUM     | 10-20s       | 1-9 (sequential) |
| COMPLEX    | 20-40s       | 1-9 (parallel) |
| CRITICAL   | 40-90s       | 1-9 (parallel + verification) |

### Parallel Speedup

- **3 subgoals**: 2.0-2.5x faster
- **5 subgoals**: 2.5-3.5x faster
- **8+ subgoals**: 3.0-4.5x faster (max_concurrent=5)

## Troubleshooting

### Problem: Tool not found

```
Error: Tool 'cursor' not found in PATH
```

**Solution:**
```bash
# Install tool or use different tool
aur soar "Query" --tool claude

# Check available tools
which claude cursor windsurf
```

### Problem: Low-quality decomposition

**Symptoms**: Too many/few subgoals, unclear goals

**Solutions:**
1. Use `--model opus` for better decomposition
2. Rephrase query to be more specific
3. Review logs for verification scores

### Problem: Verification failure

```
⚠️  PASS (marginal - score: 0.62)
└─ 3 concerns identified, 5 suggestions provided
```

**This is normal** - SOAR uses devil's advocate verification (0.6-0.7 = marginal pass).

**Actions:**
- Review concerns in logs
- Consider rephrasing query
- Use `--model opus` for critical queries

### Problem: Slow execution

**Check:**
1. Query complexity (use simpler query)
2. LLM API rate limits
3. Network latency
4. Number of subgoals

**Optimize:**
```bash
# Use faster model for simple queries
aur soar "Simple query" --model sonnet

# Check if parallel execution is used
aur soar "Complex query" --verbose | grep -i parallel
```

## Advanced Usage

### Custom Max Concurrent

Edit `packages/soar/src/aurora_soar/phases/collect.py`:

```python
# Line 252
spawn_results = await spawn_parallel(spawn_tasks, max_concurrent=10)
```

### Custom Agent Timeout

Edit `packages/soar/src/aurora_soar/phases/collect.py`:

```python
# Line 26-27
DEFAULT_AGENT_TIMEOUT = 120  # 2 minutes
DEFAULT_QUERY_TIMEOUT = 600  # 10 minutes
```

### Integration with Scripts

```bash
#!/bin/bash
# research.sh - Automated research pipeline

QUERY="$1"
OUTPUT="research-$(date +%Y%m%d-%H%M%S).md"

# Run SOAR and capture output
aur soar "$QUERY" --verbose > "$OUTPUT" 2>&1

# Check if successful
if [ $? -eq 0 ]; then
    echo "Research saved to $OUTPUT"
else
    echo "Research failed"
    exit 1
fi
```

## Comparison with Other Commands

### aur soar vs aur spawn

| Feature | soar | spawn |
|---------|------|-------|
| Purpose | Research queries | Execute tasks |
| Input | Natural language | Task file |
| Orchestration | Automatic | Manual |
| Parallelization | Automatic | Configurable |
| Synthesis | Yes | No |

**Use soar when:** You have a research question
**Use spawn when:** You have a defined task list

### Integration Example

```bash
# 1. Use soar to research and plan
aur soar "Plan implementation for user auth" > auth-plan.md

# 2. Convert plan to tasks
cat auth-plan.md | grep "^-" > auth-tasks.md

# 3. Execute tasks with spawn
aur spawn auth-tasks.md --parallel --verbose
```

## See Also

- [`aur spawn`](./aur-spawn.md) - Execute task files
- [`aur agents list`](./aur-agents.md) - List available agents
- [SOAR Architecture](../architecture/soar.md) - SOAR pipeline details
- [Spawner Package](../../packages/spawner/README.md) - Parallel spawning

## Source

- Command: `packages/cli/src/aurora_cli/commands/soar.py`
- Orchestrator: `packages/soar/src/aurora_soar/orchestrator.py`
- Phases: `packages/soar/src/aurora_soar/phases/`
- Tests: `packages/soar/tests/`
