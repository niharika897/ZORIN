# =========================================================
# ZORIN CENTRAL AI BRAIN - PRODUCTION DOCKERFILE
# =========================================================

FROM python:3.11-slim

# Install system dependencies including audio & build libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libportaudio2 \
    libasound2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency requirements
COPY requirements-server.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt

# Copy backend application source code
COPY backend/ ./backend/
COPY core/ ./core/
COPY config/ ./config/
COPY intelligence/ ./intelligence/
COPY memory/ ./memory/
COPY device/ ./device/
COPY voice/ ./voice/
COPY start_server.py .

# Create persistent storage directory
RUN mkdir -p /app/data /app/models

# Expose Central Brain port
EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch central server on all interfaces
CMD ["python", "start_server.py"]
