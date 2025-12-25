"""
AURORA Meta-Package Setup

This setup.py provides:
1. Meta-package installation that pulls in all 6 core packages
2. Post-install hook to display component installation feedback
3. Console script entry points for CLI and MCP server
"""

import sys
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install


def display_install_feedback():
    """Display component-level installation feedback after install."""
    components = [
        ("Core", "aurora-core", "Memory store, activation, ACT-R spreading"),
        ("Context Code", "aurora-context-code", "Semantic search, embeddings, AST parsing"),
        ("SOAR", "aurora-soar", "Deliberation, escalation, cognitive architecture"),
        ("Reasoning", "aurora-reasoning", "Decision-making, planning, goal management"),
        ("CLI", "aurora-cli", "Command-line interface (aur)"),
        ("Testing", "aurora-testing", "Test utilities and fixtures"),
    ]

    print("\n" + "=" * 70)
    print("AURORA v0.2.0 Installation Complete")
    print("=" * 70)
    print("\nInstalled Components:")

    for name, package, description in components:
        try:
            __import__(package.replace("-", "_"))
            status = "✓"
        except ImportError:
            status = "✗"
        print(f"  {status} {name:15} ({package})")
        print(f"    {description}")

    print("\n" + "=" * 70)
    print("Next Steps:")
    print("  1. Run 'aur init' to create configuration")
    print("  2. Run 'aur mem index <path>' to index your codebase")
    print("  3. Run 'aur --verify' to verify installation health")
    print("  4. See docs/MCP_SETUP.md for Claude Desktop integration")
    print("=" * 70 + "\n")


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
