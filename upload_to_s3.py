import boto3
import os

# Configure S3 client for LocalStack
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

# Upload file
file_path = 'documents/2_pagers.pdf'
bucket = 'medical-claims-documents'
key = 'documents/2_pagers.pdf'

try:
    s3_client.upload_file(file_path, bucket, key)
    print(f"Successfully uploaded {file_path} to s3://{bucket}/{key}")
except Exception as e:
    print(f"Upload failed: {e}")
