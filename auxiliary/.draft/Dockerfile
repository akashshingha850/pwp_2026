FROM debian:bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
     ca-certificates \
     wget \
     gnupg \
  && wget -qO- https://archive.raspberrypi.com/debian/raspberrypi.gpg.key | gpg --dearmor -o /usr/share/keyrings/raspberrypi-archive-keyring.gpg \
  && echo "deb [signed-by=/usr/share/keyrings/raspberrypi-archive-keyring.gpg] http://archive.raspberrypi.com/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
     python3 \
     python3-picamera2 \
     python3-zmq \
     python3-yaml \
     python3-numpy \
    && rm -rf /var/lib/apt/lists/*

COPY motion.py config.yaml subscriber.py ./

CMD ["python3", "motion.py"]
