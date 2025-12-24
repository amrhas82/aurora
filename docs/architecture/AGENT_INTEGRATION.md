# Agent Integration Guide

## Overview

This guide explains how to integrate agents with the SOAR pipeline, including response format requirements, execution patterns, and best practices.

## Agent Response Format

All agents must return responses in the following standardized format to be compatible with Phase 6 (Collect) and Phase 7 (Synthesize).

### Required Format

```python
{
    "subgoal_id": str,           # Which subgoal this response addresses
    "summary": str,              # Natural language summary of what was done
    "data": dict | list | None,  # Structured output data (files modified, analysis results, etc.)
    "confidence": float,         # Confidence score 0.0-1.0
    "tools_used": list[str],     # List of tools invoked during execution
    "metadata": dict             # Additional execution metadata
}
```

### Field Descriptions

#### subgoal_id (Required)
**Type**: `str`
**Purpose**: Links response to specific subgoal from decomposition
**Format**: Must match subgoal ID from decomposition (e.g., "sg1", "sg2")

**Example**:
```python
"subgoal_id": "sg1"
```

#### summary (Required)
**Type**: `str`
**Purpose**: Human-readable explanation of what the agent accomplished
**Length**: 2-10 sentences
**Style**: Clear, concise, present tense

**Good Examples**:
```python
"summary": "Created users table with email_verified column. Added index on email field for faster lookups. Migration script generated at migrations/001_users.sql."

"summary": "Analyzed calculate_total function in billing.py. Function computes order total by summing line items and applying tax/discount. Takes Order object, returns Decimal. No side effects detected."

"summary": "Implemented JWT authentication middleware. Added token validation, expiry checks, and user context injection. All 15 integration tests passing."
```

**Bad Examples**:
```python
"summary": "Done."  # Too vague

"summary": "I created the users table and then I added an email field and then I indexed it and then I wrote a migration and..."  # Too verbose, poor style

"summary": ""  # Empty
```

#### data (Optional but Recommended)
**Type**: `dict` | `list` | `None`
**Purpose**: Structured output data for other agents or synthesis
**Content**: Depends on subgoal type (see examples below)

**Examples by Subgoal Type**:

**File Modification**:
```python
"data": {
    "files_modified": ["billing.py", "tests/test_billing.py"],
    "lines_changed": {
        "billing.py": {"added": 45, "removed": 12},
        "tests/test_billing.py": {"added": 30, "removed": 0}
    },
    "functions_added": ["calculate_tax", "apply_discount"],
    "functions_modified": ["calculate_total"]
}
```

**Code Analysis**:
```python
"data": {
    "function_name": "calculate_total",
    "parameters": [
        {"name": "order", "type": "Order", "required": True},
        {"name": "tax_rate", "type": "float", "required": False, "default": 0.0}
    ],
    "return_type": "Decimal",
    "dependencies": ["calculate_tax", "apply_discount", "Order.line_items"],
    "complexity_score": 0.35,
    "side_effects": []
}
```

**Test Results**:
```python
"data": {
    "tests_run": 15,
    "tests_passed": 15,
    "tests_failed": 0,
    "coverage_percent": 92.5,
    "test_files": ["tests/test_billing.py"],
    "duration_seconds": 2.3
}
```

**Database Schema**:
```python
"data": {
    "table_name": "users",
    "columns": [
        {"name": "id", "type": "INTEGER", "primary_key": True},
        {"name": "email", "type": "VARCHAR(255)", "unique": True},
        {"name": "email_verified", "type": "BOOLEAN", "default": False}
    ],
    "indexes": [
        {"name": "idx_users_email", "columns": ["email"], "unique": True}
    ],
    "migration_file": "migrations/001_users.sql"
}
```

#### confidence (Required)
**Type**: `float`
**Range**: `0.0` to `1.0`
**Purpose**: Indicates agent's confidence in its output

**Scoring Guidelines**:
- `0.9-1.0`: High confidence
  - All tests passing
  - Complete implementation
  - No warnings or errors

- `0.7-0.9`: Good confidence
  - Implementation complete
  - Minor issues or warnings
  - Some tests passing

- `0.5-0.7`: Moderate confidence
  - Partial implementation
  - Some tests failing
  - Known limitations

- `0.3-0.5`: Low confidence
  - Incomplete implementation
  - Significant issues
  - May need rework

- `0.0-0.3`: Very low confidence
  - Failed to complete subgoal
  - Critical errors
  - Unusable output

**Examples**:
```python
# High confidence - all tests pass
"confidence": 0.95

# Good confidence - implementation complete but one test fails
"confidence": 0.80

# Moderate confidence - partial implementation, needs more work
"confidence": 0.65

# Low confidence - encountered blocking issue, made partial progress
"confidence": 0.40
```

#### tools_used (Required)
**Type**: `list[str]`
**Purpose**: Track which tools were invoked during execution
**Content**: Tool type names (not specific invocations)

**Standard Tool Types**:
- `file_reader` - Read file contents
- `file_writer` - Write/modify files
- `code_analyzer` - Analyze code structure
- `test_runner` - Execute tests
- `database_query` - Query database
- `database_migration` - Apply schema changes
- `git_operations` - Git commands
- `shell_command` - Execute shell commands
- `llm_call` - Call LLM for reasoning/generation
- `search` - Search codebase/docs

**Examples**:
```python
# Agent that analyzes and modifies code
"tools_used": ["file_reader", "code_analyzer", "file_writer"]

# Agent that runs tests
"tools_used": ["test_runner", "code_analyzer"]

# Agent that implements feature using LLM assistance
"tools_used": ["file_reader", "llm_call", "file_writer", "test_runner"]

# Read-only analysis agent
"tools_used": ["file_reader", "code_analyzer"]
```

#### metadata (Required)
**Type**: `dict`
**Purpose**: Additional execution information for debugging and monitoring

**Standard Fields**:
```python
"metadata": {
    "duration_ms": int,          # Execution time in milliseconds
    "model_used": str,           # LLM model if applicable (e.g., "claude-sonnet-4")
    "tokens_used": int,          # Total tokens if LLM was used
    "agent_version": str,        # Agent implementation version
    "retries": int,              # Number of retries performed
    "warnings": list[str],       # Non-fatal warnings
    "debug_info": dict           # Additional debugging data
}
```

**Example**:
```python
"metadata": {
    "duration_ms": 1234,
    "model_used": "claude-sonnet-4",
    "tokens_used": 2500,
    "agent_version": "1.2.0",
    "retries": 0,
    "warnings": ["File auth.py has high complexity (0.85), consider refactoring"],
    "debug_info": {
        "test_command": "pytest tests/test_billing.py -v",
        "environment": "python3.10"
    }
}
```

## Complete Example

### Example 1: Code Implementation Agent

```python
{
    "subgoal_id": "sg2",
    "summary": "Implemented JWT authentication middleware in auth/middleware.py. Middleware validates JWT tokens, checks expiry, and injects user context into request. Added error handling for expired/invalid tokens. All 12 integration tests passing with 95% coverage.",

    "data": {
        "files_modified": [
            "auth/middleware.py",
            "tests/test_auth_middleware.py"
        ],
        "lines_changed": {
            "auth/middleware.py": {"added": 78, "removed": 0},
            "tests/test_auth_middleware.py": {"added": 145, "removed": 0}
        },
        "functions_added": [
            "validate_jwt_token",
            "extract_user_from_token",
            "jwt_middleware"
        ],
        "test_results": {
            "tests_run": 12,
            "tests_passed": 12,
            "coverage_percent": 95.2
        }
    },

    "confidence": 0.92,

    "tools_used": [
        "file_reader",
        "code_analyzer",
        "file_writer",
        "test_runner"
    ],

    "metadata": {
        "duration_ms": 4567,
        "model_used": "claude-sonnet-4",
        "tokens_used": 3200,
        "agent_version": "2.1.0",
        "retries": 0,
        "warnings": [],
        "debug_info": {
            "test_command": "pytest tests/test_auth_middleware.py -v --cov",
            "python_version": "3.10.12"
        }
    }
}
```

### Example 2: Analysis Agent

```python
{
    "subgoal_id": "sg1",
    "summary": "Analyzed billing.py module structure. Found 8 functions with average complexity 0.42. Module handles order calculations including tax, discounts, and shipping. Dependencies on Order model and config.tax_rates. No critical issues found.",

    "data": {
        "module_path": "billing.py",
        "functions": [
            {
                "name": "calculate_total",
                "complexity": 0.35,
                "lines": 25,
                "dependencies": ["calculate_tax", "apply_discount"]
            },
            {
                "name": "calculate_tax",
                "complexity": 0.15,
                "lines": 10,
                "dependencies": ["config.tax_rates"]
            },
            {
                "name": "apply_discount",
                "complexity": 0.52,
                "lines": 35,
                "dependencies": ["Order.discount_code", "validate_discount"]
            }
            # ... more functions
        ],
        "imports": ["decimal", "models.order", "config"],
        "average_complexity": 0.42,
        "total_lines": 180,
        "issues": []
    },

    "confidence": 0.98,

    "tools_used": [
        "file_reader",
        "code_analyzer"
    ],

    "metadata": {
        "duration_ms": 234,
        "agent_version": "2.0.1",
        "retries": 0,
        "warnings": [],
        "debug_info": {
            "analyzer": "ast-based"
        }
    }
}
```

### Example 3: Failed Execution (Partial Output)

```python
{
    "subgoal_id": "sg3",
    "summary": "Attempted to deploy application to production but encountered authentication error. Staging deployment completed successfully. Production deployment blocked due to missing AWS credentials in environment.",

    "data": {
        "staging_url": "https://staging.example.com",
        "staging_status": "deployed",
        "production_status": "failed",
        "error_message": "AWS credentials not found in environment (AWS_ACCESS_KEY_ID)",
        "partial_results": {
            "docker_image_built": True,
            "docker_image_pushed": True,
            "ecs_task_updated": False
        }
    },

    "confidence": 0.45,

    "tools_used": [
        "shell_command",
        "git_operations"
    ],

    "metadata": {
        "duration_ms": 12000,
        "agent_version": "1.5.0",
        "retries": 2,
        "warnings": [
            "Production deployment requires manual credential setup",
            "Fallback to staging deployment only"
        ],
        "debug_info": {
            "docker_build_time_ms": 8000,
            "docker_push_time_ms": 3500,
            "deployment_error": "AwsCredentialError: Missing access key"
        }
    }
}
```

## Agent Execution Patterns

### Pattern 1: Sequential Execution

Agents execute one after another when subgoals have dependencies.

```python
# Decomposition specifies sequential execution
"execution_order": [
    {"phase": "sequential", "subgoals": ["sg1", "sg2", "sg3"]}
]

# Phase 6 (Collect) executes:
result_sg1 = await execute_agent(agent1, subgoal1)
result_sg2 = await execute_agent(agent2, subgoal2, context=result_sg1)  # Has result from sg1
result_sg3 = await execute_agent(agent3, subgoal3, context=result_sg2)  # Has result from sg2
```

**Use Cases**:
- Subgoal B depends on output from subgoal A
- Order matters (e.g., build before test)
- Shared state must be consistent

### Pattern 2: Parallel Execution

Independent agents execute concurrently for speed.

```python
# Decomposition specifies parallel execution
"execution_order": [
    {"phase": "parallel", "subgoals": ["sg1", "sg2", "sg3"]}
]

# Phase 6 (Collect) executes:
results = await asyncio.gather(
    execute_agent(agent1, subgoal1),
    execute_agent(agent2, subgoal2),
    execute_agent(agent3, subgoal3)
)
```

**Use Cases**:
- Independent subgoals (no dependencies)
- Read-only operations
- Speed optimization (2-4x faster)

**Limitations**:
- Cannot share state
- May cause conflicts if writing same files

### Pattern 3: Mixed Sequential/Parallel

Most queries use a mix of sequential and parallel phases.

```python
# Decomposition with mixed execution
"execution_order": [
    {"phase": "sequential", "subgoals": ["sg1"]},      # Analyze requirements first
    {"phase": "parallel", "subgoals": ["sg2", "sg3"]}, # Implement and test in parallel
    {"phase": "sequential", "subgoals": ["sg4"]}       # Deploy after both complete
]

# Phase 6 executes:
result_sg1 = await execute_agent(agent1, subgoal1)
results_2_3 = await asyncio.gather(
    execute_agent(agent2, subgoal2, context=result_sg1),
    execute_agent(agent3, subgoal3, context=result_sg1)
)
result_sg4 = await execute_agent(agent4, subgoal4, context=results_2_3)
```

## Timeout Handling

### Per-Agent Timeout

Each agent has a timeout (default: 60 seconds).

**Configuration**:
```python
config = {
    "agent_timeout_seconds": 60,  # Default
    "allow_timeout_override": True
}
```

**Behavior**:
- If agent exceeds timeout → Cancel execution
- If retry available → Try different agent or retry with same agent
- If no retry → Mark subgoal as failed, continue with degradation

**Agent Implementation**:
```python
async def execute(self, subgoal, context, timeout=60):
    try:
        async with asyncio.timeout(timeout):
            # Agent implementation
            result = await self._do_work(subgoal, context)
            return result
    except asyncio.TimeoutError:
        # Return partial results with low confidence
        return {
            "subgoal_id": subgoal["id"],
            "summary": "Execution timed out after {timeout}s. Partial results may be incomplete.",
            "data": self._get_partial_results(),
            "confidence": 0.3,
            "tools_used": self.tools_used,
            "metadata": {
                "timeout": True,
                "timeout_seconds": timeout,
                "duration_ms": timeout * 1000
            }
        }
```

### Overall Query Timeout

Entire query has a timeout (default: 5 minutes).

**Configuration**:
```python
config = {
    "query_timeout_seconds": 300  # 5 minutes default
}
```

**Behavior**:
- If query exceeds timeout → Cancel remaining agents
- Return partial synthesis from completed subgoals
- Include timeout metadata in response

## Error Handling

### Recoverable Errors (Retry)

**Scenarios**:
- Agent timeout
- Transient API errors
- Resource temporarily unavailable

**Behavior**:
```python
# Phase 6 retry logic
max_retries = 2
for attempt in range(max_retries + 1):
    try:
        result = await execute_agent(agent, subgoal)
        if result["confidence"] >= 0.7:
            return result
        elif attempt < max_retries:
            # Low confidence, retry with feedback
            continue
        else:
            # Max retries reached, accept low confidence result
            return result
    except AgentTimeoutError:
        if attempt < max_retries:
            # Try different agent or increase timeout
            agent = fallback_agent
            continue
        else:
            # Return timeout error
            return create_timeout_response(subgoal)
```

### Unrecoverable Errors (Fail)

**Scenarios**:
- Invalid subgoal (malformed input)
- Agent not found and no fallback
- Critical system error

**Behavior**:
- If subgoal is CRITICAL → Abort entire query
- If subgoal is MEDIUM/LOW → Continue with graceful degradation
- Include error details in synthesis

### Partial Success Handling

**Definition**: Agent completed some work but not fully successful.

**Indicators**:
- `confidence < 0.7`
- Non-empty `data` but incomplete
- `warnings` in metadata

**Synthesis Behavior**:
```python
if agent_output["confidence"] < 0.5:
    # Low confidence, acknowledge limitation
    synthesis += f"Note: {subgoal['description']} was partially completed. "
    synthesis += f"Limitation: {agent_output['metadata']['warnings'][0]}"
elif agent_output["confidence"] < 0.7:
    # Moderate confidence, use but flag
    synthesis += f"(Based on partial results from {subgoal['description']})"
else:
    # Good confidence, use normally
    synthesis += f"Successfully {subgoal['description']}."
```

## Agent Registry Integration

### Registering an Agent

```python
from aurora_soar.agent_registry import AgentRegistry, AgentInfo

registry = AgentRegistry()

# Register agent
registry.register_agent(AgentInfo(
    agent_id="code-analyzer",
    name="Code Analyzer",
    description="Analyzes code structure, complexity, and dependencies",
    capabilities=["code_analysis", "complexity_scoring", "dependency_graph"],
    tools=["file_reader", "ast_parser", "code_analyzer"],
    executor=my_code_analyzer_execute_function,
    version="2.0.1"
))
```

### Agent Lookup

```python
# Phase 5 (Route) looks up agents
agent_info = registry.get_agent("code-analyzer")
if agent_info is None:
    # Try capability-based search
    agent_info = registry.find_agent_by_capability("code_analysis")
if agent_info is None:
    # Fallback to generic executor
    agent_info = registry.get_agent("llm-executor")
```

## Best Practices

### For Agent Developers

1. **Always Return Valid Format**
   - Include all required fields
   - Use correct types
   - Validate before returning

2. **Provide Meaningful Summaries**
   - Explain what was done, not how
   - Include key metrics (tests passed, files modified)
   - Mention limitations or warnings

3. **Set Honest Confidence Scores**
   - Don't overstate confidence
   - Low confidence is better than wrong confidence
   - Consider partial results = moderate confidence

4. **Track All Tools Used**
   - Helps with debugging
   - Enables cost tracking
   - Supports reproducibility

5. **Handle Timeouts Gracefully**
   - Save intermediate state
   - Return partial results
   - Explain what completed and what didn't

6. **Test Error Paths**
   - Test timeout scenarios
   - Test partial failures
   - Test malformed inputs

### For System Integrators

1. **Register Agents Completely**
   - Include all capabilities
   - List all tools accurately
   - Keep versions up to date

2. **Monitor Agent Performance**
   - Track average execution time
   - Track confidence scores
   - Alert on high failure rates

3. **Tune Timeouts**
   - Set realistic timeouts per agent type
   - Allow override for complex subgoals
   - Monitor timeout rate (target: <5%)

4. **Implement Fallbacks**
   - Every agent type should have a fallback
   - Generic `llm-executor` as last resort
   - Log fallback usage for optimization

5. **Test Integration**
   - Integration tests with real agents
   - Fault injection tests (timeouts, errors)
   - Load testing with parallel execution

## Debugging

### Common Issues

**Issue: Agent output not used in synthesis**
- Check `subgoal_id` matches decomposition
- Check `summary` is non-empty
- Check `confidence >= 0.5`

**Issue: Agent timeout frequently**
- Increase `agent_timeout_seconds`
- Optimize agent implementation
- Break subgoal into smaller pieces

**Issue: Low confidence scores consistently**
- Review agent implementation quality
- Check if subgoals are too vague
- Verify agent has required tools

### Logging

Enable verbose logging to see agent execution details:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Logs include:
- Agent selection reasoning
- Execution timing
- Tool invocations
- Confidence score calculation
- Retry attempts

### Metrics

Track these metrics for agent health:

- **Success Rate**: `confidence ≥ 0.7 / total executions`
- **Average Confidence**: Mean confidence score
- **Timeout Rate**: `timeouts / total executions`
- **Retry Rate**: `retries / total executions`
- **Average Duration**: Mean `duration_ms`

## Conclusion

Following this guide ensures your agents integrate seamlessly with the SOAR pipeline. The standardized response format enables reliable synthesis, and proper error handling ensures graceful degradation. For questions or issues, consult the troubleshooting guide or SOAR architecture documentation.
