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

from aurora_mcp.tools import AuroraMCPTools


class AuroraMCPServer:
    """MCP Server for AURORA codebase tools."""

    def __init__(
        self, db_path: str | None = None, config_path: str | None = None, test_mode: bool = False
    ):
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
        def aurora_context(file_path: str, function: str | None = None) -> str:
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

        @self.mcp.tool()
        def aurora_query(
            query: str,
            limit: int = 10,
            type_filter: str | None = None,
            verbose: bool = False,
        ) -> str:
            """
            Retrieve relevant context from AURORA memory without LLM inference.

            This tool provides intelligent context retrieval with complexity assessment
            and confidence scoring. It returns structured context for the host LLM
            (Claude Code CLI) to reason about, rather than calling external LLM APIs.

            Args:
                query: Natural language query string (required)
                limit: Maximum number of chunks to retrieve (default: 10)
                type_filter: Filter by memory type - "code", "reas", "know", or None (default: None)
                verbose: Include detailed metadata in response (default: False)

            Returns:
                JSON string with:
                - context: Retrieved memory chunks with content, metadata, and relevance scores
                - assessment: Complexity assessment and retrieval confidence score
                - metadata: Database stats and result counts

            Examples:
                Basic retrieval:
                    aurora_query("What is a Python decorator?")

                Type-filtered retrieval:
                    aurora_query("async patterns", type_filter="code", limit=5)

                Detailed metadata:
                    aurora_query("SOAR pipeline", verbose=True)

            Note:
                No API key required. This tool runs inside Claude Code CLI which
                provides the LLM reasoning capabilities. For standalone usage with
                LLM responses, use the CLI command: $ aur query "your question"
            """
            return self.tools.aurora_query(query, limit, type_filter, verbose)

        @self.mcp.tool()
        def aurora_get(index: int) -> str:
            """
            Retrieve a full chunk by index from the last search results.

            This tool allows you to get the complete content of a specific result
            from your last aurora_search or aurora_query call. Results are numbered
            starting from 1 (1-indexed).

            Workflow:
            1. Call aurora_search or aurora_query to get numbered results
            2. Review the list and choose which result you want
            3. Call aurora_get(N) to retrieve the full chunk for result N

            Args:
                index: 1-indexed position in last search results (must be >= 1)

            Returns:
                JSON string with:
                - chunk: Complete chunk with all metadata (id, type, content, file_path, etc.)
                - metadata: Index position and total count

            Examples:
                After aurora_search("async patterns"):
                    aurora_get(1)  # Get first result
                    aurora_get(3)  # Get third result

            Note:
                Session cache expires after 10 minutes. Results are stored per-session
                and cleared when a new search is performed.
            """
            return self.tools.aurora_get(index)

        @self.mcp.tool()
        def aurora_list_agents() -> str:
            """
            List all discovered agents from configured sources.

            Use this tool to browse, discover, and find available agents. Returns
            a complete inventory of all agents accessible in the current environment.

            Primary action keywords: list, show, get, fetch, retrieve, browse, discover
            Domain keywords: agents, specialists, experts, roles, personas, subagents, assistants
            Context keywords: available, registered, defined, configured, ready, accessible, discovered
            Use case keywords: what, which, who, all, every, complete, inventory, catalog

            No API key required. Local agent directory listing only.

            Returns:
                JSON array of agents containing:
                - id: Agent identifier (kebab-case)
                - title: Agent role/title
                - source_path: Path to agent markdown file
                - when_to_use: Guidance on when to invoke this agent

            Examples:
                # List all available agents
                aurora_list_agents()

                # After listing, you can:
                # - Use aurora_search_agents() to filter by keyword
                # - Use aurora_show_agent(id) to view full agent details
            """
            return self.tools.aurora_list_agents()

        @self.mcp.tool()
        def aurora_search_agents(query: str) -> str:
            """
            Search agents by keyword with relevance scoring.

            Use this tool to find, search, discover, and filter agents by keywords.
            Returns matching agents sorted by relevance score (0.0-1.0).

            Primary action keywords: search, find, discover, filter, locate, identify, match
            Domain keywords: agent, specialist, expert, role, persona, subagent, assistant
            Context keywords: for, with, about, related, relevant, matching, suitable
            Use case keywords: help, assist, guide, when, which, who, best, right

            Uses substring matching to search agent id, title, and when_to_use fields.
            No API key required. Local substring-based search only.

            Args:
                query: Search query string (required, non-empty)

            Returns:
                JSON array of matching agents containing:
                - id: Agent identifier
                - title: Agent role/title
                - source_path: Path to agent markdown file
                - when_to_use: When to use guidance
                - relevance_score: Match score from 0.0 to 1.0

            Examples:
                # Search for testing-related agents
                aurora_search_agents("test")

                # Find agents for code review
                aurora_search_agents("review")

                # Discover quality assurance specialists
                aurora_search_agents("quality")

            Note:
                Returns empty array if no matches found. Results sorted by relevance
                score descending (best matches first).
            """
            return self.tools.aurora_search_agents(query)

        @self.mcp.tool()
        def aurora_show_agent(agent_id: str) -> str:
            """
            Show full agent details including complete markdown content.

            Use this tool to retrieve, view, get, fetch, or display full details for
            a specific agent by ID. Returns complete agent information including the
            entire markdown file content with instructions and examples.

            Primary action keywords: show, get, retrieve, fetch, view, display, read, load
            Domain keywords: agent, specialist, expert, role, persona, details, info
            Context keywords: full, complete, entire, whole, detailed, comprehensive
            Use case keywords: about, details, information, content, instructions, guide

            No API key required. Reads local agent markdown file only.

            Args:
                agent_id: Agent identifier (required, non-empty, kebab-case)

            Returns:
                JSON with full agent details:
                - id: Agent identifier
                - title: Agent role/title
                - source_path: Path to agent markdown file
                - when_to_use: When to use guidance
                - content: Complete markdown file content

                Or error JSON if agent not found:
                - error: "Agent not found"
                - agent_id: The requested agent ID

            Examples:
                # Show full details for QA test architect
                aurora_show_agent("qa-test-architect")

                # Get complete information for full stack developer
                aurora_show_agent("full-stack-dev")

                # View orchestrator agent details
                aurora_show_agent("orchestrator")

            Note:
                Use aurora_list_agents() or aurora_search_agents() to discover
                available agent IDs first.
            """
            return self.tools.aurora_show_agent(agent_id)

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
            ("aurora_context", "Retrieve code context from a specific file/function"),
            ("aurora_related", "Find related code using ACT-R spreading activation"),
            ("aurora_query", "Retrieve relevant context without LLM inference"),
            ("aurora_get", "Get full chunk by index from last search results"),
            ("aurora_list_agents", "List all discovered agents from configured sources"),
            ("aurora_search_agents", "Search agents by keyword with relevance scoring"),
            ("aurora_show_agent", "Show full agent details including markdown content"),
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
