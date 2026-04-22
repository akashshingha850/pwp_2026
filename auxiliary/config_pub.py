

"""MQTT publisher via REST API — sends config updates using EMQX Cloud API v5.

API: https://q1fd1412.ala.eu-central-1.emqxsl.com:8443/api/v5
Topic: pwp/config

Just run: python publish_config_api.py
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

# ── API settings ──────────────────────────────────────────────────────────────
API_BASE_URL = "https://q1fd1412.ala.eu-central-1.emqxsl.com:8443/api/v5"
PUBLISH_ENDPOINT = f"{API_BASE_URL}/publish"
TOPIC = "pwp/config"

def load_env_file(env_path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file into process environment."""
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file(Path(__file__).parent / "config" / ".env")

MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

# Keep publisher-side validation compatible with config.py listener schema.
SCHEMA: dict[str, type | tuple[type, ...]] = {
    "main_width": int,
    "main_height": int,
    "lores_width": int,
    "lores_height": int,
    "fps": (int, float),
    "pixel_threshold": (int, float),
    "motion_threshold": float,
    "background_alpha": float,
    "cooldown": float,
    "warmup_sec": float,
    "save_motion_frames": bool,
}

# ── hardcoded payload parameters ──────────────────────────────────────────────
PAYLOAD = {
    "fps": 25,
    "motion_threshold": 0.05,
    "save_motion_frames": True,
    "main_width": 1280,
    "main_height": 720,
    # Add/modify parameters as needed:
    # "lores_width": 640,
    # "lores_height": 360,
    # "pixel_threshold": 5,
    # "background_alpha": 0.5,
    # "cooldown": 2.0,
    # "warmup_sec": 1.0,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def validate_payload(payload: dict[str, Any]) -> bool:
    """Validate payload against the listener schema."""
    for key, value in payload.items():
        expected = SCHEMA.get(key)
        if expected is None:
            log.error("Unknown key %r", key)
            return False
        if expected is float and isinstance(value, int) and not isinstance(value, bool):
            continue
        if not isinstance(value, expected):
            log.error("Key %r: expected %s, got %s", key, expected, type(value).__name__)
            return False
    return True


def publish_via_api(payload: dict[str, Any]) -> bool:
    """Publish payload via EMQX REST API v5."""
    if not MQTT_USERNAME or not MQTT_PASSWORD:
        log.error("Missing credentials: set MQTT_USERNAME and MQTT_PASSWORD")
        return False

    # Build request body for EMQX API v5
    request_body = {
        "topic": TOPIC,
        "qos": 1,
        "retain": False,
        "payload": json.dumps(payload),
        "payload_encoding": "plain",
    }

    try:
        response = requests.post(
            PUBLISH_ENDPOINT,
            json=request_body,
            headers={"Content-Type": "application/json"},
            auth=HTTPBasicAuth(MQTT_USERNAME, MQTT_PASSWORD),
            verify=True,  # Verify SSL certificate
            timeout=10,
        )

        if response.status_code == 200:
            log.info("Message published successfully")
            log.debug("Response: %s", response.json())
            return True
        else:
            log.error("Failed to publish: %d %s", response.status_code, response.reason)
            try:
                log.error("Response: %s", response.json())
            except Exception:
                log.error("Response: %s", response.text)
            return False

    except requests.exceptions.ConnectionError as exc:
        log.error("Connection error: %s", exc)
        return False
    except requests.exceptions.Timeout:
        log.error("Request timeout")
        return False
    except requests.exceptions.RequestException as exc:
        log.error("Request error: %s", exc)
        return False


def main() -> None:
    payload = PAYLOAD

    if not validate_payload(payload):
        raise SystemExit(1)

    log.info("Publishing to %s", PUBLISH_ENDPOINT)
    log.info("Payload: %s", json.dumps(payload, indent=2))

    if not publish_via_api(payload):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
