"""
Test script to verify the enhanced API works with the actual database structure.
"""
import requests
import json

def test_regular_endpoint():
    """Test the enhanced regular chat API endpoint."""
    
    # API endpoint
    url = "http://localhost:5000/v1/threads/chat"
    
    # Test queries that should work with the actual database structure
    test_queries = [
        "What tables are available in the database?",
        "Show me data from the account table",
        "What information is in the customer table?", 
        "Display sample data from the other table",
        "How many records are in each table?"
    ]
    
    print("Testing Enhanced Text-to-SQL API")
    print("=" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: {query}")
        print("-" * 30)
        
        # Prepare request
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ]
        }
        
        try:
            # Make API request
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract the assistant's response
                if 'payload' in result:
                    for message in result['payload']:
                        if message.get('role') == 'assistant':
                            content = message.get('content')
                            if content:
                                print(f"Response: {content[:200]}...")
                            break
                        elif message.get('role') == 'tool':
                            content = message.get('content', '')
                            if content and content != 'null':
                                # Parse the tool response
                                try:
                                    tool_content = json.loads(content)
                                    print(f"Tool Response: {str(tool_content)[:200]}...")
                                except:
                                    print(f"Tool Response: {content[:200]}...")
                            break
                else:
                    print(f"Unexpected response format: {result}")
            else:
                print(f"Error: HTTP {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except Exception as e:
            print(f"Error: {e}")
    
    print(f"\nRegular API testing completed!")


def test_streaming_endpoint():
    """Test the enhanced streaming chat API endpoint."""
    
    # Streaming API endpoint
    url = "http://localhost:5000/v1/threads/chat/stream"
    
    # Simple test query for streaming
    test_query = "Show me data from the account table"
    
    print("\nTesting Enhanced Streaming Text-to-SQL API")
    print("=" * 50)
    print(f"\nStreaming Test: {test_query}")
    print("-" * 30)
    
    # Prepare request
    payload = {
        "messages": [
            {
                "role": "user",
                "content": test_query
            }
        ]
    }
    
    try:
        # Make streaming API request
        response = requests.post(url, json=payload, stream=True, timeout=30)
        
        if response.status_code == 200:
            print("Streaming response:")
            
            # Read the streaming response
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith('data: '):
                    data_part = line[6:]  # Remove 'data: ' prefix
                    try:
                        chunk_data = json.loads(data_part)
                        if 'content' in chunk_data:
                            print(chunk_data['content'], end='', flush=True)
                        if chunk_data.get('finish_reason') == 'stop':
                            print("\n[Stream completed]")
                            break
                        elif chunk_data.get('finish_reason') == 'error':
                            print(f"\n[Stream error: {chunk_data.get('content')}]")
                            break
                    except json.JSONDecodeError:
                        print(f"[Non-JSON data: {data_part}]")
        else:
            print(f"Error: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"Error: {e}")
    
    print(f"\nStreaming API testing completed!")


if __name__ == "__main__":
    print("Testing Both Enhanced Text-to-SQL API Endpoints")
    print("=" * 60)
    
    # Test regular endpoint
    test_regular_endpoint()
    
    # Test streaming endpoint
    test_streaming_endpoint()
