#!/usr/bin/env python3
"""Investigation script for activation score variance.

This script analyzes the distribution of base_level activation scores
to determine why activation scores in search results are often identical.
"""

import sqlite3
import statistics
from pathlib import Path
from typing import Any


def analyze_activation_distribution(db_path: str) -> dict[str, Any]:
    """Analyze activation score distribution in the database.

    Args:
        db_path: Path to Aurora database

    Returns:
        Dictionary with analysis results
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query all activation data
    cursor.execute("SELECT base_level, access_count FROM activations")
    rows = cursor.fetchall()

    if not rows:
        return {
            "error": "No activation data found in database",
            "total_chunks": 0,
        }

    base_levels = [row[0] for row in rows]
    access_counts = [row[1] for row in rows]

    # Calculate statistics
    results = {
        "total_chunks": len(base_levels),
        "base_level_stats": {
            "min": min(base_levels),
            "max": max(base_levels),
            "mean": statistics.mean(base_levels),
            "median": statistics.median(base_levels),
            "stdev": statistics.stdev(base_levels) if len(base_levels) > 1 else 0.0,
        },
        "access_count_stats": {
            "min": min(access_counts),
            "max": max(access_counts),
            "mean": statistics.mean(access_counts),
            "median": statistics.median(access_counts),
        },
        "distribution": {},
        "zero_access_count": sum(1 for count in access_counts if count == 0),
    }

    # Count distribution of base_level values
    unique_values: dict[float, int] = {}
    for bl in base_levels:
        # Round to 2 decimal places for grouping
        rounded = round(bl, 2)
        unique_values[rounded] = unique_values.get(rounded, 0) + 1

    results["distribution"] = unique_values
    results["unique_values_count"] = len(unique_values)

    # Check if all values are identical
    if len(unique_values) == 1:
        results["all_identical"] = True
        results["identical_value"] = list(unique_values.keys())[0]
    else:
        results["all_identical"] = False

    conn.close()
    return results


def print_analysis(results: dict[str, Any]) -> None:
    """Print analysis results in a readable format."""
    if "error" in results:
        print(f"ERROR: {results['error']}")
        return

    print("=" * 80)
    print("ACTIVATION SCORE VARIANCE INVESTIGATION")
    print("=" * 80)
    print()

    print(f"Total chunks analyzed: {results['total_chunks']}")
    print()

    print("BASE LEVEL STATISTICS:")
    print("-" * 40)
    stats = results["base_level_stats"]
    print(f"  Min:    {stats['min']:.4f}")
    print(f"  Max:    {stats['max']:.4f}")
    print(f"  Mean:   {stats['mean']:.4f}")
    print(f"  Median: {stats['median']:.4f}")
    print(f"  StdDev: {stats['stdev']:.4f}")
    print()

    if results["all_identical"]:
        print(f"⚠️  WARNING: All base_level values are identical: {results['identical_value']:.4f}")
        print()
        print("This explains why activation scores in search results are identical.")
        print("When all input values are the same, min-max normalization produces:")
        print("  - If all values are 0.0: normalized to 0.0")
        print("  - Otherwise: typically normalized to 0.5 or 1.0 depending on algorithm")
        print()
    else:
        print(f"✓ Base level values vary ({results['unique_values_count']} unique values)")
        print()

    print("DISTRIBUTION OF BASE LEVEL VALUES:")
    print("-" * 40)
    dist = results["distribution"]
    # Sort by count (descending)
    sorted_dist = sorted(dist.items(), key=lambda x: x[1], reverse=True)
    for value, count in sorted_dist[:10]:  # Show top 10
        percentage = (count / results["total_chunks"]) * 100
        print(f"  {value:.2f}: {count:5d} chunks ({percentage:5.1f}%)")
    if len(sorted_dist) > 10:
        print(f"  ... and {len(sorted_dist) - 10} more unique values")
    print()

    print("ACCESS COUNT STATISTICS:")
    print("-" * 40)
    acc_stats = results["access_count_stats"]
    print(f"  Min:    {acc_stats['min']}")
    print(f"  Max:    {acc_stats['max']}")
    print(f"  Mean:   {acc_stats['mean']:.2f}")
    print(f"  Median: {acc_stats['median']:.0f}")
    print(f"  Chunks with zero access: {results['zero_access_count']} ({(results['zero_access_count']/results['total_chunks']*100):.1f}%)")
    print()

    # Analysis conclusions
    print("ANALYSIS:")
    print("-" * 40)
    if results["all_identical"]:
        print("ISSUE CONFIRMED: All activation scores are identical")
        print()
        print("Possible causes:")
        print("  1. All chunks initialized with same base_level (likely 0.5 for non-Git)")
        print("  2. Base level calculation not accounting for recency/frequency")
        print("  3. Git history not available, causing uniform initialization")
        print()
        print("Recommendation:")
        print("  - Review base_level initialization in ActivationEngine")
        print("  - Check if Git history is being used correctly")
        print("  - Verify access recording is updating base_level over time")
    elif results["base_level_stats"]["stdev"] < 0.05:
        print("LOW VARIANCE: Activation scores have very low variance")
        print()
        print("This may cause poor discrimination in search results.")
        print("Consider tuning the activation calculation parameters.")
    else:
        print("VARIANCE OK: Activation scores show reasonable variance")
        print()
        print("The issue may be in normalization, not the underlying scores.")
        print("Check _normalize_scores() in HybridRetriever.")
    print()


def main():
    """Main entry point."""
    import sys

    # Get database path from command line or use default
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # Use default Aurora home location
        db_path = str(Path.home() / ".aurora" / "memory.db")

    if not Path(db_path).exists():
        print(f"ERROR: Database not found at {db_path}")
        print()
        print("Usage: python investigate_activation_variance.py [db_path]")
        print()
        print("Example:")
        print("  python investigate_activation_variance.py ~/.aurora/memory.db")
        sys.exit(1)

    print(f"Analyzing database: {db_path}")
    print()

    results = analyze_activation_distribution(db_path)
    print_analysis(results)


if __name__ == "__main__":
    main()
