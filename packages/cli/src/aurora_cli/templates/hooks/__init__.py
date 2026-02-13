"""Hook templates for AI coding tools."""

from pathlib import Path

HOOKS_DIR = Path(__file__).parent


def get_hook_template(name: str) -> str | None:
    """Get hook template content by name.

    Args:
        name: Hook template name (without .py extension)

    Returns:
        Template content as string, or None if not found
    """
    template_path = HOOKS_DIR / f"{name}.py"
    if template_path.exists():
        return template_path.read_text()
    return None
