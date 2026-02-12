# Security Setup Quick Start

## 🚀 Quick Setup (5 minutes)

### Step 1: Run the Setup Script

```bash
./scripts/setup-github-security.sh
```

This interactive script will:
- Check for security issues
- Configure branch protection
- Enable Dependabot
- Show current settings

### Step 2: Configure Signed Commits (Optional but Recommended)

**Why?** Proves commits are really from you.

```bash
# Generate GPG key
gpg --full-generate-key
# Choose: RSA, 4096 bits, no expiration

# Get key ID
gpg --list-secret-keys --keyid-format=long
# Note the key ID after 'sec rsa4096/'

# Export public key
gpg --armor --export <KEY_ID>
# Copy output and add to GitHub: Settings → SSH and GPG keys → New GPG key

# Configure Git
git config --global user.signingkey <KEY_ID>
git config --global commit.gpgsign true
```

### Step 3: Verify GitHub Settings

Visit https://github.com/hamr0/aurora/settings and check:

1. **Branches** → Add rule for `main`:
   - ✅ Require pull request (1 approval)
   - ✅ Require status checks: `quality-check`, `test-suite`, `security-scan`
   - ✅ Require signed commits
   - ✅ Require linear history
   - ✅ Include administrators
   - ✅ Restrict force pushes
   - ✅ Restrict deletions

2. **Code security and analysis**:
   - ✅ Dependency graph
   - ✅ Dependabot alerts
   - ✅ Dependabot security updates
   - ✅ Secret scanning (if available)
   - ✅ Code scanning (if available)

### Step 4: Test the Protection

```bash
# Try to push directly to main (should fail)
git checkout main
echo "test" > test.txt
git add test.txt
git commit -m "test: direct push"
git push origin main
# Expected: ❌ Push declined due to branch protection

# Correct workflow (should work)
git checkout -b test/protection
git push origin test/protection
gh pr create --title "test: verify protection" --body "Testing branch protection"
# Expected: ✅ PR created, status checks run
```

### Step 5: Make Repository Public (When Ready)

Before making public:

```bash
# 1. Final security audit
./scripts/setup-github-security.sh
# Answer 'y' to pre-flight checks

# 2. Scan for secrets
pip install detect-secrets
detect-secrets scan --all-files > .secrets.baseline

# 3. Review any findings
cat .secrets.baseline

# 4. Check for sensitive files
find . -name "*.env*" -o -name "*secret*" -o -name "*credential*" -o -name "*.key"

# 5. Ensure all configs are clean
grep -r "api_key\|password\|token" . --include="*.py" --include="*.json" --include="*.yml"
```

If all clear:
1. Go to https://github.com/hamr0/aurora/settings
2. Scroll to "Danger Zone"
3. Click "Change repository visibility"
4. Select "Public"
5. Confirm

## 🤖 Claude Code Access

Claude Code will work through the standard PR workflow:

1. Claude creates a branch
2. Makes changes and commits
3. Pushes branch
4. Creates PR via `gh pr create`
5. Status checks run automatically
6. You review and merge

**Authentication**: Claude uses your local `gh` CLI authentication (already configured).

## 🔥 Emergency Bypass

If you need to bypass protection (emergency only):

```bash
# 1. Temporarily disable admin enforcement
gh api repos/hamr0/aurora/branches/main/protection \
  --method PUT \
  --field enforce_admins=false

# 2. Make critical fix
git push origin main

# 3. Re-enable immediately
gh api repos/hamr0/aurora/branches/main/protection \
  --method PUT \
  --field enforce_admins=true

# 4. Document in commit message why bypass was needed
```

## 📊 Regular Maintenance

**Weekly**: Check security alerts
```bash
gh api repos/hamr0/aurora/dependabot/alerts
```

**Monthly**: Review access
```bash
gh api repos/hamr0/aurora/collaborators
```

**Quarterly**: Audit protection
```bash
gh api repos/hamr0/aurora/branches/main/protection
```

## 🆘 Troubleshooting

### "Push declined due to branch protection"
✅ **Expected behavior!** Create a PR instead:
```bash
git checkout -b feature/my-change
git push origin feature/my-change
gh pr create
```

### "Required status checks must pass"
Check workflow status:
```bash
gh run list --branch=my-branch
gh run view <run-id>
```

### "Commit signature verification failed"
Re-configure GPG:
```bash
git config --global user.signingkey <KEY_ID>
git config --global commit.gpgsign true
```

### "Cannot merge: code owner review required"
You (hamr0) must approve the PR through GitHub UI.

## 📚 More Information

- Full guide: `.github/SECURITY_SETUP.md`
- GitHub docs: https://docs.github.com/en/code-security
- Branch protection: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches
