# Task Execution Prompt

You are processing a tasks.md file with structured tasks that need to be executed.

## Task Format

Tasks follow this format:

```markdown
- [ ] 1.0 Task description
  - [ ] 1.1 Subtask description
<!-- agent: agent-name -->
<!-- model: model-name -->
```

## Agent Metadata

Tasks may include HTML comment metadata:
- `<!-- agent: AGENT_NAME -->` - Specifies which agent should execute the task
- `<!-- model: MODEL_NAME -->` - Specifies which model to use (optional)

If no agent is specified, the task defaults to `agent: self` for direct execution.

## Execution Flow

1. **Parse tasks.md** - Extract all tasks with their IDs, descriptions, completion status, and metadata
2. **Sequential execution** - Process tasks in order (1, 1.1, 1.2, 2, 2.1, etc.)
3. **Skip completed** - Tasks marked `[x]` are already done, skip them
4. **Agent dispatch**:
   - `agent: self` → Execute directly in current context
   - `agent: <name>` → Dispatch to specified agent via spawner
5. **Mark complete** - After successful execution, update tasks.md to mark task `[x]`

## Agent Dispatch Format

When dispatching to an agent (agent != "self"), use this format:

```
As <agent-name>, complete this task:

Task ID: <id>
Description: <description>

Please execute this task and provide a summary of what was accomplished.
```

The spawner will handle routing to the appropriate agent with the specified model.

## Task Completion

After successful execution:
1. Read tasks.md file
2. Find the task line: `- [ ] <task-id>. <description>`
3. Replace `[ ]` with `[x]`
4. Write updated content back to file

Failed tasks remain unchecked `[ ]` so they can be retried.

## Context Handling

Tasks may reference previous task outputs. The executor maintains context:
- Each task receives the full tasks.md content
- Agents can see task structure and dependencies
- Sequential execution ensures dependencies are resolved in order

## Error Handling

If a task fails:
1. Log the error details
2. Do NOT mark the task complete
3. Continue with remaining tasks (best-effort execution)
4. Return execution results for all tasks

## Example Workflow

Given this tasks.md:

```markdown
- [ ] 1.0 Setup infrastructure
  - [ ] 1.1 Create database schema
  - [ ] 1.2 Setup API endpoints
<!-- agent: code-developer -->

- [ ] 2.0 Design UI wireframes
<!-- agent: ui-designer -->
```

Execution:
1. Parse: Found 3 tasks (1.0, 1.1, 1.2, 2.0)
2. Execute 1.0 (self) → Success → Mark [x]
3. Execute 1.1 (self) → Success → Mark [x]
4. Execute 1.2 (code-developer via spawner) → Success → Mark [x]
5. Execute 2.0 (ui-designer via spawner) → Success → Mark [x]

Result: All tasks completed and marked in tasks.md
