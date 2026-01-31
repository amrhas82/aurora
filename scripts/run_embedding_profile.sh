#!/bin/bash
# Runner script for embedding load profiling

set -e

cd "$(dirname "$0")/.."

echo "🔍 Embedding Load Time Profiling"
echo "================================="
echo ""

# Check if in Aurora project
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must be run from Aurora project root"
    exit 1
fi

# Default parameters
RUNS="${RUNS:-5}"
MODEL="${MODEL:-all-MiniLM-L6-v2}"
COLD_START="${COLD_START:-false}"

echo "📋 Configuration:"
echo "   Model: $MODEL"
echo "   Runs: $RUNS"
echo "   Cold start: $COLD_START"
echo ""

# Build command
CMD="python3 scripts/profile_embedding_load.py --model $MODEL --runs $RUNS"

if [ "$COLD_START" = "true" ]; then
    CMD="$CMD --cold-start"
fi

# Run profiling
echo "🚀 Starting profiling..."
echo ""
$CMD

echo ""
echo "✓ Profiling complete!"
