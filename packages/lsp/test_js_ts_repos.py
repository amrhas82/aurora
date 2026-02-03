#!/usr/bin/env python3
"""Test aurora-lsp against JavaScript and TypeScript repositories.

Tests:
1. liteagents (JavaScript) - /tmp/liteagents
2. OpenSpec (TypeScript) - /tmp/OpenSpec

For each repo, tests 10 files:
- Document symbols extraction
- Reference finding
- Import vs usage filtering
"""

import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Add package to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aurora_lsp.client import AuroraLSPClient
from aurora_lsp.filters import ImportFilter


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of testing a single file."""
    file: str
    language: str
    symbols_found: int
    symbols_detail: list[dict]
    test_symbol: str | None = None
    total_refs: int = 0
    imports: int = 0
    usages: int = 0
    error: str | None = None


def format_symbol(sym: dict, indent: int = 0) -> str:
    """Format a symbol for display."""
    kind_map = {
        1: "File", 2: "Module", 3: "Namespace", 4: "Package",
        5: "Class", 6: "Method", 7: "Property", 8: "Field",
        9: "Constructor", 10: "Enum", 11: "Interface",
        12: "Function", 13: "Variable", 14: "Constant",
        15: "String", 16: "Number", 17: "Boolean", 18: "Array",
        19: "Object", 20: "Key", 21: "Null", 22: "EnumMember",
        23: "Struct", 24: "Event", 25: "Operator", 26: "TypeParameter"
    }
    name = sym.get("name", "?")
    kind_num = sym.get("kind", 0)
    kind = kind_map.get(kind_num, f"Kind({kind_num})")

    range_info = sym.get("range") or sym.get("location", {}).get("range", {})
    start = range_info.get("start", {})
    line = start.get("line", "?")

    prefix = "  " * indent
    return f"{prefix}{kind}: {name} (line {line})"


def flatten_symbols(symbols: list) -> list[dict]:
    """Flatten nested symbol tree."""
    result = []
    for s in symbols:
        result.append(s)
        children = s.get("children", [])
        if children:
            result.extend(flatten_symbols(children))
    return result


async def test_file(
    client: AuroraLSPClient,
    file_path: Path,
    workspace: Path,
) -> TestResult:
    """Test LSP operations on a single file."""
    rel_path = str(file_path.relative_to(workspace))
    lang = "JavaScript" if file_path.suffix == ".js" else "TypeScript"

    result = TestResult(
        file=rel_path,
        language=lang,
        symbols_found=0,
        symbols_detail=[],
    )

    try:
        # Get document symbols
        symbols = await client.request_document_symbols(file_path)
        flat_symbols = flatten_symbols(symbols or [])
        result.symbols_found = len(flat_symbols)
        result.symbols_detail = flat_symbols

        # Find a good symbol to test references
        # Prefer functions/methods/classes
        test_sym = None
        for sym in flat_symbols:
            kind = sym.get("kind", 0)
            if kind in [5, 6, 12]:  # Class, Method, Function
                test_sym = sym
                break

        if not test_sym and flat_symbols:
            test_sym = flat_symbols[0]

        if test_sym:
            result.test_symbol = test_sym.get("name")
            range_info = test_sym.get("range") or test_sym.get("location", {}).get("range", {})
            start = range_info.get("start", {})
            line = start.get("line", 0)
            col = start.get("character", 0)

            # Get references
            refs = await client.request_references(file_path, line, col)
            result.total_refs = len(refs)

            # Filter imports vs usages
            if refs:
                import_filter = ImportFilter(lang.lower())
                imports = []
                usages = []

                for ref in refs:
                    ref_file = ref.get("file", "")
                    ref_line = ref.get("line", 0)

                    # Read line content
                    try:
                        ref_path = Path(ref_file)
                        if ref_path.exists():
                            lines = ref_path.read_text().splitlines()
                            if 0 <= ref_line < len(lines):
                                line_content = lines[ref_line]
                                if import_filter.is_import_line(line_content):
                                    imports.append(ref)
                                else:
                                    usages.append(ref)
                            else:
                                usages.append(ref)
                        else:
                            usages.append(ref)
                    except Exception:
                        usages.append(ref)

                result.imports = len(imports)
                result.usages = len(usages)

    except Exception as e:
        result.error = str(e)

    return result


async def test_repo(
    workspace: Path,
    extension: str,
    repo_name: str,
    max_files: int = 10,
) -> list[TestResult]:
    """Test LSP on a repository."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {repo_name} ({extension.upper()})")
    logger.info(f"Workspace: {workspace}")
    logger.info(f"{'='*60}")

    # Find source files
    files = list(workspace.rglob(f"*{extension}"))

    # Filter out test files, node_modules, and barrel files
    files = [
        f for f in files
        if "node_modules" not in str(f)
        and "dist" not in str(f)
        and ".d.ts" not in str(f)
        and f.name != "index.ts"  # Skip barrel files
        and f.name != "index.js"
    ]

    # Sort by size descending (prefer larger files with more symbols)
    files.sort(key=lambda f: f.stat().st_size, reverse=True)

    # Take up to max_files
    test_files = files[:max_files]

    logger.info(f"Found {len(files)} source files, testing {len(test_files)}")

    results = []
    client = AuroraLSPClient(workspace)

    try:
        for i, file_path in enumerate(test_files, 1):
            logger.info(f"\n[{i}/{len(test_files)}] {file_path.relative_to(workspace)}")
            result = await test_file(client, file_path, workspace)
            results.append(result)

            if result.error:
                logger.info(f"  ERROR: {result.error}")
            else:
                logger.info(f"  Symbols: {result.symbols_found}")
                if result.test_symbol:
                    logger.info(f"  Test symbol: {result.test_symbol}")
                    logger.info(f"  References: {result.total_refs} (imports: {result.imports}, usages: {result.usages})")

    finally:
        await client.close()

    return results


def print_summary(js_results: list[TestResult], ts_results: list[TestResult]) -> None:
    """Print comparison summary."""

    def calc_stats(results: list[TestResult]) -> dict:
        successful = [r for r in results if r.error is None]
        total_symbols = sum(r.symbols_found for r in successful)
        total_refs = sum(r.total_refs for r in successful)
        total_imports = sum(r.imports for r in successful)
        total_usages = sum(r.usages for r in successful)

        return {
            "files_tested": len(results),
            "files_success": len(successful),
            "total_symbols": total_symbols,
            "total_refs": total_refs,
            "total_imports": total_imports,
            "total_usages": total_usages,
            "avg_symbols": total_symbols / len(successful) if successful else 0,
        }

    js_stats = calc_stats(js_results)
    ts_stats = calc_stats(ts_results)

    print("\n" + "="*70)
    print("SUMMARY: JavaScript vs TypeScript LSP Testing")
    print("="*70)

    print("\n" + "-"*70)
    print(f"{'Metric':<30} {'JavaScript':>18} {'TypeScript':>18}")
    print("-"*70)

    metrics = [
        ("Files Tested", "files_tested"),
        ("Files Successful", "files_success"),
        ("Total Symbols Found", "total_symbols"),
        ("Avg Symbols/File", "avg_symbols"),
        ("Total References", "total_refs"),
        ("Total Imports", "total_imports"),
        ("Total Usages", "total_usages"),
    ]

    for label, key in metrics:
        js_val = js_stats[key]
        ts_val = ts_stats[key]

        if isinstance(js_val, float):
            print(f"{label:<30} {js_val:>18.1f} {ts_val:>18.1f}")
        else:
            print(f"{label:<30} {js_val:>18} {ts_val:>18}")

    print("-"*70)

    # Show sample symbols from each
    print("\n" + "="*70)
    print("SAMPLE SYMBOLS FOUND")
    print("="*70)

    print("\n--- JavaScript (liteagents) ---")
    for r in js_results[:3]:
        if r.symbols_detail:
            print(f"\n{r.file}:")
            for sym in r.symbols_detail[:5]:
                print(f"  {format_symbol(sym)}")

    print("\n--- TypeScript (OpenSpec) ---")
    for r in ts_results[:3]:
        if r.symbols_detail:
            print(f"\n{r.file}:")
            for sym in r.symbols_detail[:5]:
                print(f"  {format_symbol(sym)}")

    # Show import filtering results
    print("\n" + "="*70)
    print("IMPORT vs USAGE FILTERING")
    print("="*70)

    print("\n--- JavaScript ---")
    for r in js_results:
        if r.total_refs > 0:
            print(f"  {r.test_symbol}: {r.total_refs} refs → {r.imports} imports + {r.usages} usages")

    print("\n--- TypeScript ---")
    for r in ts_results:
        if r.total_refs > 0:
            print(f"  {r.test_symbol}: {r.total_refs} refs → {r.imports} imports + {r.usages} usages")


async def main():
    """Run tests on both repos."""
    js_workspace = Path("/tmp/liteagents")
    ts_workspace = Path("/tmp/OpenSpec")

    if not js_workspace.exists():
        logger.error(f"JavaScript repo not found: {js_workspace}")
        logger.error("Clone with: git clone https://github.com/amrhas82/liteagents /tmp/liteagents")
        return

    if not ts_workspace.exists():
        logger.error(f"TypeScript repo not found: {ts_workspace}")
        logger.error("Clone with: git clone https://github.com/amrhas82/OpenSpec /tmp/OpenSpec")
        return

    # Test JavaScript
    js_results = await test_repo(js_workspace, ".js", "liteagents", max_files=10)

    # Test TypeScript
    ts_results = await test_repo(ts_workspace, ".ts", "OpenSpec", max_files=10)

    # Print summary
    print_summary(js_results, ts_results)


if __name__ == "__main__":
    asyncio.run(main())
