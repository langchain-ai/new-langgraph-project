"""LangGraph medical data extractor agent.

Extracts structured data from medical documents using Textract or OpenAI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, TypedDict, List, Optional
from enum import Enum

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime


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
    import boto3
    from botocore.exceptions import ClientError
    
    bucket = runtime.context.get("s3_bucket", "medical-documents")
    region = runtime.context.get("aws_region", "us-east-1")
    
    s3_client = boto3.client('s3', region_name=region)
    
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
    """Process document using OpenAI GPT-4V."""
    if state.processor != ProcessorType.OPENAI.value:
        return {}
    
    # For MVP, return mock data
    # In production, this would call OpenAI API
    return {
        "openai_response": {
            "model": "gpt-4-vision",
            "note": "OpenAI integration pending - mock data for MVP"
        }
    }


async def extract_fields(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Extract structured fields from processor response."""
    
    extracted = {}
    
    if state.textract_response and "Blocks" in state.textract_response:
        # Parse Textract response
        extracted = _parse_textract_response(state.textract_response)
    elif state.openai_response:
        # Parse OpenAI response (mock for MVP)
        extracted = {
            "patient_name": "John Doe",
            "patient_dob": "1980-01-01",
            "insured_id": "MOCK123456",
            "diagnosis_codes": ["Z00.00"],
            "procedure_codes": ["99213"],
            "total_charge": 150.00
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