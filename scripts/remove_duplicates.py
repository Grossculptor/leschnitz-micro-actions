#!/usr/bin/env python3
"""
Remove duplicate micro actions from projects.json based on normalized source URLs.
Keeps the first occurrence (usually the older one) and removes duplicates.
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def normalize_url(url: str) -> str:
    """Normalize URL to prevent duplicates from tracking parameters and variations."""
    if not url:
        return ""
    
    # Parse URL components
    parsed = urlparse(url)
    path = parsed.path
    
    # Special handling for nto.pl comment section identifiers
    # Convert /ar/c1-18744833, /ar/c7-18744833 etc to /ar/c-18744833
    if 'nto.pl' in parsed.netloc.lower() and '/ar/c' in path:
        path = re.sub(r'/ar/c\d+(-\d+)', r'/ar/c\1', path)
    
    # Special handling for strzelce360.pl article IDs
    # Remove trailing commas and normalize article paths
    if 'strzelce360.pl' in parsed.netloc.lower() and '/artykul/' in path:
        path = re.sub(r'/artykul/(\d+),.*', r'/artykul/\1', path)
    
    # Remove common tracking parameters
    tracking_params = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'ref', 'source', 'mc_cid', 'mc_eid'
    }
    
    # Parse query parameters and filter out tracking ones
    params = parse_qs(parsed.query)
    filtered_params = {
        k: v for k, v in params.items() 
        if k.lower() not in tracking_params
    }
    
    # Rebuild query string
    new_query = urlencode(filtered_params, doseq=True)
    
    # Rebuild URL without fragment and with filtered query
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),  # Normalize domain to lowercase
        path.rstrip('/'),  # Use normalized path without trailing slash
        parsed.params,
        new_query,
        ''  # Remove fragment
    ))
    
    return normalized

def main():
    # Load projects.json
    projects_file = Path("docs/data/projects.json")
    if not projects_file.exists():
        print("ERROR: projects.json not found")
        return
    
    with open(projects_file, 'r', encoding='utf-8') as f:
        projects = json.load(f)
    
    print(f"Loaded {len(projects)} micro actions")
    
    # Track seen normalized URLs and deduplicate
    seen_normalized = {}
    cleaned_projects = []
    duplicates_removed = []
    
    for item in projects:
        source = item.get('source', '')
        normalized = normalize_url(source) if source else ""
        
        if normalized and normalized in seen_normalized:
            # This is a duplicate
            original = seen_normalized[normalized]
            print(f"\nFound duplicate:")
            print(f"  Original: {original['title'][:50]}...")
            print(f"           Hash: {original['hash'][:8]}...")
            print(f"           Source: {original['source']}")
            print(f"  Duplicate: {item['title'][:50]}...")
            print(f"            Hash: {item['hash'][:8]}...")
            print(f"            Source: {source}")
            duplicates_removed.append(item)
        else:
            # First occurrence of this URL
            if normalized:
                seen_normalized[normalized] = item
            cleaned_projects.append(item)
    
    print(f"\nSummary:")
    print(f"  Original items: {len(projects)}")
    print(f"  After deduplication: {len(cleaned_projects)}")
    print(f"  Duplicates removed: {len(duplicates_removed)}")
    
    if duplicates_removed:
        # Create backup
        backup_file = Path("docs/data/projects_backup_before_dedup.json")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)
        print(f"\nBackup saved to: {backup_file}")
        
        # Save cleaned version
        with open(projects_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_projects, f, ensure_ascii=False, indent=2)
        print(f"Cleaned data saved to: {projects_file}")
        
        # Save removed items for reference
        removed_file = Path("docs/data/removed_duplicates.json")
        with open(removed_file, 'w', encoding='utf-8') as f:
            json.dump(duplicates_removed, f, ensure_ascii=False, indent=2)
        print(f"Removed duplicates saved to: {removed_file}")
    else:
        print("\nNo duplicates found - no changes made")

if __name__ == "__main__":
    main()