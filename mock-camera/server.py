from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import time
from urllib.parse import parse_qs, urlparse


STATE = {
    "enabled": True,
    "moving": False,
    "position_deg": 0.0,
    "speed_dps": 45.0,
    "zero_offset_deg": 0.0,
    "last_command": "boot",
    "started_at": time(),
}


def number(values: dict[str, list[str]], key: str, default: float | None = None) -> float | None:
    raw = values.get(key, [])
    if not raw:
        return default
    try:
        return float(raw[0])
    except ValueError:
        return default


class CameraHandler(BaseHTTPRequestHandler):
    server_version = "MockCameraTurner/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if path == "/status":
            self.send_json(200, self.status())
            return
        if path == "/rotate":
            deg = number(query, "deg")
            if deg is None:
                self.send_json(400, {"error": "deg query parameter is required"})
                return
            speed = number(query, "speed", STATE["speed_dps"])
            STATE["position_deg"] = round(STATE["position_deg"] + deg, 2)
            STATE["speed_dps"] = speed
            STATE["moving"] = True
            STATE["last_command"] = "rotate"
            self.send_json(200, {"ok": True, **self.status()})
            return
        if path == "/move":
            deg = number(query, "deg")
            if deg is None:
                self.send_json(400, {"error": "deg query parameter is required"})
                return
            speed = number(query, "speed", STATE["speed_dps"])
            STATE["position_deg"] = round(deg, 2)
            STATE["speed_dps"] = speed
            STATE["moving"] = True
            STATE["last_command"] = "move"
            self.send_json(200, {"ok": True, **self.status()})
            return
        if path == "/stop":
            STATE["moving"] = False
            STATE["last_command"] = "stop"
            self.send_json(200, {"ok": True, **self.status()})
            return
        if path == "/enable":
            STATE["enabled"] = True
            STATE["last_command"] = "enable"
            self.send_json(200, {"ok": True, **self.status()})
            return
        if path == "/disable":
            STATE["enabled"] = False
            STATE["moving"] = False
            STATE["last_command"] = "disable"
            self.send_json(200, {"ok": True, **self.status()})
            return
        if path == "/zero":
            STATE["zero_offset_deg"] = STATE["position_deg"]
            STATE["position_deg"] = 0.0
            STATE["last_command"] = "zero"
            self.send_json(200, {"ok": True, **self.status()})
            return

        self.send_json(404, {"error": "unknown camera endpoint"})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def status(self) -> dict:
        return {
            "enabled": STATE["enabled"],
            "moving": STATE["moving"],
            "position_deg": STATE["position_deg"],
            "speed_dps": STATE["speed_dps"],
            "zero_offset_deg": STATE["zero_offset_deg"],
            "last_command": STATE["last_command"],
            "uptime_sec": round(time() - STATE["started_at"]),
        }

    def send_json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8091"))
    server = ThreadingHTTPServer(("0.0.0.0", port), CameraHandler)
    print(f"Mock ESP32 camera turner API listening on :{port}")
    server.serve_forever()
