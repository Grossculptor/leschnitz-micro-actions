#!/usr/bin/env python3
"""
Fix severe encoding corruption in projects.json
Items with ÃÂÃÂÃÂ patterns need to be regenerated or restored
"""

import json
import re
from pathlib import Path
from datetime import datetime
import shutil

DOCS = Path("docs/data")
PROJECTS_FILE = DOCS / "projects.json"

def detect_corruption_level(text):
    """Detect how severely corrupted the text is"""
    if not text:
        return 0
    
    # Count encoding issue markers
    count = text.count('Ã')
    
    # Severe corruption if many instances
    if count > 20:
        return 3  # Severe - unrecoverable
    elif count > 5:
        return 2  # Moderate - might be fixable
    elif count > 0:
        return 1  # Light - possibly fixable
    return 0  # Clean

def attempt_fix(text):
    """Attempt to fix encoding issues"""
    if not text:
        return text
    
    # For severe corruption, truncate at first corruption
    # Look for the Ã character which indicates encoding issues
    if 'Ã' in text:
        # Find where the corruption starts
        idx = text.find('Ã')
        if idx > 0:
            # Truncate before corruption and add ellipsis
            clean_text = text[:idx].rstrip()
            # Only add ellipsis if we're actually truncating significant content
            if len(clean_text) < len(text) - 10:
                return clean_text + "..."
            else:
                # If corruption is at the very end, just remove it
                return clean_text
    
    return text

def analyze_corruption():
    """Analyze encoding corruption in current data"""
    if not PROJECTS_FILE.exists():
        print("ERROR: projects.json not found")
        return None
    
    data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    
    corrupted_items = []
    
    for i, item in enumerate(data):
        title = item.get("title", "")
        desc = item.get("description", "")
        
        title_corruption = detect_corruption_level(title)
        desc_corruption = detect_corruption_level(desc)
        
        if title_corruption > 0 or desc_corruption > 0:
            corrupted_items.append({
                "index": i,
                "hash": item.get("hash", "")[:8],
                "title": title[:80] + "..." if len(title) > 80 else title,
                "title_corruption": title_corruption,
                "desc_corruption": desc_corruption,
                "has_media": bool(item.get("media")),
                "item": item
            })
    
    return data, corrupted_items

def fix_encoding_issues():
    """Fix encoding issues in projects.json"""
    
    print("🔍 Analyzing encoding corruption...")
    data, corrupted_items = analyze_corruption()
    
    if not corrupted_items:
        print("✅ No encoding corruption found!")
        return
    
    print(f"\n⚠️  Found {len(corrupted_items)} items with encoding issues:")
    print("-" * 60)
    
    severe = 0
    moderate = 0
    light = 0
    
    for item_info in corrupted_items:
        max_corruption = max(item_info["title_corruption"], item_info["desc_corruption"])
        
        if max_corruption == 3:
            severe += 1
            marker = "🔴 SEVERE"
        elif max_corruption == 2:
            moderate += 1
            marker = "🟡 MODERATE"
        else:
            light += 1
            marker = "🟢 LIGHT"
        
        print(f"[{item_info['index']:3}] {marker} {item_info['hash']}: {item_info['title'][:50]}...")
        if item_info["has_media"]:
            print(f"      ⚠️  Has media attached")
    
    print(f"\nSummary:")
    print(f"  🔴 Severe (needs regeneration): {severe}")
    print(f"  🟡 Moderate (partial fix possible): {moderate}")
    print(f"  🟢 Light (can be fixed): {light}")
    
    # Auto-proceed with fix
    print(f"\n⚠️  Attempting to fix {len(corrupted_items)} items...")
    
    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = DOCS / f"projects_encoding_backup_{timestamp}.json"
    shutil.copy2(PROJECTS_FILE, backup_file)
    print(f"✓ Created backup: {backup_file}")
    
    # Fix items
    fixed = 0
    truncated = 0
    needs_regen = []
    
    for item_info in corrupted_items:
        idx = item_info["index"]
        item = data[idx]
        
        # Fix title
        if item_info["title_corruption"] > 0:
            original_title = item.get("title", "")
            fixed_title = attempt_fix(original_title)
            if fixed_title != original_title:
                item["title"] = fixed_title
                if item_info["title_corruption"] >= 3:
                    truncated += 1
                    needs_regen.append(idx)
                else:
                    fixed += 1
        
        # Fix description  
        if item_info["desc_corruption"] > 0:
            original_desc = item.get("description", "")
            fixed_desc = attempt_fix(original_desc)
            if fixed_desc != original_desc:
                item["description"] = fixed_desc
                if item_info["desc_corruption"] >= 3:
                    truncated += 1
                    needs_regen.append(idx)
                else:
                    fixed += 1
    
    # Save fixed data
    PROJECTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"\n✅ Fix complete!")
    print(f"  Fixed: {fixed} fields")
    print(f"  Truncated: {truncated} fields (severe corruption)")
    print(f"  Need regeneration: {len(set(needs_regen))} items")
    
    if needs_regen:
        regen_file = DOCS / "needs_regeneration.txt"
        with open(regen_file, "w") as f:
            f.write("Items that need regeneration due to severe corruption:\n")
            for idx in sorted(set(needs_regen)):
                f.write(f"{idx}: {data[idx].get('hash', '')[:8]} - {data[idx].get('title', '')[:50]}...\n")
        print(f"\n📝 List of items needing regeneration saved to: {regen_file}")
        print("Run regeneration with: python3 scripts/pipeline.py --regenerate")

if __name__ == "__main__":
    fix_encoding_issues()