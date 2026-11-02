#!/bin/bash
# Coverage analysis script for JobFlow Tracker
# Usage: ./scripts/coverage.sh

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📊 JobFlow Tracker Coverage Analysis${NC}"
echo -e "${BLUE}====================================${NC}"

# Check if pytest and coverage are available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest is not installed. Please run: pip install -r requirements-dev.txt${NC}"
    exit 1
fi

if ! command -v coverage &> /dev/null; then
    echo -e "${RED}❌ coverage is not installed. Please run: pip install -r requirements-dev.txt${NC}"
    exit 1
fi

# Set PYTHONPATH to current directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo -e "\n${YELLOW}🧪 Running tests with coverage...${NC}"

# Run tests with coverage
pytest tests/unit/ tests/integration/ \
    --cov=app \
    --cov=core_data \
    --cov=utils \
    --cov=chart \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-branch

echo -e "\n${YELLOW}📈 Coverage Summary${NC}"
coverage report --show-missing

echo -e "\n${BLUE}📊 Detailed HTML report: htmlcov/index.html${NC}"
echo -e "${BLUE}📄 XML report: coverage.xml${NC}"

# Check coverage threshold
COVERAGE_THRESHOLD=90
COVERAGE=$(coverage report --format=total)

echo -e "\n${YELLOW}Coverage: ${COVERAGE}%${NC}"

if [ "$COVERAGE" -ge "$COVERAGE_THRESHOLD" ]; then
    echo -e "${GREEN}✅ Coverage meets threshold (${COVERAGE_THRESHOLD}%)${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Coverage below threshold (${COVERAGE_THRESHOLD}%)${NC}"
    exit 1
fi