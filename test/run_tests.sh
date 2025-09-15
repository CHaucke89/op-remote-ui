#!/bin/bash
# Comprehensive test runner script

echo "======================================"
echo "OpenPilot UI Streaming - Test Suite"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "🔍 Checking environment..."
python3 --version
pip3 --version

# Install test dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt
pip3 install -r test/requirements-test.txt

# Test 1: Unit tests for shared memory
echo ""
echo "======================================"
echo "Test 1: Shared Memory Unit Tests"
echo "======================================"

# Start simulator in background
echo "Starting mock UI simulator..."
python3 test/mock_ui_simulator.py --duration 30 &
SIMULATOR_PID=$!
sleep 3

# Run shared memory tests
python3 test/test_shared_memory.py
TEST1_RESULT=$?

# Stop simulator
kill $SIMULATOR_PID 2>/dev/null
wait $SIMULATOR_PID 2>/dev/null

if [ $TEST1_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Shared memory tests PASSED${NC}"
else
    echo -e "${RED}❌ Shared memory tests FAILED${NC}"
fi

# Test 2: Integration tests
echo ""
echo "======================================"
echo "Test 2: Integration Tests"
echo "======================================"

# Start both simulator and server
echo "Starting services for integration testing..."
python3 test/mock_ui_simulator.py &
SIMULATOR_PID=$!
sleep 2

python3 stream_server.py &
SERVER_PID=$!
sleep 3

# Run integration tests
python3 test/integration_test.py
TEST2_RESULT=$?

# Stop services
kill $SIMULATOR_PID 2>/dev/null
kill $SERVER_PID 2>/dev/null
wait $SIMULATOR_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null

if [ $TEST2_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Integration tests PASSED${NC}"
else
    echo -e "${RED}❌ Integration tests FAILED${NC}"
fi

# Test 3: Performance benchmark
echo ""
echo "======================================"
echo "Test 3: Performance Benchmark"
echo "======================================"

python3 test/benchmark.py --duration 20
TEST3_RESULT=$?

if [ $TEST3_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Performance benchmark completed${NC}"
else
    echo -e "${YELLOW}⚠️  Performance benchmark had issues${NC}"
fi

# Test 4: Docker tests (if Docker is available)
echo ""
echo "======================================"
echo "Test 4: Docker Container Tests"
echo "======================================"

if command -v docker &> /dev/null; then
    echo "Docker found, running container tests..."

    # Build Docker image
    docker build -f test/Dockerfile -t openpilot-ui-test:latest .

    # Run Docker compose tests
    docker-compose -f test/docker-compose.yml up --abort-on-container-exit
    TEST4_RESULT=$?

    # Cleanup
    docker-compose -f test/docker-compose.yml down

    if [ $TEST4_RESULT -eq 0 ]; then
        echo -e "${GREEN}✅ Docker tests PASSED${NC}"
    else
        echo -e "${RED}❌ Docker tests FAILED${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker not found, skipping container tests${NC}"
    TEST4_RESULT=0
fi

# Summary
echo ""
echo "======================================"
echo "📊 Test Summary"
echo "======================================"

TOTAL_FAILED=0

if [ $TEST1_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Shared Memory Tests: PASSED${NC}"
else
    echo -e "${RED}❌ Shared Memory Tests: FAILED${NC}"
    TOTAL_FAILED=$((TOTAL_FAILED + 1))
fi

if [ $TEST2_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Integration Tests: PASSED${NC}"
else
    echo -e "${RED}❌ Integration Tests: FAILED${NC}"
    TOTAL_FAILED=$((TOTAL_FAILED + 1))
fi

if [ $TEST3_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Performance Benchmark: COMPLETED${NC}"
else
    echo -e "${YELLOW}⚠️  Performance Benchmark: ISSUES${NC}"
fi

if [ $TEST4_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Docker Tests: PASSED/SKIPPED${NC}"
else
    echo -e "${RED}❌ Docker Tests: FAILED${NC}"
    TOTAL_FAILED=$((TOTAL_FAILED + 1))
fi

echo ""
if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical tests PASSED! Safe to deploy.${NC}"
    exit 0
else
    echo -e "${RED}❌ $TOTAL_FAILED test suite(s) failed. Please review before deploying.${NC}"
    exit 1
fi