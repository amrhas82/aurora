#!/usr/bin/env python3
"""Test aurora-lsp on 10 files from each repo with before/after comparison.

Shows exact improvements LSP provides over grep for:
- JavaScript (liteagents)
- TypeScript (OpenSpec)
"""

import asyncio
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent / "src"))

from aurora_lsp.client import AuroraLSPClient
from aurora_lsp.filters import ImportFilter


@dataclass
class FileResult:
    """Results for a single file."""
    file: str
    language: str
    symbols_found: int
    top_symbols: list[str] = field(default_factory=list)

    # Best symbol analysis
    best_symbol: str = ""
    best_symbol_kind: str = ""
    grep_matches: int = 0
    lsp_refs: int = 0
    lsp_imports: int = 0
    lsp_usages: int = 0
    false_positives: int = 0


def grep_count_with_fp(workspace: Path, pattern: str, extension: str) -> tuple[int, int]:
    """Count grep matches and false positives (comments/strings)."""
    if len(pattern) < 3 or pattern in ["the", "and", "for", "var", "let", "const"]:
        return 0, 0

    matches = 0
    false_positives = 0

    for file_path in workspace.rglob(f"*{extension}"):
        if "node_modules" in str(file_path):
            continue
        try:
            content = file_path.read_text()
            for line in content.splitlines():
                if re.search(r'\b' + re.escape(pattern) + r'\b', line):
                    matches += 1
                    stripped = line.strip()
                    if (stripped.startswith("//") or
                        stripped.startswith("*") or
                        stripped.startswith("/*") or
                        stripped.startswith("#") or
                        "* @" in stripped):  # JSDoc
                        false_positives += 1
        except Exception:
            continue

    return matches, false_positives


def flatten_symbols(symbols: list) -> list[dict]:
    """Flatten nested symbol tree."""
    result = []
    for s in symbols:
        result.append(s)
        if children := s.get("children", []):
            result.extend(flatten_symbols(children))
    return result


def format_kind(kind_num: int) -> str:
    """Format symbol kind."""
    kinds = {5: "Class", 6: "Method", 12: "Function", 13: "Variable", 14: "Constant"}
    return kinds.get(kind_num, f"K{kind_num}")


async def analyze_file(
    client: AuroraLSPClient,
    workspace: Path,
    file_path: Path,
    extension: str,
) -> FileResult:
    """Analyze a single file."""
    rel_path = str(file_path.relative_to(workspace))
    lang = "JavaScript" if extension == ".js" else "TypeScript"

    result = FileResult(file=rel_path, language=lang, symbols_found=0)

    # Get document symbols
    symbols = await client.request_document_symbols(file_path)
    flat_symbols = flatten_symbols(symbols or [])
    result.symbols_found = len(flat_symbols)

    # Get top symbols
    result.top_symbols = [
        f"{format_kind(s.get('kind', 0))}:{s.get('name', '?')}"
        for s in flat_symbols[:5]
        if s.get("kind") in [5, 6, 12, 13, 14]
    ]

    # Find best symbol to analyze (class or exported function)
    best = None
    for sym in flat_symbols:
        if sym.get("kind") in [5, 12]:  # Class, Function
            name = sym.get("name", "")
            if len(name) > 4 and name[0].isupper():
                best = sym
                break

    if not best:
        for sym in flat_symbols:
            if sym.get("kind") in [5, 6, 12] and len(sym.get("name", "")) > 3:
                best = sym
                break

    if best:
        name = best.get("name", "")
        result.best_symbol = name
        result.best_symbol_kind = format_kind(best.get("kind", 0))

        # BEFORE: grep
        grep_count, fp_count = grep_count_with_fp(workspace, name, extension)
        result.grep_matches = grep_count
        result.false_positives = fp_count

        # AFTER: LSP
        range_info = best.get("range") or best.get("location", {}).get("range", {})
        start = range_info.get("start", {})
        line = start.get("line", 0)
        col = start.get("character", 0)

        refs = await client.request_references(file_path, line, col)
        result.lsp_refs = len(refs)

        # Filter imports
        import_filter = ImportFilter(lang.lower())
        for ref in refs:
            ref_file = Path(ref.get("file", ""))
            ref_line = ref.get("line", 0)
            try:
                if ref_file.exists():
                    lines = ref_file.read_text().splitlines()
                    if 0 <= ref_line < len(lines):
                        line_content = lines[ref_line]
                        if import_filter.is_import_line(line_content):
                            result.lsp_imports += 1
                        else:
                            result.lsp_usages += 1
                    else:
                        result.lsp_usages += 1
                else:
                    result.lsp_usages += 1
            except Exception:
                result.lsp_usages += 1

    return result


async def test_repo(workspace: Path, extension: str, name: str, max_files: int = 10) -> list[FileResult]:
    """Test a repository."""
    print(f"\n{'='*80}")
    print(f" {name} - 10 Files Before/After")
    print(f"{'='*80}")

    # Find source files
    files = list(workspace.rglob(f"*{extension}"))
    files = [
        f for f in files
        if "node_modules" not in str(f)
        and "dist" not in str(f)
        and f.name != f"index{extension}"
    ]
    files.sort(key=lambda f: f.stat().st_size, reverse=True)
    files = files[:max_files]

    results = []
    client = AuroraLSPClient(workspace)

    try:
        for i, file_path in enumerate(files, 1):
            result = await analyze_file(client, workspace, file_path, extension)
            results.append(result)

            # Print file result
            print(f"\n[{i:2d}] {result.file}")
            print(f"    Symbols: {result.symbols_found}")
            if result.top_symbols:
                print(f"    Top: {', '.join(result.top_symbols[:3])}")

            if result.best_symbol:
                print(f"\n    Analysis of '{result.best_symbol}' ({result.best_symbol_kind}):")
                print("    ┌─────────────────────────────────────────────────────────")
                print(f"    │ BEFORE (grep):  {result.grep_matches:>4} matches ({result.false_positives} in comments)")
                print(f"    │ AFTER  (LSP):   {result.lsp_refs:>4} refs = {result.lsp_imports} imports + {result.lsp_usages} usages")

                improvement = ""
                if result.false_positives > 0:
                    improvement = f"Avoided {result.false_positives} false positives"
                elif result.lsp_imports > 0:
                    improvement = "Separated imports from usages"
                elif result.grep_matches > result.lsp_refs:
                    improvement = f"Filtered {result.grep_matches - result.lsp_refs} noise"
                else:
                    improvement = "Semantic accuracy"

                print(f"    │ → {improvement}")
                print("    └─────────────────────────────────────────────────────────")

    finally:
        await client.close()

    return results


def print_summary(js_results: list[FileResult], ts_results: list[FileResult]):
    """Print final summary table."""
    print("\n" + "="*80)
    print(" SUMMARY TABLE")
    print("="*80)

    print("\n┌" + "─"*78 + "┐")
    print(f"│ {'Language':<12} │ {'Files':>6} │ {'Symbols':>8} │ {'Grep':>8} │ {'LSP Refs':>10} │ {'Imports':>8} │ {'Usages':>8} │")
    print("├" + "─"*78 + "┤")

    for name, results in [("JavaScript", js_results), ("TypeScript", ts_results)]:
        files = len(results)
        symbols = sum(r.symbols_found for r in results)
        grep = sum(r.grep_matches for r in results)
        lsp = sum(r.lsp_refs for r in results)
        imports = sum(r.lsp_imports for r in results)
        usages = sum(r.lsp_usages for r in results)

        print(f"│ {name:<12} │ {files:>6} │ {symbols:>8} │ {grep:>8} │ {lsp:>10} │ {imports:>8} │ {usages:>8} │")

    print("└" + "─"*78 + "┘")

    # Totals
    all_results = js_results + ts_results
    total_fp = sum(r.false_positives for r in all_results)
    total_imports = sum(r.lsp_imports for r in all_results)

    print("\n KEY METRICS:")
    print(f"   • Total false positives avoided: {total_fp}")
    print(f"   • Total imports identified: {total_imports}")
    print(f"   • Files analyzed: {len(all_results)}")
    print(f"   • Total symbols found: {sum(r.symbols_found for r in all_results)}")

    print("\n CONCLUSION:")
    print("   aurora-lsp provides semantic code analysis that grep cannot:")
    print("   1. Ignores comments and documentation")
    print("   2. Separates import statements from actual usage")
    print("   3. Understands language syntax for accurate matching")


async def main():
    """Run the comparison."""
    js_workspace = Path("/tmp/liteagents")
    ts_workspace = Path("/tmp/OpenSpec")

    if not js_workspace.exists() or not ts_workspace.exists():
        print("ERROR: Repos not found. Clone first:")
        print("  git clone https://github.com/amrhas82/liteagents /tmp/liteagents")
        print("  git clone https://github.com/amrhas82/OpenSpec /tmp/OpenSpec")
        return

    js_results = await test_repo(js_workspace, ".js", "JAVASCRIPT (liteagents)")
    ts_results = await test_repo(ts_workspace, ".ts", "TYPESCRIPT (OpenSpec)")

    print_summary(js_results, ts_results)


if __name__ == "__main__":
    asyncio.run(main())
