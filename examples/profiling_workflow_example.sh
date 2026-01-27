#!/bin/bash
# Example workflow for embedding load profiling
# This demonstrates a complete profiling cycle from baseline to optimization

set -e

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║           Embedding Load Profiling - Complete Workflow Example            ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Create reports directory if it doesn't exist
mkdir -p reports

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Establish Baseline (Warm Start)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This establishes baseline performance metrics for the current implementation."
echo "Run this BEFORE making any optimization changes."
echo ""

read -p "Press Enter to run baseline profiling (or Ctrl+C to skip)..."
echo ""

python3 scripts/profile_embedding_load.py \
  --model all-MiniLM-L6-v2 \
  --runs 5 \
  --output reports/baseline_warm.json

echo ""
echo "✓ Baseline established and saved to reports/baseline_warm.json"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: (Optional) Cold Start Baseline"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Cold start profiling clears the model cache to simulate first-time user"
echo "experience. This is optional but recommended for comprehensive profiling."
echo ""

read -p "Run cold start profiling? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "⚠️  WARNING: This will clear the model cache!"
    echo "The model will be re-downloaded (88MB for default model)."
    echo ""
    read -p "Proceed with cold start test? (y/N): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 scripts/profile_embedding_load.py \
          --model all-MiniLM-L6-v2 \
          --runs 3 \
          --cold-start \
          --output reports/baseline_cold.json

        echo ""
        echo "✓ Cold start baseline saved to reports/baseline_cold.json"
    else
        echo "Skipped cold start profiling."
    fi
else
    echo "Skipped cold start profiling."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Make Optimization Changes"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Now is the time to implement your optimization changes."
echo ""
echo "Example optimizations you might try:"
echo "  • Enable background loading"
echo "  • Add lazy imports"
echo "  • Use offline mode (HF_HUB_OFFLINE=1)"
echo "  • Try a smaller model"
echo "  • Implement model caching improvements"
echo ""
echo "After making changes, continue to Step 4 to measure the impact."
echo ""

read -p "Press Enter when you've made optimization changes (or Ctrl+C to exit)..."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Profile After Changes"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This profiles the optimized code and compares against the baseline."
echo ""

python3 scripts/profile_embedding_load.py \
  --model all-MiniLM-L6-v2 \
  --runs 5 \
  --output reports/after_optimization.json \
  --baseline reports/baseline_warm.json

echo ""
echo "✓ Post-optimization results saved to reports/after_optimization.json"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Regression Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Running automated regression check (as would be done in CI/CD)..."
echo ""

if python3 scripts/check_performance_regression.py \
  --current reports/after_optimization.json \
  --baseline reports/baseline_warm.json \
  --threshold 1.2; then

    echo ""
    echo "🎉 SUCCESS! Optimization passed regression check."
    echo ""
    echo "Next steps:"
    echo "  1. Update baseline: mv reports/after_optimization.json reports/baseline_warm.json"
    echo "  2. Commit changes"
    echo "  3. Add regression check to CI/CD pipeline"
else
    echo ""
    echo "⚠️  REGRESSION DETECTED!"
    echo ""
    echo "The optimization made performance worse. Options:"
    echo "  1. Investigate why performance degraded"
    echo "  2. Try different optimization approach"
    echo "  3. Revert changes"
    echo "  4. Adjust threshold if acceptable trade-off"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 6: Compare Multiple Models (Optional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "You can also profile different models to find the best speed/quality trade-off."
echo ""

read -p "Compare different models? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Profiling alternative models..."
    echo ""

    # Lightweight model
    echo "1. Testing paraphrase-MiniLM-L3-v2 (faster, smaller)..."
    python3 scripts/profile_embedding_load.py \
      --model paraphrase-MiniLM-L3-v2 \
      --runs 3 \
      --output reports/profile_miniml_l3.json || true

    echo ""

    # Higher quality model
    echo "2. Testing all-mpnet-base-v2 (slower, better quality)..."
    python3 scripts/profile_embedding_load.py \
      --model all-mpnet-base-v2 \
      --runs 3 \
      --output reports/profile_mpnet.json || true

    echo ""
    echo "✓ Model comparison complete. Review reports/ directory for results."
    echo ""
    echo "Summary of trade-offs:"
    echo "  • paraphrase-MiniLM-L3-v2: Fastest (128 dim), good quality"
    echo "  • all-MiniLM-L6-v2: Balanced (384 dim), better quality [DEFAULT]"
    echo "  • all-mpnet-base-v2: Slower (768 dim), best quality"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                        Profiling Workflow Complete                         ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Generated Reports:"
echo "   • reports/baseline_warm.json - Warm start baseline"
if [ -f reports/baseline_cold.json ]; then
    echo "   • reports/baseline_cold.json - Cold start baseline"
fi
echo "   • reports/after_optimization.json - Post-optimization results"
if [ -f reports/profile_miniml_l3.json ]; then
    echo "   • reports/profile_*.json - Model comparison results"
fi
echo ""
echo "📚 Documentation:"
echo "   • docs/performance/embedding_load_profiling.md - Full documentation"
echo "   • scripts/README_PROFILING.md - Quick reference"
echo ""
echo "🔧 Next Steps:"
echo "   1. Review profiling results in reports/ directory"
echo "   2. Update baseline if optimization was successful"
echo "   3. Add regression check to CI/CD pipeline"
echo "   4. Consider trying different models based on trade-offs"
echo ""
echo "For more information:"
echo "   python3 scripts/profile_embedding_load.py --help"
echo "   cat scripts/README_PROFILING.md"
echo ""
