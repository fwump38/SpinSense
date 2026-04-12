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

## 2. Standalone Engine (Docker) for single-board computers

SpinSense can run on small ARM systems such as Raspberry Pi Zero 2W (or similar) with a USB audio interface attached to the turntable.

### Prerequisites

- Single Board Computer like Raspberry Pi Zero 2W
- Docker installed on the device
- USB audio interface connected to the board
- MQTT broker reachable on the network

### Quick start

1. Copy `config.json` into the project root.
2. Edit `config.json` with your MQTT broker settings and audio device options before building the image.
3. Build the Docker image:
   ```bash
   docker compose build
   ```
4. Start the service:
   ```bash
   docker compose up -d
   ```

### Configuration

- `config.json` is the primary configuration source.
- Edit `config.json` directly before building or running the container.

Recommended fields to update:

- `MQTT.Broker.Host`
- `MQTT.Broker.Port`
- `MQTT.Broker.User`
- `MQTT.Broker.Password`
- `Audio.Volume_Threshold`
- `Audio.Song_Sample_Length`
- `Audio.New_Song_Silence_Interval`
- `Audio.Stopped_Silence_Interval`

### Notes for Pi Zero

- The Docker setup already exposes USB audio access via `/dev/snd` and host IPC.
- Use a USB audio interface with a supported sample rate; `48000` is preferred if available.
- If `48000` isn't supported, try `44100` or `16000`.
- Connect a USB audio interface with an input device; the engine will auto-detect USB audio if `AUDIO_DEVICE` is blank.
- Build times may be long on Pi Zero due to `numpy` and `sounddevice` compilation.

## 3. Recommended Setup

For the cleanest experience:

- Use Docker to build and run the standalone recognition engine.
- Run `core_engine.py` inside the container, with `config.json` mounted from the host.
- Use the same MQTT broker that Home Assistant is configured to use.

## 4. Troubleshooting

- If the engine cannot find your USB audio device, set `AUDIO_DEVICE` to the device name or use `AUDIO_DEVICE_INDEX`.
- If Home Assistant does not show the `SpinSense` integration, confirm the `custom_components/spinsense/` folder is in your HA config directory and restart HA.
- If audio recognition fails, verify the USB audio input works using `arecord -l` and test with a recording tool.
