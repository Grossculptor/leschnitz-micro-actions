# CLAUDE_HISTORY.md

This file contains detailed session histories from the Leschnitz Micro Actions project. These records are preserved for reference but moved here to keep CLAUDE.md under 30k characters for better performance.

## Session History & Known Issues (2025-08-15)

### Critical API Fix Applied
- **Problem**: Groq API returned HTTP 403 Forbidden due to Cloudflare blocking Python's urllib library
- **Solution**: Replaced urllib with requests library in pipeline.py (commit 56f480e)
- **Model**: moonshotai/kimi-k2-instruct confirmed working
- **API Key**: Stored in .env file locally, needs to be in GitHub Secrets for production

### GitHub Secrets Required (Base64 encoded)
- GROQ_API_KEY: Your Groq API key
- SYSTEM_PROMPT: Base64 encoded artistic prompt (see secrets/SYSTEM_PROMPT.local.txt)

### Repository Information
- GitHub: https://github.com/Grossculptor/leschnitz-micro-actions.git
- GitHub Pages: Auto-deployed from /docs directory
- Actions: Scraping workflow runs every 6 hours

### Important Notes
- NEVER use urllib for Groq API calls - Cloudflare blocks it
- Always use requests library with User-Agent header
- The moonshotai/kimi-k2-instruct model is the correct one
- System prompt must be base64 encoded for GitHub Secrets to handle special characters

## Session History (2025-08-16) - MAJOR UPDATES

### Overview of Today's Work
Successfully removed all DATAsculptor references, fixed frontend display issues, and moved sensitive content rules from public code to secret prompt for security.

### Major Changes Implemented

#### 1. Fixed Frontend Display Issues
- **Removed expand buttons**: Modified app.js to remove all expand button logic
- **Full text display**: Updated styles.css to remove max-height restrictions
- **Source link repositioned**: Moved source link to same line as date/hash metadata
- **Result**: All 166 micro actions now display full text immediately without truncation

#### 2. Removed All DATAsculptor References  
- **Problem**: 63 items contained "DATAsculptor" against new prompt guidelines
- **Solution**: Created fix_datasculptor.py utility to clean all references
- **Result**: All content now follows new artistic prompt system without DATAsculptor mentions

#### 3. Moved Generation Rules to Secret Prompt (SECURITY FIX)
- **Problem**: Artistic and political directives exposed in open source pipeline.py
- **Solution**: Moved ALL content rules to SYSTEM_PROMPT.local.txt, simplified pipeline.py
- **Details**: Pipeline.py now only contains technical JSON requirements
- **Result**: Sensitive content rules now hidden in GitHub Secrets, not visible in public repo

#### 4. Added Full Regeneration Capability
- **Added**: --regenerate flag to pipeline.py for regenerating all existing content
- **Added**: regenerate.yml GitHub workflow for manual regeneration with confirmation
- **Function**: regenerate_existing() processes all 166 items with new prompt
- **Result**: Can regenerate entire website content via GitHub Actions

### Scripts Created Today
- `scripts/fix_datasculptor.py`: Quick removal of DATAsculptor references
- `scripts/regenerate_all_content.py`: Full regeneration with new prompt (standalone)
- `scripts/regenerate_batch.py`: Batch processing for API rate limits
- `scripts/test_api.py`: Direct API connectivity testing

### Updated System Prompt
The new SYSTEM_PROMPT.local.txt now contains:
- All generation rules previously in pipeline.py
- Relevance classification rules
- JSON format specifications
- Atmospheric and sensual language guidelines
- Alternative terms for colonial references

### Latest Base64 Encoded Prompt
Use `python3 scripts/encode_prompt.py` to generate. Last generated: 3980 characters

### Current Commands
```bash
# Regular pipeline run
python scripts/pipeline.py

# Regenerate all existing content
python scripts/pipeline.py --regenerate

# Encode system prompt for GitHub
python3 scripts/encode_prompt.py

# Fix DATAsculptor references
python3 scripts/fix_datasculptor.py
```

### Next Steps Required
1. Update SYSTEM_PROMPT in GitHub Secrets with latest base64 encoding
2. Go to Actions → "Regenerate All Content" workflow
3. Run with confirmation "yes" to regenerate all 166 items
4. Monitor for completion

### Important Reminders
- All content generation rules now in secret prompt, NOT in code
- Frontend has NO expand buttons - everything displays in full
- Pipeline merges with existing data, never overwrites
- Use requests library for API calls, never urllib

## Critical Bug Fix History (2025-08-16)

### Pipeline Overwriting Bug
**Problem**: Pipeline was completely replacing projects.json instead of merging, causing website to only show latest 2 entries instead of all 147.

**Root Cause**: Line 359 in pipeline.py was doing:
```python
(DOCS / "projects.json").write_text(json.dumps(micros, ...))  # BAD - overwrites!
```

**Solution**: Load existing data first, merge, deduplicate, then save:
```python
# Load existing projects
existing = json.loads(projects_file.read_text()) if projects_file.exists() else []
# Merge with new, avoiding duplicates by hash
combined = new_micros + existing
# Sort by datetime and save
```

### Groq API Issues Fixed
1. **Timeout Issue**: Reduced timeout from 30s to 10s, disabled fulltext extraction temporarily
2. **Only 1 API call**: Was hanging on feed scraping, preventing classification/generation
3. **Using requests library**: NEVER use urllib - Cloudflare blocks it

### Important Files & Commands
- Test Groq API: `python3 scripts/test_groq.py`
- Encode system prompt for GitHub: `python3 scripts/encode_prompt.py`
- System prompt location: `secrets/SYSTEM_PROMPT.local.txt`
- Run pipeline locally: `source .env && export GROQ_API_KEY && export SYSTEM_PROMPT && python3 scripts/pipeline.py`

### GitHub Secrets Required (Base64 encoded)
- `GROQ_API_KEY`: Your Groq API key
- `SYSTEM_PROMPT`: Base64 encoded artistic prompt

### Key Lessons
- ALWAYS merge with existing data, never overwrite
- Pipeline must handle partial failures gracefully
- Use comprehensive logging to debug API issues
- Test locally before pushing to production

## Session History (2025-08-16) - EDIT FUNCTIONALITY

### Added Web-Based Editing System
Implemented complete editing functionality with multimedia support for micro actions via web interface.

### Features Implemented

#### 1. Edit Interface
- **Pencil icon (✏️)** added to top-right corner of each card
- **Modal dialog** for editing title and description
- **GitHub Personal Access Token** authentication (15-minute session timeout)
- **Logout button** to clear stored tokens and switch accounts

#### 2. Media Upload System
- **Drag & drop** or click to browse file upload
- **Supported formats**: JPG, PNG (images), MP4 (video), MP3 (audio)
- **Maximum 4 files** per micro action
- **Auto-generated thumbnails** for images and videos (120x120px)
- **Sanitized filenames** to prevent special character issues
- **Progress indicators** with detailed upload status

#### 3. Media Storage & Display
- Files stored in `/docs/media/[item-hash]/` directories
- Thumbnails displayed below description text
- Click thumbnails to open full media viewer
- Lightbox for images, player controls for video/audio

#### 4. GitHub API Integration
- **Files created/modified**:
  - `docs/github-api.js` - GitHub API wrapper with Bearer auth
  - `docs/edit-modal.js` - Edit interface and file upload logic  
  - `docs/media-viewer.js` - Media lightbox/player
  - `docs/app.js` - Updated to show edit buttons and media
  - `docs/styles.css` - Added styles for edit UI
  - `docs/index.html` - Includes new JavaScript modules

### Authentication Setup

#### GitHub Token Requirements
- **Scope needed**: `repo` (Full control of private repositories)
- **Create token**: https://github.com/settings/tokens/new?scopes=repo
- **Token must belong to**: Repository owner or collaborator with write access

#### Common Issues & Solutions
1. **"Resource not accessible by personal access token"**
   - Solution: Token needs `repo` scope, not just `public_repo`
   - Changed from `token` to `Bearer` authorization format
   
2. **Old token still active**
   - Solution 1: Run `sessionStorage.clear()` in browser console
   - Solution 2: Use new Logout button in edit modal

3. **403 Forbidden errors**
   - Ensure token has full `repo` scope
   - Token must belong to repository owner
   - Check token hasn't expired

### Technical Implementation Details

#### API Authentication
```javascript
// Changed from 'token' to 'Bearer' format
headers: {
  'Authorization': `Bearer ${token}`,
  'Accept': 'application/vnd.github.v3+json',
  'X-GitHub-Api-Version': '2022-11-28'
}
```

#### File Upload Process
1. Read file as base64 via FileReader API
2. Sanitize filename (replace special chars with underscores)
3. Upload to `docs/media/[hash]/[timestamp]_[filename]`
4. Generate thumbnail if image/video
5. Update projects.json with media array
6. Commit changes via GitHub API

#### Security Measures
- Token stored in sessionStorage (not localStorage)
- 15-minute timeout for authentication
- Token never exposed in code or commits
- HTTPS-only API communications

### Testing & Debugging

#### Browser Console Commands
```javascript
// Check authentication status
window.githubAPI.isAuthenticated()

// View current user
sessionStorage.getItem('github_user')

// Clear authentication
sessionStorage.clear()

// Manual logout
window.githubAPI.logout()
```

#### API Error Codes
- **401**: Invalid token or expired
- **403**: Insufficient permissions (needs repo scope)
- **404**: Repository or file not found
- **422**: Invalid request (file too large, bad format)

### Files Modified Today
- `docs/github-api.js` - Complete rewrite with Bearer auth
- `docs/edit-modal.js` - Added logout, improved error messages
- `docs/media-viewer.js` - Created new
- `docs/app.js` - Added edit buttons and media display
- `docs/styles.css` - Added ~100 lines of new styles
- `docs/index.html` - Added script imports

### Commits Made
1. "Add editing functionality with multimedia support" (fb7f8e7)
2. "Fix file upload and save bugs in edit functionality" (b1084ad)  
3. "Fix GitHub token authentication for repository access" (0e8f5fe)
4. "Add logout functionality to clear stored tokens" (84bf491)

### Important Notes
- Edit functionality requires GitHub Personal Access Token with `repo` scope
- All changes committed directly to main branch via GitHub API
- Media files permanently stored in repository (increases repo size)
- No server-side code needed - works entirely with GitHub Pages

## Session History (2025-08-16) - EDIT MODAL CRITICAL FIXES

### Overview of Critical Bug Fixes Applied Today
Multiple critical issues with the edit modal were identified and systematically fixed through extensive debugging.

### Edit Button Icon and Position Change
- Changed pencil icon from ✏️ to ✎ (Unicode character)
- Moved edit button from top-right to bottom-right corner
- Modified: app.js line 4, styles.css line 39

### Media Thumbnail Fixes
- Fixed black margins using Math.max for cover mode
- Added grayscale filter to thumbnails (color on click)
- Changed audio icon from 🎵 to ▶️
- Fixed media removal not persisting (edit-modal.js line 354)

### UTF-8 Encoding Corruption Root Cause
**Problem**: Encoding with TextEncoder but decoding with simple atob() caused cumulative corruption  
**Solution**: Matched encode/decode methods using TextDecoder in github-api.js  
**Impact**: 135 out of 168 items were corrupted with ÃÂÃÂ patterns

### Edit Modal Not Opening - Multiple Fix Attempts

#### Attempt 1: Body Check with Retry
- Added retry mechanism (50 attempts, 2.5 seconds max)
- Check document.body before inserting HTML
- Result: Partial improvement but race condition remained

#### Attempt 2: Self-Healing open() Method
- Modal ensures structure exists BEFORE accessing child elements
- Comprehensive null checks for all DOM operations
- Result: Better but GitHub API still not loading

#### Attempt 3: Event-Based Script Loading (FINAL SOLUTION)
**Root cause**: Scripts using `defer` had no guarantee of load order

**Implemented Solution**:
1. github-api.js dispatches 'githubAPIReady' event when loaded
2. edit-modal.js waits for event before initializing  
3. Script loading coordinator with onload/onerror handlers
4. 10-second timeout instead of 2 seconds
5. Removed unused preload tag for projects.json

#### Attempt 4: JavaScript Syntax Errors
- Fixed duplicate 'jsonString' declaration (lines 290 & 349)
- Renamed to 'updatedJsonString' and 'binaryStringEncoded'
- Added missing testConnection() method to fallback

### Files Modified in Today's Session
- **docs/app.js** - Edit button rendering and event handlers
- **docs/styles.css** - Edit button positioning
- **docs/edit-modal.js** - Complete rewrite with event-based init
- **docs/github-api.js** - Fixed encoding, variables, added events
- **docs/index.html** - Script coordinator, removed preload
- **docs/media-viewer.js** - Audio icon updates

### Console Debugging Messages Added
Successfully added extensive logging:
```
github-api.js: Script loaded and executing
github-api.js: Dispatching githubAPIReady event
edit-modal.js: Received githubAPIReady event
Script [name] loaded successfully
```

### Key Lessons from Today's Debugging
1. **Race conditions**: Scripts with defer don't guarantee order - use events
2. **DOM readiness**: Never assume document.body exists immediately
3. **Variable scoping**: Check for duplicate const declarations
4. **Script dependencies**: Use event-based coordination, not polling
5. **Error messages**: Always provide clear user feedback

### Troubleshooting Guide for Future Issues

#### If Edit Modal Doesn't Open
1. Check console for "github-api.js:" or "edit-modal.js:" errors
2. Verify these success messages appear:
   - "GitHub API initialized successfully"
   - "Edit modal initialized successfully"
   - "Modal opened successfully"

#### Common Error Messages and Solutions
- **"GitHub API not loaded"**: Script blocked by ad blocker/CORS
- **"SyntaxError: Identifier already declared"**: Clear cache
- **"TypeError: X is not a function"**: Missing method in fallback
- **"Authentication failed"**: Token needs "repo" scope

### Today's Commits
1. Move edit button to bottom-right corner
2. Fix thumbnail display and grayscale filter
3. Fix UTF-8 encoding corruption root cause
4. Implement self-healing edit modal
5. Add event-based script loading coordination
6. Fix duplicate variable declarations

Total debugging time: ~3 hours
Final status: ✅ WORKING

## Session History (2025-08-16) - DATA CORRUPTION FIXES & SAFE REGENERATION

### Critical Issues Fixed

#### 1. Data Corruption Bug (Items Getting Mixed Content)
**Problem**: Edit modal was passing entire item objects causing data to get mixed between different micro actions.

**Solution**: 
- Only send changed fields (title, description, media) in updates
- Deep clone items when opening edit modal
- Add hash validation and integrity checks
- Fixed in `docs/edit-modal.js` and `docs/github-api.js`

#### 2. Severe Encoding Corruption (ÃÂÃÂÃÂ Bug)
**Problem**: 16 items had severe UTF-8 encoding corruption with repeated "ÃÂÃÂÃÂ..." patterns making content unreadable.

**Solution**:
- Created `scripts/fix_encoding.py` to detect and fix corruption
- Truncated text at corruption point, adding "..." 
- 18 fields were cleaned
- Items marked for regeneration in `docs/data/needs_regeneration.txt`

#### 3. Safe Regeneration System
**Problem**: Original "Regenerate All Content" action would replace ALL 168 items, potentially losing media and manual edits.

**Solution Created**:
- `scripts/safe_regenerate.py` - Selective regeneration with analysis
- `scripts/fix_encoding.py` - Fix encoding issues
- `.github/workflows/regenerate_safe.yml` - Safe GitHub Actions workflow

### New Utilities & Scripts

#### safe_regenerate.py
```bash
# Analyze current data issues
python3 scripts/safe_regenerate.py --analyze

# Regenerate only problematic items
python3 scripts/safe_regenerate.py --regenerate problems

# Test mode (preview changes)
python3 scripts/safe_regenerate.py --regenerate datasculptor --test

# Limit to 5 items for testing
python3 scripts/safe_regenerate.py --regenerate datasculptor --max 5

# Create backup
python3 scripts/safe_regenerate.py --backup

# Rollback to previous backup
python3 scripts/safe_regenerate.py --rollback
```

#### Current Data Status
- **168 total items**
- **55 have DATAsculptor references** (need regeneration)
- **16 had encoding corruption** (fixed by truncation, need regeneration)
- **1 has media uploads** (preserved)
- **113 are clean** (no issues)

### Key Technical Fixes

#### GitHub API Authentication
- Fixed authorization header format issues
- Added retry logic with exponential backoff
- Better error messages for token issues
- Support for both `token` and `Bearer` formats
- Added `testConnection()` method for debugging

#### Data Integrity
- Only update specified fields, preserve all others
- Hash validation before updates
- Check for duplicate hashes after updates
- Verify changes were applied correctly
- Deep clone items to prevent reference issues

#### Cache & CDN Issues
- Added cache-busting to projects.json loading
- Force reload with timestamp parameters
- Alert users about GitHub Pages 1-5 minute delay
- Verification step after saving to confirm changes

### Important Commands Summary

```bash
# Fix encoding issues
python3 scripts/fix_encoding.py

# Analyze data for problems
python3 scripts/safe_regenerate.py --analyze

# Test regeneration (no changes)
python3 scripts/safe_regenerate.py --regenerate problems --test

# Regenerate only DATAsculptor items
python3 scripts/safe_regenerate.py --regenerate datasculptor

# Create backup before any major changes
python3 scripts/safe_regenerate.py --backup

# Rollback if something goes wrong
python3 scripts/safe_regenerate.py --rollback
```

### Files Created/Modified Today
- `scripts/safe_regenerate.py` - Safe selective regeneration
- `scripts/fix_encoding.py` - Fix encoding corruption
- `.github/workflows/regenerate_safe.yml` - Safe regeneration workflow
- `docs/github-api.js` - Fixed authentication and data integrity
- `docs/edit-modal.js` - Fixed data corruption issues
- `docs/app.js` - Added cache-busting

### Backups Created
Multiple timestamped backups in `docs/data/`:
- `projects_backup_*.json` - General backups
- `projects_corrupted_*.json` - Before corruption fixes
- `projects_encoding_backup_*.json` - Before encoding fixes

### Critical Lessons Learned
1. **Always preserve media fields** during regeneration
2. **Only send changed fields** in updates to prevent corruption
3. **Deep clone objects** to prevent reference issues
4. **Create backups** before any bulk operations
5. **Use selective regeneration** instead of regenerating everything
6. **Handle GitHub Pages CDN delay** with user alerts
7. **UTF-8 encoding issues** can cascade - truncate at first corruption

## Session History (2025-08-17) - BACKGROUND PHOTO FEATURE

### Overview
Implemented complete background photo feature for micro action cards with grayscale display and full-color expanded view.

### Features Added

#### 1. Background Image Selection
- **Edit Modal Enhancement**: Added 🖼 checkbox icon on image thumbnails
- **Set as Background**: Click icon to select image as card background
- **Persistence**: Background selections saved to projects.json

#### 2. Card Display with Backgrounds
- **Grayscale Filter**: Background images display in grayscale (100%)
- **Dark Overlay**: Semi-transparent dark gradient for text readability
- **Content Wrapper**: All text wrapped in dark background container
- **Hover Effect**: Grayscale reduces to 80% on hover

#### 3. Expanded View Modal
- **New File**: `docs/card-expand.js` - Full-screen modal for background cards
- **Layout**: 60% image (full color) / 40% text panel
- **Click Handler**: Click card to open expanded view (excludes links/buttons)
- **Responsive**: Mobile-friendly with stacked layout

#### 4. Critical Bug Fixes
- **Persistence Fix**: Added backgroundImage handling in `github-api.js:updateSingleProject()`
- **Source Link Fix**: Excluded anchor tags from card click handler
- **Data Integrity**: Background field properly saved/loaded

### Technical Implementation

#### Files Modified
1. **docs/edit-modal.js**
   - Added pendingBackgroundIndex property
   - Background checkbox UI in renderMediaPreview()
   - Handle background selection in save()

2. **docs/github-api.js** (Line 324-331)
   ```javascript
   if (updates.hasOwnProperty('backgroundImage')) {
     if (updates.backgroundImage === null) {
       delete updatedItem.backgroundImage;
     } else {
       updatedItem.backgroundImage = updates.backgroundImage;
     }
   }
   ```

3. **docs/app.js**
   - Added has-background class and inline background-image style
   - Click handler for background cards (line 55-69)
   - Excluded links with `e.target.closest('a')`

4. **docs/styles.css**
   - Background card styles (lines 38-44)
   - Card expand modal styles (lines 117-141)
   - Responsive breakpoints

5. **docs/card-expand.js** (New)
   - Complete modal implementation for expanded view
   - Full-color image display with text panel

6. **docs/index.html**
   - Added card-expand.js script import

### Version Control & Backup Strategy

#### Branches Created
1. **backup-before-background-feature**
   - Clean state before feature implementation
   - Safety net for quick revert if needed

2. **feature-background-photos**
   - Feature development branch
   - Merged to main after testing

#### Deployment
- Merged to main: Commit 9d672c6
- Deployed to GitHub Pages
- Live at: https://grossculptor.github.io/leschnitz-micro-actions/

### Testing Instructions
1. Edit any micro action
2. Upload an image
3. Click 🖼 icon to set as background
4. Save changes
5. Card displays with grayscale background
6. Click card to see full-color expanded view

### Revert Instructions
If issues arise:
```bash
git checkout main
git reset --hard backup-before-background-feature
git push origin main --force
```

### Key Decisions
- Grayscale aesthetic maintains site's minimalist design
- Background images stored as URL references (not duplicated)
- Card dimensions unchanged - backgrounds adapt to content
- Edit UI uses familiar checkbox pattern
- Expand modal provides immersive full-color experience

## Session History (2025-08-18) - REVERTING LIVING MEMORY

### Overview
Reverted the project back to the last GitHub version, removing the Living Memory architecture that was only in local development.

### Living Memory System (REMOVED)
The Living Memory system was designed but not deployed to GitHub. It included:
- **current.json**: Would have contained last 14 days of content (50-60 items)
- **Archive system**: Weekly/monthly/yearly JSON archives in subdirectories
- **Archive management scripts**: archive_manager.py, archive_stats.py, archive_cleanup.py
- **Archive browser**: Frontend for browsing historical data

### Reversion Process
Successfully reverted using:
```bash
# Reset to GitHub's version
git reset --hard origin/main

# Remove untracked Living Memory files
git clean -fd
```

### Files Removed
- `docs/data/current.json` - Living Memory 14-day window
- `docs/data/archive_index.json` - Archive index
- `docs/data/weeks/`, `docs/data/months/`, `docs/data/years/` - Archive directories
- `docs/archive-browser.js`, `docs/archive.html` - Archive browser UI
- `scripts/archive_manager.py` - Archive management
- `scripts/archive_stats.py` - Archive statistics
- `scripts/archive_cleanup.py` - Archive cleanup utility

### Current State
- Project matches exactly what's on GitHub (commit 25d54ad)
- Only using `projects.json` for all data (no current.json)
- No archive system or Living Memory features
- All previously committed features remain intact:
  - Background photo feature
  - Edit functionality with media uploads
  - Safe regeneration system
  - All micro actions and media files

### Important Notes
- Living Memory was never pushed to GitHub
- Changes were only in local working directory
- Reversion was clean with no conflicts
- All production features remain functional

### If Need to Restore Living Memory Later
The Living Memory concept involved:
1. Splitting data into current (14 days) and archive
2. Time-based archives for historical browsing
3. Performance optimization for faster page loads
4. Archive management automation in pipeline

The architecture details remain documented above in the "Living Memory Architecture (NEW)" section for future reference if needed.

## Session History (2025-08-18) - DUPLICATE SOURCE URL FIX

### Problem Identified
- User reported two micro actions on the website had identical source URLs
- Screenshot showed "How does the forgetting smell preserve ducal dignity in?" and "Why does Grottkau's new tourism campaign erase ducal?" both linking to same NTO.pl article
- Analysis revealed 2 duplicate source patterns in projects.json

### Root Cause
NTO.pl articles use comment section identifiers that vary for the same article:
- `/ar/c1-18744833` vs `/ar/c7-18744833` (same article, different comment sections)
- Pipeline was treating these as unique URLs, creating duplicate micro actions
- Similar issue with strzelce360.pl article URLs with trailing variations

### Solution Implemented

#### 1. Enhanced URL Normalization (`scripts/pipeline.py`)
```python
def normalize_url(url: str) -> str:
    # Special handling for nto.pl comment sections
    if 'nto.pl' in parsed.netloc.lower() and '/ar/c' in path:
        path = re.sub(r'/ar/c\d+(-\d+)', r'/ar/c\1', path)
    
    # Special handling for strzelce360.pl article IDs
    if 'strzelce360.pl' in parsed.netloc.lower() and '/artykul/' in path:
        path = re.sub(r'/artykul/(\d+),.*', r'/artykul/\1', path)
```

#### 2. Improved Deduplication Logic
- Load existing projects.json at start of pipeline
- Check normalized URLs during feed parsing (lines 456-490)
- Skip items that already exist in projects.json
- Double-check both hash and normalized source URL before adding
- Early detection prevents unnecessary API calls

#### 3. Data Cleanup
- Created `scripts/remove_duplicates.py` utility
- Removed 2 duplicate items from projects.json (182 → 180 items)
- Created backup: `projects_backup_before_dedup.json`
- Saved removed items: `removed_duplicates.json`

### Duplicates Removed
1. **NTO.pl duchy article**: Kept c7 version, removed c1 version
2. **Strzelce360.pl development article**: Kept first version, removed variant

### Testing
- Created `scripts/test_normalization.py` to verify URL normalization
- All test cases pass, confirming fix works correctly

### Files Modified
- `scripts/pipeline.py` - Enhanced normalize_url() and deduplication
- `scripts/remove_duplicates.py` - New cleanup utility
- `scripts/test_normalization.py` - New test suite
- `docs/data/projects.json` - Removed 2 duplicates

### Key Lessons
- URL variations (comment sections, tracking params) can cause duplicates
- Normalize URLs early in pipeline to prevent duplicate processing
- Always check against existing data before processing new items
- Create backups before bulk data modifications

### Commit
- Hash: f96177f
- Message: "Fix duplicate source URLs and enhance deduplication"
- Deployed to GitHub Pages successfully


## Session History (2025-08-19) - GOOGLE SEARCH CONSOLE SETUP

### Quick Summary
Added Google Search Console verification for GitHub Pages site.

### Changes Made
- Added meta tag verification to `docs/index.html`
- Moved `googledde3e0cb5135f1ea.html` to docs directory  
- Created `.github/workflows/update-sitemap.yml` for automated sitemap updates
- Pushed changes after git pull --rebase to resolve divergence

### Verification
- Meta tag: `<meta name="google-site-verification" content="I-HHE3OOuVKOe7pdMzKuyU5PpbJLocW7i3SSXsnDxt8" />`
- Site URL: https://grossculptor.github.io/leschnitz-micro-actions/
- Commit: be63d5d

## Session History (2025-08-20) - GOOGLE ANALYTICS 4 IMPLEMENTATION

### Overview
Implemented Google Analytics 4 visitor tracking focused on user behavior rather than editor actions.

### GA4 Setup
- **Measurement ID**: G-CQT69LP63B
- **Property**: Leschnitz Micro Actions
- **Privacy**: IP anonymization enabled

### Implementation
Modified files:
- `docs/index.html` - Added GA4 script with anonymization
- `docs/404.html` - Added GA4 for error tracking
- `docs/app.js` - Search tracking (500ms debounce), source link clicks
- `docs/card-expand.js` - Background card expansion tracking
- `docs/test-analytics.html` - Test page for verification

### Events Tracked
- **search** - User queries and result counts
- **source_click** - External news source clicks  
- **card_expand** - Background image interactions
- **Auto-tracked**: Page views, scrolls, engagement time

### Safety & Deployment
- Created backup branch: `backup-before-ga4-20250820-211721`
- Commit: ad737f8
- Successfully deployed to GitHub Pages

### Rollback Commands
```bash
# Option 1: Reset to backup
git reset --hard backup-before-ga4-20250820-211721
git push origin main --force

# Option 2: Revert commit
git revert ad737f8
```

## Session History (2025-08-21) - GITHUB ACTIONS FIX

### Problem
GitHub Actions notification flood - getting dozens of emails every 3 hours from workflow failures.

### Root Causes Found
1. **Sitemap workflow broken** - Missing `python-dateutil` dependency installation
2. **Sitemap never updated** - Removed `docs/data/projects.json` trigger, sitemap stayed stale
3. **Scrape workflow error handling** - Used `continue-on-error` causing partial/broken commits
4. **Cascading failures** - Each broken commit triggered more workflows, creating notification storm

### Fixes Applied
- Added `pip install python-dateutil` to sitemap workflow
- Restored `docs/data/projects.json` trigger for sitemap updates
- Removed `continue-on-error` from scrape workflow - now fails properly
- Used stable dates in sitemap.xml to prevent unnecessary commits
- Synced with upstream (was 20 commits behind)

### Result
Workflows now fail fast on errors instead of committing broken data, preventing the cascade of failures that caused notification floods.

## Session History (2025-08-20) - DELETE FUNCTIONALITY ADDED

### Overview
Implemented complete delete functionality for micro actions in the edit modal, allowing users to remove items from the website.

### Changes Implemented

#### 1. Delete Button in Edit Modal (`docs/edit-modal.js`)
- Added red "Delete" button positioned on left side of modal footer
- Confirmation dialog: "Are you sure you want to delete this micro action? This cannot be undone."
- Disables all buttons during deletion to prevent race conditions
- Shows progress feedback during deletion process
- Auto-reloads page with cache-busting after successful deletion

#### 2. Delete API Method (`docs/github-api.js`)
- Implemented `deleteSingleProject(itemHash, retryCount = 0)` method
- Uses same UTF-8 safe encoding/decoding as `updateSingleProject`
- Fetches current projects.json with SHA for conflict resolution
- Validates data integrity (array length decreased by 1, unique hashes)
- Handles SHA conflicts with exponential backoff (up to 3 retries)
- Proper error handling for network issues and permission errors

#### 3. Delete Button Styling (`docs/styles.css`)
- Red color scheme (#8b2020 background, #a52828 on hover)
- Positioned left with `margin-right: auto`
- Disabled state styling with reduced opacity

### Safety Features
- Confirmation dialog prevents accidental deletion
- Delete button visually distinct (red color, left position away from Save)
- Buttons disabled during operation to prevent conflicts
- Same robust SHA handling as update operations
- Media files remain in repository (can be cleaned manually if needed)

### Backup Strategy
- Created backup branch: `backup-before-delete-feature`
- Pushed to GitHub before implementing changes
- Easy rollback available if issues arise

### Deployment
- Commit: 733a51c
- Pushed to main branch
- Live on GitHub Pages: https://grossculptor.github.io/leschnitz-micro-actions/

### Rollback Instructions (if needed)
```bash
# Option 1: Reset to backup
git checkout main
git reset --hard backup-before-delete-feature
git push origin main --force

# Option 2: Revert commit
git revert 733a51c
git push origin main
```

## Session History (2025-08-20) - UNVERIFIED IMPORT SYSTEM

### Overview
Created a bypass system to import all content from workers.dev RSS feeds without verification, addressing the need to publish news immediately without classification filters.

### Changes Implemented

#### 1. Import Script (`scripts/import_unverified.py`)
- **Bypasses all filters**: No preselection or classification checks
- **Enhanced URL normalization**: Handles amp, page, print parameters
- **Robust datetime parsing**: Timezone-aware comparisons
- **Atomic file writing**: Temp file + rename for safety
- **Automatic backups**: Creates timestamped backup before writing
- **Dry-run mode**: Test imports before executing
- **Metadata tracking**: Adds `unverified_import: true` to items

#### 2. Successfully Imported
- 7 new micro actions from https://falling-bush-1efa.thedatasculptor.workers.dev/
- Database grew from 195 to 202 items
- Commit: a22cf50

### Usage
```bash
# Dry run (preview)
python3 scripts/import_unverified.py --feed [URL]

# Execute import
python3 scripts/import_unverified.py --feed [URL] --execute
```

### Revert if needed
```bash
git revert a22cf50
git push origin main
```

## Session History (2025-09-05) - MODEL UPDATE TO KIMI K2 0905

### Overview
Successfully updated all pipeline scripts from the old `moonshotai/kimi-k2-instruct` model to the new `moonshotai/Kimi-K2-Instruct-0905` model.

### Changes Made

#### Model Update
- **Old model**: `moonshotai/kimi-k2-instruct`
- **New model**: `moonshotai/Kimi-K2-Instruct-0905`
- **Files updated**: 7 scripts across the pipeline
- **Tested**: Confirmed working with test_api.py

#### Files Modified
1. `scripts/pipeline.py` - Main pipeline (lines 347, 562)
2. `scripts/regenerate_batch.py` - Batch regeneration (line 55)
3. `scripts/regenerate_all_content.py` - Full regeneration (line 101)
4. `scripts/regenerate_titles.py` - Title regeneration (line 76)
5. `scripts/fix_truncated_titles.py` - Title fixes (line 98)
6. `scripts/import_unverified.py` - Unverified imports (line 217)
7. `scripts/test_api.py` - API testing (line 15)

### Git Operations & Safety

#### Backup Strategy
1. Created backup branch: `backup-before-model-update-20250905-101603`
2. Pulled 121 commits from GitHub (was behind origin/main)
3. Stashed changes, pulled latest, reapplied changes
4. Committed with descriptive message
5. Successfully pushed to GitHub: commit `4f0ff43`

#### Virtual Environment Setup
```bash
# Created during session for testing
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Revert Commands (if needed)
```bash
# Option 1: Reset to backup branch
git reset --hard backup-before-model-update-20250905-101603
git push origin main --force

# Option 2: Revert the specific commit
git revert 4f0ff43
git push origin main
```

### Testing Verification
```bash
# Test new model directly
source .venv/bin/activate
export GROQ_API_KEY=$(grep GROQ_API_KEY .env | cut -d'=' -f2)
python3 scripts/test_api.py "$GROQ_API_KEY"
# Result: ✅ Successfully returns "test successful"
```

### Important Notes
- Model name is case-sensitive: must use `Kimi-K2-Instruct-0905` with exact capitalization
- All automated workflows now use the new model
- API remains compatible with same authentication and headers
- No changes needed to SYSTEM_PROMPT or other configuration