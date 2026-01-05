"""
Simplified Headless Orchestrator - Single Iteration Autonomous Execution

This is a simplified version of the HeadlessOrchestrator that:
- Executes a single SOAR iteration (no loop)
- Uses simplified PromptLoader and Scratchpad
- Focuses on core safety and validation
- Provides clear success/failure results

The simplified orchestrator:
1. Validates git branch safety
2. Loads and validates experiment prompt
3. Initializes scratchpad
4. Executes single SOAR iteration
5. Evaluates success (simple heuristic)
6. Returns clear result

Safety Philosophy:
    Single-iteration execution is safer and easier to reason about.
    Users can chain multiple invocations if needed, with full
    control between iterations.

Usage:
    from aurora_soar.headless import HeadlessOrchestrator, HeadlessConfig

    orchestrator = HeadlessOrchestrator(
        prompt_path="experiment.md",
        scratchpad_path="scratchpad.md",
        soar_orchestrator=soar,
        config=HeadlessConfig()
    )

    result = orchestrator.execute()
    print(f"Goal achieved: {result.goal_achieved}")
    print(f"Cost: ${result.total_cost:.2f}")
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .config import HeadlessConfig
from .git_enforcer import GitBranchError, GitEnforcer, GitEnforcerConfig
from .prompt_loader_simplified import PromptData, PromptLoader, PromptValidationError
from .scratchpad import ExecutionStatus, Scratchpad


class TerminationReason(Enum):
    """
    Reasons for headless execution termination.

    For simplified single-iteration orchestrator:
    - SUCCESS: Iteration completed successfully
    - BLOCKED: Execution failed or error occurred
    - GIT_SAFETY_ERROR: Git branch validation failed
    - PROMPT_ERROR: Prompt validation or loading failed
    """

    SUCCESS = "SUCCESS"
    BLOCKED = "BLOCKED"
    GIT_SAFETY_ERROR = "GIT_SAFETY_ERROR"
    PROMPT_ERROR = "PROMPT_ERROR"


@dataclass
class HeadlessResult:
    """
    Result of headless execution.

    Attributes:
        goal_achieved: Whether the goal appears to be achieved
        termination_reason: Why execution stopped
        iterations: Number of iterations completed (always 1 for simplified version)
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
    Simplified autonomous experiment orchestrator for headless mode.

    This simplified version executes a single SOAR iteration and evaluates
    success using simple heuristics. It integrates safety mechanisms and
    provides clear execution results.

    Key Features:
        - Single iteration execution (not a loop)
        - Git branch safety validation
        - Simplified prompt loading
        - Scratchpad logging
        - Clear success/failure result

    Safety Mechanisms:
        1. Git branch enforcement (blocks main/master)
        2. Prompt validation
        3. Scratchpad audit trail
        4. Error recovery (graceful failure handling)

    Examples:
        # Basic usage
        >>> from aurora_soar.headless import HeadlessOrchestrator, HeadlessConfig
        >>> orchestrator = HeadlessOrchestrator(
        ...     prompt_path="experiment.md",
        ...     scratchpad_path="scratchpad.md",
        ...     soar_orchestrator=soar
        ... )
        >>> result = orchestrator.execute()
        >>> print(f"Success: {result.goal_achieved}")

        # With dependency injection (for testing)
        >>> orchestrator = HeadlessOrchestrator(
        ...     prompt_path="experiment.md",
        ...     scratchpad_path="scratchpad.md",
        ...     soar_orchestrator=soar,
        ...     git_enforcer=mock_git,
        ...     prompt_loader=mock_prompt,
        ...     scratchpad=mock_scratchpad
        ... )
    """

    def __init__(
        self,
        prompt_path: str | Path,
        scratchpad_path: str | Path,
        soar_orchestrator: Any,  # Type: SOAROrchestrator (avoiding circular import)
        config: HeadlessConfig | None = None,
        git_enforcer: GitEnforcer | None = None,
        prompt_loader: PromptLoader | None = None,
        scratchpad: Scratchpad | None = None,
    ):
        """
        Initialize HeadlessOrchestrator.

        Args:
            prompt_path: Path to experiment prompt markdown file
            scratchpad_path: Path to scratchpad markdown file
            soar_orchestrator: SOAROrchestrator instance for query execution
            config: Optional HeadlessConfig (uses defaults if None)
            git_enforcer: Optional GitEnforcer instance (creates default if None)
            prompt_loader: Optional PromptLoader instance (creates default if None)
            scratchpad: Optional Scratchpad instance (creates default if None)
        """
        self.prompt_path = Path(prompt_path)
        self.scratchpad_path = Path(scratchpad_path)
        self.soar_orchestrator = soar_orchestrator
        self.config = config or HeadlessConfig()

        # Initialize components (allow dependency injection for testing)
        # Git enforcer uses its own default config (blocks main/master)
        self.git_enforcer = git_enforcer or GitEnforcer()

        self.prompt_loader = prompt_loader or PromptLoader(self.prompt_path)

        self.scratchpad = scratchpad or Scratchpad(self.scratchpad_path)

        # Execution state
        self.prompt_data: PromptData | None = None
        self.start_time: float | None = None

    def _validate_safety(self) -> None:
        """
        Validate all safety constraints before execution.

        Raises:
            GitBranchError: If git branch validation fails
        """
        # Validate git branch
        self.git_enforcer.validate()

    def _load_prompt(self) -> PromptData:
        """
        Load and parse the experiment prompt.

        Returns:
            Parsed PromptData

        Raises:
            PromptValidationError: If prompt cannot be loaded
        """
        return self.prompt_loader.load()

    def _build_iteration_query(self) -> str:
        """
        Build query for SOAR execution.

        Returns:
            Query string for SOAR
        """
        if not self.prompt_data:
            return "Execute the task as specified."

        # Read current scratchpad for context
        scratchpad_content = self.scratchpad.read()

        query_parts = [
            f"# Autonomous Experiment - Iteration 1",
            f"",
            f"**Goal**: {self.prompt_data.goal}",
            f"",
            f"**Success Criteria**:",
        ]

        for criterion in self.prompt_data.success_criteria:
            query_parts.append(f"- {criterion}")

        if self.prompt_data.constraints:
            query_parts.append("")
            query_parts.append("**Constraints**:")
            for constraint in self.prompt_data.constraints:
                query_parts.append(f"- {constraint}")

        if scratchpad_content:
            query_parts.append("")
            query_parts.append("**Previous Progress** (from scratchpad):")
            # Truncate if too long
            content = scratchpad_content[-2000:] if len(scratchpad_content) > 2000 else scratchpad_content
            query_parts.append(content)

        query_parts.extend([
            "",
            "Execute the next action to achieve the goal. Provide specific, actionable steps."
        ])

        return "\n".join(query_parts)

    def _evaluate_success(self) -> bool:
        """
        Simple heuristic to evaluate if goal appears achieved.

        For simplified version, checks scratchpad content for success indicators.

        Returns:
            True if success indicators found, False otherwise
        """
        scratchpad_content = self.scratchpad.read().lower()

        # Simple keyword-based heuristic
        success_keywords = [
            "completed",
            "success",
            "achieved",
            "done",
            "finished",
            "passing"
        ]

        failure_keywords = [
            "failed",
            "error",
            "blocked",
            "cannot",
            "unable"
        ]

        # Count indicators
        success_count = sum(1 for keyword in success_keywords if keyword in scratchpad_content)
        failure_count = sum(1 for keyword in failure_keywords if keyword in scratchpad_content)

        # Simple logic: more success indicators than failure indicators
        return success_count > failure_count

    def execute(self) -> HeadlessResult:
        """
        Execute the headless experiment (single iteration).

        This is the main entry point for headless mode. It runs a single
        SOAR iteration with full validation and logging.

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
            ...     print(f"Success! Cost: ${result.total_cost:.2f}")
            ... else:
            ...     print(f"Failed: {result.error_message}")
        """
        self.start_time = datetime.now().timestamp()
        total_cost = 0.0

        try:
            print("=== Headless Mode: Single Iteration Execution ===\n")

            # 1. Validate safety constraints
            print("Step 1: Validating safety constraints...")
            try:
                self._validate_safety()
                print("✓ Git branch validation passed")
            except GitBranchError as e:
                print(f"✗ Git safety error: {e}")
                duration = datetime.now().timestamp() - self.start_time
                return HeadlessResult(
                    goal_achieved=False,
                    termination_reason=TerminationReason.GIT_SAFETY_ERROR,
                    iterations=0,
                    total_cost=0.0,
                    duration_seconds=duration,
                    scratchpad_path=str(self.scratchpad_path),
                    error_message=str(e),
                )

            # 2. Load prompt
            print("\nStep 2: Loading experiment prompt...")
            try:
                self.prompt_data = self._load_prompt()
                print(f"✓ Goal: {self.prompt_data.goal}")
                print(f"✓ Success Criteria: {len(self.prompt_data.success_criteria)} items")
            except PromptValidationError as e:
                print(f"✗ Prompt error: {e}")
                duration = datetime.now().timestamp() - self.start_time
                return HeadlessResult(
                    goal_achieved=False,
                    termination_reason=TerminationReason.PROMPT_ERROR,
                    iterations=0,
                    total_cost=0.0,
                    duration_seconds=duration,
                    scratchpad_path=str(self.scratchpad_path),
                    error_message=str(e),
                )

            # 3. Scratchpad is already initialized in __init__
            print("\nStep 3: Scratchpad ready...")
            print(f"✓ Scratchpad: {self.scratchpad_path}")

            # 4. Execute single SOAR iteration
            print("\nStep 4: Executing SOAR iteration...")
            query = self._build_iteration_query()

            try:
                result = self.soar_orchestrator.execute(
                    query=query,
                    verbosity="NORMAL",
                )

                # Extract result
                answer = result.get("answer", "No answer provided")
                confidence = result.get("confidence", 0.0)
                iteration_cost = result.get("cost_usd", 0.0)
                total_cost += iteration_cost

                print(f"✓ SOAR execution completed")
                print(f"  Cost: ${iteration_cost:.4f}")
                print(f"  Response: {answer[:200]}...")

                # Log to scratchpad
                self.scratchpad.append_iteration(
                    iteration=1,
                    goal=self.prompt_data.goal,
                    action="Executed single SOAR iteration",
                    result=f"Response: {answer[:500]}... (confidence: {confidence:.2f})"
                )

                # 5. Evaluate success
                print("\nStep 5: Evaluating success...")
                goal_achieved = self._evaluate_success()

                if goal_achieved:
                    self.scratchpad.update_status(ExecutionStatus.COMPLETED)
                    termination_reason = TerminationReason.SUCCESS
                    print("✓ Goal appears achieved (based on scratchpad analysis)")
                else:
                    self.scratchpad.update_status(ExecutionStatus.IN_PROGRESS)
                    termination_reason = TerminationReason.SUCCESS  # Still successful execution
                    print("✓ Execution complete (goal not yet achieved)")

            except Exception as e:
                # SOAR execution failed
                print(f"✗ SOAR execution failed: {e}")

                # Log to scratchpad
                self.scratchpad.append_iteration(
                    iteration=1,
                    goal=self.prompt_data.goal if self.prompt_data else "Unknown goal",
                    action="SOAR execution failed",
                    result=f"Error: {str(e)}"
                )
                self.scratchpad.update_status(ExecutionStatus.FAILED)

                duration = datetime.now().timestamp() - self.start_time
                return HeadlessResult(
                    goal_achieved=False,
                    termination_reason=TerminationReason.BLOCKED,
                    iterations=1,
                    total_cost=total_cost,
                    duration_seconds=duration,
                    scratchpad_path=str(self.scratchpad_path),
                    error_message=str(e),
                )

            # 6. Calculate duration and return result
            duration = datetime.now().timestamp() - self.start_time

            print("\n=== Execution Complete ===")
            print(f"Goal Achieved: {goal_achieved}")
            print(f"Total Cost: ${total_cost:.4f}")
            print(f"Duration: {duration:.1f}s")
            print(f"Scratchpad: {self.scratchpad_path}")

            return HeadlessResult(
                goal_achieved=goal_achieved,
                termination_reason=termination_reason,
                iterations=1,
                total_cost=total_cost,
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
                iterations=0,
                total_cost=total_cost,
                duration_seconds=duration,
                scratchpad_path=str(self.scratchpad_path),
                error_message=str(e),
            )
