"""Common schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


class ProcessRequest(BaseModel):
    """Request model for document processing."""
    s3_key: str = Field(..., description="S3 object key of the document to process")
    bucket: Optional[str] = Field(None, description="S3 bucket name (optional, uses default if not provided)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "s3_key": "uploads/2024/01/claim_form_12345.pdf",
                "bucket": "medical-claims-documents"
            }
        }


class ProcessingInfo(BaseModel):
    """Processing metadata."""
    document_type: str = Field(..., description="Detected document type")
    processor_used: str = Field(..., description="Processor used (textract or openai)")
    confidence_score: float = Field(..., description="Classification confidence score")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    classification_reason: str = Field(..., description="Reason for classification decision")
    indicators_found: List[str] = Field(default_factory=list, description="List of CMS/HCFA indicators found")


class FileInfo(BaseModel):
    """File information."""
    s3_key: str = Field(..., description="S3 object key")
    s3_bucket: str = Field(..., description="S3 bucket name")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the file")
    s3_uri: str = Field(..., description="Full S3 URI")


class ValidationResult(BaseModel):
    """Data validation result."""
    is_valid: bool = Field(..., description="Whether the extracted data is valid")
    completeness: float = Field(..., description="Percentage of fields completed")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="List of validation issues")
    warnings: List[str] = Field(default_factory=list, description="List of warnings")


class ExtractedData(BaseModel):
    """Extracted data from the document."""
    # This is a simplified version - in production, this would be fully structured
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw extracted data")
    
    # CMS-1500 specific fields (subset for MVP)
    patient_name: Optional[str] = None
    patient_dob: Optional[str] = None
    insurance_id: Optional[str] = None
    diagnosis_codes: List[str] = Field(default_factory=list)
    procedure_codes: List[str] = Field(default_factory=list)
    total_charge: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_name": "John Doe",
                "patient_dob": "1980-01-01",
                "insurance_id": "123456789",
                "diagnosis_codes": ["E11.9", "I10"],
                "procedure_codes": ["99213", "80053"],
                "total_charge": 250.00
            }
        }


class ProcessResponse(BaseModel):
    """Response model for document processing."""
    status: str = Field(..., description="Processing status (success/failed)")
    processing_info: ProcessingInfo = Field(..., description="Processing metadata")
    file_info: FileInfo = Field(..., description="File information")
    extracted_data: Optional[ExtractedData] = Field(None, description="Extracted data from document")
    validation: Optional[ValidationResult] = Field(None, description="Validation results")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if processing failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "processing_info": {
                    "document_type": "cms1500_digital",
                    "processor_used": "textract",
                    "confidence_score": 0.95,
                    "processing_time_ms": 3500,
                    "classification_reason": "Found 15 CMS indicators. Digital form detected.",
                    "indicators_found": 15
                },
                "file_info": {
                    "s3_key": "uploads/2024/01/claim_form_12345.pdf",
                    "s3_bucket": "medical-claims-documents",
                    "file_size": 150000,
                    "content_type": "application/pdf",
                    "s3_uri": "s3://medical-claims-documents/uploads/2024/01/claim_form_12345.pdf"
                },
                "extracted_data": {
                    "patient_name": "John Doe",
                    "patient_dob": "1980-01-01",
                    "insurance_id": "123456789",
                    "diagnosis_codes": ["E11.9", "I10"],
                    "procedure_codes": ["99213", "80053"],
                    "total_charge": 250.00
                },
                "validation": {
                    "is_valid": True,
                    "completeness": 85.5,
                    "issues": [],
                    "warnings": []
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    status: str = Field(default="failed", description="Status (always 'failed' for errors)")
    error: Dict[str, Any] = Field(..., description="Error details")
    s3_key: Optional[str] = Field(None, description="S3 key of the document that failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "failed",
                "error": {
                    "code": "FILE_NOT_FOUND",
                    "message": "File not found in S3",
                    "details": "s3://medical-claims-documents/uploads/2024/01/missing.pdf"
                },
                "s3_key": "uploads/2024/01/missing.pdf",
                "timestamp": "2024-01-10T14:30:00Z"
            }
        }