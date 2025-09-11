#!/usr/bin/env python3
"""Test script for HCFA Reader Agent V2 with PyMuPDF + Textract."""

import asyncio
import os
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set environment for LocalStack
os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


async def test_hcfa_reader_v2():
    """Test the new HCFA Reader Agent V2."""
    from agents.hcfa_reader import graph as hcfa_reader_graph
    
    print("\n" + "="*60)
    print("Testing HCFA Reader Agent V2")
    print("Flow: PyMuPDF preprocessing -> Textract OCR -> Data extraction")
    print("="*60 + "\n")
    
    # Test files
    test_files = [
        "cms1500_test.pdf",  # Simple test file
        "misaligned.pdf"      # Scanned PDF
    ]
    
    for s3_key in test_files:
        print(f"\n📄 Testing: {s3_key}")
        print("-" * 40)
        
        # Context for the agent
        context = {
            "s3_bucket": "medical-documents",
            "aws_region": "us-east-1",
            "enable_validation": True,
            "max_pages": 2
        }
        
        # Initial state
        initial_state = {
            "s3_key": s3_key,
            "s3_bucket": "medical-documents"
        }
        
        try:
            # Execute the graph
            result = await hcfa_reader_graph.ainvoke(
                initial_state,
                config={"configurable": context}
            )
            
            # Display results
            print(f"✅ Processing completed")
            print(f"   Document Type: {result.get('document_type', 'unknown')}")
            print(f"   Is CMS-1500: {result.get('is_cms1500', False)}")
            print(f"   Confidence: {result.get('confidence', 0):.2f}")
            print(f"   Status: {result.get('processing_status', 'unknown')}")
            print(f"   Pages: {result.get('page_count', 0)}")
            
            # Show indicators found
            indicators = result.get('indicators_found', [])
            if indicators:
                print(f"\n   Indicators found ({len(indicators)}):")
                for ind in indicators[:5]:
                    print(f"     - {ind}")
            
            # Show extracted data if CMS-1500
            if result.get('is_cms1500'):
                patient = result.get('patient_info', {})
                if patient.get('name'):
                    print(f"\n   Patient: {patient.get('name')}")
                
                insurance = result.get('insurance_info', {})
                if insurance.get('insured_id'):
                    print(f"   Insurance ID: {insurance.get('insured_id')}")
                
                diagnosis = result.get('diagnosis_info', {})
                if diagnosis.get('diagnosis_codes'):
                    print(f"   Diagnoses: {', '.join(diagnosis['diagnosis_codes'][:3])}")
            
            # Show validation errors
            errors = result.get('validation_errors', [])
            if errors:
                print(f"\n   ⚠️ Validation issues ({len(errors)}):")
                for err in errors[:3]:
                    print(f"     - {err}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            logger.error(f"Processing failed for {s3_key}", exc_info=True)


async def test_api_v2():
    """Test the API with new flow."""
    import httpx
    
    print("\n" + "="*60)
    print("Testing API /api/v2/process with new flow")
    print("="*60 + "\n")
    
    url = "http://localhost:8000/api/v2/process"
    
    test_cases = [
        {"s3_key": "cms1500_test.pdf", "bucket": "medical-documents"},
        {"s3_key": "misaligned.pdf", "bucket": "medical-documents"}
    ]
    
    for request_data in test_cases:
        print(f"\n📨 Testing: {request_data['s3_key']}")
        print("-" * 40)
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=request_data)
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success!")
                
                proc_info = data.get('processing_info', {})
                print(f"   Document type: {proc_info.get('document_type')}")
                print(f"   Confidence: {proc_info.get('confidence', 0):.2f}")
                print(f"   Processing time: {proc_info.get('processing_time_ms', 0)}ms")
                
                extracted = data.get('extracted_data', {})
                if extracted.get('patient'):
                    print(f"   Patient data extracted: ✓")
                if extracted.get('procedures'):
                    print(f"   Procedures found: {len(extracted['procedures'])}")
                    
            elif response.status_code == 400:
                error = response.json()
                print(f"⚠️ Not CMS-1500: {error['detail']['error']['message']}")
            else:
                print(f"❌ Error: {response.text[:200]}")
                
        except httpx.ConnectError:
            print("❌ Cannot connect to API server")
            print("   Please ensure Docker services are running:")
            print("   docker-compose up -d")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def main():
    """Run all tests."""
    
    print("\n" + "🚀 " * 20)
    print("HCFA Reader Agent V2 Test Suite")
    print("PyMuPDF + AWS Textract Integration")
    print("🚀 " * 20)
    
    # Check LocalStack
    import boto3
    
    print("\n🔍 Checking LocalStack services...")
    
    try:
        # Check S3
        s3 = boto3.client(
            's3',
            endpoint_url='http://localhost:4566',
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )
        buckets = s3.list_buckets()
        print(f"✅ S3 available. Buckets: {[b['Name'] for b in buckets['Buckets']]}")
        
        # Check Textract
        textract = boto3.client(
            'textract',
            endpoint_url='http://localhost:4566',
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1'
        )
        # Note: LocalStack may not fully support Textract, but we check anyway
        print("✅ Textract client initialized")
        
    except Exception as e:
        print(f"❌ LocalStack issue: {str(e)}")
        print("Note: LocalStack may not fully support Textract.")
        print("The code will fall back to text extraction if Textract fails.")
    
    # Run tests
    await test_hcfa_reader_v2()
    await test_api_v2()
    
    print("\n" + "="*60)
    print("✅ Test suite completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())