import requests
import json
import PyPDF2
from io import BytesIO

def get_finma_circular_pdfs_direct():
    """
    Direct approach to find PDFs on FINMA page (without JigsawStack API)
    """
    print("🔍 Searching for FINMA PDFs directly...")
    
    url = "https://www.finma.ch/en/documentation/circulars/"
    
    try:
        response = requests.get(url, timeout=10)
        html_content = response.text
        
        # Simple regex to find PDF links
        import re
        pdf_pattern = r'href="([^"]*\.pdf)"[^>]*>([^<]*)'
        matches = re.findall(pdf_pattern, html_content, re.IGNORECASE)
        
        pdf_links = []
        for match in matches:
            pdf_url = match[0]
            title = match[1].strip() or "Unknown PDF"
            
            # Convert relative URLs to absolute
            if pdf_url.startswith('/'):
                pdf_url = "https://www.finma.ch" + pdf_url
            elif not pdf_url.startswith('http'):
                pdf_url = "https://www.finma.ch/en/documentation/circulars/" + pdf_url
                
            pdf_links.append({
                'title': title,
                'url': pdf_url
            })
        
        print(f"✅ Found {len(pdf_links)} PDF links")
        return pdf_links
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing FINMA website: {e}")
        return []

def extract_text_from_pdf_url(pdf_url):
    """
    Download PDF and extract text
    """
    print(f"📄 Downloading: {pdf_url}")
    
    try:
        # Download PDF with headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(pdf_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            pdf_file = BytesIO(response.content)
            
            # Extract text
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
            
            print(f"✅ Extracted {len(text)} characters")
            return text
        else:
            print(f"❌ Failed to download PDF (status: {response.status_code})")
            return ""
            
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
        return ""

def main():
    """
    Main function to test the PDF scraping
    """
    print("🚀 Starting FINMA PDF extraction test...")
    
    # Get PDF links
    pdf_links = get_finma_circular_pdfs_direct()
    
    if not pdf_links:
        print("❌ No PDFs found or couldn't access the website")
        return
    
    # Show found PDFs
    print(f"\n📋 Found PDFs:")
    for i, pdf in enumerate(pdf_links[:5], 1):  # Show first 5
        print(f"{i}. {pdf['title']}")
        print(f"   URL: {pdf['url']}")
    
    # Try to extract from first PDF
    if pdf_links:
        print(f"\n🔧 Testing extraction from first PDF...")
        first_pdf = pdf_links[0]
        text = extract_text_from_pdf_url(first_pdf['url'])
        
        if text:
            print(f"\n📄 Title: {first_pdf['title']}")
            print(f"📝 Content preview: {text[:300]}...")
        else:
            print("❌ Could not extract text from PDF")

if __name__ == "__main__":
    main()