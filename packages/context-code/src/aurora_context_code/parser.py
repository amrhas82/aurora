"""Abstract interface for code parsers.

This module defines the CodeParser protocol that all language-specific parsers
must implement to provide consistent code analysis capabilities across different
programming languages.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from aurora_core.chunks.code_chunk import CodeChunk


class CodeParser(ABC):
    """Abstract base class for language-specific code parsers.

    All parser implementations must subclass this and implement the parse() method
    to extract code elements (functions, classes, methods) from source files.

    Parsers should:
    - Extract code element metadata (name, signature, location)
    - Calculate complexity metrics where possible
    - Identify dependencies between elements
    - Handle parse errors gracefully (log and return empty list)
    - Return CodeChunk instances ready for storage

    Attributes:
        language: Programming language identifier (e.g., "python", "typescript")

    """

    def __init__(self, language: str):
        """Initialize the parser.

        Args:
            language: Programming language this parser handles

        """
        self.language = language

    @abstractmethod
    def parse(self, file_path: Path) -> list[CodeChunk]:
        """Parse a source file and extract code elements.

        This method should:
        1. Read and parse the source file
        2. Extract functions, classes, and methods
        3. Calculate complexity metrics
        4. Identify dependencies
        5. Create CodeChunk instances for each element
        6. Handle errors gracefully (return empty list on failure)

        Args:
            file_path: Absolute path to source file to parse

        Returns:
            List of CodeChunk instances, one per extracted element.
            Returns empty list if parsing fails or file contains no parseable elements.

        Raises:
            This method should NOT raise exceptions for parse failures.
            Log errors and return empty list instead for resilience.

        """

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.

        Typically checks file extension against supported extensions
        for this parser's language.

        Args:
            file_path: Path to check

        Returns:
            True if this parser can handle the file, False otherwise

        """

    def __repr__(self) -> str:
        """Return string representation."""
        return f"{self.__class__.__name__}(language={self.language})"


__all__ = ["CodeParser"]
