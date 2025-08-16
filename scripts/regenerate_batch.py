#!/usr/bin/env python3
"""Regenerate content in small batches"""

import json
import re
import sys
import time
from pathlib import Path
import requests
from tenacity import retry, wait_exponential, stop_after_attempt

# Setup paths
ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs/data"
SECRETS = ROOT / "secrets"

# German place name mappings
GERMAN_MAP = {
    r"\bLeśnica\b|\bLesnica\b": "Leschnitz",
    r"\bStrzelce Opolskie\b": "Gross Strehlitz",
    r"\bOpole\b|\bOpolu\b|\bOpolski(e|m|a)?\b": "Oppeln",
    r"\bGórny Śląsk\b": "Oberschlesien"
}

def normalize_german_places(text):
    """Normalize place names to German"""
    out = text or ""
    for pat, repl in GERMAN_MAP.items():
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out

def smart_truncate_title(text, min_len=45, max_len=58):
    """Truncate title at word boundary"""
    if not text:
        return ""
    text = text.rstrip('?')
    if len(text) <= max_len:
        return text + '?'
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > min_len:
        return truncated[:last_space].rstrip() + '?'
    return text[:min_len].rstrip() + '?'

@retry(wait=wait_exponential(multiplier=1, max=10), stop=stop_after_attempt(3))
def groq_chat(messages, api_key):
    """Call Groq API"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    payload = {
        "model": "moonshotai/kimi-k2-instruct",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 600
    }
    
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=10
    )
    response.raise_for_status()
    return response.json()

def extract_json(text):
    """Extract JSON from response"""
    import re
    patterns = [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{[^{}]*\}']
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1) if '```' in pattern else match.group(0))
            except: pass
    try:
        return json.loads(text)
    except:
        return {}

def regenerate_item(item, api_key):
    """Regenerate a single item"""
    # Read the new system prompt
    prompt_file = SECRETS / "SYSTEM_PROMPT.local.txt"
    if not prompt_file.exists():
        raise RuntimeError("System prompt not found")
    base_prompt = prompt_file.read_text(encoding="utf-8")
    
    sys_prompt = base_prompt + """
Create critical questions and artistic micro actions.
Title: Question 45-58 chars exposing hidden goals
Description: Atmospheric action with sensual details (max 500 chars)
Never use "DATAsculptor". Use: Settler/Invader/Occupier instead of colonial.
Return JSON with "title" and "description"."""
    
    user_prompt = f"""Transform to critical question and atmospheric action:
Original: {item.get('title', '')}
Description: {item.get('description', '')[:200]}...
Create question revealing hidden agenda and sensual micro action.
JSON with "title" and "description"."""
    
    try:
        result = groq_chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ], api_key)
        
        js = extract_json(result["choices"][0]["message"]["content"])
        if "title" in js and "description" in js:
            return {
                "title": smart_truncate_title(normalize_german_places(js["title"])),
                "description": normalize_german_places(js["description"])[:500]
            }
    except Exception as e:
        print(f"  API error: {e}")
    
    # Fallback: clean existing
    desc = re.sub(r"DATAsculptor\s*", "", item.get("description", ""))
    return {
        "title": smart_truncate_title(normalize_german_places(item.get("title", ""))),
        "description": normalize_german_places(desc)[:500]
    }

def main():
    # Get API key from command line
    if len(sys.argv) < 2:
        print("Usage: python3 regenerate_batch.py YOUR_API_KEY [start_index] [count]")
        return 1
    
    api_key = sys.argv[1]
    start_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    # Load data
    projects_file = DOCS / "projects.json"
    data = json.loads(projects_file.read_text(encoding="utf-8"))
    print(f"Loaded {len(data)} items")
    
    # Process batch
    end_idx = min(start_idx + count, len(data))
    print(f"Processing items {start_idx} to {end_idx}...")
    
    for i in range(start_idx, end_idx):
        item = data[i]
        print(f"\n[{i+1}] {item['title'][:40]}...")
        
        new_content = regenerate_item(item, api_key)
        item["title"] = new_content["title"]
        item["description"] = new_content["description"]
        
        print(f"  ✓ {new_content['title']}")
        time.sleep(0.5)  # Rate limiting
    
    # Save
    projects_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved. Next batch: python3 regenerate_batch.py API_KEY {end_idx} {count}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())