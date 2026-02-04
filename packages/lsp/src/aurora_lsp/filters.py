"""Import filtering for LSP references.

Distinguishes actual usages from import statements across multiple languages.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Awaitable, Callable


class ImportFilter:
    """Filter import statements from LSP references.

    LSP returns ALL references including imports. This class distinguishes
    actual usages from import statements using language-specific patterns.
    """

    # Language-specific import statement patterns
    IMPORT_PATTERNS: dict[str, list[str]] = {
        "python": [
            r"^\s*import\s+",
            r"^\s*from\s+[\w.]+\s+import\s+",
        ],
        "javascript": [
            r"^\s*import\s+",
            r"^\s*import\s*\{",
            r"^\s*import\s+\*\s+as\s+",
            r"^\s*(const|let|var)\s+.*\s*=\s*require\s*\(",
        ],
        "typescript": [
            r"^\s*import\s+",
            r"^\s*import\s*\{",
            r"^\s*import\s+\*\s+as\s+",
            r"^\s*import\s+type\s+",
            r"^\s*(const|let|var)\s+.*\s*=\s*require\s*\(",
        ],
        "go": [
            r"^\s*import\s+",
            r"^\s*import\s*\(",
            r'^\s*"[\w/.-]+"',  # Inside import block
        ],
        "rust": [
            r"^\s*use\s+",
            r"^\s*extern\s+crate\s+",
        ],
        "java": [
            r"^\s*import\s+",
            r"^\s*import\s+static\s+",
        ],
        "ruby": [
            r"^\s*require\s+",
            r"^\s*require_relative\s+",
            r"^\s*load\s+",
            r"^\s*autoload\s+",
        ],
        "csharp": [
            r"^\s*using\s+",
            r"^\s*using\s+static\s+",
        ],
        "dart": [
            r"^\s*import\s+",
            r"^\s*export\s+",
            r"^\s*part\s+",
        ],
        "kotlin": [
            r"^\s*import\s+",
        ],
    }

    def __init__(self, language: str):
        """Initialize filter for a specific language.

        Args:
            language: Language identifier (e.g., 'python', 'typescript').
        """
        self.language = language
        patterns = self.IMPORT_PATTERNS.get(language, [])
        self.patterns = [re.compile(p) for p in patterns]

    def is_import_line(self, line_content: str) -> bool:
        """Check if a line is an import statement.

        Args:
            line_content: The source code line to check.

        Returns:
            True if the line is an import statement.
        """
        for pattern in self.patterns:
            if pattern.match(line_content):
                return True
        return False

    async def filter_references(
        self,
        refs: list[dict],
        file_reader: Callable[[str, int], Awaitable[str]],
    ) -> tuple[list[dict], list[dict]]:
        """Split references into usages and imports.

        Args:
            refs: List of reference locations from LSP.
            file_reader: Async function to read a line from a file.
                         Signature: (file_path, line_number) -> line_content

        Returns:
            Tuple of (usages, imports) where each is a list of references.
        """
        usages = []
        imports = []

        for ref in refs:
            file_path = ref.get("file", "")
            line_num = ref.get("line", 0)

            try:
                line_content = await file_reader(file_path, line_num)
                ref_with_context = {**ref, "context": line_content.strip()}

                if self.is_import_line(line_content):
                    imports.append(ref_with_context)
                else:
                    usages.append(ref_with_context)
            except Exception:
                # If we can't read the line, assume it's a usage
                usages.append(ref)

        return usages, imports

    def filter_references_sync(
        self,
        refs: list[dict],
        file_reader: Callable[[str, int], str],
    ) -> tuple[list[dict], list[dict]]:
        """Synchronous version of filter_references.

        Args:
            refs: List of reference locations from LSP.
            file_reader: Sync function to read a line from a file.

        Returns:
            Tuple of (usages, imports).
        """
        usages = []
        imports = []

        for ref in refs:
            file_path = ref.get("file", "")
            line_num = ref.get("line", 0)

            try:
                line_content = file_reader(file_path, line_num)
                ref_with_context = {**ref, "context": line_content.strip()}

                if self.is_import_line(line_content):
                    imports.append(ref_with_context)
                else:
                    usages.append(ref_with_context)
            except Exception:
                usages.append(ref)

        return usages, imports


def get_filter_for_file(file_path: str | Path) -> ImportFilter:
    """Get appropriate ImportFilter for a file based on extension.

    Args:
        file_path: Path to file.

    Returns:
        ImportFilter for the file's language.
    """
    ext_to_lang = {
        ".py": "python",
        ".pyi": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
        ".cs": "csharp",
        ".dart": "dart",
        ".kt": "kotlin",
        ".kts": "kotlin",
    }

    ext = Path(file_path).suffix.lower()
    lang = ext_to_lang.get(ext, "python")  # Default to Python patterns
    return ImportFilter(lang)
