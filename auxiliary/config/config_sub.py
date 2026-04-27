"""MQTT listener — updates config.yaml with payloads from a remote machine.

Broker: q1fd1412.ala.eu-central-1.emqxsl.com (EMQX Cloud, TLS 8883)

Publish a JSON object to the topic below to update one or more keys, e.g.:
    {"fps": 25, "motion_threshold": 0.03, "save_motion_frames": true}

Set credentials via env vars:
    MQTT_USERNAME=<user> MQTT_PASSWORD=<pass> python config.py
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ── broker ────────────────────────────────────────────────────────────────────
MQTT_BROKER = os.environ.get("MQTT_BROKER", "")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 8883))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")
TOPIC = "pwp/config"

CONFIG_PATH = Path(__file__).parent / "config.yaml"

# ── allowed keys and their expected Python types ──────────────────────────────
SCHEMA: dict[str, type | tuple[type, ...]] = {
    "main_width":         int,
    "main_height":        int,
    "lores_width":        int,
    "lores_height":       int,
    "fps":                (int, float),
    "pixel_threshold":    (int, float),
    "motion_threshold":   float,
    "background_alpha":   float,
    "cooldown":           float,
    "warmup_sec":         float,
    "save_motion_frames": bool,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def _load() -> dict[str, Any]:
    with CONFIG_PATH.open() as f:
        return yaml.safe_load(f) or {}


def _save(data: dict[str, Any]) -> None:
    with CONFIG_PATH.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def apply_update(payload: str) -> None:
    try:
        updates: dict = json.loads(payload)
    except json.JSONDecodeError as exc:
        log.warning("Bad JSON: %s", exc)
        return

    if not isinstance(updates, dict):
        log.warning("Payload must be a JSON object, got %s", type(updates).__name__)
        return

    validated: dict[str, Any] = {}
    for key, value in updates.items():
        expected = SCHEMA.get(key)
        if expected is None:
            log.warning("Unknown key %r — skipped", key)
            continue
        # coerce int → float where float is expected (JSON has no float literal distinction)
        if expected is float and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        if not isinstance(value, expected):
            log.warning("Key %r: expected %s, got %s — skipped", key, expected, type(value).__name__)
            continue
        validated[key] = value

    if not validated:
        log.info("No valid keys in message")
        return

    cfg = _load()
    cfg.update(validated)
    _save(cfg)
    log.info("config.yaml updated: %s", validated)


def on_connect(client: mqtt.Client, _userdata, _flags, rc, _properties=None) -> None:
    if rc == 0:
        log.info("Connected — subscribing to %s", TOPIC)
        client.subscribe(TOPIC, qos=1)
    else:
        log.error("Connection refused: %s", rc)


def on_message(_client: mqtt.Client, _userdata, msg: mqtt.MQTTMessage) -> None:
    log.info("Message on %s (%d bytes)", msg.topic, len(msg.payload))
    apply_update(msg.payload.decode("utf-8", errors="replace"))


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.tls_set()  # uses system CA bundle; EMQX Cloud has a valid cert
    client.on_connect = on_connect
    client.on_message = on_message

    log.info("Connecting to %s:%d …", MQTT_BROKER, MQTT_PORT)
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
