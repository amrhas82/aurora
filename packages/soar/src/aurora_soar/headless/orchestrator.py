"""
Headless Orchestrator - Autonomous Experiment Execution

This module implements the HeadlessOrchestrator that runs autonomous experiments
without human intervention between iterations. It integrates GitEnforcer,
PromptLoader, and ScratchpadManager to safely execute goal-driven tasks.

The orchestrator:
1. Validates git branch safety (must be on "headless" branch)
2. Loads and validates experiment prompt
3. Initializes scratchpad for iteration tracking
4. Runs main loop: iterate -> evaluate -> check termination
5. Tracks budget and enforces limits
6. Detects goal achievement via LLM evaluation
7. Handles max iterations gracefully

Safety Philosophy:
    Headless mode is powerful but risky. Multiple safety mechanisms ensure
    experiments can't damage the codebase or incur runaway costs:
    - Git branch enforcement prevents running on main/master
    - Budget limits stop execution when costs exceed threshold
    - Max iterations prevent infinite loops
    - Scratchpad provides full audit trail

Usage:
    from aurora_soar.headless import HeadlessOrchestrator, HeadlessConfig

    orchestrator = HeadlessOrchestrator(
        prompt_path="experiment.md",
        scratchpad_path="scratchpad.md",
        soar_orchestrator=soar,
        config=HeadlessConfig(
            max_iterations=10,
            budget_limit=5.0,
            required_branch="headless"
        )
    )

    result = orchestrator.execute()
    print(f"Goal achieved: {result.goal_achieved}")
    print(f"Iterations: {result.iterations}")
    print(f"Total cost: ${result.total_cost:.2f}")
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .git_enforcer import GitBranchError, GitEnforcer, GitEnforcerConfig
from .prompt_loader import PromptData, PromptLoader, PromptValidationError
from .scratchpad_manager import (
    ScratchpadConfig,
    ScratchpadManager,
    ScratchpadStatus,
)


class TerminationReason(Enum):
    """
    Reasons for headless execution termination.

    These map to termination signals but are used in the result object.
    """

    GOAL_ACHIEVED = "GOAL_ACHIEVED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    BLOCKED = "BLOCKED"
    GIT_SAFETY_ERROR = "GIT_SAFETY_ERROR"
    PROMPT_ERROR = "PROMPT_ERROR"


@dataclass
class HeadlessConfig:
    """
    Configuration for headless mode execution.

    Attributes:
        max_iterations: Maximum number of SOAR iterations (default: 10)
        budget_limit: Maximum cost in USD (default: 5.0)
        required_branch: Git branch required for execution (default: "headless")
        blocked_branches: Git branches that are forbidden (default: ["main", "master"])
        auto_create_scratchpad: Create scratchpad if missing (default: True)
        scratchpad_backup: Backup scratchpad before starting (default: True)
        evaluation_prompt_template: LLM prompt template for goal evaluation
    """

    max_iterations: int = 10
    budget_limit: float = 5.0
    required_branch: str = "headless"
    blocked_branches: list[str] = field(default_factory=lambda: ["main", "master"])
    auto_create_scratchpad: bool = True
    scratchpad_backup: bool = True
    evaluation_prompt_template: str = """# Goal Achievement Evaluation

You are evaluating whether an autonomous experiment has achieved its goal.

**Goal**: {goal}

**Success Criteria**:
{success_criteria}

**Scratchpad Content** (iteration history and actions taken):
{scratchpad_content}

Based on the scratchpad, has the goal been achieved? Consider:
1. Are all success criteria met?
2. Is there evidence of successful completion in the iteration logs?
3. Are there any blockers or failures that prevent goal achievement?

Respond with exactly one of:
- GOAL_ACHIEVED: All success criteria met, goal accomplished
- IN_PROGRESS: Making progress, but goal not yet achieved
- BLOCKED: Stuck, unable to make progress toward goal

Your response (GOAL_ACHIEVED, IN_PROGRESS, or BLOCKED):"""


@dataclass
class HeadlessResult:
    """
    Result of headless execution.

    Attributes:
        goal_achieved: Whether the goal was achieved
        termination_reason: Why execution stopped
        iterations: Number of iterations completed
        total_cost: Total cost in USD
        duration_seconds: Execution time in seconds
        scratchpad_path: Path to scratchpad file
        error_message: Error message if failed (None if successful)
    """

    goal_achieved: bool
    termination_reason: TerminationReason
    iterations: int
    total_cost: float
    duration_seconds: float
    scratchpad_path: str
    error_message: str | None = None


class HeadlessOrchestrator:
    """
    Autonomous experiment orchestrator for headless mode.

    The HeadlessOrchestrator manages autonomous execution of experiments with
    defined goals, success criteria, and constraints. It integrates all safety
    mechanisms and provides the main execution loop.

    Key Features:
        - Git branch safety validation
        - Prompt loading and validation
        - Scratchpad initialization and logging
        - Main iteration loop with SOAR integration
        - Budget tracking and enforcement
        - Goal achievement evaluation
        - Graceful termination handling

    Safety Mechanisms:
        1. Git branch enforcement (blocks main/master)
        2. Budget limits (stops when exceeded)
        3. Max iterations (prevents infinite loops)
        4. Scratchpad audit trail (full transparency)
        5. Error recovery (graceful failure handling)

    Examples:
        # Basic usage
        >>> from aurora_soar.headless import HeadlessOrchestrator, HeadlessConfig
        >>> orchestrator = HeadlessOrchestrator(
        ...     prompt_path="experiment.md",
        ...     scratchpad_path="scratchpad.md",
        ...     soar_orchestrator=soar
        ... )
        >>> result = orchestrator.execute()

        # Custom configuration
        >>> config = HeadlessConfig(
        ...     max_iterations=20,
        ...     budget_limit=10.0,
        ...     required_branch="experiment-123"
        ... )
        >>> orchestrator = HeadlessOrchestrator(
        ...     prompt_path="experiment.md",
        ...     scratchpad_path="scratchpad.md",
        ...     soar_orchestrator=soar,
        ...     config=config
        ... )
        >>> result = orchestrator.execute()
    """

    def __init__(
        self,
        prompt_path: str | Path,
        scratchpad_path: str | Path,
        soar_orchestrator: Any,  # Type: SOAROrchestrator (avoiding circular import)
        config: HeadlessConfig | None = None,
    ):
        """
        Initialize HeadlessOrchestrator.

        Args:
            prompt_path: Path to experiment prompt markdown file
            scratchpad_path: Path to scratchpad markdown file
            soar_orchestrator: SOAROrchestrator instance for query execution
            config: Optional HeadlessConfig (uses defaults if None)
        """
        self.prompt_path = Path(prompt_path)
        self.scratchpad_path = Path(scratchpad_path)
        self.soar_orchestrator = soar_orchestrator
        self.config = config or HeadlessConfig()

        # Initialize components
        self.git_enforcer = GitEnforcer(
            GitEnforcerConfig(
                required_branch=self.config.required_branch,
                blocked_branches=self.config.blocked_branches,
            )
        )

        self.prompt_loader = PromptLoader(self.prompt_path)

        self.scratchpad_manager = ScratchpadManager(
            self.scratchpad_path,
            ScratchpadConfig(
                auto_create=self.config.auto_create_scratchpad,
                backup_on_init=self.config.scratchpad_backup,
            ),
        )

        # Execution state
        self.prompt_data: PromptData | None = None
        self.current_iteration: int = 0
        self.total_cost: float = 0.0
        self.start_time: float | None = None

    def _validate_safety(self) -> None:
        """
        Validate all safety constraints before execution.

        Raises:
            GitBranchError: If git branch validation fails
            PromptValidationError: If prompt validation fails
        """
        # 1. Validate git branch
        self.git_enforcer.validate()

        # 2. Validate prompt file
        is_valid, errors = self.prompt_loader.validate_format()
        if not is_valid:
            error_msg = "\n".join(errors)
            raise PromptValidationError(
                f"Prompt validation failed:\n{error_msg}"
            )

    def _load_prompt(self) -> PromptData:
        """
        Load and parse the experiment prompt.

        Returns:
            Parsed PromptData

        Raises:
            PromptValidationError: If prompt cannot be loaded
        """
        return self.prompt_loader.load()

    def _initialize_scratchpad(self) -> None:
        """
        Initialize scratchpad with experiment goal.

        Uses goal from loaded prompt data.
        """
        if not self.prompt_data:
            raise RuntimeError("Prompt data not loaded before scratchpad initialization")

        self.scratchpad_manager.initialize(
            goal=self.prompt_data.goal,
            status=ScratchpadStatus.IN_PROGRESS,
        )

    def _check_budget(self) -> bool:
        """
        Check if budget limit has been exceeded.

        Returns:
            True if budget exceeded, False otherwise
        """
        return self.total_cost >= self.config.budget_limit

    def _evaluate_goal_achievement(self) -> str:
        """
        Use LLM to evaluate if goal has been achieved.

        Reads scratchpad content and prompts LLM to evaluate against
        success criteria from the prompt.

        Returns:
            One of: "GOAL_ACHIEVED", "IN_PROGRESS", "BLOCKED"
        """
        if not self.prompt_data:
            return "IN_PROGRESS"

        # Read current scratchpad content
        scratchpad_content = self.scratchpad_manager.read()

        # Format success criteria as bullet list
        success_criteria_str = "\n".join(
            f"- {criterion}" for criterion in self.prompt_data.success_criteria
        )

        # Build evaluation prompt
        evaluation_prompt = self.config.evaluation_prompt_template.format(
            goal=self.prompt_data.goal,
            success_criteria=success_criteria_str,
            scratchpad_content=scratchpad_content,
        )

        # Query LLM for evaluation
        # Use reasoning_llm for this critical decision
        try:
            result = self.soar_orchestrator.reasoning_llm.complete(
                evaluation_prompt,
                max_tokens=50,
            )

            response = result.get("content", "IN_PROGRESS").strip().upper()

            # Extract status from response
            if "GOAL_ACHIEVED" in response:
                return "GOAL_ACHIEVED"
            if "BLOCKED" in response:
                return "BLOCKED"
            return "IN_PROGRESS"

        except Exception as e:
            # If LLM evaluation fails, assume in progress
            print(f"Warning: Goal evaluation failed: {e}")
            return "IN_PROGRESS"

    def _execute_iteration(self, iteration: int) -> dict[str, Any]:
        """
        Execute a single SOAR iteration.

        Args:
            iteration: Current iteration number (1-indexed)

        Returns:
            Result dictionary from SOAR execution with cost information
        """
        # Build query for this iteration
        # Include goal, constraints, and current scratchpad context
        query = self._build_iteration_query(iteration)

        # Execute SOAR pipeline
        result: dict[str, Any] = self.soar_orchestrator.execute(
            query=query,
            verbosity="NORMAL",
            max_cost_usd=self.config.budget_limit - self.total_cost,
        )

        return result

    def _build_iteration_query(self, iteration: int) -> str:
        """
        Build query for SOAR execution in this iteration.

        Args:
            iteration: Current iteration number

        Returns:
            Query string for SOAR
        """
        if not self.prompt_data:
            return "Continue working toward the goal."

        # Read recent scratchpad entries for context
        scratchpad_content = self.scratchpad_manager.read()

        return f"""# Autonomous Experiment - Iteration {iteration}

**Goal**: {self.prompt_data.goal}

**Success Criteria**:
{chr(10).join(f'- {c}' for c in self.prompt_data.success_criteria)}

**Constraints**:
{chr(10).join(f'- {c}' for c in self.prompt_data.constraints)}

**Previous Progress** (from scratchpad):
{scratchpad_content[-2000:] if len(scratchpad_content) > 2000 else scratchpad_content}

What is the next action to move closer to achieving the goal? Consider:
1. What has been done already (check scratchpad)
2. What remains to be done (check success criteria)
3. What is the highest priority next step

Provide a specific, actionable next step.
"""

    def _run_main_loop(self) -> TerminationReason:
        """
        Run the main iteration loop.

        Returns:
            TerminationReason indicating why loop terminated
        """
        while self.current_iteration < self.config.max_iterations:
            self.current_iteration += 1

            print(f"\n=== Iteration {self.current_iteration}/{self.config.max_iterations} ===")

            # Check budget before iteration
            if self._check_budget():
                self.scratchpad_manager.update_status(ScratchpadStatus.BUDGET_EXCEEDED)
                return TerminationReason.BUDGET_EXCEEDED

            # Execute SOAR iteration
            try:
                result = self._execute_iteration(self.current_iteration)

                # Extract cost and response
                iteration_cost = result.get("cost_usd", 0.0)
                self.total_cost += iteration_cost

                answer = result.get("answer", "No answer provided")
                confidence = result.get("confidence", 0.0)

                # Log to scratchpad
                self.scratchpad_manager.append_iteration(
                    iteration=self.current_iteration,
                    phase="SOAR Execution",
                    action=f"Executed iteration {self.current_iteration}",
                    result=f"Response: {answer[:500]}... (confidence: {confidence:.2f})",
                    cost=iteration_cost,
                    notes=f"Total cost so far: ${self.total_cost:.4f}",
                )

                print(f"Cost: ${iteration_cost:.4f} (Total: ${self.total_cost:.4f})")
                print(f"Response: {answer[:200]}...")

            except Exception as e:
                # Log error to scratchpad
                self.scratchpad_manager.append_iteration(
                    iteration=self.current_iteration,
                    phase="Error",
                    action=f"Iteration {self.current_iteration} failed",
                    result=f"Error: {str(e)}",
                    cost=0.0,
                )
                self.scratchpad_manager.update_status(ScratchpadStatus.BLOCKED)
                return TerminationReason.BLOCKED

            # Evaluate goal achievement every iteration
            evaluation = self._evaluate_goal_achievement()
            print(f"Goal evaluation: {evaluation}")

            if evaluation == "GOAL_ACHIEVED":
                self.scratchpad_manager.update_status(ScratchpadStatus.GOAL_ACHIEVED)
                return TerminationReason.GOAL_ACHIEVED

            if evaluation == "BLOCKED":
                self.scratchpad_manager.update_status(ScratchpadStatus.BLOCKED)
                return TerminationReason.BLOCKED

            # Check budget after iteration
            if self._check_budget():
                self.scratchpad_manager.update_status(ScratchpadStatus.BUDGET_EXCEEDED)
                return TerminationReason.BUDGET_EXCEEDED

        # Reached max iterations without achieving goal
        self.scratchpad_manager.update_status(ScratchpadStatus.MAX_ITERATIONS)
        return TerminationReason.MAX_ITERATIONS

    def execute(self) -> HeadlessResult:
        """
        Execute the headless experiment.

        This is the main entry point for headless mode. It runs the complete
        workflow: validation -> initialization -> main loop -> cleanup.

        Returns:
            HeadlessResult with execution summary

        Examples:
            >>> orchestrator = HeadlessOrchestrator(
            ...     prompt_path="experiment.md",
            ...     scratchpad_path="scratchpad.md",
            ...     soar_orchestrator=soar
            ... )
            >>> result = orchestrator.execute()
            >>> if result.goal_achieved:
            ...     print(f"Success in {result.iterations} iterations!")
            ... else:
            ...     print(f"Failed: {result.termination_reason}")
        """
        self.start_time = datetime.now().timestamp()

        try:
            print("=== Headless Mode: Starting Autonomous Experiment ===\n")

            # 1. Validate safety constraints
            print("Step 1: Validating safety constraints...")
            try:
                self._validate_safety()
                print("✓ Git branch validation passed")
                print("✓ Prompt validation passed")
            except GitBranchError as e:
                print(f"✗ Git safety error: {e}")
                return HeadlessResult(
                    goal_achieved=False,
                    termination_reason=TerminationReason.GIT_SAFETY_ERROR,
                    iterations=0,
                    total_cost=0.0,
                    duration_seconds=0.0,
                    scratchpad_path=str(self.scratchpad_path),
                    error_message=str(e),
                )
            except PromptValidationError as e:
                print(f"✗ Prompt error: {e}")
                return HeadlessResult(
                    goal_achieved=False,
                    termination_reason=TerminationReason.PROMPT_ERROR,
                    iterations=0,
                    total_cost=0.0,
                    duration_seconds=0.0,
                    scratchpad_path=str(self.scratchpad_path),
                    error_message=str(e),
                )

            # 2. Load prompt
            print("\nStep 2: Loading experiment prompt...")
            self.prompt_data = self._load_prompt()
            print(f"✓ Goal: {self.prompt_data.goal}")
            print(f"✓ Success Criteria: {len(self.prompt_data.success_criteria)} items")
            print(f"✓ Constraints: {len(self.prompt_data.constraints)} items")

            # 3. Initialize scratchpad
            print("\nStep 3: Initializing scratchpad...")
            self._initialize_scratchpad()
            print(f"✓ Scratchpad: {self.scratchpad_path}")

            # 4. Run main loop
            print(f"\nStep 4: Running main loop (max {self.config.max_iterations} iterations, budget ${self.config.budget_limit})...")
            termination_reason = self._run_main_loop()

            # 5. Calculate duration
            duration = datetime.now().timestamp() - self.start_time

            # 6. Build result
            goal_achieved = termination_reason == TerminationReason.GOAL_ACHIEVED

            print("\n=== Experiment Complete ===")
            print(f"Termination: {termination_reason.value}")
            print(f"Goal Achieved: {goal_achieved}")
            print(f"Iterations: {self.current_iteration}")
            print(f"Total Cost: ${self.total_cost:.4f}")
            print(f"Duration: {duration:.1f}s")
            print(f"Scratchpad: {self.scratchpad_path}")

            return HeadlessResult(
                goal_achieved=goal_achieved,
                termination_reason=termination_reason,
                iterations=self.current_iteration,
                total_cost=self.total_cost,
                duration_seconds=duration,
                scratchpad_path=str(self.scratchpad_path),
            )

        except Exception as e:
            # Unexpected error - return failure result
            duration = datetime.now().timestamp() - (self.start_time or datetime.now().timestamp())
            print(f"\n✗ Unexpected error: {e}")

            return HeadlessResult(
                goal_achieved=False,
                termination_reason=TerminationReason.BLOCKED,
                iterations=self.current_iteration,
                total_cost=self.total_cost,
                duration_seconds=duration,
                scratchpad_path=str(self.scratchpad_path),
                error_message=str(e),
            )
