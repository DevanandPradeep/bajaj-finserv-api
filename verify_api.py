import requests
import json
import time
import subprocess
import sys

def start_server():
    print("Starting server...")
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", "8000"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)  # Wait for server to start
    return process

def test_api():
    url = "http://localhost:8000/extract"
    payload = {
        "document": "Sample Document 1.pdf"
    }
    
    # Since we can't easily provide a real URL that works without internet or specific setup, 
    # we might expect an error from the download part, but we want to check if the API is reachable and tries to process.
    # However, the user provided a test file `test_with_data.py`. Let's see if we can use that logic or data.
    
    # Actually, let's just check if the endpoint exists and accepts the payload.
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    server_process = start_server()
    try:
        test_api()
    finally:
        server_process.terminate()
        print("Server stopped.")
