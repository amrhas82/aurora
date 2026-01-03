"""Init command for AURORA CLI setup."""

import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import click
from rich.console import Console

from aurora_cli.commands.init_helpers import (
    create_directory_structure,
    create_project_md,
    detect_git_repository,
    prompt_git_init,
)
from aurora_cli.config import CONFIG_SCHEMA
from aurora_cli.errors import ErrorHandler, handle_errors


console = Console()


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

    console.print()
    return git_initialized


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
    "--interactive",
    is_flag=True,
    default=False,
    help="Run interactive setup wizard with guided prompts",
)
@handle_errors
def init_command(interactive: bool) -> None:
    """Initialize AURORA configuration.

    Creates ~/.aurora/config.json with defaults and optional API key.
    Optionally indexes the current directory for memory search.

    \b
    Examples:
        # Basic initialization (will prompt for API key)
        aur init

        \b
        # Interactive setup wizard (guided experience)
        aur init --interactive

        \b
        # After initialization, set API key in environment
        export ANTHROPIC_API_KEY=sk-ant-...
        aur query "your question"
    """
    # If interactive flag is set, run the wizard
    if interactive:
        from aurora_cli.wizard import InteractiveWizard

        wizard = InteractiveWizard()
        wizard.run()
        return
    from aurora_cli.config import _get_aurora_home

    config_dir = _get_aurora_home()
    config_path = config_dir / "config.json"

    # Check if config already exists
    if config_path.exists():
        overwrite = click.confirm(
            f"Config file already exists at {config_path}. Overwrite?", default=False
        )
        if not overwrite:
            click.echo("Keeping existing config.")
            return

    # Prompt for API key
    api_key = click.prompt(
        "Enter Anthropic API key (or press Enter to skip)",
        default="",
        show_default=False,
    )

    # Validate API key format if provided
    if api_key and not api_key.startswith("sk-ant-"):
        click.echo(
            "⚠ Warning: API key should start with 'sk-ant-'. This may not be a valid Anthropic API key."
        )
        if not click.confirm("Continue anyway?", default=True):
            click.echo("Aborted.")
            return

    # Create config directory
    error_handler = ErrorHandler()
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        error_msg = error_handler.handle_path_error(e, str(config_dir), "creating config directory")
        click.echo(error_msg, err=True)
        return
    except Exception as e:
        error_msg = error_handler.handle_path_error(e, str(config_dir), "creating config directory")
        click.echo(error_msg, err=True)
        return

    # Prepare config data
    config_data = CONFIG_SCHEMA.copy()

    # Set database path to respect AURORA_HOME
    config_data["database"]["path"] = str(config_dir / "memory.db")

    # Set API key if provided (non-empty)
    if api_key and api_key.strip():
        config_data["llm"]["anthropic_api_key"] = api_key.strip()
    else:
        # Ensure API key is None if empty
        config_data["llm"]["anthropic_api_key"] = None

    # Write config file
    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
    except PermissionError as e:
        error_msg = error_handler.handle_path_error(e, str(config_path), "writing config file")
        click.echo(error_msg, err=True)
        return
    except Exception as e:
        error_msg = error_handler.handle_config_error(e, str(config_path))
        click.echo(error_msg, err=True)
        return

    # Set secure file permissions (user read/write only)
    try:
        os.chmod(config_path, 0o600)
    except Exception as e:
        click.echo(f"⚠ Warning: Could not set secure permissions on {config_path}: {e}")

    click.echo(f"Configuration created at {config_path}")

    # Check for schema migration issues with main database
    main_db_path = config_dir / "memory.db"
    if not check_and_handle_schema_mismatch(main_db_path, error_handler):
        # User aborted schema migration - exit early
        return

    # Check for local aurora.db and offer migration
    local_db = detect_local_db()
    if local_db is not None:
        from aurora_cli.config import load_config

        config = load_config()
        dest_db = Path(config.get_db_path())

        click.echo(f"\n⚠ Found local database at {local_db}")
        if click.confirm(f"Migrate data to {dest_db}?", default=True):
            try:
                chunks, activations = migrate_database(local_db, dest_db)
                click.echo("✓ Migration complete:")
                click.echo(f"  - Chunks migrated: {chunks}")
                click.echo(f"  - Activations migrated: {activations}")

                # Rename old database to backup
                backup_path = local_db.with_suffix(".db.backup")
                shutil.move(str(local_db), str(backup_path))
                click.echo(f"  - Original database backed up to: {backup_path}")
            except sqlite3.Error as e:
                error_msg = error_handler.handle_memory_error(e, "migrating database")
                click.echo(f"\n{error_msg}", err=True)
                click.echo("⚠ Migration failed, keeping original database")
            except Exception as e:
                click.echo(f"⚠ Migration failed: {e}", err=True)
                click.echo("Keeping original database")
        else:
            click.echo("Skipping migration. Local database will remain.")

    # Prompt to index current directory
    if click.confirm("Index current directory for memory search?", default=True):
        # Import memory indexing functionality
        try:
            from rich.console import Console
            from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

            from aurora_cli.config import load_config
            from aurora_cli.memory_manager import MemoryManager

            console = Console()
            console.print("[bold]Indexing current directory...[/]")

            # Load config and initialize memory manager
            config = load_config()
            manager = MemoryManager(config=config)

            # Create progress display
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                task_id = None

                def progress_callback(current: int, total: int) -> None:
                    nonlocal task_id
                    if task_id is None:
                        task_id = progress.add_task("Indexing files", total=total)
                    progress.update(task_id, completed=current)

                # Perform indexing
                stats = manager.index_path(Path.cwd(), progress_callback=progress_callback)

            if stats.files_indexed > 0:
                console.print(
                    f"[bold green]✓[/] Indexed {stats.files_indexed} files, "
                    f"{stats.chunks_created} chunks in {stats.duration_seconds:.2f}s"
                )
            else:
                console.print("[yellow]⚠[/] No Python files found to index in current directory")

        except ImportError:
            # Memory command not yet implemented - stub for Phase 3
            click.echo("⚠ Memory indexing not yet implemented (Phase 4)")

    # Display summary with rich formatting
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    console.print("\n[bold green]✓ AURORA CLI initialized successfully![/]\n")

    # Configuration summary
    console.print("[bold]Configuration:[/]")
    console.print(f"  • Config file: [cyan]{config_path}[/]")
    console.print(f"  • Database: [cyan]{config_data['database']['path']}[/]")
    if api_key:
        console.print("  • API key: [green]✓ Configured[/]")
    else:
        console.print("  • API key: [yellow]⚠ Not configured[/]")

    # Next steps panel
    next_steps = []
    if not api_key:
        next_steps.append(
            "[yellow]1. Set API key:[/]\n   [cyan]export ANTHROPIC_API_KEY=sk-ant-...[/]"
        )

    next_steps.extend(
        [
            "[bold]2. Verify your installation:[/]\n   [cyan]aur doctor[/]",
            "[bold]3. Check version info:[/]\n   [cyan]aur version[/]",
            "[bold]4. Start querying:[/]\n   [cyan]aur query 'your question'[/]",
        ]
    )

    console.print(Panel("\n\n".join(next_steps), title="[bold]Next Steps[/]", border_style="green"))

    console.print("\n[dim]For help with any command, use [cyan]aur <command> --help[/][/]\n")
