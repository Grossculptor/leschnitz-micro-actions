#!/usr/bin/env python3
"""
Extract daily word clouds from micro action titles.

Processes projects.json and generates one text file per day containing
unique, filtered words for use with visualization tools.

Usage:
    python scripts/extract_wordclouds.py
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

from dateutil import parser as dparser

# Paths
ROOT = Path(__file__).resolve().parent.parent
DOCS_DATA = ROOT / "docs" / "data"
PROJECTS_FILE = DOCS_DATA / "projects.json"
WORDCLOUDS_DIR = DOCS_DATA / "wordclouds"
INDEX_FILE = WORDCLOUDS_DIR / "index.txt"

# Default start date (first run date per spec)
DEFAULT_START_DATE = "2026-01-12"

# Stop words from specification
STOP_WORDS = {
    # Common English
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "have", "has", "had",
    "when", "why", "do", "does", "did", "must", "can", "will", "would", "could", "should",
    "what", "who", "which", "where", "how", "if", "in", "on", "at", "to", "for", "of",
    "with", "from", "by", "as", "and", "or", "but", "not", "so", "than", "that", "this",
    "these", "those", "it", "its", "they", "them", "their", "there", "here", "about",
    "into", "over", "after", "before", "between", "through", "during", "under", "above",
    # Domain-specific
    "micro", "action", "silesian",
}


def tokenize_title(title: str) -> list[str]:
    """
    Extract words from a title, preserving hyphenated words as single tokens.

    Handles German (ä, ö, ü, ß) and Polish (ą, ć, ę, ł, ń, ó, ś, ź, ż) characters.
    """
    # Match word characters including international letters, preserving hyphens within words
    # Pattern: letter followed by optional (letters/hyphens/apostrophes) ending with letter
    pattern = r"[a-zA-ZäöüÄÖÜßąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+(?:[-'][a-zA-ZäöüÄÖÜßąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+)*"
    return re.findall(pattern, title, re.UNICODE)


def filter_word(word: str) -> str | None:
    """
    Filter a single word. Returns lowercase word if valid, None otherwise.

    Rules:
    - Minimum 4 characters
    - No digits
    - Not in stop words
    """
    word_lower = word.lower()

    # Check minimum length
    if len(word_lower) < 4:
        return None

    # Check for digits
    if any(c.isdigit() for c in word_lower):
        return None

    # Check stop words
    if word_lower in STOP_WORDS:
        return None

    return word_lower


def get_start_date() -> str:
    """
    Get the start date from index.txt or return default.
    """
    if INDEX_FILE.exists():
        content = INDEX_FILE.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("# Start:"):
                return line.split(":", 1)[1].strip()
    return DEFAULT_START_DATE


def get_existing_dates() -> set[str]:
    """
    Get set of dates that already have word cloud files.
    """
    if not WORDCLOUDS_DIR.exists():
        return set()

    existing = set()
    for f in WORDCLOUDS_DIR.glob("????-??-??.txt"):
        existing.add(f.stem)
    return existing


def parse_datetime(dt_str: str) -> datetime | None:
    """
    Parse a datetime string silently. Returns None on failure.
    """
    try:
        return dparser.parse(dt_str)
    except Exception:
        return None


def extract_words_from_titles(titles: list[str]) -> set[str]:
    """
    Extract unique filtered words from a list of titles.
    """
    words = set()
    for title in titles:
        tokens = tokenize_title(title)
        for token in tokens:
            filtered = filter_word(token)
            if filtered:
                words.add(filtered)
    return words


def write_word_file(date_str: str, words: set[str]) -> None:
    """
    Write words to a daily word cloud file.
    """
    output_file = WORDCLOUDS_DIR / f"{date_str}.txt"
    sorted_words = sorted(words)
    output_file.write_text("\n".join(sorted_words) + "\n", encoding="utf-8")


def write_index(dates: list[str], start_date: str) -> None:
    """
    Write or update the index file with metadata and date list.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "# Word Cloud Index",
        f"# Start: {start_date}",
        f"# Generated: {now}",
        "",
    ]
    lines.extend(sorted(dates))

    INDEX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    # Ensure output directory exists
    WORDCLOUDS_DIR.mkdir(parents=True, exist_ok=True)

    # Load projects
    if not PROJECTS_FILE.exists():
        return

    projects = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    if not projects:
        return

    # Get start date and existing files
    start_date = get_start_date()
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    existing_dates = get_existing_dates()

    # Group titles by date (only from start_date onwards)
    titles_by_date = defaultdict(list)

    for item in projects:
        dt_str = item.get("datetime", "")
        if not dt_str:
            continue

        parsed = parse_datetime(dt_str)
        if not parsed:
            continue

        # Make timezone-aware for comparison
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        # Skip items before start date
        if parsed < start_dt:
            continue

        date_key = parsed.strftime("%Y-%m-%d")
        title = item.get("title", "")
        if title:
            titles_by_date[date_key].append(title)

    # Process each date that doesn't have a file yet
    all_dates = set(existing_dates)
    new_dates = []

    for date_key, titles in titles_by_date.items():
        if date_key in existing_dates:
            continue

        words = extract_words_from_titles(titles)

        # Skip empty days (no words after filtering)
        if not words:
            continue

        write_word_file(date_key, words)
        all_dates.add(date_key)
        new_dates.append(date_key)

    # Update index if we have any dates
    if all_dates:
        write_index(sorted(all_dates), start_date)


if __name__ == "__main__":
    main()
