"""
AURORA Meta-Package Setup

This setup.py provides:
1. Meta-package installation that pulls in all 6 core packages
2. Post-install hook to display component installation feedback
3. Console script entry points for CLI and MCP server
"""

import sys
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install


def display_install_feedback():
    """Display beads-style installation feedback after install."""
    # Verify core components are installed
    components_installed = True
    failed_components = []

    core_packages = [
        "aurora_core",
        "aurora_context_code",
        "aurora_soar",
        "aurora_reasoning",
        "aurora_cli",
        "aurora_testing",
    ]

    for package in core_packages:
        try:
            __import__(package)
        except ImportError:
            components_installed = False
            failed_components.append(package)

    # Beads-style output
    print("\n🔗 Aurora Installer")
    print()
    print("==> Installation complete!")
    print("==> Aurora v0.2.0 installed successfully")
    print()

    if not components_installed:
        print("⚠️  Warning: Some components failed to install:")
        for pkg in failed_components:
            print(f"    ✗ {pkg}")
        print()

    print("Aurora is installed and ready!")
    print()
    print("Get started:")
    print("  aur init              # Initialize Aurora in your project")
    print("  aur mem index .       # Index your codebase")
    print('  aur query "question"  # Search with natural language')
    print()
    print("For interactive setup:")
    print("  aur init --interactive")
    print()
    print("Check installation health:")
    print("  aur doctor")
    print("  aur version")
    print()


class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        develop.run(self)
        display_install_feedback()


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        install.run(self)
        display_install_feedback()


# Read version from pyproject.toml
def get_version():
    """Extract version from pyproject.toml."""
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        for line in content.splitlines():
            if line.startswith("version"):
                # Extract version like: version = "0.2.0"
                return line.split("=")[1].strip().strip('"').strip("'")
    return "0.2.0"


# Read long description from README
def get_long_description():
    """Read README.md for long description."""
    readme_path = Path(__file__).parent / "README.md"
    if readme_path.exists():
        return readme_path.read_text(encoding="utf-8")
    return ""


setup(
    name="aurora-actr",
    version=get_version(),
    description="AURORA: Adaptive Unified Reasoning and Orchestration Architecture with MCP Integration",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="AURORA Team",
    author_email="aurora@example.com",
    url="https://github.com/aurora/aurora",
    license="MIT",
    python_requires=">=3.10",
    # Package discovery - find namespace packages in src/
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    # Meta-package: install all core components
    # For development mode, these should already be installed from local packages/
    # For production, these will install from PyPI
    install_requires=[
        "aurora-core>=0.1.0",
        "aurora-context-code>=0.1.0",
        "aurora-soar>=0.1.0",
        "aurora-reasoning>=0.1.0",
        "aurora-cli>=0.1.0",
        "aurora-testing>=0.1.0",
    ],
    # Optional dependencies
    extras_require={
        # Machine learning dependencies for embeddings
        "ml": [
            "sentence-transformers>=2.2.0",
            "torch>=2.0.0",
        ],
        # MCP server dependencies
        "mcp": [
            "fastmcp>=0.1.0",
        ],
        # All optional dependencies
        "all": [
            "sentence-transformers>=2.2.0",
            "torch>=2.0.0",
            "fastmcp>=0.1.0",
        ],
        # Development dependencies
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "pytest-benchmark>=4.0.0",
            "ruff>=0.1.0",
            "mypy>=1.5.0",
            "types-jsonschema>=4.0.0",
            "bandit>=1.7.5",
            "memory-profiler>=0.61.0",
        ],
    },
    # Console script entry points
    entry_points={
        "console_scripts": [
            "aur=aurora_cli.main:cli",
            "aurora-mcp=aurora.mcp.server:main",
            "aurora-uninstall=aurora.scripts.uninstall:main",
        ],
    },
    # Custom commands for post-install feedback
    cmdclass={
        "develop": PostDevelopCommand,
        "install": PostInstallCommand,
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="aurora actr cognitive-architecture semantic-search mcp",
)
