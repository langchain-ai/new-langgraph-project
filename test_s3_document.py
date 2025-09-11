#!/usr/bin/env python3
"""Test script for processing document from LocalStack S3.

This script tests the document extraction and HCFA Reader Agent with the provided S3 file:
http://localhost:4566/medical-documents/2_page_with_back.pdf
"""

import asyncio
import json
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set environment variables for LocalStack
os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['S3_BUCKET'] = 'medical-documents'


async def test_document_extraction():
    """Test document extraction tool with LocalStack S3."""
    from common.document_extraction import DocumentExtractor
    
    print("\n" + "="*60)
    print("Testing Document Extraction with LocalStack S3")
    print("="*60 + "\n")
    
    # Configuration
    s3_key = "2_page_with_back.pdf"
    bucket_name = "medical-documents"
    
    print(f"📄 Testing file: s3://{bucket_name}/{s3_key}")
    print(f"🌐 LocalStack endpoint: {os.environ['AWS_ENDPOINT_URL']}\n")
    
    try:
        # Initialize extractor
        extractor = DocumentExtractor(
            bucket_name=bucket_name,
            aws_region="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            endpoint_url="http://localhost:4566"
        )
        
        # Process the document
        print("1️⃣ Processing CMS-1500 document...")
        result = extractor.process_cms1500_document(s3_key)
        
        print(f"✅ Document processed successfully!")
        print(f"   - File size: {result['s3_metadata']['file_size']:,} bytes")
        print(f"   - Downloaded: {result['s3_metadata']['bytes_downloaded']:,} bytes")
        print(f"   - Savings: {result['s3_metadata']['savings_percentage']:.1f}%")
        print(f"   - Pages: {result['pdf_metadata']['page_count']}")
        print(f"   - Is CMS-1500: {result['is_cms1500']}")
        print(f"   - Confidence: {result['confidence']:.2f}")
        
        if result['indicators_found']:
            print(f"\n📋 CMS-1500 Indicators Found ({len(result['indicators_found'])}):")
            for indicator in result['indicators_found'][:5]:
                print(f"   - {indicator}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        logger.error("Error details:", exc_info=True)
        return None


async def test_hcfa_reader_agent():
    """Test HCFA Reader Agent with LocalStack S3."""
    from agents.hcfa_reader import graph as hcfa_reader_graph
    
    print("\n" + "="*60)
    print("Testing HCFA Reader Agent")
    print("="*60 + "\n")
    
    # Configuration
    context = {
        "s3_bucket": "medical-documents",
        "aws_region": "us-east-1",
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "enable_validation": True,
        "max_pages": 2
    }
    
    # Initial state
    initial_state = {
        "s3_key": "2_page_with_back.pdf",
        "s3_bucket": "medical-documents"
    }
    
    try:
        print("2️⃣ Running HCFA Reader Agent...")
        result = await hcfa_reader_graph.ainvoke(
            initial_state,
            config={"configurable": context}
        )
        
        print(f"✅ Agent completed successfully!")
        print(f"   - Document Type: {result.get('document_type')}")
        print(f"   - Is CMS-1500: {result.get('is_cms1500')}")
        print(f"   - Confidence: {result.get('confidence', 0):.2f}")
        print(f"   - Processing Status: {result.get('processing_status')}")
        print(f"   - Pages Processed: {result.get('pages_processed', 0)}")
        
        # Show extracted data summary
        if result.get('patient_info'):
            print(f"\n👤 Patient Information:")
            patient = result['patient_info']
            print(f"   - Name: {patient.get('name', 'N/A')}")
            print(f"   - DOB: {patient.get('dob', 'N/A')}")
            print(f"   - Sex: {patient.get('sex', 'N/A')}")
        
        if result.get('insurance_info'):
            print(f"\n🏥 Insurance Information:")
            insurance = result['insurance_info']
            print(f"   - Insured ID: {insurance.get('insured_id', 'N/A')}")
            print(f"   - Plan Name: {insurance.get('plan_name', 'N/A')}")
        
        if result.get('procedures_info'):
            print(f"\n💊 Procedures: {len(result['procedures_info'])} found")
            for i, proc in enumerate(result['procedures_info'][:3], 1):
                print(f"   {i}. CPT: {proc.get('cpt_code', 'N/A')}, Charge: ${proc.get('charges', 0)}")
        
        if result.get('validation_errors'):
            print(f"\n⚠️  Validation Issues ({len(result['validation_errors'])}):")
            for error in result['validation_errors'][:5]:
                print(f"   - {error}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        logger.error("Error details:", exc_info=True)
        return None


async def test_api_v2_endpoint():
    """Test /api/v2/process endpoint with LocalStack S3."""
    import httpx
    
    print("\n" + "="*60)
    print("Testing API v2 Endpoint")
    print("="*60 + "\n")
    
    # API endpoint
    url = "http://localhost:8000/api/v2/process"
    
    # Request data
    request_data = {
        "s3_key": "2_page_with_back.pdf",
        "bucket": "medical-documents"
    }
    
    try:
        print("3️⃣ Calling /api/v2/process endpoint...")
        print(f"   URL: {url}")
        print(f"   Request: {json.dumps(request_data, indent=2)}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=request_data,
                timeout=30.0
            )
        
        print(f"\n📨 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ API call successful!")
            print(f"   - Status: {data.get('status')}")
            
            # Processing info
            proc_info = data.get('processing_info', {})
            print(f"\n📊 Processing Information:")
            print(f"   - Document Type: {proc_info.get('document_type')}")
            print(f"   - Confidence: {proc_info.get('confidence', 0):.2f}")
            print(f"   - Processing Time: {proc_info.get('processing_time_ms', 0)}ms")
            print(f"   - Pages Processed: {proc_info.get('pages_processed', 0)}")
            
            # File info
            file_info = data.get('file_info', {})
            print(f"\n📁 File Information:")
            print(f"   - S3 URI: {file_info.get('s3_uri')}")
            print(f"   - File Size: {file_info.get('file_size', 0):,} bytes")
            
            # Extracted data
            extracted = data.get('extracted_data', {})
            if extracted.get('patient'):
                print(f"\n👤 Extracted Patient Data:")
                patient = extracted['patient']
                print(f"   - Name: {patient.get('name', 'N/A')}")
                print(f"   - DOB: {patient.get('dob', 'N/A')}")
            
            if extracted.get('procedures'):
                print(f"\n💊 Extracted Procedures: {len(extracted['procedures'])}")
            
            # Optimization stats
            opt_stats = data.get('optimization_stats', {})
            if opt_stats:
                print(f"\n⚡ Optimization Statistics:")
                print(f"   - Bytes Saved: {opt_stats.get('bytes_saved', 0):,}")
                print(f"   - Savings: {opt_stats.get('savings_percentage', 0):.1f}%")
            
            return data
        else:
            print(f"❌ API returned error: {response.text}")
            return None
            
    except httpx.ConnectError:
        print("❌ Could not connect to API server")
        print("   Please ensure the API is running:")
        print("   - In Docker: docker-compose up ai-agents-api")
        print("   - Locally: python api/main.py")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


async def main():
    """Run all tests."""
    
    print("\n" + "🚀 " + "="*58 + " 🚀")
    print("  LocalStack S3 Document Processing Test Suite")
    print("  Testing: 2_page_with_back.pdf")
    print("🚀 " + "="*58 + " 🚀\n")
    
    # Check LocalStack connectivity first
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        print("🔍 Checking LocalStack connectivity...")
        s3_client = boto3.client(
            's3',
            endpoint_url='http://localhost:4566',
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1'
        )
        
        # List buckets
        buckets = s3_client.list_buckets()
        print(f"✅ LocalStack is running. Buckets: {[b['Name'] for b in buckets['Buckets']]}")
        
        # Check if our file exists
        try:
            s3_client.head_object(Bucket='medical-documents', Key='2_page_with_back.pdf')
            print(f"✅ Test file exists in S3\n")
        except ClientError:
            print(f"❌ Test file not found in S3")
            print(f"   Please upload it to LocalStack:")
            print(f"   aws --endpoint-url=http://localhost:4566 s3 cp 2_page_with_back.pdf s3://medical-documents/")
            return
            
    except Exception as e:
        print(f"❌ LocalStack not accessible: {str(e)}")
        print(f"   Please start LocalStack:")
        print(f"   docker-compose up localstack")
        return
    
    # Run tests
    results = {}
    
    # Test 1: Document Extraction
    extraction_result = await test_document_extraction()
    results['extraction'] = extraction_result is not None
    
    # Test 2: HCFA Reader Agent
    agent_result = await test_hcfa_reader_agent()
    results['agent'] = agent_result is not None
    
    # Test 3: API v2 Endpoint
    api_result = await test_api_v2_endpoint()
    results['api'] = api_result is not None
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    print(f"Document Extraction: {'✅ PASSED' if results['extraction'] else '❌ FAILED'}")
    print(f"HCFA Reader Agent:   {'✅ PASSED' if results['agent'] else '❌ FAILED'}")
    print(f"API v2 Endpoint:     {'✅ PASSED' if results['api'] else '❌ FAILED'}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed successfully!")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)