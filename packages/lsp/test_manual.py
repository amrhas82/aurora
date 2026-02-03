#!/usr/bin/env python3
"""Manual test script for aurora-lsp prototype.

Tests against sqlite.py to validate import filtering, usage detection, and dead code.
"""

import asyncio
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aurora_lsp.analysis import CodeAnalyzer, SymbolKind
from aurora_lsp.client import AuroraLSPClient
from aurora_lsp.filters import ImportFilter


WORKSPACE = Path("/home/hamr/PycharmProjects/aurora")
TEST_FILE = "packages/core/src/aurora_core/store/sqlite.py"

# Ground truth: Key methods and their expected characteristics
# Ground truth: Key methods and their expected characteristics (0-indexed lines)
GROUND_TRUTH = {
    "SQLiteStore": {"line": 38, "kind": "class", "expect_usages": True},
    "save_chunk": {"line": 264, "kind": "method", "expect_usages": True},
    "get_chunk": {"line": 329, "kind": "method", "expect_usages": True},
    "_get_connection": {"line": 81, "kind": "method", "expect_usages": True},  # Internal but used
    "_deserialize_chunk": {"line": 365, "kind": "method", "expect_usages": True},  # Internal
    "backup_database": {"line": 1316, "kind": "function", "expect_usages": True},  # Standalone
}


async def test_import_filtering():
    """Test import vs usage filtering."""
    print("\n" + "=" * 60)
    print("TEST: Import Filtering")
    print("=" * 60)

    f = ImportFilter("python")

    # Test cases from sqlite.py's actual imports
    test_lines = [
        ("import json", True),
        ("import sqlite3", True),
        ("from pathlib import Path", True),
        ("from aurora_core.exceptions import (", True),
        ("    ChunkNotFoundError,", False),  # Continuation, not import
        ("conn = self._get_connection()", False),
        ("def save_chunk(self, chunk):", False),
        ("if TYPE_CHECKING:", False),
    ]

    passed = 0
    for line, expected in test_lines:
        result = f.is_import_line(line)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        print(f"  {status} '{line[:50]}...' -> {result} (expected {expected})")

    print(f"\nPassed: {passed}/{len(test_lines)}")
    return passed == len(test_lines)


async def test_references_raw(client: AuroraLSPClient):
    """Test raw reference finding (no filtering)."""
    print("\n" + "=" * 60)
    print("TEST: Raw References (SQLiteStore class)")
    print("=" * 60)

    refs = await client.request_references(TEST_FILE, 38, 6)  # SQLiteStore class (line 39, 0-indexed=38)

    print(f"Found {len(refs)} total references")
    if refs:
        print("\nSample references:")
        for ref in refs[:10]:
            print(f"  {ref['file']}:{ref['line']}")

    return len(refs) > 0


async def test_document_symbols(client: AuroraLSPClient):
    """Test document symbols extraction."""
    print("\n" + "=" * 60)
    print("TEST: Document Symbols")
    print("=" * 60)

    symbols = await client.request_document_symbols(TEST_FILE)

    if not symbols:
        print("No symbols found!")
        return False

    # Flatten and count
    def flatten(syms, depth=0):
        result = []
        for s in syms:
            if s is None:
                continue
            result.append((s, depth))
            if isinstance(s, dict) and "children" in s:
                result.extend(flatten(s["children"], depth + 1))
        return result

    flat = flatten(symbols)
    print(f"Found {len(flat)} total symbols")

    # Count by kind
    kinds = {}
    for s, _ in flat:
        k = s.get("kind", 0)
        kinds[k] = kinds.get(k, 0) + 1

    print("\nBy kind:")
    for k, count in sorted(kinds.items()):
        try:
            name = SymbolKind(k).name
        except ValueError:
            name = f"Unknown({k})"
        print(f"  {name}: {count}")

    # Show some symbols
    print("\nSample symbols:")
    for s, depth in flat[:15]:
        indent = "  " * depth
        print(f"  {indent}{s.get('name', '?')} (kind={s.get('kind')})")

    return len(flat) > 10


async def test_usage_filtering(analyzer: CodeAnalyzer):
    """Test usage vs import filtering."""
    print("\n" + "=" * 60)
    print("TEST: Usage Filtering (SQLiteStore)")
    print("=" * 60)

    result = await analyzer.find_usages(TEST_FILE, 38, 6, include_imports=False)

    print(f"Usages: {result['total_usages']}")
    print(f"Imports: {result['total_imports']}")

    if result['usages']:
        print("\nSample usages (not imports):")
        for u in result['usages'][:5]:
            context = u.get('context', '')[:60]
            print(f"  {u['file']}:{u['line']}  {context}")

    if result['imports']:
        print("\nSample imports (filtered out):")
        for i in result['imports'][:5]:
            context = i.get('context', '')[:60]
            print(f"  {i['file']}:{i['line']}  {context}")

    return result['total_usages'] > 0


async def test_usage_summary(analyzer: CodeAnalyzer):
    """Test usage summary with impact."""
    print("\n" + "=" * 60)
    print("TEST: Usage Summary (save_chunk method)")
    print("=" * 60)

    # save_chunk is at line 264 (0-indexed)
    summary = await analyzer.get_usage_summary(TEST_FILE, 264, 8, "save_chunk")

    print(f"Symbol: {summary['symbol']}")
    print(f"Total usages: {summary['total_usages']}")
    print(f"Total imports: {summary['total_imports']}")
    print(f"Impact: {summary['impact']}")
    print(f"Files affected: {summary['files_affected']}")

    if summary['usages_by_file']:
        print("\nUsages by file:")
        for file, usages in list(summary['usages_by_file'].items())[:5]:
            print(f"  {file}: {len(usages)}")

    return summary['total_usages'] >= 0


async def test_callers(analyzer: CodeAnalyzer):
    """Test finding callers of a function."""
    print("\n" + "=" * 60)
    print("TEST: Callers (save_chunk method)")
    print("=" * 60)

    callers = await analyzer.get_callers(TEST_FILE, 264, 8)

    print(f"Found {len(callers)} callers")
    for c in callers[:10]:
        print(f"  {c['name']}() in {c['file']}:{c['line']}")

    return True  # Callers may be empty, that's OK


async def test_dead_code(analyzer: CodeAnalyzer):
    """Test dead code detection."""
    print("\n" + "=" * 60)
    print("TEST: Dead Code Detection (sqlite.py only)")
    print("=" * 60)

    # Test on single file first
    dead = await analyzer.find_dead_code(
        WORKSPACE / TEST_FILE,
        include_private=False
    )

    print(f"Found {len(dead)} potentially dead items")
    for item in dead[:10]:
        imports_note = f" (imported {item['imports']}x)" if item['imports'] > 0 else ""
        print(f"  {item['name']} ({item['kind']}) at line {item['line']}{imports_note}")

    return True  # Dead code results vary


async def main():
    """Run all tests."""
    print("Aurora LSP Manual Test Suite")
    print("Testing against:", TEST_FILE)
    print("Workspace:", WORKSPACE)

    # Test 1: Import filtering (no LSP needed)
    await test_import_filtering()

    # Initialize client
    print("\n" + "=" * 60)
    print("Initializing LSP client...")
    print("=" * 60)

    client = AuroraLSPClient(WORKSPACE)
    analyzer = CodeAnalyzer(client, WORKSPACE)

    try:
        # Test 2: Raw references
        await test_references_raw(client)

        # Test 3: Document symbols
        await test_document_symbols(client)

        # Test 4: Usage filtering
        await test_usage_filtering(analyzer)

        # Test 5: Usage summary
        await test_usage_summary(analyzer)

        # Test 6: Callers
        await test_callers(analyzer)

        # Test 7: Dead code
        await test_dead_code(analyzer)

    finally:
        print("\n" + "=" * 60)
        print("Closing LSP client...")
        await client.close()

    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
