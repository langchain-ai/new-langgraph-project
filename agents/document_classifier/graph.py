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
            
            # Download first 1MB for classification (or entire file if smaller)
            max_bytes = 1024 * 1024  # 1MB
            
            if file_size <= max_bytes:
                # Download entire file if it's small enough
                response = s3_client.get_object(
                    Bucket=bucket,
                    Key=state.s3_key
                )
            else:
                # Download only first 1MB for large files
                range_header = f'bytes=0-{max_bytes - 1}'
                response = s3_client.get_object(
                    Bucket=bucket,
                    Key=state.s3_key,
                    Range=range_header
                )
            
            content_sample = response['Body'].read()
            
            # If PDF, extract text content
            if content_type == 'application/pdf':
                try:
                    import io
                    import PyPDF2
                    pdf_file = io.BytesIO(content_sample)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    text_content = b""
                    for page_num in range(min(len(pdf_reader.pages), 10)):
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        text_content += text.encode('utf-8', errors='ignore')
                        if len(text_content) >= max_bytes:
                            text_content = text_content[:max_bytes]
                            break
                    if text_content:
                        content_sample = text_content
                except Exception:
                    # If PDF parsing fails, keep raw bytes
                    pass
            
            return {
                "content_sample": content_sample,
                "content_type": content_type,
                "file_size": file_size
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
    
    # CMS-1500 specific indicators
    CMS_INDICATORS = [
        b"CMS-1500",
        b"HEALTH INSURANCE CLAIM FORM",
        b"PICA",
        b"PATIENT'S NAME",
        b"INSURED'S I.D. NUMBER",
        b"PATIENT'S BIRTH DATE",
        b"INSURED'S NAME",
        b"PATIENT'S ADDRESS",
        b"DIAGNOSIS OR NATURE OF ILLNESS OR INJURY",
        b"PROCEDURES, SERVICES, OR SUPPLIES",
        b"FEDERAL TAX I.D. NUMBER",
        b"PATIENT'S ACCOUNT NO",
        b"TOTAL CHARGE",
        b"AMOUNT PAID",
        b"NPI"
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