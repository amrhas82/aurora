# Unified Solution Architecture: Single Prompt Flow
## Complete Pseudoflow Showing All Layers (Big LLM, Small LLM, SOAR, ACT-R, TAO, PEFT)

**Date**: December 6, 2025
**Purpose**: Detailed pseudocode showing exactly how all components work together on a single prompt
**Context**: Following the Hybrid Approach (Option D) from fine-tuning analysis

---

## Part 1: High-Level Architecture Overview

### The Complete Stack

```
┌─────────────────────────────────────────────────────────┐
│ USER PROMPT (e.g., "Analyze the AI agent market")       │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: ORCHESTRATOR ROUTER (Intelligent Pre-Hook)     │
│ ├─ Parse prompt complexity                              │
│ ├─ Assess reasoning need                                │
│ ├─ Route to FAST or REASONING path                      │
│ └─ Return: {path, context, requires_soar, rag_needed}   │
└────────────────────┬────────────────────────────────────┘
                     ↓
         ┌───────────┴───────────┐
         ↓                       ↓
    [FAST PATH]           [REASONING PATH]
    (easy prompts)        (complex prompts)
         ↓                       ↓
┌──────────────┐      ┌──────────────────────┐
│ LAYER 2:     │      │ LAYER 2:             │
│ Small LLM    │      │ SOAR/ACT-R Reasoning │
│ (Fast)       │      │ (Structured)         │
└──────┬───────┘      └──────┬───────────────┘
       ↓                     ↓
┌──────────────────────────────────────────┐
│ LAYER 3: Fine-tuned LLM (PEFT/Full FT)   │
│ Domain knowledge, instruction following   │
└──────┬───────────────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│ LAYER 4: Big LLM (if needed)             │
│ Complex generation, refinement           │
└──────┬───────────────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│ LAYER 5: RAG Module (Optional)           │
│ External knowledge, current information  │
└──────┬───────────────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│ LAYER 6: TAO Learning (Async)            │
│ Track outcomes, update operator utilities│
└──────┬───────────────────────────────────┘
       ↓
    RESPONSE
```

---

## Part 2: Orchestrator Router (Layer 1) - The Decision Maker

### Purpose
The orchestrator is a **lightweight intelligent router** that decides which path to take based on prompt complexity and characteristics.

### Orchestrator Logic

```python
# ORCHESTRATOR_ROUTER (Pre-Hook)
def route_prompt(user_prompt, conversation_history, persona, context):
    """
    Analyze incoming prompt and decide optimal execution path
    """

    # Step 1: Parse prompt characteristics
    prompt_analysis = {
        'complexity': analyze_complexity(user_prompt),
        # 'complexity' = "simple" | "moderate" | "complex"

        'requires_reasoning': has_reasoning_indicators(user_prompt),
        # Indicators: "why", "analyze", "compare", "strategy", "plan"
        # If YES → reasoning path

        'requires_rag': has_information_indicators(user_prompt),
        # Indicators: "current", "latest", "2025", "today", "research"
        # If YES → enable RAG

        'task_type': classify_task(user_prompt),
        # 'task_type' = "analysis" | "creation" | "brainstorm" |
        #               "design" | "research" | "faq"

        'known_task_pattern': lookup_learned_pattern(user_prompt, knowledge_base),
        # From SOAR learning: have we solved similar before?
        # Returns: {is_known, confidence, learned_operators}
    }

    # Step 2: Decision logic
    if prompt_analysis['complexity'] == 'simple' and \
       prompt_analysis['requires_reasoning'] == False and \
       prompt_analysis['known_task_pattern']['confidence'] > 0.8:

        # FAST PATH: Small LLM with learned pattern
        return {
            'path': 'FAST',
            'use_small_llm': True,
            'use_soar': False,
            'use_act_r': False,
            'llm_model': 'mistral-7b-ft',  # Fine-tuned small model
            'temperature': 0.3,  # Deterministic
            'max_tokens': 500,
        }

    elif prompt_analysis['requires_reasoning'] == True and \
         prompt_analysis['complexity'] in ['moderate', 'complex']:

        # REASONING PATH: SOAR cycles
        return {
            'path': 'REASONING',
            'use_soar': True,
            'use_act_r': False,  # SOAR for reasoning, not learning
            'llm_model': 'mistral-7b-ft',  # Start with fine-tuned small
            'temperature': 0.5,  # Balanced
            'soar_cycles': True,
            'max_soar_iterations': 3,
        }

    elif prompt_analysis['requires_rag'] == True:

        # INFORMATION PATH: RAG + Fine-tuned LLM
        return {
            'path': 'INFORMATION',
            'use_small_llm': True,
            'use_soar': False,
            'use_rag': True,
            'rag_query_type': 'semantic_search',
            'top_k_results': 5,
            'llm_model': 'mistral-7b-ft',
            'temperature': 0.3,
        }

    elif prompt_analysis['complexity'] == 'complex' and \
         prompt_analysis['requires_reasoning'] == True and \
         prompt_analysis['known_task_pattern']['confidence'] < 0.6:

        # COMPLEX REASONING PATH: SOAR + Big LLM for generation
        return {
            'path': 'COMPLEX_REASONING',
            'use_soar': True,
            'use_big_llm': True,  # Need bigger model for complex generation
            'soar_llm_model': 'mistral-7b-ft',  # SOAR cycles with small
            'generation_llm_model': 'claude-opus-4.5',  # Generation with big
            'temperature': 0.7,  # More creative for complex
            'soar_cycles': True,
            'max_soar_iterations': 5,
        }

    elif prompt_analysis['task_type'] == 'brainstorm':

        # CREATIVE PATH: High temperature, no strict reasoning
        return {
            'path': 'CREATIVE',
            'use_big_llm': True,  # Big LLM for diversity
            'temperature': 1.5,  # Creative sampling
            'ensemble_paths': 3,  # Generate 3 different ideas
            'use_soar': False,  # Reasoning blocks creativity
        }

    else:
        # DEFAULT: Moderate path with fine-tuned LLM
        return {
            'path': 'MODERATE',
            'use_small_llm': True,
            'use_soar': False,
            'llm_model': 'mistral-7b-ft',
            'temperature': 0.5,
        }

    # Step 3: Lookup learned patterns (from SOAR/ACT-R learning)
    if analysis['known_task_pattern']:
        routing_decision['learned_operators'] = analysis['known_task_pattern']['operators']
        # These will be used to hint SOAR which operators to try first

    # Step 4: Return routing decision
    return routing_decision
```

### Key Aspects of Orchestrator

✅ **Lightweight**: Runs in milliseconds (not a full reasoning cycle)
✅ **Smart**: Uses learned patterns from previous SOAR/ACT-R runs
✅ **Flexible**: Can route to multiple paths based on prompt type
✅ **Observable**: Returns routing decision so system understands why path chosen

---

## Part 3: FAST PATH (Simple Prompts)

### When Used
- Complexity: LOW
- Reasoning required: NO
- Known pattern: HIGH confidence (learned from previous SOAR runs)
- Examples: "What is X?", "Summarize Y", "List Z"

### Flow

```python
# FAST_PATH (No reasoning needed)
def fast_path_execution(user_prompt, routing_decision):
    """
    Direct execution for simple, known tasks
    """

    # Step 1: Load fine-tuned small LLM
    model = load_model(routing_decision['llm_model'])
    # model = Mistral 7B fine-tuned on domain data
    # ├─ PEFT: Only 1-2% of weights updated
    # └─ Cost: Cheap to host, fast inference

    # Step 2: Apply learned pattern (if exists)
    system_prompt = build_system_prompt(
        persona=routing_decision['persona'],
        learned_pattern=routing_decision.get('learned_operators'),
        task_type=routing_decision['task_type']
    )
    # Example system prompt:
    # "You are a business analyst. For market analysis, ask clarifying
    #  questions first, then provide structured analysis with competitors."
    # (This is based on what SOAR learned works)

    # Step 3: Generate response (fine-tuned LLM)
    response = model.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=routing_decision['temperature'],  # 0.3 (deterministic)
        max_tokens=routing_decision.get('max_tokens', 500)
    )

    # Step 4: Optional: Light verification (if needed)
    if routing_decision['task_type'] in ['factual', 'technical']:
        verification_score = verify_response(response)
        if verification_score < 0.7:
            # Fall back to RAG for verification
            rag_results = retrieve_context(user_prompt)
            response = refine_with_rag(response, rag_results)

    # Step 5: Capture outcome for learning
    outcome = {
        'input': user_prompt,
        'output': response,
        'path': 'FAST',
        'model': routing_decision['llm_model'],
        'timestamp': now(),
        # (Will be scored later by TAO learning)
    }

    # Step 6: Return response
    return {
        'response': response,
        'path_taken': 'FAST',
        'reasoning': None,  # No explicit reasoning
        'models_used': ['mistral-7b-ft'],
        'execution_time_ms': elapsed_time(),
    }

# Example execution:
# ───────────────────
# Input: "What is the current market size for AI agents?"
#
# Orchestrator: "This is simple factual, known pattern (asked 50 times).
#               Use FAST path with small LLM"
#
# Small LLM: "The AI agent market is estimated at $24B in 2024,
#             growing to $150B+ by 2030. Growth drivers include..."
#
# Output time: 200ms
# Cost: $0.001
```

---

## Part 4: REASONING PATH (Complex Prompts) - SOAR Implementation

### When Used
- Complexity: MODERATE to COMPLEX
- Reasoning required: YES (indicators like "why", "analyze", "strategy")
- Unknown domain: Task pattern not learned yet

### SOAR Cycle: How It Works with Prompts

```python
# SOAR_REASONING_PATH
def soar_reasoning_execution(user_prompt, routing_decision):
    """
    SOAR decision cycles for complex reasoning
    """

    print(f"🔄 SOAR REASONING PATH\n")
    print(f"Input: {user_prompt}\n")

    # ══════════════════════════════════════════════════════════════
    # SOAR CYCLE 1: PERCEPTION → ELABORATION
    # ══════════════════════════════════════════════════════════════

    print("─ CYCLE 1: INPUT AND ELABORATION")

    # Step 1a: Elaboration - What does the problem REQUIRE?
    # (At this stage, we ask the LLM to understand the problem)

    elaboration_prompt = f"""
    Analyze this request carefully:
    "{user_prompt}"

    Answer these questions (brief, 1-2 sentences each):
    1. What is being asked? (Core question)
    2. What information do we need? (Required knowledge)
    3. What assumptions should we question? (Potential pitfalls)
    4. What approach would work best? (Initial thinking)
    """

    elaboration = fine_tuned_llm(elaboration_prompt, temp=0.3)
    print(f"\n📋 Elaboration:\n{elaboration}\n")

    # Step 1b: Parse elaboration into SOAR state
    soar_state = {
        'problem': extract_problem(elaboration),
        'required_knowledge': extract_knowledge_needs(elaboration),
        'assumptions': extract_assumptions(elaboration),
        'initial_approach': extract_approach(elaboration),
        'cycle': 1,
    }

    # ══════════════════════════════════════════════════════════════
    # SOAR CYCLE 2: OPERATOR PROPOSAL
    # ══════════════════════════════════════════════════════════════

    print("─ CYCLE 2: OPERATOR PROPOSAL")

    # Step 2a: Generate candidate operators (approaches)
    # SOAR proposes multiple ways to solve it

    operator_proposal_prompt = f"""
    Problem: {soar_state['problem']}

    Generate 3-5 different approaches to solve this:
    - Approach A: [First method]
    - Approach B: [Second method]
    - Approach C: [Third method]

    For each, consider:
    - What information would it need?
    - How long would it take?
    - How confident are we?
    """

    operators = fine_tuned_llm(operator_proposal_prompt, temp=0.5)
    print(f"\n🔧 Candidate Operators:\n{operators}\n")

    # Step 2b: Parse operators and get utilities (from learning)
    proposed_operators = parse_operators(operators)
    for op in proposed_operators:
        op['utility'] = lookup_learned_utility(op['name'], soar_state['task_type'])
        # Utility = P(success | this operator) learned from SOAR history
        # Example:
        #   Operator "Market Research First" utility = 0.92 (been 92% successful)
        #   Operator "Direct Analysis" utility = 0.65

    print(f"Utilities (from learning): {[(op['name'], op['utility']) for op in proposed_operators]}\n")

    # ══════════════════════════════════════════════════════════════
    # SOAR CYCLE 3: OPERATOR EVALUATION
    # ══════════════════════════════════════════════════════════════

    print("─ CYCLE 3: OPERATOR EVALUATION")

    # Step 3a: Evaluate operators based on utilities and context
    evaluation_prompt = f"""
    Given problem: {soar_state['problem']}

    Available approaches with success histories:
    {format_operators_with_utilities(proposed_operators)}

    Current context:
    - Available time: Full (no time pressure)
    - Data availability: {check_data_availability()}
    - User expectations: {extract_user_expectations(user_prompt)}

    Rate each approach (1-10) for this specific context:
    """

    evaluation = fine_tuned_llm(evaluation_prompt, temp=0.3)
    print(f"\n⚖️ Evaluation:\n{evaluation}\n")

    # Step 3b: Score operators
    scores = parse_evaluation(evaluation)
    for op in proposed_operators:
        op['score'] = scores[op['name']]

    # Sort by score
    proposed_operators.sort(key=lambda x: x['score'], reverse=True)
    best_operator = proposed_operators[0]
    print(f"\nBest operator: {best_operator['name']} (score: {best_operator['score']})\n")

    # ══════════════════════════════════════════════════════════════
    # SOAR CYCLE 4: DECISION & EXECUTION
    # ══════════════════════════════════════════════════════════════

    print("─ CYCLE 4: DECISION & EXECUTION")

    # Step 4a: Decide on best operator
    decision = f"Execute: {best_operator['name']}"
    print(f"\n✅ Decision: {decision}\n")

    # Step 4b: Execute the chosen operator
    # (Each operator maps to specific LLM prompting strategy)

    execution_prompt = operator_to_prompt(best_operator, soar_state)
    # Example operator_to_prompt mapping:
    #
    # "Market Research First" operator →
    #   1. Search for market data (RAG)
    #   2. Analyze competitors (Fine-tuned LLM)
    #   3. Identify gaps (Reasoning)
    #   4. Propose solutions
    #
    # "Direct Analysis" operator →
    #   1. Analyze directly (Fine-tuned LLM)
    #   2. Self-verify reasoning
    #   3. Propose

    execution_response = fine_tuned_llm(
        execution_prompt,
        temperature=0.5,
        max_tokens=2000
    )
    print(f"\n📝 Execution Result:\n{execution_response}\n")

    # ══════════════════════════════════════════════════════════════
    # SOAR CYCLE 5: LEARNING (Update for next time)
    # ══════════════════════════════════════════════════════════════

    print("─ CYCLE 5: LEARNING")

    # Step 5a: Capture outcome (will be scored asynchronously)
    outcome = {
        'input': user_prompt,
        'chosen_operator': best_operator['name'],
        'execution_response': execution_response,
        'soar_cycles_used': 1,
        'timestamp': now(),
        'status': 'AWAITING_FEEDBACK',
        # This will be scored by TAO learning module
    }

    print(f"\n🧠 Outcome captured for learning\n")

    # ══════════════════════════════════════════════════════════════
    # IF NEEDED: REFINEMENT LOOP (More SOAR cycles)
    # ══════════════════════════════════════════════════════════════

    # Check if we need more cycles
    if should_refine(execution_response, soar_state):
        print("─ CYCLE 6: REFINEMENT (needs more thinking)")

        refinement_prompt = f"""
        Initial analysis:
        {execution_response}

        Potential gaps:
        - [Gap 1]
        - [Gap 2]

        Provide deeper analysis on:
        {refinement_questions(soar_state)}
        """

        refinement = fine_tuned_llm(refinement_prompt, temp=0.5)
        execution_response = combine_responses(execution_response, refinement)

    # Return final response
    return {
        'response': execution_response,
        'path_taken': 'REASONING',
        'soar_cycles': 5,
        'operator_used': best_operator['name'],
        'reasoning_trace': {
            'elaboration': soar_state,
            'operators_considered': proposed_operators,
            'best_operator_choice': best_operator['name'],
        },
        'execution_time_ms': elapsed_time(),
    }

# Example execution:
# ──────────────────────────────────────────
# Input: "What business opportunities exist in the AI agent market,
#         and what strategies should we pursue?"
#
# Orchestrator: "This requires reasoning. Use SOAR path."
#
# SOAR CYCLE 1 (Elaboration):
#   Problem: "Identify market opportunities and strategic responses"
#   Info needed: "Market size, competitors, gaps, our capabilities"
#   Approach: "Research-first, then analysis"
#
# SOAR CYCLE 2 (Operators):
#   - Operator A: "Market Research → Gap Analysis → Positioning"
#     (Utility: 0.92, learned from past successes)
#   - Operator B: "Direct Strategic Analysis"
#     (Utility: 0.65, less successful historically)
#   - Operator C: "Competitive Benchmarking First"
#     (Utility: 0.78)
#
# SOAR CYCLE 3 (Evaluation):
#   Scores: A=9/10, B=6/10, C=7/10
#   Winner: Operator A
#
# SOAR CYCLE 4 (Execution):
#   1. RAG search for market data
#   2. Fine-tuned LLM analyzes competitors
#   3. Identifies 3 strategic opportunities
#   4. Recommends approach
#
# SOAR CYCLE 5 (Learning):
#   Outcome captured: "Used Operator A, user rates 9/10"
#   Learning: "Operator A utility updated from 0.92 → 0.93"
#
# Output time: 5-10 seconds
# Cost: $0.01
```

---

## Part 5: ACT-R Integration (Learning Path)

### When Used
- Complex tasks where **adaptation** matters more than reasoning
- Multi-turn interactions where user feedback shapes behavior
- Tasks requiring **procedural learning** (learning how to do things)

### ACT-R in Practice

```python
# ACT_R_LEARNING_PATH
def act_r_execution(user_prompt, routing_decision, conversation_history):
    """
    ACT-R decision cycles with procedural learning
    Focus: WHAT procedure works, not HOW to reason about it
    """

    print(f"🧠 ACT-R LEARNING PATH\n")

    # ══════════════════════════════════════════════════════════════
    # ACT-R PHASE 1: PERCEPTION & PATTERN MATCHING
    # ══════════════════════════════════════════════════════════════

    print("─ PHASE 1: PATTERN MATCHING")

    # Step 1a: Check declarative memory for similar past tasks
    past_similar_tasks = search_declarative_memory(
        pattern=user_prompt,
        threshold=0.7  # Need 70% similarity match
    )
    print(f"Similar past tasks: {len(past_similar_tasks)}\n")

    # Step 1b: Retrieve procedures (production rules) used before
    if past_similar_tasks:
        procedures = get_procedures_for_tasks(past_similar_tasks)
        print(f"Learned procedures: {[p['name'] for p in procedures]}\n")

        # Activation decay: procedures used recently have higher activation
        for proc in procedures:
            proc['activation'] = calculate_activation(
                recency=proc['last_used'],
                frequency=proc['use_count']
            )

        # Sort by activation
        procedures.sort(key=lambda x: x['activation'], reverse=True)
    else:
        procedures = []

    # ══════════════════════════════════════════════════════════════
    # ACT-R PHASE 2: PRODUCTION RULE SELECTION
    # ══════════════════════════════════════════════════════════════

    print("─ PHASE 2: PRODUCTION RULE SELECTION")

    # Step 2a: If learned procedures exist, use highest activation one
    if procedures and procedures[0]['activation'] > 0.6:
        selected_procedure = procedures[0]
        print(f"Using learned procedure: {selected_procedure['name']}\n")
        print(f"  - Activation: {selected_procedure['activation']:.2f}")
        print(f"  - Used {selected_procedure['use_count']} times before")
        print(f"  - Success rate: {selected_procedure['success_rate']:.0%}\n")

        # Execute learned procedure
        response = execute_learned_procedure(
            procedure=selected_procedure,
            user_prompt=user_prompt,
            context=conversation_history
        )

    # Step 2b: If no good match, generate new procedure
    else:
        print("No strong learned procedure. Generating new one...\n")

        procedure_generation_prompt = f"""
        Task: {user_prompt}

        Previous similar tasks and their solutions:
        {format_past_tasks(past_similar_tasks)}

        Design a procedure (step-by-step process) to solve this:
        1. First step: [What to do first]
        2. Second step: [Then what]
        3. ...

        This procedure will be learned and reused if successful.
        """

        new_procedure = fine_tuned_llm(procedure_generation_prompt, temp=0.4)
        print(f"New procedure:\n{new_procedure}\n")

        # Execute new procedure
        response = execute_procedure_from_description(
            procedure_description=new_procedure,
            user_prompt=user_prompt
        )

        # Store for learning
        selected_procedure = {
            'name': f"Generated_{hash(user_prompt)}",
            'description': new_procedure,
            'created_at': now(),
            'use_count': 1,
            'success_rate': 0.0,  # Will be updated
            'activation': 0.5,
        }

    # ══════════════════════════════════════════════════════════════
    # ACT-R PHASE 3: ACTION & FEEDBACK
    # ══════════════════════════════════════════════════════════════

    print("─ PHASE 3: EXECUTION & FEEDBACK")

    # Step 3a: Execute and get feedback
    print(f"Response:\n{response}\n")

    # Implicit feedback signals (from conversation continuation)
    feedback_signals = {
        'user_continues': user_continues_conversation(),
        'user_asks_followup': user_asks_followup_question(),
        'user_refines': user_refines_request(),
        'explicit_rating': user_gives_rating(),  # 1-10
        'implementation_successful': implementation_works(),
    }

    success_score = aggregate_feedback(feedback_signals)
    print(f"Success score: {success_score:.2f}/1.0\n")

    # ══════════════════════════════════════════════════════════════
    # ACT-R PHASE 4: LEARNING (Update Activation & Success Rate)
    # ══════════════════════════════════════════════════════════════

    print("─ PHASE 4: LEARNING & MEMORY UPDATE")

    # Step 4a: Update procedural memory (production rules)
    # Higher success → higher activation for next time

    selected_procedure['use_count'] += 1
    old_success_rate = selected_procedure['success_rate']
    selected_procedure['success_rate'] = (
        (old_success_rate * (selected_procedure['use_count'] - 1) + success_score) /
        selected_procedure['use_count']
    )
    selected_procedure['last_used'] = now()

    # Recalculate activation
    selected_procedure['activation'] = calculate_activation(
        success_rate=selected_procedure['success_rate'],
        recency=selected_procedure['last_used'],
        frequency=selected_procedure['use_count']
    )

    print(f"Procedure {selected_procedure['name']} updated:")
    print(f"  - Success rate: {old_success_rate:.0%} → {selected_procedure['success_rate']:.0%}")
    print(f"  - Use count: {selected_procedure['use_count'] - 1} → {selected_procedure['use_count']}")
    print(f"  - Activation: {selected_procedure['activation']:.3f}\n")

    # Step 4b: Store in declarative memory for future reference
    memory_entry = {
        'input': user_prompt,
        'output': response,
        'procedure_used': selected_procedure['name'],
        'success_score': success_score,
        'timestamp': now(),
    }
    store_in_declarative_memory(memory_entry)
    print(f"Stored in memory for future pattern matching\n")

    # Return result
    return {
        'response': response,
        'path_taken': 'ACT_R_LEARNING',
        'procedure_used': selected_procedure['name'],
        'new_or_learned': 'learned' if selected_procedure['use_count'] > 1 else 'new',
        'success_score': success_score,
        'learning_update': {
            'procedure': selected_procedure['name'],
            'success_rate': selected_procedure['success_rate'],
            'activation': selected_procedure['activation'],
        },
    }

# Example execution:
# ──────────────────────────────────────────
# User (Turn 1): "Analyze the market for X"
#   → ACT-R generates new procedure
#   → Stores in memory
#   → Returns analysis
#
# User (Turn 2): "Based on that, what's the strategy?"
#   → ACT-R finds similar procedure (same session)
#   → Uses learned procedure
#   → Better result
#
# User (Turn 3): "Rate this: 8/10, very helpful"
#   → Feedback signal: success_score = 0.9
#   → Procedure activation increases
#   → Next time someone asks similar, this procedure is prioritized
#
# User (Week later): "Analyze market for Y"
#   → ACT-R finds similar procedure from history
#   → Activation scores high (used successfully 8 times)
#   → Uses learned procedure immediately
#   → Much faster, proven approach
```

---

## Part 6: Orchestration Decision (SOAR vs. ACT-R)

### When to Use SOAR vs. ACT-R

```python
def choose_between_soar_and_act_r(user_prompt, conversation_history, task_characteristics):
    """
    Should we use SOAR or ACT-R for this task?
    """

    # SOAR: For reasoning about novel situations
    # ACT-R: For learning from repeated patterns

    if task_characteristics.get('is_novel'):
        # Novel task, not seen before
        # Need to REASON about approach
        return 'SOAR'

    elif len(conversation_history) > 2:
        # Multi-turn conversation
        # Can LEARN from user feedback
        return 'ACT_R'

    elif task_characteristics.get('is_complex_reasoning'):
        # Requires structured problem decomposition
        # SOAR excels at this
        return 'SOAR'

    elif task_characteristics.get('is_procedural'):
        # "How to do X" questions
        # ACT-R learns procedures
        return 'ACT_R'

    elif task_characteristics.get('requires_learning'):
        # Task where feedback shapes approach
        # ACT-R improves with feedback
        return 'ACT_R'

    else:
        # Default: SOAR (safer for unknown)
        return 'SOAR'


# Example decision logic:
# ──────────────────────────────────────────
# Prompt 1: "Analyze market" (novel, first turn)
#   → choose_between_soar_and_act_r() → "SOAR"
#   → Reason through approach structurally
#
# Prompt 2: (User feedback on Prompt 1)
#   → "Based on that analysis, next steps?"
#   → len(history) > 2, task is related
#   → choose_between_soar_and_act_r() → "ACT_R"
#   → Learn from how analysis was done, apply pattern
#   → Faster, using learned procedure
#
# Prompt 3: (Day later) "Analyze market for different domain"
#   → is_novel=True, but similar to past
#   → choose_between_soar_and_act_r() → "ACT_R"
#   → Find similar memory, activate learned procedure
#   → Much faster than SOAR's full reasoning
```

---

## Part 7: TAO Learning Integration (Asynchronous)

### How TAO Continuously Improves Your System

```python
# TAO_LEARNING_MODULE (Runs Asynchronously)
def tao_continuous_learning():
    """
    Test-time Adaptive Optimization:
    Learn from user outcomes and update operator/procedure utilities
    """

    # TAO runs ASYNC (doesn't block user response)
    # Updates happen in background

    while True:
        # Step 1: Collect recent outcomes
        recent_outcomes = get_outcomes_since_last_update(hours=1)
        # outcomes = [
        #   {input, output, operator_used, success_score, timestamp},
        #   ...
        # ]

        if not recent_outcomes:
            sleep(5)
            continue

        print(f"🔄 TAO Learning: Processing {len(recent_outcomes)} outcomes\n")

        # Step 2: Group by operator/procedure
        outcomes_by_operator = group_by_operator(recent_outcomes)

        # Step 3: Update operator utilities (SOAR)
        for operator_name, outcomes in outcomes_by_operator.items():
            old_utility = get_operator_utility(operator_name)

            # Calculate success rate
            success_rate = sum(o['success_score'] for o in outcomes) / len(outcomes)

            # Update utility with exponential smoothing
            new_utility = 0.9 * old_utility + 0.1 * success_rate

            update_operator_utility(operator_name, new_utility)

            print(f"Operator '{operator_name}':")
            print(f"  - Outcomes: {len(outcomes)}")
            print(f"  - Success rate: {success_rate:.1%}")
            print(f"  - Utility: {old_utility:.3f} → {new_utility:.3f}\n")

        # Step 4: Update procedure activations (ACT-R)
        # (This happens during ACT-R execution, not here)

        # Step 5: Store insights for future routing
        update_learned_patterns(outcomes_by_operator)

        # Step 6: Sleep before next batch
        sleep(60)  # Update every minute


# Example TAO learning:
# ──────────────────────────────────────────
# Initial state:
#   "Market Research First" operator utility: 0.80
#   "Direct Analysis" operator utility: 0.65
#
# Last hour outcomes:
#   - "Market Research First": 8 uses, avg success 0.88
#   - "Direct Analysis": 5 uses, avg success 0.52
#   - "Hybrid Approach": 3 uses, avg success 0.92
#
# TAO update:
#   "Market Research First": 0.80 → 0.872
#   "Direct Analysis": 0.65 → 0.603
#   "Hybrid Approach": 0.50 → 0.542 (if existed), or created with 0.92
#
# Next prompt using "Market Analysis":
#   SOAR sees updated utilities
#   → Prioritizes "Market Research First" (higher utility now)
#   → More likely to succeed again
```

---

## Part 8: Complete Single Prompt Example

### Scenario
User: "What business opportunities exist in the AI agent market? I need data-driven insights and strategic recommendations."

### Full Execution Flow

```
═══════════════════════════════════════════════════════════════════
SINGLE PROMPT COMPLETE EXECUTION
═══════════════════════════════════════════════════════════════════

INPUT:
  "What business opportunities exist in the AI agent market?
   I need data-driven insights and strategic recommendations."

═══════════════════════════════════════════════════════════════════
STEP 1: ORCHESTRATOR ROUTER (Pre-hook, ~50ms)
═══════════════════════════════════════════════════════════════════

Orchestrator analyzes:
  ✓ Complexity: COMPLEX
  ✓ Requires reasoning: YES (analyze, opportunities)
  ✓ Requires RAG: YES (data, market info, 2025 knowledge)
  ✓ Known pattern: MODERATE confidence (asked 12 times before)

Routing decision:
  Path: COMPLEX_REASONING
  Use: SOAR + RAG + Fine-tuned LLM + Big LLM (for generation)
  Learned operators: ["Market Research First", "Competitive Benchmarking", "Gap Analysis"]

═══════════════════════════════════════════════════════════════════
STEP 2: SOAR REASONING CYCLES (~5-10 seconds)
═══════════════════════════════════════════════════════════════════

CYCLE 1: Elaboration (Fine-tuned small LLM)
  ─────────────────────────────────────────
  Question: What does this task require?

  Fine-tuned LLM:
    "Core question: Identify business opportunities in AI agent market
     Information needed: Market size, growth rate, competitors, gaps, our capabilities
     Key assumptions: Market size data available, competition is known
     Approach: Research-first (gather data) then analysis (find gaps)"

CYCLE 2: Operator Proposal (Fine-tuned small LLM)
  ────────────────────────────────────────────────
  Question: What are different approaches?

  Fine-tuned LLM proposes:
    Operator A: "Market Research → Gap Analysis → Positioning"
      - Need RAG search for data (available)
      - Utility: 0.92 (learned from past, very successful)

    Operator B: "Competitive Benchmarking → Market Analysis → Strategy"
      - Need competitor data (available)
      - Utility: 0.78 (moderately successful)

    Operator C: "Direct Strategic Analysis (no research)"
      - No external data needed
      - Utility: 0.55 (less successful, less comprehensive)

CYCLE 3: Operator Evaluation (Fine-tuned small LLM)
  ─────────────────────────────────────────────────
  Question: Which operator is best for THIS context?

  Context given to LLM:
    - User wants: "data-driven insights" (indicates research important)
    - Time: No pressure (indicates can do full research)
    - Data: All available via RAG

  Fine-tuned LLM evaluation:
    Operator A score: 9.5/10 (matches needs perfectly)
    Operator B score: 8.0/10 (good, but less comprehensive)
    Operator C score: 4.5/10 (insufficient for "data-driven")

  Winner: Operator A "Market Research First"

CYCLE 4: Execution (Fine-tuned LLM + RAG + Big LLM)
  ────────────────────────────────────────────────

  Sub-step 4a: Market Research (RAG)
    ─────────────────────────────────
    RAG query: "AI agent market size 2024 2025 growth forecasts"
    RAG results: 5 articles from Gartner, Forrester, IDC
    - Market: $24B (2024) → $150B (2030)
    - Growth: 47% CAGR
    - Top players: OpenAI, Anthropic, Google
    - Key trends: Enterprise adoption, vertical specialization

  Sub-step 4b: Competitor Analysis (Fine-tuned LLM)
    ──────────────────────────────────────────────
    Prompt to fine-tuned LLM:
      "Based on market data [from RAG], analyze 5 major competitors:
       - Market position (size, revenue)
       - Technology differentiation
       - Customer base
       - Gaps in their offerings"

    Fine-tuned LLM response:
      "OpenAI: Market leader, GPT foundation, broad use cases
               Weakness: No vertical specialization, high cost

       Anthropic: Constitutional AI, enterprise focus
                  Weakness: Smaller market share, limited reach

       [etc for 5 competitors]

       Market gaps identified:
       1. Privacy-first solutions (zero data leave org)
       2. Industry-specific agents (vertical SaaS)
       3. Cost-effective alternatives"

  Sub-step 4c: Opportunity Synthesis (Big LLM - Claude Opus)
    ──────────────────────────────────────────────────────
    Input to big LLM:
      - Market data from RAG
      - Competitor analysis from fine-tuned LLM
      - User request: "opportunities + strategic recommendations"

    Big LLM generates comprehensive response:
      "BUSINESS OPPORTUNITIES IN AI AGENT MARKET

       1. Privacy-First Enterprise Platform
          Market size: $8-12B (2030)
          Positioning: Only solution with zero data leaving organization
          Go-to-market: Enterprise security teams
          Revenue: $500K-5M per customer

       2. Vertical-Specific Agent SaaS
          Market size: $15-25B (2030)
          Positioning: Industry-specific expertise (not generic)
          Go-to-market: Vertical market leaders
          Revenue: $50-200K per customer per vertical

       3. Cost-Effective Open-Source Stack
          Market size: $5-8B (2030)
          Positioning: Lowest TCO alternative to proprietary solutions
          Go-to-market: Mid-market and developer communities
          Revenue: Support/SaaS layer

       STRATEGIC RECOMMENDATIONS:
       1. Choose ONE vertical (e.g., legal, financial, healthcare)
       2. Build for that vertical first (faster to market)
       3. Use open-source models (cost advantage)
       4. Differentiate on domain expertise, not AI capability
       5. Plan vertical expansion (year 2-3)"

CYCLE 5: Learning (Async, asynchronous capture)
  ──────────────────────────────────────────────
  Capture outcome:
    {
      input: "What business opportunities...",
      operator_used: "Market Research First",
      elaboration: "...",
      final_response: "BUSINESS OPPORTUNITIES...",
      models_used: ["mistral-7b-ft", "claude-opus-4.5"],
      rag_results_used: 5,
      execution_time: "7 seconds",
      status: "AWAITING_FEEDBACK",
    }

  (Will be scored by user: "9/10 - very helpful", "used for pitch deck")
  TAO will update: Operator A utility: 0.92 → 0.928

═══════════════════════════════════════════════════════════════════
STEP 3: RESPONSE TO USER (~7 seconds total)
═══════════════════════════════════════════════════════════════════

User receives:
  - Comprehensive market analysis
  - 3 specific opportunities with sizing
  - 5 strategic recommendations
  - Data-driven insights with citations

═══════════════════════════════════════════════════════════════════
STEP 4: TAO LEARNING (Background, async)
═══════════════════════════════════════════════════════════════════

User rates response: "9/10 - Used this for board presentation"
Success signal captured

TAO learning:
  "Market Research First" operator:
    Old utility: 0.920
    Success score: 0.90 (9/10 rating)
    New utility: 0.90 * 0.920 + 0.10 * 0.90 = 0.918

  Wait, that went DOWN? Let me recalculate:
    New utility: 0.85 * 0.920 + 0.15 * 0.90 = 0.915

  Hmm, actually with exponential smoothing and high confidence:
    New utility: 0.95 * 0.920 + 0.05 * 0.90 = 0.919

  Keep high utility, slight update.

Next time similar prompt:
  SOAR sees "Market Research First" utility: 0.919
  → Selects same operator immediately
  → Even faster and more confident

═══════════════════════════════════════════════════════════════════
SUMMARY
═══════════════════════════════════════════════════════════════════

Execution timeline:
  - Orchestrator decision: 50ms
  - SOAR cycles: 6-8 seconds (small LLM)
  - RAG retrieval: 1-2 seconds
  - Big LLM generation: 1-2 seconds
  - Total: ~7-10 seconds

Cost breakdown:
  - Fine-tuned small LLM: $0.003 (PEFT, efficient)
  - Big LLM: $0.008 (complex generation)
  - RAG: $0.001 (semantic search)
  - Total: ~$0.012 per prompt

Models used:
  ✓ Fine-tuned Mistral 7B (PEFT) - for SOAR reasoning
  ✓ Claude Opus 4.5 (big LLM) - for final generation
  ✓ RAG module - for current data

Learning captured:
  ✓ SOAR operator utility updated
  ✓ ACT-R procedure memory (if multi-turn)
  ✓ Outcome stored for future pattern matching
  ✓ System improves for next similar prompt
```

---

## Part 9: Architecture Decision Summary

### Key Design Decisions

```
1. ORCHESTRATOR ROUTER at Layer 1
   ✓ Intelligent pre-hook that routes to optimal path
   ✓ Uses learned patterns from SOAR history
   ✓ NO SOAR/ACT-R per-prompt (only when needed)
   ✓ Result: Fast simple tasks, reasoned complex tasks

2. SOAR operates at REASONING LAYER (Cycles 2-5)
   ✓ NOT per-token, NOT replacing LLM generation
   ✓ Per-PROMPT reasoning (5-10 seconds)
   ✓ Uses fine-tuned LLM for each cycle
   ✓ Final generation by big LLM
   ✓ Result: Structured problem decomposition

3. ACT-R operates at LEARNING LAYER (Procedural Memory)
   ✓ Learns PROCEDURES (how to solve recurring tasks)
   ✓ Tracks ACTIVATION (which procedures to use)
   ✓ Updates based on feedback (explicit or implicit)
   ✓ Result: Faster, proven approaches for known tasks

4. TAO operates ASYNCHRONOUSLY
   ✓ Doesn't block user response
   ✓ Updates operator utilities from outcomes
   ✓ Updates procedure activations from feedback
   ✓ Result: System improves without user noticing

5. PEFT for Fine-tuned LLM
   ✓ Only 1-2% of weights updated
   ✓ 10,000x less memory than full fine-tuning
   ✓ Fast to deploy, cheap to host
   ✓ Can have multiple domain-specific adapters
   ✓ Result: Cost-efficient, switchable models

6. LAYERING (not replacement)
   ✓ Small LLM doesn't replace big LLM
   ✓ SOAR doesn't replace LLM generation
   ✓ Each layer adds value
   ✓ Can be composed differently for different tasks
   ✓ Result: Flexibility, efficiency, capability
```

---

## Part 10: When SOAR/ACT-R Are Used (Decision Framework)

### Precise Conditions

```
ORCHESTRATOR DECISION:

USE FAST PATH (Small LLM only):
  ├─ Complexity: LOW
  ├─ Reasoning needed: NO
  ├─ Known pattern: HIGH confidence (>0.8)
  └─ Examples: "What is X?", "Summarize Y", FAQs
  └─ Time: 200-500ms, Cost: $0.001

USE SOAR (Reasoning cycles):
  ├─ Complexity: MODERATE to COMPLEX
  ├─ Reasoning needed: YES ("why", "analyze", "strategy", "plan")
  ├─ Novel task: HIGH (not seen before, or pattern <0.6 confidence)
  ├─ Tasks include: Analysis, design, strategy, multi-step
  └─ Time: 5-15 seconds, Cost: $0.01-0.02

  SOAR cycles:
    1. Elaboration (understand)
    2. Operator proposal (generate options)
    3. Evaluation (score options)
    4. Execution (do best option)
    5. Learning (capture for TAO)

USE ACT-R (Procedural learning):
  ├─ Context: Multi-turn conversation
  ├─ Task type: Procedural ("how to", recurring patterns)
  ├─ Feedback available: User gives signals (ratings, continue, refine)
  ├─ Adaptation needed: YES (approach changes based on feedback)
  └─ Time: 2-5 seconds (faster than SOAR), Cost: $0.005

  ACT-R phases:
    1. Pattern matching (find similar memories)
    2. Production selection (choose procedure)
    3. Action (execute with feedback)
    4. Learning (update activation)

USE SOAR + BIG LLM (Complex generation):
  ├─ SOAR cycles: Small LLM for reasoning
  ├─ Generation: Big LLM for complex output
  ├─ Examples: Comprehensive strategies, detailed reports
  └─ Time: 7-15 seconds, Cost: $0.01-0.03

USE RAG (Information retrieval):
  ├─ Trigger: Current data needed
  ├─ Indicators: "2025", "latest", "today", "research"
  ├─ Can combine: SOAR + RAG, ACT-R + RAG, LLM + RAG
  └─ Time: +1-2 seconds, Cost: +$0.001

USE ORCHESTRATOR ROUTING:
  ✓ ALWAYS (every prompt)
  ├─ Analyzes prompt characteristics
  ├─ Looks up learned patterns
  ├─ Decides optimal path
  ├─ ~50ms, negligible cost
  └─ Result: Automatic path selection
```

---

## Part 11: Visual Architecture

```
                    USER PROMPT
                        ↓
        ┌───────────────────────────────┐
        │  ORCHESTRATOR ROUTER          │
        │  (Pre-hook: 50ms)             │
        │  ├─ Analyze complexity        │
        │  ├─ Check learned patterns    │
        │  └─ Route to optimal path     │
        └─────────────┬─────────────────┘
                      ↓
        ┌─────────────────────────────────────┐
        │ DECISION: Which path?               │
        └──┬───────────────┬───────────┬──────┘
           ↓               ↓           ↓
     [FAST PATH]    [SOAR PATH]  [ACT-R PATH]
     (Simple)       (Complex)     (Learning)
           ↓               ↓           ↓
     ┌─────────┐  ┌──────────────┐ ┌────────┐
     │Small LLM│  │ SOAR Cycles: │ │ACT-R:  │
     │(PEFT)   │  │ 1. Elaborate │ │1.Match │
     │         │  │ 2. Propose   │ │2.Select│
     │Temp:0.3 │  │ 3. Evaluate  │ │3.Act   │
     │Cost:$0.1│  │ 4. Execute   │ │4.Learn │
     │Time:200m│  │ 5. Learn     │ │        │
     │         │  │              │ │Temp:0.5│
     │         │  │Small LLM + 1 │ │Cost:$0.01
     │         │  │big LLM cycle │ │Time:3-5s
     │         │  │Temp:0.5      │ │        │
     │         │  │Cost:$0.02    │ │        │
     │         │  │Time:5-10s    │ │        │
     └────┬────┘  └──────┬───────┘ └───┬────┘
          │               │             │
          │         [RAG optional]      │
          │         (Add facts)         │
          │               │             │
          └───────────┬───┴──────┬──────┘
                      ↓          ↓
        ┌─────────────────────────────┐
        │ Big LLM (if needed)         │
        │ Claude Opus (generation)    │
        │ Temperature: 0.5-0.7        │
        │ Cost: $0.01                 │
        │ Time: 1-2s                  │
        └──────────────┬──────────────┘
                       ↓
        ┌─────────────────────────────┐
        │ RESPONSE to User            │
        │ (7-15 seconds total)        │
        │ (Cost: $0.01-0.03 total)    │
        └──────────────┬──────────────┘
                       ↓
        ┌──────────────────────────────┐
        │ TAO LEARNING (Async)         │
        │ └─ Update operator utilities │
        │ └─ Update procedure activation
        │ └─ Store for future patterns │
        │ (Doesn't block user)         │
        └──────────────────────────────┘
```

---

## Part 12: FAQ: SOAR/ACT-R Integration

### Q: Will every prompt go through SOAR/ACT-R?

**A: NO.** Only complex prompts requiring reasoning.

- Simple prompt ("What is X?"): Small LLM only (~200ms)
- Complex prompt ("Analyze market..."): SOAR reasoning (~7s)
- Recurring prompt (multi-turn): ACT-R procedures (~3s)

Orchestrator routes automatically.

---

### Q: How many SOAR cycles per prompt?

**A: 1-5 cycles, typically 2-3.**

- Cycle 1: Elaboration (understand problem)
- Cycle 2: Operator proposal & evaluation (choose approach)
- Cycle 3+: Execution & optional refinement

Each cycle uses fine-tuned small LLM (fast).

---

### Q: At what level do SOAR/ACT-R operate?

**A: At the REASONING and LEARNING layers, not token layer.**

```
Token layer (LLM predicts):     "The AI agent market..."
                                  ↑ (Generated by LLM)

Reasoning layer (SOAR decides):  "Use Market Research operator"
                                  ↑ (Structured decision)

Learning layer (ACT-R adapts):   "This procedure worked 8 times before"
                                  ↑ (Procedural memory)
```

They don't replace LLM; they guide it.

---

### Q: What's the cost/time tradeoff?

**A: Orchestrator handles it.**

```
FAST PATH (simple):        200ms, $0.001
MODERATE PATH (moderate):  2-3s, $0.005
SOAR PATH (complex):       5-10s, $0.02
SOAR + Big LLM (very):     7-15s, $0.03
```

User doesn't pay for unnecessary complexity.

---

### Q: How does TAO work with SOAR/ACT-R?

**A: Asynchronously updates operator utilities and procedures.**

```
Execution (blocking user):
  Prompt → Orchestrator → SOAR → Response (5-10s)

Learning (background, async):
  Capture outcome → Score outcome → Update utilities → Done
  (User doesn't wait)
```

Next time similar prompt appears, SOAR/ACT-R are smarter.

---

### Q: How is this different from fine-tuning?

**A: Layered approach.**

```
Fine-tuning (Layer 3):
  ├─ Updates weights on domain data
  ├─ Makes LLM better at predicting tokens
  ├─ Cost: High compute
  └─ Benefit: Domain knowledge

SOAR/ACT-R (Layers 1-2, 5-6):
  ├─ Structures reasoning (SOAR)
  ├─ Structures learning (ACT-R)
  ├─ Orchestrates path selection (Router)
  ├─ Cost: Low (inference only)
  └─ Benefit: Reasoning, learning, adaptation
```

Both together: Better than either alone.

---

### Q: Can I use just SOAR without ACT-R?

**A: YES.** Orchestrator can be configured:

```
Config A: Router → SOAR → Response
          (Just reasoning, no learning)

Config B: Router → ACT-R → Response
          (Just learning, no reasoning)

Config C: Router → SOAR or ACT-R → Response
          (Use context to decide)

Config D: Router → SOAR → ACT-R → Response
          (Both, sequential)
```

Choose based on your use case.

---

### Q: How does user feedback feed into learning?

**A: Multiple signals captured automatically.**

```
Explicit signals:
  └─ User rates: "9/10" → success_score = 0.9

Implicit signals:
  ├─ User continues conversation → usefulness (0.7)
  ├─ User asks follow-up → foundation was good (0.8)
  ├─ User refines request → needs clarification (0.5)
  ├─ User implements → real success (0.95)
  └─ User stops responding → dissatisfaction (0.3)

TAO aggregates → updates utilities:
  operator['utility'] = 0.9 * old_utility + 0.1 * feedback_score
```

Learning is continuous and automatic.

---

## Summary: Single Prompt Flow

```
EVERY PROMPT flows through these layers:

1. ORCHESTRATOR (Pre-hook)
   └─ Route to optimal path based on complexity

2. EXECUTION PATH (One of: FAST, SOAR, ACT-R, COMPLEX)
   └─ Execute with appropriate reasoning/learning

3. RESPONSE
   └─ Return to user (200ms to 15 seconds)

4. TAO LEARNING (Async)
   └─ Update utilities for next time

Result:
  ✓ Simple tasks: FAST (no overhead)
  ✓ Complex tasks: SOAR (structured reasoning)
  ✓ Recurring tasks: ACT-R (learned procedures)
  ✓ All tasks: TAO (continuous improvement)
```

---

**Date**: December 6, 2025
**Status**: Complete pseudoflow architecture ready for implementation
**Next**: Create implementation guide for Orchestrator Router and Layer 2-6 components
