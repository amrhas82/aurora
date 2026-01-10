#!/usr/bin/env python3
"""
Batch test migration script - Move test files between directories.

This script performs careful, verified migration of test files:
1. Reads a migration plan (JSON or manual list)
2. Moves files using git mv to preserve history
3. Verifies tests still pass after each move
4. Creates granular git commits

Usage:
    # From JSON plan (with verification)
    python scripts/migrate_tests.py --plan test-migration-plan.json --batch 1

    # From manual file list
    python scripts/migrate_tests.py --file tests/unit/foo.py --to tests/integration/

    # Dry-run mode (show what would be moved)
    python scripts/migrate_tests.py --plan test-migration-plan.json --dry-run
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def run_command(cmd: List[str], check: bool = True) -> Tuple[int, str, str]:
    """Run a shell command and return results."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"   stdout: {result.stdout}", file=sys.stderr)
        print(f"   stderr: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.returncode, result.stdout, result.stderr


def verify_tests_pass(test_path: Path) -> bool:
    """Run pytest on a specific test file to verify it passes."""
    print(f"  🧪 Verifying tests in {test_path}...")
    returncode, stdout, stderr = run_command(
        ["pytest", str(test_path), "-v", "--tb=short"], check=False
    )

    if returncode == 0:
        print(f"  ✅ Tests passed")
        return True
    else:
        print(f"  ❌ Tests failed")
        print(f"     {stderr}")
        return False


def move_test_file(source: Path, dest_dir: Path, dry_run: bool = False) -> bool:
    """Move a test file using git mv to preserve history."""
    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Construct destination path
    dest_path = dest_dir / source.name

    print(f"\n📦 Moving: {source}")
    print(f"      → {dest_path}")

    if dry_run:
        print("   [DRY-RUN] Would execute: git mv")
        return True

    # Execute git mv
    returncode, stdout, stderr = run_command(
        ["git", "mv", str(source), str(dest_path)], check=False
    )

    if returncode != 0:
        print(f"❌ Failed to move file")
        return False

    print(f"✅ Moved successfully")
    return True


def migrate_from_manual_list(
    migrations: List[Tuple[Path, Path]], verify: bool = True, dry_run: bool = False
) -> bool:
    """Migrate tests from a manual list of (source, dest_dir) tuples."""
    print(f"\n{'='*70}")
    print(f"Test Migration - Manual Mode")
    print(f"{'='*70}")
    print(f"Files to migrate: {len(migrations)}")
    print(f"Verification: {'enabled' if verify else 'disabled'}")
    print(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    print(f"{'='*70}\n")

    success_count = 0
    failure_count = 0

    for source, dest_dir in migrations:
        if not source.exists():
            print(f"❌ Source file not found: {source}")
            failure_count += 1
            continue

        # Move the file
        if move_test_file(source, dest_dir, dry_run=dry_run):
            if not dry_run and verify:
                # Verify tests still pass
                dest_path = dest_dir / source.name
                if verify_tests_pass(dest_path):
                    success_count += 1
                else:
                    print(f"⚠️  Tests failed after move - consider reverting")
                    failure_count += 1
            else:
                success_count += 1
        else:
            failure_count += 1

    print(f"\n{'='*70}")
    print(f"Migration Summary")
    print(f"{'='*70}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failure_count}")
    print(f"{'='*70}\n")

    return failure_count == 0


def migrate_from_json_plan(
    plan_path: Path, batch_index: int = 0, verify: bool = True, dry_run: bool = False
) -> bool:
    """Migrate tests from a JSON migration plan."""
    with open(plan_path) as f:
        plan = json.load(f)

    if "migration_batches" not in plan:
        print("❌ Invalid migration plan: missing 'migration_batches'")
        return False

    batches = plan["migration_batches"]

    if batch_index >= len(batches):
        print(f"❌ Batch index {batch_index} out of range (0-{len(batches)-1})")
        return False

    batch_files = batches[batch_index]

    print(f"\n{'='*70}")
    print(f"Test Migration - Batch {batch_index + 1}/{len(batches)}")
    print(f"{'='*70}")
    print(f"Files in batch: {len(batch_files)}")
    print(f"Verification: {'enabled' if verify else 'disabled'}")
    print(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    print(f"{'='*70}\n")

    # For JSON plan migrations, we don't automatically know the destination
    # This would need to be added to the plan or determined separately
    print("⚠️  JSON plan migration requires destination mapping")
    print("    Use manual mode with --file and --to flags instead")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Migrate test files between directories with verification"
    )
    parser.add_argument("--plan", type=Path, help="JSON migration plan file")
    parser.add_argument(
        "--batch", type=int, default=0, help="Batch index to migrate (0-based, default: 0)"
    )
    parser.add_argument("--file", type=Path, help="Single file to migrate (manual mode)")
    parser.add_argument("--to", type=Path, help="Destination directory (manual mode)")
    parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Verify tests pass after each move (default: True)",
    )
    parser.add_argument(
        "--no-verify", dest="verify", action="store_false", help="Skip test verification"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be moved without actually moving"
    )

    args = parser.parse_args()

    # Manual mode: single file migration
    if args.file and args.to:
        migrations = [(args.file, args.to)]
        success = migrate_from_manual_list(migrations, args.verify, args.dry_run)
    # JSON plan mode: batch migration
    elif args.plan:
        success = migrate_from_json_plan(args.plan, args.batch, args.verify, args.dry_run)
    else:
        parser.print_help()
        print("\n❌ Must specify either --plan or (--file and --to)")
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
