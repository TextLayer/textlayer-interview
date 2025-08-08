#!/usr/bin/env python3
"""
Test the text_to_sql functionality directly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm.tools.text_to_sql import text_to_sql

def test_text_to_sql():
    try:
        print("🧪 Testing text_to_sql with a simple query...")
        
        # Test with a simple query about gross margin trends
        query = "Show me trends in gross margin"
        
        result = text_to_sql(query)
        
        print("✅ text_to_sql executed successfully")
        print("Result:")
        print(result)
        
    except Exception as e:
        print(f"❌ Error in text_to_sql: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Set environment variables for testing
    os.environ['DOPPLER_TOKEN'] = 'dp.st.prd.ZSiWlMjSmwiSLkGWu5fwJOYstT9x1EgqVSMy8mIEYA6'
    
    # Load Doppler secrets
    import subprocess
    try:
        result = subprocess.run(
            ['doppler', 'secrets', 'download', '--no-file', '--format', 'env'],
            capture_output=True,
            text=True,
            check=True
        )
        
        for line in result.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                os.environ[key] = value
    except:
        print("⚠️ Warning: Could not load Doppler secrets, using existing environment")
    
    test_text_to_sql()
