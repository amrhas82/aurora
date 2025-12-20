# AURORA-Context: JSON Prompt Test Suite

**Purpose**: Test prompts to validate LLM JSON format compatibility before implementation

**Date**: December 12, 2025

---

## Test Scenario: Agentic AI Market Research

All tests use this practical scenario: Research the current agentic AI landscape, identify top 3 leading frameworks, their pain points, and recommend a strategy.

---

## Test 1: Complexity Assessment

**Test**: Can LLM classify query complexity and return valid JSON?

```json
{
  "system": "You are a complexity classifier. Respond with ONLY valid JSON.",
  "query": "Research the current agentic AI landscape. Identify the top 3 leading frameworks (like AutoGPT, BabyAGI, LangChain Agents), analyze their key pain points (reliability, cost, ease of use), and recommend a differentiation strategy for a new framework.",
  "output_schema": {
    "complexity": "simple | medium | complex | critical",
    "confidence": "number (0.0-1.0)",
    "reasoning": "string (2-3 sentences)",
    "indicators": ["array", "of", "keywords"],
    "recommended_verification": "none | option_a | option_b | option_c"
  },
  "respond_with": "JSON only, no markdown, no explanation"
}
```

**Expected Output (Sample)**:
```json
{
  "complexity": "complex",
  "confidence": 0.88,
  "reasoning": "This query requires multi-step research (identify frameworks), comparative analysis (pain points), and synthesis (strategy recommendation). It involves gathering external data, analyzing trade-offs, and making strategic recommendations based on competitive landscape.",
  "indicators": ["research", "analyze", "identify", "top 3", "pain points", "recommend", "strategy"],
  "recommended_verification": "option_b"
}
```

**Validation Checklist**:
- [ ] Valid JSON (parseable)
- [ ] `complexity` is one of: simple, medium, complex, critical
- [ ] `confidence` is between 0.0 and 1.0
- [ ] `reasoning` is 2-3 sentences
- [ ] `indicators` is an array of strings
- [ ] `recommended_verification` matches one of the allowed values

---

## Test 2: Decomposition

**Test**: Can LLM decompose complex query into structured JSON subgoals?

```json
{
  "system": "You are a reasoning decomposition engine. Respond with ONLY valid JSON.",
  "query": "Research the current agentic AI landscape. Identify the top 3 leading frameworks (like AutoGPT, BabyAGI, LangChain Agents), analyze their key pain points (reliability, cost, ease of use), and recommend a differentiation strategy for a new framework.",
  "available_agents": [
    {"id": "research-agent", "capabilities": ["web_search", "documentation_lookup"], "domains": ["general"]},
    {"id": "analysis-agent", "capabilities": ["compare_data", "identify_patterns"], "domains": ["general"]},
    {"id": "strategy-agent", "capabilities": ["synthesize_findings", "recommendations"], "domains": ["product", "business"]}
  ],
  "output_schema": {
    "decomposition": {
      "id": "uuid",
      "original_query": "string",
      "given": [{"id": "G1", "fact": "string", "source": "query|context"}],
      "goal": {"description": "string", "success_criteria": ["array"]},
      "subgoals": [{
        "id": "SG1",
        "description": "string",
        "requires": ["G1"],
        "agent": "agent-id",
        "expected_output": "string",
        "depends_on": []
      }],
      "execution_order": ["SG1", "SG2", "SG3"],
      "parallelizable": [["SG1", "SG2"]]
    }
  },
  "respond_with": "JSON only, no markdown, no explanation"
}
```

**Expected Output (Sample)**:
```json
{
  "decomposition": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "original_query": "Research the current agentic AI landscape. Identify the top 3 leading frameworks (like AutoGPT, BabyAGI, LangChain Agents), analyze their key pain points (reliability, cost, ease of use), and recommend a differentiation strategy for a new framework.",
    "given": [
      {"id": "G1", "fact": "Need to identify top 3 agentic AI frameworks", "source": "query"},
      {"id": "G2", "fact": "Examples provided: AutoGPT, BabyAGI, LangChain Agents", "source": "query"},
      {"id": "G3", "fact": "Pain points to analyze: reliability, cost, ease of use", "source": "query"},
      {"id": "G4", "fact": "Need differentiation strategy recommendation", "source": "query"}
    ],
    "goal": {
      "description": "Deliver competitive analysis of agentic AI landscape with strategic differentiation recommendation",
      "success_criteria": [
        "Identified 3 leading frameworks with evidence",
        "Analyzed pain points for each framework across reliability, cost, and ease of use",
        "Provided actionable differentiation strategy with rationale"
      ]
    },
    "subgoals": [
      {
        "id": "SG1",
        "description": "Research and identify top 3 agentic AI frameworks in current market",
        "requires": ["G1", "G2"],
        "agent": "research-agent",
        "expected_output": "List of top 3 frameworks with: name, description, adoption metrics, key features",
        "depends_on": []
      },
      {
        "id": "SG2",
        "description": "For each identified framework, research and document pain points in reliability, cost, and ease of use",
        "requires": ["G3", "SG1.output"],
        "agent": "research-agent",
        "expected_output": "Pain point analysis matrix: framework × [reliability issues, cost factors, usability challenges]",
        "depends_on": ["SG1"]
      },
      {
        "id": "SG3",
        "description": "Analyze pain point patterns across frameworks to identify common weaknesses",
        "requires": ["SG2.output"],
        "agent": "analysis-agent",
        "expected_output": "Analysis of common patterns, gaps, and underserved needs in current frameworks",
        "depends_on": ["SG2"]
      },
      {
        "id": "SG4",
        "description": "Synthesize findings into differentiation strategy recommendation",
        "requires": ["G4", "SG3.output"],
        "agent": "strategy-agent",
        "expected_output": "Recommended differentiation strategy with: target pain point, unique value proposition, competitive positioning",
        "depends_on": ["SG3"]
      }
    ],
    "execution_order": ["SG1", "SG2", "SG3", "SG4"],
    "parallelizable": []
  }
}
```

**Validation Checklist**:
- [ ] Valid JSON (parseable)
- [ ] All required fields present
- [ ] `given` facts trace to query content
- [ ] `subgoals` cover all aspects of goal
- [ ] Dependencies form valid DAG (no cycles)
- [ ] Agent assignments make sense for capabilities
- [ ] `execution_order` respects dependencies
- [ ] `parallelizable` groups don't have dependencies on each other

---

## Test 3: Decomposition Verification

**Test**: Can LLM evaluate decomposition validity WITHOUT solving the problem?

```json
{
  "system": "You are a critical verification engine. Check decomposition validity. Respond with ONLY valid JSON.",
  "task": "Verify decomposition structure and logic (NOT solve the problem).",
  "decomposition": {
    "id": "test-incomplete-decomp",
    "original_query": "Research the current agentic AI landscape. Identify the top 3 leading frameworks, analyze their key pain points (reliability, cost, ease of use), and recommend a differentiation strategy.",
    "given": [
      {"id": "G1", "fact": "Need to identify top 3 frameworks", "source": "query"},
      {"id": "G2", "fact": "Need pain point analysis", "source": "query"}
    ],
    "goal": {
      "description": "Deliver competitive analysis with strategy",
      "success_criteria": ["Top 3 frameworks identified", "Pain points analyzed", "Strategy recommended"]
    },
    "subgoals": [
      {
        "id": "SG1",
        "description": "Research top 3 agentic AI frameworks",
        "requires": ["G1"],
        "agent": "research-agent",
        "expected_output": "List of 3 frameworks",
        "depends_on": []
      },
      {
        "id": "SG2",
        "description": "Analyze pain points for each framework",
        "requires": ["G2"],
        "agent": "analysis-agent",
        "expected_output": "Pain point matrix",
        "depends_on": ["SG1"]
      }
    ],
    "execution_order": ["SG1", "SG2"],
    "parallelizable": []
  },
  "verification_criteria": {
    "completeness": "Do subgoals fully cover the original goal?",
    "consistency": "Do subgoals contradict each other?",
    "groundedness": "Does each subgoal trace to given facts?",
    "routability": "Is agent assignment appropriate?"
  },
  "output_schema": {
    "verification": {
      "decomposition_id": "string",
      "checks": {
        "completeness": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "consistency": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "groundedness": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "routability": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"}
      },
      "overall_score": "0.0-1.0 (weighted average)",
      "verdict": "pass | retry | fail",
      "critical_issues": ["array"],
      "suggestions": ["array"]
    }
  },
  "respond_with": "JSON only, no markdown, no explanation"
}
```

**Expected Output (Sample - for intentionally incomplete decomposition)**:
```json
{
  "verification": {
    "decomposition_id": "test-incomplete-decomp",
    "checks": {
      "completeness": {
        "score": 0.5,
        "pass": false,
        "issues": [
          "Missing subgoal for strategy recommendation - goal explicitly requires it",
          "No given fact (G3) for 'differentiation strategy' requirement"
        ],
        "detail": "Subgoals only cover framework identification (SG1) and pain point analysis (SG2). The strategy recommendation from the original query is not addressed by any subgoal."
      },
      "consistency": {
        "score": 1.0,
        "pass": true,
        "issues": [],
        "detail": "Existing subgoals do not contradict each other. SG2 correctly depends on SG1."
      },
      "groundedness": {
        "score": 0.7,
        "pass": true,
        "issues": [
          "G3 for differentiation strategy requirement is missing from given facts"
        ],
        "detail": "SG1 traces to G1, SG2 traces to G2. However, the strategy requirement mentioned in query was not extracted as a given fact."
      },
      "routability": {
        "score": 0.9,
        "pass": true,
        "issues": [],
        "detail": "research-agent is appropriate for SG1, analysis-agent is appropriate for SG2. Expected outputs are realistic."
      }
    },
    "overall_score": 0.62,
    "verdict": "retry",
    "critical_issues": [
      "Strategy recommendation requirement from original query is not covered by any subgoal"
    ],
    "suggestions": [
      "Add G3: 'Need differentiation strategy recommendation'",
      "Add SG3: 'Synthesize pain point analysis into differentiation strategy' assigned to strategy-agent",
      "Update execution_order to include SG3 after SG2"
    ]
  }
}
```

**Validation Checklist**:
- [ ] Valid JSON (parseable)
- [ ] All checks have scores between 0.0-1.0
- [ ] `pass` boolean matches score (< 0.7 = false, >= 0.7 = true)
- [ ] Issues array populated for scores < 0.9
- [ ] `overall_score` reflects weighted average
- [ ] `verdict` matches score thresholds (>= 0.7 pass, 0.5-0.7 retry, < 0.5 fail)
- [ ] `critical_issues` lists most important problems
- [ ] `suggestions` are actionable

---

## Test 4: Agent Output Verification

**Test**: Can LLM verify agent output addresses assigned subgoal?

```json
{
  "system": "You are a critical output verifier. Respond with ONLY valid JSON.",
  "subgoal": {
    "id": "SG1",
    "description": "Research and identify top 3 agentic AI frameworks in current market",
    "expected_output": "List of top 3 frameworks with: name, description, adoption metrics, key features"
  },
  "agent_output": {
    "frameworks": [
      {
        "name": "LangChain Agents",
        "description": "Framework for building LLM-powered autonomous agents with tool use",
        "adoption": "High - 50k+ GitHub stars, widely used in production",
        "key_features": ["Tool integration", "Memory management", "Multi-agent orchestration"]
      },
      {
        "name": "AutoGPT",
        "description": "Autonomous GPT-4 agent that can create and execute tasks",
        "adoption": "Very High - 150k+ GitHub stars, strong community",
        "key_features": ["Full autonomy", "Self-directed goal pursuit", "Web browsing"]
      },
      {
        "name": "BabyAGI",
        "description": "Task-driven autonomous agent with dynamic task creation",
        "adoption": "Medium - 15k+ GitHub stars, experimental use",
        "key_features": ["Task prioritization", "Dynamic planning", "Vector storage integration"]
      }
    ]
  },
  "verification_criteria": {
    "relevance": "Does output address the subgoal description?",
    "completeness": "Are all elements of expected_output present?",
    "groundedness": "Are claims specific and verifiable?"
  },
  "output_schema": {
    "verification": {
      "subgoal_id": "string",
      "checks": {
        "relevance": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "completeness": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "groundedness": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"}
      },
      "overall_score": "0.0-1.0",
      "verdict": "pass | retry | fail",
      "issues": ["array"],
      "suggestions": ["array if retry"]
    }
  },
  "respond_with": "JSON only, no markdown, no explanation"
}
```

**Expected Output (Sample)**:
```json
{
  "verification": {
    "subgoal_id": "SG1",
    "checks": {
      "relevance": {
        "score": 1.0,
        "pass": true,
        "issues": [],
        "detail": "Output directly addresses the subgoal: identified exactly 3 frameworks from the agentic AI domain."
      },
      "completeness": {
        "score": 1.0,
        "pass": true,
        "issues": [],
        "detail": "All expected output elements present: name, description, adoption metrics (GitHub stars), and key features for each framework."
      },
      "groundedness": {
        "score": 0.9,
        "pass": true,
        "issues": [
          "GitHub star counts are specific and verifiable metrics (good), but no timestamp/source provided"
        ],
        "detail": "Claims are specific (exact star counts) and verifiable (public GitHub data). Minor: source timestamps would improve grounding."
      }
    },
    "overall_score": 0.97,
    "verdict": "pass",
    "issues": [],
    "suggestions": []
  }
}
```

**Validation Checklist**:
- [ ] Valid JSON (parseable)
- [ ] All checks have scores between 0.0-1.0
- [ ] `overall_score` is average of check scores
- [ ] `verdict` matches thresholds
- [ ] `issues` array is empty for pass, populated for retry/fail
- [ ] `suggestions` present only if verdict is retry

---

## Test 5: Synthesis Verification

**Test**: Can LLM verify final answer uses subgoal outputs correctly?

```json
{
  "system": "You are a final synthesis verifier. Respond with ONLY valid JSON.",
  "original_query": "Research the current agentic AI landscape. Identify the top 3 leading frameworks, analyze their key pain points, and recommend a differentiation strategy.",
  "subgoal_outputs": [
    {
      "subgoal_id": "SG1",
      "output": "Top 3: LangChain Agents (high adoption, tool integration), AutoGPT (very high adoption, full autonomy), BabyAGI (medium adoption, task prioritization)"
    },
    {
      "subgoal_id": "SG2",
      "output": "Pain points: LangChain - complexity in setup; AutoGPT - high cost, unreliable execution; BabyAGI - limited production readiness"
    },
    {
      "subgoal_id": "SG3",
      "output": "Common pattern: all frameworks struggle with reliability and production readiness. Gap: no framework optimizes for cost-effective, reliable execution."
    }
  ],
  "synthesis": "Based on competitive analysis, the top 3 agentic AI frameworks are LangChain Agents, AutoGPT, and BabyAGI. LangChain leads in production adoption but suffers from setup complexity. AutoGPT has the largest community but faces reliability and cost challenges. BabyAGI shows promise but lacks production maturity. \n\nKey insight: All frameworks prioritize capability over reliability. Recommended differentiation strategy: Build a reliability-first framework optimized for production use cases, with built-in cost controls and out-of-box deployment. Target enterprise users who need dependable automation over experimental features.",
  "verification_criteria": {
    "addresses_query": "Does answer respond to what was asked?",
    "traceable": "Can claims be traced to subgoal outputs?",
    "consistent": "Are there contradictions?",
    "calibrated": "Is confidence level appropriate?"
  },
  "output_schema": {
    "verification": {
      "checks": {
        "addresses_query": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "traceable": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "consistent": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"},
        "calibrated": {"score": "0.0-1.0", "pass": "bool", "issues": ["array"], "detail": "string"}
      },
      "overall_score": "0.0-1.0",
      "verdict": "pass | retry | fail",
      "cache_recommendation": "cache | no_cache",
      "issues": ["array"],
      "suggestions": ["array if retry"]
    }
  },
  "respond_with": "JSON only, no markdown, no explanation"
}
```

**Expected Output (Sample)**:
```json
{
  "verification": {
    "checks": {
      "addresses_query": {
        "score": 1.0,
        "pass": true,
        "issues": [],
        "detail": "Answer fully addresses all three parts of query: (1) identified top 3 frameworks, (2) analyzed pain points, (3) recommended differentiation strategy."
      },
      "traceable": {
        "score": 0.95,
        "pass": true,
        "issues": [],
        "detail": "All claims trace to subgoal outputs: framework names from SG1, pain points from SG2, differentiation strategy based on SG3's gap analysis. Minor: could explicitly cite subgoal IDs."
      },
      "consistent": {
        "score": 1.0,
        "pass": true,
        "issues": [],
        "detail": "No contradictions detected. Pain points align with differentiation strategy (reliability-first addresses identified reliability gaps)."
      },
      "calibrated": {
        "score": 0.9,
        "pass": true,
        "issues": [],
        "detail": "Confidence is appropriate: makes definitive claims where supported by data (framework identification), acknowledges limitations where present (production maturity). Strategy is framed as recommendation, not certainty."
      }
    },
    "overall_score": 0.96,
    "verdict": "pass",
    "cache_recommendation": "cache",
    "issues": [],
    "suggestions": []
  }
}
```

**Validation Checklist**:
- [ ] Valid JSON (parseable)
- [ ] All checks have scores
- [ ] `cache_recommendation` is "cache" if overall_score >= 0.8, else "no_cache"
- [ ] `verdict` matches thresholds
- [ ] Verification checks LOGIC not correctness (doesn't need to know if LangChain actually has that pain point)

---

## Test 6: Retry Feedback

**Test**: Can LLM provide structured feedback for retry?

```json
{
  "system": "You are a retry coordinator. Respond with ONLY valid JSON.",
  "checkpoint": "decomposition",
  "attempt_number": 1,
  "max_attempts": 2,
  "previous_score": 0.62,
  "verification_result": {
    "checks": {
      "completeness": {"score": 0.5, "issues": ["Missing strategy subgoal"]},
      "consistency": {"score": 1.0, "issues": []},
      "groundedness": {"score": 0.7, "issues": ["Missing G3"]},
      "routability": {"score": 0.9, "issues": []}
    },
    "overall_score": 0.62,
    "verdict": "retry",
    "suggestions": ["Add G3: differentiation strategy", "Add SG3: synthesize strategy"]
  },
  "output_schema": {
    "retry_feedback": {
      "attempt": "number",
      "previous_score": "number",
      "issues": [
        {
          "check": "string (which check failed)",
          "score": "number",
          "issue": "string (what's wrong)",
          "suggestion": "string (how to fix)"
        }
      ],
      "instruction": "string (clear directive for next attempt)",
      "escalate": "bool"
    }
  },
  "respond_with": "JSON only, no markdown, no explanation"
}
```

**Expected Output (Sample)**:
```json
{
  "retry_feedback": {
    "attempt": 1,
    "previous_score": 0.62,
    "issues": [
      {
        "check": "completeness",
        "score": 0.5,
        "issue": "Decomposition missing subgoal for differentiation strategy recommendation",
        "suggestion": "Add given fact G3: 'Need differentiation strategy recommendation' and subgoal SG3: 'Synthesize pain point findings into strategic differentiation recommendation' assigned to strategy-agent"
      },
      {
        "check": "groundedness",
        "score": 0.7,
        "issue": "Strategy requirement from query not captured in given facts",
        "suggestion": "Extract 'recommend differentiation strategy' from original query as explicit given fact before creating subgoals"
      }
    ],
    "instruction": "Add the missing given fact (G3) and create a new subgoal (SG3) to address the strategy recommendation requirement. Ensure SG3 depends on the pain point analysis (SG2) and is assigned to strategy-agent. Update execution_order to include SG3.",
    "escalate": false
  }
}
```

**Validation Checklist**:
- [ ] Valid JSON (parseable)
- [ ] `attempt` matches input
- [ ] `previous_score` matches input
- [ ] `issues` array has entry for each failed check (score < 0.7)
- [ ] Each issue has: check name, score, problem description, actionable suggestion
- [ ] `instruction` is clear and specific
- [ ] `escalate` is false if attempt < max_attempts, true otherwise

---

## How to Use These Tests

### Before MVP Implementation

1. **Run all 6 tests** with your target LLM (Claude, GPT-4, etc.)

2. **Check JSON validity**:
```python
import json
try:
    result = json.loads(llm_output)
    print("✓ Valid JSON")
except json.JSONDecodeError as e:
    print(f"✗ Invalid JSON: {e}")
```

3. **Validate field completeness**:
```python
required_fields = ["complexity", "confidence", "reasoning", "indicators"]
missing = [f for f in required_fields if f not in result]
if missing:
    print(f"✗ Missing fields: {missing}")
else:
    print("✓ All fields present")
```

4. **Test with variations**:
   - Different query complexities (simple, medium, complex)
   - Intentionally good and bad decompositions
   - Edge cases (empty outputs, contradictory subgoals)

### Success Criteria

- **JSON parse rate**: >= 95% (LLM consistently produces valid JSON)
- **Field completeness**: 100% (all required fields always present)
- **Score calibration**: Correlation >= 0.7 between scores and actual quality
- **Verdict accuracy**: Verdicts match score thresholds correctly

### Common Issues to Watch For

1. **Markdown wrapping**: LLM outputs ` ```json ... ``` ` instead of pure JSON
   - **Fix**: Emphasize "JSON only, no markdown" in system prompt

2. **Extra commentary**: LLM adds explanation before/after JSON
   - **Fix**: Test with "Respond with ONLY valid JSON" emphasis

3. **Schema drift**: LLM invents fields not in schema
   - **Fix**: Provide explicit schema in prompt, validate against it

4. **Type mismatches**: String where number expected, etc.
   - **Fix**: Specify types explicitly in schema ("number 0.0-1.0", not just "number")

---

**END OF TEST SUITE**
