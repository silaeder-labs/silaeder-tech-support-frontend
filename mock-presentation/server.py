from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


SLIDES = [
    {
        "index": index,
        "source": "mock-presentation.pdf",
        "local_number": index + 1,
        "cache_key": "mockdeck",
        "url": f"/slides/mockdeck/slide_{index + 1:04d}.png",
    }
    for index in range(32)
]

STATE = {
    "current_index": 11,
    "status": "Idle",
    "busy": False,
    "version": 1,
    "obs_widget": {
        "connected": True,
        "current_index": 11,
        "ready_count": 5,
        "desired_count": 5,
        "retained_count": 5,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    },
}


class PresentationHandler(BaseHTTPRequestHandler):
    server_version = "MockPresentationClicker/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in {"/", "/settings", "/clicker", "/widget"}:
            self.send_html()
            return
        if path == "/api/state":
            self.send_json(200, public_state())
            return
        if path == "/api/slides":
            self.send_json(200, SLIDES)
            return
        if path.startswith("/slides/"):
            self.send_response(204)
            self.end_headers()
            return
        if path == "/events":
            self.send_event()
            return
        self.send_json(404, {"error": "unknown presentation endpoint"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/api/next":
            move(1)
            self.send_json(200, public_state())
            return
        if path == "/api/prev":
            move(-1)
            self.send_json(200, public_state())
            return
        if path == "/api/rebuild":
            STATE["status"] = "Queue prepared"
            STATE["busy"] = False
            STATE["version"] += 1
            self.send_json(200, public_state())
            return
        if path == "/api/cache/clear":
            STATE["current_index"] = 0
            STATE["status"] = "Cache cleared"
            STATE["version"] += 1
            self.send_json(200, public_state())
            return
        if path == "/api/widget/cache":
            STATE["obs_widget"]["connected"] = True
            STATE["obs_widget"]["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.send_json(200, {"ok": True, "obs_widget": STATE["obs_widget"]})
            return
        self.send_json(404, {"error": "unknown presentation endpoint"})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def send_json(self, code: int, payload: dict | list) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def send_html(self) -> None:
        body = b"<html><body><h1>Mock Presentation Clicker</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_event(self) -> None:
        payload = json.dumps(public_state(), ensure_ascii=False)
        body = f"event: state\ndata: {payload}\n\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def move(delta: int) -> None:
    STATE["current_index"] = max(0, min(len(SLIDES) - 1, STATE["current_index"] + delta))
    STATE["version"] += 1
    STATE["obs_widget"]["current_index"] = STATE["current_index"]
    STATE["obs_widget"]["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")


def public_state() -> dict:
    current = STATE["current_index"]
    return {
        "current_index": current,
        "total": len(SLIDES),
        "status": STATE["status"],
        "busy": STATE["busy"],
        "version": STATE["version"],
        "slide": SLIDES[current] if SLIDES else None,
        "obs_widget": STATE["obs_widget"],
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8092"))
    server = ThreadingHTTPServer(("0.0.0.0", port), PresentationHandler)
    print(f"Mock presentation clicker API listening on :{port}")
    server.serve_forever()
