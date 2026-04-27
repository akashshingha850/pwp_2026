"""MQTT publisher — sends config updates to the remote listener.

Broker: q1fd1412.ala.eu-central-1.emqxsl.com (EMQX Cloud, TLS 8883)
Topic:  pwp/config

Edit PAYLOAD below, then run:
    python config_pub.py
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "config" / ".env")

# ── broker ────────────────────────────────────────────────────────────────────
MQTT_BROKER = os.environ.get("MQTT_BROKER", "")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 8883))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")
TOPIC = "pwp/config"

# ── payload — edit values here ────────────────────────────────────────────────
PAYLOAD: dict[str, Any] = {
    "fps": 25,
    "motion_threshold": 0.05,
    "save_motion_frames": True,
    "main_width": 1280,
    "main_height": 720,
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


def on_connect(client: mqtt.Client, _userdata, _flags, rc, _properties=None) -> None:
    if rc == 0:
        log.info("Connected — publishing to %s", TOPIC)
        client.publish(TOPIC, json.dumps(PAYLOAD), qos=1)
        client.disconnect()
    else:
        log.error("Connection refused: %s", rc)


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.tls_set()
    client.on_connect = on_connect

    log.info("Connecting to %s:%d …", MQTT_BROKER, MQTT_PORT)
    log.info("Payload: %s", json.dumps(PAYLOAD, indent=2))
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
