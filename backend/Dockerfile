FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System deps:
# - ffmpeg: audio extraction for transcription
# - WeasyPrint runtime: libpango/cairo/gdk-pixbuf/libffi for PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 \
    libffi8 libjpeg62-turbo shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh && mkdir -p /data/uploads /data/media

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["api"]
