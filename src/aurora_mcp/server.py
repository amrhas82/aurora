#!/usr/bin/env python3
"""AURORA MCP Server - FastMCP implementation.

Provides Model Context Protocol server for AURORA codebase indexing and search.
"""

import argparse
import sys
from pathlib import Path

try:
    from fastmcp import FastMCP
except ImportError:
    print("Error: FastMCP not installed. Install with: pip install fastmcp", file=sys.stderr)
    sys.exit(1)

from aurora_mcp.tools import AuroraMCPTools


class AuroraMCPServer:
    """MCP Server for AURORA codebase tools."""

    def __init__(
        self, db_path: str | None = None, config_path: str | None = None, test_mode: bool = False
    ):
        """Initialize AURORA MCP Server.

        Args:
            db_path: Path to SQLite database (default: ~/.aurora/memory.db)
            config_path: Path to AURORA config file (default: ~/.aurora/config.json)
            test_mode: If True, skip FastMCP initialization (for testing)
        """
        self.db_path = db_path or str(Path.home() / ".aurora" / "memory.db")
        self.config_path = config_path or str(Path.home() / ".aurora" / "config.json")
        self.test_mode = test_mode

        # Initialize tools
        self.tools = AuroraMCPTools(self.db_path, self.config_path)

        # Initialize FastMCP server only if not in test mode
        if not test_mode:
            self.mcp = FastMCP("aurora")
            # Register tools
            self._register_tools()
        else:
            self.mcp = None

    def _register_tools(self) -> None:
        """Register MCP tools with the server.

        NOTE: aurora_search, aurora_get, and aurora_query have been deprecated.
        Use slash commands instead:
        - /aur:search <query> - Search indexed codebase
        - /aur:get <N> - Get full content of result N
        - aur soar "question" - Multi-turn SOAR query (terminal command)

        Remaining tools (preserved for future use):
        - aurora_index, aurora_context, aurora_related
        - aurora_list_agents, aurora_search_agents, aurora_show_agent
        """
        pass  # No tools registered - MCP deprecated in favor of slash commands

    def run(self) -> None:
        """Run the MCP server."""
        self.mcp.run()

    def list_tools(self) -> None:
        """List all available tools (for testing)."""
        print("AURORA MCP Server - Status:")
        print("=" * 50)
        print("\nMCP tools have been deprecated in favor of slash commands.")
        print("\nUse these slash commands instead:")
        print("  /aur:search <query>  - Search indexed codebase")
        print("  /aur:get <N>         - Get full content of result N")
        print("\nCLI commands:")
        print('  aur soar "question" - Multi-turn SOAR query')
        print('  aur query "question" - Local context retrieval')
        print("  aur mem stats        - Enhanced memory statistics")
        print("\n" + "=" * 50)
        print(f"Database: {self.db_path}")
        print(f"Config: {self.config_path}")
        print("\nNote: MCP infrastructure preserved for future use")


def main() -> None:
    """Main entry point for MCP server CLI."""
    parser = argparse.ArgumentParser(
        description="AURORA MCP Server - Model Context Protocol integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--db-path",
        type=str,
        help="Path to SQLite database (default: ~/.aurora/memory.db)",
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to AURORA config file (default: ~/.aurora/config.json)",
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: start server and list available tools",
    )

    args = parser.parse_args()

    # Create server instance
    server = AuroraMCPServer(db_path=args.db_path, config_path=args.config, test_mode=args.test)

    if args.test:
        print("AURORA MCP Server - Test Mode")
        print("=" * 50)
        server.list_tools()
        print("\nTest mode complete. Server initialized successfully!")
        sys.exit(0)

    # Run server
    print("Starting AURORA MCP Server...")
    print(f"Database: {server.db_path}")
    print(f"Config: {server.config_path}")
    server.run()


if __name__ == "__main__":
    main()
