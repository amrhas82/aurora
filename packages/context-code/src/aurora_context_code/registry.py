"""Parser registry for managing language-specific code parsers.

This module provides the ParserRegistry class for registering and discovering
code parsers for different programming languages.
"""

import logging
from pathlib import Path

from aurora_context_code.parser import CodeParser


logger = logging.getLogger(__name__)


class ParserRegistry:
    """Registry for managing code parsers.

    Provides centralized registration and discovery of language-specific
    parsers. Parsers can be registered manually or auto-registered on
    module import.

    Example:
        >>> registry = ParserRegistry()
        >>> from aurora_context_code.languages.python import PythonParser
        >>> registry.register(PythonParser())
        >>> parser = registry.get_parser_for_file(Path("example.py"))

    """

    def __init__(self) -> None:
        """Initialize empty parser registry."""
        self._parsers: dict[str, CodeParser] = {}
        logger.debug("ParserRegistry initialized")

    def register(self, parser: CodeParser) -> None:
        """Register a code parser.

        Args:
            parser: Parser instance to register

        Raises:
            ValueError: If a parser for this language is already registered

        """
        if parser.language in self._parsers:
            logger.warning(
                f"Parser for language '{parser.language}' already registered, "
                f"replacing with {parser.__class__.__name__}",
            )

        self._parsers[parser.language] = parser
        logger.debug(f"Registered parser: {parser}")

    def get_parser(self, language: str) -> CodeParser | None:
        """Get parser for a specific language.

        Args:
            language: Programming language identifier (e.g., "python")

        Returns:
            Parser instance if registered, None otherwise

        """
        return self._parsers.get(language)

    def get_parser_for_file(self, file_path: Path) -> CodeParser | None:
        """Get appropriate parser for a given file.

        Checks all registered parsers to find one that can handle the file.

        Args:
            file_path: Path to source file

        Returns:
            Parser instance that can handle the file, None if no parser found

        """
        for parser in self._parsers.values():
            if parser.can_parse(file_path):
                logger.debug(f"Found parser {parser} for file {file_path}")
                return parser

        logger.debug(f"No parser found for file {file_path}")
        return None

    def list_languages(self) -> list[str]:
        """List all registered languages.

        Returns:
            List of language identifiers

        """
        return list(self._parsers.keys())

    def unregister(self, language: str) -> bool:
        """Unregister a parser.

        Args:
            language: Language identifier

        Returns:
            True if parser was unregistered, False if not found

        """
        if language in self._parsers:
            del self._parsers[language]
            logger.debug(f"Unregistered parser for language: {language}")
            return True
        return False

    def clear(self) -> None:
        """Remove all registered parsers."""
        self._parsers.clear()
        logger.debug("Cleared all parsers from registry")

    def __repr__(self) -> str:
        """Return string representation."""
        languages = ", ".join(self._parsers.keys())
        return f"ParserRegistry(languages=[{languages}])"


# Global registry instance
_global_registry: ParserRegistry | None = None


def get_global_registry() -> ParserRegistry:
    """Get the global parser registry instance.

    Creates the registry on first access (lazy initialization).

    Returns:
        Global ParserRegistry instance

    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ParserRegistry()
        logger.debug("Created global parser registry")

        # Auto-register built-in parsers
        _register_builtin_parsers(_global_registry)

    return _global_registry


def _register_builtin_parsers(registry: ParserRegistry) -> None:
    """Auto-register built-in parsers.

    Args:
        registry: Registry to register parsers in

    """
    try:
        from aurora_context_code.languages.python import PythonParser

        registry.register(PythonParser())
        logger.debug("Auto-registered PythonParser")
    except Exception as e:
        logger.warning(f"Failed to auto-register PythonParser: {e}")

    try:
        from aurora_context_code.languages.markdown import MarkdownParser

        registry.register(MarkdownParser())
        logger.debug("Auto-registered MarkdownParser")
    except Exception as e:
        logger.warning(f"Failed to auto-register MarkdownParser: {e}")

    try:
        from aurora_context_code.languages.typescript import TypeScriptParser

        registry.register(TypeScriptParser())
        logger.debug("Auto-registered TypeScriptParser")
    except Exception as e:
        logger.warning(f"Failed to auto-register TypeScriptParser: {e}")

    try:
        from aurora_context_code.languages.javascript import JavaScriptParser

        registry.register(JavaScriptParser())
        logger.debug("Auto-registered JavaScriptParser")
    except Exception as e:
        logger.warning(f"Failed to auto-register JavaScriptParser: {e}")


__all__ = ["ParserRegistry", "get_global_registry"]
