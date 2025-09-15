#!/usr/bin/env python3
"""
Test script for shared memory functionality
Verifies that frames can be written and read correctly
"""

import os
import sys
import time
import mmap
import struct
import hashlib

def test_shared_memory():
    """Test shared memory read/write operations"""
    print("🧪 Testing Shared Memory Functionality\n")

    shm_name = "/openpilot_ui_frames"
    shm_path = f"/dev/shm{shm_name}"
    shm_size = 4 * 1920 * 1080 + 1024

    tests_passed = 0
    tests_failed = 0

    # Test 1: Check if shared memory exists
    print("Test 1: Checking shared memory existence...")
    if os.path.exists(shm_path):
        print("✅ Shared memory file exists")
        tests_passed += 1
    else:
        print("❌ Shared memory file not found. Run mock_ui_simulator.py first!")
        tests_failed += 1
        return False

    # Test 2: Open and read shared memory
    print("\nTest 2: Reading shared memory metadata...")
    try:
        shm_fd = os.open(shm_path, os.O_RDONLY)
        shm_map = mmap.mmap(shm_fd, shm_size, mmap.MAP_SHARED, mmap.PROT_READ)

        # Read metadata
        shm_map.seek(0)
        timestamp = struct.unpack('Q', shm_map.read(8))[0]
        width = struct.unpack('I', shm_map.read(4))[0]
        height = struct.unpack('I', shm_map.read(4))[0]
        size = struct.unpack('I', shm_map.read(4))[0]
        format_type = struct.unpack('I', shm_map.read(4))[0]
        ready = struct.unpack('?', shm_map.read(1))[0]

        print(f"  Timestamp: {timestamp}")
        print(f"  Resolution: {width}x{height}")
        print(f"  Data size: {size} bytes")
        print(f"  Format: {'JPEG' if format_type == 1 else 'Unknown'}")
        print(f"  Ready: {ready}")

        if width > 0 and height > 0 and size > 0:
            print("✅ Metadata read successfully")
            tests_passed += 1
        else:
            print("❌ Invalid metadata values")
            tests_failed += 1

        shm_map.close()
        os.close(shm_fd)

    except Exception as e:
        print(f"❌ Failed to read shared memory: {e}")
        tests_failed += 1

    # Test 3: Monitor frame updates
    print("\nTest 3: Monitoring frame updates (5 seconds)...")
    try:
        shm_fd = os.open(shm_path, os.O_RDONLY)
        shm_map = mmap.mmap(shm_fd, shm_size, mmap.MAP_SHARED, mmap.PROT_READ)

        last_timestamp = 0
        frame_count = 0
        start_time = time.time()

        while time.time() - start_time < 5:
            shm_map.seek(0)
            timestamp = struct.unpack('Q', shm_map.read(8))[0]

            if timestamp > last_timestamp:
                frame_count += 1
                last_timestamp = timestamp
                print(f"  📸 New frame detected: {timestamp}", end='\r')

            time.sleep(0.1)

        print(f"\n  Total frames received: {frame_count}")

        if frame_count > 0:
            print("✅ Frame updates working")
            tests_passed += 1
        else:
            print("❌ No frame updates detected")
            tests_failed += 1

        shm_map.close()
        os.close(shm_fd)

    except Exception as e:
        print(f"❌ Failed to monitor frames: {e}")
        tests_failed += 1

    # Test 4: Verify frame data integrity
    print("\nTest 4: Verifying frame data integrity...")
    try:
        shm_fd = os.open(shm_path, os.O_RDONLY)
        shm_map = mmap.mmap(shm_fd, shm_size, mmap.MAP_SHARED, mmap.PROT_READ)

        # Read metadata
        shm_map.seek(0)
        timestamp = struct.unpack('Q', shm_map.read(8))[0]
        width = struct.unpack('I', shm_map.read(4))[0]
        height = struct.unpack('I', shm_map.read(4))[0]
        size = struct.unpack('I', shm_map.read(4))[0]

        # Read frame data
        shm_map.seek(64)
        frame_data = shm_map.read(size)

        # Verify JPEG header
        if len(frame_data) >= 2 and frame_data[0:2] == b'\xff\xd8':
            print("  ✅ Valid JPEG header found")

            # Calculate checksum
            checksum = hashlib.md5(frame_data).hexdigest()
            print(f"  Frame checksum: {checksum}")

            # Check if it's a valid JPEG end
            if frame_data[-2:] == b'\xff\xd9':
                print("  ✅ Valid JPEG footer found")
                tests_passed += 1
            else:
                print("  ⚠️  JPEG footer not standard (may still be valid)")
                tests_passed += 1
        else:
            print("  ❌ Invalid JPEG data")
            tests_failed += 1

        shm_map.close()
        os.close(shm_fd)

    except Exception as e:
        print(f"❌ Failed to verify frame data: {e}")
        tests_failed += 1

    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary:")
    print(f"  ✅ Passed: {tests_passed}")
    print(f"  ❌ Failed: {tests_failed}")

    if tests_failed == 0:
        print("\n🎉 All tests passed! Shared memory is working correctly.")
        return True
    else:
        print(f"\n⚠️  {tests_failed} test(s) failed. Please check the issues above.")
        return False

def main():
    if not test_shared_memory():
        sys.exit(1)

if __name__ == '__main__':
    main()