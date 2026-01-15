#!/bin/bash
echo "=== MARKER USAGE REPORT ==="
echo ""
for marker in unit integration e2e ml slow real_api critical safety cli mcp soar core fast performance; do
  count=$(grep -r "@pytest.mark.$marker" tests/ 2>/dev/null | wc -l)
  echo "$marker: $count uses"
done
