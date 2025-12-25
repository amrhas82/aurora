# Security Migration Checklist - AURORA Public Repository

## ✅ Completed Setup

The following security configurations have been created:

### 1. Documentation
- ✅ `.github/SECURITY_SETUP.md` - Comprehensive security guide
- ✅ `.github/SECURITY_QUICK_START.md` - Quick reference for setup
- ✅ `SECURITY_MIGRATION_CHECKLIST.md` - This checklist

### 2. GitHub Configuration Files
- ✅ `.github/CODEOWNERS` - Automatic review assignment (@amrhas82)
- ✅ `.github/workflows/required-checks.yml` - CI/CD quality gates
- ✅ `scripts/setup-github-security.sh` - Automated setup script

### 3. Pre-Flight Security Audit
- ✅ No `.env` files found in repository
- ✅ No hardcoded secrets detected (only documentation examples)
- ✅ `.gitignore` properly configured for sensitive files
- ✅ All API key references use environment variables

## 📋 Action Items (To Complete Before Going Public)

### Phase 1: Apply GitHub Settings (15 minutes)

#### Step 1.1: Run Setup Script
```bash
cd /home/hamr/PycharmProjects/aurora
./scripts/setup-github-security.sh
```

Answer 'y' to all prompts to:
- Run pre-flight checks
- View current settings
- Configure branch protection
- Enable security features

#### Step 1.2: Manual GitHub Web Configuration

Some settings require manual configuration via GitHub web interface:

1. **Branch Protection** (Settings → Branches → Add rule for `main`):
   - Branch name pattern: `main`
   - ✅ Require a pull request before merging
     - Required approvals: 1
     - ✅ Dismiss stale reviews
     - ✅ Require review from Code Owners
   - ✅ Require status checks to pass before merging
     - ✅ Require branches to be up to date
     - Status checks (add after first workflow run):
       - `quality-check`
       - `test-suite`
       - `security-scan`
   - ✅ Require signed commits (optional but recommended)
   - ✅ Require linear history
   - ✅ Do not allow bypassing the above settings
     - ✅ Include administrators
   - ✅ Restrict who can push to matching branches
     - Add: @amrhas82
   - ✅ Allow force pushes: Disabled
   - ✅ Allow deletions: Disabled

2. **Security & Analysis** (Settings → Code security and analysis):
   - ✅ Dependency graph (auto-enabled for public repos)
   - ✅ Dependabot alerts
   - ✅ Dependabot security updates
   - ✅ Grouped security updates
   - ✅ Secret scanning (free for public repos)
   - ✅ Secret scanning push protection
   - ⚠️ Code scanning (requires setup - optional)

3. **General Settings** (Settings → General):
   - Features to enable:
     - ✅ Issues
     - ✅ Projects (if desired)
     - ☐ Discussions (recommended for public repos)
     - ✅ Actions
   - Pull Requests:
     - ✅ Allow squash merging
     - ✅ Allow rebase merging
     - ☐ Allow merge commits (your preference)
     - ✅ Automatically delete head branches

### Phase 2: Commit Security Files (5 minutes)

```bash
# Check what we're adding
git status

# Should show:
# - .github/CODEOWNERS
# - .github/workflows/required-checks.yml
# - .github/SECURITY_SETUP.md
# - .github/SECURITY_QUICK_START.md
# - scripts/setup-github-security.sh
# - SECURITY_MIGRATION_CHECKLIST.md

# Add and commit
git add .github/ scripts/setup-github-security.sh SECURITY_MIGRATION_CHECKLIST.md
git commit -m "security: add GitHub security configuration for public repository

- Add branch protection documentation
- Create CODEOWNERS file for review requirements
- Add GitHub Actions workflow for quality checks
- Include automated setup script
- Add security migration checklist

Prepares repository for public visibility with:
- Branch protection rules
- Required status checks
- Code owner reviews
- Automated security scanning
"

# Push to main (this should work before branch protection is enabled)
git push origin main
```

### Phase 3: Configure GPG Signing (Optional, 10 minutes)

**Benefits**: Verifies commit authenticity, prevents impersonation

```bash
# 1. Generate GPG key
gpg --full-generate-key
# Select: (1) RSA and RSA
# Key size: 4096
# Expiration: 0 (no expiration) or your preference
# Enter your name and email (must match Git config)

# 2. Get your key ID
gpg --list-secret-keys --keyid-format=long
# Look for the line like: sec rsa4096/ABCD1234EFGH5678
# ABCD1234EFGH5678 is your key ID

# 3. Export public key
gpg --armor --export ABCD1234EFGH5678
# Copy the entire output (including BEGIN/END lines)

# 4. Add to GitHub
# Go to: https://github.com/settings/keys
# Click "New GPG key"
# Paste the exported public key

# 5. Configure Git
git config --global user.signingkey ABCD1234EFGH5678
git config --global commit.gpgsign true

# 6. Test signing
echo "test" > test.txt
git add test.txt
git commit -S -m "test: signed commit"
# Should succeed without errors
git log --show-signature -1
# Should show "Good signature"

# Clean up test
git reset HEAD~1
rm test.txt
```

### Phase 4: Test Branch Protection (5 minutes)

**IMPORTANT**: Only test this AFTER enabling branch protection on GitHub!

```bash
# Test 1: Try direct push to main (should fail)
git checkout main
echo "# Test" >> README.md
git add README.md
git commit -m "test: direct push should fail"
git push origin main
# ❌ Expected: "remote: error: GH006: Protected branch update failed"

# Revert test commit
git reset HEAD~1
git checkout README.md

# Test 2: PR workflow (should succeed)
git checkout -b test/branch-protection
echo "# Security Test" > .github/test.md
git add .github/test.md
git commit -m "test: verify branch protection and CI"
git push origin test/branch-protection

# Create PR
gh pr create \
  --title "test: verify security configuration" \
  --body "Testing:
- Branch protection rules
- Status checks (quality-check, test-suite, security-scan)
- Code owner reviews
- Workflow automation

This PR will be closed after verification."

# ✅ Expected: PR created, status checks run automatically

# After checks pass and you review:
# - Go to PR on GitHub
# - Review and approve
# - Merge (squash or rebase)
# - Delete branch automatically

# Clean up locally
git checkout main
git pull origin main
git branch -d test/branch-protection
```

### Phase 5: Final Pre-Public Audit (10 minutes)

```bash
# 1. Comprehensive secret scan
pip install detect-secrets
detect-secrets scan --all-files > .secrets.baseline
cat .secrets.baseline
# Review any findings - should be only false positives

# 2. Check for any forgotten sensitive files
find . -type f \( \
  -name "*.key" -o \
  -name "*.pem" -o \
  -name "*.p12" -o \
  -name "*.pfx" -o \
  -name "*secret*" -o \
  -name "*credential*" \
\) -not -path "./.git/*" -not -path "./venv/*"
# Should return nothing or only expected files

# 3. Verify no hardcoded credentials
grep -r "password\s*=\s*['\"]" packages/ --include="*.py" | grep -v "test\|example\|mock"
grep -r "api_key\s*=\s*['\"]" packages/ --include="*.py" | grep -v "test\|example\|mock"
# Should return nothing

# 4. Check LICENSE file exists
ls -la LICENSE* || echo "⚠️  Consider adding a LICENSE file"

# 5. Review README for any private information
cat README.md | grep -iE "internal|private|confidential|secret"
# Should return nothing concerning

# 6. Verify all workflows are valid
gh workflow list
# Should show: Required Quality Checks

# 7. Check all status checks pass on main
gh run list --branch=main --limit 1
# Should show: ✓ (if commits exist with workflows)
```

### Phase 6: Make Repository Public (2 minutes)

**⚠️ FINAL CHECKLIST BEFORE GOING PUBLIC:**

- ✅ All security configurations applied
- ✅ Branch protection enabled and tested
- ✅ GitHub Actions workflow running successfully
- ✅ No secrets or sensitive data in repository
- ✅ CODEOWNERS file in place
- ✅ LICENSE file exists (add if missing)
- ✅ README.md is comprehensive and up-to-date
- ✅ All documentation reviewed

**Make it public:**

1. Navigate to: https://github.com/amrhas82/aurora/settings
2. Scroll to **Danger Zone**
3. Click **Change repository visibility**
4. Select **Public**
5. Type repository name to confirm: `aurora`
6. Click **I understand, change repository visibility**

**Immediately after making public:**

```bash
# 1. Verify security features are active
gh api repos/amrhas82/aurora --jq '{
  visibility: .visibility,
  has_vulnerability_alerts: .has_vulnerability_alerts,
  security_and_analysis: .security_and_analysis
}'

# 2. Check branch protection is still active
gh api repos/amrhas82/aurora/branches/main/protection --jq '{
  enforce_admins: .enforce_admins.enabled,
  required_reviews: .required_pull_request_reviews.required_approving_review_count
}'

# 3. Monitor for any unexpected activity
gh api repos/amrhas82/aurora/events | head -20
```

## 🔄 Ongoing Maintenance

### Weekly
```bash
# Check for security alerts
gh api repos/amrhas82/aurora/dependabot/alerts

# Review recent activity
gh api repos/amrhas82/aurora/events --paginate | head -50
```

### Monthly
```bash
# Audit collaborators (should only be you)
gh api repos/amrhas82/aurora/collaborators

# Review branch protection
gh api repos/amrhas82/aurora/branches/main/protection
```

### Quarterly
```bash
# Full security audit
./scripts/setup-github-security.sh
# Run all checks

# Review and rotate PATs
gh auth status
```

## 🤖 Claude Code Workflow (Post-Public)

Claude Code will work seamlessly with these protections:

```bash
# Claude's typical workflow:
1. Create feature branch: `git checkout -b feature/claude-changes`
2. Make changes and commit: `git commit -m "feat: description"`
3. Push branch: `git push origin feature/claude-changes`
4. Create PR: `gh pr create --title "..." --body "..."`
5. Wait for status checks ✅
6. You review and merge 👍
```

**Claude cannot**:
- Push directly to `main` (blocked by branch protection)
- Bypass status checks (enforced by GitHub)
- Merge without approval (requires your review)

**Claude can**:
- Create branches ✅
- Push to feature branches ✅
- Create pull requests ✅
- Run tests locally ✅

## 📞 Support

If you encounter issues:

1. Check: `.github/SECURITY_SETUP.md` (comprehensive guide)
2. Quick reference: `.github/SECURITY_QUICK_START.md`
3. GitHub docs: https://docs.github.com/en/code-security
4. Re-run setup: `./scripts/setup-github-security.sh`

## 🎯 Success Criteria

You'll know everything is working when:

- ✅ Direct pushes to `main` are blocked
- ✅ PR workflow succeeds with automated checks
- ✅ Status checks run automatically on PRs
- ✅ Code owner review is required (@amrhas82)
- ✅ Dependabot alerts are active
- ✅ Secret scanning catches any accidental pushes
- ✅ Repository is public and secure

---

**Current Status**: Files created, ready for Phase 1 execution

**Estimated Time**: ~45 minutes total (excluding optional GPG setup)

**Next Action**: Run `./scripts/setup-github-security.sh`
