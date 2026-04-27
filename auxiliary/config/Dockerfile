FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY config/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY config/config_sub.py ./

CMD ["python3", "config_sub.py"]
