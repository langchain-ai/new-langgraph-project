import boto3

# Configure S3 client for LocalStack
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

# Create bucket
try:
    s3_client.create_bucket(Bucket='medical-claims-documents')
    print("Bucket created successfully")
except Exception as e:
    print(f"Bucket creation: {e}")

# Upload file
try:
    s3_client.upload_file('documents/2_pagers.pdf', 'medical-claims-documents', 'documents/2_pagers.pdf')
    print("File uploaded successfully to s3://medical-claims-documents/documents/2_pagers.pdf")
except Exception as e:
    print(f"Upload failed: {e}")
