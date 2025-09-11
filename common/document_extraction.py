"""Document extraction utility for processing PDF files from S3.

This module provides utilities for:
- Loading PDF files from S3 directly into memory
- Splitting multi-page PDFs into individual pages
- Extracting text and images from PDFs
- All operations are performed in memory without disk I/O
"""

import io
import logging
from typing import List, Dict, Any, Optional, Tuple
import boto3
from botocore.exceptions import ClientError
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """Handles document extraction from S3 with in-memory processing."""
    
    def __init__(
        self,
        bucket_name: str,
        aws_region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None
    ):
        """
        Initialize the document extractor.
        
        Args:
            bucket_name: S3 bucket name
            aws_region: AWS region
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
            endpoint_url: Custom S3 endpoint URL (optional)
        """
        self.bucket_name = bucket_name
        self.aws_region = aws_region
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=endpoint_url
        )
    
    def get_pdf_from_s3(self, s3_key: str, max_bytes: Optional[int] = None) -> Tuple[bytes, Dict[str, Any]]:
        """
        Load PDF from S3 directly into memory.
        
        Args:
            s3_key: S3 object key
            max_bytes: Maximum bytes to download (None for full file)
            
        Returns:
            Tuple of (pdf_content, metadata)
            
        Raises:
            FileNotFoundError: If the S3 object doesn't exist
            PermissionError: If access is denied
        """
        try:
            # Get object metadata first
            logger.info(f"Getting metadata for s3://{self.bucket_name}/{s3_key}")
            head_response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            
            file_size = head_response['ContentLength']
            content_type = head_response.get('ContentType', 'application/pdf')
            last_modified = head_response.get('LastModified')
            
            metadata = {
                'file_size': file_size,
                'content_type': content_type,
                'last_modified': str(last_modified) if last_modified else None,
                'etag': head_response.get('ETag', '').strip('"')
            }
            
            # Determine download strategy
            if max_bytes and file_size > max_bytes:
                # Partial download
                logger.info(f"Downloading first {max_bytes} bytes of {file_size} total")
                range_header = f'bytes=0-{max_bytes-1}'
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Range=range_header
                )
                pdf_content = response['Body'].read()
                metadata['bytes_downloaded'] = len(pdf_content)
                metadata['partial_download'] = True
            else:
                # Full download
                logger.info(f"Downloading entire file ({file_size} bytes)")
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                pdf_content = response['Body'].read()
                metadata['bytes_downloaded'] = file_size
                metadata['partial_download'] = False
            
            # Calculate optimization stats
            metadata['bytes_saved'] = file_size - metadata['bytes_downloaded']
            metadata['savings_percentage'] = (
                (metadata['bytes_saved'] / file_size * 100) 
                if file_size > 0 else 0
            )
            
            logger.info(
                f"Downloaded {metadata['bytes_downloaded']:,} bytes "
                f"({100 - metadata['savings_percentage']:.1f}% of file)"
            )
            
            return pdf_content, metadata
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: s3://{self.bucket_name}/{s3_key}")
            elif error_code in ['AccessDenied', 'Forbidden']:
                raise PermissionError(f"Access denied: s3://{self.bucket_name}/{s3_key}")
            else:
                raise
    
    def split_pdf_pages(self, pdf_content: bytes, max_pages: Optional[int] = None) -> List[bytes]:
        """
        Split PDF into individual pages in memory.
        
        Args:
            pdf_content: PDF file content as bytes
            max_pages: Maximum number of pages to process (None for all)
            
        Returns:
            List of PDF bytes, one for each page
        """
        pages = []
        
        try:
            # Open PDF from memory
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            
            # Determine pages to process
            total_pages = pdf_document.page_count
            pages_to_process = min(max_pages, total_pages) if max_pages else total_pages
            
            logger.info(f"Splitting {pages_to_process} of {total_pages} pages")
            
            for page_num in range(pages_to_process):
                # Create new single-page PDF
                single_page_pdf = fitz.open()
                single_page_pdf.insert_pdf(
                    pdf_document,
                    from_page=page_num,
                    to_page=page_num
                )
                
                # Convert to bytes
                page_bytes = single_page_pdf.tobytes()
                pages.append(page_bytes)
                
                # Clean up
                single_page_pdf.close()
                
                logger.debug(f"Processed page {page_num + 1}/{pages_to_process}")
            
            pdf_document.close()
            
            logger.info(f"Successfully split {len(pages)} pages")
            
        except Exception as e:
            logger.error(f"Error splitting PDF: {str(e)}")
            raise
        
        return pages
    
    def extract_text_from_pdf(self, pdf_content: bytes, max_pages: Optional[int] = None) -> str:
        """
        Extract text content from PDF.
        
        Args:
            pdf_content: PDF file content as bytes
            max_pages: Maximum number of pages to extract text from
            
        Returns:
            Extracted text as string
        """
        text_content = []
        
        try:
            # Open PDF from memory
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            
            # Determine pages to process
            total_pages = pdf_document.page_count
            pages_to_process = min(max_pages, total_pages) if max_pages else total_pages
            
            logger.info(f"Extracting text from {pages_to_process} pages")
            
            for page_num in range(pages_to_process):
                page = pdf_document[page_num]
                text = page.get_text()
                text_content.append(text)
            
            pdf_document.close()
            
            return "\n\n".join(text_content)
            
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            raise
    
    def get_pdf_metadata(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Extract metadata from PDF.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary containing PDF metadata
        """
        try:
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            
            metadata = {
                'page_count': pdf_document.page_count,
                'title': pdf_document.metadata.get('title', ''),
                'author': pdf_document.metadata.get('author', ''),
                'subject': pdf_document.metadata.get('subject', ''),
                'keywords': pdf_document.metadata.get('keywords', ''),
                'creator': pdf_document.metadata.get('creator', ''),
                'producer': pdf_document.metadata.get('producer', ''),
                'creation_date': str(pdf_document.metadata.get('creationDate', '')),
                'modification_date': str(pdf_document.metadata.get('modDate', ''))
            }
            
            # Get page dimensions from first page
            if pdf_document.page_count > 0:
                first_page = pdf_document[0]
                rect = first_page.rect
                metadata['page_width'] = rect.width
                metadata['page_height'] = rect.height
            
            pdf_document.close()
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            raise
    
    def process_cms1500_document(self, s3_key: str) -> Dict[str, Any]:
        """
        Process a CMS-1500 document from S3.
        
        This is a high-level method that:
        1. Downloads the PDF from S3 (optimized for CMS-1500 size)
        2. Extracts metadata
        3. Splits pages if needed
        4. Returns structured data
        
        Args:
            s3_key: S3 object key for the PDF file
            
        Returns:
            Dictionary containing processed document data
        """
        try:
            # CMS-1500 forms are typically 1-2 pages, so limit download to 2MB
            max_download_bytes = 2 * 1024 * 1024  # 2MB
            
            # Get PDF from S3
            pdf_content, s3_metadata = self.get_pdf_from_s3(s3_key, max_download_bytes)
            
            # Extract PDF metadata
            pdf_metadata = self.get_pdf_metadata(pdf_content)
            
            # Split pages (CMS-1500 is max 2 pages)
            page_pdfs = self.split_pdf_pages(pdf_content, max_pages=2)
            
            # Extract text for detection
            text_content = self.extract_text_from_pdf(pdf_content, max_pages=2)
            
            # Check for CMS-1500 indicators
            cms_indicators = self._detect_cms1500_indicators(text_content)
            
            result = {
                's3_key': s3_key,
                's3_metadata': s3_metadata,
                'pdf_metadata': pdf_metadata,
                'page_count': len(page_pdfs),
                'page_pdfs': page_pdfs,
                'text_preview': text_content[:1000] if text_content else '',
                'is_cms1500': cms_indicators['is_cms1500'],
                'confidence': cms_indicators['confidence'],
                'indicators_found': cms_indicators['indicators']
            }
            
            logger.info(
                f"Processed {s3_key}: CMS-1500={cms_indicators['is_cms1500']}, "
                f"Confidence={cms_indicators['confidence']:.2f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing CMS-1500 document: {str(e)}")
            raise
    
    def _detect_cms1500_indicators(self, text: str) -> Dict[str, Any]:
        """
        Detect CMS-1500 form indicators in text.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Dictionary with detection results
        """
        # CMS-1500 specific indicators
        primary_indicators = [
            "CMS-1500", "CMS 1500", "FORM 1500",
            "HCFA-1500", "HCFA 1500",
            "HEALTH INSURANCE CLAIM FORM",
            "APPROVED OMB-0938", "NUCC"
        ]
        
        field_indicators = [
            "1a. INSURED'S I.D. NUMBER",
            "2. PATIENT'S NAME",
            "3. PATIENT'S BIRTH DATE",
            "14. DATE OF CURRENT",
            "17. NAME OF REFERRING",
            "21. DIAGNOSIS OR NATURE",
            "24A", "24B", "24C", "24D",
            "32. SERVICE FACILITY",
            "33. BILLING PROVIDER"
        ]
        
        text_upper = text.upper()
        
        # Count indicators found
        primary_found = []
        field_found = []
        
        for indicator in primary_indicators:
            if indicator.upper() in text_upper:
                primary_found.append(indicator)
        
        for indicator in field_indicators:
            if indicator.upper() in text_upper:
                field_found.append(indicator)
        
        # Calculate confidence
        total_found = len(primary_found) + len(field_found)
        
        if len(primary_found) >= 1 and len(field_found) >= 3:
            is_cms1500 = True
            confidence = min(1.0, 0.7 + (total_found * 0.03))
        elif len(primary_found) >= 2:
            is_cms1500 = True
            confidence = min(1.0, 0.6 + (total_found * 0.03))
        elif len(field_found) >= 5:
            is_cms1500 = True
            confidence = min(1.0, 0.5 + (len(field_found) * 0.05))
        else:
            is_cms1500 = False
            confidence = 0.0
        
        return {
            'is_cms1500': is_cms1500,
            'confidence': confidence,
            'indicators': primary_found + field_found
        }


# Convenience function for quick usage
def extract_cms1500_from_s3(
    s3_key: str,
    bucket_name: str,
    aws_region: str = "us-east-1",
    **kwargs
) -> Dict[str, Any]:
    """
    Quick function to extract CMS-1500 document from S3.
    
    Args:
        s3_key: S3 object key
        bucket_name: S3 bucket name
        aws_region: AWS region
        **kwargs: Additional arguments for DocumentExtractor
        
    Returns:
        Processed document data
    """
    extractor = DocumentExtractor(bucket_name, aws_region, **kwargs)
    return extractor.process_cms1500_document(s3_key)