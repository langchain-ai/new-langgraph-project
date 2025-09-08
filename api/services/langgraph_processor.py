"""Document processing service using LangGraph agents."""

import os
import sys
import logging
import asyncio
from typing import Dict, Any

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '../../')
sys.path.insert(0, project_root)

from agents.document_classifier.graph import graph as classifier_graph
from agents.medical_data_extractor.graph import graph as extractor_graph
from common.common.schemas import ExtractedData, ValidationResult

logger = logging.getLogger(__name__)


class LangGraphProcessor:
    """Document processor using LangGraph agents."""
    
    def __init__(self, s3_bucket: str = None, aws_region: str = 'us-east-1'):
        """
        Initialize the processor.
        
        Args:
            s3_bucket: Default S3 bucket
            aws_region: AWS region
        """
        self.s3_bucket = s3_bucket or os.getenv("S3_BUCKET", "medical-claims-documents")
        self.aws_region = aws_region
        
        # Default context for agents
        self.classifier_context = {
            "s3_bucket": self.s3_bucket,
            "aws_region": self.aws_region,
            "confidence_threshold": 0.7
        }
        
        self.extractor_context = {
            "s3_bucket": self.s3_bucket,
            "aws_region": self.aws_region,
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "enable_validation": True
        }
    
    async def process_document(self, s3_key: str, bucket: str = None) -> Dict[str, Any]:
        """
        Process a document using LangGraph agents.
        
        Args:
            s3_key: S3 object key
            bucket: S3 bucket (uses default if not provided)
            
        Returns:
            Processing results dictionary
        """
        try:
            # Update context with specific bucket if provided
            if bucket:
                self.classifier_context["s3_bucket"] = bucket
                self.extractor_context["s3_bucket"] = bucket
            
            # Step 1: Classify document
            logger.info(f"Classifying document: {s3_key}")
            
            classifier_state = {
                "s3_key": s3_key
            }
            
            classification_result = await classifier_graph.ainvoke(
                classifier_state,
                context=self.classifier_context
            )
            
            logger.info(f"Document classified as: {classification_result['document_type']} "
                       f"with confidence: {classification_result['confidence']}")
            
            # Step 2: Extract data
            logger.info(f"Extracting data using: {classification_result['processor']}")
            
            extractor_state = {
                "s3_key": s3_key,
                "document_type": classification_result["document_type"],
                "processor": classification_result["processor"]
            }
            
            extraction_result = await extractor_graph.ainvoke(
                extractor_state,
                context=self.extractor_context
            )
            
            # Step 3: Format response
            extracted_data = ExtractedData(
                raw_data={
                    "textract_response": extraction_result.get("textract_response", {}),
                    "openai_response": extraction_result.get("openai_response", {})
                },
                patient_name=extraction_result.get("patient_name"),
                patient_dob=extraction_result.get("patient_dob"),
                insurance_id=extraction_result.get("insured_id"),
                diagnosis_codes=extraction_result.get("diagnosis_codes", []),
                procedure_codes=extraction_result.get("procedure_codes", []),
                total_charge=extraction_result.get("total_charge")
            )
            
            validation = ValidationResult(
                is_valid=extraction_result.get("is_valid", False),
                completeness=extraction_result.get("completeness_score", 0.0),
                issues=[{"field": "validation", "issue": err} 
                       for err in extraction_result.get("validation_errors", [])],
                warnings=[]
            )
            
            return {
                'classification': {
                    'document_type': classification_result["document_type"],
                    'recommended_processor': classification_result["processor"],
                    'confidence': classification_result["confidence"],
                    'reason': classification_result.get("classification_reason", ""),
                    'indicators_found': classification_result.get("indicators_found", [])
                },
                'file_info': {
                    'size': classification_result.get("file_size", 0),
                    'content_type': classification_result.get("content_type", "")
                },
                'extracted_data': extracted_data,
                'validation': validation
            }
            
        except Exception as e:
            logger.error(f"Error processing document {s3_key}: {str(e)}")
            raise
    
    def process_document_sync(self, s3_key: str, bucket: str = None) -> Dict[str, Any]:
        """
        Synchronous wrapper for process_document.
        
        Args:
            s3_key: S3 object key
            bucket: S3 bucket (uses default if not provided)
            
        Returns:
            Processing results dictionary
        """
        # Use asyncio to run in the current event loop if it exists
        try:
            loop = asyncio.get_running_loop()
            # If we're already in a loop, create a task
            task = loop.create_task(self.process_document(s3_key, bucket))
            return loop.run_until_complete(task)
        except RuntimeError:
            # No running loop, create a new one
            return asyncio.run(self.process_document(s3_key, bucket))