"""Fast, modular motion detection with Picamera2.

Motion detection runs on a low-resolution luminance stream for speed.
When motion is detected, a full-resolution image is saved.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from picamera2 import Picamera2


@dataclass
class DetectorConfig:
	main_size: tuple[int, int] = (1920, 1080)
	lores_size: tuple[int, int] = (320, 240)
	fps: int = 30
	pixel_diff_threshold: int = 20
	motion_ratio_threshold: float = 0.02
	background_alpha: float = 0.08
	event_cooldown_sec: float = 1.0
	warmup_sec: float = 0.5
	stats_interval_sec: float = 2.0
	output_dir: str = "captures"


class MotionDetector:
	def __init__(self, config: DetectorConfig) -> None:
		self.config = config
		self.picam2 = Picamera2()
		self._background: np.ndarray | None = None
		self._last_event_time = 0.0
		self._frame_count = 0
		self._stats_peak_ratio = 0.0
		self._stats_window_start = time.perf_counter()

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

	def _save_motion_frame(self, ratio: float) -> None:
		output_path = Path(self.config.output_dir)
		output_path.mkdir(parents=True, exist_ok=True)

		timestamp = time.strftime("%Y%m%d_%H%M%S")
		millis = int((time.time() % 1) * 1000)
		filename = output_path / f"motion_{timestamp}_{millis:03d}.jpg"

		self.picam2.capture_file(str(filename), name="main")
		print(f"Motion detected ({ratio:.3f}), saved: {filename}")

	def _print_stats(self, motion_ratio: float) -> None:
		if motion_ratio > self._stats_peak_ratio:
			self._stats_peak_ratio = motion_ratio

		now = time.perf_counter()
		elapsed = now - self._stats_window_start
		if elapsed < self.config.stats_interval_sec:
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
					self._save_motion_frame(ratio)
					self._last_event_time = now

				self._frame_count += 1
				self._print_stats(ratio)
		except KeyboardInterrupt:
			print("Stopping motion detector...")
		finally:
			self.stop()


def parse_args() -> DetectorConfig:
	parser = argparse.ArgumentParser(description="Fast modular motion detection")
	parser.add_argument("--fps", type=int, default=30)
	parser.add_argument("--main-width", type=int, default=1920)
	parser.add_argument("--main-height", type=int, default=1080)
	parser.add_argument("--lores-width", type=int, default=320)
	parser.add_argument("--lores-height", type=int, default=240)
	parser.add_argument("--pixel-threshold", type=int, default=20)
	parser.add_argument("--motion-threshold", type=float, default=0.02)
	parser.add_argument("--background-alpha", type=float, default=0.08)
	parser.add_argument("--cooldown", type=float, default=1.0)
	parser.add_argument("--output-dir", type=str, default="captures")
	args = parser.parse_args()

	return DetectorConfig(
		main_size=(args.main_width, args.main_height),
		lores_size=(args.lores_width, args.lores_height),
		fps=args.fps,
		pixel_diff_threshold=args.pixel_threshold,
		motion_ratio_threshold=args.motion_threshold,
		background_alpha=args.background_alpha,
		event_cooldown_sec=args.cooldown,
		output_dir=args.output_dir,
	)


def main() -> None:
	config = parse_args()
	detector = MotionDetector(config)
	detector.run()


if __name__ == "__main__":
	main()