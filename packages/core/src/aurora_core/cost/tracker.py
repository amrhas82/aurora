"""Backward compatibility alias for budget tracker.

This module provides backward compatibility for code that imports from
aurora_core.cost.tracker instead of aurora_core.budget.tracker.
"""

from aurora_core.budget.tracker import (
    BudgetExceededError,
    BudgetTracker,
    CostEntry,
    CostTracker,
    ModelPricing,
)


__all__ = [
    "BudgetExceededError",
    "BudgetTracker",
    "CostEntry",
    "CostTracker",
    "ModelPricing",
]
