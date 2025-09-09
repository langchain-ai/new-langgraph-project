#!/bin/bash

# AI Agents Local Deployment Script
set -e

echo "========================================="
echo "AI Agents - Local Docker Deployment"
echo "========================================="

# Check for required commands
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Parse command line arguments
ACTION=${1:-up}
PROFILE=${2:-default}

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "Please update .env file with your configuration (especially OPENAI_API_KEY)"
fi

# Function to check service health
check_health() {
    local service=$1
    local port=$2
    local endpoint=${3:-/health}
    
    echo -n "Checking $service health..."
    for i in {1..30}; do
        if curl -f -s "http://localhost:$port$endpoint" > /dev/null 2>&1; then
            echo " ✓"
            return 0
        fi
        echo -n "."
        sleep 2
    done
    echo " ✗"
    return 1
}

# Function to setup LocalStack resources
setup_localstack() {
    echo "Setting up LocalStack resources..."
    
    # Install AWS CLI if not present
    if ! command -v aws &> /dev/null; then
        echo "Installing AWS CLI..."
        pip install awscli-local
    fi
    
    # Wait for LocalStack to be ready
    check_health "LocalStack" 4566 "/_localstack/health"
    
    # Run initialization script
    docker exec localstack bash /docker-entrypoint-initaws.d/init.sh
}

# Main deployment logic
case "$ACTION" in
    up|start)
        echo "Starting services..."
        
        if [ "$PROFILE" == "studio" ]; then
            docker-compose --profile studio up -d
        else
            docker-compose up -d
        fi
        
        echo "Waiting for services to be ready..."
        sleep 5
        
        # Check service health
        check_health "LocalStack" 4566 "/_localstack/health"
        
        # Setup LocalStack resources
        setup_localstack
        
        # Wait for API to be ready
        check_health "API" 8000 "/health"
        
        echo ""
        echo "========================================="
        echo "Deployment successful!"
        echo "========================================="
        echo "Services available at:"
        echo "  - API: http://localhost:8000"
        echo "  - API Docs: http://localhost:8000/docs"
        echo "  - LocalStack: http://localhost:4566"
        if [ "$PROFILE" == "studio" ]; then
            echo "  - LangGraph Studio: http://localhost:8080"
        fi
        echo ""
        echo "To view logs: docker-compose logs -f"
        echo "To stop: ./scripts/deploy.sh down"
        ;;
        
    down|stop)
        echo "Stopping services..."
        docker-compose down
        echo "Services stopped."
        ;;
        
    restart)
        echo "Restarting services..."
        $0 down
        sleep 2
        $0 up $PROFILE
        ;;
        
    logs)
        docker-compose logs -f
        ;;
        
    test)
        echo "Running tests..."
        
        # Check if services are running
        if ! docker-compose ps | grep -q "Up"; then
            echo "Services are not running. Starting them..."
            $0 up
        fi
        
        # Run API tests
        echo "Testing document classification endpoint..."
        curl -X POST "http://localhost:8000/api/v1/process" \
            -H "Content-Type: application/json" \
            -d '{
                "s3_key": "test/sample-cms1500.pdf",
                "process_type": "classify"
            }' | python -m json.tool
        
        echo ""
        echo "Test complete!"
        ;;
        
    clean)
        echo "Cleaning up..."
        docker-compose down -v
        echo "All containers and volumes removed."
        ;;
        
    *)
        echo "Usage: $0 {up|down|restart|logs|test|clean} [profile]"
        echo ""
        echo "Actions:"
        echo "  up/start    - Start all services"
        echo "  down/stop   - Stop all services"
        echo "  restart     - Restart all services"
        echo "  logs        - View service logs"
        echo "  test        - Run basic tests"
        echo "  clean       - Remove containers and volumes"
        echo ""
        echo "Profiles:"
        echo "  default     - Run core services only"
        echo "  studio      - Include LangGraph Studio"
        exit 1
        ;;
esac