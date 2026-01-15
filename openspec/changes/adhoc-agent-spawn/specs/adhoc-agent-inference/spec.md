# Capability: Ad-hoc Agent Inference

## Overview
Enable `aur spawn` to automatically infer agent definitions (role + goal) for tasks that reference non-existent agents, eliminating the need for pre-defined agent markdown files.

## ADDED Requirements

### Requirement: Detect Missing Agent References
**ID**: `spawn-adhoc-detect-001`
**Priority**: HIGH
**Status**: New

The system MUST detect when tasks reference agent IDs that are not present in the agent manifest.

#### Scenario: Single missing agent detected
**Given** a task file with agent reference `<!-- agent: data-specialist -->`
**And** `data-specialist` is not in the agent manifest
**When** `aur spawn tasks.md` is executed
**Then** the system detects `data-specialist` as a missing agent

#### Scenario: Multiple missing agents detected
**Given** a task file with 3 tasks referencing agents: `qa-expert`, `db-specialist`, `security-auditor`
**And** only `qa-expert` exists in the manifest
**When** `aur spawn tasks.md` is executed
**Then** the system detects `db-specialist` and `security-auditor` as missing agents

#### Scenario: No missing agents
**Given** a task file where all agents exist in the manifest
**When** `aur spawn tasks.md` is executed
**Then** no missing agents are detected
**And** normal spawn behavior continues

---

### Requirement: Fail Fast Without Ad-hoc Flag
**ID**: `spawn-adhoc-fail-001`
**Priority**: HIGH
**Status**: New

The system MUST fail with a clear error message when missing agents are detected and the `--adhoc` flag is NOT provided.

#### Scenario: Missing agent without --adhoc flag
**Given** a task file references missing agent `unknown-agent`
**When** `aur spawn tasks.md` is executed WITHOUT `--adhoc` flag
**Then** the command fails with exit code 1
**And** displays error: "Error: Missing agents: unknown-agent"
**And** suggests: "Use --adhoc to enable ad-hoc agent inference"

#### Scenario: Multiple missing agents without --adhoc
**Given** task file references 3 missing agents
**When** `aur spawn tasks.md` is executed WITHOUT `--adhoc` flag
**Then** error lists all missing agents: "Missing agents: agent1, agent2, agent3"

---

### Requirement: Infer Agent Role and Goal
**ID**: `spawn-adhoc-infer-001`
**Priority**: HIGH
**Status**: New

The system MUST generate agent role and goal from task description when `--adhoc` flag is provided.

#### Scenario: Infer single agent from task
**Given** a task: "Migrate PostgreSQL database schema to version 14"
**And** agent ID: `db-migration-expert`
**And** `--adhoc` flag is provided
**When** inference is triggered
**Then** system generates role: "Database Migration Specialist"
**And** generates goal describing PostgreSQL migration expertise

#### Scenario: Inferred agent has valid format
**Given** any task description
**When** agent is inferred
**Then** role is non-empty and ≤200 characters
**And** goal is non-empty and ≤500 characters
**And** role does not contain placeholder text like "TODO" or "TBD"
**And** goal is specific to the task domain

---

### Requirement: Batch Inference for Efficiency
**ID**: `spawn-adhoc-batch-001`
**Priority**: MEDIUM
**Status**: New

The system MUST use batch inference when multiple missing agents are detected to reduce LLM API calls.

#### Scenario: Batch infer multiple agents
**Given** 3 tasks with missing agents: `agent-a`, `agent-b`, `agent-c`
**And** `--adhoc` flag is provided
**When** inference is triggered
**Then** system makes 1 batch LLM call (not 3 individual calls)
**And** returns inferred definitions for all 3 agents

#### Scenario: Token efficiency validation
**Given** batch inference for 5 agents
**When** compared to 5 individual inferences
**Then** batch inference uses ≤60% of individual inference token count

---

### Requirement: Cache Inferred Agents Per Session
**ID**: `spawn-adhoc-cache-001`
**Priority**: HIGH
**Status**: New

The system MUST cache inferred agents within a spawn session to avoid duplicate inference calls.

#### Scenario: Cache hit prevents duplicate inference
**Given** task 1 triggers inference for `data-analyst`
**And** task 3 also references `data-analyst`
**When** tasks are processed
**Then** inference is triggered only once for `data-analyst`
**And** cached result is reused for task 3

#### Scenario: Cache is session-scoped
**Given** a spawn session completes with inferred agents cached
**When** a new `aur spawn` command is executed
**Then** cache is empty (previous session's cache is cleared)

---

### Requirement: Execute Tasks with Ad-hoc Agents
**ID**: `spawn-adhoc-exec-001`
**Priority**: HIGH
**Status**: New

The system MUST execute tasks using inferred agent context when ad-hoc agents are provided.

#### Scenario: Task execution with ad-hoc agent
**Given** task with inferred agent: role="QA Specialist", goal="Test coverage analysis"
**When** task is spawned
**Then** agent context (role + goal) is passed to the spawned subprocess
**And** subprocess receives modified prompt with agent context

#### Scenario: Agent context format
**Given** inferred agent with role="Security Auditor" and goal="Identify vulnerabilities"
**When** prompt is constructed
**Then** prompt includes: "Acting as Security Auditor (Identify vulnerabilities)\n\n{original_task}"

---

### Requirement: Export Inferred Agents
**ID**: `spawn-adhoc-log-001`
**Priority**: MEDIUM
**Status**: New

The system MUST support exporting inferred agent definitions when `--adhoc-log` flag is provided.

#### Scenario: Export inferred agents to JSON
**Given** 2 agents inferred during spawn: `agent-x` and `agent-y`
**And** `--adhoc-log agents.json` flag is provided
**When** spawn completes
**Then** file `agents.json` is created
**And** contains JSON with agent definitions:
```json
{
  "agent-x": {
    "role": "...",
    "goal": "...",
    "confidence": 0.95
  },
  "agent-y": { ... }
}
```

#### Scenario: Log file parent directory creation
**Given** `--adhoc-log /path/to/new/dir/agents.json`
**And** `/path/to/new/dir/` does not exist
**When** spawn completes
**Then** directory `/path/to/new/dir/` is created
**And** `agents.json` is written successfully

---

### Requirement: Validate Inferred Agent Quality
**ID**: `spawn-adhoc-validate-001`
**Priority**: HIGH
**Status**: New

The system MUST validate inferred agent definitions before using them.

#### Scenario: Reject empty role
**Given** inference returns empty role
**When** validation is performed
**Then** agent is rejected as invalid
**And** system falls back to direct LLM (agent=None)

#### Scenario: Reject overly long role
**Given** inference returns role with 250 characters
**When** validation is performed
**Then** agent is rejected (max 200 chars)

#### Scenario: Reject placeholder text
**Given** inference returns role="TODO" or goal="TBD"
**When** validation is performed
**Then** agent is rejected as invalid

---

### Requirement: Graceful Degradation on Inference Failure
**ID**: `spawn-adhoc-fallback-001`
**Priority**: HIGH
**Status**: New

The system MUST fall back to direct LLM execution when ad-hoc inference fails.

#### Scenario: Inference timeout fallback
**Given** LLM inference times out after 10 seconds
**When** spawn continues execution
**Then** task executes with agent=None (direct LLM)
**And** warning is logged: "Ad-hoc inference failed, using direct LLM"

#### Scenario: Invalid JSON fallback
**Given** LLM returns malformed JSON
**When** inference validation fails
**Then** task executes with agent=None
**And** error is logged with details

---

### Requirement: Console Output for Ad-hoc Workflow
**ID**: `spawn-adhoc-ui-001`
**Priority**: MEDIUM
**Status**: New

The system MUST provide clear console output when ad-hoc inference is triggered.

#### Scenario: Inference notification
**Given** 2 missing agents detected with `--adhoc` flag
**When** inference starts
**Then** console displays: "Inferring 2 ad-hoc agents..."

#### Scenario: Verbose mode shows inferred agents
**Given** verbose flag is enabled
**And** agents are inferred
**When** inference completes
**Then** console displays for each agent:
```
→ Database Specialist: Execute database migrations with...
→ Security Auditor: Identify security vulnerabilities in...
```

#### Scenario: Completion message includes ad-hoc indicator
**Given** task completes successfully using ad-hoc agent
**When** result is displayed
**Then** output includes: "✓ Task 1: Success (using ad-hoc agent)"

---

## MODIFIED Requirements

_None - This is a new capability with no modifications to existing requirements._

---

## REMOVED Requirements

_None - This is a new capability with no removals._

---

## Dependencies

**Internal**:
- `spawn-command`: Core spawn command for task execution
- `agent-manifest`: Agent discovery and manifest system
- `llm-client`: LLM API integration for inference

**External**:
- LLM API (Anthropic/OpenAI) for agent inference
- JSON parsing for structured inference output

---

## Non-Functional Requirements

**Performance**:
- Single agent inference: <2 seconds
- Batch inference (5 agents): <3 seconds
- Cache lookup: <1ms

**Reliability**:
- Inference success rate: >95%
- Graceful fallback on all failure modes
- Zero breaking changes to existing spawn behavior

**Security**:
- Task descriptions sanitized before LLM inference
- Inferred agents validated before use
- No sensitive data in inference prompts

**Usability**:
- Clear error messages for missing agents
- Opt-in via `--adhoc` flag (safe default)
- Verbose mode explains ad-hoc workflow

---

## Testing Requirements

**Unit Tests**:
- Test inference with various task descriptions
- Test cache hit/miss scenarios
- Test validation rules (empty, long, placeholder text)
- Test batch inference logic
- Test fallback behavior

**Integration Tests**:
- Test end-to-end workflow with missing agents
- Test --adhoc-log export
- Test multiple missing agents in one spawn
- Test cache prevents duplicate inferences

**E2E Tests**:
- Test real task file with missing agents
- Test error messages without --adhoc flag
- Test verbose output format

**Coverage Target**: 95%+ for new modules

---

## Acceptance Criteria

- [ ] Tasks with missing agents fail without --adhoc flag
- [ ] Tasks with missing agents succeed with --adhoc flag
- [ ] Inferred agents produce domain-specific role and goal
- [ ] Cache prevents duplicate inferences within session
- [ ] --adhoc-log exports valid JSON
- [ ] Inference failures fall back gracefully
- [ ] Console output clearly indicates ad-hoc workflow
- [ ] Zero breaking changes to existing spawn behavior
- [ ] All tests pass with 95%+ coverage
- [ ] Documentation updated with examples
