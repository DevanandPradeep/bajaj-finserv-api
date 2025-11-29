import requests
import json

def test_updated_api():
    """Test the updated /extract-bill-data endpoint"""
    url = "http://localhost:8000/extract-bill-data"
    
    # Test with local sample document
    payload = {
        "document": "Sample Document 1.pdf"
    }
    
    print("Testing /extract-bill-data endpoint...")
    print(f"Request: {json.dumps(payload, indent=2)}\n")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"\nResponse:")
        print(json.dumps(response.json(), indent=2))
        
        # Validate response structure
        data = response.json()
        assert "is_success" in data, "Missing 'is_success' field"
        assert "token_usage" in data, "Missing 'token_usage' field"
        assert "data" in data, "Missing 'data' field"
        
        if data["is_success"]:
            assert "pagewise_line_items" in data["data"], "Missing 'pagewise_line_items'"
            assert "total_item_count" in data["data"], "Missing 'total_item_count'"
            
            # Check page_type field
            for page in data["data"]["pagewise_line_items"]:
                assert "page_type" in page, "Missing 'page_type' field in page"
        
        print("\n✅ All validations passed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the API.")
        print("Make sure the server is running: python -m uvicorn app:app")
    except AssertionError as e:
        print(f"❌ Validation failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_updated_api()
