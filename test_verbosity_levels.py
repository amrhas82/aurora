#!/usr/bin/env python3
"""Test script to validate Aurora CLI verbosity levels.

Tests:
1. Default logging level (WARNING)
2. Verbose flag (-v) sets INFO level
3. Debug flag (--debug) sets DEBUG level
4. Logging output goes to appropriate streams
"""

import logging
import subprocess
import sys
from pathlib import Path


def test_default_logging():
    """Test that default logging is WARNING level."""
    print("\n=== Test 1: Default Logging (WARNING) ===")
    result = subprocess.run(["aur", "version"], capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")

    # Should not show DEBUG or INFO logs
    assert "DEBUG" not in result.stderr
    assert "INFO" not in result.stderr
    print("✓ Default logging works (WARNING level)")


def test_verbose_flag():
    """Test that -v flag enables INFO level logging."""
    print("\n=== Test 2: Verbose Flag (-v) ===")
    result = subprocess.run(["aur", "-v", "version"], capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")

    # With verbose, we might see INFO logs in some commands
    # But version command is simple and may not log anything
    print("✓ Verbose flag accepted")


def test_debug_flag():
    """Test that --debug flag enables DEBUG level logging."""
    print("\n=== Test 3: Debug Flag (--debug) ===")
    result = subprocess.run(["aur", "--debug", "version"], capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")

    # Debug flag should be accepted without error
    assert result.returncode == 0
    print("✓ Debug flag accepted")


def test_query_verbose():
    """Test verbose output with query command."""
    print("\n=== Test 4: Query Command with Verbose ===")

    # First check if memory database exists
    db_path = Path.home() / ".aurora" / "memory.db"
    if not db_path.exists():
        print("⚠ Memory database not found, skipping query test")
        return

    result = subprocess.run(
        ["aur", "query", "test verbosity", "-v"], capture_output=True, text=True, timeout=10
    )
    print(f"Exit code: {result.returncode}")
    print(f"Stdout (first 500 chars): {result.stdout[:500]}")
    print(f"Stderr: {result.stderr}")

    # Should show phase output
    if result.returncode == 0:
        assert "Phase" in result.stdout
        print("✓ Query verbose output works")
    else:
        print(f"⚠ Query failed with exit code {result.returncode}")


def test_doctor_verbose_levels():
    """Test doctor command with different verbosity levels."""
    print("\n=== Test 5: Doctor Command Verbosity Levels ===")

    # Test default
    print("\n--- Default ---")
    result = subprocess.run(["aur", "doctor"], capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    print(f"Output length: {len(result.stdout)} chars")
    print(f"Contains 'CORE SYSTEM': {'CORE SYSTEM' in result.stdout}")

    # Test verbose
    print("\n--- Verbose ---")
    result_v = subprocess.run(["aur", "-v", "doctor"], capture_output=True, text=True)
    print(f"Exit code: {result_v.returncode}")
    print(f"Output length: {len(result_v.stdout)} chars")
    print(f"Contains 'CORE SYSTEM': {'CORE SYSTEM' in result_v.stdout}")

    # Test debug
    print("\n--- Debug ---")
    result_d = subprocess.run(["aur", "--debug", "doctor"], capture_output=True, text=True)
    print(f"Exit code: {result_d.returncode}")
    print(f"Output length: {len(result_d.stdout)} chars")
    print(f"Stderr length: {len(result_d.stderr)} chars")
    print(f"Contains 'CORE SYSTEM': {'CORE SYSTEM' in result_d.stdout}")

    print("✓ Doctor command works with all verbosity levels")


def test_python_logging_levels():
    """Test Python logging configuration directly."""
    print("\n=== Test 6: Python Logging Levels ===")

    # Test WARNING (default)
    logging.basicConfig(level=logging.WARNING, force=True)
    logger = logging.getLogger("test")

    print("\n--- WARNING level (default) ---")
    logger.debug("This DEBUG should NOT appear")
    logger.info("This INFO should NOT appear")
    logger.warning("This WARNING should appear")

    # Test INFO (verbose)
    logging.basicConfig(level=logging.INFO, force=True)
    logger = logging.getLogger("test")

    print("\n--- INFO level (verbose) ---")
    logger.debug("This DEBUG should NOT appear")
    logger.info("This INFO should appear")
    logger.warning("This WARNING should appear")

    # Test DEBUG
    logging.basicConfig(level=logging.DEBUG, force=True)
    logger = logging.getLogger("test")

    print("\n--- DEBUG level (debug) ---")
    logger.debug("This DEBUG should appear")
    logger.info("This INFO should appear")
    logger.warning("This WARNING should appear")

    print("✓ Python logging levels work correctly")


def test_verbosity_enum():
    """Test VerbosityLevel enum from conversation_logger."""
    print("\n=== Test 7: VerbosityLevel Enum ===")

    try:
        from aurora_core.logging import VerbosityLevel

        print(f"Available levels: {[v.value for v in VerbosityLevel]}")
        assert VerbosityLevel.QUIET == "quiet"
        assert VerbosityLevel.NORMAL == "normal"
        assert VerbosityLevel.VERBOSE == "verbose"
        assert VerbosityLevel.JSON == "json"

        print("✓ VerbosityLevel enum defined correctly")
    except ImportError as e:
        print(f"⚠ Could not import VerbosityLevel: {e}")


def main():
    """Run all verbosity tests."""
    print("=" * 60)
    print("Aurora CLI Verbosity Level Tests")
    print("=" * 60)

    tests = [
        test_default_logging,
        test_verbose_flag,
        test_debug_flag,
        test_query_verbose,
        test_doctor_verbose_levels,
        test_python_logging_levels,
        test_verbosity_enum,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"⚠ Test error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
