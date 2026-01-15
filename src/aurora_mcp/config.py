"""AURORA MCP Configuration and Logging.

This module provides logging configuration for MCP tools with performance metrics.
"""

import logging
import time
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any


def setup_mcp_logging(log_file: str = "~/.aurora/mcp.log") -> logging.Logger:
    """Setup MCP logging with performance metrics.

    Args:
        log_file: Path to log file (default: ~/.aurora/mcp.log)

    Returns:
        Configured logger instance
    """
    # Expand user path
    log_path = Path(log_file).expanduser()

    # Ensure directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger("aurora.mcp")
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    logger.handlers = []

    # File handler with custom format
    file_handler = logging.FileHandler(str(log_path))
    file_handler.setLevel(logging.INFO)

    # Custom format: [timestamp] level tool_name metric1=value1 metric2=value2
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


def log_performance(tool_name: str) -> Callable:
    """Decorator to log performance metrics for MCP tools.

    Args:
        tool_name: Name of the MCP tool being logged

    Returns:
        Decorator function

    Example:
        @log_performance("aurora_search")
        def aurora_search(query: str, limit: int = 10) -> str:
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get logger
            logger = logging.getLogger("aurora.mcp")

            # Record start time
            start_time = time.time()

            # Extract relevant parameters for logging
            params = []
            if args:
                # First arg is usually 'self', skip it
                if len(args) > 1:
                    params.append(f"arg={args[1]}")
            for key, value in kwargs.items():
                params.append(f"{key}={value}")

            param_str = " ".join(params) if params else "no_params"

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Log success
                logger.info(f"{tool_name} {param_str} latency={duration_ms:.1f}ms status=success")

                return result

            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Log error
                logger.error(
                    f"{tool_name} {param_str} latency={duration_ms:.1f}ms status=error error={str(e)}"
                )

                # Re-raise exception
                raise

        return wrapper

    return decorator
