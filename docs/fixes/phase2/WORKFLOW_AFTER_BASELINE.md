# Workflow: After Baseline Completes

**Created:** 2026-01-23 15:40
**Purpose:** Smart workflow that analyzes baseline before proceeding

---

## Step 1: Analyze Baseline Results ⚠️ CRITICAL

**Why this matters:**
- 632 failures detected (12.2%)
- Need to understand if any failures are in files we're modifying
- High failure count could mask Task 12 issues
- Should inform our proceed/caution decision

**Command:**
```bash
./analyze_baseline.sh
```

**What it does:**
1. ✅ Extracts test summary (passed/failed/skipped)
2. ✅ Categorizes failures by test type (e2e/integration/unit)
3. ✅ **Identifies conflicts** - checks if Task 12 files have failing tests
4. ✅ Analyzes failure patterns (MCP, planning, SOAR, spawn)
5. ✅ Checks for import/initialization errors
6. ✅ Generates failure report file
7. ✅ **Provides recommendation** (proceed/caution/investigate)

**Expected output:**
```
================================================
FINAL RECOMMENDATION
================================================

✅ PROCEED: Execute Task 12
   (if no conflicts)

OR

⚠️  CAUTION: Review conflicts and failure count
   (if conflicts detected)
```

---

## Step 2: Review Analysis & Decide

### If Analysis Says "✅ PROCEED":
- No Task 12 files have failing tests
- Failure count is reasonable (<1000)
- Safe to proceed with comment removal

**Action:** Continue to Step 3

### If Analysis Says "⚠️ CAUTION":
- Some Task 12 files have failing tests
- OR failure count is high (>1000)

**Decision matrix:**

**Option A: Fix Conflicts First (Safest)**
```bash
# Identify specific failing tests
cat phase2b_baseline_failures.txt | grep "<conflicting-file>"

# Fix those tests
# Re-run baseline
# Then proceed with Task 12
```

**Option B: Proceed with Documented Expectations**
```bash
# Document which failures are expected
# Proceed with Task 12
# Validation must show SAME failures (no new ones)
```

**Option C: Adjust Task 12 Scope**
```bash
# Exclude conflicting files from Task 12
# Modify execute_task12.sh
# Proceed with reduced scope
```

---

## Step 3: Execute Task 12 (If Cleared to Proceed)

**Command:**
```bash
./execute_task12.sh
```

**What it does:**
- Pops stash (restores comment removal changes)
- Creates 5 commits (Tasks 12.4-12.8)
- Verifies ERA001 after each commit
- Shows summary

**Duration:** ~5 minutes

**Output to verify:**
```
✅ Task 12.4 committed
✅ Task 12.5 committed
✅ Task 12.6 committed
✅ Task 12.7 committed
✅ Task 12.8 committed
All checks passed!
```

---

## Step 4: Run Validation Test Suite

**Command:**
```bash
nohup make test > phase2b_validation_tests.txt 2>&1 &
echo $! > validation_test.pid
```

**Duration:** ~5-7 hours (same as baseline)

**Monitor progress:**
```bash
# Check progress
tail -20 phase2b_validation_tests.txt
grep "\[.*%\]" phase2b_validation_tests.txt | tail -1

# Check if still running
ps aux | grep $(cat validation_test.pid)
```

---

## Step 5: Compare Baseline vs Validation

**When validation completes:**

### 5a. Quick Summary Comparison
```bash
# Extract summaries
echo "=== BASELINE ==="
tail -50 phase2b_baseline_tests.txt | grep -E "passed|failed|skipped"

echo "=== VALIDATION ==="
tail -50 phase2b_validation_tests.txt | grep -E "passed|failed|skipped"
```

### 5b. Detailed Failure Comparison
```bash
# Extract validation failures
grep "FAILED" phase2b_validation_tests.txt > phase2b_validation_failures.txt

# Compare failure counts
echo "Baseline failures: $(wc -l < phase2b_baseline_failures.txt)"
echo "Validation failures: $(wc -l < phase2b_validation_failures.txt)"

# Find NEW failures (not in baseline)
comm -13 <(sort phase2b_baseline_failures.txt) \
         <(sort phase2b_validation_failures.txt) > new_failures.txt

echo "NEW failures introduced: $(wc -l < new_failures.txt)"
```

### 5c. Decision Matrix

**If NEW failures = 0:**
```
✅ SUCCESS: Task 12 validated successfully!

Next steps:
1. Mark Tasks 12.1-12.10 complete
2. Update task list
3. Commit final state
4. Proceed to Task 13 (unused arguments)
```

**If NEW failures > 0 but < 10:**
```
⚠️  INVESTIGATE: Small number of new failures

Actions:
1. Review new_failures.txt
2. Determine if related to comment removal
3. If yes: Fix and re-validate
4. If no: Flaky tests, document and proceed
```

**If NEW failures > 10:**
```
❌ HALT: Significant new failures

Actions:
1. Review new_failures.txt in detail
2. Identify pattern (specific package, test type)
3. Likely broke something in Task 12
4. Options:
   A. Revert Task 12, investigate, fix, retry
   B. Bisect commits to find breaking change
   C. Fix failures, re-validate
```

---

## Step 6: Final Verification & Documentation

### If Validation Passed:

```bash
# 1. Final ERA001 check
ruff check packages/ tests/ --select ERA001
# Expected: All checks passed!

# 2. Update task list
# Mark Tasks 11.3, 12.1-12.10 complete

# 3. Document results
cat >> tasks/tasks-phase2-code-quality.md <<EOF
  - [x] 12.9 Run full test suite to ensure no functionality lost
    - result: ✅ Validation passed - 0 new failures
    - baseline: $(grep "FAILED" phase2b_baseline_tests.txt | wc -l) failures
    - validation: $(grep "FAILED" phase2b_validation_tests.txt | wc -l) failures
EOF

# 4. Commit task list update
git add tasks/tasks-phase2-code-quality.md
git commit -m "chore: mark Task 12.9 complete - validation passed"

# 5. Push to remote (if applicable)
git push origin feature/phase2b-cleanup
```

---

## Quick Reference

### Critical Files
- `phase2b_baseline_tests.txt` - Baseline results
- `phase2b_baseline_failures.txt` - Baseline failures (generated by analyze_baseline.sh)
- `phase2b_validation_tests.txt` - Validation results
- `phase2b_validation_failures.txt` - Validation failures
- `new_failures.txt` - NEW failures introduced by Task 12

### Scripts
- `./analyze_baseline.sh` - Analyze baseline, check conflicts
- `./execute_task12.sh` - Execute Task 12 commits
- See TASK_12_COMMIT_PLAN.md for manual approach

### Next Phase
- After Task 12: Proceed to Task 13 (unused arguments)
- See TASK_13_UNUSED_ARGS_ANALYSIS.md for strategy

---

## Summary

**Don't blindly proceed!** The analysis step is critical:

1. ✅ **Analyze** - Understand baseline failures
2. ⚠️ **Decide** - Proceed/caution/fix based on analysis
3. 🚀 **Execute** - Run Task 12 if cleared
4. ⏱️ **Validate** - Run full test suite
5. 🔍 **Compare** - Find NEW failures
6. ✅ **Document** - Record results, proceed or fix

**Key question:** Are there NEW failures after Task 12?
- If NO → Success, proceed to Task 13
- If YES → Investigate, fix, retry
