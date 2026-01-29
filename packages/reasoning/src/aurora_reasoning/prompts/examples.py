"""Few-shot examples loader for AURORA reasoning prompts."""

import json
from enum import Enum
from pathlib import Path
from typing import Any


class Complexity(str, Enum):
    """Query complexity levels."""

    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"
    CRITICAL = "CRITICAL"


class ExamplesLoader:
    """Loader for few-shot examples with complexity-based scaling.

    Examples are loaded from JSON files and selected based on query complexity:
    - SIMPLE: 0 examples (no few-shot needed)
    - MEDIUM: 2 examples
    - COMPLEX: 4 examples
    - CRITICAL: 6 examples
    """

    def __init__(self, examples_dir: Path | None = None):
        """Initialize examples loader.

        Args:
            examples_dir: Directory containing example JSON files
                         (defaults to packages/reasoning/examples/)

        """
        if examples_dir is None:
            # Default to examples directory relative to this file
            # Try two locations:
            # 1. Installed: site-packages/aurora_reasoning/examples/
            # 2. Dev mode: packages/reasoning/examples/ (outside src/)
            pkg_root = Path(__file__).resolve().parent.parent
            installed_examples = pkg_root / "examples"

            if installed_examples.exists():
                # Installed mode
                examples_dir = installed_examples
            else:
                # Dev mode: go up to reasoning package root (4 levels)
                reasoning_pkg_root = pkg_root.parent.parent
                examples_dir = reasoning_pkg_root / "examples"

        self.examples_dir = Path(examples_dir)
        self._cache: dict[str, list[dict[str, Any]]] = {}

    def load_examples(self, filename: str) -> list[dict[str, Any]]:
        """Load examples from JSON file.

        Args:
            filename: Name of JSON file in examples directory

        Returns:
            List of example dicts

        Raises:
            FileNotFoundError: If examples file doesn't exist
            ValueError: If JSON is invalid

        """
        # Check cache first
        if filename in self._cache:
            return self._cache[filename]

        filepath = self.examples_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Examples file not found: {filepath}")

        try:
            with open(filepath, encoding="utf-8") as f:
                examples = json.load(f)

            if not isinstance(examples, list):
                raise ValueError(f"Examples file must contain a JSON array: {filename}")

            # Cache and return
            self._cache[filename] = examples
            return examples

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in examples file {filename}: {e}") from e

    def get_examples_by_complexity(
        self,
        filename: str,
        complexity: Complexity,
    ) -> list[dict[str, Any]]:
        """Get appropriate number of examples based on complexity.

        Args:
            filename: Name of JSON file in examples directory
            complexity: Query complexity level

        Returns:
            List of examples (0, 2, 4, or 6 based on complexity)

        """
        all_examples = self.load_examples(filename)

        # Determine how many examples to return
        # Note: Reduced from 4/6 to 2/3 to avoid exceeding context limits
        # when piping to CLI tools (claude, cursor, etc.)
        example_counts = {
            Complexity.SIMPLE: 0,
            Complexity.MEDIUM: 1,
            Complexity.COMPLEX: 1,  # was 2
            Complexity.CRITICAL: 2,  # was 3
        }

        count = example_counts[complexity]

        # Return first N examples (assumes examples are ordered by quality/relevance)
        return all_examples[:count]

    def get_examples_by_tags(
        self,
        filename: str,
        tags: list[str],
        max_count: int = 6,
    ) -> list[dict[str, Any]]:
        """Get examples filtered by tags.

        Args:
            filename: Name of JSON file in examples directory
            tags: List of tags to filter by (examples must have at least one matching tag)
            max_count: Maximum number of examples to return

        Returns:
            List of matching examples (up to max_count)

        """
        all_examples = self.load_examples(filename)

        # Filter examples by tags
        matching = []
        for example in all_examples:
            example_tags = example.get("tags", [])
            if any(tag in example_tags for tag in tags):
                matching.append(example)
                if len(matching) >= max_count:
                    break

        return matching


# Global singleton instance
_default_loader: ExamplesLoader | None = None


def get_loader() -> ExamplesLoader:
    """Get the default examples loader instance.

    Returns:
        Global ExamplesLoader instance

    """
    global _default_loader
    if _default_loader is None:
        _default_loader = ExamplesLoader()
    return _default_loader


__all__ = ["ExamplesLoader", "Complexity", "get_loader"]
