#!/usr/bin/env python3
"""
Mock Qt UI Simulator - Simulates the Qt application's frame generation
for testing the streaming server without actual Qt/C++ compilation
"""

import os
import sys
import time
import mmap
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import threading
import argparse

class MockUISimulator:
    def __init__(self, width=2160, height=1080, fps=2):
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_interval = 1.0 / fps
        self.running = False
        self.frame_count = 0

        # Shared memory setup
        self.shm_name = "/openpilot_ui_frames"
        self.shm_size = 4 * 1920 * 1080 + 1024
        self.shm_fd = None
        self.shm_map = None

    def init_shared_memory(self):
        """Initialize shared memory for frame sharing"""
        shm_path = f"/dev/shm{self.shm_name}"

        # Create or open shared memory
        try:
            # Remove existing file if present
            if os.path.exists(shm_path):
                os.unlink(shm_path)

            # Create new shared memory file
            self.shm_fd = os.open(shm_path, os.O_CREAT | os.O_RDWR, 0o666)

            # Set size
            os.truncate(self.shm_fd, self.shm_size)

            # Map memory
            self.shm_map = mmap.mmap(self.shm_fd, self.shm_size, mmap.MAP_SHARED, mmap.PROT_WRITE)

            print(f"✅ Shared memory initialized: {shm_path}")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize shared memory: {e}")
            return False

    def generate_mock_frame(self):
        """Generate a mock UI frame with timestamp and info"""
        # Create image with gradient background
        img = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(img)

        # Gradient background
        for y in range(self.height):
            color_value = int(255 * (y / self.height))
            color = (color_value // 2, color_value // 3, color_value)
            draw.rectangle([(0, y), (self.width, y+1)], fill=color)

        # Add UI elements
        # Top bar
        draw.rectangle([(0, 0), (self.width, 100)], fill=(20, 20, 30))

        # Speed indicator
        speed = 35 + (self.frame_count % 30)
        draw.rectangle([(100, 200), (400, 500)], fill=(0, 50, 100))
        draw.text((150, 300), f"{speed} MPH", fill=(255, 255, 255))

        # Status text
        draw.text((50, 30), f"OpenPilot UI Simulator", fill=(255, 255, 255))
        draw.text((50, 60), f"Frame: {self.frame_count}", fill=(200, 200, 200))

        # Timestamp
        timestamp = time.strftime("%H:%M:%S")
        draw.text((self.width - 200, 30), timestamp, fill=(255, 255, 255))

        # Lane lines simulation
        for x in range(600, 1600, 200):
            y_offset = (self.frame_count * 10) % 100
            draw.rectangle([(x, 600 + y_offset), (x + 50, 700 + y_offset)],
                          fill=(255, 255, 0))

        # Alert box (occasionally)
        if self.frame_count % 20 < 5:
            draw.rectangle([(self.width//2 - 200, 800),
                          (self.width//2 + 200, 900)],
                          fill=(255, 100, 0))
            draw.text((self.width//2 - 100, 830), "BRAKE!",
                     fill=(255, 255, 255))

        return img

    def write_frame_to_shared_memory(self, image):
        """Write frame to shared memory in JPEG format"""
        if not self.shm_map:
            return False

        try:
            # Convert to JPEG
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            jpeg_data = buffer.getvalue()

            # Check size
            if len(jpeg_data) > self.shm_size - 64:
                print(f"⚠️  Frame too large: {len(jpeg_data)} bytes")
                return False

            # Write metadata
            timestamp = int(time.time() * 1000)  # milliseconds

            self.shm_map.seek(0)
            self.shm_map.write(struct.pack('Q', timestamp))  # timestamp
            self.shm_map.write(struct.pack('I', self.width))  # width
            self.shm_map.write(struct.pack('I', self.height))  # height
            self.shm_map.write(struct.pack('I', len(jpeg_data)))  # size
            self.shm_map.write(struct.pack('I', 1))  # format (1=JPEG)
            self.shm_map.write(struct.pack('?', True))  # ready flag

            # Pad to offset 64
            self.shm_map.seek(64)

            # Write JPEG data
            self.shm_map.write(jpeg_data)

            return True

        except Exception as e:
            print(f"❌ Error writing frame: {e}")
            return False

    def run_simulation(self):
        """Main simulation loop"""
        print(f"🚀 Starting UI simulation: {self.width}x{self.height} @ {self.fps} FPS")

        self.running = True
        last_frame_time = time.time()

        while self.running:
            current_time = time.time()

            # Check if it's time for next frame
            if current_time - last_frame_time >= self.frame_interval:
                # Generate and write frame
                frame = self.generate_mock_frame()

                if self.write_frame_to_shared_memory(frame):
                    self.frame_count += 1
                    print(f"📸 Frame {self.frame_count} written to shared memory", end='\r')

                last_frame_time = current_time

            # Small sleep to prevent CPU spinning
            time.sleep(0.01)

    def start(self):
        """Start the simulator in a thread"""
        if not self.init_shared_memory():
            return False

        thread = threading.Thread(target=self.run_simulation, daemon=True)
        thread.start()
        return True

    def stop(self):
        """Stop the simulator"""
        self.running = False

        # Cleanup shared memory
        if self.shm_map:
            self.shm_map.close()
        if self.shm_fd:
            os.close(self.shm_fd)

        # Remove shared memory file
        shm_path = f"/dev/shm{self.shm_name}"
        if os.path.exists(shm_path):
            os.unlink(shm_path)

        print("\n✅ Simulator stopped and cleaned up")

def main():
    parser = argparse.ArgumentParser(description='Mock Qt UI Simulator for Testing')
    parser.add_argument('--width', type=int, default=2160, help='Frame width')
    parser.add_argument('--height', type=int, default=1080, help='Frame height')
    parser.add_argument('--fps', type=int, default=2, help='Frames per second')
    parser.add_argument('--duration', type=int, default=0,
                       help='Run duration in seconds (0=infinite)')

    args = parser.parse_args()

    simulator = MockUISimulator(args.width, args.height, args.fps)

    if not simulator.start():
        sys.exit(1)

    try:
        if args.duration > 0:
            print(f"⏱️  Running for {args.duration} seconds...")
            time.sleep(args.duration)
        else:
            print("🔄 Running indefinitely. Press Ctrl+C to stop...")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n⛔ Interrupted by user")
    finally:
        simulator.stop()

if __name__ == '__main__':
    main()