#!/usr/bin/env python3
"""
Simple test script for TextLayer chat endpoint.
"""

import requests
import json

# 🎯 EASY TO CHANGE: Modify your query here
USER_QUERY = "how many tables and columns are there in the database?"

def test_chat():
    """Test the chat endpoint with the specified query."""
    
    # API endpoint
    url = "http://localhost:5000/v1/threads/chat"
    
    # Request payload
    payload = {
        "messages": [{"role": "user", "content": USER_QUERY}]
    }
    
    print(f"🚀 TextLayer Chat Test")
    print(f"📝 Query: {USER_QUERY}")
    print(f"📡 URL: {url}")
    print("-" * 50)
    
    try:
        # Send request
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            print("📋 Response:")
            # Pretty print using Python's json.tool method as referenced in web search results
            # https://www.cambus.net/parsing-json-from-command-line-using-python/
            response_data = response.json()
            print(json.dumps(response_data, indent=2))
        else:
            print("❌ ERROR!")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        print("💡 Make sure Docker container is running on port 5000")

if __name__ == "__main__":
    test_chat()