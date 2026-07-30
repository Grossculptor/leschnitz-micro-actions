#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline invariant tests for the pipeline. No network, no API key, ~1 second.

These encode the guarantees won back on 2026-07-30, so that a future edit which
breaks one of them fails CI instead of quietly filling the site with placeholders
for three and a half months.

The invariant that matters most: a failed generation must never become a published
item. Everything here defends that.

    python3 scripts/selftest.py
"""
import base64
import datetime as dt
import importlib.util
import os
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _install_stubs():
    """Stub only what is missing, so the suite runs with or without deps installed."""
    def stub(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        return m

    try:
        import requests  # noqa: F401
    except ImportError:
        class _Sess:
            def __init__(self): self.headers = {}
            def get(self, *a, **k): raise RuntimeError("network disabled in selftest")
            def post(self, *a, **k): raise RuntimeError("network disabled in selftest")
        stub("requests", Session=_Sess, Response=object,
             HTTPError=type("HTTPError", (Exception,), {}),
             RequestException=type("RequestException", (Exception,), {}))
    try:
        import feedparser  # noqa: F401
    except ImportError:
        stub("feedparser", parse=lambda *a, **k: None)
    try:
        import bs4  # noqa: F401
    except ImportError:
        stub("bs4", BeautifulSoup=object)
    try:
        import dateutil.parser  # noqa: F401
    except ImportError:
        def _parse(v):
            # Strict on purpose: a malformed offset such as "+02:" must not parse,
            # because repair_datetime relies on that to detect model truncation.
            return dt.datetime.fromisoformat(str(v))
        du = stub("dateutil")
        du.parser = types.SimpleNamespace(parse=_parse)
        sys.modules["dateutil.parser"] = du.parser
    try:
        import tenacity  # noqa: F401
    except ImportError:
        stub("tenacity", retry=lambda **kw: (lambda f: f),
             wait_exponential=lambda **kw: None, stop_after_attempt=lambda n: None)


def load_pipeline():
    _install_stubs()
    os.environ.setdefault("SYSTEM_PROMPT", base64.b64encode(b"test prompt").decode())
    os.environ.setdefault("GROQ_API_KEY", "selftest-not-a-real-key")
    spec = importlib.util.spec_from_file_location("pipeline_under_test",
                                                 ROOT / "scripts" / "pipeline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pl = load_pipeline()
PLACEHOLDER = "[NEEDS REGENERATION]"
GOOD_DESC = ("At dawn, place dried sage on the warning sign near Leschnitz and let "
             "the scent recall the land before the asphalt was poured.")


# --- quarantine state machine -------------------------------------------------

def test_clean_item_publishes_and_failure_is_withheld():
    q, s = {}, []
    ok = {"hash": "h1", "title": "Real?", "source": "http://x/1"}
    bad = {"hash": "h2", "fallback_used": True, "original_title": "Orig",
           "source": "http://x/2", "fallback_reason": "empty_content"}
    good, n = pl.partition_generated([ok, bad], q, s, now="T0")
    assert [g["hash"] for g in good] == ["h1"]
    assert list(q) == ["h2"] and q["h2"]["attempts"] == 1 and n == 1 and s == []


def test_three_strikes_moves_to_suppressed():
    q, s = {}, []
    bad = {"hash": "h2", "fallback_used": True, "original_title": "Orig",
           "source": "http://x/2", "fallback_reason": "empty_content"}
    for i in range(pl.MAX_GENERATION_ATTEMPTS):
        good, _ = pl.partition_generated([dict(bad)], q, s, now=f"T{i}")
        assert good == [], "a fallback item must never be publishable"
    assert "h2" not in q and len(s) == 1
    assert s[0]["reason"] == "generation_failed"
    assert s[0]["attempts"] == pl.MAX_GENERATION_ATTEMPTS


def test_quarantined_item_recovers_on_later_success():
    q, s = {}, []
    pl.partition_generated([{"hash": "h2", "fallback_used": True, "source": "http://x/2",
                             "original_title": "o"}], q, s, now="T0")
    good, _ = pl.partition_generated([{"hash": "h2", "title": "works?",
                                       "source": "http://x/2"}], q, s, now="T1")
    assert [g["hash"] for g in good] == ["h2"] and q == {} and s == []


def test_bulk_failure_publishes_nothing():
    q, s = {}, []
    many = [{"hash": f"z{i}", "fallback_used": True, "original_title": f"o{i}",
             "source": f"http://x/{i}"} for i in range(50)]
    good, n = pl.partition_generated(many, q, s, now="T0")
    assert good == [] and n == 50 and len(q) == 50


# --- end to end: a broken model must not reach the site -----------------------

def test_empty_groq_content_never_becomes_a_published_item():
    """The exact 2026-04-17 regression, reproduced offline."""
    original = pl._groq_chat
    try:
        pl._groq_chat = lambda *a, **k: {"choices": [{"message": {"content": ""}}]}
        micro = pl.generate_micro({"title": "Ostrzeżenie dla Opolskiego",
                                   "published": "2026-01-15T09:00:00+00:00"})
    finally:
        pl._groq_chat = original
    assert micro.get("fallback_used") is True
    assert micro.get("fallback_reason") == "empty_content"
    q, s = {}, []
    good, _ = pl.partition_generated([micro | {"hash": "e1", "source": "http://x/e1"}], q, s)
    assert good == [], "empty Groq content must not produce a published item"


def test_valid_groq_content_does_become_a_published_item():
    original = pl._groq_chat
    payload = ('{"title": "Why does the notice silence local voices?",'
               ' "datetime": "2026-01-15T09:00:00+00:00",'
               f' "description": "{GOOD_DESC}"}}')
    try:
        pl._groq_chat = lambda *a, **k: {"choices": [{"message": {"content": payload}}]}
        micro = pl.generate_micro({"title": "Utrudnienia w ruchu",
                                   "published": "2026-01-15T09:00:00+00:00"})
    finally:
        pl._groq_chat = original
    assert not micro.get("fallback_used"), micro
    assert pl.validate_micro(micro) == [], pl.validate_micro(micro)
    q, s = {}, []
    good, _ = pl.partition_generated([micro | {"hash": "g1", "source": "http://x/g1"}], q, s)
    assert len(good) == 1 and q == {}


# --- validator ----------------------------------------------------------------

def test_validator_accepts_a_good_item():
    assert pl.validate_micro({"title": "Why does the tender dissolve?",
                              "description": GOOD_DESC,
                              "datetime": "2026-01-15T09:00:00+00:00"}) == []


def test_validator_rejects_each_defect_class():
    base = {"title": "Why does the tender dissolve?", "description": GOOD_DESC}
    cases = {
        "empty title":        {**base, "title": ""},
        "empty description":  {**base, "description": ""},
        "too short":          {**base, "description": "Too short."},
        "too long":           {**base, "description": "x" * 501},
        "mid-sentence":       {**base, "description": GOOD_DESC.rstrip(".") + " and then"},
        "placeholder tag":    {**base, "description": f"{PLACEHOLDER} {GOOD_DESC}"},
        "datasculptor":       {**base, "description": GOOD_DESC + " DATAsculptor was here."},
        "colonial":           {**base, "description": GOOD_DESC + " A colonial echo."},
        "mojibake":           {**base, "description": GOOD_DESC + " Ã¢ââ."},
        "not english":        {**base, "description": ("To jest opis, który nie jest "
                                                       "po angielsku, oraz dla tego "
                                                       "zostanie odrzucony przez walidator.")},
    }
    for name, item in cases.items():
        problems = pl.validate_micro(item)
        assert problems, f"validator failed to reject: {name}"


def test_polish_placename_is_advisory_not_blocking():
    """A proper noun must not cost us the item; it is reported, not rejected."""
    item = {"title": "What hidden agenda fuels the Roztańczony Leśnicki Ryneczek?",
            "description": GOOD_DESC}
    assert pl.validate_micro(item) == [], "place names must not block publication"
    assert pl.advise_micro(item), "place names must still be reported"


def test_placeholder_text_can_never_pass_validation():
    """Belt and braces: even if the fallback write path were reintroduced."""
    item = {"title": "What story remains untold in X...?",
            "description": (PLACEHOLDER + " Visit the location mentioned in recent news. "
                            "Document what the official narrative excludes.")}
    assert pl.validate_micro(item), "the placeholder text must never validate"


# --- truncation and datetime repair ------------------------------------------

def test_description_truncation_never_cuts_mid_word():
    long_text = ("Walk the market square at dusk and breathe the resin. " * 20).strip()
    out = pl.smart_truncate_description(long_text)
    assert len(out) <= 500
    assert out[-1] in '.?!")…', repr(out[-60:])
    assert pl.validate_micro({"title": "Why?", "description": out}) == []


def test_description_truncation_handles_text_with_no_sentence_break():
    out = pl.smart_truncate_description("word " * 300)
    assert len(out) <= 500 and out[-1] in '.?!")…'


def test_short_description_is_untouched():
    assert pl.smart_truncate_description(GOOD_DESC) == GOOD_DESC


def test_datetime_repair():
    feed = "2026-01-15T09:00:00+00:00"
    # a sane model-supplied date is kept
    assert pl.repair_datetime("2026-01-16T10:00:00+00:00", feed) == "2026-01-16T10:00:00+00:00"
    # truncated offset, the real corruption seen on three live items
    assert pl.repair_datetime("2026-04-12T13:16:00+02:", feed) == feed
    # far-future date, which pinned garbage to the top of the site
    assert pl.repair_datetime("2027-12-19T12:00:00+00:00", feed) == feed
    # nothing usable anywhere: must still return something parseable, not crash
    out = pl.repair_datetime("nonsense", "also nonsense")
    assert dt.datetime.fromisoformat(out)


def test_validation_mode_defaults_to_a_known_value():
    assert pl.VALIDATION_MODE in ("shadow", "enforce")


def test_regenerate_all_is_guarded():
    """The 'Safe Selective Regeneration' workflow must not be able to rewrite everything."""
    saved = os.environ.pop("REGENERATE_ALL_CONFIRM", None)
    try:
        raised = False
        try:
            pl.regenerate_existing()
        except SystemExit:
            raised = True
        assert raised, "regenerate_existing must refuse to run without explicit confirmation"
    finally:
        if saved is not None:
            os.environ["REGENERATE_ALL_CONFIRM"] = saved


def main():
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"  ok    {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    if failed:
        print("failed: " + ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
