"""Fast, modular motion detection with Picamera2.

Motion detection runs on a low-resolution luminance stream for speed.
When motion is detected, a full-resolution image is saved.

Author: Akash Bappy
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
import uuid
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from picamera2 import Picamera2
import zmq

from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from PIL import Image


@dataclass
class DetectorConfig:
    main_size: tuple[int, int]
    lores_size: tuple[int, int]
    fps: int
    pixel_diff_threshold: int
    motion_ratio_threshold: float
    background_alpha: float
    event_cooldown_sec: float
    warmup_sec: float
    save_motion_frames: bool


def load_config(config_path: str) -> DetectorConfig:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    return DetectorConfig(
        main_size=(
            int(data.get("main_width", 1920)),
            int(data.get("main_height", 1080)),
        ),
        lores_size=(
            int(data.get("lores_width", 320)),
            int(data.get("lores_height", 240)),
        ),
        fps=int(data.get("fps", 30)),
        pixel_diff_threshold=int(data.get("pixel_threshold", 20)),
        motion_ratio_threshold=float(data.get("motion_threshold", 0.02)),
        background_alpha=float(data.get("background_alpha", 0.08)),
        event_cooldown_sec=float(data.get("cooldown", 1.0)),
        warmup_sec=float(data.get("warmup_sec", 0.5)),
        save_motion_frames=bool(data.get("save_motion_frames", True)),
    )


class MotionDetector:
    def __init__(self, config: DetectorConfig, config_path: str) -> None:
        self.config = config
        self.config_path = config_path
        self.config_mtime = os.path.getmtime(config_path)
        try:
            self.picam2 = Picamera2()
        except Exception as e:
            print("Failed to initialize Picamera2:", e)
            print("No camera detected or libcamera not configured inside the container.")
            exit(1)
        self._background: np.ndarray | None = None
        self._last_event_time = 0.0
        self._frame_count = 0
        self._stats_peak_ratio = 0.0
        self._stats_window_start = time.perf_counter()

        # Load MQTT credentials from one level up `.env`
        try:
            load_dotenv(Path(__file__).parent.parent / ".env")
        except Exception:
            pass
        MQTT_BROKER = os.getenv("MQTT_BROKER")
        MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
        MQTT_USERNAME = os.getenv("MQTT_USERNAME")
        MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
        MQTT_TLS = os.getenv("MQTT_TLS", "0")

        self.mqtt_client = None
        if MQTT_BROKER:
            try:
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                if MQTT_USERNAME:
                    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
                if MQTT_TLS == "1" or MQTT_PORT == 8883:
                    client.tls_set()
                client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
                client.loop_start()
                self.mqtt_client = client
                print("MQTT connected to", MQTT_BROKER)
            except Exception as e:
                print("Failed to connect MQTT broker:", e)
                self.mqtt_client = None

        # ZeroMQ PUB socket setup (fallback)
        context = zmq.Context()
        self.zmq_socket = context.socket(zmq.PUB)
        self.zmq_socket.bind("tcp://*:5556")  # Change port as needed

    def setup(self) -> None:
        video_config = self.picam2.create_video_configuration(
            main={"size": self.config.main_size, "format": "RGB888"},
            lores={"size": self.config.lores_size, "format": "YUV420"},
            controls={"FrameRate": self.config.fps},
        )
        self.picam2.configure(video_config)

    def start(self) -> None:
        self.setup()
        self.picam2.start()
        time.sleep(self.config.warmup_sec)

    def stop(self) -> None:
        self.picam2.stop()

    def _extract_luma(self, lores_frame: np.ndarray) -> np.ndarray:
        h = self.config.lores_size[1]

        if lores_frame.ndim == 2:
            # YUV420 planar frames store Y in the first h rows.
            if lores_frame.shape[0] >= h:
                return lores_frame[:h, :].astype(np.float32, copy=False)
            return lores_frame.astype(np.float32, copy=False)

        if lores_frame.ndim == 3:
            if lores_frame.shape[2] == 1:
                return lores_frame[:, :, 0].astype(np.float32, copy=False)
            if lores_frame.shape[2] >= 3:
                return np.mean(lores_frame[:, :, :3], axis=2, dtype=np.float32)

        raise ValueError(f"Unsupported lores frame shape: {lores_frame.shape}")

    def _motion_ratio(self, luma: np.ndarray) -> float:
        if self._background is None:
            self._background = luma.copy()
            return 0.0

        diff = np.abs(luma - self._background)
        moving_pixels = diff > self.config.pixel_diff_threshold
        ratio = float(np.mean(moving_pixels))

        self._background = (
            (1.0 - self.config.background_alpha) * self._background
            + self.config.background_alpha * luma
        )
        return ratio

    def _save_motion_frame(self, timestamp: str, ratio: float) -> None:
        if not self.config.save_motion_frames:
            print(f"Motion detected ({ratio:.3f}), saving disabled.")
            return
        output_dir = "captures"
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        filename = output_path / f"motion_{timestamp}.jpg"
        self.picam2.capture_file(str(filename), name="main")
        print(f"Motion detected ({ratio:.3f}), saved: {filename}")

    def _publish_motion_frame(self, timestamp: str) -> None:
        """
        Publish to MQTT topic 'pwp/motion' with payload:
        { "camera_id": "<mac>", "motion_id": "<timestamp>", "image_b64": "<base64 jpeg>" }
        Falls back to ZMQ multipart (timestamp, metadata, raw bytes) if MQTT unavailable.
        """
        try:
            # camera id (MAC)
            mac_int = uuid.getnode()
            camera_mac = ":".join(f"{(mac_int >> i) & 0xFF:02x}" for i in range(40, -1, -8))

            # capture lores JPEG to temp file
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                tmp_name = tf.name
            try:
                # Try to capture lores directly as JPEG
                self.picam2.capture_file(tmp_name, name="lores")
            except Exception:
                # Fallback: capture array and save via PIL
                arr = self.picam2.capture_array("lores")
                if arr.ndim == 2:
                    img = Image.fromarray(arr)
                else:
                    img = Image.fromarray(arr[:, :, :3])
                img.save(tmp_name, format="JPEG")

            with open(tmp_name, "rb") as f:
                img_bytes = f.read()
            try:
                os.remove(tmp_name)
            except Exception:
                pass

            image_b64 = base64.b64encode(img_bytes).decode("ascii")
            payload = {
                "camera_id": camera_mac,
                "motion_id": timestamp,
                "image_b64": image_b64,
            }

            if self.mqtt_client:
                self.mqtt_client.publish("pwp/motion", json.dumps(payload), qos=1)
                print(f"Published motion to pwp/motion: {timestamp} ({len(img_bytes)} bytes)")
            else:
                # fallback to existing zmq behavior (send metadata + raw bytes)
                metadata = {
                    "timestamp": timestamp,
                    "camera_id": camera_mac,
                    "resolution": {
                        "width": int(self.config.main_size[0]),
                        "height": int(self.config.main_size[1]),
                    },
                    "fps": int(self.config.fps),
                }
                self.zmq_socket.send_multipart(
                    [
                        timestamp.encode("utf-8"),
                        json.dumps(metadata).encode("utf-8"),
                        img_bytes,
                    ]
                )
                print("MQTT not connected — sent via ZMQ fallback.")
        except Exception as e:
            print("Failed to publish motion frame:", e)

    def _print_stats(self, motion_ratio: float) -> None:
        if motion_ratio > self._stats_peak_ratio:
            self._stats_peak_ratio = motion_ratio

        now = time.perf_counter()
        elapsed = now - self._stats_window_start
        stats_interval_sec = 2.0
        if elapsed < stats_interval_sec:
            return

        fps = self._frame_count / elapsed if elapsed > 0 else 0.0
        print(f"Detector FPS: {fps:.1f}, Motion Ratio: {self._stats_peak_ratio:.4f}")
        print(f"Resolution: {self.config.main_size[0]}x{self.config.main_size[1]}, "
              f"Pixel Threshold: {self.config.pixel_diff_threshold}, "
              f"Motion Threshold: {self.config.motion_ratio_threshold:.3f}")
        self._frame_count = 0
        self._stats_peak_ratio = 0.0
        self._stats_window_start = now

    def _check_config_changed(self) -> bool:
        """Check if config.yaml has been modified. Returns True if changed."""
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime != self.config_mtime:
                print(f"Config file changed detected! Restarting...")
                return True
        except OSError:
            pass
        return False

    def run(self) -> None:
        self.start()
        print("Motion detector running. Press Ctrl+C to stop.")

        try:
            config_check_counter = 0
            config_check_interval = 30  # Check every 30 frames (~1 second at 30 fps)
            
            while True:
                lores_frame = self.picam2.capture_array("lores")
                luma = self._extract_luma(lores_frame)
                ratio = self._motion_ratio(luma)

                now = time.monotonic()
                if (
                    ratio >= self.config.motion_ratio_threshold
                    and (now - self._last_event_time) >= self.config.event_cooldown_sec
                ):
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    millis = int((time.time() % 1) * 1000)
                    event_id = f"{timestamp}_{millis:03d}"
                    self._save_motion_frame(event_id, ratio)
                    self._publish_motion_frame(event_id)
                    self._last_event_time = now

                self._frame_count += 1
                self._print_stats(ratio)
                
                # Periodically check if config has changed
                config_check_counter += 1
                if config_check_counter >= config_check_interval:
                    if self._check_config_changed():
                        print("Exiting to trigger container restart...")
                        break
                    config_check_counter = 0
        except KeyboardInterrupt:
            print("Stopping motion detector...")
        finally:
            self.stop()

def parse_args() -> tuple[str, DetectorConfig]:
    parser = argparse.ArgumentParser(description="Fast modular motion detection")
    parser.add_argument("--config", type=str, default="config.yaml")
    args = parser.parse_args()
    config = load_config(args.config)
    return args.config, config

def main() -> None:
    config_path, config = parse_args()
    detector = MotionDetector(config, config_path)
    detector.run()

if __name__ == "__main__":
    main()
