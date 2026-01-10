# Your Follow-Up Questions: Direct Answers
## Quick Reference Guide to Implementation Details

**Date**: December 6, 2025

---

## Q1: Where does it search for previous SOAR? In JSON format previous tree?

### Answer: YES, JSON Storage

```
Location: knowledge_base/soar_history/
├── soar_history.json
│   ├── operators
│   │   ├── market_research_first
│   │   │   ├── id: "op_001"
│   │   │   ├── name: "Market Research First"
│   │   │   ├── utility: 0.925 (learned from past successes)
│   │   │   ├── use_count: 47
│   │   │   ├── success_rate: 0.893
│   │   │   └── steps: [step1, step2, step3...]
│   │   └── direct_analysis
│   │       ├── utility: 0.52
│   │       └── ...
│   └── problem_patterns
│       ├── market_analysis_general
│       │   ├── pattern_keywords: ["market", "opportunity", "analysis"]
│       │   ├── successful_operators: [...]
│       │   ├── past_executions: [exec_001, exec_002, ...]
│       │   └── pattern_confidence: 0.87
│       └── technical_design_pattern
│           └── ...
```

**How it's searched:**
1. User sends prompt: "What opportunities in AI market?"
2. Orchestrator extracts keywords: ["opportunities", "AI", "market"]
3. Searches JSON for matching patterns
4. Finds "market_analysis_general" (3 keywords match)
5. Returns recommended operators with learned utilities

---

## Q2: Does it match for similar requests that succeeded? Like market research follows previous path with high scoring?

### Answer: YES, Exactly

```
Flow:

Pattern Found: "market_analysis_general"
├─ Similar patterns: YES (75% keyword match)
├─ Pattern confidence: 87%
├─ Recommended operators:
│   ├─ "market_research_first" (utility: 0.89, success_rate: 89%)
│   ├─ "benchmarking_first" (utility: 0.78, success_rate: 78%)
│   └─ "direct_analysis" (utility: 0.52, success_rate: 52%)
│
└─ Decision:
    ├─ If match > 80%: Skip SOAR, use "market_research_first" directly
    │   (Saves 5-10 seconds)
    │
    └─ If match 60-80%: Use as hints for SOAR
        ("Try market_research_first first")
```

**Real example:**

Day 1: User asks "What opportunities in AI market?"
- SOAR runs full 5 cycles
- Chooses "market_research_first" operator
- Success: 0.95 (user rates 9/10)
- Operator utility updated: 0.92 → 0.928
- **Execution stored in JSON**

Day 2: User asks "Opportunities in blockchain market?"
- Orchestrator searches JSON
- Finds "market_analysis_general" pattern (80% match)
- Looks up operators from JSON
- Sees "market_research_first" has utility 0.928
- **Skips SOAR, executes learned operator directly**
- Response in 2-3 seconds instead of 10 seconds

---

## Q3: What decides complexity and triggers SOAR/ACT-R? Keyword matching?

### Answer: Keyword Scoring Algorithm (Decision Tree)

```
Complexity Detection Algorithm:

Score out of 100 points

1. REASONING KEYWORDS (30 points max)
   ├─ "analyze" → +5 points
   ├─ "why" → +5 points
   ├─ "strategy" → +5 points
   ├─ "compare" → +4 points
   ├─ "evaluate" → +4 points
   └─ "opportunity" → +4 points

2. QUESTION COMPLEXITY (25 points max)
   ├─ Multiple questions (>1?) → +10 points
   ├─ Starts with "how" or "why" → +8 points
   └─ Long prompt (>100 chars) → +7 points

3. DOMAIN SPECIFICITY (20 points max)
   ├─ "market" → +3 points
   ├─ "business" → +3 points
   ├─ "strategy" → +4 points
   └─ etc.

4. CONTEXT INDICATORS (25 points max)
   ├─ Multiple topics → +5 points
   ├─ Wants depth ("comprehensive") → +8 points
   └─ etc.

TOTAL SCORE:

40+ = HIGH complexity → USE SOAR
20-40 = MEDIUM complexity → USE SOAR or MODERATE
<20 = LOW complexity → USE FAST (no SOAR)

Examples:

"What is X?" (simple)
├─ Keywords: none → 0 points
├─ Questions: 1 → 0 points
├─ Total: <5
└─ Decision: FAST path (200ms)

"What opportunities in AI market?" (moderate)
├─ Keywords: "opportunities" → +4 points
├─ Questions: 1 → 0 points
├─ Domain: "market" → +3 points
├─ Total: 7
├─ BUT: has indicators for depth
└─ Decision: SOAR path (5-10s)

"Analyze the AI market. What opportunities exist? What strategy should we pursue? Need data-driven insights."
├─ Keywords: "analyze" → +5, "opportunities" → +4, "strategy" → +5 = +14 points
├─ Questions: 3 → +10 points
├─ Domain: "market" → +3 points
├─ Context: "data-driven" → wants depth → +8 points
├─ Total: 35+ points
└─ Decision: SOAR path (HIGH complexity)
```

---

## Q4: Step 1 Orchestrator Router: I've seen the code? What generates?

### Answer: Not LLM, Not a Question - Just Decision Tree Logic

```
Orchestrator GENERATES:

{
  'path': 'SOAR' | 'FAST' | 'ACT_R' | 'MODERATE' | 'CREATIVE',
  'use_soar': True | False,
  'use_act_r': True | False,
  'model_reasoning': 'mistral-7b-ft',
  'model_generation': 'claude-opus-4.5',
  'temperature': 0.3-0.7,
  'soar_max_iterations': 5,
  'hints': {
    'try_first': 'market_research_first',
    'recommended_operators': [...]
  },
  'reason': 'Complex reasoning needed'
}

What GENERATES this?

NOT: LLM (no LLM call here)
NOT: A question (no one asking)
YES: Decision tree algorithm

Pseudocode:

if complexity == HIGH and reasoning_needed == True:
    return {'path': 'SOAR', ...}
elif pattern_match_confidence > 0.8:
    return {'path': 'FAST', ...}
elif conversation_length > 2:
    return {'path': 'ACT_R', ...}
else:
    return {'path': 'MODERATE', ...}

This runs in ~50ms, no LLM involved.
```

---

## Q5: Step 2 SOAR Reasoning - Is this an internal conversation between what and what? Who generates the question?

### Answer: Orchestrator Asks, Fine-tuned LLM Answers

```
SOAR is a CONVERSATION:

But not "LLM talking to itself" (that would be hallucination)

ACTUALLY:

Orchestrator: "What does this problem require?"
Fine-tuned LLM: "Core question is..., Information needed is..."

Orchestrator: "What approaches could work?"
Fine-tuned LLM: "Approach A is..., Approach B is..."

Orchestrator: "Which is best for this context?"
Fine-tuned LLM: "Approach A is best because..."

Orchestrator: "Execute Approach A"
Fine-tuned LLM + RAG + Big LLM: [Generate response]

Orchestrator: "Learn from this"
System: [Store outcome in JSON]

WHO GENERATES THE QUESTIONS?

The Orchestrator (pre-hook script) generates the questions.
The questions are HARDCODED as templates:

Template 1: "What does this problem require?"
Template 2: "What approaches could work?"
Template 3: "Which is best?"
Template 4: [Execute chosen approach]
Template 5: [Store outcome]

These aren't generated dynamically. They're fixed question templates.
```

---

## Q6: What tokens does it use? Is this more like an internal conversation that happens between LLM and itself?

### Answer: Token Usage Breakdown

```
NOT between LLM and itself (that's not real)
ACTUALLY between fixed questions and LLM responses

Cycle 1: Elaboration
├─ Question sent: ~150 tokens
│   "You are analyzing a user request. What does it require?"
├─ LLM response: ~200 tokens
│   "Core question is..., Information needed is..."
└─ Subtotal: ~350 tokens

Cycle 2: Operator Proposal
├─ Question + elaboration: ~400 tokens
│   "Based on elaboration, propose operators..."
├─ LLM response: ~500 tokens
│   "Operator A: Market Research..., Operator B: Direct Analysis..."
└─ Subtotal: ~900 tokens

Cycle 3: Evaluation
├─ Question + operators: ~500 tokens
│   "Given these operators, which is best?"
├─ LLM response: ~300 tokens
│   "Operator A is best because..."
└─ Subtotal: ~800 tokens

Cycle 4: Execution
├─ Question + operator details: ~300-500 tokens
├─ LLM response + RAG data: ~1500 tokens
│   (Actual response to user)
└─ Subtotal: ~1800-2000 tokens

TOTAL TOKENS: ~3850-4050 tokens

Cost at $0.0005/1000 tokens:
4000 * $0.0005 = $0.002 (cheap!)

Big LLM generation adds: ~$0.01

Total per complex prompt: ~$0.012
```

---

## Q7: Is this more like a pre-hook script tree? How does it break and fill SOAR and ACT-R requirements?

### Answer: YES, Pre-Hook Script Tree

```
ARCHITECTURE:

User Prompt
    ↓
PRE-HOOK SCRIPT (Orchestrator)
├─ Detect complexity (keyword scoring)
├─ Search JSON patterns
├─ Decide route (decision tree)
└─ Return routing decision
    ↓
MAIN EXECUTION TREE (based on routing)
├─ If FAST:
│   └─ Run: small_llm(prompt) → response
│
├─ If SOAR:
│   └─ Run 5-cycle script tree:
│       ├─ Cycle 1 script: Ask elaboration question
│       ├─ Cycle 2 script: Ask operator question
│       ├─ Cycle 3 script: Ask evaluation question
│       ├─ Cycle 4 script: Execute operator
│       └─ Cycle 5 script: Store outcome
│
└─ If ACT-R:
    └─ Run 4-step script tree:
        ├─ Step 1 script: Match memory (JSON search)
        ├─ Step 2 script: Select procedure (activation lookup)
        ├─ Step 3 script: Execute procedure
        └─ Step 4 script: Update activation

HOW REQUIREMENTS ARE FILLED:

SOAR Requirements (Elaborate, Propose, Evaluate, Execute, Learn):

Elaborate:
  ├─ Requirement: "Understand the problem"
  ├─ Filled by: Cycle 1 script asking "What does this require?"
  ├─ LLM generates: Problem understanding
  └─ Stored in: soar_state['elaboration']

Propose:
  ├─ Requirement: "Generate candidate operators"
  ├─ Filled by: Cycle 2 script asking "What approaches?"
  ├─ LLM generates: 3-5 operators
  ├─ Script looks up: Utilities from JSON
  └─ Stored in: soar_state['operators']

Evaluate:
  ├─ Requirement: "Score each operator"
  ├─ Filled by: Cycle 3 script asking "Which is best?"
  ├─ LLM generates: Scores
  └─ Script selects: Highest score

Execute:
  ├─ Requirement: "Run chosen operator"
  ├─ Filled by: Cycle 4 script executing steps
  ├─ May use: RAG + LLM
  └─ Generates: Response to user

Learn:
  ├─ Requirement: "Capture outcome"
  ├─ Filled by: Cycle 5 script storing in JSON
  └─ TAO later: Updates utilities

ACT-R Requirements (Match, Select, Act, Learn):

Match:
  ├─ Requirement: "Find similar past interactions"
  ├─ Filled by: Step 1 script searching JSON declarative memory
  ├─ Uses: Keyword + semantic similarity (>70% threshold)
  └─ Returns: List of similar past interactions

Select:
  ├─ Requirement: "Choose which procedure to use"
  ├─ Filled by: Step 2 script looking up activation scores
  ├─ Activation = recency * frequency * success_rate
  └─ Selects: Highest activation procedure

Act:
  ├─ Requirement: "Execute the procedure"
  ├─ Filled by: Step 3 script running procedure steps
  ├─ Each step: LLM call (if needed) + action
  └─ Generates: Response

Learn:
  ├─ Requirement: "Update procedure activation"
  ├─ Filled by: Step 4 script updating JSON
  ├─ Formula: new = 0.4*recency + 0.3*frequency + 0.3*success
  └─ Stored in: JSON procedures[procedure_id]['activation']
```

---

## Q8: Is SOAR/ACT-R decision tree quite straightforward simple script, and if successful gets stored in JSON, and what happens when recalled?

### Answer: EXACTLY Correct

```
SOAR/ACT-R ARE SIMPLE SCRIPTS:

Not neural networks.
Not statistical models.
Just if-then-else decision trees.

Example SOAR Script:

def soar_cycle_1_elaboration():
    question = "What does this problem require?"
    response = llm.generate(question)
    soar_state['elaboration'] = response
    return response

def soar_cycle_2_operators():
    question = "What approaches could work?"
    response = llm.generate(question)
    operators = parse(response)
    for op in operators:
        op['utility'] = lookup_from_json(op['name'])
    soar_state['operators'] = operators
    return operators

def soar_cycle_3_evaluate():
    question = "Which is best?"
    response = llm.generate(question)
    scores = parse_scores(response)
    best = max(scores)
    return best

# This is SIMPLE CODE, not ML.

IF SUCCESSFUL, STORES IN JSON:

{
  "execution_trace": {
    "execution_id": "exec_12345",
    "user_prompt": "What opportunities in AI market?",
    "soar_execution": {
      "elaboration": {...},
      "operators": [...],
      "evaluation": {...},
      "execution": {...}
    },
    "outcome": {
      "user_rating": 9,
      "success_score": 0.95,
      "feedback": "Used for board presentation"
    },
    "timestamp": "2025-12-06T14:32:00Z"
  }
}

WHEN RECALLED (Next similar prompt):

Day 2 user asks: "Opportunities in blockchain market?"

Orchestrator:
├─ Searches JSON for similar patterns
├─ Finds execution_trace with 80% keyword match
├─ Looks up operators used: "market_research_first"
├─ Checks utility: 0.93 (very high)
├─ Decision: "Skip SOAR, use learned operator directly"
│
└─ DIRECT EXECUTION:
    ├─ Loads operator steps from JSON:
    │   Step 1: RAG search for market data
    │   Step 2: Fine-tuned LLM analyzes competitors
    │   Step 3: Fine-tuned LLM identifies gaps
    │   Step 4: Big LLM synthesizes opportunities
    │
    ├─ Executes steps sequentially
    ├─ Returns response in 2-3 seconds
    │   (Instead of 10 seconds for full SOAR)
    │
    └─ Stores new execution in JSON
        "This operator worked again. Utility: 0.93 → 0.934"
```

---

## Summary Table

| Question | Answer |
|----------|--------|
| **Storage location?** | JSON files in knowledge_base/ |
| **Similarity match?** | Keyword + semantic (>60% threshold) |
| **Successful path reuse?** | YES, >80% confidence skips SOAR entirely |
| **Complexity trigger?** | Keyword scoring algorithm (40+ score = SOAR) |
| **Orchestrator generates?** | Routing decision (not LLM, just decision tree) |
| **SOAR conversation?** | Orchestrator asks, Fine-tuned LLM answers |
| **Token usage?** | ~4000 tokens per SOAR (~$0.002) |
| **Script tree?** | YES, pre-hook decides path, main execution runs cycles |
| **Requirements filled?** | Each cycle/step fills one SOAR/ACT-R requirement |
| **Recall on success?** | Highest-utility operator executed directly (saves time) |

---

## Visual Flow: Simple Case vs. Complex Case

```
SIMPLE CASE (Known Pattern, >80% match):

User: "What opportunities in blockchain?"
    ↓
Orchestrator: "This matches market_analysis_general (85%)"
             "Utility of market_research_first: 0.93"
             "Decision: SKIP SOAR, execute learned operator"
    ↓
Direct execution of operator steps
    ↓
Response in 2-3 seconds

────────────────────────────────────

COMPLEX CASE (Novel Problem, low match):

User: "What opportunities in emerging biotechnology?"
    ↓
Orchestrator: "No pattern match. Novel domain."
              "Complexity: HIGH"
              "Decision: RUN SOAR"
    ↓
SOAR Cycle 1: Elaborate (understand problem)
SOAR Cycle 2: Propose (3-5 operators)
SOAR Cycle 3: Evaluate (score each)
SOAR Cycle 4: Execute (run best operator)
SOAR Cycle 5: Learn (store outcome in JSON)
    ↓
Response in 10 seconds
    ↓
TAO Learning: "This operator worked well. Update utility."
    ↓
Next similar prompt: Will use learned path (2-3 seconds)
```

---

**Status**: Complete clarification of implementation details
**Ready for**: Implementation coding
