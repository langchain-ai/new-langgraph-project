"""Test script for HCFA Reader Agent and /api/v2/process endpoint."""

import asyncio
import json
import logging
from agents.hcfa_reader import graph as hcfa_reader_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_hcfa_reader_direct():
    """Test HCFA Reader Agent directly."""
    
    print("\n=== Testing HCFA Reader Agent Directly ===\n")
    
    # Test context
    context = {
        "s3_bucket": "medical-documents",
        "aws_region": "us-east-1",
        "openai_api_key": None,  # Will use mock data
        "enable_validation": True,
        "max_pages": 2
    }
    
    # Test state
    initial_state = {
        "s3_key": "test-files/cms1500-sample.pdf",
        "s3_bucket": "medical-documents"
    }
    
    try:
        # Execute the graph
        result = await hcfa_reader_graph.ainvoke(
            initial_state,
            config={"configurable": context}
        )
        
        # Print results
        print("Document Type:", result.get("document_type"))
        print("Is CMS-1500:", result.get("is_cms1500"))
        print("Confidence:", result.get("confidence"))
        print("Processing Status:", result.get("processing_status"))
        print("\nIndicators Found:")
        for indicator in result.get("indicators_found", [])[:5]:
            print(f"  - {indicator}")
        
        print("\nExtracted Data Summary:")
        if result.get("patient_info"):
            print("  Patient Name:", result["patient_info"].get("name"))
            print("  Patient DOB:", result["patient_info"].get("dob"))
        
        if result.get("insurance_info"):
            print("  Insured ID:", result["insurance_info"].get("insured_id"))
            print("  Plan Name:", result["insurance_info"].get("plan_name"))
        
        if result.get("procedures_info"):
            print(f"  Procedures Count: {len(result['procedures_info'])}")
            for proc in result["procedures_info"][:2]:
                print(f"    - CPT: {proc.get('cpt_code')}, Charge: ${proc.get('charges')}")
        
        if result.get("validation_errors"):
            print("\nValidation Errors:")
            for error in result["validation_errors"]:
                print(f"  - {error}")
        
        print("\nOptimization Stats:")
        stats = result.get("optimization_stats", {})
        if stats:
            print(f"  File Size: {stats.get('file_size', 0):,} bytes")
            print(f"  Downloaded: {stats.get('bytes_downloaded', 0):,} bytes")
            print(f"  Saved: {stats.get('bytes_saved', 0):,} bytes ({stats.get('savings_percentage', 0):.1f}%)")
        
        print("\n✅ Direct test completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Direct test failed: {str(e)}")
        logger.error(f"Error: {str(e)}", exc_info=True)
        return False


async def test_api_endpoint():
    """Test the /api/v2/process endpoint."""
    
    print("\n=== Testing /api/v2/process Endpoint ===\n")
    
    try:
        import httpx
        
        # API endpoint
        url = "http://localhost:8000/api/v2/process"
        
        # Test request
        request_data = {
            "s3_key": "test-files/cms1500-sample.pdf",
            "bucket": "medical-documents"
        }
        
        print(f"Sending request to {url}")
        print(f"Request data: {json.dumps(request_data, indent=2)}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=request_data,
                timeout=30.0
            )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nResponse Summary:")
            print(f"  Status: {data.get('status')}")
            
            proc_info = data.get("processing_info", {})
            print(f"  Document Type: {proc_info.get('document_type')}")
            print(f"  Confidence: {proc_info.get('confidence')}")
            print(f"  Processing Time: {proc_info.get('processing_time_ms')}ms")
            print(f"  Pages Processed: {proc_info.get('pages_processed')}")
            
            extracted = data.get("extracted_data", {})
            if extracted.get("patient"):
                print("\nPatient Info:")
                print(f"  Name: {extracted['patient'].get('name')}")
                print(f"  DOB: {extracted['patient'].get('dob')}")
            
            if extracted.get("procedures"):
                print(f"\nProcedures: {len(extracted['procedures'])} found")
            
            print("\n✅ API test completed successfully")
            return True
        else:
            print(f"\n❌ API returned error: {response.text}")
            return False
            
    except httpx.ConnectError:
        print("\n⚠️  Could not connect to API server.")
        print("Please make sure the server is running: python api/main.py")
        return False
    except Exception as e:
        print(f"\n❌ API test failed: {str(e)}")
        return False


async def main():
    """Run all tests."""
    
    print("=" * 60)
    print("HCFA Reader Agent Test Suite")
    print("=" * 60)
    
    # Test 1: Direct agent test
    direct_success = await test_hcfa_reader_direct()
    
    # Test 2: API endpoint test
    api_success = await test_api_endpoint()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Direct Agent Test: {'✅ PASSED' if direct_success else '❌ FAILED'}")
    print(f"API Endpoint Test: {'✅ PASSED' if api_success else '❌ FAILED'}")
    
    if direct_success and api_success:
        print("\n🎉 All tests passed!")
    elif direct_success:
        print("\n⚠️  Direct test passed but API test failed.")
        print("Make sure the API server is running.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())