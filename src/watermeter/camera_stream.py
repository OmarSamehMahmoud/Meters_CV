from __future__ import annotations

import threading
import time

import cv2
import numpy as np
import requests


class LatestFrameCamera:
    """Read an ESP32-CAM MJPEG HTTP stream and retain only the newest frame.

    Requests is used instead of cv2.VideoCapture because OpenCV's FFmpeg
    backend can hang or fail to open some ESP32-CAM multipart streams on Windows.
    """
    def __init__(self, stream_url: str, reconnect_delay: float = 1.0):
        self.stream_url = stream_url
        self.reconnect_delay = reconnect_delay
        self._lock = threading.Lock()
        self._frame = None
        self._running = True
        self._connected = False
        self._last_error = "Connecting..."
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        while self._running:
            try:
                with requests.get(
                    self.stream_url,
                    stream=True,
                    timeout=(5, 15),
                    headers={"Cache-Control": "no-cache"},
                ) as response:
                    response.raise_for_status()
                    self._connected = True
                    self._last_error = "HTTP connected; waiting for JPEG frames..."
                    buffer = bytearray()

                    for chunk in response.iter_content(chunk_size=4096):
                        if not self._running:
                            break
                        if not chunk:
                            continue

                        buffer.extend(chunk)
                        while True:
                            start = buffer.find(b"\xff\xd8")
                            if start < 0:
                                if len(buffer) > 2:
                                    del buffer[:-2]
                                break

                            end = buffer.find(b"\xff\xd9", start + 2)
                            if end < 0:
                                if start > 0:
                                    del buffer[:start]
                                break

                            jpeg = bytes(buffer[start:end + 2])
                            del buffer[:end + 2]
                            frame = cv2.imdecode(
                                np.frombuffer(jpeg, dtype=np.uint8),
                                cv2.IMREAD_COLOR,
                            )
                            if frame is not None:
                                with self._lock:
                                    self._frame = frame
                                self._connected = True
                                self._last_error = ""

                    if self._running:
                        self._connected = False
                        self._last_error = "MJPEG stream ended; reconnecting..."

            except requests.RequestException as exc:
                self._connected = False
                self._last_error = f"HTTP stream error: {exc}"
            except Exception as exc:
                self._connected = False
                self._last_error = f"Frame decoding error: {exc}"

            if self._running:
                time.sleep(self.reconnect_delay)

    def latest(self):
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    @property
    def connected(self):
        return self._connected

    @property
    def last_error(self):
        return self._last_error

    def stop(self):
        self._running = False
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
