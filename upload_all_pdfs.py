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
except Exception as e:
    if 'BucketAlreadyOwnedByYou' in str(e) or 'BucketAlreadyExists' in str(e):
        print(f"✓ Bucket already exists: {bucket_name}")
    else:
        print(f"Bucket creation info: {e}")

test_files_dir = 'tests/test-files'
pdf_files = []

for file_path in Path(test_files_dir).glob('*.pdf'):
    pdf_files.append(str(file_path))

print(f"\n找到 {len(pdf_files)} 个 PDF 文件准备上传:\n")

uploaded_files = []
failed_files = []

for pdf_file in sorted(pdf_files):
    file_name = os.path.basename(pdf_file)
    try:
        with open(pdf_file, 'rb') as file:
            file_content = file.read()
            file_size = len(file_content)
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=file_name,
                Body=file_content,
                ContentType='application/pdf'
            )
        
        head_response = s3_client.head_object(Bucket=bucket_name, Key=file_name)
        uploaded_size = head_response['ContentLength']
        
        if uploaded_size == file_size:
            s3_url = f"http://localhost:4566/{bucket_name}/{file_name}"
            uploaded_files.append(s3_url)
            print(f"✓ 成功上传: {file_name} ({file_size} bytes)")
            print(f"  URL: {s3_url}")
        else:
            failed_files.append(file_name)
            print(f"✗ 上传失败 (大小不匹配): {file_name}")
            
    except Exception as e:
        failed_files.append(file_name)
        print(f"✗ 上传失败: {file_name}")
        print(f"  错误: {e}")

print("\n=== 上传结果汇总 ===")
print(f"成功上传: {len(uploaded_files)} 个文件")
print(f"失败: {len(failed_files)} 个文件")

if uploaded_files:
    print("\n=== 所有成功上传文件的 S3 地址 ===")
    for url in uploaded_files:
        print(url)

if failed_files:
    print("\n=== 上传失败的文件 ===")
    for file in failed_files:
        print(f"  - {file}")

print("\n=== 验证 bucket 内容 ===")
response = s3_client.list_objects_v2(Bucket=bucket_name)
if 'Contents' in response:
    print(f"Bucket 中共有 {len(response['Contents'])} 个文件:")
    for obj in response['Contents']:
        print(f"  - {obj['Key']} ({obj['Size']} bytes)")