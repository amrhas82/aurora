"""
Unit tests for Alerting class.

Tests alert rules and notification system.
"""

import logging
from unittest.mock import Mock, patch
import pytest

from aurora_core.resilience.alerting import (
    Alerting,
    Alert,
    AlertRule,
    AlertSeverity,
)


class TestAlertSeverity:
    """Test AlertSeverity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertRule:
    """Test AlertRule dataclass."""

    def test_rule_creation(self):
        """Test creating an alert rule."""
        rule = AlertRule(
            name="high_error_rate",
            metric_name="error_rate",
            threshold=0.05,
            comparison="gt",
            severity=AlertSeverity.WARNING,
            description="Error rate too high",
        )

        assert rule.name == "high_error_rate"
        assert rule.metric_name == "error_rate"
        assert rule.threshold == 0.05
        assert rule.comparison == "gt"
        assert rule.severity == AlertSeverity.WARNING

    def test_rule_evaluate_greater_than(self):
        """Test rule evaluation with greater than."""
        rule = AlertRule(
            name="test",
            metric_name="error_rate",
            threshold=0.05,
            comparison="gt",
            severity=AlertSeverity.WARNING,
            description="Test",
        )

        assert rule.evaluate(0.06) is True
        assert rule.evaluate(0.05) is False
        assert rule.evaluate(0.04) is False

    def test_rule_evaluate_greater_than_or_equal(self):
        """Test rule evaluation with greater than or equal."""
        rule = AlertRule(
            name="test",
            metric_name="latency",
            threshold=10.0,
            comparison="gte",
            severity=AlertSeverity.WARNING,
            description="Test",
        )

        assert rule.evaluate(10.1) is True
        assert rule.evaluate(10.0) is True
        assert rule.evaluate(9.9) is False

    def test_rule_evaluate_less_than(self):
        """Test rule evaluation with less than."""
        rule = AlertRule(
            name="test",
            metric_name="cache_hit_rate",
            threshold=0.20,
            comparison="lt",
            severity=AlertSeverity.WARNING,
            description="Test",
        )

        assert rule.evaluate(0.19) is True
        assert rule.evaluate(0.20) is False
        assert rule.evaluate(0.21) is False

    def test_rule_evaluate_less_than_or_equal(self):
        """Test rule evaluation with less than or equal."""
        rule = AlertRule(
            name="test",
            metric_name="cache_hit_rate",
            threshold=0.20,
            comparison="lte",
            severity=AlertSeverity.WARNING,
            description="Test",
        )

        assert rule.evaluate(0.19) is True
        assert rule.evaluate(0.20) is True
        assert rule.evaluate(0.21) is False

    def test_rule_evaluate_equal(self):
        """Test rule evaluation with equal."""
        rule = AlertRule(
            name="test",
            metric_name="count",
            threshold=100.0,
            comparison="eq",
            severity=AlertSeverity.INFO,
            description="Test",
        )

        assert rule.evaluate(100.0) is True
        assert rule.evaluate(100.1) is False
        assert rule.evaluate(99.9) is False

    def test_rule_evaluate_invalid_comparison(self):
        """Test invalid comparison operator."""
        rule = AlertRule(
            name="test",
            metric_name="test",
            threshold=1.0,
            comparison="invalid",
            severity=AlertSeverity.WARNING,
            description="Test",
        )

        with pytest.raises(ValueError, match="Unknown comparison operator"):
            rule.evaluate(1.0)


class TestAlertingInitialization:
    """Test Alerting initialization."""

    def test_default_initialization(self):
        """Test Alerting initializes with empty state."""
        alerting = Alerting()

        assert len(alerting.rules) == 0
        assert len(alerting.notification_handlers) == 0
        assert len(alerting.fired_alerts) == 0


class TestAlertingRuleManagement:
    """Test alert rule management."""

    def test_add_rule(self):
        """Test adding an alert rule."""
        alerting = Alerting()

        rule = AlertRule(
            name="high_error_rate",
            metric_name="error_rate",
            threshold=0.05,
            comparison="gt",
            severity=AlertSeverity.WARNING,
            description="Error rate too high",
        )

        alerting.add_rule(rule)

        assert len(alerting.rules) == 1
        assert "high_error_rate" in alerting.rules
        assert alerting.rules["high_error_rate"] == rule

    def test_add_duplicate_rule(self):
        """Test adding duplicate rule raises error."""
        alerting = Alerting()

        rule = AlertRule(
            name="test",
            metric_name="metric",
            threshold=1.0,
            comparison="gt",
            severity=AlertSeverity.WARNING,
            description="Test",
        )

        alerting.add_rule(rule)

        with pytest.raises(ValueError, match="already exists"):
            alerting.add_rule(rule)

    def test_remove_rule(self):
        """Test removing an alert rule."""
        alerting = Alerting()

        rule = AlertRule(
            name="test",
            metric_name="metric",
            threshold=1.0,
            comparison="gt",
            severity=AlertSeverity.WARNING,
            description="Test",
        )

        alerting.add_rule(rule)
        assert len(alerting.rules) == 1

        alerting.remove_rule("test")
        assert len(alerting.rules) == 0

    def test_remove_nonexistent_rule(self):
        """Test removing nonexistent rule raises error."""
        alerting = Alerting()

        with pytest.raises(KeyError, match="not found"):
            alerting.remove_rule("nonexistent")

    def test_add_default_rules(self):
        """Test adding default rules."""
        alerting = Alerting()
        alerting.add_default_rules()

        assert len(alerting.rules) == 3
        assert "high_error_rate" in alerting.rules
        assert "high_p95_latency" in alerting.rules
        assert "low_cache_hit_rate" in alerting.rules

        # Check thresholds from PRD
        assert alerting.rules["high_error_rate"].threshold == 0.05  # 5%
        assert alerting.rules["high_p95_latency"].threshold == 10.0  # 10s
        assert alerting.rules["low_cache_hit_rate"].threshold == 0.20  # 20%

    def test_add_default_rules_idempotent(self):
        """Test adding default rules multiple times is idempotent."""
        alerting = Alerting()

        alerting.add_default_rules()
        alerting.add_default_rules()

        # Should still be only 3 rules
        assert len(alerting.rules) == 3


class TestAlertingEvaluation:
    """Test alert evaluation."""

    def test_evaluate_no_alerts(self):
        """Test evaluation with no thresholds exceeded."""
        alerting = Alerting()
        alerting.add_default_rules()

        metrics = {
            "error_rate": 0.01,  # Below 5%
            "p95_latency": 5.0,  # Below 10s
            "cache_hit_rate": 0.80,  # Above 20%
        }

        alerts = alerting.evaluate(metrics)

        assert len(alerts) == 0

    def test_evaluate_single_alert(self):
        """Test evaluation with one threshold exceeded."""
        alerting = Alerting()
        alerting.add_default_rules()

        metrics = {
            "error_rate": 0.08,  # Above 5% threshold
            "p95_latency": 5.0,
            "cache_hit_rate": 0.80,
        }

        alerts = alerting.evaluate(metrics)

        assert len(alerts) == 1
        assert alerts[0].rule_name == "high_error_rate"
        assert alerts[0].metric_value == 0.08
        assert alerts[0].threshold == 0.05

    def test_evaluate_multiple_alerts(self):
        """Test evaluation with multiple thresholds exceeded."""
        alerting = Alerting()
        alerting.add_default_rules()

        metrics = {
            "error_rate": 0.08,  # Above 5%
            "p95_latency": 15.0,  # Above 10s
            "cache_hit_rate": 0.10,  # Below 20%
        }

        alerts = alerting.evaluate(metrics)

        assert len(alerts) == 3
        rule_names = [a.rule_name for a in alerts]
        assert "high_error_rate" in rule_names
        assert "high_p95_latency" in rule_names
        assert "low_cache_hit_rate" in rule_names

    def test_evaluate_missing_metric(self):
        """Test evaluation skips rules for missing metrics."""
        alerting = Alerting()
        alerting.add_default_rules()

        metrics = {
            "error_rate": 0.08,  # Only provide error_rate
        }

        alerts = alerting.evaluate(metrics)

        # Should only check error_rate, skip others
        assert len(alerts) == 1
        assert alerts[0].metric_name == "error_rate"

    def test_evaluate_tracks_fired_alerts(self):
        """Test that fired alerts are tracked."""
        alerting = Alerting()
        alerting.add_default_rules()

        metrics = {
            "error_rate": 0.08,
            "p95_latency": 5.0,
            "cache_hit_rate": 0.80,
        }

        alerting.evaluate(metrics)

        assert len(alerting.fired_alerts) == 1


class TestAlertingNotifications:
    """Test alert notification system."""

    @patch("aurora_core.resilience.alerting.logger")
    def test_notification_logs_alert(self, mock_logger):
        """Test that alerts are logged."""
        alerting = Alerting()
        alerting.add_default_rules()

        metrics = {
            "error_rate": 0.08,
            "p95_latency": 5.0,
            "cache_hit_rate": 0.80,
        }

        alerting.evaluate(metrics)

        # Should have logged one warning
        assert mock_logger.log.called

    def test_add_notification_handler(self):
        """Test adding custom notification handler."""
        alerting = Alerting()

        handler = Mock()
        alerting.add_notification_handler(handler)

        assert len(alerting.notification_handlers) == 1

    @patch("aurora_core.resilience.alerting.logger")
    def test_custom_handler_called(self, mock_logger):
        """Test custom handler is called for alerts."""
        alerting = Alerting()
        alerting.add_default_rules()

        handler = Mock()
        alerting.add_notification_handler(handler)

        metrics = {
            "error_rate": 0.08,
            "p95_latency": 5.0,
            "cache_hit_rate": 0.80,
        }

        alerting.evaluate(metrics)

        # Handler should be called once
        assert handler.call_count == 1
        # Handler should receive Alert object
        assert isinstance(handler.call_args[0][0], Alert)

    @patch("aurora_core.resilience.alerting.logger")
    def test_handler_exception_logged(self, mock_logger):
        """Test that handler exceptions are logged and don't propagate."""
        alerting = Alerting()
        alerting.add_default_rules()

        def failing_handler(alert):
            raise RuntimeError("Handler failed")

        alerting.add_notification_handler(failing_handler)

        metrics = {
            "error_rate": 0.08,
            "p95_latency": 5.0,
            "cache_hit_rate": 0.80,
        }

        # Should not raise exception
        alerting.evaluate(metrics)

        # Should have logged error
        assert mock_logger.error.called


class TestAlertingHistory:
    """Test alert history management."""

    def test_get_fired_alerts(self):
        """Test retrieving fired alerts."""
        alerting = Alerting()
        alerting.add_default_rules()

        metrics = {
            "error_rate": 0.08,
            "p95_latency": 5.0,
            "cache_hit_rate": 0.80,
        }

        alerting.evaluate(metrics)

        fired = alerting.get_fired_alerts()
        assert len(fired) == 1
        assert fired[0].rule_name == "high_error_rate"

    def test_get_fired_alerts_by_severity(self):
        """Test filtering fired alerts by severity."""
        alerting = Alerting()

        # Add rule with CRITICAL severity
        rule = AlertRule(
            name="critical_error",
            metric_name="critical_count",
            threshold=1.0,
            comparison="gt",
            severity=AlertSeverity.CRITICAL,
            description="Critical error",
        )
        alerting.add_rule(rule)
        alerting.add_default_rules()  # WARNING rules

        metrics = {
            "critical_count": 5.0,  # Triggers CRITICAL
            "error_rate": 0.08,  # Triggers WARNING
        }

        alerting.evaluate(metrics)

        # Get only CRITICAL alerts
        critical = alerting.get_fired_alerts(severity=AlertSeverity.CRITICAL)
        assert len(critical) == 1
        assert critical[0].severity == AlertSeverity.CRITICAL

        # Get only WARNING alerts
        warnings = alerting.get_fired_alerts(severity=AlertSeverity.WARNING)
        assert len(warnings) == 1
        assert warnings[0].severity == AlertSeverity.WARNING

    def test_clear_alerts(self):
        """Test clearing alert history."""
        alerting = Alerting()
        alerting.add_default_rules()

        metrics = {
            "error_rate": 0.08,
            "p95_latency": 5.0,
            "cache_hit_rate": 0.80,
        }

        alerting.evaluate(metrics)
        assert len(alerting.fired_alerts) == 1

        alerting.clear_alerts()
        assert len(alerting.fired_alerts) == 0


class TestAlertingStatistics:
    """Test alerting statistics."""

    def test_get_stats_empty(self):
        """Test statistics with no alerts."""
        alerting = Alerting()
        alerting.add_default_rules()

        stats = alerting.get_stats()

        assert stats["total_rules"] == 3
        assert stats["total_alerts"] == 0
        assert stats["alerts_by_severity"]["info"] == 0
        assert stats["alerts_by_severity"]["warning"] == 0
        assert stats["alerts_by_severity"]["critical"] == 0
        assert len(stats["alerts_by_rule"]) == 0

    def test_get_stats_with_alerts(self):
        """Test statistics with fired alerts."""
        alerting = Alerting()
        alerting.add_default_rules()

        metrics = {
            "error_rate": 0.08,
            "p95_latency": 15.0,
            "cache_hit_rate": 0.10,
        }

        alerting.evaluate(metrics)

        stats = alerting.get_stats()

        assert stats["total_rules"] == 3
        assert stats["total_alerts"] == 3
        assert stats["alerts_by_severity"]["warning"] == 3
        assert stats["alerts_by_rule"]["high_error_rate"] == 1
        assert stats["alerts_by_rule"]["high_p95_latency"] == 1
        assert stats["alerts_by_rule"]["low_cache_hit_rate"] == 1

    def test_get_stats_repeated_alerts(self):
        """Test statistics with repeated alerts."""
        alerting = Alerting()
        alerting.add_default_rules()

        metrics = {
            "error_rate": 0.08,
            "p95_latency": 5.0,
            "cache_hit_rate": 0.80,
        }

        # Evaluate twice
        alerting.evaluate(metrics)
        alerting.evaluate(metrics)

        stats = alerting.get_stats()

        assert stats["total_alerts"] == 2
        assert stats["alerts_by_rule"]["high_error_rate"] == 2
