#!/usr/bin/env python3
"""
Helper script to base64 encode the system prompt for GitHub Secrets
"""
import base64
import sys
from pathlib import Path

def encode_prompt():
    prompt_file = Path(__file__).parent.parent / "secrets" / "SYSTEM_PROMPT.local.txt"
    
    if not prompt_file.exists():
        print(f"Error: {prompt_file} not found")
        sys.exit(1)
    
    # Read the prompt
    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt = f.read()
    
    # Base64 encode it
    encoded = base64.b64encode(prompt.encode('utf-8')).decode('ascii')
    
    print("Your base64 encoded prompt (copy this entire string to GitHub Secrets):")
    print("=" * 80)
    print(encoded)
    print("=" * 80)
    print(f"\nOriginal prompt length: {len(prompt)} characters")
    print(f"Encoded length: {len(encoded)} characters")

if __name__ == "__main__":
    encode_prompt()