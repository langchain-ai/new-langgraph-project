#!/usr/bin/env python3
"""Test script for the Medical Claims Processor API."""

import requests
import json
import time

# API configuration
API_BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    print("✓ Health check passed\n")

def test_root_endpoint():
    """Test the root endpoint."""
    print("Testing root endpoint...")
    response = requests.get(f"{API_BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    print("✓ Root endpoint passed\n")

def test_process_document(s3_key: str, bucket: str = None):
    """Test the document processing endpoint."""
    print(f"Testing document processing for: {s3_key}")
    
    request_data = {
        "s3_key": s3_key
    }
    if bucket:
        request_data["bucket"] = bucket
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    start_time = time.time()
    response = requests.post(
        f"{API_BASE_URL}/api/v1/process",
        json=request_data
    )
    processing_time = time.time() - start_time
    
    print(f"Status: {response.status_code}")
    print(f"Processing time: {processing_time:.2f}s")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        print("✓ Document processing passed\n")
    else:
        print(f"Error: {response.text}")
        print("✗ Document processing failed\n")
    
    return response

def test_error_handling():
    """Test error handling for non-existent file."""
    print("Testing error handling for non-existent file...")
    
    request_data = {
        "s3_key": "non-existent-file.pdf"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/process",
        json=request_data
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 404:
        print("✓ Error handling passed (404 for non-existent file)\n")
    else:
        print(f"Response: {response.text}")
        print("✗ Error handling unexpected response\n")

if __name__ == "__main__":
    print("=" * 60)
    print("Medical Claims Processor API Test Suite")
    print("=" * 60 + "\n")
    
    # Test basic endpoints
    test_health_check()
    test_root_endpoint()
    
    # Test document processing
    # Note: These require actual S3 files to exist
    # Uncomment and modify with your test files:
    
    # test_process_document("test-files/cms1500-sample.pdf")
    # test_process_document("test-files/hcfa1500-sample.pdf")
    
    # Test error handling
    test_error_handling()
    
    print("=" * 60)
    print("Test suite completed!")
    print("=" * 60)