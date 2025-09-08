"""Main FastAPI application for medical claims processor."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import os
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our modules
import sys
# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '../')
sys.path.insert(0, project_root)

from common.common.schemas import ProcessRequest, ProcessResponse, ProcessingInfo, FileInfo, ErrorResponse
from api.services.langgraph_processor import LangGraphProcessor

# Initialize FastAPI app
app = FastAPI(
    title="Medical Claims Processor",
    description="API for processing medical claims documents (CMS-1500/HCFA-1500)",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processor
processor = LangGraphProcessor(
    s3_bucket=os.getenv("S3_BUCKET", "medical-claims-documents"),
    aws_region=os.getenv("AWS_REGION", "us-east-1")
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Medical Claims Processor API",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "process": "/api/v1/process",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "medical-claims-processor",
        "version": "1.0.0"
    }


@app.post("/api/v1/process", response_model=ProcessResponse)
async def process_document(request: ProcessRequest):
    """
    Process a medical claims document from S3.
    
    This endpoint performs the following steps:
    1. Downloads up to 1MB from S3 for classification
    2. Classifies the document type (CMS-1500, HCFA-1500, etc.)
    3. Processes the document using the appropriate method (Textract or OpenAI)
    4. Extracts and validates the data
    5. Returns structured JSON response
    
    Args:
        request: ProcessRequest with S3 key and optional bucket
        
    Returns:
        ProcessResponse with extracted data and metadata
        
    Raises:
        HTTPException: If file not found or processing fails
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing document: {request.s3_key}")
        
        # Process the document using async
        result = await processor.process_document(
            s3_key=request.s3_key,
            bucket=request.bucket
        )
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Build response
        response = ProcessResponse(
            status="success",
            processing_info=ProcessingInfo(
                document_type=result['classification']['document_type'],
                processor_used=result['classification']['recommended_processor'],
                confidence_score=result['classification']['confidence'],
                processing_time_ms=processing_time_ms,
                classification_reason=result['classification']['reason'],
                indicators_found=result['classification']['indicators_found']
            ),
            file_info=FileInfo(
                s3_key=request.s3_key,
                s3_bucket=request.bucket or processor.s3_bucket,
                file_size=result['file_info']['size'],
                content_type=result['file_info']['content_type'],
                s3_uri=f"s3://{request.bucket or processor.s3_bucket}/{request.s3_key}"
            ),
            extracted_data=result['extracted_data'],
            validation=result['validation']
        )
        
        logger.info(f"Successfully processed document in {processing_time_ms}ms")
        return response
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {request.s3_key}")
        raise HTTPException(
            status_code=404,
            detail={
                "status": "failed",
                "error": {
                    "code": "FILE_NOT_FOUND",
                    "message": str(e),
                    "s3_key": request.s3_key
                }
            }
        )
        
    except PermissionError as e:
        logger.error(f"Permission denied: {request.s3_key}")
        raise HTTPException(
            status_code=403,
            detail={
                "status": "failed",
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": str(e),
                    "s3_key": request.s3_key
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Processing failed for {request.s3_key}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "error": {
                    "code": "PROCESSING_ERROR",
                    "message": f"Document processing failed: {str(e)}",
                    "s3_key": request.s3_key
                }
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )