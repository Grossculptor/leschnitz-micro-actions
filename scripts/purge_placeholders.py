#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove [NEEDS REGENERATION] placeholder micro actions from projects.json.

Placeholders are written by pipeline.py's generate_micro() fallback whenever Groq
returns no usable JSON. From 2026-04-17 (commit ad939808, the Kimi-K2 ->
openai/gpt-oss-120b swap) that path fired for roughly 75% of all intake, because
the payload kept max_tokens=1000 with no reasoning_effort cap and the new model
spends its budget on hidden reasoning, returning content:"".

Selection is keyed on the immutable `hash` field, never on list position: the 3h
pipeline re-sorts projects.json on every run, so the index-based approach used by
safe_regenerate.py / regenerate_list.json can point at entirely different items by
the time it is applied.

Purged sources are appended to docs/data/suppressed.json, which pipeline.py folds
into its dedup sets so a purged item cannot be re-scraped back onto the site.

Dry run by default -- nothing is written without --execute:

    python3 scripts/purge_placeholders.py            # report only
    python3 scripts/purge_placeholders.py --execute  # apply
"""
import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "data"
PROJECTS_FILE = DOCS / "projects.json"
SUPPRESSED_FILE = DOCS / "suppressed.json"

PLACEHOLDER_TAG = "[NEEDS REGENERATION]"
# Fields whose presence means a human invested something in the item. Nothing
# carrying these is ever deleted, regardless of its flags.
PROTECTED_FIELDS = ("media", "lastEdited", "background", "images")


def signals(item):
    """The three independent markers of a fallback item."""
    return (
        item.get("needs_regeneration") is True,
        item.get("fallback_used") is True,
        PLACEHOLDER_TAG in (item.get("description") or ""),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--execute", action="store_true",
                    help="actually write the changes (default: dry run)")
    args = ap.parse_args()

    if not PROJECTS_FILE.exists():
        sys.exit(f"ERROR: {PROJECTS_FILE} not found")

    data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        sys.exit("ERROR: projects.json is not a JSON list - aborting")

    targets, ambiguous, protected = [], [], []
    for item in data:
        s = signals(item)
        if not any(s):
            continue
        if not all(s):
            # Signals disagree: something unexpected. Never guess -- report it.
            ambiguous.append(item)
        elif any(item.get(f) for f in PROTECTED_FIELDS):
            protected.append(item)
        else:
            targets.append(item)

    print(f"projects.json           : {len(data)} items")
    print(f"placeholders to remove  : {len(targets)}")
    print(f"protected (media/edits) : {len(protected)}")
    print(f"ambiguous (mixed flags) : {len(ambiguous)}")

    for item in ambiguous:
        print(f"  AMBIGUOUS {item.get('hash','?')[:8]} signals={signals(item)} "
              f"{(item.get('title') or '')[:60]}")
    for item in protected:
        print(f"  PROTECTED {item.get('hash','?')[:8]} "
              f"{(item.get('title') or '')[:60]}")

    if ambiguous:
        sys.exit("\nERROR: refusing to proceed while items have inconsistent flags. "
                 "Inspect the entries listed above first.")

    if not targets:
        print("\nNothing to do - no placeholders present.")
        return

    # Hashes must be present and unique, or removal cannot be keyed safely.
    hashes = [i.get("hash") for i in targets]
    if not all(hashes):
        sys.exit("ERROR: some placeholders have no hash - aborting")
    if len(set(hashes)) != len(hashes):
        sys.exit("ERROR: duplicate hashes among placeholders - aborting")

    doomed = set(hashes)
    remaining = [i for i in data if i.get("hash") not in doomed]
    assert len(remaining) == len(data) - len(targets), "unexpected removal count"

    # What the site loses, month by month, so the effect is visible before writing.
    by_month = {}
    for item in targets:
        by_month[(item.get("datetime") or "?")[:7]] = \
            by_month.get((item.get("datetime") or "?")[:7], 0) + 1
    print("\nremoved per month:")
    for month in sorted(by_month):
        print(f"  {month}: {by_month[month]}")

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    future = [i for i in targets if (i.get("datetime") or "")[:10] > today]
    print(f"\nof which future-dated (pinned to top of site): {len(future)}")
    for item in future:
        print(f"  {(item.get('datetime') or '')[:10]}  {(item.get('title') or '')[:55]}")

    print(f"\nresult: {len(data)} -> {len(remaining)} items")

    if not args.execute:
        print("\nDRY RUN - nothing written. Re-run with --execute to apply.")
        return

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = DOCS / f"projects_backup_{stamp}.json"
    shutil.copy2(PROJECTS_FILE, backup)
    print(f"\nbackup written: {backup.name}")

    # Suppress the purged sources so the 3h pipeline cannot re-scrape them back.
    suppressed = []
    if SUPPRESSED_FILE.exists():
        try:
            loaded = json.loads(SUPPRESSED_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                suppressed = loaded
        except Exception as e:
            print(f"WARN: could not read suppressed.json ({e}) - starting fresh")
    already = {s.get("hash") for s in suppressed if s.get("hash")}
    added = 0
    for item in targets:
        if item.get("hash") in already:
            continue
        suppressed.append({
            "hash": item.get("hash"),
            "source": item.get("source"),
            "original_title": item.get("original_title") or "",
            "published": item.get("datetime"),
            "reason": "purged_placeholder",
            "suppressed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        added += 1
    SUPPRESSED_FILE.write_text(json.dumps(suppressed, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    print(f"suppressed.json: +{added} entries ({len(suppressed)} total)")

    PROJECTS_FILE.write_text(json.dumps(remaining, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    print(f"projects.json rewritten: {len(remaining)} items")

    # Re-read from disk and confirm, rather than trusting the in-memory result.
    verify = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    left = [i for i in verify if any(signals(i))]
    print(f"\nverification: {len(verify)} items on disk, {len(left)} placeholders remaining")
    if left:
        sys.exit("ERROR: placeholders still present after purge")
    print("OK")


if __name__ == "__main__":
    main()
