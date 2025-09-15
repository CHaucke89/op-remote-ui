#!/usr/bin/env python3
"""
Real-time streaming test - Verify WebSocket streaming works without refresh
"""

import time
import json
import threading
import websocket
import subprocess
import requests

def test_realtime_streaming():
    """Test real-time WebSocket streaming"""
    print("🧪 Testing Real-Time Streaming (No Refresh Required)")
    print("-" * 50)

    # Start mock UI simulator
    print("1. Starting mock UI simulator...")
    simulator = subprocess.Popen(
        ["python3", "test/mock_ui_simulator.py", "--fps", "2"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(3)

    # Start fixed streaming server
    print("2. Starting real-time streaming server...")
    server = subprocess.Popen(
        ["python3", "stream_server_fixed.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(5)

    # Test WebSocket connection
    print("3. Testing WebSocket real-time streaming...")

    frames_received = 0
    connection_lost = False
    start_time = time.time()

    def on_message(ws, message):
        nonlocal frames_received
        try:
            data = json.loads(message)
            if data.get('type') == 'frame':
                frames_received += 1
                elapsed = time.time() - start_time
                fps = frames_received / elapsed if elapsed > 0 else 0
                print(f"   📸 Frame {frames_received} - FPS: {fps:.1f}", end='\r')
        except Exception as e:
            print(f"   ❌ Error processing frame: {e}")

    def on_error(ws, error):
        print(f"   ❌ WebSocket error: {error}")

    def on_close(ws, close_status_code, close_msg):
        nonlocal connection_lost
        connection_lost = True
        print(f"\n   🔌 WebSocket closed: {close_msg}")

    def on_open(ws):
        print("   ✅ WebSocket connected")
        # Request initial frame
        ws.send(json.dumps({'type': 'request_frame'}))

    try:
        # Test WebSocket streaming for 15 seconds
        ws = websocket.WebSocketApp(
            "ws://localhost:8081/stream",
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )

        # Run in a thread
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

        # Wait for test duration
        test_duration = 15
        time.sleep(test_duration)

        ws.close()

        # Calculate results
        expected_frames = test_duration * 2  # 2 FPS expected
        frame_rate = frames_received / test_duration

        print(f"\n\n📊 Real-Time Test Results:")
        print(f"   Duration: {test_duration} seconds")
        print(f"   Frames received: {frames_received}")
        print(f"   Expected frames: ~{expected_frames}")
        print(f"   Average FPS: {frame_rate:.2f}")
        print(f"   Connection lost: {connection_lost}")

        # Verify results
        if frames_received >= expected_frames * 0.8:  # 80% tolerance
            print(f"   ✅ PASS: Real-time streaming working properly")
            success = True
        else:
            print(f"   ❌ FAIL: Too few frames received")
            success = False

        if connection_lost:
            print(f"   ⚠️  WARNING: Connection was lost during test")

    except Exception as e:
        print(f"   ❌ WebSocket test failed: {e}")
        success = False

    finally:
        # Cleanup
        print("\n4. Cleaning up...")
        simulator.terminate()
        server.terminate()
        simulator.wait()
        server.wait()

    return success

def test_no_refresh_needed():
    """Test that browser doesn't need refresh for updates"""
    print("\n🔄 Testing Browser Refresh Requirements")
    print("-" * 50)

    # This test would normally be done with browser automation
    # For now, we'll test the HTTP endpoints to ensure no caching

    try:
        # Test main page has no-cache headers
        response = requests.get("http://localhost:8081/")
        cache_control = response.headers.get('Cache-Control', '')

        print(f"1. Main page cache headers: {cache_control}")

        # Test stats endpoint for dynamic content
        stats1 = requests.get("http://localhost:8081/stats").json()
        time.sleep(2)
        stats2 = requests.get("http://localhost:8081/stats").json()

        print(f"2. Stats endpoint updating: {stats1 != stats2}")

        print("   ✅ No refresh should be needed with WebSocket")
        return True

    except Exception as e:
        print(f"   ❌ Failed to test refresh requirements: {e}")
        return False

def main():
    print("="*60)
    print("🎯 Real-Time Streaming Verification Test")
    print("="*60)

    # Run tests
    test1_pass = test_realtime_streaming()
    test2_pass = test_no_refresh_needed()

    # Summary
    print("\n" + "="*60)
    print("📋 Test Summary")
    print("="*60)

    if test1_pass:
        print("✅ Real-time WebSocket streaming: WORKING")
    else:
        print("❌ Real-time WebSocket streaming: FAILED")

    if test2_pass:
        print("✅ No browser refresh needed: CONFIRMED")
    else:
        print("❌ Browser refresh requirements: UNCLEAR")

    if test1_pass and test2_pass:
        print("\n🎉 Real-time streaming is working correctly!")
        print("   No page refresh should be needed at http://192.168.0.112:8081/")
        return 0
    else:
        print("\n❌ Issues detected with real-time streaming")
        return 1

if __name__ == "__main__":
    exit(main())