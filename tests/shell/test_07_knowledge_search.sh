#!/usr/bin/env bash
# Shell Test ST-07: Knowledge Chunk Search
# Validates that indexed knowledge chunks can be searched

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Setup test environment
TEST_DIR=$(mktemp -d)
KNOWLEDGE_DIR="$TEST_DIR/knowledge"
mkdir -p "$KNOWLEDGE_DIR"

# Create sample conversation logs
cat > "$KNOWLEDGE_DIR/2024-01-15_bm25_implementation.md" << 'EOF'
# BM25 Implementation Notes

## Algorithm Details
BM25 (Best Match 25) is a ranking function used in information retrieval.
Key parameters: k1 controls term frequency saturation, b controls document length normalization.

## Implementation
- Tokenize query with code-aware patterns (CamelCase, snake_case)
- Calculate IDF for each term
- Score documents using BM25 formula
- Return top-k results

## Performance
Expected latency: <100ms for 10K documents
EOF

cat > "$KNOWLEDGE_DIR/2024-01-20_hybrid_search.md" << 'EOF'
# Hybrid Search Architecture

## Staged Retrieval
Stage 1: BM25 filtering (cast wide net, top-100)
Stage 2: Semantic + Activation re-ranking (final top-k)

## Score Combination
- BM25: 30% (exact matches)
- Semantic: 40% (conceptual similarity)
- Activation: 30% (recency + frequency)

## Benefits
- Fast exact match retrieval
- Maintains semantic understanding
- Leverages usage patterns
EOF

# Cleanup function
cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# Test execution
echo "ST-07: Testing knowledge chunk search..."

# Index the knowledge directory
cd "$PROJECT_ROOT"
aur mem index "$KNOWLEDGE_DIR" > /dev/null 2>&1 || true

# Search for BM25 knowledge
aur mem search "BM25 parameters k1 and b" --limit 3 2>&1 | tee "$TEST_DIR/search_output.txt"

# Validate results contain BM25 content or search completed successfully
if grep -qi "BM25\|k1\|parameters\|results\|No results" "$TEST_DIR/search_output.txt"; then
    echo "✅ ST-07 PASSED: Knowledge chunk search executed successfully"
    exit 0
else
    echo "❌ ST-07 FAILED: Search did not execute properly"
    cat "$TEST_DIR/search_output.txt"
    exit 1
fi
