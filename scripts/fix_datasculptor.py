#!/usr/bin/env python3
"""Quick fix to remove all DATAsculptor mentions"""

import json
import re
from pathlib import Path

# Setup paths
DOCS = Path(__file__).parent.parent / "docs/data"

def fix_datasculptor(text):
    """Remove DATAsculptor from text"""
    if not text:
        return text
    
    # Remove "DATAsculptor" and clean up
    text = re.sub(r"DATAsculptor\s*", "", text)
    
    # If text now starts with lowercase, capitalize
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    
    # Clean up double spaces
    text = re.sub(r"\s+", " ", text).strip()
    
    return text

def main():
    # Load data
    projects_file = DOCS / "projects.json"
    data = json.loads(projects_file.read_text(encoding="utf-8"))
    print(f"Loaded {len(data)} items")
    
    # Count and fix DATAsculptor mentions
    fixed = 0
    for item in data:
        old_desc = item.get("description", "")
        old_title = item.get("title", "")
        
        new_desc = fix_datasculptor(old_desc)
        new_title = fix_datasculptor(old_title)
        
        if new_desc != old_desc or new_title != old_title:
            item["description"] = new_desc
            item["title"] = new_title
            fixed += 1
            print(f"Fixed: {item['title'][:50]}...")
    
    # Save
    projects_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"\n✓ Fixed {fixed} items with DATAsculptor mentions")
    print(f"✓ Saved to {projects_file}")
    
    # Verify
    remaining = sum(1 for item in data if "DATAsculptor" in item.get("description", "") or "DATAsculptor" in item.get("title", ""))
    if remaining == 0:
        print("✓ All DATAsculptor references removed!")
    else:
        print(f"⚠ {remaining} references still remain")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())