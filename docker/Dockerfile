ARG PYTHON_BASE=python:3.11-slim-trixie

# --- Stage 1: Pull pre-built songrec binary from cached builder image ---
# Rebuild this image by running the songrec-builder workflow manually or on Dockerfile changes.
# See .github/workflows/songrec-builder.yml
FROM ghcr.io/fwump38/spinsense/songrec-builder:latest AS songrec-builder

# --- Stage 2: Runtime image ---
FROM ${PYTHON_BASE}

LABEL maintainer="SpinSense Contributors"
LABEL description="SpinSense - Turn Table integration for Home Assistant"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev \
    portaudio19-dev \
    alsa-utils \
    libsndfile1 \
    libffi-dev \
    libasound2 \
    libsoup-3.0-0 \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Copy songrec binary from builder
COPY --from=songrec-builder /usr/local/cargo/bin/songrec /usr/local/bin/songrec

# Copy requirements from the main folder
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary application files
COPY core/ ./core/
COPY gui/ ./gui/
COPY core_engine.py .
COPY docker/ ./docker/

# Make sure entrypoint is executable
RUN chmod +x ./docker/entrypoint.sh

ENTRYPOINT ["./docker/entrypoint.sh"]
