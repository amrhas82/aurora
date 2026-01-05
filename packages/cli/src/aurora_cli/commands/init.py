"""Init command for AURORA CLI setup."""

import asyncio
import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import click
from rich.console import Console

from aurora_cli.commands.init_helpers import (
    configure_mcp_servers,
    configure_slash_commands,
    configure_tools,
    create_agents_md,
    create_directory_structure,
    create_headless_templates,
    create_project_md,
    detect_configured_tools,
    detect_git_repository,
    get_mcp_capable_from_selection,
    prompt_git_init,
    prompt_tool_selection,
)
from aurora_cli.config import CONFIG_SCHEMA
from aurora_cli.configurators.slash import SlashCommandRegistry
from aurora_cli.errors import ErrorHandler, handle_errors


console = Console()


def get_all_tool_ids() -> list[str]:
    """Get list of all valid tool IDs from the slash command registry.

    Returns:
        List of all 20 tool IDs (e.g., ['amazon-q', 'claude', 'cursor', ...])
    """
    return [c.tool_id for c in SlashCommandRegistry.get_all()]


def parse_tools_flag(tools_str: str) -> list[str]:
    """Parse --tools flag value into list of tool IDs.

    Args:
        tools_str: Value from --tools flag (e.g., 'all', 'none', 'claude,cursor')

    Returns:
        List of tool IDs to configure

    Examples:
        >>> parse_tools_flag('all')
        ['amazon-q', 'antigravity', 'auggie', ...]  # all 20 tools
        >>> parse_tools_flag('none')
        []
        >>> parse_tools_flag('claude,cursor')
        ['claude', 'cursor']
    """
    if not tools_str or tools_str.strip() == "":
        return []

    normalized = tools_str.strip().lower()

    if normalized == "all":
        return get_all_tool_ids()

    if normalized == "none":
        return []

    # Split by comma, strip whitespace, lowercase, and remove duplicates while preserving order
    tool_ids = []
    seen = set()
    for tool_id in normalized.split(","):
        tool_id = tool_id.strip()
        if tool_id and tool_id not in seen:
            tool_ids.append(tool_id)
            seen.add(tool_id)

    return tool_ids


def validate_tool_ids(tool_ids: list[str]) -> None:
    """Validate that all tool IDs are valid.

    Args:
        tool_ids: List of tool IDs to validate

    Raises:
        ValueError: If any tool ID is invalid, with message listing invalid IDs
                   and available tool IDs
    """
    if not tool_ids:
        return

    valid_ids = set(get_all_tool_ids())
    invalid_ids = [tid for tid in tool_ids if tid not in valid_ids]

    if invalid_ids:
        available = ", ".join(sorted(valid_ids))
        invalid_str = ", ".join(invalid_ids)
        raise ValueError(
            f"Invalid tool ID(s): {invalid_str}. "
            f"Available tools: {available}"
        )


def run_step_2_memory_indexing(project_path: Path) -> bool:
    """Run Step 2: Memory Indexing.

    This step:
    1. Determines project-specific db_path (.aurora/memory.db)
    2. Prompts to re-index if memory.db already exists
    3. Creates backup before re-indexing
    4. Initializes MemoryManager with project-specific config
    5. Indexes project files with progress bar
    6. Displays success statistics

    Args:
        project_path: Path to project root directory

    Returns:
        True if indexing succeeded, False if skipped or failed

    Note:
        This function is idempotent - safe to run multiple times.
        Creates backup before re-indexing to preserve existing data.
    """
    import logging

    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

    from aurora_cli.config import Config
    from aurora_cli.memory_manager import MemoryManager

    console.print("\n[bold]Step 2/3: Memory Indexing[/]")
    console.print("[dim]Indexing codebase for semantic search...[/]\n")

    # Determine project-specific db_path
    db_path = project_path / ".aurora" / "memory.db"

    # Check if database already exists
    if db_path.exists():
        if not click.confirm(
            f"Memory database exists at {db_path}. Re-index codebase?",
            default=True
        ):
            console.print("[yellow]⚠[/] Skipping memory indexing")
            return False

        # Create backup before re-indexing
        backup_path = db_path.with_suffix(".db.backup")
        try:
            shutil.copy(db_path, backup_path)
            console.print(f"[green]✓[/] Created backup at {backup_path}")
        except Exception as e:
            console.print(f"[red]✗[/] Failed to create backup: {e}")
            console.print("[yellow]⚠[/] Continuing without backup...")

    # Create Config with project-specific db_path
    try:
        config = Config(db_path=str(db_path))

        # Create MemoryManager with custom config
        manager = MemoryManager(config=config)

        # Suppress parse warnings during indexing for cleaner output
        # Warnings are still counted in stats via WarningDetector, just not displayed to console
        parser_logger = logging.getLogger("aurora_context_code.languages.python")
        root_logger = logging.getLogger()

        # Remove all console/stream handlers temporarily from both parser and root loggers
        parser_original_handlers = parser_logger.handlers[:]
        root_original_handlers = root_logger.handlers[:]

        for handler in parser_original_handlers:
            if isinstance(handler, logging.StreamHandler):
                parser_logger.removeHandler(handler)

        for handler in root_original_handlers:
            if isinstance(handler, logging.StreamHandler):
                root_logger.removeHandler(handler)

        try:
            # Create progress bar with time remaining estimate
            from rich.progress import TimeRemainingColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                TextColumn("{task.completed}/{task.total} files"),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task_id = None

                def progress_callback(current: int, total: int) -> None:
                    nonlocal task_id
                    if task_id is None:
                        task_id = progress.add_task("Indexing files", total=total)
                    progress.update(task_id, completed=current)

                # Perform indexing
                stats = manager.index_path(project_path, progress_callback=progress_callback)
        finally:
            # Restore original handlers for both loggers
            for handler in parser_original_handlers:
                if handler not in parser_logger.handlers:
                    parser_logger.addHandler(handler)

            for handler in root_original_handlers:
                if handler not in root_logger.handlers:
                    root_logger.addHandler(handler)

        # Show success summary
        console.print()
        console.print("[bold green]Memory Indexing Complete[/]")

        if stats.files_indexed > 0:
            console.print(f"  [green]✓[/] Files indexed:  {stats.files_indexed}")
            console.print(f"  [green]✓[/] Chunks created: {stats.chunks_created}")
            console.print(f"  [dim]⏱[/] Duration:       {stats.duration_seconds:.2f}s")

            # Display error/warning summary table
            if stats.errors > 0 or stats.warnings > 0:
                console.print()
                console.print("[bold]Indexing Issues Summary:[/]")
                console.print("┌─────────────┬───────┬────────────────────────────────────────┐")
                console.print("│ Issue Type  │ Count │ What To Do                             │")
                console.print("├─────────────┼───────┼────────────────────────────────────────┤")

                if stats.errors > 0:
                    console.print(
                        f"│ [yellow]Errors[/]      │ {stats.errors:5} │ Files that failed to parse             │"
                    )
                    console.print(
                        "│             │       │ → May be corrupted or binary files     │"
                    )
                    console.print(
                        "│             │       │ → Action: Check with aur mem stats     │"
                    )

                if stats.warnings > 0:
                    if stats.errors > 0:
                        console.print("├─────────────┼───────┼────────────────────────────────────────┤")
                    console.print(
                        f"│ [yellow]Warnings[/]    │ {stats.warnings:5} │ Files with syntax/parse errors         │"
                    )
                    console.print(
                        "│             │       │ → Partial indexing succeeded           │"
                    )
                    console.print(
                        "│             │       │ → Action: Check logs with --verbose    │"
                    )

                console.print("└─────────────┴───────┴────────────────────────────────────────┘")

            return True
        else:
            console.print("  [yellow]⚠[/] No files found to index")
            return False

    except Exception as e:
        console.print(f"[red]✗[/] Indexing failed: {e}")

        # Prompt user for action
        if click.confirm("Skip this step and continue?", default=False):
            console.print("[yellow]⚠[/] Skipping memory indexing")
            return False
        else:
            console.print("[red]Aborting initialization[/]")
            raise SystemExit(1)


def run_step_1_planning_setup(project_path: Path) -> bool:
    """Run Step 1: Planning Setup (Git + Directories).

    This step:
    1. Detects if git repository exists
    2. Prompts to initialize git if missing (with benefits explanation)
    3. Creates Aurora directory structure (.aurora/plans, logs, cache)
    4. Creates project.md with auto-detected metadata

    Args:
        project_path: Path to project root directory

    Returns:
        True if git repository exists or was initialized, False if user declined

    Note:
        This function is idempotent - safe to run multiple times.
        Preserves existing project.md if already present.
    """
    console.print("\n[bold]Step 1/3: Planning Setup[/]")
    console.print("[dim]Setting up git and Aurora directory structure...[/]\n")

    git_initialized = False

    # Check for git repository
    if detect_git_repository(project_path):
        console.print("[green]✓[/] Git repository detected")
        git_initialized = True
    else:
        # Prompt user to initialize git
        if prompt_git_init():
            # Run git init
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=project_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                console.print("[green]✓[/] Git repository initialized")
                git_initialized = True
            except subprocess.CalledProcessError as e:
                console.print(f"[red]✗[/] Failed to initialize git: {e}")
                console.print("[yellow]⚠[/] Continuing without git...")
            except FileNotFoundError:
                console.print("[red]✗[/] Git command not found")
                console.print("[yellow]⚠[/] Continuing without git...")
        else:
            console.print("[yellow]⚠[/] Skipping git initialization")
            console.print("[dim]Planning directories will not be created.[/]")

    # Create Aurora directory structure
    create_directory_structure(project_path)
    console.print("[green]✓[/] Created Aurora directory structure:")
    console.print("  • .aurora/plans/active")
    console.print("  • .aurora/plans/archive")
    console.print("  • .aurora/logs")
    console.print("  • .aurora/cache")

    # Create project.md with auto-detected metadata
    aurora_dir = project_path / ".aurora"
    project_md = aurora_dir / "project.md"

    if project_md.exists():
        console.print("[green]✓[/] project.md already exists (preserved)")
    else:
        create_project_md(project_path)
        console.print("[green]✓[/] Created project.md with auto-detected metadata")

    # Create AGENTS.md with Aurora instructions
    agents_md = aurora_dir / "AGENTS.md"

    if agents_md.exists():
        console.print("[green]✓[/] AGENTS.md already exists (preserved)")
    else:
        create_agents_md(project_path)
        console.print("[green]✓[/] Created AGENTS.md with Aurora instructions")

    # Create headless mode templates
    headless_dir = aurora_dir / "headless"
    headless_readme = headless_dir / "README.md"
    headless_template = headless_dir / "prompt.md.template"

    if headless_readme.exists() and headless_template.exists():
        console.print("[green]✓[/] Headless templates already exist (preserved)")
    else:
        create_headless_templates(project_path)
        console.print("[green]✓[/] Created headless mode templates")

    console.print()
    return git_initialized


def run_step_3_tool_configuration(
    project_path: Path,
    tool_ids: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Run Step 3: Tool Configuration.

    This step:
    1. Detects existing tool configurations
    2. Prompts user to select tools (interactive checkbox) OR uses provided tool_ids
    3. Configures selected tools using Phase 1 configurator system
    4. Configures MCP servers for tools that support MCP (Claude, Cursor, Cline, Continue)
    5. Tracks created vs updated tools
    6. Displays success message

    Args:
        project_path: Path to project root directory
        tool_ids: Optional list of tool IDs to configure (bypasses interactive prompt)

    Returns:
        Tuple of (created_tools, updated_tools) - lists of tool names

    Note:
        This function is idempotent - safe to run multiple times.
        Uses marker-based updates to preserve custom content.
    """
    console.print("\n[bold]Step 3/3: Tool Configuration[/]")
    console.print("[dim]Configure AI coding tools with Aurora integration...[/]\n")

    # Use provided tool_ids or prompt user for selection
    if tool_ids is not None:
        # Non-interactive mode: use provided tool IDs
        selected_tool_ids = tool_ids
        if tool_ids:
            console.print(f"[dim]Using specified tools: {', '.join(tool_ids)}[/]")
        else:
            console.print("[yellow]⚠[/] No tools specified (--tools=none)")
            return ([], [])
    else:
        # Interactive mode: prompt user for selection
        # Detect existing tool configurations
        configured_tools = detect_configured_tools(project_path)

        # Prompt user for tool selection
        selected_tool_ids = asyncio.run(
            prompt_tool_selection(configured_tools=configured_tools)
        )

    if not selected_tool_ids:
        console.print("[yellow]⚠[/] No tools selected")
        return ([], [])

    # Configure root config files (e.g., CLAUDE.md, AGENTS.md stubs)
    console.print("\n[dim]Configuring tool instruction files...[/]")
    config_created, config_updated = asyncio.run(
        configure_tools(project_path, selected_tool_ids)
    )

    # Configure selected tools using slash command configurators
    console.print("[dim]Configuring slash commands...[/]")
    created, updated = asyncio.run(
        configure_slash_commands(project_path, selected_tool_ids)
    )

    # Merge config file results with slash command results
    created = list(set(created + config_created))
    updated = list(set(updated + config_updated))

    # Configure MCP servers for tools that support MCP
    mcp_capable = get_mcp_capable_from_selection(selected_tool_ids)
    mcp_created: list[str] = []
    mcp_updated: list[str] = []
    validation_warnings: list[str] = []

    if mcp_capable:
        console.print("[dim]Configuring MCP servers...[/]")
        mcp_created, mcp_updated, _skipped, validation_warnings = asyncio.run(
            configure_mcp_servers(project_path, mcp_capable)
        )

    # Show success message
    console.print()

    # Display slash command results
    if created:
        console.print("[green]✓[/] Created slash commands:")
        for tool_name in created:
            # Check if this tool also got MCP config
            mcp_note = ""
            if tool_name in mcp_created:
                mcp_note = " [dim](+ MCP server)[/]"
            elif tool_name in mcp_updated:
                mcp_note = " [dim](+ MCP updated)[/]"
            console.print(f"  [cyan]▌[/] {tool_name}{mcp_note}")

    if updated:
        console.print("[green]✓[/] Updated slash commands:")
        for tool_name in updated:
            mcp_note = ""
            if tool_name in mcp_created:
                mcp_note = " [dim](+ MCP server)[/]"
            elif tool_name in mcp_updated:
                mcp_note = " [dim](+ MCP updated)[/]"
            console.print(f"  [dim cyan]▌ {tool_name}{mcp_note}[/]")

    # Display MCP-only results (tools that got MCP but weren't in slash command results)
    mcp_only_created = [t for t in mcp_created if t not in created and t not in updated]
    mcp_only_updated = [t for t in mcp_updated if t not in created and t not in updated]

    if mcp_only_created or mcp_only_updated:
        console.print("[green]✓[/] Configured MCP servers:")
        for tool_name in mcp_only_created:
            console.print(f"  [cyan]▌[/] {tool_name} [dim](MCP server created)[/]")
        for tool_name in mcp_only_updated:
            console.print(f"  [dim cyan]▌ {tool_name} (MCP server updated)[/]")

    total = len(created) + len(updated)
    mcp_total = len(mcp_created) + len(mcp_updated)
    if total > 0:
        mcp_note = f" ({mcp_total} with MCP)" if mcp_total > 0 else ""
        console.print(f"\n[bold green]✓[/] Configured {total} tool{'s' if total != 1 else ''}{mcp_note}")

    # Display MCP validation warnings if any
    if validation_warnings:
        console.print()
        console.print("[yellow]⚠ MCP configuration warnings:[/]")
        for warning in validation_warnings:
            console.print(f"  [yellow]•[/] {warning}")
        console.print()
        console.print("[dim]Run 'aur doctor' for detailed MCP health checks and auto-fix options.[/]")

    console.print()
    return (created, updated)


def check_and_handle_schema_mismatch(db_path: Path, error_handler: ErrorHandler) -> bool:
    """Check for schema mismatch and handle it interactively.

    This function checks if an existing database has an incompatible schema
    and offers the user options to backup and reset.

    Args:
        db_path: Path to the database file
        error_handler: ErrorHandler instance for formatting messages

    Returns:
        True if database is ready to use, False if user aborted

    Note:
        This function handles SchemaMismatchError gracefully by prompting
        the user for action rather than displaying a traceback.
    """
    from aurora_core.exceptions import SchemaMismatchError
    from aurora_core.store.sqlite import SQLiteStore, backup_database

    if not db_path.exists():
        # No existing database - nothing to check
        return True

    # Try to open the database and check schema
    try:
        # Create a temporary store to check schema
        store = SQLiteStore(db_path=str(db_path))
        store.close()
        return True
    except SchemaMismatchError as e:
        # Schema mismatch detected - handle interactively
        click.echo("\n[Schema Migration Required]")
        click.echo(f"  Database: {db_path}")
        click.echo(f"  Found version: v{e.found_version}")
        click.echo(f"  Required version: v{e.expected_version}")
        click.echo("")
        click.echo("Your database was created with an older version of AURORA.")
        click.echo("It needs to be reset to use the new schema.")
        click.echo("")

        # Ask if user wants to proceed
        if not click.confirm(
            "Reset database and re-index? (your data will need to be re-indexed)", default=True
        ):
            click.echo("Aborted. Database unchanged.")
            click.echo("Note: You can manually backup and delete the database file to reset.")
            return False

        # Ask about backup
        if click.confirm("Create backup before reset?", default=True):
            try:
                backup_path = backup_database(str(db_path))
                click.echo(f"  Backup created: {backup_path}")
            except Exception as backup_error:
                error_msg = error_handler.handle_memory_error(backup_error, "creating backup")
                click.echo(f"\n{error_msg}", err=True)
                if not click.confirm("Continue without backup?", default=False):
                    click.echo("Aborted.")
                    return False

        # Perform reset
        try:
            # Delete the old database
            db_path.unlink()

            # Also remove WAL and SHM files if they exist
            wal_file = Path(f"{db_path}-wal")
            shm_file = Path(f"{db_path}-shm")
            if wal_file.exists():
                wal_file.unlink()
            if shm_file.exists():
                shm_file.unlink()

            click.echo("  Database reset successfully.")
            click.echo("  Run 'aur mem index .' to re-index your codebase.")
            return True
        except OSError as reset_error:
            error_msg = error_handler.handle_memory_error(reset_error, "resetting database")
            click.echo(f"\n{error_msg}", err=True)
            return False
    except Exception:
        # Other errors - let them propagate
        raise


def detect_local_db() -> Path | None:
    """Detect if there's a local aurora.db file in the current directory.

    Returns:
        Path to local aurora.db if found, None otherwise
    """
    local_db = Path.cwd() / "aurora.db"
    if local_db.exists() and local_db.is_file():
        return local_db
    return None


def migrate_database(src: Path, dst: Path) -> tuple[int, int]:
    """Migrate data from source database to destination database.

    Uses SQLite ATTACH to copy chunks and activations tables.

    Args:
        src: Source database path
        dst: Destination database path

    Returns:
        Tuple of (chunks_migrated, activations_migrated)

    Raises:
        sqlite3.Error: If migration fails
    """
    # Ensure destination parent directory exists
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Connect to destination database (creates if doesn't exist)
    conn = sqlite3.connect(str(dst))
    cursor = conn.cursor()

    try:
        # Attach source database
        cursor.execute(f"ATTACH DATABASE '{src}' AS source")

        # Get table names from source
        cursor.execute("SELECT name FROM source.sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        chunks_migrated = 0
        activations_migrated = 0

        # Copy chunks table if exists
        if "chunks" in tables:
            # Create chunks table in destination if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_start INTEGER NOT NULL,
                    line_end INTEGER NOT NULL,
                    metadata TEXT,
                    created_at REAL NOT NULL
                )
            """)

            # Copy data
            cursor.execute("""
                INSERT OR REPLACE INTO chunks
                SELECT * FROM source.chunks
            """)
            chunks_migrated = cursor.rowcount

        # Copy activations table if exists
        if "activations" in tables:
            # Create activations table in destination if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activations (
                    chunk_id TEXT PRIMARY KEY,
                    base_level REAL NOT NULL DEFAULT 0.0,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    last_access_time REAL,
                    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
                )
            """)

            # Copy data
            cursor.execute("""
                INSERT OR REPLACE INTO activations
                SELECT * FROM source.activations
            """)
            activations_migrated = cursor.rowcount

        # Copy embeddings table if exists
        if "embeddings" in tables:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    chunk_id TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    model TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
                )
            """)

            cursor.execute("""
                INSERT OR REPLACE INTO embeddings
                SELECT * FROM source.embeddings
            """)

        # Detach source database
        cursor.execute("DETACH DATABASE source")

        # Commit changes
        conn.commit()

        return chunks_migrated, activations_migrated

    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


@click.command(name="init")
@click.option(
    "--config",
    is_flag=True,
    default=False,
    help="Configure tools only (skip planning setup and memory indexing)",
)
@click.option(
    "--tools",
    type=str,
    default=None,
    help="Specify tools to configure: 'all', 'none', or comma-separated list (e.g., 'claude,cursor,gemini')",
)
@handle_errors
def init_command(config: bool, tools: str | None) -> None:
    """Initialize AURORA in current project (unified 3-step flow).

    This command sets up Aurora for your project with:
      1. Planning Setup - Git initialization and directory structure
      2. Memory Indexing - Semantic search database for codebase
      3. Tool Configuration - AI tool integrations (Claude Code, etc.)

    \b
    Examples:
        # Full initialization (all 3 steps)
        aur init

        \b
        # Configure tools only (Step 3)
        aur init --config

        \b
        # Configure specific tools (non-interactive)
        aur init --tools=claude,cursor,gemini

        \b
        # Configure all tools
        aur init --tools=all

        \b
        # Skip tool configuration
        aur init --tools=none

        \b
        # After initialization
        aur plan create "Add user authentication"
        aur mem search "database connection"
    """
    from aurora_cli.commands.init_helpers import detect_existing_setup

    project_path = Path.cwd()

    # Parse and validate --tools flag if provided
    parsed_tool_ids: list[str] | None = None
    if tools is not None:
        parsed_tool_ids = parse_tools_flag(tools)
        try:
            validate_tool_ids(parsed_tool_ids)
        except ValueError as e:
            console.print(f"[red]Error:[/] {e}")
            raise SystemExit(1)

    # Handle --config flag: fast path for tool configuration only
    if config:
        # Check if .aurora exists
        if not detect_existing_setup(project_path):
            console.print("[red]Error:[/] Project not initialized")
            console.print("Run [cyan]aur init[/] first to set up project structure")
            raise SystemExit(1)

        # Run Step 3 only
        console.print("[bold]AURORA Tool Configuration[/]")
        console.print()
        run_step_3_tool_configuration(project_path, tool_ids=parsed_tool_ids)
        console.print("[bold green]✓[/] Tool configuration complete\n")
        return

    # Check for existing setup
    if detect_existing_setup(project_path):
        from aurora_cli.commands.init_helpers import (
            prompt_rerun_options,
            selective_step_selection,
            show_status_summary,
        )

        # Show current status
        show_status_summary(project_path)

        # Prompt for re-run options
        rerun_choice = prompt_rerun_options()

        if rerun_choice == "exit":
            console.print("[dim]Exiting without changes.[/]")
            return

        if rerun_choice == "config":
            # Run Step 3 only
            console.print()
            console.print("[bold]AURORA Tool Configuration[/]")
            console.print()
            run_step_3_tool_configuration(project_path, tool_ids=parsed_tool_ids)
            console.print("[bold green]✓[/] Tool configuration complete\n")
            return

        # Determine which steps to run
        if rerun_choice == "all":
            steps_to_run = [1, 2, 3]
        elif rerun_choice == "selective":
            steps_to_run = selective_step_selection()
            if not steps_to_run:
                console.print("[dim]No steps selected. Exiting.[/]")
                return
        else:
            # Should not reach here, but handle gracefully
            console.print("[yellow]Invalid choice. Exiting.[/]")
            return

        # Display banner for re-run
        console.print()
        console.print("[bold cyan]╔═══════════════════════════════════════════╗[/]")
        console.print("[bold cyan]║[/]        [bold]AURORA Re-initialization[/]        [bold cyan]║[/]")
        console.print("[bold cyan]╚═══════════════════════════════════════════╝[/]")
        console.print()
        console.print(f"[dim]Re-running steps: {steps_to_run}[/]")
        console.print()

        # Run selected steps
        git_initialized = False
        indexing_succeeded = False
        created_tools = []
        updated_tools = []

        if 1 in steps_to_run:
            git_initialized = run_step_1_planning_setup(project_path)
        else:
            console.print("[dim]⊘ Skipping Step 1: Planning Setup[/]")

        if 2 in steps_to_run:
            indexing_succeeded = run_step_2_memory_indexing(project_path)
        else:
            console.print("[dim]⊘ Skipping Step 2: Memory Indexing[/]")

        if 3 in steps_to_run:
            created_tools, updated_tools = run_step_3_tool_configuration(
                project_path, tool_ids=parsed_tool_ids
            )
        else:
            console.print("[dim]⊘ Skipping Step 3: Tool Configuration[/]")

        # Display success summary
        console.print()
        console.print("[bold green]═══════════════════════════════════════════[/]")
        console.print("[bold green]✓ AURORA Re-initialization Complete[/]")
        console.print("[bold green]═══════════════════════════════════════════[/]")
        console.print()

        console.print("[bold]Updated Steps:[/]")
        if 1 in steps_to_run:
            if git_initialized:
                console.print("  [green]✓[/] Git repository initialized")
            console.print("  [green]✓[/] Planning directories created")
        if 2 in steps_to_run:
            if indexing_succeeded:
                console.print("  [green]✓[/] Codebase re-indexed")
            else:
                console.print("  [yellow]⚠[/] Memory indexing skipped")
        if 3 in steps_to_run:
            total_tools = len(created_tools) + len(updated_tools)
            if total_tools > 0:
                console.print(f"  [green]✓[/] {total_tools} tool{'s' if total_tools != 1 else ''} configured")

        console.print()
        console.print("[dim]Tip: Run [cyan]aur --help[/] to see all available commands[/]")
        console.print()
        return

    # Display welcome banner
    console.print()
    console.print("[bold cyan]AURORA Initialization[/]")
    console.print("[bold cyan]═════════════════════[/]")
    console.print()
    console.print("[dim]Setting up Aurora for your project...[/]")
    console.print()

    # Run 3-step initialization flow
    # Step 1: Planning Setup (Git + Directories)
    git_initialized = run_step_1_planning_setup(project_path)

    # Step 2: Memory Indexing
    indexing_succeeded = run_step_2_memory_indexing(project_path)

    # Step 3: Tool Configuration
    created_tools, updated_tools = run_step_3_tool_configuration(
        project_path, tool_ids=parsed_tool_ids
    )

    # Display success summary
    console.print()
    console.print("[bold green]═══════════════════════════════════════════[/]")
    console.print("[bold green]✓ AURORA Initialization Complete[/]")
    console.print("[bold green]═══════════════════════════════════════════[/]")
    console.print()

    console.print("[bold]Setup Summary:[/]")
    if git_initialized:
        console.print("  [green]✓[/] Git repository initialized")
    console.print("  [green]✓[/] Planning directories created")
    if indexing_succeeded:
        console.print("  [green]✓[/] Codebase indexed for semantic search")
    else:
        console.print("  [yellow]⚠[/] Memory indexing skipped")

    total_tools = len(created_tools) + len(updated_tools)
    if total_tools > 0:
        console.print(f"  [green]✓[/] {total_tools} tool{'s' if total_tools != 1 else ''} configured")

    console.print()
    console.print("[bold]Next Steps:[/]")
    console.print("  1. [cyan]aur plan create \"Your feature\"[/] - Create a plan")
    console.print("  2. [cyan]aur mem search \"keyword\"[/] - Search your codebase")
    console.print("  3. [cyan]aur agents list[/] - Discover available agents")
    console.print()
    console.print("[dim]Tip: Run [cyan]aur --help[/] to see all available commands[/]")
    console.print()
