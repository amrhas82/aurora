#!/usr/bin/env python3
"""AURORA Uninstall Helper Script.

Removes all AURORA packages cleanly.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    """Main uninstall function."""
    parser = argparse.ArgumentParser(
        description="Uninstall all AURORA packages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--keep-config",
        action="store_true",
        help="Keep ~/.aurora configuration directory",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    # List of packages to uninstall
    packages = [
        "aurora",  # Meta-package
        "aurora-core",
        "aurora-context-code",
        "aurora-soar",
        "aurora-reasoning",
        "aurora-cli",
        "aurora-testing",
    ]

    print("\n[AURORA Uninstall]")
    print("\nThe following packages will be removed:")
    for pkg in packages:
        print(f"  - {pkg}")

    if not args.keep_config:
        config_dir = Path.home() / ".aurora"
        if config_dir.exists():
            print(f"\nConfiguration directory will be removed:")
            print(f"  - {config_dir}")

    # Confirmation
    if not args.yes:
        response = input("\nProceed with uninstall? [y/N]: ")
        if response.lower() != "y":
            print("Uninstall cancelled.")
            sys.exit(0)

    print("\n[Uninstalling packages...]")

    # Uninstall each package
    for pkg in packages:
        print(f"\n→ Removing {pkg}...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", pkg],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"✓ {pkg} removed")
            else:
                # Package might not be installed - that's okay
                if "not installed" in result.stdout.lower() or "not installed" in result.stderr.lower():
                    print(f"  {pkg} was not installed (skipping)")
                else:
                    print(f"⚠ Failed to remove {pkg}: {result.stderr}")
        except Exception as e:
            print(f"⚠ Error removing {pkg}: {e}")

    # Remove config directory if requested
    if not args.keep_config:
        config_dir = Path.home() / ".aurora"
        if config_dir.exists():
            print(f"\n→ Removing configuration directory...")
            try:
                import shutil
                shutil.rmtree(config_dir)
                print(f"✓ Removed {config_dir}")
            except Exception as e:
                print(f"⚠ Failed to remove {config_dir}: {e}")
                print(f"  You can manually remove it with: rm -rf {config_dir}")

    print("\n✓ AURORA uninstall complete!\n")


if __name__ == "__main__":
    main()
