#!/usr/bin/env python3
"""Quick verification script for path locality changes."""

import sys
from pathlib import Path


def test_conversation_logger():
    """Test ConversationLogger uses project-local path."""
    from packages.core.src.aurora_core.logging.conversation_logger import ConversationLogger

    logger = ConversationLogger()
    expected = Path.cwd() / ".aurora" / "logs" / "conversations"

    if logger.base_path != expected:
        print(f"❌ ConversationLogger: Expected {expected}, got {logger.base_path}")
        return False
    print(f"✓ ConversationLogger uses project-local path: {logger.base_path}")
    return True


def test_planning_config():
    """Test planning config uses project-local path."""
    # Clear environment variable to test default
    import os

    from packages.planning.src.aurora_planning.planning_config import get_plans_dir

    old_val = os.environ.pop("AURORA_PLANS_DIR", None)

    try:
        plans_dir = get_plans_dir()
        expected = Path.cwd() / ".aurora" / "plans"

        if plans_dir != expected:
            print(f"❌ Planning config: Expected {expected}, got {plans_dir}")
            return False
        print(f"✓ Planning config uses project-local path: {plans_dir}")
        return True
    finally:
        if old_val:
            os.environ["AURORA_PLANS_DIR"] = old_val


def test_planning_core():
    """Test planning core default path."""
    from packages.cli.src.aurora_cli.planning.core import get_default_plans_path

    path = get_default_plans_path()
    expected = Path.cwd() / ".aurora" / "plans"

    if path != expected:
        print(f"❌ Planning core: Expected {expected}, got {path}")
        return False
    print(f"✓ Planning core uses project-local path: {path}")
    return True


def test_cli_config():
    """Test CLI config defaults."""
    from packages.cli.src.aurora_cli.config import Config

    config = Config()

    # Check all project-local paths
    checks = [
        ("logging_file", "./.aurora/logs/aurora.log"),
        ("mcp_log_file", "./.aurora/logs/mcp.log"),
        ("db_path", "./.aurora/memory.db"),
        ("agents_manifest_path", "./.aurora/cache/agent_manifest.json"),
        ("planning_base_dir", "./.aurora/plans"),
    ]

    all_passed = True
    for attr, expected in checks:
        actual = getattr(config, attr)
        if actual != expected:
            print(f"❌ Config.{attr}: Expected {expected}, got {actual}")
            all_passed = False
        else:
            print(f"✓ Config.{attr} = {expected}")

    # Check budget tracker is still global
    if not config.budget_tracker_path.startswith("~/.aurora"):
        print(f"❌ Budget tracker should be global: {config.budget_tracker_path}")
        all_passed = False
    else:
        print(f"✓ Budget tracker is global: {config.budget_tracker_path}")

    return all_passed


def test_budget_tracker():
    """Test budget tracker uses global path."""
    from packages.core.src.aurora_core.budget.tracker import CostTracker

    tracker = CostTracker()
    expected_prefix = str(Path.home() / ".aurora")

    if not str(tracker.tracker_path).startswith(expected_prefix):
        print(
            f"❌ Budget tracker: Expected path starting with {expected_prefix}, got {tracker.tracker_path}"
        )
        return False
    print(f"✓ Budget tracker uses global path: {tracker.tracker_path}")
    return True


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Verifying Path Locality Changes")
    print("=" * 60)
    print()

    tests = [
        ("ConversationLogger", test_conversation_logger),
        ("Planning Config", test_planning_config),
        ("Planning Core", test_planning_core),
        ("CLI Config", test_cli_config),
        ("Budget Tracker", test_budget_tracker),
    ]

    results = []
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        print("-" * 60)
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ {name} failed with error: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    print()
    print(f"Results: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n✓ All path locality changes verified successfully!")
        return 0
    else:
        print(f"\n❌ {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
