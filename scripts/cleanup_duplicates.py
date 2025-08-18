#!/usr/bin/env python3
"""
Cleanup script to remove duplicate micro actions from projects.json
Keeps the oldest entry for each unique source URL and preserves media/edits
"""

import json
import pathlib
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def normalize_url(url):
    """Normalize URL to identify duplicates."""
    if not url:
        return ""
    
    parsed = urlparse(url)
    
    # Remove common tracking parameters
    tracking_params = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'ref', 'source', 'mc_cid', 'mc_eid'
    }
    
    params = parse_qs(parsed.query)
    filtered_params = {
        k: v for k, v in params.items() 
        if k.lower() not in tracking_params
    }
    
    new_query = urlencode(filtered_params, doseq=True)
    
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        parsed.path.rstrip('/'),
        parsed.params,
        new_query,
        ''
    ))
    
    return normalized

def main():
    # Load projects.json
    project_file = pathlib.Path(__file__).resolve().parents[1] / "docs" / "data" / "projects.json"
    
    if not project_file.exists():
        print("ERROR: projects.json not found")
        return
    
    with open(project_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} micro actions")
    
    # Create backup
    backup_file = project_file.parent / f"projects_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Created backup: {backup_file}")
    
    # Group items by normalized URL
    url_groups = defaultdict(list)
    for item in data:
        source = item.get('source', '')
        if source:
            normalized = normalize_url(source)
            url_groups[normalized].append(item)
    
    # Find duplicates
    duplicates_found = 0
    cleaned_data = []
    seen_normalized = set()
    
    for item in data:
        source = item.get('source', '')
        if source:
            normalized = normalize_url(source)
            
            # If we haven't seen this normalized URL yet, keep the item
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                cleaned_data.append(item)
                
                # Check if there are duplicates for this URL
                if len(url_groups[normalized]) > 1:
                    duplicates_found += len(url_groups[normalized]) - 1
                    print(f"\nKeeping oldest for: {source[:80]}...")
                    
                    # Find the item with media or manual edits to preserve
                    items_with_media = [i for i in url_groups[normalized] if i.get('media') or i.get('backgroundImage')]
                    if items_with_media:
                        # Preserve the one with media
                        preserved = items_with_media[0]
                        cleaned_data[-1] = preserved  # Replace with the one that has media
                        print(f"  Preserved version with media/background")
                    
                    print(f"  Removed {len(url_groups[normalized]) - 1} duplicate(s)")
        else:
            # Items without source are kept
            cleaned_data.append(item)
    
    # Sort by datetime (newest first)
    cleaned_data.sort(key=lambda x: x.get("datetime", ""), reverse=True)
    
    # Save cleaned data
    with open(project_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nCleanup complete!")
    print(f"Original items: {len(data)}")
    print(f"Duplicates removed: {duplicates_found}")
    print(f"Final items: {len(cleaned_data)}")
    print(f"Saved to: {project_file}")

if __name__ == "__main__":
    main()