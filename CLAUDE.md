# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated RSS aggregation and AI-powered content generation system that creates "micro artistic actions" from local news about Leschnitz (Leśnica) and the Gross Strehlitz (Strzelce Opolskie) area in Oberschlesien, Poland. Publishes to static GitHub Pages website.

## Key Commands

### Setup and Run Pipeline
```bash
# Setup environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the pipeline
python scripts/pipeline.py

# Run regeneration of all content with new prompt
python scripts/pipeline.py --regenerate
```

### Archive Management Commands
```bash
# View archive statistics
python scripts/archive_stats.py

# Clean up old backups and empty archives (dry run)
python scripts/archive_cleanup.py

# Execute cleanup (actually delete files)
python scripts/archive_cleanup.py --execute

# Manually run archive manager
python scripts/archive_manager.py
```

### GitHub Deployment
- Scraping workflow runs every 3 hours via cron (`.github/workflows/scrape.yml`)
- Pipeline auto-commits to repository
- GitHub Pages deploys from /docs directory
- Manual regeneration available via GitHub Actions workflow

## Architecture

### Data Pipeline
RSS Feeds (config/feeds.txt) → Raw Data → Relevance Filtering → AI Generation (Groq) → docs/data/projects.json → Archive Manager → GitHub Pages

### Living Memory Architecture (NEW)
The project uses a **Living Memory** architecture for optimal performance:
- **current.json**: Contains last 14 days of content (50-60 items) - loaded by default
- **projects.json**: Complete archive (175+ items) - fallback/reference 
- **Time-based archives**: Historical data organized by week/month/year
- **Auto-archiving**: Pipeline automatically runs archive_manager.py after updates

Benefits:
- **60-70% faster page load** (52 vs 175 items)
- **Unlimited scalability** without performance degradation  
- **Preserved media/edits** across all archives
- **Browse historical data** via archive browser UI

### Core Files
- **scripts/pipeline.py**: Main processing pipeline (with --regenerate flag)
- **scripts/archive_manager.py**: Manages Living Memory time-based archives
- **scripts/archive_stats.py**: Shows archive statistics and performance metrics
- **scripts/archive_cleanup.py**: Removes empty archives and old backups
- **docs/index.html**: Static website
- **docs/app.js**: Search and UI (loads current.json first, falls back to projects.json)
- **docs/archive-browser.js**: Browse historical weekly/monthly/yearly archives
- **docs/styles.css**: Minimalist grayscale design
- **docs/data/current.json**: Last 14 days of micro actions (fast loading)
- **docs/data/projects.json**: Complete archive (166+ micro actions)
- **docs/data/archive_index.json**: Index of all time-based archives
- **config/feeds.txt**: RSS feed sources
- **secrets/SYSTEM_PROMPT.local.txt**: AI system prompt (local only, contains all generation rules)

### Data Storage
- Raw: `/data/raw/<timestamp>/`
- Filtered: `/data/relevant/<timestamp>/`
- Current output: `/docs/data/current.json` (14-day window)
- Full archive: `/docs/data/projects.json`
- Weekly archives: `/docs/data/weeks/YYYY-WNN.json`
- Monthly archives: `/docs/data/months/YYYY-MM.json`
- Yearly archives: `/docs/data/years/YYYY.json`

## Critical Content Rules

### Place Names (MUST use German names)
- Leschnitz (not Leśnica)
- Gross Strehlitz (not Strzelce Opolskie)  
- Oppeln (not Opole)
- Oberschlesien (not Upper Silesia)

### AI Generation
- English output only
- Max 500 characters
- Include original keywords
- Atmospheric, sensual tone (smell, mood, atmosphere)
- No "DATAsculptor" mentions
- Use alternatives to "colonial": Settler, Invader, Occupier, Expansionist
- Respect Upper Silesian cultural context

## API and Secrets Configuration

### Required Secrets
The pipeline requires two secrets that are handled differently in local vs production:

1. **GROQ_API_KEY**:
   - Production: GitHub Secret `GROQ_API_KEY`
   - Local: Environment variable or `secrets/groq_api_key.txt`

2. **SYSTEM_PROMPT**:
   - Production: GitHub Secret `SYSTEM_PROMPT` (base64 encoded)
   - Local: File `secrets/SYSTEM_PROMPT.local.txt`
   - Contains ALL generation rules (moved from pipeline.py for security)

### Setting up GitHub Secrets
In GitHub repository settings → Secrets and variables → Actions:
- Add `GROQ_API_KEY` with your Groq API key
- Add `SYSTEM_PROMPT` with base64 encoded contents from `secrets/SYSTEM_PROMPT.local.txt`

Use `python3 scripts/encode_prompt.py` to generate base64 encoding.

## Important Implementation Details

### Filtering Logic
- Conservative pre-filtering by geographic keywords to minimize API costs
- Two-stage AI processing: relevance check → content generation
- Deduplication using SHA1 hashing

### Error Handling
- Retry with exponential backoff via tenacity
- Heuristic fallback when AI fails
- Partial data preservation

### Frontend
- Static site, no build process
- Gray-scale minimalist design
- Progressive enhancement with JavaScript
- Grid layout with hover effects
- NO expand buttons - all content displayed in full

## Development Workflow

1. Modify pipeline.py for data processing changes
2. Update docs/ for frontend changes
3. Commit and push - GitHub Actions handles deployment
4. For full content regeneration: trigger "Regenerate All Content" workflow

## Key Patterns to Maintain

- Multilingual normalization in pipeline.py (GERMAN_MAP dictionary)
- Cultural sensitivity in prompts
- Cost-conscious API usage
- Audit trail in data/raw folders
- System prompt reads from env var first, then local file

## Invariants — do not break these (added 2026-07-30)

Read `scripts/selftest.py` first: it encodes these as executable tests and runs in CI
on every push and before every scheduled pipeline run.

1. **A failed generation must never become a published item.** Items whose
   generation failed go to `docs/data/quarantine.json`, are retried next run, and
   after 3 attempts move to `docs/data/suppressed.json`. Never write a fallback or
   placeholder into `projects.json`. The old fallback wrote poetic
   `[NEEDS REGENERATION]` text that *looked like content*, which is why nobody
   noticed for 3.5 months — a failure path must never resemble the success path.
2. **`suppressed.json` must stay wired into the dedup sets**, or the 894 purged
   placeholders return. The first run after the purge re-scraped 29 of them.
   Match on exact normalized URL and hash only — never add suppressed URLs to
   `existing_raw_urls`, which fuzzy-matches slugs at 0.80–0.85 and would then block
   every future `ostrzezenie-dla-opolskiego-*` warning as a near-duplicate.
3. **`scrape.yml` must keep committing `quarantine.json`.** The runner is ephemeral;
   without it the retry counter resets every run and nothing ever gets suppressed.
4. **`validate_micro()` runs only on newly generated items, never retroactively.**
   Hand-edited items legitimately break its rules (longer descriptions, the author's
   own word choices). `VALIDATION_MODE=shadow` reports without dropping;
   `enforce` routes failures to quarantine.
5. **Never truncate a description with a bare slice.** Use
   `smart_truncate_description()`. The old `[:500]` left 745 published items ending
   mid-word.
6. **`pipeline.py --regenerate` rewrites EVERY item's title and description** and
   has never honoured `docs/data/regenerate_list.json`. It requires
   `REGENERATE_ALL_CONFIRM=yes`. This means the **"Safe Selective Regeneration"
   workflow (`regenerate_safe.yml`) now fails loudly — it was never selective.**
   To regenerate a subset, work from `suppressed.json`'s `original_title`, never
   from `description` (which is the placeholder text for purged items).
7. **⚠ Only `pipeline.py` got the 2026-07-30 fix.** These scripts are manual-run
   only (no workflow invokes them) but they write **directly into
   `docs/data/projects.json`**, bypassing `validate_micro()`, the quarantine and the
   health check — and each hardcodes the model with no `reasoning_effort`:

   | Script | `max_tokens` | |
   |--------|--------------|---|
   | `fix_truncated_titles.py` | **200** | tighter than the 1000 that caused the flood |
   | `regenerate_titles.py` | **200** | same |
   | `regenerate_all_content.py` | 600 | |
   | `regenerate_batch.py` | 600 | |
   | `import_unverified.py` | 1000 | model is a default arg |
   | `pipeline_debug.py` | 1000 | hardcodes `llama-3.1-70b-versatile`, which Groq no longer serves |

   Running one today would very likely write empty or truncated text onto the live
   site. Before using any of them, raise `max_tokens` to ≥800 and add
   `reasoning_effort: 'low'` — or better, route them through `pipeline.py`'s
   `_groq_chat`, which is now the single place model and budget are configured
   (`GROQ_MODEL` env var overrides the default).
8. **Alarms:** `scripts/check_data_health.py` runs last in `scrape.yml` and fails on
   any published placeholder, >25 items awaiting retry, or >30% of a run's relevance
   decisions coming from the keyword fallback. An off-box canary on the Hetzner box
   (`/home/datasculptor/leschnitz-canary.py`, every 30 min) checks the *published*
   site and opens a `[canary]` issue — it is the only check that survives this
   workflow being disabled or silently unscheduled.

## Critical Implementation Notes

### API Configuration
- **NEVER use urllib for Groq API** - Cloudflare blocks it, use requests library
- **Current Model**: `openai/gpt-oss-120b`, overridable with the `GROQ_MODEL` env var
- **A model swap is never a one-line change.** `gpt-oss-120b` bills hidden reasoning
  tokens against `max_tokens`, so a budget that was fine for Kimi-K2 makes it return
  `content: ""`. Commit `ad939808` swapped only the model string and left
  `max_tokens: 1000` with no `reasoning_effort`: 894 placeholder items over 3.5
  months, every workflow run reporting success. When changing models, audit
  `max_tokens` and `reasoning_effort` at every callsite and run one real item through
  the pipeline before pushing.
- **GitHub Secrets Required**: GROQ_API_KEY and SYSTEM_PROMPT (base64 encoded)
- **System Prompt Location**: `secrets/SYSTEM_PROMPT.local.txt`

### Critical Fixes Applied
- **Pipeline Merging**: Always load existing projects.json and merge, never overwrite
- **URL Normalization**: Handle NTO.pl comment sections and strzelce360.pl variations
- **UTF-8 Encoding**: Use TextEncoder/TextDecoder pair consistently
- **Frontend Display**: No expand buttons - all content shows in full
- **Edit Modal**: Only send changed fields in updates to prevent corruption

## Features Implemented

### Web-Based Editing System
- **Edit Modal**: Pencil icon (✎) at bottom-right of cards
- **Media Upload**: Drag & drop, max 4 files (JPG/PNG/MP4/MP3)
- **Background Photos**: Grayscale on cards, full-color in expanded view
- **Delete Function**: Red delete button with confirmation dialog
- **GitHub Integration**: Direct editing via GitHub API with Bearer auth
- **Authentication**: GitHub Personal Access Token with `repo` scope required


## Safe Regeneration System

Use `scripts/safe_regenerate.py` for selective regeneration:
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

- **Always preserve media** during regeneration
- **Create backups** before bulk operations  
- **Use selective regeneration** to avoid data loss





## Word Cloud Extraction

Extracts daily word clouds from micro action titles for visualization tools.

- **Script**: `scripts/extract_wordclouds.py`
- **Output**: `docs/data/wordclouds/YYYY-MM-DD.txt` (one word per line, sorted)
- **Index**: `docs/data/wordclouds/index.txt`
- **Start date**: 2026-01-12 (only processes data from this date onwards)
- **Integration**: Auto-runs after `pipeline.py` saves projects.json

```bash
# Manual run
python scripts/extract_wordclouds.py
```

Rules: 3+ chars, no digits, preserves hyphenated words (e.g., "gross-strehlitz"), filters English stop words + domain terms (micro, action, silesian). Incremental processing - skips dates with existing files.

See `docs/WORDCLOUD_SPEC.md` for full specification.

## Session History Summary

### 2026-01-12: Added word cloud extraction system
### 2025-08-15: Fixed Groq API blocking issue (replaced urllib with requests)
### 2025-08-16: Removed DATAsculptor references, moved rules to secret prompt  
### 2025-08-16: Added web editing with media upload and GitHub API integration
### 2025-08-16: Fixed UTF-8 encoding corruption, event-based script loading
### 2025-08-16: Created safe selective regeneration system
### 2025-08-17: Added background photo feature with grayscale cards
### 2025-08-18: Reverted Living Memory architecture (never deployed)
### 2025-08-18: Fixed duplicate URL handling for NTO.pl and strzelce360.pl
### 2025-08-19: Added Google Search Console verification
### 2025-08-20: Implemented Google Analytics 4 tracking
### 2025-08-20: Added delete functionality with confirmation
### 2025-08-20: Created unverified import system for workers.dev feeds
### 2025-08-21: Fixed GitHub Actions notification flood
### 2025-09-05: Updated to Kimi-K2-Instruct-0905 model

*Full session details archived in CLAUDE_HISTORY.md*