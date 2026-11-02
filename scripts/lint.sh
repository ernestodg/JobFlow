#!/bin/bash
# Linting and formatting script for JobFlow Tracker
# Usage: ./scripts/lint.sh [--fix]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FIX_MODE=false
if [ "$1" = "--fix" ]; then
    FIX_MODE=true
fi

echo -e "${BLUE}🔍 JobFlow Tracker Code Quality Check${NC}"
echo -e "${BLUE}=====================================${NC}"

FAILED_CHECKS=0

# Function to run a check
run_check() {
    local name=$1
    local command=$2
    
    echo -e "\n${YELLOW}Running $name...${NC}"
    
    if eval $command; then
        echo -e "${GREEN}✅ $name passed${NC}"
        return 0
    else
        echo -e "${RED}❌ $name failed${NC}"
        return 1
    fi
}

# Ruff linting and formatting
if command -v ruff &> /dev/null; then
    if [ "$FIX_MODE" = true ]; then
        echo -e "\n${YELLOW}🔧 Fixing code with ruff...${NC}"
        ruff check --fix .
        ruff format .
        echo -e "${GREEN}✅ Code formatted with ruff${NC}"
    else
        run_check "Ruff linting" "ruff check ."
        if [ $? -ne 0 ]; then ((FAILED_CHECKS++)); fi
        
        run_check "Ruff formatting" "ruff format --check ."
        if [ $? -ne 0 ]; then ((FAILED_CHECKS++)); fi
    fi
else
    echo -e "${YELLOW}⚠️  Ruff not installed${NC}"
fi

# MyPy type checking
if command -v mypy &> /dev/null; then
    run_check "MyPy type checking" "mypy app.py core_data.py utils.py chart.py --ignore-missing-imports"
    if [ $? -ne 0 ]; then ((FAILED_CHECKS++)); fi
else
    echo -e "${YELLOW}⚠️  MyPy not installed${NC}"
fi

# Bandit security linting
if command -v bandit &> /dev/null; then
    run_check "Bandit security linting" "bandit -r . -x tests/ -ll"
    if [ $? -ne 0 ]; then ((FAILED_CHECKS++)); fi
else
    echo -e "${YELLOW}⚠️  Bandit not installed${NC}"
fi

# Safety vulnerability check
if command -v safety &> /dev/null; then
    run_check "Safety vulnerability check" "safety check"
    if [ $? -ne 0 ]; then ((FAILED_CHECKS++)); fi
else
    echo -e "${YELLOW}⚠️  Safety not installed${NC}"
fi

# Final summary
echo -e "\n${BLUE}🏁 Lint Summary${NC}"
echo -e "${BLUE}===============${NC}"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}🎉 All code quality checks passed!${NC}"
    exit 0
else
    echo -e "${RED}💥 $FAILED_CHECKS checks failed${NC}"
    if [ "$FIX_MODE" = false ]; then
        echo -e "${YELLOW}💡 Try running: ./scripts/lint.sh --fix${NC}"
    fi
    exit 1
fi