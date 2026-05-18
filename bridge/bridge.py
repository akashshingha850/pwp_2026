"""MQTT ↔ REST bridge for EyesEdge.

Connects the Pi-side auxiliary services to the cloud REST API:

- Subscribes to ``pwp/motion`` and POSTs MotionEvent + Image to the API.
- Polls ``/api/cameras/`` and republishes config to ``pwp/config`` on change.
- Serves captured JPEGs over a tiny HTTP server so the API's ``Image.filepath``
  URL is reachable.

MAC → camera UUID mapping is read from the bridge ``.env`` file
(``CAMERA_MAP=mac=uuid,mac=uuid,...``).

External sources used:
  - paho-mqtt (MQTT client): https://github.com/eclipse/paho.mqtt.python  (EPL-2.0)
  - Requests library (HTTP):  https://requests.readthedocs.io/              (Apache 2.0)
  - python-dotenv (env config): https://github.com/theskumar/python-dotenv  (BSD)
  - Course material (TLS setup, MQTT pub/sub patterns):
    https://lovelace.oulu.fi/ohjelmoitava-web/ohjelmoitava-web/
    exercise-4-implementing-hypermedia-clients/
"""

from __future__ import annotations

import base64
import http.server
import json
import logging
import os
import socketserver
import threading
import time
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MQTT_BROKER = os.environ.get("MQTT_BROKER", "")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 8883))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")
MQTT_TLS = os.environ.get("MQTT_TLS", "1") == "1" or MQTT_PORT == 8883

MOTION_TOPIC = os.environ.get("MOTION_TOPIC", "pwp/motion")
CONFIG_TOPIC = os.environ.get("CONFIG_TOPIC", "pwp/config")

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")
API_TOKEN = os.environ.get("API_TOKEN", "")

CAPTURES_DIR = Path(os.environ.get("CAPTURES_DIR", "captures")).resolve()
HTTP_HOST = os.environ.get("BRIDGE_HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.environ.get("BRIDGE_HTTP_PORT", 9000))
PUBLIC_URL = os.environ.get("BRIDGE_PUBLIC_URL", f"http://127.0.0.1:{HTTP_PORT}").rstrip("/")

POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", 10))
DEFAULT_DURATION = float(os.environ.get("DEFAULT_MOTION_DURATION", 0.0))
DEFAULT_THRESHOLD = float(os.environ.get("DEFAULT_MOTION_THRESHOLD", 0.05))


def _parse_camera_map(raw: str) -> dict[str, str]:
    """Parse 'mac=uuid,mac=uuid' (commas, semicolons, or whitespace) into {mac: uuid}."""
    mapping: dict[str, str] = {}
    if not raw:
        return mapping
    for token in raw.replace(";", ",").split(","):
        token = token.strip()
        if not token or "=" not in token:
            continue
        mac, uuid_str = token.split("=", 1)
        mapping[mac.strip().lower()] = uuid_str.strip()
    return mapping


CAMERA_MAP = _parse_camera_map(os.environ.get("CAMERA_MAP", ""))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("bridge")


# ── tiny HTTP server for serving captured JPEGs ───────────────────────────────
def start_file_server() -> None:
    """Start a background HTTP server that serves JPEG files from CAPTURES_DIR."""
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(CAPTURES_DIR), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:
            log.debug("http %s", format % args)

    class ReusableServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    server = ReusableServer((HTTP_HOST, HTTP_PORT), Handler)
    log.info("File server listening on %s:%d (root=%s)", HTTP_HOST, HTTP_PORT, CAPTURES_DIR)
    threading.Thread(target=server.serve_forever, name="file-server", daemon=True).start()


# ── REST helpers ──────────────────────────────────────────────────────────────
def _api_session() -> requests.Session:
    """Build an authenticated requests Session with JSON headers pre-set."""
    s = requests.Session()
    if API_TOKEN:
        s.headers["Authorization"] = f"Token {API_TOKEN}"
    s.headers["Content-Type"] = "application/json"
    s.headers["Accept"] = "application/json"
    # Force Host header so Django's ALLOWED_HOSTS check passes when bridge runs in Docker
    s.headers["Host"] = "127.0.0.1"
    return s


api = _api_session()


def post_motion_event(camera_uuid: str, duration: float, threshold: float) -> str | None:
    """POST a new MotionEvent to the API and return its UUID, or None on failure."""
    url = f"{API_BASE}/api/motions/"
    payload = {"camera": camera_uuid, "duration": duration, "threshold": threshold}
    r = api.post(url, data=json.dumps(payload), timeout=10)
    if not r.ok:
        log.error("POST /api/motions/ failed (%s): %s", r.status_code, r.text)
        return None
    return r.json().get("uuid")


def post_image(motion_uuid: str, filepath_url: str, filesize: int) -> bool:
    """POST an Image record linking a JPEG URL to an existing MotionEvent."""
    url = f"{API_BASE}/api/images/"
    payload = {"motion_event": motion_uuid, "filepath": filepath_url, "filesize": filesize}
    r = api.post(url, data=json.dumps(payload), timeout=10)
    if not r.ok:
        log.error("POST /api/images/ failed (%s): %s", r.status_code, r.text)
        return False
    return True


def list_cameras() -> list[dict[str, Any]]:
    """Fetch all cameras from the API and return them as a list of dicts."""
    url = f"{API_BASE}/api/cameras/"
    r = api.get(url, timeout=10)
    if not r.ok:
        log.error("GET /api/cameras/ failed (%s): %s", r.status_code, r.text)
        return []
    data = r.json()
    return data.get("results", data) if isinstance(data, dict) else data


# ── MQTT motion ingest ────────────────────────────────────────────────────────
def handle_motion(payload_bytes: bytes) -> None:
    """Decode an MQTT motion payload, save the JPEG, and push records to the API."""
    try:
        payload = json.loads(payload_bytes.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        log.warning("Motion payload not JSON: %s", exc)
        return

    mac = str(payload.get("camera_id", "")).lower()
    motion_id = str(payload.get("motion_id", "")) or str(int(time.time()))
    image_b64 = payload.get("image_b64")

    camera_uuid = CAMERA_MAP.get(mac)
    if not camera_uuid:
        log.warning("No CAMERA_MAP entry for MAC %r — skipping (known: %s)", mac, list(CAMERA_MAP))
        return
    if not image_b64:
        log.warning("Motion payload missing image_b64 for MAC %r", mac)
        return

    try:
        img_bytes = base64.b64decode(image_b64)
    except (ValueError, base64.binascii.Error) as exc:
        log.warning("Bad base64 from %s: %s", mac, exc)
        return

    filename = f"motion_{motion_id}.jpg"
    filepath = CAPTURES_DIR / filename
    filepath.write_bytes(img_bytes)

    motion_uuid = post_motion_event(camera_uuid, DEFAULT_DURATION, DEFAULT_THRESHOLD)
    if not motion_uuid:
        return
    file_url = f"{PUBLIC_URL}/{filename}"
    if post_image(motion_uuid, file_url, len(img_bytes)):
        log.info("Stored motion %s for camera %s (%d bytes) → %s", motion_id, mac, len(img_bytes), file_url)


def on_connect(client: mqtt.Client, _userdata, _flags, rc, _properties=None) -> None:
    """Subscribe to the motion topic once the MQTT connection is established."""
    if rc == 0:
        log.info("MQTT connected — subscribing to %s", MOTION_TOPIC)
        client.subscribe(MOTION_TOPIC, qos=1)
    else:
        log.error("MQTT connection refused: %s", rc)


def on_message(_client: mqtt.Client, _userdata, msg: mqtt.MQTTMessage) -> None:
    """Route incoming MQTT messages to the appropriate handler."""
    if msg.topic == MOTION_TOPIC:
        handle_motion(msg.payload)


def start_mqtt() -> mqtt.Client:
    """Connect to the MQTT broker with TLS and credentials, then start the network loop."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if MQTT_TLS:
        client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    log.info("Connecting MQTT %s:%d (TLS=%s) …", MQTT_BROKER, MQTT_PORT, MQTT_TLS)
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    return client


# ── camera poller → publish config on change ──────────────────────────────────
def _camera_to_config(cam: dict[str, Any]) -> dict[str, Any]:
    """Translate API Camera record into the keys config_sub.py understands."""
    cfg: dict[str, Any] = {}
    res = cam.get("resolution") or ""
    if "x" in res:
        try:
            w, h = res.split("x", 1)
            cfg["main_width"] = int(w)
            cfg["main_height"] = int(h)
        except ValueError:
            pass
    fps = cam.get("fps")
    if isinstance(fps, (int, float)):
        cfg["fps"] = int(fps)
    return cfg


def poll_loop(client: mqtt.Client) -> None:
    """Diff /api/cameras/ each tick; publish config on first sight or change."""
    last_seen: dict[str, dict[str, Any]] = {}
    while True:
        try:
            cameras = list_cameras()
            for cam in cameras:
                uuid_str = str(cam.get("uuid", ""))
                if not uuid_str:
                    continue
                snapshot = {
                    "resolution": cam.get("resolution"),
                    "fps": cam.get("fps"),
                    "status": cam.get("status"),
                }
                prev = last_seen.get(uuid_str)
                if prev == snapshot:
                    continue
                last_seen[uuid_str] = snapshot
                cfg_payload = _camera_to_config(cam)
                if not cfg_payload:
                    continue
                client.publish(CONFIG_TOPIC, json.dumps(cfg_payload), qos=1)
                log.info("Published config for camera %s → %s: %s",
                         uuid_str, CONFIG_TOPIC, cfg_payload)
        except requests.RequestException as exc:
            log.warning("Poll error: %s", exc)
        time.sleep(POLL_INTERVAL)


def main() -> None:
    """Validate config, start subsystems, and enter the camera poll loop."""
    if not MQTT_BROKER:
        log.error("MQTT_BROKER not set; configure .env first")
        return
    if not API_TOKEN:
        log.error("API_TOKEN not set; configure .env first")
        return

    log.info("CAMERA_MAP loaded: %d entries", len(CAMERA_MAP))
    start_file_server()
    client = start_mqtt()
    try:
        poll_loop(client)
    except KeyboardInterrupt:
        log.info("Shutting down")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
