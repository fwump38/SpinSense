# 💿 SpinSense
Integrate your analogue record player into your digital life. This tool uses audio recognition and a local HTTP/WebSocket service so Home Assistant can discover and display the song currently spinning on your turntable.

![Docker Image](https://img.shields.io/badge/docker-ghcr.io%2Ffwump38%2Fspinsense-blue) 

## ✨ Features
- Automatic ID: Powered by songrec (Shazam-compatible) for high-accuracy track recognition.

- Home Assistant discovery: The SpinSense service advertises itself over zeroconf so HA can prompt to add the integration.

- Local HTTP/WebSocket service: Home Assistant connects directly to SpinSense for live status and track metadata.

- Separate Audio Engine: The engine runs locally and the HA custom integration consumes live status from the service.

- Multi-Arch Ready: Runs natively on Raspberry Pi, Orange Pi Zero 2W (DietPi), or x64 systems.

- Guided Onboarding: A built-in Web GUI helps you calibrate your audio thresholds.

## 🚀 How It Works
- SpinSense doesn't just "guess." It monitors the RMS volume of your input device. When the needle drops:

  - Detection: It identifies a rise in volume above your calibrated THRESHOLD.

  - Recognition: It captures a 10-second high-fidelity sample and identifies it.

  - Communication: It updates the local SpinSense service with the currently playing track.

  - Silence Logic: When the side ends or the record is stopped, it waits for a SILENCE_LIMIT before marking the player as Stopped.

## 🛠 Project Structure

This project is built to be modular and Docker-first:

/core: The Python-based recognition engine.

/gui: A lightweight Flask/FastAPI web interface for configuration.

/docker: Multi-arch build files for Pi and NAS compatibility.

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

For complete installation steps, see [INSTALLATION.md](INSTALLATION.md).

