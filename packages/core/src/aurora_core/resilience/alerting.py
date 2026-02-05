"""Alerting system for monitoring and notifications.

Implements alert rules and notifications following PRD Section 5.4.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """Defines an alert rule with threshold and severity.

    Attributes:
        name: Human-readable name for the alert
        metric_name: Name of the metric to monitor (e.g., "error_rate")
        threshold: Threshold value that triggers the alert
        comparison: Comparison operator ("gt", "lt", "gte", "lte", "eq")
        severity: Alert severity level
        description: Human-readable description of what the alert means

    """

    name: str
    metric_name: str
    threshold: float
    comparison: str
    severity: AlertSeverity
    description: str

    def evaluate(self, metric_value: float) -> bool:
        """Evaluate if the metric value triggers this alert.

        Args:
            metric_value: Current value of the metric

        Returns:
            True if alert should fire, False otherwise

        """
        if self.comparison == "gt":
            return metric_value > self.threshold
        if self.comparison == "gte":
            return metric_value >= self.threshold
        if self.comparison == "lt":
            return metric_value < self.threshold
        if self.comparison == "lte":
            return metric_value <= self.threshold
        if self.comparison == "eq":
            return metric_value == self.threshold
        raise ValueError(f"Unknown comparison operator: {self.comparison}")


@dataclass
class Alert:
    """Represents a fired alert.

    Attributes:
        rule_name: Name of the rule that triggered
        metric_name: Name of the metric
        metric_value: Current value that triggered the alert
        threshold: Threshold that was exceeded
        severity: Alert severity
        message: Human-readable alert message

    """

    rule_name: str
    metric_name: str
    metric_value: float
    threshold: float
    severity: AlertSeverity
    message: str


class Alerting:
    """Manages alert rules and notifications.

    This class provides a centralized alerting system that:
    - Defines alert rules based on metrics thresholds
    - Evaluates metrics against rules
    - Fires alerts when thresholds are exceeded
    - Sends notifications via logging or webhooks

    **Default Alert Rules** (PRD Section 5.4):
    - Error Rate > 5%: WARNING
    - P95 Latency > 10s: WARNING
    - Cache Hit Rate < 20%: WARNING

    **Notification Channels**:
    - Log warnings (always enabled)
    - Webhook integration (optional, configured via callback)

    Example:
        >>> alerting = Alerting()
        >>> # Add default rules
        >>> alerting.add_default_rules()
        >>>
        >>> # Evaluate metrics
        >>> metrics = {"error_rate": 0.08, "p95_latency": 12.0}
        >>> alerts = alerting.evaluate(metrics)
        >>> for alert in alerts:
        >>>     print(f"ALERT: {alert.message}")
        >>>
        >>> # Add webhook notification
        >>> def webhook_handler(alert: Alert):
        >>>     # Send to monitoring system
        >>>     pass
        >>> alerting.add_notification_handler(webhook_handler)

    """

    def __init__(self) -> None:
        """Initialize the Alerting system."""
        self.rules: dict[str, AlertRule] = {}
        self.notification_handlers: list[Callable[[Alert], None]] = []
        self.fired_alerts: list[Alert] = []

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule.

        Args:
            rule: The alert rule to add

        Raises:
            ValueError: If a rule with the same name already exists

        """
        if rule.name in self.rules:
            raise ValueError(f"Alert rule '{rule.name}' already exists")
        self.rules[rule.name] = rule

    def remove_rule(self, rule_name: str) -> None:
        """Remove an alert rule by name.

        Args:
            rule_name: Name of the rule to remove

        Raises:
            KeyError: If rule does not exist

        """
        if rule_name not in self.rules:
            raise KeyError(f"Alert rule '{rule_name}' not found")
        del self.rules[rule_name]

    def add_default_rules(self) -> None:
        """Add default alert rules as specified in PRD Section 5.4.

        Default rules:
        - Error Rate > 5%: WARNING
        - P95 Latency > 10s: WARNING
        - Cache Hit Rate < 20%: WARNING
        """
        default_rules = [
            AlertRule(
                name="high_error_rate",
                metric_name="error_rate",
                threshold=0.05,  # 5%
                comparison="gt",
                severity=AlertSeverity.WARNING,
                description="Error rate has exceeded 5% threshold",
            ),
            AlertRule(
                name="high_p95_latency",
                metric_name="p95_latency",
                threshold=10.0,  # 10 seconds
                comparison="gt",
                severity=AlertSeverity.WARNING,
                description="P95 latency has exceeded 10s threshold",
            ),
            AlertRule(
                name="low_cache_hit_rate",
                metric_name="cache_hit_rate",
                threshold=0.20,  # 20%
                comparison="lt",
                severity=AlertSeverity.WARNING,
                description="Cache hit rate has fallen below 20% threshold",
            ),
        ]

        for rule in default_rules:
            # Skip if rule already exists
            if rule.name not in self.rules:
                self.rules[rule.name] = rule

    def add_notification_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a notification handler for alerts.

        The handler will be called for each fired alert. Handlers can be used
        to send alerts to external systems (webhooks, email, SMS, etc.).

        Args:
            handler: Callable that takes an Alert and sends notification

        """
        self.notification_handlers.append(handler)

    def evaluate(self, metrics: dict[str, float]) -> list[Alert]:
        """Evaluate all rules against provided metrics.

        Args:
            metrics: Dictionary of metric_name -> value

        Returns:
            List of alerts that were triggered

        Example:
            >>> metrics = {
            >>>     "error_rate": 0.08,
            >>>     "p95_latency": 12.0,
            >>>     "cache_hit_rate": 0.15
            >>> }
            >>> alerts = alerting.evaluate(metrics)
            >>> # Returns 3 alerts (all thresholds exceeded)

        """
        alerts = []

        for rule in self.rules.values():
            # Skip if metric not present in metrics dict
            if rule.metric_name not in metrics:
                continue

            metric_value = metrics[rule.metric_name]

            # Evaluate rule
            if rule.evaluate(metric_value):
                alert = Alert(
                    rule_name=rule.name,
                    metric_name=rule.metric_name,
                    metric_value=metric_value,
                    threshold=rule.threshold,
                    severity=rule.severity,
                    message=f"{rule.description}: {metric_value:.4f} "
                    f"({rule.comparison} {rule.threshold})",
                )
                alerts.append(alert)
                self.fired_alerts.append(alert)

                # Send notifications
                self._notify(alert)

        return alerts

    def _notify(self, alert: Alert) -> None:
        """Send notifications for an alert.

        Logs the alert and calls all registered notification handlers.

        Args:
            alert: The alert to notify about

        """
        # Always log the alert
        log_level = (
            logging.CRITICAL if alert.severity == AlertSeverity.CRITICAL else logging.WARNING
        )
        logger.log(log_level, f"ALERT [{alert.severity.value.upper()}]: {alert.message}")

        # Call custom handlers
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in notification handler: {e}", exc_info=True)

    def get_fired_alerts(self, severity: AlertSeverity | None = None) -> list[Alert]:
        """Get list of all fired alerts, optionally filtered by severity.

        Args:
            severity: Optional severity filter

        Returns:
            List of fired alerts

        """
        if severity is None:
            return list(self.fired_alerts)
        return [a for a in self.fired_alerts if a.severity == severity]

    def clear_alerts(self) -> None:
        """Clear the history of fired alerts."""
        self.fired_alerts.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get alerting statistics.

        Returns:
            Dictionary with statistics:
            {
                "total_rules": int,
                "total_alerts": int,
                "alerts_by_severity": dict[str, int],
                "alerts_by_rule": dict[str, int]
            }

        """
        alerts_by_severity = {
            severity.value: sum(1 for a in self.fired_alerts if a.severity == severity)
            for severity in AlertSeverity
        }

        alerts_by_rule: dict[str, int] = {}
        for alert in self.fired_alerts:
            alerts_by_rule[alert.rule_name] = alerts_by_rule.get(alert.rule_name, 0) + 1

        return {
            "total_rules": len(self.rules),
            "total_alerts": len(self.fired_alerts),
            "alerts_by_severity": alerts_by_severity,
            "alerts_by_rule": alerts_by_rule,
        }
