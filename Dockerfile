# Webhook server pre režim „napíšem botovi na WhatsAppe a odpovie hlasovkou".
# Funguje na Render, Railway, Fly.io aj na vlastnom VPS:
#   docker build -t edupage-digest .
#   docker run --env-file .env -p 8000:8000 edupage-digest
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "webhook_server.py"]
