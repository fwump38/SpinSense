ARG PYTHON_BASE=python:3.11-slim-bullseye
FROM ${PYTHON_BASE}

# The default image is multi-arch and supports amd64 and arm64 hosts,
# including Orange Pi Zero 2W running DietPi (Debian Trixie-based).
# The Docker container uses its own Debian-based Python runtime, so the host OS
# only matters for Docker installation and hardware access, not the image internals.

LABEL maintainer="SpinSense Contributors"
LABEL description="SpinSense - Vinyl Record Player integration for Home Assistant"

WORKDIR /app

# Install system dependencies
# Including dev packages needed for sounddevice and numpy compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    alsa-utils \
    libsndfile1 \
    libffi-dev \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from the main folder
COPY requirements.txt .

# Install Python dependencies
# Use no-cache to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything from the main project folder
COPY . .

# Make sure entrypoint is executable
RUN chmod +x ./docker/entrypoint.sh

ENTRYPOINT ["./docker/entrypoint.sh"]
