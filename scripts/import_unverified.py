#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import all content from workers.dev RSS feed without verification.
Bypasses classification and preselection filters.
"""

import os
import re
import json
import time
import hashlib
import pathlib
import datetime as dt
import argparse
import shutil
import tempfile
from typing import Dict, List, Optional

import requests
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dparser
from tenacity import retry, wait_exponential, stop_after_attempt

# Setup paths
ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "data"
SECRETS = ROOT / "secrets"

# Import key functions from main pipeline
import sys
sys.path.append(str(ROOT / "scripts"))

# Load German place name mappings
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
}

# Setup session
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36"
})
TIMEOUT = 20

def ts_now():
    """Current timestamp for logging"""
    return dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")

def sha1(s: str) -> str:
    """Generate SHA1 hash"""
    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()

def normalize_german_places(text: str) -> str:
    """Replace Polish names with German equivalents"""
    out = text or ""
    for pat, repl in GERMAN_MAP.items():
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out

def smart_truncate_title(text: str, min_len: int = 45, max_len: int = 58) -> str:
    """Truncate title at word boundary"""
    if not text:
        return ""
    
    text = text.rstrip('?')
    if len(text) <= min_len:
        return text + '?'
    if len(text) <= max_len:
        return text + '?'
    
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    
    if last_space > min_len:
        return truncated[:last_space].rstrip() + '?'
    return text[:min_len].rstrip() + '?'

def enhanced_normalize_url(url: str) -> str:
    """Enhanced URL normalization to prevent duplicates"""
    if not url:
        return ""
    
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    parsed = urlparse(url.lower())
    path = parsed.path
    
    # Remove double slashes
    path = re.sub(r'/+', '/', path)
    
    # Remove index files
    path = re.sub(r'/index\.(html?|php)$', '/', path)
    
    # Special handling for nto.pl comment sections
    if 'nto.pl' in parsed.netloc and '/ar/c' in path:
        path = re.sub(r'/ar/c\d+(-\d+)', r'/ar/c\1', path)
    
    # Special handling for strzelce360.pl
    if 'strzelce360.pl' in parsed.netloc and '/artykul/' in path:
        path = re.sub(r'/artykul/(\d+),.*', r'/artykul/\1', path)
    
    # Extended list of parameters to remove
    tracking_params = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'ref', 'source', 'mc_cid', 'mc_eid',
        'amp', 'output', 'page', 'print', 'mobile', 'desktop'
    }
    
    # Parse and filter query parameters
    params = parse_qs(parsed.query)
    filtered_params = {}
    for k, v in params.items():
        k_lower = k.lower()
        # Skip tracking params and amp/output params
        if k_lower not in tracking_params and not k_lower.startswith('amp'):
            filtered_params[k] = v
    
    new_query = urlencode(filtered_params, doseq=True) if filtered_params else ""
    
    # Rebuild normalized URL
    normalized = urlunparse((
        parsed.scheme or "https",
        parsed.netloc.rstrip('/'),
        path.rstrip('/') or '/',
        parsed.params,
        new_query,
        ''  # Remove fragment
    ))
    
    return normalized

def parse_datetime_robust(datetime_str: str) -> str:
    """Parse datetime string robustly and return ISO format"""
    if not datetime_str:
        return dt.datetime.utcnow().isoformat()
    
    try:
        # Try to parse with dateutil (handles many formats)
        parsed = dparser.parse(datetime_str, fuzzy=True)
        return parsed.isoformat()
    except:
        pass
    
    # Fallback: current time
    return dt.datetime.utcnow().isoformat()

def create_backup() -> Optional[pathlib.Path]:
    """Create timestamped backup of projects.json"""
    projects_file = DOCS / "projects.json"
    if not projects_file.exists():
        print("WARN: No existing projects.json to backup")
        return None
    
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = DOCS / f"projects_backup_unverified_{timestamp}.json"
    
    shutil.copy2(projects_file, backup_file)
    print(f"✓ Created backup: {backup_file}")
    return backup_file

def atomic_write(file_path: pathlib.Path, data: str) -> None:
    """Write file atomically using temp file + rename"""
    temp_fd, temp_path = tempfile.mkstemp(
        dir=file_path.parent,
        prefix=f".{file_path.stem}_",
        suffix=".tmp"
    )
    
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        
        # Atomic rename
        os.replace(temp_path, file_path)
    except:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

@retry(wait=wait_exponential(multiplier=1, max=20), stop=stop_after_attempt(4))
def fetch(url: str) -> requests.Response:
    """Fetch URL with retry logic"""
    r = SESSION.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r

def read_system_prompt() -> str:
    """Read system prompt from env or file"""
    sp = os.getenv("SYSTEM_PROMPT")
    if sp:
        try:
            import base64
            decoded = base64.b64decode(sp).decode('utf-8')
            return decoded
        except:
            return sp
    
    p = SECRETS / "SYSTEM_PROMPT.local.txt"
    if p.exists():
        return p.read_text(encoding="utf-8")
    raise RuntimeError("SYSTEM_PROMPT missing: provide env var or secrets/SYSTEM_PROMPT.local.txt")

def groq_chat(messages: List[Dict], model: str = "moonshotai/Kimi-K2-Instruct-0905") -> Dict:
    """Call Groq API"""
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
    
    response = SESSION.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30  # Standard timeout
    )
    response.raise_for_status()
    return response.json()

def extract_json(text: str) -> Dict:
    """Extract JSON from text with validation"""
    text = text.strip()
    # Remove markdown fences
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    
    # Find first balanced JSON object
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        try:
            result = json.loads(m.group(0))
            # Validate required keys
            if isinstance(result, dict):
                return result
        except:
            pass
    
    return {}

def generate_micro_action(item: Dict) -> Dict:
    """Generate micro action from RSS item"""
    sys_prompt = read_system_prompt() + """
Output JSON with exactly these keys: "title", "datetime", "description"."""
    
    # Extract keywords for generation
    kws = re.findall(r"[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż\-]{4,}", item.get("title", ""))[:4]
    
    user_prompt = f"""Transform this news item into artistic micro action.
Source title: {item.get('title', '')}
Published: {item.get('published', '')}
Available keywords: {kws}
Content: {item.get('summary') or (item.get('content') or '')[:400]}
Return JSON only."""
    
    try:
        result = groq_chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        js = extract_json(result["choices"][0]["message"]["content"])
        
        # Validate and process result
        if {"title", "datetime", "description"}.issubset(js.keys()):
            # Normalize German places
            js["title"] = smart_truncate_title(normalize_german_places(js["title"]))
            js["description"] = normalize_german_places(js["description"])[:500]
            # Normalize datetime to ISO format
            js["datetime"] = parse_datetime_robust(js.get("datetime", item.get("published", "")))
            return js
    except Exception as e:
        print(f"WARN: Generation failed: {e}")
    
    # Fallback generation
    title_base = normalize_german_places(item.get("title", ""))[:40]
    return {
        "title": f"What story remains untold in {title_base[:30]}...?",
        "datetime": parse_datetime_robust(item.get("published", "")),
        "description": f"[UNVERIFIED IMPORT - NEEDS REVIEW] Visit the location mentioned in recent news. Document what the official narrative excludes.",
        "needs_regeneration": True,
        "fallback_used": True
    }

def parse_feed(url: str) -> List[Dict]:
    """Parse RSS feed and return items"""
    try:
        response = fetch(url)
        fp = feedparser.parse(response.text)
        
        if not fp.entries:
            print(f"WARN: No entries found in feed {url}")
            return []
        
        items = []
        for idx, entry in enumerate(fp.entries[:20]):  # Limit to 20
            # Ensure we have a valid link
            link = entry.get("link", "").strip()
            if not link:
                # Generate a unique ID if no link
                link = f"https://falling-bush-1efa.thedatasculptor.workers.dev/#item-{idx}-{ts_now()}"
                print(f"WARN: No link for entry, generated: {link}")
            
            # Clean HTML from text fields
            title = BeautifulSoup(entry.get("title", ""), "html.parser").get_text()
            summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text() if entry.get("summary") else ""
            
            # Parse published date
            published = entry.get("published") or entry.get("updated") or ""
            try:
                pdt = dparser.parse(published) if published else dt.datetime.utcnow()
            except:
                pdt = dt.datetime.utcnow()
            
            items.append({
                "source": url,
                "link": link,
                "title": title,
                "summary": summary,
                "content": summary[:15000],
                "published": pdt.isoformat()
            })
        
        return items
    except Exception as e:
        print(f"ERROR: Failed to parse feed {url}: {e}")
        raise

def test_api_connectivity() -> bool:
    """Test Groq API connectivity"""
    print("INFO: Testing Groq API connectivity...")
    try:
        test_msg = [
            {"role": "system", "content": "Reply with JSON containing 'status': 'ok'"},
            {"role": "user", "content": "Test"}
        ]
        print("DEBUG: Calling Groq API...")
        result = groq_chat(test_msg)
        print("✓ API test successful")
        return True
    except Exception as e:
        print(f"✗ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main(feed_url: str, dry_run: bool = True):
    """Main import function"""
    print(f"\n{'='*60}")
    print(f"UNVERIFIED IMPORT FROM: {feed_url}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"Time: {dt.datetime.utcnow().isoformat()}")
    print(f"{'='*60}\n")
    
    # Check prerequisites
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in environment")
        return 1
    
    try:
        prompt = read_system_prompt()
        print(f"✓ System prompt loaded ({len(prompt)} chars)")
    except Exception as e:
        print(f"ERROR: Failed to load system prompt: {e}")
        return 1
    
    # Test API (optional - continue even if test fails)
    test_api_connectivity()
    
    # Load existing data
    projects_file = DOCS / "projects.json"
    existing = []
    if projects_file.exists():
        try:
            existing = json.loads(projects_file.read_text(encoding="utf-8"))
            print(f"✓ Loaded {len(existing)} existing micro actions")
        except Exception as e:
            print(f"ERROR: Failed to load existing projects.json: {e}")
            return 1
    
    # Build deduplication sets
    existing_normalized = {enhanced_normalize_url(item.get("source", "")) for item in existing if item.get("source")}
    existing_hashes = {item.get("hash") for item in existing if item.get("hash")}
    
    # Parse feed
    print(f"\nFetching feed: {feed_url}")
    try:
        items = parse_feed(feed_url)
        print(f"✓ Found {len(items)} items in feed")
    except Exception as e:
        print(f"ERROR: Failed to fetch/parse feed: {e}")
        return 1
    
    if not items:
        print("No items to process")
        return 0
    
    # Process items (NO preselection or classification)
    new_micros = []
    skipped = 0
    failed = 0
    
    for idx, item in enumerate(items, 1):
        print(f"\n[{idx}/{len(items)}] Processing: {item.get('title', '')[:50]}...")
        
        # Check for duplicates
        item_url = item.get("link") or item.get("source", "")
        normalized = enhanced_normalize_url(item_url)
        
        if normalized and normalized in existing_normalized:
            print(f"  ⟳ Skipping duplicate (exists in database)")
            skipped += 1
            continue
        
        # Generate micro action
        print(f"  ⚡ Generating micro action...")
        try:
            micro = generate_micro_action(item)
            
            # Add metadata
            micro["source"] = item_url
            micro["hash"] = sha1(normalized) if normalized else sha1(item.get("title", "") + str(idx))
            micro["unverified_import"] = True
            micro["import_timestamp"] = dt.datetime.utcnow().isoformat()
            micro["import_feed"] = feed_url
            
            # Check hash duplicate
            if micro["hash"] in existing_hashes:
                print(f"  ⟳ Skipping duplicate (hash exists)")
                skipped += 1
                continue
            
            new_micros.append(micro)
            print(f"  ✓ Generated: {micro['title']}")
            
        except Exception as e:
            print(f"  ✗ Failed to generate: {e}")
            failed += 1
        
        # Rate limiting
        if idx < len(items):
            time.sleep(0.5)  # Adaptive rate limiting
    
    # Summary
    print(f"\n{'='*60}")
    print(f"IMPORT SUMMARY:")
    print(f"  • Processed: {len(items)} items")
    print(f"  • Generated: {len(new_micros)} new micro actions")
    print(f"  • Skipped: {skipped} duplicates")
    print(f"  • Failed: {failed} items")
    print(f"{'='*60}\n")
    
    if not new_micros:
        print("No new micro actions to add")
        return 0
    
    # Prepare combined data
    combined = new_micros + existing
    
    # Sort by datetime (newest first)
    def get_sort_key(item):
        dt_str = item.get("datetime", "")
        try:
            parsed_dt = dparser.parse(dt_str) if dt_str else dt.datetime.min
            # Ensure datetime is timezone-aware for consistent comparison
            if parsed_dt.tzinfo is None:
                parsed_dt = parsed_dt.replace(tzinfo=dt.timezone.utc)
            return parsed_dt
        except:
            return dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    
    combined.sort(key=get_sort_key, reverse=True)
    
    # Save if not dry run
    if not dry_run:
        # Create backup
        backup = create_backup()
        
        # Write atomically
        print(f"Writing {len(combined)} items to projects.json...")
        try:
            json_data = json.dumps(combined, ensure_ascii=False, indent=2)
            atomic_write(projects_file, json_data)
            print(f"✓ Successfully saved to {projects_file}")
            print(f"✓ Total items in database: {len(combined)}")
        except Exception as e:
            print(f"ERROR: Failed to save: {e}")
            if backup:
                print(f"Restore from backup: {backup}")
            return 1
    else:
        print("\nDRY RUN - No changes made")
        print("To execute, run with --execute flag")
        
        # Show preview
        print("\nPreview of new items:")
        for micro in new_micros[:3]:
            print(f"  • {micro['title']}")
            print(f"    {micro['description'][:100]}...")
    
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import all content from workers.dev RSS feed without verification"
    )
    parser.add_argument(
        "--feed",
        default="https://falling-bush-1efa.thedatasculptor.workers.dev/",
        help="RSS feed URL to import from"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the import (default is dry run)"
    )
    
    args = parser.parse_args()
    
    exit_code = main(args.feed, dry_run=not args.execute)
    sys.exit(exit_code)