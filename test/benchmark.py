#!/usr/bin/env python3
"""
Performance benchmark script - Compare old vs new architecture
"""

import os
import time
import psutil
import subprocess
import tempfile
import shutil
from datetime import datetime
import json

class PerformanceBenchmark:
    def __init__(self):
        self.results = {
            "disk_based": {},
            "memory_based": {},
            "comparison": {}
        }

    def measure_disk_based_approach(self, duration=60):
        """Benchmark the original disk-based approach"""
        print("\n📊 Benchmarking Disk-Based Approach")
        print("-" * 40)

        temp_dir = tempfile.mkdtemp(prefix="ui_frames_")
        print(f"Using temp directory: {temp_dir}")

        start_time = time.time()
        frames_written = 0
        total_size = 0
        latencies = []

        try:
            while time.time() - start_time < duration:
                frame_start = time.time()

                # Simulate frame capture and save (similar to original approach)
                filename = os.path.join(temp_dir, f"ui_frame_{int(time.time()*1000)}.png")

                # Create a dummy PNG file (2MB average)
                dummy_data = os.urandom(2 * 1024 * 1024)
                with open(filename, 'wb') as f:
                    f.write(dummy_data)

                frames_written += 1
                total_size += len(dummy_data)

                # Simulate client reading the file
                read_start = time.time()
                with open(filename, 'rb') as f:
                    _ = f.read()
                read_latency = (time.time() - read_start) * 1000

                latencies.append(read_latency)

                # Wait for next frame interval (500ms)
                elapsed = time.time() - frame_start
                if elapsed < 0.5:
                    time.sleep(0.5 - elapsed)

                print(f"  Frames: {frames_written}, Disk: {total_size/1024/1024:.1f}MB", end='\r')

        finally:
            # Cleanup
            file_count = len(os.listdir(temp_dir))
            shutil.rmtree(temp_dir)

        elapsed_time = time.time() - start_time
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        self.results["disk_based"] = {
            "duration": elapsed_time,
            "frames_written": frames_written,
            "total_disk_mb": total_size / 1024 / 1024,
            "disk_mb_per_hour": (total_size / 1024 / 1024) * (3600 / elapsed_time),
            "avg_latency_ms": avg_latency,
            "max_latency_ms": max(latencies) if latencies else 0,
            "files_created": file_count,
            "fps": frames_written / elapsed_time
        }

        print(f"\n✅ Disk-based benchmark complete")
        print(f"   Total disk usage: {self.results['disk_based']['total_disk_mb']:.1f} MB")
        print(f"   Projected daily: {self.results['disk_based']['disk_mb_per_hour'] * 24:.1f} MB")

    def measure_memory_based_approach(self, duration=60):
        """Benchmark the new memory-based approach"""
        print("\n📊 Benchmarking Memory-Based Approach")
        print("-" * 40)

        # Start mock UI simulator
        simulator_process = subprocess.Popen(
            ["python3", "test/mock_ui_simulator.py", "--fps", "2"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        time.sleep(2)  # Let simulator initialize

        shm_path = "/dev/shm/openpilot_ui_frames"
        start_time = time.time()
        frames_read = 0
        latencies = []
        memory_samples = []

        try:
            last_timestamp = 0

            while time.time() - start_time < duration:
                frame_start = time.time()

                # Read from shared memory
                if os.path.exists(shm_path):
                    with open(shm_path, 'rb') as f:
                        # Read timestamp
                        timestamp_bytes = f.read(8)
                        if len(timestamp_bytes) == 8:
                            import struct
                            timestamp = struct.unpack('Q', timestamp_bytes)[0]

                            if timestamp > last_timestamp:
                                frames_read += 1
                                last_timestamp = timestamp

                                # Calculate latency
                                current_time = int(time.time() * 1000)
                                latency = current_time - timestamp
                                latencies.append(latency)

                # Sample memory usage
                memory_kb = os.path.getsize(shm_path) / 1024 if os.path.exists(shm_path) else 0
                memory_samples.append(memory_kb)

                print(f"  Frames: {frames_read}, Memory: {memory_kb:.1f}KB", end='\r')

                time.sleep(0.1)

        finally:
            # Stop simulator
            simulator_process.terminate()
            simulator_process.wait()

        elapsed_time = time.time() - start_time
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        avg_memory = sum(memory_samples) / len(memory_samples) if memory_samples else 0

        self.results["memory_based"] = {
            "duration": elapsed_time,
            "frames_read": frames_read,
            "avg_memory_kb": avg_memory,
            "max_memory_kb": max(memory_samples) if memory_samples else 0,
            "avg_latency_ms": avg_latency,
            "max_latency_ms": max(latencies) if latencies else 0,
            "disk_usage_mb": 0,  # Zero disk usage!
            "fps": frames_read / elapsed_time
        }

        print(f"\n✅ Memory-based benchmark complete")
        print(f"   Avg memory usage: {self.results['memory_based']['avg_memory_kb']:.1f} KB")
        print(f"   Zero disk usage!")

    def calculate_comparison(self):
        """Calculate comparison metrics"""
        disk = self.results["disk_based"]
        memory = self.results["memory_based"]

        if disk and memory:
            self.results["comparison"] = {
                "disk_reduction_percent": 100,  # 100% reduction (zero disk usage)
                "latency_improvement_factor": disk["avg_latency_ms"] / memory["avg_latency_ms"] if memory["avg_latency_ms"] > 0 else 0,
                "disk_saved_per_day_gb": (disk["disk_mb_per_hour"] * 24) / 1024,
                "memory_overhead_mb": memory["max_memory_kb"] / 1024
            }

    def run_benchmark(self, duration=30):
        """Run complete benchmark suite"""
        print("="*60)
        print("🏁 OpenPilot UI Streaming - Performance Benchmark")
        print("="*60)
        print(f"Benchmark duration: {duration} seconds per test")

        # Run benchmarks
        self.measure_disk_based_approach(duration)
        self.measure_memory_based_approach(duration)
        self.calculate_comparison()

        # Print results
        self.print_results()
        self.save_results()

    def print_results(self):
        """Print benchmark results"""
        print("\n" + "="*60)
        print("📊 Benchmark Results")
        print("="*60)

        print("\n🗄️  Disk-Based Approach:")
        print(f"   Frames processed: {self.results['disk_based']['frames_written']}")
        print(f"   Total disk usage: {self.results['disk_based']['total_disk_mb']:.1f} MB")
        print(f"   Projected daily: {self.results['disk_based']['disk_mb_per_hour'] * 24:.1f} MB")
        print(f"   Average latency: {self.results['disk_based']['avg_latency_ms']:.1f} ms")
        print(f"   FPS: {self.results['disk_based']['fps']:.2f}")

        print("\n💾 Memory-Based Approach:")
        print(f"   Frames processed: {self.results['memory_based']['frames_read']}")
        print(f"   Disk usage: 0 MB (ZERO!)")
        print(f"   Average memory: {self.results['memory_based']['avg_memory_kb']:.1f} KB")
        print(f"   Average latency: {self.results['memory_based']['avg_latency_ms']:.1f} ms")
        print(f"   FPS: {self.results['memory_based']['fps']:.2f}")

        if self.results.get("comparison"):
            print("\n🎯 Improvement Summary:")
            comp = self.results["comparison"]
            print(f"   ✅ Disk space saved: {comp['disk_reduction_percent']}%")
            print(f"   ✅ Latency improvement: {comp['latency_improvement_factor']:.1f}x faster")
            print(f"   ✅ Daily disk savings: {comp['disk_saved_per_day_gb']:.1f} GB")
            print(f"   ✅ Memory overhead: Only {comp['memory_overhead_mb']:.1f} MB")

    def save_results(self):
        """Save results to JSON file"""
        filename = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(f"test/{filename}", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to test/{filename}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Performance Benchmark')
    parser.add_argument('--duration', type=int, default=30,
                       help='Duration of each benchmark in seconds')
    args = parser.parse_args()

    benchmark = PerformanceBenchmark()
    benchmark.run_benchmark(args.duration)

if __name__ == "__main__":
    main()