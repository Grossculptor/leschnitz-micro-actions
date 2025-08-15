# -*- coding: utf-8 -*-
import os, re, json, time, hashlib, pathlib, datetime as dt
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
  r"\bGóra Św\.? Anny\b|\bGora Sw\.? Anny\b": "Sankt Annaberg"
}

KEYWORDS_STRONG = [
  "Leśnica","Lesnica","Leschnitz","Strzelce Opolskie","Gross Strehlitz",
  "powiat strzelecki","Kreis Gross Strehlitz","Góra Św. Anny","Sankt Annaberg",
  "Grodzisko","Gąsiorowice","Gasiorowice","Oppeln","Opole","Opolski"
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent":"Leschnitz-MicroActions/1.0 (+github)"})
TIMEOUT=30

def ts_now():
    return dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")

def normalize_german_places(text:str)->str:
    out = text or ""
    for pat, repl in GERMAN_MAP.items():
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out

def sha1(s:str)->str:
    return hashlib.sha1(s.encode("utf-8","ignore")).hexdigest()

@retry(wait=wait_exponential(multiplier=1, max=20), stop=stop_after_attempt(4))
def fetch(url:str)->requests.Response:
    r = SESSION.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r

def pull_fulltext(url:str)->str:
    try:
        html = fetch(url).text
        soup = BeautifulSoup(html, "html.parser")
        for sel in ["article",".content",".entry-content","#content",".post",".news",".art__content","main"]:
            node = soup.select_one(sel)
            if node and node.get_text(strip=True):
                return node.get_text(" ", strip=True)
        return " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))[:8000]
    except Exception:
        return ""

def parse_feed(url:str):
    try:
        fp = feedparser.parse(url)
        if fp.entries:
            out = []
            for e in fp.entries:
                link = e.get("link") or ""
                title = BeautifulSoup(e.get("title",""),"html.parser").get_text()
                summary = BeautifulSoup(e.get("summary",""),"html.parser").get_text() if e.get("summary") else ""
                published = e.get("published") or e.get("updated") or ""
                try:
                    pdt = dparser.parse(published)
                except Exception:
                    pdt = dt.datetime.utcnow()
                content = summary
                if link:
                    ft = pull_fulltext(link)
                    if ft:
                        content = ft
                out.append({
                    "title": title,
                    "summary": summary,
                    "published": pdt.isoformat(),
                    "source": link,
                    "content": content[:5000],
                    "hash": sha1(link)
                })
            return out
    except Exception:
        pass
    # HTML fallback
    try:
        html = fetch(url).text
        soup = BeautifulSoup(html,"html.parser")
        items = []
        for a in soup.find_all("a", href=True):
            if a.get_text(strip=True):
                items.append({"title":a.get_text(strip=True),"summary":"","published":dt.datetime.utcnow().isoformat(),"source":a["href"],"content":"","hash":sha1(a["href"])})
        return items
    except Exception:
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

def _groq_chat(messages, model="llama-3.1-70b-versatile"):
    """Use a known working Groq model"""
    import urllib.request, json as _json
    
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in environment")
        raise ValueError("GROQ_API_KEY not set")
    
    print(f"DEBUG: Using model {model}")
    print(f"DEBUG: API key present: {api_key[:10]}...")
    
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    payload={
        "model": model, 
        "messages": messages, 
        "temperature": 0.7, 
        "max_tokens": 1000,
        "response_format": {"type": "json_object"}  # Force JSON response
    }
    data=_json.dumps(payload).encode("utf-8")
    
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as resp:
            result = _json.loads(resp.read().decode("utf-8"))
            if "error" in result:
                print(f"GROQ API Error: {result['error']}")
                raise ValueError(f"API Error: {result['error']}")
            print(f"DEBUG: API call successful")
            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"HTTP Error {e.code}: {error_body}")
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
    # Try to parse directly
    try:
        return json.loads(text)
    except:
        pass
    # Last resort: simple heuristics
    return {}

def classify_with_kimi(item:dict)->dict:
    sys = _read_system_prompt() + "\nYou are a relevance filter for Leschnitz (Leschnitz) / Kreis Gross Strehlitz (Strzelce County) and immediate surroundings in Oberschlesien. Respond ONLY with compact JSON."
    user = f"""
Decide if the following article is relevant to Leschnitz / Kreis Gross Strehlitz / Oppeln environs (Oberschlesien).
Return JSON with keys: "relevant": boolean, "why": string, "places_german": [string].
Ignore guides/gossip/TV/clickbait/ads. Include BIP Leschnitz and Strzelce local civic content.
Title: {item.get('title','')}
Summary: {item.get('summary','')}
Content: {(item.get('content') or '')[:1200]}
"""
    try:
        print(f"DEBUG: Classifying '{item.get('title','')[:50]}...'")
        out = _groq_chat([{"role":"system","content":sys},{"role":"user","content":user}])
        text = out["choices"][0]["message"]["content"]
        js = _extract_json(text)
        # minimal validation
        if "relevant" in js:
            print(f"DEBUG: Classification successful: relevant={js.get('relevant')}")
            return js
        print(f"DEBUG: Invalid JSON response: {text[:100]}")
    except Exception as e:
        print(f"ERROR: Classification failed for '{item.get('title','')[:50]}...': {e}")
    # Fallback heuristic
    print(f"DEBUG: Using heuristic fallback for '{item.get('title','')[:50]}...'")
    return {"relevant": ("bip.lesnica.pl" in (item.get("source") or "") or strong_keyword_hit(item.get("title","")+item.get("summary","")+item.get("content",""))),
            "why":"heuristic fallback","places_german":[]}

def generate_micro(item:dict)->dict:
    sys = _read_system_prompt() + """
You write micro artistic actions in English with a clear DATAsculptor signature.
RULES: Output compact JSON with keys "title","datetime","description". Title paraphrases source & includes >=1 keyword from source; description <=500 characters; use German place names (Leschnitz, Oppeln, Gross Strehlitz, Oberschlesien/O/S).
"""
    kws = re.findall(r"[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż\-]{4,}", item.get("title",""))[:8]
    user = f"""Make ONE micro action.
Source title: {item.get('title','')}
Published: {item.get('published','')}
Available keywords: {kws}
Short gist: {item.get('summary') or (item.get('content') or '')[:400]}
Return JSON only."""
    try:
        print(f"DEBUG: Generating micro for '{item.get('title','')[:50]}...'")
        out = _groq_chat([{"role":"system","content":sys},{"role":"user","content":user}])
        js = _extract_json(out["choices"][0]["message"]["content"])
        if {"title","datetime","description"}.issubset(js.keys()):
            js["title"] = normalize_german_places(js["title"])[:200]
            js["description"] = normalize_german_places(js["description"])[:500]
            print(f"DEBUG: Generation successful")
            return js
        print(f"DEBUG: Invalid JSON response: {out['choices'][0]['message']['content'][:100]}")
    except Exception as e:
        print(f"ERROR: Generation failed for '{item.get('title','')[:50]}...': {e}")
    # Fallback: stitch minimal micro
    print(f"DEBUG: Using fallback generation for '{item.get('title','')[:50]}...'")
    return {
        "title": normalize_german_places(item.get("title",""))[:200],
        "datetime": item.get("published", dt.datetime.utcnow().isoformat()),
        "description": normalize_german_places((item.get("summary") or item.get("content",""))[:480])
    }

def main():
    print("DEBUG: Starting pipeline")
    
    # Check environment
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY missing from environment")
        raise RuntimeError("GROQ_API_KEY missing")
    print(f"DEBUG: GROQ_API_KEY found: {api_key[:10]}...")
    
    try:
        prompt = _read_system_prompt()
        print(f"DEBUG: System prompt loaded, length: {len(prompt)}")
    except Exception as e:
        print(f"ERROR: Failed to load system prompt: {e}")
        raise

    batch_ts = ts_now()
    raw_dir = RAW / batch_ts
    rel_dir = RELEVANT / batch_ts
    raw_dir.mkdir(parents=True, exist_ok=True); rel_dir.mkdir(parents=True, exist_ok=True)

    # Test API connectivity first
    print("\nDEBUG: Testing Groq API connectivity...")
    try:
        test_response = _groq_chat([
            {"role": "system", "content": "You are a helpful assistant. Respond in JSON format."},
            {"role": "user", "content": "Respond with JSON containing a single key 'status' with value 'ok'"}
        ])
        print(f"DEBUG: API test successful: {test_response['choices'][0]['message']['content']}")
    except Exception as e:
        print(f"ERROR: API connectivity test failed: {e}")
        print("ERROR: Cannot proceed without working API connection")
        return

    feeds = load_feeds()
    print(f"\nDEBUG: Processing {len(feeds)} feeds")
    
    for url in feeds:
        print(f"\nDEBUG: Fetching {url}")
        try:
            items = parse_feed(url)
            (raw_dir / (sha1(url)+"_feed.json")).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"DEBUG: Found {len(items)} items")
        except Exception as e:
            print(f"ERROR: Failed to fetch {url}: {e}")
            (raw_dir / (sha1(url)+"_error.txt")).write_text(str(e), encoding="utf-8")

    relevant=[]
    for j in raw_dir.glob("*_feed.json"):
        items = json.loads(j.read_text(encoding="utf-8"))
        for it in items:
            if not strong_keyword_hit(it.get("title","")+it.get("summary","")+it.get("content","")):
                print(f"DEBUG: Skipping (no keywords): {it.get('title','')[:50]}...")
                continue
            try:
                cl = classify_with_kimi(it)
                if cl.get("relevant"):
                    it["places_german"] = cl.get("places_german",[])
                    relevant.append(it)
                    print(f"DEBUG: Marked as relevant: {it.get('title','')[:50]}...")
            except Exception as e:
                print(f"ERROR: Classification error: {e}")
                if "bip.lesnica.pl" in (it.get("source") or ""):
                    it["places_german"]=[]
                    relevant.append(it)
    
    print(f"\nDEBUG: {len(relevant)} relevant items found")
    rel_dir.joinpath("relevant.json").write_text(json.dumps(relevant, ensure_ascii=False, indent=2), encoding="utf-8")

    existing = []
    if (DOCS / "projects.json").exists():
        existing = json.loads((DOCS / "projects.json").read_text(encoding="utf-8"))
    seen = {e["hash"] for e in existing}

    micros = []
    for it in relevant:
        if it["hash"] in seen:
            print(f"DEBUG: Skipping duplicate: {it.get('title','')[:50]}...")
            continue
        try:
            m = generate_micro(it)
            m["source"] = it.get("source","")
            m["hash"] = it["hash"]
            micros.append(m)
        except Exception as e:
            print(f"ERROR: Generation error: {e}")
            micros.append({
                "title": normalize_german_places(it.get("title",""))[:200],
                "datetime": it.get("published", dt.datetime.utcnow().isoformat()),
                "description": normalize_german_places(it.get("summary","") or it.get("content",""))[:480],
                "source": it.get("source",""),
                "hash": it["hash"]
            })
    
    print(f"\nDEBUG: Generated {len(micros)} new micro actions")
    
    combined = micros + existing
    combined.sort(key=lambda x: x.get("datetime",""), reverse=True)
    combined = combined[:100]
    
    (DOCS / "projects.json").write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DEBUG: Saved {len(combined)} total items to projects.json")
    print("DEBUG: Pipeline complete")

if __name__ == "__main__":
    main()