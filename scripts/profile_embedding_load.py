#!/usr/bin/env python3
"""Profile and measure embedding model load time to establish baseline metrics.

This script provides comprehensive profiling of the embedding model loading process,
measuring various stages and generating detailed reports with baseline metrics.

Features:
- Cold start (first load) vs warm start (cached) benchmarking
- Stage-by-stage timing breakdown
- Memory usage profiling
- Multiple run statistics with confidence intervals
- JSON report generation for tracking over time
- Comparison against performance targets

Usage:
    python profile_embedding_load.py [--runs 5] [--model all-MiniLM-L6-v2] [--output report.json]
"""

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "context-code" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "core" / "src"))


@dataclass
class LoadMetrics:
    """Metrics for a single embedding model load."""

    run_id: int
    model_name: str
    total_load_time: float
    import_time: float
    model_init_time: float
    first_encode_time: float
    memory_mb: float
    cache_status: str  # "cold" or "warm"
    success: bool
    error: str | None = None


@dataclass
class ProfilingReport:
    """Complete profiling report with statistics."""

    model_name: str
    timestamp: str
    num_runs: int
    cache_status: str
    metrics: list[dict[str, Any]]
    statistics: dict[str, Any]
    performance_targets: dict[str, Any]
    recommendations: list[str]


def clear_model_cache(model_name: str) -> bool:
    """Clear the HuggingFace cache for a model (for cold start testing).

    Args:
        model_name: Model identifier

    Returns:
        True if cache was cleared or didn't exist
    """
    from aurora_context_code.semantic.model_utils import get_model_cache_path

    cache_path = get_model_cache_path(model_name)

    if not cache_path.exists():
        print(f"  Cache not found at {cache_path}")
        return True

    try:
        import shutil

        shutil.rmtree(cache_path)
        print(f"  Cleared cache at {cache_path}")
        return True
    except Exception as e:
        print(f"  ERROR: Failed to clear cache: {e}")
        return False


def get_memory_usage_mb() -> float:
    """Get current process memory usage in MB.

    Returns:
        Memory usage in MB, or 0 if unable to measure
    """
    try:
        import psutil

        process = psutil.Process()
        mem_info = process.memory_info()
        return mem_info.rss / 1024 / 1024  # Convert bytes to MB
    except ImportError:
        return 0.0
    except Exception:
        return 0.0


def profile_single_load(
    run_id: int,
    model_name: str,
    cache_status: str,
) -> LoadMetrics:
    """Profile a single model loading operation.

    Args:
        run_id: Run identifier
        model_name: Model to load
        cache_status: "cold" or "warm"

    Returns:
        LoadMetrics with timing breakdown
    """
    print(f"\n  Run #{run_id + 1} ({cache_status} start)")

    mem_before = get_memory_usage_mb()
    total_start = time.perf_counter()

    try:
        # Stage 1: Import sentence-transformers
        print("    [1/4] Importing dependencies...", end="", flush=True)
        import_start = time.perf_counter()
        from sentence_transformers import SentenceTransformer

        import_time = time.perf_counter() - import_start
        print(f" {import_time:.2f}s")

        # Stage 2: Initialize model (downloads if needed)
        print("    [2/4] Loading model...", end="", flush=True)
        init_start = time.perf_counter()

        # Set offline mode for warm start to avoid network checks
        if cache_status == "warm":
            os.environ["HF_HUB_OFFLINE"] = "1"

        model = SentenceTransformer(model_name)
        model_init_time = time.perf_counter() - init_start
        print(f" {model_init_time:.2f}s")

        # Stage 3: First encode (model warmup)
        print("    [3/4] First encode (warmup)...", end="", flush=True)
        encode_start = time.perf_counter()
        test_text = "def calculate_total(items): return sum(item.price for item in items)"
        _ = model.encode(test_text, show_progress_bar=False, convert_to_numpy=True)
        first_encode_time = time.perf_counter() - encode_start
        print(f" {first_encode_time:.2f}s")

        # Stage 4: Memory measurement
        print("    [4/4] Measuring memory...", end="", flush=True)
        mem_after = get_memory_usage_mb()
        memory_mb = mem_after - mem_before
        print(f" {memory_mb:.1f}MB")

        total_load_time = time.perf_counter() - total_start

        print(f"    ✓ Total: {total_load_time:.2f}s")

        return LoadMetrics(
            run_id=run_id,
            model_name=model_name,
            total_load_time=total_load_time,
            import_time=import_time,
            model_init_time=model_init_time,
            first_encode_time=first_encode_time,
            memory_mb=memory_mb,
            cache_status=cache_status,
            success=True,
        )

    except Exception as e:
        print(f" ERROR: {e}")
        total_load_time = time.perf_counter() - total_start

        return LoadMetrics(
            run_id=run_id,
            model_name=model_name,
            total_load_time=total_load_time,
            import_time=0.0,
            model_init_time=0.0,
            first_encode_time=0.0,
            memory_mb=0.0,
            cache_status=cache_status,
            success=False,
            error=str(e),
        )


def calculate_statistics(metrics: list[LoadMetrics]) -> dict[str, Any]:
    """Calculate statistics from multiple runs.

    Args:
        metrics: List of load metrics

    Returns:
        Dictionary with statistics
    """
    successful_runs = [m for m in metrics if m.success]

    if not successful_runs:
        return {"error": "No successful runs"}

    # Calculate mean and std for each metric
    total_times = [m.total_load_time for m in successful_runs]
    import_times = [m.import_time for m in successful_runs]
    init_times = [m.model_init_time for m in successful_runs]
    encode_times = [m.first_encode_time for m in successful_runs]
    memory_usages = [m.memory_mb for m in successful_runs]

    def stats(values: list[float]) -> dict[str, float]:
        """Calculate basic statistics."""
        import statistics

        return {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
        }

    return {
        "num_successful_runs": len(successful_runs),
        "num_failed_runs": len(metrics) - len(successful_runs),
        "total_load_time": stats(total_times),
        "import_time": stats(import_times),
        "model_init_time": stats(init_times),
        "first_encode_time": stats(encode_times),
        "memory_usage_mb": stats(memory_usages),
    }


def generate_recommendations(
    statistics: dict[str, Any],
    cache_status: str,
    targets: dict[str, float],
) -> list[str]:
    """Generate recommendations based on profiling results.

    Args:
        statistics: Profiling statistics
        cache_status: Cache status during profiling
        targets: Performance targets

    Returns:
        List of recommendation strings
    """
    recommendations = []

    if "error" in statistics:
        recommendations.append(
            "ERROR: No successful runs. Check dependencies and model availability."
        )
        return recommendations

    total_time = statistics["total_load_time"]["mean"]
    target_time = targets.get("max_load_time_s", 5.0)

    if cache_status == "warm":
        if total_time > target_time:
            recommendations.append(
                f"⚠️  Warm start time ({total_time:.2f}s) exceeds target ({target_time:.1f}s)"
            )
            recommendations.append(
                "   Consider: Background loading, lazy initialization, or smaller model"
            )
        else:
            recommendations.append(
                f"✓ Warm start time ({total_time:.2f}s) meets target ({target_time:.1f}s)"
            )

        # Breakdown analysis
        import_time = statistics["import_time"]["mean"]
        init_time = statistics["model_init_time"]["mean"]

        if import_time > 1.0:
            recommendations.append(
                f"⚠️  Import time is high ({import_time:.2f}s). "
                f"Consider lazy imports or lighter dependencies."
            )

        if init_time > 3.0:
            recommendations.append(
                f"⚠️  Model init time is high ({init_time:.2f}s). "
                f"Background loading recommended."
            )

    else:  # cold start
        if total_time > target_time * 6:  # Cold starts can be 6x slower
            recommendations.append(
                f"⚠️  Cold start time ({total_time:.2f}s) is very slow. "
                f"Ensure model is cached for production."
            )

    # Memory recommendations
    memory = statistics["memory_usage_mb"]["mean"]
    if memory > 500:
        recommendations.append(
            f"⚠️  High memory usage ({memory:.0f}MB). " f"Consider smaller model or quantization."
        )
    elif memory > 0:
        recommendations.append(f"✓ Acceptable memory usage ({memory:.0f}MB)")

    return recommendations


def profile_embedding_load(
    model_name: str = "all-MiniLM-L6-v2",
    num_runs: int = 5,
    cold_start: bool = False,
) -> ProfilingReport:
    """Profile embedding model loading with multiple runs.

    Args:
        model_name: Model to profile
        num_runs: Number of profiling runs
        cold_start: If True, clear cache before profiling

    Returns:
        ProfilingReport with metrics and statistics
    """
    from datetime import datetime

    print("=" * 80)
    print("EMBEDDING MODEL LOAD PROFILING")
    print("=" * 80)
    print(f"\nModel: {model_name}")
    print(f"Runs: {num_runs}")

    cache_status = "cold" if cold_start else "warm"

    if cold_start:
        print("\n🗑️  Clearing model cache for cold start testing...")
        if not clear_model_cache(model_name):
            print("WARNING: Could not clear cache, results may be inaccurate")
    else:
        print(f"\n📦 Using cached model (warm start)")

    # Define performance targets
    targets = {
        "max_load_time_s": 5.0,  # Target max 5 seconds for warm start
        "max_import_time_s": 1.0,  # Target max 1 second for imports
        "max_model_init_s": 3.0,  # Target max 3 seconds for model loading
        "max_first_encode_ms": 200,  # Target max 200ms for first encode
        "max_memory_mb": 500,  # Target max 500MB memory usage
    }

    # Run profiling
    print(f"\n🔍 Running {num_runs} profiling iterations...")
    metrics = []

    for i in range(num_runs):
        # Force garbage collection between runs
        import gc

        gc.collect()

        # Small delay between runs
        if i > 0:
            time.sleep(0.5)

        metric = profile_single_load(i, model_name, cache_status)
        metrics.append(metric)

    # Calculate statistics
    print("\n📊 Calculating statistics...")
    statistics = calculate_statistics(metrics)

    # Generate recommendations
    print("\n💡 Analyzing results...")
    recommendations = generate_recommendations(statistics, cache_status, targets)

    # Create report
    report = ProfilingReport(
        model_name=model_name,
        timestamp=datetime.now().isoformat(),
        num_runs=num_runs,
        cache_status=cache_status,
        metrics=[asdict(m) for m in metrics],
        statistics=statistics,
        performance_targets=targets,
        recommendations=recommendations,
    )

    return report


def print_report(report: ProfilingReport) -> None:
    """Print profiling report to console.

    Args:
        report: Profiling report to display
    """
    print("\n" + "=" * 80)
    print("PROFILING RESULTS")
    print("=" * 80)

    stats = report.statistics

    if "error" in stats:
        print(f"\n❌ ERROR: {stats['error']}")
        return

    # Summary
    print(f"\n📋 Summary ({report.cache_status.upper()} START)")
    print(f"   Model: {report.model_name}")
    print(f"   Runs: {report.num_runs} ({stats['num_successful_runs']} successful)")
    print(f"   Timestamp: {report.timestamp}")

    # Timing breakdown
    print(f"\n⏱️  Timing Breakdown (mean ± stdev)")
    print("-" * 80)

    def format_stat(stat_dict: dict[str, float], unit: str = "s") -> str:
        """Format statistics for display."""
        mean = stat_dict["mean"]
        stdev = stat_dict["stdev"]
        min_val = stat_dict["min"]
        max_val = stat_dict["max"]
        return f"{mean:.2f} ± {stdev:.2f}{unit}  (range: {min_val:.2f}-{max_val:.2f}{unit})"

    print(f"   Total Load Time:       {format_stat(stats['total_load_time'])}")
    print(f"   ├─ Import Time:        {format_stat(stats['import_time'])}")
    print(f"   ├─ Model Init Time:    {format_stat(stats['model_init_time'])}")
    print(f"   └─ First Encode Time:  {format_stat(stats['first_encode_time'])}")

    # Memory
    print(f"\n💾 Memory Usage")
    print("-" * 80)
    memory_stats = stats["memory_usage_mb"]
    if memory_stats["mean"] > 0:
        print(f"   Memory Delta:  {format_stat(memory_stats, 'MB')}")
    else:
        print("   Memory Delta:  Not measured (psutil not available)")

    # Performance vs Targets
    print(f"\n🎯 Performance vs Targets")
    print("-" * 80)
    targets = report.performance_targets

    def check_target(actual: float, target: float, name: str, unit: str) -> None:
        """Print target comparison."""
        status = "✓" if actual <= target else "⚠️"
        print(f"   {status} {name:<25} {actual:.2f}{unit} / {target:.1f}{unit} target")

    check_target(stats["total_load_time"]["mean"], targets["max_load_time_s"], "Total Load", "s")
    check_target(stats["import_time"]["mean"], targets["max_import_time_s"], "Import", "s")
    check_target(stats["model_init_time"]["mean"], targets["max_model_init_s"], "Model Init", "s")
    check_target(
        stats["first_encode_time"]["mean"] * 1000,
        targets["max_first_encode_ms"],
        "First Encode",
        "ms",
    )
    if memory_stats["mean"] > 0:
        check_target(memory_stats["mean"], targets["max_memory_mb"], "Memory Usage", "MB")

    # Recommendations
    print(f"\n💡 Recommendations")
    print("-" * 80)
    for rec in report.recommendations:
        print(f"   {rec}")

    print("\n" + "=" * 80)


def save_report(report: ProfilingReport, output_path: Path) -> None:
    """Save profiling report to JSON file.

    Args:
        report: Profiling report
        output_path: Path to save report
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report_dict = asdict(report)

    with open(output_path, "w") as f:
        json.dump(report_dict, f, indent=2)

    print(f"\n💾 Report saved to: {output_path}")


def compare_with_baseline(current_report: ProfilingReport, baseline_path: Path) -> None:
    """Compare current results with baseline report.

    Args:
        current_report: Current profiling report
        baseline_path: Path to baseline report JSON
    """
    if not baseline_path.exists():
        print(f"\n📝 No baseline found at {baseline_path}")
        print("   This report can serve as the baseline for future comparisons.")
        return

    try:
        with open(baseline_path) as f:
            baseline_data = json.load(f)

        baseline_stats = baseline_data["statistics"]
        current_stats = current_report.statistics

        print("\n" + "=" * 80)
        print("COMPARISON WITH BASELINE")
        print("=" * 80)

        def compare_metric(name: str, baseline_val: float, current_val: float, unit: str) -> None:
            """Print metric comparison."""
            diff = current_val - baseline_val
            pct_change = (diff / baseline_val * 100) if baseline_val > 0 else 0

            if abs(pct_change) < 5:
                status = "≈"  # Similar
                color = ""
            elif pct_change < 0:
                status = "↓"  # Improved
                color = "✓"
            else:
                status = "↑"  # Regressed
                color = "⚠️"

            print(
                f"   {color} {name:<25} {current_val:.2f}{unit} {status} "
                f"({pct_change:+.1f}% vs baseline {baseline_val:.2f}{unit})"
            )

        compare_metric(
            "Total Load Time",
            baseline_stats["total_load_time"]["mean"],
            current_stats["total_load_time"]["mean"],
            "s",
        )
        compare_metric(
            "Import Time",
            baseline_stats["import_time"]["mean"],
            current_stats["import_time"]["mean"],
            "s",
        )
        compare_metric(
            "Model Init Time",
            baseline_stats["model_init_time"]["mean"],
            current_stats["model_init_time"]["mean"],
            "s",
        )

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n⚠️  Could not compare with baseline: {e}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Profile embedding model load time and establish baseline metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--model",
        type=str,
        default="all-MiniLM-L6-v2",
        help="Model to profile (default: all-MiniLM-L6-v2)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of profiling runs (default: 5)",
    )
    parser.add_argument(
        "--cold-start",
        action="store_true",
        help="Clear cache and test cold start (default: warm start)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to save JSON report (default: reports/embedding_load_baseline.json)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Path to baseline report for comparison",
    )

    args = parser.parse_args()

    # Set default output path
    if args.output is None:
        cache_type = "cold" if args.cold_start else "warm"
        default_name = f"embedding_load_{cache_type}_baseline.json"
        args.output = Path(__file__).parent.parent / "reports" / default_name

    # Run profiling
    report = profile_embedding_load(
        model_name=args.model,
        num_runs=args.runs,
        cold_start=args.cold_start,
    )

    # Print results
    print_report(report)

    # Save report
    save_report(report, args.output)

    # Compare with baseline if provided
    if args.baseline:
        compare_with_baseline(report, args.baseline)

    # Exit with appropriate code
    if "error" in report.statistics:
        sys.exit(1)


if __name__ == "__main__":
    main()
