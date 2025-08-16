#!/usr/bin/env python3
"""
Safe regeneration script with selective updates and backup capabilities
"""

import json
import os
import time
import argparse
import shutil
from pathlib import Path
from datetime import datetime
import hashlib
import re

# Paths
DOCS = Path("docs/data")
PROJECTS_FILE = DOCS / "projects.json"

def create_backup():
    """Create timestamped backup of current projects.json"""
    if not PROJECTS_FILE.exists():
        print("ERROR: projects.json not found")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = DOCS / f"projects_backup_{timestamp}.json"
    
    shutil.copy2(PROJECTS_FILE, backup_file)
    print(f"✓ Created backup: {backup_file}")
    return backup_file

def has_encoding_issues(text):
    """Check if text has encoding issues (ÃÂÃÂ patterns)"""
    if not text:
        return False
    # Look for repeated encoding issue patterns
    return "ÃÂ" in text or "Ã‚" in text

def has_datasculptor(item):
    """Check if item contains DATAsculptor references"""
    title = item.get("title", "").lower()
    desc = item.get("description", "").lower()
    return "datasculptor" in title or "datasculptor" in desc

def needs_regeneration(item, criteria):
    """Check if item needs regeneration based on criteria"""
    if criteria == "all":
        return True
    elif criteria == "encoding":
        return (has_encoding_issues(item.get("title", "")) or 
                has_encoding_issues(item.get("description", "")))
    elif criteria == "datasculptor":
        return has_datasculptor(item)
    elif criteria == "problems":
        return (has_encoding_issues(item.get("title", "")) or 
                has_encoding_issues(item.get("description", "")) or
                has_datasculptor(item))
    return False

def analyze_data():
    """Analyze current data for issues"""
    if not PROJECTS_FILE.exists():
        print("ERROR: projects.json not found")
        return
    
    data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    print(f"\n📊 Data Analysis ({len(data)} total items)")
    print("=" * 50)
    
    encoding_issues = 0
    datasculptor_refs = 0
    has_media = 0
    has_last_edited = 0
    
    for item in data:
        if has_encoding_issues(item.get("title", "")) or has_encoding_issues(item.get("description", "")):
            encoding_issues += 1
        if has_datasculptor(item):
            datasculptor_refs += 1
        if item.get("media"):
            has_media += 1
        if item.get("lastEdited"):
            has_last_edited += 1
    
    print(f"⚠️  Items with encoding issues: {encoding_issues}")
    print(f"⚠️  Items with DATAsculptor: {datasculptor_refs}")
    print(f"📷 Items with media: {has_media}")
    print(f"✏️  Items manually edited: {has_last_edited}")
    print(f"✅ Clean items: {len(data) - encoding_issues - datasculptor_refs}")
    
    # Show examples of problematic items
    if encoding_issues > 0:
        print("\n🔍 Sample encoding issues:")
        count = 0
        for item in data:
            if has_encoding_issues(item.get("title", "")):
                print(f"  - {item.get('title', '')[:60]}...")
                count += 1
                if count >= 3:
                    break
    
    if datasculptor_refs > 0:
        print("\n🔍 Items with DATAsculptor:")
        for item in data:
            if has_datasculptor(item):
                print(f"  - {item.get('title', '')[:60]}...")

def selective_regenerate(criteria="problems", test_mode=False, max_items=None):
    """Selectively regenerate items based on criteria"""
    print(f"\n🔄 Selective Regeneration")
    print(f"Criteria: {criteria}")
    print(f"Test mode: {test_mode}")
    if max_items:
        print(f"Max items: {max_items}")
    
    # Load data
    if not PROJECTS_FILE.exists():
        print("ERROR: projects.json not found")
        return
    
    data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    
    # Find items to regenerate
    items_to_regenerate = []
    for i, item in enumerate(data):
        if needs_regeneration(item, criteria):
            items_to_regenerate.append((i, item))
    
    print(f"\nFound {len(items_to_regenerate)} items to regenerate")
    
    if max_items and len(items_to_regenerate) > max_items:
        items_to_regenerate = items_to_regenerate[:max_items]
        print(f"Limited to {max_items} items for testing")
    
    if not items_to_regenerate:
        print("No items need regeneration!")
        return
    
    # Show what will be regenerated
    print("\nItems to regenerate:")
    for idx, item in items_to_regenerate[:10]:  # Show first 10
        print(f"  [{idx}] {item.get('title', '')[:50]}...")
        if item.get("media"):
            print(f"      ⚠️  Has media: {len(item['media'])} files")
        if item.get("lastEdited"):
            print(f"      ⚠️  Was manually edited")
    
    if len(items_to_regenerate) > 10:
        print(f"  ... and {len(items_to_regenerate) - 10} more")
    
    if test_mode:
        print("\n⚠️  TEST MODE - No changes will be saved")
        print("Would regenerate these items with the pipeline")
        return
    
    # Confirm
    response = input(f"\n⚠️  Regenerate {len(items_to_regenerate)} items? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled")
        return
    
    # Create backup first
    backup_file = create_backup()
    if not backup_file:
        return
    
    print(f"\n🚀 Starting regeneration...")
    print("NOTE: This would normally call the pipeline.py regeneration")
    print("For safety, the actual API calls are not implemented here")
    print("Use 'python scripts/pipeline.py --regenerate' after reviewing")
    
    # Save list of items to regenerate for pipeline
    regen_list = DOCS / "regenerate_list.json"
    regen_data = {
        "criteria": criteria,
        "indices": [idx for idx, _ in items_to_regenerate],
        "backup": str(backup_file),
        "timestamp": datetime.now().isoformat()
    }
    regen_list.write_text(json.dumps(regen_data, indent=2))
    print(f"\n✓ Saved regeneration list to {regen_list}")
    print("Run 'python scripts/pipeline.py --regenerate-selective' to execute")

def rollback(backup_file=None):
    """Rollback to a backup file"""
    backups = sorted(DOCS.glob("projects_backup_*.json"), reverse=True)
    
    if not backups:
        print("No backup files found")
        return
    
    if backup_file:
        backup_path = Path(backup_file)
        if not backup_path.exists():
            print(f"Backup file not found: {backup_file}")
            return
    else:
        # Show available backups
        print("\nAvailable backups:")
        for i, backup in enumerate(backups[:10]):
            size = backup.stat().st_size / 1024
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"  {i+1}. {backup.name} ({size:.1f}KB, {mtime})")
        
        choice = input("\nSelect backup number (or 'cancel'): ")
        if choice == "cancel":
            return
        
        try:
            idx = int(choice) - 1
            backup_path = backups[idx]
        except (ValueError, IndexError):
            print("Invalid selection")
            return
    
    # Confirm rollback
    print(f"\n⚠️  Rollback to: {backup_path.name}")
    response = input("This will replace current projects.json. Continue? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled")
        return
    
    # Create backup of current before rollback
    current_backup = create_backup()
    
    # Perform rollback
    shutil.copy2(backup_path, PROJECTS_FILE)
    print(f"✓ Rolled back to {backup_path.name}")
    print(f"✓ Current data backed up to {current_backup}")

def main():
    parser = argparse.ArgumentParser(description="Safe regeneration tool for micro actions")
    parser.add_argument("--analyze", action="store_true", 
                       help="Analyze current data for issues")
    parser.add_argument("--regenerate", choices=["all", "encoding", "datasculptor", "problems"],
                       help="Regenerate items based on criteria")
    parser.add_argument("--test", action="store_true",
                       help="Test mode - show what would be regenerated without changes")
    parser.add_argument("--max", type=int,
                       help="Maximum number of items to regenerate (for testing)")
    parser.add_argument("--rollback", nargs="?", const=True,
                       help="Rollback to a backup file")
    parser.add_argument("--backup", action="store_true",
                       help="Create a backup of current data")
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_data()
    elif args.regenerate:
        selective_regenerate(args.regenerate, args.test, args.max)
    elif args.rollback:
        if args.rollback is True:
            rollback()
        else:
            rollback(args.rollback)
    elif args.backup:
        backup_file = create_backup()
        if backup_file:
            print(f"Backup created: {backup_file}")
    else:
        # Default: analyze
        analyze_data()
        print("\nOptions:")
        print("  --analyze              Analyze data for issues")
        print("  --regenerate problems  Regenerate problematic items")
        print("  --regenerate encoding  Regenerate items with encoding issues")
        print("  --regenerate all       Regenerate everything")
        print("  --test                 Test mode (no changes)")
        print("  --max 5               Limit to 5 items")
        print("  --rollback            Rollback to a backup")
        print("  --backup              Create backup")

if __name__ == "__main__":
    main()