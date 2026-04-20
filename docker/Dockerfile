ARG PYTHON_BASE=python:3.11-slim-bookworm

# --- Stage 1: Build songrec CLI from source (no GUI dependencies) ---
FROM rust:1-bookworm AS songrec-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libasound2-dev \
    libclang-dev \
    libsoup-3.0-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN cargo install songrec --no-default-features

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
