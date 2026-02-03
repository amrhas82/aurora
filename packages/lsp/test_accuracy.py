#!/usr/bin/env python3
"""Accuracy test - compare LSP results against manual file analysis."""

import asyncio
import re
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent / "src"))

from aurora_lsp.analysis import CodeAnalyzer, SymbolKind
from aurora_lsp.client import AuroraLSPClient


WORKSPACE = Path("/home/hamr/PycharmProjects/aurora")

# 10 diverse files to test
TEST_FILES = [
    "packages/core/src/aurora_core/store/sqlite.py",
    "packages/core/src/aurora_core/store/base.py",
    "packages/core/src/aurora_core/models/chunk.py",
    "packages/core/src/aurora_core/exceptions.py",
    "packages/cli/src/aurora_cli/config.py",
    "packages/cli/src/aurora_cli/errors.py",
    "packages/soar/src/aurora_soar/orchestrator.py",
    "packages/reasoning/src/aurora_reasoning/client.py",
    "packages/context_code/src/aurora_context_code/indexer.py",
    "packages/planning/src/aurora_planning/planner.py",
]


def manual_analyze(filepath: Path) -> dict:
    """Manually count classes, functions, methods from source."""
    content = filepath.read_text()
    lines = content.splitlines()

    classes = []
    functions = []
    methods = []

    in_class = False
    class_indent = 0

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Track class context
        if stripped.startswith("class "):
            match = re.match(r"class\s+(\w+)", stripped)
            if match:
                classes.append({"name": match.group(1), "line": i})
                in_class = True
                class_indent = indent

        # Function/method detection
        if stripped.startswith("def "):
            match = re.match(r"def\s+(\w+)", stripped)
            if match:
                name = match.group(1)
                if in_class and indent > class_indent:
                    methods.append({"name": name, "line": i})
                else:
                    functions.append({"name": name, "line": i})
                    if indent <= class_indent:
                        in_class = False

        # Exit class on dedent
        if in_class and stripped and indent <= class_indent and not stripped.startswith("class "):
            if not stripped.startswith("def ") and not stripped.startswith("@"):
                in_class = False

    return {
        "classes": classes,
        "functions": functions,
        "methods": methods,
        "total": len(classes) + len(functions) + len(methods)
    }


async def lsp_analyze(client: AuroraLSPClient, filepath: str) -> dict:
    """Get symbols from LSP."""
    symbols = await client.request_document_symbols(filepath)

    classes = []
    functions = []
    methods = []

    def process(syms, parent_kind=None):
        for s in syms:
            if s is None:
                continue
            kind = s.get("kind")
            name = s.get("name", "")
            sel_range = s.get("selectionRange", s.get("range", {}))
            line = sel_range.get("start", {}).get("line", 0)

            if kind == SymbolKind.CLASS:
                classes.append({"name": name, "line": line})
            elif kind == SymbolKind.FUNCTION:
                functions.append({"name": name, "line": line})
            elif kind == SymbolKind.METHOD:
                methods.append({"name": name, "line": line})

            # Process children
            if "children" in s:
                process(s["children"], kind)

    process(symbols or [])

    return {
        "classes": classes,
        "functions": functions,
        "methods": methods,
        "total": len(classes) + len(functions) + len(methods)
    }


def compare_results(manual: dict, lsp: dict, filepath: str) -> dict:
    """Compare manual vs LSP results."""
    # Create sets of (name, line) for comparison
    manual_set = set()
    for cat in ["classes", "functions", "methods"]:
        for item in manual[cat]:
            manual_set.add((item["name"], item["line"]))

    lsp_set = set()
    for cat in ["classes", "functions", "methods"]:
        for item in lsp[cat]:
            lsp_set.add((item["name"], item["line"]))

    matched = manual_set & lsp_set
    manual_only = manual_set - lsp_set
    lsp_only = lsp_set - manual_set

    # Calculate metrics
    if len(manual_set) > 0:
        recall = len(matched) / len(manual_set) * 100
    else:
        recall = 100.0

    if len(lsp_set) > 0:
        precision = len(matched) / len(lsp_set) * 100
    else:
        precision = 100.0

    return {
        "file": filepath,
        "manual_count": len(manual_set),
        "lsp_count": len(lsp_set),
        "matched": len(matched),
        "manual_only": len(manual_only),
        "lsp_only": len(lsp_only),
        "recall": recall,
        "precision": precision,
        "manual_only_items": sorted(manual_only),
        "lsp_only_items": sorted(lsp_only),
    }


async def main():
    print("=" * 80)
    print("LSP ACCURACY TEST - Manual vs LSP Symbol Detection")
    print("=" * 80)

    client = AuroraLSPClient(WORKSPACE)
    results = []

    try:
        for filepath in TEST_FILES:
            full_path = WORKSPACE / filepath
            if not full_path.exists():
                print(f"\nSKIP: {filepath} (not found)")
                continue

            print(f"\n{'='*60}")
            print(f"FILE: {filepath}")
            print("=" * 60)

            # Manual analysis
            manual = manual_analyze(full_path)
            print(f"Manual: {len(manual['classes'])} classes, {len(manual['functions'])} functions, {len(manual['methods'])} methods = {manual['total']} total")

            # LSP analysis
            lsp = await lsp_analyze(client, filepath)
            print(f"LSP:    {len(lsp['classes'])} classes, {len(lsp['functions'])} functions, {len(lsp['methods'])} methods = {lsp['total']} total")

            # Compare
            comparison = compare_results(manual, lsp, filepath)
            results.append(comparison)

            print(f"Matched: {comparison['matched']}/{comparison['manual_count']} ({comparison['recall']:.1f}% recall)")

            if comparison['manual_only_items']:
                print(f"  Manual only (missed by LSP): {comparison['manual_only_items'][:5]}")
            if comparison['lsp_only_items']:
                print(f"  LSP only (extra): {comparison['lsp_only_items'][:5]}")

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        total_manual = sum(r['manual_count'] for r in results)
        total_lsp = sum(r['lsp_count'] for r in results)
        total_matched = sum(r['matched'] for r in results)

        overall_recall = total_matched / total_manual * 100 if total_manual > 0 else 0
        overall_precision = total_matched / total_lsp * 100 if total_lsp > 0 else 0

        print(f"\nFiles analyzed: {len(results)}")
        print(f"Total symbols (manual):  {total_manual}")
        print(f"Total symbols (LSP):     {total_lsp}")
        print(f"Total matched:           {total_matched}")
        print(f"\nOVERALL RECALL:    {overall_recall:.1f}% (LSP found {total_matched}/{total_manual} manual symbols)")
        print(f"OVERALL PRECISION: {overall_precision:.1f}% ({total_matched}/{total_lsp} LSP symbols were correct)")

        print("\nPer-file breakdown:")
        print(f"{'File':<50} {'Recall':>8} {'Precision':>10}")
        print("-" * 70)
        for r in results:
            fname = r['file'].split('/')[-1]
            print(f"{fname:<50} {r['recall']:>7.1f}% {r['precision']:>9.1f}%")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
