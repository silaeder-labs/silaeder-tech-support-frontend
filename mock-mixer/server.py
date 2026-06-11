from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import time
from urllib.parse import urlparse


def channel(num: int) -> dict:
    level = 40 + ((num * 7) % 32)
    return {
        "num": num,
        "name": f"CH {num:02d}",
        "icon": num % 10,
        "color": num % 16,
        "fader": round(level / 100, 2),
        "fader_db": round((level - 75) / 2, 1),
        "level": level,
        "on": num % 5 != 0,
        "pan": round(((num % 9) - 4) / 4, 2),
        "st": True,
        "mono": False,
        "trim": 0,
        "phantom": num in {1, 2, 7},
        "invert": False,
        "hpf": 80,
        "delay_on": False,
        "delay_time": 0,
        "dca": 0,
        "mute_grp": 0,
        "insert": False,
        "insert_sel": 0,
    }


STATE = {
    "started_at": time(),
    "selected_index": 1,
    "solo": [],
    "scene": 12,
    "cue": 4,
    "snippet": 2,
    "xremote": {"enabled": True, "last_action": "boot"},
    "channels": {num: channel(num) for num in range(1, 17)},
    "auxins": {num: channel(num) | {"name": f"AUX {num:02d}"} for num in range(1, 9)},
    "buses": {
        num: {"num": num, "name": f"BUS {num:02d}", "fader": 0.64, "fader_db": -5.5}
        for num in range(1, 17)
    },
    "dcas": {
        num: {"num": num, "name": f"DCA {num}", "fader": 0.72, "fader_db": -3.0}
        for num in range(1, 9)
    },
    "main_st": {"name": "MAIN ST", "fader": 0.69, "fader_db": -2.5, "level": 69},
    "main_m": {"name": "MAIN M", "fader": 0.58, "fader_db": -7.0, "level": 58},
    "eq": {},
    "gate": {},
    "dyn": {},
    "fx": {
        slot: {
            "slot": slot,
            "type": ["Hall Reverb", "Stereo Delay", "Plate", "Compressor"][slot % 4],
            "params": {param: round((slot * param) / 100, 2) for param in range(1, 17)},
        }
        for slot in range(1, 9)
    },
    "headamps": {
        idx: {"idx": idx, "gain": 18 + (idx % 8) * 2, "phantom": idx in {1, 2, 7}}
        for idx in range(1, 33)
    },
    "usb": {
        "mounted": True,
        "path": "/recordings",
        "tape_file": "Im So.wav",
        "tape_state": 1,
        "tape_time": 94,
        "tape_length": 205,
        "tape_started_at": time() - 94,
        "files": [
            "Im So.wav",
            "Final.wav",
            "My_favorite_unicorn.wav",
            "Finalfin.wav",
            "Applause.wav",
            "Sting.wav",
            "Intro.wav",
            "Outro.wav",
            "Bell.wav",
            "Swoosh.wav",
            "Beat loop.wav",
            "Ambient.wav",
            "Final 2.wav",
            "Final 3.wav",
            "Final 4.wav",
        ],
    },
}


def merge_patch(target: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if value is not None:
            target[key] = value
    if "fader" in patch and patch["fader"] is not None:
        target["level"] = round(float(patch["fader"]) * 100)
    return target


def validation_error(path: str, message: str) -> dict:
    return {
        "detail": [
            {
                "loc": ["path", path],
                "msg": message,
                "type": "value_error",
            }
        ]
    }


def eq_band(num: int, band: int) -> dict:
    key = (num, band)
    if key not in STATE["eq"]:
        STATE["eq"][key] = {
            "channel": num,
            "band": band,
            "type": "PEQ",
            "f": 120 * band,
            "g": round((band - 3) * 1.5, 1),
            "q": 1.2,
        }
    return STATE["eq"][key]


def dynamics(kind: str, num: int) -> dict:
    bucket = STATE[kind]
    if num not in bucket:
        bucket[num] = {
            "channel": num,
            "on": num % 2 == 0,
            "mode": "expander" if kind == "gate" else "compressor",
            "thr": -42.0 if kind == "gate" else -18.0,
            "ratio": 2.5,
            "attack": 12,
            "release": 140,
            "knee": 3,
            "mgain": 0,
        }
    return bucket[num]


def ensure_track_ext(name: str) -> str:
    if "." in name.rsplit("/", 1)[-1]:
        return name
    return f"{name}.wav"


def display_track(name: str | None) -> str:
    if not name:
        return ""
    return name.rsplit("/", 1)[-1].removesuffix(".wav")


def track_length(name: str) -> int:
    return 180 + (len(name) % 80)


def select_track(name: str, reset: bool = True) -> None:
    usb = STATE["usb"]
    usb["tape_file"] = ensure_track_ext(name)
    usb["tape_length"] = track_length(usb["tape_file"])
    if reset:
        usb["tape_time"] = 0
    usb["tape_started_at"] = time() - float(usb["tape_time"])
    usb["tape_state"] = 1


def sync_tape_time() -> None:
    usb = STATE["usb"]
    if usb["tape_state"] != 1:
        return

    files = usb["files"]
    current_time = time()
    elapsed = max(0, current_time - float(usb["tape_started_at"]))
    while elapsed >= float(usb["tape_length"]):
        elapsed -= float(usb["tape_length"])
        current = usb["tape_file"]
        idx = files.index(current) if current in files else 0
        usb["tape_file"] = files[(idx + 1) % len(files)]
        usb["tape_length"] = track_length(usb["tape_file"])
        usb["tape_started_at"] = current_time - elapsed
    usb["tape_time"] = round(elapsed, 1)


def public_usb_status() -> dict:
    sync_tape_time()
    usb = deepcopy(STATE["usb"])
    usb.pop("files", None)
    usb.pop("tape_started_at", None)
    return usb


class MixerHandler(BaseHTTPRequestHandler):
    server_version = "MockX32/0.1"

    def do_GET(self) -> None:
        self.route("GET")

    def do_POST(self) -> None:
        self.route("POST")

    def do_PUT(self) -> None:
        self.route("PUT")

    def do_PATCH(self) -> None:
        self.route("PATCH")

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def send_json(self, code: int, payload: dict | list) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def route(self, method: str) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"

        if method == "GET" and path == "/":
            self.send_json(200, {"name": "Mock X32 REST API", "docs": "/api/info"})
            return
        if method == "GET" and path == "/health":
            self.send_json(200, {"status": "ok"})
            return
        if method == "GET" and path == "/api/info":
            self.send_json(200, {"model": "X32 Mock", "version": "0.1.0", "serial": "MOCK-0001"})
            return
        if method == "GET" and path == "/api/status":
            self.send_json(200, self.status())
            return
        if method == "GET" and path == "/api/solo":
            self.send_json(200, {"solo": STATE["solo"]})
            return
        if method == "POST" and path == "/api/solo/clear":
            STATE["solo"] = []
            self.send_json(200, {"ok": True, "solo": []})
            return
        if path == "/api/selidx":
            if method == "GET":
                self.send_json(200, {"selidx": STATE["selected_index"]})
                return
            if method == "PUT":
                STATE["selected_index"] = int(self.body().get("selidx", STATE["selected_index"]))
                self.send_json(200, {"selidx": STATE["selected_index"]})
                return
        if path == "/api/main/st":
            self.fader_route(method, STATE["main_st"])
            return
        if path == "/api/main/m":
            self.fader_route(method, STATE["main_m"])
            return
        if path == "/api/usb":
            self.usb_route(method)
            return
        if path == "/api/usb/list" and method == "GET":
            self.send_json(200, {"path": STATE["usb"]["path"], "files": STATE["usb"]["files"]})
            return
        if path.startswith("/api/usb/") and method == "POST":
            self.usb_command(path.removeprefix("/api/usb/"))
            return
        if path == "/api/xremote":
            if method == "GET":
                self.send_json(200, STATE["xremote"])
                return
            if method == "POST":
                STATE["xremote"].update(self.body())
                self.send_json(200, {"ok": True, **STATE["xremote"]})
                return

        match = re.fullmatch(r"/api/channels/(\d+)", path)
        if match:
            self.patchable(method, "num", int(match.group(1)), STATE["channels"])
            return
        match = re.fullmatch(r"/api/auxins/(\d+)", path)
        if match:
            self.patchable(method, "num", int(match.group(1)), STATE["auxins"])
            return
        match = re.fullmatch(r"/api/buses/(\d+)", path)
        if match:
            self.patchable(method, "num", int(match.group(1)), STATE["buses"])
            return
        match = re.fullmatch(r"/api/dcas/(\d+)", path)
        if match:
            self.patchable(method, "num", int(match.group(1)), STATE["dcas"])
            return
        match = re.fullmatch(r"/api/channels/(\d+)/eq/(\d+)", path)
        if match:
            band = eq_band(int(match.group(1)), int(match.group(2)))
            self.fader_route(method, band)
            return
        match = re.fullmatch(r"/api/channels/(\d+)/(gate|dyn)", path)
        if match:
            item = dynamics(match.group(2), int(match.group(1)))
            self.fader_route(method, item)
            return
        match = re.fullmatch(r"/api/fx/(\d+)", path)
        if match and method == "GET":
            self.fx_type(int(match.group(1)))
            return
        match = re.fullmatch(r"/api/fx/(\d+)/type", path)
        if match and method == "PUT":
            self.set_fx_type(int(match.group(1)))
            return
        match = re.fullmatch(r"/api/fx/(\d+)/params/(\d+)", path)
        if match:
            self.fx_param(method, int(match.group(1)), int(match.group(2)))
            return
        match = re.fullmatch(r"/api/headamps/(\d+)", path)
        if match:
            self.patchable(method, "idx", int(match.group(1)), STATE["headamps"])
            return
        match = re.fullmatch(r"/api/(scene|cue|snippet)/(\d+)", path)
        if match and method == "POST":
            STATE[match.group(1)] = int(match.group(2))
            self.send_json(200, {"ok": True, match.group(1): int(match.group(2))})
            return

        self.send_json(404, {"error": {"code": "not_found", "message": "Unknown mock mixer endpoint"}})

    def status(self) -> dict:
        sync_tape_time()
        channels = [STATE["channels"][num]["level"] for num in range(1, 17)]
        meters = [
            max(0, min(100, level + (((num + round(time())) % 7) - 3)))
            for num, level in enumerate(channels, start=1)
        ]
        return {
            "recording": True,
            "recordingTime": "1:23:56",
            "fileSize": "2.4 GB",
            "freeSpace": "184 GB",
            "bitrate": "4500 kb/s",
            "slide": STATE["scene"],
            "totalSlides": 32,
            "nowPlaying": display_track(STATE["usb"]["tape_file"]),
            "channels": channels,
            "meters": meters,
            "mixer": {
                "uptime": round(time() - STATE["started_at"]),
                "selected_index": STATE["selected_index"],
                "main_st": STATE["main_st"],
                "solo": STATE["solo"],
            },
        }

    def fader_route(self, method: str, item: dict) -> None:
        if method == "GET":
            self.send_json(200, deepcopy(item))
            return
        if method in {"PATCH", "PUT"}:
            self.send_json(200, merge_patch(item, self.body()))
            return
        self.send_json(404, validation_error("method", "Unsupported method"))

    def patchable(self, method: str, path_name: str, idx: int, bucket: dict) -> None:
        if idx not in bucket:
            self.send_json(422, validation_error(path_name, "Index is out of range"))
            return
        self.fader_route(method, bucket[idx])

    def fx_type(self, slot: int) -> None:
        if slot not in STATE["fx"]:
            self.send_json(422, validation_error("slot", "FX slot is out of range"))
            return
        self.send_json(200, {"slot": slot, "type": STATE["fx"][slot]["type"]})

    def set_fx_type(self, slot: int) -> None:
        if slot not in STATE["fx"]:
            self.send_json(422, validation_error("slot", "FX slot is out of range"))
            return
        STATE["fx"][slot]["type"] = str(self.body().get("type", STATE["fx"][slot]["type"]))
        self.fx_type(slot)

    def fx_param(self, method: str, slot: int, param: int) -> None:
        if slot not in STATE["fx"]:
            self.send_json(422, validation_error("slot", "FX slot is out of range"))
            return
        params = STATE["fx"][slot]["params"]
        if method == "GET":
            self.send_json(200, {"slot": slot, "param": param, "value": params.get(param, 0)})
            return
        if method == "PUT":
            params[param] = float(self.body().get("value", params.get(param, 0)))
            self.send_json(200, {"slot": slot, "param": param, "value": params[param]})
            return
        self.send_json(404, validation_error("method", "Unsupported method"))

    def usb_route(self, method: str) -> None:
        if method == "GET":
            self.send_json(200, public_usb_status())
            return
        self.send_json(404, validation_error("method", "Unsupported method"))

    def usb_command(self, command: str) -> None:
        sync_tape_time()
        if command == "play":
            body = self.body()
            if "name" in body and body["name"]:
                next_track = ensure_track_ext(str(body["name"]))
                select_track(next_track, reset=True)
            elif "pos" in body and body["pos"] is not None:
                files = STATE["usb"]["files"]
                select_track(files[int(body["pos"]) % len(files)], reset=True)
            else:
                select_track(STATE["usb"]["tape_file"], reset=False)
        elif command == "stop":
            STATE["usb"]["tape_state"] = 0
            STATE["usb"]["tape_time"] = 0
            STATE["usb"]["tape_started_at"] = time()
        elif command == "pause":
            STATE["usb"]["tape_state"] = 2
        elif command in {"next", "prev"}:
            files = STATE["usb"]["files"]
            current = STATE["usb"]["tape_file"]
            idx = files.index(current) if current in files else 0
            select_track(files[(idx + (1 if command == "next" else -1)) % len(files)], reset=True)
        elif command == "cd":
            STATE["usb"]["path"] = str(self.body().get("path", STATE["usb"]["path"]))
        else:
            self.send_json(404, validation_error("command", "Unsupported USB command"))
            return
        self.send_json(200, {"ok": True, **public_usb_status()})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8090"))
    server = ThreadingHTTPServer(("0.0.0.0", port), MixerHandler)
    print(f"Mock X32 REST API listening on :{port}")
    server.serve_forever()
