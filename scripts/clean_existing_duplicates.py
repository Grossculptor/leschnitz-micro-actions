#!/usr/bin/env python3
"""
Clean existing cross-domain duplicates from projects.json
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

# Import the duplicate detection functions from pipeline
import sys
sys.path.append(str(Path(__file__).parent))
from pipeline import extract_article_slug, is_cross_domain_duplicate

def main():
    projects_file = Path("docs/data/projects.json")
    
    # Load existing data
    with open(projects_file, 'r', encoding='utf-8') as f:
        projects = json.load(f)
    
    print(f"Loaded {len(projects)} micro actions")
    
    # Find duplicates
    cleaned = []
    removed = []
    seen_urls = []
    
    for item in projects:
        url = item.get('source', '')
        
        if url and is_cross_domain_duplicate(url, seen_urls):
            # Found a duplicate
            print(f"\nRemoving duplicate:")
            print(f"  Title: {item.get('title', '')[:60]}...")
            print(f"  URL: {url}")
            removed.append(item)
        else:
            cleaned.append(item)
            if url:
                seen_urls.append(url)
    
    if not removed:
        print("\nNo cross-domain duplicates found!")
        return
    
    print(f"\n{'='*60}")
    print(f"Found {len(removed)} cross-domain duplicates to remove")
    print(f"Will keep {len(cleaned)} unique micro actions")
    
    # Auto-confirm in non-interactive mode
    print("\nProceeding with cleanup...")
    
    # Create backup
    backup_file = f"docs/data/projects_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    shutil.copy2(projects_file, backup_file)
    print(f"\nBackup created: {backup_file}")
    
    # Save cleaned data
    with open(projects_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    
    # Save removed items
    with open('docs/data/removed_cross_domain_duplicates.json', 'w', encoding='utf-8') as f:
        json.dump(removed, f, ensure_ascii=False, indent=2)
    
    print(f"\nCleanup complete!")
    print(f"  Original: {len(projects)} items")
    print(f"  Cleaned: {len(cleaned)} items")
    print(f"  Removed: {len(removed)} duplicates")
    print(f"  Removed items saved to: docs/data/removed_cross_domain_duplicates.json")

if __name__ == "__main__":
    main()