# Word Cloud Extraction Specification

## Overview

Extract daily word clouds from micro action titles in `docs/data/projects.json`. Generate one text file per day containing unique, filtered words for use with visualization tools.

## File Locations

- **Script**: `scripts/extract_wordclouds.py`
- **Input**: `docs/data/projects.json`
- **Output directory**: `docs/data/wordclouds/`
- **Output files**: `YYYY-MM-DD.txt` (e.g., `2026-01-12.txt`)
- **Index file**: `docs/data/wordclouds/index.txt`

## Processing Rules

### Data Source
- Process only the `title` field from micro actions
- Use `docs/data/projects.json` as the source

### Date Handling
- **Start date**: 2026-01-12 (recorded on first run)
- Only process micro actions from start date onwards
- Skip all historical data before start date
- Parse datetime fields silently; skip entries with unparseable dates
- Group by calendar date (day-level granularity)

### Word Extraction
- Tokenize titles (split on whitespace and punctuation)
- Convert to lowercase
- **Preserve hyphenated words** as single tokens (e.g., "gross-strehlitz" stays intact)
- **Minimum length**: 4+ characters
- **No numbers**: Exclude tokens containing any digits
- Include all languages (German, Polish, English)

### Stop Words (Hardcoded)
Filter out these common English words:
```
the, a, an, is, are, was, were, be, been, have, has, had,
when, why, do, does, did, must, can, will, would, could, should,
what, who, which, where, how, if, in, on, at, to, for, of,
with, from, by, as, and, or, but, not, so, than, that, this,
these, those, it, its, they, them, their, there, here, about,
into, over, after, before, between, through, during, under, above
```

**Domain-specific stop words** (project terms to filter):
```
micro, action, silesian
```

### Output Format

#### Daily Word Files (`YYYY-MM-DD.txt`)
- One word per line
- Lowercase
- Sorted alphabetically
- UTF-8 encoding (no BOM)
- Unique words only (no duplicates)

Example `2026-01-12.txt`:
```
absence
bureaucratic
expansionist
indigenous
leschnitz
missing
settler
stores
```

#### Index File (`index.txt`)
Header with metadata, followed by list of available dates:
```
# Word Cloud Index
# Start: 2026-01-12
# Generated: 2026-01-12T14:30:00Z

2026-01-12
2026-01-13
2026-01-14
```

## Operational Behavior

### Processing Mode
- **Incremental**: Only process dates that don't already have word cloud files
- Skip dates where `YYYY-MM-DD.txt` already exists
- Never regenerate existing files

### Integration
- Called automatically by `pipeline.py` after updating `projects.json`
- Can also run standalone: `python scripts/extract_wordclouds.py`

### Console Output
- **Silent operation**: No output unless errors occur
- Exit silently if no new data to process

### Edge Cases
- **Sparse days**: Create file even with only 2-3 words
- **Empty days**: Skip days with zero words after filtering (no file created)
- **Parse errors**: Silently skip entries with unparseable datetime
- **No cleanup**: Never delete existing word cloud files

## State Management

The start date is stored in `index.txt` header:
- On first run, record current date (2026-01-12) as start date
- On subsequent runs, read start date from index.txt
- Only process micro actions with datetime >= start date

## Dependencies

- `dateutil.parser` - datetime parsing (already in requirements.txt)
- `re` - word tokenization (standard library)
- `pathlib` - file operations (standard library)
- `json` - data loading (standard library)

## Example Workflow

```bash
# First run (creates initial word clouds from today onwards)
python scripts/extract_wordclouds.py

# Subsequent runs (only processes new days)
python scripts/extract_wordclouds.py

# Called automatically after pipeline
python scripts/pipeline.py  # runs extract_wordclouds.py at end
```

## File Structure After Implementation

```
docs/data/wordclouds/
├── index.txt           # Index with start date metadata
├── 2026-01-12.txt      # Word cloud for Jan 12
├── 2026-01-13.txt      # Word cloud for Jan 13
└── ...
```
