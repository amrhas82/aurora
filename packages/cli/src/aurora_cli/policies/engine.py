"""Policies engine for unified policy enforcement."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from aurora_cli.policies.defaults import get_default_policies_yaml
from aurora_cli.policies.models import (
    AnomalyConfig,
    BudgetConfig,
    DestructiveConfig,
    Operation,
    OperationType,
    PoliciesConfig,
    PolicyAction,
    PolicyResult,
    RecoveryConfig,
    SafetyConfig,
)
from aurora_core.paths import get_aurora_dir

logger = logging.getLogger(__name__)


class PoliciesEngine:
    """Unified policies engine for all commands."""

    def __init__(self, policies_path: Path | None = None):
        """Initialize policies engine.

        Args:
            policies_path: Path to policies.yaml file. If None, uses .aurora/policies.yaml

        """
        self.policies_path = policies_path or self._get_default_policies_path()
        self.config = self._load_policies()

    def _get_default_policies_path(self) -> Path:
        """Get default policies path in .aurora directory.

        Returns:
            Path to .aurora/policies.yaml

        """
        aurora_dir = get_aurora_dir()
        return aurora_dir / "policies.yaml"

    def _load_policies(self) -> PoliciesConfig:
        """Load policies from YAML file or use defaults.

        Returns:
            PoliciesConfig object

        """
        if not self.policies_path.exists():
            logger.info(f"Policies file not found at {self.policies_path}, using defaults")
            return self._parse_yaml(get_default_policies_yaml())

        try:
            with open(self.policies_path) as f:
                yaml_content = f.read()
            return self._parse_yaml(yaml_content)
        except Exception as e:
            logger.warning(
                f"Failed to load policies from {self.policies_path}: {e}, using defaults",
            )
            return self._parse_yaml(get_default_policies_yaml())

    def _parse_yaml(self, yaml_content: str) -> PoliciesConfig:
        """Parse YAML content into PoliciesConfig.

        Args:
            yaml_content: YAML string

        Returns:
            PoliciesConfig object

        """
        try:
            data = yaml.safe_load(yaml_content)

            # Parse budget config
            budget_data = data.get("budget", {})
            budget = BudgetConfig(
                monthly_limit_usd=budget_data.get("monthly_limit_usd", 100.0),
                warn_at_percent=budget_data.get("warn_at_percent", 80),
                hard_limit_action=(
                    PolicyAction.DENY
                    if budget_data.get("hard_limit_action") == "reject"
                    else PolicyAction.PROMPT
                ),
            )

            # Parse recovery config
            recovery_data = data.get("agent_recovery", {})
            agent_recovery = RecoveryConfig(
                timeout_seconds=recovery_data.get("timeout_seconds", 120),
                max_retries=recovery_data.get("max_retries", 2),
                fallback_to_llm=recovery_data.get("fallback_to_llm", True),
            )

            # Parse destructive config
            destructive_data = data.get("destructive", {})
            destructive = DestructiveConfig(
                file_delete=destructive_data.get(
                    "file_delete",
                    {"action": "prompt", "max_files": 5},
                ),
                git_force_push=destructive_data.get("git_force_push", {"action": "deny"}),
                git_push_main=destructive_data.get("git_push_main", {"action": "prompt"}),
                drop_table=destructive_data.get("drop_table", {"action": "deny"}),
                truncate=destructive_data.get("truncate", {"action": "prompt"}),
            )

            # Parse safety config
            safety_data = data.get("safety", {})
            safety = SafetyConfig(
                auto_branch=safety_data.get("auto_branch", True),
                branch_prefix=safety_data.get("branch_prefix", "aurora/"),
                max_files_modified=safety_data.get("max_files_modified", 20),
                max_lines_changed=safety_data.get("max_lines_changed", 1000),
                protected_paths=safety_data.get(
                    "protected_paths",
                    [".git/", "node_modules/", "vendor/", ".env", "*.pem", "*.key"],
                ),
            )

            # Parse anomaly config
            anomalies_data = data.get("anomalies", {})
            anomalies = AnomalyConfig(
                scope_multiplier=anomalies_data.get("scope_multiplier", 3),
                unexpected_file_types=anomalies_data.get(
                    "unexpected_file_types",
                    ["*.sql", "*.sh", "Dockerfile"],
                ),
            )

            return PoliciesConfig(
                budget=budget,
                agent_recovery=agent_recovery,
                destructive=destructive,
                safety=safety,
                anomalies=anomalies,
            )

        except Exception as e:
            logger.error(f"Failed to parse policies YAML: {e}, using defaults")
            # Return default config
            return PoliciesConfig()

    def check_operation(self, operation: Operation) -> PolicyResult:
        """Check if operation is allowed.

        Args:
            operation: Operation to check

        Returns:
            PolicyResult with action (ALLOW|PROMPT|DENY) and reason

        """
        if operation.type == OperationType.FILE_DELETE:
            config = self.config.destructive.file_delete
            action_str = config.get("action", "prompt")
            max_files = config.get("max_files", 5)

            if operation.count > max_files:
                if action_str == "deny":
                    return PolicyResult(
                        action=PolicyAction.DENY,
                        reason=f"Cannot delete {operation.count} files (limit: {max_files})",
                    )
                return PolicyResult(
                    action=PolicyAction.PROMPT,
                    reason=f"Deleting {operation.count} files (limit: {max_files})",
                )

            return PolicyResult(
                action=self._parse_action(action_str),
                reason=f"Deleting {operation.count} files",
            )

        if operation.type == OperationType.GIT_FORCE_PUSH:
            config = self.config.destructive.git_force_push
            action_str = config.get("action", "deny")
            return PolicyResult(
                action=self._parse_action(action_str),
                reason="Force push detected",
            )

        if operation.type == OperationType.GIT_PUSH_MAIN:
            config = self.config.destructive.git_push_main
            action_str = config.get("action", "prompt")
            return PolicyResult(
                action=self._parse_action(action_str),
                reason=f"Pushing to main/master branch: {operation.target}",
            )

        if operation.type == OperationType.SQL_DROP:
            config = self.config.destructive.drop_table
            action_str = config.get("action", "deny")
            return PolicyResult(
                action=self._parse_action(action_str),
                reason=f"DROP TABLE detected: {operation.target}",
            )

        if operation.type == OperationType.SQL_TRUNCATE:
            config = self.config.destructive.truncate
            action_str = config.get("action", "prompt")
            return PolicyResult(
                action=self._parse_action(action_str),
                reason=f"TRUNCATE detected: {operation.target}",
            )

        # Default case: allow operation
        return PolicyResult(
            action=PolicyAction.ALLOW,
            reason="Operation allowed",
        )

    def check_budget(self, _estimated_cost: float) -> PolicyResult:
        """Check if cost is within budget.

        Args:
            estimated_cost: Estimated cost in USD

        Returns:
            PolicyResult with action and reason

        """
        # This would integrate with existing CostTracker
        # For now, just return ALLOW
        return PolicyResult(
            action=PolicyAction.ALLOW,
            reason="Budget check passed",
        )

    def check_scope(self, files_modified: int, lines_changed: int) -> PolicyResult:
        """Check if scope is within limits.

        Args:
            files_modified: Number of files modified
            lines_changed: Number of lines changed

        Returns:
            PolicyResult with action and reason

        """
        max_files = self.config.safety.max_files_modified
        max_lines = self.config.safety.max_lines_changed

        if files_modified > max_files:
            return PolicyResult(
                action=PolicyAction.PROMPT,
                reason=f"Scope exceeds limits: {files_modified} files (limit: {max_files})",
                metadata={"files_modified": files_modified, "limit": max_files},
            )

        if lines_changed > max_lines:
            return PolicyResult(
                action=PolicyAction.PROMPT,
                reason=f"Scope exceeds limits: {lines_changed} lines (limit: {max_lines})",
                metadata={"lines_changed": lines_changed, "limit": max_lines},
            )

        return PolicyResult(
            action=PolicyAction.ALLOW,
            reason="Scope within limits",
        )

    def get_protected_paths(self) -> list[str]:
        """Return list of protected path patterns.

        Returns:
            List of protected path patterns

        """
        return self.config.safety.protected_paths

    def get_recovery_config(self) -> RecoveryConfig:
        """Get agent recovery configuration.

        Returns:
            RecoveryConfig object

        """
        return self.config.agent_recovery

    def _parse_action(self, action_str: str) -> PolicyAction:
        """Parse action string to PolicyAction enum.

        Args:
            action_str: Action string (allow, prompt, deny)

        Returns:
            PolicyAction enum value

        """
        action_map = {
            "allow": PolicyAction.ALLOW,
            "prompt": PolicyAction.PROMPT,
            "deny": PolicyAction.DENY,
        }
        return action_map.get(action_str.lower(), PolicyAction.PROMPT)

    def create_default_policies_file(self) -> Path:
        """Create default policies.yaml file.

        Returns:
            Path to created file

        """
        policies_path = self._get_default_policies_path()
        policies_path.parent.mkdir(parents=True, exist_ok=True)

        with open(policies_path, "w") as f:
            f.write(get_default_policies_yaml())

        logger.info(f"Created default policies file at {policies_path}")
        return policies_path
