"""ZeroMQ subscriber for motion frames.

Receives multipart messages from motion.py publisher:
1) timestamp (utf-8)
2) metadata JSON (utf-8)
3) raw frame bytes
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import zmq


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Subscribe to motion frame stream")
	parser.add_argument("--endpoint", default="tcp://127.0.0.1:5556")
	parser.add_argument("--save-dir", default="received")
	parser.add_argument("--save", action="store_true", help="Save received frames as raw .npy files")
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	save_dir = Path(args.save_dir)
	if args.save:
		save_dir.mkdir(parents=True, exist_ok=True)

	context = zmq.Context()
	socket = context.socket(zmq.SUB)
	socket.connect(args.endpoint)
	socket.setsockopt_string(zmq.SUBSCRIBE, "")
	print(f"Subscribed to {args.endpoint}")

	try:
		while True:
			parts = socket.recv_multipart()
			if len(parts) != 3:
				print(f"Unexpected message parts: {len(parts)}")
				continue

			timestamp = parts[0].decode("utf-8", errors="replace")
			metadata = json.loads(parts[1].decode("utf-8"))
			image_bytes = parts[2]

			dtype = np.dtype(metadata.get("dtype", "uint8"))
			shape = tuple(metadata.get("shape", []))
			if not shape:
				res = metadata.get("resolution", {})
				shape = (int(res.get("height", 0)), int(res.get("width", 0)), 3)

			frame = np.frombuffer(image_bytes, dtype=dtype)
			expected = int(np.prod(shape)) if all(dim > 0 for dim in shape) else 0
			if expected == 0 or frame.size != expected:
				print(
					"Bad frame size:",
					f"timestamp={timestamp}",
					f"shape={shape}",
					f"dtype={dtype}",
					f"bytes={len(image_bytes)}",
				)
				continue

			frame = frame.reshape(shape)
			print(
				f"timestamp={timestamp} "
				f"resolution={metadata.get('resolution')} "
				f"fps={metadata.get('fps')} "
				f"motion_threshold={metadata.get('motion_threshold')} "
				f"size_bytes={metadata.get('size_bytes')}"
			)

			if args.save:
				out_path = save_dir / f"{timestamp}.npy"
				np.save(out_path, frame)
				print(f"Saved: {out_path}")
	except KeyboardInterrupt:
		print("Stopping subscriber...")
	finally:
		socket.close(0)
		context.term()


if __name__ == "__main__":
	main()
