"""Policy models and data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OperationType(Enum):
    """Types of operations that can be policy-checked."""

    FILE_DELETE = "file_delete"
    GIT_PUSH = "git_push"
    GIT_FORCE_PUSH = "git_force_push"
    GIT_PUSH_MAIN = "git_push_main"
    SQL_DROP = "sql_drop"
    SQL_TRUNCATE = "sql_truncate"
    SCOPE_CHANGE = "scope_change"


class PolicyAction(Enum):
    """Actions that can be taken when policy is evaluated."""

    ALLOW = "allow"
    PROMPT = "prompt"
    DENY = "deny"


@dataclass
class Operation:
    """Represents an operation to be checked against policies."""

    type: OperationType
    target: str
    count: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyResult:
    """Result of a policy check."""

    action: PolicyAction
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryConfig:
    """Configuration for agent recovery."""

    timeout_seconds: int = 300  # 5 minutes - complex tasks need more time
    max_retries: int = 2
    fallback_to_llm: bool = True


@dataclass
class BudgetConfig:
    """Configuration for budget policies."""

    monthly_limit_usd: float = 100.0
    warn_at_percent: int = 80
    hard_limit_action: PolicyAction = PolicyAction.DENY


@dataclass
class DestructiveConfig:
    """Configuration for destructive operation policies."""

    file_delete: dict[str, Any] = field(
        default_factory=lambda: {"action": "prompt", "max_files": 5},
    )
    git_force_push: dict[str, Any] = field(default_factory=lambda: {"action": "deny"})
    git_push_main: dict[str, Any] = field(default_factory=lambda: {"action": "prompt"})
    drop_table: dict[str, Any] = field(default_factory=lambda: {"action": "deny"})
    truncate: dict[str, Any] = field(default_factory=lambda: {"action": "prompt"})


@dataclass
class SafetyConfig:
    """Configuration for safety policies."""

    auto_branch: bool = True
    branch_prefix: str = "aurora/"
    max_files_modified: int = 20
    max_lines_changed: int = 1000
    protected_paths: list[str] = field(
        default_factory=lambda: [".git/", "node_modules/", "vendor/", ".env", "*.pem", "*.key"],
    )


@dataclass
class AnomalyConfig:
    """Configuration for anomaly detection."""

    scope_multiplier: int = 3
    unexpected_file_types: list[str] = field(
        default_factory=lambda: ["*.sql", "*.sh", "Dockerfile"],
    )


@dataclass
class PoliciesConfig:
    """Complete policies configuration."""

    budget: BudgetConfig = field(default_factory=BudgetConfig)
    agent_recovery: RecoveryConfig = field(default_factory=RecoveryConfig)
    destructive: DestructiveConfig = field(default_factory=DestructiveConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    anomalies: AnomalyConfig = field(default_factory=AnomalyConfig)
