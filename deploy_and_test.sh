#!/bin/bash

# Deploy and test AI Agents with LocalStack
# Usage: ./deploy_and_test.sh

set -e

echo "🚀 AI Agents Deployment and Testing Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo -e "\n${YELLOW}Step 1: Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose are installed${NC}"

# Step 2: Create .env file if it doesn't exist
echo -e "\n${YELLOW}Step 2: Setting up environment...${NC}"

if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env file from .env.example${NC}"
    echo -e "${YELLOW}⚠️  Please update .env with your OPENAI_API_KEY if needed${NC}"
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

# Step 3: Build Docker images
echo -e "\n${YELLOW}Step 3: Building Docker images...${NC}"
docker-compose build

# Step 4: Start services
echo -e "\n${YELLOW}Step 4: Starting services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"

# Wait for LocalStack
echo -n "Waiting for LocalStack..."
for i in {1..30}; do
    if curl -s http://localhost:4566/_localstack/health | grep -q '"s3": "running"'; then
        echo -e " ${GREEN}✅${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# Wait for API
echo -n "Waiting for API..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health | grep -q '"status":"healthy"'; then
        echo -e " ${GREEN}✅${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# Step 5: Upload test file to LocalStack S3
echo -e "\n${YELLOW}Step 5: Setting up test data in LocalStack...${NC}"

# Create S3 bucket if it doesn't exist
aws --endpoint-url=http://localhost:4566 s3 mb s3://medical-documents 2>/dev/null || true

# Check if test file exists locally
if [ ! -f "tests/test-files/2_page_with_back.pdf" ]; then
    echo -e "${YELLOW}⚠️  Test file not found locally. Creating a dummy file...${NC}"
    mkdir -p tests/test-files
    # You should replace this with actual test file
    echo "%PDF-1.4 test content" > tests/test-files/2_page_with_back.pdf
fi

# Upload test file to S3
aws --endpoint-url=http://localhost:4566 \
    s3 cp tests/test-files/2_page_with_back.pdf \
    s3://medical-documents/2_page_with_back.pdf

echo -e "${GREEN}✅ Test file uploaded to S3${NC}"

# List S3 contents
echo -e "\n${YELLOW}S3 Bucket Contents:${NC}"
aws --endpoint-url=http://localhost:4566 s3 ls s3://medical-documents/

# Step 6: Run tests
echo -e "\n${YELLOW}Step 6: Running tests...${NC}"

# Test inside Docker container
echo -e "\n${YELLOW}Running tests in Docker container...${NC}"
docker-compose exec -T ai-agents-api python test_s3_document.py

# Step 7: Show logs
echo -e "\n${YELLOW}Step 7: Recent logs...${NC}"
docker-compose logs --tail=20 ai-agents-api

# Step 8: Test API endpoints
echo -e "\n${YELLOW}Step 8: Testing API endpoints...${NC}"

# Test health endpoint
echo -e "\n${YELLOW}Testing /health endpoint:${NC}"
curl -s http://localhost:8000/health | python -m json.tool

# Test root endpoint
echo -e "\n${YELLOW}Testing / endpoint:${NC}"
curl -s http://localhost:8000/ | python -m json.tool

# Test v2 process endpoint
echo -e "\n${YELLOW}Testing /api/v2/process endpoint:${NC}"
curl -X POST http://localhost:8000/api/v2/process \
    -H "Content-Type: application/json" \
    -d '{
        "s3_key": "2_page_with_back.pdf",
        "bucket": "medical-documents"
    }' | python -m json.tool

# Step 9: Summary
echo -e "\n${GREEN}=========================================="
echo "🎉 Deployment and Testing Complete!"
echo "==========================================${NC}"
echo ""
echo "Services running:"
echo "  - LocalStack S3: http://localhost:4566"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - Run tests: docker-compose exec ai-agents-api python test_s3_document.py"
echo ""
echo "Test file location:"
echo "  - S3: s3://medical-documents/2_page_with_back.pdf"
echo "  - URL: http://localhost:4566/medical-documents/2_page_with_back.pdf"