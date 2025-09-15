#!/usr/bin/env python3
"""
OpenPilot UI Streaming Server - Memory-Only Architecture
No disk storage required - uses shared memory and WebSocket streaming
"""

import os
import time
import json
import socket
import struct
import asyncio
import mmap
import subprocess
import threading
from typing import Optional, Set
from collections import deque
import base64

from flask import Flask, render_template_string, request, jsonify
from flask_sock import Sock
import numpy as np

app = Flask(__name__)
sock = Sock(app)

# Shared memory configuration
SHM_NAME = "/openpilot_ui_frames"
SHM_SIZE = 4 * 1920 * 1080 + 1024  # Frame buffer + metadata

# Frame cache for efficient streaming
class FrameCache:
    def __init__(self, max_frames=3):
        self.frames = deque(maxlen=max_frames)
        self.lock = threading.Lock()
        self.latest_timestamp = 0

    def add_frame(self, timestamp: int, data: bytes):
        with self.lock:
            if timestamp > self.latest_timestamp:
                self.frames.append({
                    'timestamp': timestamp,
                    'data': data,
                    'size': len(data)
                })
                self.latest_timestamp = timestamp

    def get_latest(self):
        with self.lock:
            if self.frames:
                return self.frames[-1]
            return None

    def get_stats(self):
        with self.lock:
            total_size = sum(f['size'] for f in self.frames)
            return {
                'frames_cached': len(self.frames),
                'total_memory_kb': total_size // 1024,
                'latest_timestamp': self.latest_timestamp
            }

frame_cache = FrameCache()
websocket_clients: Set = set()

# Shared memory reader
class SharedMemoryReader:
    def __init__(self):
        self.shm_fd = None
        self.shm_map = None
        self.running = False

    def connect(self):
        """Connect to shared memory created by Qt application"""
        try:
            # Open existing shared memory
            self.shm_fd = os.open(f"/dev/shm{SHM_NAME}", os.O_RDONLY)
            self.shm_map = mmap.mmap(self.shm_fd, SHM_SIZE, mmap.MAP_SHARED, mmap.PROT_READ)
            print(f"Connected to shared memory: {SHM_NAME}")
            return True
        except Exception as e:
            print(f"Failed to connect to shared memory: {e}")
            return False

    def read_frame(self):
        """Read frame from shared memory"""
        if not self.shm_map:
            return None

        try:
            # Read metadata (first 32 bytes)
            self.shm_map.seek(0)
            timestamp = struct.unpack('Q', self.shm_map.read(8))[0]
            width = struct.unpack('I', self.shm_map.read(4))[0]
            height = struct.unpack('I', self.shm_map.read(4))[0]
            size = struct.unpack('I', self.shm_map.read(4))[0]
            format_type = struct.unpack('I', self.shm_map.read(4))[0]
            ready = struct.unpack('?', self.shm_map.read(1))[0]

            if not ready or size == 0:
                return None

            # Skip padding to get to data (aligned at offset 64)
            self.shm_map.seek(64)
            frame_data = self.shm_map.read(size)

            return {
                'timestamp': timestamp,
                'width': width,
                'height': height,
                'size': size,
                'format': 'jpeg' if format_type == 1 else 'raw',
                'data': frame_data
            }
        except Exception as e:
            print(f"Error reading frame: {e}")
            return None

    def start_monitoring(self):
        """Start monitoring shared memory for new frames"""
        self.running = True

        def monitor_loop():
            last_timestamp = 0
            retry_count = 0

            while self.running:
                # Try to connect if not connected
                if not self.shm_map:
                    if self.connect():
                        retry_count = 0
                    else:
                        retry_count += 1
                        if retry_count < 10:
                            time.sleep(2)
                        else:
                            time.sleep(10)  # Back off after many failures
                        continue

                # Read frame
                frame = self.read_frame()
                if frame and frame['timestamp'] > last_timestamp:
                    last_timestamp = frame['timestamp']
                    frame_cache.add_frame(frame['timestamp'], frame['data'])

                    # Notify WebSocket clients
                    asyncio.run(broadcast_frame(frame))

                time.sleep(0.1)  # Check 10 times per second

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

    def close(self):
        """Clean up shared memory connection"""
        self.running = False
        if self.shm_map:
            self.shm_map.close()
        if self.shm_fd:
            os.close(self.shm_fd)

shm_reader = SharedMemoryReader()

async def broadcast_frame(frame):
    """Broadcast frame to all WebSocket clients"""
    if not websocket_clients:
        return

    # Prepare frame message
    message = json.dumps({
        'type': 'frame',
        'timestamp': frame['timestamp'],
        'width': frame['width'],
        'height': frame['height'],
        'format': frame['format'],
        'data': base64.b64encode(frame['data']).decode('utf-8')
    })

    # Send to all clients
    disconnected = set()
    for ws in websocket_clients:
        try:
            await ws.send(message)
        except:
            disconnected.add(ws)

    # Remove disconnected clients
    websocket_clients.difference_update(disconnected)

# Enhanced HTML with WebSocket support
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <title>OpenPilot UI Stream (Memory-Only)</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      margin: 0;
      background: #000;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    #ui-container {
      position: relative;
      max-width: 100%;
      max-height: 100%;
    }
    #ui {
      width: 100%;
      height: auto;
      touch-action: none;
      user-select: none;
      image-rendering: optimizeSpeed;
    }
    .status {
      position: absolute;
      top: 10px;
      left: 10px;
      color: #fff;
      background: rgba(0,0,0,0.8);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 13px;
      display: flex;
      align-items: center;
      gap: 8px;
      backdrop-filter: blur(10px);
    }
    .status-indicator {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #ff4444;
      animation: pulse 2s infinite;
    }
    .status-indicator.connected {
      background: #44ff44;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    .stats {
      position: absolute;
      top: 10px;
      right: 10px;
      color: #fff;
      background: rgba(0,0,0,0.8);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 11px;
      font-family: monospace;
      backdrop-filter: blur(10px);
    }
    .touch-indicator {
      position: absolute;
      width: 40px;
      height: 40px;
      border: 2px solid #00ff00;
      border-radius: 50%;
      background: rgba(0, 255, 0, 0.2);
      pointer-events: none;
      transform: translate(-50%, -50%);
      animation: fadeOut 0.5s ease-out forwards;
    }
    @keyframes fadeOut {
      0% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
      100% { opacity: 0; transform: translate(-50%, -50%) scale(1.5); }
    }
    .no-connection {
      color: #fff;
      text-align: center;
      padding: 20px;
    }
  </style>
</head>
<body>
  <div id="ui-container">
    <canvas id="ui"></canvas>
    <div class="status">
      <div class="status-indicator" id="status-indicator"></div>
      <span id="status-text">Connecting...</span>
    </div>
    <div class="stats" id="stats">
      FPS: 0 | Latency: 0ms | Memory: 0KB
    </div>
  </div>

  <script>
    const canvas = document.getElementById('ui');
    const ctx = canvas.getContext('2d');
    const container = document.getElementById('ui-container');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const stats = document.getElementById('stats');

    let ws = null;
    let reconnectTimer = null;
    let frameCount = 0;
    let lastFrameTime = 0;
    let fps = 0;
    let latency = 0;
    let memoryUsage = 0;

    // FPS calculation
    setInterval(() => {
      fps = frameCount;
      frameCount = 0;
      stats.textContent = `FPS: ${fps} | Latency: ${latency}ms | Memory: ${memoryUsage}KB`;
    }, 1000);

    function connectWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      ws = new WebSocket(`${protocol}//${window.location.host}/stream`);

      ws.onopen = () => {
        console.log('WebSocket connected');
        statusIndicator.classList.add('connected');
        statusText.textContent = 'Connected';
        if (reconnectTimer) {
          clearTimeout(reconnectTimer);
          reconnectTimer = null;
        }
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.type === 'frame') {
          const receiveTime = Date.now();
          latency = Math.round(receiveTime - message.timestamp);

          // Decode and display frame
          const img = new Image();
          img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            frameCount++;
          };
          img.src = 'data:image/jpeg;base64,' + message.data;

          memoryUsage = Math.round(message.data.length * 0.75 / 1024); // Approximate decoded size
        } else if (message.type === 'stats') {
          memoryUsage = message.memory_kb;
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        statusIndicator.classList.remove('connected');
        statusText.textContent = 'Disconnected';

        // Reconnect after 2 seconds
        if (!reconnectTimer) {
          reconnectTimer = setTimeout(connectWebSocket, 2000);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    }

    // Touch/click handling
    function getDeviceCoordinates(clientX, clientY) {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      return {
        x: Math.round((clientX - rect.left) * scaleX),
        y: Math.round((clientY - rect.top) * scaleY)
      };
    }

    function sendInput(eventData) {
      fetch('/input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(eventData)
      }).catch(err => console.error('Input send failed:', err));
    }

    function showTouchIndicator(x, y) {
      const indicator = document.createElement('div');
      indicator.className = 'touch-indicator';
      indicator.style.left = x + 'px';
      indicator.style.top = y + 'px';
      container.appendChild(indicator);
      setTimeout(() => container.removeChild(indicator), 500);
    }

    // Mouse events
    canvas.addEventListener('click', (e) => {
      const coords = getDeviceCoordinates(e.clientX, e.clientY);
      const rect = canvas.getBoundingClientRect();
      showTouchIndicator(e.clientX - rect.left, e.clientY - rect.top);
      sendInput({ type: 'click', x: coords.x, y: coords.y });
    });

    // Touch events
    canvas.addEventListener('touchstart', (e) => {
      e.preventDefault();
      if (e.touches.length === 1) {
        const touch = e.touches[0];
        const coords = getDeviceCoordinates(touch.clientX, touch.clientY);
        sendInput({ type: 'touchstart', x: coords.x, y: coords.y });
      }
    });

    canvas.addEventListener('touchend', (e) => {
      e.preventDefault();
      if (e.changedTouches.length === 1) {
        const touch = e.changedTouches[0];
        const coords = getDeviceCoordinates(touch.clientX, touch.clientY);
        const rect = canvas.getBoundingClientRect();
        showTouchIndicator(touch.clientX - rect.left, touch.clientY - rect.top);
        sendInput({ type: 'tap', x: coords.x, y: coords.y });
      }
    });

    // Scroll handling
    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const coords = getDeviceCoordinates(e.clientX, e.clientY);
      sendInput({
        type: 'scroll',
        x: coords.x,
        y: coords.y,
        deltaY: e.deltaY,
        direction: e.deltaY > 0 ? 'down' : 'up'
      });
    });

    // Start WebSocket connection
    connectWebSocket();
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/input', methods=['POST'])
def handle_input():
    """Handle input events from web client"""
    data = request.get_json()
    event_type = data.get('type', 'click')

    print(f"Received {event_type} event: {data}")

    # Send to Qt application via Unix socket
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect('/tmp/ui_touch_socket')
            message = json.dumps({
                **data,
                'timestamp': time.time()
            })
            sock.send(message.encode())
            return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Failed to send input event: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@sock.route('/stream')
def stream(ws):
    """WebSocket endpoint for frame streaming"""
    websocket_clients.add(ws)
    print(f"Client connected. Total clients: {len(websocket_clients)}")

    try:
        # Send current frame immediately if available
        latest = frame_cache.get_latest()
        if latest:
            ws.send(json.dumps({
                'type': 'frame',
                'timestamp': latest['timestamp'],
                'data': base64.b64encode(latest['data']).decode('utf-8'),
                'width': 2160,  # Default dimensions
                'height': 1080,
                'format': 'jpeg'
            }))

        # Keep connection alive and send stats periodically
        while True:
            time.sleep(5)
            stats = frame_cache.get_stats()
            ws.send(json.dumps({
                'type': 'stats',
                'memory_kb': stats['total_memory_kb'],
                'frames_cached': stats['frames_cached']
            }))
    except:
        pass
    finally:
        websocket_clients.discard(ws)
        print(f"Client disconnected. Total clients: {len(websocket_clients)}")

@app.route('/stats')
def get_stats():
    """Get memory and performance statistics"""
    stats = frame_cache.get_stats()
    stats['websocket_clients'] = len(websocket_clients)
    return jsonify(stats)

def wait_for_wifi(interface="wlan0", timeout=30, delay=2):
    """Wait for network connection"""
    print("Waiting for network connection...")
    for _ in range(timeout // delay):
        try:
            result = subprocess.run(["ip", "route", "show", "dev", interface],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if result.stdout.strip():
                print("Network is up.")
                return True
        except:
            pass
        time.sleep(delay)
    print("Network not detected, continuing anyway...")
    return False

if __name__ == '__main__':
    wait_for_wifi()

    print("Starting memory-only streaming server...")
    print("No disk storage required - using shared memory")

    # Start shared memory monitoring
    shm_reader.start_monitoring()

    # Run Flask with WebSocket support
    try:
        app.run(host='0.0.0.0', port=8081, debug=False)
    finally:
        shm_reader.close()