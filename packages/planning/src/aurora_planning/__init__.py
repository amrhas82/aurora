"""Aurora Planning System - Phase 1 Foundation.

This package provides the core planning infrastructure for Aurora, enabling
structured plan creation, management, and tracking through an eight-file workflow.

Key Features:
- Plan creation with auto-incrementing IDs (NNNN-slug format)
- Eight-file structure (4 base files + 4 capability specs)
- Plan listing, viewing, and archiving
- Jinja2-based template rendering
- Pydantic-validated schemas
- Aurora-native directory structure (.aurora/plans/)

Commands:
- aur plan create <goal>  # Create new plan
- aur plan list           # List all plans
- aur plan view <id>      # View plan details
- aur plan archive <id>   # Archive completed plan
- aur init                # Initialize Aurora directory structure

For detailed documentation, see packages/planning/README.md
"""

__version__ = "0.1.0"

from aurora_planning.renderer import TemplateRenderer, get_template_dir, render_plan_files

__all__ = [
    "__version__",
    "render_plan_files",
    "TemplateRenderer",
    "get_template_dir",
]
