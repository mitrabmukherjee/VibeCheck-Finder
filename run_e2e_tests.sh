#!/bin/bash
# End-to-End Test Runner Script
# Semantic Media Engine

set -e  # Exit on error

echo "=========================================="
echo "Semantic Media Engine - E2E Test Runner"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
POSTGRES_DB="${POSTGRES_DB:-semantic_media}"

# Function to check if a service is running
check_service() {
    local service_name=$1
    local check_command=$2
    
    echo -n "Checking $service_name... "
    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not running${NC}"
        return 1
    fi
}

# Function to wait for service
wait_for_service() {
    local service_name=$1
    local check_command=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "Waiting for $service_name to be ready"
    while [ $attempt -le $max_attempts ]; do
        if eval "$check_command" > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e " ${RED}✗ Timeout${NC}"
    return 1
}

echo "Step 1: Prerequisites Check"
echo "----------------------------"

# Check PostgreSQL
if ! check_service "PostgreSQL" "pg_isready -h localhost -p 5432"; then
    echo -e "${RED}Error: PostgreSQL is not running${NC}"
    echo "Start PostgreSQL and try again"
    exit 1
fi

# Check if database exists
echo -n "Checking database '$POSTGRES_DB'... "
if psql -lqt | cut -d \| -f 1 | grep -qw "$POSTGRES_DB"; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    echo "Create database with: createdb $POSTGRES_DB"
    exit 1
fi

# Check Qdrant
if ! check_service "Qdrant" "curl -s http://localhost:6333/health"; then
    echo -e "${YELLOW}Warning: Qdrant is not running${NC}"
    echo "Start Qdrant with: docker run -p 6333:6333 qdrant/qdrant"
    exit 1
fi

# Check sample data
echo -n "Checking sample data... "
MEDIA_COUNT=$(psql -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM media_items;" 2>/dev/null | tr -d ' ')
if [ -n "$MEDIA_COUNT" ] && [ "$MEDIA_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ $MEDIA_COUNT items${NC}"
else
    echo -e "${RED}✗ No data${NC}"
    echo "Load sample data with: python backend/data_pipeline/run_sample_pipeline.py"
    exit 1
fi

echo ""
echo "Step 2: Backend Service Check"
echo "------------------------------"

# Check if backend is running
if ! check_service "Backend API" "curl -s $BACKEND_URL/health"; then
    echo -e "${YELLOW}Backend is not running. Please start it manually:${NC}"
    echo "  cd backend"
    echo "  source venv/bin/activate"
    echo "  uvicorn main:app --reload"
    echo ""
    echo "Press Enter when backend is ready, or Ctrl+C to cancel..."
    read
    
    # Wait for backend to be ready
    if ! wait_for_service "Backend API" "curl -s $BACKEND_URL/health"; then
        echo -e "${RED}Error: Backend did not start${NC}"
        exit 1
    fi
fi

echo ""
echo "Step 3: Running Automated Tests"
echo "--------------------------------"

# Run Python E2E tests
if [ -f "test_e2e.py" ]; then
    python test_e2e.py --backend-url "$BACKEND_URL" "$@"
    TEST_EXIT_CODE=$?
else
    echo -e "${RED}Error: test_e2e.py not found${NC}"
    exit 1
fi

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "All E2E tests passed!"
    echo "==========================================${NC}"
else
    echo -e "${RED}=========================================="
    echo "Some E2E tests failed"
    echo "==========================================${NC}"
fi

exit $TEST_EXIT_CODE
