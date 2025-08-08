"""
Debug launcher for Flask with Doppler environment variables
"""
import os
import subprocess
import sys

os.environ['DOPPLER_TOKEN'] = 'dp.st.prd.ZSiWlMjSmwiSLkGWu5fwJOYstT9x1EgqVSMy8mIEYA6'

if __name__ == "__main__":
    try:
        result = subprocess.run(
            ['doppler', 'secrets', 'download', '--no-file', '--format', 'env'],
            capture_output=True,
            text=True,
            check=True
        )

        print("Loading Doppler secrets...")
        for line in result.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                os.environ[key] = value
                if 'KEY' not in key and 'SECRET' not in key and 'TOKEN' not in key:
                    print(f"  {key}={value}")
                else:
                    print(f"  {key}=***hidden***")
        
        print(f"Loaded {len(result.stdout.strip().split())} environment variables from Doppler")
        
        from application import app
        app.run(host='0.0.0.0', port=5001, debug=True)
        
    except subprocess.CalledProcessError as e:
        print(f"Error running Doppler: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting Flask app: {e}")
        sys.exit(1)