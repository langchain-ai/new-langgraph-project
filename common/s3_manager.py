"""S3 file management utilities."""

import boto3
from botocore.exceptions import ClientError
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class S3FileInfo:
    """S3 file metadata."""
    bucket: str
    key: str
    size: int
    content_type: str
    etag: str = ""
    last_modified: str = ""


class S3Manager:
    """S3 file manager for document processing."""
    
    def __init__(self, bucket_name: str = None, region: str = 'us-east-1'):
        """
        Initialize S3 manager.
        
        Args:
            bucket_name: S3 bucket name (can be overridden per operation)
            region: AWS region
        """
        self.s3_client = boto3.client('s3', region_name=region)
        self.default_bucket = bucket_name or 'medical-claims-documents'
        self.classification_sample_size = 1024 * 1024  # 1MB
        
    def get_file_info(self, s3_key: str, bucket: str = None) -> S3FileInfo:
        """
        Get file metadata without downloading content.
        
        Args:
            s3_key: S3 object key
            bucket: Bucket name (uses default if not provided)
            
        Returns:
            S3FileInfo object with metadata
            
        Raises:
            FileNotFoundError: If object doesn't exist
            PermissionError: If access is denied
        """
        bucket = bucket or self.default_bucket
        
        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=s3_key)
            
            return S3FileInfo(
                bucket=bucket,
                key=s3_key,
                size=response['ContentLength'],
                content_type=response.get('ContentType', 'application/octet-stream'),
                etag=response.get('ETag', '').strip('"'),
                last_modified=response.get('LastModified', '').isoformat() if response.get('LastModified') else ''
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404' or error_code == 'NoSuchKey':
                raise FileNotFoundError(f"File not found in S3: s3://{bucket}/{s3_key}")
            elif error_code == '403' or error_code == 'Forbidden':
                raise PermissionError(f"Access denied to S3 file: s3://{bucket}/{s3_key}")
            else:
                logger.error(f"Error accessing S3 file: {e}")
                raise
    
    def download_for_classification(self, s3_key: str, bucket: str = None) -> Tuple[bytes, S3FileInfo]:
        """
        Download file sample for classification (up to 1MB).
        
        Args:
            s3_key: S3 object key
            bucket: Bucket name (uses default if not provided)
            
        Returns:
            Tuple of (content_sample, file_info)
        """
        bucket = bucket or self.default_bucket
        
        # Get file info first
        file_info = self.get_file_info(s3_key, bucket)
        
        # Determine how much to download
        if file_info.size <= self.classification_sample_size:
            # Small file - download entire content
            logger.info(f"Downloading entire file for classification: {s3_key} ({file_info.size} bytes)")
            response = self.s3_client.get_object(Bucket=bucket, Key=s3_key)
            content = response['Body'].read()
        else:
            # Large file - download only first 1MB
            logger.info(f"Downloading first 1MB for classification: {s3_key} (total size: {file_info.size} bytes)")
            response = self.s3_client.get_object(
                Bucket=bucket,
                Key=s3_key,
                Range=f'bytes=0-{self.classification_sample_size - 1}'
            )
            content = response['Body'].read()
        
        return content, file_info
    
    def download_full_file(self, s3_key: str, bucket: str = None) -> bytes:
        """
        Download entire file content.
        
        Args:
            s3_key: S3 object key
            bucket: Bucket name (uses default if not provided)
            
        Returns:
            Complete file content as bytes
        """
        bucket = bucket or self.default_bucket
        
        logger.info(f"Downloading full file: s3://{bucket}/{s3_key}")
        
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=s3_key)
            content = response['Body'].read()
            logger.info(f"Downloaded {len(content)} bytes from {s3_key}")
            return content
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404' or error_code == 'NoSuchKey':
                raise FileNotFoundError(f"File not found in S3: s3://{bucket}/{s3_key}")
            else:
                logger.error(f"Error downloading S3 file: {e}")
                raise
    
    def get_textract_document_location(self, s3_key: str, bucket: str = None) -> Dict:
        """
        Get document location configuration for AWS Textract.
        
        Args:
            s3_key: S3 object key
            bucket: Bucket name (uses default if not provided)
            
        Returns:
            Dictionary with S3 configuration for Textract
        """
        bucket = bucket or self.default_bucket
        
        return {
            'S3Object': {
                'Bucket': bucket,
                'Name': s3_key
            }
        }
    
    def upload_file(self, content: bytes, s3_key: str, bucket: str = None, 
                    content_type: str = 'application/pdf', metadata: Dict = None) -> str:
        """
        Upload content to S3.
        
        Args:
            content: File content to upload
            s3_key: S3 object key
            bucket: Bucket name (uses default if not provided)
            content_type: MIME type of the content
            metadata: Optional metadata to attach
            
        Returns:
            S3 URI of uploaded file
        """
        bucket = bucket or self.default_bucket
        
        extra_args = {'ContentType': content_type}
        if metadata:
            extra_args['Metadata'] = metadata
        
        try:
            self.s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=content,
                **extra_args
            )
            
            s3_uri = f"s3://{bucket}/{s3_key}"
            logger.info(f"Uploaded file to {s3_uri}")
            return s3_uri
            
        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}")
            raise
    
    def file_exists(self, s3_key: str, bucket: str = None) -> bool:
        """
        Check if file exists in S3.
        
        Args:
            s3_key: S3 object key
            bucket: Bucket name (uses default if not provided)
            
        Returns:
            True if file exists, False otherwise
        """
        bucket = bucket or self.default_bucket
        
        try:
            self.s3_client.head_object(Bucket=bucket, Key=s3_key)
            return True
        except ClientError:
            return False