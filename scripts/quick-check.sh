#!/bin/bash
# Quick health check - run before committing
# Fast version that catches most issues

echo "⚡ Quick Health Check..."

# Just run tests, no coverage (faster)
pytest -m "not ml and not real_api" -q --tb=short

# Show summary
echo ""
echo "✅ Quick check complete. For full CI checks, run: ./scripts/run-local-ci.sh"
