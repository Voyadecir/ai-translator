# Minimal, reliable Python base image
FROM python:3.11-slim

# Optional: if your API does PDF OCR locally, keep these. If not, you can remove the apt-get block.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    imagemagick \
  && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python deps first (leverages Docker layer cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of your code
# Your logs showed code at //app/src/python/ai_translator/...
# so copying the whole repo is safest.
COPY . /app

# Make sure Python can import from src/python
ENV PYTHONPATH=/app/src/python

# Start the FastAPI server. $PORT is provided by Render at runtime.
CMD ["sh", "-c", "uvicorn ai_translator.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
