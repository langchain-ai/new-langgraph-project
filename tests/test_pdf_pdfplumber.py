#!/usr/bin/env python3
"""Test PDF with pdfplumber."""

import pdfplumber
import os

pdf_path = "/Users/xiong_ge/Desktop/MyCode/shoreline/ai-agents/test.pdf"

print(f"Testing PDF with pdfplumber: {pdf_path}")
print(f"File size: {os.path.getsize(pdf_path):,} bytes")
print("=" * 60)

try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Number of pages: {len(pdf.pages)}")
        print(f"PDF metadata: {pdf.metadata}")
        print("=" * 60)
        
        for i, page in enumerate(pdf.pages[:3]):  # First 3 pages
            print(f"\nPage {i + 1}:")
            print("-" * 40)
            
            # Extract text
            text = page.extract_text()
            if text:
                print("Text found:")
                print(text[:1000])
                if len(text) > 1000:
                    print("... (truncated)")
            else:
                print("No text found")
            
            # Extract tables
            tables = page.extract_tables()
            if tables:
                print(f"\nTables found: {len(tables)}")
                for j, table in enumerate(tables[:2]):  # First 2 tables
                    print(f"Table {j + 1}:")
                    for row in table[:5]:  # First 5 rows
                        print("  ", row)
            
            # Check for images
            if hasattr(page, 'images'):
                images = page.images
                if images:
                    print(f"\nImages found: {len(images)}")
                    
        # Collect all text for analysis
        all_text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n"
        
        if all_text:
            print("\n" + "=" * 60)
            print("Searching for medical form indicators...")
            indicators = [
                "CMS-1500", "CMS 1500", "HCFA-1500", "HCFA 1500",
                "HEALTH INSURANCE", "CLAIM FORM",
                "PATIENT", "DIAGNOSIS", "PROCEDURE", "INSURED",
                "MEDICARE", "MEDICAID", "CPT", "ICD",
                "NPI", "PROVIDER", "BILLING"
            ]
            
            text_upper = all_text.upper()
            found = []
            for indicator in indicators:
                if indicator in text_upper:
                    found.append(indicator)
            
            if found:
                print(f"Indicators found: {found}")
                print(f"\nDocument likely type: ", end="")
                if "CMS-1500" in text_upper or "CMS 1500" in text_upper:
                    print("CMS-1500 form")
                elif "HCFA-1500" in text_upper or "HCFA 1500" in text_upper:
                    print("HCFA-1500 form")
                elif len(found) >= 5:
                    print("Medical claim form (type unclear)")
                else:
                    print("Medical document (not a standard claim form)")
            else:
                print("No medical form indicators found")
        else:
            print("\nNo text could be extracted from this PDF.")
            print("This might be a scanned image PDF that requires OCR.")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()