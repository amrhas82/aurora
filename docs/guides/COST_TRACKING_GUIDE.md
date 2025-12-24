# Cost Tracking and Budget Enforcement Guide

## Overview

AURORA tracks LLM costs in real-time and enforces monthly budgets to prevent runaway expenses. This guide explains how cost tracking works, how to set budgets, and how to optimize costs.

## Cost Tracking Architecture

### Cost Calculation

Costs are calculated at each LLM call site based on token usage and provider-specific pricing.

```python
# Pricing (as of December 2024)
MODEL_PRICING = {
    # Anthropic Claude (prices per million tokens)
    "claude-opus-4-20250514": ModelPricing(15.0, 75.0),   # Input: $15, Output: $75
    "claude-sonnet-4-20250514": ModelPricing(3.0, 15.0),  # Input: $3, Output: $15
    "claude-3-5-haiku-20241022": ModelPricing(0.8, 4.0),  # Input: $0.80, Output: $4

    # OpenAI GPT
    "gpt-4-turbo": ModelPricing(10.0, 30.0),
    "gpt-3.5-turbo": ModelPricing(0.5, 1.5),

    # Ollama (local, free)
    "llama3": ModelPricing(0.0, 0.0),
}

# Cost calculation
cost_usd = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
```

### Cost Tracking Points

Costs are tracked at every phase that calls an LLM:

1. **Phase 1 (Assess)**: Tier 2 LLM verification
   - Model: Haiku 3.5
   - Average: $0.0002/query (30-40% of queries)

2. **Phase 3 (Decompose)**: Query decomposition
   - Model: Sonnet 4 (MEDIUM/COMPLEX), Opus 4 (CRITICAL)
   - Average: $0.02-0.10/query

3. **Phase 4 (Verify)**: Decomposition verification
   - Model: Haiku 3.5 (Option A), Sonnet 4 (Option B)
   - Average: $0.001-0.01/query

4. **Phase 6 (Collect)**: Agent execution (if agents use LLMs)
   - Model: Varies by agent
   - Average: $0.01-0.50/subgoal

5. **Phase 7 (Synthesize)**: Result synthesis
   - Model: Sonnet 4
   - Average: $0.01-0.05/query

### Total Query Costs

**Simple Query** (keyword assessment, direct LLM):
- $0.001-0.005

**Medium Query** (2-3 subgoals, self-verification):
- $0.05-0.15

**Complex Query** (4-6 subgoals, adversarial verification, parallel execution):
- $0.30-1.00

**Critical Query** (6+ subgoals, Opus 4, adversarial verification):
- $1.00-5.00

## Budget Configuration

### Setting Monthly Budget

Budget is stored in `~/.aurora/budget_tracker.json`.

**Initialize Budget**:
```python
from aurora_core.budget import CostTracker

tracker = CostTracker()
tracker.set_monthly_limit(limit_usd=100.0)  # $100/month
```

**Budget File Format**:
```json
{
  "monthly_limit_usd": 100.0,
  "current_period": "2025-01",
  "current_usage_usd": 23.45,
  "history": [
    {
      "timestamp": "2025-01-15T10:30:00",
      "model": "claude-sonnet-4",
      "input_tokens": 1500,
      "output_tokens": 800,
      "cost_usd": 0.0165,
      "operation": "decompose",
      "query_id": "q_abc123"
    }
  ]
}
```

### Budget Limits

**Soft Limit (80%)**:
- Warning logged
- Query allowed to proceed
- Notification sent (if configured)

**Hard Limit (100%)**:
- Query rejected with error
- No LLM calls made
- User must increase limit or wait for new period

**Example**:
```python
# Query cost estimation: $0.50
# Current usage: $85 / $100 limit (85%)

# Soft limit exceeded (80%)
logger.warning("Budget at 85%, approaching limit")

# Hard limit NOT exceeded (100%)
# Query proceeds normally
```

### Period Management

Budgets reset monthly:
- Period format: `YYYY-MM` (e.g., "2025-01")
- Auto-reset on first query of new month
- History preserved for analysis

**Monthly Reset**:
```python
# January 31, 2025: usage = $95 / $100
# February 1, 2025: New period starts
{
  "current_period": "2025-02",
  "current_usage_usd": 0.0,  # Reset
  "monthly_limit_usd": 100.0  # Unchanged
}
```

## Pre-Query Budget Check

Before executing a query, AURORA estimates cost and checks budget:

```python
# 1. Estimate cost based on complexity
if complexity == "SIMPLE":
    estimated_cost = 0.002
elif complexity == "MEDIUM":
    estimated_cost = 0.10
elif complexity == "COMPLEX":
    estimated_cost = 0.50
elif complexity == "CRITICAL":
    estimated_cost = 2.00

# 2. Check budget
if tracker.current_usage + estimated_cost > tracker.monthly_limit:
    raise BudgetExceededError(
        f"Estimated cost ${estimated_cost:.2f} would exceed "
        f"monthly limit ${tracker.monthly_limit:.2f} "
        f"(current: ${tracker.current_usage:.2f})"
    )

# 3. Proceed with query
# (Actual cost tracked during execution)
```

## Post-Query Cost Recording

After query execution, actual cost is recorded:

```python
# Sum costs from all phases
total_cost = (
    assess_cost +
    decompose_cost +
    verify_cost +
    collect_cost +  # Sum across all agents
    synthesize_cost
)

# Record to tracker
tracker.record_cost(
    model="claude-sonnet-4",
    input_tokens=total_input_tokens,
    output_tokens=total_output_tokens,
    cost_usd=total_cost,
    operation="full_query",
    query_id=query_id
)

# Include in response metadata
response["metadata"]["cost"] = {
    "estimated_cost_usd": estimated_cost,
    "actual_cost_usd": total_cost,
    "breakdown": {
        "assess": assess_cost,
        "decompose": decompose_cost,
        "verify": verify_cost,
        "collect": collect_cost,
        "synthesize": synthesize_cost
    },
    "tokens_used": {
        "input": total_input_tokens,
        "output": total_output_tokens
    }
}
```

## Cost Optimization Strategies

### 1. Keyword Assessment (60-70% cost savings)

**Problem**: Every query using LLM assessment costs $0.0002

**Solution**: Use keyword classifier for 60-70% of queries

**Implementation**:
```python
# Phase 1: Try keyword first
complexity, confidence = assess_tier1_keyword(query)

if confidence >= 0.8 and score not in [0.4, 0.6]:
    # High confidence, skip LLM
    return {"complexity": complexity, "method": "keyword", "cost": 0.0}
else:
    # Borderline, use LLM
    return assess_tier2_llm(query)  # Cost: $0.0002
```

**Impact**:
- Keyword-only: $0.00/assessment
- LLM: $0.0002/assessment
- Average: $0.00006/assessment (70% savings)

### 2. Verification Option Selection

**Problem**: Adversarial verification (Option B) costs 10x more than self-verification (Option A)

**Solution**: Use Option A for MEDIUM queries, Option B only for COMPLEX/CRITICAL

**Implementation**:
```python
if complexity == "MEDIUM":
    verification_option = "self"  # Haiku 3.5: $0.001
elif complexity in ["COMPLEX", "CRITICAL"]:
    verification_option = "adversarial"  # Sonnet 4: $0.01
```

**Impact**:
- 70% of queries are MEDIUM → Option A ($0.001)
- 30% of queries are COMPLEX/CRITICAL → Option B ($0.01)
- Average: $0.0037/verification (vs $0.01 for all Option B)

### 3. Model Selection by Complexity

**Problem**: Using Opus 4 ($15/$75 per MTok) for all queries is expensive

**Solution**: Tier models by complexity

**Implementation**:
```python
if complexity == "SIMPLE":
    model = "claude-3-5-haiku-20241022"  # $0.80/$4
elif complexity == "MEDIUM":
    model = "claude-sonnet-4-20250514"  # $3/$15
elif complexity in ["COMPLEX", "CRITICAL"]:
    model = "claude-opus-4-20250514"  # $15/$75
```

**Impact**:
- SIMPLE (30% queries): Haiku 3.5 ($0.002/query)
- MEDIUM (50% queries): Sonnet 4 ($0.10/query)
- COMPLEX (20% queries): Opus 4 ($0.50/query)
- Average: $0.11/query (vs $0.50 all Opus 4)

### 4. Parallel Agent Execution

**Problem**: Sequential execution increases latency, which increases timeout risk

**Solution**: Execute independent subgoals in parallel

**Implementation**:
```python
# Sequential (4 agents × 3s each = 12s)
result1 = await agent1.execute(subgoal1)
result2 = await agent2.execute(subgoal2)
result3 = await agent3.execute(subgoal3)
result4 = await agent4.execute(subgoal4)

# Parallel (max(3s, 3s, 3s, 3s) = 3s)
results = await asyncio.gather(
    agent1.execute(subgoal1),
    agent2.execute(subgoal2),
    agent3.execute(subgoal3),
    agent4.execute(subgoal4)
)
```

**Impact**:
- Reduced timeout risk → fewer retries → lower cost
- Faster user feedback → better experience

### 5. Caching and Reuse

**Problem**: Repeated queries re-decompose and re-execute

**Solution**: Cache successful reasoning patterns

**Implementation**:
```python
# Phase 2: Check for similar cached pattern
cached_pattern = store.retrieve_reasoning_chunk(
    pattern=query_pattern,
    similarity_threshold=0.85
)

if cached_pattern and cached_pattern.success_score >= 0.8:
    # Reuse decomposition, skip phases 3-4
    decomposition = cached_pattern.subgoals
    cost_saved = decompose_cost + verify_cost  # ~$0.03
```

**Impact** (Phase 3 target):
- 20% cache hit rate → $0.03 savings × 20% = $0.006/query average savings
- Over 10,000 queries → $60 saved

### 6. Early Exit for SIMPLE Queries

**Problem**: SIMPLE queries don't need decomposition/verification/routing

**Solution**: Direct LLM call after retrieval

**Implementation**:
```python
if complexity == "SIMPLE":
    # Skip phases 3-7
    context = retrieve_context(query, budget=5)
    answer = llm_client.generate(query, context=context)
    return format_response(answer)
```

**Impact**:
- SIMPLE query cost: $0.002 (vs $0.05 with full pipeline)
- 30% of queries are SIMPLE → $0.014/query average savings

## Monitoring and Alerts

### Budget Dashboard

Track budget status:
```python
status = tracker.get_status()
print(f"""
Budget Status:
  Period: {status['period']}
  Limit: ${status['limit']:.2f}
  Used: ${status['used']:.2f}
  Remaining: ${status['remaining']:.2f}
  Percentage: {status['percentage']:.1f}%
""")
```

### Cost Analytics

Analyze spending patterns:
```python
# Group by operation type
costs_by_operation = tracker.get_costs_by_operation("2025-01")
# {
#   "assess": 0.50,
#   "decompose": 12.30,
#   "verify": 2.10,
#   "collect": 45.60,
#   "synthesize": 8.95
# }

# Group by query complexity
costs_by_complexity = tracker.get_costs_by_complexity("2025-01")
# {
#   "SIMPLE": 2.30,
#   "MEDIUM": 38.50,
#   "COMPLEX": 28.65,
#   "CRITICAL": 0.00
# }
```

### Alerts

**Alert: Approaching Limit (80%)**
```
WARNING: Budget at 80% ($80 / $100)
Remaining budget: $20
Estimated queries remaining: ~200 (SIMPLE) or ~20 (COMPLEX)
Action: Monitor usage or increase limit
```

**Alert: Limit Exceeded (100%)**
```
ERROR: Budget limit exceeded ($100 / $100)
Query rejected to prevent overspending
Action: Increase monthly limit or wait for new period (resets 2025-02-01)
```

**Alert: High Cost Query**
```
WARNING: Query cost $2.50 (5% of monthly budget)
Complexity: CRITICAL
Subgoals: 8
Action: Consider breaking into smaller queries
```

## Best Practices

### For Users

1. **Set Realistic Budgets**
   - $50/month: ~500 SIMPLE queries or ~50 MEDIUM queries
   - $100/month: ~1000 SIMPLE queries or ~100 MEDIUM queries
   - $500/month: ~500 COMPLEX queries or ~5000 SIMPLE queries

2. **Monitor Usage Regularly**
   - Check budget status weekly
   - Review high-cost queries
   - Adjust limits before hitting cap

3. **Optimize Query Complexity**
   - Phrase queries clearly to reduce decomposition complexity
   - Break large tasks into smaller queries
   - Use SIMPLE queries when possible (definitions, lookups, etc.)

4. **Leverage Caching** (Phase 3)
   - Repeat similar queries to benefit from cached patterns
   - Review cached patterns to understand what works

### For Administrators

1. **Set Team Budgets**
   - Allocate budgets per team/user
   - Monitor team spending
   - Set alerts at 70% threshold

2. **Cost Optimization**
   - Enable keyword assessment (default: on)
   - Use local models (Ollama) for development/testing
   - Implement query quotas for expensive operations

3. **Track ROI**
   - Measure cost per completed task
   - Compare to human developer cost
   - Justify budget increases with productivity data

4. **Regular Audits**
   - Review top 10 most expensive queries monthly
   - Identify optimization opportunities
   - Update documentation with cost-saving patterns

## Troubleshooting

### Issue: Budget Exceeded Mid-Month

**Symptoms**:
```
BudgetExceededError: Monthly limit $100 exceeded (current: $102.50)
```

**Solutions**:
1. Increase limit: `tracker.set_monthly_limit(200.0)`
2. Wait for new period (automatic reset)
3. Use local models (Ollama) for non-critical queries
4. Review high-cost queries and optimize

### Issue: Unexpectedly High Costs

**Symptoms**:
- Query cost 10x higher than expected
- Rapid budget depletion

**Debug Steps**:
1. Check cost breakdown in response metadata
2. Look for retry loops (failed verifications)
3. Check agent execution (LLM-based agents expensive)
4. Review token counts (abnormally high = possible issue)

**Example**:
```python
response["metadata"]["cost"]["breakdown"]
# {
#   "assess": 0.0002,
#   "decompose": 0.05,
#   "verify": 0.20,  # ← HIGH: Multiple retries?
#   "collect": 2.50,  # ← HIGH: LLM-based agents?
#   "synthesize": 0.03
# }
```

### Issue: Cost Tracking Inaccurate

**Symptoms**:
- Actual costs don't match estimates
- Budget tracker shows different amount than AWS/Anthropic bill

**Causes**:
1. Token counting inaccurate (estimate vs actual)
2. Pricing data outdated
3. Additional costs not tracked (API fees, etc.)

**Solutions**:
1. Update `MODEL_PRICING` with latest prices
2. Reconcile with provider bills monthly
3. Add buffer (10-20%) to budget for discrepancies

## Cost Estimation Examples

### Example 1: Simple Query

**Query**: "What does the authenticate function do?"

**Estimated Cost**:
- Assess (keyword): $0.00
- Retrieve: $0.00 (no LLM)
- Direct LLM: $0.002 (Haiku 3.5, ~500 tokens)
- **Total**: $0.002

**Actual Cost**: $0.0018 (slight token variation)

### Example 2: Medium Query

**Query**: "Refactor the billing module to use decimal instead of float"

**Estimated Cost**:
- Assess (LLM): $0.0002
- Retrieve: $0.00
- Decompose: $0.02 (Sonnet 4, ~1500 tokens)
- Verify (Option A): $0.001
- Collect (3 agents): $0.05 (file ops, no LLM)
- Synthesize: $0.01 (Sonnet 4, ~800 tokens)
- **Total**: $0.08

**Actual Cost**: $0.09 (one agent retry)

### Example 3: Complex Query

**Query**: "Implement OAuth2 authentication system with token refresh and role-based access control"

**Estimated Cost**:
- Assess (LLM): $0.0002
- Retrieve: $0.00
- Decompose: $0.10 (Opus 4, ~2000 tokens)
- Verify (Option B): $0.01 (Sonnet 4, adversarial)
- Collect (6 agents, 2 use LLM): $0.40
- Synthesize: $0.03 (Sonnet 4, ~1000 tokens)
- **Total**: $0.54

**Actual Cost**: $0.62 (one verification retry)

## Conclusion

Cost tracking ensures AURORA remains economical while delivering high-quality results. By setting appropriate budgets, monitoring usage, and applying optimization strategies, users can achieve excellent cost-performance ratios. For typical usage (50% SIMPLE, 40% MEDIUM, 10% COMPLEX), expect $100/month to support 500-1000 queries.
