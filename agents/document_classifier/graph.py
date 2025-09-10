"""LangGraph document classifier agent.

Classifies medical documents (CMS-1500, HCFA-1500) and determines processing method.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, TypedDict, List, Optional
from enum import Enum

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime


class DocumentType(str, Enum):
    """Supported document types."""
    CMS_1500 = "cms_1500"
    HCFA_1500 = "hcfa_1500"
    UNKNOWN = "unknown"


class ProcessorType(str, Enum):
    """Available processors."""
    TEXTRACT = "textract"
    OPENAI = "openai"


class Context(TypedDict):
    """Context parameters for the document classifier.
    
    Set these when creating assistants OR when invoking the graph.
    """
    s3_bucket: str
    aws_region: str
    confidence_threshold: float


@dataclass
class State:
    """State for document classification.
    
    Tracks the document through the classification pipeline.
    """
    s3_key: str = ""
    content_sample: bytes = b""
    content_type: str = ""
    file_size: int = 0
    
    # Classification results
    document_type: str = DocumentType.UNKNOWN.value
    processor: str = ProcessorType.TEXTRACT.value
    confidence: float = 0.0
    indicators_found: List[str] = None
    classification_reason: str = ""
    
    def __post_init__(self):
        if self.indicators_found is None:
            self.indicators_found = []


async def download_sample(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Download document sample from S3 or local file for classification."""
    import os
    
    # Check if we're in test mode (s3_bucket starts with "local:")
    bucket = runtime.context.get("s3_bucket", "")
    
    if bucket.startswith("local:"):
        # Local file mode for testing
        base_path = bucket.replace("local:", "")
        file_path = os.path.join(base_path, state.s3_key)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file metadata
        file_size = os.path.getsize(file_path)
        
        # Determine content type based on extension
        if file_path.lower().endswith('.pdf'):
            content_type = "application/pdf"
        else:
            content_type = "text/plain"
        
        # Read content based on file type
        max_bytes = 1024 * 1024  # 1MB
        
        if content_type == "application/pdf":
            # Extract text from PDF
            try:
                import PyPDF2
                content_sample = b""
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    # Extract text from all pages (up to max_bytes)
                    for page_num in range(min(len(pdf_reader.pages), 10)):  # Max 10 pages
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        content_sample += text.encode('utf-8', errors='ignore')
                        if len(content_sample) >= max_bytes:
                            content_sample = content_sample[:max_bytes]
                            break
            except Exception as e:
                # If PDF parsing fails, read raw bytes
                with open(file_path, 'rb') as f:
                    content_sample = f.read(max_bytes)
        else:
            # Read text files directly
            with open(file_path, 'rb') as f:
                content_sample = f.read(max_bytes)
        
        return {
            "content_sample": content_sample,
            "content_type": content_type,
            "file_size": file_size
        }
    else:
        # S3 mode (original code)
        import os
        import boto3
        from botocore.exceptions import ClientError
        
        region = runtime.context.get("aws_region", "us-east-1")
        endpoint_url = os.getenv("AWS_ENDPOINT_URL")
        s3_client = boto3.client(
            's3', 
            region_name=region,
            endpoint_url=endpoint_url
        )
        
        try:
            # Get object metadata
            response = s3_client.head_object(Bucket=bucket, Key=state.s3_key)
            file_size = response['ContentLength']
            content_type = response.get('ContentType', 'application/octet-stream')
            
            # Strong CMS-1500 indicators for early detection
            STRONG_INDICATORS = [
                b"CMS-1500",
                b"CMS 1500",
                b"FORM 1500",
                b"HEALTH INSURANCE CLAIM FORM",
                b"APPROVED OMB-0938",
                b"1a. INSURED'S I.D. NUMBER",
                b"24A",  # Service line indicators
                b"DIAGNOSIS OR NATURE OF ILLNESS",
                b"NUCC",  # National Uniform Claim Committee
                b"HCFA-1500",
                b"HCFA 1500"
            ]
            
            # Progressive byte range strategy
            byte_ranges = [
                65536,   # 64KB - often enough for first page header
                131072,  # 128KB - usually covers full first page
                262144,  # 256KB - covers most single page PDFs
                524288,  # 512KB - safety buffer for complex layouts
            ]
            
            content_sample = b""
            text_content = b""
            strong_signal_count = 0
            confidence_threshold = 3  # Need at least 3 strong signals
            
            # Progressive streaming with early exit
            for chunk_size in byte_ranges:
                if chunk_size >= file_size:
                    # File is smaller than chunk, get entire file
                    response = s3_client.get_object(
                        Bucket=bucket,
                        Key=state.s3_key
                    )
                    content_sample = response['Body'].read()
                else:
                    # Get only the chunk we need
                    start_byte = len(content_sample)
                    end_byte = min(chunk_size - 1, file_size - 1)
                    
                    # Skip if we already have enough bytes
                    if start_byte >= end_byte:
                        break
                        
                    range_header = f'bytes={start_byte}-{end_byte}'
                    
                    try:
                        response = s3_client.get_object(
                            Bucket=bucket,
                            Key=state.s3_key,
                            Range=range_header
                        )
                        
                        new_chunk = response['Body'].read()
                        content_sample += new_chunk
                    except Exception as e:
                        # If range request fails, get the whole file
                        print(f"Range request failed: {e}, falling back to full download")
                        response = s3_client.get_object(
                            Bucket=bucket,
                            Key=state.s3_key
                        )
                        content_sample = response['Body'].read()
                        break
                
                # Try to extract text from PDF if applicable
                if content_type == 'application/pdf' or state.s3_key.lower().endswith('.pdf'):
                    try:
                        import io
                        import PyPDF2
                        pdf_file = io.BytesIO(content_sample)
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        
                        # Extract text from available pages
                        temp_text = b""
                        for page_num in range(min(len(pdf_reader.pages), 3)):  # Check first 3 pages max
                            try:
                                page = pdf_reader.pages[page_num]
                                text = page.extract_text()
                                temp_text += text.encode('utf-8', errors='ignore')
                            except:
                                continue
                        
                        if temp_text:
                            text_content = temp_text
                    except:
                        # PDF parsing failed, use raw bytes
                        text_content = content_sample
                else:
                    text_content = content_sample
                
                # Check for strong signals
                strong_signal_count = 0
                for indicator in STRONG_INDICATORS:
                    if indicator in text_content.upper():
                        strong_signal_count += 1
                
                # Early exit if we found enough strong signals
                if strong_signal_count >= confidence_threshold:
                    print(f"Early detection: Found {strong_signal_count} strong CMS-1500 signals in first {len(content_sample)} bytes")
                    break
                
                # Also exit if we've read enough and found some signals
                if len(content_sample) >= 131072 and strong_signal_count >= 2:
                    print(f"Partial detection: Found {strong_signal_count} signals in {len(content_sample)} bytes")
                    break
                
                # Exit if file is fully read
                if len(content_sample) >= file_size:
                    break
            
            # Use text content if successfully extracted, otherwise use raw bytes
            final_content = text_content if text_content else content_sample
            
            return {
                "content_sample": final_content,
                "content_type": content_type,
                "file_size": file_size,
                "bytes_read": len(content_sample),
                "early_detection": strong_signal_count >= confidence_threshold
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: s3://{bucket}/{state.s3_key}")
            elif error_code == 'AccessDenied':
                raise PermissionError(f"Access denied: s3://{bucket}/{state.s3_key}")
            else:
                raise


async def classify_document(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Classify document type based on content indicators."""
    
    # Check if early detection already found strong signals
    if hasattr(state, 'early_detection') and state.early_detection:
        # Fast path: already detected as CMS-1500 with high confidence
        return {
            "document_type": DocumentType.CMS_1500.value,
            "processor": ProcessorType.TEXTRACT.value,
            "confidence": 0.95,  # High confidence from early detection
            "indicators_found": ["CMS-1500", "FORM 1500", "HEALTH INSURANCE CLAIM"],
            "classification_reason": f"Early detection: Strong CMS-1500 signals found in first {getattr(state, 'bytes_read', 0)} bytes"
        }
    
    # CMS-1500 specific indicators (expanded)
    CMS_INDICATORS = [
        b"CMS-1500",
        b"CMS 1500",
        b"FORM 1500",  # Added for newer forms
        b"HEALTH INSURANCE CLAIM FORM",
        b"APPROVED OMB-0938-1197",  # Current OMB number
        b"APPROVED OMB-0938",  # Generic OMB pattern
        b"PICA",
        b"PATIENT'S NAME",
        b"INSURED'S I.D. NUMBER",
        b"1A. INSURED'S I.D. NUMBER",  # Field 1A specific
        b"PATIENT'S BIRTH DATE",
        b"INSURED'S NAME",
        b"PATIENT'S ADDRESS",
        b"DIAGNOSIS OR NATURE OF ILLNESS OR INJURY",
        b"PROCEDURES, SERVICES, OR SUPPLIES",
        b"FEDERAL TAX I.D. NUMBER",
        b"PATIENT'S ACCOUNT NO",
        b"TOTAL CHARGE",
        b"AMOUNT PAID",
        b"NPI",
        b"24A",  # Service line markers
        b"24B",
        b"24J",
        b"NUCC"  # National Uniform Claim Committee
    ]
    
    # HCFA-1500 indicators (older version)
    HCFA_INDICATORS = [
        b"HCFA-1500",
        b"HCFA 1500",
        b"APPROVED OMB-0938-0999",
        b"CHAMPUS",
        b"CHAMPVA",
        b"GROUP HEALTH PLAN",
        b"FECA",
        b"BLACK LUNG"
    ]
    
    # Convert content to bytes if string
    content = state.content_sample
    if isinstance(content, str):
        content = content.encode('utf-8', errors='ignore')
    
    # Search for indicators
    cms_found = []
    hcfa_found = []
    
    for indicator in CMS_INDICATORS:
        if indicator in content.upper():
            cms_found.append(indicator.decode('utf-8', errors='ignore'))
    
    for indicator in HCFA_INDICATORS:
        if indicator in content.upper():
            hcfa_found.append(indicator.decode('utf-8', errors='ignore'))
    
    # Determine document type
    threshold = runtime.context.get("confidence_threshold", 0.7)
    
    if len(cms_found) >= 3:
        document_type = DocumentType.CMS_1500.value
        confidence = min(1.0, len(cms_found) / 10.0)
        indicators = cms_found
        reason = f"Found {len(cms_found)} CMS-1500 indicators"
    elif len(hcfa_found) >= 2:
        document_type = DocumentType.HCFA_1500.value
        confidence = min(1.0, len(hcfa_found) / 8.0)
        indicators = hcfa_found
        reason = f"Found {len(hcfa_found)} HCFA-1500 indicators"
    else:
        document_type = DocumentType.UNKNOWN.value
        confidence = 0.0
        indicators = []
        reason = "No clear document type indicators found"
    
    # Select processor based on confidence
    if document_type != DocumentType.UNKNOWN.value and confidence >= threshold:
        processor = ProcessorType.TEXTRACT.value
    else:
        processor = ProcessorType.OPENAI.value
    
    return {
        "document_type": document_type,
        "processor": processor,
        "confidence": confidence,
        "indicators_found": indicators[:5],  # Limit to first 5 for response
        "classification_reason": reason
    }


# Define the graph
graph = (
    StateGraph(State, context_schema=Context)
    .add_node("download_sample", download_sample)
    .add_node("classify_document", classify_document)
    .add_edge("__start__", "download_sample")
    .add_edge("download_sample", "classify_document")
    .compile(name="Document Classifier Agent")
)