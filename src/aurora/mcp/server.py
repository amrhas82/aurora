#!/usr/bin/env python3
"""
AURORA MCP Server - FastMCP implementation.

Provides Model Context Protocol server for AURORA codebase indexing and search.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    from fastmcp import FastMCP
except ImportError:
    print("Error: FastMCP not installed. Install with: pip install fastmcp", file=sys.stderr)
    sys.exit(1)

from aurora.mcp.tools import AuroraMCPTools


class AuroraMCPServer:
    """MCP Server for AURORA codebase tools."""

    def __init__(self, db_path: Optional[str] = None, config_path: Optional[str] = None, test_mode: bool = False):
        """
        Initialize AURORA MCP Server.

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
        """Register MCP tools with the server."""

        @self.mcp.tool()
        def aurora_search(query: str, limit: int = 10) -> str:
            """
            Search AURORA indexed codebase.

            Args:
                query: Search query string
                limit: Maximum number of results (default: 10)

            Returns:
                JSON string with search results
            """
            return self.tools.aurora_search(query, limit)

        @self.mcp.tool()
        def aurora_index(path: str, pattern: str = "*.py") -> str:
            """
            Index codebase directory.

            Args:
                path: Directory path to index
                pattern: File pattern to match (default: *.py)

            Returns:
                JSON string with indexing stats
            """
            return self.tools.aurora_index(path, pattern)

        @self.mcp.tool()
        def aurora_stats() -> str:
            """
            Get database statistics.

            Returns:
                JSON string with database stats
            """
            return self.tools.aurora_stats()

        @self.mcp.tool()
        def aurora_context(file_path: str, function: Optional[str] = None) -> str:
            """
            Get code context from file.

            Args:
                file_path: Path to source file
                function: Optional function name to extract

            Returns:
                String with code content
            """
            return self.tools.aurora_context(file_path, function)

        @self.mcp.tool()
        def aurora_related(chunk_id: str, max_hops: int = 2) -> str:
            """
            Find related code chunks using ACT-R spreading activation.

            Args:
                chunk_id: Source chunk ID
                max_hops: Maximum relationship hops (default: 2)

            Returns:
                JSON string with related chunks and activation scores
            """
            return self.tools.aurora_related(chunk_id, max_hops)

    def run(self) -> None:
        """Run the MCP server."""
        self.mcp.run()

    def list_tools(self) -> None:
        """List all available tools (for testing)."""
        print("AURORA MCP Server - Available Tools:")
        print("=" * 50)

        # Get registered tools from FastMCP
        tools = [
            ("aurora_search", "Search indexed codebase with semantic + keyword search"),
            ("aurora_index", "Index a directory of code files"),
            ("aurora_stats", "Get database statistics (chunks, files, size)"),
            ("aurora_context", "Retrieve code context from a specific file/function"),
            ("aurora_related", "Find related code using ACT-R spreading activation"),
        ]

        for name, description in tools:
            print(f"\n{name}:")
            print(f"  {description}")

        print("\n" + "=" * 50)
        print(f"Database: {self.db_path}")
        print(f"Config: {self.config_path}")


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
