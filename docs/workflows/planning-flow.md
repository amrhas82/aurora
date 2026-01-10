# Planning Flow

This document describes the complete planning workflow in Aurora, from high-level goal to implementation.

## Overview

Aurora's planning flow consists of three stages:

1. **Goal Decomposition** (`aur goals`) - Break down high-level goals into subgoals with agent assignments
2. **PRD Generation** (`/plan` skill in Claude Code) - Create detailed requirements and task lists
3. **Execution** (`aur implement` or `aur spawn`) - Execute tasks sequentially or in parallel

## Step 1: Create Goals (Terminal)

Use `aur goals` to decompose a high-level goal into subgoals with recommended agent assignments.

```bash
aur goals "Implement OAuth2 authentication with JWT tokens"
```

### What Happens

1. **Memory Search**: Aurora searches indexed codebase for relevant context
2. **Goal Decomposition**: LLM breaks down the goal into 2-7 concrete subgoals
3. **Agent Matching**: Each subgoal gets a recommended agent based on capabilities
4. **Gap Detection**: Identifies missing agent capabilities
5. **User Review**: Opens goals.json in your editor for review (skip with `--yes`)

### Output

Creates directory structure:

```
.aurora/plans/0001-add-oauth2/
└── goals.json          # Subgoals with agent assignments
```

### goals.json Format

```json
{
  "id": "0001-add-oauth2",
  "title": "Implement OAuth2 authentication with JWT tokens",
  "created_at": "2026-01-10T12:00:00Z",
  "status": "ready_for_planning",
  "memory_context": [
    {"file": "src/auth/login.py", "relevance": 0.85},
    {"file": "docs/auth-design.md", "relevance": 0.72}
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Implement OAuth provider integration",
      "description": "Add Google/GitHub OAuth providers with callback handling",
      "agent": "@full-stack-dev",
      "confidence": 0.85,
      "dependencies": []
    },
    {
      "id": "sg-2",
      "title": "Implement JWT token generation and validation",
      "description": "Create JWT utilities for token lifecycle management",
      "agent": "@full-stack-dev",
      "confidence": 0.90,
      "dependencies": ["sg-1"]
    },
    {
      "id": "sg-3",
      "title": "Write OAuth integration tests",
      "description": "Test OAuth flow end-to-end including token refresh",
      "agent": "@qa-test-architect",
      "confidence": 0.92,
      "dependencies": ["sg-1", "sg-2"]
    }
  ],
  "gaps": []
}
```

### Command Options

```bash
# With context files for better decomposition
aur goals "Add caching layer" --context src/api.py --context src/config.py

# Skip decomposition (single task)
aur goals "Fix bug in login form" --no-decompose

# Use different LLM tool
aur goals "Add metrics dashboard" --tool cursor --model opus

# Non-interactive mode
aur goals "Implement feature X" --yes

# JSON output (for programmatic use)
aur goals "Implement feature X" --format json
```

## Step 2: Generate PRD and Tasks (Claude Code)

**Note**: The `/plan` skill needs to be created in your Claude Code environment to read goals.json.

Navigate to the plan directory and run `/plan` in Claude Code:

```bash
cd .aurora/plans/0001-add-oauth2/
# In Claude Code terminal:
/plan
```

### What Happens

The `/plan` skill reads `goals.json` and generates:

1. **prd.md** - Product Requirements Document with:
   - Goal overview
   - Success criteria
   - Technical requirements
   - Acceptance criteria per subgoal

2. **tasks.md** - Implementation task list with:
   - Tasks for each subgoal
   - Agent metadata comments: `<!-- agent: @agent-id -->`
   - Dependencies between tasks
   - Verification steps

3. **specs/** - Detailed specifications:
   - API specifications
   - Data schemas
   - Authentication flows
   - Testing requirements

### Output Structure

```
.aurora/plans/0001-add-oauth2/
├── goals.json          # Created by: aur goals
├── prd.md              # Created by: /plan
├── tasks.md            # Created by: /plan
├── specs/              # Created by: /plan
│   ├── 0001-add-oauth2-api.md
│   ├── 0001-add-oauth2-auth-flow.md
│   ├── 0001-add-oauth2-schemas.md
│   └── 0001-add-oauth2-testing.md
└── agents.json         # Optional: Agent execution metadata
```

### tasks.md Format

```markdown
# Tasks: Implement OAuth2 authentication with JWT tokens

## sg-1: Implement OAuth provider integration
<!-- agent: @full-stack-dev -->
- [ ] 1.1 Create OAuth provider configuration
  - Add Google OAuth client credentials
  - Add GitHub OAuth app credentials
  - Configure callback URLs
- [ ] 1.2 Implement OAuth callback handler
  - Parse authorization code
  - Exchange code for access token
  - Store user OAuth profile

## sg-2: Implement JWT token generation and validation
<!-- agent: @full-stack-dev -->
<!-- depends: sg-1 -->
- [ ] 2.1 Create JWT utilities
  - Generate access tokens (15 min expiry)
  - Generate refresh tokens (7 day expiry)
  - Validate token signatures
- [ ] 2.2 Add token refresh endpoint
  - Accept refresh token
  - Validate and issue new access token

## sg-3: Write OAuth integration tests
<!-- agent: @qa-test-architect -->
<!-- depends: sg-1, sg-2 -->
- [ ] 3.1 Test OAuth authorization flow
  - Test Google OAuth flow
  - Test GitHub OAuth flow
  - Test callback error handling
- [ ] 3.2 Test JWT token lifecycle
  - Test token generation
  - Test token validation
  - Test token refresh
```

## Step 3: Execute Tasks

You have two options for executing tasks:

### Path A: Sequential Execution in Claude Code

Use `aur implement` to execute tasks one at a time in Claude Code:

```bash
cd .aurora/plans/0001-add-oauth2/
aur implement
```

**Behavior**:
- Reads `tasks.md` and executes tasks sequentially
- Respects agent assignments and dependencies
- Asks for confirmation after each task
- Marks tasks complete with `[x]`
- Commits changes after each task

**Best for**:
- Complex tasks requiring iteration
- Tasks needing human oversight
- Learning/understanding the codebase

### Path B: Parallel Execution from Terminal

Use `aur spawn` to spawn parallel agent instances:

```bash
cd .aurora/plans/0001-add-oauth2/
aur spawn tasks.md
```

**Behavior**:
- Parses agent metadata from task comments
- Spawns independent agent processes per task
- Executes tasks in parallel (respecting dependencies)
- Faster for independent tasks

**Best for**:
- Independent tasks that can run in parallel
- Large batch operations
- Time-sensitive deliverables

## Workflow Examples

### Example 1: Simple Bug Fix

```bash
# Step 1: Create goals (single task, no decomposition)
aur goals "Fix validation bug in user registration" --no-decompose --yes

# Step 2: Generate PRD (if needed)
cd .aurora/plans/0001-fix-validation-bug/
/plan  # In Claude Code

# Step 3: Execute
aur implement
```

### Example 2: Complex Feature

```bash
# Step 1: Create goals with decomposition
aur goals "Implement real-time notifications system"

# Review and edit goals.json
cat .aurora/plans/0001-notifications/goals.json
nano .aurora/plans/0001-notifications/goals.json

# Step 2: Generate PRD and tasks
cd .aurora/plans/0001-notifications/
/plan  # In Claude Code

# Step 3: Parallel execution for speed
aur spawn tasks.md
```

### Example 3: With Context Files

```bash
# Step 1: Provide context for better decomposition
aur goals "Optimize database queries" \
  --context src/database/queries.py \
  --context src/models/user.py \
  --context docs/performance-reqs.md

# Step 2 & 3: Continue as usual
cd .aurora/plans/0001-optimize-database/
/plan
aur implement
```

## Agent Capabilities

Aurora includes several specialized agents:

| Agent ID | Capabilities | When to Use |
|----------|--------------|-------------|
| `@full-stack-dev` | General development, API, frontend, backend | Most implementation tasks |
| `@qa-test-architect` | Testing, quality assurance, test design | Test writing, quality gates |
| `@ux-expert` | UI/UX, design, frontend specs | Interface design, user flows |
| `@holistic-architect` | System design, architecture decisions | Architecture, tech selection |
| `@product-manager` | Requirements, PRDs, feature specs | Product planning, requirements |
| `@business-analyst` | Research, analysis, documentation | Research, competitive analysis |

## Agent Gaps

When Aurora cannot find a suitable agent for a subgoal, it reports a **gap**:

```json
{
  "gaps": [
    {
      "subgoal_id": "sg-3",
      "suggested_capabilities": ["blockchain", "web3", "smart-contracts"],
      "fallback": "@full-stack-dev"
    }
  ]
}
```

**What to do**:
1. Accept the fallback agent
2. Create a custom agent with the suggested capabilities
3. Refine the subgoal to use existing agent capabilities

## Configuration

### Environment Variables

```bash
# Override default LLM tool for aur goals
export AURORA_GOALS_TOOL=cursor

# Override default model
export AURORA_GOALS_MODEL=opus
```

### Config File

Add to `.aurora/config.toml`:

```toml
[goals]
default_tool = "claude"
default_model = "sonnet"
```

## Troubleshooting

### goals.json validation error

**Error**: "String should have at least 10 characters"

**Solution**: Ensure goal description is descriptive (min 10 chars)

### No agents found

**Error**: "No agents available for matching"

**Solution**: Run `aur init` to set up agent manifests

### Memory search finds no context

**Warning**: "No relevant context found in memory"

**Solution**: Run `aur mem index .` to index your codebase

### CLI tool not found

**Error**: "CLI tool 'xyz' not found in PATH"

**Solution**: Install the tool or specify a different one with `--tool`

## Advanced Usage

### Custom Agent Assignment

Edit `goals.json` after generation to assign different agents:

```bash
aur goals "Implement feature X"
cd .aurora/plans/0001-feature-x/
nano goals.json  # Modify agent assignments
```

### Reusing Goals

Archive completed plans and reuse goal patterns:

```bash
# Archive completed plan
aur plan archive 0001-add-oauth2

# List archived plans for reference
aur plan list --archive
```

### Integration with CI/CD

Use JSON output for programmatic workflow integration:

```bash
# Generate goals as JSON
PLAN_DATA=$(aur goals "Deploy to staging" --format json --yes)

# Parse and trigger CI/CD pipeline
echo "$PLAN_DATA" | jq '.subgoals[].title' | xargs -I {} ./trigger-ci.sh {}
```

## See Also

- [aur goals command reference](../commands/aur-goals.md)
- [aur implement command reference](../commands/aur-implement.md)
- [aur spawn command reference](../commands/aur-spawn.md)
- [Agent system documentation](../agents/README.md)
- [Example goals.json files](../../examples/goals/)
