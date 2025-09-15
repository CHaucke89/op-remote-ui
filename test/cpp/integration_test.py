#!/usr/bin/env python3
"""
C++ to Python integration test
Tests the complete pipeline: Mock Qt UI → C++ FrameStreamer → Python Server → Browser
"""

import os
import sys
import time
import subprocess
import threading
import requests
import json
import signal
from pathlib import Path

class CppPythonIntegrationTest:
    def __init__(self):
        self.processes = []
        self.test_results = []

    def start_cpp_application(self):
        """Start the C++ test application"""
        print("1. Starting C++ Qt application...")

        # Build if necessary
        build_dir = Path("test/cpp/build")
        if not build_dir.exists() or not (build_dir / "openpilot_ui_test").exists():
            print("   Building C++ test application...")
            result = subprocess.run(["bash", "test/cpp/build.sh"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"   ❌ Build failed: {result.stderr}")
                return False

        # Start the application
        cpp_process = subprocess.Popen(
            ["./openpilot_ui_test"],
            cwd="test/cpp/build",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        self.processes.append(("cpp_app", cpp_process))

        # Wait for initialization
        time.sleep(3)

        # Check if process is running
        if cpp_process.poll() is not None:
            stdout, stderr = cpp_process.communicate()
            print(f"   ❌ C++ application failed to start:")
            print(f"   STDOUT: {stdout}")
            print(f"   STDERR: {stderr}")
            return False

        print("   ✅ C++ application started")
        return True

    def verify_shared_memory(self):
        """Verify shared memory was created by C++ application"""
        print("2. Verifying shared memory...")

        shm_path = "/dev/shm/openpilot_ui_frames"
        timeout = 10
        start_time = time.time()

        while time.time() - start_time < timeout:
            if os.path.exists(shm_path):
                size = os.path.getsize(shm_path)
                print(f"   ✅ Shared memory found: {size} bytes")
                return True
            time.sleep(0.5)

        print(f"   ❌ Shared memory not found after {timeout}s")
        return False

    def start_python_server(self):
        """Start the Python streaming server"""
        print("3. Starting Python streaming server...")

        server_process = subprocess.Popen(
            ["python3", "stream_server_fixed.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        self.processes.append(("python_server", server_process))

        # Wait for server to start
        time.sleep(3)

        # Check if server is responding
        try:
            response = requests.get("http://localhost:8081/stats", timeout=5)
            if response.status_code == 200:
                print("   ✅ Python server started and responding")
                return True
            else:
                print(f"   ❌ Server returned status {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"   ❌ Server not responding: {e}")
            return False

    def test_frame_streaming(self):
        """Test that frames are being streamed from C++ to Python"""
        print("4. Testing frame streaming...")

        # Check stats endpoint for frame data
        for attempt in range(10):
            try:
                response = requests.get("http://localhost:8081/stats", timeout=2)
                if response.status_code == 200:
                    stats = response.json()
                    frames_cached = stats.get('frames_cached', 0)
                    memory_kb = stats.get('total_memory_kb', 0)

                    if frames_cached > 0:
                        print(f"   ✅ Frames detected: {frames_cached} cached, {memory_kb}KB memory")
                        return True

                print(f"   Attempt {attempt + 1}: No frames yet...")
                time.sleep(1)

            except Exception as e:
                print(f"   ❌ Error checking stats: {e}")

        print("   ❌ No frames detected after 10 seconds")
        return False

    def test_web_interface(self):
        """Test web interface accessibility"""
        print("5. Testing web interface...")

        try:
            response = requests.get("http://localhost:8081/", timeout=5)
            if response.status_code == 200 and "OpenPilot UI Stream" in response.text:
                print("   ✅ Web interface accessible")
                return True
            else:
                print(f"   ❌ Web interface issue: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Web interface error: {e}")
            return False

    def test_input_handling(self):
        """Test input event processing"""
        print("6. Testing input event handling...")

        test_event = {
            "type": "click",
            "x": 500,
            "y": 400,
            "timestamp": time.time()
        }

        try:
            response = requests.post(
                "http://localhost:8081/input",
                json=test_event,
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    print("   ✅ Input events processed successfully")
                    return True
                else:
                    print(f"   ❌ Input processing failed: {result}")
                    return False
            else:
                print(f"   ❌ Input endpoint returned: {response.status_code}")
                return False

        except Exception as e:
            print(f"   ❌ Input test error: {e}")
            return False

    def monitor_performance(self, duration=10):
        """Monitor performance for a period"""
        print(f"7. Monitoring performance for {duration}s...")

        start_time = time.time()
        frame_counts = []
        memory_usage = []

        while time.time() - start_time < duration:
            try:
                response = requests.get("http://localhost:8081/stats", timeout=1)
                if response.status_code == 200:
                    stats = response.json()
                    frame_counts.append(stats.get('frames_cached', 0))
                    memory_usage.append(stats.get('total_memory_kb', 0))

                time.sleep(1)

            except Exception as e:
                print(f"   ⚠️ Performance monitoring error: {e}")

        if frame_counts and memory_usage:
            avg_frames = sum(frame_counts) / len(frame_counts)
            max_memory = max(memory_usage)
            print(f"   ✅ Performance: {avg_frames:.1f} avg frames, {max_memory}KB max memory")
            return max_memory < 10000  # Less than 10MB
        else:
            print("   ❌ No performance data collected")
            return False

    def cleanup(self):
        """Clean up all processes"""
        print("\n8. Cleaning up...")

        for name, process in self.processes:
            if process.poll() is None:
                print(f"   Terminating {name}...")
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

        # Clean up shared memory
        shm_path = "/dev/shm/openpilot_ui_frames"
        if os.path.exists(shm_path):
            try:
                os.unlink(shm_path)
                print("   ✅ Shared memory cleaned up")
            except Exception as e:
                print(f"   ⚠️ Failed to clean shared memory: {e}")

    def run_integration_test(self):
        """Run complete integration test"""
        print("="*60)
        print("🔗 C++ to Python Integration Test")
        print("="*60)

        tests = [
            ("C++ Application Start", self.start_cpp_application),
            ("Shared Memory Creation", self.verify_shared_memory),
            ("Python Server Start", self.start_python_server),
            ("Frame Streaming", self.test_frame_streaming),
            ("Web Interface", self.test_web_interface),
            ("Input Handling", self.test_input_handling),
            ("Performance Monitoring", lambda: self.monitor_performance(10))
        ]

        passed = 0
        failed = 0

        try:
            for test_name, test_func in tests:
                result = test_func()
                if result:
                    passed += 1
                    self.test_results.append((test_name, "PASS"))
                else:
                    failed += 1
                    self.test_results.append((test_name, "FAIL"))

        finally:
            self.cleanup()

        # Print summary
        print("\n" + "="*60)
        print("📊 Integration Test Results")
        print("="*60)

        for test_name, result in self.test_results:
            emoji = "✅" if result == "PASS" else "❌"
            print(f"{emoji} {test_name}: {result}")

        print(f"\nTotal: {len(self.test_results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")

        if failed == 0:
            print("\n🎉 All integration tests PASSED!")
            print("C++ components work correctly with Python server!")
            return 0
        else:
            print(f"\n❌ {failed} test(s) failed")
            return 1

def main():
    # Check if we're in the right directory
    if not os.path.exists("frame_streamer.h") or not os.path.exists("stream_server_fixed.py"):
        print("❌ Please run from the project root directory")
        print("Expected files: frame_streamer.h, stream_server_fixed.py")
        return 1

    test = CppPythonIntegrationTest()
    return test.run_integration_test()

if __name__ == "__main__":
    sys.exit(main())