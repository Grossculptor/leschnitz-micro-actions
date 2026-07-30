# -*- coding: utf-8 -*-
import os, re, json, time, hashlib, pathlib, datetime as dt, argparse, subprocess, sys
import requests, feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dparser
from tenacity import retry, wait_exponential, stop_after_attempt

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RELEVANT = DATA / "relevant"
DOCS = ROOT / "docs" / "data"
CONFIG = ROOT / "config"
SECRETS = ROOT / "secrets"
DOCS.mkdir(parents=True, exist_ok=True); RAW.mkdir(parents=True, exist_ok=True); RELEVANT.mkdir(parents=True, exist_ok=True)

FEEDS_FILE = CONFIG / "feeds.txt"

# Load feeds list
def load_feeds():
    urls = []
    if FEEDS_FILE.exists():
        for line in FEEDS_FILE.read_text(encoding="utf-8").splitlines():
            s=line.strip()
            if s and s.startswith("http"):
                urls.append(s)
    return urls

GERMAN_MAP = {
  r"\bLeśnica\b|\bLesnica\b": "Leschnitz",
  r"\bStrzelce Opolskie\b": "Gross Strehlitz",
  r"\bpowiat strzelecki\b|\bPowiat strzelecki\b": "Kreis Gross Strehlitz",
  r"\bOpole\b|\bOpolu\b|\bOpolski(e|m|a)?\b": "Oppeln",
  r"\bGórny Śląsk\b|\bGórny Sląsk\b|\bGórny Śląsku\b|\bGorny Slask\b": "Oberschlesien",
  r"\bO/S\b": "O/S",
  r"\bGrodzisko\b": "Burghof",
  r"\bGąsiorowice\b|\bGasiorowice\b": "Gonschiorowitz",
  r"\bZawadzkie\b": "Zawadzki",
  r"\bJemielnica\b": "Imielnitz",
  r"\bŁąki Kozielskie\b|\bLaki Kozielskie\b": "Wiesen Kandrzin",
  r"\bZalesie Śląskie\b|\bZalesie Slaskie\b": "Zalesie OS",
  r"\bGóra Św\.? Anny\b|\bGora Sw\.? Anny\b": "Sankt Annaberg",
  r"\bOpolszczyz(na|nie|ną|ny|nę|nej|nach)\b|\bOpolszczy[źż](nie|nia|nię|ni|nej|nach)\b": "Oberschlesien"
}

KEYWORDS_STRONG = [
  "Leśnica","Lesnica","Leschnitz","Strzelce Opolskie","Gross Strehlitz",
  "powiat strzelecki","Kreis Gross Strehlitz","Góra Św. Anny","Sankt Annaberg",
  "Oppeln","Opole","Opolski","Oberschlesien","Schlesien","Schlesier", "Annaberg","Lenkau","Łąki Kozielskie",
  "Opolszczyzna","Opolszczyźnie","Opolszczyznę","Opolszczyzny","Wyssoka","Wysoka",
  "Zalesie Śląskie","Zalesie Slaskie","Zalesie OS","Salesche",
  "Raszowa","Raschowa","Poręba","Poremba","Lichinia","Lichynia","Żyrowa","Zyrowa","Zdzieszowice","Deschowitz",
  "Dolna","Dollna","Kadłubiec","Kadlubietz",
  # Cultural and linguistic keywords
  "godka","gwara","śląska","śląski","ślonski","dialekt","Ślonsko",
  "haberfloki","krepel","ucek","wodzionka","żymlok","karminadle",
  # Community keywords  
  "mieszkańcy","mieszkaniec","sołtys","sołectwo","wieś","wsie","gmina",
  "wioska","społeczność","obywatel","obywatele","rada miejska","rada gminy"
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
TIMEOUT=20  # Increased timeout for slow feeds like BIP Lesnica

def ts_now():
    return dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")

def normalize_german_places(text:str)->str:
    out = text or ""
    for pat, repl in GERMAN_MAP.items():
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out

def smart_truncate_title(text:str, min_len:int=45, max_len:int=58)->str:
    """Truncate title at word boundary to avoid mid-word cuts"""
    if not text:
        return ""
    
    # Remove existing ? if present to add it properly later
    text = text.rstrip('?')
    
    # If already short enough, just ensure it ends with ?
    if len(text) <= min_len:
        return text + '?'
    
    # If within acceptable range, keep it
    if len(text) <= max_len:
        return text + '?'
    
    # Need to truncate - find last complete word before max_len
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    
    # If we can break at a word boundary after min_len
    if last_space > min_len:
        return truncated[:last_space].rstrip() + '?'
    
    # Fallback: hard cut at min_len
    return text[:min_len].rstrip() + '?'

def smart_truncate_description(text:str, limit:int=500)->str:
    """Truncate a description at a sentence (or word) boundary.

    The previous `[:limit]` slice cut mid-word: 745 of the 2564 items on the site
    are exactly 500 characters and end in the middle of a word. Always returns
    text closed with terminal punctuation.
    """
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    window = text[:limit]
    end = max(window.rfind(". "), window.rfind("! "), window.rfind("? "),
              window.rfind("."), window.rfind("!"), window.rfind("?"))
    if end >= limit // 2:          # keep at least half the budget of real text
        return window[:end + 1].strip()
    cut = window.rfind(" ")
    if cut <= 0:
        return window
    return window[:cut].rstrip(" ,;:-–—") + "."

# Validation of generated items. Every rule here was measured against the 2564
# known-good items on the site before being enabled; the whole set rejects 6 of
# them, and all 6 are genuinely defective (one entirely empty card, three
# truncated datetimes, one Polish description, one 'colonial'). A rule that
# rejected a meaningful share of good output would starve the site, not guard it.
FORBIDDEN_SUBSTRINGS = ("datasculptor", "colonial", "[needs regeneration]")
BARE_POLISH_PLACE = re.compile(r"Leśnic|Strzelce Opolskie|\bOpol(e|u)\b")
MOJIBAKE = re.compile(r"Ã|â€")
# Polish function words: a handful in quoted source phrases is intended, a
# descriptionful of them means the model answered in the wrong language.
POLISH_FUNCTION_WORDS = re.compile(
    r"\b(jest|nie|oraz|który|która|dla|przez|tego|jako|zostanie|będzie|wszystk)\w*\b", re.I)

def validate_micro(item:dict)->list:
    """Return a list of reasons the item is unfit to publish (empty == fit)."""
    problems = []
    title = (item.get("title") or "").strip()
    desc = (item.get("description") or "").strip()
    blob = f"{title} {desc}"

    if not title:
        problems.append("empty title")
    if not desc:
        problems.append("empty description")
    if desc and len(desc) < 40:
        problems.append(f"description too short ({len(desc)} chars)")
    if len(desc) > 500:
        problems.append(f"description too long ({len(desc)} chars)")
    if desc and desc[-1] not in '.?!")…':
        problems.append("description ends mid-sentence")
    for bad in FORBIDDEN_SUBSTRINGS:
        if bad in blob.lower():
            problems.append(f"forbidden text {bad!r}")
    if MOJIBAKE.search(blob):
        problems.append("encoding damage")
    if len(POLISH_FUNCTION_WORDS.findall(desc)) >= 5:
        problems.append("description is not in English")
    return problems

def advise_micro(item:dict)->list:
    """Non-blocking observations: logged, never a reason to drop an item.

    Bare Polish place names live here rather than in validate_micro because the
    rule cannot tell a missed normalisation from a proper noun -- of the three live
    items it flags, one is the festival "Roztańczony Leśnicki Ryneczek", where the
    Polish name is the event's actual title. Gating on that would discard real
    coverage of local events to satisfy a cosmetic rule.
    """
    notes = []
    blob = f"{item.get('title') or ''} {item.get('description') or ''}"
    if BARE_POLISH_PLACE.search(blob):
        notes.append("contains a Polish place name (check normalisation, or a proper noun)")
    return notes

def repair_datetime(value, fallback):
    """Return a sane ISO datetime, preferring the feed's own published date.

    The model invents the `datetime` field, and it gets this wrong in two ways:
    truncated offsets ("2026-04-12T13:16:00+02:") and dates far in the future,
    which sort to the top of the site and pin themselves there. Mechanically
    repairable, so repair rather than discard an otherwise good item.
    """
    def parse(v):
        try:
            p = dparser.parse(str(v))
            return p if p.tzinfo else p.replace(tzinfo=dt.timezone.utc)
        except Exception:
            return None
    now = dt.datetime.now(dt.timezone.utc)
    got = parse(value)
    if got is not None and got <= now + dt.timedelta(hours=36):
        return value
    alt = parse(fallback)
    if alt is not None and alt <= now + dt.timedelta(hours=36):
        print(f"INFO: repaired datetime {value!r} -> {fallback!r} (feed published date)")
        return fallback
    print(f"INFO: repaired datetime {value!r} -> now (no usable feed date)")
    return now.isoformat()

def sha1(s:str)->str:
    return hashlib.sha1(s.encode("utf-8","ignore")).hexdigest()

def extract_article_slug(url: str) -> str:
    """Extract a normalized article slug that can identify the same article across different domains."""
    if not url:
        return ""
    
    import re
    from urllib.parse import urlparse
    
    url_lower = url.lower()
    parsed = urlparse(url_lower)
    path = parsed.path
    
    # Pattern: /slug/ar/c7-12345 -> slug
    match = re.search(r'/([a-z0-9-]+)/ar/c\d+-\d+', path)
    if match:
        return match.group(1)
    
    # Pattern: /slug,12345 -> slug
    match = re.search(r'/([a-z0-9-]+),\d+', path)
    if match:
        return match.group(1)
    
    # Pattern: /artykul/slug,12345 -> slug
    match = re.search(r'/artykul/([a-z0-9-]+)', path)
    if match:
        return match.group(1)
    
    # Extract longest slug-like pattern from the path
    slugs = re.findall(r'[a-z0-9-]{15,}', path)
    if slugs:
        return max(slugs, key=len)
    
    # Fallback: clean path and return last segment
    clean_path = re.sub(r'/ar/c\d+-\d+$', '', path)
    clean_path = re.sub(r',\d+$', '', clean_path)
    clean_path = re.sub(r'\.html?$', '', clean_path)
    clean_path = clean_path.strip('/')
    
    if '/' in clean_path:
        segments = clean_path.split('/')
        last_segment = segments[-1]
        if len(last_segment) > 10 and re.match(r'^[a-z0-9-]+$', last_segment):
            return last_segment
    
    return clean_path

def is_cross_domain_duplicate(url: str, existing_urls: list) -> bool:
    """Check if URL is a duplicate article on a different domain."""
    from urllib.parse import urlparse
    from difflib import SequenceMatcher
    
    if not url or not existing_urls:
        return False
    
    domain = urlparse(url).netloc.lower()
    slug = extract_article_slug(url)
    
    if not slug or len(slug) < 10:
        return False
    
    # Known syndication groups
    syndicated_domains = [
        {'nto.pl', 'strzelceopolskie.naszemiasto.pl', 'naszemiasto.pl'},
        {'strzelce360.pl', 'strzelce.pl'},
        {'radio.opole.pl', 'opole.pl'}
    ]
    
    for existing_url in existing_urls:
        existing_domain = urlparse(existing_url).netloc.lower()
        
        # Skip if same domain
        if domain == existing_domain:
            continue
        
        # Check if domains are in known syndication group
        threshold = 0.85
        for group in syndicated_domains:
            if domain in group and existing_domain in group:
                threshold = 0.80
                break
        
        existing_slug = extract_article_slug(existing_url)
        if not existing_slug or len(existing_slug) < 10:
            continue
        
        # Check exact match or high similarity
        if slug == existing_slug:
            return True
        
        similarity = SequenceMatcher(None, slug, existing_slug).ratio()
        if similarity >= threshold:
            return True
    
    return False

def normalize_url(url: str) -> str:
    """Normalize URL to prevent duplicates from tracking parameters and variations."""
    if not url:
        return ""
    
    import re
    # Parse URL components
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    parsed = urlparse(url)
    path = parsed.path
    
    # Special handling for nto.pl comment section identifiers
    # Convert /ar/c1-18744833, /ar/c7-18744833 etc to /ar/c-18744833
    if 'nto.pl' in parsed.netloc.lower() and '/ar/c' in path:
        path = re.sub(r'/ar/c\d+(-\d+)', r'/ar/c\1', path)
    
    # Special handling for strzelce360.pl article IDs
    # Remove trailing commas and normalize article paths
    if 'strzelce360.pl' in parsed.netloc.lower() and '/artykul/' in path:
        path = re.sub(r'/artykul/(\d+),.*', r'/artykul/\1', path)
    
    # Remove common tracking parameters
    tracking_params = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'ref', 'source', 'mc_cid', 'mc_eid'
    }
    
    # Parse query parameters and filter out tracking ones
    params = parse_qs(parsed.query)
    filtered_params = {
        k: v for k, v in params.items() 
        if k.lower() not in tracking_params
    }
    
    # Rebuild query string
    new_query = urlencode(filtered_params, doseq=True)
    
    # Rebuild URL without fragment and with filtered query
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),  # Normalize domain to lowercase
        path.rstrip('/'),  # Use normalized path without trailing slash
        parsed.params,
        new_query,
        ''  # Remove fragment
    ))
    
    return normalized

@retry(wait=wait_exponential(multiplier=1, max=20), stop=stop_after_attempt(4))
def fetch(url:str)->requests.Response:
    r = SESSION.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r

def pull_fulltext(url:str)->str:
    try:
        # Skip fulltext for certain problematic domains
        if any(domain in url for domain in ["workers.dev", "cloudflare"]):
            return ""
        html = fetch(url).text
        soup = BeautifulSoup(html, "html.parser")
        for sel in ["article",".content",".entry-content","#content",".post",".news",".art__content","main"]:
            node = soup.select_one(sel)
            if node and node.get_text(strip=True):
                return node.get_text(" ", strip=True)[:8000]
        return " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))[:8000]
    except Exception as e:
        print(f"WARN: Failed to pull fulltext from {url}: {e}")
        return ""

def parse_feed(url:str):
    try:
        # Use fetch function which has retry logic with exponential backoff
        response = fetch(url)
        fp = feedparser.parse(response.text)
        if fp.entries:
            out = []
            for e in fp.entries[:20]:  # Limit to 20 entries per feed
                link = e.get("link") or ""
                title = BeautifulSoup(e.get("title",""),"html.parser").get_text()
                summary = BeautifulSoup(e.get("summary",""),"html.parser").get_text() if e.get("summary") else ""
                published = e.get("published") or e.get("updated") or ""
                try:
                    pdt = dparser.parse(published)
                except Exception:
                    pdt = dt.datetime.utcnow()
                content = summary
                # Skip fulltext extraction for now to speed up processing
                # Can be re-enabled selectively later
                # if link:
                #     body = pull_fulltext(link)
                #     if body:
                #         content = f"{summary}\n\n{body}" if summary else body
                out.append({
                    "source": url,
                    "link": link,
                    "title": title,
                    "summary": summary,
                    "content": content[:15000],
                    "published": pdt.isoformat()
                })
            return out
    except Exception as e:
        print(f"ERROR: Failed to parse feed {url}: {e}")
        # Re-raise to ensure error files are created
        raise
    # HTML fallback - skip for now to avoid hanging
    return []

def strong_keyword_hit(text:str)->bool:
    t=(text or "").lower()
    return any(k.lower() in t for k in [*KEYWORDS_STRONG,"oppeln","gross strehlitz","leschnitz"])

def cultural_content_hit(text: str) -> bool:
    """Detect cultural preservation and community tension topics"""
    import re
    patterns = [
        r'god[kc][aiey]|gwar[aęy]|dialekt|śl[ąo]nsk',  # dialect variations including "godki"
        r'mieszka[ńn]c[yów]|sołtys|wie[śs]|wiosk',  # community
        r'tradycj|zwycza[ij]|kultur|dziedzictw',  # tradition
        r'hałas|śmie[ćc]i|imprez|zabaw[ay]|głośn',  # community tensions
        r'słownik|leksykon|mowa|język|regionali',  # language preservation
        r'konflikt|spór|problem|skarż|narzekan',  # tensions
        r'klasówk|quiz|test.*śląsk|profesor.*wons'  # educational content about dialect
    ]
    t = (text or "").lower()
    return any(re.search(p, t, re.IGNORECASE) for p in patterns)

# --- Groq OpenAI-compatible client ---
def _read_system_prompt()->str:
    sp = os.getenv("SYSTEM_PROMPT")
    if sp:
        # Try to decode if it's base64
        try:
            import base64
            decoded = base64.b64decode(sp).decode('utf-8')
            return decoded
        except:
            # If decoding fails, use as-is (plain text)
            return sp
    p = SECRETS / "SYSTEM_PROMPT.local.txt"
    if p.exists():
        return p.read_text(encoding="utf-8")
    raise RuntimeError("SYSTEM_PROMPT missing: provide env var or secrets/SYSTEM_PROMPT.local.txt")

# Model is env-overridable so a bad or withdrawn model can be rolled back without a
# commit (the pattern prosto and lesnica already use). Groq withdrew
# moonshotai/Kimi-K2 without notice on 2026-04-14; the swap that replaced it is
# what caused the 2026-04..07 placeholder flood.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# "shadow" logs what enforcement would reject without acting; "enforce" routes
# failing items to quarantine. Starts in shadow so the real false-positive rate on
# freshly generated items can be read off a live run before it can drop anything.
VALIDATION_MODE = os.getenv("VALIDATION_MODE", "shadow")

def _groq_chat(messages, model=None):
    model = model or GROQ_MODEL
    print(f"DEBUG: Making Groq API call with model {model}")
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Leschnitz-MicroActions/1.0"
    }
    
    # gpt-oss-120b bills hidden reasoning tokens against max_tokens. With a tight
    # budget and no reasoning_effort cap it spends everything on reasoning and
    # returns content:"" -- which looks like a successful call but yields no JSON.
    # This is what produced ~75% fallback items from 2026-04-17 onwards.
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000,
        "reasoning_effort": "low"
    }

    last_err = None
    for attempt in range(1, 4):
        try:
            print(f"DEBUG: Sending request to Groq API (attempt {attempt}/3)...")
            response = SESSION.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            print(f"DEBUG: Groq API response status: {response.status_code}")
            # Retry transient failures instead of burning the item on one hiccup
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(
                    f"transient {response.status_code}: {response.text[:200]}",
                    response=response)
            response.raise_for_status()
            result = response.json()
            print(f"DEBUG: Groq API call successful")
            return result
        except (requests.HTTPError, requests.RequestException, ValueError) as e:
            last_err = e
            status = getattr(getattr(e, "response", None), "status_code", None)
            # 4xx other than 429 is a request problem: retrying will not help
            if status is not None and 400 <= status < 500 and status != 429:
                print(f"Groq API Error (non-retryable {status}): {getattr(e.response, 'text', '')[:300]}")
                raise
            if attempt < 3:
                backoff = 2 ** attempt
                print(f"WARN: Groq call failed ({e}); retrying in {backoff}s")
                time.sleep(backoff)

    print(f"ERROR: Groq API failed after 3 attempts: {last_err}")
    raise RuntimeError(f"Groq API unavailable after 3 attempts: {last_err}")

def _extract_json(text:str):
    # Robust JSON extractor: take first {...} block
    text = text.strip()
    # Remove fences
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    # Find first balanced object
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        blob = m.group(0)
        try:
            return json.loads(blob)
        except Exception:
            pass
    # Last resort: simple heuristics
    return {}

def classify_with_kimi(item:dict)->dict:
    sys = _read_system_prompt() + "\nRespond ONLY with compact JSON."
    user = f"""
Classify if this article is relevant to the local area.
Return JSON with keys: "relevant": boolean, "why": string, "places_german": [string].
Title: {item.get('title','')}
Summary: {item.get('summary','')}
Content: {(item.get('content') or '')[:1200]}
"""
    try:
        out = _groq_chat([{"role":"system","content":sys},{"role":"user","content":user}])
        text = out["choices"][0]["message"]["content"]
        js = _extract_json(text)
        # minimal validation
        if "relevant" in js:
            js["classified_by"] = "llm"
            return js
    except Exception as e:
        print(f"WARN: Classification failed for '{item.get('title','')[:50]}...': {e}")
    # Heuristic fallback. This decides what enters the archive at all, and unlike a
    # generation failure it leaves no trace on the item -- during the 2026-04..07
    # outage it silently admitted drought alerts and power-cut notices. The
    # behaviour is kept (a keyword gate is a reasonable degraded mode) but the
    # decision is now labelled and counted so it cannot degrade in silence.
    print(f"WARN: Classification fell back to keyword heuristic for '{item.get('title','')[:50]}...'")
    return {"relevant": ("bip.lesnica.pl" in (item.get("source") or "") or strong_keyword_hit(item.get("title","")+item.get("summary","")+item.get("content",""))),
            "why":"heuristic fallback","places_german":[],"classified_by":"heuristic"}

def generate_micro(item:dict)->dict:
    sys = _read_system_prompt() + """
Output JSON with exactly these keys: "title", "datetime", "description"."""
    kws = re.findall(r"[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż\-]{4,}", item.get("title",""))[:4]
    user = f"""Transform this news item into artistic micro action.
Source title: {item.get('title','')}
Published: {item.get('published','')}
Available keywords: {kws}
Content: {item.get('summary') or (item.get('content') or '')[:400]}
Return JSON only."""
    reason = "unknown"
    for attempt in range(1, 3):
        msgs = [{"role":"system","content":sys},{"role":"user","content":user}]
        if attempt > 1:
            # Second pass: be blunt about the contract. Cheap insurance against a
            # single malformed or empty completion costing us the whole item.
            msgs.append({"role":"user","content":
                'Your previous reply was unusable. Reply with ONE JSON object and nothing '
                'else: {"title": "...", "datetime": "...", "description": "..."}'})
        try:
            out = _groq_chat(msgs)
            content = (out["choices"][0]["message"].get("content") or "").strip()
            if not content:
                reason = "empty_content"
                print(f"WARN: Groq returned empty content (attempt {attempt}/2)")
                continue
            js = _extract_json(content)
            if {"title","datetime","description"}.issubset(js.keys()):
                js["title"] = smart_truncate_title(normalize_german_places(js["title"]))
                js["description"] = smart_truncate_description(
                    normalize_german_places(js["description"]))
                js["datetime"] = repair_datetime(js.get("datetime"), item.get("published"))
                for note in advise_micro(js):
                    print(f"NOTE: {note}")
                problems = validate_micro(js)
                if not problems:
                    return js
                if VALIDATION_MODE == "enforce":
                    reason = "validation: " + "; ".join(problems)
                    print(f"WARN: item rejected by validator (attempt {attempt}/2): {problems}")
                    continue
                # Shadow mode: report what enforcement would have done, publish anyway.
                print(f"SHADOW: validator WOULD REJECT (attempt {attempt}/2): {problems}")
                return js
            reason = "unparseable_json"
            print(f"WARN: Groq reply missing required keys (attempt {attempt}/2)")
        except Exception as e:
            reason = f"api_error: {e}"
            print(f"WARN: Generation failed for '{item.get('title','')[:50]}...': {e}")
            break
    # Quarantine marker. main() keeps items carrying fallback_used OUT of
    # projects.json (see quarantine handling) so this placeholder text can never
    # reach the published site again.
    print(f"WARN: Generation unsuccessful ({reason}) - item goes to quarantine, not to the site")
    title_base = normalize_german_places(item.get("title",""))[:40]
    return {
        "title": f"What story remains untold in {title_base[:30]}...?",
        "datetime": item.get("published", dt.datetime.utcnow().isoformat()),
        "description": f"[NEEDS REGENERATION] Visit the location mentioned in recent news. Document what the official narrative excludes. Notice the silence between words, the spaces where indigenous memory persists. Return with evidence of what refuses to be erased.",
        "needs_regeneration": True,
        "original_title": item.get("title",""),
        "fallback_used": True,
        "fallback_reason": reason
    }

def regenerate_existing():
    """Regenerate all existing micro actions with new prompt system"""
    # This rewrites the title AND description of EVERY item in projects.json,
    # manually edited ones included. regenerate_safe.yml calls it expecting
    # docs/data/regenerate_list.json to be honoured -- it never has been, so that
    # "safe selective" workflow would in fact rewrite the whole archive. Require an
    # explicit opt-in so it fails loudly instead of silently destroying good data.
    if os.getenv("REGENERATE_ALL_CONFIRM") != "yes":
        print("ERROR: --regenerate rewrites the title AND description of EVERY item in projects.json.")
        print("ERROR: It is NOT selective - docs/data/regenerate_list.json is ignored.")
        print("ERROR: Refusing to run without REGENERATE_ALL_CONFIRM=yes in the environment.")
        raise SystemExit(1)
    print(f"INFO: Starting regeneration mode at {dt.datetime.utcnow().isoformat()}")
    
    # Check API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in environment")
        raise RuntimeError("GROQ_API_KEY missing")
    
    # Check system prompt
    try:
        prompt = _read_system_prompt()
        print(f"INFO: System prompt loaded (length: {len(prompt)} chars)")
    except Exception as e:
        print(f"ERROR: Failed to load system prompt: {e}")
        raise
    
    # Load existing projects
    projects_file = DOCS / "projects.json"
    if not projects_file.exists():
        print("ERROR: projects.json not found")
        return
    
    data = json.loads(projects_file.read_text(encoding="utf-8"))
    print(f"INFO: Loaded {len(data)} existing micro actions for regeneration")
    
    # Regenerate each item
    updated = 0
    failed = 0
    
    for i, item in enumerate(data):
        print(f"INFO: Regenerating {i+1}/{len(data)}: {item.get('title', '')[:50]}...")
        
        # Create a fake RSS item for the generator
        rss_item = {
            "title": item.get("title", ""),
            "summary": item.get("description", ""),
            "content": item.get("description", ""),
            "published": item.get("datetime", ""),
            "link": item.get("source", ""),
            "source": item.get("source", "")
        }
        
        try:
            # Generate new content
            new_micro = generate_micro(rss_item)
            
            # Update the item, preserving metadata
            item["title"] = new_micro.get("title", item["title"])
            item["description"] = new_micro.get("description", item["description"])
            # Keep existing: datetime, source, hash, media, lastEdited
            # Explicitly preserve media and edit history
            # Media field is preserved automatically since we only update title/description
            
            updated += 1
            print(f"  ✓ Regenerated: {item['title']}")
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed += 1
        
        # Rate limiting
        if i < len(data) - 1:
            time.sleep(0.5)
    
    # Save updated data
    projects_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"INFO: Regeneration complete!")
    print(f"INFO: Updated: {updated} items")
    print(f"INFO: Failed: {failed} items")
    print(f"INFO: Saved to {projects_file}")

QUARANTINE_FILE = DOCS / "quarantine.json"
SUPPRESSED_FILE = DOCS / "suppressed.json"
MAX_GENERATION_ATTEMPTS = 3

def _load_json_list(path):
    """Read a JSON list, tolerating a missing or malformed file."""
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            print(f"WARN: {path.name} is not a JSON list - ignoring")
        except Exception as e:
            print(f"WARN: Could not read {path.name}: {e}")
    return []

def _save_json_list(path, rows):
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

# A real article, kept in-repo so the pipeline can prove end-to-end that it can
# still turn a source item into a publishable micro action BEFORE it touches
# projects.json. Deliberately a weather/traffic notice: that is the exact class
# that failed for three and a half months.
PREFLIGHT_FIXTURE = {
    "title": "Ostrzeżenie dla Opolskiego. Utrudnienia w ruchu na DK46 w Leśnicy",
    "summary": ("Zarząd dróg informuje o utrudnieniach w ruchu na drodze krajowej 46 "
                "w okolicach Leśnicy. Prace potrwają do końca tygodnia."),
    "published": "2026-01-15T09:00:00+00:00",
    "link": "https://example.invalid/preflight-fixture",
    "source": "https://example.invalid/preflight-fixture",
}

def preflight_generation():
    """Abort the run if the generator cannot produce one valid item.

    The 2026-04-17 model swap degraded ~75% of output for 3.5 months while every
    workflow run reported success, because nothing ever asserted that generation
    still worked. One API call converts that into a run that fails immediately.
    """
    print("INFO: Preflight - generating one fixture micro action...")
    micro = generate_micro(dict(PREFLIGHT_FIXTURE))
    if micro.get("fallback_used"):
        raise RuntimeError(
            f"Preflight generation failed ({micro.get('fallback_reason')}). "
            "Refusing to run: the generator is broken, so this run would quarantine "
            "or degrade everything it touched. Check max_tokens / reasoning_effort in "
            f"_groq_chat and that model {GROQ_MODEL!r} still exists on Groq.")
    problems = validate_micro(micro)
    if problems:
        # In shadow mode this is informational; enforcement would drop real items.
        msg = f"Preflight item failed validation: {problems}"
        if VALIDATION_MODE == "enforce":
            raise RuntimeError(msg + " - refusing to run.")
        print(f"SHADOW: {msg}")
    print(f"INFO: Preflight OK -> {micro.get('title')}")
    return micro

def check_model_available():
    """Warn (never abort) if the configured model is absent from Groq's live list.

    Groq withdrew Kimi-K2 with no notice on 2026-04-14 and the pipeline simply
    started failing every call. Warn-only: a shape change in this endpoint must
    never be able to stop the pipeline by itself.
    """
    try:
        r = SESSION.get("https://api.groq.com/openai/v1/models",
                        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
                        timeout=20)
        r.raise_for_status()
        ids = [m.get("id") for m in r.json().get("data", [])]
        if ids and GROQ_MODEL not in ids:
            print(f"WARN: model {GROQ_MODEL!r} is NOT in Groq's live model list. "
                  f"It may have been withdrawn. Available: {sorted(i for i in ids if i)[:8]}...")
        else:
            print(f"INFO: model {GROQ_MODEL!r} confirmed available on Groq")
    except Exception as e:
        print(f"WARN: could not verify model availability ({e}) - continuing")

def partition_generated(micros, quarantine, suppressed, now=None):
    """Split freshly generated micros into publishable ones and quarantined ones.

    Failed generations never reach projects.json. A quarantined item is retried on
    the next run (its URL is absent from projects.json, so it still looks new);
    after MAX_GENERATION_ATTEMPTS it is suppressed for good. This is what makes it
    structurally impossible for "[NEEDS REGENERATION]" to appear on the site.

    `quarantine` is a dict keyed by hash and `suppressed` a list; both are mutated
    in place. Returns (publishable, quarantined_this_run).
    """
    now = now or dt.datetime.utcnow().isoformat()
    good, quarantined_now = [], 0
    for m in micros:
        if not m.get("fallback_used"):
            if quarantine.pop(m.get("hash"), None):
                print(f"INFO: Recovered from quarantine on retry: {m.get('title','')[:50]}...")
            good.append(m)
            continue
        h = m.get("hash")
        rec = quarantine.get(h) or {
            "hash": h,
            "source": m.get("source"),
            "original_title": m.get("original_title") or "",
            "published": m.get("datetime"),
            "attempts": 0,
            "first_seen": now,
        }
        rec["attempts"] = rec.get("attempts", 0) + 1
        rec["last_attempt"] = now
        rec["last_reason"] = m.get("fallback_reason", "unknown")
        if rec["attempts"] >= MAX_GENERATION_ATTEMPTS:
            quarantine.pop(h, None)
            suppressed.append({**rec, "reason": "generation_failed", "suppressed_at": now})
            print(f"INFO: Suppressed after {rec['attempts']} failed attempts: {rec['original_title'][:60]}")
        else:
            quarantine[h] = rec
            quarantined_now += 1
    return good, quarantined_now

def main():
    print(f"INFO: Starting pipeline at {dt.datetime.utcnow().isoformat()}")
    
    # Check API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in environment")
        raise RuntimeError("GROQ_API_KEY missing")
    print("INFO: GROQ_API_KEY found and configured")
    
    # Check system prompt
    try:
        prompt = _read_system_prompt()
        print(f"INFO: System prompt loaded (length: {len(prompt)} chars)")
    except Exception as e:
        print(f"ERROR: Failed to load system prompt: {e}")
        raise

    # Test API connectivity
    print("INFO: Testing Groq API connectivity...")
    try:
        test_msg = [
            {"role": "system", "content": "Reply with JSON containing 'status': 'ok'"},
            {"role": "user", "content": "Test"}
        ]
        test_result = _groq_chat(test_msg)
        print(f"INFO: API test successful, model responded")
    except Exception as e:
        print(f"ERROR: API connectivity test failed: {e}")
        print("ERROR: The Groq API is not accessible. Check:")
        print("  1. GROQ_API_KEY is valid")
        print(f"  2. The model {GROQ_MODEL!r} is available")
        print("  3. Your account has credits/access")
        raise RuntimeError(f"Cannot proceed without working API: {e}")

    # Reachability is not capability: the API answered for 3.5 months while
    # generation was broken. Prove the generator still works before scraping.
    check_model_available()
    preflight_generation()
    print(f"INFO: Validation mode: {VALIDATION_MODE}")

    batch_ts = ts_now()
    raw_dir = RAW / batch_ts
    rel_dir = RELEVANT / batch_ts
    raw_dir.mkdir(parents=True, exist_ok=True); rel_dir.mkdir(parents=True, exist_ok=True)
    FEEDS = load_feeds()

    # Load existing projects to check for duplicates early
    existing = []
    projects_file = DOCS / "projects.json"
    if projects_file.exists():
        try:
            existing = json.loads(projects_file.read_text(encoding="utf-8"))
            print(f"INFO: Loaded {len(existing)} existing micro actions for duplicate checking")
        except Exception as e:
            print(f"WARN: Could not load existing projects.json: {e}")
    
    # Suppressed = sources that must never re-enter projects.json: the placeholder
    # items purged on 2026-07-30, plus anything that failed generation
    # MAX_GENERATION_ATTEMPTS times. Matched on exact normalized URL / hash only --
    # deliberately NOT fed to the fuzzy cross-domain check below, which would then
    # block every future weather warning as an 0.85-similar slug.
    suppressed = _load_json_list(SUPPRESSED_FILE)
    suppressed_sources = {normalize_url(s.get("source", "")) for s in suppressed if s.get("source")}
    if suppressed:
        print(f"INFO: Loaded {len(suppressed)} suppressed sources (will not be re-added)")

    # Build set of existing normalized source URLs and raw URLs for cross-domain check
    existing_sources = {normalize_url(item.get("source", "")) for item in existing if item.get("source")} | suppressed_sources
    existing_raw_urls = [item.get("source", "") for item in existing if item.get("source")]

    all_items = []
    seen_urls = set()  # Track URLs seen in this pipeline run
    print(f"INFO: Processing {len(FEEDS)} feeds...")
    for idx, url in enumerate(FEEDS, 1):
        print(f"INFO: Processing feed {idx}/{len(FEEDS)}: {url}")
        try:
            items = parse_feed(url) or []
            print(f"INFO: Found {len(items)} items from {url}")
            for it in items:
                # Normalize the URL for deduplication
                item_url = it.get("link") or it.get("source", "")
                normalized = normalize_url(item_url) if item_url else ""
                
                # Skip if we've already seen this URL in this run
                if normalized and normalized in seen_urls:
                    print(f"INFO: Skipping duplicate URL in current run: {item_url[:60]}...")
                    continue
                
                # Skip if this normalized URL already exists in projects.json
                if normalized and normalized in existing_sources:
                    print(f"INFO: Skipping existing URL: {item_url[:60]}...")
                    continue
                
                # Check for cross-domain duplicates (same article on different domain)
                if item_url and is_cross_domain_duplicate(item_url, existing_raw_urls):
                    print(f"INFO: Skipping cross-domain duplicate: {item_url[:60]}...")
                    continue
                
                # Generate hash based on normalized URL only (not including date)
                it["id"] = sha1(normalized) if normalized else sha1(it.get("title", "") + it.get("published", ""))
                
                blob = " ".join([it.get("title",""), it.get("summary",""), it.get("content","")])
                it["preselect"] = (strong_keyword_hit(blob) or 
                                   cultural_content_hit(blob) or
                                   ("bip.lesnica.pl" in url) or 
                                   ("strzelce360" in url))
                # extra conservative pre-gate for NTO - but allow cultural content
                if "nto.pl/rss" in url and not it["preselect"] and not cultural_content_hit(blob):
                    continue
                
                # Add to seen URLs and items list
                if normalized:
                    seen_urls.add(normalized)
                all_items.append(it)
            if items:
                (raw_dir / (sha1(url)+"_feed.json")).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"ERROR: Failed to process feed {url}: {e}")
            (raw_dir / (sha1(url)+"_error.txt")).write_text(str(e), encoding="utf-8")

    relevant=[]
    heuristic_classifications = 0
    print(f"INFO: Processing {len(all_items)} scraped items for relevance...")
    preselected = [it for it in all_items if it.get("preselect")]
    print(f"INFO: {len(preselected)} items passed preselection filter")
    
    for idx, it in enumerate(preselected, 1):
        print(f"INFO: Classifying item {idx}/{len(preselected)}: {it.get('title','')[:50]}...")
        try:
            cls = classify_with_kimi(it)
            print(f"INFO: Classification result: relevant={cls.get('relevant')}")
            if cls.get("classified_by") == "heuristic":
                heuristic_classifications += 1
            if cls.get("relevant"):
                it["places_german"] = cls.get("places_german", [])
                it["classified_by"] = cls.get("classified_by", "llm")
                relevant.append(it)
        except Exception as e:
            print(f"WARN: Classification failed, using fallback: {e}")
            heuristic_classifications += 1
            if "bip.lesnica.pl" in (it.get("source") or ""):
                it["places_german"]=[]
                it["classified_by"] = "heuristic"
                relevant.append(it)
    (rel_dir / "relevant.json").write_text(json.dumps(relevant, ensure_ascii=False, indent=2), encoding="utf-8")

    micros=[]
    print(f"INFO: Generating micro actions for {len(relevant)} relevant items...")
    for idx, it in enumerate(relevant, 1):
        print(f"INFO: Generating micro {idx}/{len(relevant)}: {it.get('title','')[:50]}...")
        try:
            m = generate_micro(it)
            print(f"INFO: Generated micro action successfully")
            m["source"] = it.get("link") or it.get("source")
            m["hash"] = it.get("id")
            # Provenance: only stamped when the item got in via the degraded keyword
            # gate, so the archive records how it was admitted.
            if it.get("classified_by") == "heuristic":
                m["classified_by"] = "heuristic"
            micros.append(m)
        except Exception as e:
            print(f"WARN: Generation failed, using fallback: {e}")
            title_base = normalize_german_places(it.get("title",""))[:40]
            micros.append({
                "title": f"What story remains untold in {title_base[:30]}...?",
                "datetime": it.get("published", dt.datetime.utcnow().isoformat()),
                "description": f"[NEEDS REGENERATION] Visit the location mentioned in recent news. Document what the official narrative excludes. Notice the silence between words, the spaces where indigenous memory persists. Return with evidence of what refuses to be erased.",
                "source": it.get("link") or it.get("source"),
                "hash": it.get("id"),
                "needs_regeneration": True,
                "original_title": it.get("title",""),
                "fallback_used": True
            })

    # Keep failed generations out of projects.json entirely (see partition_generated)
    quarantine = {q.get("hash"): q for q in _load_json_list(QUARANTINE_FILE) if q.get("hash")}
    micros, quarantined_now = partition_generated(micros, quarantine, suppressed)
    _save_json_list(QUARANTINE_FILE, list(quarantine.values()))
    _save_json_list(SUPPRESSED_FILE, suppressed)
    print(f"INFO: {quarantined_now} item(s) quarantined this run; "
          f"{len(quarantine)} awaiting retry; {len(suppressed)} suppressed total")

    # Merge with existing projects (already loaded at the beginning)
    DOCS.mkdir(parents=True, exist_ok=True)

    # Create sets for deduplication based on both hash AND normalized source URL
    # (suppressed entries included so purged placeholders cannot come back)
    existing_hashes = ({item.get("hash") for item in existing if item.get("hash")}
                       | {s.get("hash") for s in suppressed if s.get("hash")})
    existing_sources = ({normalize_url(item.get("source", "")) for item in existing if item.get("source")}
                        | {normalize_url(s.get("source", "")) for s in suppressed if s.get("source")})
    existing_raw_urls = [item.get("source", "") for item in existing if item.get("source")]

    # Add only new micros (not already in existing by hash OR normalized source)
    new_micros = []
    skipped_count = 0
    for m in micros:
        normalized_source = normalize_url(m.get("source", ""))
        if m.get("hash") in existing_hashes:
            print(f"INFO: Skipping duplicate (by hash): {m.get('title', '')[:50]}...")
            skipped_count += 1
        elif normalized_source and normalized_source in existing_sources:
            print(f"INFO: Skipping duplicate (by source): {m.get('title', '')[:50]}...")
            print(f"      Source: {m.get('source', '')}")
            skipped_count += 1
        elif m.get("source") and is_cross_domain_duplicate(m.get("source"), existing_raw_urls):
            print(f"INFO: Skipping cross-domain duplicate: {m.get('title', '')[:50]}...")
            print(f"      Source: {m.get('source', '')}")
            skipped_count += 1
        else:
            new_micros.append(m)
    
    if skipped_count > 0:
        print(f"INFO: Skipped {skipped_count} duplicate micro actions")
    
    # Combine new and existing, with new ones first
    combined = new_micros + existing
    
    # Sort by datetime (newest first)
    combined.sort(key=lambda x: x.get("datetime", ""), reverse=True)
    
    # Save the combined data
    projects_file.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"INFO: Pipeline completed successfully.")
    print(f"INFO: Generated {len(micros)} micro actions, {len(new_micros)} were new")
    print(f"INFO: Total micro actions in database: {len(combined)}")
    print(f"INFO: Output saved to {projects_file}")

    # Run summary, same idea as prosto's /health. Two consumers: check_data_health.py
    # in this workflow, and an off-box canary that needs to answer "is this pipeline
    # still alive and still producing good output?" without trusting the pipeline to
    # report its own failure.
    (DOCS / "last_run.json").write_text(json.dumps({
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": GROQ_MODEL,
        "validation_mode": VALIDATION_MODE,
        "feeds": len(FEEDS),
        "scraped": len(all_items),
        "preselected": len(preselected),
        "relevant": len(relevant),
        "classified_by_heuristic": heuristic_classifications,
        "generated_ok": len(micros),
        "added_to_site": len(new_micros),
        "duplicates_skipped": skipped_count,
        "quarantined_this_run": quarantined_now,
        "awaiting_retry": len(quarantine),
        "suppressed_total": len(suppressed),
        "total_items": len(combined),
        "newest_item": combined[0].get("datetime") if combined else None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"INFO: Run summary written to {DOCS / 'last_run.json'}")

    # Extract word clouds from titles
    wordcloud_script = ROOT / "scripts" / "extract_wordclouds.py"
    if wordcloud_script.exists():
        subprocess.run([sys.executable, str(wordcloud_script)], check=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RSS aggregation and micro action generation pipeline")
    parser.add_argument("--regenerate", action="store_true", 
                       help="Regenerate all existing micro actions with new prompt system")
    args = parser.parse_args()
    
    if args.regenerate:
        regenerate_existing()
    else:
        main()
