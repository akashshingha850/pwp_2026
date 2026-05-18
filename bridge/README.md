# EyesEdge Bridge

Connects the Pi-side auxiliary services to the cloud REST API over MQTT.  
A browser-based management console is served at the API root (`/`).

## Architecture

![EyesEdge System Architecture](architecture.png)

> Open [`architecture.drawio`](architecture.drawio) in draw.io for the interactive version.

## What it does

### Bridge service (`bridge.py`)
- **Motion ingest** — subscribes to `pwp/motion`, decodes the JPEG, saves it locally, then POSTs a `MotionEvent` + `Image` record to the API.
- **Config push** — polls `/api/cameras/` every N seconds and publishes `{main_width, main_height, fps}` to `pwp/config` whenever a camera changes.
- **File server** — serves captured JPEGs over HTTP on port `9000` so the `Image.filepath` URLs are reachable from the browser.

### Web client (`/`)
A single-page management console is served at the Django API root.  
Open `http://localhost:8000/` in a browser after starting the API.

Features:
- **Login** — authenticates against `/api/token/` and stores the session token.
- **Dashboard** — live summary counts of cameras, motion events, and images.
- **Cameras** — list, add, edit (inline form), and delete cameras; drill down into a camera's motion events.
- **Motion Events** — list all events; view the JPEG images captured for each event.
- **Images** — full image gallery with file-size metadata and direct links.
- **Error display** — all HTTP errors show the status code and API detail message inline.

## Sources

| Library | Purpose | License |
|---|---|---|
| [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) | MQTT client | EPL-2.0 |
| [requests](https://requests.readthedocs.io/) | HTTP REST calls | Apache 2.0 |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | `.env` config | BSD |
| [Inter font](https://fonts.google.com/specimen/Inter) | Web client typography | OFL |

Course material used as reference for TLS setup and MQTT pub/sub patterns:  
https://lovelace.oulu.fi/ohjelmoitava-web/ohjelmoitava-web/exercise-4-implementing-hypermedia-clients/

## Setup

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

Key variables:

| Variable | Description |
|---|---|
| `MQTT_BROKER` | EMQX Cloud hostname |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | MQTT credentials |
| `API_BASE` | Django API URL (`http://host.docker.internal:8000` for Docker, `http://127.0.0.1:8000` for local) |
| `API_TOKEN` | DRF token — get one with `python manage.py drf_create_token <user>` |
| `CAMERA_MAP` | Comma-separated `mac=uuid` pairs mapping Pi MAC addresses to Camera UUIDs in the API |
| `BRIDGE_PUBLIC_URL` | Public URL of the file server (used as `Image.filepath` in the API) |

### CAMERA_MAP example

After adding a camera in the web client, copy its UUID from `/api/cameras/` and map it to the Pi's MAC:

```
CAMERA_MAP=dc:a6:32:51:e5:02=60ddc147-14fc-4fd9-b7a8-5b46246be866
```

Multiple cameras: comma-separated.

## Run with Docker (recommended)

```bash
docker compose up --build -d    # build and start
docker logs -f eyesedge-bridge  # live logs
docker compose stop             # stop
docker compose up -d            # restart without rebuild
```

## Run locally

```bash
pip install -r requirements.txt
python bridge.py
```

Sample log output when running:

```
2026-05-17 10:00:01 [INFO] bridge: CAMERA_MAP loaded: 1 entries
2026-05-17 10:00:01 [INFO] bridge: File server listening on 0.0.0.0:9000 (root=/captures)
2026-05-17 10:00:01 [INFO] bridge: Connecting MQTT q1fd1412.ala.eu-central-1.emqxsl.com:8883 (TLS=True) …
2026-05-17 10:00:02 [INFO] bridge: MQTT connected — subscribing to pwp/motion
2026-05-17 10:00:12 [INFO] bridge: Published config for camera 60ddc147-... → pwp/config: {'main_width': 1280, 'main_height': 720, 'fps': 25}
2026-05-17 10:00:45 [INFO] bridge: Stored motion 1747473645 for camera dc:a6:32:51:e5:02 (38420 bytes) → http://127.0.0.1:9000/motion_1747473645.jpg
```

## Linting

[ruff](https://docs.astral.sh/ruff/) is used for linting and style checking:

```bash
pip install ruff          # already in requirements.txt
ruff check bridge.py      # lint
ruff check --fix bridge.py  # auto-fix safe issues
```

Configuration is in [`ruff.toml`](ruff.toml).

## Directory layout

```
bridge/
  bridge.py           # main service
  Dockerfile
  docker-compose.yml
  requirements.txt
  ruff.toml           # linting config
  .env                # local config (git-ignored)
  .env.example        # template
  architecture.drawio # system architecture diagram
  captures/           # saved JPEGs (created at runtime)

api/eyesedge/templates/eyesedge/
  client.html         # single-page web client (served at /)
```
