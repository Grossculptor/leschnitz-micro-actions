#!/usr/bin/env python3
"""Fix titles that are still truncated at 45 chars"""

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

def smart_truncate_title(text, min_len=45, max_len=58):
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

def is_truncated(title):
    """Check if a title appears to be truncated"""
    if len(title) != 45:
        return False
    
    # Get last word before ?
    last_word = title[:-1].split()[-1] if title[:-1].split() else ''
    
    # Check if last word seems incomplete
    # Very short words or words that don't end naturally
    if len(last_word) <= 3:
        return True
    if len(last_word) <= 6 and not last_word.endswith(('ing', 'ed', 'er', 'ly', 'ion', 'ent', 'ness')):
        # Check if it looks like a partial word
        common_endings = ['tion', 'sion', 'ment', 'ence', 'ance', 'ity', 'ness']
        looks_partial = True
        for ending in common_endings:
            if ending.startswith(last_word[-3:]):
                return True
        return True
    return False

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

def expand_truncated_title(item):
    """Expand a truncated title to complete the last word"""
    title = item.get("title", "")
    kws = extract_keywords(title[:-1])  # Remove ? for keyword extraction
    
    sys_prompt = """You create critical questions revealing hidden PR goals. Grade 9 readability.
RULES: Title is a QUESTION 45-58 chars exposing the propaganda goal. COMPLETE THE LAST WORD that was cut off.
English with German place names (Leschnitz, Oppeln, Gross Strehlitz), Polish keywords preserved.
Focus on marginalization, colonization, bureaucratic pressure. Return JSON with "title" key only."""
    
    user_prompt = f"""This title is cut off mid-word. Complete it properly:
Truncated: {title}
Last word appears to be: {title[:-1].split()[-1] if title[:-1].split() else ''}
Keywords: {kws}
Create a complete question 45-58 chars. FINISH THE LAST WORD.
Return JSON with "title" key."""
    
    try:
        result = groq_chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        js = extract_json(result["choices"][0]["message"]["content"])
        if "title" in js:
            new_title = normalize_german_places(js["title"])
            return smart_truncate_title(new_title)
    except Exception as e:
        print(f"    API failed: {e}")
    
    # Fallback: try to guess the completion
    last_word = title[:-1].split()[-1] if title[:-1].split() else ''
    base = title[:-1].rsplit(' ', 1)[0] if ' ' in title[:-1] else title[:-1]
    
    # Common word completions
    completions = {
        'Contro': 'Control',
        'profi': 'profit',
        'tuszuj': 'tuszuje',
        'marginali': 'marginalize',
        'Wiejsk': 'Wiejska',
        'Leschni': 'Leschnitz',
        'Maskin': 'Masking',
        'Antwor': 'Antwort',
        'Rybac': 'Rybaczówka',
    }
    
    if last_word in completions:
        return smart_truncate_title(f"{base} {completions[last_word]}")
    
    return title  # Keep original if can't fix

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
    
    # Find truncated titles
    truncated_indices = []
    for i, item in enumerate(data):
        if is_truncated(item["title"]):
            truncated_indices.append(i)
    
    print(f"Found {len(truncated_indices)} truncated titles to fix")
    
    # Process truncated titles
    fixed = 0
    
    for idx in truncated_indices:
        item = data[idx]
        old_title = item["title"]
        print(f"\nFixing: {old_title}")
        
        try:
            new_title = expand_truncated_title(item)
            if new_title and new_title != old_title and not is_truncated(new_title):
                data[idx]["title"] = new_title
                print(f"  ✓ Fixed: {new_title} ({len(new_title)} chars)")
                fixed += 1
            else:
                print(f"  - Could not fix")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Rate limiting
        if idx < truncated_indices[-1]:
            time.sleep(0.5)
    
    # Save updated data
    if fixed > 0:
        print(f"\nSaving {fixed} fixed titles...")
        projects_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    print(f"\nComplete!")
    print(f"  Fixed: {fixed} titles")
    print(f"  Total: {len(truncated_indices)} truncated titles")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())