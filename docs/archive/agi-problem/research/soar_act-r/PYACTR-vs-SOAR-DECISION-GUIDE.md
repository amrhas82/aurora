# PyACT-R vs SOAR: Decision Guide for Your WS2 Implementation

**Date**: December 7, 2025
**Purpose**: Help you decide which open-source library to use for your solo WS2 system
**TL;DR**: Start with PyACT-R (1 week to working system). Add SOAR later if you need explicit rules (weeks 3-4).

---

## Quick Decision Tree

```
Do you want to start IMMEDIATELY?
├─ YES → Use PyACT-R (pip install python_actr, start in 1 hour)
└─ NO → Consider SOAR (requires C++ setup, starts in 1 day)

Is this your FIRST cognitive architecture project?
├─ YES → PyACT-R (simpler, pure Python)
└─ NO → Either (you can handle the setup)

Do you need EXPLICIT RULES that users can see/edit?
├─ YES → SOAR (rules are visible, editable .soar files)
└─ NO → PyACT-R (activation scores are abstract)

How much TIME do you have for setup?
├─ < 1 hour → PyACT-R only
├─ 1-2 hours → PyACT-R only
├─ 2-4 hours → PyACT-R + start SOAR research
└─ > 4 hours → Both (hybrid system)

Do you need FUZZY/PROBABILISTIC reasoning?
├─ YES → PyACT-R (activation-based, fuzzy matching)
└─ NO → SOAR (crisp symbolic rules)
```

---

## Detailed Comparison

### 1. Installation & Setup

**PyACT-R**:
```bash
pip install python_actr
# Done. Ready to use in 5 minutes.
```
- **Time**: 5 minutes
- **Complexity**: One command
- **Dependencies**: Python 3.8-3.11 (not 3.12+)
- **Gotchas**: None

**SOAR**:
```bash
# Option A: Pre-built (if available)
pip install soar-sml
# Time: 10 minutes

# Option B: Build from source (recommended)
git clone https://github.com/SoarGroup/Soar.git
cd Soar
./build.sh  # Takes 30+ minutes
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:./out
export PYTHONPATH=$PYTHONPATH:./out
# Time: 45+ minutes
```
- **Time**: 10 minutes (pip) to 45+ minutes (source)
- **Complexity**: Moderate (C++ build system)
- **Dependencies**: Java, SWIG, C++ compiler
- **Gotchas**: LD_LIBRARY_PATH/PYTHONPATH setup tricky

**Winner**: PyACT-R (by far)

---

### 2. Core Concepts Learning Curve

**PyACT-R**:
- **Main Concept**: Activation scores (0.0-1.0)
- **Memory**: Facts stored as Python dicts with activation
- **Reasoning**: Automatic spreading activation + pattern matching
- **Learning**: Automatic (success_rating improves activation)
- **Learning Curve**: Easy (similar to database queries)

**Code Example**:
```python
# Store: fact with activation
memory.add({'type': 'approach', 'name': 'market_research', 'activation': 0.92})

# Retrieve: highest activation matching pattern
result = memory.retrieve(pattern={'type': 'approach'})
# Returns fact with highest activation

# Learn: update activation based on success
memory.update_activation(fact_id, success_rating=9/10)
```

**SOAR**:
- **Main Concept**: State-Operator-Result (S→O→R)
- **Memory**: Working memory (state triples) + Production memory (if-then rules)
- **Reasoning**: Decision cycle (Elaborate→Propose→Decide→Apply→Learn)
- **Learning**: Manual (you update rule utilities)
- **Learning Curve**: Medium (like finite state machines + rule engines)

**Code Example**:
```python
# Define state
state = {'goal': 'analyze_market', 'status': 'pending'}

# Define production rules
if state['goal'] == 'analyze_market':
    # Propose operator
    operators = ['market_research_first', 'direct_analysis']
    # Decide (highest utility wins)
    chosen = 'market_research_first'  # utility 0.92
    # Apply
    result = execute(chosen)
    # Learn (update utility)
    utilities['market_research_first'] = 0.93
```

**Winner**: PyACT-R (easier to learn)

---

### 3. Integration with LLM

Both require you to build the bridge—neither has native LLM integration.

**PyACT-R Bridge** (from OPEN-SOURCE-SOAR-ACTR-PRACTICAL-GUIDE.md Part 2):
```python
class LLMBridgedACTR:
    def execute_with_llm(self, prompt):
        # Step 1: Pattern matching (retrieve from memory)
        similar = self.retrieve_similar_procedure(prompt)

        if similar and similar['activation'] > 0.75:
            # Use learned procedure
            return self._execute_steps(similar['steps'])

        # No strong match: ask LLM
        response = llm(prompt)

        # Learn: store for future use
        self.store_procedure(prompt_type, response_steps, rating)

        return response
```

**SOAR Bridge** (from OPEN-SOURCE-SOAR-ACTR-PRACTICAL-GUIDE.md Part 3):
```python
class LLMBridgedSOAR:
    def execute_reasoning_cycle(self, prompt):
        # Phase 1: Elaborate (ask LLM to understand problem)
        elaboration = llm("What does this problem require?")

        # Phase 2: Propose (ask LLM for approaches)
        operators = llm("What approaches could work?")

        # Phase 3: Decide (ask LLM to pick best)
        chosen = llm("Which is best for this context?")

        # Phase 4: Apply (execute chosen approach)
        result = llm(prompt)

        # Phase 5: Learn (update rule utilities)
        self.update_utility(chosen_operator, success_rating)

        return result
```

**Key Difference**:
- PyACT-R: Integrates automatically (pattern matching → procedure → learn)
- SOAR: Needs explicit question engineering for each cycle

**Winner**: Tie (both need work, PyACT-R simpler)

---

### 4. Code Complexity

**PyACT-R Minimal System** (QUICKSTART-PYACTR-MINIMAL.py):
- Total lines: ~100
- Classes: 1 (MinimalACTRSystem)
- Methods: 5 (solve, give_feedback, _find_similar, _execute, _extract_keywords)
- External dependencies: anthropic (LLM client)

**SOAR Minimal System** (from OPEN-SOURCE-SOAR-ACTR-PRACTICAL-GUIDE.md Part 3):
- Total lines: ~300
- Classes: 1 (LLMBridgedSOAR)
- Methods: 10+ (elaborate, propose, decide, apply, learn, pattern matching, utility updates)
- External dependencies: anthropic + soar-sml

**Winner**: PyACT-R (3x less code)

---

### 5. Performance Characteristics

**PyACT-R**:
- Startup: ~10ms (pure Python)
- Pattern matching: ~1ms per fact (linear search)
- Activation update: ~0.1ms per fact
- Memory ceiling: ~1000s of facts (lightweight)
- Latency: 2-3 seconds (pure LLM cost)

**SOAR**:
- Startup: 500-1000ms (C++ kernel + SML overhead)
- Decision cycle: ~100-500ms per cycle (depends on rule complexity)
- Rule matching: Rete network (efficient for 1000s of rules)
- Memory ceiling: 10000s of rules (heavyweight)
- Latency: 3-5 seconds (LLM + SOAR cycles)

**Winner for Solo**: PyACT-R (lower latency for small systems)
**Winner for Enterprise**: SOAR (scales better)

---

### 6. Transparency (Why did it choose that?)

**PyACT-R**:
```
Decision: "Used market_research_first"
Reason: Activation score 0.92 > 0.75 threshold
Transparency: Moderate (score visible, but "why 0.92?" is buried)
```

**SOAR**:
```
Decision: "Applied operator market_research_first"
Reason:
  - Elaboration found: need market data
  - Proposal generated: 3 operators
  - Evaluation scored: market_research_first = 9.5/10
  - Execute: ran market_research_first operator
Transparency: High (every step visible, rule-based)
```

**Winner for Explainability**: SOAR
**Winner for Simplicity**: PyACT-R

---

### 7. Learning from Outcomes

**PyACT-R**:
```python
# Automatic: just give feedback
system.give_feedback(rating=9)
# Internally: activation = rating / 10.0 = 0.9
# Next time: this procedure used more often
```
- **Feedback needed**: Explicit rating (0-10)
- **Learning mechanism**: Direct activation update
- **Speed**: Automatic, immediate
- **Complexity**: Very simple

**SOAR**:
```python
# Manual: you update operator utility
old_utility = 0.92
success = rating / 10.0  # 0.9
new_utility = 0.9 * old_utility + 0.1 * success
# new_utility = 0.828 + 0.09 = 0.918
```
- **Feedback needed**: Explicit success metric
- **Learning mechanism**: Exponential moving average
- **Speed**: Requires manual update
- **Complexity**: You control learning rate

**Winner for Solo**: PyACT-R (automatic)
**Winner for Tuning**: SOAR (explicit control)

---

### 8. Use Case Fit

**PyACT-R Best For**:
✅ Procedural learning (learning how to solve tasks)
✅ Implicit pattern matching (fuzzy similarity)
✅ Individual researcher (minimal setup)
✅ Fast prototyping (low code complexity)
✅ Automatic learning (activation-based feedback)
✅ Multi-turn conversations (works great)

❌ Complex symbolic reasoning (explicit rules needed)
❌ Hierarchical goal decomposition (no explicit goals)
❌ Rule transparency for users (activation scores abstract)

**SOAR Best For**:
✅ Complex symbolic reasoning (explicit rules)
✅ Goal-oriented behavior (hierarchical planning)
✅ Clear decision traces (why did it choose that?)
✅ Multiple domain experts (rules can be shared)
✅ Deterministic behavior (same input → same output)

❌ Probabilistic reasoning (pure SOAR is symbolic)
❌ Rapid prototyping (steeper setup)
❌ Individual researcher with time constraints

---

## Your Specific Situation

Based on PRACTICAL-SOLO-IMPLEMENTATION.md and your questions:

**You are:**
- Solo researcher (time-constrained)
- Want immediate working system (1-2 weeks)
- Need learning from outcomes (success feedback)
- Want hidden complexity (show summary, hide cycles)
- May add SOAR later if needed

**Recommendation: START WITH PYACTR**

**Timeline**:
- Week 1: PyACT-R minimal system (100 lines, QUICKSTART-PYACTR-MINIMAL.py)
  - Running system by day 2
  - Learning from feedback by day 3
  - Confident with architecture by day 5

- Week 2: Extend PyACT-R
  - Add semantic similarity (better pattern matching)
  - Add domain-specific keywords
  - Integrate with your specific prompts
  - System ready for evaluation by day 10

- Week 3: Decide on SOAR
  - If PyACT-R works well: Stop here (minimal viable system)
  - If you need explicit rules: Add SOAR (weeks 4-5)
  - If you want hybrid: Integrate both (weeks 4-6)

---

## Phased Approach

### Phase 1: PyACT-R Only (Week 1)
```
pip install python_actr
python QUICKSTART-PYACTR-MINIMAL.py
# Done. System learns from outcomes automatically.
```

**Success Criteria**:
- ✅ System starts in < 1 second
- ✅ Learns from feedback (activation improves)
- ✅ Reuses procedures on similar prompts
- ✅ Can explain activation score

**Effort**: 1 week
**Lines of Code**: ~100

### Phase 2: Extend PyACT-R (Week 2)
```python
# Improve pattern matching
def _extract_keywords(text):
    # Use semantic similarity instead of keyword overlap
    from sklearn.feature_extraction.text import TfidfVectorizer
    # Or use embeddings for better matching

# Add domain-specific classifiers
def _extract_type(prompt):
    # Rule-based or ML-based classification
```

**Success Criteria**:
- ✅ Pattern matching accuracy > 80%
- ✅ Activation scores stable
- ✅ Reuse rate > 70% on similar prompts

**Effort**: 1 week
**Lines of Code**: +150 (total ~250)

### Phase 3: Add SOAR (Optional, Weeks 3-4)
```python
# Keep PyACT-R for procedural learning
# Add SOAR for complex reasoning

class HybridSystem:
    def __init__(self):
        self.actr = PyACTRBridge()
        self.soar = SOARBridge()

    def solve(self, prompt):
        # Try ACT-R first (faster)
        result = self.actr.retrieve_procedure(prompt)
        if result and result['activation'] > 0.75:
            return result

        # Fall back to SOAR (more thorough)
        return self.soar.reason(prompt)
```

**Success Criteria**:
- ✅ SOAR cycles work without errors
- ✅ SOAR can define operators explicitly
- ✅ Hybrid system uses both appropriately
- ✅ Complex prompts use SOAR, simple use ACT-R

**Effort**: 2 weeks (includes SOAR setup + C++ build)
**Lines of Code**: +200 (total ~400)

---

## Migration Path: PyACT-R → SOAR

If you start with PyACT-R and later need SOAR:

**Step 1: Export learned procedures**
```python
# PyACT-R memory
procedures = system.memory['procedures']

# Convert to SOAR operators
soar_operators = []
for proc in procedures:
    soar_operators.append({
        'name': proc['name'],
        'utility': proc['activation'],
        'condition': proc['keywords'],
        'action': proc['steps']
    })

# Save as SOAR-compatible format
with open('operators.json', 'w') as f:
    json.dump(soar_operators, f)
```

**Step 2: Load into SOAR**
```python
# SOAR reads operators.json
for op in soar_operators:
    # Create SOAR production rule
    # if condition then propose operator
```

**Step 3: Hybrid system**
```python
# PyACT-R for quick retrieval
# SOAR for new complex tasks
```

**Migration Effort**: 1-2 hours (procedural learning → explicit rules)

---

## Final Recommendation Matrix

| Situation | Recommendation |
|-----------|-----------------|
| Solo researcher, < 2 weeks | **PyACT-R only** |
| Team, need explicit rules | **SOAR only** |
| Solo researcher, 4+ weeks | **PyACT-R + SOAR** |
| Enterprise system | **SOAR only** |
| Fast prototyping | **PyACT-R only** |
| Production system with transparency | **SOAR only** |
| Learning-focused (feedback-driven) | **PyACT-R** |
| Goal-oriented (hierarchical) | **SOAR** |
| Unknown, start simple | **PyACT-R** |

**Your situation: Solo researcher, WS2 validation → START WITH PYACTR**

---

## How to Decide Within the Hour

1. **Do you have 45+ minutes for C++ build?**
   - NO → PyACT-R
   - YES → Continue

2. **Do you need explicit rules visible to users?**
   - NO → PyACT-R
   - YES → SOAR

3. **Is learning from feedback central to your approach?**
   - YES → PyACT-R
   - NO → SOAR

4. **Are you comfortable with "activation scores" as explanations?**
   - YES → PyACT-R
   - NO → SOAR

5. **Do you want to start coding within the hour?**
   - YES → PyACT-R
   - NO → SOAR

---

## Summary

| Factor | PyACT-R | SOAR |
|--------|---------|------|
| **Installation** | 5 min | 45+ min |
| **Code Complexity** | 100 lines | 300+ lines |
| **Learning Curve** | Easy | Medium |
| **LLM Integration** | Simple bridge | Question templates |
| **Startup Time** | 10ms | 500-1000ms |
| **Transparency** | Activation scores | Explicit rules |
| **Learning Automatic?** | YES | NO (manual) |
| **Recommended for Solo?** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Time to Working System** | 1 day | 1 week |
| **Week 1 Productivity** | High (coding) | Medium (setup) |

**START: PyACT-R**
**EXTEND: Add domain-specific features**
**UPGRADE: Add SOAR if you need explicit rules (optional)**

---

## Files to Use

1. **Start Here**: `QUICKSTART-PYACTR-MINIMAL.py` (~100 lines, ready to run)
2. **Understand Architecture**: `UNIFIED-SOLUTION-ARCHITECTURE-PSEUDOFLOW.md`
3. **Detailed Implementation**: `OPEN-SOURCE-SOAR-ACTR-PRACTICAL-GUIDE.md`
4. **If Adding SOAR**: Part 3 of above guide

---

**Next Step**: Run `python QUICKSTART-PYACTR-MINIMAL.py` and see it learn from feedback. You'll understand the whole system in 10 minutes of execution.

