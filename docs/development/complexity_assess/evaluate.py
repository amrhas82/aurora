#!/usr/bin/env python3
"""
Evaluation framework for complexity assessor.

Runs the assessor against the test corpus and produces detailed metrics,
identifying misclassifications for algorithm refinement.
"""
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from complexity_assessor import AssessmentResult, ComplexityAssessor
from test_corpus import TEST_CORPUS, get_by_category, get_by_level


@dataclass
class EvaluationResult:
    """Result of evaluation run."""

    total: int
    correct: int
    accuracy: float
    by_level: dict[str, dict]
    misclassifications: list[dict]
    confusion_matrix: dict[str, dict[str, int]]
    score_distributions: dict[str, list[int]]


def evaluate_corpus(
    assessor: ComplexityAssessor | None = None, verbose: bool = False
) -> EvaluationResult:
    """
    Evaluate assessor against the full test corpus.

    Returns detailed metrics including:
    - Overall accuracy
    - Per-level accuracy
    - Confusion matrix
    - List of misclassifications with details
    - Score distributions by level
    """
    if assessor is None:
        assessor = ComplexityAssessor()

    correct = 0
    total = len(TEST_CORPUS)

    # Track per-level stats
    level_stats = {
        "simple": {"correct": 0, "total": 0, "scores": []},
        "medium": {"correct": 0, "total": 0, "scores": []},
        "complex": {"correct": 0, "total": 0, "scores": []},
    }

    # Confusion matrix: expected -> predicted -> count
    confusion = defaultdict(lambda: defaultdict(int))

    # Track misclassifications
    misclassifications = []

    for prompt, expected, category, notes in TEST_CORPUS:
        result = assessor.assess(prompt)
        predicted = result.level

        level_stats[expected]["total"] += 1
        level_stats[expected]["scores"].append(result.score)

        confusion[expected][predicted] += 1

        if predicted == expected:
            correct += 1
            level_stats[expected]["correct"] += 1
        else:
            misclassifications.append(
                {
                    "prompt": prompt,
                    "expected": expected,
                    "predicted": predicted,
                    "score": result.score,
                    "confidence": result.confidence,
                    "signals": result.signals,
                    "category": category,
                    "notes": notes,
                    "breakdown": result.breakdown,
                }
            )

            if verbose:
                print(f"\n{'='*60}")
                print(f"MISCLASSIFICATION: expected={expected}, got={predicted}")
                print(f"Prompt: {prompt[:80]}...")
                print(f"Score: {result.score}, Confidence: {result.confidence:.2f}")
                print(f"Signals: {result.signals}")

    # Calculate per-level accuracy
    by_level = {}
    for level, stats in level_stats.items():
        by_level[level] = {
            "accuracy": stats["correct"] / stats["total"] if stats["total"] > 0 else 0,
            "correct": stats["correct"],
            "total": stats["total"],
            "avg_score": sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0,
            "min_score": min(stats["scores"]) if stats["scores"] else 0,
            "max_score": max(stats["scores"]) if stats["scores"] else 0,
        }

    # Score distributions
    score_distributions = {level: stats["scores"] for level, stats in level_stats.items()}

    return EvaluationResult(
        total=total,
        correct=correct,
        accuracy=correct / total,
        by_level=by_level,
        misclassifications=misclassifications,
        confusion_matrix=dict(confusion),
        score_distributions=score_distributions,
    )


def print_report(result: EvaluationResult):
    """Print formatted evaluation report."""
    print("\n" + "=" * 70)
    print("COMPLEXITY ASSESSOR EVALUATION REPORT")
    print("=" * 70)

    # Overall accuracy
    print(f"\nOVERALL ACCURACY: {result.accuracy:.1%} ({result.correct}/{result.total})")

    # Per-level breakdown
    print("\n" + "-" * 40)
    print("PER-LEVEL ACCURACY:")
    print("-" * 40)
    for level in ["simple", "medium", "complex"]:
        stats = result.by_level[level]
        print(f"  {level.upper():8} {stats['accuracy']:6.1%} ({stats['correct']}/{stats['total']})")
        print(
            f"           Score range: {stats['min_score']}-{stats['max_score']}, avg: {stats['avg_score']:.1f}"
        )

    # Confusion matrix
    print("\n" + "-" * 40)
    print("CONFUSION MATRIX:")
    print("-" * 40)
    print(f"{'Expected':<12} {'→ Simple':<12} {'→ Medium':<12} {'→ Complex':<12}")
    for expected in ["simple", "medium", "complex"]:
        row = result.confusion_matrix.get(expected, {})
        simple = row.get("simple", 0)
        medium = row.get("medium", 0)
        complex_ = row.get("complex", 0)
        print(f"{expected:<12} {simple:<12} {medium:<12} {complex_:<12}")

    # Misclassification analysis
    print("\n" + "-" * 40)
    print(f"MISCLASSIFICATIONS: {len(result.misclassifications)}")
    print("-" * 40)

    if result.misclassifications:
        # Group by error type
        over_classified = [
            m
            for m in result.misclassifications
            if _level_order(m["predicted"]) > _level_order(m["expected"])
        ]
        under_classified = [
            m
            for m in result.misclassifications
            if _level_order(m["predicted"]) < _level_order(m["expected"])
        ]

        print(f"\n  Over-classified (predicted too complex): {len(over_classified)}")
        for m in over_classified[:5]:  # Show first 5
            print(
                f"    [{m['expected']}→{m['predicted']}] score={m['score']:3} \"{m['prompt'][:50]}...\""
            )

        print(f"\n  Under-classified (predicted too simple): {len(under_classified)}")
        for m in under_classified[:5]:  # Show first 5
            print(
                f"    [{m['expected']}→{m['predicted']}] score={m['score']:3} \"{m['prompt'][:50]}...\""
            )

    # Score threshold analysis
    print("\n" + "-" * 40)
    print("SCORE THRESHOLD ANALYSIS:")
    print("-" * 40)
    _analyze_thresholds(result)


def _level_order(level: str) -> int:
    """Convert level to numeric for comparison."""
    return {"simple": 0, "medium": 1, "complex": 2}.get(level, -1)


def _analyze_thresholds(result: EvaluationResult):
    """Analyze if threshold adjustments would improve accuracy."""
    simple_scores = result.score_distributions["simple"]
    medium_scores = result.score_distributions["medium"]
    complex_scores = result.score_distributions["complex"]

    print(
        f"  Simple scores:  min={min(simple_scores):3}, max={max(simple_scores):3}, "
        f"p90={sorted(simple_scores)[int(len(simple_scores)*0.9)]:3}"
    )
    print(
        f"  Medium scores:  min={min(medium_scores):3}, max={max(medium_scores):3}, "
        f"p10={sorted(medium_scores)[int(len(medium_scores)*0.1)]:3}, "
        f"p90={sorted(medium_scores)[int(len(medium_scores)*0.9)]:3}"
    )
    print(
        f"  Complex scores: min={min(complex_scores):3}, max={max(complex_scores):3}, "
        f"p10={sorted(complex_scores)[int(len(complex_scores)*0.1)]:3}"
    )

    # Find optimal thresholds
    print("\n  Threshold optimization:")
    best_simple_thresh, best_medium_thresh, best_acc = _find_optimal_thresholds(result)
    print("  Current: simple<=15, medium<=35")
    print(
        f"  Optimal: simple<={best_simple_thresh}, medium<={best_medium_thresh} "
        f"(would achieve {best_acc:.1%})"
    )


def _find_optimal_thresholds(result: EvaluationResult) -> tuple[int, int, float]:
    """Find thresholds that maximize accuracy on current data."""
    best_acc = 0
    best_simple = 15
    best_medium = 35

    all_scores = []
    for prompt, expected, _, _ in TEST_CORPUS:
        assessor = ComplexityAssessor()
        r = assessor.assess(prompt)
        all_scores.append((r.score, expected))

    for simple_thresh in range(5, 30, 2):
        for medium_thresh in range(simple_thresh + 5, 60, 2):
            correct = 0
            for score, expected in all_scores:
                if score <= simple_thresh:
                    predicted = "simple"
                elif score <= medium_thresh:
                    predicted = "medium"
                else:
                    predicted = "complex"

                if predicted == expected:
                    correct += 1

            acc = correct / len(all_scores)
            if acc > best_acc:
                best_acc = acc
                best_simple = simple_thresh
                best_medium = medium_thresh

    return best_simple, best_medium, best_acc


def analyze_misclassifications(result: EvaluationResult):
    """Deep analysis of misclassifications for algorithm improvement."""
    print("\n" + "=" * 70)
    print("DETAILED MISCLASSIFICATION ANALYSIS")
    print("=" * 70)

    for i, m in enumerate(result.misclassifications, 1):
        print(f"\n--- Misclassification {i}/{len(result.misclassifications)} ---")
        print(f"Prompt: {m['prompt']}")
        print(f"Expected: {m['expected']}, Got: {m['predicted']}")
        print(f"Score: {m['score']}, Confidence: {m['confidence']:.2f}")
        print(f"Category: {m['category']}, Notes: {m['notes']}")
        print(f"Signals: {m['signals']}")
        print(f"Breakdown: {m['breakdown']}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate complexity assessor")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show details during evaluation"
    )
    parser.add_argument(
        "--analyze", "-a", action="store_true", help="Deep analysis of misclassifications"
    )

    args = parser.parse_args()

    assessor = ComplexityAssessor()
    result = evaluate_corpus(assessor, verbose=args.verbose)
    print_report(result)

    if args.analyze:
        analyze_misclassifications(result)

    # Return exit code based on accuracy
    if result.accuracy >= 0.85:
        print(f"\n✓ Target accuracy (85%) achieved: {result.accuracy:.1%}")
        return 0
    else:
        print(f"\n✗ Below target accuracy (85%): {result.accuracy:.1%}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
