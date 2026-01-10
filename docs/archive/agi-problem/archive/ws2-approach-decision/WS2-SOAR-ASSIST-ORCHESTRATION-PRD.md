# WS2: SOAR-Assist + Orchestrator + Self-Organization PRD
## Complete Architecture for Emergent Reasoning with Dynamic Agent Orchestration

**Date**: December 7, 2025
**Status**: Comprehensive Production Design Document
**Purpose**: Definitive specification for WS2 implementation with integrated SOAR-Assist, dynamic routing, and unified learning

---

## Executive Summary

### The Problem We're Solving

All existing AI systems operate at the **token prediction layer**. They hit architectural ceilings:
- 25-30% accuracy ceiling on complex reasoning
- No genuine learning from experience
- No structural problem decomposition
- No dynamic agent coordination

### Our Solution: Three-Layer Architecture

```
Layer 1: SOAR-Assist (Problem Decomposition)
├─ Purpose: Understand the problem structure
├─ Question: "What are the subgoals?"
├─ Output: Explicit decomposition + routing requirements
└─ Mechanism: SOAR reasoning engine (3-5 cycles)

Layer 2: Orchestrator (Agent Routing)
├─ Purpose: Match subgoals to specialized agents
├─ Question: "Which agent is best for this subgoal?"
├─ Output: Agent assignments + execution plan
└─ Mechanism: Capability registry matching + cost optimization

Layer 3: Self-Organization (Dynamic Coordination)
├─ Purpose: Agents adapt roles and team composition
├─ Question: "How should agents work together?"
├─ Output: Optimized team + coordination protocol
└─ Mechanism: Agent negotiation + capacity management

Plus: ACT-R Learning Layer (Across all)
├─ Purpose: Learn from every execution
├─ Question: "What worked? What didn't?"
├─ Output: Updated utilities + activation scores
└─ Mechanism: Unified learning tracking
```

### Key Insight: Routing is Implicit in Decomposition

When SOAR-Assist says "Subgoal A needs market_research capability", routing becomes trivial: find the agent with market_research capability.

This solves the dynamic routing problem **without explicit routing logic**.

---

## Table of Contents

1. [Core Architecture](#core-architecture)
2. [SOAR-Assist Function Specification](#soar-assist-function-specification)
3. [Unified Memory Architecture (from Previous Sessions)](#unified-memory-architecture)
4. [Assessment & Complexity Classification](#assessment--complexity-classification)
5. [Orchestrator Function](#orchestrator-function)
6. [Subagent Capability Registry](#subagent-capability-registry)
7. [Self-Organization Function](#self-organization-function)
8. [Three Routing Flows: Simple/Complex/Medium](#three-routing-flows)
9. [Synthesis Strategies](#synthesis-strategies)
10. [Unified Learning: SOAR+ACT-R](#unified-learning-soaractr)
11. [Learning Metrics & Tracking](#learning-metrics--tracking)
12. [Complete Pseudocode Implementation](#complete-pseudocode-implementation)
13. [WHAT vs HOW Diagram & Learning Loop](#what-vs-how-diagram--learning-loop)
14. [Integration with Subagent Invocation](#integration-with-subagent-invocation)
15. [Agent Registry Tracking](#agent-registry-tracking)
16. [Implementation Checklist](#implementation-checklist)

---

## Core Architecture

### The Complete System Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     USER PROMPT INPUT                        │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│         ASSESSMENT LAYER (Inline Function - 2-3s)           │
│  ├─ Keyword extraction                                      │
│  ├─ Structural analysis                                     │
│  └─ Complexity classification: SIMPLE|MEDIUM|COMPLEX        │
└────────────────────────┬────────────────────────────────────┘
                         ↓
        ┌─────────┴─────────┬─────────┬──────────┐
        ↓                   ↓         ↓          ↓
    [SIMPLE]           [MEDIUM]  [COMPLEX]  [COMPARISON]
        ↓                   ↓         ↓          ↓
     Direct LLM      Comparison   SOAR-Assist  Both Paths
        ↓                ↓           ↓          ↓
        └────┬───────────┴─────┬─────┴──────┬──┘
             ↓                 ↓            ↓
        ┌──────────────────────────────────────────────┐
        │    SOAR-ASSIST (if needed - 3-5s)           │
        │  ├─ Elaboration: Query ACT-R facts          │
        │  ├─ Proposal: Generate subgoals             │
        │  ├─ Evaluation: Score importance            │
        │  └─ Decision: Create decomposition          │
        └──────────────────┬───────────────────────────┘
                           ↓
        ┌──────────────────────────────────────────────┐
        │   ORCHESTRATOR (if needed - 1s)             │
        │  ├─ Query capability registry               │
        │  ├─ Match subgoals to agents                │
        │  └─ Create routing + execution plan         │
        └──────────────────┬───────────────────────────┘
                           ↓
        ┌──────────────────────────────────────────────┐
        │  SELF-ORGANIZATION (optional - <1s)         │
        │  ├─ Validate team composition               │
        │  ├─ Check parallelization                   │
        │  └─ Confirm optimization                    │
        └──────────────────┬───────────────────────────┘
                           ↓
        ┌──────────────────────────────────────────────┐
        │   INVOKE SUBAGENTS (Parallel - 30-60s)      │
        │  ├─ Subagent A: Execute subgoal 1          │
        │  ├─ Subagent B: Execute subgoal 2          │
        │  └─ Subagent C: Execute subgoal 3          │
        └──────────────────┬───────────────────────────┘
                           ↓
        ┌──────────────────────────────────────────────┐
        │   SYNTHESIS (if needed - 5-15s)             │
        │  ├─ Level 1: Aggregation (main agent)       │
        │  ├─ Level 2: Integration (SOAR-Assist)      │
        │  └─ Level 3: Strategy (specialized agent)   │
        └──────────────────┬───────────────────────────┘
                           ↓
        ┌──────────────────────────────────────────────┐
        │   RETURN RESPONSE TO USER                    │
        └──────────────────┬───────────────────────────┘
                           ↓
        ┌──────────────────────────────────────────────┐
        │   ACT-R LEARNING (Async - 1s)               │
        │  ├─ Update SOAR-Assist utility              │
        │  ├─ Update orchestrator success             │
        │  ├─ Update agent activations                │
        │  ├─ Track resources used                    │
        │  ├─ Log execution metrics                   │
        │  └─ Update capability registry stats        │
        └──────────────────────────────────────────────┘
```

### System Responsibilities

```
Function          | Responsibility              | Execution | Frequency
─────────────────────────────────────────────────────────────────────────
Assessment        | Classify complexity         | 2-3s      | 100% of queries
SOAR-Assist       | Decompose complex problems  | 3-5s      | 10-25% of queries
Orchestrator      | Route to agents             | 1s        | 25-40% of queries
Self-Organization | Optimize coordination       | <1s       | Optional (5-10%)
Subagents         | Execute subgoals            | 30-60s    | Per subgoal
Synthesis         | Combine results             | 5-15s     | As needed
ACT-R Learning    | Update memory + utilities   | 1s        | 100% of queries
```

---

## SOAR-Assist Function Specification

### What is SOAR-Assist?

**SOAR-Assist is NOT pure SOAR:**
- Pure SOAR: Deep reasoning engine (50+ decision cycles possible)
- SOAR-Assist: Lightweight decomposition function (3-5 cycles)

**SOAR-Assist IS:**
- Problem decomposer (not problem solver)
- Strategy generator (not solution provider)
- Routing requirement specifier (not agent selector)

### When SOAR-Assist Runs

```
Assessment determines:
├─ SIMPLE: No SOAR-Assist (direct LLM + orchestrator)
├─ MEDIUM: Optional SOAR-Assist (comparison learning)
└─ COMPLEX: Always SOAR-Assist (decomposition required)

Decision:
├─ Keyword complexity score > 0.5: Use SOAR-Assist
├─ Score between -0.3 and 0.5: Consider comparison learning
└─ Score < -0.3: Skip SOAR-Assist (simple resolution)
```

### SOAR-Assist Decision Cycle

#### Phase 1: Elaboration (Query Facts)

```python
def elaboration_phase(prompt, current_state):
    """
    Query ACT-R for relevant facts
    Understand what we already know
    """

    # Parse prompt for context
    query_concepts = extract_concepts(prompt)

    # Query unified memory
    relevant_facts = actr_memory.retrieve(
        query=query_concepts,
        top_n=10,
        domain=extract_domain(prompt)
    )

    # Update working memory
    current_state['known_facts'] = relevant_facts
    current_state['known_topics'] = [f['domain'] for f in relevant_facts]

    return current_state
```

**Example:**
```
Prompt: "What opportunities exist in AI agent market?"

Elaboration queries:
├─ "AI market facts" → Activation retrieval
├─ "competitor data" → Activation retrieval
├─ "enterprise adoption" → Activation retrieval

Known facts populated:
├─ "30+ companies in space" (activation: 0.87)
├─ "50% YoY growth" (activation: 0.92)
├─ "Enterprise adoption lagging" (activation: 0.88)
```

#### Phase 2: Proposal (Generate Subgoals)

```python
def proposal_phase(current_state):
    """
    Generate all possible subgoals
    These become candidates for operators
    """

    proposed_subgoals = []

    # For each unknown needed to answer prompt
    for unknown_fact in identify_unknown_facts(current_state['prompt']):
        subgoal = {
            "id": f"sg_{generate_id()}",
            "goal": unknown_fact['description'],
            "domain": classify_domain(unknown_fact),
            "type": classify_type(unknown_fact),
            "priority": estimate_importance(unknown_fact, current_state['goal']),
            "why_needed": f"Needed to answer: {current_state['goal']}"
        }
        proposed_subgoals.append(subgoal)

    current_state['proposed_subgoals'] = proposed_subgoals
    return current_state
```

**Example:**
```
Prompt: "What opportunities exist in AI agent market?"

Proposed subgoals:
├─ sg1: Understand competitive landscape
│  ├─ domain: "market_research"
│  ├─ type: "competitive_analysis"
│  └─ priority: 0.9 (critical foundation)
├─ sg2: Identify market trends
│  ├─ domain: "market_research"
│  ├─ type: "trend_analysis"
│  └─ priority: 0.85 (shows direction)
├─ sg3: Analyze adoption gaps
│  ├─ domain: "market_research"
│  ├─ type: "gap_analysis"
│  └─ priority: 0.8 (identifies opportunities)
└─ sg4: Synthesize opportunities
   ├─ domain: "strategic_reasoning"
   ├─ type: "synthesis"
   └─ priority: 1.0 (critical final step)
```

#### Phase 3: Evaluation (Score Importance)

```python
def evaluation_phase(current_state):
    """
    Score each subgoal:
    - Importance to solving main goal
    - Information gap (how much unknown)
    - Effort required vs information gained
    """

    scored_subgoals = []

    for subgoal in current_state['proposed_subgoals']:
        # Score components
        importance = evaluate_importance_to_goal(
            subgoal,
            current_state['goal']
        )

        information_gap = evaluate_information_gap(
            subgoal,
            current_state['known_facts']
        )

        effort_ratio = importance / (estimate_effort(subgoal) + 0.1)

        # Combined score
        score = (
            importance * 0.4 +
            information_gap * 0.35 +
            effort_ratio * 0.25
        )

        scored_subgoals.append((subgoal, score))

    # Sort by score
    scored_subgoals.sort(key=lambda x: x[1], reverse=True)
    current_state['scored_subgoals'] = scored_subgoals

    return current_state
```

**Example Scores:**
```
sg4 (synthesize): 0.95 ← HIGHEST (critical, depends on others)
sg1 (competitive): 0.92 ← HIGH (foundation for understanding)
sg2 (trends): 0.88 ← HIGH (shows direction)
sg3 (gaps): 0.82 ← MEDIUM (identifies opportunities)
```

#### Phase 4: Decision (Create Decomposition)

```python
def decision_phase(current_state):
    """
    Decide execution order and dependencies
    Output the final decomposition
    """

    # Determine execution order
    execution_order = determine_order(
        scored_subgoals=current_state['scored_subgoals'],
        dependencies=identify_dependencies(current_state['scored_subgoals'])
    )

    # Identify parallelizable tasks
    parallelizable = identify_parallel_groups(execution_order)

    # Create decomposition output
    decomposition = {
        "problem_id": generate_id(),
        "original_prompt": current_state['prompt'],
        "timestamp": now(),

        "subgoals": [sg for sg, _ in current_state['scored_subgoals']],

        "execution_strategy": {
            "sequential": execution_order,
            "parallelizable_groups": parallelizable,
            "dependencies": identify_dependencies(current_state['scored_subgoals']),
            "critical_path": identify_critical_path(execution_order)
        },

        "routing_requirements": {
            "sg1": {"domain": "market_research", "type": "competitive_analysis"},
            "sg2": {"domain": "market_research", "type": "trend_analysis"},
            "sg3": {"domain": "market_research", "type": "gap_analysis"},
            "sg4": {"domain": "strategic_reasoning", "type": "synthesis"}
        },

        "soar_metadata": {
            "cycles_used": 4,
            "reasoning_time_s": 4.2,
            "known_facts_used": len(current_state['known_facts']),
            "confidence": 0.88
        }
    }

    return decomposition
```

**Example Decomposition Output:**
```json
{
  "problem_id": "prob-2025-12-07-001",
  "subgoals": [
    {
      "id": "sg1",
      "goal": "competitive_analysis",
      "domain": "market_research",
      "priority": 0.92
    },
    {
      "id": "sg2",
      "goal": "trend_analysis",
      "domain": "market_research",
      "priority": 0.88
    },
    {
      "id": "sg3",
      "goal": "gap_analysis",
      "domain": "market_research",
      "priority": 0.82
    },
    {
      "id": "sg4",
      "goal": "synthesize_opportunities",
      "domain": "strategic_reasoning",
      "priority": 0.95
    }
  ],
  "execution_strategy": {
    "parallelizable_groups": [["sg1", "sg2", "sg3"]],
    "then_sequential": ["sg4"],
    "critical_path": ["sg1 or sg2 or sg3", "→", "sg4"]
  },
  "soar_metadata": {
    "cycles_used": 4,
    "reasoning_time_s": 4.2,
    "confidence": 0.88
  }
}
```

### SOAR-Assist Boundaries

**SOAR-Assist DOES:**
- ✅ Decompose problems into explicit subgoals
- ✅ Identify unknown facts that need resolution
- ✅ Prioritize subgoals by importance
- ✅ Create execution order and dependencies
- ✅ Specify routing requirements (domain + type)
- ✅ Return structured decomposition

**SOAR-Assist DOES NOT:**
- ❌ Select agents (that's Orchestrator's job)
- ❌ Monitor subagent execution
- ❌ Verify subagent results
- ❌ Handle failures or retries
- ❌ Synthesize results (synthesis is separate layer)
- ❌ Make routing decisions

---

## Unified Memory Architecture

### Memory Store Structure (JSON Schema)

Complete from previous sessions - see **WS2-UNIFIED-MEMORY-ARCHITECTURE.md** for full details.

**Quick Reference:**

```json
{
  "metadata": {
    "version": "1.0",
    "system": "SOAR+ACT-R Unified",
    "created": "2025-12-07",
    "last_updated": "2025-12-07T14:35:00Z"
  },

  "facts": {
    "fact_001": {
      "id": "fact_001",
      "type": "fact",
      "content": "AI agent market growing 50% YoY",
      "domain": "market",
      "tags": ["market", "growth", "ai_agents"],
      "actr_metadata": {
        "activation": 0.92,
        "frequency": 156,
        "recency": "2025-12-07T14:35:00Z"
      }
    }
  },

  "operators": {
    "op_001": {
      "id": "op_001",
      "type": "operator",
      "name": "Competitive Analysis",
      "domain": "market_research",
      "preconditions": ["market_context"],
      "effects": ["competitive_landscape_known"],
      "learning_metadata": {
        "soar_utility": 0.82,
        "soar_uses": 42,
        "actr_activation": 0.88
      }
    }
  },

  "rules": {
    "rule_001": {
      "id": "rule_001",
      "type": "learned_rule",
      "condition": "prompt matches [market, analysis, opportunities]",
      "action": "decompose_into [competitive, trends, gaps, synthesis]",
      "soar_utility": 0.85,
      "actr_activation": 0.78
    }
  }
}
```

### ACT-R Retrieval Algorithm (Quick Summary)

```
Activation = Base_Level + Spreading + Context_Boosts - Time_Decay

Base_Level = ln(Σ(t_i^-0.5))  ← Frequency + Recency

Spreading = Σ(source_activation × association_strength)  ← Related concepts

Context_Boosts = Type_Boost + Domain_Boost + Success_Boost

Time_Decay = (time_since_use / 1000)^0.5  ← Older = lower activation
```

See **WS2-UNIFIED-MEMORY-ARCHITECTURE.md** for complete algorithm and examples.

---

## Assessment & Complexity Classification

### Keyword-Based Assessment Function

```python
COMPLEXITY_KEYWORDS = {
    # Strategic/Analysis (weight +0.3)
    "analyze": 0.3, "compare": 0.3, "evaluate": 0.3,
    "strategy": 0.3, "recommend": 0.3, "implications": 0.2,

    # Complexity indicators (weight +0.2)
    "novel": 0.2, "unprecedented": 0.2, "uncertain": 0.2,
    "contradictory": 0.2, "dilemma": 0.2,

    # Simplicity keywords (weight -0.3)
    "define": -0.3, "list": -0.3, "what is": -0.3,
    "explain": -0.2, "factual": -0.2,
}

STRUCTURAL_INDICATORS = {
    "question_count": 0.05,  # Per question beyond first
    "word_count": 0.001,     # Per word beyond 20
    "conjunctions": {
        "but": 0.1, "however": 0.15,
        "alternatively": 0.1, "and": 0.05
    }
}

def assess_complexity(prompt: str) -> dict:
    """Classify as SIMPLE | MEDIUM | COMPLEX"""

    # Keyword scoring
    keyword_score = sum(
        COMPLEXITY_KEYWORDS.get(word, 0)
        for word in prompt.lower().split()
    )

    # Structural scoring
    questions = prompt.count('?')
    words = len(prompt.split())
    question_score = max(0, (questions - 1) * 0.05)
    word_score = min((words - 20) * 0.001, 0.15)

    # Total
    total_score = keyword_score + question_score + word_score

    if total_score > 0.5:
        return {"routing": "COMPLEX", "score": total_score}
    elif total_score < -0.3:
        return {"routing": "SIMPLE", "score": total_score}
    else:
        return {"routing": "MEDIUM", "score": total_score}
```

### Decision Logic

```
if assessment.routing == "SIMPLE":
    └─ Path: Direct LLM or single subagent
    └─ Skip SOAR-Assist

elif assessment.routing == "COMPLEX":
    └─ Path: SOAR-Assist → Orchestrator → Subagents

else:  # MEDIUM
    └─ Path: Run both (simple + complex), compare
    └─ ACT-R learns which is better
```

---

## Orchestrator Function

### Purpose

Match decomposed subgoals to agents with best fit based on:
1. Capability match (domain + type)
2. Success rate (historical performance)
3. Resource availability
4. Cost optimization
5. Execution time estimates

### Algorithm

```python
def orchestrator_route(decomposition, capability_registry):
    """
    For each subgoal in decomposition:
      1. Query registry for matching agents
      2. Rank by: success_rate, availability, cost
      3. Assign best agent
      4. Check for parallelization
      5. Return routing plan
    """

    routing_plan = {
        "assignments": {},
        "parallel_groups": [],
        "execution_timeline": {},
        "resource_plan": {}
    }

    # For each subgoal, find best agent
    for subgoal in decomposition['subgoals']:
        candidates = capability_registry.find_agents_for(
            domain=subgoal['domain'],
            subgoal_type=subgoal['type'],
            min_success_rate=0.75
        )

        if not candidates:
            # Fallback: Use general LLM
            selected_agent = "direct_llm"
        else:
            # Rank by weighted score
            scored = []
            for agent in candidates:
                score = (
                    agent.success_rate * 0.5 +
                    agent.availability_ratio * 0.3 +
                    (1 - agent.cost_ratio) * 0.2
                )
                scored.append((agent, score))

            selected_agent = max(scored, key=lambda x: x[1])[0].id

        routing_plan['assignments'][subgoal['id']] = selected_agent

    # Identify parallelizable groups
    routing_plan['parallel_groups'] = identify_parallel_groups(
        subgoals=decomposition['subgoals'],
        assignments=routing_plan['assignments']
    )

    return routing_plan
```

### Capability Registry Query

The orchestrator queries the **Subagent Capability Registry** to find agents.

---

## Subagent Capability Registry

### Purpose

Central registry of all available agents and their capabilities.

**Updated every invocation** with:
- Execution metrics (success/failure, time, cost)
- Capability confirmation (what they can/can't do)
- Resource availability (current load, capacity)
- Performance history (trending success rate)

### Registry Schema

```json
{
  "registry_metadata": {
    "version": "1.0",
    "last_updated": "2025-12-07T14:35:00Z",
    "total_agents": 5,
    "total_capabilities": 18
  },

  "agents": {
    "@business-analyst": {
      "id": "@business-analyst",
      "name": "Business Analyst",
      "description": "Market and competitive analysis specialist",
      "registered_at": "2025-12-01T08:00:00Z",
      "availability": "available",

      "capabilities": [
        {
          "id": "cap_001",
          "domain": "market_research",
          "subgoal_types": [
            {
              "type": "competitive_analysis",
              "success_rate": 0.87,
              "avg_execution_time_s": 45,
              "cost_per_invocation": 0.50,
              "invocation_count": 42,
              "last_used": "2025-12-07T14:30:00Z"
            },
            {
              "type": "trend_analysis",
              "success_rate": 0.85,
              "avg_execution_time_s": 50,
              "cost_per_invocation": 0.45,
              "invocation_count": 38,
              "last_used": "2025-12-07T14:25:00Z"
            }
          ]
        }
      ],

      "constraints": {
        "max_parallel_tasks": 3,
        "min_time_per_task_s": 30,
        "skill_level": "expert"
      },

      "current_status": {
        "status": "available",
        "current_load": 0,
        "max_capacity": 3,
        "queue_length": 0
      },

      "performance_history": {
        "daily": {
          "date": "2025-12-07",
          "tasks_completed": 5,
          "successful_tasks": 4,
          "success_rate": 0.80,
          "avg_execution_time_s": 44
        },
        "weekly": {
          "tasks_completed": 32,
          "success_rate": 0.82,
          "trend": "improving"
        }
      }
    },

    "@qa-test-architect": {
      "id": "@qa-test-architect",
      "capabilities": [...],
      "current_status": {...},
      "performance_history": {...}
    }
  }
}
```

### Registry Update on Invocation

**Every time a subagent is invoked:**

```python
def update_registry_on_invocation(
    agent_id: str,
    subgoal_type: str,
    execution_time_s: float,
    success: bool,
    cost: float
):
    """
    Update registry with new invocation data
    Recalculate success rates and trends
    """

    agent = registry.get_agent(agent_id)
    capability = agent.get_capability(subgoal_type)

    # Update counts
    capability.invocation_count += 1
    capability.last_used = now()

    # Update success rate
    if success:
        capability.success_count += 1
        capability.success_rate = (
            capability.success_count / capability.invocation_count
        )
    else:
        capability.failure_count += 1
        capability.success_rate = (
            capability.success_count / capability.invocation_count
        )

    # Update execution time (moving average)
    capability.avg_execution_time_s = (
        0.7 * capability.avg_execution_time_s +
        0.3 * execution_time_s
    )

    # Update daily stats
    today = date.today()
    if today not in agent.daily_stats:
        agent.daily_stats[today] = {
            "tasks_completed": 0,
            "successful_tasks": 0
        }

    agent.daily_stats[today]['tasks_completed'] += 1
    if success:
        agent.daily_stats[today]['successful_tasks'] += 1

    # Update current status
    agent.current_status.current_load -= 1  # Task completed

    # Persist
    registry.save(agent)

    return {
        "registry_updated": True,
        "new_success_rate": capability.success_rate,
        "invocation_count": capability.invocation_count,
        "avg_time_s": capability.avg_execution_time_s
    }
```

### Registry Queries

```python
# Orchestrator queries registry

# Find agents for specific capability
agents = registry.find_agents_for(
    domain="market_research",
    subgoal_type="competitive_analysis",
    min_success_rate=0.75
)

# Get agent stats
stats = registry.get_agent_stats(agent_id="@business-analyst")

# Check availability
available = registry.check_availability(
    agent_id="@business-analyst",
    tasks_needed=1
)

# Get performance history
history = registry.get_performance_history(
    agent_id="@business-analyst",
    days=7
)
```

---

## Self-Organization Function

### Purpose

Agents dynamically adapt roles and coordination based on:
- Problem decomposition
- Current capabilities and availability
- Performance history and trends
- Resource constraints
- Execution dependencies

### When Self-Organization Runs

```
Optional validation step after Orchestrator routing:
├─ Should we use this team composition?
├─ Can agents work in parallel?
├─ Are there better alternatives?
└─ Confirm or suggest adjustments
```

### Algorithm

```python
def self_organize(decomposition, routing_plan, registry):
    """
    Validate and optimize agent team
    """

    optimization_report = {
        "original_routing": routing_plan,
        "validation_results": {},
        "optimizations_suggested": [],
        "final_routing": routing_plan  # Default to original
    }

    # Check 1: Can all agents handle their assigned tasks in parallel?
    parallel_conflicts = check_parallel_feasibility(
        assignments=routing_plan['assignments'],
        registry=registry
    )
    if parallel_conflicts:
        optimization_report['validation_results']['parallel_feasible'] = False
        # Suggest sequential execution
    else:
        optimization_report['validation_results']['parallel_feasible'] = True

    # Check 2: Are there better agents available?
    for subgoal_id, assigned_agent in routing_plan['assignments'].items():
        alternatives = find_alternatives(
            subgoal=decomposition[subgoal_id],
            current_assignment=assigned_agent,
            registry=registry
        )

        if alternatives:
            quality_improvement = compare_alternatives(
                current=assigned_agent,
                alternatives=alternatives,
                registry=registry
            )

            if quality_improvement > 0.10:  # 10% improvement threshold
                optimization_report['optimizations_suggested'].append({
                    'subgoal': subgoal_id,
                    'current': assigned_agent,
                    'suggested': alternatives[0],
                    'improvement': quality_improvement
                })

    # Check 3: Resource constraints
    resource_check = validate_resources(
        assignments=routing_plan['assignments'],
        registry=registry
    )
    optimization_report['validation_results']['resources_available'] = (
        resource_check['all_resources_available']
    )

    if not resource_check['all_resources_available']:
        optimization_report['validation_results']['warnings'] = (
            resource_check['resource_warnings']
        )

    return optimization_report
```

---

## Three Routing Flows

### Flow 1: SIMPLE Query (No SOAR-Assist)

**Timeline: 8-15 seconds**

```
User: "What is the market size for AI agents?"
    ↓
Assessment: SIMPLE (complexity_score: -0.2)
    ↓
Main Agent Logic:
  "This is a factual query, not requiring decomposition"
    ↓
Orchestrator Decision:
  Query registry: "Who handles factual_queries + market_size?"
    ↓
Candidate agents:
  ├─ @business-analyst: success_rate=0.90, time=15s, cost=$0.30
  ├─ @knowledge-specialist: success_rate=0.95, time=10s, cost=$0.20
  └─ direct_llm: success_rate=0.85, time=5s, cost=$0.00
    ↓
Selection (by score):
  @knowledge-specialist wins (best quality-cost tradeoff)
    ↓
Invoke Subagent:
  Task: "Provide market size for AI agents"
  Context: {factual_query, market_analysis}
    ↓
Subagent executes (10-15s)
    ↓
Return result: "$X billion market"
    ↓
ACT-R Learning:
  ├─ @knowledge-specialist.success_rate: 0.95 → confirmed
  ├─ @knowledge-specialist.activation: +0.15 (boost)
  ├─ Fact learned: "AI market ~$Xb"
  └─ Next similar query: Use @knowledge-specialist (high activation)
    ↓
Done (8-15s total)
```

### Flow 2: COMPLEX Query (Full SOAR-Assist + Orchestration)

**Timeline: 65-90 seconds**

```
User: "What business opportunities exist in AI agent market?"
    ↓
Assessment: COMPLEX (complexity_score: +0.72)
    ↓
SOAR-Assist Decomposition (4-5s):
  Elaboration: Query ACT-R facts
    "What do we know about AI market?"
    → Retrieved: 5 facts (activation: 0.85-0.92)

  Proposal: Generate subgoals
    ├─ "Understand competitive landscape"
    ├─ "Identify market trends"
    ├─ "Analyze adoption gaps"
    └─ "Synthesize opportunities"

  Evaluation: Score importance
    ├─ Competitive: 0.92 (foundation)
    ├─ Trends: 0.88 (shows direction)
    ├─ Gaps: 0.82 (identifies opportunities)
    └─ Synthesis: 0.95 (critical)

  Decision: Create decomposition
    Output: Structured subgoals with routing requirements
    ↓
Orchestrator Routing (1s):
  sg1 (competitive_analysis, market_research):
    Query registry → @market-researcher (success: 0.90)

  sg2 (trend_analysis, market_research):
    Query registry → @trend-analyst (success: 0.92)

  sg3 (gap_analysis, market_research):
    Query registry → @research-analyst (success: 0.88)

  sg4 (synthesize, strategic_reasoning):
    Query registry → @business-analyst (success: 0.87)
    ↓
Self-Organization (optional):
  Validate: All three research agents can work in parallel? YES
  Validate: Resources available? YES
  Decision: Proceed with parallel execution
    ↓
Invoke Subagents (Parallel - 45-60s):
  @market-researcher executes sg1 (45s) → Competitors list
  @trend-analyst executes sg2 (50s) → Trends analysis
  @research-analyst executes sg3 (40s) → Gaps identified

  All three run in parallel (max time: 50s)
    ↓
Collect Results:
  sg1_result: "Competitors: [A, B, C, D, E]"
  sg2_result: "Trends: [T1 growing, T2 declining, T3 emerging]"
  sg3_result: "Gaps: [No X solution, Y underserved, Z not addressed]"
    ↓
Synthesis (10-15s):
  SOAR-Assist new cycle (synthesis subgoal):
    Input: All three results
    Reasoning: "Given competitors, trends, gaps → opportunities?"
    Output: "Opportunities: [O1, O2, O3] with strategic positioning"
    ↓
Return Final Response (comprehensive, strategic)
    ↓
ACT-R Learning (1s):
  1. SOAR-Assist utility:
     ├─ success_score: 0.88
     ├─ soar_utility: 0.82 → 0.85
     └─ activation: 0.78 → 0.85

  2. Agent performance:
     ├─ @market-researcher: success + activation +0.15
     ├─ @trend-analyst: success + activation +0.15
     ├─ @research-analyst: success + activation +0.15
     └─ @business-analyst: success + activation +0.15

  3. Registry updated:
     ├─ @market-researcher.invocation_count: 42 → 43
     ├─ @market-researcher.success_rate: 0.88 → 0.89
     ├─ Similar for other agents
     └─ New capability signature: "market_research + strategy works"

  4. Learning metrics:
     ├─ Rules created: 1 (this decomposition style)
     ├─ Utilities updated: 4 (agent success rates)
     ├─ Facts activated: 5 (new market insights)
     └─ Resources tracked: websearch 3x, bash 2x
    ↓
Done (65-90s total)

Next similar complex problem:
  ├─ SOAR-Assist activation: HIGH (0.85)
  ├─ Agents activation: HIGH (0.85+)
  ├─ Similar decomposition will activate immediately
  └─ Faster/better next time (learning accelerates)
```

### Flow 3: MEDIUM Query (Comparison Learning)

**Timeline: First time 20s, subsequent ~5s**

```
User: "What are the main challenges in AI adoption?"
    ↓
Assessment: MEDIUM (complexity_score: 0.35)
    ↓
Decision Point: Uncertain complexity
    └─ Run both paths, learn which is better
    ↓
PARALLEL EXECUTION (Both Paths):

Path A (Simple - 4s):
  Direct LLM:
    "AI adoption challenges:"
    1. Talent shortage
    2. Integration complexity
    3. Cost concerns

  Quality: 70% (covers basics)

Path B (Complex - 14s):
  SOAR-Assist decompose:
    sg1: Understand adoption blockers
    sg2: Industry research on adoption
    sg3: Technical/organizational barriers
    sg4: Synthesize into coherent challenges

  Route to specialists
  Quality: 88% (comprehensive, nuanced)
    ↓
Compare Outcomes:
  Path B (0.88) >> Path A (0.70)
  Difference: +18% quality
  Time cost: 10 additional seconds
    ↓
ACT-R Learning:
  "For 'challenges in adoption' questions:
   - Simple path: 4s, 70% quality
   - Complex path: 14s, 88% quality
   - Recommendation: Complex is worth 10s extra"
    ↓
Return Best Result (Path B)
    ↓
Next Similar Question (within same day/week):
  Assessment: MEDIUM
  ACT-R memory: "Use complex path" (high activation)
  Decision: Automatically run SOAR-Assist
  Timeline: 14s (proven optimal)

Result: Faster convergence to optimal strategy
```

---

## Synthesis Strategies

### Level 1: Simple Aggregation (Main Agent)

**When to use:**
- Results are simple lists/facts
- Just combining data (no reasoning needed)
- Time: <5 seconds

**Example:**
```
Results:
├─ sg1: [Competitor A, B, C]
├─ sg2: [Trend 1, 2, 3]
└─ sg3: [Gap X, Y, Z]

Synthesis:
  final_response = f"""
  COMPETITIVE LANDSCAPE: {sg1_results}
  MARKET TRENDS: {sg2_results}
  IDENTIFIED OPPORTUNITIES: {sg3_results}
  """
```

### Level 2: Logical Integration (SOAR-Assist New Cycle)

**When to use:**
- Results need analysis/connection
- Requires reasoning
- Time: 10-15 seconds

**Example:**
```
Results:
├─ sg1: Competitors focus on [X, Y]
├─ sg2: Market trends show [Z direction]
└─ sg3: Customers need [A, B]

SOAR-Assist synthesis subgoal:
  "How do these results connect? Where are gaps?"

Reasoning:
  "Competitors focus on X (proven market)
   Trends show Z direction (future opportunity)
   Customers need A and B (unmet demand)
   → Opportunity: Solve A using Z approach (competitors missed)"
```

### Level 3: Strategic Synthesis (Specialized Agent)

**When to use:**
- Results need strategic decision-making
- Complex cross-domain reasoning
- Time: 15-20 seconds

**Example:**
```
Results:
├─ sg1: Competitive positioning (mature players dominate)
├─ sg2: Technology trends (AI/ML inflection point)
├─ sg3: Customer adoption barriers (talent + integration)
└─ sg4: Market sizing ($10B total)

Synthesis decision:
  if @strategist available:
    Invoke: "@strategist" with full context
  else:
    Use SOAR-Assist with strategy reasoning

Strategic questions:
  "Given competitive position + tech trends + barriers + market size:
   - Should we be aggressive entrant?
   - Should we partner with established players?
   - Should we position as acquisition target?"
```

---

## Unified Learning: SOAR+ACT-R

### How Learning is Unified

Every outcome updates **both** SOAR and ACT-R simultaneously:

```python
def unified_learning(
    execution_outcome,
    soar_strategy_id,
    subgoal_type,
    execution_details
):
    """
    When SOAR-Assist strategy is used:
      1. Update SOAR utility (success rate of this decomposition)
      2. Update ACT-R activation (frequency + recency)
      3. Update subagent performance in registry
      4. Create correlations between SOAR success and agent selection
    """

    # Get the SOAR strategy from memory
    soar_rule = knowledge_store.get_rule(soar_strategy_id)

    # Calculate success (from follow-up context or immediate metrics)
    success_score = evaluate_success(execution_outcome)

    # ===== SOAR Learning =====
    # Update utility: (successes × reward) - (failures × penalty) - cost
    if success_score > 0.7:
        soar_rule.soar_successes += 1
        utility_adjustment = success_score * 0.5
    else:
        soar_rule.soar_failures += 1
        utility_adjustment = success_score * -0.3

    soar_rule.soar_utility = calculate_utility(
        successes=soar_rule.soar_successes,
        failures=soar_rule.soar_failures,
        execution_cost=execution_details['execution_time_s'] / 1000.0
    )
    soar_rule.soar_uses += 1

    # ===== ACT-R Learning =====
    # Update activation: base + spreading + boosts - decay
    activation_boost = success_score * 0.3  # 0-0.3 boost
    soar_rule.actr_activation += activation_boost
    soar_rule.actr_frequency += 1
    soar_rule.actr_recency = now()

    if success_score > 0.7:
        soar_rule.actr_last_success = now()
    else:
        soar_rule.actr_last_failure = now()

    # ===== Agent Performance Learning =====
    # Update agent performance in registry
    for subgoal_id, agent_id in execution_details['assignments'].items():
        update_registry_on_invocation(
            agent_id=agent_id,
            subgoal_type=execution_details['subgoal_types'][subgoal_id],
            execution_time_s=execution_details['agent_execution_times'][agent_id],
            success=execution_details['agent_successes'][agent_id],
            cost=execution_details['agent_costs'][agent_id]
        )

    # ===== Correlation Learning =====
    # Connect SOAR success to agent selection
    correlation = {
        'soar_strategy_id': soar_strategy_id,
        'soar_utility': soar_rule.soar_utility,
        'soar_success': success_score > 0.7,
        'agents_used': execution_details['assignments'].values(),
        'avg_agent_success': avg([
            execution_details['agent_successes'][aid]
            for aid in execution_details['assignments'].values()
        ]),
        'timing': {
            'soar_decomposition_s': execution_details['soar_time_s'],
            'agent_execution_s': execution_details['agent_total_time_s'],
            'total_s': execution_details['total_time_s']
        }
    }

    # ===== Persist =====
    knowledge_store.update_rule(soar_strategy_id, soar_rule)
    knowledge_store.add_correlation(correlation)

    return {
        'learning_captured': True,
        'soar_utility_new': soar_rule.soar_utility,
        'actr_activation_new': soar_rule.actr_activation,
        'agents_updated': len(execution_details['assignments']),
        'correlation_recorded': True
    }
```

### Success Measurement Rules

```python
SUCCESS_RULES = [
    {
        "name": "no_followup",
        "signal": lambda response: not contains_question(response),
        "weight": 0.35,
        "meaning": "User satisfied, no gaps",
        "soar_impact": +0.25,
        "confidence": 0.90
    },
    {
        "name": "user_thanks",
        "signal": lambda response: any(p in response for p in
                  ["thanks", "perfect", "exactly", "that helps"]),
        "weight": 0.40,
        "meaning": "Explicit satisfaction",
        "soar_impact": +0.40,
        "confidence": 0.95
    },
    {
        "name": "followup_elaborate",
        "signal": lambda response: any(p in response for p in
                  ["can you elaborate", "tell me more", "explain further"]),
        "weight": 0.20,
        "meaning": "Incomplete coverage",
        "soar_impact": -0.10,
        "confidence": 0.70
    },
    {
        "name": "followup_building",
        "signal": lambda response: any(p in response for p in
                  ["given this", "based on that", "next steps", "what about"]),
        "weight": 0.30,
        "meaning": "Success! Building on response",
        "soar_impact": +0.15,
        "confidence": 0.80
    },
    {
        "name": "addressed_all_subgoals",
        "signal": lambda response: response_covers_all_subgoals(response),
        "weight": 0.40,
        "meaning": "Structurally complete",
        "soar_impact": +0.15,
        "confidence": 0.85
    }
]

def measure_success(response, followup_message=None):
    """Measure success from immediate + followup context"""
    success_score = 0
    signals = []

    # Immediate checks (no followup needed)
    for rule in SUCCESS_RULES:
        if rule['signal'](response):
            if followup_message or not rule['name'].startswith('followup'):
                success_score += rule['weight'] * rule['soar_impact']
                signals.append(rule['name'])

    return {
        'success_score': success_score,
        'signals_triggered': signals,
        'confidence': calculate_confidence(signals)
    }
```

---

## Learning Metrics & Tracking

### Comprehensive Metrics Structure

```json
{
  "session_metadata": {
    "session_id": "session-2025-12-07-001",
    "created_at": "2025-12-07T08:00:00Z",
    "duration_minutes": 480
  },

  "daily_metrics": {
    "date": "2025-12-07",
    "prompts_processed": 15,
    "soar_assist_invocations": 3,
    "subagents_invoked_total": 8,

    "learning_events": {
      "rules_created": 2,
      "rules_reinforced": 1,
      "utilities_updated": 5,
      "facts_activated": 3,
      "activations_boosted": 7,
      "new_correlations": 3
    },

    "success_metrics": {
      "successful_responses": 12,
      "partial_responses": 2,
      "failed_responses": 1,
      "avg_success_rate": 0.80
    },

    "performance": {
      "simple_queries": {"count": 8, "avg_time_s": 5.2},
      "complex_queries": {"count": 5, "avg_time_s": 68.5},
      "medium_queries": {"count": 2, "avg_time_s": 12.3}
    },

    "resources_used": {
      "mcp:websearch": 3,
      "mcp:reddit": 2,
      "bash": 4,
      "@business-analyst": 6,
      "@qa-test-architect": 2
    },

    "registry_updates": {
      "total_invocations_logged": 8,
      "agent_capabilities_confirmed": 6,
      "success_rates_improved": 4,
      "new_agent_registrations": 0
    }
  },

  "weekly_metrics": {
    "week_ending": "2025-12-07",
    "total_prompts_processed": 105,
    "avg_success_rate": 0.79,
    "total_learning_events": 78,
    "trend": "improving"
  },

  "monthly_metrics": {
    "month": "December 2025",
    "total_prompts_processed": 427,
    "improvement_vs_last_month": "+0.08",
    "most_effective_agent": "@business-analyst",
    "most_effective_resource": "mcp:websearch",
    "learning_velocity": "13 events/day"
  }
}
```

### Per-Day Learning Summary

```python
def generate_daily_summary():
    """
    Daily report showing:
    - Learning captured
    - Success trends
    - Resource efficiency
    - Agent performance
    """

    return {
        "learning_captured_today": {
            "new_rules": 2,
            "rule_reinforcements": 1,
            "utility_updates": 5,
            "fact_activations": 3,
            "total_events": 11
        },
        "success_metrics": {
            "successful_responses": 12,
            "success_rate": 0.80,
            "trend": "stable"
        },
        "average_per_day": {
            "new_rules_per_day": 2.1,
            "utilities_updated_per_day": 5.0,
            "fact_activations_per_day": 3.2,
            "success_rate_per_day": 0.79
        },
        "agent_registry_insights": {
            "agents_invoked": 3,
            "invocations_logged": 8,
            "performance_improved": 3,
            "new_capabilities_confirmed": 2
        }
    }
```

---

## Complete Pseudocode Implementation

### Main Orchestration Loop

```python
class WS2SOARAssistSystem:
    """Complete WS2 system with SOAR-Assist, Orchestrator, Self-Org"""

    def __init__(self):
        self.knowledge_store = UnifiedMemoryStore()
        self.capability_registry = SubagentCapabilityRegistry()
        self.learning_metrics = LearningMetricsTracker()

    def handle_prompt(self, user_prompt):
        """Complete flow from prompt to response"""

        # Phase 1: Assessment
        assessment = self.assess_complexity(user_prompt)

        # Phase 2: Conditional SOAR-Assist
        if assessment['routing'] in ['COMPLEX', 'MEDIUM']:
            soar_result = self.run_soar_assist(user_prompt, assessment)
        else:
            soar_result = None

        # Phase 3: Orchestrator Routing
        if soar_result:
            routing_plan = self.orchestrate(soar_result)
        else:
            routing_plan = self.orchestrate_simple(user_prompt)

        # Phase 4: Self-Organization (optional)
        optimized_routing = self.self_organize(routing_plan)

        # Phase 5: Invoke Subagents
        subagent_results = self.invoke_subagents(optimized_routing)

        # Phase 6: Synthesis
        final_response = self.synthesize(subagent_results, soar_result)

        # Phase 7: ACT-R Learning
        self.update_learning(final_response, routing_plan, soar_result)

        return final_response

    def assess_complexity(self, prompt):
        """Classify as SIMPLE|MEDIUM|COMPLEX"""
        keyword_score = self._score_keywords(prompt)
        structural_score = self._score_structure(prompt)
        total = keyword_score + structural_score

        if total > 0.5:
            return {"routing": "COMPLEX", "score": total}
        elif total < -0.3:
            return {"routing": "SIMPLE", "score": total}
        else:
            return {"routing": "MEDIUM", "score": total}

    def run_soar_assist(self, prompt, assessment):
        """Run SOAR decomposition (4-5 seconds)"""
        state = {}

        # Elaboration
        state = self._elaboration_phase(prompt, state)

        # Proposal
        state = self._proposal_phase(prompt, state)

        # Evaluation
        state = self._evaluation_phase(state)

        # Decision
        decomposition = self._decision_phase(state)

        return decomposition

    def orchestrate(self, decomposition):
        """Route subgoals to agents via capability registry"""
        routing = {}

        for subgoal in decomposition['subgoals']:
            # Query registry
            candidates = self.capability_registry.find_agents_for(
                domain=subgoal['domain'],
                subgoal_type=subgoal['type'],
                min_success_rate=0.75
            )

            # Select best
            if candidates:
                best = max(candidates, key=lambda a: a.success_rate)
                routing[subgoal['id']] = best.id
            else:
                routing[subgoal['id']] = 'direct_llm'

        return routing

    def invoke_subagents(self, routing):
        """Invoke agents and collect results"""
        results = {}

        for subgoal_id, agent_id in routing.items():
            if agent_id == 'direct_llm':
                result = self._direct_llm(subgoal_id)
            else:
                result = self._invoke_task(agent_id, subgoal_id)

            results[subgoal_id] = result

            # Update registry on completion
            self.capability_registry.update_on_invocation(
                agent_id=agent_id,
                success=result['success'],
                execution_time_s=result['time'],
                cost=result['cost']
            )

        return results

    def update_learning(self, response, routing, soar_result):
        """Unified SOAR+ACT-R learning"""

        # Measure success
        success = self._measure_success(response)

        # Update SOAR utility (if used)
        if soar_result:
            self._update_soar_utility(soar_result['id'], success)
            self._update_actr_activation(soar_result['id'], success)

        # Update metrics
        self.learning_metrics.record_execution(
            success=success,
            routing=routing,
            soar_used=soar_result is not None,
            execution_time=self._get_execution_time()
        )

        return True
```

---

## WHAT vs HOW Diagram & Learning Loop

### The Core Learning-Reasoning-Solving Loop

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                     LEARNING-REASONING-SOLVING LOOP                 │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     INPUT LAYER                             │   │
│  │  User Prompt → Assessment → Complexity Classification       │   │
│  └──────────────────────────┬────────────────────────────────┘   │
│                             ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  │                    WHAT LAYER                              │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │                                                     │   │   │
│  │  │  PROBLEM UNDERSTANDING (WHAT)                      │   │   │
│  │  │                                                     │   │   │
│  │  │  SOAR-Assist: Decomposition                        │   │   │
│  │  │  ├─ Question: What are the subgoals?              │   │   │
│  │  │  ├─ Process: Elaborate → Propose → Evaluate       │   │   │
│  │  │  └─ Output: Explicit decomposition                │   │   │
│  │  │                                                     │   │   │
│  │  │  Knowledge Store (ACT-R): Facts + Rules            │   │   │
│  │  │  ├─ Stores: What we know                           │   │   │
│  │  │  ├─ Indexes: By activation (frequency+recency)    │   │   │
│  │  │  └─ Returns: Top-N by relevance                    │   │   │
│  │  │                                                     │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                         ↓                                   │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  HOW LAYER                                          │   │   │
│  │  │                                                     │   │   │
│  │  │  EXECUTION STRATEGY (HOW)                          │   │   │
│  │  │                                                     │   │   │
│  │  │  Orchestrator: Routing                             │   │   │
│  │  │  ├─ Question: How should we solve this?            │   │   │
│  │  │  ├─ Process: Match subgoals to agents              │   │   │
│  │  │  └─ Output: Agent assignments + execution plan     │   │   │
│  │  │                                                     │   │   │
│  │  │  Capability Registry: Agent Database               │   │   │
│  │  │  ├─ Stores: Agent capabilities + performance       │   │   │
│  │  │  ├─ Tracks: Invocations + success rates            │   │   │
│  │  │  └─ Returns: Best agents for each subgoal          │   │   │
│  │  │                                                     │   │   │
│  │  │  Self-Organization (optional)                      │   │   │
│  │  │  ├─ Question: Can we optimize coordination?        │   │   │
│  │  │  ├─ Process: Validate team + parallelization       │   │   │
│  │  │  └─ Output: Optimized execution strategy           │   │   │
│  │  │                                                     │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                         ↓                                   │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  SOLVING LAYER                                     │   │   │
│  │  │                                                     │   │   │
│  │  │  EXECUTION (SOLVING)                               │   │   │
│  │  │                                                     │   │   │
│  │  │  Subagents: Domain Experts                         │   │   │
│  │  │  ├─ Execute: Assigned subgoals in parallel        │   │   │
│  │  │  └─ Return: Results + execution metrics            │   │   │
│  │  │                                                     │   │   │
│  │  │  Synthesis Layer                                   │   │   │
│  │  │  ├─ Level 1: Aggregate results (main agent)        │   │   │
│  │  │  ├─ Level 2: Integrate logically (SOAR-Assist)     │   │   │
│  │  │  └─ Level 3: Strategic synthesis (specialist)      │   │   │
│  │  │                                                     │   │   │
│  │  │  Output: Final Response                            │   │   │
│  │  │                                                     │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                         ↓                                   │   │
│  └─────────────────────────┬────────────────────────────────┘   │
│                             ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  FEEDBACK LAYER                            │   │
│  │                                                             │   │
│  │  ACT-R Learning: Unified Updates                           │   │
│  │  ├─ Measure success (from follow-up context)              │   │
│  │  ├─ Update SOAR utilities (did decomposition help?)       │   │
│  │  ├─ Update ACT-R activations (frequency + recency)        │   │
│  │  ├─ Update agent registry (invocation counts + success)    │   │
│  │  └─ Record learning metrics (daily/weekly/monthly)         │   │
│  │                                                             │   │
│  │  Knowledge Store Updates:                                 │   │
│  │  ├─ New rules: SOAR captures traces                       │   │
│  │  ├─ Fact activations: ACT-R increases activation         │   │
│  │  └─ Utility improvements: Both systems improve            │   │
│  │                                                             │   │
│  │  Next Similar Problem:                                    │   │
│  │  ├─ SOAR-Assist activation: Higher (cached strategy)      │   │
│  │  ├─ Agent activation: Higher (proven effective)           │   │
│  │  ├─ Execution: Faster + better quality                    │   │
│  │  └─ Result: Learning accelerates (virtuous cycle)         │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Detailed WHAT-HOW-SOLVE Matrix

```
┌───────────────────┬──────────────────────────┬──────────────────┐
│   LAYER           │   QUESTION (WHAT)        │   ANSWER (HOW)   │
├───────────────────┼──────────────────────────┼──────────────────┤
│ UNDERSTANDING     │                          │                  │
│ (Problem Analysis)│ What is the problem?     │ Assessment:      │
│                   │ Is it simple/complex?    │ - Keywords       │
│                   │ What are subgoals?       │ - Structure      │
│                   │ What's unknown?          │ - Complexity     │
│                   │                          │                  │
│                   │ SOAR-Assist:             │ - Elaboration    │
│                   │ What facts do we need?   │ - Proposal       │
│                   │ What are options?        │ - Evaluation     │
│                   │ Which is best?           │ - Decision       │
├───────────────────┼──────────────────────────┼──────────────────┤
│ ROUTING           │                          │                  │
│ (Agent Selection) │ What capabilities        │ Orchestrator:    │
│                   │ do we need?              │ - Query registry │
│                   │ Which agents can help?   │ - Match subgoals │
│                   │ Who's available?         │ - Rank agents    │
│                   │ What's the best order?   │ - Assign roles   │
│                   │                          │                  │
│                   │ Self-Organization:       │ - Validate team  │
│                   │ Can agents coordinate?   │ - Check parallel │
│                   │ Should we optimize?      │ - Confirm plan   │
├───────────────────┼──────────────────────────┼──────────────────┤
│ EXECUTION         │                          │                  │
│ (Problem Solving) │ What should each         │ Subagents:       │
│                   │ agent do?                │ - Execute tasks  │
│                   │ In what order?           │ - Parallel work  │
│                   │ Can they work parallel?  │ - Return results │
│                   │                          │                  │
│                   │ How do we combine        │ Synthesis:       │
│                   │ results?                 │ - Aggregate      │
│                   │ Any final reasoning?     │ - Integrate      │
│                   │ Final response?          │ - Strategize     │
├───────────────────┼──────────────────────────┼──────────────────┤
│ LEARNING          │                          │                  │
│ (Knowledge Update)│ Did it work?             │ ACT-R Learning:  │
│                   │ Should we repeat?        │ - Measure success│
│                   │ What improved?           │ - Update utils   │
│                   │ Should we change?        │ - Update activat.│
│                   │                          │ - Track metrics  │
│                   │ What worked?             │ - Update registry│
│                   │ What didn't?             │ - Learn patterns │
└───────────────────┴──────────────────────────┴──────────────────┘
```

### Data Flow Diagram

```
USER PROMPT
    ↓
ASSESSMENT (WHAT IS THIS?)
├─ Keywords: analyze, compare, evaluate → COMPLEX
├─ Structure: Multi-question, long text → COMPLEX
└─ Decision: COMPLEX → Use SOAR-Assist
    ↓
SOAR-ASSIST: WHAT ARE SUBGOALS?
├─ Query ACT-R: What do we know?
├─ Proposal: Generate 4 subgoals
├─ Evaluation: Score 0.82-0.95
└─ Output: {sg1, sg2, sg3, sg4} with routing requirements
    ↓
ORCHESTRATOR: WHO SHOULD DO WHAT?
├─ Query Registry: "Who handles competitive_analysis?"
│  └─ Found: @market-researcher (success: 0.90)
├─ Query Registry: "Who handles trend_analysis?"
│  └─ Found: @trend-analyst (success: 0.92)
├─ Query Registry: "Who handles synthesis?"
│  └─ Found: @business-analyst (success: 0.87)
└─ Output: {sg1→@market-researcher, sg2→@trend-analyst, ...}
    ↓
SELF-ORGANIZATION (optional): CAN WE OPTIMIZE?
├─ Validate: All agents available? YES
├─ Validate: Parallelizable? YES (sg1, sg2 parallel)
├─ Optimize: No changes needed
└─ Output: Proceed with current plan
    ↓
EXECUTION: SOLVE EACH SUBGOAL
├─ @market-researcher executes sg1 (45s) → Results A
├─ @trend-analyst executes sg2 (50s) → Results B
├─ (Parallel, max 50s total)
└─ Collect results
    ↓
SYNTHESIS: COMBINE & REASON
├─ SOAR-Assist new cycle: "Synthesize A+B into C"
├─ Output: Strategic opportunities framework
└─ Final response: [Comprehensive answer]
    ↓
LEARNING: UPDATE KNOWLEDGE
├─ Success? YES (user said "thanks")
├─ Update SOAR: soar_utility 0.82 → 0.85
├─ Update ACT-R: activation 0.78 → 0.85
├─ Update Registry:
│  ├─ @market-researcher: invocation_count++ (success)
│  ├─ @trend-analyst: invocation_count++ (success)
│  └─ @business-analyst: invocation_count++ (success)
└─ Log metrics: "SOAR+orchestrator+agents = success"
    ↓
NEXT SIMILAR PROBLEM:
├─ SOAR-Assist activation: 0.85 (higher, faster retrieval)
├─ Agent activations: 0.85+ (higher, selected immediately)
└─ Result: Faster execution (4s savings) + better quality
```

---

## Integration with Subagent Invocation

### How Subagent Tasks Are Invoked

```python
# Main agent invokes subagent with full SOAR context

def invoke_subagent_with_soar_context(
    subagent_type: str,
    subgoal: dict,
    soar_result: dict,
    conversation_history: list
):
    """
    Invoke subagent with SOAR decomposition context
    """

    subagent_prompt = f"""
You are solving a decomposed subgoal.

ORIGINAL PROBLEM: {soar_result['original_prompt']}

SOAR ANALYSIS (Reasoning Structure):
- Subgoals identified: {soar_result['subgoals']}
- Execution order: {soar_result['execution_strategy']['sequential']}
- Your role: Handle '{subgoal['goal']}' (type: {subgoal['type']})

YOUR SPECIFIC TASK:
Domain: {subgoal['domain']}
Type: {subgoal['type']}
Success criteria: {soar_result['routing_requirements'][subgoal['id']]['success_criteria']}

HISTORICAL GUIDANCE (What Has Worked):
- Similar problems solved: {get_similar_problems(subgoal['type'])}
- Effective approaches: {get_effective_approaches(subgoal['type'])}
- Resource requirements: {get_resource_requirements(subgoal['type'])}

CONVERSATION CONTEXT:
{format_conversation_history(conversation_history)}

Please complete this subgoal, staying within the SOAR reasoning structure.
    """

    # Invoke subagent
    result = invoke_task(
        subagent_type=subagent_type,
        prompt=subagent_prompt,
        context={
            "soar_decomposition": soar_result,
            "subgoal_id": subgoal['id'],
            "task_type": subgoal['type'],
            "conversation_history": conversation_history
        }
    )

    # Track invocation in registry
    capability_registry.log_invocation(
        agent_id=subagent_type,
        subgoal_type=subgoal['type'],
        timestamp=now(),
        success=result['success']
    )

    return result
```

### Parallel Subagent Invocation

```python
def invoke_subagents_parallel(subgoals, soar_result):
    """
    Invoke parallelizable subgoals simultaneously
    """

    # Identify parallel groups from SOAR decomposition
    parallel_groups = soar_result['execution_strategy']['parallelizable_groups']

    results = {}

    for group in parallel_groups:
        # Invoke all in group simultaneously
        group_results = {}

        for subgoal_id in group:
            subgoal = soar_result['subgoals_by_id'][subgoal_id]
            agent_id = routing_plan['assignments'][subgoal_id]

            # Non-blocking invocation
            future = invoke_task_async(
                agent_id=agent_id,
                subgoal=subgoal,
                soar_context=soar_result
            )

            group_results[subgoal_id] = future

        # Wait for all in group to complete
        for subgoal_id, future in group_results.items():
            results[subgoal_id] = future.wait()

    return results
```

---

## Agent Registry Tracking

### Registry Entry Structure

```json
{
  "@business-analyst": {
    "id": "@business-analyst",
    "registered_at": "2025-12-01T08:00:00Z",

    "capabilities": [
      {
        "domain": "market_research",
        "subgoal_types": [
          {
            "type": "competitive_analysis",
            "invocation_count": 42,
            "success_count": 37,
            "failure_count": 5,
            "success_rate": 0.881,
            "avg_execution_time_s": 45,
            "cost_per_invocation": 0.50,

            "invocation_history": [
              {
                "timestamp": "2025-12-07T14:32:00Z",
                "success": true,
                "execution_time_s": 44,
                "cost": 0.50,
                "soar_strategy_id": "rule-market-analysis-001"
              },
              {
                "timestamp": "2025-12-07T14:00:00Z",
                "success": true,
                "execution_time_s": 46,
                "cost": 0.50,
                "soar_strategy_id": "rule-market-analysis-001"
              }
            ],

            "performance_history": {
              "daily": {
                "2025-12-07": {
                  "invocations": 2,
                  "successes": 2,
                  "success_rate": 1.0,
                  "avg_time_s": 45
                }
              },
              "weekly": {
                "week_ending_2025-12-07": {
                  "invocations": 8,
                  "success_rate": 0.875,
                  "trend": "improving"
                }
              }
            }
          }
        ]
      }
    ],

    "current_status": {
      "available": true,
      "current_load": 0,
      "max_capacity": 3,
      "next_available_at": "2025-12-07T15:00:00Z"
    },

    "overall_stats": {
      "total_invocations_all_time": 42,
      "overall_success_rate": 0.88,
      "avg_execution_time_s": 45,
      "last_invoked": "2025-12-07T14:32:00Z"
    }
  }
}
```

### Registry Update Process

```python
def update_registry_on_agent_invocation(
    agent_id: str,
    subgoal_type: str,
    execution_time_s: float,
    success: bool,
    cost: float,
    soar_strategy_id: str = None
):
    """
    Called after EVERY subagent invocation to update registry
    """

    agent_entry = registry.get_agent(agent_id)
    capability = agent_entry.get_capability_for_type(subgoal_type)

    # Update counts
    capability.invocation_count += 1
    if success:
        capability.success_count += 1
    else:
        capability.failure_count += 1

    # Recalculate success rate
    capability.success_rate = (
        capability.success_count / capability.invocation_count
    )

    # Update execution time (moving average)
    capability.avg_execution_time_s = (
        0.7 * capability.avg_execution_time_s +
        0.3 * execution_time_s
    )

    # Add invocation to history
    capability.invocation_history.append({
        'timestamp': now(),
        'success': success,
        'execution_time_s': execution_time_s,
        'cost': cost,
        'soar_strategy_id': soar_strategy_id
    })

    # Update daily stats
    today = date.today()
    if today not in agent_entry.daily_stats:
        agent_entry.daily_stats[today] = {
            'invocations': 0,
            'successes': 0
        }

    agent_entry.daily_stats[today]['invocations'] += 1
    if success:
        agent_entry.daily_stats[today]['successes'] += 1

    agent_entry.daily_stats[today]['success_rate'] = (
        agent_entry.daily_stats[today]['successes'] /
        agent_entry.daily_stats[today]['invocations']
    )

    # Update overall stats
    agent_entry.overall_stats['total_invocations_all_time'] += 1
    agent_entry.overall_stats['overall_success_rate'] = capability.success_rate
    agent_entry.overall_stats['last_invoked'] = now()

    # Update current load
    agent_entry.current_status.current_load -= 1

    # Persist
    registry.save(agent_entry)

    return {
        'registry_updated': True,
        'new_success_rate': capability.success_rate,
        'new_invocation_count': capability.invocation_count,
        'daily_success_rate': agent_entry.daily_stats[today]['success_rate']
    }
```

### Registry Queries by Components

```python
# SOAR-Assist uses registry (indirectly, via Orchestrator)
# "Which agents have improved since last use?"
high_improvers = registry.get_agents_by_trend(
    trend="improving",
    days=7,
    min_improvement=0.05
)

# Orchestrator uses registry directly
# "Who can handle competitive_analysis?"
agents = registry.find_agents_for(
    domain="market_research",
    subgoal_type="competitive_analysis",
    min_success_rate=0.75,
    available=True
)

# Self-Organization uses registry
# "What's the team's average success rate?"
team_stats = registry.get_team_stats(
    agents=["@market-researcher", "@trend-analyst"],
    metric="avg_success_rate"
)

# Learning system uses registry
# "What improved this week?"
improvements = registry.get_improvements(
    time_range="weekly",
    sorted_by="improvement_magnitude"
)
```

---

## Implementation Checklist

### Phase 1: Core Infrastructure (Week 1-2)

- [ ] **Unified Memory Store**
  - [ ] JSON schema implementation
  - [ ] File-based persistence
  - [ ] ACT-R retrieval algorithm
  - [ ] Activation calculation

- [ ] **Assessment Function**
  - [ ] Keyword extraction
  - [ ] Complexity scoring
  - [ ] Routing decision logic
  - [ ] Test with 20 sample prompts

- [ ] **SOAR-Assist Skeleton**
  - [ ] Elaboration phase
  - [ ] Proposal phase
  - [ ] Evaluation phase
  - [ ] Decision phase
  - [ ] Decomposition output

### Phase 2: Orchestration (Week 3-4)

- [ ] **Orchestrator Function**
  - [ ] Registry query logic
  - [ ] Agent ranking algorithm
  - [ ] Routing plan generation
  - [ ] Cost optimization

- [ ] **Capability Registry**
  - [ ] Registry schema
  - [ ] Agent registration mechanism
  - [ ] Invocation tracking
  - [ ] Performance history
  - [ ] Daily/weekly aggregation

- [ ] **Self-Organization**
  - [ ] Parallelization detection
  - [ ] Resource validation
  - [ ] Alternative suggestions
  - [ ] Optimization scoring

### Phase 3: Integration (Week 5-6)

- [ ] **Subagent Invocation**
  - [ ] Prompt templating with SOAR context
  - [ ] Parallel execution orchestration
  - [ ] Result collection
  - [ ] Registry updates on completion

- [ ] **Synthesis Layer**
  - [ ] Level 1: Aggregation (main agent)
  - [ ] Level 2: Logical integration (SOAR-Assist)
  - [ ] Level 3: Strategic synthesis (specialist)
  - [ ] Type detection and routing

### Phase 4: Learning System (Week 7-8)

- [ ] **Unified Learning**
  - [ ] Success measurement rules
  - [ ] SOAR utility updates
  - [ ] ACT-R activation updates
  - [ ] Registry updates
  - [ ] Correlation tracking

- [ ] **Metrics Tracking**
  - [ ] Daily aggregation
  - [ ] Weekly trending
  - [ ] Monthly analysis
  - [ ] Performance dashboards

### Phase 5: Testing & Optimization (Week 9-10)

- [ ] **End-to-End Testing**
  - [ ] Simple query flows
  - [ ] Complex query flows
  - [ ] Medium/comparison flows
  - [ ] Parallel execution
  - [ ] Learning verification

- [ ] **Performance Optimization**
  - [ ] Registry query speed
  - [ ] SOAR cycle efficiency
  - [ ] Memory management
  - [ ] Activation calculation optimization

- [ ] **Quality Gates**
  - [ ] Success rate > 85% on test set
  - [ ] Response time < 90s for complex
  - [ ] Learning visible in metrics
  - [ ] Registry tracking accurate

---

## Next Steps

1. **Implement Phase 1 infrastructure** (memory store, assessment, basic SOAR-Assist)
2. **Test end-to-end with 50 sample prompts** across SIMPLE/MEDIUM/COMPLEX
3. **Integrate with actual subagents** (start with @business-analyst)
4. **Measure learning curve** over 2-week period
5. **Document learnings and optimizations** for Phase 2

---

## References

- **WS2-UNIFIED-MEMORY-ARCHITECTURE.md** - Complete memory implementation
- **WS2-APPROACH-1-SIMPLE-SOAR-ACT-R.md** - Simple architecture overview
- **WS2-APPROACH-2-ADVANCED-SOAR-ACTR-TAO-MULTIMODEL.md** - Advanced features
- **WS2-APPROACHES-COMPARISON-DECISION-MATRIX.md** - Architecture comparison
- **WS2-HONEST-ASSESSMENT-SUMMARY.md** - Design decisions and rationale

