import requests
import json
import PyPDF2
from io import BytesIO

def get_finma_circular_pdfs():
    """
    Extract PDF links from FINMA circulars page
    """
    JIGSAW_API_KEY = "pk_a0241a8825608a1a76b43a743c29965cc368fcde8f05110d86c7850592d984e2417c0f3e3a03cbc82eeb48006d839d13de63a533aa74995131f3b25c7df422ae0248pkD2cQMEn49ogWber"
    
    # Target the circulars page
    url = "https://www.finma.ch/en/documentation/circulars/"
    
    payload = {
        "url": url,
        "element_prompts": ["Extract all PDF links and titles"]
    }
    
    headers = {
        "x-api-key": JIGSAW_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        print("🔍 Calling JigsawStack API...")
        response = requests.post(
            "https://api.jigsawstack.com/v1/ai/scrape",
            json=payload,
            headers=headers,
            timeout=60  # Add timeout
        )
        
        print(f"✅ API response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except requests.exceptions.Timeout:
        print("❌ API request timed out")
        return []
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return []
    
    data = response.json()
    print(f"📊 API returned data keys: {list(data.keys())}")
    
    # Extract PDF URLs - Based on the previous successful output, PDFs are in 'links' array
    pdf_links = []
    
    # Check the 'links' array for PDF URLs
    if 'links' in data:
        print(f"🔍 Processing {len(data['links'])} links...")
        for link in data.get('links', []):
            href = link.get('href', '')
            if href.endswith('.pdf'):
                # Convert relative URLs to absolute URLs
                pdf_url = href
                if pdf_url.startswith('/'):
                    pdf_url = "https://www.finma.ch" + pdf_url
                elif not pdf_url.startswith('http'):
                    pdf_url = "https://www.finma.ch/" + pdf_url.lstrip('/')
                
                pdf_links.append({
                    'title': link.get('text', 'Unknown PDF'),
                    'url': pdf_url
                })
        
        print(f"🔍 Found {len(pdf_links)} PDF links in links array")
    
    # Also check structured data if available
    if 'data' in data and len(data['data']) > 0:
        for i, data_item in enumerate(data['data']):
            if 'results' in data_item and len(data_item['results']) > 0:
                print(f"🔍 Processing data item {i} with {len(data_item['results'])} results")
                
                # Show sample results to understand structure
                if i == 1:  # Look at the second data item which seems to have document teasers
                    for j, result in enumerate(data_item['results'][:3]):  # Show first 3
                        print(f"  📋 Sample result {j}: {result}")
                
                for result in data_item['results']:
                    # Look for PDF links in the href attribute
                    if 'attributes' in result:
                        href_value = None
                        for attr in result['attributes']:
                            if attr['name'] == 'href':
                                href_value = attr['value']
                                break
                        
                        if href_value and ('.pdf' in href_value):
                            pdf_url = href_value
                            if pdf_url.startswith('/'):
                                pdf_url = "https://www.finma.ch" + pdf_url
                            elif not pdf_url.startswith('http'):
                                pdf_url = "https://www.finma.ch/" + pdf_url.lstrip('/')
                            
                            # Avoid duplicates
                            existing_urls = [p['url'] for p in pdf_links]
                            if pdf_url not in existing_urls:
                                pdf_links.append({
                                    'title': result.get('text', 'Unknown PDF'),
                                    'url': pdf_url
                                })
                                print(f"  ✅ Found PDF: {result.get('text', 'Unknown')[:50]}...")
    
    print(f"✅ Found {len(pdf_links)} total PDF links")
    return pdf_links

def extract_text_from_pdf_url(pdf_url):
    """
    Download PDF and extract text
    """
    print(f"📄 Downloading: {pdf_url}")
    
    try:
        # Download PDF with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(pdf_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Failed to download PDF: HTTP {response.status_code}")
            return ""
            
        pdf_file = BytesIO(response.content)
        
        # Extract text
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        
        print(f"✅ Extracted {len(text)} characters")
        return text
        
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
        return ""

# Usage
print("🚀 Starting FINMA PDF scraper...")

pdf_links = get_finma_circular_pdfs()

if not pdf_links:
    print("❌ No PDFs found. Check your API key and connection.")
else:
    print(f"📋 Found {len(pdf_links)} PDFs:")
    for i, pdf in enumerate(pdf_links[:3], 1):  # First 3 PDFs
        print(f"{i}. {pdf['title'][:50]}...")
        
    for pdf in pdf_links[:3]:  # First 3 PDFs
        try:
            text = extract_text_from_pdf_url(pdf['url'])
            print(f"\nTitle: {pdf['title']}")
            print(f"Content preview: {text[:200]}...")
        except Exception as e:
            print(f"❌ Error processing {pdf['title']}: {e}")