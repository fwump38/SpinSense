# SpinSense Installation Guide

This repository contains two complementary pieces:

- `custom_components/spinsense/`: a Home Assistant custom integration that discovers the local SpinSense service and displays live track metadata.
- `core_engine.py`: the standalone recognition engine that listens to USB audio, recognizes the playing record, and serves real-time updates over HTTP/WebSocket.

## 1. Home Assistant Custom Integration

### Option A: Install via HACS (Recommended)

1. In Home Assistant, open HACS.
2. Go to `Integrations` → `+ Explore & add repositories`.
3. Add this repository URL: `https://github.com/fwump38/SpinSense`.
4. Install `SpinSense` from HACS.
5. Restart Home Assistant.
6. Open `Settings -> Devices & Services -> Add Integration` and add `SpinSense`.
6. Home Assistant should discover the SpinSense service automatically via zeroconf.
8. After setup, the `Turn Table` media player entity will appear in Home Assistant.

### Option B: Manual installation

1. Copy the `custom_components/spinsense/` folder into your Home Assistant config directory under `custom_components/`.

   Example:
   ```bash
   cp -r custom_components/spinsense /config/custom_components/
   ```

2. Restart Home Assistant.

3. Open Home Assistant and go to `Settings -> Devices & Services -> Add Integration`.

4. Search for `SpinSense` and follow the configuration flow.

5. Home Assistant should detect your SpinSense service automatically over the local network.

6. After setup, the `Turn Table` media player entity will appear in Home Assistant.

## 2. Standalone Engine (Docker) for single-board computers

SpinSense can run on small ARM systems such as Raspberry Pi Zero 2W (or similar) with a USB audio interface attached to the turntable.

### Prerequisites

- Single Board Computer like Raspberry Pi Zero 2W
- Docker installed on the device
- RCA-to-USB audio capture adapter or USB audio interface connected to the board

### Quick start

Configure your audio settings using environment variables, then run the container:

```bash
docker compose up -d
```

The Docker image is automatically built and published to GitHub Container Registry (GHCR) on every push to the main branch.

### Configuration

SpinSense can run without `config.json`. Use environment variables instead.

Common configuration variables:

- `AUDIO_DEVICE` — audio device name or alias
- `AUDIO_DEVICE_INDEX` — audio device index (optional)
- `AUDIO_THRESHOLD` — volume threshold for detection (default: `0.015`)
- `AUDIO_SAMPLE_LENGTH` — recording length in seconds (default: `5.0`)
- `AUDIO_SAMPLE_RATE` — sample rate in Hz (default: `48000`)
- `SILENCE_INTERVAL` — silence timeout in seconds (default: `5.0`)
- `LOG_LEVEL` — logging verbosity (default: `info`)

If you still want to override settings from a JSON file, `config.json` remains supported but is no longer required.

Example `docker-compose.yml` service configuration:

```yaml
services:
  spinsense:
    image: ghcr.io/fwump38/spinsense:latest
    container_name: spinsense
    restart: unless-stopped
    devices:
      - "/dev/snd:/dev/snd"
    group_add:
      - "29"
    ipc: host
    network_mode: host
    volumes:
      - /tmp:/tmp
    environment:
      - AUDIO_DEVICE=${AUDIO_DEVICE:-}
      - AUDIO_DEVICE_INDEX=${AUDIO_DEVICE_INDEX:-}
      - AUDIO_THRESHOLD=${AUDIO_THRESHOLD:-0.015}
      - AUDIO_SAMPLE_LENGTH=${AUDIO_SAMPLE_LENGTH:-5.0}
      - AUDIO_SAMPLE_RATE=${AUDIO_SAMPLE_RATE:-48000}
      - SILENCE_INTERVAL=${SILENCE_INTERVAL:-5.0}
      - LOG_LEVEL=${LOG_LEVEL:-info}
```

Use a `.env` file or Portainer stack environment section to control runtime settings.

### Notes for Pi Zero

- The Docker setup already exposes USB audio access via `/dev/snd` and host IPC.
- Use an RCA-to-USB capture adapter or USB audio interface with a supported sample rate; `48000` is preferred if available.
- If `48000` isn't supported, try `44100` or `16000`.
- Connect a USB audio capture device with an input channel; the engine will auto-detect USB audio if `AUDIO_DEVICE` is blank.

## 3. Recommended Setup

For the cleanest experience:

- Use Docker to run the standalone recognition engine.
- Configure runtime settings with environment variables instead of mounting `config.json`.
- Ensure the SpinSense service is reachable from Home Assistant on port `8000`.

## 3.5. Configuring USB Audio Devices

When you connect a USB audio interface (such as an RCA-to-USB adapter labeled "ClearClick: USB Audio"), follow these steps to ensure it's properly detected and configured:

### Step 1: Verify Device Detection

The web UI at `http://localhost:8000` displays "Available Audio Input Devices" in the logs. You can also query available devices via:

```bash
curl http://localhost:8000/api/devices
```

Look for your USB device in the list (e.g., "ClearClick: USB Audio (hw:2,0)").

### Step 2: Configure the Device

**Option A: Environment Variable (Recommended for Docker)**

Set the `AUDIO_DEVICE` environment variable to the exact device name before starting the container:

```yaml
# docker-compose.yml
services:
  spinsense:
    # ... other settings ...
    environment:
      - AUDIO_DEVICE=ClearClick: USB Audio (hw:2,0)
      - AUDIO_SAMPLE_RATE=48000
```

Or create a `.env` file:

```bash
AUDIO_DEVICE=ClearClick: USB Audio (hw:2,0)
AUDIO_SAMPLE_RATE=48000
```

**Option B: Web GUI**

1. Open the SpinSense web UI at `http://localhost:8000`.
2. Under **Configuration → Hardware**, select your USB device from the "Audio Input Device" dropdown.
3. Click **Save Settings**.
4. **Restart the engine** using the "Stop" button, then "Start Listening" to apply the changes.

### Step 3: Verify Audio Levels

After configuring the device:

1. Play audio through your turntable.
2. Check the "Audio Input Level (RMS)" meter in the web UI.
3. If no meter movement, the device is not receiving audio — verify your turntable is connected and playing.

## 4. Troubleshooting

### USB Audio Device Not Detected or Not Switching

**Problem**: The USB device appears in the device list but doesn't activate when selected in the GUI.

**Solution**: 
- The engine must be **restarted** for configuration changes to take effect.
- Click the "Stop" button in the web UI to stop the engine.
- Then click "Start Listening" to restart with the new device.
- Check logs to confirm: "Audio Input Level (RMS)" meter should show activity when turntable plays.

**Advanced**: Use Docker logs to see which device the engine detected on startup:

```bash
docker compose logs spinsense | grep "Audio Input Device"
docker compose logs spinsense | grep "Available Audio Input"
```

### Device Not Found After Restart

**Problem**: The selected device disappears from the dropdown or engine fails to start after restart.

**Solution**:
- Device names may vary. Check exact name from `/api/devices` endpoint or Docker logs.
- Try using the numeric index instead: set `AUDIO_DEVICE_INDEX=2` (replace 2 with correct index).
- Verify USB adapter is physically connected before starting the container.
- Some adapters require specific sample rates — try `AUDIO_SAMPLE_RATE=44100` if `48000` fails.

### Audio Recognition Fails

**Problem**: Engine starts but never recognizes tracks, or "Audio Input Level" meter stays at zero.

**Solution**:
- Verify USB audio input: `arecord -l` (Linux/Pi)
- Test recording: `arecord -D hw:2,0 -f S16_LE -r 48000 test.wav` (replace hw:2,0 with your device)
- Play USB-captured audio: `aplay test.wav`
- If meters show activity but no recognition, check Shazam connectivity and song audibility.

### Home Assistant Integration Not Showing Device

- If Home Assistant does not show the `SpinSense` integration, confirm the `custom_components/spinsense/` folder is in your HA config directory and restart HA.
- Verify SpinSense API is accessible: `curl http://<local-ip>:8000/api/info` from Home Assistant.
- Check Home Assistant logs for zeroconf discovery errors.
