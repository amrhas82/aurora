"""Monkey-patches for multilspy to fix TypeScript cross-file references.

Problems fixed:
1. TypeScript init params contain Rust-analyzer settings instead of TS config
2. No workspace file discovery — TS server never learns about other files
3. server_ready fires immediately with no indexing wait

Applied once at import via apply_patches().
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
from contextlib import asynccontextmanager
from typing import AsyncIterator

logger = logging.getLogger(__name__)

_PATCHED = False

# Extensions to discover per language
_TS_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}
_SKIP_DIRS = {"node_modules", "dist", "build", ".git", "vendor", "__pycache__", ".next", "coverage"}
_MAX_FILES = 500


def _discover_workspace_files(root: str, extensions: set[str]) -> list[str]:
    """Discover project files, skipping common vendor/build dirs."""
    root_path = pathlib.Path(root)
    files: list[str] = []

    for path in root_path.rglob("*"):
        if len(files) >= _MAX_FILES:
            break
        # Skip excluded directories
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in extensions and path.is_file():
            files.append(str(path))

    return files


def _make_ts_initialization_options() -> dict:
    """Return proper TypeScript initialization options."""
    return {
        "preferences": {
            "includeCompletionsForModuleExports": True,
            "includeCompletionsForImportStatements": True,
            "includeCompletionsWithSnippetText": False,
            "includeAutomaticOptionalChainCompletions": True,
        },
        "tsserver": {
            "logVerbosity": "off",
        },
    }


def _patch_ts_get_initialize_params() -> None:
    """Patch _get_initialize_params to use TS-specific initializationOptions."""
    try:
        from multilspy.language_servers.typescript_language_server.typescript_language_server import (
            TypeScriptLanguageServer,
        )
    except ImportError:
        return

    original = TypeScriptLanguageServer._get_initialize_params

    def patched_get_initialize_params(self, repository_absolute_path: str):
        params = original(self, repository_absolute_path)
        # Replace Rust-analyzer initializationOptions with TS config
        params["initializationOptions"] = _make_ts_initialization_options()
        return params

    TypeScriptLanguageServer._get_initialize_params = patched_get_initialize_params
    logger.debug("Patched TypeScriptLanguageServer._get_initialize_params")


def _patch_ts_start_server() -> None:
    """Patch start_server to discover workspace files and wait for indexing."""
    try:
        from multilspy.language_servers.typescript_language_server.typescript_language_server import (
            TypeScriptLanguageServer,
        )
    except ImportError:
        return

    original_start_server = TypeScriptLanguageServer.start_server

    @asynccontextmanager
    async def patched_start_server(self) -> AsyncIterator:
        async with original_start_server(self) as server:
            # Notify TS server about workspace files so it can resolve cross-file refs
            try:
                files = _discover_workspace_files(self.repository_root_path, _TS_EXTENSIONS)
                if files:
                    changes = []
                    for f in files:
                        uri = pathlib.Path(f).as_uri()
                        changes.append({"uri": uri, "type": 1})  # 1 = Created

                    self.server.notify.did_change_watched_files({"changes": changes})

                    # Wait for TS server to process file notifications
                    wait_time = min(1.0 + len(files) / 200, 3.0)
                    logger.debug(
                        f"TS workspace: notified {len(files)} files, "
                        f"waiting {wait_time:.1f}s for indexing"
                    )
                    await asyncio.sleep(wait_time)
            except Exception as e:
                logger.warning(f"TS workspace file discovery failed (non-fatal): {e}")

            yield server

    TypeScriptLanguageServer.start_server = patched_start_server
    logger.debug("Patched TypeScriptLanguageServer.start_server")


def apply_patches() -> None:
    """Apply all multilspy patches. Idempotent."""
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    _patch_ts_get_initialize_params()
    _patch_ts_start_server()
    logger.debug("multilspy patches applied")
