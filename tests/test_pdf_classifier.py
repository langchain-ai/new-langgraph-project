#!/usr/bin/env python3
"""Test document classifier with PDF file."""

import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from agents.document_classifier.graph import graph as classifier_graph


async def test_pdf_classification():
    """Test document classification with PDF file."""
    
    # PDF file to test
    pdf_file = "test.pdf"
    
    # Configure context for local file testing
    context = {
        "s3_bucket": "local:/Users/xiong_ge/Desktop/MyCode/shoreline/ai-agents",
        "aws_region": "us-east-1",  # Not used in local mode
        "confidence_threshold": 0.7
    }
    
    print("=" * 60)
    print("PDF Document Classification Test")
    print("=" * 60)
    
    print(f"\nTesting: {pdf_file}")
    print("-" * 40)
    
    # Initial state
    initial_state = {
        "s3_key": pdf_file,
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
        if result['indicators_found']:
            print(f"  Indicators Found: {', '.join(result['indicators_found'][:5])}")
        else:
            print(f"  Indicators Found: None")
        print(f"  File Size: {result['file_size']:,} bytes")
        
        # Show first 500 bytes of content to understand what was read
        if result['content_sample']:
            print(f"\n  Content Preview (first 500 bytes):")
            preview = result['content_sample'][:500]
            # Try to decode as text, otherwise show as hex
            try:
                text_preview = preview.decode('utf-8', errors='ignore')
                # Clean up non-printable characters
                text_preview = ''.join(char if char.isprintable() or char.isspace() else '.' for char in text_preview)
                print(f"  {text_preview[:200]}...")
            except:
                print(f"  (Binary content - showing hex): {preview[:50].hex()}")
        
    except Exception as e:
        print(f"  Error: {str(e)}")
        import traceback
        print(f"  Traceback: {traceback.format_exc()}")
    
    print("\n" + "=" * 60)
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_pdf_classification())