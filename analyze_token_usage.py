#!/usr/bin/env python3
"""
Analyze Claude Code token usage: comparing actual API tokens vs statusline calculations
"""
import json
import os
from pathlib import Path

def analyze_transcript(transcript_path):
    """Analyze a Claude Code transcript for token usage."""
    if not os.path.exists(transcript_path):
        print(f"Transcript not found: {transcript_path}")
        return
    
    print(f"\n{'='*80}")
    print(f"ANALYZING: {Path(transcript_path).name}")
    print(f"{'='*80}")
    
    # Method 1: StatusLine calculation (file size based)
    file_size = os.path.getsize(transcript_path)
    estimated_tokens = file_size // 4  # StatusLine uses /4
    
    with open(transcript_path, 'r') as f:
        lines = f.readlines()
        message_count = sum(1 for line in lines if '"role"' in line)
        # StatusLine adds 50 tokens per message
        estimated_tokens += message_count * 50
    
    print(f"\n📊 STATUSLINE METHOD (file size based):")
    print(f"   File size: {file_size:,} bytes")
    print(f"   Messages: {message_count}")
    print(f"   Estimated tokens: {estimated_tokens:,}")
    
    # Method 2: Actual API token counts
    total_input = 0
    total_cache_read = 0
    total_output = 0
    total_cache_creation = 0
    
    with open(transcript_path, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                if 'message' in entry and 'usage' in entry['message']:
                    usage = entry['message']['usage']
                    total_input += usage.get('input_tokens', 0)
                    total_cache_read += usage.get('cache_read_input_tokens', 0)
                    total_output += usage.get('output_tokens', 0)
                    total_cache_creation += usage.get('cache_creation_input_tokens', 0)
            except:
                pass
    
    actual_total = total_input + total_cache_read + total_output + total_cache_creation
    
    print(f"\n✅ ACTUAL API TOKEN COUNTS:")
    print(f"   Input tokens: {total_input:,}")
    print(f"   Cache read tokens: {total_cache_read:,}")
    print(f"   Cache creation tokens: {total_cache_creation:,}")
    print(f"   Output tokens: {total_output:,}")
    print(f"   TOTAL: {actual_total:,}")
    
    # Calculate percentage for different context limits
    models = {
        "Opus 4.1 (200k)": 200000,
        "Sonnet 4 (500k)": 500000,
        "Sonnet 3.5 (200k)": 200000
    }
    
    print(f"\n📈 CONTEXT USAGE COMPARISON:")
    for model, limit in models.items():
        statusline_pct = min(100, (estimated_tokens * 100) / limit)
        actual_pct = min(100, (actual_total * 100) / limit)
        diff = statusline_pct - actual_pct
        
        print(f"\n   {model}:")
        print(f"   StatusLine shows: {statusline_pct:.1f}% ({estimated_tokens:,}/{limit:,})")
        print(f"   Actual usage:     {actual_pct:.1f}% ({actual_total:,}/{limit:,})")
        print(f"   DISCREPANCY:      {diff:+.1f}% {'⚠️ OVERESTIMATED' if diff > 0 else '✅'}")
    
    # Show what happens after /compact
    print(f"\n⚠️  CRITICAL ISSUE AFTER /compact:")
    print(f"   - /compact resets the conversation but keeps the same transcript file")
    print(f"   - StatusLine still counts ALL bytes in the file (including pre-compact)")
    print(f"   - Actual API context is reset to near zero")
    print(f"   - Result: StatusLine shows high usage when actual is low!")
    
    return estimated_tokens, actual_total

# Analyze current session
current_session = "/Users/decom/.claude/projects/-Users-decom-leschnitz-micro-actions/d7cb4518-a94b-43b6-bc62-ecbc88fc7b9f.jsonl"
if os.path.exists(current_session):
    analyze_transcript(current_session)

# Show all sessions for this project
print(f"\n{'='*80}")
print("ALL SESSIONS IN THIS PROJECT:")
print(f"{'='*80}")

project_dir = Path("/Users/decom/.claude/projects/-Users-decom-leschnitz-micro-actions/")
if project_dir.exists():
    for transcript in sorted(project_dir.glob("*.jsonl")):
        size = transcript.stat().st_size
        print(f"   {transcript.name}: {size:,} bytes")