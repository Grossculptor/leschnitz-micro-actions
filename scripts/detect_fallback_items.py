#!/usr/bin/env python3
"""Detect micro actions that might be using fallback generation or contain raw RSS text"""

import json
import pathlib
import re
from typing import List, Dict

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "data"

def detect_problematic_items() -> List[Dict]:
    """Detect items that might be fallback-generated or contain raw RSS text"""
    
    projects_file = DOCS / "projects.json"
    if not projects_file.exists():
        print("ERROR: projects.json not found")
        return []
    
    data = json.loads(projects_file.read_text(encoding="utf-8"))
    print(f"Analyzing {len(data)} micro actions...\n")
    
    problematic = []
    
    # Patterns that indicate raw RSS content or fallback generation
    rss_patterns = [
        r"położone w",  # Polish "located in"
        r"województw",  # Polish "voivodeship"
        r"powszechnie",  # Polish "commonly"
        r"uważane",  # Polish "considered"
        r"atrakcyjne turystycznie",  # Polish "tourist attractive"
        r"szczycą się",  # Polish "pride themselves"
        r"można znaleźć",  # Polish "can be found"
        r"naprawdę sporo",  # Polish "really many"
        r"nie sposób",  # Polish "it's impossible not to"
        r"wokół miasteczka",  # Polish "around the town"
        r"\[NEEDS REGENERATION\]",  # Our new fallback marker (escaped brackets)
        r"What story remains untold in",  # Our new fallback title pattern
    ]
    
    # HTML entities that shouldn't be in properly processed text
    html_entities = [
        r"&oacute;",
        r"&aacute;",
        r"&quot;",
        r"&nbsp;",
        r"&lt;",
        r"&gt;",
        r"&#\d+;"
    ]
    
    # Check for items with fallback flags
    for item in data:
        issues = []
        
        # Check for explicit fallback flags
        if item.get("needs_regeneration"):
            issues.append("Has needs_regeneration flag")
        if item.get("fallback_used"):
            issues.append("Has fallback_used flag")
        
        # Check for RSS patterns in description
        desc = item.get("description", "").lower()
        title = item.get("title", "").lower()
        
        for pattern in rss_patterns:
            if re.search(pattern, desc, re.IGNORECASE):
                issues.append(f"Contains RSS pattern: '{pattern}'")
                break
        
        # Check for HTML entities
        for entity in html_entities:
            if re.search(entity, desc) or re.search(entity, title):
                issues.append(f"Contains HTML entity: '{entity}'")
                break
        
        # Check for very short descriptions (might be truncated RSS)
        if len(desc) < 100 and "?" not in desc:
            issues.append("Very short description without question")
        
        # Check if title is too long or doesn't end with ?
        if len(title) > 60:
            issues.append(f"Title too long ({len(title)} chars)")
        if not title.endswith("?"):
            issues.append("Title doesn't end with ?")
        
        # Check for missing artistic language
        artistic_keywords = ["smell", "scent", "dusk", "dawn", "whisper", "silence", 
                           "memory", "erase", "indigenous", "settler", "expansionist",
                           "document", "witness", "return", "collect", "trace"]
        if not any(kw in desc.lower() for kw in artistic_keywords):
            issues.append("Missing artistic/sensory language")
        
        if issues:
            problematic.append({
                "hash": item.get("hash", "unknown"),
                "title": item.get("title", "")[:80],
                "description_preview": item.get("description", "")[:150],
                "issues": issues,
                "source": item.get("source", "")
            })
    
    return problematic

def main():
    """Main function to run detection and report results"""
    
    problematic = detect_problematic_items()
    
    if not problematic:
        print("✅ No problematic items detected!")
        print("All micro actions appear to be properly generated.")
        return
    
    print(f"⚠️  Found {len(problematic)} potentially problematic items:\n")
    print("=" * 80)
    
    for i, item in enumerate(problematic, 1):
        print(f"\n{i}. Hash: {item['hash']}")
        print(f"   Title: {item['title']}")
        print(f"   Description: {item['description_preview']}...")
        print(f"   Issues:")
        for issue in item['issues']:
            print(f"     - {issue}")
        print(f"   Source: {item['source']}")
        print("-" * 80)
    
    print(f"\n📊 Summary:")
    print(f"   Total problematic items: {len(problematic)}")
    
    # Count issue types
    issue_counts = {}
    for item in problematic:
        for issue in item['issues']:
            key = issue.split(':')[0].strip()
            issue_counts[key] = issue_counts.get(key, 0) + 1
    
    print(f"\n   Issues by type:")
    for issue_type, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"     - {issue_type}: {count} items")
    
    print(f"\n💡 Recommendation:")
    if any("NEEDS REGENERATION" in str(item['issues']) for item in problematic):
        print("   Run: python3 scripts/pipeline.py --regenerate")
        print("   to regenerate items marked with NEEDS REGENERATION")
    else:
        print("   Review the listed items and consider regenerating them")
        print("   Use: python3 scripts/fix_single_item.py")
        print("   to fix individual items")

if __name__ == "__main__":
    main()