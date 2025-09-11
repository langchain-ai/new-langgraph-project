"""Test script for document extraction tool."""

import os
import logging
from common.document_extraction import DocumentExtractor, extract_cms1500_from_s3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_document_extractor():
    """Test the DocumentExtractor class."""
    
    print("\n" + "="*60)
    print("Testing Document Extraction Tool")
    print("="*60 + "\n")
    
    # Configuration
    bucket_name = os.getenv("S3_BUCKET", "medical-documents")
    aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    s3_key = "test-files/cms1500-sample.pdf"  # Update with your test file
    
    # Optional: Set AWS credentials if needed
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")  # For LocalStack or MinIO
    
    try:
        # Initialize extractor
        print(f"Initializing DocumentExtractor...")
        print(f"  Bucket: {bucket_name}")
        print(f"  Region: {aws_region}")
        print(f"  S3 Key: {s3_key}\n")
        
        extractor = DocumentExtractor(
            bucket_name=bucket_name,
            aws_region=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            endpoint_url=endpoint_url
        )
        
        # Test 1: Get PDF from S3 with size limit
        print("Test 1: Loading PDF from S3 (max 1MB)...")
        pdf_content, metadata = extractor.get_pdf_from_s3(s3_key, max_bytes=1024*1024)
        
        print(f"✅ PDF loaded successfully")
        print(f"  File size: {metadata['file_size']:,} bytes")
        print(f"  Downloaded: {metadata['bytes_downloaded']:,} bytes")
        print(f"  Saved: {metadata['bytes_saved']:,} bytes ({metadata['savings_percentage']:.1f}%)")
        print(f"  Content type: {metadata['content_type']}\n")
        
        # Test 2: Extract PDF metadata
        print("Test 2: Extracting PDF metadata...")
        pdf_meta = extractor.get_pdf_metadata(pdf_content)
        
        print(f"✅ Metadata extracted")
        print(f"  Pages: {pdf_meta['page_count']}")
        print(f"  Title: {pdf_meta['title'] or 'N/A'}")
        print(f"  Creator: {pdf_meta['creator'] or 'N/A'}")
        if 'page_width' in pdf_meta:
            print(f"  Page size: {pdf_meta['page_width']:.1f} x {pdf_meta['page_height']:.1f}\n")
        else:
            print()
        
        # Test 3: Split PDF pages
        print("Test 3: Splitting PDF pages...")
        page_pdfs = extractor.split_pdf_pages(pdf_content, max_pages=2)
        
        print(f"✅ PDF split into {len(page_pdfs)} pages")
        for i, page_pdf in enumerate(page_pdfs):
            print(f"  Page {i+1}: {len(page_pdf):,} bytes")
        print()
        
        # Test 4: Extract text
        print("Test 4: Extracting text from PDF...")
        text_content = extractor.extract_text_from_pdf(pdf_content, max_pages=1)
        
        print(f"✅ Text extracted ({len(text_content)} characters)")
        print(f"  First 200 chars: {text_content[:200].replace(chr(10), ' ')}...\n")
        
        # Test 5: Process as CMS-1500
        print("Test 5: Processing as CMS-1500 document...")
        result = extractor.process_cms1500_document(s3_key)
        
        print(f"✅ Document processed")
        print(f"  Is CMS-1500: {result['is_cms1500']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Indicators found: {len(result['indicators_found'])}")
        if result['indicators_found']:
            print(f"  Sample indicators:")
            for indicator in result['indicators_found'][:5]:
                print(f"    - {indicator}")
        print()
        
        # Test 6: Quick extraction function
        print("Test 6: Testing quick extraction function...")
        quick_result = extract_cms1500_from_s3(
            s3_key=s3_key,
            bucket_name=bucket_name,
            aws_region=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            endpoint_url=endpoint_url
        )
        
        print(f"✅ Quick extraction completed")
        print(f"  Pages processed: {quick_result['page_count']}")
        print(f"  CMS-1500 detected: {quick_result['is_cms1500']}")
        
        print("\n" + "="*60)
        print("🎉 All tests passed successfully!")
        print("="*60)
        
        return True
        
    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        print("Please make sure the test file exists in S3")
        return False
        
    except PermissionError as e:
        print(f"\n❌ Permission denied: {e}")
        print("Please check your AWS credentials and S3 bucket permissions")
        return False
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error("Error details:", exc_info=True)
        return False


def test_mock_mode():
    """Test with mock data when S3 is not available."""
    
    print("\n" + "="*60)
    print("Testing in Mock Mode (No S3)")
    print("="*60 + "\n")
    
    try:
        # Create mock PDF content
        import fitz  # PyMuPDF
        
        # Create a simple PDF with CMS-1500 text
        pdf_document = fitz.open()
        page = pdf_document.new_page()
        
        # Add CMS-1500 indicators
        text = """CMS-1500 (08-05)
        HEALTH INSURANCE CLAIM FORM
        1a. INSURED'S I.D. NUMBER: 123456789
        2. PATIENT'S NAME: JOHN DOE
        3. PATIENT'S BIRTH DATE: 01/15/1970
        21. DIAGNOSIS OR NATURE OF ILLNESS: E11.9
        24A. CPT/HCPCS: 99213
        33. BILLING PROVIDER INFO & PH: Springfield Medical"""
        
        page.insert_text((50, 50), text)
        pdf_content = pdf_document.tobytes()
        pdf_document.close()
        
        print("Created mock PDF with CMS-1500 content")
        
        # Test with mock extractor (no S3)
        extractor = DocumentExtractor(
            bucket_name="mock-bucket",
            aws_region="us-east-1"
        )
        
        # Test PDF operations
        print("\nTesting PDF operations with mock data...")
        
        # Extract metadata
        metadata = extractor.get_pdf_metadata(pdf_content)
        print(f"✅ Metadata: {metadata['page_count']} pages")
        
        # Split pages
        pages = extractor.split_pdf_pages(pdf_content)
        print(f"✅ Split into {len(pages)} pages")
        
        # Extract text
        text_extracted = extractor.extract_text_from_pdf(pdf_content)
        print(f"✅ Extracted {len(text_extracted)} characters")
        
        # Detect CMS-1500
        indicators = extractor._detect_cms1500_indicators(text_extracted)
        print(f"✅ CMS-1500 detected: {indicators['is_cms1500']} (confidence: {indicators['confidence']:.2f})")
        
        print("\n🎉 Mock tests completed successfully!")
        return True
        
    except ImportError:
        print("❌ PyMuPDF (fitz) not installed. Run: pip install PyMuPDF")
        return False
    except Exception as e:
        print(f"❌ Mock test failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    # Check for mock mode flag
    if "--mock" in sys.argv:
        success = test_mock_mode()
    else:
        # Try real S3 test
        success = test_document_extractor()
        
        if not success:
            print("\n💡 Tip: You can run in mock mode without S3:")
            print("   python test_document_extraction.py --mock")
    
    sys.exit(0 if success else 1)