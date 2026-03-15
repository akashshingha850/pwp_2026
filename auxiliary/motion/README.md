# Motion Detector Container (Raspberry Pi)

This directory contains a small containerized wrapper for `motion.py` targeted at Raspberry Pi
devices using the `libcamera` / `picamera2` stack.

**Quick start**

- Build the image on a Pi (from this directory):

```bash
docker build -t motion-detector:pi .
```

- Run the container (grants camera access and mounts config + captures):

```bash
docker run --rm -it \
  --network host \
  --privileged \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/captures:/app/captures \
  motion-detector:pi
```

Prerequisites

- Raspberry Pi OS with camera stack enabled and camera connected.
- If running from a container: ensure the host kernel and device permissions allow camera access (run with `--privileged` or configure devices appropriately).

Configuration

- Edit `config.yaml` in the workspace root to tune capture paths, sensitivity, and MQTT/ZMQ endpoints used by `motion.py`.
- Captured media will be stored in the `captures/` directory mounted into the container.

Run via VS Code task (recommended)

- The workspace includes a reusable task that runs the container with correct mounts. From the workspace root run the task labeled "Run Motion Container (Pi Camera)" or run this command in the workspace:

```bash
docker run --rm -it --network host --privileged -v ${PWD}/config.yaml:/app/config.yaml:ro -v ${PWD}/captures:/app/captures motion-detector:pi
```

Subscriber (consume events)

- To consume messages produced by `motion.py` you can run the provided `subscriber.py` from the host (or another container):

```bash
python subscriber.py --endpoint tcp://127.0.0.1:5556
```

Troubleshooting

- If the camera device is not accessible inside the container, try running without `--privileged` and instead pass the specific device nodes and group permissions, or verify `libcamera` works on the host first.
- Check `captures/` permissions if files are not being written by the container.

If you want, I can also update the top-level README to reference this quick-start. 
