#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail the build if degraded data reached the published site.

Every incident in this project so far has been silent: the workflow reports
success, the site returns HTTP 200, and the cards render politely -- while 75% of
them are placeholder text. The 2026-04-17 model swap went undetected for 3.5
months for exactly that reason. This check makes that class of failure loud.

Run after pipeline.py. Non-zero exit fails the workflow.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "data"
PLACEHOLDER_TAG = "[NEEDS REGENERATION]"
# More than this many items waiting on a retry means generation is broken, not
# that one article was awkward.
QUARANTINE_ALARM = 25
# Share of a run's relevance decisions allowed to come from the keyword fallback
# before the editorial gate counts as degraded.
HEURISTIC_ALARM = 0.30


def load_list(path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"WARN: could not read {path.name}: {e}")
        return []


def load_obj(path):
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"WARN: could not read {path.name}: {e}")
        return {}


def main():
    items = load_list(DOCS / "projects.json")
    quarantine = load_list(DOCS / "quarantine.json")
    suppressed = load_list(DOCS / "suppressed.json")
    run = load_obj(DOCS / "last_run.json")

    placeholders = [i for i in items
                    if i.get("needs_regeneration")
                    or i.get("fallback_used")
                    or PLACEHOLDER_TAG in (i.get("description") or "")]

    print(f"published items      : {len(items)}")
    print(f"placeholders on site : {len(placeholders)}")
    print(f"awaiting retry       : {len(quarantine)}")
    print(f"suppressed total     : {len(suppressed)}")

    failures = []

    if placeholders:
        for i in placeholders[:10]:
            print(f"  PLACEHOLDER {i.get('hash','?')[:8]} {(i.get('title') or '')[:65]}")
        failures.append(
            f"{len(placeholders)} placeholder item(s) reached projects.json. "
            "pipeline.py is supposed to quarantine these instead of publishing them.")

    if len(quarantine) > QUARANTINE_ALARM:
        reasons = {}
        for q in quarantine:
            key = str(q.get("last_reason", "unknown")).split(":")[0]
            reasons[key] = reasons.get(key, 0) + 1
        print(f"  quarantine reasons: {reasons}")
        failures.append(
            f"{len(quarantine)} items awaiting retry (alarm above {QUARANTINE_ALARM}) - "
            "generation is failing systematically. Check max_tokens / reasoning_effort "
            "in _groq_chat and the Groq model's availability.")

    # Classifier degradation. The keyword fallback decides what enters the archive
    # at all and leaves no mark on the item, so a Groq outage silently changes the
    # editorial gate. Ratio, not count: a run with 2 items proves nothing.
    heur = run.get("classified_by_heuristic")
    pre = run.get("preselected") or 0
    if heur is not None and pre >= 10:
        ratio = heur / pre
        print(f"heuristic gate       : {heur}/{pre} ({ratio:.0%})")
        if ratio > HEURISTIC_ALARM:
            failures.append(
                f"{ratio:.0%} of classifications fell back to the keyword heuristic "
                f"(alarm above {HEURISTIC_ALARM:.0%}). Relevance filtering is degraded, "
                "so off-topic items are entering the archive unmarked.")
    elif heur is not None:
        print(f"heuristic gate       : {heur}/{pre} (too few items to judge)")

    if run.get("validation_mode") == "shadow":
        print("validation mode      : shadow (reporting only - not yet enforcing)")

    if failures:
        print()
        for f in failures:
            print(f"FAIL: {f}")
        sys.exit(1)

    print("OK: no degraded data on the site")


if __name__ == "__main__":
    main()
