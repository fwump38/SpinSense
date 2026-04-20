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

The Docker image is automatically built and published to GitHub Container Registry (GHCR) on every version tag push.

> **How builds work**: The songrec binary is compiled once into a separate base image (`songrec-builder`). Release builds pull this prebuilt binary rather than recompiling from source — this keeps release builds fast (under 5 minutes). See [Updating songrec](#updating-songrec) if you need to rebuild the binary.

### Configuration

All configuration is via environment variables:

Common configuration variables:

- `AUDIO_DEVICE` — audio device name or alias
- `AUDIO_DEVICE_INDEX` — audio device index (optional)
- `AUDIO_THRESHOLD` — volume threshold for detection (default: `0.015`)
- `AUDIO_SAMPLE_LENGTH` — recording length in seconds (default: `5.0`)
- `AUDIO_SAMPLE_RATE` — sample rate in Hz (default: `48000`)
- `SILENCE_INTERVAL` — silence timeout in seconds (default: `5.0`)
- `LOG_LEVEL` — logging verbosity (default: `info`)

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
- Configure runtime settings with environment variables.
- Ensure the SpinSense service is reachable from Home Assistant on port `8000`.

## 3.5. Configuring USB Audio Devices

When you connect a USB audio interface (such as an RCA-to-USB adapter labeled "ClearClick: USB Audio"), follow these steps to ensure it's properly detected and configured:

### Step 1: Verify Device Detection

List all audio capture devices on the host:

```bash
arecord -l
```

Look for your USB adapter in the output (e.g., `card 2: CODEC [USB Audio CODEC]`). Note the card and device numbers — you'll need them in the steps below.

You can also query available devices from the running container via:

```bash
curl http://localhost:8000/api/devices
```

### Step 1.5: Verify Supported Sample Rate

Replace `hw:2,0` with your device's card and device numbers from Step 1.

```bash
# Test 48000 Hz (preferred)
arecord -D hw:2,0 -f S16_LE -r 48000 -c 1 -d 1 /dev/null && echo "48000 Hz: supported" || echo "48000 Hz: not supported"

# Test 44100 Hz (fallback)
arecord -D hw:2,0 -f S16_LE -r 44100 -c 1 -d 1 /dev/null && echo "44100 Hz: supported" || echo "44100 Hz: not supported"
```

Set `AUDIO_SAMPLE_RATE` to the highest supported rate.

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
3. Click **Save Settings**. Changes are applied in-memory immediately.

### Step 3: Verify Audio Levels

After configuring the device:

1. Play audio through your turntable.
2. Check the "Audio Input Level (RMS)" meter in the web UI.
3. If no meter movement, the device is not receiving audio — verify your turntable is connected and playing.

### Step 4: Calibrate AUDIO_THRESHOLD

Record 5 seconds in each of the three states below, then read the RMS amplitude. Replace `hw:2,0` with your device. Requires `sox` (`sudo apt install sox`).

**No input (turntable off or disconnected):**
```bash
arecord -D hw:2,0 -f S16_LE -r 48000 -c 1 -d 5 /tmp/off.wav && sox /tmp/off.wav -n stat 2>&1 | grep RMS
```

**Needle on record, turntable stopped (idle hum/noise only):**
```bash
arecord -D hw:2,0 -f S16_LE -r 48000 -c 1 -d 5 /tmp/stopped.wav && sox /tmp/stopped.wav -n stat 2>&1 | grep RMS
```

**Record playing:**
```bash
arecord -D hw:2,0 -f S16_LE -r 48000 -c 1 -d 5 /tmp/playing.wav && sox /tmp/playing.wav -n stat 2>&1 | grep RMS
```

Set `AUDIO_THRESHOLD` to a value roughly halfway between the **stopped** and **playing** RMS readings. For example, if stopped reads `0.004` and playing reads `0.040`, use `0.015`.

## 4. Updating songrec

The songrec binary is compiled once into a dedicated base image (`ghcr.io/fwump38/spinsense/songrec-builder:latest`) and reused by every release build. You only need to rebuild it when you want a newer version of songrec.

### When to update

- A new version of [songrec](https://github.com/marin-m/songrec) has been released and you want to pick it up.
- The Rust build environment or base image needs updating.

### How to update

1. Go to the **Actions** tab in GitHub.
2. Select the **"Build songrec Base Image"** workflow.
3. Click **"Run workflow"** → choose the `main` branch → **"Run workflow"**.
4. Wait for all jobs to complete (typically 10–20 minutes the first time; faster on subsequent runs due to GHA layer caching).
5. The new `songrec-builder:latest` multi-arch image is now published to GHCR.
6. Push a new version tag to trigger a release build — it will automatically pull the updated binary.

> The `songrec-builder` workflow also runs automatically whenever `docker/Dockerfile` is changed on `main`, so you don't need to run it manually after Dockerfile edits.

## 5. Troubleshooting

### USB Audio Device Not Detected or Not Switching

**Problem**: The USB device appears in the device list but doesn't activate when selected in the GUI.

**Solution**: 
- Configuration changes made via the web UI or environment variables take effect in-memory.
- For device changes, restart the container to reinitialize the audio input.
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
- If meters show activity but no recognition, verify `songrec` is installed and the song is in the Shazam database.

### Home Assistant Integration Not Showing Device

- If Home Assistant does not show the `SpinSense` integration, confirm the `custom_components/spinsense/` folder is in your HA config directory and restart HA.
- Verify SpinSense API is accessible: `curl http://<local-ip>:8000/api/info` from Home Assistant.
- Check Home Assistant logs for zeroconf discovery errors.
