#!/usr/bin/env python3
"""Fix single problematic micro action that contains raw Polish RSS text"""

import json
import pathlib
import sys
import os
from datetime import datetime

# Add parent directory to path to import from pipeline
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from scripts.pipeline import generate_micro, _read_system_prompt, _groq_chat

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "data"

def fix_problematic_item():
    """Fix the specific item with Polish raw text"""
    
    # Hash of the problematic item
    PROBLEM_HASH = "9518f5f24b98ca363fb22bda5e6ac70eb201048b"
    
    # Load projects
    projects_file = DOCS / "projects.json"
    if not projects_file.exists():
        print("ERROR: projects.json not found")
        return False
    
    data = json.loads(projects_file.read_text(encoding="utf-8"))
    print(f"Loaded {len(data)} micro actions")
    
    # Find the problematic item
    found = False
    for i, item in enumerate(data):
        if item.get("hash") == PROBLEM_HASH:
            print(f"\nFound problematic item at index {i}:")
            print(f"  Title: {item.get('title', '')[:60]}...")
            print(f"  Description starts with: {item.get('description', '')[:100]}...")
            
            # Check if it's already been fixed
            if "[NEEDS REGENERATION]" not in item.get("description", "") and \
               "Położone w południowej części" not in item.get("description", ""):
                print("  Item appears to already be fixed!")
                return True
            
            # Create RSS-like item for regeneration
            rss_item = {
                "title": "To miasto kiedyś było stolicą księstwa. Teraz jest trochę zapomniane",
                "summary": "Głubczyce (Leobschütz) in southern Opole voivodeship has rich ducal history",
                "content": "Historic town with ducal past, large church, renovated market square, 2km park",
                "published": item.get("datetime", ""),
                "link": item.get("source", ""),
                "source": item.get("source", "")
            }
            
            try:
                print("\nRegenerating with AI...")
                new_micro = generate_micro(rss_item)
                
                # Update the item
                item["title"] = new_micro.get("title", item["title"])
                item["description"] = new_micro.get("description", item["description"])
                
                # Remove fallback flags if they exist
                item.pop("needs_regeneration", None)
                item.pop("fallback_used", None)
                item.pop("original_title", None)
                
                print(f"\nRegenerated successfully:")
                print(f"  New title: {item['title']}")
                print(f"  New description: {item['description'][:150]}...")
                
                found = True
                break
                
            except Exception as e:
                print(f"\nERROR: Failed to regenerate: {e}")
                print("Will mark with generic placeholder instead...")
                
                item["title"] = "What ducal memories haunt Leobschütz's silent park?"
                item["description"] = "Walk the two-kilometer park at dusk where the duchy once bloomed. Press wet leaves between pages of tourist brochures that forget 1945. Document the scent of earth that remembers nobility erased. Return weekly to witness how official heritage plaques avoid mentioning who lived here before the current residents arrived."
                
                # Remove fallback flags
                item.pop("needs_regeneration", None)
                item.pop("fallback_used", None)
                item.pop("original_title", None)
                
                found = True
                break
    
    if not found:
        print(f"\nERROR: Could not find item with hash {PROBLEM_HASH}")
        return False
    
    # Save the updated data
    projects_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved updated projects.json")
    return True

if __name__ == "__main__":
    # Check for API key
    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY not found in environment")
        print("Run: export GROQ_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Fix the item
    success = fix_problematic_item()
    sys.exit(0 if success else 1)