"""PlanCommand CLI wrapper for plan management.

This is a placeholder/stub implementation to allow test collection.
Tests are written first (TDD) before full implementation.
"""

from pathlib import Path


class PlanCommand:
    """CLI command for creating and managing plans."""

    def __init__(self, project_root: Path | None = None):
        """Initialize PlanCommand.

        Args:
            project_root: Root directory of the project. Defaults to current directory.

        """
        self.project_root = project_root or Path.cwd()

    def create(
        self,
        name: str,
        description: str | None = None,
        template: str | None = None,
    ) -> Path:
        """Create a new plan.

        Args:
            name: Name of the plan
            description: Optional description
            template: Optional template name

        Returns:
            Path to the created plan directory

        Raises:
            NotImplementedError: This is a stub implementation

        """
        raise NotImplementedError("PlanCommand.create() not yet implemented")

    def list(self) -> list[dict]:
        """List all plans.

        Returns:
            List of plan metadata dictionaries

        Raises:
            NotImplementedError: This is a stub implementation

        """
        raise NotImplementedError("PlanCommand.list() not yet implemented")

    def view(self, plan_id: str) -> dict:
        """View details of a specific plan.

        Args:
            plan_id: ID of the plan to view

        Returns:
            Plan metadata and content

        Raises:
            NotImplementedError: This is a stub implementation

        """
        raise NotImplementedError("PlanCommand.view() not yet implemented")
