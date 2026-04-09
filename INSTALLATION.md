# SpinSense Installation Guide

This repository contains two complementary pieces:

- `custom_components/spinsense/`: a Home Assistant custom integration that creates a media player entity from MQTT data.
- `core_engine.py`: the standalone recognition engine that listens to USB audio, recognizes the playing record, and publishes metadata to MQTT.

## 1. Home Assistant Custom Integration

### Option A: Install via HACS (Recommended)

1. In Home Assistant, open HACS.
2. Go to `Integrations` → `+ Explore & add repositories`.
3. Add this repository URL: `https://github.com/fwump38/SpinSense`.
4. Install `SpinSense` from HACS.
5. Restart Home Assistant.
6. Open `Settings -> Devices & Services -> Add Integration` and add `SpinSense`.
7. Enter your MQTT broker settings and select the USB audio device for the engine.
8. After setup, the `Vinyl Record Player` media player entity will appear in Home Assistant.

### Option B: Manual installation

1. Copy the `custom_components/spinsense/` folder into your Home Assistant config directory under `custom_components/`.

   Example:
   ```bash
   cp -r custom_components/spinsense /config/custom_components/
   ```

2. Restart Home Assistant.

3. Open Home Assistant and go to `Settings -> Devices & Services -> Add Integration`.

4. Search for `SpinSense` and follow the configuration flow.

5. Enter your MQTT broker settings and select the USB audio device for the engine.

6. After setup, the `Vinyl Record Player` media player entity will appear in Home Assistant.

## 2. Raspberry Pi Zero Standalone Engine (Docker)

SpinSense is designed to run on Raspberry Pi Zero with a USB audio interface attached to the turntable.

### Prerequisites

- Raspberry Pi Zero W or Zero 2 W
- Raspberry Pi OS or similar with Docker installed
- USB audio interface connected to the Pi Zero
- MQTT broker reachable on the network

### Quick start

1. Copy `config.json` and `.env.example` into the project root.
2. Rename `.env.example` to `.env` and update values.
3. Build the Docker image:
   ```bash
   docker compose build
   ```

   If you are building directly on a Raspberry Pi Zero and your base image requires an ARMv6-compatible variant, use the build arg:
   ```bash
   docker compose build --build-arg PYTHON_BASE=arm32v6/python:3.11-slim-bullseye
   ```

4. Start the service:
   ```bash
   docker compose up -d
   ```

### Configuration

The engine reads configuration from these sources:

- `config.json` in the project root
- environment variables defined in `.env`

Recommended environment variables:

- `MQTT_HOST`
- `MQTT_PORT`
- `MQTT_USER`
- `MQTT_PASSWORD`
- `AUDIO_DEVICE`
- `AUDIO_SAMPLE_RATE`
- `AUDIO_THRESHOLD`
- `SILENCE_INTERVAL`

### Notes for Pi Zero

- Use `AUDIO_SAMPLE_RATE=48000` if your USB audio interface supports it. If not, try `44100` or `16000`.
- Connect a USB audio interface with an input device; the engine will auto-detect USB audio if `AUDIO_DEVICE` is blank.
- Build times may be long on Pi Zero due to `numpy` and `sounddevice` compilation.

## 3. Running Without Docker

If you want to run the engine directly on the Pi Zero:

1. Install system dependencies:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip portaudio19-dev libsndfile1 libffi-dev gcc g++ make
   ```
2. Create a virtual environment and install requirements:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run the engine:
   ```bash
   python3 core_engine.py
   ```

## 4. Recommended Setup

For the cleanest experience:

- Run `core_engine.py` on the Raspberry Pi Zero as the recognition engine.
- Install the Home Assistant custom integration in your HA instance.
- Configure the engine to use the same MQTT broker that Home Assistant uses.

## 5. Troubleshooting

- If the engine cannot find your USB audio device, set `AUDIO_DEVICE` to the device name or use `AUDIO_DEVICE_INDEX`.
- If Home Assistant does not show the `SpinSense` integration, confirm the `custom_components/spinsense/` folder is in your HA config directory and restart HA.
- If audio recognition fails, verify the USB audio input works using `arecord -l` and test with a recording tool.
