#!/usr/bin/env python3
"""Test API connection directly"""

import sys
import requests

def test_api(api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    payload = {
        "model": "moonshotai/kimi-k2-instruct",
        "messages": [
            {"role": "system", "content": "Reply with JSON: {\"status\": \"ok\"}"},
            {"role": "user", "content": "Test"}
        ],
        "temperature": 0.7,
        "max_tokens": 50
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_api.py API_KEY")
        sys.exit(1)
    
    result = test_api(sys.argv[1])
    if result:
        print("Success!")
        print(result.get("choices", [{}])[0].get("message", {}).get("content", ""))