"""LangGraph medical data extractor agent.

Extracts structured data from medical documents using Textract or OpenAI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, TypedDict, List, Optional
from enum import Enum
import os
import logging
import boto3

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)


class ProcessorType(str, Enum):
    """Available processors."""
    TEXTRACT = "textract"
    OPENAI = "openai"


class Context(TypedDict):
    """Context parameters for the data extractor.
    
    Set these when creating assistants OR when invoking the graph.
    """
    s3_bucket: str
    aws_region: str
    openai_api_key: Optional[str]
    enable_validation: bool


@dataclass
class State:
    """State for medical data extraction.
    
    Tracks the document through the extraction pipeline.
    """
    # Input
    s3_key: str = ""
    document_type: str = ""
    processor: str = ProcessorType.TEXTRACT.value
    
    # Processing
    raw_content: bytes = b""
    textract_response: Dict[str, Any] = field(default_factory=dict)
    openai_response: Dict[str, Any] = field(default_factory=dict)
    
    # Extracted data (CMS-1500 fields)
    patient_name: str = ""
    patient_dob: str = ""
    patient_sex: str = ""
    insured_name: str = ""
    insured_id: str = ""
    patient_address: str = ""
    patient_city: str = ""
    patient_state: str = ""
    patient_zip: str = ""
    patient_phone: str = ""
    
    # Insurance information
    insurance_plan_name: str = ""
    is_medicare: bool = False
    is_medicaid: bool = False
    is_tricare: bool = False
    is_champva: bool = False
    is_group_health: bool = False
    is_feca: bool = False
    is_other: bool = False
    
    # Medical information
    diagnosis_codes: List[str] = field(default_factory=list)
    procedure_codes: List[str] = field(default_factory=list)
    service_dates: List[str] = field(default_factory=list)
    place_of_service: str = ""
    
    # Billing information
    total_charge: float = 0.0
    amount_paid: float = 0.0
    balance_due: float = 0.0
    
    # Provider information
    provider_name: str = ""
    provider_npi: str = ""
    provider_tax_id: str = ""
    provider_address: str = ""
    provider_city: str = ""
    provider_state: str = ""
    provider_zip: str = ""
    provider_phone: str = ""
    
    # Validation
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)
    completeness_score: float = 0.0


async def download_document(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Download full document from S3."""
    import os
    import boto3
    from botocore.exceptions import ClientError
    
    bucket = runtime.context.get("s3_bucket", "medical-documents")
    region = runtime.context.get("aws_region", "us-east-1")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    
    s3_client = boto3.client(
        's3', 
        region_name=region,
        endpoint_url=endpoint_url
    )
    
    try:
        response = s3_client.get_object(Bucket=bucket, Key=state.s3_key)
        raw_content = response['Body'].read()
        
        return {"raw_content": raw_content}
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            raise FileNotFoundError(f"File not found: s3://{bucket}/{state.s3_key}")
        elif error_code == 'AccessDenied':
            raise PermissionError(f"Access denied: s3://{bucket}/{state.s3_key}")
        else:
            raise


async def process_with_textract(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Process document using AWS Textract."""
    if state.processor != ProcessorType.TEXTRACT.value:
        return {}
    
    import boto3
    from botocore.exceptions import ClientError
    
    bucket = runtime.context.get("s3_bucket", "medical-documents")
    region = runtime.context.get("aws_region", "us-east-1")
    
    textract_client = boto3.client('textract', region_name=region)
    
    try:
        # Call Textract analyze_document API
        response = textract_client.analyze_document(
            Document={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': state.s3_key
                }
            },
            FeatureTypes=['FORMS', 'TABLES']
        )
        
        return {"textract_response": response}
        
    except ClientError as e:
        # If Textract fails, fallback to OpenAI
        return {
            "processor": ProcessorType.OPENAI.value,
            "textract_response": {"error": str(e)}
        }


async def process_with_openai(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Process document using OpenAI GPT-4o with intelligent page-by-page processing."""
    if state.processor != ProcessorType.OPENAI.value:
        return {}
    
    import base64
    import json
    from openai import OpenAI
    import io
    import pdf2image
    import PyPDF2
    
    # Get API key from environment or context
    api_key = runtime.context.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OpenAI API key is required. Please set OPENAI_API_KEY environment variable.")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Get document metadata from S3
        bucket = runtime.context.get("s3_bucket", "medical-documents")
        region = runtime.context.get("aws_region", "us-east-1")
        endpoint_url = os.getenv("AWS_ENDPOINT_URL")
        
        s3_client = boto3.client(
            's3',
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test")
        )
        
        # Get file metadata first
        head_response = s3_client.head_object(Bucket=bucket, Key=state.s3_key)
        file_size = head_response['ContentLength']
        
        # Intelligent download strategy
        if file_size < 500000:  # Less than 500KB - download full file
            logger.info(f"Small file ({file_size} bytes), downloading full document")
            response = s3_client.get_object(Bucket=bucket, Key=state.s3_key)
            pdf_content = response['Body'].read()
            download_strategy = "full"
        else:
            # Large file - download progressively
            logger.info(f"Large file ({file_size} bytes), using progressive download")
            
            # Download first 1MB for initial pages
            range_header = 'bytes=0-1048575'
            response = s3_client.get_object(
                Bucket=bucket, 
                Key=state.s3_key,
                Range=range_header
            )
            pdf_content = response['Body'].read()
            download_strategy = "partial"
        
        # Determine number of pages to process
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        total_pages = len(pdf_reader.pages)
        
        # Quick detection with low resolution first page
        logger.info("Performing quick CMS-1500 detection...")
        quick_images = pdf2image.convert_from_bytes(
            pdf_content, 
            dpi=100,  # Low resolution for quick check
            first_page=1, 
            last_page=1
        )
        
        # Quick detection prompt
        quick_buffered = io.BytesIO()
        quick_images[0].save(quick_buffered, format="PNG")
        quick_img_base64 = base64.b64encode(quick_buffered.getvalue()).decode()
        
        quick_response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use faster mini model for quick check
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Is this a CMS-1500 or HCFA-1500 medical claim form? Reply with JSON: {\"is_cms1500\": true/false, \"confidence\": 0-1, \"needs_page_2\": true/false}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{quick_img_base64}", "detail": "low"}}
                ]
            }],
            temperature=0,
            max_tokens=100,
            response_format={"type": "json_object"}
        )
        
        quick_result = json.loads(quick_response.choices[0].message.content)
        logger.info(f"Quick detection result: {quick_result}")
        
        # Determine pages to process based on quick detection
        if not quick_result.get("is_cms1500", False):
            logger.info("Not a CMS-1500 form, skipping detailed extraction")
            return {
                "openai_response": {
                    "model": "gpt-4o",
                    "not_cms1500": True,
                    "quick_detection": quick_result
                }
            }
        
        # Determine how many pages to process
        if quick_result.get("needs_page_2", False) and total_pages > 1:
            pages_to_process = min(2, total_pages)
            logger.info(f"Processing {pages_to_process} pages (form continues on page 2)")
        else:
            pages_to_process = 1
            logger.info("Processing single page CMS-1500")
        
        # If we need more pages and only downloaded partial, get the rest
        if pages_to_process > 1 and download_strategy == "partial":
            # Download up to 2MB for 2-page form
            response = s3_client.get_object(
                Bucket=bucket,
                Key=state.s3_key,
                Range='bytes=0-2097151'
            )
            pdf_content = response['Body'].read()
        
        # Convert required pages to high quality images
        logger.info(f"Converting {pages_to_process} pages at high resolution...")
        images = pdf2image.convert_from_bytes(
            pdf_content, 
            dpi=200,  # Standard resolution for extraction
            first_page=1, 
            last_page=pages_to_process
        )
        
        # Combine images to base64
        image_contents = []
        for i, img in enumerate(images):
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
        
        # Create prompt for GPT-4o
        prompt = """You are a medical claims processing expert. Analyze this CMS-1500/HCFA-1500 insurance claim form and extract all relevant information.

Please extract and return the following information in JSON format:
{
    "patient": {
        "name": "full name",
        "dob": "YYYY-MM-DD format",
        "sex": "M/F",
        "address": "street address",
        "city": "city",
        "state": "state",
        "zip": "zip code",
        "phone": "phone number"
    },
    "insurance": {
        "insured_id": "insurance ID number",
        "insured_name": "insured person's name",
        "plan_name": "insurance plan/company name",
        "group_number": "group number if available"
    },
    "diagnoses": ["list of diagnosis codes (ICD-10)"],
    "procedures": [
        {
            "code": "CPT/HCPCS code",
            "description": "procedure description",
            "date": "service date",
            "charge": "charge amount as number"
        }
    ],
    "provider": {
        "name": "provider/clinic name",
        "npi": "NPI number",
        "tax_id": "tax ID",
        "address": "provider address",
        "phone": "provider phone"
    },
    "financial": {
        "total_charge": "total charge as number",
        "amount_paid": "amount paid as number",
        "balance_due": "balance due as number"
    }
}

If any field is not clearly visible or not present, use null for that field.
"""
        
        # Prepare message content with text prompt and all images
        message_content = [{"type": "text", "text": prompt}] + image_contents
        
        # Call GPT-4o for detailed extraction
        logger.info("Calling GPT-4o for detailed data extraction...")
        response = client.chat.completions.create(
            model="gpt-4o",  # Using GPT-4o for better performance
            messages=[{
                "role": "user",
                "content": message_content
            }],
            temperature=0.1,  # Low temperature for consistent extraction
            max_tokens=2000,
            response_format={"type": "json_object"}  # Ensure JSON response
        )
        
        # Parse the response
        extracted_data = json.loads(response.choices[0].message.content)
        
        # Calculate cost savings
        bytes_downloaded = len(pdf_content)
        bytes_saved = max(0, file_size - bytes_downloaded)
        savings_percentage = (bytes_saved / file_size * 100) if file_size > 0 else 0
        
        logger.info(f"Extraction complete. Downloaded {bytes_downloaded}/{file_size} bytes ({100-savings_percentage:.1f}% of file)")
        
        return {
            "openai_response": {
                "model": "gpt-4o",
                "extracted_data": extracted_data,
                "pages_processed": pages_to_process,
                "total_pages": total_pages,
                "quick_detection": quick_result,
                "optimization_stats": {
                    "file_size": file_size,
                    "bytes_downloaded": bytes_downloaded,
                    "bytes_saved": bytes_saved,
                    "savings_percentage": savings_percentage,
                    "download_strategy": download_strategy
                },
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "quick_check_tokens": quick_response.usage.total_tokens
                }
            }
        }
        
    except Exception as e:
        # Fallback to mock data on error
        logger.error(f"OpenAI processing error: {str(e)}")
        return {
            "openai_response": {
                "model": "gpt-4o",
                "error": str(e),
                "note": "Error occurred - returning mock data",
                "mock_data": True
            }
        }


async def extract_fields(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Extract structured fields from processor response."""
    
    extracted = {}
    
    if state.textract_response and "Blocks" in state.textract_response:
        # Parse Textract response
        extracted = _parse_textract_response(state.textract_response)
    elif state.openai_response:
        # Check if we have real extracted data from GPT-4o
        if "extracted_data" in state.openai_response:
            # Parse GPT-4o response
            data = state.openai_response["extracted_data"]
            
            # Extract patient information
            patient = data.get("patient", {})
            extracted["patient_name"] = patient.get("name", "")
            extracted["patient_dob"] = patient.get("dob", "")
            extracted["patient_sex"] = patient.get("sex", "")
            extracted["patient_address"] = patient.get("address", "")
            extracted["patient_city"] = patient.get("city", "")
            extracted["patient_state"] = patient.get("state", "")
            extracted["patient_zip"] = patient.get("zip", "")
            extracted["patient_phone"] = patient.get("phone", "")
            
            # Extract insurance information
            insurance = data.get("insurance", {})
            extracted["insured_id"] = insurance.get("insured_id", "")
            extracted["insured_name"] = insurance.get("insured_name", "")
            extracted["insurance_plan_name"] = insurance.get("plan_name", "")
            
            # Extract diagnoses
            extracted["diagnosis_codes"] = data.get("diagnoses", [])
            
            # Extract procedures
            procedures = data.get("procedures", [])
            if procedures:
                extracted["procedure_codes"] = [p.get("code", "") for p in procedures if p.get("code")]
                extracted["service_dates"] = [p.get("date", "") for p in procedures if p.get("date")]
                # Sum up charges from procedures
                total_charge = sum(float(p.get("charge", 0)) for p in procedures)
                extracted["total_charge"] = total_charge
            
            # Extract provider information
            provider = data.get("provider", {})
            extracted["provider_name"] = provider.get("name", "")
            extracted["provider_npi"] = provider.get("npi", "")
            extracted["provider_tax_id"] = provider.get("tax_id", "")
            extracted["provider_address"] = provider.get("address", "")
            extracted["provider_phone"] = provider.get("phone", "")
            
            # Extract financial information
            financial = data.get("financial", {})
            extracted["total_charge"] = float(financial.get("total_charge", extracted.get("total_charge", 0)))
            extracted["amount_paid"] = float(financial.get("amount_paid", 0))
            extracted["balance_due"] = float(financial.get("balance_due", 0))
            
        else:
            # No OpenAI response available
            extracted = {
                "error": "No data extracted - OpenAI processing may have failed"
            }
    
    return extracted


async def validate_data(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Validate extracted data."""
    if not runtime.context.get("enable_validation", True):
        return {"is_valid": True}
    
    errors = []
    
    # Required field validation
    if not state.patient_name:
        errors.append("Missing patient name")
    if not state.insured_id:
        errors.append("Missing insurance ID")
    if not state.diagnosis_codes:
        errors.append("No diagnosis codes found")
    
    # Calculate completeness
    required_fields = [
        'patient_name', 'patient_dob', 'insured_id',
        'diagnosis_codes', 'total_charge', 'provider_npi'
    ]
    
    filled = sum(1 for field in required_fields if getattr(state, field, None))
    completeness = (filled / len(required_fields)) * 100
    
    return {
        "is_valid": len(errors) == 0,
        "validation_errors": errors,
        "completeness_score": completeness
    }


def _parse_textract_response(response: Dict) -> Dict[str, Any]:
    """Parse Textract response to extract CMS-1500 fields."""
    extracted = {}
    
    # Create block map
    block_map = {}
    key_map = {}
    value_map = {}
    
    for block in response.get('Blocks', []):
        block_map[block['Id']] = block
        
        if block['BlockType'] == 'KEY_VALUE_SET':
            if 'KEY' in block.get('EntityTypes', []):
                key_map[block['Id']] = block
            else:
                value_map[block['Id']] = block
    
    # Extract key-value pairs
    for key_block in key_map.values():
        value_block = _find_value_block(key_block, value_map)
        if value_block:
            key_text = _get_text(key_block, block_map)
            value_text = _get_text(value_block, block_map)
            
            if key_text and value_text:
                # Map to specific fields
                _map_to_cms_fields(key_text.upper(), value_text, extracted)
    
    return extracted


def _find_value_block(key_block: Dict, value_map: Dict) -> Optional[Dict]:
    """Find the value block associated with a key block."""
    for relationship in key_block.get('Relationships', []):
        if relationship['Type'] == 'VALUE':
            for value_id in relationship['Ids']:
                if value_id in value_map:
                    return value_map[value_id]
    return None


def _get_text(block: Dict, block_map: Dict) -> str:
    """Extract text from a block."""
    text = ''
    if 'Relationships' in block:
        for relationship in block['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    child_block = block_map.get(child_id)
                    if child_block and child_block['BlockType'] == 'WORD':
                        text += child_block.get('Text', '') + ' '
    return text.strip()


def _map_to_cms_fields(key: str, value: str, extracted: Dict):
    """Map extracted key-value pairs to CMS-1500 fields."""
    # Patient information
    if any(term in key for term in ["PATIENT'S NAME", "PATIENT NAME", "2."]):
        extracted['patient_name'] = value
    elif any(term in key for term in ["BIRTH DATE", "DOB", "3."]):
        extracted['patient_dob'] = value
    elif "SEX" in key or "4." in key:
        extracted['patient_sex'] = value
    elif any(term in key for term in ["PATIENT'S ADDRESS", "5."]):
        extracted['patient_address'] = value
    elif "CITY" in key and "PATIENT" in key:
        extracted['patient_city'] = value
    elif "STATE" in key and "PATIENT" in key:
        extracted['patient_state'] = value
    elif "ZIP" in key and "PATIENT" in key:
        extracted['patient_zip'] = value
    elif "TELEPHONE" in key and "PATIENT" in key:
        extracted['patient_phone'] = value
    
    # Insurance information
    elif any(term in key for term in ["INSURED'S I.D.", "INSURANCE ID", "MEMBER ID", "1A."]):
        extracted['insured_id'] = value
    elif any(term in key for term in ["INSURED'S NAME", "4."]):
        extracted['insured_name'] = value
    elif "INSURANCE PLAN NAME" in key or "11C." in key:
        extracted['insurance_plan_name'] = value
    
    # Diagnosis codes (Box 21)
    elif "DIAGNOSIS" in key and "CODE" in key:
        codes = [part.strip() for part in value.split() if len(part) > 2]
        extracted['diagnosis_codes'] = codes
    
    # Procedure codes (Box 24D)
    elif "CPT" in key or "PROCEDURE" in key:
        codes = [part.strip() for part in value.split() if len(part) > 2]
        extracted['procedure_codes'] = codes
    
    # Financial information
    elif any(term in key for term in ["TOTAL CHARGE", "28."]):
        try:
            charge_str = value.replace('$', '').replace(',', '').strip()
            extracted['total_charge'] = float(charge_str)
        except ValueError:
            pass
    elif any(term in key for term in ["AMOUNT PAID", "29."]):
        try:
            paid_str = value.replace('$', '').replace(',', '').strip()
            extracted['amount_paid'] = float(paid_str)
        except ValueError:
            pass
    elif "BALANCE" in key or "30." in key:
        try:
            balance_str = value.replace('$', '').replace(',', '').strip()
            extracted['balance_due'] = float(balance_str)
        except ValueError:
            pass
    
    # Provider information
    elif "PROVIDER NAME" in key or "33." in key:
        extracted['provider_name'] = value
    elif "NPI" in key and "PROVIDER" in key:
        extracted['provider_npi'] = value
    elif "TAX ID" in key or "FEDERAL TAX" in key or "25." in key:
        extracted['provider_tax_id'] = value


# Define the graph
graph = (
    StateGraph(State, context_schema=Context)
    .add_node("download_document", download_document)
    .add_node("process_with_textract", process_with_textract)
    .add_node("process_with_openai", process_with_openai)
    .add_node("extract_fields", extract_fields)
    .add_node("validate_data", validate_data)
    .add_edge("__start__", "download_document")
    .add_edge("download_document", "process_with_textract")
    .add_edge("process_with_textract", "process_with_openai")
    .add_edge("process_with_openai", "extract_fields")
    .add_edge("extract_fields", "validate_data")
    .compile(name="Medical Data Extractor Agent")
)