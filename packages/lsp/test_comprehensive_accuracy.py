#!/usr/bin/env python3
"""Comprehensive LSP accuracy test for imports, usages, and dead code."""

import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from aurora_lsp.analysis import CodeAnalyzer
from aurora_lsp.client import AuroraLSPClient
from aurora_lsp.filters import ImportFilter

WORKSPACE = Path("/home/hamr/PycharmProjects/aurora")


# ==============================================================================
# TEST 1: IMPORT vs USAGE SEPARATION
# ==============================================================================

# Known symbols with manually verified import/usage counts
IMPORT_USAGE_TESTS = [
    # (file, symbol, line, expected_imports, expected_usages)
    ("packages/core/src/aurora_core/models/chunk.py", "Chunk", 26, 15, 50),  # Widely used model
    ("packages/core/src/aurora_core/config.py", "Config", 23, 10, 30),  # Config class
]


async def test_import_usage_accuracy(client: AuroraLSPClient, analyzer: CodeAnalyzer):
    """Test import vs usage separation accuracy."""
    print("\n" + "=" * 70)
    print("TEST 1: IMPORT vs USAGE SEPARATION")
    print("=" * 70)

    results = []

    for filepath, symbol, line, exp_imports, exp_usages in IMPORT_USAGE_TESTS:
        print(f"\n{symbol} in {filepath.split('/')[-1]}:{line + 1}")

        # Get LSP results
        refs = await client.request_references(filepath, line, 6)

        if not refs:
            print("  ⚠ No references found")
            continue

        # Filter imports vs usages
        import_filter = ImportFilter("python")
        imports = []
        usages = []

        for ref in refs:
            ref_file = Path(ref.get("file", ""))
            ref_line = ref.get("line", 0)
            try:
                if ref_file.exists():
                    lines = ref_file.read_text().splitlines()
                    if 0 <= ref_line < len(lines):
                        line_content = lines[ref_line]
                        if import_filter.is_import_line(line_content):
                            imports.append(ref)
                        else:
                            usages.append(ref)
            except Exception:
                usages.append(ref)

        lsp_imports = len(imports)
        lsp_usages = len(usages)

        # Accuracy calculation (tolerance-based since exact counts vary)
        import_accuracy = min(lsp_imports, exp_imports) / max(lsp_imports, exp_imports, 1) * 100
        usage_accuracy = min(lsp_usages, exp_usages) / max(lsp_usages, exp_usages, 1) * 100

        print(f"  Expected: ~{exp_imports} imports, ~{exp_usages} usages")
        print(f"  LSP:       {lsp_imports} imports,  {lsp_usages} usages")
        print(f"  Accuracy: {import_accuracy:.0f}% imports, {usage_accuracy:.0f}% usages")

        results.append(
            {
                "symbol": symbol,
                "lsp_imports": lsp_imports,
                "lsp_usages": lsp_usages,
                "exp_imports": exp_imports,
                "exp_usages": exp_usages,
                "import_accuracy": import_accuracy,
                "usage_accuracy": usage_accuracy,
            }
        )

    # Summary
    if results:
        avg_import_acc = sum(r["import_accuracy"] for r in results) / len(results)
        avg_usage_acc = sum(r["usage_accuracy"] for r in results) / len(results)
        print(f"\n  IMPORT ACCURACY: {avg_import_acc:.1f}%")
        print(f"  USAGE ACCURACY:  {avg_usage_acc:.1f}%")
        return avg_import_acc, avg_usage_acc

    return 0, 0


# ==============================================================================
# TEST 2: DEAD CODE DETECTION
# ==============================================================================

# Known dead code (manually verified)
KNOWN_DEAD_CODE = [
    ("packages/core/src/aurora_core/exceptions.py", "ParseError"),
    ("packages/core/src/aurora_core/exceptions.py", "FatalError"),
]

# Known live code (should NOT be flagged)
KNOWN_LIVE_CODE = [
    ("packages/core/src/aurora_core/exceptions.py", "AuroraError"),  # Base class
    ("packages/core/src/aurora_core/store/sqlite.py", "SQLiteStore"),  # Widely used
    ("packages/core/src/aurora_core/models/chunk.py", "Chunk"),  # Model
]


async def test_dead_code_accuracy(analyzer: CodeAnalyzer):
    """Test dead code detection accuracy."""
    print("\n" + "=" * 70)
    print("TEST 2: DEAD CODE DETECTION")
    print("=" * 70)

    # Find dead code in exceptions file
    test_file = WORKSPACE / "packages/core/src/aurora_core/exceptions.py"
    dead_code = await analyzer.find_dead_code(test_file, include_private=False)

    dead_names = {item["name"] for item in dead_code}

    print(f"\nDead code found: {len(dead_code)} items")
    for item in dead_code[:10]:
        print(f"  - {item['name']} ({item['kind']}) at line {item['line']}")

    # Check known dead code (true positives)
    true_positives = 0
    false_negatives = 0
    for filepath, symbol in KNOWN_DEAD_CODE:
        if symbol in dead_names:
            print(f"\n✓ {symbol}: correctly identified as dead")
            true_positives += 1
        else:
            print(f"\n✗ {symbol}: missed (false negative)")
            false_negatives += 1

    # Check known live code (should not be flagged)
    false_positives = 0
    for filepath, symbol in KNOWN_LIVE_CODE:
        if symbol in dead_names:
            print(f"\n✗ {symbol}: incorrectly flagged as dead (false positive)")
            false_positives += 1
        else:
            print(f"\n✓ {symbol}: correctly identified as live")

    # Calculate metrics
    total_known_dead = len(KNOWN_DEAD_CODE)
    total_known_live = len(KNOWN_LIVE_CODE)

    recall = true_positives / total_known_dead * 100 if total_known_dead > 0 else 0
    specificity = (
        (total_known_live - false_positives) / total_known_live * 100 if total_known_live > 0 else 0
    )

    print(f"\n  TRUE POSITIVES:  {true_positives}/{total_known_dead}")
    print(f"  FALSE NEGATIVES: {false_negatives}/{total_known_dead}")
    print(f"  FALSE POSITIVES: {false_positives}/{total_known_live}")

    print(f"\n  RECALL (dead code detection): {recall:.1f}%")
    print(f"  SPECIFICITY (live code kept): {specificity:.1f}%")

    return recall, specificity


# ==============================================================================
# TEST 3: REFERENCE FINDING ACCURACY
# ==============================================================================

# Symbols with manually verified reference counts (using grep -rw as baseline)
REFERENCE_TESTS = [
    # (file, symbol, line, min_expected_refs)
    ("packages/core/src/aurora_core/store/sqlite.py", "save_chunk", 118, 10),
    ("packages/core/src/aurora_core/store/sqlite.py", "get_chunk", 181, 5),
]


async def test_reference_accuracy(client: AuroraLSPClient):
    """Test reference finding accuracy."""
    print("\n" + "=" * 70)
    print("TEST 3: REFERENCE FINDING")
    print("=" * 70)

    results = []

    for filepath, symbol, line, min_expected in REFERENCE_TESTS:
        print(f"\n{symbol} in {filepath.split('/')[-1]}:{line + 1}")

        # Get grep count
        try:
            result = subprocess.run(
                ["grep", "-rw", "--include=*.py", "-c", symbol, str(WORKSPACE / "packages")],
                capture_output=True,
                text=True,
            )
            grep_total = sum(
                int(line.split(":")[-1])
                for line in result.stdout.strip().split("\n")
                if line and ":" in line
            )
        except Exception:
            grep_total = 0

        # Get LSP refs
        refs = await client.request_references(filepath, line, 4)
        lsp_total = len(refs)

        # Calculate accuracy (based on minimum expected)
        accuracy = min(100, lsp_total / min_expected * 100) if min_expected > 0 else 100

        print(f"  Grep: {grep_total} matches")
        print(f"  LSP:  {lsp_total} references")
        print(f"  Min expected: {min_expected}, Accuracy: {accuracy:.0f}%")

        results.append(
            {
                "symbol": symbol,
                "grep": grep_total,
                "lsp": lsp_total,
                "min_expected": min_expected,
                "accuracy": accuracy,
            }
        )

    if results:
        avg_acc = sum(r["accuracy"] for r in results) / len(results)
        print(f"\n  REFERENCE ACCURACY: {avg_acc:.1f}%")
        return avg_acc

    return 0


# ==============================================================================
# MAIN
# ==============================================================================


async def main():
    print("=" * 70)
    print("COMPREHENSIVE LSP ACCURACY REPORT")
    print("=" * 70)

    client = AuroraLSPClient(WORKSPACE)
    analyzer = CodeAnalyzer(client, WORKSPACE)

    try:
        # Test 1: Import vs Usage
        import_acc, usage_acc = await test_import_usage_accuracy(client, analyzer)

        # Test 2: Dead Code
        dead_recall, dead_spec = await test_dead_code_accuracy(analyzer)

        # Test 3: References
        ref_acc = await test_reference_accuracy(client)

        # Final Summary
        print("\n" + "=" * 70)
        print("FINAL ACCURACY SUMMARY")
        print("=" * 70)

        print(
            """
┌─────────────────────────────────────────────────────────────────────┐
│ METRIC                              │ ACCURACY                      │
├─────────────────────────────────────┼───────────────────────────────┤"""
        )
        print(
            f"│ Import Detection                    │ {import_acc:>6.1f}%                       │"
        )
        print(f"│ Usage Detection                     │ {usage_acc:>6.1f}%                       │")
        print(
            f"│ Dead Code Recall                    │ {dead_recall:>6.1f}%                       │"
        )
        print(f"│ Dead Code Specificity               │ {dead_spec:>6.1f}%                       │")
        print(f"│ Reference Finding                   │ {ref_acc:>6.1f}%                       │")
        print("└─────────────────────────────────────┴───────────────────────────────┘")

        overall = (import_acc + usage_acc + dead_recall + dead_spec + ref_acc) / 5
        print(f"\n  OVERALL ACCURACY: {overall:.1f}%")

        print(
            """
NOTES:
  • Import detection: Regex pattern matching on LSP reference lines
  • Usage detection: All non-import references from LSP
  • Dead code: Symbols with 0 usages (excluding imports)
  • Reference finding: LSP textDocument/references
  • Numbers may vary due to codebase changes
"""
        )

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
