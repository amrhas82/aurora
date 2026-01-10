# CI Switchover Plan: Legacy → New Testing Infrastructure

**Plan Version**: 1.0
**Created**: January 6, 2026
**Status**: Ready for Execution (pending 7-day stability verification)
**Related Task**: tasks-0023 Phase 6

---

## Executive Summary

This document outlines the plan to switch from Aurora's legacy CI workflow to the new testing infrastructure created in tasks-0023. The switchover will be executed after the new CI has demonstrated **7 consecutive days of stability**.

**Current State:**
- Legacy CI: `.github/workflows/testing.yml` (primary, may be failing)
- New CI: `.github/workflows/testing-infrastructure-new.yml` (parallel, stable)
- Both running on every commit/PR

**Target State:**
- New CI: `.github/workflows/testing.yml` (primary, stable)
- Legacy CI: `.github/workflows/testing-infrastructure-legacy.yml.disabled` (archived)

**Rollback Time**: 5 minutes (rename files back)

---

## Current State

### Legacy CI Workflow

**File**: `.github/workflows/testing.yml`
**Status**: May be broken (20 consecutive failures in December 2025)
**Configuration**:
- Python versions: 3.10, 3.11, 3.12, 3.13
- Test command: `pytest tests/`
- Coverage: May not be measuring correctly
- Markers: May use old marker strategy

**Issues**:
- May have import errors (73 files broken in December)
- May not collect all tests properly
- Coverage measurement may be inaccurate
- Marker strategy may be outdated (14 markers)

### New CI Workflow

**File**: `.github/workflows/testing-infrastructure-new.yml`
**Status**: Stable (running since January 5, 2026)
**Configuration**:
- Python versions: 3.10, 3.11, 3.12, 3.13
- Test command: `pytest -m "not ml and not real_api" --cov=packages --cov-report=xml`
- Coverage: Measured and uploaded to artifacts
- Markers: Uses new strategy (ml, slow, real_api)

**Improvements**:
- ✅ All tests collect successfully (3069 tests)
- ✅ Correct import patterns (aurora_*)
- ✅ Proper marker usage (3 essential markers)
- ✅ Coverage measured accurately (81.93%)
- ✅ Skips expensive tests (ml, real_api) appropriately

---

## Switchover Criteria

The new CI must meet **all** of the following criteria before switchover:

### 1. Stability Verification

- [ ] **7 consecutive days** of passing CI on new workflow
  - Monitor: GitHub Actions dashboard
  - Check: All Python versions (3.10-3.13) passing
  - No intermittent failures
  - No flaky tests

### 2. Test Coverage

- [ ] **Test count stable**: 3069 ± 50 tests collected
- [ ] **Pass rate ≥97%**: At least 2972/3069 tests passing
- [ ] **Coverage ≥80%**: Measured coverage at or above 80%
- [ ] **No collection errors**: `pytest --collect-only` succeeds

### 3. Performance

- [ ] **CI runtime acceptable**: <10 minutes per Python version
- [ ] **No significant slowdown**: Within 20% of baseline runtime
- [ ] **Resource usage reasonable**: Memory, CPU within limits

### 4. Team Validation

- [ ] **Team review**: All team members reviewed and approved plan
- [ ] **No blocking concerns**: No unresolved issues from team
- [ ] **Communication sent**: Team notified of upcoming switchover

### 5. Documentation Complete

- [ ] **All Phase 5 docs created**: TEST_MIGRATION_CHECKLIST.md, TESTING.md updates, ROOT_CAUSE_ANALYSIS, this document
- [ ] **Pre-commit hooks installed**: Hooks working and tested
- [ ] **Rollback plan tested**: Dry-run of rollback procedure successful

---

## Pre-Switchover Checklist

### 1. Verify 7-Day Stability (Days 1-7)

**Daily Monitoring Task** (10 minutes per day):

```bash
# Check GitHub Actions for new CI workflow status
# For each day, record:
# - Date:
# - New CI status: PASS / FAIL
# - Python 3.10: PASS / FAIL
# - Python 3.11: PASS / FAIL
# - Python 3.12: PASS / FAIL
# - Python 3.13: PASS / FAIL
# - Test count: _____
# - Pass rate: _____%
# - Coverage: _____%
# - Notes: Any failures or anomalies
```

**Example Tracking Table**:

| Date | New CI | Py 3.10 | Py 3.11 | Py 3.12 | Py 3.13 | Tests | Pass Rate | Coverage | Notes |
|------|--------|---------|---------|---------|---------|-------|-----------|----------|-------|
| Jan 6 | ✅ | ✅ | ✅ | ✅ | ✅ | 3069 | 97.2% | 81.93% | Baseline |
| Jan 7 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ____ | ____% | ____% | _____ |
| Jan 8 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ____ | ____% | ____% | _____ |
| Jan 9 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ____ | ____% | ____% | _____ |
| Jan 10 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ____ | ____% | ____% | _____ |
| Jan 11 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ____ | ____% | ____% | _____ |
| Jan 12 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ____ | ____% | ____% | _____ |

**Passing Criteria**: All cells ✅ for 7 consecutive days

### 2. Stakeholder Approval

**Required Approvers**:
- [ ] Technical Lead
- [ ] Team members (all who will use new CI)
- [ ] Product Owner (if applicable)

**Approval Method**:
- Present this document + 7-day stability report
- Request explicit approval (email, Slack, meeting)
- Document approval date and approver

### 3. Team Communication

**Before Switchover** (1 day before):

```
Subject: CI Switchover Tomorrow - New Testing Infrastructure

Team,

We will be switching to the new CI testing infrastructure tomorrow at [TIME].

What's Changing:
- Workflow file: testing-infrastructure-new.yml → testing.yml
- No behavior changes (already running in parallel for 7+ days)
- Legacy CI will be disabled but kept for 30 days

Impact:
- Zero downtime (switchover takes ~5 minutes)
- All PRs will use new CI automatically
- No action required from team

What to Watch For:
- CI status checks on your PRs (should be same as before)
- Any unexpected failures (report immediately)

Rollback Plan:
- If issues arise, we can rollback in 5 minutes
- Legacy CI will be re-enabled immediately

Questions? Reply to this thread or ping in #engineering.

Thanks,
[Your Name]
```

---

## Switchover Procedure

### Step 1: Final Verification (5 minutes)

**Immediately before switchover:**

```bash
# Check new CI status
gh run list --workflow=testing-infrastructure-new.yml --limit 5
# Verify: All recent runs passing

# Check test count
gh run view [latest-run-id] --log | grep "collected"
# Verify: 3069 ± 50 tests collected

# Check coverage
gh run view [latest-run-id] --log | grep "TOTAL"
# Verify: Coverage ≥80%
```

**Abort if**:
- Any recent runs failed
- Test count significantly different
- Coverage dropped below 80%
- Team member raises last-minute concern

### Step 2: Backup Legacy CI (2 minutes)

```bash
cd /home/hamr/PycharmProjects/aurora

# Create backup branch
git checkout -b ci-switchover-backup-$(date +%Y%m%d)
git push origin ci-switchover-backup-$(date +%Y%m%d)

# Create working branch
git checkout -b ci-switchover
```

### Step 3: Rename Workflow Files (3 minutes)

```bash
cd .github/workflows

# Disable legacy CI (rename with .disabled suffix)
git mv testing.yml testing-infrastructure-legacy.yml.disabled

# Promote new CI to primary (remove -new suffix)
git mv testing-infrastructure-new.yml testing.yml

# Verify files renamed correctly
ls -la
# Should see:
# - testing.yml (was testing-infrastructure-new.yml)
# - testing-infrastructure-legacy.yml.disabled (was testing.yml)

# Check file contents haven't changed
git diff --cached testing.yml
# Should show only the rename, no content changes
```

### Step 4: Update Branch Protection Rules (5 minutes)

**GitHub Web UI**:

1. Go to: `Settings → Branches → Branch protection rules → [main/master]`
2. Find: **Require status checks to pass before merging**
3. Update required checks:
   - ✅ Remove: Old CI check names (if different)
   - ✅ Add: `test (3.10, ubuntu-latest)`
   - ✅ Add: `test (3.11, ubuntu-latest)`
   - ✅ Add: `test (3.12, ubuntu-latest)`
   - ✅ Add: `test (3.13, ubuntu-latest)`
4. Save changes

**Verify**:
```bash
# Check branch protection via API
gh api repos/:owner/:repo/branches/main/protection
# Verify: Required checks updated
```

### Step 5: Commit and Push (2 minutes)

```bash
# Stage changes
git add .github/workflows/

# Commit with clear message
git commit -m "chore(ci): switch to new testing infrastructure

- Rename testing-infrastructure-new.yml → testing.yml
- Disable legacy CI: testing.yml → testing-infrastructure-legacy.yml.disabled
- All tests passing for 7+ consecutive days
- Coverage stable at 81.93%
- Pre-commit hooks in place

Related: tasks-0023 Phase 6"

# Push to remote
git push origin ci-switchover

# Create PR
gh pr create \
  --title "CI Switchover: Enable New Testing Infrastructure" \
  --body "$(cat <<'EOF'
## Summary
Switch from legacy CI to new testing infrastructure after 7+ days of stability.

## Stability Evidence
- ✅ 7 consecutive days passing (Jan 6-12, 2026)
- ✅ All Python versions (3.10-3.13) stable
- ✅ 3069 tests, 97.2% pass rate
- ✅ 81.93% coverage
- ✅ Pre-commit hooks installed

## Changes
- `testing-infrastructure-new.yml` → `testing.yml` (now primary)
- `testing.yml` → `testing-infrastructure-legacy.yml.disabled` (archived)

## Rollback Plan
If issues arise:
1. Revert this PR
2. Re-enable legacy CI (rename back)
3. Investigate issues
4. Re-attempt switchover when stable

## Checklist
- [x] 7-day stability verified
- [x] Team notified
- [x] Branch protection rules updated
- [x] Rollback plan tested

Related: tasks-0023 Phase 6
EOF
)"

# Get PR number
PR_NUMBER=$(gh pr list --head ci-switchover --json number --jq '.[0].number')
echo "PR created: #$PR_NUMBER"
```

### Step 6: Merge PR (1 minute)

```bash
# Wait for CI to pass on PR (should pass - using new CI already)
gh pr checks $PR_NUMBER --watch

# Once passing, merge
gh pr merge $PR_NUMBER --squash --delete-branch

# Verify merge
git checkout main
git pull
ls .github/workflows/
# Should show testing.yml (new CI) and testing-infrastructure-legacy.yml.disabled
```

**Switchover Complete!** ✅

---

## Post-Switchover Monitoring

### First 24 Hours (Critical)

**Hourly Checks** (5 minutes each):

```bash
# Check all recent PRs using new CI
gh pr list --limit 10 --json number,title,statusCheckRollup

# For each PR, verify:
# - CI is running (not stuck)
# - Tests are passing (or failing for legitimate reasons)
# - No complaints from team members
```

**What to Watch For**:
- ❌ CI not triggering on new PRs
- ❌ Unexpected test failures (not in new CI before)
- ❌ CI timeouts or hangs
- ❌ Team members reporting issues

**Action if Issues Found**:
- Immediately execute rollback procedure (see below)
- Investigate root cause
- Fix issues before re-attempting switchover

### First 7 Days (Standard)

**Daily Checks** (10 minutes each):

```bash
# Generate daily CI status report
gh run list --workflow=testing.yml --created=$(date -d '1 day ago' --iso-8601) \
  --json conclusion,createdAt,name | jq .

# Metrics to track:
# - Pass rate: _____%
# - Failure rate: _____%
# - Average runtime: _____ minutes
# - Any new issues reported: _____
```

**Success Criteria** (after 7 days):
- [ ] Pass rate ≥95% (some failures expected from real bugs)
- [ ] No systematic issues (flaky tests, timeouts, etc.)
- [ ] No team complaints
- [ ] No increase in test runtime
- [ ] Coverage stable

### After 30 Days: Cleanup

**Schedule Reminder** (30 days from switchover):

```bash
# Calendar reminder: Delete legacy CI file

# On Day 30:
cd /home/hamr/PycharmProjects/aurora
git checkout -b cleanup-legacy-ci
git rm .github/workflows/testing-infrastructure-legacy.yml.disabled
git commit -m "chore(ci): remove legacy testing infrastructure after 30-day safety period"
git push origin cleanup-legacy-ci
gh pr create --title "Cleanup: Remove Legacy CI" --body "Safe to delete after 30 days with no issues"
```

---

## Rollback Procedure

**When to Rollback**:
- Any systematic issues with new CI
- Increase in test failures (not due to code bugs)
- CI timeouts or hangs
- Team blocking issues
- Any concerns from stakeholders

**Rollback Time**: 5 minutes

### Emergency Rollback Steps

```bash
# Step 1: Re-enable legacy CI (1 minute)
cd /home/hamr/PycharmProjects/aurora/.github/workflows
git checkout -b emergency-rollback-ci

git mv testing.yml testing-infrastructure-new.yml
git mv testing-infrastructure-legacy.yml.disabled testing.yml

git add .
git commit -m "revert(ci): emergency rollback to legacy CI - investigating issues"
git push origin emergency-rollback-ci

# Step 2: Create emergency PR (1 minute)
gh pr create \
  --title "EMERGENCY: Rollback to Legacy CI" \
  --body "Rolling back to legacy CI due to issues. Will investigate and re-attempt switchover." \
  --label "priority:critical"

# Step 3: Force merge (if needed) (1 minute)
PR_NUMBER=$(gh pr list --head emergency-rollback-ci --json number --jq '.[0].number')
# Get admin approval or use force merge if authorized
gh pr merge $PR_NUMBER --admin --squash

# Step 4: Verify rollback (1 minute)
git checkout main
git pull
ls .github/workflows/
# Should show testing.yml (legacy) and testing-infrastructure-new.yml (new)

# Step 5: Update branch protection (1 minute)
# Go to GitHub UI, restore old required checks if needed

# Step 6: Notify team (immediately)
# Send message:
# "We've rolled back to legacy CI due to [ISSUE]. New CI disabled. Investigating."
```

**Post-Rollback Actions**:
1. **Investigate root cause** (why did new CI fail?)
2. **Fix issues** in testing-infrastructure-new.yml
3. **Test fixes** on test branch
4. **Re-run 7-day stability** period
5. **Re-attempt switchover** when stable

---

## Verification Commands

### Check CI Status

```bash
# List recent CI runs
gh run list --workflow=testing.yml --limit 10

# View specific run
gh run view [run-id]

# View logs for specific run
gh run view [run-id] --log

# Watch live run
gh run watch [run-id]
```

### Check Test Metrics

```bash
# Download coverage artifacts
gh run download [run-id] --name coverage-report

# View coverage summary
cat coverage.xml | grep '<coverage'
# Example output: <coverage line-rate="0.8193" ...>

# Count tests from logs
gh run view [run-id] --log | grep "collected"
# Example output: collected 3069 items
```

### Check PR Status

```bash
# List recent PRs with CI status
gh pr list --limit 10 --json number,title,statusCheckRollup

# Check specific PR
gh pr checks [pr-number]

# View PR CI details
gh pr view [pr-number] --json statusCheckRollup
```

---

## Communication Templates

### Before Switchover (1 day before)

**Subject**: CI Switchover Tomorrow - New Testing Infrastructure

*(See "Team Communication" section above)*

### After Switchover (immediately)

**Subject**: ✅ CI Switchover Complete - New Testing Infrastructure Live

```
Team,

The CI switchover is complete! All PRs now use the new testing infrastructure.

What Changed:
- Workflow file: testing-infrastructure-new.yml → testing.yml
- Legacy CI disabled (kept as backup for 30 days)

Current Status:
- ✅ All tests passing
- ✅ Coverage: 81.93%
- ✅ All Python versions working (3.10-3.13)

What to Expect:
- Same CI behavior as last 7 days (already running in parallel)
- No action required from you
- Report any issues immediately

Monitoring:
- I'll be monitoring CI closely for the next 24 hours
- Daily checks for the next 7 days

Questions or Issues?
- Ping me in #engineering or reply to this thread
- If urgent, use @mention in Slack

Thanks for your patience during the migration!

[Your Name]
```

### If Rollback Needed (immediately)

**Subject**: 🚨 EMERGENCY: CI Rolled Back - Investigating

```
Team,

We've rolled back to the legacy CI due to [SPECIFIC ISSUE].

What Happened:
- [Brief description of issue]
- Detected at [TIME]
- Rollback completed at [TIME]

Current Status:
- ✅ Legacy CI re-enabled
- ✅ All PRs should work normally
- 🔍 Investigating root cause

Impact:
- Your existing PRs should continue working
- May need to re-run CI on some PRs

Next Steps:
- Investigating root cause
- Will fix and re-test new CI
- Will notify when ready to re-attempt switchover

Apologies for the disruption. We'll get this sorted quickly.

[Your Name]
```

---

## Success Metrics

### Immediate Success (24 hours)

- [ ] All PRs use new CI workflow
- [ ] No increase in test failures (vs last 7 days)
- [ ] No CI timeouts or hangs
- [ ] No team complaints
- [ ] Coverage stable

### Short-Term Success (7 days)

- [ ] Pass rate ≥95%
- [ ] No systematic issues identified
- [ ] Team satisfied with CI performance
- [ ] No rollback required
- [ ] CI runtime stable

### Long-Term Success (30 days)

- [ ] Legacy CI safely deleted
- [ ] New CI is "normal" (no longer "new")
- [ ] Team confidence in testing infrastructure
- [ ] Test infrastructure improvements continue (Phase 7+)

---

## Related Documents

- **Migration Checklist**: `/docs/TEST_MIGRATION_CHECKLIST.md` - Step-by-step guide for future refactorings
- **Testing Guide**: `/docs/TESTING.md` - Test classification criteria, import patterns, lessons learned
- **Root Cause Analysis**: `/docs/ROOT_CAUSE_ANALYSIS_TESTING_BREAKAGE_2025.md` - Detailed RCA of 2025 breakage
- **Technical Debt**: `/docs/TESTING_TECHNICAL_DEBT.md` - Current status, coverage metrics, remaining issues
- **tasks-0023**: `/tasks/tasks-0023-prd-testing-infrastructure-overhaul.md` - Full task breakdown and progress

---

## Appendix: Risk Assessment

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| New CI fails after switchover | Low (7 days stable) | High | Fast rollback (<5 min) |
| Branch protection misconfigured | Medium | Medium | Verify before merge |
| Team confusion about changes | Low | Low | Clear communication |
| Rollback needed during busy period | Low | Medium | Monitor first 24h closely |
| Legacy CI needed after deletion | Very Low | Low | Keep for 30 days |

### Risk Mitigation

1. **7-Day Stability**: Reduces probability of post-switchover failures
2. **Fast Rollback**: Limits impact if issues arise
3. **Parallel Running**: New CI already proven in production
4. **Clear Communication**: Reduces team confusion
5. **30-Day Grace Period**: Allows safe deletion of legacy CI

**Overall Risk Level**: **LOW** ✅

---

**Document Version**: 1.0
**Created By**: Aurora Team
**Date**: January 6, 2026
**Next Review**: After switchover completion (estimated January 13-15, 2026)
