"""Cost tracking and budget enforcement for AURORA LLM usage."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


class BudgetExceededError(Exception):
    """Raised when an operation would exceed the budget limit."""


@dataclass
class ModelPricing:
    """Pricing information for a specific LLM model.

    All prices in USD per million tokens.
    """

    input_price_per_mtok: float  # Input token price per million tokens
    output_price_per_mtok: float  # Output token price per million tokens

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for given token usage.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated

        Returns:
            Total cost in USD

        """
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_mtok
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_mtok
        return input_cost + output_cost


# Provider-specific pricing (as of December 2024)
# Source: https://www.anthropic.com/pricing, https://openai.com/pricing
MODEL_PRICING: dict[str, ModelPricing] = {
    # Anthropic Claude models
    "claude-opus-4-20250514": ModelPricing(15.0, 75.0),  # Opus 4
    "claude-sonnet-4-20250514": ModelPricing(3.0, 15.0),  # Sonnet 4
    "claude-3-7-sonnet-20250219": ModelPricing(3.0, 15.0),  # Sonnet 3.7
    "claude-3-5-haiku-20241022": ModelPricing(0.8, 4.0),  # Haiku 3.5
    "claude-3-opus-20240229": ModelPricing(15.0, 75.0),  # Opus 3
    "claude-3-sonnet-20240229": ModelPricing(3.0, 15.0),  # Sonnet 3
    "claude-3-haiku-20240307": ModelPricing(0.25, 1.25),  # Haiku 3
    # OpenAI GPT models
    "gpt-4-turbo": ModelPricing(10.0, 30.0),
    "gpt-4-turbo-preview": ModelPricing(10.0, 30.0),
    "gpt-4": ModelPricing(30.0, 60.0),
    "gpt-4-32k": ModelPricing(60.0, 120.0),
    "gpt-3.5-turbo": ModelPricing(0.5, 1.5),
    "gpt-3.5-turbo-16k": ModelPricing(3.0, 4.0),
    # Ollama local models (free, but track as $0)
    "llama2": ModelPricing(0.0, 0.0),
    "llama3": ModelPricing(0.0, 0.0),
    "mistral": ModelPricing(0.0, 0.0),
    "mixtral": ModelPricing(0.0, 0.0),
}

# Default pricing for unknown models (assume mid-tier pricing)
DEFAULT_PRICING = ModelPricing(3.0, 15.0)


@dataclass
class CostEntry:
    """Single cost entry for tracking."""

    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    operation: str  # e.g., "assess", "decompose", "verify"
    query_id: str | None = None


@dataclass
class PeriodBudget:
    """Budget tracking for a time period (typically monthly)."""

    period: str  # YYYY-MM format
    limit_usd: float
    consumed_usd: float = 0.0
    entries: list[CostEntry] = field(default_factory=list)

    @property
    def remaining_usd(self) -> float:
        """Calculate remaining budget."""
        return max(0.0, self.limit_usd - self.consumed_usd)

    @property
    def percent_consumed(self) -> float:
        """Calculate percentage of budget consumed."""
        if self.limit_usd == 0:
            return 100.0
        return (self.consumed_usd / self.limit_usd) * 100.0

    def is_at_soft_limit(self) -> bool:
        """Check if at 80% soft limit."""
        return self.percent_consumed >= 80.0

    def is_at_hard_limit(self) -> bool:
        """Check if at 100% hard limit."""
        return self.percent_consumed >= 100.0


class CostTracker:
    """Tracks LLM usage costs and enforces budget limits.

    Features:
    - Provider-specific pricing (Anthropic, OpenAI, Ollama)
    - Per-model cost calculation
    - Monthly budget tracking with soft/hard limits
    - Persistent tracking in ~/.aurora/budget_tracker.json

    Example:
        >>> tracker = CostTracker(monthly_limit_usd=10.0)
        >>> tracker.record_cost(
        ...     model="claude-sonnet-4-20250514",
        ...     input_tokens=1000,
        ...     output_tokens=500,
        ...     operation="assess"
        ... )
        >>> status = tracker.get_status()
        >>> print(f"Remaining: ${status['remaining_usd']:.2f}")

    """

    def __init__(
        self,
        monthly_limit_usd: float = 100.0,
        tracker_path: Path | None = None,
        budget_file: str | None = None,
        total_budget: float | None = None,
    ):
        """Initialize cost tracker.

        Args:
            monthly_limit_usd: Monthly budget limit in USD (deprecated, use total_budget)
            tracker_path: Path to tracker file (defaults to ~/.aurora/budget_tracker.json)
            budget_file: Alias for tracker_path (for backward compatibility)
            total_budget: Alias for monthly_limit_usd (for backward compatibility)

        """
        # Support legacy parameter names for backward compatibility
        if total_budget is not None:
            monthly_limit_usd = total_budget
        if budget_file is not None:
            tracker_path = Path(budget_file)

        self.monthly_limit_usd = monthly_limit_usd
        self.total_budget = monthly_limit_usd  # Alias for compatibility

        if tracker_path is None:
            aurora_dir = Path.home() / ".aurora"
            aurora_dir.mkdir(exist_ok=True, parents=True)
            tracker_path = aurora_dir / "budget_tracker.json"

        self.tracker_path = tracker_path
        self.current_period = self._get_current_period()
        self.budget = self._load_or_create_budget()

        # Sync instance variables with loaded budget
        self.monthly_limit_usd = self.budget.limit_usd
        self.total_budget = self.budget.limit_usd

    def _get_current_period(self) -> str:
        """Get current period identifier (YYYY-MM)."""
        return datetime.now().strftime("%Y-%m")

    def _load_or_create_budget(self) -> PeriodBudget:
        """Load existing budget or create new one for current period."""
        if self.tracker_path.exists():
            try:
                with open(self.tracker_path) as f:
                    data = json.load(f)

                # Check if we need to roll over to new period
                if data.get("period") != self.current_period:
                    # New period - archive old data and start fresh
                    self._archive_old_period(data)
                    return PeriodBudget(
                        period=self.current_period,
                        limit_usd=self.monthly_limit_usd,
                    )

                # Same period - load existing data
                entries = [CostEntry(**entry) for entry in data.get("entries", [])]
                return PeriodBudget(
                    period=data["period"],
                    limit_usd=data.get("limit_usd", self.monthly_limit_usd),
                    consumed_usd=data.get("consumed_usd", 0.0),
                    entries=entries,
                )
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                # Corrupted file - start fresh
                print(f"Warning: Could not load budget tracker ({e}), starting fresh")

        # Create new budget
        return PeriodBudget(
            period=self.current_period,
            limit_usd=self.monthly_limit_usd,
        )

    def _archive_old_period(self, old_data: dict[str, Any]) -> None:
        """Archive old period data to archive file."""
        archive_dir = self.tracker_path.parent / "budget_archives"
        archive_dir.mkdir(exist_ok=True)

        old_period = old_data.get("period", "unknown")
        archive_path = archive_dir / f"budget_{old_period}.json"

        try:
            with open(archive_path, "w") as f:
                json.dump(old_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not archive old budget data: {e}")

    def _save_budget(self) -> None:
        """Save current budget to disk."""
        data = {
            "period": self.budget.period,
            "limit_usd": self.budget.limit_usd,
            "consumed_usd": self.budget.consumed_usd,
            "entries": [
                {
                    "timestamp": entry.timestamp,
                    "model": entry.model,
                    "input_tokens": entry.input_tokens,
                    "output_tokens": entry.output_tokens,
                    "cost_usd": entry.cost_usd,
                    "operation": entry.operation,
                    "query_id": entry.query_id,
                }
                for entry in self.budget.entries
            ],
        }

        try:
            with open(self.tracker_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save budget tracker: {e}")

    def get_model_pricing(self, model: str) -> ModelPricing:
        """Get pricing for a model.

        Args:
            model: Model identifier

        Returns:
            ModelPricing for the model (or default if unknown)

        """
        return MODEL_PRICING.get(model, DEFAULT_PRICING)

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for given usage.

        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD

        """
        pricing = self.get_model_pricing(model)
        return pricing.calculate_cost(input_tokens, output_tokens)

    def estimate_cost(
        self,
        model: str,
        prompt_length: int,
        max_output_tokens: int = 4096,
    ) -> float:
        """Estimate cost for a query before execution.

        Uses heuristic: 1 token ≈ 4 characters for input estimation.

        Args:
            model: Model identifier
            prompt_length: Length of prompt in characters
            max_output_tokens: Maximum expected output tokens

        Returns:
            Estimated cost in USD

        """
        estimated_input_tokens = prompt_length // 4
        # Assume we'll use about 50% of max output tokens on average
        estimated_output_tokens = max_output_tokens // 2

        return self.calculate_cost(model, estimated_input_tokens, estimated_output_tokens)

    def check_budget(
        self,
        estimated_cost: float = 0.0,
        raise_on_exceeded: bool = True,
    ) -> tuple[bool, str]:
        """Check if query can proceed within budget.

        Args:
            estimated_cost: Estimated cost of upcoming operation
            raise_on_exceeded: If True, raise BudgetExceededError when budget exceeded (default)

        Returns:
            Tuple of (can_proceed, message)
            - can_proceed: True if query should proceed
            - message: Status message (warning or error)

        Raises:
            BudgetExceededError: If raise_on_exceeded=True and budget is exceeded

        """
        # Check if we need to roll over to new period
        if self.budget.period != self.current_period:
            self.budget = self._load_or_create_budget()

        projected_cost = self.budget.consumed_usd + estimated_cost
        projected_percent = (projected_cost / self.budget.limit_usd) * 100.0

        # Hard limit - block query
        if projected_percent >= 100.0:
            message = (
                f"Budget exceeded: ${projected_cost:.4f} / ${self.budget.limit_usd:.2f} "
                f"({projected_percent:.1f}%). Query blocked."
            )

            # Record blocked query in history
            entry = CostEntry(
                timestamp=datetime.now().isoformat(),
                model="unknown",
                input_tokens=0,
                output_tokens=0,
                cost_usd=estimated_cost,
                operation="blocked_query",
                query_id=None,
            )
            self.budget.entries.append(entry)
            self._save_budget()

            if raise_on_exceeded:
                raise BudgetExceededError(message)
            return (False, message)

        # Soft limit - warn but allow
        if projected_percent >= 80.0:
            return (
                True,
                f"Budget warning: ${projected_cost:.4f} / ${self.budget.limit_usd:.2f} "
                f"({projected_percent:.1f}%). Approaching limit.",
            )

        # Within budget
        return (True, "")

    def record_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        operation: str,
        query_id: str | None = None,
    ) -> float:
        """Record actual cost after query execution.

        Args:
            model: Model identifier
            input_tokens: Actual input tokens used
            output_tokens: Actual output tokens generated
            operation: Operation name (e.g., "assess", "decompose")
            query_id: Optional query identifier for tracking

        Returns:
            Cost in USD

        """
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        entry = CostEntry(
            timestamp=datetime.now().isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            operation=operation,
            query_id=query_id,
        )

        self.budget.entries.append(entry)
        self.budget.consumed_usd += cost
        self._save_budget()

        return cost

    def get_status(self) -> dict[str, Any]:
        """Get current budget status.

        Returns:
            Dictionary with budget status information

        """
        return {
            "period": self.budget.period,
            "limit_usd": self.budget.limit_usd,
            "consumed_usd": self.budget.consumed_usd,
            "remaining_usd": self.budget.remaining_usd,
            "percent_consumed": self.budget.percent_consumed,
            "at_soft_limit": self.budget.is_at_soft_limit(),
            "at_hard_limit": self.budget.is_at_hard_limit(),
            "total_entries": len(self.budget.entries),
        }

    def get_breakdown_by_operation(self) -> dict[str, float]:
        """Get cost breakdown by operation type.

        Returns:
            Dictionary mapping operation names to total costs

        """
        breakdown: dict[str, float] = {}
        for entry in self.budget.entries:
            breakdown[entry.operation] = breakdown.get(entry.operation, 0.0) + entry.cost_usd
        return breakdown

    def get_breakdown_by_model(self) -> dict[str, float]:
        """Get cost breakdown by model.

        Returns:
            Dictionary mapping model names to total costs

        """
        breakdown: dict[str, float] = {}
        for entry in self.budget.entries:
            breakdown[entry.model] = breakdown.get(entry.model, 0.0) + entry.cost_usd
        return breakdown

    # Compatibility methods for integration tests

    def set_budget(self, amount: float) -> None:
        """Set the budget limit.

        Args:
            amount: New budget limit in USD

        """
        self.budget.limit_usd = amount
        self.monthly_limit_usd = amount
        self.total_budget = amount
        self._save_budget()

    def reset_spending(self) -> None:
        """Reset spending to zero (clears all entries)."""
        self.budget.consumed_usd = 0.0
        self.budget.entries = []
        self._save_budget()

    def get_total_spent(self) -> float:
        """Get total amount spent in current period.

        Returns:
            Total spent in USD

        """
        return self.budget.consumed_usd

    def get_history(self) -> list[dict[str, Any]]:
        """Get query history with costs.

        Returns:
            List of dictionaries with query information

        """
        return [
            {
                "timestamp": entry.timestamp,
                "query": entry.operation,  # Use operation as query for compatibility
                "cost": entry.cost_usd,
                "status": "blocked" if entry.operation == "blocked_query" else "success",
                "model": entry.model,
                "input_tokens": entry.input_tokens,
                "output_tokens": entry.output_tokens,
            }
            for entry in self.budget.entries
        ]

    def record_query(
        self,
        query: str,
        cost: float,
        status: str = "success",
        model: str = "unknown",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Record a query with cost (compatibility method).

        Args:
            query: Query text
            cost: Cost in USD
            status: Status of query (success, blocked, etc.)
            model: Model used
            input_tokens: Input tokens used
            output_tokens: Output tokens generated

        """
        entry = CostEntry(
            timestamp=datetime.now().isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            operation=query,  # Use query as operation
            query_id=None,
        )

        self.budget.entries.append(entry)
        if status == "success":
            self.budget.consumed_usd += cost
        self._save_budget()


class BudgetTracker(CostTracker):
    """Alias for CostTracker for backward compatibility."""
