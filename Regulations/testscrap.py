import requests
import json

# Your API key (replace with actual key)
JIGSAW_API_KEY = "pk_a0241a8825608a1a76b43a743c29965cc368fcde8f05110d86c7850592d984e2417c0f3e3a03cbc82eeb48006d839d13de63a533aa74995131f3b25c7df422ae0248pkD2cQMEn49ogWber"

def test_jigsaw_scraper():
    """
    Test Jigsaw Stack API with one URL
    """
    
    # Test URL - FINMA homepage
    test_url = "https://www.finma.ch/en/documentation/circulars/"
    
    # Jigsaw Stack API endpoint
    api_url = "https://api.jigsawstack.com/v1/ai/scrape"
    
    # Request payload
    payload = {
        "url": test_url,
        "element_prompts": ["Extract all regulation titles and links"]
    }
    
    # Headers with API key
    headers = {
        "x-api-key": JIGSAW_API_KEY,
        "Content-Type": "application/json"
    }
    
    print(f"Testing Jigsaw Stack API...")
    print(f"Target URL: {test_url}")
    print(f"-" * 60)
    
    try:
        # Make request
        response = requests.post(api_url, json=payload, headers=headers)
        
        # Check response
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS! API is working.")
            print(f"\nExtracted content (first 500 chars):")
            print(f"{str(data)[:500]}...")
            
            # Save to file
            with open("test_scrape_result2.json", "w") as f:
                json.dump(data, f, indent=2)
            print(f"\n✅ Full result saved to: test_scrape_result2.json")
            
            return data
        else:
            print(f"❌ ERROR: Status code {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None

if __name__ == "__main__":
    test_jigsaw_scraper()