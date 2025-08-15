#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.error

def test_groq_api():
    """Test Groq API connectivity and model availability"""
    
    # Check for API key
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in environment")
        print("Please set it with: export GROQ_API_KEY='your-key-here'")
        return False
    
    print(f"✓ API Key found: {api_key[:10]}...")
    
    # Test with moonshotai/kimi-k2-instruct model
    model = "moonshotai/kimi-k2-instruct"
    print(f"\nTesting model: {model}")
    
    # Prepare request
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    )
    
    # Simple test message
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Respond with JSON."},
            {"role": "user", "content": "Return JSON with a single key 'status' set to 'ok'"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    data = json.dumps(payload).encode("utf-8")
    
    try:
        print(f"Sending request to Groq API...")
        with urllib.request.urlopen(req, data=data, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            
            if "error" in result:
                print(f"✗ API returned error: {result['error']}")
                return False
            
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                print(f"✓ API call successful!")
                print(f"Response: {content}")
                return True
            else:
                print(f"✗ Unexpected response format: {json.dumps(result, indent=2)}")
                return False
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"✗ HTTP Error {e.code}")
        try:
            error_json = json.loads(error_body)
            if "error" in error_json:
                error_msg = error_json["error"]
                if isinstance(error_msg, dict):
                    print(f"Error message: {error_msg.get('message', 'Unknown error')}")
                    print(f"Error type: {error_msg.get('type', 'Unknown type')}")
                else:
                    print(f"Error: {error_msg}")
        except:
            print(f"Raw error: {error_body}")
        return False
        
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def list_available_models():
    """List all available models from Groq API"""
    
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return
    
    print("\nFetching available models...")
    
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            
            if "data" in result:
                models = result["data"]
                print(f"\nAvailable models ({len(models)}):")
                for model in models:
                    model_id = model.get("id", "unknown")
                    owned_by = model.get("owned_by", "unknown")
                    print(f"  - {model_id} (by {owned_by})")
                    
                # Check if kimi model is in list
                kimi_found = any("kimi" in m.get("id", "").lower() for m in models)
                if kimi_found:
                    print("\n✓ moonshotai/kimi-k2-instruct is available")
                else:
                    print("\n✗ moonshotai/kimi-k2-instruct NOT found in available models")
                    print("\nSuggested alternatives:")
                    for model in models:
                        model_id = model.get("id", "")
                        if "llama" in model_id.lower() or "mixtral" in model_id.lower():
                            print(f"  - {model_id}")
                            
    except Exception as e:
        print(f"✗ Failed to list models: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("GROQ API CONNECTIVITY TEST")
    print("=" * 60)
    
    # Test API connectivity
    success = test_groq_api()
    
    # List available models
    list_available_models()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ API test PASSED - connection working")
    else:
        print("✗ API test FAILED - check configuration")
    print("=" * 60)