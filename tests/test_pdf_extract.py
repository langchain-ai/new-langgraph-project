#!/usr/bin/env python3
"""Test PDF text extraction."""

import PyPDF2
import os

pdf_path = "/Users/xiong_ge/Desktop/MyCode/shoreline/ai-agents/test.pdf"

print(f"Testing PDF: {pdf_path}")
print(f"File size: {os.path.getsize(pdf_path):,} bytes")
print("=" * 60)

try:
    with open(pdf_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        
        print(f"Number of pages: {len(pdf_reader.pages)}")
        print(f"PDF metadata: {pdf_reader.metadata}")
        print("=" * 60)
        
        # Extract text from first few pages
        for page_num in range(min(3, len(pdf_reader.pages))):
            print(f"\nPage {page_num + 1} content:")
            print("-" * 40)
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            
            # Show first 1000 characters
            if text:
                print(text[:1000])
                if len(text) > 1000:
                    print("... (truncated)")
            else:
                print("(No text extracted)")
            print("-" * 40)
            
        # Check for medical form indicators
        all_text = ""
        for page in pdf_reader.pages[:10]:  # Check first 10 pages
            all_text += page.extract_text()
        
        print("\nSearching for medical form indicators...")
        indicators = [
            "CMS-1500", "HCFA-1500", "HEALTH INSURANCE CLAIM",
            "PATIENT", "DIAGNOSIS", "PROCEDURE", "INSURED",
            "MEDICARE", "MEDICAID", "CPT", "ICD"
        ]
        
        text_upper = all_text.upper()
        found = []
        for indicator in indicators:
            if indicator in text_upper:
                found.append(indicator)
                # Show context
                idx = text_upper.find(indicator)
                context = all_text[max(0, idx-20):min(len(all_text), idx+50)]
                print(f"  Found '{indicator}': ...{context}...")
        
        if not found:
            print("  No medical form indicators found")
        else:
            print(f"\nTotal indicators found: {found}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()