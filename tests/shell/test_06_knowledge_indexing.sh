#!/usr/bin/env bash
# Shell Test ST-06: Knowledge Chunk Indexing
# Validates that conversation logs can be indexed as knowledge chunks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Setup test environment
TEST_DIR=$(mktemp -d)
KNOWLEDGE_DIR="$TEST_DIR/knowledge"
mkdir -p "$KNOWLEDGE_DIR"

# Create sample conversation log
cat > "$KNOWLEDGE_DIR/2024-01-15_semantic_search_discussion.md" << 'EOF'
# Semantic Search Discussion

## Context
Discussed implementing BM25 for exact match retrieval to complement semantic search.

## Key Points
- BM25 is better for exact matches (e.g., "SoarOrchestrator")
- Semantic embeddings are better for conceptual queries
- Hybrid approach combines both strengths

## Decision
Implement tri-hybrid: BM25 + Semantic + Activation scoring

## References
- Okapi BM25 parameters: k1=1.5, b=0.75
- Stage 1: BM25 filter (top-100)
- Stage 2: Re-rank with semantic + activation
EOF

# Cleanup function
cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# Test execution
echo "ST-06: Testing knowledge chunk indexing..."

# Index the knowledge directory (markdown files treated as knowledge)
cd "$PROJECT_ROOT"
aur mem index "$KNOWLEDGE_DIR" 2>&1 | tee "$TEST_DIR/index_output.txt"

# Validate output - check for successful indexing
if grep -q "Indexing complete\|Files indexed\|Chunks created" "$TEST_DIR/index_output.txt"; then
    echo "✅ ST-06 PASSED: Knowledge directory indexed successfully"
    exit 0
else
    echo "❌ ST-06 FAILED: No indexing completion message in output"
    cat "$TEST_DIR/index_output.txt"
    exit 1
fi
