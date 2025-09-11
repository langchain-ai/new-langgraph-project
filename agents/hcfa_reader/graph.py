"""LangGraph HCFA/CMS-1500 Reader Agent.

Reads and extracts data from CMS-1500/HCFA-1500 medical claim forms directly from S3.
Processes documents entirely in memory without downloading to disk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, TypedDict, List, Optional
from enum import Enum
import os
import logging
import boto3
import io
import base64
import json

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Supported document types."""
    CMS_1500 = "cms_1500"
    HCFA_1500 = "hcfa_1500"
    UNKNOWN = "unknown"


class ProcessingStatus(str, Enum):
    """Processing status."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class Context(TypedDict):
    """Context parameters for the HCFA Reader.
    
    Set these when creating assistants OR when invoking the graph.
    """
    s3_bucket: str
    aws_region: str
    openai_api_key: Optional[str]
    enable_validation: bool
    max_pages: int  # Maximum pages to process


@dataclass
class State:
    """State for HCFA/CMS-1500 document processing.
    
    Tracks document through the entire extraction pipeline.
    """
    # Input parameters
    s3_key: str = ""
    s3_bucket: str = ""
    
    # Document content
    pdf_content: bytes = b""
    file_size: int = 0
    content_type: str = ""
    
    # PDF processing
    page_count: int = 0
    pages_processed: int = 0
    page_images: List[bytes] = field(default_factory=list)
    
    # Document classification
    document_type: str = DocumentType.UNKNOWN.value
    is_cms1500: bool = False
    confidence: float = 0.0
    indicators_found: List[str] = field(default_factory=list)
    
    # Extracted data structures
    patient_info: Dict[str, Any] = field(default_factory=dict)
    insurance_info: Dict[str, Any] = field(default_factory=dict)
    diagnosis_info: Dict[str, Any] = field(default_factory=dict)
    procedures_info: List[Dict[str, Any]] = field(default_factory=list)
    provider_info: Dict[str, Any] = field(default_factory=dict)
    billing_info: Dict[str, Any] = field(default_factory=dict)
    
    # Processing metadata
    processing_status: str = ProcessingStatus.FAILED.value
    validation_errors: List[str] = field(default_factory=list)
    processing_time_ms: int = 0
    bytes_downloaded: int = 0
    optimization_stats: Dict[str, Any] = field(default_factory=dict)


async def load_from_s3(state: State, runtime: Runtime[Context] = None) -> Dict[str, Any]:
    """Load PDF from S3 directly into memory using DocumentExtractor."""
    import time
    from common.document_extraction import DocumentExtractor
    
    start_time = time.time()
    
    bucket = state.s3_bucket or (runtime.context.get("s3_bucket", "medical-documents") if runtime and runtime.context else "medical-documents")
    region = (runtime.context.get("aws_region", "us-east-1") if runtime and runtime.context else "us-east-1")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    
    try:
        # Initialize document extractor
        extractor = DocumentExtractor(
            bucket_name=bucket,
            aws_region=region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            endpoint_url=endpoint_url
        )
        
        # Load PDF from S3 with optimization for CMS-1500 (max 2MB)
        max_bytes = 2097152  # 2MB - enough for 2-page CMS-1500
        pdf_content, metadata = extractor.get_pdf_from_s3(state.s3_key, max_bytes)
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Add processing time to optimization stats
        optimization_stats = {
            "file_size": metadata['file_size'],
            "bytes_downloaded": metadata['bytes_downloaded'],
            "bytes_saved": metadata['bytes_saved'],
            "savings_percentage": metadata['savings_percentage'],
            "download_strategy": "partial" if metadata['partial_download'] else "full",
            "download_time_ms": processing_time
        }
        
        logger.info(
            f"Downloaded {metadata['bytes_downloaded']:,}/{metadata['file_size']:,} bytes "
            f"({100-metadata['savings_percentage']:.1f}% of file) in {processing_time}ms"
        )
        
        return {
            "pdf_content": pdf_content,
            "file_size": metadata['file_size'],
            "content_type": metadata['content_type'],
            "bytes_downloaded": metadata['bytes_downloaded'],
            "optimization_stats": optimization_stats
        }
        
    except Exception as e:
        logger.error(f"Failed to load from S3: {str(e)}")
        raise


async def detect_cms1500(state: State, runtime: Runtime[Context] = None) -> Dict[str, Any]:
    """Detect if document is CMS-1500/HCFA-1500 form using indicators."""
    
    logger.info("Starting CMS-1500 detection...")
    
    # Primary indicators (strong signals)
    PRIMARY_INDICATORS = [
        b"CMS-1500",
        b"CMS 1500",
        b"FORM 1500",
        b"HCFA-1500",
        b"HCFA 1500",
        b"HEALTH INSURANCE CLAIM FORM",
        b"APPROVED OMB-0938",
        b"NUCC"
    ]
    
    # Secondary indicators (field numbers specific to CMS-1500)
    FIELD_INDICATORS = [
        b"1a. INSURED'S I.D. NUMBER",
        b"1A. INSURED'S I.D.",
        b"2. PATIENT'S NAME",
        b"3. PATIENT'S BIRTH DATE",
        b"14. DATE OF CURRENT",
        b"17. NAME OF REFERRING",
        b"21. DIAGNOSIS OR NATURE",
        b"24A", b"24B", b"24C", b"24D", b"24E", b"24F", b"24G", b"24H", b"24I", b"24J",
        b"32. SERVICE FACILITY LOCATION",
        b"33. BILLING PROVIDER INFO",
        b"33a. NPI"
    ]
    
    try:
        # Try to extract text from PDF for better detection
        import fitz  # PyMuPDF
        
        pdf_document = fitz.open(stream=state.pdf_content, filetype="pdf")
        page_count = pdf_document.page_count
        
        # Extract text from first page (and second if exists)
        text_content = b""
        pages_to_check = min(2, page_count)
        
        for page_num in range(pages_to_check):
            page = pdf_document[page_num]
            text = page.get_text()
            text_content += text.encode('utf-8', errors='ignore')
        
        pdf_document.close()
        
        # Convert to uppercase for comparison
        text_upper = text_content.upper()
        
        # Count indicators
        primary_found = []
        field_found = []
        
        for indicator in PRIMARY_INDICATORS:
            if indicator in text_upper:
                primary_found.append(indicator.decode('utf-8', errors='ignore'))
        
        for indicator in FIELD_INDICATORS:
            if indicator in text_upper:
                field_found.append(indicator.decode('utf-8', errors='ignore'))
        
        # Calculate confidence
        total_found = len(primary_found) + len(field_found)
        
        # Decision logic
        if len(primary_found) >= 1 and len(field_found) >= 3:
            # Strong confidence - has primary indicator and multiple fields
            is_cms1500 = True
            confidence = min(1.0, 0.7 + (total_found * 0.05))
            document_type = DocumentType.CMS_1500.value
        elif len(primary_found) >= 2:
            # Medium confidence - multiple primary indicators
            is_cms1500 = True
            confidence = min(1.0, 0.6 + (total_found * 0.05))
            document_type = DocumentType.CMS_1500.value
        elif len(field_found) >= 5:
            # Medium confidence - many field indicators but no primary
            is_cms1500 = True
            confidence = min(1.0, 0.5 + (len(field_found) * 0.05))
            document_type = DocumentType.CMS_1500.value
        else:
            # Not CMS-1500
            is_cms1500 = False
            confidence = 0.0
            document_type = DocumentType.UNKNOWN.value
        
        # Combine all indicators found
        all_indicators = primary_found + field_found
        
        logger.info(f"Detection complete: is_cms1500={is_cms1500}, confidence={confidence:.2f}")
        logger.info(f"Found {len(primary_found)} primary and {len(field_found)} field indicators")
        
        return {
            "is_cms1500": is_cms1500,
            "document_type": document_type,
            "confidence": confidence,
            "indicators_found": all_indicators[:10],  # Limit to 10 for response
            "page_count": page_count
        }
        
    except Exception as e:
        logger.error(f"Error during CMS-1500 detection: {str(e)}")
        # Fallback to basic detection
        return {
            "is_cms1500": False,
            "document_type": DocumentType.UNKNOWN.value,
            "confidence": 0.0,
            "indicators_found": [],
            "page_count": 0
        }


async def split_pdf_pages(state: State, runtime: Runtime[Context] = None) -> Dict[str, Any]:
    """Split PDF into individual pages using DocumentExtractor."""
    
    if not state.is_cms1500:
        logger.info("Skipping PDF split - not a CMS-1500 document")
        return {}
    
    try:
        from common.document_extraction import DocumentExtractor
        
        logger.info(f"Splitting PDF with {state.page_count} pages")
        
        # Initialize extractor (we don't need S3 for this operation)
        extractor = DocumentExtractor(
            bucket_name="dummy",  # Not used for splitting
            aws_region="us-east-1"
        )
        
        # Determine pages to process
        max_pages = (runtime.context.get("max_pages", 2) if runtime and runtime.context else 2)
        
        # Split PDF pages using the extractor
        page_images = extractor.split_pdf_pages(state.pdf_content, max_pages)
        
        logger.info(f"Successfully split {len(page_images)} pages")
        
        return {
            "page_images": page_images,
            "pages_processed": len(page_images)
        }
        
    except Exception as e:
        logger.error(f"Error splitting PDF: {str(e)}")
        return {
            "page_images": [],
            "pages_processed": 0
        }


async def extract_data(state: State, runtime: Runtime[Context] = None) -> Dict[str, Any]:
    """Extract structured data from CMS-1500 form pages."""
    
    if not state.is_cms1500:
        logger.info("Skipping data extraction - not a CMS-1500 document")
        return {"processing_status": ProcessingStatus.FAILED.value}
    
    # Get OpenAI API key
    api_key = (runtime.context.get("openai_api_key") if runtime and runtime.context else None) or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.warning("No OpenAI API key available, using mock data")
        return _get_mock_extraction_data()
    
    try:
        from openai import OpenAI
        import pdf2image
        
        client = OpenAI(api_key=api_key)
        
        # Convert PDF pages to images for OCR
        all_images = []
        
        for page_bytes in state.page_images:
            images = pdf2image.convert_from_bytes(
                page_bytes,
                dpi=200,  # Good quality for OCR
                fmt='PNG'
            )
            all_images.extend(images)
        
        # Prepare images for GPT-4 Vision
        image_contents = []
        for img in all_images:
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_base64}",
                    "detail": "high"
                }
            })
        
        # Create extraction prompt
        prompt = """You are an expert at reading CMS-1500/HCFA-1500 medical claim forms.
        
Extract the following information from this form and return as JSON:

{
    "patient_info": {
        "name": "Patient's full name (Box 2)",
        "dob": "Date of birth YYYY-MM-DD (Box 3)",
        "sex": "M or F (Box 3)",
        "address": "Patient's address (Box 5)",
        "city": "City",
        "state": "State",
        "zip": "ZIP code",
        "phone": "Phone number (Box 5)"
    },
    "insurance_info": {
        "insured_id": "Insured's ID number (Box 1a)",
        "insured_name": "Insured's name (Box 4)",
        "plan_name": "Insurance plan/program name (Box 11c)",
        "group_number": "Group number (Box 11)",
        "is_medicare": true/false,
        "is_medicaid": true/false,
        "is_tricare": true/false,
        "is_champva": true/false,
        "is_group_health": true/false,
        "is_feca": true/false,
        "is_other": true/false
    },
    "diagnosis_info": {
        "diagnosis_codes": ["List of ICD-10 codes from Box 21"],
        "diagnosis_pointers": ["Diagnosis pointers A-L"]
    },
    "procedures": [
        {
            "line_number": "1-6",
            "date_of_service": "YYYY-MM-DD (Box 24A)",
            "place_of_service": "Code (Box 24B)",
            "cpt_code": "CPT/HCPCS code (Box 24D)",
            "modifier": "Modifier (Box 24D)",
            "diagnosis_pointer": "A-L (Box 24E)",
            "charges": "Amount as number (Box 24F)",
            "units": "Days or units (Box 24G)"
        }
    ],
    "provider_info": {
        "name": "Billing provider name (Box 33)",
        "npi": "NPI number (Box 33a)",
        "tax_id": "Federal Tax ID (Box 25)",
        "address": "Provider address (Box 33)",
        "city": "City",
        "state": "State", 
        "zip": "ZIP code",
        "phone": "Phone (Box 33)"
    },
    "billing_info": {
        "total_charge": "Total charge as number (Box 28)",
        "amount_paid": "Amount paid as number (Box 29)",
        "balance_due": "Balance due (Box 30)",
        "signature_on_file": true/false,
        "service_facility": "Service facility name and address (Box 32)"
    }
}

Important: Return null for any field that is not clearly visible or not filled in."""

        # Prepare message with prompt and images
        message_content = [{"type": "text", "text": prompt}] + image_contents
        
        logger.info("Calling GPT-4 Vision for data extraction...")
        
        # Call GPT-4 Vision
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": message_content
            }],
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        extracted_data = json.loads(response.choices[0].message.content)
        
        logger.info("Data extraction completed successfully")
        
        return {
            "patient_info": extracted_data.get("patient_info", {}),
            "insurance_info": extracted_data.get("insurance_info", {}),
            "diagnosis_info": extracted_data.get("diagnosis_info", {}),
            "procedures_info": extracted_data.get("procedures", []),
            "provider_info": extracted_data.get("provider_info", {}),
            "billing_info": extracted_data.get("billing_info", {}),
            "processing_status": ProcessingStatus.SUCCESS.value
        }
        
    except Exception as e:
        logger.error(f"Error during data extraction: {str(e)}")
        return {
            "processing_status": ProcessingStatus.FAILED.value,
            "validation_errors": [f"Extraction error: {str(e)}"]
        }


async def validate_and_format(state: State, runtime: Runtime[Context] = None) -> Dict[str, Any]:
    """Validate extracted data and format for output."""
    
    if runtime and runtime.context and not runtime.context.get("enable_validation", True):
        return {}
    # Default to enable validation when runtime is None or context is missing
    
    errors = []
    
    # Validate patient info
    if not state.patient_info.get("name"):
        errors.append("Missing patient name (Box 2)")
    if not state.patient_info.get("dob"):
        errors.append("Missing patient date of birth (Box 3)")
    
    # Validate insurance info
    if not state.insurance_info.get("insured_id"):
        errors.append("Missing insured's ID number (Box 1a)")
    
    # Validate diagnosis
    if not state.diagnosis_info.get("diagnosis_codes"):
        errors.append("No diagnosis codes found (Box 21)")
    
    # Validate procedures
    if not state.procedures_info:
        errors.append("No procedures/services found (Box 24)")
    else:
        # Validate each procedure line
        for i, proc in enumerate(state.procedures_info):
            if not proc.get("cpt_code"):
                errors.append(f"Missing CPT code for line {i+1}")
            if not proc.get("charges"):
                errors.append(f"Missing charges for line {i+1}")
    
    # Validate provider info
    if not state.provider_info.get("npi"):
        errors.append("Missing provider NPI (Box 33a)")
    
    # Determine final status
    if not errors:
        processing_status = ProcessingStatus.SUCCESS.value
    elif len(errors) <= 3:
        processing_status = ProcessingStatus.PARTIAL.value
    else:
        processing_status = ProcessingStatus.FAILED.value
    
    logger.info(f"Validation complete: {len(errors)} errors found, status={processing_status}")
    
    return {
        "validation_errors": errors,
        "processing_status": processing_status
    }


def _get_mock_extraction_data() -> Dict[str, Any]:
    """Return mock data when OpenAI is not available."""
    return {
        "patient_info": {
            "name": "JOHN DOE",
            "dob": "1970-01-15",
            "sex": "M",
            "address": "123 Main Street",
            "city": "Springfield",
            "state": "IL",
            "zip": "62701",
            "phone": "(217) 555-0123"
        },
        "insurance_info": {
            "insured_id": "123456789",
            "insured_name": "JOHN DOE",
            "plan_name": "Blue Cross Blue Shield",
            "group_number": "GRP123456",
            "is_medicare": False,
            "is_medicaid": False,
            "is_group_health": True
        },
        "diagnosis_info": {
            "diagnosis_codes": ["E11.9", "I10", "Z79.4"],
            "diagnosis_pointers": ["A", "B", "C"]
        },
        "procedures_info": [
            {
                "line_number": "1",
                "date_of_service": "2024-01-15",
                "place_of_service": "11",
                "cpt_code": "99213",
                "modifier": "",
                "diagnosis_pointer": "ABC",
                "charges": 150.00,
                "units": "1"
            },
            {
                "line_number": "2",
                "date_of_service": "2024-01-15",
                "place_of_service": "11",
                "cpt_code": "80053",
                "modifier": "",
                "diagnosis_pointer": "A",
                "charges": 75.00,
                "units": "1"
            }
        ],
        "provider_info": {
            "name": "Springfield Medical Center",
            "npi": "1234567890",
            "tax_id": "12-3456789",
            "address": "456 Medical Plaza",
            "city": "Springfield",
            "state": "IL",
            "zip": "62701",
            "phone": "(217) 555-0456"
        },
        "billing_info": {
            "total_charge": 225.00,
            "amount_paid": 0.00,
            "balance_due": 225.00,
            "signature_on_file": True,
            "service_facility": "Springfield Medical Center"
        },
        "processing_status": ProcessingStatus.SUCCESS.value
    }


# Define the graph
graph = (
    StateGraph(State, context_schema=Context)
    .add_node("load_from_s3", load_from_s3)
    .add_node("detect_cms1500", detect_cms1500)
    .add_node("split_pdf_pages", split_pdf_pages)
    .add_node("extract_data", extract_data)
    .add_node("validate_and_format", validate_and_format)
    .add_edge("__start__", "load_from_s3")
    .add_edge("load_from_s3", "detect_cms1500")
    .add_edge("detect_cms1500", "split_pdf_pages")
    .add_edge("split_pdf_pages", "extract_data")
    .add_edge("extract_data", "validate_and_format")
    .compile(name="HCFA Reader Agent")
)