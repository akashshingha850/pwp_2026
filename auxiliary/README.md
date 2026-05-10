# Auxiliary Service

This directory contains the edge-side auxiliary services for EyesEdge:

- `motion/` runs the motion detector container on Raspberry Pi hardware.
- `config/` listens for configuration updates.

The `.draft/` directory is intentionally ignored here; it contains discarded experiments and older prototypes.

## Prerequisites

- Raspberry Pi OS or another Linux system with camera access if you want to run the motion detector.
- Docker and Docker Compose if you want to run the services in containers.
## Configuration

The motion service reads settings from `config.yaml` in this directory. The default values include frame size, motion thresholds, cooldown timing, and whether to save motion frames.

The Docker Compose stack also expects an `.env` file for the containerized services.

## Run with Docker Compose

From the `auxiliary/` directory, start both services with:

```bash
docker compose up --build
```

This launches:

- `motion` with camera access, host networking, and mounts for `config.yaml` and `captures/`
- `config` as the configuration listener container

## Run the motion container directly

If you only need the motion detector, build and run the image from `auxiliary/motion/`:

```bash
cd motion
docker build -t motion-detector:pi .
docker run --rm -it \
  --network host \
  --privileged \
  -v $(pwd)/../config.yaml:/app/config.yaml:ro \
  -v $(pwd)/../captures:/app/captures \
  motion-detector:pi
```

Use this mode when you want to test the camera pipeline independently of the compose stack.

## Directory Layout

- `motion/` contains the Raspberry Pi container and motion detector entry point.
- `config/` contains the configuration listener container.
- `captures/` is where motion snapshots are stored when frame saving is enabled.
- `config.yaml` holds the shared motion settings.

## Troubleshooting

- If the camera is not accessible inside the container, verify that `libcamera` works on the host first.
- If `docker compose up` fails, make sure the required `.env` file exists in this directory.
