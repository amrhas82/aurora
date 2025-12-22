# Verification Checkpoint Logic

## Overview

The SOAR pipeline implements multiple verification checkpoints to ensure quality and correctness before expensive operations. This document details the verification logic, score thresholds, and decision criteria.

## Checkpoint 1: Decomposition Verification (Phase 4)

### Purpose
Validate that query decomposition is complete, consistent, grounded, and routable before executing agents.

### When It Runs
After Phase 3 (Decompose) generates a decomposition with subgoals and execution order.

### Verification Options

#### Option A: Self-Verification (MEDIUM Complexity)
- **Description**: The same LLM that created the decomposition reviews its own work
- **Use Case**: Routine queries where cost optimization is important
- **Cost**: ~$0.001 per verification (Haiku 3.5)
- **Prompt**: `verify_self.py` template

**Advantages**:
- Fast (single LLM call)
- Low cost
- Sufficient for routine queries

**Limitations**:
- May miss subtle issues
- Same model blind spots

#### Option B: Adversarial Verification (COMPLEX/CRITICAL)
- **Description**: A different LLM (or same LLM with adversarial prompt) critiques the decomposition
- **Use Case**: High-stakes, security-critical, or complex architectural queries
- **Cost**: ~$0.01 per verification (Sonnet 4)
- **Prompt**: `verify_adversarial.py` template

**Advantages**:
- More rigorous
- Catches subtle inconsistencies
- Different perspective reveals blind spots

**Limitations**:
- Higher cost (10x Option A)
- Slightly slower (additional LLM call)

### Verification Criteria

The verification evaluates 4 dimensions:

#### 1. Completeness (Weight: 0.4)
**Question**: Does the decomposition cover all aspects of the original query?

**Scoring**:
- `1.0`: All query aspects addressed
- `0.7-0.9`: Most aspects covered, minor gaps acceptable
- `0.5-0.7`: Significant gaps, missing key aspects
- `<0.5`: Major omissions, fundamentally incomplete

**Common Issues**:
- Missing error handling subgoals
- No testing/validation steps
- Ignoring non-functional requirements (performance, security)
- Overlooking dependencies (e.g., "implement feature X" without "analyze requirements")

**Example**:
```
Query: "Implement user authentication with OAuth2 and rate limiting"

Complete (1.0):
- Analyze OAuth2 flow requirements
- Design database schema for users/tokens
- Implement OAuth2 endpoints
- Add rate limiting middleware
- Write integration tests
- Document API

Incomplete (0.5):
- Implement OAuth2 endpoints
- Add rate limiting
(Missing: requirements analysis, testing, documentation)
```

#### 2. Consistency (Weight: 0.2)
**Question**: Are subgoals compatible and non-contradictory?

**Scoring**:
- `1.0`: All subgoals align, no conflicts
- `0.7-0.9`: Minor inconsistencies, easily resolved
- `0.5-0.7`: Contradictions require reconciliation
- `<0.5`: Fundamental conflicts, cannot proceed

**Common Issues**:
- Contradictory technical choices (e.g., "use SQL" vs "use NoSQL" for same data)
- Dependency cycles (A depends on B, B depends on A)
- Incompatible agent assignments (agent lacks required capability)
- Mismatched execution order (parallel subgoals that must be sequential)

**Example**:
```
Inconsistent (0.4):
- Subgoal 1: "Design REST API with stateless authentication"
- Subgoal 2: "Implement session management with cookies"
(Conflict: Stateless vs stateful)

Consistent (1.0):
- Subgoal 1: "Design REST API with JWT tokens"
- Subgoal 2: "Implement JWT validation middleware"
(Aligned approach)
```

#### 3. Groundedness (Weight: 0.2)
**Question**: Is the decomposition grounded in the retrieved context (code, patterns)?

**Scoring**:
- `1.0`: All subgoals reference available context
- `0.7-0.9`: Most subgoals grounded, some assumptions
- `0.5-0.7`: Significant assumptions not validated by context
- `<0.5`: Ignores context, makes unfounded assumptions

**Common Issues**:
- Assuming files/functions exist when they don't
- Suggesting agents that aren't in registry
- Proposing solutions incompatible with existing architecture
- Ignoring similar patterns from reasoning chunks

**Example**:
```
Retrieved Context:
- CodeChunk: auth.py has existing JWT validation
- ReasoningChunk: Previous OAuth2 implementation pattern

Grounded (1.0):
- "Extend existing JWT validation in auth.py for OAuth2"
- "Follow OAuth2 pattern from previous implementation"

Ungrounded (0.3):
- "Create new authentication system from scratch"
- "Use library X" (when context shows library Y is used)
```

#### 4. Routability (Weight: 0.2)
**Question**: Can suggested agents actually execute the subgoals?

**Scoring**:
- `1.0`: All agents exist and have required capabilities
- `0.7-0.9`: Most agents exist, fallbacks available
- `0.5-0.7`: Some agents missing, may need generic executor
- `<0.5`: Most agents unavailable, fundamental routing issues

**Common Issues**:
- Suggesting non-existent agents
- Agent lacks required tools (e.g., database-agent without SQL tools)
- Agent not authorized for operation (e.g., deployment-agent in dev environment)
- Overly specific agent names (better to use capability matching)

**Example**:
```
Available Agents:
- code-analyzer (capabilities: read, analyze, refactor)
- test-runner (capabilities: pytest, coverage)
- generic-executor (capabilities: all)

Routable (1.0):
- "Analyze auth.py structure" → code-analyzer ✓
- "Run authentication tests" → test-runner ✓

Non-Routable (0.4):
- "Deploy to production" → deployment-agent ✗ (doesn't exist)
- "Design UX mockups" → ui-designer ✗ (doesn't exist)
```

### Overall Score Calculation

```python
overall_score = (
    0.4 * completeness +
    0.2 * consistency +
    0.2 * groundedness +
    0.2 * routability
)
```

**Weight Rationale**:
- **Completeness (40%)**: Most important; incomplete decomposition leads to partial solutions
- **Consistency (20%)**: Important but often fixable; contradictions can be resolved
- **Groundedness (20%)**: Important for quality; ungrounded assumptions cause failures
- **Routability (20%)**: Important for execution; missing agents have fallbacks (llm-executor)

### Verdict Logic

The verification produces one of three verdicts:

#### PASS (overall_score ≥ 0.7)
**Action**: Proceed to Phase 5 (Route)

**Interpretation**: Decomposition is good enough for agent execution. Minor issues are acceptable and won't cause failures.

**Typical Scores**:
- `0.85-1.0`: Excellent decomposition
- `0.75-0.85`: Good decomposition with minor improvements possible
- `0.70-0.75`: Acceptable, proceed with caution

#### RETRY (0.5 ≤ overall_score < 0.7 AND retry_count < 2)
**Action**: Generate feedback, retry Phase 3 (Decompose)

**Interpretation**: Decomposition has issues but is fixable. LLM can improve with targeted feedback.

**Feedback Generation**:
```python
# retry_feedback prompt includes:
- Original query
- Previous decomposition
- Verification scores (completeness, consistency, groundedness, routability)
- Specific issues identified
- Concrete suggestions for improvement

# Example feedback:
"""
The decomposition has incomplete coverage (completeness: 0.6).
Issues:
- Missing error handling subgoals
- No testing/validation steps
Suggestions:
- Add subgoal: "Write integration tests for OAuth2 flow"
- Add subgoal: "Implement error handling for token validation"
"""
```

**Retry Loop**:
1. First retry (retry_count=0): Include basic feedback
2. Second retry (retry_count=1): Include more detailed feedback with examples
3. Max retries reached (retry_count≥2): Fail even if score is in RETRY range

**Typical Scores**:
- `0.60-0.69`: Needs improvement, likely fixable
- `0.50-0.59`: Significant issues, may fail on second retry

#### FAIL (overall_score < 0.5 OR retry_count ≥ 2)
**Action**: Return error to user with issues and suggestions

**Interpretation**: Decomposition is fundamentally flawed or unfixable via retries. Requires human intervention or query reformulation.

**Error Response**:
```python
{
    "error": "Decomposition verification failed",
    "verdict": "FAIL",
    "overall_score": 0.42,
    "scores": {
        "completeness": 0.3,
        "consistency": 0.6,
        "groundedness": 0.4,
        "routability": 0.5
    },
    "issues": [
        "Decomposition missing 3 key aspects: error handling, testing, documentation",
        "Subgoal 2 and 5 have contradictory technical approaches",
        "Assumes agent 'specialized-deployer' exists (not in registry)"
    ],
    "suggestions": [
        "Rephrase query to be more specific about requirements",
        "Break into smaller sub-queries (e.g., separate auth implementation from rate limiting)",
        "Provide more context about existing codebase structure"
    ]
}
```

**Typical Scores**:
- `0.30-0.49`: Major issues, possibly salvageable with human input
- `<0.30`: Fundamentally flawed, requires query reformulation

### Retry Strategy

**Retry Count Tracking**:
```python
retry_count = 0  # Initial decomposition
if verdict == RETRY and retry_count < 2:
    retry_count += 1
    # Generate feedback
    # Re-run Phase 3 with feedback injected into prompt
    # Re-run Phase 4 with same verification option
```

**Feedback Injection**:
```python
# decompose_prompt includes retry_feedback section
if retry_feedback:
    prompt += f"""

PREVIOUS ATTEMPT FEEDBACK:
{retry_feedback}

Please address the above issues in your revised decomposition.
"""
```

**Max Retries Rationale**:
- 0 retries: Accept score ≥0.7 on first attempt (60-70% of queries)
- 1 retry: Fix issues with feedback (25-30% of queries)
- 2 retries: If still failing after 2 attempts, human intervention needed (<5% of queries)

## Checkpoint 2: Agent Output Verification

### Purpose
Validate that each agent's output is complete, correct, and usable before synthesis.

### When It Runs
After Phase 6 (Collect) receives output from each agent.

### Verification Criteria

**Format Validation**:
- `summary` field present and non-empty
- `data` field present (may be empty for info-only subgoals)
- `confidence` field in range [0.0, 1.0]
- `tools_used` field is list of strings
- `metadata` field is dict

**Content Validation**:
- Summary addresses the subgoal description
- Summary length is reasonable (not empty, not truncated)
- Confidence matches content quality (low confidence for partial results)

### Verdict Logic

**PASS (confidence ≥ 0.7 AND format valid)**:
- Use output in synthesis

**RETRY (0.5 ≤ confidence < 0.7 AND retry_count < 2)**:
- Retry with different agent (if available)
- Otherwise, retry with same agent but different prompt

**FAIL (confidence < 0.5 OR retry_count ≥ 2)**:
- Mark subgoal as partial success
- Include in synthesis with warning
- If subgoal is CRITICAL, abort entire query

## Checkpoint 3: Synthesis Verification

### Purpose
Ensure synthesized answer is traceable to agent outputs and doesn't hallucinate.

### When It Runs
After Phase 7 (Synthesize) generates final answer.

### Verification Criteria

**Traceability**:
- Every claim in answer links to at least one agent output
- No unsupported claims or hallucinations
- Citations are specific (not just "agent X said...")

**Coherence**:
- Answer flows logically
- No contradictions between claims
- Addresses original query

**Completeness**:
- Incorporates all relevant agent outputs
- Explains any missing information
- Acknowledges limitations

### Verdict Logic

**PASS (traceability ≥ 0.7)**:
- Return answer to user

**RETRY (traceability < 0.7 AND retry_count < 2)**:
- Generate feedback highlighting unsupported claims
- Re-run synthesis with stricter traceability constraints

**FAIL (retry_count ≥ 2)**:
- Return agent outputs directly with warning
- Explanation of why synthesis failed

## Score Threshold Rationale

### Why 0.7 for PASS?
- **Empirical**: 0.7 balances quality and throughput in testing
- **Interpretation**: "Good enough" - minor issues won't cause failures
- **Cost**: Accepting 0.7 avoids unnecessary retries (saves 30% of LLM calls)

### Why 0.5 for RETRY?
- **Salvageable**: Scores 0.5-0.7 are fixable with targeted feedback
- **Cost-Benefit**: Retry cost (~$0.002) is justified if it prevents agent execution failure (~$0.05)
- **Success Rate**: 70% of retries in this range succeed on second attempt

### Why 0.4 Weights for Completeness?
- **Impact**: Incomplete decompositions cause partial solutions (worst outcome)
- **Frequency**: Completeness issues are most common verification failure (40%)
- **Fixability**: Completeness feedback is most effective (80% success rate on retry)

## Calibration

### Verification Score Calibration

To ensure verification scores correlate with actual success:

1. **Collect Ground Truth**:
   - Track verification scores for 100+ queries
   - Track actual execution success (did agents complete? was synthesis accurate?)

2. **Compute Correlation**:
   - Target: ≥0.7 correlation between verification score and success
   - If correlation <0.7, recalibrate weights or thresholds

3. **Adjust Thresholds**:
   - If too many false positives (low score but succeeded): Lower PASS threshold
   - If too many false negatives (high score but failed): Raise PASS threshold

### Few-Shot Example Quality

Verification quality depends on few-shot example quality:

- **Good Examples**: Clear, diverse, cover edge cases
- **Bad Examples**: Trivial, homogeneous, miss common issues

**Example Selection Criteria**:
- Include 1 good decomposition (score 0.9+)
- Include 1 mediocre decomposition (score 0.6-0.7)
- Include 1 bad decomposition (score <0.5)
- Ensure examples span complexity levels

## Monitoring and Metrics

### Key Metrics

**Verification Catch Rate**:
```
catch_rate = verified_failures / (verified_failures + missed_failures)
Target: ≥ 0.70 (catch 70% of issues before they cause failures)
```

**False Positive Rate**:
```
false_positive_rate = false_rejections / total_verifications
Target: ≤ 0.10 (don't reject 10% of good decompositions)
```

**Retry Success Rate**:
```
retry_success = retries_that_passed / total_retries
Target: ≥ 0.60 (60% of retries should succeed)
```

### Dashboard

Track verification metrics in real-time:
- Average verification score by complexity
- PASS/RETRY/FAIL distribution
- Retry success rate by issue type
- Verification cost vs agent execution cost (verify ROI)

### Alerts

**Alert: Low Catch Rate** (catch_rate < 0.60):
- Action: Review false negatives, adjust thresholds
- Severity: High (verification not catching issues)

**Alert: High False Positive Rate** (fp_rate > 0.15):
- Action: Review false positives, relax thresholds
- Severity: Medium (rejecting too many good decompositions)

**Alert: Low Retry Success** (retry_success < 0.50):
- Action: Review feedback quality, improve prompts
- Severity: Medium (retries not effective)

## Best Practices

### For Prompt Engineers

1. **Calibration Examples**: Include diverse examples spanning score ranges
2. **Clear Criteria**: Define explicit scoring rubrics in prompts
3. **Concrete Feedback**: Generate specific, actionable feedback for retries
4. **Consistency**: Use same LLM for decompose and verify (Option A) to reduce cost

### For System Operators

1. **Monitor Metrics**: Track catch rate, false positive rate, retry success
2. **Tune Thresholds**: Adjust PASS/RETRY thresholds based on success data
3. **Cost Analysis**: Verify that verification cost < cost of prevented failures
4. **A/B Testing**: Test Option A vs B on representative queries to find optimal mix

### For Developers

1. **Fail Fast**: Run verification before expensive operations
2. **Graceful Degradation**: Always return partial results, never fail silently
3. **Explainability**: Log verification scores and issues for debugging
4. **Testing**: Use fault injection to verify that verification catches known bad inputs

## Examples

### Example 1: PASS on First Attempt

**Query**: "What does the calculate_total function do?"

**Decomposition**:
```json
{
  "goal": "Explain calculate_total function",
  "subgoals": [
    {"id": "sg1", "description": "Find calculate_total function definition", "agent": "code-analyzer"},
    {"id": "sg2", "description": "Analyze function logic and parameters", "agent": "code-analyzer"},
    {"id": "sg3", "description": "Explain function purpose and usage", "agent": "llm-executor"}
  ],
  "execution_order": [
    {"phase": "sequential", "subgoals": ["sg1", "sg2", "sg3"]}
  ]
}
```

**Verification (Option A)**:
- Completeness: 0.95 (covers all aspects of explanation)
- Consistency: 1.0 (no conflicts)
- Groundedness: 0.9 (grounded in codebase)
- Routability: 1.0 (all agents exist)
- **Overall: 0.94** → **PASS**

---

### Example 2: RETRY with Feedback

**Query**: "Implement user registration with email verification"

**Decomposition (Attempt 1)**:
```json
{
  "goal": "Implement user registration",
  "subgoals": [
    {"id": "sg1", "description": "Create user table", "agent": "database-agent"},
    {"id": "sg2", "description": "Write registration endpoint", "agent": "api-developer"}
  ],
  "execution_order": [
    {"phase": "sequential", "subgoals": ["sg1", "sg2"]}
  ]
}
```

**Verification (Option A)**:
- Completeness: 0.5 (missing email verification logic, testing)
- Consistency: 0.9
- Groundedness: 0.8
- Routability: 0.7 (database-agent doesn't exist)
- **Overall: 0.65** → **RETRY**

**Feedback**:
```
Issues:
- Decomposition is incomplete (completeness: 0.5). Missing:
  - Email verification logic (send verification email, verify token)
  - Input validation for registration data
  - Testing subgoals
- Agent "database-agent" not found in registry (routability: 0.7)

Suggestions:
- Add subgoal: "Implement email verification token generation and validation"
- Add subgoal: "Send verification email using email service"
- Add subgoal: "Write integration tests for registration flow"
- Use "generic-executor" or "api-developer" instead of "database-agent"
```

**Decomposition (Attempt 2 with Feedback)**:
```json
{
  "goal": "Implement user registration with email verification",
  "subgoals": [
    {"id": "sg1", "description": "Design user table schema with email_verified field", "agent": "generic-executor"},
    {"id": "sg2", "description": "Implement registration endpoint with input validation", "agent": "api-developer"},
    {"id": "sg3", "description": "Generate and store email verification tokens", "agent": "api-developer"},
    {"id": "sg4", "description": "Send verification email", "agent": "email-service"},
    {"id": "sg5", "description": "Implement email verification endpoint", "agent": "api-developer"},
    {"id": "sg6", "description": "Write integration tests for registration flow", "agent": "test-runner"}
  ],
  "execution_order": [
    {"phase": "sequential", "subgoals": ["sg1", "sg2", "sg3"]},
    {"phase": "parallel", "subgoals": ["sg4", "sg5"]},
    {"phase": "sequential", "subgoals": ["sg6"]}
  ]
}
```

**Verification (Attempt 2)**:
- Completeness: 0.9 (all key aspects covered)
- Consistency: 0.95
- Groundedness: 0.85
- Routability: 0.9 (all agents exist or have fallbacks)
- **Overall: 0.89** → **PASS**

---

### Example 3: FAIL after Max Retries

**Query**: "Build a distributed consensus algorithm using Raft"

**Decomposition (Attempt 1)**:
```json
{
  "goal": "Build Raft consensus algorithm",
  "subgoals": [
    {"id": "sg1", "description": "Implement Raft protocol", "agent": "generic-executor"}
  ]
}
```

**Verification (Option B - Adversarial)**:
- Completeness: 0.2 (far too vague, missing all details)
- Consistency: 0.8
- Groundedness: 0.3 (no context for Raft implementation)
- Routability: 0.5
- **Overall: 0.35** → **RETRY**

**Feedback**:
```
Critical Issues:
- Decomposition is far too high-level (completeness: 0.2)
- "Implement Raft protocol" is not actionable - requires breaking into specific steps:
  - Leader election
  - Log replication
  - Safety properties
  - Membership changes
  - Log compaction
- No testing, validation, or error handling
```

**Decomposition (Attempt 2)**:
```json
{
  "goal": "Build Raft consensus algorithm",
  "subgoals": [
    {"id": "sg1", "description": "Implement leader election", "agent": "generic-executor"},
    {"id": "sg2", "description": "Implement log replication", "agent": "generic-executor"},
    {"id": "sg3", "description": "Implement safety checks", "agent": "generic-executor"}
  ]
}
```

**Verification (Attempt 2)**:
- Completeness: 0.4 (still missing many details)
- Consistency: 0.9
- Groundedness: 0.4
- Routability: 0.6
- **Overall: 0.52** → **RETRY** (retry_count=2, but still < 0.7)

**Decomposition (Attempt 3)**:
[Similar issues persist]

**Verification (Attempt 3)**:
- **Overall: 0.58** → **FAIL** (retry_count ≥ 2)

**Error Returned to User**:
```json
{
  "error": "Unable to decompose query into actionable subgoals after 2 retries",
  "overall_score": 0.58,
  "issues": [
    "Query is too complex for automatic decomposition",
    "Requires deep domain expertise in distributed systems",
    "Missing clear requirements for Raft implementation specifics"
  ],
  "suggestions": [
    "Break query into smaller parts (e.g., start with 'Implement leader election in Raft')",
    "Provide more context about existing system architecture",
    "Consider using a reference implementation as a starting point"
  ]
}
```

## Conclusion

Verification checkpoints are critical for ensuring SOAR pipeline quality. The 0.7/0.5 thresholds, 0.4/0.2/0.2/0.2 weights, and max 2 retry strategy balance quality, cost, and throughput. Regular monitoring and calibration ensure the verification system adapts to real-world usage patterns.
