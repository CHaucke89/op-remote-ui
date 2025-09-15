# C++ Testing Guide - Test Your Code Without OpenPilot Device

## 🎯 Overview

This guide shows how to test your C++ frame streaming and touch injection code locally using a mock Qt application, **without needing the actual OpenPilot device or environment**.

## 🧪 What Gets Tested

### ✅ **C++ Components Tested:**
1. **FrameStreamer** - Shared memory frame capture
2. **TouchInjector** - Unix socket input handling
3. **Shared Memory IPC** - Memory allocation and data transfer
4. **JPEG Compression** - Frame encoding pipeline
5. **Integration with Python** - Complete C++ → Python pipeline

### 🏗️ **Test Architecture:**
```
Mock Qt UI → FrameStreamer → Shared Memory → Python Server → Browser
     ↑              ↓                                  ↓
TouchInjector ← Unix Socket ← Input Events ← WebSocket
```

## 🚀 Quick Start

### Option 1: Run All C++ Tests
```bash
# From project root
cd test/cpp
chmod +x build.sh
./build.sh

# Run interactive test with GUI
cd build && ./openpilot_ui_test

# Run unit tests
cd build && ./unit_tests
```

### Option 2: Complete Integration Test
```bash
# From project root
python3 test/cpp/integration_test.py
```

## 🔧 Prerequisites

### Install Qt5 Development (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install qtbase5-dev qttools5-dev cmake build-essential
```

### Install Qt5 Development (Other Systems):
```bash
# Fedora/RHEL
sudo dnf install qt5-qtbase-devel cmake gcc-c++

# macOS (Homebrew)
brew install qt@5 cmake

# Windows (MSYS2)
pacman -S mingw-w64-x86_64-qt5 mingw-w64-x86_64-cmake
```

## 🏃‍♂️ Running Tests

### 1. Build C++ Tests
```bash
cd test/cpp
./build.sh
```

Expected output:
```
======================================
Building OpenPilot UI C++ Tests
======================================
✅ Qt5 found: 5.15.3
✅ CMake found: cmake version 3.22.1
📁 Setting up build directory...
⚙️  Configuring build...
🔨 Building...
✅ Build successful!
```

### 2. Interactive GUI Test
```bash
cd test/cpp/build
./openpilot_ui_test
```

This opens a **mock OpenPilot UI** window that:
- Shows simulated driving interface
- Updates speed, lane position, alerts
- Captures frames to shared memory at 2 FPS
- Handles touch/input events

**What you'll see:**
- Qt window with mock OpenPilot UI
- Console logs showing frame capture
- Shared memory file created at `/dev/shm/openpilot_ui_frames`

### 3. Unit Tests
```bash
cd test/cpp/build
./unit_tests
```

Tests:
- ✅ FrameStreamer creation
- ✅ Shared memory initialization
- ✅ Frame capture functionality
- ✅ JPEG format validation
- ✅ TouchInjector socket creation

### 4. Complete Integration Test
```bash
# From project root
python3 test/cpp/integration_test.py
```

This runs the **complete pipeline**:
1. Builds and starts C++ mock UI
2. Verifies shared memory creation
3. Starts Python streaming server
4. Tests frame streaming C++ → Python
5. Tests web interface access
6. Tests input event handling
7. Monitors performance

## 🔍 What Each Test Verifies

### **Mock Qt Application (`test_main.cc`)**
- Creates realistic OpenPilot UI simulation
- Tests FrameStreamer with actual Qt window
- Tests TouchInjector socket creation
- Runs for 30 seconds with real frame capture

### **Unit Tests (`unit_tests.cc`)**
- **Shared Memory Tests:**
  - File creation at `/dev/shm/openpilot_ui_frames`
  - Correct size allocation (8MB)
  - Metadata structure validation

- **Frame Capture Tests:**
  - Timestamp validation (within 5 seconds)
  - JPEG format verification (0xFF 0xD8 header)
  - Frame size reasonability

- **TouchInjector Tests:**
  - Unix socket creation at `/tmp/ui_touch_socket`
  - Socket binding and listening

### **Integration Test (`integration_test.py`)**
- **C++ → Python Pipeline:**
  - Mock UI generates frames
  - FrameStreamer captures to shared memory
  - Python server reads from shared memory
  - WebSocket streams to browser

- **Performance Verification:**
  - Frame rate ~2 FPS
  - Memory usage < 10MB
  - Latency < 200ms

- **Input Event Loop:**
  - Browser sends click event
  - Python server receives via WebSocket
  - Forwards to Unix socket
  - TouchInjector processes event

## 🎯 Expected Results

### ✅ **Successful Test Output:**
```
=== OpenPilot UI C++ Unit Tests ===
=== Running FrameStreamer Tests ===
✅ testFrameStreamerCreation() PASS
✅ testSharedMemoryCreation() PASS
✅ testFrameCapture() PASS
✅ testFrameFormat() PASS

=== Running TouchInjector Tests ===
✅ testTouchInjectorCreation() PASS
✅ testSocketConnection() PASS

✅ All tests PASSED!
```

### 🔗 **Integration Test Success:**
```
🔗 C++ to Python Integration Test
✅ C++ Application Start: PASS
✅ Shared Memory Creation: PASS
✅ Python Server Start: PASS
✅ Frame Streaming: PASS
✅ Web Interface: PASS
✅ Input Handling: PASS
✅ Performance Monitoring: PASS

🎉 All integration tests PASSED!
C++ components work correctly with Python server!
```

## 🐛 Troubleshooting

### **Build Issues:**

**Qt5 Not Found:**
```bash
# Check Qt installation
pkg-config --list-all | grep -i qt
# Should show Qt5Core, Qt5Widgets, Qt5Network

# If missing, install:
sudo apt install qtbase5-dev qttools5-dev
```

**CMake Too Old:**
```bash
cmake --version
# Need 3.16+, upgrade if necessary
```

### **Runtime Issues:**

**Shared Memory Permission Error:**
```bash
# Check /dev/shm permissions
ls -la /dev/shm/
# Should allow write access

# If needed, cleanup old shared memory
sudo rm /dev/shm/openpilot_ui_frames
```

**Display Issues (Headless):**
```bash
# For headless testing, use Xvfb
sudo apt install xvfb
xvfb-run -a ./openpilot_ui_test
```

### **Integration Test Issues:**

**Port 8081 In Use:**
```bash
# Check what's using port 8081
sudo netstat -tlnp | grep :8081

# Kill existing process if needed
sudo pkill -f stream_server
```

## 📊 Performance Validation

The tests validate that your C++ code meets performance requirements:

- **Frame Rate:** ~2 FPS (configurable)
- **Memory Usage:** < 6MB fixed allocation
- **Latency:** < 200ms frame-to-display
- **CPU Usage:** Minimal (< 5% on modern systems)
- **Disk Usage:** 0 bytes (memory-only)

## 🎉 Ready for Device Deployment

If all C++ tests pass:

1. **Copy files to device:**
   ```bash
   scp frame_streamer.* main_optimized.cc root@DEVICE_IP:/data/openpilot/selfdrive/ui/
   ```

2. **Build on device:**
   ```bash
   ssh root@DEVICE_IP
   cd /data/openpilot
   scons selfdrive/ui
   ```

3. **Deploy Python server:**
   ```bash
   scp stream_server_fixed.py root@DEVICE_IP:/data/
   ```

The C++ components have been validated locally and should work identically on the device!

## 📝 Mock vs Real Differences

### **Mock Environment:**
- Simulated OpenPilot UI elements
- 2160x1080 resolution (same as device)
- JPEG compression at 85% quality
- Unix socket at `/tmp/ui_touch_socket`

### **Real Device:**
- Actual OpenPilot UI rendering
- Same resolution and compression
- Same IPC mechanisms
- Identical performance characteristics

The mock environment accurately represents the real device behavior for testing purposes.