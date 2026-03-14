"""Fast, modular motion detection with Picamera2.

Motion detection runs on a low-resolution luminance stream for speed.
When motion is detected, a full-resolution image is saved.

Author: Akash Bappy
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from picamera2 import Picamera2
import zmq


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
	def __init__(self, config: DetectorConfig) -> None:
		self.config = config
		self.picam2 = Picamera2()
		self._background: np.ndarray | None = None
		self._last_event_time = 0.0
		self._frame_count = 0
		self._stats_peak_ratio = 0.0
		self._stats_window_start = time.perf_counter()
		# ZeroMQ PUB socket setup
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
		frame = self.picam2.capture_array("main")
		image_bytes = frame.tobytes()
		metadata = {
			"timestamp": timestamp,
			"shape": list(frame.shape),
			"dtype": str(frame.dtype),
			"resolution": {
				"width": int(self.config.main_size[0]),
				"height": int(self.config.main_size[1]),
			},
			"fps": int(self.config.fps),
			"motion_threshold": float(self.config.motion_ratio_threshold),
			"size_bytes": len(image_bytes),
		}
		self.zmq_socket.send_multipart(
			[
				timestamp.encode("utf-8"),
				json.dumps(metadata).encode("utf-8"),
				image_bytes,
			]
		)

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
		self._frame_count = 0
		self._stats_peak_ratio = 0.0
		self._stats_window_start = now

	def run(self) -> None:
		self.start()
		print("Motion detector running. Press Ctrl+C to stop.")

		try:
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
		except KeyboardInterrupt:
			print("Stopping motion detector...")
		finally:
			self.stop()

def parse_args() -> DetectorConfig:
	parser = argparse.ArgumentParser(description="Fast modular motion detection")
	parser.add_argument("--config", type=str, default="config.yaml")
	args = parser.parse_args()
	return load_config(args.config)

def main() -> None:
	config = parse_args()
	detector = MotionDetector(config)
	detector.run()

if __name__ == "__main__":
	main()