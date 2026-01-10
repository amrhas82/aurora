# AURORA Framework: Interaction Patterns & Code Examples
## Visual Reference Guide with Working Examples

---

## SECTION 1: SOAR-LLM INTERACTION PATTERNS (Visual Reference)

### Pattern A: Proposal-Elaboration (Recommended)

```
┌──────────────────────────────────────────────────────────────────┐
│                    SOAR Proposal-Elaboration Flow                │
└──────────────────────────────────────────────────────────────────┘

STEP 1: Input Phase
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SOAR reads sensors:
  ├─ Current state: database_slow, queries_taking_5s
  └─ Goal: optimize-performance

STEP 2: Proposal Phase
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SOAR matches productions:
  ├─ Production 1: IF goal=optimize AND state=slow → propose add-index
  │                 score: 0.8
  ├─ Production 2: IF goal=optimize AND state=slow → propose partition
  │                 score: 0.8    ← TIED!
  └─ Production 3: IF goal=optimize → propose analyze-query
                   score: 0.3

STEP 3: Detect Impasse
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SOAR detects:
  ├─ add-index and partition have same preference (0.8)
  ├─ No clear decision possible
  └─ IMPASSE! Require elaboration

STEP 4: Call LLM for Elaboration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SOAR sends:
  {
    "goal": "optimize-performance",
    "state": {
      "database_type": "postgresql",
      "current_latency_ms": 5000,
      "query_volume": "1M queries/day"
    },
    "candidates": [
      {"name": "add-index", "soar_score": 0.8},
      {"name": "partition-table", "soar_score": 0.8}
    ],
    "question": "Which approach is better for high-volume queries?"
  }

STEP 5: LLM Elaborates
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LLM analyzes:
  - "High query volume suggests add-index is better"
  - "add-index is faster to implement"
  - "partition is infrastructure change"
  - "add-index can be rolled back easily"

  LLM returns:
  {
    "operators": [
      {
        "name": "add-index",
        "confidence": 0.92,
        "rationale": "Handles 95% of query patterns",
        "attributes": {"type": "structural", "risk": "low"}
      },
      {
        "name": "partition-table",
        "confidence": 0.71,
        "rationale": "Complements indexing for range queries",
        "attributes": {"type": "infrastructure", "risk": "medium"}
      }
    ],
    "elaboration_depth": "sufficient",
    "suggestion": "Try add-index first, then partition if needed"
  }

STEP 6: Validate LLM Output
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Validation checks:
  ├─ Schema valid? ✓ (proper JSON)
  ├─ Operators known? ✓ (both in KB)
  ├─ Confidence justified? ✓ (0.92 is high but reasonable)
  ├─ Consistency? ✓ (no contradictions)
  └─ Novel? ✓ (both suggested before, but high confidence)

STEP 7: Assimilate into Working Memory
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SOAR updates WM:
  ├─ (add-index ^elaboration-score 0.92)
  ├─ (partition ^elaboration-score 0.71)
  └─ (impasse-resolution ^status resolved)

STEP 8: Decision Phase
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SOAR decides:
  - add-index (0.92) > partition (0.71)
  - → SELECT: add-index

STEP 9: Execution Phase
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SOAR executes:
  ├─ Command: CREATE INDEX idx_query_time ON queries(execution_time)
  └─ Monitor: Wait for command result

STEP 10: Learning Phase
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Outcome: Latency 5000ms → 800ms ✓ Success!

  SOAR learns:
  (p optimize-database-via-indexing
    (goal ^name optimize-performance)
    (database ^type postgresql)
    (query-volume ^load high)
    -->
    (operator ^name add-index ^priority high)
  )
```

---

## SECTION 2: DETAILED CODE EXAMPLES

### Example 1: Complete SOAR-LLM Interface

```python
import json
import jsonschema
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ImpasseType(Enum):
    PREFERENCE_TIE = "preference_tie"
    NO_CANDIDATES = "no_candidates"
    CONSTRAINT_CONFLICT = "constraint_conflict"
    UNCLEAR_WINNER = "unclear_winner"

@dataclass
class Operator:
    """Represents an operator SOAR can execute"""
    name: str
    soar_score: float = 0.0
    elaboration_score: Optional[float] = None
    confidence: float = 1.0
    attributes: Dict = None

    def effective_score(self):
        """Returns elaboration score if available, else SOAR score"""
        return self.elaboration_score or self.soar_score

class SOARLLMInterface:
    """
    Main interface between SOAR and LLM systems
    """

    # Constraint schema - LLM output must match this
    CONSTRAINT_SCHEMA = {
        "type": "object",
        "properties": {
            "operators": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "maxLength": 50},
                        "confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0
                        },
                        "rationale": {
                            "type": "string",
                            "maxLength": 200
                        },
                        "attributes": {"type": "object"}
                    },
                    "required": ["name", "confidence"],
                    "additionalProperties": False
                },
                "maxItems": 5,  # Never return more than 5 operators
                "minItems": 1
            },
            "elaboration_depth": {
                "type": "string",
                "enum": ["insufficient", "adequate", "sufficient"]
            },
            "suggestion": {
                "type": "string",
                "maxLength": 150
            }
        },
        "required": ["operators", "elaboration_depth"],
        "additionalProperties": False
    }

    def __init__(self, llm_client, max_tokens=150, timeout=3.0):
        self.llm = llm_client
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.operator_kb = self._load_operator_knowledge_base()

    def detect_and_resolve_impasse(
        self,
        goal: str,
        current_state: Dict,
        candidates: List[Operator],
        previous_attempts: List[str] = None
    ) -> Optional[Operator]:
        """
        End-to-end impasse detection and resolution

        Returns: Selected operator, or None if unresolvable
        """

        # Step 1: Detect impasse
        has_impasse, impasse_type, operators_involved = \
            self._detect_impasse(candidates)

        if not has_impasse:
            # No impasse - return highest scoring operator
            return max(candidates, key=lambda op: op.soar_score)

        print(f"[SOAR] Impasse detected: {impasse_type}")

        # Step 2: Call LLM for elaboration
        try:
            llm_output = self._call_llm_with_constraints(
                goal=goal,
                state=current_state,
                operators=operators_involved,
                previous_attempts=previous_attempts or []
            )
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            # Fallback: use highest SOAR score
            return max(candidates, key=lambda op: op.soar_score)

        # Step 3: Validate LLM output
        is_valid, issues = self._validate_llm_output(llm_output)

        if not is_valid:
            print(f"[ERROR] LLM output invalid: {issues}")
            # Fallback
            return max(candidates, key=lambda op: op.soar_score)

        # Step 4: Assimilate into working memory
        parsed = json.loads(llm_output)
        self._update_operator_scores(candidates, parsed)

        # Step 5: Decide
        selected = max(candidates, key=lambda op: op.effective_score())
        print(f"[SOAR] Impasse resolved: selected {selected.name} "
              f"(elaboration_score={selected.elaboration_score:.2f})")

        return selected

    def _detect_impasse(self, candidates: List[Operator]) -> Tuple[bool, ImpasseType, List[Operator]]:
        """
        Detect if multiple operators tie in preference

        Returns: (has_impasse, type, operators_that_tie)
        """
        if not candidates:
            return True, ImpasseType.NO_CANDIDATES, []

        scores = [op.soar_score for op in candidates]
        top_score = max(scores)

        # Find all operators within 0.05 of top score
        tied = [op for op in candidates if op.soar_score >= top_score - 0.05]

        if len(tied) > 1:
            return True, ImpasseType.PREFERENCE_TIE, tied

        return False, None, []

    def _call_llm_with_constraints(
        self,
        goal: str,
        state: Dict,
        operators: List[Operator],
        previous_attempts: List[str]
    ) -> str:
        """
        Call LLM with hard constraints on response format and size
        """

        # Build constrained prompt
        prompt = self._build_constrained_prompt(
            goal=goal,
            state=state,
            operators=operators,
            previous_attempts=previous_attempts
        )

        # Call LLM with restrictions
        response = self.llm.create_completion(
            prompt=prompt,
            max_tokens=self.max_tokens,
            temperature=0.1,  # Low temperature for consistency
            timeout=self.timeout,
            response_format="json"  # Enforce JSON format
        )

        return response

    def _build_constrained_prompt(self, goal, state, operators, previous_attempts):
        """
        Build prompt that guides LLM to structured, concise output
        """

        operator_list = ", ".join(op.name for op in operators)

        prompt = f"""TASK: Elaborate on operators to resolve impasse.

GOAL: {goal}

CURRENT STATE:
{json.dumps(state, indent=2)}

TIED OPERATORS:
{operator_list}

CONSTRAINTS:
- Response MUST be valid JSON (no markdown, no explanation outside JSON)
- Maximum 5 operators
- Each operator MUST have: name, confidence (0.0-1.0)
- rationale: 1-2 sentences max
- NO LENGTHY EXPLANATIONS

PREVIOUS ATTEMPTS: {', '.join(previous_attempts) or 'None'}

OUTPUT SCHEMA (JSON ONLY, NO TEXT):
{{
  "operators": [
    {{"name": "operator-1", "confidence": 0.95, "rationale": "Brief reason"}},
    {{"name": "operator-2", "confidence": 0.80, "rationale": "Brief reason"}}
  ],
  "elaboration_depth": "sufficient",
  "suggestion": "Which to try first?"
}}

RESPOND WITH JSON ONLY:
"""
        return prompt

    def _validate_llm_output(self, llm_output: str) -> Tuple[bool, List[str]]:
        """
        Multi-level validation of LLM response
        """
        issues = []

        # Level 1: Parse JSON
        try:
            parsed = json.loads(llm_output)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]

        # Level 2: Schema validation
        try:
            jsonschema.validate(parsed, self.CONSTRAINT_SCHEMA)
        except jsonschema.ValidationError as e:
            return False, [f"Schema error: {e.message}"]

        # Level 3: Semantic validation
        for op in parsed.get("operators", []):
            if not self._is_plausible_operator(op["name"]):
                issues.append(f"Operator '{op['name']}' not plausible")

        # Level 4: Confidence bounds check
        for op in parsed.get("operators", []):
            conf = op["confidence"]
            if conf > 0.95:
                if not self._is_extremely_confident_justified(op["name"]):
                    issues.append(
                        f"Confidence {conf} too high for '{op['name']}'"
                    )

        return len(issues) == 0, issues

    def _is_plausible_operator(self, op_name: str) -> bool:
        """Check if operator exists in knowledge base"""
        # Simplified: check if it's in our KB
        return op_name in self.operator_kb

    def _is_extremely_confident_justified(self, op_name: str) -> bool:
        """Check if >0.95 confidence is justified for this operator"""
        # Simplified: only certain operators warrant >0.95 confidence
        high_confidence_ops = {"send-message", "write-log", "update-timestamp"}
        return op_name in high_confidence_ops

    def _update_operator_scores(self, candidates: List[Operator], llm_output: Dict):
        """
        Transfer LLM confidence scores to operator objects
        """
        llm_operators = {op["name"]: op for op in llm_output["operators"]}

        for candidate in candidates:
            if candidate.name in llm_operators:
                llm_op = llm_operators[candidate.name]
                candidate.elaboration_score = llm_op["confidence"]
                candidate.attributes = llm_op.get("attributes", {})

    def _load_operator_knowledge_base(self) -> Dict:
        """Load operators known to system"""
        return {
            "add-index": {"domain": "database", "type": "structural"},
            "partition-table": {"domain": "database", "type": "infrastructure"},
            "rewrite-query": {"domain": "database", "type": "optimization"},
            "reach-from-left": {"domain": "robotics", "type": "motion"},
            "reach-from-right": {"domain": "robotics", "type": "motion"},
            "grasp-object": {"domain": "robotics", "type": "control"},
            "approve-request": {"domain": "business", "type": "decision"},
            "escalate-case": {"domain": "business", "type": "decision"},
        }
```

### Example 2: Robotics Domain Adaptation

```python
class RoboticsSOARAgent:
    """
    SOAR agent adapted for robotics with continuous control
    """

    def __init__(self, robot_interface):
        self.robot = robot_interface
        self.soar = SOARLLMInterface(llm_client=None)  # No LLM needed for preloaded ops

        # Preload operator library (no need for LLM to generate)
        self.operator_library = self._build_operator_library()

    def _build_operator_library(self):
        """
        Preload all robotics operators - why LLM can't generate these!
        """
        return {
            "reach": {
                "approach_directions": ["from-left", "from-right", "from-above"],
                "speeds": ["slow", "normal", "fast"],
                "trajectory_planner": RRTStarPlanner(),
            },
            "grasp": {
                "forces_newtons": [5, 10, 20, 30, 40, 50],
                "widths_meters": [0.05, 0.08, 0.10, 0.12],
                "controller": GraspController(),
            },
            "place": {
                "locations": ["shelf-1", "shelf-2", "table-center"],
                "orientations": ["upright", "tilted-45", "horizontal"],
                "controller": PlacementController(),
            }
        }

    def execute_pick_task(self, object_id: str):
        """
        Execute: "Pick object from shelf" with SOAR reasoning
        """

        # Goal
        goal = "pick-object"
        goal_params = {"object_id": object_id}

        # Current state (continuous + symbolic)
        state = self._get_state()
        symbolic_state = {
            "object_location": state.object_location,  # "shelf-1"
            "gripper_status": "open" if state.gripper_width > 0.05 else "closed",
            "arm_position": self._discretize_position(state.ee_position),
            "safety_status": "safe" if not state.collision_detected else "unsafe"
        }

        # Proposal phase: Generate reach candidates
        candidates = self._generate_reach_candidates(state)

        # Detect impasse: Multiple feasible approaches?
        if len(candidates) > 1:
            print(f"[SOAR] Reach impasse: {len(candidates)} approaches feasible")

            # Call LLM to distinguish
            selected_approach = self._resolve_reach_with_llm(
                state=symbolic_state,
                candidates=candidates
            )
        else:
            selected_approach = candidates[0] if candidates else "from-left"

        # Execute: Plan trajectory for selected approach
        trajectory = self._plan_trajectory(
            approach=selected_approach,
            target_object=object_id,
            state=state
        )

        # Execute trajectory
        self.robot.execute_trajectory(trajectory)

        # Monitor execution
        success = self.robot.wait_for_completion(timeout=5.0)

        if success:
            # Learning: Save successful approach
            self._learn_successful_reach(object_id, selected_approach)

        return success

    def _generate_reach_candidates(self, state) -> List[str]:
        """
        Generate feasible reach approaches given robot state
        """
        feasible = []

        object_pose = state.object_pose
        robot_pose = state.ee_position

        for direction in self.operator_library["reach"]["approach_directions"]:
            # Check kinematic feasibility
            ik_solution = self._solve_ik(object_pose, direction)

            if ik_solution is None:
                continue  # IK failed, not feasible

            # Check collision
            if self._check_collision(ik_solution):
                continue  # Would collide

            # Check gripper constraints
            if not self._check_gripper_width(ik_solution):
                continue

            feasible.append(direction)

        return feasible

    def _resolve_reach_with_llm(self, state: Dict, candidates: List[str]) -> str:
        """
        When multiple reach approaches are feasible, ask LLM which is best
        """

        prompt = f"""
        Robot arm at {state['arm_position']} must pick object.

        Feasible approaches:
        1. from-left: 1.8s estimated, previous success rate 92%
        2. from-right: 2.1s estimated, previous success rate 87%
        3. from-above: 2.5s estimated, previous success rate 95%

        Current constraint: must complete in 2.5 seconds
        Object shape: cylindrical (symmetric, any approach works)

        Which approach? (answer: left, right, or above)
        """

        response = llm.call(prompt, max_tokens=10)
        selected = response.strip().lower()

        mapping = {"left": "from-left", "right": "from-right", "above": "from-above"}
        return mapping.get(selected, candidates[0])

    def _plan_trajectory(self, approach: str, target_object: str, state) -> List[Dict]:
        """
        Abstract SOAR operator → concrete trajectory
        """

        planner = self.operator_library["reach"]["trajectory_planner"]

        trajectory = planner.plan(
            start_config=state.joint_angles,
            target_pose=state.object_pose,
            approach_direction=approach,
            collision_check=True
        )

        return trajectory

    def _learn_successful_reach(self, object_id: str, approach: str):
        """
        SOAR-style chunking: Create production rule
        """

        # Record success
        rule = f"""
        (p pick-{object_id}-via-{approach}
            (goal ^name pick-object)
            (object ^id {object_id})
            (gripper ^status open)
            -->
            (operator ^name reach ^direction {approach})
        )
        """

        self.soar.add_production(rule)
        print(f"[SOAR] Learned: reach {object_id} via {approach}")
```

### Example 3: Impasse Resolution Tree

```python
class ImpasseResolutionTree:
    """
    Decision tree for different impasse resolution strategies
    """

    def resolve(self, impasse_type, goal, state, candidates):
        """Route to appropriate resolution strategy"""

        if impasse_type == "preference_tie":
            return self._resolve_preference_tie(goal, state, candidates)

        elif impasse_type == "unclear_winner":
            return self._resolve_unclear_winner(goal, state, candidates)

        elif impasse_type == "constraint_forced":
            return self._resolve_constraint_forced(goal, state, candidates)

        elif impasse_type == "no_candidates":
            return self._resolve_no_candidates(goal, state)

        elif impasse_type == "insufficient_decomposition":
            return self._resolve_insufficient_decomposition(goal, state)

    def _resolve_preference_tie(self, goal, state, candidates):
        """
        Two operators have equal preference scores
        Strategy: Elaborate on differences
        """

        print(f"[SOAR] Preference tie between: {[c.name for c in candidates]}")

        # Ask LLM: What distinguishes these?
        prompt = f"""
        Goal: {goal}
        State: {state}

        These operators are equally preferred:
        {[c.name for c in candidates]}

        What is the key difference between them?
        Which would you recommend for this state?
        """

        analysis = llm.call(prompt)

        # Parse analysis and re-score
        for candidate in candidates:
            if candidate.name in analysis:
                # LLM mentioned this operator positively
                candidate.elaboration_score = 0.85
            else:
                candidate.elaboration_score = 0.70

        return max(candidates, key=lambda c: c.elaboration_score)

    def _resolve_unclear_winner(self, goal, state, candidates):
        """
        Operators are very close in score, winner unclear
        Strategy: Find distinguishing criterion
        """

        print(f"[SOAR] Unclear winner among: {[c.name for c in candidates]}")

        # Ask: What would distinguish them?
        prompt = f"""
        These operators are very close:
        {[(c.name, c.soar_score) for c in candidates]}

        What criterion would distinguish them?
        - Speed to execution?
        - Reliability?
        - Side effects?
        - Future options?

        Which operator wins on the best criterion?
        """

        analysis = llm.call(prompt)

        # Simple heuristic: LLM mentioned one = that's the winner
        winner = candidates[0]
        for candidate in candidates:
            if candidate.name in analysis:
                winner = candidate
                break

        winner.elaboration_score = 0.80
        return winner

    def _resolve_constraint_forced(self, goal, state, candidates):
        """
        Constraint eliminates all but one option
        Strategy: Accept forced choice or relax constraint
        """

        constraints = state.active_constraints
        feasible = [c for c in candidates if c.check_constraints()]

        if len(feasible) == 0:
            # No option satisfies constraints
            print(f"[SOAR] Constraint conflict: no feasible operator")

            # Ask LLM to help
            prompt = f"""
            Constraints: {constraints}
            Options: {[c.name for c in candidates]}

            No operator satisfies constraints.
            Should we relax constraints or modify operators?
            """

            advice = llm.call(prompt)
            # Execute advice...

        elif len(feasible) == 1:
            # Constraint forces one choice
            print(f"[SOAR] Constraint forces: {feasible[0].name}")
            return feasible[0]

        else:
            # Multiple feasible: pick best among feasible
            return max(feasible, key=lambda c: c.soar_score)

    def _resolve_no_candidates(self, goal, state):
        """
        No operators proposed (impasse at proposal phase)
        Strategy: Call LLM to generate operators
        """

        print(f"[SOAR] Impasse: no candidates for goal {goal}")

        # Ask LLM: What operators could work?
        prompt = f"""
        Goal: {goal}
        State: {state}

        No operators found in production memory.
        What operators could achieve this goal?
        Return: ["operator-1", "operator-2", ...]
        """

        response = llm.call(prompt, format="json")
        operators = json.loads(response)

        # Create temporary operators from LLM output
        new_operators = [
            Operator(name=op, soar_score=0.5, confidence=0.7)
            for op in operators
        ]

        # Score them
        # (Would normally go through another cycle)
        return max(new_operators, key=lambda c: c.soar_score)

    def _resolve_insufficient_decomposition(self, goal, state):
        """
        First decomposition didn't resolve impasse
        Strategy: Deeper decomposition (sub-subgoals)
        """

        print(f"[SOAR] Decomposition insufficient for {goal}")

        # Ask LLM: What's the next level of detail?
        prompt = f"""
        Goal: {goal}
        Previous decomposition attempts: [...]

        We need to decompose more deeply.
        What sub-sub-goals should we consider?
        """

        response = llm.call(prompt)
        # Parse and create new goals
```

---

## SECTION 3: ROBOTICS vs. BUSINESS LOGIC COMPARISON

### Side-by-Side Implementation

```python
class DomainAdapter:
    """Adapts AURORA for different domains"""

    @staticmethod
    def adapt_for_business_logic():
        """Database optimization domain"""

        return {
            "operator_library": {
                "source": "learned_from_experience",
                "preload": False,
                "generation": "by_llm_when_impasse"
            },
            "state_representation": {
                "type": "symbolic_discrete",
                "examples": ["pending", "approved", "error"]
            },
            "time_constraints": {
                "response_required": "within_business_hours",
                "typical_cycle": "seconds_to_minutes"
            },
            "validation": {
                "level": "semantic_logic",
                "recovery": "backtrack_and_retry"
            },
            "learning": {
                "mechanism": "chunking_to_rules",
                "validation": "test_on_replay"
            }
        }

    @staticmethod
    def adapt_for_robotics():
        """Robot control domain"""

        return {
            "operator_library": {
                "source": "kinematics_and_geometry",
                "preload": True,  # Preload all feasible operators!
                "generation": "not_by_llm"
            },
            "state_representation": {
                "type": "symbolic + continuous",
                "examples": ["reach_from_left", "joint_angles=[0.1, 0.2, ...]"]
            },
            "time_constraints": {
                "response_required": "real_time_10_100hz",
                "typical_cycle": "milliseconds"
            },
            "validation": {
                "level": "kinematic + collision_safety",
                "recovery": "immediate_stop_and_safe_state"
            },
            "learning": {
                "mechanism": "chunking + gradient_learning",
                "validation": "physical_safety_first"
            }
        }

    @staticmethod
    def when_to_call_llm_business_logic():
        """Business domain: LLM used for decomposition and elaboration"""

        return [
            {
                "situation": "Novel problem (no rules match)",
                "question": "What operators could work?",
                "llm_role": "generator",
                "frequency": "rare_but_important"
            },
            {
                "situation": "Preference tie",
                "question": "Which approach is better for this state?",
                "llm_role": "elaborator",
                "frequency": "occasional"
            },
            {
                "situation": "Deep impasse (multiple elaborations failed)",
                "question": "Should we redefine the goal?",
                "llm_role": "strategist",
                "frequency": "rare"
            }
        ]

    @staticmethod
    def when_to_call_llm_robotics():
        """Robotics domain: LLM used sparingly, only for disambiguation"""

        return [
            {
                "situation": "Multiple equally feasible reach approaches",
                "question": "Which approach is safest/most reliable?",
                "llm_role": "disambiguator",
                "frequency": "occasional",
                "constraint": "must_respond_in_10ms"
            },
            {
                "situation": "Novel object shape (not in training)",
                "question": "How should we grip this?",
                "llm_role": "advisor",
                "frequency": "rare",
                "constraint": "must_respect_safety_bounds"
            }
        ]
```

---

## SECTION 4: COMPLETE SCENARIO WALKTHROUGH

### Scenario: Database Optimization (Business Logic)

```
GOAL: Optimize query performance (5s → <100ms)

┌─ SOAR State
│  ├─ goal: optimize-performance
│  ├─ metrics: {latency: 5000ms, throughput: 1000qps}
│  └─ constraints: {budget: low, risk_tolerance: medium}
│
├─ SOAR Proposal Phase
│  ├─ Rule 1 fires: high_latency → propose add-index
│  ├─ Rule 2 fires: high_latency → propose partition-table
│  └─ Rule 3 fires: high_throughput → propose query-rewrite
│
├─ SOAR Scores
│  ├─ add-index: 0.80 (matches condition well)
│  ├─ partition-table: 0.80 (matches condition well)
│  └─ query-rewrite: 0.60 (lower priority)
│
├─ IMPASSE DETECTED
│  └─ add-index ≈ partition-table (both 0.80)
│
├─ Call LLM
│  └─ "These two tie in preference. Which is better for this state?"
│
│  LLM analyzes:
│  - Query pattern: 80% single-column filters, 20% joins
│  - add-index: handles 80% of queries directly
│  - partition-table: helps with time-range queries
│  - Latency: 80% win with add-index, 20% win with partition
│
│  LLM confidence:
│  - add-index: 0.92 (handles majority case)
│  - partition-table: 0.71 (handles minority case)
│
├─ SOAR Updates Scores
│  ├─ add-index: elaboration_score = 0.92
│  └─ partition-table: elaboration_score = 0.71
│
├─ Decision: add-index wins (0.92 > 0.71)
│
├─ Execute
│  └─ CREATE INDEX idx_query_time ON queries(creation_time)
│
├─ Monitor
│  └─ Latency: 5000ms → 800ms ✓ Success!
│
└─ Learning
   └─ Create SOAR production:
      (p optimize-high-latency-via-indexing
        (goal ^name optimize-performance)
        (metrics ^latency > 1000)
        (query-pattern ^single-column-dominant)
        -->
        (operator ^name add-index)
      )
```

### Scenario: Robot Pick Task (Robotics)

```
GOAL: Pick cylindrical object from shelf

┌─ SOAR State (Symbolic)
│  ├─ goal: pick-object
│  ├─ gripper-status: open
│  ├─ object-location: shelf-1
│  └─ arm-position: starting
│
├─ Continuous State (Monitoring)
│  ├─ ee_position: [0.4, 0.2, 0.8]  meters
│  ├─ joint_angles: [0.1, 0.5, 0.3, 0.2, 0.1, 0.0]  radians
│  └─ gripper_width: 0.12  meters (open)
│
├─ SOAR Proposal Phase
│  └─ Rule: "If goal=pick and gripper=open, propose reach"
│
├─ Generate Reach Candidates (Preloaded)
│  ├─ reach-from-left
│  │  ├─ IK check: FEASIBLE ✓
│  │  ├─ Collision check: SAFE ✓
│  │  └─ Time estimate: 1.8s
│  │
│  ├─ reach-from-right
│  │  ├─ IK check: FEASIBLE ✓
│  │  ├─ Collision check: SAFE ✓
│  │  └─ Time estimate: 2.1s
│  │
│  └─ reach-from-above
│     ├─ IK check: FEASIBLE ✓
│     ├─ Collision check: RISKY (shelf edge)
│     └─ Time estimate: 2.5s
│
├─ SOAR Scores
│  ├─ reach-from-left: 0.85 (good speed, stable)
│  ├─ reach-from-right: 0.85 (good speed, stable)
│  └─ reach-from-above: 0.70 (risky, slow)
│
├─ IMPASSE DETECTED
│  └─ reach-from-left ≈ reach-from-right (both 0.85)
│
├─ Call LLM (Symbolic)
│  └─ "Two approaches equally good. Which is best?"
│
│  Context for LLM:
│  - Previous success: left=92%, right=87%
│  - Object: symmetric (any approach works)
│  - Constraint: must complete in 2.5s
│
│  LLM response: "Choose left, higher success rate"
│
├─ SOAR Updates Scores
│  ├─ reach-from-left: elaboration_score = 0.92
│  └─ reach-from-right: elaboration_score = 0.88
│
├─ Decision: reach-from-left wins
│
├─ Plan Trajectory
│  └─ RRT* planner:
│     ├─ start: [0.1, 0.5, 0.3, 0.2, 0.1, 0.0]
│     ├─ goal: [shelf-1 position]
│     ├─ approach: left
│     └─ output: [joint trajectory with 100+ waypoints]
│
├─ Execute Trajectory (Real-time Control @ 100Hz)
│  └─ For each waypoint:
│     ├─ Read current joint positions
│     ├─ Compute tracking error
│     ├─ Adjust motor commands (PID controller)
│     ├─ Check collision sensors
│     └─ Send next command
│
├─ Monitor Execution
│  ├─ Trajectory tracking error: 0.008m (acceptable)
│  ├─ Collision detection: No contact
│  ├─ Joint torques: Within limits
│  └─ Time: 1.7s (within budget)
│
├─ Execute Grasp
│  └─ GraspController:
│     ├─ Close gripper: width 0.12 → 0.05
│     ├─ Target force: 20N
│     ├─ Monitor grip stability
│     └─ Confirm object held
│
├─ Outcome
│  ├─ Trajectory: Success ✓
│  ├─ Grasp: Success ✓
│  ├─ Object secured: True ✓
│  └─ Total time: 2.3s (within 2.5s budget) ✓
│
└─ Learning
   └─ Create SOAR production:
      (p pick-cylindrical-via-left-reach
        (goal ^name pick-object)
        (object ^shape cylindrical)
        (arm-position ^status ready)
        -->
        (operator ^name reach ^direction left ^speed normal)
      )
```

---

## SECTION 5: CONSTRAINT ENFORCEMENT EXAMPLES

### Token Budget Constraint

```python
def enforce_token_limits(prompt_or_response, max_tokens, direction="input"):
    """Ensure token count stays within budget"""

    encoder = tiktoken.get_encoding("cl100k_base")

    if direction == "input":
        tokens = encoder.encode(prompt_or_response)
        if len(tokens) > max_tokens:
            # Truncate, keeping critical sections
            critical_end = max_tokens - 100
            truncated = encoder.decode(tokens[:critical_end])
            print(f"[WARNING] Input truncated: {len(tokens)} → {max_tokens}")
            return truncated
        return prompt_or_response

    elif direction == "output":
        tokens = encoder.encode(prompt_or_response)
        if len(tokens) > max_tokens:
            # Truncate JSON array
            try:
                data = json.loads(prompt_or_response)
                # Keep only first 3 operators
                data["operators"] = data["operators"][:3]
                return json.dumps(data)
            except:
                return encoder.decode(tokens[:max_tokens])
        return prompt_or_response
```

### Confidence Threshold Constraint

```python
def enforce_confidence_threshold(llm_output, min_confidence=0.7):
    """Filter operators below confidence threshold"""

    data = json.loads(llm_output)

    # Remove operators with low confidence
    original_count = len(data["operators"])
    data["operators"] = [
        op for op in data["operators"]
        if op["confidence"] >= min_confidence
    ]

    if len(data["operators"]) == 0:
        # All filtered out - restore highest confidence operator
        data["operators"] = [
            max(json.loads(llm_output)["operators"],
                key=lambda x: x["confidence"])
        ]

    return json.dumps(data)
```

### Timeout Constraint

```python
async def call_llm_with_timeout(prompt, timeout_ms=2000):
    """Call LLM with timeout for real-time requirements"""

    try:
        response = await asyncio.wait_for(
            llm.create_completion_async(
                prompt=prompt,
                max_tokens=150
            ),
            timeout=timeout_ms / 1000.0
        )
        return response

    except asyncio.TimeoutError:
        print(f"[WARNING] LLM call timeout after {timeout_ms}ms")
        # Return fallback response
        return json.dumps({
            "operators": [{"name": "default-fallback", "confidence": 0.5}],
            "elaboration_depth": "insufficient",
            "timeout": True
        })
```

