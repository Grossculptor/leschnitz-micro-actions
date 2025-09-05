#!/usr/bin/env python3
"""Regenerate all micro action content (titles and descriptions) with new prompt system"""

import json
import re
import os
import sys
import time
import base64
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
    r"\bpowiat strzelecki\b|\bPowiat strzelecki\b": "Kreis Gross Strehlitz",
    r"\bOpole\b|\bOpolu\b|\bOpolski(e|m|a)?\b": "Oppeln",
    r"\bGórny Śląsk\b|\bGórny Sląsk\b|\bGórny Śląsku\b|\bGorny Slask\b": "Oberschlesien",
    r"\bGrodzisko\b": "Burghof",
    r"\bGąsiorowice\b|\bGasiorowice\b": "Gonschiorowitz",
    r"\bZawadzkie\b": "Zawadzki",
    r"\bJemielnica\b": "Imielnitz",
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

def read_system_prompt():
    """Read the system prompt from file or environment"""
    # Try environment variable first
    prompt = os.getenv("SYSTEM_PROMPT")
    if prompt:
        try:
            # If it's base64 encoded
            decoded = base64.b64decode(prompt).decode('utf-8')
            return decoded
        except:
            # If it's plain text
            return prompt
    
    # Try local file
    prompt_file = SECRETS / "SYSTEM_PROMPT.local.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    
    raise RuntimeError("System prompt not found")

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
        "model": "moonshotai/Kimi-K2-Instruct-0905",
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

def regenerate_micro_action(item):
    """Regenerate both title and description for a micro action"""
    
    # Get the new system prompt
    base_prompt = read_system_prompt()
    
    # System prompt for generation
    sys_prompt = base_prompt + """
You create critical questions and artistic micro actions revealing hidden PR goals.
RULES: 
- Title: A QUESTION 45-58 chars exposing propaganda goals
- Description: Atmospheric micro action protocol with sensual details (smell, mood, atmosphere)
- English with German place names (Leschnitz, Oppeln, Gross Strehlitz)
- Focus on marginalization, exposing PR tricks, restoring dignity
- Grade 10 readability
- Never use "DATAsculptor" or "colonial" directly
- Use alternatives: Settler, Invader, Occupier, Expansionist, Usurper
Return JSON with "title" and "description" keys."""
    
    # Extract keywords from existing title
    kws = re.findall(r"[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż\-]{4,}", item.get("title", ""))[:4]
    
    user_prompt = f"""Transform this into critical question and artistic micro action:
Original title: {item.get('title', '')}
Current description: {item.get('description', '')[:200]}...
Keywords to use: {kws}

Create:
1. Title: Critical question revealing hidden agenda (45-58 chars)
2. Description: Atmospheric micro action with sensual details (max 500 chars)

Focus on exposing PR tricks, revealing what's missing, restoring dignity.
Return JSON with "title" and "description"."""
    
    try:
        result = groq_chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        js = extract_json(result["choices"][0]["message"]["content"])
        if "title" in js and "description" in js:
            title = normalize_german_places(js["title"])
            desc = normalize_german_places(js["description"])
            return {
                "title": smart_truncate_title(title),
                "description": desc[:500]
            }
    except Exception as e:
        print(f"  ✗ API failed: {e}")
    
    # Fallback: clean up existing content
    title = item.get("title", "What's hidden here?")
    desc = item.get("description", "")
    
    # Remove DATAsculptor references
    desc = re.sub(r"DATAsculptor\s*", "", desc)
    desc = re.sub(r"^\s*\w+\s+", "", desc, count=1)  # Remove first word if it was after DATAsculptor
    
    return {
        "title": smart_truncate_title(normalize_german_places(title)),
        "description": normalize_german_places(desc)[:500]
    }

def main():
    print("=" * 60)
    print("REGENERATING ALL MICRO ACTION CONTENT")
    print("=" * 60)
    
    # Check requirements
    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY not set")
        print("Run: export GROQ_API_KEY=your_key_here")
        return 1
    
    try:
        prompt = read_system_prompt()
        print(f"✓ System prompt loaded ({len(prompt)} chars)")
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    
    # Load data
    projects_file = DOCS / "projects.json"
    if not projects_file.exists():
        print("ERROR: projects.json not found")
        return 1
    
    data = json.loads(projects_file.read_text(encoding="utf-8"))
    print(f"✓ Loaded {len(data)} micro actions")
    
    # Count DATAsculptor mentions
    datasculptor_count = sum(1 for item in data if "DATAsculptor" in item.get("description", ""))
    print(f"✓ Found {datasculptor_count} items with 'DATAsculptor' to fix")
    
    print("\nStarting regeneration...")
    print("-" * 40)
    
    # Process each item
    updated = 0
    failed = 0
    
    for i, item in enumerate(data):
        old_title = item.get("title", "")
        old_desc = item.get("description", "")[:50]
        
        print(f"\n[{i+1}/{len(data)}] {old_title[:40]}...")
        
        try:
            # Regenerate content
            new_content = regenerate_micro_action(item)
            
            # Update item
            changed = False
            if new_content["title"] != old_title:
                item["title"] = new_content["title"]
                print(f"  ✓ Title: {new_content['title']}")
                changed = True
            
            if new_content["description"] != item.get("description", ""):
                item["description"] = new_content["description"]
                print(f"  ✓ Desc: {new_content['description'][:60]}...")
                changed = True
            
            if changed:
                updated += 1
            else:
                print(f"  - No changes needed")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1
        
        # Rate limiting
        if i < len(data) - 1:
            time.sleep(0.5)  # Avoid hitting rate limits
    
    # Save updated data
    print("\n" + "=" * 40)
    print("Saving updated data...")
    projects_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # Final report
    print("\n✓ REGENERATION COMPLETE!")
    print("-" * 40)
    print(f"  Updated: {updated} items")
    print(f"  Failed: {failed} items")
    print(f"  Total: {len(data)} items")
    
    # Verify DATAsculptor removal
    remaining = sum(1 for item in data if "DATAsculptor" in item.get("description", ""))
    if remaining == 0:
        print(f"  ✓ All 'DATAsculptor' references removed!")
    else:
        print(f"  ⚠ {remaining} 'DATAsculptor' references remain")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())