# Open-Source SOAR & ACT-R: Practical Implementation Guide

**Date**: December 7, 2025
**Purpose**: Show how to use PyACT-R and psoar (Python SOAR bindings) in your solo LLM-integrated system

---

## Executive Summary

You have **two realistic options** for open-source cognitive architectures in Python:

| Option | Library | Effort | Integration | Best For |
|--------|---------|--------|-------------|----------|
| **ACT-R** | `python_actr` (pip) | Low | Easy with LLM | Learning-focused tasks, procedural memory |
| **SOAR** | `soar-sml` (pip) + `pysoarlib` | Medium | Moderate | Reasoning-focused tasks, complex rules |
| **Hybrid (Recommended)** | Both + LLM bridge | Medium | Good | Full WS2 architecture |

**Bottom Line**: You can use either library, BUT both have a critical gap: they're cognitive architectures, not LLM integrators. You'll need to build the "bridge" between them and Claude/Mistral.

---

## Part 1: PyACT-R (ACT-R in Python)

### What It Is

**python_actr** is a native Python implementation of ACT-R that mirrors the official Lisp version. It implements:
- Declarative memory (facts with activation decay)
- Procedural memory (if-then rules)
- Subsymbolic learning (activation-based retrieval)
- Multi-buffer cognitive architecture

### Installation

```bash
pip install python_actr
```

**Note**: Does NOT work on Python 3.12+. Requires Python 3.8-3.11.

### Core Concepts

**ACT-R Structure**:
```python
from python_actr import actr

# 1. Define declarative memory (facts)
facts = [
    {'isa': 'market_analysis', 'approach': 'research_first', 'utility': 0.92},
    {'isa': 'market_analysis', 'approach': 'direct_analysis', 'utility': 0.55},
]

# 2. Define procedural memory (rules)
@actr.production
def choose_approach(market_analysis):
    """Select highest-utility approach"""
    return market_analysis.approach

# 3. Activation-based retrieval
retrieved = actr.memory.retrieve(
    'market_analysis',
    partial_match=True,  # Fuzzy matching
    activation_threshold=0.5
)
# Returns fact with highest activation, or None if below threshold

# 4. Learning: activation updates automatically
actr.memory.update_activation(
    fact_id=fact['id'],
    success=True,  # User feedback
    timestamp=time.time()
)
```

### Practical Example: Solo LLM Integration

```python
from python_actr import actr
from anthropic import Anthropic

client = Anthropic()

class LLMBridgedACTR:
    """Minimal ACT-R system integrated with Claude"""

    def __init__(self):
        # ACT-R memory
        self.facts = []
        self.conversations = []  # Procedural memory

    def store_procedure(self, task_type, steps, success_rating):
        """Store how we solved a task"""
        self.conversations.append({
            'task_type': task_type,
            'steps': steps,
            'success_rating': success_rating,
            'activation': success_rating / 10,  # 0.0-1.0
            'timestamp': time.time(),
            'frequency': 1
        })

    def retrieve_similar_procedure(self, current_task):
        """Find similar past solutions (Pattern Matching phase)"""
        best_match = None
        best_score = 0.0

        for conv in self.conversations:
            # Similarity = how well past task matches current task
            similarity = self._calculate_similarity(conv['task_type'], current_task)

            # Activation = success_rating * recency * frequency
            recency = 1.0 - (time.time() - conv['timestamp']) / (365*24*3600)
            activation = (
                0.4 * conv['activation'] +  # Success
                0.3 * recency +              # Recency
                0.3 * min(conv['frequency']/10, 1.0)  # Frequency
            )

            # Combined score
            score = similarity * activation

            if score > best_score:
                best_match = conv
                best_score = score

        return best_match if best_score > 0.6 else None

    def execute_with_llm(self, prompt):
        """Execute: use retrieved procedure OR ask LLM"""

        # Step 1: Pattern Matching (ACT-R Phase 1)
        similar = self.retrieve_similar_procedure(prompt)

        if similar and similar['activation'] > 0.75:
            # Step 2: Production Selection (ACT-R Phase 2)
            print(f"[ACT-R] Using learned procedure (activation: {similar['activation']:.2f})")
            steps = similar['steps']
        else:
            # Not confident enough: ask LLM
            print("[ACT-R] No strong match, querying LLM")
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            steps = response.content[0].text

        # Step 3: Action (ACT-R Phase 3)
        result = self._execute_steps(steps)

        return result, steps

    def _execute_steps(self, steps):
        """Execute the procedure steps"""
        # This depends on your domain
        return f"Executed: {steps[:100]}..."

    def _calculate_similarity(self, past_task, current_task):
        """Simple keyword-based similarity (0.0-1.0)"""
        past_words = set(past_task.lower().split())
        current_words = set(current_task.lower().split())
        intersection = past_words & current_words
        union = past_words | current_words
        return len(intersection) / len(union) if union else 0.0

    def learn(self, task_type, steps, user_rating):
        """Step 4: Learning - update procedural memory"""
        self.store_procedure(task_type, steps, user_rating)
        print(f"[ACT-R Learning] Stored procedure (rating: {user_rating}/10)")


# Usage Example
actr_system = LLMBridgedACTR()

# First request: no history
result1, steps1 = actr_system.execute_with_llm(
    "What opportunities in AI market?"
)
actr_system.learn("market_analysis", steps1, user_rating=9)

# Second request: similar task
result2, steps2 = actr_system.execute_with_llm(
    "What opportunities in blockchain market?"
)
actr_system.learn("market_analysis", steps2, user_rating=8)

# Third request: ACT-R retrieves learned procedure
print(f"\nFirst request used LLM")
print(f"Second request used LLM (low confidence match)")
print(f"Third request would use learned procedure (high confidence)")
```

### When to Use PyACT-R

✅ **Good For**:
- Procedural learning (how to do tasks)
- Implicit learning (activation decay over time)
- Multi-turn conversations with feedback
- Subsymbolic reasoning (fuzzy matching)
- Individual researcher (low complexity, pure Python)

❌ **Not Good For**:
- Complex symbolic reasoning (SOAR is better)
- Explicit rule definition (SOAR's Rete network is superior)
- Real-time constraint reasoning

### Limitations with LLM Integration

```python
# Problem 1: PyACT-R doesn't "know" about LLM output
retrieved_fact = actr.memory.retrieve('market_analysis')
# Returns: {'approach': 'research_first', 'utility': 0.92}
# But doesn't understand it's for "blockchain market"

# Problem 2: Manual similarity calculation required
# You must write your own pattern matcher

# Problem 3: No explicit rule system
# ACT-R stores procedures as activation scores, not explicit rules
# So you can't see "why" it chose something
```

---

## Part 2: SOAR (via Python SML Bindings)

### What It Is

**SOAR** (State, Operator, And Result) is C++ cognitive architecture with Python bindings via SML (Soar Markup Language).

**psoar** (the Python bindings) gives you:
- Working memory (state-operator-result triples)
- Production rules (if-then rules in Rete network)
- Decision making (conflict resolution for operator selection)
- Explicit symbolic reasoning

### Installation

```bash
# Option 1: Pre-built bindings (if available)
pip install soar-sml

# Option 2: Build from source (recommended)
git clone https://github.com/SoarGroup/Soar.git
cd Soar
./build.sh
# Then set PYTHONPATH and LD_LIBRARY_PATH

# Option 3: Use pysoarlib wrapper (easier)
pip install pysoarlib
```

### Core Concepts

**SOAR Structure**:
```python
from Python_sml_ClientInterface import sml  # Low-level SML
# OR use pysoarlib for simpler interface

# 1. Create kernel (SOAR engine)
kernel = sml.Kernel.CreateKernelInCurrentThread()

# 2. Create agent (reasoning system)
agent = kernel.CreateAgent("agent")

# 3. Load SOAR rules (.soar files)
agent.LoadProductions("path/to/rules.soar")

# 4. Add state to working memory
input_link = agent.GetInputLink()
# (state: S1 ^operator op1 ^context market_analysis)

# 5. Run decision cycle
agent.RunSelfForever()  # Blocks until halted
# OR
agent.RunSelf(1)  # Run 1 cycle, return immediately
```

### Practical Example: Solo LLM Integration

```python
from Python_sml_ClientInterface import sml
from anthropic import Anthropic
import json

client = Anthropic()

class LLMBridgedSOAR:
    """Minimal SOAR system integrated with Claude"""

    def __init__(self):
        # SOAR kernel setup
        self.kernel = sml.Kernel.CreateKernelInCurrentThread()
        self.agent = self.kernel.CreateAgent("reasoner")

        # Working memory structure
        self.working_memory = {
            'problem': None,
            'operators': [],
            'chosen_operator': None,
            'outcome': None
        }

        # Learned knowledge base (replaces .soar files)
        self.learned_rules = {}

    def load_initial_rules(self):
        """Instead of loading .soar files, define rules as dicts"""
        # SOAR rules are if-then: IF conditions THEN actions
        self.learned_rules = {
            'market_analysis_pattern': {
                'conditions': {
                    'contains': ['market', 'opportunity', 'analysis'],
                    'reasoning_needed': True
                },
                'operators': [
                    {
                        'name': 'market_research_first',
                        'utility': 0.92,
                        'steps': ['rag_search', 'competitor_analysis', 'gap_identification']
                    },
                    {
                        'name': 'direct_analysis',
                        'utility': 0.55,
                        'steps': ['direct_analysis_only']
                    }
                ]
            }
        }

    def elaborate_state(self, user_prompt):
        """SOAR Elaboration Phase: Understand the problem"""
        # Detect pattern
        pattern = self._match_pattern(user_prompt)

        # SOAR working memory update
        self.working_memory['problem'] = user_prompt
        self.working_memory['pattern_matched'] = pattern is not None

        if pattern:
            self.working_memory['operators'] = pattern['operators']
        else:
            # Ask LLM for new operators
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {"role": "system", "content": "You are a strategic analyst. Propose 3-5 approaches to solve this."},
                    {"role": "user", "content": user_prompt}
                ]
            )
            # Parse operators from LLM response (simplified)
            ops = self._parse_operators(response.content[0].text)
            self.working_memory['operators'] = ops

    def propose_operators(self):
        """SOAR Proposal Phase: Generate candidate operators"""
        # Working memory already has operators from elaborate phase
        return self.working_memory['operators']

    def decide(self):
        """SOAR Decision Phase: Choose best operator"""
        # SOAR decision cycle: select operator with highest utility
        operators = self.working_memory['operators']

        if not operators:
            return None

        # Selection rule: highest utility wins
        best_op = max(operators, key=lambda o: o.get('utility', 0.5))
        self.working_memory['chosen_operator'] = best_op

        return best_op

    def apply_operator(self):
        """SOAR Apply Phase: Execute chosen operator"""
        op = self.working_memory['chosen_operator']

        if not op:
            return None

        print(f"[SOAR] Applying operator: {op['name']} (utility: {op['utility']:.2f})")

        # Execute operator steps
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": f"Execute this task: {op['name']}"},
                {"role": "user", "content": self.working_memory['problem']}
            ]
        )

        result = response.content[0].text
        self.working_memory['outcome'] = result
        return result

    def learn_from_outcome(self, user_rating):
        """SOAR Learning Phase: Update operator utilities"""
        op = self.working_memory['chosen_operator']

        if not op:
            return

        # Update utility (exponential moving average)
        old_utility = op['utility']
        success_score = user_rating / 10
        new_utility = 0.9 * old_utility + 0.1 * success_score

        op['utility'] = new_utility

        print(f"[SOAR Learning] Updated {op['name']}: {old_utility:.2f} → {new_utility:.2f}")

        # Also update learned rules
        self._save_learned_rules()

    def execute_reasoning_cycle(self, user_prompt, user_rating=None):
        """Complete SOAR reasoning cycle (Elaborate→Propose→Decide→Apply→Learn)"""

        print(f"\n[SOAR Cycle] Input: {user_prompt[:50]}...")

        # Phase 1: Elaboration
        print("[SOAR] Phase 1: Elaboration")
        self.elaborate_state(user_prompt)

        # Phase 2: Proposal
        print("[SOAR] Phase 2: Proposal")
        operators = self.propose_operators()
        print(f"  → Proposed {len(operators)} operators")

        # Phase 3: Decision
        print("[SOAR] Phase 3: Decision")
        chosen = self.decide()
        print(f"  → Selected: {chosen['name']}")

        # Phase 4: Apply
        print("[SOAR] Phase 4: Apply")
        result = self.apply_operator()
        print(f"  → Generated {len(result)} char response")

        # Phase 5: Learn (if feedback provided)
        if user_rating is not None:
            print("[SOAR] Phase 5: Learn")
            self.learn_from_outcome(user_rating)

        return result

    def _match_pattern(self, prompt):
        """Check if prompt matches known patterns"""
        for pattern_name, pattern in self.learned_rules.items():
            if self._conditions_match(pattern['conditions'], prompt):
                return pattern
        return None

    def _conditions_match(self, conditions, prompt):
        """Check if conditions are satisfied"""
        prompt_lower = prompt.lower()
        contains = conditions.get('contains', [])
        return all(word in prompt_lower for word in contains)

    def _parse_operators(self, llm_response):
        """Parse operators from LLM response (simplified)"""
        # In production, use proper parsing
        return [
            {'name': 'approach_1', 'utility': 0.5, 'steps': ['step1', 'step2']},
            {'name': 'approach_2', 'utility': 0.5, 'steps': ['step1', 'step2']},
        ]

    def _save_learned_rules(self):
        """Persist learned rules to JSON"""
        with open('soar_rules.json', 'w') as f:
            json.dump(self.learned_rules, f, indent=2)


# Usage Example
soar_system = LLMBridgedSOAR()
soar_system.load_initial_rules()

# First request: no pattern match, full cycle
result1 = soar_system.execute_reasoning_cycle(
    "What opportunities in AI market?",
    user_rating=9
)

# Second request: pattern match, still runs cycle but with known operators
result2 = soar_system.execute_reasoning_cycle(
    "What opportunities in blockchain market?",
    user_rating=8
)
```

### When to Use SOAR

✅ **Good For**:
- Complex symbolic reasoning (explicit rules)
- Goal-oriented behavior (hierarchical planning)
- Clear decision traces (why did it choose that?)
- Multi-step problems (subgoals)
- Teams/larger systems

❌ **Not Good For**:
- Fuzzy/probabilistic tasks (pure SOAR is symbolic)
- Rapid prototyping (steeper learning curve)
- Python-only teams (requires C++ bindings)

### Limitations with LLM Integration

```python
# Problem 1: SOAR rules must be explicitly written
# No automatic pattern learning (unlike ACT-R activation)

# Problem 2: Working memory is strict
# S1 ^problem X ^operator Y
# Doesn't understand semantic meaning of X

# Problem 3: Slow startup
# C++ kernel initialization + SML overhead
# ~500-1000ms startup time vs PyACT-R ~10ms
```

---

## Part 3: Comparison for Your Solo Implementation

### PyACT-R vs SOAR for LLM Integration

| Factor | PyACT-R | SOAR |
|--------|---------|------|
| **Installation** | `pip install python_actr` | Complex (C++ build) |
| **Startup Time** | 10ms | 500-1000ms |
| **Learning Mechanism** | Automatic (activation decay) | Manual (rule updates) |
| **Python Integration** | Native Python | SML bindings |
| **Reasoning Transparency** | Activation scores | Explicit rules |
| **Procedural Learning** | Excellent | Good |
| **Symbolic Reasoning** | Medium | Excellent |
| **Ease for Solo Dev** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

### Recommendation for Your WS2 Solo System

**START WITH PYACTR** if you:
- Want minimal setup (pure Python, pip install)
- Need learning from outcomes (activation decay)
- Prefer rapid prototyping (low complexity)
- Are individual researcher (no team rules engineering)

**UPGRADE TO SOAR** if you:
- Need explicit rule definition (transparency)
- Have complex domain reasoning
- Want hierarchical goal planning
- Have time for C++ integration

---

## Part 4: Hybrid Implementation (Best of Both)

You can combine both architectures:

```python
from python_actr import actr
from Python_sml_ClientInterface import sml
from anthropic import Anthropic

class HybridCognitiveSystem:
    """ACT-R for procedural learning + SOAR for reasoning = WS2 Complete"""

    def __init__(self):
        # ACT-R: procedural memory (how we solve tasks)
        self.actr_procedures = []

        # SOAR: reasoning engine (why we choose operators)
        self.soar_kernel = sml.Kernel.CreateKernelInCurrentThread()
        self.soar_agent = self.soar_kernel.CreateAgent("reasoner")

        self.llm_client = Anthropic()

    def orchestrate(self, user_prompt):
        """Orchestrator decides: ACT-R retrieval OR SOAR reasoning"""

        # Try to retrieve learned procedure (ACT-R)
        learned_proc = self._actr_retrieve(user_prompt)

        if learned_proc and learned_proc['activation'] > 0.75:
            print("[Hybrid] Using ACT-R learned procedure")
            return self._actr_execute(learned_proc)
        else:
            print("[Hybrid] Using SOAR reasoning")
            return self._soar_reason(user_prompt)

    def _actr_retrieve(self, prompt):
        """ACT-R Phase 1-2: Pattern matching + selection"""
        # Search for similar past procedures
        best = None
        for proc in self.actr_procedures:
            similarity = self._similarity(proc['task_type'], prompt)
            activation = proc['activation'] * similarity
            if not best or activation > best['activation']:
                best = {'procedure': proc, 'activation': activation}
        return best

    def _actr_execute(self, match):
        """ACT-R Phase 3: Execute retrieved procedure"""
        proc = match['procedure']
        print(f"[ACT-R] Execute: {proc['name']} (activation: {match['activation']:.2f})")

        # Run the steps
        result = proc['steps'](self.llm_client)
        return result

    def _soar_reason(self, user_prompt):
        """SOAR Cycle: Full reasoning when no strong ACT-R match"""
        # [Full SOAR cycle as shown in Part 2]
        # This produces a new procedure that ACT-R can learn from
        pass

    def _similarity(self, past_task, current_task):
        """Simple keyword similarity"""
        past_words = set(past_task.lower().split())
        current_words = set(current_task.lower().split())
        intersection = len(past_words & current_words)
        union = len(past_words | current_words)
        return intersection / union if union else 0.0


# Usage: Hybrid system automatically uses best approach
system = HybridCognitiveSystem()
result = system.orchestrate("What opportunities in AI market?")
# → Uses SOAR (new task, low ACT-R confidence)

result = system.orchestrate("What opportunities in blockchain market?")
# → Uses ACT-R (similar task, learned procedure has activation > 0.75)
```

---

## Part 5: Practical Implementation Steps

### Step 1: Choose Your Starting Point

**Option A: Pure PyACT-R** (~200 lines, 1 week)
```bash
pip install python_actr
# See PyACT-R example in Part 1
```

**Option B: Pure SOAR** (~300 lines, 2 weeks)
```bash
# Follow SOAR installation in Part 2
# Requires C++ bindings setup
```

**Option C: Hybrid** (~400 lines, 2-3 weeks)
- Start with PyACT-R (1 week)
- Add SOAR for complex tasks (1-2 weeks)

### Step 2: Implement Core Bridge

```python
# bridge.py - Connect cognitive architecture to LLM
class CognitiveArchitectureBridge:

    def __init__(self, choice='actr'):  # or 'soar' or 'hybrid'
        if choice == 'actr':
            self.system = PyACTRBridge()
        elif choice == 'soar':
            self.system = SOARBridge()
        else:
            self.system = HybridBridge()

    def process_prompt(self, prompt, user_rating=None):
        """Unified interface regardless of backend"""
        result = self.system.reason(prompt)

        if user_rating:
            self.system.learn(prompt, result, user_rating)

        return result
```

### Step 3: Add Persistence

```python
# memory.py - Save learned knowledge
import json

def save_state(system):
    """Persist system to disk"""
    state = {
        'procedures': system.procedures,
        'rules': system.rules,
        'timestamp': time.time()
    }
    with open('cognitive_memory.json', 'w') as f:
        json.dump(state, f)

def load_state(system):
    """Restore from disk"""
    with open('cognitive_memory.json', 'r') as f:
        state = json.load(f)
    system.procedures = state['procedures']
    system.rules = state['rules']
```

### Step 4: Test & Iterate

```bash
# Test PyACT-R
python test_actr.py

# Test SOAR
python test_soar.py

# Test integration
python test_hybrid.py
```

---

## Part 6: Decision Matrix

Use this to decide which library to use:

```
Q1: Do you need explicit rule definition?
    YES → SOAR
    NO  → PyACT-R or Hybrid

Q2: Do you want automatic learning from outcomes?
    YES → PyACT-R or Hybrid
    NO  → SOAR

Q3: Do you have time for C++ integration setup?
    YES → SOAR (or Hybrid later)
    NO  → PyACT-R

Q4: Is your domain highly uncertain/fuzzy?
    YES → PyACT-R (activation-based fuzzy matching)
    NO  → SOAR (symbolic reasoning)

Q5: Do you want to understand every decision?
    YES → SOAR (explicit rules visible)
    NO  → PyACT-R (activation scores are abstract)
```

**Your Answer Path** (based on PRACTICAL-SOLO-IMPLEMENTATION.md):
- Q1: No (you have LLM for reasoning)
- Q2: Yes (you want learning from outcomes)
- Q3: No (minimize setup complexity)
- Q4: Yes (LLM outputs are probabilistic)
- Q5: No (show user summary, hide internals)

**Recommendation: START WITH PYACTR**

---

## Part 7: Quick Start Template

```python
# main.py - Start here
from python_actr import actr
from anthropic import Anthropic
import json
import time

class MinimalACTRSystem:
    """Minimum viable ACT-R + LLM system (~100 lines)"""

    def __init__(self):
        self.client = Anthropic()
        self.memory = {'procedures': [], 'activations': {}}

    def solve(self, prompt, visible_reasoning=False):
        # Step 1: Check memory for similar procedures
        similar = self._find_similar(prompt)

        if similar and similar['confidence'] > 0.75:
            # Reuse learned procedure
            if visible_reasoning:
                print(f"[ACT-R] Using learned procedure: {similar['name']}")
            return self._execute_procedure(similar)

        # Step 2: Ask LLM (SOAR-like reasoning)
        if visible_reasoning:
            print("[ACT-R] No learned procedure, querying LLM...")

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.content[0].text

        # Step 3: Store for future learning
        self.memory['procedures'].append({
            'prompt_type': self._extract_type(prompt),
            'prompt_keywords': prompt.split(),
            'result': result,
            'rating': 0,  # Will be set by user
            'timestamp': time.time(),
            'use_count': 1,
            'activation': 0.5  # Start neutral
        })

        return result

    def give_feedback(self, rating):
        """User rates last response (0-10)"""
        if self.memory['procedures']:
            last = self.memory['procedures'][-1]
            last['rating'] = rating
            last['activation'] = rating / 10

    def _find_similar(self, prompt):
        best = None
        prompt_words = set(prompt.lower().split())

        for proc in self.memory['procedures']:
            proc_words = set(proc['prompt_keywords'])
            similarity = len(prompt_words & proc_words) / len(prompt_words | proc_words)
            activation = proc.get('activation', 0.5) * similarity

            if not best or activation > best['confidence']:
                best = {'name': proc['prompt_type'], 'confidence': activation, 'proc': proc}

        return best

    def _execute_procedure(self, match):
        return match['proc']['result']

    def _extract_type(self, prompt):
        # Simple classification
        if 'market' in prompt.lower():
            return 'market_analysis'
        elif 'design' in prompt.lower():
            return 'design'
        return 'general'


# Run it
system = MinimalACTRSystem()

# First call: LLM
print("First call:")
result1 = system.solve("What opportunities in AI market?", visible_reasoning=True)
print(result1[:200] + "...")
system.give_feedback(9)

# Second call: Should use learned procedure (if confident enough)
print("\nSecond call:")
result2 = system.solve("What opportunities in blockchain market?", visible_reasoning=True)
print(result2[:200] + "...")
system.give_feedback(8)

# Third call: Can reuse procedure
print("\nThird call:")
result3 = system.solve("What opportunities in cybersecurity market?", visible_reasoning=True)

# Save memory
with open('actr_memory.json', 'w') as f:
    json.dump(system.memory, f, indent=2)
```

**That's it.** ~100 lines. That's your minimum viable ACT-R system.

---

## Part 8: Troubleshooting

### PyACT-R Issues

| Problem | Solution |
|---------|----------|
| `ImportError: No module actr` | `pip install python_actr` and check Python 3.8-3.11 |
| Activation too slow | Use `partial_match=False` for exact matches |
| Memory grows too large | Implement activation decay cleanup |

### SOAR Issues

| Problem | Solution |
|---------|----------|
| `SML binding not found` | Set `LD_LIBRARY_PATH` to Soar build output |
| Rules not loading | Check .soar file syntax (Soar language is strict) |
| Slow decision cycle | Use `agent.RunSelf(1)` instead of `RunSelfForever()` |

---

## Summary

**For Solo WS2 Implementation:**

1. **Start**: PyACT-R minimal system (Part 7 template) = 100 lines, 1 week
2. **Add**: SOAR for complex reasoning (Part 2 code) = +200 lines, +2 weeks
3. **Integrate**: Hybrid orchestrator (Part 4 code) = +100 lines, +1 week

**Total**: ~400 lines of code, ~4 weeks, complete WS2 system

**Best resource**: Start with Part 7 template, run it, get feedback loop working, then expand to SOAR if needed.

---

**Sources**:
- [Python ACT-R Repository](https://github.com/CarletonCognitiveModelingLab/python_actr)
- [PyPI: python_actr](https://pypi.org/project/actr/)
- [SOAR Group Repository](https://github.com/SoarGroup/Soar)
- [pysoarlib on GitHub](https://github.com/amininger/pysoarlib)
- [SOAR SML Python Bindings](https://pypi.org/project/soar-sml/)
- [The ACT-R Cognitive Architecture Research](https://www.researchgate.net/publication/341388228_The_ACT-R_Cognitive_Architecture_and_Its_pyactr_Implementation)

