# Goals JSON Format Examples

This directory contains example `goals.json` files created by the `aur goals` command.

## Format Specification

The `goals.json` format follows the specification from PRD-0026 (FR-6.2):

```json
{
  "id": "NNNN-slug",
  "title": "High-level goal description (10+ chars)",
  "created_at": "ISO 8601 timestamp",
  "status": "ready_for_planning",
  "memory_context": [
    {
      "file": "path/to/relevant/file.py",
      "relevance": 0.85
    }
  ],
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Subgoal title",
      "description": "Detailed description of what needs to be done",
      "agent": "@agent-id",
      "confidence": 0.85,
      "dependencies": ["sg-0"]
    }
  ],
  "gaps": [
    {
      "subgoal_id": "sg-3",
      "suggested_capabilities": ["capability1", "capability2"],
      "fallback": "@default-agent"
    }
  ]
}
```

## Field Descriptions

### Root Level

- **id**: Unique plan identifier in format `NNNN-slug` (e.g., `0001-add-oauth2`)
- **title**: Human-readable goal title (minimum 10 characters)
- **created_at**: ISO 8601 timestamp when goals were created
- **status**: Current status (always "ready_for_planning" after `aur goals`)
- **memory_context**: Array of relevant files found during memory search
- **subgoals**: Array of decomposed subgoals
- **gaps**: Array of detected agent capability gaps (empty if all agents found)

### Memory Context

- **file**: Relative path to relevant file from project root
- **relevance**: Relevance score from 0.0 to 1.0 (higher = more relevant)

### Subgoals

- **id**: Subgoal identifier in format `sg-N` (e.g., `sg-1`, `sg-2`)
- **title**: Brief, actionable subgoal title
- **description**: Detailed description of the subgoal including acceptance criteria
- **agent**: Recommended agent ID (e.g., `@full-stack-dev`, `@qa-test-architect`)
- **confidence**: Confidence score for agent match from 0.0 to 1.0
  - >= 0.5: Good match (agent capabilities align well)
  - < 0.5: Potential gap (may need custom agent or fallback)
- **dependencies**: Array of other subgoal IDs this depends on (e.g., `["sg-1", "sg-2"]`)

### Gaps

Reported when no suitable agent found (confidence < 0.5):

- **subgoal_id**: The subgoal lacking a good agent match
- **suggested_capabilities**: List of capabilities needed for this subgoal
- **fallback**: Default agent to use (typically `@full-stack-dev`)

## Validation Rules

The `Goals` Pydantic model enforces these constraints:

1. **title**: Minimum 10 characters
2. **subgoals**: At least 1 subgoal required
3. **dependencies**: Must reference valid subgoal IDs
4. **confidence**: Float between 0.0 and 1.0
5. **relevance**: Float between 0.0 and 1.0

## Examples

### Simple Goal (Single Subgoal)

Created with: `aur goals "Fix bug in login form" --no-decompose`

```json
{
  "id": "0001-fix-login-bug",
  "title": "Fix validation bug in login form",
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Fix login validation",
      "description": "Fix email validation regex in login form",
      "agent": "@full-stack-dev",
      "confidence": 0.95,
      "dependencies": []
    }
  ],
  "gaps": []
}
```

### Complex Goal (Multiple Subgoals with Dependencies)

See `goals-example.json` for a complete OAuth2 authentication example with:
- 5 subgoals
- Dependency chain (sg-1 → sg-2 → sg-3 → sg-4 → sg-5)
- Multiple agents (@full-stack-dev, @qa-test-architect)
- Memory context from 4 relevant files

### Goal with Agent Gap

```json
{
  "id": "0001-blockchain-integration",
  "title": "Implement blockchain transaction verification",
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Integrate blockchain adapter",
      "description": "Add Web3 integration for Ethereum transactions",
      "agent": "@full-stack-dev",
      "confidence": 0.42,
      "dependencies": []
    }
  ],
  "gaps": [
    {
      "subgoal_id": "sg-1",
      "suggested_capabilities": ["blockchain", "web3", "smart-contracts"],
      "fallback": "@full-stack-dev"
    }
  ]
}
```

## Usage in Workflow

### 1. Generate goals.json

```bash
aur goals "Your high-level goal description"
```

### 2. Review and Edit (Optional)

```bash
cd .aurora/plans/0001-your-goal/
nano goals.json  # Edit agent assignments, descriptions, etc.
```

### 3. Generate PRD and Tasks

In Claude Code:
```bash
/plan
```

This reads `goals.json` and generates:
- `prd.md` - Product Requirements Document
- `tasks.md` - Task list with agent metadata
- `specs/` - Detailed specifications

### 4. Execute Tasks

```bash
# Sequential execution
aur implement

# Parallel execution
aur spawn tasks.md
```

## See Also

- [Planning Flow Documentation](../../docs/workflows/planning-flow.md)
- [aur goals Command Reference](../../docs/commands/aur-goals.md)
- [Agent System Documentation](../../docs/agents/README.md)
