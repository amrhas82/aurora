#!/bin/bash
#
# SOAR Query - Multi-turn orchestration using claude CLI
# No API key needed - uses Claude Code authentication
#
# Usage: ./soar-query.sh "your question"
#

# Use sonnet model (faster, cheaper) - change to opus for complex queries
MODEL="sonnet"
CLAUDE="claude -p --model $MODEL"

QUERY="$1"

if [ -z "$QUERY" ]; then
    echo "Usage: ./soar-query.sh \"your question\""
    exit 1
fi

# Progress indicator function
progress() {
    local msg="$1"
    echo -n "$msg "
    while kill -0 $! 2>/dev/null; do
        echo -n "."
        sleep 1
    done
    echo " done"
}

# Run claude with progress indicator
run_claude() {
    local phase="$1"
    local prompt="$2"
    echo -n "  [$phase] Thinking"

    # Run in background, capture output
    local output
    output=$($CLAUDE "$prompt" 2>&1) &
    local pid=$!

    # Show progress dots
    while kill -0 $pid 2>/dev/null; do
        echo -n "."
        sleep 2
    done
    wait $pid

    # Get the actual output (re-run since we can't capture from background easily)
    output=$($CLAUDE "$prompt" 2>&1)
    echo " done"
    echo "$output"
}

echo "═══════════════════════════════════════════════════════════════"
echo "SOAR Query: $QUERY"
echo "═══════════════════════════════════════════════════════════════"

# ===== PHASE 1-2: Local retrieval (no LLM) =====
echo ""
echo "## Phase 1-2: ASSESS & RETRIEVE (local)"
CONTEXT=$(aur query "$QUERY" 2>/dev/null | head -40)
echo "$CONTEXT"
echo ""

# ===== PHASE 3: DECOMPOSE (claude call 1) =====
echo "## Phase 3: DECOMPOSE"
echo -n "  Thinking..."
PHASE3=$($CLAUDE "You are a helpful assistant. Answer concisely.

Query: $QUERY

Break this query into 2-4 specific subgoals that need to be answered. List them as a numbered list:

1. [subgoal]
2. [subgoal]
..." 2>&1)
echo " done"
echo "$PHASE3"
echo ""

# ===== PHASE 4: VERIFY (claude call 2) =====
echo "## Phase 4: VERIFY"
echo -n "  Thinking..."
PHASE4=$($CLAUDE "You are a helpful assistant. Answer with just PASS or FAIL and one sentence.

Query: $QUERY

Subgoals:
$PHASE3

Do these subgoals completely cover all aspects of the query? Answer PASS or FAIL with brief reason." 2>&1)
echo " done"
echo "$PHASE4"
echo ""

# ===== PHASE 5: COLLECT (claude call 3 - main research) =====
echo "## Phase 5: COLLECT"
echo "  (This phase may take 30-60 seconds for web research...)"
echo -n "  Researching..."
PHASE5=$($CLAUDE "You are a helpful research assistant. Be thorough but concise.

Query: $QUERY

Subgoals:
$PHASE3

Research and answer each subgoal. Use web search if needed for current information. Provide specific facts, names, dates, and sources where possible." 2>&1)
echo " done"
echo "$PHASE5"
echo ""

# ===== PHASE 6: SYNTHESIZE (claude call 4) =====
echo "## Phase 6: SYNTHESIZE"
echo -n "  Thinking..."
PHASE6=$($CLAUDE "You are a helpful assistant. Synthesize concisely.

Query: $QUERY

Research findings:
$PHASE5

Combine these findings into a coherent, well-organized answer. Resolve any conflicts. Be factual." 2>&1)
echo " done"
echo "$PHASE6"
echo ""

# ===== PHASE 7: RESPOND (claude call 5) =====
echo "═══════════════════════════════════════════════════════════════"
echo "## FINAL ANSWER"
echo "═══════════════════════════════════════════════════════════════"
echo -n "  Formatting..."
FINAL=$($CLAUDE "You are a helpful assistant. Give a clear, actionable answer.

Query: $QUERY

Synthesized answer:
$PHASE6

Format a clear final answer for the user. Use headers, bullet points, and structure. Include key facts and dates." 2>&1)
echo " done"
echo ""
echo "$FINAL"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "SOAR complete (5 claude calls)"

# ===== SAVE LOG =====
LOG_DIR="$HOME/PycharmProjects/aurora/.aurora/logs/soar-queries"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
SLUG=$(echo "$QUERY" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | head -c 40)
LOG_FILE="$LOG_DIR/${TIMESTAMP}-${SLUG}.md"

cat > "$LOG_FILE" << LOGEOF
# SOAR Query Log

**Query**: $QUERY
**Timestamp**: $(date -Iseconds)
**Model**: $MODEL

## Phase 1-2: ASSESS & RETRIEVE
\`\`\`
$CONTEXT
\`\`\`

## Phase 3: DECOMPOSE
$PHASE3

## Phase 4: VERIFY
$PHASE4

## Phase 5: COLLECT
$PHASE5

## Phase 6: SYNTHESIZE
$PHASE6

## Phase 7: FINAL ANSWER
$FINAL
LOGEOF

echo ""
echo "Log saved: $LOG_FILE"
