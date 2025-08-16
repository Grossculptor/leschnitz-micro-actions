#!/usr/bin/env python3
"""Regenerate all existing titles as critical questions"""

import json
import re
import os
import sys
import time
from pathlib import Path
import requests
from tenacity import retry, wait_exponential, stop_after_attempt

# Setup paths
DOCS = Path(__file__).parent.parent / "docs/data"

# German place name mappings
GERMAN_MAP = {
    r"\bLeśnica\b|\bLesnica\b": "Leschnitz",
    r"\bStrzelce Opolskie\b": "Gross Strehlitz",
    r"\bOpole\b": "Oppeln",
    r"\bGóra Św\.? Anny\b|\bGora Sw\.? Anny\b": "Sankt Annaberg"
}

def normalize_german_places(text):
    """Normalize place names to German"""
    out = text or ""
    for pat, repl in GERMAN_MAP.items():
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out

def extract_keywords(title):
    """Extract up to 4 keywords from title"""
    return re.findall(r"[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż\-]{4,}", title)[:4]

@retry(wait=wait_exponential(multiplier=1, max=10), stop=stop_after_attempt(3))
def groq_chat(messages):
    """Call Groq API"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    payload = {
        "model": "moonshotai/kimi-k2-instruct",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 200
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
    """Extract JSON from response text"""
    patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'\{[^{}]*\}'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1) if '```' in pattern else match.group(0))
            except:
                pass
    
    try:
        return json.loads(text)
    except:
        return {}

def generate_question_title(item):
    """Generate a critical question title for an item"""
    kws = extract_keywords(item.get("title", ""))
    
    sys_prompt = """You create critical questions revealing hidden PR goals. Grade 9 readability.
RULES: Title is a QUESTION max 45 chars exposing the propaganda goal. Use max 3 keywords from source.
English with German place names (Leschnitz, Oppeln, Gross Strehlitz), Polish keywords preserved.
Focus on marginalization, colonization, bureaucratic pressure. Return JSON with "title" key only."""
    
    user_prompt = f"""Convert this to a critical question:
Original: {item.get('title', '')}
Keywords (use max 3): {kws}
Create question revealing hidden PR/propaganda goal. Max 45 chars.
Return JSON with "title" key."""
    
    try:
        result = groq_chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        js = extract_json(result["choices"][0]["message"]["content"])
        if "title" in js:
            title = normalize_german_places(js["title"])[:45]
            # Ensure it's a question
            if not title.endswith("?"):
                title = title[:44] + "?"
            return title
    except Exception as e:
        print(f"API failed for '{item.get('title', '')[:30]}...': {e}")
    
    # Fallback: create simple question from keywords
    if kws:
        title = f"Why promote {kws[0]}?"
        return normalize_german_places(title)[:45]
    return "What's the hidden agenda here?"

def main():
    print("Loading projects.json...")
    projects_file = DOCS / "projects.json"
    
    if not projects_file.exists():
        print("ERROR: projects.json not found")
        return 1
    
    # Load data
    data = json.loads(projects_file.read_text(encoding="utf-8"))
    print(f"Loaded {len(data)} micro actions")
    
    # Check API key
    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY not set")
        return 1
    
    # Process each item
    updated = 0
    failed = 0
    
    for i, item in enumerate(data):
        old_title = item.get("title", "")
        print(f"\n[{i+1}/{len(data)}] Processing: {old_title[:50]}...")
        
        # Skip if already a question
        if old_title.endswith("?") and len(old_title) <= 45:
            print("  Already a question, skipping")
            continue
        
        try:
            new_title = generate_question_title(item)
            if new_title and new_title != old_title:
                item["title"] = new_title
                print(f"  ✓ New: {new_title}")
                updated += 1
            else:
                print(f"  - No change")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1
        
        # Rate limiting
        if i < len(data) - 1:
            time.sleep(0.5)  # Avoid hitting rate limits
    
    # Save updated data
    print(f"\nSaving updated data...")
    projects_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print(f"\nComplete!")
    print(f"  Updated: {updated} titles")
    print(f"  Failed: {failed} titles")
    print(f"  Total: {len(data)} items")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())