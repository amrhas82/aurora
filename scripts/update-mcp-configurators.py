#!/usr/bin/env python3
"""Script to identify and update MCP configurators for PRD-0024.

This script:
1. Lists all MCP configurator files
2. Identifies which ones have AURORA_MCP_PERMISSIONS or allowed_tools lists
3. Shows which deprecated tools need to be removed

Deprecated tools:
- mcp__aurora__aurora_query
- mcp__aurora__aurora_search
- mcp__aurora__aurora_get

Remaining tools (6):
- mcp__aurora__aurora_index
- mcp__aurora__aurora_context
- mcp__aurora__aurora_related
- mcp__aurora__aurora_list_agents
- mcp__aurora__aurora_search_agents
- mcp__aurora__aurora_show_agent
"""

import ast
import sys
from pathlib import Path
from typing import NamedTuple


class ConfiguratorInfo(NamedTuple):
    """Information about a configurator file."""

    path: Path
    has_permissions_list: bool
    permissions_list_name: str | None
    deprecated_tools_found: list[str]


# Deprecated tools to remove
DEPRECATED_TOOLS = [
    "mcp__aurora__aurora_query",
    "mcp__aurora__aurora_search",
    "mcp__aurora__aurora_get",
]

# Remaining tools (should be preserved)
REMAINING_TOOLS = [
    "mcp__aurora__aurora_index",
    "mcp__aurora__aurora_context",
    "mcp__aurora__aurora_related",
    "mcp__aurora__aurora_list_agents",
    "mcp__aurora__aurora_search_agents",
    "mcp__aurora__aurora_show_agent",
]


def find_mcp_configurators(mcp_dir: Path) -> list[Path]:
    """Find all MCP configurator Python files.

    Args:
        mcp_dir: Directory containing MCP configurators

    Returns:
        List of Python files (excluding __init__, base, registry)
    """
    exclude_files = {"__init__.py", "base.py", "registry.py"}
    return [f for f in mcp_dir.glob("*.py") if f.name not in exclude_files]


def analyze_configurator(file_path: Path) -> ConfiguratorInfo:
    """Analyze a configurator file for tool permissions lists.

    Args:
        file_path: Path to configurator file

    Returns:
        ConfiguratorInfo with analysis results
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except Exception as e:
        print(f"  ERROR parsing {file_path.name}: {e}", file=sys.stderr)
        return ConfiguratorInfo(
            path=file_path,
            has_permissions_list=False,
            permissions_list_name=None,
            deprecated_tools_found=[],
        )

    # Look for module-level list assignments
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    # Check for permission list names
                    if var_name in ("AURORA_MCP_PERMISSIONS", "ALLOWED_TOOLS", "allowed_tools"):
                        # Extract string literals from the list
                        if isinstance(node.value, ast.List):
                            tools = []
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    tools.append(elt.value)

                            # Check for deprecated tools
                            deprecated_found = [tool for tool in tools if tool in DEPRECATED_TOOLS]

                            return ConfiguratorInfo(
                                path=file_path,
                                has_permissions_list=True,
                                permissions_list_name=var_name,
                                deprecated_tools_found=deprecated_found,
                            )

    return ConfiguratorInfo(
        path=file_path,
        has_permissions_list=False,
        permissions_list_name=None,
        deprecated_tools_found=[],
    )


def main():
    """Main entry point."""
    # Find MCP configurators directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    mcp_dir = project_root / "packages" / "cli" / "src" / "aurora_cli" / "configurators" / "mcp"

    if not mcp_dir.exists():
        print(f"ERROR: MCP configurators directory not found: {mcp_dir}", file=sys.stderr)
        sys.exit(1)

    print("=" * 70)
    print("MCP Configurator Analysis for PRD-0024")
    print("=" * 70)
    print()

    # Find all configurators
    configurators = find_mcp_configurators(mcp_dir)
    print(f"Found {len(configurators)} configurator files:")
    for conf in configurators:
        print(f"  - {conf.name}")
    print()

    # Analyze each configurator
    print("=" * 70)
    print("Analysis Results")
    print("=" * 70)
    print()

    needs_update = []
    no_update_needed = []

    for conf_path in configurators:
        info = analyze_configurator(conf_path)

        if info.has_permissions_list:
            if info.deprecated_tools_found:
                needs_update.append(info)
                print(f"[UPDATE NEEDED] {info.path.name}")
                print(f"  Variable: {info.permissions_list_name}")
                print(f"  Deprecated tools found: {len(info.deprecated_tools_found)}")
                for tool in info.deprecated_tools_found:
                    print(f"    - {tool}")
                print()
            else:
                no_update_needed.append(info)
                print(f"[OK] {info.path.name}")
                print(f"  Variable: {info.permissions_list_name}")
                print("  No deprecated tools found")
                print()
        else:
            no_update_needed.append(info)
            print(f"[OK] {info.path.name}")
            print("  No permissions list found (inherits from base)")
            print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()
    print(f"Total configurators: {len(configurators)}")
    print(f"Need updates: {len(needs_update)}")
    print(f"No updates needed: {len(no_update_needed)}")
    print()

    if needs_update:
        print("Files requiring updates:")
        for info in needs_update:
            print(f"  - {info.path}")
        print()
        print("Manual update required:")
        print("  1. Open each file above")
        print(f"  2. Find the {needs_update[0].permissions_list_name} list")
        print("  3. Remove these 3 deprecated tools:")
        for tool in DEPRECATED_TOOLS:
            print(f"     - '{tool}'")
        print("  4. Add comment explaining removal")
        print("  5. Verify 6 remaining tools are present:")
        for tool in REMAINING_TOOLS:
            print(f"     - '{tool}'")
    else:
        print("All configurators are up to date!")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
