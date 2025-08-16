#!/usr/bin/env python3
import os
import json
import requests

def test_groq_api():
    """Test Groq API with a simple classification request"""
    
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        print("ERROR: GROQ_API_KEY not set")
        return False
    
    print("Using configured API key")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Leschnitz-MicroActions/1.0"
    }
    
    # Test 1: Simple test
    print("\nTest 1: Simple API connectivity test")
    payload = {
        "model": "moonshotai/kimi-k2-instruct",
        "messages": [
            {"role": "system", "content": "Reply with JSON containing 'status': 'ok'"},
            {"role": "user", "content": "Test"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Test 1 passed")
        else:
            print(f"✗ Test 1 failed: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Test 1 failed with exception: {e}")
        return False
    
    # Test 2: Classification-style request
    print("\nTest 2: Classification request (similar to pipeline)")
    payload = {
        "model": "moonshotai/kimi-k2-instruct",
        "messages": [
            {"role": "system", "content": "You are a relevance filter. Respond ONLY with compact JSON."},
            {"role": "user", "content": """Decide if this is relevant to Leschnitz.
Return JSON with keys: "relevant": boolean, "why": string.
Title: Test article about Leschnitz
Content: This is a test about Leschnitz."""}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"Response content: {content}")
            print("✓ Test 2 passed")
        else:
            print(f"✗ Test 2 failed: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Test 2 failed with exception: {e}")
        return False
    
    # Test 3: Generation-style request
    print("\nTest 3: Generation request (similar to pipeline)")
    payload = {
        "model": "moonshotai/kimi-k2-instruct",
        "messages": [
            {"role": "system", "content": """You write micro artistic actions.
Output compact JSON with keys "title","datetime","description"."""},
            {"role": "user", "content": """Make ONE micro action.
Source title: Test News from Leschnitz
Published: 2025-08-15
Return JSON only."""}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"Response content: {content}")
            print("✓ Test 3 passed")
            
            # Check token usage
            usage = result.get("usage", {})
            print(f"\nToken usage: {usage}")
        else:
            print(f"✗ Test 3 failed: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Test 3 failed with exception: {e}")
        return False
    
    print("\n✅ All tests passed!")
    return True

if __name__ == "__main__":
    test_groq_api()