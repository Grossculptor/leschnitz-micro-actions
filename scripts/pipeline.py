# -*- coding: utf-8 -*-
import os, re, json, time, hashlib, pathlib, datetime as dt, argparse
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
  "Dolna","Dollna","Kadłubiec","Kadlubietz"
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

def sha1(s:str)->str:
    return hashlib.sha1(s.encode("utf-8","ignore")).hexdigest()

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

def _groq_chat(messages, model="moonshotai/kimi-k2-instruct"):
    print(f"DEBUG: Making Groq API call with model {model}")
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Leschnitz-MicroActions/1.0"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        print(f"DEBUG: Sending request to Groq API...")
        response = SESSION.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        print(f"DEBUG: Groq API response status: {response.status_code}")
        response.raise_for_status()
        result = response.json()
        print(f"DEBUG: Groq API call successful")
        return result
    except requests.HTTPError as e:
        if e.response.text:
            print(f"Groq API Error: {e.response.text}")
        raise
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        raise

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
            return js
    except Exception as e:
        print(f"WARN: Classification failed for '{item.get('title','')[:50]}...': {e}")
    # Fallback heuristic
    return {"relevant": ("bip.lesnica.pl" in (item.get("source") or "") or strong_keyword_hit(item.get("title","")+item.get("summary","")+item.get("content",""))),
            "why":"heuristic fallback","places_german":[]}

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
    try:
        out = _groq_chat([{"role":"system","content":sys},{"role":"user","content":user}])
        js = _extract_json(out["choices"][0]["message"]["content"])
        if {"title","datetime","description"}.issubset(js.keys()):
            js["title"] = smart_truncate_title(normalize_german_places(js["title"]))
            js["description"] = normalize_german_places(js["description"])[:500]
            return js
    except Exception as e:
        print(f"WARN: Generation failed for '{item.get('title','')[:50]}...': {e}")
    # Fallback: create generic micro action when AI fails
    print(f"WARN: Using fallback generation - item needs manual review")
    title_base = normalize_german_places(item.get("title",""))[:40]
    return {
        "title": f"What story remains untold in {title_base[:30]}...?",
        "datetime": item.get("published", dt.datetime.utcnow().isoformat()),
        "description": f"[NEEDS REGENERATION] Visit the location mentioned in recent news. Document what the official narrative excludes. Notice the silence between words, the spaces where indigenous memory persists. Return with evidence of what refuses to be erased.",
        "needs_regeneration": True,
        "original_title": item.get("title",""),
        "fallback_used": True
    }

def regenerate_existing():
    """Regenerate all existing micro actions with new prompt system"""
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
        print("  2. The model 'moonshotai/kimi-k2-instruct' is available")
        print("  3. Your account has credits/access")
        raise RuntimeError(f"Cannot proceed without working API: {e}")
    
    batch_ts = ts_now()
    raw_dir = RAW / batch_ts
    rel_dir = RELEVANT / batch_ts
    raw_dir.mkdir(parents=True, exist_ok=True); rel_dir.mkdir(parents=True, exist_ok=True)
    FEEDS = load_feeds()

    all_items = []
    print(f"INFO: Processing {len(FEEDS)} feeds...")
    for idx, url in enumerate(FEEDS, 1):
        print(f"INFO: Processing feed {idx}/{len(FEEDS)}: {url}")
        try:
            items = parse_feed(url) or []
            print(f"INFO: Found {len(items)} items from {url}")
            for it in items:
                it["id"] = sha1((it.get("link") or it.get("title","")) + it.get("published",""))
                blob = " ".join([it.get("title",""), it.get("summary",""), it.get("content","")])
                it["preselect"] = strong_keyword_hit(blob) or ("bip.lesnica.pl" in url) or ("strzelce360" in url)
                # extra conservative pre-gate for NTO
                if "nto.pl/rss" in url and not it["preselect"]:
                    continue
                all_items.append(it)
            if items:
                (raw_dir / (sha1(url)+"_feed.json")).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"ERROR: Failed to process feed {url}: {e}")
            (raw_dir / (sha1(url)+"_error.txt")).write_text(str(e), encoding="utf-8")

    relevant=[]
    print(f"INFO: Processing {len(all_items)} scraped items for relevance...")
    preselected = [it for it in all_items if it.get("preselect")]
    print(f"INFO: {len(preselected)} items passed preselection filter")
    
    for idx, it in enumerate(preselected, 1):
        print(f"INFO: Classifying item {idx}/{len(preselected)}: {it.get('title','')[:50]}...")
        try:
            cls = classify_with_kimi(it)
            print(f"INFO: Classification result: relevant={cls.get('relevant')}")
            if cls.get("relevant"):
                it["places_german"] = cls.get("places_german", [])
                relevant.append(it)
        except Exception as e:
            print(f"WARN: Classification failed, using fallback: {e}")
            if "bip.lesnica.pl" in (it.get("source") or ""):
                it["places_german"]=[]
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

    # Load existing projects and merge with new ones
    DOCS.mkdir(parents=True, exist_ok=True)
    projects_file = DOCS / "projects.json"
    
    existing = []
    if projects_file.exists():
        try:
            existing = json.loads(projects_file.read_text(encoding="utf-8"))
            print(f"INFO: Loaded {len(existing)} existing micro actions")
        except Exception as e:
            print(f"WARN: Could not load existing projects.json: {e}")
    
    # Create a set of existing hashes to avoid duplicates
    existing_hashes = {item.get("hash") for item in existing if item.get("hash")}
    
    # Add only new micros (not already in existing)
    new_micros = [m for m in micros if m.get("hash") not in existing_hashes]
    
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RSS aggregation and micro action generation pipeline")
    parser.add_argument("--regenerate", action="store_true", 
                       help="Regenerate all existing micro actions with new prompt system")
    args = parser.parse_args()
    
    if args.regenerate:
        regenerate_existing()
    else:
        main()
