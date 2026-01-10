# Unified Architecture: Quick Reference Guide
## TL;DR - What Happens on Every Prompt

**Date**: December 6, 2025

---

## The Stack (6 Layers)

```
┌─────────────────────────────────────┐
│ LAYER 1: ORCHESTRATOR ROUTER        │
│ (Pre-hook, decides path)            │
└─────────────────┬───────────────────┘
                  ↓
    ┌─────────────┴──────────────┐
    ↓                            ↓
┌─────────┐           ┌──────────────────┐
│FAST     │           │SOAR REASONING    │
│(200ms)  │           │(5-10s)           │
└────┬────┘           └────┬─────────────┘
     │                     │
     └────────┬────────────┘
              ↓
    ┌─────────────────────────┐
    │LAYER 3: Fine-tuned LLM  │
    │(PEFT, domain knowledge)│
    └────────┬────────────────┘
             ↓
    ┌─────────────────────────┐
    │LAYER 4: Big LLM         │
    │(Complex generation)     │
    └────────┬────────────────┘
             ↓
    ┌─────────────────────────┐
    │LAYER 5: RAG (optional)  │
    │(Current data)           │
    └────────┬────────────────┘
             ↓
    ┌─────────────────────────┐
    │RESPONSE to User         │
    └────────┬────────────────┘
             ↓
    ┌─────────────────────────┐
    │LAYER 6: TAO Learning    │
    │(Async, async update utilities)    │
    └─────────────────────────┘
```

---

## Decision Table: When SOAR/ACT-R Are Used

| Input | Complexity | Reasoning? | Known? | Path | Time | Cost |
|-------|-----------|-----------|--------|------|------|------|
| "What is X?" | Low | No | High | FAST | 200ms | $0.001 |
| "Summarize Y" | Low | No | Medium | FAST | 500ms | $0.001 |
| "Analyze market" | High | Yes | Low | SOAR | 7-10s | $0.02 |
| "Design system" | High | Yes | Low | SOAR | 10-15s | $0.03 |
| "How to do X?" | Med | No | High | ACT-R | 3-5s | $0.005 |
| "Multi-turn follow-up" | Med | No | High | ACT-R | 3-5s | $0.005 |
| "Brainstorm ideas" | High | No | N/A | CREATIVE | 5-8s | $0.02 |

---

## The Orchestrator (Layer 1): Your Smart Router

### What It Does (Every Prompt)

```python
def orchestrator(user_prompt):
    """Analyze and route prompt (50ms)"""

    analysis = {
        'complexity': 'low' | 'medium' | 'high',
        'needs_reasoning': True | False,
        'task_type': 'analysis' | 'brainstorm' | 'faq' | ...,
        'known_pattern': confidence_score (0.0-1.0),
    }

    if analysis['complexity'] == 'low' and \
       analysis['needs_reasoning'] == False and \
       analysis['known_pattern'] > 0.8:
        return 'FAST_PATH'  # Small LLM only

    elif analysis['complexity'] in ['medium', 'high'] and \
         analysis['needs_reasoning'] == True:
        return 'SOAR_PATH'  # Reasoning cycles

    elif len(conversation_history) > 2:
        return 'ACT_R_PATH'  # Learning procedures

    else:
        return 'MODERATE_PATH'  # Balanced default
```

### Why Orchestrator Matters

✅ **Smart**: Uses learned patterns from past SOAR runs
✅ **Fast**: No overhead for simple tasks (200ms total)
✅ **Efficient**: Only uses complex paths when needed
✅ **Observable**: Can explain why path was chosen

---

## SOAR: Reasoning Layer (5-10 seconds)

### When Used
- **Complexity**: MODERATE to COMPLEX
- **Reasoning indicators**: "analyze", "why", "strategy", "design", "compare"
- **Task pattern**: NEW (not seen before, or low confidence)

### How It Works (5 Cycles)

```
CYCLE 1: Elaboration
  Question: "What does this problem require?"
  → LLM: "Need market data, competitor analysis, gaps"

CYCLE 2: Operator Proposal
  Question: "What approaches could work?"
  → LLM proposes 3-5 operators (methods)
  → Each has learned utility (success probability)

CYCLE 3: Evaluation
  Question: "Which approach is best for THIS context?"
  → LLM scores each operator
  → Select highest-scored operator

CYCLE 4: Execution
  Question: "Do the chosen approach"
  → Execute operator (may use fine-tuned LLM or big LLM)
  → Generate response

CYCLE 5: Learning
  Question: "What did we learn?"
  → Capture outcome
  → TAO will score later, update operator utilities
```

### Key Points

- **NOT per-token**: SOAR doesn't generate tokens
- **Per-problem**: 1 SOAR run per complex prompt
- **Uses small LLM**: For cycles (5-10s reasoning)
- **Uses big LLM**: For final generation (1-2s)
- **Transparent**: Reasoning trace captured

---

## ACT-R: Learning Layer (3-5 seconds)

### When Used
- **Multi-turn**: Conversation has 2+ exchanges
- **Task type**: Procedural ("how to", recurring patterns)
- **Feedback available**: User gives signals
- **Adaptation needed**: Approach changes based on feedback

### How It Works (4 Phases)

```
PHASE 1: Pattern Matching
  → Search past conversations for similar tasks
  → Find learned PROCEDURES (how we solved it before)
  → Check activation (how recent/frequent was it)

PHASE 2: Production Selection
  → If strong match (activation > 0.6):
     Use learned procedure (fast, proven)
  → Else:
     Generate new procedure

PHASE 3: Action
  → Execute procedure
  → Get feedback (explicit rating, user continue, etc.)

PHASE 4: Learning
  → Update procedure activation
  → Higher feedback → higher activation
  → Next time, procedure selected faster
```

### Key Points

- **Procedural memory**: Learns HOW to solve
- **Activation decay**: Recent/frequent procedures score high
- **Feedback-driven**: Improves based on signals
- **Multi-turn**: Best for conversations, not single queries

---

## TAO: Continuous Learning (Asynchronous)

### What Happens After Response

```
User gets response immediately (5-10 seconds)
   ↓
TAO runs in background (doesn't block)
   ↓
Collects outcomes from past hour
   ↓
Groups by operator/procedure
   ↓
Calculates success rate for each
   ↓
Updates utilities:
  new_utility = 0.9 * old_utility + 0.1 * success_rate
   ↓
Next similar prompt:
  SOAR sees updated utilities
  Selects better operators
  Better result
```

### The Improvement Curve

```
Time 0:       SOAR has equal utilities (all 0.50)
After 10 prompts:  "Market Research" = 0.92 (successful)
                   "Direct Analysis" = 0.55 (less successful)
After 100 prompts: "Market Research" = 0.95
                   "Direct Analysis" = 0.48
                   New operator discovered = 0.87

Result: System improves asymptotically from real usage
```

---

## Fine-tuning (Layer 3): Domain Knowledge

### How It Works

```
Base model (Mistral 7B):
  "The market for X is growing"
  (Generic knowledge from internet)

Fine-tuned on YOUR data (PEFT):
  "The AI agent market is $24B growing to $150B"
  (Domain-specific knowledge)

Efficiency:
  ✓ Only 1-2% of weights updated (PEFT)
  ✓ 10,000x less memory than full fine-tuning
  ✓ Cost: $10-50K to fine-tune
  ✓ Result: Domain expert model
```

### Where It Sits

- SOAR uses fine-tuned LLM for reasoning cycles
- ACT-R uses fine-tuned LLM for procedure execution
- Big LLM uses context from fine-tuned LLM
- RAG feeds fine-tuned LLM with current data

---

## Complete Flow Example: Single Prompt

### Input
"What business opportunities exist in AI agent market? I need data-driven insights."

### Execution (7-10 seconds)

```
STEP 1: Orchestrator (50ms)
  ├─ Complexity: HIGH (analyze, opportunities)
  ├─ Reasoning: YES ("opportunities" requires strategy)
  ├─ Known pattern: MEDIUM (asked before, but market changes)
  └─ Decision: SOAR_PATH (with RAG)

STEP 2: SOAR Cycles (6-8 seconds)
  ├─ Cycle 1: Elaborate
  │   "Need market size, competitors, gaps, trends"
  │
  ├─ Cycle 2: Operators
  │   - "Market Research First" (utility: 0.92)
  │   - "Direct Analysis" (utility: 0.55)
  │   - "Competitor Benchmarking" (utility: 0.78)
  │
  ├─ Cycle 3: Evaluate
  │   "Best for data-driven? Market Research First wins (9.5/10)"
  │
  └─ Cycle 4-5: Execute & Learn
      - RAG: Pull market data
      - LLM: Analyze competitors
      - Big LLM: Generate comprehensive response
      - Capture outcome for TAO learning

STEP 3: Response (1-2 seconds)
  "BUSINESS OPPORTUNITIES:
   1. Privacy-first platform ($8-12B market)
   2. Vertical-specific SaaS ($15-25B)
   3. Open-source alternative ($5-8B)

   RECOMMENDATIONS: [5-point strategy]"

STEP 4: TAO Learning (Async, background)
  - User rates: "9/10 - used for board"
  - Success score: 0.95
  - "Market Research First" utility: 0.92 → 0.923
  - Next similar prompt will choose same operator

TOTAL TIME: 7-10 seconds
TOTAL COST: $0.012
LEARNING: Operator utility improved slightly
```

---

## Cost/Performance Tradeoff

| Path | Time | Cost | Quality | Use Case |
|------|------|------|---------|----------|
| FAST | 200ms | $0.001 | Good | FAQs, simple |
| MODERATE | 1-2s | $0.005 | Very Good | Medium tasks |
| SOAR | 5-10s | $0.02 | Excellent | Complex reasoning |
| SOAR+Big | 7-15s | $0.03 | Expert | Complex + generation |
| ACT-R | 3-5s | $0.005 | Good→Excellent | Multi-turn, procedural |

**Orchestrator chooses optimal tradeoff for each prompt.**

---

## FAQ: Layer Interactions

### Q1: Does SOAR replace the LLM?
**A**: NO. SOAR guides the LLM. Uses fine-tuned LLM for reasoning cycles, big LLM for generation.

### Q2: Does every prompt use SOAR?
**A**: NO. Only ~20% of prompts (complex ones). Simple prompts use FAST path (200ms).

### Q3: How does TAO improve the system?
**A**: Asynchronously. Collects outcomes, updates operator utilities. System gets smarter without user noticing.

### Q4: What's the difference: SOAR vs. ACT-R?
**A**:
- SOAR = Reasoning about how to solve novel problems
- ACT-R = Learning procedures for recurring problems

### Q5: Can I use just SOAR without ACT-R?
**A**: YES. Configure Orchestrator to route simple → FAST, complex → SOAR, skip ACT-R.

### Q6: How is this different from fine-tuning alone?
**A**:
- Fine-tuning: Better token prediction on domain data
- SOAR: Better reasoning about novel problems
- Together: Better reasoning + domain knowledge

---

## Architecture Checklist

Before implementation, ensure:

- [ ] **Orchestrator**: Routes 100% of prompts (decides path)
- [ ] **FAST Path**: Works for low complexity, no reasoning
- [ ] **SOAR Path**: 5-cycle implementation for reasoning
- [ ] **ACT-R Path**: Procedural memory + activation for learning
- [ ] **Fine-tuned LLM**: PEFT, efficient, domain knowledge
- [ ] **Big LLM**: Used for complex generation
- [ ] **RAG Module**: Semantic search for current data
- [ ] **TAO Learning**: Async utility updates, no blocking
- [ ] **Outcome Capture**: Every prompt tracked
- [ ] **Feedback Integration**: Explicit + implicit signals collected

---

## Next: Implementation

Once you understand the architecture:

1. **Implement Orchestrator** (router logic)
2. **Implement SOAR** (5 cycles with fine-tuned LLM)
3. **Implement ACT-R** (procedural memory + selection)
4. **Set up TAO learning** (async updates)
5. **Integrate RAG** (optional, add when needed)
6. **Test end-to-end** (track metrics)

---

**Key Takeaway**:

Every prompt flows through Orchestrator → appropriate path → response → learning.

The system is **smart** (routes intelligently), **fast** (simple prompts are quick), **capable** (complex reasoning available), and **learning** (improves from production).

---

**For complete details, read**: `UNIFIED-SOLUTION-ARCHITECTURE-PSEUDOFLOW.md`
