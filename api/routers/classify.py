"""Document classification router."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class LocalFileClassifier:
    """Simple local file classifier for testing."""
    
    @staticmethod
    def classify_content(content: bytes) -> Dict[str, Any]:
        """Classify document based on content."""
        
        # CMS-1500 indicators
        CMS_INDICATORS = [
            b"CMS-1500",
            b"HEALTH INSURANCE CLAIM FORM",
            b"PATIENT'S NAME",
            b"INSURED'S I.D. NUMBER",
            b"DIAGNOSIS OR NATURE OF ILLNESS",
            b"PROCEDURES, SERVICES, OR SUPPLIES",
            b"TOTAL CHARGE",
            b"NPI"
        ]
        
        # HCFA-1500 indicators (older version)
        HCFA_INDICATORS = [
            b"HCFA-1500",
            b"HCFA 1500",
            b"APPROVED OMB-0938-0999",
            b"CHAMPUS",
            b"CHAMPVA",
            b"FECA BLK LUNG"
        ]
        
        # Convert to uppercase for comparison
        content_upper = content.upper()
        
        # Count indicators found
        cms_found = []
        hcfa_found = []
        
        for indicator in CMS_INDICATORS:
            if indicator in content_upper:
                cms_found.append(indicator.decode('utf-8', errors='ignore'))
        
        for indicator in HCFA_INDICATORS:
            if indicator in content_upper:
                hcfa_found.append(indicator.decode('utf-8', errors='ignore'))
        
        # Determine document type
        if len(cms_found) >= 3:
            return {
                "document_type": "cms_1500",
                "confidence": min(1.0, len(cms_found) / 8.0),
                "indicators_found": cms_found[:5],
                "processor": "textract",
                "reason": f"Found {len(cms_found)} CMS-1500 indicators"
            }
        elif len(hcfa_found) >= 2:
            return {
                "document_type": "hcfa_1500",
                "confidence": min(1.0, len(hcfa_found) / 6.0),
                "indicators_found": hcfa_found[:5],
                "processor": "textract",
                "reason": f"Found {len(hcfa_found)} HCFA-1500 indicators"
            }
        else:
            return {
                "document_type": "unknown",
                "confidence": 0.0,
                "indicators_found": [],
                "processor": "openai",
                "reason": "No clear document type indicators found"
            }


@router.post("/classify/file")
async def classify_uploaded_file(file: UploadFile = File(...)):
    """
    Classify an uploaded document.
    
    Args:
        file: Uploaded file
        
    Returns:
        Classification results
    """
    try:
        # Read file content (up to 1MB)
        content = await file.read(1024 * 1024)
        
        # Classify the content
        classifier = LocalFileClassifier()
        result = classifier.classify_content(content)
        
        return {
            "status": "success",
            "filename": file.filename,
            "file_size": len(content),
            "classification": result
        }
        
    except Exception as e:
        logger.error(f"Classification failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}"
        )


@router.post("/classify/local")
async def classify_local_file(filepath: str):
    """
    Classify a local test file.
    
    Args:
        filepath: Path to local file (relative to tests/test-files/)
        
    Returns:
        Classification results
    """
    try:
        # Build full path
        base_path = "/Users/xiong_ge/Desktop/MyCode/shoreline/ai-agents/tests/test-files"
        full_path = os.path.join(base_path, filepath)
        
        # Check if file exists
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Test file not found: {filepath}")
        
        # Read file content (up to 1MB)
        with open(full_path, 'rb') as f:
            content = f.read(1024 * 1024)
        
        # Classify the content
        classifier = LocalFileClassifier()
        result = classifier.classify_content(content)
        
        return {
            "status": "success",
            "filepath": filepath,
            "file_size": len(content),
            "classification": result
        }
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Classification failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}"
        )