#!/usr/bin/env python3
import boto3

s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

bucket_name = 'medical-documents'

print(f"=== 检查 {bucket_name} bucket ===\n")

try:
    response = s3_client.list_buckets()
    buckets = [b['Name'] for b in response['Buckets']]
    print(f"现有的 buckets: {buckets}")
    
    if bucket_name in buckets:
        print(f"✓ {bucket_name} bucket 存在\n")
    else:
        print(f"✗ {bucket_name} bucket 不存在\n")
        
    print(f"=== {bucket_name} 中的文件 ===")
    
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    
    if 'Contents' in response:
        print(f"找到 {len(response['Contents'])} 个文件:\n")
        for obj in response['Contents']:
            file_key = obj['Key']
            file_size = obj['Size']
            print(f"  - {file_key} ({file_size} bytes)")
            
            head_response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
            print(f"    Content-Type: {head_response.get('ContentType', 'N/A')}")
            print(f"    ETag: {head_response.get('ETag', 'N/A')}")
    else:
        print("✗ bucket 中没有找到任何文件")
        
except s3_client.exceptions.NoSuchBucket:
    print(f"✗ Bucket {bucket_name} 不存在")
except Exception as e:
    print(f"✗ 错误: {e}")