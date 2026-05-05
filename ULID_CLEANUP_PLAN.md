# ULID Binary Artifact Cleanup Plan

## Current State
- **File:** `ulid` (12MB PostScript document)
- **Location:** Repository root
- **Status:** Removed from current tree via `git rm ulid`
- **Git History:** Present in commit 30a161f "Remove unused modules and stale scaffolding"
- **.gitignore:** Already listed at line 163

## Issue
The 12MB binary file `ulid` exists in git history and bloats the repository. While it has been removed from the current working tree, it remains in git history, which:
- Bloates the repository size for all clones
- Wastes bandwidth on fetch/pull operations
- Contains no useful code (ImageMagick artifact)

## Recommended History Rewrite
To fully remove `ulid` from git history, use git-filter-repo:

```bash
# Create backup branch
git branch backup/pre-ulid-cleanup

# Remove ulid from all history
git filter-repo --path ulid --invert-paths

# Force push (ONLY AFTER TEAM COORDINATION)
git push origin main --force
```

## Alternative: BFG Repo-Cleaner
```bash
# Create backup branch
git branch backup/pre-ulid-cleanup

# Remove ulid from history
bfg --delete-files ulid

# Cleanup refs
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (ONLY AFTER TEAM COORDINATION)
git push origin main --force
```

## Safety Precautions
1. **DO NOT force-push without explicit authorization** from repo owner
2. Coordinate with team members before history rewrite
3. All contributors will need to re-clone or perform complex recovery operations
4. Backup branch `backup/pre-ulid-cleanup` provides recovery option

## Current Status
- ✅ Removed from working tree
- ✅ Already in .gitignore
- ⏳ History rewrite pending authorization
- ⏳ Force-push pending authorization

## References
- All code references to "ulid" are for the python-ulid package, not this binary file
- The binary file is an ImageMagick artifact with no code value
