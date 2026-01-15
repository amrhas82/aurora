"""Backward compatibility alias for budget tracking.

This module provides backward compatibility for code that imports from
aurora_core.cost instead of aurora_core.budget.
"""

from aurora_core.budget.tracker import BudgetExceededError, BudgetTracker, CostTracker


__all__ = ["BudgetExceededError", "BudgetTracker", "CostTracker"]
