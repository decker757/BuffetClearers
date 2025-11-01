import PyPDF2
import requests
from io import BytesIO

def test_pdf_extraction():
    """
    Test PDF extraction with a sample PDF
    """
    # Test with a sample PDF from the web (if available)
    # This is just to test if PyPDF2 is working
    print("Testing PyPDF2 installation...")
    
    try:
        # Try to download a simple PDF (this is just a test)
        test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        
        print(f"📄 Testing with: {test_url}")
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            print(f"✅ PDF has {len(pdf_reader.pages)} pages")
            
            # Extract text from first page
            if len(pdf_reader.pages) > 0:
                first_page = pdf_reader.pages[0]
                text = first_page.extract_text()
                print(f"✅ Extracted {len(text)} characters from first page")
                print(f"Sample text: {text[:100]}...")
            
            print("🎉 PyPDF2 is working correctly!")
            
        else:
            print(f"❌ Could not download test PDF (status: {response.status_code})")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        print("But PyPDF2 import worked fine!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_pdf_extraction()