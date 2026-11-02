#!/bin/bash
# Comprehensive test runner for JobFlow Tracker
# Usage: ./scripts/test.sh [test-type]
# test-type: unit, property, integration, contracts, performance, all (default)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default to running all tests
TEST_TYPE=${1:-all}

echo -e "${BLUE}🧪 JobFlow Tracker Test Suite${NC}"
echo -e "${BLUE}===============================${NC}"

# Function to run a specific test category
run_test_category() {
    local category=$1
    local description=$2
    local path=$3
    local extra_args=$4
    
    echo -e "\n${YELLOW}📋 Running $description...${NC}"
    
    if [ -d "tests/$path" ] && [ "$(ls -A tests/$path 2>/dev/null)" ]; then
        if pytest tests/$path/ -v --tb=short $extra_args; then
            echo -e "${GREEN}✅ $description passed${NC}"
            return 0
        else
            echo -e "${RED}❌ $description failed${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  No $description found (tests/$path/)${NC}"
        return 0
    fi
}

# Function to run linting
run_linting() {
    echo -e "\n${YELLOW}🔍 Running code quality checks...${NC}"
    
    # Ruff linting
    if command -v ruff &> /dev/null; then
        echo "Running ruff..."
        if ruff check .; then
            echo -e "${GREEN}✅ Ruff linting passed${NC}"
        else
            echo -e "${RED}❌ Ruff linting failed${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  Ruff not installed${NC}"
    fi
    
    # MyPy type checking
    if command -v mypy &> /dev/null; then
        echo "Running mypy..."
        if mypy app.py core_data.py utils.py --ignore-missing-imports; then
            echo -e "${GREEN}✅ Type checking passed${NC}"
        else
            echo -e "${YELLOW}⚠️  Type checking has warnings${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  MyPy not installed${NC}"
    fi
}

# Function to run security checks
run_security() {
    echo -e "\n${YELLOW}🔐 Running security checks...${NC}"
    
    # Bandit security linting
    if command -v bandit &> /dev/null; then
        echo "Running bandit..."
        if bandit -r . -x tests/; then
            echo -e "${GREEN}✅ Security check passed${NC}"
        else
            echo -e "${YELLOW}⚠️  Security check has warnings${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Bandit not installed${NC}"
    fi
    
    # Safety vulnerability check
    if command -v safety &> /dev/null; then
        echo "Running safety check..."
        if safety check; then
            echo -e "${GREEN}✅ Vulnerability check passed${NC}"
        else
            echo -e "${YELLOW}⚠️  Vulnerability check has warnings${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Safety not installed${NC}"
    fi
}

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest is not installed. Please run: pip install -r requirements-dev.txt${NC}"
    exit 1
fi

# Set PYTHONPATH to current directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Initialize test results
FAILED_TESTS=0

case $TEST_TYPE in
    "unit")
        run_test_category "unit" "Unit Tests" "unit" "--cov=. --cov-report=term-missing"
        FAILED_TESTS=$?
        ;;
        
    "property")
        run_test_category "property" "Property-Based Tests" "property" "--hypothesis-show-statistics"
        FAILED_TESTS=$?
        ;;
        
    "integration")
        run_test_category "integration" "Integration Tests" "integration"
        FAILED_TESTS=$?
        ;;
        
    "contracts")
        run_test_category "contracts" "Contract/Snapshot Tests" "contracts"
        FAILED_TESTS=$?
        ;;
        
    "performance")
        run_test_category "performance" "Performance Benchmarks" "performance" "--benchmark-only"
        FAILED_TESTS=$?
        ;;
        
    "lint")
        run_linting
        FAILED_TESTS=$?
        ;;
        
    "security")
        run_security
        FAILED_TESTS=$?
        ;;
        
    "all"|*)
        echo -e "${BLUE}Running full test suite...${NC}"
        
        # Run linting first
        run_linting
        if [ $? -ne 0 ]; then ((FAILED_TESTS++)); fi
        
        # Run unit tests with coverage
        run_test_category "unit" "Unit Tests" "unit" "--cov=. --cov-report=term-missing --cov-report=html"
        if [ $? -ne 0 ]; then ((FAILED_TESTS++)); fi
        
        # Run property-based tests
        run_test_category "property" "Property-Based Tests" "property" "--hypothesis-show-statistics"
        if [ $? -ne 0 ]; then ((FAILED_TESTS++)); fi
        
        # Run integration tests
        run_test_category "integration" "Integration Tests" "integration"
        if [ $? -ne 0 ]; then ((FAILED_TESTS++)); fi
        
        # Run contract tests
        run_test_category "contracts" "Contract/Snapshot Tests" "contracts"
        if [ $? -ne 0 ]; then ((FAILED_TESTS++)); fi
        
        # Run security checks
        run_security
        if [ $? -ne 0 ]; then ((FAILED_TESTS++)); fi
        
        # Show coverage report if available
        if [ -f htmlcov/index.html ]; then
            echo -e "\n${BLUE}📊 Coverage report generated: htmlcov/index.html${NC}"
        fi
        ;;
esac

# Final summary
echo -e "\n${BLUE}🏁 Test Summary${NC}"
echo -e "${BLUE}===============${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}💥 $FAILED_TESTS test categories failed${NC}"
    exit 1
fi