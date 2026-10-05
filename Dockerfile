FROM python:3.12-slim

# ffmpeg does the merging, thumbnails, MP3 extraction and re-encoding.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy requirements first so the dependency layer survives code edits.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ ./bot/

# Run as a non-root user; it owns the two writable directories.
RUN useradd --create-home --uid 10001 botuser \
 && mkdir -p /app/data /app/downloads \
 && chown -R botuser:botuser /app
USER botuser

ENV WORK_DIR=/app/downloads \
    DATABASE_PATH=/app/data/bot.sqlite3

CMD ["python", "-m", "bot"]
