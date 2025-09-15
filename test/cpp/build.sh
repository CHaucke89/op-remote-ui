#!/bin/bash
# Build script for OpenPilot UI C++ tests

set -e

echo "======================================"
echo "Building OpenPilot UI C++ Tests"
echo "======================================"

# Check for required dependencies
echo "🔍 Checking dependencies..."

# Check Qt5
if ! pkg-config --exists Qt5Core Qt5Widgets Qt5Network; then
    echo "❌ Qt5 development packages not found!"
    echo "Install with: sudo apt install qtbase5-dev qttools5-dev"
    exit 1
fi

echo "✅ Qt5 found: $(pkg-config --modversion Qt5Core)"

# Check CMake
if ! command -v cmake &> /dev/null; then
    echo "❌ CMake not found!"
    echo "Install with: sudo apt install cmake"
    exit 1
fi

echo "✅ CMake found: $(cmake --version | head -1)"

# Create build directory
echo ""
echo "📁 Setting up build directory..."
rm -rf build
mkdir -p build
cd build

# Configure with CMake
echo ""
echo "⚙️  Configuring build..."
cmake .. -DCMAKE_BUILD_TYPE=Debug

# Build
echo ""
echo "🔨 Building..."
make -j$(nproc)

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "To run the test:"
    echo "  cd build && ./openpilot_ui_test"
    echo ""
    echo "Or run: make run_tests"
else
    echo ""
    echo "❌ Build failed!"
    exit 1
fi