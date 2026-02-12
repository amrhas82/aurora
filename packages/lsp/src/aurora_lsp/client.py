"""Low-level multilspy wrapper for Aurora.

Manages language server instances and provides async LSP operations.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# Import multilspy components
try:
    from multilspy.language_server import LanguageServer
    from multilspy.multilspy_config import Language, MultilspyConfig
    from multilspy.multilspy_logger import MultilspyLogger

    MULTILSPY_AVAILABLE = True
except ImportError:
    MULTILSPY_AVAILABLE = False
    Language = None  # type: ignore
    LanguageServer = None  # type: ignore


class AuroraLSPClient:
    """Low-level multilspy wrapper.

    Manages language server instances per language, lazily initialized.
    Provides async methods for common LSP operations.

    Must be used within the server context:

        client = AuroraLSPClient(workspace)
        async with client.start():
            refs = await client.request_references(file, line, col)
    """

    # Map file extensions to Language enum values
    LANGUAGE_MAP: dict[str, Any] = {}

    def __init__(self, workspace: Path | str):
        """Initialize LSP client for a workspace.

        Args:
            workspace: Root directory of the project to analyze.
        """
        self.workspace = Path(workspace).resolve()
        self._servers: dict[str, Any] = {}  # Language -> server
        self._contexts: dict[str, Any] = {}  # Language -> context manager
        self._open_files: set[str] = set()  # Tracks opened files
        self._lock = asyncio.Lock()
        self._logger: Any = None
        self._started = False

        # Initialize language map if multilspy is available
        if MULTILSPY_AVAILABLE and Language is not None:
            self.LANGUAGE_MAP = {
                ".py": Language.PYTHON,
                ".pyi": Language.PYTHON,
                ".rs": Language.RUST,
                ".go": Language.GO,
                ".js": Language.JAVASCRIPT,
                ".jsx": Language.JAVASCRIPT,
                ".ts": Language.TYPESCRIPT,
                ".tsx": Language.TYPESCRIPT,
                ".java": Language.JAVA,
                ".rb": Language.RUBY,
                ".cs": Language.CSHARP,
                ".dart": Language.DART,
                ".kt": Language.KOTLIN,
                ".kts": Language.KOTLIN,
            }

    def get_language(self, file_path: str | Path) -> Any:
        """Get language enum value for a file."""
        ext = Path(file_path).suffix.lower()
        return self.LANGUAGE_MAP.get(ext)

    async def _ensure_server(self, file_path: str | Path) -> Any:
        """Ensure server is started for file's language.

        Args:
            file_path: Path to file (used to determine language).

        Returns:
            Started LanguageServer instance.
        """
        if not MULTILSPY_AVAILABLE:
            raise ImportError("multilspy not installed. Install with: pip install multilspy")

        lang = self.get_language(file_path)
        if not lang:
            raise ValueError(f"Unsupported file type: {Path(file_path).suffix}")

        lang_key = lang.name if hasattr(lang, "name") else str(lang)

        async with self._lock:
            if lang_key not in self._servers:
                # Create logger if not exists (with suppressed output)
                if self._logger is None:
                    import logging as _logging

                    self._logger = MultilspyLogger()
                    # Suppress INFO logs AFTER creating MultilspyLogger
                    # (MultilspyLogger.__init__ resets level to INFO)
                    _logging.getLogger("multilspy").setLevel(_logging.WARNING)

                # Create config
                config = MultilspyConfig(code_language=lang)

                logger.info(f"Starting {lang_key} language server for {self.workspace}")

                try:
                    # Create server (sync)
                    server = LanguageServer.create(config, self._logger, str(self.workspace))

                    # Start server (async context manager)
                    ctx = server.start_server()
                    await ctx.__aenter__()

                    self._servers[lang_key] = server
                    self._contexts[lang_key] = ctx
                    logger.info(f"Started {lang_key} language server successfully")
                except Exception as e:
                    logger.warning(
                        f"Failed to start {lang_key} language server: {e}. "
                        f"LSP features (impact, related, deadcode) will fall back to ripgrep."
                    )
                    raise

            return self._servers[lang_key]

    def _ensure_file_open(self, server: Any, file_path: str) -> None:
        """Ensure file is opened in the server."""
        rel_path = self._to_relative(file_path)
        if rel_path not in self._open_files:
            server.open_file(rel_path)
            self._open_files.add(rel_path)

    async def request_references(
        self,
        file_path: str | Path,
        line: int,
        col: int,
    ) -> list[dict]:
        """Find all references to a symbol.

        Args:
            file_path: Path to file containing the symbol.
            line: Line number (0-indexed).
            col: Column number (0-indexed).

        Returns:
            List of reference locations, each with 'file', 'line', 'col' keys.
        """
        server = await self._ensure_server(file_path)
        rel_path = self._to_relative(file_path)
        self._ensure_file_open(server, file_path)

        try:
            refs = await server.request_references(rel_path, line, col)
            normalized = self._normalize_locations(refs)
            if not normalized:
                logger.info(
                    f"LSP returned 0 references for {rel_path}:{line}:{col} "
                    f"(language server may not fully support this file type)"
                )
            return normalized
        except Exception as e:
            logger.warning(f"request_references failed for {rel_path}:{line}:{col}: {e}")
            return []

    async def request_definition(
        self,
        file_path: str | Path,
        line: int,
        col: int,
    ) -> list[dict]:
        """Find definition of a symbol."""
        server = await self._ensure_server(file_path)
        rel_path = self._to_relative(file_path)
        self._ensure_file_open(server, file_path)

        try:
            defs = await server.request_definition(rel_path, line, col)
            return self._normalize_locations(defs)
        except Exception as e:
            logger.warning(f"request_definition failed: {e}")
            return []

    async def request_document_symbols(
        self,
        file_path: str | Path,
    ) -> list[dict]:
        """Get all symbols defined in a file."""
        server = await self._ensure_server(file_path)
        rel_path = self._to_relative(file_path)
        self._ensure_file_open(server, file_path)

        try:
            result = await server.request_document_symbols(rel_path)
            # multilspy returns tuple (symbols_list, extra_info) - extract first element
            if isinstance(result, tuple):
                symbols = result[0]
            else:
                symbols = result
            return symbols or []
        except Exception as e:
            logger.warning(f"request_document_symbols failed: {e}")
            return []

    async def request_hover(
        self,
        file_path: str | Path,
        line: int,
        col: int,
    ) -> dict | None:
        """Get hover information for a symbol."""
        server = await self._ensure_server(file_path)
        rel_path = self._to_relative(file_path)
        self._ensure_file_open(server, file_path)

        try:
            return await server.request_hover(rel_path, line, col)
        except Exception as e:
            logger.warning(f"request_hover failed: {e}")
            return None

    async def request_diagnostics(
        self,
        file_path: str | Path,
    ) -> list[dict]:
        """Get diagnostics (errors, warnings) for a file.

        Args:
            file_path: Path to file to check.

        Returns:
            List of diagnostic dicts with severity, message, range.
        """
        server = await self._ensure_server(file_path)
        rel_path = self._to_relative(file_path)
        self._ensure_file_open(server, file_path)

        try:
            # multilspy may return diagnostics via different methods
            # Try the standard approach first
            if hasattr(server, "request_diagnostics"):
                return await server.request_diagnostics(rel_path) or []
            # Some servers publish diagnostics automatically after open_file
            # Check if server has cached diagnostics
            if hasattr(server, "get_diagnostics"):
                return server.get_diagnostics(rel_path) or []
            # Fallback: diagnostics may be in server state
            logger.debug(f"Diagnostics not directly supported for {file_path}")
            return []
        except Exception as e:
            logger.warning(f"request_diagnostics failed: {e}")
            return []

    async def close(self) -> None:
        """Close all language server connections."""
        async with self._lock:
            # Exit context managers
            for lang_key, ctx in self._contexts.items():
                try:
                    logger.info(f"Stopping {lang_key} language server")
                    await ctx.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error stopping {lang_key} server: {e}")

            self._servers.clear()
            self._contexts.clear()
            self._open_files.clear()

    def _to_relative(self, file_path: str | Path) -> str:
        """Convert absolute path to workspace-relative path."""
        path = Path(file_path)
        if path.is_absolute():
            try:
                return str(path.relative_to(self.workspace))
            except ValueError:
                return str(path)
        return str(path)

    def _normalize_locations(self, locations: list | None) -> list[dict]:
        """Normalize LSP location responses to consistent format."""
        if not locations:
            return []

        result = []
        for loc in locations:
            if isinstance(loc, dict):
                # Handle different LSP location formats
                if "absolutePath" in loc:
                    file_path = loc["absolutePath"]
                elif "uri" in loc:
                    file_path = loc["uri"].replace("file://", "")
                elif "targetUri" in loc:
                    file_path = loc["targetUri"].replace("file://", "")
                else:
                    file_path = loc.get("file", loc.get("relativePath", ""))

                range_info = loc.get("range") or loc.get("targetRange", {})
                start = range_info.get("start", {})

                result.append(
                    {
                        "file": file_path,
                        "line": start.get("line", 0),
                        "col": start.get("character", 0),
                    }
                )

        return result

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
