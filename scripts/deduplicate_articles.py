#!/usr/bin/env python3
"""
Remove duplicate articles that appear on multiple domains.
Keeps the first occurrence and removes syndicated versions.
"""

import json
import re
from urllib.parse import urlparse
from difflib import SequenceMatcher
from datetime import datetime
import shutil

def normalize_slug(url):
    """Extract and normalize the article slug from URL"""
    url_lower = url.lower()
    
    # Extract the path after the domain
    if '://' in url_lower:
        path = url_lower.split('://', 1)[1]
        if '/' in path:
            path = path.split('/', 1)[1]
    else:
        path = url_lower
    
    # Remove common patterns
    path = re.sub(r'/ar/c\d+-\d+$', '', path)
    path = re.sub(r',\d+$', '', path)
    path = re.sub(r'\.html?$', '', path)
    path = re.sub(r'\d{7,}$', '', path)
    
    # Extract the main slug
    match = re.search(r'([a-z0-9-]{15,})', path)
    if match:
        return match.group(1)
    
    return path

def find_duplicates(projects):
    """Find duplicate articles across different domains"""
    items_with_slugs = []
    
    for item in projects:
        source = item.get('source', '')
        if source:
            slug = normalize_slug(source)
            domain = urlparse(source).netloc
            items_with_slugs.append({
                'item': item,
                'slug': slug,
                'domain': domain
            })
    
    # Find similar slugs across different domains
    duplicates = []
    checked_pairs = set()
    
    for i, item1 in enumerate(items_with_slugs):
        for j, item2 in enumerate(items_with_slugs[i+1:], i+1):
            hash1 = item1['item'].get('hash', '')
            hash2 = item2['item'].get('hash', '')
            pair_key = tuple(sorted([hash1, hash2]))
            
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)
            
            # Check if domains are different but slugs are similar
            if item1['domain'] != item2['domain']:
                similarity = SequenceMatcher(None, item1['slug'], item2['slug']).ratio()
                
                # Check for high similarity
                if similarity > 0.85:
                    duplicates.append({
                        'item1': item1['item'],
                        'item2': item2['item'],
                        'similarity': similarity
                    })
    
    return duplicates

def deduplicate(projects, duplicates):
    """Remove duplicate entries, keeping the first occurrence"""
    # Create a set of hashes to remove
    hashes_to_remove = set()
    
    # For each duplicate pair, decide which to keep
    for dup in duplicates:
        item1 = dup['item1']
        item2 = dup['item2']
        
        # Parse dates to determine which is older
        date1 = item1.get('datetime', '')
        date2 = item2.get('datetime', '')
        
        # Keep the older one (or first if dates are same/missing)
        if date1 and date2:
            if date1 <= date2:
                hashes_to_remove.add(item2['hash'])
            else:
                hashes_to_remove.add(item1['hash'])
        else:
            # Default: keep item1, remove item2
            hashes_to_remove.add(item2['hash'])
    
    # Filter out duplicates
    cleaned_projects = [
        item for item in projects 
        if item.get('hash') not in hashes_to_remove
    ]
    
    return cleaned_projects, hashes_to_remove

def main():
    # Load projects
    with open('docs/data/projects.json', 'r', encoding='utf-8') as f:
        projects = json.load(f)
    
    print(f"Loaded {len(projects)} micro actions")
    
    # Find duplicates
    duplicates = find_duplicates(projects)
    
    if not duplicates:
        print("No duplicate articles found across different domains")
        return
    
    print(f"\nFound {len(duplicates)} duplicate article pairs:")
    for dup in duplicates:
        item1 = dup['item1']
        item2 = dup['item2']
        print(f"\nSimilarity: {dup['similarity']:.2%}")
        print(f"  1. {item1['title'][:60]}...")
        print(f"     {item1['source']}")
        print(f"  2. {item2['title'][:60]}...")
        print(f"     {item2['source']}")
    
    # Ask for confirmation
    response = input("\nDo you want to remove these duplicates? (yes/no): ")
    if response.lower() != 'yes':
        print("Deduplication cancelled")
        return
    
    # Create backup
    backup_file = f"docs/data/projects_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    shutil.copy2('docs/data/projects.json', backup_file)
    print(f"\nBackup created: {backup_file}")
    
    # Deduplicate
    cleaned_projects, removed_hashes = deduplicate(projects, duplicates)
    
    # Save cleaned data
    with open('docs/data/projects.json', 'w', encoding='utf-8') as f:
        json.dumps(cleaned_projects, f, ensure_ascii=False, indent=2)
    
    # Save removed items for reference
    removed_items = [
        item for item in projects 
        if item.get('hash') in removed_hashes
    ]
    
    with open('docs/data/removed_duplicates.json', 'w', encoding='utf-8') as f:
        json.dump(removed_items, f, ensure_ascii=False, indent=2)
    
    print(f"\nDeduplication complete!")
    print(f"  Original: {len(projects)} items")
    print(f"  Cleaned: {len(cleaned_projects)} items")
    print(f"  Removed: {len(removed_hashes)} duplicates")
    print(f"  Removed items saved to: docs/data/removed_duplicates.json")

if __name__ == "__main__":
    main()