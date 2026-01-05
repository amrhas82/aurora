"""
AURORA Headless Reasoning Mode

This module implements autonomous, goal-driven execution for AURORA where the system
can iteratively work toward a specified goal without human intervention between iterations.

Headless mode enables AURORA to:
- Execute autonomous experiments with defined goals
- Maintain iteration memory via scratchpad
- Enforce safety constraints (git branch validation, budget limits)
- Self-evaluate progress toward goal completion
- Gracefully terminate on success, budget exhaustion, or max iterations

Safety Features:
    - Git branch enforcement: Only runs on "headless" branch (blocks main/master)
    - Budget tracking: Monitors LLM costs, stops when budget exceeded ($5 default)
    - Max iterations: Prevents runaway loops (10 iterations default)
    - Scratchpad logging: Full audit trail of all actions and decisions

Components:
    - git_enforcer: Git branch validation and safety checks
    - prompt_loader: Prompt file parsing and validation
    - scratchpad_manager: Scratchpad read/write/parse logic
    - orchestrator: Main HeadlessOrchestrator loop

Usage:
    from aurora_soar.headless import HeadlessOrchestrator, HeadlessConfig

    orchestrator = HeadlessOrchestrator(
        prompt_path="experiment.md",
        scratchpad_path="scratchpad.md",
        config=HeadlessConfig(
            max_iterations=10,
            budget_limit=5.0,
            required_branch="headless"
        )
    )

    result = orchestrator.execute()
    print(f"Goal achieved: {result.goal_achieved}")
    print(f"Iterations: {result.iterations}")
    print(f"Cost: ${result.total_cost:.2f}")

Prompt Format:
    # Goal
    [Clear statement of what to achieve]

    # Success Criteria
    - [Measurable criterion 1]
    - [Measurable criterion 2]

    # Constraints
    - [Constraint 1]
    - [Constraint 2]

    # Context (optional)
    [Additional context for the experiment]

Termination Conditions:
    1. GOAL_ACHIEVED: LLM evaluates scratchpad and confirms goal met
    2. BUDGET_EXCEEDED: Total cost exceeds budget_limit
    3. MAX_ITERATIONS: Reached max_iterations without goal completion
"""

# Version information
__version__ = "1.0.0"
__author__ = "AURORA Development Team"

# Module exports - will be populated as components are implemented
__all__ = [
    # Main orchestrator
    "HeadlessOrchestrator",
    "HeadlessConfig",
    "HeadlessResult",
    "TerminationReason",
    # Git enforcement
    "GitEnforcer",
    "GitEnforcerConfig",
    "GitBranchError",
    # Prompt handling
    "PromptLoader",
    "PromptData",
    "PromptValidationError",
    # Scratchpad management
    "ScratchpadManager",
    "ScratchpadEntry",
    "ScratchpadConfig",
    "ScratchpadStatus",
    "TerminationSignal",
]

# Components will be imported here as they are implemented
from .config import HeadlessConfig
from .git_enforcer import GitBranchError, GitEnforcer, GitEnforcerConfig
from .orchestrator_simplified import HeadlessOrchestrator, HeadlessResult, TerminationReason
from .prompt_loader_simplified import PromptData, PromptLoader, PromptValidationError
from .scratchpad import Scratchpad

# Keep old imports available for backwards compatibility (if needed)
# from .orchestrator import HeadlessOrchestrator as HeadlessOrchestratorOld
# from .prompt_loader import PromptLoader as PromptLoaderOld
from .scratchpad_manager import (
    ScratchpadConfig,
    ScratchpadEntry,
    ScratchpadManager,
    ScratchpadStatus,
    TerminationSignal,
)
