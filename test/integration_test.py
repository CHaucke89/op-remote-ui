#!/usr/bin/env python3
"""
Integration test suite for the optimized streaming solution
Tests the complete pipeline: UI simulation → Shared Memory → Server → WebSocket → Client
"""

import sys
import time
import json
import requests
import websocket
import threading
import subprocess
from datetime import datetime

class IntegrationTester:
    def __init__(self, server_url="http://localhost:8081"):
        self.server_url = server_url
        self.ws_url = server_url.replace("http", "ws") + "/stream"
        self.results = []
        self.frames_received = 0
        self.total_latency = 0

    def test_server_health(self):
        """Test 1: Server health check"""
        print("\n🧪 Test 1: Server Health Check")
        try:
            response = requests.get(f"{self.server_url}/stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                print(f"  ✅ Server is healthy")
                print(f"     Frames cached: {stats.get('frames_cached', 0)}")
                print(f"     Memory usage: {stats.get('total_memory_kb', 0)} KB")
                self.results.append(("Server Health", "PASS"))
                return True
            else:
                print(f"  ❌ Server returned status {response.status_code}")
                self.results.append(("Server Health", "FAIL"))
                return False
        except Exception as e:
            print(f"  ❌ Failed to connect to server: {e}")
            self.results.append(("Server Health", "FAIL"))
            return False

    def test_web_interface(self):
        """Test 2: Web interface availability"""
        print("\n🧪 Test 2: Web Interface")
        try:
            response = requests.get(self.server_url, timeout=5)
            if response.status_code == 200 and "OpenPilot UI Stream" in response.text:
                print(f"  ✅ Web interface is accessible")
                self.results.append(("Web Interface", "PASS"))
                return True
            else:
                print(f"  ❌ Web interface not working properly")
                self.results.append(("Web Interface", "FAIL"))
                return False
        except Exception as e:
            print(f"  ❌ Failed to access web interface: {e}")
            self.results.append(("Web Interface", "FAIL"))
            return False

    def test_websocket_streaming(self):
        """Test 3: WebSocket streaming"""
        print("\n🧪 Test 3: WebSocket Streaming")

        def on_message(ws, message):
            try:
                data = json.loads(message)
                if data.get('type') == 'frame':
                    self.frames_received += 1
                    # Calculate latency
                    current_time = int(time.time() * 1000)
                    frame_time = data.get('timestamp', current_time)
                    latency = current_time - frame_time
                    self.total_latency += latency
                    print(f"  📸 Frame {self.frames_received} received (latency: {latency}ms)", end='\r')
            except Exception as e:
                print(f"  ⚠️  Error processing message: {e}")

        def on_error(ws, error):
            print(f"  ❌ WebSocket error: {error}")

        def on_close(ws, close_status_code, close_msg):
            print(f"\n  WebSocket closed")

        try:
            ws = websocket.WebSocketApp(self.ws_url,
                                       on_message=on_message,
                                       on_error=on_error,
                                       on_close=on_close)

            # Run WebSocket for 10 seconds
            ws_thread = threading.Thread(target=lambda: ws.run_forever())
            ws_thread.daemon = True
            ws_thread.start()

            time.sleep(10)
            ws.close()

            if self.frames_received > 0:
                avg_latency = self.total_latency / self.frames_received
                print(f"\n  ✅ Received {self.frames_received} frames")
                print(f"     Average latency: {avg_latency:.1f}ms")
                self.results.append(("WebSocket Streaming", "PASS"))
                return True
            else:
                print(f"\n  ❌ No frames received via WebSocket")
                self.results.append(("WebSocket Streaming", "FAIL"))
                return False

        except Exception as e:
            print(f"  ❌ WebSocket test failed: {e}")
            self.results.append(("WebSocket Streaming", "FAIL"))
            return False

    def test_input_handling(self):
        """Test 4: Input event handling"""
        print("\n🧪 Test 4: Input Event Handling")
        test_events = [
            {"type": "click", "x": 100, "y": 200},
            {"type": "scroll", "x": 500, "y": 500, "deltaY": 10},
            {"type": "drag", "x": 300, "y": 400, "startX": 200, "startY": 300}
        ]

        passed = 0
        for event in test_events:
            try:
                response = requests.post(f"{self.server_url}/input",
                                       json=event,
                                       timeout=2)
                if response.status_code == 200:
                    print(f"  ✅ {event['type']} event handled successfully")
                    passed += 1
                else:
                    print(f"  ❌ {event['type']} event failed: {response.status_code}")
            except Exception as e:
                print(f"  ❌ Failed to send {event['type']} event: {e}")

        if passed == len(test_events):
            self.results.append(("Input Handling", "PASS"))
            return True
        else:
            self.results.append(("Input Handling", "PARTIAL"))
            return False

    def test_memory_usage(self):
        """Test 5: Memory usage monitoring"""
        print("\n🧪 Test 5: Memory Usage Check")

        memory_samples = []
        for i in range(5):
            try:
                response = requests.get(f"{self.server_url}/stats", timeout=2)
                if response.status_code == 200:
                    stats = response.json()
                    memory_kb = stats.get('total_memory_kb', 0)
                    memory_samples.append(memory_kb)
                    print(f"  Sample {i+1}: {memory_kb} KB", end='\r')
                time.sleep(2)
            except Exception as e:
                print(f"  ⚠️  Failed to get memory stats: {e}")

        if memory_samples:
            avg_memory = sum(memory_samples) / len(memory_samples)
            max_memory = max(memory_samples)
            print(f"\n  Average memory: {avg_memory:.1f} KB")
            print(f"  Maximum memory: {max_memory} KB")

            # Check if memory is within expected bounds (< 10MB)
            if max_memory < 10000:
                print(f"  ✅ Memory usage is within bounds")
                self.results.append(("Memory Usage", "PASS"))
                return True
            else:
                print(f"  ⚠️  Memory usage higher than expected")
                self.results.append(("Memory Usage", "WARN"))
                return True
        else:
            print(f"  ❌ Could not measure memory usage")
            self.results.append(("Memory Usage", "FAIL"))
            return False

    def run_all_tests(self):
        """Run all integration tests"""
        print("="*60)
        print("🚀 OpenPilot UI Streaming - Integration Test Suite")
        print("="*60)

        # Wait for services to be ready
        print("\n⏳ Waiting for services to initialize...")
        time.sleep(3)

        # Run tests
        self.test_server_health()
        self.test_web_interface()
        self.test_websocket_streaming()
        self.test_input_handling()
        self.test_memory_usage()

        # Print summary
        print("\n" + "="*60)
        print("📊 Test Results Summary")
        print("="*60)

        pass_count = sum(1 for _, result in self.results if result == "PASS")
        fail_count = sum(1 for _, result in self.results if result == "FAIL")
        warn_count = sum(1 for _, result in self.results if result == "WARN")

        for test_name, result in self.results:
            emoji = "✅" if result == "PASS" else "❌" if result == "FAIL" else "⚠️"
            print(f"  {emoji} {test_name}: {result}")

        print("\n" + "-"*60)
        print(f"Total: {len(self.results)} tests")
        print(f"Passed: {pass_count}")
        print(f"Failed: {fail_count}")
        print(f"Warnings: {warn_count}")

        if fail_count == 0:
            print("\n🎉 All critical tests passed!")
            return 0
        else:
            print(f"\n❌ {fail_count} test(s) failed")
            return 1

def main():
    tester = IntegrationTester()
    exit_code = tester.run_all_tests()

    # Save results to file
    with open("/app/test-results/integration-test-results.txt", "w") as f:
        f.write(f"Integration Test Results - {datetime.now()}\n")
        f.write("="*60 + "\n")
        for test_name, result in tester.results:
            f.write(f"{test_name}: {result}\n")

    sys.exit(exit_code)

if __name__ == "__main__":
    main()