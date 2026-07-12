import threading
import queue
import json as _json
from typing import Optional

from websocket import create_connection, WebSocketTimeoutException, WebSocketException


class WebSocketClient:
    def __init__(self, url: str):
        self.url = url
        self._conn = None
        self._reader_thread = None
        self._inbox = queue.Queue()
        self._running = False
        self._lock = threading.Lock()

    def connect(self) -> None:
        with self._lock:
            if self._running:
                return
            self._conn = create_connection(self.url, timeout=10)
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()

    def _read_loop(self) -> None:
        while self._running:
            try:
                raw = self._conn.recv()
                obj = _json.loads(raw)
                self._inbox.put(obj)
            except WebSocketTimeoutException:
                pass
            except WebSocketException:
                break
            except Exception:
                break
        self._running = False

    def send(self, obj: dict) -> None:
        with self._lock:
            if self._conn is None:
                raise RuntimeError("not connected")
            self._conn.send(_json.dumps(obj))

    def recv(self, timeout: float = 1.0) -> Optional[dict]:
        try:
            return self._inbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        with self._lock:
            self._running = False
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
            self._conn = None

    def is_connected(self) -> bool:
        return self._running and self._conn is not None