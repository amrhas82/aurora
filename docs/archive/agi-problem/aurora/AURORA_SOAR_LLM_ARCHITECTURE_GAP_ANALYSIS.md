# AURORA Framework: SOAR-LLM Integration Gap Analysis
## Critical Architectural Review

**Document Status**: Detailed Gap Analysis with Proposed Solutions
**Focus Areas**: 5 critical architectural gaps identified and addressed
**Last Updated**: 2025-12-08

---

## EXECUTIVE SUMMARY: The Core Problem

The AURORA framework proposes that SOAR + LLM integration creates "semantic reasoning," but current architecture lacks clarity on:

1. **Who's actually reasoning?** (SOAR or LLM)
2. **How interaction flows** (request/response patterns)
3. **How to constrain LLM outputs** (from verbose to structured)
4. **When decomposition is complete** (impasse detection mechanism)
5. **How robotics differs from business logic** (semantic grounding)

Current architecture treats these as separate concerns but doesn't clearly define:
- Interaction protocols
- Validation mechanisms
- Responsibility boundaries
- Constraint enforcement
- Domain-specific adaptations

---

## GAP 1: SOAR-LLM INTERACTION ARCHITECTURE

### The Problem Statement

**Current Understanding**:
> "SOAR asks LLM for semantic decomposition"

**Ambiguities**:
- Does SOAR call LLM like a subroutine, or is it an agent interaction?
- How does SOAR formulate the question?
- What's the response format?
- How are constraints enforced?
- How does SOAR validate the output?

### Proposed Architecture: Three Interaction Patterns

#### Pattern A: Proposal-Elaboration (Recommended)

```
┌─────────────────────────────────────────────────────────────┐
│                    SOAR AGENT CYCLE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  INPUT PHASE → PROPOSAL PHASE → ELABORATION PHASE          │
│                                                             │
│  ┌─────────────┐         ┌──────────────┐                  │
│  │   Current   │         │  Candidate   │                  │
│  │   State     │──────→  │  Operators   │                  │
│  │             │         │  (from rules)│                  │
│  └─────────────┘         └──────┬───────┘                  │
│                                 │                          │
│                          ┌──────▼──────────┐               │
│                          │ IMPASSE DETECT? │               │
│                          │  (No preference)│               │
│                          └──────┬──────────┘               │
│                                 │ YES                      │
│                          ┌──────▼──────────────────┐       │
│                          │  CALL LLM FOR           │       │
│                          │  DECOMPOSITION          │       │
│                          │  ┌────────────────────┐ │       │
│                          │  │ LLM Elaboration:   │ │       │
│                          │  │ - Refine operators │ │       │
│                          │  │ - New attributes   │ │       │
│                          │  │ - Context enriched │ │       │
│                          │  └────────────────────┘ │       │
│                          └──────┬───────────────────┘       │
│                                 │                          │
│                          ┌──────▼──────────────────┐       │
│                          │  LLM RETURNS:           │       │
│                          │  1. Operators list      │       │
│                          │  2. Attributes map      │       │
│                          │  3. Evaluation scores   │       │
│                          └──────┬───────────────────┘       │
│                                 │                          │
│                          ┌──────▼──────────────────┐       │
│                          │ VALIDATE OUTPUT         │       │
│                          │ (Schema + Constraints)  │       │
│                          └──────┬───────────────────┘       │
│                                 │                          │
│                          ┌──────▼──────────────────┐       │
│                          │ ASSIMILATE INTO WM      │       │
│                          │ (Add as new operators)  │       │
│                          └──────┬───────────────────┘       │
│                                 │                          │
│                          ┌──────▼──────────────────┐       │
│                          │ DECISION PHASE          │       │
│                          │ (Select from expanded   │       │
│                          │  operator set)          │       │
│                          └──────────────────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Points**:
- LLM is called **only during impasse** (when multiple operators have equal preference)
- SOAR retains decision authority
- LLM provides elaboration, not decision
- Output is validated against schema before use
- Interaction is structured, not conversational

#### Pattern B: Question-by-Question Elicitation (Alternative)

```
SOAR                          LLM
  │                            │
  │─── "What are the main      │
  │     aspects of this goal?" │──→
  │                            │
  │                    ┌───────┴─────┐
  │                    │ Parse & rank │
  │                    │ key concepts │
  │                    └───────┬─────┘
  │                            │
  │  ←─── ["security",        │
  │       "performance",       │
  │       "usability"]         │
  │                            │
  │─── "What operators exist   │
  │     for 'security'?"       │──→
  │                            │
  │                    ┌───────┴──────────┐
  │                    │ Generate feasible│
  │                    │ operators        │
  │                    └───────┬──────────┘
  │                            │
  │  ←─── ["validate-input",  │
  │       "encrypt-data",     │
  │       "authenticate-user"]│
  │                            │
  │ [Continue for each aspect] │
  │                            │
  │─── "Which is most relevant│
  │     to current state?"     │──→
  │                            │
  │  ←─── "encrypt-data"       │
  │       (with confidence)    │
  │                            │
```

**Key Points**:
- Socratic method: question-by-question
- Better for handling **uncertainty and refinement**
- LLM maintains context across questions
- SOAR gradually builds operator space
- Useful for **novel or complex domains**

#### Pattern C: Streaming Constraint-Based (For Real-Time)

```
SOAR sends constraint spec:
{
  "goal": "Optimize database query",
  "constraints": {
    "max_decomposition_depth": 3,
    "operator_limit": 5,
    "response_tokens": 100,
    "format": "JSON",
    "confidence_threshold": 0.7
  },
  "context": {
    "current_state": {...},
    "previous_operators": [...],
    "domain": "systems_optimization"
  }
}

LLM streams response:
{
  "operators": [
    {
      "name": "index-frequently-accessed-columns",
      "confidence": 0.92,
      "rationale": "Based on query patterns"
    },
    {
      "name": "partition-large-table",
      "confidence": 0.88,
      "rationale": "Reduces scan scope"
    }
  ],
  "elaborated_attributes": {
    "optimization_type": "structural",
    "risk_level": "low"
  },
  "impasse_resolution": true,
  "explanation_tokens": 87
}
```

**Recommendation**: Start with **Pattern A (Proposal-Elaboration)** because:
- ✓ Preserves SOAR's decision authority
- ✓ Impasse detection is natural (when it happens)
- ✓ LLM validates reasoning, doesn't dominate it
- ✓ Easier to add constraints and validation
- ✓ Clear responsibility boundary

---

### Constraint Mechanisms: From Verbose to Structured

#### Problem: LLM Verbosity vs. SOAR Requirements

**Without Constraints** (LLM outputs):
```
"The system could potentially employ several strategies
to optimize performance. One approach might be to consider
indexing frequently accessed columns, which could significantly
improve query response times in many scenarios. Additionally,
partitioning large tables might be beneficial, although this
depends on specific access patterns and data distribution..."
```

**SOAR needs**:
```json
{
  "operators": ["index-columns", "partition-table"],
  "scores": [0.92, 0.88],
  "confidence": 0.90
}
```

#### Solution 1: Structured Output Enforcement

```python
# SOAR-LLM Interface with Constraints
class SOARLLMInterface:
    def __init__(self):
        self.constraint_schema = {
            "type": "object",
            "properties": {
                "operators": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "maxLength": 50},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "attributes": {"type": "object"}
                        },
                        "required": ["name", "confidence"]
                    },
                    "maxItems": 5,  # Limit to top-5 operators
                    "minItems": 1
                },
                "elaborated_state": {
                    "type": "object",
                    "description": "New WM elements to add"
                },
                "impasse_resolved": {"type": "boolean"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1}
            },
            "required": ["operators", "impasse_resolved", "confidence"]
        }

    def call_llm_with_constraints(self, goal, current_state, candidate_operators):
        """
        Calls LLM with hard constraints on response format
        """
        # Build constrained prompt
        prompt = self._build_constrained_prompt(
            goal=goal,
            state=current_state,
            operators=candidate_operators,
            constraints=self.constraint_schema
        )

        # Call LLM with JSON mode and token limit
        response = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # Lower temperature for more deterministic output
            max_tokens=150,   # Hard token limit
            response_format={"type": "json_object"},  # Enforce JSON
            timeout=2.0       # Timeout for real-time requirements
        )

        # Parse and validate
        parsed = json.loads(response.choices[0].message.content)
        validated = jsonschema.validate(parsed, self.constraint_schema)

        return validated

    def _build_constrained_prompt(self, goal, state, operators, constraints):
        """
        Builds a prompt that guides LLM to structured output
        """
        return f"""
TASK: Decompose the goal into operators that SOAR can execute.

GOAL: {goal}

CURRENT STATE:
{json.dumps(state, indent=2)}

CANDIDATE OPERATORS DETECTED:
{', '.join(operators)}

CONSTRAINTS:
- Response must be valid JSON (no markdown, no explanation)
- Maximum 5 operators in result
- Each operator must have: name (string), confidence (0.0-1.0)
- No lengthy explanations; be concise

OUTPUT FORMAT (JSON ONLY):
{{
  "operators": [
    {{"name": "operator-name", "confidence": 0.95}},
    ...
  ],
  "elaborated_state": {{}},
  "impasse_resolved": true,
  "confidence": 0.90
}}

DO NOT INCLUDE ANY TEXT OUTSIDE THE JSON BLOCK.
"""
```

#### Solution 2: Token Budget Enforcement

```python
class TokenBudgetConstraint:
    """
    Limits LLM response to achieve real-time responsiveness
    """
    def __init__(self, max_input_tokens=500, max_output_tokens=100):
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens

    def apply_to_prompt(self, prompt):
        """Truncate prompt if it exceeds budget"""
        encoder = tiktoken.encoding_for_model("gpt-4")
        tokens = encoder.encode(prompt)

        if len(tokens) > self.max_input_tokens:
            # Truncate, keeping critical info
            truncated = encoder.decode(tokens[:self.max_input_tokens])
            logger.warning(f"Prompt truncated from {len(tokens)} to {self.max_input_tokens} tokens")
            return truncated
        return prompt

    def enforce_output_limit(self, llm_response):
        """Ensure output doesn't exceed token budget"""
        encoder = tiktoken.encoding_for_model("gpt-4")
        tokens = encoder.encode(llm_response)

        if len(tokens) > self.max_output_tokens:
            # Parse JSON and limit arrays
            parsed = json.loads(llm_response)
            parsed["operators"] = parsed["operators"][:3]  # Keep only top-3
            return json.dumps(parsed)
        return llm_response
```

#### Solution 3: Few-Shot Prompting with Examples

```python
def build_few_shot_prompt(goal, state, operators):
    """
    Use examples to guide LLM toward concise, structured output
    """
    examples = [
        {
            "goal": "Optimize query performance",
            "state": {"query_time": "5s", "operations": "table_scan"},
            "output": {
                "operators": [
                    {"name": "add-index", "confidence": 0.95},
                    {"name": "partition-table", "confidence": 0.82}
                ],
                "impasse_resolved": True,
                "confidence": 0.90
            }
        },
        {
            "goal": "Reduce memory usage",
            "state": {"memory_usage": "80%", "process": "caching"},
            "output": {
                "operators": [
                    {"name": "clear-cache", "confidence": 0.88},
                    {"name": "optimize-data-structures", "confidence": 0.85}
                ],
                "impasse_resolved": True,
                "confidence": 0.87
            }
        }
    ]

    prompt = "Given these examples:\n\n"
    for ex in examples:
        prompt += f"Goal: {ex['goal']}\n"
        prompt += f"Output: {json.dumps(ex['output'])}\n\n"

    prompt += f"Now, for:\nGoal: {goal}\nOutput:"

    return prompt
```

**Summary of Constraint Mechanisms**:
1. **Schema Validation** - Enforce JSON structure before acceptance
2. **Token Budgets** - Hard limits on input/output tokens
3. **Array Size Limits** - Maximum 5 operators returned
4. **Confidence Thresholds** - Only return high-confidence operators
5. **Few-Shot Examples** - Guide LLM via examples
6. **Timeout Enforcement** - Real-time responsiveness requirements

---

### Validation Logic: How SOAR Validates LLM Output

```python
class SOARLLMValidator:
    """
    Validates LLM output before assimilation into working memory
    """

    def validate_response(self, llm_output, current_state, goal_context):
        """
        Multi-level validation before SOAR accepts operators
        """
        validation_results = {
            "schema_valid": False,
            "semantic_valid": False,
            "consistency_valid": False,
            "novelty_check": False,
            "overall_valid": False,
            "issues": []
        }

        # Level 1: Schema Validation
        try:
            jsonschema.validate(llm_output, CONSTRAINT_SCHEMA)
            validation_results["schema_valid"] = True
        except jsonschema.ValidationError as e:
            validation_results["issues"].append(f"Schema error: {e.message}")
            return validation_results

        # Level 2: Semantic Validity
        # Check if operators are known or plausible
        for operator in llm_output["operators"]:
            op_name = operator["name"]

            # Check against known operators
            if not self._is_plausible_operator(op_name, goal_context):
                validation_results["issues"].append(
                    f"Operator '{op_name}' not plausible for goal '{goal_context}'"
                )

            # Check confidence is justified
            if operator["confidence"] > 0.9 and not self._is_high_confidence_justified(
                op_name, current_state, goal_context
            ):
                validation_results["issues"].append(
                    f"Confidence {operator['confidence']} unjustified for '{op_name}'"
                )

        validation_results["semantic_valid"] = len(validation_results["issues"]) == 0

        # Level 3: Consistency Check
        # Ensure operators don't contradict each other
        operator_names = [op["name"] for op in llm_output["operators"]]
        if self._operators_contradict(operator_names):
            validation_results["issues"].append(
                f"Operators contradict: {operator_names}"
            )
        validation_results["consistency_valid"] = len(validation_results["issues"]) == 0

        # Level 4: Novelty Check
        # Track what LLM has suggested before (avoid repetition)
        prev_operators = self._get_previous_llm_suggestions(goal_context, limit=5)
        repeated = [op for op in operator_names if op in prev_operators]

        if len(repeated) == len(operator_names):
            validation_results["issues"].append(
                f"All operators were previously suggested: {repeated}"
            )
            # This triggers deeper exploration in next impasse

        validation_results["novelty_check"] = len(repeated) < len(operator_names)

        # Overall validation
        validation_results["overall_valid"] = (
            validation_results["schema_valid"] and
            validation_results["semantic_valid"] and
            validation_results["consistency_valid"]
            # Novelty check doesn't block, just warns
        )

        return validation_results

    def _is_plausible_operator(self, op_name, goal_context):
        """Check if operator is known or domain-plausible"""
        # Check knowledge base of known operators for this domain
        domain = goal_context.get("domain", "general")
        known_ops = self.operator_kb.get(domain, set())

        if op_name in known_ops:
            return True

        # Check if it matches known patterns
        if self._matches_operator_pattern(op_name):
            return True

        return False

    def _operators_contradict(self, operator_list):
        """
        Check if operators contradict (e.g., encrypt-data and send-unencrypted)
        """
        contradictions = [
            {"encrypt-data", "send-unencrypted"},
            {"cache-response", "disable-cache"},
            {"optimize-performance", "add-logging"},  # May contradict
        ]

        op_set = set(operator_list)
        return any(contradiction.issubset(op_set) for contradiction in contradictions)

    def _get_previous_llm_suggestions(self, goal_context, limit=5):
        """Get previous operators LLM suggested for this goal"""
        return self.suggestion_history.get(goal_context.get("goal_id"), [])[-limit:]
```

**Validation Levels**:
1. **Schema Validation** - JSON structure correct?
2. **Semantic Validity** - Operators make sense for the goal?
3. **Consistency** - Do operators contradict?
4. **Novelty** - Is LLM repeating itself?

---

### Boundary Definition: SOAR vs. LLM Reasoning

```
┌─────────────────────────────────────────────────────────┐
│           RESPONSIBILITY BOUNDARY MATRIX                │
├─────────────────────────────────────────────────────────┤
│ REASONING TASK         │ SOAR    │ LLM     │ SHARED     │
├────────────────────────┼─────────┼─────────┼────────────┤
│ Define goal            │ ✓       │         │            │
│ State representation   │ ✓       │         │            │
│ Detect impasse         │ ✓       │         │            │
│ Propose operators      │ ✓       │ (in KB) │            │
│ Score operators        │ ✓       │ ✓       │ Sometimes  │
│ Elaborate operators    │ ✓       │ ✓       │ ✓          │
│ Add new attributes     │ ✓       │ ✓       │ ✓          │
│ Decompose goals        │         │ ✓       │            │
│ Generate text          │         │ ✓       │            │
│ Make final decision     │ ✓       │         │            │
│ Execute operator       │ ✓       │         │            │
│ Learn from outcome     │ ✓       │ ✓ (log) │ ✓          │
└────────────────────────┴─────────┴─────────┴────────────┘
```

**Clear SOAR Reasoning**:
- Goal formulation
- State change detection
- Impasse detection (when multiple operators tie)
- Preference memory (which operators worked before)
- Chunking (learning rules from experience)
- Decision authority

**Clear LLM Reasoning**:
- Semantic decomposition
- Generating plausible operators
- Natural language understanding
- Cross-domain analogies
- Creative problem-solving

**Shared/Negotiated**:
- Operator scoring (SOAR preference + LLM confidence)
- Attribute elaboration (LLM suggests, SOAR validates)
- Learning (SOAR chunks, LLM provides reasoning)

---

## GAP 2: ROBOTICS DOMAIN HANDLING

### The Problem: Physical Semantics vs. Symbolic Reasoning

**Issue**: SOAR is built for **symbolic reasoning** (goals, rules, symbols). Robotics requires **continuous control** (position, velocity, forces). How does AURORA bridge this?

```
BUSINESS LOGIC WORLD        VS.        ROBOTICS WORLD
├─ States: "approved",      ├─ States: positions,
│  "pending", "error"       │  orientations, forces
├─ Actions: "approve",      ├─ Actions: move(x,y,z),
│  "reject", "escalate"     │  grasp(force), rotate(angle)
├─ Semantics: symbolic      ├─ Semantics: physical
├─ Reasoning: discrete      ├─ Reasoning: continuous
├─ Time: event-driven       ├─ Time: real-time (10-100Hz)
└─ Evaluation: logical      └─ Evaluation: kinematic/dynamic
```

### Solution: Hybrid Symbolic-Continuous Architecture

#### Three-Layer Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    AURORA Robotics Stack                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  LAYER 1: SOAR SYMBOLIC REASONING                             │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Goals: "pick-object", "place-on-shelf"                │   │
│  │ Operators: "reach-for-object", "adjust-grip"          │   │
│  │ Impasse: Multiple way to pick (hand position ambig)   │   │
│  │ Decision: "reach-from-right" vs "reach-from-left"     │   │
│  │ Learns: Which approach works in tight spaces          │   │
│  └────┬─────────────────────────────────────────────────┘   │
│       │ (Commands abstract operators)                        │
│       ▼                                                       │
│  LAYER 2: TRAJECTORY PLANNING (LLM/RL)                        │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Input: "reach-from-right" with constraints             │   │
│  │ • Must avoid shelf edge (obstacle)                      │   │
│  │ • Must maintain grip (force bounds)                     │   │
│  │ • Time budget: 2 seconds                               │   │
│  │ Output: Joint angle trajectories                        │   │
│  │ • Via RRT*, STOMP, or neural network                   │   │
│  └────┬─────────────────────────────────────────────────┘   │
│       │ (Outputs smooth trajectories)                        │
│       ▼                                                       │
│  LAYER 3: CONTINUOUS CONTROL (PID, MPC)                      │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Executes trajectory at 100Hz                            │   │
│  │ Closes feedback loops (position, force)                 │   │
│  │ Handles disturbances in real-time                       │   │
│  │ Sensor fusion (cameras, force sensors, joint encoders)  │   │
│  └────────────────────────────────────────────────────────┘   │
│       │ (Proprioceptive feedback)                            │
│       ▼                                                       │
│  SENSING LAYER                                               │
│  ├─ Vision (where is object?)                               │
│  ├─ Force (is grip stable?)                                 │
│  ├─ Proprioception (where are joints?)                      │
│  └─ Tactile (contact detected?)                             │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

#### Domain-Specific Operator Representation

```python
class RobotOperator:
    """
    Extends SOAR operator with robotics-specific semantics
    """
    def __init__(self, name, goal_state):
        self.name = name                           # "reach-for-object"
        self.goal_state = goal_state                # State to achieve
        self.parameters = {}                        # Configurable aspects
        self.preconditions = {}                     # When applicable
        self.trajectory_planner = None              # How to execute
        self.feedback_controller = None             # How to stabilize

    def decompose(self):
        """
        In robotics: decompose into trajectory + controller
        """
        trajectory = self.trajectory_planner.plan(
            start=current_state,
            goal=self.goal_state,
            constraints=self.preconditions,
            parameters=self.parameters
        )

        controller = self.feedback_controller.create(
            trajectory=trajectory,
            tracking_error_threshold=0.01,  # 1cm acceptable error
            force_bounds=(0, 50)  # Newton limits
        )

        return {
            "trajectory": trajectory,      # Abstract to SOAR
            "controller": controller,      # Concrete execution
            "expected_duration": 2.5,      # seconds
            "success_criteria": [
                "object_in_gripper",
                "gripper_force_stable",
                "no_collision"
            ]
        }

class RobotState:
    """
    Robotics-specific state representation
    """
    def __init__(self):
        # Joint angles (symbolic for SOAR level)
        self.joint_angles = [0, 0, 0, 0, 0, 0]  # 6-DOF arm

        # End-effector pose (continuous)
        self.ee_position = [0.5, 0, 0.5]  # meters
        self.ee_orientation = [[1,0,0], [0,1,0], [0,0,1]]  # rotation matrix

        # Gripper state
        self.gripper_force = 0  # Newtons
        self.gripper_width = 0.1  # meters

        # Object tracking (symbolic + continuous)
        self.object_location = "shelf_1"  # Symbolic for SOAR
        self.object_pose = {
            "position": [0.6, 0.1, 0.3],  # Continuous for control
            "orientation": [[1,0,0], [0,1,0], [0,0,1]]
        }

        # Safety state
        self.collision_detected = False
        self.force_limit_exceeded = False
        self.trajectory_following_error = 0.005

    def get_symbolic_state(self):
        """SOAR-level symbolic abstraction"""
        return {
            "arm_position": self._discretize_position(),
            "gripper_status": "open" if self.gripper_width > 0.05 else "closed",
            "object_location": self.object_location,
            "safety_status": "safe" if not self.collision_detected else "unsafe"
        }

    def _discretize_position(self):
        """Map continuous position to symbolic state"""
        if self.ee_position[2] > 1.0:
            return "high"
        elif self.ee_position[2] > 0.5:
            return "mid"
        else:
            return "low"
```

#### SOAR-Robotics Integration Example

```python
class RoboticsSOARAgent(SOARAgent):
    """
    SOAR agent adapted for robotics domain
    """

    def __init__(self, robot):
        super().__init__()
        self.robot = robot  # Actual robot interface

        # Preload operator library for common tasks
        self._preload_operator_library()

    def _preload_operator_library(self):
        """
        Robotics: preload all feasible operator primitives
        No need for LLM to generate reach operations!
        """
        self.operators = {
            "reach": {
                "approach_directions": ["from_right", "from_left", "from_above"],
                "gripper_widths": [0.05, 0.08, 0.10],
                "speeds": ["slow", "normal", "fast"]
            },
            "grasp": {
                "forces": [5, 10, 20, 30, 40, 50],  # Newtons
                "widths": [0.05, 0.08, 0.10, 0.12]
            },
            "place": {
                "locations": ["shelf_1", "shelf_2", "table"],
                "orientations": ["upright", "tilted_45", "horizontal"]
            }
        }

    def detect_impasse_robotics(self):
        """
        Robotics-specific impasse detection
        """
        # Example: Multiple ways to reach an object
        current_goal = self.state.goal

        if current_goal == "pick-object":
            # Check if multiple approaches are feasible
            approach_options = self._get_feasible_approaches()

            if len(approach_options) > 1:
                # Impasse: multiple valid approaches
                # SOAR cannot decide which is best
                return True, approach_options

        return False, None

    def _get_feasible_approaches(self):
        """
        Generate feasible approaches given robot state
        """
        object_pose = self.state.object_pose
        robot_pose = self.state.ee_position

        feasible = []

        # Try each preloaded direction
        for direction in ["from_right", "from_left", "from_above"]:
            # Check kinematic feasibility
            ik_solution = self._solve_ik(object_pose, direction)

            if ik_solution and self._check_collision(ik_solution):
                feasible.append({
                    "direction": direction,
                    "joint_angles": ik_solution,
                    "expected_time": self._estimate_time(ik_solution)
                })

        return feasible

    def resolve_robotics_impasse_with_llm(self, approach_options):
        """
        When SOAR can't decide: ask LLM to refine choice
        """
        prompt = f"""
        Robot must pick object at {self.state.object_pose["position"]}.

        Available approaches:
        1. From right: 2.1 seconds, tight fit
        2. From left: 1.8 seconds, more stable
        3. From above: 2.5 seconds, obstacle risk

        Current context:
        - Gripper at: {self.state.ee_position}
        - Previous success rate (from-left): 95%
        - Previous success rate (from-right): 87%
        - Object shape: cylindrical

        Which approach should be tried first? (one word: right, left, above)
        """

        response = llm.call(prompt)
        selected = response.strip().lower()

        # Map back to SOAR preference
        direction_map = {
            "right": "from_right",
            "left": "from_left",
            "above": "from_above"
        }

        return direction_map.get(selected, "from_left")

    def execute_operator_continuous(self, operator_name, params):
        """
        Execute operator: abstract SOAR operator → continuous control
        """
        if operator_name == "reach":
            # Expand to trajectory
            trajectory = self._plan_trajectory(params)
            # Execute with continuous control
            self.robot.execute_trajectory(trajectory)

        elif operator_name == "grasp":
            # Direct to gripper controller
            self.robot.set_gripper_force(params["force"])
            self.robot.set_gripper_width(params["width"])

        elif operator_name == "place":
            # Combination: move to location + open gripper
            self._move_to_location(params["location"])
            self.robot.open_gripper()
```

#### Learning in Robotics Domain

```python
class RoboticsLearning:
    """
    How SOAR + LLM learn from robotics experience
    """

    def chunk_successful_trajectory(self, operator_name, approach_used):
        """
        SOAR-style chunking: turn successful sequence into rule
        """
        # Record: what worked
        chunk = {
            "goal": "pick-object",
            "state": self.state.get_symbolic_state(),
            "operator": operator_name,
            "approach": approach_used,
            "outcome": "success",
            "duration": 2.1,
            "collisions": 0
        }

        # Create SOAR rule (production)
        rule = f"""
        (p reach-object-{approach_used}
            (goal ^name pick-object)
            (object ^location shelf_1)
            (gripper ^status open)
            -->
            (operator ^name reach ^direction {approach_used})
        )
        """

        self.soar_agent.add_production(rule)

    def log_for_llm_learning(self, episode):
        """
        Log experience for LLM to learn patterns
        """
        self.experience_log.append({
            "goal": episode["goal"],
            "initial_state": episode["state"],
            "approach_chosen": episode["approach"],
            "success": episode["outcome"] == "success",
            "metrics": {
                "duration": episode["duration"],
                "collisions": episode["collisions"],
                "force_peak": episode["max_force"]
            }
        })

        # Periodically, LLM analyzes patterns
        if len(self.experience_log) % 100 == 0:
            self._analyze_patterns_with_llm()

    def _analyze_patterns_with_llm(self):
        """
        Ask LLM: what patterns explain success/failure?
        """
        successes = [e for e in self.experience_log[-100:] if e["success"]]
        failures = [e for e in self.experience_log[-100:] if not e["success"]]

        prompt = f"""
        Analyze these robotics task attempts.

        Successful attempts: {len(successes)}
        - Most common approach: {self._most_common_approach(successes)}
        - Average duration: {self._avg_duration(successes):.2f}s

        Failed attempts: {len(failures)}
        - Most common approach: {self._most_common_approach(failures)}
        - Common failure mode: collision

        What pattern explains the success rate difference?
        """

        pattern = llm.call(prompt)
        logger.info(f"LLM learned pattern: {pattern}")
```

### Robotics vs. Business Logic: Adaptation Strategy

```
ASPECT              BUSINESS LOGIC      ROBOTICS
─────────────────────────────────────────────────────
Operator Library    Generated by LLM    Preloaded (kinematic safety)
State Space         Symbolic discrete   Symbolic + Continuous
Time Constraints    Flexible            Real-time (10-100Hz)
Impasse Detection   Preference tie      Kinematic ambiguity
Learning Speed      Slower (safety)     Faster (physics predictable)
LLM Role            Generate operators  Refine choice / learn patterns
Validation Level    Semantic logic      Kinematic + collision safety
Error Recovery      Backtrack + retry   Physical recovery (safety first)
```

---

## GAP 3: IMPASSE DETECTION IN DECOMPOSITION

### The Core Problem

**Current Architecture Issue**:
```
SOAR Impasse Definition: "Multiple operators have equal preference"

But when decomposing with LLM:
- LLM returns a list of operators
- There's no "tying" happening
- So when does impasse occur?
```

### Solution: Multi-Level Impasse Detection

#### Level 1: Classical SOAR Impasse (No Decomposition Needed)

```
State:
  (goal ^name solve-problem)
  (problem ^complexity low)
  (candidate-operators ^name a ^name b)
  (preferences
    ^a.desirable
    ^b.desirable
  )

Result: IMPASSE (both A and B have equal preference)

Action: Decompose into sub-operators
  "Why is A desirable?" → "Handles edge case X"
  "Why is B desirable?" → "Faster execution"

Decision: Choose based on LLM elaboration
```

#### Level 2: Decomposition-Insufficient Impasse

```
Scenario: LLM's decomposition doesn't resolve impasse

Example:
  Goal: "Optimize database"

  LLM suggests:
  1. Add-index (confidence: 0.85)
  2. Partition-table (confidence: 0.85)  ← TIED!

  SOAR Result: Impasse again! Decomposition didn't help.

  Action: Go deeper
  - Ask: "How do these approaches differ?"
  - Ask: "Which handles growth better?"
  - Ask: "What are failure modes of each?"
```

#### Level 3: Ill-Defined Goal Impasse

```
Scenario: Goal is ambiguous, multiple valid interpretations

Goal: "Improve user experience"

LLM decomposes to:
  Approach A: "Reduce latency"
  Approach B: "Add features"
  Approach C: "Improve UI aesthetics"

Result: Three equally valid directions → IMPASSE

Action: Redefine goal with constraints
  "Improve UX within 5% perf budget"
  → Narrows to: reduce latency (forced by constraint)
```

#### Level 4: Resource Constraint Impasse

```
Scenario: Multiple feasible approaches but resource-limited

Example (Robotics):
  Goal: "Pick object from shelf"

  Approaches:
  1. Reach-from-right (2.1s, smooth)
  2. Reach-from-left (1.8s, risky collision)
  3. Reach-from-above (2.5s, slow but safe)

  Constraint: "Must complete in 2 seconds"

  Result: Only approach 2 feasible → IMPASSE resolved by constraint
  But approach 2 is risky!

  Action: Relax constraint OR accept risk
```

### Impasse Detection Algorithm

```python
class SOARImpasseDetector:
    """
    Detect impasses at multiple levels
    """

    def detect_impasse(self, current_state, candidate_operators):
        """
        Return: (has_impasse, type, operators_involved, resolution_strategy)
        """

        # Level 1: Preference Tie
        if self._has_preference_tie(candidate_operators):
            return True, "preference_tie", candidate_operators, {
                "strategy": "decompose_preference",
                "ask_llm": "Why is each operator desirable?"
            }

        # Level 2: All operators equal score
        scores = [op.get_score() for op in candidate_operators]
        if len(set(scores)) == 1:
            return True, "all_equal_score", candidate_operators, {
                "strategy": "deeper_decomposition",
                "ask_llm": "How do these operators differ in outcome?"
            }

        # Level 3: No clear winner after elaboration
        top_score = max(scores)
        near_top = [op for op in candidate_operators if op.get_score() >= top_score - 0.05]

        if len(near_top) > 1:
            return True, "unclear_winner", near_top, {
                "strategy": "distinguish_operators",
                "ask_llm": "What would make each approach succeed or fail?"
            }

        # Level 4: Resource constraints eliminate all but one feasible
        feasible = [op for op in candidate_operators if self._is_feasible(op)]

        if len(feasible) == 1 and len(candidate_operators) > 1:
            return True, "constraint_forced", [candidate_operators], {
                "strategy": "relax_or_accept",
                "note": f"Constraint eliminated {len(candidate_operators)-1} options"
            }

        # No impasse
        return False, None, [], {}

    def _has_preference_tie(self, operators):
        """Check if multiple operators have equal preference"""
        preferences = [op.preference for op in operators]
        return len(set(preferences)) == 1 and len(set(preferences)) > 1

    def _is_feasible(self, operator):
        """Check if operator can be executed given constraints"""
        return operator.check_constraints()

class ImpasseResolutionStrategy:
    """
    Different strategies for different impasse types
    """

    def resolve_preference_tie(self, operators):
        """
        Impasse Type 1: Multiple operators have same preference
        Strategy: Ask LLM to elaborate on preferences
        """
        prompt = f"""
        These operators are equally preferred:
        {[op.name for op in operators]}

        Current goal: {self.goal}
        Current state attributes: {self.state.attributes}

        For each operator, explain:
        1. What does it achieve?
        2. What are risks/side-effects?
        3. What is the best case / worst case outcome?

        Based on the current state, which is most likely to succeed?
        """

        llm_analysis = llm.call(prompt)

        # Score operators based on LLM analysis
        scores = self._parse_confidence_scores(llm_analysis)

        # Return ranked operators
        return sorted(zip(operators, scores), key=lambda x: x[1], reverse=True)

    def resolve_unclear_winner(self, operators):
        """
        Impasse Type 2: No clear winner among similar-scoring operators
        Strategy: Distinguish based on secondary criteria
        """
        prompt = f"""
        Several operators are close in quality:
        {[(op.name, op.score) for op in operators]}

        What would distinguish them? Consider:
        1. Speed: How long does each take?
        2. Reliability: How often does it succeed?
        3. Side-effects: What else changes?
        4. Future options: Does it enable other operators?

        If you had to rank them, which would be first?
        """

        ranking = llm.call(prompt)
        # Extract ranking and map back to operators
        return self._parse_ranking(ranking, operators)

    def resolve_constraint_conflict(self, operators, constraint):
        """
        Impasse Type 3: Only one operator satisfies constraints
        Strategy: Relax constraint or accept forced choice
        """
        feasible = [op for op in operators if op.satisfies(constraint)]

        if len(feasible) == 0:
            # No operator satisfies constraint
            prompt = f"""
            Constraint: {constraint}
            None of these operators satisfy it: {[op.name for op in operators]}

            Options:
            1. Relax the constraint (how?)
            2. Modify operators to satisfy constraint (how?)
            3. Accept constraint violation

            What should SOAR do?
            """
            return llm.call(prompt)

        elif len(feasible) == 1:
            # Only one satisfies constraint
            logger.info(f"Constraint forces operator: {feasible[0].name}")
            return feasible[0]
```

### Impasse Trees: Visualization

```
Example 1: Business Logic (Goal: Approve Request)
═══════════════════════════════════════════════════

┌─ Goal: approve-request
│
├─ Level 0: Propose candidates
│  ├─ auto-approve (score: 0.7)
│  ├─ manual-review (score: 0.7)     ← IMPASSE (tied)
│  └─ escalate (score: 0.3)
│
├─ IMPASSE DETECTED: auto-approve ≈ manual-review
│
├─ LLM Elaboration:
│  ├─ "auto-approve" risks: Could approve fraud
│  ├─ "manual-review" cost: Takes 10 minutes
│  └─ Question: Is fraud risk > review cost?
│
├─ LLM Response: "Fraud risk is higher, use manual-review"
│
└─ Resolution: manual-review (score boosted to 0.95)


Example 2: Robotics (Goal: Pick Object)
═════════════════════════════════════════

┌─ Goal: pick-object from shelf
│
├─ Level 0: Feasible approaches
│  ├─ reach-from-right (1.8s, score: 0.85)
│  ├─ reach-from-left (1.9s, score: 0.85)      ← IMPASSE (tied)
│  └─ reach-from-above (2.3s, score: 0.70)
│
├─ IMPASSE: Two equally good approaches
│
├─ Apply Constraint: "Must complete in 2 seconds"
│  ├─ reach-from-right: 1.8s ✓ satisfies
│  ├─ reach-from-left: 1.9s ✓ satisfies
│  └─ reach-from-above: 2.3s ✗ fails
│
├─ Still tied! Use secondary criterion
│
├─ LLM: "History: right=92% success, left=88% success"
│       → "Choose right, less risky"
│
└─ Resolution: reach-from-right


Example 3: Deep Decomposition (Goal: Optimize Database)
════════════════════════════════════════════════════════

┌─ Goal: optimize-query-performance
│
├─ Level 1 Impasse
│  ├─ add-index (score: 0.85)
│  └─ partition-table (score: 0.85)    ← IMPASSE
│
├─ LLM Elaboration Q1: "What are query patterns?"
│  └─ "80% queries on timestamp; 10% on user_id"
│
├─ LLM Elaboration Q2: "add-index solves 80% queries?"
│  └─ "Yes, index on timestamp"
│
├─ LLM Elaboration Q3: "partition-table solves what?"
│  └─ "Reduces table scan scope, helps with time-range queries"
│
├─ LLM Elaboration Q4: "Are there queries hitting both?"
│  └─ "Yes, ~5% of queries do range+user filter"
│
├─ LLM Decision: "add-index-on-timestamp (most queries)"
│                "Then partition (handles remainder)"
│
├─ SOAR Resolution: Sequence
│  1. Execute: add-index-on-timestamp
│  2. Evaluate: Did queries improve?
│  3. If yes, mark as learned rule
│  4. If no improvement, try partition-table
│
└─ Learning: Create SOAR production
   "If 80% queries use timestamp, add index first"
```

### Code Example: Complete Impasse Resolution

```python
class ImpasseResolutionController:
    """
    End-to-end impasse detection and resolution
    """

    def soar_decision_cycle(self):
        """Main SOAR cycle with impasse handling"""
        while self.active:
            # Standard SOAR phases
            current_state = self.input_phase()
            candidates = self.proposal_phase(current_state)

            # NEW: Impasse detection
            has_impasse, impasse_type, operators, strategy = \
                self.impasse_detector.detect_impasse(current_state, candidates)

            if not has_impasse:
                # No impasse: normal decision
                chosen = max(candidates, key=lambda op: op.score())
                self.execute_phase(chosen)
            else:
                # Has impasse: resolve via LLM elaboration
                logger.info(f"Impasse detected: {impasse_type}")

                if impasse_type == "preference_tie":
                    resolved = self.resolve_via_elaboration(operators)
                elif impasse_type == "unclear_winner":
                    resolved = self.distinguish_operators(operators)
                elif impasse_type == "constraint_forced":
                    resolved = self.handle_constraint_conflict(operators)
                else:
                    resolved = self.handle_ill_defined_goal()

                self.execute_phase(resolved)

            # Learning: Did operator work?
            self.learning_phase()

    def resolve_via_elaboration(self, operators):
        """Ask LLM to elaborate on tied operators"""

        # Step 1: Socratic questioning
        questions = [
            "What does each operator achieve?",
            "What are the risks of each?",
            "Which has highest probability of success?"
        ]

        responses = []
        for q in questions:
            prompt = f"""
            {q}

            Operators: {[op.name for op in operators]}
            Goal: {self.goal}
            Current state: {self.current_state}
            """
            response = llm.call(prompt)
            responses.append(response)

        # Step 2: Synthesize responses into scores
        elaboration = "\n".join(responses)

        score_prompt = f"""
        Based on this analysis:
        {elaboration}

        Score each operator 0.0-1.0:
        {[op.name for op in operators]}

        Return JSON: {{"operator_name": score, ...}}
        """

        scores_json = llm.call(score_prompt, format="json")
        scores = json.loads(scores_json)

        # Step 3: Apply scores and select
        for op in operators:
            op.elaboration_score = scores.get(op.name, op.score())

        chosen = max(operators, key=lambda op: op.elaboration_score)
        logger.info(f"Impasse resolved: chose {chosen.name} "
                   f"(elaboration_score: {chosen.elaboration_score:.2f})")

        return chosen

    def distinguish_operators(self, operators):
        """When operators are very close, find distinguishing factor"""

        prompt = f"""
        These operators are very close in quality:
        {[(op.name, op.score()) for op in operators]}

        What criteria would distinguish them?
        Consider: speed, reliability, side-effects, future options

        For current state {self.current_state},
        which operator is best?
        """

        analysis = llm.call(prompt)

        # Extract reasoning
        if "speed" in analysis.lower():
            criterion = "speed"
            chosen = min(operators, key=lambda op: op.estimated_time())
        elif "reliability" in analysis.lower():
            criterion = "reliability"
            chosen = max(operators, key=lambda op: op.success_rate())
        else:
            chosen = operators[0]  # Default to first

        logger.info(f"Distinguished by {criterion}: chose {chosen.name}")
        return chosen

    def handle_constraint_conflict(self, operators):
        """When constraint eliminates all but one option"""

        constraints = self.get_active_constraints()
        feasible = [op for op in operators if op.satisfies_all(constraints)]

        if len(feasible) == 0:
            # Constraint is too strict: ask LLM to help
            prompt = f"""
            No operator satisfies constraints: {constraints}
            Available: {[op.name for op in operators]}

            Should we:
            1. Relax constraints? (which ones, how much?)
            2. Modify operators? (how?)
            3. Add new operators? (what?)

            Recommend: (one line)
            """
            recommendation = llm.call(prompt)
            logger.warning(f"Constraint conflict: {recommendation}")
            # Execute recommendation logic...

        elif len(feasible) == 1:
            logger.info(f"Constraint forces: {feasible[0].name}")
            return feasible[0]

        else:
            # Multiple feasible: pick best among feasible
            return max(feasible, key=lambda op: op.score())
```

---

## GAP 4: GENERIC ELICITATION QUESTIONS

### The Four Questions Framework

Based on AURORA's "4 generic questions":

```
Q1: "What is the goal?"
    Purpose: Define problem scope
    SOAR Action: Set up goal in WM
    LLM Action: Understand domain context
    Example: "Optimize database performance"

Q2: "What have you tried before?"
    Purpose: Leverage past experience
    SOAR Action: Query procedural memory (chunks)
    LLM Action: Retrieve relevant examples
    Example: "We tried indexing; it helped but didn't solve everything"

Q3: "What's preventing success?"
    Purpose: Identify bottlenecks/obstacles
    SOAR Action: Detect impasse or failure
    LLM Action: Analyze constraints
    Example: "Join latency is still 5 seconds; can't index join column"

Q4: "What should we try next?"
    Purpose: Generate new operators
    SOAR Action: Propose candidates
    LLM Action: Decompose goal into operators
    Example: "Consider query rewriting or table partitioning"
```

### State-Based Adaptation

```python
class AdaptiveElicitationEngine:
    """
    Adapts elicitation questions based on current state
    """

    def get_next_question(self, state):
        """
        Choose which question to ask based on where we are
        """

        if state.phase == "INITIAL":
            # At start: ask Q1 (What is the goal?)
            return self._question_1_define_goal()

        elif state.phase == "EXPLORATION":
            # After goal: ask Q2 (What have you tried?)
            return self._question_2_past_attempts(state)

        elif state.phase == "IMPASSE" and state.impasse_count < 3:
            # During impasse: ask Q3 (What's preventing?)
            return self._question_3_obstacles(state)

        elif state.phase == "IMPASSE" and state.impasse_count >= 3:
            # Deep impasse: ask Q4 (What should we try?)
            return self._question_4_generate_new(state)

        elif state.phase == "EVALUATION":
            # After trying something: assess
            return self._question_5_assess_outcome(state)

        return None

    def _question_1_define_goal(self):
        """Q1: What is the goal?"""
        return {
            "type": "definition",
            "question": "What is the primary goal we're trying to achieve?",
            "format": "open-ended",
            "llm_task": "Extract domain, constraints, success criteria",
            "soar_action": "Create goal WM element",
            "example_answer": "Reduce database query latency from 5s to <100ms"
        }

    def _question_2_past_attempts(self, state):
        """Q2: What have you tried before?"""
        return {
            "type": "exploration",
            "question": f"What approaches have been tried for {state.goal}?",
            "format": "list",
            "llm_task": "Recall similar problems, retrieve patterns",
            "soar_action": "Populate procedural memory candidates",
            "context": {
                "goal": state.goal,
                "previous_attempts": state.attempt_history,
                "success_rates": state.success_rates
            }
        }

    def _question_3_obstacles(self, state):
        """Q3: What's preventing success?"""
        return {
            "type": "diagnosis",
            "question": "What obstacles prevent achieving the goal?",
            "format": "root-cause analysis",
            "llm_task": "Analyze failure modes, identify bottlenecks",
            "soar_action": "Add obstacle WM elements, trigger new productions",
            "context": {
                "failed_operators": state.failed_attempts,
                "constraints": state.constraints,
                "metrics": state.current_metrics
            }
        }

    def _question_4_generate_new(self, state):
        """Q4: What should we try next?"""
        return {
            "type": "generation",
            "question": "What new approaches haven't been tried?",
            "format": "operator generation",
            "llm_task": "Generate novel decompositions, cross-domain analogies",
            "soar_action": "Add new operators to proposal phase",
            "constraints": {
                "avoid_previous": state.tried_operators,
                "feasibility": state.feasibility_check,
                "time_budget": state.time_budget
            }
        }

    def _question_5_assess_outcome(self, state):
        """After executing an operator: Did it work?"""
        return {
            "type": "evaluation",
            "question": f"Did {state.last_operator} improve the goal?",
            "format": "metrics comparison",
            "llm_task": "Assess outcome, identify partial progress",
            "soar_action": "Update operator scoring, trigger learning",
            "metrics": {
                "before": state.initial_metrics,
                "after": state.current_metrics,
                "improvement": state.improvement_percentage
            }
        }

class PromptTemplates:
    """
    Prompt templates for each question, adaptable to domain
    """

    @staticmethod
    def q1_for_business_logic():
        return """
        What is the business goal?

        Example:
          "Reduce invoice processing time from 3 days to 24 hours"

        Provide:
        - Goal statement
        - Current state metric
        - Target state metric
        - Constraints (budget, compliance, etc)
        """

    @staticmethod
    def q1_for_robotics():
        return """
        What is the robot task?

        Example:
          "Pick objects from shelf and place in bin"

        Provide:
        - Task description
        - Object types
        - Environmental constraints (space, obstacles)
        - Safety requirements
        """

    @staticmethod
    def q2_with_history(domain, goal, history):
        return f"""
        For goal: "{goal}" in {domain}

        Previous attempts:
        {json.dumps(history, indent=2)}

        What patterns do you notice?
        - Which approaches worked well?
        - Which failed? Why?
        - What was learned?
        """

    @staticmethod
    def q3_with_state(goal, failed_ops, current_state):
        return f"""
        Goal: {goal}
        Failed operators: {failed_ops}
        Current state: {json.dumps(current_state, indent=2)}

        Root cause analysis:
        - Why did previous operators fail?
        - What constraints prevent success?
        - What is the bottleneck?
        """

    @staticmethod
    def q4_generate_novel(goal, tried_operators, domain):
        return f"""
        Goal: {goal}
        Tried: {tried_operators}
        Domain: {domain}

        Generate NEW approaches:
        - Cross-domain analogies (how is this solved elsewhere?)
        - Creative combinations (what if we combine approaches?)
        - Constraint relaxation (what if we had more resources?)

        Return: Top 3 novel ideas, each with rationale
        """
```

### When to Use vs. When to Use Agents

```
SCENARIO                    USE ELICITATION QUESTIONS    OR    USE AGENT
─────────────────────────────────────────────────────────────────────────
Simple task, clear goal     ✓ Fast (30 sec)                 ✗ Overkill
Complex task, unclear goal  ✗ Too generic                   ✓ Use orchestrator
Familiar domain             ✓ Rules sufficient              ✗ Unnecessary
Novel domain                ✗ No rules yet                  ✓ Use market-researcher
Quick decision needed       ✓ Fast iteration                ✗ Too slow
Deep analysis required      ✗ Insufficient depth           ✓ Use specialist
User has expertise          ✓ Question + feedback           ✗ Assume knowledge
User is learning            ✗ Too fast                     ✓ Mentoring mode
Robotics task               ✓ For decomposition             ✓ For control
Business logic              ✓ For elaboration              ✓ For process design
```

---

## GAP 5: CLARIFIED RESPONSIBILITIES

### Responsibility Matrix (Detailed)

```python
class ResponsibilityFramework:
    """
    Clear definition of what each component does
    """

    SOAR_RESPONSIBILITIES = {
        "goal_management": {
            "description": "Define, maintain, and pursue goals",
            "examples": [
                "Create goal: pick-object",
                "Maintain goal hierarchy",
                "Detect goal completion"
            ],
            "soar_mechanism": "Goal WM elements, proposal phase"
        },

        "state_representation": {
            "description": "Maintain accurate world state",
            "examples": [
                "Track object positions",
                "Record action outcomes",
                "Detect state changes"
            ],
            "soar_mechanism": "Working memory (WM)"
        },

        "impasse_detection": {
            "description": "Detect when normal reasoning fails",
            "examples": [
                "Multiple operators tie in preference",
                "No operators applicable",
                "Decomposition didn't help"
            ],
            "soar_mechanism": "Impasse detection algorithm"
        },

        "preference_reasoning": {
            "description": "Apply learned preferences and rules",
            "examples": [
                "Apply decision preferences",
                "Use chunks from past experience",
                "Score operators via productions"
            ],
            "soar_mechanism": "Production system"
        },

        "decision_authority": {
            "description": "Make final choice among candidates",
            "examples": [
                "Choose operator to execute",
                "Commit to operator even if risky",
                "Make preference final"
            ],
            "soar_mechanism": "Decision cycle"
        },

        "execution_control": {
            "description": "Execute operators and monitor outcomes",
            "examples": [
                "Call motor system to execute",
                "Monitor feedback from execution",
                "Detect execution failures"
            ],
            "soar_mechanism": "Output link"
        },

        "learning": {
            "description": "Learn from experience via chunking",
            "examples": [
                "Create rule from successful sequence",
                "Learn operator order",
                "Learn context-dependent strategies"
            ],
            "soar_mechanism": "Chunking mechanism"
        }
    }

    LLM_RESPONSIBILITIES = {
        "semantic_understanding": {
            "description": "Understand natural language and domain concepts",
            "examples": [
                "Parse: 'pick object from high shelf'",
                "Understand: safety implications",
                "Map: natural language → SOAR concepts"
            ],
            "interface": "Text-based input"
        },

        "decomposition": {
            "description": "Break down goals into sub-goals/operators",
            "examples": [
                "Goal: 'optimize database'",
                "Decompose to: [index, partition, rewrite-query]",
                "Generate plausible operators"
            ],
            "interface": "Return structured operator list"
        },

        "elaboration": {
            "description": "Explain and refine operators",
            "examples": [
                "Why is operator A better than B?",
                "What are side-effects?",
                "What attributes matter?"
            ],
            "interface": "Respond to questions"
        },

        "confidence_estimation": {
            "description": "Estimate likelihood of success",
            "examples": [
                "Confidence: 0.92 for add-index",
                "Confidence: 0.75 for partition",
                "Low confidence means risky"
            ],
            "interface": "Return confidence score (0.0-1.0)"
        },

        "cross_domain_analogy": {
            "description": "Apply knowledge from other domains",
            "examples": [
                "Database optimization ~ Code optimization",
                "Robot pick ~ Surgical precision",
                "Transfer patterns across domains"
            ],
            "interface": "Suggest novel approaches"
        },

        "text_generation": {
            "description": "Generate explanations and reports",
            "examples": [
                "Explain why operator A was chosen",
                "Report on execution outcome",
                "Create documentation"
            ],
            "interface": "Text output"
        }
    }

    ACT_R_RESPONSIBILITIES = {
        "memory_management": {
            "description": "Manage declarative and procedural memory",
            "examples": [
                "Activation levels of memories",
                "Decay of unused knowledge",
                "Speed of memory retrieval"
            ],
            "actr_mechanism": "Memory modules"
        },

        "learning_mechanisms": {
            "description": "Learn and update memory",
            "examples": [
                "Strengthen memories with use",
                "Update weights of memory traces",
                "Create new memory entries"
            ],
            "actr_mechanism": "Learning rules"
        },

        "perceptual_motor": {
            "description": "Perceive world and execute actions",
            "examples": [
                "See objects via vision",
                "Hear commands via audio",
                "Execute movements via motor system"
            ],
            "actr_mechanism": "Perceptual-motor modules"
        }
    }

    SOAR_ASSIST_RESPONSIBILITIES = {
        "orchestration": {
            "description": "Coordinate SOAR, LLM, and ACT-R",
            "examples": [
                "When should LLM be called?",
                "How to pass information between systems?",
                "How to handle conflicts?"
            ]
        },

        "interface_management": {
            "description": "Translate between SOAR and LLM",
            "examples": [
                "Format SOAR state for LLM",
                "Parse LLM output for SOAR",
                "Validate compatibility"
            ]
        },

        "constraint_enforcement": {
            "description": "Enforce constraints across systems",
            "examples": [
                "Token budget limits",
                "Time budget limits",
                "Consistency constraints"
            ]
        }
    }
```

### Interaction Flowcharts

```
SCENARIO 1: Normal SOAR Operation (No LLM Needed)
═════════════════════════════════════════════════

┌─ SOAR Goal: pick-object
│
├─ Proposal Phase: Match rules → find operators
│  └─ Rule fires: "If object-in-sight and gripper-empty, propose reach"
│
├─ Elaboration Phase: Score operators
│  └─ Production: "reach has high preference (0.9)"
│  └─ Alternative: "move-closer has low preference (0.4)"
│
├─ Decision: No impasse (reach wins clearly)
│
└─ Execute: reach (SOAR calls motor system)


SCENARIO 2: Impasse → LLM Elaboration
══════════════════════════════════════

SOAR Side                          LLM Side
────────────────────────────────────────────────────

1. Proposal → propose
   - add-index (score: 0.8)
   - partition-table (score: 0.8)

2. Detect Impasse ──┐
                    │
                    ├─→ SOAR-Assist ──→ Format for LLM
                    │                    "Two operators tied:
                    │                     add-index vs partition"
                    │
                    │                  2. LLM Elaborates
                    │                     "add-index handles 80% of
                    │                      queries; partition is
                    │                      infrastructure change"
                    │
                    │                  3. Return confidence
                    │                     add-index: 0.92
                    │                     partition: 0.71
                    │
                    │   ←─────────── LLM Output
                    │
3. Update WM ──────┘
   add-index (0.92) now wins!

4. Decision: add-index

5. Execute: create-index command


SCENARIO 3: Novel Domain → Question Loop
══════════════════════════════════════════

SOAR                           LLM
────────────────────────────────────────────────

1. Goal: solve-novel-problem

2. Proposal Phase
   └─ NO RULES FIRE
   └─ No candidates!

3. LLM Called ──→ "What operators exist?"
                  ← "I need more context"

4. Question Loop:
   Q1: "What's the goal?"  → "Optimize X"
   Q2: "What have you tried?" → "Nothing yet, novel"
   Q3: "What are constraints?" → "Time, budget"
   Q4: "Generate approaches" → [list of operators]

5. LLM returns operator list
   ← [operator-A, operator-B, operator-C]

6. Assimilate into WM
   Add new operators to proposal phase

7. Decision: propose all three, no preference
   → Impasse again! Go back to step 4
   → Ask: "Which operator is most promising?"
   → LLM: "operator-B, because..."

8. Execute: operator-B

9. Observe outcome

10. Learn: Create rule
    "If goal-is-X and situation-is-Y, try operator-B"
```

### When SOAR Delegates to LLM

```python
class SOARLLMDelegationPoints:
    """
    Explicit points where SOAR calls LLM
    """

    DELEGATION_POINTS = [
        {
            "trigger": "Impasse in proposal phase",
            "reason": "No rules fire → no operators proposed",
            "llm_task": "Generate plausible operators for goal",
            "example": "Goal: solve-novel-problem → No productions match"
        },
        {
            "trigger": "Preference tie (multiple operators)",
            "reason": "Cannot decide between equal-preference operators",
            "llm_task": "Elaborate and distinguish operators",
            "example": "Both add-index and partition score 0.8"
        },
        {
            "trigger": "No feasible operators",
            "reason": "All candidates violate constraints",
            "llm_task": "Suggest constraint relaxation or new operators",
            "example": "All operators exceed time budget"
        },
        {
            "trigger": "Repeated failures",
            "reason": "Same operator fails multiple times",
            "llm_task": "Suggest alternate approaches",
            "example": "add-index didn't help; try partitioning"
        },
        {
            "trigger": "High-level goal decomposition",
            "reason": "Goal is abstract and needs sub-goals",
            "llm_task": "Decompose goal into concrete sub-goals",
            "example": "Goal: improve-system-reliability → [ensure-backups, ...]"
        },
        {
            "trigger": "User asks 'why'",
            "reason": "Need to explain operator choice",
            "llm_task": "Generate explanation",
            "example": "User: 'Why add-index instead of partition?'"
        }
    ]
```

---

## ARCHITECTURAL AMBIGUITIES & PROPOSED SOLUTIONS

### Ambiguity 1: Is SOAR + LLM "Reasoning" or Just "Execution"?

**Problem**:
- SOAR has symbolic reasoning (rules, preferences)
- LLM has semantic reasoning (understanding, generation)
- Does combining them actually improve reasoning?

**Current Confusion**:
> "SOAR asks LLM for decomposition"
> This sounds like LLM is generating answers, SOAR is executing
> But that's not reasoning; that's execution following instructions

**Proposed Solution**:
```
REDEFINE: Reasoning happens at MULTIPLE LEVELS

Level 1: SOAR Symbolic Reasoning
- "Given these preferences, which operator is best?"
- Uses rules, learned preferences, past experience
- Is logic-based

Level 2: LLM Semantic Reasoning
- "What does this goal mean in this domain?"
- "What operators could possibly solve this?"
- Is language-based

Level 3: Collaborative Reasoning
- SOAR: "I can't decide between A and B"
- LLM: "A is for 80% of cases, B is for 20%"
- SOAR: "Current state matches 80% case, choose A"
- Neither system alone could reach this conclusion

CONCLUSION: Combined reasoning > either alone
```

### Ambiguity 2: When Does LLM Answer Questions vs. Generate from Scratch?

**Problem**:
- Sometimes LLM elaborates (answers "Why is A better?")
- Sometimes LLM generates new (answers "What should we try?")
- When should SOAR expect which?

**Proposed Solution**:
```
TIER 1: Elaboration (answer about existing operators)
- Use when: Multiple operators already proposed
- Expected: "A is better because...", "Side effects of B are..."
- Format: Structured explanation
- Token budget: 100 tokens

TIER 2: Generation (create new operators)
- Use when: No proposals made (impasse, novel domain)
- Expected: "[operator-1, operator-2, ...]"
- Format: JSON list with confidence
- Token budget: 150 tokens

TIER 3: Strategy (high-level approach)
- Use when: Goal is unclear or has multiple interpretations
- Expected: "Decompose goal into [subgoal-1, subgoal-2]"
- Format: Structured decomposition
- Token budget: 200 tokens

TIER 4: Explanation (generate text)
- Use when: User asks "Why?" or requires documentation
- Expected: Natural language explanation
- Format: Free text
- Token budget: Unlimited (not used during reasoning)
```

### Ambiguity 3: How Does SOAR Know When LLM Is Wrong?

**Problem**:
- LLM is confident but wrong (hallucination)
- How does SOAR detect and recover?

**Proposed Solution**:
```
VALIDATION LAYERS:

1. Schema Validation
   - Is output valid JSON?
   - Does it match expected structure?
   ACTION if fails: Reject, ask LLM to reformat

2. Semantic Validation
   - Are proposed operators plausible?
   - Do they match domain knowledge?
   ACTION if fails: Request operator clarification

3. Consistency Validation
   - Do operators contradict each other?
   - Do they match current state?
   ACTION if fails: Request reconciliation

4. Execution Validation
   - Did operator actually work?
   - Did outcome match LLM confidence?
   ACTION if fails: Lower LLM confidence, try alternatives

5. Learning Validation
   - Did pattern hold over multiple cases?
   - Can we generalize the rule?
   ACTION if fails: Don't chunk, retry manual selection
```

---

## IMPLEMENTATION ROADMAP

### Phase 1: Core SOAR-LLM Integration (Weeks 1-4)

```
[ ] 1.1 Implement Pattern A (Proposal-Elaboration)
[ ] 1.2 Add structured output enforcement (JSON schema)
[ ] 1.3 Create validation layer (4 levels)
[ ] 1.4 Define interaction protocol
[ ] 1.5 Test with business logic domain
```

### Phase 2: Robotics Adaptation (Weeks 5-8)

```
[ ] 2.1 Design hybrid symbolic-continuous architecture
[ ] 2.2 Preload operator library for robotics
[ ] 2.3 Implement trajectory planning layer
[ ] 2.4 Create robotics-specific impasse detection
[ ] 2.5 Test with real/simulated robot
```

### Phase 3: Impasse Resolution Strategies (Weeks 9-12)

```
[ ] 3.1 Implement multi-level impasse detection
[ ] 3.2 Create elaboration strategy
[ ] 3.3 Create distinction strategy
[ ] 3.4 Create constraint handling strategy
[ ] 3.5 Test with complex scenarios
```

### Phase 4: Elicitation Engine (Weeks 13-16)

```
[ ] 4.1 Implement 4-question framework
[ ] 4.2 Create state-based adaptation
[ ] 4.3 Build domain-specific prompt templates
[ ] 4.4 Add Socratic questioning loop
[ ] 4.5 Test with diverse domains
```

### Phase 5: Integration & Learning (Weeks 17-20)

```
[ ] 5.1 Integrate all components
[ ] 5.2 Implement chunking for robotics domain
[ ] 5.3 Create end-to-end scenarios
[ ] 5.4 Performance benchmarking
[ ] 5.5 Production hardening
```

---

## CONCLUSION

**Summary of Gaps Addressed**:

1. **SOAR-LLM Interaction**: Defined Pattern A with clear request/response cycle
2. **Constraints**: Token budgets, schema validation, few-shot prompting
3. **Robotics**: Three-layer architecture (symbolic → trajectory → control)
4. **Impasse Detection**: Multi-level detection with resolution strategies
5. **Elicitation**: Adaptive 4-question framework for different scenarios

**Key Clarifications**:

- **SOAR does**: Goal management, state, impasse detection, decision
- **LLM does**: Semantic understanding, decomposition, elaboration
- **Together**: Collaborative reasoning > either alone
- **Robotics**: Preload operator library, add continuous control layer
- **Validation**: Always validate LLM output before using

**Next Steps**:
1. Review and validate architecture with domain experts
2. Implement Phase 1 (4 weeks) with business logic domain
3. Validate with robotics domain (Phase 2)
4. Measure improvement in reasoning quality
5. Iterate based on results

