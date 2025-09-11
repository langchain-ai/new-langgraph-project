#!/usr/bin/env python3
import boto3
import os
from pathlib import Path

s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

bucket_name = 'medical-documents'

try:
    s3_client.create_bucket(Bucket=bucket_name)
    print(f"✓ Created bucket: {bucket_name}")
except s3_client.exceptions.BucketAlreadyExists:
    print(f"✓ Bucket already exists: {bucket_name}")
except Exception as e:
    if 'BucketAlreadyOwnedByYou' in str(e):
        print(f"✓ Bucket already owned: {bucket_name}")
    else:
        print(f"Error creating bucket: {e}")

pdf_files = [
    'tests/test-files/2_page_with_back.pdf',
    'tests/test-files/misaligned.pdf',
    'tests/test-files/black_and_white.pdf',
    'tests/test-files/with_watermark.pdf',
    'tests/test-files/multiline_provider_id.pdf'
]

uploaded_files = []

for pdf_file in pdf_files:
    if os.path.exists(pdf_file):
        file_name = os.path.basename(pdf_file)
        try:
            with open(pdf_file, 'rb') as file:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=file_name,
                    Body=file.read()
                )
            s3_url = f"http://localhost:4566/{bucket_name}/{file_name}"
            uploaded_files.append(s3_url)
            print(f"✓ Uploaded: {file_name}")
            print(f"  URL: {s3_url}")
        except Exception as e:
            print(f"✗ Failed to upload {file_name}: {e}")
    else:
        print(f"✗ File not found: {pdf_file}")

print("\n=== 所有已上传文件的 S3 地址 ===")
for url in uploaded_files:
    print(url)