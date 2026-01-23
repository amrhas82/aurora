#!/bin/bash
# Monitor baseline test and auto-analyze when complete

PID=641798
OUTPUT_FILE="phase2b_baseline_tests.txt"

echo "Monitoring baseline test (PID: $PID)..."
echo "Started: 08:53"
echo "Output: $OUTPUT_FILE"
echo ""

# Wait for process to complete
while ps -p $PID > /dev/null 2>&1; do
    # Show current progress every 60 seconds
    sleep 60
    PERCENT=$(grep -E "\[.*%\]" $OUTPUT_FILE | tail -1 | grep -oE "[0-9]+%")
    LINES=$(wc -l < $OUTPUT_FILE)
    TIME=$(date +"%H:%M")
    echo "[$TIME] Progress: $PERCENT ($LINES lines)"
done

echo ""
echo "=================================================="
echo "✅ BASELINE TEST COMPLETE!"
echo "=================================================="
echo "Completed at: $(date +"%H:%M")"
echo ""

# Auto-run analysis
echo "Running automatic analysis..."
echo ""
./analyze_baseline.sh

echo ""
echo "=================================================="
echo "NEXT STEPS"
echo "=================================================="
echo ""
echo "1. Review the analysis above"
echo "2. Check the recommendation (PROCEED or CAUTION)"
echo "3. If PROCEED:"
echo "   ./execute_task12.sh"
echo "4. If CAUTION:"
echo "   Review conflicts in detail first"
echo ""
