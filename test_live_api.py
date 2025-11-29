import requests
import json
import sys

def test_live_api(api_url, document_url):
    """Test the live deployed API"""
    
    # Ensure URL ends with /extract-bill-data
    if not api_url.endswith("/extract-bill-data"):
        api_url = api_url.rstrip("/") + "/extract-bill-data"
    
    print(f"🚀 Testing API at: {api_url}")
    
    payload = {
        "document": document_url
    }
    
    print(f"📄 Document URL: {document_url}")
    print("⏳ Sending request... (this might take a few seconds)")
    
    try:
        response = requests.post(api_url, json=payload, timeout=60)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Success! Response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print("❌ Request failed:")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")

if __name__ == "__main__":
    # Default URL - REPLACE THIS with your actual Render URL if not provided as argument
    # Example: https://bajaj-extraction-api.onrender.com
    default_api_url = "https://bajaj-extraction-api.onrender.com"
    default_doc_url = "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png"
    
    api_url = default_api_url
    doc_url = default_doc_url
    
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    
    if len(sys.argv) > 2:
        doc_url = sys.argv[2]
        
    print(f"Using API URL: {api_url}")
    print(f"Using Document URL: {doc_url}")
        
    test_live_api(api_url, doc_url)
