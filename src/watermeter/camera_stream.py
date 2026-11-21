from __future__ import annotations

import threading
import time
import cv2


class LatestFrameCamera:
    """Continuously reads an HTTP stream and retains only the newest frame."""
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
            cap = None
            try:
                cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not cap.isOpened():
                    self._connected = False
                    self._last_error = "Could not open stream. Check URL, port, Wi-Fi and camera power."
                    time.sleep(self.reconnect_delay)
                    continue
                self._connected = True
                self._last_error = ""
                while self._running and cap.isOpened():
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        self._connected = False
                        self._last_error = "Stream interrupted; reconnecting..."
                        break
                    with self._lock:
                        self._frame = frame
            except Exception as exc:
                self._connected = False
                self._last_error = str(exc)
            finally:
                if cap is not None:
                    cap.release()
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
