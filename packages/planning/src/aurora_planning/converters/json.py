"""JSON converter for Aurora files.

Converts capability and plan markdown files to JSON format.
"""

import json
from pathlib import Path
from typing import Any

from aurora_planning.parsers.markdown import MarkdownParser
from aurora_planning.parsers.plan_parser import PlanParser


class JsonConverter:
    """Convert Aurora markdown files to JSON format."""

    def convert_capability_to_json(self, file_path: str) -> str:
        """Convert a capability file to JSON.

        Args:
            file_path: Path to the capability spec.md file

        Returns:
            JSON string representation of the capability

        """
        content = Path(file_path).read_text(encoding="utf-8")
        parser = MarkdownParser(content)
        capability_name = self._extract_name_from_path(file_path)

        capability = parser.parse_capability(capability_name)

        json_capability: dict[str, Any] = {
            "name": capability.name,
            "overview": capability.overview or "",
            "requirements": [
                {
                    "text": req.text,
                    "scenarios": [s.raw_text for s in (req.scenarios or [])],
                }
                for req in (capability.requirements or [])
            ],
            "metadata": {
                "sourcePath": file_path,
            },
        }

        return json.dumps(json_capability, indent=2)

    def convert_plan_to_json(self, file_path: str) -> str:
        """Convert a plan file to JSON.

        Args:
            file_path: Path to the plan.md file

        Returns:
            JSON string representation of the plan

        """
        content = Path(file_path).read_text(encoding="utf-8")
        plan_dir = str(Path(file_path).parent)
        plan_name = self._extract_name_from_path(file_path)

        parser = PlanParser(content, plan_dir)
        plan = parser.parse_plan_with_modifications(plan_name)

        json_plan: dict[str, Any] = {
            "name": plan.name,
            "why": plan.why or "",
            "what_changes": plan.what_changes or "",
            "modifications": [
                {
                    "operation": mod.operation,
                    "capability": mod.capability,
                    "description": mod.description,
                }
                for mod in (plan.modifications or [])
            ],
            "metadata": {
                "sourcePath": file_path,
            },
        }

        return json.dumps(json_plan, indent=2)

    def _extract_name_from_path(self, file_path: str) -> str:
        """Extract the item name from a file path.

        Looks for 'capabilities' or 'plans' directory and returns the
        following path segment as the name.

        Args:
            file_path: Path to the file

        Returns:
            Extracted name

        """
        # Normalize to forward slashes
        normalized = file_path.replace("\\", "/")
        parts = normalized.split("/")

        # Look for known directory markers
        for i, part in enumerate(parts):
            if part in ("capabilities", "plans", "specs", "changes"):
                if i < len(parts) - 1:
                    return parts[i + 1]

        # Fallback: use filename without extension
        filename = parts[-1] if parts else ""
        dot_index = filename.rfind(".")
        return filename[:dot_index] if dot_index > 0 else filename
