# Implementation Details: Storage, Matching, Decision Trees, and Internal Conversations
## How SOAR/ACT-R Actually Work Under the Hood

**Date**: December 6, 2025
**Focus**: Technical implementation details, not pseudocode

---

## Part 1: Where Previous SOAR Runs Are Stored (JSON Storage)

### Knowledge Base Structure

```json
{
  "soar_history": {
    "operators": {
      "market_research_first": {
        "id": "op_001",
        "name": "Market Research First",
        "description": "Search for market data, analyze competitors, identify gaps",
        "utility": 0.925,
        "utility_history": [
          {"date": "2025-12-05", "value": 0.92},
          {"date": "2025-12-04", "value": 0.91},
          {"date": "2025-12-01", "value": 0.88}
        ],
        "use_count": 47,
        "success_count": 42,
        "success_rate": 0.893,
        "steps": [
          {"step": 1, "action": "rag_search", "query": "market data {domain}"},
          {"step": 2, "action": "fine_tuned_llm", "prompt": "analyze_competitors"},
          {"step": 3, "action": "fine_tuned_llm", "prompt": "identify_gaps"},
          {"step": 4, "action": "big_llm", "prompt": "synthesize_opportunities"}
        ],
        "last_used": "2025-12-06T14:32:00Z",
        "created": "2025-11-15T10:00:00Z"
      },

      "direct_analysis": {
        "id": "op_002",
        "name": "Direct Analysis",
        "description": "Analyze directly without research",
        "utility": 0.52,
        "use_count": 19,
        "success_count": 10,
        "success_rate": 0.526,
        "steps": [
          {"step": 1, "action": "fine_tuned_llm", "prompt": "direct_analysis"},
          {"step": 2, "action": "fine_tuned_llm", "prompt": "verify_reasoning"}
        ],
        "last_used": "2025-12-03T09:15:00Z"
      }
    },

    "problem_patterns": {
      "market_analysis_general": {
        "pattern_id": "pat_001",
        "pattern_keywords": ["market", "opportunity", "analysis", "business"],
        "pattern_similarity": 0.85,
        "successful_operators": [
          {"operator": "market_research_first", "success_rate": 0.89},
          {"operator": "benchmarking_first", "success_rate": 0.78},
          {"operator": "direct_analysis", "success_rate": 0.52}
        ],
        "past_executions": [
          {
            "execution_id": "exec_001",
            "input": "What opportunities in AI agent market?",
            "operator_used": "market_research_first",
            "outcome": {
              "success_score": 0.95,
              "user_rating": 9,
              "feedback": "Used for board presentation",
              "implicit_signals": {
                "user_continued": true,
                "asked_followup": false,
                "requested_refinement": false
              }
            },
            "timestamp": "2025-12-05T14:22:00Z"
          },
          {
            "execution_id": "exec_002",
            "input": "Market opportunities for blockchain?",
            "operator_used": "market_research_first",
            "outcome": {
              "success_score": 0.92,
              "user_rating": 8,
              "feedback": "Excellent, actionable insights"
            },
            "timestamp": "2025-12-04T11:45:00Z"
          },
          {
            "execution_id": "exec_003",
            "input": "What's the market for IoT?",
            "operator_used": "direct_analysis",
            "outcome": {
              "success_score": 0.45,
              "user_rating": 3,
              "feedback": "Too generic, needs research"
            },
            "timestamp": "2025-12-02T16:30:00Z"
          }
        ],
        "pattern_confidence": 0.87,
        "recommended_operator": "market_research_first",
        "last_updated": "2025-12-06T14:32:00Z"
      },

      "technical_design_pattern": {
        "pattern_id": "pat_002",
        "pattern_keywords": ["design", "architecture", "system", "technical"],
        "successful_operators": [
          {"operator": "structured_design_first", "success_rate": 0.91},
          {"operator": "use_case_first", "success_rate": 0.85}
        ],
        "pattern_confidence": 0.83
      }
    }
  },

  "act_r_history": {
    "procedures": {
      "market_analysis_procedure_001": {
        "procedure_id": "proc_001",
        "name": "Market Analysis - Standard",
        "description": "Multi-step procedure for analyzing markets",
        "created": "2025-11-20T08:00:00Z",
        "steps": [
          {"step": 1, "action": "clarify", "prompt": "What segment? Geography? Timeframe?"},
          {"step": 2, "action": "research", "prompt": "Search for market data"},
          {"step": 3, "action": "analyze", "prompt": "Analyze competitors"},
          {"step": 4, "action": "synthesize", "prompt": "Find opportunities"}
        ],
        "activation": 0.87,
        "activation_components": {
          "recency": 0.92,  // Last used 30 min ago
          "frequency": 0.82,  // Used 12 times
          "success_history": 0.89  // 89% success rate
        },
        "use_count": 12,
        "success_count": 10,
        "success_rate": 0.833,
        "last_used": "2025-12-06T14:30:00Z",
        "procedural_memory": {
          "learned_patterns": [
            {
              "context": "Financial market analysis",
              "refinement": "Always ask about regulatory environment",
              "success_boost": 0.08
            },
            {
              "context": "Tech market analysis",
              "refinement": "Prioritize innovation metrics over traditional metrics",
              "success_boost": 0.12
            }
          ]
        }
      },

      "strategy_procedure_001": {
        "procedure_id": "proc_002",
        "name": "Strategy Development",
        "activation": 0.65,
        "use_count": 7,
        "success_rate": 0.714
      }
    },

    "declarative_memory": [
      {
        "memory_id": "mem_001",
        "input": "What opportunities in AI agent market?",
        "output": "BUSINESS OPPORTUNITIES: ...",
        "procedure_used": "market_analysis_procedure_001",
        "success_score": 0.95,
        "timestamp": "2025-12-05T14:22:00Z",
        "accessibility": {
          "retrieval_strength": 0.95,
          "decay_rate": 0.02  // Minimal decay (recent and successful)
        }
      },
      {
        "memory_id": "mem_002",
        "input": "Market for blockchain?",
        "output": "MARKET ANALYSIS: ...",
        "procedure_used": "market_analysis_procedure_001",
        "success_score": 0.92,
        "timestamp": "2025-12-04T11:45:00Z",
        "accessibility": {
          "retrieval_strength": 0.91
        }
      }
    ]
  }
}
```

---

## Part 2: Pattern Matching and Retrieval

### How Orchestrator Searches for Similar Requests

```python
# PATTERN_MATCHING_ENGINE
class PatternMatcher:
    """Find similar past executions and use their successful operators"""

    def find_similar_pattern(user_prompt: str, knowledge_base: dict) -> dict:
        """
        Search JSON for similar patterns
        """

        # Step 1: Extract keywords from user prompt
        keywords = extract_keywords(user_prompt)
        # Example: "What opportunities in AI market?"
        # Keywords: ["opportunities", "AI", "market", "analysis"]

        # Step 2: Search for matching patterns in knowledge_base
        candidates = []

        for pattern_id, pattern_data in knowledge_base['soar_history']['problem_patterns'].items():
            # Calculate similarity: how many keywords match?
            keyword_match = calculate_keyword_overlap(
                keywords,
                pattern_data['pattern_keywords']
            )
            # Result: 0.0-1.0 (1.0 = perfect match)

            # Similarity example:
            # New prompt keywords: ["opportunities", "AI", "market"]
            # Pattern keywords: ["market", "opportunity", "analysis", "business"]
            # Match: 3 out of 4 = 0.75 similarity

            if keyword_match > 0.6:  # At least 60% match
                candidates.append({
                    'pattern_id': pattern_id,
                    'similarity_score': keyword_match,
                    'pattern_data': pattern_data,
                    'reason': f"Matched on {keyword_match:.0%} of keywords"
                })

        # Step 3: Rank by similarity and confidence
        candidates.sort(
            key=lambda x: x['similarity_score'] * x['pattern_data']['pattern_confidence'],
            reverse=True
        )
        # Sort by: (keyword match) * (pattern confidence)
        # Example: 0.75 match * 0.87 confidence = 0.6525 score

        if candidates:
            best_match = candidates[0]
            return {
                'pattern_found': True,
                'pattern_id': best_match['pattern_id'],
                'similarity': best_match['similarity_score'],
                'pattern_confidence': best_match['pattern_data']['pattern_confidence'],
                'recommended_operators': best_match['pattern_data']['successful_operators'],
                'past_executions': best_match['pattern_data']['past_executions']
            }
        else:
            return {
                'pattern_found': False,
                'reason': 'No similar pattern found'
            }

    # Example execution:
    # ───────────────────────────────────────
    # New prompt: "What opportunities in AI market?"
    #
    # Search knowledge_base:
    #   Pattern "market_analysis_general" matches with 0.75 similarity
    #   Pattern confidence: 0.87
    #   Score: 0.75 * 0.87 = 0.6525
    #
    # Result:
    #   {
    #     'pattern_found': True,
    #     'pattern_id': 'pat_001',
    #     'similarity': 0.75,
    #     'recommended_operators': [
    #       {'operator': 'market_research_first', 'success_rate': 0.89},
    #       {'operator': 'benchmarking_first', 'success_rate': 0.78},
    #       {'operator': 'direct_analysis', 'success_rate': 0.52}
    #     ]
    #   }
```

---

## Part 3: Complexity Detection (What Triggers SOAR)

### Complexity Detection Algorithm

```python
# COMPLEXITY_DETECTOR
class ComplexityDetector:
    """Determine if prompt needs reasoning (SOAR) or not"""

    def detect_complexity(user_prompt: str) -> dict:
        """
        Analyze prompt and determine complexity level
        """

        # Scoring: Each indicator adds points
        score = 0

        # ─────────────────────────────────────────────────
        # INDICATOR 1: REASONING KEYWORDS (30 points possible)
        # ─────────────────────────────────────────────────

        reasoning_keywords = {
            'analyze': 5,
            'why': 5,
            'strategy': 5,
            'plan': 5,
            'design': 5,
            'compare': 4,
            'evaluate': 4,
            'assess': 4,
            'recommend': 4,
            'approach': 3,
            'solve': 3,
            'trade-off': 4,
            'decision': 3,
            'opportunity': 4,
            'problem': 3,
        }

        for keyword, points in reasoning_keywords.items():
            if keyword in user_prompt.lower():
                score += points

        # Example: "What opportunities exist?"
        # Found: "opportunities" (+4 points)
        # Score so far: 4

        # ─────────────────────────────────────────────────
        # INDICATOR 2: QUESTION COMPLEXITY (25 points possible)
        # ─────────────────────────────────────────────────

        # Multi-part questions are complex
        num_questions = user_prompt.count('?')
        if num_questions > 1:
            score += 10  # Multiple questions

        # Questions asking "how" or "why" are complex
        if user_prompt.lower().startswith(('how', 'why')):
            score += 8

        # Long prompts are often complex (>100 characters)
        if len(user_prompt) > 100:
            score += 7

        # Example: "What opportunities exist? What's the strategy? How should we move?"
        # Questions: 3 (+10)
        # Starts with "What": 0
        # Length: >100 (+7)
        # Score so far: 4 + 10 + 7 = 21

        # ─────────────────────────────────────────────────
        # INDICATOR 3: DOMAIN SPECIFICITY (20 points possible)
        # ─────────────────────────────────────────────────

        domain_keywords = {
            'market': 3,
            'business': 3,
            'technical': 2,
            'architecture': 3,
            'system': 2,
            'financial': 2,
            'legal': 2,
            'medical': 2,
            'strategy': 4,
        }

        for domain, points in domain_keywords.items():
            if domain in user_prompt.lower():
                score += points

        # ─────────────────────────────────────────────────
        # INDICATOR 4: CONTEXT INDICATORS (25 points possible)
        # ─────────────────────────────────────────────────

        if user_prompt.lower().count('and') > 2:
            score += 5  # Multiple topics

        if 'for' in user_prompt.lower() or 'to' in user_prompt.lower():
            score += 3  # Purpose-driven

        if any(word in user_prompt.lower() for word in ['specific', 'detailed', 'comprehensive']):
            score += 8  # Wants depth

        # Example continued:
        # Domain: "market" (+3)
        # Score so far: 21 + 3 = 24

        # ─────────────────────────────────────────────────
        # CALCULATE FINAL COMPLEXITY
        # ─────────────────────────────────────────────────

        max_score = 100  # Total possible points

        if score >= 40:
            complexity = 'HIGH'
        elif score >= 20:
            complexity = 'MEDIUM'
        else:
            complexity = 'LOW'

        return {
            'complexity': complexity,
            'score': score,
            'max_score': max_score,
            'reasoning_needed': score >= 20,
            'breakdown': {
                'reasoning_keywords': sum(v for k, v in reasoning_keywords.items() if k in user_prompt.lower()),
                'question_complexity': num_questions,
                'domain_specificity': sum(v for k, v in domain_keywords.items() if k in user_prompt.lower()),
            }
        }

    # Example execution:
    # ───────────────────────────────────────
    # Prompt: "What business opportunities exist in the AI agent market?
    #          I need data-driven insights and strategic recommendations."
    #
    # Detection results:
    # {
    #   'complexity': 'HIGH',
    #   'score': 48,
    #   'reasoning_needed': True,
    #   'breakdown': {
    #     'reasoning_keywords': 15 (opportunity + strategic + recommendations),
    #     'question_complexity': 2,
    #     'domain_specificity': 6 (market + business),
    #   }
    # }
    #
    # Decision: "This needs SOAR reasoning"
```

---

## Part 4: Orchestrator Router - Step 1 (What Generates the Routing Decision)

### The Orchestrator Generation Pipeline

```python
# ORCHESTRATOR_ROUTER_GENERATION
class OrchestratorRouter:
    """Step 1: Pre-hook that generates routing decision"""

    def generate_routing_decision(
        user_prompt: str,
        conversation_history: list,
        knowledge_base: dict
    ) -> dict:
        """
        Generate routing decision. Returns what path to take.
        This is NOT an LLM call. It's heuristic logic.
        """

        print("╔═══════════════════════════════════════════════════╗")
        print("║ ORCHESTRATOR ROUTER - GENERATING DECISION         ║")
        print("╚═══════════════════════════════════════════════════╝\n")

        # ─────────────────────────────────────────────────────────
        # ANALYSIS 1: COMPLEXITY
        # ─────────────────────────────────────────────────────────

        complexity_analyzer = ComplexityDetector()
        complexity_result = complexity_analyzer.detect_complexity(user_prompt)

        print(f"1️⃣  COMPLEXITY ANALYSIS:")
        print(f"    Level: {complexity_result['complexity']}")
        print(f"    Score: {complexity_result['score']}/100")
        print(f"    Reasoning needed: {complexity_result['reasoning_needed']}\n")

        # ─────────────────────────────────────────────────────────
        # ANALYSIS 2: PATTERN MATCHING
        # ─────────────────────────────────────────────────────────

        pattern_matcher = PatternMatcher()
        pattern_result = pattern_matcher.find_similar_pattern(user_prompt, knowledge_base)

        print(f"2️⃣  PATTERN MATCHING:")
        if pattern_result['pattern_found']:
            print(f"    Found: {pattern_result['pattern_id']}")
            print(f"    Similarity: {pattern_result['similarity']:.0%}")
            print(f"    Confidence: {pattern_result['pattern_confidence']:.0%}")
            print(f"    Best operator: {pattern_result['recommended_operators'][0]['operator']}")
        else:
            print(f"    No similar pattern found")
        print()

        # ─────────────────────────────────────────────────────────
        # ANALYSIS 3: CONVERSATION CONTEXT
        # ─────────────────────────────────────────────────────────

        is_multiturn = len(conversation_history) > 2
        previous_context = conversation_history[-1] if conversation_history else None

        print(f"3️⃣  CONVERSATION CONTEXT:")
        print(f"    Multi-turn: {is_multiturn}")
        print(f"    History length: {len(conversation_history)}\n")

        # ─────────────────────────────────────────────────────────
        # ROUTING DECISION LOGIC (NO LLM NEEDED)
        # ─────────────────────────────────────────────────────────

        # This is a decision tree, not an LLM call

        decision = None

        # Decision Rule 1: If simple and known, use FAST path
        if (complexity_result['complexity'] == 'LOW' and
            pattern_result['pattern_found'] and
            pattern_result['pattern_confidence'] > 0.8):

            decision = {
                'path': 'FAST',
                'model': 'mistral-7b-ft',
                'use_soar': False,
                'use_act_r': False,
                'temperature': 0.3,
                'reason': 'Simple task, high-confidence pattern match'
            }

            print(f"4️⃣  ROUTING DECISION: FAST_PATH")
            print(f"    → Simple complexity + high-confidence known pattern")
            print(f"    → Use fine-tuned small LLM only")
            print(f"    → Expected time: 200ms")
            print()

        # Decision Rule 2: If complex reasoning needed, use SOAR
        elif (complexity_result['complexity'] in ['MEDIUM', 'HIGH'] and
              complexity_result['reasoning_needed'] == True):

            decision = {
                'path': 'SOAR',
                'model_reasoning': 'mistral-7b-ft',
                'model_generation': 'claude-opus-4.5',
                'use_soar': True,
                'use_act_r': False,
                'temperature': 0.5,
                'soar_max_iterations': 5,
                'reason': 'Complex reasoning needed'
            }

            # If pattern found, give SOAR hints
            if pattern_result['pattern_found']:
                decision['hints'] = {
                    'recommended_operators': pattern_result['recommended_operators'],
                    'try_first': pattern_result['recommended_operators'][0]['operator']
                }

            print(f"4️⃣  ROUTING DECISION: SOAR_PATH")
            print(f"    → Complex + reasoning needed")
            if pattern_result['pattern_found']:
                print(f"    → Hinting: Try '{decision['hints']['try_first']}' first")
            print(f"    → Expected time: 5-10s")
            print()

        # Decision Rule 3: If multi-turn conversation, use ACT-R
        elif (is_multiturn and
              complexity_result['complexity'] in ['LOW', 'MEDIUM']):

            decision = {
                'path': 'ACT_R',
                'model': 'mistral-7b-ft',
                'use_soar': False,
                'use_act_r': True,
                'temperature': 0.5,
                'reason': 'Multi-turn conversation - use learned procedures'
            }

            print(f"4️⃣  ROUTING DECISION: ACT_R_PATH")
            print(f"    → Multi-turn context detected")
            print(f"    → Use procedural memory + activation")
            print(f"    → Expected time: 3-5s")
            print()

        # Decision Rule 4: Default to moderate path
        else:
            decision = {
                'path': 'MODERATE',
                'model': 'mistral-7b-ft',
                'use_soar': False,
                'use_act_r': False,
                'temperature': 0.5,
                'reason': 'Default balanced approach'
            }

            print(f"4️⃣  ROUTING DECISION: MODERATE_PATH")
            print()

        # ─────────────────────────────────────────────────────────
        # RETURN DECISION
        # ─────────────────────────────────────────────────────────

        decision['metadata'] = {
            'timestamp': datetime.now().isoformat(),
            'analysis': {
                'complexity': complexity_result,
                'pattern': pattern_result,
                'conversation': is_multiturn
            }
        }

        return decision

    # Example execution:
    # ───────────────────────────────────────
    # Prompt: "What business opportunities in AI market?
    #          I need data-driven insights."
    #
    # Output:
    # {
    #   'path': 'SOAR',
    #   'model_reasoning': 'mistral-7b-ft',
    #   'model_generation': 'claude-opus-4.5',
    #   'use_soar': True,
    #   'hints': {
    #     'recommended_operators': [
    #       {'operator': 'market_research_first', 'success_rate': 0.89},
    #       ...
    #     ],
    #     'try_first': 'market_research_first'
    #   },
    #   'reason': 'Complex reasoning needed'
    # }
    #
    # This decision is GENERATED by heuristic logic,
    # NOT by an LLM. It's a decision tree algorithm.
```

---

## Part 5: SOAR Reasoning - Step 2 (Internal Conversation)

### Is SOAR an Internal Conversation Between LLM and Itself?

**Answer: YES, but more precisely—it's a STRUCTURED CONVERSATION where the LLM responds to specific prompts**

```
NOT like:
  LLM talking to itself spontaneously
  (That would be hallucination/confusion)

ACTUALLY like:
  Orchestrator asks specific questions
  → Fine-tuned LLM generates answer
  → Answer fed into next question
  → Result: Structured reasoning conversation
```

### SOAR Cycle with Complete Detail

```python
# SOAR_REASONING_EXECUTION
class SOARReasoning:
    """Step 2: SOAR cycles - internal structured conversation"""

    def execute_soar_cycles(
        user_prompt: str,
        orchestrator_decision: dict,
        knowledge_base: dict
    ):
        """
        SOAR cycles are structured conversations with the LLM
        """

        print("╔═══════════════════════════════════════════════════╗")
        print("║ SOAR REASONING CYCLES                             ║")
        print("╚═══════════════════════════════════════════════════╝\n")

        # Load the fine-tuned model
        ft_llm = load_model(orchestrator_decision['model_reasoning'])
        # This is: Mistral 7B with PEFT fine-tuning

        soar_state = {
            'user_request': user_prompt,
            'cycle': 0,
            'elaboration': None,
            'operators': [],
            'best_operator': None,
            'execution_trace': [],
        }

        # ═════════════════════════════════════════════════════════
        # SOAR CYCLE 1: ELABORATION
        # ═════════════════════════════════════════════════════════
        # QUESTION GENERATOR: Orchestrator asks "What does this require?"
        # LLM RESPONDER: Fine-tuned LLM answers

        print("\n🔄 CYCLE 1: ELABORATION\n")
        print("Question from Orchestrator: What does this problem require?")
        print()

        elaboration_prompt = f"""
You are analyzing a user request. Break it down:

User request: "{user_prompt}"

Answer these questions (be concise):
1. What is the core question being asked?
2. What information would be most helpful?
3. What are potential challenges?
4. What type of approach would work best?

Format your answer as:
CORE_QUESTION: [answer]
INFO_NEEDED: [answer]
CHALLENGES: [answer]
APPROACH_TYPE: [answer]
        """

        # THIS IS AN LLM CALL
        # The Orchestrator asks a question
        # The fine-tuned LLM answers it

        elaboration_response = ft_llm.generate(
            prompt=elaboration_prompt,
            temperature=0.3,  # Deterministic
            max_tokens=300
        )

        print(f"LLM Response:\n{elaboration_response}\n")

        # Parse the response
        soar_state['elaboration'] = {
            'raw': elaboration_response,
            'parsed': parse_elaboration(elaboration_response)
        }

        soar_state['cycle'] = 1
        soar_state['execution_trace'].append({
            'cycle': 1,
            'phase': 'ELABORATION',
            'prompt_sent': elaboration_prompt[:100] + "...",
            'response_received': elaboration_response[:100] + "...",
            'tokens_used': count_tokens(elaboration_response)
        })

        # ═════════════════════════════════════════════════════════
        # SOAR CYCLE 2: OPERATOR PROPOSAL
        # ═════════════════════════════════════════════════════════
        # QUESTION GENERATOR: Orchestrator asks "What approaches?"
        # LLM RESPONDER: Fine-tuned LLM proposes operators

        print("\n🔄 CYCLE 2: OPERATOR PROPOSAL\n")
        print("Question from Orchestrator: What are candidate operators?")
        print()

        # Check if we have hints from orchestrator
        hints_text = ""
        if 'hints' in orchestrator_decision:
            hints_text = f"""
Note: Based on similar past problems, these operators worked well:
{format_operators(orchestrator_decision['hints']['recommended_operators'])}
Consider these, but feel free to propose others.
            """

        operator_proposal_prompt = f"""
Based on the problem elaboration:
{soar_state['elaboration']['raw']}

Propose 3-5 different OPERATORS (approaches) to solve this:

For each operator:
OPERATOR_NAME: [Clear name]
DESCRIPTION: [How it works]
STEPS: [What are the steps]
DATA_NEEDED: [What info required]
CONFIDENCE: [How confident are you this works? 0-10]

{hints_text}
        """

        operator_response = ft_llm.generate(
            prompt=operator_proposal_prompt,
            temperature=0.4,  # Slightly creative
            max_tokens=600
        )

        print(f"LLM Response:\n{operator_response}\n")

        # Parse operators
        operators = parse_operators(operator_response)

        # Look up utilities from knowledge base
        for op in operators:
            historical_utility = lookup_operator_utility(
                op['name'],
                knowledge_base
            )
            op['utility'] = historical_utility if historical_utility else 0.5
            op['utility_source'] = 'learned' if historical_utility else 'default'

        print(f"Operators with utilities:")
        for op in operators:
            print(f"  - {op['name']}: utility={op['utility']:.3f} ({op['utility_source']})")
        print()

        soar_state['operators'] = operators
        soar_state['cycle'] = 2

        # ═════════════════════════════════════════════════════════
        # SOAR CYCLE 3: EVALUATION
        # ═════════════════════════════════════════════════════════
        # QUESTION GENERATOR: Orchestrator asks "Which is best?"
        # LLM RESPONDER: Fine-tuned LLM evaluates operators

        print("\n🔄 CYCLE 3: EVALUATION\n")
        print("Question from Orchestrator: Which operator fits THIS context?")
        print()

        # Build context info
        context_info = f"""
Current context:
- User expects: data-driven insights
- Time available: No constraint
- Data available: RAG search available
- Complexity: High (user wants strategy)
        """

        evaluation_prompt = f"""
Given these candidate operators:
{format_operators_for_eval(operators)}

Context:
{context_info}

Evaluate each operator for THIS context:
For each operator:
OPERATOR: [name]
SCORE: [1-10, how good is it for this context?]
REASONING: [Why this score?]

Then select the BEST operator and explain why.
        """

        evaluation_response = ft_llm.generate(
            prompt=evaluation_prompt,
            temperature=0.3,  # Deterministic evaluation
            max_tokens=400
        )

        print(f"LLM Response:\n{evaluation_response}\n")

        # Parse evaluation and select best
        scores = parse_evaluation(evaluation_response)
        best_operator_name = max(scores.keys(), key=lambda x: scores[x])
        best_operator = next(op for op in operators if op['name'] == best_operator_name)

        print(f"Selected operator: {best_operator['name']} (score: {scores[best_operator_name]})\n")

        soar_state['best_operator'] = best_operator
        soar_state['evaluation'] = evaluation_response
        soar_state['cycle'] = 3

        # ═════════════════════════════════════════════════════════
        # SOAR CYCLE 4: EXECUTION
        # ═════════════════════════════════════════════════════════
        # EXECUTION: Actually execute the chosen operator
        # Uses: RAG (if needed) + LLM generation

        print("\n🔄 CYCLE 4: EXECUTION\n")
        print(f"Executing operator: {best_operator['name']}\n")

        # Execute operator (detailed in next section)
        execution_response = execute_operator(
            operator=best_operator,
            user_prompt=user_prompt,
            soar_state=soar_state,
            ft_llm=ft_llm,
            big_llm=orchestrator_decision.get('model_generation')
        )

        soar_state['execution_response'] = execution_response
        soar_state['cycle'] = 4

        # ═════════════════════════════════════════════════════════
        # SOAR CYCLE 5: LEARNING
        # ═════════════════════════════════════════════════════════
        # Capture outcome for TAO learning

        print("\n🔄 CYCLE 5: LEARNING\n")
        print("Capturing outcome for future improvement...\n")

        outcome = {
            'user_prompt': user_prompt,
            'operator_chosen': best_operator['name'],
            'execution_response': execution_response,
            'soar_cycles_count': 4,
            'soar_trace': soar_state['execution_trace'],
            'timestamp': datetime.now().isoformat(),
            'status': 'AWAITING_USER_FEEDBACK'
        }

        print(f"Outcome captured: {outcome['status']}\n")

        return {
            'response': execution_response,
            'soar_state': soar_state,
            'outcome_for_learning': outcome,
            'total_cycles': 4
        }

    # ═════════════════════════════════════════════════════════════
    # WHAT TOKENS ARE USED?
    # ═════════════════════════════════════════════════════════════
    #
    # ELABORATION CYCLE:
    #   Input tokens:  ~150 (prompt asking for elaboration)
    #   Output tokens: ~200 (LLM response: core question, info needed, etc.)
    #   Total: ~350 tokens
    #
    # OPERATOR PROPOSAL CYCLE:
    #   Input tokens:  ~400 (elaboration + proposal prompt)
    #   Output tokens: ~500 (3-5 operators described)
    #   Total: ~900 tokens
    #
    # EVALUATION CYCLE:
    #   Input tokens:  ~500 (operators + evaluation prompt)
    #   Output tokens: ~300 (scores and reasoning)
    #   Total: ~800 tokens
    #
    # EXECUTION CYCLE:
    #   Depends on operator, but typically:
    #   Input tokens:  ~300-500
    #   Output tokens: ~800-1500
    #   Total: ~1100-2000 tokens
    #
    # TOTAL SOAR CYCLES: ~3050-4450 tokens
    #
    # Cost at $0.0005 per 1000 tokens:
    # 4000 tokens * $0.0005 = $0.002 per SOAR run (cheap!)
    # Plus big LLM generation: ~$0.01
    # Total: ~$0.012 per complex prompt
```

---

## Part 6: Storage and Recall (JSON Tree Structure)

### When Pattern is Recalled and Found

```python
# PATTERN_RECALL_EXECUTION
def recall_and_execute_successful_pattern(
    user_prompt: str,
    pattern_match: dict,
    knowledge_base: dict
):
    """
    When orchestrator finds a successful pattern match,
    what happens?
    """

    print("\n📋 SUCCESSFUL PATTERN FOUND")
    print(f"Pattern: {pattern_match['pattern_id']}")
    print(f"Similarity: {pattern_match['similarity']:.0%}")
    print(f"Recommended operator: {pattern_match['recommended_operators'][0]['operator']}\n")

    # Get the best operator for this pattern
    best_operator_for_pattern = pattern_match['recommended_operators'][0]
    # This is: {'operator': 'market_research_first', 'success_rate': 0.89}

    # Look up the full operator definition
    operator_details = lookup_operator_in_soar_history(
        best_operator_for_pattern['operator'],
        knowledge_base
    )
    # This returns the full operator from JSON (steps, etc.)

    # Option 1: Skip SOAR cycles, use learned operator directly
    # ──────────────────────────────────────────────────────

    if pattern_match['similarity'] > 0.8:
        print("🚀 Pattern match confidence HIGH (>80%)")
        print("→ Skip SOAR cycles, use learned operator directly\n")

        # Execute the learned operator (operator_details has the steps)
        response = execute_learned_operator_directly(
            operator=operator_details,
            user_prompt=user_prompt
        )

        # This saves 5-10 seconds! Direct execution.
        # Much faster than full SOAR cycles.

        return {
            'response': response,
            'path': 'LEARNED_OPERATOR_DIRECT',
            'operator_used': operator_details['name'],
            'time_saved': '5-10 seconds',
            'outcome': {
                'used_learned_path': True,
                'operator': operator_details['name']
            }
        }

    # Option 2: Use as hints for SOAR cycles
    # ──────────────────────────────────────

    elif pattern_match['similarity'] > 0.6:
        print("🎯 Pattern match confidence MEDIUM (60-80%)")
        print("→ Use pattern as hints for SOAR, but run full cycles\n")

        # Run full SOAR cycles, but with hints
        soar_result = execute_soar_cycles(
            user_prompt=user_prompt,
            orchestrator_decision={
                'hints': {
                    'try_first': operator_details['name'],
                    'alternative_operators': pattern_match['recommended_operators']
                }
            }
        )

        return soar_result
```

### JSON Storage Example: What Gets Saved

```json
{
  "execution_trace": {
    "execution_id": "exec_12345",
    "input": "What business opportunities in AI agent market?",
    "orchestrator_decision": {
      "path": "SOAR",
      "complexity": "HIGH",
      "pattern_found": true,
      "hints": {
        "try_first": "market_research_first",
        "success_rate_of_hint": 0.89
      }
    },
    "soar_execution": {
      "cycle_1_elaboration": {
        "question_asked": "What does this problem require?",
        "llm_response": "Core question: Identify AI market opportunities...",
        "tokens_used": 200
      },
      "cycle_2_operators": {
        "question_asked": "What approaches could work?",
        "llm_response": "Operator A: Market Research First... Operator B: ...",
        "operators_proposed": 4,
        "tokens_used": 500
      },
      "cycle_3_evaluation": {
        "question_asked": "Which operator is best?",
        "llm_response": "Market Research First is best (9.5/10)...",
        "selected_operator": "market_research_first",
        "tokens_used": 300
      },
      "cycle_4_execution": {
        "operator_executed": "market_research_first",
        "rag_search": "market data AI 2024 2025",
        "rag_results": 5,
        "llm_generation": "BUSINESS OPPORTUNITIES: 1. Privacy-first... ",
        "tokens_used": 1500
      }
    },
    "final_response": "BUSINESS OPPORTUNITIES: ...",
    "outcome": {
      "user_rating": 9,
      "feedback": "Used for board presentation",
      "success_score": 0.95
    },
    "timestamp": "2025-12-06T14:32:00Z",
    "total_tokens": 2500,
    "total_cost": "$0.012",
    "execution_time_ms": 8500
  }
}
```

---

## Part 7: ACT-R Procedural Matching (JSON Storage)

### ACT-R: Match, Select, Act, Learn

```python
# ACT_R_EXECUTION
class ACTRExecution:
    """
    ACT-R is simpler than SOAR - more like a lookup table with learning
    """

    def execute_act_r(
        user_prompt: str,
        conversation_history: list,
        knowledge_base: dict
    ):
        """
        ACT-R: Pattern matching → Production selection → Action → Learn
        """

        print("╔═══════════════════════════════════════════════════╗")
        print("║ ACT-R PROCEDURAL LEARNING                         ║")
        print("╚═══════════════════════════════════════════════════╝\n")

        # ─────────────────────────────────────────────────────────
        # PHASE 1: PATTERN MATCHING (Search declarative memory)
        # ─────────────────────────────────────────────────────────

        print("1️⃣ PHASE 1: PATTERN MATCHING\n")

        # Search declarative memory for similar past interactions
        # Declarative memory is the JSON list of past successful executions

        similar_memories = search_declarative_memory(
            pattern=user_prompt,
            threshold=0.7,
            memory_list=knowledge_base['act_r_history']['declarative_memory']
        )
        # Returns: List of past interactions that are 70%+ similar

        print(f"Found {len(similar_memories)} similar past interactions\n")

        for i, memory in enumerate(similar_memories[:3]):
            print(f"Memory {i+1}: '{memory['input'][:50]}...'")
            print(f"  → Used procedure: {memory['procedure_used']}")
            print(f"  → Success: {memory['success_score']:.0%}")
            print(f"  → Accessibility: {memory['accessibility']['retrieval_strength']:.2f}\n")

        # ─────────────────────────────────────────────────────────
        # PHASE 2: PRODUCTION SELECTION (Choose procedure)
        # ─────────────────────────────────────────────────────────

        print("2️⃣ PHASE 2: PRODUCTION SELECTION\n")

        # If we have similar memories, look up their procedures
        if similar_memories:
            # Get procedures used in similar memories
            procedure_ids = [m['procedure_used'] for m in similar_memories]
            procedures = [
                knowledge_base['act_r_history']['procedures'][pid]
                for pid in procedure_ids
                if pid in knowledge_base['act_r_history']['procedures']
            ]

            # Sort by activation (recency + frequency + success)
            procedures.sort(
                key=lambda x: x['activation'],
                reverse=True
            )

            selected_procedure = procedures[0]
            print(f"Selected procedure: {selected_procedure['name']}")
            print(f"  → Activation: {selected_procedure['activation']:.2f}")
            print(f"  → Use count: {selected_procedure['use_count']}")
            print(f"  → Success rate: {selected_procedure['success_rate']:.0%}\n")

        else:
            # No similar memory, generate new procedure
            print("No similar memory found. Generating new procedure...\n")

            procedure_generation_prompt = f"""
Task: {user_prompt}

Design a step-by-step PROCEDURE to solve this:
Step 1: [First action]
Step 2: [Second action]
Step 3: [Third action]
...

This procedure will be learned and reused if successful.
            """

            procedure_text = ft_llm.generate(
                prompt=procedure_generation_prompt,
                temperature=0.4,
                max_tokens=300
            )

            selected_procedure = {
                'name': f"Generated_{hash(user_prompt)}",
                'steps': parse_procedure_steps(procedure_text),
                'activation': 0.5,
                'use_count': 1,
                'success_rate': 0.0  # Will be updated
            }

            print(f"Generated procedure:\n{procedure_text}\n")

        # ─────────────────────────────────────────────────────────
        # PHASE 3: ACTION (Execute procedure)
        # ─────────────────────────────────────────────────────────

        print("3️⃣ PHASE 3: ACTION\n")
        print(f"Executing procedure: {selected_procedure['name']}\n")

        # Execute each step of the procedure
        response = execute_procedure_steps(
            procedure=selected_procedure,
            user_prompt=user_prompt,
            context=conversation_history
        )

        print(f"Response: {response[:100]}...\n")

        # ─────────────────────────────────────────────────────────
        # PHASE 4: LEARNING (Update activation)
        # ─────────────────────────────────────────────────────────

        print("4️⃣ PHASE 4: LEARNING\n")

        # Get feedback signal (will be updated when user responds)
        # For now, assume no feedback yet
        feedback_signal = get_feedback_signal(user_prompt, response)
        # Returns: 0.5 (no signal yet)

        # Update procedure activation
        old_activation = selected_procedure['activation']

        # Activation decay formula:
        # new_activation = 0.95 * base_activation + 0.05 * recent_success
        recency_boost = calculate_recency_boost(selected_procedure['last_used'])
        frequency_boost = calculate_frequency_boost(selected_procedure['use_count'])
        success_component = selected_procedure['success_rate'] * 0.5 + feedback_signal * 0.5

        new_activation = (
            0.4 * recency_boost +
            0.3 * frequency_boost +
            0.3 * success_component
        )

        print(f"Procedure activation updated:")
        print(f"  Old: {old_activation:.3f}")
        print(f"  New: {new_activation:.3f}")
        print(f"  Change: {new_activation - old_activation:+.3f}\n")

        selected_procedure['activation'] = new_activation
        selected_procedure['last_used'] = datetime.now().isoformat()

        # Store in declarative memory for future retrieval
        memory_entry = {
            'input': user_prompt,
            'output': response,
            'procedure_used': selected_procedure['name'],
            'success_score': feedback_signal,  # Will be updated
            'accessibility': {
                'retrieval_strength': new_activation,
                'decay_rate': 0.02  # Slight decay over time
            }
        }

        return {
            'response': response,
            'procedure_used': selected_procedure['name'],
            'activation': new_activation,
            'memory_stored': True,
            'execution_time': '3-5s'
        }
```

---

## Part 8: Summary - The Script Tree Execution Model

### Is This a Pre-Hook Script Tree?

**Answer: YES, exactly. Both SOAR and ACT-R are decision trees executed as scripts**

```
SOAR = DECISION TREE (5 branches)
├─ Branch 1: Ask question "What does this require?"
│   └─ LLM generates answer
│   └─ Store elaboration
├─ Branch 2: Ask question "What approaches exist?"
│   └─ LLM generates options
│   └─ Lookup utilities from JSON
├─ Branch 3: Ask question "Which is best?"
│   └─ LLM evaluates
│   └─ Select highest-scored
├─ Branch 4: Execute chosen operator
│   └─ May use RAG + LLM
│   └─ Generate response
└─ Branch 5: Learn
    └─ Capture outcome to JSON

ACT-R = SIMPLER DECISION TREE (4 branches)
├─ Branch 1: Search JSON for similar memories
│   └─ Match by keyword/semantic similarity
├─ Branch 2: Select highest-activation procedure
│   └─ Lookup from JSON procedures
├─ Branch 3: Execute procedure steps
│   └─ Run LLM for each step
└─ Branch 4: Update activation
    └─ Write back to JSON
```

### How Requirements Are Filled

```
SOAR Requirements:
├─ Elaborate: Filled by LLM response to "what does this require?"
├─ Propose: Filled by LLM response to "what operators?"
├─ Evaluate: Filled by LLM response to "which operator best?"
├─ Execute: Filled by running chosen operator (LLM + RAG)
└─ Learn: Filled by storing outcome in JSON

ACT-R Requirements:
├─ Match: Filled by JSON search (keyword/semantic)
├─ Select: Filled by activation lookup from JSON
├─ Act: Filled by running procedure (LLM for each step)
└─ Learn: Filled by updating JSON activation values
```

---

## Part 9: Complete Flow Summary

```
USER SENDS PROMPT
    ↓
ORCHESTRATOR (Pre-hook script)
├─ Detect complexity (keyword+heuristics)
├─ Search JSON for similar patterns
├─ Decide: FAST vs SOAR vs ACT-R
└─ Return routing decision (NO LLM)
    ↓
    ├─ IF FAST:
    │   └─ LLM generates directly
    │
    ├─ IF SOAR:
    │   └─ Run 5-cycle script tree
    │       └─ Cycle 1-5: Ask questions, get LLM answers, lookup utilities, execute
    │
    └─ IF ACT-R:
        └─ Run 4-step script tree
            └─ Match, Select, Act, Learn
    ↓
RESPONSE TO USER (after 200ms - 15s)
    ↓
TAO LEARNING (Async)
├─ Collect outcomes
├─ Score success rates
├─ Update JSON utilities/activations
└─ Next similar prompt will be smarter
```

---

## Part 10: Key Insights

### 1. Where Previous Runs Are Stored
✅ **JSON files in knowledge_base/soar_history/** and **act_r_history/**

### 2. Pattern Matching for Similar Requests
✅ **Keyword matching + semantic similarity** (75%+ match triggers reuse)
✅ **Successful patterns get higher confidence scores**
✅ **Recommendation: If >80% match, skip SOAR, use learned operator directly**

### 3. What Decides Complexity
✅ **Keyword scoring algorithm** (not ML, just heuristics)
✅ **Triggers SOAR if score ≥ 40/100**
✅ **"analyze", "why", "strategy" = high score**

### 4. Orchestrator Router Generation
✅ **Generated by decision tree logic** (not LLM)
✅ **No special LLM call needed**
✅ **Just heuristic matching + JSON lookup**

### 5. SOAR Reasoning
✅ **IS an internal conversation between Orchestrator (question-asker) and fine-tuned LLM (responder)**
✅ **5 cycles, each with a specific question**
✅ **Each cycle uses ~300-500 tokens**
✅ **Total: ~3000-4000 tokens for SOAR (cheap)**

### 6. Token Usage
✅ **Elaboration cycle: ~350 tokens**
✅ **Proposal cycle: ~900 tokens**
✅ **Evaluation cycle: ~800 tokens**
✅ **Execution cycle: ~1500 tokens**
✅ **Total: ~3550 tokens per SOAR run**

### 7. Storage Model
✅ **Each execution stored in JSON**
✅ **Contains: input, operators, scores, response, outcome**
✅ **Used for pattern matching in future**

### 8. Recall and Reuse
✅ **Successful patterns with >80% confidence: Skip SOAR, execute directly**
✅ **Patterns with 60-80% confidence: Use as hints for SOAR**
✅ **Saves 5-10 seconds when high-confidence match found**

---

**Status**: Complete implementation detail documentation
**Next**: Create implementation guide with actual code
