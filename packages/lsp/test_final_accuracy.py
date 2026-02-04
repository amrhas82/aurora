#!/usr/bin/env python3
"""Final accuracy test - comprehensive LSP validation."""

import asyncio
import subprocess
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent / "src"))

from aurora_lsp.analysis import CodeAnalyzer
from aurora_lsp.client import AuroraLSPClient


WORKSPACE = Path("/home/hamr/PycharmProjects/aurora")

# Verified test cases with correct line numbers (0-indexed)
TEST_CASES = [
    # file, symbol, line (0-indexed), col, description
    ("packages/core/src/aurora_core/store/sqlite.py", "SQLiteStore", 38, 6, "Main store class"),
    ("packages/core/src/aurora_core/store/base.py", "Store", 20, 6, "Abstract base"),
    ("packages/core/src/aurora_core/exceptions.py", "AuroraError", 7, 6, "Base exception"),
    (
        "packages/core/src/aurora_core/exceptions.py",
        "ChunkNotFoundError",
        80,
        6,
        "Storage exception",
    ),
    ("packages/core/src/aurora_core/exceptions.py", "StorageError", 73, 6, "Storage base"),
    ("packages/cli/src/aurora_cli/errors.py", "AuroraBaseError", 22, 6, "CLI base error"),
    (
        "packages/soar/src/aurora_soar/orchestrator.py",
        "SoarOrchestrator",
        89,
        6,
        "Main orchestrator",
    ),
]


def grep_semantic_count(symbol: str) -> tuple[int, int, int]:
    """Count using word-boundary grep for better accuracy."""
    try:
        # Word-boundary search (more accurate than plain grep)
        result = subprocess.run(
            ["grep", "-rw", "--include=*.py", "-l", symbol, str(WORKSPACE / "packages")],
            capture_output=True,
            text=True,
        )
        files = [f for f in result.stdout.strip().split("\n") if f]

        result2 = subprocess.run(
            ["grep", "-rw", "--include=*.py", "-oh", symbol, str(WORKSPACE / "packages")],
            capture_output=True,
            text=True,
        )
        total = len([x for x in result2.stdout.strip().split("\n") if x])

        # Also get import-only count
        result3 = subprocess.run(
            [
                "grep",
                "-rw",
                "--include=*.py",
                "-E",
                f"^(from|import).*{symbol}",
                str(WORKSPACE / "packages"),
            ],
            capture_output=True,
            text=True,
        )
        import_count = len([x for x in result3.stdout.strip().split("\n") if x])

        return len(files), total, import_count
    except Exception as e:
        print(f"Grep error: {e}")
        return 0, 0, 0


async def main():
    print("=" * 90)
    print("FINAL LSP ACCURACY TEST")
    print("=" * 90)

    client = AuroraLSPClient(WORKSPACE)
    analyzer = CodeAnalyzer(client, WORKSPACE)

    results = []

    try:
        for filepath, symbol, line, col, desc in TEST_CASES:
            print(f"\n{'─' * 70}")
            print(f"📍 {symbol} ({desc})")
            print(f"   File: {filepath}:{line + 1}")
            print("─" * 70)

            # Grep count with word boundaries
            grep_files, grep_total, grep_imports = grep_semantic_count(symbol)
            grep_usages = grep_total - grep_imports

            # LSP references
            refs = await client.request_references(filepath, line, col)
            lsp_files = len(set(r["file"] for r in refs))

            # Usage filtering
            usage_result = await analyzer.find_usages(filepath, line, col, include_imports=False)
            lsp_usages = usage_result["total_usages"]
            lsp_imports = usage_result["total_imports"]

            print(
                f"   GREP:  {grep_total:3} total ({grep_usages} usages + {grep_imports} imports) in {grep_files} files"
            )
            print(
                f"   LSP:   {len(refs):3} total ({lsp_usages} usages + {lsp_imports} imports) in {lsp_files} files"
            )

            # Compare
            if grep_total > 0:
                total_match = len(refs) / grep_total * 100
            else:
                total_match = 100 if len(refs) == 0 else 0

            results.append(
                {
                    "symbol": symbol,
                    "grep_total": grep_total,
                    "grep_usages": grep_usages,
                    "grep_imports": grep_imports,
                    "lsp_total": len(refs),
                    "lsp_usages": lsp_usages,
                    "lsp_imports": lsp_imports,
                    "match_pct": total_match,
                }
            )

            # Sample references
            if refs:
                samples = [f"{Path(r['file']).name}:{r['line'] + 1}" for r in refs[:3]]
                print(f"   Sample: {', '.join(samples)}")

        # Summary
        print("\n" + "=" * 90)
        print("SUMMARY TABLE")
        print("=" * 90)

        print(f"\n{'Symbol':<22} │ {'Grep':^18} │ {'LSP':^18} │ {'Match':>7}")
        print(f"{'':─<22}─┼─{'':─^18}─┼─{'':─^18}─┼─{'':─>7}")

        totals = {"grep": 0, "grep_use": 0, "grep_imp": 0, "lsp": 0, "lsp_use": 0, "lsp_imp": 0}

        for r in results:
            grep_str = f"{r['grep_usages']}u + {r['grep_imports']}i = {r['grep_total']}"
            lsp_str = f"{r['lsp_usages']}u + {r['lsp_imports']}i = {r['lsp_total']}"
            print(f"{r['symbol']:<22} │ {grep_str:^18} │ {lsp_str:^18} │ {r['match_pct']:>6.0f}%")

            totals["grep"] += r["grep_total"]
            totals["grep_use"] += r["grep_usages"]
            totals["grep_imp"] += r["grep_imports"]
            totals["lsp"] += r["lsp_total"]
            totals["lsp_use"] += r["lsp_usages"]
            totals["lsp_imp"] += r["lsp_imports"]

        print(f"{'':─<22}─┼─{'':─^18}─┼─{'':─^18}─┼─{'':─>7}")
        grep_total_str = f"{totals['grep_use']}u + {totals['grep_imp']}i = {totals['grep']}"
        lsp_total_str = f"{totals['lsp_use']}u + {totals['lsp_imp']}i = {totals['lsp']}"
        overall = totals["lsp"] / totals["grep"] * 100 if totals["grep"] > 0 else 0
        print(f"{'TOTAL':<22} │ {grep_total_str:^18} │ {lsp_total_str:^18} │ {overall:>6.0f}%")

        print("\n" + "=" * 90)
        print("KEY INSIGHTS")
        print("=" * 90)

        print(f"""
📊 CAPTURE RATES:
   • Overall:         {overall:.1f}% of grep matches found by LSP
   • Usage accuracy:  {totals["lsp_use"]}/{totals["grep_use"]} usages ({totals["lsp_use"] / max(totals["grep_use"], 1) * 100:.1f}%)
   • Import accuracy: {totals["lsp_imp"]}/{totals["grep_imp"]} imports ({totals["lsp_imp"] / max(totals["grep_imp"], 1) * 100:.1f}%)

🎯 KEY VALUE PROPOSITION:
   • Import vs Usage distinction: {totals["lsp_use"]} usages / {totals["lsp_imp"]} imports separated
   • This separation is NOT available from grep or basic text search

⚠️  NOTES:
   • LSP > grep: type resolution, re-exports, aliases
   • LSP < grep: partial matches, comments, strings
   • Polymorphic calls through base class tracked at base, not implementation
""")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
