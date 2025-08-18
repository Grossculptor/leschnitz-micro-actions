# Revert Instructions - Fallback Text Fix

## Current Setup
- **Stable Version Tag**: `v1.0-stable-before-fallback-fix` (created from origin/main at commit d2f8f92)
- **Fix Branch**: `fix-fallback-text-issue` (contains the fallback text improvements)
- **Main Branch**: Currently at d2f8f92 (stable, without the new fixes)

## What Was Fixed
The `fix-fallback-text-issue` branch contains:
1. Improved fallback mechanism in `scripts/pipeline.py` to prevent raw Polish RSS text from appearing
2. Fixed the problematic micro action (hash: 9518f5f24b98ca363fb22bda5e6ac70eb201048b)
3. New monitoring script: `scripts/detect_fallback_items.py`
4. Fixed single item script: `scripts/fix_single_item.py`

## Testing the Fixes
To test the fixes before merging to main:
```bash
# Switch to the fix branch
git checkout fix-fallback-text-issue

# Test the pipeline locally
source .env && export GROQ_API_KEY && python3 scripts/pipeline.py

# Check for problematic items
python3 scripts/detect_fallback_items.py
```

## Merging the Fixes (if tests pass)
```bash
# Switch to main branch
git checkout main

# Pull latest changes
git pull origin main

# Merge the fixes
git merge fix-fallback-text-issue

# Push to GitHub
git push origin main
```

## Reverting if Problems Occur

### Option 1: Quick Revert to Tagged Version
```bash
# Reset main to the stable tag
git checkout main
git reset --hard v1.0-stable-before-fallback-fix
git push origin main --force
```

### Option 2: Revert Using GitHub Web Interface
1. Go to: https://github.com/Grossculptor/leschnitz-micro-actions
2. Click on "Releases" or "Tags"
3. Find `v1.0-stable-before-fallback-fix`
4. Download the source code from that tag

### Option 3: Create a Revert Commit
```bash
# Find the commit hash of the merge (if you merged the fixes)
git log --oneline -5

# Revert the merge commit
git revert -m 1 <merge-commit-hash>
git push origin main
```

## Viewing the Differences
To see what changes are in the fix branch:
```bash
git diff main..fix-fallback-text-issue
```

To see changed files only:
```bash
git diff --name-only main..fix-fallback-text-issue
```

## Pull Request Option
Instead of merging directly, you can create a Pull Request:
1. Visit: https://github.com/Grossculptor/leschnitz-micro-actions/pull/new/fix-fallback-text-issue
2. Review the changes
3. Test thoroughly
4. Merge via GitHub interface

## Important Files to Check After Any Changes
- `docs/data/projects.json` - The main data file displayed on the website
- `scripts/pipeline.py` - The main pipeline that processes RSS feeds
- GitHub Actions logs at: https://github.com/Grossculptor/leschnitz-micro-actions/actions

## Support
If issues persist after reverting:
1. Check GitHub Actions to ensure the scraping workflow is running
2. Verify the GROQ_API_KEY secret is still set in repository settings
3. Check that feeds.txt still contains valid RSS URLs