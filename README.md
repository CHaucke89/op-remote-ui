# OpenPilot UI Real-Time Web Streaming

This project enables real-time streaming of the openpilot UI to a web browser with interactive control. It captures UI frames at 10 FPS using shared memory and provides touch, drag, and scroll functionality via a WebSocket-based web interface.

See: https://www.youtube.com/watch?v=7bqbqOVJRFc

## Overview

This implementation uses a sophisticated memory-based streaming architecture:

1. **Frame Capture** (C++): Qt application captures frames at 10 FPS and writes compressed JPEG data to shared memory
2. **Stream Server** (Python): Reads shared memory continuously and broadcasts frames to connected WebSocket clients
3. **Web Interface** (HTML/JS): Displays frames on HTML5 Canvas with real-time status and FPS monitoring
4. **Input Injection** (C++): Receives touch/click/scroll events from the browser via Unix socket and injects them into the Qt application

### Technical Architecture

```
Qt Application (MainWindow)
    ↓ [10 FPS capture]
FrameStreamer (C++)
    ↓ [Shared Memory: /dev/shm/openpilot_ui_frames]
StreamServer (Python)
    ↓ [WebSocket on port 8081]
Web Browser (HTML5 Canvas)
    ↓ [Input events via WebSocket]
TouchInjector (C++) → Qt Application
```

### Key Features

- **10 FPS streaming** - Smooth real-time frame updates
- **Zero-disk storage** - All frames stay in memory (no disk writes)
- **WebSocket-based** - Low-latency bidirectional communication
- **Shared memory IPC** - Efficient C++ to Python communication using packed binary structs
- **Interactive control** - Full touch, click, drag, and scroll support
- **Auto-reconnection** - Browser automatically reconnects on network interruptions
- **Status monitoring** - Real-time FPS, latency, and connection status display

## Components

### 1. FrameStreamer (C++)
**Files**: `frame_streamer.h`, `frame_streamer.cc`

Captures the Qt MainWindow and writes compressed frames to shared memory:
- Uses `QPixmap::grab()` for screen capture
- Encodes frames as JPEG (85% quality)
- Writes to shared memory structure with metadata (timestamp, dimensions, format)
- Triggered by QTimer every 100ms (10 FPS)
- Thread-safe with mutex protection

### 2. TouchInjector (C++)
**Files**: `touch_injector.h`, `touch_injector.cc`

Listens for input events and injects them into the Qt application:
- Listens on Unix domain socket: `/tmp/ui_touch_socket`
- Receives JSON-formatted input events
- Supports: click, drag, scroll, tap, touchstart events
- Logs all events to `/data/touch_debug.log`
- Runs in separate thread for non-blocking operation

### 3. StreamServer (Python)
**File**: `stream_server.py` (Primary - Real-time streaming)

WebSocket-based streaming server:
- Reads shared memory at 20x per second (50ms intervals)
- Maintains frame cache (up to 3 frames)
- Broadcasts JPEG frames to all connected WebSocket clients
- Forwards input events to TouchInjector via Unix socket
- Serves HTML interface on port 8081

**Endpoints**:
- `/` - Main HTML interface
- `/stream` - WebSocket endpoint for frame streaming
- `/input` - Receives input events (POST)
- `/stats` - Server statistics (JSON)
- `/stream-sse` - Server-Sent Events fallback

**File**: `screenshot_server.py` (Legacy - Disk-based screenshots)

Older Flask-based implementation that saves screenshots to disk. Still present for backward compatibility but not recommended for production use.

### 4. Modified Main.cc
**File**: `main.cc`

Integrates streaming components into the openpilot UI:
- Initializes FrameStreamer after MainWindow is created
- Initializes TouchInjector for input handling
- Both components run alongside the normal UI

## Shared Memory Structure

The shared memory uses a packed binary structure for efficient IPC:

```c
struct SharedFrame {
    uint64_t timestamp;      // 8 bytes - milliseconds since epoch
    uint32_t width;          // 4 bytes - frame width
    uint32_t height;         // 4 bytes - frame height
    uint32_t size;           // 4 bytes - actual JPEG data size
    uint32_t format;         // 4 bytes - 1 for JPEG
    uint8_t ready;           // 1 byte - ready flag
    uint8_t padding[6];      // 6 bytes - alignment padding (total metadata: 31 bytes)
    uint8_t data[...];       // Variable - JPEG compressed frame data (max: 8,294,400 bytes)
}
```

Total shared memory size: **8,294,431 bytes** (31 bytes metadata + 4×1920×1080 max frame buffer)

## Installation Steps

### 1. Install Dependencies

```bash
pip3 install flask flask-sock numpy
```

Or use the requirements file:
```bash
pip3 install -r requirements.txt
```

### 2. Create a New Branch (Recommended)

Create a new branch to prevent changes from being overwritten on device reboot:

```bash
cd /data/openpilot
git checkout -b ui_streaming
```

### 3. Add Source Files

Copy the following files to your openpilot directory:

**C++ Components**:
- `frame_streamer.h` → `/data/openpilot/selfdrive/ui/`
- `frame_streamer.cc` → `/data/openpilot/selfdrive/ui/`
- `touch_injector.h` → `/data/openpilot/selfdrive/ui/`
- `touch_injector.cc` → `/data/openpilot/selfdrive/ui/`
- Replace existing `main.cc` → `/data/openpilot/selfdrive/ui/`

**Python Server**:
- `stream_server.py` → `/data/`

### 4. Update SConscript

Modify `/data/openpilot/selfdrive/ui/SConscript` to include the new source files:

```python
qt_src = [
  # ... existing files ...
  'touch_injector.cc',
  'frame_streamer.cc',
  # ... other files ...
]
```

### 5. Rebuild the UI

Compile the modified UI:

```bash
cd /data/openpilot
scons selfdrive/ui
```

### 6. Auto-Start on Boot (Optional)

Edit `/data/openpilot/launch_openpilot.sh` to launch the stream server on boot:

```bash
# Add this line before openpilot is launched
python3 /data/stream_server.py &
```

### 7. Test and Access

#### Manual Testing:
```bash
# Enter tmux session
tmux a

# Kill openpilot (Ctrl+C)
# Exit tmux (Ctrl+B, then D)

# Launch manually
cd /data/openpilot
./launch_openpilot.sh

# In another terminal/SSH session:
python3 /data/stream_server.py
```

#### Access the UI:
Navigate to:
```
http://DEVICE_IP:8081
```

You should see:
- Real-time video stream at 10 FPS
- Status indicator (connected/streaming)
- FPS counter and latency information
- Interactive controls (click, drag, scroll)

## Configuration

### Adjusting Frame Rate

To change the frame rate, modify `frame_streamer.cc`:

```cpp
// Line ~75 in frame_streamer.cc
timer_->start(100);  // 100ms = 10 FPS
                     // Change to 50 for 20 FPS, 200 for 5 FPS, etc.
```

Remember to rebuild after changes:
```bash
cd /data/openpilot
scons selfdrive/ui
```

### Adjusting JPEG Quality

Modify the quality parameter in `frame_streamer.cc`:

```cpp
// Line ~140 in frame_streamer.cc
buffer.save(&io_device, "JPEG", 85);  // Quality: 0-100 (85 is default)
```

Higher quality = larger frame size = more bandwidth usage

### Changing Port

Modify `stream_server.py`:

```python
# Bottom of stream_server.py
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8081)  # Change port here
```

## Important Notes

### Performance
- **Memory Usage**: Shared memory uses ~8.3 MB fixed size
- **CPU Usage**: Frame capture at 10 FPS has minimal CPU impact (<5% on typical hardware)
- **Network Bandwidth**: ~500 KB/s - 2 MB/s depending on frame complexity and JPEG quality
- **Latency**: Typical end-to-end latency is 100-300ms

### Storage
- Unlike the legacy screenshot server, the real-time implementation uses **zero disk space**
- All frames are processed in memory only
- No cleanup of old files needed

### Calibration and Models
- **Initial Calibration**: May not complete correctly on custom branches. Switch back to release branch after debugging if needed.
- **Model Files**: Copy from release branch if missing: `/data/openpilot/selfdrive/modeld/models/`

### Debugging
- **Touch events log**: `/data/touch_debug.log`
- **Shared memory**: Check `/dev/shm/openpilot_ui_frames` exists
- **Server stats**: Access `http://DEVICE_IP:8081/stats` for server statistics
- **Frame capture**: FrameStreamer logs debug output every 10 frames

### Legacy Screenshot Server
The older `screenshot_server.py` is still included but not recommended:
- Saves screenshots to disk (fills storage quickly)
- Uses Flask polling instead of WebSocket (higher latency)
- Runs on port 8081 by default (conflicts with stream_server.py)

Only use if you need the legacy behavior. Otherwise, use `stream_server.py`.

## Troubleshooting

### No frames appearing:
1. Check shared memory: `ls -lh /dev/shm/openpilot_ui_frames`
2. Verify UI is running: `ps aux | grep ui`
3. Check server logs for errors
4. Ensure port 8081 is not blocked by firewall

### Input not working:
1. Check socket exists: `ls -lh /tmp/ui_touch_socket`
2. Verify touch_injector is initialized in main.cc
3. Check touch debug log: `tail -f /data/touch_debug.log`
4. Ensure browser is sending events (check browser console)

### High latency:
1. Reduce JPEG quality in frame_streamer.cc
2. Check network connection quality
3. Reduce frame rate if needed
4. Verify no other heavy processes running

### Build errors:
1. Ensure all source files are in correct locations
2. Verify SConscript includes touch_injector.cc and frame_streamer.cc
3. Check for Qt version compatibility
4. Clean build: `scons -c selfdrive/ui` then rebuild

## Technical Details

### Frame Capture Process
1. QTimer triggers every 100ms
2. `QPixmap::grab()` captures the MainWindow
3. Image encoded as JPEG with 85% quality
4. Metadata written to shared memory (timestamp, dimensions, size, format)
5. JPEG data written to shared memory buffer
6. `ready` flag set to 1 to signal new frame

### Streaming Process
1. Background thread polls shared memory every 50ms
2. Checks `ready` flag
3. Reads metadata and JPEG data
4. Adds frame to cache (max 3 frames)
5. Broadcasts frame to all connected WebSocket clients
6. Clients decode JPEG and render to Canvas

### Input Processing
1. Browser captures mouse/touch events
2. Calculates device coordinates from display coordinates
3. Sends JSON event via WebSocket
4. Server forwards to Unix socket
5. TouchInjector reads from socket
6. Creates Qt mouse/wheel events
7. Posts events to application event queue
8. Qt processes events normally

## Requirements

**Python Dependencies** (requirements.txt):
```
Flask==2.3.3
flask-sock==0.7.0
numpy==1.24.3
```

**System Requirements**:
- OpenPilot device with Qt5 support
- Python 3.8+
- Network connectivity
- ~10 MB available RAM for shared memory and caching

## License

This project is provided as-is for debugging and development purposes. Use at your own risk.

## Credits

Original concept and implementation for OpenPilot UI streaming. Enhanced with real-time shared memory architecture for improved performance and zero-disk operation.
