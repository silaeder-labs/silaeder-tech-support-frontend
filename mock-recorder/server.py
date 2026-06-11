from __future__ import annotations

import json
import os
import random
import struct
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


WIDTH = int(os.getenv("NOISE_WIDTH", "160"))
HEIGHT = int(os.getenv("NOISE_HEIGHT", "90"))
FPS = float(os.getenv("NOISE_FPS", "6"))
BOUNDARY = "frame"


class RecorderHandler(BaseHTTPRequestHandler):
    server_version = "MockXUSBRecorder/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in {"/", "/ui"}:
            self.send_html()
            return
        if path == "/api/devices":
            self.send_json(200, devices())
            return
        if path == "/api/record/status":
            self.send_json(200, record_status())
            return
        if path in {"/video", "/api/stream/video"}:
            self.send_noise_stream()
            return
        self.send_json(404, {"error": "unknown recorder endpoint"})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def send_json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def send_html(self) -> None:
        body = b'<html><body><h1>Mock Recorder</h1><img src="/video" /></body></html>'
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_noise_stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Pragma", "no-cache")
        self.end_headers()

        delay = 1 / max(FPS, 1)
        while True:
            frame = noise_bmp(WIDTH, HEIGHT)
            part = (
                f"--{BOUNDARY}\r\n"
                "Content-Type: image/bmp\r\n"
                f"Content-Length: {len(frame)}\r\n\r\n"
            ).encode()
            try:
                self.wfile.write(part)
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
            time.sleep(delay)


def devices() -> dict:
    return {
        "audio": [],
        "video": [
            {
                "path": "camera1",
                "modes": [f"{WIDTH}x{HEIGHT}@{int(FPS)}"],
                "raw": "mock random noise camera",
            }
        ],
    }


def record_status() -> dict:
    return {
        "running": False,
        "started_at": None,
        "last_error": "",
        "output": "",
        "ffmpeg": [],
        "stderr": "",
        "stdout": "",
    }


def noise_bmp(width: int, height: int) -> bytes:
    row_size = (width * 3 + 3) & ~3
    pixel_size = row_size * height
    file_size = 54 + pixel_size

    header = bytearray()
    header += b"BM"
    header += struct.pack("<IHHI", file_size, 0, 0, 54)
    header += struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, pixel_size, 2835, 2835, 0, 0)

    rows = bytearray()
    padding = b"\x00" * (row_size - width * 3)
    for _ in range(height):
        rows += random.randbytes(width * 3)
        rows += padding
    return bytes(header + rows)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8093"))
    server = ThreadingHTTPServer(("0.0.0.0", port), RecorderHandler)
    print(f"Mock xusb-recorder API listening on :{port}")
    server.serve_forever()
