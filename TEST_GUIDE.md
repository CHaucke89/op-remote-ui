# Testing Guide - OpenPilot UI Memory-Only Streaming

## 🧪 Complete Testing Before Device Deployment

This guide shows how to test the optimized streaming solution on your local machine before deploying to the OpenPilot device.

## 📋 Test Components

### 1. **Mock UI Simulator** (`test/mock_ui_simulator.py`)
- Simulates the Qt application without needing C++ compilation
- Generates realistic UI frames with lane lines, speed indicators, etc.
- Writes frames to shared memory exactly like the real Qt app

### 2. **Shared Memory Tests** (`test/test_shared_memory.py`)
- Verifies shared memory creation and access
- Tests frame data integrity
- Monitors frame update frequency

### 3. **Integration Tests** (`test/integration_test.py`)
- Tests complete pipeline: UI → Memory → Server → WebSocket → Client
- Verifies latency and throughput
- Tests input event handling

### 4. **Performance Benchmark** (`test/benchmark.py`)
- Compares disk-based vs memory-based approaches
- Measures disk usage, latency, and memory consumption
- Generates performance reports

## 🚀 Quick Start Testing

### Option 1: Automated Test Suite

```bash
# Make script executable
chmod +x test/run_tests.sh

# Run all tests
./test/run_tests.sh
```

This runs:
- Unit tests
- Integration tests
- Performance benchmarks
- Docker tests (if available)

### Option 2: Manual Testing

#### Step 1: Start Mock UI Simulator
```bash
# Terminal 1 - Start UI simulator
python3 test/mock_ui_simulator.py --fps 2

# You should see:
# ✅ Shared memory initialized: /dev/shm/openpilot_ui_frames
# 🚀 Starting UI simulation: 2160x1080 @ 2 FPS
# 📸 Frame 1 written to shared memory
```

#### Step 2: Verify Shared Memory
```bash
# Terminal 2 - Test shared memory
python3 test/test_shared_memory.py

# Expected output:
# ✅ Shared memory file exists
# ✅ Metadata read successfully
# ✅ Frame updates working
# ✅ Valid JPEG data
# 🎉 All tests passed!
```

#### Step 3: Start Streaming Server
```bash
# Terminal 3 - Start server
python3 stream_server.py

# You should see:
# Starting memory-only streaming server...
# No disk storage required - using shared memory
# * Running on http://0.0.0.0:8081
```

#### Step 4: View in Browser
Open browser and navigate to: `http://localhost:8081`

You should see:
- Live UI simulation streaming
- FPS counter showing ~2 FPS
- Latency < 200ms
- Memory usage < 6MB

#### Step 5: Test Touch/Click Events
Click on the streamed UI in browser and verify:
- Green circles appear at click points
- Server logs show received events
- No errors in console

## 🐳 Docker Testing (Isolated Environment)

### Build and Run with Docker Compose
```bash
# Build containers
docker-compose -f test/docker-compose.yml build

# Run all services
docker-compose -f test/docker-compose.yml up

# Access UI at http://localhost:8081

# Stop services
docker-compose -f test/docker-compose.yml down
```

## 📊 Performance Testing

### Run Performance Benchmark
```bash
python3 test/benchmark.py --duration 60

# Expected results:
# Disk-Based Approach:
#   Total disk usage: ~120 MB (for 60 seconds)
#   Projected daily: ~43 GB
#   Average latency: 500-1000 ms
#
# Memory-Based Approach:
#   Disk usage: 0 MB
#   Average memory: ~6000 KB
#   Average latency: 50-150 ms
#
# Improvement Summary:
#   ✅ Disk space saved: 100%
#   ✅ Latency improvement: 5-10x faster
#   ✅ Daily disk savings: 43 GB
```

## 🔍 What to Verify Before Deployment

### ✅ Checklist

1. **Shared Memory Working**
   ```bash
   ls -lh /dev/shm/openpilot_ui_frames
   # Should show ~8MB file
   ```

2. **No Disk Writes**
   ```bash
   # Monitor /tmp directory during test
   watch "ls -la /tmp/ui_frame_*.png 2>/dev/null | wc -l"
   # Should show 0 files
   ```

3. **Memory Usage Stable**
   ```bash
   # Check server stats
   curl http://localhost:8081/stats
   # Should show < 10MB total memory
   ```

4. **WebSocket Streaming**
   - Open browser developer tools
   - Go to Network tab
   - Should see active WebSocket connection
   - No HTTP polling requests

5. **Latency Acceptable**
   - Check browser console for latency logs
   - Should be < 200ms consistently

## 🛠️ Troubleshooting Test Issues

### Issue: "Shared memory file not found"
```bash
# Check if simulator is running
ps aux | grep mock_ui_simulator

# Manually create shared memory
python3 -c "
import os
shm_path = '/dev/shm/openpilot_ui_frames'
if not os.path.exists(shm_path):
    with open(shm_path, 'wb') as f:
        f.write(b'\x00' * 1024)
"
```

### Issue: "WebSocket connection failed"
```bash
# Check if server is running
curl http://localhost:8081/stats

# Check firewall
sudo iptables -L | grep 8081

# Try different port
python3 stream_server.py --port 8082
```

### Issue: "High memory usage"
```bash
# Check for memory leaks
python3 -m tracemalloc test/mock_ui_simulator.py

# Monitor memory over time
while true; do
    ps aux | grep -E "mock_ui|stream_server" | awk '{print $6}'
    sleep 5
done
```

## 📈 Expected Test Results

### Successful Test Output
```
======================================
OpenPilot UI Streaming - Test Suite
======================================

Test 1: Shared Memory Unit Tests
✅ Shared memory tests PASSED

Test 2: Integration Tests
✅ Server Health: PASS
✅ Web Interface: PASS
✅ WebSocket Streaming: PASS (20 frames, avg 120ms latency)
✅ Input Handling: PASS
✅ Memory Usage: PASS (avg 5.2MB)

Test 3: Performance Benchmark
✅ 100% disk space reduction
✅ 8x latency improvement
✅ 43GB daily savings

📊 Test Summary
✅ All critical tests PASSED! Safe to deploy.
```

## 🚢 Ready for Deployment?

If all tests pass:

1. **Copy files to device:**
   ```bash
   scp frame_streamer.* stream_server.py root@DEVICE_IP:/data/
   ```

2. **Follow installation steps in README_OPTIMIZED.md**

3. **Monitor first run:**
   ```bash
   ssh root@DEVICE_IP
   journalctl -f | grep -E "frame|stream"
   ```

## 📝 Notes

- Tests simulate 2160x1080 resolution (OpenPilot UI standard)
- JPEG quality set to 85% (adjustable)
- Frame rate of 2 FPS (adjustable)
- All tests can run without root privileges
- No actual Qt/C++ compilation needed for testing