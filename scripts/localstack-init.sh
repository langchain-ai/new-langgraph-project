#!/bin/bash

echo "Initializing LocalStack resources..."

# Wait for LocalStack to be ready
until awslocal s3 ls; do
  echo "Waiting for LocalStack to be ready..."
  sleep 2
done

# Create S3 bucket for medical documents
echo "Creating S3 bucket: medical-documents"
awslocal s3 mb s3://medical-documents

# Set bucket versioning
awslocal s3api put-bucket-versioning \
  --bucket medical-documents \
  --versioning-configuration Status=Enabled

# Create test folders
awslocal s3api put-object --bucket medical-documents --key incoming/
awslocal s3api put-object --bucket medical-documents --key processed/
awslocal s3api put-object --bucket medical-documents --key failed/

# Upload sample test files if they exist
if [ -d "/docker-entrypoint-initaws.d/test-files" ]; then
  echo "Uploading test files..."
  for file in /docker-entrypoint-initaws.d/test-files/*; do
    if [ -f "$file" ]; then
      filename=$(basename "$file")
      awslocal s3 cp "$file" "s3://medical-documents/incoming/$filename"
      echo "Uploaded: $filename"
    fi
  done
fi

# Create Secrets Manager secrets for API keys (placeholder values)
echo "Creating secrets in Secrets Manager..."
awslocal secretsmanager create-secret \
  --name openai-api-key \
  --description "OpenAI API Key" \
  --secret-string '{"api_key":"sk-test-key-placeholder"}'

# Configure Textract (LocalStack Pro required for full functionality)
# Note: Textract simulation in LocalStack Community is limited
echo "Textract service configured (limited in Community edition)"

echo "LocalStack initialization complete!"
echo "S3 bucket 'medical-documents' is ready with folders:"
echo "  - incoming/ (for new documents)"
echo "  - processed/ (for successfully processed documents)"
echo "  - failed/ (for documents that failed processing)"