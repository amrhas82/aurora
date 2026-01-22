"""Project context template for Aurora planning system.

Rebranded from OpenSpec to Aurora.
"""

PROJECT_TEMPLATE = """# Project Context

## Purpose
[Describe your project's purpose and goals]

## Tech Stack
- [List your primary technologies]
- [e.g., Python, TypeScript, React, Node.js]

## Project Conventions

### Code Style
[Describe your code style preferences, formatting rules, and naming conventions]

### Architecture Patterns
[Document your architectural decisions and patterns]

### Testing Strategy
[Explain your testing approach and requirements]

### Git Workflow
[Describe your branching strategy and commit conventions]

## Domain Context
[Add domain-specific knowledge that AI assistants need to understand]

## Important Constraints
[List any technical, business, or regulatory constraints]

## External Dependencies
[Document key external services, APIs, or systems]
"""


def get_project_template() -> str:
    """Get the project.md template.

    Returns:
        project.md template string

    """
    return PROJECT_TEMPLATE
