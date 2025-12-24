# Prompt Engineering Guide for SOAR Pipeline

## Overview

The SOAR pipeline uses carefully crafted prompts at multiple phases to achieve reliable, structured outputs from LLMs. This guide explains the prompt engineering techniques used and how to optimize them.

## Core Principles

### 1. JSON-Only Output Enforcement

**Problem**: LLMs often wrap JSON in markdown code blocks or add explanatory text.

**Solution**: Explicit instructions + robust extraction

**Implementation**:
```python
# In prompt template
prompt += """
OUTPUT FORMAT:
Return ONLY valid JSON matching this schema. No markdown, no code blocks, no explanations.

Example:
{"key": "value"}

YOUR OUTPUT (JSON only):
"""

# In LLM client (automatic extraction)
def generate_json(self, prompt):
    response = self.generate(prompt)
    # Extract JSON even if wrapped in ```json...```
    json_text = self._extract_json(response.content)
    return json.loads(json_text)
```

**Key Techniques**:
- **Explicit prohibition**: "No markdown, no code blocks"
- **Show example**: Provide JSON-only example
- **Position instruction**: Place at end of prompt (recency effect)
- **Fallback extraction**: Parse markdown code blocks if present

### 2. Few-Shot Example Scaling

**Problem**: Different complexities need different amounts of guidance.

**Solution**: Scale examples by complexity level

**Implementation**:
```python
EXAMPLES_BY_COMPLEXITY = {
    "SIMPLE": 0,    # No examples needed (shouldn't reach decomposition)
    "MEDIUM": 2,    # Basic guidance
    "COMPLEX": 4,   # More nuanced examples
    "CRITICAL": 6   # Maximum guidance for high-stakes queries
}

def build_prompt(query, complexity):
    examples = load_examples(complexity)
    prompt = f"""
Decompose this {complexity} query into subgoals.

EXAMPLES:
{format_examples(examples)}

QUERY TO DECOMPOSE:
{query}
"""
    return prompt
```

**Why Scale?**:
- **Cost**: Fewer examples = fewer tokens = lower cost
- **Quality**: Complex queries need more guidance
- **Overfitting**: Too many examples can reduce adaptability

**Calibration**:
- MEDIUM (2 examples): One simple decomposition, one with moderate complexity
- COMPLEX (4 examples): Include parallel execution, dependencies, error handling
- CRITICAL (6 examples): Add security considerations, compliance, extensive validation

### 3. Schema Enforcement

**Problem**: Free-form LLM output is unpredictable and hard to parse.

**Solution**: Provide explicit JSON schema

**Implementation**:
```python
prompt += """
SCHEMA:
{
  "goal": string (high-level objective),
  "subgoals": [
    {
      "id": string (unique identifier, e.g., "sg1"),
      "description": string (what needs to be done),
      "assigned_agent": string (suggested agent name),
      "criticality": string ("HIGH" | "MEDIUM" | "LOW"),
      "dependencies": [string] (list of prerequisite subgoal IDs)
    }
  ],
  "execution_order": [
    {
      "phase": string ("sequential" | "parallel"),
      "subgoals": [string] (list of subgoal IDs)
    }
  ],
  "expected_tools": [string] (list of tool types)
}

REQUIRED FIELDS: goal, subgoals, execution_order, expected_tools
VALIDATION: Each subgoal must have id, description, assigned_agent
"""
```

**Schema Benefits**:
- **Predictability**: Always get same structure
- **Validation**: Easy to check required fields
- **Documentation**: Schema is self-documenting
- **Type Safety**: Consumers can rely on structure

### 4. Contextual Prompt Building

**Problem**: Generic prompts don't leverage available context.

**Solution**: Inject relevant context dynamically

**Implementation**:
```python
def build_decompose_prompt(query, complexity, context_summary, available_agents):
    prompt = f"""
Decompose this query into actionable subgoals.

QUERY: {query}
COMPLEXITY: {complexity}

AVAILABLE CONTEXT:
{context_summary}

AVAILABLE AGENTS:
{format_agent_list(available_agents)}

IMPORTANT: Only suggest agents from the available list above.
If no suitable agent exists, use "generic-executor".
"""
    return prompt
```

**Context Types**:
- **Code context**: Retrieved CodeChunks summarized
- **Reasoning context**: Similar past patterns
- **Agent registry**: Available agents and capabilities
- **Previous attempts**: Retry feedback from failed verification

**Context Limits**:
- Keep context summary concise (300-500 tokens)
- Prioritize relevance over completeness
- Too much context reduces focus

## Prompt Templates by Phase

### Phase 1: Complexity Assessment (Tier 2)

**Purpose**: LLM-based verification when keyword classifier has low confidence.

**Prompt Structure**:
```python
"""
Assess the complexity of this software engineering query.

QUERY: {query}

KEYWORD ASSESSMENT: {keyword_result}
- Suggested complexity: {keyword_complexity}
- Confidence: {keyword_confidence}
- Reasoning: {keyword_reasoning}

COMPLEXITY LEVELS:
- SIMPLE: Single-step, informational, definitions, lookups
- MEDIUM: Multi-step, code modifications, refactoring, new features
- COMPLEX: System integration, multi-component, architectural changes
- CRITICAL: Security-critical, compliance, high-stakes decisions

CONSIDERATIONS:
- Does it require multiple steps or components?
- Does it involve architectural decisions?
- Is it security or compliance critical?
- Does it require coordination across multiple agents?

OUTPUT (JSON only):
{
  "complexity": "SIMPLE" | "MEDIUM" | "COMPLEX" | "CRITICAL",
  "confidence": 0.0-1.0,
  "reasoning": "explanation of classification",
  "recommended_verification": "self" | "adversarial"
}
"""
```

**Key Techniques**:
- Include keyword result for context (LLM can agree or override)
- Clear definitions prevent ambiguity
- Explicit considerations guide reasoning
- Request confidence score for calibration

### Phase 3: Query Decomposition

**Prompt Structure**:
```python
"""
Decompose this {complexity} query into actionable subgoals.

{few_shot_examples}

QUERY: {query}

AVAILABLE CONTEXT:
{context_summary}

AVAILABLE AGENTS:
- code-analyzer: Analyzes code structure, complexity, dependencies
- file-writer: Creates or modifies files
- test-runner: Executes tests and reports results
- generic-executor: General-purpose agent for any task

DECOMPOSITION GUIDELINES:
1. Break query into 2-6 concrete subgoals
2. Each subgoal should be independently verifiable
3. Specify dependencies if one subgoal requires another's output
4. Mark criticality (HIGH for must-succeed, LOW for optional)
5. Suggest execution order (parallel for independent subgoals)
6. List expected tools for each subgoal

{retry_feedback if present}

OUTPUT SCHEMA:
{json_schema}

YOUR DECOMPOSITION (JSON only):
"""
```

**Optimization Strategies**:
- **Dynamic examples**: Load based on query similarity (Phase 3 enhancement)
- **Agent filtering**: Only show relevant agents (reduces decision space)
- **Retry feedback integration**: Inject feedback from verification failures
- **Token budget**: Limit context to 2000 tokens to control cost

### Phase 4: Decomposition Verification

**Option A: Self-Verification**

Used for MEDIUM complexity queries (cost optimization).

```python
"""
Verify the quality of this query decomposition.

ORIGINAL QUERY: {query}

DECOMPOSITION:
{decomposition_json}

VERIFICATION CRITERIA:
1. Completeness (0.0-1.0): Does decomposition cover all query aspects?
   - Missing steps, error handling, testing, documentation?
   - All requirements addressed?

2. Consistency (0.0-1.0): Are subgoals compatible?
   - No contradictions or conflicts?
   - Dependencies make sense?

3. Groundedness (0.0-1.0): Is decomposition grounded in available context?
   - References existing code/patterns?
   - Agents actually available?

4. Routability (0.0-1.0): Can suggested agents execute subgoals?
   - Agents exist in registry?
   - Agents have required capabilities?

SCORING GUIDELINES:
- 1.0: Excellent (no issues)
- 0.8: Good (minor issues, acceptable)
- 0.6: Fair (needs improvement)
- 0.4: Poor (significant issues)
- 0.2: Very poor (fundamental flaws)

OUTPUT (JSON only):
{
  "completeness": 0.0-1.0,
  "consistency": 0.0-1.0,
  "groundedness": 0.0-1.0,
  "routability": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "issues": [string] (list of identified problems),
  "suggestions": [string] (list of improvements)
}
"""
```

**Option B: Adversarial Verification**

Used for COMPLEX/CRITICAL queries (higher quality).

```python
"""
You are a critical reviewer. Find flaws in this query decomposition.

ORIGINAL QUERY: {query}

PROPOSED DECOMPOSITION:
{decomposition_json}

YOUR ROLE:
You are a senior engineer conducting a thorough code review.
Be skeptical, look for edge cases, question assumptions.
Your goal is to identify any issues before expensive execution.

RED FLAGS TO CHECK:
- Missing error handling or validation
- Untested assumptions about existing code
- Security vulnerabilities or risks
- Performance concerns
- Incomplete requirements coverage
- Conflicting technical approaches
- Suggested agents that don't exist
- Dependencies that create deadlocks
- Critical subgoals that could fail

VERIFICATION CRITERIA (same as Option A):
[completeness, consistency, groundedness, routability]

BE THOROUGH:
Even minor issues should be noted. The cost of fixing after
agent execution is 10x higher than fixing decomposition now.

OUTPUT (JSON only):
{same schema as Option A}
"""
```

**Key Difference**:
- **Option A**: Reviews own work (faster, cheaper, sufficient for routine)
- **Option B**: Adversarial stance (catches subtle issues, required for high-stakes)

### Phase 7: Synthesis

**Prompt Structure**:
```python
"""
Synthesize agent outputs into a coherent final answer.

ORIGINAL QUERY: {query}

AGENT OUTPUTS:
{formatted_agent_outputs}

DECOMPOSITION GOAL: {goal}

SYNTHESIS REQUIREMENTS:
1. Combine all agent outputs into natural language answer
2. Every claim must be traceable to an agent output
3. Acknowledge any incomplete or low-confidence results
4. Explain how subgoals relate to final answer
5. Use clear, professional tone
6. 3-8 sentences preferred (concise but complete)

TRACEABILITY:
For each claim in your answer, reference the agent output that supports it.
Do not hallucinate or make unsupported claims.

EXAMPLE SYNTHESIS:
"Refactored billing module to use Decimal (code-analyzer found 15 float uses,
file-writer replaced with Decimal, test-runner confirms all 32 tests passing).
Changes applied to billing.py and tests/test_billing.py."

YOUR SYNTHESIS (natural language, not JSON):
"""
```

**Synthesis vs Decomposition**:
- **Decomposition**: Structured JSON output
- **Synthesis**: Natural language (easier for users to read)
- **Traceability**: Critical requirement to prevent hallucination

## Advanced Techniques

### 1. Prompt Chaining

**Concept**: Use output from one prompt as input to next prompt.

**Example**: Decomposition → Verification → Retry with Feedback

```python
# Step 1: Decomposition
decomposition = llm.generate_json(decompose_prompt)

# Step 2: Verification
verification = llm.generate_json(verify_prompt(decomposition))

# Step 3: If failed, retry with feedback
if verification["verdict"] == "RETRY":
    feedback = generate_feedback(verification)
    # Chain: Inject feedback into decomposition prompt
    decomposition = llm.generate_json(decompose_prompt + feedback)
```

**Benefits**:
- Iterative refinement
- Error correction
- Quality gates at each step

### 2. Temperature Tuning

**Purpose**: Control randomness/creativity in LLM outputs.

**Guidelines**:
```python
TEMPERATURE_BY_PHASE = {
    "assess": 0.3,      # Low: Want consistent classification
    "decompose": 0.7,   # Medium-high: Want creative but structured
    "verify": 0.5,      # Medium: Balance thoroughness and consistency
    "synthesize": 0.7   # Medium-high: Natural language flexibility
}
```

**Rules**:
- **0.0-0.3**: Deterministic, consistent (classification, structured tasks)
- **0.4-0.7**: Balanced creativity and consistency (decomposition, synthesis)
- **0.8-1.0**: Highly creative (brainstorming, NOT used in SOAR)

### 3. System Prompt vs User Prompt

**System Prompt** (persistent, sets context):
```python
system_prompt = """
You are an expert software engineer using the SOAR reasoning framework.
Your task is to decompose queries into actionable subgoals.
Always return valid JSON matching the provided schema.
"""
```

**User Prompt** (query-specific):
```python
user_prompt = f"""
Decompose this query: {query}

AVAILABLE AGENTS: {agents}

OUTPUT (JSON only):
"""
```

**Best Practice**:
- System prompt: Role, framework, output format
- User prompt: Specific task, context, schema

### 4. Calibration with Examples

**Purpose**: Ensure LLM scoring aligns with human judgment.

**Method**:
1. Collect ground truth (human-labeled decompositions with scores)
2. Include labeled examples in few-shot prompts
3. Measure correlation between LLM scores and human scores
4. Adjust threshold if correlation < 0.7

**Example Calibration Data**:
```json
{
  "query": "Add authentication",
  "decomposition": {...},
  "human_score": 0.65,
  "llm_score": 0.72,
  "human_verdict": "RETRY",
  "issues": ["Missing error handling", "No tests"]
}
```

## Common Pitfalls and Solutions

### Pitfall 1: Inconsistent JSON Format

**Problem**: LLM sometimes adds markdown, sometimes doesn't.

**Solution**: Robust JSON extraction

```python
def _extract_json(self, text):
    # Try direct parse first
    try:
        return json.loads(text)
    except:
        pass

    # Try extracting from markdown code block
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # Try finding JSON object
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError("No valid JSON found in response")
```

### Pitfall 2: Overfitting to Examples

**Problem**: LLM copies example structure too literally.

**Solution**: Diverse examples + explicit variation instruction

```python
prompt += """
IMPORTANT: These examples show the STRUCTURE, not the content.
Your decomposition should be tailored to the specific query.
Do NOT copy example content verbatim.
"""
```

### Pitfall 3: Verbose Explanations in JSON

**Problem**: LLM adds reasoning inside JSON fields.

**Solution**: Explicit length limits

```python
schema += """
"reasoning": string (1-2 sentences MAX, concise explanation)
"issues": [string] (each issue 1 sentence, max 5 issues)
```

### Pitfall 4: Ignoring Available Context

**Problem**: LLM suggests agents that don't exist.

**Solution**: Explicit validation instruction

```python
prompt += """
CRITICAL: Only use agents from the AVAILABLE AGENTS list above.
If you suggest an agent not in the list, the decomposition will FAIL.
When in doubt, use "generic-executor".
"""
```

### Pitfall 5: Low Verification Catch Rate

**Problem**: Verification passes bad decompositions.

**Solution**: Strengthen verification prompt + add calibration examples

```python
prompt += """
ERROR PATTERNS TO WATCH FOR:
- Missing subgoals (incomplete coverage)
- Contradictory subgoals (technical conflicts)
- Unrealistic subgoals (assume non-existent code)
- No error handling or testing subgoals
- Dependencies that create circular waits
- Vague descriptions ("implement feature" too broad)

REMEMBER: Better to RETRY now than fail during expensive agent execution.
Be strict in your assessment.
"""
```

## Monitoring and Optimization

### Metrics to Track

1. **JSON Parse Success Rate**: Target 99%+
   - Track: parse_errors / total_llm_calls
   - Fix: Improve JSON extraction robustness

2. **Verification Calibration**: Target correlation ≥0.7
   - Track: correlation(llm_score, human_score)
   - Fix: Adjust scoring guidelines, add calibration examples

3. **Retry Rate**: Target <30%
   - Track: retries / total_decompositions
   - Fix: Improve decomposition prompt, better examples

4. **Average Token Usage**: Target <2000 tokens/query
   - Track: mean(input_tokens + output_tokens)
   - Fix: Trim context, fewer examples for SIMPLE queries

### A/B Testing Prompts

**Method**:
1. Create variant prompt
2. Run on 50 test queries
3. Compare metrics (quality, cost, latency)
4. Keep better prompt

**Example**:
```python
# Variant A: Current prompt (baseline)
# Variant B: Add "Be concise" instruction

results_A = [run_query(q, prompt_A) for q in test_queries]
results_B = [run_query(q, prompt_B) for q in test_queries]

compare_metrics(results_A, results_B)
# Output:
# Quality: A=0.85, B=0.84 (slight drop)
# Cost: A=$0.10, B=$0.08 (20% savings)
# Latency: A=3.2s, B=2.8s (faster)
# Decision: Use B (cost savings worth minor quality drop)
```

## Conclusion

Effective prompt engineering is critical for SOAR pipeline reliability. Key principles:

1. **JSON-only enforcement** with robust extraction
2. **Few-shot scaling** by complexity
3. **Explicit schemas** with validation
4. **Contextual building** with relevant info
5. **Temperature tuning** by phase
6. **Calibration** with ground truth

Regular monitoring and A/B testing ensure prompts remain optimal as LLM capabilities evolve.
