#!/usr/bin/env python3
"""
Fix corrupted data in projects.json by restoring from backup
and preserving media uploads
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime

def load_json(filepath):
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath):
    """Save JSON file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def calculate_hash(title, description):
    """Calculate SHA1 hash from title and description"""
    content = f"{title}{description}"
    return hashlib.sha1(content.encode()).hexdigest()

def main():
    # Paths
    docs_dir = Path('docs/data')
    current_file = docs_dir / 'projects.json'
    backup_file = docs_dir / 'projects.json.backup'  # Earliest backup from this morning
    
    # Load files
    print("Loading current projects.json...")
    current_data = load_json(current_file)
    print(f"  Found {len(current_data)} items")
    
    print("\nLoading backup from this morning...")
    backup_data = load_json(backup_file)
    print(f"  Found {len(backup_data)} items")
    
    # Create lookup by hash for backup data
    backup_by_hash = {item['hash']: item for item in backup_data}
    
    # Track fixes
    fixed_count = 0
    media_preserved = 0
    
    # Fix corrupted items
    print("\nChecking for corrupted data...")
    for i, item in enumerate(current_data):
        item_hash = item.get('hash')
        
        if item_hash and item_hash in backup_by_hash:
            original = backup_by_hash[item_hash]
            
            # Check if title or description seems wrong
            # (e.g., contains "DATAsculptor" or doesn't match the original)
            needs_fix = False
            
            # Check for obvious corruption patterns
            if item.get('title') != original.get('title'):
                print(f"\n  Item {item_hash[:8]}:")
                print(f"    Current title: {item.get('title', '')[:50]}...")
                print(f"    Original title: {original.get('title', '')[:50]}...")
                needs_fix = True
            
            if item.get('description') != original.get('description'):
                if not needs_fix:
                    print(f"\n  Item {item_hash[:8]}:")
                print(f"    Current desc: {item.get('description', '')[:50]}...")
                print(f"    Original desc: {original.get('description', '')[:50]}...")
                needs_fix = True
            
            if needs_fix:
                # Restore original content but preserve media
                current_media = item.get('media', [])
                current_edited = item.get('lastEdited')
                
                # Restore from backup
                current_data[i] = original.copy()
                
                # Preserve media if it exists
                if current_media:
                    current_data[i]['media'] = current_media
                    media_preserved += 1
                
                # Add restoration timestamp
                current_data[i]['dataRestored'] = datetime.now().isoformat()
                if current_edited:
                    current_data[i]['lastEdited'] = current_edited
                
                fixed_count += 1
                print(f"    ✓ FIXED")
    
    if fixed_count > 0:
        # Backup current corrupted version first
        backup_corrupted = docs_dir / f'projects_corrupted_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        print(f"\nBacking up corrupted data to: {backup_corrupted}")
        save_json(load_json(current_file), backup_corrupted)
        
        # Save fixed data
        print(f"\nSaving fixed data to projects.json...")
        save_json(current_data, current_file)
        
        print(f"\n✅ Fixed {fixed_count} corrupted items")
        print(f"✅ Preserved media for {media_preserved} items")
        print("\nThe corrupted data has been backed up and the original content restored.")
        print("Media uploads have been preserved.")
    else:
        print("\n✅ No corruption detected - all items appear correct")
    
    # Additional check for duplicate content
    print("\nChecking for duplicate content...")
    seen_content = {}
    duplicates = []
    
    for item in current_data:
        content_key = f"{item.get('title', '')}::{item.get('description', '')}"
        if content_key in seen_content:
            duplicates.append({
                'hash1': seen_content[content_key],
                'hash2': item['hash'],
                'title': item.get('title', '')[:50]
            })
        else:
            seen_content[content_key] = item['hash']
    
    if duplicates:
        print(f"\n⚠️  Found {len(duplicates)} items with duplicate content:")
        for dup in duplicates[:5]:  # Show first 5
            print(f"  - {dup['hash1'][:8]} and {dup['hash2'][:8]}: {dup['title']}...")
    else:
        print("✅ No duplicate content found")

if __name__ == '__main__':
    main()