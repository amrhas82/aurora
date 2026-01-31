#!/usr/bin/env python3
"""Check for performance regression by comparing profiling reports.

This script compares a current profiling report against a baseline and
exits with error code if performance has regressed beyond threshold.

Useful for CI/CD pipelines to catch performance degradation.

Usage:
    python check_performance_regression.py \\
        --current reports/current.json \\
        --baseline reports/baseline.json \\
        --threshold 1.2  # Allow 20% slowdown
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_report(path: Path) -> dict[str, Any]:
    """Load profiling report from JSON file.

    Args:
        path: Path to report JSON

    Returns:
        Report dictionary

    Raises:
        FileNotFoundError: If report file doesn't exist
        json.JSONDecodeError: If report is invalid JSON
    """
    if not path.exists():
        raise FileNotFoundError(f"Report not found: {path}")

    with open(path) as f:
        return json.load(f)


def check_regression(
    current: dict[str, Any],
    baseline: dict[str, Any],
    threshold: float = 1.2,
) -> tuple[bool, list[str]]:
    """Check if current performance has regressed vs baseline.

    Args:
        current: Current profiling report
        baseline: Baseline profiling report
        threshold: Regression threshold (1.2 = allow 20% slowdown)

    Returns:
        Tuple of (passed, messages):
        - passed: True if no regression detected
        - messages: List of status messages
    """
    messages = []
    passed = True

    # Extract statistics
    current_stats = current.get("statistics", {})
    baseline_stats = baseline.get("statistics", {})

    if "error" in current_stats:
        messages.append(f"❌ FAIL: Current profiling failed - {current_stats['error']}")
        return False, messages

    if "error" in baseline_stats:
        messages.append(f"⚠️  WARNING: Baseline profiling has error - {baseline_stats['error']}")
        messages.append("   Skipping regression check")
        return True, messages

    # Check total load time (primary metric)
    current_total = current_stats.get("total_load_time", {}).get("mean", 0)
    baseline_total = baseline_stats.get("total_load_time", {}).get("mean", 0)

    if current_total == 0 or baseline_total == 0:
        messages.append("⚠️  WARNING: Missing timing data, skipping regression check")
        return True, messages

    ratio = current_total / baseline_total
    pct_change = (ratio - 1.0) * 100

    messages.append(f"📊 Performance Comparison")
    messages.append(f"   Baseline total load time: {baseline_total:.2f}s")
    messages.append(f"   Current total load time:  {current_total:.2f}s")
    messages.append(f"   Change: {pct_change:+.1f}%")
    messages.append(f"   Threshold: {(threshold - 1.0) * 100:.1f}%")
    messages.append("")

    if ratio > threshold:
        messages.append(
            f"❌ REGRESSION DETECTED: Performance degraded by {pct_change:.1f}% "
            f"(threshold: {(threshold - 1.0) * 100:.1f}%)"
        )
        passed = False
    elif ratio > 1.05:  # More than 5% slower
        messages.append(
            f"⚠️  WARNING: Performance slightly degraded by {pct_change:.1f}% "
            f"(within threshold but worth investigating)"
        )
    elif ratio < 0.95:  # More than 5% faster
        messages.append(f"✓ IMPROVEMENT: Performance improved by {-pct_change:.1f}%")
    else:
        messages.append(f"✓ PASS: Performance is similar (change: {pct_change:+.1f}%)")

    # Check memory if available
    current_memory = current_stats.get("memory_usage_mb", {}).get("mean", 0)
    baseline_memory = baseline_stats.get("memory_usage_mb", {}).get("mean", 0)

    if current_memory > 0 and baseline_memory > 0:
        memory_ratio = current_memory / baseline_memory
        memory_change = (memory_ratio - 1.0) * 100

        messages.append("")
        messages.append(f"💾 Memory Usage Comparison")
        messages.append(f"   Baseline memory: {baseline_memory:.0f}MB")
        messages.append(f"   Current memory:  {current_memory:.0f}MB")
        messages.append(f"   Change: {memory_change:+.1f}%")

        # Memory threshold is more lenient (50% increase allowed)
        memory_threshold = 1.5
        if memory_ratio > memory_threshold:
            messages.append(
                f"   ⚠️  WARNING: Memory usage increased significantly "
                f"({memory_change:.1f}% > {(memory_threshold - 1.0) * 100:.0f}%)"
            )
            # Don't fail on memory, just warn
        elif memory_ratio < 0.9:
            messages.append(f"   ✓ Memory usage improved by {-memory_change:.1f}%")
        else:
            messages.append(f"   ✓ Memory usage is similar")

    # Detailed breakdown (informational only)
    messages.append("")
    messages.append(f"📈 Detailed Breakdown")

    for metric_name, display_name in [
        ("import_time", "Import Time"),
        ("model_init_time", "Model Init"),
        ("first_encode_time", "First Encode"),
    ]:
        current_val = current_stats.get(metric_name, {}).get("mean", 0)
        baseline_val = baseline_stats.get(metric_name, {}).get("mean", 0)

        if current_val > 0 and baseline_val > 0:
            metric_ratio = current_val / baseline_val
            metric_change = (metric_ratio - 1.0) * 100

            status = "↑" if metric_ratio > 1.05 else "↓" if metric_ratio < 0.95 else "≈"
            messages.append(
                f"   {status} {display_name:15} {current_val:.2f}s "
                f"({metric_change:+.1f}% vs {baseline_val:.2f}s)"
            )

    return passed, messages


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check for performance regression vs baseline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to current profiling report JSON",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline profiling report JSON",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=1.2,
        help="Regression threshold as ratio (1.2 = allow 20%% slowdown, default: 1.2)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("PERFORMANCE REGRESSION CHECK")
    print("=" * 80)
    print()

    # Load reports
    try:
        print(f"📂 Loading reports...")
        print(f"   Baseline: {args.baseline}")
        baseline = load_report(args.baseline)
        print(f"   Current:  {args.current}")
        current = load_report(args.current)
        print()
    except FileNotFoundError as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON - {e}")
        sys.exit(1)

    # Check for regression
    passed, messages = check_regression(current, baseline, args.threshold)

    # Print messages
    for msg in messages:
        print(msg)

    print()
    print("=" * 80)

    # Exit with appropriate code
    if passed:
        print("✓ PASSED: No performance regression detected")
        print("=" * 80)
        sys.exit(0)
    else:
        print("❌ FAILED: Performance regression detected")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
