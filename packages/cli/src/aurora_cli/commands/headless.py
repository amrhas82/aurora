"""Headless command - autonomous AI tool execution loop.

Supports single-tool and multi-tool concurrent execution modes with
configurable routing rules and tool-specific settings.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from aurora_cli.config import Config
from aurora_cli.templates.headless import SCRATCHPAD_TEMPLATE

console = Console()


def _parse_tools_callback(_ctx, _param, value):
    """Parse comma-separated tools or return tuple as-is."""
    if not value:
        return None
    # Flatten and split on comma
    result = []
    for item in value:
        if "," in item:
            result.extend(t.strip() for t in item.split(",") if t.strip())
        else:
            result.append(item.strip())
    return tuple(result) if result else None


def _parse_tool_flags_callback(_ctx, _param, value):
    """Parse tool:flags pairs into a dict.

    Format: --tool-flags "claude:--model opus" --tool-flags "opencode:--verbose"
    """
    if not value:
        return {}
    result = {}
    for item in value:
        if ":" in item:
            tool, flags = item.split(":", 1)
            result[tool.strip()] = flags.strip().split()
        else:
            # Apply to all tools if no prefix
            result["_all"] = item.strip().split()
    return result


def _parse_tool_env_callback(_ctx, _param, value):
    """Parse tool:KEY=VALUE pairs into a dict.

    Format: --tool-env "claude:ANTHROPIC_MODEL=opus" --tool-env "opencode:DEBUG=1"
    """
    if not value:
        return {}
    result = {}
    for item in value:
        if ":" in item:
            tool, env_pair = item.split(":", 1)
            tool = tool.strip()
            if tool not in result:
                result[tool] = {}
            if "=" in env_pair:
                key, val = env_pair.split("=", 1)
                result[tool][key.strip()] = val.strip()
    return result


# ============================================================================
# Extracted helper functions to reduce headless_command complexity (Task 6.0)
# ============================================================================


def _apply_config_defaults(
    config: "Config",
    tools: tuple[str, ...] | None,
    max_iter: int | None,
    strategy: str | None,
    parallel: bool | None,
    timeout: int | None,
    budget: float | None,
    time_limit: int | None,
) -> dict[str, Any]:
    """Apply config defaults to CLI arguments.

    Args:
        config: Config object with headless settings
        tools: CLI-provided tools tuple or None
        max_iter: CLI-provided max iterations or None
        strategy: CLI-provided strategy or None
        parallel: CLI-provided parallel flag or None
        timeout: CLI-provided timeout or None
        budget: CLI-provided budget or None
        time_limit: CLI-provided time limit or None

    Returns:
        Dict with resolved values for all settings
    """
    return {
        "tools_list": list(tools) if tools else config.headless_tools,
        "max_iter": max_iter if max_iter is not None else config.headless_max_iterations,
        "strategy": strategy if strategy is not None else config.headless_strategy,
        "parallel": parallel if parallel is not None else config.headless_parallel,
        "timeout": timeout if timeout is not None else config.headless_timeout,
        "budget": budget if budget is not None else config.headless_budget,
        "time_limit": time_limit if time_limit is not None else config.headless_time_limit,
        "tool_configs": config.headless_tool_configs,
        "routing_rules": config.headless_routing_rules,
    }


def _apply_cli_tool_overrides(
    tools_list: list[str],
    model: str | None,
    tool_flags: dict[str, list[str]],
    tool_env: dict[str, dict[str, str]],
    max_retries: int | None,
    retry_delay: float | None,
) -> dict[str, dict[str, Any]]:
    """Apply CLI-level per-tool configuration overrides.

    Args:
        tools_list: List of tool names
        model: Model to apply (for claude)
        tool_flags: Per-tool extra flags
        tool_env: Per-tool environment variables
        max_retries: Retry count to apply to all tools
        retry_delay: Retry delay to apply to all tools

    Returns:
        Dict mapping tool names to their override configurations
    """
    cli_tool_overrides: dict[str, dict[str, Any]] = {}

    # Handle --model flag (applies to claude)
    if model:
        for tool_name in tools_list:
            if tool_name not in cli_tool_overrides:
                cli_tool_overrides[tool_name] = {}
            if tool_name == "claude":
                cli_tool_overrides[tool_name]["extra_flags"] = ["--model", model]

    # Handle --tool-flags overrides
    if tool_flags:
        for tool_name, flags in tool_flags.items():
            if tool_name == "_all":
                for t in tools_list:
                    if t not in cli_tool_overrides:
                        cli_tool_overrides[t] = {}
                    cli_tool_overrides[t]["extra_flags"] = (
                        cli_tool_overrides[t].get("extra_flags", []) + flags
                    )
            elif tool_name in tools_list:
                if tool_name not in cli_tool_overrides:
                    cli_tool_overrides[tool_name] = {}
                cli_tool_overrides[tool_name]["extra_flags"] = (
                    cli_tool_overrides[tool_name].get("extra_flags", []) + flags
                )

    # Handle --tool-env overrides
    if tool_env:
        for tool_name, env_vars in tool_env.items():
            if tool_name in tools_list:
                if tool_name not in cli_tool_overrides:
                    cli_tool_overrides[tool_name] = {}
                cli_tool_overrides[tool_name]["env"] = env_vars

    # Handle retry settings
    if max_retries is not None or retry_delay is not None:
        for tool_name in tools_list:
            if tool_name not in cli_tool_overrides:
                cli_tool_overrides[tool_name] = {}
            if max_retries is not None:
                cli_tool_overrides[tool_name]["max_retries"] = max_retries
            if retry_delay is not None:
                cli_tool_overrides[tool_name]["retry_delay"] = retry_delay

    return cli_tool_overrides


def _validate_headless_params(
    max_retries: int | None,
    retry_delay: float | None,
    budget: float | None,
    time_limit: int | None,
    timeout: int | None,
) -> list[str]:
    """Validate headless command parameters.

    Args:
        max_retries: Max retry count
        retry_delay: Delay between retries
        budget: Budget limit
        time_limit: Time limit in seconds
        timeout: Per-iteration timeout

    Returns:
        List of error messages (empty if all valid)
    """
    errors = []
    if max_retries is not None and max_retries < 0:
        errors.append("--max-retries must be >= 0")
    if retry_delay is not None and retry_delay < 0:
        errors.append("--retry-delay must be >= 0")
    if budget is not None and budget <= 0:
        errors.append("--budget must be > 0")
    if time_limit is not None and time_limit <= 0:
        errors.append("--time-limit must be > 0")
    if timeout is not None and timeout <= 0:
        errors.append("--timeout must be > 0")
    return errors


def _resolve_prompt(
    use_stdin: bool,
    prompt_path: Path | None,
) -> tuple[str, str]:
    """Resolve prompt from stdin or file.

    Args:
        use_stdin: Whether to read from stdin
        prompt_path: Path to prompt file (used if not stdin)

    Returns:
        Tuple of (prompt_content, source_description)

    Raises:
        ValueError: If stdin is TTY or empty
        FileNotFoundError: If prompt file doesn't exist
    """
    import sys

    if use_stdin:
        if sys.stdin.isatty():
            raise ValueError("--stdin specified but no input piped")
        prompt = sys.stdin.read().strip()
        if not prompt:
            raise ValueError("Empty prompt from stdin")
        return prompt, "stdin"
    else:
        if prompt_path is None:
            prompt_path = Path.cwd() / ".aurora" / "headless" / "prompt.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8"), str(prompt_path)


def _check_tools_exist(tools_list: list[str]) -> list[str]:
    """Check that all tools exist in PATH.

    Args:
        tools_list: List of tool names to check

    Returns:
        List of missing tool names (empty if all exist)
    """
    return [t for t in tools_list if not shutil.which(t)]


def _check_git_safety(allow_main: bool) -> str | None:
    """Check git branch safety.

    Args:
        allow_main: Whether to allow main/master branches

    Returns:
        Error message if on protected branch, None if safe
    """
    if allow_main:
        return None

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        branch = result.stdout.strip()
        if branch in ["main", "master"]:
            return "Cannot run on main/master branch. Use --allow-main to override."
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass  # Not a git repo, continue
    return None


def _display_headless_config(
    tools_list: list[str],
    max_iter: int,
    is_multi_tool: bool,
    parallel: bool,
    strategy: str,
    model: str | None,
    prompt_source: str,
    scratchpad: Path,
    budget: float | None,
    time_limit: int | None,
    test_cmd: str | None,
    tool_flags: dict[str, list[str]],
) -> None:
    """Display headless execution configuration to console.

    Args:
        tools_list: List of tool names
        max_iter: Maximum iterations
        is_multi_tool: Whether multiple tools are configured
        parallel: Whether parallel execution is enabled
        strategy: Aggregation strategy
        model: Model override (if any)
        prompt_source: Source of the prompt (stdin or file path)
        scratchpad: Path to scratchpad file
        budget: Budget limit (if any)
        time_limit: Time limit in seconds (if any)
        test_cmd: Test backpressure command (if any)
        tool_flags: Per-tool flag overrides
    """
    tools_display = ", ".join(tools_list)
    mode_display = "parallel" if (is_multi_tool and parallel) else "sequential"
    console.print(f"[bold]Headless execution[/]: {tools_display} (max {max_iter} iterations)")
    if is_multi_tool:
        console.print(f"[dim]Mode: {mode_display}, Strategy: {strategy}[/]")
    if model:
        console.print(f"[dim]Model: {model}[/]")
    console.print(f"[dim]Prompt: {prompt_source}[/]")
    console.print(f"[dim]Scratchpad: {scratchpad}[/]")
    if budget is not None:
        console.print(f"[dim]Budget: ${budget:.2f}[/]")
    if time_limit is not None:
        console.print(f"[dim]Time limit: {time_limit}s[/]")
    if test_cmd:
        console.print(f"[dim]Backpressure: {test_cmd}[/]")
    if tool_flags:
        console.print(f"[dim]Tool flags: {tool_flags}[/]")
    console.print()


@click.command(name="headless")
@click.option(
    "-t",
    "--tool",
    "--tools",
    "tools",
    type=str,
    multiple=True,
    default=None,
    callback=_parse_tools_callback,
    help="CLI tool(s). Use: -t claude -t opencode OR --tools claude,opencode",
)
@click.option(
    "--max",
    "max_iter",
    type=int,
    default=None,
    help="Maximum iterations (default: from config or 10)",
)
@click.option(
    "-p",
    "--prompt",
    "prompt_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Prompt file (default: .aurora/headless/prompt.md)",
)
@click.option(
    "-i",
    "--stdin",
    "use_stdin",
    is_flag=True,
    default=False,
    help="Read prompt from stdin instead of file",
)
@click.option(
    "--test-cmd",
    type=str,
    default=None,
    help="Test command for backpressure (e.g., 'pytest tests/')",
)
@click.option(
    "--allow-main",
    is_flag=True,
    default=False,
    help="DANGEROUS: Allow running on main/master branch",
)
@click.option(
    "--strategy",
    type=click.Choice(
        [
            "first_success",
            "all_complete",
            "voting",
            "best_score",
            "merge",
            "smart_merge",
            "consensus",
        ],
    ),
    default=None,
    help="Multi-tool aggregation strategy (default: from config or first_success)",
)
@click.option(
    "--parallel/--sequential",
    "parallel",
    default=None,
    help="Run multiple tools in parallel (default) or sequentially",
)
@click.option(
    "--timeout",
    type=int,
    default=None,
    help="Per-tool timeout in seconds (default: from config or 600)",
)
@click.option(
    "--budget",
    type=float,
    default=None,
    help="Budget limit in USD (stops when exceeded, default: unlimited)",
)
@click.option(
    "--time-limit",
    type=int,
    default=None,
    help="Time limit in seconds (stops when exceeded, default: unlimited)",
)
@click.option(
    "--tool-flags",
    multiple=True,
    callback=_parse_tool_flags_callback,
    help="Per-tool flags. Format: 'tool:flags' (e.g., 'claude:--model opus-4')",
)
@click.option(
    "--tool-env",
    multiple=True,
    callback=_parse_tool_env_callback,
    help="Per-tool env vars. Format: 'tool:KEY=VALUE' (e.g., 'claude:ANTHROPIC_MODEL=opus')",
)
@click.option(
    "--model",
    type=str,
    default=None,
    help="Model to use (for tools that support it, e.g., claude --model opus-4)",
)
@click.option(
    "--max-retries",
    type=int,
    default=None,
    help="Max retry attempts per tool on failure (default: 2)",
)
@click.option(
    "--retry-delay",
    type=float,
    default=None,
    help="Delay between retries in seconds (default: 1.0)",
)
@click.option(
    "--output-format",
    type=click.Choice(["text", "json", "quiet"]),
    default="text",
    help="Output format: text (default), json (structured), quiet (minimal)",
)
@click.option(
    "--show-config",
    is_flag=True,
    default=False,
    help="Show effective configuration and exit",
)
@click.option(
    "--list-tools",
    is_flag=True,
    default=False,
    help="List available tool providers and exit",
)
def headless_command(
    tools: tuple[str, ...] | None,
    max_iter: int | None,
    prompt_path: Path | None,
    use_stdin: bool,
    test_cmd: str | None,
    allow_main: bool,
    strategy: str | None,
    parallel: bool | None,
    timeout: int | None,
    budget: float | None,
    time_limit: int | None,
    tool_flags: dict[str, list[str]],
    tool_env: dict[str, dict[str, str]],
    model: str | None,
    max_retries: int | None,
    retry_delay: float | None,
    output_format: str,
    show_config: bool,
    list_tools: bool,
) -> None:
    r"""Autonomous AI tool execution loop with multi-tool support.

    Reads a prompt file, executes AI tools in a loop, and manages
    state via a scratchpad file. Exits early when STATUS: DONE is set.

    Supports running multiple tools concurrently with result aggregation.

    \b
    Examples:
        # Single tool (default)
        aur headless -t claude --max=10

        # Multiple tools in parallel
        aur headless -t claude -t opencode --max=10

        # Read prompt from stdin
        echo "Fix all lint errors" | aur headless -t claude --stdin

        # Specify model for Claude
        aur headless -t claude --model opus-4 --max=10

        # Per-tool flags override
        aur headless -t claude -t opencode --tool-flags "claude:--model opus-4"

        # Per-tool environment variables
        aur headless -t claude --tool-env "claude:ANTHROPIC_MODEL=opus-4"

        # Multiple tools with voting (requires 3+)
        aur headless -t claude -t opencode -t cursor --strategy voting

        # Sequential multi-tool (round-robin)
        aur headless -t claude -t opencode --sequential

        # Custom prompt file
        aur headless -p my-task.md -t claude --max=20

        # With test backpressure
        aur headless --test-cmd "pytest tests/" --max=15

        # JSON output for scripting
        aur headless -t claude --output-format json --max=5

        # Custom retry settings
        aur headless -t claude --max-retries 3 --retry-delay 2.0

    \b
    Aggregation Strategies:
        first_success - Return first successful result, cancel others
        all_complete  - Wait for all tools, return best result
        voting        - Consensus from 3+ tools (majority wins)
        best_score    - Score results by success, output length, speed
        merge         - Combine outputs from all tools
        smart_merge   - Intelligent merge with conflict detection (preserves unique content)
        consensus     - Require agreement; reports conflicts if tools disagree
    """
    # Handle --list-tools early (before config loading)
    if list_tools:
        _list_available_tools()
        return

    # Load config and apply defaults
    config = Config()
    defaults = _apply_config_defaults(
        config=config,
        tools=tools,
        max_iter=max_iter,
        strategy=strategy,
        parallel=parallel,
        timeout=timeout,
        budget=budget,
        time_limit=time_limit,
    )
    tools_list = defaults["tools_list"]
    max_iter = defaults["max_iter"]
    strategy = defaults["strategy"]
    parallel = defaults["parallel"]
    timeout = defaults["timeout"]
    budget = defaults["budget"]
    time_limit = defaults["time_limit"]
    tool_configs = defaults["tool_configs"]
    routing_rules = defaults["routing_rules"]

    # Load tool configurations from config into the registry
    from aurora_cli.tool_providers import ToolProviderRegistry

    registry = ToolProviderRegistry.get_instance()
    if config.headless_tool_configs:
        registry.load_from_config(config.headless_tool_configs)

    # Apply CLI-level per-tool configurations
    cli_tool_overrides = _apply_cli_tool_overrides(
        tools_list=tools_list,
        model=model,
        tool_flags=tool_flags,
        tool_env=tool_env,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )

    # Validate parameters
    quiet_mode = output_format == "quiet"
    json_mode = output_format == "json"
    validation_errors = _validate_headless_params(
        max_retries=max_retries,
        retry_delay=retry_delay,
        budget=budget,
        time_limit=time_limit,
        timeout=timeout,
    )
    if validation_errors:
        if not quiet_mode:
            for error in validation_errors:
                console.print(f"[red]Error: {error}[/]")
        raise click.Abort()

    # Apply CLI overrides to registry
    for tool_name, overrides in cli_tool_overrides.items():
        existing_config = tool_configs.get(tool_name, {}).copy()
        existing_config.update(overrides)
        registry.configure(tool_name, existing_config)

    is_multi_tool = len(tools_list) > 1

    # Handle --show-config
    if show_config:
        _show_effective_config(
            tools_list=tools_list,
            strategy=strategy,
            parallel=parallel,
            max_iter=max_iter,
            timeout=timeout,
            budget=budget,
            time_limit=time_limit,
            tool_configs=tool_configs,
            routing_rules=routing_rules,
            test_cmd=test_cmd,
            model=model,
            tool_flags=tool_flags,
            tool_env=tool_env,
            max_retries=max_retries,
            retry_delay=retry_delay,
            output_format=output_format,
        )
        return

    # Resolve prompt from stdin or file
    try:
        prompt, prompt_source = _resolve_prompt(use_stdin=use_stdin, prompt_path=prompt_path)
    except ValueError as e:
        if not quiet_mode:
            console.print(f"[red]Error: {e}[/]")
            if "stdin" in str(e).lower():
                console.print("[dim]Usage: echo 'your prompt' | aur headless --stdin[/]")
        raise click.Abort()
    except FileNotFoundError as e:
        if not quiet_mode:
            console.print(f"[red]Error: {e}[/]")
            console.print("[dim]Create a prompt file with your goal, or use -p to specify one.[/]")
        raise click.Abort()

    # Check all tools exist
    missing_tools = _check_tools_exist(tools_list)
    if missing_tools:
        if not quiet_mode:
            console.print(f"[red]Error: Tools not found in PATH: {', '.join(missing_tools)}[/]")
        raise click.Abort()

    # Git safety check
    git_error = _check_git_safety(allow_main=allow_main)
    if git_error:
        if not quiet_mode:
            console.print(f"[red]Error: {git_error}[/]")
        raise click.Abort()

    # Initialize scratchpad
    scratchpad = Path.cwd() / ".aurora" / "headless" / "scratchpad.md"
    scratchpad.parent.mkdir(parents=True, exist_ok=True)
    if not scratchpad.exists():
        scratchpad.write_text(SCRATCHPAD_TEMPLATE, encoding="utf-8")

    # Display configuration (unless quiet/json mode)
    if not quiet_mode and not json_mode:
        _display_headless_config(
            tools_list=tools_list,
            max_iter=max_iter,
            is_multi_tool=is_multi_tool,
            parallel=parallel,
            strategy=strategy,
            model=model,
            prompt_source=prompt_source,
            scratchpad=scratchpad,
            budget=budget,
            time_limit=time_limit,
            test_cmd=test_cmd,
            tool_flags=tool_flags,
        )

    # Main execution loop
    if is_multi_tool and parallel:
        # Multi-tool concurrent execution
        asyncio.run(
            _run_multi_tool_loop(
                tools_list=tools_list,
                prompt=prompt,
                scratchpad=scratchpad,
                max_iter=max_iter,
                test_cmd=test_cmd,
                strategy=strategy,
                timeout=timeout,
                budget=budget,
                time_limit=time_limit,
                output_format=output_format,
            ),
        )
    else:
        # Single-tool or sequential multi-tool execution
        _run_single_tool_loop(
            tools_list=tools_list,
            prompt=prompt,
            scratchpad=scratchpad,
            max_iter=max_iter,
            test_cmd=test_cmd,
            sequential_multi=is_multi_tool and not parallel,
            timeout=timeout,
            budget=budget,
            time_limit=time_limit,
            output_format=output_format,
        )


def _run_single_tool_loop(
    tools_list: list[str],
    prompt: str,
    scratchpad: Path,
    max_iter: int,
    test_cmd: str | None,
    sequential_multi: bool = False,
    timeout: int = 600,
    budget: float | None = None,
    time_limit: int | None = None,
    output_format: str = "text",
) -> None:
    """Run execution loop with single tool or sequential multi-tool.

    Uses ToolProviderRegistry when available for proper command building.
    Stops early if budget or time_limit is exceeded.
    """
    import json as json_module
    import time as time_module

    from aurora_cli.tool_providers import ToolProviderRegistry

    registry = ToolProviderRegistry.get_instance()
    tool_index = 0
    total_cost = 0.0
    start_time = time_module.time()
    quiet_mode = output_format == "quiet"
    json_mode = output_format == "json"
    json_results: list[dict[str, Any]] = []

    for i in range(1, max_iter + 1):
        # Check time limit
        if time_limit is not None:
            elapsed = time_module.time() - start_time
            if elapsed >= time_limit:
                if not quiet_mode and not json_mode:
                    console.print(f"\n[yellow]Time limit reached ({time_limit}s)[/]")
                    console.print(f"[dim]Elapsed: {elapsed:.1f}s, Iterations completed: {i - 1}[/]")
                _check_final_state(scratchpad, output_format)
                if json_mode:
                    print(
                        json_module.dumps(
                            {"status": "time_limit", "iterations": i - 1, "results": json_results},
                        ),
                    )
                return

        # Check budget (placeholder - actual cost tracking would need tool integration)
        if budget is not None and total_cost >= budget:
            if not quiet_mode and not json_mode:
                console.print(f"\n[yellow]Budget limit reached (${budget:.2f})[/]")
                console.print(
                    f"[dim]Total cost: ${total_cost:.2f}, Iterations completed: {i - 1}[/]",
                )
            _check_final_state(scratchpad, output_format)
            if json_mode:
                print(
                    json_module.dumps(
                        {"status": "budget_limit", "iterations": i - 1, "results": json_results},
                    ),
                )
            return

        # Read current scratchpad state
        scratchpad_content = scratchpad.read_text(encoding="utf-8")

        # Check for early exit BEFORE running
        if "STATUS: DONE" in scratchpad_content:
            if not quiet_mode and not json_mode:
                console.print(f"\n[bold green]Goal achieved![/] (iteration {i - 1})")
                console.print(f"[dim]See: {scratchpad}[/]")
            if json_mode:
                print(
                    json_module.dumps(
                        {"status": "done", "iterations": i - 1, "results": json_results},
                    ),
                )
            return

        # Select tool (round-robin for sequential multi-tool)
        if sequential_multi:
            tool_name = tools_list[tool_index % len(tools_list)]
            tool_index += 1
            if not quiet_mode and not json_mode:
                console.print(f"[{i}/{max_iter}] Running iteration with [cyan]{tool_name}[/]...")
        else:
            tool_name = tools_list[0]
            if not quiet_mode and not json_mode:
                console.print(f"[{i}/{max_iter}] Running iteration...")

        # Build context
        context = f"{prompt}\n\n## Current Scratchpad State:\n{scratchpad_content}"

        # Try to use registered tool provider
        provider = registry.get(tool_name)
        iteration_result: dict[str, Any] = {"iteration": i, "tool": tool_name}
        if provider and provider.is_available():
            # Use retry-enabled execution
            result = provider.execute_with_retry(context, working_dir=Path.cwd(), timeout=timeout)
            iteration_result["success"] = result.success
            iteration_result["duration"] = result.duration_seconds
            if result.metadata.get("retry_attempts"):
                iteration_result["retry_attempts"] = result.metadata["retry_attempts"]
            if not result.success:
                if not quiet_mode and not json_mode:
                    console.print(
                        f"[yellow]Warning: {tool_name} exited with code {result.return_code}[/]",
                    )
                    if result.metadata.get("retry_attempts"):
                        console.print(
                            f"[dim]After {result.metadata['retry_attempts']} retry attempts[/]",
                        )
                    if result.stderr:
                        console.print(f"[dim]{result.stderr[:500]}[/]")
                iteration_result["error"] = result.stderr[:500] if result.stderr else None
        else:
            # Fallback to direct subprocess execution
            try:
                if tool_name == "claude":
                    proc_result = subprocess.run(
                        [tool_name, "--print", "--dangerously-skip-permissions", context],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                else:
                    proc_result = subprocess.run(
                        [tool_name],
                        input=context,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )

                iteration_result["success"] = proc_result.returncode == 0
                if proc_result.returncode != 0:
                    if not quiet_mode and not json_mode:
                        console.print(
                            f"[yellow]Warning: {tool_name} exited with code {proc_result.returncode}[/]",
                        )
                        if proc_result.stderr:
                            console.print(f"[dim]{proc_result.stderr[:500]}[/]")
                    iteration_result["error"] = (
                        proc_result.stderr[:500] if proc_result.stderr else None
                    )
            except subprocess.TimeoutExpired:
                if not quiet_mode and not json_mode:
                    console.print(f"[red]Error: {tool_name} timed out after {timeout}s[/]")
                iteration_result["success"] = False
                iteration_result["error"] = f"Timeout after {timeout}s"
                raise click.Abort()

        json_results.append(iteration_result)

        # Optional backpressure
        if test_cmd:
            _run_backpressure(test_cmd, output_format)

        if not quiet_mode and not json_mode:
            console.print(f"[green]Iteration {i} complete[/]")

    # Check final state
    _check_final_state(scratchpad, output_format)
    if json_mode:
        print(
            json_module.dumps(
                {"status": "max_iterations", "iterations": max_iter, "results": json_results},
            ),
        )


async def _run_multi_tool_loop(
    tools_list: list[str],
    prompt: str,
    scratchpad: Path,
    max_iter: int,
    test_cmd: str | None,
    strategy: str,
    timeout: int = 600,
    budget: float | None = None,
    time_limit: int | None = None,
    output_format: str = "text",
) -> None:
    """Run execution loop with multiple tools in parallel.

    Stops early if budget or time_limit is exceeded.
    """
    import json as json_module
    import time as time_module

    from aurora_cli.concurrent_executor import AggregationStrategy, ConcurrentToolExecutor

    strategy_enum = AggregationStrategy(strategy)
    executor = ConcurrentToolExecutor(
        tools_list,
        strategy=strategy_enum,
        timeout=float(timeout),
        track_file_changes=True,
        working_dir=Path.cwd(),
    )
    total_cost = 0.0
    start_time = time_module.time()
    quiet_mode = output_format == "quiet"
    json_mode = output_format == "json"
    json_results: list[dict[str, Any]] = []

    for i in range(1, max_iter + 1):
        # Check time limit
        if time_limit is not None:
            elapsed = time_module.time() - start_time
            if elapsed >= time_limit:
                if not quiet_mode and not json_mode:
                    console.print(f"\n[yellow]Time limit reached ({time_limit}s)[/]")
                    console.print(f"[dim]Elapsed: {elapsed:.1f}s, Iterations completed: {i - 1}[/]")
                _check_final_state(scratchpad, output_format)
                if json_mode:
                    print(
                        json_module.dumps(
                            {"status": "time_limit", "iterations": i - 1, "results": json_results},
                        ),
                    )
                return

        # Check budget (placeholder - actual cost tracking would need tool integration)
        if budget is not None and total_cost >= budget:
            if not quiet_mode and not json_mode:
                console.print(f"\n[yellow]Budget limit reached (${budget:.2f})[/]")
                console.print(
                    f"[dim]Total cost: ${total_cost:.2f}, Iterations completed: {i - 1}[/]",
                )
            _check_final_state(scratchpad, output_format)
            if json_mode:
                print(
                    json_module.dumps(
                        {"status": "budget_limit", "iterations": i - 1, "results": json_results},
                    ),
                )
            return

        # Read current scratchpad state
        scratchpad_content = scratchpad.read_text(encoding="utf-8")

        # Check for early exit BEFORE running
        if "STATUS: DONE" in scratchpad_content:
            if not quiet_mode and not json_mode:
                console.print(f"\n[bold green]Goal achieved![/] (iteration {i - 1})")
                console.print(f"[dim]See: {scratchpad}[/]")
            if json_mode:
                print(
                    json_module.dumps(
                        {"status": "done", "iterations": i - 1, "results": json_results},
                    ),
                )
            return

        if not quiet_mode and not json_mode:
            console.print(f"[{i}/{max_iter}] Running parallel execution...")

        # Build context
        context = f"{prompt}\n\n## Current Scratchpad State:\n{scratchpad_content}"

        # Execute all tools in parallel
        result = await executor.execute(context)

        # Display results
        if not quiet_mode and not json_mode:
            _display_multi_tool_results(result, strategy)

        # Store result for JSON output
        if json_mode:
            json_results.append({"iteration": i, "result": _result_to_dict(result)})

        # Optional backpressure
        if test_cmd:
            _run_backpressure(test_cmd, output_format)

        if not quiet_mode and not json_mode:
            console.print(f"[green]Iteration {i} complete[/]")

    # Check final state
    _check_final_state(scratchpad, output_format)
    if json_mode:
        print(
            json_module.dumps(
                {"status": "max_iterations", "iterations": max_iter, "results": json_results},
            ),
        )


def _display_multi_tool_results(result, strategy: str) -> None:
    """Display multi-tool execution results."""
    from aurora_cli.concurrent_executor import AggregatedResult, ConflictSeverity

    if not isinstance(result, AggregatedResult):
        return

    # Create summary table
    table = Table(title=f"Results ({strategy})", show_header=True)
    table.add_column("Tool", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Time", style="yellow")
    table.add_column("Output", style="dim")

    for tr in result.tool_results:
        status = "[green]OK[/]" if tr.success else "[red]FAIL[/]"
        time_str = f"{tr.execution_time:.1f}s"
        output_preview = tr.output[:50] + "..." if len(tr.output) > 50 else tr.output
        output_preview = output_preview.replace("\n", " ")
        table.add_row(tr.tool, status, time_str, output_preview)

    console.print(table)

    if result.winning_tool:
        console.print(f"[cyan]Winner:[/] {result.winning_tool}")

    if "scores" in result.metadata:
        scores_str = ", ".join(f"{k}: {v:.1f}" for k, v in result.metadata["scores"].items())
        console.print(f"[dim]Scores: {scores_str}[/]")

    # Display conflict information if available
    if result.conflict_info:
        ci = result.conflict_info
        severity_colors = {
            ConflictSeverity.NONE: "green",
            ConflictSeverity.FORMATTING: "dim",
            ConflictSeverity.MINOR: "yellow",
            ConflictSeverity.MODERATE: "yellow bold",
            ConflictSeverity.MAJOR: "red bold",
        }
        color = severity_colors.get(ci.severity, "white")
        console.print(f"[{color}]Conflict: {ci.severity.value}[/] - {ci.description}")
        console.print(f"[dim]Similarity: {ci.similarity_score:.1%}[/]")

        if ci.severity in (ConflictSeverity.MODERATE, ConflictSeverity.MAJOR):
            console.print(
                "[yellow]Review recommended: Tools produced significantly different outputs[/]",
            )
            if ci.conflicting_sections:
                for section in ci.conflicting_sections:
                    console.print(
                        f"[dim]  - {section.get('type', 'unknown')}: "
                        f"{section.get('tool1')} vs {section.get('tool2')}[/]",
                    )

    # Display consensus-specific metadata
    if "consensus_reached" in result.metadata:
        if result.metadata["consensus_reached"]:
            console.print("[green]Consensus reached[/]")
        else:
            console.print(
                f"[yellow]No consensus (threshold: {result.metadata.get('threshold', 0.8):.0%})[/]",
            )
            console.print(
                f"[dim]Resolution: {result.metadata.get('resolution_method', 'fallback')}[/]",
            )

    # Display file change information if available
    if result.file_changes:
        _display_file_changes(result.file_changes)


def _display_file_changes(file_result) -> None:
    """Display file change aggregation results."""
    from aurora_cli.file_change_aggregator import ConflictType

    if not file_result.files_changed:
        return

    console.print()
    console.print("[bold]File Changes[/]")

    # Files changed table
    file_table = Table(show_header=True)
    file_table.add_column("File", style="cyan")
    file_table.add_column("Status", style="green")

    for path in file_result.files_changed[:10]:  # Limit display
        rel_path = path.name if len(str(path)) > 50 else str(path)
        # Check if file has conflict
        conflict = next((c for c in file_result.conflicts if c.path == path), None)
        if conflict and conflict.conflict_type != ConflictType.NONE:
            status = f"[yellow]{conflict.conflict_type.value}[/]"
        else:
            status = "[green]merged[/]"
        file_table.add_row(rel_path, status)

    if len(file_result.files_changed) > 10:
        file_table.add_row(f"... and {len(file_result.files_changed) - 10} more", "")

    console.print(file_table)

    # Display conflicts
    if file_result.has_conflicts:
        unresolved = file_result.unresolved_conflicts
        resolved = len(file_result.conflicts) - len(unresolved)

        if unresolved:
            console.print(f"[red bold]File Conflicts: {len(unresolved)} unresolved[/]")
            for conflict in unresolved[:3]:
                console.print(f"  [red]! {conflict.path}[/]: {conflict.description}")
            console.print("[yellow]Manual review required for unresolved conflicts[/]")
        else:
            console.print(f"[green]All {resolved} file conflicts resolved automatically[/]")


def _run_backpressure(test_cmd: str, output_format: str = "text") -> None:
    """Run backpressure test command."""
    quiet_mode = output_format == "quiet"
    json_mode = output_format == "json"

    if not quiet_mode and not json_mode:
        console.print(f"[dim]Running tests: {test_cmd}[/]")

    test_result = subprocess.run(
        test_cmd,
        shell=True,  # nosec B602 - user-provided test command
        capture_output=True,
        text=True,
        timeout=300,
    )
    if test_result.returncode != 0:
        if not quiet_mode and not json_mode:
            console.print("[yellow]Tests failed, tools will see this next iteration[/]")
    else:
        if not quiet_mode and not json_mode:
            console.print("[green]Tests passed[/]")


def _check_final_state(scratchpad: Path, output_format: str = "text") -> None:
    """Check and report final scratchpad state."""
    quiet_mode = output_format == "quiet"
    json_mode = output_format == "json"

    if quiet_mode or json_mode:
        return  # JSON output handles this in the main loop

    final_scratchpad = scratchpad.read_text(encoding="utf-8")
    if "STATUS: DONE" in final_scratchpad:
        console.print("\n[bold green]Goal achieved![/]")
    else:
        console.print("\n[yellow]Max iterations reached without STATUS: DONE[/]")
    console.print(f"[dim]See: {scratchpad}[/]")


def _result_to_dict(result) -> dict[str, Any]:
    """Convert an AggregatedResult to a JSON-serializable dict."""
    from aurora_cli.concurrent_executor import AggregatedResult

    if not isinstance(result, AggregatedResult):
        return {"error": "Unknown result type"}

    return {
        "winning_tool": result.winning_tool,
        "final_output": result.final_output[:1000] if result.final_output else None,  # Truncate
        "tool_results": [
            {
                "tool": tr.tool,
                "success": tr.success,
                "execution_time": tr.execution_time,
                "output_preview": tr.output[:200] if tr.output else None,
            }
            for tr in result.tool_results
        ],
        "metadata": result.metadata,
    }


def _list_available_tools() -> None:
    """Display available tool providers from the registry."""
    from aurora_cli.tool_providers import ToolProviderRegistry

    registry = ToolProviderRegistry.get_instance()

    console.print("[bold]Available Tool Providers[/]\n")

    registered = registry.list_available()
    installed = registry.list_installed()

    table = Table(show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Display Name")
    table.add_column("Input Method", style="dim")
    table.add_column("Priority", style="yellow")
    table.add_column("Status")

    # Sort by priority
    providers_info = []
    for name in registered:
        provider = registry.get(name)
        if provider:
            providers_info.append((name, provider))

    providers_info.sort(key=lambda x: x[1].priority)

    for name, provider in providers_info:
        status = "[green]installed[/]" if name in installed else "[red]not found[/]"
        table.add_row(
            name,
            provider.display_name,
            provider.input_method.value,
            str(provider.priority),
            status,
        )

    console.print(table)
    console.print()
    console.print("[bold]Usage Examples:[/]")
    console.print("  aur headless -t claude -t opencode     # Run both tools in parallel")
    console.print("  aur headless -t claude --sequential    # Run sequentially (round-robin)")
    console.print("  aur headless --strategy voting -t a -t b -t c  # Consensus from 3+ tools")
    console.print()
    console.print("[bold]Adding Custom Tools:[/]")
    console.print("  1. Via config file (headless.tool_configs):")
    console.print('     {"mytool": {"executable": "mytool", "input_method": "stdin"}}')
    console.print("  2. Programmatically: registry.register_from_config('mytool', {...})")
    console.print("  3. Create a provider class extending ToolProvider")


def _show_effective_config(
    tools_list: list[str],
    strategy: str,
    parallel: bool,
    max_iter: int,
    timeout: int,
    budget: float | None,
    time_limit: int | None,
    tool_configs: dict[str, Any],
    routing_rules: list[dict[str, Any]],
    test_cmd: str | None = None,
    model: str | None = None,
    tool_flags: dict[str, list[str]] | None = None,
    tool_env: dict[str, dict[str, str]] | None = None,
    max_retries: int | None = None,
    retry_delay: float | None = None,
    output_format: str = "text",
) -> None:
    """Display effective headless configuration."""
    console.print("[bold]Effective Headless Configuration[/]")
    console.print()

    # Basic settings
    settings_table = Table(title="General Settings", show_header=True, header_style="bold cyan")
    settings_table.add_column("Setting", style="cyan")
    settings_table.add_column("Value", style="green")

    settings_table.add_row("Tools", ", ".join(tools_list))
    settings_table.add_row("Strategy", strategy)
    settings_table.add_row("Mode", "parallel" if parallel else "sequential")
    settings_table.add_row("Max Iterations", str(max_iter))
    settings_table.add_row("Timeout", f"{timeout}s")
    settings_table.add_row("Budget", f"${budget:.2f}" if budget is not None else "(unlimited)")
    settings_table.add_row(
        "Time Limit",
        f"{time_limit}s" if time_limit is not None else "(unlimited)",
    )
    settings_table.add_row("Test Command", test_cmd or "(none)")
    settings_table.add_row("Model", model or "(default)")
    settings_table.add_row(
        "Max Retries",
        str(max_retries) if max_retries is not None else "(default: 2)",
    )
    settings_table.add_row(
        "Retry Delay",
        f"{retry_delay}s" if retry_delay is not None else "(default: 1.0)",
    )
    settings_table.add_row("Output Format", output_format)

    console.print(settings_table)
    console.print()

    # CLI tool overrides
    if tool_flags or tool_env:
        override_table = Table(
            title="CLI Tool Overrides",
            show_header=True,
            header_style="bold cyan",
        )
        override_table.add_column("Tool", style="cyan")
        override_table.add_column("Extra Flags", style="green")
        override_table.add_column("Env Vars", style="yellow")

        all_tools = set(tool_flags.keys() if tool_flags else []) | set(
            tool_env.keys() if tool_env else [],
        )
        for tool_name in sorted(all_tools):
            flags = " ".join(tool_flags.get(tool_name, [])) if tool_flags else ""
            env_vars = ", ".join(
                f"{k}={v}" for k, v in (tool_env.get(tool_name, {}) if tool_env else {}).items()
            )
            override_table.add_row(tool_name, flags or "(none)", env_vars or "(none)")

        console.print(override_table)
        console.print()

    # Tool-specific configs
    if tool_configs:
        tool_table = Table(title="Tool Configurations", show_header=True, header_style="bold cyan")
        tool_table.add_column("Tool", style="cyan")
        tool_table.add_column("Priority", style="yellow")
        tool_table.add_column("Timeout", style="green")
        tool_table.add_column("Input Method", style="magenta")
        tool_table.add_column("Flags", style="dim")

        for tool_name, tc in tool_configs.items():
            priority = str(tc.get("priority", "-"))
            tool_timeout = str(tc.get("timeout", "-"))
            input_method = tc.get("input_method", "-")
            flags = " ".join(tc.get("flags", [])) or "(none)"
            tool_table.add_row(tool_name, priority, tool_timeout, input_method, flags)

        console.print(tool_table)
        console.print()

    # Routing rules
    if routing_rules:
        rules_table = Table(title="Routing Rules", show_header=True, header_style="bold cyan")
        rules_table.add_column("#", style="dim")
        rules_table.add_column("Pattern/Condition", style="cyan")
        rules_table.add_column("Tools", style="green")

        for i, rule in enumerate(routing_rules, 1):
            pattern = rule.get("pattern") or rule.get("condition", "-")
            rule_tools = ", ".join(rule.get("tools", []))
            rules_table.add_row(str(i), pattern, rule_tools)

        console.print(rules_table)
        console.print()
    else:
        console.print("[dim]No routing rules configured[/]")
        console.print()

    # Environment variables reminder
    console.print("[bold]Environment Variable Overrides:[/]")
    console.print("  AURORA_HEADLESS_TOOLS           - Comma-separated tools")
    console.print("  AURORA_HEADLESS_STRATEGY        - Aggregation strategy")
    console.print("  AURORA_HEADLESS_PARALLEL        - true/false")
    console.print("  AURORA_HEADLESS_MAX_ITERATIONS  - Max iterations")
    console.print("  AURORA_HEADLESS_TIMEOUT         - Per-tool timeout (seconds)")
    console.print("  AURORA_HEADLESS_BUDGET          - Budget limit in USD")
    console.print("  AURORA_HEADLESS_TIME_LIMIT      - Time limit in seconds")
