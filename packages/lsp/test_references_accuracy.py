#!/usr/bin/env python3
"""Reference accuracy test - verify LSP finds actual usages."""

import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from aurora_lsp.analysis import CodeAnalyzer
from aurora_lsp.client import AuroraLSPClient

WORKSPACE = Path("/home/hamr/PycharmProjects/aurora")

# Test cases: (file, symbol_name, line (0-indexed), col)
# Verified by checking actual file contents
TEST_CASES = [
    ("packages/core/src/aurora_core/store/sqlite.py", "SQLiteStore", 38, 6),
    ("packages/core/src/aurora_core/store/base.py", "Store", 20, 6),  # line 21 (0-indexed=20)
    ("packages/core/src/aurora_core/exceptions.py", "AuroraError", 7, 6),  # line 8 (0-indexed=7)
    ("packages/core/src/aurora_core/exceptions.py", "ChunkNotFoundError", 22, 6),
    ("packages/cli/src/aurora_cli/config.py", "AuroraConfig", 44, 6),  # Need to verify
    ("packages/cli/src/aurora_cli/errors.py", "AuroraBaseError", 22, 6),  # Need to verify
]


def grep_count(symbol: str) -> tuple[int, int]:
    """Count occurrences using grep (ground truth)."""
    try:
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "-l", symbol, str(WORKSPACE / "packages")],
            capture_output=True,
            text=True,
        )
        files = [f for f in result.stdout.strip().split("\n") if f]

        result2 = subprocess.run(
            ["grep", "-r", "--include=*.py", "-oh", symbol, str(WORKSPACE / "packages")],
            capture_output=True,
            text=True,
        )
        total = len(result2.stdout.strip().split("\n")) if result2.stdout.strip() else 0

        return len(files), total
    except Exception:
        return 0, 0


async def main():
    print("=" * 80)
    print("REFERENCE FINDING ACCURACY TEST")
    print("=" * 80)
    print("\nComparing LSP references vs grep (ground truth)\n")

    client = AuroraLSPClient(WORKSPACE)
    analyzer = CodeAnalyzer(client, WORKSPACE)

    results = []

    try:
        for filepath, symbol, line, col in TEST_CASES:
            print(f"\n{'=' * 60}")
            print(f"Symbol: {symbol}")
            print(f"Location: {filepath}:{line + 1} (0-indexed: {line})")
            print("=" * 60)

            # Grep count (ground truth)
            grep_files, grep_total = grep_count(symbol)
            print(f"Grep:  {grep_total} occurrences in {grep_files} files")

            # LSP references
            refs = await client.request_references(filepath, line, col)
            lsp_files = len(set(r["file"] for r in refs))
            print(f"LSP:   {len(refs)} references in {lsp_files} files")

            # Usage filtering
            usage_result = await analyzer.find_usages(filepath, line, col, include_imports=False)
            usages = usage_result["total_usages"]
            imports = usage_result["total_imports"]
            print(f"Split: {usages} usages + {imports} imports = {usages + imports} total")

            # Calculate capture rate (based on grep as baseline)
            if grep_total > 0:
                capture = len(refs) / grep_total * 100
            else:
                capture = 0

            results.append(
                {
                    "symbol": symbol,
                    "grep_total": grep_total,
                    "grep_files": grep_files,
                    "lsp_refs": len(refs),
                    "lsp_files": lsp_files,
                    "usages": usages,
                    "imports": imports,
                    "capture": capture,
                }
            )

            if len(refs) > 0:
                print(
                    f"Sample refs: {[r['file'].split('/')[-1] + ':' + str(r['line']) for r in refs[:3]]}"
                )

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        print(
            f"\n{'Symbol':<25} {'Grep':>8} {'LSP':>8} {'Usages':>8} {'Imports':>8} {'Capture':>10}"
        )
        print("-" * 75)

        total_grep = 0
        total_lsp = 0
        total_usages = 0
        total_imports = 0

        for r in results:
            print(
                f"{r['symbol']:<25} {r['grep_total']:>8} {r['lsp_refs']:>8} {r['usages']:>8} {r['imports']:>8} {r['capture']:>9.1f}%"
            )
            total_grep += r["grep_total"]
            total_lsp += r["lsp_refs"]
            total_usages += r["usages"]
            total_imports += r["imports"]

        print("-" * 75)
        overall = total_lsp / total_grep * 100 if total_grep > 0 else 0
        print(
            f"{'TOTAL':<25} {total_grep:>8} {total_lsp:>8} {total_usages:>8} {total_imports:>8} {overall:>9.1f}%"
        )

        print("\nKEY METRICS:")
        print(f"  Total References Found: {total_lsp}")
        print(
            f"  Usages (actual code):   {total_usages} ({total_usages / total_lsp * 100:.1f}% of refs)"
        )
        print(
            f"  Imports (filtered):     {total_imports} ({total_imports / total_lsp * 100:.1f}% of refs)"
        )

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
