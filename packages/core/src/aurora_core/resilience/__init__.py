"""Resilience module for AURORA.

This module provides production hardening features including:
- RetryHandler: Exponential backoff retry logic for transient errors
- MetricsCollector: Performance and reliability metrics tracking
- RateLimiter: Token bucket rate limiting
- Alerting: Alert rules and notification system
"""

from aurora_core.resilience.alerting import Alert, Alerting, AlertRule, AlertSeverity
from aurora_core.resilience.metrics_collector import MetricsCollector
from aurora_core.resilience.rate_limiter import RateLimiter
from aurora_core.resilience.retry_handler import RetryHandler


__all__ = [
    "RetryHandler",
    "MetricsCollector",
    "RateLimiter",
    "Alerting",
    "Alert",
    "AlertRule",
    "AlertSeverity",
]
