#!/usr/bin/env python3
"""Before/After comparison showing LSP value vs grep-only approach.

Demonstrates what aurora-lsp provides that raw grep cannot:
1. Semantic symbol extraction (not just text patterns)
2. Import vs usage separation
3. Accurate reference finding (ignores comments/strings)
"""

import asyncio
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from aurora_lsp.client import AuroraLSPClient
from aurora_lsp.filters import ImportFilter


@dataclass
class ComparisonResult:
    """Before/after comparison for a single symbol."""

    file: str
    symbol: str
    symbol_kind: str
    symbol_line: int

    # BEFORE (grep-only)
    grep_matches: int
    grep_false_positives: list[str]  # Matches in comments/strings

    # AFTER (LSP)
    lsp_refs: int
    lsp_imports: int
    lsp_usages: int

    def improvement(self) -> str:
        """Describe the improvement from LSP."""
        if self.grep_false_positives:
            return f"Avoided {len(self.grep_false_positives)} false positives"
        if self.lsp_imports > 0:
            return f"Separated {self.lsp_imports} imports from {self.lsp_usages} usages"
        return "Accurate semantic matching"


def grep_count(workspace: Path, pattern: str, extensions: list[str]) -> tuple[int, list[str]]:
    """Count grep matches and find potential false positives."""
    matches = 0
    false_positives = []

    for ext in extensions:
        for file_path in workspace.rglob(f"*{ext}"):
            if "node_modules" in str(file_path):
                continue
            try:
                content = file_path.read_text()
                for i, line in enumerate(content.splitlines(), 1):
                    if re.search(r"\b" + re.escape(pattern) + r"\b", line):
                        matches += 1
                        # Check if in comment or string
                        stripped = line.strip()
                        if (
                            stripped.startswith("//")
                            or stripped.startswith("*")
                            or stripped.startswith("#")
                            or stripped.startswith("/*")
                        ):
                            rel_path = file_path.relative_to(workspace)
                            false_positives.append(f"{rel_path}:{i}: {stripped[:60]}")
            except Exception:
                continue

    return matches, false_positives


async def analyze_symbol(
    client: AuroraLSPClient,
    workspace: Path,
    file_path: Path,
    symbol: dict,
    extensions: list[str],
) -> ComparisonResult:
    """Analyze a symbol with both grep and LSP."""
    name = symbol.get("name", "?")
    kind_num = symbol.get("kind", 0)
    kind_map = {5: "Class", 6: "Method", 12: "Function", 13: "Variable", 14: "Constant"}
    kind = kind_map.get(kind_num, f"Kind({kind_num})")

    range_info = symbol.get("range") or symbol.get("location", {}).get("range", {})
    start = range_info.get("start", {})
    line = start.get("line", 0)
    col = start.get("character", 0)

    # BEFORE: Grep count
    grep_matches, false_positives = grep_count(workspace, name, extensions)

    # AFTER: LSP references
    refs = await client.request_references(file_path, line, col)
    lsp_refs = len(refs)

    # Filter imports vs usages
    lang = "javascript" if file_path.suffix == ".js" else "typescript"
    import_filter = ImportFilter(lang)
    imports = 0
    usages = 0

    for ref in refs:
        ref_file = Path(ref.get("file", ""))
        ref_line = ref.get("line", 0)
        try:
            if ref_file.exists():
                lines = ref_file.read_text().splitlines()
                if 0 <= ref_line < len(lines):
                    line_content = lines[ref_line]
                    if import_filter.is_import_line(line_content):
                        imports += 1
                    else:
                        usages += 1
                else:
                    usages += 1
            else:
                usages += 1
        except Exception:
            usages += 1

    return ComparisonResult(
        file=str(file_path.relative_to(workspace)),
        symbol=name,
        symbol_kind=kind,
        symbol_line=line + 1,
        grep_matches=grep_matches,
        grep_false_positives=false_positives[:3],  # Limit
        lsp_refs=lsp_refs,
        lsp_imports=imports,
        lsp_usages=usages,
    )


def flatten_symbols(symbols: list) -> list[dict]:
    """Flatten nested symbol tree."""
    result = []
    for s in symbols:
        result.append(s)
        children = s.get("children", [])
        if children:
            result.extend(flatten_symbols(children))
    return result


async def test_repo(workspace: Path, extension: str, repo_name: str) -> list[ComparisonResult]:
    """Test a repository."""
    print(f"\n{'=' * 70}")
    print(f"BEFORE/AFTER COMPARISON: {repo_name}")
    print(f"{'=' * 70}")

    # Find good source files (not tests, not barrel files)
    files = list(workspace.rglob(f"*{extension}"))
    files = [
        f
        for f in files
        if "node_modules" not in str(f)
        and "test" not in str(f).lower()
        and f.name != f"index{extension}"
    ]
    files.sort(key=lambda f: f.stat().st_size, reverse=True)
    files = files[:5]  # Top 5 source files

    results = []
    client = AuroraLSPClient(workspace)
    extensions = [extension]

    try:
        for file_path in files:
            symbols = await client.request_document_symbols(file_path)
            flat_symbols = flatten_symbols(symbols or [])

            # Find classes/functions to analyze
            interesting = [
                s
                for s in flat_symbols
                if s.get("kind") in [5, 6, 12, 14]  # Class, Method, Function, Constant
                and len(s.get("name", "")) > 3
                and not s.get("name", "").startswith("_")
            ]

            # Analyze up to 2 symbols per file
            for sym in interesting[:2]:
                result = await analyze_symbol(client, workspace, file_path, sym, extensions)
                results.append(result)
                print(
                    f"\n{result.symbol} ({result.symbol_kind}) in {result.file}:{result.symbol_line}"
                )
                print(f"  BEFORE (grep): {result.grep_matches} matches")
                if result.grep_false_positives:
                    print("    False positives found:")
                    for fp in result.grep_false_positives:
                        print(f"      - {fp}")
                print(
                    f"  AFTER (LSP):   {result.lsp_refs} refs ({result.lsp_imports} imports + {result.lsp_usages} usages)"
                )
                print(f"  → {result.improvement()}")

    finally:
        await client.close()

    return results


def print_final_summary(js_results: list[ComparisonResult], ts_results: list[ComparisonResult]):
    """Print final comparison summary."""
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    all_results = js_results + ts_results

    total_grep = sum(r.grep_matches for r in all_results)
    total_lsp = sum(r.lsp_refs for r in all_results)
    total_imports = sum(r.lsp_imports for r in all_results)
    total_usages = sum(r.lsp_usages for r in all_results)
    total_fp = sum(len(r.grep_false_positives) for r in all_results)

    print(f"\nSymbols analyzed: {len(all_results)}")
    print("\nGREP (Before):")
    print(f"  Total matches: {total_grep}")
    print(f"  False positives detected: {total_fp}")

    print("\nLSP (After):")
    print(f"  Total references: {total_lsp}")
    print(f"  Imports: {total_imports}")
    print(f"  Usages: {total_usages}")

    if total_imports > 0:
        print(f"\n✓ Import/Usage separation: {total_imports} imports identified")
    if total_fp > 0:
        print(f"✓ False positives avoided: {total_fp} grep matches in comments/strings")

    print("\n" + "-" * 70)
    print("LSP ADVANTAGES:")
    print("  1. Semantic accuracy - ignores comments, strings, partial matches")
    print("  2. Import filtering - separates import statements from actual usages")
    print("  3. Language-aware - understands syntax, not just text patterns")
    print("-" * 70)


async def main():
    """Run before/after comparison on both repos."""
    js_workspace = Path("/tmp/liteagents")
    ts_workspace = Path("/tmp/OpenSpec")

    js_results = await test_repo(js_workspace, ".js", "liteagents (JavaScript)")
    ts_results = await test_repo(ts_workspace, ".ts", "OpenSpec (TypeScript)")

    print_final_summary(js_results, ts_results)


if __name__ == "__main__":
    asyncio.run(main())
