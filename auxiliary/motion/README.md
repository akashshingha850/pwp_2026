# Motion Detector Container (Raspberry Pi)

This setup containerizes `motion.py` with a minimal image approach for Raspberry Pi.

## Build (Dockerfile directly)

```bash
docker build -t motion-detector:pi .
```

## Run on Raspberry Pi

Camera access from containers still requires device permissions, but Python `libcamera`/`picamera2`
dependencies are now installed inside the image.

Run with:

```bash
docker run --rm -it \
  --network host \
  --privileged \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/captures:/app/captures \
  motion-detector:pi
```

## Notes on size

- Uses a minimal Debian base plus Raspberry Pi packages (`python3-picamera2`, `libcamera` stack) installed in-image.
- Uses `.dockerignore` to avoid copying virtualenv/caches into image context.
- Uses `PIP_NO_CACHE_DIR=1` to reduce layer size.

## Subscriber (outside container or another container)

```bash
python subscriber.py --endpoint tcp://127.0.0.1:5556
```
