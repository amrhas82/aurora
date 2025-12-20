"""
Complex Python file for testing advanced features:
- Nested classes
- Multiple inheritance
- Complex control flow
- High cyclomatic complexity
"""

from typing import List, Dict, Any, Optional
import json
import logging


logger = logging.getLogger(__name__)


class BaseProcessor:
    """Base class for data processors."""

    def __init__(self, name: str):
        """Initialize processor with a name."""
        self.name = name
        self.stats = {"processed": 0, "errors": 0}

    def log_stats(self) -> None:
        """Log processing statistics."""
        logger.info(f"{self.name}: {self.stats}")


class DataValidator:
    """Mixin for data validation."""

    def validate(self, data: Any) -> bool:
        """Validate input data."""
        return data is not None


class DataProcessor(BaseProcessor, DataValidator):
    """
    Advanced data processor with validation.

    Combines processing and validation capabilities.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize processor with configuration."""
        super().__init__(name)
        self.config = config or {}
        self.cache: Dict[str, Any] = {}

    def process(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of data items with complex logic.

        This method has high cyclomatic complexity for testing purposes.
        """
        results = []

        for item in data:
            try:
                # Validate item
                if not self.validate(item):
                    self.stats["errors"] += 1
                    continue

                # Check cache
                item_id = item.get("id")
                if item_id and item_id in self.cache:
                    results.append(self.cache[item_id])
                    continue

                # Process based on type
                item_type = item.get("type")
                if item_type == "text":
                    processed = self._process_text(item)
                elif item_type == "number":
                    processed = self._process_number(item)
                elif item_type == "list":
                    processed = self._process_list(item)
                elif item_type == "dict":
                    processed = self._process_dict(item)
                else:
                    processed = self._process_unknown(item)

                # Apply transformations
                if self.config.get("uppercase"):
                    processed = self._apply_uppercase(processed)

                if self.config.get("trim"):
                    processed = self._apply_trim(processed)

                if self.config.get("validate_output"):
                    if not self.validate(processed):
                        self.stats["errors"] += 1
                        continue

                # Cache result
                if item_id:
                    self.cache[item_id] = processed

                results.append(processed)
                self.stats["processed"] += 1

            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Error processing item: {e}")
                self.stats["errors"] += 1
            except Exception as e:
                logger.exception(f"Unexpected error: {e}")
                self.stats["errors"] += 1

        return results

    def _process_text(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process text items."""
        return {"type": "text", "value": str(item.get("value", ""))}

    def _process_number(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process number items."""
        value = item.get("value", 0)
        return {"type": "number", "value": float(value)}

    def _process_list(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process list items."""
        value = item.get("value", [])
        return {"type": "list", "value": list(value)}

    def _process_dict(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process dictionary items."""
        value = item.get("value", {})
        return {"type": "dict", "value": dict(value)}

    def _process_unknown(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process unknown item types."""
        return {"type": "unknown", "value": item}

    def _apply_uppercase(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Apply uppercase transformation."""
        if item["type"] == "text":
            item["value"] = item["value"].upper()
        return item

    def _apply_trim(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Apply trim transformation."""
        if item["type"] == "text":
            item["value"] = item["value"].strip()
        return item

    def clear_cache(self) -> None:
        """Clear the processing cache."""
        self.cache.clear()

    class CacheManager:
        """Nested class for cache management."""

        def __init__(self, parent):
            """Initialize cache manager."""
            self.parent = parent

        def get_size(self) -> int:
            """Get cache size."""
            return len(self.parent.cache)

        def evict_old_entries(self, max_size: int) -> None:
            """Evict old cache entries if size exceeds limit."""
            if self.get_size() > max_size:
                # Keep only the last max_size entries
                items = list(self.parent.cache.items())
                self.parent.cache = dict(items[-max_size:])


def analyze_complexity(code: str) -> Dict[str, int]:
    """
    Analyze code complexity metrics.

    Has moderate complexity for testing.
    """
    metrics = {
        "lines": 0,
        "functions": 0,
        "classes": 0,
        "branches": 0,
    }

    lines = code.split("\n")
    metrics["lines"] = len(lines)

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("def "):
            metrics["functions"] += 1
        elif stripped.startswith("class "):
            metrics["classes"] += 1
        elif any(kw in stripped for kw in ["if ", "elif ", "for ", "while "]):
            metrics["branches"] += 1

    return metrics
