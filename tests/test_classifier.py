#!/usr/bin/env python3
"""Test document classifier with local files."""

import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from agents.document_classifier.graph import graph as classifier_graph


async def test_classification():
    """Test document classification with local files."""
    
    # Test files
    test_files = [
        "cms1500-sample.txt",
        "hcfa1500-sample.txt"
    ]
    
    # Configure context for local file testing
    context = {
        "s3_bucket": "local:/Users/xiong_ge/Desktop/MyCode/shoreline/ai-agents/tests/test-files",
        "aws_region": "us-east-1",  # Not used in local mode
        "confidence_threshold": 0.7
    }
    
    print("=" * 60)
    print("Document Classification Test")
    print("=" * 60)
    
    for filename in test_files:
        print(f"\n Testing: {filename}")
        print("-" * 40)
        
        # Initial state
        initial_state = {
            "s3_key": filename,
            "content_sample": b"",
            "content_type": "",
            "file_size": 0,
            "document_type": "unknown",
            "processor": "textract",
            "confidence": 0.0,
            "indicators_found": [],
            "classification_reason": ""
        }
        
        try:
            # Run the graph
            result = await classifier_graph.ainvoke(
                initial_state,
                context=context
            )
            
            # Display results
            print(f"  Document Type: {result['document_type']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Processor: {result['processor']}")
            print(f"  Reason: {result['classification_reason']}")
            print(f"  Indicators Found: {', '.join(result['indicators_found'][:3])}")
            print(f"  File Size: {result['file_size']} bytes")
            
        except Exception as e:
            print(f"  Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_classification())