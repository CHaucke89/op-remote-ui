# OpenPilot Remote UI Streaming

Real-time browser streaming and remote input for openpilot UI.

This is a port of the original Qt-based remote UI streamer by [ecpp](https://github.com/ecpp/op-remote-ui). The openpilot UI has moved from Qt (C++) to raylib/pyray (Python), so the original implementation is no longer functional in newer releases of openpilot. This fixes that.

Current primary path is Python + raylib/pyray:

- Frame capture: `frame_streamer.py`
- Input injection: `touch_injector.py`
- UI integration helper: `remote_ui.py`
- Browser server: `stream_server.py`

The C++/Qt files are still in this repository as a legacy implementation reference:

- `frame_streamer.cc/.h`
- `touch_injector.cc/.h`
- `main.cc`

## What This Repository Provides

This project moves openpilot UI frames from the render loop to a browser with no disk writes:

1. UI process captures the current framebuffer and JPEG-encodes it.
2. Encoded frame is written into POSIX shared memory at `/dev/shm/openpilot_ui_frames`.
3. `stream_server.py` reads shared memory and broadcasts frames over WebSocket.
4. Browser displays frames on a `<canvas>` and sends touch/mouse/scroll input to `/input`.
5. Input is forwarded to `/tmp/ui_touch_socket`, where `touch_injector.py` applies it to pyray input hooks.

## Current Components

### Python (active)

- `frame_streamer.py`
    - Captures with `pyray.load_image_from_screen()`.
    - JPEG encodes with Pillow.
    - Publishes to shared memory using a packed 31-byte header + payload.
    - Frame rate limited to 10 FPS by `FRAME_RATE_LIMIT`.

- `touch_injector.py`
    - Listens on Unix socket `/tmp/ui_touch_socket`.
    - Accepts JSON input events (`click`, `tap`, `drag`, `scroll`, `touchstart`, etc.).
    - Monkeypatches pyray polled input functions to expose remote state.

- `remote_ui.py`
    - Convenience wrapper that starts `TouchInjector` and `FrameStreamer`.
    - Intended to be instantiated after window/GL context initialization.

- `stream_server.py`
    - Flask + flask-sock server on port `8081`.
    - Reads shared memory via `mmap`.
    - Broadcasts latest frames to connected WebSocket clients.
    - Serves a built-in HTML page with remote controls.

- `screenshot_server.py` (legacy)
    - Older polling server that serves PNG screenshots from `/tmp/ui_frame_*.png`.
    - Kept for compatibility/testing, not the recommended runtime path.

### C++/Qt (legacy)

The C++ files implement the same shared-memory + socket concepts for the older Qt UI. They are useful as protocol references, but are not the primary integration path for current raylib/pyray UI.

## Shared Memory Contract

Both writer and reader use this packed layout:

```c
struct SharedFrame {
    uint64_t timestamp;   // epoch ms
    uint32_t width;
    uint32_t height;
    uint32_t size;        // JPEG byte length
    uint32_t format;      // 1 = JPEG
    uint8_t ready;
    uint8_t padding[6];
    uint8_t data[4 * 1920 * 1080];
};
```

- Metadata size: 31 bytes
- Data capacity: 8,294,400 bytes
- Total shared memory size: 8,294,431 bytes

## Installation

Install Python dependencies for the server and frame encoding:

```bash
pip3 install -r requirements.txt
```

`requirements.txt` includes:

- Flask
- flask-sock
- numpy
- Pillow

## Integrating into openpilot UI (raylib/pyray)

Edit your UI entrypoint (typically `selfdrive/ui/ui.py`) and wire `RemoteUI` into the render loop:

```python
from openpilot.selfdrive.ui.remote_ui import RemoteUI

def main():
        gui_app.init_window("UI")
        remote = RemoteUI()
        try:
                for _ in gui_app.render():
                        # existing draw logic...
                        remote.stream_frame()
        finally:
                remote.close()
```

Important:

- Construct `RemoteUI()` only after the window/context exists.
- Call `remote.stream_frame()` while the current frame is still available (before buffer swap).

## Running the Streaming Server

Start server:

```bash
python3 stream_server.py
```

Open in browser:

```text
http://DEVICE_IP:8081
```

## Endpoints

- `GET /` : Built-in HTML viewer
- `WS /stream` : Real-time frame stream
- `POST /input` : Remote input events (JSON)
- `GET /stats` : Cache/client stats
- `GET /stream-sse` : SSE fallback stream

## Input Event Format

Input payloads are JSON sent to `POST /input` and forwarded to `/tmp/ui_touch_socket`.

Examples:

```json
{"type":"click","x":1080,"y":540}
```

```json
{"type":"scroll","x":1080,"y":540,"deltaY":120}
```

```json
{"type":"drag","x":1200,"y":600,"startX":1080,"startY":540}
```

## Smoke Testing

`remote_ui.py` includes a standalone test window in its `__main__` block.

Important: this file imports modules via the openpilot package path (`openpilot.selfdrive.ui...`).
Run this smoke test from an environment where these files are placed in that package structure (for example inside your openpilot checkout), not from this flat repository layout as-is.

## Troubleshooting

### No frames in browser

1. Confirm shared memory exists: `ls -lh /dev/shm/openpilot_ui_frames`
2. Confirm server is running on port 8081.
3. Check server logs for shared-memory connect/read errors.
4. Confirm `remote.stream_frame()` is being called from the render loop.

### Input does not affect UI

1. Confirm socket exists: `ls -lh /tmp/ui_touch_socket`
2. Confirm `TouchInjector` was started (`RemoteUI()` created successfully).
3. Confirm browser requests to `/input` are succeeding (HTTP 200).

### Latency is high

1. Check network quality between browser and host.
2. Lower JPEG quality or capture rate in `frame_streamer.py`.
3. Reduce competing load on the UI host.

## Notes

- This repository focuses on streaming and input plumbing, not full openpilot deployment orchestration.
- `main.cc` and the Qt classes document the older integration style and protocol history.
