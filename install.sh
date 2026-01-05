#!/bin/bash
# Aurora installation script - installs main package in editable mode
# Use this after making code changes to test locally
#
# Usage: sudo ./install.sh

set -e  # Exit on error

echo "════════════════════════════════════════"
echo "  Aurora Local Development Install"
echo "════════════════════════════════════════"
echo ""

# Check if running as root/sudo
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  This script requires sudo to uninstall system packages."
    echo "   Please run: sudo ./install.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo "Installing for user: $ACTUAL_USER"
echo ""

# Uninstall old installations (system-wide)
echo "Cleaning old installations..."
pip uninstall -y aurora-actr aurora-cli aurora-context-code aurora-core aurora-reasoning aurora-soar aurora-testing aurora-planning 2>/dev/null || true

# Remove stale metadata from source directories
find src/ packages/ -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove stale metadata from site-packages (both system and user)
rm -rf /usr/local/lib/python*/dist-packages/aurora*.dist-info 2>/dev/null || true
rm -rf /usr/local/lib/python*/dist-packages/*aurora*.pth 2>/dev/null || true
rm -rf $ACTUAL_HOME/.local/lib/python*/site-packages/aurora*.dist-info 2>/dev/null || true
rm -rf $ACTUAL_HOME/.local/lib/python*/site-packages/*aurora*.pth 2>/dev/null || true
rm -rf $ACTUAL_HOME/.local/lib/python*/site-packages/*.egg-link 2>/dev/null || true

# Clean up /usr/local/bin
rm -f /usr/local/bin/aur /usr/local/bin/aurora /usr/local/bin/aurora-mcp 2>/dev/null || true

echo ""
echo "Installing aurora-actr in editable mode..."

# Install main package with dependencies (as actual user, system-wide)
pip install -e .

echo ""
echo "✓ Installation complete!"
echo ""
echo "Installed version:"
pip show aurora-actr | grep -E "^(Name|Version|Location):"
echo ""
echo "CLI commands available:"
which aur
which aurora-mcp
echo ""
echo "CLI version:"
aur --version
echo ""
echo "To install dev dependencies:"
echo "  sudo pip install -e .[dev]"
echo ""
echo "To install ML features:"
echo "  sudo pip install -e .[ml]"
echo ""
