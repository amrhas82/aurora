"""Memory command implementation for AURORA CLI.

This module implements the 'aur mem' command for explicit memory recall.
It uses HybridRetriever (activation + semantic) to search stored chunks
and displays results in a readable format.

Usage:
    aur mem "query text" [options]
    aur mem "calculate total" --max-results 10
    aur mem "authentication" --type function --min-activation 0.5
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from aurora_context_code.semantic import EmbeddingProvider, HybridRetriever
from aurora_core.activation import ActivationEngine
from aurora_core.store import SQLiteStore


__all__ = ["memory_command", "format_memory_results"]

logger = logging.getLogger(__name__)
console = Console()


def extract_keywords(query: str) -> list[str]:
    """Extract keywords from query for memory search.

    Args:
        query: User query string

    Returns:
        List of extracted keywords (lowercase, deduplicated)

    Example:
        >>> extract_keywords("How to calculate the total price?")
        ['calculate', 'total', 'price']
    """
    # Remove common stop words
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
        "to", "was", "will", "with", "how", "what", "when", "where", "why",
    }

    # Extract words (alphanumeric sequences)
    words = re.findall(r'\b\w+\b', query.lower())

    # Filter stop words and short words
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return unique_keywords


def format_memory_results(
    results: list[dict[str, Any]],
    show_content: bool = False,
    max_content_length: int = 200,
) -> Table:
    """Format memory search results as a Rich table.

    Args:
        results: List of search results from HybridRetriever
        show_content: Whether to show chunk content (default: False)
        max_content_length: Maximum length of content preview

    Returns:
        Rich Table object ready for display

    Example:
        >>> results = retriever.retrieve("calculate total", top_k=5)
        >>> table = format_memory_results(results, show_content=True)
        >>> console.print(table)
    """
    # Create table with columns
    table = Table(title="Memory Search Results", show_header=True, header_style="bold magenta")

    table.add_column("ID", style="cyan", no_wrap=True, width=8)
    table.add_column("Type", style="green", no_wrap=True, width=12)
    table.add_column("Name", style="yellow", width=25)
    table.add_column("Activation", justify="right", style="blue", no_wrap=True, width=10)
    table.add_column("Semantic", justify="right", style="blue", no_wrap=True, width=10)
    table.add_column("Score", justify="right", style="bold blue", no_wrap=True, width=10)
    table.add_column("File", style="dim", width=30)

    if show_content:
        table.add_column("Context", style="white", width=max_content_length)

    # Add rows
    for result in results:
        chunk_id = str(result["chunk_id"])[:8]  # Truncate ID for display
        chunk_type = result["metadata"].get("type", "unknown")
        chunk_name = result["metadata"].get("name", "<unnamed>")
        file_path = result["metadata"].get("file_path", "")

        # Scores
        activation_score = result["activation_score"]
        semantic_score = result["semantic_score"]
        hybrid_score = result["hybrid_score"]

        # Format scores with color gradient
        activation_text = _format_score(activation_score)
        semantic_text = _format_score(semantic_score)
        hybrid_text = _format_score(hybrid_score, bold=True)

        # Prepare row data
        row = [
            chunk_id,
            chunk_type,
            chunk_name[:25],  # Truncate long names
            activation_text,
            semantic_text,
            hybrid_text,
            _truncate_path(file_path, 30),
        ]

        if show_content:
            content = result.get("content", "")
            content_preview = _truncate_content(content, max_content_length)
            row.append(content_preview)

        table.add_row(*row)

    return table


def _format_score(score: float, bold: bool = False) -> Text:
    """Format score with color gradient (red → yellow → green).

    Args:
        score: Score value (0.0 - 1.0)
        bold: Whether to make text bold

    Returns:
        Rich Text object with colored score
    """
    # Color gradient based on score
    if score >= 0.7:
        color = "green"
    elif score >= 0.4:
        color = "yellow"
    else:
        color = "red"

    style = f"bold {color}" if bold else color
    return Text(f"{score:.3f}", style=style)


def _truncate_path(path: str, max_length: int) -> str:
    """Truncate file path for display.

    Args:
        path: Full file path
        max_length: Maximum length

    Returns:
        Truncated path with ellipsis if needed

    Example:
        >>> _truncate_path("/long/path/to/file.py", 15)
        "...to/file.py"
    """
    if len(path) <= max_length:
        return path

    # Try to keep filename and some parent directories
    path_obj = Path(path)
    filename = path_obj.name

    if len(filename) >= max_length:
        return f"...{filename[:max_length-3]}"

    # Keep as many parent dirs as possible
    remaining = max_length - len(filename) - 3  # 3 for "..."
    parent_parts = list(path_obj.parent.parts)

    # Build from end (closest to file)
    truncated_parent = ""
    for part in reversed(parent_parts):
        if len(truncated_parent) + len(part) + 1 <= remaining:
            truncated_parent = f"{part}/{truncated_parent}"
        else:
            break

    return f"...{truncated_parent}{filename}"


def _truncate_content(content: str, max_length: int) -> str:
    """Truncate content for preview.

    Args:
        content: Full content
        max_length: Maximum length

    Returns:
        Truncated content with ellipsis
    """
    if len(content) <= max_length:
        return content

    # Try to break at word boundary
    truncated = content[:max_length-3]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.8:  # If space is in last 20%
        truncated = truncated[:last_space]

    return f"{truncated}..."


@click.command(name="mem")
@click.argument("query", type=str)
@click.option(
    "--max-results",
    "-n",
    type=int,
    default=10,
    help="Maximum number of results to return (default: 10)",
)
@click.option(
    "--type",
    "-t",
    "chunk_type",
    type=str,
    default=None,
    help="Filter by chunk type (function, class, etc.)",
)
@click.option(
    "--min-activation",
    "-a",
    type=float,
    default=0.0,
    help="Minimum activation score threshold (0.0-1.0)",
)
@click.option(
    "--show-content",
    "-c",
    is_flag=True,
    default=False,
    help="Show content preview for each result",
)
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to AURORA database (default: ./aurora.db)",
)
def memory_command(
    query: str,
    max_results: int,
    chunk_type: str | None,
    min_activation: float,
    show_content: bool,
    db_path: Path | None,
) -> None:
    """Search AURORA memory for relevant chunks.

    QUERY is the text to search for in memory. It will use hybrid retrieval
    (activation + semantic similarity) to find the most relevant chunks.

    Examples:

        \b
        # Search for authentication-related code
        aur mem "authentication"

        \b
        # Search with type filter and show content
        aur mem "calculate total" --type function --show-content

        \b
        # Search with activation threshold
        aur mem "database" --min-activation 0.5 --max-results 20
    """
    try:
        # Determine database path
        if db_path is None:
            db_path = Path.cwd() / "aurora.db"

        if not db_path.exists():
            console.print(
                f"[bold red]Error:[/] Database not found at {db_path}\n"
                f"Please initialize AURORA first or specify --db-path",
                style="red"
            )
            raise click.Abort()

        # Initialize components
        console.print(f"[dim]Loading AURORA memory from {db_path}...[/]")

        store = SQLiteStore(str(db_path))
        activation_engine = ActivationEngine()  # ActivationEngine doesn't take store as argument
        embedding_provider = EmbeddingProvider()
        retriever = HybridRetriever(store, activation_engine, embedding_provider)

        # Extract keywords for logging
        keywords = extract_keywords(query)
        logger.info(f"Memory search: query='{query}', keywords={keywords}")

        # Perform retrieval
        console.print(f"[dim]Searching for: '{query}'...[/]")
        results = retriever.retrieve(query, top_k=max_results)

        # Filter by type if specified
        if chunk_type is not None:
            results = [
                r for r in results
                if r["metadata"].get("type") == chunk_type
            ]

        # Filter by minimum activation
        if min_activation > 0.0:
            results = [
                r for r in results
                if r["activation_score"] >= min_activation
            ]

        # Display results
        if not results:
            console.print("\n[yellow]No results found.[/]")
            console.print("Try:\n"
                        "  - Broadening your search query\n"
                        "  - Lowering --min-activation threshold\n"
                        "  - Removing --type filter")
            return

        console.print(f"\n[bold green]Found {len(results)} results[/]\n")

        # Format and display table
        table = format_memory_results(
            results,
            show_content=show_content,
            max_content_length=200
        )
        console.print(table)

        # Show summary statistics
        avg_activation = sum(r["activation_score"] for r in results) / len(results)
        avg_semantic = sum(r["semantic_score"] for r in results) / len(results)
        avg_hybrid = sum(r["hybrid_score"] for r in results) / len(results)

        console.print("\n[dim]Average scores:[/]")
        console.print(f"  Activation: {avg_activation:.3f}")
        console.print(f"  Semantic:   {avg_semantic:.3f}")
        console.print(f"  Hybrid:     {avg_hybrid:.3f}")

    except Exception as e:
        logger.error(f"Memory command failed: {e}", exc_info=True)
        console.print(f"\n[bold red]Error:[/] {e}", style="red")
        raise click.Abort()


if __name__ == "__main__":
    memory_command()
