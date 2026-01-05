#!/bin/bash
# Aurora installation script - installs main package in editable mode
# Use this after making code changes to test locally

set -e  # Exit on error

echo "════════════════════════════════════════"
echo "  Aurora Local Development Install"
echo "════════════════════════════════════════"
echo ""

# Uninstall old installations
echo "Cleaning old installations..."
pip uninstall -y aurora-actr aurora-cli aurora-context-code aurora-core aurora-reasoning aurora-soar aurora-testing aurora-planning 2>/dev/null || true

# Remove stale metadata from source directories
find src/ packages/ -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove stale metadata from site-packages
rm -rf ~/.local/lib/python*/site-packages/aurora*.dist-info 2>/dev/null || true
rm -rf ~/.local/lib/python*/site-packages/*aurora*.pth 2>/dev/null || true
rm -rf ~/.local/lib/python*/site-packages/*.egg-link 2>/dev/null || true

echo ""
echo "Installing aurora-actr in editable mode..."

# Install main package with dependencies
pip install -e . --quiet

echo ""
echo "✓ Installation complete!"
echo ""
echo "Installed version:"
pip show aurora-actr | grep -E "^(Name|Version|Location):"
echo ""
echo "CLI version:"
aur --version
echo ""
echo "To install dev dependencies:"
echo "  pip install -e .[dev]"
echo ""
echo "To install ML features:"
echo "  pip install -e .[ml]"
echo ""
