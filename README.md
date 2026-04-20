# 💿 SpinSense
Integrate your analogue record player into your digital life. This tool uses audio recognition and a local HTTP/WebSocket service so Home Assistant can discover and display the song currently spinning on your turntable.

![Docker Image](https://img.shields.io/badge/docker-ghcr.io%2Ffwump38%2Fspinsense-blue) 

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=Integration&repository=spinsense&owner=fwump38)

## ✨ Features
- Automatic ID: Powered by songrec (Shazam-compatible) for high-accuracy track recognition.

- Home Assistant discovery: The SpinSense service advertises itself over zeroconf so HA can prompt to add the integration.

- Local HTTP/WebSocket service: Home Assistant connects directly to SpinSense for live status and track metadata.

- Single Process: The recognition engine and web GUI run as a single process — no separate daemons or IPC.

- Multi-Arch Ready: Runs natively on Raspberry Pi, Orange Pi Zero 2W (DietPi), or x64 systems.

- Guided Onboarding: A built-in Web GUI helps you calibrate your audio thresholds.

- RCA-to-USB Capture Support: Use an RCA-to-USB audio capture adapter or USB audio interface with an analog line/mic input. This is a capture device, not a USB storage-style flash drive.

## 🚀 How It Works
- SpinSense doesn't just "guess." It monitors the RMS volume of your input device. When the needle drops:

  - Detection: It identifies a rise in volume above your calibrated THRESHOLD.

  - Recognition: It captures a 10-second high-fidelity sample and identifies it.

  - Communication: It updates the local SpinSense service with the currently playing track.

  - Silence Logic: When the side ends or the record is stopped, it waits for a SILENCE_LIMIT before marking the player as Stopped.

## 🛠 Project Structure

This project is built to be modular and Docker-first:

/core: The Python-based recognition engine.

/gui: A lightweight FastAPI web interface and dashboard.

/docker: Multi-stage Docker build (Rust builder for songrec + Python runtime).

## 🏗 Installation

SpinSense includes both a standalone recognition engine and a Home Assistant custom integration:

- `custom_components/spinsense/` is the HA custom integration. 
- `core_engine.py` is the standalone audio recognition engine.

### Home Assistant Installation via HACS

This repository is HACS-ready. To install it with HACS:

1. In Home Assistant, open HACS.
2. Go to `Integrations` → `+ Explore & add repositories`.
3. Add this repository URL: `https://github.com/fwump38/SpinSense`.
4. Install `SpinSense` from HACS and restart Home Assistant.

> Note: Configuration is via environment variables only. See [INSTALLATION.md](INSTALLATION.md) for details.

For complete installation steps, see [INSTALLATION.md](INSTALLATION.md).

